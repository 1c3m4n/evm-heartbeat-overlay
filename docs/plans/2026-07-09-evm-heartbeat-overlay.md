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

### Task 4a: Implement bounded temporal-bandpass EVM core

**Objective:** Add a CPU-first signal EVM processor which applies a Gaussian/Laplacian pyramid and a bounded temporal bandpass filter to an ROI.

**Files:**
- Create: `src/evm_overlay/evm.py`
- Create: `tests/test_evm.py`

**Design constraints:**
- Downsample the ROI into a configurable pyramid level before temporal filtering.
- Use bounded rolling state; do not retain unbounded full-resolution frames.
- Preserve the original ROI shape on output.
- Support `enabled: false` as a transparent pass-through.
- Make temporal frequency limits explicit in config.

**TDD verification:**

```bash
uv run --extra dev pytest tests/test_evm.py -q
```

Tests must demonstrate: pass-through when disabled, synthetic in-band modulation is amplified, and out-of-band/static content is not amplified.

### Task 4b: Integrate signal EVM into the estimator pipeline

**Objective:** Route the configured ROI through the signal EVM stage before pulse estimation, while retaining the existing display EVM panel as an independent debug/visualization feature.

**Files:**
- Modify: `src/evm_overlay/config.py`
- Modify: `src/evm_overlay/service.py`
- Modify: `config.example.yaml`
- Test: `tests/test_config.py`

**TDD verification:**

```bash
uv run --extra dev pytest tests/test_config.py tests/test_evm.py -q
```

### Task 5a: Add shared runtime telemetry state and health endpoint

**Objective:** Publish a lightweight JSON endpoint with service liveness, stream counters, OpenCL state, and latest non-medical estimates.

**Files:**
- Create: `src/evm_overlay/health.py`
- Create: `tests/test_health.py`
- Modify: `src/evm_overlay/config.py`
- Modify: `src/evm_overlay/service.py`

**Required JSON fields:**

```text
status, frames_processed, dropped_frames, opencl_available, opencl_enabled,
pulse_bpm, pulse_confidence, breathing_bpm, breathing_confidence,
signal_quality, updated_at
```

**TDD verification:**

```bash
uv run --extra dev pytest tests/test_health.py -q
```

### Task 5b: Add optional Home Assistant MQTT discovery/state publishing

**Objective:** When explicitly configured, publish pulse/breathing state and Home Assistant MQTT discovery metadata without affecting users who do not configure MQTT.

**Files:**
- Create: `src/evm_overlay/mqtt.py`
- Create: `tests/test_mqtt.py`
- Modify: `pyproject.toml`
- Modify: `src/evm_overlay/config.py`
- Modify: `src/evm_overlay/service.py`
- Modify: `config.example.yaml`

**TDD verification:**

```bash
uv run --extra dev pytest tests/test_mqtt.py -q
```

### Task 6: Release verification

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
