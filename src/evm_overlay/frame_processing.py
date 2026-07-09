from __future__ import annotations

import cv2
import numpy as np

from evm_overlay.config import OutputConfig


def resize_for_output(frame: np.ndarray, config: OutputConfig) -> np.ndarray:
    if config.width is None or config.height is None:
        return frame
    if frame.shape[1] == config.width and frame.shape[0] == config.height:
        return frame
    return cv2.resize(frame, (config.width, config.height), interpolation=cv2.INTER_AREA)
