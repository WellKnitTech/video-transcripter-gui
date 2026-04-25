import queue
from pathlib import Path

from video_transcriber.gui_events import (
    QUEUE_ERROR,
    QUEUE_EXPORT_ERROR,
    QUEUE_EXPORT_RESULT,
    QUEUE_RESULT,
    GuiEventHandlers,
    GuiEventPoller,
    QueueEvent,
)
from video_transcriber.models import JobResult


def test_gui_event_poller_dispatches_each_supported_event() -> None:
    seen: list[tuple[str, object]] = []
    event_queue: queue.Queue[QueueEvent] = queue.Queue()
    poller = GuiEventPoller(
        event_queue,
        GuiEventHandlers(
            on_progress=lambda payload: seen.append(("progress", payload)),
            on_result=lambda payload: seen.append(("result", payload)),
            on_error=lambda payload: seen.append(("error", payload)),
            on_export_result=lambda payload: seen.append(("export_result", payload)),
            on_export_error=lambda payload: seen.append(("export_error", payload)),
        ),
    )
    result = JobResult(video_file=Path("video.mp4"), subtitle_file=Path("video.ass"))
    export_path = Path("edited.txt")
    error = RuntimeError("broken")
    export_error = ValueError("bad export")

    poller.queue_progress("status", "Downloading source", 15.0)
    event_queue.put((QUEUE_RESULT, result))
    event_queue.put((QUEUE_ERROR, error))
    event_queue.put((QUEUE_EXPORT_RESULT, export_path))
    event_queue.put((QUEUE_EXPORT_ERROR, export_error))

    poller.poll()

    assert seen == [
        ("progress", ("status", "Downloading source", 15.0)),
        ("result", result),
        ("error", error),
        ("export_result", export_path),
        ("export_error", export_error),
    ]
