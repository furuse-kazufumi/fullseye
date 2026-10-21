"""Performance batch 19-A: reference agreements and opt-in memory variants."""
from __future__ import annotations

import numpy as np

import fit_primitives_ext as fpe
import fringe
import pcl_filter
import volfreq
import volrestore
from scipy.signal import fftconvolve


def _old_triangulate(column, kc, kp, rot, trans):
    col = np.asarray(column, dtype=np.float64)
    h, w = col.shape
    v_i, u_i = np.mgrid[0:h, 0:w].astype(np.float64)
    pix = np.stack([u_i, v_i, np.ones_like(u_i)], axis=-1)
    d = pix @ np.linalg.inv(kc).T
    rd = d @ np.asarray(rot).T
    a = np.asarray(kp)[0][None, None, :] - col[..., None] * np.asarray(kp)[2][None, None, :]
    denom = np.einsum("ijk,ijk->ij", a, rd)
    num = -np.einsum("ijk,k->ij", a, trans)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = num / denom
    bad = ~np.isfinite(z) | (np.abs(denom) < 1e-12) | (z <= 0) | ~np.isfinite(col)
    z[bad] = np.nan
    return z


def test_81_decode_fringe_reuses_phase_sums(monkeypatch):
    images = fringe.synthesize_fringes(np.zeros((18, 20)), n_steps=5, freq=0.2)
    old = fringe.decode_fringe(images, min_modulation=0.01)
    calls = 0
    original = fringe._phase_sums

    def counted(stack):
        nonlocal calls
        calls += 1
        return original(stack)

    monkeypatch.setattr(fringe, "_phase_sums", counted)
    got = fringe.decode_fringe(images, min_modulation=0.01)
    assert calls == 1
    assert np.array_equal(got, old, equal_nan=True)


def test_85_triangulate_scalar_form_matches_array_reference():
    kc = np.array([[700., 3., 12.], [0., 710., 9.], [0., 0., 1.]])
    kp = np.array([[680., 0., 15.], [0., 690., 8.], [0., 0., 1.]])
    rot = np.array([[.9998, 0., .02], [0., 1., 0.], [-.02, 0., .9998]])
    trans = np.array([-.12, 0., 0.])
    col = np.linspace(-50, 80, 20 * 24).reshape(20, 24)
    col[0, 0] = np.nan
    ref = _old_triangulate(col, kc, kp, rot, trans)
    got = fringe.triangulate_column(col, kc, kp, rot, trans)
    assert np.array_equal(np.isnan(got), np.isnan(ref))
    np.testing.assert_allclose(got, ref, rtol=1e-10, atol=1e-10)


def test_83_four_step_mode_matches_general_path():
    images = fringe.synthesize_fringes(np.linspace(-2, 2, 600).reshape(20, 30), n_steps=4)
    np.testing.assert_allclose(fringe.wrapped_phase(images, method="four_step"),
                               fringe.wrapped_phase(images), rtol=0, atol=1e-12)


def test_86_statistical_outlier_chunk_is_bit_identical():
    rng = np.random.default_rng(8619)
    points = np.r_[rng.normal(size=(301, 3)), [[30., 30., 30.]]]
    ref, ref_mask = pcl_filter.statistical_outlier_removal(points, k=11)
    got, mask = pcl_filter.statistical_outlier_removal(points, k=11, chunk=37)
    assert np.array_equal(mask, ref_mask)
    assert np.array_equal(got, ref)


def test_89_voxel_bincount_keeps_bitwise_means_and_cell_order():
    rng = np.random.default_rng(8919)
    points = rng.normal(size=(1000, 3))
    keys = np.floor((points - points.min(0)) / .3).astype(np.int64)
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    sums = np.zeros((inv.max() + 1, 3)); counts = np.zeros(inv.max() + 1)
    np.add.at(sums, inv, points); np.add.at(counts, inv, 1.)
    ref = sums / counts[:, None]
    assert np.array_equal(pcl_filter.voxel_grid_downsample(points, .3), ref)


