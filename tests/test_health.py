import json
from urllib.request import urlopen

from evm_overlay.health import RuntimeTelemetry, start_health_server


def test_runtime_telemetry_snapshot_contains_required_metrics():
    telemetry = RuntimeTelemetry(opencl_available=True, opencl_enabled=False)
    telemetry.record_frame(
        pulse_bpm=122.5,
        pulse_confidence=0.8,
        breathing_bpm=28.0,
        breathing_confidence=0.6,
    )
    telemetry.record_drop()

    snapshot = telemetry.snapshot()

    assert snapshot["status"] == "ok"
    assert snapshot["frames_processed"] == 1
    assert snapshot["dropped_frames"] == 1
    assert snapshot["opencl_available"] is True
    assert snapshot["opencl_enabled"] is False
    assert snapshot["pulse_bpm"] == 122.5
    assert snapshot["breathing_bpm"] == 28.0
    assert snapshot["signal_quality"] == 0.8
    assert snapshot["updated_at"] is not None


def test_health_server_serves_telemetry_json():
    telemetry = RuntimeTelemetry(opencl_available=True, opencl_enabled=True)
    telemetry.record_frame(pulse_bpm=100.0, pulse_confidence=0.5)
    server = start_health_server("127.0.0.1", 0, telemetry)
    try:
        port = server.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            payload = json.loads(response.read())

        assert response.status == 200
        assert payload["pulse_bpm"] == 100.0
        assert payload["opencl_enabled"] is True
    finally:
        server.shutdown()
        server.server_close()
