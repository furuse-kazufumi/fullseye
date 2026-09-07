# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""電極の呼吸を µm で測る —— サブピクセルなら何でもよいわけではない。

充放電のたびに電極は膨らんで縮みます(グラファイト負極が主犯)。セルの外形に
出るのは数 µm で、寿命・拘束圧・モジュール設計に直結するのに、**どの材料が
どれだけ膨らんだか**は外からは分かりません。この PoC は、2 時期の断面画像の
**層境界をサブピクセルで追って**それを出します。積層 3 単位・境界 13 本、
1 画素 = 1 µm、真値は負極 1.00 % / 正極 0.20 % / セパレータ 0 % の伸びで、
積層全体は 480.0 → 482.136 µm(**+2.136 µm = +0.4450 %**)。

EXTEND: 実機に差し替えるなら :func:`render` が返す画像 2 枚を、放電状態と
充電状態の断面画像(オペランド CT の同一スライス、または断面研磨の顕微鏡像)に
置き換えます。**必要なのは 2 枚が同じ倍率・同じ視野であること**で、平行移動は
:func:`strain_regression` が吸収します(切片が動くだけ)。倍率が違うと伸びと
区別できません —— そこが差し替えの限界で、実機では視野内に不変の基準
(集電箔の厚み、治具のピン)を写し込んで倍率を固定します。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点を 2 つ置く**。(Z1) 二値化して層の画素数を数えると、負極の
   +0.58 µm は量子化 1 px に埋もれて **13 本中 0 本**が真値の 3 分の 1 以内に
   入らない。(Z2) 固定しきい値 55 % の交差を線形補間する —— これは
   **サブピクセルなので、雑音なしなら +0.004459(真値 +0.004450)とほぼ当たる**。
   問題は精度ではなく、次の 3 章。
2. **提案(`fs.ledger.measure_pos` の勾配ピーク + 全境界の回帰)は雑音なしで
   完全**。13 本の境界位置の誤差は最大 **1.8e-14 px**、層ごとの伸びも
   負極 +1.014 / +0.958 / +1.013 %(真値 +1.00 %)、正極 +0.206 / +0.207 /
   +0.188 %(真値 +0.20 %)、セパレータ 0.000 %(真値 0)で回収できる。
3. ★★**対照群がゼロ点を殺す**。伸びゼロのまま照明だけ変えた 4 条件で、
   Z2(固定しきい値)は**偽の伸び**を出す: オフセット +0.10 で
   **-1.07e-02 = 真値の 2.4 倍を逆符号で**、傾斜 ±30 % で -1.18e-04、
   ぼけ 1.6→2.4 px で -3.77e-04(真値の 8.5 %)、ゲイン x1.30 では
   **交差が 12 本から 6 本に落ちて測定不能**。同じ 4 条件で `measure_pos` は
   0.0 / -2.2e-06 / -8.5e-12 / 0.0 —— **勾配のピークはゲインにもオフセットにも
   厳密に動かない**から。★予想が 1 つ外れた: 「ぼけが変わると隣の境界が
   引き合って偽の伸びが出る」と踏んだが、σ=2.4 px では **-8.5e-12** で
   何も起きない(最も狭いセパレータ 18 px でも 7.5σ 離れている)。
   σ を 6.0 px まで上げて初めて偽の伸びが出る。
4. ★**雑音の効き方は先に計算できる、ただし 2.9 倍の割引つき**。エッジ位置の
   Cramer-Rao 下界 σ_x = (σ_n/√W)/h・√(2√π σ_b) を先に書いてから測ると、
   σ_n = 0.02 / 0.05 / 0.10 / 0.20 で **実測 / 下界 = 2.61 / 2.77 / 2.95 / 3.01**。
   放物線あてはめの勾配ピークは**下界の約 3 分の 1 の効率**で、その比は
   雑音によらずほぼ一定 —— つまり**予測は係数 1 つで使える**。
5. ★★**いちばん欲しい数字が、いちばんばらつく**。σ_n = 0.10 で、積層全体の
   ひずみのばらつきは **5.9e-04**(真値 4.45e-03 の 13 %)なのに、
   負極 1 層だけのひずみは **3.0e-03**(真値 1.00e-02 の 30 %)—— **5.1 倍**。
   てこの腕が 480 px から 58 px に縮むからで、これは推定器の出来ではなく幾何。
6. ★**全体のひずみにも 2 通りあり、精度と偏りが逆を向く**。端から端の比は
   定義上**厳密に不偏**(誤差 0.0e+00)だが境界 2 本しか使わない。13 本の
   回帰は雑音に強い代わりに、**ひずみが一様でないと -2.7 % 偏る**
   (回帰は境界を重心からの距離で重みづけるが、真の平均は層厚で重みづける)。
   どちらが良いかは雑音次第で、σ_n = 0.10 では回帰の全誤差 5.9e-04 に対し
   端から端は 6.7e-04。
7. ★★**崖は 2 段で、種類が違う**。コントラストを落とすと、まず
   **数字が静かに悪くなり**(CNR 8.8 → 4.4 でばらつき 5.9e-04 → 1.2e-03)、
   次に **CNR 1.8 で境界の本数が壊れる**(24 回中 9 回が 13 本を返せず、
   その先は平均も意味を失う)。予測した崖(3σ 検出限界 = CNR 2.0)は
   本数が壊れる崖とほぼ同じ位置に来た —— **精度の限界と検出の限界が
   たまたま重なっている**ので、どちらで死んだのかは本数を数えないと分からない。

【グラウンドトゥルース】層境界の位置は誤差関数の重ね合わせとして**解析的に**
置くので(画像を作るときに再標本化しない)、真値は浮動小数点の精度で既知です。
伸びは層ごとの厚みに掛けるので、積層全体の伸びは層厚で重みづけた平均として
閉形式で出ます(+0.44500 %)。

