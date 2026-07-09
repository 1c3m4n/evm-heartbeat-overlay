import numpy as np

from evm_overlay.config import OverlayConfig
from evm_overlay.overlay import draw_overlay
from evm_overlay.pulse import PulseEstimate


def test_draw_overlay_hides_pulse_below_minimum_confidence():
    frame = np.zeros((80, 240, 3), dtype=np.uint8)
    estimate = PulseEstimate(bpm=90, confidence=0.2, samples=300)
    config = OverlayConfig(enabled=True, min_confidence=0.5)

    out = draw_overlay(frame.copy(), estimate, config)

    assert not out.any()


def test_draw_overlay_renders_when_confidence_meets_threshold():
    frame = np.zeros((80, 240, 3), dtype=np.uint8)
    estimate = PulseEstimate(bpm=90, confidence=0.5, samples=300)
    config = OverlayConfig(enabled=True, min_confidence=0.5, position=(10, 40))

    out = draw_overlay(frame.copy(), estimate, config)

    assert out.any()
