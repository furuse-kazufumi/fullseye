# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wingastro_gallery — Qiita 記事「紙面の科学館」の **天体写真スタッキング
ウィング** を生成する.
Generate the "astronomical stacking wing" exhibits for the museum article.

方針 (honest disclosure) / policy
---------------------------------
* 画像はすべて **``astrostack`` の op を実際に実行した結果**。モックアップは
  1 枚も無い。図に焼き込む数値は **その場で計算した実測値**のみ(創作禁止)。
* 素材は ``astrostack.synth_starfield`` / ``synth_frame_series`` が作る**合成
  星野**で、星の座標もフラックスも既知。実写の天体画像は 1 枚も使っていない
  (キャプションにも明記する)。ノイズは ``photoncount.photon_sample`` の
  Poisson + 加法ガウス、宇宙線の位置は ``defectgen.defect_pits`` の点過程。
* 描画は numpy 合成と ``imagedraw`` op。**matplotlib は使わない**。文字だけは
  Fullseye にテキスト op が無いため PIL で焼く(``gen_wingct_gallery.py`` と
  同じ流儀)。
* **配色は自分で選ばない。** ``palette`` の役割(``fs.role_rgb8("right")`` 等)
  で引く。赤緑の対は使わない。
* 版面は ``tools/exhibit_tile.py`` の判断基準に従う。**同じ寸法で工程が進む
  もの**は ``flipbook`` の GIF、**並べて比べるもの**は ``contact_sheet``、
  **図中の数値が主役のもの**は原寸 1 枚。
* 乱数はすべて seed 固定(``SEED`` とその派生)。同じコマンドで再生成すると
  PNG / GIF の SHA-256 が一致する(``--verify`` で機械確認できる)。

このウィングが見せたいこと / what this wing is for
--------------------------------------------------
天体写真スタッキングは、画像処理の中では珍しく **答えが閉じた形で書ける**。
だからこのウィングの展示はどれも「きれいになった」ではなく **「理論値と何桁
合ったか / どこで理論どおりに壊れたか」** を絵にしている。とくに σ クリップの
破綻は、**バグではなく中央値の定義そのもの**が 50 % で折れることの絵であって、
これが本ウィングの主展示。

出力 / outputs
--------------
``docs/articles/assets/wingastro_<name>.png``               静止展示(フル解像度)
``docs/articles/assets/wingastro_<name>_thumb.jpg``         サムネ
``docs/articles/assets/media/wingastro_<name>.gif``         動く展示
``docs/articles/assets/thumbs/wingastro_<name>_thumb.jpg``  動く展示のサムネ
``docs/articles/exhibits/wingastro.ja.md`` / ``wingastro.en.md``  キャプション(2 言語)
``docs/articles/assets/_wingastro_meta.json``               使用 op・実測値・ファイル情報

使い方 / run
------------
    py -3.11 tools/gen_wingastro_gallery.py                     # 全展示
    py -3.11 tools/gen_wingastro_gallery.py --list              # 展示名の一覧
    py -3.11 tools/gen_wingastro_gallery.py --exhibits drizzle  # 一部だけ
    py -3.11 tools/gen_wingastro_gallery.py --verify            # 再生成して SHA-256 照合
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import astrostack as A                                    # noqa: E402
import fullseye as fs                                     # noqa: E402
import imagedraw                                          # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exhibit_tile as et                                 # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_PATH = os.path.join(ROOT, "docs", "articles", "assets",
                         "_wingastro_meta.json")
EXHIBITS_DIR = os.path.join(ROOT, "docs", "articles", "exhibits")

SEED = 20260902                  # 星野の抽選(field_seed)
PANEL = 440                      # 各パネルの一辺(画素)

#: 役割で引いた色(自分で選ばない)。赤緑の対は palette 側が拒否する。
C_RIGHT = fs.role_rgb8("right")            # (86, 180, 233)  正しい / 保たれた
C_WRONG = fs.role_rgb8("wrong")            # (213, 94, 0)    壊れた / 失われた
C_EMPH = fs.role_rgb8("emphasis")          # (230, 159, 0)   注目
C_REF = fs.role_rgb8("reference")          # (0, 114, 178)   基準
C_NEUTRAL = fs.role_rgb8("neutral")        # (158, 158, 168)
M = fs.ROLE_MARKERS                        # 色だけに意味を載せないための記号


# --------------------------------------------------------------------------- #
# 描画ヘルパ(matplotlib なし)                                                #
# --------------------------------------------------------------------------- #
def _norm(a, lo=None, hi=None):
    a = np.asarray(a, np.float64)
    lo = float(a.min()) if lo is None else float(lo)
    hi = float(a.max()) if hi is None else float(hi)
    if hi <= lo:
        return np.zeros_like(a)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def _stretch(a, frame_for_scale=None, low=25.0, high=99.7, gamma=0.45):
    """天体画像の見せ方: パーセンタイルで切ってガンマを掛ける。

    線形のまま出すと、最も明るい星以外は真っ黒になって**何も見えない**
    (点検スクリプトの「実質単色」に引っかかる典型)。切り位置は
    *frame_for_scale* から取れるので、比較する 2 枚を**同じ尺度**で塗れる。
    """
    ref = a if frame_for_scale is None else frame_for_scale
    lo, hi = np.percentile(np.asarray(ref, np.float64), [low, high])
    return _norm(a, lo, hi) ** gamma


def _gray(a, **kw):
    """グレイ画像 -> (H, W, 3) float [0,1]。着色のみで、処理はしない。"""
    g = _stretch(a, **kw)
    return np.repeat(g[..., None], 3, axis=2)


def _tint(a, rgb8, **kw):
    """単色で塗る(役割色を渡す)。"""
    g = _stretch(a, **kw)
    c = np.asarray(rgb8, np.float64) / 255.0
    return g[..., None] * c[None, None, :]


def _signed(a, limit):
    """符号つきの量を ``palette`` の発散 LUT で塗る(wrong <- 暗 -> right)。"""
    lut = fs.diverging_lut(256)
    t = np.clip((np.asarray(a, np.float64) / (2.0 * limit)) + 0.5, 0.0, 1.0)
    idx = np.clip((t * 255.0).astype(np.int64), 0, 255)
    return lut[idx]


