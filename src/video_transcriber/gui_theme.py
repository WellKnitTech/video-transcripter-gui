"""Shared theme constants and style helpers for the Tkinter GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

MODEL_OPTIONS = ["tiny", "base", "small", "medium", "large"]
SUBTITLE_FORMAT_OPTIONS = ["ass", "srt", "vtt"]
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


def configure_styles(root: tk.Misc) -> None:
    """Apply the shared application theme."""
    style = ttk.Style(root)
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
