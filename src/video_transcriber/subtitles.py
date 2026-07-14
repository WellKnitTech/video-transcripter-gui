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
    r"(?: \((?P<speaker>[^)]+)\))?(?: (?P<text>.*))?$"
)

SPEAKER_COLORS = [
    "&H0000FF00",
    "&H000000FF",
    "&H00FF0000",
    "&H0000FFFF",
    "&H00FF00FF",
    "&H0000A5FF",
    "&H0080FF80",
    "&H00FF80C0",
    "&H0080FFFF",
    "&H00FFFF80",
    "&H00C080FF",
    "&H0080C0FF",
]


def write_subtitle_file(
    segments: list[TranscriptSegment],
    subtitle_path: Path,
    subtitle_format: str,
    speaker_names: dict[str, str] | None = None,
) -> Path:
    """Write subtitle output in the requested format."""
    subtitle_path.parent.mkdir(parents=True, exist_ok=True)
    if subtitle_format == "ass":
        subtitle_path.write_text(_build_ass(segments, speaker_names), encoding="utf-8")
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
    speaker_names: dict[str, str] | None = None,
) -> Path:
    """Write a human-readable transcript with metadata."""
    last_end = segments[-1].end if segments else 0.0
    speaker_labels = sorted(
        {segment.speaker for segment in segments if segment.speaker is not None}
    )
    lines = [
        "===== Forensic Metadata =====",
        f"Source URL: {source_url}",
        f"Video Length: {last_end:.2f} seconds",
        f"SHA1 Hash: {calculate_sha1(video_file)}",
        f"Accessed Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Original Filename: {video_file.name}",
    ]
    if speaker_labels:
        lines.append(f"Speaker Labels: {len(speaker_labels)}")
    lines.extend(["=============================", ""])

    for segment in segments:
        speaker_label = _display_speaker_label(segment.speaker, speaker_names)
        lines.append(f"[{segment.start:.2f} - {segment.end:.2f}] {speaker_label}: {segment.text}")

    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return text_path


def _build_ass(
    segments: list[TranscriptSegment], speaker_names: dict[str, str] | None = None
) -> str:
    unique_speakers = [
        speaker for speaker in sorted({seg.speaker for seg in segments if seg.speaker})
    ]
    style_names = {speaker: f"Speaker{index}" for index, speaker in enumerate(unique_speakers)}
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
    for speaker_index, speaker in enumerate(unique_speakers):
        color = SPEAKER_COLORS[speaker_index % len(SPEAKER_COLORS)]
        lines.append(
            f"Style: {style_names[speaker]},Arial,20,{color},&H000000FF,"
            "&H00000000,&H64000000,-1,0,0,0,100,100,0,0.00,1,1.00,0.00,2,"
            "10,10,10,1"
        )

    lines.extend(
        [
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
    )
    for segment in segments:
        style = style_names[segment.speaker] if segment.speaker is not None else "Default"
        speaker_name = _display_speaker_label(segment.speaker, speaker_names)
        lines.append(
            "Dialogue: 0,"
            f"{convert_to_ass_time(segment.start)},"
            f"{convert_to_ass_time(segment.end)},"
            f"{style},{speaker_name},0,0,0,,{escape_ass_text(segment.text)}"
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
        speaker = f" ({segment.speaker})" if segment.speaker is not None else ""
        lines.append(
            f"[{_seconds_to_editor_time(segment.start)} --> {_seconds_to_editor_time(segment.end)}]"
            f"{speaker} {segment.text.strip()}"
        )
    return "\n".join(lines)


def parse_editable_transcript(text: str) -> list[TranscriptSegment]:
    """Parse edited transcript text back into timestamped segments."""
    segments: list[TranscriptSegment] = []
    previous_end: float | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = EDITOR_LINE_RE.match(line)
        if match is None:
            raise ValueError(
                f"Line {line_number}: edited transcript lines must look like "
                "[00:00:01.000 --> 00:00:02.500] Transcript text"
            )
        start = _editor_time_to_seconds(match.group("start"))
        end = _editor_time_to_seconds(match.group("end"))
        transcript_text = (match.group("text") or "").strip()
        if not transcript_text:
            raise ValueError(f"Line {line_number}: transcript text cannot be empty.")
        if end <= start:
            raise ValueError(
                f"Line {line_number}: end timestamp must be greater than start timestamp."
            )
        if previous_end is not None and start < previous_end:
            raise ValueError(
                f"Line {line_number}: timestamps must stay in order without overlapping."
            )
        speaker_text = match.group("speaker")
        segments.append(
            TranscriptSegment(
                start=start,
                end=end,
                text=transcript_text,
                speaker=speaker_text.strip() if speaker_text is not None else None,
            )
        )
        previous_end = end
    if not segments:
        raise ValueError("Edited transcript is empty. Add at least one timestamped line.")
    return segments


def _display_speaker_label(speaker: str | None, speaker_names: dict[str, str] | None = None) -> str:
    if speaker is None:
        return "Unknown"
    if speaker_names is None:
        return speaker
    return speaker_names.get(speaker, speaker)


def _seconds_to_editor_time(seconds: float) -> str:
    total_milliseconds = max(int(round(max(seconds, 0.0) * 1000)), 0)
    total_seconds, milliseconds = divmod(total_milliseconds, 1000)
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}.{milliseconds:03}"


def _editor_time_to_seconds(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(".")
    return (int(hours) * 3600) + (int(minutes) * 60) + int(seconds) + int(milliseconds) / 1000
