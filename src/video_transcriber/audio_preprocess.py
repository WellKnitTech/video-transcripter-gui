"""Audio extraction and cleanup helpers for speaker labeling."""

from __future__ import annotations

from pathlib import Path

from .exceptions import DependencyError, ProcessingError
from .models import AudioCleanupPreset


def extract_clean_audio(video_file: Path, audio_path: Path, preset: AudioCleanupPreset) -> Path:
    """Extract mono 16 kHz audio with an optional cleanup preset."""
    try:
        import ffmpeg  # pyright: ignore[reportMissingImports]
    except ImportError as exc:
        raise DependencyError("ffmpeg-python is not installed.") from exc

    audio_stream = ffmpeg.input(str(video_file)).audio
    for filter_name, kwargs in _audio_filters_for_preset(preset):
        audio_stream = audio_stream.filter(filter_name, **kwargs)

    try:
        (
            ffmpeg.output(
                audio_stream,
                str(audio_path),
                acodec="pcm_s16le",
                ac=1,
                ar=16000,
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except Exception as exc:  # pragma: no cover - depends on ffmpeg runtime
        raise ProcessingError(f"Failed to extract audio for speaker labeling: {exc}") from exc

    return audio_path


def _audio_filters_for_preset(preset: AudioCleanupPreset) -> list[tuple[str, dict[str, int]]]:
    if preset == "off":
        return []
    filters: list[tuple[str, dict[str, int]]] = [
        ("highpass", {"f": 80}),
        ("lowpass", {"f": 8000}),
        ("dynaudnorm", {"f": 150, "g": 15}),
    ]
    if preset == "light":
        filters.append(("afftdn", {"nf": -25}))
        return filters
    filters.append(("afftdn", {"nf": -30}))
    return filters
