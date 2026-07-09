import numpy as np

from evm_overlay.breathing import BreathingEstimator


def test_breathing_estimator_recovers_synthetic_breath_rate_from_motion_signal():
    fps = 15
    bpm = 18
    samples = fps * 40
    t = np.arange(samples) / fps
    signal = 80 + 15 * np.sin(2 * np.pi * (bpm / 60.0) * t)

    estimator = BreathingEstimator(fps=fps, min_bpm=8, max_bpm=35, window_seconds=30)
    estimate = None
    for value in signal:
        patch = np.full((12, 12, 3), value, dtype=np.float32)
        estimate = estimator.update(patch)

    assert estimate is not None
    assert abs(estimate.bpm - bpm) <= 2
    assert 0.0 <= estimate.confidence <= 1.0


def test_breathing_estimator_ignores_large_frame_jumps():
    estimator = BreathingEstimator(fps=5, min_bpm=8, max_bpm=35, window_seconds=4, max_signal_delta=10)
    patch = np.full((8, 8, 3), 50, dtype=np.float32)
    jump = np.full((8, 8, 3), 200, dtype=np.float32)

    estimator.update(patch)
    estimator.update(jump)

    assert len(estimator._values) == 1
