"""Render and bridge an *imported* 3-D object into the 2-D / volume perception
stack (numpy + scipy only).

:mod:`mesh` imports a 3-D object into plain arrays ``(V, F)``; this module makes
that object *pay rent* inside a library that otherwise speaks images and volumes.
It renders a mesh to the sorts the rest of the library already consumes and
bridges the three representations a physical-AI project juggles — surface mesh,
occupancy volume and signed-distance field:

    import fullseye as fs
    V, F = fs.read_mesh("gripper_target.stl")
    view = fs.render_mesh(V, F)                 # -> depth / silhouette / normals
    sdf, origin = fs.mesh_to_sdf(V, F, pitch=0.01)   # collision / grasp SDF
    occ, origin = fs.voxelize_solid(V, F, 0.01)      # interior-filled occupancy

Why this earns its place next to a 2-D vision suite: a robot needs to *look at*
the thing it will grasp (synthetic depth / silhouette templates for pose and
detection), and to reason about the *inside* of it (a solid occupancy grid or an
SDF for collision and grasp metrics). None of that is a 2-D operator, and all of
it is exactly what evis / onocollo / hillco reach for when they turn a MuJoCo
asset or a CAD part into perception input.

Pixel-centre convention (**one convention, library-wide — do not add 0.5**):

    The centre of pixel ``(row=r, col=c)`` **is** the continuous image coordinate
    ``(u, v) = (c, r)``, exactly. Columns are ``u = 0 .. W-1`` and rows are
    ``v = 0 .. H-1``; a pixel therefore covers ``[c-0.5, c+0.5) x [r-0.5, r+0.5)``
    and the image spans ``[-0.5, W-0.5] x [-0.5, H-0.5]``. This is the OpenCV
    convention and it is the one :func:`camera.depth_to_points` uses (its
    ``v, u = np.mgrid[0:H, 0:W]`` are pixel *centres*), the one :mod:`cadmap` and
    :mod:`visualhull` use, and the one the calibration modules use. The competing
    OpenGL convention — pixel *corners* at integers, centres at ``index + 0.5`` —
    is **not** used anywhere here. Mixing the two does not raise: it silently
    biases every depth by half a pixel, which is a systematic metrology error
    (measured on a tilted plane at ``fx = 241.4``: back-projected points sat
    3.9e-4 world units off the true plane, all on the same side).

    Consequently :func:`intrinsics_from_fov` puts the principal point at
    ``cx = (W - 1) / 2``, ``cy = (H - 1) / 2`` — the centre of that span.

Relation to :mod:`camera` (a *different* question from the pixel-centre one):
:mod:`camera` is OpenCV-handed (``+X`` right, ``+Y`` **down**, ``+Z`` forward)
while this module is OpenGL-handed (``+X`` right, ``+Y`` **up**, ``-Z`` forward).
The two share the pixel-centre convention and the intrinsics ``K``, but the
camera-space axes differ, so a camera-space point converts as::

    (x, y, z)_camera_py = (x, -y, -z)_render3d

In particular a :func:`render_mesh` ``depth`` map can be fed straight to
``camera.depth_to_points(depth, K)`` — ``depth`` is already ``-z_render3d``,
i.e. the positive ``+Z`` that :mod:`camera` expects — and the resulting cloud is
in the :mod:`camera` (y-down) frame; negate ``y`` and ``z`` to get back to
render3d camera space.

Frame / array conventions (matching the rest of the library):

  * ``depth``      float64 (H, W). The metric distance *in front of* the camera
                   along the view axis (positive), ``background`` where no
                   triangle covers the pixel. A pinhole camera looks down its
                   local ``-Z`` (OpenGL convention), so a visible point has
                   camera-space ``z < 0`` and ``depth = -z_camera > 0``. This is
                   the ``image`` sort's grid with a metric (not [0,1]) range.
  * ``silhouette`` float64 (H, W) binary — the ``region`` sort. 1 where a triangle
                   covers the pixel, 0 elsewhere.
  * ``normals``    float64 (H, W, 3) — per-face (flat) camera-space unit surface
                   normal oriented toward the camera; the zero vector where empty.
  * volumes        float64 / bool (D, H, W) indexed ``[z, y, x]`` — the ``volume``
                   sort (CT/MRI/depth-stack layout). ``origin`` is the float64
                   (3,) world ``(x, y, z)`` coordinate of the *corner* of cell
                   ``[0, 0, 0]``, so a world point maps to
                   ``floor((p - origin) / pitch)`` — the same convention
                   :func:`mesh.voxelize` uses.

Provenance:

  * Z-buffer hidden-surface removal — Catmull, "A Subdivision Algorithm for
    Computer Display of Curved Surfaces" (1974).
  * Barycentric / edge-function triangle rasterisation — standard (Pineda, "A
    Parallel Algorithm for Polygon Rasterization", 1988).
  * Ray–triangle intersection — Möller & Trumbore, "Fast, Minimum Storage
    Ray/Triangle Intersection" (1997), used for the inside/outside parity test.
  * ``look_at`` follows the classic ``gluLookAt`` construction.

Honest limitations — nothing here claims a capability its tests do not prove:

  * The rasteriser is a **z-buffer**: nearest opaque surface only. No
    transparency, no shading/lighting, no anti-aliasing (a pixel is in or out by
    its centre), and **no near-plane clipping** — a triangle with any vertex at
    or behind the camera is dropped whole, so a mesh that straddles the camera
    plane loses those faces. Frame the camera outside the mesh.
  * ``normals`` are **per-face flat** (one normal per triangle), not smooth /
    interpolated — a curved surface shows facets.
  * :func:`mesh_to_sdf` computes the **unsigned** distance from a *sampled*
    surface approximation (``mesh.sample_surface`` + a KD-tree), so it is an
    approximate distance whose error shrinks with the sample count; it slightly
    over-estimates near the surface. The **sign** comes from a +X ray-parity
    (even/odd crossing) test, which is only well defined for a **watertight**
    (closed, non-self-intersecting) mesh; on an open mesh the interior is
    ill-defined and the sign is unreliable.
  * :func:`voxelize_solid` likewise assumes a **watertight** mesh — a voxel is
    solid iff its centre is inside by the same odd-crossing parity. Sample points
    are nudged off the grid lattice by a sub-pitch epsilon so a ray never lands
    exactly on a shared edge / vertex (which would double-count a crossing); a
    coincidental exact hit on a non-perturbed feature can still misclassify a
    single voxel.

Fail-closed on untrusted geometry (like :mod:`mesh`): ``V`` / ``F`` shapes and
index ranges are validated, non-finite vertices are rejected, and the output size
is capped **before** allocation — ``width * height`` against ``MAX_PIXELS`` and
the voxel-grid cell count against ``MAX_VOXELS`` — so a hostile mesh or a tiny
pitch cannot allocate an unbounded buffer. Degenerate cameras / intrinsics raise
``ValueError``.
"""
from __future__ import annotations

