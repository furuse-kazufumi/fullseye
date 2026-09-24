#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 遠ざかると消える距離と、形が変わるときの面積。

★主張は「高周波と低周波を混ぜた絵が作れます」でも「形が滑らかに変わります」でも
ない。**どちらにも、絵から直接測れる厳密な真値がある** —— そして
**よく使われている作り方のほうが、その真値を外す。**

1 本目は **周波数**。画像を「低い方」と「高い方」に分けるとき、
理想的な周波数マスクで分ければ 2 枚は **厳密に直交**する。だから

    E(低) + E(高) = E(元)          ← 厳密に成り立つ(パーセバル + 直交)

ところが**教科書どおりの作り方(ガウシアンでぼかし、残りを高域にする)では
直交しない**。足せば元に戻るのに、エネルギーの帳尻だけが合わない。
**可逆であることと、直交であることは別**。

2 本目は **遠ざかること**。k 画素を束ねる(= 遠くから見る)操作の伝達関数は

    H(f, k) = sin(π f k) / (k sin(π f))

で、**f·k が整数のときちょうど 0**。つまり「周期 p 画素の模様は、p 画素に
束ねるとちょうど消える」—— **消える距離が整数で決まる**。しかも
**1 画素ずれただけで模様は戻る。**

3 本目は **形**。多角形の頂点を線形に補間(モーフ)すると、囲む面積は
``t`` の**厳密な 2 次式**になる(グリーンの定理の積が t について 2 次だから)。
だから **3 コマ測れば全コマを予言できる**。

★★この PoC の芯は 5 つ:

  1. **分解の直交性は、よくある作り方のほうが壊れている。** 理想マスクなら
     エネルギーの帳尻が相対 0.0 で合うのに、ガウシアン分解ではノブをどう
     振っても 0.53 % 〜 3.10 % ずれる。**どちらも足せば元に戻る。**
     しかも★**単調でない** —— ぼかしを強くしても弱くしても直らない。
  2. **消える距離は整数で、束ねた絵は 1 画素ずつ式で書ける。** 周期 p 画素の
     模様は k = p でちょうど消え(実測 1e-14)、k = p ± 1 では戻る。しかも
     束ねたあとの絵は振幅も位相も閉形式と一致する(全画素で 1e-14)——
     **束ねた画素の中心が (k − 1)/2 ずれること**まで式に入っている。
     ところが同じ絵から「最大と最小」で振幅を測ると小さく出る。
     **画素が山の頂上を踏まないから** —— 式は踏まなくても正しい。
  3. **形の面積は t の 2 次式 —— それが絵からも出る。** 閉形式では 1e-15、
     絵から測った面積でも格子と細分を上げると 1.10 % → 0.053 % に寄る。
     しかも「1 画素を 4×4 に分ける」のは「格子を 4 倍細かくする」と**同じ数字**。
  4. **絵から測ると符号が消える。そこで予言はちょうど 25 % 外れる。**
     向きが反転するモーフでは符号つき面積が t の 1 次式になるが、絵から測った
     面積は必ず正なので折り返す。3 コマから当てた放物線は最大値の **ちょうど
     1/4** 外れる —— **外れ方まで閉形式で出る。**
  5. **外した予言を 1 つ残してある。** 「ハイブリッド画像が切り替わる束ね幅は
     遮断周波数 fc から 1/(2 fc) で予言できる」は**外れ**。fc を 3 倍振っても
     実測の切り替わりはほとんど動かない。決めているのは遮断周波数ではなく
     **高域側の絵が実際に持っている周期**だった。

**新しい op は 1 つも足していない。**
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

_PAPER = (0.985, 0.980, 0.968)
#: 色。★赤と緑は対にしない
_STOPS = [(0.0, (0.06, 0.11, 0.28)), (0.4, (0.19, 0.44, 0.62)),
          (0.75, (0.72, 0.78, 0.80)), (1.0, _PAPER)]
_MARK = (0.90, 0.62, 0.18)


def check(ok, label, detail=""):
    _PASS.append(bool(ok))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label,
                            ("---- " + detail) if detail else ""))


def _ramp(t, stops=_STOPS):
    pos = np.array([s[0] for s in stops], np.float64)
    col = np.array([s[1] for s in stops], np.float64)
    out = np.empty(t.shape + (3,), np.float64)
    for c in range(3):
        out[..., c] = np.interp(t, pos, col[:, c])
    return out


def _norm(a):
    a = np.asarray(a, np.float64)
    lo, hi = float(a.min()), float(a.max())
    return np.zeros_like(a) if hi - lo < 1e-15 else (a - lo) / (hi - lo)


# --------------------------------------------------------------------------- #
# 周波数で分ける                                                                #
# --------------------------------------------------------------------------- #
def radial_freq(n):
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    return np.hypot(fx, fy)


def split_ideal(img, cut):
    """理想的な周波数マスクで低域と高域に分ける(★2 枚は厳密に直交する)。"""
    F = np.fft.fft2(img)
    m = radial_freq(img.shape[0]) <= cut
    lo = np.real(np.fft.ifft2(F * m))
    hi = np.real(np.fft.ifft2(F * (~m)))
    return lo, hi


def split_gauss(img, a):
    """教科書どおりの作り方。★足せば元に戻るが、直交はしない。

    ``a`` は ``gauss_filter`` のノブで、シグマは ``0.3 + 2.7 a``。
    """
    lo = np.asarray(fs.op.gauss_filter(img, a=float(a)), np.float64)
    return lo, img - lo


