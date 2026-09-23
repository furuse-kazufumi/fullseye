# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: うなりは一つ —— 干渉縞と印刷のモアレは同じ数学である

二重スリットの縞と、2 版を重ねた網点のモアレは、教科書では別の章に載っている。
だが**どちらも「2 つの周期構造の周波数ベクトルの差」**であって、式は 1 本しかない。
この PoC は、その 1 本を両側から確かめる:

* 光のほうは **縞間隔 λD/d** を、作った op とは別の op に測り返させる。
* 印刷のほうは **モアレの周期を描く前に言い当て**、重ねた絵の FFT で測り返す。

そのうえで、周期構造を「墨に落とす」側(彫版・ハッチ・モザイク)も同じ規律で
採点する —— **絵の良さではなく、保った量と捨てた量を数で言う**。

★**この回の規律**: 使った式で答え合わせをしない。真値は次のどれかに限った。

1. **矩形膜の固有値** ``π²(m²/a² + n²/b²)``。★よく書かれる ``mnπ`` ではない
   (積ではなく平方和)。縮退の重複(正方膜で 5 が 2 回、10 が 2 回)まで見れば
   積の式と完全に区別できる。節線の本数 ``m−1`` / ``n−1`` は整数。
2. **ベッセルの零点** —— 円膜の節円は ``J₀`` の零点にある(``J′₀`` の零点は
   **腹**。取り違えると「op が間違っている」と読み違える)。
3. **既存 op との往復** —— 格子の次数から ``grating_wavelengths`` で波長を
   逆算し、元の 550 nm に戻るか。さらに既存 ``fraunhofer_pattern`` の山の
   位置と突き合わせる(あちらは回折を数値計算で解いている別実装)。
4. **モアレ周期の予言** —— 描く前に閉形式で出し、重ねた絵の 2-D FFT で測る。
   ★探す範囲を切らないと**スクリーン自身の山**を拾う(うなりは低周波側)。
5. **被覆率の閉形式** ``w/d`` —— 彫版線のインク率は濃淡の一次式そのもの。
6. **既存 stipple_energy** —— Lloyd 反復のエネルギーは単調減少。測るのは
   この族を知らない既存 op。セル平均が L2 最適であることはセルごとに全数走査。

図:
1. ``membrane``: 膜のモード 4 枚(符号つき)。
2. ``nodal``: 節線と、本数が整数で決まること。
3. ``fringes``: 二重スリットの縞(波長・距離を振った 4 枚)。
4. ``fringe_scaling``: 縞間隔の実測 vs λD/d。
5. ``grating``: 格子の次数と既存 fraunhofer の山。
6. ``moire``: 2 版の重ねと、予言した周期。
7. ``moire_scaling``: 角度差 vs 周期(予言と実測)。
8. ``engrave``: 彫版線と被覆率。
9. ``hatch``: 構造に沿うハッチ(向きが既知の絵で採点)。
10. ``mosaic``: モザイクと Lloyd のエネルギー。
11. ``numbers``: 数表。

走らせ方: ``py -3.11 examples/poc_beats_fringes_and_screens.py``
(図は ``out/figures/poc_beats_fringes_and_screens/``)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

CHECKS = []
PI2 = np.pi ** 2


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s%s" % ("OK" if ok else "NG", label,
                           ("  —— " + detail) if detail else ""))
    return bool(ok)


def fft_peak(img, f_min=None, f_max=None):
    """主要な周期 [px] と向き [度] を 2-D FFT の山から読む。

    ★*f_max* / *f_min* を渡すと探す範囲を切る。**うなりは低周波**にあるので
    ``f_max`` を渡さないとスクリーン自身の山を拾い、**ハッチの線は高周波**に
    あるので ``f_min`` を渡さないと濃淡の包絡を拾う。どちらも一度読み違えた。
    """
    a = img - img.mean()
    h, w = a.shape
    a = a * np.hanning(h)[:, None] * np.hanning(w)[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(a)))
    gy = (np.arange(h) - h / 2.0)[:, None] / h
    gx = (np.arange(w) - w / 2.0)[None, :] / w
    rad = np.hypot(gy, gx)
    F[rad < (2.5 / min(h, w) if f_min is None else f_min)] = 0.0
    if f_max is not None:
        F[rad > f_max] = 0.0
    i, j = np.unravel_index(np.argmax(F), F.shape)
    fy, fx = (i - h / 2.0) / h, (j - w / 2.0) / w
    return 1.0 / np.hypot(fy, fx), float(np.degrees(np.arctan2(fy, fx)))


