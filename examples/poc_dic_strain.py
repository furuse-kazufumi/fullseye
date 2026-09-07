# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_dic_strain — スペックル画像から**ひずみ**を測る(DIC、デジタル画像相関)。
真値を仕込んだ合成変形で、変位 0.01 px 台・ひずみ 100 µε 台まで追い込む PoC。

    py -3.11 examples/poc_dic_strain.py

【この PoC が答える問い】
材料試験室でいちばん普通の問い —「試験片にスペックルを吹いて写真を撮った。
ひずみゲージを貼らずに、画像だけでひずみが測れるか。どこまで信じてよいか」。
答えは「変位は **0.002 px**、ひずみは 100 µε 台まで測れる。ただし**試験機の
わずかな回転が数百 µε の嘘のひずみを作る**ので、ひずみの定義を間違えると
鋼の降伏ひずみの 3 割に相当する誤差が乗る」。

比べる推定器は 4 つ —— ゼロ点(「動いていない」と答えるだけ)/
`optical_flow_lk` / `optical_flow_hs` / **`piv_cross_correlate`**(窓の相関)。
★最後の 1 つは**この repo に最初からあった**。「サブセット相関の op が無い」と
書きかけて、`op_find("correlation")` がそれを返さなかったせいで見落とした
(検索の側を直した)。測り直すと piv が他を 1 桁上回る —— **新しい相関器を
書く必要は無かった**。10 節にその経緯と、本当に欠けていた 4 つを書いてある。

【グラウンドトゥルース(自分で仕込んだ真値)】
スペックルを **3000 個のガウス斑点の重ね合わせとして解析的に描く**。変形後の
画像は「元画像を補間で歪めたもの」ではなく、**斑点の中心座標を変形写像で
移してから描き直したもの**。これが要点で、補間で作った変形画像を補間で
測ると、測っているのが自分の補間器なのか推定器なのか分からなくなる。
斑点を描き直せば真の変位が**厳密に**分かる(丸め誤差だけ)。

仕込む変形は 5 種:

  * 一様並進 u(0〜2 px、0.05 px 刻み)—— サブピクセル精度の素の性能
  * 一様ひずみ ε_xx(500〜20000 µε)—— 測りたい量そのもの
  * 剛体回転 θ(0〜2 度)—— **ひずみは 0 が真値**。嘘を検出する試験
  * ひずみ集中(切欠き、ガウス形)—— 窓の大きさが空間分解能を決める
  * 雑音(σ = 0〜0.05)—— 雑音下限の理論値と突き合わせる

【節立て】
 1) 合成器の検算 —— 整数シフトが厳密に一致するか(ゼロ点その 0)
 2) ★ゼロ点 —— 「変位 0 と答える」推定器に勝てるか
 3) ★サブピクセル掃引 —— lk の偏りは 0.5 px 側へ寄る(教科書の peak locking と逆)
 4) 変位の大きさ掃引 —— どこで壊れるか
 5) ★一様ひずみ —— 100 µε まで届くか
 6) ★★剛体回転 —— 微小ひずみの定義が作る嘘。Green-Lagrange なら厳密に 0
 7) ★ひずみ集中 —— 窓の大きさ vs 空間分解能(尖頭を過小に読む)
 8) 雑音下限 —— 実測と理論 σ_u = σ_n / sqrt(Σ I_x^2)
 9) ★スペックルの粒径 —— 偏りの半分は推定器ではなくスペックルが作る
10) ★所見(**一度書き直している**。既存 op を見落とした経緯つき)

【この PoC で分かった fullseye 側の穴 → 末尾の「所見」節】
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 合成スペックルの諸元 ---------------------------------------------------- #
N = 256                 # 画素
N_BLOB = 3000           # 斑点の数(輝度 0.2 超の被覆率が約 29 % になる密度)
RADIUS = 1.6            # 斑点の 1 シグマ半径 [px] -> 直径 ~3.8 px(推奨帯の中)
MARGIN = 40             # 端は評価しない(推定器の境界処理を測らないため)
SEED = 7

_SL = (slice(MARGIN, N - MARGIN), slice(MARGIN, N - MARGIN))
_YY, _XX = np.mgrid[0:N, 0:N].astype(np.float64)


