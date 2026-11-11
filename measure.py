"""Measurement primitives (numpy + scipy) — line intensity profiles and simple
geometry, the "measure" tools a vision IDE provides. Points are (row, col)."""
from __future__ import annotations

import numpy as np

__all__ = ["line_profile", "distance", "angle", "profile_stats",
           "fit_line", "fit_circle", "fit_circle_geometric",
           "fit_curve_principal_axis", "fit_ellipse", "fit_rectangle2",
           "fit_rectangle2_lsq"]


def line_profile(image, p0, p1, num=None):
    """Intensity along the segment p0 -> p1 (bilinear sampled). Returns a 1-D array
    (gray) or (N, 3) (color). ``num`` samples defaults to the pixel length."""
    from scipy.ndimage import map_coordinates
    img = np.asarray(image, np.float64)
    (y0, x0), (y1, x1) = p0, p1
    n = int(num) if num else int(np.hypot(y1 - y0, x1 - x0)) + 1
    ys = np.linspace(y0, y1, n)
    xs = np.linspace(x0, x1, n)
    if img.ndim == 2:
        return map_coordinates(img, [ys, xs], order=1, mode="nearest")
    return np.stack([map_coordinates(img[..., c], [ys, xs], order=1, mode="nearest")
                     for c in range(img.shape[2])], axis=-1)


def distance(p0, p1) -> float:
    """Euclidean distance between two (row, col) points."""
    return float(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))


def angle(p0, p1) -> float:
    """Angle of the segment p0 -> p1 in degrees (image y downward), in (-180, 180]."""
    return float(np.degrees(np.arctan2(p1[0] - p0[0], p1[1] - p0[1])))


def profile_stats(prof) -> dict:
    """min / max / mean / and the index of the strongest edge (|gradient| peak)."""
    p = np.asarray(prof, np.float64)
    g = np.abs(np.gradient(p if p.ndim == 1 else p.mean(-1)))
    return {"n": int(len(p)), "min": float(np.min(p)), "max": float(np.max(p)),
            "mean": float(np.mean(p)), "edge_at": int(np.argmax(g))}


# --------------------------------------------------------------------------- #
# Geometric primitive fitting — the sub-pixel metrology HALCON does with       #
# fit_line_contour_xld / fit_circle_contour_xld / fit_ellipse_contour_xld.     #
# Fit a line / circle / ellipse to a set of (row, col) points (e.g. an XLD     #
# edge contour) by classical least squares; return the geometric parameters    #
# plus an honest RMS residual. Fail-closed: malformed or degenerate input       #
# raises ValueError rather than returning a meaningless fit.                    #
# --------------------------------------------------------------------------- #
def _as_points(points, min_n: int, name: str = "points") -> np.ndarray:
    p = np.asarray(points, np.float64)
    if p.ndim != 2 or p.shape[1] != 2:
        raise ValueError(f"{name} must be an (N, 2) array of (row, col); got shape {p.shape}")
    if not np.all(np.isfinite(p)):
        raise ValueError(f"{name} contains non-finite values")
    if len(p) < min_n:
        raise ValueError(f"{name} needs >= {min_n} points to fit; got {len(p)}")
    return p


def _centre_and_scale(p: np.ndarray, what: str):
    """Centroid ``(mx, my)`` and RMS radius ``scale`` of (row, col) points.

    ★2026-11-05 敵対的検証 N6/N8: 当てはめは重心を引いて ``scale`` で割った座標で解く。
    生の座標のまま ``x²`` を組むと、画像上の位置(オフセット 6000 px)で楕円の軸が 2 % ずれ、
    小さい物体(半径 8e-7)を絶対の床 ``1e-12`` で「退化」と捨てていた。退化(一致点)の判定は
    座標の大きさに対する相対量(丸めの屑 ~ eps·|p| の 450 倍)で行う。
    """
    y, x = p[:, 0], p[:, 1]
    mx, my = float(x.mean()), float(y.mean())
    xc, yc = x - mx, y - my
    scale = float(np.sqrt(np.mean(xc * xc + yc * yc)))
    mag = float(np.max(np.abs(p)))
    if not np.isfinite(scale) or scale == 0.0 or scale <= 1e-13 * mag:
        raise ValueError(f"points are coincident; no {what} is defined")
    return mx, my, xc, yc, scale