import numpy as np

import mesh

__all__ = [
    "render_mesh", "look_at", "intrinsics_from_fov", "auto_view",
    "mesh_to_sdf", "voxelize_solid", "marching_cubes",
    "MAX_PIXELS", "MAX_VOXELS",
]

#: Refuse a render larger than this many pixels (``width * height``).
MAX_PIXELS = 1 << 24            # 16,777,216 px (e.g. 4096 x 4096)
#: Refuse a voxel grid with more cells than this (guards the float64 SDF too).
MAX_VOXELS = 1 << 25            # ~33.5 M cells

_NEAR_EPS = 1e-9                # a vertex this close to / behind the camera is culled
_DET_EPS = 1e-12               # parallel ray / degenerate triangle threshold
_BARY_EPS = 1e-9               # pixel-coverage tolerance on barycentric coords
#: Distinct sub-pitch nudges keep interior-test rays off shared edges / vertices.
_EPS_P, _EPS_Q = 1.9e-4, 3.7e-4


# --------------------------------------------------------------------------- #
# validation (mirrors mesh.py's fail-closed guards)                           #
# --------------------------------------------------------------------------- #
def _mesh_arrays(V, F, allow_empty_faces: bool = False):
    """Coerce and validate ``(V, F)`` the way :mod:`mesh` does: float64 (nv, 3)
    finite vertices, int64 (nf, 3) faces with every index in range."""
    Vv = mesh._finite_points(V, "vertices", "render3d")
    Ff = np.asarray(F, np.int64)
    if Ff.size == 0:
        if not allow_empty_faces:
            raise ValueError("mesh has no faces")
        return Vv, np.zeros((0, 3), np.int64)
    if Ff.ndim != 2 or Ff.shape[1] != 3:
        raise ValueError("faces must be (M, 3) triangles, got %r" % (Ff.shape,))
    lo, hi = int(Ff.min()), int(Ff.max())
    if lo < 0 or hi >= Vv.shape[0]:
        raise ValueError("face index %d out of range for %d vertices"
                         % (hi if hi >= Vv.shape[0] else lo, Vv.shape[0]))
    return Vv, Ff


