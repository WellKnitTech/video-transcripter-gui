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
QUEUE_PROGRESS = "progress"
QUEUE_RESULT = "result"
QUEUE_ERROR = "error"
PLACEHOLDER_TEXT = {
    "url": "https://example.com/video",
    "file": "/path/to/video.mp4",
    "output": "/path/to/output-folder",
}

PALETTE = {
    "bg": "#F5F0E7",
    "surface": "#FCF8F2",
    "surface_alt": "#EFE4D4",
    "border": "#D7C5AE",
    "accent": "#A56A43",
    "accent_soft": "#E8D2BB",
    "text": "#3A3128",
    "muted": "#756656",
    "success": "#5C7A5B",
    "warning": "#B4784A",
    "danger": "#A34A40",
    "editor_bg": "#FFFDF8",
}

QueuePayload = tuple[str, str, float | None] | JobResult | Exception


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
        self.cancellation_token: CancellationToken | None = None
        self.settings = load_settings()
        self._entry_placeholders: dict[ttk.Entry, dict[str, object]] = {}

        self._configure_styles()
        self._init_state_vars()
        self._build_ui()
        self._apply_settings(self.settings)
        self._refresh_input_mode_ui()
        self._reset_result_summary()
        self._bind_shortcuts()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_events)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=PALETTE["bg"])
        style.configure("Card.TFrame", background=PALETTE["surface"])
        style.configure("AccentCard.TFrame", background=PALETTE["surface_alt"])
        style.configure(
            "HeroTitle.TLabel",
            background=PALETTE["bg"],
            foreground=PALETTE["text"],
            font=("TkDefaultFont", 24, "bold"),
        )
        style.configure(
            "HeroBody.TLabel",
            background=PALETTE["bg"],
            foreground=PALETTE["muted"],
            font=("TkDefaultFont", 11),
        )
        style.configure(
            "Section.TLabel",
            background=PALETTE["surface"],
            foreground=PALETTE["text"],
            font=("TkDefaultFont", 12, "bold"),
        )
        style.configure(
            "Field.TLabel",
            background=PALETTE["surface"],
            foreground=PALETTE["text"],
            font=("TkDefaultFont", 10, "bold"),
        )
        style.configure(
            "Muted.TLabel",
            background=PALETTE["surface"],
            foreground=PALETTE["muted"],
            font=("TkDefaultFont", 10),
        )
        style.configure(
            "Status.TLabel",
            background=PALETTE["surface_alt"],
            foreground=PALETTE["accent"],
            font=("TkDefaultFont", 10, "bold"),
            padding=(14, 8),
        )
        style.configure(
            "SummaryTitle.TLabel",
            background=PALETTE["surface_alt"],
            foreground=PALETTE["text"],
            font=("TkDefaultFont", 15, "bold"),
        )
        style.configure(
            "SummaryBody.TLabel",
            background=PALETTE["surface_alt"],
            foreground=PALETTE["muted"],
            font=("TkDefaultFont", 10),
        )
        style.configure(
            "Primary.TButton",
            background=PALETTE["accent"],
            foreground="#FFF8F0",
            borderwidth=0,
            focusthickness=0,
            padding=(16, 10),
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#935B37"), ("disabled", PALETTE["border"])],
            foreground=[("disabled", "#F4EDE3")],
        )
        style.configure(
            "Secondary.TButton",
            background=PALETTE["surface"],
            foreground=PALETTE["text"],
            padding=(14, 9),
            bordercolor=PALETTE["border"],
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", PALETTE["accent_soft"]), ("disabled", PALETTE["surface"])],
            foreground=[("disabled", PALETTE["muted"])],
        )
        style.configure(
            "Warm.TRadiobutton",
            background=PALETTE["surface"],
            foreground=PALETTE["text"],
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map(
            "Warm.TRadiobutton",
            background=[("active", PALETTE["surface"])],
            foreground=[("selected", PALETTE["accent"])],
        )
        style.configure(
            "Warm.TCheckbutton",
            background=PALETTE["surface"],
            foreground=PALETTE["text"],
        )
        style.configure(
            "Warm.Horizontal.TProgressbar",
            troughcolor=PALETTE["accent_soft"],
            background=PALETTE["accent"],
            bordercolor=PALETTE["accent_soft"],
            lightcolor=PALETTE["accent"],
            darkcolor=PALETTE["accent"],
        )
        style.configure(
            "Warm.TNotebook",
            background=PALETTE["surface"],
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "Warm.TNotebook.Tab",
            background=PALETTE["accent_soft"],
            foreground=PALETTE["muted"],
            padding=(14, 8),
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map(
            "Warm.TNotebook.Tab",
            background=[("selected", PALETTE["surface"]), ("active", "#F4E7D8")],
            foreground=[("selected", PALETTE["text"])],
        )

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
        self.num_speakers_var = tk.StringVar(value="2")
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

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, style="App.TFrame", padding=20)
        shell.pack(fill=tk.BOTH, expand=True)
        shell.columnconfigure(0, weight=11)
        shell.columnconfigure(1, weight=14)
        shell.rowconfigure(1, weight=1)

        self._build_header(shell)
        self._build_left_column(shell)
        self._build_right_column(shell)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        header.columnconfigure(0, weight=1)

        left = ttk.Frame(header, style="App.TFrame")
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="Video Transcriber", style="HeroTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            left,
            textvariable=self.hero_hint_var,
            style="HeroBody.TLabel",
            wraplength=720,
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        ttk.Label(
            left,
            text="Shortcuts: Ctrl+Enter run   Esc cancel   Ctrl+Shift+O output   Ctrl+E export",
            style="HeroBody.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

        status_box = tk.Frame(
            header,
            bg=PALETTE["surface_alt"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            bd=0,
            padx=10,
            pady=8,
        )
        status_box.grid(row=0, column=1, sticky="e")
        ttk.Label(status_box, text="Current status", style="SummaryBody.TLabel").pack(anchor="w")
        ttk.Label(status_box, textvariable=self.status_var, style="Status.TLabel").pack(
            anchor="w",
            pady=(4, 0),
        )

    def _build_left_column(self, parent: ttk.Frame) -> None:
        card = self._card(parent, row=1, column=0, sticky="nsew", padx=(0, 14))
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="Job setup", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            card,
            text=(
                "Choose your source, tune the output, and start a job when "
                "everything looks right."
            ),
            style="Muted.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))

        ttk.Label(card, text="[Source] Input mode", style="Field.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w"
        )
        mode_frame = ttk.Frame(card, style="Card.TFrame")
        mode_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Radiobutton(
            mode_frame,
            text="Download from URL",
            variable=self.input_mode_var,
            value="url",
            command=self._refresh_input_mode_ui,
            style="Warm.TRadiobutton",
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_frame,
            text="Use local file",
            variable=self.input_mode_var,
            value="file",
            command=self._refresh_input_mode_ui,
            style="Warm.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(18, 0))
        ttk.Label(card, textvariable=self.mode_hint_var, style="Muted.TLabel", wraplength=360).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(6, 12)
        )

        ttk.Label(card, text="[Source] Video source", style="Field.TLabel").grid(
            row=5, column=0, columnspan=2, sticky="w"
        )
        self.input_entry = ttk.Entry(card, textvariable=self.input_var)
        self.input_entry.grid(row=6, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
        self._install_placeholder(self.input_entry, self.input_var, PLACEHOLDER_TEXT["url"])
        self.input_browse_button = ttk.Button(
            card,
            text="Browse  [Ctrl+L]",
            command=self._browse_input,
            style="Secondary.TButton",
        )
        self.input_browse_button.grid(row=6, column=1, sticky="ew", pady=(6, 0))

        ttk.Label(card, text="[Output] Output directory", style="Field.TLabel").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(14, 0)
        )
        self.output_entry = ttk.Entry(card, textvariable=self.output_dir_var)
        self.output_entry.grid(row=8, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
        self._install_placeholder(
            self.output_entry,
            self.output_dir_var,
            PLACEHOLDER_TEXT["output"],
        )
        self.output_browse_button = ttk.Button(
            card,
            text="Choose  [Ctrl+Shift+O]",
            command=self._browse_output_dir,
            style="Secondary.TButton",
        )
        self.output_browse_button.grid(row=8, column=1, sticky="ew", pady=(6, 0))

        ttk.Label(card, text="Transcription options", style="Section.TLabel").grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(18, 0)
        )
        ttk.Label(card, text="Whisper model", style="Field.TLabel").grid(
            row=10, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Label(card, text="Subtitle format", style="Field.TLabel").grid(
            row=10, column=1, sticky="w", pady=(10, 0)
        )
        self.model_name_combo = ttk.Combobox(
            card,
            textvariable=self.model_name_var,
            values=MODEL_OPTIONS,
            state="readonly",
        )
        self.model_name_combo.grid(row=11, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
        self.subtitle_format_combo = ttk.Combobox(
            card,
            textvariable=self.subtitle_format_var,
            values=SUBTITLE_FORMAT_OPTIONS,
            state="readonly",
        )
        self.subtitle_format_combo.grid(row=11, column=1, sticky="ew", pady=(6, 0))

        ttk.Label(card, text="Subtitle delay (seconds)", style="Field.TLabel").grid(
            row=12, column=0, sticky="w", pady=(12, 0)
        )
        ttk.Label(card, text="Speakers", style="Field.TLabel").grid(
            row=12, column=1, sticky="w", pady=(12, 0)
        )
        self.delay_entry = ttk.Entry(card, textvariable=self.delay_var)
        self.delay_entry.grid(row=13, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
        self.num_speakers_entry = ttk.Entry(card, textvariable=self.num_speakers_var)
        self.num_speakers_entry.grid(row=13, column=1, sticky="ew", pady=(6, 0))

        toggle_box = ttk.Frame(card, style="Card.TFrame")
        toggle_box.grid(row=14, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ttk.Checkbutton(
            toggle_box,
            text="Enable speaker diarization",
            variable=self.enable_diarization_var,
            style="Warm.TCheckbutton",
        ).pack(anchor="w")
        ttk.Checkbutton(
            toggle_box,
            text="Save transcript as a text file",
            variable=self.save_text_var,
            style="Warm.TCheckbutton",
        ).pack(anchor="w", pady=(8, 0))
        ttk.Checkbutton(
            toggle_box,
            text="Embed subtitles into video",
            variable=self.embed_subtitles_var,
            style="Warm.TCheckbutton",
        ).pack(anchor="w", pady=(8, 0))

        self.inline_message_label = tk.Label(
            card,
            textvariable=self.inline_message_var,
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
            justify=tk.LEFT,
            wraplength=360,
            anchor="w",
        )
        self.inline_message_label.grid(row=15, column=0, columnspan=2, sticky="ew", pady=(14, 0))

        action_frame = ttk.Frame(card, style="Card.TFrame")
        action_frame.grid(row=16, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        self.process_button = ttk.Button(
            action_frame,
            text="Start Transcription  [Ctrl+Enter]",
            command=self._start_processing,
            style="Primary.TButton",
        )
        self.process_button.pack(side=tk.LEFT)
        self.cancel_button = ttk.Button(
            action_frame,
            text="Cancel  [Esc]",
            command=self._cancel_processing,
            style="Secondary.TButton",
            state=tk.DISABLED,
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(10, 0))
        self.open_output_button = ttk.Button(
            action_frame,
            text="Open Output Folder",
            command=self._open_output_dir,
            style="Secondary.TButton",
            state=tk.DISABLED,
        )
        self.open_output_button.pack(side=tk.LEFT, padx=(10, 0))

    def _build_right_column(self, parent: ttk.Frame) -> None:
        right = ttk.Frame(parent, style="App.TFrame")
        right.grid(row=1, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        summary = self._accent_card(right, row=0, column=0, sticky="ew", pady=(0, 14))
        summary.columnconfigure(0, weight=1)
        ttk.Label(summary, textvariable=self.summary_title_var, style="SummaryTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            summary,
            textvariable=self.summary_body_var,
            style="SummaryBody.TLabel",
            wraplength=560,
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky="w", pady=(6, 10))
        ttk.Label(summary, textvariable=self.progress_caption_var, style="SummaryBody.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        self.progress_bar = ttk.Progressbar(
            summary,
            orient=tk.HORIZONTAL,
            mode="determinate",
            maximum=100,
            style="Warm.Horizontal.TProgressbar",
        )
        self.progress_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        workspace = self._card(right, row=1, column=0, sticky="nsew")
        workspace.rowconfigure(1, weight=1)
        workspace.columnconfigure(0, weight=1)
        ttk.Label(workspace, text="Workspace", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            workspace,
            text="Follow the job, review logs, and refine the transcript in one place.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="e")

        self.workspace_notebook = ttk.Notebook(workspace, style="Warm.TNotebook")
        self.workspace_notebook.grid(row=1, column=0, sticky="nsew", pady=(14, 0))

        self.overview_tab = ttk.Frame(self.workspace_notebook, style="Card.TFrame")
        self.logs_tab = ttk.Frame(self.workspace_notebook, style="Card.TFrame")
        self.transcript_tab = ttk.Frame(self.workspace_notebook, style="Card.TFrame")
        self.workspace_notebook.add(self.overview_tab, text="Overview")
        self.workspace_notebook.add(self.logs_tab, text="Logs")
        self.workspace_notebook.add(self.transcript_tab, text="Transcript")

        self._build_overview_tab()
        self._build_logs_tab()
        self._build_transcript_tab()

    def _build_overview_tab(self) -> None:
        self.overview_tab.columnconfigure(0, weight=1)

        self.result_summary_label = ttk.Label(
            self.overview_tab,
            textvariable=self.summary_body_var,
            style="Muted.TLabel",
            wraplength=560,
            justify=tk.LEFT,
        )
        self.result_summary_label.grid(row=0, column=0, sticky="ew", pady=(10, 12))

        quick_actions = ttk.Frame(self.overview_tab, style="Card.TFrame")
        quick_actions.grid(row=1, column=0, sticky="w")
        ttk.Button(
            quick_actions,
            text="Open Output Folder  [Ctrl+O]",
            command=self._open_output_dir,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT)
        ttk.Button(
            quick_actions,
            text="Focus Transcript Editor",
            command=lambda: self.workspace_notebook.select(self.transcript_tab),
            style="Secondary.TButton",
        ).pack(side=tk.LEFT, padx=(10, 0))

    def _build_logs_tab(self) -> None:
        self.logs_tab.columnconfigure(0, weight=1)
        self.logs_tab.rowconfigure(0, weight=1)
        self.log_text = scrolledtext.ScrolledText(
            self.logs_tab,
            height=18,
            wrap=tk.WORD,
            relief=tk.FLAT,
            bd=0,
            bg=PALETTE["editor_bg"],
            fg=PALETTE["text"],
            insertbackground=PALETTE["text"],
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
            padx=14,
            pady=14,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew", pady=(10, 0))

    def _build_transcript_tab(self) -> None:
        self.transcript_tab.columnconfigure(0, weight=1)
        self.transcript_tab.rowconfigure(1, weight=1)

        header = ttk.Frame(self.transcript_tab, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(10, 8))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, textvariable=self.editor_status_var, style="Muted.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        actions = ttk.Frame(header, style="Card.TFrame")
        actions.grid(row=0, column=1, sticky="e")
        ttk.Combobox(
            actions,
            textvariable=self.export_format_var,
            values=["txt", "ass", "srt", "vtt"],
            state="readonly",
            width=8,
        ).pack(side=tk.LEFT)
        ttk.Button(
            actions,
            text="Reset",
            command=self._reset_transcript_editor,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(
            actions,
            text="Export Edited Transcript  [Ctrl+E]",
            command=self._export_edited_transcript,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.editor_text = scrolledtext.ScrolledText(
            self.transcript_tab,
            height=20,
            wrap=tk.WORD,
            relief=tk.FLAT,
            bd=0,
            bg=PALETTE["editor_bg"],
            fg=PALETTE["text"],
            insertbackground=PALETTE["text"],
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
            padx=16,
            pady=16,
        )
        self.editor_text.grid(row=1, column=0, sticky="nsew")
        self.editor_text.bind("<<Modified>>", self._handle_editor_modified)

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
        self._refresh_placeholders()

    def _card(
        self,
        parent: tk.Misc,
        *,
        row: int,
        column: int,
        sticky: str,
        padx: tuple[int, int] | int = 0,
        pady: tuple[int, int] | int = 0,
    ) -> ttk.Frame:
        frame = tk.Frame(
            parent,
            bg=PALETTE["surface"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            bd=0,
            padx=18,
            pady=18,
        )
        frame.grid(row=row, column=column, sticky=sticky, padx=padx, pady=pady)
        wrapper = ttk.Frame(frame, style="Card.TFrame")
        wrapper.pack(fill=tk.BOTH, expand=True)
        return wrapper

    def _accent_card(
        self,
        parent: tk.Misc,
        *,
        row: int,
        column: int,
        sticky: str,
        padx: tuple[int, int] | int = 0,
        pady: tuple[int, int] | int = 0,
    ) -> ttk.Frame:
        frame = tk.Frame(
            parent,
            bg=PALETTE["surface_alt"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            bd=0,
            padx=18,
            pady=18,
        )
        frame.grid(row=row, column=column, sticky=sticky, padx=padx, pady=pady)
        wrapper = ttk.Frame(frame, style="AccentCard.TFrame")
        wrapper.pack(fill=tk.BOTH, expand=True)
        return wrapper

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
                    self.editor_status_var.set(
                        "Loaded generated transcript. Make edits and export when ready."
                    )
                    self.workspace_notebook.select(self.transcript_tab)
                elif event_type == QUEUE_ERROR and isinstance(payload, Exception):
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
                    else:
                        self.status_var.set("Failed")
                        self.progress_caption_var.set("Something went wrong during processing")
                        message = str(payload)
                        self._append_log(f"Error: {message}")
                        self._set_inline_message(message, tone="danger")
                        messagebox.showerror("Processing Error", message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_events)

    def _friendly_status(self, message: str) -> str:
        lowered = message.lower()
        if "download" in lowered:
            return "Downloading"
        if "whisper model" in lowered:
            return "Loading model"
        if "transcription" in lowered or "transcrib" in lowered:
            return "Transcribing"
        if "diarization" in lowered:
            return "Diarizing"
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
            self.num_speakers_entry,
        ]:
            widget.configure(state=field_state)
        for widget in [self.model_name_combo, self.subtitle_format_combo]:
            widget.configure(state=combo_state)
        input_browse_state = tk.DISABLED
        if not is_running and self._current_input_mode() == "file":
            input_browse_state = tk.NORMAL
        self.input_browse_button.configure(state=input_browse_state)
        self.output_browse_button.configure(state=field_state)

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

        try:
            segments = parse_editable_transcript(self.editor_text.get("1.0", tk.END))
        except ValueError as exc:
            self._set_inline_message(str(exc), tone="danger")
            self.workspace_notebook.select(self.transcript_tab)
            return

        export_format = self.export_format_var.get()
        base_name = self.current_result.video_file.stem + "_edited"
        output_dir = Path(self.output_dir_var.get()).expanduser()
        speaker_count = max((segment.speaker or 0) for segment in segments) + 1 if segments else 1

        if export_format == "txt":
            export_path = output_dir / f"{base_name}.txt"
            write_text_transcript(
                segments,
                export_path,
                self.current_result.video_file,
                None,
                any(segment.speaker is not None for segment in segments),
                speaker_count,
            )
        else:
            export_path = output_dir / f"{base_name}.{export_format}"
            write_subtitle_file(
                segments,
                export_path,
                cast(SubtitleFormat, export_format),
                speaker_count,
            )

        self._append_log(f"Edited transcript exported: {export_path}")
        self.editor_status_var.set(f"Last export: {export_path.name}")
        self._set_inline_message(f"Saved edited transcript to {export_path}", tone="success")

    def _reset_transcript_editor(self) -> None:
        if self.current_result is None:
            self._set_editor_contents("")
            self.editor_status_var.set("Transcript editor is empty")
            return
        self._set_editor_contents(render_editable_transcript(self.current_result.segments))
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
            num_speakers=int(self.num_speakers_var.get()),
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
            num_speakers=self.num_speakers_var.get(),
            model_name=self.model_name_var.get(),
            subtitle_format=self._current_subtitle_format(),
        )
        save_settings(settings)

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
        self.root.destroy()


def create_app() -> tk.Tk:
    """Create the Tkinter application root."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    root = tk.Tk()
    VideoTranscriberApp(root)
    return root
