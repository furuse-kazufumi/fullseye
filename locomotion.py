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
- Kajita, Kanehiro, Kaneko, Yokoi & Hirukawa, "The 3D linear inverted pendulum mode",
  IROS 2001 (LIPM); Pratt, Carff, Drakunov & Goswami, "Capture point: a step toward
  humanoid push recovery", Humanoids 2006; Koolen, de Boer, Rebula, Goswami & Pratt,
  "Capturability-based analysis and control of legged locomotion, Part 1", IJRR 2012
  (capture point / 0-step capturability).
- Dijkstra 1959 (footstep search over states); the friction-cone pyramid in the static
  force LP is the standard linearisation (e.g. Trinkle, Pang, Sudarsky & Lo 1997).

歩行の第 1 便(2026-11-06): 2 足支持の線分までの余裕・LIPM の捕捉点と踏み出さずに止まれる
余裕・足の軌跡からの一歩・立脚中の滑りと足で測る前進・足場の列・静的な接触力の線形計画。
台帳は opsdrive の ``locomotion``(地形側は ``walkterrain``)。

呼び出し例::

    import numpy as np
    import locomotion as L
    feet = np.array([[0.0, 0.1, 0.0], [0.0, -0.1, 0.0]])          # 2 足支持 = 線分
    assert L.com_support_margin([0.05, 0.0], feet) == -np.inf     # 面積が無い(値は変えない)
    assert abs(L.support_line_margin([0.05, 0.0], feet) + 0.05) < 1e-12
    xi = L.lipm_capture_point(np.array([0.0, 0.0, 0.8]), np.array([0.3, 0.0, 0.0]), 0.8)
    assert abs(xi[0] - 0.3 / np.sqrt(9.81 / 0.8)) < 1e-12
    plan = L.footstep_plan(np.ones((9, 20), bool), 0.1, ((5, 0), (3, 0)), 15, 0.3, 0.15, 0.25)
    assert plan["reached"] and [s["side"] for s in plan["steps"][:2]] == ["L", "R"]
    up = np.tile([0.0, 0.0, 1.0], (2, 1))
    f = L.static_contact_force_lp(feet, up, [0.0, 0.0, 0.8], 50.0, 0.8)
    assert f["feasible"] and np.allclose(f["normal"], 50 * 9.81 / 2)
"""
from __future__ import annotations

import numpy as np

__all__ = ["contact_points", "com_from_silhouette", "support_polygon",
           "com_support_margin", "gait_phase",
           # 歩行の第 1 便(2026-11-06)/ walking ops, first batch
           "support_line_margin", "lipm_capture_point", "capture_margin",
           "gait_step_events", "foot_slip_metrics", "footstep_plan",
           "static_contact_force_lp"]


def contact_points(points, plane, tol: float = 0.02):
    """Points lying within *tol* of a ground plane ``[a,b,c,d]`` = ground contacts.

    Given a cloud and the fitted ground plane (see :func:`pcseg.fit_plane_ransac`),
    returns ``(contacts (M,3), mask)`` — the feet/wheels/base actually touching the
    floor, the input to :func:`support_polygon`.

    空の入力(``points`` が 0 要素)は(0, 3) の点と空の maskを返す(理由: 点が無ければ接地点も無い。拒否すると逐次の処理が止まる)。"""
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
    empty mask.

    空の入力(``mask`` が 0 要素)は ``(nan, nan)`` を返す(理由: 画素の無いシルエットには重心が無く、0 で埋めると原点に人がいることになる)。"""
    m = np.asarray(mask) > 0.5
    if not m.any():
        return (float("nan"), float("nan"))
    ys, xs = np.nonzero(m)
    return (float(ys.mean()), float(xs.mean()))


def _ground_contact_mask(C, ground, tol):
    """Mask of the rows of ``C`` (N,3) touching *ground* within *tol*.

    *ground* is either a floor level ``z`` (scalar, as in :func:`gait_phase`) or a
    plane ``[a, b, c, d]`` (as in :func:`contact_points`). Airborne feet are
    dropped, never projected down onto the floor."""
    if C.shape[1] != 3:                             # no z to test -> cannot honour the
        raise ValueError("ground filtering needs (N, 3) contacts, got (N, 2)")  # gate
    g = np.asarray(ground, np.float64).ravel()
    if g.size == 1:                                 # floor level: |z - ground| <= tol
        dist = np.abs(C[:, 2] - g[0])
    elif g.size == 4:                               # plane: same rule as contact_points
        nrm = np.linalg.norm(g[:3])
        if nrm < 1e-12:
            raise ValueError("degenerate ground plane: normal has zero length")
        dist = np.abs(C @ g[:3] + g[3]) / nrm
    else:
        raise ValueError("ground must be a floor level z or a plane [a, b, c, d]")
    return dist <= float(tol)


