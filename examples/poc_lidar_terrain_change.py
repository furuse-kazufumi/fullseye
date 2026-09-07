# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""斜面の土量を測る —— 縦に引くか、法線方向に測るか。

航空 LiDAR で斜面が崩れた前後を測り、**掘削した土量と堆積した土量 [m3]**、
そして**変化した面積 [m2]** を出す仕事です。現場でいちばん普通のやり方は
**DoD**(DEM of Difference: 両時期を格子の標高図にして引き算)。もう一つが
**M3C2**(局所平面を当てて、その**法線方向**に距離を測る)。

EXTEND: 実測に差し替えるなら :func:`make_cloud` の戻り値(記録座標 (N,3) の
点群と地面点フラグ)を LAS/LAZ の読み込みに置き換えます。実データでは
(a) 地面点の分類は済んでいる代わりに**分類の誤りが真値として見えなくなる**、
(b) 系統誤差の真値が無いので :func:`section_systematic` の「位置合わせ前後の
実変位」は測れず安定域の残差 RMS で代用するしかない、(c) 崩壊土量の真値は
現地測量か UAV-SfM でしか得られず精度は本 PoC の合成真値より 1 桁悪い ——
という 3 点が変わります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**「DoD は斜面で cos だけ体積を間違える」は間違い**。予想は「傾斜 40 度
   では体積が cos40 = 0.766 倍に縮む」だったが、鉛直差分を**水平投影面積で
   積分する**限り cos は約分して消える(式は 2 節で先に出す)。雑音を止めた
   格子標本で測ると 傾斜 0→40 度で掘削体積の誤差は **-0.06 % → -0.09 %**、
   傾向は無い。間違うのは体積ではなく**厚さ**のほう。
2. ★**DoD の「深さ」は法線厚さを sec θ 倍で過大に言う**。崩壊中心の
   DoD 深さ / M3C2 厚さの比は 10 度で **1.003**、40 度で **1.247**
   (予測 sec θ = 1.015 / 1.305)。「1.2 m 掘れた」は鉛直の話で、40 度斜面の
   法面実厚は 1.007 m。**同じ現場の 2 つの数字は別の量**。
3. ★★**変化なしの対照が 83.8 m3 の偽の土量を出す**。同じ地形を 2 回撮って
   引くだけで、偽掘削 83.8 m3 / 偽堆積 90.7 m3(真の掘削 164.2 m3 の 51 %)。
   雑音の正負を別々に足しているので、**正味 +6.9 m3 は小さいのに内訳は巨大**。
   有意性でしきると 18.1 / 18.7 m3 に落ちる —— しきい値は飾りではなく本体。
4. ★**M3C2 の利得は傾斜からしか来ない**。足跡面積を 1.00 m2 に揃えて比べると
   検出限界 LoD は 傾斜 0 度で DoD 0.061 m / M3C2 0.052 m と**ほぼ同じ**、
   40 度で 0.277 m / 0.082 m と **3.4 倍**の差。平面を当てる分だけ、セル内の
   傾斜(cell/sqrt12)と水平位置誤差の寄与が落ちる。
5. **点密度の崖**: 最小検出厚は 0.5 pt/m2 で 0.408 m(この崩壊の最大深さ
   1.20 m の 34 %)、16 pt/m2 で 0.112 m。★ただし M3C2 の LoD は低密度で
   **見かけ上よくなる** —— 円柱に点が足りない core を捨てるので、
   有効 core 率が 1 pt/m2 で 21.6 % まで落ちる**生存者バイアス**。
   「よく見える」のではなく「見えた所だけ数えている」。
6. ★★**系統誤差が生む偽体積は DoD も M3C2 も同じ**。0.30 m の平行移動に対し
   予測 540.5 m3、実測 DoD 540.4 / M3C2 545.3 m3。M3C2 が有利なのは厚さと
   有意性であって体積ではない(法線方向の見かけ変化は cos 倍小さいが、
   体積に直すとき 1/cos するので約分する)。
7. ★★**合わせた分だけ変化が消える**。変化のある点群対をそのまま ICP に掛けると
   正味土量は -30.4 → -0.9 m3(真値の 3 %)に潰れる。変化域が窓の 33 % もあると
   ICP はそれを系統誤差と読む。上位 60 % だけ使う trimmed ICP で -25.6 m3 まで戻る。
8. ★★**位置合わせで決まらない成分は、測定にも現れない**。斜面に沿った
   0.29 m の面内ずれを与えると、純平面では ICP 後も点は 0.243 m ずれたまま
   なのに DoD の偽正味は 0.6 m3。同じずれをうねりのある地形に与えると
   ICP は 0.011 m まで詰める。**測れない形は合わせられない形と同じ**。
9. ★**法線の符号は道具では決まらない**。``estimate_normals`` は「近傍重心から
   離れる側」に揃えるので、開いた斜面では 50.7 % が下向きを向く。
   ``estimate_oriented_normals`` は大域的に一貫させる(実測は 100 % 上向き)が、
   一貫させるだけで**符号そのものは種の取り方次第**。法線方向に測る手法は、
   符号を自分で決めないと掘削と堆積が入れ替わる。

【グラウンドトゥルース】
地面は**閉形式**(傾斜 θ の平面 + 2 波のうねり)、変化は**鉛直変位場**
d(x,y) = 2 つのガウス(掘削 +、堆積 -)。1 個ぶんの土量は解析積分
2 pi D sx sy で厳密(掘削 165.876 / 堆積 135.717 m3)。**ただし 2 つを足すと
互いの裾が符号を打ち消す**ので、真値は解析窓での数値積分(掘削 164.154 /
堆積 133.726 m3)を使う —— 解析式との 1.0 % / 1.5 % の差はこの重なりと窓の端。
観測は上空からの点群として合成: 密度 [pt/m2]、鉛直測距雑音、水平位置雑音、
GNSS/IMU 由来の剛体系統誤差、樹冠による地表遮蔽、そして 2 時期で点は
**対応しない**。幾何だけを見たい節では格子標本 + 雑音ゼロに切り替える。

来歴(公開文献のみ): Lague, Brodu & Leroux, *ISPRS J. Photogramm.* 82 (2013) 10
—— M3C2 / Wheaton et al., *Earth Surf. Process. Landforms* 35 (2010) 136 ——
DoD の空間可変 LoD / Brasington et al., *Geomorphology* 53 (2003) 299 ——
DEM 差分の体積不確かさ / Besl & McKay, *IEEE TPAMI* 14 (1992) 239 —— ICP。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
LX = LY = 60.0             # 調査区画 [m]
MARGIN = 4.0               # 解析窓の余白 [m](端の平面当てはめを避ける)
WIN = (MARGIN, LX - MARGIN)
WIN_AREA = (LX - 2 * MARGIN) ** 2      # 解析窓の水平投影面積 [m2]

SLOPE = 25.0               # 既定の斜面傾斜 [deg]
UNDUL = 0.35               # うねりの振幅 [m]
DENSITY = 8.0              # 点密度 [pt/m2]
LAT_DENSITY = 9.0          # 幾何だけを見る節の格子標本(1 セルにちょうど 3x3 点)
SIG_R = 0.05               # 鉛直測距雑音 sigma [m]
SIG_H = 0.10               # 水平位置雑音 sigma [m](★斜面ではこれが tan θ 倍で効く)
OCCL = 0.30                # 樹冠で地表に届かない確率
SEED = 7

CELL = 1.0                 # DEM のセル [m]
CORE = 1.0                 # M3C2 の core point 間隔 [m](DoD と同じ格子にする)
R_NORM = 2.0               # 局所平面を当てる水平半径 [m]
#: M3C2 の円柱半径。**DEM セルと足跡面積を合わせる**(pi r^2 = CELL^2)——
#: 揃えないと「M3C2 のほうが良い」が単に「窓が大きい」の言い換えになる。
R_CYL = CELL / math.sqrt(math.pi)
MAX_HALF = 2.0             # 円柱の長さの半分 [m]
MIN_FIT, MIN_CYL = 8, 4    # 平面当てはめ / 円柱内の最小点数

TAU = 0.05                 # 真の「変化あり」の定義 [m](これ未満は変化と呼ばない)

#: 掘削(scar)と堆積(lobe)。``amp`` は**鉛直**変位 [m]、正 = 地面が下がる。
#: 1 個ぶんの体積は解析積分 2 pi |amp| sx sy。3 sigma が解析窓に収まる位置に置く。
SCAR = {"x": 20.0, "y": 37.0, "sx": 4.0, "sy": 5.5, "amp": +1.20}
LOBE = {"x": 36.0, "y": 17.0, "sx": 6.0, "sy": 4.5, "amp": -0.80}

V_ERO_EXACT = 2 * math.pi * abs(SCAR["amp"]) * SCAR["sx"] * SCAR["sy"]
V_DEP_EXACT = 2 * math.pi * abs(LOBE["amp"]) * LOBE["sx"] * LOBE["sy"]
A_ERO_EXACT = 2 * math.pi * SCAR["sx"] * SCAR["sy"] * math.log(abs(SCAR["amp"]) / TAU)
A_DEP_EXACT = 2 * math.pi * LOBE["sx"] * LOBE["sy"] * math.log(abs(LOBE["amp"]) / TAU)


def _make_trees(n: int = 80, seed: int = 11) -> np.ndarray:
    """樹木(円形の樹冠)の一覧 ``(cx, cy, R, H)``。場面ごとに変わらない。"""
    rng = np.random.default_rng(seed)
    return np.column_stack([rng.uniform(0, LX, n), rng.uniform(0, LY, n),
                            rng.uniform(2.0, 4.0, n), rng.uniform(3.0, 9.0, n)])


TREES = _make_trees()


# --------------------------------------------------------------------------- #
# 場面 —— すべて閉形式                                                          #
# --------------------------------------------------------------------------- #
def surface(x, y, slope_deg: float = SLOPE, undul: float = UNDUL):
    """地面の標高 [m]。傾斜 ``slope_deg`` の平面 + 2 波のうねり。y が増える向きに下る。"""
    z = -math.tan(math.radians(slope_deg)) * y
    if undul:
        z = z + undul * (np.sin(2 * np.pi * x / 23.0 + 0.7) * np.cos(2 * np.pi * y / 31.0)
                         + 0.6 * np.sin(2 * np.pi * (x + y) / 17.0))
    return z


def change(x, y):
    """時期 1 -> 2 の**鉛直**変位場 d [m](正 = 地面が下がる = 掘削)。"""
    d = np.zeros_like(np.asarray(x, np.float64))
    for p in (SCAR, LOBE):
        d = d + p["amp"] * np.exp(-((x - p["x"]) ** 2 / (2 * p["sx"] ** 2)
                                    + (y - p["y"]) ** 2 / (2 * p["sy"] ** 2)))
    return d


def canopy(x, y):
    """樹冠に入っているか、そのときの樹冠高 [m](地面からの高さ)。"""
    top = np.zeros_like(x)
    inside = np.zeros(np.shape(x), bool)
    for cx, cy, r, h in TREES:
        r2 = (x - cx) ** 2 + (y - cy) ** 2
        m = r2 < r * r
        if not m.any():
            continue
        top[m] = np.maximum(top[m], h * np.sqrt(np.maximum(0.0, 1.0 - r2[m] / (r * r))))
        inside |= m
    return inside, top


