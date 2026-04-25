from pathlib import Path

import pytest

from video_transcriber.models import TranscriptSegment
from video_transcriber.subtitles import (
    _seconds_to_editor_time,
    parse_editable_transcript,
    render_editable_transcript,
    write_subtitle_file,
    write_text_transcript,
)


def test_write_ass_subtitle_file_contains_dialogue(tmp_path: Path) -> None:
    output = tmp_path / "sample.ass"
    write_subtitle_file(
        [TranscriptSegment(start=0.0, end=1.0, text="Hello world", speaker="SPEAKER_01")],
        output,
        "ass",
        {"SPEAKER_01": "Chair"},
    )
    content = output.read_text(encoding="utf-8")
    assert "[Events]" in content
    assert "Dialogue: 0,0:00:00.00,0:00:01.00,Speaker0,Chair" in content


def test_write_srt_subtitle_file_contains_blocks(tmp_path: Path) -> None:
    output = tmp_path / "sample.srt"
    write_subtitle_file(
        [TranscriptSegment(start=0.0, end=1.5, text="Hello world")],
        output,
        "srt",
    )
    content = output.read_text(encoding="utf-8")
    assert "1\n00:00:00,000 --> 00:00:01,500" in content


def test_write_text_transcript_contains_metadata(tmp_path: Path) -> None:
    video_file = tmp_path / "video.mp4"
    video_file.write_text("video-data", encoding="utf-8")
    transcript_path = tmp_path / "sample.txt"
    write_text_transcript(
        [TranscriptSegment(start=0.0, end=1.0, text="Hello world", speaker="SPEAKER_00")],
        transcript_path,
        video_file,
        "https://example.com",
        {"SPEAKER_00": "Chair"},
    )
    content = transcript_path.read_text(encoding="utf-8")
    assert "SHA1 Hash:" in content
    assert "Chair: Hello world" in content


def test_write_vtt_subtitle_file_contains_header(tmp_path: Path) -> None:
    output = tmp_path / "sample.vtt"
    write_subtitle_file(
        [TranscriptSegment(start=0.0, end=1.5, text="Hello world")],
        output,
        "vtt",
    )
    content = output.read_text(encoding="utf-8")
    assert content.startswith("WEBVTT")


def test_editable_transcript_round_trip() -> None:
    segments = [TranscriptSegment(start=0.0, end=1.5, text="Hello world", speaker="Chair")]
    rendered = render_editable_transcript(segments)
    parsed = parse_editable_transcript(rendered)
    assert parsed == segments


def test_editor_time_rolls_over_minutes_and_hours() -> None:
    assert _seconds_to_editor_time(59.9996) == "00:01:00.000"
    assert _seconds_to_editor_time(3599.9996) == "01:00:00.000"


def test_parse_editable_transcript_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="Line 1: transcript text cannot be empty"):
        parse_editable_transcript("[00:00:01.000 --> 00:00:02.000]   ")


def test_parse_editable_transcript_rejects_reversed_timestamps() -> None:
    with pytest.raises(ValueError, match="Line 1: end timestamp must be greater"):
        parse_editable_transcript("[00:00:02.000 --> 00:00:01.000] Hello")


def test_parse_editable_transcript_rejects_overlapping_segments() -> None:
    with pytest.raises(ValueError, match="Line 2: timestamps must stay in order"):
        parse_editable_transcript(
            "\n".join(
                [
                    "[00:00:01.000 --> 00:00:03.000] Hello",
                    "[00:00:02.500 --> 00:00:04.000] World",
                ]
            )
        )


def test_parse_editable_transcript_rejects_empty_document() -> None:
    with pytest.raises(ValueError, match="Edited transcript is empty"):
        parse_editable_transcript("\n\n")
