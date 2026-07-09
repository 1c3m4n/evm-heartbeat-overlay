import numpy as np

from evm_overlay.config import EvmVisualizationConfig
from evm_overlay.evm_visualization import EvmVisualizer


def test_evm_visualizer_amplifies_subtle_changes_but_ignores_large_changes():
    cfg = EvmVisualizationConfig(alpha=10, learning_rate=0.1, subtle_only=True, subtle_min_delta=0.0, subtle_max_delta=5.0)
    visualizer = EvmVisualizer(cfg)
    baseline = np.full((2, 2, 3), 100, dtype=np.uint8)
    visualizer.update(baseline)

    current = baseline.copy()
    current[0, 0] = [102, 102, 102]  # subtle change, amplify
    current[1, 1] = [140, 140, 140]  # large movement/change, ignore

    out = visualizer.update(current)

    assert out[0, 0, 0] > current[0, 0, 0]
    assert out[1, 1].tolist() == current[1, 1].tolist()


def test_evm_visualizer_spatial_denoise_reduces_high_frequency_variance():
    cfg = EvmVisualizationConfig(alpha=0, learning_rate=0.1, denoise_spatial_kernel=5, denoise_temporal_alpha=1.0)
    visualizer = EvmVisualizer(cfg)
    baseline = np.full((32, 32, 3), 100, dtype=np.uint8)
    visualizer.update(baseline)
    rng = np.random.default_rng(42)
    noisy = np.clip(baseline.astype(np.int16) + rng.integers(-20, 21, size=baseline.shape), 0, 255).astype(np.uint8)

    out = visualizer.update(noisy)

    assert float(np.var(out.astype(float))) < float(np.var(noisy.astype(float)))
