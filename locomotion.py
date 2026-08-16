"""Balance & gait perception — the decision layer above terrain / pose (numpy+scipy).

Where :mod:`terrain` says *what the ground is like* and :mod:`pose` says *what
posture a silhouette is in*, this module answers the locomotion questions a legged
robot actually asks: which points are touching the ground, is the centre of mass
over the feet (am I about to fall), and where is each foot in its gait cycle. It
turns perceived 3-D structure into the static-stability quantities hillco/onocollo
walking controllers reason about.

Frame convention: a **world/ground frame** where x, y span the ground and z is up
(same as :mod:`terrain`). "Contacts" are foot/ground contact points; the support
polygon and stability margin live in the ground (x, y) plane.

References (public literature — reimplemented, not derived from any product):
- McGhee & Frank, "On the stability properties of quadruped creeping gaits",
  Mathematical Biosciences 1968 (static stability margin / support polygon).
- Alexander, "The gaits of bipedal and quadrupedal animals", Int. J. Robotics
  Research 1984 (duty factor / gait phase).
"""
from __future__ import annotations

import numpy as np

__all__ = ["contact_points", "com_from_silhouette", "support_polygon",
           "com_support_margin", "gait_phase"]


def contact_points(points, plane, tol: float = 0.02):
    """Points lying within *tol* of a ground plane ``[a,b,c,d]`` = ground contacts.

    Given a cloud and the fitted ground plane (see :func:`pcseg.fit_plane_ransac`),
    returns ``(contacts (M,3), mask)`` — the feet/wheels/base actually touching the
    floor, the input to :func:`support_polygon`."""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    pl = np.asarray(plane, np.float64).ravel()
    if pl.size != 4:
        raise ValueError("plane must be [a, b, c, d]")
    nrm = np.linalg.norm(pl[:3])
    if nrm < 1e-12:                                 # a zero-normal 'plane' is not a
        raise ValueError("degenerate plane: normal has zero length")   # plane; would
    dist = np.abs(P @ pl[:3] + pl[3]) / nrm         # otherwise mark EVERY point a contact
    mask = dist <= float(tol)
    return P[mask], mask


def com_from_silhouette(mask):
    """Centre of mass (centroid) of a binary silhouette, as ``(row, col)`` in
    image coordinates. A cheap proxy for the body COM projection when a full mass
    model is unavailable (evis/hillco posture). Returns ``(nan, nan)`` for an
    empty mask."""
    m = np.asarray(mask) > 0.5
    if not m.any():
        return (float("nan"), float("nan"))
    ys, xs = np.nonzero(m)
    return (float(ys.mean()), float(xs.mean()))


def support_polygon(contacts) -> dict:
    """Convex support polygon of the ground-contact points (ground x, y plane).

    Returns ``{vertices (M,2 CCW), area, perimeter, centroid}``. With <3 distinct
    points it degenerates gracefully (a point or a segment, ``area = 0``). This is
    the base of support a static-stability check is measured against."""
    C = np.asarray(contacts, np.float64)
    if C.ndim != 2 or C.shape[1] not in (2, 3):
        raise ValueError("contacts must be (N, 2) or (N, 3)")
    xy = C[:, :2]
    xy = xy[np.isfinite(xy).all(1)]                 # drop inf/NaN contacts (not a foot)
    uniq = np.unique(np.round(xy, 9), axis=0)
    if uniq.shape[0] < 3:
        # a point or a segment: centroid = midpoint / the point (consistent everywhere)
        return {"vertices": uniq, "area": 0.0,
                "perimeter": (2.0 * float(np.linalg.norm(uniq[0] - uniq[-1]))
                              if uniq.shape[0] == 2 else 0.0),
                "centroid": uniq.mean(0) if uniq.size else np.array([np.nan, np.nan])}
    from scipy.spatial import ConvexHull, QhullError
    try:
        h = ConvexHull(xy)
    except QhullError:                              # collinear points -> segment
        d = uniq - uniq.mean(0)
        t = d @ (d[np.argmax(np.linalg.norm(d, axis=1))])
        ends = uniq[[int(np.argmin(t)), int(np.argmax(t))]]
        return {"vertices": ends, "area": 0.0,
                "perimeter": 2.0 * float(np.linalg.norm(ends[0] - ends[1])),
                "centroid": ends.mean(0)}
    verts = xy[h.vertices]                           # scipy gives CCW for 2-D
    # true area (shoelace) centroid, not the mean of vertices
    x, y = verts[:, 0], verts[:, 1]
    cross = x * np.roll(y, -1) - np.roll(x, -1) * y
    A2 = cross.sum()
    if abs(A2) < 1e-15:
        centroid = verts.mean(0)
    else:
        cx = ((x + np.roll(x, -1)) * cross).sum() / (3.0 * A2)
        cy = ((y + np.roll(y, -1)) * cross).sum() / (3.0 * A2)
        centroid = np.array([cx, cy])
    return {"vertices": verts, "area": float(h.volume),   # 'volume' = area in 2-D
            "perimeter": float(h.area), "centroid": centroid}


