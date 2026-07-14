"""Overall job progress banding helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProgressBand:
    start: float
    end: float

    def map_fraction(self, fraction: float) -> float:
        """Map a 0-1 fraction into this band."""
        clamped = max(0.0, min(float(fraction), 1.0))
        return self.start + (self.end - self.start) * clamped

    def map_percent(self, percent: float | None) -> float | None:
        """Map a 0-100 percent value into this band."""
        if percent is None:
            return None
        return self.map_fraction(percent / 100.0)


DOWNLOAD_BAND = ProgressBand(0.0, 20.0)
LOAD_MODEL_BAND = ProgressBand(20.0, 25.0)
TRANSCRIBE_BAND = ProgressBand(25.0, 70.0)
DIARIZATION_BAND = ProgressBand(70.0, 85.0)
WRITE_OUTPUTS_BAND = ProgressBand(85.0, 95.0)
EMBED_BAND = ProgressBand(95.0, 100.0)


def clamp_monotonic(previous: float | None, current: float | None) -> float | None:
    """Ensure progress values never move backwards within a job."""
    if current is None:
        return previous
    if previous is None:
        return current
    return max(previous, current)
