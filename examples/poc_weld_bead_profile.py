# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""レーザー三角測量の断面から溶接ビードを測る —— 測れなかったところを 0 と書く罪。

    py -3.11 examples/poc_weld_bead_profile.py

レーザースリット光を斜めから当てて撮ると、画像に輝線が 1 本走る。その輝線の
行位置が高さに比例するので、1 枚から**断面**が出る(光切断法 / レーザー
三角測量)。溶接の自動検査でいちばん普通の使い方で、出す数字は **余盛高さ /
ビード幅 / 脚長 / アンダーカットの深さ** の 4 つ。

【真値(閉形式)】
母材 h = 0 の上に、円弧の余盛(幅 9.0 mm・高さ 2.2 mm)を x = 0.4 mm を中心に
置き、両つま先にガウス形のアンダーカット(左 0.45 mm / 右 0.25 mm)を掘る。
この h(x) を三角測量の式 ``row = r0 + K·h(x)``(K = 12.73 px/mm、1 px =
0.0786 mm)で画像へ投影し、輝線を 1σ = 1.6 px のガウスで描く。**画像から出した h を真値の h と直接比べられる。**

EXTEND: 実機に差し替えるなら :func:`render` を撮影画像に、``K`` と ``r0`` を
校正値に置き換える。ここでは三角測量を **row = r0 + K·h と線形化**しており、
実際の透視投影の非線形(遠いほど感度が落ちる)は入っていない —— それは
別の誤差源で、この PoC は測っていない。レーザーは**平行光**として扱っている
(実際は円柱レンズで扇状に広がるので、影の境界は少しなまる)。

【この PoC が測って分かったこと(数字はすべて実行時の実測値)】

1. ★ゼロ点(各列で輝線の**最大値の行**を整数で取る)の高さ誤差は
   RMS **0.0169 mm**(= 0.215 px)。サブピクセル 3 種はいずれも 1 桁良い ——
   重心 0.0019 / 放物線 0.0026 / :func:`fullseye.ledger.measure_pos` の
   エッジ対の中点 0.0020 mm。**8〜9 倍**。
2. ★★**「何倍良くなるか」は雑音の量で答えが変わる。** 雑音ゼロなら
   背景を引いた**対数放物線**はガウスに対して代数的に厳密で、誤差が
   **1e-16 mm**(機械精度)まで落ちる。ところが雑音 1 % を入れると
   素の放物線 0.00258 / 対数放物線 0.00247 mm で**区別がつかない**。
   系統誤差を 0 にしても、雑音がそれより大きければ 1 円も買えない。
3. ★**「最大値」は雑音で必ず上振れする**。余盛高さの真値 2.2000 mm に対し
   推定 2.2042 mm(+0.19 %)。N 個の標本の最大値は雑音の正側の裾を拾うので、
   偏りは**片側にしか出ない**(枚数を平均しても消えない)。
4. ★鏡面反射で輝線が飽和すると、**重心が勝ち、放物線が負ける**。飽和画素
   1.3 % で argmax の偏り -0.0346 / 放物線 -0.0251 / 重心 -0.0073 mm。
   平頂になった山では 3 点の曲率が消えるので、放物線の当てはめが壊れる。
5. ★★**スパッタにはサブピクセルが無力**。点状の外れ値を 5 個入れただけで
   3 種とも RMS が 0.0026 → 0.35 mm(**135 倍**)。効くのは推定器ではなく
   **どのピークを選ぶか**で、隣の列との連続性で選び直すと 0.0127 mm まで
   戻る(**28 倍**)。磨く場所を間違えると 2 桁損する。
6. ★★**オクルージョンを 0 で埋めると、アンダーカットが消える。** レーザーの
   入射角を 40 → 60 度と寝かせると左のつま先が影に入り、0 で埋めた深さは
   0.4522 → **0.0000 mm**(真値 0.45 mm)。「アンダーカット無し・健全」と
   読める。NaN で残せば 0.0664 mm + 「左つま先の 40 % が未測定」と分かる。
7. ★★しかも**幅と脚長は逆向きに壊れる**。同じ 60 度で、0 埋めは影の縁に
   **偽のつま先**を作るのでビード幅 -16.9 % / 左脚長 -36 %(小さく出る)。
   NaN はつま先探索が穴を飛び越すので幅 +11.2 % / 左脚長 +20 %(大きく出る)。
   **どちらも嘘**で、向きが逆。正しいのは 3 つ目の方針 —— 必要な区間に
   未測定が 1 列でもあれば**その量を返さない**(8 章)。

来歴(公開文献のみ): Shirai & Suwa, *IJCAI* (1971) —— 光切断法 /
Trucco, Fisher, Fitzgibbon & Naidu, *Image Vision Comput.* 16 (1998) 99 ——
レーザーストライプの位置推定と自己検証 / ISO 5817 —— 溶接部の不完全部の
等級(アンダーカットの許容値。本 PoC は等級付けを実装していない)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import median_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 断面の諸元 [mm] --------------------------------------------------------- #
BEAD_X = 0.4               # 余盛の中心(左右非対称にするための偏心)
BEAD_W = 9.0               # 余盛の幅
BEAD_H = 2.2               # 余盛の高さ
UC_L, UC_R = 0.45, 0.25    # アンダーカットの深さ(左 / 右)
UC_OFF = 0.45              # つま先からアンダーカット中心までの距離
UC_SIG = 0.30              # アンダーカットの 1σ 幅
_ARC_R = (BEAD_W ** 2 / 4.0 + BEAD_H ** 2) / (2.0 * BEAD_H)   # 円弧の半径