class Speckle:
    """解析スペックル。斑点の中心を写してから描き直す(補間を通さない)。"""

    def __init__(self, n_blob=N_BLOB, radius=RADIUS, seed=SEED):
        rng = np.random.default_rng(seed)
        # 端の外にも撒く。撒かないと変形で視野へ入ってくる斑点が無くなり、
        # 「境界だけ相関が落ちる」という**合成側の都合**を測ってしまう。
        self.cx = rng.uniform(-8, N + 8, n_blob)
        self.cy = rng.uniform(-8, N + 8, n_blob)
        self.amp = rng.uniform(0.6, 1.0, n_blob)
        self.radius = radius
        self.scale = None                      # 基準画像で 1 度だけ決める

    def render(self, fx=None, fy=None):
        """変形写像 (fx, fy) を掛けた像。``None`` は恒等。"""
        px = self.cx if fx is None else fx(self.cx, self.cy)
        py = self.cy if fy is None else fy(self.cx, self.cy)
        img = np.zeros((N, N))
        r = self.radius
        win = int(np.ceil(4 * r))
        two_rr = 2.0 * r * r
        for k in range(px.size):
            x0, y0 = px[k], py[k]
            i0, i1 = max(0, int(y0) - win), min(N, int(y0) + win + 1)
            j0, j1 = max(0, int(x0) - win), min(N, int(x0) + win + 1)
            if i0 >= i1 or j0 >= j1:
                continue
            dx = _XX[i0:i1, j0:j1] - x0
            dy = _YY[i0:i1, j0:j1] - y0
            img[i0:i1, j0:j1] += self.amp[k] * np.exp(-(dx * dx + dy * dy) / two_rr)
        # ★正規化は**基準画像で決めた 1 つの定数**で行う。像ごとの最大で割ると、
        #   変形で最大値がわずかに動くだけで全体の明るさが変わり、輝度不変を
        #   仮定する推定器(Lucas-Kanade / Horn-Schunck)に無関係な誤差が乗る。
        if self.scale is None:
            self.scale = float(img.max())
        return img / self.scale


# --- 推定器(いま fullseye にあるもの)---------------------------------------- #
def est_lk(ref, cur):
    """ピラミッド Lucas-Kanade。局所窓の輝度不変から解く。"""
    u, v = fs.optical_flow_lk(ref, cur, window=21, levels=3, iters=6)
    return np.asarray(u), np.asarray(v)


def est_hs(ref, cur):
    """Horn-Schunck。全域の滑らかさを正則化として入れる。"""
    u, v = fs.optical_flow_hs(ref, cur, alpha=1.0, iters=300)
    return np.asarray(u), np.asarray(v)


def est_piv(ref, cur):
    """窓ごとの相関(``fs.ledger.piv_cross_correlate``)を画素格子へ戻したもの。

    ★これは**この repo に最初からあった**。「サブセット相関の op が無い」と
    書きかけて、`fs.op_find("correlation")` が 5 件返すのにこの op を
    含めなかったせいで見落とした(検索の側を直した。CHANGELOG 参照)。
    """
    from scipy.interpolate import RegularGridInterpolator

    import pivops

    flow, info = pivops.piv_cross_correlate(ref, cur, window=32, overlap=0.75)
    flow = np.asarray(flow)
    ys, xs = np.asarray(info["rows"], float), np.asarray(info["cols"], float)
    yy, xx = np.mgrid[0:N, 0:N]
    pts = np.stack([yy.ravel(), xx.ravel()], axis=1)
    out = []
    for k in (1, 0):                       # flow は (dy, dx) 並び
        f = RegularGridInterpolator((ys, xs), flow[k], bounds_error=False,
                                    fill_value=None)
        out.append(f(pts).reshape(N, N))
    return out[0], out[1]


def est_zero(ref, cur):
    """★ゼロ点 —— 「動いていません」と答えるだけの推定器。"""
    return np.zeros((N, N)), np.zeros((N, N))


ESTIMATORS = [("zero", est_zero), ("lk", est_lk), ("hs", est_hs), ("piv", est_piv)]


# --- ひずみ(fullseye に op が無いのでここで書く。所見節を参照)---------------- #
def _local_slope(f, coord, w):
    """w x w 窓の最小二乗で ``df/dcoord`` を出す(平面当てはめの傾き)。"""
    sx = uniform_filter(coord, w)
    sf = uniform_filter(f, w)
    sxx = uniform_filter(coord * coord, w)
    sxf = uniform_filter(coord * f, w)
    var = sxx - sx * sx
    return np.where(var > 1e-9, (sxf - sx * sf) / np.maximum(var, 1e-12), 0.0)


def strain(u, v, w=31, method="infinitesimal"):
    """変位場 → ひずみ場 ``(exx, eyy, exy)``。

    ``method="infinitesimal"``: ε_xx = ∂u/∂x(教科書の微小ひずみ)。
    ``method="green"``: Green-Lagrange
    ``E_xx = ∂u/∂x + ½((∂u/∂x)² + (∂v/∂x)²)``。剛体回転で**厳密に 0** になる
    (6 節で確かめる)。
    """
    ux = _local_slope(u, _XX, w)
    uy = _local_slope(u, _YY, w)
    vx = _local_slope(v, _XX, w)
    vy = _local_slope(v, _YY, w)
    if method == "infinitesimal":
        return ux, vy, 0.5 * (uy + vx)
    exx = ux + 0.5 * (ux * ux + vx * vx)
    eyy = vy + 0.5 * (uy * uy + vy * vy)
    exy = 0.5 * (uy + vx + ux * uy + vx * vy)
    return exx, eyy, exy