def energy_gap(lo, hi, img):
    """E(低) + E(高) − E(元) の相対値。直交なら 0。"""
    e = float(np.sum(img * img))
    return (float(np.sum(lo * lo)) + float(np.sum(hi * hi)) - e) / e


def bin_pixels(img, k):
    """k 画素を束ねる = 遠ざかる。"""
    n = img.shape[0] // k * k
    s = n // k
    return img[:n, :n].reshape(s, k, s, k).mean(axis=(1, 3))


def box_transfer_signed(f, k):
    """★箱平均の伝達関数(閉形式)。f·k が整数のとき厳密に 0。

    符号つき —— 束ねると模様が反転することがある。
    """
    d = np.sin(np.pi * f)
    if abs(d) < 1e-15:
        return 1.0
    return np.sin(np.pi * f * k) / (k * d)


def box_transfer(f, k):
    return abs(box_transfer_signed(f, k))


def binned_closed_form(f, k, count):
    """★束ねたあとの列を、1 画素ずつ閉形式で書く。

    振幅が ``H(f, k)`` になるだけでなく、**束ねた画素の中心が元の絵の
    ``(k − 1) / 2`` だけずれる**ことまで式に入っている。
    """
    i = np.arange(count)
    return box_transfer_signed(f, k) * np.sin(
        2.0 * np.pi * f * (k * i + (k - 1) / 2.0))


# --------------------------------------------------------------------------- #
# 形を変える                                                                    #
# --------------------------------------------------------------------------- #
def ngon(k, r=1.0, phase=0.0, cx=0.0, cy=0.0):
    a = 2.0 * np.pi * np.arange(k) / k + phase
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], 1)


