"""Transcript editor controller helpers for the GUI shell."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .gui_logic import build_export_path, parse_speaker_name_map, speaker_name_map_text
from .models import JobResult, SubtitleFormat, TranscriptSegment
from .subtitles import (
    parse_editable_transcript,
    render_editable_transcript,
    write_subtitle_file,
    write_text_transcript,
)


@dataclass(slots=True)
class TranscriptEditorDocument:
    """Editable transcript text plus related sidebar content."""

    contents: str
    speaker_names: str
    status: str


@dataclass(slots=True)
class TranscriptExportRequest:
    """Validated transcript export request built from editor state."""

    segments: list[TranscriptSegment]
    speaker_names: dict[str, str]
    export_path: Path
    export_format: str
    video_file: Path


def empty_editor_document() -> TranscriptEditorDocument:
    """Build the empty transcript editor state."""
    return TranscriptEditorDocument(
        contents="",
        speaker_names="",
        status="Transcript editor is empty",
    )


def generated_editor_document(result: JobResult) -> TranscriptEditorDocument:
    """Build transcript editor content from a completed job result."""
    return TranscriptEditorDocument(
        contents=render_editable_transcript(result.segments),
        speaker_names=speaker_name_map_text(result.segments),
        status="Loaded generated transcript. Make edits and export when ready.",
    )


def reset_editor_document(result: JobResult | None) -> TranscriptEditorDocument:
    """Build transcript editor state for a reset action."""
    if result is None:
        return empty_editor_document()
    return TranscriptEditorDocument(
        contents=render_editable_transcript(result.segments),
        speaker_names=speaker_name_map_text(result.segments),
        status="Transcript reset to the original generated version",
    )


def editor_status_for_text(text: str) -> str:
    """Build the short status text for edited transcript content."""
    if text.strip():
        return "Unsaved transcript edits"
    return "Transcript editor is empty"


def build_export_request(
    current_result: JobResult | None,
    editor_text: str,
    speaker_names_text: str,
    export_format: str,
    output_dir: str,
    default_output_directory: Path,
) -> TranscriptExportRequest:
    """Validate the editor state and build an export request."""
    if current_result is None:
        raise RuntimeError("Run a job first so the transcript editor has content to export.")

    return TranscriptExportRequest(
        segments=parse_editable_transcript(editor_text),
        speaker_names=parse_speaker_name_map(speaker_names_text),
        export_path=build_export_path(
            current_result.video_file,
            output_dir,
            export_format,
            default_output_directory,
        ),
        export_format=export_format,
        video_file=current_result.video_file,
    )


def write_edited_transcript_export(request: TranscriptExportRequest) -> Path:
    """Write an edited transcript export to disk."""
    request.export_path.parent.mkdir(parents=True, exist_ok=True)
    if request.export_format == "txt":
        return write_text_transcript(
            request.segments,
            request.export_path,
            request.video_file,
            None,
            request.speaker_names,
        )
    return write_subtitle_file(
        request.segments,
        request.export_path,
        subtitle_export_format(request.export_format),
        request.speaker_names,
    )


def subtitle_export_format(value: str) -> SubtitleFormat:
    """Normalize transcript editor export choices to subtitle formats."""
    if value == "srt":
        return "srt"
    if value == "vtt":
        return "vtt"
    return "ass"
