"""Queue event polling helpers for the GUI shell."""

from __future__ import annotations

import queue
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .models import JobResult

QUEUE_PROGRESS = "progress"
QUEUE_RESULT = "result"
QUEUE_ERROR = "error"
QUEUE_EXPORT_RESULT = "export_result"
QUEUE_EXPORT_ERROR = "export_error"

ProgressPayload = tuple[str, str, float | None]
QueuePayload = ProgressPayload | JobResult | Path | Exception
QueueEvent = tuple[str, QueuePayload]


@dataclass(slots=True)
class GuiEventHandlers:
    """Callbacks used to dispatch queued GUI events."""

    on_progress: Callable[[ProgressPayload], None]
    on_result: Callable[[JobResult], None]
    on_error: Callable[[Exception], None]
    on_export_result: Callable[[Path], None]
    on_export_error: Callable[[Exception], None]


class GuiEventPoller:
    """Poll queued worker events and dispatch them to handlers."""

    def __init__(
        self,
        event_queue: queue.Queue[QueueEvent],
        handlers: GuiEventHandlers,
    ) -> None:
        self._event_queue = event_queue
        self._handlers = handlers

    def queue_progress(self, event_type: str, message: str, progress: float | None) -> None:
        """Enqueue a progress update from a worker thread."""
        self._event_queue.put((QUEUE_PROGRESS, (event_type, message, progress)))

    def poll(self) -> None:
        """Drain queued events and dispatch them."""
        while True:
            try:
                event_type, payload = self._event_queue.get_nowait()
            except queue.Empty:
                return

            if event_type == QUEUE_PROGRESS and isinstance(payload, tuple):
                self._handlers.on_progress(payload)
            elif event_type == QUEUE_RESULT and isinstance(payload, JobResult):
                self._handlers.on_result(payload)
            elif event_type == QUEUE_ERROR and isinstance(payload, Exception):
                self._handlers.on_error(payload)
            elif event_type == QUEUE_EXPORT_RESULT and isinstance(payload, Path):
                self._handlers.on_export_result(payload)
            elif event_type == QUEUE_EXPORT_ERROR and isinstance(payload, Exception):
                self._handlers.on_export_error(payload)