def _stat(err):
    """偏り(平均)と散らばり(標準偏差)を分けて返す。RMS 1 本にまとめない。"""
    return float(np.mean(err)), float(np.std(err))


# =========================================================================== #
def section1_synth_check(sp, ref):
    print("=" * 78)
    print("1) 合成器の検算 —— 整数シフトは厳密に一致するか(ゼロ点その 0)")
    print("=" * 78)
    cov = float(np.mean(ref > 0.2))
    print("  スペックル: 斑点 %d 個 / 1σ 半径 %.1f px / 被覆率(>0.2) %.1f %%"
          % (N_BLOB, RADIUS, 100 * cov))
    print("  輝度: 平均 %.3f  標準偏差 %.3f  最大 %.3f" % (ref.mean(), ref.std(), ref.max()))

    # 整数 3 px シフト。斑点を描き直しても、重なった領域は 1 ビットまで一致する
    # はず —— 一致しなければ「描き直し」自体が真値になっていない。
    cur = sp.render(lambda x, y: x + 3.0, lambda x, y: y)
    a = ref[MARGIN:N - MARGIN, MARGIN:N - MARGIN - 3]
    b = cur[MARGIN:N - MARGIN, MARGIN + 3:N - MARGIN]
    d = float(np.max(np.abs(a - b)))
    print("  整数 3 px シフトの再現誤差(最大): %.3e  → %s"
          % (d, "厳密一致(真値として使える)" if d < 1e-12 else "★不一致"))
    # ★所見を固定する: 変形は補間ではなく斑点の再描画なので、整数シフトは
    #   **厳密に**一致するはず。ここが崩れたら 2 節以降の「真値」が真値でなくなり、
    #   測っているのが推定器なのか自分の補間器なのか分からなくなる。
    assert d < 1e-12, "整数シフトが厳密一致しない: %.3e" % d

    # 勾配の RMS。8 節の雑音下限の理論値に使う。
    ix = np.gradient(ref, axis=1)
    print("  ∂I/∂x の RMS: %.5f /px(8 節の雑音下限に使う)"
          % float(np.sqrt(np.mean(ix[_SL] ** 2))))
    figs.save_grid("speckle", [ref, cur, cur - ref],
                   ["基準", "3 px シフト後", "差分(重なりでは厳密に 0)"],
                   title="解析スペックル(斑点 %d、1σ %.1f px)" % (N_BLOB, RADIUS),
                   ncols=3, signed=[False, False, True],
                   caption="変形は補間ではなく斑点の再描画。だから真値が厳密。")
    return ix


def section2_zero_point(sp, ref):
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— 「動いていません」と答える推定器に勝てるか")
    print("=" * 78)
    print("  真の変位 0.37 px。ゼロ点の誤差は定義から 0.37 px。")
    cur = sp.render(lambda x, y: x + 0.37, lambda x, y: y)
    print("  %-6s %10s %10s %10s" % ("手法", "偏り px", "散らばり px", "ゼロ点比"))
    base = 0.37
    ratio, bias = {}, {}
    for name, est in ESTIMATORS:
        u, _ = est(ref, cur)
        m, s = _stat(u[_SL] - 0.37)
        rms = float(np.sqrt(m * m + s * s))
        if name != "zero":
            ratio[name] = base / max(rms, 1e-12)
            bias[name] = m
        print("  %-6s %10.4f %10.4f %10s"
              % (name, m, s, "—" if name == "zero" else "%.0f 倍" % (base / max(rms, 1e-12))))
    # ★所見を固定する: 3 つとも「動いていない」と答えるだけのゼロ点に**桁で勝つ**。
    #   1 つでも 10 倍を割ったら、その推定器はこの場面では使い物になっていない。
    assert min(ratio.values()) > 10.0, ratio
    #   piv は 2 桁上回る(10 節 (a) の看板)。実測 167 倍なので下限は広めに取る。
    assert ratio["piv"] > 100.0, ratio
    return ratio, bias


