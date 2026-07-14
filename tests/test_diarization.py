from __future__ import annotations

from video_transcriber.audio_preprocess import _audio_filters_for_preset
from video_transcriber.diarization import AudioDiarizer


def test_audio_filters_for_presets() -> None:
    assert _audio_filters_for_preset("off") == []
    light = _audio_filters_for_preset("light")
    meeting = _audio_filters_for_preset("meeting")
    assert light[0][0] == "highpass"
    assert light[-1] == ("afftdn", {"nf": -25})
    assert meeting[-1] == ("afftdn", {"nf": -30})


def test_choose_cluster_count_exact_mode() -> None:
    diarizer = AudioDiarizer(speaker_count_mode="exact", exact_speakers=3)
    features = [[0.0] * 4 for _ in range(10)]
    assert diarizer._choose_cluster_count(features, silhouette_score=lambda *_a: 1.0) == 3


def test_choose_cluster_count_caps_at_feature_count() -> None:
    diarizer = AudioDiarizer(speaker_count_mode="exact", exact_speakers=8)
    features = [[0.0] * 4 for _ in range(3)]
    assert diarizer._choose_cluster_count(features, silhouette_score=lambda *_a: 1.0) == 3


def test_label_names_orders_by_first_seen_timestamp() -> None:
    diarizer = AudioDiarizer()
    labels = [1, 0, 1, 0]
    names = diarizer._label_names(labels, [0.0, 0.6, 1.2, 1.8])
    assert names[1] == "SPEAKER_00"
    assert names[0] == "SPEAKER_01"
