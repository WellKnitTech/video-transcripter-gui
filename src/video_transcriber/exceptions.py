"""Project-specific exceptions."""


class VideoTranscriberError(Exception):
    """Base exception for the application."""


class ValidationError(VideoTranscriberError):
    """Raised when user input or configuration is invalid."""


class DependencyError(VideoTranscriberError):
    """Raised when an external dependency is unavailable."""


class ProcessingError(VideoTranscriberError):
    """Raised when media processing fails."""


class CancelledError(VideoTranscriberError):
    """Raised when the current job is cancelled."""
