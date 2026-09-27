# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""文字はどこにあるか、を学習なしで —— 描いた文字の矩形を真値に、ストローク幅の検出器を採点する。

    py -3.11 examples/poc_text_region_truth.py

fullseye は OCR の前処理(傾き・二値化・連結成分)までで止まり、「どこに文字があるか」を
出す層が無かった。認識器(学習済みモデル)は載せない方針なので、文字の幾何 —— ストロークの
幅がほぼ一定 —— だけで領域を出す古典(Stroke Width Transform、Epshtein 2010)を op にした
(:mod:`textregion` の 3 op)。ここでは**自分でフォント描画した文字**を素材にする。描いたので
文字の矩形は 1 px 単位で分かり、それが真値になる。

この PoC が測る唯一の主張:

    **ストローク幅の一定性だけで、ラテン文字と CJK(漢字・かな)の行が同じ規則で見つかる。
    見つからなくなるのは、雑音でなく「ストローク幅が一定でなくなる」条件(太さの混在・
    小さすぎる字)である。**

検査する恒等式(下の assert、当てはめた数字は無い):

1. 幅 w の矩形ストロークの SWT = w(w = 3, 7、全画素で厳密)。
2. 描いたインク画素(雑音を乗せる前)のうち候補矩形に入った割合(再現率)と、候補矩形の
   面積のうちインクの割合(精度)。文字の大きさ 6 段・雑音 4 段で「どこから落ちるか」を測り、
   行のまとめ(検出した行数 vs 描いた行数)は別に出す。
3. 同じ画像を 2 倍に拡大すると、SWT の中央値も 2 倍(拡大前後の候補の中央値で厳密)。

フォントは手元で開けて CJK が描けるものを :func:`glyphops.available_fonts` で選ぶ。無ければ
ラテン文字だけで回り、その旨を印字する(CI の Linux では CJK フォントが無いことがある)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import annotate  # noqa: E402
import examplefig as figs  # noqa: E402
import glyphops  # noqa: E402
import textregion as T  # noqa: E402

SIZES = (12, 16, 24, 32, 48, 64)
NOISES = (0.0, 0.05, 0.10, 0.20)
LINES_LATIN = ("Stroke width", "fullseye 0.2", "no model needed")
LINES_CJK = ("画像検査の門", "文字領域を幾何で", "中文也可以")


def _font(cjk: bool):
    from PIL import ImageFont
    if cjk:
        fonts = glyphops.available_fonts()
        if not fonts:
            return None, "CJK フォント無し"
        return ImageFont.truetype(fonts[0], 48), Path(fonts[0]).name
    for p in annotate.FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, 48), Path(p).name
        except OSError:
            continue
    return ImageFont.load_default(), "PIL default"


def _page(lines, size, font, noise, seed):
    """行を縦に並べて描き、行ごとの矩形(真値)を返す。"""
    from PIL import Image, ImageDraw, ImageFont
    f = font.font_variant(size=size) if hasattr(font, "font_variant") else font
    W, H = 640, 40 + len(lines) * int(size * 1.8)
    im = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(im)
    truth = []
    y = 20
    for t in lines:
        d.text((24, y), t, fill=0, font=f)
        x0, y0, x1, y1 = d.textbbox((24, y), t, font=f)
        truth.append((y0, x0, y1, x1))
        y += int(size * 1.8)
    g = np.asarray(im, dtype=np.float64) / 255.0
    ink = g < 0.5                      # 真値: 描いたインク(雑音を乗せる前)
    if noise > 0:
        rng = np.random.default_rng(seed)
        g = np.clip(g + noise * rng.standard_normal(g.shape), 0.0, 1.0)
    return g, truth, ink


def _coverage(ink, boxes):
    """再現率 = 描いたインク画素のうち候補矩形に入った割合 / 精度 = 候補矩形の面積のうちインクの割合。
    真値は行矩形でなく**描いたインクそのもの**(行矩形は字間・上下の余白を含み、候補が字画ごとに
    出る検出器を面積で採点すると原理的に 100 % にならない、2026-09-27 実測)。"""
    d = np.zeros(ink.shape, bool)
    for y0, x0, y1, x1 in boxes:
        d[y0:y1, x0:x1] = True
    rec = float((ink & d).sum() / max(ink.sum(), 1))
    prec = float((ink & d).sum() / max(d.sum(), 1))
    return rec, prec


