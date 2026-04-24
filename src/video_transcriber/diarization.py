"""Optional speaker diarization support."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .exceptions import DependencyError
from .models import SpeakerSegment

LOGGER = logging.getLogger(__name__)


class AudioDiarizer:
    """Handle simple speaker diarization for audio segments."""

    def __init__(self, num_speakers: int = 2) -> None:
        self.num_speakers = num_speakers
        self.sample_rate = 16000

    def process_audio(self, audio_path: Path) -> list[SpeakerSegment]:
        """Process an audio file and return speaker segments."""
        try:
            import librosa
            import numpy as np
            from sklearn.cluster import KMeans
        except ImportError as exc:  # pragma: no cover - depends on optional deps
            raise DependencyError(
                "Speaker diarization requires the optional diarization dependencies."
            ) from exc

        waveform, _ = librosa.load(str(audio_path), sr=self.sample_rate)
        window_size = int(0.5 * self.sample_rate)
        hop_length = int(0.25 * self.sample_rate)

        segments: list[Any] = []
        timestamps: list[float] = []
        for index in range(0, len(waveform) - window_size, hop_length):
            segment = waveform[index : index + window_size]
            energy = float(np.sum(segment ** 2))
            if len(segment) == window_size and energy > 0.001:
                segments.append(segment)
                timestamps.append(index / self.sample_rate)

        if len(segments) < self.num_speakers:
            LOGGER.info("Skipping diarization because too few voiced audio windows were found.")
            return []

        features = []
        for segment in segments:
            segment_mfcc = librosa.feature.mfcc(y=segment, sr=self.sample_rate, n_mfcc=20)
            features.append(np.mean(segment_mfcc.T, axis=0))

        kmeans = KMeans(n_clusters=self.num_speakers, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(np.array(features))

        results: list[SpeakerSegment] = []
        current_speaker = int(labels[0])
        start_time = timestamps[0]
        for index in range(1, len(labels)):
            if int(labels[index]) != current_speaker:
                results.append(
                    SpeakerSegment(start=start_time, end=timestamps[index], speaker=current_speaker)
                )
                current_speaker = int(labels[index])
                start_time = timestamps[index]

        results.append(
            SpeakerSegment(start=start_time, end=timestamps[-1] + 0.5, speaker=current_speaker)
        )
        return results
