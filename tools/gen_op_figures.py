#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""各 2-D op の「入力 → 出力」の図と、Studio で**そのまま走る**プログラムを作る。

    py -3.11 tools/gen_op_figures.py            # 全 op
    py -3.11 tools/gen_op_figures.py --limit 40 # 試し

## なぜ要るか(2026-09-06)

Studio のヘルプ 11,854 ページを実際に読んだところ、**画像を 1 枚も持っていな
かった**(0 ページ)。画像処理のオペレータの説明が全部文字なのは、辞書として
すら不便で、「見て選ぶ」ができない。

同じ日に手書きヘルプ 3 本と機械生成 902 本を並べて数えたところ、勝っている軸が
きれいに分かれた:

| | 手書き 3 本 | 機械生成 |
|---|---|---|
| 実行できる `sample:` パイプライン | 3/3 | **0** |
| 使い方の本文(中央) | 409 字 | 288 字 |
| 呼び出し形(コピーして動く 1 行) | **0/3** | 100 % |
| 型が繋がる次の op / 兄弟 / 出典 / 5 言語 | 一部 | ほぼ全数 |

機械生成に足りないのは「**その場で動く**」だけで、そこは機械にも作れる。
このスクリプトが埋めるのはそこ —— 各 op について

1. 画像から始めて**型が繋がる前置き**を求め、
2. **実際に走らせ**(`on_error="raise"`。fail-soft で恒等に落ちたものを
   「動いた」と数えない)、
3. 通ったものだけ図と `sample:` プログラムを出す。

走らなかったもの・型が届かないものは**理由つきで数える**(黙って飛ばさない)。

## 入力画像を合成にした理由

外部データセット(`skimage.data.camera` 等)は版で中身が変わりうるので、
図を commit する以上**再生成で同じ絵になる**ことを優先した。合成だが乱数の
一様ノイズではなく、**構造**を入れてある(円・矩形・細線・市松・階調)——
一様乱数だけの入力は対称性の破れを隠し、しきい値・形態学・周波数系の op が
「何をする op なのか」が絵に出ない。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import numpy as np  # noqa: E402

#: 図の置き場(GitHub Pages が配信する `docs/` の下。Studio 用は opdocs が複製)。
FIG_DIR = os.path.join(_ROOT, "docs", "ops", "_fig")
#: 生成の結果(op ごとの図・プログラム・失敗理由)。opdocs がこれを読む。
MANIFEST = os.path.join(_ROOT, "docs", "ops", "_fig", "figures.json")

#: 入力画像の一辺。小さすぎると窓の大きい op が意味を持たず、大きいと
#: 図が重くなる。128 は「5 段のガウシアンピラミッドが組める」下限。
SIZE = 128

#: `in_sort` ごとの前置き(画像から型を作る鎖)。2026-09-06 までは**画像から
#: 到達できる sort が 6 つだけ**(image / region / contour / color / feature /
#: match)で、残りの 161 op は「型が届かない」と記録するしかなかった。
#: 2026-09-07 に入口 op(`backends_bridge`、category `bridge`)を足し、**登録
#: されている全 in_sort に鎖がある**ことを `tests/test_op_figures.py` が確かめる。
#: ここに無い sort は「型が届かない」として記録される(落ちたとは数えない)。
PREFIX = {
    "image": [],
    "any": [],
    "region": [("threshold", 0.5, 0.5)],
    "contour": [("threshold", 0.5, 0.5), ("sk_find_contours", 0.5, 0.5)],
    "color": [("cfa_to_rgb", 0.5, 0.5)],
    # --- backends_bridge の入口 op(image → 新設 sort) ---
    "points": [("img_to_points", 0.5, 0.5)],
    "keypoints": [("img_to_keypoints", 0.5, 0.5)],
    "signal": [("img_to_signal", 0.5, 0.5)],
    "counts": [("img_to_counts", 0.5, 0.5)],
    "matrix": [("img_to_matrix", 0.5, 0.5)],
    "video": [("img_to_video", 0.5, 0.5)],
    "volume": [("img_to_volume", 0.5, 0.5)],
    "lightfield": [("img_to_lightfield", 0.5, 0.5)],
    "rgbimage": [("img_to_rgb", 0.5, 0.5)],
    "cimage": [("img_to_cimage", 0.5, 0.5)],
    "beatcube": [("img_to_beatcube", 0.5, 0.5)],
    # qimage は rgbimage を経由(rgb → 純四元数の埋め込みは既存の橋渡し op)。
    "qimage": [("img_to_rgb", 0.5, 0.5), ("tb_rgb_to_quaternion", 0.5, 0.5)],
}

#: op ごとの前置きの上書き。sort は同じでも **その op が受け付ける値の作り方が
#: 違う** とき(qimage: 色の四元数 vs モノジェニック信号)。
PREFIX_OP = {
    "tb_monogenic_amplitude": [("img_to_monogenic", 0.5, 0.5)],
    "tb_monogenic_phase": [("img_to_monogenic", 0.5, 0.5)],
    "tb_monogenic_orientation": [("img_to_monogenic", 0.5, 0.5)],
}