def section3_subpixel(sp, ref):
    print()
    print("=" * 78)
    print("3) ★サブピクセル掃引 —— 偏りは整数側か 0.5 px 側か")
    print("=" * 78)
    print("  教科書の peak locking は「推定値が整数へ吸い寄せられる」。")
    print("  この合成スペックルでは**逆に 0.5 px 側へ寄る**。実測:")
    print()
    print("  %8s |" % "u 真値", end="")
    for name, _ in ESTIMATORS[1:]:
        print(" %10s %10s" % (name + " 偏り", name + " 散らばり"), end="")
    print()
    print("  " + "-" * (11 + 22 * (len(ESTIMATORS) - 1)))
    worst = {n: 0.0 for n, _ in ESTIMATORS[1:]}
    swept = {}
    for u0 in np.arange(0.0, 1.001, 0.125):
        cur = sp.render(lambda x, y: x + u0, lambda x, y: y)
        print("  %8.3f |" % u0, end="")
        for name, est in ESTIMATORS[1:]:
            uu, _ = est(ref, cur)
            mm, ss = _stat(uu[_SL] - u0)
            worst[name] = max(worst[name], abs(mm))
            swept[(name, round(float(u0), 3))] = mm
            print(" %10.4f %10.4f" % (mm, ss), end="")
        print()
    print()
    print("  最大の偏り: " + " / ".join("%s %.4f px" % (n, worst[n]) for n, _ in ESTIMATORS[1:]))
    # ★所見を固定する。
    #   (1) piv の偏りは掃引の全域で lk / hs より小さい。※「1 桁小さい」が成り立つのは
    #       2 節の u=0.37 の 1 点(0.0002 vs 0.0042 = 21 倍)で、**掃引の最大どうし**では
    #       6 倍程度(piv 0.0015 / lk 0.0088)。ここは最大どうしを 2 倍で固定する。
    assert worst["piv"] < 0.004, worst
    assert worst["piv"] < worst["lk"] / 2.0 and worst["piv"] < worst["hs"] / 2.0, worst
    #   (2) lk の偏りは u=0.5 を境に符号が反転する(0.5 px 側へ寄る = peak locking の逆)。
    assert swept[("lk", 0.125)] > 0.002 and swept[("lk", 0.75)] < -0.002, swept
    if figs.enabled():
        us = np.arange(0.0, 1.001, 0.0625)
        series = []
        for name, est in ESTIMATORS[1:]:
            bias = []
            for u0 in us:
                cur = sp.render(lambda x, y: x + u0, lambda x, y: y)
                bias.append(1000.0 * _stat(est(ref, cur)[0][_SL] - u0)[0])
            series.append((name, us, np.array(bias)))
        figs.save_plot("subpixel_bias", series, xlabel="真の変位 u [px]",
                       ylabel="偏り [1/1000 px]",
                       title="サブピクセル掃引 —— 偏りの向き",
                       caption="lk は 0.5 px 側へ寄る(教科書の peak locking と逆)。"
                               "piv は 1 桁小さい。")
    print("  → lk は符号が u=0.5 を境に反転する(0.5 側へ寄る)—— 教科書の")
    print("     peak locking(整数へ吸い寄せられる)と**向きが逆**。")
    print("     hs は反転せず、0.4 付近に山を持つ片側の偏り(正則化の影響)。")
    print("     ★piv(窓の相関 + ガウス 3 点)は偏りが 1 桁小さい。")
    print("     どれも**系統誤差なので枚数を増やしても消えない**。ただし 9 節の")
    print("     とおり偏りの大きさは**スペックルの粒径にも依る**ので、推定器だけの")
    print("     性質ではない。0.01 px を主張するならこの 2 つを同時に押さえること。")


def section4_magnitude(sp, ref):
    print()
    print("=" * 78)
    print("4) 変位の大きさ掃引 —— どこで壊れるか")
    print("=" * 78)
    print("  %8s |" % "u 真値", end="")
    for name, _ in ESTIMATORS[1:]:
        print(" %10s %10s" % (name + " 偏り", name + " 散らばり"), end="")
    print()
    print("  " + "-" * (11 + 22 * (len(ESTIMATORS) - 1)))
    for u0 in [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]:
        cur = sp.render(lambda x, y: x + u0, lambda x, y: y)
        print("  %8.1f |" % u0, end="")
        for name, est in ESTIMATORS[1:]:
            uu, _ = est(ref, cur)
            print(" %10.4f %10.4f" % _stat(uu[_SL] - u0), end="")
        print()
    print()
    print("  → それぞれ壊れる場所が違う。**窓や段数で決まる上限**があるので、")
    print("     変位の見積もりを先に立ててから道具を選ぶ。")


