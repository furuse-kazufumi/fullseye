# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""設計モデルと実際の建物のずれを点群から測る —— 部屋は合わせの自由度を吸い、余りを他の部材へ配る。

建物は設計どおりには建ちません。壁が傾き、床が反り、柱が寸法どおりでなく、開口が
ずれる。BIM(設計モデル)と実測点群を突き合わせて「どこがどれだけ違うか」を出すのが
Scan-to-BIM の as-built 検査です。ここでは施工誤差も測定の癖も**すべて既知の量**で
仕込み、要素ごとの判定がどこで嘘になるかを測ります。

EXTEND: 実スキャンに差し替えるなら :func:`make_surface` が返す辞書の ``P``(点)と
``elem``(どの部材の点か)を、実機の点群と BIM 案内のラベルに置き換えます。
``dev_true``(真の偏差)は実物では手に入らないので、**基準器**(トータルステーション
の基準点・下げ振り・レーザーレベルの水糸)を別に測って部分的な真値にします。
測れなくなるのは (1) 部材ごとの真の傾き —— 面の裏側が見えないので「壁が傾いた」のか
「壁が厚い」のか区別できない、(2) 混合画素の正解ラベル、(3) 各スキャン位置の
レジストレーション誤差の真値(球ターゲットの残差は下限であって真値ではない)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(点群全体を BIM に一括 ICP して平均距離を出す)は、施工誤差の有無を
   ほとんど区別しない**。誤差ゼロの建物 2.02 mm、施工誤差入り 2.63 mm ——
   差は 0.61 mm しかない。同じ点群を要素ごとに見ると柱の半径 +6.53 mm、
   床の反り 11.5 mm と、桁の違う不良が出ている。**建物 1 個の数字は、
   場所ごとに符号の違う偏差を平均して打ち消してしまう**。
2. ★★**一括で合わせると、部屋という箱が剛体モードを吸い、その分を他の部材へ
   配る**。真値は「壁の傾き 3.00 mrad(東西の壁がそろって東へ)+ 床の勾配
   1.50 mrad(東へ下がる)+ 天井は完全に水平」。全体 ICP のあと壁は 1.99 mrad
   (真値の 66 %)、床は 0.48 mrad(32 %)、そして★**無傷の天井が 1.03 mrad
   傾いて見える**。これは幾何で先に予測できる: 各部材の y 軸まわりのてこ
   Σ(腕の長さ)² で重みづけした平均角 —— 予測 1.02 mrad / ICP の実測 1.00 mrad。
   **一番大きな偽の施工誤差は、いちばん正しく建った部材に出る**。
3. ★**吸われるのは剛体モードだけ**。同じ点群で、南北の壁の「開き」(上で外へ、
   互いに逆向き = 剛体でない)は真値 2.50 mrad に対し合わせても 2.50 mrad の
   まま。床の反り(対称な 2 次曲面)も 11.5 mm で生き残る。合わせ方を変えると
   傾きだけが動く(合わせない 3.02 / 床と 2 壁を基準 2.20 / 全体 ICP 1.99 mrad)。
4. ★**崖は「欠測率」では決まらない**。予想は「点が減れば σ/√N で悪くなる」
   だったが、**同じ欠測率でも壊れ方が 2 桁違う**。無作為に 90 % 落としても
   壁の傾きの散らばりは 0.05 mrad(検出できる)。ところが**下から順に残す**
   構造的な欠測(床置きスキャナと擦過角で実際に起きる形)で同じ 90 % を
   落とすと 0.55 mrad まで荒れる。効くのは残った点の数ではなく**残った面の
   高さ L** で、σ√12/(L√N) の予測(0.51 mrad)と 8 % で一致した。
5. ★★**レジストレーション誤差は点を増やしても消えない**。無作為欠測は
   √N で薄まるのに、スキャン位置ごとの姿勢誤差は系統誤差なので N に無関係。
   1.0 mrad の回転誤差で偽の傾きが 0.74 mrad 出て、3 mrad の施工誤差に対する
   信号対雑音が 4.1 まで落ちる。**検出限界は雑音でなくレジストレーションで
   決まる**(点群の密度をいくら上げても改善しない)。
6. ★**混合画素は平面には効かず、円柱の半径にだけ効く**。開口の縁で 30 % の
   点を混合にしても壁の傾きは 0.02 mrad しか動かない(RANSAC が外れ値として
   落とす)。同じ割合で柱の半径は -0.93 mm 動く —— 柱は**輪郭がぐるりと全周
   縁**なので混合画素が均等に内側へ寄り、外れ値でなく系統的な縮みになる。
7. **CSG の交差は角で厳密でない**。6 枚の半空間(``plane_sdf``)を ``sdf_intersect``
   で重ねた部屋と、``box_sdf`` の厳密な箱を比べると、部屋の**内側**では最大
   0.000 mm 差(どちらも最近面までの距離)、**外側の角**では最大 1201.6 mm
   の過小評価。距離そのものを測るなら箱の op を使う —— op の docstring が
   警告しているとおりだった。

【グラウンドトゥルース】部屋は半空間(``plane_sdf``)・直方体(``box_sdf``)・
円柱(``cylinder_sdf``)の CSG。施工誤差は (a) 東西の壁の傾き 3.00 mrad
(b) 南北の壁の開き 2.50 mrad (c) 床の勾配 1.50 mrad と反り 12.0 mm
(d) 柱の半径 +6.5 / -4.0 mm (e) 壁の面外の膨らみ 8.0 mm (f) 開口の位置ずれ
25.0 / 18.0 mm。測定は 3 か所からの走査で、視線に依存する欠測(柱の影・
擦過角)・入射角依存の雑音 σ=1.2 mm/(1 m, 垂直入射)・混合画素・
レジストレーション誤差 0.80 mrad + 2.0 mm。すべて既知。

来歴(公開文献のみ): ISO 17123-9 / JIS A 3301 系の施工精度の考え方 /
Bosché, *Automated recognition of 3D CAD model objects in laser scans*,
Adv. Eng. Informatics 24 (2010) 107 / Tang et al., *Automatic reconstruction of
as-built BIM*, Automation in Construction 19 (2010) 829 / Soudarissanane et al.,
*Scanning geometry: influencing factor on the quality of terrestrial laser
scanning points*, ISPRS J. 66 (2011) 389 —— 入射角と雑音の関係。
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

# --- 部屋の設計(BIM)------------------------------------------------------- #
RX, RY, RZ = 6.0, 4.0, 3.0        # 内法 [m]
COL_R = 0.200                     # 柱の設計半径 [m]
COL_XY = ((1.60, 1.20), (4.40, 2.80))
WIN_U = (1.20, 3.00)              # 窓の開口(壁 x=RX 上の y 範囲)[m]
WIN_V = (0.90, 2.10)              # 同 z 範囲 [m]
WIN_D = 0.10                      # 窓の見込み(奥行き)[m]
DOOR_U = (2.40, 3.40)             # 戸の開口(壁 y=0 上の x 範囲)[m]
DOOR_V = (0.00, 2.10)
DOOR_D = 0.12
BASE_T, BASE_H = 0.015, 0.10      # 幅木の出と高さ [m]

# --- 施工誤差の真値(scale=0 で「設計どおりに建った建物」)------------------ #
RACK = 3.0e-3        # 東西の壁がそろって東へ傾く [rad](= 剛体モード)
SPLAY = 2.5e-3       # 南北の壁が上で開く [rad](= 剛体でないモード)
FLOOR_SLOPE = -1.5e-3  # 床が東へ下がる [rad](符号は z = SLOPE*(x-3))
SAG = 0.012          # 床の反り(中央が下がる)[m]
BULGE = 0.008        # 東の壁の面外の膨らみ [m]
BULGE_S = 0.90       # 膨らみの広がり [m]
DCOL = (0.0065, -0.0040)   # 柱の半径の狂い [m]
WIN_DZ = 0.025       # 窓が上へずれる [m]
DOOR_DX = 0.018      # 戸が東へずれる [m]

# --- 測定の癖 --------------------------------------------------------------- #
STATIONS = ((1.10, 0.80, 1.55), (5.00, 3.20, 1.55), (1.20, 3.20, 1.55))
SIG0 = 0.0012        # 1 m・垂直入射での測距の 1σ [m]
K_R = 0.15           # 距離への依存 [1/m]
COS_MIN = 0.12       # これより浅い入射角は返らない(擦過角の欠測)
MIX_FRAC = 0.12      # 段差の縁で混合画素になる割合
EDGE_BAND = 0.030    # 縁とみなす帯 [m]
REG_MRAD = 0.40      # スキャン位置ごとの姿勢誤差 [mrad]
REG_MM = 1.5         # 同 並進 [mm]

STEP = 0.055         # 本編の面のサンプル間隔 [m]
STEP_LIGHT = 0.110   # 掃引用(壁と床天井だけの軽い場面)
SEED = 7

# 部材の番号
FLOOR, CEIL, WX0, WX1, WY0, WY1, COL0, COL1, WINR, DOORR, BASE = range(11)
ELEM_JA = ("床", "天井", "西の壁", "東の壁", "南の壁", "北の壁",
           "柱 A", "柱 B", "窓の見込み", "戸の見込み", "幅木")
PLANARS = (FLOOR, CEIL, WX0, WX1, WY0, WY1)


