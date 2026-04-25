"""Optional local speaker labeling support."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .exceptions import DependencyError
from .models import SpeakerCountMode, SpeakerSegment

LOGGER = logging.getLogger(__name__)


class AudioDiarizer:
    """Handle simple local speaker labeling for audio segments."""

    def __init__(
        self,
        speaker_count_mode: SpeakerCountMode = "auto",
        exact_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> None:
        self.speaker_count_mode = speaker_count_mode
        self.exact_speakers = exact_speakers
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self.sample_rate = 16000
        self.window_seconds = 1.2
        self.hop_seconds = 0.6

    def process_audio(self, audio_path: Path) -> list[SpeakerSegment]:
        """Process an audio file and return speaker segments."""
        try:
            import librosa
            import numpy as np
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
        except ImportError as exc:  # pragma: no cover - depends on optional deps
            raise DependencyError(
                "Speaker labeling requires the optional speakers dependencies. "
                "Install them with 'pip install -e .[speakers]'."
            ) from exc

        waveform, _ = librosa.load(str(audio_path), sr=self.sample_rate)
        window_size = int(self.window_seconds * self.sample_rate)
        hop_length = int(self.hop_seconds * self.sample_rate)

        if len(waveform) < window_size:
            return []

        segments: list[Any] = []
        timestamps: list[float] = []
        energies: list[float] = []
        for index in range(0, len(waveform) - window_size, hop_length):
            segment = waveform[index : index + window_size]
            if len(segment) != window_size:
                continue
            energy = float(np.sqrt(np.mean(segment**2)))
            segments.append(segment)
            timestamps.append(index / self.sample_rate)
            energies.append(energy)

        if not segments:
            return []

        energy_floor = max(float(np.percentile(np.array(energies), 25)) * 0.5, 0.003)
        voiced_segments = [
            segment
            for segment, energy in zip(segments, energies, strict=True)
            if energy >= energy_floor
        ]
        voiced_timestamps = [
            timestamp
            for timestamp, energy in zip(timestamps, energies, strict=True)
            if energy >= energy_floor
        ]

        if not voiced_segments:
            LOGGER.info("Skipping speaker labeling because too little voiced audio was found.")
            return []

        features = []
        for segment in voiced_segments:
            segment_mfcc = librosa.feature.mfcc(y=segment, sr=self.sample_rate, n_mfcc=20)
            delta = librosa.feature.delta(segment_mfcc)
            features.append(np.concatenate((np.mean(segment_mfcc, axis=1), np.mean(delta, axis=1))))

        feature_array = np.array(features)
        cluster_count = self._choose_cluster_count(feature_array, silhouette_score)
        if cluster_count <= 1:
            return [
                SpeakerSegment(
                    start=voiced_timestamps[0],
                    end=voiced_timestamps[-1] + self.window_seconds,
                    speaker="SPEAKER_00",
                )
            ]

        kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(feature_array)
        label_names = self._label_names(labels, voiced_timestamps)

        results: list[SpeakerSegment] = []
        current_speaker = label_names[int(labels[0])]
        start_time = voiced_timestamps[0]
        for index in range(1, len(labels)):
            label_name = label_names[int(labels[index])]
            if label_name != current_speaker:
                results.append(
                    SpeakerSegment(
                        start=start_time,
                        end=voiced_timestamps[index],
                        speaker=current_speaker,
                    )
                )
                current_speaker = label_name
                start_time = voiced_timestamps[index]

        results.append(
            SpeakerSegment(
                start=start_time,
                end=voiced_timestamps[-1] + self.window_seconds,
                speaker=current_speaker,
            )
        )
        return results

    def _choose_cluster_count(self, feature_array: Any, silhouette_score: Any) -> int:
        feature_count = len(feature_array)
        if self.speaker_count_mode == "exact":
            return max(1, min(int(self.exact_speakers or 1), feature_count))

        from sklearn.cluster import KMeans

        minimum = 1 if self.min_speakers is None else max(1, self.min_speakers)
        maximum = 6 if self.max_speakers is None else min(self.max_speakers, 12)
        maximum = min(maximum, feature_count)
        minimum = min(minimum, maximum)
        if minimum == maximum:
            return minimum

        best_count = minimum
        best_score = -1.0
        for cluster_count in range(max(2, minimum), maximum + 1):
            if feature_count <= cluster_count:
                continue
            model = KMeans(n_clusters=cluster_count, random_state=42, n_init="auto")
            labels = model.fit_predict(feature_array)
            if len(set(labels)) < 2:
                continue
            score = float(silhouette_score(feature_array, labels))
            if score > best_score:
                best_score = score
                best_count = cluster_count

        if minimum <= 1 and best_score < 0.12:
            return 1
        return best_count

    def _label_names(self, labels: Any, timestamps: list[float]) -> dict[int, str]:
        first_seen: dict[int, float] = {}
        for label, timestamp in zip(labels, timestamps, strict=True):
            label_int = int(label)
            first_seen.setdefault(label_int, timestamp)
        ordered = sorted(first_seen, key=lambda label: first_seen[label])
        return {label: f"SPEAKER_{index:02d}" for index, label in enumerate(ordered)}
