from pathlib import Path

from video_transcriber.models import TranscriptSegment
from video_transcriber.subtitles import (
    parse_editable_transcript,
    render_editable_transcript,
    write_subtitle_file,
    write_text_transcript,
)


def test_write_ass_subtitle_file_contains_dialogue(tmp_path: Path) -> None:
    output = tmp_path / "sample.ass"
    write_subtitle_file(
        [TranscriptSegment(start=0.0, end=1.0, text="Hello world", speaker=1)],
        output,
        "ass",
        2,
    )
    content = output.read_text(encoding="utf-8")
    assert "[Events]" in content
    assert "Dialogue: 0,0:00:00.00,0:00:01.00,Speaker1" in content


def test_write_srt_subtitle_file_contains_blocks(tmp_path: Path) -> None:
    output = tmp_path / "sample.srt"
    write_subtitle_file(
        [TranscriptSegment(start=0.0, end=1.5, text="Hello world")],
        output,
        "srt",
        1,
    )
    content = output.read_text(encoding="utf-8")
    assert "1\n00:00:00,000 --> 00:00:01,500" in content


def test_write_text_transcript_contains_metadata(tmp_path: Path) -> None:
    video_file = tmp_path / "video.mp4"
    video_file.write_text("video-data", encoding="utf-8")
    transcript_path = tmp_path / "sample.txt"
    write_text_transcript(
        [TranscriptSegment(start=0.0, end=1.0, text="Hello world", speaker=0)],
        transcript_path,
        video_file,
        "https://example.com",
        True,
        2,
    )
    content = transcript_path.read_text(encoding="utf-8")
    assert "SHA1 Hash:" in content
    assert "Speaker 0: Hello world" in content


def test_write_vtt_subtitle_file_contains_header(tmp_path: Path) -> None:
    output = tmp_path / "sample.vtt"
    write_subtitle_file(
        [TranscriptSegment(start=0.0, end=1.5, text="Hello world")],
        output,
        "vtt",
        1,
    )
    content = output.read_text(encoding="utf-8")
    assert content.startswith("WEBVTT")


def test_editable_transcript_round_trip() -> None:
    segments = [TranscriptSegment(start=0.0, end=1.5, text="Hello world", speaker=2)]
    rendered = render_editable_transcript(segments)
    parsed = parse_editable_transcript(rendered)
    assert parsed == segments