# --------------------------------------------------------------------------- #
# 1. 部屋の面をつくる —— 真値は「設計面からの符号つき偏差」                     #
# --------------------------------------------------------------------------- #
def _grid(a0, a1, b0, b1, step):
    a = np.arange(a0 + step / 2, a1, step)
    b = np.arange(b0 + step / 2, b1, step)
    A, B = np.meshgrid(a, b, indexing="ij")
    return A.ravel(), B.ravel()


def _outside_rect(u, v, rect):
    """矩形 ``rect=(u0,u1,v0,v1)`` の外にあるか。"""
    u0, u1, v0, v1 = rect
    return ~((u >= u0) & (u <= u1) & (v >= v0) & (v <= v1))


def _rim(u, v, rect, band):
    """矩形の**外側**で縁から ``band`` 以内(= 段差の縁)。"""
    u0, u1, v0, v1 = rect
    du = np.maximum(np.maximum(u0 - u, u - u1), 0.0)
    dv = np.maximum(np.maximum(v0 - v, v - v1), 0.0)
    d = np.hypot(du, dv)
    return (d > 0) & (d <= band)


def _rim_inside(u, v, rect, band):
    """矩形の**内側**で縁から ``band`` 以内。"""
    u0, u1, v0, v1 = rect
    d = np.minimum(np.minimum(u - u0, u1 - u), np.minimum(v - v0, v1 - v))
    return (d >= 0) & (d <= band)


def make_surface(scale: float = 1.0, step: float = STEP, light: bool = False) -> dict:
    """as-built の面を一様サンプルし、点・法線・部材番号・真の偏差・段差を返す。

    ``scale`` は施工誤差の倍率(0 = 設計どおりに建った建物 = 偽の誤差の対照群)。
    ``light=True`` は掃引用に床・天井・壁 4 枚だけを作る(柱・開口・幅木なし)。
    法線は**部屋の内側(スキャナ側)を向く**。偏差は同じ向きを正とする。
    """
    s = float(scale)
    P, N, E, D, G = [], [], [], [], []

    def add(p, n, e, d, g=None):
        n = np.asarray(n, np.float64)
        n = n / np.linalg.norm(n, axis=1, keepdims=True)
        P.append(np.asarray(p, np.float64))
        N.append(n)
        E.append(np.full(len(p), e, np.int32))
        D.append(np.asarray(d, np.float64) * np.ones(len(p)))
        G.append(np.zeros(len(p)) if g is None else np.asarray(g, np.float64))

    win = (WIN_U[0], WIN_U[1], WIN_V[0] + WIN_DZ * s, WIN_V[1] + WIN_DZ * s)
    door = (DOOR_U[0] + DOOR_DX * s, DOOR_U[1] + DOOR_DX * s, DOOR_V[0], DOOR_V[1])

    # --- 床 ---------------------------------------------------------------- #
    x, y = _grid(0, RX, 0, RY, step)
    keep = (x > BASE_T) & (x < RX - BASE_T) & (y > BASE_T) & (y < RY - BASE_T)
    if not light:
        for (cx, cy) in COL_XY:
            keep &= np.hypot(x - cx, y - cy) > COL_R + 0.02
    x, y = x[keep], y[keep]
    bx = 1.0 - ((x - RX / 2) / (RX / 2)) ** 2
    by = 1.0 - ((y - RY / 2) / (RY / 2)) ** 2
    z = FLOOR_SLOPE * s * (x - RX / 2) - SAG * s * bx * by
    zx = FLOOR_SLOPE * s + SAG * s * by * 2 * (x - RX / 2) / (RX / 2) ** 2
    zy = SAG * s * bx * 2 * (y - RY / 2) / (RY / 2) ** 2
    add(np.column_stack([x, y, z]), np.column_stack([-zx, -zy, np.ones_like(x)]),
        FLOOR, z)

    # --- 天井(完全に設計どおり)-------------------------------------------- #
    x, y = _grid(0, RX, 0, RY, step)
    add(np.column_stack([x, y, np.full_like(x, RZ)]),
        np.column_stack([np.zeros_like(x), np.zeros_like(x), -np.ones_like(x)]),
        CEIL, 0.0)

    # --- 西の壁 x=0(傾き RACK)--------------------------------------------- #
    y, z = _grid(0, RY, BASE_H, RZ, step)
    xx = RACK * s * (z - RZ / 2)
    add(np.column_stack([xx, y, z]),
        np.column_stack([np.ones_like(y), np.zeros_like(y), np.full_like(y, -RACK * s)]),
        WX0, xx)

    # --- 東の壁 x=RX(傾き RACK + 膨らみ、窓あり)---------------------------- #
    y, z = _grid(0, RY, BASE_H, RZ, step)
    if not light:
        m = _outside_rect(y, z, win)
        rim = _rim(y, z, win, EDGE_BAND)
        y, z, rim = y[m], z[m], rim[m]
    else:
        rim = np.zeros_like(y, bool)
    g = BULGE * s * np.exp(-((y - RY / 2) ** 2 + (z - RZ / 2) ** 2) / (2 * BULGE_S ** 2))
    xx = RX + RACK * s * (z - RZ / 2) + g
    gy = -g * (y - RY / 2) / BULGE_S ** 2
    gz = -g * (z - RZ / 2) / BULGE_S ** 2
    add(np.column_stack([xx, y, z]),
        np.column_stack([-np.ones_like(y), gy, RACK * s + gz]),
        WX1, -(xx - RX), np.where(rim, WIN_D, 0.0))

    # --- 南の壁 y=0(開き SPLAY、戸あり)------------------------------------ #
    x, z = _grid(0, RX, BASE_H, RZ, step)
    if not light:
        m = _outside_rect(x, z, door)
        rim = _rim(x, z, door, EDGE_BAND)
        x, z, rim = x[m], z[m], rim[m]
    else:
        rim = np.zeros_like(x, bool)
    yy = -SPLAY * s * (z - RZ / 2)
    add(np.column_stack([x, yy, z]),
        np.column_stack([np.zeros_like(x), np.ones_like(x), np.full_like(x, SPLAY * s)]),
        WY0, yy, np.where(rim, DOOR_D, 0.0))

    # --- 北の壁 y=RY(開き SPLAY、逆向き)----------------------------------- #
    x, z = _grid(0, RX, BASE_H, RZ, step)
    yy = RY + SPLAY * s * (z - RZ / 2)
    add(np.column_stack([x, yy, z]),
        np.column_stack([np.zeros_like(x), -np.ones_like(x), np.full_like(x, SPLAY * s)]),
        WY1, -(yy - RY))

    if light:
        out = _pack(P, N, E, D, G)
        out["win"], out["door"] = win, door
        return out

    # --- 柱 2 本(半径が設計と違う)------------------------------------------ #
    for k, (cx, cy) in enumerate(COL_XY):
        r = COL_R + DCOL[k] * s
        nth = max(12, int(round(2 * np.pi * r / step)))
        th1 = (np.arange(nth) + 0.5) * (2 * np.pi / nth)
        z1 = np.arange(step / 2, RZ, step)
        th, z = np.meshgrid(th1, z1, indexing="ij")
        th, z = th.ravel(), z.ravel()
        px = cx + r * np.cos(th)
        py = cy + r * np.sin(th)
        add(np.column_stack([px, py, z]),
            np.column_stack([np.cos(th), np.sin(th), np.zeros_like(th)]),
            COL0 + k, r - COL_R)

    # --- 窓・戸の見込み(奥の面。開口の位置ずれはここに出る)------------------ #
    #    矩形は端まで**対称に**張る(片側だけ余ると中心が半格子ずれる)。
    def _sym(a0, a1, n):
        return np.linspace(a0, a1, max(2, n))

    for rect, eid, depth, axis in ((win, WINR, WIN_D, 0), (door, DOORR, DOOR_D, 1)):
        nu = int(round((rect[1] - rect[0]) / step)) + 1
        nv = int(round((rect[3] - rect[2]) / step)) + 1
        U, V = np.meshgrid(_sym(rect[0], rect[1], nu), _sym(rect[2], rect[3], nv),
                           indexing="ij")
        u, v = U.ravel(), V.ravel()
        rim = _rim_inside(u, v, rect, EDGE_BAND)
        if axis == 0:
            p = np.column_stack([np.full_like(u, RX + depth), u, v])
            n = np.column_stack([-np.ones_like(u), np.zeros_like(u), np.zeros_like(u)])
        else:
            p = np.column_stack([u, np.full_like(u, -depth), v])
            n = np.column_stack([np.zeros_like(u), np.ones_like(u), np.zeros_like(u)])
        add(p, n, eid, 0.0, np.where(rim, -depth, 0.0))

    # --- 幅木(設計どおり。小さい出っ張りが 1 個の数字に出ないことを見る)----- #
    for (o, ax) in ((0, 0), (RX, 0), (0, 1), (RY, 1)):
        sgn = 1.0 if o == 0 else -1.0
        span = RY if ax == 0 else RX
        a, z = _grid(0, span, 0.0, BASE_H, step)
        pos = o + sgn * BASE_T
        p = (np.column_stack([np.full_like(a, pos), a, z]) if ax == 0
             else np.column_stack([a, np.full_like(a, pos), z]))
        n = (np.column_stack([np.full_like(a, sgn), np.zeros_like(a), np.zeros_like(a)])
             if ax == 0 else
             np.column_stack([np.zeros_like(a), np.full_like(a, sgn), np.zeros_like(a)]))
        gap = np.where(z > BASE_H - EDGE_BAND, BASE_T, 0.0)
        add(p, n, BASE, 0.0, gap)
        # 幅木の上面(出は 15 mm。床は 100 mm 下 = 段差)
        a, t = _grid(0, span, 0.0, BASE_T, step / 3)
        pos2 = o + sgn * t
        p = (np.column_stack([pos2, a, np.full_like(a, BASE_H)]) if ax == 0
             else np.column_stack([a, pos2, np.full_like(a, BASE_H)]))
        n = np.column_stack([np.zeros_like(a), np.zeros_like(a), np.ones_like(a)])
        add(p, n, BASE, 0.0, np.full_like(a, BASE_H))
    return _pack(P, N, E, D, G)


