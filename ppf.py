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


_PAIR_BLOCK = 32768
_VOTE_BLOCK = 1000000


class _PPFTable:
    """Sorted PPF buckets without a Python hash map. / Python 辞書を使わない整列済み PPF バケット。"""

    __slots__ = ("keys", "offsets", "model_indices", "alphas")

    def __init__(self, keys, offsets, model_indices, alphas):
        self.keys = keys
        self.offsets = offsets
        self.model_indices = model_indices
        self.alphas = alphas

    def __len__(self):
        return len(self.keys)

    # dict だった頃の読み手(set(model["table"]) で鍵を集める回転不変の門、PoC)を壊さない。
    # Keep the mapping-like reads the old dict table supported (iteration = keys, membership).
    def __iter__(self):
        return iter(np.asarray(self.keys).tolist())

    def __contains__(self, key):
        keys = np.asarray(self.keys)
        i = int(np.searchsorted(keys, key))
        return i < len(keys) and keys[i] == key


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


def _quantized_keys(distance, angle_1, angle_2, angle_3, dist_step, angle_bins):
    """Pack quantized PPF rows into sortable integers. / 量子化 PPF 行を整列可能な整数へ詰める。"""
    astep = np.pi / angle_bins
    base = angle_bins + 1
    qd = np.floor(distance / dist_step).astype(np.int64)
    q1 = np.floor(angle_1 / astep).astype(np.int64)
    q2 = np.floor(angle_2 / astep).astype(np.int64)
    q3 = np.floor(angle_3 / astep).astype(np.int64)
    return ((qd * base + q1) * base + q2) * base + q3


def _pair_table(P, N, dist_step, angle_bins):
    """Vectorize ordered model pairs in bounded blocks. / モデル順序対を上限付きブロックでベクトル化する。"""
    count_max = P.shape[0] * (P.shape[0] - 1)
    keys = np.empty(count_max, dtype=np.int64)
    model_indices = np.empty(count_max, dtype=np.int32)
    alphas = np.empty(count_max, dtype=np.float64)
    write = 0
    total = P.shape[0] * P.shape[0]
    x_axis = np.array([1.0, 0.0, 0.0])
    for first in range(0, total, _PAIR_BLOCK):
        pair = np.arange(first, min(first + _PAIR_BLOCK, total), dtype=np.int64)
        i, j = pair // P.shape[0], pair % P.shape[0]
        keep = i != j
        i, j = i[keep], j[keep]
        d = P[j] - P[i]
        distance = np.linalg.norm(d, axis=1)
        keep = distance >= 1e-9
        if not np.any(keep):
            continue
        i, j, d, distance = i[keep], j[keep], d[keep], distance[keep]
        direction = d / distance[:, None]
        packed = _quantized_keys(
            distance,
            _angle(N[i], direction),
            _angle(N[j], direction),
            _angle(N[i], N[j]),
            dist_step,
            angle_bins,
        )
        refs, inverse = np.unique(i, return_inverse=True)
        rotations = np.stack([_rot_align(N[index], x_axis) for index in refs])
        rotations = rotations[inverse]
        translations = -np.einsum("nij,nj->ni", rotations, P[i])
        local = np.einsum("nij,nj->ni", rotations, P[j]) + translations
        alpha = _alpha_of(local)
        stop = write + len(i)
        keys[write:stop] = packed
        model_indices[write:stop] = i
        alphas[write:stop] = alpha
        write = stop
    keys = keys[:write]
    model_indices = model_indices[:write]
    alphas = alphas[:write]
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    model_indices = model_indices[order]
    alphas = alphas[order]
    unique_keys, starts = np.unique(keys, return_index=True)
    offsets = np.append(starts, len(keys)).astype(np.int64, copy=False)
    return _PPFTable(unique_keys, offsets, model_indices, alphas)


