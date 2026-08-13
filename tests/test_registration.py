"""Ground-truth tests: the applied rigid transform is known, so registration must
recover it exactly (Kabsch) or converge to it (ICP)."""
import numpy as np

import registration as reg


def _rot(ax, ay, az):
    cx, sx = np.cos(ax), np.sin(ax)
    cy, sy = np.cos(ay), np.sin(ay)
    cz, sz = np.cos(az), np.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _cloud(n=300, seed=0):
    return np.random.default_rng(seed).random((n, 3)) * 2 - 1


def test_kabsch_recovers_known_transform_exactly():
    P = _cloud()
    R0 = _rot(0.3, -0.2, 0.5)
    t0 = np.array([1.5, -0.7, 0.2])
    Q = reg.apply_transform(P, R0, t0)
    R, t = reg.kabsch(P, Q)
    assert np.allclose(R, R0, atol=1e-9)
    assert np.allclose(t, t0, atol=1e-9)
    assert np.isclose(np.linalg.det(R), 1.0)          # proper rotation, no reflection


def test_kabsch_is_reflection_free():
    # a planar (degenerate) set must still yield a proper rotation, not a flip
    P = _cloud()
    P[:, 2] = 0.0
    R0 = _rot(0.0, 0.0, 0.4)
    Q = reg.apply_transform(P, R0, np.zeros(3))
    R, _ = reg.kabsch(P, Q)
    assert np.isclose(np.linalg.det(R), 1.0, atol=1e-6)


def test_icp_converges_to_known_transform():
    P = _cloud(seed=1)
    R0 = _rot(0.15, 0.1, -0.2)
    t0 = np.array([0.3, -0.2, 0.1])
    Q = reg.apply_transform(P, R0, t0)
    R, t, aligned, rmse = reg.icp(P, Q, max_iter=100)
    assert rmse < 1e-6                                  # same points -> perfect alignment
    assert np.allclose(aligned, Q, atol=1e-4)
    assert np.allclose(R, R0, atol=1e-4) and np.allclose(t, t0, atol=1e-4)


def test_icp_partial_overlap_reduces_error():
    P = _cloud(seed=2)
    R0 = _rot(0.1, 0.0, 0.1)
    Q = reg.apply_transform(P, R0, np.array([0.2, 0.0, 0.0]))
    # start far off; ICP should still reduce the alignment error substantially
    _, _, _, rmse = reg.icp(P, Q, max_iter=60)
    start = float(np.sqrt(np.mean(np.sum((P - Q) ** 2, axis=1))))
    assert rmse < start


def _anisotropic(n=400, seed=0):
    """A cloud with distinct principal extents so PCA axes are well-defined."""
    rng = np.random.default_rng(seed)
    return (rng.random((n, 3)) * 2 - 1) * np.array([3.0, 1.0, 0.4])


def test_pca_align_then_register_recovers_large_rotation():
    P = _anisotropic()
    R0 = _rot(0.2, 2.4, 0.3)                    # ~140 deg about y — a big rotation
    t0 = np.array([2.0, -1.0, 0.5])
    Q = reg.apply_transform(P, R0, t0)
    # plain ICP from identity gets stuck; register (PCA start + trimmed ICP) does not
    _, _, _, rmse_plain = reg.icp(P, Q, max_iter=60)
    R, t, aligned, rmse = reg.register(P, Q, trim=None)
    assert rmse < 1e-3, f"register rmse {rmse} not tight"
    assert rmse_plain > 10 * rmse                # PCA start genuinely helped
    assert np.allclose(R, R0, atol=1e-3) and np.allclose(t, t0, atol=1e-3)


def _ellipsoid(n=900, seed=0):
    """Points on an ellipsoid surface — non-symmetric, so registration is well posed."""
    v = np.random.default_rng(seed).standard_normal((n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v * np.array([1.0, 0.6, 0.4])


def test_point_to_plane_icp_recovers_transform_on_a_surface():
    P = _ellipsoid()
    R0 = _rot(0.10, 0.08, -0.06)
    t0 = np.array([0.05, -0.03, 0.02])
    Q = reg.apply_transform(P, R0, t0)
    R, t, aligned, rmse = reg.point_to_plane_icp(P, Q, max_iter=60)
    assert rmse < 1e-4, f"point-to-plane rmse {rmse} not tight"
    assert np.allclose(R, R0, atol=1e-2) and np.allclose(t, t0, atol=1e-2)
    assert np.allclose(aligned, Q, atol=1e-2)


def test_trimmed_icp_rejects_outliers():
    base = _anisotropic(n=300, seed=3)
    R0 = _rot(0.12, 0.08, -0.1)
    t0 = np.array([0.3, -0.2, 0.15])
    Q = reg.apply_transform(base, R0, t0)                 # dst = inliers only
    rng = np.random.default_rng(9)
    outliers = rng.random((45, 3)) * 8 - 4                # ~13% src points with no match
    P = np.vstack([base, outliers])
    # trimming more than the outlier fraction recovers the inlier transform;
    # vanilla ICP is dragged off by the unmatched outliers.
    R, t, _, _ = reg.icp(P, Q, max_iter=80, trim=0.25)
    Rv, tv, _, _ = reg.icp(P, Q, max_iter=80)
    assert np.allclose(R, R0, atol=1e-2) and np.allclose(t, t0, atol=1e-2)
    assert not (np.allclose(Rv, R0, atol=1e-2) and np.allclose(tv, t0, atol=1e-2))