def _pack(P, N, E, D, G) -> dict:
    return {"P": np.concatenate(P), "N": np.concatenate(N), "elem": np.concatenate(E),
            "dev_true": np.concatenate(D), "gap": np.concatenate(G)}


# --------------------------------------------------------------------------- #
# 2. 走査をまねる —— 死角・擦過角・混合画素・レジストレーション誤差            #
# --------------------------------------------------------------------------- #
def _reg_transform(k: int, mrad: float, mm: float, rng) -> tuple:
    """スキャン位置 k のレジストレーション誤差(既知)。0 番は基準で恒等。"""
    if k == 0 or (mrad <= 0 and mm <= 0):
        return np.eye(3), np.zeros(3)
    ax = rng.standard_normal(3)
    ax /= np.linalg.norm(ax)
    a = mrad * 1e-3
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    R = np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
    t = rng.standard_normal(3)
    t = t / np.linalg.norm(t) * mm * 1e-3
    return R, t


def _box_exit(p, u):
    """点 p から向き u へ進んで部屋の箱を出るまでの距離(混合画素の背景まで)。"""
    lo = np.array([0.0, 0.0, 0.0])
    hi = np.array([RX, RY, RZ])
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (lo - p) / u
        t2 = (hi - p) / u
    tmax = np.nanmin(np.maximum(t1, t2), axis=1)
    return np.clip(tmax, 0.0, 20.0)


def scan(surf: dict, seed: int = SEED, dropout: float = 0.0, dropout_mode: str = "random",
         mix: float = MIX_FRAC, reg_mrad: float = REG_MRAD, reg_mm: float = REG_MM,
         sig0: float = SIG0) -> dict:
    """3 か所からの走査。返り値は点・部材番号・見た位置・真の偏差。"""
    rng = np.random.default_rng(seed)
    P, N, E, D = surf["P"], surf["N"], surf["elem"], surf["dev_true"]
    gap = surf["gap"]
    out_p, out_e, out_s, out_d, out_mix = [], [], [], [], []
    seen = np.zeros(len(P), np.int32)

    for k, S in enumerate(STATIONS):
        S = np.asarray(S, np.float64)
        d = S - P
        r = np.linalg.norm(d, axis=1)
        u = d / r[:, None]
        cos = np.einsum("ij,ij->i", N, u)
        vis = cos > COS_MIN
        # 柱の影(自分自身の柱は除く)
        for j, (cx, cy) in enumerate(COL_XY):
            rc = COL_R + DCOL[j] * 1.0
            own = E == (COL0 + j)
            a = u[:, 0] ** 2 + u[:, 1] ** 2
            b = 2 * ((P[:, 0] - cx) * u[:, 0] + (P[:, 1] - cy) * u[:, 1])
            c = (P[:, 0] - cx) ** 2 + (P[:, 1] - cy) ** 2 - rc ** 2
            disc = b * b - 4 * a * c
            hit = np.zeros(len(P), bool)
            ok = disc > 0
            sq = np.sqrt(np.where(ok, disc, 0.0))
            for t in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)):
                hit |= ok & (t > 1e-3) & (t < r - 1e-3)
            vis &= ~(hit & ~own)
        # 見込みの奥の面は開口を通してしか見えない
        for eid, wall_x, rect, axis in ((WINR, RX, (WIN_U[0], WIN_U[1],
                                                    WIN_V[0] + WIN_DZ, WIN_V[1] + WIN_DZ), 0),
                                        (DOORR, 0.0, (DOOR_U[0] + DOOR_DX, DOOR_U[1] + DOOR_DX,
                                                      DOOR_V[0], DOOR_V[1]), 1)):
            m = E == eid
            if not m.any():
                continue
            denom = u[m, axis]
            t = (wall_x - P[m, axis]) / np.where(np.abs(denom) < 1e-9, 1e-9, denom)
            q = P[m] + t[:, None] * u[m]
            uu = q[:, 1] if axis == 0 else q[:, 0]
            vv = q[:, 2]
            inside = ((uu >= rect[0]) & (uu <= rect[1]) & (vv >= rect[2]) & (vv <= rect[3]))
            idx = np.nonzero(m)[0]
            vis[idx] &= inside

        seen += vis.astype(np.int32)
        idx = np.nonzero(vis)[0]
        if idx.size == 0:
            continue
        # 欠測(無作為 / 構造的 = 下から順に残す)
        if dropout > 0:
            if dropout_mode == "random":
                idx = idx[rng.random(idx.size) >= dropout]
            else:                       # "low": 高いところから落ちる
                zmax = RZ * (1.0 - dropout)
                idx = idx[P[idx, 2] <= max(zmax, 0.15)]
        if idx.size == 0:
            continue

        cc = np.clip(cos[idx], COS_MIN, 1.0)
        sig = sig0 * (1.0 + K_R * r[idx]) / cc ** 0.7
        q = P[idx] + (rng.standard_normal(idx.size) * sig)[:, None] * u[idx]

        # 混合画素 —— 段差の縁でだけ起きる(角では起きない: 段差が無いから)
        ismix = np.zeros(idx.size, bool)
        g = gap[idx].copy()
        sil = np.zeros(idx.size, bool)
        for j in (COL0, COL1):
            oncol = E[idx] == j
            sil |= oncol & (cos[idx] < 0.35)
        if sil.any():
            g[sil] = _box_exit(P[idx][sil], -u[idx][sil])
        cand = np.nonzero(np.abs(g) > 1e-6)[0]
        if cand.size and mix > 0:
            take = cand[rng.random(cand.size) < mix]
            frac = rng.uniform(0.15, 0.75, take.size)
            q[take] -= (frac * g[take])[:, None] * u[idx][take]
            ismix[take] = True

        R, t = _reg_transform(k, reg_mrad, reg_mm, np.random.default_rng(seed * 31 + k))
        q = q @ R.T + t
        out_p.append(q)
        out_e.append(E[idx])
        out_s.append(np.full(idx.size, k, np.int32))
        out_d.append(D[idx])
        out_mix.append(ismix)

    return {"P": np.concatenate(out_p), "elem": np.concatenate(out_e),
            "st": np.concatenate(out_s), "dev_true": np.concatenate(out_d),
            "mixed": np.concatenate(out_mix), "seen": seen}


# --------------------------------------------------------------------------- #
# 3. 設計モデル(CSG)—— 半空間・箱・円柱で部屋を組む                           #
# --------------------------------------------------------------------------- #
def design_sdf(pts: np.ndarray, halfspace: bool = False) -> np.ndarray:
    """設計の部屋(空気の側が負)の符号つき距離。``|値|`` が設計面までの距離。"""
    pts = np.asarray(pts, np.float64)
    if halfspace:
        # 6 枚の半空間の交わり(法線は外向き = 正の側が部屋の外)
        v = L.plane_sdf(pts, (0, 0, 0), (-1, 0, 0))
        for pt, nn in (((RX, 0, 0), (1, 0, 0)), ((0, 0, 0), (0, -1, 0)),
                       ((0, RY, 0), (0, 1, 0)), ((0, 0, 0), (0, 0, -1)),
                       ((0, 0, RZ), (0, 0, 1))):
            v = L.sdf_intersect(v, L.plane_sdf(pts, pt, nn))
    else:
        v = L.box_sdf(pts, (RX / 2, RY / 2, RZ / 2), (RX / 2, RY / 2, RZ / 2))
    for (cx, cy) in COL_XY:                       # 柱を抜く
        v = L.sdf_subtract(v, L.cylinder_sdf(pts, (cx, cy, RZ / 2), (0, 0, 1), COL_R, RZ))
    # 開口の見込み(部屋の外へ張り出す箱)
    v = L.sdf_union(v, L.box_sdf(
        pts, (RX + WIN_D / 2, sum(WIN_U) / 2, sum(WIN_V) / 2),
        (WIN_D / 2 + 0.02, (WIN_U[1] - WIN_U[0]) / 2, (WIN_V[1] - WIN_V[0]) / 2)))
    v = L.sdf_union(v, L.box_sdf(
        pts, (sum(DOOR_U) / 2, -DOOR_D / 2, sum(DOOR_V) / 2),
        ((DOOR_U[1] - DOOR_U[0]) / 2, DOOR_D / 2 + 0.02, (DOOR_V[1] - DOOR_V[0]) / 2)))
    # 幅木(部屋の内側を削る)
    for (o, ax) in ((0, 0), (RX, 0), (0, 1), (RY, 1)):
        c = [RX / 2, RY / 2, BASE_H / 2]
        h = [RX / 2, RY / 2, BASE_H / 2]
        c[ax] = o + (BASE_T / 2 if o == 0 else -BASE_T / 2)
        h[ax] = BASE_T / 2
        v = L.sdf_subtract(v, L.box_sdf(pts, c, h))
    return np.asarray(v)