def _vote(table, scene_keys, scene_alphas, model_size, angle_bins):
    """Accumulate matching buckets with bounded bincount blocks. / 一致バケットを上限付き bincount で投票する。"""
    positions = np.searchsorted(table.keys, scene_keys)
    found = positions < len(table.keys)
    found[found] &= table.keys[positions[found]] == scene_keys[found]
    positions = positions[found]
    scene_alphas = scene_alphas[found]
    if positions.size == 0:
        return np.zeros((model_size, angle_bins), dtype=np.int64)
    starts = table.offsets[positions]
    counts = table.offsets[positions + 1] - starts
    accumulator = np.zeros(model_size * angle_bins, dtype=np.int64)
    cumulative = np.cumsum(counts, dtype=np.int64)
    cursor = 0
    two_pi = 2.0 * np.pi
    while cursor < len(counts):
        before = 0 if cursor == 0 else cumulative[cursor - 1]
        end = int(np.searchsorted(cumulative, before + _VOTE_BLOCK, side="right"))
        if end == cursor:
            # One exceptionally large model bucket. / モデル側の単一巨大バケット。
            for entry_first in range(int(starts[cursor]),
                                     int(starts[cursor] + counts[cursor]), _VOTE_BLOCK):
                entry_last = min(entry_first + _VOTE_BLOCK,
                                 int(starts[cursor] + counts[cursor]))
                model_rows = np.arange(entry_first, entry_last, dtype=np.int64)
                bins = np.rint(((table.alphas[model_rows] - scene_alphas[cursor]) % two_pi)
                               / (two_pi / angle_bins)).astype(np.int64) % angle_bins
                flat = table.model_indices[model_rows].astype(np.int64) * angle_bins + bins
                accumulator += np.bincount(flat, minlength=accumulator.size)
            cursor += 1
            continue
        block_counts = counts[cursor:end]
        repeated = np.repeat(np.arange(end - cursor), block_counts)
        block_offsets = np.repeat(np.cumsum(block_counts) - block_counts, block_counts)
        model_rows = starts[cursor:end][repeated] + np.arange(repeated.size) - block_offsets
        bins = np.rint(((table.alphas[model_rows] - scene_alphas[cursor:end][repeated]) % two_pi)
                       / (two_pi / angle_bins)).astype(np.int64) % angle_bins
        flat = table.model_indices[model_rows].astype(np.int64) * angle_bins + bins
        accumulator += np.bincount(flat, minlength=accumulator.size)
        cursor = end
    return accumulator.reshape(model_size, angle_bins)


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
    table = _pair_table(P, N, float(dist_step), int(angle_bins))
    return {"points": P, "normals": N, "table": table,
            "dist_step": float(dist_step), "angle_bins": int(angle_bins),
            "diameter": diam}


