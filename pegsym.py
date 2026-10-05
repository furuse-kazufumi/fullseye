# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pegsym — 角・六角ペグの挿入で、ペグの n 回対称を使って回転の探索を 1/n に絞る(学習なし、2026-10-05)。

物理シミュ × Fullseye 系列(柔らかい手首のペグ挿入 pegsim、失敗の分類 pegfail、2 本指の膜 pegtactile)の続き。正 n 角柱のペグ
(n = 3, 4, 6)と、同じ形を隙間 δ だけ外へずらした穴(45° の面取り W)で、ペグと穴の向きの差は **2π/n を法として**しか意味を持たない。
対称性を学習で覚えさせる研究(Symmetry-aware RL、ICRA 2024、arXiv:2402.18002)は群をデータ拡張と補助損失に使う。ここでは群論の恒等式
そのものを門にして、学習なしで残る部品を作る:
  * 画像(手首カメラで穴、上向きカメラでペグの端面)を平面の上から見た図に打ち直し、輪郭の複素フーリエ位相から向きを **2π/n を法として**
    読む(:func:`polygon_yaw_read`、:func:`relative_yaw_from_images`)。2 次モーメントは n ≥ 3 で等方になり向きを持たない。
  * 回転の探索は 1 周期 2π/n だけを、面取りが捕まえる角 φ_cap の 2 倍以下の刻みで掃く(:func:`rotation_search_plan`)。未知の向きが一様なら
    期待試行回数は (M + 1)/2(M = ⌈π/(n φ_cap)⌉、:func:`search_expected_tries` の閉形式)で、対称を知らない探索(周期 2π)との比は
    (M + 1)/(nM + 1) → 1/n。キー付きのペグ(角を 1 つ落とした正方形)は n = 1 に落ち、比は 1 になる。
  * 横ずれは Archimedes のらせん(:func:`spiral_search_points`)で掃き、期待点数は掃いた面積の閉形式 πρ²/(2ps)(:func:`spiral_expected_tries`)。

外から来るもの:
  * **閉形式(導出)**: 正 n 角形(内接円の半径 = 辺心距離 A)の穴に中心を揃えて入る回転の窓は a cos(π/n − φ) ≤ A + δ(a = A/cos(π/n))
    から φ_fit = π/n − arccos((A + δ) cos(π/n)/A)(atan2 で書く)。面取りの口(A + δ + W)で同じ式が φ_cap。中心が最適な平行移動である
    ことは回転群で不変な凸集合の議論から(正多角形のみ)。キー付きは閉形式が無いので、平行移動の線形計画(:func:`polygon_fit_check`、
    第 2 実装)で窓を測る。
  * **公表式**: 長方形のペグの二点接触(Goli, Aflakian, Qu, Zang, Saadat, Pham, Wang, "Characterizing the mechanics of rectangular peg-hole
    disassembly and the effect of the active compliance centre on the extraction force", R. Soc. Open Sci. 11(11) 240956, 2024,
    DOI 10.1098/rsos.240956、CC BY)の式 (2.28) φ = (v − v′)/h(小角)—— 面に平行な軸で傾けた正方形の二点接触の深さの極限。
    Whitney 1982 の円柱の式 l₂ = (2R − r(cos θ + sec θ))/tan θ は pegsim(原著は未読、MIT OCW 2.875 Class 3 の本文から)。多角形を任意の
    向きに傾けた時の閉形式は見つからなかった(Sturges 1988 / 1996 の正方形ペグのくさびは**未読**)ので、厳密な数値解
    (:func:`polygon_two_point_depth`、凸包の頂点が穴に入るかの線形計画 + 二分法)を、内接円(半径 clearance δ)と外接円
    (δ/cos(π/n))の円柱の式で挟む(傾き 6° の正方形で内接円の側に 1 µm = 0.03 % 出る所がある —— 円柱の式の縁の高さの項が角柱と違う)。
  * **摩擦で止まる限界(導出)**: 面取りが頂点を押してペグを回すには、軸まわりのモーメントが滑りの摩擦に勝つ必要があり、
    sin²β* = (√(1 + 8μ²) − 1)/2(β = 口に載った頂点の面の法線からの角)。六角形は頂点が面の法線に近いので、μ = 0.3 で幾何の窓 20.9° が
    6.8° に縮む(MuJoCo は 7.25°)。三角形・四角形は幾何で決まる(:func:`rotation_window` の ``mu``)。
  * **物理エンジン**(facade、mujoco が要る): 凸メッシュのペグと箱の壁の穴、手首の 6 自由度ばね(ねじりは柔らかい)、搬送台の yaw、
    手首カメラ(下向き)と上向きカメラの画像、試行の成否と相対姿勢の真値。

numpy 層(台帳 ``pegsym``、opsdrive): :func:`polygon_peg` 正 n 角形 / キー付きの頂点 / :func:`polygon_offset` 穴 = 辺を外へ δ /
  :func:`polygon_fit_check` 平行移動で入るか(線形計画の余裕)/ :func:`rotation_window` 回転の窓(閉形式 + 線形計画)/
  :func:`polygon_two_point_depth` 傾けた多角形ペグの二点接触の深さ(厳密)と円の上下限 / :func:`polygon_coverage_image` 真値つきの合成 /
  :func:`plane_topview` 斜めの画像を平面の上から見た図に / :func:`polygon_yaw_read` 向き mod 2π/n / :func:`relative_yaw_from_images` /
  :func:`symmetry_fold` 角を (−π/n, π/n] に畳む / :func:`rotation_search_plan` / :func:`search_expected_tries` /
  :func:`spiral_search_points` / :func:`spiral_expected_tries` / :func:`pegsym_scene_mjcf`(MJCF 文字列)。
mujoco 層(facade のみ): :func:`pegsym_scene_build` / :func:`pegsym_views` / :func:`pegsym_insert_try` / :func:`pegsym_search_run` /
  :func:`pegsym_two_point_depth_sim` / :func:`pegsym_scene_close`。

規約: 長さは m、角は rad(引数名に _deg / _mm が付くものだけ度・mm)。多角形は世界の xy 平面で反時計回りの頂点列 (V, 2)。向き(yaw)は
「面 0 の外向き法線」の世界 x 軸からの角(上から見て反時計回り)。穴の口(面取りの上端)が z = 0、最狭部(面取りの下端)が z = −W、
穴の軸が世界 z。上から見た図は列 = +x、行 = −y(北が上)で、画素中心が整数。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "polygon_peg", "polygon_offset", "polygon_fit_check", "rotation_window", "polygon_two_point_depth",
    "polygon_coverage_image", "plane_topview", "polygon_yaw_read", "relative_yaw_from_images", "symmetry_fold",
    "rotation_search_plan", "search_expected_tries", "spiral_search_points", "spiral_expected_tries", "pegsym_scene_mjcf",
    # mujoco が要る(facade のみ、台帳の外)
    "pegsym_scene_build", "pegsym_views", "pegsym_insert_try", "pegsym_search_run", "pegsym_two_point_depth_sim",
    "pegsym_scene_close",
]


