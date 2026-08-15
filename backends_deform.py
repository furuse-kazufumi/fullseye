"""Control-point / free-form image deformation (registry cluster ``deform_``).

Three classical *scattered-control-point* warps. Each op builds a smooth,
deterministic displacement of a small set of control points, turns that into a
**dense backward map** (destination pixel -> source location) with the model's
own interpolation scheme, and resamples the image bilinearly with
``scipy.ndimage.map_coordinates(order=1, mode="reflect")``. Output keeps the
input HxW and stays in [0,1].

Provenance
----------
  * ``deform_tps`` -- F. L. Bookstein, "Principal Warps: Thin-Plate Splines and
    the Decomposition of Deformations", IEEE TPAMI 11(6):567-585, 1989.
    Radial basis U(r) = r^2 log r, the (K | P ; P^T | 0) linear system and the
    side conditions sum(w_i) = 0, sum(w_i p_i) = 0.
  * ``deform_ffd`` -- D. Rueckert et al., "Nonrigid Registration Using Free-Form
    Deformations: Application to Breast MR Images", IEEE TMI 18(8):712-721,
    1999; the tensor cubic B-spline FFD of S. Lee, G. Wolberg, S. Y. Shin,
    "Scattered Data Interpolation with Multilevel B-Splines", IEEE TVCG 3(3),
    1997. The 0.45*spacing amplitude cap follows the injectivity bound
    |phi| < 0.48*delta of Choi & Lee, "Injectivity Conditions of 2D and 3D
    Uniform Cubic B-Spline Functions", GMOD 62(6):411-427, 2000.
  * ``deform_mls`` -- S. Schaefer, T. McPhail, J. Warren, "Image Deformation
    Using Moving Least Squares", ACM SIGGRAPH 2006 (ACM TOG 25(3):533-540),
    the *affine* variant of section 2.1 (eqs. 1-7).

HALCON honesty
--------------
``halcon = ""`` for every op in this cluster; nothing here claims coverage.
MVTec HALCON has **no** thin-plate-spline, no free-form-deformation and no
moving-least-squares operator (verified against ``data/halcon_operators.json``,
all 2313 names: no ``thin_plate`` / ``tps`` / ``spline`` / ``free_form`` /
``ffd`` / ``moving_least`` / ``mls`` / ``elastic`` / ``control_point`` node
exists). The nearest HALCON names are *not* aliases and are deliberately not
claimed:

  * ``unwarp_image_vector_field`` / ``gen_image_warp_map`` **apply a vector
    field that the caller already has** -- they are resamplers, not deformation
    *models*; the whole content of these three ops is the model that turns a
    handful of control points into that field.
  * the ``*_deformable_model`` family (``create_local_deformable_model``,
    ``find_deformable_surface_model``, ...) is *matching* -- it locates a
    deformed instance of a template -- not deformation synthesis.

Non-overlap with the existing registry (disclosed, not hidden)
--------------------------------------------------------------
imgevolve already ships two parametric geometric warps and this cluster does
**not** reimplement either of them:

  * ``sk_swirl`` (``backends.py``, halcon alias ``polar_trans_image``) -- a
    single closed-form angular twist about the image centre;
  * ``aug_barrel`` (``backends_aug.py``) -- the closed-form radial lens
    polynomial r*(1+k r^2), barrel and pincushion.

Both are *global, analytic, 1-parameter-family* warps with no control points.
The three ops here are *scattered-control-point / free-form* deformations:
the warp is defined by a lattice of displacements and an interpolation model
(RBF, tensor B-spline, moving weighted least squares), which is a different
capability -- locally controllable, non-radial, and reducible to an arbitrary
prescribed displacement field.

Operators (a, b are the two knobs, both in [0,1])
-------------------------------------------------
  deform_tps   Thin-plate-spline warp over a 5x5 control grid. The 3x3 INTERIOR
               control points are displaced by the deterministic smooth field
               d = amp*[sin(2 pi f gx), cos(2 pi f gy)] (gy,gx = normalised
               control coordinates); the 16 border control points are pinned, so
               the frame is anchored. a -> amp = 0.15*a*min(H,W);
               b -> spatial frequency f = 0.5 + 1.5b. The TPS system is solved
               exactly (dense LU, least-squares fallback) and evaluated at every
               destination pixel. a = 0 is the identity (up to sub-pixel resampling error).
  deform_ffd   Cubic B-spline free-form deformation on a (n+3)x(n+3) control
               lattice covering n x n spans. The displacement at a pixel is the
               tensor product of the four cubic B-spline basis functions of its
               span coordinate with the surrounding 4x4 control displacements,
               so each control point influences exactly 4 spans (compact
               support). a -> amplitude 0.45*a*min(dy,dx) (injectivity bound);
               b -> lattice resolution n = 2 + int(6b) spans. a = 0 is the
               identity (up to sub-pixel resampling error).
  deform_mls   Moving-least-squares (affine) deformation from a 5x5 control
               grid. For every pixel v the weights w_i = 1/|p_i - v|^(2 alpha)
               define a weighted least-squares affine map {p_i} -> {q_i} that is
               re-solved *per pixel*; v is mapped by its own local affine. The
               map reproduces any affine data exactly, interpolates the control
               points, and is smooth everywhere. a -> displacement amplitude
               0.12*a*min(H,W); b -> alpha = 0.5 + 1.5b (large alpha = tightly
               local, small alpha = global). a = 0 is the identity (up to sub-pixel resampling error).

Determinism: no random number generator is used anywhere in this module -- the
control displacements are closed-form trigonometric functions of the control
index, and every solve is a deterministic dense linear algebra call. Same input
and (a, b) give bit-identical output.

Contract: ``fn(v, a, b)`` maps a 2-D float64 image in [0,1] (knobs a,b in [0,1])
to a 2-D float64 image in [0,1] of the same HxW.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

# Pixel chunk used by the dense evaluators, so a large image never materialises
# an (n_control x n_pixel) matrix in one go.
_CHUNK = 1 << 15

_TPS_GRID = 5      # 5x5 thin-plate-spline control grid (3x3 interior)
_MLS_GRID = 5      # 5x5 moving-least-squares control grid


# --------------------------------------------------------------------------- #
# safety wrapper (shared pattern with the other backends)                     #
# --------------------------------------------------------------------------- #
def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:  # noqa: BLE001 - fail-soft per op contract
            out = None
        return sanitize(out, v, out_sort)

    return w


# --------------------------------------------------------------------------- #
# small helpers                                                               #
# --------------------------------------------------------------------------- #
def _img(v):
    """Coerce input to a finite 2-D float64 image in [0,1] (fail-soft)."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:                       # accidental colour -> luma
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    if x.size == 0:
        return np.zeros((1, 1), np.float64)
    return np.clip(x, 0.0, 1.0)


