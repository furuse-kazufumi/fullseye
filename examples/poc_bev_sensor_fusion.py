# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""鳥瞰図への多センサ融合 —— 画像で 5 px のずれが、遠方では 1 台ぶん動く。

自動運転・移動ロボットの定番である「**低い位置の LiDAR** と **高い位置の深度
カメラ**を共通の鳥瞰格子(BEV)に投影して融合する」仕事です。真値は解析的な
場面(地面 + 直方体の障害物 + 側壁)から作り、両センサの**外部パラメータ
(R, t)は既知**として与えたうえで、その既知値を**わざと間違えて**いきます。

EXTEND: 実測に差し替えるなら :func:`scan_lidar` と :func:`scan_camera` の
戻り値(センサ座標の点群 (N,3) と深度画像)を実機の 1 スキャンに置き換えます。
実データでは (a) 真の外部パラメータが無いので「誤差 0」の行が作れず、
基準は**別の校正結果**にしかならない、(b) 占有の真値が無いので IoU は人手の
箱ラベルの footprint に対してしか測れず、本 PoC の「未知セルを評価から外す」
扱い(:func:`known_mask`)が使えない、(c) 時刻ずれは自車のオドメトリで
しか推定できない —— の 3 点が変わります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**画像の再投影誤差で校正を報告すると、BEV の壊れ方が見えない**。
   外部の yaw を 1.00 度ずらしたときの画像上の再投影誤差は **4.63 px**
   (画像の対角の 0.9 %)で、校正レポートなら合格に見える。同じ誤差は
   BEV では距離に比例し、22.0 m の車で **0.384 m = 1.9 セル**動く。
   px は角度の指標、BEV は長さの指標で、**換算係数が距離そのもの**。
2. ★★**融合が単センサに勝つのは「見えていない場所」でだけ**。低い LiDAR
   (高さ 0.55 m)は先行車の陰に入る 22 m の車を **1 セルも**返せない
   (既知セル 0 個)。高いカメラ(1.90 m)は屋根越しに見えるので、融合の
   IoU は LiDAR 単独 0.5991 → 0.7666(+0.1675)。一方カメラ単独は 0.5714 で
   **LiDAR 単独より低い**。勝っているのは精度ではなく**視界**。
3. ★**融合の規則で壊れ方の種類が変わる**。yaw 1.00 度で 最大値則の適合率は
   0.503(偽占有 1245 セル)、平均則の再現率は 0.615(見逃し 483 セル)——
   同じ誤差から、片方は偽物を作り、もう片方は本物を消す。IoU は 0.363 と
   0.501 で、**IoU 1 本ではこの違いが出ない**。
4. ★**回転の崖は幾何で予測できる**。角度 θ の誤差は距離 R の点を Rθ 動かす
   ので、セル c=0.200 m を超えるのは R > c/θ。θ=0.50 度なら 22.9 m、
   1.00 度なら 11.5 m、2.00 度なら 5.7 m。実測の「1 セル以上ずれた占有
   セルの割合」は 0.29 / 0.61 / 0.87 で、予測(評価窓内の占有セルのうち
   R>c/θ の割合)0.27 / 0.60 / 0.88 と一致した(最大差 0.02)。
5. ★★**並進の崖は距離に依らないので、近くから壊れる**。100 mm(= c/2)を
   超えると全距離帯で一斉に 1 セルずれる。距離帯別に割ると、回転 1.00 度
   では 5-12 m 帯の IoU 0.632 に対し 18-28 m 帯は 0.144(4.4 倍の差)、
   並進 150 mm では 0.564 と 0.529 で **ほぼ平ら**(1.07 倍)。同じ IoU の
   低下でも、**どこが壊れたかは正反対**。
6. ★**時刻ずれは、この速度域では並進とほぼ同じもの**。自車 14.0 m/s・
   ヨー角速度 5.0 度/s で Δt=40 ms なら並進 560 mm・回転 0.20 度。20 m 地点
   での寄与は並進 0.560 m 対 回転 0.070 m で **8.0 倍**の開き。実測でも
   時刻ずれ 40 ms の IoU 0.2984 は、同量の純並進 0.3013 とほぼ一致し
   (差 0.0029)、純回転 0.20 度の 0.7562 とは全く違う。
7. ★★**融合が単センサより悪くなる領域がある**。カメラ側だけを yaw 1.00 度
   ずらすと、最大値則の IoU 0.363 は **LiDAR 単独 0.599 を下回る**。
   誤差のあるセンサを足すと、正しいセンサの結果まで汚れる。信頼度重み則
   (校正の宣言誤差 0.30 度と深度雑音から重みを作る)は 0.660 で、
   ★予想「重み則なら LiDAR 単独を上回り続ける」は**外れ**た —— 0.50 度で
   0.712、1.00 度で 0.660 と、やはり 1 度では単独に届かない。
8. **偽占有は「どれだけ外れた所」に出るかで数えないと分からない**。yaw
   1.00 度の最大値則の偽占有セルは、真の障害物からの距離(ESDF)の中央値が
   **0.383 m**(2 セル)で、大半は輪郭の帯。並進 150 mm では 0.283 m。
   偽占有の**個数**が同じでも、遠くに散るか輪郭に貼りつくかは別の話。
9. ★**高さは 1 セル刻みに潰れる**。ボクセル 0.200 m の格子では高さ誤差の
   下限は c/2 = 0.100 m で、誤差 0 の融合の実測 中央値 0.079 m は
   その水準。yaw 1.00 度では 0.079 → 0.107 m。**高さは占有ほど壊れない**
   —— ずれた先のセルにも似た高さの物が居るから。
10. ★整形(closing)は unknown を埋めて footprint に近づけるが、**偽占有も
    同じ倍率で太る**。誤差 0 では占有セルが 2.30 倍になり solid footprint
    に対する IoU が 0.2497 → 0.4441 に上がるが、yaw 1.00 度では偽占有が
    1245 → 3739 セル(3.00 倍)に増える。整形は判断を増幅する装置で、
    誤差を直しはしない。

【グラウンドトゥルース】
場面は**解析的**: 地面 z=0 の平面と、軸平行直方体 5 個(先行車・その先の車・
路肩の車・歩行者・側壁)。BEV の真値占有は :func:`fullseye.ledger.grid_coords`
で作ったボクセル中心に :func:`box_sdf` を評価して :func:`sdf_union` /
:func:`sdf_to_occupancy` で合成する —— **式で決まる**。高さの真値も同じ式。
観測は解析的な光線 - 直方体交差(slab 法)で作り、LiDAR は距離雑音、カメラは
深度の 2 乗に比例する雑音を載せる。評価窓は前方 3-30 m・左右 9 m、評価対象は
**真の校正で少なくとも一方のセンサから見通せたセル**(:func:`known_mask`)に
限る —— 車体内部のように**どちらからも見えないセルを分母に入れると、
上限が幾何で決まってしまい規則の差が埋もれる**。

来歴(公開文献のみ): Moravec & Elfes, *Proc. IEEE ICRA* (1985) 116 —— 占有格子 /
Elfes, *IEEE Computer* 22 (1989) 46 —— occupancy grid の定式化 /
Levinson & Thrun, *Robotics: Science and Systems* (2013) —— カメラ・レーザの
外部校正のドリフト / Philion & Fidler, *ECCV* (2020) 194 —— Lift-Splat-Shoot
(カメラから BEV へ) / Olson, *IEEE/RSJ IROS* (2010) 1059 —— 受動的な時刻同期。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- BEV 格子 ---------------------------------------------------------------- #
#: 世界の箱。**``occupancy_grid`` は立方 res³ しか取らない**ので、BEV に要る
#: のは x,y 方向の細かさだけなのに z も同じ刻みで 32 m ぶん確保している
#: (9 節の「道具の穴」で数える)。
BOUNDS = ((0.0, 32.0), (-16.0, 16.0), (0.0, 32.0))
RES = 160                      # 1 辺のボクセル数 → セル 0.200 m
CELL = (BOUNDS[0][1] - BOUNDS[0][0]) / RES

Z_LO, Z_HI = 0.30, 2.60        # 占有を数える帯 [m](地面と高すぎる物を外す)
K0, K1 = int(Z_LO / CELL), int(Z_HI / CELL) + 1

WIN_X = (3.0, 30.0)            # 評価窓 [m]
WIN_Y = (-9.0, 9.0)

# --- 場面(真値はすべて式で決まる)------------------------------------------- #
#: 障害物。面の位置は**セル中心と境界のちょうど中間**(四分の一セル = 0.05 m)に
#: 置いてある。★これは飾りではない:
#:   * 面をセル**境界**に載せると、面の返りが雑音で隣へ半分こぼれ、適合率が
#:     discretisation だけで 0.5 に落ちる。
#:   * 面をセル**中心**に載せると、今度は真値のほうが浮動小数の丸めで
#:     入ったり入らなかったりする(実際に踏んだ: 側壁の返る列が真値から
#:     外れ、偽占有 133 セルのうち大半がそれだった)。
#: 中間に置けば両方が起きない。``h`` は **0.2 m の倍数を避けて**ある ——
#: 高さの量子化を見せるため。``lx``/``ly`` は 0.1 m の**奇数倍**にする。
OBSTACLES = (
    # 遮蔽物は**帯より高い**トラック(h > Z_HI)。低い車にすると、屋根の上を
    # 通る視線が向こう側に届いてしまい、影が横位置だけでは決まらなくなる。
    {"name": "先行トラック", "cx": 10.2, "cy": 0.0, "lx": 6.3, "ly": 2.3,
     "h": 2.73},
    {"name": "左の遠方車", "cx": 22.1, "cy": 2.8, "lx": 4.5, "ly": 1.9, "h": 1.47},
    {"name": "右の遠方車", "cx": 22.1, "cy": -2.8, "lx": 4.5, "ly": 1.9, "h": 1.51},
    {"name": "路肩の車", "cx": 13.2, "cy": -4.2, "lx": 4.3, "ly": 1.9, "h": 1.44},
    {"name": "歩行者", "cx": 7.0, "cy": 3.2, "lx": 0.7, "ly": 0.7, "h": 1.72},
    {"name": "側壁", "cx": 16.1, "cy": 6.1, "lx": 24.1, "ly": 0.5, "h": 2.38},
)

