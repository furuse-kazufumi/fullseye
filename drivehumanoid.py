# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""運転の世界を歩くヒューマノイド(2026-10-03)—— 実在ロボットの MJCF から、**軽い**歩行者を作る。

ユーザー: 「自動運転の世界で人の代わりにヒューマノイドも何種類か擬似的に歩かせておく」「計算コストを下げられるなら
手段は特に指定しない」「当たり判定はそこまで精密でなくてもいい」。

★**なぜ軽くする必要があるか(実測)**: Menagerie のヒューマノイドの見た目のメッシュは 1 体 17 万〜157 万三角形。
今の歩行者(:func:`driveterrain.pedestrian_mesh`)は 208。3 体置くと運転の世界の 1 コマが 0.066 s → 0.45〜1.5 s。
3DGS に変えても(物体ごとの上限 1,000〜30,000)0.74〜3.2 s で、メッシュより速くならなかった(描画の時間は
「ガウシアン × 覆う画素」の組の数で決まり、数を減らすと 1 個が大きくなる)。そこで:

* **見た目** = geom ごとの局所座標で頂点を格子にまとめる(vertex clustering)。三角形の予算(既定 1,500)に収まる
  格子幅を二分法で選ぶ。**失ったものを返す**: 元と後の三角形数・格子幅・頂点の最大のずれ(定理: ≤ 格子の対角 √3·c)。
* **当たり判定** = 外形の箱 ``dims``(今の歩行者と同じ扱い)。精密な形は判定に使わない。
* **動き** = 手続き的な歩き方(学習した方策は使わない —— 運転の部品はルールベース限定)。股・膝・足首・肩・肘を
  周期の式で振る。関節の符号は**関節の軸の向き**(世界の y 軸への射影)と**膝の可動域の側**から自動で決めるので、
  機種ごとの手直しは要らない。足首は足の裏が水平になるよう股と膝の和を打ち消す。腰の高さは毎コマ「いちばん低い点
  = 地面」。前進量は**支持脚の足首が地面で止まる**ように積算する(足が滑らない)。
