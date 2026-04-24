"""Tkinter GUI application."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import cast

from .exceptions import CancelledError, VideoTranscriberError
from .models import (
    AppSettings,
    CancellationToken,
    InputMode,
    JobConfig,
    JobResult,
    SubtitleFormat,
)
from .pipeline import ProcessingService
from .subtitles import (
    parse_editable_transcript,
    render_editable_transcript,
    write_subtitle_file,
    write_text_transcript,
)
from .utils import default_output_dir, load_settings, open_directory, save_settings
from .validation import validate_job_config

LOGGER = logging.getLogger(__name__)
MODEL_OPTIONS = ["tiny", "base", "small", "medium", "large"]
SUBTITLE_FORMAT_OPTIONS = ["ass", "srt", "vtt"]
QueuePayload = tuple[str, str, float | None] | JobResult | Exception


class VideoTranscriberApp:
    """Tkinter front end for the video transcriber."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Video Transcriber")
        self.root.minsize(760, 560)

        self.processing_service = ProcessingService()
        self.event_queue: queue.Queue[tuple[str, QueuePayload]] = queue.Queue()
        self.current_result: JobResult | None = None
        self.active_worker: threading.Thread | None = None
        self.cancellation_token: CancellationToken | None = None

        self.settings = load_settings()
        self._build_ui()
        self._apply_settings(self.settings)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_events)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(10, weight=1)
        container.rowconfigure(12, weight=1)

        title = ttk.Label(container, text="Video Transcriber", font=("TkDefaultFont", 18, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        self.input_mode_var = tk.StringVar(value="url")
        ttk.Label(container, text="Input mode").grid(row=1, column=0, sticky="w", pady=4)
        mode_frame = ttk.Frame(container)
        mode_frame.grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Radiobutton(
            mode_frame,
            text="Download from URL",
            variable=self.input_mode_var,
            value="url",
            command=self._update_input_mode,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_frame,
            text="Use local file",
            variable=self.input_mode_var,
            value="file",
            command=self._update_input_mode,
        ).pack(side=tk.LEFT, padx=(12, 0))

        ttk.Label(container, text="Video source").grid(row=2, column=0, sticky="w", pady=4)
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(container, textvariable=self.input_var)
        self.input_entry.grid(row=2, column=1, sticky="ew", padx=(0, 8))
        self.input_browse_button = ttk.Button(container, text="Browse", command=self._browse_input)
        self.input_browse_button.grid(row=2, column=2, sticky="ew")

        ttk.Label(container, text="Output directory").grid(row=3, column=0, sticky="w", pady=4)
        self.output_dir_var = tk.StringVar()
        output_entry = ttk.Entry(container, textvariable=self.output_dir_var)
        output_entry.grid(row=3, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(container, text="Choose", command=self._browse_output_dir).grid(
            row=3,
            column=2,
            sticky="ew",
        )

        ttk.Label(container, text="Subtitle delay (seconds)").grid(
            row=4,
            column=0,
            sticky="w",
            pady=4,
        )
        self.delay_var = tk.StringVar(value="0.0")
        ttk.Entry(container, textvariable=self.delay_var, width=10).grid(
            row=4,
            column=1,
            sticky="w",
        )

        options_frame = ttk.Frame(container)
        options_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        for column in range(4):
            options_frame.columnconfigure(column, weight=1)

        ttk.Label(options_frame, text="Whisper model").grid(row=0, column=0, sticky="w")
        self.model_name_var = tk.StringVar(value="base")
        ttk.Combobox(
            options_frame,
            textvariable=self.model_name_var,
            values=MODEL_OPTIONS,
            state="readonly",
        ).grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(options_frame, text="Subtitle format").grid(row=0, column=1, sticky="w")
        self.subtitle_format_var = tk.StringVar(value="ass")
        ttk.Combobox(
            options_frame,
            textvariable=self.subtitle_format_var,
            values=SUBTITLE_FORMAT_OPTIONS,
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(options_frame, text="Speakers").grid(row=0, column=2, sticky="w")
        self.num_speakers_var = tk.StringVar(value="2")
        ttk.Entry(options_frame, textvariable=self.num_speakers_var, width=8).grid(
            row=1,
            column=2,
            sticky="w",
            padx=(0, 8),
        )

        checkbox_frame = ttk.Frame(container)
        checkbox_frame.grid(row=6, column=0, columnspan=3, sticky="w", pady=(12, 0))
        self.enable_diarization_var = tk.BooleanVar(value=False)
        self.save_text_var = tk.BooleanVar(value=False)
        self.embed_subtitles_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            checkbox_frame,
            text="Enable speaker diarization",
            variable=self.enable_diarization_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            checkbox_frame,
            text="Save transcript as a text file",
            variable=self.save_text_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            checkbox_frame,
            text="Embed subtitles into video",
            variable=self.embed_subtitles_var,
        ).pack(anchor="w")

        action_frame = ttk.Frame(container)
        action_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(12, 8))
        self.process_button = ttk.Button(
            action_frame,
            text="Process Video",
            command=self._start_processing,
        )
        self.process_button.pack(side=tk.LEFT)
        self.cancel_button = ttk.Button(
            action_frame,
            text="Cancel",
            command=self._cancel_processing,
            state=tk.DISABLED,
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(8, 0))
        self.open_output_button = ttk.Button(
            action_frame,
            text="Open Output Folder",
            command=self._open_output_dir,
            state=tk.DISABLED,
        )
        self.open_output_button.pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(container, textvariable=self.status_var).grid(
            row=8,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 4),
        )

        self.progress_bar = ttk.Progressbar(
            container,
            orient=tk.HORIZONTAL,
            mode="determinate",
            maximum=100,
        )
        self.progress_bar.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        self.log_text = scrolledtext.ScrolledText(container, height=14, wrap=tk.WORD)
        self.log_text.grid(row=10, column=0, columnspan=3, sticky="nsew")

        editor_header = ttk.Frame(container)
        editor_header.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(12, 6))
        ttk.Label(editor_header, text="Transcript editor").pack(side=tk.LEFT)
        self.export_format_var = tk.StringVar(value="txt")
        ttk.Combobox(
            editor_header,
            textvariable=self.export_format_var,
            values=["txt", "ass", "srt", "vtt"],
            state="readonly",
            width=8,
        ).pack(side=tk.RIGHT)
        ttk.Button(
            editor_header,
            text="Export Edited Transcript",
            command=self._export_edited_transcript,
        ).pack(side=tk.RIGHT, padx=(8, 8))

        self.editor_text = scrolledtext.ScrolledText(container, height=12, wrap=tk.WORD)
        self.editor_text.grid(row=12, column=0, columnspan=3, sticky="nsew")

        self._update_input_mode()

    def _apply_settings(self, settings: AppSettings) -> None:
        self.input_mode_var.set(settings.input_mode)
        self.output_dir_var.set(settings.output_dir or str(default_output_dir()))
        self.delay_var.set(settings.delay)
        self.save_text_var.set(settings.save_text)
        self.embed_subtitles_var.set(settings.embed_subtitles)
        self.enable_diarization_var.set(settings.enable_diarization)
        self.num_speakers_var.set(settings.num_speakers)
        self.model_name_var.set(settings.model_name)
        self.subtitle_format_var.set(settings.subtitle_format)
        self._update_input_mode()

    def _browse_input(self) -> None:
        if self.input_mode_var.get() != "file":
            return
        path = filedialog.askopenfilename(
            title="Choose a local video file",
            filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All files", "*.*")],
        )
        if path:
            self.input_var.set(path)

    def _browse_output_dir(self) -> None:
        path = filedialog.askdirectory(
            title="Choose output directory",
            initialdir=self.output_dir_var.get() or str(default_output_dir()),
        )
        if path:
            self.output_dir_var.set(path)

    def _update_input_mode(self) -> None:
        is_file_mode = self.input_mode_var.get() == "file"
        self.input_browse_button.configure(state=tk.NORMAL if is_file_mode else tk.DISABLED)
        self.input_entry.configure()

    def _start_processing(self) -> None:
        if self.active_worker and self.active_worker.is_alive():
            messagebox.showinfo(
                "Job Running",
                "Wait for the current job to finish before starting another.",
            )
            return

        try:
            config = validate_job_config(self._build_config())
        except (ValueError, VideoTranscriberError) as exc:
            messagebox.showerror("Input Error", str(exc))
            return

        self._persist_settings()
        self.current_result = None
        self.cancellation_token = CancellationToken()
        self.process_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.open_output_button.configure(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.status_var.set("Working...")
        self._append_log("Starting job")
        self.editor_text.delete("1.0", tk.END)

        self.active_worker = threading.Thread(target=self._run_job, args=(config,), daemon=True)
        self.active_worker.start()

    def _run_job(self, config: JobConfig) -> None:
        try:
            result = self.processing_service.process(
                config,
                self._queue_event,
                self.cancellation_token,
            )
            self.event_queue.put(("result", result))
        except Exception as exc:  # noqa: BLE001
            if not isinstance(exc, CancelledError):
                LOGGER.exception("Job failed")
            self.event_queue.put(("error", exc))

    def _cancel_processing(self) -> None:
        if self.cancellation_token is None:
            return
        self.cancellation_token.cancel()
        self.status_var.set("Cancelling...")
        self._append_log("Cancellation requested")
        self.cancel_button.configure(state=tk.DISABLED)

    def _queue_event(self, event_type: str, message: str, progress: float | None) -> None:
        self.event_queue.put(("progress", (event_type, message, progress)))

    def _poll_events(self) -> None:
        try:
            while True:
                event_type, payload = self.event_queue.get_nowait()
                if event_type == "progress":
                    _kind, message, progress = cast(tuple[str, str, float | None], payload)
                    self.status_var.set(message)
                    self._append_log(message)
                    if progress is not None:
                        self.progress_bar["value"] = progress
                elif event_type == "result" and isinstance(payload, JobResult):
                    self.current_result = payload
                    self.process_button.configure(state=tk.NORMAL)
                    self.cancel_button.configure(state=tk.DISABLED)
                    self.open_output_button.configure(state=tk.NORMAL)
                    self.progress_bar["value"] = 100
                    self.status_var.set("Completed")
                    self.editor_text.delete("1.0", tk.END)
                    self.editor_text.insert("1.0", render_editable_transcript(payload.segments))
                    self._show_success(payload)
                elif event_type == "error" and isinstance(payload, Exception):
                    self.process_button.configure(state=tk.NORMAL)
                    self.cancel_button.configure(state=tk.DISABLED)
                    if isinstance(payload, CancelledError):
                        self.status_var.set("Cancelled")
                        self._append_log(str(payload))
                        self.progress_bar["value"] = 0
                    else:
                        self.status_var.set("Failed")
                        message = str(payload)
                        self._append_log(f"Error: {message}")
                        messagebox.showerror("Processing Error", message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_events)

    def _show_success(self, result: JobResult) -> None:
        parts = [f"Subtitle file: {result.subtitle_file}"]
        if result.text_file:
            parts.append(f"Transcript file: {result.text_file}")
        if result.embedded_video_file:
            parts.append(f"Embedded video: {result.embedded_video_file}")
        messagebox.showinfo("Success", "\n".join(parts))

    def _open_output_dir(self) -> None:
        path = Path(self.output_dir_var.get()).expanduser()
        if path.exists():
            open_directory(path)

    def _export_edited_transcript(self) -> None:
        if self.current_result is None:
            messagebox.showinfo(
                "No Transcript",
                "Run a job first so there is transcript text to edit.",
            )
            return

        try:
            segments = parse_editable_transcript(self.editor_text.get("1.0", tk.END))
        except ValueError as exc:
            messagebox.showerror("Invalid Transcript", str(exc))
            return

        export_format = self.export_format_var.get()
        base_name = self.current_result.video_file.stem + "_edited"
        output_dir = Path(self.output_dir_var.get()).expanduser()

        if export_format == "txt":
            export_path = output_dir / f"{base_name}.txt"
            write_text_transcript(
                segments,
                export_path,
                self.current_result.video_file,
                None,
                any(segment.speaker is not None for segment in segments),
                max((segment.speaker or 0) for segment in segments) + 1 if segments else 0,
            )
        else:
            export_path = output_dir / f"{base_name}.{export_format}"
            write_subtitle_file(
                segments,
                export_path,
                cast(SubtitleFormat, export_format),
                max((segment.speaker or 0) for segment in segments) + 1 if segments else 1,
            )

        self._append_log(f"Edited transcript exported: {export_path}")
        messagebox.showinfo("Exported", f"Saved edited transcript to:\n{export_path}")

    def _build_config(self) -> JobConfig:
        input_mode = self._current_input_mode()
        subtitle_format = self._current_subtitle_format()
        return JobConfig(
            input_mode=input_mode,
            input_value=self.input_var.get(),
            output_dir=Path(self.output_dir_var.get() or default_output_dir()),
            delay=float(self.delay_var.get()),
            save_text=self.save_text_var.get(),
            embed_subtitles=self.embed_subtitles_var.get(),
            enable_diarization=self.enable_diarization_var.get(),
            num_speakers=int(self.num_speakers_var.get()),
            model_name=self.model_name_var.get(),
            subtitle_format=subtitle_format,
        )

    def _persist_settings(self) -> None:
        input_mode = self._current_input_mode()
        subtitle_format = self._current_subtitle_format()
        settings = AppSettings(
            input_mode=input_mode,
            output_dir=self.output_dir_var.get(),
            delay=self.delay_var.get(),
            save_text=self.save_text_var.get(),
            embed_subtitles=self.embed_subtitles_var.get(),
            enable_diarization=self.enable_diarization_var.get(),
            num_speakers=self.num_speakers_var.get(),
            model_name=self.model_name_var.get(),
            subtitle_format=subtitle_format,
        )
        save_settings(settings)

    def _append_log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _current_input_mode(self) -> InputMode:
        value = self.input_mode_var.get()
        return "file" if value == "file" else "url"

    def _current_subtitle_format(self) -> SubtitleFormat:
        value = self.subtitle_format_var.get()
        return "srt" if value == "srt" else "ass"

    def _on_close(self) -> None:
        self._persist_settings()
        self.root.destroy()


def create_app() -> tk.Tk:
    """Create the Tkinter application root."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    root = tk.Tk()
    VideoTranscriberApp(root)
    return root