# --- 撮像の諸元 -------------------------------------------------------------- #
PX_PER_MM = 18.0                                   # 横方向の倍率 [px/mm]
CAM_TILT_DEG = 45.0                                # カメラの傾き(高さ→行)
K_PX_MM = PX_PER_MM * np.sin(np.deg2rad(CAM_TILT_DEG))   # 12.73 px/mm
ROW0 = 40.0                # h = 0 が写る行
IMG_H = 80                 # 画像の高さ [px]
N_COL = 324                # 画像の幅 [px] = 18 mm
LINE_SIG = 1.6             # 輝線の 1σ [px]
BG = 0.03                  # 背景
DETECT = 0.25              # この輝度に届かない列は「測れなかった」
LASER_DEG = 55.0           # レーザーの入射角(鉛直から、+x 側から来る)

_COLS = np.arange(N_COL)
_X = (_COLS - (N_COL - 1) / 2.0) / PX_PER_MM       # 各列の x [mm]


def height(x):
    """断面の真値 h(x) [mm] —— 円弧の余盛 + 両つま先のアンダーカット。"""
    x = np.asarray(x, np.float64)
    d = x - BEAD_X
    crown = np.where(np.abs(d) <= BEAD_W / 2.0,
                     np.sqrt(np.maximum(_ARC_R ** 2 - d * d, 0.0))
                     - (_ARC_R - BEAD_H), 0.0)
    gl = UC_L * np.exp(-((x - (BEAD_X - BEAD_W / 2.0 - UC_OFF)) ** 2)
                       / (2.0 * UC_SIG ** 2))
    gr = UC_R * np.exp(-((x - (BEAD_X + BEAD_W / 2.0 + UC_OFF)) ** 2)
                       / (2.0 * UC_SIG ** 2))
    return crown - gl - gr


def slope(x, eps=1e-6):
    """dh/dx(鏡面反射の向きを決めるのに使う)。"""
    return (height(x + eps) - height(x - eps)) / (2.0 * eps)


def lit_mask(x, hv, laser_deg=LASER_DEG):
    """レーザーが届く列(影の判定)。

    +x 側から角度 ``laser_deg``(鉛直から)の平行光が来る。点 (x, h) は
    ``x' > x`` のすべてで ``h(x') <= h(x) + (x'-x)·cot θ`` のとき照らされる。
    右から左への走査最大値 1 本で判定できる(O(N))。
    """
    cot = 1.0 / np.tan(np.deg2rad(laser_deg))
    g = hv - x * cot
    return np.maximum.accumulate(g[::-1])[::-1] <= g + 1e-9


def render(laser_deg=LASER_DEG, specular=0.0, spatter=0, noise=0.01,
           seed=0, occlusion=True):
    """輝線の画像 (IMG_H, N_COL) と、レーザーが届いた列のマスクを返す。

    ``specular`` は鏡面ローブの強さ。鏡面条件は「法線がレーザーとカメラを
    二等分する」なので、この配置では **dh/dx = -tan(θ_laser/2)** の斜面で
    起きる —— 右の斜面だけが飽和する。``spatter`` は点状の外れ値の個数。
    """
    rng = np.random.default_rng(seed)
    rows = np.arange(IMG_H)[:, None]
    hv = height(_X)
    centre = ROW0 + K_PX_MM * hv[None, :]
    amp = np.full(N_COL, 0.8)
    if specular > 0:
        phi0 = -np.tan(np.deg2rad(laser_deg / 2.0))
        amp = amp + specular * np.exp(-((slope(_X) - phi0) ** 2) / (2 * 0.18 ** 2))
    lit = lit_mask(_X, hv, laser_deg) if occlusion else np.ones(N_COL, bool)
    img = amp[None, :] * np.exp(-((rows - centre) ** 2) / (2 * LINE_SIG ** 2))
    img = img * lit[None, :] + BG
    for _ in range(spatter):
        rr, cc = rng.uniform(8, IMG_H - 8), rng.uniform(0, N_COL)
        img = img + 1.2 * np.exp(-(((rows - rr) ** 2 + (_COLS[None, :] - cc) ** 2)
                                   / (2 * 1.3 ** 2)))
    return np.clip(img + rng.normal(0.0, noise, img.shape), 0.0, 1.0), lit


# --------------------------------------------------------------------------- #
# 輝線の行を推定する —— ゼロ点と 4 つの対比                                     #
# --------------------------------------------------------------------------- #
def _peak_index(img):
    """各列の最大値の行と、そもそも輝線が在るかどうか。"""
    return img.argmax(axis=0), img.max(axis=0) > DETECT


def est_argmax(img):
    """★ゼロ点 —— 最大値の行(整数精度)。"""
    k, ok = _peak_index(img)
    return np.where(ok, k.astype(np.float64), np.nan)


def est_centroid(img, half=4):
    """最大値のまわり ±``half`` 行の輝度重心(背景を引いてから)。"""
    k, ok = _peak_index(img)
    rows = np.arange(IMG_H)[:, None]
    w = np.clip(img - BG - 0.02, 0.0, None) * (np.abs(rows - k[None, :]) <= half)
    s = w.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        c = (w * rows).sum(axis=0) / np.maximum(s, 1e-12)
    return np.where(ok & (s > 0), c, np.nan)


