from __future__ import annotations

import cv2

from evm_overlay.config import OverlayConfig
from evm_overlay.pulse import PulseEstimate


def draw_overlay(frame, estimate: PulseEstimate | None, config: OverlayConfig, position: tuple[int, int] | None = None):
    if not config.enabled:
        return frame
    if estimate is not None and estimate.confidence < config.min_confidence:
        return frame
    text = f"{config.label}: -- bpm" if estimate is None else f"{config.label}: {estimate.bpm:0.0f} bpm  conf {estimate.confidence:0.2f}"
    x, y = position or config.position
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80, 255, 80), 2, cv2.LINE_AA)
    return frame
