import numpy as np

from evm_overlay.snapshot import SnapshotStore


def test_snapshot_store_returns_jpeg_after_frame_update():
    store = SnapshotStore()
    frame = np.zeros((20, 30, 3), dtype=np.uint8)
    frame[:, :, 1] = 255

    store.update(frame)
    data = store.get_jpeg()

    assert data is not None
    assert data.startswith(b"\xff\xd8")
    assert data.endswith(b"\xff\xd9")


def test_snapshot_store_returns_none_before_first_frame():
    store = SnapshotStore()

    assert store.get_jpeg() is None