* 1 周期を準備時に一度だけ作り(ここだけ mujoco が要る)、再生は numpy の補間だけ(:func:`humanoid_clip_mesh`)。
"""
from __future__ import annotations

import os

import numpy as np

__all__ = ["humanoid_walk_clip", "humanoid_clip_mesh", "world_pose_humanoid", "humanoid_impostors",
           "world_camera_impostors"]


# ─────────────────────────────── 形: 頂点を格子にまとめる ───────────────────────────────

def _cluster(V, F, cell):
    """頂点を幅 ``cell`` の格子でまとめる(代表 = 升の中の頂点の平均)。潰れた面・重複した面を落とす。"""
    if cell <= 0:
        return V, F, np.arange(len(V))
    key = np.floor(V / cell).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    n = int(inv.max()) + 1
    W = np.zeros((n, 3))
    np.add.at(W, inv, V)
    W /= np.bincount(inv, minlength=n)[:, None]
    G = inv[F]
    ok = (G[:, 0] != G[:, 1]) & (G[:, 1] != G[:, 2]) & (G[:, 0] != G[:, 2])
    G = G[ok]
    if len(G):
        _, first = np.unique(np.sort(G, axis=1), axis=0, return_index=True)
        G = G[np.sort(first)]
    used = np.unique(G)
    remap = np.full(n, -1, np.int64)
    remap[used] = np.arange(len(used))
    return W[used], remap[G], remap[inv]


def _primitive(gtype, size, res=8):
    """MuJoCo の基本形状(球・カプセル・円柱・箱・楕円体)を粗い三角形で(geom の局所座標、z = 軸)。"""
    import mujoco
    T = mujoco.mjtGeom
    if gtype == T.mjGEOM_BOX:
        sx, sy, sz = size
        V = np.array([[x, y, z] for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)], np.float64)
        F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                      [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]], np.int64)
        return V, F
    th = np.linspace(0, 2 * np.pi, res, endpoint=False)
    if gtype in (T.mjGEOM_SPHERE, T.mjGEOM_ELLIPSOID, T.mjGEOM_CAPSULE):
        r = float(size[0])
        half = float(size[1]) if gtype == T.mjGEOM_CAPSULE else 0.0
        ph = np.linspace(-np.pi / 2, np.pi / 2, res // 2 + 1)
        rings = []
        for p in ph:
            z = r * np.sin(p) + (half if p > 0 else -half if p < 0 else 0.0)
            rings.append(np.column_stack([r * np.cos(p) * np.cos(th), r * np.cos(p) * np.sin(th), np.full(res, z)]))
        if gtype == T.mjGEOM_CAPSULE:                                      # 赤道を上下に割って円柱部を作る
            eq = len(ph) // 2
            rings[eq] = rings[eq] + [0, 0, half]
            rings.insert(eq, rings[eq] - [0, 0, 2 * half])
        V = np.vstack(rings)
        if gtype == T.mjGEOM_ELLIPSOID:
            V = V / r * np.asarray(size[:3], np.float64)
    elif gtype == T.mjGEOM_CYLINDER:
        r, h = float(size[0]), float(size[1])
        ring = np.column_stack([r * np.cos(th), r * np.sin(th)])
        V = np.vstack([np.column_stack([ring, np.full(res, -h)]), np.column_stack([ring, np.full(res, h)])])
        rings = [V[:res], V[res:]]
    else:
        return None
    nr = len(V) // res
    F = []
    for a in range(nr - 1):
        for k in range(res):
            i0, i1 = a * res + k, a * res + (k + 1) % res
            F += [[i0, i1, i1 + res], [i0, i1 + res, i0 + res]]
    c0, c1 = len(V), len(V) + 1                                            # 両端の蓋
    V = np.vstack([V, V[:res].mean(axis=0), V[-res:].mean(axis=0)])
    for k in range(res):
        F += [[c0, (k + 1) % res, k], [c1, (nr - 1) * res + k, (nr - 1) * res + (k + 1) % res]]
    return V, np.asarray(F, np.int64)


def _local_meshes(m):
    """描く geom の局所メッシュ ``[(geom_id, V, F, rgb)]``。見た目専用の geom(衝突しない)があればそれだけ、無ければ全部。"""
    import mujoco
    T = mujoco.mjtGeom
    skip = (T.mjGEOM_PLANE, T.mjGEOM_HFIELD)
    cand = [g for g in range(m.ngeom) if m.geom_type[g] not in skip and m.geom_rgba[g, 3] > 0 and m.geom_bodyid[g] > 0]
    vis = [g for g in cand if not (m.geom_contype[g] or m.geom_conaffinity[g])]
    out = []
    for g in (vis or cand):
        if m.geom_type[g] == T.mjGEOM_MESH:
            k = int(m.geom_dataid[g])
            va, vn, fa, fn = int(m.mesh_vertadr[k]), int(m.mesh_vertnum[k]), int(m.mesh_faceadr[k]), int(m.mesh_facenum[k])
            V = np.array(m.mesh_vert[va:va + vn], np.float64)
            F = np.array(m.mesh_face[fa:fa + fn], np.int64)
        else:
            pr = _primitive(m.geom_type[g], np.asarray(m.geom_size[g], np.float64))
            if pr is None:
                continue
            V, F = pr
        mid = int(m.geom_matid[g])
        rgb = np.asarray(m.mat_rgba[mid, :3] if mid >= 0 else m.geom_rgba[g, :3], np.float64)
        out.append((g, V, F, rgb))
    if not out:
        raise ValueError("humanoid_walk_clip: 描ける geom が無い")
    return out


def _simplify_all(parts, budget):
    """全 geom を同じ格子幅でまとめ、三角形の総数が ``budget`` 以下になる最小の幅を二分法で選ぶ。"""
    n0 = sum(len(F) for _g, _V, F, _c in parts)
    if n0 <= budget:
        return [(g, V, F, c) for g, V, F, c in parts], 0.0, n0, 0.0, 0

    def run(cell):
        res, dev = [], 0.0
        for g, V, F, c in parts:
            W, G, inv = _cluster(V, F, cell)
            if len(G):
                res.append((g, W, G, c))
                dev = max(dev, float(np.max(np.linalg.norm(V - W[inv], axis=1))) if (inv >= 0).all() else dev)
        return res, dev
    ext = max(float(np.ptp(V, axis=0).max()) for _g, V, _F, _c in parts)
    lo, hi = 0.0, max(ext, 1e-3)
    best = None
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        res, dev = run(mid)
        n = sum(len(G) for _g, _W, G, _c in res)
        if n <= budget:
            hi, best = mid, (res, mid, dev)
        else:
            lo = mid
        if hi - lo < 1e-4 * max(hi, 1e-3):
            break
    if best is None:
        best = (*run(hi)[:1], hi, run(hi)[1])
    res, cell, dev = best
    return res, cell, n0, dev, len(parts) - len(res)


# ─────────────────────────────── 動き: 手続き的な歩き方 ───────────────────────────────

def _find_joints(m, d):
    """関節の役割を**名前でなく体の形**から決める(名前は機種ごとにばらばら: left_hip_pitch / LL_HFE / leg_left_3 …)。

    体の木の葉(子の無い体)から根までの鎖をたどり、軸が世界の y に近い(|axis·y| > 0.7 = 矢状面の)ヒンジを根の側から
    順に並べる。脚 = 左右それぞれでいちばん低い葉の鎖 → [股, 膝, 足首]。腕 = 脚の鎖に入らない葉のうち、その側で
    鎖のいちばん長いもの → [肩, 肘]。左右 = 葉の体の位置の y の符号(+y = 左、体は +x か −x を向いて立つ)。"""
    import mujoco
    nb = m.nbody
    kids = np.bincount(m.body_parentid[1:], minlength=nb)
    leaves = [b for b in range(1, nb) if kids[b] == 0]

    def chain(b):
        js = []
        while b > 0:
            for j in range(m.body_jntadr[b], m.body_jntadr[b] + m.body_jntnum[b]):
                if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE and abs(float(d.xaxis[j] @ (0, 1, 0))) > 0.7:
                    js.append(j)
            b = m.body_parentid[b]
        return js[::-1]                                                   # 根の側から
    root_y = float(d.xpos[1][1])
    found, leg_j = {}, set()
    for side, sg in (("left", 1.0), ("right", -1.0)):
        cand = [b for b in leaves if sg * (d.xpos[b][1] - root_y) > 0.02]
        if not cand:
            continue
        foot = min(cand, key=lambda b: d.xpos[b][2])
        js = chain(foot)
        for role, j in zip(("hip", "knee", "ankle"), js):
            found[(side, role)] = j
        leg_j |= set(js)
    for side, sg in (("left", 1.0), ("right", -1.0)):
        cand = []
        for b in leaves:
            if sg * (d.xpos[b][1] - root_y) <= 0.05:
                continue
            js = [j for j in chain(b) if j not in leg_j]
            if js and not (set(chain(b)) & leg_j):
                cand.append((len(js), js))
        if cand:
            js = max(cand)[1]
            for role, j in zip(("shoulder", "elbow"), js):
                found[(side, role)] = j
    return found


def humanoid_walk_clip(model_path, *, n_frames: int = 24, tri_budget: int = 1500, swing: float = 0.35,
                       knee: float = 0.55, arm: float = 0.6) -> dict:
    """MJCF / URDF のヒューマノイドから**歩行 1 周期**の軽いメッシュ列を作る(mujoco が要る。再生は numpy だけ)。

    Args:
        model_path: MJCF(``<mujoco>``)か URDF。根に自由関節(floating base)があること。
        n_frames: 1 周期のコマ数。
        tri_budget: 1 体の三角形の上限(格子幅を二分法で選ぶ)。
        swing: 腿を前後に振る振幅 [rad]。 knee: 振り出す脚の膝の最大の曲げ [rad]。 arm: 腕の振り / 腿の振り。

    Returns:
        ``{"V" (T, n, 3), "F" (m, 3), "color" (m, 3), "label" 7, "dims" (奥行き, 幅, 高さ), "advance" (T,)
        (各コマで腰が進んだ距離 [m]、0 から始まる), "cycle_length" [m], "facing" (+1 = 元から +x 向き / −1 = 反転した),
        "joints" (使った関節の名前), "decimation" {tris_before, tris_after, cell, max_vertex_shift, geoms_dropped
        (格子で潰れて丸ごと消えた geom の数 = 失った部品)}}``。予算は目安: geom ごとに潰しきれない下限があり、
        小さすぎる予算では部品が消える(``geoms_dropped`` で分かる)。
        V は**腰の真下の地面を原点**、+x = 前、z = 上(:func:`driveterrain.pedestrian_mesh` と同じ規約)。

    Raises:
        ImportError: mujoco が無い。 ValueError: 自由関節が無い / 股・膝が左右とも見つからない / 描ける geom が無い。
    """
    import mujoco
    if int(n_frames) < 4 or int(tri_budget) < 12:
        raise ValueError("humanoid_walk_clip: n_frames ≥ 4、tri_budget ≥ 12")
    m = mujoco.MjModel.from_xml_path(os.fspath(model_path))
    d = mujoco.MjData(m)
    free = [j for j in range(m.njnt) if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE]
    if not free:
        raise ValueError("humanoid_walk_clip: 自由関節(floating base)が無い —— 歩く体ではない")
    qa = int(m.jnt_qposadr[free[0]])
    base = np.array(m.key_qpos[0] if m.nkey else m.qpos0, np.float64)
    base[qa + 3:qa + 7] = (1, 0, 0, 0)                                    # 根は水平・回転なしから
    d.qpos[:] = base
    mujoco.mj_forward(m, d)
    J = _find_joints(m, d)
    need = [(s, r) for s in ("left", "right") for r in ("hip", "knee")]
    if any(k not in J for k in need):
        names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(m.njnt)]
        raise ValueError("humanoid_walk_clip: 左右の股(pitch)と膝が見つからない。関節: %s" % names)
    d.qpos[:] = base
    mujoco.mj_forward(m, d)
    s_y = {k: float(d.xaxis[j] @ (0, 1, 0)) for k, j in J.items()}       # 関節の軸の世界 y 成分(±1 なら矢状面の軸)
    J = {k: j for k, j in J.items() if abs(s_y[k]) > 0.7}

    def flex_side(j):                                                    # 可動域の広い側 = 曲げる向き
        lo, hi = m.jnt_range[j]
        return 1.0 if (not m.jnt_limited[j]) or abs(hi) >= abs(lo) else -1.0
    jk = J[("left", "knee")]
    facing = 1.0 if s_y[("left", "knee")] * flex_side(jk) > 0 else -1.0  # 膝を曲げると脛が後ろ = +y 回り(+x 向きの体)

    def setq(key, world_pitch):
        if key not in J:
            return
        j = J[key]
        q = world_pitch * facing / s_y[key]
        if m.jnt_limited[j]:
            q = float(np.clip(q, *m.jnt_range[j]))
        d.qpos[m.jnt_qposadr[j]] = q

    parts = _local_meshes(m)
    simp, cell, n0, dev, dropped = _simplify_all(parts, int(tri_budget))
    F = np.vstack([G + off for (_g, W, G, _c), off in
                   zip(simp, np.cumsum([0] + [len(W) for _g, W, _G, _c in simp])[:-1])])
    C = np.vstack([np.tile(c, (len(G), 1)) for _g, _W, G, c in simp])
    ank_body = {s: int(m.jnt_bodyid[J[(s, "ankle")]]) if (s, "ankle") in J else int(m.jnt_bodyid[J[(s, "knee")]])
                for s in ("left", "right")}
    frames, feet = [], []
    T = int(n_frames)
    for k in range(T):
        ph = 2 * np.pi * k / T
        d.qpos[:] = base
        for s, sg in (("left", 1.0), ("right", -1.0)):
            th = sg * swing * np.sin(ph)                                  # 腿が前 = 正
            kb = knee * max(0.0, sg * np.cos(ph)) + 0.05                  # 振り出し中(腿が前へ動く)の脚だけ深く曲げる
            setq((s, "hip"), -th)                                         # 脚を前へ = 世界の −y 回り(+x 向きの体)
            setq((s, "knee"), kb)
            setq((s, "ankle"), th - kb)                                   # 足の裏を水平に(股と膝の和を打ち消す)
            setq((s, "shoulder"), arm * th)                               # 腕は反対の脚と一緒に前へ(= 同じ側の腿と逆)
            if (s, "elbow") in J:
                j = J[(s, "elbow")]
                q = 0.3 * flex_side(j)
                d.qpos[m.jnt_qposadr[j]] = float(np.clip(q, *m.jnt_range[j])) if m.jnt_limited[j] else q
        mujoco.mj_forward(m, d)
        Vs = []
        for g, W, _G, _c in simp:
            R = np.asarray(d.geom_xmat[g]).reshape(3, 3)
            Vs.append(W @ R.T + d.geom_xpos[g])
        V = np.vstack(Vs)
        root = np.array(d.qpos[qa:qa + 3])
        V = (V - [root[0], root[1], 0.0]) * [facing, facing, 1.0]          # 腰の真下を原点、前 = +x
        dz = V[:, 2].min()
        V[:, 2] -= dz
        frames.append(V)
        feet.append({s: (np.array(d.xpos[b]) - root) * [facing, facing, 1.0] + [0, 0, -dz] for s, b in ank_body.items()})
    # 前進量: 支持脚(低い方の足首)が地面で止まるように、腰をその分だけ前へ
    adv = np.zeros(T + 1)
    for k in range(T):
        a, b = feet[k], feet[(k + 1) % T]
        st = min(("left", "right"), key=lambda s: a[s][2] + b[s][2])
        adv[k + 1] = adv[k] + max(0.0, float(a[st][0] - b[st][0]))
    V0 = frames[0]
    dims = (float(np.ptp(V0[:, 0])), float(np.ptp(V0[:, 1])), float(V0[:, 2].max()))
    return {"V": np.stack(frames), "F": F, "color": C, "label": 7, "dims": dims, "advance": adv[:T],
            "cycle_length": float(adv[T]), "facing": facing,
            "joints": sorted("%s_%s" % k for k in J),
            "decimation": {"tris_before": int(n0), "tris_after": int(len(F)), "cell": float(cell),
                           "max_vertex_shift": float(dev), "geoms_dropped": int(dropped)},
            "model": os.path.basename(os.fspath(model_path))}


# ─────────────────────────────── 再生(numpy だけ) ───────────────────────────────

def humanoid_clip_mesh(clip: dict, distance: float) -> dict:
    """歩いた距離 ``distance`` [m] でのメッシュ(``{"V","F","color","label","dims"}``、原点 = 腰の真下、+x = 前)。

    1 周期で ``cycle_length`` 進む。コマの間は頂点を線形に補間する(面の組み方は全コマ同じ)。形は腰の真下が原点のまま
    なので、**置く位置を ``distance`` だけ進めれば**支持脚は地面で止まって見える(コマの位相は ``advance`` で歩いた距離に
    合わせてある)。★2026-10-03: 最初の版は周期内の前進をここでも差し引き、置く側と 2 重に引いていた(滑りの門で発覚)。"""
    V = np.asarray(clip["V"], np.float64)
    if V.ndim != 3 or V.shape[0] < 2:
        raise ValueError("humanoid_clip_mesh: clip['V'] は (T, n, 3)、T ≥ 2")
    L = float(clip["cycle_length"])
    if not (np.isfinite(L) and L > 0) or not np.isfinite(distance):
        raise ValueError("humanoid_clip_mesh: cycle_length > 0 と有限の distance が要る")
    T = V.shape[0]
    adv = np.append(np.asarray(clip["advance"], np.float64), L)
    s = float(distance) % L
    k = int(np.clip(np.searchsorted(adv, s, side="right") - 1, 0, T - 1))
    w = (s - adv[k]) / max(adv[k + 1] - adv[k], 1e-12)
    Vk = (1 - w) * V[k] + w * V[(k + 1) % T]                              # 腰の真下が原点のまま(進むのは置く側)
    return {"V": Vk, "F": np.asarray(clip["F"], np.int64), "color": np.asarray(clip["color"], np.float64),
            "label": int(clip.get("label", 7)), "dims": tuple(clip["dims"])}


def world_pose_humanoid(world: dict, i: int, clip: dict, distance: float, x: float, y: float, yaw: float) -> None:
    """世界の物体 ``i``(:func:`driveterrain.add_mesh_object` で ``humanoid_clip_mesh`` を置いたもの)を、歩いた距離
    ``distance`` の姿勢にして ``(x, y, yaw)`` へ置き直す(頂点だけ書き換える。面・色・ラベル・``dims`` は不変)。"""
    import driveworld
    obj = world["objects"][i]
    v0, v1 = obj["verts"]
    mesh = humanoid_clip_mesh(clip, distance)
    if len(mesh["V"]) != v1 - v0:
        raise ValueError("world_pose_humanoid: objects[%d] の頂点数 %d がクリップの %d と違う" % (i, v1 - v0, len(mesh["V"])))
    world["V"][v0:v1] = driveworld.place_mesh(mesh["V"], float(x), float(y), float(yaw), float(obj.get("z", 0.0)))
    obj["pose"] = (float(x), float(y), float(yaw))


# ─────────────────── マスク付きの事前描画(インポスタ): カメラ画像はこれを貼るだけ ───────────────────
# ★ユーザー案(2026-10-03)「あらかじめ物体ごとの描画をマスク付きで作っておく」。精細なメッシュを向き × 位相ごとに
#   一度だけ描き(色・マスク・深度のずれ)、毎コマは縮めて貼り、世界の深度と比べて前後を決める。見た目は精細なまま、
#   1 体の費用は貼る画素の数だけ。近似は 2 つ(門で大きさを測る): (1) 方位を n_yaw 段に丸める、(2) 事前描画は水平に
#   遠くから見た像なので、カメラが高い・近いときの透視の違いを無視する。

def humanoid_impostors(clip: dict, *, n_yaw: int = 16, n_phase: int = 12, res: int = 128, distance: float = 30.0,
                       light=(0.3, -0.5, 0.8), ambient: float = 0.35) -> dict:
    """クリップ(:func:`humanoid_walk_clip`)を **方位 n_yaw × 位相 n_phase** の向きから描いておく。

    方位 b = 体から見たカメラの向き 2πb / n_yaw(0 = 正面 +x から見る)。カメラは体の高さの中ほどの高さから水平に、
    距離 ``distance`` で見る(ほぼ平行投影)。色は :func:`driveworld.world_camera` と同じ Lambert(光はカメラ系)。

    Returns:
        ``{"color" (n_yaw, n_phase, res, res, 3) uint8, "mask" (...) bool, "dz" (...) float16 (画素の深度 − distance [m]),
        "f" (事前描画の焦点距離 [px]), "distance", "eye_h" [m], "res", "n_yaw", "n_phase", "cycle_length", "dims",
        "phase_s" (各位相の歩いた距離 [m])}``。
    """
    import render3d
    import driveworld as DW
    n_yaw, n_phase, res = int(n_yaw), int(n_phase), int(res)
    if n_yaw < 1 or n_phase < 1 or res < 8 or not distance > 0:
        raise ValueError("humanoid_impostors: n_yaw ≥ 1、n_phase ≥ 1、res ≥ 8、distance > 0")
    Hh = float(clip["dims"][2])
    W = float(max(clip["dims"][0], clip["dims"][1])) * 1.6
    span = max(Hh, W) * 1.08
    eye_h = 0.5 * Hh
    f = res * float(distance) / span
    K = np.array([[f, 0, (res - 1) / 2.0], [0, f, (res - 1) / 2.0], [0, 0, 1.0]])
    L = float(clip["cycle_length"])
    phase_s = L * np.arange(n_phase) / n_phase
    l = np.asarray(light, np.float64)
    l = l / np.linalg.norm(l)
    col = np.zeros((n_yaw, n_phase, res, res, 3), np.uint8)
    msk = np.zeros((n_yaw, n_phase, res, res), bool)
    dz = np.zeros((n_yaw, n_phase, res, res), np.float16)
    C = np.asarray(clip["color"], np.float64)
    for p, s in enumerate(phase_s):
        mesh = humanoid_clip_mesh(clip, s)
        for b in range(n_yaw):
            a = 2 * np.pi * b / n_yaw
            eye = (distance * np.cos(a), distance * np.sin(a), eye_h)
            pose = DW.camera_pose(eye, (0.0, 0.0, eye_h))
            out = render3d.render_mesh(mesh["V"], mesh["F"], pose=pose, intrinsics=K, width=res, height=res,
                                       attributes=True)
            face = np.asarray(out["face"])
            hit = face >= 0
            sh = ambient + (1 - ambient) * np.clip(np.abs(out["normals"] @ l), 0, 1)
            c = np.zeros((res, res, 3))
            c[hit] = C[face[hit]] * sh[hit][:, None]
            col[b, p] = np.clip(np.rint(c * 255), 0, 255).astype(np.uint8)
            msk[b, p] = hit
            dz[b, p] = np.where(hit, np.asarray(out["depth"]) - distance, 0).astype(np.float16)
    return {"color": col, "mask": msk, "dz": dz, "f": float(f), "distance": float(distance), "eye_h": float(eye_h),
            "res": res, "n_yaw": n_yaw, "n_phase": n_phase, "cycle_length": L, "dims": tuple(clip["dims"]),
            "phase_s": phase_s, "label": int(clip.get("label", 7))}


def world_camera_impostors(world: dict, pose, K, width: int = 640, height: int = 400, actors=(), **camera_kw) -> dict:
    """:func:`driveworld.world_camera` で世界を撮り、``actors`` のインポスタを**深度で前後を比べて**貼る。

    ``actors`` = ``[{"imp": humanoid_impostors の返り値, "x", "y", "yaw", "distance" (歩いた距離 [m])}, …]``。
    向きの段 = 体から見たカメラの方位を n_yaw 段に丸めたもの、位相 = 歩いた距離を周期で割った余りに最も近い段。
    大きさ = 実際のカメラの「1 m あたりの画素」/ 事前描画の「1 m あたりの画素」(最近傍で拡大縮小)。
    返り値は world_camera と同じ鍵。貼った画素は ``label`` = 物体のラベル(7)、``face`` = −2(三角形が無い)、
    ``shade`` = 1。加えて ``"impostor_pixels"``(貼った画素の数)。"""
    import driveworld as DW
    v = DW.world_camera(world, pose, K, width, height, **camera_kw)
    pose = np.asarray(pose, np.float64)
    K = np.asarray(K, np.float64)
    Rinv = pose[:3, :3].T
    eye = -Rinv @ pose[:3, 3]                                             # カメラの位置(世界)
    depth = v["depth"].copy()
    color, label, face, shade = v["color"].copy(), v["label"].copy(), v["face"].copy(), v["shade"].copy()
    fx = float(K[0, 0])
    order = sorted(actors, key=lambda a: -np.hypot(a["x"] - eye[0], a["y"] - eye[1]))
    n_pix = 0
    for a in order:
        imp = a["imp"]
        res, f_s, D = imp["res"], imp["f"], imp["distance"]
        c = np.array([[float(a["x"]), float(a["y"]), imp["eye_h"]]])
        u, r, d = (np.asarray(t, np.float64)[0] for t in DW.world_project_points(c, pose, K))
        if not (np.isfinite(d) and d > 0.3):
            continue
        rel = np.arctan2(eye[1] - a["y"], eye[0] - a["x"]) - float(a["yaw"])
        b = int(np.rint(rel / (2 * np.pi / imp["n_yaw"]))) % imp["n_yaw"]
        L = imp["cycle_length"]
        p = int(np.rint((float(a["distance"]) % L) / L * imp["n_phase"])) % imp["n_phase"]
        ratio = (fx / d) / (f_s / D)
        half = (res - 1) / 2.0
        r0, r1 = int(np.floor(r - half * ratio)), int(np.ceil(r + half * ratio))
        c0, c1 = int(np.floor(u - half * ratio)), int(np.ceil(u + half * ratio))
        R0, R1, C0, C1 = max(r0, 0), min(r1, height - 1), max(c0, 0), min(c1, width - 1)
        if R0 > R1 or C0 > C1:
            continue
        rr, cc = np.mgrid[R0:R1 + 1, C0:C1 + 1]
        sr = np.rint((rr - r) / ratio + half).astype(np.int64)
        sc = np.rint((cc - u) / ratio + half).astype(np.int64)
        ok = (sr >= 0) & (sr < res) & (sc >= 0) & (sc < res)
        sr, sc = np.clip(sr, 0, res - 1), np.clip(sc, 0, res - 1)
        m = ok & imp["mask"][b, p][sr, sc]
        zd = d + imp["dz"][b, p][sr, sc].astype(np.float64)
        m &= zd < depth[R0:R1 + 1, C0:C1 + 1]
        if not m.any():
            continue
        sub = (slice(R0, R1 + 1), slice(C0, C1 + 1))
        color[sub][m] = imp["color"][b, p][sr[m], sc[m]] / 255.0
        depth[sub][m] = zd[m]
        label[sub][m] = imp["label"]
        face[sub][m] = -2
        shade[sub][m] = 1.0
        n_pix += int(m.sum())
    return {"color": color, "label": label, "depth": depth, "face": face, "shade": shade, "impostor_pixels": n_pix}
