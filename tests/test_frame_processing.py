import numpy as np

from evm_overlay.config import OutputConfig
from evm_overlay.frame_processing import resize_for_output


def test_resize_for_output_scales_frame_when_dimensions_are_set():
    frame = np.zeros((1296, 2304, 3), dtype=np.uint8)
    cfg = OutputConfig(width=1152, height=648)

    resized = resize_for_output(frame, cfg)

    assert resized.shape == (648, 1152, 3)


def test_resize_for_output_returns_original_frame_when_disabled():
    frame = np.zeros((20, 30, 3), dtype=np.uint8)
    cfg = OutputConfig()

    resized = resize_for_output(frame, cfg)

    assert resized is frame
