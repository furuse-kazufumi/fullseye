"""6-DoF surface matching by Point Pair Features (numpy + scipy).

The step that lets a robot answer "*where is this known object?*": given a CAD /
reference point cloud (the model) and a scene cloud from :mod:`stereo` /
:mod:`camera`, recover the rigid pose ``(R, t)`` that places the model into the
scene — the 6-DoF pose a manipulator needs before it plans a grasp. Global,
initialisation-free matching by the Point Pair Feature voting scheme, refined with
the local ICP in :mod:`registration`.

The complement to :mod:`registration`: ICP needs a rough initial pose and finds
the *nearest* alignment, whereas this votes over the whole model to find the pose
from scratch (then hands off to ICP for the fine fit).

Frame convention: clouds are (N, 3) in metric units; normals are unit (N, 3).
``(R, t)`` maps the model into the scene: ``scene ~ model @ R.T + t``.

Reference (public literature — reimplemented, not derived from any product):
Drost, Ulrich, Navab & Ilic, "Model Globally, Match Locally: Efficient and Robust
3D Object Recognition", CVPR 2010 (Point Pair Features + Hough-style voting).
"""
from __future__ import annotations

import numpy as np

__all__ = ["ppf_model", "surface_match", "find_surface_pose"]


def _unit(v, axis=-1):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-12)


def _rot_align(a, b):
    """Rotation matrix taking unit vector ``a`` onto unit vector ``b``."""
    a = _unit(np.asarray(a, np.float64))
    b = _unit(np.asarray(b, np.float64))
    v = np.cross(a, b)
    c = float(a @ b)
    s = np.linalg.norm(v)
    if s < 1e-12:
        if c > 0:
            return np.eye(3)                        # a == b
        # a == -b: a proper 180 deg rotation about ANY axis perpendicular to a maps
        # a onto b. (diag([1,-1,-1]) only works when a is along +x — it left a normal
        # of -x pointing at -x, so _align_to_x mis-aligned it.)
        p = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        p = p - (p @ a) * a
        p = p / np.linalg.norm(p)
        return 2.0 * np.outer(p, p) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1.0 - c) / (s * s))


def _align_to_x(p, n):
    """4x4 transform sending point ``p`` to the origin and normal ``n`` to +x."""
    R = _rot_align(n, np.array([1.0, 0.0, 0.0]))
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = -R @ np.asarray(p, np.float64)
    return T


def _alpha_of(pg):
    """Angle about +x that rotates transformed point(s) ``pg`` into the y>=0 plane."""
    return np.arctan2(-pg[..., 2], pg[..., 1])


def _rot_x(a):
    ca, sa = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])


def _angle(u, v):
    """Unsigned angle in [0, pi] between rows of u and v (both (..,3))."""
    d = np.clip((u * v).sum(-1), -1.0, 1.0)
    return np.arccos(d)


def _invariant_diameter(P) -> float:
    """点群の直径。**回転で変わらない**量として測る。

    2026-09-06 まで、既定の ``dist_step`` は**軸平行境界箱の対角 / 20** だった。
    その対角は向きで変わる —— 同じ 800 点の箱を z 軸まわりに回すと 1.2333
    (0 度、90 度)と 1.5735(143 度)で **28 % 動く**。``dist_step`` は距離を
    量子化する幅なので、動けばハッシュ鍵が変わる。実測でモデルと場面の鍵の
    一致率が 58 % まで落ちた。PPF は「モデルを 1 度作って多くの場面に使い回す」
    設計なので、**別の向きで撮った場面だけ当たらない**という、再現しにくい
    壊れ方になる。

    ここでは凸包の頂点どうしの最大距離(= 真の直径)を返す。上の箱では回転角に
    依らず 1.1784 で一定。50000 点でも凸包の頂点は 174 個しかなく **7.1 ms**。

    凸包が作れない配置(同一平面・同一直線・4 点未満)では ``2 * max|p - c|`` に
    落とす。**こちらも回転不変**なので、落ちても今回の不具合は戻らない
    (値は 1-5 % 大きめに出る。球殻で 2.0927 対 2.0000)。
    """
    P = np.asarray(P, np.float64)
    if P.shape[0] < 2:
        return 0.0
    try:
        from scipy.spatial import ConvexHull
        h = P[ConvexHull(P).vertices]
        return float(np.linalg.norm(h[:, None, :] - h[None, :, :], axis=-1).max())
    except Exception:                            # noqa: BLE001 — 退化配置
        c = P.mean(0)
        return float(2.0 * np.linalg.norm(P - c, axis=1).max())


