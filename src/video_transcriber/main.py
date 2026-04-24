"""Application entry point."""

from .gui import create_app


def main() -> None:
    """Launch the GUI application."""
    root = create_app()
    root.mainloop()
