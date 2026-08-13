"""Ground-truth tests for 3-D rendering + mesh/volume/SDF bridges (render3d.py).

The reference object is the same unit cube [0,1]^3 as test_mesh.py (imported from
mesh, so an imported object really does drive the renderer). Silhouette areas and
depths are cross-checked against pinhole projection worked out by hand, not
against render3d's own helpers.
"""
import numpy as np
import pytest

import mesh
import render3d

# Reuse the hand-written unit cube (8 vertices, 12 triangles).
CUBE_V = np.array([
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
])
CUBE_F = np.array([
    [0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
    [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7],
])


# --------------------------------------------------------------------------- #
# a known frontal pose: camera on +Z, front face (z=1) parallel to the image  #
# --------------------------------------------------------------------------- #
W = H = 256
F_PIX = 200.0                                     # focal length in pixels
EYE_Z = 3.0

FRONTAL_K = np.array([[F_PIX, 0.0, W / 2.0],
                      [0.0, F_PIX, H / 2.0],
                      [0.0, 0.0, 1.0]])


def frontal_pose(eye_z=EYE_Z):
    return render3d.look_at((0.5, 0.5, eye_z), (0.5, 0.5, 0.5), up=(0, 1, 0))


def test_render_cube_frontal_silhouette_depth_normals():
    pose = frontal_pose()
    out = render3d.render_mesh(CUBE_V, CUBE_F, pose=pose, intrinsics=FRONTAL_K,
                               width=W, height=H)
    depth, sil, nrm = out["depth"], out["silhouette"], out["normals"]

    assert depth.shape == (H, W) and depth.dtype == np.float64
    assert sil.shape == (H, W) and set(np.unique(sil)).issubset({0.0, 1.0})
    assert nrm.shape == (H, W, 3)

    # The front face (z=1) is nearest and largest, so the silhouette is its
    # projection: a unit square at depth EYE_Z-1=2, side F_PIX*1/2 = 100 px.
    side = F_PIX * 1.0 / (EYE_Z - 1.0)
    expected_area = side * side
    area = float(sil.sum())
    assert abs(area - expected_area) / expected_area < 0.05, (area, expected_area)

    # Depth: covered pixels lie between the front (2.0) and back (3.0) faces.
    cov = sil > 0.5
    dvals = depth[cov]
    assert np.isfinite(dvals).all()
    assert dvals.min() >= (EYE_Z - 1.0) - 1e-6            # nothing nearer than the front
    assert dvals.max() <= EYE_Z + 1e-6                   # nothing behind the far face
    assert abs(dvals.min() - (EYE_Z - 1.0)) < 0.05       # front face actually reached

    # Background is inf where empty; finite where covered.
    assert np.isinf(depth[~cov]).all()
    assert np.isfinite(depth[cov]).all()

    # Normals: unit length where covered, exactly zero where empty.
    lens = np.linalg.norm(nrm[cov], axis=1)
    assert np.allclose(lens, 1.0, atol=1e-9)
    assert np.all(nrm[~cov] == 0.0)
    # The dominant visible face points back at the camera (+Z in camera space).
    assert np.median(nrm[cov][:, 2]) > 0.9


def test_render_depth_monotonic_with_camera_distance():
    near = render3d.render_mesh(CUBE_V, CUBE_F, pose=frontal_pose(3.0),
                                intrinsics=FRONTAL_K, width=W, height=H)
    far = render3d.render_mesh(CUBE_V, CUBE_F, pose=frontal_pose(6.0),
                               intrinsics=FRONTAL_K, width=W, height=H)
    dn = near["depth"][near["silhouette"] > 0.5]
    df = far["depth"][far["silhouette"] > 0.5]
    assert df.min() > dn.min() + 1.0                     # moving back pushes depth out
    assert abs(dn.min() - 2.0) < 0.05 and abs(df.min() - 5.0) < 0.05
    # Farther camera -> smaller projected silhouette.
    assert far["silhouette"].sum() < near["silhouette"].sum()


def test_render_single_triangle_matches_analytic_area():
    # One triangle in a plane parallel to the image at z=1 (depth 2). Its screen
    # projection scales by F_PIX/depth, so screen area = world area * (F/depth)^2.
    V = np.array([[0.2, 0.2, 1.0], [0.8, 0.2, 1.0], [0.2, 0.7, 1.0]])
    Ftri = np.array([[0, 1, 2]])
    out = render3d.render_mesh(V, Ftri, pose=frontal_pose(), intrinsics=FRONTAL_K,
                               width=W, height=H)
    sil = out["silhouette"]
    world_area = 0.5 * abs((0.8 - 0.2) * (0.7 - 0.2))    # right triangle, legs .6 x .5
    scale = F_PIX / (EYE_Z - 1.0)
    expected = world_area * scale * scale
    area = float(sil.sum())
    assert abs(area - expected) / expected < 0.05, (area, expected)


def test_render_is_deterministic():
    a = render3d.render_mesh(CUBE_V, CUBE_F, pose=frontal_pose(), intrinsics=FRONTAL_K)
    b = render3d.render_mesh(CUBE_V, CUBE_F, pose=frontal_pose(), intrinsics=FRONTAL_K)
    assert np.array_equal(a["depth"], b["depth"])
    assert np.array_equal(a["silhouette"], b["silhouette"])
    assert np.array_equal(a["normals"], b["normals"])


def test_render_default_view_frames_the_mesh():
    # No pose / intrinsics -> auto_view must frame the mesh (non-empty silhouette).
    out = render3d.render_mesh(CUBE_V, CUBE_F, width=128, height=128)
    assert out["silhouette"].sum() > 0
    assert out["depth"].shape == (128, 128)


def test_render_empty_faces_is_all_background():
    out = render3d.render_mesh(CUBE_V, np.zeros((0, 3), np.int64),
                               pose=frontal_pose(), intrinsics=FRONTAL_K,
                               width=32, height=32)
    assert out["silhouette"].sum() == 0
    assert np.isinf(out["depth"]).all()
    assert np.all(out["normals"] == 0.0)


# --------------------------------------------------------------------------- #
# camera helpers                                                              #
# --------------------------------------------------------------------------- #
def test_look_at_shape_and_orthonormal():
    pose = render3d.look_at((0, 0, 5), (0, 0, 0), up=(0, 1, 0))
    assert pose.shape == (4, 4) and pose.dtype == np.float64
    R = pose[:3, :3]
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-9)    # orthonormal rotation
    # camera at (0,0,5) looking -Z: the target maps to depth 5 in front.
    cam = R @ np.array([0.0, 0.0, 0.0]) + pose[:3, 3]
    assert abs(-cam[2] - 5.0) < 1e-9


