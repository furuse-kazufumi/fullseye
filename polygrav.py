# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""一様密度の多面体(閉じた三角形メッシュ)の重力を厳密に出す —— 小惑星の表面の重力・斜面・実効ポテンシャル(2026-10-25)。

小さな天体は球ではないので ``GM/r²`` では表面の重力が分からない。形が三角形メッシュで与えられ、中の密度が一様なら、
重力ポテンシャルは面と辺の和で厳密に出る(R. A. Werner & D. J. Scheeres, "Exterior gravitation of a
polyhedron derived and compared with harmonic and mascon gravitation representations of asteroid 4769 Castalia",
Celestial Mechanics and Dynamical Astronomy 65, 313–344 (1997))。体積分を発散定理で面の積分に、面の積分を
Stokes の定理で辺の積分に落とすので、メッシュの外でも中でも表面の上でも同じ式が使える(展開の収束半径が無い)。

1. :func:`polyhedron_gravity` —— 点ごとのポテンシャル Φ・重力加速度 g = −∇Φ・発散 ∇·g(中で −4πGρ、外で 0。
   面の立体角の和なので、点が中か外かの判定にもなる)と、立体の質量・体積・重心。自転の角速度 ``omega`` を
   渡すと回る座標の実効ポテンシャルと実効重力(遠心力を足したもの)、法線を渡すと斜面の角(実効重力と
   「真下」= −法線 のなす角)も返す。
2. :func:`polyhedron_clip_halfspace` —— 閉じたメッシュを平面で切り、片側を閉じた立体として返す(切り口は
   平面上の 1 点からの扇の三角形で塞ぐ)。頭と胴で密度が違う天体は、重ね合わせ
   ``ρ_胴 · (全体) + (ρ_頭 − ρ_胴) · (頭の部分)`` で出せる(式が密度について線形だから)。

式(1 面 f ごと。r_i = 頂点 i − 観測点、n_f は外向きの単位法線、n_fe は辺 e の面内で外向きの単位法線)::

    ω_f = 2 atan2( r1·(r2×r3), |r1||r2||r3| + |r1|(r2·r3) + |r2|(r3·r1) + |r3|(r1·r2) )   (面の立体角)
    L_e = ln( (|r_i| + |r_j| + |e|) / (|r_i| + |r_j| − |e|) )                              (辺の対数)
    h_f = r_i·n_f,   S_f = Σ_e (n_fe·r_i) L_e
    Φ   = −(Gρ/2) Σ_f ( h_f S_f − h_f² ω_f )
    g   = −∇Φ = Gρ Σ_f n_f ( −S_f + h_f ω_f )
    ∇·g = −Gρ Σ_f ω_f

Werner–Scheeres の元の式は辺ごとに 2 面の行列 E_e をまとめるが、ここでは面ごとに自分の 3 辺を足す
(和の順番を変えただけで同じ値)。こうすると式が面について線形になり、平面で切った切り口を非凸の扇で
塞いでも(重なった三角形は逆向きの面積で打ち消し合う)そのまま正しい。

一次情報で確かめた式の出典: 上の Werner & Scheeres (1997) の式 (15)(16)(21)(22)(27)。
重力定数 G = 6.67430e-11 m³/(kg s²)(CODATA 2018)。

限界(honest): 密度は一様(または :func:`polyhedron_clip_halfspace` で区切った区分ごとに一様)だけ。メッシュは
閉じて向きが揃っていること(有向辺が逆向きの辺とちょうど打ち消すこと)を検査し、開いていれば ``ValueError``。
自己交差は検出しない。点 1 つに面の数の手間がかかる(5 万面 × 2.5 万点で数十秒)。

失敗はすべて ``ValueError``(空・非有限・形の不一致・閉じていないメッシュ・範囲外の索引)。numpy と標準ライブラリだけ。

呼び出し例(台帳の op を繋ぐ。tests/test_polygrav.py の test_call_example が実行する)::

    import numpy as np
    import polygrav
    V = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float) * 100.0     # 一辺 100 m の四面体
    F = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])                     # 外向きに巻く
    far = np.array([[1.0e4, 0.0, 0.0]])
    g = polygrav.polyhedron_gravity((V, F), far, density=2000.0)
    # 遠くでは点質量 GM/r² に近づく: g["acceleration"][0, 0] ≈ −G·g["mass"]/1e8
    head = polygrav.polyhedron_clip_halfspace((V, F), [50.0, 0.0, 0.0], [1.0, 0.0, 0.0])   # x ≥ 50 の側
    h = polygrav.polyhedron_gravity(head, far, density=2000.0)                    # 体積は全体の 1/8
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["G_NEWTON", "polyhedron_gravity", "polyhedron_clip_halfspace"]