来歴(公開文献のみ): Ohzuku et al., *J. Electrochem. Soc.* 140 (1993) 2490 ——
グラファイトの層間膨張 / Oh et al., *J. Power Sources* 267 (2014) 197 ——
セルの可逆的な厚み変化(呼吸)の実測 / Rieutord et al., *Rev. Sci. Instrum.*
71 (2000) 4638 —— エッジ位置推定の Cramer-Rao 下界の形 / HALCON
"1D Measuring" —— 測定線上のサブピクセルエッジ抽出の規約。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
H, W = 512, 128         # 断面画像 [px]。行方向 = 積層の厚み方向
PX_UM = 1.0             # 1 px の大きさ [µm]
SIG_PSF = 1.6           # 撮像のぼけ σ [px]
BASE_ROW = 12.0         # 集電箔(不動の基準)の位置 [px]
G_OUT = 0.85            # 積層の外(電解液/缶)のグレー値

#: 単位セル: (名前, 厚み [µm], グレー値, 充電時のひずみ)
UNIT = (("負極", 58.0, 0.30, 0.0100),
        ("セパレータ", 18.0, 0.75, 0.0),
        ("正極", 66.0, 0.45, 0.0020),
        ("セパレータ", 18.0, 0.75, 0.0))
N_UNIT = 3

#: measure_pos の平滑化 σ [サンプル]。振幅のしきい値は画像の値域から自動で決める。
MEAS_SIGMA = 1.0
#: 自動しきい値の係数(いちばん弱い境界 0.10 が通り、雑音は通らない値)
THR_FRAC = 0.15
#: 固定しきい値のゼロ点 Z2 が使う値(現場で 1 回だけ決める運用の模擬)
FIXED_LEVEL = 0.55
SEED = 7


# --------------------------------------------------------------------------- #
# 場面を作る —— 境界位置は erf の重ね合わせで**解析的に**置く                    #
# --------------------------------------------------------------------------- #
def layers() -> list[tuple[str, float, float, float]]:
    return [row for _ in range(N_UNIT) for row in UNIT]