def _fit(rgb, side=PANEL):
    """(H, W, 3) を一辺 *side* の正方形へ**最近傍**で拡大縮小する。

    決定的で、補間による「無い解像度」を作らない。フリップブックは寸法が
    揃っていないと例外になるので、すべてここを通す。
    """
    h, w = rgb.shape[:2]
    yi = np.minimum((np.arange(side) * h // side), h - 1)
    xi = np.minimum((np.arange(side) * w // side), w - 1)
    return rgb[yi][:, xi]


def _label(rgb, lines, corner="tl", size=17, color=None):
    """パネル上に実測値を焼く。凡例が無いと止まった 1 コマが意味を失う。"""
    from PIL import Image, ImageDraw
    im = Image.fromarray(et._to_u8(rgb), "RGB")
    dr = ImageDraw.Draw(im, "RGBA")
    font = et._font(size)
    pad, lh = 7, size + 5
    box_h = lh * len(lines) + pad
    wmax = max(dr.textlength(t, font=font) for t in lines) + 2 * pad
    x0 = pad if corner[1] == "l" else im.width - wmax - pad
    y0 = pad if corner[0] == "t" else im.height - box_h - pad
    dr.rectangle([x0, y0, x0 + wmax, y0 + box_h], fill=(8, 8, 14, 205))
    for i, t in enumerate(lines):
        dr.text((x0 + pad, y0 + pad // 2 + i * lh), t,
                fill=(color or et.FG), font=font)
    return np.asarray(im, np.float64) / 255.0


class Plot:
    """軸ラベルつきの折れ線図を 1 枚作る最小の道具(matplotlib なし)。

    ``imagedraw`` の線 op で枠と曲線を描き、文字だけ最後に PIL で焼く
    (Fullseye にテキスト op が無いため)。
    """

    def __init__(self, w=PANEL, h=PANEL, xlim=(0.0, 1.0), ylim=(0.0, 1.0),
                 xlog=False, ylog=False, margin=(62, 18, 46, 16)):
        self.w, self.h = int(w), int(h)
        self.ml, self.mr, self.mb, self.mt = margin
        self.xlog, self.ylog = bool(xlog), bool(ylog)
        self.xlim = tuple(np.log10(v) for v in xlim) if xlog else tuple(xlim)
        self.ylim = tuple(np.log10(v) for v in ylim) if ylog else tuple(ylim)
        self.rgb = np.zeros((self.h, self.w, 3), np.float64)
        self.rgb[:] = np.asarray(et.BG, np.float64) / 255.0
        self._text = []
        self._frame()

    def _px(self, x):
        x = np.log10(x) if self.xlog else x
        t = (np.asarray(x, float) - self.xlim[0]) / (self.xlim[1] - self.xlim[0])
        return self.ml + t * (self.w - self.ml - self.mr)

    def _py(self, y):
        y = np.log10(y) if self.ylog else y
        t = (np.asarray(y, float) - self.ylim[0]) / (self.ylim[1] - self.ylim[0])
        return self.h - self.mb - t * (self.h - self.mb - self.mt)

    def _stroke(self, pts, rgb8, width=2, closed=False):
        stencil = np.zeros((self.h, self.w), np.float64)
        stencil = imagedraw.draw_polyline(stencil, pts, color=1.0, width=width,
                                          closed=closed)
        c = np.asarray(rgb8, np.float64) / 255.0
        self.rgb = self.rgb * (1.0 - stencil[..., None]) \
            + stencil[..., None] * c[None, None, :]

    def _frame(self):
        x0, x1 = float(self._px(self.xlim[0] if not self.xlog
                                else 10 ** self.xlim[0])), \
            float(self._px(self.xlim[1] if not self.xlog
                           else 10 ** self.xlim[1]))
        y0, y1 = self.h - self.mb, self.mt
        self._stroke([(x0, y1), (x1, y1), (x1, y0), (x0, y0)], (70, 72, 92),
                     width=1, closed=True)

    def grid_y(self, values, fmt="%.2f"):
        for v in values:
            y = float(self._py(v))
            self._stroke([(self.ml, y), (self.w - self.mr, y)], (44, 46, 60),
                         width=1)
            self._text.append((self.ml - 8, y, fmt % v, et.MUTED, 14, "rm"))

    def grid_x(self, values, fmt="%g"):
        for v in values:
            x = float(self._px(v))
            self._stroke([(x, self.mt), (x, self.h - self.mb)], (44, 46, 60),
                         width=1)
            self._text.append((x, self.h - self.mb + 6, fmt % v, et.MUTED, 14,
                               "ma"))

    def line(self, xs, ys, rgb8, width=2, dashed=False):
        px = [float(v) for v in np.atleast_1d(self._px(np.asarray(xs, float)))]
        py = [float(v) for v in np.atleast_1d(self._py(np.asarray(ys, float)))]
        pts = list(zip(px, py))
        if dashed:
            for i in range(0, len(pts) - 1, 2):
                self._stroke(pts[i:i + 2], rgb8, width=width)
        else:
            self._stroke(pts, rgb8, width=width)

    def markers(self, xs, ys, rgb8, size=5):
        px = np.atleast_1d(self._px(np.asarray(xs, float)))
        py = np.atleast_1d(self._py(np.asarray(ys, float)))
        stencil = np.zeros((self.h, self.w), np.float64)
        stencil = imagedraw.draw_markers(
            stencil, [(float(a), float(b)) for a, b in zip(px, py)],
            color=1.0, size=size, shape="cross", width=2)
        c = np.asarray(rgb8, np.float64) / 255.0
        self.rgb = self.rgb * (1.0 - stencil[..., None]) \
            + stencil[..., None] * c[None, None, :]

    def vline(self, x, rgb8, width=2, dashed=True):
        xp = float(self._px(x))
        ys = np.linspace(self.mt, self.h - self.mb, 24)
        step = 2 if dashed else 1
        for i in range(0, len(ys) - 1, step):
            self._stroke([(xp, float(ys[i])), (xp, float(ys[i + 1]))], rgb8,
                         width=width)

    def text(self, x, y, s, rgb8=None, size=15, anchor="la", data=False):
        if data:
            x, y = float(self._px(x)), float(self._py(y))
        self._text.append((x, y, s, rgb8 or et.FG, size, anchor))

    def done(self):
        from PIL import Image, ImageDraw
        im = Image.fromarray(et._to_u8(self.rgb), "RGB")
        dr = ImageDraw.Draw(im)
        for x, y, s, col, size, anchor in self._text:
            dr.text((x, y), s, fill=tuple(int(v) for v in col),
                    font=et._font(size), anchor=anchor)
        return np.asarray(im, np.float64) / 255.0


def _fwhm_of(image, **kw):
    """検出星の FWHM 中央値(``frame_quality`` の 1 数字)。"""
    return float(A.frame_quality(image, **kw)["fwhm_px"])


def _science(sci, wht):
    """drizzle の**見る側**の像 = ``sci / wht``(被覆で割る)。

    ``sci`` は総フラックスを保存するために「撒かれた量」を持っているので、
    被覆のむらがそのまま像に残る。``pixfrac`` を小さくするとそれは格子になり、
    生の ``sci`` に :func:`astrostack.star_detect` を掛けると**格子が星に化ける**
    —— 実測で ``scale=3`` / ``pixfrac=0.4`` の二重星に対し 200 個(検出上限)
    対 2 個。保存則と見た目は別の量で、片方をもう片方の代わりには使えない。
    """
    return np.where(wht > 1e-9, sci / np.maximum(wht, 1e-9), 0.0)


# --------------------------------------------------------------------------- #
# 展示 1: 重ねると雑音は sqrt(N) で減る(タイル + グラフ)                      #
# --------------------------------------------------------------------------- #
def ex_sqrt_n():
    """1 枚 vs N 枚。真値が分かっているので**残差そのもの**を測る。"""
    n_max = 64
    frames, truth = A.synth_frame_series(
        shape=(160, 160), n_frames=n_max, dither_px=0.0, n_stars=45,
        flux_min=600.0, flux_max=30000.0, fwhm_px=3.4, sky=200.0,
        read_sigma=8.0, seed=SEED, margin_px=10.0)
    ideal = truth["noiseless"]

    def rms(img):
        return float(np.sqrt(np.mean((np.asarray(img) - ideal) ** 2)))

    base = rms(frames[0])
    counts = [1, 2, 4, 8, 16, 32, 64]
    stacks, measured = {}, {}
    for n in counts:
        img = frames[0] if n == 1 else A.sigma_clip_stack(frames[:n],
                                                          mode="mean")[0]
        stacks[n] = img
        measured[n] = rms(img)

    panels, labels = [], []
    for n in (1, 16, 64):
        img = stacks[n]
        panels.append(_label(
            _fit(_gray(img, frame_for_scale=frames[0])),
            ["N = %d" % n,
             "残差 RMS %.3f e-" % measured[n],
             "%s 1 枚比 %.2f 倍" % (M["right"], base / measured[n])]))
        labels.append("%d 枚合成 — 残差 %.3f e-" % (n, measured[n]))

    # 測ったものと sqrt(N) を重ねた図(軸ラベルつき = 原寸で読ませる)。
    # 理論を太く下に、測定を細く上に描く —— 逆にすると完全に重なって
    # 「線が 1 本しか無い」ように見え、一致しているのか片方を描き忘れたのか
    # 読者に区別が付かない。
    worst = max(abs(base / measured[n] / np.sqrt(n) - 1.0) for n in counts)
    p = Plot(xlim=(1, 64), ylim=(0.9, 10.0), xlog=True, ylog=True,
             margin=(64, 20, 46, 74))
    p.grid_x(counts, "%d")
    p.grid_y([1, 2, 4, 8], "%dx")
    p.line(counts, [np.sqrt(n) for n in counts], C_REF, width=7)
    p.line(counts, [base / measured[n] for n in counts], C_EMPH, width=2)
    p.markers(counts, [base / measured[n] for n in counts], C_EMPH)
    p.text(PANEL // 2, 8, "雑音の下がり方(両対数)", size=17, anchor="ma")
    p.text(PANEL // 2, 32, "縦 = 1 枚に対する改善 / 横 = 枚数 N", et.MUTED, 13,
           anchor="ma")
    p.text(76, 92, "%s sqrt(N)(理論・太線)" % M["reference"], C_REF, 14)
    p.text(76, 112, "%s 測定(細線)" % M["emphasis"], C_EMPH, 14)
    p.text(76, 132, "ずれは最大 %.1f %%" % (100 * worst), et.FG, 14)
    panels.append(_fit(p.done()))
    labels.append("測定 vs sqrt(N)(両対数)")

    # 残差そのものを同じ尺度で 2 枚。雑音が減ったことを「絵の暗さ」で示す。
    lim = float(np.percentile(np.abs(frames[0] - ideal), 99.0))
    for n in (1, 64):
        panels.append(_label(
            _fit(_signed(stacks[n] - ideal, lim)),
            ["残差(真値との差)N = %d" % n,
             "同じ尺度 ±%.0f e- で塗ってある" % lim,
             "%s 減 / %s 増" % (M["wrong"], M["right"]),
             "RMS %.3f e-" % measured[n]]))
        labels.append("残差 N=%d(同じ尺度 ±%.0f e-)" % (n, lim))

    sheet = et.contact_sheet(panels, labels, ncols=3, panel_px=PANEL,
                             title="重ねると雑音は sqrt(N) で減る"
                                   "(合成星野なので残差を直接測れる)")
    info = et.save_exhibit(sheet, "wingastro_stack_sqrtn")
    data = {"base_rms": base, "rms": measured, "counts": counts,
            "max_dev_pct": 100 * worst,
            "ratio": {n: base / measured[n] for n in counts},
            "n_stars": int(truth["n_stars"]), "sky": truth["sky"],
            "read_sigma": truth["read_sigma"],
            "predicted_single": float(np.sqrt(truth["sky"]
                                              + truth["read_sigma"] ** 2))}
    return info, data


# --------------------------------------------------------------------------- #
# 展示 2: lucky imaging —— 品質順に並べる(タイル)                            #
# --------------------------------------------------------------------------- #
def _lucky_series(n_frames=16):
    return A.synth_frame_series(
        shape=(140, 140), n_frames=n_frames, dither_px=0.0, n_stars=26,
        flux_min=2500.0, flux_max=26000.0, fwhm_px=3.0, fwhm_jitter=1.1,
        sky=90.0, read_sigma=6.0, seed=SEED + 11, margin_px=12.0)


def ex_lucky_sheet():
    """品質点で並べ替えると、シーイングの良い順に並ぶ。"""
    frames, truth = _lucky_series()
    idx, scores = A.lucky_select(frames, keep_fraction=0.25)
    order = np.argsort(-scores, kind="stable")
    fwhms = np.array([_fwhm_of(f) for f in frames])
    keep = set(int(i) for i in idx)

    panels, labels = [], []
    for rank, i in enumerate(order[:8]):
        i = int(i)
        chosen = i in keep
        col = C_RIGHT if chosen else C_NEUTRAL
        panels.append(_label(
            _fit(_tint(frames[i], col, frame_for_scale=frames[int(order[0])])),
            ["%d 位  frame %d" % (rank + 1, i),
             "点 %.4f" % scores[i],
             "FWHM %.2f px" % fwhms[i],
             ("%s 採用" % M["right"]) if chosen else ("%s 不採用" % M["neutral"])],
            color=col))
        labels.append("%d 位 — 点 %.4f / FWHM %.2f px%s"
                      % (rank + 1, scores[i], fwhms[i],
                         "(採用)" if chosen else ""))

    corr = float(np.corrcoef(fwhms, scores)[0, 1])
    sheet = et.contact_sheet(
        panels, labels, ncols=4, panel_px=380,
        title="lucky imaging —— 16 枚を品質点の高い順に(上位 25 %% を採用、"
              "点と FWHM の相関 %.3f)" % corr)
    info = et.save_exhibit(sheet, "wingastro_lucky_sheet")
    data = {"scores": scores.tolist(), "fwhms": fwhms.tolist(),
            "kept": [int(i) for i in idx], "corr": corr,
            "n_frames": len(frames),
            "fwhm_best": float(fwhms[int(order[0])]),
            "fwhm_worst": float(fwhms[int(order[-1])])}
    return info, data


def ex_lucky_sweep():
    """上位何 % を採るか、を振る(GIF)。鋭さと雑音の取引がそのまま見える。"""
    frames, truth = _lucky_series()
    ideal = truth["noiseless"]
    fracs = [1.0, 0.75, 0.5, 0.25, 0.125]
    shots, labels, rows = [], [], []
    scores = A.lucky_select(frames, keep_fraction=1.0)[1]
    order = np.argsort(-scores, kind="stable")
    scale_ref = None
    for f in fracs:
        k = max(1, int(np.ceil(f * len(frames))))
        picked = [frames[int(i)] for i in order[:k]]
        stack = A.sigma_clip_stack(picked, mode="mean")[0] if k > 1 else picked[0]
        if scale_ref is None:
            scale_ref = stack
        fwhm = _fwhm_of(stack)
        rms = float(np.sqrt(np.mean((stack - ideal) ** 2)))
        rows.append({"fraction": f, "kept": k, "fwhm": fwhm, "rms": rms})
        shots.append(_label(
            _fit(_gray(stack, frame_for_scale=scale_ref), 520),
            ["上位 %d %%(%d / %d 枚)" % (round(100 * f), k, len(frames)),
             "%s FWHM %.3f px" % (M["right"], fwhm),
             "%s 残差 RMS %.3f e-" % (M["wrong"], rms)]))
        labels.append("上位 %d %% — FWHM %.3f px / 残差 %.3f"
                      % (round(100 * f), fwhm, rms))
    book = et.flipbook(shots, labels,
                       title="採る割合を絞ると像は鋭くなり、雑音は増える")
    info = et.save_animation(book, "wingastro_lucky_sweep", duration_ms=1100,
                             hold_last_ms=2200)
    data = {"rows": rows,
            "fwhm_gain_pct": 100 * (1 - rows[-1]["fwhm"] / rows[0]["fwhm"]),
            "rms_cost_x": rows[-1]["rms"] / rows[0]["rms"]}
    return info, data


# --------------------------------------------------------------------------- #
# 展示 3: 宇宙線の消え方(タイル)                                             #
# --------------------------------------------------------------------------- #
def ex_cosmic():
    """**「最大値」では語れない。** 宇宙線の無い同じ観測を作って差を測る。

    最初の版はフレームの最大値を並べていたが、それは**一番明るい星**の値で
    あって宇宙線とは関係が無く、除去の前後でほとんど動かなかった
    (実測 7120 -> 7119 e-)。``n_cosmic=0`` の同じ seed で「宇宙線だけ無い
    観測」を作れば、正解との差を直接測れる —— 合成データを使う利点はここ。
    """
    kw = dict(shape=(150, 150), n_stars=30, flux_min=1500.0, flux_max=30000.0,
              fwhm_px=3.2, sky=90.0, read_sigma=6.0, seed=SEED + 21,
              margin_px=10.0)
    frame, truth = A.synth_starfield(n_cosmic=18, cosmic_flux=7000.0, **kw)
    ideal_frame, _ = A.synth_starfield(n_cosmic=0, **kw)
    cleaned, mask = A.cosmic_ray_reject(frame, sigma=5.0, f_lim=2.0)
    hit = truth["cosmic_mask"]
    tp = int((mask & hit).sum())
    precision = tp / max(1, int(mask.sum()))
    recall = tp / max(1, int(hit.sum()))
    res_raw = float(np.abs(frame - ideal_frame).max())
    res_cleaned = float(np.abs(cleaned - ideal_frame).max())

    skw = dict(shape=(150, 150), n_frames=8, dither_px=0.0, n_stars=30,
               flux_min=1500.0, flux_max=30000.0, fwhm_px=3.2, sky=90.0,
               read_sigma=6.0, seed=SEED + 21, margin_px=10.0)
    series, _ = A.synth_frame_series(n_cosmic=12, cosmic_flux=7000.0, **skw)
    clean_series, _ = A.synth_frame_series(n_cosmic=0, **skw)
    ideal = A.sigma_clip_stack(clean_series, mode="mean")[0]
    cleaned_series, masks = A.cosmic_ray_reject_stack(series, kappa=5.0,
                                                      read_sigma=6.0)
    naive = A.sigma_clip_stack(series, mode="mean")[0]
    fixed = A.sigma_clip_stack(cleaned_series, mode="mean")[0]
    clipped = A.sigma_clip_stack(series, mode="sigma_clip", kappa=3.0)[0]
    e_naive = float(np.abs(naive - ideal).max())
    e_clip = float(np.abs(clipped - ideal).max())
    e_fixed = float(np.abs(fixed - ideal).max())
    n_before, n_after = len(A.star_detect(frame)), len(A.star_detect(cleaned))

    panels, labels = [], []
    panels.append(_label(_fit(_gray(frame)),
                         ["元のフレーム 150x150(合成)",
                          "植えた宇宙線 %d 画素" % int(hit.sum()),
                          "星 %d 個 / 空 %.0f e-" % (truth["n_stars"],
                                                     truth["sky"])]))
    labels.append("元(合成・宇宙線 %d 画素)" % int(hit.sum()))

    panels.append(_label(_fit(_tint(mask.astype(float), C_EMPH,
                                    frame_for_scale=np.array([[0.0, 1.0]]))),
                         ["検出マスク %d 画素" % int(mask.sum()),
                          "%s 適合率 %.3f" % (M["right"], precision),
                          "%s 再現率 %.3f" % (M["neutral"], recall),
                          "星の中心は 1 つも拾っていない"], color=C_EMPH))
    labels.append("検出マスク(適合率 %.3f)" % precision)

    panels.append(_label(_fit(_gray(cleaned, frame_for_scale=frame)),
                         ["除去後(同じ尺度)",
                          "正解との最大差 %.0f -> %.0f e-"
                          % (res_raw, res_cleaned),
                          "「星」の検出数 %d -> %d" % (n_before, n_after),
                          "減ったぶんは宇宙線が星に化けていた分"]))
    labels.append("単一フレーム除去のあと(最大差 %.0f e-)" % res_cleaned)

    panels.append(_label(_fit(_gray(naive)),
                         ["8 枚を素直に平均",
                          "%s 正解との最大差 %.0f e-" % (M["wrong"], e_naive),
                          "宇宙線は 1/8 に薄まって全部残る"]))
    labels.append("素直な平均 — 最大差 %.0f e-" % e_naive)

    panels.append(_label(_fit(_gray(clipped, frame_for_scale=naive)),
                         ["8 枚を κ-σ 合成(κ=3)",
                          "%s 正解との最大差 %.0f e-" % (M["right"], e_clip),
                          "検出も置換もしていない"]))
    labels.append("κ-σ 合成 — 最大差 %.0f e-" % e_clip)

    panels.append(_label(_fit(_gray(fixed, frame_for_scale=naive)),
                         ["フレーム間除去 -> 平均",
                          "%s 正解との最大差 %.0f e-" % (M["right"], e_fixed),
                          "同じ場所に二度は当たらない"]))
    labels.append("フレーム間比較で除去してから平均 — 最大差 %.0f e-" % e_fixed)

    sheet = et.contact_sheet(panels, labels, ncols=3, panel_px=PANEL,
                             title="宇宙線の消え方 —— 尖りで見分ける / "
                                   "枚数で見分ける")
    info = et.save_exhibit(sheet, "wingastro_cosmic")
    data = {"truth_px": int(hit.sum()), "detected_px": int(mask.sum()),
            "precision": precision, "recall": recall,
            "residual_raw": res_raw, "residual_cleaned": res_cleaned,
            "err_naive": e_naive, "err_clipped": e_clip, "err_fixed": e_fixed,
            "stack_detected_px": int(masks.sum()),
            "n_stars_before": n_before, "n_stars_after": n_after,
            "n_frames": 8}
    return info, data


# --------------------------------------------------------------------------- #
# 展示 4: drizzle —— 解像度が上がる過程と、保存されるフラックス(GIF)         #
# --------------------------------------------------------------------------- #
def _drizzle_series():
    return A.synth_frame_series(
        shape=(56, 56), n_frames=24, dither_px=1.5, n_stars=14,
        flux_min=6000.0, flux_max=26000.0, fwhm_px=1.15, sky=60.0,
        read_sigma=4.0, seed=SEED + 31, margin_px=9.0)


def ex_drizzle():
    """しずくを小さくすると像が立ち上がる。総和は最後まで動かない。"""
    frames, truth = _drizzle_series()
    want = float(np.mean([f.sum() for f in frames]))
    shots, labels, rows = [], [], []

    single = frames[0]
    ref = single
    shots.append(_label(_fit(_gray(single), 560),
                        ["1 枚だけ(56x56、FWHM 1.15 px = 標本化不足)",
                         "総フラックス %.1f e-" % single.sum(),
                         "測った FWHM %.3f px" % _fwhm_of(single,
                                                          threshold_sigma=4.0)]))
    labels.append("1 枚(標本化が足りていない)")

    naive = A.sigma_clip_stack(frames, mode="mean")[0]
    shots.append(_label(_fit(_gray(naive, frame_for_scale=ref), 560),
                        ["24 枚をそのまま平均(ずれを平均してしまう)",
                         "総フラックス %.1f e-" % naive.sum(),
                         "%s FWHM %.3f px(1 枚より鈍い)"
                         % (M["wrong"], _fwhm_of(naive, threshold_sigma=4.0))]))
    labels.append("そのまま平均 — ディザを平均すると鈍る")

    for pf in (1.0, 0.6, 0.3):
        sci, wht = A.drizzle_resample(frames, shifts=truth["shifts"], scale=2.0,
                                      pixfrac=pf)
        # 見る / 測る のは被覆で割った像。生の sci は保存則の側の量。
        view = _science(sci, wht)
        fwhm_out = _fwhm_of(view, threshold_sigma=4.0, psf_box=15) / 2.0
        loss = (want - float(sci.sum())) / want
        rows.append({"pixfrac": pf, "fwhm_in_px": fwhm_out,
                     "sum": float(sci.sum()), "loss": loss,
                     "wht_min": float(wht.min()), "wht_mean": float(wht.mean())})
        shots.append(_label(_fit(_gray(view, frame_for_scale=view), 560),
                            ["drizzle x2  pixfrac = %.1f(表示は sci/wht)" % pf,
                             "総フラックス %.1f e-(縁で %.2f %% だけ外へ)"
                             % (sci.sum(), 100 * loss),
                             "%s FWHM %.3f 入力画素" % (M["right"], fwhm_out),
                             "被覆 wht 最小 %.3f / 平均 %.3f"
                             % (wht.min(), wht.mean())]))
        labels.append("drizzle x2 pixfrac %.1f — FWHM %.3f 入力画素"
                      % (pf, fwhm_out))

    book = et.flipbook(shots, labels,
                       title="drizzle —— しずくを小さくすると像が立つ")
    info = et.save_animation(book, "wingastro_drizzle", duration_ms=1200,
                             hold_last_ms=2400)
    data = {"input_sum": want, "rows": rows,
            "fwhm_single": _fwhm_of(single, threshold_sigma=4.0),
            "fwhm_naive": _fwhm_of(naive, threshold_sigma=4.0),
            "n_frames": len(frames), "dither_px": 1.5, "true_fwhm": 1.15}
    return info, data


def ex_drizzle_flux():
    """**面積保存そのもの**を数字で。ディザ 0 なら誤差は float64 の丸め。"""
    frames, _ = A.synth_frame_series(
        shape=(48, 48), n_frames=8, dither_px=0.0, n_stars=12,
        flux_min=4000.0, flux_max=20000.0, sky=80.0, read_sigma=5.0,
        seed=SEED + 41, margin_px=8.0)
    want = float(np.mean([f.sum() for f in frames]))
    grid = []
    for pf in (1.0, 0.7, 0.4):
        row = []
        for sc in (1.0, 2.0, 3.0, 4.0):
            sci, wht = A.drizzle_resample(frames, scale=sc, pixfrac=pf)
            row.append({"pixfrac": pf, "scale": sc,
                        "rel": abs(float(sci.sum()) - want) / want,
                        "wht_mean": float(wht.mean())})
        grid.append(row)
    worst = max(c["rel"] for r in grid for c in r)

    panels, labels = [], []
    for pf, row in zip((1.0, 0.7, 0.4), grid):
        sci, wht = A.drizzle_resample(frames, scale=3.0, pixfrac=pf)
        panels.append(_label(_fit(_gray(sci)),
                             ["pixfrac = %.1f, 倍率 x3" % pf,
                              "総和 %.4f e-" % sci.sum(),
                              "入力の平均 %.4f e-" % want,
                              "%s 相対誤差 %.1e" % (M["right"],
                                                    row[2]["rel"]),
                              "被覆 wht 平均 %.4f = pixfrac^2 %.4f"
                              % (wht.mean(), pf * pf)]))
        labels.append("pixfrac %.1f — 相対誤差 %.1e" % (pf, row[2]["rel"]))

    p = Plot(xlim=(1, 4), ylim=(1e-16, 1e-12), ylog=True,
             margin=(80, 20, 44, 66))
    p.grid_x([1, 2, 3, 4], "x%d")
    p.grid_y([1e-16, 1e-15, 1e-14, 1e-13, 1e-12], "%.0e")
    for pf, row, col in zip((1.0, 0.7, 0.4),
                            grid, (C_RIGHT, C_EMPH, fs.role_rgb8("baseline"))):
        ys = [max(c["rel"], 1e-16) for c in row]
        p.line([c["scale"] for c in row], ys, col, width=2)
        p.markers([c["scale"] for c in row], ys, col)
    p.text(PANEL // 2, 6, "総フラックスの相対誤差", size=17, anchor="ma")
    p.text(PANEL // 2, 30, "縦 = 相対誤差 / 横 = 出力の倍率", et.MUTED, 13,
           anchor="ma")
    p.text(100, 88, "%s pixfrac 1.0" % M["right"], C_RIGHT, 14)
    p.text(100, 108, "%s pixfrac 0.7" % M["emphasis"], C_EMPH, 14)
    p.text(100, 128, "%s pixfrac 0.4" % M["baseline"],
           fs.role_rgb8("baseline"), 14)
    p.text(100, 152, "最大でも %.1e = 倍精度の丸め" % worst, et.FG, 14)
    panels.append(_fit(p.done()))
    labels.append("12 通りすべてで丸め誤差の桁")

    sheet = et.contact_sheet(panels, labels, ncols=4, panel_px=PANEL,
                             title="drizzle は面積を保存する —— しずくが格子の"
                                   "内側にある限り総和は動かない")
    info = et.save_exhibit(sheet, "wingastro_drizzle_flux")
    data = {"input_sum": want, "grid": grid, "worst_rel": worst}
    return info, data


def ex_drizzle_pair():
    """標本化不足の二重星。平均合成は 1 つ、drizzle は 2 つに見える。"""
    sep = 1.6
    n_frames, size = 24, 44
    golden = np.pi * (3.0 - np.sqrt(5.0))
    frames, shifts = [], []
    for i in range(n_frames):
        rad = 1.5 * (i / (n_frames - 1))
        dr, dc = rad * np.cos(golden * i), rad * np.sin(golden * i)
        img = np.full((size, size), 25.0)
        img += A._gaussian_star_exact(size, size, 22 + dr, 21 + dc, 26000.0,
                                      0.55, 0.55)
        img += A._gaussian_star_exact(size, size, 22 + dr, 21 + sep + dc,
                                      26000.0, 0.55, 0.55)
        frames.append(A.synth_starfield.__globals__["photoncount"].photon_sample(
            img, 1.0, 0.0, seed=(SEED + 51 + i) % (1 << 31)))
        shifts.append((dr, dc))
    shifts = np.asarray(shifts)
    naive = A.sigma_clip_stack(frames, mode="mean")[0]
    sci, wht = A.drizzle_resample(frames, shifts=shifts, scale=3.0, pixfrac=0.4)
    view = _science(sci, wht)
    n_naive = len(A.star_detect(naive, threshold_sigma=5.0, min_separation=1))
    n_driz = len(A.star_detect(view, threshold_sigma=5.0, min_separation=2))
    n_raw = len(A.star_detect(sci, threshold_sigma=5.0, min_separation=2))

    # ★ 原寸で並べると「2 個検出した」が**目では確かめられない**(44x44 の
    # 中で 1.6 画素の対は数画素の塊にしかならない)。検出器の言い分だけを
    # 信じさせる図にしないため、対の周りを同じ物理範囲だけ切って拡大する。
    def _zoom(img, r, c, half_in, scale):
        r0 = int(round((r + 0.5) * scale - 0.5 - half_in * scale))
        c0 = int(round((c + 0.5) * scale - 0.5 - half_in * scale))
        n = int(round(2 * half_in * scale))
        r0 = max(0, min(img.shape[0] - n, r0))
        c0 = max(0, min(img.shape[1] - n, c0))
        return img[r0:r0 + n, c0:c0 + n]

    half_in = 5.0                       # 対の左右 5 入力画素ぶんだけ見る
    z_single = _zoom(frames[0], 22.0, 21.0 + sep / 2, half_in, 1)
    z_naive = _zoom(naive, 22.0, 21.0 + sep / 2, half_in, 1)
    z_view = _zoom(view, 22.0, 21.0 + sep / 2, half_in, 3)
    z_sci = _zoom(sci, 22.0, 21.0 + sep / 2, half_in, 3)

    def _dip(z):
        """対を横切る行の「2 つの峰の低い方」に対する谷の深さ(%)。

        「目でも分かれる」は主観なので、**谷の深さ**という数で言い直す。
        谷が無ければ 0 %(= 分かれていない)。
        """
        row = z[z.shape[0] // 2]
        i = int(np.argmax(row))
        lo, hi = max(0, i - 6), min(len(row), i + 7)
        seg = row[lo:hi]
        peaks = [k for k in range(1, len(seg) - 1)
                 if seg[k] >= seg[k - 1] and seg[k] > seg[k + 1]]
        if len(peaks) < 2:
            return 0.0
        a, b = peaks[0], peaks[-1]
        valley = float(seg[a:b + 1].min())
        weaker = float(min(seg[a], seg[b]))
        return 100.0 * (1.0 - valley / weaker) if weaker > 0 else 0.0

    dip_naive, dip_view = _dip(z_naive), _dip(z_view)
    # 表示は線形(ガンマ 1、上端は最大値)。ガンマを掛けると芯が飽和して
    # 2 つの峰が 1 つに潰れて見える —— 図の主張と表示が食い違う。
    show = dict(low=2.0, high=100.0, gamma=1.0)
    panels = [
        _label(_fit(_gray(z_single, **show), 420),
               ["1 枚(対の周り %.0f 入力画素を拡大)" % (2 * half_in),
                "間隔 %.1f px / sigma 0.55 px = 標本化不足" % sep,
                "表示は線形(全パネル共通)"]),
        _label(_fit(_gray(z_naive, **show), 420),
               ["24 枚を平均(同じ範囲)",
                "%s 検出できた星 %d 個" % (M["wrong"], n_naive),
                "峰の間の谷 %.1f %%(= 分かれていない)" % dip_naive]),
        _label(_fit(_gray(z_view, **show), 420),
               ["drizzle x3 pixfrac 0.4(sci/wht)",
                "%s 検出できた星 %d 個" % (M["right"], n_driz),
                "峰の間の谷 %.1f %%" % dip_view]),
        _label(_fit(_gray(z_sci, **show), 420),
               ["同じ drizzle の生の sci(割らない)",
                "%s 全画面で検出 %d 個 = 被覆の格子" % (M["wrong"], n_raw),
                "保存則の像と、見る像は別物"]),
    ]
    labels = ["1 枚(拡大)", "平均合成 — %d 個" % n_naive,
              "drizzle x3 (sci/wht) — %d 個" % n_driz,
              "割らないと格子が星に化ける — %d 個" % n_raw]
    sheet = et.contact_sheet(panels, labels, ncols=4, panel_px=420,
                             title="間隔 %.1f 画素の二重星 —— 平均では 1 つ、"
                                   "drizzle では 2 つ" % sep)
    info = et.save_exhibit(sheet, "wingastro_drizzle_pair")
    data = {"separation_px": sep, "n_naive": n_naive, "n_drizzle": n_driz,
            "n_raw_sci": n_raw, "n_frames": n_frames,
            "dip_naive_pct": dip_naive, "dip_drizzle_pct": dip_view}
    return info, data


# --------------------------------------------------------------------------- #
# 展示 5(主展示): σ クリップの破綻(GIF)                                     #
# --------------------------------------------------------------------------- #
CONTAM = [0.0, 0.10, 0.20, 0.30, 0.40, 0.45, 0.50, 0.55, 0.60]


def _contaminated(frames, k, boost):
    """先頭 *k* 枚に、画面全体の一様な明るさ *boost* を足す。"""
    out = []
    for i, f in enumerate(frames):
        out.append(f + boost if i < k else f.copy())
    return out


def ex_clip_breakdown():
    """**このウィングの主展示**: 汚染 50 % で理論どおり折れる。"""
    n = 20
    boost = 900.0
    frames, truth = A.synth_frame_series(
        shape=(120, 120), n_frames=n, dither_px=0.0, n_stars=24,
        flux_min=1200.0, flux_max=24000.0, fwhm_px=3.2, sky=120.0,
        read_sigma=6.0, seed=SEED + 61, margin_px=10.0)
    ideal = truth["noiseless"]

    rows = []
    for c in CONTAM:
        k = int(round(c * n))
        dirty = _contaminated(frames, k, boost)
        clip = A.sigma_clip_stack(dirty, mode="sigma_clip", kappa=3.0,
                                  iters=5, scale="mad")
        med = A.sigma_clip_stack(dirty, mode="median")[0]
        mean = A.sigma_clip_stack(dirty, mode="mean")[0]
        rows.append({
            "contam": c, "k": k,
            "clip_err": float(np.median(clip[0] - ideal)),
            "median_err": float(np.median(med - ideal)),
            "mean_err": float(np.median(mean - ideal)),
            "rejected": float(1.0 - clip[1].mean()),
            "image": clip[0], "ref": mean})

    # 表示尺度は**全コマ共通**で、汚染で持ち上がるぶんまで含めて切る。
    # 最初の版は汚染 0 % のコマの分位で切っていたので、50 % を超えたコマが
    # 真っ白に飽和して**何も読めなかった**(点検スクリプトの「ほぼ単色」に
    # 引っかかる寸前でもある)。右側の誤差図は固定の ±limit なので、
    # 「どこがどれだけずれたか」がコマ間で直接比べられる。
    lo, hi = np.percentile(rows[0]["image"], [25.0, 99.7])
    hi = hi + boost
    lim = boost * 1.15
    panel_px = 330
    shots, labels = [], []
    for r in rows:
        broken = abs(r["clip_err"]) > 1.0
        col = C_WRONG if broken else C_RIGHT
        mark = M["wrong"] if broken else M["right"]
        left = _label(
            _fit(np.repeat(_norm(r["image"], lo, hi)[..., None] ** 0.7, 3,
                           axis=2), panel_px),
            ["汚染 %d %%(%d / %d 枚に +%.0f e-)"
             % (round(100 * r["contam"]), r["k"], n, boost),
             "全コマ共通の表示尺度"], size=14)
        # ★ 誤差図は**符号ではなく大きさ**を塗る。最初の版は発散配色で塗って
        # いたが、この実験の誤差は常に正なので「正 = right の青」になり、
        # **壊れている状態が「正しい」色で塗られる**という逆の意味になった。
        # ここで読者に伝えたいのは向きではなく「どれだけ間違っているか」なので、
        # wrong の 1 色で濃さだけを変える(色だけに意味を載せないよう、
        # 記号と数値も併記する)。
        err_map = np.clip(np.abs(r["image"] - ideal) / lim, 0.0, 1.0) ** 0.6
        c_wrong = np.asarray(C_WRONG, np.float64) / 255.0
        right = _label(
            _fit(err_map[..., None] * c_wrong[None, None, :], panel_px),
            ["%s |真値との差| を 0〜%.0f e- で塗る" % (M["wrong"], lim),
             "%s κ-σ 合成の誤差 %+.2f e-" % (mark, r["clip_err"]),
             "棄却率 %.1f %%" % (100 * r["rejected"]),
             "(参考)単純平均 %+.1f e-" % r["mean_err"]],
            size=14, color=col)
        gap = np.zeros((panel_px, 10, 3))
        gap[:] = np.asarray(et.BG, np.float64) / 255.0
        shots.append(np.concatenate([left, gap, right], axis=1))
        labels.append("汚染 %d %% — 誤差 %+.2f e-"
                      % (round(100 * r["contam"]), r["clip_err"]))

    # 最後に、折れ線で「どこで折れたか」を 1 枚
    c_med = fs.role_rgb8("baseline")
    p = Plot(w=2 * panel_px + 10, h=panel_px, xlim=(0.0, 62.0),
             ylim=(-40.0, 1010.0), margin=(78, 22, 44, 44))
    p.grid_x([0, 10, 20, 30, 40, 50, 60], "%.0f%%")
    p.grid_y([0, 225, 450, 675, 900], "%.0f")
    xs = [100 * r["contam"] for r in rows]
    p.line(xs, [r["mean_err"] for r in rows], C_NEUTRAL, width=2, dashed=True)
    p.line(xs, [r["median_err"] for r in rows], c_med, width=5)
    p.line(xs, [r["clip_err"] for r in rows], C_RIGHT, width=2)
    p.markers(xs, [r["clip_err"] for r in rows], C_RIGHT)
    p.vline(50.0, C_WRONG, width=2)
    p.text(p.w // 2, 6, "縦 = 真値からの誤差 (e-) / 横 = 汚染フレームの割合",
           et.MUTED, 14, anchor="ma")
    p.text(96, 40, "%s κ-σ(中央値 + MAD、細線)" % M["right"], C_RIGHT, 14)
    p.text(96, 60, "%s 中央値(太線)—— 同じ場所で折れる" % M["baseline"],
           c_med, 14)
    p.text(96, 80, "%s 単純平均(破線)—— 汚染に比例して外れる" % M["neutral"],
           C_NEUTRAL, 14)
    p.text(96, 104, "%s 中央値の破綻点 50 %%" % M["wrong"], C_WRONG, 14)
    fig = p.done()
    shots.append(fig[:panel_px, :2 * panel_px + 10])
    labels.append("汚染率と誤差(折れ目は 50 %)")

    book = et.flipbook(shots, labels,
                       title="σ クリップの破綻 —— 折れ目は 50 %")
    info = et.save_animation(book, "wingastro_clip_breakdown",
                             duration_ms=1000, hold_last_ms=3000)
    data = {"boost": boost, "n_frames": n,
            "rows": [{kk: vv for kk, vv in r.items()
                      if kk not in ("image", "ref")} for r in rows],
            "last_good": max(r["contam"] for r in rows
                             if abs(r["clip_err"]) < 1.0),
            "first_broken": min(r["contam"] for r in rows
                                if abs(r["clip_err"]) > 1.0)}
    return info, data


# --------------------------------------------------------------------------- #
# 展示 6: 位置合わせ —— 星は互いに見分けがつかない(タイル)                   #
# --------------------------------------------------------------------------- #
def ex_align():
    frames, truth = A.synth_frame_series(
        shape=(150, 150), n_frames=9, dither_px=6.0, n_stars=34,
        flux_min=2000.0, flux_max=28000.0, fwhm_px=3.0, sky=90.0,
        read_sigma=6.0, seed=SEED + 71, margin_px=14.0)
    errs, infos = [], []
    for i in range(1, len(frames)):
        _, nfo = A.frame_align(frames[0], frames[i], model="similarity")
        want = truth["shifts"][0] - truth["shifts"][i]
        errs.append(float(np.hypot(nfo["shift_row"] - want[0],
                                   nfo["shift_col"] - want[1])))
        infos.append(nfo)
    median_err = float(np.median(errs))

    before = A.sigma_clip_stack(frames, mode="mean")[0]
    aligned, _ = A.align_frames(frames, reference=0)
    after = A.sigma_clip_stack(aligned, mode="mean")[0]
    f_before, f_after = _fwhm_of(before), _fwhm_of(after)

    stars = A.star_detect(frames[0], max_stars=40)
    marks = np.zeros(frames[0].shape)
    marks = imagedraw.draw_markers(
        marks, [(float(c), float(r)) for r, c in stars], color=1.0, size=7,
        shape="cross", width=1)
    overlay = _gray(frames[0])
    overlay = overlay * (1.0 - marks[..., None]) \
        + marks[..., None] * (np.asarray(C_EMPH, float) / 255.0)

    panels = [
        _label(_fit(overlay),
               ["星の検出 %d 個(副画素の重心)" % len(stars),
                "記述子は使わない —— 星は互いに",
                "見分けがつかないので比検定が全部捨てる"]),
        _label(_fit(_gray(before)),
               ["9 枚を位置合わせ「せず」平均",
                "%s FWHM %.3f px" % (M["wrong"], f_before),
                "最大 6.0 px のディザがそのまま滲む"]),
        _label(_fit(_gray(after, frame_for_scale=before)),
               ["frame_align -> align_frames -> 平均",
                "%s FWHM %.3f px(%.1f %% 改善)"
                % (M["right"], f_after, 100 * (1 - f_after / f_before)),
                "ずれの推定誤差 中央値 %.4f px" % median_err]),
    ]
    labels = ["検出した星(記述子ではなく配置で照合)",
              "位置合わせなし — FWHM %.3f px" % f_before,
              "位置合わせあり — FWHM %.3f px" % f_after]
    sheet = et.contact_sheet(panels, labels, ncols=3, panel_px=PANEL,
                             title="位置合わせ —— 星の配置だけで %.4f px まで"
                                   "合う(記述子は使えない)" % median_err)
    info = et.save_exhibit(sheet, "wingastro_align")
    data = {"median_shift_err_px": median_err, "errors": errs,
            "fwhm_before": f_before, "fwhm_after": f_after,
            "n_stars": len(stars), "n_frames": len(frames),
            "dither_px": 6.0,
            "median_inliers": float(np.median([i["n_inliers"] for i in infos])),
            "median_rms_px": float(np.median([i["rms_px"] for i in infos]))}
    return info, data


# --------------------------------------------------------------------------- #
# 展示 7: 既知フラックスの測光(原寸 1 枚 = 数値が主役)                       #
# --------------------------------------------------------------------------- #
def ex_photometry():
    sigmas = (1.0, 1.5, 2.0, 3.0)
    wide, tight = [], []
    for s in sigmas:
        frame, truth = A.synth_starfield(
            shape=(96, 96), n_stars=1, flux_min=10000.0, flux_max=10000.0,
            fwhm_px=s * A.FWHM_PER_SIGMA, sky=0.0, read_sigma=0.0, noise=False,
            seed=SEED + 81, margin_px=40.0)
        ctr = np.array([[truth["rows"][0], truth["cols"][0]]])
        for rmul, bucket in ((8.0, wide), (3.0, tight)):
            r = rmul * s
            ph = A.aperture_photometry(frame, ctr, r_aperture=r,
                                       r_inner=r + 4, r_outer=r + 10)[0]
            th = 10000.0 * (1.0 - np.exp(-r * r / (2.0 * s * s)))
            bucket.append({"sigma": s, "r": r, "meas": ph["flux"],
                           "theory": th, "err": (ph["flux"] - th) / th})

    p = Plot(w=980, h=560, xlim=(0.8, 3.3), ylim=(-1.25, 0.30),
             margin=(96, 26, 56, 76))
    p.grid_x([1.0, 1.5, 2.0, 3.0], "%.1f")
    p.grid_y([-1.0, -0.75, -0.5, -0.25, 0.0, 0.25], "%+.2f%%")
    p.line([1.0, 3.0], [0.0, 0.0], (90, 92, 112), width=1)
    p.line([w["sigma"] for w in wide], [100 * w["err"] for w in wide],
           C_RIGHT, width=4)
    p.markers([w["sigma"] for w in wide], [100 * w["err"] for w in wide],
              C_RIGHT, size=7)
    p.line([t["sigma"] for t in tight], [100 * t["err"] for t in tight],
           C_WRONG, width=4)
    p.markers([t["sigma"] for t in tight], [100 * t["err"] for t in tight],
              C_WRONG, size=7)
    p.text(p.w // 2, 8, "既知フラックス 10000 e- を測り返す", size=20,
           anchor="ma")
    p.text(p.w // 2, 36, "縦 = 閉形式との差 (%) / 横 = 星の sigma(画素)",
           et.MUTED, 14, anchor="ma")
    # 凡例は左下の空いている領域へ(曲線とも 0 % 線とも重ならない位置)
    # 凡例と註は右下の空白へ(2 本の曲線とも 0 % 線とも重ならない領域)
    p.text(430, 300, "%s 半径 8 sigma:4 点すべてで誤差 %.4f %%"
           % (M["right"], 100 * max(abs(w["err"]) for w in wide)), C_RIGHT, 16)
    p.text(430, 326, "%s 半径 3 sigma:%.3f %% 〜 %.3f %%(常に負)"
           % (M["wrong"], 100 * tight[0]["err"], 100 * tight[-1]["err"]),
           C_WRONG, 16)
    p.text(430, 364, "小さい開口のずれは画素化に由来する。開口の縁の画素を",
           et.MUTED, 14)
    p.text(430, 384, "「画素平均 x 面積比」で代表すると、円の内側ほど明るい分",
           et.MUTED, 14)
    p.text(430, 404, "だけ必ず少なく出る。sigma の 2 乗で消えるのがその証拠 ——",
           et.MUTED, 14)
    p.text(430, 424, "%.3f %% -> %.3f %%(sigma 1.0 -> 3.0 で %.1f 倍小さく)"
           % (100 * tight[0]["err"], 100 * tight[-1]["err"],
              tight[0]["err"] / tight[-1]["err"]), et.MUTED, 14)
    fig = p.done()
    info = et.save_exhibit(fig, "wingastro_photometry")
    data = {"wide": wide, "tight": tight,
            "wide_worst_pct": 100 * max(abs(w["err"]) for w in wide),
            "bias_ratio": tight[0]["err"] / tight[-1]["err"]}
    return info, data


# --------------------------------------------------------------------------- #
EXHIBITS = {
    "sqrt_n": ex_sqrt_n,
    "lucky_sheet": ex_lucky_sheet,
    "lucky_sweep": ex_lucky_sweep,
    "cosmic": ex_cosmic,
    "drizzle": ex_drizzle,
    "drizzle_flux": ex_drizzle_flux,
    "drizzle_pair": ex_drizzle_pair,
    "clip_breakdown": ex_clip_breakdown,
    "align": ex_align,
    "photometry": ex_photometry,
}

#: 展示 -> (stem, GIF か, 使用 op)
KIND = {
    "sqrt_n": ("wingastro_stack_sqrtn", False,
               ["synth_frame_series", "sigma_clip_stack", "noise_sigma"]),
    "lucky_sheet": ("wingastro_lucky_sheet", False,
                    ["synth_frame_series", "frame_quality", "lucky_select"]),
    "lucky_sweep": ("wingastro_lucky_sweep", True,
                    ["lucky_select", "sigma_clip_stack", "frame_quality"]),
    "cosmic": ("wingastro_cosmic", False,
               ["synth_starfield", "cosmic_ray_reject",
                "cosmic_ray_reject_stack", "sigma_clip_stack", "star_detect"]),
    "drizzle": ("wingastro_drizzle", True,
                ["synth_frame_series", "drizzle_resample", "sigma_clip_stack",
                 "frame_quality"]),
    "drizzle_flux": ("wingastro_drizzle_flux", False,
                     ["synth_frame_series", "drizzle_resample"]),
    "drizzle_pair": ("wingastro_drizzle_pair", False,
                     ["drizzle_resample", "sigma_clip_stack", "star_detect"]),
    "clip_breakdown": ("wingastro_clip_breakdown", True,
                       ["synth_frame_series", "sigma_clip_stack"]),
    "align": ("wingastro_align", False,
              ["star_detect", "frame_align", "align_frames",
               "sigma_clip_stack", "frame_quality"]),
    "photometry": ("wingastro_photometry", False,
                   ["synth_starfield", "aperture_photometry"]),
}


def _captions(meta):
    """ja / en のキャプション原稿を、**実測値だけ**を差し込んで作る。"""
    d = {k: meta[k]["data"] for k in meta}
    ja, en = [], []

    def add(name, alt_ja, alt_en, body_ja, body_en):
        stem, is_gif, ops = KIND[name]
        ops_s = ", ".join("`%s`" % o for o in ops)
        fn = et.markdown_animation if is_gif else et.markdown
        ja.append(fn(stem, alt_ja, "**%s** ―― %s使用 op: %s。"
                     % (alt_ja, body_ja, ops_s)))
        en.append(fn(stem, alt_en, "**%s** — %s Ops used: %s."
                     % (alt_en, body_en, ops_s)))

    s = d["sqrt_n"]
    add("sqrt_n",
        "重ねると雑音は sqrt(N) で減る",
        "Stacking divides the noise by the square root of N",
        "合成星野なので**真値が分かっており、雑音は残差そのもので測れる**。"
        "1 枚の残差 RMS は %.3f e-(空 %.0f + 読み出し %.0f e- から予測される "
        "%.3f)で、64 枚まで倍々に重ねると改善は sqrt(N) から**最大 %.1f %% "
        "しか外れない**。右下の差分図は、星の位置に何も残らず雑音だけが消えた"
        "ことを示す(発散配色。赤緑の対は使っていない)。"
        % (s["base_rms"], s["sky"], s["read_sigma"], s["predicted_single"],
           s["max_dev_pct"]),
        "The star field is synthetic, so **the truth is known and the noise can "
        "be measured as the residual itself**. One frame has a residual RMS of "
        "%.3f e- (against %.3f predicted from %.0f e- of sky plus %.0f e- of "
        "read noise), and stacking up to 64 frames tracks sqrt(N) to within "
        "**%.1f %%**. The difference panel at the bottom right shows nothing "
        "left at the star positions and only the noise gone."
        % (s["base_rms"], s["predicted_single"], s["sky"], s["read_sigma"],
           s["max_dev_pct"]))

    l1, l2 = d["lucky_sheet"], d["lucky_sweep"]
    add("lucky_sheet",
        "lucky imaging —— 品質点で並べ替える",
        "Lucky imaging — sorting the frames by quality",
        "大気が良い瞬間ほど、同じ総フラックスが少ない画素に集まる。だから選別"
        "基準は「基準星のピーク割合 x 真円度」で、これは露出やゲインを変えても"
        "動かない。%d 枚を点の高い順に並べたのが上位 8 枚で、点と FWHM の相関は"
        "**%.3f**(FWHM %.2f 〜 %.2f px)。青が採用、灰が不採用。"
        % (l1["n_frames"], l1["corr"], l1["fwhm_best"], l1["fwhm_worst"]),
        "The better the atmosphere, the more of the same total flux lands in "
        "fewer pixels, so the selection criterion is peak fraction times "
        "roundness — a number that does not move when exposure or gain change. "
        "These are the best 8 of %d frames by score; score and FWHM correlate "
        "at **%.3f** across FWHM %.2f to %.2f px. Blue is kept, grey is dropped."
        % (l1["n_frames"], l1["corr"], l1["fwhm_best"], l1["fwhm_worst"]))

    r0, rl = l2["rows"][0], l2["rows"][-1]
    add("lucky_sweep",
        "上位何 % を採るか —— 鋭さと雑音の取引",
        "How much to keep — sharpness bought with noise",
        "全部(%d 枚)から上位 %d %%(%d 枚)まで絞ると、合成後の FWHM は "
        "%.3f -> %.3f px と **%.1f %% 良くなる**。ただし枚数が減るぶん残差 RMS は "
        "%.3f -> %.3f e- と **%.2f 倍**に増える。lucky imaging は「改善」ではなく"
        "**取引**であり、その両側を同じ図に出すのが正直な出し方。"
        % (r0["kept"], round(100 * rl["fraction"]), rl["kept"], r0["fwhm"],
           rl["fwhm"], l2["fwhm_gain_pct"], r0["rms"], rl["rms"],
           l2["rms_cost_x"]),
        "Going from all %d frames down to the best %d %% (%d frames) improves "
        "the stacked FWHM from %.3f to %.3f px, **a %.1f %% gain** — and costs "
        "a residual RMS of %.3f rising to %.3f e-, **%.2f times worse**. Lucky "
        "imaging is a trade, not an improvement, and both sides belong in the "
        "same figure."
        % (r0["kept"], round(100 * rl["fraction"]), rl["kept"], r0["fwhm"],
           rl["fwhm"], l2["fwhm_gain_pct"], r0["rms"], rl["rms"],
           l2["rms_cost_x"]))

    c = d["cosmic"]
    add("cosmic",
        "宇宙線の消え方 —— 尖りで見分ける / 枚数で見分ける",
        "How a cosmic ray disappears — by sharpness, or by counting frames",
        "宇宙線は光学系を通っていないので**星より尖る**。ラプラシアンを 2 倍"
        "標本化して微細構造と比べると、植えた %d 画素に対し %d 画素を検出して"
        "適合率 **%.3f** / 再現率 **%.3f** ―― 星の中心を 1 つも拾わないことが"
        "要点。合成なので「宇宙線だけ無い同じ観測」を作れて、正解との最大差が "
        "%.0f -> %.0f e- に落ちることまで言える(**フレームの最大値では言えない**"
        " —— それは一番明るい星の値であって、除去の前後でほとんど動かない)。"
        "枚数がある場合はもっと簡単で、%d 枚を素直に平均しても宇宙線は 1/%d に"
        "薄まって残り正解から %.0f e- ずれるのに対し、κ-σ 合成は検出も置換も"
        "せずに %.0f e-、フレーム間比較で先に除去すれば %.0f e- になる。"
        % (c["truth_px"], c["detected_px"], c["precision"], c["recall"],
           c["residual_raw"], c["residual_cleaned"], c["n_frames"],
           c["n_frames"], c["err_naive"], c["err_clipped"], c["err_fixed"]),
        "A cosmic ray never went through the optics, so **it is sharper than a "
        "star**. Comparing a 2x-subsampled Laplacian against the fine-structure "
        "image finds %d pixels against the %d planted — precision **%.3f**, "
        "recall **%.3f** — and the point is that it flags no star core at all. "
        "Because the data is synthetic we can also make the same exposure "
        "*without* the cosmic rays, so the largest departure from the truth is "
        "quotable: %.0f e- before, %.0f e- after. (**The frame maximum cannot "
        "say this** — that is the brightest star, and it barely moves.) With "
        "several frames it is easier still: plainly averaging %d frames only "
        "dilutes each hit to 1/%d and still lands %.0f e- from the truth, while "
        "a kappa-sigma combine reaches %.0f e- with no detection or replacement "
        "at all, and rejecting frame-to-frame first reaches %.0f e-."
        % (c["detected_px"], c["truth_px"], c["precision"], c["recall"],
           c["residual_raw"], c["residual_cleaned"], c["n_frames"],
           c["n_frames"], c["err_naive"], c["err_clipped"], c["err_fixed"]))

    z = d["drizzle_flux"]
    add("drizzle_flux",
        "drizzle は面積を保存する",
        "Drizzle conserves area",
        "入力画素を一回り縮めた「しずく」として出力格子へ**面積比で**撒くので、"
        "しずくが格子の内側にある限り総和は動かない。pixfrac 1.0 / 0.7 / 0.4 x "
        "倍率 x1〜x4 の **12 通りすべてで相対誤差は最大 %.1e** ―― これは"
        "「ほぼ保存」ではなく倍精度の丸めそのもの。被覆マップ ``wht`` の平均が "
        "pixfrac の 2 乗にきっちり一致するのも、撒き方が面積で定義されている"
        "ことの裏取りになる。入力の総和は %.4f e-。"
        % (z["worst_rel"], z["input_sum"]),
        "Each input pixel is shrunk into a *drop* and spread over the output "
        "grid **in proportion to overlap area**, so while the drops stay inside "
        "the grid the total cannot change. Across **all 12 combinations** of "
        "pixfrac 1.0 / 0.7 / 0.4 and magnification x1 to x4 the relative error "
        "peaks at **%.1e** — that is double-precision rounding, not "
        "\"approximately conserved\". The mean of the weight map matches "
        "pixfrac squared exactly, which is the same statement seen from the "
        "coverage side. The input total is %.4f e-."
        % (z["worst_rel"], z["input_sum"]))

    dz = d["drizzle"]
    lastrow = dz["rows"][-1]
    add("drizzle",
        "drizzle —— しずくを小さくすると像が立ち上がる",
        "Drizzle — the image stands up as the drop shrinks",
        "真の FWHM %.2f 画素、つまり**ナイキストを破った**星野を 24 枚、"
        "1.5 画素のディザで撮る。1 枚では FWHM %.3f 画素にしか見えず、"
        "そのまま平均すると **%.3f 画素とかえって鈍る**(ずれを平均するから)。"
        "同じずれを drizzle に渡すと pixfrac 1.0 / 0.6 / 0.3 で %.3f / %.3f / "
        "%.3f 入力画素まで立ち上がり、そのあいだ総フラックスは縁から出た "
        "%.2f %% 以外**一切動かない**。しずくを小さくするほど鋭くなる代わりに"
        "覆われない出力画素が出る(被覆 wht の最小が %.3f まで下がる)—— "
        "これが drizzle の唯一の調整点。"
        % (dz["true_fwhm"], dz["fwhm_single"], dz["fwhm_naive"],
           dz["rows"][0]["fwhm_in_px"], dz["rows"][1]["fwhm_in_px"],
           dz["rows"][2]["fwhm_in_px"], 100 * lastrow["loss"],
           lastrow["wht_min"]),
        "A star field with a true FWHM of %.2f pixels — **below Nyquist** — "
        "shot 24 times with a 1.5-pixel dither. One frame measures %.3f px, and "
        "plainly averaging them makes it **worse, %.3f px**, because the dither "
        "gets averaged too. Handing drizzle the same dither brings it to %.3f / "
        "%.3f / %.3f input pixels at pixfrac 1.0 / 0.6 / 0.3, while the total "
        "flux **does not move** apart from the %.2f %% that left through the "
        "border. Smaller drops mean sharper images and emptier output pixels "
        "(the minimum weight falls to %.3f) — that tug-of-war is drizzle's only "
        "knob."
        % (dz["true_fwhm"], dz["fwhm_single"], dz["fwhm_naive"],
           dz["rows"][0]["fwhm_in_px"], dz["rows"][1]["fwhm_in_px"],
           dz["rows"][2]["fwhm_in_px"], 100 * lastrow["loss"],
           lastrow["wht_min"]))

    dp = d["drizzle_pair"]
    add("drizzle_pair",
        "間隔 1.6 画素の二重星",
        "A double star 1.6 pixels apart",
        "sigma 0.55 画素の星を 2 つ、%.1f 画素だけ離して %d 枚ディザ撮影する。"
        "平均合成では **%d 個**しか立たないのに、同じ生データを drizzle x3 "
        "(pixfrac 0.4)に通すと **%d 個**に分かれる。解像度は「上げた」のでは"
        "なく、**ディザという形で既に撮れていた情報を捨てずに拾った**だけ。"
        "「分かれた」を主観にしないため、対を横切る行の**谷の深さ**も測って"
        "ある: 平均合成 %.1f %%(谷が無い)に対し drizzle は **%.1f %%**。"
        "4 枚目は同じ drizzle の生の ``sci``(被覆で割っていない像)で、"
        "そこに検出をかけると被覆の格子が **%d 個の偽の星**になる ―― "
        "総フラックスを保存する像と、目で見る像は別の量である。"
        % (dp["separation_px"], dp["n_frames"], dp["n_naive"],
           dp["n_drizzle"], dp["dip_naive_pct"], dp["dip_drizzle_pct"],
           dp["n_raw_sci"]),
        "Two stars of sigma 0.55 px, %.1f px apart, shot %d times with dither. "
        "A mean stack yields **%d star**, while the same raw frames through "
        "drizzle x3 (pixfrac 0.4) separate into **%d**. Nothing was added: the "
        "information was already in the dither, and drizzle simply does not "
        "throw it away. The fourth panel is the same drizzle without dividing "
        "by the weight map, and detecting on it turns the coverage lattice into "
        "**%d spurious stars** — the flux-conserving image and the image you "
        "look at are different quantities."
        % (dp["separation_px"], dp["n_frames"], dp["n_naive"],
           dp["n_drizzle"], dp["n_raw_sci"]))

    b = d["clip_breakdown"]
    rw = {r["contam"]: r for r in b["rows"]}
    add("clip_breakdown",
        "σ クリップの破綻 —— 折れ目はちょうど 50 %",
        "Where sigma clipping breaks — exactly at 50 %",
        "20 枚のうち先頭 k 枚に +%.0f e- の汚染を入れ、割合を 0 から 60 %% まで"
        "上げていく。**45 %% までは誤差 %+.3f e-** と、汚染ゼロのとき"
        "(%+.3f e-)と変わらない答えを返す。ところが **ちょうど 50 %% で誤差は "
        "%+.1f e-**(汚染量のちょうど半分)、**55 %% で %+.1f e-**(汚染量その"
        "もの)に跳ぶ。これは実装の不具合ではなく**中央値の破綻点そのもの**で、"
        "半数を超えた時点で中央値が汚染側の母集団に乗り、クリップは**正しい"
        "フレームの方を捨てる**(棄却率は %.1f %% のまま働いているのに、"
        "捨てる側が入れ替わっている)。最後のコマの折れ線がその証拠で、"
        "**中央値そのものも同じ 50 %% で折れる**(55 %% で %+.1f e-)一方、"
        "単純平均は最初から汚染に比例してずれ続ける(%+.1f e-)。"
        "直せない限界は、直せるふりをせずそのまま展示する。"
        % (b["boost"], rw[0.45]["clip_err"], rw[0.0]["clip_err"],
           rw[0.50]["clip_err"], rw[0.55]["clip_err"],
           100 * rw[0.55]["rejected"], rw[0.55]["median_err"],
           rw[0.55]["mean_err"]),
        "The first k of 20 frames get +%.0f e- of contamination, and k sweeps "
        "from 0 to 60 %%. **Up to 45 %% the error is %+.3f e-** — the same "
        "answer as with no contamination at all (%+.3f e-). Then **at exactly "
        "50 %% it jumps to %+.1f e-**, precisely half the contamination, and "
        "**at 55 %% to %+.1f e-**, all of it. This is not an implementation "
        "fault but the breakdown point of the median: once the contaminated "
        "frames are the majority the median sits among them and the clipping "
        "throws away the *good* frames — it is still rejecting %.1f %% of the "
        "pixels, it has simply swapped which half. The plot in the last frame "
        "is the proof: **the plain median folds at the same 50 %%** (%+.1f e- "
        "at 55 %%), while the plain mean drifts in proportion to the "
        "contamination from the very start (%+.1f e-). A limit that cannot be "
        "fixed is shown as it is."
        % (b["boost"], rw[0.45]["clip_err"], rw[0.0]["clip_err"],
           rw[0.50]["clip_err"], rw[0.55]["clip_err"],
           100 * rw[0.55]["rejected"], rw[0.55]["median_err"],
           rw[0.55]["mean_err"]))

    a = d["align"]
    add("align",
        "位置合わせ —— 星は互いに見分けがつかない",
        "Registration — every star looks like every other star",
        "星野に記述子マッチングは効かない。星は**全部同じ形**なので Lowe の"
        "比検定がほとんど全部を捨ててしまう。代わりに使うのは配置の幾何 ―― "
        "全ペアの差ベクトルを投票させ、最頻値を粗い平行移動とし、既存の "
        "2-D 点対応 RANSAC で誤対応を落として Umeyama で当てはめる。%d 枚・"
        "最大 %.1f 画素のディザで、ずれの推定誤差は中央値 **%.4f 画素**"
        "(内点 中央値 %.0f 対応、残差 RMS %.3f 画素)。位置合わせせずに"
        "平均すると FWHM %.3f px、合わせてから平均すると **%.3f px**。"
        % (a["n_frames"], a["dither_px"], a["median_shift_err_px"],
           a["median_inliers"], a["median_rms_px"], a["fwhm_before"],
           a["fwhm_after"]),
        "Descriptor matching does not work on a star field: every star has the "
        "same shape, so Lowe's ratio test discards nearly all of them. What "
        "works is the geometry of the arrangement — every pair of stars votes "
        "for a displacement, the mode is the coarse shift, an existing 2-D "
        "point-correspondence RANSAC drops the mismatches, and Umeyama fits the "
        "rest. Across %d frames with up to %.1f px of dither the median shift "
        "error is **%.4f px** (median %.0f inliers, residual RMS %.3f px). "
        "Averaging without registering gives FWHM %.3f px; registering first "
        "gives **%.3f px**."
        % (a["n_frames"], a["dither_px"], a["median_shift_err_px"],
           a["median_inliers"], a["median_rms_px"], a["fwhm_before"],
           a["fwhm_after"]))

    ph = d["photometry"]
    add("photometry",
        "既知フラックスを測り返す",
        "Measuring a known flux back",
        "合成星の総フラックスは 10000 e- とこちらが決めた値で、``erf`` による"
        "画素の厳密積分で描いてあるので画像の総和もそれに一致する。半径 8 sigma "
        "の開口で測ると 4 つの尺度すべてで誤差 **%.4f %%** ―― 文字どおり測り"
        "返す。半径 3 sigma に絞ると %.3f %% 〜 %.3f %% の**負の**ずれが残るが、"
        "これはバグではなく**画素化**である: 開口の縁の画素を「画素平均 x 面積"
        "比」で代表すると、円の内側ほど明るいぶん必ず少なく出る。ずれが sigma の"
        "2 乗で消える(sigma 1.0 -> 3.0 で %.1f 倍小さくなる)ことがその証拠。"
        % (ph["wide_worst_pct"], 100 * ph["tight"][0]["err"],
           100 * ph["tight"][-1]["err"], ph["bias_ratio"]),
        "The synthetic star's total flux is 10000 e- because we chose it, and "
        "the profile is drawn by exact per-pixel integration of the Gaussian "
        "(``erf``), so the image sums to that too. An aperture of radius "
        "8 sigma measures it back to **%.4f %%** at all four scales. Squeezing "
        "to 3 sigma leaves a **negative** bias of %.3f %% to %.3f %%, and that "
        "is pixelation rather than a bug: representing an edge pixel by its "
        "average times an area fraction always undercounts, because the part "
        "inside the circle is the brighter part. The proof is that the bias "
        "falls as sigma squared — %.1f times smaller from sigma 1.0 to 3.0."
        % (ph["wide_worst_pct"], 100 * ph["tight"][0]["err"],
           100 * ph["tight"][-1]["err"], ph["bias_ratio"]))

    note_ja = ("<!-- 素材はすべて `astrostack.synth_starfield` / "
               "`synth_frame_series` が作った合成星野(星の座標・フラックス・"
               "PSF・宇宙線が既知)。実写の天体画像は使っていない。数値は"
               "すべてその場の実測。 -->\n")
    note_en = ("<!-- Every frame here is synthetic, made by "
               "`astrostack.synth_starfield` / `synth_frame_series` with known "
               "star positions, fluxes, PSF and cosmic rays. No real "
               "astronomical image is used. All numbers are measured at "
               "generation time. -->\n")
    return "\n".join([note_ja] + ja), "\n".join([note_en] + en)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exhibits", default="", help="カンマ区切りの展示名")
    ap.add_argument("--list", action="store_true", help="展示名を並べて終了")
    ap.add_argument("--verify", action="store_true",
                    help="2 回生成して SHA-256 が一致することを確かめる")
    args = ap.parse_args(argv)

    if args.list:
        for name in EXHIBITS:
            print(name)
        return 0

    want = [w.strip() for w in args.exhibits.split(",") if w.strip()] \
        or list(EXHIBITS)
    unknown = [w for w in want if w not in EXHIBITS]
    if unknown:
        raise SystemExit("未知の展示: %s. --list で一覧" % unknown)

    meta = {}
    for name in want:
        print("[wingastro] %s ..." % name, flush=True)
        info, data = EXHIBITS[name]()
        digest = info.get("png_sha256") or info.get("gif_sha256")
        meta[name] = {"file": info.get("png") or info.get("gif"),
                      "sha256": digest, "data": data}
        print("             -> %s  sha256 %s"
              % (os.path.basename(meta[name]["file"]), digest[:16]))

    if args.verify:
        print("[wingastro] 再生成して SHA-256 を照合 ...", flush=True)
        bad = 0
        for name in want:
            info, _ = EXHIBITS[name]()
            again = info.get("png_sha256") or info.get("gif_sha256")
            same = again == meta[name]["sha256"]
            bad += 0 if same else 1
            print("             %-16s %s" % (name, "一致" if same else "★不一致"))
        if bad:
            raise SystemExit("%d 件が決定的でない" % bad)

    os.makedirs(os.path.dirname(META_PATH), exist_ok=True)
    with open(META_PATH, "w", encoding="utf-8") as fh:
        json.dump({"generator": "tools/gen_wingastro_gallery.py", "seed": SEED,
                   "exhibits": meta}, fh, ensure_ascii=False, indent=1,
                  default=float)
    print("[wingastro] meta -> %s" % os.path.relpath(META_PATH, ROOT))

    if set(want) == set(EXHIBITS):
        ja, en = _captions(meta)
        os.makedirs(EXHIBITS_DIR, exist_ok=True)
        for lang, body in (("ja", ja), ("en", en)):
            path = os.path.join(EXHIBITS_DIR, "wingastro.%s.md" % lang)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body)
            print("[wingastro] キャプション -> %s"
                  % os.path.relpath(path, ROOT))
    else:
        print("[wingastro] 一部生成のためキャプションは書き換えていない")

    print("[wingastro] 完了: %d 点" % len(want))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
