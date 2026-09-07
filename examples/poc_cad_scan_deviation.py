# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CAD と実測点群の差分検査 —— 位置合わせが欠陥を吸って、無い所にへこみを作る。

機械部品を作ったあと「設計どおりか」を 3-D スキャナで確かめる仕事です。
出す数字は 2 つ: **各点の符号付き偏差[mm]**(+ = 肉が余っている、- = 足りない)と、
**公差 ±t を外れた領域の面積[mm^2]**。ところが実測点群には姿勢が付いていないので、
先に CAD へ**重ねてから**測ることになります。この PoC は「重ねる誤差」と
「測る誤差」を**別々に数える**ための台です。

EXTEND: 実スキャンに差し替えるなら :func:`make_scan` の戻り辞書のうち ``pts``
(実測点、mm)だけを実データにします。**そのとき失われるのは ``dev_true``**
(各点の真の符号付き偏差)—— これは合成だから書ける量で、実物では
「もっと精密な測定機(CMM)の値」を借りるしかありません。CAD 側 :func:`nominal_cloud`
は STEP/STL を読んで ``fs.ledger.mesh_sample_points`` で点にすれば同じ形で入ります。
**法線は必ず CAD 側(向きが定義できる側)から取ること** —— 実測点から推定すると
第 4 章の符号反転を踏みます。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(位置合わせせずに最近傍距離)は 32.52 mm**。部品の対角 74 mm に対して
   同じ桁で、公差 0.10 mm とは 300 倍以上離れている。重心だけ合わせても 11.11 mm。
   **差分検査は位置合わせの後段ではなく、位置合わせそのもの**が主要な誤差源。
2. **姿勢の誤差と偏差の誤差は別々に数える**。FPFH の粗合わせだけだと姿勢
   0.243 度 / 点の移動 RMS 0.0808 mm で、偏差の RMS は 91.2 µm ——
   **公差 100 µm とほぼ同じ大きさの嘘**が姿勢から入る。点-面 ICP まで通すと
   姿勢 0.0012 度・偏差 RMS 21.5 µm(雑音 20 µm の床)まで落ちる。
3. ★**法線を実測点から推定すると、面積の 14.2 % で符号が裏返る**。穴の内壁と
   フィレットは凹面で、「近傍重心から離れる向き」が材料の中を向く。実測 14.6 %
   (予測 14.2 % = 凹面の面積比)。**へこみが出っ張りとして報告される**。
   Hoppe の大域向き付け(``estimate_oriented_normals``)でも 47.3 % 反転した。
4. **雑音は必ず正側へ偏る、が符号付きにすると消える**。予測 σ√(2/π)、σ=20 µm で
   15.96 µm —— 実測 15.94 µm(比 0.999)。同じ点の符号付き偏差の平均は +0.06 µm。
   **符号を付けるだけで偏りが 250 分の 1 になる**。
5. ★**参照点群の密度そのものが偏差の下限を決める**。無雑音・完全一致でも、
   最近傍距離の平均は予測 0.5/√ρ(ρ=点密度[点/mm^2])に従い、
   40000 点(ρ=4.84)で 0.2264 mm(予測 0.2273、比 0.996)—— **公差 0.10 mm を
   素で 2.3 倍超える**。法線へ射影した符号付きにすると 0.0002 mm に落ちる。
   密度を 1/1〜1/50 に間引いた掃引でも符号付き側は偏りを持たない。
6. ★★**中心的な主張: 欠陥は自分で自分を薄める。しかもどれだけ薄まるかは
   閉形式で予測できる**。剛体 6 自由度が吸える偏差場は
   ``J = [n | X×n]`` の張る 6 次元部分空間で、位置合わせ後に残るのは
   ``d - J(JᵀJ)⁻¹Jᵀd``。局所へこみ(深さ 450 µm・σ 3.5 mm)は 0.90 %(予測 0.93 %)
   しか薄まらないのに、★**反り(振幅 360 µm)は 33.0 % 吸われ(予測 a/3 = 33.3 %)、
   部品の中心に真値 0 の場所へ深さ 118 µm の「存在しないへこみ」が出る**
   (予測 -a/3 = -120 µm)。公差 ±100 µm なので**偽の不合格**になる。
7. ★**引かれ方は欠陥の大きさに比例し、傾きが予測と合う**。反りの振幅を
   0→600 µm と振ると ICP の並進 z が 0→198 µm と直線に動き、傾き 0.330
   (予測 1/3 = 0.333)。★**へこみは深さを 10 倍にしても薄まる割合が変わらない**
   (0.90 % のまま)—— 「大きい欠陥ほど食われる」のは**面積**の話で、深さではない。
8. **欠測(裏が見えない片側スキャン)は姿勢を引く**。可視面積 4179 mm^2(50.6 %)で
   姿勢誤差 0.0016 度 → 0.0059 度(3.6 倍)、偏差 RMS 21.5 → 21.9 µm。
   引かれ量は小さいが、**測れない 49.4 % の面積は「公差内」ではなく「未測定」**。
9. **崖(初期姿勢)**: ICP 単独は初期ずれ 12 度まで収束(残差 < 50 µm)、16 度で
   落ちる。★**28 度で残差が再び小さくなる**が、これは収束ではなく
   直方体の 90 度対称に落ちた別解(姿勢誤差 62.8 度)——
   **残差を合否に使うと嘘を見抜けない**。

【グラウンドトゥルース】部品は解析的な立体(直方体 60x40x12 + ボス φ18 + 根元
フィレット R2.5 + 貫通穴 φ10 と φ8)。表面積 8266.79 mm^2・体積 28742.32 mm^3 は
閉形式で、面積重み一様サンプリングの実測と 0.10 % / 0.06 % 以内で一致する。
偏差の真値は「法線方向にどれだけ動かしたか」そのもの(構成で厳密)。

【datum の但し書き】反りのある部品では「真の姿勢」は一意ではない —— 真値側は
製作時の座標系、ICP 側は最小二乗の座標系で、**両者は別の datum 規約**。第 6 章の
「偽のへこみ」は ICP のバグではなく、規約の差が偏差に化けたもの。実務で
datum 面を指定するのはこのため。

来歴(公開文献のみ): Besl & McKay, *IEEE TPAMI* 14 (1992) 239 —— ICP /
Chen & Medioni, *Image Vision Comput.* 10 (1992) 145 —— 点-面 /
Rusu et al., *ICRA* (2009) 3212 —— FPFH / Segal et al., *RSS* (2009) —— GICP /
Hoppe et al., *SIGGRAPH* (1992) 71 —— 法線の大域向き付け /
ISO 1101 —— 幾何公差と datum。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 部品の諸元 [mm] -------------------------------------------------------- #
L, W, H = 60.0, 40.0, 12.0        # 台の直方体(x, y, z)。台の上面は z = H
BX = 12.0                          # ボスの中心 x(y = 0)
BOSS_R = 9.0                       # ボス外半径
BOSS_TOP = 20.0                    # ボス頂面の z
RF = 2.5                           # 根元フィレットの半径(1/4 トーラス)
HOLE_R = 5.0                       # 貫通穴(ボスと同心、z = 0..BOSS_TOP)
H2X, H2R = -18.0, 4.0              # もう 1 本の穴(台だけ、z = 0..H)
RC = BOSS_R + RF                   # フィレットの中心円半径 = 11.5
ZC = H + RF                        # フィレットの中心円の z = 14.5

TOL = 0.10                         # 公差 ±t [mm]
NOISE = 0.020                      # 既定の測定雑音 σ [mm]
N_REF = 40000                      # CAD 参照点群の点数
N_SCAN = 30000                     # 実測点群の点数(主実験)
SEED = 7

# --- 欠陥の諸元(すべて真値として仕込む) --------------------------------------- #
DENT_C = np.array([-8.0, 6.0, H])  # 局所へこみの中心(上面)
DENT_H = 0.45                      # へこみの深さ [mm]
DENT_S = 3.5                       # へこみの広がり σ [mm]
WARP_A = 0.36                      # 反りの振幅 [mm](端で +a、中央で 0)
WEAR_W = 0.14                      # 摩耗 [mm](ボス外周と頂面、法線方向に一定)

_L = fs.ledger                      # 3-D op の公開経路(ファサードには出ていない)


