from __future__ import annotations

import cv2

from evm_overlay.breathing import BreathingEstimate
from evm_overlay.config import OverlayConfig
from evm_overlay.pulse import PulseEstimate


def draw_overlay(
    frame,
    estimate: PulseEstimate | None,
    config: OverlayConfig,
    position: tuple[int, int] | None = None,
    breathing: BreathingEstimate | None = None,
):
    if not config.enabled:
        return frame
    if estimate is not None and estimate.confidence < config.min_confidence:
        if breathing is None:
            return frame
        estimate = None
    lines = [f"{config.pulse_label}: -- bpm" if estimate is None else f"{config.pulse_label}: {estimate.bpm:0.0f} bpm  conf {estimate.confidence:0.2f}"]
    if breathing is not None:
        lines.append(f"{config.breathing_label}: {breathing.bpm:0.0f} br/min  conf {breathing.confidence:0.2f}")
    else:
        lines.append(f"{config.breathing_label}: -- br/min")
    x, y = position or config.position
    for i, text in enumerate(lines):
        line_y = y + i * 34
        cv2.putText(frame, text, (x, line_y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, text, (x, line_y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 255, 80), 2, cv2.LINE_AA)
    return frame