def fit_line(points) -> dict:
    """Total-least-squares line fit to (row, col) points — orthogonal regression via
    SVD, minimising the perpendicular distance (unlike y-on-x regression, it is
    isotropic and handles vertical lines). Returns a point on the line ``(cy, cx)``,
    a unit direction ``(dy, dx)``, the image-plane angle in degrees (y downward,
    in (-90, 90]), and the RMS orthogonal residual. Raises ``ValueError`` on < 2
    points or a coincident cluster with no defined direction."""
    p = _as_points(points, 2, "points")
    y, x = p[:, 0], p[:, 1]
    # 一致点の判定は座標の大きさに対する相対量(以前は s[0] <= 1e-12 の絶対量で、
    # 長さ 1e-13 の正しい線分を「一致点」と捨てていた。敵対的検証 2026-11-05 N6 の兄弟)。
    mx, my, _xc, _yc, _scale = _centre_and_scale(p, "line direction")
    _, s, vt = np.linalg.svd(np.column_stack([x - mx, y - my]),
                             full_matrices=False)  # full_matrices=False: U は捨てるのに (N,N) を確保していた(2026-09-06 実測 20000 点で 3.73 s / 3.2 GB → 0.88 ms、Vt はビット一致)
    dx, dy = float(vt[0, 0]), float(vt[0, 1])          # unit direction (col, row)
    resid = (x - mx) * (-dy) + (y - my) * dx           # signed perpendicular distance
    ang = np.degrees(np.arctan2(dy, dx))
    ang = ((ang + 90.0) % 180.0) - 90.0                # direction is a line, not a ray
    return {"cy": my, "cx": mx, "dy": dy, "dx": dx,
            "angle_deg": float(ang), "rms": float(np.sqrt(np.mean(resid ** 2)))}


def fit_circle(points) -> dict:
    """Algebraic (Kåsa / Coope) least-squares circle fit to (row, col) points: solve
    ``x² + y² = 2·cx·x + 2·cy·y + c`` in the least-squares sense — exact for points
    on a circle, and a standard robust estimator under moderate noise (Coope 1993).
    Returns centre ``(cy, cx)``, ``r``, and the RMS radial residual. Raises
    ``ValueError`` on < 3 points or a collinear/degenerate set (no finite circle).
    This algebraic fit is biased on short noisy arcs; use
    :func:`fit_circle_geometric` to minimise geometric radial distances."""
    p = _as_points(points, 3, "points")
    y, x = p[:, 0], p[:, 1]
    # ★2026-11-05 敵対的検証 N6: 重心を引き RMS 半径で割った座標で解く。生の座標では
    # x²+y² の桁落ちでオフセット 1e6 の r=2 が 2.00003 になり、r² <= 1e-12 の絶対の床で
    # 半径 8e-7 の円を「退化」と捨てていた。退化の判定はいずれも相対量。
    mx, my, xc, yc, scale = _centre_and_scale(p, "circle")
    # Collinear points admit only an infinite-radius (line) "circle": the algebraic
    # system is rank-deficient. Reject it explicitly (perpendicular spread ~ 0).
    _, sv, _ = np.linalg.svd(np.column_stack([xc, yc]),
                             full_matrices=False)  # U は捨てる(2026-09-06)
    if sv[1] <= 1e-9 * sv[0]:
        raise ValueError("points are collinear or coincident; no circle fit")
    u, v = xc / scale, yc / scale                      # 無次元(RMS 半径 1)
    a_mat = np.column_stack([2.0 * u, 2.0 * v, np.ones(len(u))])
    sol, *_ = np.linalg.lstsq(a_mat, u * u + v * v, rcond=None)
    cu, cv, c = float(sol[0]), float(sol[1]), float(sol[2])
    r2 = c + cu * cu + cv * cv                          # 無次元の r²
    if not np.isfinite(r2) or r2 <= 1e-12:
        raise ValueError("points are collinear or degenerate; no circle fit")
    cx, cy = mx + scale * cu, my + scale * cv
    r = float(scale * np.sqrt(r2))
    resid = np.hypot(x - cx, y - cy) - r
    return {"cy": cy, "cx": cx, "r": r, "rms": float(np.sqrt(np.mean(resid ** 2)))}


