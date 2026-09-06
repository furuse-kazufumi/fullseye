# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_dic_strain — スペックル画像から**ひずみ**を測る(DIC、デジタル画像相関)。
真値を仕込んだ合成変形で、変位 0.01 px 台・ひずみ 100 µε 台まで追い込む PoC。

    py -3.11 examples/poc_dic_strain.py

【この PoC が答える問い】
材料試験室でいちばん普通の問い —「試験片にスペックルを吹いて写真を撮った。
ひずみゲージを貼らずに、画像だけでひずみが測れるか。どこまで信じてよいか」。
答えは「変位は 0.01 px、ひずみは 100 µε 台まで測れる。ただし**試験機の
わずかな回転が数百 µε の嘘のひずみを作る**ので、ひずみの定義を間違えると
鋼の降伏ひずみの 3 割に相当する誤差が乗る」。

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
  * ひずみ勾配(曲げ、ε_xx = κx)—— 窓の大きさが空間分解能を決める
  * 雑音(σ = 0〜0.05)—— 雑音下限の理論値と突き合わせる

【節立て】
 1) 合成器の検算 —— 整数シフトが厳密に一致するか(ゼロ点その 0)
 2) ★ゼロ点 —— 「変位 0 と答える」推定器に勝てるか
 3) ★サブピクセル掃引 —— 偏りは 0.5 px 側へ寄る(教科書の peak locking と逆)
 4) 変位の大きさ掃引 —— どこで壊れるか
 5) ★一様ひずみ —— 100 µε まで届くか
 6) ★★剛体回転 —— 微小ひずみの定義が作る嘘。Green-Lagrange なら厳密に 0
 7) ひずみ勾配 —— 窓の大きさ vs 空間分解能(必ず鈍る)
 8) 雑音下限 —— 実測と理論 σ_u = σ_n / sqrt(Σ I_x^2)
 9) スペックルの粒径 —— 「3〜5 px が良い」を測る
10) 順位表と所見

【この PoC で分かった fullseye 側の穴 → 末尾の「所見」節】
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fullseye as fs                                            # noqa: E402

# --- 合成スペックルの諸元 ---------------------------------------------------- #
N = 256                 # 画素
N_BLOB = 3000           # 斑点の数(被覆率 ~50% になる密度)
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


def est_zero(ref, cur):
    """★ゼロ点 —— 「動いていません」と答えるだけの推定器。"""
    return np.zeros((N, N)), np.zeros((N, N))


ESTIMATORS = [("zero", est_zero), ("lk", est_lk), ("hs", est_hs)]


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

    # 勾配の RMS。8 節の雑音下限の理論値に使う。
    ix = np.gradient(ref, axis=1)
    print("  ∂I/∂x の RMS: %.5f /px(8 節の雑音下限に使う)"
          % float(np.sqrt(np.mean(ix[_SL] ** 2))))
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
    for name, est in ESTIMATORS:
        u, _ = est(ref, cur)
        m, s = _stat(u[_SL] - 0.37)
        rms = float(np.sqrt(m * m + s * s))
        print("  %-6s %10.4f %10.4f %10s"
              % (name, m, s, "—" if name == "zero" else "%.0f 倍" % (base / max(rms, 1e-12))))


def section3_subpixel(sp, ref):
    print()
    print("=" * 78)
    print("3) ★サブピクセル掃引 —— 偏りは整数側か 0.5 px 側か")
    print("=" * 78)
    print("  教科書の peak locking は「推定値が整数へ吸い寄せられる」。")
    print("  この合成スペックルでは**逆に 0.5 px 側へ寄る**。実測:")
    print()
    print("  %8s | %9s %9s | %9s %9s" % ("u 真値", "lk 偏り", "lk 散らばり", "hs 偏り", "hs 散らばり"))
    print("  " + "-" * 62)
    fr = np.arange(0.0, 1.001, 0.125)
    worst = {"lk": 0.0, "hs": 0.0}
    for u0 in fr:
        cur = sp.render(lambda x, y: x + u0, lambda x, y: y)
        row = []
        for name, est in ESTIMATORS[1:]:
            uu, _ = est(ref, cur)
            m, s = _stat(uu[_SL] - u0)
            row += [m, s]
            worst[name] = max(worst[name], abs(m))
        print("  %8.3f | %9.4f %9.4f | %9.4f %9.4f" % (u0, *row))
    print()
    print("  最大の偏り: lk %.4f px / hs %.4f px" % (worst["lk"], worst["hs"]))
    print("  → 偏りの符号が u=0.5 を境に反転する(0.5 側へ寄る)。**系統誤差なので")
    print("     枚数を増やしても消えない**。0.01 px を主張するならここが天井。")


