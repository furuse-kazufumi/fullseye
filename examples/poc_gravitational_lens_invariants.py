#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 重力レンズの像を、産業用の測定 op で採点する。

★主張は「重力レンズの絵が作れます」ではない。**重力レンズには、絵から直接測れる
厳密な不変量がある** —— しかもそれを測る道具は、この箱にある平凡な 2-D の op
(連結成分・面積・重心)でよい。

点質量レンズをアインシュタイン半径 1 の単位で書くと、光源位置 ``u`` に対し::

    像の位置   θ± = (u ± sqrt(u² + 4)) / 2
    倍率       μ± = (u² + 2) / (2 u sqrt(u² + 4)) ± 1/2

から、**光源がどこにあっても**成り立つ 2 つの等式が出る::

    θ₊ · θ₋ = −1        (積が光源位置に依らない)
    μ₊ − μ₋ =  1        (差が光源位置に依らない —— 整数)

さらにリウヴィルの定理から、**レンズは面輝度を変えない**。変わるのは面積だけで、
面積比がそのまま倍率になる。だから「絵の明るさは厳密に変わらず、絵の広さだけが
変わる」という、同じ 1 枚から出る対の量が取れる。

★★この PoC の芯は 6 つ:

  1. **整数の不変量が、絵から出る。** 2 つの像を連結成分で分けて面積を測ると
     ``μ₊ − |μ₋|`` の **1** からのずれが、格子 801 → 1601 → 3201 で
     0.0660 → 0.0216 → 0.0126 と縮む。
     モデルの数字ではなく、**描いた絵を測って**出している。
  2. **面輝度は厳密に変わらない。** 像の内部の値は u を振っても
     ``1.000000000000000`` のままで、面積だけが 2,325 → 480 画素と変わる。
  3. **環の太さは光源の半径に等しい。** アインシュタイン環の上では動径方向の
     倍率が厳密に 1/2 なので、直径 2ρ の光源は太さ ρ の環になる(4 通りで一致)。
  4. **特異点はちょうど 1 画素の偽の像を作る。** 光源が真後ろ(u = 0)のとき、像は
     アインシュタイン環**1 本**のはずなのに、連結成分は **2 個**になる。増えた
     1 個はレンズ中心の 1 画素で、そこは偏向角が発散する点 —— 数値の上でだけ
     光線が光源に当たる。**個数を数える門は、ここで嘘をつく。**

  5. **絵から測る方法が負ける場所も、数で出る。そして予想は外れた。** はじめ
     「光源が遠いと暗い像が小さくなるから、そこが苦しい」と読んだが**外れ**で、
     実測ではどの解像度でも **焦線に近い u = 0.3 が最悪**(u = 1.5 の暗い像は
     n = 3201 で 209 画素ある)。苦しいのは像が小さいほうではなく、**像が
     引き伸ばされて細い弧になる**ほうだった。**「測れる範囲」を主張と一緒に出す。**

  6. **被覆率の幅は「像面の画素」で測る。** 縁のアンチエイリアスを光源面の距離で
     作ると、倍率の大きいところで縁が細く見えて面積が系統的にずれる。距離場を
     像面での変化率 ``|∇d|`` で割るだけで、u = 0.3 のずれが **0.0214 → 0.0126** に
     下がった。**写像の先で測った距離を、そのまま手前の画素に使ってはいけない。**

**新しい op は 1 つも足していない。** 像は逆写像(像面の画素を光源面へ引き戻す)で
作り、測る側は ``blob_label`` / ``blob_features`` と面積・重心だけを使う。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L = fs.ledger
_PASS = []

#: 像面の半幅(アインシュタイン半径の単位)
_HALF = 3.0
#: 既定の格子
_N = 1201
#: 既定の光源半径
_SRC = 0.06
#: レンズ中心のまわりで像を数えない半径(特異点よけ)
_GUARD = 0.02
_PAPER = (0.985, 0.980, 0.968)
#: 色。★赤と緑は対にしない
_STOPS = [(0.0, _PAPER), (0.35, (0.72, 0.78, 0.80)), (0.7, (0.19, 0.44, 0.62)),
          (1.0, (0.06, 0.11, 0.28))]
_MARK = (0.90, 0.62, 0.18)


def check(ok, label, detail=""):
    _PASS.append(bool(ok))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label,
                            ("---- " + detail) if detail else ""))