def _iou(a, b):
    y0, x0, y1, x1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, y1 - y0) * max(0, x1 - x0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def detect(g):
    r = T.swt_map(g, sigma=1.0, max_width=48)
    c = T.text_candidates(r["swt"], min_area=6)
    ln = T.text_lines(c["boxes"], c["stroke_width"])
    return r, c, ln


def main() -> None:
    # ---- 恒等式 1: 矩形ストローク --------------------------------------------------
    for w in (3, 7):
        img = np.ones((60, 160))
        img[25:25 + w, 20:140] = 0.0
        assert np.all(T.swt_map(img)["swt"][25:25 + w, 30:130] == w)
    # ---- 恒等式 3: 拡大 --------------------------------------------------------------
    img = np.ones((60, 160))
    img[25:30, 20:140] = 0.0
    a = T.swt_map(img)["swt"]
    b = T.swt_map(np.kron(img, np.ones((2, 2))))["swt"]
    assert np.median(a[a > 0]) == 5 and np.median(b[b > 0]) == 10
    print("恒等式: 矩形ストローク w=3,7 で SWT = w(全画素)/ 2 倍拡大で中央値 5 → 10")

    rows = []
    for cjk, lines in ((False, LINES_LATIN), (True, LINES_CJK)):
        font, fname = _font(cjk)
        if font is None:
            print("%s: %s —— この段は飛ばす(印字して残す)" % ("CJK" if cjk else "Latin", fname))
            continue
        print("\n%s(%s): インク再現率/矩形の精度 [%%]、列 = 文字の大きさ、行 = 雑音 σ。末尾は検出した行数(真値 %d 行)" % ("CJK" if cjk else "Latin", fname, len(lines)))
        print("  σ \\ size " + " ".join("%5d" % s for s in SIZES))
        for noise in NOISES:
            rec = []
            for size in SIZES:
                g, truth, ink = _page(lines, size, font, noise, seed=int(size * 100 + noise * 1000))
                _, c, ln = detect(g)
                cov, prec = _coverage(ink, c["boxes"])
                rec.append((cov, prec, len(ln["lines"])))
                rows.append((cjk, noise, size, cov, prec, len(ln["lines"])))
            print("  %4.2f     " % noise + " ".join("%3.0f/%3.0f" % (100 * cv, 100 * pr) for cv, pr, _ in rec)
                  + "   行 " + "/".join(str(n) for _, _, n in rec))

    # ---- 図: 実物の 1 枚(検出した行を重ねる)+ 再現率の曲線 --------------------------
    font, fname = _font(True)
    if font is None:
        font, fname = _font(False)
        lines = LINES_LATIN
    else:
        lines = LINES_CJK
    g, truth, _ink = _page(lines, 32, font, 0.05, seed=1)
    r, c, ln = detect(g)
    view = np.repeat(g[..., None], 3, axis=2)
    for (y0, x0, y1, x1) in truth:
        view[y0:y1, [x0, x1 - 1]] = (0.1, 0.6, 1.0)
        view[[y0, y1 - 1], x0:x1] = (0.1, 0.6, 1.0)
    for (y0, x0, y1, x1) in ln["lines"]:
        view[y0:y1, [x0, min(x1, view.shape[1]) - 1]] = (1.0, 0.4, 0.0)
        view[[y0, min(y1, view.shape[0]) - 1], x0:x1] = (1.0, 0.4, 0.0)
    pos = r["swt"][r["swt"] > 0]
    swt_view = np.clip(r["swt"] / max(float(np.percentile(pos, 99)) if pos.size else 1.0, 1e-9), 0.0, 1.0)   # 外れ値 1 本で潰れないよう 99 %点
    figs.save_grid("text_region_scene", [g, swt_view, view],
                   ["描いた行(σ=0.05、size 32)", "SWT(明るいほど太い)", "真値(青)と検出した行(橙)"],
                   title="%s —— 候補 %d / 行 %d(真値 %d 行)" % (fname, len(c["boxes"]), len(ln["lines"]), len(truth)), ncols=3)
    for cjk in (False, True):
        sub = [rw for rw in rows if rw[0] == cjk]
        if not sub:
            continue
        series = []
        for noise in NOISES:
            xs = np.array([rw[2] for rw in sub if rw[1] == noise], float)
            ys = np.array([100 * rw[3] for rw in sub if rw[1] == noise])
            series.append(("再現率 σ=%.2f" % noise, xs, ys))
        figs.save_plot("text_region_coverage_%s" % ("cjk" if cjk else "latin"), series,
                       xlabel="文字の大きさ [px]", ylabel="インクの再現率 [%]", ylim=(0.0, 100.0),
                       title="%s: 大きさと雑音で再現率はどこから落ちるか" % ("CJK" if cjk else "Latin"),
                       caption="真値は描いたインク画素。再現率 = インクのうち候補矩形に入った割合。")
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    clean = [rw for rw in rows if rw[1] == 0.0 and rw[2] >= 24]
    print("\nPASS: 恒等式 3 つが通り、雑音なし・size ≥ 24 のインク再現率は %s(平均 %.0f %%、精度の平均 %.0f %%)。"
          % ("/".join("%.0f%%" % (100 * rw[3]) for rw in clean), 100 * np.mean([rw[3] for rw in clean]) if clean else 0,
             100 * np.mean([rw[4] for rw in clean]) if clean else 0))


if __name__ == "__main__":
    main()
