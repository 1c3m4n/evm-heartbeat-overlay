from __future__ import annotations

import cv2
import numpy as np

from evm_overlay.config import SkinDetectionConfig


def is_infrared_frame(frame_bgr: np.ndarray, config: SkinDetectionConfig) -> bool:
    if frame_bgr.size == 0:
        return False
    frame = frame_bgr.astype(np.int16)
    spread = np.max(frame, axis=2) - np.min(frame, axis=2)
    nearly_gray = spread <= config.ir_grayscale_tolerance
    return float(np.mean(nearly_gray)) >= 0.85


def _visible_skin_mask(frame_bgr: np.ndarray, preset: str) -> np.ndarray:
    ycrcb = cv2.cvtColor(frame_bgr.astype(np.uint8), cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0]
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]

    if preset == "light":
        # Tuned for light/fair skin under indoor camera lighting. Keep broad
        # enough for shadows and camera white-balance drift, but reject blue,
        # green, and grey bedding/fabric.
        return (y > 45) & (cr >= 132) & (cr <= 180) & (cb >= 75) & (cb <= 135)
    return (y > 35) & (cr >= 125) & (cr <= 185) & (cb >= 65) & (cb <= 145)


def _infrared_skin_candidate_mask(frame_bgr: np.ndarray, config: SkinDetectionConfig) -> np.ndarray:
    gray = cv2.cvtColor(frame_bgr.astype(np.uint8), cv2.COLOR_BGR2GRAY)
    frame = frame_bgr.astype(np.int16)
    spread = np.max(frame, axis=2) - np.min(frame, axis=2)
    nearly_gray = spread <= config.ir_grayscale_tolerance
    # In night/IR mode the camera image is monochrome; skin-color chroma is gone.
    # Use usable non-clipped luminance and grayscale-ness as the candidate mask.
    return nearly_gray & (gray >= config.ir_luma_min) & (gray <= config.ir_luma_max)


def make_skin_mask(frame_bgr: np.ndarray, config: SkinDetectionConfig) -> np.ndarray:
    if not config.enabled:
        return np.ones(frame_bgr.shape[:2], dtype=bool)

    if config.preset == "ir":
        mask = _infrared_skin_candidate_mask(frame_bgr, config)
    elif config.preset == "auto" and is_infrared_frame(frame_bgr, config):
        mask = _infrared_skin_candidate_mask(frame_bgr, config)
    else:
        visible_preset = "light" if config.preset == "auto" else config.preset
        mask = _visible_skin_mask(frame_bgr, visible_preset)

    return mask.astype(bool)


def apply_mask_visualization(frame_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = frame_bgr.copy()
    out[~mask] = (out[~mask] * 0.25).astype(out.dtype)
    return out