#: 重力定数 [m³/(kg s²)](CODATA 2018)。
G_NEWTON = 6.67430e-11

#: 1 回にまとめて計算する観測点の数の上限を決める目安(点 × 面 の要素数)。
_BLOCK_ELEMS = 2_000_000


def _mesh(mesh, op: str):
    if not isinstance(mesh, (tuple, list)) or len(mesh) != 2:
        raise ValueError("%s: mesh は (vertices (N,3), faces (M,3)) の 2 要素" % op)
    V = np.asarray(mesh[0], dtype=float)
    F_raw = np.asarray(mesh[1])
    if V.ndim != 2 or V.shape[1] != 3 or V.shape[0] < 4:
        raise ValueError("%s: vertices は (N,3)、N ≥ 4(得たのは %s)" % (op, V.shape))
    if F_raw.ndim != 2 or F_raw.shape[1] != 3 or F_raw.shape[0] < 4:
        raise ValueError("%s: faces は (M,3)、M ≥ 4(得たのは %s)" % (op, F_raw.shape))
    if not np.all(np.isfinite(V)):
        raise ValueError("%s: vertices に NaN / inf" % op)
    if F_raw.dtype.kind == "f":
        if not np.all(np.isfinite(F_raw)) or np.any(F_raw != np.round(F_raw)):
            raise ValueError("%s: faces は整数の索引" % op)
    elif F_raw.dtype.kind not in "iu":
        raise ValueError("%s: faces は整数の索引" % op)
    F = F_raw.astype(np.int64)
    if F.min() < 0 or F.max() >= V.shape[0]:
        raise ValueError("%s: faces の索引が範囲外(0..%d)" % (op, V.shape[0] - 1))
    return V, F


def _check_closed(F: np.ndarray, op: str) -> None:
    """有向辺 (i→j) の本数が逆向き (j→i) の本数とすべて等しいこと(閉じて向きが揃った曲面)。"""
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    e = e[e[:, 0] != e[:, 1]]                     # 退化した面の 0 長の辺は数えない
    n = int(F.max()) + 1
    fwd = np.unique(e[:, 0] * n + e[:, 1], return_counts=True)
    rev = np.unique(e[:, 1] * n + e[:, 0], return_counts=True)
    if fwd[0].shape != rev[0].shape or np.any(fwd[0] != rev[0]) or np.any(fwd[1] != rev[1]):
        raise ValueError("%s: メッシュが閉じていない、または面の向きが揃っていない"
                         "(有向辺が逆向きの辺と打ち消さない)" % op)


def _pos(x, name: str, op: str) -> float:
    if isinstance(x, bool):
        raise ValueError("%s: %s は正の有限な数(得たのは %r)" % (op, name, x))
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s は正の有限な数(得たのは %r)" % (op, name, x)) from None
    if not math.isfinite(v) or v <= 0:
        raise ValueError("%s: %s は正の有限な数(得たのは %r)" % (op, name, x))
    return v


def _vec3(x, name: str, op: str, unit: bool = False) -> np.ndarray:
    a = np.asarray(x, dtype=float).reshape(-1)
    if a.shape != (3,) or not np.all(np.isfinite(a)):
        raise ValueError("%s: %s は有限な長さ 3 のベクトル" % (op, name))
    if unit:
        n = float(np.linalg.norm(a))
        if n == 0.0:
            raise ValueError("%s: %s の長さが 0" % (op, name))
        a = a / n
    return a


def _mass_props(V: np.ndarray, F: np.ndarray):
    """符号付き四面体(原点を頂点に)の和で体積と重心(発散定理。面について線形)。"""
    c = V.mean(axis=0)                            # 丸めを抑えるため頂点の平均を原点に
    a, b, d = V[F[:, 0]] - c, V[F[:, 1]] - c, V[F[:, 2]] - c
    vol6 = np.einsum("ij,ij->i", a, np.cross(b, d))
    vol = float(vol6.sum()) / 6.0
    if not vol > 0:
        raise ValueError("polyhedron_gravity: 体積が正でない(%.6g)—— 面が内向きに巻かれている" % vol)
    cen = (vol6[:, None] * (a + b + d)).sum(axis=0) / (4.0 * vol6.sum()) + c
    return vol, cen