def _check_pose(pose) -> np.ndarray:
    P = np.asarray(pose, np.float64)
    if P.shape != (4, 4):
        raise ValueError("pose must be a 4x4 matrix, got %r" % (P.shape,))
    if not np.isfinite(P).all():
        raise ValueError("pose contains non-finite values")
    R = P[:3, :3]
    if abs(float(np.linalg.det(R))) < 1e-9:
        raise ValueError("pose rotation is degenerate (near-zero determinant)")
    return P


def _check_intrinsics(K) -> np.ndarray:
    M = np.asarray(K, np.float64)
    if M.shape != (3, 3):
        raise ValueError("intrinsics must be a 3x3 matrix, got %r" % (M.shape,))
    if not np.isfinite(M).all():
        raise ValueError("intrinsics contain non-finite values")
    if abs(M[0, 0]) < 1e-12 or abs(M[1, 1]) < 1e-12:
        raise ValueError("intrinsics have a zero focal length (fx or fy)")
    return M


def _check_size(width: int, height: int):
    w, h = int(width), int(height)
    if w <= 0 or h <= 0:
        raise ValueError("width and height must be positive, got %dx%d" % (w, h))
    if float(w) * float(h) > MAX_PIXELS:
        raise ValueError("%dx%d = %.3g pixels, over the %d cap (render3d.MAX_PIXELS)"
                         % (w, h, float(w) * float(h), MAX_PIXELS))
    return w, h


# --------------------------------------------------------------------------- #
# camera helpers                                                              #
# --------------------------------------------------------------------------- #
def look_at(eye, target, up=(0.0, 0.0, 1.0)) -> np.ndarray:
    """Build a 4x4 world->camera pose for a camera at *eye* looking at *target*.

    Follows the ``gluLookAt`` construction: the camera looks down its local
    ``-Z``, with local ``+X`` right and ``+Y`` up. Returns float64 (4, 4). Raises
    ``ValueError`` if *eye* and *target* coincide or *up* is parallel to the view
    direction (the frame would be degenerate)."""
    e = np.asarray(eye, np.float64).reshape(3)
    t = np.asarray(target, np.float64).reshape(3)
    u = np.asarray(up, np.float64).reshape(3)
    f = t - e
    fn = np.linalg.norm(f)
    if not np.isfinite(fn) or fn < 1e-12:
        raise ValueError("look_at: eye and target coincide")
    f = f / fn
    s = np.cross(f, u)
    sn = np.linalg.norm(s)
    if sn < 1e-9:
        raise ValueError("look_at: 'up' is parallel to the view direction")
    s = s / sn
    u2 = np.cross(s, f)
    R = np.stack([s, u2, -f], axis=0)             # rows: right, up, -forward
    pose = np.eye(4, dtype=np.float64)
    pose[:3, :3] = R
    pose[:3, 3] = -R @ e
    return pose


