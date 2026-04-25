"""Passive Tkinter view builders for the GUI shell."""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk
from typing import Any

from .gui_theme import (
    MODEL_OPTIONS,
    PALETTE,
    PLACEHOLDER_TEXT,
    SUBTITLE_FORMAT_OPTIONS,
)


def build_ui(app: Any) -> None:
    """Construct the GUI shell and child views."""
    shell = ttk.Frame(app.root, style="App.TFrame", padding=20)
    shell.pack(fill=tk.BOTH, expand=True)
    shell.columnconfigure(0, weight=11)
    shell.columnconfigure(1, weight=14)
    shell.rowconfigure(1, weight=1)

    _build_header(app, shell)
    _build_left_column(app, shell)
    _build_right_column(app, shell)


def create_card(
    parent: tk.Misc,
    *,
    row: int,
    column: int,
    sticky: str,
    padx: tuple[int, int] | int = 0,
    pady: tuple[int, int] | int = 0,
) -> ttk.Frame:
    """Create a standard framed content card."""
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


def create_accent_card(
    parent: tk.Misc,
    *,
    row: int,
    column: int,
    sticky: str,
    padx: tuple[int, int] | int = 0,
    pady: tuple[int, int] | int = 0,
) -> ttk.Frame:
    """Create an accent framed content card."""
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


def _build_header(app: Any, parent: ttk.Frame) -> None:
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
        textvariable=app.hero_hint_var,
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
    ttk.Label(status_box, textvariable=app.status_var, style="Status.TLabel").pack(
        anchor="w",
        pady=(4, 0),
    )


