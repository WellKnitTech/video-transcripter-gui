"""Application processing pipeline."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from .audio_preprocess import extract_clean_audio
from .diarization import AudioDiarizer
from .download import download_video
from .exceptions import CancelledError, DependencyError, ProcessingError
from .models import (
    CancellationToken,
    JobConfig,
    JobResult,
    SpeakerSegment,
    TranscriptionOptions,
    TranscriptSegment,
)
from .progress import (
    DIARIZATION_BAND,
    DOWNLOAD_BAND,
    EMBED_BAND,
    LOAD_MODEL_BAND,
    TRANSCRIBE_BAND,
    WRITE_OUTPUTS_BAND,
)
from .subtitles import write_subtitle_file, write_text_transcript
from .transcription import WhisperTranscriber
from .utils import format_seconds, sanitize_filename

LOGGER = logging.getLogger(__name__)
EventCallback = Callable[[str, str, float | None], None]


class Transcriber(Protocol):
    def transcribe(
        self,
        video_file: Path,
        options: TranscriptionOptions,
        cancellation_token: CancellationToken | None = None,
    ) -> list[TranscriptSegment]: ...


class ProcessingService:
    """Run download, transcription, subtitle generation, and embedding."""

    def __init__(self, transcriber: Transcriber | None = None) -> None:
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

            def download_callback(event_type: str, message: str, progress: float | None) -> None:
                mapped = DOWNLOAD_BAND.map_percent(progress) if progress is not None else None
                if mapped is None and progress is None:
                    self._emit(callback, event_type, message, DOWNLOAD_BAND.start)
                else:
                    self._emit(callback, event_type, message, mapped)

            self._emit(callback, "status", "Starting download", DOWNLOAD_BAND.start)
            video_file = download_video(
                config.input_value,
                config.output_dir,
                download_callback,
                cancellation_token,
            )
        else:
            video_file = Path(config.input_value).expanduser().resolve()
            self._emit(
                callback,
                "status",
                f"Using local file: {video_file.name}",
                DOWNLOAD_BAND.end,
            )

        self._check_cancelled(cancellation_token)
        estimate = self.estimate_processing_time(video_file, config.enable_diarization)
        self._emit(
            callback,
            "status",
            f"Estimated processing time: {format_seconds(estimate)}",
            DOWNLOAD_BAND.end,
        )

        self._emit(
            callback,
            "status",
            f"Loading Whisper model: {config.model_name}",
            LOAD_MODEL_BAND.start,
        )
        options = TranscriptionOptions(
            model_name=config.model_name,
            language=config.language,
            device=config.device,
        )
        self._emit(callback, "status", "Starting transcription", TRANSCRIBE_BAND.start)
        segments = self.transcriber.transcribe(video_file, options, cancellation_token)
        self._emit(callback, "status", "Transcription complete", TRANSCRIBE_BAND.end)
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
            self._emit(
                callback,
                "status",
                "Preparing audio for speaker labeling",
                DIARIZATION_BAND.start,
            )
            speaker_segments = self._run_diarization(video_file, config)
            if not speaker_segments:
                self._emit(
                    callback,
                    "status",
                    "Speaker labeling skipped: insufficient voiced audio",
                    DIARIZATION_BAND.map_fraction(0.5),
                )
            else:
                self._emit(
                    callback,
                    "status",
                    "Applying speaker labels",
                    DIARIZATION_BAND.map_fraction(0.55),
                )
                segments = apply_speakers(segments, speaker_segments)
                segments = smooth_speaker_segments(segments)
                segments = merge_adjacent_same_speaker_segments(segments)
                self._emit(
                    callback,
                    "status",
                    "Speaker labeling complete",
                    DIARIZATION_BAND.end,
                )
            self._check_cancelled(cancellation_token)

        base_name = sanitize_filename(video_file.stem, "transcript")
        subtitle_file = config.output_dir / f"{base_name}.{config.subtitle_format}"
        write_subtitle_file(segments, subtitle_file, config.subtitle_format)
        self._emit(
            callback,
            "status",
            f"Subtitle file created: {subtitle_file.name}",
            WRITE_OUTPUTS_BAND.map_fraction(0.4),
        )
        self._check_cancelled(cancellation_token)

        text_file: Path | None = None
        if config.save_text:
            text_file = config.output_dir / f"{base_name}.txt"
            write_text_transcript(
                segments,
                text_file,
                video_file,
                source_url,
            )
            self._emit(
                callback,
                "status",
                f"Transcript file created: {text_file.name}",
                WRITE_OUTPUTS_BAND.map_fraction(0.8),
            )
            self._check_cancelled(cancellation_token)

        self._emit(callback, "status", "Outputs written", WRITE_OUTPUTS_BAND.end)

        embedded_file: Path | None = None
        if config.embed_subtitles:
            self._emit(callback, "status", "Embedding subtitles into video", EMBED_BAND.start)
            embedded_file = self.embed_subtitles(
                video_file,
                subtitle_file,
                config.output_dir,
                cancellation_token,
            )
            self._emit(
                callback,
                "status",
                f"Embedded video created: {embedded_file.name}",
                EMBED_BAND.end,
            )
        else:
            self._emit(callback, "status", "Processing complete", EMBED_BAND.end)

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
        speaker_labeling_time = duration * 0.08 if enable_diarization else 0.0
        return transcription_time + speaker_labeling_time + 5.0

    def embed_subtitles(
        self,
        video_file: Path,
        subtitle_file: Path,
        output_dir: Path,
        cancellation_token: CancellationToken | None = None,
    ) -> Path:
        """Embed subtitles into a video file with cancellable ffmpeg."""
        self._check_cancelled(cancellation_token)
        if shutil.which("ffmpeg") is None:
            raise DependencyError("ffmpeg is not installed or is not on PATH.")

        output_file = output_dir / f"{sanitize_filename(video_file.stem, 'video')}_subtitled.mp4"
        # Escape path for the subtitles filter.
        filter_path = str(subtitle_file.resolve()).replace("\\", "/").replace(":", "\\:")
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_file),
            "-vf",
            f"subtitles={filter_path}",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(output_file),
        ]
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            raise ProcessingError(f"Failed to start ffmpeg for embedding: {exc}") from exc

        try:
            while True:
                self._check_cancelled(cancellation_token, process=process)
                try:
                    returncode = process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    continue
                if returncode != 0:
                    stderr = b""
                    if process.stderr is not None:
                        stderr = process.stderr.read()
                    detail = stderr.decode("utf-8", errors="replace").strip()
                    raise ProcessingError(
                        f"Failed to embed subtitles: {detail or f'ffmpeg exited {returncode}'}"
                    )
                return output_file
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

    def _ensure_dependencies(self) -> None:
        if shutil.which("ffmpeg") is None:
            raise DependencyError("ffmpeg is not installed or is not on PATH.")

    def _run_diarization(self, video_file: Path, config: JobConfig) -> list[SpeakerSegment]:
        diarizer = AudioDiarizer(
            speaker_count_mode=config.speaker_count_mode,
            exact_speakers=config.exact_speakers,
            min_speakers=config.min_speakers,
            max_speakers=config.max_speakers,
        )
        with tempfile.TemporaryDirectory(prefix="video-transcriber-") as temp_dir:
            audio_path = Path(temp_dir) / f"{video_file.stem}_audio.wav"
            extract_clean_audio(video_file, audio_path, config.audio_cleanup_preset)
            return diarizer.process_audio(audio_path)

    @staticmethod
    def _check_cancelled(
        cancellation_token: CancellationToken | None,
        process: subprocess.Popen[bytes] | None = None,
    ) -> None:
        if cancellation_token is not None and cancellation_token.is_cancelled():
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
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
    """Attach speaker labels to transcript segments using largest overlap."""
    if not speaker_segments:
        return segments

    annotated: list[TranscriptSegment] = []
    for segment in segments:
        speaker = None
        best_overlap = 0.0
        for speaker_segment in speaker_segments:
            overlap = overlap_seconds(
                segment.start,
                segment.end,
                speaker_segment.start,
                speaker_segment.end,
            )
            if overlap > best_overlap:
                best_overlap = overlap
                speaker = speaker_segment.speaker
        annotated.append(
            TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text,
                speaker=speaker,
            )
        )
    return annotated


def overlap_seconds(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    """Return the overlap between two time ranges."""
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def smooth_speaker_segments(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """Smooth isolated short speaker flips between matching neighbors."""
    if len(segments) < 3:
        return segments

    smoothed = list(segments)
    for index in range(1, len(smoothed) - 1):
        previous = smoothed[index - 1]
        current = smoothed[index]
        following = smoothed[index + 1]
        short_duration = current.end - current.start <= 1.5
        nearby = current.start - previous.end <= 0.75 and following.start - current.end <= 0.75
        if (
            short_duration
            and nearby
            and previous.speaker is not None
            and previous.speaker == following.speaker
            and current.speaker != previous.speaker
        ):
            smoothed[index] = TranscriptSegment(
                start=current.start,
                end=current.end,
                text=current.text,
                speaker=previous.speaker,
            )
    return smoothed


def merge_adjacent_same_speaker_segments(
    segments: list[TranscriptSegment], max_gap_seconds: float = 0.9
) -> list[TranscriptSegment]:
    """Merge adjacent transcript segments that clearly belong together."""
    if not segments:
        return []

    merged = [segments[0]]
    for segment in segments[1:]:
        previous = merged[-1]
        gap = segment.start - previous.end
        if (
            previous.speaker == segment.speaker
            and previous.speaker is not None
            and gap <= max_gap_seconds
        ):
            merged[-1] = TranscriptSegment(
                start=previous.start,
                end=segment.end,
                text=f"{previous.text.rstrip()} {segment.text.lstrip()}".strip(),
                speaker=previous.speaker,
            )
            continue
        merged.append(segment)
    return merged