def support_polygon(contacts, ground=None, contact_tol: float = 0.02) -> dict:
    """Convex support polygon of the ground-contact points (ground x, y plane).

    Returns ``{vertices (M,2 CCW), area, perimeter, centroid}``. With <3 distinct
    points it degenerates gracefully (a point or a segment, ``area = 0``). This is
    the base of support a static-stability check is measured against.
    空の入力(``contacts`` が 0 要素)は頂点 0 個・面積 0 の多角形を返す(理由: 足が 1 つも接地していない状態そのもの。重心は nan)。

    ★Precondition — only feet ACTUALLY TOUCHING the floor may take part: every
    contact is projected to (x, y), so a lifted foot out at some far x/y inflates
    the polygon and can make a tipping robot read as statically stable.

    * ``ground`` given (recommended for anti-cheat) — a floor level ``z`` or a
      plane ``[a, b, c, d]``; contacts further than ``contact_tol`` from it are
      filtered out here, so an airborne foot supports nothing.
    * ``ground=None`` (default, backward-compatible) — no z check at all; the
      caller MUST pre-filter with :func:`contact_points`."""
    C = np.asarray(contacts, np.float64)
    if C.ndim != 2 or C.shape[1] not in (2, 3):
        raise ValueError("contacts must be (N, 2) or (N, 3)")
    if ground is not None:                          # a foot in the air supports nothing
        C = C[_ground_contact_mask(C, ground, contact_tol)]
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


def com_support_margin(com_xy, contacts, ground=None, contact_tol: float = 0.02) -> float:
    """Static stability margin: signed distance from the COM ground-projection to
    the support-polygon boundary (McGhee & Frank 1968).

    ``com_xy`` is the COM projected onto the ground (x, y). Positive = the COM is
    **inside** the support polygon by that margin (statically stable, larger =
    safer); negative = outside (tipping). Returns the margin in world units
    (``-inf`` if the polygon is degenerate / has no area).

    ★``ground`` / ``contact_tol`` are forwarded to :func:`support_polygon` — pass
    them (floor level ``z`` or plane ``[a, b, c, d]``) so airborne feet are
    excluded. Without them the contacts are used as given and a lifted foot can
    turn a tipping robot into a "stable" one; pre-filter with
    :func:`contact_points` in that case.

    ★2 足支持(線分)と 1 足(点)では面積が無いので ``-inf`` を返す(この値は変えない ——
    変えると破壊的変更)。線分・点までの余裕が要るときは :func:`support_line_margin`。
    Two-foot (segment) and one-foot support return ``-inf`` by contract; use
    :func:`support_line_margin` for a finite margin there."""
    com = np.asarray(com_xy, np.float64).ravel()[:2]
    poly = support_polygon(contacts, ground=ground, contact_tol=contact_tol)
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


# =========================================================================== #
# 歩行の第 1 便(2026-11-06): 線分の余裕・LIPM の捕捉点・一歩の取り出し・足の滑り・
# 足場の列・静的な接触力。Walking ops, first batch (2026-11-06).
# =========================================================================== #
def _xy(v, name):
    """(2,) か (3,) の有限な点の (x, y)。A finite (2,) or (3,) point -> its (x, y)."""
    a = np.asarray(v, np.float64).ravel()
    if a.size not in (2, 3):
        raise ValueError("%s must be a ground point (x, y) or a world point (x, y, z), got %d values"
                         % (name, a.size))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s must be finite" % name)
    return a[:2].copy()


def _point_segment_distance(p, a, b):
    """点 p と閉じた線分 ab の距離(閉形式)。Distance from p to the closed segment ab."""
    e = b - a
    den = float(e @ e)
    if den < 1e-24:
        return float(np.linalg.norm(p - a))
    t = float(np.clip(((p - a) @ e) / den, 0.0, 1.0))
    return float(np.linalg.norm(p - (a + t * e)))


def support_line_margin(com, contacts, ground=None, contact_tol: float = 0.02) -> float:
    """Support margin that is defined for EVERY support set, including two-foot (segment) support.

    支持の形がどれでも値を持つ静的安定余裕。:func:`com_support_margin` は支持多角形に面積が
    無いとき(2 足支持 = 線分、1 足 = 点)``-inf`` を返す ―― 2 足で立つ人型の大半の時間が
    「測れない」になる穴がある。既存の値を変えると破壊的変更なので、この op を別に足した。

    * 面積のある多角形: :func:`com_support_margin` と同じ符号つき距離(+ = 内側)。
    * 線分(2 足、または一直線に並んだ足): COM の地面への射影から閉じた線分までの距離に
      **負号を付けた値**(``-dist``)。線分の上でちょうど 0、離れるほど負。線分には内側が
      無いので正にはならない(刃の上で釣り合うのが最良)。点と線分の距離は閉形式
      ``t = clip(((p-a)·(b-a))/|b-a|², 0, 1)``。
    * 点(1 足): ``-|p - foot|``。

    ``com`` は (x, y) か (x, y, z)(z は使わない)。``contacts`` は (N, 2) / (N, 3)。
    ``ground`` / ``contact_tol`` は :func:`support_polygon` に渡す(宙に浮いた足を外す)。
    単位は入力の世界単位。足が 1 つも無い(フィルタ後も含む)ときは ``ValueError``
    (支えが無いことを ``-inf`` で黙って返さない)。

    English: polygon with area -> the same signed distance as :func:`com_support_margin`;
    segment -> ``-distance`` to the closed segment (0 on it, never positive: a line has no
    interior); single foot -> ``-distance`` to that foot; no foot -> ``ValueError``.
    The first source of the segment rule is ``fullseye_shows/common/measure.py``
    (``support_line_margin``, same author).
    """
    c = _xy(com, "com")
    poly = support_polygon(contacts, ground=ground, contact_tol=contact_tol)
    V = np.asarray(poly["vertices"], np.float64)
    if V.shape[0] == 0:
        raise ValueError("no ground contact: a support margin needs at least one foot on the ground")
    if V.shape[0] >= 3 and poly["area"] > 0.0:
        return float(com_support_margin(c, V))
    # 線分・点は丸める前の座標で測る(support_polygon は重複を消すために頂点を 1e-9 に丸める。
    # その丸めで fullseye_shows の式と 7e-10 ずれていた —— 2026-11-08 に実物と突き合わせて直した)
    C = np.asarray(contacts, np.float64)
    if ground is not None:
        C = C[_ground_contact_mask(C, ground, contact_tol)]
    xy = C[:, :2]
    xy = xy[np.isfinite(xy).all(1)]
    if V.shape[0] == 1:
        return -float(np.linalg.norm(c - xy[0]))
    d = xy - xy.mean(0)
    axis = d[int(np.argmax(np.linalg.norm(d, axis=1)))]
    t = d @ axis
    i0, i1 = sorted((int(np.argmin(t)), int(np.argmax(t))))     # 端点は与えられた順(試作の a, b と同じ向き)
    return -_point_segment_distance(c, xy[i0], xy[i1])


