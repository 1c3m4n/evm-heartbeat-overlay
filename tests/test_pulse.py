import numpy as np

from evm_overlay.pulse import PulseEstimator


def test_pulse_estimator_recovers_synthetic_heart_rate_from_green_channel():
    fps = 30
    bpm = 120
    samples = fps * 10
    t = np.arange(samples) / fps
    signal = 100 + 4 * np.sin(2 * np.pi * (bpm / 60.0) * t)
    rng = np.random.default_rng(42)

    estimator = PulseEstimator(fps=fps, min_bpm=60, max_bpm=180, window_seconds=8)
    estimate = None
    for value in signal + rng.normal(0, 0.1, size=samples):
        patch = np.zeros((8, 8, 3), dtype=np.float32)
        patch[:, :, 1] = value
        estimate = estimator.update(patch)

    assert estimate is not None
    assert abs(estimate.bpm - bpm) <= 4
    assert 0.0 <= estimate.confidence <= 1.0
