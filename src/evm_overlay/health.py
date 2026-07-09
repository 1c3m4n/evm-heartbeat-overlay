from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class RuntimeTelemetry:
    """Thread-safe latest-state and counters for health/observability."""

    def __init__(self, *, opencl_available: bool, opencl_enabled: bool) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, object] = {
            "frames_processed": 0,
            "dropped_frames": 0,
            "opencl_available": opencl_available,
            "opencl_enabled": opencl_enabled,
            "pulse_bpm": None,
            "pulse_confidence": None,
            "breathing_bpm": None,
            "breathing_confidence": None,
            "updated_at": None,
        }

    def record_frame(
        self,
        *,
        pulse_bpm: float | None = None,
        pulse_confidence: float | None = None,
        breathing_bpm: float | None = None,
        breathing_confidence: float | None = None,
    ) -> None:
        with self._lock:
            self._data["frames_processed"] = int(self._data["frames_processed"]) + 1
            if pulse_bpm is not None:
                self._data["pulse_bpm"] = pulse_bpm
                self._data["pulse_confidence"] = pulse_confidence
            if breathing_bpm is not None:
                self._data["breathing_bpm"] = breathing_bpm
                self._data["breathing_confidence"] = breathing_confidence
            self._data["updated_at"] = datetime.now(UTC).isoformat()

    def record_drop(self) -> None:
        with self._lock:
            self._data["dropped_frames"] = int(self._data["dropped_frames"]) + 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            data = dict(self._data)
        confidences = [value for value in (data["pulse_confidence"], data["breathing_confidence"]) if value is not None]
        data["signal_quality"] = max(confidences, default=0.0)
        data["status"] = "ok" if data["updated_at"] is not None else "starting"
        return data


def start_health_server(host: str, port: int, telemetry: RuntimeTelemetry) -> ThreadingHTTPServer:
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/health":
                self.send_error(404)
                return
            body = json.dumps(telemetry.snapshot()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True, name="health-server").start()
    return server
