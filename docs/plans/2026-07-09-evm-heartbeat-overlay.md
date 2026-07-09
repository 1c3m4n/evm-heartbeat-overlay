# EVM Heartbeat Overlay Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a Dockerized microservice that reads a Frigate/go2rtc camera restream, crops to a configured ROI, extracts an experimental EVM/rPPG pulse estimate, and publishes a new stream with overlay information.

**Architecture:** Frigate owns camera connections and exposes go2rtc restreams. This service consumes one restream, performs ROI-first processing to minimize CPU/GPU load, uses OpenCV/OpenCL where available on AMD, and writes an overlay stream plus future Home Assistant telemetry.

**Tech Stack:** Python 3.10+, OpenCV, NumPy, PyYAML, Docker, Unraid Docker XML template, AMD `/dev/dri` + `/dev/kfd` passthrough.

---

### Task 1: Establish tested project skeleton

**Objective:** Create a Python package with deterministic unit tests for config parsing, ROI cropping, and synthetic pulse estimation.

**Files:**
- Create: `pyproject.toml`
- Create: `src/evm_overlay/config.py`
- Create: `src/evm_overlay/roi.py`
- Create: `src/evm_overlay/pulse.py`
- Test: `tests/test_config.py`, `tests/test_roi.py`, `tests/test_pulse.py`

**Verification:**

```bash
uv run --extra dev pytest -q
# Expected: 3 passed
```

### Task 2: Add stream service loop

**Objective:** Add an executable service that opens RTSP input, applies ROI pulse estimation, draws an overlay, and writes an output stream.

**Files:**
- Create: `src/evm_overlay/service.py`
- Create: `src/evm_overlay/overlay.py`

**Verification:**

```bash
uv run python -m evm_overlay.service --config config.example.yaml
# Expected with fake URLs: clear RuntimeError for unavailable input stream.
# Expected with real go2rtc URLs: startup OpenCL log and output stream frames.
```

### Task 3: Add Docker and Unraid deployment assets

**Objective:** Provide container deployment files for Unraid with AMD GPU passthrough.

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `unraid/evm-heartbeat-overlay.xml`

**Verification:**

```bash
docker build -t evm-heartbeat-overlay:local .
docker run --rm --device=/dev/dri --device=/dev/kfd evm-heartbeat-overlay:local python3 - <<'PY'
import cv2
print(cv2.ocl.haveOpenCL(), cv2.ocl.useOpenCL())
PY
```

### Task 4: Replace simple rPPG with real EVM stage

**Objective:** Insert a Laplacian/Gaussian pyramid and temporal bandpass stage between ROI crop and pulse estimation.

**Files:**
- Create: `src/evm_overlay/evm.py`
- Test: `tests/test_evm.py`

**Implementation notes:**
- Start with CPU NumPy/OpenCV implementation.
- Add OpenCV `UMat` acceleration only after correctness tests pass.
- Test with synthetic modulated frames where the amplified component is known.

### Task 5: Add production telemetry

**Objective:** Publish non-video state for Home Assistant and observability.

**Files:**
- Create: `src/evm_overlay/mqtt.py`
- Create: `src/evm_overlay/health.py`
- Test: `tests/test_mqtt.py`, `tests/test_health.py`

**Metrics:**
- BPM estimate
- Confidence
- Signal/noise score
- Dropped frames
- OpenCL available/enabled

---

## Frigate/go2rtc deployment notes

- Prefer Frigate's built-in go2rtc restream as input so the camera sees one connection.
- Use a lower resolution/substream for this service if available.
- Keep ROI as small and stable as possible; EVM is sensitive to motion and lighting changes.
- Do not treat estimates as medical data; surface confidence and signal quality prominently.

## Unraid note

Unraid Community Applications Docker templates are XML, not YAML. The initial template is in `unraid/evm-heartbeat-overlay.xml`.