def truth(charged: bool, shift: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """境界位置 [px] と、境界をまたぐグレー値の列(``len = 境界 + 1``)。

    ``shift`` は積層まるごとの平行移動 [px]。**真値を画素の中心に乗せるかどうか**
    を変えるためのつまみで、3 章のピークロッキングの検査に使う。
    """
    pos, lev = [], [G_OUT]
    r = BASE_ROW + shift
    for _name, t_um, gray, strain in layers():
        pos.append(r)
        lev.append(gray)
        r += (t_um / PX_UM) * (1.0 + strain if charged else 1.0)
    pos.append(r)
    lev.append(G_OUT)
    return np.asarray(pos), np.asarray(lev)


def render(charged: bool = False, sig_psf: float = SIG_PSF, noise: float = 0.0,
           gain: float = 1.0, offset: float = 0.0, ramp: float = 0.0,
           contrast: float = 1.0, seed: int = SEED, shift: float = 0.0) -> np.ndarray:
    """断面画像を作る。``ramp`` は視野内で明るさが傾く照明(ケラレ/ビーム硬化)。"""
    pos, lev = truth(charged, shift)
    lev = G_OUT + (lev - G_OUT) * contrast
    rows = np.arange(H, dtype=float)
    prof = np.full(H, lev[0])
    for k in range(len(pos)):
        prof = prof + (lev[k + 1] - lev[k]) * 0.5 * (
            1.0 + erf((rows - pos[k]) / (math.sqrt(2.0) * sig_psf)))
    img = np.repeat(prof[:, None], W, axis=1)
    if ramp:
        img = img * (1.0 + ramp * (rows[:, None] / (H - 1) - 0.5))
    img = img * gain + offset
    if noise:
        img = img + np.random.default_rng(seed).normal(0.0, noise, img.shape)
    return img


# --------------------------------------------------------------------------- #
# 推定器 3 つ                                                                   #
# --------------------------------------------------------------------------- #
def _column_profile(img: np.ndarray) -> np.ndarray:
    return np.asarray(img, float).mean(axis=1)


def auto_threshold(img: np.ndarray) -> float:
    """振幅のしきい値を画像の値域から決める(コントラストが変わっても追従する)。"""
    p = _column_profile(img)
    return THR_FRAC * float(np.percentile(p, 99) - np.percentile(p, 1))


def edges_gradient(img: np.ndarray) -> np.ndarray:
    """★提案: :func:`fullseye.ledger.measure_pos`(勾配ピークの放物線サブピクセル)。

    測定矩形は厚み方向に張り、幅方向 ``W-4`` px を平均する(fullseye 側の機能)。
    """
    handle = fs.ledger.gen_measure_rectangle2(
        (H - 1) / 2.0, (W - 1) / 2.0, math.pi / 2.0, (H - 1) / 2.0, W - 4, img.shape)
    edges = fs.ledger.measure_pos(img, handle, sigma=MEAS_SIGMA,
                                  threshold=auto_threshold(img))
    return np.asarray([e["row"] for e in edges], float)


def edges_fixed_level(img: np.ndarray, level: float = FIXED_LEVEL) -> np.ndarray:
    """ゼロ点 Z2: 固定しきい値の交差を線形補間(**これもサブピクセル**)。"""
    prof = _column_profile(img)
    out = []
    for i in range(1, H):
        a, b = prof[i - 1], prof[i]
        if (a - level) * (b - level) < 0.0:
            out.append(i - 1 + (level - a) / (b - a))
    return np.asarray(out, float)


def thickness_integer(img: np.ndarray, level: float = FIXED_LEVEL) -> np.ndarray:
    """ゼロ点 Z1: 二値化して層の画素数を数える(整数の厚み)。"""
    b = _column_profile(img) > level
    runs, start = [], 0
    for i in range(1, H):
        if b[i] != b[i - 1]:
            runs.append(i - start)
            start = i
    runs.append(H - start)
    return np.asarray(runs[1:-1], float)   # 外側の背景 2 本を落とす


def strain_regression(p0: np.ndarray, p1: np.ndarray) -> float:
    """全境界の回帰で積層全体のひずみ。平行移動は切片が吸う。"""
    if p0.size != p1.size or p0.size < 3:
        return float("nan")
    return float(np.polyfit(p0, p1, 1)[0] - 1.0)


def strain_end_to_end(p0: np.ndarray, p1: np.ndarray) -> float:
    """端から端の比 —— 定義上**不偏**だが境界 2 本しか使わない。"""
    if p0.size != p1.size or p0.size < 2:
        return float("nan")
    return float((p1[-1] - p1[0]) / (p0[-1] - p0[0]) - 1.0)


def true_mean_strain() -> float:
    p0, p1 = truth(False)[0], truth(True)[0]
    return float((p1[-1] - p1[0]) / (p0[-1] - p0[0]) - 1.0)


# --------------------------------------------------------------------------- #
# 1-2. ゼロ点と提案                                                             #
# --------------------------------------------------------------------------- #
def section_zero_and_proposal() -> dict:
    print("\n" + "=" * 78)
    print("1-2) ゼロ点 2 つと提案 —— 雑音なしでどこまで当たるか")
    print("=" * 78)

    b0, b1 = truth(False)[0], truth(True)[0]
    e_true = true_mean_strain()
    print("  積層 %.1f -> %.3f µm (+%.3f µm = %+.5f %%) / 境界 %d 本 / 1 px = %.1f µm"
          % (b0[-1] - b0[0], b1[-1] - b1[0], (b1[-1] - b1[0]) - (b0[-1] - b0[0]),
             100 * e_true, len(b0), PX_UM))

    img0, img1 = render(False), render(True)
    p0, p1 = edges_gradient(img0), edges_gradient(img1)
    assert p0.size == b0.size, (p0.size, b0.size)
    bias = float(np.abs(p0 - b0).max())
    print("\n  提案: measure_pos の境界位置の誤差(雑音なし)最大 %.1e px" % bias)

    # Z1 —— 整数の厚み
    t0i, t1i = thickness_integer(img0), thickness_integer(img1)
    t0t = np.diff(b0)
    t1t = np.diff(b1)
    good = 0
    if t0i.size == t0t.size:
        for k in range(t0t.size):
            est = (t1i[k] - t0i[k])
            tru = (t1t[k] - t0t[k])
            if abs(est - tru) <= abs(tru) / 3.0 + 1e-9:
                good += 1
    print("  Z1(二値化して画素数)—— 層 %d 本のうち厚み変化が真値の 1/3 以内 %d 本"
          % (t0t.size, good))
    print("     負極の伸びは %.2f µm、量子化は 1 px = %.1f µm。原理的に読めない。"
          % ((t1t[0] - t0t[0]), PX_UM))

    # Z2 —— 固定しきい値の交差
    q0, q1 = edges_fixed_level(img0), edges_fixed_level(img1)
    e_z2 = strain_regression(q0, q1)
    e_prop = strain_regression(p0, p1)
    print("  Z2(固定しきい値 %.2f の交差、サブピクセル)—— 交差 %d 本、"
          "ひずみ %+.6f(真値 %+.6f)" % (FIXED_LEVEL, q0.size, e_z2, e_true))
    print("  提案(勾配ピーク %d 本の回帰)             —— ひずみ %+.6f"
          % (p0.size, e_prop))
    print("  -> 雑音なしでは**どちらも当たる**。差が出るのは 3 章の対照群。")

    # 層ごとの伸び
    print("\n   層          厚み(放電→充電)[µm]    ひずみ 実測 / 真値 [%]")
    per = []
    for k, (name, _t, _g, s) in enumerate(layers()):
        d0, d1 = p1[k + 1] - p1[k], p0[k + 1] - p0[k]
        est = d0 / d1 - 1.0
        per.append((name, est, s))
        print("   %-10s  %7.3f -> %7.3f      %+7.3f / %+7.3f"
              % (name, d1, d0, 100 * est, 100 * s))

    prof0, prof1 = _column_profile(img0), _column_profile(img1)
    figs.save_grid("scene", [img0, img1],
                   ["放電状態", "充電状態(+%.3f µm)" % ((b1[-1] - b1[0]) - (b0[-1] - b0[0]))],
                   title="積層電極の断面(縦 = 厚み方向 %d µm)" % H, ncols=2,
                   caption="負極(暗)・セパレータ(明)・正極(中)が 3 単位。"
                           "2 枚の違いは µm 級で、並べても見えない —— そこが主題。")
    rows = np.arange(H)
    figs.save_plot("profiles",
                   [("放電", rows, prof0), ("充電", rows, prof1)],
                   xlabel="行(厚み方向)[px]", ylabel="グレー値 [-]",
                   title="厚み方向のグレープロファイル(境界 13 本)",
                   caption="境界は erf の重ね合わせで解析的に置いてあるので、"
                           "真値は浮動小数点の精度で既知。")
    figs.save_plot("displacement",
                   [("境界の移動量(実測)", b0, p1 - p0),
                    ("真値", b0, b1 - b0)],
                   xlabel="放電状態での境界位置 [px]", ylabel="移動量 [px]",
                   title="境界はどれだけ動いたか(最大 %.2f px)" % float((b1 - b0).max()),
                   caption="階段状に増えるのは、伸びる層(負極 1.00 %)と"
                           "伸びない層(セパレータ 0 %)が交互だから。"
                           "傾きが積層全体のひずみ。")
    return {"e_true": e_true, "e_prop": e_prop, "e_z2": e_z2, "bias": bias,
            "z1_good": good, "n_layer": int(t0t.size), "per": per,
            "img0": img0, "b0": b0}


# --------------------------------------------------------------------------- #
# 3. 真値を格子に乗せると推定器は「完璧」に見える —— ピークロッキング            #
# --------------------------------------------------------------------------- #
def section_peak_locking() -> dict:
    print("\n" + "=" * 78)
    print("3) ★★1-2 章の「誤差 1.8e-14 px」を疑う —— 真値を格子から外す")
    print("=" * 78)
    print("  1-2 章は境界が %g, %g, ... と**画素の中心にぴったり**乗っていた。"
          % (BASE_ROW, BASE_ROW + UNIT[0][1]))
    print("  放物線あてはめは左右対称な標本に対して厳密なので、それは"
          "**推定器の性能ではなく\n  場面の作り方**かもしれない。積層まるごとを"
          "小数画素だけずらして測り直す:")

    offs = np.linspace(0.0, 0.95, 20)
    errs, est_frac, true_frac = [], [], []
    for off in offs:
        b = truth(False, shift=off)[0]
        p = edges_gradient(render(False, shift=off))
        if p.size != b.size:
            continue
        errs.append(p - b)
        est_frac.append(np.mod(p, 1.0))
        true_frac.append(np.mod(b, 1.0))
    err = np.concatenate(errs)
    rms, mx = float(np.sqrt(np.mean(err ** 2))), float(np.abs(err).max())
    print("\n  小数画素のずれを 0 -> 0.95 まで %d 通り x 境界 %d 本 = %d 点:"
          % (len(errs), errs[0].size, err.size))
    print("    位置の誤差 RMS %.4f px / 最大 %.4f px"
          "   <- 1-2 章の 1.8e-14 px は**格子に乗せた場合だけ**" % (rms, mx))
    print("    ずれ 0.00 のときだけ %.1e px、ずれ 0.25 では %+.4f px"
          % (float(np.abs(errs[0]).max()),
             float(np.mean(errs[int(0.25 / (offs[1] - offs[0]))]))))

    # fullseye の PIV 族が持つ「ピークロッキング」の指標をそのまま使う。
    # 真値の c0 と比べて読む(op の docstring がそう指示している)。
    ef = np.asarray(est_frac)                     # (ずらし量, 境界) の 2-D
    tf = np.asarray(true_frac)
    c0_est = fs.ledger.piv_peak_locking(np.stack([ef, ef]), bins=10)["c0"]
    c0_true = fs.ledger.piv_peak_locking(np.stack([tf, tf]), bins=10)["c0"]
    print("    小数部の偏り c0(fs.ledger.piv_peak_locking、一様なら 1 前後): "
          "推定 %.2f / 真値 %.2f" % (c0_est, c0_true))
    print("    ★c0 はこの大きさのロッキングに**気づかない**(どちらも 1 前後)。"
          "\n     0.012 px の引き寄せは 10 個の階級では見えないから —— "
          "op の docstring が\n     『決定的な診断は小数部を 0->0.9 まで振ること』"
          "と書いているとおりだった。")

    span = float(truth(False)[0][-1] - truth(False)[0][0])
    e_true = true_mean_strain()
    print("\n  この %.4f px が伸びに効く大きさ:" % mx)
    print("    積層全体(腕 %.0f px)   %.1e = 真値の %.1f %%"
          % (span, mx * math.sqrt(2) / span,
             100 * mx * math.sqrt(2) / span / e_true))
    print("    負極 1 層(腕 %.0f px)  %.1e = 真値の %.1f %%"
          % (UNIT[0][1], mx * math.sqrt(2) / UNIT[0][1],
             100 * mx * math.sqrt(2) / UNIT[0][1] / UNIT[0][3]))
    print("  -> **雑音ゼロでも層別の伸びは数 % ずれる**。1-2 章で層別が"
          " +1.014 / +0.958 % と\n     ばらついたのは雑音ではなく、これ。")

    grid = np.asarray(errs)                       # (ずらし量, 境界)
    figs.save_plot("peak_locking",
                   [("境界ごとの誤差", np.repeat(offs[:grid.shape[0]], grid.shape[1]),
                     grid.ravel()),
                    ("ゼロ", offs, np.zeros_like(offs))],
                   xlabel="積層を小数画素だけずらした量 [px]",
                   ylabel="境界位置の誤差 [px]",
                   title="ピークロッキング(格子に乗ると誤差 0、外すと %.3f px)" % mx,
                   kinds=("scatter", "line"),
                   caption="真値を画素の中心に置いた検査は、推定器を実力以上に"
                           "良く見せる。乗せない検査を必ず 1 本置くこと。")
    return {"rms": rms, "max": mx, "c0_est": c0_est, "c0_true": c0_true}


# --------------------------------------------------------------------------- #
# 4. 対照群 —— 伸びゼロで照明だけ変える                                          #
# --------------------------------------------------------------------------- #
def section_controls() -> dict:
    print("\n" + "=" * 78)
    print("4) 対照群 —— 伸びゼロのまま照明とぼけだけ変える(偽の伸びが出るか)")
    print("=" * 78)
    e_true = true_mean_strain()
    base = render(False)
    cases = (("ゲイン x1.30", dict(gain=1.30)),
             ("オフセット +0.10", dict(offset=0.10)),
             ("傾斜 +-30 %", dict(ramp=0.30)),
             ("ぼけ 1.6->2.4 px", dict(sig_psf=2.4)),
             ("ぼけ 1.6->5.0 px", dict(sig_psf=5.0)),
             ("ぼけ 1.6->6.0 px", dict(sig_psf=6.0)))
    print("   条件               提案(勾配ピーク)      Z2(固定しきい値)")
    rows, out = [], {}
    for name, kw in cases:
        other = render(False, **kw)
        pg = strain_regression(edges_gradient(base), edges_gradient(other))
        n_g = edges_gradient(other).size
        qf = edges_fixed_level(other)
        pf = strain_regression(edges_fixed_level(base), qf)
        out[name] = (pg, pf, n_g, qf.size)
        s_g = "測定不能(%d 本)" % n_g if not np.isfinite(pg) else "%+.2e" % pg
        s_f = "測定不能(%d 本)" % qf.size if not np.isfinite(pf) else "%+.2e" % pf
        print("   %-18s %-20s %s" % (name, s_g, s_f))
        rows.append([name, s_g, s_f,
                     "-" if not np.isfinite(pg) else "%.0f %%" % (100 * abs(pg) / e_true),
                     "-" if not np.isfinite(pf) else "%.0f %%" % (100 * abs(pf) / e_true)])

    print("\n  真値の伸びは %+.2e。上の数字が**それに対してどれだけ大きいか**が問題。" % e_true)
    off = out["オフセット +0.10"]
    print("  ★★Z2 はオフセットだけで %+.2e = 真値の %.1f 倍を**逆符号で**返す。"
          % (off[1], abs(off[1]) / e_true))
    print("     ゲインでは交差が %d 本に落ちて測定そのものが成立しない。"
          % out["ゲイン x1.30"][3])
    print("  勾配ピークがゲインとオフセットに厳密に動かないのは、"
          "|dI/dr| のピーク位置が\n     I -> aI + b で変わらないから(a > 0)。"
          "傾斜と大きなぼけはその限りではない:")
    print("     傾斜 %+.2e / ぼけ 2.4 px %+.2e / ぼけ 5.0 px %+.2e"
          % (out["傾斜 +-30 %"][0], out["ぼけ 1.6->2.4 px"][0], out["ぼけ 1.6->5.0 px"][0]))
    print("  ★予想が 2 段で外れた。「ぼけが増えると隣の境界が引き合って偽の伸びが"
          "出る」と\n     踏んだが、(1) 2.4 px では %+.1e で**何も起きない**"
          "(最も狭いセパレータ 18 px でも\n     %.1f σ 離れている)。"
          "5.0 px でようやく %+.1e(真値の %.1f %%)。"
          % (out["ぼけ 1.6->2.4 px"][0], 18.0 / 2.4, out["ぼけ 1.6->5.0 px"][0],
             100 * abs(out["ぼけ 1.6->5.0 px"][0]) / e_true))
    print("     (2) 6.0 px では偏りが大きくなる前に**境界が 1 本消えて"
          "測定不能**(%d 本)。\n     引き合いより先に検出が死ぬ ——"
          "壊れ方の順番まで当てないと予測とは言えない。"
          % out["ぼけ 1.6->6.0 px"][2])

    figs.save_table("controls",
                    ["条件(伸びは 0)", "提案 勾配ピーク", "Z2 固定しきい値",
                     "真値比 提案", "真値比 Z2"], rows,
                    title="対照群: 伸びゼロで照明だけ変えたときの「偽の伸び」",
                    caption="真値の伸びは %+.2e。Z2 はサブピクセルなのに"
                            "オフセットだけで真値を超える嘘をつく。" % e_true)
    return out


# --------------------------------------------------------------------------- #
# 5-6. 雑音 —— 先に下界を書いてから測る                                          #
# --------------------------------------------------------------------------- #
def _crb_sigma_pos(noise: float, height: float, sig_psf: float = SIG_PSF,
                   n_avg: int = W - 4) -> float:
    """エッジ位置の Cramer-Rao 下界 [px]。

    誤差関数のエッジ ``h Phi((r-x0)/sigma_b)`` を白色雑音 ``sigma_n`` で観測する
    ときの Fisher 情報から ``sigma_x = (sigma_n/sqrt(W)) / h * sqrt(2 sqrt(pi) sigma_b)``。
    """
    return (noise / math.sqrt(n_avg)) / height * math.sqrt(
        2.0 * math.sqrt(math.pi) * sig_psf)


def section_noise() -> dict:
    print("\n" + "=" * 78)
    print("5-6) 雑音 —— Cramer-Rao 下界を先に書いてから測る")
    print("=" * 78)
    b0 = truth(False)[0]
    lev = truth(False)[1]
    h_rms = float(np.sqrt(np.mean(np.diff(lev) ** 2)))
    lever = float(np.sum((b0 - b0.mean()) ** 2))
    span = float(b0[-1] - b0[0])
    t_anode = UNIT[0][1] / PX_UM
    e_true = true_mean_strain()
    print("  予測に使う量: 境界の平均的なグレー差 h_rms = %.3f / ぼけ σ_b = %.1f px /"
          " 幅方向の平均 %d 本" % (h_rms, SIG_PSF, W - 4))
    print("  予測 1: σ_x = (σ_n/√%d)/h * √(2√π σ_b)" % (W - 4))
    print("  予測 2: 積層全体 σ_e = σ_x √2 / √Σ(b-b̄)² = σ_x * %.2e" % (
        math.sqrt(2.0) / math.sqrt(lever)))
    print("  予測 3: 負極 1 層 σ_e = σ_x √2 / %.0f px = σ_x * %.2e" % (
        t_anode, math.sqrt(2.0) / t_anode))
    print("\n   σ_n    σ_x 下界   σ_x 実測  比    全体 σ_e(予測)   負極 σ_e(予測)   採用")

    n_seed = 24
    rows, ratios = [], []
    glob_sd, an_sd, noises = [], [], []
    for nz in (0.02, 0.05, 0.10, 0.20):
        pos, gl, an, e2e = [], [], [], []
        for s in range(n_seed):
            a = edges_gradient(render(False, noise=nz, seed=1000 + s))
            b = edges_gradient(render(True, noise=nz, seed=2000 + s))
            if a.size == b0.size:
                pos.append(a)
            if a.size != b0.size or b.size != b0.size:
                continue
            gl.append(strain_regression(a, b))
            e2e.append(strain_end_to_end(a, b))
            an.append((b[1] - b[0]) / (a[1] - a[0]) - 1.0)
        sx = float(np.asarray(pos).std(axis=0).mean())
        crb = _crb_sigma_pos(nz, h_rms)
        gl_sd, an_sd_v = float(np.std(gl)), float(np.std(an))
        ratios.append(sx / crb)
        glob_sd.append(gl_sd)
        an_sd.append(an_sd_v)
        noises.append(nz)
        rows.append([("%.2f" % nz), "%.4f" % crb, "%.4f" % sx, "%.2f" % (sx / crb),
                     "%.2e" % gl_sd, "%.2e" % an_sd_v, "%d/%d" % (len(gl), n_seed)])
        print("   %.2f   %.4f px  %.4f px  %.2f   %.2e (%.2e)  %.2e (%.2e)   %d/%d"
              % (nz, crb, sx, sx / crb, gl_sd, sx * math.sqrt(2) / math.sqrt(lever),
                 an_sd_v, sx * math.sqrt(2) / t_anode, len(gl), n_seed))
        if abs(nz - 0.10) < 1e-9:
            keep = {"gl": gl_sd, "an": an_sd_v, "e2e": float(np.std(e2e)),
                    "gl_bias": float(np.mean(gl)) - e_true,
                    "e2e_bias": float(np.mean(e2e)) - e_true}

    print("\n  ★実測 / 下界 = %s —— 放物線あてはめは下界の約 1/3 の効率で、"
          % " / ".join("%.2f" % r for r in ratios))
    print("     比は雑音でほとんど動かない(**予測は係数 1 つで使える**)。")
    print("  ★★いちばん欲しい数字がいちばんばらつく: σ_n=0.10 で"
          " 全体 %.1e に対し負極 1 層は %.1e(**%.1f 倍**)。"
          % (keep["gl"], keep["an"], keep["an"] / keep["gl"]))
    print("     てこの腕が %.0f px から %.0f px に縮むだけの幾何で、"
          "推定器の出来ではない。" % (span, t_anode))

    figs.save_plot("noise_scaling",
                   [("積層全体(回帰 13 本)", noises, glob_sd),
                    ("負極 1 層", noises, an_sd),
                    ("真値の伸び(全体)", noises, [e_true] * len(noises)),
                    ("真値の伸び(負極)", noises, [UNIT[0][3]] * len(noises))],
                   xlabel="画素雑音 σ_n [グレー値]", ylabel="ひずみのばらつき [-]",
                   title="ばらつきは雑音に比例。層別は全体の 5 倍ばらつく",
                   caption="横線は真値。線が横線を越えたところで、その量は"
                           "「測れていない」。")
    figs.save_table("noise_table",
                    ["σ_n", "σ_x 下界 [px]", "σ_x 実測 [px]", "実測/下界",
                     "全体 σ_e", "負極 σ_e", "採用回数"], rows,
                    title="エッジ位置の下界と実測(24 種の乱数)")
    return {"ratios": ratios, "glob": glob_sd, "an": an_sd, "keep": keep,
            "lever": lever, "h_rms": h_rms, "span": span, "t_anode": t_anode}


# --------------------------------------------------------------------------- #
# 7. 全体のひずみの 2 通り —— 精度と偏りが逆を向く                               #
# --------------------------------------------------------------------------- #
def section_bias_vs_precision(noise_out: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) 全体のひずみの 2 通り —— 回帰(精度)と端から端(不偏)")
    print("=" * 78)
    e_true = true_mean_strain()
    p0, p1 = edges_gradient(render(False)), edges_gradient(render(True))
    e_reg, e_e2e = strain_regression(p0, p1), strain_end_to_end(p0, p1)
    print("  雑音なし: 回帰 %+.6f(真値比 %+.2f %%) / 端から端 %+.6f(真値比 %+.2f %%)"
          % (e_reg, 100 * (e_reg - e_true) / e_true,
             e_e2e, 100 * (e_e2e - e_true) / e_true))
    print("  ★回帰が %.1f %% 低いのは推定の誤差ではなく**重みの違い**: 回帰は"
          % abs(100 * (e_reg - e_true) / e_true))
    print("     境界を重心からの距離で重みづけるが、真の平均は層厚で重みづける。"
          "\n     ひずみが一様(全層同じ)ならこの差は消える —— 確かめる:")
    # 対照群: 全層に同じひずみを掛けたら回帰も不偏になるはず
    save = list(UNIT)
    try:
        globals()["UNIT"] = tuple((n, t, g, 0.0045) for n, t, g, _ in save)
        u0, u1 = edges_gradient(render(False)), edges_gradient(render(True))
        e_u = strain_regression(u0, u1)
        print("     一様 0.45 %% を掛けると回帰は %+.6f(真値 %+.6f、差 %+.1e)"
              " —— 予想どおり偏りは消えた。" % (e_u, 0.0045, e_u - 0.0045))
    finally:
        globals()["UNIT"] = tuple(save)

    k = noise_out["keep"]
    print("\n  σ_n = 0.10 での全誤差(偏り + ばらつき):")
    print("     回帰      偏り %+.2e / ばらつき %.2e" % (k["gl_bias"], k["gl"]))
    print("     端から端  偏り %+.2e / ばらつき %.2e" % (k["e2e_bias"], k["e2e"]))
    print("  -> この雑音では回帰のほうがばらつきが %.0f %% 小さいが、"
          % (100 * (1 - k["gl"] / k["e2e"])))
    print("     偏りは端から端のほうが %.1f 倍小さい。**どちらが良いかは雑音次第**。"
          % (abs(k["gl_bias"]) / max(abs(k["e2e_bias"]), 1e-12)))
    return {"e_reg": e_reg, "e_e2e": e_e2e, "e_uniform": e_u}


# --------------------------------------------------------------------------- #
# 8. 崖 —— コントラストを落とす                                                 #
# --------------------------------------------------------------------------- #
def section_cliff(noise_out: dict) -> dict:
    print("\n" + "=" * 78)
    print("8) 崖 —— コントラストを落とす。壊れ方を種類ごとに数える")
    print("=" * 78)
    nz = 0.05
    e_true = true_mean_strain()
    n_boundary = truth(False)[0].size
    # 予測: 3σ 検出限界 = ばらつきが真値の 1/3 になるコントラスト
    ratio = float(np.mean(noise_out["ratios"]))
    sx_at = lambda c: ratio * _crb_sigma_pos(nz, noise_out["h_rms"] * c)   # noqa: E731
    sd_at = lambda c: sx_at(c) * math.sqrt(2.0) / math.sqrt(noise_out["lever"])  # noqa: E731
    c_pred = 3.0 * sd_at(1.0) / e_true
    print("  予測: ばらつき σ_e(c) = %.2e / c。3σ で検出できる限界は"
          " c = %.3f、\n        そのときの CNR = h_rms*c/σ_n = %.2f。"
          % (sd_at(1.0), c_pred, noise_out["h_rms"] * c_pred / nz))
    print("\n   コントラスト  CNR    ばらつき   予測      偏り     本数不一致  余分な境界")

    n_seed = 24
    cs, sds, preds, cnrs = [], [], [], []
    lost = {}
    for c in (1.0, 0.7, 0.5, 0.35, 0.25, 0.12):
        vals, n_bad, n_extra, n_miss = [], 0, 0, 0
        for s in range(n_seed):
            a = edges_gradient(render(False, noise=nz, contrast=c, seed=3000 + s))
            b = edges_gradient(render(True, noise=nz, contrast=c, seed=4000 + s))
            if a.size != n_boundary or b.size != n_boundary:
                n_bad += 1
                n_extra += int(a.size > n_boundary) + int(b.size > n_boundary)
                n_miss += int(a.size < n_boundary) + int(b.size < n_boundary)
                continue
            vals.append(strain_regression(a, b))
        cnr = noise_out["h_rms"] * c / nz
        sd = float(np.std(vals)) if len(vals) > 2 else float("nan")
        bias = float(np.mean(vals)) - e_true if len(vals) > 2 else float("nan")
        cs.append(c)
        cnrs.append(cnr)
        sds.append(sd)
        preds.append(sd_at(c))
        lost[c] = (n_bad, n_extra, n_miss, len(vals))
        print("      %.2f      %5.2f  %.2e  %.2e  %+.2e     %2d/%d    足りない %d / 余分 %d"
              % (c, cnr, sd, sd_at(c), bias, n_bad, n_seed, n_miss, n_extra))

    first_break = next((c for c in cs if lost[c][0] > 0), None)
    print("\n  ★★崖は 2 段で、しかも**予測を外した**。まず数字が静かに悪くなる"
          "(CNR %.1f -> %.1f で\n     ばらつき %.1e -> %.1e、予測どおり 1/c に比例)。"
          % (cnrs[0], cnrs[2], sds[0], sds[2]))
    if first_break is not None:
        print("     ところが **CNR %.1f で境界の本数が壊れ始め**(%d/%d 回)、"
              "予測した 3σ の崖\n     (CNR %.2f)より **%.1f 倍手前**で死ぬ。"
              % (noise_out["h_rms"] * first_break / nz, lost[first_break][0], n_seed,
                 noise_out["h_rms"] * c_pred / nz,
                 (noise_out["h_rms"] * first_break / nz)
                 / (noise_out["h_rms"] * c_pred / nz)))
    print("  ★★生き残りだけを見ると**逆に良く見える**ことがある —— "
          "採用回数が減った行では\n     ばらつきが下がることすらある"
          "(数え損ねた回が落ちるので、易しい乱数だけが残る)。")
    print("     **1 つの数字に畳まず、足りない / 余分 / 数は合うが誤差、を分けて"
          "数えること。**")

    ok = [(x, y, p) for x, y, p in zip(cnrs, sds, preds) if np.isfinite(y)]
    figs.save_plot("contrast_cliff",
                   [("ばらつき(実測)", [x for x, _, _ in ok], [y for _, y, _ in ok]),
                    ("予測(下界 x %.1f)" % ratio, cnrs, preds),
                    ("3σ 検出限界", cnrs, [e_true / 3.0] * len(cnrs))],
                   xlabel="CNR = h_rms x コントラスト / σ_n [-]",
                   ylabel="積層全体のひずみのばらつき [-]",
                   title="コントラストの崖(予測と実測)",
                   caption="実測が予測から離れる左端は、雑音が増えたのではなく"
                           "**境界を数え損ねている**。種類を分けて数えること。")
    figs.save_grid("frames",
                   [render(False, noise=nz, contrast=1.0, seed=3000),
                    render(False, noise=nz, contrast=0.35, seed=3000),
                    render(False, noise=nz, contrast=0.12, seed=3000)],
                   ["CNR %.1f" % cnrs[0], "CNR %.1f" % cnrs[3], "CNR %.1f" % cnrs[-1]],
                   title="崖の手前・上・向こう(同じ場面、コントラストだけ)", ncols=3)
    return {"cnr": cnrs, "sd": sds, "lost": lost, "c_pred": c_pred,
            "cnr_pred": noise_out["h_rms"] * c_pred / nz}


# --------------------------------------------------------------------------- #
# 9. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(1-D 計測族を µm 級の追跡に使ってみて)")
    print("=" * 78)

    img = render(False)
    handle = fs.ledger.gen_measure_rectangle2(
        (H - 1) / 2.0, (W - 1) / 2.0, math.pi / 2.0, (H - 1) / 2.0, W - 4, img.shape)

    # (a) 2 時期のエッジ列を対応づける口が無い
    for name in ("match_edge_lists", "measure_pos_pair", "strain_from_edges"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    print("  (a) **2 時期のエッジ列を対応づけて伸びを出す**口が無い。"
          "measure_pos は\n      1 枚ぶんのエッジしか返さないので、"
          "本数が変わったときの扱いは呼び手任せ。")

    # (b) しきい値は絶対値。画像の値域に対する相対で渡せない
    e_lo = fs.ledger.measure_pos(img, handle, sigma=MEAS_SIGMA, threshold=0.05)
    e_hi = fs.ledger.measure_pos(img * 2.0, handle, sigma=MEAS_SIGMA, threshold=0.05)
    assert len(e_lo) == len(e_hi), (len(e_lo), len(e_hi))
    e_gain = fs.ledger.measure_pos(img * 0.2, handle, sigma=MEAS_SIGMA, threshold=0.05)
    assert len(e_gain) < len(e_lo), (len(e_gain), len(e_lo))
    print("  (b) `threshold` が**絶対グレー差**なので、露光が変わると本数が変わる"
          "\n      (x0.2 で %d -> %d 本)。この PoC は値域から自動で決めている。"
          % (len(e_lo), len(e_gain)))

    # (c) エッジ位置の**不確かさ**を返さない
    assert set(e_lo[0]) == {"pos", "dist", "row", "col", "amplitude", "polarity"}, e_lo[0]
    print("  (c) 各エッジに `amplitude` は付くが**位置の不確かさ**が付かない。"
          "\n      5 章の下界は amplitude と局所雑音から出せるので、"
          "op 側で返せる(返せば\n      呼び手が重みつき回帰を書ける)。")

    # (d) 1-D プロファイルからの分位点・値域が無い(自動しきい値を毎回自作する)
    assert not hasattr(fs, "profile_contrast")
    print("  (d) プロファイルの値域(p1..p99)を返す定型が無く、"
          "自動しきい値を毎回自作する。")

    # (e) 在って助かった
    print("  (e) 在って助かった: `gen_measure_rectangle2` + `measure_pos`。"
          "幅方向 %d px の\n      平均が op 側に入っているので、"
          "√%d の雑音低減を呼び手が書かずに済む。" % (W - 4, W - 4))


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("電極の呼吸を µm で測る —— サブピクセルなら何でもよいわけではない")
    print("=" * 78)

    base = section_zero_and_proposal()
    lock = section_peak_locking()
    ctrl = section_controls()
    noise = section_noise()
    bias = section_bias_vs_precision(noise)
    cliff = section_cliff(noise)
    section_tool_gaps()

    e_true = base["e_true"]
    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * サブピクセルであることは条件の半分。**照明に動かない**推定量を選ぶ"
          "(Z2 はオフセットだけで真値の %.1f 倍の嘘)。"
          % (abs(ctrl["オフセット +0.10"][1]) / e_true))
    print("  * 雑音の効き方は下界から予測でき、係数は %.1f 倍でほぼ一定。"
          % float(np.mean(noise["ratios"])))
    print("  * 層別(欲しい数字)は全体の %.1f 倍ばらつく。てこの腕の幾何。"
          % (noise["keep"]["an"] / noise["keep"]["gl"]))
    print("  * 崖は 2 段(精度の劣化と本数の崩壊)。分けて数えないと読み違える。")

    # --- 所見を固定する assert ------------------------------------------------ #
    # 1-2) 雑音なしの提案は完全、Z1 は原理的に読めない
    assert base["bias"] < 1e-9, base["bias"]
    assert base["z1_good"] == 0, base["z1_good"]
    assert abs(base["e_prop"] - e_true) < 2e-4, (base["e_prop"], e_true)
    for name, est, tru in base["per"]:
        assert abs(est - tru) < 5e-4, (name, est, tru)
    # 3) 対照群: 勾配ピークはゲイン/オフセットに動かない、Z2 は動く
    assert abs(ctrl["ゲイン x1.30"][0]) < 1e-12, ctrl["ゲイン x1.30"]
    assert abs(ctrl["オフセット +0.10"][0]) < 1e-12, ctrl["オフセット +0.10"]
    assert abs(ctrl["オフセット +0.10"][1]) > 2.0 * e_true, ctrl["オフセット +0.10"]
    assert ctrl["オフセット +0.10"][1] < 0.0, "偽の伸びは負(逆符号)のはず"
    assert not np.isfinite(ctrl["ゲイン x1.30"][1]), "Z2 はゲインで測定不能のはず"
    assert abs(ctrl["ぼけ 1.6->2.4 px"][0]) < 1e-9, ctrl["ぼけ 1.6->2.4 px"]
    assert abs(ctrl["ぼけ 1.6->5.0 px"][0]) > 1e-5, "σ=5 px では偽の伸びが出るはず"
    assert not np.isfinite(ctrl["ぼけ 1.6->6.0 px"][0]), "σ=6 px は本数が壊れるはず"
    # 4-5) 下界との比は 2〜4 でほぼ一定 / 層別は全体より 3 倍以上ばらつく
    assert all(2.0 < r < 4.0 for r in noise["ratios"]), noise["ratios"]
    assert max(noise["ratios"]) / min(noise["ratios"]) < 1.4, noise["ratios"]
    assert noise["keep"]["an"] / noise["keep"]["gl"] > 3.0, noise["keep"]
    # 6) 回帰は偏る / 一様なら偏らない
    assert bias["e_reg"] < e_true, (bias["e_reg"], e_true)
    assert abs(bias["e_reg"] - e_true) / e_true > 0.01
    assert abs(bias["e_e2e"] - e_true) < 1e-12, bias["e_e2e"]
    assert abs(bias["e_uniform"] - 0.0045) < 1e-5, bias["e_uniform"]
    # 7) 崖は 2 段: 高 CNR では本数は崩れず、低 CNR で崩れる
    assert cliff["lost"][1.0][0] == 0, cliff["lost"][1.0]
    assert cliff["lost"][0.12][0] > 0, cliff["lost"][0.12]
    assert cliff["sd"][1] > cliff["sd"][0], cliff["sd"]

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
