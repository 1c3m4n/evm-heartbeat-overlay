import numpy as np

from evm_overlay.config import SkinDetectionConfig
from evm_overlay.skin_detection import apply_mask_visualization, is_infrared_frame, make_skin_mask


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


def test_auto_skin_mask_uses_ir_luminance_when_frame_is_grayscale_night_vision():
    frame = np.zeros((3, 3, 3), dtype=np.uint8)
    frame[:, :] = [95, 95, 95]  # monochrome IR candidate
    frame[0, 0] = [255, 255, 255]  # clipped highlight should be rejected
    frame[0, 1] = [5, 5, 5]  # too dark should be rejected
    cfg = SkinDetectionConfig(enabled=True, preset="auto", ir_luma_min=30, ir_luma_max=220, min_pixels=1)

    mask = make_skin_mask(frame, cfg)

    assert is_infrared_frame(frame, cfg)
    assert mask[1, 1]
    assert not mask[0, 0]
    assert not mask[0, 1]


def test_auto_skin_mask_keeps_visible_light_rules_for_color_frame():
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    frame[0, 0] = [170, 190, 230]
    frame[0, 1] = [95, 95, 95]
    cfg = SkinDetectionConfig(enabled=True, preset="auto", min_pixels=1)

    mask = make_skin_mask(frame, cfg)

    assert not is_infrared_frame(frame, cfg)
    assert mask[0, 0]
    assert not mask[0, 1]
