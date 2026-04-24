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
        num_speakers=0,
    )
    with pytest.raises(ValidationError):
        validate_job_config(config)


def test_validate_job_config_creates_output_directory(tmp_path: Path) -> None:
    video_file = tmp_path / "video.mp4"
    video_file.write_text("x", encoding="utf-8")
    output_dir = tmp_path / "nested" / "out"
    config = JobConfig(input_mode="file", input_value=str(video_file), output_dir=output_dir)
    validated = validate_job_config(config)
    assert validated.output_dir.exists()
