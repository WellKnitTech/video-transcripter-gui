from pathlib import Path

import pytest

from video_transcriber.gui_transcript_editor import (
    build_export_request,
    editor_status_for_text,
    empty_editor_document,
    generated_editor_document,
    reset_editor_document,
    subtitle_export_format,
    write_edited_transcript_export,
)
from video_transcriber.models import JobResult, TranscriptSegment


def test_generated_editor_document_includes_transcript_text_and_speaker_map() -> None:
    result = JobResult(
        video_file=Path("sample.mp4"),
        subtitle_file=Path("sample.ass"),
        segments=[
            TranscriptSegment(start=0.0, end=1.0, text="Hello", speaker="SPEAKER_00"),
            TranscriptSegment(start=1.0, end=2.0, text="World"),
        ],
    )

    document = generated_editor_document(result)

    assert "[00:00:00.000 --> 00:00:01.000] (SPEAKER_00) Hello" in document.contents
    assert document.speaker_names == "SPEAKER_00 = SPEAKER_00"
    assert document.status == "Loaded generated transcript. Make edits and export when ready."


def test_reset_editor_document_without_result_returns_empty_state() -> None:
    document = reset_editor_document(None)

    assert document == empty_editor_document()


def test_editor_status_for_text_reflects_empty_and_modified_content() -> None:
    assert editor_status_for_text("   \n") == "Transcript editor is empty"
    assert (
        editor_status_for_text("[00:00:00.000 --> 00:00:01.000] Hello")
        == "Unsaved transcript edits"
    )


def test_build_export_request_parses_editor_text_and_uses_default_output_dir() -> None:
    result = JobResult(video_file=Path("sample.mp4"), subtitle_file=Path("sample.ass"))

    request = build_export_request(
        result,
        "[00:00:00.000 --> 00:00:01.000] (SPEAKER_00) Hello\n",
        "SPEAKER_00 = Host\n",
        "txt",
        "",
        Path("/tmp/exports"),
    )

    assert request.export_path == Path("/tmp/exports/sample_edited.txt")
    assert request.speaker_names == {"SPEAKER_00": "Host"}
    assert request.segments[0].speaker == "SPEAKER_00"


def test_build_export_request_requires_existing_result() -> None:
    with pytest.raises(RuntimeError, match="Run a job first"):
        build_export_request(None, "text", "", "txt", "", Path("/tmp/exports"))


def test_write_edited_transcript_export_writes_text_transcript(tmp_path) -> None:
    request = build_export_request(
        JobResult(video_file=tmp_path / "sample.mp4", subtitle_file=tmp_path / "sample.ass"),
        "[00:00:00.000 --> 00:00:01.000] (SPEAKER_00) Hello\n",
        "SPEAKER_00 = Host\n",
        "txt",
        str(tmp_path),
        tmp_path,
    )
    request.video_file.write_bytes(b"video-bytes")

    export_path = write_edited_transcript_export(request)

    assert export_path.exists()
    assert "Host: Hello" in export_path.read_text(encoding="utf-8")


def test_subtitle_export_format_defaults_to_ass() -> None:
    assert subtitle_export_format("srt") == "srt"
    assert subtitle_export_format("vtt") == "vtt"
    assert subtitle_export_format("ass") == "ass"
    assert subtitle_export_format("unknown") == "ass"
