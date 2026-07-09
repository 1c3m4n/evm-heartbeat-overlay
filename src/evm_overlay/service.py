from __future__ import annotations

import argparse
import logging
import time

import cv2

from evm_overlay.config import load_config
from evm_overlay.evm_visualization import EvmVisualizer, draw_evm_inset
from evm_overlay.frame_processing import resize_for_output
from evm_overlay.overlay import draw_overlay
from evm_overlay.pulse import PulseEstimator
from evm_overlay.roi import crop_roi
from evm_overlay.stream_writer import FfmpegRtspWriter

LOG = logging.getLogger(__name__)


def configure_opencl(enabled: bool) -> None:
    cv2.ocl.setUseOpenCL(bool(enabled))
    LOG.info("OpenCL requested=%s available=%s enabled=%s", enabled, cv2.ocl.haveOpenCL(), cv2.ocl.useOpenCL())


def run(config_path: str) -> int:
    cfg = load_config(config_path)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    configure_opencl(cfg.processing.use_opencl)

    capture = cv2.VideoCapture(cfg.input_url, cv2.CAP_FFMPEG)
    if not capture.isOpened():
        raise RuntimeError(f"could not open input stream: {cfg.input_url}")

    fps = cfg.processing.fps
    source_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    source_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    width = cfg.output.width or source_width
    height = cfg.output.height or source_height
    LOG.info("source size=%sx%s output size=%sx%s fps=%s", source_width, source_height, width, height, fps)
    writer = FfmpegRtspWriter(cfg.output_url, width, height, fps)

    estimator = PulseEstimator(
        fps=fps,
        min_bpm=cfg.processing.min_bpm,
        max_bpm=cfg.processing.max_bpm,
        window_seconds=cfg.processing.window_seconds,
    )
    evm_visualizer = EvmVisualizer(cfg.evm_visualization)
    last = 0.0
    while True:
        ok, frame = capture.read()
        if not ok:
            LOG.warning("input read failed; retrying")
            time.sleep(0.5)
            continue
        frame = resize_for_output(frame, cfg.output)
        roi = crop_roi(frame, cfg.roi)
        estimate = estimator.update(roi)
        evm_roi = evm_visualizer.update(roi)
        if estimate and time.monotonic() - last > 5:
            LOG.info("pulse bpm=%0.1f confidence=%0.2f samples=%s", estimate.bpm, estimate.confidence, estimate.samples)
            last = time.monotonic()
        output_frame = draw_evm_inset(frame, evm_roi, cfg.roi, cfg.evm_visualization)
        writer.write(draw_overlay(output_frame, estimate, cfg.overlay))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/config/config.yaml")
    args = parser.parse_args()
    raise SystemExit(run(args.config))


if __name__ == "__main__":
    main()
