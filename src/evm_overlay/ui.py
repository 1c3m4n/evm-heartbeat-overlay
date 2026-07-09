from __future__ import annotations

import json
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from evm_overlay.config import AppConfig, RoiConfig, load_config
from evm_overlay.snapshot import SnapshotStore


class ConfigController:
    def __init__(self, config_path: str | Path, config: AppConfig) -> None:
        self.config_path = Path(config_path)
        self._lock = threading.Lock()
        self._config = config

    def get_config(self) -> AppConfig:
        with self._lock:
            return self._config

    def snapshot(self) -> dict[str, Any]:
        cfg = self.get_config()
        return {
            "roi": _roi_dict(cfg.roi),
            "breathing_roi": _roi_dict(cfg.breathing_roi) if cfg.breathing_roi is not None else None,
            "output": {"width": cfg.output.width, "height": cfg.output.height},
            "yaml": self.config_path.read_text(encoding="utf-8"),
        }

    def update_rois(self, payload: dict[str, Any]) -> dict[str, Any]:
        roi = _parse_roi(payload.get("roi"), "roi") if "roi" in payload else self.get_config().roi
        if "breathing_roi" in payload and payload["breathing_roi"] is not None:
            breathing_roi = _parse_roi(payload.get("breathing_roi"), "breathing_roi")
        else:
            breathing_roi = self.get_config().breathing_roi

        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        data["roi"] = _roi_dict(roi)
        if breathing_roi is not None:
            data["breathing_roi"] = _roi_dict(breathing_roi)
        elif "breathing_roi" in data:
            del data["breathing_roi"]
        self.config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        with self._lock:
            self._config = replace(self._config, roi=roi, breathing_roi=breathing_roi)
        return self.snapshot()

    def replace_from_disk(self) -> AppConfig:
        cfg = load_config(self.config_path)
        with self._lock:
            self._config = cfg
        return cfg


def _roi_dict(roi: RoiConfig) -> dict[str, int]:
    return {"x": roi.x, "y": roi.y, "width": roi.width, "height": roi.height}


def _parse_roi(value: Any, name: str) -> RoiConfig:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return RoiConfig(x=int(value["x"]), y=int(value["y"]), width=int(value["width"]), height=int(value["height"]))