def polyhedron_gravity(mesh, points, density: float = 1.0, G: float = G_NEWTON, omega: float = 0.0,
                       spin_axis=(0.0, 0.0, 1.0), spin_center=None, normals=None) -> dict:
    """一様密度の閉じた多面体が観測点に作る重力(Werner & Scheeres 1997 の厳密な式)。

    Parameters
    ----------
    mesh : (vertices (N,3), faces (M,3))
        閉じた三角形メッシュ。面は外向き(右手系)に巻く。長さの単位は m として扱う(km のデータは 1000 倍)。
    points : (K,3)
        観測点 [m]。外・中・表面の上(頂点・辺の上も)のどこでもよい。
    density : float
        密度 [kg/m³](正)。
    G : float
        重力定数(既定 6.67430e-11、CODATA 2018)。
    omega : float
        自転の角速度 [rad/s](0 以上)。正なら回る座標の実効ポテンシャルと実効重力も返す。
    spin_axis : (3,)
        自転軸の向き(正規化する)。既定は +z。
    spin_center : (3,), optional
        自転軸が通る点。既定は立体の重心(自由に回る天体は重心のまわりに回る)。
    normals : (K,3), optional
        観測点での外向きの法線。渡すと斜面の角 ``slope_deg`` を返す(実効重力と −法線 のなす角、
        omega = 0 なら重力そのもの)。

    Returns
    -------
    dict
        ``potential`` (K,) Φ [J/kg](負。無限遠で 0)、``acceleration`` (K,3) g = −∇Φ [m/s²](天体へ向く)、
        ``div_g`` (K,) ∇·g [1/s²](中で −4πGρ、外で 0、面の上で −2πGρ —— ガウスの法則)、
        ``solid_angle`` (K,) Σ ω_f(中で 4π、外で 0)、``mass`` [kg]、``volume`` [m³]、``center_of_mass`` (3,)。
        omega > 0 のとき ``effective_potential`` (K,) = Φ − ½ω²ρ⊥²、``effective_acceleration`` (K,3) = g + ω²ρ⊥
        (ρ⊥ は自転軸からの垂直な距離のベクトル)、``spin_center`` (3,)。normals があれば ``slope_deg`` (K,)。

    Notes
    -----
    辺の上・頂点の上の点では、その辺の対数 L_e が発散するが掛かる係数 n_fe·r_i が 0 なので、その項を 0 とする
    (極限値)。メッシュが閉じていない(有向辺が逆向きの辺と打ち消さない)、体積が正でない(内向きの巻き)、
    非有限、範囲外の索引は ``ValueError``。空の入力(``points`` が 0 要素)は ValueError で拒否する。
    """
    op = "polyhedron_gravity"
    V, F = _mesh(mesh, op)
    _check_closed(F, op)
    P = np.asarray(points, dtype=float)
    if P.ndim == 1 and P.shape == (3,):
        P = P[None, :]
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("%s: points は (K,3)(得たのは %s)" % (op, P.shape))
    if P.shape[0] == 0:
        raise ValueError("%s: points が空" % op)
    if not np.all(np.isfinite(P)):
        raise ValueError("%s: points に NaN / inf" % op)
    rho = _pos(density, "density", op)
    G = _pos(G, "G", op)
    if isinstance(omega, bool) or not math.isfinite(float(omega)) or float(omega) < 0:
        raise ValueError("%s: omega は 0 以上の有限な数(得たのは %r)" % (op, omega))
    omega = float(omega)
    nrm = None
    if normals is not None:
        nrm = np.asarray(normals, dtype=float)
        if nrm.shape != P.shape or not np.all(np.isfinite(nrm)):
            raise ValueError("%s: normals は points と同じ (K,3) の有限な配列" % op)
        ln = np.linalg.norm(nrm, axis=1)
        if np.any(ln == 0):
            raise ValueError("%s: normals に長さ 0 の行" % op)
        nrm = nrm / ln[:, None]

    vol, com = _mass_props(V, F)

    # 面ごとの定数: 単位法線、3 辺の面内の外向き法線、辺の長さ(退化した面は法線 0 = 寄与 0)
    i0, i1, i2 = F[:, 0], F[:, 1], F[:, 2]
    cr = np.cross(V[i1] - V[i0], V[i2] - V[i0])
    ca = np.linalg.norm(cr, axis=1)
    scale = float(np.ptp(V, axis=0).max())
    good = ca > 1e-14 * scale * scale
    nf = np.zeros_like(cr)
    nf[good] = cr[good] / ca[good, None]
    idx = (F[:, [0, 1, 2]], F[:, [1, 2, 0]])      # 辺 k: 頂点 idx[0][:,k] → idx[1][:,k]
    ev = V[idx[1]] - V[idx[0]]                    # (M,3,3)
    nfe = np.cross(ev, nf[:, None, :])
    nl = np.linalg.norm(nfe, axis=2)
    ok_e = nl > 0
    nfe[ok_e] = nfe[ok_e] / nl[ok_e, None]
    nfe[~ok_e] = 0.0

    # 辺の対数 L_e は辺の 2 頂点だけで決まるので、向きを無視した辺ごとに 1 回だけ計算して面へ配る
    ea, eb = idx[0].reshape(-1), idx[1].reshape(-1)
    lo, hi = np.minimum(ea, eb), np.maximum(ea, eb)
    ukey, einv = np.unique(lo * V.shape[0] + hi, return_inverse=True)
    u_a, u_b = ukey // V.shape[0], ukey % V.shape[0]
    u_len = np.linalg.norm(V[u_b] - V[u_a], axis=1)
    einv = einv.reshape(-1, 3)
    K = P.shape[0]
    M = F.shape[0]
    Phi = np.empty(K)
    acc = np.empty((K, 3))
    omg = np.empty(K)
    blk = max(1, _BLOCK_ELEMS // max(M, 1))
    for s in range(0, K, blk):
        X = P[s:s + blk]
        R = V[None, :, :] - X[:, None, :]          # (k,N,3)
        Rn = np.linalg.norm(R, axis=2)             # (k,N)
        r1, r2, r3 = R[:, i0], R[:, i1], R[:, i2]  # (k,M,3)
        n1, n2, n3 = Rn[:, i0], Rn[:, i1], Rn[:, i2]
        num = np.einsum("kmj,kmj->km", r1, np.cross(r2, r3))
        den = (n1 * n2 * n3 + n1 * np.einsum("kmj,kmj->km", r2, r3)
               + n2 * np.einsum("kmj,kmj->km", r3, r1) + n3 * np.einsum("kmj,kmj->km", r1, r2))
        w = 2.0 * np.arctan2(num, den)
        w[:, ~good] = 0.0
        h = np.einsum("kmj,mj->km", r1, nf)       # 面の平面までの符号付き距離(どの頂点でも同じ)
        ssum = Rn[:, u_a] + Rn[:, u_b]             # (k,E) 辺ごと
        dnm = ssum - u_len[None, :]
        safe = dnm > 1e-12 * u_len[None, :]
        Lu = np.log(np.where(safe, (ssum + u_len[None, :]) / np.where(safe, dnm, 1.0), 1.0))
        S = np.zeros_like(h)
        rr = (r1, r2, r3)
        for k in range(3):
            proj = np.einsum("kmj,mj->km", rr[k], nfe[:, k, :])
            S += proj * Lu[:, einv[:, k]]
        Phi[s:s + blk] = -0.5 * G * rho * np.sum(h * S - h * h * w, axis=1)
        acc[s:s + blk] = G * rho * ((-S + h * w) @ nf)
        omg[s:s + blk] = w.sum(axis=1)

    out = {"potential": Phi, "acceleration": acc, "div_g": -G * rho * omg, "solid_angle": omg,
           "mass": rho * vol, "volume": vol, "center_of_mass": com}
    if omega > 0:
        ax = _vec3(spin_axis, "spin_axis", op, unit=True)
        c = com if spin_center is None else _vec3(spin_center, "spin_center", op)
        d = P - c
        perp = d - np.outer(d @ ax, ax)
        out["effective_potential"] = Phi - 0.5 * omega * omega * np.einsum("ij,ij->i", perp, perp)
        out["effective_acceleration"] = acc + omega * omega * perp
        out["spin_center"] = c
    if nrm is not None:
        ge = out.get("effective_acceleration", acc)
        gn = np.linalg.norm(ge, axis=1)
        cosang = np.where(gn > 0, -np.einsum("ij,ij->i", ge, nrm) / np.where(gn > 0, gn, 1.0), 1.0)
        out["slope_deg"] = np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0)))
    return out


