# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""沈下したのか、測り直しただけなのか —— 検出限界(LoD)で切ると景色が変わる。

トンネルを掘ると地表が沈みます。2 時期の点群を引き算すれば沈下量は出ますが、
出てきた数字のうち**どこまでが本物か**を言わないと、補修も補償も決められません。
M3C2(Lague 2013)は core ごとに符号つきの差と一緒に **LoD**(level of detection,
``1.96·sqrt(σa²/na + σb²/nb)``)を返します。この PoC は真値を仕込んだ合成点群で

* ゼロ点 = C2C(最近傍距離。符号が無い)
* M3C2 の生の差(平均を見る)
* M3C2 + LoD(有意なものだけ見る)

を並べ、**「全体が沈んだ」と「有意に沈んだのは一部」の差**を数字で出します。

EXTEND: 実測に差し替えるなら :func:`make_clouds` が返す ``(N,3)`` を TLS / MMS の
点群に置き換えます。実データでは (a) 真の沈下場が無いので 3 節の TPR/FPR は
**水準測量の測点でしか**数えられず、(b) 粗さの真値も無いので 4 節の LoD の予測は
core ごとの残差 RMS で代用し、(c) 合わせの残差(6 節)は「変わっていないと
分かっている領域」を人が指定するしかありません。``NORMALS`` は必ず**局所平面**から
取ること —— 5 節のとおり鉛直で代用すると横断勾配が LoD に化けます。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(C2C)は沈下を見つけられない**。沈下ありの中央値 5.28 mm に対し、
   沈下ゼロで測り返しただけの対照群でも 5.20 mm(差 0.08 mm)。真の最大沈下
   8.00 mm と同じ桁の値が**変化ゼロでも出る**うえ、C2C には符号が無いので
   「沈んだ」と「盛り上がった」を区別できない。M3C2 なら同じデータで
   平均 -2.28 mm(真値 -2.31 mm)。
2. ★★**平均は「全体が沈んだ」と言い、LoD は「沈んだのは 46 %」と言う**。
   551 core の平均は -2.28 mm。ところが |d| > LoD を満たすのは 254/551
   (46.1 %)で、その平均は -4.71 mm。真値(|S| >= 2 mm を陽性とする)に対して
   TPR 89.5 % / FPR 4.9 % —— **有意判定は沈下の地図をよく復元する**が、
   「平均 2.28 mm 沈んだ」という 1 行はどちらの数字とも一致しない。
3. ★★**LoD の地図は沈下の地図ではなく、粗さと点密度の地図**。同じ 2〜4 mm の
   沈下でも、アスファルト(粗さ 1.5 mm)では 92.9 % が有意、砂利の路肩
   (粗さ 15 mm・密度半分)では 0.0 %。ゾーンごとの LoD 実測 0.61 / 3.02 /
   1.13 mm は閉形式 1.96·σ·sqrt(1/na+1/nb) と比 0.96〜1.00 で一致する。
4. ★★**法線を鉛直で代用すると、横断勾配 2 % だけで LoD が 4.7 倍になる**
   (0.90 -> 4.25 mm)。円筒に入る点の高さが勾配ぶん散らばるのを、M3C2 は
   「面が粗い」と読むため。沈下量そのものは両方とも当たっている
   (-2.28 / -2.28 mm)のに、**有意な core は 254 個から 41 個へ落ちる** ——
   測れているのに「有意でない」になる。
5. ★**551 回の検定をすれば 5 % は偽陽性になる**。沈下ゼロの対照群で有意と
   出た core は 27/551(4.9 %、名目 5 % どおり)。Benjamini-Hochberg
   (FDR 5 %)で 0 個、8 近傍のうち 3 個以上が有意という塊の規則で 1 個。
   ★同じ規則を本番に掛けると TPR は 89.5 -> 82.7 %(BH)/ 88.0 %(塊)で、
   **偽陽性はほぼ全部消えるのに真陽性はあまり減らない**。
6. ★★**LoD は雑音しか見ていない —— 合わせの残差は素通りする**。沈下ゼロで
   鉛直に -0.70 mm だけずらした対照群では、有意な core が 27 -> 288(52.3 %)に
   跳ね、平均は -0.70 mm。BH も塊の規則も**まったく効かない**(288 -> 288 / 288)
   —— 系統誤差は多重比較の問題ではないから。安定域(切羽の前方)の中央値で
   較正すると 288 -> 32 core に戻る。
7. ★★**有意なものだけ足すと体積は必ず過小になり、その量は先に計算できる**。
   真の沈下体積 0.6708 m3 に対し、全 core を足すと 0.6684 m3(-0.4 %)、
   有意な core だけだと 0.5423 m3(**-19.2 %**)。横断ガウスを LoD で切った
   ときの閉形式 erf(sqrt(ln(S_max/L))) は 0.815、真の場を数値積分した予測は
   0.816 で、実測の比 0.811 と 0.6 % 差。**「有意でない」は「ゼロ」ではない**。

【グラウンドトゥルース】
地表は 横断勾配 2 % + 縦断 0.5 % + 波長 11/7 m のうねり(振幅 8 mm)に、
**ゾーンごとに粗さの違う面**(砂利 15 mm / アスファルト 1.5 mm / 平板 4 mm、
相関長 0.12 m)を足した曲面。沈下は Peck の横断ガウス
``S = -S_max·exp(-(y-y0)²/2i²)`` に Attewell の縦断プロファイル
``Φ((x_f-x)/i_x)``(切羽の前は沈まない)を掛けた閉形式。2 時期は
**別の位置に別の密度で撒き直す**(A: 180 / B: 120 pt/m²、路肩は半分)。
測距雑音 σ=2 mm は点ごとに独立。core は 0.8 m 格子、円筒半径 0.6 m。

来歴(公開文献のみ): Peck, *Proc. 7th ICSMFE* (1969) 225 —— 横断沈下のガウス形 /
Attewell & Woodman, *Ground Engineering* 15 (1982) 13 —— 縦断プロファイル /
Lague, Brodu & Leroux, *ISPRS J. Photogramm.* 82 (2013) 10 —— M3C2 と LoD /
Benjamini & Hochberg, *JRSS-B* 57 (1995) 289 —— FDR。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree
from scipy.special import erf, ndtr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元(長さはすべて m。表示は mm)-------------------------------- #
AREA_X, AREA_Y = 24.0, 16.0     # 計測区画 [m]
CROSS, GRADE = 0.020, 0.005     # 横断勾配 / 縦断勾配
UNDU = 0.008                    # うねりの振幅 [m]

#: ゾーン (y の下限, 名前, 粗さ [m], 点密度の倍率)
ZONES = ((0.0, "砂利の路肩", 0.015, 0.5),
         (5.0, "アスファルト", 0.0015, 1.0),
         (11.0, "コンクリート平板", 0.004, 1.0))
ROUGH_CORR = 0.12               # 粗さの相関長 [m]
RHO_A, RHO_B = 180.0, 120.0     # 点密度 [pt/m2]
SIGMA_RANGE = 0.002             # 測距雑音 [m]

