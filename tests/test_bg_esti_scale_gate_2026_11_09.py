"""create_bg_esti / run_bg_esti: 画素値の尺度を検査していなかった(2026-11-09 点検)。

既定の threshold = 0.1 は [0, 1] の尺度。uint8 の静止場面(±2 DN の雑音)を渡すと前景率 79 %。
"""
import numpy as np
import pytest

import mvtrack as T


def _frames():
    rng = np.random.default_rng(0)
    base = rng.integers(40, 200, size=(32, 32))
    return [np.clip(base + rng.integers(-2, 3, size=base.shape), 0, 255).astype(np.uint8) for _ in range(5)]


def test_uint8_frames_are_refused():
    fr = _frames()
    with pytest.raises(ValueError, match="integer dtype"):
        T.create_bg_esti(fr[0])
    m = T.create_bg_esti(fr[0] / 255.0)
    with pytest.raises(ValueError, match="integer dtype"):
        T.run_bg_esti(m, fr[1])


def test_float_out_of_unit_range_is_refused():
    fr = _frames()
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        T.create_bg_esti(fr[0].astype(np.float64))


def test_scaled_static_scene_has_almost_no_foreground():
    fr = _frames()
    m = T.create_bg_esti(fr[0] / 255.0)
    fg = []
    for f in fr[1:]:
        r = T.run_bg_esti(m, f / 255.0)
        m = r["model"]
        fg.append(r["foreground"].mean())
    assert max(fg) < 0.01