def ppf_model(points, normals=None, dist_step: float = None, angle_bins: int = 30,
              k_normals: int = 16) -> dict:
    """Build the Point Pair Feature descriptor (hash table) of a model cloud.

    Precomputes, for every ordered pair of model points, the 4-D feature
    ``F = (||d||, ang(n1,d), ang(n2,d), ang(n1,n2))`` discretised into a hash key,
    and the aligning angle ``alpha`` — the model half of Drost 2010. Reuse the
    returned descriptor across many scenes (build once, match many). ``dist_step``
    defaults to 1/20 of the model diameter; ``angle_bins`` sets the angular
    resolution. If *normals* is None they are estimated."""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    M = P.shape[0]
    if M < 5:
        raise ValueError("need >= 5 model points")
    if normals is None:
        # ★ 素の PCA 法線は**符号が任意**で、回転すると 4 割の点で裏返る。PPF の
        #   特徴は法線どうしの角度なので、裏返れば鍵が変わる。実測(400 点、
        #   z 軸まわり): 素の法線だと鍵の一致率が 0/37/90/143 度で
        #   100 / 73.6 / 69.4 / 67.2 %、向き付き法線なら **すべて 100 %**。
        #   ``pointcloud.fpfh`` が踏んでいたのと同じ穴で、同じ日に一緒に直した。
        from normals_orient import estimate_oriented_normals
        N = estimate_oriented_normals(P, k=k_normals)
    else:
        N = _unit(np.asarray(normals, np.float64))
    diam = _invariant_diameter(P)
    if dist_step is None:
        dist_step = diam / 20.0 if diam > 0 else 1.0
    astep = np.pi / int(angle_bins)
    table: dict = {}
    for i in range(M):
        d = P - P[i]                                   # (M,3) vectors to all others
        dn = np.linalg.norm(d, axis=1)
        du = _unit(d)
        f1 = dn
        f2 = _angle(np.broadcast_to(N[i], du.shape), du)
        f3 = _angle(N, du)
        f4 = _angle(np.broadcast_to(N[i], N.shape), N)
        qd = np.floor(f1 / dist_step).astype(np.int64)
        q2 = np.floor(f2 / astep).astype(np.int64)
        q3 = np.floor(f3 / astep).astype(np.int64)
        q4 = np.floor(f4 / astep).astype(np.int64)
        Ti = _align_to_x(P[i], N[i])
        pg = (P @ Ti[:3, :3].T) + Ti[:3, 3]            # all points in i's local frame
        alpha_m = _alpha_of(pg)
        for j in range(M):
            if j == i or dn[j] < 1e-9:
                continue
            key = (int(qd[j]), int(q2[j]), int(q3[j]), int(q4[j]))
            table.setdefault(key, []).append((i, float(alpha_m[j])))
    return {"points": P, "normals": N, "table": table,
            "dist_step": float(dist_step), "angle_bins": int(angle_bins)}


def _pose_from(sr_p, sr_n, model, mi, alpha):
    """Rigid transform (R, t) mapping the model into the scene for a matched
    reference pair (scene ref sr, model point mi) and aligning angle ``alpha``."""
    Ts = _align_to_x(sr_p, sr_n)
    Tm = _align_to_x(model["points"][mi], model["normals"][mi])
    Rx = np.eye(4)
    Rx[:3, :3] = _rot_x(alpha)
    T = np.linalg.inv(Ts) @ Rx @ Tm                    # model -> scene
    return T[:3, :3], T[:3, 3]


