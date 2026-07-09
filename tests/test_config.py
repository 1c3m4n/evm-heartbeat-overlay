from pathlib import Path

from evm_overlay.config import load_config


def test_example_config_uses_current_grouped_schema():
    example = Path(__file__).parents[1] / "config.example.yaml"

    cfg = load_config(example)

    assert cfg.overlay.pulse_label
    assert cfg.overlay.breathing_label
    assert cfg.evm_visualization.label


def test_load_config_parses_grouped_runtime_schema_and_display_labels(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        """
streams:
  input_url: rtsp://frigate:8554/nursery
  output_url: rtsp://relay:8554/nursery-vitals
roi:
  x: 10
  y: 20
  width: 120
  height: 80
capture:
  fps: 15
  use_opencl: true
vitals:
  pulse:
    min_bpm: 80
    max_bpm: 180
    window_seconds: 20
  signal_evm:
    enabled: true
    low_hz: 0.7
    high_hz: 2.5
    alpha: 8
    pyramid_level: 1
  breathing:
    enabled: true
    min_bpm: 8
    max_bpm: 35
    window_seconds: 30
    max_signal_delta: 20
    min_confidence: 0.25
skin_detection:
  enabled: true
  preset: auto
  min_pixels: 50
  visualize: true
  ir_luma_min: 40
  ir_luma_max: 240
  ir_grayscale_tolerance: 12
output:
  video:
    width: 1152
    height: 648
  snapshot:
    enabled: true
    host: 0.0.0.0
    port: 8088
    path: /snapshot.jpg
  health:
    enabled: true
    host: 0.0.0.0
    port: 8089
  overlay:
    enabled: true
    position: [24, 48]
    min_confidence: 0.5
    pulse_label: Heart rate
    breathing_label: Respiration
  evm:
    enabled: true
    label: Subtle motion
    alpha: 25
    learning_rate: 0.05
    mode: inset
    source: frame
    inset_scale: 0.5
    subtle_only: true
    subtle_min_delta: 0.5
    subtle_max_delta: 8.0
    denoise_spatial_kernel: 5
    denoise_temporal_alpha: 0.35
""",
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.input_url == "rtsp://frigate:8554/nursery"
    assert cfg.output_url == "rtsp://relay:8554/nursery-vitals"
    assert cfg.roi.as_slice() == (slice(20, 100), slice(10, 130))
    assert cfg.processing.fps == 15
    assert cfg.processing.use_opencl is True
    assert cfg.processing.min_bpm == 80
    assert cfg.processing.max_bpm == 180
    assert cfg.processing.window_seconds == 20
    assert cfg.signal_evm.enabled is True
    assert cfg.signal_evm.low_hz == 0.7
    assert cfg.signal_evm.high_hz == 2.5
    assert cfg.signal_evm.alpha == 8
    assert cfg.signal_evm.pyramid_level == 1
    assert cfg.breathing.enabled is True
    assert cfg.breathing.min_bpm == 8
    assert cfg.breathing.max_bpm == 35
    assert cfg.breathing.window_seconds == 30
    assert cfg.breathing.max_signal_delta == 20
    assert cfg.breathing.min_confidence == 0.25
    assert cfg.output.width == 1152
    assert cfg.output.height == 648
    assert cfg.snapshot.enabled is True
    assert cfg.snapshot.port == 8088
    assert cfg.health.enabled is True
    assert cfg.health.port == 8089
    assert cfg.skin_detection.preset == "auto"
    assert cfg.overlay.pulse_label == "Heart rate"
    assert cfg.overlay.breathing_label == "Respiration"
    assert cfg.evm_visualization.label == "Subtle motion"
    assert cfg.evm_visualization.denoise_spatial_kernel == 5
    assert cfg.evm_visualization.denoise_temporal_alpha == 0.35