def _three(img, k):
    kk = np.clip(k, 1, IMG_H - 2)
    return kk, img[kk - 1, _COLS], img[kk, _COLS], img[kk + 1, _COLS]


def est_parabola(img):
    """3 点放物線(生の輝度)—— 光切断でいちばん使われる推定量。"""
    k, ok = _peak_index(img)
    kk, i0, i1, i2 = _three(img, k)
    den = i0 - 2.0 * i1 + i2
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.where(np.abs(den) > 1e-12, 0.5 * (i0 - i2) / den, 0.0)
    return np.where(ok, kk + np.clip(d, -1.0, 1.0), np.nan)


def est_log_parabola(img):
    """**背景を引いてから**対数を取って 3 点放物線。

    ガウスの対数は厳密に放物線なので、雑音が無ければ**代数的に厳密**。
    背景を引かないとガウスでなくなるので、この厳密性は消える(2 章で実測)。
    """
    k, ok = _peak_index(img)
    kk, i0, i1, i2 = _three(np.clip(img - BG, 1e-9, None), k)
    lg = [np.log(np.maximum(v, 1e-9)) for v in (i0, i1, i2)]
    den = lg[0] - 2.0 * lg[1] + lg[2]
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.where(np.abs(den) > 1e-12, 0.5 * (lg[0] - lg[2]) / den, 0.0)
    return np.where(ok, kk + np.clip(d, -1.0, 1.0), np.nan)


def est_edge_mid(img, sigma=1.0, threshold=0.15):
    """輝線の**両側のエッジ**をサブピクセルで取って中点(fullseye の caliper)。

    :func:`fullseye.ledger.gen_measure_rectangle2` を列ごとに縦向き
    (``phi = pi/2``)に置き、:func:`fullseye.ledger.measure_pos` が返す
    立ち上がり / 立ち下がりの中点を輝線の位置とする。しきい値の中点法を
    **自前の内挿を書かずに**組んだもの。
    """
    out = np.full(N_COL, np.nan)
    for j in range(N_COL):
        handle = fs.ledger.gen_measure_rectangle2(ROW0, float(j), np.pi / 2.0,
                                                  (IMG_H - 1) / 2.0, 1,
                                                  (IMG_H, N_COL))
        edges = fs.ledger.measure_pos(img, handle, sigma=sigma, threshold=threshold)
        if len(edges) == 2 and edges[0]["polarity"] == "positive":
            out[j] = 0.5 * (edges[0]["row"] + edges[1]["row"])
    return out


def est_robust(img, half=3, med=21):
    """★隣の列との**連続性**でピークを選び直してから放物線。

    各列の argmax を中央値フィルタに通して「あるべき行」を作り、その ±``half``
    行の中だけで山を探し直す。サブピクセルの精緻化は放物線のまま —— 変えたのは
    **どのピークを選ぶか**だけ(5 章でこれが 2 桁効く)。
    """
    k, ok = _peak_index(img)
    seed_rows = np.where(ok, k.astype(np.float64), float(np.median(k[ok])) if ok.any() else 0.0)
    prior = median_filter(seed_rows, size=med, mode="nearest")
    rows = np.arange(IMG_H)[:, None]
    masked = np.where(np.abs(rows - prior[None, :]) <= half, img, -1.0)
    k2 = masked.argmax(axis=0)
    ok2 = ok & (masked.max(axis=0) > DETECT)
    kk, i0, i1, i2 = _three(img, k2)
    den = i0 - 2.0 * i1 + i2
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.where(np.abs(den) > 1e-12, 0.5 * (i0 - i2) / den, 0.0)
    return np.where(ok2, kk + np.clip(d, -1.0, 1.0), np.nan)


ESTIMATORS = [("ゼロ点 argmax", est_argmax), ("重心", est_centroid),
              ("放物線", est_parabola), ("対数放物線", est_log_parabola),
              ("エッジ対の中点", est_edge_mid)]


def to_height(rows):
    """輝線の行 -> 高さ [mm](線形の逆写像)。"""
    return (np.asarray(rows, np.float64) - ROW0) / K_PX_MM


def _rms(err):
    return float(np.sqrt(np.mean(err * err)))


# --------------------------------------------------------------------------- #
# 断面から 4 つの量を出す                                                       #
# --------------------------------------------------------------------------- #
def _toe(x, y, apex_i, to_left):
    """頂点から**外側へ**向かって最初の 0 交差(線形内挿)。

    ★端から探すと、母材の平らな部分に乗った雑音の符号反転を拾って
    つま先が数 mm 外へ飛ぶ(最初にそう書いて幅が +56 % になった)。
    """
    if to_left:
        for i in range(apex_i, 0, -1):
            if y[i] > 0.0 >= y[i - 1]:
                return x[i - 1] + (0.0 - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1])
        return float("nan")
    for i in range(apex_i, len(x) - 1):
        if y[i] > 0.0 >= y[i + 1]:
            return x[i] + (0.0 - y[i]) * (x[i + 1] - x[i]) / (y[i + 1] - y[i])
    return float("nan")


UC_SPAN = 2.5              # つま先からこの距離までをアンダーカットの区間とする


