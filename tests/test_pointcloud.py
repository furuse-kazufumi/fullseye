"""Ground-truth tests for point-cloud geometry: analytic surfaces (plane, sphere,
cylinder) have known normals, and a regular grid has a known downsample count."""
import numpy as np

import pointcloud as pc


def test_plane_normals_point_along_z():
    rng = np.random.default_rng(0)
    P = np.column_stack([rng.random(600) * 2, rng.random(600) * 2, np.zeros(600)])
    n = pc.estimate_normals(P, k=16)
    # every normal is +/- the z axis
    assert np.abs(n[:, 2]).min() > 0.99
    assert np.abs(n[:, :2]).max() < 0.05


def test_sphere_normals_are_radial():
    rng = np.random.default_rng(1)
    v = rng.standard_normal((1000, 3))
    P = v / np.linalg.norm(v, axis=1, keepdims=True)          # unit sphere surface
    n = pc.estimate_normals(P, k=20, viewpoint=(0, 0, 0))
    radial = np.abs(np.einsum("ni,ni->n", n, P))              # |normal · unit radius|
    assert np.median(radial) > 0.95
    # oriented toward the origin viewpoint -> normals point inward (dot with P < 0)
    assert np.mean(np.einsum("ni,ni->n", n, P) < 0) > 0.9


def test_cylinder_normals_have_no_axial_component():
    rng = np.random.default_rng(2)
    theta = rng.random(1500) * 2 * np.pi
    z = rng.random(1500) * 4                                   # long axis = z
    P = np.column_stack([np.cos(theta), np.sin(theta), z])
    n = pc.estimate_normals(P, k=20)
    assert np.median(np.abs(n[:, 2])) < 0.1                    # normal ~ perpendicular to z
    radial = np.abs(n[:, 0] * np.cos(theta) + n[:, 1] * np.sin(theta))
    assert np.median(radial) > 0.95                            # and radial in the xy plane


def test_voxel_downsample_reduces_and_preserves_extent():
    xs, ys = np.meshgrid(np.linspace(0, 1, 20), np.linspace(0, 1, 20))
    P = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(400)])
    ds = pc.voxel_downsample(P, voxel=0.25)                    # ~4x4 voxels
    assert ds.shape[0] < P.shape[0]
    assert ds.shape[0] <= 25                                   # at most a 5x5 grid of cells
    # downsample stays inside the original bounding box
    assert ds[:, 0].min() >= P[:, 0].min() - 1e-9
    assert ds[:, 0].max() <= P[:, 0].max() + 1e-9


def test_pointcloud_reachable_through_facade():
    import fullseye as fs
    rng = np.random.default_rng(3)
    P = np.column_stack([rng.random(300), rng.random(300), np.zeros(300)])
    n = fs.estimate_normals(P, k=12)
    assert n.shape == P.shape and np.allclose(np.linalg.norm(n, axis=1), 1.0)
    assert fs.voxel_downsample(P, voxel=0.3).shape[0] < P.shape[0]
