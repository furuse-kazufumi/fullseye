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
    K = np.array([[f, 0.0, (w - 1) * 0.5],
                  [0.0, f, (h - 1) * 0.5],
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
                height: int = 256, background=np.inf, *,
                attributes: bool = False) -> dict:
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
    # Per-pixel triangle id and perspective-correct barycentric weights. These let a
    # caller interpolate ANY per-vertex quantity exactly the way depth is interpolated
    # here, instead of guessing it from nearby vertices in 3-D. Measured 2026-09-02:
    # ``render_ao`` used inverse-distance weighting over the 3 nearest vertices, which
    # turns a coarse per-vertex field into polygonal cells — the mottling visible on
    # the ground plane of the article's hero render. Off by default because the shadow
    # pass calls this at 512x512 six times and only ever reads ``depth``.
    want_attr = bool(attributes)
    face = np.full((h, w), -1, np.int64) if want_attr else None
    bary = np.zeros((h, w, 3), np.float64) if want_attr else None

    def _pack(depth_img):
        out = {"depth": depth_img, "silhouette": sil, "normals": normals}
        if want_attr:
            out["face"] = face
            out["bary"] = bary
        return out

    if Ff.shape[0] == 0:
        depth = np.where(sil > 0, zbuf, background).astype(np.float64)
        return _pack(depth)

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

    # ---- vectorised rasterisation (2026-09-03) ---------------------------------
    # Until 2026-09-03 this was a Python ``for ti in range(M)`` loop that rasterised
    # each triangle's own screen bounding box with numpy. That is fine for 50k
    # faces (~1 s) but the Itokawa hero now subdivides the Gaskell model to
    # ~1.5 m facets (≥ 500k faces) and the loop alone cost ~40 s per pass, three
    # passes per render. The loop is replaced by a **chunked all-triangles-at-once**
    # rasteriser that evaluates *exactly the same arithmetic* (same barycentric
    # formulas, same perspective-correct ``1/z`` interpolation, same
    # ``_BARY_EPS`` / ``_DET_EPS``) over the flattened (triangle, pixel) pairs of
    # every bounding box. Tie-breaking is preserved too: the loop kept the FIRST
    # triangle that reached a pixel at a given depth (strict ``<``), so the pairs
    # are lexsorted by (pixel, depth, triangle index) before the nearest-per-pixel
    # winner is taken and compared strictly against the running z-buffer.
    # ``tests/test_render3d.py::test_vectorised_rasteriser_matches_loop`` pins the
    # bit-exact equivalence (depth / silhouette / normals / face / bary).
    _raster_all(Ff, su, sv, depth_v, fnorm, w, h, zbuf, sil, normals,
                face, bary, want_attr)

    depth = np.where(sil > 0, zbuf, background).astype(np.float64)
    return _pack(depth)


#: Upper bound on flattened (triangle, pixel) pairs held in memory per chunk.
_RASTER_PAIR_CHUNK = 3_000_000


def _raster_all(Ff, su, sv, depth_v, fnorm, w, h, zbuf, sil, normals,
                face, bary, want_attr) -> None:
    """Rasterise every triangle into the shared buffers (in place), vectorised over
    (triangle, pixel) pairs and chunked to ``_RASTER_PAIR_CHUNK`` pairs.

    Semantics are identical to the historical per-triangle loop (see the caller):
    pixel centres at integer coordinates, no near-plane clipping (a triangle with
    any vertex at depth ≤ ``_NEAR_EPS`` is dropped), degenerate screen triangles
    dropped, first-triangle-wins on exact depth ties."""
    M = Ff.shape[0]
    if M == 0:
        return
    d = depth_v[Ff]                                   # (M,3)
    u = su[Ff]
    v = sv[Ff]
    ok = np.all(d > _NEAR_EPS, axis=1)
    with np.errstate(invalid="ignore"):
        cmin = np.floor(np.nanmin(u, axis=1))
        cmax = np.ceil(np.nanmax(u, axis=1))
        rmin = np.floor(np.nanmin(v, axis=1))
        rmax = np.ceil(np.nanmax(v, axis=1))
    ok &= np.isfinite(cmin) & np.isfinite(cmax) & np.isfinite(rmin) & np.isfinite(rmax)
    cmin = np.clip(np.where(ok, cmin, 0), 0, w - 1).astype(np.int64)
    cmax = np.clip(np.where(ok, cmax, -1), -1, w - 1).astype(np.int64)
    rmin = np.clip(np.where(ok, rmin, 0), 0, h - 1).astype(np.int64)
    rmax = np.clip(np.where(ok, rmax, -1), -1, h - 1).astype(np.int64)
    ok &= (cmin <= cmax) & (rmin <= rmax)
    u0, u1, u2 = u[:, 0], u[:, 1], u[:, 2]
    v0, v1, v2 = v[:, 0], v[:, 1], v[:, 2]
    with np.errstate(invalid="ignore"):
        denom = (v1 - v2) * (u0 - u2) + (u2 - u1) * (v0 - v2)
    ok &= np.isfinite(denom) & (np.abs(denom) >= _DET_EPS)
    ids = np.nonzero(ok)[0]
    if ids.size == 0:
        return
    bw = cmax[ids] - cmin[ids] + 1
    bh = rmax[ids] - rmin[ids] + 1
    npx = bw * bh
    cum = np.cumsum(npx)
    inv_all = np.zeros(M, np.float64)
    inv_all[ids] = 1.0 / denom[ids]
    d0, d1, d2 = d[:, 0], d[:, 1], d[:, 2]

    start = 0
    n_ok = ids.size
    while start < n_ok:
        base = cum[start - 1] if start > 0 else 0
        end = int(np.searchsorted(cum, base + _RASTER_PAIR_CHUNK, side="right"))
        end = max(end, start + 1)                      # at least one triangle per chunk
        end = min(end, n_ok)
        sel = ids[start:end]
        cnt = npx[start:end]
        total = int(cnt.sum())
        tri = np.repeat(sel, cnt)
        offs = np.repeat(np.cumsum(cnt) - cnt, cnt)
        k = np.arange(total, dtype=np.int64) - offs
        bw_r = np.repeat(bw[start:end], cnt)
        # Pixel-centre convention (see the module docstring): the centre of pixel
        # ``(row=r, col=c)`` IS the continuous coordinate ``(u, v) = (c, r)`` —
        # integer, matching :func:`camera.depth_to_points`'s ``np.mgrid[0:H, 0:W]``.
        # Do NOT add 0.5 here: that is the OpenGL "pixel corners are integers"
        # convention and mixing the two silently shifts depth by half a pixel.
        pr = np.repeat(rmin[sel], cnt) + k // bw_r
        pc = np.repeat(cmin[sel], cnt) + k % bw_r
        px = pc.astype(np.float64)
        py = pr.astype(np.float64)
        inv = inv_all[tri]
        tu0, tu1, tu2 = u0[tri], u1[tri], u2[tri]
        tv0, tv1, tv2 = v0[tri], v1[tri], v2[tri]
        l0 = ((tv1 - tv2) * (px - tu2) + (tu2 - tu1) * (py - tv2)) * inv
        l1 = ((tv2 - tv0) * (px - tu2) + (tu0 - tu2) * (py - tv2)) * inv
        l2 = 1.0 - l0 - l1
        inside = (l0 >= -_BARY_EPS) & (l1 >= -_BARY_EPS) & (l2 >= -_BARY_EPS)
        td0, td1, td2 = d0[tri], d1[tri], d2[tri]
        inv_d = l0 / td0 + l1 / td1 + l2 / td2         # perspective-correct depth
        with np.errstate(divide="ignore", invalid="ignore"):
            zpix = 1.0 / inv_d
        keep = inside & np.isfinite(zpix)
        if not keep.any():
            start = end
            continue
        tri, pr, pc, zpix = tri[keep], pr[keep], pc[keep], zpix[keep]
        l0, l1, l2 = l0[keep], l1[keep], l2[keep]
        td0, td1, td2 = td0[keep], td1[keep], td2[keep]
        pix = pr * w + pc
        # nearest per pixel, first triangle wins exact ties (= the loop's strict '<')
        order = np.lexsort((tri, zpix, pix))
        pix_s = pix[order]
        first = np.empty(pix_s.size, bool)
        first[0] = True
        first[1:] = pix_s[1:] != pix_s[:-1]
        win = order[first]
        closer = zpix[win] < zbuf.reshape(-1)[pix[win]]
        win = win[closer]
        if win.size:
            r_w, c_w = pr[win], pc[win]
            zbuf[r_w, c_w] = zpix[win]
            sil[r_w, c_w] = 1.0
            normals[r_w, c_w] = fnorm[tri[win]]
            if want_attr:
                face[r_w, c_w] = tri[win]
                # Perspective-correct vertex weights: the screen-space barycentric
                # ``l_i`` divided by that vertex's depth and renormalised by the same
                # ``1/zpix`` the depth interpolation above uses. Screen-space ``l_i``
                # alone would be affine-correct only — on the ground plane, seen at a
                # grazing angle, that is exactly where the error is largest.
                zw = zpix[win]
                bary[r_w, c_w] = np.stack(
                    [l0[win] * zw / td0[win], l1[win] * zw / td1[win],
                     l2[win] * zw / td2[win]], axis=-1)
        start = end


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


# --------------------------------------------------------------------------- #
# Terrain relief — fBm displacement, sea/highland mask, boulder scattering     #
# --------------------------------------------------------------------------- #
# 2026-09-03: the Itokawa hero looked "like a potato". Two causes — the turntable
# mesh came from a 3000-point cloud voxelised at 72³ (no relief survives), and a
# smooth shape model has no metre-scale roughness (the Gaskell model resolves
# ~10 m facets). Real Itokawa has smooth regolith "seas" (MUSES-C Regio at the
# neck, Sagamihara) and boulder-strewn highlands with a cumulative boulder
# size–frequency N(>D) ∝ D^-3.1 for D ≳ 5 m (Michikami et al. 2008, EPS 60:13).
# These ops add that relief procedurally and deterministically (seeded), as real
# geometry so it self-shadows and casts shadows through the same ray path.

def _mesh_check(V, F):
    Vv = np.asarray(V, np.float64)
    Ff = np.asarray(F, np.int64)
    if Vv.ndim != 2 or Vv.shape[1] != 3 or Vv.shape[0] == 0:
        raise ValueError("V must be a non-empty (N,3) array, got %r" % (Vv.shape,))
    if Ff.ndim != 2 or Ff.shape[1] != 3 or Ff.shape[0] == 0:
        raise ValueError("F must be a non-empty (M,3) array, got %r" % (Ff.shape,))
    if Ff.min() < 0 or Ff.max() >= Vv.shape[0]:
        raise ValueError("face index out of range")
    if not np.all(np.isfinite(Vv)):
        raise ValueError("V contains non-finite coordinates")
    return Vv, Ff


def _vertex_normals(Vv, Ff):
    """Area-weighted outward vertex normals (unit; zero-area fallback = +Z)."""
    tri = Vv[Ff]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    vn = np.zeros_like(Vv)
    for k in range(3):
        np.add.at(vn, Ff[:, k], fn)
    n = np.linalg.norm(vn, axis=1, keepdims=True)
    vn = np.where(n > 1e-15, vn / np.where(n > 1e-15, n, 1.0), np.array([0.0, 0.0, 1.0]))
    return vn


def _value_noise3(p, perm):
    """Seeded lattice value noise in [-1, 1] at points ``p`` (N,3) (C1 smoothstep)."""
    p0 = np.floor(p).astype(np.int64)
    f = p - p0
    f = f * f * (3.0 - 2.0 * f)

    def lat(ix, iy, iz):
        hsh = perm[(perm[(perm[ix & 255] + iy) & 255] + iz) & 255]
        return hsh / 255.0 * 2.0 - 1.0

    x, y, z = p0[:, 0], p0[:, 1], p0[:, 2]
    c000 = lat(x, y, z); c100 = lat(x + 1, y, z)
    c010 = lat(x, y + 1, z); c110 = lat(x + 1, y + 1, z)
    c001 = lat(x, y, z + 1); c101 = lat(x + 1, y, z + 1)
    c011 = lat(x, y + 1, z + 1); c111 = lat(x + 1, y + 1, z + 1)
    fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
    x00 = c000 + (c100 - c000) * fx
    x10 = c010 + (c110 - c010) * fx
    x01 = c001 + (c101 - c001) * fx
    x11 = c011 + (c111 - c011) * fx
    y0 = x00 + (x10 - x00) * fy
    y1 = x01 + (x11 - x01) * fy
    return y0 + (y1 - y0) * fz


def fbm_noise(points, scale: float, *, octaves: int = 4, lacunarity: float = 2.0,
              gain: float = 0.5, seed: int = 0) -> np.ndarray:
    """Seeded fractional-Brownian-motion value noise in [-1, 1] at ``points`` (N,3)."""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N,3)")
    sc = float(scale)
    if not np.isfinite(sc) or sc <= 0.0:
        raise ValueError("scale must be a positive finite length")
    oc = int(octaves)
    if oc < 1 or oc > 16:
        raise ValueError("octaves must be in [1, 16]")
    lac, gn = float(lacunarity), float(gain)
    if not (np.isfinite(lac) and lac > 0.0 and np.isfinite(gn) and 0.0 < gn <= 1.0):
        raise ValueError("lacunarity must be > 0 and gain in (0, 1]")
    rng = np.random.default_rng(int(seed))
    perm = np.tile(rng.permutation(256), 2)
    out = np.zeros(P.shape[0], np.float64)
    amp, freq, norm = 1.0, 1.0 / sc, 0.0
    offset = np.array([37.1, 17.7, 91.3])                  # keep lattice off the origin
    for o in range(oc):
        out += amp * _value_noise3(P * freq + offset * (o + 1), perm)
        norm += amp
        amp *= gn
        freq *= lac
    return out / norm


