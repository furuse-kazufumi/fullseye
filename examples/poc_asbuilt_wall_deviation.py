# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""室内の壁が設計どおりに建ったか —— 外接直方体は寸法でなく**部屋の向き**を測る。

改修・内装・什器の製作では、竣工した部屋の**内法寸法・壁の倒れ(垂直度)・
隅の直交度・面のふくらみ**が要ります(Scan-to-BIM の as-built 検査)。点群は
1 部屋 30 秒で取れるのに、そこから出す 4 つの数字がどこで嘘になるかは
測ってみないと分かりません。ここでは施工誤差も測定の癖も**すべて既知の量**で
仕込み、素朴なやり方と平面当てはめを同じ点群の上で突き合わせます。

EXTEND: 実スキャンに差し替えるなら :func:`make_room` が返す辞書の ``walls``
(壁ごとの点群)を、実機の点群 + 壁面の切り出し(``plane_segmentation`` か
BIM 案内)に置き換えます。真値のうち **倒れと直交度は下げ振り・レーザー
レベル・トータルステーションの基準点で部分的に取れます**が、面のふくらみの
真値は取れません(基準面が無い)—— 実物では「平面当てはめの残差」が
ふくらみの**下限**であって真値ではない、という §6 の関係だけが残ります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(点群の AABB = 外接直方体から内法を読む)は、傾いた壁で必ず
   過大になる**。東西 +19.1 mm / 南北 +34.6 mm(許容 ±10 mm)に対し、
   平面 2 枚の距離は +2.2 / -0.0 mm。★AABB の値は**測る前に閉形式で書ける**:
   倒れ + ふくらみ 10.0 mm + **雑音の最大値統計 2σ√(2 ln N) = 11.9 mm**。
   予測 +21.9 mm は上界(2 つの最大値が同じ点で起きるとした)なので、
   実測 +19.1 mm はいつもその少し内側に出る。
2. ★★**AABB が測っているのは寸法ではなく「部屋が走査軸に対してどれだけ
   傾いているか」**。部屋を ψ = 0.5 度回すだけで +46.8 mm、1 度で +80.1 mm、
   10 度で +611.1 mm。閉形式 W cosψ + D sinψ - W(+34.7 / +68.9 / +603.4 mm)
   と同じ形で伸びる。同じ点群から出した平面 2 枚の距離は **ψ を振っても
   +2.24 mm から 1 桁も動かない**(0.01 mm 未満)。
3. ★**AABB は点を増やすほど大きくなる —— 一致推定量ですらない**。壁 1 枚
   200 点で +14.9 mm、51200 点(256 倍)で +19.7 mm。最大値統計は
   √(2 ln N) でしか収束しないので、**「測点を増やす」という普通の対策が
   逆に効く**。閉形式は上界なので絶対値は 3.5〜4.9 mm 高いが、**伸び方**は
   予測 4.2 mm / 実測 4.8 mm(差 0.6 mm)で当たる。
4. **倒れは平面の法線から 0.02 mrad で出る**(west 真値 1.20 → 1.22、
   south 0.50 → 0.50、north 9.00 → 9.01 mrad)。★**予想が外れたのは
   「倒れが直交度に漏れる」のほう** —— 3-D の二面角と平面図に落とした角の差は
   最大 0.045 mrad で、2 次の効果として無視できた。**ただし AABB からは
   直交度が原理的に出ない**(軸平行なので常に 90 度)。
5. ★★**漏らしていたのは倒れではなく、面のふくらみ 1 個だった**。東の壁だけが
   倒れを -1.258 mrad 外し(他の 3 枚は 0.02 mrad 以内)、east-north の
   直交度を +0.500 mrad 押し、内法を +2.2 mm 広げる。**3 つとも別々の判定
   なのに、原因は 1 つ**。しかもどれも閉形式で予測できる —— ふくらみの場を
   {1, η, ζ} へ射影した係数がそのまま偽の倒れ -1.197 mrad / 偽の振れ
   +0.480 mrad / 平均 +2.3 mm になる(実測との差はそれぞれ 0.06 mrad /
   0.02 mrad / 0.1 mm)。
6. ★★**外れ点への壊れ方は 2 種類あり、1 つの数字では片方しか見えない**。
   出 450 mm の棚を東の壁の前に置き、点の割合を振る。**最小二乗は 2 % で
   もう壊れている**(4.77 → 17.83 mrad)。10 % で 66.3 mrad = 真値の 11 倍、
   45 % で 189.5 mrad。混合分布のモーメントから書いた閉形式
   ``Cov(dev,ζ)/Var(ζ)`` の予測(17.97 / 63.79 / 184.53)と **4 % 以内**。
   RANSAC は 45 % まで 4.7 mrad で踏みとどまり、**55 % で棚へ乗り換える**
   (予測 50 % = 棚の点が壁を上回る点)。★崖の向こうで**倒れの誤差は
   0.13 mrad と小さいまま**、面そのものは 449.9 mm 手前にある —— 倒れだけを
   見ていると破綻に気づけないので、**面の位置ずれを別に数える**。
7. ★★**広いふくらみほど「平ら」と報告される**。振幅 9 mm 固定で広がり σ を
   振ると、平面に吸われる割合は σ=0.25 m で 5.0 %、σ=3.00 m で 90.1 %。
   雑音を切った残差の山は 7.99 → 0.86 mm で、閉形式と最大 0.56 mm で一致。
   **壁全体が出ているという一番危ない状態が、一番見えない**。
8. ★★**崖は「吸われる量」ではなく雑音の床との交点にある**。ふくらみゼロの
   壁でも同じ読み方(上位 0.5 % の中央値)で **4.17 mm** 出る。σ >= 1.10 m で
   真の残差がこの床を下回るので、σ=3.00 m の読み 4.38 mm は**中身が全部
   雑音**—— ふくらみが 9 mm あっても 0 mm あっても同じ数字になる。
   吸われた分は消えず**倒れへ移る**(偽の倒れ最大 -1.33 mrad = 階高 3.6 mm
   = 許容 5 mm の 72 %)。

【グラウンドトゥルース】内法 6.000 x 4.000 x 2.700 m、基準高さ 1.35 m。
倒れ west 1.20 / east 6.00 / south 0.50 / north 9.00 mrad(正 = 上で外へ)。
平面図の振れ north +5.00 mrad(= 直交度の真値)。東の壁の面外のふくらみ
振幅 9.0 mm・σ 0.70 m・中心 (η, ζ) = (+0.30, -0.45) m。測距の雑音は
面の法線方向に σ = 1.5 mm。家具は出 450 mm・幅 1.6 m・高さ 0.05〜0.80 m の
**完全に鉛直な**前面(乗り換えの壊れ方を倒れの誤差から分離するため)。
許容は内法 ±10 mm / 倒れ 階高あたり 5 mm / 直交度 3 mrad。

