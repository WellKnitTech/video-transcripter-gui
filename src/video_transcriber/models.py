"""Domain models used by the application."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

InputMode = Literal["url", "file"]
SubtitleFormat = Literal["ass", "srt", "vtt"]


@dataclass(slots=True)
class JobConfig:
    input_mode: InputMode
    input_value: str
    output_dir: Path
    delay: float = 0.0
    save_text: bool = False
    embed_subtitles: bool = True
    enable_diarization: bool = False
    num_speakers: int = 2
    model_name: str = "base"
    subtitle_format: SubtitleFormat = "ass"


@dataclass(slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    speaker: int | None = None


@dataclass(slots=True)
class SpeakerSegment:
    start: float
    end: float
    speaker: int


@dataclass(slots=True)
class JobResult:
    video_file: Path
    subtitle_file: Path
    segments: list[TranscriptSegment] = field(default_factory=list)
    text_file: Path | None = None
    embedded_video_file: Path | None = None


@dataclass(slots=True)
class AppSettings:
    input_mode: InputMode = "url"
    output_dir: str = ""
    delay: str = "0.0"
    save_text: bool = False
    embed_subtitles: bool = True
    enable_diarization: bool = False
    num_speakers: str = "2"
    model_name: str = "base"
    subtitle_format: SubtitleFormat = "ass"


@dataclass(slots=True)
class CancellationToken:
    _event: threading.Event = field(default_factory=threading.Event)

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()