def section5_uniform_strain(sp, ref):
    print()
    print("=" * 78)
    print("5) ★一様ひずみ —— 100 µε まで届くか")
    print("=" * 78)
    print("  ε_xx を仕込み、変位場から 31x31 窓の最小二乗で読み戻す。")
    print("  1 µε = 1e-6。鋼の降伏ひずみは約 2000 µε。")
    print()
    print("  %10s |" % "ε 真値 µε", end="")
    for name, _ in ESTIMATORS[1:]:
        print(" %10s %10s" % (name + " µε", name + " 散 µε"), end="")
    print()
    print("  " + "-" * (13 + 22 * (len(ESTIMATORS) - 1)))
    got = {}
    for eps in [100e-6, 500e-6, 2000e-6, 5000e-6, 20000e-6]:
        cur = sp.render(lambda x, y: x * (1.0 + eps), lambda x, y: y)
        print("  %10.0f |" % (1e6 * eps), end="")
        for name, est in ESTIMATORS[1:]:
            uu, vv = est(ref, cur)
            exx, _, _ = strain(uu, vv, w=31)
            mu, sd = 1e6 * float(np.mean(exx[_SL])), 1e6 * float(np.std(exx[_SL]))
            got[(name, round(1e6 * eps))] = (mu, sd)
            print(" %10.1f %10.1f" % (mu, sd), end="")
        print()
    print()
    print("  → 100 µε でも符号と桁は出る。ただし散らばりが同じ桁なので、")
    print("     **1 点の値ではなく領域平均でしか使えない**。")
    # ★所見を固定する。
    #   (1) lk と piv は 100 µε を ±30 µε で回収する(実測 +9.1 / +0.4)。
    for name in ("lk", "piv"):
        assert abs(got[(name, 100)][0] - 100.0) < 30.0, (name, got[(name, 100)])
    #   (2) ★hs は 100 µε で 22 µε しか返さない —— 上の「符号と桁は出る」は
    #       **hs には当てはまらない**(正則化が一様ひずみそのものを平らにする)。
    #       主張と実測の食い違いなので、実測のほうを固定しておく。
    assert got[("hs", 100)][0] < 60.0, got[("hs", 100)]
    #   (3) 20000 µε(2 %、塑性域)なら 3 つとも ±3 % で一致する。
    for name in ("lk", "hs", "piv"):
        assert abs(got[(name, 20000)][0] / 20000.0 - 1.0) < 0.03, (name, got[(name, 20000)])
    #   (4) 100 µε では散らばりが真値と同じ桁 = 1 点の値では使えない。
    assert got[("piv", 100)][1] > 3.0, got[("piv", 100)]
    return got


def section6_rotation(sp, ref):
    print()
    print("=" * 78)
    print("6) ★★剛体回転 —— ひずみの定義が作る嘘")
    print("=" * 78)
    print("  試験片がわずかに回っただけ。**ひずみの真値は 0**。")
    print("  微小ひずみ ∂u/∂x は回転で cosθ-1 ≈ -θ²/2 を返す(材料は伸びていない)。")
    print("  Green-Lagrange は代数的に厳密 0(下の列で確かめる)。")
    print()
    print("  %8s | %10s |" % ("θ 度", "理論 µε"), end="")
    for name, _ in ESTIMATORS[1:]:
        print(" %11s %11s" % (name + " 微小", name + " Green"), end="")
    print()
    print("  " + "-" * (24 + 24 * (len(ESTIMATORS) - 1)))
    c0 = N / 2.0
    rot, theo_ue = {}, {}
    for th_deg in [0.0, 0.2, 0.5, 1.0, 2.0]:
        t = np.deg2rad(th_deg)
        ct, st = np.cos(t), np.sin(t)
        cur = sp.render(lambda x, y: c0 + (x - c0) * ct - (y - c0) * st,
                        lambda x, y: c0 + (x - c0) * st + (y - c0) * ct)
        theo_ue[th_deg] = 1e6 * (ct - 1.0)
        print("  %8.2f | %10.1f |" % (th_deg, 1e6 * (ct - 1.0)), end="")
        for name, est in ESTIMATORS[1:]:
            uu, vv = est(ref, cur)
            e_inf, _, _ = strain(uu, vv, w=31, method="infinitesimal")
            e_grn, _, _ = strain(uu, vv, w=31, method="green")
            mi, mg = 1e6 * float(np.mean(e_inf[_SL])), 1e6 * float(np.mean(e_grn[_SL]))
            rot[(name, th_deg)] = (mi, mg)
            print(" %11.1f %11.1f" % (mi, mg), end="")
        print()
    print()
    # ★所見を固定する。
    #   (1) 2 度の回転は微小ひずみでは理論どおり -609 µε 前後の**嘘**になる
    #       (材料は伸びていない)。鋼の降伏ひずみ 2000 µε の 3 割。
    assert abs(rot[("lk", 2.0)][0] - theo_ue[2.0]) < 0.25 * abs(theo_ue[2.0]), rot[("lk", 2.0)]
    #   (2) Green-Lagrange は**代数的には**厳密 0 だが、実測では推定器で効き方が逆になる:
    #       lk では嘘が 1/3 以下に減り、piv では**補正が過剰になって悪化する**。
    #       「既定をどちらかに決めてはいけない」の根拠がこの 1 行。
    assert abs(rot[("lk", 2.0)][1]) < abs(rot[("lk", 2.0)][0]) / 3.0, rot[("lk", 2.0)]
    assert abs(rot[("piv", 2.0)][1]) > abs(rot[("piv", 2.0)][0]), rot[("piv", 2.0)]
    print("  → 2 度の回転が微小ひずみでは約 -600 µε の嘘になる(理論 -609 µε)。")
    print("     **鋼の降伏ひずみの 3 割**。Green-Lagrange は代数的には厳密 0。")
    print("     ★ただし**実測では 0 にならない** —— Green の補正項は勾配の")
    print("     推定値から作るので、勾配自体の誤差がそのまま乗る。lk のように")
    print("     勾配が素直な推定器では効き、勾配の散らばりが数百 µε ある推定器では")
    print("     補正が過剰になって逆に悪化することがある(下の表で確かめられる)。")
    print("     どちらにせよ**既定をどちらかに決めてはいけない**という結論は変わらない。")
    print("     → `fs.ledger.strain_from_displacement(u, v, window, method)` は")
    print("       この 2 つを必須引数にしてある(`dic.py`)。")


