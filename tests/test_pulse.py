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


def test_pulse_estimator_uses_only_masked_skin_pixels():
    estimator = PulseEstimator(fps=5, min_bpm=50, max_bpm=150, window_seconds=4)
    estimate = None
    mask = np.zeros((4, 4), dtype=bool)
    mask[:2, :2] = True
    for i in range(20):
        patch = np.zeros((4, 4, 3), dtype=np.float32)
        patch[:, :, 1] = 250  # non-skin region should be ignored
        patch[:2, :2, 1] = 100 + np.sin(i)
        estimate = estimator.update(patch, mask=mask)

    assert estimate is not None
    assert estimator.last_masked_pixels == 4


def test_pulse_estimator_skips_frame_when_mask_has_too_few_pixels():
    estimator = PulseEstimator(fps=5, min_bpm=50, max_bpm=150, window_seconds=4, min_masked_pixels=4)
    patch = np.zeros((4, 4, 3), dtype=np.float32)
    mask = np.zeros((4, 4), dtype=bool)
    mask[0, 0] = True

    assert estimator.update(patch, mask=mask) is None
    assert len(estimator._values) == 0