def design_dev(pts: np.ndarray, elem: np.ndarray) -> np.ndarray:
    """部材ごとの設計面からの符号つき偏差(部屋の内側が正)。"""
    p = np.asarray(pts, np.float64)
    d = np.full(len(p), np.nan)
    d[elem == FLOOR] = p[elem == FLOOR, 2]
    d[elem == CEIL] = -(p[elem == CEIL, 2] - RZ)
    d[elem == WX0] = p[elem == WX0, 0]
    d[elem == WX1] = -(p[elem == WX1, 0] - RX)
    d[elem == WY0] = p[elem == WY0, 1]
    d[elem == WY1] = -(p[elem == WY1, 1] - RY)
    for k, (cx, cy) in enumerate(COL_XY):
        m = elem == COL0 + k
        d[m] = np.hypot(p[m, 0] - cx, p[m, 1] - cy) - COL_R
    d[elem == WINR] = -(p[elem == WINR, 0] - (RX + WIN_D))
    d[elem == DOORR] = p[elem == DOORR, 1] + DOOR_D
    d[elem == BASE] = 0.0
    return d


def assign_elements(pts: np.ndarray) -> np.ndarray:
    """BIM 案内の割り当て —— いちばん近い設計部材へ。実務の Scan-to-BIM と同じ。"""
    p = np.asarray(pts, np.float64)
    cand = np.stack([np.abs(design_dev(p, np.full(len(p), e, np.int32)))
                     for e in range(BASE + 1)], axis=1)
    # 幅木は面が 4 枚あるので個別に(design_dev は 0 を返す)
    bb = np.full(len(p), np.inf)
    for (o, ax) in ((0, 0), (RX, 0), (0, 1), (RY, 1)):
        sgn = 1.0 if o == 0 else -1.0
        front = np.abs(p[:, ax] - (o + sgn * BASE_T))
        far = np.maximum(np.abs(p[:, 2] - BASE_H / 2) - BASE_H / 2, 0.0)
        bb = np.minimum(bb, np.hypot(front, far))
        top = np.hypot(np.abs(p[:, 2] - BASE_H),
                       np.maximum(np.abs(p[:, ax] - o) - BASE_T, 0.0))
        bb = np.minimum(bb, top)
    cand[:, BASE] = bb
    # 部材の広がりの外は候補にしない(壁の面は部屋の中だけ)
    for e, lim in ((WX0, 0), (WX1, 0), (WY0, 1), (WY1, 1)):
        pass
    for e in (COL0, COL1):
        k = e - COL0
        far = np.maximum(np.abs(p[:, 2] - RZ / 2) - RZ / 2, 0.0)
        cand[:, e] = np.hypot(cand[:, e], far)
    for e, rect, axes in ((WINR, (WIN_U[0], WIN_U[1], WIN_V[0], WIN_V[1]), (1, 2)),
                          (DOORR, (DOOR_U[0], DOOR_U[1], DOOR_V[0], DOOR_V[1]), (0, 2))):
        du = np.maximum(np.maximum(rect[0] - p[:, axes[0]], p[:, axes[0]] - rect[1]), 0)
        dv = np.maximum(np.maximum(rect[2] - p[:, axes[1]], p[:, axes[1]] - rect[3]), 0)
        cand[:, e] = np.sqrt(cand[:, e] ** 2 + du ** 2 + dv ** 2)
    return np.argmin(cand, axis=1).astype(np.int32)


def bim_samples(step: float = 0.08) -> tuple:
    """設計モデルの面を一様サンプル(ICP の相手)。点と外向き法線。"""
    s = make_surface(scale=0.0, step=step)
    return s["P"], s["N"]


# --------------------------------------------------------------------------- #
# 4. 部材ごとの推定                                                            #
# --------------------------------------------------------------------------- #
def plane_slopes(pts: np.ndarray, axis: int, thresh: float = 0.008, seed: int = 0):
    """平面を当てて「面の法線軸に対する 2 方向の傾き [rad]」を返す。

    ``axis`` は設計上の法線の軸(0=x,1=y,2=z)。返り値は (slope_a, slope_b, rms, n)。
    壁 (axis=0) なら slope_b が z に対する傾き = 鉛直からの倒れ。
    """
    if len(pts) < 30:
        return np.nan, np.nan, np.nan, 0
    params, mask, _ = L.ransac_plane.raw(pts, thresh, iters=300, seed=seed)
    n = np.asarray(params["normal"], np.float64)
    if abs(n[axis]) < 1e-6:
        return np.nan, np.nan, np.nan, int(mask.sum())
    other = [i for i in range(3) if i != axis]
    sa, sb = -n[other[0]] / n[axis], -n[other[1]] / n[axis]
    inl = pts[mask]
    pt = np.asarray(params["point"], np.float64)
    rms = float(np.sqrt(np.mean(((inl - pt) @ (n / np.linalg.norm(n))) ** 2)))
    return float(sa), float(sb), rms, int(mask.sum())


def column_radius(pts: np.ndarray, seed: int = 0) -> float:
    """柱の半径 [m]。``estimate_normals`` → ``ransac_cylinder``。"""
    if len(pts) < 60:
        return np.nan
    q = pts if len(pts) <= 1400 else pts[np.linspace(0, len(pts) - 1, 1400).astype(int)]
    nn = np.asarray(L.estimate_normals(q, k=16))
    par, _, _ = L.ransac_cylinder.raw(q, nn, 0.006, iters=400, seed=seed)
    return float(par["radius"])


def opening_center(pts: np.ndarray, axes=(1, 2)) -> tuple:
    """見込みの奥の面の点群から開口の中心を取る(``obb``)。"""
    if len(pts) < 40:
        return np.nan, np.nan
    o = L.obb.raw(pts)
    c = np.asarray(o["center"], np.float64)
    return float(c[axes[0]]), float(c[axes[1]])


def align(scan_p: np.ndarray, mode: str, seed: int = 0) -> np.ndarray:
    """点群を BIM へ合わせる。``mode`` = none / global / datum。"""
    if mode == "none":
        return scan_p
    src = np.asarray(L.voxel_grid_downsample(scan_p, 0.10), np.float64)
    if mode == "datum":
        # 床 + 西の壁 + 南の壁だけを基準にする(現場の遣り方に近い)
        e = assign_elements(src)
        src = src[np.isin(e, (FLOOR, WX0, WY0))]
        dp, dn = bim_samples(0.10)
        e2 = np.asarray(make_surface(0.0, 0.10)["elem"])
        m = np.isin(e2, (FLOOR, WX0, WY0))
        dp, dn = dp[m], dn[m]
    else:
        dp, dn = bim_samples(0.09)
    R, t, _, _, _ = L.icp_point2plane.raw(src, dp, dn, iters=25, trim=0.9)
    return np.asarray(scan_p) @ np.asarray(R).T + np.asarray(t)


def measure_elements(scan_p: np.ndarray, seed: int = 0) -> dict:
    """割り当て → 部材ごとの推定値。"""
    e = assign_elements(scan_p)
    out = {"elem": e}
    _, out["wx0"], _, out["n_wx0"] = plane_slopes(scan_p[e == WX0], 0, seed=seed)
    _, out["wx1"], _, out["n_wx1"] = plane_slopes(scan_p[e == WX1], 0, seed=seed)
    _, out["wy0"], _, _ = plane_slopes(scan_p[e == WY0], 1, seed=seed)
    _, out["wy1"], _, _ = plane_slopes(scan_p[e == WY1], 1, seed=seed)
    out["floor_sx"], _, _, _ = plane_slopes(scan_p[e == FLOOR], 2, seed=seed)
    out["ceil_sx"], _, _, _ = plane_slopes(scan_p[e == CEIL], 2, seed=seed)
    # 床の平面度(最良平面からの残差の PV / RMS)
    fp = scan_p[e == FLOOR]
    if len(fp) > 50:
        par, mask, _ = L.ransac_plane.raw(fp, 0.020, iters=300, seed=seed)
        n = np.asarray(par["normal"]) / np.linalg.norm(par["normal"])
        res = (fp - np.asarray(par["point"])) @ n
        h, _, _ = np.histogram2d(fp[:, 0], fp[:, 1], bins=(24, 16),
                                 range=((0, RX), (0, RY)), weights=res)
        c, _, _ = np.histogram2d(fp[:, 0], fp[:, 1], bins=(24, 16), range=((0, RX), (0, RY)))
        grid = np.where(c > 0, h / np.maximum(c, 1), np.nan)
        good = np.isfinite(grid)
        out["floor_pv"] = float(np.nanmax(grid) - np.nanmin(grid))
        out["floor_rms"] = float(np.sqrt(np.nanmean(grid[good] ** 2)))
        out["floor_grid"] = grid
    else:
        out["floor_pv"] = out["floor_rms"] = np.nan
        out["floor_grid"] = np.zeros((24, 16))
    for k in (0, 1):
        out["col%d" % k] = column_radius(scan_p[e == COL0 + k], seed=seed)
    out["win_z"] = opening_center(scan_p[e == WINR], (1, 2))[1]
    out["door_x"] = opening_center(scan_p[e == DOORR], (0, 2))[0]
    return out


# --------------------------------------------------------------------------- #
# 図の道具                                                                     #
# --------------------------------------------------------------------------- #
def _bin_mean(u, v, w, rng_u, rng_v, nu, nv):
    h, _, _ = np.histogram2d(u, v, bins=(nu, nv), range=(rng_u, rng_v), weights=w)
    c, _, _ = np.histogram2d(u, v, bins=(nu, nv), range=(rng_u, rng_v))
    return np.where(c > 0, h / np.maximum(c, 1), 0.0).T[::-1]