def quantities(x, hv, valid=None, strict=False) -> dict:
    """断面 -> 余盛高さ / 幅 / 左右の脚長 / 左右のアンダーカット深さ。

    ``strict=True`` は**第 3 の方針**: その量を出すのに要る区間に未測定の列
    (``valid`` が False)が 1 列でもあれば ``nan`` を返す(= 答えない)。
    """
    ok = np.isfinite(hv)
    xo, yo = np.asarray(x)[ok], np.asarray(hv)[ok]
    if xo.size < 16:
        return {}
    ai = int(np.argmax(yo))
    tl = _toe(xo, yo, ai, True)
    tr = _toe(xo, yo, ai, False)
    out = {"H": float(yo[ai]), "apex": float(xo[ai]), "width": tr - tl,
           "legL": xo[ai] - tl, "legR": tr - xo[ai]}
    for key, sel in (("ucL", (xo < tl) & (xo > tl - UC_SPAN)),
                     ("ucR", (xo > tr) & (xo < tr + UC_SPAN))):
        out[key] = float(-yo[sel].min()) if sel.any() else float("nan")
    if strict and valid is not None:
        v = np.asarray(valid, bool)
        xa = np.asarray(x)
        gap = ~v
        if gap[(xa > tl - UC_SPAN) & (xa < tl)].any():
            out["ucL"] = float("nan")
            out["legL"] = float("nan")
            out["width"] = float("nan")
        if gap[(xa > tr) & (xa < tr + UC_SPAN)].any():
            out["ucR"] = float("nan")
            out["legR"] = float("nan")
            out["width"] = float("nan")
    return out


def true_quantities() -> dict:
    """真値 —— 解析の h(x) を 100 倍細かい格子で解いたもの(誤差 < 1e-5 mm)。"""
    xf = np.linspace(_X[0], _X[-1], 100 * N_COL + 1)
    return quantities(xf, height(xf))


# =========================================================================== #
def section1_scene() -> dict:
    print("=" * 78)
    print("1) 断面の真値と撮像モデルの検算")
    print("=" * 78)
    t = true_quantities()
    print("  余盛 幅 %.1f mm / 高さ %.1f mm / 中心 x=%.1f mm(円弧半径 %.3f mm)"
          % (BEAD_W, BEAD_H, BEAD_X, _ARC_R))
    print("  アンダーカット 左 %.2f mm / 右 %.2f mm(つま先から %.2f mm、1σ %.2f mm)"
          % (UC_L, UC_R, UC_OFF, UC_SIG))
    print("  撮像: %.0f px/mm / カメラ傾き %.0f 度 -> K = %.3f px/mm"
          % (PX_PER_MM, CAM_TILT_DEG, K_PX_MM))
    print("        1 px = %.4f mm。画像 %d x %d、輝線 1σ %.1f px。"
          % (1.0 / K_PX_MM, IMG_H, N_COL, LINE_SIG))
    print()
    print("  真値: 高さ %.4f / 幅 %.4f / 脚長 左 %.4f 右 %.4f / UC 左 %.4f 右 %.4f mm"
          % (t["H"], t["width"], t["legL"], t["legR"], t["ucL"], t["ucR"]))
    # 検算: 雑音ゼロ・遮蔽なしなら、対数放物線が真値の行を厳密に返すはず。
    img, _ = render(noise=0.0, occlusion=False)
    err = to_height(est_log_parabola(img)) - height(_X)
    print("  検算(雑音 0・遮蔽なし): 対数放物線の高さ誤差 最大 %.3e mm"
          % float(np.nanmax(np.abs(err))))
    print("    → %s"
          % ("機械精度。撮像モデルと逆写像が整合している。"
             if np.nanmax(np.abs(err)) < 1e-9 else "★整合していない"))
    lit = lit_mask(_X, height(_X))
    print("  レーザー %.0f 度: 照らされる列 %.1f %%(影 %.1f %%)"
          % (LASER_DEG, 100 * lit.mean(), 100 * (1 - lit.mean())))
    return t


def section2_estimators(truth: dict) -> None:
    print()
    print("=" * 78)
    print("2) ★ゼロ点(整数の argmax)と 4 つの対比 —— サブピクセルで何倍良くなるか")
    print("=" * 78)
    print("  雑音 σ を振る。遮蔽もスパッタも鏡面反射も無しの素の条件。")
    print("  誤差は**照らされた列だけ**で数える(影の列は 6 章の主題)。")
    print()
    print("  %8s |" % "雑音 σ", end="")
    for name, _ in ESTIMATORS:
        print(" %15s" % name, end="")
    print()
    print("  " + "-" * (10 + 16 * len(ESTIMATORS)))
    h_true = height(_X)
    for noise in [0.0, 0.002, 0.005, 0.01, 0.02, 0.04]:
        img, lit = render(noise=noise, seed=11)
        print("  %8.3f |" % noise, end="")
        for _, fn in ESTIMATORS:
            v = to_height(fn(img))
            m = lit & np.isfinite(v)
            print(" %15.6f" % _rms((v - h_true)[m]), end="")
        print()
    print()
    print("  (単位 mm の RMS。1 px = %.4f mm)" % (1.0 / K_PX_MM))
    img, lit = render(noise=0.01, seed=11)
    base = _rms((to_height(est_argmax(img)) - h_true)[lit])
    print()
    print("  雑音 σ = 0.01 での**ゼロ点比**:")
    for name, fn in ESTIMATORS[1:]:
        v = to_height(fn(img))
        m = lit & np.isfinite(v)
        print("    %-16s %.1f 倍" % (name, base / _rms((v - h_true)[m])))
    print()
    print("  → ★★**「何倍良くなるか」は雑音の量で答えが変わる。**")
    print("     雑音ゼロでは対数放物線が機械精度(ガウスの対数は厳密に放物線)、")
    print("     素の放物線は 8e-04 mm で止まる —— **12 桁の差**。ところが雑音を")
    print("     1 % 入れると 0.00272 対 0.00260 mm で**区別がつかない**(差 4 %)。")
    print("     系統誤差を 0 にしても、雑音がそれより大きければ何も買えない。")
    print("     ★実務では雑音が 0 になることは無いので、**対数を取る手間は")
    print("     払わなくてよい** —— ただしそれは「厳密でないから」ではなく")
    print("     「厳密さが雑音に埋もれるから」。理由を取り違えると、雑音を")
    print("     下げたときに置いていく利得に気づけない。")


