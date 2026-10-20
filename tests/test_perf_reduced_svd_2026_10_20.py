"""性能レビュー第10便の回帰門。

SVD監査表（レビューで数えた57箇所。末尾に補助コード3箇所も併記）::

  file:line                                  shape/use                action
  balltrack.py:288                           design/null              left-for-slice
  balltrack.py:403                           square,U,Vt              left-for-slice
  calib.py:63,175                            design/null              shape-branch
  calib.py:265                               square,U,Vt              leave
  caltab.py:103                              design/null              shape-branch
  camera.py:289,328,389,502,533,555,599      square,U/Vt             leave
  camera.py:324,382,500,530                  design/null              shape-branch
  deform3d.py:424                            square,U,Vt              leave
  feat_fpfh.py:200                           square,U,Vt              leave
  final_genuine2.py:86                       design/null              shape-branch
  fit_transform.py:33,51                     square,U,Vt              leave
  fit_transform.py:107                       design/null              shape-branch
  geocam.py:281,452                          square,U,Vt              leave
  match3d.py:1876                            square,U,Vt              leave
  measure3d.py:316                           square,U,Vt              leave
  mosaic.py:17                               design/null              shape-branch
  odometry.py:40,173                         square,U,Vt              leave
  ozakimm.py:466                             square,U,Vt              leave
  pnp3d.py:78                                square,U,Vt              leave
  pnp3d.py:170,199                           design/null              shape-branch
  profileops.py:612                          square,U,Vt              left-for-slice
  reconstruction.py:67                       design/null              shape-branch
  reconstruction.py:69,112,222,244,272,321  square,U/Vt             leave
  registration.py:43                         square,U,Vt              leave
  transforms.py:253,303                      square,U,Vt              leave
  transforms.py:270                          design/null              shape-branch
  twoview.py:81,236                          design/null              shape-branch
  twoview.py:84,125,145,194                  square,U/Vt             leave
  examples/poc_aoi_ct_traceability.py:206    square,U,Vt              leave
  examples/poc_camera_calibration.py:241     singular-values-only     compute_uv=False
  examples/poc_panorama_drift.py:293         square,U,Vt              leave
  examples/poc_reproducible_icp.py:123       square,U,Vt              leave
  examples/poc_worm_core_persists.py:201      square,U,Vt              leave
  -- review scope: 57 sites above --
  examples_3d/nonrigid_deform.py:75           square,U,Vt              leave (extra)
  examples_3d/two_view_pose.py:66             singular-values-only     compute_uv=False (extra)
  tools/gen_backmatter_figs.py:154            square,U,Vt              leave (extra)
"""
from __future__ import annotations

import ast
import pathlib
import tracemalloc

import numpy as np

import calibration3d
import camera
import geometry2d
import reprconv


def _old_affine(points, H=None):
    p = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    H = np.eye(4) if H is None else np.asarray(H, dtype=np.float64)
    return (np.column_stack([p, np.ones(len(p))]) @ H.T)[:, :3]


def _old_voxel(gaussians, shape, origin, spacing, truncate):
    mu, sigma, w = reprconv._gaussians(gaussians)
    d, h, ww = shape
    org, sp = np.asarray(origin), np.asarray(spacing)
    out = np.zeros(shape, np.float64)
    idx = (mu - org) / sp
    rad = truncate * sigma[:, None] / sp[None, :]
    for i in range(len(mu)):
        lo = np.maximum(np.floor(idx[i] - rad[i]).astype(np.int64), [0, 0, 0])
        hi = np.minimum(np.ceil(idx[i] + rad[i]).astype(np.int64) + 1, [d, h, ww])
        if np.any(hi <= lo):
            continue
        zz = (np.arange(lo[0], hi[0]) - idx[i, 0]) * sp[0]
        yy = (np.arange(lo[1], hi[1]) - idx[i, 1]) * sp[1]
        xx = (np.arange(lo[2], hi[2]) - idx[i, 2]) * sp[2]
        r2 = zz[:, None, None] ** 2 + yy[None, :, None] ** 2 + xx[None, None, :] ** 2
        amp = w[i] / ((2 * np.pi) ** 1.5 * sigma[i] ** 3) * np.prod(sp)
        out[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] += amp * np.exp(-r2 / (2 * sigma[i] ** 2))
    return out


def _old_grid(args, n=60):
    r1, c1, p1, a1, b1, r2, c2, p2, a2, b2 = args
    def inside(pts, r, c, phi, la, lb):
        d = pts - [r, c]; cp, sp = np.cos(-phi), np.sin(-phi)
        x = d[:, 1] * cp - d[:, 0] * sp; y = d[:, 1] * sp + d[:, 0] * cp
        return (np.abs(x) <= la) & (np.abs(y) <= lb)
    m = max(a1, b1, a2, b2)
    lo, hi = np.array([min(r1, r2)-m, min(c1, c2)-m]), np.array([max(r1, r2)+m, max(c1, c2)+m])
    gy, gx = np.meshgrid(np.linspace(lo[0], hi[0], n), np.linspace(lo[1], hi[1], n))
    pts = np.column_stack([gy.ravel(), gx.ravel()])
    return float(np.sum(inside(pts, r1, c1, p1, a1, b1) & inside(pts, r2, c2, p2, a2, b2)) * np.prod(hi-lo) / n**2)


