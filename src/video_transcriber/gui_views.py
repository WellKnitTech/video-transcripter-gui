"""Passive Tkinter view builders for the GUI shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import scrolledtext, ttk

from .gui_theme import (
    DEVICE_OPTIONS,
    LANGUAGE_OPTIONS,
    MODEL_OPTIONS,
    PALETTE,
    SUBTITLE_FORMAT_OPTIONS,
)


@dataclass(slots=True)
class GuiViewState:
    """Tkinter state variables consumed by the passive view layer."""

    hero_hint_var: tk.StringVar
    status_var: tk.StringVar
    input_mode_var: tk.StringVar
    input_var: tk.StringVar
    output_dir_var: tk.StringVar
    delay_var: tk.StringVar
    model_name_var: tk.StringVar
    subtitle_format_var: tk.StringVar
    language_var: tk.StringVar
    device_var: tk.StringVar
    device_hint_var: tk.StringVar
    speaker_count_mode_var: tk.StringVar
    exact_speakers_var: tk.StringVar
    min_speakers_var: tk.StringVar
    max_speakers_var: tk.StringVar
    audio_cleanup_preset_var: tk.StringVar
    enable_diarization_var: tk.BooleanVar
    save_text_var: tk.BooleanVar
    embed_subtitles_var: tk.BooleanVar
    export_format_var: tk.StringVar
    inline_message_var: tk.StringVar
    mode_hint_var: tk.StringVar
    progress_caption_var: tk.StringVar
    summary_title_var: tk.StringVar
    summary_body_var: tk.StringVar
    editor_status_var: tk.StringVar


@dataclass(slots=True)
class GuiViewBindings:
    """Callbacks bound by the passive view layer."""

    refresh_input_mode_ui: Callable[[], None]
    browse_input: Callable[[], None]
    browse_output_dir: Callable[[], None]
    refresh_speaker_mode_ui: Callable[[], None]
    refresh_device_hint: Callable[[], None]
    start_processing: Callable[[], None]
    cancel_processing: Callable[[], None]
    open_output_dir: Callable[[], None]
    focus_transcript_tab: Callable[[], None]
    reset_transcript_editor: Callable[[], None]
    export_edited_transcript: Callable[[], None]
    handle_editor_modified: Callable[[tk.Event[tk.Misc]], None]


@dataclass(slots=True)
class GuiWidgets:
    """Widget handles returned by the passive view layer."""

    input_entry: ttk.Entry
    output_entry: ttk.Entry
    delay_entry: ttk.Entry
    exact_speakers_entry: ttk.Entry
    min_speakers_entry: ttk.Entry
    max_speakers_entry: ttk.Entry
    input_browse_button: ttk.Button
    output_browse_button: ttk.Button
    process_button: ttk.Button
    cancel_button: ttk.Button
    open_output_button: ttk.Button
    model_name_combo: ttk.Combobox
    subtitle_format_combo: ttk.Combobox
    language_combo: ttk.Combobox
    device_combo: ttk.Combobox
    speaker_mode_combo: ttk.Combobox
    audio_cleanup_combo: ttk.Combobox
    export_format_combo: ttk.Combobox
    reset_editor_button: ttk.Button
    export_button: ttk.Button
    inline_message_label: tk.Label
    progress_bar: ttk.Progressbar
    workspace_notebook: ttk.Notebook
    overview_tab: ttk.Frame
    logs_tab: ttk.Frame
    transcript_tab: ttk.Frame
    result_summary_label: ttk.Label
    log_text: tk.Text
    speaker_names_text: tk.Text
    editor_text: tk.Text


@dataclass(slots=True)
class _LeftColumnWidgets:
    input_entry: ttk.Entry
    output_entry: ttk.Entry
    delay_entry: ttk.Entry
    exact_speakers_entry: ttk.Entry
    min_speakers_entry: ttk.Entry
    max_speakers_entry: ttk.Entry
    input_browse_button: ttk.Button
    output_browse_button: ttk.Button
    process_button: ttk.Button
    cancel_button: ttk.Button
    open_output_button: ttk.Button
    model_name_combo: ttk.Combobox
    subtitle_format_combo: ttk.Combobox
    language_combo: ttk.Combobox
    device_combo: ttk.Combobox
    speaker_mode_combo: ttk.Combobox
    audio_cleanup_combo: ttk.Combobox
    inline_message_label: tk.Label


@dataclass(slots=True)
class _OverviewWidgets:
    result_summary_label: ttk.Label


@dataclass(slots=True)
class _TranscriptWidgets:
    speaker_names_text: tk.Text
    editor_text: tk.Text
    export_format_combo: ttk.Combobox
    reset_editor_button: ttk.Button
    export_button: ttk.Button


@dataclass(slots=True)
class _RightColumnWidgets:
    progress_bar: ttk.Progressbar
    workspace_notebook: ttk.Notebook
    overview_tab: ttk.Frame
    logs_tab: ttk.Frame
    transcript_tab: ttk.Frame
    result_summary_label: ttk.Label
    log_text: tk.Text
    speaker_names_text: tk.Text
    editor_text: tk.Text
    export_format_combo: ttk.Combobox
    reset_editor_button: ttk.Button
    export_button: ttk.Button


def build_ui(root: tk.Tk, state: GuiViewState, bindings: GuiViewBindings) -> GuiWidgets:
    """Construct the GUI shell and return widget handles."""
    shell = ttk.Frame(root, style="App.TFrame", padding=20)
    shell.pack(fill=tk.BOTH, expand=True)
    shell.columnconfigure(0, weight=11)
    shell.columnconfigure(1, weight=14)
    shell.rowconfigure(1, weight=1)

    _build_header(shell, state)
    left_widgets = _build_left_column(shell, state, bindings)
    right_widgets = _build_right_column(shell, state, bindings)
    return GuiWidgets(
        input_entry=left_widgets.input_entry,
        output_entry=left_widgets.output_entry,
        delay_entry=left_widgets.delay_entry,
        exact_speakers_entry=left_widgets.exact_speakers_entry,
        min_speakers_entry=left_widgets.min_speakers_entry,
        max_speakers_entry=left_widgets.max_speakers_entry,
        input_browse_button=left_widgets.input_browse_button,
        output_browse_button=left_widgets.output_browse_button,
        process_button=left_widgets.process_button,
        cancel_button=left_widgets.cancel_button,
        open_output_button=left_widgets.open_output_button,
        model_name_combo=left_widgets.model_name_combo,
        subtitle_format_combo=left_widgets.subtitle_format_combo,
        language_combo=left_widgets.language_combo,
        device_combo=left_widgets.device_combo,
        speaker_mode_combo=left_widgets.speaker_mode_combo,
        audio_cleanup_combo=left_widgets.audio_cleanup_combo,
        export_format_combo=right_widgets.export_format_combo,
        reset_editor_button=right_widgets.reset_editor_button,
        export_button=right_widgets.export_button,
        inline_message_label=left_widgets.inline_message_label,
        progress_bar=right_widgets.progress_bar,
        workspace_notebook=right_widgets.workspace_notebook,
        overview_tab=right_widgets.overview_tab,
        logs_tab=right_widgets.logs_tab,
        transcript_tab=right_widgets.transcript_tab,
        result_summary_label=right_widgets.result_summary_label,
        log_text=right_widgets.log_text,
        speaker_names_text=right_widgets.speaker_names_text,
        editor_text=right_widgets.editor_text,
    )


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


def _build_header(parent: ttk.Frame, state: GuiViewState) -> None:
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
        textvariable=state.hero_hint_var,
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
    ttk.Label(status_box, textvariable=state.status_var, style="Status.TLabel").pack(
        anchor="w",
        pady=(4, 0),
    )


def _build_left_column(
    parent: ttk.Frame,
    state: GuiViewState,
    bindings: GuiViewBindings,
) -> _LeftColumnWidgets:
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
        variable=state.input_mode_var,
        value="url",
        command=bindings.refresh_input_mode_ui,
        style="Warm.TRadiobutton",
    ).pack(side=tk.LEFT)
    ttk.Radiobutton(
        mode_frame,
        text="Use local file",
        variable=state.input_mode_var,
        value="file",
        command=bindings.refresh_input_mode_ui,
        style="Warm.TRadiobutton",
    ).pack(side=tk.LEFT, padx=(18, 0))
    ttk.Label(card, textvariable=state.mode_hint_var, style="Muted.TLabel", wraplength=360).grid(
        row=4, column=0, columnspan=2, sticky="w", pady=(6, 12)
    )

    ttk.Label(card, text="[Source] Video source", style="Field.TLabel").grid(
        row=5, column=0, columnspan=2, sticky="w"
    )
    input_entry = ttk.Entry(card, textvariable=state.input_var)
    input_entry.grid(row=6, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
    input_browse_button = ttk.Button(
        card,
        text="Browse  [Ctrl+L]",
        command=bindings.browse_input,
        style="Secondary.TButton",
    )
    input_browse_button.grid(row=6, column=1, sticky="ew", pady=(6, 0))

    ttk.Label(card, text="[Output] Output directory", style="Field.TLabel").grid(
        row=7, column=0, columnspan=2, sticky="w", pady=(14, 0)
    )
    output_entry = ttk.Entry(card, textvariable=state.output_dir_var)
    output_entry.grid(row=8, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
    output_browse_button = ttk.Button(
        card,
        text="Choose  [Ctrl+Shift+O]",
        command=bindings.browse_output_dir,
        style="Secondary.TButton",
    )
    output_browse_button.grid(row=8, column=1, sticky="ew", pady=(6, 0))

    ttk.Label(card, text="Transcription options", style="Section.TLabel").grid(
        row=9, column=0, columnspan=2, sticky="w", pady=(18, 0)
    )
    ttk.Label(card, text="Whisper model", style="Field.TLabel").grid(
        row=10, column=0, sticky="w", pady=(10, 0)
    )
    ttk.Label(card, text="Subtitle format", style="Field.TLabel").grid(
        row=10, column=1, sticky="w", pady=(10, 0)
    )
    model_name_combo = ttk.Combobox(
        card,
        textvariable=state.model_name_var,
        values=MODEL_OPTIONS,
        state="readonly",
    )
    model_name_combo.grid(row=11, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
    subtitle_format_combo = ttk.Combobox(
        card,
        textvariable=state.subtitle_format_var,
        values=SUBTITLE_FORMAT_OPTIONS,
        state="readonly",
    )
    subtitle_format_combo.grid(row=11, column=1, sticky="ew", pady=(6, 0))

    ttk.Label(card, text="Language", style="Field.TLabel").grid(
        row=12, column=0, sticky="w", pady=(12, 0)
    )
    ttk.Label(card, text="Device", style="Field.TLabel").grid(
        row=12, column=1, sticky="w", pady=(12, 0)
    )
    language_combo = ttk.Combobox(
        card,
        textvariable=state.language_var,
        values=LANGUAGE_OPTIONS,
        state="readonly",
    )
    language_combo.grid(row=13, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
    device_combo = ttk.Combobox(
        card,
        textvariable=state.device_var,
        values=DEVICE_OPTIONS,
        state="readonly",
    )
    device_combo.grid(row=13, column=1, sticky="ew", pady=(6, 0))
    device_combo.bind("<<ComboboxSelected>>", lambda _event: bindings.refresh_device_hint())
    ttk.Label(
        card,
        textvariable=state.device_hint_var,
        style="Muted.TLabel",
        wraplength=360,
    ).grid(row=14, column=0, columnspan=2, sticky="w", pady=(6, 0))

    ttk.Label(card, text="Subtitle delay (seconds)", style="Field.TLabel").grid(
        row=15, column=0, sticky="w", pady=(12, 0)
    )
    ttk.Label(card, text="Speaker count", style="Field.TLabel").grid(
        row=15, column=1, sticky="w", pady=(12, 0)
    )
    delay_entry = ttk.Entry(card, textvariable=state.delay_var)
    delay_entry.grid(row=16, column=0, sticky="ew", pady=(6, 0), padx=(0, 8))
    speaker_mode_combo = ttk.Combobox(
        card,
        textvariable=state.speaker_count_mode_var,
        values=["auto", "exact", "range"],
        state="readonly",
    )
    speaker_mode_combo.grid(row=16, column=1, sticky="ew", pady=(6, 0))
    speaker_mode_combo.bind(
        "<<ComboboxSelected>>", lambda _event: bindings.refresh_speaker_mode_ui()
    )

    toggle_box = ttk.Frame(card, style="Card.TFrame")
    toggle_box.grid(row=17, column=0, columnspan=2, sticky="ew", pady=(16, 0))
    toggle_box.columnconfigure(1, weight=1)
    toggle_box.columnconfigure(3, weight=1)
    ttk.Checkbutton(
        toggle_box,
        text="Enable speaker labeling",
        variable=state.enable_diarization_var,
        command=bindings.refresh_speaker_mode_ui,
        style="Warm.TCheckbutton",
    ).grid(row=0, column=0, columnspan=4, sticky="w")
    ttk.Label(toggle_box, text="Exact speakers", style="Muted.TLabel").grid(
        row=1, column=0, sticky="w", pady=(10, 0)
    )
    exact_speakers_entry = ttk.Entry(toggle_box, textvariable=state.exact_speakers_var)
    exact_speakers_entry.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
    ttk.Label(toggle_box, text="Minimum speakers", style="Muted.TLabel").grid(
        row=1, column=1, sticky="w", pady=(10, 0)
    )
    min_speakers_entry = ttk.Entry(toggle_box, textvariable=state.min_speakers_var)
    min_speakers_entry.grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(4, 0))
    ttk.Label(toggle_box, text="Maximum speakers", style="Muted.TLabel").grid(
        row=1, column=2, sticky="w", pady=(10, 0)
    )
    max_speakers_entry = ttk.Entry(toggle_box, textvariable=state.max_speakers_var)
    max_speakers_entry.grid(row=2, column=2, sticky="ew", padx=(0, 8), pady=(4, 0))
    ttk.Label(toggle_box, text="Audio cleanup", style="Muted.TLabel").grid(
        row=1, column=3, sticky="w", pady=(10, 0)
    )
    audio_cleanup_combo = ttk.Combobox(
        toggle_box,
        textvariable=state.audio_cleanup_preset_var,
        values=["off", "light", "meeting"],
        state="readonly",
    )
    audio_cleanup_combo.grid(row=2, column=3, sticky="ew", pady=(4, 0))
    ttk.Checkbutton(
        toggle_box,
        text="Save transcript as a text file",
        variable=state.save_text_var,
        style="Warm.TCheckbutton",
    ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))
    ttk.Checkbutton(
        toggle_box,
        text="Embed subtitles into video",
        variable=state.embed_subtitles_var,
        style="Warm.TCheckbutton",
    ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(8, 0))

    inline_message_label = tk.Label(
        card,
        textvariable=state.inline_message_var,
        bg=PALETTE["surface"],
        fg=PALETTE["muted"],
        justify=tk.LEFT,
        wraplength=360,
        anchor="w",
    )
    inline_message_label.grid(row=18, column=0, columnspan=2, sticky="ew", pady=(14, 0))

    action_frame = ttk.Frame(card, style="Card.TFrame")
    action_frame.grid(row=19, column=0, columnspan=2, sticky="ew", pady=(18, 0))
    process_button = ttk.Button(
        action_frame,
        text="Start Transcription  [Ctrl+Enter]",
        command=bindings.start_processing,
        style="Primary.TButton",
    )
    process_button.pack(side=tk.LEFT)
    cancel_button = ttk.Button(
        action_frame,
        text="Cancel  [Esc]",
        command=bindings.cancel_processing,
        style="Secondary.TButton",
        state=tk.DISABLED,
    )
    cancel_button.pack(side=tk.LEFT, padx=(10, 0))
    open_output_button = ttk.Button(
        action_frame,
        text="Open Output Folder",
        command=bindings.open_output_dir,
        style="Secondary.TButton",
        state=tk.DISABLED,
    )
    open_output_button.pack(side=tk.LEFT, padx=(10, 0))

    return _LeftColumnWidgets(
        input_entry=input_entry,
        output_entry=output_entry,
        delay_entry=delay_entry,
        exact_speakers_entry=exact_speakers_entry,
        min_speakers_entry=min_speakers_entry,
        max_speakers_entry=max_speakers_entry,
        input_browse_button=input_browse_button,
        output_browse_button=output_browse_button,
        process_button=process_button,
        cancel_button=cancel_button,
        open_output_button=open_output_button,
        model_name_combo=model_name_combo,
        subtitle_format_combo=subtitle_format_combo,
        language_combo=language_combo,
        device_combo=device_combo,
        speaker_mode_combo=speaker_mode_combo,
        audio_cleanup_combo=audio_cleanup_combo,
        inline_message_label=inline_message_label,
    )


def _build_right_column(
    parent: ttk.Frame,
    state: GuiViewState,
    bindings: GuiViewBindings,
) -> _RightColumnWidgets:
    right = ttk.Frame(parent, style="App.TFrame")
    right.grid(row=1, column=1, sticky="nsew")
    right.rowconfigure(1, weight=1)
    right.columnconfigure(0, weight=1)

    summary = create_accent_card(right, row=0, column=0, sticky="ew", pady=(0, 14))
    summary.columnconfigure(0, weight=1)
    ttk.Label(summary, textvariable=state.summary_title_var, style="SummaryTitle.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    ttk.Label(
        summary,
        textvariable=state.summary_body_var,
        style="SummaryBody.TLabel",
        wraplength=560,
        justify=tk.LEFT,
    ).grid(row=1, column=0, sticky="w", pady=(6, 10))
    ttk.Label(summary, textvariable=state.progress_caption_var, style="SummaryBody.TLabel").grid(
        row=2, column=0, sticky="w"
    )
    progress_bar = ttk.Progressbar(
        summary,
        orient=tk.HORIZONTAL,
        mode="determinate",
        maximum=100,
        style="Warm.Horizontal.TProgressbar",
    )
    progress_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))

    workspace = create_card(right, row=1, column=0, sticky="nsew")
    workspace.rowconfigure(1, weight=1)
    workspace.columnconfigure(0, weight=1)
    ttk.Label(workspace, text="Workspace", style="Section.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(
        workspace,
        text="Follow the job, review logs, and refine the transcript in one place.",
        style="Muted.TLabel",
    ).grid(row=0, column=0, sticky="e")

    workspace_notebook = ttk.Notebook(workspace, style="Warm.TNotebook")
    workspace_notebook.grid(row=1, column=0, sticky="nsew", pady=(14, 0))

    overview_tab = ttk.Frame(workspace_notebook, style="Card.TFrame")
    logs_tab = ttk.Frame(workspace_notebook, style="Card.TFrame")
    transcript_tab = ttk.Frame(workspace_notebook, style="Card.TFrame")
    workspace_notebook.add(overview_tab, text="Overview")
    workspace_notebook.add(logs_tab, text="Logs")
    workspace_notebook.add(transcript_tab, text="Transcript")

    overview_widgets = _build_overview_tab(overview_tab, state, bindings)
    log_text = _build_logs_tab(logs_tab)
    transcript_widgets = _build_transcript_tab(transcript_tab, state, bindings)
    return _RightColumnWidgets(
        progress_bar=progress_bar,
        workspace_notebook=workspace_notebook,
        overview_tab=overview_tab,
        logs_tab=logs_tab,
        transcript_tab=transcript_tab,
        result_summary_label=overview_widgets.result_summary_label,
        log_text=log_text,
        speaker_names_text=transcript_widgets.speaker_names_text,
        editor_text=transcript_widgets.editor_text,
        export_format_combo=transcript_widgets.export_format_combo,
        reset_editor_button=transcript_widgets.reset_editor_button,
        export_button=transcript_widgets.export_button,
    )


def _build_overview_tab(
    overview_tab: ttk.Frame,
    state: GuiViewState,
    bindings: GuiViewBindings,
) -> _OverviewWidgets:
    overview_tab.columnconfigure(0, weight=1)

    result_summary_label = ttk.Label(
        overview_tab,
        textvariable=state.summary_body_var,
        style="Muted.TLabel",
        wraplength=560,
        justify=tk.LEFT,
    )
    result_summary_label.grid(row=0, column=0, sticky="ew", pady=(10, 12))

    quick_actions = ttk.Frame(overview_tab, style="Card.TFrame")
    quick_actions.grid(row=1, column=0, sticky="w")
    ttk.Button(
        quick_actions,
        text="Open Output Folder  [Ctrl+O]",
        command=bindings.open_output_dir,
        style="Secondary.TButton",
    ).pack(side=tk.LEFT)
    ttk.Button(
        quick_actions,
        text="Focus Transcript Editor",
        command=bindings.focus_transcript_tab,
        style="Secondary.TButton",
    ).pack(side=tk.LEFT, padx=(10, 0))
    return _OverviewWidgets(result_summary_label=result_summary_label)


def _build_logs_tab(logs_tab: ttk.Frame) -> tk.Text:
    logs_tab.columnconfigure(0, weight=1)
    logs_tab.rowconfigure(0, weight=1)
    log_text = scrolledtext.ScrolledText(
        logs_tab,
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
    log_text.grid(row=0, column=0, sticky="nsew", pady=(10, 0))
    return log_text


def _build_transcript_tab(
    transcript_tab: ttk.Frame,
    state: GuiViewState,
    bindings: GuiViewBindings,
) -> _TranscriptWidgets:
    transcript_tab.columnconfigure(0, weight=1)
    transcript_tab.rowconfigure(2, weight=1)

    header = ttk.Frame(transcript_tab, style="Card.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(10, 8))
    header.columnconfigure(0, weight=1)
    ttk.Label(header, textvariable=state.editor_status_var, style="Muted.TLabel").grid(
        row=0, column=0, sticky="w"
    )

    actions = ttk.Frame(header, style="Card.TFrame")
    actions.grid(row=0, column=1, sticky="e")
    export_format_combo = ttk.Combobox(
        actions,
        textvariable=state.export_format_var,
        values=["txt", "ass", "srt", "vtt"],
        state="readonly",
        width=8,
    )
    export_format_combo.pack(side=tk.LEFT)
    reset_editor_button = ttk.Button(
        actions,
        text="Reset",
        command=bindings.reset_transcript_editor,
        style="Secondary.TButton",
    )
    reset_editor_button.pack(side=tk.LEFT, padx=(8, 0))
    export_button = ttk.Button(
        actions,
        text="Export Edited Transcript  [Ctrl+E]",
        command=bindings.export_edited_transcript,
        style="Secondary.TButton",
    )
    export_button.pack(side=tk.LEFT, padx=(8, 0))

    rename_box = ttk.Frame(transcript_tab, style="Card.TFrame")
    rename_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    rename_box.columnconfigure(0, weight=1)
    ttk.Label(
        rename_box,
        text="Speaker names (one per line: SPEAKER_00 = Chair)",
        style="Muted.TLabel",
    ).grid(row=0, column=0, sticky="w")
    speaker_names_text = scrolledtext.ScrolledText(
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
    speaker_names_text.grid(row=1, column=0, sticky="ew", pady=(6, 0))

    editor_text = scrolledtext.ScrolledText(
        transcript_tab,
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
    editor_text.grid(row=2, column=0, sticky="nsew")
    editor_text.bind("<<Modified>>", bindings.handle_editor_modified)

    return _TranscriptWidgets(
        speaker_names_text=speaker_names_text,
        editor_text=editor_text,
        export_format_combo=export_format_combo,
        reset_editor_button=reset_editor_button,
        export_button=export_button,
    )