def mesh_displace_fbm(V, F, amplitude: float, *, scale=None, octaves: int = 4,
                      lacunarity: float = 2.0, gain: float = 0.5, seed: int = 0):
    """Roughen a mesh by displacing vertices along their normals with seeded fBm noise → ``(V, F)``.

    ``amplitude`` is the peak displacement **in the mesh's own units** (the Itokawa STL is in
    km, so 0.003 = 3 m); every vertex moves by at most ``amplitude`` (|fBm| ≤ 1, asserted by
    tests). ``scale`` is the base wavelength (default = bounding-box diagonal / 12);
    ``octaves``/``lacunarity``/``gain`` shape the spectrum (multifractal ridges come from the
    default 4 octaves). Deterministic for a given ``seed``; ``amplitude=0`` returns the input
    unchanged. Face normals of the displaced mesh carry the matching shading perturbation
    (no separate bump map is faked). Fail-closed on degenerate meshes / non-finite arguments."""
    Vv, Ff = _mesh_check(V, F)
    amp = float(amplitude)
    if not np.isfinite(amp) or amp < 0.0:
        raise ValueError("amplitude must be finite and >= 0")
    if amp == 0.0:
        return Vv.copy(), Ff.copy()
    diag = float(np.linalg.norm(Vv.max(axis=0) - Vv.min(axis=0)))
    sc = diag / 12.0 if scale is None else float(scale)
    noise = fbm_noise(Vv, sc, octaves=octaves, lacunarity=lacunarity, gain=gain, seed=seed)
    vn = _vertex_normals(Vv, Ff)
    return Vv + vn * (amp * noise)[:, None], Ff.copy()