S_MAX = 0.008                   # 最大沈下量 [m]
Y0, I_TRANS = 8.0, 3.2          # 横断ガウスの中心と幅(i = K·z0)
X_FACE, I_LONG = 14.0, 2.5      # 切羽の位置と縦断の立ち上がり

CORE_STEP, RADIUS, MAX_DEPTH = 0.8, 0.6, 0.15
MIN_POINTS = 8
TRUE_POS_MM = 2.0               # 「本当に沈んだ」とみなす真値 [mm]
TRUE_NULL_MM = 0.2              # 「実質沈んでいない」とみなす真値 [mm]
SEED = 21

_GRID = 0.04                    # 粗さの場を作る格子 [m]


# --------------------------------------------------------------------------- #
# 真値                                                                          #
# --------------------------------------------------------------------------- #
def settlement(x, y, s_max: float = S_MAX) -> np.ndarray:
    """沈下量 [m](負が沈下)。Peck の横断ガウス x Attewell の縦断。"""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    return -s_max * np.exp(-((y - Y0) ** 2) / (2.0 * I_TRANS ** 2)) \
        * ndtr((X_FACE - x) / I_LONG)


def base_z(x, y) -> np.ndarray:
    """沈下前の地表(勾配 + うねり)[m]。"""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    return (CROSS * (y - 0.5 * AREA_Y) + GRADE * (x - 0.5 * AREA_X)
            + UNDU * np.sin(2.0 * np.pi * x / 11.0) * np.cos(2.0 * np.pi * y / 7.0))


def zone_of(y) -> np.ndarray:
    """ゾーン番号 (0,1,2)。"""
    y = np.asarray(y, np.float64)
    return np.searchsorted(np.asarray([z[0] for z in ZONES[1:]]), y, side="right")


_rough_cache: dict[int, np.ndarray] = {}


def rough_field(seed: int = SEED) -> np.ndarray:
    """粗さの場(格子 (ny,nx))。**面の性質なので 2 時期で同じ**。"""
    if seed in _rough_cache:
        return _rough_cache[seed]
    ny, nx = int(AREA_Y / _GRID) + 1, int(AREA_X / _GRID) + 1
    rng = np.random.default_rng(seed)
    f = gaussian_filter(rng.standard_normal((ny, nx)), ROUGH_CORR / _GRID)
    f /= f.std() or 1.0
    yy = np.arange(ny) * _GRID
    amp = np.asarray([ZONES[k][2] for k in zone_of(yy)])[:, None]
    _rough_cache[seed] = f * amp
    return _rough_cache[seed]


def rough_at(x, y, seed: int = SEED) -> np.ndarray:
    fld = rough_field(seed)
    return map_coordinates(fld, [np.asarray(y) / _GRID, np.asarray(x) / _GRID],
                           order=1, mode="nearest")


def surface_z(x, y, *, settle: bool, dz: float = 0.0, seed: int = SEED,
              s_max: float = S_MAX) -> np.ndarray:
    z = base_z(x, y) + rough_at(x, y, seed)
    if settle:
        z = z + settlement(x, y, s_max)
    return z + dz