def make_ui_handler(controller: ConfigController, input_store: SnapshotStore, output_store: SnapshotStore):
    class UiHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/" or path == "/ui":
                self._send_bytes(ui_html().encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/config":
                self._send_json(controller.snapshot())
            elif path == "/input.jpg":
                self._send_jpeg(input_store)
            elif path == "/output.jpg":
                self._send_jpeg(output_store)
            else:
                self.send_error(404)

        def do_PUT(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path != "/api/rois":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                self._send_json(controller.update_rois(payload))
            except Exception as exc:  # noqa: BLE001 - report JSON API error
                self.send_error(400, str(exc))

        def _send_jpeg(self, store: SnapshotStore) -> None:
            jpeg = store.get_jpeg()
            if jpeg is None:
                self.send_error(503, "frame not ready")
                return
            self._send_bytes(jpeg, "image/jpeg")

        def _send_json(self, payload: dict[str, Any]) -> None:
            self._send_bytes(json.dumps(payload).encode("utf-8"), "application/json")

        def _send_bytes(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

    return UiHandler


def ui_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EVM Heartbeat Overlay</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#101418;color:#e6edf3}header{padding:16px 24px;background:#17202a}main{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px}.panel{background:#151b23;border:1px solid #30363d;border-radius:12px;padding:12px}.preview{position:relative;display:inline-block;max-width:100%}img{max-width:100%;border-radius:8px}canvas{position:absolute;inset:0;width:100%;height:100%;cursor:crosshair}.controls{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}label{font-size:12px;color:#9da7b1}input,select,button,textarea{background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:8px;padding:8px}button{cursor:pointer;background:#238636;border-color:#2ea043}.hint{color:#9da7b1;font-size:13px}textarea{width:100%;min-height:260px;font-family:ui-monospace,monospace}.full{grid-column:1/-1}.badge{display:inline-block;margin-left:8px;color:#9da7b1}</style>
</head>
<body>
<header><strong>EVM Heartbeat Overlay</strong><span id="status" class="badge">loading…</span></header>
<main>
<section class="panel"><h2>Input preview</h2><p class="hint">Choose ROI type, then drag a box over the input frame. Green = pulse ROI, blue = breathing ROI.</p><select id="roi-kind"><option value="roi">Pulse ROI</option><option value="breathing_roi">Breathing ROI</option></select><div class="preview"><img id="input-preview" src="/input.jpg"><canvas id="roi-canvas"></canvas></div></section>
<section class="panel"><h2>Output preview</h2><p class="hint">Processed stream snapshot with overlay.</p><img id="output-preview" src="/output.jpg"></section>
<section class="panel full"><h2>ROI boxes</h2><div class="controls" id="roi-controls"></div><p><button id="save-rois">Save ROI boxes live</button></p></section>
<section class="panel full"><h2>Current config</h2><p class="hint">ROI saves are live. For estimator band/config changes, edit YAML and restart the container.</p><textarea id="config-yaml" readonly></textarea></section>
</main>
<script>
const img=document.getElementById('input-preview'), canvas=document.getElementById('roi-canvas'), ctx=canvas.getContext('2d');
let cfg={roi:{x:0,y:0,width:1,height:1},breathing_roi:null,output:{width:null,height:null}}, drag=null;
function scale(){return {x:canvas.width/(cfg.output.width||img.naturalWidth||1), y:canvas.height/(cfg.output.height||img.naturalHeight||1)}}
function fit(){canvas.width=img.clientWidth;canvas.height=img.clientHeight;draw()}
function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);drawBox(cfg.roi,'#2ea043','Pulse'); if(cfg.breathing_roi) drawBox(cfg.breathing_roi,'#58a6ff','Breathing')}
function drawBox(r,color,label){const s=scale();ctx.strokeStyle=color;ctx.lineWidth=3;ctx.strokeRect(r.x*s.x,r.y*s.y,r.width*s.x,r.height*s.y);ctx.fillStyle=color;ctx.font='14px system-ui';ctx.fillText(label,r.x*s.x+5,r.y*s.y+18)}
function pointer(e){const rect=canvas.getBoundingClientRect(),s=scale();return {x:Math.round((e.clientX-rect.left)/s.x),y:Math.round((e.clientY-rect.top)/s.y)}}
canvas.onmousedown=e=>{drag=pointer(e)}; canvas.onmousemove=e=>{if(!drag)return; const p=pointer(e), kind=document.getElementById('roi-kind').value; cfg[kind]={x:Math.min(drag.x,p.x),y:Math.min(drag.y,p.y),width:Math.abs(p.x-drag.x),height:Math.abs(p.y-drag.y)}; renderControls(); draw()}; canvas.onmouseup=()=>{drag=null};
function renderControls(){const el=document.getElementById('roi-controls'); el.innerHTML=''; for(const kind of ['roi','breathing_roi']){const r=cfg[kind]||{x:0,y:0,width:0,height:0}; for(const k of ['x','y','width','height']){const wrap=document.createElement('label'); wrap.textContent=kind+'.'+k; const input=document.createElement('input'); input.type='number'; input.value=r[k]; input.oninput=()=>{cfg[kind]=cfg[kind]||{}; cfg[kind][k]=parseInt(input.value||0); draw()}; wrap.appendChild(input); el.appendChild(wrap)}}}
async function load(){const r=await fetch('/api/config'); cfg=await r.json(); document.getElementById('config-yaml').value=cfg.yaml; renderControls(); fit(); document.getElementById('status').textContent='ready'}
document.getElementById('save-rois').onclick=async()=>{const r=await fetch('/api/rois',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({roi:cfg.roi,breathing_roi:cfg.breathing_roi})}); cfg=await r.json(); document.getElementById('config-yaml').value=cfg.yaml; renderControls(); draw(); document.getElementById('status').textContent='saved'};
setInterval(()=>{document.getElementById('input-preview').src='/input.jpg?t='+Date.now();document.getElementById('output-preview').src='/output.jpg?t='+Date.now()},1000);
img.onload=fit; window.onresize=fit; load();
</script>
</body></html>"""



def start_ui_server(host: str, port: int, controller: ConfigController, input_store: SnapshotStore, output_store: SnapshotStore) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_ui_handler(controller, input_store, output_store))
    thread = threading.Thread(target=server.serve_forever, name="ui-http", daemon=True)
    thread.start()
    return server
