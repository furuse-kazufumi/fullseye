"""convol_image は画像より小さいマスクを受け付ける(2026-10-12)。

以前は n-ary 層の「2 つのラスタは同じ形」の検査に掛かり、3×3 のマスクを画像と同じ大きさの
ゼロ配列に埋めないと呼べなかった。
"""
import numpy as np
import pytest

import fullseye


def test_small_mask_is_accepted_and_correlates():
    rng = np.random.default_rng(0)
    img = rng.random((40, 40))
    mask = np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 2.0], [0.0, 0.0, 0.0]])
    small = fullseye.apply([img, mask], "convol_image", on_error="raise")
    assert small.shape == img.shape
    # 相関の向き: 右に重み 2 の核は右隣を多く読む
    ref = (img + 2 * np.roll(img, -1, axis=1)) / 3
    assert np.allclose(small[:, 1:-1], np.clip(ref, 0, 1)[:, 1:-1], atol=1e-6)


def test_other_binary_raster_ops_still_reject_mismatched_shapes():
    with pytest.raises(ValueError, match="share one shape"):
        fullseye.apply([np.zeros((40, 40)), np.zeros((3, 3))], "add_image", on_error="raise")
