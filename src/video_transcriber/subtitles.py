"""Subtitle and transcript file writers."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import TranscriptSegment
from .utils import (
    calculate_sha1,
    convert_to_ass_time,
    convert_to_srt_time,
    escape_ass_text,
    escape_srt_text,
)

EDITOR_LINE_RE = re.compile(
    r"^\[(?P<start>\d{2}:\d{2}:\d{2}\.\d{3}) --> (?P<end>\d{2}:\d{2}:\d{2}\.\d{3})\]"
    r"(?: \(Speaker (?P<speaker>\d+)\))? (?P<text>.*)$"
)

SPEAKER_COLORS = [
    "&H0000FF00",
    "&H000000FF",
    "&H00FF0000",
    "&H0000FFFF",
]


def write_subtitle_file(
    segments: list[TranscriptSegment],
    subtitle_path: Path,
    subtitle_format: str,
    num_speakers: int,
) -> Path:
    """Write subtitle output in the requested format."""
    subtitle_path.parent.mkdir(parents=True, exist_ok=True)
    if subtitle_format == "ass":
        subtitle_path.write_text(_build_ass(segments, num_speakers), encoding="utf-8")
        return subtitle_path
    if subtitle_format == "srt":
        subtitle_path.write_text(_build_srt(segments), encoding="utf-8")
        return subtitle_path
    if subtitle_format == "vtt":
        subtitle_path.write_text(_build_vtt(segments), encoding="utf-8")
        return subtitle_path
    raise ValueError(f"Unsupported subtitle format: {subtitle_format}")


def write_text_transcript(
    segments: list[TranscriptSegment],
    text_path: Path,
    video_file: Path,
    source_url: str | None,
    enable_diarization: bool,
    num_speakers: int,
) -> Path:
    """Write a human-readable transcript with metadata."""
    last_end = segments[-1].end if segments else 0.0
    lines = [
        "===== Forensic Metadata =====",
        f"Source URL: {source_url}",
        f"Video Length: {last_end:.2f} seconds",
        f"SHA1 Hash: {calculate_sha1(video_file)}",
        f"Accessed Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Original Filename: {video_file.name}",
    ]
    if enable_diarization:
        lines.append(f"Number of Speakers: {num_speakers}")
    lines.extend(["=============================", ""])

    for segment in segments:
        speaker_label = f"Speaker {segment.speaker}" if segment.speaker is not None else "Unknown"
        lines.append(f"[{segment.start:.2f} - {segment.end:.2f}] {speaker_label}: {segment.text}")

    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return text_path


def _build_ass(segments: list[TranscriptSegment], num_speakers: int) -> str:
    lines = [
        "[Script Info]",
        "Title: Whisper Transcript",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
            "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding"
        ),
        (
            "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
            "-1,0,0,0,100,100,0,0.00,1,1.00,0.00,2,10,10,10,1"
        ),
    ]
    for speaker_index in range(num_speakers):
        color = SPEAKER_COLORS[speaker_index % len(SPEAKER_COLORS)]
        lines.append(
            
                f"Style: Speaker{speaker_index},Arial,20,{color},&H000000FF,"
                "&H00000000,&H64000000,-1,0,0,0,100,100,0,0.00,1,1.00,0.00,2,"
                "10,10,10,1"
            
        )

    lines.extend([
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])
    for segment in segments:
        style = f"Speaker{segment.speaker}" if segment.speaker is not None else "Default"
        lines.append(
            
                "Dialogue: 0,"
                f"{convert_to_ass_time(segment.start)},"
                f"{convert_to_ass_time(segment.end)},"
                f"{style},,0,0,0,,{escape_ass_text(segment.text)}"
            
        )
    return "\n".join(lines) + "\n"


def _build_srt(segments: list[TranscriptSegment]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{convert_to_srt_time(segment.start)} --> {convert_to_srt_time(segment.end)}",
                    escape_srt_text(segment.text),
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def _build_vtt(segments: list[TranscriptSegment]) -> str:
    blocks = ["WEBVTT", ""]
    for segment in segments:
        blocks.extend(
            [
                (
                    f"{_seconds_to_editor_time(segment.start)} --> "
                    f"{_seconds_to_editor_time(segment.end)}"
                ),
                escape_srt_text(segment.text),
                "",
            ]
        )
    return "\n".join(blocks)


def render_editable_transcript(segments: list[TranscriptSegment]) -> str:
    """Render timestamped transcript text for user editing."""
    lines = []
    for segment in segments:
        speaker = f" (Speaker {segment.speaker})" if segment.speaker is not None else ""
        lines.append(
            f"[{_seconds_to_editor_time(segment.start)} --> {_seconds_to_editor_time(segment.end)}]"
            f"{speaker} {segment.text.strip()}"
        )
    return "\n".join(lines)


def parse_editable_transcript(text: str) -> list[TranscriptSegment]:
    """Parse edited transcript text back into timestamped segments."""
    segments: list[TranscriptSegment] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = EDITOR_LINE_RE.match(line)
        if match is None:
            raise ValueError(
                "Edited transcript lines must look like "
                "[00:00:01.000 --> 00:00:02.500] Transcript text"
            )
        speaker_text = match.group("speaker")
        segments.append(
            TranscriptSegment(
                start=_editor_time_to_seconds(match.group("start")),
                end=_editor_time_to_seconds(match.group("end")),
                text=match.group("text").strip(),
                speaker=int(speaker_text) if speaker_text is not None else None,
            )
        )
    return segments


def _seconds_to_editor_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    if milliseconds == 1000:
        secs += 1
        milliseconds = 0
    return f"{hours:02}:{minutes:02}:{secs:02}.{milliseconds:03}"


def _editor_time_to_seconds(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(".")
    return (int(hours) * 3600) + (int(minutes) * 60) + int(seconds) + int(milliseconds) / 1000