def lipm_capture_point(com, com_vel, com_height, gravity: float = 9.81):
    """Instantaneous capture point of the linear inverted pendulum, ``xi = c + c_dot / omega``.

    線形倒立振子(LIPM)の捕捉点 ξ = c + ċ/ω、ω = √(g / z_c)(Kajita ほか 2001、
    Pratt ほか 2006、Koolen ほか 2012)。足圧中心 p を ξ に置けば重心は p の真上で止まり、
    p が ξ から離れていると ξ は ``ξ̇ = ω (ξ - p)`` で指数的に離れていく。

    * ``com`` / ``com_vel``: 重心の位置と速度。(3,) か (T, 3) の世界座標 [m]、[m/s]
      (x, y が地面、z が上)。(2,) / (T, 2) の地面の点でもよい。形は 2 つで揃える。
    * ``com_height``: LIPM の一定の重心高さ z_c [m] (地面から)。正の有限値。既定値は置かない
      (ロボットごとに違い、間違うと ω が √ で狂う)。
    * ``gravity``: 重力加速度 [m/s²]。
    * 返り値: ``com`` と同じ形。x, y が捕捉点、3 列のときの z は ``com_z - com_height``
      (振子の支点 = 地面の高さ)。

    照合: 解析解 ``x(t) = x0 cosh ωt + (v0/ω) sinh ωt`` から ``ξ(t) = (x0 + v0/ω) e^{ωt}``
    (tests/test_locomotion_ops_2026_11_06.py)。
    空の入力(``com`` が 0 要素)は ValueError で拒否する。

    English: xi = c + c_dot / omega with omega = sqrt(g / z_c); same shape as ``com``; for
    3-column input the z of the result is the pendulum pivot height ``com_z - com_height``.
    The source of the law is onocollo ``scripts/evis_video/capture_point_train.py``
    (Apache-2.0, same author); this is a fresh numpy implementation.
    """
    C = np.asarray(com, np.float64)
    Vv = np.asarray(com_vel, np.float64)
    if C.size == 0:
        raise ValueError("com is empty: a capture point needs a centre of mass")
    if C.shape != Vv.shape:
        raise ValueError("com and com_vel must have the same shape, got %s and %s" % (C.shape, Vv.shape))
    if C.ndim not in (1, 2) or C.shape[-1] not in (2, 3):
        raise ValueError("com must be (2,), (3,), (T, 2) or (T, 3), got %s" % (C.shape,))
    if not (np.all(np.isfinite(C)) and np.all(np.isfinite(Vv))):
        raise ValueError("com and com_vel must be finite")
    zc = float(com_height)
    g = float(gravity)
    if not (np.isfinite(zc) and zc > 0.0):
        raise ValueError("com_height must be a positive finite height in metres, got %r" % (com_height,))
    if not (np.isfinite(g) and g > 0.0):
        raise ValueError("gravity must be a positive finite acceleration, got %r" % (gravity,))
    omega = np.sqrt(g / zc)
    out = C.copy()
    out[..., :2] = C[..., :2] + Vv[..., :2] / omega
    if C.shape[-1] == 3:
        out[..., 2] = C[..., 2] - zc
    return out


def capture_margin(com, com_vel, com_height, contacts, gravity: float = 9.81,
                   ground=None, contact_tol: float = 0.02) -> float:
    """Signed distance of the LIPM capture point to the support set (0-step capturability).

    捕捉点 ξ(:func:`lipm_capture_point`)の、支持の形(:func:`support_line_margin` と同じ規則)
    までの符号つき余裕。正 = ξ が支持多角形の内側で、**踏み出さずに止まれる**(足圧中心を ξ に
    置ける。Koolen ほか 2012 の 0 歩捕捉可能)。負 = どこに足圧中心を置いても重心は止まらない
    ので、踏み出すか倒れる。静的な :func:`com_support_margin` は速度を見ないので、前へ
    走っている重心を「安定」と読む ―― この op はそれを負にする。

    ``com`` / ``com_vel`` は 1 時刻の (3,) か (2,)。``com_height`` [m] は正の有限値。
    足が 1 つも無いときは ``ValueError``。空の入力(``com`` が 0 要素)も ValueError で拒否する。

    English: positive = the capture point lies inside the support polygon, so the robot can
    stop without stepping (0-step capturable); negative = it must step. Segment / single-foot
    support follows :func:`support_line_margin` (never positive).
    """
    c = np.asarray(com, np.float64).ravel()
    v = np.asarray(com_vel, np.float64).ravel()
    if c.size == 0:
        raise ValueError("com is empty: a capture margin needs a centre of mass")
    if c.size not in (2, 3) or v.size != c.size:
        raise ValueError("com and com_vel must both be one (2,) or (3,) point")
    xi = lipm_capture_point(c, v, com_height, gravity=gravity)
    return support_line_margin(xi[:2], contacts, ground=ground, contact_tol=contact_tol)