def intrinsics_from_fov(fov_deg: float, width: int, height: int) -> np.ndarray:
    """Pinhole intrinsics ``K`` (3x3) for a **vertical** field of view *fov_deg*.

    Square pixels (``fx == fy``). The principal point sits at the image centre
    **expressed in this library's pixel-centre convention**: the centre of pixel
    ``(row=r, col=c)`` is the continuous coordinate ``(u, v) = (c, r)``, so the
    columns run ``0 .. w-1`` and their midpoint — the image centre — is
    ``cx = (w - 1) / 2`` (likewise ``cy = (h - 1) / 2``), *not* ``w / 2``.
    ``w / 2`` would be the centre only under the OpenGL "pixel corners are
    integers" convention, which this library does not use; using it here puts the
    optical axis half a pixel off centre, and a mirrored scene then no longer
    renders to a mirrored image (measured: 54 of 4096 silhouette pixels disagree,
    depth off by up to 0.15 world units, on a 64x64 tilted quad). Matches
    OpenCV's ``initCameraMatrix2D``, which also uses ``(size - 1) * 0.5``, and
    :mod:`calibration3d`, which already takes ``((w-1)/2, (h-1)/2)`` as the image
    centre.

    Returns float64 (3, 3). Raises ``ValueError`` for a non-positive size or a
    field of view outside ``(0, 180)`` degrees."""
    w, h = int(width), int(height)
    if w <= 0 or h <= 0:
        raise ValueError("width and height must be positive, got %dx%d" % (w, h))
    fov = float(fov_deg)
    if not np.isfinite(fov) or fov <= 0.0 or fov >= 180.0:
        raise ValueError("fov_deg must be in (0, 180), got %r" % (fov_deg,))
    f = (h * 0.5) / np.tan(np.deg2rad(fov) * 0.5)
    K = np.array([[f, 0.0, w * 0.5],
                  [0.0, f, h * 0.5],
                  [0.0, 0.0, 1.0]], np.float64)
    return K


def auto_view(V, margin: float = 1.2, width: int = 256, height: int = 256):
    """Frame the mesh's bounding sphere -> ``(pose, K)``.

    Places the camera on ``+Z`` from the vertex centroid looking back down ``-Z``
    at a distance where the bounding sphere (grown by *margin*) fits the smaller
    image dimension, using a 45 deg vertical field of view. This is the default
    view :func:`render_mesh` uses when *pose* / *intrinsics* are not given.
    Returns ``(pose (4,4), K (3,3))``."""
    P = mesh._finite_points(V, "vertices", "auto_view")
    if P.shape[0] == 0:
        raise ValueError("auto_view needs at least one vertex")
    w, h = int(width), int(height)
    lo, hi = P.min(axis=0), P.max(axis=0)
    center = 0.5 * (lo + hi)
    radius = float(np.linalg.norm(P - center, axis=1).max())
    if not np.isfinite(radius) or radius <= 0.0:
        radius = 1.0                                # a single point: pick a scale
    m = max(float(margin), 1e-3)
    K = intrinsics_from_fov(45.0, w, h)
    f = float(K[1, 1])
    half_min = 0.5 * min(w, h)
    dist = m * f * radius / max(half_min, 1e-9)     # screen radius f*r/dist <= half_min/m
    dist = max(dist, radius * 1e-3 + 1e-6)
    eye = center + np.array([0.0, 0.0, dist], np.float64)
    pose = look_at(eye, center, up=(0.0, 1.0, 0.0))
    return pose, K


def _default_view(V, width, height):
    return auto_view(V, margin=1.2, width=width, height=height)