★同じ室内点群を扱う `poc_scan_to_bim_asbuilt` とは測る軸が違います。あちらは
**設計モデルへ合わせる段階**(剛体モードが吸われて他の部材へ配られる)、
こちらは**合わせる前に点群だけから壁を出す段階**(素朴な外接直方体・直交度・
外れ点への頑健性・面の偏差の吸収)を測っています。

来歴(公開文献のみ): JIS A 3301 / 建築工事標準仕様書系の施工精度の考え方 /
Fischler & Bolles, *Random Sample Consensus*, CACM 24 (1981) 381 —— RANSAC の
破綻点 / Rousseeuw & Leroy, *Robust Regression and Outlier Detection*
(Wiley, 1987) —— 最小二乗の破綻点は 0 / Leadbetter, Lindgren & Rootzén,
*Extremes and Related Properties of Random Sequences* (Springer, 1983) ——
標本最大値の √(2 ln N) 則 / Bosché, *Automated recognition of 3D CAD model
objects in laser scans*, Adv. Eng. Informatics 24 (2010) 107。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L = fs.ledger

# --- 部屋の設計 -------------------------------------------------------------- #
RW, RD, RH = 6.000, 4.000, 2.700     # 内法 幅(東西) / 奥行(南北) / 階高 [m]
ZREF = RH / 2.0                      # 寸法を読む基準の高さ [m](= 1.35 m)

# --- 施工誤差の真値 ---------------------------------------------------------- #
#: 壁ごとの倒れ(鉛直からの傾き)[rad]。正 = 上で外へ倒れる。
TILT = {"west": 0.0012, "east": 0.0060, "south": 0.0005, "north": 0.0090}
#: 壁ごとの平面内の振れ(平面図での向きの狂い)[rad]。直交度はこの差で決まる。
YAW = {"west": 0.0, "east": 0.0, "south": 0.0, "north": 0.0050}
#: 東の壁の面外のふくらみ(振幅 [m]、広がり σ [m]、中心 (η,ζ) [m])
BULGE_A, BULGE_S = 0.0090, 0.70
BULGE_C = (0.30, -0.45)              # 壁の中心から見た位置(η=水平, ζ=z-ZREF)

# --- 測定の癖 ---------------------------------------------------------------- #
SIG = 0.0015                         # 測距の雑音 σ [m](面の法線方向)
N_WALL = 2500                        # 壁 1 枚あたりの点数
SEED = 5

# --- 家具(外れ点)------------------------------------------------------------ #
CAB_D = 0.450                        # 東の壁の前に立つ棚の出 [m]
CAB_ETA = (-1.00, 0.60)              # 棚の水平範囲(壁中心からの η)[m]
CAB_Z = (0.05, 0.80)                 # 棚の高さ範囲 [m]

# --- 許容 -------------------------------------------------------------------- #
TOL_PLUMB_MM = 5.0                   # 階高あたりの倒れの許容 [mm]
TOL_DIM_MM = 10.0                    # 内法寸法の許容 [mm]
TOL_SQUARE_MRAD = 3.0                # 直交度の許容 [mrad]

#: 壁の諸元 —— (法線の平面内向き u, 面内水平 t, 面の中心の平面位置, 壁の幅)
WALLS = {
    "west":  ((-1.0, 0.0), (0.0, -1.0), (0.0, RD / 2), RD),
    "east":  ((+1.0, 0.0), (0.0, +1.0), (RW, RD / 2), RD),
    "south": ((0.0, -1.0), (+1.0, 0.0), (RW / 2, 0.0), RW),
    "north": ((0.0, +1.0), (-1.0, 0.0), (RW / 2, RD), RW),
}


# --------------------------------------------------------------------------- #
# 場面を作る —— 真値は「仕込んだ倒れ・振れ・ふくらみ」                          #
# --------------------------------------------------------------------------- #
def _rot_z(v2, ang):
    """平面内のベクトルを角 ``ang`` [rad] だけ回す。"""
    c, s = np.cos(ang), np.sin(ang)
    return np.array([c * v2[0] - s * v2[1], s * v2[0] + c * v2[1]])


def bulge_field(eta, zeta, amp=BULGE_A, sig=BULGE_S):
    """東の壁の面外のふくらみ [m]。面内座標 (η, ζ) のガウス。"""
    e0, z0 = BULGE_C
    return amp * np.exp(-((eta - e0) ** 2 + (zeta - z0) ** 2) / (2.0 * sig * sig))


def true_normal(name: str) -> np.ndarray:
    """仕込んだ壁面の**真の法線**(単位、外向き)。ふくらみは含まない。"""
    u2 = _rot_z(WALLS[name][0], YAW[name])
    n = np.array([u2[0], u2[1], -TILT[name]])
    return n / np.linalg.norm(n)


def make_wall(name: str, n_pts: int = N_WALL, rng=None, sig: float = SIG,
              tilt: float | None = None, amp: float = BULGE_A,
              bsig: float = BULGE_S, clutter_frac: float = 0.0,
              jitter_free: bool = False) -> dict:
    """壁 1 枚の点群と、その点の面内座標・真の偏差を返す。

    ``clutter_frac`` は**全点に占める家具の割合**(0.2 なら 5 点に 1 点が棚の前面)。
    棚の前面は完全に鉛直に立てる —— そうしないと「頑健推定が棚に乗り換えた」
    ときの壊れ方が倒れの誤差に混ざって見えなくなる。
    """
    rng = np.random.default_rng(SEED if rng is None else rng)
    u2, t2, base2, width = WALLS[name]
    tau = TILT[name] if tilt is None else tilt
    ug = _rot_z(u2, YAW[name])
    tg = _rot_z(t2, YAW[name])
    u3 = np.array([ug[0], ug[1], 0.0])
    t3 = np.array([tg[0], tg[1], 0.0])
    base = np.array([base2[0], base2[1], 0.0])

    n_cl = int(round(n_pts * clutter_frac))
    n_w = n_pts - n_cl
    eta = rng.uniform(-width / 2, width / 2, n_w)
    zeta = rng.uniform(-RH / 2, RH / 2, n_w)
    dev = tau * zeta
    if name == "east" and amp > 0:
        dev = dev + bulge_field(eta, zeta, amp, bsig)
    eps = np.zeros(n_w) if jitter_free else rng.normal(0.0, sig, n_w)
    P = (base + np.outer(eta, t3) + np.outer(zeta + ZREF, (0.0, 0.0, 1.0))
         + np.outer(dev + eps, u3))
    is_cl = np.zeros(n_w, bool)

    if n_cl > 0:
        ce = rng.uniform(CAB_ETA[0], CAB_ETA[1], n_cl)
        cz = rng.uniform(CAB_Z[0], CAB_Z[1], n_cl)
        cd = np.full(n_cl, -CAB_D) + (0.0 if jitter_free else rng.normal(0, sig, n_cl))
        Q = (base + np.outer(ce, t3) + np.outer(cz, (0.0, 0.0, 1.0))
             + np.outer(cd, u3))
        P = np.vstack([P, Q])
        eta = np.concatenate([eta, ce])
        zeta = np.concatenate([zeta, cz - ZREF])
        dev = np.concatenate([dev, np.full(n_cl, -CAB_D)])
        is_cl = np.concatenate([is_cl, np.ones(n_cl, bool)])
    return {"P": P, "eta": eta, "zeta": zeta, "dev": dev, "clutter": is_cl,
            "u": u3, "t": t3, "base": base, "width": width, "tau": tau}