def com_support_margin(com_xy, contacts) -> float:
    """Static stability margin: signed distance from the COM ground-projection to
    the support-polygon boundary (McGhee & Frank 1968).

    ``com_xy`` is the COM projected onto the ground (x, y). Positive = the COM is
    **inside** the support polygon by that margin (statically stable, larger =
    safer); negative = outside (tipping). Returns the margin in world units
    (``-inf`` if the polygon is degenerate / has no area)."""
    com = np.asarray(com_xy, np.float64).ravel()[:2]
    poly = support_polygon(contacts)
    V = poly["vertices"]
    if poly["area"] <= 0.0 or V.shape[0] < 3:
        return float("-inf")
    # signed distance to each CCW edge; inside => positive for all edges
    margins = []
    n = V.shape[0]
    for i in range(n):
        a, b = V[i], V[(i + 1) % n]
        e = b - a
        elen = np.linalg.norm(e)
        if elen < 1e-12:
            continue
        # inward normal for a CCW polygon is the left-hand normal of the edge
        nrm = np.array([-e[1], e[0]]) / elen
        margins.append(float(nrm @ (com - a)))
    if not margins:
        return float("-inf")
    return min(margins)                              # distance to the nearest edge (signed)


def gait_phase(foot_heights, stance_frac: float = 0.25, ground=None, contact_tol=None):
    """Classify each foot as stance (planted) or swing per frame from its height.

    ``foot_heights`` is ``(T, F)`` — the height of each of ``F`` feet over ``T``
    frames. Returns ``{stance (T,F bool), duty_factor (F,), n_contacts (T,),
    double_support}`` (duty factor, Alexander 1984; how many feet are down each
    frame; fraction of frames with >=2 feet down).

    ★Stance is defined against a ground reference:

    * ``ground`` given (recommended for anti-cheat) — a foot is stance only when it
      is within ``contact_tol`` of the absolute floor level ``ground``. This is the
      honest test: an airborne / hopping / frozen-in-air foot is correctly NOT
      stance.  ``contact_tol`` defaults to ``stance_frac`` × the foot's own range.
    * ``ground=None`` (default, backward-compatible) — stance is inferred from each
      foot's OWN height range (within ``stance_frac`` of its per-foot minimum).
      ★This heuristic CANNOT tell a foot planted on the floor from a foot at the
      bottom of an airborne trajectory, so it must NOT be used as a stability /
      cheat gate — pass ``ground`` for that."""
    H = np.asarray(foot_heights, np.float64)
    if H.ndim != 2:
        raise ValueError("foot_heights must be (T, F)")
    import warnings
    with warnings.catch_warnings():                 # all-NaN foot -> handled below
        warnings.simplefilter("ignore", RuntimeWarning)
        lo = np.nanmin(H, 0, keepdims=True)          # a single NaN sample must not
        rng = np.nanmax(H, 0, keepdims=True) - lo    # poison the whole foot's min/max
    rng = np.where(~np.isfinite(rng) | (rng < 1e-12), 1.0, rng)  # never-moving foot = planted
    lo = np.where(np.isfinite(lo), lo, 0.0)
    # a NaN height at a frame compares False -> that (foot, frame) counts as not-stance
    if ground is not None:
        tol = float(contact_tol) if contact_tol is not None else float(stance_frac) * rng
        stance = (H - float(ground)) <= tol          # absolute proximity to the floor
    else:
        stance = (H - lo) <= float(stance_frac) * rng
    duty = stance.mean(0)
    n_contacts = stance.sum(1)
    return {"stance": stance, "duty_factor": duty,
            "n_contacts": n_contacts,
            "double_support": float((n_contacts >= 2).mean())}