#: LiDAR は**左のミラー**、カメラは**右のミラー**。高さは同じ(屋根の見えかたを
#: 揃えて、差が「横位置による陰の違い」だけになるようにする)。``div`` はビーム
#: 発散(3 mrad)—— 距離に比例して足跡が広がる。
LIDAR = {"C": np.array([0.0, 0.90, 1.85]), "rmax": 32.0, "sigma": 0.020,
         "div": 0.003, "az": 70.0, "daz": 0.15, "el": (-16.0, 4.0), "nel": 64}
#: 深度カメラ: σ_z = ``kz``·z²(ステレオの視差量子化に相当)、測距 25 m まで。
CAM = {"C": np.array([0.0, -0.90, 1.85]), "zmax": 25.0, "kz": 0.0008,
       "W": 320, "H": 240, "f": 265.0}

#: 融合器が**宣言している**外部校正の不確かさ [deg]。信頼度重みはこれで作る。
SIGMA_THETA_DEG = 0.30
#: 時刻ずれの節で使う自車運動。
EGO_V, EGO_YAWRATE = 14.0, 5.0        # [m/s], [deg/s]

SEED = 11


# --------------------------------------------------------------------------- #
# 幾何 —— 光線と直方体(slab 法)                                              #
# --------------------------------------------------------------------------- #
def _box_lohi(o: dict):
    return (np.array([o["cx"] - o["lx"] / 2, o["cy"] - o["ly"] / 2, 0.0]),
            np.array([o["cx"] + o["lx"] / 2, o["cy"] + o["ly"] / 2, o["h"]]))


