from video_transcriber.progress import (
    DOWNLOAD_BAND,
    TRANSCRIBE_BAND,
    clamp_monotonic,
)


def test_progress_band_maps_percent() -> None:
    assert DOWNLOAD_BAND.map_percent(0) == 0.0
    assert DOWNLOAD_BAND.map_percent(100) == 20.0
    assert DOWNLOAD_BAND.map_percent(50) == 10.0
    assert TRANSCRIBE_BAND.map_fraction(0.0) == 25.0
    assert TRANSCRIBE_BAND.map_fraction(1.0) == 70.0


def test_clamp_monotonic_never_decreases() -> None:
    assert clamp_monotonic(None, 10.0) == 10.0
    assert clamp_monotonic(40.0, 35.0) == 40.0
    assert clamp_monotonic(40.0, 55.0) == 55.0
    assert clamp_monotonic(40.0, None) == 40.0
