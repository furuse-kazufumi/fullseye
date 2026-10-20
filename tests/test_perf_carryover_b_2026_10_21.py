"""Identity gates for the performance carry-over variants (2026-10-21)."""

from __future__ import annotations

import numpy as np

import opassist
import tomography
import lightfield
import profileops
import tsdf_fusion
import flow
from scipy import ndimage
from scipy.optimize import least_squares
import fit_primitives_ext


def _original_sart(sinogram, angles_deg, *, size, n_iter=1, relaxation=0.15):
    """The pre-plan SART loop retained as an executable reference."""
    sino = np.asarray(sinogram, dtype=np.float64)
    rad = np.deg2rad(np.asarray(angles_deg, dtype=np.float64))
    n_det = sino.shape[1]
    x = np.zeros((size, size), dtype=np.float64)
    ones_img = np.ones_like(x)
    ones_sino = np.ones((1, n_det), dtype=np.float64)
    eps = 1e-9
    row_sums = tomography._project(ones_img, rad, n_det, 1)
    col_sums = [
        np.maximum(tomography._backproject(ones_sino, rad[i:i + 1], size), eps)
        for i in range(rad.size)
    ]
    for _ in range(n_iter):
        for i in range(rad.size):
            fp = tomography._project(x, rad[i:i + 1], n_det, 1)[0]
            resid = (sino[i] - fp) / np.maximum(row_sums[i], eps)
            x = x + relaxation * tomography._backproject(
                resid[None, :], rad[i:i + 1], size
            ) / col_sums[i]
        np.clip(x, 0.0, None, out=x)
    return x


def _original_find(query, limit=20):
    """Reference entry point for the uncached search contract."""
    return opassist.find(query, limit=limit)


def test_ct_geometry_plan_is_bit_identical_on_two_shapes_and_iteration_knob():
    rng = np.random.default_rng(20261021)
    for size, n_angles, n_iter in ((9, 5, 1), (12, 7, 2)):
        angles = np.linspace(0.0, 160.0, n_angles)
        image = rng.random((size, size))
        sino = tomography._project(image, np.deg2rad(angles), 2 * size - 1)
        expected = _original_sart(sino, angles, size=size, n_iter=n_iter)
        actual = tomography.sart_reconstruct(
            sino, angles, size=size, n_iter=n_iter, relaxation=0.15
        )
        assert np.array_equal(actual, expected)


def test_op_search_reference_has_stable_order_for_name_and_doc_queries():
    for query, limit in (("dem_slope", 5), ("strain measurement", 10)):
        first = _original_find(query, limit)
        second = _original_find(query, limit)
        assert second == first


def _original_focal_stack(lf, slopes, edge):
    """The per-shift cubic prefilter path retained as a reference."""
    mode = lightfield.EDGE_MODES[edge]
    out = []
    for slope in slopes:
        acc = np.zeros(lf.shape[2:], dtype=np.float64)
        for _, _, image in lightfield._shifted_views(lf, slope, 3, mode):
            acc += image
        out.append(acc / (lf.shape[0] * lf.shape[1]))
    return out


def test_cubic_focal_stack_reuses_coefficients_for_each_boundary_mode():
    rng = np.random.default_rng(41)
    for shape, edge, slopes in (
        ((2, 3, 9, 11), "nearest", (-0.75, 0.25)),
        ((3, 2, 8, 10), "wrap", (-1.0, 0.5, 1.25)),
    ):
        lf = rng.random(shape)
        expected = _original_focal_stack(lf, slopes, edge)
        exact = lightfield.lf_focal_stack(lf, slopes, interp="cubic", edge=edge)
        reused = lightfield.lf_focal_stack(
            lf, slopes, interp="cubic", edge=edge, prefilter="reuse"
        )
        assert len(exact) == len(reused) == len(expected) == len(slopes)
        for got, fast, want in zip(exact, reused, expected):
            assert np.array_equal(got, want)
            assert np.max(np.abs(fast - want)) < 0.10