def fit_circle_geometric(points, *, max_iterations: int = 100,
                         radius_limit_factor: float = 1e6) -> dict:
    """短い円弧を含む ``(row, col)`` 点に幾何距離の最小二乗で円と半径を当てはめる。

    Kåsa's algebraic fit supplies the initial centre and radius, then a
    Levenberg--Marquardt solve minimises ``hypot(x-cx, y-cy) - r`` (Chernov &
    Lesort 2005).  Returns ``cy``, ``cx``, ``r``, geometric ``rms``,
    ``iterations`` and ``converged``. ``max_iterations`` is the maximum number
    of function evaluations. ``radius_limit_factor`` bounds the fitted radius
    relative to the point-cloud span; an exceeded bound is reported as
    ``ValueError`` instead of returning a line-like, effectively infinite
    circle. Non-finite, collinear, or fewer than three points are also rejected.
    """
    from scipy.optimize import least_squares
    p = _as_points(points, 3, "points")
    initial = fit_circle(p)  # also performs the collinearity check
    y, x = p[:, 0], p[:, 1]
    span = float(np.hypot(np.ptp(x), np.ptp(y)))
    if not isinstance(max_iterations, (int, np.integer)) or max_iterations < 1:
        raise ValueError("max_iterations must be a positive integer")
    lim = float(radius_limit_factor)
    if not np.isfinite(lim) or lim <= 1.0:
        raise ValueError("radius_limit_factor must be finite and > 1")

    def residual(q):
        return np.hypot(x - q[0], y - q[1]) - q[2]

    sol = least_squares(residual, [initial["cx"], initial["cy"], initial["r"]],
                        method="lm", max_nfev=int(max_iterations),
                        ftol=1e-12, xtol=1e-12, gtol=1e-12)
    cx, cy, radius = map(float, sol.x)
    if (not np.all(np.isfinite(sol.x)) or radius <= 0.0
            or radius > lim * max(span, np.finfo(float).eps)):
        raise ValueError("geometric circle radius diverged; the arc is too line-like")
    res = residual(sol.x)
    return {"cy": cy, "cx": cx, "r": radius,
            "rms": float(np.sqrt(np.mean(res * res))),
            "iterations": int(sol.nfev), "converged": bool(sol.success)}


def fit_curve_principal_axis(points, degree: int = 2,
                             *, isotropy_ratio: float = 0.95) -> dict:
    """斜めの曲がった縁を主軸へ回してから多項式 ``y'=f(x')`` を当てはめる。

    Returns the image-plane ``angle_deg``, ``centroid`` (row, col), polynomial
    ``coefficients`` in NumPy's descending-power convention, orthonormal
    ``axes`` (rows are local x/y axes in col,row order), local coordinates,
    ``fitted_points`` in the original row/col frame, and a gradient-normalised
    geometric ``rms``. ``degree`` must be at least one and leave more samples
    than coefficients. A nearly round cloud (minor/major variance ratio at or
    above ``isotropy_ratio``) is rejected because its principal direction is
    undefined.
    """
    p = _as_points(points, 3, "points")
    degree = int(degree)
    if degree < 1 or len(p) <= degree:
        raise ValueError("degree must be >= 1 with more points than coefficients")
    ratio_limit = float(isotropy_ratio)
    if not (0.0 < ratio_limit < 1.0):
        raise ValueError("isotropy_ratio must be in (0, 1)")
    xy = p[:, ::-1]
    center = xy.mean(0)
    _, s, vt = np.linalg.svd(xy - center, full_matrices=False)
    if s[0] <= np.finfo(float).eps * np.linalg.norm(xy - center) or (s[1] / s[0]) ** 2 >= ratio_limit:
        raise ValueError("point cloud is too isotropic; no principal axis is defined")
    if np.linalg.det(vt) < 0:
        vt[1] *= -1
    if vt[0, 0] < 0:
        vt *= -1
    local = (xy - center) @ vt.T
    coef = np.polyfit(local[:, 0], local[:, 1], degree)
    fitted_local = np.column_stack([local[:, 0], np.polyval(coef, local[:, 0])])
    fitted_xy = center + fitted_local @ vt
    slope = np.polyval(np.polyder(coef), local[:, 0])
    geometric = (local[:, 1] - fitted_local[:, 1]) / np.sqrt(1.0 + slope * slope)
    angle = float(((np.degrees(np.arctan2(vt[0, 1], vt[0, 0])) + 90) % 180) - 90)
    return {"angle_deg": angle, "centroid": center[::-1].copy(),
            "coefficients": coef, "axes": vt, "local_points": local,
            "fitted_points": fitted_xy[:, ::-1],
            "rms": float(np.sqrt(np.mean(geometric * geometric)))}


