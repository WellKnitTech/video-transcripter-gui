"""Faster-Whisper transcription integration."""

from __future__ import annotations

import multiprocessing as mp
import os
import queue
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .exceptions import CancelledError, DependencyError, ProcessingError
from .models import CancellationToken, DeviceChoice, TranscriptionOptions, TranscriptSegment
from .validation import normalize_model_name

POLL_INTERVAL_SECONDS = 0.2


class WhisperTranscriber:
    """Lazy-loading wrapper around faster-whisper models."""

    def __init__(self) -> None:
        self._models: dict[tuple[str, str, str], Any] = {}

    def transcribe(
        self,
        video_file: Path,
        options: TranscriptionOptions,
        cancellation_token: CancellationToken | None = None,
    ) -> list[TranscriptSegment]:
        """Transcribe media into timestamped segments in a killable child process."""
        self._check_cancelled(cancellation_token)
        payload = {
            "video_file": str(video_file),
            "options": asdict(options),
        }
        ctx = mp.get_context("spawn")
        result_queue: mp.Queue[tuple[str, object]] = ctx.Queue()
        process = ctx.Process(target=_transcribe_worker, args=(payload, result_queue), daemon=True)
        process.start()
        try:
            while True:
                self._check_cancelled(cancellation_token, process=process)
                try:
                    kind, value = result_queue.get(timeout=POLL_INTERVAL_SECONDS)
                except queue.Empty:
                    if not process.is_alive():
                        break
                    continue
                if kind == "result":
                    process.join(timeout=5)
                    return [
                        TranscriptSegment(
                            start=float(item["start"]),
                            end=float(item["end"]),
                            text=str(item["text"]),
                        )
                        for item in value  # type: ignore[union-attr]
                    ]
                if kind == "error":
                    process.join(timeout=5)
                    message = str(value)
                    if message.startswith("DependencyError:"):
                        raise DependencyError(message.removeprefix("DependencyError:").strip())
                    raise ProcessingError(message)
        finally:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)

        self._check_cancelled(cancellation_token)
        raise ProcessingError("Transcription worker exited without returning segments.")

    def clear_cache(self) -> None:
        """Drop cached Whisper models from this process."""
        self._models.clear()

    def _load_model(self, model_name: str, device: str, compute_type: str) -> Any:
        key = (model_name, device, compute_type)
        if key in self._models:
            return self._models[key]
        model = _create_whisper_model(model_name, device, compute_type)
        self._models[key] = model
        return model

    def _transcribe_in_process(
        self,
        video_file: Path,
        options: TranscriptionOptions,
    ) -> list[TranscriptSegment]:
        """Run transcription in the current process (used by the worker and tests)."""
        model_name = normalize_model_name(options.model_name)
        device, compute_type = resolve_device_and_compute(options.device)
        model = self._load_model(model_name, device, compute_type)
        language = None if options.language == "auto" else options.language
        segments_iter, _info = model.transcribe(
            str(video_file),
            **_transcribe_kwargs(device=device, language=language),
        )
        return segments_from_faster_whisper(segments_iter)

    @staticmethod
    def _check_cancelled(
        cancellation_token: CancellationToken | None,
        process: mp.Process | None = None,
    ) -> None:
        if cancellation_token is not None and cancellation_token.is_cancelled():
            if process is not None and process.is_alive():
                process.terminate()
                process.join(timeout=5)
            raise CancelledError("Job cancelled.")


def resolve_device_and_compute(device_choice: DeviceChoice) -> tuple[str, str]:
    """Resolve runtime device and compute type for faster-whisper."""
    if device_choice == "cpu":
        return "cpu", "int8"
    if device_choice == "cuda":
        return "cuda", "float16"
    try:
        import ctranslate2
    except ImportError:
        return "cpu", "int8"
    try:
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def cpu_thread_count() -> int:
    """Return a sensible CPU thread count for transcription."""
    return max(1, (os.cpu_count() or 4) - 1)


def _transcribe_kwargs(*, device: str, language: str | None) -> dict[str, object]:
    options: dict[str, object] = {
        "vad_filter": True,
        "beam_size": 5,
        "language": language,
    }
    if device == "cpu":
        options["condition_on_previous_text"] = False
    return options


def _create_whisper_model(model_name: str, device: str, compute_type: str) -> Any:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise DependencyError("faster-whisper is not installed.") from exc

    kwargs: dict[str, object] = {
        "device": device,
        "compute_type": compute_type,
    }
    if device == "cpu":
        kwargs["cpu_threads"] = cpu_thread_count()

    try:
        return WhisperModel(model_name, **kwargs)
    except Exception as first_exc:
        if device == "cuda" and compute_type == "float16":
            try:
                return WhisperModel(
                    model_name,
                    device="cuda",
                    compute_type="int8_float16",
                )
            except Exception as second_exc:
                raise ProcessingError(
                    f"Failed to load Whisper model '{model_name}': {second_exc}"
                ) from second_exc
        raise ProcessingError(
            f"Failed to load Whisper model '{model_name}': {first_exc}"
        ) from first_exc


def _transcribe_worker(payload: dict[str, Any], result_queue: mp.Queue) -> None:
    try:
        options = TranscriptionOptions(**payload["options"])
        transcriber = WhisperTranscriber()
        segments = transcriber._transcribe_in_process(Path(payload["video_file"]), options)
        result_queue.put(
            (
                "result",
                [
                    {"start": segment.start, "end": segment.end, "text": segment.text}
                    for segment in segments
                ],
            )
        )
    except DependencyError as exc:
        result_queue.put(("error", f"DependencyError:{exc}"))
    except Exception as exc:  # pragma: no cover - passthrough to parent
        result_queue.put(("error", str(exc)))


def segments_from_faster_whisper(raw_segments: Iterable[Any]) -> list[TranscriptSegment]:
    """Convert faster-whisper segment objects into domain segments."""
    segments = [
        TranscriptSegment(
            start=float(segment.start),
            end=float(segment.end),
            text=str(segment.text).strip(),
        )
        for segment in raw_segments
        if str(getattr(segment, "text", "")).strip()
    ]
    if not segments:
        raise ProcessingError("The transcription completed but returned no subtitle segments.")
    return segments