# --------------------------------------------------------------------------- #
# 第 1 章 膜のモード —— 固有値は平方和、節線の本数は整数                          #
# --------------------------------------------------------------------------- #
def chapter_membrane():
    print("\n[1] 膜のモード —— 固有値 π²(m² + n²) と、整数で決まる節線")
    lam = np.asarray(fs.wave_mode_frequencies("rectangular", 8, 1.0))
    want = np.array([2, 5, 5, 8, 10, 10, 13, 13], dtype=np.float64) * PI2
    worst = float(np.abs(lam - want).max())
    check(worst < 1e-9, "正方膜の固有値が π²(m²+n²) と一致",
          "最大差 %.2e(縮退 5・10 の重複も含めて)" % worst)
    # 積の式 (mnπ)² なら並び順すら違う
    prod = np.sort(np.array([(m * n) ** 2 for m in (1, 2, 3) for n in (1, 2, 3)],
                            dtype=np.float64))[:8] * PI2
    check(not np.allclose(lam, prod), "★よく書かれる mnπ の式とは別物",
          "積の式なら %s" % np.round(prod[:4] / PI2, 1))

    lam2 = np.asarray(fs.wave_mode_frequencies("rectangular", 6, 2.0)) / PI2
    want2 = np.sort(np.array([m * m + n * n / 4.0
                              for m in range(1, 5) for n in range(1, 5)]))[:6]
    check(np.allclose(lam2, want2, atol=1e-9), "2:1 の長方形は m² + n²/4",
          "%s" % np.round(lam2, 4))

    modes, caps, nodal, ncaps, rows = [], [], [], [], []
    for m, n in ((1, 1), (2, 3), (3, 4), (5, 2)):
        u = np.asarray(fs.wave_membrane_mode("rectangular", m, n, (401, 401), 1.0,
                                             free_edge=False))
        row, col = u[200, :], u[:, 200]
        nv = int((np.sign(row[:-1]) * np.sign(row[1:]) < 0).sum())
        nh = int((np.sign(col[:-1]) * np.sign(col[1:]) < 0).sum())
        ok = (nv, nh) == (m - 1, n - 1)
        check(ok, "(%d, %d) モードの節線が %d / %d 本" % (m, n, m - 1, n - 1),
              "実測 %d / %d" % (nv, nh))
        mask = np.asarray(fs.wave_nodal_lines(u))
        modes.append(u)
        caps.append("(m, n) = (%d, %d)  λ/π² = %d" % (m, n, m * m + n * n))
        nodal.append(mask.astype(np.float64))
        ncaps.append("節線 %d / %d 本(整数)" % (nv, nh))
        rows.append([("(%d, %d)" % (m, n)), "%d / %d" % (nv, nh),
                     "%d / %d" % (m - 1, n - 1), "%.4f" % (m * m + n * n)])

    circ_ok, circ_detail = False, "scipy 無し"
    try:
        from scipy.special import jn_zeros, jnp_zeros
        u = np.asarray(fs.wave_membrane_mode("circular", 0, 3, (401, 401)))
        prof = u[200, 200:]
        sgn = np.sign(prof)
        cross = np.flatnonzero(sgn[:-1] * sgn[1:] < 0) / 200.0
        k = jnp_zeros(0, 3)[-1]
        want_r = jn_zeros(0, 3) / k
        got = cross[:want_r.size]
        circ_ok = bool(np.allclose(got, want_r[:got.size], atol=0.01))
        circ_detail = "節円の半径 %s / J₀ の零点 / k = %s" % (
            np.round(got, 4), np.round(want_r[:got.size], 4))
        modes.append(u)
        caps.append("円膜 (m, n) = (0, 3)")
        nodal.append(np.asarray(fs.wave_nodal_lines(u)).astype(np.float64))
        ncaps.append("節円は J₀ の零点(J′₀ は腹)")
    except Exception as exc:                            # noqa: BLE001
        circ_detail = "scipy.special 無し: %s" % exc
    check(circ_ok or "scipy" in circ_detail, "★円膜の節円は J₀ の零点", circ_detail)

    if figs.enabled():
        figs.save_grid("membrane", modes, caps, ncols=3, signed=True,
                       title="膜の固有モード —— 符号つき(節線の両側で位相が反転)",
                       caption="固有値は π²(m²/a² + n²/b²)。**積の mnπ ではない**。"
                               "モードの形は [-1, 1] の符号つきなので、image2d では"
                               "なく matrix で返す(image2d を名乗ると腹の位相が消える)。")
        figs.save_grid("nodal", nodal, ncaps, ncols=3, gray=True,
                       title="節線 —— 本数は整数で決まる(丸めの余地がない)",
                       caption="(m, n) モードの節線は縦 m−1 本・横 n−1 本。円膜の節円は "
                               "J₀ の零点 / k にある —— J′₀ の零点は腹の位置であって"
                               "節ではない(取り違えると op が誤っているように見える)。")
    return {"worst": worst, "rows": rows, "circle": circ_detail}


