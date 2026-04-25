from __future__ import annotations

from pathlib import Path

from video_transcriber.download import _build_download_options, _is_youtube_url


def test_build_download_options_enables_remote_components_for_youtube_urls() -> None:
    options = _build_download_options(
        "https://www.youtube.com/watch?v=abc123",
        Path("/tmp/video.%(ext)s"),
        lambda _data: None,
    )

    assert options["remote_components"] == ["ejs:github"]


def test_build_download_options_skips_remote_components_for_non_youtube_urls() -> None:
    options = _build_download_options(
        "https://vimeo.com/123456",
        Path("/tmp/video.%(ext)s"),
        lambda _data: None,
    )

    assert "remote_components" not in options


def test_is_youtube_url_accepts_supported_hosts() -> None:
    assert _is_youtube_url("https://www.youtube.com/shorts/abc123")
    assert _is_youtube_url("https://youtu.be/abc123")
    assert not _is_youtube_url("https://example.com/watch?v=abc123")
