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
evm_visualization:
  enabled: true
  alpha: 25
  learning_rate: 0.05
  mode: inset
  inset_scale: 0.5
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
    assert cfg.evm_visualization.enabled is True
    assert cfg.evm_visualization.alpha == 25
    assert cfg.evm_visualization.learning_rate == 0.05
    assert cfg.evm_visualization.mode == "inset"
    assert cfg.evm_visualization.inset_scale == 0.5