def fit_ellipse(points) -> dict:
    """Direct least-squares ellipse fit to (row, col) points — Halir & Flusser 1998,
    the numerically-stable form of Fitzgibbon 1996 that is guaranteed to return an
    ellipse-specific conic (never a hyperbola/parabola). Returns centre ``(cy, cx)``,
    the semi-major/minor axes ``ra >= rb``, the major-axis image-plane angle in
    degrees (y downward, in (-90, 90]), and the RMS algebraic residual of the
    unit-normalised conic. Raises ``ValueError`` on < 5 points or a point set that
    admits no ellipse (collinear / hyperbolic)."""
    p = _as_points(points, 5, "points")
    y, x = p[:, 0], p[:, 1]
    # ★2026-11-05 敵対的検証 N8: Halir-Flusser の散布行列を生の座標で組むと、x⁴ と 1 が同じ
    # 行列に並び、画像上の位置だけで答えが変わっていた(ra=5, rb=4, 20° が中心 (6000,8000) で
    # 5.119 / 3.912 / 21.94°)。重心を引き RMS 半径で割った (u, v) で解いて戻す
    # (Hartley 正規化と同じ考え)。rms は従来どおり元の座標での単位正規化した 2 次曲線の残差。
    mx, my, xc, yc, sc = _centre_and_scale(p, "ellipse")
    un, vn = xc / sc, yc / sc
    d1 = np.column_stack([un * un, un * vn, vn * vn])  # quadratic part
    d2 = np.column_stack([un, vn, np.ones(len(un))])   # linear part
    s1, s2, s3 = d1.T @ d1, d1.T @ d2, d2.T @ d2
    try:
        t = -np.linalg.solve(s3, s2.T)
    except np.linalg.LinAlgError:
        raise ValueError("degenerate point set; no ellipse fit") from None
    m = s1 + s2 @ t
    m = np.array([m[2] / 2.0, -m[1], m[0] / 2.0])      # premultiply by inv(C1)
    _evals, evecs = np.linalg.eig(m)
    evecs = np.real(evecs)                             # degenerate sets can yield complex evecs
    cond = 4.0 * evecs[0] * evecs[2] - evecs[1] ** 2   # 4ac - b² > 0 selects the ellipse
    valid = np.where(cond > 0)[0]
    if len(valid) == 0:
        raise ValueError("point set admits no ellipse (collinear or hyperbolic)")
    a1 = evecs[:, valid[0]]
    a2 = t @ a1
    a, b, c, d, e, f = (float(a1[0]), float(a1[1]), float(a1[2]),
                        float(a2[0]), float(a2[1]), float(a2[2]))
    m0 = np.array([[a, b / 2.0], [b / 2.0, c]])        # 2×2 quadratic form
    try:
        u0, v0 = np.linalg.solve(m0, [-d / 2.0, -e / 2.0])
    except np.linalg.LinAlgError:
        raise ValueError("degenerate ellipse conic; no centre") from None
    f_center = a * u0 * u0 + b * u0 * v0 + c * v0 * v0 + d * u0 + e * v0 + f
    lam, vec = np.linalg.eigh(m0)                      # ascending eigenvalues
    # The conic's overall sign is arbitrary (eigenvector direction), so test the
    # sign-invariant shape: same-signed eigenvalues => ellipse; the semi-axes are
    # sqrt(-f_center / lam), which must be real and positive.
    if lam[0] * lam[1] <= 0:
        raise ValueError("point set admits no ellipse (hyperbolic quadratic form)")
    ratios = -f_center / lam
    if not np.all(np.isfinite(ratios)) or np.any(ratios <= 0):
        raise ValueError("point set admits no ellipse (degenerate quadratic form)")
    axes = sc * np.sqrt(ratios)                        # a semi-axis per eigenvector (元の単位)
    imaj = int(np.argmax(axes))
    ra, rb = float(axes[imaj]), float(axes[1 - imaj])
    vmaj = vec[:, imaj]                                # (x, y) direction of the major axis
    ang = np.degrees(np.arctan2(float(vmaj[1]), float(vmaj[0])))
    ang = ((ang + 90.0) % 180.0) - 90.0
    x0, y0 = mx + sc * float(u0), my + sc * float(v0)
    # (u, v) = ((x-mx)/sc, (y-my)/sc) の 2 次曲線を sc² 倍して元の座標の係数へ戻す。
    coef = np.array([
        a, b, c,
        -2.0 * a * mx - b * my + d * sc,
        -b * mx - 2.0 * c * my + e * sc,
        a * mx * mx + b * mx * my + c * my * my - d * sc * mx - e * sc * my + f * sc * sc,
    ], np.float64)
    coef = coef / (np.linalg.norm(coef) or 1.0)
    resid = (coef[0] * x * x + coef[1] * x * y + coef[2] * y * y
             + coef[3] * x + coef[4] * y + coef[5])
    return {"cy": float(y0), "cx": float(x0), "ra": ra, "rb": rb,
            "angle_deg": float(ang), "rms": float(np.sqrt(np.mean(resid ** 2)))}


