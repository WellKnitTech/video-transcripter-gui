from pathlib import Path

from video_transcriber.gui_logic import (
    GuiFormData,
    build_export_path,
    form_data_to_job_config,
    form_data_to_settings,
    friendly_status,
    parse_optional_int,
    parse_speaker_name_map,
    settings_to_form_data,
    speaker_name_map_text,
)
from video_transcriber.models import AppSettings, TranscriptSegment


def test_settings_to_form_data_uses_default_output_dir_when_empty() -> None:
    form_data = settings_to_form_data(AppSettings(), Path("/tmp/downloads"))

    assert form_data.output_dir == "/tmp/downloads"
    assert form_data.input_mode == "url"
    assert form_data.subtitle_format == "ass"


def test_form_data_to_job_config_preserves_values_and_parses_numbers() -> None:
    form_data = GuiFormData(
        input_mode="file",
        input_value="movie.mp4",
        output_dir="~/exports",
        delay="1.5",
        save_text=True,
        embed_subtitles=False,
        enable_diarization=True,
        speaker_count_mode="range",
        exact_speakers="",
        min_speakers="2",
        max_speakers="4",
        audio_cleanup_preset="meeting",
        model_name="small",
        subtitle_format="srt",
        language="en",
        device="cpu",
    )

    config = form_data_to_job_config(form_data, Path("/fallback"))

    assert config.input_mode == "file"
    assert config.input_value == "movie.mp4"
    assert config.output_dir == Path("~/exports").expanduser()
    assert config.delay == 1.5
    assert config.enable_diarization is True
    assert config.min_speakers == 2
    assert config.max_speakers == 4
    assert config.exact_speakers is None
    assert config.subtitle_format == "srt"
    assert config.language == "en"
    assert config.device == "cpu"


def test_form_data_to_settings_keeps_empty_output_dir() -> None:
    form_data = GuiFormData(
        input_mode="url",
        input_value="https://example.com/watch?v=1",
        output_dir="",
        delay="0.0",
        save_text=False,
        embed_subtitles=True,
        enable_diarization=False,
        speaker_count_mode="auto",
        exact_speakers="",
        min_speakers="",
        max_speakers="",
        audio_cleanup_preset="light",
        model_name="base",
        subtitle_format="ass",
        language="auto",
        device="auto",
    )

    settings = form_data_to_settings(form_data)

    assert settings.output_dir == ""
    assert settings.input_mode == "url"
    assert settings.language == "auto"
    assert settings.device == "auto"


def test_settings_to_form_data_normalizes_legacy_large_model() -> None:
    form_data = settings_to_form_data(
        AppSettings(model_name="large", language="fr", device="cuda"),
        Path("/tmp/downloads"),
    )
    assert form_data.model_name == "large-v3"
    assert form_data.language == "fr"
    assert form_data.device == "cuda"


def test_build_export_path_uses_default_directory_and_suffix() -> None:
    export_path = build_export_path(
        Path("/videos/sample.mp4"),
        "",
        "txt",
        Path("/tmp/exports"),
    )

    assert export_path == Path("/tmp/exports/sample_edited.txt")


def test_speaker_name_helpers_round_trip_clean_entries() -> None:
    mapping_text = speaker_name_map_text(
        [
            TranscriptSegment(start=0.0, end=1.0, text="Hello", speaker="SPEAKER_02"),
            TranscriptSegment(start=1.0, end=2.0, text="World", speaker="SPEAKER_01"),
            TranscriptSegment(start=2.0, end=3.0, text="No label"),
        ]
    )

    assert mapping_text == "SPEAKER_01 = SPEAKER_01\nSPEAKER_02 = SPEAKER_02"
    assert parse_speaker_name_map("\n".join([mapping_text, "invalid", "SPEAKER_03 = "])) == {
        "SPEAKER_01": "SPEAKER_01",
        "SPEAKER_02": "SPEAKER_02",
    }


def test_friendly_status_maps_known_messages_and_preserves_unknown() -> None:
    assert friendly_status("Downloading source video") == "Downloading"
    assert friendly_status("Subtitle file created at output path") == "Generating outputs"
    assert friendly_status("Waiting for user input") == "Waiting for user input"


def test_parse_optional_int_returns_none_for_blank() -> None:
    assert parse_optional_int("  ") is None
    assert parse_optional_int("7") == 7