def make_room(rng_seed: int = SEED, n_pts: int = N_WALL, sig: float = SIG,
              yaw_room: float = 0.0) -> dict:
    """4 枚の壁をまとめた室内点群。``yaw_room`` は**部屋ごと**走査軸に対して回す。"""
    rng = np.random.default_rng(rng_seed)
    walls = {k: make_wall(k, n_pts, rng, sig) for k in WALLS}
    P = np.vstack([w["P"] for w in walls.values()])
    if yaw_room != 0.0:
        c, s = np.cos(yaw_room), np.sin(yaw_room)
        R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        P = P @ R.T
        for w in walls.values():
            w["P"] = w["P"] @ R.T
            w["u"] = R @ w["u"]
    return {"P": P, "walls": walls}


# --------------------------------------------------------------------------- #
# 測る —— 平面を取り出して倒れ・直交度・寸法を出す                              #
# --------------------------------------------------------------------------- #
def fit_wall(P: np.ndarray, robust: bool = True, thresh: float = 0.008,
             seed: int = 0) -> dict:
    """壁の平面。``robust=True`` は RANSAC、False は最小二乗。"""
    if robust:
        par, mask, info = L.ransac_plane(P, thresh=thresh, iters=300, seed=seed)
        n = np.asarray(par["normal"], float)
        pt = np.asarray(par["point"], float)
        return {"normal": n / np.linalg.norm(n), "point": pt,
                "inliers": int(mask.sum()), "mask": mask}
    r = L.fit_plane3(P)
    n = np.asarray(r["normal"], float)
    return {"normal": n / np.linalg.norm(n), "point": np.asarray(r["center"], float),
            "inliers": len(P), "mask": np.ones(len(P), bool)}


def plumb_mrad(normal: np.ndarray) -> float:
    """壁面の**倒れ**[mrad] —— 鉛直線と壁面のなす角(``angle_line_plane``)。"""
    return float(np.deg2rad(L.angle_line_plane(np.array([0.0, 0.0, 1.0]),
                                               np.asarray(normal, float)))) * 1e3


def plan_dir(normal: np.ndarray) -> np.ndarray:
    """法線の**水平成分**(単位)。直交度はここで測る(倒れを混ぜないため)。"""
    h = np.asarray(normal, float)[:2].copy()
    nrm = np.linalg.norm(h)
    return h / nrm if nrm > 1e-12 else np.array([1.0, 0.0])


def squareness_mrad(n1: np.ndarray, n2: np.ndarray) -> float:
    """2 枚の壁の**平面図での**直交度のずれ [mrad](0 = 直角)。"""
    a, b = plan_dir(n1), plan_dir(n2)
    ang = np.arccos(np.clip(abs(float(a @ b)), 0.0, 1.0))   # [0, π/2]
    return float(np.pi / 2 - ang) * 1e3


def signed_offset(pt_on_plane: np.ndarray, normal: np.ndarray,
                  q: np.ndarray) -> float:
    """基準点 q から壁面までの距離 [m](``distance_point_plane``)。"""
    return float(L.distance_point_plane(np.asarray(q, float),
                                        np.asarray(pt_on_plane, float),
                                        np.asarray(normal, float)))


# --------------------------------------------------------------------------- #
# 図のための小道具                                                              #
# --------------------------------------------------------------------------- #
def _residual(w: dict, f: dict) -> np.ndarray:
    """点の面からの残差 [m]。**外向きが正**になるよう向きを揃える。

    ``ransac_plane`` も ``fit_plane3`` も法線の**符号は任意**なので、
    そのまま塗ると同じふくらみが図によって青にも橙にもなる。
    """
    n = f["normal"] * (1.0 if float(f["normal"] @ w["u"]) >= 0 else -1.0)
    return (w["P"] - f["point"]) @ n


def _bin_mean(u, v, w, ru, rv, nu, nv, up=1):
    """散らばった (u, v, 値) を格子に落として平均する(空セルは 0)。

    ★格子を細かく取りすぎると空セルだらけになって図が真っ黒になる
    (2026-09-08 に 420x290 で踏んだ)。粗く落としてから ``up`` 倍に
    引き伸ばすほうが、点の密度に対して素直。
    """
    iu = np.clip(((u - ru[0]) / (ru[1] - ru[0]) * nu).astype(int), 0, nu - 1)
    iv = np.clip(((v - rv[0]) / (rv[1] - rv[0]) * nv).astype(int), 0, nv - 1)
    k = iv * nu + iu
    s = np.bincount(k, weights=w, minlength=nu * nv)
    c = np.bincount(k, minlength=nu * nv)
    out = np.where(c > 0, s / np.maximum(c, 1), 0.0).reshape(nv, nu)[::-1]
    return np.repeat(np.repeat(out, up, axis=0), up, axis=1) if up > 1 else out


# --------------------------------------------------------------------------- #
# 1. ゼロ点 —— 外接直方体(AABB)から寸法を出す                                  #
# --------------------------------------------------------------------------- #
def predict_aabb(n_pts: int = N_WALL, sig: float = SIG) -> dict:
    """AABB の x 方向の幅を**測る前に**予測する(閉形式)。

    3 つの足し算: (a) 倒れ —— 東西の壁が上で外へ出る分 τ·H/2、(b) ふくらみ ——
    面外へ出た最大値、(c) **雑音の最大値統計** —— N 点の N(0,σ) の最大値は
    σ√(2 ln N) で伸びる。(c) が肝で、**点を増やすほど AABB は大きくなる**。
    """
    grid_e = np.linspace(-RH / 2, RH / 2, 401)
    eta_e = np.linspace(-RD / 2, RD / 2, 401)
    EE, ZZ = np.meshgrid(eta_e, grid_e)
    out_e = float(np.max(TILT["east"] * ZZ + bulge_field(EE, ZZ)))
    out_w = float(np.max(TILT["west"] * grid_e))
    noise = sig * np.sqrt(2.0 * np.log(max(n_pts, 2)))
    return {"tilt_bulge": out_e + out_w, "noise": 2.0 * noise,
            "width": RW + out_e + out_w + 2.0 * noise}


#: 2 つの最大値が同じ点で起きると仮定した上界なので、実測はこれより少し小さい。
AABB_PRED_IS_UPPER_BOUND = True


