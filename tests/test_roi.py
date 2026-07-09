import numpy as np

from evm_overlay.roi import crop_roi
from evm_overlay.config import RoiConfig


def test_crop_roi_returns_exact_frame_region_without_copying_shape():
    frame = np.arange(4 * 5 * 3, dtype=np.uint8).reshape((4, 5, 3))
    roi = RoiConfig(x=1, y=1, width=3, height=2)

    cropped = crop_roi(frame, roi)

    assert cropped.shape == (2, 3, 3)
    np.testing.assert_array_equal(cropped, frame[1:3, 1:4])
