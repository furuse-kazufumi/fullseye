# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wing3d_gallery — Qiita 記事「紙面の科学館」の **3D 計測ウィング** を生成する.
Generate the "3-D metrology wing" exhibits for the Qiita science-museum article.

方針 (honest disclosure) / policy
---------------------------------
* 画像はすべて **Fullseye の登録 op を実際に実行した結果**。モックアップは 1 枚も無い。
* 図に焼き込む数値は **その場で計算した実測値**のみ(創作禁止)。キャプション
  (``docs/articles/exhibits/wing3d.md``)も本スクリプトが実測値から自動生成する。
* 描画は Fullseye の ``imagedraw`` op(線・折れ線・円・マーカー)と numpy 合成。
  **matplotlib は使わない**。文字だけは Fullseye にテキスト op が無いため PIL で焼く
  (``gen_visionlab_video.py`` と同じ流儀)。
* 版面の方針は ``tools/exhibit_tile.py`` の判断基準に従う。**同じ被写体の
  パラメータ違いを 3 枚以上並べるものは ``contact_sheet`` でタイルに束ね**、
  図中の数値が主役のもの・軸ラベル付きのグラフ・GIF は原寸で置く。静止画は
  ``save_exhibit`` / ``markdown`` を通すので、記事では必ず「サムネイル +
  クリックで原寸」になる。
* 乱数は ``SEED`` 固定 + ``np.random.default_rng`` で決定的。同じコマンドで
  再生成すると PNG / GIF は SHA-256 が一致する。
* アニメーションは **静止フレーム 1 枚だけでも意味が分かる**よう、凡例・軸・単位・
  実測値を毎フレームに焼き込む。

出力 / outputs
--------------
``docs/articles/assets/wing3d_<name>.png``            静止展示(フル解像度)
``docs/articles/assets/wing3d_<name>_thumb.jpg``      幅 900px サムネ
``docs/articles/assets/media/wing3d_<name>.gif``      動く展示(+ 同一フレーム列の .mp4)
``docs/articles/assets/thumbs/wing3d_<name>_thumb.jpg`` 動く展示のサムネ
``docs/articles/exhibits/wing3d.md``                  記事貼付け用キャプション原稿
``docs/articles/assets/_wing3d_meta.json``            使用 op・実測値・ファイル情報

使い方 / run
------------
    py -3.11 tools/gen_wing3d_gallery.py                       # 全展示
    py -3.11 tools/gen_wing3d_gallery.py --exhibits rle,obb    # 一部だけ
    py -3.11 tools/gen_wing3d_gallery.py --list                # 展示名の一覧
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from typing import Callable, Sequence

import numpy as np

# 直実行(py tools/gen_wing3d_gallery.py)でも repo ルートを import できるように。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import imagedraw                                    # Fullseye の描画 op
import ops3d                                        # Fullseye の 3-D op レジストリ
import video                                        # Fullseye の書き出し
import visualhull                                   # look_at / synthesize_silhouette

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # tools/ 自身
import exhibit_tile as et                           # 共通の版面部品(タイル/保存/md)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
ASSETS = os.path.join(_ROOT, "docs", "articles", "assets")
MEDIA = os.path.join(ASSETS, "media")
THUMBS = os.path.join(ASSETS, "thumbs")
EXHIBITS = os.path.join(_ROOT, "docs", "articles", "exhibits")
META_PATH = os.path.join(ASSETS, "_wing3d_meta.json")
CAPTION_PATH = os.path.join(EXHIBITS, "wing3d.md")
RAW_BASE = ("https://raw.githubusercontent.com/furuse-kazufumi/fullseye/"
            "master/docs/articles/assets/")

SEED = 20260902
THUMB_W = 720                       # exhibit_tile.save_exhibit の既定に合わせる
GIF_MAX_BYTES = 2_900_000            # 「3 MB 以下」を 10 進で確実に満たす上限

G = ops3d.get                                       # op を名前で引く

# --------------------------------------------------------------------------- #
# 配色 — 赤緑の対で意味を担わせない(色覚に依らず読める組合せ)                     #
# --------------------------------------------------------------------------- #
C_BG = (0.047, 0.055, 0.067)
C_PANEL = (0.092, 0.102, 0.121)
C_TEXT = (0.88, 0.89, 0.87)
C_DIM = (0.52, 0.55, 0.59)
C_RULE = (0.24, 0.26, 0.30)
C_A = (0.20, 0.78, 0.94)        # 系列 A(シアン)
C_B = (1.00, 0.68, 0.18)        # 系列 B(アンバー)
C_C = (0.66, 0.52, 0.95)        # 系列 C(パープル)
C_D = (0.40, 0.86, 0.58)        # 系列 D(ミント)
C_E = (0.96, 0.42, 0.52)        # 系列 E(ローズ)
C_AXIS_X = (0.96, 0.42, 0.52)
C_AXIS_Y = (0.40, 0.86, 0.58)
C_AXIS_Z = (0.36, 0.68, 1.00)


# --------------------------------------------------------------------------- #
# 文字と下地(Fullseye にテキスト op が無いので文字のみ PIL)                      #
# --------------------------------------------------------------------------- #
_FONT_CACHE: dict = {}


#: 日本語が要る文字列用(Consolas 系には CJK グリフが無く豆腐になる)。
_CJK_FONTS = (r"C:\Windows\Fonts\meiryo.ttc", r"C:\Windows\Fonts\YuGothM.ttc",
              r"C:\Windows\Fonts\msgothic.ttc")
_ASCII_FONTS_B = (r"C:\Windows\Fonts\consolab.ttf", r"C:\Windows\Fonts\seguisb.ttf")
_ASCII_FONTS_R = (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\segoeui.ttf")


def _font(size: int = 14, bold: bool = False, cjk: bool = False):
    """フォントを引く。ASCII だけの文字列は等幅(数値が桁で揃う)、日本語を含む
    ものは CJK グリフのあるフォント ―― 豆腐(□)で焼かないための切り替え。"""
    key = (size, bold, cjk)
    if key not in _FONT_CACHE:
        from PIL import ImageFont
        cand = _CJK_FONTS if cjk else (_ASCII_FONTS_B if bold else _ASCII_FONTS_R)
        font = None
        for p in cand:
            try:
                font = (ImageFont.truetype(p, size, index=0) if p.endswith(".ttc")
                        else ImageFont.truetype(p, size))
                break
            except OSError:
                continue
        if font is None and cjk:                       # CJK が無いなら ASCII へ退避
            font = _font(size, bold, cjk=False)
        _FONT_CACHE[key] = font or ImageFont.load_default()
    return _FONT_CACHE[key]


def _is_ascii(s: str) -> bool:
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _text(canvas: np.ndarray, items) -> np.ndarray:
    """``(x, y, s, color01, size, bold)`` の列をまとめて焼く。float [0,1] を返す。

    文字列ごとに ASCII / CJK でフォントを選ぶ(日本語を等幅英字フォントで焼くと
    全部 □ になる ―― 図が黙って壊れる典型)。
    """
    from PIL import Image, ImageDraw
    im = Image.fromarray(_to_u8(canvas))
    d = ImageDraw.Draw(im)
    for x, y, s, col, size, bold in items:
        d.text((int(x), int(y)), s,
               fill=tuple(int(round(255 * float(c))) for c in col),
               font=_font(size, bold, cjk=not _is_ascii(s)))
    return np.asarray(im, np.float64) / 255.0


def _text_w(s: str, size: int, bold: bool = False) -> int:
    """焼く前に文字幅を測る(右詰め・中央寄せの版面計算用)。"""
    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    box = d.textbbox((0, 0), s, font=_font(size, bold, cjk=not _is_ascii(s)))
    return int(box[2] - box[0])


def _to_u8(canvas: np.ndarray) -> np.ndarray:
    a = np.asarray(canvas)
    if a.dtype == np.uint8:
        return a
    return np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _canvas(w: int, h: int, color=C_BG) -> np.ndarray:
    c = np.empty((h, w, 3), np.float64)
    c[:, :, :] = np.asarray(color, np.float64)
    return c


def _fill(c: np.ndarray, x0: int, y0: int, x1: int, y1: int, color) -> None:
    c[y0:y1, x0:x1, :] = np.asarray(color, np.float64)


def _paste(c: np.ndarray, img: np.ndarray, x: int, y: int) -> None:
    h, w = img.shape[:2]
    c[y:y + h, x:x + w, :] = img


def _gray_rgb(g: np.ndarray) -> np.ndarray:
    return np.repeat(np.clip(np.asarray(g, np.float64), 0, 1)[:, :, None], 3, axis=2)


def _upscale(a: np.ndarray, k: int) -> np.ndarray:
    """最近傍の整数倍拡大 — ボクセルの粗さ自体が見せたい情報なので補間しない。"""
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


# --------------------------------------------------------------------------- #
# カラーマップ(matplotlib を使わず制御点の線形補間で作る)                        #
# --------------------------------------------------------------------------- #
_CMAPS = {
    "viridis": [(0.267, 0.005, 0.329), (0.283, 0.141, 0.458), (0.254, 0.265, 0.530),
                (0.207, 0.372, 0.553), (0.164, 0.471, 0.558), (0.128, 0.567, 0.551),
                (0.135, 0.659, 0.518), (0.478, 0.821, 0.318), (0.993, 0.906, 0.144)],
    "inferno": [(0.001, 0.000, 0.014), (0.114, 0.046, 0.246), (0.281, 0.056, 0.402),
                (0.440, 0.115, 0.390), (0.601, 0.183, 0.325), (0.752, 0.271, 0.230),
                (0.875, 0.398, 0.113), (0.962, 0.573, 0.020), (0.988, 0.998, 0.645)],
    "magma": [(0.001, 0.000, 0.014), (0.135, 0.068, 0.315), (0.372, 0.092, 0.499),
              (0.603, 0.161, 0.506), (0.833, 0.246, 0.442), (0.968, 0.446, 0.360),
              (0.995, 0.671, 0.472), (0.996, 0.849, 0.657), (0.987, 0.991, 0.750)],
    "gray": [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)],
    # 距離の等高線が読める虹(端が暗い turbo 風)
    "rainbow": [(0.190, 0.072, 0.232), (0.196, 0.322, 0.808), (0.144, 0.639, 0.876),
                (0.243, 0.855, 0.647), (0.639, 0.933, 0.318), (0.949, 0.812, 0.192),
                (0.984, 0.541, 0.153), (0.869, 0.246, 0.130), (0.480, 0.016, 0.011)],
}


def _cmap(g: np.ndarray, name: str = "viridis") -> np.ndarray:
    """``[0,1]`` のスカラー場を制御点補間で着色。戻り HxWx3 float [0,1]。"""
    stops = np.asarray(_CMAPS[name], np.float64)
    x = np.clip(np.asarray(g, np.float64), 0.0, 1.0)
    pos = x * (len(stops) - 1)
    i0 = np.clip(np.floor(pos).astype(int), 0, len(stops) - 2)
    f = (pos - i0)[..., None]
    return stops[i0] * (1.0 - f) + stops[i0 + 1] * f


def _norm01(a: np.ndarray, lo=None, hi=None) -> np.ndarray:
    a = np.asarray(a, np.float64)
    lo = float(a.min()) if lo is None else float(lo)
    hi = float(a.max()) if hi is None else float(hi)
    if hi - lo < 1e-15:
        return np.zeros_like(a)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def _colorbar(c: np.ndarray, x: int, y: int, w: int, h: int, name: str,
              lo_label: str, hi_label: str, title: str = "") -> np.ndarray:
    """横長のカラーバー + 端のラベル。数値の意味を毎フレーム読めるようにする。"""
    ramp = _cmap(np.tile(np.linspace(0, 1, w), (h, 1)), name)
    _paste(c, ramp, x, y)
    c = imagedraw.draw_polyline(
        c, [(x, y), (x + w - 1, y), (x + w - 1, y + h - 1), (x, y + h - 1)],
        color=C_RULE, width=1, closed=True)
    items = [(x, y + h + 3, lo_label, C_DIM, 12, False),
             (x + w - _text_w(hi_label, 12), y + h + 3, hi_label, C_DIM, 12, False)]
    if title:
        items.append((x, y - 17, title, C_DIM, 12, False))
    return _text(c, items)


# --------------------------------------------------------------------------- #
# 3-D 投影(点群・ワイヤフレーム)— 自前の正射影 + z ソート splat                  #
# --------------------------------------------------------------------------- #
def _rot(azim_deg: float, elev_deg: float) -> np.ndarray:
    """world (x, y, z) を視点座標へ回す行列。z が上、azim は z 軸まわり。"""
    a, e = math.radians(azim_deg), math.radians(elev_deg)
    rz = np.array([[math.cos(a), -math.sin(a), 0.0],
                   [math.sin(a), math.cos(a), 0.0],
                   [0.0, 0.0, 1.0]])
    rx = np.array([[1.0, 0.0, 0.0],
                   [0.0, math.cos(e), -math.sin(e)],
                   [0.0, math.sin(e), math.cos(e)]])
    return rx @ rz


def _project(pts_xyz: np.ndarray, R: np.ndarray, scale: float,
             cx: float, cy: float, center: np.ndarray):
    """正射影。戻り ``(u, v, depth)`` — u/v は画素、depth は大きいほど手前。"""
    q = (np.asarray(pts_xyz, np.float64) - center) @ R.T
    u = cx + scale * q[:, 0]
    v = cy - scale * q[:, 2]          # 画面 y は下向きなので z を反転(上が +z)
    return u, v, -q[:, 1]             # 視線は +y 方向 -> -y が手前


def _splat(c: np.ndarray, u, v, depth, colors, radius: int = 1,
           shade: float = 0.45) -> np.ndarray:
    """奥から手前へ順に点を置く簡易 z ソート splat。奥ほど暗くして立体感を出す。"""
    h, w = c.shape[:2]
    u = np.asarray(u); v = np.asarray(v); depth = np.asarray(depth)
    colors = np.asarray(colors, np.float64)
    if colors.ndim == 1:
        colors = np.tile(colors, (u.size, 1))
    order = np.argsort(depth)                       # 奥 -> 手前
    ui = np.rint(u[order]).astype(np.int64)
    vi = np.rint(v[order]).astype(np.int64)
    d = depth[order]
    col = colors[order]
    if d.size:
        dn = _norm01(d)
        col = col * ((1.0 - shade) + shade * dn)[:, None]
    ok = (ui >= radius) & (ui < w - radius) & (vi >= radius) & (vi < h - radius)
    ui, vi, col = ui[ok], vi[ok], col[ok]
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            c[vi + dy, ui + dx, :] = col
    return c


def _draw_wire(c: np.ndarray, corners_xyz, edges, R, scale, cx, cy, center,
               color, width: int = 1) -> np.ndarray:
    u, v, _ = _project(np.asarray(corners_xyz, np.float64), R, scale, cx, cy, center)
    for i, j in edges:
        c = imagedraw.draw_line(c, (u[i], v[i]), (u[j], v[j]), color=color, width=width)
    return c


_BOX_EDGES = [(0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4),
              (0, 4), (1, 5), (2, 6), (3, 7)]


def _box_corners(center_xyz, half_xyz, axes=None) -> np.ndarray:
    """``axes`` は列が箱の軸(None なら軸平行)。戻り (8,3)。"""
    signs = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)],
                     np.float64)
    local = signs * np.asarray(half_xyz, np.float64)
    if axes is not None:
        local = local @ np.asarray(axes, np.float64).T
    return local + np.asarray(center_xyz, np.float64)


def _axis_gizmo(c: np.ndarray, R, x: int, y: int, size: int = 34,
                labels=("+x", "+y", "+z")) -> np.ndarray:
    """右手系の座標軸を毎フレーム描く — 軸の入れ替わり/反転を目で検出できるように。"""
    eye = np.eye(3)
    u, v, _ = _project(eye, R, size, x, y, np.zeros(3))
    items = []
    for k, (col, lab) in enumerate(zip((C_AXIS_X, C_AXIS_Y, C_AXIS_Z), labels)):
        c = imagedraw.draw_line(c, (x, y), (u[k], v[k]), color=col, width=2)
        items.append((u[k] + 3, v[k] - 7, lab, col, 11, True))
    return _text(c, items)


# --------------------------------------------------------------------------- #
# 折れ線グラフ(すべて imagedraw op + PIL 文字。matplotlib 不使用)                #
# --------------------------------------------------------------------------- #
class Plot:
    """左下原点の直交座標。``imagedraw`` の線分だけで軸・目盛り・系列を描く。"""

    def __init__(self, c, x0, y0, w, h, xlim, ylim, *, xlabel="", ylabel="",
                 xticks=None, yticks=None, xfmt="%g", yfmt="%g", logy=False):
        self.c, self.x0, self.y0, self.w, self.h = c, x0, y0, w, h
        self.xlim, self.ylim, self.logy = xlim, ylim, logy
        self.items = []
        _fill(c, x0, y0, x0 + w, y0 + h, C_PANEL)
        c = imagedraw.draw_polyline(
            c, [(x0, y0), (x0 + w - 1, y0), (x0 + w - 1, y0 + h - 1), (x0, y0 + h - 1)],
            color=C_RULE, width=1, closed=True)
        self.c = c
        # 範囲外の目盛りは描かない — 描くと枠の外に数字と線が漏れる(黙って壊れる)
        xticks = [t for t in (xticks or [])
                  if min(xlim) - 1e-12 <= t <= max(xlim) + 1e-12]
        yticks = [t for t in (yticks or [])
                  if min(ylim) - 1e-12 <= t <= max(ylim) + 1e-12]
        for t in xticks:
            px = self.px(t)
            self.c = imagedraw.draw_line(self.c, (px, y0 + h - 1), (px, y0 + h - 6),
                                         color=C_RULE, width=1)
            s = xfmt % t
            self.items.append((px - _text_w(s, 11) / 2, y0 + h + 2, s, C_DIM, 11, False))
        for t in yticks:
            py = self.py(t)
            self.c = imagedraw.draw_line(self.c, (x0 + 1, py), (x0 + w - 2, py),
                                         color=(0.16, 0.18, 0.21), width=1)
            s = yfmt % t
            self.items.append((x0 - _text_w(s, 11) - 5, py - 7, s, C_DIM, 11, False))
        if xlabel:
            self.items.append((x0 + w - _text_w(xlabel, 11) - 4, y0 + h + 15,
                               xlabel, C_DIM, 11, False))
        if ylabel:
            self.items.append((x0, y0 - 16, ylabel, C_DIM, 11, False))

    def px(self, x):
        lo, hi = self.xlim
        return self.x0 + (self.w - 1) * (float(x) - lo) / (hi - lo)

    def py(self, y):
        lo, hi = self.ylim
        if self.logy:
            y = math.log10(max(float(y), 1e-30))
            lo, hi = math.log10(max(lo, 1e-30)), math.log10(max(hi, 1e-30))
        return self.y0 + (self.h - 1) - (self.h - 1) * (float(y) - lo) / (hi - lo)

    def series(self, xs, ys, color, width=2, markers=False):
        pts = [(self.px(x), self.py(y)) for x, y in zip(xs, ys)]
        if len(pts) >= 2:
            self.c = imagedraw.draw_polyline(self.c, pts, color=color, width=width)
        if markers and pts:
            self.c = imagedraw.draw_markers(self.c, pts, color=color, size=3,
                                            shape="dot", width=1)
        return self

    def hline(self, y, color, width=1, dash=6, gap=5):
        py = self.py(y)
        x = self.x0
        while x < self.x0 + self.w:
            x2 = min(x + dash, self.x0 + self.w - 1)
            self.c = imagedraw.draw_line(self.c, (x, py), (x2, py), color=color,
                                         width=width)
            x = x2 + gap
        return self

    def marker(self, x, y, color, size=5):
        self.c = imagedraw.draw_markers(self.c, [(self.px(x), self.py(y))],
                                        color=color, size=size, shape="cross", width=2)
        return self

    def label(self, x, y, s, color, size=11, bold=False):
        self.items.append((self.px(x), self.py(y), s, color, size, bold))
        return self

    def done(self):
        return _text(self.c, self.items)