def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— 点群の外接直方体(AABB)から内法寸法を出す")
    print("=" * 78)

    room = make_room()
    lo, hi = L.aabb(room["P"])
    size = hi - lo
    pr = predict_aabb()
    q = np.array([RW / 2, RD / 2, ZREF])
    dim_pl = {}
    for pair, axis in ((("west", "east"), 0), (("south", "north"), 1)):
        d = 0.0
        for k in pair:
            f = fit_wall(room["walls"][k]["P"], seed=3)
            d += signed_offset(f["point"], f["normal"], q)
        dim_pl[axis] = d

    print("  真値(基準高さ %.2f m での内法) 東西 %.4f m / 南北 %.4f m" % (ZREF, RW, RD))
    print("  AABB            東西 %.4f m (%+6.1f mm) / 南北 %.4f m (%+6.1f mm)" % (
        size[0], 1e3 * (size[0] - RW), size[1], 1e3 * (size[1] - RD)))
    print("  平面 2 枚の距離  東西 %.4f m (%+6.1f mm) / 南北 %.4f m (%+6.1f mm)" % (
        dim_pl[0], 1e3 * (dim_pl[0] - RW), dim_pl[1], 1e3 * (dim_pl[1] - RD)))
    pb = predict_bulge(BULGE_A, BULGE_S)
    print("\n  ★AABB の東西幅は**測る前に閉形式で予測できる**:")
    print("     倒れ + ふくらみ %.1f mm + 雑音の最大値統計 2σ√(2 ln N) = %.1f mm"
          "  -> 予測 %+.1f mm / 実測 %+.1f mm(差 %.1f mm)"
          % (1e3 * pr["tilt_bulge"], 1e3 * pr["noise"],
             1e3 * (pr["width"] - RW), 1e3 * (size[0] - RW),
             1e3 * abs(pr["width"] - size[0])))
    print("     予測は**上界**(2 つの最大値が同じ点で起きるとした)なので、"
          "実測はいつも少し内側に出る。")
    print("  ★平面法の残り %+.1f mm も測定誤差ではない —— ふくらみの平均 %+.1f mm"
          "(閉形式)が\n     面をそのぶん外へ押している。**面の偏差は寸法にも漏れる**。"
          % (1e3 * (dim_pl[0] - RW), 1e3 * pb["mean"]))

    # 場面の図: 上面図 + 東壁の偏差マップ
    P = room["P"]
    plan = _bin_mean(P[:, 0], P[:, 1], np.ones(len(P)), (-0.2, RW + 0.2),
                     (-0.2, RD + 0.2), 140, 96, up=3)
    # 偏差マップは点を多めに撒いた壁で描く(2500 点だと格子が埋まらない)
    ew = make_wall("east", 40000, np.random.default_rng(SEED))
    res = _residual(ew, fit_wall(ew["P"], seed=3))
    emap = _bin_mean(ew["eta"], ew["zeta"], res * 1e3, (-RD / 2, RD / 2),
                     (-RH / 2, RH / 2), 84, 58, up=5)
    figs.save_grid("scene", [plan, emap],
                   ["上面図(壁 4 枚 %d 点)" % len(P),
                    "東の壁の偏差 [mm](倒れ + ふくらみ %.0f mm)" % (1e3 * BULGE_A)],
                   title="室内点群と壁面(内法 %.1f x %.1f x %.1f m)"
                         % (RW, RD, RH), signed=[False, True], ncols=2)
    return {"aabb": size, "plane": dim_pl, "pred": pr}


def section_aabb_yaw() -> dict:
    print("\n" + "=" * 78)
    print("2) AABB は部屋の向きを測っている —— 走査軸に対する回転 ψ の掃引")
    print("=" * 78)
    print("   ψ [deg]   AABB 東西 [mm 誤差]   閉形式 W cosψ + D sinψ   平面法 [mm 誤差]")

    q0 = np.array([RW / 2, RD / 2, ZREF])
    psis, aabb_err, pred_err, plane_err = [], [], [], []
    for psi_deg in (0.0, 0.5, 1.0, 2.0, 5.0, 10.0):
        psi = np.deg2rad(psi_deg)
        room = make_room(yaw_room=psi)
        lo, hi = L.aabb(room["P"])
        pred = RW * np.cos(psi) + RD * np.sin(psi)
        c, s = np.cos(psi), np.sin(psi)
        R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        q = R @ q0
        d = 0.0
        for k in ("west", "east"):
            f = fit_wall(room["walls"][k]["P"], seed=3)
            d += signed_offset(f["point"], f["normal"], q)
        psis.append(psi_deg)
        aabb_err.append(1e3 * (hi[0] - lo[0] - RW))
        pred_err.append(1e3 * (pred - RW))
        plane_err.append(1e3 * (d - RW))
        print("   %6.1f    %+10.1f          %+10.1f              %+8.2f" % (
            psi_deg, aabb_err[-1], pred_err[-1], plane_err[-1]))
    print("\n  ★AABB は 1 度で %+.0f mm、10 度で %+.0f mm 外す —— これは施工誤差では"
          "なく\n     **部屋が走査軸に対して傾いていること**を測っている。"
          "平面法は最大 %.2f mm。" % (aabb_err[2], aabb_err[-1],
                                     max(abs(e) for e in plane_err)))
    print("     しかも平面法の読みは ψ を振っても **%.1e mm しか動かない**"
          "(回転に対して不変)。" % (max(plane_err) - min(plane_err)))

    figs.save_plot("aabb_vs_yaw",
                   [("AABB", psis, aabb_err),
                    ("閉形式 W cosψ + D sinψ - W", psis, pred_err),
                    ("平面 2 枚の距離", psis, plane_err)],
                   xlabel="部屋の向き ψ [deg]", ylabel="東西の内法の誤差 [mm]",
                   title="外接直方体は「部屋の向き」を寸法と取り違える",
                   caption="許容 ±%.0f mm。AABB は ψ=0.5 度で既に外れる。"
                           % TOL_DIM_MM)
    return {"psi": psis, "aabb": aabb_err, "plane": plane_err}


def section_aabb_n() -> dict:
    print("\n" + "=" * 78)
    print("3) ★AABB は点を増やすほど大きくなる —— 一致推定量ですらない")
    print("=" * 78)
    print("   壁 1 枚の点数    AABB 東西 [mm 誤差]   予測 2σ√(2 ln N) + 倒れ [mm]")

    ns, meas, pred = [], [], []
    for n in (200, 800, 3200, 12800, 51200):
        room = make_room(n_pts=n)
        lo, hi = L.aabb(room["P"])
        pr = predict_aabb(n_pts=n)
        ns.append(n)
        meas.append(1e3 * (hi[0] - lo[0] - RW))
        pred.append(1e3 * (pr["width"] - RW))
        print("   %8d        %+10.1f            %+10.1f" % (n, meas[-1], pred[-1]))
    g_m, g_p = meas[-1] - meas[0], pred[-1] - pred[0]
    print("\n  ★点を 256 倍にすると AABB は %+.1f -> %+.1f mm と %.1f mm 広がる。"
          % (meas[0], meas[-1], g_m))
    print("     最大値統計は N で対数的にしか収束しないので、**測点を増やす**"
          "という\n     普通の対策が逆に効く。")
    print("     予測は**上界**なので絶対値は常に %.1f〜%.1f mm 大きく出るが、"
          "**伸び方**は\n     当たっている(予測 %.1f mm / 実測 %.1f mm、差 %.1f mm)。"
          % (min(p - m for m, p in zip(meas, pred)),
             max(p - m for m, p in zip(meas, pred)), g_p, g_m, abs(g_p - g_m)))

    figs.save_plot("aabb_grows_with_points",
                   [("AABB の誤差(実測)", np.log10(ns), meas),
                    ("閉形式の予測", np.log10(ns), pred),
                    ("許容 +%.0f mm" % TOL_DIM_MM, np.log10(ns),
                     [TOL_DIM_MM] * len(ns))],
                   xlabel="log10(壁 1 枚の点数)", ylabel="東西の内法の誤差 [mm]",
                   title="点を増やすと外接直方体は必ず大きくなる")
    return {"n": ns, "meas": meas, "pred": pred}