def _build_left_column(app: Any, parent: ttk.Frame) -> None:
    card = create_card(parent, row=1, column=0, sticky="nsew", padx=(0, 14))
    card.columnconfigure(0, weight=1)
    card.columnconfigure(1, weight=1)

    ttk.Label(card, text="Job setup", style="Section.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(
        card,
        text=("Choose your source, tune the output, and start a job when everything looks right."),
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
        variable=app.input_mode_var,
        value="url",
        command=app._refresh_input_mode_ui,
        style="Warm.TRadiobutton",
    ).pack(side=tk.LEFT)
    ttk.Radiobutton(
        mode_frame,
        text="Use local file",
        variable=app.input_mode_var,
        value="file",
        command=app._refresh_input_mode_ui,
        style="Warm.TRadiobutton",
    ).pack(side=tk.LEFT, padx=(18, 0))
    ttk.Label(card, textvariable=app.mode_hint_var, style="Muted.TLabel", wraplength=360).grid(
        row=4, column=0, columnspan=2, sticky="w", pady=(6, 12)
    )

    ttk.Label(card, text="[Source] Video source", style="Field.TLabel").grid(
        row=5, column=0, columnspan=2, sticky="w"
    )
    app.input_entry = ttk.Entry(card, textvariable=app.input_var)
    app.input_entry.grid(row=6, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
    app._install_placeholder(app.input_entry, app.input_var, PLACEHOLDER_TEXT["url"])
    app.input_browse_button = ttk.Button(
        card,
        text="Browse  [Ctrl+L]",
        command=app._browse_input,
        style="Secondary.TButton",
    )
    app.input_browse_button.grid(row=6, column=1, sticky="ew", pady=(6, 0))

    ttk.Label(card, text="[Output] Output directory", style="Field.TLabel").grid(
        row=7, column=0, columnspan=2, sticky="w", pady=(14, 0)
    )
    app.output_entry = ttk.Entry(card, textvariable=app.output_dir_var)
    app.output_entry.grid(row=8, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
    app._install_placeholder(app.output_entry, app.output_dir_var, PLACEHOLDER_TEXT["output"])
    app.output_browse_button = ttk.Button(
        card,
        text="Choose  [Ctrl+Shift+O]",
        command=app._browse_output_dir,
        style="Secondary.TButton",
    )
    app.output_browse_button.grid(row=8, column=1, sticky="ew", pady=(6, 0))

    ttk.Label(card, text="Transcription options", style="Section.TLabel").grid(
        row=9, column=0, columnspan=2, sticky="w", pady=(18, 0)
    )
    ttk.Label(card, text="Whisper model", style="Field.TLabel").grid(
        row=10, column=0, sticky="w", pady=(10, 0)
    )
    ttk.Label(card, text="Subtitle format", style="Field.TLabel").grid(
        row=10, column=1, sticky="w", pady=(10, 0)
    )
    app.model_name_combo = ttk.Combobox(
        card,
        textvariable=app.model_name_var,
        values=MODEL_OPTIONS,
        state="readonly",
    )
    app.model_name_combo.grid(row=11, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
    app.subtitle_format_combo = ttk.Combobox(
        card,
        textvariable=app.subtitle_format_var,
        values=SUBTITLE_FORMAT_OPTIONS,
        state="readonly",
    )
    app.subtitle_format_combo.grid(row=11, column=1, sticky="ew", pady=(6, 0))

    ttk.Label(card, text="Subtitle delay (seconds)", style="Field.TLabel").grid(
        row=12, column=0, sticky="w", pady=(12, 0)
    )
    ttk.Label(card, text="Speaker count", style="Field.TLabel").grid(
        row=12, column=1, sticky="w", pady=(12, 0)
    )
    app.delay_entry = ttk.Entry(card, textvariable=app.delay_var)
    app.delay_entry.grid(row=13, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
    app.speaker_mode_combo = ttk.Combobox(
        card,
        textvariable=app.speaker_count_mode_var,
        values=["auto", "exact", "range"],
        state="readonly",
    )
    app.speaker_mode_combo.grid(row=13, column=1, sticky="ew", pady=(6, 0))
    app.speaker_mode_combo.bind(
        "<<ComboboxSelected>>", lambda _event: app._refresh_speaker_mode_ui()
    )

    toggle_box = ttk.Frame(card, style="Card.TFrame")
    toggle_box.grid(row=14, column=0, columnspan=2, sticky="ew", pady=(16, 0))
    toggle_box.columnconfigure(1, weight=1)
    toggle_box.columnconfigure(3, weight=1)
    ttk.Checkbutton(
        toggle_box,
        text="Enable speaker labeling",
        variable=app.enable_diarization_var,
        command=app._refresh_speaker_mode_ui,
        style="Warm.TCheckbutton",
    ).grid(row=0, column=0, columnspan=4, sticky="w")
    ttk.Label(toggle_box, text="Exact speakers", style="Muted.TLabel").grid(
        row=1, column=0, sticky="w", pady=(10, 0)
    )
    app.exact_speakers_entry = ttk.Entry(toggle_box, textvariable=app.exact_speakers_var)
    app.exact_speakers_entry.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
    ttk.Label(toggle_box, text="Minimum speakers", style="Muted.TLabel").grid(
        row=1, column=1, sticky="w", pady=(10, 0)
    )
    app.min_speakers_entry = ttk.Entry(toggle_box, textvariable=app.min_speakers_var)
    app.min_speakers_entry.grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(4, 0))
    ttk.Label(toggle_box, text="Maximum speakers", style="Muted.TLabel").grid(
        row=1, column=2, sticky="w", pady=(10, 0)
    )
    app.max_speakers_entry = ttk.Entry(toggle_box, textvariable=app.max_speakers_var)
    app.max_speakers_entry.grid(row=2, column=2, sticky="ew", padx=(0, 8), pady=(4, 0))
    ttk.Label(toggle_box, text="Audio cleanup", style="Muted.TLabel").grid(
        row=1, column=3, sticky="w", pady=(10, 0)
    )
    app.audio_cleanup_combo = ttk.Combobox(
        toggle_box,
        textvariable=app.audio_cleanup_preset_var,
        values=["off", "light", "meeting"],
        state="readonly",
    )
    app.audio_cleanup_combo.grid(row=2, column=3, sticky="ew", pady=(4, 0))
    ttk.Checkbutton(
        toggle_box,
        text="Save transcript as a text file",
        variable=app.save_text_var,
        style="Warm.TCheckbutton",
    ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))
    ttk.Checkbutton(
        toggle_box,
        text="Embed subtitles into video",
        variable=app.embed_subtitles_var,
        style="Warm.TCheckbutton",
    ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(8, 0))

    app.inline_message_label = tk.Label(
        card,
        textvariable=app.inline_message_var,
        bg=PALETTE["surface"],
        fg=PALETTE["muted"],
        justify=tk.LEFT,
        wraplength=360,
        anchor="w",
    )
    app.inline_message_label.grid(row=15, column=0, columnspan=2, sticky="ew", pady=(14, 0))

    action_frame = ttk.Frame(card, style="Card.TFrame")
    action_frame.grid(row=16, column=0, columnspan=2, sticky="ew", pady=(18, 0))
    app.process_button = ttk.Button(
        action_frame,
        text="Start Transcription  [Ctrl+Enter]",
        command=app._start_processing,
        style="Primary.TButton",
    )
    app.process_button.pack(side=tk.LEFT)
    app.cancel_button = ttk.Button(
        action_frame,
        text="Cancel  [Esc]",
        command=app._cancel_processing,
        style="Secondary.TButton",
        state=tk.DISABLED,
    )
    app.cancel_button.pack(side=tk.LEFT, padx=(10, 0))
    app.open_output_button = ttk.Button(
        action_frame,
        text="Open Output Folder",
        command=app._open_output_dir,
        style="Secondary.TButton",
        state=tk.DISABLED,
    )
    app.open_output_button.pack(side=tk.LEFT, padx=(10, 0))


def _build_right_column(app: Any, parent: ttk.Frame) -> None:
    right = ttk.Frame(parent, style="App.TFrame")
    right.grid(row=1, column=1, sticky="nsew")
    right.rowconfigure(1, weight=1)
    right.columnconfigure(0, weight=1)

    summary = create_accent_card(right, row=0, column=0, sticky="ew", pady=(0, 14))
    summary.columnconfigure(0, weight=1)
    ttk.Label(summary, textvariable=app.summary_title_var, style="SummaryTitle.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    ttk.Label(
        summary,
        textvariable=app.summary_body_var,
        style="SummaryBody.TLabel",
        wraplength=560,
        justify=tk.LEFT,
    ).grid(row=1, column=0, sticky="w", pady=(6, 10))
    ttk.Label(summary, textvariable=app.progress_caption_var, style="SummaryBody.TLabel").grid(
        row=2, column=0, sticky="w"
    )
    app.progress_bar = ttk.Progressbar(
        summary,
        orient=tk.HORIZONTAL,
        mode="determinate",
        maximum=100,
        style="Warm.Horizontal.TProgressbar",
    )
    app.progress_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))

    workspace = create_card(right, row=1, column=0, sticky="nsew")
    workspace.rowconfigure(1, weight=1)
    workspace.columnconfigure(0, weight=1)
    ttk.Label(workspace, text="Workspace", style="Section.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(
        workspace,
        text="Follow the job, review logs, and refine the transcript in one place.",
        style="Muted.TLabel",
    ).grid(row=0, column=0, sticky="e")

    app.workspace_notebook = ttk.Notebook(workspace, style="Warm.TNotebook")
    app.workspace_notebook.grid(row=1, column=0, sticky="nsew", pady=(14, 0))

    app.overview_tab = ttk.Frame(app.workspace_notebook, style="Card.TFrame")
    app.logs_tab = ttk.Frame(app.workspace_notebook, style="Card.TFrame")
    app.transcript_tab = ttk.Frame(app.workspace_notebook, style="Card.TFrame")
    app.workspace_notebook.add(app.overview_tab, text="Overview")
    app.workspace_notebook.add(app.logs_tab, text="Logs")
    app.workspace_notebook.add(app.transcript_tab, text="Transcript")

    _build_overview_tab(app)
    _build_logs_tab(app)
    _build_transcript_tab(app)