def _original_signed_distance(points, normals, poly):
    seg0 = poly
    d = np.roll(poly, -1, axis=0) - seg0
    ll = np.einsum("ij,ij->i", d, d)
    ll = np.where(ll < profileops._EPS, 1.0, ll)
    rel = points[:, None, :] - seg0[None, :, :]
    t = np.clip(np.einsum("nmj,mj->nm", rel, d) / ll, 0.0, 1.0)
    diff = seg0[None, :, :] + t[:, :, None] * d[None, :, :] - points[:, None, :]
    dist2 = np.einsum("nmj,nmj->nm", diff, diff)
    k = np.argmin(dist2, axis=1)
    return np.einsum("ij,ij->i", diff[np.arange(len(points)), k], normals)


def test_polyline_bvh_is_bit_identical_including_first_segment_ties():
    rng = np.random.default_rng(80)
    cases = []
    for n, m in ((7, 31), (19, 64), (33, 129)):
        poly = np.cumsum(rng.normal(size=(m, 2)), axis=0)
        points = rng.normal(size=(n, 2))
        normals = rng.normal(size=(n, 2))
        cases.append((points, normals, poly))
    # The origin is equally close to all four square segments.  Segment zero's
    # displacement has a different signed projection from segment one.
    square = np.array([[-1., -1.], [1., -1.], [1., 1.], [-1., 1.]])
    cases.append((np.array([[0., 0.]]), np.array([[0., 1.]]), square))
    for points, normals, poly in cases:
        expected = _original_signed_distance(points, normals, poly)
        actual = profileops._signed_distance_to_polyline(points, normals, poly)
        assert np.array_equal(actual, expected)


def _original_tsdf_integrate(tsdf, weight, depth, K, R, t, trunc, bounds):
    d = np.asarray(depth, dtype=np.float64)
    fx, fy, cx, cy = tsdf_fusion._as_K(K)
    centers = tsdf_fusion._voxel_centers(tsdf.shape, bounds)
    pc = centers @ np.asarray(R, np.float64).T + np.asarray(t, np.float64)
    z = pc[:, 2]
    zc = np.where(z > 0, z, 1.0)
    ui = np.rint(fx * pc[:, 0] / zc + cx).astype(np.int64)
    vi = np.rint(fy * pc[:, 1] / zc + cy).astype(np.int64)
    h, w = d.shape
    inside = (z > 0) & (ui >= 0) & (ui < w) & (vi >= 0) & (vi < h)
    measured = np.zeros(len(z), np.float64)
    measured[inside] = d[vi[inside], ui[inside]]
    delta = measured - z
    valid = inside & (measured > 0) & np.isfinite(measured) & (delta >= -trunc)
    sdf = np.minimum(1.0, delta / trunc).reshape(tsdf.shape)
    valid = valid.reshape(tsdf.shape)
    old = weight[valid].astype(np.float64)
    tsdf[valid] = ((old * tsdf[valid] + sdf[valid]) / (old + 1)).astype(tsdf.dtype)
    weight[valid] = (old + 1).astype(weight.dtype)


def test_tsdf_block_frustum_is_bit_identical_at_edge_and_in_free_space():
    rng = np.random.default_rng(4)
    depth = np.full((25, 31), 4.0)
    depth[3, 4] = np.nan
    K = np.array([[18., 0., 15.], [0., 17., 12.], [0., 0., 1.]])
    bounds_cases = [
        ((-5., 5.), (-4., 4.), (0.2, 6.0)),
        ((-1.0, 3.5), (-2., 2.), (0.5, 3.5)),  # edge-touching and free-space blocks
        ((-8., -1.), (-3., 3.), (0.1, 5.0)),
    ]
    for bounds in bounds_cases:
        a = rng.random((33, 34, 35), dtype=np.float32)
        wa = rng.integers(0, 3, a.shape).astype(np.float32)
        b, wb = a.copy(), wa.copy()
        _original_tsdf_integrate(a, wa, depth, K, np.eye(3), np.zeros(3), .4, bounds)
        tsdf_fusion.integrate(b, wb, depth, K, np.eye(3), np.zeros(3), .4, bounds)
        assert np.array_equal(b, a)
        assert np.array_equal(wb, wa)