# --------------------------------------------------------------------------- #
# rasteriser (z-buffer)                                                       #
# --------------------------------------------------------------------------- #
def render_mesh(V, F, pose=None, intrinsics=None, width: int = 256,
                height: int = 256, background=np.inf) -> dict:
    """Rasterise a triangle mesh to a depth image, silhouette and normal map.

    Returns a ``dict`` with:

      * ``depth``      float64 (H, W) — metric distance in front of the camera
                       (positive), *background* where no triangle covers the pixel.
      * ``silhouette`` float64 (H, W) binary ``region`` — 1 where covered.
      * ``normals``    float64 (H, W, 3) — per-face camera-space unit normal
                       toward the camera; zero where empty.

    *pose* is a 4x4 object->camera matrix (see :func:`look_at`); *intrinsics* is a
    3x3 pinhole ``K`` with ``fx, fy, cx, cy`` (see :func:`intrinsics_from_fov`).
    When either is ``None`` the missing one is taken from :func:`auto_view`, which
    frames the mesh. A correct barycentric **z-buffer** keeps the nearest surface
    per pixel (Catmull 1974); depth is perspective-correct (linear in ``1/z``).

    **Pixel centres are at integer coordinates**: ``depth[r, c]`` is the depth
    sampled by the ray through the continuous image point ``(u, v) = (c, r)`` —
    *not* ``(c + 0.5, r + 0.5)``. This is the library-wide convention (see the
    module docstring), so the result lines up pixel-for-pixel with
    :func:`camera.depth_to_points`, :mod:`cadmap` and :mod:`visualhull`; feeding
    ``depth`` to ``camera.depth_to_points(depth, K)`` back-projects onto the true
    surface to machine precision instead of half a pixel off it.

    Vectorised per triangle (each triangle rasterises its own screen bounding box
    with numpy) — there is no Python loop over image pixels. Empty ``F`` yields an
    all-*background* image. Raises ``ValueError`` on a bad mesh, a degenerate
    camera / intrinsics, or a ``width * height`` over ``MAX_PIXELS``."""
    w, h = _check_size(width, height)
    Vv, Ff = _mesh_arrays(V, F, allow_empty_faces=True)

    if pose is None or intrinsics is None:
        dpose, dK = _default_view(Vv, w, h)
    pose = dpose if pose is None else _check_pose(pose)
    K = dK if intrinsics is None else _check_intrinsics(intrinsics)

    fx, fy, cx, cy = float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2])

    zbuf = np.full((h, w), np.inf, np.float64)      # z-test buffer (nearest wins)
    sil = np.zeros((h, w), np.float64)
    normals = np.zeros((h, w, 3), np.float64)

    if Ff.shape[0] == 0:
        depth = np.where(sil > 0, zbuf, background).astype(np.float64)
        return {"depth": depth, "silhouette": sil, "normals": normals}

    R, t = pose[:3, :3], pose[:3, 3]
    Vc = Vv @ R.T + t                               # camera space (nv, 3)
    depth_v = -Vc[:, 2]                             # camera looks -Z; front is z<0
    safe = np.where(depth_v > _NEAR_EPS, depth_v, np.nan)
    su = fx * (Vc[:, 0] / safe) + cx               # screen column (x)
    sv = cy - fy * (Vc[:, 1] / safe)               # screen row (y up -> row down)

    A, B, C = Vc[Ff[:, 0]], Vc[Ff[:, 1]], Vc[Ff[:, 2]]
    fnorm = np.cross(B - A, C - A)                  # per-face normal (camera space)
    fn = np.linalg.norm(fnorm, axis=1, keepdims=True)
    fnorm = fnorm / np.maximum(fn, 1e-12)
    centroid = (A + B + C) / 3.0
    flip = np.einsum("ij,ij->i", fnorm, centroid) > 0.0   # orient toward camera
    fnorm[flip] *= -1.0

    for ti in range(Ff.shape[0]):
        i0, i1, i2 = Ff[ti]
        d0, d1, d2 = depth_v[i0], depth_v[i1], depth_v[i2]
        if not (d0 > _NEAR_EPS and d1 > _NEAR_EPS and d2 > _NEAR_EPS):
            continue                                # no near-plane clipping (documented)
        u0, u1, u2 = su[i0], su[i1], su[i2]
        v0, v1, v2 = sv[i0], sv[i1], sv[i2]
        cmin = int(np.floor(min(u0, u1, u2)))
        cmax = int(np.ceil(max(u0, u1, u2)))
        rmin = int(np.floor(min(v0, v1, v2)))
        rmax = int(np.ceil(max(v0, v1, v2)))
        cmin, cmax = max(cmin, 0), min(cmax, w - 1)
        rmin, rmax = max(rmin, 0), min(rmax, h - 1)
        if cmin > cmax or rmin > rmax:
            continue
        denom = (v1 - v2) * (u0 - u2) + (u2 - u1) * (v0 - v2)
        if abs(denom) < _DET_EPS:
            continue                                # degenerate (zero screen area)
        # Pixel-centre convention (see the module docstring): the centre of pixel
        # ``(row=r, col=c)`` IS the continuous coordinate ``(u, v) = (c, r)`` —
        # integer, matching :func:`camera.depth_to_points`'s ``np.mgrid[0:H, 0:W]``.
        # Do NOT add 0.5 here: that is the OpenGL "pixel corners are integers"
        # convention and mixing the two silently shifts depth by half a pixel.
        cols = np.arange(cmin, cmax + 1) + 0.5
        rows = np.arange(rmin, rmax + 1) + 0.5
        px, py = np.meshgrid(cols, rows)            # (bh, bw)
        inv = 1.0 / denom
        l0 = ((v1 - v2) * (px - u2) + (u2 - u1) * (py - v2)) * inv
        l1 = ((v2 - v0) * (px - u2) + (u0 - u2) * (py - v2)) * inv
        l2 = 1.0 - l0 - l1
        inside = (l0 >= -_BARY_EPS) & (l1 >= -_BARY_EPS) & (l2 >= -_BARY_EPS)
        if not inside.any():
            continue
        inv_d = l0 / d0 + l1 / d1 + l2 / d2         # perspective-correct depth
        with np.errstate(divide="ignore", invalid="ignore"):
            zpix = 1.0 / inv_d
        sub_z = zbuf[rmin:rmax + 1, cmin:cmax + 1]
        closer = inside & np.isfinite(zpix) & (zpix < sub_z)
        if not closer.any():
            continue
        sub_z[closer] = zpix[closer]
        sil[rmin:rmax + 1, cmin:cmax + 1][closer] = 1.0
        nblock = normals[rmin:rmax + 1, cmin:cmax + 1]
        nblock[closer] = fnorm[ti]

    depth = np.where(sil > 0, zbuf, background).astype(np.float64)
    return {"depth": depth, "silhouette": sil, "normals": normals}


