import pytest

from video_transcriber.exceptions import CancelledError
from video_transcriber.models import CancellationToken, JobConfig, SpeakerSegment, TranscriptSegment
from video_transcriber.pipeline import (
    ProcessingService,
    apply_speakers,
    merge_adjacent_same_speaker_segments,
    smooth_speaker_segments,
)


class _StubTranscriber:
    def transcribe(self, video_file: object, model_name: str) -> list[TranscriptSegment]:
        return [TranscriptSegment(start=0.0, end=1.0, text="Hello")]


def test_apply_speakers_uses_largest_overlap() -> None:
    segments = [
        TranscriptSegment(start=0.5, end=1.0, text="Hello"),
        TranscriptSegment(start=2.0, end=3.2, text="World"),
    ]
    speaker_segments = [
        SpeakerSegment(start=0.0, end=1.5, speaker="SPEAKER_00"),
        SpeakerSegment(start=1.5, end=2.4, speaker="SPEAKER_00"),
        SpeakerSegment(start=2.4, end=3.5, speaker="SPEAKER_01"),
    ]
    annotated = apply_speakers(segments, speaker_segments)
    assert annotated[0].speaker == "SPEAKER_00"
    assert annotated[1].speaker == "SPEAKER_01"


def test_apply_speakers_leaves_unmatched_segments_without_speaker() -> None:
    segments = [TranscriptSegment(start=5.0, end=6.0, text="Hello")]
    speaker_segments = [SpeakerSegment(start=0.0, end=1.0, speaker="SPEAKER_00")]

    annotated = apply_speakers(segments, speaker_segments)

    assert annotated[0].speaker is None


def test_merge_adjacent_same_speaker_segments_combines_text() -> None:
    merged = merge_adjacent_same_speaker_segments(
        [
            TranscriptSegment(start=0.0, end=1.0, text="Hello", speaker="SPEAKER_00"),
            TranscriptSegment(start=1.3, end=2.0, text="world", speaker="SPEAKER_00"),
            TranscriptSegment(start=3.5, end=4.0, text="Again", speaker="SPEAKER_01"),
        ]
    )

    assert len(merged) == 2
    assert merged[0].text == "Hello world"
    assert merged[0].speaker == "SPEAKER_00"


def test_smooth_speaker_segments_repairs_short_isolated_flip() -> None:
    smoothed = smooth_speaker_segments(
        [
            TranscriptSegment(start=0.0, end=1.0, text="One", speaker="SPEAKER_00"),
            TranscriptSegment(start=1.1, end=1.8, text="Two", speaker="SPEAKER_01"),
            TranscriptSegment(start=1.9, end=3.0, text="Three", speaker="SPEAKER_00"),
        ]
    )

    assert smoothed[1].speaker == "SPEAKER_00"


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