def _with_bar(m, clip, up=4):
    """共通の色目盛りを左端に付けてから拡大する(パネル間で尺度をそろえる)。"""
    m = np.clip(np.nan_to_num(m), -clip, clip)
    h = m.shape[0]
    bar = np.linspace(clip, -clip, h)[:, None].repeat(3, 1)
    out = np.concatenate([bar, np.zeros((h, 2)), m], axis=1)
    return np.repeat(np.repeat(out, up, 0), up, 1)


# --------------------------------------------------------------------------- #
# 節 1 —— 場面と真値                                                           #
# --------------------------------------------------------------------------- #
def section_scene(surf: dict, sc: dict) -> None:
    print("\n" + "=" * 78)
    print("1) 場面 —— 部屋 %.1f x %.1f x %.1f m、走査 3 か所、施工誤差はすべて既知"
          % (RX, RY, RZ))
    print("=" * 78)
    P, E = sc["P"], sc["elem"]
    print("   面のサンプル %d 点 -> 走査で得た点 %d 点(混合画素 %d 点 = %.1f %%)"
          % (len(surf["P"]), len(P), int(sc["mixed"].sum()),
             100 * sc["mixed"].mean()))
    for e in range(BASE + 1):
        m = E == e
        if m.sum():
            print("     %-10s %6d 点   真の偏差 %+7.2f 〜 %+7.2f mm"
                  % (ELEM_JA[e], m.sum(), 1000 * sc["dev_true"][m].min(),
                     1000 * sc["dev_true"][m].max()))

    if figs.enabled():
        plan = _bin_mean(P[:, 0], P[:, 1], P[:, 2], (0, RX), (0, RY), 150, 100)
        sec = P[np.abs(P[:, 1] - 2.0) < 0.12]
        sect = _bin_mean(sec[:, 0], sec[:, 2], sec[:, 1], (0, RX), (0, RZ), 150, 75)
        elm = _bin_mean(P[:, 0], P[:, 1], E.astype(float), (0, RX), (0, RY), 150, 100)
        figs.save_grid("scene_plan_section",
                       [np.repeat(np.repeat(plan, 3, 0), 3, 1),
                        np.repeat(np.repeat(sect, 3, 0), 3, 1),
                        np.repeat(np.repeat(elm, 3, 0), 3, 1)],
                       ["平面図(色 = 点の高さ z [m]、0〜3 m)",
                        "断面 y=2.0±0.12 m(色 = y [m])",
                        "部材の割り当て(床・天井・壁 4・柱 2・見込み 2・幅木)"],
                       title="部屋 6.0 x 4.0 x 3.0 m を 3 か所から走査した点群", ncols=3,
                       caption="柱の後ろに影(欠測)が伸び、開口の見込みが奥に見える。")
        cov = _bin_mean(surf["P"][:, 0], surf["P"][:, 1], surf["seen"].astype(float),
                        (0, RX), (0, RY), 120, 80)
        w = surf["elem"] == WY1
        covw = _bin_mean(surf["P"][w, 0], surf["P"][w, 2], surf["seen"][w].astype(float),
                         (0, RX), (0, RZ), 120, 60)
        figs.save_grid("station_coverage",
                       [np.repeat(np.repeat(cov, 4, 0), 4, 1),
                        np.repeat(np.repeat(covw, 4, 0), 4, 1)],
                       ["床を見たスキャン位置の数(0〜3)", "北の壁を見た数(0〜3)"],
                       title="視線に依存する欠測 —— 柱の影と擦過角",
                       caption="暗い所は 1 か所も見ていない。柱の影は放射状に伸びる。")


# --------------------------------------------------------------------------- #
# 節 2 —— ゼロ点: 建物 1 個の数字                                              #
# --------------------------------------------------------------------------- #
def section_zero_point(seed: int = SEED) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— 点群全体を BIM へ一括 ICP して平均距離を 1 個出す")
    print("=" * 78)
    rows, keep = [], {}
    for tag, sscale, msig in (("(a) 誤差ゼロ + 測定の癖", 0.0, 1.0),
                              ("(b) 施工誤差だけ(測定は理想)", 1.0, 0.0),
                              ("(c) 両方(実際に測る条件)", 1.0, 1.0)):
        surf = make_surface(sscale)
        s = scan(surf, seed=seed, mix=MIX_FRAC * msig, sig0=SIG0 * msig,
                 reg_mrad=REG_MRAD * msig, reg_mm=REG_MM * msig)
        p = align(s["P"], "global", seed=seed)
        d = np.abs(design_sdf(p))
        rows.append([tag, "%.2f" % (1000 * d.mean()), "%.2f" % (1000 * np.median(d)),
                     "%.2f" % (1000 * np.percentile(d, 95))])
        print("   %-30s 平均 %5.2f mm / 中央 %5.2f mm / 95 %% %6.2f mm"
              % (tag, 1000 * d.mean(), 1000 * np.median(d), 1000 * np.percentile(d, 95)))
        keep[tag[1]] = (surf, s, p, d)
    gap = float(rows[2][1]) - float(rows[0][1])
    print("\n   ★施工誤差のあるなしで平均距離は %.2f mm しか動かない。" % gap)
    print("     同じ点群を要素ごとに見ると柱の半径 +6.5 mm、床の反り 12 mm の"
          "不良が入っている(節 5)。")
    print("     幅木(出 %.0f mm)は点の %.1f %% しかないので、1 個の数字には最初から出てこない。"
          % (1000 * BASE_T, 100 * (keep["c"][1]["elem"] == BASE).mean()))
    figs.save_table("one_number", ["条件", "平均 [mm]", "中央 [mm]", "95 % [mm]"], rows,
                    title="建物 1 個の数字(BIM への平均距離)は施工誤差にほとんど反応しない",
                    caption="(a) と (c) の差 %.2f mm。要素ごとの不良は桁が違う。" % gap)
    return {"rows": rows, "gap": gap, "keep": keep}


# --------------------------------------------------------------------------- #
# 節 3 —— 合わせが吸うもの・配るもの                                           #
# --------------------------------------------------------------------------- #
def predicted_phi(surf: dict, sc: dict) -> float:
    """y 軸まわりの回転を最小二乗で決めたときの角 [rad] を幾何で予測する。

    回転 φ は各部材へ「腕の長さ × φ」の変位を与える。壁 x=const は z 方向の腕、
    床と天井は x 方向の腕。最小二乗解は各部材の**てこ** Σ(腕 - 平均腕)² を
    重みにした、部材ごとの含み角の加重平均になる。
    """
    P, E = sc["P"], sc["elem"]
    num = den = 0.0
    for e, arm, theta in ((WX0, 2, RACK), (WX1, 2, RACK),
                          (FLOOR, 0, -FLOOR_SLOPE), (CEIL, 0, 0.0)):
        m = E == e
        if m.sum() < 10:
            continue
        w = float(np.var(P[m, arm]) * m.sum())
        num += w * theta
        den += w
    return num / den if den else 0.0


