# EVM Heartbeat Overlay

Prototype microservice for extracting a remote photoplethysmography / Eulerian Video Magnification signal from a Frigate/go2rtc camera stream and publishing a new stream with an on-frame pulse overlay.

> Not medical software. Treat output as experimental presence/vitals signal quality telemetry, not a clinical heart-rate monitor.

## Architecture

```text
Camera -> Frigate -> built-in go2rtc restream -> this container -> RTSP/WebRTC output stream
                                      \-> ROI crop -> green-channel rPPG/EVM -> BPM estimate -> overlay
```

Recommended first deployment path:

1. In Frigate, enable/reuse a low-load go2rtc restream for the camera.
2. Point `input_url` at that restream, not the physical camera, so this service does not add another camera connection.
3. Crop the ROI aggressively to the crib/bed/mattress area before any EVM math.
4. Pass AMD devices into Docker: `/dev/dri` and `/dev/kfd`.
5. Enable OpenCL in config; the service logs whether OpenCV sees OpenCL.

## Quick start

```bash
uv run --extra dev pytest -q
uv run python -m evm_overlay.service --config config.example.yaml
```

For a real camera, copy the example config and point it to Frigate/go2rtc:

```bash
cp config.example.yaml config.yaml
# edit input_url/output_url/roi
```

Example URLs:

```yaml
input_url: rtsp://1c4.local:8554/nursery
output_url: rtsp://1c4.local:8554/nursery-heart
```

## AMD GPU / OpenCL notes

The container template passes both AMD render nodes:

- `/dev/dri` for DRM/render access
- `/dev/kfd` for ROCm/HSA access

At startup, logs include:

```text
OpenCL requested=True available=<bool> enabled=<bool>
```

If `available=False`, the container can still run on CPU while you adjust the Unraid AMD/ROCm/OpenCL runtime pieces.

## Roadmap

- [x] Config loading, ROI crop, synthetic pulse estimator tests.
- [x] Initial RTSP ingest/output service skeleton.
- [x] Unraid Docker template draft.
- [ ] Add Laplacian pyramid + temporal bandpass EVM stage.
- [ ] Add face/skin/bed-surface ROI calibration UI or snapshot tool.
- [ ] Publish Home Assistant MQTT sensor alongside video overlay.
- [ ] Add Prometheus/health endpoint for signal quality and dropped frames.
