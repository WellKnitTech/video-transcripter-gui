from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from video_transcriber.exceptions import DependencyError, ProcessingError
from video_transcriber.models import TranscriptionOptions
from video_transcriber.transcription import (
    WhisperTranscriber,
    resolve_device_and_compute,
    segments_from_faster_whisper,
)
from video_transcriber.validation import normalize_model_name


class _StubSegment:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start = start
        self.end = end
        self.text = text


class _StubModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def transcribe(self, audio: str, **kwargs: object) -> tuple[list[_StubSegment], object]:
        self.calls.append((audio, dict(kwargs)))
        return (
            [
                _StubSegment(0.0, 1.0, " Hello "),
                _StubSegment(1.0, 2.0, " "),
            ],
            SimpleNamespace(language="en"),
        )


def test_normalize_model_name_maps_large_to_large_v3() -> None:
    assert normalize_model_name("large") == "large-v3"
    assert normalize_model_name("base") == "base"


def test_resolve_device_and_compute_forces_cpu_int8() -> None:
    assert resolve_device_and_compute("cpu") == ("cpu", "int8")
    assert resolve_device_and_compute("cuda") == ("cuda", "float16")


def test_transcribe_in_process_uses_vad_and_language(monkeypatch) -> None:
    transcriber = WhisperTranscriber()
    model = _StubModel()
    monkeypatch.setattr(
        "video_transcriber.transcription.resolve_device_and_compute",
        lambda _device: ("cpu", "int8"),
    )
    transcriber._models[("base", "cpu", "int8")] = model

    segments = transcriber._transcribe_in_process(
        Path("sample.mp4"),
        TranscriptionOptions(model_name="base", language="en", device="cpu"),
    )

    assert segments[0].text == "Hello"
    assert len(segments) == 1
    assert model.calls[0][1]["vad_filter"] is True
    assert model.calls[0][1]["language"] == "en"
    assert model.calls[0][1]["beam_size"] == 5
    assert model.calls[0][1]["condition_on_previous_text"] is False


def test_transcribe_in_process_auto_language_passes_none(monkeypatch) -> None:
    transcriber = WhisperTranscriber()
    model = _StubModel()
    monkeypatch.setattr(
        "video_transcriber.transcription.resolve_device_and_compute",
        lambda _device: ("cuda", "float16"),
    )
    transcriber._models[("base", "cuda", "float16")] = model

    transcriber._transcribe_in_process(
        Path("sample.mp4"),
        TranscriptionOptions(model_name="base", language="auto", device="cuda"),
    )

    assert model.calls[0][1]["language"] is None
    assert "condition_on_previous_text" not in model.calls[0][1]


def test_segments_from_faster_whisper_rejects_empty() -> None:
    with pytest.raises(ProcessingError):
        segments_from_faster_whisper([])


def test_load_model_raises_dependency_error_when_faster_whisper_missing(monkeypatch) -> None:
    transcriber = WhisperTranscriber()
    original = sys.modules.pop("faster_whisper", None)

    real_import = __import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "faster_whisper":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _fake_import)

    try:
        with pytest.raises(DependencyError):
            transcriber._load_model("base", "cpu", "int8")
    finally:
        if original is not None:
            sys.modules["faster_whisper"] = original


def test_transcribe_in_process_maps_legacy_large(monkeypatch) -> None:
    transcriber = WhisperTranscriber()
    model = _StubModel()
    monkeypatch.setattr(
        "video_transcriber.transcription.resolve_device_and_compute",
        lambda _device: ("cpu", "int8"),
    )
    transcriber._models[("large-v3", "cpu", "int8")] = model

    transcriber._transcribe_in_process(
        Path("sample.mp4"),
        TranscriptionOptions(model_name="large", language="auto", device="cpu"),
    )

    assert model.calls