def section_alignment(seed: int = SEED) -> dict:
    print("\n" + "=" * 78)
    print("3) ★合わせは剛体モードを吸い、余りを他の部材へ配る")
    print("=" * 78)
    surf = make_surface(1.0)
    sc = scan(surf, seed=seed)
    phi_pred = predicted_phi(surf, sc)
    print("   真値: 東西の壁の傾き %.2f mrad / 床の勾配 %.2f mrad / 天井 %.2f mrad"
          % (1000 * RACK, -1000 * FLOOR_SLOPE, 0.0))
    print("   幾何の予測 —— てこ Σ(腕)² で重みづけした加重平均角 φ = %.2f mrad"
          % (1000 * phi_pred))

    rows, res = [], {}
    for mode, name in (("none", "合わせない(設計座標のまま)"),
                       ("datum", "床 + 西 + 南の壁を基準"),
                       ("global", "全体 ICP(点群まるごと)")):
        p = align(sc["P"], mode, seed=seed)
        m = measure_elements(p, seed=seed)
        rack = 0.5 * (m["wx0"] + m["wx1"])
        splay = 0.5 * (m["wy0"] - m["wy1"])
        res[mode] = m
        res[mode]["rack"] = rack
        res[mode]["splay"] = splay
        res[mode]["P"] = p
        rows.append([name, "%+.2f" % (1000 * rack), "%+.2f" % (1000 * splay),
                     "%+.2f" % (1000 * m["floor_sx"]), "%+.2f" % (1000 * m["ceil_sx"]),
                     "%.2f" % (1000 * m["floor_pv"])])
        print("   %-26s 壁の傾き %+5.2f / 開き %+5.2f / 床の勾配 %+5.2f / "
              "天井の勾配 %+5.2f mrad / 床の反り %5.2f mm"
              % (name, 1000 * rack, 1000 * splay, 1000 * m["floor_sx"],
                 1000 * m["ceil_sx"], 1000 * m["floor_pv"]))
    rows.append(["真値", "%+.2f" % (1000 * RACK), "%+.2f" % (1000 * SPLAY),
                 "%+.2f" % (-1000 * FLOOR_SLOPE), "+0.00", "%.2f" % (1000 * SAG)])
    print("   %-26s 壁の傾き %+5.2f / 開き %+5.2f / 床の勾配 %+5.2f / "
          "天井の勾配 %+5.2f mrad / 床の反り %5.2f mm"
          % ("真値", 1000 * RACK, 1000 * SPLAY, -1000 * FLOOR_SLOPE, 0.0, 1000 * SAG))

    g = res["global"]
    print("\n   ★全体 ICP のあと、無傷の天井が %+.2f mrad 傾いて見える(真値 0)。"
          % (1000 * g["ceil_sx"]))
    print("     壁は真値の %.0f %%、床の勾配は %.0f %% に痩せた。"
          % (100 * g["rack"] / RACK, 100 * g["floor_sx"] / (-FLOOR_SLOPE)))
    phi_icp = float(np.mean([RACK - g["rack"], -FLOOR_SLOPE - g["floor_sx"],
                             0.0 - g["ceil_sx"]]))
    print("     ICP が取った角 φ の実測 %.2f mrad(予測 %.2f mrad、差 %.2f mrad)。"
          % (1000 * phi_icp, 1000 * phi_pred, 1000 * abs(phi_icp - phi_pred)))
    print("   ★吸われるのは剛体モードだけ: 南北の壁の開き %.2f mrad(真値 %.2f)と"
          % (1000 * g["splay"], 1000 * SPLAY))
    print("     床の反り %.2f mm(真値 %.2f)は合わせても動かない。"
          % (1000 * g["floor_pv"], 1000 * SAG))

    figs.save_table("alignment_absorption",
                    ["合わせ方", "壁の傾き [mrad]", "壁の開き [mrad]",
                     "床の勾配 [mrad]", "天井の勾配 [mrad]", "床の反り PV [mm]"], rows,
                    title="合わせ方で動くのは剛体モードだけ(天井は無傷なのに傾いて見える)",
                    caption="予測 φ = %.2f mrad / 実測 %.2f mrad。"
                            % (1000 * phi_pred, 1000 * phi_icp))
    figs.save_plot("alignment_bars",
                   [("真値", [0, 1, 2, 3], [1000 * RACK, 1000 * SPLAY,
                                            -1000 * FLOOR_SLOPE, 0.0]),
                    ("合わせない", [0, 1, 2, 3],
                     [1000 * res["none"]["rack"], 1000 * res["none"]["splay"],
                      1000 * res["none"]["floor_sx"], 1000 * res["none"]["ceil_sx"]]),
                    ("床+2 壁を基準", [0, 1, 2, 3],
                     [1000 * res["datum"]["rack"], 1000 * res["datum"]["splay"],
                      1000 * res["datum"]["floor_sx"], 1000 * res["datum"]["ceil_sx"]]),
                    ("全体 ICP", [0, 1, 2, 3],
                     [1000 * g["rack"], 1000 * g["splay"],
                      1000 * g["floor_sx"], 1000 * g["ceil_sx"]])],
                   xlabel="0=壁の傾き 1=壁の開き 2=床の勾配 3=天井の勾配",
                   ylabel="角度 [mrad]",
                   title="合わせるほど傾きは消え、天井には無い傾きが生まれる",
                   kinds=["scatter"] * 4)
    return {"res": res, "phi_pred": phi_pred, "phi_icp": phi_icp, "surf": surf, "sc": sc}


# --------------------------------------------------------------------------- #
# 節 4 —— 偏差の地図と、偽の施工誤差の地図                                     #
# --------------------------------------------------------------------------- #
def _dev_maps(p: np.ndarray, e: np.ndarray, clip=0.012):
    d = design_dev(p, e)
    panels, caps = [], []
    spec = ((FLOOR, 0, 1, (0, RX), (0, RY)), (CEIL, 0, 1, (0, RX), (0, RY)),
            (WX0, 1, 2, (0, RY), (0, RZ)), (WX1, 1, 2, (0, RY), (0, RZ)),
            (WY0, 0, 2, (0, RX), (0, RZ)), (WY1, 0, 2, (0, RX), (0, RZ)))
    for elem, ia, ib, ra, rb in spec:
        m = (e == elem) & np.isfinite(d)
        nu = 48 if ra[1] > 5 else 36
        mp = _bin_mean(p[m, ia], p[m, ib], 1000 * d[m], ra, rb, nu, 30)
        panels.append(_with_bar(mp, 1000 * clip))
        caps.append("%s(%+.1f 〜 %+.1f mm)"
                    % (ELEM_JA[elem], 1000 * np.nanmin(d[m]), 1000 * np.nanmax(d[m])))
    return panels, caps


def section_maps(alignres: dict, zero: dict, seed: int = SEED) -> dict:
    print("\n" + "=" * 78)
    print("4) 偏差の地図 —— 本物の施工誤差と、何も間違っていないのに出る偽の誤差")
    print("=" * 78)
    g = alignres["res"]["global"]
    p, e = g["P"], g["elem"]
    panels, caps = _dev_maps(p, e)
    figs.save_grid("deviation_map", panels, caps, ncols=3, signed=True,
                   title="設計面からの偏差 [mm](全体 ICP のあと、±12 mm で切る)",
                   caption="左端の帯が色目盛り(上 +12 mm / 下 -12 mm)。"
                           "天井は無傷なのに東西方向の傾きが乗っている。")

    surf0 = make_surface(0.0)
    s0 = scan(surf0, seed=seed)
    p0 = align(s0["P"], "global", seed=seed)
    e0 = assign_elements(p0)
    panels0, caps0 = _dev_maps(p0, e0)
    figs.save_grid("false_deviation_map", panels0, caps0, ncols=3, signed=True,
                   title="偽の施工誤差 —— 設計どおりに建った建物を同じ手順で測った地図",
                   caption="仕込んだ施工誤差はゼロ。見えているのは測定と合わせだけが作った量。")

    m0 = measure_elements(p0, seed=seed)
    rack0 = 0.5 * (m0["wx0"] + m0["wx1"])
    splay0 = 0.5 * (m0["wy0"] - m0["wy1"])
    print("   誤差ゼロの建物を同じ手順で測ると: 壁の傾き %+.2f mrad / 開き %+.2f mrad /"
          % (1000 * rack0, 1000 * splay0))
    print("     床の勾配 %+.2f mrad / 天井の勾配 %+.2f mrad / 床の反り PV %.2f mm /"
          % (1000 * m0["floor_sx"], 1000 * m0["ceil_sx"], 1000 * m0["floor_pv"]))
    print("     柱の半径 %+.2f / %+.2f mm。**これが偽の施工誤差の大きさ**。"
          % (1000 * (m0["col0"] - COL_R), 1000 * (m0["col1"] - COL_R)))
    d0 = design_dev(p0, e0)
    print("   偽の偏差の大きさ: RMS %.2f mm / 95 %% %.2f mm / 最大 %.2f mm"
          % (1000 * np.sqrt(np.nanmean(d0 ** 2)),
             1000 * np.nanpercentile(np.abs(d0), 95), 1000 * np.nanmax(np.abs(d0))))
    return {"false": m0, "rack0": rack0, "splay0": splay0}


# --------------------------------------------------------------------------- #
# 節 5 —— 要素ごとの判定表                                                     #
# --------------------------------------------------------------------------- #
TOL = {"wall": 3.0, "floor_slope": 3.0, "ceil_slope": 3.0,
       "flatness": 7.0, "col": 5.0, "open": 20.0}


def section_verdicts(alignres: dict, false_m: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) 要素ごとの判定 —— 建物 1 個の数字では見えない不良が並ぶ")
    print("=" * 78)
    g = alignres["res"]["global"]
    n = alignres["res"]["none"]
    f = false_m["false"]
    items = [
        ("東西の壁の傾き [mrad]", 1000 * RACK, 1000 * n["rack"], 1000 * g["rack"],
         1000 * false_m["rack0"], TOL["wall"]),
        ("南北の壁の開き [mrad]", 1000 * SPLAY, 1000 * n["splay"], 1000 * g["splay"],
         1000 * false_m["splay0"], TOL["wall"]),
        ("床の勾配 [mrad]", -1000 * FLOOR_SLOPE, 1000 * n["floor_sx"],
         1000 * g["floor_sx"], 1000 * f["floor_sx"], TOL["floor_slope"]),
        ("天井の勾配 [mrad]", 0.0, 1000 * n["ceil_sx"], 1000 * g["ceil_sx"],
         1000 * f["ceil_sx"], TOL["ceil_slope"]),
        ("床の平面度 PV [mm]", 1000 * SAG, 1000 * n["floor_pv"], 1000 * g["floor_pv"],
         1000 * f["floor_pv"], TOL["flatness"]),
        ("柱 A の半径の狂い [mm]", 1000 * DCOL[0], 1000 * (n["col0"] - COL_R),
         1000 * (g["col0"] - COL_R), 1000 * (f["col0"] - COL_R), TOL["col"]),
        ("柱 B の半径の狂い [mm]", 1000 * DCOL[1], 1000 * (n["col1"] - COL_R),
         1000 * (g["col1"] - COL_R), 1000 * (f["col1"] - COL_R), TOL["col"]),
        ("窓の高さのずれ [mm]", 1000 * WIN_DZ,
         1000 * (n["win_z"] - sum(WIN_V) / 2), 1000 * (g["win_z"] - sum(WIN_V) / 2),
         1000 * (f["win_z"] - sum(WIN_V) / 2), TOL["open"]),
        ("戸の位置のずれ [mm]", 1000 * DOOR_DX,
         1000 * (n["door_x"] - sum(DOOR_U) / 2), 1000 * (g["door_x"] - sum(DOOR_U) / 2),
         1000 * (f["door_x"] - sum(DOOR_U) / 2), TOL["open"]),
    ]
    rows = []
    print("   項目                      真値   合わせない  全体ICP   偽の誤差  許容  判定")
    n_ok = n_miss = n_false = 0
    for name, t, vn, vg, vf, tol in items:
        jt = "不合格" if abs(t) > tol else "合格"
        jg = "不合格" if abs(vg) > tol else "合格"
        if jt != jg:
            n_miss += 1
        else:
            n_ok += 1
        if abs(t) <= tol and abs(vf) > tol:
            n_false += 1
        rows.append([name, "%+.2f" % t, "%+.2f" % vn, "%+.2f" % vg, "%+.2f" % vf,
                     "±%.1f" % tol, "%s / %s" % (jt, jg)])
        print("   %-24s %+7.2f  %+8.2f  %+8.2f  %+8.2f  ±%.1f  真=%s 測=%s"
              % (name, t, vn, vg, vf, tol, jt, jg))
    print("\n   全体 ICP のあとの判定は %d 項目中 %d 項目が真値と食い違う。"
          % (len(items), n_miss))
    figs.save_table("element_verdicts",
                    ["項目", "真値", "合わせない", "全体 ICP", "偽の誤差", "許容", "判定 真/測"],
                    rows, title="要素ごとの as-built 判定(許容値は施工精度の目安)",
                    caption="「偽の誤差」列は設計どおりに建った建物を同じ手順で測った値。")
    return {"n_miss": n_miss, "n_ok": n_ok, "rows": rows}


