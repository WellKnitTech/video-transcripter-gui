import json
from pathlib import Path

import pytest

from video_transcriber.exceptions import SettingsError
from video_transcriber.models import AppSettings
from video_transcriber.utils import (
    calculate_sha1,
    convert_to_ass_time,
    convert_to_srt_time,
    escape_ass_text,
    is_url,
    load_settings,
    sanitize_filename,
    save_settings,
    wrap_subtitle_text,
)


def test_is_url_accepts_http_and_https() -> None:
    assert is_url("https://example.com/watch?v=123")
    assert is_url("http://example.com")
    assert not is_url("ftp://example.com")
    assert not is_url("/tmp/file.mp4")


def test_convert_to_ass_time_rounds_expected_format() -> None:
    assert convert_to_ass_time(3661.34) == "1:01:01.34"


def test_convert_to_srt_time_rounds_expected_format() -> None:
    assert convert_to_srt_time(3661.34) == "01:01:01,340"


def test_timestamp_conversion_rolls_over_correctly() -> None:
    assert convert_to_ass_time(59.995) == "0:01:00.00"
    assert convert_to_srt_time(3599.9996) == "01:00:00,000"


def test_escape_ass_text_wraps_and_escapes() -> None:
    value = escape_ass_text("Hello {world} with some fairly long text that wraps nicely")
    assert "\\{" in value
    assert r"\N" in value


def test_sanitize_filename_removes_unsafe_chars() -> None:
    assert sanitize_filename("bad:/name?.mp4") == "bad_name_.mp4"


def test_wrap_subtitle_text_breaks_long_lines() -> None:
    wrapped = wrap_subtitle_text("one two three four five six seven eight nine ten", width=14)
    assert "\n" in wrapped


def test_calculate_sha1_matches_known_value(tmp_path: Path) -> None:
    file_path = tmp_path / "data.txt"
    file_path.write_text("hello", encoding="utf-8")
    assert calculate_sha1(file_path) == "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"


def test_save_settings_writes_json(monkeypatch, tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("video_transcriber.utils.SETTINGS_PATH", settings_path)
    save_settings(AppSettings(output_dir="/tmp"))
    assert settings_path.exists()
    assert json.loads(settings_path.read_text(encoding="utf-8"))["output_dir"] == "/tmp"


def test_save_settings_raises_clean_error_when_replace_fails(monkeypatch, tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("video_transcriber.utils.SETTINGS_PATH", settings_path)

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("video_transcriber.utils.os.replace", fail_replace)

    with pytest.raises(SettingsError, match="Unable to save application settings"):
        save_settings(AppSettings(output_dir="/tmp"))

    assert list(tmp_path.iterdir()) == []


def test_load_settings_returns_defaults_for_invalid_json(monkeypatch, tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr("video_transcriber.utils.SETTINGS_PATH", settings_path)

    settings = load_settings()

    assert settings == AppSettings()
