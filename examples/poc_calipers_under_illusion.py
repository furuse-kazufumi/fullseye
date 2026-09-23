#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 産業用キャリパーを、錯視で健診する。

★この PoC の主張は「錯視がきれいです」ではない。**答えの分かっている図で、
測定器そのものを採点する**。Fullseye は

    真値つきの絵を作る op(``illusion_*``)と、
    HALCON 流のサブピクセル測定器(``measure_pos`` / ``measure_pairs`` /
    ``fuzzy_measure_pairing`` / ``apply_metrology_model``)

を**同じ箱**に持っている。だから「測定器が外すのはどこか、なぜか」を
1 本の走行で、**測った結果を絵の上に描き戻しながら**示せる。

新しい op は 1 つも足していない。全部すでにある op である。

結論を先に書くと:

  * カフェウォール ―― 目が「傾いている」と言い張る図で、正しく設定した
    キャリパーは傾き **0.0 を厳密に**返す。ただし**探索半幅を目地の帯幅
    以上にすると外れる**。しかも外れるのは**一部のずらし量だけ**で、
    既定に見える 0.25 はたまたま外れない側 ―― **探針 1 枚では足りない**。
    そして★**外したことは答え(0.14 度、目には「ほぼ 0」)ではなく
    残差(rms 0.00 → 1.70)に出る**。門は残差に置く。
  * ミュラー・リヤー ―― **キャリパーも外す。ただし目とは別の理由で。**
    矢羽根が測定線の上に余計なエッジを置くので、**違う構造を対にする**。
  * 想定幅を宣言したファジィ対選択は、外すのではなく
    **「合う対が無い」とスコアで申告する**。
  * 矢羽根が無くても答えは真値と合わない。これは錯視のせいではなく
    **「線分の長さ」と「外側エッジ間の距離」が別の量**だから。
    線幅を宣言すれば閉形式で説明できる。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import illusion as IL                                            # noqa: E402

L = fs.ledger
_PASS = []

_ACCENT = (0.05, 0.45, 0.95)      # 測定の幾何(測定線・当て直した直線)
_MARK = (1.00, 0.55, 0.00)        # 測定器が見つけたエッジ点


def check(ok, label, detail=""):
    _PASS.append(bool(ok))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label,
                            ("---- " + detail) if detail else ""))


# --------------------------------------------------------------------------- #
# 描き戻しの道具(測った結果を、絵の上に重ねる)                                   #
# --------------------------------------------------------------------------- #
def _as_gray(img):
    """錯視 op の返りは rgb (H, W, 3)。測る側は image2d なのでグレーにする。"""
    a = np.asarray(img, dtype=float)
    return a.mean(axis=2) if a.ndim == 3 else a


def _as_rgb(img):
    a = np.asarray(img, dtype=float)
    return a if a.ndim == 3 else np.repeat(a[..., None], 3, axis=2)


def _stroke(canvas, rows, cols, color, radius=1):
    """(row, col) の列に色を置く(画像の外は落とす)。"""
    h, w = canvas.shape[:2]
    for r, c in zip(np.asarray(rows, float), np.asarray(cols, float)):
        r0, c0 = int(round(r)), int(round(c))
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                rr, cc = r0 + dr, c0 + dc
                if 0 <= rr < h and 0 <= cc < w:
                    canvas[rr, cc] = color


def _line(canvas, r0, c0, r1, c1, color, radius=0):
    n = int(max(abs(r1 - r0), abs(c1 - c0))) + 1
    _stroke(canvas, np.linspace(r0, r1, n), np.linspace(c0, c1, n), color, radius)


def _bands_of_constant_rows(g):
    """行内の分散が 0 の行を、連続する帯にまとめる(目地の帯を拾う)。"""
    flat = np.where(g.std(axis=1) < 1e-12)[0]
    if flat.size == 0:
        return []
    bands, cur = [], [int(flat[0])]
    for r in flat[1:]:
        if int(r) == cur[-1] + 1:
            cur.append(int(r))
        else:
            bands.append(cur)
            cur = [int(r)]
    bands.append(cur)
    return bands