def test_87_mls_chunk_and_88_sparse_flow_agree_with_defaults():
    rng = np.random.default_rng(8719)
    xy = rng.uniform(-1, 1, size=(180, 2))
    points = np.column_stack([xy, .1 * (xy[:, 0] ** 2 + xy[:, 1] ** 2)])
    np.testing.assert_allclose(pcl_filter.mls_smooth(points, .45, chunk=23),
                               pcl_filter.mls_smooth(points, .45), rtol=0, atol=1e-12)
    moved = points + [.02, -.01, .03]
    exact = __import__("scene_flow3d").smooth_flow(points, moved, k=7, n_iter=3)
    sparse = __import__("scene_flow3d").smooth_flow(points, moved, k=7, n_iter=3,
                                                     method="sparse")
    np.testing.assert_allclose(sparse, exact, rtol=0, atol=1e-12)


def _ellipsoid_points(n=2000, offset=0.0):
    rng = np.random.default_rng(9319)
    q = rng.normal(size=(n, 3)); q /= np.linalg.norm(q, axis=1)[:, None]
    return q * [4., 2., .7] + [offset, -offset, offset]


def test_93_94_ellipsoid_chunk_agrees_at_large_coordinate_offset():
    points = _ellipsoid_points(offset=1e6)
    ref = fpe.fit_ellipsoid(points)
    got = fpe.fit_ellipsoid(points, chunk=113)
    np.testing.assert_allclose(got["center"], ref["center"], rtol=0, atol=1e-10)
    np.testing.assert_allclose(got["radii"], ref["radii"], rtol=0, atol=1e-10)
    assert abs(got["residual"] - ref["residual"]) <= 1e-10


def _old_rl(vol, psf, iterations=3, clip_tiny=1e-12):
    v = np.asarray(vol, dtype=np.float64); k = np.asarray(psf, dtype=np.float64)
    k = k / k.sum(); km = k[::-1, ::-1, ::-1]
    crop = tuple(slice(s // 2, s // 2 + n) for s, n in zip(k.shape, v.shape))
    est = np.full(v.shape, max(float(v.mean()), clip_tiny))
    for _ in range(iterations):
        denom = fftconvolve(est, k, mode="same")
        ratio = v / np.maximum(denom, clip_tiny)
        est = est * fftconvolve(ratio, km, mode="full")[crop]
        np.maximum(est, 0, out=est)
    return np.ascontiguousarray(est)


def test_67_rl_default_and_even_psf_crop():
    rng = np.random.default_rng(6719)
    vol = rng.random((12, 13, 14)); psf = rng.random((2, 3, 4))
    ref = _old_rl(vol, psf)
    got = volrestore.vol_richardson_lucy(vol, psf, 3)
    np.testing.assert_allclose(got, ref, rtol=1e-10, atol=1e-10)


def test_69_70_rl_default_exact_and_zero_avoids_convolution(monkeypatch):
    rng = np.random.default_rng(6919)
    vol = rng.random((9, 10, 11)); psf = rng.random((3, 3, 3))
    # 統合(2026-10-21): 既定経路は第 3 便の核スペクトル再利用(FFT 形が旧 fftconvolve と違う)なので
    # bit 一致ではなく丸めの範囲で比べる(統合枝で実測した差は 1e-15 台)。
    assert np.allclose(volrestore.vol_richardson_lucy(vol, psf, 4), _old_rl(vol, psf, 4), rtol=1e-12, atol=0)
    calls = 0
    def forbidden(*args, **kwargs):
        nonlocal calls; calls += 1
        raise AssertionError("zero observation must not convolve")
    monkeypatch.setattr(volrestore, "fftconvolve", forbidden)
    assert np.array_equal(volrestore.vol_richardson_lucy(np.zeros_like(vol), psf, 2), np.zeros_like(vol))
    assert calls == 0


def test_71_72_73_gaussian_transfer_matches_old_formula():
    rng = np.random.default_rng(7119); vol = rng.normal(size=(9, 10, 11)); c = .17
    fz = np.fft.fftfreq(9); fy = np.fft.fftfreq(10); fx = np.fft.rfftfreq(11)
    radius = np.sqrt(fz[:, None, None] ** 2 + fy[None, :, None] ** 2 + fx[None, None, :] ** 2)
    ref = np.fft.irfftn(np.fft.rfftn(vol) * np.exp(-(radius * radius) / (2*c*c)), s=vol.shape)
    np.testing.assert_allclose(volfreq.vol_fft_lowpass(vol, c), ref, rtol=1e-14, atol=1e-14)