def _ramp(t, stops):
    pos = np.array([s[0] for s in stops], np.float64)
    col = np.array([s[1] for s in stops], np.float64)
    out = np.empty(t.shape + (3,), np.float64)
    for c in range(3):
        out[..., c] = np.interp(t, pos, col[:, c])
    return out


# --------------------------------------------------------------------------- #
# 閉形式 —— 絵を見ずに決まる値                                                   #
# --------------------------------------------------------------------------- #
def images_point(u):
    """点質量レンズの 2 つの像の位置(θ_E = 1 の単位)。"""
    r = np.sqrt(u * u + 4.0)
    return 0.5 * (u + r), 0.5 * (u - r)


def mags_point(u):
    """同じく 2 つの像の倍率(符号つき。μ₋ は負 = 像が裏返る)。"""
    r = np.sqrt(u * u + 4.0)
    base = (u * u + 2.0) / (2.0 * u * r)
    return base + 0.5, base - 0.5


# --------------------------------------------------------------------------- #
# 絵 —— 像面の画素を光源面へ引き戻す(逆写像)                                    #
# --------------------------------------------------------------------------- #
def render(u, n=_N, half=_HALF, src_r=_SRC, kind="point", guard=0.0):
    """円盤の光源をレンズ越しに見た像。**縁は被覆率で描く**(0/1 だと量子化が残る)。"""
    g = np.linspace(-half, half, n)
    X, Y = np.meshgrid(g, g)
    r = np.hypot(X, Y)
    r = np.where(r < 1e-12, 1e-12, r)
    if kind == "point":                       # 偏向角 α = θ_E² / θ
        bx, by = X - X / (r * r), Y - Y / (r * r)
    else:                                     # 特異等温球: α = θ_E(一定)
        bx, by = X - X / r, Y - Y / r
    px = 2.0 * half / (n - 1)
    d = np.hypot(bx - u, by)
    # ★縁の幅は**像面の画素**で測る。光源面の距離をそのまま使うと、倍率の
    #   大きいところで縁が細く見え、面積が系統的にずれる(実測 2.1% → 0.2%)。
    #   d は光源面の量なので、像面での変化率 |∇d| で割って像面の単位に直す。
    gy, gx = np.gradient(d, px)
    grad = np.hypot(gx, gy)
    grad = np.where(grad < 1e-12, 1e-12, grad)
    cov = np.clip(0.5 + (src_r - d) / (px * grad), 0.0, 1.0)
    if guard > 0.0:
        cov = np.where(r < guard, 0.0, cov)
    return cov, px, X, Y


def render_target(u, n=701, half=2.25, src_r=0.22, kind="point", spokes=12,
                  rings=4):
    """光源を**校正ターゲット**(同心円 + 放射スポーク)にして歪みを目で読めるようにする。

    ★この箱の語彙そのもの —— 既知の構造を持つ的を置いて、歪んだ像から
    元の構造を読み返す。測るのは面積だが、**見えるのは剪断**。
    """
    g = np.linspace(-half, half, n)
    X, Y = np.meshgrid(g, g)
    r = np.hypot(X, Y)
    r = np.where(r < 1e-12, 1e-12, r)
    if kind == "point":
        bx, by = X - X / (r * r), Y - Y / (r * r)
    else:
        bx, by = X - X / r, Y - Y / r
    sx, sy = bx - u, by
    sr = np.hypot(sx, sy)
    th = np.arctan2(sy, sx)
    inside = sr <= src_r
    ring = 0.5 + 0.5 * np.cos(2.0 * np.pi * rings * sr / src_r)
    spoke = 0.5 + 0.5 * np.cos(spokes * th)
    pat = np.clip(0.30 + 0.45 * ring + 0.35 * spoke, 0.0, 1.0)
    return np.where(inside, pat, 0.0), X, Y


def ring_overlay(img, X, Y, radius=1.0, colour=_MARK, width=0.006):
    """アインシュタイン半径の円を薄く重ねる(測定の幾何を絵の上に置く)。"""
    d = np.abs(np.hypot(X, Y) - radius)
    a = np.clip(1.0 - d / width, 0.0, 1.0)[..., None] * 0.85
    return img * (1 - a) + np.asarray(colour, np.float64).reshape(1, 1, 3) * a


