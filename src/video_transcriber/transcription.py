"""Whisper transcription integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from .exceptions import DependencyError, ProcessingError
from .models import TranscriptSegment


class WhisperTranscriber:
    """Lazy-loading wrapper around Whisper models."""

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}

    def transcribe(self, video_file: Path, model_name: str) -> list[TranscriptSegment]:
        """Transcribe media into timestamped segments."""
        model = self._load_model(model_name)
        result = cast(
            dict[str, Any], model.transcribe(str(video_file), **self._transcribe_options(model))
        )
        raw_segments = cast(list[dict[str, object]], result.get("segments") or [])
        segments = [
            TranscriptSegment(
                start=float(segment["start"]),
                end=float(segment["end"]),
                text=str(segment["text"]).strip(),
            )
            for segment in raw_segments
            if segment.get("text")
        ]
        if not segments:
            raise ProcessingError("The transcription completed but returned no subtitle segments.")
        return segments

    def _load_model(self, model_name: str) -> Any:
        if model_name in self._models:
            return self._models[model_name]
        try:
            import whisper
        except ImportError as exc:
            raise DependencyError("openai-whisper is not installed.") from exc
        model = cast(Any, whisper.load_model(model_name))
        self._models[model_name] = model
        return model

    def _transcribe_options(self, model: Any) -> dict[str, bool]:
        device = getattr(model, "device", None)
        device_type = getattr(device, "type", device)
        if str(device_type).lower() == "cpu":
            return {"fp16": False}
        return {}