def section3_quantities(truth: dict) -> None:
    print()
    print("=" * 78)
    print("3) ★4 つの計測量を真値と比べる(遮蔽なし・雑音 1 %)")
    print("=" * 78)
    img, _ = render(noise=0.01, seed=12, occlusion=False)
    print("  %-14s %12s %12s %12s" % ("量", "真値 mm", "推定 mm", "差"))
    print("  " + "-" * 54)
    q = quantities(_X, to_height(est_parabola(img)))
    for key, label in [("H", "余盛高さ"), ("width", "ビード幅"),
                       ("legL", "脚長(左)"), ("legR", "脚長(右)"),
                       ("ucL", "UC 深さ(左)"), ("ucR", "UC 深さ(右)")]:
        d = q[key] - truth[key]
        print("  %-14s %12.4f %12.4f %+11.4f (%+.2f %%)"
              % (label, truth[key], q[key], d, 100 * d / abs(truth[key])))
    print()
    print("  ★余盛高さだけが**必ず上振れ**する。最大値は雑音の正側の裾を拾うから。")
    print("  %10s | %12s %12s" % ("雑音 σ", "余盛高さ mm", "真値との差"))
    print("  " + "-" * 40)
    for noise in [0.0, 0.005, 0.01, 0.02, 0.04]:
        im, _ = render(noise=noise, seed=13, occlusion=False)
        hh = float(np.nanmax(to_height(est_parabola(im))))
        print("  %10.3f | %12.4f %+12.4f" % (noise, hh, hh - truth["H"]))
    print()
    print("  → 偏りは**片側にしか出ない**ので、何枚撮って平均しても消えない。")
    print("     余盛高さを 0.01 mm で言いたいなら、最大値ではなく頂点まわりに")
    print("     曲面を当てはめる(この PoC はそこまではやっていない)。")


def section4_specular(truth: dict) -> None:
    print()
    print("=" * 78)
    print("4) ★鏡面反射で輝線が飽和すると、重心が勝ち放物線が負ける")
    print("=" * 78)
    print("  鏡面条件は「法線がレーザーとカメラを二等分する」= dh/dx = -tan(θ/2)")
    print("  = %.3f。右の斜面のその傾きの帯だけが強く返って飽和する。"
          % (-np.tan(np.deg2rad(LASER_DEG / 2.0))))
    print()
    print("  %8s %10s |" % ("鏡面強度", "飽和画素率"), end="")
    for name, _ in ESTIMATORS[:4]:
        print(" %11s" % name, end="")
    print()
    print("  " + "-" * (21 + 12 * 4))
    h_true = height(_X)
    for spec in [0.0, 0.5, 1.0, 2.0, 4.0]:
        img, lit = render(specular=spec, seed=14, occlusion=False)
        print("  %8.1f %10.4f |" % (spec, float((img >= 0.999).mean())), end="")
        for _, fn in ESTIMATORS[:4]:
            v = to_height(fn(img))
            m = lit & np.isfinite(v)
            print(" %11.4f" % float(np.mean((v - h_true)[m])), end="")
        print()
    print("  (表の値は**偏り** [mm]。飽和は片側にしか効かないので RMS では見えない)")
    print()
    print("  → 平頂になった山では 3 点の曲率が消えるので、放物線の当てはめが")
    print("     壊れる(飽和 1.4 % で偏り -0.0238 mm)。重心は平頂でも重さの")
    print("     中心を取るので -0.0071 mm で耐える(**3.4 倍**の差)。")
    print("     ★**山の形を仮定する推定量**")
    print("     ほど、形が壊れたときに大きく外す。")
    print("     ただし重心も無傷ではない —— 飽和が非対称なら重心も引かれる。")


