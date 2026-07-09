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
class OutputConfig:
    width: int | None = None
    height: int | None = None

    def __post_init__(self) -> None:
        if (self.width is None) != (self.height is None):
            raise ValueError("output.width and output.height must be set together")
        if self.width is not None and self.width <= 0:
            raise ValueError("output.width must be > 0")
        if self.height is not None and self.height <= 0:
            raise ValueError("output.height must be > 0")


@dataclass(frozen=True)
class OverlayConfig:
    enabled: bool = True
    label: str = "Pulse"
    position: tuple[int, int] = (24, 48)
    min_confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.min_confidence < 0 or self.min_confidence > 1:
            raise ValueError("overlay.min_confidence must be between 0 and 1")


@dataclass(frozen=True)
class EvmVisualizationConfig:
    enabled: bool = False
    alpha: float = 20.0
    learning_rate: float = 0.05
    mode: str = "inset"
    inset_scale: float = 0.5
    anchor: str = "near_roi"
    margin: int = 8
    border_color: tuple[int, int, int] = (0, 255, 255)

    def __post_init__(self) -> None:
        if self.alpha < 0:
            raise ValueError("evm_visualization.alpha must be >= 0")
        if not (0 < self.learning_rate <= 1):
            raise ValueError("evm_visualization.learning_rate must be in (0, 1]")
        if self.mode not in {"inset", "replace_roi", "off"}:
            raise ValueError("evm_visualization.mode must be inset, replace_roi, or off")
        if self.anchor not in {"near_roi", "bottom_right"}:
            raise ValueError("evm_visualization.anchor must be near_roi or bottom_right")
        if self.inset_scale <= 0:
            raise ValueError("evm_visualization.inset_scale must be > 0")


@dataclass(frozen=True)
class AppConfig:
    input_url: str
    output_url: str
    roi: RoiConfig
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    evm_visualization: EvmVisualizationConfig = field(default_factory=EvmVisualizationConfig)


def _expect_mapping(data: Any, name: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"{name} must be a mapping")
    return data


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    data = _expect_mapping(raw, "config")
    roi = RoiConfig(**_expect_mapping(data["roi"], "roi"))
    processing = ProcessingConfig(**data.get("processing", {}))
    output = OutputConfig(**data.get("output", {}))
    overlay_data = data.get("overlay", {})
    if "position" in overlay_data:
        overlay_data = {**overlay_data, "position": tuple(overlay_data["position"])}
    overlay = OverlayConfig(**overlay_data)
    evm_data = data.get("evm_visualization", {})
    if "border_color" in evm_data:
        evm_data = {**evm_data, "border_color": tuple(evm_data["border_color"])}
    evm_visualization = EvmVisualizationConfig(**evm_data)
    return AppConfig(
        input_url=str(data["input_url"]),
        output_url=str(data["output_url"]),
        roi=roi,
        processing=processing,
        output=output,
        overlay=overlay,
        evm_visualization=evm_visualization,
    )
