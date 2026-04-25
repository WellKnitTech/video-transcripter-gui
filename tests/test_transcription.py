from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from video_transcriber.exceptions import DependencyError, ProcessingError
from video_transcriber.transcription import WhisperTranscriber


class _StubModel:
    def __init__(self, device: object, result: dict[str, object] | None = None) -> None:
        self.device = device
        self.result = result or {
            "segments": [{"start": 0.0, "end": 1.0, "text": " Hello "}],
        }
        self.calls: list[tuple[str, dict[str, object]]] = []

    def transcribe(self, audio: str, **kwargs: object) -> dict[str, object]:
        self.calls.append((audio, dict(kwargs)))
        return self.result


def test_transcribe_disables_fp16_on_cpu() -> None:
    transcriber = WhisperTranscriber()
    model = _StubModel(device="cpu")
    video_file = Path("sample.mp4")

    transcriber._models["base"] = model

    segments = transcriber.transcribe(video_file, "base")

    assert model.calls == [(str(video_file), {"fp16": False})]
    assert segments[0].text == "Hello"


def test_transcribe_keeps_default_precision_off_cpu() -> None:
    transcriber = WhisperTranscriber()
    model = _StubModel(device=types.SimpleNamespace(type="cuda"))

    transcriber._models["base"] = model

    transcriber.transcribe(Path("sample.mp4"), "base")

    assert model.calls == [("sample.mp4", {})]


def test_transcribe_raises_when_no_segments_returned() -> None:
    transcriber = WhisperTranscriber()
    transcriber._models["base"] = _StubModel(device="cpu", result={"segments": []})

    with pytest.raises(ProcessingError):
        transcriber.transcribe(Path("sample.mp4"), "base")


def test_load_model_raises_dependency_error_when_whisper_missing(monkeypatch) -> None:
    transcriber = WhisperTranscriber()
    original = sys.modules.pop("whisper", None)

    real_import = __import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "whisper":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _fake_import)

    try:
        with pytest.raises(DependencyError):
            transcriber._load_model("base")
    finally:
        if original is not None:
            sys.modules["whisper"] = original