def signed_area(V):
    """★符号つき面積(靴ひも公式)。向きが反転すると負になる。"""
    x, y = V[:, 0], V[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def morph(A, B, t):
    return (1.0 - t) * A + t * B


def poly_coverage(V, n, half=1.6, sub=1):
    """多角形を n×n に塗る(sub>1 で 1 画素を sub² に分けて被覆率にする)。"""
    m = n * sub
    g = (np.arange(m) + 0.5) / m * (2.0 * half) - half
    X, Y = np.meshgrid(g, g)
    inside = np.zeros((m, m), bool)
    k = len(V)
    for i in range(k):
        x1, y1 = V[i]
        x2, y2 = V[(i + 1) % k]
        if y1 == y2:
            continue
        cond = ((y1 > Y) != (y2 > Y)) & (X < (x2 - x1) * (Y - y1) / (y2 - y1) + x1)
        inside ^= cond
    if sub == 1:
        return inside.astype(np.float64)
    return inside.reshape(n, sub, n, sub).mean(axis=(1, 3))


def area_from_picture(V, n, half=1.6, sub=1):
    """★絵から測った面積。必ず正 —— ここが 4 番目の芯になる。"""
    cov = poly_coverage(V, n, half=half, sub=sub)
    px = (2.0 * half / n) ** 2
    return float(cov.sum()) * px


def quad_from_three(ts, ys):
    """3 点(t = 0, 0.5, 1)から 2 次式を決める。"""
    return np.polyfit(np.asarray(ts, np.float64)[[0, len(ts) // 2, -1]],
                      np.asarray(ys, np.float64)[[0, len(ys) // 2, -1]], 2)


def catmull_rom(P, m=40):
    """★Catmull-Rom スプラインは制御点を厳密に通る。"""
    P = np.asarray(P, np.float64)
    Q = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = Q[i], Q[i + 1], Q[i + 2], Q[i + 3]
        t = np.linspace(0.0, 1.0, m, endpoint=False)[:, None]
        out.append(0.5 * ((2.0 * p1) + (-p0 + p2) * t
                          + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t ** 2
                          + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t ** 3))
    out.append(P[-1][None, :])
    return np.vstack(out)


def bezier(P, m=401):
    """de Casteljau。★曲線は制御点の凸包から出ない。"""
    P = np.asarray(P, np.float64)
    t = np.linspace(0.0, 1.0, m)[:, None]
    Q = np.repeat(P[None, :, :], m, axis=0)
    for _ in range(len(P) - 1):
        Q = (1 - t)[:, :, None] * Q[:, :-1, :] + t[:, :, None] * Q[:, 1:, :]
    return Q[:, 0, :]


def convex_hull(P):
    """単調連鎖法。外部依存を足さない。"""
    pts = sorted(map(tuple, np.asarray(P, np.float64)))

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2:
                (ax, ay), (bx, by) = out[-2], out[-1]
                if (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) > 0:
                    break
                out.pop()
            out.append(p)
        return out[:-1]

    return np.array(half(pts) + half(pts[::-1]), np.float64)


def inside_hull(H, pts, tol=1e-12):
    """凸包(反時計回り)の内側か。"""
    k = len(H)
    ok = np.ones(len(pts), bool)
    for i in range(k):
        ax, ay = H[i]
        bx, by = H[(i + 1) % k]
        cross = (bx - ax) * (pts[:, 1] - ay) - (by - ay) * (pts[:, 0] - ax)
        ok &= cross >= -tol
    return ok


# --------------------------------------------------------------------------- #
# 絵づくり                                                                      #
# --------------------------------------------------------------------------- #
def draw_polyline(shape, pts, half, colour, width=1.6, close=False,
                  base=None):
    """折れ線を薄く重ねる(図の説明用。測定には使わない)。"""
    n = shape
    img = np.ones((n, n, 3), np.float64) * np.array(_PAPER) if base is None \
        else base.copy()
    P = np.asarray(pts, np.float64)
    if close:
        P = np.vstack([P, P[:1]])
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        steps = max(2, int(np.hypot(*(b - a)) / (2.0 * half) * n * 2))
        for s in np.linspace(0.0, 1.0, steps):
            x, y = a + (b - a) * s
            c = int(round((x + half) / (2.0 * half) * (n - 1)))
            r = int(round((half - y) / (2.0 * half) * (n - 1)))
            lo = int(np.floor(-width)); hi = int(np.ceil(width)) + 1
            for dr in range(lo, hi):
                for dc in range(lo, hi):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < n and 0 <= cc < n:
                        img[rr, cc] = colour
    return img


def fit_frame(*point_sets, margin=1.14):
    """描く点の広がりから、中心と半幅を決める(隅に寄らないように)。"""
    P = np.vstack([np.asarray(q, np.float64) for q in point_sets])
    c = 0.5 * (P.max(axis=0) + P.min(axis=0))
    return c, float(np.max(np.abs(P - c))) * margin


def shape_picture(V, n=360, half=1.6, colour=(0.19, 0.44, 0.62)):
    cov = poly_coverage(V, n, half=half, sub=2)
    img = np.ones((n, n, 3), np.float64) * np.array(_PAPER)
    for c in range(3):
        img[..., c] = img[..., c] * (1.0 - cov) + colour[c] * cov
    return img


def main():
    t0 = time.time()
    print("PoC: 遠ざかると消える距離と、形が変わるときの面積")
    print("=" * 72)

    # ---------------------------------------------------------------- #
    print("\n1. 分解の直交性 —— 理想マスクは厳密、ぼかしは厳密でない")
    n = 256
    g = np.linspace(-1.0, 1.0, n)
    X, Y = np.meshgrid(g, g)
    rng = np.random.default_rng(7)
    base = (0.5 + 0.30 * np.sin(9.0 * X) * np.cos(7.0 * Y)
            + 0.15 * rng.standard_normal((n, n)))

    cuts = (0.02, 0.05, 0.10, 0.20)
    ideal_recon, ideal_dot, ideal_gap = [], [], []
    for cut in cuts:
        lo, hi = split_ideal(base, cut)
        ideal_recon.append(float(np.max(np.abs(lo + hi - base))))
        ideal_dot.append(abs(float(np.sum(lo * hi))))
        ideal_gap.append(abs(energy_gap(lo, hi, base)))
        print("   遮断 %.2f  再構成 %.1e  内積 %.1e  エネルギーの帳尻 %.1e"
              % (cut, ideal_recon[-1], ideal_dot[-1], ideal_gap[-1]))
    check(max(ideal_recon) < 1e-12, "理想マスクは足せば元に戻る",
          "最大 %.1e(4 通りの遮断)" % max(ideal_recon))
    check(max(ideal_gap) < 1e-12,
          "★理想マスクはエネルギーが厳密に足し算(= 直交)",
          "帳尻の相対値 最大 %.1e" % max(ideal_gap))

    knobs = (0.1, 0.3, 0.5, 0.7, 0.9)
    g_recon, g_gap = [], []
    for a in knobs:
        lo, hi = split_gauss(base, a)
        g_recon.append(float(np.max(np.abs(lo + hi - base))))
        g_gap.append(abs(energy_gap(lo, hi, base)))
        print("   ぼかし a=%.1f(σ=%.2f) 再構成 %.1e  エネルギーの帳尻 %.4f %%"
              % (a, 0.3 + 2.7 * a, g_recon[-1], 100.0 * g_gap[-1]))
    check(max(g_recon) < 1e-12, "ぼかしでも足せば元に戻る(可逆)",
          "最大 %.1e" % max(g_recon))
    check(min(g_gap) > 1e-3,
          "★しかし直交しない —— 帳尻が合わない",
          "%.2f %% 〜 %.2f %%。**可逆と直交は別**"
          % (100.0 * min(g_gap), 100.0 * max(g_gap)))
    worst_knob = knobs[int(np.argmax(g_gap))]
    best_knob = knobs[int(np.argmin(g_gap))]
    check(best_knob not in (knobs[0], knobs[-1]),
          "★ずれはノブに対して単調でない —— 強くしても弱くしても直らない",
          "いちばんずれるのは a=%.1f(%.2f %%)、いちばん小さいのは "
          "a=%.1f(%.2f %%)。**両端ではない**"
          % (worst_knob, 100.0 * max(g_gap), best_knob, 100.0 * min(g_gap)))

    # ---------------------------------------------------------------- #
    print("\n2. 遠ざかると消える距離は整数 —— 1 画素ずれると戻る")
    m = 1536
    xs = np.arange(m)
    periods = (8, 12, 16, 24, 32)
    at_p, near_err = [], []
    for p in periods:
        f = 1.0 / p
        wave = np.sin(2.0 * np.pi * f * xs)
        amps, preds = {}, {}
        for k in (p - 1, p, p + 1, 2 * p):
            d = bin_pixels(wave[None, :].repeat(2, 0), 1)  # 形だけ合わせる
            s = m // k * k
            dd = wave[:s].reshape(-1, k).mean(axis=1)
            amps[k] = float(np.ptp(dd)) / 2.0
            preds[k] = box_transfer(f, k)
        at_p.append(amps[p])
        near_err.append(max(abs(amps[p - 1] - preds[p - 1]),
                            abs(amps[p + 1] - preds[p + 1])))
        print("   周期 %2d 画素  k=p-1 %.4f(閉形式 %.4f)  k=p %.1e  "
              "k=p+1 %.4f(閉形式 %.4f)"
              % (p, amps[p - 1], preds[p - 1], amps[p],
                 amps[p + 1], preds[p + 1]))
    check(max(at_p) < 1e-12,
          "★周期 p 画素の模様は p 画素に束ねるとちょうど消える",
          "5 通りの周期で最大 %.1e —— **消える距離は整数**" % max(at_p))
    check(max(near_err) < 1e-9,
          "★1 画素ずれると戻る(閉形式どおりの振幅で)",
          "k = p ± 1 で閉形式との差 最大 %.1e" % max(near_err))

    ks = np.arange(1, 49)
    f0 = 1.0 / 24.0
    wave = np.sin(2.0 * np.pi * f0 * xs)
    meas_h, pred_h, series_err = [], [], []
    for k in ks:
        s = m // k * k
        dd = wave[:s].reshape(-1, k).mean(axis=1)
        series_err.append(float(np.max(np.abs(
            dd - binned_closed_form(f0, k, len(dd))))))
        meas_h.append(float(np.ptp(dd)) / 2.0)
        pred_h.append(box_transfer(f0, k))
    meas_h = np.array(meas_h); pred_h = np.array(pred_h)
    check(max(series_err) < 1e-12,
          "★束ねた絵そのものが、1 画素ずつ閉形式で書ける",
          "束ね幅 1〜48 の全画素で最大の差 %.1e —— 振幅だけでなく "
          "**中心が (k−1)/2 ずれること**まで式に入っている"
          % max(series_err))
    naive_gap = float(np.max(np.abs(meas_h - pred_h)))
    naive_k = int(ks[int(np.argmax(np.abs(meas_h - pred_h)))])
    check(naive_gap > 1e-3,
          "★ところが「絵の最大と最小」で測った振幅は小さく出る",
          "最大のずれは k=%d で %.4f(%.2f %%)—— "
          "**画素が山の頂上を踏まない**から。閉形式は踏まなくても正しい"
          % (naive_k, naive_gap, 100.0 * naive_gap / pred_h[naive_k - 1]))

    # ---------------------------------------------------------------- #
    print("\n3. 外した予言 —— 切り替わりは遮断周波数では決まらない")
    nn = 512
    gg = np.linspace(-1.0, 1.0, nn)
    XX, YY = np.meshgrid(gg, gg)
    coarse = np.sin(3.0 * XX) * np.cos(2.0 * YY)
    fine = np.sin(70.0 * XX) * np.cos(61.0 * YY)
    F1, F2 = np.fft.fft2(coarse), np.fft.fft2(fine)
    rad = radial_freq(nn)

    def crossing(fc):
        mm = rad <= fc
        lo = np.real(np.fft.ifft2(F1 * mm))
        hi = np.real(np.fft.ifft2(F2 * (~mm)))
        hyb = lo + hi
        kk = [k for k in range(1, 65) if nn % k == 0]
        d = []
        for k in kk:
            a, b, c = (bin_pixels(hyb, k), bin_pixels(lo, k), bin_pixels(hi, k))
            d.append(_corr(a, b) - _corr(a, c))
        d = np.array(d); kk = np.array(kk, np.float64)
        i = int(np.argmax(d > 0))
        if i == 0:
            return float(kk[0]), hyb, lo, hi
        x0, x1 = np.log(kk[i - 1]), np.log(kk[i])
        y0, y1 = d[i - 1], d[i]
        return float(np.exp(x0 + (x1 - x0) * (-y0) / (y1 - y0))), hyb, lo, hi

    fcs = (0.015, 0.02, 0.03, 0.05)
    crosses, ratios = [], []
    for fc in fcs:
        c, _, _, _ = crossing(fc)
        crosses.append(c)
        ratios.append(c / (1.0 / (2.0 * fc)))
        print("   遮断 %.3f  予言 1/(2fc) = %4.1f 画素  実測 %4.1f 画素  比 %.3f"
              % (fc, 1.0 / (2.0 * fc), c, ratios[-1]))
    check(max(ratios) / min(ratios) < 4.0 and max(ratios) < 0.6,
          "★予言 1/(2 fc) は外れ —— 比が 1 にならない",
          "fc を %.0f 倍振って比は %.2f〜%.2f(1 なら当たり)"
          % (fcs[-1] / fcs[0], min(ratios), max(ratios)))
    check(float(np.ptp(crosses)) < 1.5,
          "★実測の切り替わりは遮断周波数でほとんど動かない",
          "%.1f〜%.1f 画素 —— 決めているのは**高域の絵が持つ周期**"
          % (min(crosses), max(crosses)))

    # ---------------------------------------------------------------- #
    print("\n4. 形の面積は t の厳密な 2 次式 —— 3 コマで全コマを予言する")
    ts = np.linspace(0.0, 1.0, 21)
    shapes = ((5, 0.60, 0.7), (7, 1.40, 0.0), (12, 0.35, 1.1))
    pred_err, d2_span = [], []
    for k, r2, ph in shapes:
        A, B = ngon(k), ngon(k, r=r2, phase=ph, cx=0.30, cy=-0.20)
        ar = np.array([abs(signed_area(morph(A, B, t))) for t in ts])
        c = quad_from_three(ts, ar)
        pred_err.append(float(np.max(np.abs(np.polyval(c, ts) - ar))))
        d2_span.append(float(np.ptp(np.diff(ar, 2))))
        print("   %2d 角形  3 コマからの予言誤差 %.1e   2 階差分の幅 %.1e"
              % (k, pred_err[-1], d2_span[-1]))
    check(max(pred_err) < 1e-12, "★面積は t の 2 次式(3 通りの形)",
          "予言誤差 最大 %.1e —— **3 コマ測れば全コマ出る**" % max(pred_err))
    check(max(d2_span) < 1e-12, "2 階差分が t に依らず一定",
          "幅 最大 %.1e" % max(d2_span))

    # ---------------------------------------------------------------- #
    print("\n5. その 2 次式が、絵からも出る(格子と細分を振る)")
    A6 = ngon(6)
    B6 = ngon(6, r=0.45, phase=0.9, cx=0.35, cy=-0.25)
    truth = np.array([abs(signed_area(morph(A6, B6, t))) for t in ts])
    rows = []
    for nn2, sub in ((128, 1), (256, 1), (512, 1), (128, 4), (256, 4), (512, 4)):
        meas = np.array([area_from_picture(morph(A6, B6, t), nn2, sub=sub)
                         for t in ts])
        c = quad_from_three(ts, meas)
        e = float(np.max(np.abs(np.polyval(c, ts) - meas)))
        rows.append((nn2, sub, e, 100.0 * e / truth.mean()))
        print("   格子 %4d 細分 %d  予言誤差 %.2e(面積の %.3f %%)"
              % (nn2, sub, e, rows[-1][3]))
    best = min(r[2] for r in rows)
    worst = max(r[2] for r in rows)
    check(best < worst / 10.0,
          "★絵から測った面積も、細かくすると 2 次式に寄る",
          "%.3f %% → %.3f %%"
          % (100.0 * worst / truth.mean(), 100.0 * best / truth.mean()))
    s1 = [r for r in rows if r[1] == 1]
    worse = [(s1[i], s1[i + 1]) for i in range(len(s1) - 1)
             if s1[i][2] < s1[i + 1][2]]
    check(bool(worse),
          "★細かくすれば必ず良くなるわけではない",
          "細分なしで 格子 %d → %d のとき %.3f %% → %.3f %% と**増える** —— "
          "多角形の辺と画素の格子の噛み合わせが変わるから"
          % (worse[0][0][0], worse[0][1][0], worse[0][0][3], worse[0][1][3])
          if worse else "単調だった")
    same = [r for r in rows if r[0] == 128 and r[1] == 4]
    same2 = [r for r in rows if r[0] == 512 and r[1] == 1]
    check(abs(same[0][2] - same2[0][2]) < 1e-12,
          "★1 画素を 4×4 に分けるのは、格子を 4 倍にするのと同じ",
          "格子 128 細分 4 と 格子 512 細分 1 が %.2e で一致"
          % abs(same[0][2] - same2[0][2]))

    # ---------------------------------------------------------------- #
    print("\n6. 絵から測ると符号が消える —— 予言はちょうど 25 % 外れる")
    flips = (("5 角形を裏返す", ngon(5), ngon(5)[::-1]),
             ("6 角形を回して裏返す", ngon(6), ngon(6, phase=0.4)[::-1]))
    flip_signed, flip_abs = [], []
    for name, A, B in flips:
        s = np.array([signed_area(morph(A, B, t)) for t in ts])
        a = np.abs(s)
        cs, ca = quad_from_three(ts, s), quad_from_three(ts, a)
        es = float(np.max(np.abs(np.polyval(cs, ts) - s)))
        ea = float(np.max(np.abs(np.polyval(ca, ts) - a)))
        flip_signed.append(es)
        flip_abs.append(100.0 * ea / max(a.max(), 1e-15))
        print("   %s  符号つき %.1e / 絵から測る %.4f(最大値の %.1f %%)"
              % (name, es, ea, flip_abs[-1]))
    check(max(flip_signed) < 1e-12,
          "符号つきなら裏返っても 2 次式のまま",
          "予言誤差 最大 %.1e" % max(flip_signed))
    check(max(abs(v - 25.0) for v in flip_abs) < 0.5,
          "★絵から測ると予言はちょうど 25 % 外れる",
          "実測 %s —— 1 次式の絶対値を 3 点で放物線に当てた外れ幅 = 最大値の 1/4"
          % " / ".join("%.1f %%" % v for v in flip_abs))
    zero_t = ts[int(np.argmin(np.abs(
        [signed_area(morph(flips[0][1], flips[0][2], t)) for t in ts])))]
    check(abs(zero_t - 0.5) < 1e-12, "裏返る途中で多角形は線に潰れる",
          "面積が 0 になるのは t = %.3f" % zero_t)

    # ---------------------------------------------------------------- #
    print("\n7. スプラインの 2 つの厳密な性質")
    P = np.array([[0.0, 0.0], [1.0, 2.0], [3.0, 1.0], [4.0, 3.0], [6.0, 0.0]])
    C = catmull_rom(P, m=40)
    worst_d = max(float(np.min(np.hypot(C[:, 0] - p[0], C[:, 1] - p[1])))
                  for p in P)
    print("   Catmull-Rom: 制御点 %d 個への最小距離の最大 = %.1e"
          % (len(P), worst_d))
    check(worst_d < 1e-12, "★Catmull-Rom は制御点を厳密に通る",
          "最小距離の最大 %.1e(制御点 %d 個)" % (worst_d, len(P)))

    rng2 = np.random.default_rng(3)
    all_in = []
    for _ in range(4):
        Pb = rng2.random((6, 2))
        Bz = bezier(Pb, m=401)
        H = convex_hull(Pb)
        all_in.append(int(inside_hull(H, Bz).sum()))
    print("   ベジエ: 凸包の中 %s / 401 点(4 通りの制御点)"
          % "、".join(str(v) for v in all_in))
    check(min(all_in) == 401, "★ベジエは制御点の凸包から出ない",
          "4 通りとも 401/401 点")

    # ---------------------------------------------------------------- #
    print("\n8. 図を書く")
    if figs.enabled():
        # 1. ハイブリッド画像 —— 近くで見る / 遠くで見る
        fc = 0.03
        _, hyb, lo_p, hi_p = crossing(fc)
        panels, caps = [], []
        for k in (1, 4, 16, 32):
            d = bin_pixels(hyb, k)
            up = np.kron(d, np.ones((k, k)))
            panels.append(_ramp(_norm(up)))
            caps.append("%d 画素に束ねる(= 遠ざかる)" % k if k > 1 else "そのまま")
        figs.save_grid("hybrid_near_far", panels, caps, ncols=2,
                       caption="低い周波数に粗い模様、高い周波数に細かい模様を"
                               "入れた 1 枚を、束ねながら見たもの。"
                               "**束ねるのは「遠ざかる」こと**で、"
                               "細かいほうが先に消える。"
                               "ただし ★**いつ消えるかは遮断周波数では決まらない** "
                               "—— 下の数表の「外した予言」を参照。")

        # 2. 分解の直交性
        lo_i, hi_i = split_ideal(base, 0.05)
        lo_g, hi_g = split_gauss(base, 0.5)
        figs.save_grid("orthogonal_split",
                       [_ramp(_norm(lo_i)), _ramp(_norm(hi_i)),
                        _ramp(_norm(lo_g)), _ramp(_norm(hi_g))],
                       ["理想マスク・低域(遮断 0.05)", "理想マスク・高域",
                        "ぼかし・低域(a = 0.5、σ = 1.65)", "ぼかし・高域(元 − 低域)"],
                       ncols=2,
                       caption="**どちらも足せば元に戻る**(再構成の誤差は両方 "
                               "1e-13 未満)。違うのはエネルギーの帳尻で、"
                               "上の組は相対 **%.1e** で合うのに、下の組は "
                               "**%.2f %%** ずれる —— **可逆であることと、"
                               "直交であることは別**。"
                               % (ideal_gap[1], 100.0 * g_gap[2]))

        figs.save_plot("energy_ledger",
                       [("理想マスク(遮断を振る)", list(cuts),
                         [max(v, 1e-17) for v in ideal_gap]),
                        ("ぼかし(ノブ a を振る)", [a / 8.0 for a in knobs],
                         list(g_gap))],
                       xlabel="遮断周波数(ぼかしは a/8 の位置に置いた)",
                       ylabel="|E(低)+E(高)−E(元)| / E(元)",
                       title="エネルギーの帳尻が合うか",
                       caption="縦軸は 0 が正解。理想マスクは 4 通りすべてで "
                               "2e-16 以下、ぼかしはどのノブでも "
                               "**%.2f %%〜%.2f %%** 離れる。"
                               "★しかも**単調ではない** —— いちばんずれるのは "
                               "a = %.1f で、強くしても弱くしても直らない。"
                               "横軸のぼかし側は a を 8 で割って重ねただけで、"
                               "遮断周波数と同じ量ではない。"
                               % (100.0 * min(g_gap), 100.0 * max(g_gap),
                                  worst_knob))

        # 3. 消える距離は整数(束ね幅を縦に積む。★各行を正規化しない)
        p = 24
        f = 1.0 / p
        width = 480
        line = np.sin(2.0 * np.pi * f * np.arange(width))
        band = []
        for k in range(1, 49):
            s2 = width // k * k
            dd = line[:s2].reshape(-1, k).mean(axis=1)
            up = np.repeat(dd, k)
            if len(up) < width:
                up = np.concatenate([up, np.full(width - len(up), up[-1])])
            band.append(np.repeat(up[None, :], 6, axis=0))
        band = np.vstack(band)
        band_img = _ramp(np.clip((band + 1.0) / 2.0, 0.0, 1.0))
        # ★消える行(f·k が整数)に左端で印を付ける
        for kk in (p, 2 * p):
            band_img[(kk - 1) * 6:(kk - 1) * 6 + 6, :14] = np.array(_MARK)
        figs.save("vanish_at_p", band_img,
                  caption="周期 **%d 画素**の縞を、上から順に 1, 2, 3 … 48 画素で"
                          "束ねたもの(各行が 1 つの束ね幅。★**行ごとの正規化は"
                          "していない**ので、薄い行は本当に薄い)。"
                          "**k = %d と k = %d でちょうど消える** —— "
                          "`sin(πfk)/(k sin(πf))` が 0 になる、つまり "
                          "**f·k が整数**になる幅(左端の橙がその 2 行)。振幅は k=%d で %.1e、"
                          "その 1 つ手前の k=%d では %.4f に戻る。"
                          % (p, p, 2 * p, p, at_p[3], p - 1,
                             box_transfer(f, p - 1)))

        figs.save_plot("transfer_curve",
                       [("閉形式 |sin(πfk)/(k sin(πf))|",
                         list(ks.astype(float)), list(pred_h)),
                        ("絵の最大と最小で測った振幅",
                         list(ks.astype(float)), list(meas_h))],
                       xlabel="束ねる幅 k(画素)", ylabel="残る振幅",
                       title="遠ざかったときに何が残るか(周期 24 画素)",
                       caption="k = 24 と k = 48(f·k が整数)で **厳密に 0**、"
                               "その間では戻る。★**束ねた絵そのもの**は 1 画素ずつ "
                               "閉形式と一致する(全画素で %.1e)のに、"
                               "**「絵の最大と最小」で振幅を測ると k=%d で %.2f %% "
                               "小さく出る** —— 画素が山の頂上を踏まないから。"
                               "式は踏まなくても正しい。"
                               % (max(series_err), naive_k,
                                  100.0 * naive_gap / pred_h[naive_k - 1]))

        # 4. 形が変わる
        frames = []
        for t in np.linspace(0.0, 1.0, 24, endpoint=False):
            tt = 0.5 - 0.5 * np.cos(2.0 * np.pi * t)   # 行って戻る
            frames.append(shape_picture(morph(A6, B6, tt), n=300))
        figs.save_gif("morph_loop", frames, fps=12,
                      caption="6 角形が別の 6 角形へ変わって戻るところ。"
                              "★見た目は連続に変わるが、**囲む面積は t の "
                              "厳密な 2 次式**に乗っている(次の図)。")

        steps, scaps = [], []
        for t in (0.0, 0.25, 0.5, 0.75):
            steps.append(shape_picture(morph(A6, B6, t), n=300))
            scaps.append("t = %.2f(面積 %.4f)"
                         % (t, abs(signed_area(morph(A6, B6, t)))))
        figs.save_grid("morph_steps", steps, scaps, ncols=4,
                       caption="同じモーフを 4 コマで。面積は "
                               "%.4f → %.4f と減るが、**減り方が 2 次式**。"
                               % (abs(signed_area(A6)),
                                  abs(signed_area(morph(A6, B6, 0.75)))))

        ar6 = np.array([abs(signed_area(morph(A6, B6, t))) for t in ts])
        c6 = quad_from_three(ts, ar6)
        figs.save_plot("area_is_quadratic",
                       [("全 21 コマの面積", list(ts), list(ar6)),
                        ("3 コマから当てた 2 次式", list(ts),
                         list(np.polyval(c6, ts)))],
                       xlabel="t", ylabel="囲む面積",
                       title="3 コマ測れば、全コマ予言できる",
                       caption="t = 0 / 0.5 / 1 の **3 コマだけ**から 2 次式を"
                               "決めて、残り 18 コマを予言した。"
                               "最大の差は **%.1e** —— グリーンの定理の積が "
                               "t について 2 次だから、これは偶然ではない。"
                               % float(np.max(np.abs(np.polyval(c6, ts) - ar6))))

        figs.save_plot("area_from_picture",
                       [("細分なし", [float(r[0]) for r in rows if r[1] == 1],
                         [r[3] for r in rows if r[1] == 1]),
                        ("1 画素を 4×4 に分ける",
                         [float(r[0]) for r in rows if r[1] == 4],
                         [r[3] for r in rows if r[1] == 4])],
                       xlabel="格子(画素)", ylabel="予言からのずれ(面積の %)",
                       title="絵から測っても、細かくすれば 2 次式に乗る",
                       caption="閉形式なら %.1e。**絵から測ると** 格子 128 で "
                               "%.2f %% あったずれが、格子 512・細分 4 で "
                               "**%.3f %%** まで縮む。"
                               "★ただし**単調ではない**(細分なしは 格子 %d → %d で "
                               "%.3f %% → %.3f %% と増える)—— 多角形の辺と画素の "
                               "格子の噛み合わせが変わるから。"
                               "★2 本の線は横軸 2 段ぶんずれて重なる —— "
                               "**1 画素を 4×4 に分けるのは、格子を 4 倍に"
                               "するのと同じ**(%.2e で一致)。"
                               % (max(pred_err), rows[0][3], rows[-1][3],
                                  worse[0][0][0], worse[0][1][0],
                                  worse[0][0][3], worse[0][1][3],
                                  abs(same[0][2] - same2[0][2])))

        # 5. 裏返すと予言が 25 % 外れる
        Af, Bf = flips[0][1], flips[0][2]
        sflip = np.array([signed_area(morph(Af, Bf, t)) for t in ts])
        aflip = np.abs(sflip)
        caf = quad_from_three(ts, aflip)
        figs.save_plot("flip_breaks_it",
                       [("絵から測る面積(必ず正)", list(ts), list(aflip)),
                        ("3 コマから当てた 2 次式", list(ts),
                         list(np.polyval(caf, ts))),
                        ("符号つき面積", list(ts), list(sflip))],
                       xlabel="t", ylabel="面積",
                       title="裏返るモーフでは、絵から測った瞬間に予言が破れる",
                       caption="5 角形を裏返すモーフ。**符号つき**の面積は "
                               "t の 1 次式で、2 次式の予言は %.1e で当たる。"
                               "しかし**絵から測れるのは正の面積だけ**なので "
                               "t = 0.5 で折り返し、3 コマから当てた放物線は "
                               "**最大値のちょうど 25 %% 外れる**(実測 %.1f %%)"
                               " —— 外れ方まで閉形式で出る。"
                               % (flip_signed[0], flip_abs[0]))

        fp = []
        for t in (0.0, 0.35, 0.5, 0.65):
            fp.append(shape_picture(morph(Af, Bf, t), n=300,
                                    colour=(0.55, 0.30, 0.55)))
        figs.save_grid("flip_steps", fp,
                       ["t = %.2f(符号つき面積 %+.3f)"
                        % (t, signed_area(morph(Af, Bf, t)))
                        for t in (0.0, 0.35, 0.5, 0.65)], ncols=4,
                       caption="同じモーフの絵。**t = 0.5 で多角形は線に潰れる** "
                               "—— 面積が 0 を通り、そこから先は向きが逆になる。"
                               "絵はそれを区別できない。")

        # 6. スプライン
        nimg = 360
        Ccur = catmull_rom(P, m=60)
        cen, halfp = fit_frame(P, Ccur)
        Pc = P - cen
        img = draw_polyline(nimg, Pc, halfp, (0.78, 0.80, 0.82), width=0.8,
                            close=False)
        img = draw_polyline(nimg, Ccur - cen, halfp, (0.19, 0.44, 0.62),
                            width=1.2, base=img)
        for q in Pc:
            img = draw_polyline(nimg, [q, q], halfp, _MARK, width=2.4, base=img)
        figs.save("catmull_through_points", img,
                  caption="薄い折れ線が制御点をつないだもの、濃い線が "
                          "Catmull-Rom。橙の点が制御点で、曲線は "
                          "**%d 個すべてを距離 %.1e で通る**(通ることが"
                          "定義に入っている補間スプラインだから)。"
                          % (len(Pc), worst_d))

        # ★見せる図は決め打ちの制御点で(検査のほうは乱数 4 通りで通してある)
        Pb = np.array([[-1.00, -0.55], [-0.62, 0.92], [0.28, 1.00],
                       [0.95, -0.18], [0.22, -1.00], [-0.38, -0.30]])
        Bz = bezier(Pb, m=401)
        Hb = convex_hull(Pb)
        cen2, half2 = fit_frame(Pb, Bz, Hb)
        shown_in = int(inside_hull(Hb, Bz).sum())
        img2 = draw_polyline(nimg, Hb - cen2, half2, (0.85, 0.72, 0.55),
                             width=1.0, close=True)
        img2 = draw_polyline(nimg, Bz - cen2, half2, (0.19, 0.44, 0.62),
                             width=1.2, base=img2)
        for q in Pb - cen2:
            img2 = draw_polyline(nimg, [q, q], half2, _MARK, width=2.0,
                                 base=img2)
        figs.save("bezier_hull", img2,
                  caption="ベジエ曲線(濃い線)、制御点(橙)と その凸包"
                          "(薄い橙)。この図では曲線の **%d/401 点**が凸包の"
                          "内側にあり、別に乱数で選んだ 4 通りの制御点でも "
                          "401/401。"
                          "★ベジエは制御点を**通らない**代わりに、"
                          "**凸包から出ない**ことが保証される —— "
                          "Catmull-Rom とちょうど裏返しの性質。" % shown_in)

        tbl = [
            ["理想マスクの分解", "E(低)+E(高)−E(元)", "0(厳密に直交)",
             "%.1e" % max(ideal_gap), "4 通りの遮断"],
            ["ぼかしの分解", "同上", "0 のはず", "%.2f %%〜%.2f %%"
             % (100.0 * min(g_gap), 100.0 * max(g_gap)),
             "★直交しない(5 通りのノブ)。足せば戻るのに"],
            ["同上", "ノブを振ると", "単調に減るはずだった",
             "最悪は a=%.1f" % worst_knob,
             "★外れ。両端でなく途中が最小"],
            ["束ねる(遠ざかる)", "周期 p の模様が消える幅", "k = p(整数)",
             "%.1e" % max(at_p), "5 通りの周期"],
            ["同上", "k = p ± 1 の振幅", "sin(πfk)/(k sin(πf))",
             "%.1e のずれ" % max(near_err), "1 画素ずれると戻る"],
            ["同上", "束ねた絵そのもの", "1 画素ずつ閉形式で書ける",
             "%.1e" % max(series_err), "k = 1〜48 の全画素"],
            ["同上", "最大と最小で測った振幅", "同じ閉形式のはず",
             "%.2f %% 小さい" % (100.0 * naive_gap / pred_h[naive_k - 1]),
             "★画素が山を踏まない k=%d で" % naive_k],
            ["モーフの面積", "t への依存", "2 次式(厳密)",
             "%.1e" % max(pred_err), "3 コマで全コマ予言"],
            ["絵から測った面積", "同上", "同じ 2 次式",
             "%.3f %%" % rows[-1][3], "格子 128 では %.2f %%" % rows[0][3]],
            ["細分と格子", "予言誤差", "同じ値になるはず",
             "%.1e の差" % abs(same[0][2] - same2[0][2]),
             "128×4分割 と 512 が一致"],
            ["裏返るモーフ", "絵から測った予言のずれ", "最大値の 1/4",
             "%.1f %% / %.1f %%" % (flip_abs[0], flip_abs[1]),
             "★符号が消えるから"],
            ["Catmull-Rom", "制御点への距離", "0", "%.1e" % worst_d,
             "通ることが定義"],
            ["ベジエ", "凸包の内側", "全点", "%d/401" % min(all_in),
             "4 通りの制御点"],
            ["切り替わる束ね幅", "1/(2 fc) か", "当たるはずだった",
             "比 %.2f〜%.2f" % (min(ratios), max(ratios)),
             "★外れ。決めるのは高域の周期"],
        ]
        figs.save_table("numbers", ["対象", "量", "真値", "実測", "備考"], tbl,
                        title="絵を見ずに採点した結果",
                        caption="真値はすべて**式から出る値**(パーセバルと直交、"
                                "箱平均の伝達関数、グリーンの定理、スプラインの"
                                "定義)で、実測は**絵と数列が返したもの**。"
                                "最後の行は**外した予言**をそのまま残してある。"
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


def _corr(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return 0.0 if d < 1e-15 else float((a * b).sum()) / d


if __name__ == "__main__":
    raise SystemExit(main())
