# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wing1d_gallery — 記事の「信号・音響・1D ウィング」展示を作る。

``tools/gen_visionlab_video.py`` と同じ流儀で組んである。

  * **数字はすべてその場で op を呼んで得た実測値**。図に焼く値は決め打ちを 1 つも
    含まない(文字列は毎フレームの計算結果を整形しただけ)。
  * **描画は Fullseye 自身の ``imagedraw`` op と numpy 合成のみ**。波形もスペクトルも
    ``draw_line`` / ``draw_polyline`` / ``draw_circle`` / ``draw_markers`` で描く。
    **matplotlib は使わない**。文字だけは Fullseye にテキスト描画 op が無いため
    PIL の ``ImageDraw.text``(数値ラベル専用)。
  * **決定的**。乱数は seed 固定、掃引格子も固定なので、同じコマンドは同じ
    バイト列を返す(``--verify`` で 2 回生成して SHA-256 を突き合わせる)。
  * **アニメは静止フレームだけで意味が分かる**ように、軸・単位・凡例・現在値を
    毎フレーム焼き込む。

展示は 12 点(GIF 9 / PNG 3):

  1. ``defect_not_in_raw``    PNG  欠陥周波数は生スペクトルに無い
  2. ``kurtosis_band``        GIF  スペクトルカートシスが復調帯域を選ぶ
  3. ``window_sweep``         GIF  窓長を間違えると負の尖度が出る
  4. ``order_tracking``       GIF  次数比分析 — 角度領域で立場が逆転する
  5. ``bearing_geometry``     GIF  軸受の幾何から欠陥周波数
  6. ``weighting_ac``         GIF  A 特性・C 特性の重み付け(1 kHz が構成上 0 dB)
  7. ``funct1d_truth``        PNG  funct1d の解析真値
  8. ``smoothing_tradeoff``   GIF  平滑化のトレードオフ
  9. ``aliasing``             GIF  サンプリングとエイリアシング
 10. ``profile_sources``      PNG  1D プロファイルはどこから来るか
 11. ``peak_match``           GIF  極値検出と照合
 12. ``envelope_truncation``  GIF  包絡線の端が切れると 76 % 間違う

使い方::

    py -3.11 tools/gen_wing1d_gallery.py                       # 全部
    py -3.11 tools/gen_wing1d_gallery.py --only aliasing,peak_match
    py -3.11 tools/gen_wing1d_gallery.py --verify              # 決定性の検査
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np

# スクリプト直実行でも動くよう repo ルートと tools/ を sys.path に足す。
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

import acoustics as A            # noqa: E402  音響状態監視 op
import dsp                       # noqa: E402  基本 DSP
import funct1d as F              # noqa: E402  1-D 関数代数(HALCON funct_1d)
import imagedraw                 # noqa: E402  Fullseye の描画 op(唯一の描画経路)
import interferometry as I       # noqa: E402  コヒーレンス走査(包絡線の切断)
import measure                   # noqa: E402  2D 測定線
import volprobe                  # noqa: E402  3D プローブ

# 束ね方の共通部品(著者提供・自己テスト済み)。
#   contact_sheet = 並べて比べる / flipbook = 同寸で工程が進む / 原寸 1 枚 = 主張そのもの
from exhibit_tile import (contact_sheet, flipbook, markdown,   # noqa: E402
                          markdown_animation, save_animation, save_exhibit)

ASSETS = os.path.join(_ROOT, "docs", "articles", "assets")
MEDIA = os.path.join(ASSETS, "media")
THUMBS = os.path.join(ASSETS, "thumbs")
EXHIBITS = os.path.join(_ROOT, "docs", "articles", "exhibits")
SAMPLES_IMG = os.path.join(_ROOT, "studio_assets", "sample_images")
RAW_BASE = ("https://raw.githubusercontent.com/furuse-kazufumi/fullseye/"
            "master/docs/articles/assets/")
THUMB_W = 720

# --------------------------------------------------------------------------- #
# 配色 — 赤緑の対で意味を担わせない(色覚に依らず読める組み合わせ)              #
# --------------------------------------------------------------------------- #
C_BG = (0.055, 0.062, 0.075)
C_PANEL = (0.098, 0.108, 0.128)
C_PANEL2 = (0.078, 0.086, 0.104)
C_TEXT = (0.87, 0.88, 0.85)
C_DIM = (0.50, 0.53, 0.57)
C_AXIS = (0.42, 0.45, 0.50)
C_A = (0.35, 0.72, 1.00)      # 第 1 系列(青)
C_B = (0.98, 0.80, 0.30)      # 第 2 系列(琥珀)
C_C = (0.16, 0.86, 0.78)      # 第 3 系列(青緑)
C_D = (0.72, 0.55, 0.98)      # 第 4 系列(紫)
C_E = (1.00, 0.55, 0.42)      # 強調(珊瑚)
C_TRUE = (0.95, 0.95, 0.92)   # 真値
C_WARN = (0.90, 0.45, 0.42)   # 「黙って間違う」領域

GIF_W, GIF_H = 1000, 620


# --------------------------------------------------------------------------- #
# 描画の下ごしらえ                                                              #
# --------------------------------------------------------------------------- #
_FONT_CACHE: dict = {}


def _font(size: int = 12, bold: bool = False):
    """等幅フォント(数値が桁で揃うので読み取りやすい)。無ければ既定へ退避。"""
    key = (size, bold)
    if key not in _FONT_CACHE:
        from PIL import ImageFont
        path = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except OSError:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def _to_u8(rgb: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(rgb) * 255.0 + 0.5, 0, 255).astype(np.uint8)


class Ink:
    """``imagedraw`` op で 1 枚のステンシル(H,W)を描き、まとめて 1 色で焼く。

    RGB キャンバスへ op を直接掛けると 1 呼び出しごとに 3 面ぶんのコピーが出る。
    同じ色の要素を 1 枚のステンシルに溜めてから numpy で合成するほうが速く、
    **描線そのものは全部 Fullseye の op** が行う(ここでは色を持たないだけ)。
    """

    def __init__(self, h: int, w: int):
        self.a = np.zeros((h, w), np.float64)

    def line(self, p0, p1, width: int = 1) -> "Ink":
        self.a = imagedraw.draw_line(self.a, p0, p1, color=1.0, width=width)
        return self

    def poly(self, pts, width: int = 1, closed: bool = False) -> "Ink":
        pts = np.asarray(pts, np.float64).reshape(-1, 2)
        if pts.shape[0] >= 2:
            self.a = imagedraw.draw_polyline(self.a, pts, color=1.0, width=width,
                                             closed=closed)
        return self

    def circle(self, centre, radius, width: int = 1, fill: bool = False) -> "Ink":
        self.a = imagedraw.draw_circle(self.a, centre, radius, color=1.0,
                                       width=width, fill=fill)
        return self

    def marks(self, pts, size: int = 5, shape: str = "cross", width: int = 1) -> "Ink":
        pts = np.asarray(pts, np.float64).reshape(-1, 2)
        if pts.shape[0]:
            self.a = imagedraw.draw_markers(self.a, pts, color=1.0, size=size,
                                            shape=shape, width=width)
        return self

    def dashed(self, p0, p1, width: int = 1, dash: float = 7.0,
               gap: float = 6.0) -> "Ink":
        """破線 — ``draw_line`` を短い区間に分けて重ねる(破線 op は無いので)。"""
        x0, y0 = float(p0[0]), float(p0[1])
        x1, y1 = float(p1[0]), float(p1[1])
        length = float(np.hypot(x1 - x0, y1 - y0))
        if length < 1e-9:
            return self
        t = 0.0
        while t < length:
            t2 = min(t + dash, length)
            self.line((x0 + (x1 - x0) * t / length, y0 + (y1 - y0) * t / length),
                      (x0 + (x1 - x0) * t2 / length, y0 + (y1 - y0) * t2 / length),
                      width=width)
            t = t2 + gap
        return self

    def mask(self) -> np.ndarray:
        return self.a > 0.5


class Fig:
    """1 フレーム。RGB 下地 + ステンシル合成 + 最後にテキストを焼く。"""

    def __init__(self, w: int, h: int, bg=C_BG):
        self.w, self.h = int(w), int(h)
        self.rgb = np.empty((self.h, self.w, 3), np.float64)
        self.rgb[:, :] = np.asarray(bg, np.float64)
        self._labels: list = []

    def box(self, x0, y0, x1, y1, color) -> None:
        self.rgb[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1), :] = \
            np.asarray(color, np.float64)

    def blit(self, x0, y0, rgb: np.ndarray) -> None:
        h, w = rgb.shape[:2]
        self.rgb[int(y0):int(y0) + h, int(x0):int(x0) + w, :] = rgb

    def ink(self) -> Ink:
        return Ink(self.h, self.w)

    def stamp(self, ink: Ink, color, alpha: float = 1.0) -> None:
        m = ink.mask()
        if not m.any():
            return
        c = np.asarray(color, np.float64)
        if alpha >= 1.0:
            self.rgb[m] = c
        else:
            self.rgb[m] = (1.0 - alpha) * self.rgb[m] + alpha * c

    def text(self, x, y, s, color=C_TEXT, size: int = 12, bold: bool = False) -> None:
        self._labels.append((int(x), int(y), str(s), color, int(size), bool(bold)))

    def u8(self) -> np.ndarray:
        """テキストを焼いて uint8 フレームにする(Fullseye にテキスト op は無い)。"""
        from PIL import Image, ImageDraw
        im = Image.fromarray(_to_u8(self.rgb))
        d = ImageDraw.Draw(im)
        for x, y, s, col, size, bold in self._labels:
            d.text((x, y), s, fill=tuple(int(round(255 * c)) for c in col),
                   font=_font(size, bold))
        return np.asarray(im)


class Ax:
    """データ座標 → 画素座標の写像 + 枠・目盛り・曲線。"""

    def __init__(self, fig: Fig, x0, y0, x1, y1, xlim, ylim,
                 logx: bool = False, logy: bool = False):
        self.fig = fig
        self.x0, self.y0, self.x1, self.y1 = int(x0), int(y0), int(x1), int(y1)
        self.xlo, self.xhi = float(xlim[0]), float(xlim[1])
        self.ylo, self.yhi = float(ylim[0]), float(ylim[1])
        self.logx, self.logy = bool(logx), bool(logy)

    # -- 写像 ------------------------------------------------------------- #
    def X(self, v):
        v = np.asarray(v, np.float64)
        if self.logx:
            v = np.clip(v, min(self.xlo, self.xhi), None)
            t = (np.log10(np.maximum(v, 1e-300)) - np.log10(self.xlo)) / \
                (np.log10(self.xhi) - np.log10(self.xlo))
        else:
            t = (v - self.xlo) / (self.xhi - self.xlo)
        return self.x0 + (self.x1 - self.x0) * np.clip(t, -0.02, 1.02)

    def Y(self, v):
        v = np.asarray(v, np.float64)
        if self.logy:
            v = np.clip(v, 1e-300, None)
            t = (np.log10(v) - np.log10(self.ylo)) / (np.log10(self.yhi) - np.log10(self.ylo))
        else:
            t = (v - self.ylo) / (self.yhi - self.ylo)
        return self.y1 - (self.y1 - self.y0) * np.clip(t, -0.02, 1.02)

    # -- 部品 ------------------------------------------------------------- #
    def panel(self, color=C_PANEL) -> None:
        self.fig.box(self.x0 - 1, self.y0 - 1, self.x1 + 2, self.y1 + 2, color)

    def frame(self, ink: Ink) -> Ink:
        ink.line((self.x0, self.y1), (self.x1, self.y1), width=1)
        ink.line((self.x0, self.y0), (self.x0, self.y1), width=1)
        return ink

    def curve(self, ink: Ink, xs, ys, width: int = 2) -> Ink:
        """曲線。画素列より点が多ければ列ごとの min/max に間引いて描く。

        間引きは **表示のため**であって値は変えない(極値は min/max として残る)。
        """
        px = np.asarray(self.X(np.asarray(xs, np.float64)), np.float64)
        py = np.asarray(self.Y(np.asarray(ys, np.float64)), np.float64)
        span = max(2, self.x1 - self.x0)
        if px.size <= 2 * span:
            return ink.poly(np.column_stack([px, py]), width=width)
        col = np.clip(np.round(px).astype(np.int64), self.x0, self.x1)
        uniq, inv = np.unique(col, return_inverse=True)
        lo = np.full(uniq.size, np.inf)
        hi = np.full(uniq.size, -np.inf)
        np.minimum.at(lo, inv, py)
        np.maximum.at(hi, inv, py)
        pts = np.empty((uniq.size * 2, 2), np.float64)
        pts[0::2, 0] = uniq
        pts[1::2, 0] = uniq
        pts[0::2, 1] = lo
        pts[1::2, 1] = hi
        return ink.poly(pts, width=width)

    def hline(self, ink: Ink, y, width: int = 1, dashed: bool = False) -> Ink:
        yy = float(self.Y(y))
        if dashed:
            return ink.dashed((self.x0, yy), (self.x1, yy), width=width)
        return ink.line((self.x0, yy), (self.x1, yy), width=width)

    def vline(self, ink: Ink, x, width: int = 1, dashed: bool = False) -> Ink:
        xx = float(self.X(x))
        if dashed:
            return ink.dashed((xx, self.y0), (xx, self.y1), width=width)
        return ink.line((xx, self.y0), (xx, self.y1), width=width)

    def xticks(self, ink: Ink, values, fmt="%g", color=C_DIM, size: int = 10,
               dy: int = 4) -> Ink:
        for v in values:
            xx = float(self.X(v))
            ink.line((xx, self.y1), (xx, self.y1 + 4), width=1)
            s = fmt % v
            self.fig.text(xx - 3.1 * len(s), self.y1 + dy + 2, s, color, size)
        return ink

    def yticks(self, ink: Ink, values, fmt="%g", color=C_DIM, size: int = 10) -> Ink:
        for v in values:
            yy = float(self.Y(v))
            ink.line((self.x0 - 4, yy), (self.x0, yy), width=1)
            s = fmt % v
            self.fig.text(self.x0 - 8 - 6.2 * len(s), yy - 7, s, color, size)
        return ink


def _colormap(t: np.ndarray) -> np.ndarray:
    """0..1 → RGB。4 点の線形補間(matplotlib を使わないので自前)。"""
    stops = np.array([[0.043, 0.055, 0.098],
                      [0.106, 0.310, 0.545],
                      [0.176, 0.706, 0.694],
                      [0.984, 0.898, 0.494]], np.float64)
    t = np.clip(np.asarray(t, np.float64), 0.0, 1.0) * (len(stops) - 1)
    i = np.clip(np.floor(t).astype(int), 0, len(stops) - 2)
    f = (t - i)[..., None]
    return stops[i] * (1.0 - f) + stops[i + 1] * f


def _resize_nn(img: np.ndarray, h: int, w: int) -> np.ndarray:
    """最近傍の拡大縮小(補間しない — 画素の粗さ自体が情報なので)。"""
    r = np.clip((np.arange(h) + 0.5) * img.shape[0] / h, 0, img.shape[0] - 1).astype(int)
    c = np.clip((np.arange(w) + 0.5) * img.shape[1] / w, 0, img.shape[1] - 1).astype(int)
    return img[np.ix_(r, c)] if img.ndim == 2 else img[np.ix_(r, c, np.arange(img.shape[2]))]


def _gray_rgb(g: np.ndarray) -> np.ndarray:
    return np.repeat(np.clip(np.asarray(g, np.float64), 0.0, 1.0)[:, :, None], 3, axis=2)


# --------------------------------------------------------------------------- #
# 書き出しと読み戻し検証                                                        #
# --------------------------------------------------------------------------- #
def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save_png(frame_u8: np.ndarray, name: str, log) -> dict:
    """原寸 1 枚。``exhibit_tile.save_exhibit`` が PNG + 幅 720 サムネを書く。

    記事側は必ず**サムネイル表示 + クリックで原寸**にする(``markdown()`` がその形)。
    """
    stem = f"wing1d_{name}"
    r = save_exhibit(frame_u8, stem)
    out = {"kind": "png", "path": r["png"], "thumb": r["thumb"], "frames": 1,
           "shape": (r["size"][1], r["size"][0], 3), "bytes": r["png_bytes"],
           "thumb_bytes": r["thumb_bytes"], "sha256": r["png_sha256"],
           "stem": stem}
    log(f"    png  {stem}.png  {r['size'][0]}x{r['size'][1]}  "
        f"{out['bytes'] / 1e3:.0f} kB  thumb {out['thumb_bytes'] / 1e3:.0f} kB")
    return out


def save_flipbook(frames_u8, name: str, labels, *, ms: int, hold_ms: int,
                  title=None, log=print) -> dict:
    """コマ送り GIF。``exhibit_tile.flipbook`` で **各コマに工程名と i/N の進捗バー**を
    焼いてから ``save_animation`` で書く(読み戻してフレーム数を照合してくれる)。

    止まった 1 コマだけ見ても意味が分かることを、この 2 つが構造的に保証する。
    """
    stem = f"wing1d_{name}"
    book = flipbook(list(frames_u8), list(labels), title=title)
    r = save_animation(book, stem, duration_ms=ms, hold_last_ms=hold_ms)
    out = {"kind": "gif", "path": r["gif"], "thumb": r["thumb"], "frames": r["frames"],
           "shape": (r["size"][1], r["size"][0], 3), "bytes": r["gif_bytes"],
           "ms": ms, "hold_ms": hold_ms, "sha256": r["gif_sha256"], "stem": stem}
    log(f"    gif  {stem}.gif  {r['frames']} frames (read back)  "
        f"{r['size'][0]}x{r['size'][1]}  {out['bytes'] / 1e6:.2f} MB  "
        f"{ms} ms/frame")
    if out["bytes"] > 3.0e6:
        log(f"    !! {stem}.gif is {out['bytes'] / 1e6:.2f} MB (> 3 MB target)")
    return out


def save_sheet(panels, name: str, labels, *, ncols: int, title: str,
               panel_px: int = 420, log=print) -> dict:
    """タイル(コンタクトシート)。並べて比べるものを 1 点に束ねる。"""
    stem = f"wing1d_{name}"
    sheet = contact_sheet(list(panels), list(labels), ncols=ncols, title=title,
                          panel_px=panel_px)
    r = save_exhibit(sheet, stem)
    out = {"kind": "sheet", "path": r["png"], "thumb": r["thumb"],
           "frames": len(panels), "shape": (r["size"][1], r["size"][0], 3),
           "bytes": r["png_bytes"], "thumb_bytes": r["thumb_bytes"],
           "sha256": r["png_sha256"], "stem": stem, "ncols": ncols}
    log(f"    tile {stem}.png  {len(panels)} panels  "
        f"{r['size'][0]}x{r['size'][1]}  {out['bytes'] / 1e3:.0f} kB")
    return out


# --------------------------------------------------------------------------- #
# 共通の版面部品                                                                #
# --------------------------------------------------------------------------- #
def _header(fig: Fig, title: str, sub: str = "") -> None:
    fig.box(0, 0, fig.w, 34, (0.085, 0.095, 0.115))
    fig.text(14, 7, title, C_TEXT, 15, True)
    if sub:
        fig.text(14 + 9.0 * len(title) + 18, 10, sub, C_DIM, 12, False)


def _legend(fig: Fig, x: int, y: int, items, size: int = 11,
            backing: bool = True) -> None:
    """凡例。曲線の上に重なっても読めるよう、既定で下敷きの箱を敷く。"""
    if backing and items:
        w = 4 + int(round(0.62 * size * (4 + max(len(s) for s, _ in items))))
        fig.box(x - 6, y - 4, x + w, y + 15 * len(items) + 2, (0.06, 0.07, 0.085))
    for i, (label, col) in enumerate(items):
        fig.text(x, y + i * 15, "--- " + label, col, size, True)