def _feet_xyz(foot_xyz, name="foot_xyz"):
    """(T, F, 3) の足の軌跡を検査する。Validate a (T, F, 3) foot trajectory."""
    P = np.asarray(foot_xyz, np.float64)
    if P.ndim == 2 and P.shape[1] == 3:
        P = P[:, None, :]                              # 1 本の足 (T, 3) -> (T, 1, 3)
    if P.ndim != 3 or P.shape[2] != 3:
        raise ValueError("%s must be (T, F, 3) world xyz per frame and foot, got %s" % (name, P.shape))
    if P.shape[0] < 2:
        raise ValueError("%s needs at least 2 frames" % name)
    if not np.all(np.isfinite(P)):
        raise ValueError("%s must be finite (fill or drop occluded frames first)" % name)
    return P


def gait_step_events(foot_xyz, dt, plant_z, swing_z, min_swing_s: float = 0.1,
                     min_stance_s: float = 0.1, clearance_min: float = 0.02,
                     advance_min: float = 0.05) -> dict:
    """Extract walking steps (liftoff -> swing -> touchdown) from foot trajectories, with hysteresis.

    足の軌跡から「一歩」を取り出す。足の高さにヒステリシスを掛けて着地 / 遊脚を決め
    (``z < plant_z`` で着地、``z > swing_z`` で遊脚、その間は直前の状態を保つ = 接地の
    ばたつきを一歩に数えない)、離地 → 遊脚 → 着地の 1 周期のうち次をすべて満たすものだけを
    一歩と認める:

    * 遊脚の長さ ≥ ``min_swing_s`` [s]、着地後の立脚 ≥ ``min_stance_s`` [s] (最後の一歩は
      記録の終わりまで立脚していれば足りる)
    * 遊脚中の足の最高点 − 直前の立脚の始まりの高さ ≥ ``clearance_min`` [m] (すり足を落とす)
    * 着地点の水平の前進(直前の立脚の始まり = 前の足場から着地点への変位の、進行方向への
      成分)≥ ``advance_min`` [m] (引きずりを落とす)。ヒステリシスの帯の中ではまだ「着地」と
      読むので、離地のコマの位置から測ると遊脚の出だしの分だけ短く出る —— だから前の足場から
      測る。進行方向は全足の最初と最後の位置の平均の差(動いていなければ +x)。

    ``foot_xyz`` は (T, F, 3) の世界座標 [m] (z が上)、``dt`` はコマの間隔 [s]。
    ``plant_z`` < ``swing_z`` は地面からの高さの閾値 [m] (既定値を置かない: 足の形・
    センサで違う)。
    返り値 ``{"steps": [{foot, liftoff, touchdown, t_touchdown, xy, advance, clearance,
    swing_s}], "per_foot": [n_steps …], "rejected": [{foot, touchdown, reason}],
    "alternating": bool, "direction": (2,)}``。``steps`` は着地のコマ順。``alternating`` は
    足が 2 本以上で、続く一歩がいつも別の足のとき True。

    ★同じコマで 2 本以上の足が着地したら ``ValueError`` で拒否する: 両足の同時着地は歩行の
    一歩ではなく(跳躍・両足着地)、交互かどうかの順序も決まらない(onocollo の
    ``alternation_ok`` が min_sep で落としていた穴を、ここでは入口で止める)。
    空の入力(``foot_xyz`` が 0 要素)は ValueError で拒否する。

    English: hysteresis step detector (plant below ``plant_z``, swing above ``swing_z``);
    a step needs enough swing time, stance dwell, clearance and forward advance. Two feet
    touching down in the same frame raise ``ValueError``. Adapted from onocollo
    ``evolve/musculo.py`` ``detect_steps`` / ``alternation_ok`` (Apache-2.0, same author).
    """
    P = _feet_xyz(foot_xyz)
    T, F, _ = P.shape
    dt = float(dt)
    pz, sz = float(plant_z), float(swing_z)
    if not (np.isfinite(dt) and dt > 0.0):
        raise ValueError("dt must be a positive finite frame interval in seconds")
    if not (np.isfinite(pz) and np.isfinite(sz) and pz < sz):
        raise ValueError("plant_z must be finite and below swing_z (hysteresis band)")
    for nm, v in (("min_swing_s", min_swing_s), ("min_stance_s", min_stance_s),
                  ("clearance_min", clearance_min), ("advance_min", advance_min)):
        if not np.isfinite(float(v)) or float(v) < 0.0:
            raise ValueError("%s must be a non-negative finite number" % nm)
    d = (P[-1, :, :2] - P[0, :, :2]).mean(0)
    nd = float(np.linalg.norm(d))
    direction = d / nd if nd > 1e-9 else np.array([1.0, 0.0])
    planted = np.zeros((T, F), bool)
    for f in range(F):
        state = bool(P[0, f, 2] < sz)
        for i in range(T):
            z = P[i, f, 2]
            if z < pz:
                state = True
            elif z > sz:
                state = False
            planted[i, f] = state
    cand, rejected = [], []
    for f in range(F):
        i = 1
        s0 = 0                                                   # いまの立脚の始まり
        while i < T:
            if planted[i, f] and not planted[i - 1, f]:
                s0 = i
            if planted[i - 1, f] and not planted[i, f]:          # 離地 / liftoff
                lo = s0
                j = i
                while j < T and not planted[j, f]:
                    j += 1
                if j >= T:
                    break                                         # 着地しないまま終わった
                k = j
                while k < T and planted[k, f]:
                    k += 1
                swing_s = (j - i) * dt
                stance_s = (k - j) * dt
                clearance = float(P[i:j, f, 2].max() - P[lo, f, 2])
                advance = float((P[j, f, :2] - P[lo, f, :2]) @ direction)
                reason = None
                if swing_s < float(min_swing_s):
                    reason = "short_swing"
                elif stance_s < float(min_stance_s) and k < T:
                    reason = "short_stance"
                elif clearance < float(clearance_min):
                    reason = "no_clearance"
                elif advance < float(advance_min):
                    reason = "no_advance"
                rec = {"foot": f, "liftoff": lo, "touchdown": j, "t_touchdown": j * dt,
                       "xy": P[j, f, :2].copy(), "advance": advance, "clearance": clearance,
                       "swing_s": swing_s}
                if reason is None:
                    cand.append(rec)
                else:
                    rejected.append({"foot": f, "touchdown": j, "reason": reason})
                s0 = j
                i = j
            i += 1
    td = {}
    for s in cand:
        td.setdefault(s["touchdown"], []).append(s["foot"])
    clash = sorted(k for k, v in td.items() if len(v) > 1)
    if clash:
        raise ValueError("feet %s touched down in the same frame %d: a synchronous landing is not a "
                         "walking step and its order cannot be decided" % (td[clash[0]], clash[0]))
    steps = sorted(cand, key=lambda s: s["touchdown"])
    alternating = bool(F >= 2 and len(steps) >= 2
                       and all(a["foot"] != b["foot"] for a, b in zip(steps, steps[1:])))
    return {"steps": steps, "per_foot": [sum(1 for s in steps if s["foot"] == f) for f in range(F)],
            "rejected": rejected, "alternating": alternating, "direction": direction}


