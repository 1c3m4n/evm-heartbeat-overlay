import numpy as np

from evm_overlay.config import SkinDetectionConfig
from evm_overlay.skin_detection import make_skin_mask, apply_mask_visualization


def test_make_skin_mask_detects_light_skin_ycrcb_sample_and_rejects_blue_fabric():
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    frame[0, 0] = [170, 190, 230]  # BGR light warm skin-like sample
    frame[0, 1] = [230, 40, 30]    # blue fabric-like sample
    cfg = SkinDetectionConfig(enabled=True, preset="light", min_pixels=1)

    mask = make_skin_mask(frame, cfg)

    assert mask[0, 0]
    assert not mask[0, 1]


def test_make_skin_mask_returns_all_pixels_when_disabled():
    frame = np.zeros((3, 4, 3), dtype=np.uint8)
    cfg = SkinDetectionConfig(enabled=False)

    mask = make_skin_mask(frame, cfg)

    assert mask.shape == (3, 4)
    assert mask.all()


def test_apply_mask_visualization_darkens_non_skin_pixels():
    frame = np.full((2, 2, 3), 100, dtype=np.uint8)
    mask = np.array([[True, False], [False, True]])

    visualized = apply_mask_visualization(frame, mask)

    assert visualized[0, 0].tolist() == [100, 100, 100]
    assert visualized[0, 1].tolist() == [25, 25, 25]
