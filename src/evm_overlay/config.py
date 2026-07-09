from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RoiConfig:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        for name in ("x", "y", "width", "height"):
            value = getattr(self, name)
            if not isinstance(value, int):
                raise TypeError(f"roi.{name} must be an integer")
        if self.x < 0 or self.y < 0:
            raise ValueError("roi.x and roi.y must be >= 0")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("roi.width and roi.height must be > 0")

    def as_slice(self) -> tuple[slice, slice]:
        return (slice(self.y, self.y + self.height), slice(self.x, self.x + self.width))


@dataclass(frozen=True)
class ProcessingConfig:
    fps: int = 15
    min_bpm: int = 80
    max_bpm: int = 200
    window_seconds: int = 12
    use_opencl: bool = True


@dataclass(frozen=True)
class OverlayConfig:
    enabled: bool = True
    label: str = "Pulse"
    position: tuple[int, int] = (24, 48)


@dataclass(frozen=True)
class AppConfig:
    input_url: str
    output_url: str
    roi: RoiConfig
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)


def _expect_mapping(data: Any, name: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"{name} must be a mapping")
    return data


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    data = _expect_mapping(raw, "config")
    roi = RoiConfig(**_expect_mapping(data["roi"], "roi"))
    processing = ProcessingConfig(**data.get("processing", {}))
    overlay_data = data.get("overlay", {})
    if "position" in overlay_data:
        overlay_data = {**overlay_data, "position": tuple(overlay_data["position"])}
    overlay = OverlayConfig(**overlay_data)
    return AppConfig(
        input_url=str(data["input_url"]),
        output_url=str(data["output_url"]),
        roi=roi,
        processing=processing,
        overlay=overlay,
    )
