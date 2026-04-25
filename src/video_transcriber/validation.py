"""Validation helpers for user-provided job configuration."""

from __future__ import annotations

from pathlib import Path

from .exceptions import ValidationError
from .models import AudioCleanupPreset, JobConfig, SpeakerCountMode
from .utils import is_url

MAX_SPEAKERS = 12
VALID_SPEAKER_MODES: set[SpeakerCountMode] = {"auto", "exact", "range"}
VALID_AUDIO_PRESETS: set[AudioCleanupPreset] = {"off", "light", "meeting"}


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

    if config.audio_cleanup_preset not in VALID_AUDIO_PRESETS:
        raise ValidationError("Choose a valid audio cleanup preset.")

    if config.enable_diarization:
        if config.speaker_count_mode not in VALID_SPEAKER_MODES:
            raise ValidationError("Choose a valid speaker count mode.")
        if config.speaker_count_mode == "exact":
            if config.exact_speakers is None or not 1 <= config.exact_speakers <= MAX_SPEAKERS:
                raise ValidationError("Exact speaker count must be between 1 and 12.")
        elif config.speaker_count_mode == "range":
            if config.min_speakers is None and config.max_speakers is None:
                raise ValidationError("Range mode requires a minimum, maximum, or both.")
            if config.min_speakers is not None and not 1 <= config.min_speakers <= MAX_SPEAKERS:
                raise ValidationError("Minimum speakers must be between 1 and 12.")
            if config.max_speakers is not None and not 1 <= config.max_speakers <= MAX_SPEAKERS:
                raise ValidationError("Maximum speakers must be between 1 and 12.")
            if (
                config.min_speakers is not None
                and config.max_speakers is not None
                and config.min_speakers > config.max_speakers
            ):
                raise ValidationError("Minimum speakers cannot be greater than maximum speakers.")

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
        speaker_count_mode=config.speaker_count_mode,
        exact_speakers=config.exact_speakers,
        min_speakers=config.min_speakers,
        max_speakers=config.max_speakers,
        audio_cleanup_preset=config.audio_cleanup_preset,
        model_name=config.model_name,
        subtitle_format=config.subtitle_format,
    )
