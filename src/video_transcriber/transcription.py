"""Whisper transcription integration."""

from __future__ import annotations

from pathlib import Path

from .exceptions import DependencyError, ProcessingError
from .models import TranscriptSegment


class WhisperTranscriber:
    """Lazy-loading wrapper around Whisper models."""

    def __init__(self) -> None:
        self._models: dict[str, object] = {}

    def transcribe(self, video_file: Path, model_name: str) -> list[TranscriptSegment]:
        """Transcribe media into timestamped segments."""
        model = self._load_model(model_name)
        result = model.transcribe(str(video_file))
        raw_segments = result.get("segments") or []
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

    def _load_model(self, model_name: str) -> object:
        if model_name in self._models:
            return self._models[model_name]
        try:
            import whisper
        except ImportError as exc:
            raise DependencyError("openai-whisper is not installed.") from exc
        model = whisper.load_model(model_name)
        self._models[model_name] = model
        return model