def _half_turn_angle(ang: float) -> float:
    """Fold an axis angle (deg) into ``(-90, 90]``; within 1e-9 deg of +-90 snaps to 90.

    An undirected axis is defined modulo 180 deg. ``((a + 90) % 180) - 90`` lands in
    ``[-90, 90)``, and floating-point noise on a vertical axis flipped it between
    ``-90`` and ``+90`` for the same rectangle (2026-11-09 probe)."""
    a = float(-((90.0 - float(ang)) % 180.0) + 90.0)        # (-90, 90]
    if abs(abs(a) - 90.0) < 1e-9:
        a = 90.0
    return a


def fit_rectangle2(points) -> dict:
    """Minimum-area oriented bounding rectangle of (row, col) points, via rotating
    calipers on the convex hull (an optimal min-area rectangle has one side
    collinear with a hull edge; Freeman & Shapira 1975). This is HALCON's
    ``smallest_rectangle2`` / OpenCV's ``cv2.minAreaRect`` (identical half sides
    in the 2026-11-09 probe), **not** the least-squares fit of HALCON
    ``fit_rectangle2_contour_xld`` — for that use :func:`fit_rectangle2_lsq`.

    Returns centre ``(cy, cx)``, the two half-side lengths ``l1 >= l2``, the
    long-side angle ``angle_deg`` and the RMS distance of the points to the
    rectangle boundary (~0 for points on a rectangle outline).

    Angle convention: ``atan2(d_row, d_col)`` of the long side in degrees with
    rows growing downward — i.e. **clockwise on screen**, the opposite sign of
    HALCON's ``phi`` (counter-clockwise). Range ``(-90, 90]``: a vertical long
    side is always ``+90.0`` (before 2026-11-09 the same rectangle came out as
    ``+90`` or ``-90`` depending on rounding). Other angles are not bit-identical to
    the pre-2026-11-09 values: the half-turn folding moves them by rounding only
    (434 of 2000 random rectangles, at most 2.8e-14 degrees).

    Limits: because it encloses every point, noise and outliers bias the sides
    outward — on a 40x20 half-side outline, sigma 0.5 px gives l1/l2 +4.3 %/+7.4 %,
    sigma 1 px +8 %/+15 %, and one far outlier turns l1 = 40 into 170.
    Raises ``ValueError`` on < 3 points, non-finite values or a collinear set."""
    from scipy.spatial import ConvexHull
    try:                                               # public since scipy 1.8
        from scipy.spatial import QhullError
    except ImportError:                                # older scipy
        from scipy.spatial.qhull import QhullError
    p = _as_points(points, 3, "points")
    pts = np.column_stack([p[:, 1], p[:, 0]])          # (x, y)
    try:
        hull = ConvexHull(pts)
    except QhullError:
        raise ValueError("points are collinear or degenerate; no rectangle fit") from None
    h = pts[hull.vertices]                              # ordered hull vertices
    best = None
    for i in range(len(h)):
        edge = h[(i + 1) % len(h)] - h[i]
        norm = float(np.hypot(edge[0], edge[1]))
        # ★1.0 前の修正 2026-11-05 abs-floor: 以前は ``norm < 1e-12``。辺 1e-13 の矩形では全辺を飛ばし TypeError で落ちた。
        #   凸包の頂点は互いに異なるので、長さ 0 の辺だけを飛ばす。
        if norm == 0.0:
            continue
        u = edge / norm                                # a candidate rectangle axis
        v = np.array([-u[1], u[0]])
        pu, pv = h @ u, h @ v
        w, ht = float(np.ptp(pu)), float(np.ptp(pv))
        area = w * ht
        if best is None or area < best[0]:
            centre = ((pu.max() + pu.min()) / 2.0) * u + ((pv.max() + pv.min()) / 2.0) * v
            best = (area, w, ht, u.copy(), centre)
    _, w, ht, u, centre = best
    long_axis = u if w >= ht else np.array([-u[1], u[0]])
    a_half, b_half = max(w, ht) / 2.0, min(w, ht) / 2.0
    ang = _half_turn_angle(np.degrees(np.arctan2(float(long_axis[1]), float(long_axis[0]))))
    # RMS point-to-boundary distance in the rectangle frame (signed box SDF, Quilez).
    u2 = long_axis
    v2 = np.array([-u2[1], u2[0]])
    rel = pts - centre
    qu = np.abs(rel @ u2) - a_half
    qv = np.abs(rel @ v2) - b_half
    sdf = np.hypot(np.maximum(qu, 0.0), np.maximum(qv, 0.0)) + np.minimum(np.maximum(qu, qv), 0.0)
    return {"cy": float(centre[1]), "cx": float(centre[0]), "l1": a_half, "l2": b_half,
            "angle_deg": float(ang), "rms": float(np.sqrt(np.mean(sdf ** 2)))}


