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
class BreathingConfig:
    enabled: bool = True
    min_bpm: int = 8
    max_bpm: int = 35
    window_seconds: int = 30
    max_signal_delta: float = 20.0
    min_confidence: float = 0.0

    def __post_init__(self) -> None:
        if not (0 < self.min_bpm < self.max_bpm):
            raise ValueError("breathing.min_bpm must be > 0 and lower than breathing.max_bpm")
        if self.window_seconds <= 0:
            raise ValueError("breathing.window_seconds must be > 0")
        if self.max_signal_delta <= 0:
            raise ValueError("breathing.max_signal_delta must be > 0")
        if self.min_confidence < 0 or self.min_confidence > 1:
            raise ValueError("breathing.min_confidence must be between 0 and 1")


@dataclass(frozen=True)
class SignalEvmConfig:
    enabled: bool = False
    low_hz: float = 0.7
    high_hz: float = 2.5
    alpha: float = 8.0
    pyramid_level: int = 1

    def __post_init__(self) -> None:
        if not (0 < self.low_hz < self.high_hz):
            raise ValueError("vitals.signal_evm low_hz must be > 0 and lower than high_hz")
        if self.alpha < 0:
            raise ValueError("vitals.signal_evm.alpha must be >= 0")
        if self.pyramid_level < 0:
            raise ValueError("vitals.signal_evm.pyramid_level must be >= 0")


@dataclass(frozen=True)
class MqttConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    discovery_prefix: str = "homeassistant"
    topic_prefix: str = "evm_heartbeat_overlay"
    device_name: str = "EVM Heartbeat Overlay"
    publish_interval_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.port <= 0 or self.port > 65535:
            raise ValueError("telemetry.mqtt.port must be a valid TCP port")
        if self.publish_interval_seconds <= 0:
            raise ValueError("telemetry.mqtt.publish_interval_seconds must be > 0")


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
class SnapshotConfig:
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8088
    path: str = "/snapshot.jpg"

    def __post_init__(self) -> None:
        if self.port <= 0 or self.port > 65535:
            raise ValueError("snapshot.port must be a valid TCP port")
        if not self.path.startswith("/"):
            raise ValueError("snapshot.path must start with /")


@dataclass(frozen=True)
class HealthConfig:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8089

    def __post_init__(self) -> None:
        if self.port <= 0 or self.port > 65535:
            raise ValueError("health.port must be a valid TCP port")


@dataclass(frozen=True)
class SkinDetectionConfig:
    enabled: bool = False
    preset: str = "auto"
    min_pixels: int = 250
    visualize: bool = False
    ir_luma_min: int = 35
    ir_luma_max: int = 245
    ir_grayscale_tolerance: int = 18

    def __post_init__(self) -> None:
        if self.preset not in {"auto", "light", "broad", "ir"}:
            raise ValueError("skin_detection.preset must be auto, light, broad, or ir")
        if self.min_pixels < 0:
            raise ValueError("skin_detection.min_pixels must be >= 0")
        if not (0 <= self.ir_luma_min < self.ir_luma_max <= 255):
            raise ValueError("skin_detection.ir_luma_min/max must be within 0..255 and ordered")
        if self.ir_grayscale_tolerance < 0:
            raise ValueError("skin_detection.ir_grayscale_tolerance must be >= 0")


@dataclass(frozen=True)
class OverlayConfig:
    enabled: bool = True
    pulse_label: str = "Pulse"
    breathing_label: str = "Breathing"
    position: tuple[int, int] = (24, 48)
    min_confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.min_confidence < 0 or self.min_confidence > 1:
            raise ValueError("overlay.min_confidence must be between 0 and 1")