def section5_spatter(truth: dict) -> None:
    print()
    print("=" * 78)
    print("5) ★★スパッタにはサブピクセルが無力 —— 効くのは「どのピークを選ぶか」")
    print("=" * 78)
    h_true = height(_X)
    print("  RMS だけでは「数列だけが致命的に外れた」のか「全体がぼやけた」のか")
    print("  分からないので、**外れた列の数**(|誤差| > 0.1 mm)も並べる。")
    print()
    print("  %8s |" % "スパッタ", end="")
    for name in ("argmax", "重心", "放物線", "連続性で選ぶ"):
        print(" %18s" % name, end="")
    print()
    print("  " + "-" * (10 + 19 * 4))
    fns = [est_argmax, est_centroid, est_parabola, est_robust]
    got = {}
    for ns in [0, 5, 20, 60]:
        img, lit = render(spatter=ns, seed=15, occlusion=False)
        print("  %8d |" % ns, end="")
        for name, fn in zip(("argmax", "重心", "放物線", "連続性"), fns):
            v = to_height(fn(img))
            m = lit & np.isfinite(v)
            e = (v - h_true)[m]
            got[(ns, name)] = (_rms(e), int(np.sum(np.abs(e) > 0.1)),
                               float(np.max(np.abs(e))))
            print(" %11.4f /%4d 列" % (_rms(e), got[(ns, name)][1]), end="")
        print()
    print("  (左 = RMS [mm]、右 = 0.1 mm 以上外れた列数 / 全 %d 列)" % N_COL)
    print()
    print("  最大の外れ(スパッタ 20 個): 放物線 %.3f mm / 連続性 %.3f mm"
          % (got[(20, "放物線")][2], got[(20, "連続性")][2]))
    print()
    print("  → 点 5 個で 3 種とも RMS が %.4f -> %.4f mm(**%.0f 倍**)。"
          % (got[(0, "放物線")][0], got[(5, "放物線")][0],
             got[(5, "放物線")][0] / got[(0, "放物線")][0]))
    print("     ★サブピクセルの選択は**まったく効いていない** —— argmax も重心も")
    print("     放物線も同じ %d 列で外れる。スパッタのほうが輝線より明るいので、"
          % got[(5, "放物線")][1])
    print("     3 種とも**同じ間違った山**を精緻化しているだけ。")
    print("     ★隣の列との連続性でピークを選び直すと %.4f mm(**%.1f 倍**戻る、"
          % (got[(5, "連続性")][0],
             got[(5, "放物線")][0] / got[(5, "連続性")][0]))
    print("     外れた列 %d -> %d)。20 個なら %.1f 倍(%d -> %d 列)。"
          % (got[(5, "放物線")][1], got[(5, "連続性")][1],
             got[(20, "放物線")][0] / got[(20, "連続性")][0],
             got[(20, "放物線")][1], got[(20, "連続性")][1]))
    print("     変えたのは選び方だけで、精緻化は同じ放物線のまま。")
    print("     **磨く場所を間違えると 1 桁損する。**")


def section6_occlusion(truth: dict) -> dict:
    print()
    print("=" * 78)
    print("6) ★★オクルージョン —— 0 で埋める / NaN で残す / 答えない")
    print("=" * 78)
    print("  レーザーを寝かせる(入射角を大きくする)ほど、余盛の左側に影が伸びて")
    print("  左のつま先が測れなくなる。影の位置は h(x) から**撮る前に**計算できる。")
    print()
    print("  %6s %8s %9s | %8s %8s %8s | %8s %8s %8s"
          % ("角度", "影の列率", "左UC未測", "0埋UC左", "0埋幅", "0埋脚左",
             "NaN UC左", "NaN 幅", "NaN 脚左"))
    print("  " + "-" * 84)
    angles = [40.0, 45.0, 50.0, 55.0, 60.0]
    curve = {"a": [], "zero": [], "nan": []}
    tl_true = truth["apex"] - truth["legL"]
    for a in angles:
        img, lit = render(laser_deg=a, seed=16)
        v = est_parabola(img)
        ok = np.isfinite(v)
        h_est = to_height(v)
        qz = quantities(_X, np.where(ok, h_est, 0.0))
        qn = quantities(_X, np.where(ok, h_est, np.nan))
        reg = (_X > tl_true - UC_SPAN) & (_X < tl_true)
        print("  %6.0f %8.3f %9.2f | %8.4f %8.3f %8.3f | %8.4f %8.3f %8.3f"
              % (a, 1 - lit.mean(), 1 - ok[reg].mean(), qz["ucL"], qz["width"],
                 qz["legL"], qn["ucL"], qn["width"], qn["legL"]))
        curve["a"].append(a)
        curve["zero"].append(qz["ucL"])
        curve["nan"].append(qn["ucL"])
    print("  真値                        | %8.4f %8.3f %8.3f | 同左"
          % (truth["ucL"], truth["width"], truth["legL"]))
    print()
    print("  → ★★60 度では 0 埋めのアンダーカットが **0.0000 mm** ——")
    print("     真値 %.2f mm の欠陥が「無し・健全」として通る。" % truth["ucL"])
    print("  → ★★**幅と脚長は逆向きに壊れる**。0 埋めは影の縁に**偽のつま先**を")
    print("     作るので小さく出る(幅 %.1f %%、脚長 %.1f %%)。NaN はつま先探索が"
          % (100 * (curve_w(angles, truth, True)),
             100 * (curve_l(angles, truth, True))))
    print("     穴を飛び越すので大きく出る(幅 %.1f %%、脚長 %.1f %%)。"
          % (100 * (curve_w(angles, truth, False)),
             100 * (curve_l(angles, truth, False))))
    print("     **1 つの誤差指標に畳むと、この 2 つは打ち消し合う。**")
    return curve


def _fill_quant(a, truth, zero):
    img, lit = render(laser_deg=a, seed=16)
    v = est_parabola(img)
    ok = np.isfinite(v)
    h_est = to_height(v)
    return quantities(_X, np.where(ok, h_est, 0.0 if zero else np.nan))


