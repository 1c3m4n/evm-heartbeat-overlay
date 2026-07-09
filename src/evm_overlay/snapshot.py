from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np

from evm_overlay.config import SnapshotConfig


class SnapshotStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jpeg: bytes | None = None

    def update(self, frame: np.ndarray) -> None:
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            return
        with self._lock:
            self._jpeg = encoded.tobytes()

    def get_jpeg(self) -> bytes | None:
        with self._lock:
            return self._jpeg


def make_snapshot_handler(store: SnapshotStore, path: str):
    class SnapshotHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server API name
            if self.path != path:
                self.send_error(404)
                return
            jpeg = store.get_jpeg()
            if jpeg is None:
                self.send_error(503, "snapshot not ready")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpeg)))
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.end_headers()
            self.wfile.write(jpeg)

        def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
            return

    return SnapshotHandler


def start_snapshot_server(config: SnapshotConfig, store: SnapshotStore) -> ThreadingHTTPServer | None:
    if not config.enabled:
        return None
    server = ThreadingHTTPServer((config.host, config.port), make_snapshot_handler(store, config.path))
    thread = threading.Thread(target=server.serve_forever, name="snapshot-http", daemon=True)
    thread.start()
    return server
