import numpy as np

from evm_overlay.config import EvmVisualizationConfig, RoiConfig
from evm_overlay.evm_visualization import EvmVisualizer, draw_evm_inset


def test_evm_visualizer_amplifies_temporal_roi_changes():
    cfg = EvmVisualizationConfig(enabled=True, alpha=20.0, learning_rate=0.5, inset_scale=1.0)
    visualizer = EvmVisualizer(cfg)
    first = np.full((4, 4, 3), 100, dtype=np.uint8)
    second = first.copy()
    second[:, :, 1] = 104

    baseline = visualizer.update(first)
    amplified = visualizer.update(second)

    assert baseline.dtype == np.uint8
    assert amplified[:, :, 1].mean() > second[:, :, 1].mean()
    assert amplified[:, :, 0].mean() == second[:, :, 0].mean()


def test_draw_evm_inset_places_labeled_visualization_next_to_roi():
    frame = np.zeros((100, 160, 3), dtype=np.uint8)
    evm_roi = np.full((20, 30, 3), 180, dtype=np.uint8)
    roi = RoiConfig(x=10, y=15, width=30, height=20)
    cfg = EvmVisualizationConfig(enabled=True, inset_scale=1.0, border_color=(1, 2, 3))

    out = draw_evm_inset(frame.copy(), evm_roi, roi, cfg)

    # Inset is drawn to the right of the ROI at x + width + margin.
    assert out[15, 48].tolist() == [1, 2, 3]
    assert out[20, 55].mean() > 100