def section4_magnitude(sp, ref):
    print()
    print("=" * 78)
    print("4) 変位の大きさ掃引 —— どこで壊れるか")
    print("=" * 78)
    print("  %8s | %9s %9s | %9s %9s" % ("u 真値", "lk 偏り", "lk 散らばり", "hs 偏り", "hs 散らばり"))
    print("  " + "-" * 62)
    for u0 in [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]:
        cur = sp.render(lambda x, y: x + u0, lambda x, y: y)
        row = []
        for name, est in ESTIMATORS[1:]:
            uu, _ = est(ref, cur)
            row += list(_stat(uu[_SL] - u0))
        print("  %8.1f | %9.4f %9.4f | %9.4f %9.4f" % (u0, *row))


def section5_uniform_strain(sp, ref):
    print()
    print("=" * 78)
    print("5) ★一様ひずみ —— 100 µε まで届くか")
    print("=" * 78)
    print("  ε_xx を仕込み、変位場から 31x31 窓の最小二乗で読み戻す。")
    print("  1 µε = 1e-6。鋼の降伏ひずみは約 2000 µε。")
    print()
    print("  %10s | %10s %10s | %10s %10s"
          % ("ε 真値 µε", "lk µε", "lk 散 µε", "hs µε", "hs 散 µε"))
    print("  " + "-" * 62)
    for eps in [100e-6, 500e-6, 2000e-6, 5000e-6, 20000e-6]:
        cur = sp.render(lambda x, y: x * (1.0 + eps), lambda x, y: y)
        row = []
        for name, est in ESTIMATORS[1:]:
            uu, vv = est(ref, cur)
            exx, _, _ = strain(uu, vv, w=31)
            row += [1e6 * float(np.mean(exx[_SL])), 1e6 * float(np.std(exx[_SL]))]
        print("  %10.0f | %10.1f %10.1f | %10.1f %10.1f" % (1e6 * eps, *row))
    print()
    print("  → 100 µε でも符号と桁は出る。ただし散らばりが同じ桁なので、")
    print("     **1 点の値ではなく領域平均でしか使えない**。")


def section6_rotation(sp, ref):
    print()
    print("=" * 78)
    print("6) ★★剛体回転 —— ひずみの定義が作る嘘")
    print("=" * 78)
    print("  試験片がわずかに回っただけ。**ひずみの真値は 0**。")
    print("  微小ひずみ ∂u/∂x は回転で cosθ-1 ≈ -θ²/2 を返す(材料は伸びていない)。")
    print("  Green-Lagrange は代数的に厳密 0(下の列で確かめる)。")
    print()
    print("  %8s | %10s | %11s %11s | %11s %11s"
          % ("θ 度", "理論 µε", "lk 微小 µε", "lk Green µε", "hs 微小 µε", "hs Green µε"))
    print("  " + "-" * 76)
    c0 = N / 2.0
    for th_deg in [0.0, 0.2, 0.5, 1.0, 2.0]:
        t = np.deg2rad(th_deg)
        ct, st = np.cos(t), np.sin(t)
        cur = sp.render(lambda x, y: c0 + (x - c0) * ct - (y - c0) * st,
                        lambda x, y: c0 + (x - c0) * st + (y - c0) * ct)
        row = [th_deg, 1e6 * (ct - 1.0)]
        for name, est in ESTIMATORS[1:]:
            uu, vv = est(ref, cur)
            e_inf, _, _ = strain(uu, vv, w=31, method="infinitesimal")
            e_grn, _, _ = strain(uu, vv, w=31, method="green")
            row += [1e6 * float(np.mean(e_inf[_SL])), 1e6 * float(np.mean(e_grn[_SL]))]
        print("  %8.2f | %10.1f | %11.1f %11.1f | %11.1f %11.1f" % tuple(row))
    print()
    print("  → 2 度の回転が微小ひずみでは約 -600 µε の嘘になる。**鋼の降伏ひずみの")
    print("     3 割**。Green-Lagrange に替えるとほぼ消える(残りは推定器の誤差)。")
    print("     ひずみを出す op を作るなら、既定はどちらかを黙って選んではいけない。")


def section7_gradient(sp, ref):
    print()
    print("=" * 78)
    print("7) ひずみ勾配(曲げ)—— 窓の大きさが空間分解能を決める")
    print("=" * 78)
    kappa = 4.0e-5          # ε_xx = kappa*(x - c0) -> 端で ±5120 µε
    c0 = N / 2.0
    cur = sp.render(lambda x, y: x + 0.5 * kappa * (x - c0) ** 2, lambda x, y: y)
    print("  仕込み: ε_xx = κ(x-c0)、κ = %.1e /px。x=%d で %.0f µε、x=%d で %.0f µε。"
          % (kappa, MARGIN, 1e6 * kappa * (MARGIN - c0), N - MARGIN,
             1e6 * kappa * (N - MARGIN - c0)))
    print()
    print("  %6s | %12s %12s | %12s %12s"
          % ("窓 px", "lk 傾き誤差", "lk 残差 µε", "hs 傾き誤差", "hs 残差 µε"))
    print("  " + "-" * 64)
    for w in [11, 21, 31, 51, 81]:
        row = [w]
        for name, est in ESTIMATORS[1:]:
            uu, vv = est(ref, cur)
            exx, _, _ = strain(uu, vv, w=w)
            xs = _XX[_SL].ravel()
            es = exx[_SL].ravel()
            k_hat = np.polyfit(xs, es, 1)[0]
            resid = es - np.polyval(np.polyfit(xs, es, 1), xs)
            row += [k_hat / kappa - 1.0, 1e6 * float(np.std(resid))]
        print("  %6d | %11.2f%% %12.1f | %11.2f%% %12.1f"
              % (row[0], 100 * row[1], row[2], 100 * row[3], row[4]))
    print()
    print("  → 窓を広げると散らばりは下がるが**勾配そのものが鈍る**。")
    print("     ひずみの『空間分解能』は窓幅で決まり、精度と直接トレードオフ。")