def surface_match(model: dict, scene_points, scene_normals=None,
                  ref_fraction: float = 0.3, topk: int = 5, refine: bool = True,
                  k_normals: int = 16, seed: int = 0) -> dict:
    """Find the model's 6-DoF pose in a scene cloud by PPF voting + ICP refine.

    Votes each sampled scene reference point against the precomputed *model*
    descriptor (Drost 2010), takes the top-``topk`` pose hypotheses by vote count,
    refines each with :func:`registration.icp`, and returns the best.
    Returns ``{R, t, rmse, votes, inlier_fraction}`` where ``(R, t)`` maps the model
    into the scene. ``ref_fraction`` sets how many scene points seed a vote."""
    from registration import icp, apply_transform
    from scipy.spatial import cKDTree

    S = np.asarray(scene_points, np.float64)
    if S.ndim != 2 or S.shape[1] != 3:
        raise ValueError("scene_points must be (N, 3)")
    if scene_normals is None:
        from pointcloud import estimate_normals
        SN = estimate_normals(S, k=k_normals)
    else:
        SN = _unit(np.asarray(scene_normals, np.float64))
    ns = S.shape[0]
    M = model["points"].shape[0]
    dist_step = model["dist_step"]
    ab = model["angle_bins"]
    astep = np.pi / ab
    two_pi = 2.0 * np.pi
    rng = np.random.default_rng(seed)
    n_ref = max(1, int(round(ref_fraction * ns)))
    refs = rng.choice(ns, min(n_ref, ns), replace=False)

    hypotheses = []
    for r in refs:
        Ts = _align_to_x(S[r], SN[r])
        d = S - S[r]
        dn = np.linalg.norm(d, axis=1)
        du = _unit(d)
        f2 = _angle(np.broadcast_to(SN[r], du.shape), du)
        f3 = _angle(SN, du)
        f4 = _angle(np.broadcast_to(SN[r], SN.shape), SN)
        qd = np.floor(dn / dist_step).astype(np.int64)
        q2 = np.floor(f2 / astep).astype(np.int64)
        q3 = np.floor(f3 / astep).astype(np.int64)
        q4 = np.floor(f4 / astep).astype(np.int64)
        pg = (S @ Ts[:3, :3].T) + Ts[:3, 3]
        alpha_s = _alpha_of(pg)
        acc = np.zeros((M, ab))
        for j in range(ns):
            if j == r or dn[j] < 1e-9:
                continue
            hits = model["table"].get((int(qd[j]), int(q2[j]), int(q3[j]), int(q4[j])))
            if not hits:
                continue
            for mi, alpha_m in hits:
                # T = Ts^-1 . Rx(alpha) . Tm maps model -> scene, and Rx(alpha_m) pg_m
                # and Rx(alpha_s) pg_s both land in the y>=0 half-plane, so
                # pg_s = Rx(alpha_m - alpha_s) pg_m: vote for alpha_m - alpha_s.
                # (The reversed difference put the sign of the rotation about the
                # normal backwards: Rerr 27-169 deg on random poses, 2026-09-02.)
                b = int(round(((alpha_m - alpha_s[j]) % two_pi) / (two_pi / ab))) % ab
                acc[mi, b] += 1.0
        if acc.max() <= 0:
            continue
        mi_star, b_star = np.unravel_index(int(acc.argmax()), acc.shape)
        alpha = b_star * (two_pi / ab)
        R, t = _pose_from(S[r], SN[r], model, int(mi_star), alpha)
        hypotheses.append((float(acc.max()), R, t))

    if not hypotheses:
        return {"R": np.eye(3), "t": np.zeros(3), "rmse": float("inf"),
                "votes": 0.0, "inlier_fraction": 0.0}

    hypotheses.sort(key=lambda h: -h[0])
    tree = cKDTree(S)
    tol = 2.0 * dist_step
    best = None
    for votes, R0, t0 in hypotheses[:max(1, int(topk))]:
        if refine:
            R, t, _aln, rmse = icp(model["points"], S, init=(R0, t0), trim=0.2)
        else:
            R, t, rmse = R0, t0, float("nan")
        moved = apply_transform(model["points"], R, t)
        dist, _ = tree.query(moved, k=1)
        inlier = float((dist <= tol).mean())
        score = (inlier, -(rmse if np.isfinite(rmse) else 1e9))
        if best is None or score > best[0]:
            best = (score, R, t, rmse, votes, inlier)
    _, R, t, rmse, votes, inlier = best
    return {"R": R, "t": t, "rmse": float(rmse), "votes": float(votes),
            "inlier_fraction": float(inlier)}


def find_surface_pose(model_points, scene_points, model_normals=None,
                      scene_normals=None, dist_step: float = None,
                      angle_bins: int = 30, k_normals: int = 16, **kw) -> dict:
    """One-shot convenience: build the model descriptor and match it against a scene.

    Equivalent to :func:`ppf_model` followed by :func:`surface_match`; use the
    two-step form when matching the same model into many scenes. Returns the same
    ``{R, t, rmse, votes, inlier_fraction}`` dict — the 6-DoF pose of the model in
    the scene, ready to drive a grasp."""
    model = ppf_model(model_points, model_normals, dist_step=dist_step,
                      angle_bins=angle_bins, k_normals=k_normals)
    return surface_match(model, scene_points, scene_normals, k_normals=k_normals, **kw)