def terrain_region_mask(V, F, *, smooth_fraction: float = 0.3, method: str = "neck",
                        seed: int = 0) -> np.ndarray:
    """Per-face terrain weights (M,) in [0,1]: 0 = smooth regolith "sea", 1 = rough highland.

    ``method='neck'`` (default, Itokawa-motivated): the sea is the band of faces around the
    narrowest cross-section along the principal (long) axis — MUSES-C Regio sits in the neck
    between head and body — widened until it covers ``smooth_fraction`` of the surface area.
    ``method='noise'``: low-frequency seeded fBm thresholded at the area-weighted
    ``smooth_fraction`` quantile (generic patches). ``method='slope'``: faces are ranked by
    local slope (angle between face normal and the smoothed neighbourhood normal); the
    flattest ``smooth_fraction`` of the area is sea. Deterministic; fail-closed on bad input."""
    Vv, Ff = _mesh_check(V, F)
    sf = float(smooth_fraction)
    if not np.isfinite(sf) or sf < 0.0 or sf > 1.0:
        raise ValueError("smooth_fraction must be in [0, 1]")
    if method not in ("neck", "noise", "slope"):
        raise ValueError("method must be neck|noise|slope, got %r" % (method,))
    tri = Vv[Ff]
    fc = tri.mean(axis=1)
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(fn, axis=1)
    M = Ff.shape[0]
    if sf == 0.0:
        return np.ones(M, np.float64)
    if sf == 1.0:
        return np.zeros(M, np.float64)
    if method == "neck":
        c = fc - np.average(fc, axis=0, weights=np.maximum(area, 1e-18))
        _, _, vt = np.linalg.svd(c, full_matrices=False)
        axis = vt[0]
        s = c @ axis
        perp = np.linalg.norm(c - s[:, None] * axis[None, :], axis=1)
        # narrowest cross-section: smallest 90th-percentile radius over 24 bins of the
        # central 60 % of the long axis (ends excluded — tips are trivially narrow)
        lo, hi = np.percentile(s, 20), np.percentile(s, 80)
        edges = np.linspace(lo, hi, 25)
        best, best_s = np.inf, 0.5 * (lo + hi)
        for k in range(24):
            sel = (s >= edges[k]) & (s < edges[k + 1])
            if sel.sum() < 8:
                continue
            r90 = np.percentile(perp[sel], 90)
            if r90 < best:
                best, best_s = r90, 0.5 * (edges[k] + edges[k + 1])
        score = np.abs(s - best_s)                     # distance from the neck plane
    elif method == "noise":
        diag = float(np.linalg.norm(Vv.max(axis=0) - Vv.min(axis=0)))
        score = fbm_noise(fc, diag / 3.0, octaves=2, seed=seed)
    else:
        vn = _vertex_normals(Vv, Ff)
        smooth_n = vn[Ff].mean(axis=1)
        smooth_n /= np.maximum(np.linalg.norm(smooth_n, axis=1, keepdims=True), 1e-15)
        unit_fn = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-15)
        score = np.arccos(np.clip(np.einsum("ij,ij->i", unit_fn, smooth_n), -1.0, 1.0))
    order = np.argsort(score, kind="stable")
    cum = np.cumsum(area[order])
    n_sea = int(np.searchsorted(cum, sf * cum[-1], side="right")) + 1
    weights = np.ones(M, np.float64)
    weights[order[:n_sea]] = 0.0
    return weights