# --------------------------------------------------------------------------- #
# 4. 垂直度と直交度                                                             #
# --------------------------------------------------------------------------- #
def section_plumb_square() -> dict:
    print("\n" + "=" * 78)
    print("4) 垂直度(倒れ)と直交度 —— 平面の法線から出す")
    print("=" * 78)
    print("   壁      真値 [mrad]  推定 [mrad]  差 [mrad]   階高 %.2f m あたり [mm]  判定"
          % RH)

    room = make_room()
    rows, fits = [], {}
    for k in ("west", "east", "south", "north"):
        f = fit_wall(room["walls"][k]["P"], seed=3)
        fits[k] = f
        est = plumb_mrad(f["normal"])
        tru = plumb_mrad(true_normal(k))
        mm = est * 1e-3 * RH * 1e3
        ok = "合格" if mm <= TOL_PLUMB_MM else "不合格"
        rows.append([k, "%.2f" % tru, "%.2f" % est, "%+.3f" % (est - tru),
                     "%.1f" % mm, ok])
        print("   %-6s   %8.2f     %8.2f    %+8.3f        %8.1f          %s" % (
            k, tru, est, est - tru, mm, ok))

    print("\n   直交する 2 面の組み合わせ(平面図での直交度)")
    sq_rows = []
    for a, b in (("east", "north"), ("north", "west"), ("west", "south"),
                 ("south", "east")):
        tru = squareness_mrad(true_normal(a), true_normal(b))
        est = squareness_mrad(fits[a]["normal"], fits[b]["normal"])
        d3 = 90.0 - float(L.angle_between_planes(fits[a]["normal"], fits[b]["normal"]))
        ok = "合格" if abs(est) <= TOL_SQUARE_MRAD else "不合格"
        sq_rows.append([a + "-" + b, "%.2f" % tru, "%.2f" % est,
                        "%.3f" % (d3 * np.pi / 180 * 1e3), ok])
        print("   %-12s 真値 %6.2f mrad / 推定 %6.2f mrad / "
              "3-D 二面角から %6.2f mrad   %s"
              % (a + "-" + b, tru, est, d3 * np.pi / 180 * 1e3, ok))
    leak = max(abs(float(r[3]) - float(r[2])) for r in sq_rows)
    print("\n  ★倒れが直交度に漏れると踏んでいたが、3-D の二面角と平面図の角の差は"
          "\n     最大 %.3f mrad —— 2 次の効果で無視できた(予想は外れ)。"
          "\n     ただし **AABB からは直交度が原理的に出ない**(軸平行なので"
          "常に 90 度)。" % leak)

    # ★漏れていたのは倒れではなく**ふくらみ**。閉形式で predict_bulge が
    #   1 次の係数として返す量が、そのまま偽の倒れと偽の平面内の振れになる。
    pb = predict_bulge(BULGE_A, BULGE_S)
    east_err = float([r for r in rows if r[0] == "east"][0][3])
    sq_err = float(sq_rows[0][2]) - float(sq_rows[0][1])
    print("\n  ★★漏れていたのは倒れではなく**東の壁のふくらみ**だった。")
    print("     東の壁の倒れ  実測 %+.3f mrad / 閉形式の予測 %+.3f mrad"
          % (east_err, 1e3 * pb["fake_tilt"]))
    print("     east-north の直交度  実測 %+.3f mrad / 閉形式の予測 %+.3f mrad"
          % (sq_err, 1e3 * pb["fake_yaw"]))
    print("     **面外のふくらみ 1 個が、倒れ・直交度・内法の 3 つの判定を"
          "同時に汚す**\n     (どれも §6 の 1 次の吸収で説明がつく)。")
    pl_extra = {"east_err": east_err, "sq_err": sq_err,
                "pred_tilt": 1e3 * pb["fake_tilt"], "pred_yaw": 1e3 * pb["fake_yaw"]}

    figs.save_table("plumb_verdicts",
                    ["壁", "真値 mrad", "推定 mrad", "差 mrad",
                     "階高あたり mm", "判定(許容 %.0f mm)" % TOL_PLUMB_MM],
                    rows, title="壁ごとの倒れ(垂直度)")
    figs.save_table("squareness",
                    ["組", "真値 mrad", "平面図の角 mrad", "3-D 二面角 mrad",
                     "判定(許容 %.0f mrad)" % TOL_SQUARE_MRAD],
                    sq_rows, title="隣り合う 2 面の直交度")
    return {"rows": rows, "sq": sq_rows, "leak": leak, **pl_extra}


# --------------------------------------------------------------------------- #
# 5. 家具(外れ点)—— 最小二乗と頑健推定                                        #
# --------------------------------------------------------------------------- #
def predict_ls_tilt(f: float, tau: float | None = None) -> float:
    """外れ点の割合 f のとき、**最小二乗**が読む倒れ [rad] を閉形式で。

    面内の高さ ζ = z - ZREF に対して偏差 dev を 1 次で当てはめると、傾きは
    ``Cov(dev, ζ) / Var(ζ)``。壁は ζ~U[-H/2, H/2] で dev = τζ、棚は
    ζ~U[ζ0,ζ1] で dev = -d。混合分布のモーメントは全部書けるので、
    **点を 1 つも作らずに**答えが出る。
    """
    tau = TILT["east"] if tau is None else tau
    d = CAB_D
    z0, z1 = CAB_Z[0] - ZREF, CAB_Z[1] - ZREF
    m1 = 0.5 * (z0 + z1)
    m2 = (z1 ** 3 - z0 ** 3) / (3.0 * (z1 - z0))
    ez = f * m1
    ez2 = (1 - f) * (RH ** 2 / 12.0) + f * m2
    cov = (1 - f) * tau * (RH ** 2 / 12.0) - f * (1 - f) * d * m1
    var = ez2 - ez * ez
    return cov / var


