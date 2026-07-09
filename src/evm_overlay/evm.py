from __future__ import annotations

import math

import cv2
import numpy as np


class TemporalPyramidEvm:
    """CPU-first Eulerian video magnification for one ROI.

    A Laplacian pyramid isolates a spatial frequency band. Two exponential
    low-pass filters form a bounded temporal band-pass signal; only that signal
    is amplified and added back to the original ROI. The class retains two
    downsampled float images, so memory use is bounded by the selected pyramid
    level rather than the duration of the stream.
    """

    def __init__(
        self,
        *,
        fps: float,
        low_hz: float,
        high_hz: float,
        alpha: float,
        pyramid_level: int = 1,
        enabled: bool = True,
    ) -> None:
        if fps <= 0:
            raise ValueError("fps must be > 0")
        if not (0 < low_hz < high_hz < fps / 2):
            raise ValueError("low_hz and high_hz must be ordered and below Nyquist")
        if alpha < 0:
            raise ValueError("alpha must be >= 0")
        if pyramid_level < 0:
            raise ValueError("pyramid_level must be >= 0")
        self.fps = float(fps)
        self.low_hz = float(low_hz)
        self.high_hz = float(high_hz)
        self.alpha = float(alpha)
        self.pyramid_level = pyramid_level
        self.enabled = enabled
        self._fast: np.ndarray | None = None
        self._fast_stage2: np.ndarray | None = None
        self._slow: np.ndarray | None = None
        self._slow_stage2: np.ndarray | None = None
        self._level_shape: tuple[int, int] | None = None
        self._fast_alpha = self._smoothing_alpha(high_hz)
        self._slow_alpha = self._smoothing_alpha(low_hz)

    def _smoothing_alpha(self, cutoff_hz: float) -> float:
        return 1.0 - math.exp(-2.0 * math.pi * cutoff_hz / self.fps)

    def _laplacian_level(self, frame: np.ndarray) -> np.ndarray:
        level = frame.astype(np.float32)
        for _ in range(self.pyramid_level):
            level = cv2.pyrDown(level)
        next_level = cv2.pyrDown(level)
        expanded = cv2.pyrUp(next_level, dstsize=(level.shape[1], level.shape[0]))
        self._level_shape = level.shape[:2]
        return level - expanded

    def _expand_to_frame(self, band: np.ndarray, frame_shape: tuple[int, int]) -> np.ndarray:
        expanded = band
        for _ in range(self.pyramid_level):
            expanded = cv2.pyrUp(expanded)
        return cv2.resize(expanded, (frame_shape[1], frame_shape[0]), interpolation=cv2.INTER_LINEAR)

    def update(self, frame_bgr: np.ndarray) -> np.ndarray:
        if not self.enabled:
            return frame_bgr.copy()
        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            raise ValueError("frame_bgr must be an HxWx3 BGR image")

        laplacian = self._laplacian_level(frame_bgr)
        if self._fast is None or self._fast.shape != laplacian.shape:
            self._fast = laplacian.copy()
            self._fast_stage2 = laplacian.copy()
            self._slow = laplacian.copy()
            self._slow_stage2 = laplacian.copy()
            return frame_bgr.copy()

        self._fast = self._fast + self._fast_alpha * (laplacian - self._fast)
        self._fast_stage2 = self._fast_stage2 + self._fast_alpha * (self._fast - self._fast_stage2)
        self._slow = self._slow + self._slow_alpha * (laplacian - self._slow)
        self._slow_stage2 = self._slow_stage2 + self._slow_alpha * (self._slow - self._slow_stage2)
        temporal_band = self._fast_stage2 - self._slow_stage2
        amplified = self._expand_to_frame(temporal_band, frame_bgr.shape[:2])
        output = frame_bgr.astype(np.float32) + self.alpha * amplified
        return np.clip(output, 0, 255).astype(np.uint8)