def _default_scene_normals(S, k_normals):
    """Scene normals when the caller passes none: the same oriented estimator
    as :func:`ppf_model` uses for the model (``estimate_oriented_normals``).

    ★2026-11-09 敵対的点検: 以前は場面側だけ素の ``pointcloud.estimate_normals``
    (符号が任意)だった。PPF の鍵は法線どうしの角度なので、場面とモデルで符号の
    決め方が違うと鍵が半分ずれる。実測(当て金 250/325 点・回転 30-180 度・48 試行):
    場面法線とモデル法線(真値で写したもの)の符号一致率 0.50 → 1.00、
    ``find_surface_pose`` の成功率(回転 < 5 度かつ重心 < 3 % 直径)54 % → 79〜83 %
    (探針と回帰テストで間引き関数が違う)。
    非有限の点は ``ValueError``(fail-closed、``estimate_oriented_normals`` と同じ)。"""
    from normals_orient import estimate_oriented_normals
    return estimate_oriented_normals(S, k=k_normals)


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
    into the scene. ``ref_fraction`` sets how many scene points seed a vote.
    If *scene_normals* is None they are estimated with the same oriented
    estimator as the model side (``normals_orient.estimate_oriented_normals``,
    ``k_normals`` neighbours) so that model and scene normals agree in sign;
    if you pass your own, orient them consistently with ``model["normals"]``
    (an arbitrary-sign PCA normal halves the key agreement).

    前提と限界(★2026-11-09 独立レビュー): 既定の場面法線は **場面の重心から外向き** に
    伝播して符号を決める。場面に床や他の物体が入ると、物体の法線が **物体ごと裏返る** ことが
    ある(片側視 + 床の場面で試行の 20 % が全体逆符号)。そのため既定の法線のときは
    **両方の符号で投票** し(各符号の上位 ``topk`` 仮説を ICP で詰める)、当てはまり
    (``inlier_fraction``、同点は ``rmse``)の良い方を返す。法線を自分で渡すと渡した
    符号だけを使う。

    両符号の代償(2026-11-09 実測): 時間は 1.84〜2.05 倍(投票と ICP がそれぞれ 2 回ぶん)。
    向きが正しい場面(当て金 325 点・全周)では、片符号で渡したときより成功率がわずかに
    下がる —— 種 7 本 × 48 試行の平均 0.842 → 0.827(種 7 では 0.83 → 0.79)。裏返った
    場面では片符号 0.33 → 両符号 0.7 以上。

    限界: **片側だけ見えた物体 + 床** の場面では、既定でも、カメラ位置で向けた法線
    (``estimate_normals(S, viewpoint=cam)``)を渡しても、成功はほぼ 0(30 試行で 1 回)。
    法線の向きではなく、片側視で点対特徴の表が合わないことが効いている。床は事前に
    ``remove_ground`` 等で除くこと。"""
    from registration import icp, apply_transform
    from scipy.spatial import cKDTree

    S = np.asarray(scene_points, np.float64)
    if S.ndim != 2 or S.shape[1] != 3:
        raise ValueError("scene_points must be (N, 3)")
    if scene_normals is None:
        SN = _default_scene_normals(S, k_normals)
        # ★2026-11-09 独立レビュー: 向き付き法線の符号は「場面の重心から外向き」に決まる。
        #   床や他の物体を含む場面では物体ごと裏返ることがある(片側視+床で試行の 20 % が
        #   物体全体の符号がモデルと逆)。既定の法線のときは両方の符号で投票し、ICP 後の
        #   当てはまりで選ぶ(符号を渡されたときは渡された向きを信じる)。
        sign_choices = (1.0, -1.0)
    else:
        SN = _unit(np.asarray(scene_normals, np.float64))
        sign_choices = (1.0,)
    ns = S.shape[0]
    M = model["points"].shape[0]
    dist_step = model["dist_step"]
    ab = model["angle_bins"]
    two_pi = 2.0 * np.pi
    rng = np.random.default_rng(seed)
    n_ref = max(1, int(round(ref_fraction * ns)))
    refs = rng.choice(ns, min(n_ref, ns), replace=False)

    tree = cKDTree(S)
    diameter = float(model.get("diameter", _invariant_diameter(model["points"])))
    hypotheses = []
    for sgn in sign_choices:
        hypotheses.extend(_vote_hypotheses(S, sgn * SN, refs, tree, diameter, model,
                                           dist_step, ab, M, two_pi, sgn))

    if not hypotheses:
        return {"R": np.eye(3), "t": np.zeros(3), "rmse": float("inf"),
                "votes": 0.0, "inlier_fraction": 0.0}

    hypotheses.sort(key=lambda h: -h[0])
    tol = 2.0 * dist_step
    best = None
    # 符号ごとに上位 topk を詰める(片方の符号の仮説だけで枠が埋まらないように)
    chosen = []
    for sgn in sign_choices:
        chosen.extend([h for h in hypotheses if h[3] == sgn][:max(1, int(topk))])
    for votes, R0, t0, _sgn in chosen:
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


def _vote_hypotheses(S, SN, refs, tree, diameter, model, dist_step, ab, M, two_pi, sgn):
    """PPF voting for every reference point; returns ``[(votes, R, t, sgn)]``."""
    hypotheses = []
    for r in refs:
        Ts = _align_to_x(S[r], SN[r])
        neighbours = np.asarray(tree.query_ball_point(S[r], r=diameter,
                                                      return_sorted=True), dtype=np.int64)
        neighbours = neighbours[neighbours != r]
        d = S[neighbours] - S[r]
        dn = np.linalg.norm(d, axis=1)
        keep = dn >= 1e-9
        neighbours, d, dn = neighbours[keep], d[keep], dn[keep]
        if neighbours.size == 0:
            continue
        du = d / dn[:, None]
        keys = _quantized_keys(
            dn,
            _angle(np.broadcast_to(SN[r], du.shape), du),
            _angle(SN[neighbours], du),
            _angle(np.broadcast_to(SN[r], (len(neighbours), 3)), SN[neighbours]),
            dist_step,
            ab,
        )
        pg = (S[neighbours] @ Ts[:3, :3].T) + Ts[:3, 3]
        alpha_s = _alpha_of(pg)
        acc = _vote(model["table"], keys, alpha_s, M, ab)
        if acc.max() <= 0:
            continue
        mi_star, b_star = np.unravel_index(int(acc.argmax()), acc.shape)
        alpha = b_star * (two_pi / ab)
        R, t = _pose_from(S[r], SN[r], model, int(mi_star), alpha)
        hypotheses.append((float(acc.max()), R, t, sgn))
    return hypotheses


def find_surface_pose(model_points, scene_points, model_normals=None,
                      scene_normals=None, dist_step: float = None,
                      angle_bins: int = 30, k_normals: int = 16, **kw) -> dict:
    """既知の物体(モデル点群)が場面の点群のどこにあるかを、点対特徴(PPF)の投票と ICP で求める(``pose``)。

    HALCON ``find_surface_model`` にあたる初期値の要らない 6-DoF 照合(Drost et al., CVPR 2010):
    :func:`ppf_model` でモデルの点対特徴を表にし、:func:`surface_match` で場面の参照点ごとに
    投票して上位の仮説を ICP で詰める。同じモデルを多くの場面へ当てるときは 2 段の形を使う。
    素の関数(``fullseye.find_surface_pose``)は ``{R, t, rmse, votes, inlier_fraction}`` の
    dict を返し、台帳 ``fullseye.ledger.find_surface_pose`` は ``pose`` の正典 ``(R, t)`` を返す
    (残りは ``.raw``)。``(R, t)`` はモデルを場面へ写す: ``scene ≈ model @ R.T + t``(点は
    (N, 3)、単位はそのまま)。法線を渡さなければ ``k_normals`` 近傍で向きつき法線を推定する。
    ``dist_step`` の既定はモデルの直径の 1/20、``angle_bins`` は角度の分割数。

    ★回転対称な物体(球・円柱・平板)は姿勢が一意に決まらない —— 対称の分だけ別の答えが
    同じ票を取る。照合が外れたとき(仮説が 1 つも立たない)は ``rmse`` が inf、``votes`` が 0。

    空の入力(``model_points`` が 0 要素)は ``ValueError``。
    拒否(``ValueError``): 点群が (N, 3) でない、モデル点が 5 個未満、場面の点群が空。
    """
    if np.asarray(model_points).size == 0:
        raise ValueError("find_surface_pose: model_points is empty — pass at least 5 (x, y, z) points")
    if np.asarray(scene_points).size == 0:
        raise ValueError("find_surface_pose: scene_points is empty — pass the scene cloud")
    model = ppf_model(model_points, model_normals, dist_step=dist_step,
                      angle_bins=angle_bins, k_normals=k_normals)
    return surface_match(model, scene_points, scene_normals, k_normals=k_normals, **kw)
