"""Scene flow & ego-motion — geometric analysis of an optical-flow field (numpy).

The bridge between :mod:`flow` (which *measures* 2-D image motion as ``(u, v)``
fields) and :mod:`camera` (which knows the 2-D<->3-D geometry). From a flow field
this recovers the quantities a moving agent needs to *navigate*: where it is
heading (focus of expansion / ego-translation direction), how soon it will hit
what it sees (time-to-contact / looming), and — with stereo depth — the full 3-D
motion of every surface point (scene flow).

Flow convention (matching :mod:`flow`): a feature at ``(x, y)`` moves to
``(x + u, y + v)``; ``u``/``v`` are equal-shape (H, W) arrays.

References (public literature — reimplemented, not derived from any product):
- Longuet-Higgins & Prazdny, "The interpretation of a moving retinal image",
  Proc. R. Soc. Lond. B 1980 (focus of expansion, flow field structure).
- Lee, "A theory of visual control of braking based on information about
  time-to-collision", Perception 1976 (tau / time-to-contact).
- Vedula et al., "Three-Dimensional Scene Flow", ICCV 1999 (scene flow).
"""
from __future__ import annotations

import numpy as np

__all__ = ["flow_divergence", "flow_curl", "focus_of_expansion",
           "time_to_contact", "looming", "ego_translation_from_flow", "scene_flow"]


def _uv(u, v):
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    if u.shape != v.shape or u.ndim != 2:
        raise ValueError("u and v must be equal-shape 2-D flow fields")
    return u, v


def flow_divergence(u, v) -> np.ndarray:
    """Divergence of the flow field ``du/dx + dv/dy`` (per-pixel).

    Positive where the flow spreads apart — a surface growing in the image because
    it is approaching (looming). The scalar collision cue underlying
    :func:`time_to_contact`. Returns (H, W)."""
    u, v = _uv(u, v)
    dudx = np.gradient(u, axis=1)
    dvdy = np.gradient(v, axis=0)
    return dudx + dvdy


def flow_curl(u, v) -> np.ndarray:
    """Curl (vorticity) of the flow field ``dv/dx - du/dy`` (per-pixel).

    Non-zero under camera roll or a spinning object; separating it from divergence
    tells rotation apart from approach. Returns (H, W)."""
    u, v = _uv(u, v)
    dvdx = np.gradient(v, axis=1)
    dudy = np.gradient(u, axis=0)
    return dvdx - dudy


def focus_of_expansion(u, v, min_speed: float = 1e-3):
    """Focus of expansion: the image point the flow radiates from under translation.

    For a translating camera every flow vector points along a line through the FoE
    (Longuet-Higgins & Prazdny 1980); this returns the least-squares intersection of
    those lines, weighted by flow magnitude. The FoE is the projected heading
    direction — where the camera is going. Only pixels moving faster than
    *min_speed* vote. Returns ``(x0, y0)`` in pixels (``(nan, nan)`` if too little
    motion)."""
    u, v = _uv(u, v)
    H, W = u.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    speed = np.hypot(u, v)
    m = speed > float(min_speed)
    if m.sum() < 2:
        return (float("nan"), float("nan"))
    # each flow line has normal (v, -u): n . q = n . p
    a = np.stack([v[m], -u[m]], axis=1)
    b = v[m] * xx[m] - u[m] * yy[m]
    w = speed[m]
    aw = a * w[:, None]
    q, *_ = np.linalg.lstsq(aw, b * w, rcond=None)
    return (float(q[0]), float(q[1]))


def time_to_contact(u, v, foe=None, min_speed: float = 1e-3) -> np.ndarray:
    """Per-pixel time-to-contact ``tau`` in frames (Lee 1976).

    ``tau = |p - foe|^2 / (flow . (p - foe))`` — the radial distance from the focus
    of expansion divided by the radial flow speed. It is *positive and finite* where
    a surface is approaching (the flow points outward from the FoE) and how many
    frames until contact if the motion holds; ``inf`` where there is no approaching
    radial motion. Object-size-independent (that is tau's whole point). *foe* is
    computed by :func:`focus_of_expansion` if not given. Returns (H, W)."""
    u, v = _uv(u, v)
    if foe is None:
        foe = focus_of_expansion(u, v, min_speed)
    fx0, fy0 = float(foe[0]), float(foe[1])
    H, W = u.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    rx, ry = xx - fx0, yy - fy0
    r2 = rx * rx + ry * ry
    radial = u * rx + v * ry                        # flow projected onto the radial dir
    tau = np.full_like(u, np.inf)
    ok = radial > 1e-9                              # approaching (outward) motion only
    tau[ok] = r2[ok] / radial[ok]
    return tau


