"""Application processing pipeline."""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from .diarization import AudioDiarizer
from .download import download_video
from .exceptions import CancelledError, DependencyError, ProcessingError
from .models import CancellationToken, JobConfig, JobResult, SpeakerSegment, TranscriptSegment
from .subtitles import write_subtitle_file, write_text_transcript
from .transcription import WhisperTranscriber
from .utils import format_seconds, sanitize_filename

LOGGER = logging.getLogger(__name__)
EventCallback = Callable[[str, str, float | None], None]


class ProcessingService:
    """Run download, transcription, subtitle generation, and embedding."""

    def __init__(self, transcriber: WhisperTranscriber | None = None) -> None:
        self.transcriber = transcriber or WhisperTranscriber()

    def process(
        self,
        config: JobConfig,
        callback: EventCallback | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> JobResult:
        """Run a complete processing job."""
        self._ensure_dependencies()
        self._check_cancelled(cancellation_token)

        source_url = config.input_value if config.input_mode == "url" else None
        if config.input_mode == "url":
            self._emit(callback, "status", "Starting download", 0.0)
            video_file = download_video(
                config.input_value,
                config.output_dir,
                callback,
                cancellation_token,
            )
        else:
            video_file = Path(config.input_value).expanduser().resolve()
            self._emit(callback, "status", f"Using local file: {video_file.name}", 0.0)

        self._check_cancelled(cancellation_token)
        estimate = self.estimate_processing_time(video_file, config.enable_diarization)
        self._emit(
            callback,
            "status",
            f"Estimated processing time: {format_seconds(estimate)}",
            5.0,
        )

        self._emit(callback, "status", f"Loading Whisper model: {config.model_name}", 10.0)
        segments = self.transcriber.transcribe(video_file, config.model_name)
        self._emit(callback, "status", "Transcription complete", 65.0)
        self._check_cancelled(cancellation_token)

        if config.delay:
            segments = [
                TranscriptSegment(
                    start=max(segment.start + config.delay, 0.0),
                    end=max(segment.end + config.delay, 0.0),
                    text=segment.text,
                    speaker=segment.speaker,
                )
                for segment in segments
            ]

        if config.enable_diarization:
            self._emit(callback, "status", "Running speaker diarization", 72.0)
            speaker_segments = self._run_diarization(video_file, config.num_speakers)
            segments = apply_speakers(segments, speaker_segments)
            self._emit(callback, "status", "Speaker diarization complete", 82.0)
            self._check_cancelled(cancellation_token)

        base_name = sanitize_filename(video_file.stem, "transcript")
        subtitle_file = config.output_dir / f"{base_name}.{config.subtitle_format}"
        write_subtitle_file(segments, subtitle_file, config.subtitle_format, config.num_speakers)
        self._emit(callback, "status", f"Subtitle file created: {subtitle_file.name}", 90.0)
        self._check_cancelled(cancellation_token)

        text_file: Path | None = None
        if config.save_text:
            text_file = config.output_dir / f"{base_name}.txt"
            write_text_transcript(
                segments,
                text_file,
                video_file,
                source_url,
                config.enable_diarization,
                config.num_speakers,
            )
            self._emit(callback, "status", f"Transcript file created: {text_file.name}", 94.0)
            self._check_cancelled(cancellation_token)

        embedded_file: Path | None = None
        if config.embed_subtitles:
            self._emit(callback, "status", "Embedding subtitles into video", 96.0)
            embedded_file = self.embed_subtitles(video_file, subtitle_file, config.output_dir)
            self._emit(callback, "status", f"Embedded video created: {embedded_file.name}", 100.0)
        else:
            self._emit(callback, "status", "Processing complete", 100.0)

        return JobResult(
            video_file=video_file,
            subtitle_file=subtitle_file,
            segments=segments,
            text_file=text_file,
            embedded_video_file=embedded_file,
        )

    def estimate_processing_time(self, video_file: Path, enable_diarization: bool) -> float | None:
        """Estimate job runtime using media duration."""
        try:
            import ffmpeg  # pyright: ignore[reportMissingImports]
        except ImportError:
            return None

        try:
            probe = ffmpeg.probe(str(video_file))
            duration = float(probe["format"]["duration"])
        except Exception:  # pragma: no cover - depends on system ffmpeg/media
            LOGGER.exception("Unable to probe video duration for processing estimate.")
            return None

        transcription_time = duration * 0.1
        diarization_time = duration * 0.05 if enable_diarization else 0.0
        return transcription_time + diarization_time + 5.0

    def embed_subtitles(self, video_file: Path, subtitle_file: Path, output_dir: Path) -> Path:
        """Embed subtitles into a video file."""
        try:
            import ffmpeg  # pyright: ignore[reportMissingImports]
        except ImportError as exc:
            raise DependencyError("ffmpeg-python is not installed.") from exc

        output_file = output_dir / f"{sanitize_filename(video_file.stem, 'video')}_subtitled.mp4"
        subtitle_filter_path = str(subtitle_file.resolve())
        try:
            media = ffmpeg.input(str(video_file))
            video_stream = media.video.filter("subtitles", subtitle_filter_path)
            (
                ffmpeg.output(
                    video_stream,
                    media.audio,
                    str(output_file),
                    vcodec="libx264",
                    acodec="aac",
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except Exception as exc:  # pragma: no cover - depends on ffmpeg runtime
            raise ProcessingError(f"Failed to embed subtitles: {exc}") from exc
        return output_file

    def _ensure_dependencies(self) -> None:
        if shutil.which("ffmpeg") is None:
            raise DependencyError("ffmpeg is not installed or is not on PATH.")

    def _run_diarization(self, video_file: Path, num_speakers: int) -> list[SpeakerSegment]:
        try:
            import ffmpeg  # pyright: ignore[reportMissingImports]
        except ImportError as exc:
            raise DependencyError("ffmpeg-python is not installed.") from exc

        diarizer = AudioDiarizer(num_speakers=num_speakers)
        with tempfile.TemporaryDirectory(prefix="video-transcriber-") as temp_dir:
            audio_path = Path(temp_dir) / f"{video_file.stem}_audio.wav"
            try:
                (
                    ffmpeg.input(str(video_file))
                    .output(str(audio_path), acodec="pcm_s16le", ac=1, ar=16000)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            except Exception as exc:  # pragma: no cover - depends on ffmpeg runtime
                raise ProcessingError(f"Failed to extract audio for diarization: {exc}") from exc
            return diarizer.process_audio(audio_path)

    @staticmethod
    def _check_cancelled(cancellation_token: CancellationToken | None) -> None:
        if cancellation_token is not None and cancellation_token.is_cancelled():
            raise CancelledError("Job cancelled.")

    @staticmethod
    def _emit(
        callback: EventCallback | None,
        event_type: str,
        message: str,
        progress: float | None,
    ) -> None:
        if callback is not None:
            callback(event_type, message, progress)


def apply_speakers(
    segments: list[TranscriptSegment], speaker_segments: list[SpeakerSegment]
) -> list[TranscriptSegment]:
    """Attach diarization speaker labels to transcript segments."""
    if not speaker_segments:
        return segments

    annotated: list[TranscriptSegment] = []
    for segment in segments:
        speaker = None
        for speaker_segment in speaker_segments:
            if segment.start >= speaker_segment.start and segment.start < speaker_segment.end:
                speaker = speaker_segment.speaker
                break
        annotated.append(
            TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text,
                speaker=speaker,
            )
        )
    return annotated