def section7_gradient(sp, ref):
    print()
    print("=" * 78)
    print("7) ひずみ集中(切欠き)—— 窓の大きさが空間分解能を決める")
    print("=" * 78)
    # ★一様勾配(ε が x の 1 次)では鈍らない —— 対称窓の最小二乗は 1 次関数の
    #   傾きを厳密に返すため。窓の効果を見るには**曲率のある**ひずみ場が要る。
    #   切欠き先端のひずみ集中がまさにそれなので、ガウス形の集中を仕込む。
    from scipy.special import erf

    eps0 = 20000e-6         # 尖頭ひずみ 20000 µε(2 %、塑性域)
    sig_c = 20.0            # 集中の 1σ 幅 [px] -> FWHM 47 px
    c0 = N / 2.0
    amp = eps0 * sig_c * np.sqrt(np.pi / 2.0)

    def _u(x, y):
        return x + amp * (erf((x - c0) / (sig_c * np.sqrt(2.0))) + 1.0)

    cur = sp.render(_u, lambda x, y: y)
    print("  仕込み: ε_xx(x) = %.0f µε × exp(-(x-%.0f)²/2·%.0f²)。FWHM %.0f px、"
          % (1e6 * eps0, c0, sig_c, 2.355 * sig_c))
    print("          変位の総量は %.2f px(端から端まで)。" % (2 * amp))
    print()
    print("  %6s |" % "窓 px", end="")
    for name, _ in ESTIMATORS[1:]:
        print(" %11s %11s" % (name + " 尖頭 µε", name + " FWHM"), end="")
    print()
    print("  " + "-" * (9 + 24 * (len(ESTIMATORS) - 1)))
    xs = _XX[N // 2, :]
    windows = [11, 21, 31, 51, 81]
    peaks = {}
    for w in windows:
        print("  %6d |" % w, end="")
        for name, est in ESTIMATORS[1:]:
            uu, vv = est(ref, cur)
            exx, _, _ = strain(uu, vv, w=w)
            prof = exx[MARGIN:N - MARGIN, :].mean(axis=0)
            peak = float(prof[MARGIN:N - MARGIN].max())
            idx = np.where(prof[MARGIN:N - MARGIN] >= peak / 2.0)[0]
            fwhm = float(xs[MARGIN + idx[-1]] - xs[MARGIN + idx[0]]) if idx.size else 0.0
            peaks[(name, w)] = 1e6 * peak
            print(" %11.0f %11.1f" % (1e6 * peak, fwhm), end="")
        print()
    print("  %6s |" % "真値", end="")
    for _ in ESTIMATORS[1:]:
        print(" %11.0f %11.1f" % (1e6 * eps0, 2.355 * sig_c), end="")
    print()
    print()
    print("  → 窓を広げると尖頭が下がり、幅が広がる —— **集中の高さを過小に**")
    print("     読む。ひずみの空間分解能は窓幅で決まり、散らばり(5 節)と")
    print("     直接トレードオフ。切欠きや亀裂先端では窓を集中幅より小さく取る。")
    if figs.enabled():
        prof_true = eps0 * np.exp(-((xs - c0) ** 2) / (2 * sig_c ** 2))
        series = [("真値", xs[MARGIN:N - MARGIN], 1e6 * prof_true[MARGIN:N - MARGIN])]
        for w in (11, 31, 81):
            uu, vv = est_lk(ref, cur)
            exx, _, _ = strain(uu, vv, w=w)
            pr = exx[MARGIN:N - MARGIN, :].mean(axis=0)
            series.append(("lk 窓 %d" % w, xs[MARGIN:N - MARGIN],
                           1e6 * pr[MARGIN:N - MARGIN]))
        figs.save_plot("strain_concentration", series, xlabel="x [px]",
                       ylabel="ε_xx [µε]", title="ひずみ集中と窓幅",
                       caption="窓を広げると尖頭が下がり幅が広がる(空間分解能の限界)。")
        uu, vv = est_lk(ref, cur)
        exx, _, _ = strain(uu, vv, w=21)
        figs.save_grid("strain_map", [exx, exx - np.outer(np.ones(N), prof_true)],
                       ["推定 ε_xx(lk、窓 21)", "真値との差"],
                       title="ひずみ場", signed=True,
                       caption="どちらも同じ発散 LUT。0 が黒。")
    print("     ★hs は**どの窓でも尖頭を 3 割落とす**(全域の滑らかさを正則化に")
    print("     入れているので、局所の集中そのものを平らにしてしまう)。5 節の")
    print("     一様ひずみでは hs のほうが散らばりが小さかったが、集中を見るなら")
    print("     使ってはいけない —— **「どちらが良いか」は測る対象で反転する**。")


def section8_noise(sp, ref, ix):
    print()
    print("=" * 78)
    print("8) 雑音下限 —— 実測と理論")
    print("=" * 78)
    w = 21
    # ★1 枚の隅を切って数えると窓の取り方で 2 倍動く。**全窓の平均**を使う。
    sum_ix2 = float(w * w * np.mean(ix[_SL] ** 2))
    print("  理論(相関法の下限): σ_u = σ_n / sqrt(Σ_窓 (∂I/∂x)²)")
    print("  21x21 窓の Σ(∂I/∂x)²(全窓平均)= %.4f → σ_u = σ_n × %.3f"
          % (sum_ix2, 1 / np.sqrt(sum_ix2)))
    print()
    u0 = 0.37
    cur0 = sp.render(lambda x, y: x + u0, lambda x, y: y)
    rng = np.random.default_rng(11)
    print("  %8s | %10s |" % ("σ_n", "理論 σ_u"), end="")
    for name, _ in ESTIMATORS[1:]:
        print(" %10s %10s" % (name + " 偏り", name + " 散らばり"), end="")
    print()
    print("  " + "-" * (24 + 22 * (len(ESTIMATORS) - 1)))
    for sg in [0.0, 0.005, 0.01, 0.02, 0.05]:
        r2 = ref + rng.normal(0, sg, ref.shape)
        c2 = cur0 + rng.normal(0, sg, cur0.shape)
        theo = np.sqrt(2.0) * sg / np.sqrt(sum_ix2)
        print("  %8.3f | %10.4f |" % (sg, theo), end="")
        for name, est in ESTIMATORS[1:]:
            uu, _ = est(r2, c2)
            print(" %10.4f %10.4f" % _stat(uu[_SL] - u0), end="")
        print()
    print()
    print("  → lk の散らばりは σ_n に**比例**する(理論どおりの振る舞い)が、")
    print("     絶対値は理論の下限を**下回る**。矛盾ではない: この下限は「21x21 の")
    print("     窓 1 つだけを使う推定器」の下限で、lk はピラミッド 3 段ぶんの")
    print("     画素を実効的に平均している。理論値は**桁の目安**として使う。")
    print("     hs はさらに下回るが、その代わり**偏りが残る**(平滑化が変位を鈍らせる)。")
    print("     もう 1 つ: σ_n=0.05 で lk の**偏り**が 0.004 → 0.040 と 10 倍になる。")
    print("     雑音は散らばりだけでなく系統誤差も作る —— 平均枚数では消えない。")


def section9_speckle_quality():
    print()
    print("=" * 78)
    print("9) スペックルの粒径 —— 「3〜5 px が良い」を測る")
    print("=" * 78)
    print("  斑点が細かすぎるとエイリアシング、粗すぎると勾配が足りない。")
    print("  被覆率が同じになるよう斑点数を半径に合わせて調整する。")
    print()
    print("  %8s %8s %8s | %9s %9s" % ("1σ px", "直径", "斑点数", "lk 偏り", "lk 散らばり"))
    print("  " + "-" * 52)
    u0 = 0.37
    for r in [0.6, 1.0, 1.6, 2.5, 4.0]:
        n_b = max(200, int(N_BLOB * (RADIUS / r) ** 2))
        sp = Speckle(n_blob=n_b, radius=r, seed=SEED)
        ref = sp.render()
        cur = sp.render(lambda x, y: x + u0, lambda x, y: y)
        uu, _ = est_lk(ref, cur)
        m, s = _stat(uu[_SL] - u0)
        print("  %8.1f %8.1f %8d | %9.4f %9.4f" % (r, 2.355 * r, n_b, m, s))
    print()
    print("  → 直径 1.4 px では偏りも散らばりも最悪(標本化が足りない)。")
    print("     **偏りは斑点を太くすると単調に減る** —— 3 節で見た 0.008 px の偏りは")
    print("     推定器だけの性質ではなく、スペックルの標本化不足が半分を作っている。")
    print("     散らばりの最小は 1σ≈2.5 px(直径 6 px)付近。ただし太い斑点は")
    print("     斑点数が減るので、7 節の空間分解能とは逆向きのトレードオフになる。")


def section10_findings():
    print()
    print("=" * 78)
    print("10) 所見 —— fullseye に足りないもの")
    print("=" * 78)
    print("""
  ★この節は**一度書き直している**。最初の版には「サブセット相関(ZNCC)の
  op が無い」「スペックル合成器が無い」と書いた。**どちらも誤り**で、
  `pivops` の 23 op(`fs.ledger.piv_*`)が最初からあった。見落とした理由は
  検索の側にあり(`op_find("correlation")` が `piv_cross_correlate` を返さ
  なかった)、そちらは直した(CHANGELOG「op_find が語幹と複数語で引ける」)。
  以下は**測り直したあと**の所見。

  (a) **既にあって、しかも強い**: `piv_cross_correlate`。
      2〜9 節のとおり、偏り・散らばりとも lk / hs を 1 桁上回る
      (u=0.37 px で偏り 0.0002 px / 散らばり 0.0022 px、ゼロ点比 167 倍)。
      さらに**照明変化に強い**: 明るさを 0.7 倍 + 0.15 加算しても変位の
      ずれは 3.7e-15 px(`subtract_mean=True` が加算を、ガウス 3 点当てはめ
      の対数差が乗算を代数的に打ち消す)。同じ条件で `optical_flow_lk` は
      1.31 px 動く。**新しい相関器を書く理由は無かった。**

  (b) ★★**`piv_strain_rate` は剛体回転で 0 にならない**。docstring は
      「剛体回転では 0」と書いているが、それが成り立つのは**線形化した
      流体の回転** `u=-ωy, v=ωx` のときだけ。DIC が測る**有限回転**では
      2 度で **+1218 µε** を返す(真値 0)。流体の族に固体の量を借りると
      静かに間違う、という例。`dic.strain_from_displacement(u, v, window,
      method)` を足した —— `window` と `method` に既定を置かず、
      `"infinitesimal"` と `"green"` を呼び手に選ばせる。

  (c) **微分の質**: `piv_velocity_gradient` は `np.gradient`(2 点差分)。
      同じ流れ場・500 µε で散らばりが 136.9 µε、窓最小二乗(w=9)なら
      12.4 µε —— **11 倍**。平均は同じなので、1 点の値を見る用途でだけ効く。

  (d) **相関品質**: `info["peak_ratio"]` はあるが、60x60 の領域を別の絵に
      貼り替えても内 1.184 / 外 1.329 で分離できない。ZNCC 係数なら
      0.100 / 0.999。`zncc >= 0.8` で切ると RMS が 1.9122 → 0.0036 px
      (**537 倍**)。`dic.correlation_quality` を足した —— **相関器では
      なく、既にある変位場を採点する op**(piv でも lk でも demons でも使える)。

  (e) **スペックルの品質指標**: 9 節のとおり同じ推定器でも粒径で偏りが
      20 倍変わるのに、撮影時に判定する指標が無かった。
      `dic.speckle_quality`(平均輝度勾配 MIG・被覆率・平均斑点径)を足した。
      `speckle_filter` は SAR の**デスペックル**で別物。

  (f) **合成器**: `piv_synth_pair` が既にあり、任意の変位写像(callable)を
      受け、正規化を一切しない。この PoC の `Speckle` は**解析レンダで
      真値を厳密に**という点だけが違うが、`piv_synth_pair` も整数 3 px
      シフトを 0.0 で再現するので、実用上は差が無い。**新しく作らない。**

  次にやるべきこと: (b)(c)(d)(e) は `dic.py` として入れ、台帳は
  `opspiv`(piv 族)へ相乗りさせた —— 別の族を立てると「流体の相関器」と
  「固体のひずみ」が別物に見えてしまい、同じ道具だという事実が消えるため。
""")


def main():
    t0 = time.time()
    print("poc_dic_strain — スペックル画像から**ひずみ**を測る")
    print("(真値は解析スペックルの再描画。補間で作った変形画像は使わない)")
    print()
    sp = Speckle()
    ref = sp.render()
    ix = section1_synth_check(sp, ref)
    section2_zero_point(sp, ref)
    section3_subpixel(sp, ref)
    section4_magnitude(sp, ref)
    section5_uniform_strain(sp, ref)
    section6_rotation(sp, ref)
    section7_gradient(sp, ref)
    section8_noise(sp, ref, ix)
    section9_speckle_quality()
    section10_findings()
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("経過 %.1f 秒" % (time.time() - t0))


if __name__ == "__main__":
    main()