def foot_slip_metrics(foot_xyz, stance, body_xyz, max_slip: float = 0.02,
                      min_advance_ratio: float = 0.5) -> dict:
    """Horizontal foot slip during stance, foot-measured progression, and a 'body-only' gate.

    立脚中の足の水平の滑りと、足で測った前進。

    * 滑り: 立脚の区間(``stance`` が続けて True のコマ)ごとに、足の水平位置が区間の最初の
      位置から離れた最大の距離 [m] (``slip``)。全区間の最大が ``max_slip_observed``。
    * 足で測る前進: 足ごとに、続く 2 つの立脚の区間の最初の位置の差を進行方向に射影して
      足し、足の平均を取る(``foot_advance`` [m])。足を置き直さない限り増えない。
    * 胴の前進: ``body_xyz`` の最初と最後の水平の差の大きさ(``body_advance``)。進行方向は
      その向き(胴が動かなければ足の平均の向き、それも無ければ +x)。
    * 門 ``walking_ok``: ``max_slip_observed ≤ max_slip`` かつ
      ``foot_advance ≥ min_advance_ratio × body_advance``。胴だけが進み、足が置き直されない
      (滑っている・引きずられている・足が地面に描かれているだけ)見せかけの歩行を落とす。
      ``advance_ratio`` = ``foot_advance / body_advance``(胴が動かなければ ``None``)。

    ``foot_xyz`` (T, F, 3) [m]、``stance`` (T, F) bool(:func:`gait_phase` の ``stance``)、
    ``body_xyz`` (T, 3) [m]。空の入力(``foot_xyz`` が 0 要素)は ValueError で拒否する。

    English: per stance interval the slip is the largest horizontal excursion of the foot from
    where it touched down; progression measured by the feet is the sum of stance-to-stance
    displacements along the direction of travel. ``walking_ok`` fails a scene in which only
    the body advances.
    """
    P = _feet_xyz(foot_xyz)
    T, F, _ = P.shape
    S = np.asarray(stance)
    if S.shape != (T, F):
        raise ValueError("stance must be (T, F) = %s, got %s" % ((T, F), S.shape))
    S = S.astype(bool)
    B = np.asarray(body_xyz, np.float64)
    if B.ndim != 2 or B.shape[0] != T or B.shape[1] not in (2, 3):
        raise ValueError("body_xyz must be (T, 3) or (T, 2) with the same T as foot_xyz")
    if not np.all(np.isfinite(B)):
        raise ValueError("body_xyz must be finite")
    if not (np.isfinite(float(max_slip)) and float(max_slip) >= 0.0):
        raise ValueError("max_slip must be a non-negative finite length")
    if not (np.isfinite(float(min_advance_ratio)) and float(min_advance_ratio) >= 0.0):
        raise ValueError("min_advance_ratio must be a non-negative finite number")
    bd = B[-1, :2] - B[0, :2]
    body_adv = float(np.linalg.norm(bd))
    if body_adv > 1e-9:
        direction = bd / body_adv
    else:
        fd = (P[-1, :, :2] - P[0, :, :2]).mean(0)
        nf = float(np.linalg.norm(fd))
        direction = fd / nf if nf > 1e-9 else np.array([1.0, 0.0])
    intervals, slips, per_foot_adv = [], [], []
    for f in range(F):
        starts = []
        i = 0
        while i < T:
            if S[i, f]:
                j = i
                while j < T and S[j, f]:
                    j += 1
                seg = P[i:j, f, :2]
                ex = np.linalg.norm(seg - seg[0], axis=1)
                s = float(ex.max())
                intervals.append({"foot": f, "start": i, "end": j - 1, "slip": s,
                                  "slip_speed": s / max((j - 1 - i), 1) if j - 1 > i else 0.0})
                slips.append(s)
                starts.append(seg[0])
                i = j
            else:
                i += 1
        adv = sum(float((b - a) @ direction) for a, b in zip(starts, starts[1:]))
        per_foot_adv.append(adv)
    foot_adv = float(np.mean(per_foot_adv)) if per_foot_adv else 0.0
    max_obs = float(max(slips)) if slips else 0.0
    ratio = (foot_adv / body_adv) if body_adv > 1e-9 else None
    ok = bool(slips) and max_obs <= float(max_slip) and \
        foot_adv >= float(min_advance_ratio) * body_adv
    return {"intervals": intervals, "max_slip_observed": max_obs,
            "foot_advance": foot_adv, "per_foot_advance": per_foot_adv,
            "body_advance": body_adv, "advance_ratio": ratio,
            "direction": direction, "walking_ok": ok}


