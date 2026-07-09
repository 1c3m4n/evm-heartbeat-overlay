# EVM Heartbeat Overlay Implementation Plan

> **For Hermes:** Execute remaining tasks using test-driven development and review each task for specification and code quality.

**Goal:** Build a Dockerized microservice that consumes a Frigate/go2rtc restream, estimates experimental pulse and respiration information from a configured ROI, shows a subtle-motion EVM visualization, and exposes stream plus non-video telemetry for Home Assistant.

**Architecture:** Frigate/go2rtc owns camera connections. The service consumes one restream, processes an ROI first, and publishes frames through MediaMTX. The display EVM panel and the signal-processing EVM stage are distinct: display EVM makes subtle motion visible; signal EVM filters a Gaussian/Laplacian pyramid band before pulse estimation. A small in-process state store feeds an HTTP health endpoint and optional Home Assistant-facing telemetry.

**Tech Stack:** Python 3.10+, OpenCV, NumPy, PyYAML, Docker, MediaMTX, HTTP stdlib server, AMD `/dev/dri` + `/dev/kfd` passthrough.

---

## Completed work

### Task 1: Tested project skeleton — complete

Implemented configuration parsing, ROI handling, synthetic pulse estimation, and a Pytest suite.

### Task 2: RTSP stream service — complete

Implemented ingest, output publishing with ffmpeg, snapshot endpoint, skin/IR candidate masks, pulse/breathing overlays, and a configurable subtle-motion visualization.

### Task 3: Docker / Unraid deployment assets — complete

Implemented Docker image and local MediaMTX testing workflow. The published image is currently:

```text
ghcr.io/1c3m4n/evm-heartbeat-overlay:v1
```

### Configuration and documentation — complete

Runtime configuration is grouped into `streams`, `roi`, `capture`, `vitals`, `skin_detection`, and `output`. README contains the local Docker run and verification workflow.

---

## Remaining work

### Task 4a: Implement bounded temporal-bandpass EVM core — complete

Implemented `TemporalPyramidEvm`: a CPU-first Laplacian-pyramid stage with cascaded temporal low-pass filters that form a bounded temporal band-pass signal. Unit tests cover pass-through mode, in-band amplification, and high-frequency rejection.

### Task 4b: Integrate signal EVM into the estimator pipeline — complete

Added `vitals.signal_evm` configuration and routed the estimation ROI through the signal EVM stage before pulse estimation. The existing `output.evm` panel remains a separate display/debug feature.

### Task 5a: Add shared runtime telemetry state and health endpoint — complete

Implemented `RuntimeTelemetry` and `output.health`. `GET /health` now returns service liveness, frame/drop counters, OpenCL state, latest rates/confidence, signal quality, and an update timestamp.

### Task 5b: Add optional Home Assistant MQTT discovery/state publishing — complete

Implemented optional `telemetry.mqtt`. When enabled, the service publishes Home Assistant MQTT discovery for pulse, breathing, confidence, and signal-quality sensors, then publishes the latest telemetry state at the configured interval. MQTT remains disabled by default.

### Task 6: Release verification — in progress

**Objective:** Verify the complete service locally, then publish a new GHCR version tag and update README usage if required.

**Verification:**

```bash
uv run --extra dev pytest -q
docker build -t evm-heartbeat-overlay:local .
# start local MediaMTX and service using config.local.yaml
docker logs --tail 100 evm-heartbeat-overlay-test
curl -sS http://127.0.0.1:8088/health
curl -sS -o /tmp/snapshot.jpg http://127.0.0.1:8088/snapshot.jpg
file /tmp/snapshot.jpg
```

---

## Safety and deployment notes

- Prefer Frigate's built-in go2rtc restream as input so the camera sees one connection.
- Use a low-resolution substream where available and a stable ROI.
- Treat pulse and breathing estimates as experimental signal-quality data, never medical monitoring.
- Keep MQTT disabled by default and do not commit broker credentials into tracked config files.
