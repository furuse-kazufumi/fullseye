"""Ground-truth tests for fit_transform (2-D transform estimation from point pairs).

The module contract is ``(row, col)`` points and matrices that act on ``(row, col, 1)``
homogeneous vectors. Every test builds the destination from a known transform and
checks that the estimate reproduces it — the truth is exact by construction."""
import numpy as np

import fit_transform as ft
import transforms


def _src(n=30, seed=0):
    return np.random.default_rng(seed).uniform(0, 100, (n, 2))       # (row, col)


def _apply_h(H, pts):
    h = np.c_[pts, np.ones(len(pts))] @ H.T
    return h[:, :2] / h[:, 2:3]


_H_TRUE = np.array([[1.1, 0.1, 3.0],
                    [0.05, 0.9, -2.0],
                    [0.001, 0.002, 1.0]])


def test_homography_acts_on_row_col_order():
    """Regression (2026-09-02): the DLT rows were assembled in (col, row) order, so the
    returned H mapped (row, col, 1) with the two coordinates swapped — 27 px error
    on a mild projective warp. Applied per the module contract it must be exact."""
    src = _src()
    dst = _apply_h(_H_TRUE, src)
    H = ft.hom_vector_to_proj_hom_mat2d(src, dst)
    assert np.abs(_apply_h(H, src) - dst).max() < 1e-9
    assert np.abs(H / H[2, 2] - _H_TRUE).max() < 1e-9


def test_homography_matches_transforms_projective_trans_point_2d():
    src = _src(seed=1)
    dst = _apply_h(_H_TRUE, src)
    H = ft.hom_vector_to_proj_hom_mat2d(src, dst)
    for (r, c), (r2, c2) in zip(src[:5], dst[:5]):
        p = transforms.projective_trans_point_2d(H, r, c)
        assert np.allclose(p, [r2, c2], atol=1e-9)


def test_homography_agrees_with_affine_estimate_on_affine_data():
    src = _src(seed=2)
    A = np.array([[1.2, 0.3], [-0.1, 0.8]])
    tr = np.array([5.0, -7.0])
    dst = src @ A.T + tr
    H = ft.hom_vector_to_proj_hom_mat2d(src, dst)
    M = ft.vector_to_hom_mat2d(src, dst)
    assert np.abs(_apply_h(H, src) - dst).max() < 1e-9
    assert np.abs(H - M).max() < 1e-8                      # same map, same (row, col) frame


def test_homography_is_well_conditioned_for_large_coordinates():
    """Hartley normalisation: pixel coordinates in the thousands must not degrade the fit."""
    src = _src(seed=3) * 40 + 2000                          # ~[2000, 6000]
    dst = _apply_h(_H_TRUE, src)
    H = ft.hom_vector_to_proj_hom_mat2d(src, dst)
    assert np.abs(_apply_h(H, src) - dst).max() < 1e-6


def test_homography_minimal_four_points_and_guard():
    import pytest
    src = _src(n=4, seed=4)
    dst = _apply_h(_H_TRUE, src)
    H = ft.hom_vector_to_proj_hom_mat2d(src, dst)
    assert np.abs(_apply_h(H, src) - dst).max() < 1e-8
    with pytest.raises(ValueError):
        ft.hom_vector_to_proj_hom_mat2d(src[:3], dst[:3])


def test_rigid_and_similarity_still_exact():
    src = _src(seed=5)
    th = np.deg2rad(30)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    tr = np.array([5.0, -7.0])
    M = ft.vector_to_rigid(src, src @ R.T + tr)
    assert np.abs(M[:2, :2] - R).max() < 1e-9 and np.abs(M[:2, 2] - tr).max() < 1e-9
    M = ft.vector_to_similarity(src, 1.7 * src @ R.T + tr)
    assert abs(np.sqrt(np.linalg.det(M[:2, :2])) - 1.7) < 1e-9