def _bars(c, x0, y0, w, h, values, labels, colors, *, vmax=None, fmt="%.0f",
          title=""):
    """横棒グラフ。棒は塗り、値は文字で焼く(比が一目で分かるよう最大値で正規化)。"""
    _fill(c, x0, y0, x0 + w, y0 + h, C_PANEL)
    vmax = float(max(values)) if vmax is None else float(vmax)
    n = len(values)
    bh = max(10, int((h - 12) / n) - 8)
    items = []
    lab_w = max(_text_w(s, 12, True) for s in labels) + 8
    for i, (v, lab, col) in enumerate(zip(values, labels, colors)):
        yy = y0 + 8 + i * (bh + 8)
        bw = int(max(1.0, (w - lab_w - 96) * float(v) / max(vmax, 1e-30)))
        _fill(c, x0 + lab_w, yy, x0 + lab_w + bw, yy + bh, col)
        items.append((x0 + 6, yy + bh // 2 - 8, lab, C_TEXT, 12, True))
        items.append((x0 + lab_w + bw + 6, yy + bh // 2 - 8, fmt % v, col, 12, True))
    if title:
        items.append((x0, y0 - 17, title, C_DIM, 12, False))
    return _text(c, items)


def _header(c, title: str, subtitle: str = "", x: int = 18, y: int = 12):
    items = [(x, y, title, C_TEXT, 19, True)]
    if subtitle:
        items.append((x, y + 25, subtitle, C_DIM, 13, False))
    return _text(c, items)


def _footer(c, s: str, y_off: int = 22):
    h = c.shape[0]
    return _text(c, [(18, h - y_off, s, C_DIM, 12, False)])


# --------------------------------------------------------------------------- #
# 書き出しと検証(必ず読み戻して実測する)                                          #
# --------------------------------------------------------------------------- #
def _sha256(path: str) -> str:
    hh = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            hh.update(chunk)
    return hh.hexdigest()


def _save_png(canvas: np.ndarray, name: str, log) -> dict:
    """共通部品 ``exhibit_tile.save_exhibit`` で PNG + サムネを書く。

    記事は必ず「サムネイル + クリックで原寸」の形にする(縦に伸びるのを抑える)。
    書き出したあとに読み戻して寸法・バイト数・SHA-256 を実測する。
    """
    from PIL import Image
    res = et.save_exhibit(np.clip(np.asarray(canvas, np.float64), 0.0, 1.0), name)
    with Image.open(res["png"]) as im:                       # 読み戻して実測
        size = im.size
    info = {"kind": "png", "png": res["png"], "png_bytes": res["png_bytes"],
            "png_size": size, "png_sha256": res["png_sha256"],
            "thumb": res["thumb"], "thumb_bytes": res["thumb_bytes"]}
    log(f"    png  {os.path.basename(res['png'])}  {size[0]}x{size[1]}  "
        f"{info['png_bytes'] / 1e3:.0f} kB  thumb {info['thumb_bytes'] / 1e3:.0f} kB"
        f"  sha {info['png_sha256'][:12]}")
    return info


def _save_clip(frames: Sequence[np.ndarray], name: str, *, fps: int,
               thumb_index: int, log) -> dict:
    """**同一のフレーム列**から GIF と mp4 を書く(撮り直さない)。

    GIF は適応パレットで書き、``GIF_MAX_BYTES`` を超えるうちは色数を段階的に
    落とす(それでも超えるなら honest に報告する)。書き出し後は必ず読み戻して
    フレーム数・寸法・バイト数を実測する。
    """
    from PIL import Image
    os.makedirs(MEDIA, exist_ok=True)
    os.makedirs(THUMBS, exist_ok=True)
    u8 = [_to_u8(f) for f in frames]
    # 連続する同一フレームがあると Pillow の optimize が黙って 1 枚に畳み、
    # 読み戻したフレーム数が合わなくなる(= コマが飛んだアニメになる)。
    # ここで先に見つけて落とす — 「送っているのに止まっている」画は作らない。
    dup = [i for i in range(1, len(u8)) if np.array_equal(u8[i], u8[i - 1])]
    if dup:
        raise RuntimeError(
            "%s: frame(s) %s are identical to the previous frame; the GIF writer "
            "would collapse them and the animation would stall. Make every step "
            "advance (check the easing / rounding of the sweep parameter)."
            % (name, dup[:8]))
    gif = os.path.join(MEDIA, f"{name}.gif")
    mp4 = os.path.join(MEDIA, f"{name}.mp4")

    colors_used = None
    for colors in (256, 192, 128, 96, 64, 48):
        pil = [Image.fromarray(f, "RGB").convert(
            "P", palette=Image.ADAPTIVE, colors=colors) for f in u8]
        pil[0].save(gif, save_all=True, append_images=pil[1:],
                    duration=int(round(1000.0 / fps)), loop=0, optimize=True)
        colors_used = colors
        if os.path.getsize(gif) <= GIF_MAX_BYTES:
            break
    video.write_video(mp4, u8, fps=fps)

    import imageio.v2 as iio
    def _count(path):
        rd = iio.get_reader(path)
        n, shape = 0, None
        try:
            for fr in rd:
                if shape is None:
                    shape = tuple(np.asarray(fr).shape)
                n += 1
        finally:
            rd.close()
        return n, shape

    n_gif, shape_gif = _count(gif)
    n_mp4, shape_mp4 = _count(mp4)
    if n_gif != len(u8):
        raise RuntimeError(f"{gif}: read back {n_gif} frames, expected {len(u8)}")
    if n_mp4 != len(u8):
        raise RuntimeError(f"{mp4}: read back {n_mp4} frames, expected {len(u8)}")

    idx = int(np.clip(thumb_index, 0, len(u8) - 1))
    thumb = os.path.join(THUMBS, f"{name}_thumb.jpg")
    im = Image.fromarray(u8[idx])
    if im.width > THUMB_W:
        im = im.resize((THUMB_W, max(2, round(im.height * THUMB_W / im.width))),
                       Image.LANCZOS)
    im.save(thumb, format="JPEG", quality=88, optimize=True)

    info = {"kind": "gif", "gif": gif, "mp4": mp4, "thumb": thumb,
            "frames": n_gif, "fps": fps, "gif_shape": shape_gif,
            "mp4_shape": shape_mp4, "gif_colors": colors_used,
            "gif_bytes": os.path.getsize(gif), "mp4_bytes": os.path.getsize(mp4),
            "thumb_bytes": os.path.getsize(thumb), "thumb_frame": idx,
            "gif_sha256": _sha256(gif), "mp4_sha256": _sha256(mp4)}
    warn = "  [OVER 3MB]" if info["gif_bytes"] > GIF_MAX_BYTES else ""
    log(f"    gif  {os.path.basename(gif)}  {n_gif} frames  {shape_gif[1]}x{shape_gif[0]}"
        f"  {info['gif_bytes'] / 1e6:.2f} MB ({colors_used} colors){warn}")
    log(f"    mp4  {os.path.basename(mp4)}  {n_mp4} frames  "
        f"{info['mp4_bytes'] / 1e6:.2f} MB")
    return info


# --------------------------------------------------------------------------- #
# 共通のファントム(合成データ — 実データは使わない)                              #
# --------------------------------------------------------------------------- #
def _grid(shape):
    d, h, w = shape
    return np.mgrid[0:d, 0:h, 0:w].astype(np.float64)


def _aa_ball(shape, c, r):
    """反エイリアスした球。50 % 等値面が厳密に半径 r に来るので測長の真値が作れる。"""
    zz, yy, xx = _grid(shape)
    rr = np.sqrt((zz - c[0]) ** 2 + (yy - c[1]) ** 2 + (xx - c[2]) ** 2)
    return np.clip(r - rr + 0.5, 0.0, 1.0)


def _capsule(shape, p0, p1, rad):
    """線分 p0-p1 を軸とする太さ ``rad`` のカプセル(二値)。"""
    zz, yy, xx = _grid(shape)
    p0 = np.asarray(p0, np.float64); p1 = np.asarray(p1, np.float64)
    d = p1 - p0
    L2 = float(d @ d)
    P = np.stack([zz, yy, xx], -1) - p0
    t = np.clip((P @ d) / L2, 0.0, 1.0)[..., None]
    return (((P - t * d) ** 2).sum(-1) <= rad * rad)


def _ct_phantom(n=128):
    """胸部 CT 風の HU ボリューム(合成)。空気 -1000 / 肺 -820 / 軟部 40 /
    肋骨 900 / 椎体 1100 — CT 窓の効きを見るための既知の真値。"""
    zz, yy, xx = _grid((n, n, n))
    hu = np.full((n, n, n), -1000.0)
    cy = cx = n / 2.0
    body = ((yy - cy) ** 2 + ((xx - cx) / 1.12) ** 2) <= (0.41 * n) ** 2
    hu[body] = 40.0
    lung_l = (((yy - cy + 0.05 * n) / 1.0) ** 2 + ((xx - cx + 0.19 * n) / 1.25) ** 2) <= (0.19 * n) ** 2
    lung_r = (((yy - cy + 0.05 * n) / 1.0) ** 2 + ((xx - cx - 0.19 * n) / 1.25) ** 2) <= (0.19 * n) ** 2
    hu[(lung_l | lung_r) & body] = -820.0
    rr = np.sqrt((yy - cy) ** 2 + ((xx - cx) / 1.12) ** 2)
    rib = (rr > 0.345 * n) & (rr < 0.385 * n) & (((zz + 3) % (n // 8)) < max(2, n // 26))
    hu[rib & body] = 900.0
    spine = ((yy - cy - 0.28 * n) ** 2 + (xx - cx) ** 2) <= (0.085 * n) ** 2
    hu[spine & body] = 1100.0
    vessel = _capsule((n, n, n), (0.1 * n, cy - 0.02 * n, cx - 0.19 * n),
                      (0.9 * n, cy - 0.10 * n, cx - 0.19 * n), 0.022 * n)
    hu[vessel] = 120.0
    return hu


# --------------------------------------------------------------------------- #
# 展示 01 — 処理領域(domain)でメモリが縮む                                        #
# --------------------------------------------------------------------------- #
def ex_domain(log) -> dict:
    n = 192
    zz, yy, xx = _grid((n, n, n))
    # 大きな空の視野の隅に置かれた小さな部品(実際の CT でよくある構図)
    obj = ((((zz - 62.) / 19.) ** 2 + ((yy - 72.) / 24.) ** 2
            + ((xx - 84.) / 17.) ** 2) <= 1.0)
    bore = _capsule((n, n, n), (44, 72, 84), (80, 72, 84), 5.0)
    obj = obj & ~bore
    vol = np.where(obj, 0.85, 0.0)
    vol += 0.10 * np.where(obj, np.sin(xx * 0.6) * np.sin(yy * 0.6), 0.0)

    dom = obj.astype(np.float64)
    part, off = G("vol_crop_domain")(vol, dom, margin=2)
    back = G("vol_uncrop")(part, off, vol.shape)
    exact = bool(np.array_equal(np.asarray(back), vol))
    red = np.asarray(G("vol_reduce_domain")(vol, dom))
    bbox = G("vol_bounding_box")(dom, margin=2)

    full_mb = vol.nbytes / 1e6
    part_mb = np.asarray(part).nbytes / 1e6
    ratio = vol.nbytes / np.asarray(part).nbytes
    log(f"    full {vol.shape} {full_mb:.2f} MB -> part {np.asarray(part).shape} "
        f"{part_mb:.3f} MB  = 1/{ratio:.1f}  uncrop exact={exact}")

    # 時間の実測(同じ op を full / cropped の両方に掛ける)
    def _timeit(fn, rep=3):
        best = math.inf
        for _ in range(rep):
            t = time.perf_counter(); fn(); best = min(best, time.perf_counter() - t)
        return best
    t_full = _timeit(lambda: G("vol_gradient_magnitude")(vol))
    t_part = _timeit(lambda: G("vol_gradient_magnitude")(np.asarray(part)))
    log(f"    vol_gradient_magnitude  full {t_full * 1e3:.1f} ms -> "
        f"cropped {t_part * 1e3:.1f} ms  = {t_full / t_part:.1f}x")

    W, H = 1120, 690
    pw = 236
    z0, y0, x0, z1, y1, x1 = bbox
    frames = []
    nf = 40
    for k in range(nf):
        z = int(round(z0 + (z1 - 1 - z0) * k / (nf - 1)))
        c = _canvas(W, H)
        c = _header(c, "処理領域(domain)— 見る範囲を切ると記憶と時間が縮む",
                    f"192^3 の視野に置いた合成部品を 1 枚ずつ輪切りにして見る "
                    f"(z = {z:3d} / {n - 1})")
        panels = []
        # 1) 全視野スライス + domain の枠
        s_full = _cmap(_norm01(vol[z], 0, 1.0), "gray")
        s_full = np.asarray(s_full)
        panels.append(("元ボリューム 192^3", s_full, "full frame"))
        # 2) マスク(domain)
        m = np.zeros((n, n, 3))
        m[..., 0] = dom[z] * C_B[0]; m[..., 1] = dom[z] * C_B[1]; m[..., 2] = dom[z] * C_B[2]
        panels.append(("domain マスク", m, "the domain"))
        # 3) 切り出し後(部分ボリューム)
        pc = np.zeros((n, n, 3))
        sub = np.asarray(part)[z - z0] if z0 <= z < z0 + np.asarray(part).shape[0] else None
        if sub is not None:
            pc[y0:y0 + sub.shape[0], x0:x0 + sub.shape[1], :] = _cmap(
                _norm01(sub, 0, 1.0), "gray")
        panels.append(("vol_crop_domain 後", pc, "cropped"))
        # 4) 貼り戻し
        panels.append(("vol_uncrop で貼り戻し", np.asarray(_cmap(_norm01(np.asarray(back)[z], 0, 1.0), "gray")), "restored"))

        px = 18
        items = []
        for title, img, sub_en in panels:
            small = img[::1, ::1]
            sc = pw / n
            from PIL import Image
            im = Image.fromarray(_to_u8(small)).resize((pw, pw), Image.NEAREST)
            arr = np.asarray(im, np.float64) / 255.0
            _paste(c, arr, px, 78)
            c = imagedraw.draw_polyline(
                c, [(px, 78), (px + pw - 1, 78), (px + pw - 1, 78 + pw - 1), (px, 78 + pw - 1)],
                color=C_RULE, width=1, closed=True)
            if title.startswith("元") or title.startswith("vol_uncrop"):
                c = imagedraw.draw_polyline(
                    c, [(px + x0 * sc, 78 + y0 * sc), (px + x1 * sc, 78 + y0 * sc),
                        (px + x1 * sc, 78 + y1 * sc), (px + x0 * sc, 78 + y1 * sc)],
                    color=C_B, width=1, closed=True)
            items.append((px, 78 + pw + 6, title, C_TEXT, 13, True))
            px += pw + 12

        c = _text(c, items)
        c = _bars(c, 18, 400, 520, 118,
                  [full_mb, part_mb],
                  ["元 192^3", f"切出 {np.asarray(part).shape[0]}x{np.asarray(part).shape[1]}x{np.asarray(part).shape[2]}"],
                  [C_A, C_B], fmt="%.3f MB",
                  title="float64 ボリュームのメモリ(実測 nbytes)")
        c = _bars(c, 580, 400, 522, 118, [t_full * 1e3, t_part * 1e3],
                  ["元 192^3", "切出後"], [C_A, C_B], fmt="%.1f ms",
                  title="vol_gradient_magnitude の実行時間(3 回の最小値)")
        c = _text(c, [
            (18, 540, f"メモリ比 1/{ratio:.1f}  ({full_mb:.2f} MB -> {part_mb:.3f} MB)",
             C_D, 16, True),
            (18, 564, f"実行時間比 {t_full / t_part:.1f}x 速い  "
                      f"({t_full * 1e3:.1f} ms -> {t_part * 1e3:.1f} ms)", C_D, 16, True),
            (18, 590, f"vol_uncrop で元の座標へ貼り戻した結果は元と bit 一致: "
                      f"{'YES' if exact else 'NO'}", C_TEXT, 14, True),
            (18, 614, f"bounding box (z,y,x) = ({z0},{y0},{x0}) .. ({z1},{y1},{x1})  "
                      f"margin=2  前景 {int(dom.sum()):,} voxel "
                      f"= 全体の {100 * dom.mean():.2f} %", C_DIM, 13, False),
        ])
        c = _footer(c, "使用 op: vol_bounding_box / vol_crop_domain / vol_reduce_domain / "
                       "vol_uncrop / vol_gradient_magnitude  — 合成データ, seed 固定")
        frames.append(c)

    info = _save_clip(frames, "wing3d_domain_memory", fps=12,
                      thumb_index=nf // 2, log=log)
    return {
        "name": "wing3d_domain_memory", "title": "処理領域(domain)でメモリが 1/%.0f になる" % ratio,
        "ops": ["vol_bounding_box", "vol_crop_domain", "vol_reduce_domain", "vol_uncrop",
                "vol_gradient_magnitude"],
        "facts": {"full_shape": list(vol.shape), "part_shape": list(np.asarray(part).shape),
                  "full_MB": full_mb, "part_MB": part_mb, "memory_ratio": ratio,
                  "t_full_ms": t_full * 1e3, "t_part_ms": t_part * 1e3,
                  "speedup": t_full / t_part, "uncrop_exact": exact,
                  "foreground_voxels": int(dom.sum()),
                  "foreground_pct": 100 * float(dom.mean())},
        "caption": ("192³ の視野に浮かぶ合成部品を輪切りで送りながら、元ボリューム・"
                    "domain マスク・切り出し後・貼り戻しを並べた。前景は全体の "
                    f"{100 * float(dom.mean()):.2f} % しかないので `vol_crop_domain` で "
                    f"メモリは {full_mb:.2f} MB → {part_mb:.3f} MB(**1/{ratio:.1f}**)、"
                    f"同じ `vol_gradient_magnitude` が {t_full * 1e3:.1f} ms → "
                    f"{t_part * 1e3:.1f} ms(**{t_full / t_part:.1f} 倍速**)になる。"
                    "`vol_uncrop` の貼り戻しは元と bit 一致。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 02 — 境界だけ持つ / 球フィット                                            #
# --------------------------------------------------------------------------- #
def ex_boundary(log) -> dict:
    n = 128
    sp = (0.4, 0.4, 0.4)                       # mm / voxel
    r_vox = 40.0
    ball = (_aa_ball((n, n, n), (64., 64., 64.), r_vox) > 0.5).astype(np.float64)
    shell = np.asarray(G("vol_boundary")(ball, connectivity=6, side="inner"))
    pts_mm = np.asarray(G("vol_boundary_points")(ball, spacing=sp, connectivity=6))
    fit = G("fit_sphere3")(pts_mm)

    solid_n = int(ball.sum()); shell_n = int(shell.sum())
    pct = 100.0 * shell_n / solid_n
    solid_mb = ball.astype(bool).nbytes / 1e6
    pts_mb = pts_mm.nbytes / 1e6
    truth_center_mm = np.array([64.0 * sp[0], 64.0 * sp[1], 64.0 * sp[2]])
    truth_r_mm = r_vox * sp[0]
    cen = np.asarray([fit["cd"], fit["cr"], fit["cc"]], np.float64)
    cen_err = float(np.linalg.norm(cen - truth_center_mm))
    r_err = float(fit["r"] - truth_r_mm)
    log(f"    solid {solid_n} shell {shell_n} = {pct:.1f}%  points {pts_mm.shape}")
    log(f"    fit center {np.round(cen, 4)} truth {truth_center_mm}  err {cen_err:.4f} mm")
    log(f"    fit r {fit['r']:.4f} truth {truth_r_mm:.4f}  err {r_err:+.4f} mm  "
        f"rms {fit['rms']:.4f} mm")

    # 表示用に間引いた点(描画のためだけ。測定は全点で行っている)
    rng = np.random.default_rng(SEED)
    idx = rng.choice(pts_mm.shape[0], size=min(6000, pts_mm.shape[0]), replace=False)
    idx = np.sort(idx)
    show = pts_mm[idx]
    solid_idx = np.argwhere(ball > 0.5).astype(np.float64) * np.asarray(sp)
    sidx = rng.choice(solid_idx.shape[0], size=6000, replace=False)
    solid_show = solid_idx[np.sort(sidx)]

    W, H = 1120, 640
    pw, ph = 350, 380
    nf = 36                       # 点群 3 面 x 高フレーム数は GIF が太る。36 で 1 周。
    frames = []
    cen_world = truth_center_mm[[2, 1, 0]]                  # (x, y, z)
    for k in range(nf):
        az = 360.0 * k / nf
        R = _rot(az, 22.0)
        c = _canvas(W, H)
        c = _header(c, "境界だけ持つ — 中実の球を「殻」と「mm 点群」に痩せさせる",
                    "同じ球を 3 通りの持ち方で(左から 中実ボクセル / 内側 1 層の殻 / "
                    "mm 単位の境界点群)。ターンテーブルで 1 周。")
        scale = 6.4
        for i, (pts, col, title) in enumerate((
                (solid_show, C_A, "中実ボクセル(表示は 9000 点に間引き)"),
                (np.argwhere(shell > 0.5).astype(np.float64) * np.asarray(sp), C_B,
                 "vol_boundary(side='inner', 6 近傍)"),
                (show, C_D, "vol_boundary_points(spacing 付き, mm)"))):
            px = 18 + i * (pw + 20)
            _fill(c, px, 76, px + pw, 76 + ph, C_PANEL)
            world = pts[:, [2, 1, 0]]                       # (z,y,x) -> (x,y,z)
            u, v, d = _project(world, R, scale, px + pw / 2, 76 + ph / 2, cen_world)
            sub = c[76:76 + ph, px:px + pw]
            _splat(sub, u - px, v - 76, d, col, radius=1, shade=0.55)
            c = imagedraw.draw_polyline(
                c, [(px, 76), (px + pw - 1, 76), (px + pw - 1, 76 + ph - 1), (px, 76 + ph - 1)],
                color=C_RULE, width=1, closed=True)
            c = _axis_gizmo(c, R, px + 44, 76 + ph - 44, size=26)
            c = _text(c, [(px, 76 + ph + 6, title, C_TEXT, 12, True)])

        c = _bars(c, 18, 500, 520, 86,
                  [float(solid_n), float(shell_n)],
                  ["中実 voxel", "殻 voxel"], [C_A, C_B], fmt="%.0f",
                  title="ボクセル数(実測)")
        c = _text(c, [
            (18, 600, f"殻は中実の {pct:.1f} %({shell_n:,} / {solid_n:,} voxel)",
             C_B, 15, True),
            (580, 505, "fit_sphere3(境界点群 %d 点, mm)" % pts_mm.shape[0], C_DIM, 12, False),
            (580, 524, f"中心 (d,r,c) = ({cen[0]:.3f}, {cen[1]:.3f}, {cen[2]:.3f}) mm",
             C_TEXT, 13, False),
            (580, 544, f"真値 ({truth_center_mm[0]:.3f}, {truth_center_mm[1]:.3f}, "
                       f"{truth_center_mm[2]:.3f}) mm -> 中心誤差 {cen_err:.3f} mm",
             C_D, 13, True),
            (580, 566, f"半径 {fit['r']:.3f} mm(真値 {truth_r_mm:.3f} mm, "
                       f"差 {r_err:+.3f} mm)  残差 rms {fit['rms']:.3f} mm",
             C_TEXT, 13, False),
            (580, 588, "半径だけ内側にずれるのは、殻が「内側 1 層」の voxel 中心だから "
                       "— 消さずに書いておく。", C_DIM, 12, False),
        ])
        c = _footer(c, "使用 op: vol_boundary / vol_boundary_points / fit_sphere3  "
                       "— 合成データ(反エイリアス球), spacing 0.4 mm/voxel")
        frames.append(c)

    info = _save_clip(frames, "wing3d_boundary_shell", fps=14, thumb_index=6, log=log)
    return {
        "name": "wing3d_boundary_shell",
        "title": "境界だけ持つと %.0f %% に痩せる" % pct,
        "ops": ["vol_boundary", "vol_boundary_points", "fit_sphere3"],
        "facts": {"solid_voxels": solid_n, "shell_voxels": shell_n, "shell_pct": pct,
                  "boundary_points": int(pts_mm.shape[0]),
                  "center_mm": cen.tolist(), "center_truth_mm": truth_center_mm.tolist(),
                  "center_err_mm": cen_err, "radius_mm": float(fit["r"]),
                  "radius_truth_mm": truth_r_mm, "radius_err_mm": r_err,
                  "fit_rms_mm": float(fit["rms"]),
                  "solid_bool_MB": solid_mb, "points_MB": pts_mb},
        "caption": (f"中実の球({solid_n:,} voxel)を `vol_boundary` で内側 1 層の殻に"
                    f"すると **{pct:.1f} %**({shell_n:,} voxel)まで痩せる。"
                    f"その殻を `vol_boundary_points` で mm 座標の点群にして "
                    f"`fit_sphere3` に渡すと、**中心誤差 {cen_err:.3f} mm**(真値 "
                    f"({truth_center_mm[0]:.1f}, {truth_center_mm[1]:.1f}, "
                    f"{truth_center_mm[2]:.1f}) mm)。半径だけは {r_err:+.3f} mm ずれる "
                    "— 殻が「内側 1 層」だからで、これは消さずに図に書いてある。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 03 — run-length で持つ                                                   #
# --------------------------------------------------------------------------- #
def ex_rle(log) -> dict:
    n = 256
    zz, yy, xx = _grid((n, n, n))
    ball = ((zz - 128.) ** 2 + (yy - 128.) ** 2 + (xx - 128.) ** 2) <= 70.0 ** 2
    axle = ((yy - 128.) ** 2 + (xx - 128.) ** 2) <= 14.0 ** 2
    flange = (np.abs(zz - 40.) <= 6) & (((yy - 128.) ** 2 + (xx - 128.) ** 2) <= 52.0 ** 2)
    part = (ball | axle | flange).astype(np.float64)

    rle = G("vol_rle_encode")(part)
    dense_bytes = (part > 0.5).astype(bool).nbytes
    ratio = dense_bytes / rle.nbytes
    dec = np.asarray(G("vol_rle_decode")(rle))
    exact = bool(np.array_equal(dec, part))

    b = part > 0.5

    def _bench(fn, rep=25):
        best = math.inf
        for _ in range(rep):
            t = time.perf_counter(); fn(); best = min(best, time.perf_counter() - t)
        return best

    t_rle_vol = _bench(lambda: G("vol_rle_volume")(rle))
    t_den_vol = _bench(lambda: int(b.sum()))
    t_rle_bb = _bench(lambda: G("vol_rle_bbox")(rle))

    def dense_bbox():
        zs = np.nonzero(b.any(axis=(1, 2)))[0]
        ys = np.nonzero(b.any(axis=(0, 2)))[0]
        xs = np.nonzero(b.any(axis=(0, 1)))[0]
        return zs[0], ys[0], xs[0], zs[-1], ys[-1], xs[-1]
    t_den_bb = _bench(dense_bbox)

    r_ball = G("vol_rle_encode")(ball.astype(np.float64))
    r_axle = G("vol_rle_encode")(axle.astype(np.float64))
    t_un = _bench(lambda: G("vol_rle_union")(r_ball, r_axle), rep=8)
    t_in = _bench(lambda: G("vol_rle_intersect")(r_ball, r_axle), rep=8)
    t_di = _bench(lambda: G("vol_rle_difference")(r_ball, r_axle), rep=8)
    v_un = G("vol_rle_volume")(G("vol_rle_union")(r_ball, r_axle))
    v_in = G("vol_rle_volume")(G("vol_rle_intersect")(r_ball, r_axle))
    v_di = G("vol_rle_volume")(G("vol_rle_difference")(r_ball, r_axle))
    bbox = G("vol_rle_bbox")(rle)
    cent = G("vol_rle_centroid")(rle)
    vox = G("vol_rle_volume")(rle)
    log(f"    dense {dense_bytes / 1e6:.2f} MB -> rle {rle.nbytes / 1e6:.3f} MB "
        f"= 1/{ratio:.1f}  runs {len(rle):,}  roundtrip exact={exact}")
    log(f"    volume rle {t_rle_vol * 1e6:.1f} us vs dense {t_den_vol * 1e6:.1f} us "
        f"= {t_den_vol / t_rle_vol:.0f}x ;  bbox {t_den_bb / t_rle_bb:.0f}x")

    W, H = 1120, 720
    c = _canvas(W, H)
    c = _header(c, "run-length で持つ — ビットマップを作らずに測る",
                "256³ の合成部品(球 + 軸 + フランジ)。RLE は「x 方向に連続する区間」"
                "の並びなので、体積・BBox・集合演算は展開せずに答えられる。")

    # 上段左: スライス 1 枚の run を線分で描く(RLE の中身そのもの)
    z = 128
    sl = b[z]
    pw = 360
    sc = pw / n
    px, py = 18, 82
    _fill(c, px, py, px + pw, py + pw, C_PANEL)
    step = 3
    for y in range(0, n, step):
        row = sl[y]
        if not row.any():
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts = np.nonzero(d == 1)[0]
        ends = np.nonzero(d == -1)[0]
        for s, e in zip(starts, ends):
            c = imagedraw.draw_line(c, (px + s * sc, py + y * sc),
                                    (px + (e - 1) * sc, py + y * sc),
                                    color=C_A, width=1)
    c = imagedraw.draw_polyline(
        c, [(px, py), (px + pw - 1, py), (px + pw - 1, py + pw - 1), (px, py + pw - 1)],
        color=C_RULE, width=1, closed=True)
    n_runs_slice = 0
    for y in range(n):
        row = sl[y]
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        n_runs_slice += int((d == 1).sum())
    c = _text(c, [(px, py + pw + 6, f"z = {z} スライスの run(3 行おきに描画)"
                                    f" — この面だけで {n_runs_slice:,} run",
                   C_TEXT, 12, True)])

    c = _bars(c, 430, 100, 672, 96, [dense_bytes / 1e6, rle.nbytes / 1e6],
              ["dense bool", "VolRLE"], [C_A, C_B], fmt="%.3f MB",
              title="同じ領域を保持するメモリ(実測 nbytes)")
    c = _bars(c, 430, 240, 672, 96,
              [t_den_vol * 1e6, t_rle_vol * 1e6],
              ["dense.sum()", "vol_rle_volume"], [C_A, C_B], fmt="%.1f us",
              title="体積(voxel 数)を求める時間(25 回の最小値)")
    c = _bars(c, 430, 380, 672, 96,
              [t_den_bb * 1e6, t_rle_bb * 1e6],
              ["dense 走査", "vol_rle_bbox"], [C_A, C_B], fmt="%.1f us",
              title="bounding box を求める時間(25 回の最小値)")

    rows = [
        f"メモリ比            1/{ratio:.1f}  ({dense_bytes / 1e6:.2f} MB -> {rle.nbytes / 1e6:.3f} MB, run 数 {len(rle):,})",
        f"decode 往復          元と bit 一致: {'YES' if exact else 'NO'}",
        f"体積                 {vox:,} voxel   ({t_den_vol / t_rle_vol:.0f} 倍速)",
        f"bounding box         (z,y,x) {bbox[:3]} .. {bbox[3:]}   ({t_den_bb / t_rle_bb:.0f} 倍速)",
        f"重心                 ({cent[0]:.2f}, {cent[1]:.2f}, {cent[2]:.2f}) voxel",
        f"union(球, 軸)        {v_un:,} voxel  {t_un * 1e3:.2f} ms",
        f"intersect(球, 軸)    {v_in:,} voxel  {t_in * 1e3:.2f} ms",
        f"difference(球 - 軸)  {v_di:,} voxel  {t_di * 1e3:.2f} ms",
    ]
    items = [(430, 500, "展開せずに答えた測定(すべて run の上で計算)", C_DIM, 12, False)]
    for i, s in enumerate(rows):
        items.append((430, 522 + i * 21, s, C_TEXT, 13, False))
    c = _text(c, items)
    c = _text(c, [(18, 500, f"1/{ratio:.1f}", C_B, 46, True),
                  (18, 556, "dense bool 配列に対する VolRLE のメモリ比", C_DIM, 12, False),
                  (18, 582, f"{len(rle):,} run で 256³ = {n ** 3:,} voxel 分の領域を表す",
                   C_TEXT, 13, False),
                  (18, 606, f"(dense は 1 voxel 1 byte = {dense_bytes / 1e6:.2f} MB)",
                   C_DIM, 12, False)])
    c = _footer(c, "使用 op: vol_rle_encode / vol_rle_decode / vol_rle_volume / "
                   "vol_rle_bbox / vol_rle_centroid / vol_rle_union / vol_rle_intersect / "
                   "vol_rle_difference  — 合成データ")
    info = _save_png(c, "wing3d_rle_compression", log)
    return {
        "name": "wing3d_rle_compression", "title": "run-length で 1/%.0f" % ratio,
        "ops": ["vol_rle_encode", "vol_rle_decode", "vol_rle_volume", "vol_rle_bbox",
                "vol_rle_centroid", "vol_rle_union", "vol_rle_intersect",
                "vol_rle_difference"],
        "facts": {"dense_MB": dense_bytes / 1e6, "rle_MB": rle.nbytes / 1e6,
                  "ratio": ratio, "runs": len(rle), "roundtrip_exact": exact,
                  "voxels": int(vox), "bbox": list(bbox), "centroid": list(cent),
                  "volume_speedup": t_den_vol / t_rle_vol,
                  "bbox_speedup": t_den_bb / t_rle_bb,
                  "union_voxels": int(v_un), "intersect_voxels": int(v_in),
                  "difference_voxels": int(v_di)},
        "caption": (f"256³ の合成部品を run-length で持つと **1/{ratio:.0f}**"
                    f"({dense_bytes / 1e6:.2f} MB → {rle.nbytes / 1e6:.3f} MB、"
                    f"{len(rle):,} run)。しかも展開せずに体積 {vox:,} voxel を "
                    f"**{t_den_vol / t_rle_vol:.0f} 倍速**、BBox を "
                    f"**{t_den_bb / t_rle_bb:.0f} 倍速**で返し、集合演算(球 ∪ 軸 = "
                    f"{v_un:,} voxel)も run のまま解ける。decode の往復は bit 一致。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 04 — CT windowing                                                        #
# --------------------------------------------------------------------------- #
def ex_windowing(log) -> dict:
    n = 128
    hu = _ct_phantom(n)
    windows = [("軟部組織窓 soft", 40.0, 400.0, C_A),
               ("骨窓 bone", 500.0, 2000.0, C_B),
               ("肺野窓 lung", -600.0, 1500.0, C_D)]
    outs = {}
    for name, cw, ww, _ in windows:
        o = np.asarray(G("vol_window_level")(hu, cw, ww))
        outs[name] = o
        log(f"    {name:18s} center {cw:+7.1f} width {ww:7.1f}  "
            f"saturate_low {100 * (o <= 0).mean():5.1f} %  "
            f"saturate_high {100 * (o >= 1).mean():5.1f} %  mean {o.mean():.3f}")

    tissue = {"空気 air": -1000.0, "肺 lung": -820.0, "軟部 soft": 40.0,
              "血管 vessel": 120.0, "肋骨 rib": 900.0, "椎体 spine": 1100.0}

    W, H = 1120, 726
    pw = 330
    frames = []
    # 往復する送り。**同じ z を 2 コマ続けて出さない**(折り返しの端も 1 回だけ)
    z_lo, z_hi = 14, n - 14
    up = list(range(z_lo, z_hi + 1, 5))
    zs = up + up[-2:0:-1]
    nf = len(zs)
    for z in zs:
        c = _canvas(W, H)
        c = _header(c, "CT の「窓」— 同じ 1 つのボリュームが 3 通りに見える",
                    f"合成 HU ボリューム(空気 -1000 / 肺 -820 / 軟部 40 / 血管 120 / "
                    f"肋骨 900 / 椎体 1100)を輪切りで送る  z = {z:3d} / {n - 1}")
        for i, (name, cw, ww, col) in enumerate(windows):
            px = 18 + i * (pw + 18)
            img = _cmap(outs[name][z], "gray")
            from PIL import Image
            im = Image.fromarray(_to_u8(img)).resize((pw, pw), Image.NEAREST)
            _paste(c, np.asarray(im, np.float64) / 255.0, px, 84)
            c = imagedraw.draw_polyline(
                c, [(px, 84), (px + pw - 1, 84), (px + pw - 1, 84 + pw - 1),
                    (px, 84 + pw - 1)], color=col, width=2, closed=True)
            sl = outs[name][z]
            c = _text(c, [
                (px, 84 + pw + 8, name, col, 15, True),
                (px, 84 + pw + 30, f"center {cw:+.0f} HU  width {ww:.0f} HU", C_DIM, 12, False),
                (px, 84 + pw + 48,
                 f"このスライスで黒に潰れた {100 * (sl <= 0).mean():.1f} % / "
                 f"白に飛んだ {100 * (sl >= 1).mean():.1f} %", C_TEXT, 12, False),
            ])

        # 下段: HU 軸に 3 つの窓を並べ、組織の位置を打つ
        p = Plot(c, 90, 566, W - 130, 92, (-1200, 1400), (0, 1),
                 xlabel="HU (Hounsfield 値) ->",
                 xticks=[-1000, -600, -200, 0, 200, 600, 1000, 1400],
                 yticks=[0, 0.5, 1.0], xfmt="%d", yfmt="%.1f")
        p.items.append((18, 546, "縦 = 窓の出力 [0,1](3 本の折れ線が 3 つの窓そのもの)",
                        C_DIM, 12, False))
        for name, cw, ww, col in windows:
            lo, hi = cw - ww / 2, cw + ww / 2
            xs = [-1200, lo, hi, 1400]
            ys = [0.0, 0.0, 1.0, 1.0]
            p.series(xs, ys, col, width=2)
        for j, (tname, huv) in enumerate(tissue.items()):
            p.c = imagedraw.draw_line(p.c, (p.px(huv), p.y0), (p.px(huv), p.y0 + p.h - 1),
                                      color=(0.30, 0.32, 0.36), width=1)
            p.items.append((p.px(huv) - _text_w(tname, 10, True) / 2,
                            p.y0 - 34 + 16 * (j % 2), tname, C_DIM, 10, True))
        c = p.done()
        c = _footer(c, "使用 op: vol_window_level  — 合成 HU データ(実在の患者・"
                       "スキャンではありません)")
        frames.append(c)

    info = _save_clip(frames, "wing3d_ct_windowing", fps=12, thumb_index=nf // 3, log=log)
    return {
        "name": "wing3d_ct_windowing", "title": "CT の「窓」で同じ体が 3 通りに見える",
        "ops": ["vol_window_level"],
        "facts": {w[0]: {"center": w[1], "width": w[2],
                         "saturate_low_pct": 100 * float((outs[w[0]] <= 0).mean()),
                         "saturate_high_pct": 100 * float((outs[w[0]] >= 1).mean()),
                         "mean": float(outs[w[0]].mean())} for w in windows},
        "caption": ("同じ合成 HU ボリュームを `vol_window_level` の 3 つの窓で見る。"
                    f"軟部組織窓では体積の {100 * float((outs['軟部組織窓 soft'] <= 0).mean()):.1f} % "
                    f"が黒へ潰れ肋骨は白飛びし、骨窓では白飛びが "
                    f"{100 * float((outs['骨窓 bone'] >= 1).mean()):.1f} % まで下がって骨梁が読め、"
                    f"肺野窓では黒潰れが {100 * float((outs['肺野窓 lung'] <= 0).mean()):.1f} % で"
                    "肺の中身が出る。下の折れ線が窓そのもの(HU → [0,1] の一次写像 + クリップ)。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 05 — Frangi 対 Sato 対 blobness                                          #
# --------------------------------------------------------------------------- #
def ex_vesselness(log) -> dict:
    n = 88
    tube = _capsule((n, n, n), (6, 44, 26), (81, 44, 26), 3.2)
    b1 = _aa_ball((n, n, n), (26., 42., 60.), 6.0) > 0.5
    b2 = _aa_ball((n, n, n), (60., 46., 60.), 6.0) > 0.5
    vol = (tube | b1 | b2).astype(np.float64)
    import scipy.ndimage as ndi
    vol = ndi.gaussian_filter(vol, 1.0)

    fr = np.asarray(G("vol_frangi")(vol, scales=(1, 2, 3)))
    sa = np.asarray(G("vol_sato")(vol, scales=(1, 2, 3)))
    # blobness は単一スケールの op なので、frangi/sato と条件を揃えるため
    # 同じ 3 スケールで掛けて voxel ごとの最大応答を取る(多スケール化を明示)。
    bl = np.max([np.asarray(G("vol_hessian_blobness")(vol, scale=s))
                 for s in (1, 2, 3)], axis=0)
    m_t, m_b = tube, (b1 | b2)
    res = {}
    for nm, r in (("vol_frangi", fr), ("vol_sato", sa), ("vol_hessian_blobness", bl)):
        tm, bm = float(r[m_t].mean()), float(r[m_b].mean())
        res[nm] = {"tube_mean": tm, "blob_mean": bm, "ratio": tm / max(bm, 1e-12),
                   "max": float(r.max())}
        log(f"    {nm:22s} tube {tm:.4f}  blob {bm:.4f}  tube/blob {tm / max(bm, 1e-12):.3f}")

    W, H = 1120, 700
    pw = 258
    c = _canvas(W, H)
    c = _header(c, "管を光らせる op と、粒を光らせる op — 否定対照で確かめる",
                "合成 CT(まっすぐな管 1 本 + 球 2 個)。「管状度」が本当に管だけを "
                "選んでいるかは、粒だけを選ぶ op と並べないと分からない。")
    z = 43
    panels = [("入力(合成 CT の 1 枚)", _cmap(_norm01(vol[z]), "gray"), C_TEXT),
              ("vol_frangi(管状度)", _cmap(_norm01(fr[z], 0, 1), "inferno"), C_B),
              ("vol_sato(管状度・別定式)", _cmap(_norm01(sa[z], 0, 1), "inferno"), C_C),
              ("vol_hessian_blobness(粒状度)", _cmap(_norm01(bl[z], 0, 1), "viridis"), C_D)]
    from PIL import Image
    for i, (title, img, col) in enumerate(panels):
        px = 18 + i * (pw + 14)
        im = Image.fromarray(_to_u8(img)).resize((pw, pw), Image.NEAREST)
        _paste(c, np.asarray(im, np.float64) / 255.0, px, 84)
        c = imagedraw.draw_polyline(
            c, [(px, 84), (px + pw - 1, 84), (px + pw - 1, 84 + pw - 1), (px, 84 + pw - 1)],
            color=col, width=2, closed=True)
        sc = pw / n
        # 管と球の在り処を毎回示す(応答が 0 でも「そこに何があるか」が読める)
        c = imagedraw.draw_circle(c, (px + 26 * sc, 84 + 44 * sc), 7 * sc,
                                  color=(0.95, 0.95, 0.95), width=1)
        c = imagedraw.draw_circle(c, (px + 60 * sc, 84 + 46 * sc), 9 * sc,
                                  color=(0.62, 0.64, 0.68), width=1)
        c = _text(c, [(px, 84 + pw + 6, title, col, 12, True)])
    c = _text(c, [(18 + 26 * (pw / n) + 8, 84 + 30, "管", (0.95, 0.95, 0.95), 12, True),
                  (18 + 60 * (pw / n) + 10, 84 + 40, "球", (0.62, 0.64, 0.68), 12, True)])

    names = list(res.keys())
    p = Plot(c, 110, 400, 470, 170, (-0.5, 2.5), (0, 1.05),
             ylabel="領域内の平均応答(0-1)", xticks=[], yticks=[0, 0.25, 0.5, 0.75, 1.0],
             yfmt="%.2f")
    bw = 44
    for i, nm in enumerate(names):
        x = p.px(i)
        for j, (key, col) in enumerate((("tube_mean", C_B), ("blob_mean", C_D))):
            v = res[nm][key]
            xx0 = int(x - bw + j * bw)
            yy0 = int(p.py(v)); yy1 = int(p.py(0))
            _fill(p.c, xx0 + 3, yy0, xx0 + bw - 3, yy1, col)
            p.items.append((xx0 + 4, yy0 - 17, "%.3f" % v, col, 11, True))
        p.items.append((x - _text_w(nm.replace("vol_", ""), 11) / 2, p.y0 + p.h + 4,
                        nm.replace("vol_", ""), C_TEXT, 11, True))
    p.items.append((116, 404, "管の中の平均", C_B, 12, True))
    p.items.append((116, 422, "球の中の平均", C_D, 12, True))
    c = p.done()

    lines = ["op                        管の平均   球の平均   管/球",
             "-" * 52]
    for nm in names:
        r = res[nm]
        lines.append("%-24s  %7.4f   %7.4f   %6.3f" %
                     (nm, r["tube_mean"], r["blob_mean"], r["ratio"]))
    items = [(610, 400, "実測(領域内平均。値は 0-1 に正規化済みの応答)", C_DIM, 12, False)]
    for i, s in enumerate(lines):
        items.append((610, 424 + i * 20, s, C_TEXT if i > 1 else C_DIM, 13, i > 1))
    items.append((610, 424 + len(lines) * 20 + 8,
                  "読み: frangi は管を球より %.2f 倍強く出す。sato は %.2f 倍で"
                  % (res["vol_frangi"]["ratio"], res["vol_sato"]["ratio"]), C_TEXT, 12, False))
    items.append((610, 424 + len(lines) * 20 + 26,
                  "ほぼ区別しない。blobness は %.2f 倍 = 逆転し、否定対照になっている。"
                  % (res["vol_hessian_blobness"]["ratio"]), C_TEXT, 12, False))
    c = _text(c, items)
    c = _footer(c, "使用 op: vol_frangi / vol_sato / vol_hessian_blobness  — 合成データ")
    info = _save_png(c, "wing3d_vesselness_control", log)
    return {
        "name": "wing3d_vesselness_control",
        "title": "Frangi 対 Sato ―― 否定対照(粒状度)を並べて初めて分かる",
        "ops": ["vol_frangi", "vol_sato", "vol_hessian_blobness"],
        "facts": res,
        "caption": ("管 1 本と球 2 個だけの合成 CT に、管状度 2 種と粒状度 1 種を掛けた。"
                    f"`vol_frangi` は管を球より **{res['vol_frangi']['ratio']:.2f} 倍**強く出すが、"
                    f"`vol_sato` は **{res['vol_sato']['ratio']:.2f} 倍**でほとんど区別しない。"
                    f"否定対照の `vol_hessian_blobness` は **{res['vol_hessian_blobness']['ratio']:.2f} 倍** "
                    "= 管より球を選び、向きがきれいに逆転する。「血管が光った」だけでは"
                    "管状度の証明にならない、という当たり前を図にした。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 06 — 3D スケルトンのグラフ化                                              #
# --------------------------------------------------------------------------- #
def ex_skeleton(log) -> dict:
    n = 104
    segs = [((10, 52, 52), (46, 52, 52), 5.0),
            ((46, 52, 52), (80, 22, 40), 3.4),
            ((46, 52, 52), (80, 80, 42), 3.4),
            ((46, 52, 52), (72, 52, 88), 3.0),
            ((80, 22, 40), (96, 14, 20), 2.4),
            ((80, 80, 42), (95, 90, 72), 2.2)]
    tree = np.zeros((n, n, n), bool)
    for p0, p1, r in segs:
        tree |= _capsule((n, n, n), p0, p1, r)
    solid = tree.astype(np.float64)
    sk = np.asarray(G("skeletonize_vol")(solid))
    ep = np.asarray(G("skeleton_endpoints3d")(sk))
    ju = np.asarray(G("skeleton_junctions3d")(sk))
    br = np.asarray(G("skeleton_branches3d")(sk, min_length=0))

    import scipy.ndimage as ndi
    st = np.ones((3, 3, 3), int)
    lab_b, n_b = ndi.label(br, structure=st)
    lab_j, n_j = ndi.label(ju, structure=st)
    lab_e, n_e = ndi.label(ep, structure=st)
    log(f"    solid {int(solid.sum()):,} -> skeleton {int(sk.sum()):,} voxel "
        f"({100 * sk.sum() / solid.sum():.2f} %)")
    log(f"    branches {n_b}  junction clusters {n_j} ({int(ju.sum())} voxel)  "
        f"endpoints {n_e}")

    pts_solid = np.argwhere(solid > 0.5).astype(np.float64)
    rng = np.random.default_rng(SEED)
    sel = np.sort(rng.choice(pts_solid.shape[0], size=min(11000, pts_solid.shape[0]),
                             replace=False))
    pts_solid = pts_solid[sel]
    pts_br = np.argwhere(br).astype(np.float64)
    id_br = lab_b[br]
    pts_ju = np.argwhere(ju).astype(np.float64)
    pts_ep = np.argwhere(ep).astype(np.float64)
    branch_colors = np.asarray([C_A, C_B, C_C, C_D, C_E, (0.95, 0.85, 0.35),
                                (0.45, 0.75, 0.98), (0.85, 0.55, 0.75)])
    col_br = branch_colors[(id_br - 1) % len(branch_colors)]

    W, H = 1120, 660
    pw, ph = 348, 420
    center = np.array([n / 2.0, n / 2.0, n / 2.0])[[2, 1, 0]]
    nf = 48
    frames = []
    for k in range(nf):
        R = _rot(360.0 * k / nf, 20.0)
        c = _canvas(W, H)
        c = _header(c, "3-D スケルトン ―― 塊を 1 voxel 幅の針金にしてグラフにする",
                    "合成した枝分かれ構造(6 本の円柱)を細線化し、枝・分岐点・端点に"
                    "色を分ける。1 周回してつながり方を確かめる。")
        scale = 3.05
        for i, (title, pts, cols, rad) in enumerate((
                ("入力(中実 %d voxel、表示は間引き)" % int(solid.sum()), pts_solid, C_DIM, 1),
                ("skeletonize_vol(%d voxel)" % int(sk.sum()),
                 np.argwhere(sk).astype(np.float64), (0.92, 0.93, 0.90), 1),
                ("枝 %d 本 / 分岐 %d / 端点 %d" % (n_b, n_j, n_e), None, None, 1))):
            px = 18 + i * (pw + 20)
            _fill(c, px, 84, px + pw, 84 + ph, C_PANEL)
            sub = c[84:84 + ph, px:px + pw]
            if pts is not None:
                world = pts[:, [2, 1, 0]]
                u, v, d = _project(world, R, scale, pw / 2, ph / 2, center)
                _splat(sub, u, v, d, cols, radius=rad, shade=0.5)
            else:
                world = pts_br[:, [2, 1, 0]]
                u, v, d = _project(world, R, scale, pw / 2, ph / 2, center)
                _splat(sub, u, v, d, col_br, radius=1, shade=0.35)
                for pset, col, rr in ((pts_ju, (1.0, 1.0, 1.0), 4),
                                      (pts_ep, C_E, 3)):
                    if pset.size:
                        uu, vv, dd = _project(pset[:, [2, 1, 0]], R, scale,
                                              pw / 2, ph / 2, center)
                        _splat(sub, uu, vv, dd, col, radius=rr, shade=0.0)
            c = imagedraw.draw_polyline(
                c, [(px, 84), (px + pw - 1, 84), (px + pw - 1, 84 + ph - 1),
                    (px, 84 + ph - 1)], color=C_RULE, width=1, closed=True)
            c = _axis_gizmo(c, R, px + 44, 84 + ph - 44, size=26)
            c = _text(c, [(px, 84 + ph + 6, title, C_TEXT, 12, True)])

        c = _text(c, [
            (18, 548, f"中実 {int(solid.sum()):,} voxel  ->  骨格 {int(sk.sum()):,} voxel "
                      f"({100 * sk.sum() / solid.sum():.2f} %)", C_TEXT, 14, True),
            (18, 572, f"枝(skeleton_branches3d)= {n_b} 本   "
                      f"分岐(skeleton_junctions3d)= {n_j} か所 / {int(ju.sum())} voxel   "
                      f"端点(skeleton_endpoints3d)= {n_e}", C_TEXT, 14, True),
            (18, 598, "白 = 分岐点, ローズ = 端点, 枝は連結成分ごとに色分け。"
                      "分岐 voxel は 26 近傍次数で拾うので複数 voxel に散る "
                      "— 個数は連結成分でまとめて数えている。", C_DIM, 12, False),
            (18, 620, f"入力は円柱 {len(segs)} 本だが、まっすぐ続く 2 本は 1 本の枝に"
                      f"なるので位相的な枝は 4 本・端点は 4 点が真値。実測 "
                      f"{n_b} 本 / {n_e} 点で一致。", C_DIM, 12, False),
        ])
        c = _footer(c, "使用 op: skeletonize_vol / skeleton_branches3d / "
                       "skeleton_junctions3d / skeleton_endpoints3d  — 合成データ")
        frames.append(c)

    info = _save_clip(frames, "wing3d_skeleton_graph", fps=14, thumb_index=8, log=log)
    return {
        "name": "wing3d_skeleton_graph", "title": "3-D スケルトンをグラフにする",
        "ops": ["skeletonize_vol", "skeleton_branches3d", "skeleton_junctions3d",
                "skeleton_endpoints3d"],
        "facts": {"solid_voxels": int(solid.sum()), "skeleton_voxels": int(sk.sum()),
                  "skeleton_pct": 100 * float(sk.sum() / solid.sum()),
                  "branches": int(n_b), "junction_clusters": int(n_j),
                  "junction_voxels": int(ju.sum()), "endpoints": int(n_e),
                  "input_segments": len(segs)},
        "caption": (f"合成した枝分かれ構造({int(solid.sum()):,} voxel)を `skeletonize_vol` に"
                    f"通すと {int(sk.sum()):,} voxel の 1 voxel 幅の針金になる"
                    f"(**{100 * float(sk.sum() / solid.sum()):.2f} %**)。そこから枝 **{n_b} 本**・"
                    f"分岐 **{n_j} か所**・端点 **{n_e} 点**をグラフとして取り出した。"
                    "白が分岐、ローズが端点、枝は連結成分ごとに色分け。ターンテーブルで"
                    "1 周するとつながり方が読める。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 07 — virtual probe で壁厚                                                #
# --------------------------------------------------------------------------- #
def ex_wall(log) -> dict:
    sp = (0.25, 0.25, 0.25)
    n = 96
    zz, yy, xx = _grid((n, n, n))
    cy = cx = 48.0
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    r_out_mm, r_in_mm = 10.0, 8.0
    ro, ri = r_out_mm / sp[1], r_in_mm / sp[1]
    # 反エイリアス(50 % 等値面が厳密に r_out / r_in に来る)= 測長の真値が作れる
    pipe = np.clip(ro - rr + 0.5, 0, 1) * np.clip(rr - ri + 0.5, 0, 1)
    truth = r_out_mm - r_in_mm

    p0 = (48.0, 48.0, 0.0)
    p1 = (48.0, 48.0, float(n - 1))
    th = list(G("vol_wall_thickness")(pipe, p0, p1, sigma=1.0, threshold=0.05, spacing=sp))
    edges = G("vol_edge_probe")(pipe, p0, p1, sigma=1.0, threshold=0.05, spacing=sp)
    t_mm, prof = G("vol_profile_line")(pipe, p0, p1, spacing=sp)
    t_mm = np.asarray(t_mm); prof = np.asarray(prof)
    log(f"    thickness {['%.4f' % v for v in th]} mm  truth {truth:.4f} mm")
    for e in edges:
        log(f"      edge t={e['t_mm']:8.4f} mm  pol {e['polarity']:+d}  "
            f"amp {e['amplitude']:.4f}  x_vox {e['position'][2]:.3f}")
    sweep = {}
    for sg in (0.5, 1.0, 2.0, 3.0, 4.0):
        sweep[sg] = list(G("vol_wall_thickness")(pipe, p0, p1, sigma=sg,
                                                 threshold=0.05, spacing=sp))
        log(f"      sigma={sg:.1f} -> {['%.4f' % v for v in sweep[sg]]}")

    W, H = 1120, 680
    c = _canvas(W, H)
    c = _header(c, "virtual probe ―― パイプ断面にプローブを 1 本刺して壁厚を測る",
                "合成パイプ(外径 10.000 mm / 内径 8.000 mm、spacing 0.25 mm/voxel、"
                "反エイリアスで 50 % 等値面が厳密に真値へ来るように作った)")
    # 左: 断面 + プローブ
    pw = 400
    px, py = 18, 92
    from PIL import Image
    img = _cmap(pipe[48], "gray")
    im = Image.fromarray(_to_u8(img)).resize((pw, pw), Image.NEAREST)
    _paste(c, np.asarray(im, np.float64) / 255.0, px, py)
    sc = pw / n
    c = imagedraw.draw_line(c, (px + 0 * sc, py + 48 * sc), (px + (n - 1) * sc, py + 48 * sc),
                            color=C_B, width=2)
    for e in edges:
        xv = e["position"][2]
        c = imagedraw.draw_markers(c, [(px + xv * sc, py + 48 * sc)],
                                   color=C_A if e["polarity"] > 0 else C_E,
                                   size=7, shape="cross", width=2)
    c = imagedraw.draw_polyline(
        c, [(px, py), (px + pw - 1, py), (px + pw - 1, py + pw - 1), (px, py + pw - 1)],
        color=C_RULE, width=1, closed=True)
    c = _text(c, [(px, py + pw + 6, "z = 48 の断面とプローブ(黄)。× = 検出したエッジ",
                   C_TEXT, 12, True),
                  (px, py + pw + 26, "シアン = 立ち上がり(暗→明)、ローズ = 立ち下がり",
                   C_DIM, 12, False)])

    # 右: プロファイルとエッジ
    p = Plot(c, 500, 100, 590, 200, (0, float(t_mm[-1])), (-0.05, 1.1),
             xlabel="プローブに沿った距離 [mm] ->", ylabel="濃淡値(0-1)",
             xticks=[0, 4, 8, 12, 16, 20, 24], yticks=[0, 0.5, 1.0],
             xfmt="%d", yfmt="%.1f")
    p.series(t_mm, prof, C_TEXT, width=2)
    p.hline(0.5, C_DIM, width=1)
    for e in edges:
        col = C_A if e["polarity"] > 0 else C_E
        p.c = imagedraw.draw_line(p.c, (p.px(e["t_mm"]), p.y0),
                                  (p.px(e["t_mm"]), p.y0 + p.h - 1), color=col, width=1)
        p.items.append((p.px(e["t_mm"]) - 18, p.y0 - 16, "%.3f" % e["t_mm"], col, 10, True))
    c = p.done()

    rows = ["エッジ(vol_edge_probe, sigma=1.0, threshold=0.05)"]
    for i, e in enumerate(edges):
        rows.append("  #%d  t = %8.4f mm   %s   |dI/dt| = %.3f /mm"
                    % (i + 1, e["t_mm"],
                       "立ち上がり" if e["polarity"] > 0 else "立ち下がり",
                       e["amplitude"]))
    rows.append("")
    rows.append("壁厚(vol_wall_thickness = 立ち上がり→立ち下がりの対)")
    for i, v in enumerate(th):
        rows.append("  壁 %d :  %.4f mm   (真値 %.4f mm, 差 %+.4f mm)"
                    % (i + 1, v, truth, v - truth))
    items = [(500, 340 + i * 21, s, C_TEXT if s.startswith("  ") else C_DIM,
              13, not s.startswith("  ")) for i, s in enumerate(rows)]
    c = _text(c, items)

    p2 = Plot(c, 560, 520, 530, 118, (0.3, 4.2), (1.95, 2.20),
              xlabel="平滑化 sigma [サンプル] ->", ylabel="測った壁厚 [mm]",
              xticks=[0.5, 1, 2, 3, 4], yticks=[2.00, 2.05, 2.10, 2.15],
              xfmt="%.1f", yfmt="%.2f")
    xs = sorted(sweep.keys())
    ys = [sweep[s][0] for s in xs]
    p2.series(xs, ys, C_B, width=2, markers=True)
    p2.hline(truth, C_D, width=1)
    p2.items.append((p2.px(0.55), p2.py(truth) - 16, "真値 2.000 mm", C_D, 11, True))
    c = p2.done()
    c = _text(c, [(18, 520, "平滑化を強めると測長は太る側へ壊れる", C_TEXT, 15, True),
                  (18, 546, "sigma=1.0 では %.4f mm(誤差 %+.4f mm)。" % (th[0], th[0] - truth),
                   C_TEXT, 13, False),
                  (18, 566, "sigma=3.0 では %.4f mm(誤差 %+.4f mm)= %.1f %% の偏り。"
                   % (sweep[3.0][0], sweep[3.0][0] - truth,
                      100 * (sweep[3.0][0] - truth) / truth), C_B, 13, True),
                  (18, 590, "ノイズを抑えるつもりの平滑化が、そのまま寸法の偏りに変わる。",
                   C_DIM, 12, False),
                  (18, 612, "反エイリアスしていない二値パイプで同じことをすると",
                   C_DIM, 12, False),
                  (18, 630, "離散化だけで +0.125 mm ずれる(内外の境界が半 voxel 動くため)。",
                   C_DIM, 12, False)])
    c = _footer(c, "使用 op: vol_profile_line / vol_edge_probe / vol_wall_thickness  "
                   "— 合成データ", y_off=18)
    info = _save_png(c, "wing3d_wall_thickness", log)
    return {
        "name": "wing3d_wall_thickness",
        "title": "virtual probe で壁厚 %.3f mm(真値 %.3f mm)" % (th[0], truth),
        "ops": ["vol_profile_line", "vol_edge_probe", "vol_wall_thickness"],
        "facts": {"thicknesses_mm": th, "truth_mm": truth,
                  "edges": [{"t_mm": e["t_mm"], "polarity": int(e["polarity"]),
                             "amplitude": float(e["amplitude"]),
                             "x_voxel": float(e["position"][2])} for e in edges],
                  "sigma_sweep": {str(k): v for k, v in sweep.items()},
                  "spacing_mm": list(sp)},
        "caption": (f"外径 10.000 mm / 内径 8.000 mm の合成パイプにプローブを 1 本だけ刺す。"
                    f"`vol_edge_probe` が 4 つのエッジをサブサンプル精度で拾い、"
                    f"`vol_wall_thickness` が立ち上がり→立ち下がりの対から壁厚 "
                    f"**{th[0]:.4f} mm / {th[1]:.4f} mm**(真値 {truth:.3f} mm)を返す。"
                    f"平滑化 sigma を 3.0 まで上げると {sweep[3.0][0]:.4f} mm "
                    f"(**{100 * (sweep[3.0][0] - truth) / truth:+.1f} %**)に太る "
                    "— ノイズ対策がそのまま寸法の偏りになる、という測定の基本も一緒に。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 08 — Richardson-Lucy                                                     #
# --------------------------------------------------------------------------- #
def ex_rl(log) -> dict:
    n = 64
    truth = ((_aa_ball((n, n, n), (32., 26., 26.), 8.0) > 0.5) |
             (_aa_ball((n, n, n), (32., 40., 40.), 8.0) > 0.5)).astype(np.float64)
    psf = np.asarray(G("vol_gaussian_psf")(2.0))
    import scipy.ndimage as ndi
    obs = ndi.convolve(truth, psf, mode="constant")

    def rmse(a, b):
        return float(np.sqrt(((np.asarray(a) - np.asarray(b)) ** 2).mean()))

    base = rmse(obs, truth)
    iters = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 18, 22, 26, 30, 35, 40, 45, 50]
    ests, r_gt, r_fw = {}, {}, {}
    for it in iters:
        est = np.asarray(G("vol_richardson_lucy")(obs, psf, iterations=it))
        ests[it] = est
        r_gt[it] = rmse(est, truth) / base
        r_fw[it] = rmse(ndi.convolve(est, psf, mode="constant"), obs) / base
        log(f"    it={it:3d}  RMSE(真値) {r_gt[it]:.4f}x   前方一貫性 {r_fw[it]:.4f}x")

    W, H = 1120, 660
    frames = []
    pw = 250
    z = 32
    from PIL import Image
    for k, it in enumerate(iters):
        c = _canvas(W, H)
        c = _header(c, "Richardson-Lucy ―― ぼけを解く反復と、解けない部分",
                    f"合成ボリューム(球 2 個)を sigma=2.0 のガウス PSF でぼかし、"
                    f"反復 {it:2d} 回で復元。z = {z} の断面。")
        est = ests[it]
        fwd = ndi.convolve(est, psf, mode="constant")
        panels = [("真値(ground truth)", truth[z], C_D),
                  ("観測(PSF でぼけた)", obs[z], C_DIM),
                  ("vol_richardson_lucy %d 回" % it, est[z], C_B),
                  ("復元をもう一度ぼかした", fwd[z], C_A)]
        for i, (title, img, col) in enumerate(panels):
            px = 18 + i * (pw + 14)
            im = Image.fromarray(_to_u8(_cmap(np.clip(img, 0, 1), "gray"))).resize(
                (pw, pw), Image.NEAREST)
            _paste(c, np.asarray(im, np.float64) / 255.0, px, 86)
            c = imagedraw.draw_polyline(
                c, [(px, 86), (px + pw - 1, 86), (px + pw - 1, 86 + pw - 1), (px, 86 + pw - 1)],
                color=col, width=2, closed=True)
            c = _text(c, [(px, 86 + pw + 6, title, col, 12, True)])

        p = Plot(c, 100, 400, 560, 190, (0, 52), (0.02, 1.4),
                 xlabel="反復回数 ->", ylabel="観測のぼけを 1.000 としたときの RMSE 比",
                 xticks=[1, 10, 20, 30, 40, 50], yticks=[0.05, 0.1, 0.2, 0.5, 1.0],
                 xfmt="%d", yfmt="%.2f", logy=True)
        p.hline(1.0, C_DIM)
        p.items.append((p.px(41), p.py(1.0) - 16, "観測のぼけ = 1.000", C_DIM, 11, False))
        p.series(iters, [r_gt[i] for i in iters], C_B, width=2)
        p.series(iters, [r_fw[i] for i in iters], C_A, width=2)
        p.marker(it, r_gt[it], C_B, size=6)
        p.marker(it, r_fw[it], C_A, size=6)
        p.items.append((106, 404, "真値との RMSE", C_B, 12, True))
        p.items.append((106, 422, "前方一貫性(復元を再びぼかして観測と比べる)", C_A, 12, True))
        c = p.done()

        c = _text(c, [
            (700, 400, "反復 %d 回のとき" % it, C_DIM, 13, False),
            (700, 424, "前方一貫性  %.4f x" % r_fw[it], C_A, 22, True),
            (700, 456, "真値の RMSE  %.4f x" % r_gt[it], C_B, 22, True),
            (700, 496, "前方一貫性は %.3fx まで一気に落ちる(= 観測は完全に"
             % min(r_fw.values()), C_TEXT, 12, False),
            (700, 514, "説明できている)のに、真値との差は %.3fx までしか下がらない。"
             % min(r_gt.values()), C_TEXT, 12, False),
            (700, 536, "残るのは球のふちの階段 — 離散格子では PSF の逆問題が", C_DIM, 12, False),
            (700, 554, "端で不定になるため。速さの違いをそのまま出しておく。", C_DIM, 12, False),
            (700, 582, "「よく復元できた」を前方一貫性だけで言うと嘘になる、", C_TEXT, 12, True),
            (700, 600, "という実例。", C_TEXT, 12, True),
        ])
        c = _footer(c, "使用 op: vol_gaussian_psf / vol_richardson_lucy  — 合成データ")
        frames.append(c)

    info = _save_clip(frames, "wing3d_richardson_lucy", fps=4, thumb_index=len(iters) - 6,
                      log=log)
    return {
        "name": "wing3d_richardson_lucy",
        "title": "Richardson-Lucy ―― 前方一貫性 %.3fx に対し真値 RMSE は %.3fx" % (
            min(r_fw.values()), min(r_gt.values())),
        "ops": ["vol_gaussian_psf", "vol_richardson_lucy"],
        "facts": {"psf_sigma": 2.0, "psf_shape": list(psf.shape),
                  "blurred_rmse": base,
                  "rmse_ratio_vs_truth": {str(k): v for k, v in r_gt.items()},
                  "forward_consistency_ratio": {str(k): v for k, v in r_fw.items()}},
        "caption": ("sigma 2.0 のガウス PSF でぼかした合成ボリュームを "
                    "`vol_richardson_lucy` で反復復元する。復元をもう一度ぼかして観測と"
                    f"比べる**前方一貫性は {min(r_fw.values()):.3f} 倍**まで一気に落ちるのに、"
                    f"**真値との RMSE は {min(r_gt.values()):.3f} 倍**までしか下がらない。"
                    "残っているのは球のふちの階段で、「観測をよく説明できた」ことは"
                    "「真値に近い」ことではない ―― という反例をそのまま展示にした。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 09 — visual hull(空間彫刻)                                              #
# --------------------------------------------------------------------------- #
def ex_visual_hull(log) -> dict:
    rng = np.random.default_rng(SEED)
    npts = 9000

    def box_pts(c, half, k):
        return rng.uniform(-1, 1, (k, 3)) * np.asarray(half, np.float64) + np.asarray(c, np.float64)

    half1, cen1 = (18.0, 6.0, 6.0), (0.0, 0.0, 0.0)
    half2, cen2 = (6.0, 11.0, 6.0), (10.0, 12.0, 0.0)
    pts = np.vstack([box_pts(cen1, half1, npts // 2), box_pts(cen2, half2, npts // 2)])

    K = np.array([[300.0, 0.0, 80.0], [0.0, 300.0, 80.0], [0.0, 0.0, 1.0]])
    bounds = ((-30.0, 30.0), (-30.0, 30.0), (-20.0, 20.0))
    res = 56
    n_views = 16
    sils, Ks, Rs, ts, eyes = [], [], [], [], []
    for i in range(n_views):
        a = 2 * math.pi * i / n_views
        eye = (120.0 * math.cos(a), 120.0 * math.sin(a), 42.0)
        R, t = visualhull.look_at(eye, (0.0, 0.0, 0.0), up=(0.0, 0.0, 1.0))
        sils.append(visualhull.synthesize_silhouette(pts, K, R, t, (160, 160)))
        Ks.append(K); Rs.append(R); ts.append(t); eyes.append(eye)

    # 真の占有(同じ格子に 2 つの直方体を離散化)
    xs = bounds[0][0] + (np.arange(res) + 0.5) * (bounds[0][1] - bounds[0][0]) / res
    ys = bounds[1][0] + (np.arange(res) + 0.5) * (bounds[1][1] - bounds[1][0]) / res
    zs = bounds[2][0] + (np.arange(res) + 0.5) * (bounds[2][1] - bounds[2][0]) / res
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")

    def in_box(c, half):
        return ((np.abs(X - c[0]) <= half[0]) & (np.abs(Y - c[1]) <= half[1])
                & (np.abs(Z - c[2]) <= half[2]))
    gt = in_box(cen1, half1) | in_box(cen2, half2)
    gt_n = int(gt.sum())

    occ_by_m, stats = {}, {}
    for m in range(1, n_views + 1):
        occ = visualhull.carve(sils[:m], Ks[:m], Rs[:m], ts[:m], bounds, res)
        occ_by_m[m] = occ
        inter = int((occ & gt).sum())
        stats[m] = {"occ": int(occ.sum()), "over": int(occ.sum()) / gt_n,
                    "recall": inter / gt_n,
                    "iou": inter / max(int((occ | gt).sum()), 1)}
        log(f"    views {m:2d}: occ {stats[m]['occ']:6d}  over {stats[m]['over']:.3f}x  "
            f"recall {stats[m]['recall']:.4f}  IoU {stats[m]['iou']:.4f}")

    cell = np.array([(bounds[0][1] - bounds[0][0]) / res,
                     (bounds[1][1] - bounds[1][0]) / res,
                     (bounds[2][1] - bounds[2][0]) / res])
    origin = np.array([bounds[0][0], bounds[1][0], bounds[2][0]])

    W, H = 1120, 690
    pw, ph = 400, 400
    frames = []
    for m in range(1, n_views + 1):
        occ = occ_by_m[m]
        idx = np.argwhere(occ).astype(np.float64)
        world = origin + (idx + 0.5) * cell               # 既に (x, y, z)
        gt_idx = np.argwhere(gt).astype(np.float64)
        gt_world = origin + (gt_idx + 0.5) * cell
        R = _rot(28.0 + 8.0 * m, 24.0)
        c = _canvas(W, H)
        c = _header(c, "visual hull(空間彫刻)―― 影を重ねて形を削り出す",
                    f"L 字の合成物体を {n_views} 方向から撮ったシルエットのうち、"
                    f"手前から {m} 枚だけ使って彫った結果。")
        px, py = 18, 88
        _fill(c, px, py, px + pw, py + ph, C_PANEL)
        sub = c[py:py + ph, px:px + pw]
        scale = 5.2
        cen = np.zeros(3)
        if gt_world.size:
            u, v, d = _project(gt_world, R, scale, pw / 2, ph / 2, cen)
            _splat(sub, u, v, d, (0.22, 0.24, 0.28), radius=2, shade=0.3)
        if world.size:
            u, v, d = _project(world, R, scale, pw / 2, ph / 2, cen)
            _splat(sub, u, v, d, C_B, radius=1, shade=0.55)
        c = imagedraw.draw_polyline(
            c, [(px, py), (px + pw - 1, py), (px + pw - 1, py + ph - 1), (px, py + ph - 1)],
            color=C_RULE, width=1, closed=True)
        c = _axis_gizmo(c, R, px + 46, py + ph - 46, size=30)
        c = _text(c, [(px, py + ph + 6, "アンバー = 彫り出した占有 voxel / "
                                        "グレー = 真の形(同じ格子に離散化)", C_TEXT, 12, True)])

        # 中央: 使ったシルエット(最大 8 枚をタイル)
        sx, sy = 440, 88
        tile = 92
        for i in range(min(m, 8)):
            gx = sx + (i % 4) * (tile + 8)
            gy = sy + (i // 4) * (tile + 24)
            im = Image.fromarray(_to_u8(_gray_rgb(sils[i].astype(np.float64)))) \
                if False else None
            from PIL import Image as _Im
            im = _Im.fromarray(_to_u8(_gray_rgb(sils[i].astype(np.float64)))).resize(
                (tile, tile), _Im.NEAREST)
            _paste(c, np.asarray(im, np.float64) / 255.0, gx, gy)
            c = imagedraw.draw_polyline(
                c, [(gx, gy), (gx + tile - 1, gy), (gx + tile - 1, gy + tile - 1),
                    (gx, gy + tile - 1)], color=C_A, width=1, closed=True)
            a = 360.0 * i / n_views
            c = _text(c, [(gx, gy + tile + 3, "view %d  %.0f deg" % (i + 1, a), C_DIM, 10, False)])
        if m > 8:
            c = _text(c, [(sx, sy + 2 * (tile + 24) + 2,
                           "... 以下 %d 枚(合計 %d 枚を使用)" % (m - 8, m), C_DIM, 12, False)])

        p = Plot(c, 500, 350, 590, 190, (1, n_views), (0.8, 5.0),
                 xlabel="使ったシルエットの枚数 ->",
                 ylabel="真の体積を 1.0 としたときの倍率 / IoU",
                 xticks=[1, 4, 8, 12, 16], yticks=[1, 2, 3, 4, 5],
                 xfmt="%d", yfmt="%.0f")
        p.series(range(1, n_views + 1), [stats[i]["over"] for i in range(1, n_views + 1)],
                 C_B, width=2, markers=True)
        p.series(range(1, n_views + 1),
                 [0.8 + 4.2 * stats[i]["iou"] for i in range(1, n_views + 1)],
                 C_D, width=2, markers=True)
        p.hline(1.0, C_DIM)
        p.marker(m, stats[m]["over"], C_B, size=6)
        p.marker(m, 0.8 + 4.2 * stats[m]["iou"], C_D, size=6)
        p.items.append((506, 354, "体積の倍率(1.0 = 真値)", C_B, 12, True))
        p.items.append((506, 372, "IoU(右目盛り 0 - 1 を 0.8-5.0 に伸ばして重ねた)",
                        C_D, 12, True))
        c = p.done()
        c = _text(c, [
            (500, 566, "使用 %2d 枚 :  占有 %6d voxel = 真値の %.2f 倍"
             % (m, stats[m]["occ"], stats[m]["over"]), C_B, 16, True),
            (500, 592, "recall %.4f(真の voxel の取りこぼし %.2f %%)   IoU %.4f"
             % (stats[m]["recall"], 100 * (1 - stats[m]["recall"]), stats[m]["iou"]),
             C_D, 14, True),
            (500, 618, "1 枚では柱のように過大(%.2f 倍)。%d 枚で %.2f 倍まで縮むが、"
             % (stats[1]["over"], n_views, stats[n_views]["over"]), C_TEXT, 12, False),
            (500, 636, "L 字の凹みは何枚重ねても埋まらない — visual hull の原理的な限界。",
             C_TEXT, 12, False),
            (500, 656, "格子 %d³、真の占有 %d voxel(同じ格子に離散化した値)。"
             % (res, gt_n), C_DIM, 11, False),
        ])
        frames.append(c)

    info = _save_clip(frames, "wing3d_visual_hull", fps=3, thumb_index=n_views - 1, log=log)
    return {
        "name": "wing3d_visual_hull", "title": "visual hull ―― 影を重ねて形を削り出す",
        "ops": ["look_at", "synthesize_silhouette", "visual_hull"],
        "facts": {"res": res, "views": n_views, "gt_voxels": gt_n,
                  "per_view": {str(k): v for k, v in stats.items()}},
        "caption": (f"L 字の合成物体を {n_views} 方向から撮ったシルエットで `visual_hull` を"
                    f"彫る。1 枚では真の体積の **{stats[1]['over']:.2f} 倍**という柱状の"
                    f"塊だが、枚数を足すと {n_views} 枚で **{stats[n_views]['over']:.2f} 倍**"
                    f"(IoU {stats[n_views]['iou']:.3f})まで縮む。ただし L 字の凹みは"
                    "何枚重ねても埋まらない ―― これは実装の粗さではなく visual hull の"
                    "原理的な限界で、収束先が真値でないことが図から読める。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 10 — OBB と最大内接直方体                                                 #
# --------------------------------------------------------------------------- #
def ex_obb(log) -> dict:
    n = 88
    zz, yy, xx = _grid((n, n, n))
    ang = 30.0
    th = math.radians(ang)
    cs, sn = math.cos(th), math.sin(th)
    Y = yy - 44.0; X = xx - 44.0; Z = zz - 44.0
    u = cs * Y + sn * X
    v = -sn * Y + cs * X
    half = (20.0, 10.0, 8.0)                 # (u, v, z) 半幅 [voxel]
    box = (np.abs(u) <= half[0]) & (np.abs(v) <= half[1]) & (np.abs(Z) <= half[2])
    vol = box.astype(np.float64)

    pts = np.argwhere(box).astype(np.float64)          # (z, y, x)
    o = G("obb")(pts)
    ib = G("inner_box3")(vol)
    obb_vol = float(8.0 * np.prod(o["extents"]))
    ib_vol = float(ib["volume"])
    aabb = G("vol_bounding_box")(vol)
    aabb_vol = float((aabb[3] - aabb[0]) * (aabb[4] - aabb[1]) * (aabb[5] - aabb[2]))
    log(f"    voxels {int(box.sum()):,}  OBB extents {np.round(o['extents'], 3)} "
        f"vol {obb_vol:.0f}")
    log(f"    AABB {aabb} vol {aabb_vol:.0f}   inner_box3 size {ib['size']} "
        f"vol {ib_vol:.0f}")
    log(f"    OBB axes (columns)\n{np.round(o['axes'], 4)}")

    rng = np.random.default_rng(SEED)
    sel = np.sort(rng.choice(pts.shape[0], size=min(12000, pts.shape[0]), replace=False))
    shown = pts[sel]

    obb_corners = np.asarray(o["corners"], np.float64)[:, [2, 1, 0]]     # -> (x,y,z)
    ib_min = np.asarray(ib["min"], np.float64); ib_max = np.asarray(ib["max"], np.float64)
    ib_c = (ib_min + ib_max) / 2.0
    ib_h = (ib_max - ib_min) / 2.0
    ib_corners = _box_corners(ib_c[[2, 1, 0]], ib_h[[2, 1, 0]])
    aabb_c = np.array([(aabb[0] + aabb[3]) / 2, (aabb[1] + aabb[4]) / 2,
                       (aabb[2] + aabb[5]) / 2])
    aabb_h = np.array([(aabb[3] - aabb[0]) / 2, (aabb[4] - aabb[1]) / 2,
                       (aabb[5] - aabb[2]) / 2])
    aabb_corners = _box_corners(aabb_c[[2, 1, 0]], aabb_h[[2, 1, 0]])

    # OBB の corners が本当に 8 隅の順番で並んでいるか(辺の長さ)を実測
    def _wire_edges(cs8):
        d = np.linalg.norm(cs8[:, None, :] - cs8[None, :, :], axis=-1)
        # 各頂点から近い 3 本を辺とみなす
        e = set()
        for i in range(8):
            for j in np.argsort(d[i])[1:4]:
                e.add((min(i, int(j)), max(i, int(j))))
        return sorted(e)
    obb_edges = _wire_edges(obb_corners)

    W, H = 1120, 700
    pw, ph = 700, 440
    center = np.array([44.0, 44.0, 44.0])
    nf = 48
    frames = []
    for k in range(nf):
        R = _rot(360.0 * k / nf, 20.0)
        c = _canvas(W, H)
        c = _header(c, "外から抱く箱と、中に入る箱 ―― OBB と最大内接直方体",
                    f"z 軸まわりに {ang:.0f}° 傾けた合成直方体(半幅 {half[0]:.0f} x "
                    f"{half[1]:.0f} x {half[2]:.0f} voxel)。3 つの箱を同時に描いて 1 周。")
        px, py = 18, 84
        _fill(c, px, py, px + pw, py + ph, C_PANEL)
        sub = c[py:py + ph, px:px + pw]
        scale = 5.4
        u2, v2, d2 = _project(shown[:, [2, 1, 0]], R, scale, pw / 2, ph / 2,
                              center[[2, 1, 0]])
        _splat(sub, u2, v2, d2, (0.28, 0.31, 0.36), radius=1, shade=0.5)
        c = _draw_wire(c, aabb_corners, _BOX_EDGES, R, scale, px + pw / 2, py + ph / 2,
                       center[[2, 1, 0]], C_C, width=1)
        c = _draw_wire(c, obb_corners, obb_edges, R, scale, px + pw / 2, py + ph / 2,
                       center[[2, 1, 0]], C_B, width=2)
        c = _draw_wire(c, ib_corners, _BOX_EDGES, R, scale, px + pw / 2, py + ph / 2,
                       center[[2, 1, 0]], C_D, width=2)
        c = imagedraw.draw_polyline(
            c, [(px, py), (px + pw - 1, py), (px + pw - 1, py + ph - 1), (px, py + ph - 1)],
            color=C_RULE, width=1, closed=True)
        c = _axis_gizmo(c, R, px + 50, py + ph - 50, size=32)
        c = _text(c, [
            (px + 10, py + 10, "灰 = 物体の voxel", C_DIM, 12, True),
            (px + 10, py + 28, "紫 = AABB(軸平行の外接箱)", C_C, 12, True),
            (px + 10, py + 46, "アンバー = obb(PCA の向き付き外接箱)", C_B, 12, True),
            (px + 10, py + 64, "ミント = inner_box3(軸平行の最大内接箱)", C_D, 12, True),
        ])
        rows = [
            ("物体の voxel 数", "%d" % int(box.sum()), C_TEXT),
            ("AABB 体積", "%.0f voxel  (%.2f 倍)" % (aabb_vol, aabb_vol / int(box.sum())), C_C),
            ("obb 体積", "%.0f voxel  (%.2f 倍)" % (obb_vol, obb_vol / int(box.sum())), C_B),
            ("inner_box3 体積", "%.0f voxel  (%.2f 倍)" % (ib_vol, ib_vol / int(box.sum())), C_D),
            ("obb の半幅", "%.2f, %.2f, %.2f voxel" % tuple(o["extents"]), C_B),
            ("真の半幅", "%.1f, %.1f, %.1f voxel" % half, C_DIM),
            ("inner_box3 の全幅", "%.0f x %.0f x %.0f voxel (d,r,c)" % tuple(ib["size"]), C_D),
            ("inner_box3 の中心", "(%.1f, %.1f, %.1f)" % (ib["cd"], ib["cr"], ib["cc"]), C_D),
        ]
        items = [(760, 90, "実測", C_DIM, 13, False)]
        for i, (kk, vv, col) in enumerate(rows):
            items.append((760, 116 + i * 26, kk, C_DIM, 12, False))
            items.append((760, 133 + i * 26, vv, col, 13, True))
        c = _text(c, items)
        c = _text(c, [
            (18, 548, "AABB は %.2f 倍まで膨らむのに、向きを合わせた obb は %.2f 倍まで縮む。"
             % (aabb_vol / int(box.sum()), obb_vol / int(box.sum())), C_TEXT, 14, True),
            (18, 574, "obb の体積が voxel 数より小さいのは、点群が voxel の "
                      "「中心」の集まりで、箱はその外接だから(半 voxel 分の縁が入らない)。",
             C_DIM, 12, False),
            (18, 596, "inner_box3 は「どの深さ区間でも全スライスの論理積の中に入る」"
                      "厳密な最大内接箱なので、傾いた物体では %.2f 倍まで痩せる。"
             % (ib_vol / int(box.sum())), C_DIM, 12, False),
            (18, 620, "ロボットが掴み幅を決めるときは obb、"
                      "中に部品を通せるかを見るときは inner_box3。", C_TEXT, 13, True),
        ])
        c = _footer(c, "使用 op: obb / inner_box3 / vol_bounding_box  — 合成データ")
        frames.append(c)

    info = _save_clip(frames, "wing3d_obb_innerbox", fps=14, thumb_index=10, log=log)
    return {
        "name": "wing3d_obb_innerbox", "title": "外から抱く箱(OBB)と中に入る箱(inner_box3)",
        "ops": ["obb", "inner_box3", "vol_bounding_box"],
        "facts": {"object_voxels": int(box.sum()), "rotation_deg": ang,
                  "true_half_extents": list(half),
                  "obb_extents": [float(x) for x in o["extents"]],
                  "obb_center": [float(x) for x in o["center"]],
                  "obb_axes": np.asarray(o["axes"]).tolist(),
                  "obb_volume": obb_vol, "aabb": list(aabb), "aabb_volume": aabb_vol,
                  "inner_box_size": [float(x) for x in ib["size"]],
                  "inner_box_volume": ib_vol},
        "caption": (f"z 軸まわりに 30° 傾けた合成直方体({int(box.sum()):,} voxel)に 3 つの箱を"
                    f"同時に描いてターンテーブルで 1 周させた。軸平行の AABB は voxel 数の "
                    f"**{aabb_vol / int(box.sum()):.2f} 倍**まで膨らむのに、`obb`(PCA で向きを"
                    f"合わせた外接箱)は **{obb_vol / int(box.sum()):.2f} 倍**まで縮み、半幅は "
                    f"{o['extents'][0]:.2f} / {o['extents'][1]:.2f} / {o['extents'][2]:.2f} voxel "
                    f"(真値 {half[0]:.0f} / {half[1]:.0f} / {half[2]:.0f})とほぼ真値。"
                    "1 倍を切るのは、点群が voxel の「中心」の集まりでその外接を測っているから"
                    "(縁の半 voxel が入らない)。逆に `inner_box3` の最大内接箱は "
                    f"**{ib_vol / int(box.sum()):.2f} 倍**まで痩せる。掴み幅を決めるなら OBB、"
                    "中を部品が通るかを見るなら内接箱。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 11 — 点群レジストレーション(ICP / GICP)                                   #
# --------------------------------------------------------------------------- #
def ex_icp(log) -> dict:
    rng = np.random.default_rng(SEED)
    n = 2600
    # 表面点群(だ円体 + 突起) — 対称すぎると ICP が回りやすいので突起を付ける
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    target = d * np.array([26.0, 17.0, 13.0])
    bump = rng.normal(size=(500, 3))
    bump /= np.linalg.norm(bump, axis=1, keepdims=True)
    target = np.vstack([target, bump * 7.0 + np.array([20.0, 12.0, 6.0])])

    ang_deg = 22.0
    a = math.radians(ang_deg)
    Rt = np.array([[math.cos(a), -math.sin(a), 0.0],
                   [math.sin(a), math.cos(a), 0.0],
                   [0.0, 0.0, 1.0]])
    tt = np.array([6.0, -4.0, 3.0])
    source = target @ Rt.T + tt

    R_icp, t_icp, info_icp = G("icp_point2point_3d")(source, target, iters=60, tol=1e-10)
    R_icp = np.asarray(R_icp, np.float64); t_icp = np.asarray(t_icp, np.float64)
    hist = [float(x) for x in info_icp["rmse_history"]]
    g = G("gicp")(source, target, max_iter=40)
    log(f"    ICP  iters {info_icp['iters']} converged {info_icp['converged']} "
        f"rmse {info_icp['rmse']:.3e} inliers {info_icp['inliers']}")
    log(f"    GICP iterations {g['iterations']} rmse {g['rmse']:.3e}")

    # 復元した角度・並進の誤差(真値は Rt, tt の逆変換)
    R_true_inv = Rt.T
    t_true_inv = -Rt.T @ tt
    ang_err = math.degrees(math.acos(
        np.clip((np.trace(R_icp @ R_true_inv.T) - 1.0) / 2.0, -1.0, 1.0)))
    t_err = float(np.linalg.norm(t_icp - t_true_inv))
    log(f"    recovered angle err {ang_err:.4e} deg   translation err {t_err:.4e}")

    # 反復ごとの姿勢を自分で追う必要があるので、iters を段階的に増やして撮る
    steps = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 25, 30, 40, 60]
    poses = {}
    for s in steps:
        if s == 0:
            poses[s] = (np.eye(3), np.zeros(3), hist[0])
        else:
            Rk, tk, ik = G("icp_point2point_3d")(source, target, iters=s, tol=0.0)
            poses[s] = (np.asarray(Rk, np.float64), np.asarray(tk, np.float64),
                        float(ik["rmse"]))

    W, H = 1120, 660
    pw, ph = 620, 430
    frames = []
    for s in steps:
        Rk, tk, rk = poses[s]
        moved = source @ Rk.T + tk
        R = _rot(28.0, 22.0)
        c = _canvas(W, H)
        c = _header(c, "点群レジストレーション ―― ずれた 2 つの点群を重ねる",
                    f"合成した表面点群({target.shape[0]} 点)を "
                    f"{ang_deg:.0f}° 回して平行移動したものが「動く側」。"
                    f"ICP の反復 {s:2d} 回。")
        px, py = 18, 88
        _fill(c, px, py, px + pw, py + ph, C_PANEL)
        sub = c[py:py + ph, px:px + pw]
        scale = 5.6
        cen = np.zeros(3)
        u, v, dd = _project(target, R, scale, pw / 2, ph / 2, cen)
        _splat(sub, u, v, dd, C_A, radius=1, shade=0.5)
        u, v, dd = _project(moved, R, scale, pw / 2, ph / 2, cen)
        _splat(sub, u, v, dd, C_B, radius=1, shade=0.5)
        c = imagedraw.draw_polyline(
            c, [(px, py), (px + pw - 1, py), (px + pw - 1, py + ph - 1), (px, py + ph - 1)],
            color=C_RULE, width=1, closed=True)
        c = _axis_gizmo(c, R, px + 46, py + ph - 46, size=30)
        c = _text(c, [(px + 10, py + 10, "シアン = 固定側(target)", C_A, 13, True),
                      (px + 10, py + 30, "アンバー = 動く側(source を現在の姿勢で変換)",
                       C_B, 13, True),
                      (px, py + ph + 6, "同じ視点から見た 2 つの点群。重なるほど"
                                        "アンバーがシアンを覆い隠す。", C_TEXT, 12, True)])

        p = Plot(c, 730, 130, 360, 220, (0, 60), (1e-15, 20.0),
                 xlabel="ICP 反復 ->", ylabel="対応点 RMSE",
                 xticks=[0, 10, 20, 30, 40, 50, 60],
                 yticks=[1e-14, 1e-10, 1e-6, 1e-2, 10],
                 xfmt="%d", yfmt="%.0e", logy=True)
        p.series(range(len(hist)), [max(h, 1e-15) for h in hist], C_B, width=2)
        p.marker(min(s, len(hist) - 1), max(hist[min(s, len(hist) - 1)], 1e-15), C_D, size=6)
        c = p.done()
        c = _text(c, [
            (730, 380, "反復 %d 回時点の RMSE" % s, C_DIM, 12, False),
            (730, 400, "%.3e" % max(rk, 0.0), C_B, 24, True),
            (730, 440, "収束後(ICP)", C_DIM, 12, False),
            (730, 458, "反復 %d 回 / RMSE %.2e / インライア %d 点"
             % (info_icp["iters"], info_icp["rmse"], info_icp["inliers"]), C_A, 13, True),
            (730, 482, "gicp: 反復 %d 回 / RMSE %.2e" % (g["iterations"], g["rmse"]),
             C_D, 13, True),
            (730, 512, "復元した姿勢の誤差(真値との差)", C_DIM, 12, False),
            (730, 532, "回転 %.2e 度   並進 %.2e" % (ang_err, t_err), C_TEXT, 13, True),
            (730, 560, "GICP は面の共分散を使うので %d 回で終わる"
             % g["iterations"], C_DIM, 12, False),
            (730, 578, "(点対点 ICP は %d 回)。同じ答えに、違う速さで着く。"
             % info_icp["iters"], C_DIM, 12, False),
        ])
        c = _footer(c, "使用 op: icp_point2point_3d / gicp  — 合成データ, seed 固定")
        frames.append(c)

    info = _save_clip(frames, "wing3d_icp_registration", fps=4,
                      thumb_index=len(steps) - 1, log=log)
    return {
        "name": "wing3d_icp_registration",
        "title": "点群レジストレーション ―― ICP %d 回 / GICP %d 回" % (
            info_icp["iters"], g["iterations"]),
        "ops": ["icp_point2point_3d", "gicp"],
        "facts": {"points": int(target.shape[0]), "applied_rotation_deg": ang_deg,
                  "applied_translation": tt.tolist(),
                  "icp_iters": int(info_icp["iters"]), "icp_rmse": float(info_icp["rmse"]),
                  "icp_inliers": int(info_icp["inliers"]),
                  "icp_rmse_history": hist,
                  "gicp_iterations": int(g["iterations"]), "gicp_rmse": float(g["rmse"]),
                  "rotation_error_deg": ang_err, "translation_error": t_err},
        "caption": (f"合成した表面点群({target.shape[0]} 点)を {ang_deg:.0f}° 回して平行移動した"
                    f"ものを、`icp_point2point_3d` で戻す。初期 RMSE {hist[0]:.3f} が "
                    f"**{info_icp['iters']} 反復**で {info_icp['rmse']:.1e} まで落ち、"
                    f"復元した姿勢の誤差は回転 {ang_err:.1e} 度・並進 {t_err:.1e}。"
                    f"面の共分散を使う `gicp` は同じ答えに **{g['iterations']} 反復**で着く。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 12 — 異方性ボクセル                                                       #
# --------------------------------------------------------------------------- #
def ex_anisotropic(log) -> dict:
    sp = (1.5, 0.4, 0.4)                     # z だけ粗い(実際の CT でよくある)
    D, H_, W_ = 44, 128, 128
    semi_mm = (18.0, 16.0, 16.0)
    rz = semi_mm[0] / sp[0]; ry = semi_mm[1] / sp[1]; rx = semi_mm[2] / sp[2]
    zz, yy, xx = _grid((D, H_, W_))
    ell = (((zz - 22.) / rz) ** 2 + ((yy - 64.) / ry) ** 2
           + ((xx - 64.) / rx) ** 2) <= 1.0
    vol = ell.astype(np.float64)
    lab, nlab = G("vol_label")(vol)
    lab = np.asarray(lab)
    pr_sp = G("vol_region_props")(lab, spacing=sp)[0]
    pr_no = G("vol_region_props")(lab)[0]
    truth = 4.0 / 3.0 * math.pi * semi_mm[0] * semi_mm[1] * semi_mm[2]
    err_sp = 100 * (pr_sp["volume"] - truth) / truth
    err_no = 100 * (pr_no["volume"] - truth) / truth
    log(f"    truth {truth:.1f} mm^3")
    log(f"    with spacing {pr_sp['volume']:.1f} ({err_sp:+.2f} %)  "
        f"surface {pr_sp['surface_area']:.1f} mm^2  sphericity {pr_sp['sphericity']:.4f}")
    log(f"    ignoring spacing {pr_no['volume']:.1f} ({err_no:+.2f} %)  "
        f"= {pr_no['volume'] / pr_sp['volume']:.3f}x")

    bp_sp = np.asarray(G("vol_boundary_points")(vol, spacing=sp))
    bp_no = np.asarray(G("vol_boundary_points")(vol))
    ext_sp = bp_sp.max(0) - bp_sp.min(0)
    ext_no = bp_no.max(0) - bp_no.min(0)
    log(f"    boundary extent with spacing {np.round(ext_sp, 2)} mm  "
        f"without {np.round(ext_no, 2)} voxel")

    W, H = 1120, 700
    c = _canvas(W, H)
    c = _header(c, "異方性ボクセル ―― z だけ粗い CT で spacing を忘れると",
                f"合成だ円体(真の半径 {semi_mm[0]:.0f} x {semi_mm[1]:.0f} x "
                f"{semi_mm[2]:.0f} mm)を spacing ({sp[0]}, {sp[1]}, {sp[2]}) mm/voxel で"
                "サンプリングした。")
    pw = 330
    from PIL import Image
    # 左: 添字空間のまま(= spacing を無視した見え方)
    mid = vol[:, :, 64]
    im = Image.fromarray(_to_u8(_cmap(mid, "gray"))).resize((pw, pw), Image.NEAREST)
    _paste(c, np.asarray(im, np.float64) / 255.0, 18, 96)
    c = imagedraw.draw_polyline(c, [(18, 96), (18 + pw - 1, 96), (18 + pw - 1, 96 + pw - 1),
                                    (18, 96 + pw - 1)], color=C_E, width=2, closed=True)
    # 右: spacing を効かせた見え方(z を 1.5/0.4 = 3.75 倍に伸ばす)
    stretch = sp[0] / sp[1]
    hh = int(round(pw * (D * stretch) / H_))
    im2 = Image.fromarray(_to_u8(_cmap(mid, "gray"))).resize((pw, hh), Image.NEAREST)
    _paste(c, np.zeros((pw, pw, 3)) + np.asarray(C_PANEL), 386, 96)
    _paste(c, np.asarray(im2, np.float64) / 255.0, 386, 96 + max(0, (pw - hh) // 2))
    c = imagedraw.draw_polyline(c, [(386, 96), (386 + pw - 1, 96), (386 + pw - 1, 96 + pw - 1),
                                    (386, 96 + pw - 1)], color=C_D, width=2, closed=True)
    c = _text(c, [
        (18, 96 + pw + 8, "添字のまま表示(spacing を無視)", C_E, 13, True),
        (18, 96 + pw + 28, "z 方向に潰れて見える。断面は x = 64。", C_DIM, 12, False),
        (386, 96 + pw + 8, "spacing を効かせて表示(z を %.2f 倍)" % stretch, C_D, 13, True),
        (386, 96 + pw + 28, "これが本当の形。半径 %.0f : %.0f mm。"
         % (semi_mm[0], semi_mm[1]), C_DIM, 12, False),
    ])

    rows = [
        ("真値(解析解)", "%10.1f mm^3" % truth, C_TEXT),
        ("spacing あり vol_region_props", "%10.1f mm^3  (%+.2f %%)" % (pr_sp["volume"], err_sp), C_D),
        ("spacing なし(voxel を 1 mm 立方と誤解)",
         "%10.1f      (%+.1f %%)" % (pr_no["volume"], err_no), C_E),
        ("倍率", "%.3f 倍  = 1 / (%.1f x %.1f x %.1f)"
         % (pr_no["volume"] / pr_sp["volume"], sp[0], sp[1], sp[2]), C_B),
        ("", "", C_DIM),
        ("表面積 spacing あり", "%10.1f mm^2" % pr_sp["surface_area"], C_D),
        ("表面積 spacing なし", "%10.1f" % pr_no["surface_area"], C_E),
        ("球形度 sphericity", "%.4f (spacing あり) / %.4f (なし)"
         % (pr_sp["sphericity"], pr_no["sphericity"]), C_B),
        ("", "", C_DIM),
        ("境界点の広がり spacing あり", "%.1f x %.1f x %.1f mm" % tuple(ext_sp), C_D),
        ("境界点の広がり spacing なし", "%.0f x %.0f x %.0f voxel" % tuple(ext_no), C_E),
    ]
    items = [(740, 100, "同じ 1 つの領域を測った結果", C_DIM, 13, False)]
    for i, (k, v, col) in enumerate(rows):
        if not k:
            continue
        items.append((740, 128 + i * 34, k, C_DIM, 11, False))
        items.append((740, 145 + i * 34, v, col, 13, True))
    c = _text(c, items)

    c = _bars(c, 18, 500, 690, 118, [truth, pr_sp["volume"], pr_no["volume"]],
              ["真値", "spacing あり", "spacing なし"], [C_TEXT, C_D, C_E],
              fmt="%.0f", title="体積(mm³ として読んだ値)")
    c = _text(c, [
        (18, 636, "spacing を渡さないと体積は %.2f 倍(%+.0f %%)に化ける。"
         % (pr_no["volume"] / pr_sp["volume"], err_no), C_E, 15, True),
        (18, 660, "エラーは出ない。もっともらしい数字が返るだけ ―― "
                  "3D 計測でいちばん静かな事故。", C_TEXT, 13, True),
    ])
    c = _footer(c, "使用 op: vol_label / vol_region_props / vol_boundary_points  "
                   "— 合成データ", y_off=16)
    info = _save_png(c, "wing3d_anisotropic_voxel", log)
    return {
        "name": "wing3d_anisotropic_voxel",
        "title": "異方性ボクセル ―― spacing を忘れると体積が %.2f 倍" % (
            pr_no["volume"] / pr_sp["volume"]),
        "ops": ["vol_label", "vol_region_props", "vol_boundary_points"],
        "facts": {"spacing_mm": list(sp), "semi_axes_mm": list(semi_mm),
                  "truth_mm3": truth, "volume_with_spacing": float(pr_sp["volume"]),
                  "volume_without_spacing": float(pr_no["volume"]),
                  "err_with_spacing_pct": err_sp, "err_without_spacing_pct": err_no,
                  "ratio": float(pr_no["volume"] / pr_sp["volume"]),
                  "surface_with_spacing": float(pr_sp["surface_area"]),
                  "surface_without_spacing": float(pr_no["surface_area"]),
                  "sphericity_with": float(pr_sp["sphericity"]),
                  "sphericity_without": float(pr_no["sphericity"]),
                  "extent_with_spacing_mm": ext_sp.tolist(),
                  "extent_without_spacing_voxel": ext_no.tolist()},
        "caption": (f"z だけ粗い spacing ({sp[0]}, {sp[1]}, {sp[2]}) mm/voxel でサンプリング"
                    f"した合成だ円体(真の体積 {truth:.1f} mm³)。`vol_region_props` に "
                    f"spacing を渡せば {pr_sp['volume']:.1f} mm³(**{err_sp:+.2f} %**)だが、"
                    f"渡し忘れると {pr_no['volume']:.0f}(**{err_no:+.0f} %**、"
                    f"{pr_no['volume'] / pr_sp['volume']:.2f} 倍)になる。例外は飛ばない。"
                    "もっともらしい数字が静かに返るだけ、というのがこの展示の要点。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 13 — MIP ターンテーブル(合成 CT を X 線のように)                          #
# --------------------------------------------------------------------------- #
def ex_mip(log) -> dict:
    n = 96
    hu = _ct_phantom(n)
    bone = np.asarray(G("vol_window_level")(hu, 500.0, 2000.0))
    soft = np.asarray(G("vol_window_level")(hu, 40.0, 400.0))
    nf = 36
    mips, xrays = [], []
    t0 = time.perf_counter()
    for k in range(nf):
        az = 360.0 * k / nf
        mips.append(np.asarray(G("render_volume_projection")(bone, azimuth=az,
                                                             elevation=12.0, mode="mip")))
        xrays.append(np.asarray(G("render_volume_projection")(soft, azimuth=az,
                                                              elevation=12.0, mode="xray")))
    dt = time.perf_counter() - t0
    mip_hi = float(max(m.max() for m in mips))
    xr_hi = float(max(x.max() for x in xrays))
    log(f"    render_volume_projection x{2 * nf} in {dt:.2f} s "
        f"({1e3 * dt / (2 * nf):.0f} ms/frame)   mip max {mip_hi:.3f}  xray max {xr_hi:.2f}")

    W, H = 1120, 640
    pw = 430
    frames = []
    from PIL import Image
    for k in range(nf):
        az = 360.0 * k / nf
        c = _canvas(W, H)
        c = _header(c, "voxel を任意視点から投影する ―― MIP と X 線(減衰積算)",
                    f"合成 CT ボリューム({n}³)を 1 周させながら 2 通りに投影。"
                    f"仰角 12°、方位 {az:5.1f}°。")
        for i, (title, img, hi, cmap_name, col, note) in enumerate((
                ("mode='mip'(最大値投影・骨窓)", mips[k], mip_hi, "gray", C_B,
                 "光線上の最大値だけを拾う。骨が浮く。"),
                ("mode='xray'(減衰積算・軟部窓)", xrays[k], xr_hi, "inferno", C_A,
                 "光線上を足し合わせる。厚みが出る。"))):
            px = 18 + i * (pw + 34)
            # 全フレーム共通の上限で正規化 = 回転中に明るさがちらつかない
            im = Image.fromarray(_to_u8(_cmap(np.clip(img / hi, 0, 1), cmap_name))).resize(
                (pw, pw), Image.NEAREST)
            _paste(c, np.asarray(im, np.float64) / 255.0, px, 92)
            c = imagedraw.draw_polyline(
                c, [(px, 92), (px + pw - 1, 92), (px + pw - 1, 92 + pw - 1), (px, 92 + pw - 1)],
                color=col, width=2, closed=True)
            c = _colorbar(c, px, 92 + pw + 12, 200, 12, cmap_name,
                          "0", "%.2f" % hi, "")
            c = _text(c, [(px, 92 + pw + 46, title, col, 14, True),
                          (px, 92 + pw + 68, note, C_DIM, 12, False)])
        c = _text(c, [
            (930, 100, "方位角", C_DIM, 12, False),
            (930, 118, "%5.1f deg" % az, C_TEXT, 22, True),
            (930, 152, "仰角", C_DIM, 12, False),
            (930, 170, " 12.0 deg", C_TEXT, 22, True),
            (930, 210, "ボリューム", C_DIM, 12, False),
            (930, 228, "%d x %d x %d" % (n, n, n), C_TEXT, 15, True),
            (930, 254, "投影 %d 枚 / %.1f s" % (2 * nf, dt), C_TEXT, 13, False),
            (930, 274, "= %.0f ms / 枚" % (1e3 * dt / (2 * nf)), C_DIM, 12, False),
            (930, 310, "正規化の上限は", C_DIM, 12, False),
            (930, 328, "全フレーム共通", C_TEXT, 13, True),
            (930, 346, "(1 枚ごとに正規化", C_DIM, 11, False),
            (930, 362, "すると回転中に", C_DIM, 11, False),
            (930, 378, "明るさがちらつく)", C_DIM, 11, False),
        ])
        c = _footer(c, "使用 op: vol_window_level / render_volume_projection  "
                       "— 合成 HU データ(実在の患者・スキャンではありません)")
        frames.append(c)

    info = _save_clip(frames, "wing3d_mip_turntable", fps=12, thumb_index=5, log=log)
    return {
        "name": "wing3d_mip_turntable", "title": "MIP と X 線投影のターンテーブル",
        "ops": ["vol_window_level", "render_volume_projection"],
        "facts": {"volume": [n, n, n], "frames": nf, "elevation_deg": 12.0,
                  "render_seconds_total": dt,
                  "ms_per_projection": 1e3 * dt / (2 * nf),
                  "mip_max": mip_hi, "xray_max": xr_hi},
        "caption": (f"合成 CT ボリューム({n}³)を `render_volume_projection` で 1 周させた。"
                    "左は最大値投影(MIP、骨窓)で光線上の最大値だけを拾うので骨が浮き、"
                    "右は減衰積算(X 線)で厚みが出る。投影 "
                    f"{2 * nf} 枚を {dt:.1f} 秒(**{1e3 * dt / (2 * nf):.0f} ms/枚**)。"
                    "正規化の上限は全フレーム共通にしてある ―― 1 枚ごとに正規化すると"
                    "回転中に明るさがちらついて、形の変化と見分けがつかなくなる。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 14 — 距離変換で「中心線」と「いちばん太いところ」                          #
# --------------------------------------------------------------------------- #
def ex_distance(log) -> dict:
    n = 112
    sp = (0.5, 0.5, 0.5)
    # 枝は必ず主管の**軸上**から生やす(軸から外して置くと連結しない別々の管になる)
    parts = [((16, 56, 30), (96, 56, 30), 9.0),
             ((44, 56, 30), (44, 20, 78), 6.0),
             ((76, 56, 30), (76, 92, 80), 5.0)]
    obj = np.zeros((n, n, n), bool)
    for p0, p1, r in parts:
        obj |= _capsule((n, n, n), p0, p1, r)
    vol = obj.astype(np.float64)
    dt = np.asarray(G("vol_distance_transform")(vol, spacing=sp))
    dt_vox = np.asarray(G("vol_distance_transform")(vol))
    max_mm = float(dt.max())
    arg = np.unravel_index(int(np.argmax(dt)), dt.shape)
    log(f"    max inscribed radius {max_mm:.4f} mm at (z,y,x) = {arg}  "
        f"(voxel units {dt_vox.max():.4f})")
    log(f"    truth: 太い管の半径 {parts[0][2] * sp[0]:.3f} mm")

    W, H = 1120, 660
    pw = 300
    frames = []
    from PIL import Image
    # 往復する送り。同じ z を 2 コマ続けて出さない(GIF が畳んでコマ落ちするため)
    z_lo, z_hi = 10, n - 10
    up = list(range(z_lo, z_hi + 1, 4))
    zs = up + up[-2:0:-1]
    nf = len(zs)
    for z in zs:
        c = _canvas(W, H)
        c = _header(c, "距離変換 ―― 「ふちから何 mm 離れているか」で中心線と太さが出る",
                    f"合成した 3 本の管(spacing 0.5 mm/voxel)を輪切りで送る。"
                    f"z = {z:3d} / {n - 1}")
        sl_bin = vol[z]
        sl_dt = dt[z]
        panels = [("二値ボリューム", _cmap(sl_bin, "gray"), C_TEXT),
                  ("vol_distance_transform(mm)", _cmap(_norm01(sl_dt, 0, max_mm),
                                                       "rainbow"), C_B),
                  ("最大内接球の半径 = 局所の太さ", None, C_D)]
        for i, (title, img, col) in enumerate(panels):
            px = 18 + i * (pw + 16)
            if img is None:
                # 等高線(0.5 mm ごと)を線で描く = 距離が「読める」表示
                base = _cmap(sl_bin * 0.25, "gray")
                im = Image.fromarray(_to_u8(base)).resize((pw, pw), Image.NEAREST)
                _paste(c, np.asarray(im, np.float64) / 255.0, px, 88)
                sc = pw / n
                levels = np.arange(0.5, max_mm, 0.5)
                for li, lv in enumerate(levels):
                    band = (sl_dt >= lv) & (sl_dt < lv + 0.5 * 0.28)
                    ys, xs = np.nonzero(band)
                    if ys.size == 0:
                        continue
                    colr = _cmap(np.array([lv / max_mm]), "rainbow")[0]
                    sub = c[88:88 + pw, px:px + pw]
                    uu = np.clip(np.rint(xs * sc).astype(int), 0, pw - 1)
                    vv = np.clip(np.rint(ys * sc).astype(int), 0, pw - 1)
                    sub[vv, uu, :] = colr
                c = imagedraw.draw_polyline(
                    c, [(px, 88), (px + pw - 1, 88), (px + pw - 1, 88 + pw - 1),
                        (px, 88 + pw - 1)], color=col, width=2, closed=True)
            else:
                im = Image.fromarray(_to_u8(img)).resize((pw, pw), Image.NEAREST)
                _paste(c, np.asarray(im, np.float64) / 255.0, px, 88)
                c = imagedraw.draw_polyline(
                    c, [(px, 88), (px + pw - 1, 88), (px + pw - 1, 88 + pw - 1),
                        (px, 88 + pw - 1)], color=col, width=2, closed=True)
            c = _text(c, [(px, 88 + pw + 6, title, col, 12, True)])
        c = _colorbar(c, 334, 88 + pw + 30, 300, 14, "rainbow",
                      "0.0 mm", "%.2f mm" % max_mm,
                      "ふちからの距離(vol_distance_transform, spacing 込み)")

        # スライスごとの最大距離のグラフ(いま見ている z に印)
        per_z = dt.max(axis=(1, 2))
        p = Plot(c, 90, 470, W - 130, 130, (0, n - 1), (0, max_mm * 1.1),
                 xlabel="z(スライス番号)->", ylabel="そのスライスの最大内接半径 [mm]",
                 xticks=[0, 20, 40, 60, 80, 100], yticks=[0, 1, 2, 3, 4],
                 xfmt="%d", yfmt="%.0f")
        p.series(range(n), per_z, C_B, width=2)
        p.marker(z, per_z[z], C_D, size=7)
        p.hline(parts[0][2] * sp[0], C_A, width=1)
        p.items.append((p.px(2), p.py(parts[0][2] * sp[0]) - 16,
                        "太い管の真の半径 %.2f mm" % (parts[0][2] * sp[0]), C_A, 11, True))
        p.items.append((p.px(z) + 6, p.py(per_z[z]) - 18, "z=%d: %.3f mm" % (z, per_z[z]),
                        C_D, 12, True))
        c = p.done()
        c = _text(c, [
            (740, 96, "全体の最大内接半径", C_DIM, 12, False),
            (740, 116, "%.4f mm" % max_mm, C_B, 26, True),
            (740, 152, "位置 (z,y,x) = (%d, %d, %d)" % arg, C_TEXT, 13, False),
            (740, 174, "voxel 単位なら %.4f voxel" % dt_vox.max(), C_DIM, 12, False),
            (740, 198, "太い管の真の半径 %.3f mm(半径 %.0f voxel x %.1f mm)"
             % (parts[0][2] * sp[0], parts[0][2], sp[0]), C_A, 12, False),
            (740, 220, "差 %+.4f mm — 離散格子で「ふち」が半 voxel 内側に"
             % (max_mm - parts[0][2] * sp[0]), C_DIM, 12, False),
            (740, 238, "来るぶん。消さずに出しておく。", C_DIM, 12, False),
        ])
        c = _footer(c, "使用 op: vol_distance_transform  — 合成データ, spacing 0.5 mm/voxel")
        frames.append(c)

    info = _save_clip(frames, "wing3d_distance_transform", fps=12, thumb_index=nf // 4,
                      log=log)
    return {
        "name": "wing3d_distance_transform",
        "title": "距離変換で局所の太さを測る(最大内接半径 %.3f mm)" % max_mm,
        "ops": ["vol_distance_transform"],
        "facts": {"spacing_mm": list(sp), "max_radius_mm": max_mm,
                  "max_radius_voxel": float(dt_vox.max()),
                  "argmax_zyx": [int(v) for v in arg],
                  "truth_radius_mm": parts[0][2] * sp[0],
                  "radius_err_mm": max_mm - parts[0][2] * sp[0]},
        "caption": ("合成した 3 本の管に `vol_distance_transform` を掛けると、"
                    "各ボクセルが「ふちから何 mm 離れているか」になる。その最大値が"
                    f"最大内接球の半径 = 局所の太さで、実測 **{max_mm:.4f} mm**"
                    f"(真値 {parts[0][2] * sp[0]:.3f} mm、差 "
                    f"{max_mm - parts[0][2] * sp[0]:+.4f} mm — 離散格子でふちが半 voxel "
                    "内側に来るぶん)。虹の等高線は 0.5 mm ごと。"),
        **info}


# --------------------------------------------------------------------------- #
# 断層まわりの共通部品 — 断面 1 枚を「読める形」で置く                             #
# --------------------------------------------------------------------------- #
def _slice_panel(c, sl, x, y, size, cmap_name="gray", lo=None, hi=None,
                 border=C_RULE, nearest=True):
    """スライス 1 枚を size x size に置いて枠を付ける。戻り (canvas, 画素/voxel)。"""
    from PIL import Image
    img = _cmap(_norm01(sl, lo, hi) if (lo is not None or hi is not None)
                else np.clip(sl, 0, 1), cmap_name)
    im = Image.fromarray(_to_u8(img)).resize(
        (size, size), Image.NEAREST if nearest else Image.BILINEAR)
    _paste(c, np.asarray(im, np.float64) / 255.0, x, y)
    c = imagedraw.draw_polyline(
        c, [(x, y), (x + size - 1, y), (x + size - 1, y + size - 1), (x, y + size - 1)],
        color=border, width=1, closed=True)
    return c, size / sl.shape[0]


def _crosshair(c, x, y, size, u, v, color, gap=9):
    """クロスヘア(中心に隙間を空けるので、指している画素そのものは隠れない)。"""
    cxp, cyp = x + u, y + v
    c = imagedraw.draw_line(c, (x, cyp), (cxp - gap, cyp), color=color, width=1)
    c = imagedraw.draw_line(c, (cxp + gap, cyp), (x + size - 1, cyp), color=color, width=1)
    c = imagedraw.draw_line(c, (cxp, y), (cxp, cyp - gap), color=color, width=1)
    c = imagedraw.draw_line(c, (cxp, cyp + gap), (cxp, y + size - 1), color=color, width=1)
    return c


def _ruler(c, x, y, w, h, frac, color, label_lo, label_hi, cur_label):
    """位置バー — いま断面がどこにあるかを 1 本の帯で示す(単位つき)。"""
    _fill(c, x, y, x + w, y + h, (0.14, 0.15, 0.18))
    px = int(x + (w - 1) * float(np.clip(frac, 0, 1)))
    _fill(c, x, y, px, y + h, color)
    c = imagedraw.draw_line(c, (px, y - 4), (px, y + h + 4), color=(1, 1, 1), width=1)
    return _text(c, [(x, y + h + 4, label_lo, C_DIM, 11, False),
                     (x + w - _text_w(label_hi, 11), y + h + 4, label_hi, C_DIM, 11, False),
                     (min(max(x, px - _text_w(cur_label, 12, True) // 2),
                          x + w - _text_w(cur_label, 12, True)), y - 20,
                      cur_label, color, 12, True)])


def _extent_50(sl, axis, spacing_mm):
    """50 % 等値面の幅を mm で測る(voxel 数ではなく交差位置で測る)。

    二値マスクの voxel 数を「直径」と呼ぶと必ず 1 voxel ぶん狂う。0.5 を跨ぐ位置を
    線形補間して、いちばん広いところの幅を返す。

    *axis* は **測る方向**(0 = 軸 0 に沿った幅、1 = 軸 1 に沿った幅)。2-D 断面
    ``sl`` が ``(row, col)`` なら ``axis=0`` は縦(row 方向)の幅、``axis=1`` は
    横(col 方向)の幅。方向を取り違えると長径と短径が入れ替わるので、呼ぶ側で
    必ず理論値と突き合わせること。
    """
    a = np.asarray(sl, np.float64)
    best = 0.0
    lines = a.T if axis == 0 else a          # axis=0 の幅は「列ごとに縦を走査」
    for line in lines:
        idx = np.nonzero(line >= 0.5)[0]
        if idx.size < 1:
            continue
        i0, i1 = idx[0], idx[-1]
        lo = i0 - 0.5
        if i0 > 0 and line[i0] > line[i0 - 1]:
            lo = i0 - 1 + (0.5 - line[i0 - 1]) / max(line[i0] - line[i0 - 1], 1e-12)
        hi = i1 + 0.5
        if i1 + 1 < line.size and line[i1] > line[i1 + 1]:
            hi = i1 + (line[i1] - 0.5) / max(line[i1] - line[i1 + 1], 1e-12)
        best = max(best, (hi - lo) * spacing_mm)
    return best


# --------------------------------------------------------------------------- #
# 展示 S1 — z スライス送り(添字と物理位置の両方)                                 #
# --------------------------------------------------------------------------- #
def ex_slice_zsweep(log) -> dict:
    """異方性 spacing の CT を 1 スライスずつ送る。添字と mm を必ず併記する。"""
    n_z, n_y, n_x = 96, 128, 128
    sp = (0.8, 0.3, 0.3)                     # z だけ粗い(典型的な CT)
    zz, yy, xx = np.mgrid[0:n_z, 0:n_y, 0:n_x].astype(np.float64)
    hu = np.full((n_z, n_y, n_x), -1000.0)
    body = ((yy - 64.) ** 2 + ((xx - 64.) / 1.08) ** 2) <= 52.0 ** 2
    hu[body] = 40.0
    lung = ((((yy - 56.) / 1.0) ** 2 + ((xx - 42.) / 0.72) ** 2) <= 22.0 ** 2) | \
           ((((yy - 56.) / 1.0) ** 2 + ((xx - 86.) / 0.72) ** 2) <= 22.0 ** 2)
    hu[lung & body] = -820.0
    rr = np.sqrt((yy - 64.) ** 2 + ((xx - 64.) / 1.08) ** 2)
    rib = (rr > 44) & (rr < 49) & ((zz % 10) < 3)
    hu[rib & body] = 900.0
    spine = ((yy - 98.) ** 2 + (xx - 64.) ** 2) <= 11.0 ** 2
    hu[spine & body] = 1100.0
    # 斜めに走る血管(スライス送りで動いて見えるもの = 送っている実感)
    vessel = _capsule((n_z, n_y, n_x), (4, 50, 34), (92, 84, 96), 3.2)
    hu[vessel] = 150.0
    win = np.asarray(G("vol_window_level")(hu, 40.0, 400.0))
    bone = np.asarray(G("vol_window_level")(hu, 500.0, 2000.0))
    thick_mm = n_z * sp[0]
    log(f"    volume {n_z}x{n_y}x{n_x}  spacing {sp} mm  z 全長 {thick_mm:.1f} mm")
    log(f"    1 スライス送り = {sp[0]:.2f} mm、面内 1 画素 = {sp[1]:.2f} mm "
        f"({sp[0] / sp[1]:.2f} 倍)")

    W, H = 1120, 748
    ps = 430
    frames = []
    for z in range(n_z):
        c = _canvas(W, H)
        c = _header(c, "断層を送る ―― 添字と物理位置は別物",
                    f"合成 CT {n_z}x{n_y}x{n_x}、spacing (z, y, x) = "
                    f"({sp[0]}, {sp[1]}, {sp[2]}) mm/voxel。1 スライス送りは "
                    f"{sp[0]:.2f} mm、面内 1 画素は {sp[1]:.2f} mm。")
        c, s1 = _slice_panel(c, win[z], 18, 84, ps, "gray", border=C_A)
        c, _ = _slice_panel(c, bone[z], 18 + ps + 16, 84, ps, "gray", border=C_B)
        c = _text(c, [(18, 84 + ps + 6, "軟部組織窓(center 40 / width 400 HU)",
                       C_A, 13, True),
                      (18 + ps + 16, 84 + ps + 6, "骨窓(center 500 / width 2000 HU)",
                       C_B, 13, True),
                      (18, 84 + ps + 26, "上が y=0(前)、左が x=0。表示は最近傍拡大 "
                                         "%.2f 倍。" % s1, C_DIM, 11, False)])
        # 位置の読み(添字 / mm / 全長比)
        c = _text(c, [
            (924, 96, "スライス添字", C_DIM, 12, False),
            (924, 114, "z = %2d / %d" % (z, n_z - 1), C_TEXT, 22, True),
            (924, 152, "物理位置", C_DIM, 12, False),
            (924, 170, "%6.2f mm" % (z * sp[0]), C_D, 24, True),
            (924, 206, "(= %d x %.2f mm)" % (z, sp[0]), C_DIM, 12, False),
            (924, 232, "全長 %.1f mm の %.1f %%" % (thick_mm, 100 * z / (n_z - 1)),
             C_DIM, 12, False),
            (924, 268, "面内で同じ 1 画素は", C_DIM, 12, False),
            (924, 286, "%.2f mm" % sp[1], C_E, 20, True),
            (924, 312, "= 送り 1 コマの %.2f 倍" % (sp[1] / sp[0]), C_DIM, 12, False),
            (924, 340, "「1 つ動かす」が軸で", C_TEXT, 12, True),
            (924, 358, "違う距離を意味する。", C_TEXT, 12, True),
        ])
        c = _ruler(c, 18, 588, W - 200, 14, z / (n_z - 1), C_D,
                   "0.0 mm (z=0)", "%.1f mm (z=%d)" % (thick_mm, n_z - 1),
                   "z=%d  %.2f mm" % (z, z * sp[0]))
        # 添字 -> mm の対応(軸ごとに傾きが違う)
        p = Plot(c, 60, 652, 620, 58, (0, 127), (0, 105),
                 xlabel="添字(voxel)->", xticks=[0, 32, 64, 96, 127],
                 yticks=[0, 50, 100], xfmt="%d", yfmt="%d")
        p.series([0, n_z - 1], [0, (n_z - 1) * sp[0]], C_D, width=2)
        p.series([0, n_y - 1], [0, (n_y - 1) * sp[1]], C_E, width=2)
        p.marker(z, z * sp[0], C_D, size=5)
        p.items.append((66, 634, "z 軸 %.2f mm/voxel" % sp[0], C_D, 11, True))
        p.items.append((210, 634, "y / x 軸 %.2f mm/voxel" % sp[1], C_E, 11, True))
        p.items.append((380, 634, "縦は mm(同じ添字でも進む距離が違う)", C_DIM, 11, False))
        c = p.done()
        c = _text(c, [(724, 660, "使用 op: vol_window_level", C_DIM, 12, False),
                      (724, 680, "合成 HU データ(実在の患者・スキャン", C_DIM, 12, False),
                      (724, 698, "ではありません)。seed 固定。", C_DIM, 12, False)])
        frames.append(c)

    info = _save_clip(frames, "wing3d_slice_zsweep", fps=15, thumb_index=n_z // 2, log=log)
    return {
        "name": "wing3d_slice_zsweep",
        "title": "断層を送る ―― `z = 48 / 95` は %.2f mm のこと" % (48 * sp[0]),
        "ops": ["vol_window_level"],
        "facts": {"shape": [n_z, n_y, n_x], "spacing_mm": list(sp),
                  "z_extent_mm": thick_mm, "mm_per_slice": sp[0],
                  "mm_per_inplane_pixel": sp[1],
                  "anisotropy_ratio": sp[0] / sp[1], "frames": n_z},
        "caption": (f"合成 CT({n_z}×{n_y}×{n_x}、spacing ({sp[0]}, {sp[1]}, {sp[2]}) mm)を "
                    f"1 スライスずつ {n_z} コマ送る。各コマに**添字と物理位置の両方**"
                    f"(`z = 48 / 95` = {48 * sp[0]:.2f} mm)と位置バーを焼いた。"
                    f"1 スライス送りは {sp[0]:.2f} mm、面内 1 画素は {sp[1]:.2f} mm "
                    f"= **{sp[1] / sp[0]:.2f} 倍**なので、下の折れ線のとおり「添字を 1 つ"
                    "動かす」は軸ごとに違う距離を意味する ―― 異方性 CT でいちばん"
                    "踏みやすい段差。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 S2 — 3 直交断面(MPR)とクロスヘア                                         #
# --------------------------------------------------------------------------- #
def ex_mpr(log) -> dict:
    """axial / coronal / sagittal を同時に動かし、交差線で見ている点を示す。"""
    n = 128
    sp = (0.5, 0.5, 0.5)
    # 向きが一目で分かるよう、非対称なランドマークを入れる(左右反転の検出用)
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    vol = np.zeros((n, n, n))
    body = (((zz - 64.) / 52.) ** 2 + ((yy - 64.) / 44.) ** 2
            + ((xx - 64.) / 38.) ** 2) <= 1.0
    vol[body] = 0.35
    # 右側(x 大)にだけ球、前側(y 小)にだけ棒、上側(z 大)にだけリング
    vol[_aa_ball((n, n, n), (64., 64., 96.), 11.0) > 0.5] = 0.95
    vol[_capsule((n, n, n), (30, 30, 64), (98, 30, 64), 5.0)] = 0.75
    ring = (np.abs(zz - 100.) <= 3) & (np.abs(np.sqrt((yy - 64.) ** 2 + (xx - 64.) ** 2) - 26.) <= 3)
    vol[ring] = 0.85
    helix = np.zeros((n, n, n), bool)
    for t in np.linspace(0, 1, 900):
        z = 16 + t * 96
        a = 2 * math.pi * 2.0 * t
        y = 64 + 28 * math.sin(a)
        x = 64 + 28 * math.cos(a)
        helix |= _aa_ball((n, n, n), (z, y, x), 2.6) > 0.5
    vol[helix] = 1.0
    log(f"    volume {vol.shape} spacing {sp}  landmarks: +x 球 / -y 棒 / +z リング / らせん")

    W, H = 1120, 620
    ps = 300
    nf = 60
    frames = []
    for k in range(nf):
        t = k / nf
        a = 2 * math.pi * 2.0 * t
        cz = 16.0 + 96.0 * t
        cy = 64.0 + 28.0 * math.sin(a)
        cx = 64.0 + 28.0 * math.cos(a)
        iz, iy, ix = int(round(cz)), int(round(cy)), int(round(cx))
        c = _canvas(W, H)
        c = _header(c, "3 直交断面(MPR)―― どの断面のどこを見ているか",
                    "らせん状の目印を追いかけながら axial / coronal / sagittal を"
                    "同時に動かす。3 本のクロスヘアは同じ 1 点を指している。")
        # axial: vol[z] は (y, x) — 縦 y、横 x
        c, s = _slice_panel(c, vol[iz], 18, 92, ps, "gray", border=C_A)
        c = _crosshair(c, 18, 92, ps, ix * s, iy * s, C_A)
        # coronal: vol[:, y, :] は (z, x) — 縦 z、横 x。z を上向きにするので上下反転
        cor = vol[:, iy, :][::-1, :]
        c, _ = _slice_panel(c, cor, 18 + ps + 16, 92, ps, "gray", border=C_B)
        c = _crosshair(c, 18 + ps + 16, 92, ps, ix * s, (n - 1 - iz) * s, C_B)
        # sagittal: vol[:, :, x] は (z, y) — 縦 z(上向き)、横 y
        sag = vol[:, :, ix][::-1, :]
        c, _ = _slice_panel(c, sag, 18 + 2 * (ps + 16), 92, ps, "gray", border=C_C)
        c = _crosshair(c, 18 + 2 * (ps + 16), 92, ps, iy * s, (n - 1 - iz) * s, C_C)

        c = _text(c, [
            (18, 92 + ps + 8, "axial  vol[z=%d]" % iz, C_A, 14, True),
            (18, 92 + ps + 28, "横 = x ->  縦 = y (下向き)", C_DIM, 12, False),
            (18 + ps + 16, 92 + ps + 8, "coronal  vol[:, y=%d, :]" % iy, C_B, 14, True),
            (18 + ps + 16, 92 + ps + 28, "横 = x ->  縦 = z (上向き・表示で反転)",
             C_DIM, 12, False),
            (18 + 2 * (ps + 16), 92 + ps + 8, "sagittal  vol[:, :, x=%d]" % ix, C_C, 14, True),
            (18 + 2 * (ps + 16), 92 + ps + 28, "横 = y ->  縦 = z (上向き・表示で反転)",
             C_DIM, 12, False),
        ])
        c = _text(c, [
            (18, 470, "交点(z, y, x) = (%3d, %3d, %3d) voxel" % (iz, iy, ix),
             C_TEXT, 17, True),
            (18, 496, "        = (%.2f, %.2f, %.2f) mm  spacing %.1f mm/voxel"
             % (iz * sp[0], iy * sp[1], ix * sp[2], sp[0]), C_D, 15, True),
            (18, 524, "その点の値 %.3f" % float(vol[iz, iy, ix]), C_TEXT, 13, False),
            (470, 466, "向きの確認用ランドマーク(取り違えたら図が壊れる)", C_DIM, 12, False),
            (470, 488, "x が大きい側にだけ 明るい球     -> axial / coronal の右端",
             C_TEXT, 12, False),
            (470, 508, "y が小さい側にだけ 横棒         -> axial の上端 / sagittal の左端",
             C_TEXT, 12, False),
            (470, 528, "z が大きい側にだけ リング       -> coronal / sagittal の上端",
             C_TEXT, 12, False),
            (470, 552, "coronal / sagittal は z を上向きに見せるため表示時に上下反転して"
                       "いる(配列そのものは反転していない)。", C_DIM, 12, False),
        ])
        c = _ruler(c, 18, 586, W - 40, 12, t, C_A, "z=0", "z=%d" % (n - 1),
                   "z=%d (%.1f mm)" % (iz, iz * sp[0]))
        frames.append(c)

    info = _save_clip(frames, "wing3d_mpr_crosshair", fps=15, thumb_index=nf // 4, log=log)
    return {
        "name": "wing3d_mpr_crosshair",
        "title": "3 直交断面(MPR)とクロスヘア",
        "ops": ["(numpy スライス + imagedraw)"],
        "facts": {"shape": [n, n, n], "spacing_mm": list(sp), "frames": nf,
                  "landmarks": {"+x": "球", "-y": "横棒", "+z": "リング"}},
        "caption": ("同じ 1 点を 3 方向から見る MPR。axial(`vol[z]`)・coronal"
                    "(`vol[:, y, :]`)・sagittal(`vol[:, :, x]`)を横に並べ、"
                    "らせん状の目印を追いながら 3 本のクロスヘアを同時に動かした。"
                    "各パネルに**どの軸が横でどの軸が縦か**を書き、`+x` に球・`-y` に横棒・"
                    "`+z` にリングという非対称なランドマークを入れてある ―― 軸の"
                    "入れ替わりや左右反転が起きたら、この 3 つの位置がずれて必ず露見する。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 S3 — 斜め断面(円柱を斜めに切ると楕円になる)                               #
# --------------------------------------------------------------------------- #
def ex_oblique(log) -> dict:
    """切断面を 0 -> 80 度まで倒し、切り口が円から楕円へ伸びるのを測る。"""
    n = 192
    sp = 0.25                                  # mm / voxel(等方)
    r_vox = 20.0
    r_mm = r_vox * sp
    ctr = n // 2
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    rr = np.sqrt((yy - float(ctr)) ** 2 + (xx - float(ctr)) ** 2)
    cyl = np.clip(r_vox - rr + 0.5, 0.0, 1.0)         # 軸 = z、反エイリアス
    # 70 deg で長径は 2r/cos70 = 117 voxel。枠(192)に収まる範囲までしか回さない
    # — reshape=False の vol_rotate は枠から出た部分を**黙って捨てる**ので、
    #   収まらない角度まで回すと「測った長径が枠幅で頭打ち」になってしまう。
    angles = list(range(0, 71, 2))
    rows = []
    slices = {}
    for ang in angles:
        v = np.asarray(G("vol_rotate")(cyl, float(ang), axes=(0, 1), order=1,
                                       reshape=False, mode="constant", cval=0.0))
        sl = v[ctr]
        slices[ang] = sl
        # sl は (y, x)。切断面を z-y 面内で倒したので、伸びるのは y 方向 = axis 0。
        minor = _extent_50(sl, 1, sp)          # x 方向(倒しても変わらない)
        major = _extent_50(sl, 0, sp)          # y 方向(1/cos で伸びる)
        truth_major = 2 * r_mm / math.cos(math.radians(ang))
        m = sl >= 0.5
        clipped = bool(m[0, :].any() or m[-1, :].any() or m[:, 0].any() or m[:, -1].any())
        if clipped:                            # fail-closed: 頭打ちの数字を出さない
            raise RuntimeError(
                "oblique slice at %d deg touches the frame border — vol_rotate("
                "reshape=False) has clipped the cut and the measured extent would "
                "saturate at the frame width. Enlarge the volume or reduce the angle."
                % ang)
        rows.append({"angle_deg": ang, "minor_mm": minor, "major_mm": major,
                     "truth_minor_mm": 2 * r_mm, "truth_major_mm": truth_major,
                     "area_mm2": float(m.sum()) * sp * sp,
                     "truth_area_mm2": math.pi * r_mm ** 2 / math.cos(math.radians(ang))})
    for r in rows[::8]:
        log(f"    ang {r['angle_deg']:2d} deg  minor {r['minor_mm']:.3f} "
            f"(truth {r['truth_minor_mm']:.3f})  major {r['major_mm']:.3f} "
            f"(truth {r['truth_major_mm']:.3f})  err {r['major_mm'] - r['truth_major_mm']:+.3f} mm")
    max_major_err = max(abs(r["major_mm"] - r["truth_major_mm"]) for r in rows)
    max_minor_err = max(abs(r["minor_mm"] - r["truth_minor_mm"]) for r in rows)
    log(f"    max |major err| {max_major_err:.4f} mm   max |minor err| {max_minor_err:.4f} mm")

    W, H = 1120, 640
    ps = 380
    frames = []
    for r in rows:
        ang = r["angle_deg"]
        c = _canvas(W, H)
        c = _header(c, "斜めに切る ―― 円柱の切り口は角度で楕円に伸びる",
                    f"半径 {r_mm:.2f} mm の合成円柱(軸 = z)。切断面を z-y 面内で "
                    f"{ang:2d}° 倒して切る(vol_rotate の逆回しで実現)。")
        c, s = _slice_panel(c, slices[ang], 18, 92, ps, "gray", border=C_B)
        # 測った長短径を線で重ねる
        m = slices[ang] >= 0.5
        if m.any():
            ys, xs = np.nonzero(m)
            cyv = (ys.min() + ys.max()) / 2.0
            cxv = (xs.min() + xs.max()) / 2.0
            hy = r["major_mm"] / sp / 2.0
            hx = r["minor_mm"] / sp / 2.0
            c = imagedraw.draw_line(c, (18 + cxv * s, 92 + (cyv - hy) * s),
                                    (18 + cxv * s, 92 + (cyv + hy) * s), color=C_E, width=2)
            c = imagedraw.draw_line(c, (18 + (cxv - hx) * s, 92 + cyv * s),
                                    (18 + (cxv + hx) * s, 92 + cyv * s), color=C_A, width=2)
        c = _text(c, [(18, 92 + ps + 6, "切り口(vol_rotate 後の z 中央スライス)",
                       C_B, 13, True),
                      (18, 92 + ps + 26, "ローズ = 長径(y 方向) / シアン = 短径(x 方向)",
                       C_DIM, 12, False)])
        # 断面の作り方の模式(側面図)
        sx, sy, sw, sh = 428, 92, 250, ps
        _fill(c, sx, sy, sx + sw, sy + sh, C_PANEL)
        cx0, cy0 = sx + sw / 2, sy + sh / 2
        rw = 42.0
        c = imagedraw.draw_polyline(
            c, [(cx0 - rw, cy0 - 140), (cx0 + rw, cy0 - 140),
                (cx0 + rw, cy0 + 140), (cx0 - rw, cy0 + 140)],
            color=(0.30, 0.34, 0.40), width=2, closed=True)
        th = math.radians(ang)
        L = 118.0
        c = imagedraw.draw_line(c, (cx0 - L * math.cos(th), cy0 + L * math.sin(th)),
                                (cx0 + L * math.cos(th), cy0 - L * math.sin(th)),
                                color=C_B, width=3)
        c = imagedraw.draw_line(c, (cx0 - L, cy0), (cx0 + L, cy0), color=C_RULE, width=1)
        c = imagedraw.draw_polyline(
            c, [(sx, sy), (sx + sw - 1, sy), (sx + sw - 1, sy + sh - 1), (sx, sy + sh - 1)],
            color=C_RULE, width=1, closed=True)
        c = _text(c, [(sx + 8, sy + 8, "側面図(z 上, y 右)", C_DIM, 12, True),
                      (sx + 8, sy + 28, "灰 = 円柱、黄 = 切断面", C_DIM, 11, False),
                      (sx + 8, sy + sh - 26, "傾き %2d deg" % ang, C_B, 15, True),
                      (sx, sy + sh + 6, "切断面の傾き", C_TEXT, 12, True)])

        p = Plot(c, 760, 120, 330, 200, (0, 80), (0, 32),
                 xlabel="切断面の傾き [deg] ->", ylabel="切り口の径 [mm]",
                 xticks=[0, 20, 40, 60, 80], yticks=[0, 10, 20, 30],
                 xfmt="%d", yfmt="%d")
        p.series([x["angle_deg"] for x in rows], [x["truth_major_mm"] for x in rows],
                 (0.55, 0.30, 0.36), width=3)
        p.series([x["angle_deg"] for x in rows], [x["major_mm"] for x in rows], C_E, width=2)
        p.series([x["angle_deg"] for x in rows], [x["minor_mm"] for x in rows], C_A, width=2)
        p.marker(ang, r["major_mm"], C_E, size=6)
        p.marker(ang, r["minor_mm"], C_A, size=6)
        p.items.append((766, 124, "長径 = 2r / cos(theta)(太い暗線が理論値)", C_E, 11, True))
        p.items.append((766, 142, "短径 = 2r(角度によらない)", C_A, 11, True))
        c = p.done()
        c = _text(c, [
            (760, 360, "傾き %2d deg のとき" % ang, C_DIM, 12, False),
            (760, 380, "短径 %.3f mm" % r["minor_mm"], C_A, 17, True),
            (760, 404, " 真値 %.3f mm  (差 %+.3f)"
             % (r["truth_minor_mm"], r["minor_mm"] - r["truth_minor_mm"]), C_DIM, 12, False),
            (760, 428, "長径 %.3f mm" % r["major_mm"], C_E, 17, True),
            (760, 452, " 真値 %.3f mm  (差 %+.3f)"
             % (r["truth_major_mm"], r["major_mm"] - r["truth_major_mm"]), C_DIM, 12, False),
            (760, 480, "面積 %.2f mm^2(真値 %.2f)"
             % (r["area_mm2"], r["truth_area_mm2"]), C_TEXT, 12, False),
            (18, 520, "斜めに切った断面で測った「直径」は、そのままでは部品の直径ではない。",
             C_TEXT, 15, True),
            (18, 546, "短径は角度によらず %.3f mm のままなのに、長径は %d deg で %.3f mm "
                      "= %.2f 倍になる。"
             % (rows[0]["minor_mm"], rows[-1]["angle_deg"], rows[-1]["major_mm"],
                rows[-1]["major_mm"] / rows[0]["minor_mm"]), C_TEXT, 13, False),
            (18, 570, "全 %d 角度での実測と理論の差は 長径 最大 %.4f mm / "
                      "短径 最大 %.4f mm(spacing %.2f mm の %.2f 画素ぶん)。"
             % (len(rows), max_major_err, max_minor_err, sp, max_major_err / sp),
             C_D, 13, True),
            (18, 596, "測り方は 50 % 等値面の交差位置を線形補間して求めた "
                      "— 二値の voxel 数を直径と呼ぶと必ず 1 画素ぶん狂う。",
             C_DIM, 12, False),
        ])
        c = _footer(c, "使用 op: vol_rotate  — 合成データ(反エイリアス円柱)", y_off=14)
        frames.append(c)

    info = _save_clip(frames, "wing3d_oblique_slice", fps=10,
                      thumb_index=len(rows) * 3 // 4, log=log)
    return {
        "name": "wing3d_oblique_slice",
        "title": "斜めに切ると円が楕円になる(長径は 1/cos で伸びる)",
        "ops": ["vol_rotate"],
        "facts": {"radius_mm": r_mm, "spacing_mm": sp, "angles_deg": angles,
                  "rows": rows, "max_major_err_mm": max_major_err,
                  "max_minor_err_mm": max_minor_err},
        "caption": (f"半径 {r_mm:.2f} mm の合成円柱を、切断面を 0° から 80° まで倒しながら"
                    f"切る(`vol_rotate` の逆回し)。短径は角度によらず "
                    f"{rows[0]['minor_mm']:.3f} mm のままなのに、長径は "
                    f"**2r / cos θ** に沿って伸び、80° では {rows[-1]['major_mm']:.3f} mm "
                    f"= {rows[-1]['major_mm'] / rows[0]['minor_mm']:.2f} 倍になる。"
                    f"{len(rows)} 角度({angles[0]}°〜{angles[-1]}°)すべてで理論値との差は"
                    f"最大 {max_major_err:.4f} mm({max_major_err / sp:.2f} 画素)。"
                    "「斜めの断面で測った直径」を"
                    "そのまま寸法にしてはいけない、という一本。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 S4 — CT の窓を掃引する                                                    #
# --------------------------------------------------------------------------- #
def ex_window_sweep(log) -> dict:
    """center / width を動かして、何が飽和し何が沈むかを 1 本で見せる。"""
    n = 128
    hu = _ct_phantom(n)
    z = 64
    tissue = [("空気", -1000.0, C_DIM), ("肺", -820.0, C_D), ("軟部", 40.0, C_A),
              ("血管", 120.0, C_C), ("肋骨", 900.0, C_B), ("椎体", 1100.0, C_E)]
    seq = []
    for cc in np.linspace(-800, 900, 30):
        seq.append((float(cc), 400.0, "center を掃引(width 400 HU 固定)"))
    for ww in np.geomspace(150, 2600, 26):
        seq.append((40.0, float(ww), "width を掃引(center 40 HU 固定)"))
    for cc, ww in zip(np.linspace(40, 500, 14), np.linspace(400, 2000, 14)):
        seq.append((float(cc), float(ww), "軟部窓 -> 骨窓へ移る"))
    rows = []
    outs = []
    for cc, ww, phase in seq:
        o = np.asarray(G("vol_window_level")(hu, cc, ww))
        outs.append(o[z])
        rows.append({"center": cc, "width": ww, "phase": phase,
                     "sat_low_pct": 100 * float((o <= 0).mean()),
                     "sat_high_pct": 100 * float((o >= 1).mean()),
                     "vals": {name: float(np.clip((v - (cc - ww / 2)) / ww, 0, 1))
                              for name, v, _ in tissue}})
    log(f"    {len(seq)} 通りの窓を掃引 (center {min(r['center'] for r in rows):.0f} .. "
        f"{max(r['center'] for r in rows):.0f} HU, width "
        f"{min(r['width'] for r in rows):.0f} .. {max(r['width'] for r in rows):.0f} HU)")
    for i in (0, 29, 42, 55, len(rows) - 1):
        r = rows[i]
        log(f"      c={r['center']:+7.1f} w={r['width']:7.1f}  "
            f"黒潰れ {r['sat_low_pct']:5.1f} %  白飛び {r['sat_high_pct']:5.1f} %")

    W, H = 1120, 660
    ps = 420
    frames = []
    for i, (r, sl) in enumerate(zip(rows, outs)):
        c = _canvas(W, H)
        c = _header(c, "CT の窓を掃引する ―― 見えるものは窓が決めている",
                    f"同じ 1 枚のスライス(z = {z})に `vol_window_level` の窓だけを"
                    f"動かして当てる。{r['phase']}")
        c, s = _slice_panel(c, sl, 18, 92, ps, "gray", border=C_A)
        c = _text(c, [(18, 92 + ps + 6, "z = %d の軟部〜骨を含む断面" % z, C_A, 13, True),
                      (18, 92 + ps + 26,
                       "黒に潰れた %.1f %% / 白に飛んだ %.1f %%"
                       % (r["sat_low_pct"], r["sat_high_pct"]), C_TEXT, 13, True)])
        c = _text(c, [
            (470, 96, "center", C_DIM, 12, False),
            (470, 114, "%+7.1f HU" % r["center"], C_B, 26, True),
            (700, 96, "width", C_DIM, 12, False),
            (700, 114, "%7.1f HU" % r["width"], C_C, 26, True),
            (470, 154, "窓の範囲  %+.0f .. %+.0f HU"
             % (r["center"] - r["width"] / 2, r["center"] + r["width"] / 2),
             C_TEXT, 15, True),
        ])
        p = Plot(c, 530, 214, 550, 142, (-1200, 1400), (-0.05, 1.05),
                 xlabel="HU ->", xticks=[-1000, -500, 0, 500, 1000],
                 yticks=[0, 0.5, 1.0], xfmt="%d", yfmt="%.1f")
        p.items.append((470, 194, "窓の出力 [0,1]", C_DIM, 11, False))
        lo, hi = r["center"] - r["width"] / 2, r["center"] + r["width"] / 2
        p.series([-1200, lo, hi, 1400], [0, 0, 1, 1], C_B, width=3)
        for j, (name, v, col) in enumerate(tissue):
            p.c = imagedraw.draw_line(p.c, (p.px(v), p.y0), (p.px(v), p.y0 + p.h - 1),
                                      color=(0.28, 0.30, 0.34), width=1)
            y = r["vals"][name]
            p.c = imagedraw.draw_markers(p.c, [(p.px(v), p.py(y))], color=col,
                                         size=5, shape="dot", width=2)
            # 上下 2 段に振り分ける(HU 軸上で近い組織のラベルが重ならないように)
            p.items.append((p.px(v) - _text_w(name, 10, True) / 2,
                            p.y0 - 32 + 16 * (j % 2), name, col, 10, True))
        c = p.done()
        # 各組織が「いま何色に見えるか」の帯
        bx, by, bw, bh = 530, 408, 550, 26
        c = _text(c, [(bx, by - 20, "この窓での各組織の見え方(0 = 真っ黒, 1 = 真っ白)",
                       C_DIM, 12, False)])
        seg = bw // len(tissue)
        items = []
        for j, (name, v, col) in enumerate(tissue):
            y = r["vals"][name]
            _fill(c, bx + j * seg, by, bx + (j + 1) * seg - 4, by + bh,
                  (y, y, y))
            c = imagedraw.draw_polyline(
                c, [(bx + j * seg, by), (bx + (j + 1) * seg - 5, by),
                    (bx + (j + 1) * seg - 5, by + bh - 1), (bx + j * seg, by + bh - 1)],
                color=col, width=1, closed=True)
            items.append((bx + j * seg + 2, by + bh + 4, name, col, 11, True))
            items.append((bx + j * seg + 2, by + bh + 20, "%.2f" % y, C_TEXT, 11, False))
        c = _text(c, items)
        c = _text(c, [
            (530, 494, "軟部窓(center 40 / width 400)では肋骨も椎体も 1.00 = 白飛び。",
             C_TEXT, 13, False),
            (530, 516, "骨窓(center 500 / width 2000)では軟部と肺が 0 付近に沈む。",
             C_TEXT, 13, False),
            (530, 540, "どちらも情報が消えている。窓は「見せ方」ではなく"
                       "「何を捨てるか」の選択。", C_D, 13, True),
        ])
        c = _ruler(c, 18, 596, 420, 12, i / (len(rows) - 1), C_B,
                   "掃引 開始", "終了",
                   "%d / %d コマ" % (i + 1, len(rows)))
        c = _footer(c, "使用 op: vol_window_level  — 合成 HU データ(実在の患者・"
                       "スキャンではありません)", y_off=18)
        frames.append(c)

    info = _save_clip(frames, "wing3d_window_sweep", fps=12, thumb_index=29, log=log)
    lo_soft = [r for r in rows if abs(r["center"] - 40) < 1 and abs(r["width"] - 400) < 60]
    return {
        "name": "wing3d_window_sweep",
        "title": "CT の窓を掃引する ―― 見えるものは窓が決めている",
        "ops": ["vol_window_level"],
        "facts": {"steps": len(rows), "z": z,
                  "center_range": [min(r["center"] for r in rows),
                                   max(r["center"] for r in rows)],
                  "width_range": [min(r["width"] for r in rows),
                                  max(r["width"] for r in rows)],
                  "rows": rows},
        "caption": (f"同じ 1 枚の断面に `vol_window_level` の窓だけを {len(rows)} 通り当てる。"
                    "center を動かすと明るさの基準が、width を動かすと捨てる範囲が変わる。"
                    "各コマに center / width の実数値と、黒潰れ・白飛びの割合、"
                    "6 つの組織が「いま何色に見えるか」を焼いた。軟部窓では骨が 1.00 で"
                    "飽和し、骨窓では軟部と肺が 0 付近に沈む ―― どちらも情報を捨てている、"
                    "というのが 1 本で見える。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 S5 — 等値面のしきい値を掃引する                                            #
# --------------------------------------------------------------------------- #
def ex_isosurface(log) -> dict:
    """marching cubes の level を動かし、面が育つ/くびれて割れるのを測る。"""
    n = 96
    import scipy.ndimage as ndi
    # 2 つの球を細い橋でつなぐ。level を上げると橋が先に消えて面が「割れる」。
    a = _aa_ball((n, n, n), (48., 34., 34.), 14.0)
    b = _aa_ball((n, n, n), (48., 62., 62.), 12.0)
    bridge = _capsule((n, n, n), (48, 34, 34), (48, 62, 62), 3.6).astype(np.float64)
    vol = ndi.gaussian_filter(np.maximum(np.maximum(a, b), bridge), 2.2)
    vol = _norm01(vol)
    levels = [round(x, 3) for x in np.linspace(0.06, 0.82, 40)]
    rows, meshes = [], {}
    st = np.ones((3, 3, 3), int)
    for lv in levels:
        try:
            verts, faces, _ = G("voxel_to_mesh")(vol, iso=lv)
        except Exception as exc:                     # 面が消えたら honest に記録
            rows.append({"level": lv, "verts": 0, "faces": 0, "area": 0.0,
                         "components": 0, "occupied": int((vol > lv).sum()),
                         "note": str(exc)[:80]})
            meshes[lv] = None
            continue
        area = float(G("mesh_area")((verts, faces)))
        ncomp = int(ndi.label(vol > lv, structure=st)[1])
        rows.append({"level": lv, "verts": int(len(verts)), "faces": int(len(faces)),
                     "area": area, "components": ncomp,
                     "occupied": int((vol > lv).sum()), "note": ""})
        meshes[lv] = np.asarray(verts, np.float64)
    for r in rows[::6]:
        log(f"    level {r['level']:.3f}  verts {r['verts']:6d}  faces {r['faces']:6d}  "
            f"area {r['area']:9.1f}  成分 {r['components']}  占有 {r['occupied']:7d}")
    split = next((r["level"] for r in rows if r["components"] >= 2), None)
    log(f"    2 つに割れ始める level = {split}")

    W, H = 1120, 640
    ps = 400
    frames = []
    center = np.array([48.0, 48.0, 48.0])
    R = _rot(32.0, 20.0)
    for i, r in enumerate(rows):
        lv = r["level"]
        c = _canvas(W, H)
        c = _header(c, "等値面のしきい値を動かす ―― 面は育ち、くびれ、割れる",
                    "2 つの球をぼかして重ねた合成ボリューム。`voxel_to_mesh`"
                    "(marching cubes)の level だけを動かす。")
        px, py = 18, 92
        _fill(c, px, py, px + ps, py + ps, C_PANEL)
        sub = c[py:py + ps, px:px + ps]
        v = meshes[lv]
        if v is not None and len(v):
            u, vv, dd = _project(v[:, [2, 1, 0]], R, 3.5, ps / 2, ps / 2,
                                 center[[2, 1, 0]])
            _splat(sub, u, vv, dd, C_B if r["components"] < 2 else C_E,
                   radius=1, shade=0.6)
        c = imagedraw.draw_polyline(
            c, [(px, py), (px + ps - 1, py), (px + ps - 1, py + ps - 1), (px, py + ps - 1)],
            color=C_RULE, width=1, closed=True)
        c = _axis_gizmo(c, R, px + 42, py + ps - 42, size=28)
        c = _text(c, [(px, py + ps + 6, "等値面の頂点(%d 点)を点で表示" % r["verts"],
                       C_TEXT, 12, True)])
        # 断面での等値線(level のどこを切っているかを 2D でも見せる)
        c2, s2 = _slice_panel(c, vol[48], 440, 92, 260, "viridis", 0, 1, border=C_C)
        c = c2
        # 等値線は「しきい値を超えた領域の境界」で描く。|value - level| < eps の帯だと
        # 勾配が急なところで線が途切れて、閉じていない等値線に見えてしまう。
        above = vol[48] > lv
        band = above & ~ndi.binary_erosion(above, structure=np.ones((3, 3), bool))
        ys, xs = np.nonzero(band)
        if ys.size:
            sub2 = c[92:92 + 260, 440:440 + 260]
            uu = np.clip(np.rint(xs * s2).astype(int), 1, 258)
            vv2 = np.clip(np.rint(ys * s2).astype(int), 1, 258)
            for dy in (-1, 0, 1):                      # 3x3 に太らせて縮小でも消えない
                for dx in (-1, 0, 1):
                    sub2[vv2 + dy, uu + dx, :] = np.asarray(C_E)
        c = _text(c, [(440, 92 + 260 + 6, "z = 48 の断面(色 = 値)と等値線", C_C, 12, True),
                      (440, 92 + 260 + 24, "ローズの線が level = %.3f" % lv, C_E, 12, True)])

        p = Plot(c, 770, 130, 320, 190, (0.05, 0.9), (0, max(r2["area"] for r2 in rows) * 1.08),
                 xlabel="level ->", ylabel="等値面の表面積 [voxel^2]",
                 xticks=[0.1, 0.3, 0.5, 0.7, 0.9], yticks=[0, 5000, 10000, 15000],
                 xfmt="%.1f", yfmt="%d")
        p.series([r2["level"] for r2 in rows], [r2["area"] for r2 in rows], C_B, width=2)
        p.marker(lv, r["area"], C_D, size=6)
        if split is not None:
            p.c = imagedraw.draw_line(p.c, (p.px(split), p.y0),
                                      (p.px(split), p.y0 + p.h - 1), color=C_E, width=1)
            lab = "ここで 2 つに割れる"
            p.items.append((min(p.px(split) + 4, p.x0 + p.w - _text_w(lab, 10, True) - 2),
                            p.y0 + 6, lab, C_E, 10, True))
        c = p.done()
        c = _text(c, [
            (770, 356, "level", C_DIM, 12, False),
            (770, 374, "%.3f" % lv, C_B, 26, True),
            (770, 412, "頂点 %6d / 三角形 %6d" % (r["verts"], r["faces"]), C_TEXT, 13, False),
            (770, 434, "表面積 %.1f voxel^2" % r["area"], C_TEXT, 13, False),
            (770, 456, "内側の占有 %d voxel" % r["occupied"], C_TEXT, 13, False),
            (770, 478, "連結成分 %d 個" % r["components"],
             C_E if r["components"] >= 2 else C_D, 15, True),
            (18, 528, "level を上げると等値面は内側へ縮み、表面積は %.0f -> %.0f voxel^2 "
                      "へ %.2f 倍に。"
             % (rows[0]["area"], rows[-1]["area"],
                rows[-1]["area"] / max(rows[0]["area"], 1e-9)), C_TEXT, 14, True),
            (18, 554, "%s"
             % ("level %.3f を超えると 1 つだった面が 2 つに割れる(くびれが切れる)。"
                % split if split is not None else "この範囲では割れなかった。"),
             C_E, 14, True),
            (18, 580, "「等値面の体積」は level を決めた時点で決まっている。"
                      "しきい値を書かない 3D 計測は再現できない。", C_DIM, 13, False),
        ])
        c = _footer(c, "使用 op: voxel_to_mesh / mesh_area  — 合成データ", y_off=14)
        frames.append(c)

    info = _save_clip(frames, "wing3d_isosurface_sweep", fps=8,
                      thumb_index=len(rows) // 2, log=log)
    return {
        "name": "wing3d_isosurface_sweep",
        "title": "等値面のしきい値で面が育ち、くびれ、割れる",
        "ops": ["voxel_to_mesh", "mesh_area"],
        "facts": {"levels": levels, "rows": rows, "split_level": split},
        "caption": ("2 つの球をぼかして重ねた合成ボリュームに `voxel_to_mesh`"
                    f"(marching cubes)を掛け、level を {levels[0]:.2f} から "
                    f"{levels[-1]:.2f} まで {len(levels)} 段階で動かした。表面積は "
                    f"{rows[0]['area']:.0f} → {rows[-1]['area']:.0f} voxel² へ縮み、"
                    + (f"level {split:.3f} を超えると 1 つだった面が **2 つに割れる**。"
                       if split is not None else "この範囲では割れなかった。")
                    + "各コマに level・頂点数・三角形数・表面積・連結成分数を焼いてある。"
                      "しきい値を書かない 3D 計測は再現できない、ということでもある。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 S6 — 管の走行に沿って断面を送る                                            #
# --------------------------------------------------------------------------- #
def ex_vessel_reslice(log) -> dict:
    """傾いた管を、軸に直交する断面と素朴な軸方向断面の両方で測って比べる。"""
    sp = 0.2                                    # mm/voxel(等方)
    n = 176
    tilt = 28.0                                 # 管を z-y 面内で傾ける [deg]
    th = math.radians(tilt)
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    # 軸は **配列の中心** を通す。scipy の回転中心は (shape-1)/2 なので、そこを外すと
    # 回した後で軸が z からずれ、直交断面と真値の対応が半 voxel 単位で狂う。
    ctr = (n - 1) / 2.0
    az = math.cos(th); ay = math.sin(th)
    s = (zz - ctr) * az + (yy - ctr) * ay        # 軸に沿った座標 [voxel]
    d2 = ((zz - ctr) - s * az) ** 2 + ((yy - ctr) - s * ay) ** 2 + (xx - ctr) ** 2
    dist = np.sqrt(d2)

    def radius_at(sv):
        """軸座標 sv [voxel] における管の半径 [voxel](中央に狭窄を 1 つ)。"""
        return 11.0 - 4.0 * np.exp(-((np.asarray(sv, np.float64) / 22.0) ** 2))

    tube = np.clip(radius_at(s) - dist + 0.5, 0.0, 1.0)

    # 軸に直交する断面 = 体積を -tilt だけ回してから z スライスを取る
    rot = np.asarray(G("vol_rotate")(tube, -tilt, axes=(0, 1), order=1, reshape=False,
                                     mode="constant", cval=0.0))
    stations = list(range(40, 137, 2))
    rows = []
    for zc in stations:
        naive = tube[zc]                                     # 素朴な軸方向(z)断面
        ortho = rot[zc]                                      # 軸に直交する断面
        # 直交断面の添字は、回転後は軸に沿った座標そのもの
        s_ortho = zc - ctr
        # 素朴な z 断面が軸と交わるのは s = (zc - ctr) / cos(tilt)
        s_naive = (zc - ctr) / az
        truth_d = 2.0 * float(radius_at(s_ortho)) * sp
        truth_naive_major = 2.0 * float(radius_at(s_naive)) * sp / az
        rows.append({
            "z": zc,
            "s_ortho_voxel": s_ortho, "s_naive_voxel": s_naive,
            "naive_major_mm": _extent_50(naive, 0, sp),
            "naive_minor_mm": _extent_50(naive, 1, sp),
            "ortho_major_mm": _extent_50(ortho, 0, sp),
            "ortho_minor_mm": _extent_50(ortho, 1, sp),
            "truth_diameter_mm": truth_d,
            "truth_naive_major_mm": truth_naive_major,
        })
    for r in rows[::8]:
        log(f"    z {r['z']:3d}  直交断面 {r['ortho_major_mm']:.3f} x "
            f"{r['ortho_minor_mm']:.3f} mm (真値 {r['truth_diameter_mm']:.3f})  "
            f"素朴断面 長径 {r['naive_major_mm']:.3f} mm "
            f"(楕円の理論値 {r['truth_naive_major_mm']:.3f})")
    ortho_err = [abs(r["ortho_minor_mm"] - r["truth_diameter_mm"]) for r in rows]
    naive_err = [abs(r["naive_major_mm"] - r["truth_diameter_mm"]) for r in rows]
    naive_model_err = [abs(r["naive_major_mm"] - r["truth_naive_major_mm"]) for r in rows]
    log(f"    素朴断面の長径 vs 楕円モデル 2r/cos: 平均 "
        f"{np.mean(naive_model_err):.4f} mm 最大 {max(naive_model_err):.4f} mm")
    log(f"    直交断面の短径 誤差 平均 {np.mean(ortho_err):.4f} mm 最大 {max(ortho_err):.4f} mm")
    log(f"    素朴断面の長径 誤差 平均 {np.mean(naive_err):.4f} mm 最大 {max(naive_err):.4f} mm")
    i_min = int(np.argmin([r["truth_diameter_mm"] for r in rows]))
    log(f"    狭窄の最小内径 真値 {rows[i_min]['truth_diameter_mm']:.4f} mm  "
        f"直交断面で {rows[i_min]['ortho_minor_mm']:.4f} mm  "
        f"素朴断面で {rows[i_min]['naive_major_mm']:.4f} mm")

    W, H = 1120, 664
    ps = 258
    PX0, PX1, PX2, TX = 18, 292, 566, 848
    PY = 90
    frames = []
    for i, r in enumerate(rows):
        zc = r["z"]
        c = _canvas(W, H)
        c = _header(c, "管の走行に沿って断面を送る ―― 軸に直交して切らないと太る",
                    f"z-y 面内で {tilt:.0f}° 傾いた合成管(中央に狭窄あり、"
                    f"spacing {sp} mm/voxel)。断面を軸に沿って送る。")
        # 側面図(管の走行と、いま切っている場所)
        side = tube[:, :, int(round(ctr))]
        c, s_side = _slice_panel(c, side, PX0, PY, ps, "gray", border=C_C)
        # 素朴な z 断面(水平線)と、軸に直交する断面(軸に垂直な線)を重ねる
        c = imagedraw.draw_line(c, (PX0, PY + zc * s_side),
                                (PX0 + ps - 1, PY + zc * s_side), color=C_E, width=1)
        y_ax = ctr + (zc - ctr) * math.tan(th)      # その z における軸の y 座標
        L = 46.0
        c = imagedraw.draw_line(
            c, (PX0 + (y_ax - L * math.cos(th)) * s_side,
                PY + (zc + L * math.sin(th)) * s_side),
            (PX0 + (y_ax + L * math.cos(th)) * s_side,
             PY + (zc - L * math.sin(th)) * s_side),
            color=C_D, width=2)
        c = imagedraw.draw_markers(c, [(PX0 + y_ax * s_side, PY + zc * s_side)],
                                   color=(1, 1, 1), size=4, shape="cross", width=1)
        c, s2 = _slice_panel(c, tube[zc], PX1, PY, ps, "gray", border=C_E)
        c, _ = _slice_panel(c, rot[zc], PX2, PY, ps, "gray", border=C_D)
        cy = PY + ps + 6
        c = _text(c, [
            (PX0, cy, "側面図 vol[:, :, x=%d]" % int(round(ctr)), C_C, 13, True),
            (PX0, cy + 20, "横 = y ->   縦 = z (下向き)", C_DIM, 11, False),
            (PX0, cy + 37, "ローズ = 素朴な z 断面 / ミント = 直交断面", C_DIM, 11, False),
            (PX1, cy, "素朴な軸方向断面 vol[z=%d]" % zc, C_E, 13, True),
            (PX1, cy + 20, "長径 %.3f / 短径 %.3f mm"
             % (r["naive_major_mm"], r["naive_minor_mm"]), C_E, 12, True),
            (PX1, cy + 37, "楕円の理論値 2r/cos = %.3f mm" % r["truth_naive_major_mm"],
             C_DIM, 11, False),
            (PX2, cy, "管の軸に直交する断面", C_D, 13, True),
            (PX2, cy + 20, "長径 %.3f / 短径 %.3f mm"
             % (r["ortho_major_mm"], r["ortho_minor_mm"]), C_D, 12, True),
            (PX2, cy + 37, "真の内径 %.3f mm" % r["truth_diameter_mm"], C_DIM, 11, False),
        ])
        c = _text(c, [
            (TX, PY + 4, "いまの断面", C_DIM, 12, False),
            (TX, PY + 22, "z = %3d" % zc, C_TEXT, 22, True),
            (TX, PY + 56, "真の内径", C_DIM, 12, False),
            (TX, PY + 74, "%.3f mm" % r["truth_diameter_mm"], C_TEXT, 20, True),
            (TX, PY + 106, "直交断面 短径", C_D, 12, True),
            (TX, PY + 124, "%.3f mm (差 %+.3f)"
             % (r["ortho_minor_mm"], r["ortho_minor_mm"] - r["truth_diameter_mm"]),
             C_D, 15, True),
            (TX, PY + 152, "素朴断面 長径", C_E, 12, True),
            (TX, PY + 170, "%.3f mm (差 %+.3f)"
             % (r["naive_major_mm"], r["naive_major_mm"] - r["truth_diameter_mm"]),
             C_E, 15, True),
            (TX, PY + 202, "素朴断面は 1/cos(%.0f deg)" % tilt, C_DIM, 12, False),
            (TX, PY + 219, "= %.3f 倍に伸びる。" % (1 / math.cos(th)), C_DIM, 12, False),
            (TX, PY + 236, "狭窄が浅く見える。", C_DIM, 12, False),
            (TX, PY + 264, "全 %d 断面の平均誤差" % len(rows), C_DIM, 12, False),
            (TX, PY + 282, "直交 %.4f mm" % float(np.mean(ortho_err)), C_D, 13, True),
            (TX, PY + 300, "素朴 %.4f mm" % float(np.mean(naive_err)), C_E, 13, True),
        ])
        p = Plot(c, 76, 452, W - 116, 152, (rows[0]["z"], rows[-1]["z"]), (1.0, 5.8),
                 xlabel="断面の位置 z(voxel)->",
                 xticks=[40, 60, 80, 100, 120, 136],
                 yticks=[1.5, 2.5, 3.5, 4.5, 5.5], xfmt="%d", yfmt="%.1f")
        p.series([x["z"] for x in rows], [x["truth_diameter_mm"] for x in rows],
                 (0.72, 0.74, 0.78), width=5)
        p.series([x["z"] for x in rows], [x["ortho_minor_mm"] for x in rows], C_D, width=2)
        p.series([x["z"] for x in rows], [x["naive_major_mm"] for x in rows], C_E, width=2)
        p.marker(zc, r["ortho_minor_mm"], C_D, size=6)
        p.marker(zc, r["naive_major_mm"], C_E, size=6)
        p.items.append((30, 436, "縦 = 測った内径 [mm]", C_DIM, 11, False))
        p.items.append((200, 436, "灰(太)= 真の内径", C_DIM, 11, True))
        p.items.append((330, 436, "ミント = 軸に直交する断面(短径)", C_D, 11, True))
        p.items.append((560, 436, "ローズ = 素朴な軸方向断面(長径)", C_E, 11, True))
        p.items.append((800, 436, "狭窄の最小内径 真値 %.3f -> 直交 %.3f / 素朴 %.3f mm"
                        % (rows[i_min]["truth_diameter_mm"],
                           rows[i_min]["ortho_minor_mm"],
                           rows[i_min]["naive_major_mm"]), C_TEXT, 11, True))
        c = p.done()
        c = _footer(c, "使用 op: vol_rotate  — 合成データ(反エイリアス管)", y_off=20)
        frames.append(c)

    info = _save_clip(frames, "wing3d_vessel_reslice", fps=10, thumb_index=i_min, log=log)
    return {
        "name": "wing3d_vessel_reslice",
        "title": "管に沿って切る ―― 軸に直交しないと内径が %.2f 倍に太る" % (1 / math.cos(th)),
        "ops": ["vol_rotate"],
        "facts": {"tilt_deg": tilt, "spacing_mm": sp, "stations": len(rows),
                  "rows": rows,
                  "ortho_mean_err_mm": float(np.mean(ortho_err)),
                  "ortho_max_err_mm": float(max(ortho_err)),
                  "naive_mean_err_mm": float(np.mean(naive_err)),
                  "naive_max_err_mm": float(max(naive_err)),
                  "naive_vs_ellipse_model_mean_err_mm": float(np.mean(naive_model_err)),
                  "naive_vs_ellipse_model_max_err_mm": float(max(naive_model_err)),
                  "stenosis_truth_mm": rows[i_min]["truth_diameter_mm"],
                  "stenosis_ortho_mm": rows[i_min]["ortho_minor_mm"],
                  "stenosis_naive_mm": rows[i_min]["naive_major_mm"]},
        "caption": (f"{tilt:.0f}° 傾いた合成管(中央に狭窄)を {len(rows)} 断面ぶん送る。"
                    "軸に直交する断面で測った短径は真の内径をほぼそのまま返す"
                    f"(平均誤差 **{float(np.mean(ortho_err)):.4f} mm**)のに、素朴に "
                    "z 方向へ切った断面の長径は 1/cos θ = "
                    f"**{1 / math.cos(th):.3f} 倍**に伸びて平均 "
                    f"{float(np.mean(naive_err)):.4f} mm ずれる。狭窄部では真値 "
                    f"{rows[i_min]['truth_diameter_mm']:.3f} mm が素朴断面では "
                    f"{rows[i_min]['naive_major_mm']:.3f} mm ―― 狭窄が浅く見えてしまう。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 15 — 連結性 6 / 18 / 26 と inner / outer(タイルで比べる)                  #
# --------------------------------------------------------------------------- #
def ex_connectivity(log) -> dict:
    """同じ球の殻を 6 通りの設定で取り、``contact_sheet`` で 1 枚に束ねる。"""
    n = 96
    r = 30.0
    ball = (_aa_ball((n, n, n), (48., 48., 48.), r) > 0.5).astype(np.float64)
    solid = int(ball.sum())
    variants, panels, labels = [], [], []
    R = _rot(28.0, 20.0)
    center = np.array([48.0, 48.0, 48.0])
    ps = 300
    rng = np.random.default_rng(SEED)
    for side in ("inner", "outer"):
        for conn in (6, 18, 26):
            sh = np.asarray(G("vol_boundary")(ball, connectivity=conn, side=side))
            cnt = int(sh.sum())
            pct = 100.0 * cnt / solid
            variants.append({"side": side, "connectivity": conn, "voxels": cnt,
                             "pct_of_solid": pct})
            log(f"    side={side:5s} conn={conn:2d} -> {cnt:6d} voxel  {pct:5.2f} %")
            pts = np.argwhere(sh > 0.5).astype(np.float64)
            if pts.shape[0] > 16000:
                pts = pts[np.sort(rng.choice(pts.shape[0], 16000, replace=False))]
            # 半分に切って殻の「厚み」が見えるようにする(手前側を削ぐ)
            keep = pts[:, 1] <= 48.0
            pts = pts[keep]
            panel = _canvas(ps, ps, C_PANEL)
            u, v, d = _project(pts[:, [2, 1, 0]], R, 3.6, ps / 2, ps / 2,
                               center[[2, 1, 0]])
            _splat(panel, u, v, d, C_B if side == "inner" else C_A, radius=1, shade=0.55)
            panel = _axis_gizmo(panel, R, 38, ps - 38, size=24)
            panels.append(panel)
            labels.append("side='%s'  connectivity=%d  ->  %d voxel (%.2f %%)"
                          % (side, conn, cnt, pct))

    sheet = et.contact_sheet(
        panels, labels, ncols=3, panel_px=300,
        title="vol_boundary の 6 通り ― 同じ球(%d voxel)の殻を、"
              "触れ方の定義だけ変えて取る(手前半分を切って厚みを見せている)" % solid,
        title_font_size=20, font_size=15)
    info = _save_png(sheet, "wing3d_boundary_connectivity", log)
    thin = variants[0]; thick = variants[5]
    return {
        "name": "wing3d_boundary_connectivity",
        "title": "連結性の定義だけで殻の厚みが %.1f 倍変わる" % (
            thick["voxels"] / thin["voxels"]),
        "ops": ["vol_boundary"],
        "facts": {"solid_voxels": solid, "radius_voxel": r, "variants": variants},
        "caption": (f"半径 {r:.0f} voxel の合成球({solid:,} voxel)の殻を、`vol_boundary` の "
                    "`connectivity`(6 / 18 / 26)と `side`(inner / outer)だけ変えて 6 通り"
                    f"取った。面だけ触れる 6 近傍の内側殻は {thin['voxels']:,} voxel"
                    f"({thin['pct_of_solid']:.2f} %)、斜めの接触も数える 26 近傍の外側殻は "
                    f"{thick['voxels']:,} voxel({thick['pct_of_solid']:.2f} %)で、"
                    f"**同じ形なのに {thick['voxels'] / thin['voxels']:.2f} 倍**違う。"
                    "「表面のボクセル数」という言い方が定義抜きでは意味を持たない、"
                    "という 6 枚。手前半分を切って厚みが見えるようにしてある。"),
        **info}


# --------------------------------------------------------------------------- #
# 展示 16 — 計測パイプラインのフリップブック                                      #
# --------------------------------------------------------------------------- #
def ex_pipeline(log) -> dict:
    """CT から寸法が出るまでの 7 工程を ``flipbook`` でコマ送りにする。"""
    # 視野は広く、対象は隅に(実際の CT と同じ構図 — crop の効きが見えるように)
    n = 176
    sp = (0.6, 0.6, 0.6)
    # 枝は主管の**軸上**から生やす(外すと連結成分が分かれ、細線化がただの直線になる)
    parts = [((18, 70, 46), (106, 70, 46), 8.0),
             ((50, 70, 46), (50, 30, 96), 5.0),
             ((86, 70, 46), (86, 112, 96), 4.0)]
    obj = np.zeros((n, n, n), bool)
    for p0, p1, rr in parts:
        obj |= _capsule((n, n, n), p0, p1, rr)
    # 「CT らしさ」— HU 値を振り、ノイズを乗せる(seed 固定)
    rng = np.random.default_rng(SEED)
    hu = np.where(obj, 900.0, -1000.0)
    hu = hu + rng.normal(0.0, 60.0, hu.shape)

    steps = []
    win = np.asarray(G("vol_window_level")(hu, 300.0, 1600.0))
    binv = (win > 0.62).astype(np.float64)
    lab, nlab = G("vol_label")(binv, connectivity=26)
    lab = np.asarray(lab)
    props = G("vol_region_props")(lab, spacing=sp)
    biggest = max(props, key=lambda p: p["voxel_count"])
    keep = (lab == biggest["label"]).astype(np.float64)
    part, off = G("vol_crop_domain")(keep, keep, margin=2)
    part = np.asarray(part)
    sk_part = np.asarray(G("skeletonize_vol")(part))
    sk = np.asarray(G("vol_uncrop")(sk_part.astype(np.float64), off, keep.shape))
    dt = np.asarray(G("vol_distance_transform")(keep, spacing=sp))
    ep = np.asarray(G("skeleton_endpoints3d")(sk > 0.5))
    ju = np.asarray(G("skeleton_junctions3d")(sk > 0.5))
    br = np.asarray(G("skeleton_branches3d")(sk > 0.5))
    import scipy.ndimage as ndi
    st = np.ones((3, 3, 3), int)
    n_br = ndi.label(br, structure=st)[1]
    n_ep = ndi.label(ep, structure=st)[1]
    n_ju = ndi.label(ju, structure=st)[1]
    max_r = float(dt.max())
    log(f"    labels {nlab}  largest {biggest['voxel_count']:,} voxel "
        f"= {biggest['volume']:.1f} mm^3  sphericity {biggest['sphericity']:.4f}")
    log(f"    crop {keep.shape} -> {part.shape}  "
        f"memory 1/{keep.nbytes / part.nbytes:.1f}")
    log(f"    skeleton {int(sk.sum())} voxel  branches {n_br} endpoints {n_ep} "
        f"junctions {n_ju}   max inscribed radius {max_r:.4f} mm")

    # --- 同じ寸法のコマを作る(flipbook は寸法不一致を例外にする) ---
    FW, FH = 900, 496            # パネル 400 + 下に説明 3 行(はみ出さない高さ)
    pw = 400
    zc = 50                      # 枝が 1 本出ている高さ(工程の違いが見える断面)
    center = np.array([n / 2.0] * 3)
    Rv = _rot(32.0, 20.0)

    def frame(slice_img, cmap_name, pts, pts_col, note_lines, extra=None):
        c = _canvas(FW, FH, C_BG)
        from PIL import Image
        im = Image.fromarray(_to_u8(_cmap(np.clip(slice_img, 0, 1), cmap_name))).resize(
            (pw, pw), Image.NEAREST)
        _paste(c, np.asarray(im, np.float64) / 255.0, 14, 14)
        c = imagedraw.draw_polyline(
            c, [(14, 14), (14 + pw - 1, 14), (14 + pw - 1, 14 + pw - 1), (14, 14 + pw - 1)],
            color=C_RULE, width=1, closed=True)
        _fill(c, 428, 14, 428 + pw, 14 + pw, C_PANEL)
        sub = c[14:14 + pw, 428:428 + pw]
        for p, col, rad in (extra or []):
            if p is not None and len(p):
                uu, vv, dd = _project(p[:, [2, 1, 0]], Rv, 2.9, pw / 2, pw / 2,
                                      center[[2, 1, 0]])
                _splat(sub, uu, vv, dd, col, radius=rad, shade=0.4)
        if pts is not None and len(pts):
            uu, vv, dd = _project(pts[:, [2, 1, 0]], Rv, 2.9, pw / 2, pw / 2,
                                  center[[2, 1, 0]])
            _splat(sub, uu, vv, dd, pts_col, radius=1, shade=0.5)
        c = imagedraw.draw_polyline(
            c, [(428, 14), (428 + pw - 1, 14), (428 + pw - 1, 14 + pw - 1),
                (428, 14 + pw - 1)], color=C_RULE, width=1, closed=True)
        c = _axis_gizmo(c, Rv, 428 + 40, 14 + pw - 40, size=26)
        c = _text(c, [(18, 18, "断面 z = %d" % zc, C_DIM, 12, True),
                      (432, 18, "3-D(点で表示)", C_DIM, 12, True)])
        items = []
        for i, s in enumerate(note_lines):
            items.append((14, 14 + pw + 8 + i * 18, s, C_TEXT if i == 0 else C_DIM,
                          13 if i == 0 else 12, i == 0))
        return _text(c, items)

    def sample(mask, k=14000):
        p = np.argwhere(mask).astype(np.float64)
        if p.shape[0] > k:
            p = p[np.sort(rng.choice(p.shape[0], k, replace=False))]
        return p

    dt_col = _cmap(np.clip(dt[keep > 0.5] / max_r, 0, 1), "rainbow")
    dt_pts = np.argwhere(keep > 0.5).astype(np.float64)
    if dt_pts.shape[0] > 14000:
        pick = np.sort(rng.choice(dt_pts.shape[0], 14000, replace=False))
        dt_pts, dt_col = dt_pts[pick], dt_col[pick]

    steps = [
        frame(_norm01(hu[zc], -1200, 1400), "gray", sample(hu > 300.0), (0.55, 0.57, 0.62),
              ["1. 入力 — 合成 CT(HU、ガウスノイズ sigma 60)",
               "%d^3 voxel, spacing %.1f mm。まだ「物」ではなく数字の塊。" % (n, sp[0]),
               "この段階の閾値は決めていない。"]),
        frame(win[zc], "gray", sample(win > 0.62), C_A,
              ["2. vol_window_level(center 300 HU / width 1600 HU)",
               "HU を [0,1] に写す。黒潰れ %.1f %% / 白飛び %.1f %%。"
               % (100 * (win <= 0).mean(), 100 * (win >= 1).mean()),
               "窓を決めた時点で、あとの二値化の意味が決まる。"]),
        frame(binv[zc], "gray", sample(binv > 0.5), C_A,
              ["3. 二値化 + vol_label(26 連結)",
               "連結成分 %d 個。ノイズ由来の小片が混ざっている。" % nlab,
               "最大成分は %d voxel = %.1f mm^3。"
               % (biggest["voxel_count"], biggest["volume"])]),
        frame(keep[zc], "gray", sample(keep > 0.5), C_D,
              ["4. 最大成分だけ残す(vol_region_props で選ぶ)",
               "体積 %.1f mm^3 / 表面積 %.1f mm^2 / 球形度 %.4f"
               % (biggest["volume"], biggest["surface_area"], biggest["sphericity"]),
               "重心 (z,y,x) = (%.1f, %.1f, %.1f) voxel"
               % tuple(biggest["centroid"])]),
        frame(keep[zc], "gray", sample(keep > 0.5), C_D,
              ["5. vol_crop_domain — 処理領域だけ持ち歩く",
               "%s -> %s、メモリ 1/%.1f。offset (z,y,x) = %s"
               % (tuple(keep.shape), tuple(part.shape),
                  keep.nbytes / part.nbytes, tuple(off)),
               "以降の重い op はこの小さい箱の中だけで動く。"]),
        frame(np.clip(keep[zc] * 0.25 + (sk[zc] > 0.5) * 1.0, 0, 1), "gray",
              np.argwhere(sk > 0.5).astype(np.float64), (0.95, 0.96, 0.94),
              ["6. skeletonize_vol — 1 voxel 幅の針金へ",
               "%d voxel -> %d voxel(%.2f %%)。枝 %d / 分岐 %d / 端点 %d。"
               % (int(keep.sum()), int(sk.sum()), 100 * sk.sum() / keep.sum(),
                  n_br, n_ju, n_ep),
               "つながり方(トポロジー)はここで確定する。"],
              extra=[(sample(keep > 0.5, 9000), (0.20, 0.22, 0.26), 1)]),
        frame(_norm01(dt[zc], 0, max_r), "rainbow", None, C_B,
              ["7. vol_distance_transform — 局所の太さを mm で読む",
               "最大内接半径 %.4f mm(いちばん太い管の真値 %.3f mm、差 %+.4f mm)"
               % (max_r, parts[0][2] * sp[0], max_r - parts[0][2] * sp[0]),
               "虹は 0 mm(紫)から %.2f mm(赤)。ここまで来て初めて寸法になる。" % max_r],
              extra=[(dt_pts, dt_col, 1)]),
    ]
    labels = ["入力(合成 CT)", "vol_window_level", "二値化 + vol_label",
              "最大成分を選ぶ", "vol_crop_domain", "skeletonize_vol",
              "vol_distance_transform"]
    book = et.flipbook(steps, labels,
                       title="CT のかたまりが寸法になるまで ― 3-D 計測の 7 工程",
                       font_size=19, title_font_size=23)
    res = et.save_animation(book, "wing3d_pipeline_flow",
                            duration_ms=1500, hold_last_ms=2600)
    log(f"    gif  {os.path.basename(res['gif'])}  {res['frames']} frames  "
        f"{res['size'][0]}x{res['size'][1]}  {res['gif_bytes'] / 1e6:.2f} MB")
    info = {"kind": "gif", "gif": res["gif"], "mp4": None, "thumb": res["thumb"],
            "frames": res["frames"], "fps": None,
            "gif_shape": (res["size"][1], res["size"][0], 3),
            "mp4_shape": None, "gif_colors": None,
            "gif_bytes": res["gif_bytes"], "mp4_bytes": 0,
            "thumb_bytes": os.path.getsize(res["thumb"]), "thumb_frame": 0,
            "gif_sha256": res["gif_sha256"], "mp4_sha256": None}
    return {
        "name": "wing3d_pipeline_flow",
        "title": "CT のかたまりが寸法になるまで(7 工程)",
        "ops": ["vol_window_level", "vol_label", "vol_region_props", "vol_crop_domain",
                "vol_uncrop", "skeletonize_vol", "skeleton_branches3d",
                "skeleton_endpoints3d", "skeleton_junctions3d",
                "vol_distance_transform"],
        "facts": {"shape": [n, n, n], "spacing_mm": list(sp), "labels": int(nlab),
                  "largest_voxels": int(biggest["voxel_count"]),
                  "largest_volume_mm3": float(biggest["volume"]),
                  "largest_surface_mm2": float(biggest["surface_area"]),
                  "sphericity": float(biggest["sphericity"]),
                  "crop_shape": list(part.shape),
                  "crop_memory_ratio": float(keep.nbytes / part.nbytes),
                  "skeleton_voxels": int(sk.sum()), "branches": int(n_br),
                  "endpoints": int(n_ep), "junctions": int(n_ju),
                  "max_inscribed_radius_mm": max_r,
                  "truth_radius_mm": parts[0][2] * sp[0]},
        "caption": (f"ノイズ付きの合成 CT({n}³、spacing {sp[0]} mm)が寸法になるまでの 7 工程を"
                    "コマ送りに束ねた。窓 → 二値化 → ラベリング(連結成分 "
                    f"{nlab} 個)→ 最大成分({biggest['volume']:.1f} mm³、球形度 "
                    f"{biggest['sphericity']:.4f})→ `vol_crop_domain` でメモリ "
                    f"**1/{keep.nbytes / part.nbytes:.1f}** → 細線化(枝 {n_br} / 分岐 "
                    f"{n_ju} / 端点 {n_ep})→ 距離変換で最大内接半径 "
                    f"**{max_r:.4f} mm**(真値 {parts[0][2] * sp[0]:.3f} mm)。"
                    "各コマに工程名と進捗が焼いてあるので、止めた 1 コマでも読める。"),
        **info}


# --------------------------------------------------------------------------- #
# 一覧と実行                                                                     #
# --------------------------------------------------------------------------- #
_EXHIBITS = [
    ("domain", ex_domain),
    ("boundary", ex_boundary),
    ("rle", ex_rle),
    ("windowing", ex_windowing),
    ("vesselness", ex_vesselness),
    ("skeleton", ex_skeleton),
    ("wall", ex_wall),
    ("rl", ex_rl),
    ("visualhull", ex_visual_hull),
    ("obb", ex_obb),
    ("icp", ex_icp),
    ("anisotropic", ex_anisotropic),
    ("mip", ex_mip),
    ("distance", ex_distance),
    ("connectivity", ex_connectivity),
    ("pipeline", ex_pipeline),
    # 断層(断面を段階的に動かす)シリーズ — このウィングの中核
    ("zsweep", ex_slice_zsweep),
    ("mpr", ex_mpr),
    ("oblique", ex_oblique),
    ("windowsweep", ex_window_sweep),
    ("isosurface", ex_isosurface),
    ("vessel", ex_vessel_reslice),
]


def _md_line(m: dict) -> str:
    """記事と同じ書式の展示 1 点(画像 Markdown + 斜体キャプション)。

    版面は ``exhibit_tile`` に任せる — 静止画は「サムネイル + クリックで原寸」、
    GIF は動いてこそなので直接埋め込み。
    """
    ops = ", ".join("`%s`" % o for o in m["ops"])
    cap = f"**{m['title']}** ―― {m['caption']} 使用 op: {ops}。"
    if m["kind"] == "gif":
        return et.markdown_animation(m["name"], m["title"], cap).rstrip("\n")
    return et.markdown(m["name"], m["title"], cap).rstrip("\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Qiita 記事「紙面の科学館」3D 計測ウィングの展示を生成する")
    ap.add_argument("--exhibits", default="all",
                    help="カンマ区切りの展示名(既定 all)")
    ap.add_argument("--list", action="store_true", help="展示名を並べて終了")
    args = ap.parse_args(argv)

    if args.list:
        for name, fn in _EXHIBITS:
            print("%-12s %s" % (name, (fn.__doc__ or "").strip().splitlines()[0]
                                if fn.__doc__ else ""))
        return 0

    wanted = ([n for n, _ in _EXHIBITS] if args.exhibits == "all"
              else [s.strip() for s in args.exhibits.split(",") if s.strip()])
    unknown = [w for w in wanted if w not in dict(_EXHIBITS)]
    if unknown:
        print("unknown exhibit(s): %s" % ", ".join(unknown), file=sys.stderr)
        return 2

    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(MEDIA, exist_ok=True)
    os.makedirs(THUMBS, exist_ok=True)
    os.makedirs(EXHIBITS, exist_ok=True)

    def log(s):
        print(s, flush=True)

    results = []
    t_all = time.perf_counter()
    for name, fn in _EXHIBITS:
        if name not in wanted:
            continue
        log(f"[{name}]")
        t = time.perf_counter()
        meta = fn(log)
        meta["exhibit"] = name
        meta["seconds"] = time.perf_counter() - t
        results.append(meta)
        log(f"    done in {meta['seconds']:.1f} s")

    # メタ(既存分は残してマージ — 一部だけ再生成しても壊れないように)
    old = {}
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, encoding="utf-8") as fh:
                for m in json.load(fh).get("exhibits", []):
                    old[m["exhibit"]] = m
        except Exception:
            old = {}
    for m in results:
        old[m["exhibit"]] = m
    ordered = [old[n] for n, _ in _EXHIBITS if n in old]
    with open(META_PATH, "w", encoding="utf-8") as fh:
        json.dump({"generated_by": "tools/gen_wing3d_gallery.py", "seed": SEED,
                   "exhibits": ordered}, fh, ensure_ascii=False, indent=2,
                  default=lambda o: (o.tolist() if isinstance(o, np.ndarray)
                                     else (bool(o) if isinstance(o, np.bool_)
                                           else float(o))))
    log(f"meta -> {META_PATH}")

    # キャプション原稿
    lines = [
        "# 3D 計測ウィング ―― 紙面の科学館",
        "",
        "本ファイルは `tools/gen_wing3d_gallery.py` が **実行結果から自動生成**して"
        "います(手で数値を書き換えないでください)。",
        "図に焼き込んだ数字はすべてその場の計算結果で、素材は合成データのみです"
        "(実データ・AI 生成素材は使っていません)。",
        "",
        f"生成: seed `{SEED}` 固定 / `py -3.11 tools/gen_wing3d_gallery.py`",
        "",
        "---",
        "",
        "### 3D 計測ウィング ―― ボクセルと点群を「測る」ための op",
        "",
    ]
    for m in ordered:
        lines.append(_md_line(m))
        lines.append("")
    lines += ["---", "", "## 生成物の実測(読み戻して確認した値)", "",
              "| 展示 | 形式 | ファイル | 実測 |", "|---|---|---|---|"]
    for m in ordered:
        if m["kind"] == "gif":
            extra = ""
            if m.get("gif_colors"):
                extra += ", %d 色" % m["gif_colors"]
            if m.get("mp4_bytes"):
                extra += ", mp4 %.2f MB" % (m["mp4_bytes"] / 1e6)
            lines.append("| %s | %s | `media/%s.gif` | %d フレーム, %dx%d, %.2f MB%s |"
                         % (m["exhibit"], "GIF+mp4" if m.get("mp4_bytes") else "GIF",
                            m["name"], m["frames"],
                            m["gif_shape"][1], m["gif_shape"][0],
                            m["gif_bytes"] / 1e6, extra))
        else:
            lines.append("| %s | PNG | `%s.png` | %dx%d, %.0f kB |"
                         % (m["exhibit"], m["name"], m["png_size"][0],
                            m["png_size"][1], m["png_bytes"] / 1e3))
    lines.append("")
    with open(CAPTION_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    log(f"captions -> {CAPTION_PATH}")
    log(f"total {time.perf_counter() - t_all:.1f} s for {len(results)} exhibit(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