def fit_rectangle2_lsq(points, max_iter: int = 50, tukey_c: float = 4.685) -> dict:
    """Robust least-squares rectangle fitted to outline points (row, col).

    Starts from :func:`fit_rectangle2` (min-area rectangle) of the points that
    are not isolated (8th-nearest-neighbour distance <= 3x the median; an
    outline is dense, a stray point is not), then alternates
    (1) assigning each point to the nearest of the 4 side segments and (2) one
    Gauss-Newton step on ``(cx, cy, theta, l1, l2)`` minimising the Tukey-
    weighted signed point-to-side distances (scale = 1.4826 * MAD, floored at
    1e-9 of the point span so an exact outline converges). This is the
    counterpart of HALCON ``fit_rectangle2_contour_xld`` (least squares with
    robust weights), which :func:`fit_rectangle2` is *not*.

    Measured (2026-11-09, half sides 40x20 at 25 deg, 2000 outline points,
    sigma 1 px): min-area l1/l2 = 43.18/23.05, this function within 0.1 px and
    0.1 deg; one far outlier (min-area l1 = 170) gets weight 0.

    Returns the keys of :func:`fit_rectangle2` (``cy, cx, l1 >= l2,
    angle_deg`` in ``(-90, 90]`` clockwise on screen, ``rms`` = RMS distance of
    the inlier points to their side) plus ``inlier_fraction`` (Tukey weight > 0)
    and ``iterations``.

    Limits: the min-area start must put most points on the right side — a
    dense cluster of outliers (not isolated stray points) survives the start
    filter and drags the start too far. The points must sample all four sides; a side with no
    inlier keeps its min-area extent.

    Raises:
        ValueError: < 4 points, non-finite values, a collinear set, or
            ``max_iter`` / ``tukey_c`` not positive.
    """
    p = _as_points(points, 4, "points")
    if int(max_iter) < 1:
        raise ValueError(f"max_iter must be >= 1; got {max_iter!r}")
    tc = float(tukey_c)
    if not np.isfinite(tc) or tc <= 0.0:
        raise ValueError(f"tukey_c must be a finite positive number; got {tukey_c!r}")
    # 外接矩形は孤立した点 1 個で辺が伸びる(40 -> 170)。初期値だけは孤立点を除いて作る:
    # 8 番目の近傍までの距離が中央値の 3 倍を超える点(輪郭は密、孤立点は疎)。
    from scipy.spatial import cKDTree
    kk = int(min(8, len(p) - 1))
    dk = cKDTree(p).query(p, k=kk + 1)[0][:, -1]
    dense = dk <= 3.0 * float(np.median(dk))
    try:
        init = fit_rectangle2(p[dense]) if dense.sum() >= 3 else fit_rectangle2(p)
    except ValueError:
        init = fit_rectangle2(p)
    pts = np.column_stack([p[:, 1], p[:, 0]])                # (x, y)
    span = float(np.ptp(pts, axis=0).max()) or 1.0
    c = np.array([init["cx"], init["cy"]], np.float64)
    th = float(np.radians(init["angle_deg"]))
    half = np.array([init["l1"], init["l2"]], np.float64)
    it = 0
    w = np.ones(len(pts))
    r = np.zeros(len(pts))
    for it in range(1, int(max_iter) + 1):
        u = np.array([np.cos(th), np.sin(th)])
        v = np.array([-np.sin(th), np.cos(th)])
        rel = pts - c
        qu, qv = rel @ u, rel @ v
        # distance to each side *segment* (not the infinite line) decides the side
        du = np.abs(np.abs(qu) - half[0]) + np.maximum(np.abs(qv) - half[1], 0.0)
        dv = np.abs(np.abs(qv) - half[1]) + np.maximum(np.abs(qu) - half[0], 0.0)
        on_u = du <= dv                                    # a side normal to u (length 2*l2)
        s_k = np.where(on_u, np.sign(qu), np.sign(qv))
        s_k[s_k == 0] = 1.0
        n = np.where(on_u[:, None], s_k[:, None] * u, s_k[:, None] * v)
        dn = np.where(on_u[:, None], s_k[:, None] * v, -s_k[:, None] * u)   # d n / d theta
        r = np.einsum("ij,ij->i", n, rel) - np.where(on_u, half[0], half[1])
        mad = float(np.median(np.abs(r - np.median(r))))
        sc = max(1.4826 * mad, 1e-9 * span)
        z = r / (tc * sc)
        w = np.where(np.abs(z) < 1.0, (1.0 - z * z) ** 2, 0.0)
        J = np.zeros((len(pts), 5))
        J[:, 0:2] = -n
        J[:, 2] = np.einsum("ij,ij->i", dn, rel)
        J[:, 3] = np.where(on_u, -1.0, 0.0)
        J[:, 4] = np.where(on_u, 0.0, -1.0)
        sw = np.sqrt(w)
        free = np.ones(5, bool)
        free[3] = bool(np.any(w[on_u] > 0))
        free[4] = bool(np.any(w[~on_u] > 0))
        sol, *_ = np.linalg.lstsq(J[:, free] * sw[:, None], -r * sw, rcond=None)
        delta = np.zeros(5)
        delta[free] = sol
        c = c + delta[0:2]
        th = th + float(delta[2])
        half = half + delta[3:5]
        if np.all(np.abs(delta[[0, 1, 3, 4]]) <= 1e-12 * span) and abs(delta[2]) <= 1e-12:
            break
    half = np.abs(half)
    long_u = np.array([np.cos(th), np.sin(th)])
    if half[1] > half[0]:
        half = half[::-1]
        long_u = np.array([-long_u[1], long_u[0]])
    ang = _half_turn_angle(np.degrees(np.arctan2(long_u[1], long_u[0])))
    inl = w > 0
    rms = float(np.sqrt(np.mean(r[inl] ** 2))) if inl.any() else float("nan")
    return {"cy": float(c[1]), "cx": float(c[0]), "l1": float(half[0]), "l2": float(half[1]),
            "angle_deg": float(ang), "rms": rms,
            "inlier_fraction": float(inl.mean()), "iterations": int(it)}
