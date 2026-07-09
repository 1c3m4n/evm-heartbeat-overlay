from __future__ import annotations

import numpy as np

from evm_overlay.config import RoiConfig


def crop_roi(frame: np.ndarray, roi: RoiConfig) -> np.ndarray:
    """Return the configured region of interest from a HxWxC frame."""
    row_slice, col_slice = roi.as_slice()
    if frame.ndim < 2:
        raise ValueError("frame must have at least height and width dimensions")
    if roi.y + roi.height > frame.shape[0] or roi.x + roi.width > frame.shape[1]:
        raise ValueError(f"roi {roi} exceeds frame shape {frame.shape}")
    return frame[row_slice, col_slice]
