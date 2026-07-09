from __future__ import annotations

import cv2
import numpy as np

from evm_overlay.config import EvmVisualizationConfig, RoiConfig


class EvmVisualizer:
    """Small temporal EVM-style visualizer for the ROI.

    This keeps an exponential moving average per pixel and amplifies short-term
    color deviations. It is intentionally lightweight for live Docker testing;
    the later full EVM task can replace this with pyramid + bandpass filtering.
    """

    def __init__(self, config: EvmVisualizationConfig) -> None:
        self.config = config
        self._baseline: np.ndarray | None = None

    def update(self, roi_frame: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        current = roi_frame.astype(np.float32)
        if self._baseline is None or self._baseline.shape != current.shape:
            self._baseline = current.copy()
            return roi_frame.copy()

        delta = current - self._baseline
        amplified_float = current + delta * self.config.alpha
        if mask is not None:
            amplified_float = current.copy()
            amplified_float[mask] = current[mask] + delta[mask] * self.config.alpha
        amplified = np.clip(amplified_float, 0, 255).astype(np.uint8)
        lr = self.config.learning_rate
        self._baseline = (1.0 - lr) * self._baseline + lr * current
        return amplified


def compute_evm_inset_rect(frame: np.ndarray, evm_roi: np.ndarray, roi: RoiConfig, config: EvmVisualizationConfig) -> tuple[int, int, int, int]:
    inset_w = max(1, int(evm_roi.shape[1] * config.inset_scale))
    inset_h = max(1, int(evm_roi.shape[0] * config.inset_scale))

    if config.anchor == "bottom_right":
        x = max(0, frame.shape[1] - inset_w - config.margin)
        y = max(0, frame.shape[0] - inset_h - config.margin)
        return x, y, inset_w, inset_h

    x = roi.x + roi.width + config.margin
    if x + inset_w > frame.shape[1]:
        x = max(0, roi.x - config.margin - inset_w)
    y = min(max(0, roi.y), max(0, frame.shape[0] - inset_h))
    return x, y, inset_w, inset_h


def draw_evm_inset(frame: np.ndarray, evm_roi: np.ndarray, roi: RoiConfig, config: EvmVisualizationConfig) -> np.ndarray:
    if not config.enabled or config.mode == "off":
        return frame

    if config.mode == "replace_roi":
        resized = cv2.resize(evm_roi, (roi.width, roi.height), interpolation=cv2.INTER_LINEAR)
        frame[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width] = resized
        cv2.rectangle(frame, (roi.x, roi.y), (roi.x + roi.width, roi.y + roi.height), config.border_color, 2)
        cv2.putText(frame, "EVM", (roi.x + 6, max(roi.y + 24, 24)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, config.border_color, 2, cv2.LINE_AA)
        return frame

    x, y, inset_w, inset_h = compute_evm_inset_rect(frame, evm_roi, roi, config)
    inset = cv2.resize(evm_roi, (inset_w, inset_h), interpolation=cv2.INTER_LINEAR)

    frame[y : y + inset_h, x : x + inset_w] = inset
    cv2.rectangle(frame, (x, y), (x + inset_w, y + inset_h), config.border_color, 2)
    cv2.putText(frame, "EVM", (x + 6, max(y + 24, 24)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, config.border_color, 2, cv2.LINE_AA)
    return frame