def blobs(cov, X, Y):
    """像を連結成分に分け、(光量, 重心 x, 重心 y)を大きい順に返す。"""
    lab = np.asarray(L.blob_label((cov > 0.5).astype(np.float64)))
    out = []
    for k in range(1, int(lab.max()) + 1):
        w = cov * (lab == k)
        s = float(w.sum())
        if s <= 0.0:
            continue
        out.append((s, float((w * X).sum() / s), float((w * Y).sum() / s)))
    out.sort(key=lambda t: -t[0])
    return out


def src_area_px(px, src_r=_SRC):
    return np.pi * src_r * src_r / (px * px)


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.time()
    print("PoC: 重力レンズの像を、産業用の測定 op で採点する")
    print("=" * 72)

    # ------------------------------------------------------------------ #
    print("\n1. 光源がどこにあっても成り立つ 2 つの等式(閉形式)")
    us = (0.05, 0.1, 0.3, 0.7, 1.0, 1.5, 2.0, 3.5, 7.0)
    prod, diff, tot = [], [], []
    for u in us:
        tp, tm = images_point(u)
        mp, mm = mags_point(u)
        prod.append(tp * tm)
        diff.append(mp - mm)
        tot.append(mp + abs(mm))
    e_prod = float(np.abs(np.asarray(prod) + 1.0).max())
    e_diff = float(np.abs(np.asarray(diff) - 1.0).max())
    check(e_prod < 1e-14, "θ₊·θ₋ = −1 が %d 通りの光源位置すべてで成立" % len(us),
          "最大のずれ %.1e" % e_prod)
    check(e_diff < 1e-14, "★μ₊ − μ₋ = 1(整数)が %d 通りすべてで成立" % len(us),
          "最大のずれ %.1e —— 差が光源位置に依らない" % e_diff)
    check(all(tot[i] > tot[i + 1] for i in range(len(tot) - 1)),
          "総倍率は光源が近いほど大きい(単調)",
          "u=%.2f で %.3f 倍 → u=%.1f で %.5f 倍" % (us[0], tot[0], us[-1], tot[-1]))

    # ------------------------------------------------------------------ #
    print("\n2. その整数を、絵から測る(連結成分で像を分ける)")
    probe_us = (0.3, 0.7, 1.5)
    conv = []                      # 近い 2 点(u = 0.3, 0.7)の最大のずれ
    per_u = {u: [] for u in probe_us}
    faint_px = {}
    for n in (801, 1601, 3201):
        worst_near = 0.0
        for u in probe_us:
            cov, px, X, Y = render(u, n=n)
            bs = blobs(cov, X, Y)
            a = src_area_px(px)
            got = (bs[0][0] - bs[1][0]) / a
            per_u[u].append(abs(got - 1.0))
            if u == 1.5:
                faint_px[n] = bs[1][0]
            if u in (0.3, 0.7):
                worst_near = max(worst_near, abs(got - 1.0))
        conv.append(worst_near)
        print("   n=%4d  ずれ  u=0.3 %.4f / u=0.7 %.4f / u=1.5 %.4f"
              % (n, per_u[0.3][-1], per_u[0.7][-1], per_u[1.5][-1]))
    check(conv[-1] < conv[0], "解像度を上げると絵から測った差が 1 に寄る",
          "u ≤ 0.7 で %s" % " -> ".join("%.4f" % c for c in conv))
    check(conv[-1] < 0.02, "いちばん細かい格子で 2 %% 未満(u ≤ 0.7)",
          "n=3201 で %.4f" % conv[-1])
    # ★はじめ「暗い像が小さくなる u = 1.5 がいちばん苦しい」と読んで**外した**。
    #   実測ではどの解像度でも **u = 0.3(焦線に近い側)が最悪**で、u = 1.5 の
    #   暗い像は n=3201 でも 209 画素ある。苦しいのは「像が小さい」ほうではなく
    #   「像が引き伸ばされて細い弧になる」ほうだった。
    worst_u = [max(probe_us, key=lambda u: per_u[u][i]) for i in range(3)]
    check(all(w == 0.3 for w in worst_u),
          "★いちばん残るのは焦線に近い側(u = 0.3)—— 暗い像が小さい側ではない",
          "3 つの解像度とも最悪は u=%.1f。u=1.5 の暗い像は n=3201 で %.0f 画素ある"
          % (worst_u[0], faint_px[3201]))

    cov, px, X, Y = render(0.3, n=3201)
    bs = blobs(cov, X, Y)
    a = src_area_px(px)
    mp, mm = mags_point(0.3)
    m_plus, m_minus = bs[0][0] / a, bs[1][0] / a
    check(abs(m_plus - mp) / mp < 0.01, "明るい像の倍率が閉形式と 1 %% 以内",
          "実測 %.5f / 閉形式 %.5f" % (m_plus, mp))
    check(abs(m_minus - abs(mm)) / abs(mm) < 0.02, "暗い像も 2 %% 以内",
          "実測 %.5f / 閉形式 %.5f" % (m_minus, abs(mm)))

    # ------------------------------------------------------------------ #
    print("\n3. 面輝度は厳密に変わらない —— 変わるのは面積だけ(リウヴィル)")
    bright, areas = [], []
    for u in (0.2, 0.7, 2.0):
        cov, px, X, Y = render(u)
        inner = cov[cov > 0.999]
        bright.append((float(inner.min()), float(inner.max())))
        areas.append(float(cov.sum()))
        print("   u=%.1f  像の内部 %.15f〜%.15f  面積 %.1f 画素"
              % (u, inner.min(), inner.max(), cov.sum()))
    check(all(lo == 1.0 and hi == 1.0 for lo, hi in bright),
          "★像の内部の値が厳密に 1.0 のまま(3 通りとも)",
          "面輝度は保存される")
    check(max(areas) / min(areas) > 4.0, "同じ 3 通りで面積は 4 倍以上変わる",
          "%.0f → %.0f 画素" % (max(areas), min(areas)))

    # ------------------------------------------------------------------ #
    print("\n4. 像はちょうど 2 個 —— ただし光源が真後ろのときは環 1 本が 2 個になる")
    counts = []
    for u in probe_us:
        cov, px, X, Y = render(u)
        counts.append(len(blobs(cov, X, Y)))
    check(all(c == 2 for c in counts), "u > 0 では像がちょうど 2 個",
          "%s" % counts)

    cov0, px0, X0, Y0 = render(0.0, n=1601, src_r=0.05)
    n_raw = len(blobs(cov0, X0, Y0))
    cov0g, _p, _x, _y = render(0.0, n=1601, src_r=0.05, guard=_GUARD)
    n_guard = len(blobs(cov0g, X0, Y0))
    small = sorted([b[0] for b in blobs(cov0, X0, Y0)])[0]
    check(n_raw == 2 and n_guard == 1,
          "★u = 0 では特異点が偽の像を 1 個足す(環 + 中心の点)",
          "素のまま %d 個 / 中心を除くと %d 個(偽の像は %.1f 画素)"
          % (n_raw, n_guard, small))

    # ------------------------------------------------------------------ #
    print("\n5. アインシュタイン環 —— 半径は 1、太さは光源の半径")
    rad_mean = None
    widths = []
    for sr in (0.03, 0.05, 0.08, 0.12):
        cov, px, X, Y = render(0.0, n=1601, src_r=sr, guard=_GUARD)
        m = cov > 0.5
        rad = np.hypot(X[m], Y[m])
        w = float(rad.max() - rad.min())
        widths.append((sr, w, float(rad.mean())))
        if sr == 0.05:
            rad_mean = float(rad.mean())
        print("   光源半径 %.2f  環 %.6f〜%.6f  太さ %.5f(真値 %.5f)"
              % (sr, rad.min(), rad.max(), w, sr))
    check(abs(rad_mean - 1.0) < 0.01, "環の半径がアインシュタイン半径 1 と一致",
          "実測 %.6f" % rad_mean)
    werr = max(abs(w - sr) for sr, w, _m in widths)
    check(werr < 1e-3, "★環の太さ = 光源の半径(4 通りとも)",
          "最大のずれ %.1e —— 環の上では動径方向の倍率が厳密に 1/2" % werr)

    # ------------------------------------------------------------------ #
    print("\n6. 特異等温球 —— 像の間隔は光源位置に依らない")
    seps = []
    for u in (0.2, 0.4, 0.6, 0.8):
        cov, px, X, Y = render(u, n=1601, src_r=0.04, kind="sis")
        bs = blobs(cov, X, Y)
        if len(bs) < 2:
            seps.append((u, float("nan"), len(bs)))
            continue
        d = float(np.hypot(bs[0][1] - bs[1][1], bs[0][2] - bs[1][2]))
        seps.append((u, d, len(bs)))
        print("   u=%.1f  間隔 %.6f(真値 2)  差 %+.2e  像 %d 個" % (u, d, d - 2.0, len(bs)))
    check(all(c == 2 for _u, _d, c in seps), "SIS でも像はちょうど 2 個",
          "%s" % [c for _u, _d, c in seps])
    serr = max(abs(d - 2.0) for _u, d, _c in seps)
    check(serr < 0.02, "間隔が 2θ_E(光源位置に依らない)",
          "最大のずれ %.1e —— 4 通りの光源位置で" % serr)

    # ------------------------------------------------------------------ #
    print("\n7. 光源が横切る —— 動く図と、そのとき測った倍率")
    frames, curve = [], []
    us_anim = np.linspace(-1.6, 1.6, 28)
    for uu in us_anim:
        u = abs(float(uu))
        cov, px, X, Y = render(max(u, 1e-3), n=421, half=2.6, src_r=0.09,
                               guard=_GUARD)
        curve.append(float(cov.sum()) / src_area_px(px, 0.09))
        if figs.enabled():
            pat, TX, TY = render_target(max(u, 1e-4), n=381, half=2.25)
            frames.append(ring_overlay(_ramp(pat, _STOPS), TX, TY))
        else:
            frames.append(_ramp(cov, _STOPS))
    content = int(sum(1 for f in frames if float(np.ptp(f)) > 1e-9))
    check(content == len(frames), "★中身のあるコマが %d/%d(空でない)"
          % (content, len(frames)), "「動いた」を別に数える")
    peak = int(np.argmax(curve))
    check(abs(peak - len(curve) // 2) <= 1, "倍率の山が光源の最接近と一致",
          "%d コマ目で最大 %.2f 倍(全 %d コマ)" % (peak, max(curve), len(curve)))
    truth_curve = [mags_point(max(abs(float(uu)), 1e-3)) for uu in us_anim]
    truth_tot = np.asarray([mp + abs(mm) for mp, mm in truth_curve])
    relall = np.abs((np.asarray(curve) - truth_tot) / truth_tot)
    far = np.abs(us_anim) >= 0.3
    rel = float(relall[far].max())
    rel_near = float(relall[~far].max())
    check(rel < 0.06, "|u| ≥ 0.3 では測った倍率が閉形式に沿う",
          "最大の相対差 %.3f(格子 421 で描いている)" % rel)
    check(rel_near > 2.0 * rel,
          "★焦線の近く(|u| < 0.3)では絵から測る方法が負ける",
          "そこだけ相対差 %.3f —— 弧が画素より細くなるため。"
          "**測れる範囲を主張と一緒に出す**" % rel_near)

    # ------------------------------------------------------------------ #
    if figs.enabled():
        print("\n8. 図を書く")
        panels, caps = [], []
        for u in (0.0, 0.25, 0.6, 1.2):
            pat, X, Y = render_target(max(u, 1e-4))
            panels.append(ring_overlay(_ramp(pat, _STOPS), X, Y))
            caps.append("u = %.2f" % u)
        figs.save_grid("images_vs_u", panels, caps, ncols=2,
                       title="校正ターゲットを置いて、歪みを目で読む",
                       caption="光源は同心円 %d 本 + 放射スポーク %d 本の的。"
                               "橙の円がアインシュタイン半径。左上は完全に真後ろ"
                               "(環)、右下まで離すと 2 つの像に分かれる。"
                               "**環になるのは真後ろのときだけ**で、u > 0 では"
                               "つねにちょうど 2 個。位置の積 θ₊·θ₋ = −1 と"
                               "倍率の差 μ₊ − μ₋ = 1 は**光源位置に依らない**。"
                               % (4, 12))

        shear = []
        for u in (0.15, 0.4, 0.8, 1.4):
            cov, px, X, Y = render(u, n=701, half=2.6, src_r=0.09, guard=_GUARD)
            shear.append(_ramp(cov, _STOPS))
        figs.save_grid("disc_images_vs_u", shear,
                       ["u = 0.15", "u = 0.40", "u = 0.80", "u = 1.40"], ncols=2,
                       title="測るときは的を無地の円盤に戻す",
                       caption="面積を測るのに模様は要らない。明るいほうの像は外側"
                               "(θ₊ > 1)、暗いほうは内側(|θ₋| < 1)に出て、"
                               "離れるほど内側の像は小さく暗くなる。")

        figs.save_plot("closed_form_invariants",
                       [("θ₊·θ₋", np.asarray(us), np.asarray(prod)),
                        ("μ₊ − μ₋", np.asarray(us), np.asarray(diff))],
                       xlabel="光源位置 u(アインシュタイン半径の単位)",
                       ylabel="不変量", title="光源をどこへ動かしても平らなまま",
                       caption="%d 通りの u で θ₊·θ₋ は −1 から **%.1e**、"
                               "μ₊ − μ₋ は 1 から **%.1e** しか動かない。"
                               % (len(us), e_prod, e_diff))

        figs.save_plot("measured_integer",
                       [("絵から測った μ₊ − |μ₋| のずれ",
                         np.arange(3, dtype=float), np.asarray(conv))],
                       xlabel="格子(801 / 1601 / 3201)",
                       ylabel="1 からのずれ",
                       title="★整数の不変量が、絵から出てくる",
                       caption="2 つの像を `blob_label` で分けて面積を測っただけ。"
                               "%s と 1 に寄る —— モデルの数字ではなく、"
                               "**描いた絵を測って**出している。"
                               % " -> ".join("%.4f" % c for c in conv))

        cov, px, X, Y = render(0.2, n=701, half=2.6, src_r=0.09, guard=_GUARD)
        cov2, px2, _X, _Y = render(2.0, n=701, half=2.6, src_r=0.09, guard=_GUARD)
        figs.save_grid("brightness_and_area",
                       [_ramp(cov, _STOPS), _ramp(cov2, _STOPS)],
                       ["u = 0.2(面積 %.0f 画素)" % cov.sum(),
                        "u = 2.0(面積 %.0f 画素)" % cov2.sum()], ncols=2,
                       title="明るさは変わらない。変わるのは広さだけ",
                       caption="像の内部の値はどちらも厳密に "
                               "**1.000000000000000**。レンズは面輝度を変えない"
                               "(リウヴィル)ので、増えるのは面積のほうで、"
                               "その比がそのまま倍率になる。")

        ringimg, _p, RX, RY = render(0.0, n=901, half=2.0, src_r=0.09,
                                     guard=_GUARD)
        raw0, _p2, _x2, _y2 = render(0.0, n=901, half=2.0, src_r=0.09)
        figs.save_grid("einstein_ring",
                       [_ramp(ringimg, _STOPS), _ramp(raw0, _STOPS),
                        _ramp(np.abs(raw0 - ringimg), _STOPS)],
                       ["中心を除いたもの", "素のまま", "差 = 偽の像"], ncols=3,
                       title="★光源が真後ろのときだけ、特異点が像を 1 個足す",
                       caption="光源が真後ろのとき、像はアインシュタイン環"
                               "**1 本**のはず。それでも素のまま数えると "
                               "**%d 個**(環 + 中心の %.1f 画素)になる —— "
                               "レンズ中心は偏向角が発散する"
                               "点で、そこを通る光線は数値の上でだけ光源に"
                               "当たってしまう。**個数を数える門は、ここで嘘をつく。**"
                               % (n_raw, small))

        figs.save_plot("ring_width",
                       [("環の太さ", np.asarray([w[0] for w in widths]),
                         np.asarray([w[1] for w in widths])),
                        ("光源の半径", np.asarray([w[0] for w in widths]),
                         np.asarray([w[0] for w in widths]))],
                       xlabel="光源の半径", ylabel="環の太さ",
                       title="環の太さは光源の半径にちょうど等しい",
                       caption="環の上では動径方向の倍率が**厳密に 1/2** なので、"
                               "直径 2ρ の光源は太さ ρ の環になる。"
                               "4 通りで最大のずれ **%.1e**。" % werr)

        sis_panels, sis_caps = [], []
        for u in (0.2, 0.5, 0.8):
            cov, px, X, Y = render(u, n=701, half=2.6, src_r=0.07, kind="sis")
            sis_panels.append(_ramp(cov, _STOPS))
            sis_caps.append("u = %.1f" % u)
        figs.save_grid("sis_images", sis_panels, sis_caps, ncols=3,
                       title="特異等温球 —— 像は動くが、間隔は動かない",
                       caption="偏向角が一定のレンズでは、2 つの像の間隔が"
                               "**光源位置に依らず 2θ_E**。4 通りで最大のずれ "
                               "%.1e。" % serr)

        figs.save_plot("sis_separation",
                       [("測った間隔", np.asarray([s[0] for s in seps]),
                         np.asarray([s[1] for s in seps])),
                        ("真値 2θ_E", np.asarray([s[0] for s in seps]),
                         np.full(len(seps), 2.0))],
                       xlabel="光源位置 u", ylabel="像の間隔",
                       title="光源を動かしても間隔は 2 のまま",
                       caption="重心は `blob_label` で分けた成分ごとに、"
                               "被覆率で重みを付けて出している。")

        figs.save_gif("source_crossing", frames, fps=10,
                      caption="光源がレンズの裏を横切る(図は校正ターゲット)。"
                              "最接近で 2 つの像が伸びて環に近づく。"
                              "**倍率の数字は同じ光源位置を無地の円盤で描き直して"
                              "測ったもの**で、最大 %.2f 倍。" % max(curve))

        figs.save_plot("crossing_magnification",
                       [("絵から測った総倍率", us_anim, np.asarray(curve)),
                        ("閉形式", us_anim, np.asarray(truth_tot))],
                       xlabel="光源位置 u(横切る)", ylabel="総倍率",
                       title="横切るあいだ、測った倍率は閉形式に沿う",
                       caption="動く図と同じ %d コマを、そのまま面積で測ったもの。"
                               "**|u| ≥ 0.3 では相対差 %.3f** と閉形式に沿うのに、"
                               "焦線に近い |u| < 0.3 では **%.3f** まで開く —— "
                               "弧が画素より細くなって面積が取れなくなる。"
                               "**測れる範囲を主張と一緒に出す。**"
                               % (len(frames), rel, rel_near))

        tbl = [
            ["点質量レンズ", "θ₊·θ₋", "−1(u に依らない)", "%.1e のずれ" % e_prod,
             "%d 通りの光源位置" % len(us)],
            ["点質量レンズ", "μ₊ − μ₋", "1(整数)", "%.1e のずれ" % e_diff,
             "★差が光源位置に依らない"],
            ["絵から測った倍率", "μ₊ − |μ₋|", "1", "%.4f" % (1.0 + conv[-1]),
             "801→3201 で %s" % " -> ".join("%.3f" % c for c in conv)],
            ["像の内部", "面輝度", "変わらない", "1.000000000000000",
             "u = 0.2 / 0.7 / 2.0 の 3 通りとも"],
            ["像", "面積", "μ 倍に変わる", "%.0f → %.0f 画素" % (max(areas), min(areas)),
             "同じ 3 通り。明るさは動かない"],
            ["像の個数", "連結成分", "2", "%s" % counts, "u > 0 では"],
            ["像の個数(u = 0)", "同上", "2(環 1 本)", "%d" % n_raw,
             "★特異点が %.1f 画素の偽の像を足す" % small],
            ["アインシュタイン環", "半径", "1", "%.6f" % rad_mean, "θ_E の単位"],
            ["アインシュタイン環", "太さ", "光源の半径 ρ", "%.1e のずれ" % werr,
             "動径倍率が厳密に 1/2 だから"],
            ["特異等温球", "像の間隔", "2θ_E(u に依らない)", "%.1e のずれ" % serr,
             "4 通りの光源位置"],
        ]
        figs.save_table("numbers", ["対象", "量", "真値", "実測", "備考"], tbl,
                        title="絵を見ずに採点した結果",
                        caption="★この表に「絵を見て判断した」行はありません。"
                                "真値は**レンズ方程式から導かれる等式**で、実測は"
                                "**`blob_label` と面積・重心**が返したものです。"
                                "**新しい op は 1 つも足していません。**")
        errs = figs.errors()
        assert not errs, errs

    ok = sum(_PASS)
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(_PASS), ok, time.time() - t0))
    if ok != len(_PASS):
        for i, v in enumerate(_PASS):
            if not v:
                print("  NG が残っている(%d 番目)" % (i + 1))
        return 1
    # ★門 tests/test_poc_scripts_run.py は exit 0 だけでなく PASS の印字も見る。
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