def _unit_ellipsoid(subdiv: int):
    """Icosphere (unit radius) with ``subdiv`` midpoint subdivisions → (V, F)."""
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    Vs = np.array([(-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
                   (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
                   (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)], np.float64)
    Fs = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
                   [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
                   [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
                   [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]], np.int64)
    Vs /= np.linalg.norm(Vs, axis=1, keepdims=True)
    for _ in range(int(subdiv)):
        cache = {}
        vl = [tuple(v) for v in Vs]
        nf = []

        def mid(a, b):
            key = (a, b) if a < b else (b, a)
            if key in cache:
                return cache[key]
            m = (np.asarray(vl[a]) + np.asarray(vl[b])) / 2.0
            m /= np.linalg.norm(m)
            vl.append(tuple(m))
            cache[key] = len(vl) - 1
            return cache[key]

        for a, b, c in Fs:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        Vs = np.asarray(vl, np.float64)
        Fs = np.asarray(nf, np.int64)
    return Vs, Fs


def sample_boulders(V, F, *, density: float, d_min: float, d_max=None,
                    exponent: float = 3.1, seed: int = 0, region_weights=None):
    """Poisson-process boulder sample on a mesh → ``dict(centre (n,3), normal (n,3), diameter (n,), face (n,), expected)``.

    The expected count is ``density × Σ(face area × region weight)`` (``density`` = boulders
    with D ≥ ``d_min`` per unit area, mesh units²); the actual count is Poisson. Positions are
    area-weighted (times ``region_weights`` per face, e.g. :func:`terrain_region_mask`) and
    uniform inside the chosen triangle. Diameters follow the truncated power law
    N(>D) ∝ D^-exponent on [d_min, d_max] (Michikami et al. 2008: exponent 3.1 for Itokawa;
    ``d_max`` default 10·d_min). Deterministic under ``seed``. Fail-closed."""
    Vv, Ff = _mesh_check(V, F)
    dens, dmin, ex = float(density), float(d_min), float(exponent)
    dmax = 10.0 * dmin if d_max is None else float(d_max)
    if not np.isfinite(dens) or dens < 0.0:
        raise ValueError("density must be finite and >= 0")
    if not np.isfinite(dmin) or dmin <= 0.0 or not np.isfinite(dmax) or dmax <= dmin:
        raise ValueError("need 0 < d_min < d_max")
    if not np.isfinite(ex) or ex <= 0.0:
        raise ValueError("exponent must be > 0")
    tri = Vv[Ff]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(fn, axis=1)
    if region_weights is None:
        wgt = np.ones(Ff.shape[0], np.float64)
    else:
        wgt = np.asarray(region_weights, np.float64).reshape(-1)
        if wgt.shape[0] != Ff.shape[0] or not np.all(np.isfinite(wgt)) or np.any(wgt < 0.0):
            raise ValueError("region_weights must be a finite non-negative (M,) array")
    eff = area * wgt
    lam = dens * float(eff.sum())
    rng = np.random.default_rng(int(seed))
    n = int(rng.poisson(lam)) if lam > 0.0 else 0
    if n == 0 or eff.sum() <= 0.0:
        return {"centre": np.zeros((0, 3)), "normal": np.zeros((0, 3)),
                "diameter": np.zeros(0), "expected": lam, "face": np.zeros(0, np.int64)}
    faces = rng.choice(Ff.shape[0], size=n, p=eff / eff.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s1 = np.sqrt(r1)
    b = np.stack([1.0 - s1, s1 * (1.0 - r2), s1 * r2], 1)
    centre = np.einsum("ij,ijk->ik", b, tri[faces])
    nrm = fn[faces] / np.maximum(np.linalg.norm(fn[faces], axis=1, keepdims=True), 1e-15)
    u = rng.random(n)
    ratio = (dmax / dmin) ** (-ex)
    diam = dmin * np.power(1.0 - u * (1.0 - ratio), -1.0 / ex)
    return {"centre": centre, "normal": nrm, "diameter": diam, "expected": lam,
            "face": faces}


def mesh_scatter_boulders(V, F, *, density: float, d_min: float, d_max=None,
                          exponent: float = 3.1, seed: int = 0, region_weights=None,
                          aspect=(1.0, 0.7, 0.5), embed: float = 0.35, subdiv: int = 1):
    """Scatter partly-buried ellipsoidal boulders on a mesh (power-law sizes, seeded) → ``(V, F)``.

    Boulders are icosphere ellipsoids with semi-axes ``D/2 × aspect`` (default 1 : 0.7 : 0.5,
    the shortest axis along the local surface normal), randomly rotated about the normal and
    sunk by ``embed`` (0 = resting on the surface, 1 = centre on the surface). Placement and
    sizes come from :func:`sample_boulders` (Poisson process, N(>D) ∝ D^-exponent); pass
    ``region_weights`` from :func:`terrain_region_mask` to keep the seas smooth. The boulders
    are appended as real geometry, so they self-shadow, cast shadows and occlude through the
    same rasteriser / ray-cast path as the terrain. Deterministic under ``seed``. Fail-closed."""
    Vv, Ff = _mesh_check(V, F)
    asp = np.asarray(aspect, np.float64).reshape(-1)
    if asp.shape != (3,) or not np.all(np.isfinite(asp)) or np.any(asp <= 0.0):
        raise ValueError("aspect must be three positive numbers")
    em = float(embed)
    if not np.isfinite(em) or em < 0.0 or em > 1.0:
        raise ValueError("embed must be in [0, 1]")
    sd = int(subdiv)
    if sd < 0 or sd > 3:
        raise ValueError("subdiv must be in [0, 3]")
    smp = sample_boulders(Vv, Ff, density=density, d_min=d_min, d_max=d_max,
                          exponent=exponent, seed=seed, region_weights=region_weights)
    n = smp["diameter"].shape[0]
    if n == 0:
        return Vv.copy(), Ff.copy()
    rng = np.random.default_rng(int(seed) + 1)
    Vu, Fu = _unit_ellipsoid(sd)
    parts_v, parts_f = [Vv], [Ff]
    off = Vv.shape[0]
    for k in range(n):
        nrm = smp["normal"][k]
        a = np.array([1.0, 0.0, 0.0]) if abs(nrm[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        t1 = np.cross(nrm, a)
        t1 /= np.linalg.norm(t1)
        t2 = np.cross(nrm, t1)
        ang = rng.random() * 2.0 * np.pi
        ax1 = np.cos(ang) * t1 + np.sin(ang) * t2
        ax2 = np.cross(nrm, ax1)
        semi = 0.5 * smp["diameter"][k] * asp
        R = np.stack([ax1 * semi[0], ax2 * semi[1], nrm * semi[2]], axis=0)   # rows = axes
        ctr = smp["centre"][k] + nrm * semi[2] * (1.0 - em)
        parts_v.append(Vu @ R + ctr)
        parts_f.append(Fu + off)
        off += Vu.shape[0]
    return np.vstack(parts_v), np.vstack(parts_f)



# --------------------------------------------------------------------------- #
# mesh resolution: local edge length / adaptive midpoint subdivision            #
# --------------------------------------------------------------------------- #
# The Gaskell Itokawa model (itokawa_f0049152.stl) is NOT uniform: edge length
# p5 2.6 m / median 4.7 m / p95 7.2 m / max 14.1 m (measured 2026-09-03). Any
# synthetic detail added uniformly in *noise space* therefore resolves in the
# dense regions and aliases into facet noise in the coarse ones. The ops below
# make the facet size uniform in metres first (adaptive midpoint subdivision:
# geometry is unchanged, only refined — never decimated) and expose the local
# edge length so the displacement can be band-limited per vertex.

def _unique_edges(Ff):
    """Sorted unique undirected edges ``(E,2)`` and per-face edge ids ``(M,3)``
    (face edge ``j`` = ``(v_j, v_{j+1 mod 3})``)."""
    e = np.stack([Ff[:, [0, 1]], Ff[:, [1, 2]], Ff[:, [2, 0]]], axis=1)   # (M,3,2)
    e = np.sort(e, axis=2).reshape(-1, 2)
    uniq, inv = np.unique(e, axis=0, return_inverse=True)
    return uniq, np.asarray(inv).reshape(-1, 3)


def mesh_edge_lengths(V, F, *, per: str = "vertex") -> np.ndarray:
    """Local edge length of a triangle mesh → ``(N,)`` per vertex (mean of incident edges),
    ``(M,)`` per face (mean of its 3 edges) or ``(E,)`` per unique edge.

    This is the resolution map of the mesh in its own units: the shortest wavelength a
    region can carry as *geometry* is about twice the local edge (Nyquist), which is what
    :func:`mesh_subdivide` (``target_edge``) and :func:`displacement_band_weights` use.
    Deterministic; fail-closed on degenerate meshes / unknown ``per``."""
    Vv, Ff = _mesh_check(V, F)
    if per not in ("vertex", "face", "edge"):
        raise ValueError("per must be vertex|face|edge, got %r" % (per,))
    E, fe = _unique_edges(Ff)
    el = np.linalg.norm(Vv[E[:, 0]] - Vv[E[:, 1]], axis=1)
    if per == "edge":
        return el
    if per == "face":
        return el[fe].mean(axis=1)
    acc = np.zeros(Vv.shape[0], np.float64)
    cnt = np.zeros(Vv.shape[0], np.float64)
    for k in range(2):
        np.add.at(acc, E[:, k], el)
        np.add.at(cnt, E[:, k], 1.0)
    out = np.divide(acc, cnt, out=np.zeros_like(acc), where=cnt > 0)
    if np.any(cnt == 0):                                    # isolated vertices: global mean
        out[cnt == 0] = float(el.mean())
    return out


def _subdivide_once(Vv, Ff, split_edge):
    """One conforming midpoint pass: edges flagged in ``split_edge`` (E,) get a midpoint;
    faces are split by their 1 / 2 / 3-edge pattern (2 / 3 / 4 triangles, winding kept)."""
    E, fe = _unique_edges(Ff)
    if split_edge.shape[0] != E.shape[0]:
        raise ValueError("split mask does not match the edge count")
    n0 = Vv.shape[0]
    mid_id = np.full(E.shape[0], -1, np.int64)
    sel = np.nonzero(split_edge)[0]
    mid_id[sel] = n0 + np.arange(sel.size)
    Vm = 0.5 * (Vv[E[sel, 0]] + Vv[E[sel, 1]])
    Vout = np.vstack([Vv, Vm]) if sel.size else Vv.copy()
    fsplit = split_edge[fe]                                 # (M,3) bool
    s = fsplit.sum(axis=1)
    parts = [Ff[s == 0]]
    # --- 3 edges: 4 triangles ------------------------------------------------
    f3 = np.nonzero(s == 3)[0]
    if f3.size:
        a, b, c = Ff[f3, 0], Ff[f3, 1], Ff[f3, 2]
        m01, m12, m20 = mid_id[fe[f3, 0]], mid_id[fe[f3, 1]], mid_id[fe[f3, 2]]
        parts += [np.stack([a, m01, m20], 1), np.stack([b, m12, m01], 1),
                  np.stack([c, m20, m12], 1), np.stack([m01, m12, m20], 1)]
    # --- 1 edge: rotate so the split edge is edge 0 → 2 triangles --------------
    f1 = np.nonzero(s == 1)[0]
    if f1.size:
        k = np.argmax(fsplit[f1], axis=1)                   # index of the split edge
        rot = (np.arange(3)[None, :] + k[:, None]) % 3
        Fr = np.take_along_axis(Ff[f1], rot, axis=1)
        er = np.take_along_axis(fe[f1], rot, axis=1)
        a, b, c = Fr[:, 0], Fr[:, 1], Fr[:, 2]
        m = mid_id[er[:, 0]]
        parts += [np.stack([a, m, c], 1), np.stack([m, b, c], 1)]
    # --- 2 edges: rotate so the UNsplit edge is edge 2 → 3 triangles ----------
    f2 = np.nonzero(s == 2)[0]
    if f2.size:
        k = np.argmin(fsplit[f2], axis=1)                   # index of the unsplit edge
        rot = (np.arange(3)[None, :] + ((k + 1) % 3)[:, None]) % 3
        Fr = np.take_along_axis(Ff[f2], rot, axis=1)
        er = np.take_along_axis(fe[f2], rot, axis=1)
        a, b, c = Fr[:, 0], Fr[:, 1], Fr[:, 2]
        m01, m12 = mid_id[er[:, 0]], mid_id[er[:, 1]]
        parts.append(np.stack([b, m12, m01], 1))
        # quad (a, m01, m12, c): cut along the shorter diagonal (fewer slivers)
        d1 = np.linalg.norm(Vout[m01] - Vout[c], axis=1)
        d2 = np.linalg.norm(Vout[a] - Vout[m12], axis=1)
        use1 = d1 <= d2
        parts += [np.where(use1[:, None], np.stack([a, m01, c], 1), np.stack([a, m01, m12], 1)),
                  np.where(use1[:, None], np.stack([m01, m12, c], 1), np.stack([a, m12, c], 1))]
    Fout = np.vstack([p_ for p_ in parts if p_.size]).astype(np.int64)
    return Vout, Fout


#: Hard cap on the number of faces a subdivision may produce (memory guard).
MAX_SUBDIVIDE_FACES = 4_000_000
#: Adaptive tessellation: an edge is cut into at most this many segments per call.
_MAX_SEGMENTS = 64


def _zipper(a: int, b: int):
    """Triangle strip between two parallel point sequences of ``a`` (outer) and ``b`` (inner)
    points, as (i, j, advance_outer) steps — purely parametric (geometry-independent)."""
    steps = []
    i = j = 0
    while i < a - 1 or j < b - 1:
        if j == b - 1:
            adv = True
        elif i == a - 1:
            adv = False
        else:
            ui1 = (i + 1) / (a - 1)
            vj = j / (b - 1)
            ui = i / (a - 1)
            vj1 = (j + 1) / (b - 1)
            adv = abs(ui1 - vj) <= abs(ui - vj1)
        steps.append((i, j, adv))
        if adv:
            i += 1
        else:
            j += 1
    return steps


def _tess_pattern(n0: int, n1: int, n2: int):
    """Conforming tessellation of one triangle whose edges carry ``n0, n1, n2`` segments
    (edge ``i`` = corner ``i`` → corner ``i+1``): returns ``(bary (P,3), tris (T,3),
    n_boundary)`` in a local numbering — corners 0..2, then the interior points of edge 0,
    1, 2 in traversal order, then interior points. Rings are homothetic insets (OpenGL
    tessellation-style): inner level ``m = round(mean n)``, ring ``r`` at barycentric inset
    ``2r/(3m)`` with ``m − 2r`` segments per side, neighbouring rings joined by :func:`_zipper`.
    All points lie inside the triangle (positions are barycentric combinations of its
    corners), so the refined surface is *identical* to the original facet."""
    corners = np.eye(3)
    pts = [corners[0], corners[1], corners[2]]
    edge_ids = []
    for i, n in enumerate((n0, n1, n2)):
        c0, c1 = corners[i], corners[(i + 1) % 3]
        ids = []
        for k in range(1, n):
            pts.append(c0 + (c1 - c0) * (k / n))
            ids.append(len(pts) - 1)
        edge_ids.append(ids)
    n_boundary = len(pts)
    ring = [[i] + edge_ids[i] + [(i + 1) % 3] for i in range(3)]   # 3 sides, each a point list
    tris = []
    m = max(1, int(round((n0 + n1 + n2) / 3.0)))
    if m == 1 and n0 == 1 and n1 == 1 and n2 == 1:
        return np.asarray(pts), np.array([[0, 1, 2]], np.int64), n_boundary
    r = 1
    while True:
        mr = m - 2 * r
        if mr <= 0:
            pts.append(np.full(3, 1.0 / 3.0))
            c = len(pts) - 1
            for i in range(3):
                A = ring[i]
                for k in range(len(A) - 1):
                    tris.append([A[k], A[k + 1], c])
            break
        d = 2.0 * r / (3.0 * m)
        cc = [np.array([1 - 2 * d, d, d]), np.array([d, 1 - 2 * d, d]), np.array([d, d, 1 - 2 * d])]
        cid = []
        for i in range(3):
            pts.append(cc[i])
            cid.append(len(pts) - 1)
        new_ring = []
        for i in range(3):
            c0, c1 = cc[i], cc[(i + 1) % 3]
            side = [cid[i]]
            for k in range(1, mr):
                pts.append(c0 + (c1 - c0) * (k / mr))
                side.append(len(pts) - 1)
            side.append(cid[(i + 1) % 3])
            new_ring.append(side)
        for i in range(3):
            A, B = ring[i], new_ring[i]
            for (ii, jj, adv) in _zipper(len(A), len(B)):
                if adv:
                    tris.append([A[ii], A[ii + 1], B[jj]])
                else:
                    tris.append([A[ii], B[jj + 1], B[jj]])
        ring = new_ring
        if mr == 1:
            tris.append([cid[0], cid[1], cid[2]])
            break
        r += 1
    return np.asarray(pts), np.asarray(tris, np.int64), n_boundary


_TESS_CACHE: dict = {}


def _tessellate(Vv, Ff, n_seg):
    """Apply per-edge segment counts ``n_seg`` (E,) with conforming per-face patterns."""
    E, fe = _unique_edges(Ff)
    n0 = Vv.shape[0]
    # shared edge points: edge e gets n_e - 1 points from E[e,0] → E[e,1]
    n_in = n_seg - 1
    off = np.cumsum(n_in) - n_in + n0
    tot = int(n_in.sum())
    ke = np.repeat(np.arange(E.shape[0]), n_in)
    kk = np.arange(tot) - np.repeat(off - n0, n_in) + 1
    t = kk / n_seg[ke]
    Vedge = Vv[E[ke, 0]] + (Vv[E[ke, 1]] - Vv[E[ke, 0]]) * t[:, None]
    parts_v = [Vv, Vedge]
    parts_f = []
    n_cur = n0 + tot
    # traversal direction of each face edge relative to the sorted edge
    fwd = Ff == E[fe][:, :, 0]                              # (M,3) face edge j starts at E[e,0]
    fn = n_seg[fe]                                          # (M,3)
    sig = fn[:, 0] * (_MAX_SEGMENTS + 1) ** 2 + fn[:, 1] * (_MAX_SEGMENTS + 1) + fn[:, 2]
    order = np.argsort(sig, kind="stable")
    sig_s = sig[order]
    bounds = np.flatnonzero(np.r_[True, sig_s[1:] != sig_s[:-1], True])
    for gi in range(bounds.size - 1):
        faces = order[bounds[gi]:bounds[gi + 1]]
        a, b, c = (int(x) for x in fn[faces[0]])
        key = (a, b, c)
        if key not in _TESS_CACHE:
            _TESS_CACHE[key] = _tess_pattern(a, b, c)
        bary, ltris, nb = _TESS_CACHE[key]
        nf = faces.size
        P = bary.shape[0]
        n_int = P - nb
        # local → global id table (nf, P)
        gid = np.empty((nf, P), np.int64)
        gid[:, 0:3] = Ff[faces]
        col = 3
        for j, n in enumerate((a, b, c)):
            if n > 1:
                e = fe[faces, j]
                base = off[e]                                # first point of that edge
                k = np.arange(1, n)
                ids_f = base[:, None] + (k - 1)[None, :]     # forward order
                ids_b = base[:, None] + (n - 1 - k)[None, :] # reversed traversal
                gid[:, col:col + n - 1] = np.where(fwd[faces, j][:, None], ids_f, ids_b)
                col += n - 1
        if n_int:
            gid[:, nb:] = n_cur + np.arange(nf * n_int).reshape(nf, n_int)
            tri = Vv[Ff[faces]]                              # (nf,3,3)
            Vint = np.einsum("pk,fkd->fpd", bary[nb:], tri).reshape(-1, 3)
            parts_v.append(Vint)
            n_cur += nf * n_int
        parts_f.append(np.take_along_axis(
            gid[:, None, :].repeat(ltris.shape[0], axis=1),
            np.broadcast_to(ltris[None, :, :], (nf,) + ltris.shape), axis=2).reshape(-1, 3))
    return np.vstack(parts_v), np.vstack(parts_f).astype(np.int64)


def mesh_subdivide(V, F, *, levels: int = 1, target_edge=None,
                   max_faces: int = MAX_SUBDIVIDE_FACES):
    """Refine a triangle mesh → ``(V, F)``: uniform midpoint subdivision (``levels`` passes,
    ×4 faces each) or **adaptive tessellation to a target edge length** (``target_edge``).

    The geometry is *unchanged* — every new vertex lies on an old facet, so surface area
    and enclosed volume are preserved exactly (tests pin this) and nothing is ever
    decimated; only the facet size changes, so a later :func:`mesh_displace_spectrum` can
    carry short wavelengths without aliasing.

    Adaptive mode cuts each edge into ``n = round(length / target_edge)`` (≥ 1) segments
    — a per-*edge* count, hence conforming across neighbours (no T-junctions) — and fills
    each face with an OpenGL-tessellation-style pattern (homothetic inner rings zipped to
    the outer ring). Unlike repeated midpoint bisection (which leaves a factor-2 spread
    ``(target/2, target]``) the result is uniform in metres: on the Gaskell Itokawa model
    (edge p5/median/p95 = 2.6/4.7/7.2 m) a 1.5 m target gives p95/p5 ≈ 1.4 (measured;
    the test pins ≤ 1.5 on a graded plane). ``max_faces`` (default
    ``MAX_SUBDIVIDE_FACES``) is a memory guard: if the plan would exceed it the call
    raises ``ValueError`` (fail-closed) rather than silently under-refining.
    Deterministic. Fail-closed: degenerate mesh, ``levels < 0``, non-positive
    ``target_edge`` / caps → ``ValueError``."""
    Vv, Ff = _mesh_check(V, F)
    lv = int(levels)
    if lv < 0:
        raise ValueError("levels must be >= 0")
    mf = int(max_faces)
    if mf < 1:
        raise ValueError("max_faces must be >= 1")
    if target_edge is None:
        for _ in range(lv):
            if Ff.shape[0] * 4 > mf:
                raise ValueError("uniform subdivision would exceed max_faces=%d" % mf)
            E, _fe = _unique_edges(Ff)
            Vv, Ff = _subdivide_once(Vv, Ff, np.ones(E.shape[0], bool))
        return Vv, Ff
    te = float(target_edge)
    if not np.isfinite(te) or te <= 0.0:
        raise ValueError("target_edge must be a positive finite length")
    E, fe = _unique_edges(Ff)
    el = np.linalg.norm(Vv[E[:, 0]] - Vv[E[:, 1]], axis=1)
    n_seg = np.clip(np.rint(el / te).astype(np.int64), 1, _MAX_SEGMENTS)
    if not np.any(n_seg > 1):
        return Vv.copy(), Ff.copy()
    fn = n_seg[fe]
    m = np.maximum(1, np.rint(fn.mean(axis=1)).astype(np.int64))
    est = int((fn.sum(axis=1) + 3 * m * np.maximum(m - 1, 0)).sum())   # upper-ish bound
    if est > mf:
        raise ValueError("adaptive tessellation would produce ~%d faces > max_faces=%d "
                         "(raise max_faces or target_edge)" % (est, mf))
    return _tessellate(Vv, Ff, n_seg)


# --------------------------------------------------------------------------- #
# band-limited multi-octave displacement + sub-facet bump normals               #
# --------------------------------------------------------------------------- #
def _octave_noise(P, wavelength: float, perm, k: int) -> np.ndarray:
    """One value-noise octave in [-1, 1] at wavelength ``wavelength`` (lattice offset per octave)."""
    offset = np.array([37.1, 17.7, 91.3]) * (k + 1)
    return _value_noise3(P / float(wavelength) + offset, perm)


def _check_spectrum(wavelengths, amplitudes):
    lam = np.asarray(wavelengths, np.float64).reshape(-1)
    if lam.size == 0 or lam.size > 32:
        raise ValueError("wavelengths must hold 1..32 values")
    if not np.all(np.isfinite(lam)) or np.any(lam <= 0.0):
        raise ValueError("wavelengths must be positive finite lengths")
    if amplitudes is None:
        raise ValueError("amplitudes are required (one per wavelength, mesh units)")
    amp = np.asarray(amplitudes, np.float64).reshape(-1)
    if amp.shape != lam.shape:
        raise ValueError("amplitudes must have one entry per wavelength")
    if not np.all(np.isfinite(amp)) or np.any(amp < 0.0):
        raise ValueError("amplitudes must be finite and >= 0")
    return lam, amp


def displacement_band_weights(V, F, wavelengths=(0.06, 0.03, 0.015, 0.0075, 0.00375), *,
                              nyquist: float = 2.0, fade: float = 1.0,
                              local_edge=None) -> np.ndarray:
    """Per-octave, per-vertex band gate ``(K, N)`` in [0,1]: 1 where the mesh can carry the
    wavelength as geometry, 0 where it would alias.

    A vertex with local edge length ``e`` (mean incident edge, :func:`mesh_edge_lengths`,
    or ``local_edge`` (N,) if given) carries wavelength ``λ`` only when ``λ ≥ nyquist·e``;
    the gate rises linearly from 0 at ``λ = nyquist·e`` to 1 at ``λ = (nyquist+fade)·e``
    (``fade=0`` → hard cut). Used two ways by the Itokawa pipeline: (i) on the *rendered*
    mesh to decide which octaves may be displaced (the rest go to bump normals); (ii) on
    the *source* model to measure which wavelengths the real data already carries — the
    complement ``1 − gate`` is the synthetic-relief weight (0 where the data are fine,
    1 where they are coarse), so dense regions are not double-textured. Deterministic."""
    Vv, Ff = _mesh_check(V, F)
    lam = np.asarray(wavelengths, np.float64).reshape(-1)
    if lam.size == 0 or not np.all(np.isfinite(lam)) or np.any(lam <= 0.0):
        raise ValueError("wavelengths must be positive finite lengths")
    ny, fd = float(nyquist), float(fade)
    if not np.isfinite(ny) or ny <= 0.0 or not np.isfinite(fd) or fd < 0.0:
        raise ValueError("nyquist must be > 0 and fade >= 0")
    if local_edge is None:
        e = mesh_edge_lengths(Vv, Ff, per="vertex")
    else:
        e = np.asarray(local_edge, np.float64).reshape(-1)
        if e.shape[0] != Vv.shape[0] or not np.all(np.isfinite(e)) or np.any(e <= 0.0):
            raise ValueError("local_edge must be a positive finite (N,) array")
    ratio = lam[:, None] / e[None, :]                       # (K,N)
    if fd == 0.0:
        return (ratio >= ny).astype(np.float64)
    return np.clip((ratio - ny) / fd, 0.0, 1.0)


def mesh_displace_spectrum(V, F, wavelengths=(0.06, 0.03, 0.015, 0.0075, 0.00375),
                           amplitudes=(0.003, 0.00176, 0.00103, 0.0006, 0.00035), *,
                           seed: int = 0, nyquist: float = 2.0, fade: float = 1.0,
                           weights=None, local_edge=None):
    """Displace vertices along their normals with a **stated amplitude spectrum**, band-limited
    per vertex → ``(V, F)``.

    ``displacement_i = Σ_k A_k · n_k(x_i) · gate_k(i) · w_k(i)`` with one seeded value-noise
    octave ``n_k ∈ [−1, 1]`` per ``(wavelength_k, amplitude_k)`` pair (mesh units — the
    Itokawa STL is in km, so the default is 3 m at 60 m falling as ``A ∝ λ^0.77`` to
    0.35 m at 3.75 m), ``gate`` = :func:`displacement_band_weights` on *this* mesh
    (an octave shorter than ``nyquist × local edge`` is not applied — it would alias into
    facet noise; route it to :func:`bump_normals_fbm` instead) and ``weights`` = optional
    ``(N,)`` per-vertex or ``(K, N)`` per-octave-per-vertex factor in [0,1] (e.g. the
    synthetic-relief weight ``1 − gate`` of the source model). The peak displacement at a
    vertex is at most ``Σ_k A_k`` (tests pin it). Unlike :func:`mesh_displace_fbm` (one
    amplitude, octave ratio 2, no band limit) every octave's amplitude is explicit.
    Deterministic under ``seed``. Fail-closed on shapes / non-finite / negative values."""
    Vv, Ff = _mesh_check(V, F)
    lam, amp = _check_spectrum(wavelengths, amplitudes)
    gate = displacement_band_weights(Vv, Ff, lam, nyquist=nyquist, fade=fade,
                                     local_edge=local_edge)          # (K,N)
    if weights is not None:
        w = np.asarray(weights, np.float64)
        if w.ndim == 1:
            w = np.broadcast_to(w[None, :], gate.shape)
        if w.shape != gate.shape or not np.all(np.isfinite(w)) or np.any(w < 0.0) or np.any(w > 1.0):
            raise ValueError("weights must be (N,) or (K,N) in [0,1], got %r" % (w.shape,))
        gate = gate * w
    rng = np.random.default_rng(int(seed))
    perm = np.tile(rng.permutation(256), 2)
    disp = np.zeros(Vv.shape[0], np.float64)
    for k in range(lam.size):
        if amp[k] == 0.0:
            continue
        disp += amp[k] * gate[k] * _octave_noise(Vv, lam[k], perm, k)
    vn = _vertex_normals(Vv, Ff)
    return Vv + vn * disp[:, None], Ff.copy()


def bump_normals_fbm(normals, positions, wavelengths=(0.002, 0.001),
                     amplitudes=(0.0002, 0.00012), *, seed: int = 0,
                     rotation=None, step=None) -> np.ndarray:
    """Perturb a normal map with the *gradient* of a seeded multi-octave height field
    (sub-facet relief the geometry cannot afford to displace) → unit normals ``(H, W, 3)``.

    ``h(x) = Σ_k A_k n_k(x)`` is the same value-noise field :func:`mesh_displace_spectrum`
    would displace with (same ``seed`` ⇒ same lattice), so passing the octaves that the
    displacement's band gate rejected makes the shading continue the *same* amplitude
    spectrum below the facet size (no fake sandpaper: an octave of amplitude ``A`` at
    wavelength ``λ`` tilts the normal by about ``2πA/λ`` at most). The bumped normal is
    ``normalize(n − ∇_t h)`` (first-order shading normal of a height field over the
    surface; ``∇_t`` = tangential gradient by central differences with ``step`` =
    ``min(λ)/64``). ``positions`` are world coordinates ``(H, W, 3)`` (NaN = background,
    left untouched); if ``rotation`` (3×3, world → normal frame, e.g. ``pose[:3,:3]``)
    is given the normals are taken in that frame. Deterministic; fail-closed."""
    N = np.asarray(normals, np.float64)
    P = np.asarray(positions, np.float64)
    if N.ndim != 3 or N.shape[2] != 3 or P.shape != N.shape:
        raise ValueError("normals and positions must both be (H, W, 3)")
    lam, amp = _check_spectrum(wavelengths, amplitudes)
    if rotation is None:
        R = np.eye(3)
    else:
        R = np.asarray(rotation, np.float64)
        if R.shape != (3, 3) or not np.all(np.isfinite(R)):
            raise ValueError("rotation must be a finite 3x3 matrix")
    hstep = float(lam.min()) / 64.0 if step is None else float(step)
    if not np.isfinite(hstep) or hstep <= 0.0:
        raise ValueError("step must be a positive finite length")
    mask = np.all(np.isfinite(P), axis=-1) & (np.linalg.norm(N, axis=-1) > 1e-12)
    out = N.copy()
    if not mask.any():
        return out
    pts = P[mask]
    n_w = N[mask] @ R                                       # frame → world (R^T applied)
    rng = np.random.default_rng(int(seed))
    perm = np.tile(rng.permutation(256), 2)

    def height(q):
        h = np.zeros(q.shape[0], np.float64)
        for k in range(lam.size):
            if amp[k] > 0.0:
                h += amp[k] * _octave_noise(q, lam[k], perm, k)
        return h

    grad = np.zeros_like(pts)
    for ax in range(3):
        dv = np.zeros(3)
        dv[ax] = hstep
        grad[:, ax] = (height(pts + dv) - height(pts - dv)) / (2.0 * hstep)
    gt = grad - np.einsum("ij,ij->i", grad, n_w)[:, None] * n_w   # tangential part
    nb = n_w - gt
    nb /= np.maximum(np.linalg.norm(nb, axis=1, keepdims=True), 1e-15)
    out[mask] = nb @ R.T                                    # back to the normals' frame
    return out


__all__ += ["fbm_noise", "mesh_displace_fbm", "terrain_region_mask", "sample_boulders",
            "mesh_scatter_boulders", "mesh_edge_lengths", "mesh_subdivide",
            "displacement_band_weights", "mesh_displace_spectrum", "bump_normals_fbm",
            "MAX_SUBDIVIDE_FACES"]