# --------------------------------------------------------------------------- #
# 第 1 章 カフェウォール —— 目が傾きを主張する図で、測定器は 0 を厳密に返す         #
# --------------------------------------------------------------------------- #
def chapter_cafe_wall():
    print("\n[1] カフェウォール —— 目地の傾きの真値は厳密に 0")
    img = L.illusion_cafe_wall(size=40, rows=8, cols=10, mortar=7.0, shift=0.25)
    g = _as_gray(img)
    h, w = g.shape
    truth = float(L.illusion_ground_truth("cafe_wall")["value"][0])

    bands = _bands_of_constant_rows(g)
    check(len(bands) >= 5 and all(len(b) >= 4 for b in bands),
          "目地の帯を行内分散 0 の行として拾えた",
          "%d 本、幅 %d px" % (len(bands), len(bands[0])))

    # (a) 探索半幅を振っても、当て直した直線の角度は動かない
    top = float(bands[len(bands) // 2][0]) - 0.5      # 中ほどの目地の上端
    sweep, pts = [], {}
    for ml in (3.0, 6.0, 10.0, 16.0):
        m = L.create_metrology_model()
        L.add_metrology_object_line_measure(m, top, 10.0, top, w - 10.0, n=41)
        res = L.apply_metrology_model(m, g, measure_length=ml, sigma=1.0,
                                      threshold=0.05)[0]
        p = res.get("params")
        ang = float("nan") if p is None else float(p["angle_deg"])
        sweep.append((ml, len(res.get("edge_points", [])), ang,
                      float(res.get("rms", np.inf))))
        pts[ml] = np.asarray(res.get("edge_points", []), dtype=float)
    angs = np.array([s[2] for s in sweep])
    check(bool(np.all(angs == 0.0)),
          "★探索半幅 3〜16 px のどれでも、当て直した直線の角度は厳密に 0",
          "真値 %.1f / 実測 %s" % (truth, ", ".join("%.1f" % a for a in angs)))
    check(all(s[3] == 0.0 for s in sweep),
          "当てた直線の残差 rms も厳密に 0(エッジ点が一直線に乗っている)")
    # ★はじめ図説に「半幅を変えると採用点の数が変わる」と書いたが、生成された
    #   本文を読むと 4 通りとも 41 点だった。**書いたことがデータと違った**ので
    #   直し、「変わらない」ほうを門にした。証拠の数が動く例は第 5 章のツェルナー。
    npts_sweep = [s[1] for s in sweep]
    check(len(set(npts_sweep)) == 1 and npts_sweep[0] == 41,
          "★採用点の数も半幅に依らない(4 通りとも同数)",
          "41 点中 %s —— 目地が一様グレーなので、半幅を広げても拾える点は増えない"
          % "/".join(str(n) for n in npts_sweep))

    # (b) ★探針 1 枚では足りない ---- ずらし量 × 探索半幅の格子で全数を見る
    #     最初は shift=0.25 だけで試して「測定器は決して動かない」と書いた。
    #     格子で見ると **0.125 と 0.375 でだけ** 0.14 度傾く。既定に見える
    #     0.25 は、たまたま外れない側だった。
    band_w = len(bands[0])
    shifts = (0.0, 0.125, 0.25, 0.375, 0.5)
    mls = (3.0, 6.0, 10.0, 16.0)
    grid_ang = np.zeros((len(shifts), len(mls)))
    grid_rms = np.zeros_like(grid_ang)
    for i, sh in enumerate(shifts):
        gi = _as_gray(L.illusion_cafe_wall(size=40, rows=8, cols=10, mortar=7.0,
                                           shift=sh))
        bi = _bands_of_constant_rows(gi)
        t = float(bi[len(bi) // 2][0]) - 0.5
        for j, ml in enumerate(mls):
            m = L.create_metrology_model()
            L.add_metrology_object_line_measure(m, t, 10.0, t,
                                                gi.shape[1] - 10.0, n=41)
            r = L.apply_metrology_model(m, gi, measure_length=ml, sigma=1.0,
                                        threshold=0.05)[0]
            p = r.get("params")
            grid_ang[i, j] = float("nan") if p is None else float(p["angle_deg"])
            grid_rms[i, j] = float(r.get("rms", np.inf))

    narrow = np.array([j for j, ml in enumerate(mls) if ml < band_w])
    wide = np.array([j for j, ml in enumerate(mls) if ml >= band_w])
    check(bool(np.all(grid_ang[:, narrow] == 0.0)),
          "★探索半幅が目地の帯幅 %d px より狭ければ、%d 通り全部で厳密に 0"
          % (band_w, len(shifts) * len(narrow)),
          "半幅 %s" % "/".join("%.0f" % mls[j] for j in narrow))
    bad = np.argwhere(grid_ang[:, wide] != 0.0)
    check(len(bad) > 0,
          "★★探索半幅が帯幅に届くと外れる ---- しかも外れるのは一部のずらし量だけ",
          "%d / %d 通りが非ゼロ: %s"
          % (len(bad), len(shifts) * len(wide),
             ", ".join("ずらし %.3f・半幅 %.0f で %+.4f 度"
                       % (shifts[i], mls[wide[j]], grid_ang[i, wide[j]])
                       for i, j in bad)))
    check(bool(np.all((grid_ang == 0.0) == (grid_rms == 0.0))),
          "★★★外したことは答えでなく残差に出る(角度 0 <=> rms 0 が全 %d 通りで一致)"
          % grid_ang.size,
          "外れた側の rms は %.2f(0.14 度は目で見れば「ほぼ 0」に見える)"
          % float(grid_rms[grid_rms > 0].max()))
    shift_ang = grid_ang[:, list(mls).index(10.0)]

    if figs.enabled():
        over = _as_rgb(img).copy()
        ep = pts[10.0]
        if ep.size:
            _stroke(over, ep[:, 0], ep[:, 1], _MARK, radius=1)
        _line(over, top, 10.0, top, w - 10.0, _ACCENT)
        figs.save("caliper_on_cafe_wall", over,
                  caption="カフェウォール錯視に、**産業用のサブピクセル測定器**を"
                          "当てたところ。青い罫が `add_metrology_object_line_measure` "
                          "で与えた参照線、橙の点が `apply_metrology_model` が"
                          "**法線方向に探して見つけたエッジ点** 41 個です。"
                          "★タイルは傾いて見えたままなのに、見つかった点は"
                          "**一直線**に乗り(rms = 0.0)、当て直した直線の角度は"
                          "**厳密に 0.0 度**。真値も 0。**測った結果を、絵の横では"
                          "なく絵の上に描き戻しています。**")
        x = np.array([s[0] for s in sweep], float)
        figs.save_plot("cafe_wall_sweep",
                       [("当て直した角度[度](実測)", x, angs),
                        ("真値 0", np.array([2.0, 17.0]), np.zeros(2))],
                       kinds=["scatter", "line"],
                       xlabel="探索半幅 measure_length [px]",
                       ylabel="目地の傾き[度]", ylim=(-0.6, 0.6),
                       title="探索半幅を 5 倍振っても、答えは動かない",
                       caption="`measure_length` は「参照線の法線方向に何 px 探すか」。"
                               "3 px から 16 px まで振っても角度は **0.0 のまま**で、"
                               "採用された点も **%d 通りとも %d 点**(%s)。"
                               "目地は一様なグレーなので、探索を広げても拾える点は"
                               "増えません。★これは**何も起きなかった図**です ---- "
                               "はじめこの図説に「半幅を変えると点の数が変わる」と"
                               "書きましたが、**生成された本文を読み返すとデータと"
                               "違っていました**。証拠の数が実際に動く例は"
                               "第 5 章のツェルナー(61 点中 13 と 19)のほうです。"
                               % (len(sweep), sweep[0][1],
                                  ", ".join("半幅 %.0f px" % s[0] for s in sweep)))
        xs = np.array(shifts, float)
        series = []
        for j, ml in enumerate(mls):
            series.append(("探索半幅 %.0f px" % ml, xs, grid_ang[:, j]))
        figs.save_plot("cafe_wall_grid",
                       series[:2] + [("真値 0", np.array([-0.02, 0.52]),
                                      np.zeros(2))] + series[2:],
                       kinds=["scatter", "scatter", "line", "scatter", "scatter"],
                       xlabel="1 行ごとのずらし量(タイル幅に対する割合)",
                       ylabel="測った目地の傾き[度]", ylim=(-0.05, 0.25),
                       title="探針 1 枚では足りない ---- 外れるのは一部のずらし量だけ",
                       caption="ずらし量 5 通り × 探索半幅 4 通りの **%d 通り全部**を"
                               "測ったもの。★はじめは ずらし量 0.25 だけで試して"
                               "「測定器は決して動かない」と書きました。格子で見ると、"
                               "**半幅が目地の帯幅 %d px に届く 10/16 px のとき、"
                               "ずらし量 0.125 と 0.375 でだけ 0.14 度傾きます**。"
                               "0.25 はたまたま外れない側だった ---- **既定に見える"
                               "1 点だけで試すと、この欠陥は構造的に見つかりません**。"
                               % (grid_ang.size, band_w))
        figs.save_plot("cafe_wall_residual",
                       [("当て直した角度[度]", np.arange(grid_ang.size, dtype=float),
                         grid_ang.ravel()),
                        ("当てた直線の残差 rms[px]",
                         np.arange(grid_ang.size, dtype=float), grid_rms.ravel())],
                       kinds=["scatter", "scatter"],
                       xlabel="ずらし量 × 探索半幅 の %d 通り" % grid_ang.size,
                       ylabel="値", ylim=(-0.15, 2.0),
                       title="外したことは答えでなく残差に出る",
                       caption="同じ %d 通りについて、**答え(角度)**と"
                               "**残差(rms)**を重ねたもの。★角度は外れても "
                               "**0.14 度** ---- 数字だけ見れば「ほぼ 0」で"
                               "通ってしまいます。ところが **rms は 0.00 から "
                               "%.2f へ桁で動く**。★★だから門は答えでなく"
                               "**残差に置く**。「当てた形が本当にそこにあったか」は"
                               "答えの側からは見えません。"
                               % (grid_ang.size, float(grid_rms.max())))

        # 外れた組み合わせを絵の上に描き戻す。★全体図では 8 px の飛びが潰れて
        #   見えないので、目地の帯の周りだけを**等倍で切り出す**。
        i_bad, j_bad = int(bad[0][0]), int(wide[bad[0][1]])
        raw = L.illusion_cafe_wall(size=40, rows=8, cols=10, mortar=7.0,
                                   shift=shifts[i_bad])
        gi = _as_gray(raw)
        bi = _bands_of_constant_rows(gi)
        t = float(bi[len(bi) // 2][0]) - 0.5
        crops, ccaps = [], []
        for ml, tag in ((mls[int(narrow[-1])], "帯幅より狭い探索"),
                        (mls[j_bad], "帯幅に届く探索")):
            m = L.create_metrology_model()
            L.add_metrology_object_line_measure(m, t, 10.0, t,
                                                gi.shape[1] - 10.0, n=41)
            rr = L.apply_metrology_model(m, gi, measure_length=ml, sigma=1.0,
                                         threshold=0.05)[0]
            ov = _as_rgb(raw).copy()
            ep = np.asarray(rr.get("edge_points", []), dtype=float)
            if ep.size:
                _stroke(ov, ep[:, 0], ep[:, 1], _MARK, radius=1)
            _line(ov, t, 10.0, t, gi.shape[1] - 10.0, _ACCENT)
            r0 = max(0, int(t) - 13)
            crops.append(ov[r0:r0 + 34])
            ang_ = rr["params"]["angle_deg"]
            ccaps.append("%s(半幅 %.0f px): 角度 %+.4f 度 / rms %.2f"
                         % (tag, ml, ang_, float(rr["rms"])))
        figs.save_grid("caliper_grabbed_the_far_side", crops, captions=ccaps,
                       ncols=1,
                       title="目地の帯の周りだけを等倍で切り出す",
                       caption="同じ図・同じ参照線(青)で、探索半幅だけを変えた"
                           "ときの測定器の見つけた点(橙)です。★全体図では "
                           "**%d px の飛びは潰れて見えません** ---- 目地の帯の"
                           "周り 34 行だけを等倍で切り出すと、下の段では点が"
                           "**帯の反対側にも乗っている**のが分かります。"
                           "目地の帯は %d px 幅なので、半幅 %.0f px の探索は"
                           "向こう側の境界にも届きます。★錯視のせいではなく、"
                           "**探索範囲の決め方**のせいです。帯幅より狭くすれば "
                           "%d 通り全部で厳密に 0 に戻ります。"
                           % (band_w, band_w, mls[j_bad],
                              len(shifts) * len(narrow)))
    return angs, shift_ang, grid_ang, grid_rms, shifts, mls, band_w


# --------------------------------------------------------------------------- #
# 第 2 章 ミュラー・リヤー —— 測定器も外す。ただし目とは別の理由で                  #
# --------------------------------------------------------------------------- #
def _shaft_row(g):
    return int(np.argmax((g < 0.5).sum(axis=1)))


def _caliper_on_shaft(g, margin=2.0):
    h, w = g.shape
    r = _shaft_row(g)
    mh = L.gen_measure_rectangle2(float(r), w / 2.0, 0.0, w / 2.0 - margin, 1.0,
                                  g.shape)
    edges = L.measure_pos(g, mh, sigma=1.0, threshold=0.05)
    pairs = L.measure_pairs(g, mh, sigma=1.0, threshold=0.05)
    return r, mh, edges, pairs


def chapter_muller_lyer():
    print("\n[2] ミュラー・リヤー —— 2 本の軸は厳密に等長(真値 220)")
    true_len = 220.0
    bare = IL.illusion_muller_lyer(length=true_len, head=0.0, angle_deg=35.0)
    arrow = IL.illusion_muller_lyer(length=true_len, head=34.0, angle_deg=35.0)
    gb, ga = _as_gray(bare), _as_gray(arrow)

    rb, mb, eb, pb = _caliper_on_shaft(gb)
    ra, ma, ea, pa = _caliper_on_shaft(ga)
    check(len(eb) == 2, "矢羽根なし: 測定線上のエッジはちょうど 2 本",
          "位置 %s" % ", ".join("%.2f" % e["dist"] for e in eb))
    check(len(ea) == 4, "★矢羽根あり: 測定線上のエッジが 4 本に増える",
          "位置 %s" % ", ".join("%.2f" % e["dist"] for e in ea))

    wb = float(pb[0]["width"]) if pb else float("nan")
    wa = float(pa[0]["width"]) if pa else float("nan")
    check(3.0 < abs(wb - true_len) < 5.0,
          "★矢羽根なしでも、測った幅は真値と 3〜5 px ずれる",
          "実測 %.3f / 真値 %.1f(差 %+.3f)" % (wb, true_len, wb - true_len))
    check(wa < 10.0,
          "★★矢羽根ありでは、測定器は軸ではなく矢羽根のストロークを対にする",
          "最良対の幅 %.3f px(軸の長さではない)" % wa)

    # ファジィ対選択: 想定幅を宣言すると「合う対が無い」と申告する
    fb = L.fuzzy_measure_pairing(gb, mb, sigma=1.0, threshold=0.05,
                                 pair_size=true_len)
    fa = L.fuzzy_measure_pairing(ga, ma, sigma=1.0, threshold=0.05,
                                 pair_size=true_len)
    sb = float(fb[0]["fuzzy_score"]) if fb else 0.0
    sa = float(fa[0]["fuzzy_score"]) if fa else 0.0
    check(sb > 0.99 and sa < 0.05,
          "★★想定幅を宣言すると、外すのではなく「合う対が無い」と申告する",
          "矢羽根なし %.4f -> 矢羽根あり %.4f" % (sb, sa))

    if figs.enabled():
        panels, caps = [], []
        for img, g_, r_, es, tag in ((bare, gb, rb, eb, "矢羽根なし"),
                                     (arrow, ga, ra, ea, "矢羽根あり")):
            ov = _as_rgb(img).copy()
            # ★測定線は軸そのものの上にある。そのまま塗ると被写体が消えるので、
            #   指示線だけ 12 px 上へ逃がして描く(測っている行は軸の行のまま)。
            ind = max(1, r_ - 12)
            _line(ov, ind, 2.0, ind, g_.shape[1] - 3.0, _ACCENT)
            for c_ in (2.0, g_.shape[1] - 3.0):
                _line(ov, ind, c_, min(g_.shape[0] - 1, r_ - 2), c_, _ACCENT)
            for e in es:
                cc = float(e.get("col", float(e["dist"]) + 2.0))
                _line(ov, max(0, r_ - 9), cc, min(g_.shape[0] - 1, r_ + 9), cc,
                      _MARK)
            panels.append(ov)
            caps.append("%s: 測定線上のエッジ %d 本" % (tag, len(es)))
        figs.save_grid("muller_caliper", panels, captions=caps, ncols=1,
                       title="同じ測定器を、同じ長さの 2 本の軸に当てる",
                       caption="青い横罫が測定線(`gen_measure_rectangle2`)、"
                               "橙の縦罫が `measure_pos` が見つけたサブピクセル"
                               "エッジです。**上は 2 本、下は 4 本**。"
                               "★矢羽根は「長く見せる」だけでなく、**測定線の上に"
                               "余計なエッジを置く**。測定器は隣り合う逆極性の"
                               "エッジを対にするので、**軸ではなく矢羽根のストローク"
                               "を測ってしまいます**(幅 %.2f px)。"
                               "目は「長く見える」と外し、測定器は「別の物を測る」"
                               "と外す ---- **外れ方が違う**。" % wa)
        labels = ("真値", "素朴な行走査", "キャリパー(矢羽根なし)",
                  "キャリパー(矢羽根あり)")
        naive = float(np.ptp(np.where(gb[rb] < 0.5)[0]) + 1)
        vals = np.array([true_len, naive, wb, wa])
        x = np.arange(len(labels), dtype=float)
        figs.save_plot("muller_widths",
                       [("測り方ごとの答え[px]", x, vals),
                        ("真値 220", np.array([-0.2, 3.2]), np.full(2, true_len))],
                       kinds=["scatter", "line"],
                       xlabel="測り方(0=真値 1=行走査 2=矢羽根なし 3=矢羽根あり)",
                       ylabel="軸の長さ[px]", ylim=(-10.0, 260.0),
                       title="同じ 1 本の軸が、測り方で 4 通りの答えになる",
                       caption="真値は生成器が保証する **%.1f px**。素朴な行走査は "
                               "**%.0f px**(反エイリアスの裾が端に乗る)、"
                               "キャリパーは矢羽根なしで **%.2f px**、"
                               "矢羽根ありで **%.2f px**(別の構造を測っている)。"
                               "★どれも「バグ」ではありません。**何を長さと呼ぶかを"
                               "決めずに測ると、決めていない分だけ答えが割れる**。"
                               % (true_len, naive, wb, wa))
        fx = np.arange(2, dtype=float)
        figs.save_plot("fuzzy_score",
                       [("想定幅 220 への適合度", fx, np.array([sb, sa])),
                        ("ぴったり合う = 1", np.array([-0.2, 1.2]), np.ones(2))],
                       kinds=["scatter", "line"],
                       xlabel="0 = 矢羽根なし / 1 = 矢羽根あり",
                       ylabel="fuzzy_score", ylim=(-0.05, 1.15),
                       title="測り方を宣言すると、静かな誤りが見える拒否に変わる",
                       caption="`fuzzy_measure_pairing` に「幅は %.0f px のはず」と"
                               "**宣言して**測らせたもの。矢羽根なしでは適合度 "
                               "**%.4f**(ほぼ 1)。矢羽根ありでは **%.4f** ---- "
                               "★これは「間違った値を返した」のではなく、"
                               "**「想定幅 %.0f の構造は見つからない」と数で申告"
                               "している**状態です。隣り合う逆極性の対しか候補に"
                               "しないので、軸をまたぐ対はそもそも提案されません。"
                               "**測り方を宣言した分だけ、失敗が静かな誤りから"
                               "見える拒否に変わります。**"
                               % (true_len, sb, sa, true_len))
    return true_len, wb, wa, sb, sa


# --------------------------------------------------------------------------- #
# 第 3 章 端の定義 —— ずれは錯視ではなく線幅である                                 #
# --------------------------------------------------------------------------- #
def chapter_edge_definition(true_len, wb):
    print("\n[3] 端の定義 —— 「線分の長さ」と「外側エッジ間の距離」は別の量")
    lens = (140.0, 180.0, 220.0, 260.0, 300.0)
    meas = []
    for ln in lens:
        g = _as_gray(IL.illusion_muller_lyer(length=ln, head=0.0, angle_deg=35.0))
        _, _, _, pr = _caliper_on_shaft(g)
        meas.append(float(pr[0]["width"]) if pr else float("nan"))
    meas = np.array(meas)
    resid = meas - np.array(lens)
    check(float(np.ptp(resid)) < 0.05,
          "★ずれは長さに依らず一定 ---- つまり錯視ではなく線幅である",
          "長さ %s に対し ずれ %s(振れ幅 %.4f px)"
          % ("/".join("%.0f" % v for v in lens),
             "/".join("%+.3f" % v for v in resid), float(np.ptp(resid))))
    offset = float(resid.mean())
    check(abs((wb - offset) - true_len) < 0.05,
          "線幅ぶんを引くと真値に戻る",
          "%.3f - %.3f = %.3f(真値 %.1f)" % (wb, offset, wb - offset, true_len))

    if figs.enabled():
        x = np.array(lens, float)
        figs.save_plot("edge_definition",
                       [("キャリパーの答え[px]", x, meas),
                        ("真値(生成器が保証)", x, x)],
                       kinds=["scatter", "line"],
                       xlabel="生成器に指定した長さ[px]",
                       ylabel="測った幅[px]",
                       title="ずれは長さに比例しない ---- 一定の下駄である",
                       caption="軸の長さを 140〜300 px まで振って、毎回同じ"
                               "キャリパーで測ったもの。答えは常に真値より "
                               "**%+.3f px** 大きく、**振れ幅は %.4f px しか"
                               "ありません**。★比例していれば倍率の誤り、"
                               "一定なら**端の定義のずれ**です。軸は太さを持って"
                               "描かれているので、外側エッジ間の距離は線分の長さ"
                               "より線幅ぶん長い。**引けば真値に戻ります**"
                               "(%.3f - %.3f = %.3f)。"
                               % (offset, float(np.ptp(resid)), wb, offset,
                                  wb - offset))
    return offset, meas, resid


# --------------------------------------------------------------------------- #
# 第 4 章 エビングハウス —— 円キャリパーは「同じ大きさ」と言う                     #
# --------------------------------------------------------------------------- #
# ★中心の座標は推測せず illusion.py から読む(最初 (h/2, w/4) と当てずっぽうに
#   置いて、周りの円のエッジを掴み rms が 3.4 になった)。真の中心は (170, 168)
#   と (170, 452)、半径 30。
_EBB_CENTRES = ((170.0, 168.0), (170.0, 452.0))
_EBB_RADIUS = 30.0


def chapter_ebbinghaus():
    print("\n[4] エビングハウス —— 中央の 2 円は厳密に同じ半径(真値 差 0)")
    img = L.illusion_ebbinghaus(radius=_EBB_RADIUS)
    g = _as_gray(img)
    fits = []
    for cr, cc in _EBB_CENTRES:
        m = L.create_metrology_model()
        L.add_metrology_object_circle_measure(m, cr, cc, _EBB_RADIUS, n=64)
        r = L.apply_metrology_model(m, g, measure_length=6.0, sigma=1.0,
                                    threshold=0.05)[0]
        fits.append((r, r["params"]))
    r0, r1 = float(fits[0][1]["radius"]), float(fits[1][1]["radius"])
    d = abs(r0 - r1)
    check(d < 1e-9,
          "★★目が「明らかに大きさが違う」と言う 2 円を、円キャリパーは同値と返す",
          "半径 %.6f / %.6f(差 %.3e px、真値 0)" % (r0, r1, d))
    check(all(len(f[0]["edge_points"]) == 64 for f in fits)
          and max(float(f[0]["rms"]) for f in fits) < 0.1,
          "どちらも円周 64 点すべてを採用し、円フィットの残差も小さい",
          "rms %s" % " / ".join("%.4f" % float(f[0]["rms"]) for f in fits))
    off = [float(fits[i][1]["col"]) - _EBB_CENTRES[i][1] for i in (0, 1)]
    check(abs(off[0] - off[1]) < 1e-9,
          "★中心のずれ %+.4f px は両方に同じだけ乗る系統誤差 ---- 差を取ると消える"
          % off[0],
          "左 %+.6f / 右 %+.6f(差 %.3e)" % (off[0], off[1], abs(off[0] - off[1])))

    if figs.enabled():
        ov = _as_rgb(img).copy()
        for (r_, p) in fits:
            ep = np.asarray(r_["edge_points"], dtype=float)
            if ep.size:
                _stroke(ov, ep[:, 0], ep[:, 1], _MARK, radius=1)
            th = np.linspace(0.0, 2 * np.pi, 400)
            _stroke(ov, p["row"] + p["radius"] * np.sin(th),
                    p["col"] + p["radius"] * np.cos(th), _ACCENT, radius=0)
        figs.save("ebbinghaus_circle_caliper", ov,
                  caption="エビングハウス錯視に**円の計測オブジェクト**"
                          "(`add_metrology_object_circle_measure`)を当てたもの。"
                          "橙が円周 64 方向に半径方向へ探して見つけたエッジ点、"
                          "青が**そこに当て直した円**です。★左の円は小さく、"
                          "右の円は大きく見えます。測った半径は "
                          "**%.6f px と %.6f px** ---- 差は **%.1e px**。"
                          "目が主張する差は測定器の側には存在しません。"
                          % (r0, r1, d))
        x = np.arange(2, dtype=float)
        figs.save_plot("ebbinghaus_radius",
                       [("測った半径[px]", x, np.array([r0, r1])),
                        ("生成器が指定した半径 %.0f" % _EBB_RADIUS,
                         np.array([-0.2, 1.2]), np.full(2, _EBB_RADIUS))],
                       kinds=["scatter", "line"],
                       xlabel="0 = 大きい円に囲まれた側 / 1 = 小さい円に囲まれた側",
                       ylabel="半径[px]", ylim=(29.9, 30.1),
                       title="差は 2.5e-12 px ---- 目が見ているものは画像に無い",
                       caption="縦軸を 0.2 px 幅まで拡大しても、2 つの点は"
                               "**重なったまま**です(差 %.1e px)。"
                               "どちらも指定した %.0f px より **%.4f px 小さい** ---- "
                               "これは反エイリアスの裾を含む端の定義のずれで、"
                               "★**両方に同じだけ乗るので、差を取ると消えます**。"
                               "第 3 章のミュラー・リヤーと同じ構造です。"
                               % (d, _EBB_RADIUS, _EBB_RADIUS - r0))
    return r0, r1, d


# --------------------------------------------------------------------------- #
# 第 5 章 ツェルナー —— 錯視の仕掛けは答えでなく「証拠の数」に効く                  #
# --------------------------------------------------------------------------- #
_ZOL_LINES, _ZOL_GAP = 7, 56.0


def chapter_zollner():
    print("\n[5] ツェルナー —— 長い線は厳密に平行(真値 傾きの広がり 0)")
    img = L.illusion_zollner(lines=_ZOL_LINES, gap=_ZOL_GAP, hatch_deg=38.0)
    g = _as_gray(img)
    h, w = g.shape
    angs, npts, rmss, eps = [], [], [], []
    for i in range(1, _ZOL_LINES + 1):
        cy = i * _ZOL_GAP
        m = L.create_metrology_model()
        L.add_metrology_object_line_measure(m, cy - 1.5, 20.0, cy - 1.5,
                                            w - 20.0, n=61)
        r = L.apply_metrology_model(m, g, measure_length=4.0, sigma=1.0,
                                    threshold=0.10)[0]
        angs.append(float(r["params"]["angle_deg"]))
        npts.append(len(r["edge_points"]))
        rmss.append(float(r["rms"]))
        eps.append(np.asarray(r["edge_points"], dtype=float))
    a = np.array(angs)
    check(float(np.abs(a).max()) < 1e-3,
          "★収束して見える %d 本すべてが、測ると水平" % _ZOL_LINES,
          "最大 |傾き| %.2e 度(500 px 渡って %.4f px)"
          % (np.abs(a).max(), w * np.tan(np.deg2rad(np.abs(a).max()))))
    check(float(np.ptp(a)) < 1e-3,
          "傾きの広がりも 0 に潰れている(真値 0)",
          "広がり %.2e 度" % float(np.ptp(a)))
    uniq = sorted(set(npts))
    check(len(uniq) == 2,
          "★★ハッチの向きが変わると、答えでなく**採用された点の数**が変わる",
          "61 点中 %s が採用(ハッチが交互に傾いているため)"
          % " と ".join(str(u) for u in uniq))

    if figs.enabled():
        ov = _as_rgb(img).copy()
        for i, ep in enumerate(eps):
            if ep.size:
                _stroke(ov, ep[:, 0], ep[:, 1], _MARK, radius=1)
        figs.save("zollner_caliper", ov,
                  caption="ツェルナー錯視の長い線 %d 本に、それぞれ直線の計測"
                          "オブジェクトを当てたもの。橙が採用されたエッジ点です。"
                          "★線は**収束して見えます**が、当て直した直線の傾きは"
                          "最大でも **%.1e 度**(画像の幅 %d px を渡って %.4f px "
                          "の高さ差)。★★注目は**点の密度が線ごとに違う**こと ---- "
                          "ハッチの向きが交互なので、61 点中 %s しか採用されません。"
                          "**錯視の仕掛けは答えではなく、証拠の量に効いています。**"
                          % (_ZOL_LINES, np.abs(a).max(), w,
                             w * np.tan(np.deg2rad(np.abs(a).max())),
                             " と ".join(str(u) for u in uniq)))
        x = np.arange(1, _ZOL_LINES + 1, dtype=float)
        figs.save_plot("zollner_angles",
                       [("測った傾き[度]", x, a),
                        ("真値 0", np.array([0.5, _ZOL_LINES + 0.5]), np.zeros(2)),
                        ("採用された点の数 ÷ 100", x, np.array(npts) / 100.0)],
                       kinds=["scatter", "line", "scatter"],
                       xlabel="上から何本目の長い線か",
                       ylabel="傾き[度] / 点の数 ÷ 100",
                       ylim=(-0.05, 0.25),
                       title="答えは動かない。動くのは証拠の数のほうだった",
                       caption="7 本の長い線について、**測った傾き**(真値 0)と"
                               "**採用されたエッジ点の数**を重ねたもの。"
                               "傾きは 7 本とも 0 の線に重なって見分けが付きません"
                               "(最大 %.1e 度)。一方で点の数は **%s** を"
                               "交互に取ります ---- ハッチの傾きが 1 本おきに"
                               "反転しているからです。★**「測れた」と「よく測れた」"
                               "は別の量**で、前者だけ見ていると差が見えません。"
                               % (np.abs(a).max(),
                                  " と ".join(str(u) for u in uniq)))
    return a, npts


# --------------------------------------------------------------------------- #
# 第 6 章 ポッゲンドルフ —— ここでは測定器が外す。そして残差がそれを申告する        #
# --------------------------------------------------------------------------- #
_POG_ANGLE, _POG_BAR = 30.0, 90.0


def _poggendorff_naive(g, cy, cx, w):
    """素朴: 見えている 2 区間に直線の計測オブジェクトを当てる。"""
    slope = np.tan(np.deg2rad(_POG_ANGLE))
    out = []
    for xa, xb in ((30.0, cx - 0.5 * _POG_BAR), (cx + 0.5 * _POG_BAR, w - 30.0)):
        m = L.create_metrology_model()
        L.add_metrology_object_line_measure(m, cy + slope * (xa - cx), xa,
                                            cy + slope * (xb - cx), xb, n=41)
        r = L.apply_metrology_model(m, g, measure_length=5.0, sigma=1.0,
                                    threshold=0.10)[0]
        out.append(r)
    return out


def _poggendorff_paired(g, cy, cx, w):
    """直し方: 線の**両側のエッジを対にして中心**を取り、その中心に直線を当てる。"""
    slope = np.tan(np.deg2rad(_POG_ANGLE))
    phi = np.deg2rad(90.0 + _POG_ANGLE)
    out = []
    for xa, xb in ((30.0, cx - 0.5 * _POG_BAR - 1.0),
                   (cx + 0.5 * _POG_BAR + 1.0, w - 30.0)):
        pts = []
        for x in np.linspace(xa, xb, 25):
            mh = L.gen_measure_rectangle2(cy + slope * (x - cx), x, phi, 8.0, 1.0,
                                          g.shape)
            pr = L.measure_pairs(g, mh, sigma=1.0, threshold=0.10)
            if not pr:
                continue
            p = pr[0]
            pts.append(((p["first_point"][0] + p["second_point"][0]) * 0.5,
                        (p["first_point"][1] + p["second_point"][1]) * 0.5))
        P = np.array(pts, dtype=float)
        k, b = np.polyfit(P[:, 1], P[:, 0], 1)
        rms = float(np.sqrt(((P[:, 0] - (k * P[:, 1] + b)) ** 2).mean()))
        out.append((k, b, rms, P))
    return out


def chapter_poggendorff():
    print("\n[6] ポッゲンドルフ —— 2 本の線分は厳密に共線(真値 角度差 0)")
    img = L.illusion_poggendorff(angle_deg=_POG_ANGLE, bar=_POG_BAR)
    g = _as_gray(img)
    h, w = g.shape
    cy, cx = h * 0.5, w * 0.5

    naive = _poggendorff_naive(g, cy, cx, w)
    na = [float(r["params"]["angle_deg"]) for r in naive]
    nr = [float(r["rms"]) for r in naive]
    d_naive = abs(na[0] - na[1])
    check(d_naive > 0.1,
          "★★ここでは測定器が外す ---- 共線のはずの 2 区間で角度が %.3f 度違う"
          % d_naive,
          "%.4f 度 と %.4f 度(真値は同じ)" % (na[0], na[1]))
    check(max(nr) > 1.0,
          "★★★そして残差がそれを申告している(答えだけ見ると 0.45 度は小さい)",
          "rms %.3f / %.3f px(第 1 章の合格例は 0.00)" % (nr[0], nr[1]))

    # 原因: 細い線には**上下 2 つのエッジ**があり、測定器はその間を行き来する
    amp = np.asarray(naive[0]["amplitudes"], dtype=float)
    runs = 1 + int((np.sign(amp[1:]) != np.sign(amp[:-1])).sum())
    check(runs < len(amp) // 2,
          "★原因: 極性が塊で交互する ---- 上側エッジと下側エッジを行き来している",
          "%d 点が %d 個の塊に分かれる(+%d / -%d)。無作為ならもっと細かく散る"
          % (len(amp), runs, int((amp > 0).sum()), int((amp < 0).sum())))

    paired = _poggendorff_paired(g, cy, cx, w)
    pa = [float(np.rad2deg(np.arctan(p[0]))) for p in paired]
    d_pair = abs(pa[0] - pa[1])
    check(d_pair < d_naive * 0.5,
          "★対にして中心を取ると、角度差も残差も下がる(ただし 0 にはならない)",
          "角度差 %.4f -> %.4f 度 / rms %.3f・%.3f -> %.3f・%.3f px"
          % (d_naive, d_pair, nr[0], nr[1], paired[0][2], paired[1][2]))

    if figs.enabled():
        ov = _as_rgb(img).copy()
        for r in naive:
            ep = np.asarray(r["edge_points"], dtype=float)
            if ep.size:
                _stroke(ov, ep[:, 0], ep[:, 1], _MARK, radius=1)
        for k, b, _rms, P in paired:
            cols = np.linspace(P[:, 1].min(), P[:, 1].max(), 300)
            _stroke(ov, k * cols + b, cols, _ACCENT, radius=0)
        figs.save("poggendorff_caliper", ov,
                  caption="ポッゲンドルフ錯視。帯の左右に見えている 2 本の線分は"
                          "**厳密に 1 本の直線**です(帯で隠れているだけ)。"
                          "橙が素朴な直線キャリパーの見つけた点、青が"
                          "**両側のエッジを対にして中心を取り直した**線です。"
                          "★橙の点は 1 本に乗っておらず、**線の上側と下側を"
                          "行き来しています** ---- 細い線には 2 つのエッジがあり、"
                          "「線の位置」はどちらか(あるいは中心か)を言うまで"
                          "定義されません。この図では測定器が **%.3f 度**の"
                          "非共線を報告します(真値 0)。" % d_naive)
        x = np.arange(2, dtype=float)
        figs.save_plot("poggendorff_residual",
                       [("素朴な直線キャリパーの残差[px]", x, np.array(nr)),
                        ("両エッジを対にした残差[px]", x,
                         np.array([paired[0][2], paired[1][2]])),
                        ("合格なら 0", np.array([-0.2, 1.2]), np.zeros(2))],
                       kinds=["scatter", "scatter", "line"],
                       xlabel="0 = 帯の左の線分 / 1 = 帯の右の線分",
                       ylabel="フィット残差 rms[px]", ylim=(-0.2, 2.6),
                       title="答えより先に、残差が「信じるな」と言っている",
                       caption="同じ 2 区間を 2 通りの測り方で当てたときの"
                               "**フィット残差**です。素朴な直線キャリパーは "
                               "**%.2f / %.2f px**、両エッジを対にすると "
                               "**%.2f / %.2f px** まで下がります(角度差も "
                               "%.3f → %.3f 度)。★★それでも 0 ではありません ---- "
                               "**この PoC は「直った」と書けません**。帯の縁の"
                               "細い縦線と画像の端が測定線に掛かっており、"
                               "そこまでは追い込んでいない、というのが正直な状態です。"
                               % (nr[0], nr[1], paired[0][2], paired[1][2],
                                  d_naive, d_pair))
    return d_naive, d_pair, nr, [paired[0][2], paired[1][2]]


def main():
    t0 = time.time()
    print("=" * 74)
    print("PoC: 産業用キャリパーを、錯視で健診する")
    print("=" * 74)
    angs, shift_ang, g_ang, g_rms, shifts, mls, band_w = chapter_cafe_wall()
    true_len, wb, wa, sb, sa = chapter_muller_lyer()
    offset, meas, resid = chapter_edge_definition(true_len, wb)
    r0, r1, dr = chapter_ebbinghaus()
    zang, znpts = chapter_zollner()
    d_naive, d_pair, nrms, prms = chapter_poggendorff()

    if figs.enabled():
        rows = [
            ["カフェウォール", "目地の傾き[度]", "0(厳密)",
             "%.1f" % float(g_ang[:, 0].max()), "探索半幅 < 帯幅 %d px" % band_w],
            ["カフェウォール", "目地の傾き[度]", "0(厳密)",
             "%+.4f" % float(g_ang.max()), "探索半幅 >= 帯幅(rms %.2f で申告)"
             % float(g_rms.max())],
            ["ミュラー・リヤー", "軸長[px]", "220.0", "%.3f" % wb,
             "矢羽根なし(差は線幅ぶんの一定の下駄 %+.3f)" % offset],
            ["ミュラー・リヤー", "軸長[px]", "220.0", "%.3f" % wa,
             "矢羽根あり ---- 軸でなく矢羽根を対にした"],
            ["ミュラー・リヤー", "想定幅 220 への適合度", "1.0", "%.4f" % sa,
             "宣言すると「合う対が無い」と申告(矢羽根なしは %.4f)" % sb],
            ["エビングハウス", "2 円の半径差[px]", "0(厳密)", "%.1e" % dr,
             "系統誤差は両方に同じだけ乗り、差で消える"],
            ["ツェルナー", "傾きの広がり[度]", "0(厳密)",
             "%.1e" % float(np.ptp(zang)),
             "答えでなく採用点数が %s と交互に変わる"
             % "/".join(str(u) for u in sorted(set(znpts)))],
            ["ポッゲンドルフ", "2 区間の角度差[度]", "0(厳密)",
             "%.3f" % d_naive, "★外した(rms %.2f が申告)" % max(nrms)],
            ["ポッゲンドルフ", "2 区間の角度差[度]", "0(厳密)",
             "%.3f" % d_pair,
             "両エッジを対にして中心を取ると下がる(rms %.2f)" % max(prms)],
        ]
        figs.save_table("audit", ["錯視", "量", "真値", "測定器の答え", "備考"],
                        rows,
                        title="測定器の健診結果",
                        caption="★この表に「絵を見て判断した」行は 1 つもありません。"
                                "真値は**生成器が保証**し、答えは**既存の測定 op**が"
                                "返したものです。**新しい op は 1 つも足していません**。"
                                "★真値をそのまま回復したのは **3 行**"
                                "(カフェウォール・エビングハウス・ツェルナー)。"
                                "**真値から外れたのは 5 行**で、内訳は 3 通りです ---- "
                                "(1) **決めれば戻るもの**: 探索半幅を帯幅より狭くする"
                                "(カフェウォール)、線幅ぶんの下駄を引く"
                                "(ミュラー・リヤー 矢羽根なし)。"
                                "(2) **拒否に変えられるもの**: 想定幅を宣言すると"
                                "間違った対でなく低い適合度が返る"
                                "(ミュラー・リヤー 矢羽根あり)。"
                                "(3) ★★**戻らなかったもの**: ポッゲンドルフは両エッジを"
                                "対にしても %.3f 度残り、**0 にはなっていません**。"
                                "この表は「全部直した」表ではなく、**どこまで"
                                "追い込んだかを正直に並べた**表です。" % d_pair)
        errs = figs.errors()
        assert not errs, errs

    ok = sum(_PASS)
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(_PASS), ok, time.time() - t0))
    if ok != len(_PASS):
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