def polyhedron_clip_halfspace(mesh, point, normal):
    """閉じたメッシュを平面で切り、``(x − point)·normal ≥ 0`` の側を閉じた立体として返す → (vertices, faces)。

    切り口(平面上の多角形)は ``point`` からの扇の三角形で塞ぐ。切り口が非凸でも、``point`` が切り口の外でも、
    扇の三角形は向き付きで重なって打ち消し合うので、面について線形な量(:func:`polyhedron_gravity` の重力・
    ``mesh_volume`` の体積・重心)はそのまま正しい(見た目の三角形は重なることがある)。
    辺と平面の交点は辺ごとに 1 回だけ作るので、返りのメッシュは有向辺がちょうど打ち消す(閉じている)。
    平面の上にちょうど乗る頂点は残す側に数える。

    Parameters
    ----------
    mesh : (vertices (N,3), faces (M,3))
        閉じた三角形メッシュ(外向きの巻き)。
    point : (3,)
        平面上の 1 点(切り口の扇の中心にもなる)。
    normal : (3,)
        残す側を向く平面の法線(正規化する)。

    Returns
    -------
    (vertices (N',3), faces (M',3))
        残した側の閉じたメッシュ(使わない頂点は落とす)。切り口の三角形は末尾に並ぶ。

    平面がメッシュに交わらない(全部が片側)ときは、残す側に全部あればそのまま、全部が反対側なら ``ValueError``。
    メッシュが閉じていない・非有限・範囲外の索引も ``ValueError``。空の入力(``mesh`` の面が 0 個)は ValueError で拒否する。
    """
    op = "polyhedron_clip_halfspace"
    V, F = _mesh(mesh, op)
    _check_closed(F, op)
    p = _vec3(point, "point", op)
    n = _vec3(normal, "normal", op, unit=True)
    s = (V - p) @ n
    inside = s >= 0.0
    if not np.any(inside[F].all(axis=1) | inside[F].any(axis=1)):
        raise ValueError("%s: メッシュがすべて平面の反対側にある(残す部分が無い)" % op)
    verts = [V]
    nv = V.shape[0]
    cut_index: dict = {}

    def cut(i: int, j: int) -> int:
        # 内(s ≥ 0)の i と外(s < 0)の j の間の交点。s_i = 0 なら頂点 i そのもの。
        if s[i] == 0.0:
            return i
        key = (i, j) if i < j else (j, i)
        k = cut_index.get(key)
        if k is None:
            t = s[i] / (s[i] - s[j])
            verts.append((V[i] + t * (V[j] - V[i]))[None, :])
            k = nv + len(cut_index)
            cut_index[key] = k
        return k

    faces = []
    segs = []
    for tri in F:
        ins = inside[tri]
        if ins.all():
            faces.append(tri.tolist())
            continue
        if not ins.any():
            continue
        poly = []
        entry = exitp = None
        for k in range(3):
            a, b = int(tri[k]), int(tri[(k + 1) % 3])
            if inside[a]:
                poly.append(a)
                if not inside[b]:
                    exitp = cut(a, b)
                    poly.append(exitp)
            elif inside[b]:
                entry = cut(b, a)
                poly.append(entry)
        clean = []
        for v in poly:
            if not clean or clean[-1] != v:
                clean.append(v)
        if len(clean) > 1 and clean[0] == clean[-1]:
            clean.pop()
        for k in range(1, len(clean) - 1):
            faces.append([clean[0], clean[k], clean[k + 1]])
        if entry is not None and exitp is not None and entry != exitp:
            segs.append((entry, exitp))
    Vall = np.concatenate(verts, axis=0)
    if segs:
        o = Vall.shape[0]
        Vall = np.concatenate([Vall, p[None, :]], axis=0)
        for a, b in segs:
            faces.append([o, a, b])
    Fo = np.asarray(faces, dtype=np.int64)
    if Fo.shape[0] < 4:
        raise ValueError("%s: 残る部分が小さすぎる(面 %d 個)" % (op, Fo.shape[0]))
    used = np.unique(Fo)
    remap = -np.ones(Vall.shape[0], dtype=np.int64)
    remap[used] = np.arange(used.size)
    Vo, Fo = Vall[used], remap[Fo]
    _check_closed(Fo, op)
    return Vo, Fo