def _build_overview_tab(app: Any) -> None:
    app.overview_tab.columnconfigure(0, weight=1)

    app.result_summary_label = ttk.Label(
        app.overview_tab,
        textvariable=app.summary_body_var,
        style="Muted.TLabel",
        wraplength=560,
        justify=tk.LEFT,
    )
    app.result_summary_label.grid(row=0, column=0, sticky="ew", pady=(10, 12))

    quick_actions = ttk.Frame(app.overview_tab, style="Card.TFrame")
    quick_actions.grid(row=1, column=0, sticky="w")
    ttk.Button(
        quick_actions,
        text="Open Output Folder  [Ctrl+O]",
        command=app._open_output_dir,
        style="Secondary.TButton",
    ).pack(side=tk.LEFT)
    ttk.Button(
        quick_actions,
        text="Focus Transcript Editor",
        command=lambda: app.workspace_notebook.select(app.transcript_tab),
        style="Secondary.TButton",
    ).pack(side=tk.LEFT, padx=(10, 0))


def _build_logs_tab(app: Any) -> None:
    app.logs_tab.columnconfigure(0, weight=1)
    app.logs_tab.rowconfigure(0, weight=1)
    app.log_text = scrolledtext.ScrolledText(
        app.logs_tab,
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
    app.log_text.grid(row=0, column=0, sticky="nsew", pady=(10, 0))


def _build_transcript_tab(app: Any) -> None:
    app.transcript_tab.columnconfigure(0, weight=1)
    app.transcript_tab.rowconfigure(2, weight=1)

    header = ttk.Frame(app.transcript_tab, style="Card.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(10, 8))
    header.columnconfigure(0, weight=1)
    ttk.Label(header, textvariable=app.editor_status_var, style="Muted.TLabel").grid(
        row=0, column=0, sticky="w"
    )

    actions = ttk.Frame(header, style="Card.TFrame")
    actions.grid(row=0, column=1, sticky="e")
    app.export_format_combo = ttk.Combobox(
        actions,
        textvariable=app.export_format_var,
        values=["txt", "ass", "srt", "vtt"],
        state="readonly",
        width=8,
    )
    app.export_format_combo.pack(side=tk.LEFT)
    app.reset_editor_button = ttk.Button(
        actions,
        text="Reset",
        command=app._reset_transcript_editor,
        style="Secondary.TButton",
    )
    app.reset_editor_button.pack(side=tk.LEFT, padx=(8, 0))
    app.export_button = ttk.Button(
        actions,
        text="Export Edited Transcript  [Ctrl+E]",
        command=app._export_edited_transcript,
        style="Secondary.TButton",
    )
    app.export_button.pack(side=tk.LEFT, padx=(8, 0))

    rename_box = ttk.Frame(app.transcript_tab, style="Card.TFrame")
    rename_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    rename_box.columnconfigure(0, weight=1)
    ttk.Label(
        rename_box,
        text="Speaker names (one per line: SPEAKER_00 = Chair)",
        style="Muted.TLabel",
    ).grid(row=0, column=0, sticky="w")
    app.speaker_names_text = scrolledtext.ScrolledText(
        rename_box,
        height=4,
        wrap=tk.WORD,
        relief=tk.FLAT,
        bd=0,
        bg=PALETTE["editor_bg"],
        fg=PALETTE["text"],
        insertbackground=PALETTE["text"],
        highlightthickness=1,
        highlightbackground=PALETTE["border"],
        padx=10,
        pady=10,
    )
    app.speaker_names_text.grid(row=1, column=0, sticky="ew", pady=(6, 0))

    app.editor_text = scrolledtext.ScrolledText(
        app.transcript_tab,
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
    app.editor_text.grid(row=2, column=0, sticky="nsew")
    app.editor_text.bind("<<Modified>>", app._handle_editor_modified)