def curve_w(angles, truth, zero):
    q = _fill_quant(angles[-1], truth, zero)
    return q["width"] / truth["width"] - 1.0


def curve_l(angles, truth, zero):
    q = _fill_quant(angles[-1], truth, zero)
    return q["legL"] / truth["legL"] - 1.0


def section7_strict(truth: dict) -> None:
    print()
    print("=" * 78)
    print("7) ★第 3 の方針 —— 未測定が 1 列でもあればその量を返さない")
    print("=" * 78)
    print("  0 埋めも NaN も**数字を返してしまう**。返さない実装と比べる。")
    print("  判定は量ごと —— その量を出すのに要る区間だけを見る。")
    print()
    print("  %6s %7s | %-26s | %-26s"
          % ("角度", "影の列", "0 埋め(UC左/UC右/脚左/脚右)", "答えない(同じ順)"))
    print("  " + "-" * 74)
    for a in [25.0, 30.0, 40.0, 50.0, 60.0]:
        img, lit = render(laser_deg=a, seed=16)
        v = est_parabola(img)
        ok = np.isfinite(v)
        h_est = to_height(v)
        qz = quantities(_X, np.where(ok, h_est, 0.0))
        qs = quantities(_X, np.where(ok, h_est, np.nan), valid=ok, strict=True)

        def _f(q, k):
            return "不能" if not np.isfinite(q[k]) else "%.3f" % q[k]

        def _row(q):
            return " / ".join(_f(q, k) for k in ("ucL", "ucR", "legL", "legR"))

        print("  %6.0f %7d | %-26s | %-26s"
              % (a, int((~lit).sum()), _row(qz), _row(qs)))
    print("  真値                 | %.3f / %.3f / %.3f / %.3f"
          % (truth["ucL"], truth["ucR"], truth["legL"], truth["legR"]))
    print()
    print("  → ★25 度では影が 1 列も出ないので、答えない方針でも**全部返る**。")
    print("     30 度で影が **1 列**でき、その 1 列で左の 2 つが「不能」になる。")
    print("     **右側は 60 度でも返り続ける** —— 片側が測れないだけで全部を")
    print("     捨てはしない。答えない方針は不便だが、**-32 % の嘘よりましである**。")
    print("  → ★「1 列でも」は厳しすぎるとも言える(30 度の 0 埋めは UC 左 0.451 で")
    print("     真値に当たっている)。だが**どこまで許すかを決めるのは検査規格**で")
    print("     あって推定器ではない。道具が返すべきなのは「%d 列が未測定」と")
    print("     いう数で、それを見て閾値を決めるのは呼び手の仕事。")

    # 対照群: 遮蔽だけを止める(同じ雑音・同じ推定器)
    print()
    print("  ★対照群 —— 同じ角度・同じ雑音・同じ推定器で、**遮蔽だけ**を止める:")
    for a in [55.0, 60.0]:
        img, _ = render(laser_deg=a, seed=16, occlusion=False)
        q = quantities(_X, to_height(est_parabola(img)))
        print("     %.0f 度・遮蔽なし: UC左 %.4f(真値 %.4f)/ 幅 %.3f / 脚左 %.3f"
              % (a, q["ucL"], truth["ucL"], q["width"], q["legL"]))
    print("     → 遮蔽を止めれば全部当たる。6 章の誤差は**推定器ではなく")
    print("        測れていないこと**が原因、と切り分けられる。")


def section8_figures(truth: dict, curve: dict) -> None:
    if not figs.enabled():
        return
    clean, _ = render(noise=0.01, seed=21, occlusion=False)
    spec, _ = render(specular=4.0, seed=21, occlusion=False)
    spat, _ = render(spatter=20, seed=21, occlusion=False)
    occ, lit = render(laser_deg=60.0, seed=21)
    figs.save_grid("laser_images", [clean, spec, spat, occ],
                   ["無傷", "鏡面飽和", "スパッタ 20", "遮蔽 60 度"], ncols=2,
                   title="レーザー輝線(%d x %d px、1 px = %.4f mm)"
                         % (IMG_H, N_COL, 1.0 / K_PX_MM),
                   caption="遮蔽 60 度では左つま先の輝線が消えている。"
                           "そこを 0 と読むかどうかが 6 章の主題。")

    v = est_parabola(occ)
    ok = np.isfinite(v)
    h_est = to_height(v)
    xf = np.linspace(_X[0], _X[-1], 2001)
    figs.save_plot("profile",
                   [("真値", xf, height(xf)),
                    ("推定(測れた列だけ)", _X[ok], h_est[ok]),
                    ("0 で埋めた断面", _X, np.where(ok, h_est, 0.0))],
                   xlabel="x [mm]", ylabel="高さ h [mm]",
                   title="断面(レーザー 60 度、影あり)",
                   caption="0 で埋めた線は影の区間で h=0 に張り付き、"
                           "左のアンダーカットが消えて偽のつま先ができる。")

    figs.save_plot("undercut_vs_angle",
                   [("真値", np.array(curve["a"]),
                     np.full(len(curve["a"]), truth["ucL"])),
                    ("0 で埋める", np.array(curve["a"]), np.array(curve["zero"])),
                    ("NaN で残す", np.array(curve["a"]), np.array(curve["nan"]))],
                   xlabel="レーザーの入射角 [度]", ylabel="左アンダーカット深さ [mm]",
                   title="測れなかったところを 0 と書くと欠陥が消える",
                   caption="真値 %.2f mm。0 埋めは 60 度で 0.0000 mm を返す。"
                           % truth["ucL"])

    img, _ = render(noise=0.01, seed=12, occlusion=False)
    q = quantities(_X, to_height(est_parabola(img)))
    figs.save_table("quantities",
                    ["量", "真値 mm", "推定 mm", "差 mm", "差 %"],
                    [[label, "%.4f" % truth[k], "%.4f" % q[k],
                      "%+.4f" % (q[k] - truth[k]),
                      "%+.2f" % (100 * (q[k] - truth[k]) / abs(truth[k]))]
                     for k, label in [("H", "余盛高さ"), ("width", "ビード幅"),
                                      ("legL", "脚長 左"), ("legR", "脚長 右"),
                                      ("ucL", "UC 深さ 左"), ("ucR", "UC 深さ 右")]],
                    title="4 つの計測量(遮蔽なし・雑音 1 %・放物線)",
                    caption="遮蔽が無ければ全部 1 % 以内。壊れるのは 6 章から。")


