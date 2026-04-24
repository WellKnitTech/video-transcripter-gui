import pytest

from video_transcriber.exceptions import CancelledError
from video_transcriber.models import CancellationToken, JobConfig, SpeakerSegment, TranscriptSegment
from video_transcriber.pipeline import ProcessingService, apply_speakers


class _StubTranscriber:
    def transcribe(self, video_file: object, model_name: str) -> list[TranscriptSegment]:
        return [TranscriptSegment(start=0.0, end=1.0, text="Hello")]


def test_apply_speakers_matches_segment_by_start_time() -> None:
    segments = [
        TranscriptSegment(start=0.5, end=1.0, text="Hello"),
        TranscriptSegment(start=2.0, end=3.0, text="World"),
    ]
    speaker_segments = [
        SpeakerSegment(start=0.0, end=1.5, speaker=1),
        SpeakerSegment(start=1.5, end=3.5, speaker=2),
    ]
    annotated = apply_speakers(segments, speaker_segments)
    assert annotated[0].speaker == 1
    assert annotated[1].speaker == 2


def test_process_raises_when_cancelled_before_start(tmp_path, monkeypatch) -> None:
    video_file = tmp_path / "video.mp4"
    video_file.write_text("x", encoding="utf-8")
    service = ProcessingService(transcriber=_StubTranscriber())
    token = CancellationToken()
    token.cancel()

    monkeypatch.setattr(service, "_ensure_dependencies", lambda: None)

    with pytest.raises(CancelledError):
        service.process(
            JobConfig(input_mode="file", input_value=str(video_file), output_dir=tmp_path),
            cancellation_token=token,
        )