@dataclass(frozen=True)
class EvmVisualizationConfig:
    enabled: bool = False
    label: str = "EVM"
    alpha: float = 20.0
    learning_rate: float = 0.05
    mode: str = "inset"
    source: str = "roi"
    inset_scale: float = 0.5
    anchor: str = "near_roi"
    margin: int = 8
    border_color: tuple[int, int, int] = (0, 255, 255)
    subtle_only: bool = False
    subtle_min_delta: float = 0.0
    subtle_max_delta: float = 12.0
    denoise_spatial_kernel: int = 0
    denoise_temporal_alpha: float = 1.0

    def __post_init__(self) -> None:
        if self.alpha < 0:
            raise ValueError("evm_visualization.alpha must be >= 0")
        if not (0 < self.learning_rate <= 1):
            raise ValueError("evm_visualization.learning_rate must be in (0, 1]")
        if self.mode not in {"inset", "replace_roi", "off"}:
            raise ValueError("evm_visualization.mode must be inset, replace_roi, or off")
        if self.source not in {"roi", "frame"}:
            raise ValueError("evm_visualization.source must be roi or frame")
        if self.anchor not in {"near_roi", "bottom_right"}:
            raise ValueError("evm_visualization.anchor must be near_roi or bottom_right")
        if self.inset_scale <= 0:
            raise ValueError("evm_visualization.inset_scale must be > 0")
        if self.subtle_min_delta < 0 or self.subtle_max_delta <= self.subtle_min_delta:
            raise ValueError("evm_visualization subtle delta range must be >= 0 and ordered")
        if self.denoise_spatial_kernel < 0 or self.denoise_spatial_kernel % 2 == 0 and self.denoise_spatial_kernel != 0:
            raise ValueError("evm_visualization.denoise_spatial_kernel must be 0 or a positive odd integer")
        if not 0 < self.denoise_temporal_alpha <= 1:
            raise ValueError("evm_visualization.denoise_temporal_alpha must be in (0, 1]")


@dataclass(frozen=True)
class AppConfig:
    input_url: str
    output_url: str
    roi: RoiConfig
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    signal_evm: SignalEvmConfig = field(default_factory=SignalEvmConfig)
    breathing: BreathingConfig = field(default_factory=BreathingConfig)
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    snapshot: SnapshotConfig = field(default_factory=SnapshotConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    skin_detection: SkinDetectionConfig = field(default_factory=SkinDetectionConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    evm_visualization: EvmVisualizationConfig = field(default_factory=EvmVisualizationConfig)


def _expect_mapping(data: Any, name: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"{name} must be a mapping")
    return data


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    data = _expect_mapping(raw, "config")
    streams = _expect_mapping(data["streams"], "streams")
    roi = RoiConfig(**_expect_mapping(data["roi"], "roi"))
    capture = _expect_mapping(data.get("capture", {}), "capture")
    vitals = _expect_mapping(data.get("vitals", {}), "vitals")
    pulse = _expect_mapping(vitals.get("pulse", {}), "vitals.pulse")
    signal_evm_data = _expect_mapping(vitals.get("signal_evm", {}), "vitals.signal_evm")
    breathing_data = _expect_mapping(vitals.get("breathing", {}), "vitals.breathing")
    processing = ProcessingConfig(
        fps=capture.get("fps", ProcessingConfig.fps),
        use_opencl=capture.get("use_opencl", ProcessingConfig.use_opencl),
        **pulse,
    )
    breathing = BreathingConfig(**breathing_data)
    signal_evm = SignalEvmConfig(**signal_evm_data)
    telemetry = _expect_mapping(data.get("telemetry", {}), "telemetry")
    mqtt = MqttConfig(**_expect_mapping(telemetry.get("mqtt", {}), "telemetry.mqtt"))
    output_group = _expect_mapping(data.get("output", {}), "output")
    output = OutputConfig(**_expect_mapping(output_group.get("video", {}), "output.video"))
    snapshot = SnapshotConfig(**_expect_mapping(output_group.get("snapshot", {}), "output.snapshot"))
    health = HealthConfig(**_expect_mapping(output_group.get("health", {}), "output.health"))
    skin_detection = SkinDetectionConfig(**data.get("skin_detection", {}))
    overlay_data = _expect_mapping(output_group.get("overlay", {}), "output.overlay")
    if "position" in overlay_data:
        overlay_data = {**overlay_data, "position": tuple(overlay_data["position"])}
    overlay = OverlayConfig(**overlay_data)
    evm_data = _expect_mapping(output_group.get("evm", {}), "output.evm")
    if "border_color" in evm_data:
        evm_data = {**evm_data, "border_color": tuple(evm_data["border_color"])}
    evm_visualization = EvmVisualizationConfig(**evm_data)
    return AppConfig(
        input_url=str(streams["input_url"]),
        output_url=str(streams["output_url"]),
        roi=roi,
        processing=processing,
        signal_evm=signal_evm,
        breathing=breathing,
        mqtt=mqtt,
        output=output,
        snapshot=snapshot,
        health=health,
        skin_detection=skin_detection,
        overlay=overlay,
        evm_visualization=evm_visualization,
    )