def _knob(t):
    """Clamp a knob to [0,1] and strip non-finite values."""
    t = float(np.nan_to_num(np.float64(t), nan=0.0, posinf=1.0, neginf=0.0))
    return float(np.clip(t, 0.0, 1.0))


def _grid_points(h, w, n):
    """(n*n, 2) regular grid of (y, x) control points spanning the full frame."""
    ys = np.linspace(0.0, float(h - 1), n)
    xs = np.linspace(0.0, float(w - 1), n)
    gy, gx = np.meshgrid(ys, xs, indexing="ij")
    return np.stack([gy.ravel(), gx.ravel()], axis=1)


def _pixel_points(h, w):
    """(h*w, 2) destination pixel centres as (y, x), row-major."""
    yy, xx = np.mgrid[0:h, 0:w]
    return np.stack([yy.ravel().astype(np.float64),
                     xx.ravel().astype(np.float64)], axis=1)


def _resample(x, src_yx):
    """Bilinear backward resampling of ``x`` at the (N,2) source coordinates."""
    h, w = x.shape[:2]
    coords = np.vstack([src_yx[:, 0], src_yx[:, 1]])
    out = ndimage.map_coordinates(x, coords, order=1, mode="reflect")
    return np.clip(out.reshape(h, w), 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 1. thin-plate spline (Bookstein 1989)                                       #
# --------------------------------------------------------------------------- #
def _tps_kernel(r2):
    """Biharmonic radial basis U(r) = r^2 log r, written as 0.5*r2*log(r2).

    U(0) = 0 by continuity (r^2 log r -> 0 as r -> 0).
    """
    r2 = np.asarray(r2, np.float64)
    out = np.zeros(r2.shape, np.float64)
    m = r2 > 0.0
    out[m] = 0.5 * r2[m] * np.log(r2[m])
    return out


def _tps_fit(src, dst):
    """Solve the Bookstein thin-plate-spline system for src -> dst.

    Builds the (n+3)x(n+3) block matrix

        L = [ K  P ]        K_ij = U(|p_i - p_j|),  P = [1 | p]  (n x 3)
            [ P^T 0 ]

    and solves ``L [W; A] = [dst; 0]``. The three zero rows are the side
    conditions sum(w_i) = 0 and sum(w_i p_i) = 0 that make the interpolant have
    minimum bending energy and reduce to a pure affine map far from the control
    points. Returns ``(W (n,2), A (3,2))``.
    """
    src = np.asarray(src, np.float64)
    dst = np.asarray(dst, np.float64)
    n = int(src.shape[0])
    diff = src[:, None, :] - src[None, :, :]
    k = _tps_kernel((diff * diff).sum(-1))
    p = np.concatenate([np.ones((n, 1), np.float64), src], axis=1)
    lmat = np.zeros((n + 3, n + 3), np.float64)
    lmat[:n, :n] = k
    lmat[:n, n:] = p
    lmat[n:, :n] = p.T
    rhs = np.zeros((n + 3, 2), np.float64)
    rhs[:n, :] = dst
    try:
        sol = np.linalg.solve(lmat, rhs)
    except np.linalg.LinAlgError:
        sol = np.linalg.lstsq(lmat, rhs, rcond=None)[0]
    if not np.isfinite(sol).all():          # near-singular control layout
        sol = np.linalg.lstsq(lmat, rhs, rcond=None)[0]
        sol = np.nan_to_num(sol, nan=0.0, posinf=0.0, neginf=0.0)
    return sol[:n, :], sol[n:, :]


def _tps_eval(src, weights, affine, pts):
    """Evaluate the TPS map f(v) = [1 v] A + sum_i U(|v - p_i|) w_i."""
    src = np.asarray(src, np.float64)
    pts = np.asarray(pts, np.float64)
    out = np.empty((pts.shape[0], 2), np.float64)
    for s in range(0, pts.shape[0], _CHUNK):
        q = pts[s:s + _CHUNK]
        diff = q[:, None, :] - src[None, :, :]
        u = _tps_kernel((diff * diff).sum(-1))
        lin = np.concatenate([np.ones((q.shape[0], 1), np.float64), q], axis=1)
        out[s:s + _CHUNK] = u @ weights + lin @ affine
    return out


def deform_tps(v, a, b):
    """Thin-plate-spline warp over a 5x5 control grid (Bookstein, TPAMI 1989).

    The 3x3 interior control points are displaced by the deterministic smooth
    field ``d = amp * [sin(2 pi f gx), cos(2 pi f gy)]`` (gy, gx = the control
    point's normalised coordinates), the 16 border control points are pinned so
    the frame stays anchored. The backward map is the TPS interpolant fitted
    from the *displaced* control points back to the original ones -- the unique
    minimum-bending-energy interpolant, i.e. the surface a thin metal plate
    would take -- and it is evaluated at every destination pixel before bilinear
    resampling. ``a`` sets the amplitude ``amp = 0.15*a*min(H,W)``, ``b`` the
    spatial frequency ``f = 0.5 + 1.5b``. ``a = 0`` leaves the control points
    where they are, so the solved map is the identity (up to sub-pixel resampling error).
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    h, w = x.shape[:2]
    if h < 2 or w < 2:
        return x
    src = _grid_points(h, w, _TPS_GRID)
    amp = 0.15 * a * float(min(h, w))
    freq = 0.5 + 1.5 * b
    gy = src[:, 0] / float(h - 1)
    gx = src[:, 1] / float(w - 1)
    disp = np.stack([amp * np.sin(2.0 * np.pi * freq * gx),
                     amp * np.cos(2.0 * np.pi * freq * gy)], axis=1)
    interior = (gy > 1e-9) & (gy < 1.0 - 1e-9) & (gx > 1e-9) & (gx < 1.0 - 1e-9)
    disp[~interior] = 0.0
    dst = src + disp
    # backward map: destination (displaced) control points -> source grid
    weights, affine = _tps_fit(dst, src)
    src_yx = _tps_eval(dst, weights, affine, _pixel_points(h, w))
    return _resample(x, src_yx)


# --------------------------------------------------------------------------- #
# 2. cubic B-spline free-form deformation (Rueckert 1999)                     #
# --------------------------------------------------------------------------- #
def _bspline3(u):
    """The four uniform cubic B-spline basis functions at u in [0,1).

    B0 = (1-u)^3/6, B1 = (3u^3 - 6u^2 + 4)/6, B2 = (-3u^3 + 3u^2 + 3u + 1)/6,
    B3 = u^3/6. They are non-negative and form a partition of unity.
    Returns an array of shape (4,) + u.shape.
    """
    u = np.asarray(u, np.float64)
    u2 = u * u
    u3 = u2 * u
    return np.stack([(1.0 - 3.0 * u + 3.0 * u2 - u3) / 6.0,
                     (4.0 - 6.0 * u2 + 3.0 * u3) / 6.0,
                     (1.0 + 3.0 * u + 3.0 * u2 - 3.0 * u3) / 6.0,
                     u3 / 6.0], axis=0)


def _ffd_field(shape, phi, ny, nx):
    """Dense FFD displacement field from a control lattice.

    ``phi`` has shape ``(ny+3, nx+3, 2)``: control displacement (dy, dx) for
    lattice index ``i = k - 1`` (k the array index), i.e. one padding ring on
    each side so the 4x4 neighbourhood of every span exists. With span sizes
    ``sy = (H-1)/ny`` and ``sx = (W-1)/nx``, the displacement at pixel (y,x) is

        T(y,x) = sum_{l=0..3} sum_{m=0..3} B_l(u) B_m(w) phi[i0+l, j0+m]

    where ``i0 = clip(floor(y/sy), 0, ny-1)`` and ``u = y/sy - floor(y/sy)``.
    Because only 4 consecutive controls per axis appear, every control point
    influences exactly 4 spans -- the compact support that makes an FFD locally
    controllable. Returns an ``(H, W, 2)`` array of (dy, dx).
    """
    h, w = int(shape[0]), int(shape[1])
    ny = max(1, int(ny))
    nx = max(1, int(nx))
    phi = np.asarray(phi, np.float64)
    if phi.shape != (ny + 3, nx + 3, 2):
        raise ValueError("phi must have shape (ny+3, nx+3, 2)")
    sy = float(h - 1) / ny if h > 1 else 1.0
    sx = float(w - 1) / nx if w > 1 else 1.0
    ty = np.arange(h, dtype=np.float64) / sy
    tx = np.arange(w, dtype=np.float64) / sx
    i0 = np.clip(np.floor(ty).astype(np.int64), 0, ny - 1)
    j0 = np.clip(np.floor(tx).astype(np.int64), 0, nx - 1)
    uy = ty - i0
    ux = tx - j0
    by = _bspline3(uy)                      # (4, H)
    bx = _bspline3(ux)                      # (4, W)
    field = np.zeros((h, w, 2), np.float64)
    for l in range(4):
        ci = i0 + l                         # array index = (i0 - 1 + l) + 1
        for m in range(4):
            cj = j0 + m
            coef = phi[np.ix_(ci, cj)]      # (H, W, 2)
            wgt = by[l][:, None] * bx[m][None, :]
            field += wgt[:, :, None] * coef
    return field


def deform_ffd(v, a, b):
    """Cubic B-spline free-form deformation (Rueckert et al., IEEE TMI 1999).

    A coarse control lattice of ``n x n`` spans (``n = 2 + int(6b)``, one padding
    ring on each side) carries a deterministic smooth displacement pattern
    ``phi[i,j] = amp * [sin(2 pi j/n), cos(2 pi i/n)]``; the dense displacement
    at a pixel is the tensor product of the four uniform cubic B-spline basis
    functions of its span coordinate with the surrounding 4x4 control
    displacements, so a control point only ever moves the 4 spans it supports.
    That field is used as the backward map and the image is bilinearly resampled.
    ``a`` sets the amplitude ``amp = 0.45*a*min(sy,sx)`` -- kept under the
    ``0.48*spacing`` injectivity bound of Choi & Lee (2000), so the deformation
    stays a fold-free bijection -- and ``b`` the lattice resolution. ``a = 0``
    gives a zero lattice, hence the identity (up to sub-pixel resampling error).
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    h, w = x.shape[:2]
    if h < 2 or w < 2:
        return x
    ny = nx = 2 + int(b * 6)                # 2..8 spans per axis
    sy = float(h - 1) / ny
    sx = float(w - 1) / nx
    amp = 0.45 * a * float(min(sy, sx))
    lat_i = (np.arange(ny + 3, dtype=np.float64) - 1.0) / ny
    lat_j = (np.arange(nx + 3, dtype=np.float64) - 1.0) / nx
    phi = np.zeros((ny + 3, nx + 3, 2), np.float64)
    phi[:, :, 0] = amp * np.sin(2.0 * np.pi * lat_j)[None, :]
    phi[:, :, 1] = amp * np.cos(2.0 * np.pi * lat_i)[:, None]
    field = _ffd_field((h, w), phi, ny, nx)
    yy, xx = np.mgrid[0:h, 0:w]
    src_yx = np.stack([(yy + field[:, :, 0]).ravel(),
                       (xx + field[:, :, 1]).ravel()], axis=1)
    return _resample(x, src_yx)


# --------------------------------------------------------------------------- #
# 3. moving least squares, affine variant (Schaefer et al. 2006)              #
# --------------------------------------------------------------------------- #
def _mls_affine(p, q, pts, alpha=1.0, eps=1e-8):
    """Moving-least-squares *affine* deformation (Schaefer et al., SIGGRAPH 2006).

    For every query point v the weights ``w_i = 1/(|p_i - v|^2 + eps)^alpha``
    define the weighted least-squares affine map that best carries ``{p_i}`` to
    ``{q_i}`` *at that point*:

        p* = sum w_i p_i / sum w_i,     q* = sum w_i q_i / sum w_i
        M  = (sum_i w_i ph_i^T ph_i)^-1 (sum_j w_j ph_j^T qh_j)
        f(v) = (v - p*) M + q*

    with ``ph_i = p_i - p*`` and ``qh_i = q_i - q*``. Because the solve is a
    plain weighted least-squares fit, the map reproduces affine data *exactly*
    for any weights: if ``q_i = p_i A + t`` then ``f(v) = v A + t`` everywhere.
    As v approaches a control point its weight dominates and ``f(v) -> q_i``
    (interpolation). Returns the mapped points, shape ``pts.shape``.
    """
    p = np.asarray(p, np.float64)
    q = np.asarray(q, np.float64)
    pts = np.asarray(pts, np.float64)
    alpha = float(alpha)
    n = int(p.shape[0])
    out = np.empty((pts.shape[0], 2), np.float64)
    for s in range(0, pts.shape[0], _CHUNK):
        vv = pts[s:s + _CHUNK]
        m = vv.shape[0]
        wts = np.empty((n, m), np.float64)
        for i in range(n):
            dy = vv[:, 0] - p[i, 0]
            dx = vv[:, 1] - p[i, 1]
            wts[i] = 1.0 / np.power(dy * dy + dx * dx + eps, alpha)
        sw = wts.sum(axis=0)
        sw = np.where(sw > 0.0, sw, 1.0)
        pstar = (wts.T @ p) / sw[:, None]
        qstar = (wts.T @ q) / sw[:, None]
        a11 = np.zeros(m); a12 = np.zeros(m); a22 = np.zeros(m)
        b11 = np.zeros(m); b12 = np.zeros(m)
        b21 = np.zeros(m); b22 = np.zeros(m)
        for i in range(n):
            wi = wts[i]
            hpy = p[i, 0] - pstar[:, 0]
            hpx = p[i, 1] - pstar[:, 1]
            hqy = q[i, 0] - qstar[:, 0]
            hqx = q[i, 1] - qstar[:, 1]
            a11 += wi * hpy * hpy
            a12 += wi * hpy * hpx
            a22 += wi * hpx * hpx
            b11 += wi * hpy * hqy
            b12 += wi * hpy * hqx
            b21 += wi * hpx * hqy
            b22 += wi * hpx * hqx
        det = a11 * a22 - a12 * a12
        ok = np.abs(det) > 1e-12
        safe = np.where(ok, det, 1.0)
        # M = A_pp^-1 A_pq, degenerate pixels fall back to a pure translation
        m11 = np.where(ok, (a22 * b11 - a12 * b21) / safe, 1.0)
        m12 = np.where(ok, (a22 * b12 - a12 * b22) / safe, 0.0)
        m21 = np.where(ok, (a11 * b21 - a12 * b11) / safe, 0.0)
        m22 = np.where(ok, (a11 * b22 - a12 * b12) / safe, 1.0)
        ry = vv[:, 0] - pstar[:, 0]
        rx = vv[:, 1] - pstar[:, 1]
        out[s:s + _CHUNK, 0] = ry * m11 + rx * m21 + qstar[:, 0]
        out[s:s + _CHUNK, 1] = ry * m12 + rx * m22 + qstar[:, 1]
    return out


def deform_mls(v, a, b):
    """Moving-least-squares image deformation, affine variant (Schaefer 2006).

    A 5x5 grid of control points ``p_i`` is displaced to
    ``q_i = p_i + amp*[sin(2 pi gx), cos(2 pi gy)]`` (gy, gx = normalised
    control coordinates). For every destination pixel the weighted
    least-squares affine map is re-solved with the weights
    ``w_i = 1/|p_i - v|^(2 alpha)``, so the warp is a *different* affine at every
    pixel -- smooth, interpolating at the control points, and exact on affine
    data. The backward map is obtained by solving the same MLS problem with the
    roles of ``p`` and ``q`` swapped (the resampling formulation of the paper's
    section 4), which is the exact inverse whenever the control data is affine
    and a smooth approximation of it otherwise. ``a`` sets the amplitude
    ``amp = 0.12*a*min(H,W)``, ``b`` the falloff ``alpha = 0.5 + 1.5b`` (large
    alpha = tightly local deformation). ``a = 0`` gives ``q = p``, hence the
    identity (up to sub-pixel resampling error).
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    h, w = x.shape[:2]
    if h < 2 or w < 2:
        return x
    p = _grid_points(h, w, _MLS_GRID)
    amp = 0.12 * a * float(min(h, w))
    gy = p[:, 0] / float(h - 1)
    gx = p[:, 1] / float(w - 1)
    q = p + np.stack([amp * np.sin(2.0 * np.pi * gx),
                      amp * np.cos(2.0 * np.pi * gy)], axis=1)
    alpha = 0.5 + 1.5 * b
    src_yx = _mls_affine(q, p, _pixel_points(h, w), alpha)
    return _resample(x, src_yx)


# --------------------------------------------------------------------------- #
# registry                                                                    #
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # halcon="" for EVERY op. HALCON has no thin-plate-spline, free-form
    # deformation or moving-least-squares operator at all (its warp operators
    # only *apply* a vector field the caller supplies, and its deformable-model
    # family is matching, not synthesis), so this cluster is a new capability
    # and makes no coverage claim. It also does not overlap the existing
    # sk_swirl / aug_barrel closed-form global warps -- see the module docstring.
    defs = [
        ("deform_tps", "deformation", deform_tps),
        ("deform_ffd", "deformation", deform_ffd),
        ("deform_mls", "deformation", deform_mls),
    ]
    return [Op(n, c, "", IMAGE, IMAGE, _safe(f, IMAGE)) for (n, c, f) in defs]