def section8_noise(sp, ref, ix):
    print()
    print("=" * 78)
    print("8) 雑音下限 —— 実測と理論")
    print("=" * 78)
    w = 21
    sum_ix2 = float(np.sum(ix[_SL][:w, :w] ** 2))    # 1 窓ぶんの Σ(∂I/∂x)²
    print("  理論(相関法の下限): σ_u = σ_n / sqrt(Σ_窓 (∂I/∂x)²)")
    print("  21x21 窓の Σ(∂I/∂x)² = %.4f → σ_u = σ_n × %.3f" % (sum_ix2, 1 / np.sqrt(sum_ix2)))
    print()
    u0 = 0.37
    cur0 = sp.render(lambda x, y: x + u0, lambda x, y: y)
    rng = np.random.default_rng(11)
    print("  %8s | %10s | %10s %10s | %10s %10s"
          % ("σ_n", "理論 σ_u", "lk 偏り", "lk 散らばり", "hs 偏り", "hs 散らばり"))
    print("  " + "-" * 68)
    for s in [0.0, 0.005, 0.01, 0.02, 0.05]:
        r2 = ref + rng.normal(0, s, ref.shape)
        c2 = cur0 + rng.normal(0, s, cur0.shape)
        # 2 枚とも雑音を持つので、差の雑音は √2 倍。
        theo = np.sqrt(2.0) * s / np.sqrt(sum_ix2)
        row = [s, theo]
        for name, est in ESTIMATORS[1:]:
            uu, _ = est(r2, c2)
            row += list(_stat(uu[_SL] - u0))
        print("  %8.3f | %10.4f | %10.4f %10.4f | %10.4f %10.4f" % tuple(row))
    print()
    print("  → lk の散らばりは理論に沿って σ_n に比例。hs は正則化が効いて下回るが、")
    print("     その代わり**偏りが残る**(平滑化が変位そのものを鈍らせる)。")


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
    print("  → 直径 1.4 px(1σ=0.6)では散らばりが跳ね上がる。標本化定理の下限。")
    print("     太くしても偏りは消えない —— 偏りは推定器の側の性質。")


def section10_findings():
    print()
    print("=" * 78)
    print("10) 所見 —— fullseye に足りないもの")
    print("=" * 78)
    print("""
  (a) ★**サブセット相関(ZNCC)の op が無い**。DIC の中核はテンプレート相関で、
      材料試験の標準手法(ZNCC + サブピクセル反復、IC-GN)はこれ。いま代用
      できるのは `optical_flow_lk` / `optical_flow_hs` / `demons_register` の
      3 本だけで、どれも**輝度不変を仮定する**ので照明が変わると使えない。
      ZNCC は平均と分散を正規化するので照明変化に強い —— この差は実験室では
      決定的(試験中に照明は必ず変わる)。

  (b) ★★**変位場 → ひずみ場の op が無い**。この PoC では 40 行書いた。
      しかも 6 節が示すとおり、**微小ひずみと Green-Lagrange のどちらを
      返すかで 2 度の回転が 600 µε の嘘になる**。既定を黙って選ぶ設計に
      してはいけない類の分岐。`strain_from_displacement(u, v, window, method)`
      として、method を必須引数にするのが正しい。

  (c) **相関品質(ZNCC 係数)のマップが無い**。DIC では「測れなかった点」を
      品質で切るのが常識。いまの optical flow は品質を返さないので、
      デコリレーションした点と正しく 0 の点を区別できない。

  (d) **スペックル合成器が無い**。この PoC の `Speckle` は再利用価値がある
      (真値つきの変形画像はひずみ計測の検証に必須)。`surface_synth_psd` が
      粗さ族にとってそうだったのと同じ位置づけ。

  (e) 既存 op の穴: `optical_flow_lk` / `optical_flow_hs` に**窓ごとの残差を
      返す口が無い**。収束したのか発散したのかが呼び手から見えない。

  次にやるべきこと: (a)(b)(c)(d) をまとめて `dic` 族として出す。ただし
  **出す前にこの PoC と同じ土俵で ZNCC が LK に勝つことを実測してから**
  (`mosaic` を測って出さなかったのと同じ手順)。
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
    print("経過 %.1f 秒" % (time.time() - t0))


if __name__ == "__main__":
    main()