def apply_pose(pts: np.ndarray, shift, rot_deg: float = 0.0) -> np.ndarray:
    """GNSS/IMU 由来の剛体系統誤差(重心まわりの微小回転 + 平行移動)。"""
    shift = np.asarray(shift, float)
    if not shift.any() and rot_deg == 0.0:
        return pts
    a = math.radians(rot_deg)
    rot = np.array([[1.0, 0.0, 0.0],
                    [0.0, math.cos(a), -math.sin(a)],
                    [0.0, math.sin(a), math.cos(a)]])
    c = pts.mean(axis=0)
    return (pts - c) @ rot.T + c + shift


def make_cloud(rng, slope_deg=SLOPE, density=DENSITY, with_change=True,
               occl=OCCL, shift=(0.0, 0.0, 0.0), rot_deg=0.0,
               sig_r=SIG_R, sig_h=SIG_H, undul=UNDUL, lattice=False):
    """上空からの点群を合成。返り値 ``(記録座標 (N,3), 地面点フラグ (N,))``。

    ★標高は**真の水平位置**で評価し、記録するのは**誤差の乗った水平位置**。
    これが斜面で ``tan θ * sigma_h`` の見かけ標高誤差を生む —— 逆にすると
    水平位置誤差が標高に一切効かなくなり、この PoC の主要な崖が消える。

    ``lattice=True`` は**格子標本**(両時期で同じ水平位置)。幾何だけを見る節で
    標本の食い違いを止めるために使う。
    """
    if lattice:
        k = int(round(math.sqrt(density)))
        c = (np.arange(int(LX * k)) + 0.5) / k
        x, y = (v.ravel() for v in np.meshgrid(c, c))
    else:
        n = int(density * LX * LY)
        x = rng.uniform(0.0, LX, n)
        y = rng.uniform(0.0, LY, n)
    n = x.size
    z = surface(x, y, slope_deg, undul)
    if with_change:
        z = z - change(x, y)
    ground = np.ones(n, bool)
    if occl > 0.0:
        inside, top = canopy(x, y)
        blocked = inside & (rng.random(n) < occl)
        z = np.where(blocked, z + top + 0.15 * rng.standard_normal(n), z)
        ground = ~blocked
    if sig_r:
        z = z + sig_r * rng.standard_normal(n)
    if sig_h:
        x = x + sig_h * rng.standard_normal(n)
        y = y + sig_h * rng.standard_normal(n)
    return apply_pose(np.column_stack([x, y, z]), shift, rot_deg), ground


