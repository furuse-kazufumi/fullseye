# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wingconv_gallery — 記事の「表現変換ウィング」展示を作る。

``tools/gen_wing1d_gallery.py`` と同じ流儀:

  * **数字はすべてその場で op を呼んで得た実測値**。図に焼く値に決め打ちは 1 つも無い。
  * **描画は fullseye 自身の ``imagedraw`` op と numpy 合成のみ**(matplotlib 不使用)。
    文字だけは fullseye にテキスト描画 op が無いため PIL の ``ImageDraw.text``。
  * **決定的**。乱数は seed 固定、幾何も固定なので再生成でバイト列が一致する
    (``--verify`` で 2 回作って SHA-256 を突き合わせる)。
  * **アニメは静止 1 コマだけで意味が分かる**ように、軸・単位・凡例・現在値を
    毎フレーム焼き込む(``exhibit_tile.flipbook`` が工程名と ``i/N`` を足す)。

このウィングの主張は 1 つ ―― **変換の嘘は往復で露見する**。だから主役は
「A → B → A' を並べ、最後のコマに残差と誤差の数値を焼いた GIF」で、可逆なものは
**残差が真っ黒 = 誤差 0.0** が目で見える形になっている。

展示は 8 点(GIF 5 / PNG 3):

  1. ``roundtrip_normals``   GIF  法線 → 方位・仰角[度] → 法線。残差は真っ黒
  2. ``roundtrip_curvature`` GIF  主曲率 → 形状指数 → 主曲率。臍点でも真っ黒
  3. ``roundtrip_keypoints`` GIF  keypoints → 画素格子 → keypoints(**不可逆**)
  4. ``roundtrip_gaussians`` GIF  点群 → ガウシアン → 体積(**不可逆**、質量で測る)
  5. ``cross_loop``          GIF  voxel → mesh → points → gaussians → voxel の一周
  6. ``flow_colorwheel``     PNG  死んだ型 ``flow`` が「見える」ようになった(凡例つき)
  7. ``axis_unit_traps``     PNG  軸・単位・spacing の取り違え(**誤り例**と明記)
  8. ``dead_vocabulary``     PNG  袋小路の型 25 → 9(台帳の機械集計)

使い方::

    py -3.11 tools/gen_wingconv_gallery.py                     # 全部
    py -3.11 tools/gen_wingconv_gallery.py --only cross_loop
    py -3.11 tools/gen_wingconv_gallery.py --verify            # 決定性の検査
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

import imagedraw                                              # noqa: E402
import opsreprconv                                            # noqa: E402
import reprconv as R                                          # noqa: E402
from exhibit_tile import (contact_sheet, flipbook, markdown,   # noqa: E402
                          markdown_animation, save_animation, save_exhibit)

ASSETS = os.path.join(_ROOT, "docs", "articles", "assets")
MEDIA = os.path.join(ASSETS, "media")
EXHIBITS = os.path.join(_ROOT, "docs", "articles", "exhibits")
PREFIX = "wingconv"

# 配色 — 赤緑の対で意味を担わせない(色覚に依らず読める組み合わせ)
C_BG = (0.055, 0.062, 0.075)
C_PANEL = (0.098, 0.108, 0.128)
C_TEXT = (0.87, 0.88, 0.85)
C_DIM = (0.52, 0.55, 0.59)
C_OK = (0.35, 0.72, 1.00)      # 可逆・正しい経路(青)
C_WARN = (0.98, 0.72, 0.25)    # 不可逆・誤り例(琥珀)
C_ACC = (0.72, 0.55, 0.98)     # 補助(紫)

TILE = 240          # 1 タイルの一辺 [px]
PAD = 18
HEAD = 58           # 表題の帯
FOOT = 92           # 数値の帯

_FONT_CACHE: dict = {}


def _font(size=13, bold=False):
    key = (size, bold)
    if key not in _FONT_CACHE:
        from PIL import ImageFont
        path = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except OSError:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def _jp_font(size=13, bold=False):
    """日本語を焼くときだけ使う(等幅にならないので数値には使わない)。"""
    key = ("jp", size, bold)
    if key not in _FONT_CACHE:
        from PIL import ImageFont
        for path in (r"C:\Windows\Fonts\meiryob.ttc" if bold else r"C:\Windows\Fonts\meiryo.ttc",
                     r"C:\Windows\Fonts\YuGothM.ttc", r"C:\Windows\Fonts\msgothic.ttc"):
            try:
                _FONT_CACHE[key] = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
        else:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


# --------------------------------------------------------------------------- #
# 色付け(matplotlib は使わない。全部 numpy)                                    #
# --------------------------------------------------------------------------- #
def cmap_gray(a, lo=None, hi=None):
    a = np.asarray(a, float)
    lo = float(np.min(a)) if lo is None else lo
    hi = float(np.max(a)) if hi is None else hi
    t = np.zeros_like(a) if hi <= lo else np.clip((a - lo) / (hi - lo), 0, 1)
    return np.dstack([t, t, t])


def cmap_diverging(a, span=None):
    """0 を中央にした発散配色(青 - 灰 - 琥珀)。**符号つき量はこれで見る**。"""
    a = np.asarray(a, float)
    s = float(np.max(np.abs(a))) if span is None else float(span)
    t = np.clip(a / s, -1, 1) if s > 0 else np.zeros_like(a)
    neg, pos = np.clip(-t, 0, 1), np.clip(t, 0, 1)
    base = np.full(a.shape + (3,), 0.20)
    return np.clip(base + neg[..., None] * (np.array(C_OK) - 0.20)
                   + pos[..., None] * (np.array(C_WARN) - 0.20), 0, 1)


def cmap_cyclic(deg, value=None):
    """周期量(方位[度])の配色。**色相環が一周する**ことが要件。"""
    h = (np.asarray(deg, float) % 360.0) / 60.0
    v = np.ones_like(h) if value is None else np.clip(np.asarray(value, float), 0, 1)
    i = np.floor(h).astype(np.int64) % 6
    f = h - np.floor(h)
    p, q, t = np.zeros_like(v), v * (1 - f), v * f
    sel = [i == k for k in range(6)]
    r = np.select(sel, [v, q, p, p, t, v])
    g = np.select(sel, [t, v, v, q, p, p])
    b = np.select(sel, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)


def _fit(rgb, side=TILE):
    """任意サイズの RGB を一辺 side の正方タイルへ(最近傍で等方拡大/縮小)。"""
    rgb = np.asarray(rgb, float)
    if rgb.ndim == 2:
        rgb = np.dstack([rgb] * 3)
    h, w = rgb.shape[:2]
    s = min(side / h, side / w)
    nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    yi = np.clip((np.arange(nh) / s).astype(np.int64), 0, h - 1)
    xi = np.clip((np.arange(nw) / s).astype(np.int64), 0, w - 1)
    small = rgb[yi][:, xi]
    out = np.full((side, side, 3), C_PANEL, float)
    y0, x0 = (side - nh) // 2, (side - nw) // 2
    out[y0:y0 + nh, x0:x0 + nw] = np.clip(small, 0, 1)
    return out


def _scatter(pts_uv, extent, side=TILE, color=C_OK, size=3):
    """(N,2) の (u, v) を正方タイルに散布する(``imagedraw.draw_markers`` 経由)."""
    u0, u1, v0, v1 = extent
    ink = np.zeros((side, side), float)
    if len(pts_uv):
        p = np.asarray(pts_uv, float)
        x = (p[:, 0] - u0) / max(u1 - u0, 1e-12) * (side - 1)
        y = (p[:, 1] - v0) / max(v1 - v0, 1e-12) * (side - 1)
        keep = (x >= 0) & (x < side) & (y >= 0) & (y < side)
        if keep.any():
            ink = imagedraw.draw_markers(ink, np.stack([x[keep], y[keep]], 1),
                                         color=1.0, size=size, shape="cross", width=1)
    out = np.full((side, side, 3), C_PANEL, float)
    m = ink > 0.5
    out[m] = np.asarray(color, float)
    return out


