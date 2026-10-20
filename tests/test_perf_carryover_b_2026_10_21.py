"""Identity gates for the performance carry-over variants (2026-10-21)."""

from __future__ import annotations

import numpy as np

import opassist
import tomography
import lightfield


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
        for got, fast, want in zip(exact, reused, expected):
            assert np.array_equal(got, want)
            assert np.max(np.abs(fast - want)) < 0.10
