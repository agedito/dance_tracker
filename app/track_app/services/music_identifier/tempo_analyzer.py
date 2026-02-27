from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks

from app.interface.music import SongMetadata


class ScipyTempoAnalyzer:
    """Estimate pulse count and tempo from a local WAV file using scipy + numpy."""

    def analyze(self, audio_path: str) -> SongMetadata:
        audio_file = Path(audio_path)
        if not audio_file.exists() or not audio_file.is_file():
            return SongMetadata(
                status="analysis_unavailable",
                analysis_provider="scipy",
                message="Audio sample not found for tempo analysis.",
            )

        try:
            sample_rate, audio_data = wavfile.read(str(audio_file))
        except Exception as err:
            return SongMetadata(
                status="analysis_unavailable",
                analysis_provider="scipy",
                message=f"Could not read audio for tempo analysis: {err}",
            )

        mono = self._to_mono_float(audio_data)
        if mono.size < 4 or sample_rate <= 0:
            return SongMetadata(
                status="analysis_unavailable",
                analysis_provider="scipy",
                message="Audio sample is too short for tempo analysis.",
            )

        duration_s = float(mono.size / sample_rate)
        envelope = self._energy_envelope(mono, sample_rate)
        if envelope.size < 8:
            return SongMetadata(
                status="analysis_unavailable",
                analysis_provider="scipy",
                audio_duration_s=duration_s,
                message="Audio sample is too short for pulse detection.",
            )

        peaks = self._detect_pulses(envelope, sample_rate)
        pulse_count = int(peaks.size)
        tempo_bpm = self._estimate_bpm(peaks, sample_rate)

        return SongMetadata(
            status="analysis_ready",
            analysis_provider="scipy",
            tempo_bpm=tempo_bpm,
            pulse_count=pulse_count,
            audio_duration_s=duration_s,
        )

    @staticmethod
    def _to_mono_float(audio_data: np.ndarray) -> np.ndarray:
        data = audio_data.astype(np.float64)
        if data.ndim == 2:
            data = data.mean(axis=1)
        max_abs = np.max(np.abs(data)) if data.size else 0.0
        if max_abs > 0:
            data = data / max_abs
        return data

    @staticmethod
    def _energy_envelope(mono: np.ndarray, sample_rate: int) -> np.ndarray:
        window_s = 0.05
        window = max(32, int(sample_rate * window_s))
        kernel = np.ones(window, dtype=np.float64) / float(window)
        return np.convolve(mono * mono, kernel, mode="same")

    @staticmethod
    def _detect_pulses(envelope: np.ndarray, sample_rate: int) -> np.ndarray:
        mean_energy = float(np.mean(envelope))
        std_energy = float(np.std(envelope))
        min_distance = max(1, int(sample_rate * 0.24))
        prominence = max(1e-6, mean_energy + std_energy * 0.5)
        peaks, _ = find_peaks(envelope, distance=min_distance, prominence=prominence)
        return peaks

    @staticmethod
    def _estimate_bpm(peaks: np.ndarray, sample_rate: int) -> float | None:
        if peaks.size < 2:
            return None
        intervals = np.diff(peaks.astype(np.float64)) / float(sample_rate)
        intervals = intervals[intervals > 1e-3]
        if intervals.size == 0:
            return None

        median_interval = float(np.median(intervals))
        if median_interval <= 0:
            return None

        bpm = 60.0 / median_interval
        return round(float(np.clip(bpm, 40.0, 220.0)), 1)
