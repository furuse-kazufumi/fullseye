"""Measurement primitives (numpy + scipy) — line intensity profiles and simple
geometry, the "measure" tools a vision IDE provides. Points are (row, col)."""
from __future__ import annotations

import numpy as np

__all__ = ["line_profile", "distance", "angle", "profile_stats",
           "fit_line", "fit_circle", "fit_ellipse", "fit_rectangle2"]


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


def fit_line(points) -> dict:
    """Total-least-squares line fit to (row, col) points — orthogonal regression via
    SVD, minimising the perpendicular distance (unlike y-on-x regression, it is
    isotropic and handles vertical lines). Returns a point on the line ``(cy, cx)``,
    a unit direction ``(dy, dx)``, the image-plane angle in degrees (y downward,
    in (-90, 90]), and the RMS orthogonal residual. Raises ``ValueError`` on < 2
    points or a coincident cluster with no defined direction."""
    p = _as_points(points, 2, "points")
    y, x = p[:, 0], p[:, 1]
    mx, my = float(x.mean()), float(y.mean())
    _, s, vt = np.linalg.svd(np.column_stack([x - mx, y - my]))
    if s[0] <= 1e-12:
        raise ValueError("points are coincident; no line direction is defined")
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
    ``ValueError`` on < 3 points or a collinear/degenerate set (no finite circle)."""
    p = _as_points(points, 3, "points")
    y, x = p[:, 0], p[:, 1]
    # Collinear points admit only an infinite-radius (line) "circle": the algebraic
    # system is rank-deficient. Reject it explicitly (perpendicular spread ~ 0).
    _, sv, _ = np.linalg.svd(np.column_stack([x - x.mean(), y - y.mean()]))
    if sv[0] <= 1e-12 or sv[1] <= 1e-9 * sv[0]:
        raise ValueError("points are collinear or coincident; no circle fit")
    a_mat = np.column_stack([2.0 * x, 2.0 * y, np.ones(len(x))])
    sol, *_ = np.linalg.lstsq(a_mat, x * x + y * y, rcond=None)
    cx, cy, c = float(sol[0]), float(sol[1]), float(sol[2])
    r2 = c + cx * cx + cy * cy
    if not np.isfinite(r2) or r2 <= 1e-12:
        raise ValueError("points are collinear or degenerate; no circle fit")
    r = float(np.sqrt(r2))
    resid = np.hypot(x - cx, y - cy) - r
    return {"cy": cy, "cx": cx, "r": r, "rms": float(np.sqrt(np.mean(resid ** 2)))}


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
    d1 = np.column_stack([x * x, x * y, y * y])        # quadratic part
    d2 = np.column_stack([x, y, np.ones(len(x))])      # linear part
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
        x0, y0 = np.linalg.solve(m0, [-d / 2.0, -e / 2.0])
    except np.linalg.LinAlgError:
        raise ValueError("degenerate ellipse conic; no centre") from None
    f_center = a * x0 * x0 + b * x0 * y0 + c * y0 * y0 + d * x0 + e * y0 + f
    lam, vec = np.linalg.eigh(m0)                      # ascending eigenvalues
    # The conic's overall sign is arbitrary (eigenvector direction), so test the
    # sign-invariant shape: same-signed eigenvalues => ellipse; the semi-axes are
    # sqrt(-f_center / lam), which must be real and positive.
    if lam[0] * lam[1] <= 0:
        raise ValueError("point set admits no ellipse (hyperbolic quadratic form)")
    ratios = -f_center / lam
    if not np.all(np.isfinite(ratios)) or np.any(ratios <= 0):
        raise ValueError("point set admits no ellipse (degenerate quadratic form)")
    axes = np.sqrt(ratios)                             # a semi-axis per eigenvector
    imaj = int(np.argmax(axes))
    ra, rb = float(axes[imaj]), float(axes[1 - imaj])
    vmaj = vec[:, imaj]                                # (x, y) direction of the major axis
    ang = np.degrees(np.arctan2(float(vmaj[1]), float(vmaj[0])))
    ang = ((ang + 90.0) % 180.0) - 90.0
    coef = np.array([a, b, c, d, e, f], np.float64)
    coef = coef / (np.linalg.norm(coef) or 1.0)
    resid = (coef[0] * x * x + coef[1] * x * y + coef[2] * y * y
             + coef[3] * x + coef[4] * y + coef[5])
    return {"cy": float(y0), "cx": float(x0), "ra": ra, "rb": rb,
            "angle_deg": float(ang), "rms": float(np.sqrt(np.mean(resid ** 2)))}


def fit_rectangle2(points) -> dict:
    """Minimum-area oriented bounding rectangle of (row, col) points — the HALCON
    ``fit_rectangle2_contour_xld`` primitive, via rotating calipers on the convex
    hull (an optimal min-area rectangle has one side collinear with a hull edge;
    Freeman & Shapira 1975). Returns centre ``(cy, cx)``, the two half-side lengths
    ``l1 >= l2``, the long-side image-plane angle (deg, y downward, in (-90, 90]),
    and the RMS distance of the points to the rectangle boundary (~0 for points on
    a rectangle outline). Raises ``ValueError`` on < 3 points or a collinear set."""
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
        if norm < 1e-12:
            continue
        u = edge / norm                                # a candidate rectangle axis
        v = np.array([-u[1], u[0]])
        pu, pv = h @ u, h @ v
        w, ht = float(pu.ptp()), float(pv.ptp())
        area = w * ht
        if best is None or area < best[0]:
            centre = ((pu.max() + pu.min()) / 2.0) * u + ((pv.max() + pv.min()) / 2.0) * v
            best = (area, w, ht, u.copy(), centre)
    _, w, ht, u, centre = best
    long_axis = u if w >= ht else np.array([-u[1], u[0]])
    a_half, b_half = max(w, ht) / 2.0, min(w, ht) / 2.0
    ang = np.degrees(np.arctan2(float(long_axis[1]), float(long_axis[0])))
    ang = ((ang + 90.0) % 180.0) - 90.0
    # RMS point-to-boundary distance in the rectangle frame (signed box SDF, Quilez).
    u2 = long_axis
    v2 = np.array([-u2[1], u2[0]])
    rel = pts - centre
    qu = np.abs(rel @ u2) - a_half
    qv = np.abs(rel @ v2) - b_half
    sdf = np.hypot(np.maximum(qu, 0.0), np.maximum(qv, 0.0)) + np.minimum(np.maximum(qu, qv), 0.0)
    return {"cy": float(centre[1]), "cx": float(centre[0]), "l1": a_half, "l2": b_half,
            "angle_deg": float(ang), "rms": float(np.sqrt(np.mean(sdf ** 2)))}