# ======================================================================================================================
# 1. 多角形
def _poly(v, name: str, min_v: int = 3) -> np.ndarray:
    """(V, 2) の有限な頂点列を反時計回りに揃えて返す。凸でなければ ValueError(fail-closed)。"""
    p = np.asarray(v, np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < min_v or not np.all(np.isfinite(p)):
        raise ValueError("%s: vertices must be a finite (V >= %d, 2) array" % (name, min_v))
    x, y = p[:, 0], p[:, 1]
    area = 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
    if not abs(area) > 0.0:
        raise ValueError("%s: polygon has zero area" % name)
    if area < 0:
        p = p[::-1].copy()
    e = np.roll(p, -1, axis=0) - p
    cr = e[:, 0] * np.roll(e, -1, axis=0)[:, 1] - e[:, 1] * np.roll(e, -1, axis=0)[:, 0]
    if np.any(cr < -1e-12 * float(np.max(np.abs(p))) ** 2):
        raise ValueError("%s: polygon must be convex" % name)
    return p


def _halfplanes(p: np.ndarray):
    """反時計回りの凸多角形 → 外向き単位法線 (V, 2) と辺心距離 h (V,)(n·x ≤ h が内側)。"""
    e = np.roll(p, -1, axis=0) - p
    L = np.hypot(e[:, 0], e[:, 1])
    if np.any(L <= 0):
        raise ValueError("polygon has a repeated vertex")
    nrm = np.stack([e[:, 1], -e[:, 0]], axis=1) / L[:, None]
    return nrm, np.sum(nrm * p, axis=1)


def polygon_peg(n: int, apothem: float = 5.0e-3, yaw: float = 0.0, cut: float = 0.0, centre=(0.0, 0.0)) -> dict:
    """ペグの断面(反時計回りの頂点列): 正 n 角形(辺心距離 ``apothem`` [m]、面 0 の法線が ``yaw`` [rad])。``cut`` > 0 なら頂点 0
    (面 0 と面 1 の間)を、その頂点の向きを法線とする直線で外接円から ``cut`` [m] 内側で落とす —— キー付き(対称は n = 1)。
    返り ``vertices``(V, 2)、``n``(形の名目の n 回対称: キー付きは 1)、``apothem``、``circumradius``、``yaw``。
    **Raises** ValueError: n < 3、apothem ≤ 0、cut < 0 か外接円と内接円の差以上(辺が消える)。"""
    n = int(n)
    A = float(apothem)
    c = float(cut)
    if n < 3 or not (A > 0.0) or not math.isfinite(float(yaw)):
        raise ValueError("polygon_peg: need n >= 3, apothem > 0, finite yaw")
    a = A / math.cos(math.pi / n)
    if not (0.0 <= c < a - A):
        raise ValueError("polygon_peg: cut must be in [0, circumradius - apothem) = [0, %.4g), got %r" % (a - A, cut))
    cx, cy = float(centre[0]), float(centre[1])
    ang = float(yaw) + math.pi / n + 2.0 * math.pi * np.arange(n) / n
    v = np.stack([a * np.cos(ang), a * np.sin(ang)], axis=1)
    if c > 0.0:
        u = np.array([math.cos(ang[0]), math.sin(ang[0])])
        hc = a - c
        prev_, next_ = v[-1], v[1]
        # 頂点 0 の両側の辺(prev → v0、v0 → next)を n·x = hc で切る
        t1 = (hc - u @ prev_) / (u @ (v[0] - prev_))
        t2 = (hc - u @ v[0]) / (u @ (next_ - v[0]))
        p1 = prev_ + t1 * (v[0] - prev_)
        p2 = v[0] + t2 * (next_ - v[0])
        v = np.vstack([p1, p2, v[1:]])
    v = v + np.array([cx, cy])
    return {"vertices": v, "n": 1 if c > 0.0 else n, "apothem": A, "circumradius": a, "yaw": float(yaw), "cut": c}


def polygon_offset(vertices, clearance: float) -> dict:
    """凸多角形の各辺を外へ ``clearance`` [m] ずらした多角形(角は尖ったまま = 穴の図面の作り方)。正多角形なら相似拡大で、向きと
    対称は変わらない。返り ``vertices``・``normals``・``offsets``(n·x ≤ h)。**Raises** ValueError: 凸でない、clearance < 0 か有限でない、
    ずらすと辺が消える(凹みを持つ角は無いので、ここでは起きない形だけを通す)。"""
    p = _poly(vertices, "polygon_offset")
    d = float(clearance)
    if not (d >= 0.0 and math.isfinite(d)):
        raise ValueError("polygon_offset: clearance must be finite and >= 0")
    nrm, h = _halfplanes(p)
    h2 = h + d
    V = len(p)
    out = np.zeros_like(p)
    for i in range(V):
        j = (i - 1) % V                                          # 頂点 i は辺 j(i−1 → i)と辺 i(i → i+1)の交点
        M = np.array([nrm[j], nrm[i]])
        out[i] = np.linalg.solve(M, np.array([h2[j], h2[i]]))
    return {"vertices": out, "normals": nrm, "offsets": h2}


def polygon_fit_check(peg_points, hole_vertices) -> dict:
    """点群(ペグの頂点、または傾けたペグの射影した頂点)を**平行移動だけで**凸多角形の穴に入れられるか —— 余裕 m を最大にする線形計画
    max m s.t. n_j·(p + t) ≤ h_j − m(全点・全辺)を、3 本の制約が等号になる頂点の列挙で厳密に解く(辺は高々十数本、組はまとめて解く)。
    返り ``fit``(m ≥ 0)、``margin`` [m] (負なら最小の食い込み)、``t``(最適な平行移動 (2,))、``active``(等号の辺の番号)。
    **Raises** ValueError: 点群が (N ≥ 1, 2) でない・有限でない、穴が凸多角形でない、穴の法線が全方向を囲まない(有界でない)。"""
    P = np.asarray(peg_points, np.float64)
    if P.ndim != 2 or P.shape[1] != 2 or len(P) < 1 or not np.all(np.isfinite(P)):
        raise ValueError("polygon_fit_check: peg_points must be a finite (N >= 1, 2) array")
    H = _poly(hole_vertices, "polygon_fit_check")
    nrm, h = _halfplanes(H)
    b = h - np.max(P @ nrm.T, axis=0)                           # n_j·t + m ≤ b_j
    J = len(b)
    A = np.hstack([nrm, np.ones((J, 1))])
    tri = _TRIPLES.get(J)
    if tri is None:
        tri = np.array([(i, j, k) for i in range(J) for j in range(i + 1, J) for k in range(j + 1, J)], dtype=int).reshape(-1, 3)
        _TRIPLES[J] = tri
    M = A[tri]                                                    # (T, 3, 3): 3 本の等号の組を全部まとめて解く
    det = np.linalg.det(M)
    ok = np.abs(det) > 1e-12
    if not np.any(ok):
        raise ValueError("polygon_fit_check: the linear programme has no vertex (hole normals do not enclose the origin)")
    X = np.linalg.solve(M[ok], b[tri[ok]][..., None])[..., 0]     # (T', 3) = (t_x, t_y, m)
    feas = np.all(X @ A.T <= b[None, :] + 1e-12, axis=1)
    if not np.any(feas):
        raise ValueError("polygon_fit_check: the linear programme has no vertex (hole normals do not enclose the origin)")
    idx = np.where(feas)[0]
    kbest = idx[int(np.argmax(X[idx, 2]))]
    best = float(X[kbest, 2])
    return {"fit": bool(best >= 0.0), "margin": best, "t": X[kbest, :2].copy(), "active": [int(v) for v in tri[ok][kbest]]}


_TRIPLES: dict = {}


def _rot2(phi):
    c, s = math.cos(phi), math.sin(phi)
    return np.array([[c, -s], [s, c]])


def rotation_window(n: int, apothem: float, clearance: float, chamfer: float = 0.0, peg_vertices=None, hole_vertices=None,
                    tol: float = 1e-10, mu: float | None = None) -> dict:
    """ペグが穴(面取りがあれば口)に入る回転の窓。正 n 角形の閉形式(導出): 中心を揃えた時、頂点は面の法線から π/n ∓ φ の向きにあり、
    最も外へ出る頂点の法線方向の長さ a cos(π/n − |φ|) が A + δ(+ W)以下なら入る:
        φ = π/n − arccos(x)、x = (A + δ + W) cos(π/n)/A(x ≥ 1 なら窓は半周期 π/n いっぱい)。
    arccos は 1 の近くで丸めの床があるので atan2(√(1 − x²), x) で書く。``peg_vertices``・``hole_vertices`` を渡すと、線形計画
    (:func:`polygon_fit_check`、平行移動も自由)の二分法で正・負の向きの窓も測る(第 2 実装。キー付きはこちらだけ)。
    返り ``phi_fit``(口でなく最狭部)・``phi_cap``(面取りの口)・``period`` = 2π/n、``M`` = ⌈period/(2 phi_cap)⌉、
    ``lp``(``plus``/``minus``: 頂点を渡した時、口に入る窓の両端 = 0 を含む連結な区間。走査は半周期を 360 刻み、端は二分法)。

    ``mu`` を渡すと**摩擦で止まる限界**も返す(導出、45° の面取り): 口に載った頂点(面の法線から β = π/n − φ の向き)が面取りを滑り下りる
    には、ペグが回らなければならない(偶数の n では向かい合う頂点の横向きの力が打ち消し合い、並進しない)。軸まわりのばねが弱いと
    接触力の軸まわりのモーメントが 0 で釣り合う: 面取りの法線の接線成分 sin β/√2 と、滑りの向き(面の上で下り + 回転)に逆らう摩擦
    μ/√(1 + sin²β) が等しい所が境で、回るのは s√(1 + s²) > √2 μ(s = sin β)、すなわち s² > (√(1 + 8μ²) − 1)/2 の時。
    ``phi_friction`` = π/n − β*、``phi_eff`` = max(phi_fit, min(phi_cap, phi_friction))(面取りに頼らず入る分は摩擦に依らない)。
    六角形(頂点が面の法線に近い)は摩擦で窓が狭まり、三角形・四角形は幾何で決まる —— MuJoCo の試作で確かめた(PoC の --full)。
    **Raises** ValueError: n < 1、apothem ≤ 0、clearance < 0、chamfer < 0、mu < 0、頂点を片方だけ渡した。"""
    n = int(n)
    A, d, W = float(apothem), float(clearance), float(chamfer)
    if n < 1 or not (A > 0.0) or not (d >= 0.0) or not (W >= 0.0):
        raise ValueError("rotation_window: need n >= 1, apothem > 0, clearance >= 0, chamfer >= 0")
    if (peg_vertices is None) != (hole_vertices is None):
        raise ValueError("rotation_window: pass both peg_vertices and hole_vertices, or neither")
    period = 2.0 * math.pi / n

    def closed(gap):
        if n < 3:
            return float("nan")
        x = (A + gap) * math.cos(math.pi / n) / A
        if x >= 1.0:
            return math.pi / n
        return math.pi / n - math.atan2(math.sqrt(1.0 - x * x), x)

    out = {"phi_fit": closed(d), "phi_cap": closed(d + W), "period": period}
    if mu is not None:
        mu_ = float(mu)
        if not (mu_ >= 0.0 and math.isfinite(mu_)):
            raise ValueError("rotation_window: mu must be finite and >= 0")
        s2 = (math.sqrt(1.0 + 8.0 * mu_ * mu_) - 1.0) / 2.0
        beta = math.atan2(math.sqrt(s2), math.sqrt(max(0.0, 1.0 - s2))) if s2 < 1.0 else math.pi / 2
        out["beta_star"] = beta
        out["phi_friction"] = (math.pi / n - beta) if n >= 3 else float("nan")
        if n >= 3:
            out["phi_eff"] = max(out["phi_fit"], min(out["phi_cap"], out["phi_friction"]))
    if peg_vertices is not None:
        P = _poly(peg_vertices, "rotation_window")
        Hm = polygon_offset(hole_vertices, W)["vertices"] if W > 0 else _poly(hole_vertices, "rotation_window")
        c0 = P.mean(axis=0)

        def fits(phi):
            return polygon_fit_check((P - c0) @ _rot2(phi).T + c0, Hm)["fit"]

        if not fits(0.0):
            raise ValueError("rotation_window: the peg does not fit even when aligned")
        lp = {}
        half = math.pi / n
        n_scan = 360
        for sgn, key in ((1.0, "plus"), (-1.0, "minus")):
            # 窓は 0 を含む連結な区間: 半周期を 0.5° 刻みで外へ歩いて最初に入らない角を探し、その手前と二分法(キー付きは 90° 先の
            # 口にも入りうるので、半周期の端だけを見ると窓を取り違える)
            lo, hi = 0.0, None
            for j in range(1, n_scan + 1):
                a = half * j / n_scan
                if fits(sgn * a):
                    lo = a
                else:
                    hi = a
                    break
            if hi is None:
                lp[key] = half
                continue
            while hi - lo > tol:
                mid = 0.5 * (lo + hi)
                if fits(sgn * mid):
                    lo = mid
                else:
                    hi = mid
            lp[key] = 0.5 * (lo + hi)
        out["lp"] = lp
    cap = out.get("phi_eff", out["phi_cap"])
    if not math.isfinite(cap):
        cap = min(out["lp"].values()) if "lp" in out else float("nan")
    out["M"] = int(math.ceil(period / (2.0 * cap) - 1e-12)) if cap > 0 and math.isfinite(cap) else 1
    return out


def _tilt_matrix(theta, psi):
    """z 軸を、水平の向き ψ へ θ だけ傾ける回転(回転軸 = z × u、u = (cos ψ, sin ψ, 0))。"""
    u = np.array([math.cos(psi), math.sin(psi), 0.0])
    k = np.cross([0.0, 0.0, 1.0], u)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(theta) * K + (1 - math.cos(theta)) * K @ K


def _projected_set(P2, theta, psi, depth):
    """断面 P2(ペグ系、軸 = 原点)のペグを θ・ψ に傾け、先端の中心を z = −depth に置いた時、z ≤ 0 の部分の凸包の頂点(水平の射影)。"""
    Rm = _tilt_matrix(theta, psi)
    tip = np.hstack([P2, np.zeros((len(P2), 1))]) @ Rm.T + np.array([0.0, 0.0, -depth])
    ax = Rm[:, 2]
    s = -tip[:, 2] / ax[2]                                    # 側面の稜線が z = 0 を切る点
    top = tip + s[:, None] * ax[None, :]
    keep = s > 0
    return np.vstack([tip[:, :2], top[keep, :2]])


def polygon_two_point_depth(peg_vertices, hole_vertices, theta: float, tilt_dir: float = 0.0, depth_max: float = 0.05,
                            tol: float = 1e-10) -> dict:
    """傾けた多角形ペグの二点接触の深さ l₂ [m] (最狭部 z = 0 から先端の中心まで)を厳密に: 深さ l で z ≤ 0 にあるペグの部分は、先端面の
    頂点と側面の稜線が z = 0 を切る点の凸包。穴は鉛直な角柱なので、この頂点の水平の射影が平行移動で穴に入る(:func:`polygon_fit_check`)
    間は入り、l を深くすると入らなくなる —— その境を二分法で。``tilt_dir`` = 傾ける水平の向き [rad] (世界系、ペグの断面と同じ系)。
    比べる円の式(Whitney、pegsim の 3-D 円柱の厳密式 (2R − r(cos θ + sec θ))/tan θ)を、内接円(r = A、R = A + δ)と外接円
    (r = A/cos(π/n)、R = (A + δ)/cos(π/n))で返す(``circle_in``・``circle_out``)。正方形を面に平行な軸で傾けた時の小角の極限は
    Goli ほか 2024 の式 (2.28) φ = (v − v′)/h、すなわち l₂ tan θ → 2δ(``goli_small_angle`` = 2δ/tan θ)。
    奇数の n(三角形)は面の向かいが頂点なので、どの向きでも内接円の式より深い。偶数の n は面の法線の向きで内接円の式に一致する
    (正方形で 1e-11 m)。内接円の側に 0.03 % まで出る組がある(傾き 6°、面から 15°)。
    返り ``l2``・``circle_in``・``circle_out``・``goli_small_angle``(δ は辺心距離の差の平均、n は頂点数)。
    **Raises** ValueError: θ ≤ 0 か ≥ 30°、まっすぐでも入らない、depth_max まで二点接触しない。"""
    P = _poly(peg_vertices, "polygon_two_point_depth")
    H = _poly(hole_vertices, "polygon_two_point_depth")
    th = float(theta)
    if not (0.0 < th < math.radians(30.0)):
        raise ValueError("polygon_two_point_depth: theta must be in (0, 30 deg)")
    c0 = P.mean(axis=0)
    P0 = P - c0

    def fits(depth):
        return polygon_fit_check(_projected_set(P0, th, float(tilt_dir), depth), H)["fit"]

    lo, hi = 0.0, float(depth_max)
    if not fits(lo):
        raise ValueError("polygon_two_point_depth: the tilted peg does not enter at the narrowest section (tilt too large)")
    if fits(hi):
        raise ValueError("polygon_two_point_depth: no two-point contact down to depth_max=%.4g m" % hi)
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if fits(mid):
            lo = mid
        else:
            hi = mid
    l2 = 0.5 * (lo + hi)
    nP, hP = _halfplanes(P0)
    nH, hH = _halfplanes(H - H.mean(axis=0))
    A, Ah = float(np.mean(hP)), float(np.mean(hH))
    nv = len(P)
    cs = math.cos(math.pi / nv)

    def circ(r, R):
        return (2.0 * R - r * (math.cos(th) + 1.0 / math.cos(th))) / math.tan(th)

    return {"l2": l2, "circle_in": circ(A, Ah), "circle_out": circ(A / cs, Ah / cs), "goli_small_angle": 2.0 * (Ah - A) / math.tan(th),
            "theta": th, "tilt_dir": float(tilt_dir)}


# ======================================================================================================================
# 2. 画像
def polygon_coverage_image(vertices_px, size: int = 160, ss: int = 8, width: int | None = None) -> np.ndarray:
    """凸多角形(画素座標 (col, row) の頂点列)の被覆率の像 0..1((size, width)、反エイリアスは ``ss`` × ``ss`` の副標本)。真値つきの
    合成の部品。**Raises** ValueError: 凸でない、size < 8、ss < 1。"""
    if int(size) < 8 or int(ss) < 1 or (width is not None and int(width) < 8):
        raise ValueError("polygon_coverage_image: need size >= 8, width >= 8, ss >= 1")
    P = np.asarray(vertices_px, np.float64)
    if P.ndim != 2 or P.shape[1] != 2:
        raise ValueError("polygon_coverage_image: vertices_px must be (V, 2) = (col, row)")
    Pc = _poly(P, "polygon_coverage_image")
    nrm, h = _halfplanes(Pc)
    Hh, Ww = int(size), int(size if width is None else width)
    off = (np.arange(int(ss)) + 0.5) / int(ss) - 0.5
    yy, xx = np.mgrid[0:Hh, 0:Ww].astype(np.float64)
    acc = np.zeros((Hh, Ww))
    for dy in off:
        for dx in off:
            x, y = xx + dx, yy + dy
            inside = np.ones((Hh, Ww), bool)
            for k in range(len(h)):
                inside &= nrm[k, 0] * x + nrm[k, 1] * y <= h[k]
            acc += inside
    return acc / (int(ss) ** 2)


def _gray(img) -> np.ndarray:
    a = np.asarray(img, np.float64)
    if a.ndim == 3 and a.shape[2] in (3, 4):
        a = a[..., :3] @ np.array([0.299, 0.587, 0.114])
    if a.ndim != 2 or a.shape[0] < 4 or a.shape[1] < 4 or not np.all(np.isfinite(a)):
        raise ValueError("image must be a finite (H >= 4, W >= 4) gray or (H, W, 3) colour array")
    return a


def plane_topview(image, K, R, t, z: float = 0.0, centre=(0.0, 0.0), extent: float = 0.02, res: float = 0.05e-3,
                  fill: float = 0.0) -> np.ndarray:
    """斜めや下からの画像を、世界の平面 z = ``z`` を真上から見た図に打ち直す(ホモグラフィ = 各格子点を投影して双線形で引く)。
    カメラは世界 → OpenCV カメラの ``R``・``t``(x_c = R X + t)、内部 ``K``(画素中心が整数の規約)。格子は ``centre`` = (x, y) を中心に
    一辺 ``extent`` [m]、画素 ``res`` [m]。列 = +x、行 = −y(北が上)。下から見た画像(鏡像)もこの図では同じ向きになる。カメラの後ろ・
    画像の外の格子点は ``fill``。返り = (S, S) の濃淡(カラーは輝度にする)。
    **Raises** ValueError: 画像が 2-D 濃淡か (H, W, 3) でない、K・R が 3×3 でない、t が 3 成分でない、extent ≤ 0、res ≤ 0、S > 4096。"""
    g = _gray(image)
    Km, Rm = np.asarray(K, np.float64), np.asarray(R, np.float64)
    tv = np.asarray(t, np.float64).reshape(-1)
    if Km.shape != (3, 3) or Rm.shape != (3, 3) or tv.shape != (3,):
        raise ValueError("plane_topview: K and R must be 3x3, t must have 3 components")
    if not (float(extent) > 0.0 and float(res) > 0.0):
        raise ValueError("plane_topview: extent and res must be > 0")
    S = int(round(float(extent) / float(res)))
    if S < 8 or S > 4096:
        raise ValueError("plane_topview: extent/res gives %d px (need 8..4096)" % S)
    c = (S - 1) / 2.0
    ii, jj = np.mgrid[0:S, 0:S].astype(np.float64)
    X = float(centre[0]) + (jj - c) * float(res)
    Y = float(centre[1]) - (ii - c) * float(res)
    Pw = np.stack([X, Y, np.full_like(X, float(z))], axis=-1).reshape(-1, 3)
    Pc = Pw @ Rm.T + tv
    zc = Pc[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        u = Km[0, 0] * Pc[:, 0] / zc + Km[0, 1] * Pc[:, 1] / zc + Km[0, 2]
        v = Km[1, 1] * Pc[:, 1] / zc + Km[1, 2]
    Hh, Ww = g.shape
    ok = (zc > 0) & (u >= 0) & (u <= Ww - 1) & (v >= 0) & (v <= Hh - 1)
    out = np.full(S * S, float(fill))
    u0 = np.clip(np.floor(u[ok]).astype(int), 0, Ww - 2)
    v0 = np.clip(np.floor(v[ok]).astype(int), 0, Hh - 2)
    fu, fv = u[ok] - u0, v[ok] - v0
    out[ok] = ((1 - fu) * (1 - fv) * g[v0, u0] + fu * (1 - fv) * g[v0, u0 + 1] + (1 - fu) * fv * g[v0 + 1, u0]
               + fu * fv * g[v0 + 1, u0 + 1])
    return out.reshape(S, S)


def symmetry_fold(angle: float, n: int) -> float:
    """角を n 回対称の商 SO(2)/C_n の代表 (−π/n, π/n] に畳む(n = 1 は (−π, π]、n = 0 = 円は 0)。群の恒等式
    symmetry_fold(α + 2πk/n, n) = symmetry_fold(α, n) が門。**Raises** ValueError: n < 0、角が有限でない。"""
    n = int(n)
    a = float(angle)
    if n < 0 or not math.isfinite(a):
        raise ValueError("symmetry_fold: need n >= 0 and a finite angle")
    if n == 0:
        return 0.0
    P = 2.0 * math.pi / n
    r = math.fmod(a + 0.5 * P, P)
    if r <= 0.0:
        r += P
    return r - 0.5 * P


def polygon_yaw_read(topview, n: int | None = None, polarity: str = "dark", K: int = 24, rel: float = 0.02) -> dict:
    """上から見た図(:func:`plane_topview`、列 = +x・行 = −y)の物体の輪郭(副画素の等値線、:mod:`pegtactile` と同じ ``threshold_sub_pix``)
    の複素フーリエ係数から、向きを**周期 2π/n を法として**読む。n 回対称なら非零の係数は k ≡ 1 (mod n) だけで、
    arg(c₁₋ₙ c₁ⁿ⁻¹)/n は始点に依らない(:func:`pegtactile.symmetry_order_contour`)。``n`` を渡すと検出した n でなくその n の位相を使う
    (図面で n が分かっている時。実画像の縁の揺れで余分な係数が有意になっても位相は読める)。
    ``polarity`` = 物体が暗い("dark"、穴)か明るい("bright"、ペグの端面)。濃淡は 2 % と 98 % の分位で 0..1 に伸ばしてから 0.5 の等値線。
    返り ``n_detected``・``n_used``・``yaw``(世界の向き、像の行が −y なので符号を戻す、周期 2π/n_used の代表 [0, P))・``centroid_px``
    (row, col)・``amps``。n_used = 0(円)なら yaw = nan。
    **Raises** ValueError: polarity が不明、像が平ら、輪郭が無い、n < 0。"""
    import fourierdesc as FD
    import pegtactile as PT
    g = _gray(topview)
    if polarity not in ("dark", "bright"):
        raise ValueError("polygon_yaw_read: polarity must be 'dark' or 'bright'")
    if n is not None and int(n) < 0:
        raise ValueError("polygon_yaw_read: n must be >= 0")
    lo, hi = np.percentile(g, [2.0, 98.0])
    if not (hi - lo > 1e-9):
        raise ValueError("polygon_yaw_read: the image is flat")
    cov = np.clip((g - lo) / (hi - lo), 0.0, 1.0)
    if polarity == "dark":
        cov = 1.0 - cov
    cont = PT._level_contour(cov, 0.5)
    sym = PT.symmetry_order_contour(cont, K=int(K), rel=float(rel))
    nu = sym["n"] if n is None else int(n)
    yaw = float("nan")
    if nu >= 1:
        sp = FD.contour_fourier_complex(np.asarray(cont, np.float64), n_harmonics=int(K), parametrisation="arclength")
        coef = {int(round(k)): complex(re, im) for k, re, im in sp}
        c1 = coef[1]
        if nu >= 2:
            if (1 - nu) not in coef:
                raise ValueError("polygon_yaw_read: K=%d is too small for n=%d" % (K, nu))
            zz = coef[1 - nu] * c1 ** (nu - 1)
            a_img = math.atan2(zz.imag, zz.real) / nu
        else:
            zz = coef[2] * c1 ** (-2)
            a_img = -math.atan2(zz.imag, zz.real)
        P = 2.0 * math.pi / nu
        yaw = (-a_img) % P
    return {"n_detected": sym["n"], "n_used": nu, "yaw": yaw, "centroid_px": sym["centroid"], "amps": sym["amps"]}


def relative_yaw_from_images(peg_view, hole_view, n: int, peg_polarity: str = "bright", hole_polarity: str = "dark", K: int = 24) -> dict:
    """ペグ(上向きカメラ → 先端面の平面に打ち直した図)と穴(手首カメラ → 口の平面の図)の向きの差を、n 回対称の商で:
    Δ = symmetry_fold(yaw_peg − yaw_hole, n)。どちらも :func:`polygon_yaw_read` で読み、形ごとの位相の定数(頂点の向きと面の向きの差)は
    同じ形どうしの差で消える(穴はペグを外へずらした相似形なので)。キー付き(n = 1)は相似でないので、ずれが小さく残る(門で測る)。
    返り ``delta``(ペグを −delta 回せば揃う)、``peg``・``hole``(読み)、``n``。
    **Raises** ValueError: n < 1、読みが失敗した(:func:`polygon_yaw_read` の例外)。"""
    if int(n) < 1:
        raise ValueError("relative_yaw_from_images: n must be >= 1 (a round peg has no orientation)")
    rp = polygon_yaw_read(peg_view, n=int(n), polarity=peg_polarity, K=K)
    rh = polygon_yaw_read(hole_view, n=int(n), polarity=hole_polarity, K=K)
    return {"delta": symmetry_fold(rp["yaw"] - rh["yaw"], int(n)), "peg": rp, "hole": rh, "n": int(n)}


# ======================================================================================================================
# 3. 探索
def rotation_search_plan(n_sym: int, phi_cap: float, estimate: float = 0.0, order: str = "alternate") -> dict:
    """回転の探索の候補(ペグに加える yaw の補正): 1 周期 P = 2π/n_sym を M = ⌈P/(2 phi_cap)⌉ 等分した刻み s = P/M(≤ 2 phi_cap なので
    捕まえる窓が隙間なく覆う)。``order`` = "alternate"(推定値から 0, +s, −s, +2s, …)か "sweep"(0, s, 2s, …)。n_sym = 0(円)は 1 候補。
    返り ``angles``(M,)、``step``、``period``、``M``。
    **Raises** ValueError: n_sym < 0、phi_cap ≤ 0、order が不明。"""
    n = int(n_sym)
    cap = float(phi_cap)
    if n < 0 or not (cap > 0.0) or not math.isfinite(cap):
        raise ValueError("rotation_search_plan: need n_sym >= 0 and phi_cap > 0")
    if order not in ("alternate", "sweep"):
        raise ValueError("rotation_search_plan: order must be 'alternate' or 'sweep'")
    if n == 0:
        return {"angles": np.array([float(estimate)]), "step": 0.0, "period": 0.0, "M": 1}
    P = 2.0 * math.pi / n
    M = max(1, int(math.ceil(P / (2.0 * cap) - 1e-12)))
    s = P / M
    if order == "sweep":
        k = np.arange(M)
    else:
        k = [0]
        for j in range(1, M):
            k.append((j + 1) // 2 if j % 2 else -(j // 2))
        k = np.asarray(k)
    assert len(k) >= 1
    return {"angles": float(estimate) + k * s, "step": s, "period": P, "M": M}


def search_expected_tries(n_sym: int, phi_cap: float, order: str = "alternate", estimate_sigma: float | None = None) -> dict:
    """回転の探索の期待試行回数(未知の向きの誤差 e が 1 周期に一様のとき、厳密)。候補 c_k(:func:`rotation_search_plan`)で k 回目に
    入るのは e が [c_k − φ, c_k + φ] (周期 P)に初めて入った時なので E = Σ_k (1 − |∪_{i<k} I_i|/P)。計算は区間の端で円周を割り、
    小区間ごとに最初に覆う候補の番号を数える(同じ値、O(M²) のベクトル演算)。刻みが
    ちょうど 2φ なら E = (M + 1)/2(``closed``)。対称を知らない探索(周期 2π、M₁ = ⌈π/φ⌉)との比 ``ratio_vs_blind`` → 1/n。
    ``estimate_sigma`` [rad] を渡すと、e が推定値のまわりに標準偏差 σ の正規(周期に巻いたもの)で、"alternate" の順の期待回数も返す
    (``expected_with_estimate``、数値積分 4,096 点)。返り ``expected``・``closed``・``M``・``blind_expected``・``ratio_vs_blind``。
    **Raises** ValueError: n_sym < 1、phi_cap ≤ 0、sigma ≤ 0。"""
    n = int(n_sym)
    if n < 1:
        raise ValueError("search_expected_tries: n_sym must be >= 1 (a round peg needs no rotation search)")
    plan = rotation_search_plan(n, phi_cap, 0.0, order)
    P, cap = plan["period"], float(phi_cap)

    def expected(pl, period):
        # 区間の端で円周を小区間に割り、各小区間を最初に覆う候補の番号 k で E = Σ 長さ·k / P(和の長さの式と同じ値を O(M²) の
        # ベクトル演算で。覆われない小区間は全候補を試しても入らないので M + 1 回と数える —— 刻み ≤ 2φ なら起きない)
        ang = np.asarray(pl["angles"], np.float64)
        ends = np.sort(np.concatenate([(ang - cap) % period, (ang + cap) % period, [0.0, period]]))
        seg = np.diff(ends)
        mid = ends[:-1] + 0.5 * seg
        keep = seg > 0
        mid, seg = mid[keep], seg[keep]
        dist = np.abs((mid[:, None] - ang[None, :] + 0.5 * period) % period - 0.5 * period)
        hit = dist <= cap
        first = np.where(hit.any(axis=1), np.argmax(hit, axis=1) + 1, len(ang) + 1)
        return float(np.sum(seg * first) / period)

    E = expected(plan, P)
    blind = rotation_search_plan(1, cap, 0.0, order)
    Eb = expected(blind, 2.0 * math.pi)
    out = {"expected": E, "closed": (plan["M"] + 1) / 2.0, "M": plan["M"], "blind_M": blind["M"], "blind_expected": Eb,
           "ratio_vs_blind": E / Eb, "period": P}
    if estimate_sigma is not None:
        sg = float(estimate_sigma)
        if not (sg > 0.0):
            raise ValueError("search_expected_tries: estimate_sigma must be > 0")
        e = (np.arange(4096) + 0.5) / 4096 * P - 0.5 * P
        w = np.zeros_like(e)
        for m in range(-3, 4):
            w += np.exp(-0.5 * ((e + m * P) / sg) ** 2)
        w /= w.sum()
        alt = rotation_search_plan(n, cap, 0.0, "alternate")["angles"]
        tries = np.full(e.shape, len(alt), float)
        found = np.zeros(e.shape, bool)
        for k, a in enumerate(alt):
            d = np.abs((e - a + 0.5 * P) % P - 0.5 * P)
            hit = (~found) & (d <= cap)
            tries[hit] = k + 1
            found |= hit
        out["expected_with_estimate"] = float(np.sum(w * tries))
    return out


def spiral_search_points(pitch: float, step: float, r_max: float, centre=(0.0, 0.0)) -> dict:
    """横ずれの探索点: Archimedes のらせん r = p φ/(2π) を弧長 ``step`` [m] ごとに(中心から)、半径 ``r_max`` まで。隣の巻きとの間隔 =
    ``pitch``。面取りが捕まえる半径を c とすると、p ≤ 2c かつ step ≤ 2c で抜けなく覆う(隣の巻きの間の点の最悪の距離 √((p/2)² + (s/2)²)
    ≤ c が十分条件、``worst_gap`` で返す)。返り ``points``(N, 2)、``worst_gap``、``n``。
    **Raises** ValueError: pitch・step・r_max ≤ 0、点が 200,000 を超える。"""
    p, s, rm = float(pitch), float(step), float(r_max)
    if not (p > 0 and s > 0 and rm > 0):
        raise ValueError("spiral_search_points: pitch, step and r_max must be > 0")
    est = math.pi * rm * rm / (p * s) + 2
    if est > 200000:
        raise ValueError("spiral_search_points: too many points (%d)" % est)
    b = p / (2.0 * math.pi)
    # 弧長 ds = √(r² + b²) dφ を細かい φ の格子で積み、s ごとに点を置く(1 歩で φ を進めると中心の近くで最初の巻きを飛び越え、
    # 覆いに穴が開く —— 試作で 64 / 11,285 格子点)
    phi_max = rm / b
    n_fine = int(min(4_000_000, max(2000, 40 * (rm / s) * (rm / p) * 2 * math.pi)))
    phi = np.linspace(0.0, phi_max, n_fine)
    r = b * phi
    ds = np.sqrt(r[:-1] ** 2 + b * b) * np.diff(phi)
    arc = np.concatenate([[0.0], np.cumsum(ds)])
    targets = np.arange(0.0, arc[-1], s)
    ph = np.interp(targets, arc, phi)
    rr = b * ph
    P = np.stack([rr * np.cos(ph), rr * np.sin(ph)], axis=1) + np.array([float(centre[0]), float(centre[1])])
    return {"points": P, "worst_gap": math.hypot(p / 2.0, s / 2.0), "n": len(P)}


def spiral_expected_tries(points, capture: float, rho: float, grid: int = 161) -> dict:
    """横ずれが半径 ``rho`` の円板に一様のとき、点列 ``points`` を順に試して初めて(距離 ≤ ``capture``)捕まえるまでの期待試行回数。
    ``measured`` = 円板内の格子(grid × grid、円の外は捨てる)の平均。``closed`` = 掃いた面積の近似: k 点で面積 k·p·s を掃くので、半径 r に
    達するのは k = πr²/(ps)、r が円板に一様なら E = πρ²/(2ps) + 1/2(p・s は点列から推定: s = 隣の点の距離の中央値、p = 外周の点の半径の
    巻きあたりの増分)。どの点でも捕まらない格子点があれば ``uncovered`` > 0(覆いの穴)。
    **Raises** ValueError: 点が (N ≥ 3, 2) でない、capture・rho ≤ 0、grid < 11。"""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 2 or len(P) < 3 or not np.all(np.isfinite(P)):
        raise ValueError("spiral_expected_tries: points must be a finite (N >= 3, 2) array")
    c, rho = float(capture), float(rho)
    if not (c > 0 and rho > 0) or int(grid) < 11:
        raise ValueError("spiral_expected_tries: need capture > 0, rho > 0, grid >= 11")
    g = np.linspace(-rho, rho, int(grid))
    X, Y = np.meshgrid(g, g)
    m = X * X + Y * Y <= rho * rho
    Q = np.stack([X[m], Y[m]], axis=1) + P[0]
    tries = np.full(len(Q), np.nan)
    for k in range(len(P)):
        todo = np.isnan(tries)
        if not np.any(todo):
            break
        d2 = np.sum((Q[todo] - P[k]) ** 2, axis=1)
        idx = np.where(todo)[0][d2 <= c * c]
        tries[idx] = k + 1
    unc = int(np.sum(np.isnan(tries)))
    ds = np.hypot(*np.diff(P, axis=0).T)
    s = float(np.median(ds))
    r = np.hypot(*(P - P[0]).T)
    ang = np.unwrap(np.arctan2(*(P - P[0])[:, ::-1].T))
    sel = r > 0.3 * r.max()
    pitch = float(np.polyfit(ang[sel], r[sel], 1)[0] * 2 * math.pi) if np.sum(sel) >= 3 else float("nan")
    return {"measured": float(np.nanmean(tries)) if unc < len(Q) else float("nan"), "closed": math.pi * rho * rho / (2 * pitch * s) + 0.5,
            "uncovered": unc, "pitch": pitch, "step": s, "n_grid": int(len(Q))}


# ======================================================================================================================
# 4. MJCF(numpy だけ)
def _quat_z(phi):
    return np.array([math.cos(phi / 2), 0.0, 0.0, math.sin(phi / 2)])


def _quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def pegsym_scene_mjcf(peg_vertices, hole_vertices, chamfer: float = 0.5e-3, hole_depth: float = 20.0e-3, peg_length: float = 40.0e-3,
                      mu: float = 0.3, k_trans: float = 600.0, k_rot: float = 1.5, k_yaw: float = 0.01, timestep: float = 5e-4,
                      image_size=(480, 480), fovy_deg: float = 40.0, station=(0.10, 0.0), offsamples: int = 4) -> str:
    """多角形ペグの場面の MJCF 文字列(mujoco 不要): 穴 = 辺ごとに壁の箱(最狭部より下)・45° の面取りの板・明るい襟(口の面 z = 0)、
    ペグ = 凸メッシュの角柱(断面 ``peg_vertices``、ペグ系、軸が原点)。搬送台は x・y・z のスライドと yaw のヒンジ(位置制御)、
    その先に 6 自由度のばねの手首(傾き ``k_rot``・ねじり ``k_yaw`` [N m/rad] は別。把持はねじりに柔らかい)。カメラは
    手首(搬送台の 30 mm 横、真下向き)と、穴から ``station`` [m] の上向きカメラ(床の面、ペグの端面を下から見る)、
    図のための斜め上の固定カメラ ``side``。
    箱は自分の辺の外側の半平面にだけあるので、角を越えて伸ばしても穴の中に入らない(凸の穴ならどの形でも同じ作り方)。
    **Raises** ValueError: 多角形が凸でない、面取り < 0、穴の深さ ≤ 面取り、摩擦 < 0、剛性 ≤ 0。"""
    P = _poly(peg_vertices, "pegsym_scene_mjcf")
    H = _poly(hole_vertices, "pegsym_scene_mjcf")
    W, Hd, L = float(chamfer), float(hole_depth), float(peg_length)
    if not (W >= 0.0 and Hd > W and L > 0.0 and float(mu) >= 0.0 and min(k_trans, k_rot, k_yaw) > 0):
        raise ValueError("pegsym_scene_mjcf: need chamfer >= 0, hole_depth > chamfer, peg_length > 0, mu >= 0, stiffness > 0")
    nrm, h = _halfplanes(H)
    V = len(H)
    span = float(np.max(np.hypot(H[:, 0], H[:, 1])))
    wall_t = 6.0e-3
    ext = 2.0 * span + 3 * wall_t
    seg = []
    for i in range(V):
        nx, ny = nrm[i]
        phi = math.atan2(ny, nx)
        mid = 0.5 * (H[i] + H[(i + 1) % V])
        tang = np.array([-ny, nx])
        tc = float(tang @ mid)                                   # 辺の中点の接線方向の位置
        qz = _quat_z(phi)
        hz = (Hd - W) / 2
        base = np.array([nx, ny]) * (h[i] + wall_t / 2) + tang * tc
        seg.append('<geom name="wall%d" type="box" size="%.6f %.6f %.6f" pos="%.7f %.7f %.7f" quat="%.9f 0 0 %.9f" '
                   'rgba="0.05 0.05 0.06 1" class="hole"/>' % (i, wall_t / 2, ext, hz, base[0], base[1], -(W + hz), qz[0], qz[3]))
        if W > 0:
            ht = 1.0e-3
            hl = (W * math.sqrt(2.0)) / 2
            fr, fz = h[i] + W / 2, -W / 2                         # 面取りの面の中点(法線方向の距離、高さ)
            nr, nzz = -1 / math.sqrt(2), 1 / math.sqrt(2)          # 面の法線(穴の中心と上を向く)
            br, bz = fr - nr * ht, fz - nzz * ht
            bc = np.array([nx, ny]) * br + tang * tc
            q = _quat_mul(qz, np.array([math.cos(math.radians(-45.0) / 2), 0.0, math.sin(math.radians(-45.0) / 2), 0.0]))
            seg.append('<geom name="chamf%d" type="box" size="%.6f %.6f %.6f" pos="%.7f %.7f %.7f" quat="%.9f %.9f %.9f %.9f" '
                       'rgba="0.16 0.16 0.18 1" class="hole"/>' % (i, hl, ext, ht, bc[0], bc[1], bz, q[0], q[1], q[2], q[3]))
        col_t = 2.0 * ext                                       # 襟は角の外まで覆う幅(狭いと角に壁の黒が覗く)
        cc = np.array([nx, ny]) * (h[i] + W + col_t / 2) + tang * tc
        seg.append('<geom name="collar%d" type="box" size="%.6f %.6f 0.0005" pos="%.7f %.7f -0.0005" quat="%.9f 0 0 %.9f" '
                   'rgba="0.62 0.62 0.60 1" class="hole"/>' % (i, col_t / 2, ext, cc[0], cc[1], qz[0], qz[3]))
    verts = " ".join("%.7f %.7f %.7f" % (x, y, z) for z in (-L, 0.0) for x, y in P)
    img_w, img_h = int(image_size[0]), int(image_size[1])
    hover = L + 10e-3
    sx, sy = float(station[0]), float(station[1])
    fl = span + W + wall_t
    return """
<mujoco model="pegsym">
  <compiler angle="radian"/>
  <option timestep="%(ts)g" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="5"/>
  <visual>
    <global offwidth="%(w)d" offheight="%(h)d"/>
    <map znear="0.005" zfar="60"/>
    <headlight ambient="0.45 0.45 0.45" diffuse="0.5 0.5 0.5" specular="0.05 0.05 0.05"/>
    <quality shadowsize="2048" offsamples="%(offs)d"/>
  </visual>
  <asset>
    <mesh name="pegmesh" vertex="%(verts)s"/>
  </asset>
  <default>
    <default class="hole">
      <geom contype="1" conaffinity="1" condim="3" friction="%(mu)g 0.005 0.0001" solref="0.002 1" solimp="0.95 0.99 0.0002"/>
    </default>
  </default>
  <worldbody>
    <light pos="0.1 -0.1 0.4" dir="-0.2 0.2 -1" diffuse="0.6 0.6 0.6" specular="0.1 0.1 0.1" castshadow="false"/>
    <geom name="floor" type="plane" size="0.5 0.5 0.01" pos="0 0 -0.03" rgba="0.6 0.62 0.65 1" contype="0" conaffinity="0"/>
    <body name="plate" pos="0 0 0">
      <site name="hole_center" pos="0 0 0" size="0.0003" rgba="0 1 0 0"/>
      <geom name="hole_floor" type="box" size="%(fl).5f %(fl).5f 0.0025" pos="0 0 %(flz).5f" rgba="0.04 0.04 0.05 1" class="hole"/>
      %(segs)s
    </body>
    <camera name="up" pos="%(sx)g %(sy)g 0.0" xyaxes="1 0 0 0 -1 0" fovy="%(fovy)g"/>
    <camera name="side" pos="0.0 -0.055 0.05" xyaxes="1 0 0 0 0.6 0.8" fovy="32"/>
    <body name="carriage" pos="0 0 %(hover)g">
      <joint name="cx" type="slide" axis="1 0 0" damping="5"/>
      <joint name="cy" type="slide" axis="0 1 0" damping="5"/>
      <joint name="cz" type="slide" axis="0 0 1" damping="5"/>
      <joint name="cyaw" type="hinge" axis="0 0 1" damping="0.05"/>
      <geom type="box" size="0.012 0.012 0.004" pos="0 0 0.004" rgba="0.08 0.08 0.09 1" mass="0.5" contype="0" conaffinity="0"/>
      <camera name="wrist" pos="-0.03 0 0.0" xyaxes="1 0 0 0 1 0" fovy="%(fovy)g"/>
      <body name="wrist" pos="0 0 0">
        <joint name="wx" type="slide" axis="1 0 0" stiffness="%(kt)g" damping="2"/>
        <joint name="wy" type="slide" axis="0 1 0" stiffness="%(kt)g" damping="2"/>
        <joint name="wz" type="slide" axis="0 0 1" stiffness="%(kt)g" damping="2"/>
        <joint name="wrx" type="hinge" axis="1 0 0" pos="0 0 0" stiffness="%(kr)g" damping="0.01"/>
        <joint name="wry" type="hinge" axis="0 1 0" pos="0 0 0" stiffness="%(kr)g" damping="0.01"/>
        <joint name="wrz" type="hinge" axis="0 0 1" pos="0 0 0" stiffness="%(ky)g" damping="0.0005"/>
        <geom name="peg" type="mesh" mesh="pegmesh" rgba="0.85 0.80 0.70 1" mass="0.03" class="hole"/>
        <site name="tip" pos="0 0 %(mL)g" size="0.0003" rgba="1 0 0 0"/>
        <site name="peg_top" pos="0 0 0" size="0.0003" rgba="1 0 0 0"/>
      </body>
    </body>
  </worldbody>
  <actuator>
    <position name="ax" joint="cx" kp="4000" kv="60"/>
    <position name="ay" joint="cy" kp="4000" kv="60"/>
    <position name="az" joint="cz" kp="4000" kv="60"/>
    <position name="ayaw" joint="cyaw" kp="5" kv="0.2"/>
  </actuator>
</mujoco>
""" % {"ts": timestep, "w": img_w, "h": img_h, "offs": int(offsamples), "verts": verts, "mu": mu, "fl": fl, "flz": -Hd - 0.0025,
       "segs": "\n      ".join(seg), "sx": sx, "sy": sy, "fovy": float(fovy_deg), "hover": hover, "kt": k_trans, "kr": k_rot,
       "ky": k_yaw, "mL": -L}


# ======================================================================================================================
# 5. mujoco 層(facade のみ)
def _mujoco():
    try:
        import mujoco
    except ImportError as exc:
        raise ImportError("pegsym: this function needs the optional dependency mujoco (pip install mujoco)") from exc
    return mujoco


def pegsym_scene_build(peg_vertices, hole_vertices, **kw) -> dict:
    """MuJoCo の場面を組む(mujoco が要る): :func:`pegsym_scene_mjcf` をコンパイルし、名前 → id の表と一緒に返す。``kw`` は MJCF の引数。
    返り ``model``・``data``・``ids``(peg / tip / top / hole_center / cam_wrist / cam_up / 関節の qpos 添字 ``qadr`` / アクチュエータ ``act``)・
    ``peg_vertices``・``hole_vertices``・``kw``。**Raises** ImportError: mujoco が無い。"""
    mujoco = _mujoco()
    xml = pegsym_scene_mjcf(peg_vertices, hole_vertices, **kw)
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    g = mujoco.mj_name2id
    O = mujoco.mjtObj
    ids = {"peg": g(m, O.mjOBJ_GEOM, "peg"), "tip": g(m, O.mjOBJ_SITE, "tip"), "top": g(m, O.mjOBJ_SITE, "peg_top"),
           "hole_center": g(m, O.mjOBJ_SITE, "hole_center"), "cam_wrist": g(m, O.mjOBJ_CAMERA, "wrist"),
           "cam_up": g(m, O.mjOBJ_CAMERA, "up"), "floor": g(m, O.mjOBJ_GEOM, "hole_floor"),
           "peg_body": g(m, O.mjOBJ_BODY, "wrist")}
    jn = ["cx", "cy", "cz", "cyaw", "wx", "wy", "wz", "wrx", "wry", "wrz"]
    ids["qadr"] = {n: int(m.jnt_qposadr[g(m, O.mjOBJ_JOINT, n)]) for n in jn}
    ids["act"] = {n: g(m, O.mjOBJ_ACTUATOR, n) for n in ("ax", "ay", "az", "ayaw")}
    return {"model": m, "data": d, "ids": ids, "peg_vertices": _poly(peg_vertices, "pegsym_scene_build"),
            "hole_vertices": _poly(hole_vertices, "pegsym_scene_build"), "kw": dict(kw), "xml": xml}


def pegsym_scene_close(scene) -> None:
    """描画器を閉じる(持っていなければ何もしない)。"""
    ren = scene.pop("_ren", None)
    if ren is not None:
        ren.close()


def _cam_cv(m, d, cid):
    Rw = d.cam_xmat[cid].reshape(3, 3) @ np.diag([1.0, -1.0, -1.0])       # OpenCV カメラ → 世界
    return Rw.T, -Rw.T @ d.cam_xpos[cid]


def _peg_yaw(scene):
    """ペグの世界での yaw(本体の x 軸の水平の向き)と先端位置。"""
    d, ids = scene["data"], scene["ids"]
    xm = d.xmat[ids["peg_body"]].reshape(3, 3)
    return math.atan2(xm[1, 0], xm[0, 0]), d.site_xpos[ids["tip"]].copy()


def _settle(scene, seconds):
    mujoco = _mujoco()
    m, d = scene["model"], scene["data"]
    for _ in range(int(round(seconds / m.opt.timestep))):
        mujoco.mj_step(m, d)


def _move(scene, x, y, z_tip, yaw, seconds=0.25):
    """搬送台の目標を「先端の位置 (x, y, z_tip) と yaw」で置き、seconds だけ進める(ばねのたわみは無視した目標)。"""
    m, d, ids = scene["model"], scene["data"], scene["ids"]
    L = scene["kw"].get("peg_length", 40.0e-3)
    hover = L + 10e-3
    d.ctrl[ids["act"]["ax"]] = x
    d.ctrl[ids["act"]["ay"]] = y
    d.ctrl[ids["act"]["az"]] = (z_tip + L) - hover
    d.ctrl[ids["act"]["ayaw"]] = yaw
    _settle(scene, seconds)


def pegsym_views(scene, extent: float = 0.024, res: float = 0.06e-3, peg_station_height: float = 0.03) -> dict:
    """2 枚の画像を撮って上から見た図に打ち直す(mujoco が要る): (1) 搬送台を穴の上へずらして(手首カメラが穴の真上)穴の口の平面 z = 0、
    (2) ペグの先端を上向きカメラの ``peg_station_height`` 上へ運んで先端面の平面(先端の z は運動学から)。撮った後は元の指令に戻さない
    (呼び手が次の指令を出す)。返り ``hole_view``・``peg_view``(:func:`plane_topview`)、``rgb_hole``・``rgb_peg``、``truth``
    (穴の yaw は場面の作り方から 0 とは限らないので、真値はペグの世界 yaw と穴の頂点列から呼び手が計算する —— ここではペグの yaw と先端)。"""
    mujoco = _mujoco()
    m, d, ids = scene["model"], scene["data"], scene["ids"]
    kw = scene["kw"]
    W, H = kw.get("image_size", (480, 480))
    if "_ren" not in scene:
        scene["_ren"] = mujoco.Renderer(m, height=int(H), width=int(W))
    ren = scene["_ren"]
    import render3d
    yaw_cmd = float(d.ctrl[ids["act"]["ayaw"]])
    # (1) 手首カメラを穴の真上へ(カメラは搬送台の −30 mm x)
    _move(scene, 0.03, 0.0, 0.03, yaw_cmd, 0.4)
    ren.update_scene(d, camera="wrist")
    rgb_h = ren.render().copy()
    cid = ids["cam_wrist"]
    K = render3d.intrinsics_from_fov(float(m.cam_fovy[cid]), int(W), int(H))
    Rh, th = _cam_cv(m, d, cid)
    hole_view = plane_topview(rgb_h, K, Rh, th, z=0.0, centre=(0.0, 0.0), extent=extent, res=res)
    # (2) ペグを上向きカメラの上へ
    sx, sy = kw.get("station", (0.10, 0.0))
    _move(scene, sx, sy, peg_station_height, yaw_cmd, 0.5)
    ren.update_scene(d, camera="up")
    rgb_p = ren.render().copy()
    cid = ids["cam_up"]
    Ku = render3d.intrinsics_from_fov(float(m.cam_fovy[cid]), int(W), int(H))
    Ru, tu = _cam_cv(m, d, cid)
    yaw_p, tip = _peg_yaw(scene)
    peg_view = plane_topview(rgb_p, Ku, Ru, tu, z=float(tip[2]), centre=(float(tip[0]), float(tip[1])), extent=extent, res=res)
    return {"hole_view": hole_view, "peg_view": peg_view, "rgb_hole": rgb_h, "rgb_peg": rgb_p, "peg_yaw": yaw_p, "tip": tip}


def _contact_force(scene):
    mujoco = _mujoco()
    m, d, ids = scene["model"], scene["data"], scene["ids"]
    f6 = np.zeros(6)
    tot = 0.0
    for i in range(d.ncon):
        c = d.contact[i]
        if ids["peg"] in (int(c.geom1), int(c.geom2)):
            mujoco.mj_contactForce(m, d, i, f6)
            tot += float(f6[0])
    return tot


def pegsym_insert_try(scene, xy=(0.0, 0.0), yaw: float = 0.0, v: float = 10e-3, f_max: float = 6.0, success_depth: float = 6e-3,
                      t_max: float = 1.6, record: bool = False) -> dict:
    """1 回の挿入の試み(mujoco が要る、規則だけ): 先端を口の 3 mm 上・横 ``xy``・搬送台の yaw ``yaw`` に構え、``v`` [m/s] で下げる。
    先端の深さ(口から)≥ ``success_depth`` で成功、接触の法線力の和が ``f_max`` を超えて 0.15 s 進まなければ失敗(面取りか襟の上で止まった)、
    ``t_max`` で timeout。終わったら口の 3 mm 上へ戻す(成功でも戻すかは呼び手: ``lift`` は返りの後に :func:`_move` で)。
    返り ``success``・``depth``(最大、m)・``peg_yaw_final``(ペグの世界 yaw、面取りが回した後)・``max_force``・``t``・``frames``(record)。"""
    m, d, ids = scene["model"], scene["data"], scene["ids"]
    x, y = float(xy[0]), float(xy[1])
    _move(scene, x, y, 3e-3, float(yaw), 0.35)
    dt = float(m.opt.timestep)
    z_cmd = 3e-3
    best, t, stuck_since, fmax = -1.0, 0.0, None, 0.0
    frames = []
    status = "timeout"
    while t < t_max:
        F = _contact_force(scene)
        fmax = max(fmax, F)
        _, tip = _peg_yaw(scene)
        depth = -float(tip[2])
        if depth > best + 1e-5:
            best = depth
            stuck_since = None
        elif F > f_max and stuck_since is None:
            stuck_since = t
        if depth >= success_depth:
            status = "success"
            break
        if stuck_since is not None and t - stuck_since > 0.15:
            status = "stuck"
            break
        if F <= f_max:
            z_cmd -= v * dt * 20
        _move(scene, x, y, z_cmd, float(yaw), 20 * dt)
        t += 20 * dt
        if record and len(frames) < 400:
            frames.append(d.qpos.copy())
    yaw_f, tip = _peg_yaw(scene)
    out = {"success": status == "success", "status": status, "depth": max(best, -float(tip[2])), "peg_yaw_final": yaw_f,
           "max_force": fmax, "t": t, "frames": frames}
    _move(scene, x, y, 3e-3, float(yaw), 0.3)
    return out


def pegsym_search_run(scene, n_sym: int, phi_cap: float, hole_yaw: float, peg_yaw0: float = 0.0, estimate: float = 0.0,
                      order: str = "alternate", max_tries: int | None = None, xy=(0.0, 0.0), log=None, record: bool = False) -> dict:
    """規則だけの回転の探索(mujoco が要る): :func:`rotation_search_plan` の候補を順に試す(各候補 = 搬送台の yaw = peg_yaw0 からの補正)。
    ``estimate`` は画像の読み(:func:`relative_yaw_from_images` の −delta)。成功した試行の番号を返す。真値の誤差
    e = symmetry_fold(hole_yaw − peg_yaw0 − estimate, n_sym) も返す(門で閉形式の期待と比べる)。
    返り ``tries``(成功までの回数、失敗なら None)、``e_true``、``rows``(試行ごと、``record`` なら qpos の列 ``frames``)。"""
    plan = rotation_search_plan(n_sym, phi_cap, estimate, order)
    rows = []
    tries = None
    mt = len(plan["angles"]) if max_tries is None else int(max_tries)
    for k, a in enumerate(plan["angles"][:mt]):
        r = pegsym_insert_try(scene, xy=xy, yaw=float(a), record=record)
        rows.append({"k": k + 1, "yaw_cmd": float(a), "status": r["status"], "depth": r["depth"], "max_force": r["max_force"],
                     "frames": r["frames"]})
        if log:
            log("    try %d yaw %+.1f deg -> %s depth %.2f mm" % (k + 1, math.degrees(a), r["status"], 1e3 * r["depth"]))
        if r["success"]:
            tries = k + 1
            break
        _move(scene, xy[0], xy[1], 8e-3, float(a), 0.2)
    e = symmetry_fold(float(hole_yaw) - float(peg_yaw0) - float(estimate), int(n_sym)) if int(n_sym) >= 1 else 0.0
    return {"tries": tries, "e_true": e, "rows": rows, "M": plan["M"]}


def pegsym_two_point_depth_sim(scene, theta: float, tilt_dir: float = 0.0, depth_max: float = 0.019) -> float:
    """二点接触の深さ l₂ を接触計算から(mujoco が要る、:func:`polygon_two_point_depth` の第 2 実装): ペグを運動学的に置き(傾き θ を
    向き ``tilt_dir`` へ、先端の中心を最狭部から深さ l)、横位置を「どの壁とも mj_geomDistance > 0 になる平行移動」が残るかで判定 ——
    平行移動は壁ごとの符号付き距離の最小を最大にするパターン探索(16 方向、歩幅を半分ずつ)。境の l を二分法で(26 段)。"""
    mujoco = _mujoco()
    m, d, ids = scene["model"], scene["data"], scene["ids"]
    W = scene["kw"].get("chamfer", 0.5e-3)
    L = scene["kw"].get("peg_length", 40.0e-3)
    walls = [i for i in range(m.ngeom) if (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i) or "").startswith("wall")]
    fromto = np.zeros(6)
    Rm = _tilt_matrix(float(theta), float(tilt_dir))
    # 関節で置く代わりに geom の位置・姿勢を直接書いて距離だけ取る(mj_geomDistance は geom_xpos / geom_xmat を読む)
    g = ids["peg"]
    mujoco.mj_forward(m, d)
    Rg = np.zeros(9)
    mujoco.mju_quat2Mat(Rg, m.geom_quat[g])
    Rg = Rg.reshape(3, 3)
    gp = np.array(m.geom_pos[g], np.float64)                  # コンパイラはメッシュを重心へ寄せ、geom の位置で埋め合わせる

    def place(tx, ty, depth):
        tip = np.array([tx, ty, -(W + depth)])
        body = tip + Rm[:, 2] * L                             # 本体の原点 = ペグの上端(先端は本体系で (0, 0, −L))
        d.geom_xpos[g] = body + Rm @ gp
        d.geom_xmat[g] = (Rm @ Rg).reshape(-1)

    def min_dist(tx, ty, depth):
        place(tx, ty, depth)
        return min(float(mujoco.mj_geomDistance(m, d, g, w, 0.01, fromto)) for w in walls)


    # 16 方向(傾きの向きを含む): 最小距離の稜は斜めに走るので、軸方向だけの座標降下は対角の傾きで局所解に止まる(試作で 4.9 mm ずれた)
    dirs = np.array([(math.cos(float(tilt_dir) + k * math.pi / 8), math.sin(float(tilt_dir) + k * math.pi / 8)) for k in range(16)])

    def best_margin(depth):
        tx = ty = 0.0
        step = 0.4e-3
        cur = min_dist(tx, ty, depth)
        for _ in range(60):
            moved = False
            for dx, dy in dirs * step:
                v_ = min_dist(tx + dx, ty + dy, depth)
                if v_ > cur:
                    tx, ty, cur, moved = tx + dx, ty + dy, v_, True
                    break
            if not moved:
                step *= 0.5
                if step < 1e-7:
                    break
        return cur

    lo, hi = 0.0, float(depth_max)
    if best_margin(lo) <= 0:
        raise ValueError("pegsym_two_point_depth_sim: the tilted peg does not enter at the narrowest section")
    if best_margin(hi) > 0:
        raise ValueError("pegsym_two_point_depth_sim: no two-point contact down to depth_max")
    for _ in range(26):
        mid = 0.5 * (lo + hi)
        if best_margin(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
