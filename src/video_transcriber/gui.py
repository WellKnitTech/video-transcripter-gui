"""Tkinter GUI application."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Literal, cast

from .exceptions import CancelledError, SettingsError, VideoTranscriberError
from .gui_theme import PALETTE, PLACEHOLDER_TEXT
from .gui_theme import configure_styles as configure_gui_styles
from .gui_views import build_ui
from .models import (
    AppSettings,
    CancellationToken,
    InputMode,
    JobConfig,
    JobResult,
    SubtitleFormat,
    TranscriptSegment,
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
QUEUE_PROGRESS = "progress"
QUEUE_RESULT = "result"
QUEUE_ERROR = "error"
QUEUE_EXPORT_RESULT = "export_result"
QUEUE_EXPORT_ERROR = "export_error"

QueuePayload = tuple[str, str, float | None] | JobResult | Path | Exception


class VideoTranscriberApp:
    """Tkinter front end for the video transcriber."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Video Transcriber")
        self.root.geometry("1180x820")
        self.root.minsize(980, 700)
        self.root.configure(bg=PALETTE["bg"])

        self.processing_service = ProcessingService()
        self.event_queue: queue.Queue[tuple[str, QueuePayload]] = queue.Queue()
        self.current_result: JobResult | None = None
        self.active_worker: threading.Thread | None = None
        self.active_export_worker: threading.Thread | None = None
        self.cancellation_token: CancellationToken | None = None
        self._close_requested = False
        self.settings = load_settings()
        self._entry_placeholders: dict[ttk.Entry, dict[str, object]] = {}
        self.input_entry: ttk.Entry
        self.output_entry: ttk.Entry
        self.delay_entry: ttk.Entry
        self.exact_speakers_entry: ttk.Entry
        self.min_speakers_entry: ttk.Entry
        self.max_speakers_entry: ttk.Entry
        self.input_browse_button: ttk.Button
        self.output_browse_button: ttk.Button
        self.process_button: ttk.Button
        self.cancel_button: ttk.Button
        self.open_output_button: ttk.Button
        self.model_name_combo: ttk.Combobox
        self.subtitle_format_combo: ttk.Combobox
        self.speaker_mode_combo: ttk.Combobox
        self.audio_cleanup_combo: ttk.Combobox
        self.export_format_combo: ttk.Combobox
        self.reset_editor_button: ttk.Button
        self.export_button: ttk.Button
        self.inline_message_label: tk.Label
        self.progress_bar: ttk.Progressbar
        self.workspace_notebook: ttk.Notebook
        self.overview_tab: ttk.Frame
        self.logs_tab: ttk.Frame
        self.transcript_tab: ttk.Frame
        self.result_summary_label: ttk.Label
        self.log_text: tk.Text
        self.speaker_names_text: tk.Text
        self.editor_text: tk.Text

        configure_gui_styles(self.root)
        self._init_state_vars()
        build_ui(self)
        self._apply_settings(self.settings)
        self._refresh_input_mode_ui()
        self._reset_result_summary()
        self._bind_shortcuts()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_events)

    def _init_state_vars(self) -> None:
        self.status_var = tk.StringVar(value="Ready to transcribe")
        self.hero_hint_var = tk.StringVar(
            value=(
                "Turn videos into subtitles and friendly transcript exports "
                "from one calm workspace."
            )
        )
        self.input_mode_var = tk.StringVar(value="url")
        self.input_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.delay_var = tk.StringVar(value="0.0")
        self.model_name_var = tk.StringVar(value="base")
        self.subtitle_format_var = tk.StringVar(value="ass")
        self.speaker_count_mode_var = tk.StringVar(value="auto")
        self.exact_speakers_var = tk.StringVar(value="")
        self.min_speakers_var = tk.StringVar(value="")
        self.max_speakers_var = tk.StringVar(value="")
        self.audio_cleanup_preset_var = tk.StringVar(value="light")
        self.enable_diarization_var = tk.BooleanVar(value=False)
        self.save_text_var = tk.BooleanVar(value=False)
        self.embed_subtitles_var = tk.BooleanVar(value=True)
        self.export_format_var = tk.StringVar(value="txt")
        self.inline_message_var = tk.StringVar(value="")
        self.inline_message_color = tk.StringVar(value=PALETTE["muted"])
        self.mode_hint_var = tk.StringVar(value="Paste a video URL to download and transcribe.")
        self.progress_caption_var = tk.StringVar(value="No job running")
        self.summary_title_var = tk.StringVar(value="No results yet")
        self.summary_body_var = tk.StringVar(
            value=(
                "Run a job to see generated files, processing status, and "
                "transcript editing tools here."
            )
        )
        self.editor_status_var = tk.StringVar(value="Transcript editor is empty")

    def _apply_settings(self, settings: AppSettings) -> None:
        self.input_mode_var.set(settings.input_mode)
        self.output_dir_var.set(settings.output_dir or str(default_output_dir()))
        self.delay_var.set(settings.delay)
        self.save_text_var.set(settings.save_text)
        self.embed_subtitles_var.set(settings.embed_subtitles)
        self.enable_diarization_var.set(settings.enable_diarization)
        self.speaker_count_mode_var.set(settings.speaker_count_mode)
        self.exact_speakers_var.set(settings.exact_speakers)
        self.min_speakers_var.set(settings.min_speakers)
        self.max_speakers_var.set(settings.max_speakers)
        self.audio_cleanup_preset_var.set(settings.audio_cleanup_preset)
        self.model_name_var.set(settings.model_name)
        self.subtitle_format_var.set(settings.subtitle_format)
        self._refresh_speaker_mode_ui()
        self._refresh_placeholders()

    def _browse_input(self) -> None:
        if self._current_input_mode() != "file":
            return
        path = filedialog.askopenfilename(
            title="Choose a local video file",
            filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All files", "*.*")],
        )
        if path:
            self.input_var.set(path)
            self._set_inline_message("", tone="muted")

    def _browse_output_dir(self) -> None:
        path = filedialog.askdirectory(
            title="Choose output directory",
            initialdir=self.output_dir_var.get() or str(default_output_dir()),
        )
        if path:
            self.output_dir_var.set(path)
            self._set_inline_message("", tone="muted")

    def _refresh_input_mode_ui(self) -> None:
        is_file_mode = self._current_input_mode() == "file"
        self.input_browse_button.configure(state=tk.NORMAL if is_file_mode else tk.DISABLED)
        self.mode_hint_var.set(
            (
                "Choose a local video file from your computer. Outputs will still "
                "go to the folder you pick below."
            )
            if is_file_mode
            else "Paste a video URL to download, transcribe, and export from one run."
        )
        self.hero_hint_var.set(
            "Drop in a local file for a quiet editing workflow."
            if is_file_mode
            else "Download, transcribe, and polish a video from the web in one calm workspace."
        )
        self._refresh_placeholders()

    def _refresh_speaker_mode_ui(self) -> None:
        mode = self.speaker_count_mode_var.get()
        speakers_enabled = self.enable_diarization_var.get()
        exact_state = tk.NORMAL if speakers_enabled and mode == "exact" else tk.DISABLED
        range_state = tk.NORMAL if speakers_enabled and mode == "range" else tk.DISABLED
        combo_state = "readonly"
        if hasattr(self, "exact_speakers_entry"):
            self.exact_speakers_entry.configure(state=exact_state)
            self.min_speakers_entry.configure(state=range_state)
            self.max_speakers_entry.configure(state=range_state)
            self.audio_cleanup_combo.configure(
                state=combo_state if speakers_enabled else tk.DISABLED
            )

    def _start_processing(self) -> None:
        if self.active_worker and self.active_worker.is_alive():
            self._set_inline_message(
                "A job is already running. Wait for it to finish or cancel it first.",
                tone="warning",
            )
            return

        try:
            config = validate_job_config(self._build_config())
        except (ValueError, VideoTranscriberError) as exc:
            self._set_inline_message(str(exc), tone="danger")
            self.status_var.set("Please fix the highlighted details")
            return

        self._persist_settings()
        self.current_result = None
        self.cancellation_token = CancellationToken()
        self._set_running_state(True)
        self._set_inline_message(
            "Job started. You can follow progress from the overview and logs.",
            tone="success",
        )
        self.status_var.set("Preparing job")
        self.progress_caption_var.set("Creating a new transcription job")
        self.progress_bar["value"] = 0
        self._append_log("Starting job")
        self._reset_result_summary()
        self._set_editor_contents("")
        self.workspace_notebook.select(self.overview_tab)

        self.active_worker = threading.Thread(target=self._run_job, args=(config,), daemon=True)
        self.active_worker.start()

    def _run_job(self, config: JobConfig) -> None:
        try:
            result = self.processing_service.process(
                config,
                self._queue_event,
                self.cancellation_token,
            )
            self.event_queue.put((QUEUE_RESULT, result))
        except Exception as exc:  # noqa: BLE001
            if not isinstance(exc, CancelledError):
                LOGGER.exception("Job failed")
            self.event_queue.put((QUEUE_ERROR, exc))

    def _cancel_processing(self) -> None:
        if self.cancellation_token is None:
            return
        self.cancellation_token.cancel()
        self.status_var.set("Cancelling")
        self.progress_caption_var.set("Waiting for the active step to stop safely")
        self._append_log("Cancellation requested")
        self._set_inline_message(
            "Cancellation requested. The current step may need a moment to finish.",
            tone="warning",
        )
        self.cancel_button.configure(state=tk.DISABLED)

    def _queue_event(self, event_type: str, message: str, progress: float | None) -> None:
        self.event_queue.put((QUEUE_PROGRESS, (event_type, message, progress)))

    def _poll_events(self) -> None:
        try:
            while True:
                event_type, payload = self.event_queue.get_nowait()
                if event_type == QUEUE_PROGRESS:
                    _kind, message, progress = cast(tuple[str, str, float | None], payload)
                    self.status_var.set(self._friendly_status(message))
                    self.progress_caption_var.set(message)
                    self._append_log(message)
                    if progress is not None:
                        self.progress_bar["value"] = progress
                elif event_type == QUEUE_RESULT and isinstance(payload, JobResult):
                    self.active_worker = None
                    self.current_result = payload
                    self._set_running_state(False)
                    self.progress_bar["value"] = 100
                    self.status_var.set("Completed")
                    self.progress_caption_var.set("Your outputs are ready below")
                    self._set_inline_message(
                        (
                            "Everything finished cleanly. Review the files in the "
                            "overview or refine the transcript in the editor."
                        ),
                        tone="success",
                    )
                    self._update_result_summary(payload)
                    self._set_editor_contents(render_editable_transcript(payload.segments))
                    self._set_speaker_name_map(payload.segments)
                    self.editor_status_var.set(
                        "Loaded generated transcript. Make edits and export when ready."
                    )
                    self.workspace_notebook.select(self.transcript_tab)
                    if self._close_requested:
                        self._finish_close_when_idle()
                elif event_type == QUEUE_ERROR and isinstance(payload, Exception):
                    self.active_worker = None
                    self._set_running_state(False)
                    if isinstance(payload, CancelledError):
                        self.status_var.set("Cancelled")
                        self.progress_bar["value"] = 0
                        self.progress_caption_var.set("The active job was cancelled")
                        self._append_log(str(payload))
                        self._set_inline_message(
                            (
                                "The job was cancelled before completion. Adjust "
                                "settings and start again when ready."
                            ),
                            tone="warning",
                        )
                        if self._close_requested:
                            self._finish_close_when_idle()
                    else:
                        self._close_requested = False
                        self.status_var.set("Failed")
                        self.progress_caption_var.set("Something went wrong during processing")
                        message = str(payload)
                        self._append_log(f"Error: {message}")
                        self._set_inline_message(message, tone="danger")
                        messagebox.showerror("Processing Error", message)
                elif event_type == QUEUE_EXPORT_RESULT and isinstance(payload, Path):
                    self.active_export_worker = None
                    self._set_export_state(False)
                    self._append_log(f"Edited transcript exported: {payload}")
                    self.editor_status_var.set(f"Last export: {payload.name}")
                    self._set_inline_message(
                        f"Saved edited transcript to {payload}", tone="success"
                    )
                elif event_type == QUEUE_EXPORT_ERROR and isinstance(payload, Exception):
                    self.active_export_worker = None
                    self._set_export_state(False)
                    message = str(payload)
                    self._append_log(f"Export error: {message}")
                    self.editor_status_var.set("Export failed")
                    self._set_inline_message(message, tone="danger")
                    messagebox.showerror("Export Error", message)
        except queue.Empty:
            pass
        finally:
            if self.root.winfo_exists():
                self.root.after(100, self._poll_events)

    def _friendly_status(self, message: str) -> str:
        lowered = message.lower()
        if "download" in lowered:
            return "Downloading"
        if "whisper model" in lowered:
            return "Loading model"
        if "transcription" in lowered or "transcrib" in lowered:
            return "Transcribing"
        if "speaker labeling" in lowered:
            return "Speaker labeling"
        if "audio" in lowered:
            return "Preparing audio"
        if "embed" in lowered:
            return "Embedding subtitles"
        if "subtitle file created" in lowered:
            return "Generating outputs"
        return message

    def _set_running_state(self, is_running: bool) -> None:
        self.process_button.configure(state=tk.DISABLED if is_running else tk.NORMAL)
        self.cancel_button.configure(state=tk.NORMAL if is_running else tk.DISABLED)
        self.open_output_button.configure(
            state=tk.DISABLED if is_running or not self.current_result else tk.NORMAL
        )

        field_state = tk.DISABLED if is_running else tk.NORMAL
        combo_state = tk.DISABLED if is_running else "readonly"
        for widget in [
            self.input_entry,
            self.output_entry,
            self.delay_entry,
            self.exact_speakers_entry,
            self.min_speakers_entry,
            self.max_speakers_entry,
        ]:
            widget.configure(state=field_state)
        for widget in [
            self.model_name_combo,
            self.subtitle_format_combo,
            self.speaker_mode_combo,
            self.audio_cleanup_combo,
        ]:
            widget.configure(state=combo_state)
        input_browse_state = tk.DISABLED
        if not is_running and self._current_input_mode() == "file":
            input_browse_state = tk.NORMAL
        self.input_browse_button.configure(state=input_browse_state)
        self.output_browse_button.configure(state=field_state)
        if not is_running:
            self._refresh_speaker_mode_ui()

    def _set_export_state(self, is_exporting: bool) -> None:
        self.export_button.configure(state=tk.DISABLED if is_exporting else tk.NORMAL)
        self.reset_editor_button.configure(state=tk.DISABLED if is_exporting else tk.NORMAL)
        self.export_format_combo.configure(state=tk.DISABLED if is_exporting else "readonly")

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-Return>", self._handle_start_shortcut)
        self.root.bind("<Escape>", self._handle_cancel_shortcut)
        self.root.bind("<Control-o>", self._handle_open_output_shortcut)
        self.root.bind("<Control-O>", self._handle_open_output_shortcut)
        self.root.bind("<Control-Shift-O>", self._handle_choose_output_shortcut)
        self.root.bind("<Control-l>", self._handle_local_file_shortcut)
        self.root.bind("<Control-L>", self._handle_local_file_shortcut)
        self.root.bind("<Control-e>", self._handle_export_shortcut)
        self.root.bind("<Control-E>", self._handle_export_shortcut)

    def _handle_start_shortcut(self, _event: tk.Event[tk.Misc]) -> str:
        self._start_processing()
        return "break"

    def _handle_cancel_shortcut(self, _event: tk.Event[tk.Misc]) -> str:
        self._cancel_processing()
        return "break"

    def _handle_open_output_shortcut(self, _event: tk.Event[tk.Misc]) -> str:
        self._open_output_dir()
        return "break"

    def _handle_choose_output_shortcut(self, _event: tk.Event[tk.Misc]) -> str:
        if self.output_browse_button.cget("state") != tk.DISABLED:
            self._browse_output_dir()
        return "break"

    def _handle_local_file_shortcut(self, _event: tk.Event[tk.Misc]) -> str:
        self.input_mode_var.set("file")
        self._refresh_input_mode_ui()
        if self.input_browse_button.cget("state") != tk.DISABLED:
            self._browse_input()
        return "break"

    def _handle_export_shortcut(self, _event: tk.Event[tk.Misc]) -> str:
        self._export_edited_transcript()
        return "break"

    def _install_placeholder(
        self,
        entry: ttk.Entry,
        variable: tk.StringVar,
        placeholder: str,
    ) -> None:
        self._entry_placeholders[entry] = {"text": placeholder, "active": False}
        entry.bind("<FocusIn>", lambda _event, e=entry, v=variable: self._clear_placeholder(e, v))
        entry.bind("<FocusOut>", lambda _event, e=entry, v=variable: self._apply_placeholder(e, v))
        self._apply_placeholder(entry, variable)

    def _refresh_placeholders(self) -> None:
        input_placeholder = (
            PLACEHOLDER_TEXT["file"]
            if self._current_input_mode() == "file"
            else PLACEHOLDER_TEXT["url"]
        )
        self._entry_placeholders[self.input_entry]["text"] = input_placeholder
        self._apply_placeholder(self.input_entry, self.input_var)
        self._apply_placeholder(self.output_entry, self.output_dir_var)

    def _apply_placeholder(self, entry: ttk.Entry, variable: tk.StringVar) -> None:
        current_text = variable.get().strip()
        placeholder_state = self._entry_placeholders.get(entry, {"text": "", "active": False})
        placeholder_text = cast(str, placeholder_state["text"])
        placeholder_active = bool(placeholder_state["active"])
        if current_text and not placeholder_active:
            entry.configure(foreground=PALETTE["text"])
            return
        if placeholder_text and not current_text and not entry.focus_get() == entry:
            variable.set(placeholder_text)
            entry.configure(foreground=PALETTE["muted"])
            placeholder_state["active"] = True

    def _clear_placeholder(self, entry: ttk.Entry, variable: tk.StringVar) -> None:
        placeholder_state = self._entry_placeholders.get(entry, {"text": "", "active": False})
        if bool(placeholder_state["active"]):
            variable.set("")
            entry.configure(foreground=PALETTE["text"])
            placeholder_state["active"] = False

    def _value_without_placeholder(self, entry: ttk.Entry, variable: tk.StringVar) -> str:
        placeholder_state = self._entry_placeholders.get(entry, {"active": False})
        return "" if bool(placeholder_state["active"]) else variable.get().strip()

    def _reset_result_summary(self) -> None:
        self.summary_title_var.set("No results yet")
        self.summary_body_var.set(
            "Run a job to see generated files, progress notes, and transcript editing tools here."
        )

    def _update_result_summary(self, result: JobResult) -> None:
        pieces = [f"Subtitle file ready: {result.subtitle_file.name}"]
        if result.text_file is not None:
            pieces.append(f"Transcript text saved: {result.text_file.name}")
        if result.embedded_video_file is not None:
            pieces.append(f"Embedded video ready: {result.embedded_video_file.name}")
        pieces.append(f"Segments loaded into editor: {len(result.segments)}")
        self.summary_title_var.set("Your outputs are ready")
        self.summary_body_var.set("\n".join(pieces))

    def _open_output_dir(self) -> None:
        path = Path(
            self._value_without_placeholder(self.output_entry, self.output_dir_var)
        ).expanduser()
        if path.exists():
            open_directory(path)

    def _export_edited_transcript(self) -> None:
        if self.current_result is None:
            self._set_inline_message(
                "Run a job first so the transcript editor has content to export.",
                tone="warning",
            )
            self.workspace_notebook.select(self.transcript_tab)
            return

        if self.active_export_worker and self.active_export_worker.is_alive():
            self._set_inline_message("An export is already running.", tone="warning")
            return

        try:
            segments = parse_editable_transcript(self.editor_text.get("1.0", tk.END))
        except ValueError as exc:
            self._set_inline_message(str(exc), tone="danger")
            self.workspace_notebook.select(self.transcript_tab)
            return

        speaker_names = self._parse_speaker_name_map()
        export_format = self.export_format_var.get()
        base_name = self.current_result.video_file.stem + "_edited"
        output_dir = Path(
            self._value_without_placeholder(self.output_entry, self.output_dir_var)
            or default_output_dir()
        ).expanduser()
        export_path = output_dir / f"{base_name}.{export_format}"

        self._set_export_state(True)
        self._append_log(f"Exporting edited transcript to {export_path}")
        self.editor_status_var.set("Export in progress")
        self._set_inline_message("Exporting edited transcript in the background.", tone="muted")

        self.active_export_worker = threading.Thread(
            target=self._run_export,
            args=(segments, speaker_names, export_path, export_format),
            daemon=True,
        )
        self.active_export_worker.start()

    def _run_export(
        self,
        segments: list[TranscriptSegment],
        speaker_names: dict[str, str],
        export_path: Path,
        export_format: str,
    ) -> None:
        try:
            export_path.parent.mkdir(parents=True, exist_ok=True)
            current_result = self.current_result
            if export_format == "txt":
                if current_result is None:
                    raise RuntimeError(
                        "Run a job first so the transcript editor has content to export."
                    )
                write_text_transcript(
                    segments,
                    export_path,
                    current_result.video_file,
                    None,
                    speaker_names,
                )
            else:
                write_subtitle_file(
                    segments,
                    export_path,
                    cast(SubtitleFormat, export_format),
                    speaker_names,
                )
            self.event_queue.put((QUEUE_EXPORT_RESULT, export_path))
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Edited transcript export failed")
            self.event_queue.put((QUEUE_EXPORT_ERROR, exc))

    def _reset_transcript_editor(self) -> None:
        if self.current_result is None:
            self._set_editor_contents("")
            self._set_speaker_name_map([])
            self.editor_status_var.set("Transcript editor is empty")
            return
        self._set_editor_contents(render_editable_transcript(self.current_result.segments))
        self._set_speaker_name_map(self.current_result.segments)
        self.editor_status_var.set("Transcript reset to the original generated version")
        self._set_inline_message("Transcript editor reset to the generated output.", tone="muted")

    def _build_config(self) -> JobConfig:
        input_mode = self._current_input_mode()
        subtitle_format = self._current_subtitle_format()
        return JobConfig(
            input_mode=input_mode,
            input_value=self._value_without_placeholder(self.input_entry, self.input_var),
            output_dir=Path(
                self._value_without_placeholder(self.output_entry, self.output_dir_var)
                or default_output_dir()
            ),
            delay=float(self.delay_var.get()),
            save_text=self.save_text_var.get(),
            embed_subtitles=self.embed_subtitles_var.get(),
            enable_diarization=self.enable_diarization_var.get(),
            speaker_count_mode=cast(
                Literal["auto", "exact", "range"], self.speaker_count_mode_var.get()
            ),
            exact_speakers=self._parse_optional_int(self.exact_speakers_var.get()),
            min_speakers=self._parse_optional_int(self.min_speakers_var.get()),
            max_speakers=self._parse_optional_int(self.max_speakers_var.get()),
            audio_cleanup_preset=cast(
                Literal["off", "light", "meeting"], self.audio_cleanup_preset_var.get()
            ),
            model_name=self.model_name_var.get(),
            subtitle_format=subtitle_format,
        )

    def _persist_settings(self) -> None:
        settings = AppSettings(
            input_mode=self._current_input_mode(),
            output_dir=self._value_without_placeholder(self.output_entry, self.output_dir_var),
            delay=self.delay_var.get(),
            save_text=self.save_text_var.get(),
            embed_subtitles=self.embed_subtitles_var.get(),
            enable_diarization=self.enable_diarization_var.get(),
            speaker_count_mode=cast(
                Literal["auto", "exact", "range"], self.speaker_count_mode_var.get()
            ),
            exact_speakers=self.exact_speakers_var.get(),
            min_speakers=self.min_speakers_var.get(),
            max_speakers=self.max_speakers_var.get(),
            audio_cleanup_preset=cast(
                Literal["off", "light", "meeting"], self.audio_cleanup_preset_var.get()
            ),
            model_name=self.model_name_var.get(),
            subtitle_format=self._current_subtitle_format(),
        )
        try:
            save_settings(settings)
        except SettingsError as exc:
            LOGGER.warning("Unable to persist settings: %s", exc)
            self._append_log(str(exc))
            self._set_inline_message(
                "Settings could not be saved. The app will keep running with your current values.",
                tone="warning",
            )

    def _parse_optional_int(self, raw_value: str) -> int | None:
        value = raw_value.strip()
        if not value:
            return None
        return int(value)

    def _set_speaker_name_map(self, segments: list[TranscriptSegment]) -> None:
        speaker_ids = sorted(
            {segment.speaker for segment in segments if segment.speaker is not None}
        )
        self.speaker_names_text.delete("1.0", tk.END)
        if speaker_ids:
            lines = [f"{speaker_id} = {speaker_id}" for speaker_id in speaker_ids]
            self.speaker_names_text.insert("1.0", "\n".join(lines))

    def _parse_speaker_name_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for raw_line in self.speaker_names_text.get("1.0", tk.END).splitlines():
            line = raw_line.strip()
            if not line or "=" not in line:
                continue
            speaker_id, display_name = line.split("=", maxsplit=1)
            speaker_id = speaker_id.strip()
            display_name = display_name.strip()
            if speaker_id and display_name:
                mapping[speaker_id] = display_name
        return mapping

    def _append_log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _set_inline_message(self, message: str, *, tone: str) -> None:
        colors = {
            "muted": PALETTE["muted"],
            "success": PALETTE["success"],
            "warning": PALETTE["warning"],
            "danger": PALETTE["danger"],
        }
        self.inline_message_var.set(message)
        self.inline_message_label.configure(fg=colors.get(tone, PALETTE["muted"]))

    def _set_editor_contents(self, text: str) -> None:
        self.editor_text.delete("1.0", tk.END)
        if text:
            self.editor_text.insert("1.0", text)
        self.editor_text.edit_modified(False)

    def _handle_editor_modified(self, _event: tk.Event[tk.Misc]) -> None:
        if not self.editor_text.edit_modified():
            return
        content = self.editor_text.get("1.0", tk.END).strip()
        if not content:
            self.editor_status_var.set("Transcript editor is empty")
        else:
            self.editor_status_var.set("Unsaved transcript edits")
        self.editor_text.edit_modified(False)

    def _current_input_mode(self) -> InputMode:
        return "file" if self.input_mode_var.get() == "file" else "url"

    def _current_subtitle_format(self) -> SubtitleFormat:
        value = self.subtitle_format_var.get()
        if value == "srt":
            return "srt"
        if value == "vtt":
            return "vtt"
        return "ass"

    def _on_close(self) -> None:
        self._persist_settings()
        if self.active_export_worker and self.active_export_worker.is_alive():
            self._set_inline_message(
                "Wait for the export to finish before closing the app.",
                tone="warning",
            )
            self.status_var.set("Waiting for export")
            return
        if self.active_worker and self.active_worker.is_alive():
            if not self._close_requested:
                self._close_requested = True
                self._cancel_processing()
                self._set_inline_message(
                    "Closing after the active job cancels cleanly.",
                    tone="warning",
                )
                self.status_var.set("Cancelling before close")
                self.progress_caption_var.set("Waiting for the worker thread to exit safely")
            self.root.after(100, self._finish_close_when_idle)
            return
        self.root.destroy()

    def _finish_close_when_idle(self) -> None:
        if not self.root.winfo_exists():
            return
        if self.active_worker and self.active_worker.is_alive():
            self.root.after(100, self._finish_close_when_idle)
            return
        self.root.destroy()


def create_app() -> tk.Tk:
    """Create the Tkinter application root."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    root = tk.Tk()
    VideoTranscriberApp(root)
    return root
