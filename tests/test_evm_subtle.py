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