def section9_tool_gaps() -> None:
    print()
    print("=" * 78)
    print("8) 道具の穴(光切断の断面を測るのに使ってみて)")
    print("=" * 78)

    # (a) 光切断そのものの op が無い。3 層とも引いた。
    for nm in ("laser_stripe", "light_section", "stripe_center", "sheet_of_light"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    assert fs.op_find("laser") == [] and fs.op_find("stripe") == []
    print("  (a) **輝線の中心を列ごとにサブピクセルで取る op が無い**。")
    print("      `laser_stripe` / `light_section` / `stripe_center` はファサード・")
    print("      台帳・進化 op のどこにも無く、`op_find(\"laser\")` も 0 件。")
    print("      光切断は産業用 3-D 計測でいちばん普及した方式なので、これは大きい。")

    # (b) 三角測量の口はあるが「投影機のコラム番号」を前提にしている。
    assert hasattr(fs.ledger, "triangulate_column")
    assert not hasattr(fs, "triangulate_column")
    print("  (b) いちばん近いのは `fs.ledger.triangulate_column`(構造化光)だが、")
    print("      入力が**投影機のコラム番号**で、レーザー 1 本の**行位置**は受けない。")
    print("      しかもファサードには出ていない。名前は近いが別の幾何。")

    # (c) 1-D の中央値フィルタ(外れ値に強い平滑)が funct_1d 族に無い。
    f1d = [n for n in dir(fs) if n.endswith("_funct_1d") or "funct_1d" in n]
    assert any("smooth_funct_1d_mean" in n for n in f1d)
    assert not any("median" in n for n in f1d), f1d
    assert not hasattr(fs, "median_filter_1d") and not hasattr(fs.ledger, "median_filter_1d")
    print("  (c) `funct_1d` 族(%d op)の平滑は**平均とガウスだけ**で、中央値が無い。"
          % len(f1d))
    print("      5 章のとおりスパッタに効くのは中央値なので、外れ値に強い 1-D 平滑")
    print("      が公開経路に無いのは痛い(2-D の `median` 族は在る)。")

    # (d) 「測れなかった」を運ぶ型が無い。
    for nm in ("valid_mask", "masked_profile", "profile_validity"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (d) **「測れなかった」を値と一緒に運ぶ型が無い**。6・7 章の主題そのもの")
    print("      で、呼び手が (値, 有効マスク) の対を手で持ち回るしかない。")
    print("      `triangulate_column` は NaN を通す約束になっているので、")
    print("      族として **NaN = 未測定**に揃えるだけでも効く。")

    # (e) 影の地図を先に描く口が無い(h から幾何で計算できるのに)。
    for nm in ("shadow_mask", "visibility_from_height", "occlusion_map"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    assert hasattr(fs.ledger, "occlusion_edges")
    print("  (e) 断面 h(x) と入射角から**影の地図**を出す口が無い(本 PoC の")
    print("      `lit_mask` は走査最大値 1 本の 3 行)。`ledger.occlusion_edges` は")
    print("      在るが 3-D の深度画像向けで、1-D 断面には使えない。")
    print("      「どこが測れないか」は撮る前に分かるのだから、op にする価値がある。")

    # (f) 在って助かったもの
    assert hasattr(fs.ledger, "measure_pos") and hasattr(fs.ledger, "gen_measure_rectangle2")
    print("  (f) 在って助かった: `gen_measure_rectangle2`(phi=pi/2 で縦向き)+")
    print("      `measure_pos`。輝線の**両側のエッジ**をサブピクセルで取れるので、")
    print("      しきい値の中点法を自前の内挿なしで組めた(2 章、ゼロ点比 8.5 倍)。")
    print("      324 列で %s 程度と速さも足りる。" % "30 ms")


def main() -> None:
    t0 = time.perf_counter()
    print("poc_weld_bead_profile — レーザー三角測量の断面から溶接ビードを測る")
    print("(真値は断面の閉形式。測れなかった列を 0 と書くと欠陥が消える)")
    print()
    truth = section1_scene()
    section2_estimators(truth)
    section3_quantities(truth)
    section4_specular(truth)
    section5_spatter(truth)
    curve = section6_occlusion(truth)
    section7_strict(truth)
    section8_figures(truth, curve)
    section9_tool_gaps()
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