# --------------------------------------------------------------------------- #
# 観測(2 時期を別の位置に別の密度で撒き直す)                                  #
# --------------------------------------------------------------------------- #
def sample_xy(rng, rho: float, dens_scale: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for k, (y0, _, _, dens) in enumerate(ZONES):
        y1 = ZONES[k + 1][0] if k + 1 < len(ZONES) else AREA_Y
        n = int(round(AREA_X * (y1 - y0) * rho * dens * dens_scale))
        xs.append(rng.uniform(0.0, AREA_X, n))
        ys.append(rng.uniform(y0, y1, n))
    return np.concatenate(xs), np.concatenate(ys)


def make_clouds(*, settle: bool = True, dz: float = 0.0, seed: int = SEED,
                dens_scale: float = 1.0,
                s_max: float = S_MAX) -> tuple[np.ndarray, np.ndarray]:
    """(A, B) = 2 時期の点群 ``(N,3)``。B に沈下と合わせの残差 ``dz`` が入る。"""
    rng = np.random.default_rng(seed)
    xa, ya = sample_xy(rng, RHO_A, dens_scale)
    za = surface_z(xa, ya, settle=False, seed=seed) \
        + SIGMA_RANGE * rng.standard_normal(xa.size)
    xb, yb = sample_xy(rng, RHO_B, dens_scale)
    zb = surface_z(xb, yb, settle=settle, dz=dz, seed=seed, s_max=s_max) \
        + SIGMA_RANGE * rng.standard_normal(xb.size)
    return (np.column_stack([xa, ya, za]), np.column_stack([xb, yb, zb]))


def core_grid() -> tuple[np.ndarray, np.ndarray, int, int]:
    """core の格子。返り値 (cores (M,3), 真の沈下 [m] (M,), nx, ny)。"""
    xs = np.arange(RADIUS + 0.2, AREA_X - RADIUS - 0.1, CORE_STEP)
    ys = np.arange(RADIUS + 0.2, AREA_Y - RADIUS - 0.1, CORE_STEP)
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    x, y = gx.ravel(), gy.ravel()
    c = np.column_stack([x, y, surface_z(x, y, settle=False)])
    return c, settlement(x, y), xs.size, ys.size


def fitted_normals(a: np.ndarray, cores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """core ごとに局所平面を当てて法線を取る(**+z 側に向きを揃える**)。

    Returns: 法線 ``(M,3)`` と、面からの直交距離の RMS ``(M,)``[m]。後者は
    「その円筒で実際に効いている粗さ」で、LoD の予測に使う。
    """
    tree = cKDTree(a[:, :2])
    out = np.tile(np.asarray([0.0, 0.0, 1.0]), (len(cores), 1))
    res = np.full(len(cores), np.nan)
    for k, c in enumerate(cores):
        idx = tree.query_ball_point(c[:2], RADIUS)
        if len(idx) < 8:
            continue
        _, n, r = fs.ledger.fit_plane_3d.raw(a[idx])
        n = np.asarray(n, np.float64)
        out[k] = n if n[2] >= 0 else -n
        res[k] = float(r)
    return out, res


def m3c2(a, b, cores, normals):
    d, lod = fs.ledger.m3c2_distance.raw(a, b, cores, normals, RADIUS, MAX_DEPTH,
                                         MIN_POINTS)
    return np.asarray(d, np.float64), np.asarray(lod, np.float64)


def c2c_map(a: np.ndarray, b: np.ndarray, cores: np.ndarray) -> np.ndarray:
    """ゼロ点。core ごとに「円筒内の A 点から B への最近傍距離」の平均 [m]。

    ★``fullseye`` には ``chamfer_distance``(スカラー 1 個)しか無く、
    **点ごと / core ごとの最近傍距離を返す口が無い**ので scipy で書いている。
    """
    dist_a = cKDTree(b).query(a, k=1)[0]
    tree = cKDTree(a[:, :2])
    out = np.full(len(cores), np.nan)
    for k, c in enumerate(cores):
        idx = tree.query_ball_point(c[:2], RADIUS)
        if len(idx) >= MIN_POINTS:
            out[k] = float(dist_a[idx].mean())
    return out


# --------------------------------------------------------------------------- #
# 有意性のまとめ方                                                              #
# --------------------------------------------------------------------------- #
def zscore(d: np.ndarray, lod: np.ndarray) -> np.ndarray:
    """LoD = 1.96σ_diff なので、z = |d| / (LoD/1.96)。"""
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.abs(d) / np.maximum(lod / 1.96, 1e-12)


def pvalues(z: np.ndarray) -> np.ndarray:
    return 2.0 * (1.0 - ndtr(z))


def bh_reject(p: np.ndarray, q: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg の FDR 制御。有限の p だけで手続きを回す。"""
    ok = np.isfinite(p)
    out = np.zeros_like(p, bool)
    pp = p[ok]
    if pp.size == 0:
        return out
    order = np.argsort(pp)
    m = pp.size
    thr = q * (np.arange(1, m + 1) / m)
    passed = pp[order] <= thr
    if not passed.any():
        return out
    kmax = int(np.nonzero(passed)[0].max())
    cut = pp[order][kmax]
    sel = np.zeros(m, bool)
    sel[pp <= cut] = True
    out[np.nonzero(ok)[0][sel]] = True
    return out


def cluster_filter(sig: np.ndarray, nx: int, ny: int, need: int = 3) -> np.ndarray:
    """8 近傍のうち ``need`` 個以上が有意な core だけ残す(塊の規則)。"""
    g = sig.reshape(nx, ny).astype(np.int32)
    cnt = np.zeros_like(g)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            cnt += np.roll(np.roll(g, dx, axis=0), dy, axis=1)
    return (sig.reshape(nx, ny) & (cnt >= need)).ravel()


def confusion(sig: np.ndarray, truth_mm: np.ndarray) -> dict:
    """陽性 = 真値 |S| >= 2 mm、陰性 = |S| <= 0.2 mm、その間は**灰色帯**。

    ★真値のしきい値(2 mm)と検定のしきい値(LoD、実測 0.8 mm 前後)は別物なので、
    間の core を「偽陽性」に数えると**本物の小さな沈下を誤検出として罰する**ことに
    なる。3 分類で数え、灰色帯は別に報告する。
    """
    pos = np.abs(truth_mm) >= TRUE_POS_MM
    neg = np.abs(truth_mm) <= TRUE_NULL_MM
    grey = ~pos & ~neg
    tp = int(np.count_nonzero(sig & pos))
    fn = int(np.count_nonzero(~sig & pos))
    fp = int(np.count_nonzero(sig & neg))
    tn = int(np.count_nonzero(~sig & neg))
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "grey": int(grey.sum()), "grey_sig": int(np.count_nonzero(sig & grey)),
            "tpr": 100.0 * tp / max(tp + fn, 1), "fpr": 100.0 * fp / max(fp + tn, 1)}


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                 #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— Peck の横断ガウス x Attewell の縦断")
    print("=" * 78)
    cores, s_true, nx, ny = core_grid()
    s_mm = s_true * 1000.0

    # 体積の閉形式: S_max · (i√2π の切り出し) · (縦断の積分)
    yy = np.linspace(0.0, AREA_Y, 4001)
    xx = np.linspace(0.0, AREA_X, 4001)
    trans = float(np.trapezoid(np.exp(-((yy - Y0) ** 2) / (2 * I_TRANS ** 2)), yy))
    longi = float(np.trapezoid(ndtr((X_FACE - xx) / I_LONG), xx))
    vol = S_MAX * trans * longi
    print("  区画 %.0f x %.0f m / core %d 個(%d x %d、間隔 %.1f m、円筒半径 %.1f m)"
          % (AREA_X, AREA_Y, len(cores), nx, ny, CORE_STEP, RADIUS))
    print("  沈下: 最大 %.1f mm / 横断 i = %.1f m / 切羽 x = %.1f m"
          % (S_MAX * 1000, I_TRANS, X_FACE))
    print("  真の沈下体積(閉形式) %.4f m3 = 横断 %.3f m x 縦断 %.3f m x %.4f m"
          % (vol, trans, longi, S_MAX))
    print("  区画平均の沈下 %.3f mm / |S| >= %.1f mm の core は %d/%d (%.1f %%)"
          % (s_mm.mean(), TRUE_POS_MM, int(np.count_nonzero(np.abs(s_mm) >= TRUE_POS_MM)),
             len(cores), 100 * np.count_nonzero(np.abs(s_mm) >= TRUE_POS_MM) / len(cores)))
    for k, (y0, name, rgh, dens) in enumerate(ZONES):
        y1 = ZONES[k + 1][0] if k + 1 < len(ZONES) else AREA_Y
        print("   ゾーン %d %-16s y %.0f-%.0f m  粗さ %5.1f mm  密度 %.0f/%.0f pt/m2"
              % (k, name, y0, y1, rgh * 1000, RHO_A * dens, RHO_B * dens))

    fld = rough_field()
    figs.save_grid("scene",
                   [s_mm.reshape(nx, ny).T, fld * 1000.0,
                    zone_of(np.arange(fld.shape[0]) * _GRID)[:, None]
                    * np.ones((1, fld.shape[1]))],
                   ["真の沈下 [mm](青=沈下、%.1f mm まで)" % (S_MAX * 1000),
                    "面の粗さ [mm](2 時期で同じ)", "ゾーン(0 砂利 / 1 舗装 / 2 平板)"],
                   ncols=1, signed=[True, True, False],
                   title="仕込んだ真値 —— 沈下は切羽 x=%.0f m の後ろだけ" % X_FACE,
                   caption="横軸 x [%.0f m]、縦軸 y [%.0f m]。粗さはゾーンで 10 倍"
                           "違い、これが LoD をゾーンごとに変える。"
                           % (AREA_X, AREA_Y))
    return {"cores": cores, "s_mm": s_mm, "nx": nx, "ny": ny, "vol": vol,
            "trans": trans, "longi": longi}


# --------------------------------------------------------------------------- #
# 2. ゼロ点 C2C                                                                 #
# --------------------------------------------------------------------------- #
def section_zero(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— C2C(最近傍距離)は符号を持たず、変化ゼロでも値を返す")
    print("=" * 78)
    cores = sc["cores"]
    a1, b1 = make_clouds(settle=True)
    a0, b0 = make_clouds(settle=False)
    n_fit, resid = fitted_normals(a1, cores)
    c1, c0 = c2c_map(a1, b1, cores) * 1000.0, c2c_map(a0, b0, cores) * 1000.0
    d1, l1 = m3c2(a1, b1, cores, n_fit)

    print("  点数: A %d / B %d(密度 %.0f / %.0f pt/m2)" % (len(a1), len(b1), RHO_A, RHO_B))
    print("   量                       沈下あり      沈下ゼロ(対照群)    差")
    print("   C2C の中央値            %7.2f mm     %7.2f mm        %+6.2f mm"
          % (np.nanmedian(c1), np.nanmedian(c0), np.nanmedian(c1) - np.nanmedian(c0)))
    print("   C2C の最大              %7.2f mm     %7.2f mm        %+6.2f mm"
          % (np.nanmax(c1), np.nanmax(c0), np.nanmax(c1) - np.nanmax(c0)))
    print("   M3C2 の平均             %7.2f mm     %7.2f mm        %+6.2f mm"
          % (np.nanmean(d1) * 1000, np.nanmean(
              m3c2(a0, b0, cores, n_fit)[0]) * 1000,
             (np.nanmean(d1) - np.nanmean(m3c2(a0, b0, cores, n_fit)[0])) * 1000))
    print("\n  ★C2C は真の最大沈下 %.1f mm の %.0f 倍の値を**変化ゼロでも**返す"
          "(沈下ありとの中央値の差はわずか %+.2f mm)。符号も無い。"
          % (S_MAX * 1000, np.nanmedian(c0) / (S_MAX * 1000),
             np.nanmedian(c1) - np.nanmedian(c0)))
    print("     正体は**点間隔**(密度 %.0f pt/m2 なら平均間隔 %.0f mm)—— "
          "「いちばん近い点までの距離」は撒き直しただけで出る。"
          % (RHO_B, 1000.0 / math.sqrt(RHO_B)))
    print("     M3C2 の平均 %.2f mm は真値の平均 %.2f mm と %+.2f mm。"
          % (np.nanmean(d1) * 1000, sc["s_mm"].mean(),
             np.nanmean(d1) * 1000 - sc["s_mm"].mean()))
    assert abs(np.nanmedian(c1) - np.nanmedian(c0)) < 1.0
    assert abs(np.nanmean(d1) * 1000 - sc["s_mm"].mean()) < 0.5
    return {"a1": a1, "b1": b1, "a0": a0, "b0": b0, "n_fit": n_fit, "resid": resid,
            "c2c_1": c1, "c2c_0": c0, "d1": d1, "l1": l1}


# --------------------------------------------------------------------------- #
# 3. 平均 vs 有意                                                               #
# --------------------------------------------------------------------------- #
def section_mean_vs_significant(sc: dict, z: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 平均は『全体が沈んだ』と言い、LoD は『沈んだのは一部』と言う")
    print("=" * 78)
    d, lod, s_mm = z["d1"] * 1000.0, z["l1"] * 1000.0, sc["s_mm"]
    ok = np.isfinite(d)
    sig = np.isfinite(d) & (np.abs(d) > lod)
    cm = confusion(sig, s_mm)
    print("  有効な core %d/%d  /  LoD の中央値 %.2f mm(最小 %.2f 最大 %.2f)"
          % (int(ok.sum()), len(d), np.nanmedian(lod), np.nanmin(lod), np.nanmax(lod)))
    print("   全 core の平均            %7.2f mm  (真値の平均 %.2f mm)"
          % (np.nanmean(d), s_mm.mean()))
    print("   有意な core               %d/%d (%.1f %%)、その平均 %.2f mm"
          % (int(sig.sum()), int(ok.sum()), 100 * sig.sum() / max(ok.sum(), 1),
             float(np.nanmean(d[sig]))))
    print("   真値 |S| >= %.1f mm の core %d 個、その真値の平均 %.2f mm"
          % (TRUE_POS_MM, int(np.count_nonzero(np.abs(s_mm) >= TRUE_POS_MM)),
             float(s_mm[np.abs(s_mm) >= TRUE_POS_MM].mean())))
    print("\n   混同行列(陽性 = |S| >= %.1f mm、陰性 = |S| <= %.1f mm):"
          % (TRUE_POS_MM, TRUE_NULL_MM))
    print("   TP %d / FN %d / FP %d / TN %d   -> TPR %.1f %% / FPR %.1f %%"
          % (cm["tp"], cm["fn"], cm["fp"], cm["tn"], cm["tpr"], cm["fpr"]))
    print("   灰色帯(%.1f 〜 %.1f mm)は %d core、うち有意 %d(%.1f %%)—— "
          "**本物の小さな沈下なので偽陽性ではない**。"
          % (TRUE_NULL_MM, TRUE_POS_MM, cm["grey"], cm["grey_sig"],
             100 * cm["grey_sig"] / max(cm["grey"], 1)))
    print("\n  ★『平均 %.2f mm 沈んだ』は、有意な %.1f %% の平均 %.2f mm とも、"
          "本当に沈んだ領域の平均 %.2f mm とも一致しない。"
          % (np.nanmean(d), 100 * sig.sum() / max(ok.sum(), 1), float(np.nanmean(d[sig])),
             float(s_mm[np.abs(s_mm) >= TRUE_POS_MM].mean())))
    assert cm["tpr"] > 70.0 and cm["fpr"] < 15.0, cm

    nx, ny = sc["nx"], sc["ny"]
    figs.save_grid("map_change",
                   [d.reshape(nx, ny).T, sig.reshape(nx, ny).T.astype(np.float64),
                    (np.abs(s_mm) >= TRUE_POS_MM).reshape(nx, ny).T.astype(np.float64)],
                   ["M3C2 の差 [mm](青=沈下)",
                    "有意 |d| > LoD(%d core)" % int(sig.sum()),
                    "真値 |S| >= %.1f mm(%d core)"
                    % (TRUE_POS_MM, int(np.count_nonzero(np.abs(s_mm) >= TRUE_POS_MM)))],
                   ncols=1, signed=[True, False, False],
                   title="沈下の地図と、有意の地図と、真値の地図",
                   caption="有意の地図は真値の地図をよく復元する(TPR %.1f %% / "
                           "FPR %.1f %%)。ただし縁が痩せる —— そこが 7 節の体積の話。"
                           % (cm["tpr"], cm["fpr"]))
    figs.save_grid("map_lod", [lod.reshape(nx, ny).T],
                   ["LoD [mm](中央値 %.2f)" % np.nanmedian(lod)], ncols=1,
                   title="検出限界の地図 —— 沈下ではなく粗さと密度の地図",
                   caption="上の帯(砂利の路肩)は粗さ %.0f mm・密度半分なので LoD が"
                           "跳ね上がる。同じ沈下でもここでは有意にならない。"
                           % (ZONES[0][2] * 1000))
    return {"sig": sig, "cm": cm, "d": d, "lod": lod, "ok": ok}


# --------------------------------------------------------------------------- #
# 4. LoD は粗さと密度の地図                                                     #
# --------------------------------------------------------------------------- #
def section_lod_is_roughness(sc: dict, z: dict, mv: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) LoD の地図は粗さと点密度の地図 —— 閉形式と突き合わせる")
    print("=" * 78)
    print("  予測 A(素朴): LoD = 1.96·σ·sqrt(1/na + 1/nb)、σ = sqrt(粗さ² + 測距雑音²)、"
          "n = ρ·π·r²")
    print("  予測 B: σ を**平面当てはめの残差 RMS**にする(円筒内の粗さのうち"
          "平面で説明できる分は法線に吸われるので、A は上振れするはず)")
    print("\n   ゾーン            粗さ mm  残差 mm  LoD 実測  予測 A  比A   予測 B  比B  "
          "|S| %.0f-%.0f mm の検出率" % (TRUE_POS_MM, 2 * TRUE_POS_MM))

    cores, s_mm = sc["cores"], sc["s_mm"]
    lod, sig, resid = mv["lod"], mv["sig"], z["resid"] * 1000.0
    zid = zone_of(cores[:, 1])
    rows, meas, pred, predb = [], [], [], []
    for k, (y0, name, rgh, dens) in enumerate(ZONES):
        m = zid == k
        sg = math.sqrt(rgh ** 2 + SIGMA_RANGE ** 2)
        na = RHO_A * dens * math.pi * RADIUS ** 2
        nb = RHO_B * dens * math.pi * RADIUS ** 2
        fac = math.sqrt(1.0 / na + 1.0 / nb)
        p = 1.96 * sg * fac * 1000.0
        rs = float(np.nanmedian(resid[m]))
        pb = 1.96 * rs * fac
        mm = float(np.nanmedian(lod[m]))
        band = m & (np.abs(s_mm) >= TRUE_POS_MM) & (np.abs(s_mm) < 2 * TRUE_POS_MM)
        rate = 100.0 * np.count_nonzero(sig & band) / max(int(band.sum()), 1)
        rows.append([name, "%.1f" % (rgh * 1000), "%.1f" % rs, "%.2f" % mm,
                     "%.2f" % p, "%.2f" % (mm / p), "%.2f" % pb, "%.2f" % (mm / pb),
                     "%.1f %% (%d core)" % (rate, int(band.sum()))])
        meas.append(mm)
        pred.append(p)
        predb.append(pb)
        print("   %-16s %6.1f  %6.1f   %6.2f   %6.2f  %.2f  %6.2f  %.2f  %5.1f %% (%d core)"
              % (name, rgh * 1000, rs, mm, p, mm / p, pb, mm / pb, rate, int(band.sum())))

    ratio = [a / b for a, b in zip(meas, pred)]
    ratio_b = [a / b for a, b in zip(meas, predb)]
    print("\n  ★素朴な予測 A との比は %.2f 〜 %.2f と**一貫して 1 を下回る**。"
          "予想どおり上振れしていた —— 局所平面を当てるので、円筒内の粗さのうち"
          % (min(ratio), max(ratio)))
    print("     平面で説明できる分(路肩なら %.1f -> %.1f mm)が法線に吸われるため。"
          "残差を使う予測 B なら比 %.2f 〜 %.2f。"
          % (ZONES[0][2] * 1000, float(np.nanmedian(resid[zid == 0])),
             min(ratio_b), max(ratio_b)))
    print("  ★同じ %.0f〜%.0f mm の沈下が、舗装では %s、路肩では %s しか有意に"
          "ならない。**測れるかどうかは場所の性質**で、沈下量では決まらない。"
          % (TRUE_POS_MM, 2 * TRUE_POS_MM, rows[1][8].split(" ")[0], rows[0][8].split(" ")[0]))
    assert 0.90 < min(ratio_b) and max(ratio_b) < 1.10, ratio_b
    assert max(ratio) < 1.0, ratio

    figs.save_table("lod_by_zone",
                    ["ゾーン", "粗さ mm", "平面残差 mm", "LoD 実測 mm", "予測A mm",
                     "比A", "予測B mm", "比B",
                     "%.0f-%.0f mm の検出率" % (TRUE_POS_MM, 2 * TRUE_POS_MM)], rows,
                    title="LoD はゾーンで %.1f 倍違う" % (max(meas) / min(meas)),
                    caption="予測は 1.96·σ·sqrt(1/na+1/nb)。σ に生の粗さを使うと"
                            "上振れし、平面当てはめの残差を使うと合う。沈下量は"
                            "この式に入っていない —— LoD の地図は面の地図。")
    return {"meas": meas, "pred": pred, "predb": predb, "ratio": ratio,
            "ratio_b": ratio_b}


# --------------------------------------------------------------------------- #
# 5. 法線を鉛直で代用すると勾配が LoD に化ける                                  #
# --------------------------------------------------------------------------- #
def section_normals(sc: dict, z: dict, mv: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) 法線を鉛直で代用する —— 横断勾配 %.0f %% が LoD に化ける" % (100 * CROSS))
    print("=" * 78)
    cores, s_mm = sc["cores"], sc["s_mm"]
    n_up = np.tile(np.asarray([0.0, 0.0, 1.0]), (len(cores), 1))
    d_up, l_up = m3c2(z["a1"], z["b1"], cores, n_up)
    d_up, l_up = d_up * 1000.0, l_up * 1000.0
    sig_up = np.isfinite(d_up) & (np.abs(d_up) > l_up)
    cm_up = confusion(sig_up, s_mm)

    # 予測: 半径 r の円板に一様に撒いた点の、勾配 g の面での鉛直方向の散らばりは
    # g·r/2(円板上の座標の標準偏差が r/2)。
    slope = math.hypot(CROSS, GRADE)
    sd_tilt = slope * RADIUS / 2.0
    print("  予測を先に: 勾配 %.4f の面を半径 %.1f m の円筒で切ると、鉛直軸への"
          "射影は σ = g·r/2 = %.2f mm 散らばる。" % (slope, RADIUS, sd_tilt * 1000))
    print("\n   ゾーン            LoD 局所平面   LoD 鉛直   予測(鉛直)   比")
    zid = zone_of(cores[:, 1])
    for k, (_, name, rgh, dens) in enumerate(ZONES):
        m = zid == k
        na = RHO_A * dens * math.pi * RADIUS ** 2
        nb = RHO_B * dens * math.pi * RADIUS ** 2
        sg = math.sqrt(sd_tilt ** 2 + rgh ** 2 + SIGMA_RANGE ** 2)
        p = 1.96 * sg * math.sqrt(1.0 / na + 1.0 / nb) * 1000.0
        got = float(np.nanmedian(l_up[m]))
        print("   %-16s %8.2f mm  %8.2f mm  %8.2f mm   %.2f"
              % (name, float(np.nanmedian(mv["lod"][m])), got, p, got / p))
    print("\n   法線          LoD 中央値   平均の差      有意な core   TPR      FPR")
    print("   局所平面      %7.2f mm  %7.2f mm    %4d      %5.1f %%  %5.1f %%"
          % (np.nanmedian(mv["lod"]), np.nanmean(mv["d"]), int(mv["sig"].sum()),
             mv["cm"]["tpr"], mv["cm"]["fpr"]))
    print("   鉛直 (0,0,1)  %7.2f mm  %7.2f mm    %4d      %5.1f %%  %5.1f %%"
          % (np.nanmedian(l_up), np.nanmean(d_up), int(sig_up.sum()),
             cm_up["tpr"], cm_up["fpr"]))
    print("\n  ★沈下量そのものはどちらも当たっている(%.2f / %.2f mm、真値 %.2f)。"
          % (np.nanmean(mv["d"]), np.nanmean(d_up), s_mm.mean()))
    print("     壊れるのは LoD で、%.2f -> %.2f mm(%.1f 倍)。有意な core は "
          "%d -> %d 個。" % (np.nanmedian(mv["lod"]), np.nanmedian(l_up),
                            np.nanmedian(l_up) / np.nanmedian(mv["lod"]),
                            int(mv["sig"].sum()), int(sig_up.sum())))
    print("     予測: 勾配 %.4f の面を半径 %.1f m で切ると軸方向の σ は %.2f mm 増える"
          " → LoD は sqrt(σ²+…) 経由で効く。" % (slope, RADIUS, sd_tilt * 1000))
    print("  **測れているのに『有意でない』になる** —— これは面の問題ではなく"
          "法線の取り方の問題。")
    assert np.nanmedian(l_up) > 2.0 * np.nanmedian(mv["lod"])
    return {"lod_up": float(np.nanmedian(l_up)), "n_up": int(sig_up.sum()),
            "cm_up": cm_up, "d_up": d_up}


# --------------------------------------------------------------------------- #
# 6. 多重比較 —— 551 回検定すれば 5 % は偽陽性                                  #
# --------------------------------------------------------------------------- #
def section_multiplicity(sc: dict, z: dict, mv: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) 多重比較 —— core の数だけ検定している")
    print("=" * 78)
    cores, s_mm, nx, ny = sc["cores"], sc["s_mm"], sc["nx"], sc["ny"]
    d0, l0 = m3c2(z["a0"], z["b0"], cores, z["n_fit"])
    d0, l0 = d0 * 1000.0, l0 * 1000.0
    ok0 = np.isfinite(d0)
    sig0 = ok0 & (np.abs(d0) > l0)
    p0 = pvalues(zscore(d0, l0))
    bh0 = bh_reject(p0)
    cl0 = cluster_filter(sig0, nx, ny)

    print("  対照群(沈下ゼロ・合わせも完全)。真の陽性は 0 個。")
    print("   規則                     有意と出た core        名目")
    print("   |d| > LoD (95 %%)         %3d/%3d (%.1f %%)        5.0 %%"
          % (int(sig0.sum()), int(ok0.sum()), 100 * sig0.sum() / max(ok0.sum(), 1)))
    print("   + Benjamini-Hochberg     %3d/%3d (%.1f %%)        FDR 5 %%"
          % (int(bh0.sum()), int(ok0.sum()), 100 * bh0.sum() / max(ok0.sum(), 1)))
    print("   + 塊の規則(8 近傍 3 個)  %3d/%3d (%.1f %%)"
          % (int(cl0.sum()), int(ok0.sum()), 100 * cl0.sum() / max(ok0.sum(), 1)))

    # 名目 5 % を下回った。検定が保守的なのか、たまたまか —— z の散らばりで測る。
    zz = (d0 / np.maximum(l0 / 1.96, 1e-12))[ok0]
    print("\n  ★実測 %.1f %% は名目 5 %% を下回る。理由を測る: 帰無仮説のもとでの "
          "z の標準偏差は %.3f(1.0 のはず)。" % (100 * sig0.sum() / max(ok0.sum(), 1),
                                                float(zz.std(ddof=1))))
    print("     σ は**面そのものの形と粗さ**を測っているが、面は 2 時期で同じなので"
          "その大半は差を取ると消える。LoD は雑音を多めに見積もり、検定は保守側に"
          "倒れる(実測の差の σ %.3f mm vs LoD/1.96 の中央値 %.3f mm)。"
          % (float(d0[ok0].std(ddof=1)), float(np.nanmedian(l0) / 1.96)))

    sig, d, lod = mv["sig"], mv["d"], mv["lod"]
    bh = bh_reject(pvalues(zscore(d, lod)))
    cl = cluster_filter(sig, nx, ny)
    print("\n  同じ規則を本番(沈下あり)に掛けると:")
    for name, s in (("|d| > LoD", sig), ("+ BH", bh), ("+ 塊の規則", cl)):
        cm = confusion(s, s_mm)
        print("   %-24s 有意 %3d   TPR %5.1f %%   FPR %5.1f %%"
              % (name, int(s.sum()), cm["tpr"], cm["fpr"]))
    print("\n  ★偽陽性は %d -> %d(BH)/ %d(塊)に落ちるのに、TPR は %.1f -> %.1f / "
          "%.1f %% しか下がらない。"
          % (int(sig0.sum()), int(bh0.sum()), int(cl0.sum()), mv["cm"]["tpr"],
             confusion(bh, s_mm)["tpr"], confusion(cl, s_mm)["tpr"]))
    assert int(bh0.sum()) < int(sig0.sum()), (bh0.sum(), sig0.sum())
    return {"sig0": int(sig0.sum()), "bh0": int(bh0.sum()), "cl0": int(cl0.sum()),
            "n0": int(ok0.sum()), "bh": bh, "cl": cl,
            "tpr_bh": confusion(bh, s_mm)["tpr"], "tpr_cl": confusion(cl, s_mm)["tpr"]}


# --------------------------------------------------------------------------- #
# 7. 合わせの残差は LoD に入っていない                                          #
# --------------------------------------------------------------------------- #
DZ_BIAS = -0.0007


def section_registration(sc: dict, mult: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) 合わせの残差 —— LoD は雑音しか見ていない(Lague 原論文の限界そのもの)")
    print("=" * 78)
    cores, s_mm, nx, ny = sc["cores"], sc["s_mm"], sc["nx"], sc["ny"]
    a, b = make_clouds(settle=False, dz=DZ_BIAS)
    n_fit, _ = fitted_normals(a, cores)
    d, lod = m3c2(a, b, cores, n_fit)
    d, lod = d * 1000.0, lod * 1000.0
    ok = np.isfinite(d)
    sig = ok & (np.abs(d) > lod)
    bh = bh_reject(pvalues(zscore(d, lod)))
    cl = cluster_filter(sig, nx, ny)

    print("  対照群: 沈下ゼロ + 鉛直に %.2f mm の合わせ残差。真の沈下は 0。"
          % (DZ_BIAS * 1000))
    print("   平均の差 %.2f mm(真値 0)、有意な core %d/%d (%.1f %%)"
          % (np.nanmean(d), int(sig.sum()), int(ok.sum()),
             100 * sig.sum() / max(ok.sum(), 1)))
    print("   BH %d / 塊の規則 %d —— ★**どちらも効かない**。系統誤差は"
          "多重比較の問題ではない。" % (int(bh.sum()), int(cl.sum())))
    print("   (比較: 残差ゼロの対照群は 有意 %d / BH %d / 塊 %d)"
          % (mult["sig0"], mult["bh0"], mult["cl0"]))

    # 安定域(切羽の前方)の中央値で較正する
    stable = cores[:, 0] > X_FACE + 2.0 * I_LONG
    off = float(np.nanmedian(d[stable & ok]))
    d_cal = d - off
    sig_cal = ok & (np.abs(d_cal) > lod)
    print("\n  安定域(x > %.1f m、%d core)の中央値 %.2f mm を引いて較正すると:"
          % (X_FACE + 2.0 * I_LONG, int(stable.sum()), off))
    print("   有意な core %d -> %d (%.1f %%)。平均 %.2f -> %.2f mm。"
          % (int(sig.sum()), int(sig_cal.sum()),
             100 * sig_cal.sum() / max(ok.sum(), 1), np.nanmean(d), np.nanmean(d_cal)))
    print("  ★LoD を報告するときは『雑音に対する検出限界であって、"
          "合わせの残差は別勘定』と書かないと嘘になる。")
    assert int(sig.sum()) > 3 * mult["sig0"], (sig.sum(), mult["sig0"])
    assert int(sig_cal.sum()) < int(sig.sum())

    figs.save_grid("map_bias",
                   [d.reshape(nx, ny).T, sig.reshape(nx, ny).T.astype(np.float64),
                    sig_cal.reshape(nx, ny).T.astype(np.float64)],
                   ["合わせ残差 %.2f mm だけの差 [mm]" % (DZ_BIAS * 1000),
                    "有意 %d core(沈下は 0 なのに)" % int(sig.sum()),
                    "安定域で較正した後 %d core" % int(sig_cal.sum())],
                   ncols=1, signed=[True, False, False],
                   title="沈下ゼロ + 合わせ残差 %.2f mm の対照群" % (DZ_BIAS * 1000),
                   caption="LoD は雑音しか見ていないので、系統誤差はそのまま"
                           "「有意な沈下」として通る。BH も塊の規則も効かない。")
    return {"n_sig": int(sig.sum()), "n_bh": int(bh.sum()), "n_cl": int(cl.sum()),
            "n_cal": int(sig_cal.sum()), "mean": float(np.nanmean(d)), "off": off}


# --------------------------------------------------------------------------- #
# 8. 有意なものだけ足すと体積は過小になる                                       #
# --------------------------------------------------------------------------- #
def section_volume(sc: dict, mv: dict) -> dict:
    print("\n" + "=" * 78)
    print("8) 有意なものだけ足すと体積は必ず過小 —— 量は先に計算できる")
    print("=" * 78)
    d, sig, ok, s_mm = mv["d"], mv["sig"], mv["ok"], sc["s_mm"]
    cell = CORE_STEP ** 2
    v_true = sc["vol"]
    v_all = -float(np.nansum(d[ok])) / 1000.0 * cell
    v_sig = -float(np.nansum(d[sig])) / 1000.0 * cell
    v_truth_core = -float(np.sum(s_mm)) / 1000.0 * cell

    # 予測 1: 横断ガウスを LoD(中央値 1 個)で切ったときに残る割合(閉形式)
    lod_med = float(np.nanmedian(mv["lod"]))
    ratio_cf = float(erf(math.sqrt(max(math.log(S_MAX * 1000 / lod_med), 0.0))))
    # 予測 2: 真の場を LoD 中央値で切って数値積分(縦断の立ち上がりも入る)
    xg = np.linspace(0.0, AREA_X, 601)
    yg = np.linspace(0.0, AREA_Y, 401)
    S = np.abs(settlement(*np.meshgrid(xg, yg, indexing="ij"))) * 1000.0
    ratio_num = float(S[S > lod_med].sum() / S.sum())
    # 予測 3: LoD は場所ごとに違う。core ごとの LoD で切る(測った距離は使わない)
    st, ld = np.abs(s_mm), mv["lod"]
    ratio_core = float(st[st > ld].sum() / st.sum())

    print("  core 格子で足した体積(cell %.2f m2)"
          % cell)
    print("   真値(閉形式の積分)          %.4f m3" % v_true)
    print("   真値(core 格子で足す)        %.4f m3  (%+.1f %%、格子の粗さ)"
          % (v_truth_core, 100 * (v_truth_core - v_true) / v_true))
    print("   全 core を足す                %.4f m3  (%+.1f %%)"
          % (v_all, 100 * (v_all - v_true) / v_true))
    print("   有意な core だけ足す          %.4f m3  (%+.1f %%)"
          % (v_sig, 100 * (v_sig - v_true) / v_true))
    print("\n   残る割合 実測                                   %.3f" % (v_sig / v_all))
    print("     予測1 閉形式 erf(sqrt(ln(S_max/LoD中央値)))     %.3f" % ratio_cf)
    print("     予測2 真の場を LoD 中央値で切って数値積分       %.3f" % ratio_num)
    print("     予測3 **core ごとの LoD** で切る                %.3f" % ratio_core)
    print("  ★『有意でない』は『ゼロ』ではない。有意なものだけ足すと "
          "%.1f %% 足りない —— しかもその量は LoD から**先に計算できる**。"
          % (100 * (1.0 - v_sig / v_all)))
    print("  ★LoD を 1 個の数字(中央値)で代表すると欠け量を %.1f 倍**過小に**"
          "見積もる。粗い場所ほど LoD が大きく、そこの沈下がまるごと落ちるから ——"
          % ((1 - ratio_num) and (1 - ratio_core) / (1 - ratio_num)))
    print("     欠け量の予測にも**LoD の地図**が要る(予測 3 は実測と %.1f %% 差)。"
          % (100 * abs(ratio_core - v_sig / v_all)))
    assert abs(ratio_core - v_sig / v_all) < 0.05, (ratio_core, v_sig / v_all)
    return {"v_true": v_true, "v_all": v_all, "v_sig": v_sig,
            "ratio": v_sig / v_all, "ratio_cf": ratio_cf, "ratio_num": ratio_num,
            "ratio_core": ratio_core, "lod_med": lod_med}


# --------------------------------------------------------------------------- #
# 9. 崖 —— 沈下量と点密度を振る                                                 #
# --------------------------------------------------------------------------- #
def section_cliff(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("9) 崖 —— どれだけ沈めば、どれだけ撒けば有意になるか")
    print("=" * 78)
    cores, nx, ny = sc["cores"], sc["nx"], sc["ny"]

    print("   最大沈下 mm   舗装ゾーンの検出率   全体の有意率   平均 [mm]")
    smax_l, rate_l = [], []
    for s in (1.0, 2.0, 4.0, 8.0, 16.0):
        a, b = make_clouds(settle=True, s_max=s / 1000.0)
        n_fit, _ = fitted_normals(a, cores)
        d, lod = m3c2(a, b, cores, n_fit)
        d, lod = d * 1000.0, lod * 1000.0
        s_mm = settlement(cores[:, 0], cores[:, 1], s / 1000.0) * 1000.0
        ok = np.isfinite(d)
        sig = ok & (np.abs(d) > lod)
        band = (zone_of(cores[:, 1]) == 1) & (np.abs(s_mm) >= 0.5 * s)
        rate = 100.0 * np.count_nonzero(sig & band) / max(int(band.sum()), 1)
        smax_l.append(s)
        rate_l.append(rate)
        print("     %5.1f          %6.1f %%            %5.1f %%      %7.2f"
              % (s, rate, 100 * sig.sum() / max(ok.sum(), 1), np.nanmean(d)))

    print("\n   点密度 x    LoD 中央値 mm   予測 (1/sqrt) mm   有意率")
    dens_l, lod_l, pred_l = [], [], []
    lod_ref = None
    for f in (0.25, 0.5, 1.0, 2.0):
        a, b = make_clouds(settle=True, dens_scale=f)
        n_fit, _ = fitted_normals(a, cores)
        d, lod = m3c2(a, b, cores, n_fit)
        d, lod = d * 1000.0, lod * 1000.0
        ok = np.isfinite(d)
        sig = ok & (np.abs(d) > lod)
        med = float(np.nanmedian(lod))
        if lod_ref is None:
            lod_ref = med * math.sqrt(0.25)
        pred = lod_ref / math.sqrt(f)
        dens_l.append(f)
        lod_l.append(med)
        pred_l.append(pred)
        print("     %.2f         %6.2f          %6.2f         %5.1f %%"
              % (f, med, pred, 100 * sig.sum() / max(ok.sum(), 1)))

    r = [a / b for a, b in zip(lod_l, pred_l)]
    print("\n  ★LoD は点密度の平方根で落ちる(実測/予測 %.2f 〜 %.2f)。"
          "**4 倍撒いて半分**。" % (min(r), max(r)))
    print("  ★検出率は %.1f mm で %.1f %%、%.1f mm で %.1f %% —— 崖は LoD の"
          "あたり(舗装ゾーンの LoD 中央値 %.2f mm)。"
          % (smax_l[1], rate_l[1], smax_l[2], rate_l[2], lod_l[2]))
    assert max(r) < 1.2 and min(r) > 0.8, r

    figs.save_plot("cliff",
                   [("舗装ゾーンの検出率 [%]", smax_l, rate_l),
                    ("50 % の線", smax_l, [50.0] * len(smax_l))],
                   xlabel="最大沈下 [mm]", ylabel="有意と判定できた割合 [%]",
                   kinds=["scatter", "line"],
                   title="どれだけ沈めば有意になるか(舗装ゾーン)",
                   caption="崖の位置はそのゾーンの LoD で決まる。粗い路肩なら"
                           "同じ沈下でも崖はもっと右にある。")
    figs.save_plot("density",
                   [("LoD 実測", dens_l, lod_l), ("予測 1/sqrt(密度)", dens_l, pred_l)],
                   xlabel="点密度の倍率", ylabel="LoD の中央値 [mm]",
                   kinds=["scatter", "line"],
                   title="LoD は点密度の平方根で落ちる",
                   caption="4 倍撒くと LoD は半分。撒く量を決めるのはこの式。")
    return {"smax": smax_l, "rate": rate_l, "dens": dens_l, "lod": lod_l,
            "pred": pred_l, "ratio": r}


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("10) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    assert hasattr(fs.ledger, "chamfer_distance")
    assert not hasattr(fs.ledger, "c2c_distance") and not hasattr(fs, "c2c_distance")
    print("  (a) C2C(点ごと / core ごとの最近傍距離)を**地図として**返す口が無い。"
          "chamfer_distance はスカラー 1 個だけ。ゼロ点を出すのに scipy を書いた。")

    assert not hasattr(fs.ledger, "m3c2_significance")
    print("  (b) m3c2_distance は (distance, lod) を返すが、**有意判定・p 値・"
          "FDR・塊の規則**が無い。6 節はこの PoC の中で書いている ——"
          "「測った」から「言い切れる」への変換がライブラリの外にある。")

    for nm in ("bh_fdr", "benjamini_hochberg", "multiple_test"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (c) 多重比較の補正(BH / Bonferroni)が無い。core を 1 個増やすたびに"
          "検定が 1 回増える道具を出しているのだから、族に入る価値がある。")

    assert not hasattr(fs.ledger, "core_normals") and not hasattr(fs, "core_normals")
    print("  (d) **core ごとの法線**を作る口が無い。estimate_normals は点ごとで、"
          "core 格子に対しては自前で平面を当てるしかない(5 節のとおり"
          "ここを鉛直で代用すると LoD が %.1f 倍になる)。" % (CROSS * RADIUS * 1e3 / 2))

    assert not hasattr(fs.ledger, "volume_from_core_field")
    print("  (e) core の場から**体積**を出す口が無い(格子の cell を掛けて足す"
          "だけだが、欠測 core の扱いと有意性の扱いで答えが 20 % 変わる)。")

    assert not hasattr(fs.ledger, "register_by_stable_region")
    print("  (f) **安定域を指定して合わせの残差を較正する**口が無い。7 節のとおり"
          "LoD だけでは系統誤差に無力なので、ここが実務では本体。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("沈下したのか、測り直しただけなのか —— 検出限界(LoD)で切る")
    print("区画 %.0f x %.0f m / 最大沈下 %.1f mm / 測距雑音 %.1f mm" % (
        AREA_X, AREA_Y, S_MAX * 1000, SIGMA_RANGE * 1000))
    print("=" * 78)

    sc = section_scene()
    z = section_zero(sc)
    mv = section_mean_vs_significant(sc, z)
    lodz = section_lod_is_roughness(sc, z, mv)
    nrm = section_normals(sc, z, mv)
    mult = section_multiplicity(sc, z, mv)
    reg = section_registration(sc, mult)
    vol = section_volume(sc, mv)
    cliff = section_cliff(sc)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * C2C は変化ゼロでも中央値 %.2f mm を返す(沈下ありは %.2f mm)。符号も無い。"
          % (np.nanmedian(z["c2c_0"]), np.nanmedian(z["c2c_1"])))
    print("  * 平均は %.2f mm、有意なのは %d/%d core(%.1f %%)でその平均は %.2f mm。"
          % (np.nanmean(mv["d"]), int(mv["sig"].sum()), int(mv["ok"].sum()),
             100 * mv["sig"].sum() / max(mv["ok"].sum(), 1),
             float(np.nanmean(mv["d"][mv["sig"]]))))
    print("  * LoD はゾーンで %.2f 〜 %.2f mm(予測との比 %.2f〜%.2f)。沈下ではなく"
          "粗さの地図。" % (min(lodz["meas"]), max(lodz["meas"]),
                            min(lodz["ratio"]), max(lodz["ratio"])))
    print("  * 法線を鉛直にすると LoD %.2f mm、有意 %d core(局所平面なら %d)。"
          % (nrm["lod_up"], nrm["n_up"], int(mv["sig"].sum())))
    print("  * 沈下ゼロで %d/%d core が有意(名目 5 %%)。BH %d / 塊 %d。"
          % (mult["sig0"], mult["n0"], mult["bh0"], mult["cl0"]))
    print("  * 合わせ残差 %.2f mm だけで有意 %d core。BH %d / 塊 %d で**減らない**。"
          "安定域で較正して %d。"
          % (DZ_BIAS * 1000, reg["n_sig"], reg["n_bh"], reg["n_cl"], reg["n_cal"]))
    print("  * 有意なものだけ足すと体積は %.4f -> %.4f m3(残る割合 実測 %.3f / "
          "予測 %.3f)。" % (vol["v_all"], vol["v_sig"], vol["ratio"], vol["ratio_num"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