#: 型は届くが **定義域が合わない** op —— 汎用の合成入力では必ず拒否される
#: (その op が要るのは「ちょうど 3 点」「整数の添字」「64×64 の raster」…)。
#: 「落ちた」に混ぜず、理由つきで別に数える。**この表に載る op が通るように
#: なったら表から外す**(tests/test_op_figures.py が「本当にまだ拒否される」
#: ことを確かめる —— 免除台帳が黙って腐らないように)。
DOMAIN_MISMATCH = {
    "tb_angle_3points": "3 点(頂点 b と両端)を取る op で、(N,3) の点群は定義域の外",
    "tb_indices_to_labels": "signal を整数の添字として読む op で、濃度プロファイルは定義域の外",
    "tb_keypoints_to_image2d": "橋渡しで束縛した raster が 64×64 固定で、128×128 の点は外に落ちる",
    "tb_cx_apply_transfer_function": "橋渡しで束縛した伝達関数 H が 32×32 固定で、128×128 のスペクトルと合わない",
}

#: 出力の濃淡がこれより狭いときだけ min–max で伸ばし、キャプションで「伸ばした」と
#: 明示する(`out (stretched)`)。周波数系(fft / qft / gabor)は値の範囲が [0,1] の内側で
#: 0.01 程度に集まり、伸ばさないとほぼ黒い板になる(2026-09-07 実測 13 本)。
#: 伸ばした事実を隠すと弱い効果が強く見えるので、キャプションに残す。
STRETCH_BELOW = 0.1

#: ★2026-09-07(ユーザー指示「1 枚に纏める必要はない。段階的なもの・条件が複数
#: あるものは分けて出す」「物によっては疑似カラーのほうが分かりやすい」「複雑なものは
#: アニメーション GIF でも」)。主図 `<op>.png` に加えて、
#:   `<op>.a.jpg` / `<op>.b.jpg` — つまみを 0.1 / 0.5 / 0.9 に振った 3 枚(**出力が
#:                                変わるときだけ**。変わらなければ manifest に理由)
#:   `<op>.chain.jpg`            — 前置き op がある op の段階図(画像 → 中間 → 出力)
#:   `<op>.gif`                  — 出力が動画 / ライトフィールド / 体積のとき、フレーム /
#:                                視点 / スライスを順に見せる(静止画 `<op>.png` が完成形で
#:                                GIF は追加。Studio の QTextBrowser は 1 コマ目を出す)
#: 疑似カラーは**量の場**(距離・位相・向き・深度・曲率 …)の出力にだけ掛け、
#: キャプションに `(viridis)` と書く。フィルタ系はグレーのまま(色が変わる op に
#: 見せない)。
SWEEP = (0.1, 0.5, 0.9)
SWEEP_SIZE = 128           # 縮小しない(ユーザー指示 2026-09-07「縮小し過ぎ」)。容量は JPEG で抑える
JPEG_QUALITY = 92          # 3 枚組・段階図・複数入力は JPEG(主図と GIF は PNG/GIF のまま)
GIF_FRAMES = 8
GIF_SORTS = ("video", "lightfield", "volume")

import re as _re
#: 疑似カラーを掛ける op 名(出力 sort が image のときだけ)。量の場の名前。
PSEUDOCOLOR = _re.compile(
    r"dist|phase|orient|angle|depth|curv|hess|lapl|salien|heat|entrop|varian|energy|"
    r"sdf|height|dispar|harris|corner|frangi|sato|ridge|vessel|geodesic|spectrum|fft|"
    r"power|coheren|structure|eigen|response|score|prob|confidence|wavelet|dwt|texture|"
    r"coocc|lbp|gabor|_std|std_|dt_|_edt|edt_|hough|accum|vote|density|flow|monogenic")

#: viridis 風の 5 点 LUT(暗い紫 → 青 → 緑 → 黄)。matplotlib には依存しない。
_VIRIDIS = np.array([[0.267, 0.005, 0.329], [0.231, 0.322, 0.545], [0.129, 0.569, 0.549],
                     [0.369, 0.788, 0.384], [0.993, 0.906, 0.144]])


def _pseudocolor(gray01: np.ndarray) -> np.ndarray:
    """[0,1] のグレーを viridis 風 RGB に(線形補間)。"""
    g = np.clip(np.asarray(gray01, np.float64), 0, 1)
    x = g * (len(_VIRIDIS) - 1)
    i = np.clip(np.floor(x).astype(int), 0, len(_VIRIDIS) - 2)
    t = (x - i)[..., None]
    return _VIRIDIS[i] * (1 - t) + _VIRIDIS[i + 1] * t


