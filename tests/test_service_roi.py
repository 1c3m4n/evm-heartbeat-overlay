import numpy as np

from evm_overlay.config import AppConfig, RoiConfig
from evm_overlay.service import crop_breathing_roi


def test_crop_breathing_roi_uses_separate_breathing_roi_when_configured():
    frame = np.arange(10 * 12 * 3, dtype=np.uint8).reshape(10, 12, 3)
    cfg = AppConfig(
        input_url="rtsp://in",
        output_url="rtsp://out",
        roi=RoiConfig(x=1, y=1, width=3, height=3),
        breathing_roi=RoiConfig(x=5, y=2, width=4, height=5),
    )

    cropped = crop_breathing_roi(frame, cfg)

    assert cropped.shape == (5, 4, 3)
    np.testing.assert_array_equal(cropped, frame[2:7, 5:9])


def test_crop_breathing_roi_falls_back_to_pulse_roi_when_not_configured():
    frame = np.arange(10 * 12 * 3, dtype=np.uint8).reshape(10, 12, 3)
    cfg = AppConfig(
        input_url="rtsp://in",
        output_url="rtsp://out",
        roi=RoiConfig(x=1, y=1, width=3, height=3),
    )

    cropped = crop_breathing_roi(frame, cfg)

    assert cropped.shape == (3, 3, 3)
    np.testing.assert_array_equal(cropped, frame[1:4, 1:4])
