from pathlib import Path

import pytest

from video_transcriber.exceptions import ValidationError
from video_transcriber.models import JobConfig
from video_transcriber.validation import validate_job_config


def test_validate_url_config_accepts_valid_input(tmp_path: Path) -> None:
    config = JobConfig(input_mode="url", input_value="https://example.com", output_dir=tmp_path)
    validated = validate_job_config(config)
    assert validated.output_dir == tmp_path


def test_validate_file_config_rejects_missing_file(tmp_path: Path) -> None:
    config = JobConfig(
        input_mode="file",
        input_value=str(tmp_path / "missing.mp4"),
        output_dir=tmp_path,
    )
    with pytest.raises(ValidationError):
        validate_job_config(config)


def test_validate_job_config_rejects_invalid_speaker_count(tmp_path: Path) -> None:
    video_file = tmp_path / "video.mp4"
    video_file.write_text("x", encoding="utf-8")
    config = JobConfig(
        input_mode="file",
        input_value=str(video_file),
        output_dir=tmp_path,
        enable_diarization=True,
        speaker_count_mode="exact",
        exact_speakers=0,
    )
    with pytest.raises(ValidationError):
        validate_job_config(config)


def test_validate_job_config_accepts_speaker_range(tmp_path: Path) -> None:
    video_file = tmp_path / "video.mp4"
    video_file.write_text("x", encoding="utf-8")
    config = JobConfig(
        input_mode="file",
        input_value=str(video_file),
        output_dir=tmp_path,
        enable_diarization=True,
        speaker_count_mode="range",
        min_speakers=2,
        max_speakers=4,
    )

    validated = validate_job_config(config)

    assert validated.min_speakers == 2
    assert validated.max_speakers == 4


def test_validate_job_config_rejects_invalid_cleanup_preset(tmp_path: Path) -> None:
    video_file = tmp_path / "video.mp4"
    video_file.write_text("x", encoding="utf-8")
    config = JobConfig(
        input_mode="file",
        input_value=str(video_file),
        output_dir=tmp_path,
        audio_cleanup_preset="light",  # type: ignore[arg-type]
    )
    config.audio_cleanup_preset = "invalid"  # type: ignore[assignment]

    with pytest.raises(ValidationError):
        validate_job_config(config)


def test_validate_job_config_creates_output_directory(tmp_path: Path) -> None:
    video_file = tmp_path / "video.mp4"
    video_file.write_text("x", encoding="utf-8")
    output_dir = tmp_path / "nested" / "out"
    config = JobConfig(input_mode="file", input_value=str(video_file), output_dir=output_dir)
    validated = validate_job_config(config)
    assert validated.output_dir.exists()
