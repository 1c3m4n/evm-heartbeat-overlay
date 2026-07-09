from __future__ import annotations

import cv2
import numpy as np

from evm_overlay.config import SkinDetectionConfig


def make_skin_mask(frame_bgr: np.ndarray, config: SkinDetectionConfig) -> np.ndarray:
    if not config.enabled:
        return np.ones(frame_bgr.shape[:2], dtype=bool)

    ycrcb = cv2.cvtColor(frame_bgr.astype(np.uint8), cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0]
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]

    if config.preset == "light":
        # Tuned for light/fair skin under indoor camera lighting. Keep broad
        # enough for shadows and camera white-balance drift, but reject blue,
        # green, and grey bedding/fabric.
        mask = (y > 45) & (cr >= 132) & (cr <= 180) & (cb >= 75) & (cb <= 135)
    else:
        mask = (y > 35) & (cr >= 125) & (cr <= 185) & (cb >= 65) & (cb <= 145)

    return mask.astype(bool)


def apply_mask_visualization(frame_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = frame_bgr.copy()
    out[~mask] = (out[~mask] * 0.25).astype(out.dtype)
    return out