def _frame(title, tiles, captions, footer_lines, foot_colors=None):
    """1 コマ = 表題 + 横並びタイル + 各タイルの下の 1 行 + 数値の帯。

    全コマで同じ寸法になるよう、タイル数を固定して呼ぶこと
    (``flipbook`` は寸法が揃っていないと例外にする)。
    """
    from PIL import Image, ImageDraw

    n = len(tiles)
    w = PAD + n * (TILE + PAD)
    h = HEAD + TILE + 26 + FOOT
    canvas = np.full((h, w, 3), C_BG, float)
    for i, t in enumerate(tiles):
        x = PAD + i * (TILE + PAD)
        canvas[HEAD:HEAD + TILE, x:x + TILE] = _fit(t)
    im = Image.fromarray(np.clip(canvas * 255 + 0.5, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im)
    d.text((w // 2, HEAD // 2), title, fill=tuple(int(c * 255) for c in C_TEXT),
           font=_jp_font(17, True), anchor="mm")
    for i, cap in enumerate(captions):
        x = PAD + i * (TILE + PAD) + TILE // 2
        d.text((x, HEAD + TILE + 13), cap, fill=tuple(int(c * 255) for c in C_DIM),
               font=_jp_font(12), anchor="mm")
    y = HEAD + TILE + 32
    cols = foot_colors or [C_TEXT] * len(footer_lines)
    for line, col in zip(footer_lines, cols):
        d.text((PAD, y), line, fill=tuple(int(c * 255) for c in col), font=_font(13))
        y += 18
    return np.asarray(im, np.float64) / 255.0


def _legend_wheel(side=120):
    """色相環の凡例。**色の意味を書かないフロー図は綺麗なだけで読めない**。"""
    yy, xx = np.mgrid[0:side, 0:side].astype(float) - (side - 1) / 2.0
    r = np.hypot(yy, xx) / ((side - 1) / 2.0)
    rgb = cmap_cyclic(np.degrees(np.arctan2(yy, xx)), np.clip(r, 0, 1))
    rgb[r > 1.0] = np.asarray(C_BG)
    return rgb


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _gif(frames, labels, stem, title, log, duration_ms=900, hold_last_ms=2200):
    book = flipbook(frames, labels, title=title)
    info = save_animation(book, f"{PREFIX}_{stem}", duration_ms=duration_ms,
                          hold_last_ms=hold_last_ms)
    log(f"    gif {info['frames']} frames {info['size']} {info['gif_bytes'] / 1e6:.3f} MB")
    return {"kind": "GIF", "frames": info["frames"],
            "shape": (info["size"][1], info["size"][0]),
            "bytes": info["gif_bytes"], "sha256": info["gif_sha256"],
            "path": f"docs/articles/assets/media/{PREFIX}_{stem}.gif",
            "thumb": f"docs/articles/assets/thumbs/{PREFIX}_{stem}_thumb.jpg"}


def _png(image, stem, log):
    info = save_exhibit(image, f"{PREFIX}_{stem}")
    log(f"    png {info['size']} {info['png_bytes'] / 1e6:.3f} MB")
    return {"kind": "PNG", "frames": 1, "shape": (info["size"][1], info["size"][0]),
            "bytes": info["png_bytes"], "sha256": info["png_sha256"],
            "path": f"docs/articles/assets/{PREFIX}_{stem}.png",
            "thumb": f"docs/articles/assets/{PREFIX}_{stem}_thumb.jpg"}


# --------------------------------------------------------------------------- #
# 共通の合成データ(**閉形式の真値が分かっているものだけ**を使う)               #
# --------------------------------------------------------------------------- #
def _bumpy_surface(n=96):
    """既知の解析式で作った高さ場。法線も曲率も閉形式で照合できる。"""
    y, x = np.mgrid[0:n, 0:n].astype(float) / (n - 1) * 2.0 - 1.0
    return 0.35 * np.exp(-(x ** 2 + y ** 2) * 4.0) - 0.22 * np.exp(
        -((x - 0.55) ** 2 + (y + 0.5) ** 2) * 16.0), y, x


def _surface_normals(z):
    """高さ場 z(H,W)の単位法線 (N,3)、成分順 (n0, n1, n2) = (dy 方向, dx 方向, 上)。"""
    gy, gx = np.gradient(z)
    v = np.stack([-gy, -gx, np.ones_like(z)], -1).reshape(-1, 3)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


# --------------------------------------------------------------------------- #
# 1. 法線 ⇄ 方位・仰角[度](可逆。残差は真っ黒)                                 #
# --------------------------------------------------------------------------- #
def build_roundtrip_normals(log):
    z, _, _ = _bumpy_surface(96)
    n = _surface_normals(z)
    h, w = z.shape

    ang = R.normals_to_angles(n)
    back = R.angles_to_normals(ang)
    err = np.linalg.norm(back - n, axis=1)
    max_abs = float(np.max(np.abs(back - n)))

    az = ang[:, 0].reshape(h, w)
    el = ang[:, 1].reshape(h, w)
    t_in = (n.reshape(h, w, 3) + 1.0) / 2.0
    t_az = cmap_cyclic(az)
    t_el = cmap_diverging(el, span=90.0)
    t_out = (back.reshape(h, w, 3) + 1.0) / 2.0
    t_err = cmap_gray(err.reshape(h, w), 0.0, 1.0)          # ★ 固定スケール

    facts = {"n_normals": int(n.shape[0]), "max_abs": max_abs,
             "max_angle_error_deg": float(np.degrees(np.max(np.arccos(
                 np.clip(np.sum(back * n, 1), -1, 1))))),
             "az_range_deg": [float(az.min()), float(az.max())],
             "el_range_deg": [float(el.min()), float(el.max())]}

    common = [f"normals (N,3) -> pairs [az, el] deg -> normals   N = {n.shape[0]}",
              "az = atan2(c1, c0) in (-180, 180]   el = asin(c2/|v|) in [-90, 90]"]
    frames = [
        _frame("① 入力: 法線 (N,3) ―― 袋小路だった型",
               [t_in, np.full((8, 8, 3), C_PANEL), np.full((8, 8, 3), C_PANEL)],
               ["法線を RGB で(=(v+1)/2)", "", ""],
               common + ["出口 0 / 入口 2 —— ここから他の型へ行く単入力 op が無かった"],
               [C_TEXT, C_TEXT, C_WARN]),
        _frame("② 変換: 方位[度] と 仰角[度] の対 (N,2)",
               [t_in, t_az, t_el],
               ["法線", "方位 az(色相環=一周)", "仰角 el(青 -90 / 琥珀 +90)"],
               common + [f"az in [{az.min():+7.2f}, {az.max():+7.2f}] deg    "
                         f"el in [{el.min():+7.2f}, {el.max():+7.2f}] deg"],
               [C_TEXT, C_TEXT, C_TEXT]),
        _frame("③ 逆変換: 対 (N,2) から法線を組み直す",
               [t_az, t_el, t_out], ["方位", "仰角", "復元した法線"],
               common + ["c = cos(el);  v = (c cos(az), c sin(az), sin(el))"],
               [C_TEXT, C_TEXT, C_TEXT]),
        _frame("④ 残差 ―― 可逆なら真っ黒になる(0 を黒、1 を白の固定スケール)",
               [t_in, t_out, t_err], ["入力", "復元", "|入力 - 復元|(0..1 固定)"],
               [f"max|Δ| = {max_abs:.3e}          "
                f"最大の角度差 = {facts['max_angle_error_deg']:.3e} deg",
                "残差の絵は自動スケールにしていない ―― 自動にすると倍精度の丸めが",
                "「模様」に見えてしまい、可逆なのに壊れているように読める"],
               [C_OK, C_DIM, C_DIM]),
    ]
    info = _gif(frames, ["入力(袋小路の型)", "方位・仰角へ", "組み直す", "残差 = 真っ黒"],
                "roundtrip_normals",
                "可逆な変換 ―― 法線 ⇄ 方位・仰角[度]", log)
    return info, facts


# --------------------------------------------------------------------------- #
# 2. 主曲率 ⇄ 形状指数(臍点を含めて可逆)                                       #
# --------------------------------------------------------------------------- #
def build_roundtrip_curvature(log):
    """閉形式の真値つき: 球・鞍・円柱・平面のパッチを並べる。"""
    n = 96
    k1 = np.zeros((n, n))
    k2 = np.zeros((n, n))
    q = n // 2
    k1[:q, :q], k2[:q, :q] = 1.0, 1.0          # 球(臍点) S = +1
    k1[:q, q:], k2[:q, q:] = 1.0, -1.0         # 鞍          S =  0
    k1[q:, :q], k2[q:, :q] = 0.8, 0.0          # 円柱        S = +0.5
    k1[q:, q:], k2[q:, q:] = 0.0, 0.0          # 平面        S =  0, C = 0
    # 各パッチに滑らかな変調を掛けて「一様な四角」に見えないようにする
    yy, xx = np.mgrid[0:n, 0:n].astype(float) / (n - 1)
    mod = 0.75 + 0.5 * np.sin(6.0 * np.pi * xx) * np.sin(6.0 * np.pi * yy)
    k1, k2 = k1 * mod, k2 * mod
    k = np.stack([np.maximum(k1, k2).ravel(), np.minimum(k1, k2).ravel()], 1)

    si = R.curvature_to_shape_index(k)
    back = R.shape_index_to_curvature(si)
    max_abs = float(np.max(np.abs(back - k)))
    err = np.max(np.abs(back - k), axis=1).reshape(n, n)

    umbilic = int(np.count_nonzero(np.isclose(k[:, 0], k[:, 1])))
    span = float(np.max(np.abs(k)))
    tiles = {
        "k1": cmap_diverging(k[:, 0].reshape(n, n), span),
        "k2": cmap_diverging(k[:, 1].reshape(n, n), span),
        "S": cmap_diverging(si[:, 0].reshape(n, n), 1.0),
        "C": cmap_gray(si[:, 1].reshape(n, n), 0.0, span),
        "k1b": cmap_diverging(back[:, 0].reshape(n, n), span),
        "err": cmap_gray(err, 0.0, 1.0),
    }
    truth = [(("球  (k1=k2= 1)", (1.0, 1.0))), (("杯  (k1=k2=-1)", (-1.0, -1.0))),
             (("鞍  (k1=1, k2=-1)", (1.0, -1.0))), (("稜  (k1=1, k2= 0)", (1.0, 0.0)))]
    truth_lines = []
    for lbl, kk in truth:
        s, c = R.curvature_to_shape_index(np.array([kk]))[0]
        truth_lines.append(f"  {lbl:20s} -> S = {s:+.6f}   C = {c:.6f}")

    facts = {"n_points": int(k.shape[0]), "umbilic_or_flat": umbilic,
             "max_abs": max_abs,
             "closed_form": {lbl: list(map(float, R.curvature_to_shape_index(
                 np.array([kk]))[0])) for lbl, kk in truth}}

    common = ["curvature (N,2)=[k1,k2] -> pairs [S, C] -> curvature",
              "S = (2/pi) atan2(k1+k2, k1-k2)     C = sqrt((k1^2+k2^2)/2)"]
    frames = [
        _frame("① 入力: 主曲率の対(球・鞍・円柱・平面の 4 パッチ)",
               [tiles["k1"], tiles["k2"], np.full((8, 8, 3), C_PANEL)],
               ["k1(発散配色)", "k2(発散配色)", ""],
               common + [f"臍点・平面(k1 == k2)を {umbilic} 点 / {k.shape[0]} 点 含む ―― "
                         "**除算で書いた式はここでだけ NaN を出す**"],
               [C_TEXT, C_TEXT, C_WARN]),
        _frame("② 変換: 形状指数 S と 曲がり C(Koenderink & van Doorn 1992)",
               [tiles["k1"], tiles["S"], tiles["C"]],
               ["k1", "形状指数 S in [-1,1]", "曲がり C >= 0"],
               common + truth_lines[:2], [C_TEXT, C_OK, C_OK]),
        _frame("③ 閉形式の真値と突き合わせる",
               [tiles["S"], tiles["C"], tiles["k1b"]],
               ["S", "C", "S,C から戻した k1"], common + truth_lines[2:],
               [C_TEXT, C_OK, C_OK]),
        _frame("④ 残差 ―― 臍点でも平面でも真っ黒(atan2 形だから)",
               [tiles["k1"], tiles["k1b"], tiles["err"]],
               ["入力 k1", "復元 k1", "max|Δ| per point(0..1 固定)"],
               [f"max|Δ| = {max_abs:.3e}   ({k.shape[0]} 点、うち臍点・平面 {umbilic} 点)",
                "教科書の atan((k1+k2)/(k1-k2)) をそのまま実装すると臍点で NaN が出て、",
                "その NaN は下流で「暗い画素」に化けて誰も気づけない"],
               [C_OK, C_DIM, C_DIM]),
    ]
    info = _gif(frames, ["主曲率の対", "形状指数へ", "戻す", "残差 = 真っ黒"],
                "roundtrip_curvature",
                "可逆な変換 ―― 主曲率 ⇄ 形状指数(臍点を含めて厳密)", log)
    return info, facts


# --------------------------------------------------------------------------- #
# 3. keypoints ⇄ 画素格子(**不可逆**。落ちる量を数字で)                        #
# --------------------------------------------------------------------------- #
def build_roundtrip_keypoints(log):
    from scipy.spatial import cKDTree

    rng = np.random.default_rng(3)
    side = 128
    g = np.stack(np.meshgrid(np.arange(3.0, 122.0, 4.0),
                             np.arange(3.0, 122.0, 4.0), indexing="ij"), -1).reshape(-1, 2)
    kp = g + rng.uniform(-0.5, 0.5, size=g.shape)
    img = R.keypoints_to_image2d(kp, shape=(side, side))
    back = R.keypoints_from_image2d(img)
    _, j = cKDTree(back).query(kp, k=1)
    axis_rms = float(np.sqrt(np.mean((back[j] - kp) ** 2)))
    dist_rms = float(np.sqrt(np.mean(np.sum((back[j] - kp) ** 2, 1))))

    rng2 = np.random.default_rng(4)
    kp_r = rng2.random((120, 2)) * 110.0 + 6.0
    img_r = R.keypoints_to_image2d(kp_r, shape=(side, side))
    back_r = R.keypoints_from_image2d(img_r)

    ext = (0.0, float(side), 0.0, float(side))
    t_in = _scatter(kp, ext, color=C_OK)
    t_img = cmap_gray(img, 0.0, 1.0)
    t_out = _scatter(back, ext, color=C_WARN)
    t_in_r = _scatter(kp_r, ext, color=C_OK)
    t_out_r = _scatter(back_r, ext, color=C_WARN)

    facts = {"separated_n": int(kp.shape[0]), "separated_back_n": int(back.shape[0]),
             "axis_rms_px": axis_rms, "dist_rms_px": dist_rms,
             "axis_theory_px": 1.0 / math.sqrt(12.0),
             "dist_theory_px": math.sqrt(2.0 / 12.0),
             "random_n": int(kp_r.shape[0]), "random_back_n": int(back_r.shape[0])}

    common = ["keypoints (N,2)=(u,v) -> image2d (H,W) -> keypoints",
              "行 = round(v)、列 = round(u)(**軸の約束が op 名に書いてある**)"]
    frames = [
        _frame("① 入力: 4 px 間隔に置いた keypoints(融合しない配置)",
               [t_in, np.full((8, 8, 3), C_PANEL), np.full((8, 8, 3), C_PANEL)],
               [f"{kp.shape[0]} 点(副画素位置)", "", ""],
               common + ["融合と量子化は**別の損失**なので、混ぜて測らない"],
               [C_TEXT, C_TEXT, C_WARN]),
        _frame("② 変換: 画素格子に落とす(ここで副画素の位置が消える)",
               [t_in, t_img, np.full((8, 8, 3), C_PANEL)],
               ["入力 keypoints", f"計数画像 {side}x{side}", ""],
               common + [f"非零画素 {int((img > 0).sum())} 個 = 入力 {kp.shape[0]} 点"],
               [C_TEXT, C_TEXT, C_TEXT]),
        _frame("③ 逆変換: 連結成分の強度重み付き重心で拾い直す",
               [t_in, t_img, t_out], ["入力", "計数画像", "復元 keypoints"],
               common + [f"点数 {kp.shape[0]} -> {back.shape[0]}(融合なし)"],
               [C_TEXT, C_TEXT, C_TEXT]),
        _frame("④ 不可逆 ―― 落ちた量は一様量子化の理論値と一致する",
               [t_in, t_out, cmap_gray(np.abs(img - R.keypoints_to_image2d(
                   back, shape=(side, side))), 0.0, 1.0)],
               ["入力", "復元", "計数画像の差(真っ黒 = 同じ画素)"],
               [f"軸あたり RMS = {axis_rms:.4f} px   "
                f"理論 1/sqrt(12) = {1 / math.sqrt(12):.4f} px",
                f"2-D 距離 RMS = {dist_rms:.4f} px   "
                f"理論 sqrt(2/12) = {math.sqrt(2 / 12):.4f} px",
                "★軸あたりと距離を混ぜると、正しい実装が誤って見える(実際に一度読み違えた)"],
               [C_WARN, C_WARN, C_DIM]),
        _frame("⑤ もう 1 つの損失 ―― 近い 2 点は 8 近傍で融合する",
               [t_in_r, cmap_gray(img_r, 0.0, 1.0), t_out_r],
               [f"ランダム {kp_r.shape[0]} 点", "計数画像", f"復元 {back_r.shape[0]} 点"],
               [f"点数 {kp_r.shape[0]} -> {back_r.shape[0]} "
                f"({kp_r.shape[0] - back_r.shape[0]} 点が融合)",
                "量子化(位置がずれる)と融合(点が消える)は**別の損失**。",
                "1 つの RMS にまとめると、どちらがどれだけ効いたか言えなくなる"],
               [C_WARN, C_DIM, C_DIM]),
    ]
    info = _gif(frames, ["離した点", "画素格子へ", "拾い直す", "量子化の損失", "融合の損失"],
                "roundtrip_keypoints",
                "不可逆な変換 ―― keypoints ⇄ 画素格子(落ちる量を測る)", log)
    return info, facts


# --------------------------------------------------------------------------- #
# 4. 点群 → ガウシアン → 体積(質量で測る不可逆)                                #
# --------------------------------------------------------------------------- #
def build_roundtrip_gaussians(log):
    rng = np.random.default_rng(5)
    n = 48
    # 既知の螺旋 —— 位置が閉形式で分かっている点群
    t = np.linspace(0.0, 4.0 * np.pi, 260)
    pts = np.stack([n / 2 + 9.0 * t / (4 * np.pi) - 4.5,
                    n / 2 + 9.0 * np.cos(t), n / 2 + 9.0 * np.sin(t)], 1)
    g = R.points_to_gaussians(pts, k=4)
    back = R.gaussians_to_points(g)
    exact = float(np.max(np.abs(back - pts)))

    vol = R.gaussians_to_voxel(g, shape=(n, n, n), truncate=3.0)
    box = math.erf(3.0 / math.sqrt(2.0)) ** 3
    one = {"mu": np.array([[8.0, 8.0, 8.0]]), "sigma": np.array([1.5]), "w": np.array([1.0])}
    conv = [(sp, float(R.gaussians_to_voxel(one, shape=(int(round(16 / sp)),) * 3,
                                            spacing=(sp,) * 3).sum()))
            for sp in (1.0, 0.5, 0.25, 0.125)]

    def mip(v, axis=0):
        return cmap_gray(v.max(axis=axis), 0.0, float(v.max()))

    ext = (0.0, float(n), 0.0, float(n))
    t_pts = _scatter(pts[:, [2, 1]], ext, color=C_OK, size=3)
    t_sig = _scatter(pts[:, [2, 1]], ext, color=C_ACC, size=5)
    t_vol = mip(vol, 0)
    t_vol1 = mip(vol, 1)

    facts = {"n_points": int(pts.shape[0]), "centres_max_abs": exact,
             "sigma_median": float(np.median(g["sigma"])),
             "weight_sum": float(g["w"].sum()), "voxel_mass": float(vol.sum()),
             "box_truncation_theory": box, "convergence": conv,
             "ball_truncation_wrong_value": float(
                 math.erf(3 / math.sqrt(2)) - math.sqrt(2 / math.pi) * 3 * math.exp(-4.5))}

    common = ["points (N,3) -> gaussians {mu, sigma, w} -> voxel (D,H,W)",
              "sigma は k 近傍の平均距離、w は 1/N の等分(3DGS の初期化と同じ)"]
    frames = [
        _frame("① 入力: 既知の螺旋(**産む op が 1 つも無かった型へ入る**)",
               [t_pts, np.full((8, 8, 3), C_PANEL), np.full((8, 8, 3), C_PANEL)],
               [f"{pts.shape[0]} 点 (x-y 投影)", "", ""],
               common + ["gaussians は消費側(to_points)だけがあり、入口が無かった —— "
                         "入口の無い型は一度も実行されない"],
               [C_TEXT, C_TEXT, C_WARN]),
        _frame("② 変換: 局所間隔から sigma を決める",
               [t_pts, t_sig, np.full((8, 8, 3), C_PANEL)],
               ["点群", "ガウシアン(sigma で拡大)", ""],
               common + [f"sigma 中央値 = {np.median(g['sigma']):.4f} voxel   "
                         f"重み和 = {g['w'].sum():.6f}",
                         f"中心 mu は入力そのもの ―― 往復 max|Δ| = {exact:.3e}(bit 一致)"],
               [C_TEXT, C_OK, C_OK]),
        _frame("③ 変換: 密度体積へ焼く(2 方向の最大値投影で見る)",
               [t_sig, t_vol, t_vol1], ["ガウシアン", "MIP(軸 0)", "MIP(軸 1)"],
               common + [f"体積の総質量 = {vol.sum():.4f}(重み和 {g['w'].sum():.4f} に対して)"],
               [C_TEXT, C_TEXT, C_TEXT]),
        _frame("④ 不可逆 ―― 落ちた質量を数字で(★一度間違えた値の訂正つき)",
               [t_vol, t_vol1, _legend_mass(conv, box)],
               ["MIP(軸 0)", "MIP(軸 1)", "刻みを細かくすると"],
               [f"3σ の**箱**打ち切りの理論値 erf(3/√2)^3 = {box * 100:.3f}%",
                "  刻み " + " / ".join(f"{s}:{m * 100:.2f}%" for s, m in conv)
                + "  と単調に収束",
                f"★最初「3σ の**球** {facts['ball_truncation_wrong_value'] * 100:.2f}%」と"
                "書いたが、実装は箱。刻みを細かくして反証した"],
               [C_OK, C_DIM, C_WARN]),
    ]
    info = _gif(frames, ["点群", "ガウシアンへ", "体積へ焼く", "落ちた質量"],
                "roundtrip_gaussians",
                "不可逆な変換 ―― 点群 → ガウシアン → 体積(質量で測る)", log)
    return info, facts


def _legend_mass(conv, box, side=TILE):
    """刻み vs 質量の収束を棒で描く小さな図(``imagedraw`` で線を引く)。"""
    ink = np.zeros((side, side), float)
    lo, hi = box * 100.0 - 0.05, max(m for _, m in conv) * 100.0 + 0.15
    for i, (_, m) in enumerate(conv):
        x = 26 + i * 52
        y = side - 34 - (m * 100.0 - lo) / (hi - lo) * (side - 74)
        ink = imagedraw.draw_line(ink, (x, side - 34), (x, y), color=1.0, width=9)
    out = np.full((side, side, 3), C_PANEL, float)
    out[ink > 0.5] = np.asarray(C_WARN)
    ln = np.zeros((side, side), float)
    yb = side - 34 - (box * 100.0 - lo) / (hi - lo) * (side - 74)
    ln = imagedraw.draw_line(ln, (10, yb), (side - 10, yb), color=1.0, width=2)
    out[ln > 0.5] = np.asarray(C_OK)
    return out


# --------------------------------------------------------------------------- #
# 5. ★表現をまたいで一周(変換の連鎖こそが嘘の出る場所)                         #
# --------------------------------------------------------------------------- #
def build_cross_loop(log):
    import ops3d

    n = 40
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n].astype(float)
    c, r = (n - 1) / 2.0, n * 0.30
    # 球からトーラス状の窪みを削った形(対称すぎると「戻った」が自明になる)
    ball = ((zz - c) ** 2 + (yy - c) ** 2 + (xx - c) ** 2 <= r ** 2)
    notch = ((np.abs(zz - c) < 2.5) & ((yy - c) ** 2 + (xx - c) ** 2 > (r * 0.45) ** 2))
    vox = (ball & ~notch).astype(float)
    v_true = float(vox.sum())

    verts, faces = ops3d.OPS3D["voxel_to_mesh"]["func"](vox, 0.5)[:2]
    area = float(ops3d.OPS3D["mesh_area"]["func"]((verts, faces)))
    pts = np.asarray(verts, float)                     # 頂点をそのまま点群に(決定的)
    cen_pts = R.points_to_position(pts)
    g = R.points_to_gaussians(pts, k=6)
    back = R.gaussians_to_voxel(g, shape=(n, n, n), truncate=3.0)
    thr = 0.5 * float(np.percentile(back[back > 0], 90))
    shell = back > thr
    cen_vox = R.points_to_position(np.argwhere(vox > 0.5).astype(float))
    cen_back = R.points_to_position(np.argwhere(shell).astype(float))

    def mip(v):
        return cmap_gray(v.max(axis=0), 0.0, float(v.max()))

    ext = (0.0, float(n), 0.0, float(n))
    t_vox = mip(vox)
    t_mesh = _scatter(np.asarray(verts)[:, [2, 1]], ext, color=C_ACC, size=2)
    t_pts = _scatter(pts[:, [2, 1]], ext, color=C_OK, size=2)
    t_g = _scatter(g["mu"][:, [2, 1]], ext, color=C_ACC, size=3)
    t_back = mip(back)
    t_shell = cmap_gray(shell.max(axis=0).astype(float), 0.0, 1.0)

    facts = {"start_volume_voxel": v_true, "mesh_vertices": int(len(verts)),
             "mesh_faces": int(len(faces)), "mesh_area": area,
             "points": int(pts.shape[0]), "sigma_median": float(np.median(g["sigma"])),
             "shell_voxel": int(shell.sum()), "mass": float(back.sum()),
             "centroid_start": list(cen_vox), "centroid_points": list(cen_pts),
             "centroid_end": list(cen_back),
             "centroid_shift": float(np.linalg.norm(
                 np.asarray(cen_back) - np.asarray(cen_vox)))}

    head = "voxel -> mesh -> points -> gaussians -> voxel(4 つの表現を一周する)"
    frames = [
        _frame("① voxel ―― 出発(中身の詰まった立体)",
               [t_vox, np.full((8, 8, 3), C_PANEL), np.full((8, 8, 3), C_PANEL)],
               ["MIP(軸 0)", "", ""],
               [head, f"体積 = {v_true:.0f} voxel   "
                      f"重心 = ({cen_vox[0]:.3f}, {cen_vox[1]:.3f}, {cen_vox[2]:.3f})"],
               [C_TEXT, C_TEXT]),
        _frame("② mesh ―― **ここで中身が消える**(表面だけになる)",
               [t_vox, t_mesh, np.full((8, 8, 3), C_PANEL)],
               ["voxel", f"頂点 {len(verts)} / 面 {len(faces)}", ""],
               [head, f"表面積 = {area:.1f}。体積は持たなくなった —— "
                      "以後「体積」を語ったらそれは嘘"],
               [C_TEXT, C_WARN]),
        _frame("③ points ―― 面の接続と法線が消える(頂点の集合になる)",
               [t_mesh, t_pts, np.full((8, 8, 3), C_PANEL)],
               ["mesh", f"{pts.shape[0]} 点 (z,y,x)", ""],
               [head, f"重心 = ({cen_pts[0]:.3f}, {cen_pts[1]:.3f}, {cen_pts[2]:.3f})"],
               [C_TEXT, C_TEXT]),
        _frame("④ gaussians ―― 局所間隔から広がりが**足される**(損失ではない)",
               [t_pts, t_g, np.full((8, 8, 3), C_PANEL)],
               ["points", f"sigma 中央 {np.median(g['sigma']):.3f}", ""],
               [head, f"重み和 = {g['w'].sum():.6f}(単位は「重み」であって「体積」ではない)"],
               [C_TEXT, C_ACC]),
        _frame("⑤ voxel ―― 一周した。だが戻ったのは**殻**であって立体ではない",
               [t_vox, t_back, t_shell],
               ["出発 (MIP)", "一周後の密度 (MIP)", "しきい値後の殻"],
               [head,
                f"体積 {v_true:.0f} voxel -> 殻 {int(shell.sum())} voxel"
                f"   質量 = {back.sum():.4f}",
                f"重心のずれ = {facts['centroid_shift']:.4f} voxel "
                f"(**一致する指標**と**しない指標**を両方出す)"],
               [C_TEXT, C_WARN, C_OK]),
    ]
    info = _gif(frames, ["voxel", "mesh(中身が消える)", "points(接続が消える)",
                         "gaussians(広がりが足される)", "voxel(殻が戻る)"],
                "cross_loop",
                "表現をまたいで一周 ―― 何が残り、何が消えるか", log,
                duration_ms=1200, hold_last_ms=2600)
    return info, facts


# --------------------------------------------------------------------------- #
# 6. flow が「見える」ようになった(凡例つき)                                    #
# --------------------------------------------------------------------------- #
def build_flow_colorwheel(log):
    """密なシーンフローの標準的な可視化。**色の意味の凡例を必ず焼く**。"""
    n = 96
    d = 24
    zz, yy, xx = np.mgrid[0:d, 0:n, 0:n].astype(float)
    cy, cx = (n - 1) / 2.0, (n - 1) / 2.0
    ry, rx = yy - cy, xx - cx
    rad = np.hypot(ry, rx) + 1e-9
    # 既知の場: 渦(回転) + 湧き出し(発散) + z 方向の一様並進
    swirl = np.exp(-(rad / (n * 0.30)) ** 2)
    vy = (-rx / rad) * swirl * 3.0 + (ry / rad) * swirl * 1.2
    vx = (ry / rad) * swirl * 3.0 + (rx / rad) * swirl * 1.2
    vz = np.full_like(vy, 0.8)
    flow = np.stack([vz, vy, vx])

    mag = R.flow_magnitude(flow)
    rgb = R.flow_to_rgbimage(flow, index=d // 2)
    slice_mag = np.hypot(vy[d // 2], vx[d // 2])

    scattered = np.stack([vz[0].ravel()[:400], vy[0].ravel()[:400],
                          vx[0].ravel()[:400]], 1)
    speed = R.flow_speed(scattered)

    wheel = _legend_wheel(TILE)
    facts = {"flow_shape": list(flow.shape), "mag_max": float(mag.max()),
             "slice_mag_max": float(slice_mag.max()),
             "hue_at_plus_x_deg": float(np.degrees(np.arctan2(0.0, 1.0)) % 360.0),
             "scattered_speed_mean": float(speed.mean()),
             "dense_ops": ["flow_magnitude", "flow_to_rgbimage"],
             "scattered_ops": ["flow_speed", "flow_apply"]}

    panels = [
        cmap_gray(mag[d // 2], 0.0, float(mag.max())),
        rgb,
        wheel,
        cmap_gray(np.abs(vy[d // 2]), 0.0, float(np.abs(vy).max())),
    ]
    labels = [
        f"|v| の大きさだけ(最大 {mag.max():.3f})",
        "色相 = 面内の向き / 明度 = 面内の速さ",
        "凡例: 色相環(角度 = 向き、半径 = 速さ)",
        "面内 1 成分だけ(dz は捨てている)",
    ]
    sheet = contact_sheet(panels, labels, ncols=2, panel_px=330,
                          title="死んだ型 flow が「見える」ようになった "
                                "―― 大きさ・向き・凡例")
    info = _png(sheet, "flow_colorwheel", log)
    return info, facts


# --------------------------------------------------------------------------- #
# 7. 軸・単位・spacing の取り違え(**誤り例**と明記)                             #
# --------------------------------------------------------------------------- #
def build_axis_unit_traps(log):
    n = 64
    # (a) (u,v) を (v,u) と読む
    tt = np.linspace(0.0, 2.0 * np.pi, 200)
    kp = np.stack([32.0 + 24.0 * np.cos(tt), 32.0 + 8.0 * np.sin(tt)], 1)
    right = R.keypoints_to_image2d(kp, shape=(n, n))
    wrong = R.keypoints_to_image2d(kp[:, ::-1], shape=(n, n))
    swap_shift = float(np.linalg.norm(
        np.asarray(R.points_to_position(R.keypoints_uv_to_points(kp)))
        - np.asarray(R.points_to_position(R.keypoints_uv_to_points(kp[:, ::-1])))))

    # (b) spacing を無視する
    g = {"mu": np.array([[10.0, 12.0, 14.0]]), "sigma": np.array([0.5]),
         "w": np.array([1.0])}
    ok = R.gaussians_to_voxel(g, shape=(24,) * 3, origin=(2.0,) * 3,
                              spacing=(2.0,) * 3, truncate=4.0)
    ng = R.gaussians_to_voxel(g, shape=(24,) * 3, truncate=4.0)
    p_ok = np.unravel_index(int(np.argmax(ok)), ok.shape)
    p_ng = np.unravel_index(int(np.argmax(ng)), ng.shape)

    # (c) 角度にラジアンを渡す
    base = np.zeros((n, n))
    base = imagedraw.draw_polyline(
        base, np.array([[16.0, 32.0], [48.0, 32.0], [48.0, 40.0], [16.0, 40.0]]),
        color=1.0, width=2, closed=True)
    pts2 = np.argwhere(base > 0.5).astype(float)          # (row, col)
    ctr = pts2.mean(0)

    def rot(deg_value):
        m = R.angle_to_matrix(deg_value)[1:, 1:]          # z 回転の面内 2x2
        q = (pts2 - ctr) @ m.T + ctr
        img = np.zeros((n, n))
        keep = (q[:, 0] >= 0) & (q[:, 0] < n) & (q[:, 1] >= 0) & (q[:, 1] < n)
        if keep.any():
            img = imagedraw.draw_markers(img, np.stack([q[keep, 1], q[keep, 0]], 1),
                                         color=1.0, size=1, shape="dot", width=1)
        return img

    deg_img = rot(30.0)
    rad_img = rot(math.radians(30.0))
    rad_back = R.matrix_to_angle(R.angle_to_matrix(math.radians(30.0)))

    # (d) 積算窓の取り違え
    cr = np.array([1.0e6])
    c_ms = float(R.countrate_to_counts(cr, 1e-3)[0])
    c_s = float(R.countrate_to_counts(cr, 1.0)[0])

    facts = {"uv_swap_centroid_shift": swap_shift,
             "spacing_peak_correct": [int(v) for v in p_ok],
             "spacing_peak_wrong": [int(v) for v in p_ng],
             "deg_30_recovered": float(R.matrix_to_angle(R.angle_to_matrix(30.0))),
             "rad_as_deg_recovered": float(rad_back),
             "counts_gate_1ms": c_ms, "counts_gate_1s": c_s,
             "counts_ratio": c_s / c_ms}

    panels = [
        cmap_gray(right, 0, 1), cmap_gray(wrong, 0, 1),
        cmap_gray(ok.max(0), 0, float(ok.max())), cmap_gray(ng.max(0), 0, float(ng.max())),
        cmap_gray(deg_img, 0, 1), cmap_gray(rad_img, 0, 1),
    ]
    labels = [
        "正: (u,v) = (列, 行)",
        f"★誤り例: (v,u) と読む(重心が {swap_shift:.1f} ずれる。例外は出ない)",
        f"正: origin/spacing を渡す → ピーク {tuple(int(v) for v in p_ok)}",
        f"★誤り例: spacing 既定のまま → ピーク {tuple(int(v) for v in p_ng)}",
        "正: 30 [度] を渡す",
        f"★誤り例: π/6 rad を「度」として渡す(復元 {rad_back:.4f} 度)",
    ]
    sheet = contact_sheet(panels, labels, ncols=2, panel_px=300,
                          title="軸・単位・spacing の取り違えは "
                                "**例外を出さずに**通る(★= 誤り例)")
    info = _png(sheet, "axis_unit_traps", log)
    return info, facts


# --------------------------------------------------------------------------- #
# 8. 死んだ語彙 25 → 9(台帳の機械集計)                                          #
# --------------------------------------------------------------------------- #
def build_dead_vocabulary(log):
    import collections

    import chain_fuzz

    base = chain_fuzz.catalog()

    def out_edges(ops):
        e = collections.defaultdict(set)
        for _, _, ins, out, _ in ops:
            if len(ins) == 1 and ins[0] != out:
                e[ins[0]].add(out)
        return e

    new = [(k, "rc", m["in"], m["out"], m["func"])
           for k, m in opsreprconv.OPSREPRCONV.items()]
    before, after = out_edges(base), out_edges(base + new)
    types = sorted({t for _, _, ins, out, _ in base + new for t in list(ins) + [out]})
    dead_b = [t for t in types if not before[t]]
    dead_a = [t for t in types if not after[t]]
    fixed = [t for t in dead_b if after[t]]

    facts = {"ops_before": len(base), "ops_after": len(base) + len(new),
             "pairs_before": sum(len(v) for v in before.values()),
             "pairs_after": sum(len(v) for v in after.values()),
             "dead_before": dead_b, "dead_after": dead_a, "fixed": fixed,
             "new_edges": {t: sorted(after[t]) for t in fixed}}

    from PIL import Image, ImageDraw
    w, h = 1180, 720
    im = Image.new("RGB", (w, h), tuple(int(c * 255) for c in C_BG))
    d = ImageDraw.Draw(im)
    tc = tuple(int(c * 255) for c in C_TEXT)
    dc = tuple(int(c * 255) for c in C_DIM)
    okc = tuple(int(c * 255) for c in C_OK)
    wc = tuple(int(c * 255) for c in C_WARN)

    d.text((w // 2, 30), "死んだ語彙 ―― 産む op はあるのに、そこから先へ行けない型",
           fill=tc, font=_jp_font(22, True), anchor="mm")
    d.text((w // 2, 60),
           f"台帳 {facts['ops_before']} op → {facts['ops_after']} op / "
           f"単入力の変換ペア {facts['pairs_before']} → {facts['pairs_after']} 種 / "
           f"出口 0 の型 {len(dead_b)} → {len(dead_a)} 個",
           fill=dc, font=_jp_font(15), anchor="mm")

    y0 = 100
    d.text((40, y0), f"出口ができた型 {len(fixed)} 個(reprconv が新設した辺)",
           fill=okc, font=_jp_font(16, True))
    for i, t in enumerate(fixed):
        yy = y0 + 30 + i * 26
        d.text((56, yy), f"{t:<12s}", fill=tc, font=_font(15, True))
        d.text((190, yy), "→  " + ", ".join(sorted(after[t])), fill=okc, font=_font(14))

    y1 = y0 + 30 + len(fixed) * 26 + 24
    d.text((40, y1), f"まだ出口が無い型 {len(dead_a)} 個(埋めなかった理由は台帳に書いてある)",
           fill=wc, font=_jp_font(16, True))
    d.text((56, y1 + 28), ", ".join(dead_a), fill=dc, font=_font(14))
    d.text((56, y1 + 54),
           "poly/bspline_surface = 正直な出口は「評価する」ことで既存 3 入力 op が持つ / "
           "gradient・hessian = flow と同じ計算になる /",
           fill=dc, font=_jp_font(12))
    d.text((56, y1 + 74),
           "roots = 順序を勝手に付けると周回積分が黙って間違う / "
           "axes・frame・graph = 中身を実測していない(実測せずに変換を書くのが一番危ない)",
           fill=dc, font=_jp_font(12))

    info = _png(np.asarray(im, np.float64) / 255.0, "dead_vocabulary", log)
    return info, facts


# --------------------------------------------------------------------------- #
EXHIBIT_ORDER = [
    ("roundtrip_normals", build_roundtrip_normals),
    ("roundtrip_curvature", build_roundtrip_curvature),
    ("roundtrip_keypoints", build_roundtrip_keypoints),
    ("roundtrip_gaussians", build_roundtrip_gaussians),
    ("cross_loop", build_cross_loop),
    ("flow_colorwheel", build_flow_colorwheel),
    ("axis_unit_traps", build_axis_unit_traps),
    ("dead_vocabulary", build_dead_vocabulary),
]

CAPTION_JA = {
    "roundtrip_normals": (
        "可逆な変換 ―― 法線 ⇄ 方位・仰角[度]",
        "袋小路だった `normals` に出口を作った。方位 az と仰角 el(**どちらも度**)へ"
        "変換し、そこから組み直すと {n_normals} 本の法線が **max|Δ| = {max_abs:.3e}**"
        "(角度差 {max_angle_error_deg:.3e} 度)で戻る。最後のコマの残差が真っ黒なのは"
        "「絵が暗い」のではなく **0..1 の固定スケールで 0** だからで、"
        "自動スケールにすると倍精度の丸めが模様に見えて可逆なのに壊れて見える。"),
    "roundtrip_curvature": (
        "可逆な変換 ―― 主曲率 ⇄ 形状指数(臍点を含めて厳密)",
        "球・鞍・円柱・平面の 4 パッチ({n_points} 点。うち臍点・平面 {umbilic_or_flat} 点)を"
        "形状指数 S と曲がり C へ移し、戻して **max|Δ| = {max_abs:.3e}**。"
        "教科書の `atan((k1+k2)/(k1-k2))` は臍点で 0 除算になるが、`atan2` 形で書けば"
        "球 S=+1・鞍 S=0・円柱 S=+0.5 が閉形式のまま全域で厳密に往復する。"),
    "roundtrip_keypoints": (
        "不可逆な変換 ―― keypoints ⇄ 画素格子(落ちる量を測る)",
        "4 px 間隔に置いた {separated_n} 点を計数画像へ焼いて拾い直すと、"
        "軸あたり RMS **{axis_rms_px:.4f} px**(一様量子化の理論 1/√12 = 0.2887)、"
        "2-D 距離 RMS {dist_rms_px:.4f} px(理論 √(2/12) = 0.4082)。"
        "ランダム配置なら {random_n} → {random_back_n} 点に融合する ―― "
        "**量子化(ずれる)と融合(消える)は別の損失**で、混ぜて 1 つの RMS にすると"
        "どちらがどれだけ効いたか言えなくなる。"),
    "roundtrip_gaussians": (
        "不可逆な変換 ―― 点群 → ガウシアン → 体積(質量で測る)",
        "**産む op が 1 つも無かった** `gaussians` に入口を作った。中心 mu は"
        "往復 max|Δ| = {centres_max_abs:.3e} で bit 一致し、sigma と w は"
        "往復で消える「追加された情報」。体積へ焼くと 3σ の**箱**打ち切りで"
        "**{box_truncation_theory:.5f}** が理論値 —— "
        "最初これを 3σ の**球** {ball_truncation_wrong_value:.4f} と書いたが、"
        "刻みを 1.0 → 0.125 と細かくすると箱の値へ収束して球へは近づかず、反証できた。"),
    "cross_loop": (
        "表現をまたいで一周 ―― 何が残り、何が消えるか",
        "voxel → mesh → points → gaussians → voxel。体積 {start_volume_voxel:.0f} voxel の"
        "立体は mesh の段で**中身を失い**({mesh_vertices} 頂点 / {mesh_faces} 面、"
        "表面積 {mesh_area:.1f})、points で接続と法線を失い、最後に戻るのは"
        "立体ではなく殻 {shell_voxel} voxel。一方で重心は {centroid_shift:.4f} voxel しか"
        "動かない。**一致する指標と一致しない指標を両方出す**のが正直な報告で、"
        "重心だけ見せると「一周して戻った」という嘘になる。"),
    "flow_colorwheel": (
        "死んだ型 `flow` が「見える」ようになった",
        "`flow` は単入力で産む op も食う op も無い完全な孤島だった。"
        "密なシーンフロー {flow_shape} を大きさ(voxel)と色相環(rgbimage)へ出す 2 つの"
        "出口を作り、**色の意味の凡例を同じ図に焼いた**。"
        "この repo の `flow` は (3,D,H,W) の密フローと (N,3) の散在フローが"
        "**同じ型名で同居している**ので、密用 {dense_ops} と散在用 {scattered_ops} で"
        "op を分け、相手の形は fail-closed にしてある。"),
    "axis_unit_traps": (
        "軸・単位・spacing の取り違えは例外を出さずに通る",
        "(u,v) を (v,u) と読むと重心が {uv_swap_centroid_shift:.1f} ずれ、"
        "spacing を既定のままにするとピークが {spacing_peak_correct} でなく"
        "{spacing_peak_wrong} に立ち、π/6 rad を「度」として渡すと"
        "{rad_as_deg_recovered:.4f} 度だけ回る。積算窓を 1 ms でなく 1 s と読めば"
        "計数は {counts_ratio:.0f} 倍になる。**どれも例外は出ず、有限で、"
        "もっともらしい絵が返る** ―― だから op 名に軸を書き、単位を引数にした。"),
    "dead_vocabulary": (
        "死んだ語彙 ―― 産む op はあるのに、そこから先へ行けない型",
        "台帳 {ops_before} op を「単入力かつ in 型 ≠ out 型 = 変換」で機械集計すると、"
        "他型へ一歩も出られない型が **{n_dead_before} 個**あった。"
        "`reprconv` の 42 op で **{n_fixed} 型**に出口ができ、変換ペアは"
        "{pairs_before} → {pairs_after} 種、袋小路は {n_dead_before} → {n_dead_after} 個。"
        "残した 9 型は**埋めない理由**を台帳に書いてある ―― 埋めないことも判断である。"),
}

CAPTION_EN = {
    "roundtrip_normals": (
        "Reversible — normals ⇄ (azimuth, elevation) in degrees",
        "The dead-end type `normals` now has an exit. Converting to azimuth and "
        "elevation (**both in degrees**) and back returns {n_normals} normals to "
        "**max|Δ| = {max_abs:.3e}** ({max_angle_error_deg:.3e} deg of angular error). "
        "The residual panel is black because it is drawn on a **fixed 0..1 scale**; "
        "auto-scaling would turn double-precision rounding into a visible pattern and "
        "make a reversible conversion look broken."),
    "roundtrip_curvature": (
        "Reversible — principal curvatures ⇄ shape index (exact at umbilics)",
        "Four patches (sphere, saddle, cylinder, plane; {n_points} points of which "
        "{umbilic_or_flat} are umbilic or flat) map to shape index S and curvedness C "
        "and back to **max|Δ| = {max_abs:.3e}**. The textbook form "
        "`atan((k1+k2)/(k1-k2))` divides by zero at umbilics; the `atan2` form keeps "
        "sphere S=+1, saddle S=0 and cylinder S=+0.5 exact everywhere."),
    "roundtrip_keypoints": (
        "Lossy — keypoints ⇄ pixel raster (measure what is lost)",
        "{separated_n} keypoints on a 4 px lattice, rasterised and picked back up, "
        "land **{axis_rms_px:.4f} px** RMS per axis (uniform-quantisation theory "
        "1/√12 = 0.2887) and {dist_rms_px:.4f} px in 2-D distance (theory √(2/12) = "
        "0.4082). Random placement merges {random_n} → {random_back_n} points — "
        "**quantisation (displacement) and merging (disappearance) are different "
        "losses** and collapsing them into one RMS hides which one dominates."),
    "roundtrip_gaussians": (
        "Lossy — points → gaussians → volume (measured by mass)",
        "`gaussians` had **no producing op at all**; this adds the entrance. Centres "
        "round-trip bit-identically (max|Δ| = {centres_max_abs:.3e}); sigma and w are "
        "information *added*, not lost. Splatting to a volume keeps "
        "**{box_truncation_theory:.5f}** of the mass under a 3σ **box** truncation — "
        "first written as the 3σ **ball** value {ball_truncation_wrong_value:.4f}, then "
        "refuted by refining the grid from 1.0 to 0.125, which converges to the box."),
    "cross_loop": (
        "Around the representations — what survives and what does not",
        "voxel → mesh → points → gaussians → voxel. A solid of "
        "{start_volume_voxel:.0f} voxels loses its interior at the mesh stage "
        "({mesh_vertices} vertices / {mesh_faces} faces, area {mesh_area:.1f}), loses "
        "connectivity and orientation at the points stage, and comes back as a "
        "{shell_voxel}-voxel shell rather than a solid. Yet the centroid moves only "
        "{centroid_shift:.4f} voxel. **Reporting both an agreeing and a disagreeing "
        "metric** is what keeps 'it came back' from being a lie."),
    "flow_colorwheel": (
        "The dead type `flow` becomes visible",
        "`flow` was a complete island: no single-input op produced or consumed it. Dense "
        "scene flow {flow_shape} now exits as magnitude (voxel) and as a colour wheel "
        "(rgbimage), **with the colour legend burnt into the same figure**. In this repo "
        "`flow` holds two different things under one name — dense (3,D,H,W) and "
        "scattered (N,3) — so the dense ops {dense_ops} and scattered ops "
        "{scattered_ops} are separate and fail closed on the other shape."),
    "axis_unit_traps": (
        "Axis, unit and spacing mix-ups pass without raising",
        "Reading (u,v) as (v,u) shifts the centroid by {uv_swap_centroid_shift:.1f}; "
        "leaving `spacing` at its default puts the peak at {spacing_peak_wrong} instead "
        "of {spacing_peak_correct}; passing π/6 radians as degrees rotates by "
        "{rad_as_deg_recovered:.4f} degrees; reading the gate as 1 s instead of 1 ms "
        "multiplies counts by {counts_ratio:.0f}. **None of these raise; all return "
        "finite, plausible pictures** — which is why the axis is in the op name and the "
        "unit is an explicit argument."),
    "dead_vocabulary": (
        "Dead vocabulary — types that are produced but lead nowhere",
        "Counting the {ops_before}-op catalogue for 'single input, in type ≠ out type = "
        "a conversion' found **{n_dead_before} types** with no outgoing conversion at "
        "all. The 42 ops of `reprconv` open **{n_fixed}** of them; conversion pairs go "
        "{pairs_before} → {pairs_after} and dead ends {n_dead_before} → {n_dead_after}. "
        "The 9 that remain carry a written reason for **not** filling them — deciding "
        "not to is also a decision."),
}


def _fmt(template, facts):
    extra = dict(facts)
    for key, val in list(facts.items()):
        if isinstance(val, list) and key.startswith("dead"):
            extra["n_" + key] = len(val)
        if key == "fixed":
            extra["n_fixed"] = len(val)
    try:
        return template.format(**extra)
    except (KeyError, IndexError, ValueError):
        return template


def _write_captions(results, log):
    """``wingconv.ja.md`` と ``wingconv.en.md`` を書く(**2 言語必須**)。"""
    os.makedirs(EXHIBITS, exist_ok=True)
    for lang, table, head in (
        ("ja", CAPTION_JA,
         "# 表現変換ウィング ―― 展示キャプション原稿\n\n"
         "生成元: `tools/gen_wingconv_gallery.py`"
         "(`py -3.11 tools/gen_wingconv_gallery.py`)。画像はすべて fullseye の op\n"
         "(`reprconv` / `imagedraw`)と numpy 合成で描いており(matplotlib 不使用)、"
         "図に焼いた数値は\n1 つ残らずその場で op を呼んで得た実測値である。"
         "乱数は seed 固定・幾何も固定なので\n再生成でバイト列が一致する"
         "(`--verify` で検査)。\n\n"
         "このウィングの主張は 1 つ ―― **変換の嘘は往復で露見する**。\n"
         "変換 op は「入口の型」と「出口の型」の両方を主張するので、嘘をつく面が 2 つある。\n"
         "だから主役は「A → B → A' を並べ、最後のコマに残差と誤差の数値を焼いた GIF」で、\n"
         "**可逆なものは残差が真っ黒 = 誤差 0**、**不可逆なものは何がどれだけ落ちるか**"
         "を数字で出す。\n"),
        ("en", CAPTION_EN,
         "# The Representation-Conversion Wing — exhibit captions\n\n"
         "Generated by `tools/gen_wingconv_gallery.py`. Every picture is drawn with "
         "fullseye's own ops\n(`reprconv` / `imagedraw`) and numpy compositing — no "
         "matplotlib — and every number burnt\ninto a figure was measured by calling "
         "the op at generation time. Seeds and geometry are fixed,\nso regeneration is "
         "byte-identical (`--verify`).\n\n"
         "This wing makes one claim: **a conversion's lie shows up in the round trip.** "
         "A conversion op\nasserts both an input type and an output type, so it has two "
         "faces on which to lie. Hence the\nlead exhibits are `A → B → A'` flipbooks "
         "whose last frame carries the residual and its number:\n**reversible → the "
         "residual is black**, **lossy → the loss is quantified**.\n"),
    ):
        lines = [
            "<!-- tools/gen_wingconv_gallery.py が自動生成。記事 md への挿入候補であり、"
            "このファイル自体は記事ではない。数値はすべて生成時の実測値。 -->\n"
            if lang == "ja" else
            "<!-- Generated by tools/gen_wingconv_gallery.py. A candidate for insertion "
            "into the article; not the article itself. Every number is measured at "
            "generation time. -->\n",
            head,
        ]
        for i, (name, _) in enumerate(EXHIBIT_ORDER, 1):
            if name not in results:
                continue
            info = results[name]["info"]
            facts = results[name]["facts"]
            title, body = table[name]
            caption = f"**{title}** ―— {_fmt(body, facts)}" if lang == "ja" \
                else f"**{title}** — {_fmt(body, facts)}"
            lines.append(f"\n## {i}. {title}\n")
            stem = f"{PREFIX}_{name}"
            if info["kind"] == "GIF":
                lines.append(markdown_animation(stem, title, caption))
            else:
                lines.append(markdown(stem, title, caption))
            lines.append(
                f"\n- {'GIF' if info['kind'] == 'GIF' else 'PNG'}: `{info['path']}` "
                f"({info['frames']} frame(s), {info['shape'][1]}x{info['shape'][0]} px, "
                f"{info['bytes'] / 1e6:.2f} MB)\n"
                f"- {'サムネ' if lang == 'ja' else 'Thumbnail'}: `{info['thumb']}`\n"
                f"- SHA-256: `{info['sha256']}`\n")
        path = os.path.join(EXHIBITS, f"{PREFIX}.{lang}.md")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(lines))
        log(f"[caption] {os.path.relpath(path, _ROOT)}")


def main(argv=None):
    names = [n for n, _ in EXHIBIT_ORDER]
    ap = argparse.ArgumentParser(description="表現変換ウィングの展示(GIF 5 / PNG 3)")
    ap.add_argument("--only", default="", help=f"comma list of {','.join(names)}")
    ap.add_argument("--verify", action="store_true",
                    help="2 回生成して SHA-256 が一致することを確かめる")
    ap.add_argument("--no-captions", action="store_true")
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
        _write_captions(results, log)

    if args.verify:
        log("[verify] regenerating to check the bytes are identical")
        first = {n: results[n]["info"]["sha256"] for n in results}
        again = build_all()
        bad = [n for n in first if again[n]["info"]["sha256"] != first[n]]
        for n in sorted(first):
            same = again[n]["info"]["sha256"] == first[n]
            log(f"    {'OK  ' if same else 'DIFF'} {n:22s} {first[n][:16]}...")
        if bad:
            log(f"[verify] NOT deterministic: {bad}")
            return 1
        log(f"[verify] all {len(first)} outputs are byte-identical on regeneration")

    log(f"=== done in {time.time() - t0:.1f}s ===")
    for n, r in results.items():
        i = r["info"]
        log(f"  {n:22s} {i['kind']}  {i['frames']:2d} frame(s)  "
            f"{i['shape'][1]}x{i['shape'][0]}  {i['bytes'] / 1e6:6.3f} MB")
    log(f"  total {sum(r['info']['bytes'] for r in results.values()) / 1e6:.2f} MB "
        f"in {len(results)} exhibits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
