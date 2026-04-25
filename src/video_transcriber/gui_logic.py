"""Pure helpers for GUI state translation and exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import (
    AppSettings,
    AudioCleanupPreset,
    InputMode,
    JobConfig,
    SpeakerCountMode,
    SubtitleFormat,
    TranscriptSegment,
)


@dataclass(slots=True)
class GuiFormData:
    input_mode: InputMode
    input_value: str
    output_dir: str
    delay: str
    save_text: bool
    embed_subtitles: bool
    enable_diarization: bool
    speaker_count_mode: SpeakerCountMode
    exact_speakers: str
    min_speakers: str
    max_speakers: str
    audio_cleanup_preset: AudioCleanupPreset
    model_name: str
    subtitle_format: SubtitleFormat


def settings_to_form_data(settings: AppSettings, default_output_directory: Path) -> GuiFormData:
    """Translate persisted settings into concrete form values."""
    return GuiFormData(
        input_mode=settings.input_mode,
        input_value="",
        output_dir=settings.output_dir or str(default_output_directory),
        delay=settings.delay,
        save_text=settings.save_text,
        embed_subtitles=settings.embed_subtitles,
        enable_diarization=settings.enable_diarization,
        speaker_count_mode=settings.speaker_count_mode,
        exact_speakers=settings.exact_speakers,
        min_speakers=settings.min_speakers,
        max_speakers=settings.max_speakers,
        audio_cleanup_preset=settings.audio_cleanup_preset,
        model_name=settings.model_name,
        subtitle_format=settings.subtitle_format,
    )


def form_data_to_job_config(form_data: GuiFormData, default_output_directory: Path) -> JobConfig:
    """Translate GUI form values into a job configuration."""
    return JobConfig(
        input_mode=form_data.input_mode,
        input_value=form_data.input_value,
        output_dir=resolve_output_dir(form_data.output_dir, default_output_directory),
        delay=float(form_data.delay),
        save_text=form_data.save_text,
        embed_subtitles=form_data.embed_subtitles,
        enable_diarization=form_data.enable_diarization,
        speaker_count_mode=form_data.speaker_count_mode,
        exact_speakers=parse_optional_int(form_data.exact_speakers),
        min_speakers=parse_optional_int(form_data.min_speakers),
        max_speakers=parse_optional_int(form_data.max_speakers),
        audio_cleanup_preset=form_data.audio_cleanup_preset,
        model_name=form_data.model_name,
        subtitle_format=form_data.subtitle_format,
    )


def form_data_to_settings(form_data: GuiFormData) -> AppSettings:
    """Translate GUI form values into persisted app settings."""
    return AppSettings(
        input_mode=form_data.input_mode,
        output_dir=form_data.output_dir,
        delay=form_data.delay,
        save_text=form_data.save_text,
        embed_subtitles=form_data.embed_subtitles,
        enable_diarization=form_data.enable_diarization,
        speaker_count_mode=form_data.speaker_count_mode,
        exact_speakers=form_data.exact_speakers,
        min_speakers=form_data.min_speakers,
        max_speakers=form_data.max_speakers,
        audio_cleanup_preset=form_data.audio_cleanup_preset,
        model_name=form_data.model_name,
        subtitle_format=form_data.subtitle_format,
    )


def resolve_output_dir(output_dir: str, default_output_directory: Path) -> Path:
    """Resolve an output directory with the same fallback as the GUI."""
    return Path(output_dir or default_output_directory).expanduser()


def build_export_path(
    video_file: Path,
    output_dir: str,
    export_format: str,
    default_output_directory: Path,
) -> Path:
    """Build the export path for an edited transcript."""
    base_name = f"{video_file.stem}_edited"
    return resolve_output_dir(output_dir, default_output_directory) / f"{base_name}.{export_format}"


def friendly_status(message: str) -> str:
    """Map verbose progress messages to short UI labels."""
    lowered = message.lower()
    if "download" in lowered:
        return "Downloading"
    if "whisper model" in lowered:
        return "Loading model"
    if "transcription" in lowered or "transcrib" in lowered:
        return "Transcribing"
    if "speaker labeling" in lowered:
        return "Speaker labeling"
    if "audio" in lowered:
        return "Preparing audio"
    if "embed" in lowered:
        return "Embedding subtitles"
    if "subtitle file created" in lowered:
        return "Generating outputs"
    return message


def speaker_name_map_text(segments: list[TranscriptSegment]) -> str:
    """Render the editable speaker mapping text from transcript segments."""
    speaker_ids = sorted({segment.speaker for segment in segments if segment.speaker is not None})
    return "\n".join(f"{speaker_id} = {speaker_id}" for speaker_id in speaker_ids)


def parse_speaker_name_map(raw_text: str) -> dict[str, str]:
    """Parse editable speaker mappings from the transcript sidebar."""
    mapping: dict[str, str] = {}
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        speaker_id, display_name = line.split("=", maxsplit=1)
        speaker_id = speaker_id.strip()
        display_name = display_name.strip()
        if speaker_id and display_name:
            mapping[speaker_id] = display_name
    return mapping


def parse_optional_int(raw_value: str) -> int | None:
    """Parse an optional integer form field."""
    value = raw_value.strip()
    if not value:
        return None
    return int(value)