def section_outliers() -> dict:
    print("\n" + "=" * 78)
    print("5) 家具を何 %s 混ぜると平面が引きずられるか —— 最小二乗 vs RANSAC" % "%")
    print("=" * 78)
    print("  出 %.0f mm の棚を東の壁の前に立て、全点に占める割合を振る"
          "(棚の前面は完全に鉛直)" % (1e3 * CAB_D))
    print("\n   割合 %s   最小二乗 [mrad]  閉形式の予測   RANSAC [mrad]  "
          "RANSAC の面の位置ずれ [mm]" % "%")

    # ★閉形式には**ふくらみが吸われた分**(§6)を入れた実効の倒れを渡す。
    #   入れないと f=0 の 1 点だけが 1.2 mrad ずれ、予測が外れたように見える。
    tau_eff = TILT["east"] + predict_bulge(BULGE_A, BULGE_S)["fake_tilt"]
    tru = 1e3 * TILT["east"]
    fr, ls_e, ls_p, rs_e, rs_off = [], [], [], [], []
    rng_master = np.random.default_rng(101)
    for frac in (0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.45, 0.55, 0.70):
        w = make_wall("east", 4000, np.random.default_rng(int(rng_master.integers(1e6))),
                      clutter_frac=frac)
        fl = fit_wall(w["P"], robust=False)
        frb = fit_wall(w["P"], robust=True, seed=7)
        e_ls = plumb_mrad(fl["normal"])
        e_rs = plumb_mrad(frb["normal"])
        # 面の位置 —— 部屋の中心から東の壁までの距離。棚に乗り換えると 450 mm 縮む。
        q = np.array([RW / 2, RD / 2, ZREF])
        off = 1e3 * (signed_offset(frb["point"], frb["normal"], q) - RW / 2)
        pred = 1e3 * predict_ls_tilt(frac, tau_eff)
        fr.append(round(100 * frac, 1))
        ls_e.append(e_ls)
        ls_p.append(abs(pred))
        rs_e.append(e_rs)
        rs_off.append(off)
        print("   %5.0f    %10.2f     %10.2f     %10.2f        %+10.1f" % (
            100 * frac, e_ls, abs(pred), e_rs, off))

    print("\n   真値 %.2f mrad(ふくらみを吸った実効値 %.2f mrad —— 閉形式には"
          "こちらを渡す)。" % (tru, 1e3 * tau_eff))
    i10 = fr.index(10.0)
    print("  ★最小二乗は %.0f %s の混入で %.1f mrad(真値の %.0f 倍)。"
          "閉形式の予測 %.1f mrad と %.1f %s 以内で一致。"
          % (fr[i10], "%", ls_e[i10], ls_e[i10] / tru, ls_p[i10],
             100 * abs(ls_e[i10] - ls_p[i10]) / ls_p[i10], "%"))
    bad = [i for i, o in enumerate(rs_off) if abs(o) > 100.0]
    j = bad[0] if bad else len(fr) - 1
    if bad:
        print("  ★★RANSAC の崖は %.0f %s と %.0f %s のあいだ(予測 50 %s = 棚の点が"
              "壁を上回る点)。" % (fr[j - 1], "%", fr[j], "%", "%"))
        print("     ★崖の向こうで**倒れの誤差は小さいまま**(%.2f mrad)なのに、"
              "面そのものが\n        %.0f mm 手前の棚へ乗り換えている。"
              "1 つの数字(倒れ)では破綻が見えない。" % (rs_e[j], abs(rs_off[j])))

    figs.save_plot("outlier_sweep",
                   [("最小二乗(実測)", fr, ls_e),
                    ("最小二乗(閉形式)", fr, ls_p),
                    ("RANSAC(実測)", fr, rs_e),
                    ("真値 %.1f mrad" % tru, fr, [tru] * len(fr))],
                   xlabel="家具の点の割合 [%]", ylabel="読み取った倒れ [mrad]",
                   title="最小二乗は最初の 1 % で壊れ、RANSAC は 50 % で乗り換える")
    figs.save_plot("outlier_offset",
                   [("RANSAC が置いた面の位置ずれ", fr, rs_off),
                    ("許容 ±%.0f mm" % TOL_DIM_MM, fr, [-TOL_DIM_MM] * len(fr))],
                   xlabel="家具の点の割合 [%]", ylabel="壁面の位置ずれ [mm]",
                   title="壊れ方は 2 種類 —— 傾く(最小二乗)/ 乗り換える(RANSAC)")

    # 場面の図: 20 % 混入の東壁を、2 つの当てはめの残差で塗り分ける
    w = make_wall("east", 16000, np.random.default_rng(4242), clutter_frac=0.20)
    fl = fit_wall(w["P"], robust=False)
    frb = fit_wall(w["P"], robust=True, seed=7)
    maps = []
    for f in (fl, frb):
        r = _residual(w, f)
        maps.append(_bin_mean(w["eta"], w["zeta"], np.clip(r, -0.25, 0.25) * 1e3,
                              (-RD / 2, RD / 2), (-RH / 2, RH / 2), 84, 58, up=5))
    figs.save_grid("outlier_maps", maps,
                   ["最小二乗の残差 [mm](面が回った)",
                    "RANSAC の残差 [mm](棚だけ残る)"],
                   title="家具 20 %s を混ぜた東の壁(棚の出 %.0f mm)"
                         % ("%", 1e3 * CAB_D), signed=True)
    return {"frac": fr, "ls": ls_e, "pred": ls_p, "rs": rs_e, "off": rs_off}


# --------------------------------------------------------------------------- #
# 6. 面のふくらみ —— 平面当てはめが自分で食べてしまう分                         #
# --------------------------------------------------------------------------- #
def predict_bulge(amp: float, sig: float) -> dict:
    """ふくらみのうち平面に**吸われる**分を、真値の場から直接計算する。

    面内の密な格子でふくらみの場を作り、``{1, η, ζ}`` の張る部分空間へ
    最小二乗射影して引く。残った山の高さが「測れるふくらみ」、
    ζ に掛かる係数が「ふくらみが化けた偽の倒れ」。点も雑音も使わない。
    """
    eta = np.linspace(-RD / 2, RD / 2, 161)
    zeta = np.linspace(-RH / 2, RH / 2, 121)
    E, Z = np.meshgrid(eta, zeta)
    b = bulge_field(E, Z, amp, sig).ravel()
    A = np.column_stack([np.ones(b.size), E.ravel(), Z.ravel()])
    coef, *_ = np.linalg.lstsq(A, b, rcond=None)
    resid = b - A @ coef
    return {"peak": float(resid.max()), "mean": float(coef[0]),
            "fake_yaw": float(coef[1]), "fake_tilt": float(coef[2]),
            "absorbed": float(1.0 - resid.max() / amp) if amp else 0.0}