def test_affine_matches_old_and_reduces_peak():
    rng = np.random.default_rng(10); p = rng.normal(size=(1000, 3))
    H = rng.normal(size=(4, 4)); H[3] = [0.2, -0.3, 0.4, 2.0]
    np.testing.assert_allclose(calibration3d.affine_trans_point_3d(p, H), _old_affine(p, H), rtol=1e-12, atol=1e-12)
    big = np.zeros((1_000_000, 3))
    tracemalloc.start(); _old_affine(big, H); old = tracemalloc.get_traced_memory()[1]; tracemalloc.reset_peak()
    calibration3d.affine_trans_point_3d(big, H); new = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
    assert new <= old * 0.6


def test_voxel_separable_matches_old_and_uses_three_1d_exponentials(monkeypatch):
    rng = np.random.default_rng(11)
    g = {"mu": rng.uniform(0, 63, (500, 3)), "sigma": rng.uniform(.2, 2, 500), "w": rng.uniform(.1, 2, 500)}
    expected = _old_voxel(g, (64,)*3, (0,)*3, (1,)*3, 3.0)
    sizes = []; real = np.exp
    monkeypatch.setattr(np, "exp", lambda x: (sizes.append(np.asarray(x).size), real(x))[1])
    actual = reprconv.gaussians_to_voxel(g, shape=(64,)*3)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-14)
    assert max(sizes) <= 15


def test_rectangle_grid_unchanged_and_exact_closed_forms():
    cases = [
        ((0,0,0,2,1, 0,0,0,2,1), 8.0),
        ((0,0,0,2,1, 0,5,0,2,1), 0.0),
        ((0,0,0,2,1, 0,4,0,2,1), 0.0),
        ((0,0,0,3,2, 0,0,0,1,.5), 2.0),
    ]
    for args, area in cases:
        assert geometry2d.area_intersection_rectangle2(*args, method="exact") == area
        assert geometry2d.area_intersection_rectangle2(*args) == _old_grid(args)
    # 同じ正方形を45度回した交差は既知の正八角形: 8(sqrt(2)-1), 半辺1。
    args = (0,0,0,1,1, 0,0,np.pi/4,1,1)
    assert abs(geometry2d.area_intersection_rectangle2(*args, method="exact") - 8*(np.sqrt(2)-1)) < 1e-12
    assert geometry2d.area_intersection_rectangle2(0,0,0,0,1, 0,0,0,1,1, method="exact") == 0.0


def test_reduced_svd_preserves_tall_and_wide_nullspace_probe():
    rng = np.random.default_rng(12)
    for shape in ((2000, 12), (12, 12)):
        A = rng.normal(size=shape); uf, sf, vf = np.linalg.svd(A); ur, sr, vr = np.linalg.svd(A, full_matrices=False)
        np.testing.assert_array_equal(sf, sr); np.testing.assert_array_equal(vf, vr)
        np.testing.assert_allclose(uf[:, :min(shape)], ur, rtol=1e-12, atol=1e-15)
    A = rng.normal(size=(8, 9)); full = np.linalg.svd(A)[2]; reduced = np.linalg.svd(A, full_matrices=False)[2]
    assert full.shape == (9, 9) and reduced.shape == (8, 9)
    assert np.linalg.norm(A @ full[-1]) < 1e-12 and np.linalg.norm(A @ reduced[-1]) > 1e-3
    # 2,000点PnPの設計行列は4,000x12。完全Uを作る旧経路とのpeak比を固定する。
    A = rng.normal(size=(4000, 12))
    tracemalloc.start(); np.linalg.svd(A); old_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop(); tracemalloc.start()
    np.linalg.svd(A, full_matrices=False); new_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert new_peak <= old_peak * 0.5


def test_camera_estimates_stable_for_correspondence_counts(monkeypatch):
    rng = np.random.default_rng(13); K = camera.intrinsic_matrix(700, 710, 320, 240)
    R, t = camera.rodrigues([.1,-.2,.05]), np.array([.2,-.1,4.])
    for n in (8, 9, 50, 2000):
        X = rng.normal(size=(n,3)); uv, _ = camera.project_points(X, K, R, t)
        f = camera.fundamental_matrix(uv, uv + [.3, -.2])
        e = camera.essential_matrix(uv, uv + [.3, -.2], K)
        rr, tt = camera._pnp_dlt(X, uv, K)
        real_svd = np.linalg.svd
        def full_svd(a, *args, **kwargs):
            kwargs.pop("full_matrices", None)
            return real_svd(a, *args, full_matrices=True, **kwargs)
        with monkeypatch.context() as m:
            m.setattr(np.linalg, "svd", full_svd)
            f0 = camera.fundamental_matrix(uv, uv + [.3, -.2])
            e0 = camera.essential_matrix(uv, uv + [.3, -.2], K)
            rr0, tt0 = camera._pnp_dlt(X, uv, K)
        np.testing.assert_allclose(f, f0, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(e, e0, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(rr, rr0, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(tt, tt0, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(rr, R, atol=1e-10); np.testing.assert_allclose(tt, t, atol=1e-10)