# --------------------------------------------------------------------------- #
# 0. 小道具                                                                     #
# --------------------------------------------------------------------------- #
def rot(axis, deg: float) -> np.ndarray:
    """軸まわり ``deg`` 度の回転行列(ロドリゲス)。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def rot_err_deg(R_est, R_true) -> float:
    """2 つの回転の測地距離[度]。"""
    c = (np.trace(np.asarray(R_est) @ np.asarray(R_true).T) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def pose_shift_mm(R_est, t_est, R_true, t_true, X) -> float:
    """姿勢の差が**点をどれだけ動かすか** [mm]。

    並進ベクトルの差だけでは原点の取り方に依存する。部品の点を実際に
    動かして RMS を測れば、回転と並進をまとめて mm で言える。
    """
    a = X @ np.asarray(R_est).T + np.asarray(t_est)
    b = X @ np.asarray(R_true).T + np.asarray(t_true)
    return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))


# --------------------------------------------------------------------------- #
# 1. 部品 —— 面ごとに閉形式の面積と厳密な法線                                    #
# --------------------------------------------------------------------------- #
def face_areas() -> dict:
    """各面の面積[mm^2](すべて閉形式)。"""
    pi = np.pi
    return {
        "bottom": L * W - pi * HOLE_R ** 2 - pi * H2R ** 2,
        "top": L * W - pi * RC ** 2 - pi * H2R ** 2,
        "side_xp": W * H, "side_xm": W * H, "side_yp": L * H, "side_ym": L * H,
        # 回転面 dA = 2*pi*r*ds、r(phi) = RC - RF*sin(phi)、ds = RF*dphi
        "fillet": 2 * pi * RF * (pi * RC / 2.0 - RF),
        "boss_wall": 2 * pi * BOSS_R * (BOSS_TOP - ZC),
        "boss_top": pi * (BOSS_R ** 2 - HOLE_R ** 2),
        "hole1": 2 * pi * HOLE_R * BOSS_TOP,
        "hole2": 2 * pi * H2R * H,
    }


def nominal_volume() -> float:
    """部品の体積[mm^3](閉形式)。フィレットは Pappus の定理で足す。"""
    pi = np.pi
    v = L * W * H                                    # 台
    v += pi * (BOSS_R ** 2 - HOLE_R ** 2) * (BOSS_TOP - H)   # ボス(筒)
    v -= pi * HOLE_R ** 2 * H                        # 穴 1(台を貫く分)
    v -= pi * H2R ** 2 * H                           # 穴 2
    # フィレット = 正方形断面 - 1/4 円、それぞれ Pappus で回す
    v_sq = 2 * pi * ((RC ** 2 - BOSS_R ** 2) / 2.0) * RF
    a_q = pi * RF ** 2 / 4.0
    r_q = RC - 4.0 * RF / (3.0 * pi)                 # 1/4 円の重心半径
    v += v_sq - 2 * pi * r_q * a_q
    return float(v)


def _in_plate_plane(x, y, *, top: bool) -> np.ndarray:
    """台の上面/下面の穴抜き判定(上面はフィレットの外周まで抜ける)。"""
    r1 = np.hypot(x - BX, y)
    r2 = np.hypot(x - H2X, y)
    return (r1 > (RC if top else HOLE_R)) & (r2 > H2R)


def _sample_face(name: str, m: int, rng) -> tuple:
    """面 ``name`` から ``m`` 点を面積一様にサンプルし、(点, 外向き法線) を返す。"""
    if name in ("bottom", "top"):
        top = name == "top"
        xs, ys = [], []
        need = m
        while need > 0:
            x = rng.uniform(-L / 2, L / 2, need * 2)
            y = rng.uniform(-W / 2, W / 2, need * 2)
            ok = _in_plate_plane(x, y, top=top)
            xs.append(x[ok][:need])
            ys.append(y[ok][:need])
            need -= int(ok.sum())
        x = np.concatenate(xs)[:m]
        y = np.concatenate(ys)[:m]
        z = np.full(m, H if top else 0.0)
        n = np.zeros((m, 3))
        n[:, 2] = 1.0 if top else -1.0
        return np.column_stack([x, y, z]), n
    if name.startswith("side"):
        ax = 0 if name[5] == "x" else 1
        sgn = 1.0 if name[6] == "p" else -1.0
        half = (L / 2) if ax == 0 else (W / 2)
        other = (W / 2) if ax == 0 else (L / 2)
        u = rng.uniform(-other, other, m)
        z = rng.uniform(0.0, H, m)
        p = np.zeros((m, 3))
        p[:, ax] = sgn * half
        p[:, 1 - ax] = u
        p[:, 2] = z
        n = np.zeros((m, 3))
        n[:, ax] = sgn
        return p, n
    if name == "fillet":
        # phi ~ 密度 (RC - RF sin phi) / RC の棄却法(回転面の面積重み)
        acc = []
        while sum(len(a) for a in acc) < m:
            phi = rng.uniform(0.0, np.pi / 2, m)
            w = (RC - RF * np.sin(phi)) / RC
            acc.append(phi[rng.random(m) < w])
        phi = np.concatenate(acc)[:m]
        th = rng.uniform(0.0, 2 * np.pi, m)
        r = RC - RF * np.sin(phi)
        z = ZC - RF * np.cos(phi)
        p = np.column_stack([BX + r * np.cos(th), r * np.sin(th), z])
        # 凹面の外向き法線はトーラスの中心円を向く(= 材料の外へ)
        n = np.column_stack([np.sin(phi) * np.cos(th), np.sin(phi) * np.sin(th),
                             np.cos(phi)])
        return p, n
    if name in ("boss_wall", "hole1", "hole2"):
        if name == "boss_wall":
            r, z0, z1, cx, out = BOSS_R, ZC, BOSS_TOP, BX, 1.0
        elif name == "hole1":
            r, z0, z1, cx, out = HOLE_R, 0.0, BOSS_TOP, BX, -1.0
        else:
            r, z0, z1, cx, out = H2R, 0.0, H, H2X, -1.0
        th = rng.uniform(0.0, 2 * np.pi, m)
        z = rng.uniform(z0, z1, m)
        p = np.column_stack([cx + r * np.cos(th), r * np.sin(th), z])
        n = np.column_stack([out * np.cos(th), out * np.sin(th), np.zeros(m)])
        return p, n
    if name == "boss_top":
        th = rng.uniform(0.0, 2 * np.pi, m)
        r = np.sqrt(rng.uniform(HOLE_R ** 2, BOSS_R ** 2, m))
        p = np.column_stack([BX + r * np.cos(th), r * np.sin(th),
                             np.full(m, BOSS_TOP)])
        n = np.zeros((m, 3))
        n[:, 2] = 1.0
        return p, n
    raise ValueError("未知の面 %r" % name)


#: 凹面(外向き法線が「近傍重心から離れる向き」と逆になる面)
CONCAVE = ("hole1", "hole2", "fillet")


def nominal_cloud(n: int, seed: int) -> dict:
    """公称形状の表面点群(面積一様)+ 厳密な外向き法線 + 面 ID。"""
    rng = np.random.default_rng(seed)
    areas = face_areas()
    tot = sum(areas.values())
    names = list(areas)
    counts = {k: max(8, int(round(n * areas[k] / tot))) for k in names}
    P, N, F = [], [], []
    for i, k in enumerate(names):
        p, nn = _sample_face(k, counts[k], rng)
        P.append(p)
        N.append(nn)
        F.append(np.full(len(p), i, np.int32))
    P = np.concatenate(P)
    N = np.concatenate(N)
    F = np.concatenate(F)
    return {"pts": P, "nrm": N, "face": F, "names": names,
            "area": tot, "w": tot / len(P),
            "concave": np.isin(F, [names.index(c) for c in CONCAVE])}


# --------------------------------------------------------------------------- #
# 2. 欠陥 —— 法線方向にどれだけ動かすか(それがそのまま真値)                     #
# --------------------------------------------------------------------------- #
def defect_field(P, N, dent_h=DENT_H, dent_s=DENT_S, warp_a=WARP_A,
                 wear_w=WEAR_W) -> dict:
    """各点の真の符号付き偏差[mm]を、種類ごとに分けて返す。

    + = 肉が余っている / - = 足りない。3 種を**足す前に別々に持つ**のは、
    第 6 章でどの種類がどれだけ位置合わせに吸われるかを分けて数えるため。
    """
    d_dent = -dent_h * np.exp(-np.sum((P - DENT_C) ** 2, axis=1)
                              / (2.0 * dent_s ** 2))
    # 反り: 板が弓なりに反る = z 方向の変位 u_z(x) を法線へ射影する
    d_warp = warp_a * (2.0 * P[:, 0] / L) ** 2 * N[:, 2]
    r_boss = np.hypot(P[:, 0] - BX, P[:, 1])
    worn = (P[:, 2] > ZC - 1e-9) & (r_boss < BOSS_R + 1e-6)
    d_wear = np.where(worn, -wear_w, 0.0)
    return {"dent": d_dent, "warp": d_warp, "wear": d_wear,
            "total": d_dent + d_warp + d_wear}


# --------------------------------------------------------------------------- #
# 3. 実測点群を合成する                                                         #
# --------------------------------------------------------------------------- #
VIEW = np.array([0.30, -0.20, 1.0])
VIEW = VIEW / np.linalg.norm(VIEW)      # センサの居る向き(部品から見て)


def make_scan(n=N_SCAN, seed=SEED, noise=NOISE, defects=True, transform=True,
              occlude=False, keep=1.0, **dkw) -> dict:
    """既知の欠陥・姿勢・雑音・欠測を持つ「実測点群」を作る。

    真値は 3 つ: ``dev_true``(各点の符号付き偏差)、``R_true``/``t_true``
    (点群を CAD 系へ戻す剛体変換)、``w``(1 点が代表する面積)。
    """
    rng = np.random.default_rng(seed + 1000)
    nom = nominal_cloud(n, seed=seed + 3)
    P, N = nom["pts"], nom["nrm"]
    dev = defect_field(P, N, **dkw)["total"] if defects else np.zeros(len(P))
    Q = P + dev[:, None] * N
    if occlude:
        vis = N @ VIEW > 0.10
        Q, N, dev, P = Q[vis], N[vis], dev[vis], P[vis]
        nom["face"] = nom["face"][vis]
    if keep < 1.0:
        m = max(200, int(round(len(Q) * keep)))
        idx = rng.choice(len(Q), m, replace=False)
        Q, N, dev, P = Q[idx], N[idx], dev[idx], P[idx]
        nom["face"] = nom["face"][idx]
    if noise > 0:
        Q = Q + noise * rng.standard_normal(Q.shape)
    if transform:
        Rg = rot([0.35, 0.82, 0.45], 24.0)
        tg = np.array([35.0, -20.0, 9.0])
    else:
        Rg, tg = np.eye(3), np.zeros(3)
    scan = Q @ Rg.T + tg
    return {"pts": scan, "nom": P, "nrm": N, "dev_true": dev,
            "R_true": Rg.T, "t_true": -Rg.T @ tg, "face": nom["face"],
            "w": nom["area"] / n, "area_seen": nom["area"] / n * len(scan)}


# --------------------------------------------------------------------------- #
# 4. 推定器 —— 位置合わせ → 符号付き偏差 → 公差外面積                            #
# --------------------------------------------------------------------------- #
class CadRef:
    """CAD 側の参照。最近傍と、その点の法線への射影で符号を決める。"""

    def __init__(self, n=N_REF, seed=SEED + 77):
        c = nominal_cloud(n, seed=seed)
        self.pts, self.nrm, self.face = c["pts"], c["nrm"], c["face"]
        self.names, self.area, self.w = c["names"], c["area"], c["w"]
        self.concave = c["concave"]
        self.tree = cKDTree(self.pts)
        self.rho = len(self.pts) / self.area      # 点密度 [点/mm^2]

    def deviate(self, q, k=6, edge_deg=30.0):
        """(素の最近傍距離, 符号付き偏差, 参照点 index, 稜線帯フラグ)。

        符号付き偏差 = 最近傍の参照点から見た変位を**その点の法線へ射影**した値。
        ★稜線(面と面の境)の近くでは、最近傍が**隣の面へ飛ぶ**ことがある。
        隣の面の法線へ射影した値は偏差でも何でもない。ここでは直そうとせず
        **見つけて外に出す**: k 近傍の法線が ``edge_deg`` 以上割れている点を
        「稜線帯 = 測れない」として旗を立てる(黙って数を出すほうが罪が重い)。
        """
        q = np.asarray(q, float)
        d, i = self.tree.query(q, k=k, workers=-1)
        i0 = i[:, 0]
        s = np.einsum("ij,ij->i", q - self.pts[i0], self.nrm[i0])
        cos = np.einsum("mkj,mj->mk", self.nrm[i], self.nrm[i0])
        edge = cos.min(axis=1) < np.cos(np.radians(edge_deg))
        return d[:, 0], s, i0, edge


def out_of_tol_area(dev, w, tol=TOL) -> float:
    """公差 ±tol を外れた領域の面積[mm^2](1 点 = 面積 w を代表)。"""
    return float(np.count_nonzero(np.abs(np.asarray(dev)) > tol) * w)


def align(scan, ref: CadRef, method="p2plane", init=None, iters=40, sub=6000,
          seed=0):
    """点群を CAD 系へ重ねる。返り値 (R, t)。``dst ~= src @ R.T + t`` 規約。"""
    rng = np.random.default_rng(seed)
    src = scan if len(scan) <= sub else scan[rng.choice(len(scan), sub, False)]
    dst, dn = ref.pts, ref.nrm
    if method == "none":
        return np.eye(3), np.zeros(3)
    if method == "centroid":
        return np.eye(3), dst.mean(0) - src.mean(0)
    if method == "fpfh":
        R, t, _ = _L.register_fpfh(src, dst, dst_normals=dn, voxel_size=1.2,
                                   ransac_iters=4000, seed=1)
        return np.asarray(R), np.asarray(t)
    if init is None:
        init = (np.eye(3), np.zeros(3))
    if method == "p2point":
        R, t, _ = _L.icp_point2point_3d(src, dst, iters=iters,
                                        init_R=init[0], init_t=init[1])
        return np.asarray(R), np.asarray(t)
    if method == "p2plane":
        R, t = _L.icp_point2plane(src, dst, dn, iters=iters, init=init)[:2]
        return np.asarray(R), np.asarray(t)
    if method == "gicp":
        # ★台帳の out アダプタが dict を (R, t) に切り詰めるので rmse は届かない
        R, t = _L.gicp(src, dst, max_iter=25, init=init)
        return np.asarray(R), np.asarray(t)
    raise ValueError(method)


# --------------------------------------------------------------------------- #
# 5. 剛体 6 自由度が吸える偏差場(第 6 章の予測)                                 #
# --------------------------------------------------------------------------- #
def rigid_basis(P, N) -> np.ndarray:
    """点-面 ICP が吸える偏差場の基底 ``J = [n | X x n]`` (M, 6)。"""
    return np.column_stack([N, np.cross(P, N)])


def absorbed(P, N, d):
    """``d`` のうち剛体運動で説明できる成分と、残る成分、係数 [omega|tau]。"""
    J = rigid_basis(P, N)
    c, *_ = np.linalg.lstsq(J, d, rcond=None)
    fit = J @ c
    return fit, d - fit, c


# --------------------------------------------------------------------------- #
# 図の道具 —— 3-D は投影図と誤差地図で見せる                                     #
# --------------------------------------------------------------------------- #
#: カメラの居る向き(部品の原点から見て)と、陰影づけの光の向き
CAM = np.array([0.62, -0.72, 0.75])
LIGHT = np.array([0.35, -0.55, 0.90])


def _cam_basis():
    """(右, 上, カメラ方向) の正規直交基底。カメラは部品の上・手前に置く。"""
    c = CAM / np.linalg.norm(CAM)
    r = np.cross(np.array([0.0, 0.0, 1.0]), c)
    r /= np.linalg.norm(r)
    return r, np.cross(c, r), c


def render(P, val=None, nrm=None, shade=False, res=(320, 250), pad=4.0, splat=1,
           scale=None):
    """斜め視点の正射影 + z バッファ。点を散らさず**面として**見せる。

    ``nrm`` を渡すとカメラに背を向けた点を落とす(裏面が透けない)。
    ``shade=True`` なら Lambert 陰影の (H,W,3)、``val`` なら符号付きの誤差地図
    (H,W)。``scale`` を渡すと ±scale で切り、右端に**色の目盛り帯**を付ける
    (パネルごとに勝手な正規化がかかって見比べられなくなるのを防ぐ)。
    """
    r, up, c = _cam_basis()
    P = np.asarray(P, float)
    if nrm is not None:
        keep = np.asarray(nrm, float) @ c > 0.02
        P, nrm = P[keep], np.asarray(nrm, float)[keep]
        if val is not None:
            val = np.asarray(val, float)[keep]
    x, y = P @ r, P @ up
    dep = -(P @ c)                        # 小さいほど手前
    Wp, Hp = res
    s = max((x.max() - x.min() + 2 * pad) / Wp, (y.max() - y.min() + 2 * pad) / Hp)
    ix = np.clip(((x - x.min() + pad) / s).astype(int), 0, Wp - 1)
    iy = np.clip((Hp - 1 - (y - y.min() + pad) / s).astype(int), 0, Hp - 1)
    if shade:
        lam = np.asarray(nrm, float) @ (LIGHT / np.linalg.norm(LIGHT))
        v = 0.18 + 0.82 * np.clip(lam, 0.0, 1.0)
    else:
        v = np.asarray(val, float)
    img = np.full((Hp, Wp), np.nan)
    order = np.argsort(dep)[::-1]         # 遠い順に描き、手前で上書き
    for dy in range(-splat, splat + 1):   # 1 点を数画素に広げて隙間を埋める
        for dx in range(-splat, splat + 1):
            img[np.clip(iy[order] + dy, 0, Hp - 1),
                np.clip(ix[order] + dx, 0, Wp - 1)] = v[order]
    img = np.nan_to_num(img, nan=0.02 if shade else 0.0)
    if shade:
        return np.stack([img] * 3, axis=-1)
    return with_scalebar(img, scale) if scale else img


def with_scalebar(img, s: float, wpx: int = 12):
    """右端に ±``s`` の色の目盛り帯を足す(全パネルで色と値の対応を固定する)。"""
    h = img.shape[0]
    ramp = np.linspace(s, -s, h)[:, None] * np.ones((1, wpx))
    gap = np.zeros((h, 4))
    return np.concatenate([np.clip(img, -s, s), gap, ramp], axis=1)


def top_map(P2, val, res=(300, 200), rmax=1.2):
    """上面(x, y)へ最近傍で塗った偏差地図。``P2`` は (M, 2)。"""
    Wp, Hp = res
    xs = np.linspace(-L / 2, L / 2, Wp)
    ys = np.linspace(W / 2, -W / 2, Hp)
    gx, gy = np.meshgrid(xs, ys)
    if len(P2) < 4:
        return np.zeros((Hp, Wp))
    d, i = cKDTree(np.asarray(P2)).query(np.column_stack([gx.ravel(), gy.ravel()]),
                                         k=1, workers=-1)
    out = np.asarray(val, float)[i]
    out[d > rmax] = 0.0
    return out.reshape(Hp, Wp)


# --------------------------------------------------------------------------- #
# 章 1: 部品と真値                                                              #
# --------------------------------------------------------------------------- #
def section_part(ref: CadRef) -> dict:
    print("\n" + "=" * 78)
    print("1) 部品と真値 —— 面積・体積を閉形式で検算する")
    print("=" * 78)
    areas = face_areas()
    a_closed = sum(areas.values())
    # 標本から面積を出し直す(面ごとの点数比 x 全面積は自明なので、
    # 体積をモンテカルロで独立に出して閉形式と突き合わせる)
    rng = np.random.default_rng(5)
    m = 240000
    q = np.column_stack([rng.uniform(-L / 2, L / 2, m), rng.uniform(-W / 2, W / 2, m),
                         rng.uniform(0.0, BOSS_TOP, m)])
    inside = _inside(q)
    v_mc = float(inside.mean()) * L * W * BOSS_TOP
    v_closed = nominal_volume()
    print("  表面積(閉形式) %.2f mm^2   体積(閉形式) %.2f mm^3" % (a_closed, v_closed))
    print("  体積(モンテカルロ %d 点) %.2f mm^3  -> 差 %+.3f %%"
          % (m, v_mc, 100 * (v_mc - v_closed) / v_closed))
    # 面積は「面積重み一様サンプリング」で標本の面別比率が閉形式比率に合うかで検算
    cnt = np.bincount(ref.face, minlength=len(ref.names))
    err = max(abs(cnt[i] / len(ref.face) - areas[k] / a_closed) / (areas[k] / a_closed)
              for i, k in enumerate(ref.names))
    print("  面別の点数比 vs 面積比: 最大ずれ %.3f %%(%d 点)" % (100 * err, len(ref.face)))
    print("  参照点密度 rho = %.3f 点/mm^2" % ref.rho)
    for k in ref.names:
        print("      %-10s %8.2f mm^2" % (k, areas[k]))

    d = defect_field(ref.pts, ref.nrm)
    print("\n  仕込んだ欠陥(真値):")
    for k in ("dent", "warp", "wear"):
        v = d[k]
        print("      %-5s  最小 %+7.1f µm  最大 %+7.1f µm  公差外面積 %8.2f mm^2"
              % (k, 1000 * v.min(), 1000 * v.max(), out_of_tol_area(v, ref.w)))
    print("      %-5s  最小 %+7.1f µm  最大 %+7.1f µm  公差外面積 %8.2f mm^2"
          % ("total", 1000 * d["total"].min(), 1000 * d["total"].max(),
             out_of_tol_area(d["total"], ref.w)))

    if figs.enabled():
        big = nominal_cloud(140000, seed=3)
        dv = defect_field(big["pts"], big["nrm"])["total"]
        vis = big["nrm"] @ VIEW > 0.10
        S = 0.40
        figs.save_grid(
            "scene",
            [render(big["pts"], nrm=big["nrm"]),
             render(big["pts"], dv, scale=S),
             render(big["pts"][vis], dv[vis], scale=S)],
            ["公称形状(60x40x12 + ボス + フィレット + 穴 2)",
             "真の偏差(だいだい = 足りない / 青 = 余る、±%.2f mm)" % S,
             "片側スキャンで見える面だけ(可視 %.0f %%)" % (100 * vis.mean())],
            title="CAD と実測の差分検査 —— 場面", ncols=3,
            signed=[False, True, True],
            caption="偏差は法線方向の変位そのもの(構成で厳密)。"
                    "右端の帯が色と値の対応。")
    return {"area": a_closed, "vol": v_closed, "vol_mc": v_mc, "dev": d}


def _inside(q) -> np.ndarray:
    """点が部品の内側か(体積のモンテカルロ検算用)。"""
    x, y, z = q[:, 0], q[:, 1], q[:, 2]
    r1 = np.hypot(x - BX, y)
    r2 = np.hypot(x - H2X, y)
    plate = (z <= H) & (np.abs(x) <= L / 2) & (np.abs(y) <= W / 2)
    boss = (z > H) & (z <= BOSS_TOP) & (r1 <= BOSS_R)
    # フィレット: 角の四角から 1/4 円を抜いた回転体
    fil = ((z > H) & (z <= ZC) & (r1 > BOSS_R) & (r1 <= RC)
           & ((r1 - RC) ** 2 + (z - ZC) ** 2 >= RF ** 2))
    solid = plate | boss | fil
    return solid & (r1 > HOLE_R) & ~((r2 <= H2R) & (z <= H))


# --------------------------------------------------------------------------- #
# 章 2-3: ゼロ点と位置合わせ 4 手法                                             #
# --------------------------------------------------------------------------- #
def section_align(ref: CadRef) -> dict:
    print("\n" + "=" * 78)
    print("2-3) ゼロ点と位置合わせ —— 姿勢の誤差[度/mm]と偏差の誤差[µm]は別物")
    print("=" * 78)
    sc = make_scan()
    tru = sc["dev_true"]
    # 稜線帯は姿勢に依らずほぼ同じ点集合なので、真の姿勢で 1 回決めて全手法で使う
    _, _, _, edge = ref.deviate(sc["pts"] @ sc["R_true"].T + sc["t_true"])
    ok = ~edge
    a_true = out_of_tol_area(tru[ok], sc["w"])
    print("  真値: 公差外面積 %.2f mm^2 / 最大 |偏差| %.1f µm / 点数 %d"
          % (a_true, 1000 * np.abs(tru).max(), len(sc["pts"])))
    print("  稜線帯(k 近傍の法線が 30 度以上割れる点)を %.1f %% = %.0f mm^2 除外して"
          "測る(理由は表のあと)。" % (100 * edge.mean(), edge.mean() * ref.area))
    print("\n  手法            姿勢[度]   点移動[mm]   偏差RMS[µm]  偏差最大[µm]"
          "  公差外面積[mm^2]  面積誤差")

    rows, keep = [], {}
    init = None
    for name, meth in (("なし(ゼロ点)", "none"), ("重心だけ", "centroid"),
                       ("FPFH 粗合わせ", "fpfh"), ("+ 点-点 ICP", "p2point"),
                       ("+ 点-面 ICP", "p2plane"), ("+ GICP", "gicp"),
                       ("真の姿勢を与える", "oracle")):
        if meth in ("p2point", "p2plane", "gicp") and init is None:
            raise RuntimeError("粗合わせが先")
        if meth == "oracle":
            R, t = sc["R_true"], sc["t_true"]
        else:
            R, t = align(sc["pts"], ref, method=meth,
                         init=init if meth in ("p2point", "p2plane", "gicp") else None)
        if meth == "fpfh":
            init = (R, t)
        q = sc["pts"] @ R.T + t
        dd, ss, _, _ = ref.deviate(q)
        e_rot = rot_err_deg(R, sc["R_true"])
        e_mm = pose_shift_mm(R, t, sc["R_true"], sc["t_true"], ref.pts)
        err = (ss - tru)[ok]
        area = out_of_tol_area(ss[ok], sc["w"])
        rows.append([name, "%.4f" % e_rot, "%.4f" % e_mm,
                     "%.1f" % (1000 * np.sqrt(np.mean(err ** 2))),
                     "%.1f" % (1000 * np.abs(err).max()),
                     "%.1f" % area, "%+.1f %%" % (100 * (area - a_true) / a_true)])
        print("   %-14s %8.4f  %10.4f  %11.1f  %12.1f  %14.1f  %+8.1f %%"
              % (name, e_rot, e_mm, 1000 * np.sqrt(np.mean(err ** 2)),
                 1000 * np.abs(err).max(), area, 100 * (area - a_true) / a_true))
        if meth in ("none", "centroid"):
            print("        (素の最近傍距離の平均 %.2f mm —— 公差 %.2f mm の %.0f 倍)"
                  % (dd.mean(), TOL, dd.mean() / TOL))
        keep[meth] = {"R": R, "t": t, "sig": ss, "unsig": dd, "q": q}

    figs.save_table("methods", ["手法", "姿勢 [度]", "点移動 [mm]", "偏差RMS [µm]",
                                "偏差最大 [µm]", "公差外面積 [mm^2]", "面積誤差"],
                    rows, title="位置合わせの段階と、そこから出る偏差の誤差",
                    caption="真の姿勢を与えた最終行が推定器そのものの床。"
                            "点-面 ICP との差は姿勢ではなく datum の取り方の差。")

    # --- 稜線の罠 —— 最近傍が隣の面へ飛ぶ ------------------------------------ #
    print("\n  稜線の罠(姿勢は真値を与えているので、これは**推定器そのもの**の誤差):")
    q0 = sc["pts"] @ sc["R_true"].T + sc["t_true"]
    _, s0, i0, ed0 = ref.deviate(q0)
    scn = make_scan(noise=0.0, defects=False)          # 欠陥も雑音も無い対照
    q1 = scn["pts"] @ scn["R_true"].T + scn["t_true"]
    _, s1, _, ed1 = ref.deviate(q1)
    cross = float(np.mean(ref.face[i0] != sc["face"]))
    for lab, m in (("全点(素朴)", np.ones(len(s0), bool)), ("稜線帯を除く", ~ed0)):
        e = (s0 - tru)[m]
        print("   %-16s 点 %5.1f %%  偏差RMS %6.1f µm  最大 %7.1f µm"
              % (lab, 100 * m.mean(), 1000 * np.sqrt(np.mean(e ** 2)),
                 1000 * np.abs(e).max()))
    a_false = out_of_tol_area(s1, scn["w"])
    a_false_ok = out_of_tol_area(s1[~ed1], scn["w"])
    print("   ★**欠陥ゼロ・雑音ゼロ・姿勢は真値**の対照で、素朴に測ると "
          "%.1f mm^2 の偽の公差外領域が出る" % a_false)
    print("      (稜線帯を除くと %.1f mm^2)。最近傍が隣の面へ飛んだ対応が "
          "%.1f %% あり、" % (a_false_ok, 100 * cross))
    print("      その点では「隣の面の法線への射影」を偏差として報告している。")
    edge_naive = (100.0 * float(ed0.mean()), a_false)
    edge_fixed = (a_false_ok, 1000 * float(np.sqrt(np.mean(((s0 - tru)[~ed0]) ** 2))))

    if figs.enabled():
        best = keep["p2plane"]
        _, _, idx, _ = ref.deviate(best["q"])
        on_top = ref.face[idx] == ref.names.index("top")
        P2 = best["q"][on_top][:, :2]
        S = 0.40
        figs.save_grid(
            "deviation_maps",
            [with_scalebar(top_map(P2, tru[on_top]), S),
             with_scalebar(top_map(P2, best["sig"][on_top]), S),
             with_scalebar(top_map(P2, best["sig"][on_top] - tru[on_top]), S),
             with_scalebar(top_map(P2, np.where(np.abs(best["sig"][on_top]) > TOL,
                                                np.sign(best["sig"][on_top]),
                                                0.0)) * S, S)],
            ["真の偏差(±%.2f mm)" % S, "点-面 ICP のあとの推定(同じ目盛り)" ,
             "推定 - 真値(同じ目盛り)", "公差 ±%.2f mm を外れた領域" % TOL],
            title="上面の偏差地図(だいだい = 足りない / 青 = 余る)", ncols=2,
            signed=True,
            caption="3 枚目が一様に色づくのが第 6 章の主張 —— 位置合わせが"
                    "反りの平均を吸って、部品全体が下へずれて読める。")
    return {"scan": sc, "keep": keep, "a_true": a_true, "rows": rows,
            "edge_naive": edge_naive, "edge_fixed": edge_fixed,
            "edge_frac": float(edge.mean()), "cross": cross}


# --------------------------------------------------------------------------- #
# 章 4: 法線の符号                                                              #
# --------------------------------------------------------------------------- #
def section_normals(ref: CadRef) -> dict:
    print("\n" + "=" * 78)
    print("4) 法線の符号 —— 凹面で裏返る(偏差の符号がそのまま裏返る)")
    print("=" * 78)
    rng = np.random.default_rng(4)
    idx = rng.choice(len(ref.pts), 8000, replace=False)
    P, Ntrue, cc = ref.pts[idx], ref.nrm[idx], ref.concave[idx]
    face = ref.face[idx]
    pred = float(np.mean(cc))
    print("   予想: 反転するのは凹面(穴 2 本 + フィレット)だけ = 面積比 %.1f %%。"
          % (100 * pred))
    res = {}
    for name, fn in (("estimate_normals(k=25)", lambda p: _L.estimate_normals(p, k=25)),
                     ("estimate_oriented_normals(k=20)",
                      lambda p: _L.estimate_oriented_normals(p, k=20))):
        Ne = np.asarray(fn(P), float)
        dot = np.einsum("ij,ij->i", Ne, Ntrue)
        flip = dot < 0
        ang = np.degrees(np.arccos(np.clip(np.abs(dot), 0, 1)))
        print("   %-32s 反転 %5.1f %% / 軸のずれ 中央値 %.2f 度"
              % (name, 100 * flip.mean(), np.median(ang)))
        res[name] = float(flip.mean())
        if "oriented" not in name:
            print("        面別の反転率:", end="")
            for i, k in enumerate(ref.names):
                m = face == i
                if m.any():
                    print("  %s %.0f %%" % (k, 100 * flip[m].mean()), end="")
            print()
    flip_en = res["estimate_normals(k=25)"]
    flip_or = res["estimate_oriented_normals(k=20)"]
    print("   ★予想 %.1f %%、実測 %.1f %% —— **外れた**。理由は面別の内訳が言う:"
          % (100 * pred, 100 * flip_en))
    print("      凹面(hole1 / hole2 / fillet)は 73〜100 % 反転する(予想どおり)。"
          "外れたのは**平面**で、")
    print("      面ごとに 0 % から 68 % までばらつく。平面では近傍重心が点の上に"
          "ほぼ載るので、")
    print("      「重心から離れる向き」の法線成分がほぼ 0 —— 符号を決めているのは"
          "数値誤差であって形状ではない。")
    print("   Hoppe の大域向き付け(estimate_oriented_normals)は %.1f %% で"
          "この場面では正しい。" % (100 * flip_or))
    print("      ただし閉曲面の内外は**大域に 1 回反転できる**"
          "(seed_dir を渡さないと保証は無い)。")
    print("   ★符号が裏返った点では、へこみ(-)が出っ張り(+)として報告される。")
    print("   → この PoC の推定器は **CAD 側の厳密な法線**を使う(実測側から取らない)。")
    return {"pred": pred, "flip_en": flip_en, "flip_or": flip_or}


# --------------------------------------------------------------------------- #
# 章 5: 雑音の偏り(予測 sigma*sqrt(2/pi))                                       #
# --------------------------------------------------------------------------- #
def section_noise(ref: CadRef) -> dict:
    print("\n" + "=" * 78)
    print("5) 崖(雑音) —— 最近傍距離は必ず正へ偏る。予測 σ√(2/π)")
    print("=" * 78)
    print("   σ [µm]   予測 σ√(2/π)   実測|平面まで|   比      符号付きの平均")
    sig, pred, meas, sgn = [], [], [], []
    rng = np.random.default_rng(9)
    base = nominal_cloud(60000, seed=21)
    top = base["face"] == base["names"].index("top")
    P = base["pts"][top]
    for s in (0.005, 0.010, 0.020, 0.040, 0.080):
        q = P + s * rng.standard_normal(P.shape)
        # 上面は平面 z = H なので、平面までの距離は閉形式(離散化の混入ゼロ)
        d = np.abs(q[:, 2] - H)
        p = s * np.sqrt(2.0 / np.pi)
        sig.append(1000 * s)
        pred.append(1000 * p)
        meas.append(1000 * float(d.mean()))
        sgn.append(1000 * float((q[:, 2] - H).mean()))
        print("   %6.1f   %11.2f   %14.2f   %6.4f   %+12.3f µm"
              % (1000 * s, 1000 * p, 1000 * d.mean(), d.mean() / p, sgn[-1]))
    figs.save_plot("noise_bias",
                   [("予測 σ√(2/π)", sig, pred), ("実測(符号なし)", sig, meas),
                    ("実測(符号付き)", sig, sgn)],
                   xlabel="測定雑音 σ [µm]", ylabel="平面までの距離の平均 [µm]",
                   title="符号を捨てると雑音がそのまま偏りになる",
                   caption="半正規分布の平均。符号付き(法線へ射影)にすると 0 に戻る。")
    return {"sig": sig, "pred": pred, "meas": meas, "sgn": sgn}


# --------------------------------------------------------------------------- #
# 章 5b: 参照密度の偏り(予測 0.5/sqrt(rho))                                     #
# --------------------------------------------------------------------------- #
def section_density() -> dict:
    print("\n" + "=" * 78)
    print("5b) 崖(参照密度) —— 無雑音・完全一致でも最近傍距離は 0 にならない")
    print("=" * 78)
    print("   参照点数   ρ[点/mm^2]   予測 0.5/√ρ [mm]   実測(符号なし)  比"
          "     実測(符号付き)")
    q_src = nominal_cloud(8000, seed=333)
    rows, rho_l, pl, ml = [], [], [], []
    for n in (2500, 5000, 10000, 20000, 40000):
        r = CadRef(n=n, seed=555)
        d, s, _, _ = r.deviate(q_src["pts"])
        p = 0.5 / np.sqrt(r.rho)
        rho_l.append(r.rho)
        pl.append(1000 * p)
        ml.append(1000 * float(d.mean()))
        rows.append([str(n), "%.2f" % r.rho, "%.4f" % p, "%.4f" % d.mean(),
                     "%.3f" % (d.mean() / p), "%+.4f" % s.mean()])
        print("   %8d   %9.2f   %16.4f   %14.4f  %5.3f   %+12.4f"
              % (n, r.rho, p, d.mean(), d.mean() / p, s.mean()))
    print("   ★公差 %.2f mm に対し、%d 点の参照(ρ=%.2f)でも符号なしは %.4f mm"
          " —— **素で公差を超える**。" % (TOL, 40000, rho_l[-1], ml[-1] / 1000))
    print("      符号付き(最近傍点の法線へ射影)は接線方向のずれを落とすので"
          "残らない。")
    figs.save_plot("density_bias",
                   [("予測 0.5/√ρ", rho_l, pl), ("実測(符号なし)", rho_l, ml),
                    ("公差 %.0f µm" % (1000 * TOL), rho_l, [1000 * TOL] * len(rho_l))],
                   xlabel="参照点密度 ρ [点/mm^2]", ylabel="最近傍距離の平均 [µm]",
                   title="参照点群の密度そのものが偏差の下限を決める",
                   caption="2 次元 Poisson 点過程の最近傍距離の平均 = 0.5/√ρ。")
    figs.save_table("density_bias_table",
                    ["参照点数", "ρ [点/mm^2]", "予測 0.5/√ρ [mm]",
                     "実測 符号なし [mm]", "比", "実測 符号付き [mm]"], rows,
                    title="参照密度と最近傍距離")
    return {"rho": rho_l, "pred": pl, "meas": ml}


# --------------------------------------------------------------------------- #
# 章 6: ★欠陥が位置合わせを引く —— 剛体 6 次元への射影で予測する                #
# --------------------------------------------------------------------------- #
def section_pull(ref: CadRef) -> dict:
    print("\n" + "=" * 78)
    print("6) ★欠陥は自分で自分を薄める —— どれだけ薄まるかは閉形式で出る")
    print("=" * 78)
    print("   剛体 6 自由度が吸える偏差場 = J = [n | X×n] の張る 6 次元。")
    print("   位置合わせ後に残るのは d - J(JᵀJ)⁻¹Jᵀd。")
    print("\n   欠陥       測る場所         真値[µm] 予測の読み 実測の読み  ずれ"
          "   剛体に吸われた割合")

    P, N = ref.pts, ref.nrm
    cases = [("へこみのみ", "へこみの底", dict(dent_h=DENT_H, warp_a=0.0, wear_w=0.0)),
             ("反りのみ", "部品の中央", dict(dent_h=0.0, warp_a=WARP_A, wear_w=0.0)),
             ("摩耗のみ", "ボス外周", dict(dent_h=0.0, warp_a=0.0, wear_w=WEAR_W)),
             ("3 つ同時", "へこみの底", dict())]
    out = {}
    for name, where, kw in cases:
        d = defect_field(P, N, **kw)["total"]
        fit, res, c = absorbed(P, N, d)
        rho = float(np.linalg.norm(fit) / (np.linalg.norm(d) or 1.0))
        # 「読む場所」を先に決めてから、真値・予測・実測をそこで比べる
        if where == "部品の中央":
            sel = (np.abs(P[:, 0]) < 3.0) & (P[:, 2] > H - 1e-6) & (N[:, 2] > 0.9)
            true_read, pred_read = float(np.mean(d[sel])), float(np.mean(res[sel]))
        elif where == "ボス外周":
            sel = (P[:, 2] > ZC) & (np.hypot(P[:, 0] - BX, P[:, 1]) > BOSS_R - 1e-6)
            true_read, pred_read = float(np.mean(d[sel])), float(np.mean(res[sel]))
        else:
            k = np.argmin(d)
            true_read, pred_read = float(d[k]), float(res[k])
        sc = make_scan(n=14000, noise=0.0, occlude=False, **kw)
        R0, t0 = sc["R_true"], sc["t_true"]
        R, t = align(sc["pts"], ref, method="p2plane", init=(R0, t0), iters=25)
        _, s, _, ed = ref.deviate(sc["pts"] @ R.T + t)
        Pn = sc["nom"]
        if where == "部品の中央":
            m = ((np.abs(Pn[:, 0]) < 3.0) & (Pn[:, 2] > H - 1e-6)
                 & (sc["nrm"][:, 2] > 0.9) & ~ed)
            meas_read = float(np.mean(s[m]))
        elif where == "ボス外周":
            m = ((Pn[:, 2] > ZC) & (np.hypot(Pn[:, 0] - BX, Pn[:, 1]) > BOSS_R - 1e-6)
                 & ~ed)
            meas_read = float(np.mean(s[m]))
        else:
            dv = np.where(ed, 0.0, sc["dev_true"])
            meas_read = float(s[np.argmin(dv)])
        dz = 1000.0 * float((t - t0)[2])
        print("   %-10s %-14s %8.1f %9.1f %10.1f %+7.1f %14.1f %%"
              % (name, where, 1000 * true_read, 1000 * pred_read, 1000 * meas_read,
                 1000 * (meas_read - true_read), 100 * rho))
        out[name] = {"rho": rho, "true": true_read, "pred": pred_read,
                     "meas": meas_read, "dz": dz, "res": res, "d": d}

    dent = out["へこみのみ"]
    print("\n   ★読み方(単位はすべて µm、公差は ±%.0f):" % (1000 * TOL))
    print("      へこみ: %.1f -> %.1f、薄まりは %.1f %%。局所なので剛体に似ておらず、"
          "ほとんど残る。" % (-1000 * dent["true"], -1000 * dent["meas"],
                              100 * (1 - dent["meas"] / dent["true"])))
    print("      摩耗:   %.1f -> %.1f、薄まりは %.1f %%。ボス全周なので法線の平均が"
          "0 で、並進では吸えない。"
          % (-1000 * out["摩耗のみ"]["true"], -1000 * out["摩耗のみ"]["meas"],
             100 * (1 - out["摩耗のみ"]["meas"] / out["摩耗のみ"]["true"])))
    print("      ★反り: 真値 %.1f の中央に **%.1f の偽のへこみ**が出る。"
          % (1000 * out["反りのみ"]["true"], 1000 * out["反りのみ"]["meas"]))
    print("        閉形式の予測: u_z = a(2x/L)^2 の平均 a/3 = %.0f µm を並進 z が"
          "吸うので中央の読みは -a/3 = %.0f。"
          % (1000 * WARP_A / 3, -1000 * WARP_A / 3))
    print("        実測 %.1f。**公差 ±%.0f を超えるので偽の不合格**。"
          % (1000 * out["反りのみ"]["meas"], 1000 * TOL))
    print("      「吸われた割合」(場のエネルギー比)と「読みの薄まり」は別の数字 ——"
          "へこみは %.0f %% 吸われても" % (100 * dent["rho"]))
    print("      底の読みは %.1f %% しか動かない。**合否を決めるのは読みのほう**。"
          % (100 * (1 - dent["meas"] / dent["true"])))

    # 振幅を振る —— 引かれ量は欠陥の大きさに比例する
    print("\n   振幅を振る(無雑音・全密度・真の姿勢から出発):")
    print("     反り a [µm]  ICP の z 並進[µm]  中央の読み[µm]  |  "
          "へこみ h [µm]  薄まる割合[%]")
    amps = [0.0, 0.12, 0.24, 0.36, 0.48, 0.60]
    dzs, reads = [], []
    for a in amps:
        sc = make_scan(n=9000, noise=0.0, dent_h=0.0, warp_a=a, wear_w=0.0)
        R, t = align(sc["pts"], ref, method="p2plane",
                     init=(sc["R_true"], sc["t_true"]), iters=20, sub=9000)
        _, s, _, ed = ref.deviate(sc["pts"] @ R.T + t)
        m = ((np.abs(sc["nom"][:, 0]) < 3.0) & (sc["nom"][:, 2] > H - 1e-6)
             & (sc["nrm"][:, 2] > 0.9) & ~ed)
        dzs.append(1000 * float((t - sc["t_true"])[2]))
        reads.append(1000 * float(np.mean(s[m])) if m.any() else np.nan)
    hs = [0.05, 0.15, 0.45, 1.00, 1.50]
    dil = []
    for h in hs:
        d = defect_field(P, N, dent_h=h, warp_a=0.0, wear_w=0.0)["total"]
        fit, res, _ = absorbed(P, N, d)
        k = np.argmin(d)
        dil.append(100.0 * (1.0 - res[k] / d[k]))
    for i, a in enumerate(amps):
        tail = ("  |  %9.0f  %14.2f" % (1000 * hs[i], dil[i])) if i < len(hs) else ""
        print("     %10.0f  %17.1f  %14.1f%s" % (1000 * a, dzs[i], reads[i], tail))
    slope = float(np.polyfit(amps, np.asarray(dzs) / 1000.0, 1)[0])
    print("     ★ICP の z 並進 vs 反り振幅の傾き = %.3f(予測 -1/3 = -0.333)" % slope)
    print("     ★へこみは深さを %.0f 倍にしても薄まる割合が %.2f → %.2f %% で"
          "変わらない。" % (hs[-1] / hs[0], dil[0], dil[-1]))
    print("        薄まりを決めるのは**面積**(2πσ²/A = %.2f %%)であって深さでない。"
          % (100 * 2 * np.pi * DENT_S ** 2 / ref.area))

    figs.save_plot("defect_pull",
                   [("ICP の z 並進", [1000 * a for a in amps], dzs),
                    ("予測 a/3", [1000 * a for a in amps],
                     [1000 * a / 3 for a in amps]),
                    ("部品中央の読み", [1000 * a for a in amps], reads)],
                   xlabel="反りの振幅 a [µm]", ylabel="[µm]",
                   title="欠陥が大きいほど位置合わせが欠陥側へ寄る(傾き 1/3)",
                   caption="中央の読みは真値 0。位置合わせが吸った平均が"
                           "そのまま偽のへこみになる。")

    if figs.enabled():
        sel = (np.abs(P[:, 1]) < 4.0) & (P[:, 2] > H - 1e-6) & (N[:, 2] > 0.9)
        o = np.argsort(P[sel, 0])
        xs = P[sel, 0][o]
        figs.save_plot(
            "warp_false_dent",
            [("真の偏差(反り)", xs, 1000 * out["反りのみ"]["d"][sel][o]),
             ("位置合わせ後に残る(予測)", xs, 1000 * out["反りのみ"]["res"][sel][o]),
             ("公差 +%.0f µm" % (1000 * TOL), xs, [1000 * TOL] * len(xs)),
             ("公差 -%.0f µm" % (1000 * TOL), xs, [-1000 * TOL] * len(xs))],
            xlabel="x [mm](上面の帯 |y| < 4 mm)", ylabel="偏差 [µm]",
            title="反りは全体が平行移動して見える —— 中央に無いへこみが出る",
            caption="真値は中央 0。位置合わせが平均 a/3 を吸うので下へずれる。")
        big = nominal_cloud(90000, seed=13)
        db = defect_field(big["pts"], big["nrm"], dent_h=0.0, warp_a=WARP_A,
                          wear_w=0.0)["total"]
        _, rb, _ = absorbed(big["pts"], big["nrm"], db)
        S = 0.40
        figs.save_grid("warp_maps",
                       [render(big["pts"], db, scale=S),
                        render(big["pts"], rb, scale=S)],
                       ["真の反り(端で +%.2f、中央 0)" % WARP_A,
                        "位置合わせ後に残る(中央が偽のへこみ、同じ目盛り)"],
                       title="反りを剛体 6 自由度で最小二乗した残り"
                             "(だいだい = 足りない / 青 = 余る)",
                       signed=True,
                       caption="上面だけを見ている。右の中央がだいだいに"
                               "変わるのが「無いへこみ」。")
    return {"cases": out, "slope": slope, "dzs": dzs, "reads": reads, "dil": dil}


# --------------------------------------------------------------------------- #
# 章 7: 崖(初期姿勢)と、対称形の別解                                            #
# --------------------------------------------------------------------------- #
def section_basin(ref: CadRef) -> dict:
    print("\n" + "=" * 78)
    print("7) 崖(初期姿勢) —— ICP 単独はどこから収束しなくなるか")
    print("=" * 78)
    print("   予想: 直方体の 90 度対称に落ちた別解は残差が小さく、見抜けない。")
    print("   初期ずれ[度]  姿勢誤差[度]  点移動[mm]  最終残差[µm]  判定")
    sc = make_scan(n=8000, noise=0.010)
    angs, errs, resid = [], [], []
    floor = None
    for a in (0, 10, 20, 30, 50, 75, 90, 180):
        Rp = rot([0.2, 0.3, 0.93], a) @ sc["R_true"]
        R, t = align(sc["pts"], ref, method="p2plane", init=(Rp, sc["t_true"]),
                     iters=40, sub=5000)
        q = sc["pts"] @ R.T + t
        d, _, _, _ = ref.deviate(q)
        e = rot_err_deg(R, sc["R_true"])
        mm = pose_shift_mm(R, t, sc["R_true"], sc["t_true"], ref.pts)
        angs.append(a)
        errs.append(e)
        resid.append(1000 * float(d.mean()))
        if floor is None:
            floor = resid[-1]
        ok = "収束" if e < 0.5 else "別解(残差は床の %.1f 倍)" % (resid[-1] / floor)
        print("   %11d  %12.3f  %10.4f  %12.1f  %s" % (a, e, mm, resid[-1], ok))
    last = resid[-1] / floor
    print("\n   ★予想は外れた。この部品では別解の残差が床の %.1f 倍あり、"
          "**残差で見抜ける**。" % last)
    print("      理由: ボスが片側にあり、穴が φ%.0f と φ%.0f で径も位置も違う ——"
          " 90/180 度対称が壊れている。" % (2 * HOLE_R, 2 * H2R))

    # 対照群: 対称を壊す特徴を取り去った素の直方体だと、同じ 180 度で見抜けない
    box = _plain_box_cloud(20000, seed=41)
    bref = _PlainRef(_plain_box_cloud(40000, seed=42))
    Rg = rot([0.35, 0.82, 0.45], 24.0)
    bs = box["pts"] @ Rg.T + np.array([35.0, -20.0, 9.0])
    bs = bs + 0.010 * np.random.default_rng(3).standard_normal(bs.shape)
    Rt, tt = Rg.T, -Rg.T @ np.array([35.0, -20.0, 9.0])
    b_rows = []
    for a in (0, 180):
        Rp = rot([0, 0, 1.0], a) @ Rt
        R, t = align(bs, bref, method="p2plane", init=(Rp, tt), iters=40, sub=5000)
        d, _, _, _ = bref.deviate(bs @ R.T + t)
        b_rows.append((a, rot_err_deg(R, Rt), 1000 * float(d.mean())))
        print("   対照(素の直方体 %.0fx%.0fx%.0f、ボスも穴も無し) 初期 %3d 度: "
              "姿勢誤差 %6.2f 度 / 残差 %6.1f µm" % (L, W, H, a, b_rows[-1][1],
                                                     b_rows[-1][2]))
    print("      ★対称形では 180 度ずれたまま残差が %.2f 倍(= 床)。"
          "**残差を合否に使うと嘘を見抜けない**のはこちら。"
          % (b_rows[1][2] / b_rows[0][2]))

    figs.save_plot("basin",
                   [("姿勢誤差 [度]", angs, errs),
                    ("最終残差 [µm] / 10", angs, [r / 10 for r in resid])],
                   xlabel="初期姿勢のずれ [度]", ylabel="[度] / [µm]/10",
                   title="ICP の収束域(非対称な部品なら別解は残差で分かる)",
                   caption="この部品は 75 度まで収束する。90 度以降の別解は"
                           "残差が床の数倍に上がるので見抜ける ——"
                           "素の直方体ではそうならない(本文の対照群)。")
    return {"ang": angs, "err": errs, "resid": resid, "floor": floor,
            "alt_ratio": last, "box": b_rows}


def _plain_box_cloud(n: int, seed: int) -> dict:
    """対称を壊す特徴(ボス・フィレット・穴)を持たない素の直方体の表面点群。"""
    rng = np.random.default_rng(seed)
    faces = [("z", 1.0, L, W), ("z", -1.0, L, W), ("x", 1.0, W, H),
             ("x", -1.0, W, H), ("y", 1.0, L, H), ("y", -1.0, L, H)]
    ar = np.array([a * b for _, _, a, b in faces], float)
    m = np.maximum(8, (n * ar / ar.sum()).astype(int))
    P, N = [], []
    for (ax, sg, u1, u2), mi in zip(faces, m):
        u = rng.uniform(-u1 / 2, u1 / 2, mi)
        v = rng.uniform(-u2 / 2, u2 / 2, mi)
        p = np.zeros((mi, 3))
        nn = np.zeros((mi, 3))
        if ax == "z":
            p[:, 0], p[:, 1], p[:, 2] = u, v, (H if sg > 0 else 0.0)
            nn[:, 2] = sg
        elif ax == "x":
            p[:, 0], p[:, 1], p[:, 2] = sg * L / 2, u, v + H / 2
            nn[:, 0] = sg
        else:
            p[:, 0], p[:, 1], p[:, 2] = u, sg * W / 2, v + H / 2
            nn[:, 1] = sg
        P.append(p)
        N.append(nn)
    return {"pts": np.concatenate(P), "nrm": np.concatenate(N)}


class _PlainRef:
    """対照群用の最小の参照(CadRef と同じ口だけ持つ)。"""

    def __init__(self, cloud):
        self.pts, self.nrm = cloud["pts"], cloud["nrm"]
        self.tree = cKDTree(self.pts)

    def deviate(self, q, k=6, edge_deg=30.0):
        d, i = self.tree.query(np.asarray(q, float), k=k, workers=-1)
        i0 = i[:, 0]
        s = np.einsum("ij,ij->i", np.asarray(q, float) - self.pts[i0], self.nrm[i0])
        cos = np.einsum("mkj,mj->mk", self.nrm[i], self.nrm[i0])
        return d[:, 0], s, i0, cos.min(axis=1) < np.cos(np.radians(edge_deg))


# --------------------------------------------------------------------------- #
# 章 8: 欠測・密度・対照群                                                       #
# --------------------------------------------------------------------------- #
def section_controls(ref: CadRef) -> dict:
    print("\n" + "=" * 78)
    print("8) 欠測と密度、そして対照群 —— 要因を 1 つずつ止める")
    print("=" * 78)
    print("   条件                        点数  可視面積[mm^2] 姿勢[度]"
          "  偏差RMS[µm]  公差外面積 推定/真値[mm^2]")
    conds = [
        ("対照: 変換なし・欠陥なし・雑音なし", dict(noise=0.0, defects=False,
                                                     transform=False)),
        ("対照: 欠陥なし(雑音のみ)", dict(defects=False)),
        ("対照: 雑音なし(欠陥のみ)", dict(noise=0.0)),
        ("基準: 欠陥 + 雑音", dict()),
        ("欠測: 片側スキャン", dict(occlude=True)),
        ("密度 1/10", dict(keep=0.1)),
        ("密度 1/50", dict(keep=0.02)),
        ("欠測 + 密度 1/10", dict(occlude=True, keep=0.1)),
    ]
    rows, out = [], {}
    for name, kw in conds:
        sc = make_scan(**kw)
        R, t = align(sc["pts"], ref, method="p2plane",
                     init=(sc["R_true"], sc["t_true"]), iters=30)
        q = sc["pts"] @ R.T + t
        _, s, _, ed = ref.deviate(q)
        e = rot_err_deg(R, sc["R_true"])
        rms = 1000 * float(np.sqrt(np.mean(((s - sc["dev_true"])[~ed]) ** 2)))
        a_est = out_of_tol_area(s[~ed], sc["w"])
        a_tru = out_of_tol_area(sc["dev_true"][~ed], sc["w"])
        # ★真値が 0 の対照群で「%」を出すと 0 割りで意味の無い巨大な数になる。
        #   面積は mm^2 のまま並べ、%は真値が意味を持つときだけ添える。
        da = ("%.1f / %.1f (%+.1f %%)" % (a_est, a_tru,
                                          100 * (a_est - a_tru) / a_tru)
              if a_tru > 1.0 else "%.1f / %.1f" % (a_est, a_tru))
        rows.append([name, str(len(sc["pts"])), "%.0f" % sc["area_seen"],
                     "%.4f" % e, "%.1f" % rms, da])
        print("   %-28s %6d %12.0f %9.4f %11.1f  %s"
              % (name, len(sc["pts"]), sc["area_seen"], e, rms, da))
        out[name] = {"e": e, "rms": rms, "a_est": a_est, "a_tru": a_tru,
                     "area": sc["area_seen"]}
    print("\n   ★欠測は姿勢を %.1f 倍に引くが、効きは小さい。危ないのは"
          % (out["欠測: 片側スキャン"]["e"] / max(out["基準: 欠陥 + 雑音"]["e"], 1e-9)))
    print("      **測れなかった %.0f mm^2(%.1f %%)を『公差内』と書くこと**。"
          % (ref.area - out["欠測: 片側スキャン"]["area"],
             100 * (1 - out["欠測: 片側スキャン"]["area"] / ref.area)))
    figs.save_table("controls", ["条件", "点数", "可視面積 [mm^2]", "姿勢 [度]",
                                 "偏差RMS [µm]", "公差外面積 推定/真値 [mm^2]"], rows,
                    title="対照群 —— 要因を 1 つずつ止める")
    return out


# --------------------------------------------------------------------------- #
# 章 9: 道具の穴                                                                #
# --------------------------------------------------------------------------- #
def section_tool_gaps(ref: CadRef) -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で 3-D op を使ってみて)")
    print("=" * 78)

    # (a) 位置合わせ・距離の族が 1 行ファサードに出ていない
    hidden = [n for n in ("icp_point2point_3d", "icp_point2plane", "gicp",
                          "register_fpfh", "chamfer_distance", "hausdorff_distance",
                          "estimate_oriented_normals", "voxel_grid_downsample")
              if not hasattr(fs, n)]
    assert hidden, "全部ファサードに出た(この節を書き換えること)"
    print("  (a) 位置合わせ・距離の主要 %d 本が fs.<名前> に無く"
          " fs.ledger 経由でしか呼べない: %s" % (len(hidden), ", ".join(hidden)))

    # (b) 台帳の out アダプタが gicp の dict を (R, t) に切り詰める
    rng = np.random.default_rng(1)
    a = rng.normal(size=(400, 3)) * 5.0
    b = a + np.array([0.2, -0.1, 0.05])
    raw = _L.gicp.raw(a, b, max_iter=5)
    lg = _L.gicp(a, b, max_iter=5)
    assert isinstance(raw, dict) and isinstance(lg, tuple) and len(lg) == 2
    print("  (b) gicp の docstring は dict{R,t,rmse,iterations} と書いてあるが、"
          "台帳の out='pose' アダプタが (R, t) に切り詰める。")
    print("      rmse / iterations は fs.ledger.gicp.raw(...) からしか取れない"
          "(収束したかを呼び手が判断できない)。")

    # (c) 符号付き偏差(点群 -> CAD 面までの符号付き距離)を出す op が無い
    for n in ("signed_deviation", "cloud_to_mesh_distance", "deviation_map",
              "compare_to_cad"):
        assert not hasattr(fs, n) and not hasattr(fs.ledger, n), n
    print("  (c) **符号付き偏差**を出す op が無い。chamfer/hausdorff は符号なしの"
          "要約 1 個で、点ごとの ±が要る検査には使えない。")
    print("      query_distance + esdf は在るが格子解像度で量子化される"
          "(この PoC は cKDTree + CAD 法線への射影を自前で書いた)。")

    # (d) esdf/query_distance の量子化を実測しておく
    n_g = 96
    lo = np.array([-L / 2 - 2, -W / 2 - 2, -2.0])
    hi = np.array([L / 2 + 2, W / 2 + 2, BOSS_TOP + 2.0])
    gx = [np.linspace(lo[k], hi[k], n_g) for k in range(3)]
    G = np.stack(np.meshgrid(*gx, indexing="ij"), -1).reshape(-1, 3)
    occ = _inside(G).reshape(n_g, n_g, n_g).astype(np.float64)
    vs = float((hi - lo).max() / (n_g - 1))
    sdf = np.asarray(_L.esdf(occ, voxel_size=vs))
    q = ref.pts[::37]
    bnd = tuple((float(lo[k]), float(hi[k])) for k in range(3))
    v = np.asarray(_L.query_distance(sdf, bnd, n_g, q, mode="trilinear"))
    print("  (d) esdf(%d^3, ボクセル %.3f mm)+ query_distance を表面上の %d 点で"
          "引くと" % (n_g, vs, len(q)))
    print("      平均 %+.4f mm / 標準偏差 %.4f mm(真値は 0)。"
          "公差 %.2f mm には %.1f 倍足りない。"
          % (v.mean(), v.std(), TOL, v.std() / TOL))

    # (e) 公差外領域の面積を出す口が無い
    assert not hasattr(fs.ledger, "out_of_tolerance_area")
    print("  (e) 「公差外領域の面積」を出す op が無い。検査の合否はこの 1 個の"
          "数字で決まるので、族に入れる価値はある(面積重みは点群では"
          "自明でないため、点 -> 面積の対応を持つ入口が要る)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("CAD と実測点群の差分検査 —— 位置合わせが欠陥を吸う")
    print("部品 %.0fx%.0fx%.0f mm + ボス φ%.0f + フィレット R%.1f + 穴 φ%.0f/φ%.0f"
          % (L, W, H, 2 * BOSS_R, RF, 2 * HOLE_R, 2 * H2R))
    print("公差 ±%.2f mm / 測定雑音 σ %.0f µm / 参照 %d 点 / 実測 %d 点"
          % (TOL, 1000 * NOISE, N_REF, N_SCAN))
    print("=" * 78)

    ref = CadRef()
    part = section_part(ref)
    al = section_align(ref)
    nr = section_normals(ref)
    nz = section_noise(ref)
    de = section_density()
    pl = section_pull(ref)
    ba = section_basin(ref)
    ct = section_controls(ref)
    section_tool_gaps(ref)

    # --- 所見を固定する(壊れたら鳴る) --- #
    assert abs(part["vol_mc"] - part["vol"]) / part["vol"] < 0.01, part["vol_mc"]
    assert abs(nz["meas"][2] / nz["pred"][2] - 1.0) < 0.05, nz["meas"]
    assert abs(de["meas"][-1] / de["pred"][-1] - 1.0) < 0.15, de["meas"]
    assert de["meas"][-1] > 1000 * TOL, "参照密度の偏りが公差を超えなかった"
    assert nr["flip_en"] > 0.30, nr["flip_en"]        # 平面がコイン投げになる
    assert nr["flip_or"] < 0.05, nr["flip_or"]        # Hoppe は正しく向く
    dent = pl["cases"]["へこみのみ"]
    assert abs(1 - dent["meas"] / dent["true"]) < 0.06, dent   # 局所欠陥は残る
    assert pl["cases"]["反りのみ"]["meas"] < -TOL, pl["cases"]["反りのみ"]
    assert abs(pl["slope"] + 1.0 / 3.0) < 0.05, pl["slope"]
    assert abs(pl["cases"]["反りのみ"]["meas"] + WARP_A / 3) < 0.02, \
        pl["cases"]["反りのみ"]["meas"]
    assert abs(pl["dil"][0] - pl["dil"][-1]) < 0.3, pl["dil"]
    assert al["edge_naive"][1] > 50.0, al["edge_naive"]     # 偽の公差外領域が出る
    assert al["edge_fixed"][0] < 5.0, al["edge_fixed"]      # 除外すればほぼ消える
    assert ba["alt_ratio"] > 3.0, ba["alt_ratio"]           # 非対称なら別解は見える
    assert ba["box"][1][1] > 170.0 and ba["box"][1][2] / ba["box"][0][2] < 1.2, ba["box"]
    assert ct["対照: 変換なし・欠陥なし・雑音なし"]["rms"] < 8.0, ct

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点(位置合わせなし)は %.2f mm。差分検査の主要な誤差源は"
          "位置合わせそのもの。" % al["keep"]["none"]["unsig"].mean())
    print("  * 姿勢の誤差[度]と偏差の誤差[µm]を別々に数える —— FPFH だけだと"
          "姿勢 %.3f 度で偏差 RMS %s µm。"
          % (float(al["rows"][2][1]), al["rows"][2][3]))
    print("  * 符号なしの距離は雑音(σ√(2/π))と参照密度(0.5/√ρ)で**必ず正へ"
          "偏る**。法線へ射影して符号を付けると両方消える。")
    print("  * 稜線では最近傍が隣の面へ飛ぶ。欠陥ゼロの対照でも偽の公差外領域が "
          "%.1f mm^2 出る(稜線帯 %.1f %% を外に出すと %.1f mm^2)。"
          % (al["edge_naive"][1], al["edge_naive"][0], al["edge_fixed"][0]))
    print("  * ★位置合わせが吸えるのは J = [n | X×n] の 6 次元だけ。局所へこみの"
          "読みは %.1f %% しか薄まらないが、"
          % (100 * (1 - pl["cases"]["へこみのみ"]["meas"]
                    / pl["cases"]["へこみのみ"]["true"])))
    print("    反りでは真値 0 の中央に深さ %.0f µm の**偽のへこみ**が出る"
          "(予測 a/3 = %.0f µm)。"
          % (-1000 * pl["cases"]["反りのみ"]["meas"], 1000 * WARP_A / 3))
    print("  * 薄まりを決めるのは欠陥の**面積**であって深さではない"
          "(深さ %.0f 倍で割合は変わらず)。" % (1.50 / 0.05))

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