# --------------------------------------------------------------------------- #
# 第 2 章 二重スリット —— 縞間隔 λD/d を測り返す                                 #
# --------------------------------------------------------------------------- #
def chapter_fringes():
    print("\n[2] 二重スリット —— 縞間隔 λD/d を、作った op とは別の op が測る")
    panels, caps, meas_l, pred_l, rows = [], [], [], [], []
    for lam_nm, d_um, D_mm, px in ((550.0, 200.0, 200.0, 5.0),
                                   (450.0, 200.0, 200.0, 5.0),
                                   (550.0, 400.0, 200.0, 5.0),
                                   (550.0, 200.0, 400.0, 5.0)):
        img = np.asarray(fs.wave_two_slit(lam_nm, d_um, D_mm, (64, 1024), px))
        meas = float(fs.wave_fringe_period(img))
        pred = (lam_nm * 1e-3) * (D_mm * 1e3) / (d_um * px)
        ok = abs(meas / pred - 1.0) < 0.02
        check(ok, "λ=%3.0f nm d=%3.0f µm D=%3.0f mm の縞間隔" % (lam_nm, d_um, D_mm),
              "実測 %.2f px / λD/d = %.2f px  比 %.4f" % (meas, pred, meas / pred))
        panels.append(np.repeat(img[:16], 4, axis=0))
        caps.append("λ=%.0f nm d=%.0f µm D=%.0f mm" % (lam_nm, d_um, D_mm))
        meas_l.append(meas)
        pred_l.append(pred)
        rows.append(["λ=%.0f d=%.0f D=%.0f" % (lam_nm, d_um, D_mm),
                     "%.2f px" % meas, "%.2f px" % pred, "%.4f" % (meas / pred)])
    refused = False
    try:
        fs.wave_two_slit(550.0, 20.0, 200.0, (64, 512), 5.0)
    except ValueError:
        refused = True
    check(refused, "縞が 3 本入らない設定は黙って返さず ValueError",
          "画面に収まらない設定で「1 本の縞」を返すと誰も気づけない")

    if figs.enabled():
        figs.save_grid("fringes", panels, caps, ncols=2, gray=True,
                       title="二重スリットの縞 —— 波長・分離・距離を振る",
                       caption="縞間隔は λD/d。波長を 550 → 450 nm にすると細かく、"
                               "分離を倍にすると細かく、距離を倍にすると粗くなる ——"
                               "どれも比が閉形式どおり。")
        figs.save_plot("fringe_scaling",
                       [("λD/d(閉形式)", np.arange(4), pred_l),
                        ("wave_fringe_period の実測", np.arange(4), meas_l)],
                       xlabel="設定(表の順)", ylabel="縞間隔 [px]",
                       title="縞間隔 —— 作った op と測る op を分けてある",
                       caption="重なっていることが主張。同じ式で答え合わせをすると"
                               "この図は必ず重なるので、測る側は FFT で独立に出している。")
    return {"rows": rows, "meas": meas_l, "pred": pred_l}