def footstep_plan(mask, cell, start, goal_col, step_max, width_min, width_max,
                  deviation_weight: float = 0.1, extent=None) -> dict:
    """Alternating left/right footstep sequence over a foothold mask (exact shortest path).

    足場の候補の mask と、歩幅・歩隔の制約から、左右交互の着地点の列を出す。

    格子の約束は :func:`terrain.elevation_map` と同じ(行 i = y、列 j = x、セル辺 ``cell`` [m])。
    進行方向は +x(列が増える向き)、**左足は y が大きい側**(行が大きい)。

    * 状態 = (いま立っている足のセル, その足が左か右か, 反対の足がゴールを越えているか)。
      次の一歩は反対の足を、``mask`` が True のセル c に置く:
      歩幅 ``0 ≤ (x_c − x_stance) ≤ step_max`` [m]、歩隔
      ``width_min ≤ (y_left − y_right) ≤ width_max`` [m] (左右が入れ替わる交差を許さない)。
    * 一歩の費用 = ``1 + deviation_weight·[((x_c − x_s − step_max)/step_max)² +
      ((w − w_mid)/w_half)²]``(``w_mid``・``w_half`` は歩隔の幅の中央と半幅、
      半幅が 0 のときは 2 項目を 0)。第 1 項 1 が歩数を数え、残りは最大の歩幅・中央の
      歩隔へ寄せる(平地では規則的に交互に並ぶ)。
    * ゴール = 最後の 2 歩(左右 1 歩ずつ)の両方が列 ``goal_col`` 以上。
    * 解法: 状態の上の Dijkstra(費用は非負)= 厳密な最小費用。小さな格子では総当たりの
      最小と一致する(tests の門)。

    ``start`` は ``((行, 列) の左足, (行, 列) の右足)``。どちらの足から踏み出すかも探索が
    決める。返り値 ``{"reached", "steps": [{"side": "L"/"R", "cell": (i, j), "xy"(extent が
    あるとき)}], "cost", "n_steps", "expanded"}``。届かないときは ``reached = False``・
    ``steps`` 空・``cost = inf``(``risk_aware_path`` と同じ約束)。

    ★``roverslip.risk_aware_path`` は再利用しなかった: あちらの状態は 1 セル、辺は 8 近傍の
    (8, H, W) の費用で、左右交互・歩幅の窓・歩隔の窓(反対の足との相対位置)を持てない。
    空の入力(``mask`` が 0 要素)は ValueError で拒否する。

    English: exact Dijkstra over (stance cell, side, other-foot-past-goal) states; a step puts
    the other foot on a True cell within the step-length window ``[0, step_max]`` and the
    step-width window ``[width_min, width_max]`` (left foot on the larger-y side). Unreachable
    goals return ``reached = False`` and ``cost = inf``.
    """
    import heapq
    M = np.asarray(mask)
    if M.size == 0:
        raise ValueError("mask is empty: no foothold candidates")
    if M.ndim != 2:
        raise ValueError("mask must be a 2-D (H, W) foothold mask")
    M = M.astype(bool)
    H, W = M.shape
    c = float(cell)
    if not (np.isfinite(c) and c > 0.0):
        raise ValueError("cell must be a positive finite cell size in metres")
    smax, wmin, wmax = float(step_max), float(width_min), float(width_max)
    if not (np.isfinite(smax) and smax > 0.0):
        raise ValueError("step_max must be a positive finite length")
    if not (np.isfinite(wmin) and np.isfinite(wmax) and 0.0 < wmin <= wmax):
        raise ValueError("step width window must satisfy 0 < width_min <= width_max")
    lam = float(deviation_weight)
    if not (np.isfinite(lam) and lam >= 0.0):
        raise ValueError("deviation_weight must be a non-negative finite number")
    try:
        (li, lj), (ri, rj) = start
        li, lj, ri, rj = int(li), int(lj), int(ri), int(rj)
    except (TypeError, ValueError):
        raise ValueError("start must be ((row, col) of the left foot, (row, col) of the right foot)") from None
    for (i, j) in ((li, lj), (ri, rj)):
        if not (0 <= i < H and 0 <= j < W):
            raise ValueError("start foot (%d, %d) is outside the mask" % (i, j))
    g = int(goal_col)
    w_mid, w_half = 0.5 * (wmin + wmax), 0.5 * (wmax - wmin)
    nmax = int(np.floor(smax / c + 1e-9))

    def step_cost(si, sj, ni, nj, side_new):
        dx = (nj - sj) * c
        wy = ((ni - si) if side_new == "L" else (si - ni)) * c
        dev = ((dx - smax) / smax) ** 2
        if w_half > 0.0:
            dev += ((wy - w_mid) / w_half) ** 2
        return 1.0 + lam * dev

    def moves(si, sj, side):
        new = "R" if side == "L" else "L"
        out = []
        for dj in range(0, nmax + 1):
            nj = sj + dj
            if nj >= W:
                break
            for ni in range(H):
                if not M[ni, nj]:
                    continue
                wy = ((ni - si) if new == "L" else (si - ni)) * c
                if wmin - 1e-9 <= wy <= wmax + 1e-9:
                    out.append((ni, nj, new))
        return out

    # 初期状態: どちらの足から踏み出してもよい(立っている足 = 踏み出さない側)
    dist, prev, heap = {}, {}, []
    for (si, sj, side, oi, oj) in ((li, lj, "L", ri, rj), (ri, rj, "R", li, lj)):
        st = (si, sj, side, oj >= g)
        dist[st] = 0.0
        prev[st] = None
        heapq.heappush(heap, (0.0, st))
    goal_state, expanded = None, 0
    while heap:
        dcur, st = heapq.heappop(heap)
        if dcur > dist.get(st, np.inf):
            continue
        expanded += 1
        si, sj, side, other_past = st
        if sj >= g and other_past:
            goal_state = st
            break
        for (ni, nj, new) in moves(si, sj, side):
            nst = (ni, nj, new, sj >= g)
            nd = dcur + step_cost(si, sj, ni, nj, new)
            if nd < dist.get(nst, np.inf) - 1e-12:
                dist[nst] = nd
                prev[nst] = st
                heapq.heappush(heap, (nd, nst))
    if goal_state is None:
        return {"reached": False, "steps": [], "cost": float("inf"), "n_steps": 0, "expanded": expanded}
    seq = []
    st = goal_state
    while prev[st] is not None:
        seq.append(st)
        st = prev[st]
    seq.reverse()
    steps = []
    for (i, j, side, _p) in seq:
        rec = {"side": side, "cell": (int(i), int(j))}
        if extent is not None:
            xmin, _xmax, ymin, _ymax = extent
            rec["xy"] = (xmin + (j + 0.5) * c, ymin + (i + 0.5) * c)
        steps.append(rec)
    return {"reached": True, "steps": steps, "cost": float(dist[goal_state]),
            "n_steps": len(steps), "expanded": expanded}