# =========================================================================== #
# 展示 1: 欠陥周波数は生スペクトルに無い                            (PNG)      #
# =========================================================================== #
def ex_defect_not_in_raw(log):
    fs = 25600.0
    dur = 1.0
    fc, fd, m = 3000.0, 107.0, 0.5
    x = A.synthesize_bearing_signal(fs, dur, carrier_hz=fc, defect_hz=fd,
                                    modulation=m, mode="am")
    freqs, mag = dsp.spectrum(x, fs)
    # dsp.spectrum は素の |rfft| を返すので、片側振幅にするには 2/N が要る。
    amp = mag * (2.0 / x.size)
    res_hz = fs / x.size

    def at(hz):
        i = int(np.argmin(np.abs(freqs - hz)))
        return float(freqs[i]), float(amp[i])

    f_defect, a_defect = at(fd)
    f_car, a_car = at(fc)
    f_lo, a_lo = at(fc - fd)
    f_hi, a_hi = at(fc + fd)
    env = A.envelope_spectrum(x, fs, 2000.0, 4000.0)
    i_env = int(np.argmin(np.abs(env["freqs"] - fd)))

    log(f"  raw @{f_defect:g} Hz = {a_defect:.4e}   carrier @{f_car:g} = {a_car:.6f}   "
        f"sidebands {a_lo:.6f} / {a_hi:.6f}")
    log(f"  envelope peak {env['peak_freq']:.6f} Hz amp {env['peak_amplitude']:.6f} "
        f"band_fraction {env['band_fraction']:.6f} prominence {env['peak_prominence']:.1f}")

    W, H = 1120, 780
    fig = Fig(W, H)
    _header(fig, "The defect frequency is not in the raw spectrum",
            f"AM bearing signal: carrier {fc:g} Hz, defect {fd:g} Hz, m = {m:g}, "
            f"{fs:g} Hz x {dur:g} s")

    # -- 上: 生スペクトル(片側振幅) ----------------------------------------- #
    ax1 = Ax(fig, 92, 78, W - 190, 300, (0.0, 4000.0), (0.0, 1.12))
    ax1.panel()
    ink = fig.ink()
    ax1.frame(ink)
    ax1.xticks(ink, [0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000], "%.0f")
    ax1.yticks(ink, [0.0, 0.25, 0.5, 0.75, 1.0], "%.2f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax1.curve(ink, freqs, amp, width=2)
    fig.stamp(ink, C_A)
    ink = fig.ink()
    ax1.vline(ink, fd, width=2, dashed=True)
    fig.stamp(ink, C_WARN)
    ink = fig.ink()
    ink.marks([(ax1.X(f_car), ax1.Y(a_car)), (ax1.X(f_lo), ax1.Y(a_lo)),
               (ax1.X(f_hi), ax1.Y(a_hi))], size=7, shape="cross", width=2)
    fig.stamp(ink, C_TRUE)
    fig.text(96, 54, "raw single-sided amplitude spectrum  (dsp.spectrum x 2/N)",
             C_TEXT, 13, True)
    fig.text(ax1.X(fd) + 6, 84, f"defect {fd:g} Hz", C_WARN, 11, True)
    fig.text(ax1.X(fd) + 6, 100, f"amplitude {a_defect:.3e}", C_WARN, 11, True)
    fig.text(ax1.X(fd) + 6, 116, "= nothing is there", C_WARN, 11, True)
    fig.text(ax1.X(f_car) - 62, ax1.Y(a_car) - 22, f"carrier {f_car:g} Hz {a_car:.6f}",
             C_TRUE, 11, True)
    fig.text(ax1.X(f_lo) - 118, ax1.Y(a_lo) - 20, f"{f_lo:g} Hz {a_lo:.6f}", C_TRUE, 11, True)
    fig.text(ax1.X(f_hi) + 12, ax1.Y(a_hi) - 20, f"{f_hi:g} Hz {a_hi:.6f}", C_TRUE, 11, True)
    fig.text(ax1.X(f_hi) + 12, ax1.Y(a_hi) - 4, "= m/2 exactly", C_DIM, 11, False)
    fig.text(W - 176, 96, "the energy sits at", C_DIM, 11, False)
    fig.text(W - 176, 112, "carrier +- defect,", C_DIM, 11, False)
    fig.text(W - 176, 128, "never at the defect", C_DIM, 11, False)
    fig.text(W - 176, 144, "rate itself.", C_DIM, 11, False)
    fig.text(30, 176, "amplitude", C_DIM, 11, False)
    fig.text(W - 300, 306, "frequency [Hz] ->", C_DIM, 11, False)

    # -- 下: 包絡線スペクトル ----------------------------------------------- #
    ax2 = Ax(fig, 92, 400, W - 190, 640, (0.0, 500.0), (0.0, 0.58))
    ax2.panel()
    ink = fig.ink()
    ax2.frame(ink)
    ax2.xticks(ink, [0, 107, 200, 214, 300, 321, 400, 500], "%.0f")
    ax2.yticks(ink, [0.0, 0.1, 0.2, 0.3, 0.4, 0.5], "%.2f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax2.curve(ink, env["freqs"], env["magnitude"], width=2)
    fig.stamp(ink, C_C)
    ink = fig.ink()
    ax2.vline(ink, fd, width=2, dashed=True)
    fig.stamp(ink, C_WARN)
    ink = fig.ink()
    ink.marks([(ax2.X(env["peak_freq"]), ax2.Y(env["peak_amplitude"]))],
              size=8, shape="cross", width=2)
    fig.stamp(ink, C_TRUE)
    fig.text(96, 376, "envelope spectrum of the 2000-4000 Hz band  "
                      "(acoustics.envelope_spectrum)", C_TEXT, 13, True)
    fig.text(ax2.X(fd) + 10, 412, f"peak {env['peak_freq']:.6f} Hz", C_TRUE, 12, True)
    fig.text(ax2.X(fd) + 10, 430, f"amplitude {env['peak_amplitude']:.6f}", C_TRUE, 12, True)
    fig.text(ax2.X(fd) + 10, 448, f"= the modulation depth m = {m:g}", C_C, 11, True)
    fig.text(30, 500, "amplitude", C_DIM, 11, False)
    fig.text(W - 300, 646, "envelope frequency [Hz] ->", C_DIM, 11, False)
    fig.text(W - 176, 418, "same record,", C_DIM, 11, False)
    fig.text(W - 176, 434, "demodulated.", C_DIM, 11, False)
    fig.text(W - 176, 450, "the line is there", C_C, 11, True)
    fig.text(W - 176, 466, "and it is exact.", C_C, 11, True)

    # -- 数表 ---------------------------------------------------------------- #
    fig.box(30, 676, W - 30, H - 14, C_PANEL2)
    rows = [
        ("resolution", f"{res_hz:.6f} Hz/bin ({x.size} samples)",
         f"envelope resolution {env['resolution_hz']:.6f} Hz/bin"),
        (f"raw amplitude at {fd:g} Hz", f"{a_defect:.4e}", "no component exists"),
        (f"envelope amplitude at {fd:g} Hz",
         f"{env['magnitude'][i_env]:.6f}", f"peak prominence {env['peak_prominence']:.1f}"),
        ("band_fraction", f"{env['band_fraction']:.6f}",
         "how much of the record lives in the demodulation band"),
    ]
    for i, (k, v, note) in enumerate(rows):
        y = 682 + i * 21
        fig.text(40, y, k, C_DIM, 12, False)
        fig.text(300, y, v, C_TEXT, 12, True)
        fig.text(560, y, note, C_DIM, 12, False)

    frame = fig.u8()
    info = save_png(frame, "defect_not_in_raw", log)
    facts = {
        "rate_hz": fs, "duration_s": dur, "carrier_hz": fc, "defect_hz": fd,
        "modulation": m, "resolution_hz": res_hz,
        "raw_amplitude_at_defect": a_defect, "raw_amplitude_at_carrier": a_car,
        "raw_sideband_lower": a_lo, "raw_sideband_upper": a_hi,
        "envelope_peak_freq": env["peak_freq"],
        "envelope_peak_amplitude": env["peak_amplitude"],
        "envelope_band_fraction": env["band_fraction"],
        "envelope_prominence": env["peak_prominence"],
        "ops": ["synthesize_bearing_signal", "spectrum", "envelope_spectrum"],
    }
    return info, facts


# =========================================================================== #
# 展示 2: スペクトルカートシスが復調帯域を選ぶ                      (GIF)      #
# =========================================================================== #
def ex_kurtosis_band(log):
    fs = 25600.0
    dur = 1.0
    fc, fd = 3000.0, 107.0
    x = A.synthesize_bearing_signal(fs, dur, carrier_hz=fc, defect_hz=fd,
                                    modulation=0.5, mode="impulse",
                                    noise_sigma=0.15, seed=3)
    sk = A.spectral_kurtosis(x, fs, win=64)
    tr = A.stft(x, fs, win=256, hop=128)
    inner = tr["interior"]
    z = np.abs(tr["spectra"][:, inner])
    times = tr["times"][inner]
    plane = np.log10(z + 1e-6)
    lo, hi = float(np.percentile(plane, 5.0)), float(plane.max())
    plane_rgb = _colormap((plane - lo) / max(1e-12, hi - lo))[::-1]   # 低周波を下に

    width_hz = 800.0
    centres = np.linspace(600.0, 11800.0, 32)
    log(f"  SK win=64: max {sk['max_kurtosis']:.4f} at {sk['max_freq']:g} Hz "
        f"(bin {sk['bin_hz']:g} Hz, {sk['n_frames']} interior frames, "
        f"estimator sigma {sk['noise_sigma']:.4f})")
    log(f"  STFT plane: {z.shape[0]} bins x {z.shape[1]} interior frames "
        f"(of {tr['n_frames']}), t {times[0]:.4f}..{times[-1]:.4f} s")

    rows = []
    for c in centres:
        blo, bhi = c - width_hz / 2.0, c + width_hz / 2.0
        e = A.envelope_spectrum(x, fs, blo, bhi)
        rows.append({"centre": float(c), "low": float(blo), "high": float(bhi),
                     "peak_freq": e["peak_freq"], "peak_amp": e["peak_amplitude"],
                     "band_fraction": e["band_fraction"],
                     "prominence": e["peak_prominence"],
                     "freqs": e["freqs"], "magnitude": e["magnitude"]})
    best = int(np.argmax([r["band_fraction"] for r in rows]))
    sk_pick = int(np.argmin(np.abs(centres - sk["max_freq"])))
    log(f"  band sweep: strongest band_fraction {rows[best]['band_fraction']:.4f} at "
        f"{rows[best]['centre']:.0f} Hz; SK picked {sk['max_freq']:g} Hz "
        f"(frame {sk_pick}, band_fraction {rows[sk_pick]['band_fraction']:.4f})")

    W, H = GIF_W, GIF_H
    frames, labels = [], []
    for k, r in enumerate(rows):
        labels.append(f"復調帯域 {r['low']:.0f}–{r['high']:.0f} Hz  /  包絡線ピーク "
                      f"{r['peak_freq']:.1f} Hz  /  band_fraction {r['band_fraction']:.4f}"
                      + ("  ← SK が選んだ帯域" if k == sk_pick else ""))
        fig = Fig(W, H)
        _header(fig, "Spectral kurtosis picks the demodulation band",
                f"impulse bearing signal, resonance {fc:g} Hz, defect {fd:g} Hz, "
                f"noise sigma 0.15")
        # 左: 時間周波数平面
        axp = Ax(fig, 76, 62, 560, 330, (float(times[0]), float(times[-1])),
                 (0.0, fs / 2.0))
        axp.panel(C_PANEL2)
        fig.blit(axp.x0, axp.y0, _resize_nn(plane_rgb, axp.y1 - axp.y0, axp.x1 - axp.x0))
        ink = fig.ink()
        axp.frame(ink)
        axp.xticks(ink, [0.0, 0.25, 0.5, 0.75, 1.0], "%.2f")
        axp.yticks(ink, [0, 3200, 6400, 9600, 12800], "%.0f")
        fig.stamp(ink, C_AXIS)
        # 帯域の帯を平面に重ねる
        ink = fig.ink()
        ink.line((axp.x0, axp.Y(r["low"])), (axp.x1, axp.Y(r["low"])), width=2)
        ink.line((axp.x0, axp.Y(r["high"])), (axp.x1, axp.Y(r["high"])), width=2)
        fig.stamp(ink, C_B)
        ink = fig.ink()
        ink.dashed((axp.x0, axp.Y(fc)), (axp.x1, axp.Y(fc)), width=1, dash=6, gap=6)
        fig.stamp(ink, C_TRUE)
        fig.text(80, 44, "STFT magnitude (log), interior frames only", C_TEXT, 12, True)
        fig.text(24, 180, "Hz", C_DIM, 11)
        fig.text(axp.x1 - 116, axp.y1 + 22, "time [s] ->", C_DIM, 11)
        fig.text(axp.x0 + 8, axp.Y(fc) - 16, f"true resonance {fc:g} Hz", C_TRUE, 11, True)

        # 右: SK 曲線(周波数を縦に取り、平面と軸を揃える)
        axk = Ax(fig, 600, 62, 800, 330, (-1.5, max(4.0, sk["max_kurtosis"] * 1.15)),
                 (0.0, fs / 2.0))
        axk.panel(C_PANEL)
        ink = fig.ink()
        axk.frame(ink)
        axk.xticks(ink, [-1, 0, 1, 2, 3], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        ink.poly(np.column_stack([axk.X(sk["kurtosis"]), axk.Y(sk["freqs"])]), width=2)
        fig.stamp(ink, C_D)
        ink = fig.ink()
        ink.line((axk.X(0.0), axk.y0), (axk.X(0.0), axk.y1), width=1)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        ink.marks([(axk.X(sk["max_kurtosis"]), axk.Y(sk["max_freq"]))],
                  size=7, shape="cross", width=2)
        fig.stamp(ink, C_E)
        fig.text(604, 44, "spectral kurtosis", C_TEXT, 12, True)
        fig.text(604, 344, f"max {sk['max_kurtosis']:.4f} at {sk['max_freq']:.0f} Hz",
                 C_E, 11, True)
        fig.text(604, 360, f"win {sk['win']} = {sk['window_seconds'] * 1e3:.2f} ms, "
                           f"bin {sk['bin_hz']:.0f} Hz", C_DIM, 11)
        fig.text(604, 376, f"estimator sigma {sk['noise_sigma']:.4f}", C_DIM, 11)

        # 右端: 読み取り値
        fig.box(818, 62, W - 14, 332, C_PANEL2)
        fig.text(828, 70, "current band", C_TEXT, 12, True)
        fig.text(828, 92, f"{r['low']:.0f} - {r['high']:.0f} Hz", C_B, 13, True)
        fig.text(828, 116, "envelope peak", C_DIM, 11)
        fig.text(828, 132, f"{r['peak_freq']:.3f} Hz", C_C, 13, True)
        fig.text(828, 156, "peak amplitude", C_DIM, 11)
        fig.text(828, 172, f"{r['peak_amp']:.5f}", C_TEXT, 12, True)
        fig.text(828, 196, "band_fraction", C_DIM, 11)
        fig.text(828, 212, f"{r['band_fraction']:.5f}", C_TEXT, 12, True)
        fig.text(828, 236, "prominence", C_DIM, 11)
        fig.text(828, 252, f"{r['prominence']:.1f}", C_TEXT, 12, True)
        if k == sk_pick:
            fig.text(828, 282, "<- the band SK chose", C_E, 11, True)
        fig.text(828, 302, f"defect truth {fd:g} Hz", C_DIM, 11)

        # 下: この帯域の包絡線スペクトル
        axe = Ax(fig, 76, 396, W - 30, 552, (0.0, 600.0),
                 (0.0, max(0.02, max(rr["peak_amp"] for rr in rows) * 1.15)))
        axe.panel()
        ink = fig.ink()
        axe.frame(ink)
        axe.xticks(ink, [0, 107, 214, 321, 428, 500, 600], "%.0f")
        axe.yticks(ink, [0.0, 0.05, 0.10, 0.15], "%.2f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axe.curve(ink, r["freqs"], r["magnitude"], width=2)
        fig.stamp(ink, C_C)
        ink = fig.ink()
        axe.vline(ink, fd, width=1, dashed=True)
        fig.stamp(ink, C_WARN)
        ink = fig.ink()
        ink.marks([(axe.X(r["peak_freq"]), axe.Y(r["peak_amp"]))], size=7,
                  shape="cross", width=2)
        fig.stamp(ink, C_TRUE)
        fig.text(80, 378, "envelope spectrum of the current band", C_TEXT, 12, True)
        fig.text(axe.X(fd) + 6, 400, f"defect truth {fd:g} Hz", C_WARN, 11, True)
        fig.text(24, 460, "amp", C_DIM, 11)
        fig.text(W - 250, 558, "envelope frequency [Hz] ->", C_DIM, 11)
        fig.text(14, H - 26,
                 "the peak stays at the defect rate everywhere; what moves is "
                 "band_fraction - how much of the record is actually in the band.",
                 C_DIM, 12)
        frames.append(fig.u8())

    info = save_flipbook(frames, "kurtosis_band", labels, ms=220, hold_ms=1400,
                         log=log)
    facts = {
        "sk_max_kurtosis": sk["max_kurtosis"], "sk_max_freq": sk["max_freq"],
        "sk_win": sk["win"], "sk_window_ms": sk["window_seconds"] * 1e3,
        "sk_bin_hz": sk["bin_hz"], "sk_frames": sk["n_frames"],
        "sk_noise_sigma": sk["noise_sigma"],
        "stft_bins": int(z.shape[0]), "stft_interior_frames": int(z.shape[1]),
        "stft_total_frames": int(tr["n_frames"]),
        "band_width_hz": width_hz,
        "best_band_centre": rows[best]["centre"],
        "best_band_fraction": rows[best]["band_fraction"],
        "sk_band_fraction": rows[sk_pick]["band_fraction"],
        "sk_band_peak_freq": rows[sk_pick]["peak_freq"],
        "worst_band_fraction": min(r["band_fraction"] for r in rows),
        "ops": ["synthesize_bearing_signal", "stft", "spectral_kurtosis",
                "envelope_spectrum"],
    }
    return info, facts


# =========================================================================== #
# 展示 3: 窓長を間違えると負の尖度が出る                            (GIF)      #
# =========================================================================== #
def ex_window_sweep(log):
    fs = 25600.0
    fc, fd = 3000.0, 107.0
    period_ms = 1000.0 / fd
    x = A.synthesize_bearing_signal(fs, 1.0, carrier_hz=fc, defect_hz=fd,
                                    modulation=0.5, mode="impulse")
    wins = [8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512]
    rows = []
    for w in wins:
        sk = A.spectral_kurtosis(x, fs, win=w)
        rows.append({"win": w, "ms": sk["window_seconds"] * 1e3,
                     "max": sk["max_kurtosis"], "at": sk["max_freq"],
                     "bin": sk["bin_hz"], "frames": sk["n_frames"],
                     "sigma": sk["noise_sigma"],
                     "freqs": sk["freqs"], "k": sk["kurtosis"]})
        log(f"  win={w:4d}  {rows[-1]['ms']:6.2f} ms  max SK {rows[-1]['max']:+9.4f} "
            f"at {rows[-1]['at']:8.1f} Hz  bin {rows[-1]['bin']:7.1f} Hz")
    bad = [r for r in rows if r["max"] < 0.0]
    kmax = max(r["max"] for r in rows)

    seg_n = int(round(0.05 * fs))                      # 50 ms の抜粋
    seg = x[:seg_n]
    seg_t = np.arange(seg_n) / fs * 1e3

    W, H = GIF_W, GIF_H
    frames, labels, hold = [], [], 2
    for r in rows:
        fig = Fig(W, H)
        _header(fig, "Get the window wrong and the kurtosis reports the opposite",
                f"impulses every {period_ms:.3f} ms (defect {fd:g} Hz), "
                f"true resonance {fc:g} Hz, {fs:g} Hz")
        # 上: 波形 + 窓の長さ
        axw = Ax(fig, 76, 66, W - 30, 210, (0.0, 50.0),
                 (-float(np.abs(seg).max()) * 1.1, float(np.abs(seg).max()) * 1.1))
        axw.panel(C_PANEL2)
        ink = fig.ink()
        axw.frame(ink)
        axw.xticks(ink, [0, 10, 20, 30, 40, 50], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axw.curve(ink, seg_t, seg, width=1)
        fig.stamp(ink, C_A)
        # 衝撃の到来時刻(合成の真値)
        ink = fig.ink()
        for j in range(0, int(50.0 / period_ms) + 1):
            axw.vline(ink, j * period_ms, width=1, dashed=True)
        fig.stamp(ink, C_TRUE, alpha=0.55)
        # 窓の長さを実寸で焼く
        ink = fig.ink()
        wx0, wx1 = axw.X(2.0), axw.X(2.0 + r["ms"])
        ink.poly([(wx0, axw.y0 + 6), (wx1, axw.y0 + 6), (wx1, axw.y0 + 22),
                  (wx0, axw.y0 + 22)], width=2, closed=True)
        fig.stamp(ink, C_B)
        fig.text(80, 48, "signal (first 50 ms) with the analysis window drawn to scale",
                 C_TEXT, 12, True)
        fig.text(wx1 + 8, axw.y0 + 5, f"win = {r['win']} = {r['ms']:.2f} ms", C_B, 12, True)
        fig.text(axw.X(period_ms) + 4, axw.y1 - 30,
                 f"impact period {period_ms:.3f} ms", C_TRUE, 11, True)
        fig.text(W - 190, 216, "time [ms] ->", C_DIM, 11)

        # 中: SK 曲線
        axk = Ax(fig, 76, 280, W - 30, 486, (0.0, fs / 2.0),
                 (min(-1.2, min(rr["max"] for rr in rows) * 1.3), kmax * 1.12))
        axk.panel()
        ink = fig.ink()
        axk.frame(ink)
        axk.xticks(ink, [0, 2000, 4000, 6000, 8000, 10000, 12000], "%.0f")
        axk.yticks(ink, [-1, 0, 5, 10, 15, 20, 25, 30], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axk.hline(ink, 0.0, width=1)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        axk.curve(ink, r["freqs"], r["k"], width=2)
        fig.stamp(ink, C_D)
        ink = fig.ink()
        axk.vline(ink, fc, width=2, dashed=True)
        fig.stamp(ink, C_TRUE)
        ink = fig.ink()
        ink.marks([(axk.X(r["at"]), axk.Y(r["max"]))], size=8, shape="cross", width=2)
        fig.stamp(ink, C_E if r["max"] < 0 else C_B)
        fig.text(80, 262, "spectral kurtosis vs frequency", C_TEXT, 12, True)
        fig.text(axk.X(fc) + 6, 286, f"true resonance {fc:g} Hz", C_TRUE, 11, True)
        fig.text(30, 370, "SK", C_DIM, 11)
        fig.text(W - 220, 492, "frequency [Hz] ->", C_DIM, 11)

        # 下: 読み取り + 判定
        fig.box(76, 516, W - 30, H - 16, C_PANEL2)
        fig.text(88, 524, f"win {r['win']:4d}   window {r['ms']:6.2f} ms   "
                          f"bin {r['bin']:7.1f} Hz   {r['frames']} interior frames   "
                          f"estimator sigma {r['sigma']:.4f}", C_TEXT, 13, True)
        verdict = ("window LONGER than the impact period -> every frame holds an "
                   "impact -> the band looks stationary"
                   if r["ms"] >= period_ms else
                   "window shorter than the impact period -> impacts are resolved")
        fig.text(88, 548, verdict, C_E if r["ms"] >= period_ms else C_C, 12, True)
        col = C_E if r["max"] < 0 else C_B
        fig.text(88, 572, f"max SK {r['max']:+9.4f} at {r['at']:8.1f} Hz", col, 14, True)
        if r["max"] < 0:
            fig.text(400, 572, f"NEGATIVE, and {abs(r['at'] - fc):.0f} Hz away from the "
                               f"resonance. Nothing raised.", C_E, 12, True)
        else:
            fig.text(400, 572, f"|reported - true| = {abs(r['at'] - fc):.0f} Hz "
                               f"(one bin is {r['bin']:.0f} Hz)", C_DIM, 12, False)
        lab = (f"窓 {r['win']} = {r['ms']:.2f} ms(衝撃間隔 {period_ms:.2f} ms)  /  "
               f"最大 SK {r['max']:+.4f} @ {r['at']:.0f} Hz"
               + ("  ← 負。共振と無関係な周波数" if r["max"] < 0 else ""))
        u8 = fig.u8()
        for _ in range(hold):
            frames.append(u8)
            labels.append(lab)

    info = save_flipbook(frames, "window_sweep", labels, ms=380, hold_ms=1800,
                         log=log)
    facts = {
        "impact_period_ms": period_ms, "true_resonance_hz": fc,
        "table": [{k: r[k] for k in ("win", "ms", "max", "at", "bin", "frames")}
                  for r in rows],
        "negative_windows": [{"win": r["win"], "ms": r["ms"], "max": r["max"],
                              "at": r["at"]} for r in bad],
        "ops": ["synthesize_bearing_signal", "spectral_kurtosis"],
    }
    return info, facts


# =========================================================================== #
# 展示 4: 次数比分析 — 角度領域で立場が逆転する                    (GIF)      #
# =========================================================================== #
def ex_order_tracking(log):
    fs = 5000.0
    dur = 4.0
    run = A.synthesize_speed_ramp(fs, dur, 600.0, 1800.0, orders=(1.0, 3.5),
                                  resonance_hz=400.0)
    sig, rpm = run["signal"], run["rpm"]

    # 記録全体の主張(ガイドの表と同じ条件で、その場で測り直す)
    ff, mm = dsp.spectrum(sig, fs)
    amp_all = mm * (2.0 / sig.size)
    sel = (ff >= 30.0) & (ff <= 115.0)
    j = int(np.argmax(np.where(sel, amp_all, -1.0)))
    peak35_hz, peak35_amp = float(ff[j]), float(amp_all[j])
    half = peak35_amp / np.sqrt(2.0)
    lo_i = j
    while lo_i > 0 and amp_all[lo_i - 1] >= half:
        lo_i -= 1
    hi_i = j
    while hi_i < amp_all.size - 1 and amp_all[hi_i + 1] >= half:
        hi_i += 1
    width_hz = float(ff[hi_i] - ff[lo_i])
    os_all = A.order_spectrum(sig, fs, rpm, samples_per_rev=64, revolutions=78,
                              max_order=32.0)
    i35 = int(np.argmin(np.abs(os_all["orders"] - 3.5)))
    amp35_order = float(os_all["magnitude"][i35])
    h2 = amp35_order / np.sqrt(2.0)
    lo_o, hi_o = i35, i35
    while lo_o > 0 and os_all["magnitude"][lo_o - 1] >= h2:
        lo_o -= 1
    while hi_o < os_all["magnitude"].size - 1 and os_all["magnitude"][hi_o + 1] >= h2:
        hi_o += 1
    width_order = float(os_all["orders"][hi_o] - os_all["orders"][lo_o])
    res_order_400 = 400.0 / (os_all["mean_rpm"] / 60.0)
    k400 = int(np.argmin(np.abs(os_all["orders"] - res_order_400)))
    log(f"  ordinary spectrum: order-3.5 smears to {peak35_amp:.6f} at "
        f"{peak35_hz:.2f} Hz, -3 dB width {width_hz:.2f} Hz")
    log(f"  order spectrum (78 rev): order 3.5 = {amp35_order:.6f}, "
        f"-3 dB width {width_order:.5f} order ({hi_o - lo_o + 1} bin)")
    log(f"  400 Hz resonance -> order {res_order_400:.4f}, amplitude "
        f"{os_all['magnitude'][k400]:.6f} (was 1.0 in Hz)")

    # 滑走窓
    win_s = 1.2
    win_n = int(round(win_s * fs))
    n_frames = 30
    starts = np.linspace(0, sig.size - win_n, n_frames).round().astype(int)
    rows = []
    for s0 in starts:
        seg = sig[s0:s0 + win_n]
        seg_rpm = rpm[s0:s0 + win_n]
        f2, m2 = dsp.spectrum(seg, fs)
        a2 = m2 * (2.0 / seg.size)
        ang = A.angular_resample(seg, fs, seg_rpm, samples_per_rev=64)
        rev_even = int(ang["whole_revolutions"]) // 2 * 2        # 偶数回転で切る
        os_ = A.order_spectrum(seg, fs, seg_rpm, samples_per_rev=64,
                               revolutions=rev_even, max_order=25.0)
        shaft = float(np.mean(seg_rpm)) / 60.0
        rows.append({
            "t0": s0 / fs, "shaft_hz": shaft, "rpm": float(np.mean(seg_rpm)),
            "f": f2, "a": a2, "orders": os_["orders"], "mag": os_["magnitude"],
            "rev": rev_even, "res_order": os_["resolution_order"],
            "o400": 400.0 / shaft,
            "amp_o1": float(os_["magnitude"][int(np.argmin(np.abs(os_["orders"] - 1.0)))]),
            "amp_o35": float(os_["magnitude"][int(np.argmin(np.abs(os_["orders"] - 3.5)))]),
        })
    log(f"  sliding window {win_s:g} s: shaft {rows[0]['shaft_hz']:.3f} -> "
        f"{rows[-1]['shaft_hz']:.3f} Hz, order-3.5 amplitude "
        f"{rows[0]['amp_o35']:.4f} -> {rows[-1]['amp_o35']:.4f}")

    a_hi = max(float(np.max(r["a"][(r["f"] > 2.0) & (r["f"] < 600.0)])) for r in rows)
    m_hi = max(float(np.max(r["mag"][1:])) for r in rows)
    W, H = GIF_W, GIF_H
    frames, labels = [], []
    for k, r in enumerate(rows):
        labels.append(f"窓 {r['t0']:.2f}–{r['t0'] + win_s:.2f} s  /  {r['rpm']:.0f} rpm  /  "
                      f"Hz 軸の次数3.5 = {3.5 * r['shaft_hz']:.1f} Hz(動く)  /  "
                      f"次数軸の振幅 {r['amp_o35']:.4f}(動かない)")
        fig = Fig(W, H)
        _header(fig, "Order tracking: which spectrum is sharp tells you what it is",
                f"run-up 600 -> 1800 rpm, orders 1.0 and 3.5, fixed 400 Hz resonance")
        # 上: 回転数プロファイルと窓
        axr = Ax(fig, 76, 62, W - 30, 146, (0.0, dur), (500.0, 1900.0))
        axr.panel(C_PANEL2)
        ink = fig.ink()
        axr.frame(ink)
        axr.xticks(ink, [0, 1, 2, 3, 4], "%.0f")
        axr.yticks(ink, [600, 1200, 1800], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axr.curve(ink, np.arange(rpm.size) / fs, rpm, width=2)
        fig.stamp(ink, C_A)
        ink = fig.ink()
        ink.poly([(axr.X(r["t0"]), axr.y0), (axr.X(r["t0"] + win_s), axr.y0),
                  (axr.X(r["t0"] + win_s), axr.y1), (axr.X(r["t0"]), axr.y1)],
                 width=2, closed=True)
        fig.stamp(ink, C_B)
        fig.text(80, 44, f"shaft speed [rpm] and the {win_s:g} s analysis window",
                 C_TEXT, 12, True)
        fig.text(W - 320, 66, f"window {r['t0']:.2f} - {r['t0'] + win_s:.2f} s   "
                              f"mean {r['rpm']:7.1f} rpm = {r['shaft_hz']:6.3f} Hz",
                 C_B, 12, True)

        # 中: 通常のスペクトル(Hz)
        axf = Ax(fig, 76, 200, W - 30, 356, (0.0, 600.0), (0.0, a_hi * 1.12))
        axf.panel()
        ink = fig.ink()
        axf.frame(ink)
        axf.xticks(ink, [0, 100, 200, 300, 400, 500, 600], "%.0f")
        axf.yticks(ink, [0.0, 0.25, 0.5, 0.75, 1.0], "%.2f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axf.curve(ink, r["f"], r["a"], width=2)
        fig.stamp(ink, C_A)
        ink = fig.ink()
        axf.vline(ink, 400.0, width=2, dashed=True)
        fig.stamp(ink, C_TRUE)
        ink = fig.ink()
        for o, col in ((1.0, C_C), (3.5, C_B)):
            axf.vline(ink, o * r["shaft_hz"], width=1, dashed=True)
        fig.stamp(ink, C_B)
        fig.text(80, 182, "ordinary spectrum [Hz] - the shaft components move, "
                          "the resonance stays", C_TEXT, 12, True)
        fig.text(axf.X(400.0) + 6, 204, "400 Hz resonance (fixed)", C_TRUE, 11, True)
        fig.text(axf.X(1.0 * r["shaft_hz"]) + 4, 226,
                 f"order 1.0 = {1.0 * r['shaft_hz']:.2f} Hz", C_B, 11, True)
        fig.text(axf.X(3.5 * r["shaft_hz"]) + 4, 248,
                 f"order 3.5 = {3.5 * r['shaft_hz']:.2f} Hz", C_B, 11, True)
        fig.text(30, 270, "amp", C_DIM, 11)

        # 下: 次数スペクトル
        axo = Ax(fig, 76, 410, W - 30, 552, (0.0, 25.0), (0.0, m_hi * 1.12))
        axo.panel()
        ink = fig.ink()
        axo.frame(ink)
        axo.xticks(ink, [0, 1, 3.5, 5, 10, 15, 20, 25], "%g")
        axo.yticks(ink, [0.0, 0.25, 0.5, 0.75, 1.0], "%.2f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axo.curve(ink, r["orders"], r["mag"], width=2)
        fig.stamp(ink, C_C)
        ink = fig.ink()
        axo.vline(ink, 1.0, width=1, dashed=True)
        axo.vline(ink, 3.5, width=1, dashed=True)
        fig.stamp(ink, C_B)
        ink = fig.ink()
        axo.vline(ink, r["o400"], width=2, dashed=True)
        fig.stamp(ink, C_TRUE)
        fig.text(80, 392, "order spectrum [shaft order] - the shaft components stay, "
                          "the resonance moves", C_TEXT, 12, True)
        fig.text(axo.X(r["o400"]) + 6, 414,
                 f"400 Hz = order {r['o400']:.2f} (moves)", C_TRUE, 11, True)
        fig.text(axo.X(3.5) + 4, 436, "order 3.5 (fixed)", C_B, 11, True)
        fig.text(30, 470, "amp", C_DIM, 11)
        fig.text(W - 250, 558, "shaft order ->", C_DIM, 11)

        fig.box(76, 574, W - 30, H - 12, C_PANEL2)
        fig.text(88, 580, f"cropped to {r['rev']} whole revolutions (even, so order 3.5 "
                          f"lands on a bin)   resolution {r['res_order']:.6f} order",
                 C_DIM, 12)
        fig.text(88, 600, f"order 1.0 amplitude {r['amp_o1']:.6f}     "
                          f"order 3.5 amplitude {r['amp_o35']:.6f}     "
                          f"(true amplitude 1.0 for both)", C_C, 13, True)
        frames.append(fig.u8())

    info = save_flipbook(frames, "order_tracking", labels, ms=220, hold_ms=1400,
                         log=log)
    facts = {
        "rpm_start": 600.0, "rpm_end": 1800.0, "duration_s": dur, "rate_hz": fs,
        "total_revolutions": run["total_revolutions"],
        "ordinary_order35_amp": peak35_amp, "ordinary_order35_hz": peak35_hz,
        "ordinary_order35_width_hz": width_hz,
        "order_spectrum_order35_amp": amp35_order,
        "order_spectrum_order35_width": width_order,
        "order_spectrum_order35_bins": int(hi_o - lo_o + 1),
        "resonance_order_at_mean_rpm": res_order_400,
        "resonance_amp_in_order_domain": float(os_all["magnitude"][k400]),
        "window_s": win_s, "frames": n_frames,
        "shaft_hz_first": rows[0]["shaft_hz"], "shaft_hz_last": rows[-1]["shaft_hz"],
        "ops": ["synthesize_speed_ramp", "spectrum", "angular_resample",
                "order_spectrum"],
    }
    return info, facts


# =========================================================================== #
# 展示 5: 軸受の幾何から欠陥周波数                                  (GIF)      #
# =========================================================================== #
def ex_bearing_geometry(log):
    rpm = 1800.0
    D = 40.0
    n_frames = 36
    # 3 つのパラメータを順に動かす(転動体数 → 接触角 → 転動体径)
    seq = []
    for n in (7, 8, 9, 10, 11, 12, 13, 14):
        seq.append({"n": n, "d": 8.0, "ang": 0.0, "phase": "rolling elements N"})
    for a in np.linspace(0.0, 40.0, 14):
        seq.append({"n": 14, "d": 8.0, "ang": float(a), "phase": "contact angle"})
    for d in np.linspace(8.0, 15.0, 14):
        seq.append({"n": 14, "d": float(d), "ang": 40.0, "phase": "element diameter"})
    n_frames = len(seq)

    rows = []
    for i, s in enumerate(seq):
        b = A.bearing_defect_frequencies(rpm, s["n"], s["d"], D, s["ang"])
        rows.append({**s, **b,
                     "id1": b["bpfo_hz"] + b["bpfi_hz"] - s["n"] * b["shaft_hz"],
                     "id2": b["bpfo_hz"] - s["n"] * b["ftf_hz"]})
    hi = max(max(r["bpfi_hz"], r["bsf_hz_2x"]) for r in rows) * 1.1
    log(f"  {n_frames} frames; BPFO {rows[0]['bpfo_hz']:.4f} -> "
        f"{rows[-1]['bpfo_hz']:.4f} Hz, BPFI {rows[0]['bpfi_hz']:.4f} -> "
        f"{rows[-1]['bpfi_hz']:.4f} Hz")
    log(f"  exact identities over all frames: max |BPFO+BPFI-N*f_r| = "
        f"{max(abs(r['id1']) for r in rows):.3e}, max |BPFO-N*FTF| = "
        f"{max(abs(r['id2']) for r in rows):.3e}")

    W, H = GIF_W, GIF_H
    frames, labels = [], []
    phase_ja = {"rolling elements N": "転動体数を振る",
                "contact angle": "接触角を振る",
                "element diameter": "転動体径を振る"}
    for i, r in enumerate(rows):
        labels.append(f"{phase_ja[r['phase']]}  /  N={int(r['n_elements'])}  "
                      f"d={r['element_diameter']:.2f} mm  α={r['contact_angle_deg']:.1f}°  /  "
                      f"BPFO {r['bpfo_hz']:.4f} Hz  BPFI {r['bpfi_hz']:.4f} Hz")
        fig = Fig(W, H)
        _header(fig, "Bearing defect frequencies come out of the geometry",
                f"{rpm:g} rpm, pitch diameter {D:g} mm - derived, never tabulated")
        # 左: 断面図。保持器は FTF で、転動体は BSF で自転する。
        cx, cy, R = 250.0, 320.0, 180.0
        fig.box(60, 60, 440, 560, C_PANEL2)
        r_ball = R * (r["element_diameter"] / D) * 0.5
        r_pitch = R * 0.62
        ink = fig.ink()
        ink.circle((cx, cy), R, width=3)
        ink.circle((cx, cy), R * 0.88, width=2)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        ink.circle((cx, cy), r_pitch - r_ball * 0.62, width=2)
        ink.circle((cx, cy), r_pitch - r_ball * 1.05, width=3)
        fig.stamp(ink, C_A)
        ink = fig.ink()
        ink.dashed((cx - R, cy), (cx + R, cy), width=1, dash=6, gap=6)
        fig.stamp(ink, C_AXIS)
        # 保持器の回転位相(FTF に比例した実際の角度。0.02 s ぶん進める)
        theta0 = 2.0 * np.pi * r["ftf_hz"] * (i * 0.02)
        ink = fig.ink()
        for kb in range(int(r["n_elements"])):
            th = theta0 + 2.0 * np.pi * kb / r["n_elements"]
            ink.circle((cx + r_pitch * np.cos(th), cy - r_pitch * np.sin(th)),
                       max(4.0, r_ball), width=2)
        fig.stamp(ink, C_B)
        ink = fig.ink()
        ink.marks([(cx, cy)], size=6, shape="cross", width=2)
        fig.stamp(ink, C_TEXT)
        fig.text(70, 66, "cross-section (cage advances at FTF)", C_TEXT, 12, True)
        fig.text(70, 500, f"N = {int(r['n_elements'])} elements", C_B, 13, True)
        fig.text(70, 520, f"d = {r['element_diameter']:.2f} mm, "
                          f"D = {r['pitch_diameter']:.2f} mm", C_TEXT, 12, True)
        fig.text(70, 538, f"contact angle {r['contact_angle_deg']:.2f} deg  ->  "
                          f"ratio d/D cos a = {r['ratio']:.6f}", C_TEXT, 12, True)

        # 右: 4 つの特徴周波数を棒で
        axb = Ax(fig, 520, 100, W - 40, 430, (0.0, hi), (-0.6, 5.4))
        axb.panel(C_PANEL)
        ink = fig.ink()
        axb.frame(ink)
        axb.xticks(ink, [0, 50, 100, 150, 200, 250, 300], "%.0f")
        fig.stamp(ink, C_AXIS)
        bars = [("FTF  cage", r["ftf_hz"], C_D),
                ("BPFO outer", r["bpfo_hz"], C_A),
                ("BPFI inner", r["bpfi_hz"], C_C),
                ("BSF  ball", r["bsf_hz"], C_B),
                ("2xBSF", r["bsf_hz_2x"], C_E)]
        for bi, (label, val, col) in enumerate(bars):
            yy = axb.Y(4.7 - bi)
            ink = fig.ink()
            ink.line((axb.X(0.0), yy), (axb.X(val), yy), width=13)
            fig.stamp(ink, col)
            fig.text(524, yy - 26, label, col, 11, True)
            fig.text(axb.X(val) + 8, yy - 7, f"{val:9.4f} Hz", C_TEXT, 12, True)
        fig.text(524, 80, "characteristic frequencies", C_TEXT, 12, True)
        fig.text(W - 210, 436, "frequency [Hz] ->", C_DIM, 11)

        fig.box(520, 462, W - 40, 560, C_PANEL2)
        fig.text(532, 468, f"sweeping: {r['phase']}", C_B, 12, True)
        fig.text(532, 490, f"shaft f_r = {r['shaft_hz']:.6f} Hz", C_TEXT, 12, True)
        fig.text(532, 510, f"BPFO + BPFI - N f_r = {r['id1']:.3e}", C_C, 12, True)
        fig.text(532, 530, f"BPFO - N x FTF     = {r['id2']:.3e}", C_C, 12, True)
        fig.text(532, 546, "exactly zero in float64 - the identities that catch a "
                           "transposed d and D", C_DIM, 11)
        fig.text(60, 580, "These are the no-slip kinematic rates. A real bearing slips "
                          "by about a percent, so a line within ~1 % is a match;",
                 C_DIM, 12)
        fig.text(60, 598, "an exact match is a coincidence. That tolerance belongs to "
                          "the caller, so the operator does not apply one.", C_DIM, 12)
        frames.append(fig.u8())

    info = save_flipbook(frames, "bearing_geometry", labels, ms=200, hold_ms=1400,
                         log=log)
    facts = {
        "rpm": rpm, "pitch_diameter_mm": D, "frames": n_frames,
        "first": {k: rows[0][k] for k in ("n_elements", "element_diameter",
                                          "contact_angle_deg", "ratio", "shaft_hz",
                                          "ftf_hz", "bpfo_hz", "bpfi_hz", "bsf_hz")},
        "last": {k: rows[-1][k] for k in ("n_elements", "element_diameter",
                                          "contact_angle_deg", "ratio", "shaft_hz",
                                          "ftf_hz", "bpfo_hz", "bpfi_hz", "bsf_hz")},
        "max_abs_identity_1": max(abs(r["id1"]) for r in rows),
        "max_abs_identity_2": max(abs(r["id2"]) for r in rows),
        "bpfo_range": (min(r["bpfo_hz"] for r in rows), max(r["bpfo_hz"] for r in rows)),
        "bpfi_range": (min(r["bpfi_hz"] for r in rows), max(r["bpfi_hz"] for r in rows)),
        "ops": ["bearing_defect_frequencies"],
    }
    return info, facts


# =========================================================================== #
# 展示 6: A 特性・C 特性の重み付け                                  (GIF)      #
# =========================================================================== #
def ex_weighting_ac(log):
    grid = np.logspace(np.log10(8.0), np.log10(20000.0), 900)
    curve_a = A.weighting_response(grid, "A")
    curve_c = A.weighting_response(grid, "C")
    curve_z = A.weighting_response(grid, "Z")
    a1k = float(A.weighting_response(np.array([1000.0]), "A")[0])
    c1k = float(A.weighting_response(np.array([1000.0]), "C")[0])
    log(f"  A(1000) = {a1k!r}  is exactly 0.0: {a1k == 0.0}")
    log(f"  C(1000) = {c1k!r}  is exactly 0.0: {c1k == 0.0}")

    fs = 48000.0
    dur = 0.5
    amp = 1.0
    n = int(round(dur * fs))
    t = np.arange(n) / fs
    bin_hz = 1.0 / dur                       # この記録の周波数分解能
    # **bin 中心の音**だけを掃引する。理由は下の off-bin 対照で測ってある:
    # 矩形窓の漏れ込みが重み付けの効いた総和を支配し、低域では 11 dB 以上ずれる。
    tones = np.unique(np.round(np.logspace(np.log10(20.0), np.log10(16000.0), 34)
                               / bin_hz).astype(int)) * bin_hz
    leq_z_closed = 10.0 * np.log10(amp * amp / 2.0)
    rows = []
    for f0 in tones:
        x = amp * np.sin(2.0 * np.pi * f0 * t)
        lz = A.equivalent_level(x, fs, weighting="Z", ref=1.0)
        la = A.equivalent_level(x, fs, weighting="A", ref=1.0)
        lc = A.equivalent_level(x, fs, weighting="C", ref=1.0)
        wa = float(A.weighting_response(np.array([f0]), "A")[0])
        wc = float(A.weighting_response(np.array([f0]), "C")[0])
        # 対照: 同じ音を bin から半分ずらす(記録に半端な周期が残る)
        f_off = float(f0) + 0.5 * bin_hz
        xo = amp * np.sin(2.0 * np.pi * f_off * t)
        lzo = A.equivalent_level(xo, fs, weighting="Z", ref=1.0)
        lao = A.equivalent_level(xo, fs, weighting="A", ref=1.0)
        wao = float(A.weighting_response(np.array([f_off]), "A")[0])
        rows.append({"f": float(f0), "lz": float(lz), "la": float(la), "lc": float(lc),
                     "wa": wa, "wc": wc, "da": float(la - lz) - wa,
                     "dc": float(lc - lz) - wc,
                     "f_off": f_off, "da_off": float(lao - lzo) - wao,
                     "wave": x[:int(round(0.006 * fs))]})
    worst_a = max(abs(r["da"]) for r in rows)
    worst_c = max(abs(r["dc"]) for r in rows)
    worst_off = max(abs(r["da_off"]) for r in rows)
    k_off = int(np.argmax([abs(r["da_off"]) for r in rows]))
    log(f"  L_eq(Z) closed form {leq_z_closed:.6f} dB; measured "
        f"{rows[0]['lz']:.6f} .. {rows[-1]['lz']:.6f} dB")
    log(f"  bin-centred tones ({len(rows)}, resolution {bin_hz:g} Hz): "
        f"max |(L_A - L_Z) - A(f)| = {worst_a:.4e} dB, "
        f"max |(L_C - L_Z) - C(f)| = {worst_c:.4e} dB")
    log(f"  off-bin control (same tones + {0.5 * bin_hz:g} Hz): the same difference "
        f"reaches {worst_off:.4f} dB at {rows[k_off]['f_off']:.1f} Hz "
        f"-- rectangular-window leakage, weighted at a different gain")

    W, H = GIF_W, GIF_H
    i1k = int(np.argmin(np.abs(tones - 1000.0)))
    frames, labels = [], []
    for k, r in enumerate(rows):
        labels.append(f"純音 {r['f']:.1f} Hz  /  A(f) {r['wa']:+.4f} dB  "
                      f"C(f) {r['wc']:+.4f} dB  /  実測 L_A−L_Z との差 "
                      f"{r['da']:+.2e} dB")
        fig = Fig(W, H)
        _header(fig, "A and C weighting: 1 kHz is exactly 0 dB by construction",
                "computed from the four defining pole frequencies - no published "
                "table is transcribed")
        axw = Ax(fig, 84, 76, W - 300, 400, (8.0, 20000.0), (-75.0, 8.0), logx=True)
        axw.panel()
        ink = fig.ink()
        axw.frame(ink)
        axw.xticks(ink, [10, 31.5, 100, 316, 1000, 3160, 10000, 20000], "%g")
        axw.yticks(ink, [0, -10, -20, -30, -40, -50, -60, -70], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axw.hline(ink, 0.0, width=1, dashed=True)
        axw.vline(ink, 1000.0, width=1, dashed=True)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        axw.curve(ink, grid, curve_z, width=2)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        axw.curve(ink, grid, curve_c, width=2)
        fig.stamp(ink, C_C)
        ink = fig.ink()
        axw.curve(ink, grid, curve_a, width=2)
        fig.stamp(ink, C_A)
        ink = fig.ink()
        axw.vline(ink, r["f"], width=2)
        fig.stamp(ink, C_B, alpha=0.75)
        ink = fig.ink()
        ink.marks([(axw.X(r["f"]), axw.Y(r["wa"])),
                   (axw.X(r["f"]), axw.Y(r["wc"]))], size=8, shape="cross", width=2)
        fig.stamp(ink, C_TRUE)
        fig.text(88, 58, "weighting response [dB] vs frequency (log)", C_TEXT, 12, True)
        _legend(fig, W - 292, 84, [("A weighting", C_A), ("C weighting", C_C),
                                   ("Z (flat, 0 dB)", C_DIM),
                                   ("current tone", C_B)])
        fig.text(axw.X(1000.0) + 6, 92, "1 kHz", C_DIM, 11, True)
        fig.text(axw.X(1000.0) + 6, 108, f"A = {a1k:.1f} dB exactly", C_A, 11, True)
        fig.text(axw.X(1000.0) + 6, 124, f"C = {c1k:.1f} dB exactly", C_C, 11, True)
        fig.text(30, 220, "dB", C_DIM, 11)
        fig.text(W - 470, 406, "frequency [Hz] ->", C_DIM, 11)

        # 右: 現在のトーンと実測レベル
        fig.box(W - 292, 160, W - 24, 400, C_PANEL2)
        fig.text(W - 282, 168, "pure tone, measured", C_TEXT, 12, True)
        fig.text(W - 282, 190, f"f = {r['f']:9.2f} Hz", C_B, 13, True)
        fig.text(W - 282, 214, f"L_eq(Z) {r['lz']:9.6f} dB", C_DIM, 12, True)
        fig.text(W - 282, 234, f"L_eq(A) {r['la']:9.6f} dB", C_A, 12, True)
        fig.text(W - 282, 254, f"L_eq(C) {r['lc']:9.6f} dB", C_C, 12, True)
        fig.text(W - 282, 282, f"A(f) curve {r['wa']:+9.4f} dB", C_A, 12, True)
        fig.text(W - 282, 302, f"L_A - L_Z  {r['la'] - r['lz']:+9.4f} dB", C_A, 12, True)
        fig.text(W - 282, 322, f"difference {r['da']:+.3e} dB", C_TEXT, 12, True)
        fig.text(W - 282, 350, f"C(f) curve {r['wc']:+9.4f} dB", C_C, 12, True)
        fig.text(W - 282, 370, f"difference {r['dc']:+.3e} dB", C_TEXT, 12, True)

        # 下: 誤差の推移 — bin 中心 vs bin から半分ずらした対照
        lim = max(1.0, worst_off * 1.15)
        axe = Ax(fig, 84, 452, 540, 556, (20.0, 16000.0), (-lim, lim), logx=True)
        axe.panel(C_PANEL2)
        ink = fig.ink()
        axe.frame(ink)
        axe.xticks(ink, [20, 100, 1000, 10000], "%g")
        axe.yticks(ink, [-10, 0, 10], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axe.hline(ink, 0.0, width=1)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        axe.curve(ink, [rr["f"] for rr in rows[:k + 1]],
                  [rr["da_off"] for rr in rows[:k + 1]], width=2)
        fig.stamp(ink, C_WARN)
        ink = fig.ink()
        axe.curve(ink, [rr["f"] for rr in rows[:k + 1]],
                  [rr["da"] for rr in rows[:k + 1]], width=2)
        axe.curve(ink, [rr["f"] for rr in rows[:k + 1]],
                  [rr["dc"] for rr in rows[:k + 1]], width=2)
        fig.stamp(ink, C_C)
        fig.text(88, 434, "(L_weighted - L_Z) minus the curve value [dB]", C_TEXT, 12, True)
        _legend(fig, 300, 458, [("tone ON a bin", C_C),
                                (f"same tone +{0.5 * bin_hz:g} Hz (off bin)", C_WARN)])
        fig.text(88, 560, f"on-bin worst so far   A {max(abs(rr['da']) for rr in rows[:k+1]):.2e} dB"
                          f"   C {max(abs(rr['dc']) for rr in rows[:k+1]):.2e} dB",
                 C_C, 12, True)
        fig.text(88, 578, f"off-bin worst so far  {max(abs(rr['da_off']) for rr in rows[:k+1]):8.4f} dB"
                          f"   <- rectangular-window leakage, weighted at another gain",
                 C_WARN, 12, True)

        axs = Ax(fig, 596, 452, W - 24, 556, (0.0, 6.0), (-1.25, 1.25))
        axs.panel(C_PANEL2)
        ink = fig.ink()
        axs.frame(ink)
        axs.xticks(ink, [0, 2, 4, 6], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        tw = np.arange(r["wave"].size) / fs * 1e3
        axs.curve(ink, tw, r["wave"], width=2)
        fig.stamp(ink, C_B)
        fig.text(600, 434, "the tone itself (first 6 ms)", C_TEXT, 12, True)
        fig.text(W - 130, 562, "time [ms] ->", C_DIM, 11)
        fig.text(600, 580, f"L_eq(Z) = 10 log10(A^2/2) = {leq_z_closed:.6f} dB "
                           f"by closed form; measured {r['lz']:.6f} dB.", C_DIM, 12)
        frames.append(fig.u8())

    info = save_flipbook(frames, "weighting_ac", labels, ms=220, hold_ms=1400, log=log)
    facts = {
        "a_at_1k": a1k, "c_at_1k": c1k, "a_at_1k_is_exact_zero": a1k == 0.0,
        "c_at_1k_is_exact_zero": c1k == 0.0,
        "leq_z_closed_form_db": leq_z_closed,
        "leq_z_measured_range": (min(r["lz"] for r in rows), max(r["lz"] for r in rows)),
        "max_abs_a_mismatch_db": worst_a, "max_abs_c_mismatch_db": worst_c,
        "bin_hz": bin_hz,
        "off_bin_offset_hz": 0.5 * bin_hz,
        "off_bin_max_abs_a_mismatch_db": worst_off,
        "off_bin_worst_freq_hz": rows[k_off]["f_off"],
        "n_tones": len(rows), "rate_hz": fs, "duration_s": dur,
        "sample_points": {f"{r['f']:.1f}": {"A": r["wa"], "C": r["wc"]}
                          for r in rows[::6]},
        "ops": ["weighting_response", "apply_weighting", "equivalent_level"],
    }
    return info, facts


# =========================================================================== #
# 展示 7: funct1d の解析真値                                        (PNG)      #
# =========================================================================== #
def ex_funct1d_truth(log):
    # (a) 微分 — sin の微分は cos
    n = 512
    t = np.linspace(0.0, 4.0 * np.pi, n)
    dx = float(t[1] - t[0])
    y = np.sin(t)
    d = F.derivate_funct_1d(y) / dx
    c = np.cos(t)
    err_d = float(np.max(np.abs(d - c)))
    # (b) ゼロ交差 — k pi
    zc = F.zero_crossings_funct_1d(y)
    refined = np.array([(t[i] + dx * abs(y[i]) / (abs(y[i]) + abs(y[i + 1]))) / np.pi
                        for i in zc])
    err_zc = float(np.max(np.abs(refined - np.round(refined))))
    # (c) 積分の往復
    back = F.integrate_funct_1d(F.derivate_funct_1d(y))
    err_round = F.distance_funct_1d(back, y - y[0], mode="max")
    # (d) 減衰振動から周期・時定数・遅延
    rng = np.random.default_rng(20260902)
    dt, f0, tau = 0.002, 5.0, 0.4
    tt = np.arange(0.0, 1.2, dt)
    clean = np.exp(-tt / tau) * np.sin(2.0 * np.pi * f0 * tt)
    noisy = F.create_funct_1d_array(clean + rng.normal(0.0, 0.02, tt.size))
    sm = F.smooth_funct_1d_gauss(noisy, sigma=3.0)
    win = int(0.9 / dt)
    sm_w, t_w = sm[:win], tt[:win]
    peaks = F.local_min_max_funct_1d(sm_w)["max"]
    period = float(np.mean(np.diff(peaks))) * dt
    zc2 = F.zero_crossings_funct_1d(sm_w)
    half = float(np.mean(np.diff(zc2))) * dt
    peak_amp = np.array([F.get_pair_funct_1d(F.abs_funct_1d(sm_w), int(i))[1]
                         for i in peaks])
    slope = float(np.polyfit(t_w[peaks], np.log(peak_amp), 1)[0])
    tau_est = -1.0 / slope
    delay = 25
    y1 = noisy[:400]
    y2 = noisy[delay:400 + delay]
    m = F.match_funct_1d_trans(F.derivate_funct_1d(y1), F.derivate_funct_1d(y2))
    log(f"  d/dx sin - cos: max |err| {err_d:.3e} (dx = {dx:.6f}, second order)")
    log(f"  zero crossings {list(map(int, zc))} -> x/pi {np.round(refined, 8).tolist()} "
        f"(max deviation from an integer {err_zc:.3e})")
    log(f"  integrate(derivate(y)) - (y - y[0]): max {err_round:.3e}")
    log(f"  period {period:.6f} s (true {1 / f0:.6f}), half period {half:.6f} s "
        f"(true {1 / (2 * f0):.6f}), tau {tau_est:.6f} s (true {tau:g}), "
        f"match shift {m['shift']} (true {delay})")

    W, H = 1160, 860
    fig = Fig(W, H)
    _header(fig, "funct1d against closed-form truth",
            "every number below is compared with an answer known before the "
            "measurement")

    # (a) sin / cos
    ax = Ax(fig, 86, 78, 560, 232, (0.0, 4.0 * np.pi), (-1.25, 1.25))
    ax.panel()
    ink = fig.ink()
    ax.frame(ink)
    ax.xticks(ink, [0, np.pi, 2 * np.pi, 3 * np.pi, 4 * np.pi], "%.2f")
    ax.yticks(ink, [-1, 0, 1], "%.0f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax.curve(ink, t, y, width=2)
    fig.stamp(ink, C_A)
    ink = fig.ink()
    ax.curve(ink, t, c, width=3)
    fig.stamp(ink, C_DIM)
    ink = fig.ink()
    ax.curve(ink, t, d, width=1)
    fig.stamp(ink, C_B)
    fig.text(90, 60, "derivate_funct_1d(sin) / dx  vs  cos", C_TEXT, 13, True)
    _legend(fig, 380, 86, [("sin", C_A), ("cos (truth)", C_DIM),
                           ("derivative", C_B)], 11)
    fig.text(90, 240, f"max |derivative - cos| = {err_d:.4e}   "
                      f"(dx = {dx:.6f}; central differences are second order, "
                      f"so the residual scales as dx^2)", C_TEXT, 12, True)

    # (b) ゼロ交差
    ax2 = Ax(fig, 640, 78, W - 40, 232, (0.0, 4.0 * np.pi), (-1.25, 1.25))
    ax2.panel()
    ink = fig.ink()
    ax2.frame(ink)
    ax2.xticks(ink, [0, np.pi, 2 * np.pi, 3 * np.pi, 4 * np.pi], "%.2f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax2.hline(ink, 0.0, width=1)
    fig.stamp(ink, C_DIM)
    ink = fig.ink()
    ax2.curve(ink, t, y, width=2)
    fig.stamp(ink, C_A)
    ink = fig.ink()
    ink.marks([(ax2.X(t[i]), ax2.Y(0.0)) for i in zc], size=9, shape="cross", width=2)
    fig.stamp(ink, C_E)
    fig.text(644, 60, "zero_crossings_funct_1d", C_TEXT, 13, True)
    for i, (idx, xr) in enumerate(zip(zc, refined)):
        fig.text(644, 246 + i * 18,
                 f"index {int(idx):3d}  ->  x = {xr:.8f} pi", C_E, 12, True)
    fig.text(644, 246 + len(zc) * 18,
             f"max deviation from an integer multiple of pi: {err_zc:.3e}",
             C_TEXT, 12, True)
    fig.text(644, 264 + len(zc) * 18,
             "(the op reports the sample BEFORE the crossing; the sub-sample",
             C_DIM, 11)
    fig.text(644, 280 + len(zc) * 18,
             " position above is linear interpolation between the two samples)",
             C_DIM, 11)

    # (c)(d) 減衰振動
    ax3 = Ax(fig, 86, 400, W - 40, 596, (0.0, 1.2), (-1.15, 1.15))
    ax3.panel()
    ink = fig.ink()
    ax3.frame(ink)
    ax3.xticks(ink, [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0, 1.2], "%.1f")
    ax3.yticks(ink, [-1, 0, 1], "%.0f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax3.curve(ink, tt, noisy, width=1)
    fig.stamp(ink, C_DIM)
    ink = fig.ink()
    ax3.curve(ink, tt, sm, width=2)
    fig.stamp(ink, C_A)
    ink = fig.ink()
    ax3.curve(ink, tt, np.exp(-tt / tau), width=2)
    ax3.curve(ink, tt, -np.exp(-tt / tau), width=2)
    fig.stamp(ink, C_C)
    ink = fig.ink()
    ink.marks([(ax3.X(t_w[i]), ax3.Y(sm_w[i])) for i in peaks], size=7,
              shape="cross", width=2)
    fig.stamp(ink, C_B)
    ink = fig.ink()
    ink.marks([(ax3.X(t_w[i]), ax3.Y(0.0)) for i in zc2], size=5,
              shape="square", width=1)
    fig.stamp(ink, C_E)
    ink = fig.ink()
    ax3.vline(ink, 0.9, width=1, dashed=True)
    fig.stamp(ink, C_WARN)
    fig.text(90, 382, "damped oscillation  exp(-t/0.4) sin(2 pi 5 t) + N(0, 0.02)",
             C_TEXT, 13, True)
    _legend(fig, W - 250, 408, [("raw", C_DIM), ("gauss sigma 3", C_A),
                                ("true envelope", C_C), ("local maxima", C_B),
                                ("zero crossings", C_E)], 11)
    fig.text(ax3.X(0.9) + 6, 410, "analysis window ends here", C_WARN, 11, True)
    fig.text(ax3.X(0.9) + 6, 426, "(below 0.1 amplitude the noise", C_WARN, 11)
    fig.text(ax3.X(0.9) + 6, 442, " forges extrema)", C_WARN, 11)
    fig.text(W - 300, 602, "time [s] ->", C_DIM, 11)

    fig.box(86, 630, W - 40, H - 16, C_PANEL2)
    fig.text(96, 638, "quantity", C_DIM, 12, True)
    fig.text(420, 638, "recovered", C_DIM, 12, True)
    fig.text(620, 638, "closed-form truth", C_DIM, 12, True)
    fig.text(830, 638, "note", C_DIM, 12, True)
    table = [
        ("period from local maxima", f"{period:.6f} s", f"{1 / f0:.6f} s",
         f"{len(peaks)} maxima, mean spacing"),
        ("half period from zero crossings", f"{half:.6f} s", f"{1 / (2 * f0):.6f} s",
         f"{len(zc2)} crossings"),
        ("decay time constant tau", f"{tau_est:.6f} s", f"{tau:.6f} s",
         "slope of log peak envelope"),
        ("delay by cross-correlation", f"{m['shift']} samples", f"{delay} samples",
         f"score {m['score']:.4f}, matched on derivatives"),
        ("integrate(derivate(y)) round trip", f"{err_round:.3e}", "0",
         "max error, amplitude ~1"),
    ]
    for i, (k, v, tv, note) in enumerate(table):
        yy = 662 + i * 22
        fig.text(96, yy, k, C_TEXT, 12, False)
        fig.text(420, yy, v, C_C, 12, True)
        fig.text(620, yy, tv, C_TRUE, 12, True)
        fig.text(830, yy, note, C_DIM, 12, False)

    frame = fig.u8()
    info = save_png(frame, "funct1d_truth", log)
    facts = {
        "derivative_max_error": err_d, "dx": dx,
        "zero_crossing_indices": [int(v) for v in zc],
        "zero_crossing_x_over_pi": [float(v) for v in refined],
        "zero_crossing_max_deviation": err_zc,
        "round_trip_max_error": float(err_round),
        "period_s": period, "period_true_s": 1 / f0,
        "half_period_s": half, "half_period_true_s": 1 / (2 * f0),
        "tau_s": tau_est, "tau_true_s": tau,
        "match_shift": int(m["shift"]), "match_shift_true": delay,
        "match_score": float(m["score"]),
        "n_peaks": int(len(peaks)), "n_zero_crossings": int(len(zc2)),
        "ops": ["derivate_funct_1d", "integrate_funct_1d", "zero_crossings_funct_1d",
                "local_min_max_funct_1d", "smooth_funct_1d_gauss", "abs_funct_1d",
                "get_pair_funct_1d", "distance_funct_1d", "match_funct_1d_trans",
                "create_funct_1d_array"],
    }
    return info, facts


# =========================================================================== #
# 展示 8: 平滑化のトレードオフ                                      (GIF)      #
# =========================================================================== #
def ex_smoothing_tradeoff(log):
    rng = np.random.default_rng(20260902)
    n = 600
    dt = 0.002
    tt = np.arange(n) * dt
    clean = np.exp(-tt / 0.4) * np.sin(2.0 * np.pi * 5.0 * tt)
    noisy = clean + rng.normal(0.0, 0.06, n)
    true_max = len(F.local_min_max_funct_1d(clean)["max"])
    true_peak = float(clean.max())

    sigmas = np.concatenate([[0.0], np.logspace(np.log10(0.6), np.log10(40.0), 31)])
    rows = []
    for s in sigmas:
        y = np.asarray(noisy) if s == 0.0 else F.smooth_funct_1d_gauss(noisy, sigma=float(s))
        ex = F.local_min_max_funct_1d(y)
        rows.append({"sigma": float(s), "y": y,
                     "rmse": float(np.sqrt(np.mean((y - clean) ** 2))),
                     "peak": float(y.max()), "nmax": int(len(ex["max"])),
                     "nmin": int(len(ex["min"])), "maxima": ex["max"]})
    best = int(np.argmin([r["rmse"] for r in rows]))
    log(f"  clean: {true_max} maxima, peak {true_peak:.6f}")
    log(f"  raw:   {rows[0]['nmax']} maxima, rmse {rows[0]['rmse']:.6f}, "
        f"peak {rows[0]['peak']:.6f}")
    log(f"  best rmse at sigma {rows[best]['sigma']:.3f}: rmse {rows[best]['rmse']:.6f} "
        f"({rows[0]['rmse'] / rows[best]['rmse']:.2f}x better), "
        f"peak {rows[best]['peak']:.6f} ({100 * (rows[best]['peak'] / true_peak - 1):+.2f} %), "
        f"{rows[best]['nmax']} maxima")
    log(f"  over-smoothed sigma {rows[-1]['sigma']:.2f}: rmse {rows[-1]['rmse']:.6f}, "
        f"peak {rows[-1]['peak']:.6f} "
        f"({100 * (rows[-1]['peak'] / true_peak - 1):+.2f} %)")

    rmse_hi = max(r["rmse"] for r in rows) * 1.12
    W, H = GIF_W, GIF_H
    frames, labels = [], []
    for k, r in enumerate(rows):
        labels.append(f"ガウス σ={r['sigma']:.2f}  /  RMS 誤差 {r['rmse']:.6f}  /  "
                      f"極大 {r['nmax']} 個(真値 {true_max})  /  ピーク "
                      f"{100 * (r['peak'] / true_peak - 1):+.2f} %")
        fig = Fig(W, H)
        _header(fig, "Smoothing: the noise falls and the extrema flatten",
                "damped 5 Hz oscillation + N(0, 0.06), gaussian smoothing swept")
        axw = Ax(fig, 84, 70, W - 30, 300, (0.0, 1.2), (-1.15, 1.15))
        axw.panel()
        ink = fig.ink()
        axw.frame(ink)
        axw.xticks(ink, [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2], "%.1f")
        axw.yticks(ink, [-1, 0, 1], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axw.curve(ink, tt, noisy, width=1)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        axw.curve(ink, tt, clean, width=2)
        fig.stamp(ink, C_C)
        ink = fig.ink()
        axw.curve(ink, tt, r["y"], width=2)
        fig.stamp(ink, C_B)
        ink = fig.ink()
        ink.marks([(axw.X(tt[i]), axw.Y(r["y"][i])) for i in r["maxima"]],
                  size=4, shape="square", width=1)
        fig.stamp(ink, C_E)
        fig.text(88, 52, "waveform", C_TEXT, 12, True)
        _legend(fig, W - 230, 78, [("noisy input", C_DIM), ("clean truth", C_C),
                                   ("smoothed", C_B), ("local maxima", C_E)])
        fig.text(W - 230, 148, f"sigma = {r['sigma']:6.3f} samples", C_B, 13, True)
        fig.text(W - 230, 168, f"     = {r['sigma'] * dt * 1e3:6.2f} ms", C_DIM, 12)
        fig.text(30, 170, "amp", C_DIM, 11)

        # 下段左: RMSE
        axr = Ax(fig, 84, 372, 520, 552, (0.5, 45.0), (0.0, rmse_hi), logx=True)
        axr.panel(C_PANEL2)
        ink = fig.ink()
        axr.frame(ink)
        axr.xticks(ink, [1, 2, 5, 10, 20, 40], "%g")
        axr.yticks(ink, [0.0, 0.05, 0.1, 0.15, 0.2], "%.2f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axr.hline(ink, rows[0]["rmse"], width=1, dashed=True)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        pts = [(axr.X(rr["sigma"]), axr.Y(rr["rmse"]))
               for rr in rows[1:k + 1]] if k >= 1 else []
        if len(pts) >= 2:
            ink.poly(pts, width=2)
        fig.stamp(ink, C_A)
        if k >= 1:
            ink = fig.ink()
            ink.marks([(axr.X(r["sigma"]), axr.Y(r["rmse"]))], size=6,
                      shape="cross", width=2)
            fig.stamp(ink, C_TRUE)
        ink = fig.ink()
        axr.vline(ink, rows[best]["sigma"], width=1, dashed=True)
        fig.stamp(ink, C_C)
        fig.text(88, 354, "RMS error against the clean truth", C_TEXT, 12, True)
        fig.text(axr.X(rows[best]["sigma"]) + 5, 376,
                 f"best {rows[best]['rmse']:.6f}", C_C, 11, True)
        fig.text(axr.X(rows[best]["sigma"]) + 5, 392,
                 f"at sigma {rows[best]['sigma']:.3f}", C_C, 11, True)
        fig.text(90, axr.Y(rows[0]["rmse"]) - 16,
                 f"raw {rows[0]['rmse']:.6f}", C_DIM, 11, True)
        fig.text(300, 558, "sigma [samples] ->", C_DIM, 11)

        # 下段右: 極値の数とピークの高さ
        axn = Ax(fig, 596, 372, W - 30, 552, (0.5, 45.0),
                 (0.0, max(r0["nmax"] for r0 in rows) * 1.12), logx=True)
        axn.panel(C_PANEL2)
        ink = fig.ink()
        axn.frame(ink)
        axn.xticks(ink, [1, 2, 5, 10, 20, 40], "%g")
        axn.yticks(ink, [0, 50, 100, 150, 200], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axn.hline(ink, true_max, width=1, dashed=True)
        fig.stamp(ink, C_C)
        ink = fig.ink()
        pts = [(axn.X(rr["sigma"]), axn.Y(rr["nmax"]))
               for rr in rows[1:k + 1]] if k >= 1 else []
        if len(pts) >= 2:
            ink.poly(pts, width=2)
        fig.stamp(ink, C_E)
        if k >= 1:
            ink = fig.ink()
            ink.marks([(axn.X(r["sigma"]), axn.Y(r["nmax"]))], size=6,
                      shape="cross", width=2)
            fig.stamp(ink, C_TRUE)
        fig.text(600, 354, "number of strict local maxima", C_TEXT, 12, True)
        fig.text(604, axn.Y(true_max) - 18, f"clean truth = {true_max}", C_C, 11, True)
        fig.text(820, 558, "sigma [samples] ->", C_DIM, 11)

        fig.box(84, 574, W - 30, H - 12, C_PANEL2)
        fig.text(96, 580, f"sigma {r['sigma']:6.3f}   rmse {r['rmse']:.6f} "
                          f"({rows[0]['rmse'] / max(r['rmse'], 1e-15):5.2f}x vs raw)   "
                          f"maxima {r['nmax']:3d} (truth {true_max})   "
                          f"peak {r['peak']:.6f} "
                          f"({100 * (r['peak'] / true_peak - 1):+6.2f} % vs the clean peak "
                          f"{true_peak:.6f})", C_TEXT, 13, True)
        msg = ("noise still forges extrema" if r["nmax"] > 3 * true_max else
               "the peak is being flattened" if r["peak"] < 0.92 * true_peak else
               "both readings are usable here")
        fig.text(96, 602, msg, C_B, 12, True)
        frames.append(fig.u8())

    info = save_flipbook(frames, "smoothing_tradeoff", labels, ms=220, hold_ms=1600,
                         log=log)
    facts = {
        "true_maxima": true_max, "true_peak": true_peak,
        "raw_rmse": rows[0]["rmse"], "raw_maxima": rows[0]["nmax"],
        "raw_peak": rows[0]["peak"],
        "best_sigma": rows[best]["sigma"], "best_rmse": rows[best]["rmse"],
        "best_peak": rows[best]["peak"], "best_maxima": rows[best]["nmax"],
        "best_gain": rows[0]["rmse"] / rows[best]["rmse"],
        "best_peak_loss_pct": 100 * (rows[best]["peak"] / true_peak - 1),
        "over_sigma": rows[-1]["sigma"], "over_rmse": rows[-1]["rmse"],
        "over_peak": rows[-1]["peak"],
        "over_peak_loss_pct": 100 * (rows[-1]["peak"] / true_peak - 1),
        "frames": len(rows),
        "ops": ["smooth_funct_1d_gauss", "local_min_max_funct_1d"],
    }
    return info, facts


# =========================================================================== #
# 展示 9: サンプリングとエイリアシング                              (GIF)      #
# =========================================================================== #
def ex_aliasing(log):
    f_true = 300.0
    dur = 0.5
    rates = np.arange(1300, 318, -32, dtype=int)      # すべて偶数 -> n も整数
    rows = []
    for fs in rates:
        n = int(round(dur * fs))
        t = np.arange(n) / float(fs)
        x = np.sin(2.0 * np.pi * f_true * t)
        f, mg = dsp.spectrum(x, float(fs))
        amp = mg * (2.0 / n)
        pk = int(np.argmax(amp))
        expected = abs(f_true - fs * round(f_true / fs))
        rows.append({"fs": float(fs), "n": n, "nyq": fs / 2.0, "t": t, "x": x,
                     "f": f, "amp": amp, "peak_hz": float(f[pk]),
                     "peak_amp": float(amp[pk]), "expected": float(expected),
                     "res": float(fs) / n,
                     "aliased": bool(fs / 2.0 < f_true)})
    first_alias = next(i for i, r in enumerate(rows) if r["aliased"])
    log(f"  {len(rows)} rates from {rates[0]} down to {rates[-1]} Hz; "
        f"true tone {f_true:g} Hz")
    log(f"  aliasing starts at fs = {rows[first_alias]['fs']:.0f} Hz "
        f"(Nyquist {rows[first_alias]['nyq']:.0f} Hz)")
    worst = max(abs(r["peak_hz"] - r["expected"]) for r in rows)
    log(f"  max |measured peak - folding prediction| = {worst:.6f} Hz "
        f"(bin resolution {rows[0]['res']:.4f} Hz)")
    log(f"  end of sweep: fs {rows[-1]['fs']:.0f} Hz -> peak "
        f"{rows[-1]['peak_hz']:.2f} Hz, amplitude {rows[-1]['peak_amp']:.6f} "
        f"(the tone is still full height, only its frequency is a lie)")

    tref = np.linspace(0.0, 0.03, 1400)
    xref = np.sin(2.0 * np.pi * f_true * tref)
    W, H = GIF_W, GIF_H
    frames, labels = [], []
    for k, r in enumerate(rows):
        labels.append(f"fs {r['fs']:.0f} Hz(Nyquist {r['nyq']:.0f} Hz)  /  "
                      f"ピークは {r['peak_hz']:.1f} Hz  /  "
                      + ("折り返し予測 |300 − fs·k| = "
                         f"{r['expected']:.1f} Hz" if r["aliased"] else "正しい"))
        fig = Fig(W, H)
        _header(fig, "Sampling and aliasing: the tone never changes, the reading does",
                f"true tone {f_true:g} Hz, {dur:g} s record, sampling rate swept down")
        # 上: 時間波形
        axt = Ax(fig, 84, 70, W - 30, 300, (0.0, 30.0), (-1.35, 1.35))
        axt.panel()
        ink = fig.ink()
        axt.frame(ink)
        axt.xticks(ink, [0, 5, 10, 15, 20, 25, 30], "%.0f")
        axt.yticks(ink, [-1, 0, 1], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axt.curve(ink, tref * 1e3, xref, width=2)
        fig.stamp(ink, C_DIM)
        keep = r["t"] <= 0.030
        ink = fig.ink()
        axt.curve(ink, r["t"][keep] * 1e3, r["x"][keep], width=2)
        fig.stamp(ink, C_B)
        ink = fig.ink()
        ink.marks([(axt.X(tv * 1e3), axt.Y(xv))
                   for tv, xv in zip(r["t"][keep], r["x"][keep])],
                  size=4, shape="cross", width=2)
        fig.stamp(ink, C_A)
        fig.text(88, 52, f"first 30 ms - the {f_true:g} Hz tone, the samples taken from "
                         f"it, and what the samples join up to", C_TEXT, 12, True)
        _legend(fig, W - 250, 78, [(f"true {f_true:g} Hz tone", C_DIM),
                                   ("samples", C_A),
                                   ("what the samples say", C_B)])
        fig.text(W - 250, 134, f"{int(keep.sum())} samples in 30 ms", C_DIM, 11)
        fig.text(W - 190, 306, "time [ms] ->", C_DIM, 11)

        # 下: スペクトル
        axf = Ax(fig, 84, 372, W - 30, 546, (0.0, 700.0), (0.0, 1.18))
        axf.panel()
        ink = fig.ink()
        axf.frame(ink)
        axf.xticks(ink, [0, 100, 200, 300, 400, 500, 600, 700], "%.0f")
        axf.yticks(ink, [0.0, 0.5, 1.0], "%.1f")
        fig.stamp(ink, C_AXIS)
        # Nyquist より上は「この記録に存在し得ない」領域
        fig.box(axf.X(r["nyq"]), axf.y0, axf.x1 + 1, axf.y1, (0.155, 0.125, 0.125))
        ink = fig.ink()
        axf.frame(ink)
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axf.curve(ink, r["f"], r["amp"], width=2)
        fig.stamp(ink, C_C)
        ink = fig.ink()
        axf.vline(ink, f_true, width=2, dashed=True)
        fig.stamp(ink, C_TRUE)
        ink = fig.ink()
        axf.vline(ink, r["nyq"], width=2)
        fig.stamp(ink, C_WARN)
        ink = fig.ink()
        ink.marks([(axf.X(r["peak_hz"]), axf.Y(r["peak_amp"]))], size=8,
                  shape="cross", width=2)
        fig.stamp(ink, C_E)
        fig.text(88, 354, "single-sided amplitude spectrum of the sampled record "
                          "(dsp.spectrum x 2/N)", C_TEXT, 12, True)
        fig.text(axf.X(f_true) + 6, 376, f"true {f_true:g} Hz", C_TRUE, 11, True)
        fig.text(axf.X(r["nyq"]) + 6, 396,
                 f"Nyquist {r['nyq']:.0f} Hz", C_WARN, 12, True)
        fig.text(axf.X(r["nyq"]) + 6, 412, "nothing above this line", C_WARN, 11)
        fig.text(axf.X(r["nyq"]) + 6, 428, "can exist in this record", C_WARN, 11)
        fig.text(30, 450, "amp", C_DIM, 11)
        fig.text(W - 230, 552, "frequency [Hz] ->", C_DIM, 11)

        fig.box(84, 568, W - 30, H - 12, C_PANEL2)
        fig.text(96, 574, f"fs {r['fs']:7.0f} Hz   Nyquist {r['nyq']:6.1f} Hz   "
                          f"{r['n']:4d} samples   bin {r['res']:.3f} Hz", C_TEXT, 13, True)
        if r["aliased"]:
            fig.text(96, 594, f"peak reads {r['peak_hz']:7.2f} Hz, amplitude "
                              f"{r['peak_amp']:.6f}   folding predicts "
                              f"|{f_true:g} - {r['fs']:.0f} k| = {r['expected']:.2f} Hz",
                     C_E, 12, True)
            fig.text(96, 612, "a full-height line at the wrong frequency - nothing "
                              "raised, nothing is NaN", C_E, 12, True)
        else:
            fig.text(96, 594, f"peak reads {r['peak_hz']:7.2f} Hz, amplitude "
                              f"{r['peak_amp']:.6f}   correct", C_C, 12, True)
            fig.text(96, 612, "Nyquist is still above the tone", C_C, 12, True)
        frames.append(fig.u8())

    info = save_flipbook(frames, "aliasing", labels, ms=260, hold_ms=1800, log=log)
    facts = {
        "true_tone_hz": f_true, "duration_s": dur,
        "rate_first": float(rates[0]), "rate_last": float(rates[-1]),
        "n_rates": len(rows),
        "first_alias_rate": rows[first_alias]["fs"],
        "first_alias_nyquist": rows[first_alias]["nyq"],
        "max_abs_prediction_error_hz": worst,
        "bin_resolution_hz": rows[0]["res"],
        "last": {"fs": rows[-1]["fs"], "nyquist": rows[-1]["nyq"],
                 "peak_hz": rows[-1]["peak_hz"], "peak_amp": rows[-1]["peak_amp"],
                 "expected": rows[-1]["expected"]},
        "table": [{"fs": r["fs"], "nyquist": r["nyq"], "peak_hz": r["peak_hz"],
                   "expected": r["expected"], "peak_amp": r["peak_amp"]}
                  for r in rows[::4]],
        "ops": ["spectrum"],
    }
    return info, facts


# =========================================================================== #
# 展示 10: 1D プロファイルはどこから来るか                          (PNG)      #
# =========================================================================== #
def ex_profile_sources(log):
    from PIL import Image
    # (1) 2D 画像の測定線 — 実写真(skimage coins、studio_assets 同梱)
    src = os.path.join(SAMPLES_IMG, "coins.png")
    with Image.open(src) as im:
        img2d = np.asarray(im.convert("L"), np.float64) / 255.0
    r0, c0, r1, c1 = 120, 6, 120, img2d.shape[1] - 6
    prof2d = measure.line_profile(img2d, (r0, c0), (r1, c1))
    st2d = measure.profile_stats(prof2d)

    # (2) 3D ボリュームのプローブ — 合成の球殻(内側に空洞)
    Dv = 96
    zz, yy, xx = np.mgrid[0:Dv, 0:Dv, 0:Dv]
    rr = np.sqrt((zz - 48.0) ** 2 + (yy - 48.0) ** 2 + (xx - 48.0) ** 2)
    vol = 0.08 + 0.75 * ((rr < 34.0) & (rr > 19.0)) + 0.35 * (rr < 9.0)
    t_mm, prof3d = volprobe.vol_profile_line(vol, (48.0, 48.0, 2.0),
                                            (48.0, 48.0, 93.0))
    # 立ち上がり -> 立ち下がりの対だけを厚みにするので、殻を 2 回横切れば 2 個返る。
    walls = [float(w) for w in
             volprobe.vol_wall_thickness(vol, (48.0, 48.0, 2.0), (48.0, 48.0, 93.0))]

    # (3) センサー時系列 — 音響記録
    fs = 2000.0
    sensor = A.synthesize_bearing_signal(fs, 0.25, carrier_hz=300.0, defect_hz=20.0,
                                         modulation=0.5, mode="impulse",
                                         noise_sigma=0.05, seed=11)
    feats = dsp.signal_features(sensor, fs)

    # 3 本とも「素の 1-D float64」なので funct1d がそのまま食える
    srcs = [("2D image, measurement line", prof2d, C_A, "measure.line_profile"),
            ("3D volume, probe line", prof3d, C_C, "volprobe.vol_profile_line"),
            ("sensor time series", sensor, C_B, "acoustics.synthesize_bearing_signal")]
    common = []
    for name, arr, col, op in srcs:
        f1 = F.create_funct_1d_array(arr)
        common.append({
            "name": name, "op": op, "color": col, "y": np.asarray(f1),
            "n": F.num_points_funct_1d(f1),
            "xr": F.x_range_funct_1d(f1), "yr": F.y_range_funct_1d(f1),
            "nzc": int(len(F.zero_crossings_funct_1d(f1))),
            "nmax": int(len(F.local_min_max_funct_1d(f1)["max"])),
        })
        log(f"  {name:28s} n={common[-1]['n']:4d} "
            f"y in [{common[-1]['yr'][0]:.4f}, {common[-1]['yr'][1]:.4f}] "
            f"zero-crossings {common[-1]['nzc']:3d} local maxima {common[-1]['nmax']:3d}")
    log(f"  2D profile stats: {st2d}")
    log(f"  3D probe: {prof3d.size} samples over {t_mm[-1]:.3f} voxel units; "
        f"wall thicknesses {walls} voxel units")
    log(f"  sensor features: rms {feats['rms']:.6f} zcr {feats['zero_crossing_rate']:.6f} "
        f"centroid {feats['centroid']:.4f} Hz")

    W, H = 1200, 900
    fig = Fig(W, H)
    _header(fig, "Where a 1-D profile comes from",
            "three different instruments, one representation - plain 1-D float64")

    # 上段: 3 つの出所
    pw = 360
    # (1) 画像 + 測定線
    thumb = _resize_nn(img2d, 200, pw)
    fig.blit(30, 74, _gray_rgb(thumb))
    ink = fig.ink()
    sy = 74 + 200 * (r0 / img2d.shape[0])
    ink.line((30 + pw * (c0 / img2d.shape[1]), sy),
             (30 + pw * (c1 / img2d.shape[1]), sy), width=2)
    ink.marks([(30 + pw * (c0 / img2d.shape[1]), sy),
               (30 + pw * (c1 / img2d.shape[1]), sy)], size=6, shape="cross", width=2)
    fig.stamp(ink, C_A)
    fig.text(30, 56, "1. 2D image (skimage coins, real photograph)", C_A, 12, True)
    fig.text(34, 282, f"line_profile row {r0}, cols {c0}..{c1} -> {prof2d.size} samples",
             C_DIM, 11)
    fig.text(34, 298, f"min {st2d['min']:.4f}  max {st2d['max']:.4f}  "
                      f"strongest edge at index {st2d['edge_at']}", C_DIM, 11)

    # (2) ボリュームの中央スライス + プローブ線
    sl = vol[48]
    fig.blit(410, 74, _gray_rgb(_resize_nn(sl, 200, pw)))
    ink = fig.ink()
    ink.line((410 + pw * (2.0 / Dv), 74 + 200 * (48.0 / Dv)),
             (410 + pw * (93.0 / Dv), 74 + 200 * (48.0 / Dv)), width=2)
    ink.marks([(410 + pw * (2.0 / Dv), 74 + 200 * (48.0 / Dv)),
               (410 + pw * (93.0 / Dv), 74 + 200 * (48.0 / Dv))], size=6,
              shape="cross", width=2)
    fig.stamp(ink, C_C)
    fig.text(410, 56, "2. 3D volume (synthetic shell), slice z = 48", C_C, 12, True)
    fig.text(414, 282, f"vol_profile_line (48,48,2) -> (48,48,93): {prof3d.size} samples",
             C_DIM, 11)
    fig.text(414, 298, "vol_wall_thickness pairs rising->falling edges: "
                       + " / ".join("%.2f" % w for w in walls)
                       + " voxel units", C_DIM, 11)

    # (3) センサー波形
    axs = Ax(fig, 800, 74, W - 30, 274, (0.0, 0.25),
             (-float(np.abs(sensor).max()) * 1.1, float(np.abs(sensor).max()) * 1.1))
    axs.panel(C_PANEL2)
    ink = fig.ink()
    axs.frame(ink)
    axs.xticks(ink, [0.0, 0.1, 0.2], "%.1f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    axs.curve(ink, np.arange(sensor.size) / fs, sensor, width=1)
    fig.stamp(ink, C_B)
    fig.text(800, 56, "3. sensor time series (acoustic record)", C_B, 12, True)
    fig.text(804, 282, f"{fs:g} Hz x 0.25 s = {sensor.size} samples, rms "
                       f"{feats['rms']:.4f}", C_DIM, 11)
    fig.text(804, 298, f"zero-crossing rate {feats['zero_crossing_rate']:.4f}, "
                       f"centroid {feats['centroid']:.1f} Hz", C_DIM, 11)

    # 合流: 同じ (x, y) 面に 3 本を正規化して重ねる
    fig.text(30, 336, "They arrive as the same thing: a 1-D float64 array indexed by "
                      "sample. funct1d takes all three without an adapter.",
             C_TEXT, 13, True)
    for i, cinfo in enumerate(common):
        y0 = 372 + i * 158
        ax = Ax(fig, 92, y0, W - 300, y0 + 120, (0.0, float(cinfo["n"] - 1)),
                (cinfo["yr"][0] - 0.06 * (cinfo["yr"][1] - cinfo["yr"][0]),
                 cinfo["yr"][1] + 0.06 * (cinfo["yr"][1] - cinfo["yr"][0])))
        ax.panel()
        ink = fig.ink()
        ax.frame(ink)
        ax.xticks(ink, np.linspace(0, cinfo["n"] - 1, 5), "%.0f")
        ax.yticks(ink, [cinfo["yr"][0], 0.5 * (cinfo["yr"][0] + cinfo["yr"][1]),
                        cinfo["yr"][1]], "%.3f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        ax.curve(ink, np.arange(cinfo["n"]), cinfo["y"], width=2)
        fig.stamp(ink, cinfo["color"])
        fig.text(96, y0 - 18, f"{cinfo['name']}   ({cinfo['op']})",
                 cinfo["color"], 12, True)
        fig.text(W - 288, y0 + 6, f"num_points_funct_1d  {cinfo['n']}", C_TEXT, 12, True)
        fig.text(W - 288, y0 + 26, f"x_range  {cinfo['xr'][0]:.0f} .. {cinfo['xr'][1]:.0f}",
                 C_DIM, 12)
        fig.text(W - 288, y0 + 46, f"y_range  {cinfo['yr'][0]:.4f} .. {cinfo['yr'][1]:.4f}",
                 C_DIM, 12)
        fig.text(W - 288, y0 + 66, f"zero_crossings  {cinfo['nzc']}", C_DIM, 12)
        fig.text(W - 288, y0 + 86, f"local maxima    {cinfo['nmax']}", C_DIM, 12)
    fig.text(30, H - 26, "The 1-D wing has no source type of its own on purpose: an "
                         "arbitrary real 1-D array is a genuine profile from any of "
                         "these instruments, so a dedicated type would only cut the "
                         "connection.", C_DIM, 12)

    frame = fig.u8()
    info = save_png(frame, "profile_sources", log)
    facts = {
        "image_source": "studio_assets/sample_images/coins.png (skimage coins, real photo)",
        "profile2d": {"n": int(prof2d.size), **{k: float(v) if k != "n" else int(v)
                                                for k, v in st2d.items()}},
        "profile3d": {"n": int(prof3d.size), "length_voxels": float(t_mm[-1]),
                      "min": float(prof3d.min()), "max": float(prof3d.max()),
                      "wall_thicknesses": walls},
        "sensor": {"n": int(sensor.size), "rate_hz": fs,
                   "rms": float(feats["rms"]),
                   "zero_crossing_rate": float(feats["zero_crossing_rate"]),
                   "centroid_hz": float(feats["centroid"])},
        "funct1d": [{k: (list(map(float, v)) if isinstance(v, tuple) else v)
                     for k, v in c.items() if k not in ("y", "color")}
                    for c in common],
        "ops": ["line_profile", "profile_stats", "vol_profile_line",
                "vol_wall_thickness", "signal_features", "create_funct_1d_array",
                "num_points_funct_1d", "x_range_funct_1d", "y_range_funct_1d",
                "zero_crossings_funct_1d", "local_min_max_funct_1d"],
    }
    return info, facts


# =========================================================================== #
# 展示 11: 極値検出と照合                                           (GIF)      #
# =========================================================================== #
def ex_peak_match(log):
    n = 400
    centres = [60, 150, 245, 330]
    width = 9.0
    idx = np.arange(n, dtype=np.float64)
    base = np.zeros(n)
    for c in centres:
        base += np.exp(-0.5 * ((idx - c) / width) ** 2)
    half = 40
    tmpl = np.exp(-0.5 * ((np.arange(2 * half + 1) - float(half)) / width) ** 2)

    sigmas = np.linspace(0.0, 0.42, 30)
    rows = []
    for s in sigmas:
        rng = np.random.default_rng(7)              # seed 固定 = 決定的
        y = base + rng.normal(0.0, float(s), n)
        sm = F.smooth_funct_1d_gauss(y, sigma=3.0)
        raw_ex = F.local_min_max_funct_1d(y)["max"]
        sm_ex = F.local_min_max_funct_1d(sm)["max"]
        strong = np.array([int(i) for i in sm_ex if sm[i] > 0.45])
        shifts = [F.match_funct_1d_trans(y[c - half:c + half + 1], tmpl)["shift"]
                  for c in centres]
        scores = [F.match_funct_1d_trans(y[c - half:c + half + 1], tmpl)["score"]
                  for c in centres]
        rows.append({"sigma": float(s), "y": y, "sm": sm,
                     "raw": raw_ex, "sm_ex": sm_ex, "strong": strong,
                     "shifts": shifts, "scores": scores,
                     "n_raw": int(len(raw_ex)), "n_sm": int(len(sm_ex)),
                     "n_strong": int(strong.size),
                     "pos_err": (float(np.max(np.abs(np.sort(strong) - np.array(centres))))
                                 if strong.size == len(centres) else None)})
    log(f"  {len(rows)} noise levels 0 .. {sigmas[-1]:.3f}")
    for r in rows[::7]:
        log(f"  sigma={r['sigma']:.3f}  raw maxima {r['n_raw']:3d}  "
            f"after gauss {r['n_sm']:3d}  above 0.45: {r['n_strong']}  "
            f"positions {list(map(int, r['strong']))}  match shifts {r['shifts']}")
    exact = [r for r in rows if all(s == 0 for s in r["shifts"])]
    log(f"  match_funct_1d_trans returned the exact lag 0 for all four peaks in "
        f"{len(exact)}/{len(rows)} noise levels "
        f"(up to sigma {max(r['sigma'] for r in exact):.3f})")

    W, H = GIF_W, GIF_H
    frames, labels = [], []
    for k, r in enumerate(rows):
        labels.append(f"雑音 σ={r['sigma']:.3f}  /  生の極大 {r['n_raw']} 個  →  "
                      f"平滑+門で {r['n_strong']} 個(真値 {len(centres)})  /  "
                      f"テンプレート lag {r['shifts']}")
        fig = Fig(W, H)
        _header(fig, "Finding the peaks, then matching a template to them",
                f"four gaussian peaks (sigma {width:g} samples) at "
                f"{', '.join(map(str, centres))}, noise swept")
        axp = Ax(fig, 84, 70, W - 260, 300, (0.0, float(n - 1)), (-1.35, 1.62))
        axp.panel()
        ink = fig.ink()
        axp.frame(ink)
        axp.xticks(ink, [0, 60, 150, 245, 330, 399], "%.0f")
        axp.yticks(ink, [-1, 0, 1], "%.0f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axp.curve(ink, idx, r["y"], width=1)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        axp.curve(ink, idx, base, width=2)
        fig.stamp(ink, C_C)
        ink = fig.ink()
        axp.curve(ink, idx, r["sm"], width=2)
        fig.stamp(ink, C_A)
        ink = fig.ink()
        ink.marks([(axp.X(i), axp.Y(r["y"][i])) for i in r["raw"]], size=3,
                  shape="cross", width=1)
        fig.stamp(ink, C_WARN)
        ink = fig.ink()
        ink.marks([(axp.X(i), axp.Y(r["sm"][i])) for i in r["strong"]], size=9,
                  shape="square", width=2)
        fig.stamp(ink, C_B)
        ink = fig.ink()
        for c in centres:
            axp.vline(ink, c, width=1, dashed=True)
        fig.stamp(ink, C_TRUE, alpha=0.45)
        fig.text(88, 52, "profile, smoothed profile, and every strict local maximum",
                 C_TEXT, 12, True)
        _legend(fig, W - 250, 78, [("noisy input", C_DIM), ("noise-free truth", C_C),
                                   ("gauss sigma 3", C_A),
                                   ("raw local maxima", C_WARN),
                                   ("accepted peaks", C_B)])
        fig.text(W - 250, 168, f"noise sigma {r['sigma']:.4f}", C_TEXT, 13, True)
        fig.text(W - 250, 190, f"raw maxima      {r['n_raw']:3d}", C_WARN, 12, True)
        fig.text(W - 250, 210, f"after smoothing {r['n_sm']:3d}", C_A, 12, True)
        fig.text(W - 250, 230, f"above 0.45      {r['n_strong']:3d}", C_B, 12, True)
        fig.text(W - 250, 250, f"true count        {len(centres)}", C_TRUE, 12, True)
        if r["pos_err"] is not None:
            fig.text(W - 250, 274, f"worst position err {r['pos_err']:.0f} sample",
                     C_TEXT, 12, True)
        fig.text(W - 190, 306, "sample index ->", C_DIM, 11)

        # 下: テンプレートと 4 つの照合
        fig.text(88, 344, f"match_funct_1d_trans of the {2 * half + 1}-sample template "
                          f"against an equally long window centred on each true peak",
                 C_TEXT, 12, True)
        for j, c in enumerate(centres):
            x0 = 84 + j * 230
            axm = Ax(fig, x0, 376, x0 + 200, 500, (0.0, float(2 * half)),
                     (-1.3, 1.62))
            axm.panel(C_PANEL2)
            ink = fig.ink()
            axm.frame(ink)
            axm.xticks(ink, [0, 40, 80], "%.0f")
            fig.stamp(ink, C_AXIS)
            ink = fig.ink()
            axm.curve(ink, np.arange(2 * half + 1),
                      r["y"][c - half:c + half + 1], width=1)
            fig.stamp(ink, C_DIM)
            ink = fig.ink()
            axm.curve(ink, np.arange(2 * half + 1), tmpl, width=2)
            fig.stamp(ink, C_D)
            ink = fig.ink()
            axm.vline(ink, float(half), width=1, dashed=True)
            fig.stamp(ink, C_TRUE)
            ok = r["shifts"][j] == 0
            fig.text(x0, 358, f"window at {c}", C_TEXT, 12, True)
            fig.text(x0, 506, f"shift {r['shifts'][j]:+d}  (truth 0)",
                     C_C if ok else C_E, 12, True)
            fig.text(x0, 524, f"score {r['scores'][j]:8.4f}", C_DIM, 11)
        _legend(fig, W - 250, 376, [("window", C_DIM), ("template", C_D)])

        fig.box(84, 552, W - 30, H - 12, C_PANEL2)
        fig.text(96, 558, "local_min_max_funct_1d uses STRICT inequalities and has no "
                          "noise model: on the raw trace it reports every sample that "
                          "happens to sit above both neighbours.", C_DIM, 12)
        fig.text(96, 578, f"here that is {r['n_raw']} maxima for {len(centres)} peaks. "
                          f"Smoothing first, then a height gate, is the whole method - "
                          f"and it is the caller's decision, not the operator's.",
                 C_DIM, 12)
        allok = all(s == 0 for s in r["shifts"])
        fig.text(96, 600, ("all four template lags are exactly 0 - "
                           "the correlation peak has not moved yet"
                           if allok else
                           "at this noise level at least one lag has moved off 0"),
                 C_C if allok else C_E, 12, True)
        frames.append(fig.u8())

    info = save_flipbook(frames, "peak_match", labels, ms=240, hold_ms=1600, log=log)
    facts = {
        "true_centres": centres, "peak_sigma_samples": width,
        "template_length": int(tmpl.size), "n_frames": len(rows),
        "sigma_max": float(sigmas[-1]),
        "raw_maxima_first": rows[0]["n_raw"], "raw_maxima_last": rows[-1]["n_raw"],
        "smoothed_maxima_last": rows[-1]["n_sm"],
        "accepted_last": rows[-1]["n_strong"],
        "positions_last": [int(v) for v in rows[-1]["strong"]],
        "exact_lag_levels": len(exact), "total_levels": len(rows),
        "exact_lag_up_to_sigma": max(r["sigma"] for r in exact),
        "ops": ["smooth_funct_1d_gauss", "local_min_max_funct_1d",
                "match_funct_1d_trans"],
    }
    return info, facts


# =========================================================================== #
# 展示 12: 包絡線の端が切れると 76 % 間違う                         (GIF)      #
# =========================================================================== #
def ex_envelope_truncation(log):
    z_step, n_planes, lam = 0.05, 241, 0.6
    z = np.arange(n_planes) * z_step
    z_max = float(z[-1])
    surfaces = np.round(np.linspace(6.0, 0.30, 32), 6)
    rows = []
    for s in surfaces:
        sig = I.csi_signal_simulate(surface_um=float(s), z_start_um=0.0,
                                    z_step_um=z_step, n_planes=n_planes,
                                    wavelength_um=lam)
        env = I.csi_envelope(sig)
        # 端レベルは op と同じ定義(中央値基準・[0,1] にクリップ)を再計算する。
        med = float(np.median(env))
        top = float(env.max()) - med
        ends = float(max(env[0], env[-1])) - med
        edge = float(np.clip(ends / top if top > 0 else 1.0, 0.0, 1.0))
        forced = float(I.csi_peak_position(sig, z_step_um=z_step, z_start_um=0.0,
                                           wavelength_um=lam, mode="gaussian",
                                           max_edge_envelope=1.0))
        try:
            I.csi_peak_position(sig, z_step_um=z_step, z_start_um=0.0,
                                wavelength_um=lam, mode="gaussian")
            refused = False
        except ValueError:
            refused = True
        rows.append({"surface": float(s), "sig": sig, "env": env, "edge": edge,
                     "forced": forced, "refused": refused,
                     "err": forced - float(s),
                     "rel": 100.0 * (forced - float(s)) / float(s),
                     "argmax": int(np.argmax(env))})
    first_refusal = next((i for i, r in enumerate(rows) if r["refused"]), None)
    worst = max(rows, key=lambda r: abs(r["rel"]))
    log(f"  scan {n_planes} planes x {z_step} um = {z_max:g} um, lambda {lam} um")
    for r in rows[::5]:
        log(f"  surface {r['surface']:6.3f} um  edge {r['edge']:.4f}  "
            f"argmax plane {r['argmax']:3d}/{n_planes}  returns {r['forced']:8.4f} um  "
            f"error {r['err']:+8.4f} um ({r['rel']:+8.2f} %)  "
            f"{'REFUSED at default threshold' if r['refused'] else 'accepted'}")
    if first_refusal is not None:
        log(f"  the operator starts refusing at surface "
            f"{rows[first_refusal]['surface']:.3f} um (edge level "
            f"{rows[first_refusal]['edge']:.4f}); at that point the forced answer is "
            f"already off by {rows[first_refusal]['rel']:+.2f} %")
    log(f"  worst: surface {worst['surface']:.3f} um -> {worst['forced']:.4f} um "
        f"= {worst['rel']:+.2f} % wrong, and its argmax is plane {worst['argmax']} "
        f"of {n_planes} (interior, so an end-of-scan check does not fire)")

    W, H = GIF_W, GIF_H
    frames, labels = [], []
    for k, r in enumerate(rows):
        labels.append(f"表面 {r['surface']:.2f} µm  /  端レベル {r['edge']:.4f}  /  "
                      f"返り値 {r['forced']:.4f} µm({r['rel']:+.1f} %)  /  "
                      + ("op は拒否" if r["refused"] else "op は受理"))
        fig = Fig(W, H)
        _header(fig, "A truncated envelope returns a plausible, badly wrong height",
                f"coherence scan {z_max:g} um in {n_planes} planes of {z_step} um, "
                f"lambda {lam} um")
        axz = Ax(fig, 84, 70, W - 262, 320, (0.0, z_max), (-0.02, 1.0))
        axz.panel()
        ink = fig.ink()
        axz.frame(ink)
        axz.xticks(ink, [0, 2, 4, 6, 8, 10, 12], "%.0f")
        axz.yticks(ink, [0.0, 0.25, 0.5, 0.75, 1.0], "%.2f")
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axz.curve(ink, z, r["sig"], width=1)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        axz.curve(ink, z, r["env"], width=2)
        fig.stamp(ink, C_A)
        ink = fig.ink()
        axz.vline(ink, r["surface"], width=2, dashed=True)
        fig.stamp(ink, C_TRUE)
        ink = fig.ink()
        axz.vline(ink, r["forced"], width=2)
        fig.stamp(ink, C_E if abs(r["rel"]) > 1.0 else C_C)
        ink = fig.ink()
        ink.marks([(axz.X(z[r["argmax"]]), axz.Y(r["env"][r["argmax"]]))],
                  size=8, shape="cross", width=2)
        fig.stamp(ink, C_B)
        # 端の高さを目に見える形で
        ink = fig.ink()
        ink.marks([(axz.X(0.0), axz.Y(r["env"][0])),
                   (axz.X(z_max), axz.Y(r["env"][-1]))], size=7, shape="square",
                  width=2)
        fig.stamp(ink, C_WARN)
        fig.text(88, 52, "z-scan interferogram and its analytic envelope", C_TEXT, 12, True)
        fig.text(axz.X(r["surface"]) + 6, 76, f"true {r['surface']:.3f} um",
                 C_TRUE, 11, True)
        fig.text(axz.X(r["forced"]) + 6, 96, f"returned {r['forced']:.4f} um",
                 C_E if abs(r["rel"]) > 1.0 else C_C, 11, True)
        fig.text(88, 300, "the two squares are the envelope at the scan ends - "
                          "when they lift off the floor, part of the peak is outside "
                          "the scan", C_WARN, 11)
        fig.text(30, 190, "I(z)", C_DIM, 11)
        fig.text(W - 430, 326, "scan position z [um] ->", C_DIM, 11)

        fig.box(W - 252, 70, W - 24, 320, C_PANEL2)
        fig.text(W - 242, 78, "readout", C_TEXT, 12, True)
        fig.text(W - 242, 100, f"true surface {r['surface']:8.3f} um", C_TRUE, 12, True)
        fig.text(W - 242, 122, f"returned     {r['forced']:8.4f} um",
                 C_E if abs(r["rel"]) > 1.0 else C_C, 12, True)
        fig.text(W - 242, 144, f"error        {r['err']:+8.4f} um", C_TEXT, 12, True)
        fig.text(W - 242, 166, f"relative     {r['rel']:+8.2f} %",
                 C_E if abs(r["rel"]) > 1.0 else C_DIM, 12, True)
        fig.text(W - 242, 194, f"edge level   {r['edge']:8.4f}", C_WARN, 12, True)
        fig.text(W - 242, 214, f"threshold        0.0500", C_DIM, 12)
        fig.text(W - 242, 236, f"envelope argmax", C_DIM, 11)
        fig.text(W - 242, 252, f"plane {r['argmax']} of {n_planes}", C_B, 12, True)
        fig.text(W - 242, 272, "-- interior, so an" if 0 < r["argmax"] < n_planes - 1
                 else "-- pinned to an end", C_DIM, 11)
        fig.text(W - 242, 288, "   end-check does not" if 0 < r["argmax"] < n_planes - 1
                 else "", C_DIM, 11)
        fig.text(W - 242, 304, "   fire" if 0 < r["argmax"] < n_planes - 1 else "",
                 C_DIM, 11)

        # 下: 誤差 vs 表面位置(掃引の履歴)
        axe = Ax(fig, 84, 400, W - 262, 552, (0.2, 6.2),
                 (min(-80.0, min(rr["rel"] for rr in rows) * 1.1), 12.0))
        axe.panel()
        ink = fig.ink()
        axe.frame(ink)
        axe.xticks(ink, [0.5, 1, 2, 3, 4, 5, 6], "%g")
        axe.yticks(ink, [0, -20, -40, -60, -80], "%.0f")
        fig.stamp(ink, C_AXIS)
        if first_refusal is not None:
            fig.box(axe.x0, axe.y0,
                    axe.X(rows[first_refusal]["surface"]), axe.y1, (0.155, 0.125, 0.125))
            ink = fig.ink()
            axe.frame(ink)
            fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        axe.hline(ink, 0.0, width=1)
        fig.stamp(ink, C_DIM)
        ink = fig.ink()
        pts = [(axe.X(rr["surface"]), axe.Y(rr["rel"])) for rr in rows[:k + 1]]
        if len(pts) >= 2:
            ink.poly(pts, width=2)
        fig.stamp(ink, C_E)
        ink = fig.ink()
        ink.marks([(axe.X(r["surface"]), axe.Y(r["rel"]))], size=7, shape="cross",
                  width=2)
        fig.stamp(ink, C_TRUE)
        fig.text(88, 382, "relative error of the returned height [%] as the surface "
                          "walks toward the edge of the scan", C_TEXT, 12, True)
        if first_refusal is not None:
            fig.text(axe.x0 + 8, 404, "operator refuses in here", C_WARN, 11, True)
            fig.text(axe.x0 + 8, 420, "(edge level above 0.05)", C_WARN, 11)
        fig.text(W - 430, 558, "true surface height [um] ->", C_DIM, 11)

        fig.box(W - 252, 400, W - 24, 552, C_PANEL2)
        if r["refused"]:
            fig.text(W - 242, 408, "csi_peak_position", C_TEXT, 12, True)
            fig.text(W - 242, 428, "REFUSES this scan.", C_E, 13, True)
            fig.text(W - 242, 452, "the number shown was", C_DIM, 11)
            fig.text(W - 242, 468, "forced out with", C_DIM, 11)
            fig.text(W - 242, 484, "max_edge_envelope=1.0", C_DIM, 11)
            fig.text(W - 242, 508, "the refusal is the", C_C, 11, True)
            fig.text(W - 242, 524, "feature: there is", C_C, 11, True)
            fig.text(W - 242, 540, "nothing to repair.", C_C, 11, True)
        else:
            fig.text(W - 242, 408, "csi_peak_position", C_TEXT, 12, True)
            fig.text(W - 242, 428, "accepts this scan.", C_C, 13, True)
            fig.text(W - 242, 452, "the envelope sits", C_DIM, 11)
            fig.text(W - 242, 468, "inside the scan and", C_DIM, 11)
            fig.text(W - 242, 484, "the height is right", C_DIM, 11)
            fig.text(W - 242, 500, f"to {abs(r['err']):.2e} um.", C_DIM, 11)
        fig.text(14, H - 26,
                 "Zero-padding and reflect-padding were both measured and both made "
                 "it worse - truncation is missing physics, not an FFT artefact.",
                 C_DIM, 12)
        frames.append(fig.u8())

    info = save_flipbook(frames, "envelope_truncation", labels, ms=240, hold_ms=2000,
                         log=log)
    facts = {
        "scan_planes": n_planes, "z_step_um": z_step, "z_range_um": z_max,
        "wavelength_um": lam, "n_frames": len(rows),
        "surface_first": rows[0]["surface"], "surface_last": rows[-1]["surface"],
        "first_refusal_surface": (None if first_refusal is None
                                  else rows[first_refusal]["surface"]),
        "first_refusal_edge": (None if first_refusal is None
                               else rows[first_refusal]["edge"]),
        "worst_surface": worst["surface"], "worst_returned": worst["forced"],
        "worst_rel_pct": worst["rel"], "worst_argmax_plane": worst["argmax"],
        "centred_error_um": rows[0]["err"], "centred_edge": rows[0]["edge"],
        "table": [{"surface": r["surface"], "edge": r["edge"], "returned": r["forced"],
                   "rel_pct": r["rel"], "argmax": r["argmax"], "refused": r["refused"]}
                  for r in rows[::5]],
        "ops": ["csi_signal_simulate", "csi_envelope", "csi_peak_position"],
    }
    return info, facts


# =========================================================================== #
# 展示 13: 欠陥周波数が出てくるまで(工程)               (フリップブック GIF)  #
# =========================================================================== #
def ex_envelope_flow(log):
    """同じ寸法のコマで工程が進むので ``flipbook`` に束ねる(並べるより速い)。"""
    rpm, n_el, d_el, d_pitch = 1800.0, 9, 8.0, 40.0
    geo = A.bearing_defect_frequencies(rpm, n_el, d_el, d_pitch, 0.0)
    fd = float(geo["bpfo_hz"])                       # 外輪剥離の通過周波数
    fs, dur, fc = 25600.0, 1.0, 3000.0
    x = A.synthesize_bearing_signal(fs, dur, carrier_hz=fc, defect_hz=fd,
                                    modulation=0.5, mode="impulse",
                                    noise_sigma=0.05, seed=5)
    t = np.arange(x.size) / fs
    freqs, mag = dsp.spectrum(x, fs)
    amp = mag * (2.0 / x.size)
    i_fd = int(np.argmin(np.abs(freqs - fd)))
    sk = A.spectral_kurtosis(x, fs, win=64)
    lo = max(1.0, sk["max_freq"] - sk["bin_hz"])
    hi = sk["max_freq"] + sk["bin_hz"]
    band = dsp.bandpass(x, fs, lo, hi, order=4)
    env = dsp.envelope(band)
    es = A.envelope_spectrum(x, fs, lo, hi)
    # 対照 2 本 — 「その数字は本物か」を数で決めるための材料。
    #   (a) 真の共振をまたぐ帯域(人が答えを知っている場合の理想)
    #   (b) 同じ帯域に入れた白色雑音(中身が無いときに何が返るか)
    res_lo, res_hi = fc - 400.0, fc + 400.0
    es_res = A.envelope_spectrum(x, fs, res_lo, res_hi)
    ctrl = np.random.default_rng(1).normal(0.0, 1.0, x.size)
    es_ctrl = A.envelope_spectrum(ctrl, fs, lo, hi)
    # 手で組み直した合成が op の返りと一致することを確かめる(同じ経路のはず)
    e0 = env - env.mean()
    mag_manual = np.abs(np.fft.rfft(e0)) * (2.0 / e0.size)
    agree = float(np.max(np.abs(mag_manual - es["magnitude"])))
    lines = {"FTF": geo["ftf_hz"], "BPFO": geo["bpfo_hz"], "BPFI": geo["bpfi_hz"],
             "BSF": geo["bsf_hz"], "2xBSF": geo["bsf_hz_2x"]}
    best_name = min(lines, key=lambda k: abs(lines[k] - es["peak_freq"]))
    rel = 100.0 * abs(lines[best_name] - es["peak_freq"]) / lines[best_name]
    log(f"  geometry: BPFO {geo['bpfo_hz']:.6f} Hz (synthesised at that rate)")
    log(f"  raw amplitude at {fd:g} Hz = {amp[i_fd]:.6e}; the record's peak is "
        f"{amp.max():.6f} at {freqs[int(np.argmax(amp))]:.0f} Hz")
    log(f"  SK win {sk['win']} -> band {lo:.0f}-{hi:.0f} Hz "
        f"(max SK {sk['max_kurtosis']:.4f} at {sk['max_freq']:.0f} Hz)")
    log(f"  envelope spectrum peak {es['peak_freq']:.6f} Hz amp "
        f"{es['peak_amplitude']:.6f} band_fraction {es['band_fraction']:.6f} "
        f"prominence {es['peak_prominence']:.1f}")
    log(f"  manual dsp.bandpass -> dsp.envelope -> rfft agrees with "
        f"envelope_spectrum to {agree:.3e}")
    log(f"  closest kinematic rate: {best_name} = {lines[best_name]:.6f} Hz "
        f"({rel:.4f} % away)")

    PW, PH = 940, 430
    ms = 60                                          # 抜粋する時間窓 [ms]
    keep = t <= ms / 1000.0
    steps = []

    def _base(title, sub):
        fig = Fig(PW, PH)
        fig.box(0, 0, PW, 32, (0.085, 0.095, 0.115))
        fig.text(12, 6, title, C_TEXT, 14, True)
        fig.text(12 + 9.0 * len(title) + 16, 9, sub, C_DIM, 11)
        return fig

    # 1. 生波形
    fig = _base("1. the raw record",
                f"impulse bearing signal, {fs:g} Hz x {dur:g} s, noise sigma 0.05")
    ax = Ax(fig, 78, 56, PW - 24, PH - 78, (0.0, ms),
            (-float(np.abs(x).max()) * 1.1, float(np.abs(x).max()) * 1.1))
    ax.panel()
    ink = fig.ink()
    ax.frame(ink)
    ax.xticks(ink, [0, 10, 20, 30, 40, 50, 60], "%.0f")
    ax.yticks(ink, [-1, 0, 1], "%.0f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax.curve(ink, t[keep] * 1e3, x[keep], width=1)
    fig.stamp(ink, C_A)
    fig.text(82, PH - 40, f"first {ms} ms of {x.size} samples. Nothing here says "
                          f"{fd:.0f} Hz - the impacts are buried under the ringing.",
             C_DIM, 12)
    fig.text(PW - 130, PH - 18, "time [ms] ->", C_DIM, 11)
    steps.append(fig.u8())

    # 2. 生スペクトル
    fig = _base("2. the raw spectrum", "dsp.spectrum x 2/N - the resonance is loud, "
                                       "the defect rate is not there")
    ax = Ax(fig, 78, 56, PW - 24, PH - 78, (0.0, 8000.0), (0.0, amp.max() * 1.12))
    ax.panel()
    ink = fig.ink()
    ax.frame(ink)
    ax.xticks(ink, [0, 1000, 2000, 3000, 4000, 6000, 8000], "%.0f")
    ax.yticks(ink, [0.0, 0.05, 0.10], "%.2f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax.curve(ink, freqs, amp, width=2)
    fig.stamp(ink, C_A)
    ink = fig.ink()
    ax.vline(ink, fd, width=2, dashed=True)
    fig.stamp(ink, C_WARN)
    fig.text(ax.X(fd) + 8, 66, f"defect {fd:.0f} Hz", C_WARN, 11, True)
    fig.text(ax.X(fd) + 8, 82, f"amplitude {amp[i_fd]:.3e}", C_WARN, 11, True)
    fig.text(82, PH - 40, f"peak {amp.max():.6f} at "
                          f"{freqs[int(np.argmax(amp))]:.0f} Hz (the structure's "
                          f"resonance). Reading this spectrum finds the wrong thing.",
             C_DIM, 12)
    fig.text(PW - 170, PH - 18, "frequency [Hz] ->", C_DIM, 11)
    steps.append(fig.u8())

    # 3. スペクトル尖度で帯域を選ぶ
    fig = _base("3. let the machine pick the band",
                f"acoustics.spectral_kurtosis, win {sk['win']} = "
                f"{sk['window_seconds'] * 1e3:.2f} ms")
    ax = Ax(fig, 78, 56, PW - 24, PH - 78, (0.0, fs / 2.0),
            (min(-1.2, float(sk["kurtosis"].min()) * 1.2),
             float(sk["max_kurtosis"]) * 1.15))
    ax.panel()
    ink = fig.ink()
    ax.frame(ink)
    ax.xticks(ink, [0, 2000, 4000, 6000, 8000, 10000, 12000], "%.0f")
    ax.yticks(ink, [-1, 0, 1, 2, 3], "%.0f")
    fig.stamp(ink, C_AXIS)
    fig.box(ax.X(lo), ax.y0, ax.X(hi), ax.y1, (0.14, 0.16, 0.10))
    ink = fig.ink()
    ax.frame(ink)
    ax.hline(ink, 0.0, width=1)
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax.curve(ink, sk["freqs"], sk["kurtosis"], width=2)
    fig.stamp(ink, C_D)
    ink = fig.ink()
    ink.marks([(ax.X(sk["max_freq"]), ax.Y(sk["max_kurtosis"]))], size=8,
              shape="cross", width=2)
    fig.stamp(ink, C_E)
    fig.text(ax.X(hi) + 8, 66, f"band {lo:.0f} - {hi:.0f} Hz", C_B, 12, True)
    fig.text(ax.X(hi) + 8, 84, f"max SK {sk['max_kurtosis']:.4f}", C_E, 11, True)
    fig.text(82, PH - 40, "the operator returns a BAND, not a line: max_freq +- one "
                          f"bin ({sk['bin_hz']:.0f} Hz). The true resonance is "
                          f"{fc:.0f} Hz.", C_DIM, 12)
    steps.append(fig.u8())

    # 4. 帯域通過
    fig = _base("4. band-pass that band", f"dsp.bandpass({lo:.0f}, {hi:.0f} Hz, order 4)")
    ax = Ax(fig, 78, 56, PW - 24, PH - 78, (0.0, ms),
            (-float(np.abs(x).max()) * 1.1, float(np.abs(x).max()) * 1.1))
    ax.panel()
    ink = fig.ink()
    ax.frame(ink)
    ax.xticks(ink, [0, 10, 20, 30, 40, 50, 60], "%.0f")
    ax.yticks(ink, [-1, 0, 1], "%.0f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax.curve(ink, t[keep] * 1e3, x[keep], width=1)
    fig.stamp(ink, C_DIM)
    ink = fig.ink()
    ax.curve(ink, t[keep] * 1e3, band[keep], width=1)
    fig.stamp(ink, C_B)
    _legend(fig, PW - 230, 64, [("raw", C_DIM), ("band-passed", C_B)])
    fig.text(82, PH - 58, f"band_fraction {es['band_fraction']:.6f} in this band - and "
                          f"white noise put through the SAME band reads "
                          f"{es_ctrl['band_fraction']:.6f}.", C_DIM, 12)
    fig.text(82, PH - 40, f"So band_fraction alone does NOT separate them here. "
                          f"Across the true resonance ({res_lo:.0f}-{res_hi:.0f} Hz) it "
                          f"would read {es_res['band_fraction']:.6f}.", C_WARN, 12)
    steps.append(fig.u8())

    # 5. 包絡線
    fig = _base("5. take the envelope", "dsp.envelope (analytic / Hilbert)")
    ax = Ax(fig, 78, 56, PW - 24, PH - 78, (0.0, ms),
            (-float(np.abs(band).max()) * 1.15, float(np.abs(band).max()) * 1.15))
    ax.panel()
    ink = fig.ink()
    ax.frame(ink)
    ax.xticks(ink, [0, 10, 20, 30, 40, 50, 60], "%.0f")
    ax.yticks(ink, [-0.2, 0.0, 0.2], "%.1f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax.curve(ink, t[keep] * 1e3, band[keep], width=1)
    fig.stamp(ink, C_DIM)
    ink = fig.ink()
    ax.curve(ink, t[keep] * 1e3, env[keep], width=2)
    fig.stamp(ink, C_C)
    ink = fig.ink()
    for j in range(int(ms / (1000.0 / fd)) + 1):
        ax.vline(ink, j * 1000.0 / fd, width=1, dashed=True)
    fig.stamp(ink, C_TRUE, alpha=0.6)
    _legend(fig, PW - 250, 64, [("band-passed", C_DIM), ("envelope", C_C),
                                (f"every 1/{fd:.0f} s", C_TRUE)])
    fig.text(82, PH - 40, f"the impacts are now visible as bumps in the envelope, "
                          f"one every {1000.0 / fd:.3f} ms. The carrier is gone; only "
                          f"the modulation is left.", C_DIM, 12)
    steps.append(fig.u8())

    # 6. 包絡線スペクトル
    fig = _base("6. transform the envelope", "acoustics.envelope_spectrum")
    ax = Ax(fig, 78, 56, PW - 24, PH - 78, (0.0, 600.0),
            (0.0, float(es["peak_amplitude"]) * 1.2))
    ax.panel()
    ink = fig.ink()
    ax.frame(ink)
    ax.xticks(ink, [0, 108, 216, 324, 432, 500, 600], "%.0f")
    ax.yticks(ink, [0.0, 0.025, 0.05, 0.075], "%.3f")
    fig.stamp(ink, C_AXIS)
    ink = fig.ink()
    ax.curve(ink, es_ctrl["freqs"], es_ctrl["magnitude"], width=1)
    fig.stamp(ink, C_DIM)
    ink = fig.ink()
    ax.curve(ink, es["freqs"], es["magnitude"], width=2)
    fig.stamp(ink, C_C)
    ink = fig.ink()
    ink.marks([(ax.X(es["peak_freq"]), ax.Y(es["peak_amplitude"]))], size=8,
              shape="cross", width=2)
    fig.stamp(ink, C_TRUE)
    _legend(fig, PW - 300, 62, [("this record", C_C),
                                ("white-noise control, same band", C_DIM)])
    fig.text(ax.X(es["peak_freq"]) + 8, 110,
             f"peak {es['peak_freq']:.6f} Hz", C_TRUE, 12, True)
    fig.text(ax.X(es["peak_freq"]) + 8, 128,
             f"prominence {es['peak_prominence']:.1f}", C_C, 11, True)
    fig.text(ax.X(es["peak_freq"]) + 8, 144,
             f"control  {es_ctrl['peak_prominence']:.1f} at "
             f"{es_ctrl['peak_freq']:.0f} Hz", C_DIM, 11, True)
    fig.text(82, PH - 58, f"resolution {es['resolution_hz']:.6f} Hz/bin. Rebuilt by "
                          f"hand from dsp.bandpass + dsp.envelope + rfft, the two "
                          f"agree to {agree:.2e}.", C_DIM, 12)
    fig.text(82, PH - 40, f"prominence separates what band_fraction could not: "
                          f"{es['peak_prominence']:.0f} against the control's "
                          f"{es_ctrl['peak_prominence']:.0f}. Return numbers, not a "
                          f"verdict - that is the design.", C_C, 12)
    steps.append(fig.u8())

    # 7. 幾何と照合
    fig = _base("7. match it against the geometry",
                f"acoustics.bearing_defect_frequencies({rpm:g} rpm, N={n_el}, "
                f"d={d_el:g}, D={d_pitch:g})")
    ax = Ax(fig, 78, 56, PW - 24, PH - 78, (0.0, 200.0), (-0.6, 5.2))
    ax.panel()
    ink = fig.ink()
    ax.frame(ink)
    ax.xticks(ink, [0, 25, 50, 75, 100, 125, 150, 175, 200], "%.0f")
    fig.stamp(ink, C_AXIS)
    for bi, (nm, val) in enumerate(lines.items()):
        yy = ax.Y(4.6 - bi)
        col = C_E if nm == best_name else C_D
        ink = fig.ink()
        ink.line((ax.X(0.0), yy), (ax.X(min(val, 200.0)), yy), width=11)
        fig.stamp(ink, col)
        fig.text(84, yy - 24, f"{nm} {val:.4f} Hz", col, 11, True)
    ink = fig.ink()
    ax.vline(ink, es["peak_freq"], width=3)
    fig.stamp(ink, C_TRUE)
    fig.text(ax.X(es["peak_freq"]) + 8, 62,
             f"measured {es['peak_freq']:.4f} Hz", C_TRUE, 12, True)
    fig.text(82, PH - 40, f"closest kinematic rate: {best_name} at "
                          f"{lines[best_name]:.4f} Hz, {rel:.4f} % away. A real bearing "
                          f"slips ~1 %, so this is a match - and an exact one would be "
                          f"a coincidence.", C_DIM, 12)
    steps.append(fig.u8())

    step_labels = [
        f"生の記録 — {ms} ms 抜粋、{x.size} サンプル",
        f"生スペクトル — 欠陥率 {fd:.0f} Hz の振幅は {amp[i_fd]:.2e}(何も無い)",
        f"スペクトル尖度 — 復調帯域 {lo:.0f}–{hi:.0f} Hz を機械が選ぶ",
        f"帯域通過 — band_fraction {es['band_fraction']:.4f}"
        f"(白色雑音の対照 {es_ctrl['band_fraction']:.4f}= 区別できない)",
        f"包絡線 — {1000.0 / fd:.3f} ms ごとの衝撃が見える",
        f"包絡線スペクトル — ピーク {es['peak_freq']:.4f} Hz、突出度 "
        f"{es['peak_prominence']:.0f}(白色雑音の対照は {es_ctrl['peak_prominence']:.0f})",
        f"幾何と照合 — {best_name} {lines[best_name]:.4f} Hz と {rel:.4f} % 一致",
    ]
    info = save_flipbook(steps, "envelope_flow", step_labels, ms=1500, hold_ms=3000,
                         title="欠陥周波数が出てくるまで(工程)", log=log)
    facts = {
        "rpm": rpm, "n_elements": n_el, "element_diameter_mm": d_el,
        "pitch_diameter_mm": d_pitch,
        "bpfo_hz": geo["bpfo_hz"], "bpfi_hz": geo["bpfi_hz"],
        "ftf_hz": geo["ftf_hz"], "bsf_hz": geo["bsf_hz"],
        "synth_defect_hz": fd, "carrier_hz": fc, "rate_hz": fs, "duration_s": dur,
        "raw_amplitude_at_defect": float(amp[i_fd]),
        "raw_peak_amplitude": float(amp.max()),
        "raw_peak_hz": float(freqs[int(np.argmax(amp))]),
        "sk_max_kurtosis": sk["max_kurtosis"], "sk_max_freq": sk["max_freq"],
        "sk_bin_hz": sk["bin_hz"], "sk_win": sk["win"],
        "band_low_hz": lo, "band_high_hz": hi,
        "envelope_peak_freq": es["peak_freq"],
        "envelope_peak_amplitude": es["peak_amplitude"],
        "envelope_band_fraction": es["band_fraction"],
        "envelope_prominence": es["peak_prominence"],
        "envelope_resolution_hz": es["resolution_hz"],
        "control_band_fraction": es_ctrl["band_fraction"],
        "control_prominence": es_ctrl["peak_prominence"],
        "control_peak_freq": es_ctrl["peak_freq"],
        "resonance_band": (res_lo, res_hi),
        "resonance_band_fraction": es_res["band_fraction"],
        "resonance_band_peak_freq": es_res["peak_freq"],
        "resonance_band_peak_amplitude": es_res["peak_amplitude"],
        "resonance_band_prominence": es_res["peak_prominence"],
        "manual_vs_operator_max_abs_diff": agree,
        "closest_rate_name": best_name, "closest_rate_hz": lines[best_name],
        "closest_rate_error_pct": rel,
        "steps": len(steps),
        "ops": ["bearing_defect_frequencies", "synthesize_bearing_signal", "spectrum",
                "spectral_kurtosis", "bandpass", "envelope", "envelope_spectrum"],
    }
    return info, facts


# =========================================================================== #
# 展示 14: 分数オクターブ帯域の一族                             (タイル PNG)  #
# =========================================================================== #
def ex_octave_family(log):
    """同じ軸に fraction 違いを当てた 6 枚 = 並べて比べるもの → ``contact_sheet``。"""
    fs, dur, a = 48000.0, 0.5, 0.7
    t = np.arange(int(round(dur * fs))) / fs
    x = a * np.sin(2.0 * np.pi * 1000.0 * t)
    closed = 10.0 * np.log10(a * a / 2.0)
    fractions = (1, 2, 3, 6, 12, 24)
    panels, labels, rows = [], [], []
    for fr in fractions:
        b = A.octave_bands(fraction=fr, f_min=22.0, f_max=20000.0)
        s = A.octave_spectrum(x, fs, fraction=fr, f_min=22.0, f_max=20000.0, ref=1.0)
        c, L = s["centers"], s["levels"]
        k = int(np.argmax(L))
        exact = bool(np.any(np.abs(c - 1000.0) < 1e-9))
        n_clamped = int(np.sum(s["clamped"]))
        rows.append({"fraction": fr, "n_bands": int(c.size), "max_level": float(L[k]),
                     "max_center": float(c[k]), "exact_1k": exact,
                     "diff_from_closed": float(L[k] - closed),
                     "clamped": n_clamped,
                     "total_level": float(s["total_level"]),
                     "nominal_at_max": float(s["nominal"][k]),
                     "bandwidth_at_max": float(b["upper"][k] - b["lower"][k])})
        log(f"  1/{fr:<2d}: {c.size:3d} bands  max {L[k]:10.6f} dB @ "
            f"{c[k]:9.4f} Hz  exact 1 kHz centre: {exact}  "
            f"diff from 10log10(A^2/2) {L[k] - closed:+.3e} dB  "
            f"floored bands {n_clamped}")

        PW, PH = 470, 360
        fig = Fig(PW, PH)
        fig.box(0, 0, PW, 30, (0.085, 0.095, 0.115))
        fig.text(10, 6, f"1/{fr} octave", C_TEXT, 14, True)
        fig.text(110, 8, f"{c.size} bands   band level [dB] vs frequency [Hz], log",
                 C_DIM, 11)
        ax = Ax(fig, 62, 52, PW - 18, PH - 80, (22.0, 20000.0), (-72.0, 4.0),
                logx=True)
        ax.panel()
        ink = fig.ink()
        ax.frame(ink)
        ax.xticks(ink, [31.5, 125, 500, 2000, 8000], "%g", size=10)
        ax.yticks(ink, [0, -20, -40, -60], "%.0f", size=10)
        fig.stamp(ink, C_AXIS)
        ink = fig.ink()
        ax.hline(ink, closed, width=1, dashed=True)
        fig.stamp(ink, C_TRUE)
        # 帯域を階段で描く(帯域端から端まで水平、間を垂直に繋ぐ)
        pts = []
        for lo_e, hi_e, lv in zip(b["lower"], b["upper"], L):
            v = max(lv, -70.0)
            pts.append((ax.X(lo_e), ax.Y(v)))
            pts.append((ax.X(hi_e), ax.Y(v)))
        ink = fig.ink()
        ink.poly(pts, width=2)
        fig.stamp(ink, C_A)
        ink = fig.ink()
        ax.vline(ink, 1000.0, width=1, dashed=True)
        fig.stamp(ink, C_B)
        ink = fig.ink()
        ink.marks([(ax.X(c[k]), ax.Y(L[k]))], size=8, shape="cross", width=2)
        fig.stamp(ink, C_E)
        fig.text(ax.X(1000.0) - 66, 56, "1 kHz", C_B, 11, True)
        fig.text(26, 150, "dB", C_DIM, 10)
        fig.text(12, PH - 44, f"max {L[k]:.6f} dB at {c[k]:.3f} Hz", C_E, 12, True)
        fig.text(12, PH - 26,
                 ("a band IS centred at 1000.000 Hz" if exact else
                  "NO band is centred at 1000 Hz (even fraction)"),
                 C_C if exact else C_WARN, 12, True)
        panels.append(fig.u8())
        labels.append(f"1/{fr} oct  {c.size} 帯域  1 kHz 中心"
                      + ("あり" if exact else "なし"))

    odd = [r for r in rows if r["exact_1k"]]
    even = [r for r in rows if not r["exact_1k"]]
    worst = max(abs(r["diff_from_closed"]) for r in rows)
    log(f"  closed form 10log10({a}^2/2) = {closed:.6f} dB; every fraction reports it "
        f"to within {worst:.3e} dB")
    log(f"  exact 1 kHz centre exists for fractions "
        f"{[r['fraction'] for r in odd]} and not for {[r['fraction'] for r in even]}")

    info = save_sheet(panels, "octave_family", labels, ncols=3,
                      title="分数オクターブ帯域 — 偶数分数には 1 kHz 帯域が無い",
                      panel_px=470, log=log)
    facts = {
        "tone_hz": 1000.0, "tone_amplitude": a, "rate_hz": fs, "duration_s": dur,
        "closed_form_db": closed, "max_abs_diff_from_closed_db": worst,
        "fractions_with_exact_1k": [r["fraction"] for r in odd],
        "fractions_without_exact_1k": [r["fraction"] for r in even],
        "table": rows,
        "ops": ["octave_bands", "octave_spectrum"],
    }
    return info, facts


# =========================================================================== #
# キャプション原稿                                                             #
# =========================================================================== #
CAPTIONS = {
    "defect_not_in_raw": {
        "title": "欠陥周波数は生スペクトルに無い",
        "text": lambda f: (
            f"共振 {f['carrier_hz']:.0f} Hz を欠陥率 {f['defect_hz']:.0f} Hz で振幅変調した"
            f"軸受信号({f['rate_hz']:.0f} Hz × {f['duration_s']:.0f} s、変調度 "
            f"{f['modulation']:.1f})。上の生スペクトルは {f['defect_hz']:.0f} Hz に "
            f"{f['raw_amplitude_at_defect']:.3e} しか無く、エネルギーは搬送波 "
            f"{f['raw_amplitude_at_carrier']:.6f} と側帯波 {f['raw_sideband_lower']:.6f} / "
            f"{f['raw_sideband_upper']:.6f}(= m/2 ちょうど)に居る。下の包絡線スペクトルは"
            f"同じ記録から {f['envelope_peak_freq']:.6f} Hz に振幅 "
            f"{f['envelope_peak_amplitude']:.6f} = 変調度そのものを返す"
            f"(band_fraction {f['envelope_band_fraction']:.6f})。"),
    },
    "kurtosis_band": {
        "title": "スペクトルカートシスが復調帯域を選ぶ",
        "text": lambda f: (
            f"共振の位置を人が知らないとき、どの帯域で復調するかを機械に決めさせる。"
            f"STFT 平面({f['stft_bins']} bin × {f['stft_interior_frames']} 内側フレーム、"
            f"全 {f['stft_total_frames']} フレームのうち)にスペクトル尖度を重ね、幅 "
            f"{f['band_width_hz']:.0f} Hz の復調帯域を掃引した。SK の最大は "
            f"{f['sk_max_kurtosis']:.4f} @ {f['sk_max_freq']:.0f} Hz(窓 {f['sk_win']} = "
            f"{f['sk_window_ms']:.2f} ms、bin {f['sk_bin_hz']:.0f} Hz、推定器の標準偏差 "
            f"{f['sk_noise_sigma']:.4f})で、その帯域の band_fraction は "
            f"{f['sk_band_fraction']:.4f}(最悪の帯域は {f['worst_band_fraction']:.4f})。"
            f"包絡線のピークはどの帯域でも欠陥率に立つ ―― 動くのは「記録のどれだけが"
            f"その帯域に居るか」のほうである。"),
    },
    "window_sweep": {
        "title": "窓長を間違えると負の尖度が出る",
        "text": lambda f: (
            f"衝撃が {f['impact_period_ms']:.3f} ms ごとに来る軸受信号(真の共振 "
            f"{f['true_resonance_hz']:.0f} Hz)で窓長を {f['table'][0]['win']} から "
            f"{f['table'][-1]['win']} まで掃引した。窓が衝撃の間隔より長くなると"
            f"どのフレームにも衝撃が 1 個ずつ入り、その帯域は構成上「定常」に見える。"
            f"窓 {f['negative_windows'][0]['win']}({f['negative_windows'][0]['ms']:.2f} ms)"
            f"で最大 SK は {f['negative_windows'][0]['max']:+.4f} ―― 負の値を、共振から "
            f"{abs(f['negative_windows'][0]['at'] - f['true_resonance_hz']):.0f} Hz 離れた "
            f"{f['negative_windows'][0]['at']:.0f} Hz で報告する。例外は出ない。"
            f"窓を掃引することはこの op の使い方の一部であって最適化ではない。"),
    },
    "order_tracking": {
        "title": "次数比分析 — 角度領域で立場が逆転する",
        "text": lambda f: (
            f"600 → 1800 rpm の走行記録({f['duration_s']:.0f} s、{f['rate_hz']:.0f} Hz、"
            f"次数 1.0 と 3.5、固定共振 400 Hz、計 {f['total_revolutions']:.4f} 回転)を "
            f"{f['window_s']:.1f} s の窓で滑らせる。素朴なスペクトルでは次数 3.5 が "
            f"{f['ordinary_order35_amp']:.6f}(真値 1.0 の 7 %)まで潰れ、−3 dB 幅は "
            f"{f['ordinary_order35_width_hz']:.2f} Hz に広がる。角度領域に置き直すと同じ成分が "
            f"{f['order_spectrum_order35_amp']:.6f}、幅 {f['order_spectrum_order35_bins'] - 1} bin "
            f"({f['order_spectrum_order35_width']:.5f} 次数)。逆に 400 Hz の固定共振は"
            f"次数軸では平均回転数で次数 {f['resonance_order_at_mean_rpm']:.2f} へ散る"
            f"(振幅 {f['resonance_amp_in_order_domain']:.6f})。この逆転が診断そのもの。"),
    },
    "bearing_geometry": {
        "title": "軸受の幾何から欠陥周波数",
        "text": lambda f: (
            f"{f['rpm']:.0f} rpm、ピッチ径 {f['pitch_diameter_mm']:.0f} mm の軸受で、"
            f"転動体数 → 接触角 → 転動体径の順に掃引した({f['frames']} フレーム)。"
            f"BPFO は {f['bpfo_range'][0]:.4f} → {f['bpfo_range'][1]:.4f} Hz、BPFI は "
            f"{f['bpfi_range'][0]:.4f} → {f['bpfi_range'][1]:.4f} Hz まで動く。全フレームで "
            f"`BPFO + BPFI − N·f_r` の最大絶対値は {f['max_abs_identity_1']:.3e}、"
            f"`BPFO − N·FTF` は {f['max_abs_identity_2']:.3e} ―― float64 で厳密にゼロで、"
            f"これは d と D を取り違えると即座に壊れる恒等式である。数表からではなく"
            f"幾何から再導出しているので、こう書ける。"),
    },
    "weighting_ac": {
        "title": "A 特性・C 特性の重み付け ―― 1 kHz は構成上ちょうど 0 dB",
        "text": lambda f: (
            f"重み付け曲線は公表オフセット定数を足すのではなく**自身の 1 kHz 値で割って**"
            f"作ってあるので、A(1000) も C(1000) も丸めではなく Python の float として厳密に "
            f"{f['a_at_1k']:.1f} になる(実測 `== 0.0` は "
            f"{f['a_at_1k_is_exact_zero']} / {f['c_at_1k_is_exact_zero']})。"
            f"純音を {f['n_tones']} 点掃引して `equivalent_level` の重み付き差 "
            f"`L_A − L_Z` を曲線値 `A(f)` と突き合わせると、最大差は "
            f"{f['max_abs_a_mismatch_db']:.2e} dB(C 特性は {f['max_abs_c_mismatch_db']:.2e} dB)。"
            f"振幅 1 の正弦の `L_eq(Z)` は閉形式 10log10(A²/2) = "
            f"{f['leq_z_closed_form_db']:.6f} dB で、実測もその値。"),
    },
    "funct1d_truth": {
        "title": "funct1d の解析真値",
        "text": lambda f: (
            f"答えが先に分かっている入力だけで組んだ 1 枚。`derivate_funct_1d(sin)/dx` と "
            f"cos の最大差は {f['derivative_max_error']:.3e}(格子 dx = {f['dx']:.6f}、"
            f"中心差分は 2 次なので残差は dx² で効く)。`zero_crossings_funct_1d` が返す "
            f"{len(f['zero_crossing_indices'])} 個の交差は、線形内挿すると "
            f"{', '.join(f'{v:.6f}π' for v in f['zero_crossing_x_over_pi'])} ―― 整数倍からの"
            f"最大ずれ {f['zero_crossing_max_deviation']:.3e}。減衰振動からは周期 "
            f"{f['period_s']:.6f} s(真値 {f['period_true_s']:.6f})、半周期 "
            f"{f['half_period_s']:.6f} s(真値 {f['half_period_true_s']:.6f})、時定数 "
            f"{f['tau_s']:.6f} s(真値 {f['tau_true_s']:.1f})、遅延 {f['match_shift']} サンプル"
            f"(真値 {f['match_shift_true']}、微分で白色化してから照合)が戻る。"),
    },
    "smoothing_tradeoff": {
        "title": "平滑化のトレードオフ",
        "text": lambda f: (
            f"減衰 5 Hz 振動 + N(0, 0.06) にガウス平滑を掛け、σ を {f['frames'] - 1} 段掃引した。"
            f"生の信号は真値 {f['true_maxima']} 個の極大に対して {f['raw_maxima']} 個を報告する"
            f"(`local_min_max_funct_1d` は狭義不等式で、雑音モデルを持たない)。RMS 誤差は "
            f"σ = {f['best_sigma']:.3f} で最小の {f['best_rmse']:.6f}(生の "
            f"{f['best_gain']:.2f} 倍良い)になり、そのときピーク高さは真値から "
            f"{f['best_peak_loss_pct']:+.2f} %。掛けすぎると σ = {f['over_sigma']:.1f} で "
            f"RMS 誤差が {f['over_rmse']:.6f} まで悪化し、ピークは "
            f"{f['over_peak_loss_pct']:+.2f} % なまる。雑音は減るが極値はなまる ―― "
            f"最小点はあるが、無料ではない。"),
    },
    "aliasing": {
        "title": "サンプリングとエイリアシング",
        "text": lambda f: (
            f"{f['true_tone_hz']:.0f} Hz の純音は一度も変えず、サンプリング周波数だけを "
            f"{f['rate_first']:.0f} Hz から {f['rate_last']:.0f} Hz へ {f['n_rates']} 段下げた"
            f"({f['duration_s']:.1f} s 記録、bin {f['bin_resolution_hz']:.0f} Hz)。fs = "
            f"{f['first_alias_rate']:.0f} Hz(Nyquist {f['first_alias_nyquist']:.0f} Hz)から"
            f"折り返しが始まり、最後は fs = {f['last']['fs']:.0f} Hz で "
            f"{f['last']['peak_hz']:.2f} Hz に振幅 {f['last']['peak_amp']:.6f} の線が立つ ―― "
            f"高さは満額のまま、周波数だけが嘘。全 {f['n_rates']} 段で実測ピークと折り返しの"
            f"予測 |f − fs·k| の差は最大 {f['max_abs_prediction_error_hz']:.3f} Hz。"
            f"Nyquist の線から右は、この記録に原理的に存在し得ない領域として焼いてある。"),
    },
    "profile_sources": {
        "title": "1D プロファイルはどこから来るか",
        "text": lambda f: (
            f"2D 画像の測定線(実写真 coins、{f['profile2d']['n']} サンプル、最強エッジは"
            f"添字 {f['profile2d']['edge_at']})、3D ボリュームのプローブ"
            f"({f['profile3d']['n']} サンプル、壁厚 "
            + " / ".join("%.2f" % w for w in f["profile3d"]["wall_thicknesses"])
            + f" voxel)、センサー時系列({f['sensor']['n']} サンプル、rms "
            f"{f['sensor']['rms']:.4f}、スペクトル重心 {f['sensor']['centroid_hz']:.1f} Hz)。"
            f"3 本とも素の 1-D float64 で届くので、`funct1d` はアダプタ無しでそのまま食える。"
            f"1D ウィングに専用の型を作らなかったのはこのためで ―― 任意の実数 1-D は"
            f"どの計器から来ても本当に正当なプロファイルであり、型を切ると接続を失うだけ。"),
    },
    "peak_match": {
        "title": "極値検出と照合",
        "text": lambda f: (
            f"既知の 4 点({', '.join(map(str, f['true_centres']))})に立てたガウスピークへ"
            f"雑音を σ = 0 から {f['sigma_max']:.2f} まで {f['n_frames']} 段加えた。"
            f"`local_min_max_funct_1d` は狭義不等式なので、生の波形では極大が "
            f"{f['raw_maxima_first']} 個から {f['raw_maxima_last']} 個へ暴発する。"
            f"σ = 3 のガウス平滑と高さ 0.45 の門を通すと最後まで "
            f"{f['accepted_last']} 個({f['positions_last']})に落ち着く。"
            f"`match_funct_1d_trans` は同じ長さの窓とテンプレートを突き合わせるかぎり、"
            f"{f['total_levels']} 段のうち {f['exact_lag_levels']} 段"
            f"(σ {f['exact_lag_up_to_sigma']:.3f} まで)で 4 点すべて lag = 0 を厳密に返す。"),
    },
    "envelope_flow": {
        "title": "欠陥周波数が出てくるまで(工程)",
        "text": lambda f: (
            f"幾何から出した外輪通過周波数 BPFO = {f['bpfo_hz']:.4f} Hz でわざと鳴らした"
            f"軸受記録を、7 工程で診断まで持っていく。生スペクトルでは欠陥率の振幅は "
            f"{f['raw_amplitude_at_defect']:.2e} しか無く、目立つのは "
            f"{f['raw_peak_hz']:.0f} Hz の構造共振({f['raw_peak_amplitude']:.4f})。"
            f"スペクトル尖度(窓 {f['sk_win']}、最大 {f['sk_max_kurtosis']:.4f} @ "
            f"{f['sk_max_freq']:.0f} Hz)が復調帯域 {f['band_low_hz']:.0f}–"
            f"{f['band_high_hz']:.0f} Hz を選び(真の共振 {f['carrier_hz']:.0f} Hz より "
            f"{f['carrier_hz'] - 0.5 * (f['band_low_hz'] + f['band_high_hz']):.0f} Hz 低い ―― "
            f"SK が返すのは帯域であって線ではない)、帯域通過 → 包絡線 → 変換で "
            f"{f['envelope_peak_freq']:.4f} Hz。それが幾何の "
            f"{f['closest_rate_name']} {f['closest_rate_hz']:.4f} Hz と "
            f"{f['closest_rate_error_pct']:.4f} % で一致する。**正直な内訳**: この帯域の "
            f"band_fraction は {f['envelope_band_fraction']:.4f} で、同じ帯域に通した"
            f"白色雑音の {f['control_band_fraction']:.4f} と区別がつかない。分けるのは"
            f"突出度のほうで、{f['envelope_prominence']:.0f} 対 "
            f"{f['control_prominence']:.0f} である(共振をまたぐ "
            f"{f['resonance_band'][0]:.0f}–{f['resonance_band'][1]:.0f} Hz を人が選べば "
            f"band_fraction は {f['resonance_band_fraction']:.4f} まで上がる)。"
            f"`dsp.bandpass` + `dsp.envelope` + rfft で手組みした結果と op の返りは "
            f"{f['manual_vs_operator_max_abs_diff']:.1e} で一致した(作り直していない証拠)。"),
    },
    "octave_family": {
        "title": "分数オクターブ帯域 ―― 偶数分数には 1 kHz 帯域が無い",
        "text": lambda f: (
            f"振幅 {f['tone_amplitude']} の {f['tone_hz']:.0f} Hz 純音を、1/1・1/2・1/3・"
            f"1/6・1/12・1/24 オクターブで測った 6 枚。帯域レベルはどの分数でも閉形式 "
            f"10log10(A²/2) = {f['closed_form_db']:.6f} dB を返す(最大差 "
            f"{f['max_abs_diff_from_closed_db']:.1e} dB)。違うのは**どの帯域が**それを"
            f"報告するかで、fraction が奇数 {f['fractions_with_exact_1k']} では "
            f"1000.000 Hz ちょうどを中心とする帯域があるが、偶数 "
            f"{f['fractions_without_exact_1k']} では指数のオフセットにより 1000 Hz が"
            f"帯域**端**になり、同じエネルギーが "
            + ", ".join("%.2f Hz" % r["max_center"]
                        for r in f["table"] if not r["exact_1k"])
            + f" を中心とする半端な帯域から報告される。定義であって不具合ではないが、"
            f"「1 kHz でのレベル」を引用するときに知っていないと嘘になる。"
            f"空の帯域は −inf ではなく床(−200 dB)に落ちる。"),
    },
    "envelope_truncation": {
        "title": "包絡線の端が切れると 76 % 間違う",
        "text": lambda f: (
            f"{f['z_range_um']:.0f} µm の走査({f['scan_planes']} plane × "
            f"{f['z_step_um']} µm)の中で、表面を中央 {f['surface_first']:.1f} µm から端の "
            f"{f['surface_last']:.2f} µm まで {f['n_frames']} 段歩かせた。中央では誤差 "
            f"{abs(f['centred_error_um']):.1e} µm。表面が {f['worst_surface']:.2f} µm まで"
            f"寄ると `csi_peak_position` は {f['worst_returned']:.4f} µm を返す ―― 有限で、"
            f"もっともらしく、{abs(f['worst_rel_pct']):.0f} % 間違っている。しかも包絡線の "
            f"argmax は {f['scan_planes']} plane 中の {f['worst_argmax_plane']} 番目、つまり"
            f"**内部**なので「端に張り付いたら拒否」という素直な検査は発動しない。"
            f"中央値基準の端レベルが {f['first_refusal_edge']:.4f} を超えた表面 "
            f"{f['first_refusal_surface']:.2f} µm から op は拒否に転じる"
            f"(図の値は `max_edge_envelope=1.0` で強制的に取り出したもの)。"),
    },
}

EXHIBIT_ORDER = [
    ("defect_not_in_raw", ex_defect_not_in_raw),
    ("kurtosis_band", ex_kurtosis_band),
    ("window_sweep", ex_window_sweep),
    ("order_tracking", ex_order_tracking),
    ("bearing_geometry", ex_bearing_geometry),
    ("weighting_ac", ex_weighting_ac),
    ("funct1d_truth", ex_funct1d_truth),
    ("smoothing_tradeoff", ex_smoothing_tradeoff),
    ("aliasing", ex_aliasing),
    ("profile_sources", ex_profile_sources),
    ("peak_match", ex_peak_match),
    ("envelope_truncation", ex_envelope_truncation),
    ("envelope_flow", ex_envelope_flow),
    ("octave_family", ex_octave_family),
]

# 束ね方の宣言(記事の縦を伸ばさないための判断を、コードに残しておく)。
#   still  = 原寸 1 枚(主張そのもの / 軸と数値が読めないと意味が無い)
#   gif    = コマ送り GIF(掃引・工程。flipbook がラベルと進捗バーを焼く)
#   sheet  = タイル(同じ軸にパラメータ違いを当てた小さなプロットを 3 枚以上束ねる)
BUNDLING = {
    "defect_not_in_raw": "still",   # 主張そのもの(生 vs 包絡線)
    "funct1d_truth": "still",       # 数値表が主役
    "profile_sources": "still",     # 3 つの出所と合流を 1 枚で見せる図
    "octave_family": "sheet",       # fraction 違い 6 枚 = 並べて比べる
    "envelope_flow": "gif",         # 同寸で工程が進む = フリップブック
}


def _write_exhibit_md(results: dict, log) -> str:
    """キャプション原稿を書く。記事本体(docs/articles/*.md)には一切触れない。"""
    os.makedirs(EXHIBITS, exist_ok=True)
    path = os.path.join(EXHIBITS, "wing1d.md")
    lines = [
        "<!-- tools/gen_wing1d_gallery.py が自動生成。記事 md への挿入候補であり、",
        "     このファイル自体は記事ではない。数値はすべて生成時の実測値。 -->",
        "",
        "# 信号・音響・1D ウィング — 展示キャプション原稿",
        "",
        "生成元: `tools/gen_wing1d_gallery.py`(`py -3.11 tools/gen_wing1d_gallery.py`)。",
        "画像はすべて Fullseye の `imagedraw` op と numpy 合成で描いており(matplotlib 不使用)、",
        "図に焼いた数値は 1 つ残らずその場で op を呼んで得た実測値である。乱数は seed 固定、",
        "掃引格子も固定なので再生成でバイト列が一致する(`--verify` で検査)。",
        "",
        "束ね方は `tools/exhibit_tile.py` の 3 種に従う ―― **コマ送り GIF**(`flipbook`、",
        "掃引と工程。各コマに工程名と `i/N` の進捗バーが焼いてあるので止めても意味が分かる)、",
        "**タイル**(`contact_sheet`、同じ軸にパラメータ違いを当てた小さなプロットを束ねる)、",
        "**原寸 1 枚**(主張そのもの・軸と数値が読めないと意味が無い図)。静止画の Markdown は",
        "すべて **サムネイル表示 + クリックで原寸** の形で出してある。",
        "",
    ]
    for i, (name, _) in enumerate(EXHIBIT_ORDER, start=1):
        if name not in results:
            continue
        info, facts = results[name]["info"], results[name]["facts"]
        cap = CAPTIONS[name]
        ops = ", ".join(f"`{o}`" for o in facts["ops"])
        stem = info["stem"]
        caption = (f"**{cap['title']}** ―― {cap['text'](facts)} 使用 op: {ops}。")
        lines.append(f"## {i}. {cap['title']}")
        lines.append("")
        if info["kind"] == "gif":
            # GIF は動いてこそなので直接埋め込む(markdown_animation の形)。
            lines.append(markdown_animation(stem, cap["title"], caption).rstrip())
            lines.append("")
            lines.append(f"- GIF: `docs/articles/assets/media/{stem}.gif` "
                         f"({info['frames']} コマ, "
                         f"{info['shape'][1]}x{info['shape'][0]} px, "
                         f"{info['bytes'] / 1e6:.2f} MB, {info['ms']} ms/コマ・"
                         f"最終コマ {info['hold_ms']} ms)")
            lines.append(f"- サムネ: `docs/articles/assets/thumbs/{stem}_thumb.jpg`")
        else:
            # 静止画は必ずサムネ表示 + クリックで原寸(markdown の形)。
            lines.append(markdown(stem, cap["title"], caption).rstrip())
            lines.append("")
            kindja = "タイル" if info["kind"] == "sheet" else "原寸 1 枚"
            extra = (f", {info['frames']} パネル / {info['ncols']} 列"
                     if info["kind"] == "sheet" else "")
            lines.append(f"- PNG({kindja}): `docs/articles/assets/{stem}.png` "
                         f"({info['shape'][1]}x{info['shape'][0]} px, "
                         f"{info['bytes'] / 1e3:.0f} kB{extra})")
            lines.append(f"- サムネ(記事はこちらを表示): "
                         f"`docs/articles/assets/{stem}_thumb.jpg` "
                         f"({info['thumb_bytes'] / 1e3:.0f} kB)")
        lines.append(f"- 束ね方: {BUNDLING.get(name, 'gif')}")
        lines.append(f"- SHA-256: `{info['sha256']}`")
        lines.append("")
        lines.append("<details><summary>この図に焼いた実測値</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(
            {k: v for k, v in facts.items() if k != "ops"},
            ensure_ascii=False, indent=2, default=_jsonable))
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    log(f"  captions -> {path} ({os.path.getsize(path) / 1e3:.0f} kB)")
    return path


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


# --------------------------------------------------------------------------- #
# CLI                                                                           #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    names = [n for n, _ in EXHIBIT_ORDER]
    ap = argparse.ArgumentParser(
        description="信号・音響・1D ウィングの展示(GIF 9 / PNG 3)を作る")
    ap.add_argument("--only", default="", help=f"comma list of {','.join(names)}")
    ap.add_argument("--verify", action="store_true",
                    help="2 回生成して SHA-256 が一致することを確かめる")
    ap.add_argument("--no-captions", action="store_true",
                    help="キャプション原稿を書かない")
    args = ap.parse_args(argv)

    want = {s.strip() for s in args.only.split(",") if s.strip()} or set(names)
    unknown = want - set(names)
    if unknown:
        print(f"unknown exhibits: {sorted(unknown)} (valid: {names})", file=sys.stderr)
        return 2

    def log(m):
        print(m, flush=True)

    def build_all():
        out = {}
        for name, fn in EXHIBIT_ORDER:
            if name not in want:
                continue
            log(f"[build] {name}")
            t = time.time()
            info, facts = fn(log)
            out[name] = {"info": info, "facts": facts}
            log(f"    ({time.time() - t:.1f} s)")
        return out

    t0 = time.time()
    results = build_all()
    if not args.no_captions:
        _write_exhibit_md(results, log)

    if args.verify:
        log("[verify] regenerating to check the bytes are identical")
        first = {n: results[n]["info"]["sha256"] for n in results}
        again = build_all()
        bad = [n for n in first if again[n]["info"]["sha256"] != first[n]]
        for n in sorted(first):
            same = again[n]["info"]["sha256"] == first[n]
            log(f"    {'OK  ' if same else 'DIFF'} {n}  {first[n][:16]}...")
        if bad:
            log(f"[verify] NOT deterministic: {bad}")
            return 1
        log(f"[verify] all {len(first)} outputs are byte-identical on regeneration")

    log(f"=== done in {time.time() - t0:.1f}s ===")
    total = sum(r["info"]["bytes"] for r in results.values())
    for n, r in results.items():
        i = r["info"]
        log(f"  {n:22s} {i['kind']}  {i['frames']:3d} frame(s)  "
            f"{i['shape'][1]}x{i['shape'][0]}  {i['bytes'] / 1e6:6.3f} MB")
    log(f"  total {total / 1e6:.2f} MB in {len(results)} exhibits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
