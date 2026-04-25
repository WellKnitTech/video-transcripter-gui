"""Pure utility helpers."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import re
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

from .exceptions import SettingsError
from .models import AppSettings

LOGGER = logging.getLogger(__name__)
SETTINGS_PATH = Path.home() / ".video_transcriber_gui.json"
SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]+")


def is_url(input_string: str) -> bool:
    """Check whether the input is a supported URL."""
    try:
        parsed = urlparse(input_string.strip())
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def calculate_sha1(filepath: Path) -> str:
    """Calculate the SHA1 hash for a file."""
    sha1 = hashlib.sha1()
    with filepath.open("rb") as handle:
        while data := handle.read(65536):
            sha1.update(data)
    return sha1.hexdigest()


def convert_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format."""
    hours, minutes, secs, centiseconds = _split_timestamp_parts(seconds, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centiseconds:02}"


def convert_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format."""
    hours, minutes, secs, milliseconds = _split_timestamp_parts(seconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def format_seconds(seconds: float | None) -> str:
    """Format a duration in a user-friendly way."""
    if seconds is None:
        return "unknown"
    minutes, secs = divmod(max(int(seconds), 0), 60)
    return f"{minutes}m {secs}s"


def sanitize_filename(value: str, fallback: str = "transcript") -> str:
    """Sanitize a string for use as a filesystem name."""
    cleaned = SAFE_NAME_PATTERN.sub("_", value).strip(" ._")
    return cleaned or fallback


def wrap_subtitle_text(text: str, width: int = 42) -> str:
    """Wrap subtitle text to a readable width."""
    words = text.strip().split()
    if not words:
        return ""

    lines: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in words:
        projected = current_length + len(word) + (1 if current else 0)
        if projected > width and current:
            lines.append(" ".join(current))
            current = [word]
            current_length = len(word)
        else:
            current.append(word)
            current_length = projected
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def escape_ass_text(text: str) -> str:
    """Escape text for ASS subtitle output."""
    wrapped = wrap_subtitle_text(text)
    return wrapped.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def escape_srt_text(text: str) -> str:
    """Escape text for SRT output."""
    return wrap_subtitle_text(text)


def save_settings(settings: AppSettings) -> None:
    """Persist recent application settings."""
    payload = json.dumps(asdict(settings), indent=2)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=SETTINGS_PATH.parent,
            prefix=f".{SETTINGS_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(temp_path, SETTINGS_PATH)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise SettingsError(f"Unable to save application settings: {exc}") from exc


def load_settings() -> AppSettings:
    """Load persisted application settings."""
    if not SETTINGS_PATH.exists():
        return AppSettings()
    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("Unable to read settings from %s. Falling back to defaults.", SETTINGS_PATH)
        return AppSettings()
    if not isinstance(raw, dict):
        LOGGER.warning("Settings file did not contain an object. Falling back to defaults.")
        return AppSettings()
    valid_keys = {field.name for field in AppSettings.__dataclass_fields__.values()}
    filtered = {key: value for key, value in raw.items() if key in valid_keys}
    try:
        return AppSettings(**filtered)
    except TypeError:
        LOGGER.warning("Settings file contained invalid fields. Falling back to defaults.")
        return AppSettings()


def _split_timestamp_parts(seconds: float, precision: int) -> tuple[int, int, int, int]:
    total_units = max(int(round(max(seconds, 0.0) * precision)), 0)
    total_seconds, fractional = divmod(total_units, precision)
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return hours, minutes, secs, fractional


def default_output_dir() -> Path:
    """Return a sensible default output directory."""
    downloads = Path.home() / "Downloads"
    return downloads if downloads.exists() else Path.cwd()


def open_directory(path: Path) -> None:
    """Open a directory using the platform default handler."""
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if os.name == "posix":
        import subprocess

        program_name = "open" if platform.system() == "Darwin" else "xdg-open"
        program_path = shutil.which(program_name)
        if program_path is None:
            raise FileNotFoundError(f"{program_name} is not available on this system.")
        subprocess.Popen([program_path, str(path)])
