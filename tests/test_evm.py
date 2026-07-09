import numpy as np

from evm_overlay.evm import TemporalPyramidEvm


def _checkerboard(size: int = 32, cell_size: int = 4) -> np.ndarray:
    yy, xx = np.indices((size, size))
    return (((xx // cell_size + yy // cell_size) % 2) * 2 - 1).astype(np.float32)


def _modulated_frame(pattern: np.ndarray, amplitude: float) -> np.ndarray:
    image = 120.0 + amplitude * pattern
    return np.repeat(image[:, :, None], 3, axis=2).clip(0, 255).astype(np.uint8)


def test_disabled_temporal_pyramid_evm_is_a_passthrough():
    processor = TemporalPyramidEvm(fps=15, low_hz=0.7, high_hz=2.5, alpha=10, pyramid_level=1, enabled=False)
    frame = _modulated_frame(_checkerboard(), 4)

    output = processor.update(frame)

    assert np.array_equal(output, frame)


def test_temporal_pyramid_evm_amplifies_in_band_spatial_modulation():
    fps = 15
    processor = TemporalPyramidEvm(fps=fps, low_hz=0.7, high_hz=2.5, alpha=12, pyramid_level=1, enabled=True)
    pattern = _checkerboard()
    residuals = []
    for frame_index in range(fps * 8):
        amplitude = 2.0 * np.sin(2 * np.pi * 1.2 * frame_index / fps)
        frame = _modulated_frame(pattern, amplitude)
        output = processor.update(frame)
        if frame_index > fps * 3:
            residuals.append(float(np.mean(np.abs(output.astype(float) - frame.astype(float)))))

    assert np.mean(residuals) > 1.0


def test_temporal_pyramid_evm_rejects_out_of_band_modulation_more_than_in_band():
    fps = 15
    pattern = _checkerboard()

    def mean_residual(frequency_hz: float) -> float:
        processor = TemporalPyramidEvm(fps=fps, low_hz=0.7, high_hz=2.5, alpha=12, pyramid_level=1, enabled=True)
        residuals = []
        for frame_index in range(fps * 8):
            amplitude = 2.0 * np.sin(2 * np.pi * frequency_hz * frame_index / fps)
            frame = _modulated_frame(pattern, amplitude)
            output = processor.update(frame)
            if frame_index > fps * 3:
                residuals.append(float(np.mean(np.abs(output.astype(float) - frame.astype(float)))))
        return float(np.mean(residuals))

    assert mean_residual(1.2) > mean_residual(6.0) * 1.5