# --------------------------------------------------------------------------- #
# 節 6-8 —— 崖                                                                 #
# --------------------------------------------------------------------------- #
def _light_rack(seed, dropout=0.0, mode="random", mix=0.0, reg=0.0, sig=SIG0):
    """軽い場面で「東西の壁の傾き」を測る(掃引用)。傾きと使った点数・高さを返す。"""
    surf = make_surface(1.0, step=STEP_LIGHT, light=True)
    s = scan(surf, seed=seed, dropout=dropout, dropout_mode=mode, mix=mix,
             reg_mrad=reg, reg_mm=reg * 2.0, sig0=sig)
    e = assign_elements(s["P"])
    vals, ns, hs = [], [], []
    for elem, ax in ((WX0, 0), (WX1, 0)):
        q = s["P"][e == elem]
        if len(q) < 40:
            return np.nan, 0, 0.0
        _, sb, _, ni = plane_slopes(q, ax, seed=seed)
        vals.append(sb if elem == WX0 else sb)
        ns.append(ni)
        hs.append(q[:, 2].std() * np.sqrt(12.0))
    return float(np.mean(vals)), int(np.mean(ns)), float(np.mean(hs))


def section_cliff_dropout() -> dict:
    print("\n" + "=" * 78)
    print("6) ★崖は欠測率では決まらない —— 効くのは残った面の高さ L")
    print("=" * 78)
    print("   予測: 傾きの標準誤差 = σ√12 / (L √N)。σ は面に直交する測距誤差。")
    print("   欠測率  無作為: 傾き±散らばり [mrad]   構造的(下から残す): 傾き±散らばり  L [m]  予測")
    fr, rnd_sd, low_sd, pred = [], [], [], []
    rows = []
    for dr in (0.0, 0.3, 0.6, 0.8, 0.9, 0.95):
        a = [_light_rack(11 + i, dropout=dr, mode="random") for i in range(4)]
        b = [_light_rack(11 + i, dropout=dr, mode="low") for i in range(4)]
        av = np.array([x[0] for x in a])
        bv = np.array([x[0] for x in b])
        bn = np.mean([x[1] for x in b])
        bl = np.mean([x[2] for x in b])
        sig_n = SIG0 * (1 + K_R * 3.0)      # 3 m 前後の距離での代表的な σ
        pr = sig_n * np.sqrt(12.0) / (max(bl, 0.05) * np.sqrt(max(bn, 1)))
        fr.append(100 * dr)
        rnd_sd.append(1000 * float(np.std(av)))
        low_sd.append(1000 * float(np.std(bv)))
        pred.append(1000 * pr)
        rows.append(["%.0f %%" % (100 * dr), "%+.3f ± %.3f" % (1000 * av.mean(), rnd_sd[-1]),
                     "%+.3f ± %.3f" % (1000 * bv.mean(), low_sd[-1]),
                     "%.2f" % bl, "%.3f" % pred[-1]])
        print("   %4.0f %%   %+6.3f ± %5.3f              %+6.3f ± %5.3f          "
              "%.2f   %.3f"
              % (100 * dr, 1000 * av.mean(), rnd_sd[-1], 1000 * bv.mean(),
                 low_sd[-1], bl, pred[-1]))
    ratio = low_sd[-2] / max(rnd_sd[-2], 1e-9)
    print("\n   ★同じ欠測率 %.0f %% で散らばりが %.1f 倍違う(無作為 %.3f / 構造的 %.3f mrad)。"
          % (fr[-2], ratio, rnd_sd[-2], low_sd[-2]))
    print("     予測 %.3f mrad と実測 %.3f mrad の差は %.0f %%。"
          % (pred[-2], low_sd[-2], 100 * abs(pred[-2] - low_sd[-2]) / max(low_sd[-2], 1e-9)))
    figs.save_plot("cliff_dropout",
                   [("無作為に落とす", fr, rnd_sd), ("下から順に残す(構造的)", fr, low_sd),
                    ("予測 σ√12/(L√N)", fr, pred),
                    ("施工誤差 3 mrad の 1/3", fr, [1000 * RACK / 3] * len(fr))],
                   xlabel="欠測率 [%]", ylabel="壁の傾きの散らばり(4 種) [mrad]",
                   title="同じ欠測率でも壊れ方が 2 桁違う(効くのは残った面の高さ L)",
                   caption="構造的な欠測は L を縮めるので L^-1.5 で荒れる。")
    figs.save_table("cliff_dropout_table",
                    ["欠測率", "無作為 [mrad]", "構造的 [mrad]", "残った高さ L [m]", "予測 [mrad]"],
                    rows, title="欠測の掃引 —— 同じ欠測率、違う崖")
    return {"fr": fr, "rnd": rnd_sd, "low": low_sd, "pred": pred, "ratio": ratio}


def section_cliff_registration() -> dict:
    print("\n" + "=" * 78)
    print("7) ★★レジストレーション誤差は系統誤差 —— 点を増やしても消えない")
    print("=" * 78)
    print("   姿勢誤差 [mrad]   偽の傾き(誤差ゼロの建物) [mrad]   信号対雑音(3 mrad に対して)")
    xs, bias, snr = [], [], []
    rows = []
    for reg in (0.0, 0.5, 1.0, 2.0, 3.0, 5.0):
        vals = []
        for i in range(4):
            surf = make_surface(0.0, step=STEP_LIGHT, light=True)
            s = scan(surf, seed=31 + i, mix=0.0, reg_mrad=reg, reg_mm=reg * 2.0)
            e = assign_elements(s["P"])
            v = []
            for elem in (WX0, WX1):
                q = s["P"][e == elem]
                _, sb, _, _ = plane_slopes(q, 0, seed=i)
                v.append(sb)
            vals.append(np.mean(v))
        b = 1000 * float(np.sqrt(np.mean(np.square(vals))))
        xs.append(reg)
        bias.append(b)
        snr.append(1000 * RACK / max(b, 1e-3))
        rows.append(["%.1f" % reg, "%.3f" % b, "%.1f" % snr[-1]])
        print("   %8.1f          %8.3f                         %6.1f" % (reg, b, snr[-1]))
    print("\n   ★点の数は 3 条件とも同じ(%s 点前後)。無作為欠測は √N で薄まるのに、"
          % "9 千")
    print("     姿勢誤差は N に無関係な系統誤差なので薄まらない。")
    i1 = xs.index(1.0)
    print("     姿勢誤差 %.1f mrad で偽の傾き %.3f mrad、信号対雑音 %.1f。"
          % (xs[i1], bias[i1], snr[i1]))
    figs.save_plot("cliff_registration",
                   [("偽の傾き(誤差ゼロの建物)", xs, bias),
                    ("施工誤差 3 mrad", xs, [1000 * RACK] * len(xs)),
                    ("その 1/3(検出の目安)", xs, [1000 * RACK / 3] * len(xs))],
                   xlabel="スキャン位置の姿勢誤差 [mrad]", ylabel="偽の壁の傾き [mrad]",
                   title="検出限界を決めるのは測距の雑音ではなくレジストレーション",
                   caption="点を増やしても系統誤差は薄まらない。")
    figs.save_table("cliff_registration_table",
                    ["姿勢誤差 [mrad]", "偽の傾き [mrad]", "信号対雑音"], rows,
                    title="レジストレーション誤差の掃引")
    return {"xs": xs, "bias": bias, "snr": snr}


