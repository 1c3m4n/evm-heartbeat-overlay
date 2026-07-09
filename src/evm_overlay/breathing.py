from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class BreathingEstimate:
    bpm: float
    confidence: float
    samples: int


class BreathingEstimator:
    """Estimate breathing rate from slow brightness/motion changes in an ROI.

    This is deliberately conservative: sudden large signal jumps are treated as
    gross motion and skipped so they do not poison the low-frequency FFT buffer.
    """

    def __init__(
        self,
        *,
        fps: int,
        min_bpm: int = 8,
        max_bpm: int = 35,
        window_seconds: int = 30,
        max_signal_delta: float = 20.0,
    ) -> None:
        if fps <= 0:
            raise ValueError("fps must be > 0")
        if not (0 < min_bpm < max_bpm):
            raise ValueError("min_bpm must be > 0 and lower than max_bpm")
        self.fps = fps
        self.min_hz = min_bpm / 60.0
        self.max_hz = max_bpm / 60.0
        self.samples_required = max(int(fps * window_seconds), fps * 10)
        self.max_signal_delta = max_signal_delta
        self._values: deque[float] = deque(maxlen=self.samples_required)
        self._last_value: float | None = None

    def update(self, roi_frame: np.ndarray, mask: np.ndarray | None = None) -> BreathingEstimate | None:
        if roi_frame.ndim != 3:
            raise ValueError("roi_frame must be an HxWxC image")
        gray = cv2.cvtColor(roi_frame.astype(np.uint8), cv2.COLOR_BGR2GRAY)
        if mask is not None:
            if mask.shape != gray.shape:
                raise ValueError("mask must match roi_frame height and width")
            if not np.any(mask):
                return None
            value = float(np.mean(gray[mask]))
        else:
            value = float(np.mean(gray))

        if self._last_value is not None and abs(value - self._last_value) > self.max_signal_delta:
            self._last_value = value
            return None
        self._last_value = value
        self._values.append(value)
        if len(self._values) < self.samples_required:
            return None
        return self._estimate(np.asarray(self._values, dtype=np.float64))

    def _estimate(self, values: np.ndarray) -> BreathingEstimate | None:
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
        return BreathingEstimate(bpm=peak_hz * 60.0, confidence=max(0.0, min(1.0, confidence)), samples=len(values))
