# EVM Heartbeat Overlay

Experimental RTSP microservice that reads a Frigate/go2rtc restream, estimates pulse and breathing from a configured region of interest (ROI), renders a subtle-motion EVM panel, and publishes a new RTSP stream plus an HTTP JPEG snapshot.

> **Not medical software.** Pulse and respiration output is experimental visual telemetry only. Do not use it to monitor a child's safety, diagnose a condition, or make medical decisions.

## Architecture

```text
Camera -> Frigate -> go2rtc restream -> EVM container -> MediaMTX -> RTSP consumers
                                      |                    |
                                      |                    +-> Home Assistant / Frigate
                                      +-> JPEG snapshot endpoint
```

Use a Frigate/go2rtc restream as the input whenever possible. It avoids opening an additional connection to the physical camera.

## Configuration

Start from the documented example:

```bash
cp config.example.yaml config.local.yaml
```

`config.local.yaml` is ignored by Git, so it is the place for actual camera URLs, IPs, and credentials.

### Section overview

| Section | Purpose |
| --- | --- |
| `streams` | RTSP input restream and published RTSP output URL. |
| `roi` | Pixel rectangle used for pulse and breathing estimation. Coordinates are relative to `output.video`. |
| `capture` | Processing frame rate and OpenCL request. |
| `vitals.pulse` / `vitals.breathing` | Physiological frequency bands, windows, and confidence/motion gates. |
| `skin_detection` | Visible-light/IR skin candidate mask for pulse estimation. |
| `telemetry.mqtt` | Optional Home Assistant MQTT discovery and periodic state publishing. Disabled by default. |
| `output.video` / `output.snapshot` / `output.health` | Published resolution, HTTP snapshot, and JSON health/metrics endpoint. |
| `output.overlay` | Display toggle, rate confidence threshold, position, and both on-frame rate labels. |
| `output.evm` | EVM panel appearance, subtle-motion filtering, and display denoising. |

The complete list and tuning comments are in [`config.example.yaml`](config.example.yaml).

Key display labels are intentionally configurable:

```yaml
output:
  overlay:
    pulse_label: Pulse
    breathing_label: Breathing
  evm:
    label: Subtle motion
```

### Optional Home Assistant MQTT telemetry

Set `telemetry.mqtt.enabled: true` only after adding your broker host and credentials to ignored `config.local.yaml`. On startup, the service publishes Home Assistant MQTT discovery for pulse, breathing, confidence, and signal-quality sensors, then sends one state update every configured interval.

```yaml
telemetry:
  mqtt:
    enabled: true
    host: 192.168.1.10
    username: your_mqtt_user
    password: your_mqtt_password
    topic_prefix: nursery_evm
```

## Local Docker test

These commands create a local MediaMTX relay, build the image, and run the service against `config.local.yaml`.

### 1. Prepare the local config

Set your actual input and output endpoints. The output hostname must be resolvable **inside** the container; when using the relay command below, keep the MediaMTX container hostname:

```yaml
streams:
  input_url: rtsp://YOUR_FRIGATE_HOST:8554/YOUR_RESTREAM
  output_url: rtsp://evm-mediamtx:8554/evm-overlay
```

### 2. Create the test relay and get the image

Use the published `v2` image for local testing. The current GitHub Container Registry package is private, so authenticate once before pulling it:

```bash
echo "$(gh auth token)" | docker login ghcr.io -u 1c3m4n --password-stdin
```

```bash
docker network create evm-test 2>/dev/null || true

docker rm -f evm-mediamtx 2>/dev/null || true
docker run -d --name evm-mediamtx --network evm-test \
  -p 8554:8554 \
  bluenviron/mediamtx:latest

docker pull ghcr.io/1c3m4n/evm-heartbeat-overlay:v2
```

To test unpushed local code instead, build a local image and replace the final image name in the run command with `evm-heartbeat-overlay:local`:

```bash
docker build -t evm-heartbeat-overlay:local .
```

### 3. Run the processor

Replace `192.168.1.32` with the LAN IP of the Frigate/go2rtc host when its `.local` name is not resolvable inside Docker. Remove the AMD device arguments when testing on a system without AMD/ROCm access.

```bash
docker rm -f evm-heartbeat-overlay-test 2>/dev/null || true

docker run -d --name evm-heartbeat-overlay-test \
  --network evm-test \
  --add-host 1c4.local:192.168.1.32 \
  --device=/dev/dri \
  --device=/dev/kfd \
  --group-add video \
  --group-add render \
  --security-opt seccomp=unconfined \
  -p 8088:8088 \
  -p 8089:8089 \
  -v "$PWD/config.local.yaml:/config/config.yaml:ro" \
  ghcr.io/1c3m4n/evm-heartbeat-overlay:v2
```

### 4. Verify all layers

```bash
docker ps --filter name=evm- \
  --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

docker logs --tail 100 evm-heartbeat-overlay-test

curl -sS --max-time 5 -o /tmp/evm-snapshot.jpg \
  http://127.0.0.1:8088/snapshot.jpg
file /tmp/evm-snapshot.jpg

curl -sS http://127.0.0.1:8089/health

timeout 10 ffprobe -v error -rtsp_transport tcp \
  -select_streams v:0 \
  -show_entries stream=codec_name,width,height,avg_frame_rate \
  -of default=nw=1 \
  rtsp://127.0.0.1:8554/evm-overlay
```

For LAN consumers, replace `127.0.0.1` with the Docker host's LAN IP:

```text
RTSP:     rtsp://HOST_LAN_IP:8554/evm-overlay
Snapshot: http://HOST_LAN_IP:8088/snapshot.jpg
Health:   http://HOST_LAN_IP:8089/health
```

In Home Assistant Generic Camera, use the HTTP endpoint as **Still Image URL** and the RTSP endpoint as **Stream Source URL**.

## Development

```bash
uv run --extra dev pytest -q
```

## AMD GPU / OpenCL notes

The Docker command passes both AMD render paths:

- `/dev/dri` for DRM/render access
- `/dev/kfd` for ROCm/HSA access

Startup logs include:

```text
OpenCL requested=True available=<bool> enabled=<bool>
```

If `available=False`, the service can still run on CPU.

## Tuning notes

- Start with a narrow, stable ROI containing exposed skin or a visibly moving chest/torso area.
- The breathing estimate needs the configured window of usable frames before it appears; the example uses 30 seconds.
- `output.evm.subtle_max_delta` rejects large movement from amplification. Lower it to ignore more movement; raise it to admit more motion.
- `denoise_spatial_kernel: 5` and `denoise_temporal_alpha: 0.35` provide moderate smoothing. A lower temporal alpha is calmer but adds delay.
- In IR/night mode, `skin_detection.preset: auto` switches from color thresholds to grayscale-luminance candidates.