def _original_track_points(prev, nxt, points, **kwargs):
    u, v = flow.optical_flow_lk(prev, nxt, **kwargs)
    pts = np.asarray(points, np.float64).reshape(-1, 2)
    du = ndimage.map_coordinates(u, [pts[:, 1], pts[:, 0]], order=1, mode="nearest")
    dv = ndimage.map_coordinates(v, [pts[:, 1], pts[:, 0]], order=1, mode="nearest")
    tracked = pts + np.stack([du, dv], axis=1)
    h, w = np.asarray(prev).shape[:2]
    ok = ((tracked[:, 0] >= 0) & (tracked[:, 0] <= w - 1)
          & (tracked[:, 1] >= 0) & (tracked[:, 1] <= h - 1))
    return tracked, ok


def test_sparse_point_tracker_is_gated_against_dense_reference():
    rng = np.random.default_rng(80)
    for shape, shift, levels in (((96, 128), (3, -2), 3),
                                 ((111, 143), (-4, 2), 3),
                                 ((80, 120), (1, 1), 2)):
        prev = ndimage.gaussian_filter(rng.random(shape), 1.2)
        nxt = ndimage.shift(prev, (shift[1], shift[0]), order=1, mode="nearest")
        pts = np.array([[35., 35.], [60., 50.], [80., 65.]])
        expected, expected_ok = _original_track_points(prev, nxt, pts, levels=levels, iters=5)
        dense, dense_ok = flow.track_points(prev, nxt, pts, levels=levels, iters=5)
        sparse, sparse_ok = flow.track_points(prev, nxt, pts, method="sparse",
                                              levels=levels)
        assert np.array_equal(dense, expected)
        assert np.array_equal(dense_ok, expected_ok)
        assert dense_ok.all() and sparse_ok.all()
        assert np.max(np.abs(sparse - dense)) <= 1.0


def _original_fit_torus(points):
    p = np.asarray(points, np.float64)
    c0 = p.mean(0)
    n0 = fit_primitives_ext._symmetry_axis(p - c0)
    a, rho = fit_primitives_ext._axial_radial(p, c0, n0)
    major = float(rho.mean())
    minor = float(np.mean(np.sqrt((rho - major) ** 2 + a ** 2)))
    def residual(x):
        aa, rr = fit_primitives_ext._axial_radial(
            p, x[:3], fit_primitives_ext._unit(x[3:6]))
        return np.sqrt((rr - x[6]) ** 2 + aa ** 2) - x[7]
    sol = least_squares(residual, np.r_[c0, n0, major, minor],
                        bounds=(np.r_[[-np.inf] * 6, 1e-9, 1e-9], np.repeat(np.inf, 8)),
                        method="trf", xtol=1e-12, ftol=1e-12, max_nfev=8000)
    return sol


def test_torus_tangent_axis_mode_keeps_default_and_converges_within_contract():
    rng = np.random.default_rng(95)
    for n, major, minor, noise in ((300, 2., .5, 0.), (600, 3., .3, .001),
                                    (900, 1.5, .7, .003)):
        u = rng.uniform(0, 2 * np.pi, n)
        w = rng.uniform(0, 2 * np.pi, n)
        points = np.c_[(major + minor * np.cos(w)) * np.cos(u),
                       (major + minor * np.cos(w)) * np.sin(u), minor * np.sin(w)]
        points += rng.normal(0, noise, points.shape)
        ref = _original_fit_torus(points)
        default = fit_primitives_ext.fit_torus(points)
        assert np.array_equal(default["center"], ref.x[:3])
        assert np.array_equal(default["axis"], fit_primitives_ext._unit(ref.x[3:6]))
        fast = fit_primitives_ext.fit_torus(points, axis_parameterization="tangent")
        assert np.max(np.abs(fast["center"] - default["center"])) < 1e-9
        axis_delta = min(np.max(np.abs(fast["axis"] - default["axis"])),
                         np.max(np.abs(fast["axis"] + default["axis"])))
        assert axis_delta < 1e-9
        assert max(abs(fast["R"] - default["R"]), abs(fast["r"] - default["r"])) < 1e-9
