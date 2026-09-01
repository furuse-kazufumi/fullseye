"""Ground-truth tests for 3-D rendering + mesh/volume/SDF bridges (render3d.py).

The reference object is the same unit cube [0,1]^3 as test_mesh.py (imported from
mesh, so an imported object really does drive the renderer). Silhouette areas and
depths are cross-checked against pinhole projection worked out by hand, not
against render3d's own helpers.
"""
import numpy as np
import pytest

import camera
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
    # Pixel centres are integers (columns 0..w-1), so the image centre — and thus
    # the principal point — is (w-1)/2, (h-1)/2. NOT w/2, h/2: that is the centre
    # only under the OpenGL "pixel corners are integers" convention, which this
    # library does not use. See test_principal_point_is_the_image_centre below for
    # the behavioural consequence.
    assert np.isclose(K[0, 2], 49.5) and np.isclose(K[1, 2], 99.5)


# --------------------------------------------------------------------------- #
# pixel-centre convention: render3d <-> camera must agree to machine precision #
# --------------------------------------------------------------------------- #
# A tilted plane is the discriminating scene: its depth varies across the image,
# so a half-pixel sampling offset becomes a measurable depth bias. A
# frontoparallel plane would hide the bug entirely (constant depth).
PLANE_D, PLANE_A, PLANE_B = 2.0, 0.3, 0.2      # z_cam = -(D + a*x + b*y)


def _tilted_plane_mesh(extent=2.0):
    """Two triangles spanning a tilted plane, in render3d camera space (identity
    pose), large enough to cover the whole image at the intrinsics used below."""
    xy = [(-extent, -extent), (extent, -extent), (extent, extent), (-extent, extent)]
    V = np.array([[x, y, -(PLANE_D + PLANE_A * x + PLANE_B * y)] for x, y in xy],
                 np.float64)
    F = np.array([[0, 1, 2], [0, 2, 3]], np.int64)
    return V, F


def _plane_depth(u, v, K):
    """Analytic depth of the tilted plane along the ray through the *continuous*
    image point (u, v). Worked out by hand from the pinhole model, independent of
    render3d: a render3d camera-space point at depth d is
    ((u-cx)/fx*d, -(v-cy)/fy*d, -d); substituting into z = -(D + a x + b y) gives
    d * (1 - a*(u-cx)/fx + b*(v-cy)/fy) = D."""
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    return PLANE_D / (1.0 - PLANE_A * (u - cx) / fx + PLANE_B * (v - cy) / fy)


def test_render_samples_pixel_centres_at_integer_coordinates():
    # Regression guard for the half-pixel convention clash: render3d used to
    # sample at (col+0.5, row+0.5) (OpenGL corners-at-integers) while the rest of
    # the library — camera.depth_to_points, cadmap, visualhull — reads pixel
    # centres as integers. Silent half-pixel bias, straight into any measurement.
    Wp = Hp = 200
    K = render3d.intrinsics_from_fov(45.0, Wp, Hp)
    V, F = _tilted_plane_mesh()
    out = render3d.render_mesh(V, F, pose=np.eye(4), intrinsics=K,
                               width=Wp, height=Hp)
    depth, sil = out["depth"], out["silhouette"]
    assert sil.sum() == Wp * Hp                       # the plane covers everything

    rows, cols = np.mgrid[0:Hp, 0:Wp].astype(np.float64)
    d_integer = _plane_depth(cols, rows, K)           # this library's convention
    d_half = _plane_depth(cols + 0.5, rows + 0.5, K)  # the OpenGL convention

    err_integer = float(np.abs(depth - d_integer).max())
    err_half = float(np.abs(depth - d_half).max())
    assert err_integer < 1e-12, err_integer
    # ...and the wrong convention really is distinguishable here, so this test
    # would fail loudly if the +0.5 came back (measured gap: ~6.6e-4 world units).
    assert err_half > 1e-5, err_half


def test_render_depth_to_points_roundtrip_closes():
    # depth -> camera.depth_to_points -> (a) reproject to the same pixels and
    # (b) land on the true plane. Both must close to ~machine precision; with the
    # old half-pixel mismatch (b) was biased by ~3.9e-4 world units, all one sign.
    Wp = Hp = 200
    K = render3d.intrinsics_from_fov(45.0, Wp, Hp)
    V, F = _tilted_plane_mesh()
    depth = render3d.render_mesh(V, F, pose=np.eye(4), intrinsics=K,
                                 width=Wp, height=Hp)["depth"]

    # render3d's depth is already the positive +Z that camera.py expects.
    grid = camera.depth_to_points(depth, K, organized=True)      # camera.py frame
    assert grid.shape == (Hp, Wp, 3)
    good = np.isfinite(grid).all(axis=-1)
    assert good.all()

    # (a) reprojection returns the original *integer* pixel coordinates.
    rows, cols = np.mgrid[0:Hp, 0:Wp].astype(np.float64)
    uv, _ = camera.project_points(grid.reshape(-1, 3), K)
    assert np.abs(uv[:, 0] - cols.ravel()).max() < 1e-9
    assert np.abs(uv[:, 1] - rows.ravel()).max() < 1e-9

    # (b) the points lie on the true plane. camera.py is y-down / +Z-forward and
    # render3d is y-up / -Z-forward, so convert: (x,y,z)_r3d = (x, -y, -z)_cam.
    # That is a handedness difference, not a pixel-centre one — it must be
    # applied whichever pixel convention is in force.
    P = grid.reshape(-1, 3)
    Pr = np.stack([P[:, 0], -P[:, 1], -P[:, 2]], axis=1)
    n = np.array([PLANE_A, PLANE_B, 1.0])
    signed = (Pr @ n + PLANE_D) / np.linalg.norm(n)               # world units
    assert np.abs(signed).max() < 1e-12, float(np.abs(signed).max())
    # The old failure was a *bias*, not noise: guard the mean too, so a future
    # regression cannot hide behind a symmetric tolerance.
    assert abs(float(signed.mean())) < 1e-13


def test_principal_point_is_the_image_centre():
    # Behavioural check that cx = (w-1)/2 is right under integer pixel centres:
    # mirroring the geometry about x = 0 must render to the exactly mirrored
    # image. With cx = w/2 the optical axis sits half a pixel off centre and this
    # fails (measured: 54 of 4096 silhouette pixels differ, depth off by 0.15).
    Wp = Hp = 64
    K = render3d.intrinsics_from_fov(45.0, Wp, Hp)
    V = np.array([[-0.6, -0.5, -3.0], [0.7, -0.4, -3.0],
                  [0.1, 0.65, -3.4], [-0.3, 0.2, -2.6]], np.float64)
    F = np.array([[0, 1, 2], [0, 2, 3]], np.int64)
    Vm = V * np.array([-1.0, 1.0, 1.0])                # mirror about x = 0
    Fm = F[:, ::-1].copy()                             # keep the winding outward

    a = render3d.render_mesh(V, F, pose=np.eye(4), intrinsics=K, width=Wp, height=Hp)
    b = render3d.render_mesh(Vm, Fm, pose=np.eye(4), intrinsics=K, width=Wp, height=Hp)
    assert a["silhouette"].sum() > 100                 # the scene is actually there
    assert np.array_equal(a["silhouette"], np.fliplr(b["silhouette"]))
    da, db = a["depth"], np.fliplr(b["depth"])
    both = np.isfinite(da) & np.isfinite(db)
    assert both.sum() > 100
    assert np.abs(da[both] - db[both]).max() < 1e-12


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