def ray_box(origin, dirs, lo, hi):
    """光線 (origin, dirs) と AABB の交差。``(t_enter, t_exit, hit)`` を返す。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / dirs
        t1 = (lo - origin) * inv
        t2 = (hi - origin) * inv
    tn = np.nanmax(np.minimum(t1, t2), axis=1)
    tf = np.nanmin(np.maximum(t1, t2), axis=1)
    return tn, tf, (tf >= np.maximum(tn, 0.0)) & (tf > 0.0)


def cast(origin, dirs, rmax: float):
    """地面 z=0 と全障害物へ光線を飛ばし、**最も近い**当たりまでの距離を返す。"""
    t = np.full(dirs.shape[0], np.inf)
    dz = dirs[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        tg = -origin[2] / dz
    ok = (dz < -1e-9) & (tg > 0)
    t = np.where(ok, np.minimum(t, tg), t)
    for o in OBSTACLES:
        lo, hi = _box_lohi(o)
        tn, tf, hit = ray_box(origin, dirs, lo, hi)
        tb = np.where(tn > 0, tn, tf)
        t = np.where(hit & (tb > 0) & (tb < t), tb, t)
    return np.where(t <= rmax, t, np.inf)


# --------------------------------------------------------------------------- #
# 観測 —— センサ座標の点群を作る                                                #
# --------------------------------------------------------------------------- #
def scan_lidar(rng) -> np.ndarray:
    """LiDAR の 1 スキャン。返り値は **センサ座標** (N,3)(x 前・y 左・z 上)。"""
    az = np.radians(np.arange(-LIDAR["az"], LIDAR["az"] + 1e-9, LIDAR["daz"]))
    el = np.radians(np.linspace(LIDAR["el"][0], LIDAR["el"][1], LIDAR["nel"]))
    A, E = np.meshgrid(az, el, indexing="ij")
    A, E = A.ravel(), E.ravel()
    d = np.stack([np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E)], 1)
    t = cast(LIDAR["C"], d, LIDAR["rmax"])
    good = np.isfinite(t)
    r = t[good] + LIDAR["sigma"] * rng.standard_normal(int(good.sum()))
    return d[good] * r[:, None]


def scan_camera(rng):
    """深度カメラの 1 枚。``(depth 画像, センサ座標の点群)`` を返す。

    カメラ座標は ``Xc`` 右 = ``-y_w``、``Yc`` 下 = ``-z_w``、``Zc`` 前 = ``+x_w``。
    深度画像から点群に戻すのは :func:`fullseye.ledger.depth_to_points`(公開 op)。
    """
    W, H, f = CAM["W"], CAM["H"], CAM["f"]
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
    u, v = np.meshgrid(np.arange(W), np.arange(H))
    dc = np.stack([(u - cx) / f, (v - cy) / f, np.ones_like(u, float)], -1)
    dc = dc / np.linalg.norm(dc, axis=-1, keepdims=True)
    # カメラ座標 -> 世界座標(真の姿勢、yaw 0)
    R_wc = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
    dw = dc.reshape(-1, 3) @ R_wc.T
    t = cast(CAM["C"], dw, CAM["zmax"] / dc[..., 2].min())
    z = t * dc.reshape(-1, 3)[:, 2]                     # 視線方向 -> 光軸方向
    z = np.where(np.isfinite(z) & (z <= CAM["zmax"]), z, 0.0)
    z = np.where(z > 0, z + CAM["kz"] * z ** 2 * rng.standard_normal(z.size), 0.0)
    depth = np.clip(z, 0.0, None).reshape(H, W)
    pc = np.asarray(fs.ledger.depth_to_points(depth, f, f, cx, cy))
    pts = pc @ R_wc.T                                   # センサ座標(= 世界の向き)
    return depth, pts


# --------------------------------------------------------------------------- #
# 姿勢誤差                                                                      #
# --------------------------------------------------------------------------- #
def rz(deg: float) -> np.ndarray:
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def place(pts_sensor: np.ndarray, C: np.ndarray, dyaw=0.0, dt=(0.0, 0.0, 0.0)):
    """センサ座標の点群を、**思い込みの外部パラメータ**で世界座標へ置く。"""
    return pts_sensor @ rz(dyaw).T + C + np.asarray(dt, float)


# --------------------------------------------------------------------------- #
# 真値の BEV(op で作る)                                                       #
# --------------------------------------------------------------------------- #
def ground_truth():
    """占有と高さの真値。占有は ``grid_coords`` + ``box_sdf`` + ``sdf_union``。"""
    zc = (Z_LO + Z_HI) / 2.0
    coords = np.asarray(fs.ledger.grid_coords(
        (BOUNDS[0], BOUNDS[1], (0.4, 0.6)), (RES, RES, 1)))
    sdf = None
    for o in OBSTACLES:
        lo, hi = _box_lohi(o)
        c = (lo + hi) / 2.0
        s = fs.ledger.box_sdf(coords, c, (hi - lo) / 2.0)
        sdf = s if sdf is None else fs.ledger.sdf_union(sdf, s)
    occ = np.asarray(fs.ledger.sdf_to_occupancy(sdf))[:, :, 0] > 0.5
    xs = BOUNDS[0][0] + (np.arange(RES) + 0.5) * CELL
    ys = BOUNDS[1][0] + (np.arange(RES) + 0.5) * CELL
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    hgt = np.zeros((RES, RES))
    for o in OBSTACLES:
        inside = ((np.abs(X - o["cx"]) <= o["lx"] / 2)
                  & (np.abs(Y - o["cy"]) <= o["ly"] / 2))
        hgt = np.where(inside, np.maximum(hgt, o["h"]), hgt)
    del zc
    return occ, hgt, X, Y


def window_mask(X, Y):
    return ((X >= WIN_X[0]) & (X <= WIN_X[1])
            & (Y >= WIN_Y[0]) & (Y <= WIN_Y[1]))


# --------------------------------------------------------------------------- #
# 見通し(known)—— 分母をここで決める                                          #
# --------------------------------------------------------------------------- #
#: 「自由」と言い切るために見通せねばならない高さ [m](帯のいちばん下)。
#: **上のほうだけ見えても自由とは言えない** —— 車の屋根の上は見通せても、
#: その真下に車が居る。占有格子の 3 状態(占有 / 自由 / 未知)の「自由」は
#: 帯の下端まで視線が通ったセルに限る。
LOS_Z = Z_LO + 0.05
LOS_TOL = 0.30                 # 手前の遮蔽をこの距離だけ許す(自分の前面のため)


def free_mask(sensor: str, X, Y) -> np.ndarray:
    """センサが「ここは空だ」と言い切れる BEV セル。**真の姿勢**で 1 回作る。"""
    C = LIDAR["C"] if sensor == "lidar" else CAM["C"]
    flat = np.stack([X.ravel(), Y.ravel()], 1)
    tgt = np.concatenate([flat, np.full((flat.shape[0], 1), LOS_Z)], 1)
    d = tgt - C
    L = np.linalg.norm(d, axis=1)
    u = d / L[:, None]
    blocked = np.zeros(L.shape, bool)
    for o in OBSTACLES:
        lo, hi = _box_lohi(o)
        tn, tf, hit = ray_box(C, u, lo, hi)
        tb = np.where(tn > 0, tn, tf)
        blocked |= hit & (tb > 1e-6) & (tb < L - LOS_TOL)
    if sensor == "lidar":
        az = np.degrees(np.abs(np.arctan2(d[:, 1], d[:, 0])))
        ok = (~blocked) & (L <= LIDAR["rmax"]) & (az <= LIDAR["az"])
    else:
        ok = (~blocked) & in_camera(tgt)
    return ok.reshape(X.shape)


def in_camera(pts_world: np.ndarray) -> np.ndarray:
    """世界座標の点がカメラの画角と測距範囲に入るか(``project_points`` を使う)。"""
    R_wc = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
    R, t = R_wc.T, -R_wc.T @ CAM["C"]
    W, H, f = CAM["W"], CAM["H"], CAM["f"]
    K = np.array([[f, 0.0, (W - 1) / 2.0], [0.0, f, (H - 1) / 2.0],
                  [0.0, 0.0, 1.0]])
    uv, dep = fs.ledger.project_points.raw(pts_world, K, R, t)
    uv = np.asarray(uv)
    dep = np.asarray(dep)
    return ((dep > 0.3) & (dep <= CAM["zmax"]) & (uv[:, 0] >= 0) & (uv[:, 0] < W)
            & (uv[:, 1] >= 0) & (uv[:, 1] < H))


def resample_free(known: np.ndarray, C, dyaw, dt, X, Y) -> np.ndarray:
    """思い込みの姿勢で置いたときの既知マスク(真の既知マスクを剛体で写す)。"""
    q = np.stack([X.ravel(), Y.ravel(), np.zeros(X.size)], 1) - C - np.asarray(dt)
    p = q @ rz(dyaw) + C                              # R^T q + C
    i = np.floor((p[:, 0] - BOUNDS[0][0]) / CELL).astype(int)
    j = np.floor((p[:, 1] - BOUNDS[1][0]) / CELL).astype(int)
    ok = (i >= 0) & (i < RES) & (j >= 0) & (j < RES)
    out = np.zeros(X.size, bool)
    out[ok] = known[i[ok], j[ok]]
    return out.reshape(X.shape)


# --------------------------------------------------------------------------- #
# 点群 -> BEV(占有 + 高さ)                                                    #
# --------------------------------------------------------------------------- #
def to_bev(pts_world: np.ndarray):
    """世界座標の点群 → ``(占有 (RES,RES) bool, 高さ (RES,RES) float)``。"""
    p = pts_world[(pts_world[:, 2] >= Z_LO) & (pts_world[:, 2] < Z_HI)]
    grid = np.asarray(fs.ledger.occupancy_grid(p, BOUNDS, RES))
    sub = grid[:, :, K0:K1]
    occ = sub.any(axis=2)
    krev = np.argmax(sub[:, :, ::-1], axis=2)
    ktop = K0 + (K1 - K0 - 1) - krev
    return occ, np.where(occ, (ktop + 0.5) * CELL, 0.0)


# --------------------------------------------------------------------------- #
# 融合の規則                                                                    #
# --------------------------------------------------------------------------- #
def weights(C, X, Y, kz=0.0, sigma=0.0, lin=0.0):
    """信頼度 = 1/(1 + (Rσθ/c)² + (測距雑音/c)²)。**校正の宣言値**から作る。"""
    R = np.hypot(X - C[0], Y - C[1])
    sth = np.radians(SIGMA_THETA_DEG)
    noise = sigma + lin * R + kz * R ** 2
    return 1.0 / (1.0 + (R * sth / CELL) ** 2 + (noise / CELL) ** 2), R


def fuse(rule, occ_a, kn_a, h_a, occ_b, kn_b, h_b, w_a, w_b):
    """2 センサの証拠を 1 枚の BEV に。``rule`` = max / mean / weight。"""
    ea, eb = occ_a.astype(float), occ_b.astype(float)
    if rule == "max":
        f = np.maximum(np.where(kn_a, ea, 0.0), np.where(kn_b, eb, 0.0))
        occ = f > 0.5
    elif rule == "mean":
        n = kn_a.astype(float) + kn_b.astype(float)
        s = np.where(kn_a, ea, 0.0) + np.where(kn_b, eb, 0.0)
        occ = np.divide(s, np.maximum(n, 1e-9)) > 0.5
    else:
        wa = np.where(kn_a, w_a, 0.0)
        wb = np.where(kn_b, w_b, 0.0)
        occ = np.divide(wa * ea + wb * eb, np.maximum(wa + wb, 1e-9)) > 0.5
    h = np.maximum(np.where(occ_a & kn_a, h_a, 0.0),
                   np.where(occ_b & kn_b, h_b, 0.0))
    return occ, h


# --------------------------------------------------------------------------- #
# 指標                                                                          #
# --------------------------------------------------------------------------- #
def metrics(occ, hgt, gt_occ, gt_h, evalm, esdf_gt) -> dict:
    o = occ & evalm
    g = gt_occ & evalm
    tp = int((o & g).sum())
    fp = int((o & ~g).sum())
    fn = int((~o & g).sum())
    iou = float(fs.ledger.voxel_iou(o.astype(float), g.astype(float)))
    d = esdf_gt[o & ~g]
    both = o & g
    herr = np.abs(hgt - gt_h)[both]
    return {"iou": iou, "prec": tp / max(tp + fp, 1), "rec": tp / max(tp + fn, 1),
            "tp": tp, "fp": fp, "fn": fn,
            "fp_dist": float(np.median(d)) if d.size else 0.0,
            "fp_far": float(np.mean(d > 2 * CELL)) if d.size else 0.0,
            "h_err": float(np.median(herr)) if herr.size else float("nan")}


# --------------------------------------------------------------------------- #
# 実験の組み立て                                                                #
# --------------------------------------------------------------------------- #
class Rig:
    """場面・観測・真値を 1 度だけ作って持ち回す。"""

    def __init__(self):
        rng = np.random.default_rng(SEED)
        self.gt_occ, self.gt_h, self.X, self.Y = ground_truth()
        self.win = window_mask(self.X, self.Y)
        self.pa = scan_lidar(rng)
        self.depth, pb_raw = scan_camera(rng)
        self.pb_raw_n = int(pb_raw.shape[0])
        self.pb = np.asarray(fs.ledger.voxel_grid_downsample(pb_raw, CELL / 2))
        self.free_a = free_mask("lidar", self.X, self.Y)
        self.free_b0 = free_mask("cam", self.X, self.Y)
        self.esdf = np.asarray(fs.ledger.esdf(self.gt_occ, CELL))
        self.wa, self.Ra = weights(LIDAR["C"], self.X, self.Y,
                                   sigma=LIDAR["sigma"], kz=0.0,
                                   lin=LIDAR["div"])
        self.wb, self.Rb = weights(CAM["C"], self.X, self.Y, kz=CAM["kz"])
        occ, h = to_bev(place(self.pa, LIDAR["C"]))
        self.occ_a, self.h_a = occ, h
        # known = 自由と言い切れる ∪ 実際に返りがあった(= 占有と分かった)
        self.kn_a0 = self.free_a | self.occ_a
        occ_b0, self.kn_b0, _ = self.sensor_b()
        self.occ_b0 = occ_b0
        self.evalm = (self.kn_a0 | self.kn_b0) & self.win

    def sensor_b(self, dyaw=0.0, dt=(0.0, 0.0, 0.0)):
        occ, h = to_bev(place(self.pb, CAM["C"], dyaw, dt))
        free = resample_free(self.free_b0, CAM["C"], dyaw, dt, self.X, self.Y)
        return occ, free | occ, h

    def run(self, rule, dyaw=0.0, dt=(0.0, 0.0, 0.0)):
        ob, kb, hb = self.sensor_b(dyaw, dt)
        occ, h = fuse(rule, self.occ_a, self.kn_a0, self.h_a, ob, kb, hb,
                      self.wa, self.wb)
        return metrics(occ, h, self.gt_occ, self.gt_h, self.evalm, self.esdf), occ

    def cell_shift(self, dyaw=0.0, dt=(0.0, 0.0, 0.0)):
        """カメラの点が **実際に** BEV のセルを跨いだ割合と、その幾何予測。

        予測は 1 - (1-|dx|/c)(1-|dy|/c)(それぞれ 1 で頭打ち)—— セル内の
        位置が一様なら、ずれ ``d`` で index が変わる確率はこれ。
        """
        p0 = place(self.pb, CAM["C"])
        p1 = place(self.pb, CAM["C"], dyaw, dt)
        sel = (p0[:, 2] >= Z_LO) & (p0[:, 2] < Z_HI)
        p0, p1 = p0[sel], p1[sel]
        lo = np.array([BOUNDS[0][0], BOUNDS[1][0]])
        i0 = np.floor((p0[:, :2] - lo) / CELL).astype(int)
        i1 = np.floor((p1[:, :2] - lo) / CELL).astype(int)
        meas = float(np.mean(np.any(i0 != i1, axis=1)))
        d = np.abs(p1[:, :2] - p0[:, :2])
        q = np.minimum(d / CELL, 1.0)
        pred = float(np.mean(1.0 - (1.0 - q[:, 0]) * (1.0 - q[:, 1])))
        return meas, pred

    def single(self, which):
        if which == "lidar":
            occ, h, kn = self.occ_a, self.h_a, self.kn_a0
        else:
            occ, kn, h = self.sensor_b()
        return metrics(occ & kn, h, self.gt_occ, self.gt_h, self.evalm,
                       self.esdf), occ & kn


RULES = ("max", "mean", "weight")
RULE_JA = {"max": "最大値則(どちらかが言えば占有)",
           "mean": "平均則(両方が言わないと占有にしない)",
           "weight": "信頼度重み則(距離と雑音で重みづけ)"}


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                 #
# --------------------------------------------------------------------------- #
def section_scene(rig: Rig) -> None:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— BEV の真値は式で決まる")
    print("=" * 78)
    print("  格子 %d x %d セル(セル %.3f m)、占有を数える帯 z=%.2f-%.2f m。"
          % (RES, RES, CELL, Z_LO, Z_HI))
    print("  評価窓 x %.0f-%.0f m / y %+.0f-%+.0f m にある真値の占有セル %d 個"
          "(面積 %.1f m2)。"
          % (WIN_X[0], WIN_X[1], WIN_Y[0], WIN_Y[1],
             int((rig.gt_occ & rig.win).sum()),
             float((rig.gt_occ & rig.win).sum()) * CELL ** 2))
    print("\n   障害物            中心 [m]        大きさ [m]     高さ [m]  "
          "LiDAR 既知  カメラ既知")
    for o in OBSTACLES:
        inside = ((np.abs(rig.X - o["cx"]) <= o["lx"] / 2)
                  & (np.abs(rig.Y - o["cy"]) <= o["ly"] / 2) & rig.win)
        na = int((inside & rig.kn_a0).sum())
        nb = int((inside & rig.kn_b0).sum())
        print("   %-14s (%5.1f,%5.1f)   %4.1f x %3.1f      %.2f     %5d 個"
              "     %5d 個" % (o["name"], o["cx"], o["cy"], o["lx"], o["ly"],
                                o["h"], na, nb))
    blocker = OBSTACLES[0]
    x0, x1 = blocker["cx"] - blocker["lx"] / 2, blocker["cx"] + blocker["lx"] / 2
    yb = blocker["ly"] / 2
    xq = OBSTACLES[1]["cx"] - OBSTACLES[1]["lx"] / 2
    print("\n  ★陰の縁は幾何で先に出せる。遮蔽物 x=%.2f-%.2f m / |y|<%.2f m の"
          "影を x=%.2f m の断面で予測すると:" % (x0, x1, yb, xq))
    for nm, C in (("LiDAR(左)", LIDAR["C"]), ("カメラ(右)", CAM["C"])):
        edges = []
        for sy in (-yb, yb):
            for sx in (x0, x1):
                edges.append(C[1] + (sy - C[1]) * xq / sx)
        print("     %-12s 影 y = %+.2f 〜 %+.2f m" % (nm, min(edges), max(edges)))
    for o in OBSTACLES[1:3]:
        print("     「%s」は y = %+.2f 〜 %+.2f m —— %s"
              % (o["name"], o["cy"] - o["ly"] / 2, o["cy"] + o["ly"] / 2,
                 "左のセンサ側の影の外" if o["cy"] > 0 else "右のセンサ側の影の外"))
    print("     **横に 1.80 m 離しただけで、22 m 先では影が 2 台ぶん食い違う**"
          " —— これが融合の取り分。")
    print("\n  観測: LiDAR %d 点(σ %.3f m)、カメラ %d 点 → 格子間引き %.2f m 後 %d 点。"
          % (rig.pa.shape[0], LIDAR["sigma"], rig.pb_raw_n, CELL / 2,
             rig.pb.shape[0]))
    print("  評価に使うセル(真の校正でどちらかから見通せた窓内のセル) %d 個 = 窓の %.1f %%。"
          % (int(rig.evalm.sum()), 100.0 * rig.evalm.sum() / rig.win.sum()))


# --------------------------------------------------------------------------- #
# 2. 画像の px と BEV の m                                                       #
# --------------------------------------------------------------------------- #
def section_reprojection(rig: Rig) -> dict:
    print("\n" + "=" * 78)
    print("2) ★★同じ校正誤差を、画像の px と BEV の m で測る")
    print("=" * 78)

    corners = []
    for o in OBSTACLES:
        lo, hi = _box_lohi(o)
        for sx in (lo[0], hi[0]):
            for sy in (lo[1], hi[1]):
                corners.append([sx, sy, hi[2]])
    corners = np.array(corners)
    keep = in_camera(corners)
    corners = corners[keep]

    R_wc = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
    W, H, f = CAM["W"], CAM["H"], CAM["f"]
    K = np.array([[f, 0.0, (W - 1) / 2.0], [0.0, f, (H - 1) / 2.0],
                  [0.0, 0.0, 1.0]])
    diag = float(np.hypot(W, H))
    print("   yaw 誤差    画像の再投影誤差   予測 f·tanθ   画像対角比"
          "    BEV のずれ @ %.1f m   セル数" % OBSTACLES[1]["cx"])
    rows, out = [], {}
    for dy in (0.1, 0.2, 0.5, 1.0, 2.0):
        # ★誤差は **世界の z 軸まわり**(= place と同じ)。``R_wc @ rz`` と
        #   書くと光軸まわりの roll になり、再投影誤差が 1/5 に化ける
        #   (2026-09-07 に踏んだ: 0.98 px と出て、幾何の予測 f·tanθ と合わず発覚)。
        Rt = R_wc.T
        Re = (rz(dy) @ R_wc).T
        uv0 = np.asarray(fs.ledger.project_points(corners, K, Rt,
                                                  -Rt @ CAM["C"]))
        uv1 = np.asarray(fs.ledger.project_points(corners, K, Re,
                                                  -Re @ CAM["C"]))
        px = float(np.mean(np.linalg.norm(uv1 - uv0, axis=1)))
        pred_px = f * np.tan(np.radians(dy))
        shift = OBSTACLES[1]["cx"] * np.tan(np.radians(dy))
        rows.append(["%.2f deg" % dy, "%.2f px" % px, "%.2f px" % pred_px,
                     "%.2f %%" % (100 * px / diag),
                     "%.3f m" % shift, "%.1f" % (shift / CELL)])
        out[dy] = (px, shift)
        print("   %5.2f deg    %8.2f px      %8.2f px    %6.2f %%      %8.3f m"
              "        %5.1f" % (dy, px, pred_px, 100 * px / diag, shift,
                                 shift / CELL))
    px1, sh1 = out[1.0]
    px02, sh02 = out[0.2]
    print("\n  実測は予測 f·tanθ よりわずかに大きい(隅の点ほど tan の効きが"
          "強いため)。")
    print("  ★★換算則: 再投影 1 px = %.3f 度 = 距離 R で **R/f メートル**。"
          "この光学系(f=%.0f px)なら %.1f m 先で **%.3f m/px = %.2f セル/px**。"
          % (np.degrees(1.0 / f), f, OBSTACLES[1]["cx"],
             OBSTACLES[1]["cx"] / f, OBSTACLES[1]["cx"] / f / CELL))
    print("     再投影誤差 %.2f px(yaw %.2f 度)は**サブピクセルに近く校正"
          "レポートなら合格**だが、%.1f m 先の BEV では既に %.3f m ずれている。"
          % (px02, 0.2, OBSTACLES[1]["cx"], sh02))
    print("     yaw %.2f 度(%.2f px)なら %.3f m = %.1f セル。"
          "**px は角度の指標、BEV は長さの指標で、換算係数が距離そのもの** ——"
          "同じ校正が近くでは合格・遠くでは不合格になる。"
          % (1.0, px1, sh1, sh1 / CELL))
    figs.save_table("reprojection", ["yaw 誤差", "画像の再投影誤差",
                                     "予測 f·tanθ", "画像対角比",
                                     "BEV のずれ(%.1f m)" % OBSTACLES[1]["cx"],
                                     "セル数"], rows,
                    title="同じ外部校正誤差を、画像と BEV で測る",
                    caption="画像 %d x %d px、焦点距離 %.0f px。"
                            "画像側は角度に比例し、BEV 側は距離に比例する。"
                            % (W, H, f))
    return out


# --------------------------------------------------------------------------- #
# 3. ゼロ点と融合(誤差 0)                                                     #
# --------------------------------------------------------------------------- #
def section_zero(rig: Rig) -> dict:
    print("\n" + "=" * 78)
    print("3) ゼロ点(単センサ)と融合 —— 誤差 0 で、融合は本当に勝つのか")
    print("=" * 78)
    print("   手法                              IoU     適合率   再現率   "
          "偽占有  見逃し  高さ誤差中央値")

    res = {}
    for nm, key in (("ゼロ点 A: LiDAR 単独", "lidar"), ("ゼロ点 B: カメラ単独", "cam")):
        m, _ = rig.single(key)
        res[key] = m
        print("   %-28s %.4f   %.4f   %.4f   %5d   %5d   %7.3f m"
              % (nm, m["iou"], m["prec"], m["rec"], m["fp"], m["fn"], m["h_err"]))
    for rule in RULES:
        m, _ = rig.run(rule)
        res[rule] = m
        print("   %-28s %.4f   %.4f   %.4f   %5d   %5d   %7.3f m"
              % ("融合 " + RULE_JA[rule].split("(")[0], m["iou"], m["prec"],
                 m["rec"], m["fp"], m["fn"], m["h_err"]))

    best = max(res["lidar"]["iou"], res["cam"]["iou"])
    gain = res["max"]["iou"] - best
    print("\n  ★★融合(最大値則)は単センサの最良 %.4f を %+.4f 上回る。"
          % (best, gain))
    print("     勝ち幅の出どころ(遠方 2 台の占有セルを、どちらが取れたか):")
    for far in OBSTACLES[1:3]:
        inside = ((np.abs(rig.X - far["cx"]) <= far["lx"] / 2)
                  & (np.abs(rig.Y - far["cy"]) <= far["ly"] / 2) & rig.win)
        print("       %-12s 真値 %3d セル / LiDAR が占有と言えた %3d / "
              "カメラ %3d / 融合 %3d"
              % (far["name"], int(inside.sum()),
                 int((inside & rig.occ_a).sum()), int((inside & rig.occ_b0).sum()),
                 int((inside & (rig.occ_a | rig.occ_b0)).sum())))
    print("  ★2 つのゼロ点は IoU では拮抗(%.4f 対 %.4f)なのに**中身は正反対**: "
          "LiDAR は 適合率 %.3f / 再現率 %.3f(正確だが疎)、カメラは %.3f / %.3f"
          "(密だが深度雑音 %.4f z² で滲む)。"
          % (res["lidar"]["iou"], res["cam"]["iou"], res["lidar"]["prec"],
             res["lidar"]["rec"], res["cam"]["prec"], res["cam"]["rec"],
             CAM["kz"]))
    print("     融合が両方を上回るのはこの**相補性**があるから —— "
          "同じ弱点の 2 台を足しても増えない。")
    frac = float(np.mean(rig.wa[rig.evalm] > rig.wb[rig.evalm]))
    both = rig.kn_a0 & rig.kn_b0 & rig.evalm
    print("  ★信頼度重み則の正体: 宣言校正誤差 %.2f 度と雑音モデルから作った重みは"
          "、評価セルの **%.1f %%** で LiDAR のほうが大きい。"
          % (SIGMA_THETA_DEG, 100 * frac))
    print("     つまり両方が見えている %d セル(評価セルの %.0f %%)では"
          "**実質 LiDAR 優先の順位規則**に退化し、"
          "カメラが効くのは片方しか見えていない所だけ。"
          % (int(both.sum()), 100.0 * both.sum() / rig.evalm.sum()))
    print("     ★予想は「距離に応じてなめらかに混ざる」だったが、"
          "**雑音モデルが交差しないので混ざらない**。")
    print("\n  高さを物体ごとに(融合・最大値則、真値と中央値の差):")
    _, occ = rig.run("max")
    _, hf = fuse("max", rig.occ_a, rig.kn_a0, rig.h_a, rig.occ_b0, rig.kn_b0,
                 to_bev(place(rig.pb, CAM["C"]))[1], rig.wa, rig.wb)
    for o in OBSTACLES:
        sel = ((np.abs(rig.X - o["cx"]) <= o["lx"] / 2)
               & (np.abs(rig.Y - o["cy"]) <= o["ly"] / 2) & occ & rig.evalm)
        if not sel.any():
            continue
        print("     %-12s 真値 %.2f m / 実測中央値 %.2f m(差 %+.2f m、%d セル)"
              % (o["name"], o["h"], float(np.median(hf[sel])),
                 float(np.median(hf[sel])) - o["h"], int(sel.sum())))
    print("  ★格子の刻み %.3f m による量子化誤差は最大 %.3f m・期待値 %.3f m。"
          "融合の実測中央値 %.3f m はこの水準 —— **占有より高さのほうが素直**。"
          % (CELL, CELL / 2, CELL / 4, res["max"]["h_err"]))
    print("  ★★ただし**帯の上端 %.2f m より高い物の高さは測れない**。トラック"
          "(真値 %.2f m)は帯で切られるので、この誤差だけは量子化ではなく"
          "**測り方の上限**。" % (Z_HI, OBSTACLES[0]["h"]))
    return res


# --------------------------------------------------------------------------- #
# 4. 回転の崖(予測と突き合わせる)                                             #
# --------------------------------------------------------------------------- #
YAWS = (0.0, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0)


def section_rotation(rig: Rig) -> dict:
    print("\n" + "=" * 78)
    print("4) 崖その 1: 回転(yaw)—— 幾何の予測 R > c/θ と突き合わせる")
    print("=" * 78)
    print("  角度 θ の誤差は距離 R の点を Rθ 動かす。セル c=%.3f m を超えるのは "
          "R > c/θ。" % CELL)
    print("  予測 = セル内の位置が一様なら index が変わる確率 "
          "1-(1-|dx|/c)(1-|dy|/c)。実測 = 実際に index が変わった点の割合。")
    print("\n     yaw     c/θ [m]   予測セル跨ぎ   実測セル跨ぎ   "
          + "   ".join("IoU:%s" % r for r in RULES))

    curves = {r: [] for r in RULES}
    pred_l, meas_l = [], []
    for dy in YAWS:
        th = np.radians(dy)
        rcrit = CELL / th if th > 0 else np.inf
        meas, pred = rig.cell_shift(dyaw=dy)
        pred_l.append(pred)
        meas_l.append(meas)
        row = []
        for r in RULES:
            m, _ = rig.run(r, dyaw=dy)
            curves[r].append(m["iou"])
            row.append(m["iou"])
        print("   %5.2f deg  %8.1f   %10.3f     %10.3f     %s"
              % (dy, rcrit, pred, meas, "   ".join("%.4f" % v for v in row)))

    err = max(abs(p - m) for p, m in zip(pred_l, meas_l))
    print("\n  予測と実測の最大差 %.4f —— 点がセルを跨ぐ量は**量子化まで含めて"
          "幾何で当たる**。" % err)
    i1 = YAWS.index(1.0)
    base = curves["max"][0]
    fall = next((y for y, v in zip(YAWS, curves["max"]) if v < 0.9 * base), None)
    print("  ★★しかし **IoU は c/θ では折れない**。yaw %.2f 度で点の %.0f %% が"
          "既にセルを跨いでいるのに、IoU は %.4f -> %.4f(%.1f %% 減)しか落ちない。"
          % (0.5, 100 * meas_l[YAWS.index(0.5)], base,
             curves["max"][YAWS.index(0.5)],
             100 * (1 - curves["max"][YAWS.index(0.5)] / base)))
    print("     予想は「セル 1 個ずれたら崖」。実測の崖の尺度は**セルではなく"
          "物体の大きさ** —— 幅 %.1f m の車を %.2f m ずらしても重なりは "
          "%.0f %% 残る。IoU が 90 %% を切るのは yaw %.2f 度(BEV のずれ "
          "%.2f m = 物体幅の %.0f %%)。"
          % (OBSTACLES[1]["ly"], CELL, 100 * (1 - CELL / OBSTACLES[1]["ly"]),
             fall, OBSTACLES[1]["cx"] * np.tan(np.radians(fall)),
             100 * OBSTACLES[1]["cx"] * np.tan(np.radians(fall))
             / OBSTACLES[1]["ly"]))
    print("  ★★yaw %.2f 度で 最大値則 %.4f / 平均則 %.4f —— 同じ誤差から"
          "**片方は偽物を作り、片方は本物を消す**(次節で内訳)。"
          % (1.0, curves["max"][i1], curves["mean"][i1]))
    return {"pred": pred_l, "meas": meas_l, "curves": curves}


# --------------------------------------------------------------------------- #
# 5. 崖の内訳(適合率 / 再現率 / 偽占有の距離)                                 #
# --------------------------------------------------------------------------- #
def section_breakdown(rig: Rig) -> dict:
    print("\n" + "=" * 78)
    print("5) ★★壊れ方を 1 つの数字に畳まない —— 規則ごとの内訳")
    print("=" * 78)
    print("   条件            規則       IoU     適合率   再現率   偽占有  見逃し"
          "  偽占有の距離中央値  2 セル超の割合")

    conds = (("誤差なし", dict()),
             ("yaw 1.00 度", dict(dyaw=1.0)),
             ("並進 150 mm(横)", dict(dt=(0.0, 0.150, 0.0))),
             ("時刻ずれ 40 ms", dict(dyaw=EGO_YAWRATE * 0.040,
                                      dt=(EGO_V * 0.040, 0.0, 0.0))))
    rows, out = [], {}
    for cname, kw in conds:
        for r in RULES:
            m, _ = rig.run(r, **kw)
            out[(cname, r)] = m
            rows.append([cname, r, "%.4f" % m["iou"], "%.4f" % m["prec"],
                         "%.4f" % m["rec"], str(m["fp"]), str(m["fn"]),
                         "%.3f m" % m["fp_dist"], "%.3f" % m["fp_far"]])
            print("   %-16s %-8s %.4f   %.4f   %.4f   %5d   %5d   %8.3f m"
                  "        %.3f"
                  % (cname, r, m["iou"], m["prec"], m["rec"], m["fp"], m["fn"],
                     m["fp_dist"], m["fp_far"]))

    mx = out[("yaw 1.00 度", "max")]
    mn = out[("yaw 1.00 度", "mean")]
    print("\n  ★yaw 1 度: 最大値則は適合率 %.3f(偽占有 %d セル)、平均則は"
          "再現率 %.3f(見逃し %d セル)。" % (mx["prec"], mx["fp"], mn["rec"],
                                              mn["fn"]))
    print("     IoU は %.4f と %.4f。**IoU 1 本ではこの違いが出ない** —— "
          "計画に使うなら偽占有(急停止)と見逃し(衝突)は別物。"
          % (mx["iou"], mn["iou"]))
    tr = out[("並進 150 mm(横)", "max")]
    z0 = out[("誤差なし", "max")]
    print("  ★偽占有が真の障害物から 2 セル(%.1f m)より遠くに出る割合: "
          "誤差なし %.3f / yaw 1 度 %.3f / 並進 150 mm %.3f。"
          % (2 * CELL, z0["fp_far"], mx["fp_far"], tr["fp_far"]))
    print("     偽占有の**個数**が近くても、輪郭に貼りつくのか離れて散るのかは"
          "別の量 —— 計画器にとっては後者だけが本当に邪魔をする。")
    figs.save_table("conditions", ["条件", "規則", "IoU", "適合率", "再現率",
                                   "偽占有", "見逃し", "偽占有の距離中央値",
                                   "2 セル超の割合"],
                    rows, title="誤差の種類 x 融合の規則(対照群)",
                    caption="誤差はカメラ側の外部パラメータにだけ入れる。"
                            "LiDAR は常に正しい校正。")
    return out


# --------------------------------------------------------------------------- #
# 6. 崖その 2: 並進、そして時刻ずれ                                             #
# --------------------------------------------------------------------------- #
TRANS = (0.0, 0.02, 0.05, 0.10, 0.15, 0.30, 0.60, 0.90, 1.20)
DTS = (0.0, 0.005, 0.010, 0.020, 0.040, 0.080)


def section_translation(rig: Rig) -> dict:
    print("\n" + "=" * 78)
    print("6) 崖その 2: 並進と時刻ずれ —— 並進は距離に依らない")
    print("=" * 78)
    print("  並進 t は全ての点を同じだけ動かすので、崖は t > c/2 = %.3f m の"
          "1 か所しかない。" % (CELL / 2))
    print("\n     並進 [mm]   セル数    " + "   ".join("IoU:%s" % r for r in RULES))
    curves = {r: [] for r in RULES}
    for t in TRANS:
        row = []
        for r in RULES:
            m, _ = rig.run(r, dt=(0.0, t, 0.0))
            curves[r].append(m["iou"])
            row.append(m["iou"])
        print("      %6.0f    %6.2f    %s"
              % (1000 * t, t / CELL, "   ".join("%.4f" % v for v in row)))

    print("\n  時刻ずれ Δt: 自車 %.1f m/s・ヨー角速度 %.1f 度/s。並進 v·Δt と"
          "回転 ω·Δt が**同時に**入る。" % (EGO_V, EGO_YAWRATE))
    print("\n     Δt [ms]  並進 [mm]  回転 [deg]  20 m での寄与(並進/回転)"
          "   IoU:max   同量の純並進   同量の純回転")
    tcurve, mixed = [], {}
    for dt in DTS:
        tr, yw = EGO_V * dt, EGO_YAWRATE * dt
        c_tr, c_rot = tr, 20.0 * np.radians(yw)
        m, _ = rig.run("max", dyaw=yw, dt=(tr, 0.0, 0.0))
        mt, _ = rig.run("max", dt=(tr, 0.0, 0.0))
        mr, _ = rig.run("max", dyaw=yw)
        tcurve.append(m["iou"])
        mixed[dt] = (m["iou"], mt["iou"], mr["iou"], c_tr, c_rot)
        print("     %6.0f   %8.0f   %8.2f     %.3f m / %.3f m (%4.1f 倍)"
              "     %.4f     %.4f       %.4f"
              % (1000 * dt, 1000 * tr, yw, c_tr, c_rot,
                 c_tr / max(c_rot, 1e-9), m["iou"], mt["iou"], mr["iou"]))

    w = OBSTACLES[1]["ly"]
    base_t = curves["max"][0]
    fall_t = next((t for t, v in zip(TRANS, curves["max"]) if v < 0.9 * base_t),
                  None)
    print("\n  ★実際には c/2 に崖は無い —— 0-150 mm では IoU が上下する"
          "(%.4f -> %.4f -> %.4f)。**半セル以下のずれは、どのセルに丸められるかで"
          "行ったり来たりするだけ**。" % (curves["max"][0], curves["max"][3],
                                          curves["max"][4]))
    print("     はっきり落ちるのは回転と同じく**物体の幅**に近づいてから: "
          "IoU が 90 %% を切るのは %.0f mm(車幅 %.1f m の %.0f %%)。"
          % (1000 * fall_t, w, 100 * fall_t / w))
    a, b, c, ctr, crot = mixed[0.040]
    print("\n  ★Δt=%.0f ms は「並進 %.0f mm + 回転 %.2f 度」。20 m 地点での寄与は"
          " %.1f 倍 並進が大きい。" % (40, 1000 * EGO_V * 0.040,
                                        EGO_YAWRATE * 0.040, ctr / crot))
    print("     実測 IoU %.4f は 純並進 %.4f と差 %.4f、純回転 %.4f とは差 %.4f。"
          "**この速度域では時刻ずれ = 並進**。" % (a, b, abs(a - b), c, abs(a - c)))
    return {"trans": curves, "time": tcurve, "mixed": mixed}


# --------------------------------------------------------------------------- #
# 7. 距離帯別 —— 回転は遠くから、並進は一様に壊れる                             #
# --------------------------------------------------------------------------- #
BANDS = ((4.0, 13.0), (13.0, 19.0), (19.0, 28.0))
#: 距離帯で比べるときは **BEV のずれ量を揃える**(回転 1.00 度は 20 m で
#: 0.349 m なので、並進はその値を使う)。揃えないと「壊れ方の形」でなく
#: 「壊した量」を比べてしまう。
BAND_YAW = 1.0
BAND_SHIFT = 20.0 * np.tan(np.radians(BAND_YAW))


def _band_iou(occ, gt, evalm, X):
    vals, ns = [], []
    for b in BANDS:
        sel = evalm & (X >= b[0]) & (X < b[1])
        o, g = occ & sel, gt & sel
        ns.append(int(g.sum()))
        vals.append(float(fs.ledger.voxel_iou(o.astype(float), g.astype(float))))
    return vals, ns


def section_bands(rig: Rig) -> dict:
    print("\n" + "=" * 78)
    print("7) ★★距離帯で割る —— 同じ IoU 低下でも「どこが壊れたか」は正反対")
    print("=" * 78)
    print("  比べるのは **BEV のずれ量を揃えた 2 条件**: yaw %.2f 度(20 m で"
          " %.3f m)と 並進 %.0f mm。" % (BAND_YAW, BAND_SHIFT,
                                          1000 * BAND_SHIFT))

    conds = (("誤差なし", dict()), ("回転 %.2f 度" % BAND_YAW, dict(dyaw=BAND_YAW)),
             ("並進 %.0f mm" % (1000 * BAND_SHIFT),
              dict(dt=(0.0, BAND_SHIFT, 0.0))))

    # (a) まず「点が実際にどれだけ動いたか」を帯ごとに測る(IoU より直接的)
    print("\n   カメラの点の平均移動量 [m]    "
          + "  ".join("%5.0f-%2.0f m" % b for b in BANDS) + "   遠 / 近の比")
    p0 = place(rig.pb, CAM["C"])
    insl = (p0[:, 2] >= Z_LO) & (p0[:, 2] < Z_HI)
    shift_ratio = {}
    for cname, kw in conds[1:]:
        p1 = place(rig.pb, CAM["C"], **kw)
        d = np.linalg.norm((p1 - p0)[:, :2], axis=1)
        vals = []
        for b in BANDS:
            sel = insl & (p0[:, 0] >= b[0]) & (p0[:, 0] < b[1])
            vals.append(float(d[sel].mean()) if sel.any() else 0.0)
        shift_ratio[cname] = vals[-1] / max(vals[0], 1e-9)
        print("   %-26s" % cname + "  ".join("%9.3f" % v for v in vals)
              + "   %8.2f" % shift_ratio[cname])
    print("   ★回転は帯ごとに %.2f 倍(距離に比例)、並進は %.2f 倍(定数)—— "
          "**原因はここで既に分かれている**。"
          % (shift_ratio[conds[1][0]], shift_ratio[conds[2][0]]))

    out, rows = {}, []
    hdr = "   誤差を持つセンサ(カメラ)単独  " + " ".join(
        "%5.0f-%2.0f m" % b for b in BANDS) + "   遠 / 近の比"
    print("\n" + hdr)
    for cname, kw in conds:
        ob, kb, _ = rig.sensor_b(**kw)
        vals, ns = _band_iou(ob & kb, rig.gt_occ, rig.evalm, rig.X)
        out[("cam", cname)] = vals
        ratio = vals[-1] / max(vals[0], 1e-9)
        rows.append(["カメラ単独", cname] + ["%.4f" % v for v in vals]
                    + ["%.2f" % ratio])
        print("   %-28s" % cname + " ".join("%9.4f" % v for v in vals)
              + "   %8.2f" % ratio)
    print("   (帯ごとの真値セル数: %s)"
          % " / ".join("%d" % n for n in ns))

    print("\n   融合(最大値則)で同じことを見ると:")
    for cname, kw in conds:
        _, occ = rig.run("max", **kw)
        vals, _ = _band_iou(occ, rig.gt_occ, rig.evalm, rig.X)
        out[("max", cname)] = vals
        ratio = vals[-1] / max(vals[0], 1e-9)
        rows.append(["融合(最大値)", cname] + ["%.4f" % v for v in vals]
                    + ["%.2f" % ratio])
        print("   %-28s" % cname + " ".join("%9.4f" % v for v in vals)
              + "   %8.2f" % ratio)

    rot, tra = out[("cam", conds[1][0])], out[("cam", conds[2][0])]
    base = out[("cam", "誤差なし")]
    dr = [1 - r / max(b, 1e-9) for r, b in zip(rot, base)]
    dt_ = [1 - t / max(b, 1e-9) for t, b in zip(tra, base)]
    print("\n  誤差なしからの低下率(カメラ単独): 回転 %s / 並進 %s"
          % (" ".join("%.0f%%" % (100 * v) for v in dr),
             " ".join("%.0f%%" % (100 * v) for v in dt_)))
    print("  ★回転は近 %.0f %% -> 遠 %.0f %% と**遠方ほど大きく落ちる**。"
          "並進は %.0f %% -> %.0f %% で、落ち方の差は回転の %.2f 倍しかない ——"
          " 近くも遠くも同じだけ壊す。"
          % (100 * dr[0], 100 * dr[-1], 100 * dt_[0], 100 * dt_[-1],
             abs(dt_[-1] - dt_[0]) / max(abs(dr[-1] - dr[0]), 1e-9)))
    print("  ★★融合すると LiDAR が遠方を埋めるので、この距離依存性は"
          "**薄まる**(遠 / 近の比 %.2f -> %.2f)。融合は誤差を消さずに**隠す**"
          " —— 校正の異常を IoU の距離依存で見つける診断は、融合の後では効かない。"
          % (rot[-1] / max(rot[0], 1e-9),
             out[("max", conds[1][0])][-1]
             / max(out[("max", conds[1][0])][0], 1e-9)))
    figs.save_table("range_bands", ["手法", "条件"]
                    + ["%.0f-%.0f m" % b for b in BANDS] + ["遠 / 近の比"],
                    rows, title="距離帯別の占有 IoU(ずれ量を揃えた 2 条件)",
                    caption="回転誤差は距離に比例して効き、並進誤差は距離に"
                            "依らない。融合するとその差が隠れる。")
    return out


# --------------------------------------------------------------------------- #
# 8. 整形(closing)—— unknown を埋めると偽占有も太る                           #
# --------------------------------------------------------------------------- #
def shape_up(occ: np.ndarray) -> np.ndarray:
    """表面の返りを footprint に近づける定番の整形。2-D の公開 op を使う。"""
    a = np.asarray(fs.apply(occ.astype(np.float64), "closing_circle", a=1.0))
    return np.asarray(fs.apply(a, "fill_up")) > 0.5


def section_shaping(rig: Rig) -> dict:
    print("\n" + "=" * 78)
    print("8) 整形(closing + 穴埋め)—— footprint には近づくが、偽占有も太る")
    print("=" * 78)
    print("  表面の返りだけでは車の内部は unknown のまま。整形すると solid な"
          "footprint に近づく。")
    print("\n   条件            整形    占有セル   solid IoU   偽占有(窓内)")

    solid = rig.gt_occ & rig.win
    out = {}
    for cname, kw in (("誤差なし", dict()), ("yaw 1.00 度", dict(dyaw=1.0))):
        _, occ = rig.run("max", **kw)
        for tag, o in (("なし", occ & rig.win), ("あり", shape_up(occ) & rig.win)):
            iou = float(fs.ledger.voxel_iou(o.astype(float), solid.astype(float)))
            fp = int((o & ~solid).sum())
            out[(cname, tag)] = (int(o.sum()), iou, fp)
            print("   %-16s %-6s %7d    %.4f      %6d"
                  % (cname, tag, int(o.sum()), iou, fp))

    a0, a1 = out[("誤差なし", "なし")], out[("誤差なし", "あり")]
    b0, b1 = out[("yaw 1.00 度", "なし")], out[("yaw 1.00 度", "あり")]
    print("\n  ★誤差 0 では占有セルが %.2f 倍になり solid IoU は %.4f -> %.4f。"
          % (a1[0] / a0[0], a0[1], a1[1]))
    print("  ★同じ整形を yaw %.2f 度に掛けると偽占有は %d -> %d セル(%.2f 倍)。"
          "整形は**判断を増幅する装置**で、誤差を直しはしない。"
          % (1.0, b0[2], b1[2], b1[2] / max(b0[2], 1)))
    return out


# --------------------------------------------------------------------------- #
# 9. 図                                                                         #
# --------------------------------------------------------------------------- #
def far_cells(rig, idx: int) -> np.ndarray:
    """``OBSTACLES[idx]`` の footprint(所見を固定する assert 用)。"""
    o = OBSTACLES[idx]
    return ((np.abs(rig.X - o["cx"]) <= o["lx"] / 2)
            & (np.abs(rig.Y - o["cy"]) <= o["ly"] / 2))


#: 図に出す範囲(評価窓の少し外まで)。全 32 x 32 m を出すと空が大半になる。
CROP_X, CROP_Y = (2.0, 30.0), (-10.0, 10.0)


def bev_img(a) -> np.ndarray:
    """BEV 配列 (x,y) → 画像(上が前方、左が車の左)。表示範囲に切る。"""
    i0 = int((CROP_X[0] - BOUNDS[0][0]) / CELL)
    i1 = int((CROP_X[1] - BOUNDS[0][0]) / CELL)
    j0 = int((CROP_Y[0] - BOUNDS[1][0]) / CELL)
    j1 = int((CROP_Y[1] - BOUNDS[1][0]) / CELL)
    v = np.asarray(a, float)[i0:i1, j0:j1][::-1, ::-1]
    # パネルが小さすぎると題が入らない(annotate は切り詰めずに例外にする)ので
    # 最近傍で 2 倍に伸ばす。BEV は格子そのものなので補間はしない。
    return np.repeat(np.repeat(v, 2, axis=0), 2, axis=1)


def _tri_color(occ, gt, evalm) -> np.ndarray:
    """当たり / 偽占有 / 見逃しを 3 色に(赤緑は使わない)。"""
    rgb = np.full(occ.shape + (3,), 0.10)
    rgb[evalm] = 0.22
    tp, fp, fn = occ & gt & evalm, occ & ~gt & evalm, ~occ & gt & evalm
    rgb[tp] = (0.95, 0.95, 0.95)
    rgb[fp] = (0.95, 0.60, 0.10)      # 偽占有 = 橙
    rgb[fn] = (0.20, 0.50, 0.95)      # 見逃し = 青
    return rgb


def section_scene_figures(rig: Rig) -> None:
    """場面の図(記事の看板になるので **最初に**書く)。"""
    if not figs.enabled():
        return
    # (a) 場面: 真値占有 / 真値高さ / 既知マスク / LiDAR の生 BEV
    cov = np.zeros(rig.X.shape)
    cov[rig.kn_a0] = 0.5
    cov[rig.kn_b0] += 0.5
    figs.save_grid("scene_bev",
                   [bev_img(rig.gt_occ), bev_img(rig.gt_h), bev_img(cov),
                    bev_img(rig.occ_a & rig.kn_a0)],
                   ["真値の占有", "真値の高さ [m]", "既知セル(片方 / 両方)",
                    "LiDAR 単独の BEV"],
                   ncols=2, title="鳥瞰図の真値と観測(1 セル %.2f m、上が前方)"
                                  % CELL,
                   caption="評価窓は前方 %.0f-%.0f m。既知でない領域"
                           "(車体内部・陰)は評価から外す。" % WIN_X)

    # (b) 陰の食い違い —— 融合の取り分がどこから来るか
    shadow = np.zeros(rig.X.shape + (3,))
    shadow[..., 2] = np.where(rig.free_a, 0.62, 0.10)      # LiDAR が見た自由
    shadow[..., 0] = np.where(rig.free_b0, 0.62, 0.10)     # カメラが見た自由
    shadow[..., 1] = np.where(rig.free_a & rig.free_b0, 0.45, 0.10)
    shadow[rig.gt_occ] = (1.0, 1.0, 1.0)
    figs.save("shadow_map", bev_img(shadow),
              "横に %.2f m 離した 2 センサの「自由と言い切れた領域」。"
              "青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、"
              "灰色は両方。白は真値の障害物。22 m の 2 台は"
              "**互いの影に 1 台ずつ入っている**。"
              % float(LIDAR["C"][1] - CAM["C"][1]))


def section_figures(rig: Rig, zero: dict) -> None:
    if not figs.enabled():
        return
    # (c) 各センサと融合(誤差 0)
    _, o_max = rig.run("max")
    _, o_lid = rig.single("lidar")
    _, o_cam = rig.single("cam")
    figs.save_grid("fusion_map",
                   [bev_img(o_lid), bev_img(o_cam), bev_img(o_max),
                    bev_img(rig.gt_occ & rig.evalm)],
                   ["LiDAR 単独 IoU %.3f" % zero["lidar"]["iou"],
                    "カメラ単独 IoU %.3f" % zero["cam"]["iou"],
                    "融合(最大値則) IoU %.3f" % zero["max"]["iou"],
                    "真値(評価セルのみ)"],
                   ncols=2, title="誤差 0 の BEV —— 融合が買っているのは視界",
                   caption="LiDAR は 22 m の車を 1 セルも返せない(先行車の陰)。"
                           "カメラは屋根越しに見えるので融合で復活する。")

    # (d) 誤差地図(yaw 1 度、規則ごと)
    panels, caps = [], []
    for r in RULES:
        m, occ = rig.run(r, dyaw=1.0)
        panels.append(_tri_color(occ, rig.gt_occ, rig.evalm))
        caps.append("%s IoU %.3f 偽%d 見逃%d"
                    % (r, m["iou"], m["fp"], m["fn"]))
    m, occ = rig.run("max", dt=(0.0, 0.150, 0.0))
    panels.append(_tri_color(occ, rig.gt_occ, rig.evalm))
    caps.append("max / 並進 150 mm IoU %.3f" % m["iou"])
    figs.save_grid("error_map", [bev_img(p) for p in panels], caps, ncols=2,
                   title="誤差地図(白=当たり、橙=偽占有、青=見逃し)",
                   caption="同じ yaw 1.00 度でも、最大値則は橙(偽占有)、"
                           "平均則は青(見逃し)に偏る。壊れ方の種類が違う。")


def section_curves(rot: dict, tr: dict, zero: dict) -> None:
    if not figs.enabled():
        return
    series = [("LiDAR 単独", list(YAWS), [zero["lidar"]["iou"]] * len(YAWS)),
              ("カメラ単独", list(YAWS), [zero["cam"]["iou"]] * len(YAWS))]
    for r in RULES:
        series.append((RULE_JA[r].split("(")[0], list(YAWS), rot["curves"][r]))
    figs.save_plot("cliff_rotation", series, xlabel="カメラ側 yaw 誤差 [deg]",
                   ylabel="占有 IoU",
                   title="回転誤差と占有 IoU(崖はセルでなく物体の大きさで決まる)",
                   caption="水平の 2 本は単センサのゼロ点。点の 6 割以上が"
                           "セルを跨ぐ yaw 0.5 度でも IoU はまだ落ちず、"
                           "ずれが車幅に近づく数度で単センサに追い抜かれる。")
    ser2 = [("LiDAR 単独", [1000 * t for t in TRANS],
             [zero["lidar"]["iou"]] * len(TRANS))]
    for r in RULES:
        ser2.append((RULE_JA[r].split("(")[0], [1000 * t for t in TRANS],
                     tr["trans"][r]))
    figs.save_plot("cliff_translation", ser2, xlabel="カメラ側 並進誤差 [mm]",
                   ylabel="占有 IoU",
                   title="並進の崖(c/2 = %.0f mm の 1 か所だけ)" % (500 * CELL),
                   caption="並進は距離に依らず全セルを同じだけ動かすので、"
                           "崖は半セルを超えたところに 1 回だけ来る。")


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    assert hasattr(fs.ledger, "occupancy_grid") and hasattr(fs.ledger, "grid_coords")
    n_used = RES * RES * (K1 - K0)
    print("  (a) ``occupancy_grid`` は **立方 res³ しか取らない**(``grid_coords`` は"
          "軸ごとの res を受けるのに)。BEV は x,y に %.2f m、z は %.1f m ぶんしか"
          "要らないのに %d 個のボクセルを確保して、実際に使うのは %d 個"
          "(%.1f %%)。" % (CELL, Z_HI - Z_LO, RES ** 3, n_used,
                            100.0 * n_used / RES ** 3))

    assert not hasattr(fs.ledger, "bev_project") and not hasattr(fs, "bev_project")
    assert not hasattr(fs.ledger, "log_odds_update")
    print("  (b) 占有格子の **log-odds 更新**(Elfes の定式化)が無い。"
          "本 PoC の 3 規則(最大値 / 平均 / 信頼度重み)はどれも自前 10 行で、"
          "センサモデルつきの逐次更新は書けない。占有格子は 3 状態"
          "(占有 / 自由 / 未知)なのに、``occupancy_grid`` は bool の 2 状態しか"
          "返さないので**未知が表現できない**(この PoC は known マスクを"
          "自前で持ち回している)。")

    assert not hasattr(fs.ledger, "ray_box_intersect")
    print("  (c) **光線 - AABB 交差**(slab 法)が公開経路に無い。"
          "``shadow_raycast`` / ``visual_hull`` / ``carve`` はボクセル前提で、"
          "解析的な直方体に対する交差が要る場面(合成データ作成・見通し判定)は"
          "自前になる。本 PoC の :func:`ray_box` / :func:`cast` がそれ。")

    assert hasattr(fs.ledger, "voxel_iou")
    print("  (d) ``voxel_iou`` は 2-D 配列でもそのまま動く(shape 一致だけ見る)が、"
          "**マスクつきの IoU**(評価から外すセルを指定する)口が無い。"
          "未知セルを分母に入れるか外すかで数字が変わるので、"
          "評価器を族に入れるなら**分母を引数で強制する**設計にすべき。")

    print("  (e) 外部校正の誤差を**姿勢に注入する**口(rig の作法)が無い。"
          "``pose_error`` / ``rotation_translation_error`` は 2 姿勢の差を測るが、"
          "「既知の誤差を入れて下流を壊す」向きの道具は無い。感度解析はこの向きが要る。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("鳥瞰図への多センサ融合 —— 外部キャリブ誤差が融合をどこで壊すか")
    print("BEV %d x %d セル(%.2f m)/ LiDAR 高 %.2f m / カメラ高 %.2f m"
          % (RES, RES, CELL, LIDAR["C"][2], CAM["C"][2]))
    print("=" * 78)

    rig = Rig()
    section_scene(rig)
    section_scene_figures(rig)
    rep = section_reprojection(rig)
    zero = section_zero(rig)
    rot = section_rotation(rig)
    brk = section_breakdown(rig)
    tr = section_translation(rig)
    bands = section_bands(rig)
    shp = section_shaping(rig)
    section_figures(rig, zero)
    section_curves(rot, tr, zero)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    px1, sh1 = rep[1.0]
    print("  * 再投影 1 px は %.1f m 先の BEV で %.3f m(%.2f セル)。"
          "yaw 1 度 = %.2f px = %.3f m = %.1f セル —— "
          "**px と m は距離で換算される別の指標**。"
          % (OBSTACLES[1]["cx"], OBSTACLES[1]["cx"] / CAM["f"],
             OBSTACLES[1]["cx"] / CAM["f"] / CELL, px1, sh1, sh1 / CELL))
    print("  * 誤差 0: LiDAR 単独 %.4f / カメラ単独 %.4f / 融合 %.4f。"
          "勝ち幅 %+.4f はすべて**視界(先行車の陰)**から来ている。"
          % (zero["lidar"]["iou"], zero["cam"]["iou"], zero["max"]["iou"],
             zero["max"]["iou"] - max(zero["lidar"]["iou"], zero["cam"]["iou"])))
    best = max(zero["lidar"]["iou"], zero["cam"]["iou"])
    cross = next((y for y, v in zip(YAWS, rot["curves"]["max"]) if v < best),
                 None)
    print("  * 点がセルを跨ぐ量は R > c/θ で予測できる(予測と実測の最大差 %.4f)"
          "が、**IoU はそこでは折れない** —— 効く尺度は物体の大きさ。"
          "融合(最大値則)が単センサの最良 %.4f を割るのは yaw %.1f 度。"
          % (max(abs(p - m) for p, m in zip(rot["pred"], rot["meas"])),
             best, cross))
    kr, kt = "回転 %.2f 度" % BAND_YAW, "並進 %.0f mm" % (1000 * BAND_SHIFT)
    b0 = bands[("cam", "誤差なし")]
    drop = {k: [1 - v / max(u, 1e-9) for v, u in zip(bands[("cam", k)], b0)]
            for k in (kr, kt)}
    print("  * 同じずれ量で距離帯を割ると、カメラ単独の低下率は 回転 %.0f→%.0f %%"
          "(遠方ほど大きい)、並進 %.0f→%.0f %%(帯によらない)。"
          "融合すると遠 / 近の比は %.2f → %.2f に薄まる。"
          % (100 * drop[kr][0], 100 * drop[kr][-1],
             100 * drop[kt][0], 100 * drop[kt][-1],
             bands[("cam", kr)][-1] / max(bands[("cam", kr)][0], 1e-9),
             bands[("max", kr)][-1] / max(bands[("max", kr)][0], 1e-9)))
    print("  * 時刻ずれ 40 ms(%.1f m/s)は純並進 %.0f mm とほぼ同じ"
          "(IoU 差 %.4f)。"
          % (EGO_V, 1000 * EGO_V * 0.040,
             abs(tr["mixed"][0.040][0] - tr["mixed"][0.040][1])))
    print("  * 整形は footprint に近づける(solid IoU %.4f -> %.4f)が、"
          "yaw 1 度では偽占有を %.2f 倍にする。"
          % (shp[("誤差なし", "なし")][1], shp[("誤差なし", "あり")][1],
             shp[("yaw 1.00 度", "あり")][2]
             / max(shp[("yaw 1.00 度", "なし")][2], 1)))

    # --- 所見を固定する assert(壊れたら鳴る)------------------------------- #
    assert zero["max"]["iou"] > best + 0.10, "融合の視界の利得"
    assert rig.occ_a[far_cells(rig, 2)].sum() == 0, "右の遠方車は LiDAR に見えない"
    assert rig.occ_b0[far_cells(rig, 1)].sum() == 0, "左の遠方車はカメラに見えない"
    assert max(abs(p - m) for p, m in zip(rot["pred"], rot["meas"])) < 0.08
    assert rot["meas"][YAWS.index(0.5)] > 0.5 \
        and rot["curves"]["max"][YAWS.index(0.5)] > 0.85 * rot["curves"]["max"][0], \
        "半分の点がセルを跨いでも IoU は折れない"
    assert cross is not None and cross >= 2.0, "融合が単独に負ける yaw"
    assert brk[("yaw 1.00 度", "max")]["prec"] < brk[("yaw 1.00 度", "mean")]["prec"]
    assert brk[("yaw 1.00 度", "mean")]["rec"] < brk[("yaw 1.00 度", "max")]["rec"]
    assert drop[kr][-1] > drop[kr][0], "回転は遠方ほど落ちる"
    assert abs(drop[kt][-1] - drop[kt][0]) < abs(drop[kr][-1] - drop[kr][0]), \
        "並進のほうが一様"
    assert abs(tr["mixed"][0.040][0] - tr["mixed"][0.040][1]) < 0.05

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
