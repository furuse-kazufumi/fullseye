"""性能レビュー第27便の一致ゲート。

旧実装は各テスト内の参照関数として残し、高速経路の結果と比較する。
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage

import volxform as vx
import quatimage as qi
import residue as residue_mod
import render3d as render3d_mod
from scipy.spatial import cKDTree


def _old_resize(v, shape, order=1, mode="nearest", cval=0.0):
    zoom = [t / s for t, s in zip(shape, v.shape)]
    out = ndimage.zoom(v, zoom, order=order, grid_mode=True, mode=mode, cval=cval)
    return np.ascontiguousarray(out, dtype=np.float64)


def _old_rotate(v, angle, axes=(1, 2), order=1, reshape=False,
                mode="constant", cval=0.0):
    out = ndimage.rotate(v, angle, axes=axes, reshape=reshape, order=order,
                         mode=mode, cval=cval)
    return np.ascontiguousarray(out, dtype=np.float64)


def _old_affine(v, matrix, offset, shape, order=1,
                mode="constant", cval=0.0):
    out = ndimage.affine_transform(v, matrix, offset=offset, output_shape=shape,
                                   order=order, mode=mode, cval=cval)
    return np.ascontiguousarray(out, dtype=np.float64)


@pytest.mark.parametrize("order", [0, 1])
def test_368_same_shape_resize_is_bit_identical(order):
    v = np.random.default_rng(368).normal(size=(13, 11, 9))
    got = vx.vol_resize(v, shape=v.shape, order=order)
    ref = _old_resize(v, v.shape, order=order)
    assert np.array_equal(got, ref)
    assert got is not v and got.flags.c_contiguous


@pytest.mark.parametrize("angle", [-270.0, -180.0, -90.0, 0.0, 90.0, 180.0, 270.0])
@pytest.mark.parametrize("order", [0, 1])
def test_367_quarter_turn_is_bit_identical(angle, order):
    v = np.arange(7 * 9 * 9, dtype=np.float64).reshape(7, 9, 9)
    got = vx.vol_rotate(v, angle, order=order)
    ref = _old_rotate(v, angle, order=order)
    assert np.array_equal(got, ref)


def test_367_near_quarter_turn_uses_general_path(monkeypatch):
    calls = 0
    old = ndimage.rotate

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return old(*args, **kwargs)

    monkeypatch.setattr(vx.ndimage, "rotate", counted)
    vx.vol_rotate(np.ones((5, 5, 5)), 90.0000001, order=1)
    assert calls == 1


def test_364_diagonal_affine_variant_and_near_miss_dispatch(monkeypatch):
    v = np.random.default_rng(364).normal(size=(17, 15, 13))
    calls = []
    old = ndimage.affine_transform

    def counted(inp, matrix, **kwargs):
        calls.append(np.asarray(matrix).shape)
        return old(inp, matrix, **kwargs)

    monkeypatch.setattr(vx.ndimage, "affine_transform", counted)
    diag = np.diag([0.75, 1.0, 1.25])
    got = vx.vol_affine(v, diag, offset=(0.2, 0.0, -0.3), order=1)
    ref = _old_affine(v, diag, (0.2, 0.0, -0.3), v.shape)
    assert np.array_equal(got, ref)
    assert calls[-1] == (3, 3)
    fast = vx.vol_affine(v, diag, offset=(0.2, 0.0, -0.3), order=1,
                         method="fast")
    assert calls[-1] == (3,)
    assert np.max(np.abs(fast - ref)) <= 1e-12
    near = diag.copy()
    near[0, 1] = 1e-9
    vx.vol_affine(v, near, order=1, method="fast")
    assert calls[-1] == (3, 3)


def test_364_fast_variant_large_dc_tiny_variance_probe():
    rng = np.random.default_rng(1364)
    v = 1e6 + rng.normal(scale=1e-8, size=(17, 15, 13))
    A = np.diag([0.875, 1.125, 0.9375])
    exact = vx.vol_affine(v, A, offset=(0.2, -0.3, 0.4), method="exact")
    fast = vx.vol_affine(v, A, offset=(0.2, -0.3, 0.4), method="fast")
    assert np.max(np.abs(fast - exact)) <= 1e-9


@pytest.mark.parametrize("order", [0, 1])
def test_366_integer_translation_matches_reference(order):
    v = np.random.default_rng(366).normal(size=(17, 15, 13))
    off = np.array([2.0, -3.0, 1.0])
    got = vx.vol_affine(v, np.eye(3), offset=off, order=order,
                        mode="constant", cval=-7.25)
    ref = _old_affine(v, np.eye(3), off, v.shape, order=order,
                      mode="constant", cval=-7.25)
    assert np.array_equal(got, ref)


def test_366_non_integer_translation_uses_general_path(monkeypatch):
    calls = 0
    old = ndimage.affine_transform

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return old(*args, **kwargs)

    monkeypatch.setattr(vx.ndimage, "affine_transform", counted)
    vx.vol_affine(np.ones((5, 5, 5)), np.eye(3), offset=(1.000000001, 0, 0))
    assert calls == 1


def test_365_output_array_matches_allocating_path_and_refuses_overlap():
    v = np.random.default_rng(365).normal(size=(11, 9, 7))
    expected = vx.vol_affine(v, np.diag([0.9, 1.0, 1.1]), order=1)
    out = np.empty_like(expected)
    got = vx.vol_affine(v, np.diag([0.9, 1.0, 1.1]), order=1, output=out)
    assert got is out
    assert np.array_equal(got, expected)
    with pytest.raises(ValueError, match="overlap"):
        vx.vol_affine(v, np.eye(3), output=v)


def _old_quat_correlate(a, b):
    fa = [np.fft.fft2(a[..., i]) for i in range(4)]
    fb = [np.fft.fft2(b[..., i]) for i in range(4)]

    def xc(i, j):
        return np.real(np.fft.ifft2(np.conj(fa[i]) * fb[j]))

    return np.stack([
        xc(0, 0) + xc(1, 1) + xc(2, 2) + xc(3, 3),
        xc(0, 1) - xc(1, 0) - xc(2, 3) + xc(3, 2),
        xc(0, 2) + xc(1, 3) - xc(2, 0) - xc(3, 1),
        xc(0, 3) - xc(1, 2) + xc(2, 1) - xc(3, 0),
    ], axis=-1)


@pytest.mark.parametrize("shape", [(16, 18), (15, 17), (8, 9)])
def test_319_quaternion_correlation_four_inverse_transforms(shape):
    rng = np.random.default_rng(sum(shape))
    a = rng.normal(size=shape + (4,))
    b = rng.normal(size=shape + (4,))
    ref = _old_quat_correlate(a, b)
    got = qi.quat_correlate(a, b)
    assert np.max(np.abs(got - ref)) <= 1e-10
    assert np.unravel_index(np.argmax(got[..., 0]), shape) == np.unravel_index(
        np.argmax(ref[..., 0]), shape)


def test_319_peak_location_is_bit_identical_on_shifted_fixture():
    rng = np.random.default_rng(319)
    a = rng.normal(size=(31, 29, 4))
    b = np.roll(a, (7, -4), axis=(0, 1))
    ref = _old_quat_correlate(a, b)
    got = qi.quat_correlate(a, b)
    assert np.unravel_index(np.argmax(got[..., 0]), got.shape[:2]) == (7, 25)
    assert np.unravel_index(np.argmax(ref[..., 0]), ref.shape[:2]) == (7, 25)


def test_322_public_qft_is_bit_identical_to_reference_path():
    rng = np.random.default_rng(322)
    q = rng.normal(size=(15, 17, 4))
    for side in ("left", "right"):
        m, n, lam = qi._mu_basis(None, "test")
        A, B = qi._to_symplectic(q, m, n, lam)
        FA = np.fft.fft2(A)
        FB = np.fft.fft2(B) if side == "left" else np.conj(np.fft.fft2(np.conj(B)))
        ref = qi._from_symplectic(np.fft.fftshift(FA), np.fft.fftshift(FB), m, n, lam)
        assert np.array_equal(qi.qft2(q, side), ref)


def test_324_combined_monogenic_metrics_match_three_calls(monkeypatch):
    q = qi.monogenic_signal(np.random.default_rng(324).normal(size=(31, 29)))
    calls = 0
    old = qi._require_monogenic

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return old(*args, **kwargs)

    monkeypatch.setattr(qi, "_require_monogenic", counted)
    got = qi.monogenic_metrics(q)
    assert calls == 1
    monkeypatch.setattr(qi, "_require_monogenic", old)
    ref = (qi.monogenic_amplitude(q), qi.monogenic_phase(q),
           qi.monogenic_orientation(q))
    assert len(got) == len(ref) == 3
    for actual, expected in zip(got, ref):
        assert np.allclose(actual, expected, rtol=0.0, atol=1e-12)


def _old_from_symplectic(A, B, m, n, lam):
    out = np.empty(A.shape + (4,), np.float64)
    out[..., 0] = np.real(A)
    out[..., 1:] = (np.imag(A)[..., None] * m[None, None, :]
                    + np.real(B)[..., None] * n[None, None, :]
                    + np.imag(B)[..., None] * lam[None, None, :])
    return out


def test_323_fused_symplectic_reconstruction_is_identical():
    rng = np.random.default_rng(323)
    A = rng.normal(size=(71, 69)) + 1j * rng.normal(size=(71, 69))
    B = rng.normal(size=(71, 69)) + 1j * rng.normal(size=(71, 69))
    m, n, lam = qi._mu_basis(None, "test")
    got = qi._from_symplectic(A, B, m, n, lam)
    ref = _old_from_symplectic(A, B, m, n, lam)
    assert np.array_equal(got, ref)


def _old_identity_magnification(video, scales):
    spec = np.fft.fft2(video, axes=(1, 2))
    bank = qi._radial_bank(video.shape[1], video.shape[2], scales)
    out = np.zeros_like(video, dtype=np.float64)
    for G in bank["bands"]:
        out += qi._band_monogenic(spec, G, bank)[0]
    out += np.real(np.fft.ifft2(spec * bank["lowpass"][None], axes=(1, 2)))
    out += np.real(np.fft.ifft2(spec * bank["highpass"][None], axes=(1, 2)))
    return out


def test_325_326_identity_gain_skips_riesz_and_matches_old(monkeypatch):
    rng = np.random.default_rng(326)
    video = rng.normal(size=(16, 31, 29))
    ref = _old_identity_magnification(video, 3)
    calls = 0
    old = qi._band_monogenic

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return old(*args, **kwargs)

    monkeypatch.setattr(qi, "_band_monogenic", counted)
    got = qi.riesz_motion_magnify(video, 1.0, 1.0, 3.0, 16.0, scales=3)
    assert calls == 0
    assert np.max(np.abs(got["video"] - ref)) <= 1e-12


def _old_crt_core(r, p, w, lo, hi, ref, edge=0.0):
    """The current pre-slice implementation, kept as the result oracle."""
    n = r.shape[0]
    shp = r.shape[1:]
    pb = p.reshape((n,) + (1,) * len(shp))
    ref = np.broadcast_to(np.asarray(ref), shp)
    pr = p[ref]
    rr = np.take_along_axis(r, ref[None], 0)[0]
    ks = residue_mod._candidate_ks(p, lo - edge, hi + edge)
    cand = rr[None] + ks.reshape((-1,) + (1,) * len(shp)) * pr[None]
    inside = (cand >= lo - edge) & (cand < hi + edge)
    ph = 2.0 * np.pi * (cand[None] - r[:, None]) / pb[:, None]
    score = (w[:, None] * np.cos(ph)).sum(0)
    score = np.where(inside, score, -np.inf)
    order = np.argsort(-score, axis=0, kind="stable")
    best = np.take_along_axis(cand, order[:1], 0)[0]
    s1 = np.take_along_axis(score, order[:1], 0)[0]
    s2 = np.take_along_axis(score, order[1:2], 0)[0]
    e = residue_mod._wrap_signed(r - best[None], pb)
    iv = w / pb ** 2
    ivs = iv.sum(0)
    val = best + np.where(ivs > 0, (iv * e).sum(0) / np.where(ivs > 0, ivs, 1.0), 0.0)
    resid = residue_mod._wrap_signed(r - val[None], pb)
    wsum = w.sum(0)
    safe = np.where(wsum > 0, wsum, 1.0)
    with np.errstate(invalid="ignore"):
        margin = np.where(np.isfinite(s2), (s1 - s2) / safe, 2.0)
    return val, np.where(wsum > 0, s1 / safe, 0.0), np.where(wsum > 0, margin, 0.0), resid


def test_329_top_two_matches_stable_sort_including_ties():
    p = np.array([5.0, 7.0, 9.0])
    r = np.zeros((3, 6, 5))
    w = np.ones_like(r)
    ref = np.zeros((6, 5), dtype=np.int64)
    old = _old_crt_core(r, p, w, -20.0, 20.0, ref)
    new = residue_mod._crt_core(r, p, w, -20.0, 20.0, ref)
    assert len(new[:4]) == len(old) == 4
    for got, expected in zip(new[:4], old):
        assert np.array_equal(got, expected, equal_nan=True)


def test_329_random_candidates_match_stable_sort_bit_for_bit():
    rng = np.random.default_rng(329)
    p = np.array([7.0, 9.0, 11.0, 13.0])
    r = rng.uniform(0.0, p[:, None, None], size=(4, 23, 19))
    w = rng.random(r.shape)
    ref = rng.integers(0, 4, size=r.shape[1:])
    old = _old_crt_core(r, p, w, -100.0, 100.0, ref)
    new = residue_mod._crt_core(r, p, w, -100.0, 100.0, ref)
    assert len(new[:4]) == len(old) == 4
    for got, expected in zip(new[:4], old):
        assert np.array_equal(got, expected, equal_nan=True)


def _old_fault_locate(residues, periods, weights=None, lo=0.0, hi=None, tol=0.05):
    p = residue_mod._periods(periods, "test")
    r = residue_mod._residues(residues, p.size, "test")
    w = residue_mod._weights(weights, r.shape, "test")
    full = residue_mod.residue_crt(r, p, w, lo, hi, on_outside="flag")
    hi_eff = float(lo) + full["unambiguous_range"] if hi is None else float(hi)
    pb = p.reshape((p.size,) + (1,) * (r.ndim - 1))
    ok_all = (np.abs(full["residual"]) <= tol * pb).all(0)
    worst, vals, outl = [], [], []
    for j in range(p.size):
        keep = [i for i in range(p.size) if i != j]
        sub = residue_mod.residue_crt(r[keep], p[keep], w[keep], lo, hi_eff,
                                      on_outside="flag")
        worst.append((np.abs(sub["residual"]) / pb[keep]).max(0))
        vals.append(sub["value"])
        outl.append(np.abs(residue_mod._wrap_signed(r[j] - sub["value"], p[j])) / p[j])
    worst, vals, outl = np.stack(worst), np.stack(vals), np.stack(outl)
    j = np.argmin(worst, 0)
    wj = np.take_along_axis(worst, j[None], 0)[0]
    oj = np.take_along_axis(outl, j[None], 0)[0]
    good = (wj <= tol) & (oj > tol) & (np.sort(worst, 0)[1] > tol)
    return {"value": np.where(ok_all, full["value"],
                              np.where(good, np.take_along_axis(vals, j[None], 0)[0], np.nan)),
            "faulty": np.where(ok_all, -1, np.where(good, j, -2)).astype(np.int64),
            "consistent_all": ok_all, "worst_leave_one_out": wj}


def test_333_fault_localisation_streaming_is_bit_identical():
    rng = np.random.default_rng(333)
    p = np.array([5.0, 7.0, 9.0, 11.0])
    values = rng.uniform(-20.0, 20.0, (31, 27))
    r = np.mod(values[None], p[:, None, None])
    r[2, 4:20, 3:19] = np.mod(r[2, 4:20, 3:19] + 2.0, p[2])
    old = _old_fault_locate(r, p, lo=-30.0, hi=30.0)
    got = residue_mod.residue_fault_locate(r, p, lo=-30.0, hi=30.0)
    for key in old:
        assert np.array_equal(got[key], old[key], equal_nan=True)


def _old_band_measure(img0, img1, periods, sigma_px, axis):
    s0, s1 = np.fft.fft2(img0), np.fft.fft2(img1)
    res, per, wts = [], [], []
    for p in periods:
        z0, k0 = residue_mod._band(s0, img0.shape, p, sigma_px, axis)
        z1, k1 = residue_mod._band(s1, img1.shape, p, sigma_px, axis)
        k = 0.5 * (k0 + k1)
        knom = 2.0 * np.pi / p
        k = np.where((k > knom / 3.0) & (k < 3.0 * knom), k, knom)
        pl = 2.0 * np.pi / k
        dphi = np.angle(z1 * np.conj(z0))
        res.append(np.mod(-dphi / k, pl)); per.append(pl)
        wts.append(np.abs(z0) * np.abs(z1))
    return np.stack(res), np.stack(per), np.stack(wts)


def test_334_335_shared_band_kernel_is_bit_identical():
    rng = np.random.default_rng(334)
    a = rng.normal(size=(65, 67)); b = np.roll(a, 7, axis=1)
    old = _old_band_measure(a, b, (5.0, 7.0, 11.0), 12.0, 1)
    got = residue_mod._band_measure(a, b, (5.0, 7.0, 11.0), 12.0, 1)
    for actual, expected in zip(got, old):
        assert np.array_equal(actual, expected)


def _old_query_sdf_grid(tree, xc, yc, zc):
    """Pre-slice full-grid nearest-surface query."""
    zz, yy, xx = np.meshgrid(zc, yc, xc, indexing="ij")
    centers = np.stack([xx, yy, zz], axis=-1).reshape(-1, 3)
    return tree.query(centers)[0].reshape(len(zc), len(yc), len(xc))


def test_349_sdf_slab_query_is_bit_identical():
    rng = np.random.default_rng(349)
    tree = cKDTree(rng.normal(size=(200, 3)))
    xc = np.linspace(-2.0, 2.0, 47)
    yc = np.linspace(-1.5, 1.5, 43)
    zc = np.linspace(-1.0, 1.0, 53)
    old = _old_query_sdf_grid(tree, xc, yc, zc)
    got = render3d_mod._query_sdf_grid(tree, xc, yc, zc)
    assert np.array_equal(got, old)


def test_353_sdf_in_place_sign_matches_where_bit_identically():
    rng = np.random.default_rng(353)
    dist = rng.random((17, 15, 13))
    inside = rng.random(dist.shape) > 0.5
    old = np.where(inside, -dist, dist).astype(np.float64)
    got = dist.copy(); got[inside] *= -1.0
    assert np.array_equal(got, old)