def looming(u, v) -> dict:
    """Global approach (collision-imminence) summary from the flow field.

    Returns ``{mean_divergence, expanding, ttc}``: the mean flow divergence (>0 =
    the scene as a whole is growing = the camera is closing on it), a boolean
    ``expanding`` flag, and a global time-to-contact estimate ``ttc = 2 /
    mean_divergence`` frames (from ``div ~ 2/tau`` for a frontally approached plane),
    ``inf`` when not approaching. A cheap "am I about to hit something" gate."""
    div = flow_divergence(u, v)
    md = float(np.mean(div))
    ttc = 2.0 / md if md > 1e-9 else float("inf")
    return {"mean_divergence": md, "expanding": md > 0.0, "ttc": ttc}


def ego_translation_from_flow(u, v, K, min_speed: float = 1e-3) -> np.ndarray:
    """Camera translation *direction* (heading) from a translational flow field.

    The focus of expansion is the projection of the translation direction, so
    ``t_dir ∝ K^-1 [foe_x, foe_y, 1]``. Returns the unit heading vector (3,) in the
    camera frame (``+z`` forward): flow radiating from the principal point comes back
    as ``[0, 0, 1]`` (driving straight ahead), an off-centre FoE tilts it. Assumes
    dominant translation (rotation not decoupled). ``(nan, nan, nan)`` if the FoE is
    undefined."""
    foe = focus_of_expansion(u, v, min_speed)
    if not np.isfinite(foe[0]):
        return np.array([np.nan, np.nan, np.nan])
    K = np.asarray(K, np.float64)
    if K.shape != (3, 3):
        raise ValueError("K must be 3x3")
    d = np.linalg.inv(K) @ np.array([foe[0], foe[1], 1.0])
    return d / max(np.linalg.norm(d), 1e-12)


def scene_flow(disp0, disp1, u, v, fx: float = 1.0, baseline: float = 1.0,
               cx: float | None = None, cy: float | None = None,
               min_disp: float = 1e-6) -> np.ndarray:
    """Per-pixel 3-D scene flow from a stereo+optical-flow pair (Vedula 1999).

    Combines two disparity maps and the optical flow between the two left frames:
    back-projects each pixel at t0 (depth from *disp0*) and its flow-matched pixel at
    t1 (depth from *disp1* sampled at ``(x+u, y+v)``), and returns their 3-D
    displacement ``(H, W, 3)`` in camera units — the true 3-D motion of each visible
    surface point, not just its 2-D image motion. ``NaN`` where either disparity is
    invalid. This is the depth-aware motion field a manipulator/navigator uses to
    tell a receding object from an approaching one and to predict where a moving
    part will be."""
    from scipy import ndimage

    d0 = np.asarray(disp0, np.float64)
    d1 = np.asarray(disp1, np.float64)
    u, v = _uv(u, v)
    if d0.shape != u.shape or d1.shape != u.shape:
        raise ValueError("disp0/disp1/u/v must share shape")
    H, W = d0.shape
    cx = (W - 1) / 2.0 if cx is None else float(cx)
    cy = (H - 1) / 2.0 if cy is None else float(cy)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

    def points(disp, X, Y):
        Z = np.full_like(disp, np.nan)
        ok = disp > min_disp
        Z[ok] = float(fx) * float(baseline) / disp[ok]
        Xc = (X - cx) * Z / float(fx)
        Yc = (Y - cy) * Z / float(fx)
        return np.stack([Xc, Yc, Z], axis=-1)

    P0 = points(d0, xx, yy)
    x1, y1 = xx + u, yy + v
    d1_at = ndimage.map_coordinates(d1, [y1, x1], order=1, mode="constant", cval=np.nan)
    P1 = points(d1_at, x1, y1)
    return P1 - P0
