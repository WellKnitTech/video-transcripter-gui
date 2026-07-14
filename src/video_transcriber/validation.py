"""Validation helpers for user-provided job configuration."""

from __future__ import annotations

from pathlib import Path

from .exceptions import ValidationError
from .models import (
    AudioCleanupPreset,
    DeviceChoice,
    JobConfig,
    SpeakerCountMode,
    SubtitleFormat,
)
from .utils import is_url, sanitize_filename

MAX_SPEAKERS = 12
VALID_SPEAKER_MODES: set[SpeakerCountMode] = {"auto", "exact", "range"}
VALID_AUDIO_PRESETS: set[AudioCleanupPreset] = {"off", "light", "meeting"}
VALID_SUBTITLE_FORMATS: set[SubtitleFormat] = {"ass", "srt", "vtt"}
VALID_DEVICES: set[DeviceChoice] = {"auto", "cpu", "cuda"}
VALID_MODEL_NAMES = {
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
    "distil-large-v3",
}
LEGACY_MODEL_NAMES = {"large"}
VALID_LANGUAGES = {
    "auto",
    "en",
    "es",
    "fr",
    "de",
    "pt",
    "it",
    "nl",
    "pl",
    "ru",
    "uk",
    "tr",
    "ar",
    "hi",
    "ja",
    "zh",
    "ko",
    "sv",
    "da",
    "fi",
    "no",
    "cs",
    "ro",
    "hu",
    "el",
    "he",
    "id",
    "ms",
    "th",
    "vi",
}


def normalize_model_name(model_name: str) -> str:
    """Normalize legacy Whisper model names to faster-whisper ids."""
    name = model_name.strip()
    if name == "large":
        return "large-v3"
    return name


def predicted_output_paths(config: JobConfig, video_stem: str) -> list[Path]:
    """Return artifact paths a job would write for the given media stem."""
    base_name = sanitize_filename(video_stem, "transcript")
    paths = [config.output_dir / f"{base_name}.{config.subtitle_format}"]
    if config.save_text:
        paths.append(config.output_dir / f"{base_name}.txt")
    if config.embed_subtitles:
        video_base = sanitize_filename(video_stem, "video")
        paths.append(config.output_dir / f"{video_base}_subtitled.mp4")
    return paths


def existing_output_conflicts(config: JobConfig, video_stem: str) -> list[Path]:
    """Return predicted output paths that already exist."""
    return [path for path in predicted_output_paths(config, video_stem) if path.exists()]


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

    raw_model = config.model_name.strip()
    if raw_model not in VALID_MODEL_NAMES | LEGACY_MODEL_NAMES:
        raise ValidationError("Choose a valid Whisper model size.")
    model_name = normalize_model_name(raw_model)

    if config.subtitle_format not in VALID_SUBTITLE_FORMATS:
        raise ValidationError("Choose a valid subtitle format.")

    if config.device not in VALID_DEVICES:
        raise ValidationError("Choose a valid device: auto, cpu, or cuda.")

    language = config.language.strip().lower() or "auto"
    if language not in VALID_LANGUAGES:
        raise ValidationError("Choose a valid language code or auto.")

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
        model_name=model_name,
        subtitle_format=config.subtitle_format,
        language=language,
        device=config.device,
    )