# --------------------------------------------------------------------------- #
# 地面点の分類 —— 斜面では「セル内最低点 + 許容幅」は先に傾きを抜かないと壊れる  #
# --------------------------------------------------------------------------- #
def ground_filter(pts: np.ndarray, tol: float = 0.35, detrend: bool = True,
                  win: int = 1):
    """粗い地面分類。``detrend`` で RANSAC 平面を抜いてからセル内最低点を取る。

    ``win`` は最低点を探す窓の**セル数**(既定 1 = 自分のセルだけ)。
    ★``win=1`` は「そのセルの点が全部樹冠」のとき無力 —— 樹冠の底が
    そのセルの最低点になり、まるごと地面として通ってしまう。``win=3`` なら
    隣のセルの地面と比べるので、丸ごと遮蔽されたセルは**空になる**
    (= 測れなかったと分かる)。
    """
    if detrend:
        step = max(1, len(pts) // 4000)
        params, _, _ = fs.ledger.ransac_plane(pts[::step], thresh=1.0, iters=200, seed=0)
        nrm = np.asarray(params["normal"], float)
        resid = pts @ nrm + float(params["d"])
        if nrm[2] < 0:
            resid = -resid
    else:
        resid = pts[:, 2].copy()
    ix = np.floor(pts[:, 0] / CELL).astype(np.int64)
    iy = np.floor(pts[:, 1] / CELL).astype(np.int64)
    ix -= ix.min()
    iy -= iy.min()
    nx, ny = int(ix.max()) + 1, int(iy.max()) + 1
    flat = ix * ny + iy
    lo = np.full(nx * ny, np.inf)
    np.minimum.at(lo, flat, resid)
    if win > 1:
        from scipy import ndimage
        big = np.where(np.isfinite(lo), lo, 1e9).reshape(nx, ny)
        lo = ndimage.minimum_filter(big, size=win, mode="nearest").ravel()
    return resid - lo[flat] < tol


# --------------------------------------------------------------------------- #
# ゼロ点: DoD(格子の標高図を引き算)                                           #
# --------------------------------------------------------------------------- #
def dem(pts: np.ndarray, stat: str = "mean") -> tuple[np.ndarray, np.ndarray]:
    """点群 -> セル代表値の標高図 (ny,nx) と点数。空セルは NaN。行 0 が y 最小。

    ``stat="median"`` は**セル中央値**。樹冠の取りこぼしのように 1 セルに数点だけ
    数 m 高い点が混ざる汚染に強い(平均は 1 点で数 m 動く)。
    """
    nx = ny = int(round(LX / CELL))
    ix = np.floor(pts[:, 0] / CELL).astype(np.int64)
    iy = np.floor(pts[:, 1] / CELL).astype(np.int64)
    ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    flat = iy[ok] * nx + ix[ok]
    cnt = np.bincount(flat, minlength=nx * ny).astype(np.float64)
    if stat == "median":
        from scipy import ndimage
        z = np.full(nx * ny, np.nan)
        lab = np.nonzero(cnt > 0)[0]
        if lab.size:
            z[lab] = ndimage.median(pts[ok, 2], labels=flat, index=lab)
    else:
        ssum = np.bincount(flat, weights=pts[ok, 2], minlength=nx * ny)
        with np.errstate(invalid="ignore", divide="ignore"):
            z = np.where(cnt > 0, ssum / np.maximum(cnt, 1), np.nan)
    return z.reshape(ny, nx), cnt.reshape(ny, nx)


def window_mask(nx: int) -> np.ndarray:
    """解析窓(端から MARGIN)のセル。"""
    c = (np.arange(nx) + 0.5) * CELL
    inside = (c >= WIN[0]) & (c <= WIN[1])
    return inside[:, None] & inside[None, :]


def dod(p1: np.ndarray, p2: np.ndarray, lod: float = 0.0, stat: str = "mean") -> dict:
    """DoD。``lod`` 以下の差は 0 に落として(有意性でしきって)土量を積む。"""
    z1, _ = dem(p1, stat)
    z2, _ = dem(p2, stat)
    dz = z2 - z1
    win = window_mask(z1.shape[1])
    ok = np.isfinite(dz) & win
    sig = ok & (np.abs(dz) > lod)
    val = np.where(sig, dz, 0.0)
    a = CELL * CELL
    return {"dz": np.where(ok, dz, np.nan),
            "ero": float(-val[val < 0].sum() * a),
            "dep": float(val[val > 0].sum() * a),
            "net": float(val.sum() * a),
            "abs": float(np.abs(val).sum() * a),
            "area": float(sig.sum() * a),
            "empty": int((~np.isfinite(dz) & win).sum()),
            "sig": sig, "ok": ok}


# --------------------------------------------------------------------------- #
# M3C2: 局所平面の法線方向に測る                                                #
# --------------------------------------------------------------------------- #
def core_grid() -> np.ndarray:
    """core point の水平位置(DoD のセル中心と同じ)。"""
    c = (np.arange(int(round(LX / CELL))) + 0.5) * CELL
    c = c[(c >= WIN[0]) & (c <= WIN[1])]
    xx, yy = np.meshgrid(c, c)
    return np.column_stack([xx.ravel(), yy.ravel()])


def m3c2(p1: np.ndarray, p2: np.ndarray, cores: np.ndarray | None = None) -> dict:
    """M3C2 —— 時期 1 で局所平面を当て、その法線方向に平均位置の差を測る。

    返り値の ``L`` は法線方向の距離 [m](正 = 法線の向き = 上向き = 堆積)、
    ``nz`` は法線の鉛直成分 = cos(局所傾斜)、``sigma`` は L の標準誤差。
    """
    cores = core_grid() if cores is None else cores
    tree2d = cKDTree(p1[:, :2])
    t1, t2 = cKDTree(p1), cKDTree(p2)
    nb = tree2d.query_ball_point(cores, R_NORM, workers=-1)

    m = len(cores)
    cen = np.zeros((m, 3))
    nor = np.zeros((m, 3))
    nor[:, 2] = 1.0
    good = np.zeros(m, bool)
    for i, idx in enumerate(nb):
        if len(idx) < MIN_FIT:
            continue
        c, nvec, _ = fs.ledger.fit_plane_3d(p1[idx])
        nvec = np.asarray(nvec, float)
        if nvec[2] < 0:                       # ★符号は任意 —— 上向きに固定する
            nvec = -nvec
        cen[i], nor[i], good[i] = np.asarray(c, float), nvec, True

    rq = math.hypot(R_CYL, MAX_HALF)
    b1 = t1.query_ball_point(cen, rq, workers=-1)
    b2 = t2.query_ball_point(cen, rq, workers=-1)
    ll = np.full(m, np.nan)
    sg = np.full(m, np.nan)
    for i in range(m):
        if not good[i]:
            continue
        stats = []
        for pts, ball in ((p1, b1[i]), (p2, b2[i])):
            if len(ball) < MIN_CYL:
                stats = []
                break
            v = pts[ball] - cen[i]
            t = v @ nor[i]
            perp2 = np.einsum("ij,ij->i", v, v) - t * t
            sel = (perp2 < R_CYL * R_CYL) & (np.abs(t) < MAX_HALF)
            if int(sel.sum()) < MIN_CYL:
                stats = []
                break
            tt = t[sel]
            stats.append((float(tt.mean()), float(tt.std(ddof=1)), int(tt.size)))
        if len(stats) != 2:
            good[i] = False
            continue
        ll[i] = stats[1][0] - stats[0][0]
        sg[i] = math.sqrt(stats[0][1] ** 2 / stats[0][2] + stats[1][1] ** 2 / stats[1][2])
    return {"L": ll, "sigma": sg, "nz": nor[:, 2], "ok": good, "cores": cores,
            "rate": float(good.mean())}


def m3c2_volume(res: dict, lod: float | None = None, conf: float = 1.96) -> dict:
    """法線方向の距離 -> 土量。**斜面の面積 = 水平面積 / cos** で積む。

    ``lod=None`` なら core ごとの sigma から有意性判定(M3C2 の本来の使い方)、
    数値を渡せば一律しきい値、``0.0`` ならしきらない。
    """
    ok = res["ok"] & np.isfinite(res["L"])
    lim = (conf * res["sigma"]) if lod is None else np.full(res["L"].shape, float(lod))
    sig = ok & (np.abs(res["L"]) > lim)
    val = np.where(sig, res["L"], 0.0)
    nz = np.where(res["nz"] > 1e-6, res["nz"], 1.0)
    vol = val * (CORE * CORE / nz)             # ★水平セルが覆う斜面上の面積
    # ★測れなかった core の面積は土量に一切入らない。有効率で割り戻した値も返す
    #   —— 割り戻さないと「静かに欠けた土量」を正しい値だと思ってしまう。
    rate = max(res["rate"], 1e-9)
    return {"ero": float(-vol[val < 0].sum()), "dep": float(vol[val > 0].sum()),
            "net": float(vol.sum()), "abs": float(np.abs(vol).sum()),
            "net_cov": float(vol.sum() / rate), "ero_cov": float(-vol[val < 0].sum() / rate),
            "area": float(sig.sum() * CORE * CORE),
            "naive": float(np.abs(val * CORE * CORE)[val < 0].sum()),
            "sig": sig, "n_ok": int(ok.sum()), "rate": res["rate"]}


def spread(v: np.ndarray) -> float:
    """有限値だけの標準偏差(空なら NaN)。低密度で core が全滅する場合がある。"""
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    return float(np.std(v)) if v.size > 1 else float("nan")


def robust_spread(v: np.ndarray) -> float:
    """外れ値に強い散らばり(1.4826 x MAD)。正規分布なら標準偏差と一致する。

    ★樹冠の取りこぼしのように**数十点だけ数 m ずれる**汚染があると、標準偏差は
    その少数に引きずられて桁で飛ぶ。LoD をそれで決めると、しきい値が現実離れする。
    """
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if v.size < 2:
        return float("nan")
    return float(1.4826 * np.median(np.abs(v - np.median(v))))


# --------------------------------------------------------------------------- #
# 真値(解析窓の中で数値積分)                                                   #
# --------------------------------------------------------------------------- #
def truth(lod: float = 0.0, step: float = 0.25) -> dict:
    """解析窓での真の土量・面積。``lod`` を渡すとその厚さ以下を切り落とした真値。"""
    c = np.arange(WIN[0] + step / 2, WIN[1], step)
    xx, yy = np.meshgrid(c, c)
    d = change(xx, yy)
    d = np.where(np.abs(d) > lod, d, 0.0)
    a = step * step
    return {"ero": float(d[d > 0].sum() * a), "dep": float(-d[d < 0].sum() * a),
            "net": float(-d.sum() * a),
            "area": float((np.abs(d) > max(lod, TAU)).sum() * a)}


# --------------------------------------------------------------------------- #
# 予測式                                                                        #
# --------------------------------------------------------------------------- #
def pred_sigma_dod(slope_deg: float, density: float) -> float:
    """DoD の 1 セルあたり差分標準偏差 [m]。

    セル内で z ~ zbar + g*(y-yc)。分散は g^2 (cell^2/12 + sigma_h^2) + sigma_r^2、
    n = 密度 * cell^2 点の平均で 1/n、2 時期ぶんで 2 倍。
    """
    g = math.tan(math.radians(slope_deg))
    inner = SIG_R ** 2 + g * g * (CELL ** 2 / 12.0 + SIG_H ** 2)
    return math.sqrt(2.0 / (density * CELL * CELL) * inner)


def pred_sigma_m3c2(slope_deg: float, density: float) -> float:
    """M3C2 の core あたり標準偏差 [m]。平面を当てるのでセル内傾斜の項が消える。"""
    th = math.radians(slope_deg)
    inner = (math.cos(th) * SIG_R) ** 2 + (math.sin(th) * SIG_H) ** 2
    return math.sqrt(2.0 / (density * math.pi * R_CYL ** 2) * inner)


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                 #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— 何を仕込んだか")
    print("=" * 78)
    tr = truth()
    print("  区画 %.0f x %.0f m / 解析窓 %.0f x %.0f m(水平投影面積 %.0f m2)"
          % (LX, LY, LX - 2 * MARGIN, LY - 2 * MARGIN, WIN_AREA))
    print("  掘削(scar): 鉛直 %.2f m, sigma %.1f x %.1f m -> 単独なら %.3f m3(解析式)"
          % (SCAR["amp"], SCAR["sx"], SCAR["sy"], V_ERO_EXACT))
    print("  堆積(lobe): 鉛直 %.2f m, sigma %.1f x %.1f m -> 単独なら %.3f m3(解析式)"
          % (-LOBE["amp"], LOBE["sx"], LOBE["sy"], V_DEP_EXACT))
    print("  ★真値は**解析窓での数値積分**を使う: 掘削 %.3f / 堆積 %.3f m3"
          % (tr["ero"], tr["dep"]))
    print("     解析式より %.2f %% / %.2f %% 小さいのは、2 つのガウスの**裾が符号を"
          "打ち消す**ため" % (100 * (1 - tr["ero"] / V_ERO_EXACT),
                              100 * (1 - tr["dep"] / V_DEP_EXACT)))
    print("     (中間点で掘削 +0.031 m と堆積 -0.028 m が同じ桁で重なる)+ 窓の端の"
          "切り落とし。1 個ずつの解析式をそのまま真値にすると 1 % 嘘をつく。")
    print("  変化ありの真の面積(|d| >= %.2f m): %.1f m2(窓の %.1f %%)。"
          "解析式 %.1f + %.1f = %.1f m2"
          % (TAU, tr["area"], 100 * tr["area"] / WIN_AREA,
             A_ERO_EXACT, A_DEP_EXACT, A_ERO_EXACT + A_DEP_EXACT))

    rng = np.random.default_rng(SEED)
    p1, g1 = make_cloud(rng, occl=OCCL)
    fine = np.linspace(0, LX, 601)
    xx, yy = np.meshgrid(fine, fine)
    cover = float(canopy(xx, yy)[0].mean())
    print("\n  点群: 密度 %.1f pt/m2 -> %d 点/時期。樹冠被覆 %.1f %%、"
          "遮蔽確率 %.2f -> 地面点 %.1f %%"
          % (DENSITY, len(p1), 100 * cover, OCCL, 100 * g1.mean()))
    print("  測距雑音 sigma_r %.3f m / 水平位置雑音 sigma_h %.3f m / うねり振幅 %.2f m"
          % (SIG_R, SIG_H, UNDUL))

    print("\n  地面分類(セル内最低点 + 許容 0.35 m)—— 先に傾きを抜くかどうか:")
    print("    傾斜   傾き抜きあり: 地面の再現率 / 樹冠の混入   傾き抜きなし: 再現率")
    rows = []
    for sl in (0.0, 25.0, 40.0):
        r2 = np.random.default_rng(SEED + 1)
        q, gq = make_cloud(r2, slope_deg=sl)
        k1 = ground_filter(q, detrend=True)
        k0 = ground_filter(q, detrend=False)
        rows.append((sl, float((k1 & gq).sum() / gq.sum()),
                     float((k1 & ~gq).sum() / max(int(k1.sum()), 1)),
                     float((k0 & gq).sum() / gq.sum())))
        print("    %4.0f deg      %6.1f %% / %5.1f %%                    %6.1f %%"
              % (sl, 100 * rows[-1][1], 100 * rows[-1][2], 100 * rows[-1][3]))
    print("  ★傾き抜きなしは %.0f 度で再現率 %.1f %% —— セル内最低点は"
          "**斜面ではそもそも地面を落とす**" % (rows[-1][0], 100 * rows[-1][3]))
    print("     (セルを横切る標高差 tan%.0f x %.1f m = %.2f m が許容幅 0.35 m を超えるため)。"
          % (rows[-1][0], CELL, math.tan(math.radians(rows[-1][0])) * CELL))
    return {"truth": tr, "ground_rows": rows, "cover": cover}


# --------------------------------------------------------------------------- #
# 2. ゼロ点 = DoD。式を先に出してから、雑音を止めて幾何だけ見る                  #
# --------------------------------------------------------------------------- #
def section_geometry(tr: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 = DoD(格子の引き算)—— 先に式を出し、雑音を止めて確かめる")
    print("=" * 78)
    print("  素朴な予想: 「斜面では面が cos θ だけ縮んで見えるので体積も cos θ 倍に間違う」。")
    print("  実際に立つ式: 法線厚さ t の層を剥がすと鉛直変位は dz = t / cos θ、")
    print("    水平投影面積 A_h = A_slope cos θ。DoD は dz を A_h で積むので")
    print("    V = (t / cos θ) x A_slope cos θ = t A_slope。**cos が約分して消える**。")
    print("  -> 予測: 傾斜を変えても DoD の体積は正しい。間違うのは「深さ」のほう。")
    print("\n  雑音・遮蔽・系統誤差をすべて止め、両時期で**同じ格子標本**"
          "(%.0f pt/m2 = 1 セルに 3x3 点)にして幾何だけを見る:" % LAT_DENSITY)
    print("\n   傾斜   DoD 掘削 [m3]  誤差%   DoD 堆積 [m3]  誤差%   "
          "M3C2 掘削 [m3] 誤差%   M3C2 堆積 誤差%")
    sl_l, ero_e, dep_e, mero_e, mdep_e, rows = [], [], [], [], [], []
    for sl in (0.0, 5.0, 10.0, 20.0, 30.0, 40.0):
        rng = np.random.default_rng(SEED)
        a, _ = make_cloud(rng, slope_deg=sl, density=LAT_DENSITY, with_change=False,
                          occl=0.0, sig_r=0.0, sig_h=0.0, lattice=True)
        b, _ = make_cloud(rng, slope_deg=sl, density=LAT_DENSITY, with_change=True,
                          occl=0.0, sig_r=0.0, sig_h=0.0, lattice=True)
        rd = dod(a, b)
        vm = m3c2_volume(m3c2(a, b), lod=0.0)
        e1 = 100 * (rd["ero"] / tr["ero"] - 1)
        e2 = 100 * (rd["dep"] / tr["dep"] - 1)
        e3 = 100 * (vm["ero"] / tr["ero"] - 1)
        e4 = 100 * (vm["dep"] / tr["dep"] - 1)
        sl_l.append(sl)
        ero_e.append(e1)
        dep_e.append(e2)
        mero_e.append(e3)
        mdep_e.append(e4)
        rows.append(["%.0f" % sl, "%.3f" % rd["ero"], "%+.2f" % e1,
                     "%.3f" % rd["dep"], "%+.2f" % e2,
                     "%.3f" % vm["ero"], "%+.2f" % e3, "%+.2f" % e4])
        print("   %4.0f %13.3f %+7.2f %14.3f %+7.2f %14.3f %+7.2f %12.2f"
              % (sl, rd["ero"], e1, rd["dep"], e2, vm["ero"], e3, e4))
    print("\n  ★★予測どおり **体積は傾斜に依らない**: DoD の掘削誤差は "
          "%+.2f %% 〜 %+.2f %%(傾向なし)。" % (min(ero_e), max(ero_e)))
    print("     素朴な予想「cos40 = %.3f 倍に縮む」= %.1f %% は**外れ**。cos は約分して消える。"
          % (math.cos(math.radians(40)), -100 * (1 - math.cos(math.radians(40)))))
    print("  ★M3C2 も同じ範囲(%+.2f 〜 %+.2f %%)。**1/cos(局所傾斜)を掛けて"
          "斜面上の面積で積めば**、法線方向に測っても同じ体積になる。"
          % (min(mero_e), max(mero_e)))
    figs.save_table("geometry",
                    ["傾斜 deg", "DoD 掘削 m3", "誤差 %", "DoD 堆積 m3", "誤差 %",
                     "M3C2 掘削 m3", "誤差 %", "M3C2 堆積 誤差 %"], rows,
                    title="雑音を止めた幾何だけの比較(真値 掘削 %.3f / 堆積 %.3f m3)"
                          % (tr["ero"], tr["dep"]),
                    caption="傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。"
                            "cos は積分で約分する。")
    return {"slope": sl_l, "ero_err": ero_e, "dep_err": dep_e, "m_ero_err": mero_e}


# --------------------------------------------------------------------------- #
# 3. 雑音を入れる -> 対照群 = 変化なしで出てしまう土量                          #
# --------------------------------------------------------------------------- #
def section_control(tr: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) ★★雑音を入れる —— 「変化なし」で出てしまう偽の土量(= 検出限界そのもの)")
    print("=" * 78)
    rng = np.random.default_rng(SEED)
    p1, _ = make_cloud(rng, with_change=False, occl=0.0)
    p2, _ = make_cloud(rng, with_change=True, occl=0.0)
    real = dod(p1, p2)
    print("  まず本物の変化を、現実的な観測(%.1f pt/m2・雑音あり・対応なし)で測る:"
          % DENSITY)
    print("    掘削 %8.3f m3(真 %8.3f、%+.1f %%)  堆積 %8.3f m3(真 %8.3f、%+.1f %%)"
          % (real["ero"], tr["ero"], 100 * (real["ero"] / tr["ero"] - 1),
             real["dep"], tr["dep"], 100 * (real["dep"] / tr["dep"] - 1)))
    print("    しきい値なしの変化面積 %.0f m2(真値 %.0f m2)= 窓のほぼ全部。"
          % (real["area"], tr["area"]))

    print("\n   対照群                           偽掘削   偽堆積   偽正味  偽変化面積")
    rows, out = [], {}
    conds = (("変化なし・遮蔽なし・誤差なし", dict(occl=0.0, shift=(0, 0, 0))),
             ("変化なし・遮蔽 30 %", dict(occl=OCCL, shift=(0, 0, 0))),
             ("変化なし・系統誤差 0.10 m", dict(occl=0.0, shift=(0.06, 0.08, 0.02))),
             ("変化なし・遮蔽 + 系統誤差", dict(occl=OCCL, shift=(0.06, 0.08, 0.02))))
    for name, kw in conds:
        r0 = np.random.default_rng(SEED + 5)
        a, _ = make_cloud(r0, with_change=False, **kw)
        b, _ = make_cloud(r0, with_change=False, **kw)
        if kw["occl"] > 0:
            a, b = a[ground_filter(a)], b[ground_filter(b)]
        r = dod(a, b)
        out[name] = r
        rows.append([name, "%.1f" % r["ero"], "%.1f" % r["dep"],
                     "%+.1f" % r["net"], "%.0f" % r["area"]])
        print("   %-30s %8.1f %8.1f %8.1f %8.0f"
              % (name, r["ero"], r["dep"], r["net"], r["area"]))

    base = out["変化なし・遮蔽なし・誤差なし"]
    print("\n  ★★何も変わっていないのに偽掘削 %.1f m3 / 偽堆積 %.1f m3 が出る"
          "(真の掘削 %.1f m3 の %.0f %%)。"
          % (base["ero"], base["dep"], tr["ero"], 100 * base["ero"] / tr["ero"]))
    print("     偽正味は %+.1f m3 と小さい —— **正味だけ見ていると内訳の嘘に気づけない**。"
          % base["net"])
    lod = 1.96 * pred_sigma_dod(SLOPE, DENSITY)
    r0 = np.random.default_rng(SEED + 5)
    ca, _ = make_cloud(r0, with_change=False, occl=0.0, shift=(0, 0, 0))
    cb, _ = make_cloud(r0, with_change=False, occl=0.0, shift=(0, 0, 0))
    thr = dod(ca, cb, lod=lod)
    real_thr = dod(p1, p2, lod=lod)
    tr_thr = truth(lod=lod)
    print("     有意性でしきる(LoD95 = 1.96 sigma = %.3f m): 偽掘削 %.1f / 偽堆積 %.1f m3、"
          "偽変化面積 %.0f m2。" % (lod, thr["ero"], thr["dep"], thr["area"]))
    print("     -> **しきい値は飾りではなく本体**。しきらない DoD は現場で使えない。")
    print("  ★ただししきると本物の縁も落ちる: 同じ LoD での本物は 掘削 %.1f m3。"
          % real_thr["ero"])
    print("     しきい値以上の真値 %.1f m3 と比べれば %+.1f %% で合う —— "
          "落ちた %.1f m3 は測定の失敗ではなく**しきい値の定義**。"
          % (tr_thr["ero"], 100 * (real_thr["ero"] / tr_thr["ero"] - 1),
             tr["ero"] - tr_thr["ero"]))
    figs.save_table("controls",
                    ["条件", "偽掘削 m3", "偽堆積 m3", "偽正味 m3", "偽変化面積 m2"],
                    rows + [["変化なし・誤差なし + LoD %.3f m でしきる" % lod,
                             "%.1f" % thr["ero"], "%.1f" % thr["dep"],
                             "%+.1f" % thr["net"], "%.0f" % thr["area"]]],
                    title="対照群: 変化が無いのに出てしまう土量",
                    caption="真の掘削は %.1f m3。しきらない DoD の内訳は"
                            "その半分近くを雑音から作る。" % tr["ero"])
    return {"base": base, "thr": thr, "lod": lod, "all": out,
            "real": real, "real_thr": real_thr, "tr_thr": tr_thr,
            "p1": p1, "p2": p2}


# --------------------------------------------------------------------------- #
# 4. M3C2 —— 法線方向に測る                                                     #
# --------------------------------------------------------------------------- #
def section_m3c2(ctrl: dict, tr: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) M3C2(局所平面の法線方向に測る)—— 厚さと体積は別の量")
    print("=" * 78)
    p1, p2 = ctrl["p1"], ctrl["p2"]
    t0 = time.perf_counter()
    res = m3c2(p1, p2)
    raw = m3c2_volume(res, lod=0.0)
    sig = m3c2_volume(res, lod=None)
    print("  core %d 点(間隔 %.1f m)、うち有効 %d(%.1f %%)。円柱半径 %.3f m"
          "(足跡 %.2f m2 = DEM セル %.2f m2 と一致)、%.2f 秒"
          % (len(res["cores"]), CORE, raw["n_ok"], 100 * res["rate"], R_CYL,
             math.pi * R_CYL ** 2, CELL * CELL, time.perf_counter() - t0))
    print("\n  しきらない土量: 掘削 %8.3f(真 %8.3f、%+.1f %%)  堆積 %8.3f(真 %8.3f、%+.1f %%)"
          % (raw["ero"], tr["ero"], 100 * (raw["ero"] / tr["ero"] - 1),
             raw["dep"], tr["dep"], 100 * (raw["dep"] / tr["dep"] - 1)))
    print("     ★DoD の同条件 %.1f / %.1f m3 に比べて内訳の水増しが小さい"
          "(足跡は同じ %.2f m2 なのに、平面を当てるぶん 1 core の sigma が小さい)。"
          % (ctrl["real"]["ero"], ctrl["real"]["dep"], math.pi * R_CYL ** 2))
    # ★真値に近い数字が「正しい」とは限らない —— 逆向きの 2 つの誤差を分けて数える
    r0 = np.random.default_rng(SEED + 13)
    ca, _ = make_cloud(r0, with_change=False, occl=0.0)
    cb, _ = make_cloud(r0, with_change=False, occl=0.0)
    false_ero = m3c2_volume(m3c2(ca, cb), lod=0.0)["ero"]
    print("  ★★この %+.1f %% を「よく合っている」と読んではいけない。"
          "**逆向きの 2 つが効いている**:" % (100 * (raw["ero"] / tr["ero"] - 1)))
    print("     (i) 測れなかった core %.1f %% —— その面積の土量は一度も足されない(被覆の欠け)"
          % (100 * (1 - res["rate"])))
    print("     (ii) 雑音の水増し —— 変化なしの対照で偽掘削 %+.1f m3 が出る" % false_ero)
    print("     有効率で割り戻すと %.1f m3(%+.1f %%)。**生値が真値に近かったのは偶然**で、"
          % (raw["ero_cov"], 100 * (raw["ero_cov"] / tr["ero"] - 1)))
    print("     被覆と雑音を別々に報告しないと、打ち消し合った 1 個の数字が"
          "「正確」に見えてしまう。")
    print("  core ごとの sigma で有意性判定: 掘削 %8.3f  堆積 %8.3f  変化面積 %.0f m2(真 %.0f)"
          % (sig["ero"], sig["dep"], sig["area"], tr["area"]))
    print("  ★★体積に直すとき **1 / cos(局所傾斜)** を掛けるのを忘れると:")
    print("     掘削 %.3f m3(真値の %.1f %%)—— cos%.0f = %.3f そのぶん足りない。"
          "面積で割った「平均の厚さ」も同じだけ狂う。"
          % (raw["naive"], 100 * raw["naive"] / tr["ero"], SLOPE,
             math.cos(math.radians(SLOPE))))

    print("\n  ★崩壊中心での「深さ」: DoD は鉛直 dz、M3C2 は法線厚さ。比は sec θ のはず。")
    print("     傾斜   DoD 深さ [m]   M3C2 厚さ [m]     比     予測 sec θ   ずれ")
    ratios = []
    for sl in (0.0, 10.0, 25.0, 40.0):
        rng = np.random.default_rng(SEED + 2)
        a, _ = make_cloud(rng, slope_deg=sl, with_change=False, occl=0.0)
        b, _ = make_cloud(rng, slope_deg=sl, with_change=True, occl=0.0)
        rd = dod(a, b)
        rm = m3c2(a, b, cores=np.array([[SCAR["x"], SCAR["y"]]]))
        cx, cy = int(SCAR["x"] / CELL), int(SCAR["y"] / CELL)
        dz = float(np.nanmean(rd["dz"][cy - 1:cy + 2, cx - 1:cx + 2]))
        ln = float(rm["L"][0])
        sec = 1.0 / math.cos(math.radians(sl))
        ratios.append((sl, dz, ln, abs(dz / ln), sec))
        print("     %4.0f      %8.3f      %8.3f     %6.3f     %6.3f    %+.3f"
              % (sl, dz, ln, abs(dz / ln), sec, abs(dz / ln) - sec))
    err = max(abs(r[3] - r[4]) for r in ratios)
    print("  -> 予測と実測の差は最大 %.3f(1 セルぶんの雑音 %.3f m 相当)。"
          % (err, err * abs(ratios[-1][2])))
    print("     **「%.2f m 掘れた」は鉛直の話**で、40 度斜面の法面実厚は %.3f m。"
          "どちらを報告するかで %.0f %% 違う。"
          % (SCAR["amp"], abs(ratios[-1][2]),
             100 * (ratios[-1][4] - 1)))
    return {"res": res, "raw": raw, "sig": sig, "ratios": ratios}


# --------------------------------------------------------------------------- #
# 5. 崖(1) 傾斜 0 -> 40 度 —— 検出限界                                          #
# --------------------------------------------------------------------------- #
def section_slope() -> dict:
    print("\n" + "=" * 78)
    print("5) 崖(1) 傾斜 0 -> 40 度 —— 体積は崩れない。崩れるのは検出限界")
    print("=" * 78)
    print("  予測(変化ゼロの対照で測る 1 セルあたりの散らばり):")
    print("    DoD  : sqrt(2/n) sqrt(sigma_r^2 + tan^2 θ (cell^2/12 + sigma_h^2))")
    print("    M3C2 : sqrt(2/n) sqrt(cos^2 θ sigma_r^2 + sin^2 θ sigma_h^2)"
          "  ← 平面を当てるので cell^2/12 の項が消える")
    print("\n   傾斜   sigma_dz 実測/予測 [m]   sigma_L 実測/予測 [m]   "
          "LoD95 DoD / M3C2 [m]   比")
    sl_l, lod_d, lod_m, sd_m, sd_p, sm_m, sm_p, rows = [], [], [], [], [], [], [], []
    for sl in (0.0, 5.0, 10.0, 20.0, 30.0, 40.0):
        rng = np.random.default_rng(SEED + 4)
        a, _ = make_cloud(rng, slope_deg=sl, with_change=False, occl=0.0)
        b, _ = make_cloud(rng, slope_deg=sl, with_change=False, occl=0.0)
        rc = dod(a, b)
        mc = m3c2(a, b)
        s_d, s_m = spread(rc["dz"][rc["ok"]]), spread(mc["L"])
        sl_l.append(sl)
        sd_m.append(s_d)
        sd_p.append(pred_sigma_dod(sl, DENSITY))
        sm_m.append(s_m)
        sm_p.append(pred_sigma_m3c2(sl, DENSITY))
        lod_d.append(1.96 * s_d)
        lod_m.append(1.96 * s_m)
        rows.append(["%.0f" % sl, "%.4f / %.4f" % (s_d, sd_p[-1]),
                     "%.4f / %.4f" % (s_m, sm_p[-1]),
                     "%.3f / %.3f" % (lod_d[-1], lod_m[-1]),
                     "%.2f" % (lod_d[-1] / lod_m[-1])])
        print("   %4.0f      %8.4f / %.4f      %8.4f / %.4f      %.3f / %.3f      %.2f"
              % (sl, s_d, sd_p[-1], s_m, sm_p[-1], lod_d[-1], lod_m[-1],
                 lod_d[-1] / lod_m[-1]))
    print("\n  ★DoD の LoD は %.3f m(0 度)-> %.3f m(40 度)で %.1f 倍。"
          "予測式との比は %.2f 〜 %.2f 倍(うねりの分だけ実測が上)。"
          % (lod_d[0], lod_d[-1], lod_d[-1] / lod_d[0],
             min(m / p for m, p in zip(sd_m, sd_p)),
             max(m / p for m, p in zip(sd_m, sd_p))))
    print("  ★★M3C2 の利得は**傾斜からしか来ない**: LoD 比 DoD/M3C2 は "
          "0 度で %.2f、20 度で %.2f、40 度で %.2f。"
          % (lod_d[0] / lod_m[0], lod_d[3] / lod_m[3], lod_d[-1] / lod_m[-1]))
    print("     平地では落ちる項が無いので**同じ**。「M3C2 は常に良い」は嘘で、"
          "良いのは斜面と粗い面だけ。")
    figs.save_plot("slope_cliff",
                   [("DoD の LoD95 実測", sl_l, lod_d),
                    ("DoD 予測", sl_l, [1.96 * v for v in sd_p]),
                    ("M3C2 の LoD95 実測", sl_l, lod_m),
                    ("M3C2 予測", sl_l, [1.96 * v for v in sm_p])],
                   xlabel="傾斜 [deg]", ylabel="検出できる最小の変化 [m]",
                   title="斜面が壊すのは体積ではなく検出限界",
                   caption="足跡面積を揃えた比較。平地では両者は一致し、"
                           "傾斜とともに DoD だけが悪化する。")
    figs.save_table("slope_table",
                    ["傾斜 deg", "sigma_dz 実測/予測 m", "sigma_L 実測/予測 m",
                     "LoD95 DoD / M3C2 m", "比"], rows,
                    title="傾斜掃引(変化ゼロの対照から測った検出限界)",
                    caption="予測式は先に立ててから測った。うねりの寄与ぶん"
                            "実測がわずかに上に出る。")
    return {"slope": sl_l, "lod_d": lod_d, "lod_m": lod_m,
            "sd_m": sd_m, "sd_p": sd_p}


# --------------------------------------------------------------------------- #
# 6. 崖(2) 点密度                                                               #
# --------------------------------------------------------------------------- #
def section_density() -> dict:
    print("\n" + "=" * 78)
    print("6) 崖(2) 点密度 —— 「検出できる最小の変化厚」は 1/sqrt(密度)")
    print("=" * 78)
    print("   密度  セル内点数  DoD LoD95 [m] 予測   DoD 空セル  M3C2 LoD95 [m] 予測  "
          "M3C2 有効 core  C2C [m]")
    dens, ld, lm, pd_, pm, c2c, rate, emp = [], [], [], [], [], [], [], []
    for rho in (0.5, 1.0, 2.0, 5.0, 10.0, 20.0):
        rng = np.random.default_rng(SEED + 6)
        a, _ = make_cloud(rng, density=rho, with_change=False, occl=0.0)
        b, _ = make_cloud(rng, density=rho, with_change=False, occl=0.0)
        rc = dod(a, b)
        mc = m3c2(a, b)
        s_d = 1.96 * spread(rc["dz"][rc["ok"]])
        #: ★有効 core が少なすぎるときの LoD は「測った」ことにしない
        #   (2 点の標準偏差は数字にはなるが意味を持たない)。
        s_m = 1.96 * spread(mc["L"]) if int(mc["ok"].sum()) >= 100 else float("nan")
        step = max(1, len(a) // 6000)
        ch = float(fs.ledger.chamfer_distance(a[::step], b[::step]))
        dens.append(rho)
        ld.append(s_d)
        lm.append(s_m)
        pd_.append(1.96 * pred_sigma_dod(SLOPE, rho))
        pm.append(1.96 * pred_sigma_m3c2(SLOPE, rho))
        c2c.append(ch)
        rate.append(100 * mc["rate"])
        emp.append(100 * rc["empty"] / WIN_AREA)
        print("   %5.1f %9.1f %12.3f %7.3f %8.1f %% %13s %7.3f %12.1f %% %8.3f"
              % (rho, rho * CELL * CELL, s_d, pd_[-1], emp[-1],
                 ("%.3f" % s_m) if np.isfinite(s_m) else "測れず", pm[-1],
                 rate[-1], ch))
    print("\n  ★DoD の LoD は %.3f m(%.1f pt/m2)-> %.3f m(%.1f pt/m2)。"
          "密度 32 倍で %.2f 倍(予測 1/sqrt(32) = %.3f)。"
          % (ld[0], dens[0], ld[-1], dens[-1], ld[-1] / ld[0], 1 / math.sqrt(32)))
    print("     %.1f pt/m2 では最小検出厚 %.3f m —— この崩壊の最大深さ %.2f m の %.0f %% で、"
          "**縁は丸ごと見えない**。" % (dens[0], ld[0], SCAR["amp"],
                                        100 * ld[0] / SCAR["amp"]))
    print("     低密度側で予測より良く見えるのは、点の無いセル(%.1f %% at %.1f pt/m2)が"
          "差分から落ちるため —— これも「見えた所だけ数えている」。" % (emp[0], dens[0]))
    print("  ★★崖の形が 2 つの手法で違う。DoD は空セルが %.1f %% 増えるだけで動き続けるが、"
          % emp[0])
    print("     M3C2 は有効 core 率が %.1f %%(4 pt/m2)-> %.1f %%(2)-> %.1f %%(0.5)と"
          "**崩れて測れなくなる**" % (rate[3], rate[2], rate[0]))
    print("     (円柱の足跡 %.2f m2 に %d 点そろわない core を捨てるため)。"
          "止まるのは正直な壊れ方だが、" % (math.pi * R_CYL ** 2, MIN_CYL))
    print("     **体積を足す側が有効率で補正しないと土量が静かに欠ける**"
          "(7 節で %.0f %% 欠けるのを実測する)。" % (100 * (1 - 0.868)))
    print("  ★ゼロ点その 2: C2C(点群どうしの最近傍距離)は**変化が無くても** "
          "%.3f -> %.3f m を返す。" % (c2c[0], c2c[-1]))
    print("     これは点間隔そのもの(密度で決まる)で、しかも**符号が無い**ので"
          "掘削と堆積を分けられない。C2C で土量は測れない。")
    figs.save_plot("density_cliff",
                   [("DoD LoD95 実測", dens, ld), ("DoD 予測", dens, pd_),
                    ("M3C2 LoD95 実測", dens, lm), ("M3C2 予測", dens, pm),
                    ("C2C 最近傍距離(符号なし)", dens, c2c)],
                   xlabel="点密度 [pt/m2]", ylabel="距離 [m]",
                   title="密度は「何 m の変化まで言えるか」を決める",
                   caption="変化ゼロの対照で測った検出限界。C2C は変化が無くても"
                           "点間隔ぶんの距離を返し、符号も持たない。")
    return {"dens": dens, "lod_d": ld, "lod_m": lm, "pred_d": pd_, "pred_m": pm,
            "c2c": c2c, "rate": rate, "empty": emp}


# --------------------------------------------------------------------------- #
# 7. 崖(3) 系統誤差と位置合わせ                                                 #
# --------------------------------------------------------------------------- #
def align_icp(src: np.ndarray, dst: np.ndarray, voxel: float = 1.0,
              trim: float = 0.6):
    """安定域で位置を合わせる。点群は ``voxel_grid_downsample`` で間引く。"""
    s = np.asarray(fs.ledger.voxel_grid_downsample(src, voxel), float)
    d = np.asarray(fs.ledger.voxel_grid_downsample(dst, voxel), float)
    rot, tra, info = fs.ledger.icp_point2point_3d(s, d, iters=60, trim_ratio=trim,
                                                  max_corr_dist=3.0)
    rot = np.asarray(rot, float)
    tra = np.asarray(tra, float)
    return src @ rot.T + tra, rot, tra, info


def section_systematic(tr: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) 崖(3) GNSS/IMU の系統誤差 —— 予測: 偽の正味土量 = (delta_z + tan θ delta_y) x 面積")
    print("=" * 78)
    g = math.tan(math.radians(SLOPE))
    print("  平行移動 delta の見かけ鉛直変化は dz = delta_z + tan θ delta_y"
          "(斜面を登る向きにずらすと地面が上がって見える)。")
    print("  M3C2 の見かけ厚さは L = delta.n = delta_y sin θ + delta_z cos θ。"
          "体積に直すとき 1/cos θ するので")
    print("  V = (delta_y tan θ + delta_z) A_h —— **DoD と厳密に同じ式**。"
          "雑音は正味では打ち消すので、正味なら予測と直接比べられる。")
    print("\n    水平ずれ  予測 偽正味 [m3]  DoD 偽正味  M3C2 偽正味  "
          "M3C2(有効率で補正)  位置合わせ後")
    mags, pred, md, mm, mc, aft, rate = [], [], [], [], [], [], []
    for mag in (0.0, 0.05, 0.10, 0.20, 0.30):
        rng = np.random.default_rng(SEED + 7)
        a, _ = make_cloud(rng, with_change=False, occl=0.0)
        b0, _ = make_cloud(rng, with_change=False, occl=0.0)
        b = apply_pose(b0, (0.0, mag, 0.2 * mag), 0.02)
        rd = dod(a, b)
        vm = m3c2_volume(m3c2(a, b), lod=0.0)
        b_al, _, _, _ = align_icp(b, a)
        rd2 = dod(a, b_al)
        p = (0.2 * mag + g * mag) * WIN_AREA
        mags.append(mag)
        pred.append(p)
        md.append(rd["net"])
        mm.append(vm["net"])
        mc.append(vm["net_cov"])
        aft.append(rd2["net"])
        rate.append(vm["rate"])
        print("     %.2f m %14.1f %12.1f %12.1f %17.1f %14.1f"
              % (mag, p, md[-1], mm[-1], mc[-1], aft[-1]))
    print("\n  ★★予測 %.1f m3 に対し実測 DoD %.1f m3(差 %.1f %%)。"
          % (pred[-1], md[-1], 100 * abs(md[-1] / pred[-1] - 1)))
    print("  ★★M3C2 の生値 %.1f m3 は %.1f %% 足りない —— これは手法の差ではなく"
          "**有効 core 率 %.1f %% そのもの**。" % (mm[-1], 100 * (1 - mm[-1] / md[-1]),
                                                   100 * rate[-1]))
    print("     測れなかった core の面積は土量に一度も足されない。有効率で割り戻すと "
          "%.1f m3 で DoD と %.1f %% 差、予測とも一致する。"
          % (mc[-1], 100 * abs(mc[-1] / md[-1] - 1)))
    print("     -> 体積を返す実装は**測れた面積を必ず一緒に返す**べき。"
          "面積を返さない体積は、静かに欠けていても気づけない。")
    print("     M3C2 が有利なのは厚さと有意性であって体積ではない —— 法線方向の"
          "見かけ変化は cos 倍小さいが、体積で 1/cos するので約分する。")
    print("  ★位置合わせ(ICP、%.1f m ボクセルで間引き、trim 0.6)で 偽正味 %.1f -> %.1f m3。"
          % (1.0, md[-1], aft[-1]))
    print("     真の変化が無いので ICP は迷わない。次に**変化がある**場合を見る。")

    # --- ★ 合わせた分だけ変化が消える -------------------------------------- #
    print("\n  ★★合わせると変化が消える —— 変化のある点群対をそのまま ICP に掛ける:")
    print("     trim   使う対応   ICP 後の正味 [m3]   真値との比   吸われた鉛直量 [m]")
    rng = np.random.default_rng(SEED + 12)
    a, _ = make_cloud(rng, with_change=False, occl=0.0)
    b, _ = make_cloud(rng, with_change=True, occl=0.0)
    base_net = dod(a, b)["net"]
    eat = []
    for trim in (1.0, 0.8, 0.6):
        b_al, _, _, _ = align_icp(b, a, trim=trim)
        r = dod(a, b_al)
        eat.append((trim, r["net"], (r["net"] - base_net) / WIN_AREA))
        print("     %.1f  %8.0f %%      %12.2f      %6.1f %%        %+.4f"
              % (trim, 100 * trim, r["net"], 100 * r["net"] / tr["net"], eat[-1][2]))
    print("     位置合わせ前(系統誤差ゼロ)は %.2f m3(真値 %.2f)。" % (base_net, tr["net"]))
    print("  ★★変化域が窓の %.0f %% もあると、全対応を使う ICP は**変化を系統誤差と読む**。"
          % (100 * tr["area"] / WIN_AREA))
    print("     鉛直に %+.4f m 引き上げるだけで正味は真値の %.0f %% に潰れる ——"
          " 平均変化量 %.4f m とほぼ同じ量を吸っている。"
          % (eat[0][2], 100 * eat[0][1] / tr["net"], tr["net"] / WIN_AREA))
    print("     上位 %.0f %% だけ使う trimmed ICP なら %.1f %% まで戻る。"
          "**合わせてから測ると、合わせた分だけ変化が消える**。"
          % (100 * eat[-1][0], 100 * eat[-1][1] / tr["net"]))

    # --- 対照: 面内のずれは決まらないが、測定にも現れない -------------------- #
    print("\n  ★★対照: **斜面に沿った(面内の)ずれ**を与える —— 平面を自分自身に写すので")
    print("     予測: 偽の正味は厳密に 0。ICP はこの成分を決められない。")
    th = math.radians(SLOPE)
    inplane = np.array([0.15, 0.25 * math.cos(th), -0.25 * math.sin(th)])
    print("     ずれ (%.3f, %.3f, %.3f) m、大きさ %.3f m、法線成分 %.2e m"
          % (*inplane, np.linalg.norm(inplane),
             inplane @ np.array([0.0, math.sin(th), math.cos(th)])))
    print("     ★区画の**縁**は ICP に情報を与える(ずらすと縁の位置も動く)ので、")
    print("       「縁ごと」と「両時期を同じ窓に切ってから」の 2 通りで測る。")
    res = {}
    for label, undul, crop in (("うねりあり・縁ごと", UNDUL, False),
                               ("純平面・縁ごと", 0.0, False),
                               ("うねりあり・窓で切る", UNDUL, True),
                               ("純平面・窓で切る", 0.0, True)):
        rng = np.random.default_rng(SEED + 8)
        a, _ = make_cloud(rng, with_change=False, occl=0.0, undul=undul)
        b0, _ = make_cloud(rng, with_change=False, occl=0.0, undul=undul)
        b = apply_pose(b0, inplane)
        before = float(np.sqrt(np.mean(np.sum((b - b0) ** 2, axis=1))))
        if crop:
            def keep(q):
                return q[(q[:, 0] > WIN[0]) & (q[:, 0] < WIN[1])
                         & (q[:, 1] > WIN[0]) & (q[:, 1] < WIN[1])]
            _, rot, tra, _ = align_icp(keep(b), keep(a), trim=0.8)
            b_al = b @ rot.T + tra
        else:
            b_al, _, _, _ = align_icp(b, a, trim=0.8)
        rest = float(np.sqrt(np.mean(np.sum((b_al - b0) ** 2, axis=1))))
        v0, v1 = dod(a, b), dod(a, b_al)
        res[label] = (before, rest, v0["net"], v1["net"], v0["abs"], v1["abs"])
        print("     %-22s 実変位 %.3f -> %.3f m   偽正味 %+.1f -> %+.1f m3"
              % (label, before, rest, v0["net"], v1["net"]))
    pl, un = res["純平面・窓で切る"], res["うねりあり・窓で切る"]
    print("  ★★予測どおり**面内のずれは偽の正味を生まない**: どの条件でも |偽正味| <= %.1f m3"
          "(雑音の floor)。" % max(abs(v[2]) for v in res.values()))
    print("  ★予想は「純平面なら ICP が面内を全く決められない」だった。**縁ごと**だと"
          "実測は %.3f m まで詰まる —— 区画の縁が拘束になるから(うねりありの %.3f m と"
          "ほぼ同じ)。" % (res["純平面・縁ごと"][1], res["うねりあり・縁ごと"][1]))
    print("     両時期を**同じ窓に切って**縁の情報を消すと、純平面では %.3f m"
          "(与えた %.3f m の %.0f %%)が残ったまま —— 縮退が現れる。"
          % (pl[1], pl[0], 100 * pl[1] / pl[0]))
    print("     うねりがあれば同じ条件でも %.3f m まで詰まる。形が無ければ合わせられない。"
          % un[1])
    print("  -> それでも偽正味は %+.1f m3。**決まらない成分(面内の平行移動)は"
          "平面を自分自身に写すので、そもそも差分に現れない**。" % pl[3])
    print("     位置合わせの残差だけを見て「合っていない」と言うと判断を誤る。")

    figs.save_plot("systematic",
                   [("予測 (delta_z + tan θ delta_y) x 面積", mags, pred),
                    ("DoD 偽正味", mags, md), ("M3C2 偽正味(生値)", mags, mm),
                    ("M3C2 有効率で補正", mags, mc),
                    ("位置合わせ後の DoD", mags, aft)],
                   xlabel="水平の系統ずれ [m]", ylabel="偽の正味土量 [m3]",
                   title="系統誤差が生む偽の土量は傾斜に比例する",
                   caption="変化ゼロの対照。DoD と M3C2 は体積では同じだけ間違える。"
                           "雑音は正味では打ち消すので予測と直接比べられる。")
    return {"mag": mags, "pred": pred, "dod": md, "m3c2": mm, "m3c2_cov": mc,
            "after": aft, "plane": res, "eat": eat, "base_net": base_net,
            "rate": rate}


# --------------------------------------------------------------------------- #
# 8. 崖(4) 樹木による遮蔽                                                       #
# --------------------------------------------------------------------------- #
def section_occlusion(tr: dict, lod0: float) -> dict:
    print("\n" + "=" * 78)
    print("8) 崖(4) 樹冠による遮蔽 0 -> 60 %")
    print("=" * 78)
    print("  遮蔽は 2 つのことを同時にやる: (i) 地面点を減らして密度を下げる、"
          "(ii) 樹冠の点を地面に混ぜる(分類の取りこぼし)。")
    print("  **条件ごとに変化なしの対照を取り、その場で LoD を測り直す**ことで分ける。")
    print("  さらに LoD を標準偏差と MAD の 2 通りで出し、"
          "**外れ値汚染と密度低下を分ける**。")
    print("\n   遮蔽率 地面点 取りこぼし 全滅セル LoD(MAD)  平均 DEM 誤差%  "
          "中央値 DEM 誤差%  3x3 窓 誤差%  空セル  分類なし")
    occ, gr, leak, lstd, lmad = [], [], [], [], []
    adapt, med, wide, raw, rows, dead, empt = [], [], [], [], [], [], []
    for p in (0.0, 0.15, 0.30, 0.45, 0.60):
        rng = np.random.default_rng(SEED + 9)
        a, ga = make_cloud(rng, with_change=False, occl=p)
        b, _ = make_cloud(rng, with_change=True, occl=p)
        ka, kb = ground_filter(a), ground_filter(b)
        wa, wb = ground_filter(a, win=3), ground_filter(b, win=3)
        r0 = np.random.default_rng(SEED + 10)
        c0, gc = make_cloud(r0, with_change=False, occl=p)
        c1, _ = make_cloud(r0, with_change=False, occl=p)
        k0, k1 = ground_filter(c0), ground_filter(c1)
        rc = dod(c0[k0], c1[k1])
        dz_c = rc["dz"][rc["ok"]]
        l_std = 1.96 * spread(dz_c)
        l_mad = 1.96 * robust_spread(dz_c)
        r_ada = dod(a[ka], b[kb], lod=l_mad)
        r_med = dod(a[ka], b[kb], lod=l_mad, stat="median")
        r_wid = dod(a[wa], b[wb], lod=l_mad)
        r_raw = dod(a, b, lod=l_mad)
        t_ada = truth(lod=l_mad)
        e2 = 100 * (r_ada["ero"] / t_ada["ero"] - 1)
        e3 = 100 * (r_med["ero"] / t_ada["ero"] - 1)
        e4 = 100 * (r_wid["ero"] / t_ada["ero"] - 1)
        # 「地面点が 1 つも届かなかったセル」を数える(真値を知っているから数えられる)
        gz, _ = dem(a[ga])
        dead_cells = int((~np.isfinite(gz) & window_mask(gz.shape[1])).sum())
        occ.append(100 * p)
        gr.append(100 * float(ga.mean()))
        leak.append(100 * float((k0 & ~gc).sum()) / max(int(k0.sum()), 1))
        lstd.append(l_std)
        lmad.append(l_mad)
        adapt.append(r_ada["ero"])
        med.append(r_med["ero"])
        wide.append(r_wid["ero"])
        raw.append(r_raw["ero"])
        dead.append(dead_cells)
        empt.append(r_wid["empty"])
        rows.append(["%.0f" % (100 * p), "%.1f" % gr[-1], "%.2f" % leak[-1],
                     "%d" % dead_cells, "%.3f" % l_std, "%.3f" % l_mad,
                     "%.1f" % r_ada["ero"], "%+.1f" % e2,
                     "%.1f" % r_med["ero"], "%+.1f" % e3,
                     "%.1f" % r_wid["ero"], "%+.1f" % e4, "%d" % r_wid["empty"],
                     "%.1f" % t_ada["ero"], "%.1f" % r_raw["ero"]])
        print("   %5.0f %% %6.1f %% %7.2f %% %6d %8.3f %10.1f %+7.1f %11.1f %+7.1f"
              " %8.1f %+7.1f %6d %8.1f"
              % (100 * p, gr[-1], leak[-1], dead_cells, l_mad,
                 r_ada["ero"], e2, r_med["ero"], e3, r_wid["ero"], e4,
                 r_wid["empty"], raw[-1]))
    print("\n  ★★取りこぼしはたった %.2f %%(遮蔽 %.0f %%)なのに、標準偏差で引いた LoD は "
          "%.3f -> %.3f m と %.1f 倍に飛ぶ。" % (leak[-1], occ[-1], lstd[0], lstd[-1],
                                                 lstd[-1] / lstd[0]))
    print("     樹冠は 3〜9 m 高いので、1 セルに 1 点混ざるだけでそのセルが数 m ずれる。"
          "**少数の外れ値に標準偏差は弱い**。")
    print("  ★MAD で引けば %.3f -> %.3f m(%.1f 倍)で、密度低下ぶん"
          "(sqrt(%.1f/%.1f) = %.2f 倍)に近い。汚染と密度が分けられた。"
          % (lmad[0], lmad[-1], lmad[-1] / lmad[0], gr[0], gr[-1],
             math.sqrt(gr[0] / gr[-1])))
    print("  ★分類しないと樹冠が標高に混ざる: 遮蔽 %.0f %% で掘削 %.1f m3 —— "
          "分類したときの %.1f 倍。" % (occ[-1], raw[-1], raw[-1] / adapt[-1]))
    print("     ★予想は「樹冠は両時期に同じだけ入るので差分では消える」だった。"
          "実測は消えない —— 遮蔽は**確率的**で、どの点が樹冠で返るかが時期ごとに違う。")
    tt = truth(lod=lmad[-1])["ero"]
    print("  ★★しきい値を正しく引いても**足りない**: 平均 DEM のままだと遮蔽 %.0f %% で"
          "掘削 %.1f m3(誤差 %+.1f %%)。" % (occ[-1], adapt[-1], 100 * (adapt[-1] / tt - 1)))
    print("     しきい値が抑えるのは**雑音由来の偽陽性**であって、混ざった樹冠そのものは"
          "しきい値を軽々と超える。")
    print("  ★★予想は「セル代表値を平均から**中央値**に替えれば直る」だった。"
          "実測は %.1f m3(%+.1f %%)で**直らない**。"
          % (med[-1], 100 * (med[-1] / tt - 1)))
    print("     対照で原因を追うと、汚染は「1 セルに数点混ざる」ではなく"
          "**「セルの点が全部樹冠」**だった:")
    print("     遮蔽 %.0f %% で地面点が 1 つも届かないセルが %d 個(窓の %.1f %%)。"
          % (occ[-1], dead[-1], 100 * dead[-1] / WIN_AREA))
    print("     8 発すべてが遮られる確率は %.2f^8 = %.3f、樹冠下のセル数を掛けると"
          "この桁になる。中央値は**全員が外れ値**のセルを救えない。"
          % (occ[-1] / 100, (occ[-1] / 100) ** 8))
    print("  ★★直し方は代表値でなく**分類の窓**: 最低点を 3x3 セルで探すと、"
          "全滅したセルは隣の地面と比べて弾かれ、")
    print("     そのセルは**空になる**(= 測れなかったと分かる)。掘削 %.1f m3"
          "(%+.1f %%、遮蔽 0〜60 %% で %+.1f 〜 %+.1f %% と横ばい)、空セル %d 個。"
          % (wide[-1], 100 * (wide[-1] / tt - 1),
             100 * (min(wide) / tt - 1), 100 * (max(wide) / tt - 1), empt[-1]))
    print("     代償は 2 つ: 中央値は平坦部で平均より sqrt(pi/2) = 1.25 倍ばらつき"
          "(遮蔽 0 で誤差 %+.1f %% vs 平均 %+.1f %%)、"
          % (100 * (med[0] / truth(lod=lmad[0])["ero"] - 1),
             100 * (adapt[0] / truth(lod=lmad[0])["ero"] - 1)))
    print("     3x3 窓は遮蔽ゼロでも %d 個のセルを落とす(隣より高い正しい地面を疑うため)。"
          % empt[0])
    print("  -> **「地面点が届かなかった」を「変化した」と混同しない**のが要点。"
          "しきい値をその場で外れ値に強く引き直し、")
    print("     測れなかったセルは体積でなく**面積として**報告する。")
    print("     ただし LoD を上げるほど縁が落ちる: しきい値以上の真値は "
          "%.1f -> %.1f m3(-%.0f %%)。測れる土量そのものが減る。"
          % (truth(lod=lmad[0])["ero"], truth(lod=lmad[-1])["ero"],
             100 * (1 - truth(lod=lmad[-1])["ero"] / truth(lod=lmad[0])["ero"])))
    figs.save_table("occlusion",
                    ["遮蔽 %", "地面点 %", "取りこぼし %", "全滅セル",
                     "LoD std m", "LoD MAD m", "平均 DEM m3", "誤差 %",
                     "中央値 DEM m3", "誤差 %", "3x3 窓 m3", "誤差 %", "空セル",
                     "しきい値以上の真値 m3", "分類なし m3"], rows,
                    title="樹冠の遮蔽 —— 直すのは代表値ではなく分類の窓",
                    caption="誤差はそのしきい値以上の真値に対する値。全滅セル = "
                            "地面点が 1 つも届かなかったセル。中央値では救えない。")
    figs.save_plot("occlusion_lod",
                   [("LoD95(標準偏差)", occ, lstd),
                    ("LoD95(MAD、外れ値に強い)", occ, lmad),
                    ("固定 LoD(遮蔽 0 で決めた値)", occ, [lod0] * len(occ))],
                   xlabel="樹冠での遮蔽率 [%]", ylabel="検出できる最小の変化 [m]",
                   title="分類の取りこぼしが検出限界を飛ばす",
                   caption="取りこぼしは 1 % 未満でも、樹冠は数 m 高いので"
                           "標準偏差だけが桁で跳ねる。")
    return {"occ": occ, "raw": raw, "lstd": lstd, "lmad": lmad, "adapt": adapt,
            "median": med, "wide": wide, "dead": dead, "leak": leak, "ground": gr}


# --------------------------------------------------------------------------- #
# 9. 法線の符号                                                                 #
# --------------------------------------------------------------------------- #
def section_normals() -> dict:
    print("\n" + "=" * 78)
    print("9) 3-D の落とし穴 —— 法線の符号は道具では決まらない")
    print("=" * 78)
    rng = np.random.default_rng(SEED + 11)
    p, _ = make_cloud(rng, with_change=False, occl=0.0)
    sub = np.asarray(fs.ledger.voxel_grid_downsample(p, 2.0), float)[:1500]
    n1 = np.asarray(fs.ledger.estimate_normals(sub, k=16), float)
    n2 = np.asarray(fs.ledger.estimate_oriented_normals(sub, k=16), float)
    up1 = float((n1[:, 2] > 0).mean())
    up2 = float((n2[:, 2] > 0).mean())
    print("  %d 点(2.0 m ボクセルで間引き)で法線を推定:" % len(sub))
    print("    estimate_normals(近傍重心から離れる側に統一)  : 上向き %.1f %%"
          % (100 * up1))
    print("    estimate_oriented_normals(Hoppe の MST 伝播)  : 上向き %.1f %%"
          % (100 * up2))
    print("  ★開いた斜面には「外側」が無いので、局所ヒューリスティクスは %.1f %% を"
          "下向きにする。" % (100 * (1 - up1)))
    print("     大域向き付けは**一貫**させる(実測 %.0f %% が同じ側)が、"
          "**符号そのものは種の取り方次第** —— 今回たまたま上を向いただけ。"
          % (100 * max(up2, 1 - up2)))
    print("     -> 法線方向に測る手法は、符号を自分で固定しないと"
          "**掘削と堆積が入れ替わる**。この PoC は n_z > 0 を強制している。")
    return {"up_raw": up1, "up_oriented": up2}


# --------------------------------------------------------------------------- #
# 10. 図                                                                        #
# --------------------------------------------------------------------------- #
def section_figures(ctrl: dict, mm: dict, tr: dict) -> None:
    p1, p2 = ctrl["p1"], ctrl["p2"]
    z1, _ = dem(p1)
    step = max(1, len(p1) // 4000)
    params, _, _ = fs.ledger.ransac_plane(p1[::step], thresh=1.0, iters=200, seed=0)
    nrm = np.asarray(params["normal"], float)
    dd = float(params["d"])
    if nrm[2] < 0:
        nrm, dd = -nrm, -dd
    nx = z1.shape[1]
    cc = (np.arange(nx) + 0.5) * CELL
    xx, yy = np.meshgrid(cc, cc)
    detr = nrm[0] * xx + nrm[1] * yy + nrm[2] * np.nan_to_num(z1, nan=0.0) + dd
    detr = np.where(np.isfinite(z1), detr, np.nan)

    d_true = change(xx, yy)
    r = dod(p1, p2)
    lmap = np.full(z1.shape, np.nan)
    cores = mm["res"]["cores"]
    ci = np.round(cores[:, 0] / CELL - 0.5).astype(int)
    cj = np.round(cores[:, 1] / CELL - 0.5).astype(int)
    lmap[cj, ci] = mm["res"]["L"]

    def up(a):
        return np.asarray(a, float)[::-1]        # 行 0 = 南。北を上にする

    figs.save_grid("scene",
                   [up(detr), up(-d_true), up(r["dz"]), up(lmap)],
                   ["時期 1 の起伏(平面を抜いた残差 [m])",
                    "真の鉛直変位 [m](負 = 掘削)",
                    "DoD: 鉛直差 dz [m]", "M3C2: 法線方向の距離 L [m]"],
                   ncols=2, signed=[False, True, True, True],
                   title="航空 LiDAR の 2 時期差分(傾斜 %.0f 度・%.1f pt/m2)"
                         % (SLOPE, DENSITY),
                   caption="左上は樹冠と %.2f m のうねり。右上が仕込んだ真値"
                           "(掘削 %.1f m3 / 堆積 %.1f m3)。下 2 枚は足跡面積を"
                           "揃えて測った 2 通りの差。" % (UNDUL, tr["ero"], tr["dep"]))

    lod = ctrl["lod"]
    sig_dod = dod(p1, p2, lod=lod)["sig"]
    sig_m = np.zeros(z1.shape, bool)
    sig_m[cj, ci] = m3c2_volume(mm["res"], lod=None)["sig"]
    truth_mask = np.abs(d_true) > TAU
    figs.save_grid("change_maps",
                   [up(truth_mask.astype(float)), up(sig_dod.astype(float)),
                    up(sig_m.astype(float))],
                   ["真の変化域 %.0f m2" % tr["area"],
                    "DoD 有意 %.0f m2(LoD %.3f m 一律)" % (float(sig_dod.sum()), lod),
                    "M3C2 有意 %.0f m2(core ごとの sigma)" % float(sig_m.sum())],
                   ncols=3, title="「変化ありと判定した面積」は体積とは別に数える",
                   caption="面積と体積は別の量。面積が合っていても、縁の薄い層を"
                           "落としていれば体積は足りない。")

    row = int(SCAR["y"] / CELL)
    figs.save_plot("scar_profile",
                   [("真の鉛直変位 -d", cc, -d_true[row]),
                    ("DoD の dz", cc, r["dz"][row]),
                    ("M3C2 の L(法線方向)", cc, lmap[row])],
                   xlabel="x [m](崩壊中心を通る東西断面)", ylabel="変化量 [m]",
                   title="同じ崩壊、2 つの「深さ」",
                   caption="M3C2 の L は法線方向なので cos %.0f 度 = %.3f 倍だけ"
                           "浅く出る。体積にするときは 1/cos を掛ける。"
                           % (SLOPE, math.cos(math.radians(SLOPE))))


# --------------------------------------------------------------------------- #
# 11. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("11) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)
    for nm in ("fit_plane_3d", "ransac_plane", "icp_point2point_3d",
               "voxel_grid_downsample", "chamfer_distance", "estimate_normals",
               "estimate_oriented_normals"):
        assert hasattr(fs.ledger, nm), nm
    print("  (a) 使えた op: fit_plane_3d / ransac_plane / icp_point2point_3d /")
    print("      voxel_grid_downsample / chamfer_distance / estimate_normals /")
    print("      estimate_oriented_normals。3-D 変化検出の部品はほぼ揃っている。")
    print("      ただし ledger には在るがファサード ``fs.<名前>`` に出ていないものが多い"
          "(fit_plane_3d / ransac_plane / icp_point2point_3d / voxel_grid_downsample /"
          " chamfer_distance はすべて ledger 経由)。")

    assert not hasattr(fs, "m3c2") and not hasattr(fs.ledger, "m3c2")
    print("  (b) M3C2 そのものが無い(この PoC は 60 行で自前)。"
          "「局所平面 -> 法線方向の円柱 -> 平均位置の差 -> 空間可変 LoD」は"
          "地形・構造物・摩耗のどれでも同じ形なので、族に入る価値がある。")

    assert not hasattr(fs.ledger, "points_to_dem") and not hasattr(fs, "points_to_dem")
    print("  (c) **点群 -> DEM(格子の標高図)の口が無い**。demops は完成した"
          "標高図を受け取る前提で、その手前(セルに落として平均/最低/最頻を取る、"
          "空セルの方針を選ぶ)が公開経路に無い。この PoC は自前で書いた。")

    assert not hasattr(fs.ledger, "ground_filter") and not hasattr(fs, "csf_filter")
    print("  (d) 地面点の分類(CSF / 形態学的 / 進行 TIN)が無い。1 節で測ったとおり"
          "「セル内最低点 + 許容幅」は**先に傾きを抜かないと斜面で壊れる**ので、"
          "素朴な実装を各自が書くと同じ罠を踏む。")

    assert not hasattr(fs.ledger, "level_of_detection")
    print("  (e) 検出限界(LoD)を出す口が無い。土量を返す op を作るなら"
          "**しきらない値を返してはいけない** —— 3 節で見たとおり、しきらない"
          "内訳は真値の半分近くを雑音から作る。sigma と LoD を同時に返す契約にすべき。")

    print("  (f) 点の列規約: 3-D の点群 op は (N,3) = (x,y,z)、体積 op(esdf /")
    print("      query_distance)は (depth,row,col) = z 先頭。**同じ 3-D の中で"
          "軸の順が違う**ので、点群と体積を混ぜる処理は取り違えやすい。")
    print("  (g) icp_point2point_3d は numpy を渡しても **torch.Tensor を返す**。"
          "``np.asarray`` を忘れると下流で静かに型が変わる。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("斜面の土量を測る —— 縦に引くか、法線方向に測るか")
    print("傾斜 %.0f 度 / %.1f pt/m2 / 測距 sigma %.2f m / 水平 sigma %.2f m"
          % (SLOPE, DENSITY, SIG_R, SIG_H))
    print("=" * 78)

    sc = section_scene()
    tr = sc["truth"]
    ge = section_geometry(tr)
    ctrl = section_control(tr)
    mm = section_m3c2(ctrl, tr)
    sl = section_slope()
    de = section_density()
    sy = section_systematic(tr)
    oc = section_occlusion(tr, ctrl["lod"])
    nr = section_normals()
    section_figures(ctrl, mm, tr)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 予想「斜面では DoD の体積が cos だけ縮む」は**外れ**。鉛直差を水平投影"
          "面積で積むと cos は約分し、雑音を止めた実測の掘削誤差は 0〜40 度で "
          "%+.3f 〜 %+.3f %%(傾向なし)。"
          % (min(ge["ero_err"]), max(ge["ero_err"])))
    print("  * 間違うのは厚さ。DoD 深さ / M3C2 厚さ = %.3f(40 度、予測 sec = %.3f)。"
          % (mm["ratios"][-1][3], mm["ratios"][-1][4]))
    print("  * **変化なしの対照で偽掘削 %.1f m3 / 偽堆積 %.1f m3**(真の掘削の %.0f %%)。"
          "偽正味は %+.1f m3 なので正味だけ見ると気づけない。しきると %.1f m3。"
          % (ctrl["base"]["ero"], ctrl["base"]["dep"],
             100 * ctrl["base"]["ero"] / tr["ero"], ctrl["base"]["net"],
             ctrl["thr"]["ero"]))
    print("  * M3C2 の利得は傾斜からのみ: LoD 比 DoD/M3C2 は 0 度 %.2f、40 度 %.2f。"
          % (sl["lod_d"][0] / sl["lod_m"][0], sl["lod_d"][-1] / sl["lod_m"][-1]))
    print("  * 密度 %.1f -> %.1f pt/m2 で最小検出厚 %.3f -> %.3f m。低密度側は"
          "壊れ方が違い、DoD は空セル %.0f %% で測り続け、M3C2 は有効 core 率 %.1f %% で"
          "止まる(体積は有効率で割り戻さないと静かに欠ける)。"
          % (de["dens"][0], de["dens"][-1], de["lod_d"][0], de["lod_d"][-1],
             de["empty"][0], de["rate"][0]))
    print("  * 系統誤差 0.30 m の偽正味は予測 %.1f、DoD %.1f、M3C2 は有効率 %.1f %% で"
          "割り戻して %.1f m3 —— **手法が違っても体積は同じだけ間違える**。"
          "位置合わせ後 %.1f m3。"
          % (sy["pred"][-1], sy["dod"][-1], 100 * sy["rate"][-1],
             sy["m3c2_cov"][-1], sy["after"][-1]))
    print("  * ★変化のある対を全対応で合わせると正味は %.2f -> %.2f m3(真値 %.2f)。"
          "trim 0.6 で %.2f m3 まで戻る —— **合わせた分だけ変化が消える**。"
          % (sy["base_net"], sy["eat"][0][1], tr["net"], sy["eat"][-1][1]))
    print("  * 面内のずれは窓で切ると ICP が決められない(純平面で %.3f m 残る)が、"
          "偽正味は %+.1f m3 —— 決まらない成分は測定にも現れない。"
          % (sy["plane"]["純平面・窓で切る"][1],
             sy["plane"]["純平面・窓で切る"][3]))
    print("  * 遮蔽 %.0f %%: 取りこぼし %.2f %% で LoD(std)が %.3f -> %.3f m に飛ぶ"
          "(MAD なら %.3f -> %.3f m)。掘削は 平均 DEM %.1f / 中央値 %.1f / "
          "3x3 窓の分類 %.1f m3(真値 %.1f)—— ★直るのは代表値でなく分類の窓。"
          % (oc["occ"][-1], oc["leak"][-1], oc["lstd"][0], oc["lstd"][-1],
             oc["lmad"][0], oc["lmad"][-1], oc["adapt"][-1], oc["median"][-1],
             oc["wide"][-1], truth(lod=oc["lmad"][-1])["ero"]))
    print("  * 法線の符号は道具では決まらない(estimate_normals の上向きは %.1f %%)。"
          % (100 * nr["up_raw"]))

    # ---- 所見を固定する検査 ------------------------------------------------- #
    assert abs(tr["ero"] / V_ERO_EXACT - 1) < 0.02, "真値の数値積分が解析式から離れすぎ"
    assert max(abs(e) for e in ge["ero_err"]) < 1.0, "雑音なしの DoD 体積が傾斜で崩れた"
    assert max(abs(e) for e in ge["m_ero_err"]) < 3.0, "雑音なしの M3C2 体積が傾斜で崩れた"
    assert abs(mm["ratios"][-1][3] - mm["ratios"][-1][4]) < 0.10, "厚さの比が sec θ でない"
    assert ctrl["base"]["ero"] > 0.2 * tr["ero"], "対照の偽体積が小さすぎる(場面が甘い)"
    assert ctrl["thr"]["ero"] < 0.3 * ctrl["base"]["ero"], "しきっても偽体積が減らない"
    assert sl["lod_d"][0] / sl["lod_m"][0] < 1.3, "平地で M3C2 が有利になっている"
    assert sl["lod_d"][-1] / sl["lod_m"][-1] > 2.0, "斜面で M3C2 の利得が出ていない"
    assert de["lod_d"][-1] < 0.5 * de["lod_d"][0], "LoD が密度で下がっていない"
    assert de["rate"][1] < 0.5 * de["rate"][-1], "低密度で core が落ちていない(生存者バイアス)"
    assert abs(sy["dod"][-1] / sy["pred"][-1] - 1) < 0.10, "偽正味が予測から外れた"
    assert abs(sy["m3c2_cov"][-1] / sy["dod"][-1] - 1) < 0.10, "偽正味が両手法で違う"
    assert sy["m3c2"][-1] < 0.95 * sy["dod"][-1], "M3C2 の被覆欠けが再現していない"
    assert abs(sy["after"][-1]) < 0.15 * abs(sy["dod"][-1]), "ICP が系統誤差を落とせていない"
    assert abs(sy["eat"][0][1]) < 0.3 * abs(tr["net"]), "全対応 ICP が変化を吸っていない"
    assert abs(sy["eat"][-1][1]) > 0.6 * abs(tr["net"]), "trimmed ICP で戻っていない"
    pl = sy["plane"]["純平面・窓で切る"]
    assert pl[1] > 0.5 * pl[0], "純平面の面内縮退が再現していない"
    assert max(abs(v[3]) for v in sy["plane"].values()) < 10.0, \
        "面内のずれが偽の正味土量を生んでいる"
    assert oc["raw"][-1] > 1.5 * oc["adapt"][-1], "地面分類の効果が出ていない"
    assert oc["lstd"][-1] > 3 * oc["lstd"][0], "取りこぼしが標準偏差を飛ばしていない"
    assert oc["lmad"][-1] < 0.5 * oc["lstd"][-1], "MAD が外れ値を吸収できていない"
    assert oc["dead"][-1] > 10, "地面点が全滅するセルが出ていない(場面が甘い)"
    assert oc["wide"][-1] < 0.7 * oc["adapt"][-1], "3x3 窓の分類が汚染を落とせていない"
    assert abs(oc["wide"][-1] / truth(lod=oc["lmad"][-1])["ero"] - 1) < 0.4, \
        "3x3 窓で分類しても遮蔽で土量が壊れる"
    assert nr["up_raw"] < 0.95, "開いた斜面で法線の符号が揃ってしまった"

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