def static_contact_force_lp(contacts, normals, com, mass, mu, gravity: float = 9.81,
                            n_facets: int = 8) -> dict:
    """Static contact-force distribution under linearised friction cones (``scipy.optimize.linprog``).

    静的な接触力の配分。各接触 i の力を、摩擦錐を ``n_facets`` 角の多角錐で内側から近似した
    生成ベクトル ``g_ik = n_i + μ·t_ik``(t_ik は接平面の単位ベクトルを等角に回したもの)の
    非負結合 ``f_i = Σ_k λ_ik g_ik`` で表し、静的な釣り合い

        Σ f_i + m·g = 0,   Σ (p_i − c) × f_i = 0      (g = (0, 0, −gravity))

    を満たす λ ≥ 0 を線形計画で探す。目的は **法線力の最大値の最小化**(荷重を均す)に、
    接線力の L1 和を 1e-3 の重みで足したもの(足どうしで押し合う内力 = 解の不定さを消す)。

    * 多角錐は錐の内側(頂点が錐面の上)なので、ここで実行可能なら真の摩擦錐でも実行可能。
      逆は ``n_facets`` が小さいと成り立たない(縁の近くは保守的)。
    * 平地(法線がすべて +z)では、μ > 0 なら「解がある ⇔ COM の地面への射影が支持多角形の
      内側」(接線力は z = 0 の点で水平な軸のまわりのモーメントを作れない)。
      :func:`com_support_margin` と突き合わせる門が tests にある。
    * ``contacts`` (N, 3) [m]、``normals`` (N, 3)(正規化する。外向き = 地面から足へ)、
      ``com`` (3,) [m]、``mass`` [kg] > 0、``mu`` ≥ 0(0 なら摩擦なし = 法線だけ)。
    * 返り値 ``{"feasible", "forces" (N, 3) [N] か None, "normal" (N,), "tangential" (N,),
      "max_normal", "residual"(釣り合いの残差 [N]、[N·m]), "status", "message"}``。
      解が無ければ ``feasible = False``、力は ``None``。

    空の入力(``contacts`` が 0 要素)は ValueError で拒否する。

    English: friction cones are replaced by inscribed ``n_facets``-sided pyramids, so a
    feasible answer here is feasible for the true cone. The LP minimises the largest normal
    force plus 1e-3 x the L1 tangential force. On flat ground with mu > 0, feasibility is
    equivalent to the COM projection lying inside the support polygon.
    """
    from scipy.optimize import linprog
    Pc = np.asarray(contacts, np.float64)
    if Pc.size == 0:
        raise ValueError("contacts is empty: no contact can carry the weight")
    if Pc.ndim != 2 or Pc.shape[1] != 3:
        raise ValueError("contacts must be (N, 3)")
    Nn = np.asarray(normals, np.float64)
    if Nn.shape != Pc.shape:
        raise ValueError("normals must have the same shape as contacts, got %s" % (Nn.shape,))
    c = np.asarray(com, np.float64).ravel()
    if c.size != 3:
        raise ValueError("com must be a world point (x, y, z)")
    if not (np.all(np.isfinite(Pc)) and np.all(np.isfinite(Nn)) and np.all(np.isfinite(c))):
        raise ValueError("contacts, normals and com must be finite")
    m, mu_, g = float(mass), float(mu), float(gravity)
    if not (np.isfinite(m) and m > 0.0):
        raise ValueError("mass must be a positive finite mass in kg")
    if not (np.isfinite(mu_) and mu_ >= 0.0):
        raise ValueError("mu must be a non-negative finite friction coefficient")
    if not (np.isfinite(g) and g > 0.0):
        raise ValueError("gravity must be a positive finite acceleration")
    K = int(n_facets)
    if K < 3:
        raise ValueError("n_facets must be >= 3 (a pyramid needs at least 3 sides)")
    nl = np.linalg.norm(Nn, axis=1)
    if np.any(nl < 1e-12):
        raise ValueError("every contact normal must be non-zero")
    Nn = Nn / nl[:, None]
    N = Pc.shape[0]
    gens = np.zeros((N, K, 3))
    for i in range(N):
        n = Nn[i]
        a = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        t1 = a - (a @ n) * n
        t1 /= np.linalg.norm(t1)
        t2 = np.cross(n, t1)
        for k in range(K):
            th = 2.0 * np.pi * k / K
            gens[i, k] = n + mu_ * (np.cos(th) * t1 + np.sin(th) * t2)
    # 変数: λ (N*K), t (1), u (N*3 の接線の絶対値の上界)
    nl_ = N * K
    nv = nl_ + 1 + 3 * N
    A_eq = np.zeros((6, nv))
    G = gens.reshape(nl_, 3)
    arm = np.repeat(Pc - c, K, axis=0)
    A_eq[0:3, :nl_] = G.T
    A_eq[3:6, :nl_] = np.cross(arm, G).T
    b_eq = np.concatenate([[0.0, 0.0, m * g], [0.0, 0.0, 0.0]])
    rows, rhs = [], []
    for i in range(N):                                 # 法線力 ≤ t
        r = np.zeros(nv)
        r[i * K:(i + 1) * K] = gens[i] @ Nn[i]
        r[nl_] = -1.0
        rows.append(r)
        rhs.append(0.0)
        P = np.eye(3) - np.outer(Nn[i], Nn[i])         # 接線成分 = (I − n nᵀ) f
        for ax in range(3):
            for sgn in (1.0, -1.0):
                r = np.zeros(nv)
                r[i * K:(i + 1) * K] = sgn * (gens[i] @ P)[:, ax]
                r[nl_ + 1 + 3 * i + ax] = -1.0
                rows.append(r)
                rhs.append(0.0)
    cost = np.zeros(nv)
    cost[nl_] = 1.0
    cost[nl_ + 1:] = 1e-3
    res = linprog(cost, A_ub=np.asarray(rows), b_ub=np.asarray(rhs), A_eq=A_eq, b_eq=b_eq,
                  bounds=[(0, None)] * nv, method="highs")
    if res.status != 0:
        return {"feasible": False, "forces": None, "normal": None, "tangential": None,
                "max_normal": None, "residual": None, "status": int(res.status),
                "message": str(res.message)}
    lam = res.x[:nl_].reshape(N, K)
    F = np.einsum("ik,ikj->ij", lam, gens)
    normal = np.einsum("ij,ij->i", F, Nn)
    tang = np.linalg.norm(F - normal[:, None] * Nn, axis=1)
    resid_f = float(np.linalg.norm(F.sum(0) + np.array([0.0, 0.0, -m * g])))
    resid_m = float(np.linalg.norm(np.cross(Pc - c, F).sum(0)))
    return {"feasible": True, "forces": F, "normal": normal, "tangential": tang,
            "max_normal": float(normal.max()), "residual": (resid_f, resid_m),
            "status": 0, "message": str(res.message)}
