from evm_overlay.config import load_config


def test_load_config_parses_stream_roi_and_processing_defaults(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        """
input_url: rtsp://frigate:8554/nursery
output_url: rtsp://go2rtc:8554/nursery-heart
roi:
  x: 10
  y: 20
  width: 120
  height: 80
processing:
  fps: 15
  min_bpm: 80
  max_bpm: 180
output:
  width: 1152
  height: 648
snapshot:
  enabled: true
  host: 0.0.0.0
  port: 8088
  path: /snapshot.jpg
skin_detection:
  enabled: true
  preset: auto
  min_pixels: 50
  visualize: true
  ir_luma_min: 40
  ir_luma_max: 240
  ir_grayscale_tolerance: 12
breathing:
  enabled: true
  min_bpm: 8
  max_bpm: 35
  window_seconds: 30
  max_signal_delta: 20
evm_visualization:
  enabled: true
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
    assert cfg.output_url == "rtsp://go2rtc:8554/nursery-heart"
    assert cfg.roi.as_slice() == (slice(20, 100), slice(10, 130))
    assert cfg.processing.fps == 15
    assert cfg.processing.min_bpm == 80
    assert cfg.processing.max_bpm == 180
    assert cfg.output.width == 1152
    assert cfg.output.height == 648
    assert cfg.snapshot.enabled is True
    assert cfg.snapshot.host == "0.0.0.0"
    assert cfg.snapshot.port == 8088
    assert cfg.snapshot.path == "/snapshot.jpg"
    assert cfg.skin_detection.enabled is True
    assert cfg.skin_detection.preset == "auto"
    assert cfg.skin_detection.min_pixels == 50
    assert cfg.skin_detection.visualize is True
    assert cfg.skin_detection.ir_luma_min == 40
    assert cfg.skin_detection.ir_luma_max == 240
    assert cfg.skin_detection.ir_grayscale_tolerance == 12
    assert cfg.breathing.enabled is True
    assert cfg.breathing.min_bpm == 8
    assert cfg.breathing.max_bpm == 35
    assert cfg.breathing.window_seconds == 30
    assert cfg.breathing.max_signal_delta == 20
    assert cfg.evm_visualization.enabled is True
    assert cfg.evm_visualization.alpha == 25
    assert cfg.evm_visualization.learning_rate == 0.05
    assert cfg.evm_visualization.mode == "inset"
    assert cfg.evm_visualization.source == "frame"
    assert cfg.evm_visualization.inset_scale == 0.5
    assert cfg.evm_visualization.subtle_only is True
    assert cfg.evm_visualization.subtle_min_delta == 0.5
    assert cfg.evm_visualization.subtle_max_delta == 8.0
    assert cfg.evm_visualization.denoise_spatial_kernel == 5
    assert cfg.evm_visualization.denoise_temporal_alpha == 0.35