def _wants_pseudocolor(op) -> bool:
    out_sort = op.in_sort if op.out_sort == "any" else op.out_sort
    return out_sort == "image" and bool(PSEUDOCOLOR.search(op.name))


#: つまみの既定。0.5 は「まん中」だが、平滑・形態学は効果が見えないので
#: 少しだけ強めに振る(op ごとではなくカテゴリごと —— 恣意を最小にする)。
KNOB = {"smoothing": (0.35, 0.5), "morphology": (0.35, 0.5),
        "edges": (0.4, 0.5), "frequency": (0.4, 0.5)}


def canonical_image() -> np.ndarray:
    """決定的な合成シーン。構造(円・矩形・細線・市松・階調)+ 弱いノイズ。"""
    n = SIZE
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    img = 0.18 + 0.42 * (xx / (n - 1))                    # 横方向の階調
    for cy, cx, r, v in ((34, 34, 17, 0.92), (36, 92, 9, 0.10),
                         (95, 40, 13, 0.72)):
        img[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = v  # 大きさ違いの円
    img[80:112, 74:118] = 0.86                             # 矩形
    img[20:24, 60:120] = 0.05                              # 太い線
    for c in range(62, 122, 6):                            # 細線の並び(平滑が効く)
        img[52:60, c:c + 1] = 0.98
    ch = ((yy[100:126, 4:30] // 4 + xx[100:126, 4:30] // 4) % 2)
    img[100:126, 4:30] = 0.15 + 0.7 * ch                   # 市松(周波数系)
    # ノイズは**右下の区画だけ**(構造としての「ノイズの多い領域」)。全面に
    # 撒くと PNG が縮まず 1 枚 16 KB になる(σ=0.02)。区画に限れば平滑・
    # 非局所平均などの効果はそこで見え、残り 3/4 はきれいに縮む。
    rng = np.random.default_rng(20260906)
    img[64:128, 64:128] = np.clip(
        img[64:128, 64:128] + rng.normal(0, 0.035, (64, 64)), 0, 1)
    return img


def _knobs(op) -> tuple:
    return KNOB.get(getattr(op, "category", ""), (0.5, 0.5))


def _program(op, chain) -> str:
    """Studio のプログラム文字列(1 行 1 op、`名前 a b`)。"""
    rows = ["%s %.2f %.2f" % (n, a, b) for n, a, b in chain]
    a, b = _knobs(op)
    rows.append("%s %.2f %.2f" % (op.name, a, b))
    return chr(10).join(rows)


def _is_image(v) -> bool:
    if isinstance(v, dict):
        return False
    a = np.asarray(v)
    return a.ndim in (2, 3) and a.size > 4 and a.dtype != object


def _plate(shape, value) -> np.ndarray:
    """絵にならない返り値(スカラ・辞書・1-D)を短い札にする。

    ★図の中の文字は**短い英語だけ**(ユーザー指示 2026-09-06)。ヘルプは 6 言語で
    出るが図は 1 枚なので、日本語を焼き込むと読めない読者が出る。言語ごとの
    説明は本文(対訳表)で持つ。

    最初の版は 1 行に書いて `text_box` が「128 px に収まらない」で 47 op ぶん
    落ちた。**op は走っていたのに描画側で落として「失敗」に数えていた** ——
    まさに数え間違いの型。3 行・各 16 字に折り返す。
    """
    import fullseye as fs

    if isinstance(value, dict):
        items = list(value.items())
        lines = ["%s=%s" % (k, _short(v, 10)) for k, v in items[:3]]
        if len(items) > 3:
            lines.append("+%d more" % (len(items) - 3))
    else:
        a = np.asarray(value)
        if a.ndim == 1:
            lines = ["n=%d" % a.size,
                     np.array2string(a[:3], precision=2, separator=",")[:16]]
        else:
            lines = ["→ " + _short(value, 14)]
    plate = np.full(shape, 0.12)
    y = 8
    for ln in lines[:4]:
        plate = np.asarray(fs.text_box(plate, ln[:16], (8, y),
                                       anchor="lt", font_size=10))
        y += 22
    return plate


def _line_plot(shape, y) -> np.ndarray:
    """1-D 列(signal / counts)を折れ線で描く。縦軸は min–max、横軸は添字。"""
    import fullseye as fs

    h, w = shape[:2]
    y = np.asarray(y, np.float64).ravel()
    plate = np.full((h, w, 3), 0.12)
    # 非有限(inf / NaN)は落として残りを描く —— 測地距離のように「届かない点 = inf」を
    # 含む列で何も描けなくなっていた(2026-09-07 実測: tb_geodesic_distances が真っ黒)。
    y = y[np.isfinite(y)]
    if y.size < 2:
        return plate
    lo, hi = float(y.min()), float(y.max())
    yn = (y - lo) / (hi - lo) if hi - lo > 1e-12 else np.full_like(y, 0.5)
    xs = np.linspace(4, w - 5, y.size)
    ys = (h - 5) - yn * (h - 10)
    pts = np.stack([xs, ys], axis=1)
    return np.asarray(fs.draw_polyline(plate, pts, color=(0.25, 0.85, 0.75), width=1,
                                       closed=False))


def _scatter(shape, xy, z=None) -> np.ndarray:
    """(N,2|3) の点を上から見た散布図(x → 列、y → 行、z → 明るさ)。"""
    h, w = shape[:2]
    plate = np.full((h, w, 3), 0.12)
    p = np.asarray(xy, np.float64)
    if p.ndim != 2 or p.shape[0] == 0:
        return plate
    x, y = p[:, 0], p[:, 1]
    def _n(t, n):
        lo, hi = float(t.min()), float(t.max())
        return ((t - lo) / (hi - lo) * (n - 5) + 2 if hi - lo > 1e-12
                else np.full_like(t, n / 2.0))
    xi = np.clip(np.round(_n(x, w)).astype(int), 0, w - 1)
    yi = np.clip(np.round(_n(y, h)).astype(int), 0, h - 1)
    if z is not None and np.asarray(z).size == p.shape[0]:
        zz = np.asarray(z, np.float64)
        lo, hi = float(zz.min()), float(zz.max())
        val = 0.3 + 0.7 * ((zz - lo) / (hi - lo) if hi - lo > 1e-12 else 0.5)
    else:
        val = np.full(p.shape[0], 0.9)
    plate[yi, xi] = np.stack([val * 0.35, val, val * 0.85], axis=1)
    return plate


def _panel_for(value, sort: str, base) -> np.ndarray:
    """sort に応じて「絵」にする。sort が分からない・絵にならないなら None。

    2026-09-07: 新設 sort(points / signal / video / …)の出力を `array(4096, 3)`
    と書いた札にしていたが、それでは op が何をしたか伝わらない(ユーザー指摘
    「意味が伝わる事が大事」)。sort ごとに素直な見せ方を決める。
    """
    a = value
    if isinstance(a, np.ndarray):
        if sort in ("points",) and a.ndim == 2 and a.shape[1] >= 2:
            return _scatter(base.shape, a[:, :2], a[:, 2] if a.shape[1] >= 3 else None)
        if sort == "keypoints" and a.ndim == 2 and a.shape[1] == 2:
            import fullseye as fs
            return np.asarray(fs.draw_markers(_panel(base), a, color=(1.0, 0.3, 0.1), size=3))
        if sort in ("signal", "counts") and a.ndim == 1:
            return _line_plot(base.shape, a)
        if sort == "cimage" and a.ndim == 2:
            return _panel(np.abs(a))
        if sort == "beatcube" and a.ndim == 3:
            return _panel(np.abs(a[0]))
        if sort == "video" and a.ndim == 3:
            return _panel(a[a.shape[0] // 2])           # 中央フレーム
        if sort == "volume" and a.ndim == 3:
            return _panel(a.max(axis=0))                # z 方向の MIP
        if sort == "lightfield" and a.ndim == 4:
            return _panel(a[a.shape[0] // 2, a.shape[1] // 2])   # 中央視点
        if sort == "qimage" and a.ndim == 3 and a.shape[-1] == 4:
            return _panel(a[..., 1:4])                  # ベクトル部 (i, j, k) を RGB に
        if sort == "matrix" and a.ndim == 2:
            return _panel(a)
        if a.dtype.kind == "c":
            return _panel(np.abs(a))
    return None


def _render(base, before, after, op) -> np.ndarray:
    """入力と出力を横に並べた 1 枚。

    左は**画素の画像**(前置きの結果が contour のような非画像なら元画像)。
    右は出力が絵ならそれ、そうでなければ値を書いた札。
    """
    import fullseye as fs

    left = _panel_for(before, op.in_sort, base)
    if left is None:
        left = _panel(before if _is_image(before) else base)
    left = _upscale(np.asarray(left, np.float64))
    out_sort = op.in_sort if op.out_sort == "any" else op.out_sort
    right = _panel_for(after, out_sort, base)
    if right is not None:
        pass
    elif _is_image(after):
        right = _panel(after)
    elif isinstance(after, dict) and "cs" in after:
        # contour(XLD)は**元画像に重ね描き**する。`cs=[array(…` と書いた札では
        # 何をする op か伝わらない(ユーザー指摘「意味が伝わる事が大事」)。
        # `draw_contour` は輪郭を**閉じて**描くので、`find_contours` の開いた
        # 輪郭に始点へ戻る線が足され、図が赤い線で埋まった(2026-09-06 実測)。
        # 1 本ずつ**開いた折れ線**で描く。
        right = left.copy()
        for c in list(after["cs"])[:200]:
            c = np.asarray(c, np.float64)
            if c.ndim == 2 and len(c) >= 2:
                # XLD は (row, col)、draw_polyline は (x, y) = (col, row)。
                # 入れ替えないと図が斜めの赤い筋で埋まる(2026-09-06 実測)。
                right = np.asarray(fs.draw_polyline(right, c[:, ::-1], color=(1.0, 0.25, 0.1),
                                                    width=1, closed=False))
    else:
        right = _plate(left.shape, after)
    right = _upscale(np.asarray(right, np.float64))
    caption = "out"
    rng_ = float(np.ptp(np.asarray(right, np.float64)))
    if 0.0 < rng_ < STRETCH_BELOW:
        r = np.asarray(right, np.float64)
        right = (r - r.min()) / rng_
        caption = "out (stretched)"
    if _wants_pseudocolor(op) and _is_image(after) and np.asarray(after).ndim == 2:
        r = np.asarray(right, np.float64)
        right = _pseudocolor(r[..., 0] if r.ndim == 3 else r)
        caption = caption.replace("out", "out (viridis)")
    # op 名は**題**に(全幅に置ける)。キャプションに入れると 124 px に収まらない
    # 名前が 36 本あって描画で落ちる —— op は走っているのに。
    return np.asarray(fs.annotate_figure_grid(
        [left, right], captions=["in", caption], ncols=2,
        title=op.name if len(op.name) <= 26 else op.name[:25] + "…"))


def _panel_of(value, sort, base):
    """どんな返り値も (h, w, 3) の絵にする(主図・段階図・複数入力で共通)。"""
    import fullseye as fs

    p = _panel_for(value, sort, base)
    if p is None:
        if _is_image(value):
            p = _panel(value)
        elif isinstance(value, dict) and "cs" in value:
            p = _panel(base)
            for c in list(value["cs"])[:200]:
                c = np.asarray(c, np.float64)
                if c.ndim == 2 and len(c) >= 2:
                    p = np.asarray(fs.draw_polyline(p, c[:, ::-1], color=(1.0, 0.25, 0.1),
                                                    width=1, closed=False))
        else:
            p = _plate(base.shape, value)
    p = np.asarray(p, np.float64)
    if p.ndim == 2:
        p = np.stack([p, p, p], axis=-1)
    return _upscale(p)


def _upscale(p: np.ndarray, target: int = 96) -> np.ndarray:
    """小さい絵(EGI 36 px、体積 16 px …)は最近傍で整数倍に拡大する。

    キャプション `(a) a=0.1` が 36 px に入らず描画で落ちた(2026-09-07 実測 4 本)。
    画素を作らない拡大なので値は変わらない。
    """
    h, w = p.shape[:2]
    m = min(h, w)
    if m >= target or m == 0:
        return p
    f = int(np.ceil(target / m))
    return np.repeat(np.repeat(p, f, axis=0), f, axis=1)


def _small(rgb: np.ndarray, n: int = SWEEP_SIZE) -> np.ndarray:
    """縮小(平均プール)。3 枚組の 1 枚を軽くする。"""
    rgb = np.asarray(rgb, np.float64)
    if rgb.ndim == 2:
        rgb = np.stack([rgb, rgb, rgb], axis=-1)
    h, w = rgb.shape[:2]
    if h <= n and w <= n:
        return rgb
    fy, fx = max(1, h // n), max(1, w // n)
    hh, ww = (h // fy) * fy, (w // fx) * fx
    return rgb[:hh, :ww].reshape(hh // fy, fy, ww // fx, fx, -1).mean(axis=(1, 3))


def _sweep(base, pre_value, op, knob: str):
    """つまみを SWEEP に振った 3 枚。全部同じなら None(= そのつまみは効かない)。"""
    import fullseye as fs

    ka, kb = _knobs(op)
    outs = []
    for t in SWEEP:
        a, b = (t, kb) if knob == "a" else (ka, t)
        outs.append(fs.apply(pre_value, op.name, a, b, on_error="raise"))
    same = all(_same(outs[0], o) for o in outs[1:])
    if same:
        return None
    out_sort = op.in_sort if op.out_sort == "any" else op.out_sort
    panels = []
    for o in outs:
        pnl = _panel_of(o, out_sort, base)
        if _wants_pseudocolor(op) and _is_image(o) and np.asarray(o).ndim == 2:
            pnl = _pseudocolor(pnl[..., 0])
        panels.append(_small(pnl))
    return np.asarray(fs.annotate_figure_grid(
        panels, captions=["%s=%.1f" % (knob, t) for t in SWEEP], ncols=3,
        title=(op.name if len(op.name) <= 26 else op.name[:25] + "…")))


def _same(x, y) -> bool:
    try:
        if isinstance(x, dict) or isinstance(y, dict):
            return repr(x) == repr(y)
        return np.array_equal(np.asarray(x), np.asarray(y))
    except Exception:                                    # noqa: BLE001
        return False


def _chain_figure(base, pre, op, out):
    """前置き op がある op の段階図: 画像 → 各前置きの出力 → この op の出力。"""
    import fullseye as fs
    import ops as OPS

    panels, caps, v, sort = [_small(_panel(base))], ["in"], base, "image"
    for nm, ka, kb in pre:
        v = fs.apply(v, nm, ka, kb, on_error="raise")
        o = OPS._BY_NAME[nm]
        sort = sort if o.out_sort == "any" else o.out_sort
        panels.append(_small(_panel_of(v, sort, base)))
        caps.append("step %d" % len(caps))            # op 名は 64 px に収まらない。鎖はノートの program 欄
    out_sort = op.in_sort if op.out_sort == "any" else op.out_sort
    panels.append(_small(_panel_of(out, out_sort, base)))
    caps.append("out")
    return np.asarray(fs.annotate_figure_grid(
        panels, captions=caps, ncols=len(panels),
        title=(op.name if len(op.name) <= 26 else op.name[:25] + "…")))


def _gif_frames(value, sort: str):
    """動画 / ライトフィールド / 体積を、フレーム / 視点 / スライスの列にする。"""
    a = np.asarray(value)
    if sort == "video" and a.ndim == 3:
        idx = np.linspace(0, a.shape[0] - 1, min(GIF_FRAMES, a.shape[0])).astype(int)
        return [a[i] for i in idx]
    if sort == "lightfield" and a.ndim == 4:
        vc = a.shape[0] // 2
        return [a[vc, u] for u in range(a.shape[1])]
    if sort == "volume" and a.ndim == 3:
        idx = np.linspace(0, a.shape[0] - 1, min(GIF_FRAMES, a.shape[0])).astype(int)
        return [a[i] for i in idx]
    return None


def _save_gif(path: str, frames) -> None:
    from PIL import Image

    ims = []
    for f in frames:
        u8 = (np.clip(_panel(f), 0, 1) * 255).astype(np.uint8)
        ims.append(Image.fromarray(u8, "RGB").quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=0))
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=250, loop=0, optimize=True)


def _inputs():
    """複数の入力画像(合成 / 写真 / 硬貨)。skimage.data(BSD)が無ければ合成の変種。

    ユーザー指示(2026-09-07)「高品質を求められるものは、いくつかの画像を試した結果が
    有っても良い」。合成 1 枚では平滑・エッジ・分割・特徴の良し悪しは判断できない。
    """
    global _INPUTS
    if _INPUTS is not None:
        return _INPUTS
    out = [("scene", canonical_image())]
    try:
        from skimage import data as _d
        cam = np.asarray(_d.camera(), np.float64) / 255.0
        coins = np.asarray(_d.coins(), np.float64) / 255.0
        out.append(("photo", _block_mean(cam, SIZE)))
        out.append(("coins", _block_mean(coins[40:296, 64:320], SIZE)))
        # 画像生成 AI で作った産業寄りの被写体(tools/gen_ai_inputs.py、来歴は
        # docs/ops/_fig/inputs/PROVENANCE.json)。載っているものだけ使う。
        out += _ai_inputs()
        # カラー(ユーザー指示 2026-09-07「モノクロとカラーの両方に対応している op もある」)。
        # 色を跨ぐ 89 op(api._CHANNEL_UNSAFE_OPS、KNOWN_ISSUES §34)には掛けない。
        ast = np.asarray(_d.astronaut(), np.float64) / 255.0
        out.append(("color", np.stack([_block_mean(ast[..., c], SIZE) for c in range(3)], axis=-1)))
    except Exception:                                    # noqa: BLE001 - optional
        rng = np.random.default_rng(7)
        yy, xx = np.mgrid[0:SIZE, 0:SIZE] / SIZE
        out.append(("stripes", 0.5 + 0.4 * np.sin(2 * np.pi * (6 * xx + 3 * yy))))
        out.append(("noise", np.clip(canonical_image() + rng.normal(0, 0.1, (SIZE, SIZE)), 0, 1)))
    _INPUTS = out
    return out


_INPUTS = None


def _ai_inputs():
    """``docs/ops/_fig/inputs/PROVENANCE.json`` に載る生成画像(グレー)を 128 に縮めて返す。"""
    pj = os.path.join(FIG_DIR, "inputs", "PROVENANCE.json")
    if not os.path.exists(pj):
        return []
    from PIL import Image
    with open(pj, encoding="utf-8") as f:
        prov = json.load(f)
    out = []
    for name in sorted(prov):
        p = os.path.join(FIG_DIR, "inputs", prov[name]["gray"])
        if not os.path.exists(p):
            continue
        g = np.asarray(Image.open(p).convert("L"), np.float64) / 255.0
        out.append((name, _block_mean(g, SIZE)))
    return out


def _color_safe(op) -> bool:
    """カラー (H,W,3) を渡してよい op か。色を跨ぐ op(§34)は除く。"""
    try:
        import api as _api
        return op.name not in _api._CHANNEL_UNSAFE_OPS
    except Exception:                                    # noqa: BLE001
        return False


def _block_mean(img: np.ndarray, n: int) -> np.ndarray:
    """(H,W) → (n,n) の平均プール(決定的・依存なし)。端数は切り捨て。"""
    h, w = img.shape
    fy, fx = max(1, h // n), max(1, w // n)
    sub = img[:fy * n, :fx * n].reshape(n, fy, n, fx).mean(axis=(1, 3))
    return np.clip(sub, 0, 1)


def _inputs_figure(pre, op):
    """入力 3 枚に同じ鎖を掛けた 2 段 × 3 列(上 = 入力、下 = 出力)。1 枚でも落ちたら None。"""
    import fullseye as fs

    ka, kb = _knobs(op)
    out_sort = op.in_sort if op.out_sort == "any" else op.out_sort
    if out_sort in ("feature", "match"):
        return None                                   # 札が 6 枚並ぶだけで意味が無い
    tops, bots, caps = [], [], []
    for name, img in _inputs():
        if img.ndim == 3:
            # カラーは「画像を直接受ける op で、色を跨がないもの」だけ。落ちたら黙って外す
            # (カラー非対応は欠陥ではなく契約。manifest の color_ok に記録する)
            if pre or op.in_sort not in ("image", "any") or not _color_safe(op):
                continue
            try:
                out = fs.apply(img, op.name, ka, kb, on_error="raise")
            except Exception:                            # noqa: BLE001
                continue
            if not (isinstance(out, np.ndarray) and out.size) or not np.isfinite(np.asarray(out, np.float64)).all():
                continue
        else:
            v = img
            try:
                for nm, a_, b_ in pre:
                    v = fs.apply(v, nm, a_, b_, on_error="raise")
                out = fs.apply(v, op.name, ka, kb, on_error="raise")
            except Exception:                            # noqa: BLE001
                return None
            if isinstance(out, np.ndarray) and out.size == 0:
                return None
        pnl = _panel_of(out, out_sort, img)
        if _wants_pseudocolor(op) and _is_image(out) and np.asarray(out).ndim == 2:
            pnl = _pseudocolor(pnl[..., 0])
        tops.append(_small(_panel(img)))
        bots.append(_small(pnl))
        caps.append("in: " + name)
    return np.asarray(fs.annotate_figure_grid(
        tops + bots, captions=caps + ["out"] * len(bots), ncols=len(tops),
        title=(op.name if len(op.name) <= 26 else op.name[:25] + "…")))


def _panel(v) -> np.ndarray:
    """(H,W) は**グレーのまま**、(H,W,3) はそのまま。float [0,1] RGB を返す。

    `examplefig._to_rgb8` は 2-D を viridis で塗るが、平滑・形態学のようなグレー
    → グレーの op に色を付けると「色が変わる op」に見えて誤解を招く。
    値域は [0,1] を超えるときだけ min-max で伸ばす(勝手に伸ばすと弱い効果が
    「強く見える」)。bool は 0/1。
    """
    a = np.asarray(v)
    if a.dtype == np.bool_:
        a = a.astype(np.float64)
    a = np.nan_to_num(np.asarray(a, np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    if a.ndim == 3:
        a = a[..., :3]
    lo, hi = float(a.min()), float(a.max())
    if hi > 1.0 or lo < 0.0:
        a = (a - lo) / (hi - lo) if hi - lo > 1e-12 else np.zeros_like(a)
    a = np.clip(a, 0, 1)
    if a.ndim == 2:
        a = np.stack([a, a, a], axis=-1)
    return a


def _save_jpeg(path: str, rgb01: np.ndarray) -> None:
    """複数パネルの図は JPEG(品質 85)。128 px を保ったまま 1 枚 10〜25 KB。"""
    from PIL import Image

    u8 = (np.clip(rgb01, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(u8, "RGB").save(path, "JPEG", quality=JPEG_QUALITY, optimize=True)


def _save_small(path: str, rgb01: np.ndarray) -> None:
    """可逆 PNG で等倍保存(主図。wheel に同梱する側)。"""
    from PIL import Image

    u8 = (np.clip(rgb01, 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(u8, "RGB")
    # 2026-09-07 まで 32 色パレットに落としていた(1 枚 5 KB)。ユーザー指示
    # 「極力は高品質な部分を見せたい」で **可逆・等倍** に(1 枚 15〜40 KB、
    # 892 枚で 20 MB 強。wheel は 100 MB の内側)。疑似カラーや写真は 32 色では
    # 階調が壊れる。
    im.save(path, optimize=True)


def _short(v, n: int = 40) -> str:
    if isinstance(v, (float, np.floating)):
        return "%.4g" % v
    if isinstance(v, np.ndarray):
        return "array%s" % (v.shape,)
    s = str(v)
    return s if len(s) <= n else s[:n - 1] + "…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=FIG_DIR)
    a = ap.parse_args()

    import fullseye as fs
    import ops as OPS

    os.makedirs(a.out, exist_ok=True)
    base = canonical_image()
    rows, stats = {}, {"ok": 0, "unreachable": 0, "failed": 0, "domain": 0, "empty": 0}
    t0 = time.time()
    todo = list(OPS.REGISTRY)[: a.limit or None]
    for op in todo:
        pre = PREFIX_OP.get(op.name, PREFIX.get(op.in_sort))
        if op.name in DOMAIN_MISMATCH:
            rows[op.name] = {"status": "domain", "in_sort": op.in_sort,
                             "reason": DOMAIN_MISMATCH[op.name]}
            stats["domain"] += 1
            continue
        if pre is None:
            rows[op.name] = {"status": "unreachable", "in_sort": op.in_sort,
                             "reason": "画像から `%s` を作る登録 op が無い"
                                       % op.in_sort}
            stats["unreachable"] += 1
            continue
        try:
            v = base
            for nm, ka, kb in pre:
                v = fs.apply(v, nm, ka, kb, on_error="raise")
            before = v
            ka, kb = _knobs(op)
            out = fs.apply(v, op.name, ka, kb, on_error="raise")
            if isinstance(out, np.ndarray) and out.size == 0:
                # ★「走った」と「意味のある出力が出た」は別(2026-09-07、ユーザー
                # 指摘「out が真っ黒なのはなんだ?」)。空配列を「図あり」に数えると
                # 黒い板が図になる。空は空と記録し、ノートに理由を書く。
                rows[op.name] = {"status": "empty", "in_sort": op.in_sort,
                                 "program": _program(op, pre),
                                 "reason": "走ったが返り値が空(合成入力ではこの op の答えが無い)"}
                stats["empty"] += 1
                continue
            fig = _render(base, before, out, op)
            rel = "%s.png" % op.name
            _save_small(os.path.join(a.out, rel), np.asarray(fig))
            row = {"status": "ok", "fig": rel, "program": _program(op, pre),
                   "out_kind": type(out).__name__, "pseudocolor": _wants_pseudocolor(op),
                   "extra": {}, "knob_dead": []}
            # つまみの段階図(効くときだけ)
            for knob in ("a", "b"):
                sw = _sweep(base, before, op, knob)
                if sw is None:
                    row["knob_dead"].append(knob)
                else:
                    rel_k = "%s.%s.jpg" % (op.name, knob)
                    _save_jpeg(os.path.join(a.out, rel_k), sw)
                    row["extra"][knob] = rel_k
            # 前置きのある op は段階図
            if pre:
                rel_c = "%s.chain.jpg" % op.name
                _save_jpeg(os.path.join(a.out, rel_c), _chain_figure(base, pre, op, out))
                row["extra"]["chain"] = rel_c
            # 複数の入力画像(合成 / 写真 / 硬貨)
            fig_in = _inputs_figure(pre, op)
            if fig_in is not None:
                rel_i = "%s.inputs.jpg" % op.name
                _save_jpeg(os.path.join(a.out, rel_i), fig_in)
                row["extra"]["inputs"] = rel_i
                row["inputs"] = [nm for nm, _ in _inputs()]
                row["color_ok"] = (not pre and op.in_sort in ("image", "any") and _color_safe(op))
            # 動くもの
            out_sort = op.in_sort if op.out_sort == "any" else op.out_sort
            frames = _gif_frames(out, out_sort) if out_sort in GIF_SORTS else None
            if frames and len(frames) > 1:
                rel_g = "%s.gif" % op.name
                _save_gif(os.path.join(a.out, rel_g), frames)
                row["extra"]["gif"] = rel_g
            rows[op.name] = row
            stats["ok"] += 1
        except Exception as exc:                        # noqa: BLE001
            rows[op.name] = {"status": "failed", "in_sort": op.in_sort,
                             "reason": "%s: %s" % (type(exc).__name__,
                                                   str(exc)[:160])}
            stats["failed"] += 1

    n_sw = sum(1 for r in rows.values() if r.get("extra", {}).get("a") or r.get("extra", {}).get("b"))
    n_gif = sum(1 for r in rows.values() if r.get("extra", {}).get("gif"))
    n_ch = sum(1 for r in rows.values() if r.get("extra", {}).get("chain"))
    stats.update({"with_sweep": n_sw, "with_gif": n_gif, "with_chain": n_ch})
    out = {"generated_for": len(todo), "size": SIZE, "stats": stats, "ops": rows}
    with open(os.path.join(a.out, "figures.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("[figures] %d op: 図あり %d / 型が届かない %d / 定義域が合わない %d / 空を返した %d / 落ちた %d  (%.1f 秒)"
          % (len(todo), stats["ok"], stats["unreachable"], stats["domain"],
             stats["empty"], stats["failed"], time.time() - t0))
    if stats["failed"]:
        bad = [k for k, v in rows.items() if v["status"] == "failed"][:8]
        print("  落ちた例:", bad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
