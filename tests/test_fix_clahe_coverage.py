"""Regression guard: `clahe` must tile the WHOLE image (audit finding #51).

Ground truth for per-tile histogram equalization:
  * the tiles partition the image, so every pixel belongs to exactly one tile;
  * inside a tile the transform is the tile's own normalised CDF, so the tile's
    maximum maps to 1.0 and a strictly-increasing ramp is *never* left at its
    raw value.
The pre-fix implementation used hs = H // nb with i in range(nb), leaving the
H % nb trailing rows / W % nb trailing columns raw (a visible seam).

2026-09-02: `b` は **clip limit** になった(それまでは完全に死んだ引数だった)。
これらのケースが検証しているのは「タイルの CDF がタイル全体を覆うか」なので、
切り取りが一度も効かない端 ``b=AHE_B`` (= 素の AHE、旧実装とビット一致)で
呼ぶ。clip limit そのものの検証は tests/test_fix_clahe_clip_limit.py。
"""
from __future__ import annotations

import numpy as np
import pytest

import ops

#: clip limit が効かない端 = 旧実装(AHE)と同じ写像。
AHE_B = 1.0

# (size, a): sizes chosen so that nb = 2 + int(a*3) does NOT divide the size.
UNEVEN = [(33, 1.0), (33, 0.75), (32, 0.5), (50, 0.75), (17, 0.75), (64, 0.5)]


def _ramp(n):
    """Strictly increasing ramp: every pixel has a distinct value."""
    return np.linspace(0.2, 0.8, n * n).reshape(n, n)


@pytest.mark.parametrize("n,a", UNEVEN)
def test_clahe_leaves_no_unequalised_trailing_strip(n, a):
    v = _ramp(n)
    out = np.asarray(ops.RT["clahe"](v, a, AHE_B), np.float64)
    same = np.isclose(out, v)
    raw_rows = [i for i in range(n) if same[i].all()]
    raw_cols = [j for j in range(n) if same[:, j].all()]
    assert not raw_rows, f"clahe(a={a}) never equalised rows {raw_rows} of a {n}x{n} image"
    assert not raw_cols, f"clahe(a={a}) never equalised cols {raw_cols} of a {n}x{n} image"


@pytest.mark.parametrize("n,a", UNEVEN)
def test_clahe_maps_the_image_maximum_to_one(n, a):
    # whichever tile owns the global maximum, that pixel is that tile's maximum,
    # so its equalised value is the top of the tile CDF = 1.0.
    v = _ramp(n)
    out = np.asarray(ops.RT["clahe"](v, a, AHE_B), np.float64)
    idx = np.unravel_index(int(np.argmax(v)), v.shape)
    assert out[idx] == pytest.approx(1.0, abs=1e-9), (
        f"clahe(a={a}) left the image maximum at {idx} = {out[idx]:.4f} "
        f"(raw {v[idx]:.4f}) -> that pixel was never equalised")


@pytest.mark.parametrize("n,a", UNEVEN + [(1, 0.0), (3, 1.0), (7, 0.5)])
def test_clahe_output_contract(n, a):
    v = _ramp(n)
    out = np.asarray(ops.RT["clahe"](v, a, AHE_B), np.float64)
    assert out.shape == v.shape
    assert np.all(np.isfinite(out)), "clahe produced NaN/Inf"
    assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, (
        f"clahe out of [0,1]: min={out.min()} max={out.max()}")