# --------------------------------------------------------------------------- #
# inside / outside parity (Möller-Trumbore) — shared by SDF & solid voxels    #
# --------------------------------------------------------------------------- #
def _line_crossings(A, B, C, o, axis: int) -> np.ndarray:
    """Sorted coordinates (along world *axis*) where the infinite line through *o*
    parallel to *axis* crosses the triangles ``(A, B, C)``. Vectorised
    Möller-Trumbore; both sides of *o* are returned (it is a line, not a ray) so a
    caller can count crossings on either side for an even/odd parity test."""
    d = np.zeros(3, np.float64)
    d[axis] = 1.0
    e1 = B - A                                      # (M, 3)
    e2 = C - A
    hvec = np.cross(d, e2)                          # (M, 3)
    det = np.einsum("ij,ij->i", e1, hvec)
    nonpar = np.abs(det) > _DET_EPS
    inv = np.zeros_like(det)
    inv[nonpar] = 1.0 / det[nonpar]
    s = o[None, :] - A
    u = np.einsum("ij,ij->i", s, hvec) * inv
    q = np.cross(s, e1)
    v = q[:, axis] * inv                            # d . q  (d is a unit basis axis)
    t = np.einsum("ij,ij->i", e2, q) * inv
    valid = (nonpar & (u >= -_BARY_EPS) & (u <= 1.0 + _BARY_EPS)
             & (v >= -_BARY_EPS) & (u + v <= 1.0 + _BARY_EPS))
    coords = o[axis] + t[valid]
    coords = coords[np.isfinite(coords)]
    coords.sort()
    return coords


def _interior_mask(A, B, C, origin, dims, pitch: float, axis: int) -> np.ndarray:
    """Boolean occupancy of voxel *centres* inside a watertight mesh, by odd
    crossing parity of a line parallel to world *axis*.

    *origin* is world ``(x, y, z)``; *dims* is ``(nx, ny, nz)`` cell counts.
    Returns a world-indexed bool array ``(nx, ny, nz)`` (the caller transposes to
    the ``(D, H, W)`` volume layout). Rays are nudged off the lattice by a
    sub-pitch epsilon so they never strike a shared edge / vertex exactly."""
    n = (int(dims[0]), int(dims[1]), int(dims[2]))
    occ = np.zeros(n, bool)
    a = int(axis)
    p, q = [ax for ax in (0, 1, 2) if ax != a]
    centers_a = origin[a] + (np.arange(n[a]) + 0.5) * pitch
    for ip in range(n[p]):
        cp = origin[p] + (ip + 0.5) * pitch + _EPS_P * pitch
        for iq in range(n[q]):
            cq = origin[q] + (iq + 0.5) * pitch + _EPS_Q * pitch
            o = np.zeros(3, np.float64)
            o[p], o[q] = cp, cq
            cross = _line_crossings(A, B, C, o, a)
            if cross.size == 0:
                continue
            cnt = np.searchsorted(cross, centers_a, side="left")
            inside = (cnt % 2) == 1
            if not inside.any():
                continue
            sl = [None, None, None]
            sl[p], sl[q], sl[a] = ip, iq, slice(None)
            occ[tuple(sl)] = inside
    return occ