def section_cliff_mixed(seed: int = SEED) -> dict:
    print("\n" + "=" * 78)
    print("8) ★混合画素は平面に効かず、円柱の半径にだけ効く")
    print("=" * 78)
    print("   混合の割合   壁の傾き [mrad]   柱 A の半径の狂い [mm]  柱 B [mm]")
    xs, wall, ca, cb = [], [], [], []
    rows = []
    base_rack = None
    for mf in (0.0, 0.05, 0.12, 0.20, 0.30):
        surf = make_surface(1.0)
        s = scan(surf, seed=seed, mix=mf, reg_mrad=0.0, reg_mm=0.0)
        e = assign_elements(s["P"])
        r = []
        for elem in (WX0, WX1):
            _, sb, _, _ = plane_slopes(s["P"][e == elem], 0, seed=seed)
            r.append(sb)
        rk = 1000 * float(np.mean(r))
        r0 = 1000 * (column_radius(s["P"][e == COL0], seed=seed) - COL_R)
        r1 = 1000 * (column_radius(s["P"][e == COL1], seed=seed) - COL_R)
        if base_rack is None:
            base_rack, base_c0 = rk, r0
        xs.append(100 * mf)
        wall.append(rk)
        ca.append(r0)
        cb.append(r1)
        rows.append(["%.0f %%" % (100 * mf), "%+.3f" % rk, "%+.2f" % r0, "%+.2f" % r1])
        print("   %8.0f %%   %+10.3f       %+12.2f        %+8.2f" % (100 * mf, rk, r0, r1))
    dw = wall[-1] - base_rack
    dc = ca[-1] - base_c0
    print("\n   ★混合 %.0f %% で壁の傾きは %+.3f mrad しか動かない(RANSAC が外れ値として落とす)。"
          % (xs[-1], dw))
    print("     同じ割合で柱 A の半径は %+.2f mm 動く —— 柱は輪郭が**全周**縁なので、"
          % dc)
    print("     混合画素が一様に内側へ寄って外れ値でなく系統的な縮みになる。")
    figs.save_plot("cliff_mixed",
                   [("柱 A の半径の狂い [mm]", xs, ca), ("柱 B の半径の狂い [mm]", xs, cb),
                    ("壁の傾き [mrad](別単位)", xs, wall),
                    ("柱の真値 A [mm]", xs, [1000 * DCOL[0]] * len(xs))],
                   xlabel="混合画素の割合 [%]", ylabel="狂い [mm] / 傾き [mrad]",
                   title="混合画素は平面には効かず円柱の半径を縮める",
                   caption="平面は片側だけが縁なので外れ値、円柱は全周が縁なので系統誤差。")
    figs.save_table("cliff_mixed_table",
                    ["混合の割合", "壁の傾き [mrad]", "柱 A [mm]", "柱 B [mm]"], rows,
                    title="混合画素の掃引")
    return {"xs": xs, "wall": wall, "ca": ca, "cb": cb, "dw": dw, "dc": dc}


# --------------------------------------------------------------------------- #
# 節 9 —— 道具の穴と 3-D の落とし穴                                            #
# --------------------------------------------------------------------------- #
def section_tool_gaps(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("9) 道具の穴と 3-D の落とし穴")
    print("=" * 78)
    q = sc["P"][::37]
    a = design_sdf(q, halfspace=True)
    b = design_sdf(q, halfspace=False)
    inside = b < 0
    di = float(np.max(np.abs(a[inside] - b[inside]))) if inside.any() else 0.0
    do = float(np.max(np.abs(a[~inside] - b[~inside]))) if (~inside).any() else 0.0
    print("   (a) 6 枚の半空間 (plane_sdf + sdf_intersect) と厳密な box_sdf の差:")
    print("       部屋の内側 最大 %.4f mm / 外側(角の近く)最大 %.1f mm。"
          % (1000 * di, 1000 * do))
    print("       max による交差は角の外で過小評価する —— op の docstring の警告どおり。")

    n = np.asarray(L.estimate_normals(sc["P"][:800], k=16))
    up = float(np.mean(n[:, 2] > 0))
    print("   (b) estimate_normals の符号は任意: 同じ壁の点で上向き %.0f %% / 下向き %.0f %%。"
          % (100 * up, 100 * (1 - up)))

    assert not hasattr(fs, "plane_segmentation") and hasattr(fs.ledger, "plane_segmentation")
    print("   (c) 3-D の面の op(plane_segmentation / ransac_plane / icp_* / *_sdf)は"
          "fullseye.ledger からしか呼べない(1 行ファサードには出ていない)。")

    print("   (d) 公開経路に無かった処理: ① 散らばった点を面の座標へ落として"
          "格子に均す(偏差地図)")
    print("       ② 平面の法線から『鉛直からの倒れ』を出す(法線 → 2 方向の勾配)")
    print("       ③ 施工の許容値と突き合わせる判定 ④ 点群からの開口(矩形の穴)の"
          "検出 —— obb で代用した")
    print("       ⑤ 走査の視線シミュレーション(死角・入射角・混合画素)。"
          "いずれも numpy で書いた。")

    print("   (e) icp_point2point_3d は torch.Tensor を返す(icp_point2plane は numpy)。"
          "同じ族で戻り値の型が違う。")
    return {"di": di, "do": do, "normal_up": up}


# --------------------------------------------------------------------------- #
def section_segmentation(sc: dict, seed: int = SEED) -> dict:
    print("\n" + "=" * 78)
    print("10) BIM 案内の割り当て vs BIM 無しの面分割")
    print("=" * 78)
    e = assign_elements(sc["P"])
    acc = float(np.mean(e == sc["elem"]))
    mm = sc["mixed"]
    acc_mix = float(np.mean(e[mm] == sc["elem"][mm])) if mm.any() else np.nan
    print("   BIM 案内の割り当ての正答率 %.2f %%(混合画素だけだと %.2f %%)"
          % (100 * acc, 100 * acc_mix))
    q = np.asarray(L.voxel_grid_downsample(sc["P"], 0.09), np.float64)
    lab = np.asarray(L.plane_segmentation(q, 0.010, 400, max_planes=8, iters=200, seed=seed))
    nseg = int(lab.max()) + 1
    print("   BIM 無し(plane_segmentation)は %d 点から %d 枚の面を出し、"
          "%.1f %% の点が残差(柱・幅木・見込み)。"
          % (len(q), nseg, 100 * np.mean(lab < 0)))
    return {"acc": acc, "acc_mix": acc_mix, "nseg": nseg}


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("設計モデルと実際の建物のずれを点群から測る(Scan-to-BIM の as-built 検査)")
    print("部屋 %.1f x %.1f x %.1f m / 柱 2 本 / 開口 2 つ / 幅木、走査 3 か所"
          % (RX, RY, RZ))
    print("=" * 78)

    surf = make_surface(1.0)
    sc = scan(surf, seed=SEED)
    surf["seen"] = sc["seen"]
    section_scene(surf, sc)
    zero = section_zero_point()
    al = section_alignment()
    fm = section_maps(al, zero)
    vd = section_verdicts(al, fm)
    cd = section_cliff_dropout()
    cr = section_cliff_registration()
    cm = section_cliff_mixed()
    sg = section_segmentation(sc)
    tg = section_tool_gaps(sc)

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    g = al["res"]["global"]
    print("  * 建物 1 個の数字(BIM への平均距離)は施工誤差のあるなしで %.2f mm しか"
          "動かない。" % zero["gap"])
    print("  * 全体 ICP は剛体モードを吸い、余りを配る: 壁 %.2f → %.2f mrad、"
          "無傷の天井に %+.2f mrad。"
          % (1000 * RACK, 1000 * g["rack"], 1000 * g["ceil_sx"]))
    print("    予測 φ %.2f / 実測 %.2f mrad。剛体でない開き %.2f mrad と反り %.2f mm は残る。"
          % (1000 * al["phi_pred"], 1000 * al["phi_icp"],
             1000 * g["splay"], 1000 * g["floor_pv"]))
    print("  * 崖は欠測率でなく残った面の高さ L で決まる(同じ %.0f %% で %.1f 倍)。"
          % (cd["fr"][-2], cd["ratio"]))
    print("  * 検出限界を決めるのはレジストレーション(1 mrad で偽の傾き %.3f mrad)。"
          % cr["bias"][cr["xs"].index(1.0)])
    print("  * 混合画素は平面に効かず(%+.3f mrad)円柱に効く(%+.2f mm)。"
          % (cm["dw"], cm["dc"]))

    # --- 所見を固定する ------------------------------------------------------ #
    assert abs(g["rack"]) < 0.80 * RACK, ("全体 ICP が傾きを吸っていない", g["rack"])
    assert abs(g["ceil_sx"]) > 0.4e-3, ("天井の偽の傾きが出ていない", g["ceil_sx"])
    assert abs(al["phi_icp"] - al["phi_pred"]) < 0.6e-3, (al["phi_icp"], al["phi_pred"])
    assert abs(g["splay"] - SPLAY) < 0.6e-3, ("剛体でないモードまで消えた", g["splay"])
    assert g["floor_pv"] > 0.6 * SAG, ("反りが消えた", g["floor_pv"])
    assert zero["gap"] < 2.0, ("1 個の数字が思ったより反応した", zero["gap"])
    assert cd["ratio"] > 3.0, ("構造的な欠測の崖が出ていない", cd["ratio"])
    assert cr["bias"][-1] > cr["bias"][0], ("姿勢誤差が効いていない", cr["bias"])
    assert abs(cm["dw"]) < 0.30, ("混合画素が平面に効いてしまった", cm["dw"])
    assert abs(cm["dc"]) > 0.30, ("混合画素が円柱に効いていない", cm["dc"])
    assert tg["do"] > 10 * tg["di"], ("CSG の角の過小評価が出ていない", tg)
    assert sg["acc"] > 0.90, ("BIM 案内の割り当てが壊れている", sg["acc"])

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
