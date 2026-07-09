from __future__ import annotations

import argparse
import logging
import time

import cv2

from evm_overlay.config import load_config
from evm_overlay.breathing import BreathingEstimator
from evm_overlay.evm import TemporalPyramidEvm
from evm_overlay.evm_visualization import EvmVisualizer, compute_evm_inset_rect, draw_evm_inset
from evm_overlay.frame_processing import resize_for_output
from evm_overlay.health import RuntimeTelemetry, start_health_server
from evm_overlay.mqtt import connect_publisher
from evm_overlay.overlay import draw_overlay
from evm_overlay.pulse import PulseEstimator
from evm_overlay.roi import crop_roi
from evm_overlay.snapshot import SnapshotStore, start_snapshot_server
from evm_overlay.skin_detection import apply_mask_visualization, make_skin_mask
from evm_overlay.stream_writer import FfmpegRtspWriter

LOG = logging.getLogger(__name__)


def crop_breathing_roi(frame, cfg):
    return crop_roi(frame, cfg.breathing_roi or cfg.roi)


def configure_opencl(enabled: bool) -> tuple[bool, bool]:
    cv2.ocl.setUseOpenCL(bool(enabled))
    available = bool(cv2.ocl.haveOpenCL())
    active = bool(cv2.ocl.useOpenCL())
    LOG.info("OpenCL requested=%s available=%s enabled=%s", enabled, available, active)
    return available, active


def run(config_path: str) -> int:
    cfg = load_config(config_path)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    opencl_available, opencl_enabled = configure_opencl(cfg.processing.use_opencl)
    telemetry = RuntimeTelemetry(opencl_available=opencl_available, opencl_enabled=opencl_enabled)

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
    snapshot_store = SnapshotStore()
    snapshot_server = start_snapshot_server(cfg.snapshot, snapshot_store)
    if snapshot_server is not None:
        LOG.info("snapshot server listening on http://%s:%s%s", cfg.snapshot.host, cfg.snapshot.port, cfg.snapshot.path)
    health_server = start_health_server(cfg.health.host, cfg.health.port, telemetry) if cfg.health.enabled else None
    if health_server is not None:
        LOG.info("health server listening on http://%s:%s/health", cfg.health.host, cfg.health.port)
    mqtt_publisher = None
    if cfg.mqtt.enabled:
        try:
            mqtt_publisher = connect_publisher(cfg.mqtt)
            LOG.info("MQTT telemetry enabled for %s:%s", cfg.mqtt.host, cfg.mqtt.port)
        except Exception:
            LOG.exception("MQTT setup failed; continuing without MQTT telemetry")

    estimator = PulseEstimator(
        fps=fps,
        min_bpm=cfg.processing.min_bpm,
        max_bpm=cfg.processing.max_bpm,
        window_seconds=cfg.processing.window_seconds,
        min_masked_pixels=cfg.skin_detection.min_pixels,
    )
    evm_visualizer = EvmVisualizer(cfg.evm_visualization)
    signal_evm = TemporalPyramidEvm(
        fps=fps,
        low_hz=cfg.signal_evm.low_hz,
        high_hz=cfg.signal_evm.high_hz,
        alpha=cfg.signal_evm.alpha,
        pyramid_level=cfg.signal_evm.pyramid_level,
        enabled=cfg.signal_evm.enabled,
    )
    breathing_estimator = BreathingEstimator(
        fps=fps,
        min_bpm=cfg.breathing.min_bpm,
        max_bpm=cfg.breathing.max_bpm,
        window_seconds=cfg.breathing.window_seconds,
        max_signal_delta=cfg.breathing.max_signal_delta,
    )
    last = 0.0
    last_mqtt_publish = 0.0
    while True:
        ok, frame = capture.read()
        if not ok:
            telemetry.record_drop()
            LOG.warning("input read failed; retrying")
            time.sleep(0.5)
            continue
        frame = resize_for_output(frame, cfg.output)
        roi = crop_roi(frame, cfg.roi)
        signal_roi = signal_evm.update(roi)
        skin_mask = make_skin_mask(roi, cfg.skin_detection)
        estimate = estimator.update(signal_roi, mask=skin_mask)
        breathing_frame = crop_breathing_roi(frame, cfg)
        breathing_estimate = breathing_estimator.update(breathing_frame) if cfg.breathing.enabled else None
        if breathing_estimate is not None and breathing_estimate.confidence < cfg.breathing.min_confidence:
            breathing_estimate = None
        evm_source = frame if cfg.evm_visualization.source == "frame" else roi
        evm_mask = None if cfg.evm_visualization.subtle_only else make_skin_mask(evm_source, cfg.skin_detection)
        evm_roi = evm_visualizer.update(evm_source, mask=evm_mask)
        if cfg.skin_detection.enabled and cfg.skin_detection.visualize and evm_mask is not None:
            evm_roi = apply_mask_visualization(evm_roi, evm_mask)
        if estimate and time.monotonic() - last > 5:
            LOG.info("pulse bpm=%0.1f confidence=%0.2f samples=%s", estimate.bpm, estimate.confidence, estimate.samples)
            last = time.monotonic()
        evm_rect = compute_evm_inset_rect(frame, evm_roi, cfg.roi, cfg.evm_visualization)
        output_frame = draw_evm_inset(frame, evm_roi, cfg.roi, cfg.evm_visualization)
        pulse_position = (evm_rect[0], max(32, evm_rect[1] - 52)) if cfg.evm_visualization.enabled else None
        output_frame = draw_overlay(output_frame, estimate, cfg.overlay, position=pulse_position, breathing=breathing_estimate)
        telemetry.record_frame(
            pulse_bpm=estimate.bpm if estimate else None,
            pulse_confidence=estimate.confidence if estimate else None,
            breathing_bpm=breathing_estimate.bpm if breathing_estimate else None,
            breathing_confidence=breathing_estimate.confidence if breathing_estimate else None,
        )
        if mqtt_publisher is not None and time.monotonic() - last_mqtt_publish >= cfg.mqtt.publish_interval_seconds:
            try:
                mqtt_publisher.publish_state(telemetry.snapshot())
                last_mqtt_publish = time.monotonic()
            except Exception:
                LOG.exception("MQTT state publish failed")
        snapshot_store.update(output_frame)
        writer.write(output_frame)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/config/config.yaml")
    args = parser.parse_args()
    raise SystemExit(run(args.config))


if __name__ == "__main__":
    main()