def _grid_dims(lo, hi, pitch: float, mode: str):
    """Per-axis cell counts over ``[lo, hi]`` at *pitch*. ``mode='cover'`` matches
    :func:`mesh.voxelize` (``floor(span/pitch) + 1``); ``mode='ceil'`` rounds up
    to fully enclose a padded box. Caps the total cell count before allocation."""
    span = np.asarray(hi, np.float64) - np.asarray(lo, np.float64)
    if mode == "cover":
        dims = np.maximum(np.floor(span / pitch) + 1.0, 1.0)
    else:
        dims = np.maximum(np.ceil(span / pitch), 1.0)
    cells = float(np.prod(dims))
    if not np.isfinite(cells) or cells > MAX_VOXELS:
        raise ValueError("pitch %g gives a %s grid (%.3g cells), over the %d cap "
                         "(render3d.MAX_VOXELS) — use a larger pitch"
                         % (pitch, tuple(int(d) for d in dims), cells, MAX_VOXELS))
    return dims.astype(np.int64)


# --------------------------------------------------------------------------- #
# mesh <-> volume <-> SDF bridges                                             #
# --------------------------------------------------------------------------- #
def voxelize_solid(V, F, pitch: float, fill_axis: int = 2):
    """Solid (interior-filled) voxel occupancy of a watertight mesh -> ``(occ,
    origin)``.

    Complements :func:`mesh.voxelize` (surface only): a cell is occupied iff its
    centre lies **inside** the mesh, decided by scanline parity — the count of
    surface crossings of a line parallel to world axis *fill_axis* (0=x, 1=y,
    2=z) is odd. *occ* is a bool ``(D, H, W)`` volume indexed ``[z, y, x]`` and
    *origin* is the float64 (3,) bounding-box minimum (world ``x, y, z``), on the
    same grid :func:`mesh.voxelize` would use (``floor(span / pitch) + 1`` cells
    per axis) so the two are directly comparable.

    Assumes a **watertight** mesh — for an open or self-intersecting mesh the
    odd-crossing interior is ill-defined. Sample rays are nudged off the grid
    lattice so a shared edge / vertex is not double-counted, but a coincidental
    exact feature hit can still misclassify a lone voxel. Raises ``ValueError`` on
    a bad mesh, a non-positive pitch, an out-of-range *fill_axis*, or a grid over
    ``MAX_VOXELS``."""
    Vv, Ff = _mesh_arrays(V, F)
    pitch = float(pitch)
    if not np.isfinite(pitch) or pitch <= 0.0:
        raise ValueError("pitch must be > 0, got %r" % (pitch,))
    if int(fill_axis) not in (0, 1, 2):
        raise ValueError("fill_axis must be 0, 1 or 2 (x, y, z), got %r" % (fill_axis,))
    A, B, C = Vv[Ff[:, 0]], Vv[Ff[:, 1]], Vv[Ff[:, 2]]
    lo = np.minimum(np.minimum(A.min(0), B.min(0)), C.min(0))
    hi = np.maximum(np.maximum(A.max(0), B.max(0)), C.max(0))
    dims = _grid_dims(lo, hi, pitch, "cover")
    occ_world = _interior_mask(A, B, C, lo, dims, pitch, int(fill_axis))
    occ = np.ascontiguousarray(occ_world.transpose(2, 1, 0))     # (nx,ny,nz)->(nz,ny,nx)
    return occ, lo.astype(np.float64)


