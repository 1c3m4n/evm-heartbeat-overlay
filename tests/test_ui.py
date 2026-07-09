import json
from urllib.request import Request, urlopen

import numpy as np
import yaml

from evm_overlay.config import load_config
from evm_overlay.snapshot import SnapshotStore
from evm_overlay.ui import ConfigController, start_ui_server, ui_html


def _write_config(path):
    path.write_text(
        """
streams:
  input_url: rtsp://camera/input
  output_url: rtsp://relay/output
roi:
  x: 10
  y: 20
  width: 120
  height: 80
breathing_roi:
  x: 30
  y: 40
  width: 200
  height: 120
capture:
  fps: 15
vitals:
  breathing:
    min_bpm: 15
    max_bpm: 70
output:
  video:
    width: 640
    height: 360
  ui:
    enabled: true
    host: 127.0.0.1
    port: 0
""",
        encoding="utf-8",
    )


def test_ui_api_returns_config_and_updates_roi_boxes(tmp_path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path)
    controller = ConfigController(config_path, load_config(config_path))
    input_store = SnapshotStore()
    output_store = SnapshotStore()
    input_store.update(np.zeros((12, 16, 3), dtype=np.uint8))
    output_store.update(np.zeros((12, 16, 3), dtype=np.uint8))
    server = start_ui_server("127.0.0.1", 0, controller, input_store, output_store)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        cfg_payload = json.loads(urlopen(f"{base}/api/config", timeout=5).read())
        assert cfg_payload["roi"] == {"x": 10, "y": 20, "width": 120, "height": 80}
        assert cfg_payload["breathing_roi"] == {"x": 30, "y": 40, "width": 200, "height": 120}
        assert cfg_payload["output"] == {"width": 640, "height": 360}

        body = json.dumps(
            {
                "roi": {"x": 11, "y": 22, "width": 123, "height": 82},
                "breathing_roi": {"x": 33, "y": 44, "width": 210, "height": 130},
            }
        ).encode()
        req = Request(f"{base}/api/rois", data=body, method="PUT", headers={"Content-Type": "application/json"})
        updated = json.loads(urlopen(req, timeout=5).read())
        assert updated["roi"]["x"] == 11
        assert updated["breathing_roi"]["width"] == 210

        reloaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert reloaded["roi"] == {"x": 11, "y": 22, "width": 123, "height": 82}
        assert reloaded["breathing_roi"] == {"x": 33, "y": 44, "width": 210, "height": 130}
        assert controller.get_config().roi.x == 11
        assert controller.get_config().breathing_roi.width == 210
    finally:
        server.shutdown()
        server.server_close()


def test_ui_page_contains_preview_images_and_roi_canvas():
    html = ui_html()

    assert "input-preview" in html
    assert "output-preview" in html
    assert "roi-canvas" in html
    assert "save-rois" in html
