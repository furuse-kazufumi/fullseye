"""Regression tests for the KNOWN_ISSUES.md fixes (2026-08-30).

One test group per issue, in KNOWN_ISSUES order:

  #1 `count_obj` / `blob_count` counted with 4-connectivity (HALCON non-parity:
     `connection`/counting default to 8-connectivity; a diagonally-touching pair
     was counted as 2 objects — cell counts 342 vs 327 on real data).
  #2 `sk_frangi` ignored both a and b knobs (four distinct settings were
     bit-identical). Now a -> sigma scale range, b -> Frangi beta; the default
     (0.5, 0.5) must stay bit-identical to the historical output so already
     published generated imagery remains valid.
  #3 `gen_contour_region_xld` returned boundary points in raster order, silently
     breaking order-dependent consumers (fourierdesc elliptic Fourier collapsed
     to one axis). Now returns TRACE-ordered contours.
  #4 registry `clahe` equalised tiles independently -> visible seams at tile
     boundaries. Now blends the 4 nearest tile CDFs with bilinear weights
     (standard CLAHE interpolation, Zuiderveld 1994).
  #5 `spec_decorrelation_stretch` refused RGB (B=3) — covered where it lives, in
     tests/test_specops_fusion.py::test_dcs_accepts_rgb_photograph.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops

# --------------------------------------------------------------------------- #
# #1 count_obj / blob_count: 8-connectivity default (HALCON parity)           #
# --------------------------------------------------------------------------- #
def _diag_pair():
    m = np.zeros((8, 8)); m[2, 2] = m[3, 3] = 1.0
    return m


def _separate_pair():
    m = np.zeros((8, 8)); m[1, 1] = m[5, 5] = 1.0
    return m


@pytest.mark.parametrize("opname", ["blob_count", "count_obj"])
def test_count_diagonal_pair_is_one_object(opname):
    """The KNOWN_ISSUES #1 minimal repro: two diagonally-touching pixels are ONE
    8-connected object (HALCON `connection` default), not two."""
    if opname not in ops.RT:
        pytest.skip(f"{opname} not registered on this install")
    assert float(ops.RT[opname](_diag_pair(), 0.5, 0.5)) == 1.0


@pytest.mark.parametrize("opname", ["blob_count", "count_obj"])
def test_count_separate_pair_is_two_objects(opname):
    if opname not in ops.RT:
        pytest.skip(f"{opname} not registered on this install")
    assert float(ops.RT[opname](_separate_pair(), 0.5, 0.5)) == 2.0


def test_count_matches_segment_objects_grouping():
    """The inconsistency that exposed the bug: count_obj disagreed with the
    8-connected segmentation the rest of the library uses."""
    from scipy import ndimage
    m = _diag_pair()
    lab, n8 = ndimage.label(m > 0.5, structure=np.ones((3, 3), bool))
    assert float(ops.RT["blob_count"](m, 0.0, 0.0)) == float(n8) == 1.0


def test_blob_count_legacy_4_connectivity_still_reachable():
    """Back-compat escape hatch documented in the docstring change history."""
    from ops import _blob_count
    assert float(_blob_count(_diag_pair(), 0.0, 0.0, connectivity=4)) == 2.0
    assert float(_blob_count(_diag_pair(), 0.0, 0.0)) == 1.0


def test_region_feat_count_connectivity_param():
    """The data-driven count_obj factory honours params={'connectivity': 4}."""
    import backends_auto
    fn8 = backends_auto._sh_region_feat({"metric": "count"})
    fn4 = backends_auto._sh_region_feat({"metric": "count", "connectivity": 4})
    m = _diag_pair()
    assert float(fn8(m, 0.0, 0.0)) == 1.0
    assert float(fn4(m, 0.0, 0.0)) == 2.0


# --------------------------------------------------------------------------- #
# #2 sk_frangi: knobs wired, default bit-identical to the historical output   #
# --------------------------------------------------------------------------- #
def _texture_img(n=64, seed=5):
    rng = np.random.default_rng(seed)
    v = np.clip(rng.random((n, n)) * 0.3, 0, 1)
    for r in range(8, n, 12):                    # ridge structures for frangi to see
        v[r:r + 2, :] = 0.9
    return v


def test_sk_frangi_default_matches_historical_output_bitwise():
    """(a, b) = (0.5, 0.5) must reproduce the pre-fix pipeline bit-exactly
    (norm(frangi(v, sigmas=range(1, 4)))) so published generated imagery stays
    valid."""
    skfilters = pytest.importorskip("skimage.filters")
    if "sk_frangi" not in ops.RT:
        pytest.skip("sk_frangi not registered")
    v = _texture_img()
    old = ops._norm(skfilters.frangi(v, sigmas=range(1, 4)))
    new = np.asarray(ops.RT["sk_frangi"](v, 0.5, 0.5), np.float64)
    assert np.array_equal(new, old), "default sk_frangi output moved from the historical result"


def test_sk_frangi_knobs_change_the_output():
    """KNOWN_ISSUES #2 repro inverted: the four settings that used to be
    bit-identical must now be pairwise distinguishable from the default."""
    pytest.importorskip("skimage.filters")
    if "sk_frangi" not in ops.RT:
        pytest.skip("sk_frangi not registered")
    v = _texture_img()
    ref = np.asarray(ops.RT["sk_frangi"](v, 0.5, 0.5), np.float64)
    for (a, b) in [(0.3, 0.8), (0.8, 0.8), (0.5, 0.2)]:
        out = np.asarray(ops.RT["sk_frangi"](v, a, b), np.float64)
        assert not np.array_equal(out, ref), f"sk_frangi ignored the knobs at (a,b)=({a},{b})"


# --------------------------------------------------------------------------- #
# #3 gen_contour_region_xld: boundary points in trace order                   #
# --------------------------------------------------------------------------- #
def _ellipse_mask(H=64, W=80, ry=18, rx=28):
    yy, xx = np.mgrid[:H, :W]
    return (((yy - H / 2) / ry) ** 2 + ((xx - W / 2) / rx) ** 2 <= 1.0).astype(np.float64)


def _max_adjacent_gap(c):
    d = np.hypot(np.diff(c[:, 0]), np.diff(c[:, 1]))
    return float(d.max())


def test_gen_contour_region_xld_points_are_trace_ordered():
    """Pre-fix: raster order gave adjacent-point distances of mean 17 px / max
    50 px on an ellipse. A traced boundary never jumps more than a few px."""
    if "gen_contour_region_xld" not in ops.RT:
        pytest.skip("gen_contour_region_xld not registered")
    cv = ops.RT["gen_contour_region_xld"](_ellipse_mask(), 0.5, 0.5)
    assert isinstance(cv, dict) and cv["cs"], "expected an XLD dict with contours"
    c = max((np.asarray(c, np.float64) for c in cv["cs"]), key=len)
    assert len(c) >= 20
    assert _max_adjacent_gap(c) <= 3.0, (
        f"boundary points are not in trace order (max adjacent gap {_max_adjacent_gap(c):.1f} px)")


def test_gen_contour_region_xld_feeds_elliptic_fourier_without_collapse():
    """The downstream breakage from KNOWN_ISSUES #3: EFD of a raster-ordered
    'contour' reconstructed to a shape collapsed onto one axis. With trace order
    the reconstruction must recover both ellipse axes."""
    if "gen_contour_region_xld" not in ops.RT:
        pytest.skip("gen_contour_region_xld not registered")
    import fourierdesc
    mask = _ellipse_mask()
    cv = ops.RT["gen_contour_region_xld"](mask, 0.5, 0.5)
    idx = int(np.argmax([len(c) for c in cv["cs"]]))
    pts = fourierdesc.from_xld(cv, idx)
    model = fourierdesc.elliptic_fourier(pts, n_harmonics=10)
    rec = fourierdesc.reconstruct(model, n_points=400)
    # reconstruction spans BOTH axes of the ellipse (ry=18 -> extent 36,
    # rx=28 -> extent 56), within 25% — a collapsed axis would be near zero
    ext = rec.max(axis=0) - rec.min(axis=0)      # (row extent, col extent)
    assert abs(ext[0] - 36) < 9, f"row extent collapsed/distorted: {ext[0]:.1f} (want ~36)"
    assert abs(ext[1] - 56) < 14, f"col extent collapsed/distorted: {ext[1]:.1f} (want ~56)"
    # and the reconstruction fills the mask area (IoU on the rasterised polygon)
    H, W = mask.shape
    rr = np.clip(np.round(rec[:, 0]).astype(int), 0, H - 1)
    cc = np.clip(np.round(rec[:, 1]).astype(int), 0, W - 1)
    from scipy import ndimage
    poly = np.zeros((H, W), bool)
    poly[rr, cc] = True
    filled = ndimage.binary_fill_holes(poly)
    inter = float(np.logical_and(filled, mask > 0.5).sum())
    union = float(np.logical_or(filled, mask > 0.5).sum())
    assert inter / union > 0.8, f"EFD reconstruction does not cover the mask (IoU {inter/union:.2f})"


def test_moore_fallback_traces_in_order_and_closes():
    """The numpy-only fallback used when skimage is absent must also produce
    trace-ordered, closed boundaries (adjacent steps are 8-neighbour moves)."""
    import backends_auto
    mask = _ellipse_mask() > 0.5
    cs = backends_auto._moore_boundaries(mask)
    assert cs, "no boundary traced"
    c = max(cs, key=len)
    assert np.array_equal(c[0], c[-1]), "boundary loop is not closed"
    d = np.hypot(np.diff(c[:, 0]), np.diff(c[:, 1]))
    assert float(d.max()) <= np.sqrt(2) + 1e-9, "fallback trace jumps beyond an 8-neighbour step"
    # every traced point is an actual boundary pixel of the mask
    from scipy import ndimage
    boundary = mask & ~ndimage.binary_erosion(mask)
    assert all(boundary[int(y), int(x)] for y, x in c)


def test_moore_fallback_handles_degenerate_components():
    import backends_auto
    m = np.zeros((6, 6), bool)
    m[1, 1] = True                               # isolated pixel
    m[3, 3] = m[4, 4] = True                     # diagonal 2-px line
    cs = backends_auto._moore_boundaries(m)
    assert len(cs) == 2                          # 8-connected: 2 components
    for c in cs:
        assert np.array_equal(c[0], c[-1])       # closed
        if len(c) > 1:
            d = np.hypot(np.diff(c[:, 0]), np.diff(c[:, 1]))
            assert float(d.max()) <= np.sqrt(2) + 1e-9


# --------------------------------------------------------------------------- #
# #4 clahe: no visible tile seams (bilinear inter-tile blending)              #
# --------------------------------------------------------------------------- #
#: `b` は 2026-09-02 に **clip limit** になった(それまで完全に死んだ引数)。
#: この節が測っているのはタイル境界の継ぎ目なので、切り取りが一度も効かない端
#: (= 素の AHE、clip limit 導入前とビット一致)で呼ぶ。
AHE_B = 1.0


def _clahe_no_interp(v, a):
    """Replica of the PRE-FIX clahe (independent per-tile equalisation) — the
    seam baseline the fix is measured against."""
    from ops import _equalize
    nb = 2 + int(a * 3); H, W = v.shape; out = v.copy()
    ys = np.linspace(0, H, nb + 1).astype(int); xs = np.linspace(0, W, nb + 1).astype(int)
    for i in range(nb):
        for j in range(nb):
            blk = v[ys[i]:ys[i + 1], xs[j]:xs[j + 1]]
            if blk.size:
                out[ys[i]:ys[i + 1], xs[j]:xs[j + 1]] = _equalize(blk, 0, 0)
    return out


def _gradient_noise(n=512, seed=11):
    rng = np.random.default_rng(seed)
    return np.clip(np.linspace(0.1, 0.9, n)[None, :] * np.ones((n, 1))
                   + 0.05 * rng.standard_normal((n, n)), 0, 1)


def _seam_ratio(out, a):
    """max column-boundary discontinuity / median column discontinuity (the
    KNOWN_ISSUES #4 metric: pre-fix this exceeded 6x at cols 169/340)."""
    n = out.shape[1]
    nb = 2 + int(a * 3)
    xs = np.linspace(0, n, nb + 1).astype(int)[1:-1]     # interior tile boundaries
    dcol = np.median(np.abs(np.diff(out, axis=1)), axis=0)   # (n-1,) per-column step
    med = float(np.median(dcol))
    seams = [float(dcol[j - 1]) for j in xs]             # step across each boundary
    return max(seams) / max(med, 1e-12)


@pytest.mark.parametrize("a", [0.5, 0.75])
def test_clahe_tile_seams_are_gone(a):
    v = _gradient_noise()
    r_old = _seam_ratio(_clahe_no_interp(v, a), a)
    r_new = _seam_ratio(np.asarray(ops.RT["clahe"](v, a, AHE_B), np.float64), a)
    assert r_old > 4.0, f"baseline lost its seam (ratio {r_old:.1f}) — metric broken?"
    assert r_new < r_old / 3, f"seam barely improved: {r_old:.1f} -> {r_new:.1f}"
    assert r_new < 2.5, f"tile boundary still an outlier: ratio {r_new:.1f}"


def test_clahe_correlates_better_with_cv_clahe_than_before():
    """The seam-free references (cv_clahe) should agree with the fixed op more
    than with the seamy one."""
    if "cv_clahe" not in ops.RT:
        pytest.skip("cv_clahe not registered (opencv absent)")
    v = _gradient_noise(256)
    ref = np.asarray(ops.RT["cv_clahe"](v, 0.5, 0.5), np.float64)
    old = _clahe_no_interp(v, 0.5)
    new = np.asarray(ops.RT["clahe"](v, 0.5, AHE_B), np.float64)
    c_old = float(np.corrcoef(old.ravel(), ref.ravel())[0, 1])
    c_new = float(np.corrcoef(new.ravel(), ref.ravel())[0, 1])
    assert c_new > c_old, f"correlation with cv_clahe did not improve: {c_old:.4f} -> {c_new:.4f}"


def test_clahe_still_equalises_locally():
    """The fix must not degrade clahe into a global equalise: a dark-left /
    bright-right image must have both halves' contrast opened up."""
    rng = np.random.default_rng(3)
    v = np.concatenate([0.05 + 0.05 * rng.random((64, 32)),
                        0.80 + 0.05 * rng.random((64, 32))], axis=1)
    out = np.asarray(ops.RT["clahe"](v, 0.5, AHE_B), np.float64)
    assert float(out[:, :32].std()) > 3 * float(v[:, :32].std())
    assert float(out[:, 32:].std()) > 3 * float(v[:, 32:].std())
