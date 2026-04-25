"""Video download integration."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from .exceptions import CancelledError, DependencyError, ProcessingError
from .models import CancellationToken
from .utils import sanitize_filename

ProgressCallback = Callable[[str, str, float | None], None]


def download_video(
    url: str,
    output_dir: Path,
    callback: ProgressCallback | None = None,
    cancellation_token: CancellationToken | None = None,
) -> Path:
    """Download a video and return the resolved output path."""
    try:
        import yt_dlp
    except ImportError as exc:
        raise DependencyError("yt-dlp is not installed.") from exc

    template = output_dir / f"{sanitize_filename('%(title)s', 'downloaded_video')}.%(ext)s"

    def progress_hook(data: dict[str, object]) -> None:
        if cancellation_token is not None and cancellation_token.is_cancelled():
            raise CancelledError("Download cancelled.")
        if callback is None:
            return
        status = str(data.get("status", "unknown"))
        if status == "downloading":
            downloaded = _as_float(data.get("downloaded_bytes"), 0.0) or 0.0
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            total_bytes = _as_float(total)
            progress = (downloaded / total_bytes * 100.0) if total_bytes else None
            callback("download", "Downloading video", progress)
        elif status == "finished":
            callback("download", "Download complete", 100.0)

    options = _build_download_options(url, template, progress_hook)

    with yt_dlp.YoutubeDL(options) as ydl:  # pyright: ignore[reportArgumentType]
        try:
            info = ydl.extract_info(url, download=True)
        except CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - passthrough from yt-dlp
            raise ProcessingError(f"Failed to download video: {exc}") from exc

        candidates = _candidate_paths(ydl, dict(info))
        for candidate in candidates:
            if candidate.exists():
                return candidate

    raise ProcessingError("Download finished but the output video file could not be found.")


def _candidate_paths(ydl: object, info: dict[str, object]) -> list[Path]:
    """Build a list of likely output paths from yt-dlp metadata."""
    paths: list[Path] = []
    requested_downloads = info.get("requested_downloads")
    if isinstance(requested_downloads, list):
        for item in requested_downloads:
            if isinstance(item, dict) and item.get("filepath"):
                paths.append(Path(str(item["filepath"])))

    filepath = info.get("_filename")
    if filepath:
        paths.append(Path(str(filepath)))

    prepared = getattr(ydl, "prepare_filename", None)
    if callable(prepared):
        prepared_path = Path(str(prepared(info)))
        paths.append(prepared_path)
        paths.append(prepared_path.with_suffix(".mp4"))

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def _build_download_options(
    url: str,
    template: Path,
    progress_hook: Callable[[dict[str, object]], None],
) -> dict[str, object]:
    options: dict[str, object] = {
        "outtmpl": str(template),
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "progress_hooks": [progress_hook],
        "restrictfilenames": True,
        "noplaylist": True,
    }
    if _is_youtube_url(url):
        options["remote_components"] = ["ejs:github"]
    return options


def _is_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return hostname in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def _as_float(value: object, default: float | None = None) -> float | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float | str):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default