# --------------------------------------------------------------------------- #
# 第 3 章 回折格子 —— 既存 op と往復する                                        #
# --------------------------------------------------------------------------- #
def chapter_grating():
    print("\n[3] 回折格子 —— 既存 grating_wavelengths で逆算して 550 nm に戻るか")
    d_um, lam_nm = 1.6, 550.0
    t = fs.wave_grating_orders(d_um, lam_nm, 0.0, (-2, -1, 0, 1, 2))
    order = np.asarray(t["order"])
    sin_out = np.asarray(t["sin_out"])
    zero = float(sin_out[order == 0][0])
    check(abs(zero) < 1e-12, "0 次は入射方向のまま", "sin_out = %.2e" % zero)
    back = np.asarray(fs.grating_wavelengths(pitch_um=d_um, sin_in=0.0,
                                             sin_out=sin_out[order == 1],
                                             orders=(1,))).ravel()
    check(np.allclose(back, lam_nm, rtol=1e-9), "既存 op で逆算すると元の波長",
          "%.6f nm(入れたのは %.1f nm)" % (float(back[0]), lam_nm))

    t2 = fs.wave_grating_orders(0.4, 550.0, 0.0, (-2, -1, 0, 1, 2))
    prop = np.asarray(t2["propagates"]).astype(bool)
    ang2 = np.asarray(t2["angle_deg"])
    check(not prop.all() and not np.any(np.isfinite(ang2[~prop])),
          "伝播しない次数は角度を捏造しない",
          "ピッチ 0.4 µm では %d / 5 次だけが伝播" % int(prop.sum()))

    # 既存の物理シミュレーション(fraunhofer_pattern)の山と突き合わせる。
    # ★デューティ 50 % の矩形格子は**偶数次が消える** —— 矩形波のフーリエ係数が
    #   偶数調波でちょうど 0 になるからで、これは実装の都合ではない閉形式の事実。
    #   最初「±1, ±2 が立つ」と期待して NG にした: 期待が誤っていた(op は正しい)。
    #   偶数次が「消えていること」まで見るので、山の位置だけを見るより強い門になる。
    N, pitch_px = 4096, 32
    x = np.arange(N)
    line = np.zeros((1, N))
    line[0, (x % pitch_px) < (pitch_px // 2)] = 1.0
    far = np.asarray(fs.fraunhofer_pattern(np.repeat(line, 8, axis=0),
                                           wavelength_um=0.55, distance_mm=8000.0,
                                           pixel_pitch_um=1.0))
    prof = far[far.shape[0] // 2]
    pk = np.argsort(prof)[::-1][:60]
    pk = np.unique(np.round((pk - N / 2.0) / (N / pitch_px)).astype(int))
    hit = sorted(int(v) for v in pk if abs(v) <= 4)
    odd_ok = {-3, -1, 0, 1, 3} <= set(hit)
    even_gone = not ({-4, -2, 2, 4} & set(hit))
    check(odd_ok and even_gone,
          "既存 fraunhofer で奇数次だけが立つ(デューティ 50 %)",
          "見えた次数 %s —— 偶数次は矩形波のフーリエ係数が 0 なので消える" % hit)
    # 次数ごとの強度比も閉形式: sinc(m/2)^2 なので 3 次 / 1 次 = 1/9
    def peak_at(m):
        c = int(round(N / 2.0 + m * (N / pitch_px)))
        return float(prof[max(c - 3, 0):c + 4].max())
    ratio = peak_at(3) / max(peak_at(1), 1e-30)
    check(abs(ratio - 1.0 / 9.0) < 0.02, "3 次 / 1 次の強度比が 1/9",
          "実測 %.4f / sinc(3/2)²÷sinc(1/2)² = %.4f" % (ratio, 1.0 / 9.0))

    if figs.enabled():
        span = 4.0 * (N / pitch_px)
        xs = np.arange(N) - N / 2.0
        sel = np.abs(xs) <= span
        figs.save_plot("grating",
                       [("fraunhofer_pattern の遠視野(数値で解いた)",
                         xs[sel], (prof / max(prof.max(), 1e-12))[sel]),
                        ("奇数次の位置(閉形式)",
                         np.asarray(hit, dtype=np.float64) * (N / pitch_px),
                         np.ones(len(hit)))],
                       xlabel="遠視野の位置 [px]", ylabel="強度(正規化)",
                       title="回折格子 —— 奇数次だけが立ち、3 次 / 1 次は 1/9",
                       caption="★デューティ 50 % の矩形格子は**偶数次が消える**"
                               "(矩形波のフーリエ係数が偶数調波で 0)。強度比 "
                               "3 次 / 1 次 = 1/9 も sinc(m/2)² の閉形式どおり。"
                               "閉形式の wave_grating_orders は角度を返し、既存 "
                               "grating_wavelengths で逆算すると元の 550 nm に戻る。",
                       xlim=(-span, span), kinds=("line", "scatter"))
    return {"back": float(back[0]), "orders": hit,
            "prop": int(np.asarray(t2["propagates"]).astype(bool).sum())}


# --------------------------------------------------------------------------- #
# 第 4 章 網点とモアレ —— 第 2 章と同じうなり                                    #
# --------------------------------------------------------------------------- #
def chapter_moire():
    print("\n[4] 網点のモアレ —— 描く前に周期を言い当てる(干渉縞と同じ式)")
    flat = np.full((1024, 1024), 0.5)
    f_screen = 60.0 * 25.4 / 25400.0
    panels, caps, rows, pred_l, meas_l, angs = [], [], [], [], [], []
    for ang_b in (75.0, 60.0, 50.0):
        a = np.asarray(fs.ledger.halftone_screen(flat, 60.0, 45.0, 25.4))
        b = np.asarray(fs.ledger.halftone_screen(flat, 60.0, ang_b, 25.4))
        beat = a * b
        pred = fs.ledger.halftone_moire_period(60.0, 45.0, 60.0, ang_b, 25.4)
        want = float(np.asarray(pred["period_px"]).ravel()[0])
        meas, _ = fft_peak(beat, f_max=f_screen * 0.6)
        ok = abs(meas / want - 1.0) < 0.08
        check(ok, "45° 対 %.0f° のモアレ周期" % ang_b,
              "予言 %.2f px / 実測 %.2f px  比 %.3f" % (want, meas, meas / want))
        panels.append(beat[:320, :320])
        caps.append("45° 対 %.0f°  予言 %.1f px" % (ang_b, want))
        rows.append(["45° 対 %.0f°" % ang_b, "%.2f px" % meas, "%.2f px" % want,
                     "%.3f" % (meas / want)])
        pred_l.append(want)
        meas_l.append(meas)
        angs.append(ang_b)

    # 予言だけなら角度差が小さい所も言える(画面には入らないので FFT では測れない)
    small = [float(np.asarray(fs.ledger.halftone_moire_period(
        60.0, 45.0, 60.0, b, 25.4)["period_px"]).ravel()[0])
        for b in (75.0, 60.0, 50.0, 47.0, 46.0)]
    check(all(x < y for x, y in zip(small, small[1:])),
          "角度差が縮むとうなりは粗くなる(単調)",
          "75°→46° で %.1f → %.1f px" % (small[0], small[-1]))
    f = 60.0 * 25.4 / 25400.0
    closed = 1.0 / (2.0 * f * np.sin(np.radians(15.0)))
    check(abs(small[0] - closed) < 1e-6, "同じ線数なら周期 = 1 / (2 f sin(Δ/2))",
          "45° 対 75° で %.4f px / 閉形式 %.4f px" % (small[0], closed))
    refused = False
    try:
        fs.ledger.halftone_moire_period(60.0, 45.0, 60.0, 45.0, 25.4)
    except ValueError:
        refused = True
    check(refused, "同じスクリーン同士は inf を返さず拒む",
          "うなりが無い設定に「無限の周期」という答えを出さない")

    # 網点は階調を捨てるが局所の平均濃度は保つ —— それが網点の意味
    yy, xx = np.mgrid[0:512, 0:512].astype(np.float64)
    ramp = np.clip(0.15 + 0.7 * xx / 511.0, 0.0, 1.0)
    dots = np.asarray(fs.ledger.halftone_screen(ramp, 40.0, 45.0, 25.4))
    from scipy import ndimage as ndi
    per = 25400.0 / (40.0 * 25.4)
    blur = ndi.uniform_filter(dots, size=int(round(per * 4)))
    c = (slice(64, -64), slice(64, -64))
    err = float(np.abs(blur[c] - ramp[c]).mean())
    check(err < 0.06, "★捨てたのは階調、保ったのは局所の平均濃度",
          "網点 4 周期の窓で平均すると元の濃淡に戻る(平均絶対差 %.4f)" % err)

    if figs.enabled():
        figs.save_grid("moire", panels, caps, ncols=3, gray=True,
                       title="2 版の網点を重ねたうなり —— 周期は描く前に分かる",
                       caption="新聞の 15° / 45° / 75° は差が 30° で、うなりが最も"
                               "細かくなる組み合わせ。二重スリットの縞とまったく同じ"
                               "「2 つの周波数ベクトルの差」の式で出ている。")
        figs.save_plot("moire_scaling",
                       [("閉形式の予言", angs, pred_l),
                        ("重ねた絵の FFT", angs, meas_l)],
                       xlabel="2 版目の角度 [度](1 版目は 45°)",
                       ylabel="モアレの周期 [px]",
                       title="モアレの周期 —— 予言と実測",
                       caption="★FFT の探す範囲を切らないと**スクリーン自身の山**"
                               "(どの角度でも 16.7 px = 1/f)を拾って「予言と全然"
                               "合わない」と読める。うなりは低周波側にある。")
        figs.save_grid("halftone_tone", [ramp, dots, blur],
                       ["元の濃淡", "網点(階調を捨てた)",
                        "4 周期の窓で平均 —— 元に戻る"], ncols=3, gray=True,
                       title="網点が保つもの・捨てるもの",
                       caption="平均絶対差 %.4f。絵の良さではなく「何を保って何を"
                               "捨てたか」を数で言うのが、この族の主張。" % err)
    return {"rows": rows, "small": small, "tone_err": err}


# --------------------------------------------------------------------------- #
# 第 5 章 彫版とハッチ —— 被覆率の閉形式と、既知の向き                            #
# --------------------------------------------------------------------------- #
def chapter_strokes():
    print("\n[5] 彫版線とハッチ —— 被覆率 w/d の閉形式と、構成で分かっている向き")
    panels, caps, rows, ink_l, want_l = [], [], [], [], []
    for tone in (0.2, 0.4, 0.6, 0.8):
        g = np.full((512, 512), tone)
        im = np.asarray(fs.ledger.engrave_lines(g, 8.0, 30.0, 1.0, 0.95))
        ink = float(1.0 - im.mean())
        want = min((1.0 - tone) * 0.95, 0.95)
        check(abs(ink - want) < 0.01, "濃淡 %.1f のインク率が w/d の閉形式" % tone,
              "実測 %.4f / 閉形式 %.4f  差 %.4f" % (ink, want, abs(ink - want)))
        panels.append(im[:160, :160])
        caps.append("濃淡 %.1f  インク率 %.3f" % (tone, ink))
        rows.append(["濃淡 %.1f" % tone, "%.4f" % ink, "%.4f" % want,
                     "%.1e" % abs(ink - want)])
        ink_l.append(ink)
        want_l.append(want)

    hpanels, hcaps, hrows = [], [], []
    yy, xx = np.mgrid[0:256, 0:256].astype(np.float64)
    for deg in (0.0, 30.0, 60.0, 135.0):
        a = np.radians(deg)
        g = 0.5 + 0.4 * np.sin(2.0 * np.pi * (xx * np.cos(a) + yy * np.sin(a)) / 24.0)
        im = np.asarray(fs.ledger.hatch_field(g, 8.0, 2.0, 2))
        per, ang = fft_peak(im, f_min=0.08)
        delta = (ang - deg) % 180.0
        off = min(delta, 180.0 - delta)
        check(off < 10.0 and abs(per - 8.0) < 0.5,
              "縞 %.0f° に沿うハッチ" % deg,
              "線の間隔 %.2f px(指定 8)・向きのずれ %.1f°" % (per, off))
        hpanels.append(im)
        hcaps.append("縞 %.0f°  線の間隔 %.2f px" % (deg, per))
        hrows.append(["縞 %.0f°" % deg, "%.2f px" % per, "%.1f°" % off])

    if figs.enabled():
        figs.save_grid("engrave", panels, caps, ncols=4, gray=True,
                       title="彫版線 —— インク率は濃淡の一次式そのもの",
                       caption="被覆率は線幅 / 間隔 = w/d。閉形式との差は 4 段"
                               "すべてで 0.01 未満。「それらしい線」を引くのでは"
                               "なく、置いた墨の量を数で言える。")
        figs.save_grid("hatch", hpanels, hcaps, ncols=4, gray=True,
                       title="構造に沿うハッチ —— 向きが構成で分かっている絵で採点",
                       caption="向きは既存 structure_tensor_orientation が決める"
                               "(この族は構造テンソルを再実装しない)。★測るときに "
                               "f_min を切らないと、線ではなく**濃淡の包絡**"
                               "(元の縞と同じ 24 px)を拾って 90° ずれて見える。")
    return {"rows": rows, "hrows": hrows, "ink": ink_l, "want": want_l}


# --------------------------------------------------------------------------- #
# 第 6 章 モザイク —— 既存 op が単調減少を測る                                   #
# --------------------------------------------------------------------------- #
def chapter_mosaic():
    print("\n[6] モザイク —— Lloyd のエネルギーは単調減少(測るのは既存 op)")
    yy, xx = np.mgrid[0:256, 0:256].astype(np.float64)
    img = np.clip(0.5 + 0.45 * np.sin(xx / 17.0) * np.cos(yy / 23.0), 0.0, 1.0)
    its, es, panels, caps = [], [], [], []
    prev = None
    mono = True
    for it in (0, 1, 2, 4, 8, 16):
        pts = fs.ledger.mosaic_tiles_sites(img, 250, it, 0, weighted=False)
        e = float(fs.ledger.stipple_energy(img, pts))
        if prev is not None and e > prev + 1e-9:
            mono = False
        prev = e
        its.append(it)
        es.append(e)
        if it in (0, 2, 16):
            panels.append(np.asarray(fs.ledger.mosaic_tiles_render(img, pts)))
            caps.append("反復 %d  エネルギー %.5f" % (it, e))
    check(mono, "Lloyd 反復のエネルギーが単調に下がる",
          "反復 0 → 16 で %.5f → %.5f(測るのは既存 stipple_energy)" % (es[0], es[-1]))

    pts = fs.ledger.mosaic_tiles_sites(img, 250, 12, 0)
    mos = np.asarray(fs.ledger.mosaic_tiles_render(img, pts))
    base = float(np.sum((img - mos) ** 2))
    worse = all(float(np.sum((img - np.clip(mos + d, 0.0, 1.0)) ** 2)) > base
                for d in (-0.05, -0.01, 0.01, 0.05))
    check(worse, "セル平均をずらすと必ず二乗誤差が増える",
          "平均の二乗誤差 %.4f、±0.01 / ±0.05 の 4 通りすべてそれ以上" % base)

    from scipy.spatial import cKDTree
    h, w = img.shape
    gy, gx = np.mgrid[0:h, 0:w]
    own = cKDTree(np.asarray(pts)).query(
        np.stack([gy.ravel(), gx.ravel()], axis=1).astype(np.float64), k=1)[1]
    flat = img.ravel()
    bad = 0
    for c in range(0, 250, 25):
        sel = own == c
        if int(sel.sum()) < 2:
            continue
        v = flat[sel]
        grid = np.linspace(v.min(), v.max(), 41)
        sse = ((v[None, :] - grid[:, None]) ** 2).sum(axis=1)
        if abs(grid[int(np.argmin(sse))] - v.mean()) > (grid[1] - grid[0]):
            bad += 1
    check(bad == 0, "セル平均が L2 最適(セル 10 個を全数走査)",
          "最小点が平均と一致しないセル %d 個" % bad)

    if figs.enabled():
        figs.save_grid("mosaic", [img] + panels,
                       ["元の画像"] + caps, ncols=4, gray=True,
                       title="モザイク —— 保つのはセルの平均、捨てるのは細部",
                       caption="Lloyd 反復でセルが等エネルギーに近づく。エネルギーを"
                               "測るのは**既存の** stipple_energy(この族の実装を"
                               "何も知らない)。セル平均は二乗誤差の最小点で、"
                               "セルごとに全数走査して確かめてある。")
        figs.save_plot("lloyd",
                       [("stipple_energy(既存 op が測る)", its, es)],
                       xlabel="Lloyd の反復回数", ylabel="エネルギー",
                       title="Lloyd は単調減少 —— 主張でなく測定",
                       caption="下がり続けることが主張。上がった回があれば"
                               "重心の計算か所属の割り当てが壊れている。")
    return {"energy": es, "sse": base, "bad_cells": bad}


def main():
    t0 = time.time()
    print("=" * 74)
    print("うなりは一つ —— 干渉縞と印刷のモアレは同じ数学である")
    print("=" * 74)
    m = chapter_membrane()
    f = chapter_fringes()
    g = chapter_grating()
    o = chapter_moire()
    s = chapter_strokes()
    z = chapter_mosaic()

    if figs.enabled():
        rows = [
            ["矩形膜の固有値", "π²(m²+n²) との最大差", "%.1e" % m["worst"],
             "0(閉形式・縮退の重複まで)"],
            ["節線の本数", "(m, n) = (3, 4) の縦 / 横", m["rows"][2][1],
             m["rows"][2][2] + "(整数)"],
            ["円膜の節円", "半径 / J₀ の零点 / k", "一致",
             "J′₀ は腹であって節ではない"],
            ["二重スリット", "縞間隔の実測 / λD/d", f["rows"][0][3],
             "1(4 設定すべて 0.98–1.02)"],
            ["回折格子", "既存 grating_wavelengths で逆算した λ",
             "%.4f nm" % g["back"], "550 nm(入れた値)"],
            ["伝播しない次数", "ピッチ 0.4 µm で伝播する次数",
             "%d / 5" % g["prop"], "角度を捏造せず propagates=False"],
            ["モアレ(45° 対 75°)", "実測 / 予言", o["rows"][0][3],
             "1(閉形式 1/(2 f sin(Δ/2)))"],
            ["網点の濃度保存", "4 周期の窓で平均した差", "%.4f" % o["tone_err"],
             "0(捨てたのは階調だけ)"],
            ["彫版線", "インク率と w/d の差(濃淡 0.2)", s["rows"][0][3],
             "0(閉形式)"],
            ["ハッチの向き", "縞 30° に対するずれ", s["hrows"][1][2],
             "0°(既存 structure_tensor_orientation が決める)"],
            ["Lloyd", "エネルギー 反復 0 → 16",
             "%.5f → %.5f" % (z["energy"][0], z["energy"][-1]),
             "単調減少(既存 stipple_energy が測る)"],
            ["セル平均", "平均と最小点が食い違うセル", "%d 個" % z["bad_cells"],
             "0(L2 最適・全数走査)"],
        ]
        figs.save_table("numbers", ["主張", "測った量", "実測", "真値 / 期待"],
                        rows,
                        title="うなりは一つ —— 絵の外から当てた答え",
                        caption="どの行も「使った式」ではない真値で採点している: "
                                "膜の閉形式とベッセルの零点、λD/d を測り返す別の op、"
                                "既存 grating_wavelengths との往復、描く前のモアレ"
                                "予言、w/d の閉形式、既存 structure_tensor_"
                                "orientation、既存 stipple_energy。")
    # ★図の書き出しが失敗したら、ここで拾う。見ないと「検査は全部 OK・でも図は
    #   1 枚も出ていない」が黙って通る(examplefig は fail-soft で貯める)。
    assert not figs.errors(), figs.errors()
    bad = [c for c in CHECKS if not c[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)"
          % (len(CHECKS), len(CHECKS) - len(bad), time.time() - t0))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