def test_look_at_and_intrinsics_reject_degenerate():
    with pytest.raises(ValueError):
        render3d.look_at((0, 0, 0), (0, 0, 0))           # eye == target
    with pytest.raises(ValueError):
        render3d.look_at((0, 0, 5), (0, 0, 0), up=(0, 0, 1))   # up parallel to view
    with pytest.raises(ValueError):
        render3d.intrinsics_from_fov(0.0, 64, 64)
    with pytest.raises(ValueError):
        render3d.intrinsics_from_fov(45.0, 0, 64)


def test_intrinsics_from_fov_values():
    K = render3d.intrinsics_from_fov(90.0, 100, 200)
    assert K.shape == (3, 3)
    assert np.isclose(K[1, 1], (200 / 2) / np.tan(np.deg2rad(45.0)))   # f = h/2 / tan(fov/2)
    assert np.isclose(K[0, 2], 50.0) and np.isclose(K[1, 2], 100.0)


# --------------------------------------------------------------------------- #
# mesh_to_sdf                                                                  #
# --------------------------------------------------------------------------- #
def test_mesh_to_sdf_cube_sign_and_shape():
    sdf, origin = render3d.mesh_to_sdf(CUBE_V, CUBE_F, grid=20, pad=0.2)
    assert sdf.dtype == np.float64 and sdf.ndim == 3
    assert origin.shape == (3,) and origin.dtype == np.float64
    # pad=0.2 * extent 1.0 -> origin sits 0.2 below the cube minimum.
    assert np.allclose(origin, [-0.2, -0.2, -0.2], atol=1e-9)

    pitch = 1.4 / 20.0                                   # padded span 1.4 over 20 cells

    def sample(pt):
        idx = np.floor((np.asarray(pt) - origin) / pitch).astype(int)   # (ix,iy,iz)
        return sdf[idx[2], idx[1], idx[0]]               # volume is (D,H,W)=(z,y,x)

    assert sample([0.5, 0.5, 0.5]) < 0                   # deep inside -> negative
    assert sample([0.05, 0.5, 0.5]) < 0                  # still inside
    assert sample([-0.15, 0.5, 0.5]) > 0                 # in the pad, outside -> positive
    assert sample([0.5, 0.5, 1.15]) > 0                  # above the top face -> positive

    # Distance magnitude is sane: the centre is ~0.5 from the nearest face.
    assert abs(abs(sample([0.5, 0.5, 0.5])) - 0.5) < 0.1
    assert sdf.min() < 0 and sdf.max() > 0
    # Near-surface cells straddle zero.
    assert np.abs(sdf).min() < pitch