def mesh_to_sdf(V, F, pitch=None, grid=None, pad: float = 0.1, samples=None):
    """Signed-distance field of a watertight mesh -> ``(sdf, origin)``.

    *sdf* is a float64 ``(D, H, W)`` volume indexed ``[z, y, x]``: the (approximate)
    Euclidean distance from each voxel centre to the mesh surface, **negative
    inside** and positive outside. *origin* is the float64 (3,) world ``(x, y, z)``
    corner of cell ``[0, 0, 0]``.

    The grid pads the mesh bounding box by *pad* times its largest extent on every
    side. Give either *pitch* (world cell size) or *grid* (an int = cells across
    the largest padded span); with neither, a 32-cell grid is used.

    Method (and its honest limits): the **unsigned** distance is the nearest of a
    dense area-weighted surface sampling (``mesh.sample_surface`` + a
    ``scipy.spatial.cKDTree``) — an approximation that improves with *samples* and
    slightly over-estimates near the surface. The **sign** is a +X ray-parity
    (even/odd crossing) inside test, which requires a **watertight** mesh; on an
    open mesh the interior — and thus the sign — is undefined. Raises
    ``ValueError`` on a bad mesh, a non-positive pitch, or a grid over
    ``MAX_VOXELS``."""
    from scipy.spatial import cKDTree

    Vv, Ff = _mesh_arrays(V, F)
    A, B, C = Vv[Ff[:, 0]], Vv[Ff[:, 1]], Vv[Ff[:, 2]]
    lo = np.minimum(np.minimum(A.min(0), B.min(0)), C.min(0))
    hi = np.maximum(np.maximum(A.max(0), B.max(0)), C.max(0))
    extent = float((hi - lo).max())
    if not np.isfinite(extent) or extent <= 0.0:
        raise ValueError("degenerate mesh: zero bounding-box extent, no SDF to build")
    padw = float(pad) * extent
    lo_p, hi_p = lo - padw, hi + padw
    span = float((hi_p - lo_p).max())

    if pitch is not None:
        pitch = float(pitch)
        if not np.isfinite(pitch) or pitch <= 0.0:
            raise ValueError("pitch must be > 0, got %r" % (pitch,))
    else:
        g = int(grid) if grid is not None else 32
        if g <= 0:
            raise ValueError("grid must be > 0, got %r" % (grid,))
        pitch = span / g

    dims = _grid_dims(lo_p, hi_p, pitch, "ceil")
    nx, ny, nz = int(dims[0]), int(dims[1]), int(dims[2])

    ns = int(samples) if samples is not None else max(20000, 8 * Ff.shape[0])
    surf = mesh.sample_surface(Vv, Ff, ns, seed=0)
    tree = cKDTree(surf)

    xc = lo_p[0] + (np.arange(nx) + 0.5) * pitch
    yc = lo_p[1] + (np.arange(ny) + 0.5) * pitch
    zc = lo_p[2] + (np.arange(nz) + 0.5) * pitch
    ZZ, YY, XX = np.meshgrid(zc, yc, xc, indexing="ij")     # (nz, ny, nx) = (D, H, W)
    centers = np.stack([XX, YY, ZZ], axis=-1).reshape(-1, 3)
    dist, _ = tree.query(centers)
    dist = dist.reshape(nz, ny, nx)

    inside_world = _interior_mask(A, B, C, lo_p, dims, pitch, 0)   # +X parity
    inside = inside_world.transpose(2, 1, 0)                       # -> (D, H, W)
    sdf = np.where(inside, -dist, dist).astype(np.float64)
    return sdf, lo_p.astype(np.float64)


def marching_cubes(vol, level: float):
    """Extract a triangle mesh from a scalar volume at iso-value *level* ->
    ``(V, F)`` matching :mod:`mesh` (float64 (nv, 3), int64 (nf, 3)).

    **Optional** — thin wrapper over ``skimage.measure.marching_cubes`` (Lorensen
    & Cline 1987), imported lazily so :mod:`render3d`'s numpy/scipy core never
    depends on scikit-image. Turns a :func:`mesh_to_sdf` field (``level=0``) or a
    :func:`voxelize_solid` occupancy back into a surface. Raises a clear
    ``ImportError`` telling the caller to ``pip install scikit-image`` when the
    optional extra is absent. Vertices are in voxel-index space; add your grid
    ``origin`` and multiply by ``pitch`` to place them in world coordinates."""
    try:
        from skimage import measure
    except ImportError as e:                        # pragma: no cover - extra absent
        raise ImportError("marching_cubes needs scikit-image (an optional extra): "
                          "pip install scikit-image") from e
    A = np.asarray(vol, np.float64)
    if A.ndim != 3:
        raise ValueError("vol must be a 3-D volume (D, H, W), got %r" % (A.shape,))
    verts, faces, _, _ = measure.marching_cubes(A, level=float(level))
    return np.ascontiguousarray(verts, np.float64), np.ascontiguousarray(faces, np.int64)