def section_bulge() -> dict:
    print("\n" + "=" * 78)
    print("6) 面のふくらみ —— 広いふくらみは平面当てはめに食べられる")
    print("=" * 78)
    print("  振幅は %.0f mm 固定、広がり σ を振る(壁は %.1f x %.1f m)"
          % (1e3 * BULGE_A, RD, RH))

    def _peak(pts, fit):
        """残差の山 —— 1 点の外れ値に振られないよう上位 0.5 %% の中央値で読む。"""
        r = (pts - fit["point"]) @ fit["normal"]
        return float(np.median(np.sort(r)[-max(1, len(r) // 200):]))

    # ★雑音だけの床。ふくらみゼロの壁で同じ読み方をすると、これが出る。
    w0 = make_wall("east", 20000, np.random.default_rng(31), amp=0.0)
    floor = 1e3 * _peak(w0["P"], fit_wall(w0["P"], seed=3))
    print("  ★先に**雑音の床**を測る: ふくらみゼロの壁でも同じ読み方で %.2f mm 出る"
          "(σ_雑音 %.1f mm の 2.6 倍)。" % (floor, 1e3 * SIG))
    print("\n   σ [m]   残差の山 [mm]  雑音なし  閉形式  吸われた割合 [%s]  "
          "偽の倒れ [mrad](実測 / 予測)" % "%")

    sigs, peak_m, peak_c, peak_p, fake_m, fake_p = [], [], [], [], [], []
    base_tilt = 1e3 * TILT["east"]
    for bs in (0.25, 0.40, 0.70, 1.10, 1.80, 3.00):
        w = make_wall("east", 20000, np.random.default_rng(31), bsig=bs)
        wc = make_wall("east", 20000, np.random.default_rng(31), bsig=bs,
                       jitter_free=True)
        f = fit_wall(w["P"], seed=3)
        pr = predict_bulge(BULGE_A, bs)
        sigs.append(bs)
        peak_m.append(1e3 * _peak(w["P"], f))
        peak_c.append(1e3 * _peak(wc["P"], fit_wall(wc["P"], seed=3)))
        peak_p.append(1e3 * pr["peak"])
        fake_m.append(plumb_mrad(f["normal"]) - base_tilt)
        fake_p.append(1e3 * pr["fake_tilt"])
        print("   %5.2f    %10.2f  %8.2f  %6.2f      %10.1f        %+6.2f / %+6.2f"
              % (bs, peak_m[-1], peak_c[-1], peak_p[-1], 100 * pr["absorbed"],
                 fake_m[-1], fake_p[-1]))

    print("\n  ★雑音を切ると閉形式とぴったり合う(差は最大 %.2f mm)。"
          "σ = %.2f m では真の残り %.2f mm、\n     σ = %.2f m では %.2f mm ——"
          " **ふくらみが広いほど「平ら」と報告される**。一番危ない\n     "
          "(壁全体が出ている)状態が一番見えない。"
          % (max(abs(a - b) for a, b in zip(peak_c, peak_p)),
             sigs[0], peak_c[0], sigs[-1], peak_c[-1]))
    cross = [s for s, p in zip(sigs, peak_c) if p < floor]
    print("  ★★崖は「吸われる量」ではなく**雑音の床と交わる所**にある。"
          "予測は残差 < %.2f mm、\n     つまり σ >= %.2f m。そこから先の読み"
          "(%.2f mm)は**中身が全部雑音**で、\n     ふくらみが 9 mm あっても "
          "0 mm あっても同じ数字が出る(床 %.2f mm)。"
          % (floor, cross[0] if cross else float("nan"),
             peak_m[-1], floor))
    print("  ★しかも吸われた分は消えるのでなく**倒れに化ける**: 偽の倒れは"
          " 最大 %+.2f mrad\n     (階高で %.1f mm)。許容 %.0f mm の %.0f %s を"
          "ふくらみだけで使う。"
          % (max(fake_m, key=abs), abs(max(fake_m, key=abs)) * 1e-3 * RH * 1e3,
             TOL_PLUMB_MM,
             100 * abs(max(fake_m, key=abs)) * 1e-3 * RH * 1e3 / TOL_PLUMB_MM, "%"))

    figs.save_plot("bulge_absorption",
                   [("残差の山(実測・雑音あり)", sigs, peak_m),
                    ("残差の山(雑音なし)", sigs, peak_c),
                    ("閉形式の予測", sigs, peak_p),
                    ("雑音の床 %.2f mm" % floor, sigs, [floor] * len(sigs))],
                   xlabel="ふくらみの広がり σ [m]", ylabel="残差の山 [mm]",
                   title="広いふくらみは平面に吸われ、残りは雑音の床に沈む",
                   caption="真の振幅はどの σ でも %.0f mm。" % (1e3 * BULGE_A))
    figs.save_plot("bulge_fake_tilt",
                   [("偽の倒れ(実測)", sigs, fake_m),
                    ("偽の倒れ(閉形式)", sigs, fake_p),
                    ("許容 %.0f mm 相当" % TOL_PLUMB_MM, sigs,
                     [-TOL_PLUMB_MM / RH] * len(sigs))],
                   xlabel="ふくらみの広がり σ [m]", ylabel="倒れの読みのずれ [mrad]",
                   title="吸われた分は消えず、倒れの判定へ移る")

    maps, caps = [], []
    for bs in (0.25, 0.70, 3.00):
        w = make_wall("east", 20000, np.random.default_rng(31), bsig=bs)
        r = _residual(w, fit_wall(w["P"], seed=3))
        maps.append(_bin_mean(w["eta"], w["zeta"], r * 1e3, (-RD / 2, RD / 2),
                              (-RH / 2, RH / 2), 84, 58, up=4))
        caps.append("σ = %.2f m" % bs)
    figs.save_grid("bulge_maps", maps, caps,
                   title="東の壁の偏差マップ [mm] —— 同じ振幅 %.0f mm のふくらみ"
                         % (1e3 * BULGE_A), signed=True, ncols=3)
    return {"sig": sigs, "peak": peak_m, "clean": peak_c, "pred": peak_p,
            "fake": fake_m, "fake_pred": fake_p, "floor": floor}


# --------------------------------------------------------------------------- #
# 7. 判定が食い違う —— 3 つのやり方を並べる                                     #
# --------------------------------------------------------------------------- #
def section_verdicts(zero: dict, out: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) 同じ点群・同じ許容で判定が食い違う")
    print("=" * 78)

    room = make_room()
    q = np.array([RW / 2, RD / 2, ZREF])
    rows = []

    def _verdict(v, tol):
        return "合格" if abs(v) <= tol else "不合格"

    lo, hi = L.aabb(room["P"])
    rows.append(["内法 東西", "AABB", "%+.1f mm" % (1e3 * (hi[0] - lo[0] - RW)),
                 _verdict(1e3 * (hi[0] - lo[0] - RW), TOL_DIM_MM)])
    rows.append(["内法 東西", "平面 2 枚", "%+.1f mm" % (1e3 * (zero["plane"][0] - RW)),
                 _verdict(1e3 * (zero["plane"][0] - RW), TOL_DIM_MM)])
    rows.append(["内法 南北", "AABB", "%+.1f mm" % (1e3 * (hi[1] - lo[1] - RD)),
                 _verdict(1e3 * (hi[1] - lo[1] - RD), TOL_DIM_MM)])
    rows.append(["内法 南北", "平面 2 枚", "%+.1f mm" % (1e3 * (zero["plane"][1] - RD)),
                 _verdict(1e3 * (zero["plane"][1] - RD), TOL_DIM_MM)])

    i = out["frac"].index(20.0)
    rows.append(["東壁の倒れ(家具 20 %)", "最小二乗",
                 "%.1f mrad" % out["ls"][i],
                 _verdict(out["ls"][i] * 1e-3 * RH * 1e3, TOL_PLUMB_MM)])
    rows.append(["東壁の倒れ(家具 20 %)", "RANSAC",
                 "%.2f mrad" % out["rs"][i],
                 _verdict(out["rs"][i] * 1e-3 * RH * 1e3, TOL_PLUMB_MM)])
    rows.append(["東壁の倒れ(真値)", "—", "%.2f mrad" % (1e3 * TILT["east"]),
                 _verdict(1e3 * TILT["east"] * 1e-3 * RH * 1e3, TOL_PLUMB_MM)])

    for r in rows:
        print("   %-24s %-10s %12s   %s" % tuple(r))
    figs.save_table("verdicts",
                    ["項目", "やり方", "読み",
                     "判定(内法 ±%.0f mm / 倒れ %.0f mm)"
                     % (TOL_DIM_MM, TOL_PLUMB_MM)], rows,
                    title="やり方を変えると判定が変わる")
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 公開経路に無かった処理(この PoC が自前で書いたもの)")
    print("=" * 78)
    for name in ("plumb_deviation", "squareness", "plane_pair_distance",
                 "extreme_value_inflation"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    print("  (a) plumb_deviation(normal) —— 壁面の倒れを mrad と「階高あたり mm」で。"
          "\n      角そのものは angle_line_plane で取れるが、度で返るので"
          "施工の単位へ\n      直す所を毎回書いている。")
    print("  (b) squareness(n1, n2) —— **平面図に落としてから**の直交度。"
          "angle_between_planes は\n      3-D の二面角なので、床や天井を"
          "混ぜた瞬間に意味が変わる。")
    print("  (c) plane_pair_distance(planeA, planeB, ref) —— 向かい合う 2 面の"
          "基準点での\n      内法。distance_point_plane を 2 回呼んで足すだけだが、"
          "**寸法検査の\n      基本の 1 つ**が 1 行で書けない。")
    print("  (d) 面内座標への写像(点群 -> (η, ζ, 偏差) の 3 列)。偏差マップを"
          "描くのに\n      毎回書いている(warp_by_plane は画像を歪める op で"
          "別物)。")
    print("  (e) 外れ点に対する**最小二乗と頑健推定の対照**を返す口。"
          "ransac_plane と\n      fit_plane3 は在るが、「どちらがどれだけ"
          "引きずられたか」を返す層が無い。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("室内点群から壁の施工誤差を出す —— 外接直方体は寸法を測っていない")
    print("設計 %.1f x %.1f x %.1f m / 測距の雑音 σ = %.1f mm / 壁 1 枚 %d 点"
          % (RW, RD, RH, 1e3 * SIG, N_WALL))
    print("=" * 78)

    zero = section_zero_point()
    yaw = section_aabb_yaw()
    grow = section_aabb_n()
    pl = section_plumb_square()
    out = section_outliers()
    bul = section_bulge()
    section_verdicts(zero, out)
    section_tool_gaps()

    # --- 所見を固定する assert -------------------------------------------- #
    pb = predict_bulge(BULGE_A, BULGE_S)
    # 1) AABB は必ず過大、平面法は許容内(残りはふくらみの平均で説明がつく)
    assert zero["aabb"][0] - RW > 0.010, zero["aabb"][0]
    assert abs(zero["plane"][0] - RW) < 0.010, zero["plane"][0]
    assert abs((zero["plane"][0] - RW) - pb["mean"]) < 0.001
    # 2) AABB の閉形式は**上界**として当たる(実測より大きく、差は 5 mm 未満)
    assert zero["pred"]["width"] >= zero["aabb"][0]
    assert zero["pred"]["width"] - zero["aabb"][0] < 0.005
    # 3) 部屋を 10 度回すと AABB は 500 mm 以上外すが、平面法は**動かない**
    assert yaw["aabb"][-1] > 500.0, yaw["aabb"]
    assert max(yaw["plane"]) - min(yaw["plane"]) < 0.05, yaw["plane"]
    # 4) 点を増やすほど AABB は広がる(単調)。伸び方は閉形式と 1 mm 以内で一致
    assert all(b >= a - 0.2 for a, b in zip(grow["meas"], grow["meas"][1:]))
    assert grow["meas"][-1] - grow["meas"][0] > 4.0
    assert abs((grow["meas"][-1] - grow["meas"][0])
               - (grow["pred"][-1] - grow["pred"][0])) < 1.0
    # 5) ふくらみの無い 3 枚の倒れは 0.05 mrad 以内。東の壁のずれは
    #    「測定の誤差」ではなく閉形式のふくらみ吸収で 0.1 mrad 以内に説明される
    for r in pl["rows"]:
        if r[0] != "east":
            assert abs(float(r[3])) < 0.05, r
        else:
            assert abs(float(r[3]) - 1e3 * pb["fake_tilt"]) < 0.10, r
    # 6) 倒れは直交度へは漏れない(2 次)。漏らすのはふくらみのほうで、
    #    その量も閉形式で 0.1 mrad 以内に当たる
    assert pl["leak"] < 0.1, pl["leak"]
    assert abs(pl["sq_err"] - pl["pred_yaw"]) < 0.10, (pl["sq_err"], pl["pred_yaw"])
    # 7) 最小二乗は 10 % 混入で真値の 5 倍以上、閉形式の予測と 5 % 以内
    i10 = out["frac"].index(10.0)
    assert out["ls"][i10] > 5.0 * 1e3 * TILT["east"]
    assert abs(out["ls"][i10] - out["pred"][i10]) < 0.05 * out["pred"][i10]
    # 8) RANSAC は 45 % までは踏みとどまり、55 % で棚へ乗り換える
    i45 = out["frac"].index(45.0)
    i55 = out["frac"].index(55.0)
    assert abs(out["off"][i45]) < 20.0 and abs(out["off"][i55]) > 300.0
    # 9) 雑音を切った残差の山は閉形式と 0.6 mm 以内。雑音ありは床より下がらない
    assert bul["clean"][0] > bul["clean"][-1] * 3.0
    assert all(abs(m - p) < 0.6 for m, p in zip(bul["clean"], bul["pred"]))
    assert bul["peak"][-1] >= bul["floor"] - 0.3
    assert all(abs(m - p) < 0.10 for m, p in zip(bul["fake"], bul["fake_pred"]))

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 外接直方体は寸法でなく「部屋の向き + 点の数」を測っている"
          "(ψ=10 度で %+.0f mm、点 256 倍で %+.1f mm)。"
          % (yaw["aabb"][-1], grow["meas"][-1] - grow["meas"][0]))
    print("  * 外れ点への壊れ方は 2 種類 —— 最小二乗は傾き、RANSAC は乗り換え。")
    print("  * 広いふくらみは平面に吸われ、消えずに倒れへ化ける。")
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