def test_mesh_to_sdf_respects_voxel_cap():
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        render3d.mesh_to_sdf(CUBE_V, CUBE_F, pitch=1e-4)


# --------------------------------------------------------------------------- #
# voxelize_solid                                                               #
# --------------------------------------------------------------------------- #
def test_voxelize_solid_cube_is_filled_and_beats_surface():
    pitch = 0.1
    occ, origin = render3d.voxelize_solid(CUBE_V, CUBE_F, pitch)
    assert occ.dtype == bool and occ.ndim == 3
    assert np.allclose(origin, [0.0, 0.0, 0.0])
    surf, _ = mesh.voxelize(CUBE_V, CUBE_F, pitch)
    assert occ.shape == surf.shape                       # same grid, comparable counts
    assert int(occ.sum()) > int(surf.sum())              # solid fill beats hollow shell
    assert occ.any() and occ[occ.shape[0] // 2].any()    # the interior is filled
    # A cube [0,1]^3 at pitch 0.1: centres 0.05..0.95 inside -> a 10x10x10 solid.
    assert int(occ.sum()) == 1000


def test_voxelize_solid_fill_axis_agrees():
    # A watertight cube fills the same interior whichever axis the rays run along.
    a = render3d.voxelize_solid(CUBE_V, CUBE_F, 0.1, fill_axis=0)[0]
    b = render3d.voxelize_solid(CUBE_V, CUBE_F, 0.1, fill_axis=2)[0]
    assert np.array_equal(a, b)


def test_voxelize_solid_rejects_bad_input():
    for bad in (0.0, -0.1, np.nan):
        with pytest.raises(ValueError):
            render3d.voxelize_solid(CUBE_V, CUBE_F, bad)
    with pytest.raises(ValueError):
        render3d.voxelize_solid(CUBE_V, CUBE_F, 0.1, fill_axis=3)
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        render3d.voxelize_solid(CUBE_V, CUBE_F, 1e-4)


# --------------------------------------------------------------------------- #
# fail-closed on bad geometry / oversized output                              #
# --------------------------------------------------------------------------- #
def test_render_rejects_bad_face_indices():
    bad_F = np.array([[0, 1, 99]])
    with pytest.raises(ValueError, match="out of range"):
        render3d.render_mesh(CUBE_V, bad_F, pose=frontal_pose(), intrinsics=FRONTAL_K)


def test_render_rejects_non_finite_vertices():
    badV = CUBE_V.copy()
    badV[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        render3d.render_mesh(badV, CUBE_F, pose=frontal_pose(), intrinsics=FRONTAL_K)
    badV[0, 0] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        render3d.mesh_to_sdf(badV, CUBE_F, grid=8)
    with pytest.raises(ValueError, match="non-finite"):
        render3d.voxelize_solid(badV, CUBE_F, 0.2)


def test_render_caps_output_pixels():
    with pytest.raises(ValueError, match="MAX_PIXELS"):
        render3d.render_mesh(CUBE_V, CUBE_F, width=100000, height=100000)


def test_render_rejects_degenerate_camera():
    with pytest.raises(ValueError):
        render3d.render_mesh(CUBE_V, CUBE_F, pose=np.zeros((4, 4)), intrinsics=FRONTAL_K)
    with pytest.raises(ValueError):
        render3d.render_mesh(CUBE_V, CUBE_F, pose=frontal_pose(),
                             intrinsics=np.zeros((3, 3)))
