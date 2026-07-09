from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PulseEstimate:
    bpm: float
    confidence: float
    samples: int


class PulseEstimator:
    """Estimate pulse rate from the mean green-channel value of an ROI.

    This is the first rPPG building block. It keeps a rolling signal buffer and
    selects the strongest FFT peak inside the configured physiological band.
    EVM amplification can be inserted upstream later to improve SNR.
    """

    def __init__(self, *, fps: int, min_bpm: int, max_bpm: int, window_seconds: int = 12, min_masked_pixels: int = 0) -> None:
        if fps <= 0:
            raise ValueError("fps must be > 0")
        if not (0 < min_bpm < max_bpm):
            raise ValueError("min_bpm must be > 0 and lower than max_bpm")
        self.fps = fps
        self.min_hz = min_bpm / 60.0
        self.max_hz = max_bpm / 60.0
        self.samples_required = max(int(fps * window_seconds), fps * 4)
        self.min_masked_pixels = min_masked_pixels
        self.last_masked_pixels = 0
        self._values: deque[float] = deque(maxlen=self.samples_required)

    def update(self, roi_frame: np.ndarray, mask: np.ndarray | None = None) -> PulseEstimate | None:
        if roi_frame.ndim != 3 or roi_frame.shape[2] < 2:
            raise ValueError("roi_frame must be an HxWxC image with a green channel")
        if mask is None:
            self.last_masked_pixels = int(roi_frame.shape[0] * roi_frame.shape[1])
            value = float(np.mean(roi_frame[:, :, 1]))
        else:
            if mask.shape != roi_frame.shape[:2]:
                raise ValueError("mask must match roi_frame height and width")
            self.last_masked_pixels = int(np.count_nonzero(mask))
            if self.last_masked_pixels < self.min_masked_pixels:
                return None
            value = float(np.mean(roi_frame[:, :, 1][mask]))
        self._values.append(value)
        if len(self._values) < self.samples_required:
            return None
        return self._estimate(np.asarray(self._values, dtype=np.float64))

    def _estimate(self, values: np.ndarray) -> PulseEstimate | None:
        detrended = values - np.mean(values)
        std = float(np.std(detrended))
        if std <= 1e-9:
            return None
        windowed = detrended * np.hamming(len(detrended))
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(windowed), d=1.0 / self.fps)
        band = (freqs >= self.min_hz) & (freqs <= self.max_hz)
        if not np.any(band):
            return None
        band_power = spectrum[band]
        peak_idx = int(np.argmax(band_power))
        peak_hz = float(freqs[band][peak_idx])
        total_power = float(np.sum(band_power))
        confidence = 0.0 if total_power <= 1e-12 else float(band_power[peak_idx] / total_power)
        return PulseEstimate(bpm=peak_hz * 60.0, confidence=max(0.0, min(1.0, confidence)), samples=len(values))
