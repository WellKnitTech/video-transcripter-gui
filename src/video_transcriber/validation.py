"""Validation helpers for user-provided job configuration."""

from __future__ import annotations

from pathlib import Path

from .exceptions import ValidationError
from .models import JobConfig
from .utils import is_url


def validate_job_config(config: JobConfig) -> JobConfig:
    """Validate and normalize a job configuration."""
    if not config.input_value.strip():
        raise ValidationError("Provide a video URL or choose a local file.")

    if config.input_mode == "url":
        if not is_url(config.input_value):
            raise ValidationError("Enter a valid http or https URL.")
    else:
        source_file = Path(config.input_value).expanduser()
        if not source_file.exists() or not source_file.is_file():
            raise ValidationError("Choose an existing local video file.")

    if config.delay < -3600 or config.delay > 3600:
        raise ValidationError("Subtitle delay must be between -3600 and 3600 seconds.")

    if not 1 <= config.num_speakers <= 12:
        raise ValidationError("Number of speakers must be between 1 and 12.")

    if config.embed_subtitles and config.subtitle_format not in {"ass", "srt"}:
        raise ValidationError("Embedded subtitles are only supported for ASS or SRT output.")

    output_dir = config.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not output_dir.is_dir():
        raise ValidationError("Select a valid output directory.")

    return JobConfig(
        input_mode=config.input_mode,
        input_value=config.input_value.strip(),
        output_dir=output_dir,
        delay=config.delay,
        save_text=config.save_text,
        embed_subtitles=config.embed_subtitles,
        enable_diarization=config.enable_diarization,
        num_speakers=config.num_speakers,
        model_name=config.model_name,
        subtitle_format=config.subtitle_format,
    )
