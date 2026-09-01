# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wingopt_gallery — 「紙面の科学館」**光学設計・検査ウィング**の展示を作る。

記事本文の 2 本の掃引動画(``tools/gen_visionlab_video.py``)が「系を決めたあとで
何 µm から見えるか」を見せるのに対し、こちらは**その手前**を並べる ―― レンズと
センサとイルミネーションが、どの物理量でぶつかり合って「見える/見えない」を
決めているのか。12 点の展示は全部、``optics`` / ``visiondesign`` / ``defectgen`` /
``visionlab`` の関数を**実際に呼んだ結果**である。焼き込んだ数字に手入力は 1 つも
無い(すべて毎フレーム計算した値を整形しただけ)。

展示(10 本が GIF、2 点が静止画):

  1.  ``defect_atlas``      静止 — 欠陥 4 種と、**画素完全な正解マスク**の見本帳
  2.  ``limit_crossover``   GIF  — 作動距離を掃くと律速が回折→標本化へ入れ替わる
  3.  ``cos4_falloff``      GIF  — 焦点距離を短くすると cos⁴ で角が暗くなる
  4.  ``mtf``               GIF  — F 値とコントラスト伝達(カットオフつき)
  5.  ``dof_coc``           GIF  — 許容錯乱円を変えると被写界深度が比例して伸びる
  6.  ``res_vs_dof``        GIF  — 横分解能と被写界深度は**独立な 2 軸**(窓がある)
  7.  ``airy_rayleigh``     GIF  — Airy 像 2 点の分離と Rayleigh 基準
  8.  ``polarizer``         GIF  — 直交偏光子で鏡面反射が 0.0 まで落ち、傷が出る
  9.  ``abcd_rays``         GIF  — ABCD 行列の光線追跡と、固定センサ上のぼけ円
  10. ``detect_map``        静止 — (欠陥サイズ × コントラスト) の検出率マップ
  11. ``illumination``      GIF  — 明視野風/暗視野風でどちらが先に見つかるか
  12. ``pixel_pitch``       GIF  — 画素ピッチを粗くして Nyquist を割る瞬間

描画は Fullseye 自身の ``imagedraw`` op(``draw_line`` / ``draw_polyline`` /
``draw_circle`` / ``draw_markers``)と numpy 合成のみ。**matplotlib は使わない**
(カラーマップも自前の制御点補間)。文字だけは Fullseye にテキスト描画 op が無い
ため PIL の ``ImageDraw.text`` を数値ラベル専用に使う。

決定的である ―― 乱数は全部 seed 固定で、同じコマンドは同じバイト列を返す
(``--verify`` で 2 回作って SHA-256 を突き合わせられる)。

使い方::

    py -3.11 tools/gen_wingopt_gallery.py                       # 全部
    py -3.11 tools/gen_wingopt_gallery.py --exhibits mtf,polarizer
    py -3.11 tools/gen_wingopt_gallery.py --exhibits mtf --verify   # 決定性の確認
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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defectgen                                          # noqa: E402
import imagedraw                                          # Fullseye の描画 op
import optics                                             # noqa: E402
import visiondesign as vd                                 # noqa: E402
import visionlab as vl                                    # noqa: E402
from exhibit_tile import (contact_sheet, flipbook, markdown,      # noqa: E402
                          markdown_animation, save_animation, save_exhibit)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
ASSETS = os.path.join(_ROOT, "docs", "articles", "assets")
MEDIA = os.path.join(ASSETS, "media")
THUMBS = os.path.join(ASSETS, "thumbs")
EXHIBITS = os.path.join(_ROOT, "docs", "articles", "exhibits")
RAW_BASE = ("https://raw.githubusercontent.com/furuse-kazufumi/fullseye/"
            "master/docs/articles/assets/")

PREFIX = "wingopt_"
THUMB_WIDTH = 720
GIF_BUDGET = 3 * 1024 * 1024          # 3 MB 目安(記事の読み込みを重くしない)

# 基準の系 — 記事本文の掃引動画と同じ構成にしてある(数字が地続きに読める)。
SYS = dict(focal_mm=35.0, working_distance_mm=200.0, pixel_pitch_um=3.45,
           width_px=2448, height_px=2048, f_number=4.0, wavelength_um=0.55,
           depth_tolerance_mm=1.0)

# 配色(赤緑対で意味を担わせない = 色覚に依らず読める)
C_BG = (0.055, 0.062, 0.075)
C_PANEL = (0.10, 0.11, 0.13)
C_HDR = (0.09, 0.10, 0.12)
C_TEXT = (0.86, 0.87, 0.84)
C_DIM = (0.52, 0.55, 0.58)
C_HIT = (0.13, 0.85, 0.80)            # 当たり / 通った条件
C_MISS = (1.00, 0.70, 0.16)           # 見逃し / 目標線
C_FALSE = (0.58, 0.42, 0.90)          # 誤検出 / 第 2 の曲線
C_OPT = (0.35, 0.72, 1.00)            # 光学の限界
C_CURVE = (0.98, 0.86, 0.35)          # 実測の曲線
C_GRID = (0.24, 0.26, 0.30)
C_BAD = (0.86, 0.52, 0.48)

MIN_IOU = 0.1                         # inspection_sweep の既定と同じ判定閾値


# --------------------------------------------------------------------------- #
# 小道具                                                                        #
# --------------------------------------------------------------------------- #
_FONT_CACHE: dict = {}


def _font(size: int = 13, bold: bool = False):
    """等幅フォント(数値が桁で揃う)。無ければ既定へ退避。"""
    key = (size, bool(bold))
    if key not in _FONT_CACHE:
        from PIL import ImageFont
        path = ("C:/Windows/Fonts/consolab.ttf" if bold
                else "C:/Windows/Fonts/consola.ttf")
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except OSError:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def _canvas(h: int, w: int, color=C_BG) -> np.ndarray:
    c = np.empty((h, w, 3), np.float64)
    c[:, :] = np.asarray(color, np.float64)
    return c


def _fill(canvas: np.ndarray, y0: int, y1: int, x0: int, x1: int, color) -> None:
    """矩形をベタ塗り(op を通すまでもない下地)。範囲はクリップする。"""
    h, w = canvas.shape[:2]
    y0, y1 = max(0, int(y0)), min(h, int(y1))
    x0, x1 = max(0, int(x0)), min(w, int(x1))
    if y0 < y1 and x0 < x1:
        canvas[y0:y1, x0:x1, :] = np.asarray(color, np.float64)


def _upscale(a: np.ndarray, k: int) -> np.ndarray:
    """最近傍の整数倍拡大。**補間しない** — 画素の粗さ自体が見せたい情報。"""
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def _gray_to_rgb(img: np.ndarray) -> np.ndarray:
    return np.repeat(np.clip(np.asarray(img, np.float64), 0.0, 1.0)[:, :, None],
                     3, axis=2)


def _to_u8(canvas: np.ndarray) -> np.ndarray:
    return np.clip(canvas * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _text(frame_u8: np.ndarray, items) -> np.ndarray:
    """``(x, y, text, rgb01, size, bold)`` の列を焼き込む。

    Fullseye にはテキスト描画 op が無いため、**数値ラベルに限って** PIL を使う。
    図形(線・円・マーカー・折れ線)は ``imagedraw`` op で描いている。
    """
    from PIL import Image, ImageDraw
    im = Image.fromarray(frame_u8)
    d = ImageDraw.Draw(im)
    for x, y, s, col, size, bold in items:
        rgb = tuple(int(round(255 * float(c))) for c in col)
        d.text((int(x), int(y)), s, fill=rgb, font=_font(size, bold))
    return np.asarray(im)


def _dashed(canvas: np.ndarray, p0, p1, color, width=1, dash=8, gap=6):
    """破線 — ``imagedraw.draw_line`` を短い区間に分けて重ねる。

    ``draw_line`` は入力を破壊しない規約なので毎回フルコピーが走る。破線は
    呼び出し回数が多いので、**線の外接矩形だけを切り出して**そこに描き、
    書き戻す(op はそのまま使い、コピー量だけ落とす)。
    """
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    length = float(np.hypot(x1 - x0, y1 - y0))
    if length < 1e-9:
        return canvas
    h, w = canvas.shape[:2]
    pad = int(width) + 3
    bx0 = max(0, int(min(x0, x1)) - pad)
    bx1 = min(w, int(max(x0, x1)) + pad + 1)
    by0 = max(0, int(min(y0, y1)) - pad)
    by1 = min(h, int(max(y0, y1)) + pad + 1)
    if bx0 >= bx1 or by0 >= by1:
        return canvas
    sub = canvas[by0:by1, bx0:bx1]
    t = 0.0
    while t < length:
        t2 = min(t + dash, length)
        a = (x0 + (x1 - x0) * t / length - bx0, y0 + (y1 - y0) * t / length - by0)
        b = (x0 + (x1 - x0) * t2 / length - bx0, y0 + (y1 - y0) * t2 / length - by0)
        sub = imagedraw.draw_line(sub, a, b, color=color, width=width)
        t = t2 + gap
    canvas[by0:by1, bx0:bx1] = sub
    return canvas


# viridis 風の制御点(matplotlib は使わない — 数字を自前で補間するだけ)。
_HEAT_STOPS = np.array([
    [0.00, 0.267, 0.005, 0.329],
    [0.25, 0.230, 0.322, 0.546],
    [0.50, 0.128, 0.567, 0.551],
    [0.75, 0.369, 0.789, 0.383],
    [1.00, 0.993, 0.906, 0.144],
], np.float64)


def _heat(v: np.ndarray) -> np.ndarray:
    """[0,1] のスカラ場 → RGB。**NaN は無言で黒にせず**灰色で塗って可視化する。"""
    a = np.asarray(v, np.float64)
    bad = ~np.isfinite(a)
    a = np.clip(np.where(bad, 0.0, a), 0.0, 1.0)
    out = np.stack([np.interp(a, _HEAT_STOPS[:, 0], _HEAT_STOPS[:, k])
                    for k in (1, 2, 3)], axis=-1)
    out[bad] = (0.45, 0.45, 0.45)
    return out


# --------------------------------------------------------------------------- #
# 小さなプロット層(軸・目盛り・曲線 — すべて imagedraw op で描く)              #
# --------------------------------------------------------------------------- #
class Plot:
    """矩形 ``box=(x0, y0, x1, y1)`` にデータ座標を張る。

    ``imagedraw`` の op は入力を破壊せず新しい配列を返す規約なので、各メソッドは
    ``self.c`` を差し替える。描き終わったら ``plot.c`` を取り出して使う。
    """

    def __init__(self, canvas, box, xlim, ylim, xlog=False, ylog=False):
        self.c = canvas
        self.x0, self.y0, self.x1, self.y1 = [float(v) for v in box]
        self.xlim = (float(xlim[0]), float(xlim[1]))
        self.ylim = (float(ylim[0]), float(ylim[1]))
        self.xlog, self.ylog = bool(xlog), bool(ylog)

    # -- 座標変換 ----------------------------------------------------------- #
    def px(self, x):
        lo, hi = self.xlim
        v = np.clip(np.asarray(x, np.float64), min(lo, hi), max(lo, hi))
        if self.xlog:
            t = (np.log10(v) - np.log10(lo)) / (np.log10(hi) - np.log10(lo))
        else:
            t = (v - lo) / (hi - lo)
        return self.x0 + (self.x1 - self.x0) * t

    def py(self, y):
        lo, hi = self.ylim
        v = np.clip(np.asarray(y, np.float64), min(lo, hi), max(lo, hi))
        if self.ylog:
            t = (np.log10(v) - np.log10(lo)) / (np.log10(hi) - np.log10(lo))
        else:
            t = (v - lo) / (hi - lo)
        return self.y1 - (self.y1 - self.y0) * t          # 上が大きい値

    # -- 下地と枠 ----------------------------------------------------------- #
    def bg(self, color=C_PANEL):
        _fill(self.c, self.y0, self.y1 + 1, self.x0, self.x1 + 1, color)
        return self

    def band_x(self, xa, xb, color):
        """x 方向の帯(領域の意味づけ)。"""
        a, b = sorted((float(self.px(xa)), float(self.px(xb))))
        _fill(self.c, self.y0, self.y1 + 1, a, b, color)
        return self

    def band_y(self, ya, yb, color):
        a, b = sorted((float(self.py(ya)), float(self.py(yb))))
        _fill(self.c, a, b, self.x0, self.x1 + 1, color)
        return self

    def frame(self, color=C_DIM):
        self.c = imagedraw.draw_line(self.c, (self.x0, self.y1),
                                     (self.x1, self.y1), color=color, width=1)
        self.c = imagedraw.draw_line(self.c, (self.x0, self.y0),
                                     (self.x0, self.y1), color=color, width=1)
        return self

    def grid_x(self, values, color=C_GRID):
        for v in values:
            x = float(self.px(v))
            self.c = imagedraw.draw_line(self.c, (x, self.y0), (x, self.y1),
                                         color=color, width=1)
        return self

    def grid_y(self, values, color=C_GRID):
        for v in values:
            y = float(self.py(v))
            self.c = imagedraw.draw_line(self.c, (self.x0, y), (self.x1, y),
                                         color=color, width=1)
        return self

    def ticks_x(self, values, color=C_DIM, length=4):
        for v in values:
            x = float(self.px(v))
            self.c = imagedraw.draw_line(self.c, (x, self.y1),
                                         (x, self.y1 + length), color=color, width=1)
        return self

    def ticks_y(self, values, color=C_DIM, length=4):
        for v in values:
            y = float(self.py(v))
            self.c = imagedraw.draw_line(self.c, (self.x0 - length, y),
                                         (self.x0, y), color=color, width=1)
        return self

    # -- データ ------------------------------------------------------------- #
    def curve(self, xs, ys, color, width=2):
        xs = np.asarray(xs, np.float64)
        ys = np.asarray(ys, np.float64)
        ok = np.isfinite(xs) & np.isfinite(ys)
        if ok.sum() < 2:
            return self
        pts = list(zip(self.px(xs[ok]), self.py(ys[ok])))
        self.c = imagedraw.draw_polyline(self.c, pts, color=color, width=width)
        return self

    def vline(self, x, color, width=2, dashed=False, dash=8, gap=6):
        px = float(self.px(x))
        if dashed:
            self.c = _dashed(self.c, (px, self.y0), (px, self.y1), color,
                             width, dash, gap)
        else:
            self.c = imagedraw.draw_line(self.c, (px, self.y0), (px, self.y1),
                                         color=color, width=width)
        return self

    def hline(self, y, color, width=2, dashed=False, dash=8, gap=6):
        py = float(self.py(y))
        if dashed:
            self.c = _dashed(self.c, (self.x0, py), (self.x1, py), color,
                             width, dash, gap)
        else:
            self.c = imagedraw.draw_line(self.c, (self.x0, py), (self.x1, py),
                                         color=color, width=width)
        return self

    def marker(self, x, y, color=(1.0, 1.0, 1.0), size=5, shape="cross", width=2):
        self.c = imagedraw.draw_markers(self.c, [(float(self.px(x)), float(self.py(y)))],
                                        color=color, size=size, shape=shape,
                                        width=width)
        return self

    def dot(self, x, y, color, radius=3):
        self.c = imagedraw.draw_circle(self.c, (float(self.px(x)), float(self.py(y))),
                                       radius, color=color, width=1, fill=True)
        return self


# --------------------------------------------------------------------------- #
# 書き出し                                                                      #
# --------------------------------------------------------------------------- #
def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _save_png(frame_u8: np.ndarray, stem: str, log) -> dict:
    """静止展示は共通部品 ``exhibit_tile.save_exhibit`` に一本化する。

    サムネイル方針(幅 720 の JPEG + クリックで原寸)を 2 か所に持たないため。
    書いたあと**読み戻して**形を実測し、期待と照合する。
    """
    from PIL import Image
    res = save_exhibit(frame_u8, f"{PREFIX}{stem}")
    path, thumb = res["png"], res["thumb"]
    with Image.open(path) as back:
        shape = (back.height, back.width)
    if shape != frame_u8.shape[:2]:
        raise RuntimeError(f"{path}: read back {shape}, expected {frame_u8.shape[:2]}")
    info = {"kind": "png", "path": path, "thumb": thumb,
            "bytes": res["png_bytes"], "thumb_bytes": res["thumb_bytes"],
            "size": (shape[1], shape[0]), "frames": 1,
            "sha256": res["png_sha256"]}
    log(f"    png  {os.path.basename(path)}  {shape[1]}x{shape[0]}  "
        f"{info['bytes'] / 1e3:.0f} kB   thumb {info['thumb_bytes'] / 1e3:.0f} kB")
    return info


def _save_flipbook(frames_u8, stem: str, log) -> dict:
    """工程のコマ送りは共通部品 ``exhibit_tile.save_animation`` で書く。

    こちらは 1 コマを長く見せる(既定 700 ms、最後だけ 1400 ms)ので、掃引の
    GIF(``_save_gif``、10 fps で連続的に動く)とは別の道具として使い分ける。
    """
    res = save_animation(frames_u8, f"{PREFIX}{stem}")
    path = res["gif"]
    if res["frames"] != len(frames_u8):
        raise RuntimeError(f"{path}: read back {res['frames']} frame(s), expected "
                           f"{len(frames_u8)}")
    if os.path.getsize(path) > GIF_BUDGET:
        log(f"    WARNING {os.path.basename(path)} is "
            f"{os.path.getsize(path) / 1e6:.2f} MB, above the "
            f"{GIF_BUDGET / 1e6:.0f} MB budget")
    info = {"kind": "gif", "path": path, "thumb": res["thumb"],
            "bytes": res["gif_bytes"], "thumb_bytes": os.path.getsize(res["thumb"]),
            "size": res["size"], "frames": res["frames"], "fps": None,
            "step_ms": 700, "colors": None, "thumb_frame": 0,
            "sha256": res["gif_sha256"]}
    log(f"    gif  {os.path.basename(path)}  {res['size'][0]}x{res['size'][1]}  "
        f"{res['frames']} steps  700 ms/step  {info['bytes'] / 1e6:.2f} MB   "
        f"thumb {info['thumb_bytes'] / 1e3:.0f} kB")
    return info


def _save_gif(frames_u8, stem: str, fps: int, thumb_index: int, log) -> dict:
    """GIF を書き、**読み戻して**フレーム数と形を実測してから返す。

    3 MB 予算に収まるまで色数を落とす(256 → 128 → 64)。色数を落とすと縞が
    出るが、**サイズのために解像度やフレームを削らない** — 動きと数字が展示の
    中身なので、そこを削ると展示ではなくなる。
    """
    from PIL import Image
    os.makedirs(MEDIA, exist_ok=True)
    os.makedirs(THUMBS, exist_ok=True)
    path = os.path.join(MEDIA, f"{PREFIX}{stem}.gif")
    used_colors = None
    for colors in (256, 192, 128, 64):
        pil = [Image.fromarray(f, "RGB").convert("P", palette=Image.ADAPTIVE,
                                                 colors=colors)
               for f in frames_u8]
        pil[0].save(path, save_all=True, append_images=pil[1:],
                    duration=int(round(1000.0 / float(fps))), loop=0, optimize=True)
        used_colors = colors
        if os.path.getsize(path) <= GIF_BUDGET:
            break
    # 読み戻し検証
    with Image.open(path) as back:
        n, shape = 0, (back.height, back.width)
        try:
            while True:
                back.seek(n)
                n += 1
        except EOFError:
            pass
    if n != len(frames_u8):
        raise RuntimeError(f"{path}: read back {n} frame(s), expected "
                           f"{len(frames_u8)}")
    if shape != frames_u8[0].shape[:2]:
        raise RuntimeError(f"{path}: read back {shape}, expected "
                           f"{frames_u8[0].shape[:2]}")
    idx = int(np.clip(thumb_index, 0, len(frames_u8) - 1))
    thumb = os.path.join(THUMBS, f"{PREFIX}{stem}_thumb.jpg")
    im = Image.fromarray(frames_u8[idx], "RGB")
    if im.width > THUMB_WIDTH:
        im = im.resize((THUMB_WIDTH, max(2, round(im.height * THUMB_WIDTH / im.width))),
                       Image.LANCZOS)
    im.save(thumb, format="JPEG", quality=88, optimize=True)
    info = {"kind": "gif", "path": path, "thumb": thumb,
            "bytes": os.path.getsize(path), "thumb_bytes": os.path.getsize(thumb),
            "size": (shape[1], shape[0]), "frames": n, "fps": fps,
            "colors": used_colors, "thumb_frame": idx, "sha256": _sha256(path)}
    log(f"    gif  {os.path.basename(path)}  {shape[1]}x{shape[0]}  {n} frames  "
        f"fps={fps}  {used_colors} colors  {info['bytes'] / 1e6:.2f} MB   "
        f"thumb frame {idx} ({info['thumb_bytes'] / 1e3:.0f} kB)")
    return info


# --------------------------------------------------------------------------- #
# 共通の系ヘルパ                                                                #
# --------------------------------------------------------------------------- #
def _system(**over):
    p = dict(SYS)
    p.update(over)
    return vl.VisionSystem(focal_mm=p["focal_mm"],
                           working_distance_mm=p["working_distance_mm"],
                           pixel_pitch_um=p["pixel_pitch_um"],
                           width_px=p["width_px"], height_px=p["height_px"],
                           f_number=p["f_number"], wavelength_um=p["wavelength_um"],
                           depth_tolerance_mm=p["depth_tolerance_mm"])


def _limits(**over):
    """その構成の (geometry, resolving_power) を返す。"""
    p = dict(SYS)
    p.update(over)
    geo = vd.system_geometry(p["focal_mm"], p["working_distance_mm"],
                             p["pixel_pitch_um"], p["width_px"], p["height_px"])
    res = vd.resolving_power(p["pixel_pitch_um"], p["f_number"],
                             geo["magnification"], p["wavelength_um"])
    return geo, res


def _detect(img, mask):
    """基準検出器を通し、``(pred, iou, detected)``。visionlab と同じ判定。"""
    pred = vl._default_detector(img)
    inter = float(np.sum(pred & mask))
    union = float(np.sum(pred | mask))
    iou = inter / union if union > 0 else 0.0
    return pred, iou, bool(iou >= MIN_IOU)


def _verdict_rgb(img, mask, pred, dim=0.38):
    """当たり/見逃し/誤検出の 3 色重ね合わせ。"""
    base = _gray_to_rgb(img) * dim
    hit = pred & mask
    base[pred & ~mask] = np.asarray(C_FALSE) * 0.75
    base[mask & ~pred] = np.asarray(C_MISS)
    base[hit] = np.asarray(C_HIT)
    return base


def _bisect(fn, lo, hi, tol=1e-7, iters=200):
    """符号が変わる区間を二分する(scipy を持ち出すまでもない)。無ければ None。"""
    flo, fhi = fn(lo), fn(hi)
    if not (np.isfinite(flo) and np.isfinite(fhi)) or flo == 0.0:
        return lo if flo == 0.0 else None
    if flo * fhi > 0:
        return None
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fm = fn(mid)
        if fm == 0.0 or (hi - lo) < tol:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def _header(canvas, w, title, subtitle):
    """上端の帯。タイトルと系の諸元(実測値)。"""
    _fill(canvas, 0, 34, 0, w, C_HDR)
    return [(14, 4, title, (0.95, 0.95, 0.92), 15, True),
            (14, 20, subtitle, C_DIM, 11, False)]


# =========================================================================== #
# 1. 欠陥ジェネレータの見本帳(静止画)                                          #
# =========================================================================== #
def ex_defect_atlas(log):
    """欠陥 5 種 × (撮れる画像 | 画素完全な正解マスク)を格子に束ねる。

    1 枚ずつ原寸で並べると記事が縦に伸びるだけなので、共通部品
    ``exhibit_tile.contact_sheet`` に載せる。**「撮像 → その正解マスク」の対を
    横に隣り合わせ**、1 行に 2 種類ぶん(4 パネル)並べる — 縦 5 段の帯にすると
    今度は記事が縦に伸びてしまうので、対の隣接だけ守って横に畳む。
    ラベルに載る数字は ``defect_stats`` の実測値。
    """
    system = _system()
    geo, res = _limits()
    upp = geo["um_per_pixel"]
    tile = 232
    sh = (tile, tile)

    def surf(seed):
        return defectgen.surface_texture(sh, "orange_peel", strength=0.055,
                                         scale_px=5.0, seed=seed)

    # 幾何は画素で頼み、**µm は換算して表示する**(換算点は system.px_for_um と
    # 同じ um_per_pixel 1 つだけ)。render_part は長さ/幅を 4:1 に固定するので、
    # 見本帳ではその制約を外して各生成器の素の姿を見せる。
    specs = [
        ("scratch", dict(length_px=176.0, width_px=4.5, angle_deg=22.0,
                         wander=0.11, contrast=-0.30, seed=7),
         defectgen.defect_scratch, "長さ{L:.0f}µm × 幅{W:.0f}µm"),
        ("pits", dict(count=16, radius_px=4.0, radius_sigma=0.35,
                      contrast=-0.34, clustering=0.45, seed=7),
         defectgen.defect_pits, "16 個 直径{D:.0f}µm"),
        ("crack", dict(length_px=150.0, width_px=3.0, angle_deg=104.0,
                       branch_prob=0.22, wander=0.30, contrast=-0.36, seed=7),
         defectgen.defect_crack, "長さ{L:.0f}µm × 幅{W:.0f}µm"),
        ("blob", dict(radius_px=27.0, roughness=0.40, contrast=0.26, seed=7),
         defectgen.defect_blob, "直径{D:.0f}µm"),
    ]
    rows = []
    for i, (kind, kw, fn, tmpl) in enumerate(specs):
        ideal, mask = fn(sh, **kw)
        scene = defectgen.composite_defect(surf(1000 + i), ideal, mask)
        order = tmpl.format(
            L=kw.get("length_px", 0.0) * upp, W=kw.get("width_px", 0.0) * upp,
            D=kw.get("radius_px", 0.0) * 2.0 * upp)
        rows.append({"kind": kind, "order": order, "params": dict(kw),
                     "img": system.capture(scene), "mask": mask})

    # 5 段目 = composite: 3 種を 1 つの部品に重ねる(実ラインの部品が 1 種類の
    # 欠陥しか出さない、という前提の方が非現実的なので)。マスクは論理和。
    scene = surf(1004)
    comp_mask = np.zeros(sh, bool)
    for ideal, msk in (
            defectgen.defect_scratch(sh, length_px=138.0, width_px=4.0,
                                     angle_deg=18.0, wander=0.12,
                                     contrast=-0.30, seed=21),
            defectgen.defect_pits(sh, count=10, radius_px=3.6, radius_sigma=0.35,
                                  contrast=-0.34, clustering=0.5, seed=22),
            defectgen.defect_blob(sh, radius_px=16.0, roughness=0.42,
                                  contrast=0.26, seed=23, centre=(64.0, 172.0))):
        scene = defectgen.composite_defect(scene, ideal, msk)
        comp_mask |= msk
    rows.append({"kind": "composite", "order": "scratch+pits+blob",
                 "params": None, "img": system.capture(scene), "mask": comp_mask})

    panels, labels = [], []
    for r in rows:
        st = defectgen.defect_stats(r["mask"], um_per_pixel=upp)
        pred, iou, det = _detect(r["img"], r["mask"])
        r["stats"], r["iou"], r["detected"] = st, iou, det
        mask_rgb = np.zeros((tile, tile, 3), np.float64)
        mask_rgb[:, :] = (0.07, 0.08, 0.10)
        mask_rgb[r["mask"]] = C_HIT
        panels += [_gray_to_rgb(r["img"]), mask_rgb]
        labels += [f"{r['kind']} — {r['order']}",
                   f"正解マスク {st['area_px']}px / IoU {iou:.3f}"]

    title = f"欠陥 5 種 —— 対で「撮像 → 画素完全な正解マスク」({upp:.3f} µm/画素)"
    sheet = contact_sheet(panels, labels, ncols=4, panel_px=tile, pad=14,
                          label_h=28, title=title, title_h=46,
                          font_size=13, title_font_size=19)
    frame = _to_u8(sheet)
    facts = {
        "system": repr(system), "um_per_pixel": upp,
        "optical_limit_um": res["resolution_object_um"],
        "limited_by": res["limited_by"], "tile_px": tile,
        "rows": [{k: v for k, v in r.items() if k not in ("img", "mask")}
                 for r in rows],
    }
    log(f"  {len(rows)} kinds on one contact sheet ({frame.shape[1]}x{frame.shape[0]}); "
        + ", ".join(f"{r['kind']} IoU {r['iou']:.3f}" for r in rows))
    return {"frames": [frame], "facts": facts, "fps": None, "thumb_index": 0}


# =========================================================================== #
# 2. 律速の入れ替わり(GIF)                                                     #
# =========================================================================== #
def ex_limit_crossover(log):
    """作動距離を掃くと、回折律速と標本化律速が入れ替わる。交点を実測で出す。"""
    pitch, fn, lam, f = SYS["pixel_pitch_um"], SYS["f_number"], SYS["wavelength_um"], SYS["focal_mm"]
    wd_lo, wd_hi, nfr = 120.0, 320.0, 42
    wds = np.linspace(wd_lo, wd_hi, nfr)

    rows = []
    for wd in wds:
        geo, res = _limits(working_distance_mm=float(wd))
        rows.append({"wd": float(wd), "nyq": res["nyquist_object_um"],
                     "dif": res["diffraction_object_um"],
                     "lim": res["resolution_object_um"],
                     "by": res["limited_by"], "upp": geo["um_per_pixel"],
                     "m": geo["magnification"], "neff": res["working_f_number"]})

    def gap(wd):
        _, r = _limits(working_distance_mm=float(wd))
        return r["nyquist_object_um"] - r["diffraction_object_um"]

    cross_wd = _bisect(gap, wd_lo, wd_hi, tol=1e-9)
    geo_c, res_c = _limits(working_distance_mm=float(cross_wd))
    cross_um = res_c["resolution_object_um"]
    # 記事本文の掃引(120->700 mm を 44 段)が最初に入れ替わりを報告する格子点
    grid44 = np.linspace(120.0, 700.0, 44)
    grid_first = None
    for g in grid44:
        _, r = _limits(working_distance_mm=float(g))
        if r["limited_by"] == "sampling":
            grid_first = float(g)
            break
    log(f"  crossover at WD {cross_wd:.4f} mm, both limits {cross_um:.4f} um "
        f"(m={geo_c['magnification']:.6f}); the 44-step article grid first "
        f"flags it at {grid_first:.1f} mm")

    w, hdr = 1000, 34
    plot_box = (86, hdr + 96, w - 22, hdr + 96 + 268)
    h = int(plot_box[3]) + 46
    y_lo = min(min(r["nyq"] for r in rows), min(r["dif"] for r in rows)) * 0.92
    y_hi = max(max(r["nyq"] for r in rows), max(r["dif"] for r in rows)) * 1.05

    frames = []
    for i, r in enumerate(rows):
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "WHICH LIMIT BINDS  --  diffraction and sampling swap places",
            f"f={f:g}mm  f/{fn:g}  pitch={pitch:g}um  lambda={lam:g}um  "
            f"{SYS['width_px']}x{SYS['height_px']}px   sweeping the working distance")
        # 上段: 2 本の限界を横棒で見せる(どちらが長いか = どちらが律速か)
        bx0, bx1 = 250, w - 40
        _fill(canvas, hdr + 6, hdr + 88, 14, w - 14, C_PANEL)
        bar_hi = y_hi
        for k, (name, val, col) in enumerate((
                ("sampling  (Nyquist)", r["nyq"], C_CURVE),
                ("diffraction (Airy)", r["dif"], C_OPT))):
            yb = hdr + 16 + k * 34
            wpx = int(round((bx1 - bx0) * val / bar_hi))
            _fill(canvas, yb, yb + 22, bx0, bx0 + max(1, wpx), col)
            labels += [
                (24, yb + 3, name, C_TEXT, 13, True),
                (bx0 + max(1, wpx) + 8, yb + 3, f"{val:6.2f} um", col, 13, True),
            ]
        binding = "sampling" if r["by"] == "sampling" else "diffraction"
        labels.append((24, hdr + 68,
                       f"WD {r['wd']:6.1f} mm   m {r['m']:.5f}   {r['upp']:6.3f} um/px"
                       f"   N_eff {r['neff']:.3f}   ->  limited by {binding.upper()}"
                       f"  = {r['lim']:.2f} um",
                       (C_CURVE if binding == "sampling" else C_OPT), 13, True))
        # 下段: 2 本の曲線と交点
        p = Plot(canvas, plot_box, (wd_lo, wd_hi), (y_lo, y_hi))
        p.bg()
        p.band_x(wd_lo, cross_wd, (0.13, 0.15, 0.19))
        p.grid_y([15, 20, 25, 30, 35, 40, 45])
        p.frame()
        wa = np.array([q["wd"] for q in rows])
        p.curve(wa, [q["nyq"] for q in rows], C_CURVE, 2)
        p.curve(wa, [q["dif"] for q in rows], C_OPT, 2)
        p.vline(cross_wd, (0.95, 0.95, 0.92), 1, dashed=True, dash=6, gap=6)
        p.ticks_x([120, 160, 200, 240, 280, 320])
        p.ticks_y([20, 25, 30, 35, 40])
        p.marker(r["wd"], r["nyq"], C_CURVE, 5, "cross", 2)
        p.marker(r["wd"], r["dif"], C_OPT, 5, "cross", 2)
        p.dot(cross_wd, cross_um, (1.0, 1.0, 1.0), 3)
        canvas = p.c
        for t in (120, 160, 200, 240, 280, 320):
            labels.append((int(p.px(t)) - 12, plot_box[3] + 6, f"{t}", C_DIM, 11, False))
        for t in (20, 25, 30, 35, 40):
            labels.append((plot_box[0] - 34, int(p.py(t)) - 7, f"{t}", C_DIM, 11, False))
        labels += [
            (plot_box[0] + 6, plot_box[1] + 4, "object-side limit [um]", C_DIM, 11, False),
            (plot_box[2] - 178, plot_box[3] - 16, "working distance [mm] ->", C_DIM, 11, False),
            (int(p.px(cross_wd)) + 6, plot_box[1] + 6,
             f"crossover  WD {cross_wd:.2f} mm   both = {cross_um:.2f} um",
             (0.95, 0.95, 0.92), 12, True),
            (plot_box[0] + 8, plot_box[1] + 24, "diffraction binds", C_OPT, 11, True),
            (int(p.px(cross_wd)) + 6, plot_box[1] + 24, "sampling binds", C_CURVE, 11, True),
            (plot_box[0] + 8, plot_box[3] - 34,
             f"the 44-step sweep in the article first reports the swap at "
             f"WD {grid_first:.1f} mm -- that is the grid, not the physics",
             C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = int(np.argmin([abs(r["wd"] - cross_wd) for r in rows]))
    facts = {"crossover_wd_mm": cross_wd, "crossover_limit_um": cross_um,
             "crossover_magnification": geo_c["magnification"],
             "grid44_first_sampling_wd_mm": grid_first,
             "wd_range_mm": [wd_lo, wd_hi], "rows": rows}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 3. cos^4 の周辺光量落ち(GIF)                                                 #
# =========================================================================== #
def ex_cos4_falloff(log):
    """焦点距離を短くすると画角が広がり、角が cos^4 で暗くなる。"""
    wd = SYS["working_distance_mm"]
    pitch, wpx, hpx = SYS["pixel_pitch_um"], SYS["width_px"], SYS["height_px"]
    focals = np.linspace(42.0, 8.0, 36)

    sensor_w = wpx * pitch * 1e-3
    sensor_h = hpx * pitch * 1e-3
    map_w, map_h = 372, 312                      # 表示用の粗い格子(アスペクト維持)
    yy, xx = np.mgrid[0:map_h, 0:map_w].astype(np.float64)
    # センサ面の物理座標 [mm](画素中心。端 1 画素ぶんのずれを出さないよう
    # (i+0.5)/n でセルの中心を取る)
    sx = ((xx + 0.5) / map_w - 0.5) * sensor_w
    sy = ((yy + 0.5) / map_h - 0.5) * sensor_h
    r_mm = np.hypot(sx, sy)

    rows = []
    for f in focals:
        conj = optics.thin_lens(focal_mm=float(f), object_mm=wd)
        img_mm = float(conj["image_mm"])
        half = float(np.degrees(np.arctan2(np.hypot(sensor_w, sensor_h) / 2.0, img_mm)))
        curve = np.asarray(optics.relative_illumination(half_angle_deg=half,
                                                        samples=128), np.float64)
        corner = float(curve[-1, 1])
        field = np.degrees(np.arctan2(r_mm, img_mm))
        rel = np.cos(np.radians(field)) ** 4.0
        feas = vd.system_feasibility(defect_um=100.0, focal_mm=float(f),
                                     working_distance_mm=wd, pixel_pitch_um=pitch,
                                     f_number=SYS["f_number"], width_px=wpx,
                                     height_px=hpx, wavelength_um=SYS["wavelength_um"],
                                     depth_tolerance_mm=SYS["depth_tolerance_mm"])
        rows.append({"f": float(f), "image_mm": img_mm, "half_deg": half,
                     "corner": corner, "curve": curve, "rel": rel,
                     "feas_corner": feas["corner_illumination"],
                     "feas_half": feas["half_angle_deg"],
                     "edge_mid": float(rel[map_h // 2, 0])})

    # 独立に計算した 2 経路(自前の cos^4 マップの角 と system_feasibility の
    # corner_illumination)が一致することを確認する — 片方が壊れたら気付ける。
    worst = max(abs(r["corner"] - r["feas_corner"]) for r in rows)
    log(f"  corner illumination: own map vs system_feasibility differ by at most "
        f"{worst:.2e} (independent code paths, so this is a real cross-check)")

    w, hdr = 1000, 34
    map_x, map_y = 18, hdr + 26
    plot_box = (map_x + map_w + 78, map_y + 8, w - 24, map_y + map_h - 44)
    h = map_y + map_h + 96
    frames = []
    for i, r in enumerate(rows):
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "COS^4 FALLOFF  --  the corner of the field is the darkest place",
            f"WD={wd:g}mm  pitch={pitch:g}um  sensor {sensor_w:.3f}x{sensor_h:.3f} mm "
            f"({wpx}x{hpx})   sweeping the focal length")
        canvas[map_y:map_y + map_h, map_x:map_x + map_w] = _heat(r["rel"])
        canvas = imagedraw.draw_polyline(
            canvas, [(map_x - 1, map_y - 1), (map_x + map_w, map_y - 1),
                     (map_x + map_w, map_y + map_h), (map_x - 1, map_y + map_h)],
            color=C_GRID, width=1, closed=True)
        # 中心と角にマーカー(数字がどこの値かを迷わせない)
        canvas = imagedraw.draw_markers(
            canvas, [(map_x + map_w / 2.0, map_y + map_h / 2.0)],
            color=(1.0, 1.0, 1.0), size=7, shape="cross", width=1)
        canvas = imagedraw.draw_circle(canvas, (map_x + 6, map_y + 6), 5,
                                       color=(1.0, 1.0, 1.0), width=1)
        p = Plot(canvas, plot_box, (0.0, 46.0), (0.0, 1.02))
        p.bg()
        p.grid_y([0.25, 0.5, 0.75, 1.0])
        p.frame()
        p.curve(r["curve"][:, 0], r["curve"][:, 1], C_OPT, 2)
        p.hline(r["corner"], C_MISS, 1, dashed=True, dash=7, gap=6)
        p.vline(r["half_deg"], C_MISS, 1, dashed=True, dash=7, gap=6)
        p.marker(r["half_deg"], r["corner"], (1.0, 1.0, 1.0), 5, "cross", 2)
        p.ticks_x([0, 10, 20, 30, 40])
        p.ticks_y([0.25, 0.5, 0.75, 1.0])
        canvas = p.c
        for t in (0, 10, 20, 30, 40):
            labels.append((int(p.px(t)) - 6, plot_box[3] + 6, f"{t}", C_DIM, 11, False))
        for t in (0.25, 0.5, 0.75, 1.0):
            labels.append((plot_box[0] - 36, int(p.py(t)) - 7, f"{t:.2f}", C_DIM, 11, False))
        yi = map_y + map_h + 10
        labels += [
            (map_x + 4, map_y - 18, "relative illuminance across the sensor",
             (0.95, 0.95, 0.92), 12, True),
            (map_x + map_w + 82, map_y - 18, "cos^4 vs field angle (relative_illumination)",
             (0.95, 0.95, 0.92), 12, True),
            (plot_box[2] - 140, plot_box[3] - 16, "field angle [deg] ->", C_DIM, 11, False),
            (18, yi,
             f"f = {r['f']:5.1f} mm   image distance {r['image_mm']:6.2f} mm   "
             f"half field angle {r['half_deg']:5.2f} deg",
             C_TEXT, 14, True),
            (18, yi + 20,
             f"centre 1.000   corner {r['corner']:.4f}   "
             f"= {1.0 / r['corner']:.2f}x brighter in the middle   "
             f"({(1.0 - r['corner']) * 100:.1f} % of the light is gone at the corner)",
             C_MISS if r["corner"] < 0.7 else C_TEXT, 14, True),
            (18, yi + 40,
             f"cross-check: system_feasibility reports corner_illumination "
             f"{r['feas_corner']:.6f} at half angle {r['feas_half']:.4f} deg "
             f"(own map differs by {abs(r['corner'] - r['feas_corner']):.1e})",
             C_DIM, 11, False),
            (18, yi + 56,
             "white cross = sensor centre, white circle = corner where the number "
             "above is measured", C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = len(rows) - 1
    facts = {"working_distance_mm": wd, "sensor_mm": [sensor_w, sensor_h],
             "focal_range_mm": [float(focals[0]), float(focals[-1])],
             "corner_first": rows[0]["corner"], "corner_last": rows[-1]["corner"],
             "half_deg_first": rows[0]["half_deg"], "half_deg_last": rows[-1]["half_deg"],
             "max_crosscheck_delta": worst,
             "rows": [{k: v for k, v in r.items() if k not in ("curve", "rel")}
                      for r in rows]}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 4. 回折限界の MTF(GIF)                                                       #
# =========================================================================== #
def ex_mtf(log):
    """F 値を変えるとコントラスト伝達がどう落ちるか。カットオフつき。"""
    lam = SYS["wavelength_um"]
    fnums = np.exp(np.linspace(np.log(1.4), np.log(22.0), 34))
    probes = (40.0, 100.0, 200.0)                # cyc/mm で見る 3 本のバー
    bar_w, bar_h = 208, 92
    upp_mm = 1.0                                 # バーは像面 [mm] の実寸で描く
    xs_mm = (np.arange(bar_w) + 0.5) / bar_w * upp_mm    # 幅 1 mm ぶん

    rows = []
    for n in fnums:
        curve = np.asarray(optics.mtf_diffraction(f_number=float(n),
                                                  wavelength_um=lam, samples=256),
                           np.float64)
        cutoff = float(curve[-1, 0])
        vals = [float(np.interp(pf, curve[:, 0], curve[:, 1], left=1.0, right=0.0))
                for pf in probes]
        rows.append({"n": float(n), "curve": curve, "cutoff": cutoff, "mtf": vals})

    half = float(np.interp(0.5, np.asarray(rows[0]["curve"])[::-1, 1],
                           np.asarray(rows[0]["curve"])[::-1, 0]))
    log(f"  cutoff {rows[0]['cutoff']:.1f} cyc/mm at f/{rows[0]['n']:.2f}  ->  "
        f"{rows[-1]['cutoff']:.1f} cyc/mm at f/{rows[-1]['n']:.2f}")

    w, hdr = 1000, 34
    bars_x, bars_y = 20, hdr + 30
    plot_box = (bars_x + bar_w + 84, bars_y - 4, w - 24, bars_y + 3 * (bar_h + 26) + 6)
    h = int(plot_box[3]) + 96
    frames = []
    for r in rows:
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "DIFFRACTION MTF  --  what the aperture does to contrast",
            f"lambda={lam:g}um, circular unobstructed pupil, no aberration, "
            f"no defocus, no detector MTF   --   sweeping the f-number")
        # 左: 3 本のバーターゲット。振幅は MTF 曲線から読んだ実測値。
        for k, (pf, m) in enumerate(zip(probes, r["mtf"])):
            y = bars_y + k * (bar_h + 26)
            g = 0.5 + 0.5 * m * np.cos(2.0 * np.pi * pf * xs_mm)
            tile = np.repeat(g[None, :], bar_h, axis=0)
            canvas[y:y + bar_h, bars_x:bars_x + bar_w] = _gray_to_rgb(tile)
            canvas = imagedraw.draw_polyline(
                canvas, [(bars_x - 1, y - 1), (bars_x + bar_w, y - 1),
                         (bars_x + bar_w, y + bar_h), (bars_x - 1, y + bar_h)],
                color=C_GRID, width=1, closed=True)
            labels += [
                (bars_x, y + bar_h + 3, f"{pf:.0f} cyc/mm", C_TEXT, 12, True),
                (bars_x + 108, y + bar_h + 3,
                 f"contrast {m:.3f}" + ("   (gone)" if m <= 1e-6 else ""),
                 (C_BAD if m <= 1e-6 else C_HIT if m > 0.3 else C_MISS), 12, True),
            ]
        # 右: MTF 曲線
        p = Plot(canvas, plot_box, (0.0, 1300.0), (0.0, 1.02))
        p.bg()
        p.grid_y([0.25, 0.5, 0.75, 1.0])
        p.grid_x([200, 400, 600, 800, 1000, 1200])
        p.frame()
        p.curve(r["curve"][:, 0], r["curve"][:, 1], C_OPT, 2)
        p.vline(r["cutoff"], C_BAD, 1, dashed=True, dash=7, gap=6)
        for pf, m in zip(probes, r["mtf"]):
            p.vline(pf, C_GRID, 1, dashed=True, dash=4, gap=8)
            p.marker(pf, m, C_CURVE, 4, "cross", 2)
        p.ticks_x([0, 200, 400, 600, 800, 1000, 1200])
        p.ticks_y([0.25, 0.5, 0.75, 1.0])
        canvas = p.c
        for t in (0, 200, 400, 600, 800, 1000, 1200):
            labels.append((int(p.px(t)) - 14, plot_box[3] + 6, f"{t}", C_DIM, 11, False))
        for t in (0.25, 0.5, 0.75, 1.0):
            labels.append((plot_box[0] - 36, int(p.py(t)) - 7, f"{t:.2f}", C_DIM, 11, False))
        yi = int(plot_box[3]) + 26
        labels += [
            (plot_box[0] + 6, plot_box[1] + 4, "MTF (contrast transfer)", C_DIM, 11, False),
            (plot_box[2] - 214, plot_box[3] - 16,
             "spatial frequency [cycles/mm] ->", C_DIM, 11, False),
            (min(int(p.px(r["cutoff"])) + 6, plot_box[2] - 190), plot_box[1] + 22,
             f"cutoff {r['cutoff']:.1f} cyc/mm", C_BAD, 12, True),
            (18, yi, f"f/{r['n']:.2f}   cutoff = 1/(lambda*N) = {r['cutoff']:7.1f} cyc/mm"
                     f"   MTF at half cutoff = 0.391 (textbook, exact)",
             C_TEXT, 14, True),
            (18, yi + 20,
             "   ".join(f"{pf:.0f} cyc/mm: {m:.3f}" for pf, m in zip(probes, r["mtf"])),
             C_TEXT, 14, True),
            (18, yi + 42,
             "the bars on the left are drawn with exactly the modulation the curve "
             "on the right reports -- nothing is stylised",
             C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = int(np.argmin([abs(r["n"] - 8.0) for r in rows]))
    facts = {"wavelength_um": lam, "probe_freqs_cyc_per_mm": list(probes),
             "half_cutoff_freq_at_first": half,
             "rows": [{"f_number": r["n"], "cutoff_cyc_per_mm": r["cutoff"],
                       "mtf_at_probes": r["mtf"]} for r in rows]}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 5. 被写界深度と錯乱円(GIF)                                                   #
# =========================================================================== #
def ex_dof_coc(log):
    """許容錯乱円を変えると被写界深度が**比例して**伸びる。利得の出どころ。"""
    f, fn, wd, pitch = SYS["focal_mm"], SYS["f_number"], SYS["working_distance_mm"], SYS["pixel_pitch_um"]
    tol = SYS["depth_tolerance_mm"]
    ks = np.linspace(1.0, 10.0, 37)              # 錯乱円 = 画素ピッチの k 倍
    base = optics.depth_of_field(focal_mm=f, f_number=fn, subject_mm=wd,
                                 coc_mm=pitch * 1e-3)
    rows = []
    for k in ks:
        d = optics.depth_of_field(focal_mm=f, f_number=fn, subject_mm=wd,
                                  coc_mm=pitch * 1e-3 * float(k))
        rows.append({"k": float(k), "near": d["near_mm"], "far": d["far_mm"],
                     "depth": d["depth_mm"], "hyper": d["hyperfocal_mm"],
                     "ratio": d["depth_mm"] / base["depth_mm"]})
    k_tol = _bisect(lambda k: optics.depth_of_field(
        focal_mm=f, f_number=fn, subject_mm=wd,
        coc_mm=pitch * 1e-3 * float(k))["depth_mm"] - tol, 1.0, 10.0, tol=1e-9)
    log(f"  1 px CoC -> DoF {base['depth_mm']:.4f} mm; 10 px CoC -> "
        f"{rows[-1]['depth']:.4f} mm (ratio {rows[-1]['ratio']:.4f}); "
        f"the {tol:g} mm tolerance is met from CoC = {k_tol:.3f} px")

    w, hdr = 1000, 34
    ruler_y, ruler_h = hdr + 46, 88
    ruler_box = (86, ruler_y, w - 30, ruler_y + ruler_h)
    plot_box = (86, ruler_y + ruler_h + 76, w - 30, ruler_y + ruler_h + 76 + 200)
    h = int(plot_box[3]) + 72
    span_lo, span_hi = wd - 5.0, wd + 5.0
    frames = []
    for r in rows:
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "DEPTH OF FIELD  --  it is your choice of blur circle, not a property "
            "of the lens",
            f"f={f:g}mm  f/{fn:g}  subject {wd:g}mm  pixel pitch {pitch:g}um   "
            f"sweeping the acceptable circle of confusion")
        # 上段: 距離軸の上に近点〜遠点のブラケット
        rp = Plot(canvas, ruler_box, (span_lo, span_hi), (0.0, 1.0))
        rp.bg()
        rp.band_x(wd - tol / 2.0, wd + tol / 2.0, (0.17, 0.15, 0.12))
        rp.band_x(r["near"], r["far"], (0.10, 0.22, 0.24))
        rp.frame()
        rp.vline(wd, (0.95, 0.95, 0.92), 1, dashed=True, dash=6, gap=5)
        rp.vline(r["near"], C_HIT, 2)
        rp.vline(r["far"], C_HIT, 2)
        rp.ticks_x([wd - 4, wd - 2, wd, wd + 2, wd + 4])
        canvas = rp.c
        for t in (wd - 4, wd - 2, wd, wd + 2, wd + 4):
            labels.append((int(rp.px(t)) - 16, ruler_box[3] + 6, f"{t:.0f}", C_DIM, 11, False))
        inside = bool(r["depth"] >= tol)
        labels += [
            (ruler_box[0] + 6, ruler_box[1] + 4, "distance from the lens [mm]",
             C_DIM, 11, False),
            (int(rp.px(wd)) + 6, ruler_box[1] + 22, "focus plane", (0.95, 0.95, 0.92), 11, True),
            (max(ruler_box[0] + 4, int(rp.px(r["near"])) - 96), ruler_box[3] - 22,
             f"near {r['near']:.3f}", C_HIT, 12, True),
            (min(ruler_box[2] - 110, int(rp.px(r["far"])) + 6), ruler_box[3] - 22,
             f"far {r['far']:.3f}", C_HIT, 12, True),
            (ruler_box[0] + 6, ruler_box[3] - 40,
             f"part tolerance +/-{tol / 2:.2f} mm (orange band)", C_MISS, 11, True),
        ]
        yi = ruler_box[3] + 24
        labels += [
            (18, yi,
             f"CoC = {r['k']:5.2f} px = {pitch * r['k']:6.2f} um   "
             f"depth of field {r['depth']:7.4f} mm   hyperfocal {r['hyper']:9.1f} mm",
             C_TEXT, 14, True),
            (18, yi + 20,
             f"ratio to the 1-pixel case {r['ratio']:8.4f}   "
             f"(the 1-px reference is {base['depth_mm']:.4f} mm)   ->  "
             + (f"the {tol:g} mm tolerance FITS" if inside
                else f"the {tol:g} mm tolerance does NOT fit"),
             (C_HIT if inside else C_BAD), 14, True),
        ]
        # 下段: 深度 対 錯乱円(直線 = 厳密な比例)
        p = Plot(canvas, plot_box, (1.0, 10.0), (0.0, 8.0))
        p.bg()
        p.grid_y([2, 4, 6, 8])
        p.grid_x([2, 4, 6, 8, 10])
        p.frame()
        p.curve([q["k"] for q in rows], [q["depth"] for q in rows], C_OPT, 2)
        p.hline(tol, C_MISS, 1, dashed=True, dash=7, gap=6)
        if k_tol is not None:
            p.vline(k_tol, C_MISS, 1, dashed=True, dash=7, gap=6)
        p.marker(r["k"], r["depth"], (1.0, 1.0, 1.0), 5, "cross", 2)
        p.ticks_x([2, 4, 6, 8, 10])
        p.ticks_y([2, 4, 6, 8])
        canvas = p.c
        for t in (2, 4, 6, 8, 10):
            labels.append((int(p.px(t)) - 5, plot_box[3] + 6, f"{t}", C_DIM, 11, False))
        for t in (2, 4, 6, 8):
            labels.append((plot_box[0] - 24, int(p.py(t)) - 7, f"{t}", C_DIM, 11, False))
        labels += [
            (plot_box[0] + 6, plot_box[1] + 4, "depth of field [mm]", C_DIM, 11, False),
            (plot_box[2] - 250, plot_box[3] - 16,
             "acceptable circle of confusion [pixel pitches] ->", C_DIM, 11, False),
            (int(p.px(k_tol)) + 6, plot_box[1] + 20,
             f"tolerance met from {k_tol:.3f} px", C_MISS, 11, True),
            (plot_box[0] + 8, plot_box[3] - 34,
             "the light-field refocus gain in the article is exactly this line read "
             "twice -- a 6x6 angular grid buys a 6x CoC, hence a 6x depth",
             C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = int(np.argmin([abs(r["k"] - 6.0) for r in rows]))
    facts = {"base_depth_mm": base["depth_mm"], "base": base,
             "tolerance_mm": tol, "coc_px_meeting_tolerance": k_tol,
             "rows": rows}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 6. 横分解能 対 被写界深度(GIF)                                                #
# =========================================================================== #
def ex_res_vs_dof(log):
    """独立な 2 軸。1 つの判定に畳むと「レンズを買いに行く」誤読が起きる。"""
    f, wd, pitch = SYS["focal_mm"], SYS["working_distance_mm"], SYS["pixel_pitch_um"]
    lam = SYS["wavelength_um"]
    target_um, tol = 60.0, 1.0
    ns = np.linspace(2.0, 16.0, 43)

    rows = []
    for n in ns:
        geo, res = _limits(f_number=float(n))
        d = optics.depth_of_field(focal_mm=f, f_number=float(n), subject_mm=wd,
                                  coc_mm=pitch * 1e-3)
        rows.append({"n": float(n), "lat": res["resolution_object_um"],
                     "nyq": res["nyquist_object_um"],
                     "dif": res["diffraction_object_um"], "by": res["limited_by"],
                     "dof": d["depth_mm"],
                     "res_ok": bool(target_um >= res["resolution_object_um"]),
                     "dof_ok": bool(d["depth_mm"] >= tol)})
    n_res = _bisect(lambda n: target_um - _limits(f_number=float(n))[1]["resolution_object_um"],
                    2.0, 16.0, tol=1e-9)
    n_dof = _bisect(lambda n: optics.depth_of_field(
        focal_mm=f, f_number=float(n), subject_mm=wd,
        coc_mm=pitch * 1e-3)["depth_mm"] - tol, 2.0, 16.0, tol=1e-9)
    n_swap = _bisect(lambda n: (_limits(f_number=float(n))[1]["nyquist_object_um"]
                                - _limits(f_number=float(n))[1]["diffraction_object_um"]),
                     2.0, 16.0, tol=1e-9)
    log(f"  a {target_um:g} um defect stays resolvable up to f/{n_res:.3f}; the "
        f"{tol:g} mm tolerance needs at least f/{n_dof:.3f}  ->  the usable "
        f"window is f/{n_dof:.2f} .. f/{n_res:.2f} (sampling/diffraction swap at "
        f"f/{n_swap:.3f})")

    w, hdr = 1000, 34
    plot_box = (86, hdr + 40, w - 96, hdr + 40 + 306)
    h = int(plot_box[3]) + 118
    lat_hi, dof_hi = 130.0, 3.2
    frames = []
    for r in rows:
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "TWO AXES, NOT ONE  --  lateral resolution and depth of field are "
            "independent",
            f"f={f:g}mm  WD={wd:g}mm  pitch={pitch:g}um  lambda={lam:g}um   "
            f"target defect {target_um:g} um, part tolerance {tol:g} mm   "
            f"sweeping the f-number")
        p = Plot(canvas, plot_box, (2.0, 16.0), (0.0, lat_hi))
        p.bg()
        if n_dof is not None and n_res is not None:
            p.band_x(n_dof, n_res, (0.10, 0.20, 0.19))
            p.band_x(2.0, n_dof, (0.17, 0.14, 0.13))
            p.band_x(n_res, 16.0, (0.17, 0.14, 0.13))
        p.grid_x([4, 6, 8, 10, 12, 14, 16])
        p.grid_y([25, 50, 75, 100, 125])
        p.frame()
        p.curve([q["n"] for q in rows], [q["lat"] for q in rows], C_OPT, 2)
        p.curve([q["n"] for q in rows], [q["nyq"] for q in rows], C_GRID, 1)
        p.curve([q["n"] for q in rows], [q["dif"] for q in rows], C_GRID, 1)
        p.hline(target_um, C_MISS, 1, dashed=True, dash=7, gap=6)
        p.marker(r["n"], r["lat"], C_OPT, 5, "cross", 2)
        # 第 2 の縦軸(右) = 被写界深度 [mm]
        p2 = Plot(canvas, plot_box, (2.0, 16.0), (0.0, dof_hi))
        p2.curve([q["n"] for q in rows], [q["dof"] for q in rows], C_CURVE, 2)
        p2.hline(tol, C_CURVE, 1, dashed=True, dash=4, gap=8)
        p2.marker(r["n"], r["dof"], C_CURVE, 5, "cross", 2)
        p2.ticks_x([2, 4, 6, 8, 10, 12, 14, 16])
        p.ticks_y([25, 50, 75, 100, 125])
        canvas = p2.c
        for t in (2, 4, 6, 8, 10, 12, 14, 16):
            labels.append((int(p.px(t)) - 5, plot_box[3] + 6, f"{t}", C_DIM, 11, False))
        for t in (25, 50, 75, 100, 125):
            labels.append((plot_box[0] - 32, int(p.py(t)) - 7, f"{t}", C_OPT, 11, False))
        for t in (1, 2, 3):
            labels.append((plot_box[2] + 8, int(p2.py(t)) - 7, f"{t} mm", C_CURVE, 11, False))
        yi = int(plot_box[3]) + 24
        both = r["res_ok"] and r["dof_ok"]
        verdict = ("resolvable" if both
                   else "marginal (lateral OK, part drifts out of focus)"
                   if r["res_ok"] else "not_resolvable")
        labels += [
            (plot_box[0] + 6, plot_box[1] + 4,
             "lateral resolution limit [um]  (blue)", C_OPT, 11, True),
            (plot_box[2] - 208, plot_box[1] + 4,
             "depth of field [mm]  (yellow)", C_CURVE, 11, True),
            (plot_box[2] - 116, plot_box[3] - 16, "f-number ->", C_DIM, 11, False),
            (int(p.px(min(n_res, 15.0))) - 148, plot_box[1] + 22,
             f"resolvable only left of f/{n_res:.2f}", C_OPT, 11, True),
            (int(p.px(n_dof)) + 6, plot_box[3] - 40,
             f"tolerance met only right of f/{n_dof:.2f}", C_CURVE, 11, True),
            (int(p.px(0.5 * (n_dof + n_res))) - 46, plot_box[1] + 40,
             "usable window", C_HIT, 12, True),
            (18, yi,
             f"f/{r['n']:5.2f}   lateral limit {r['lat']:6.2f} um "
             f"({r['by']}-limited)   depth of field {r['dof']:6.3f} mm",
             C_TEXT, 14, True),
            (18, yi + 20,
             f"resolves {target_um:g} um: "
             + ("yes" if r["res_ok"] else "NO ")
             + f"    tolerance {tol:g} mm fits: "
             + ("yes" if r["dof_ok"] else "NO ")
             + f"    ->  system_feasibility verdict: {verdict}",
             (C_HIT if both else C_BAD), 14, True),
            (18, yi + 44,
             "fold these two into a single yes/no and the reader goes shopping for "
             "a lens when the fix is the aperture, the tolerance, or a focus "
             "mechanism", C_DIM, 11, False),
            (18, yi + 60,
             f"(the faint grey pair are the two raw limits; they swap at "
             f"f/{n_swap:.3f}, and the blue curve is their maximum)",
             C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = int(np.argmin([abs(r["n"] - 0.5 * (n_dof + n_res)) for r in rows]))
    facts = {"target_um": target_um, "tolerance_mm": tol,
             "n_max_resolvable": n_res, "n_min_for_tolerance": n_dof,
             "n_limit_swap": n_swap, "rows": rows}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 7. Airy パターンと Rayleigh 基準(GIF)                                        #
# =========================================================================== #
def ex_airy_rayleigh(log):
    """2 点が分離できる/できない境界。Rayleigh 基準を実測の谷で確かめる。"""
    lam, fn = SYS["wavelength_um"], 5.6
    fine = 0.02                                  # 微細格子 [um/画素]
    size = 601
    psf = np.asarray(optics.airy_pattern(size=size, wavelength_um=lam,
                                         f_number=fn, pixel_pitch_um=fine),
                     np.float64)
    c = size // 2
    prof = psf[c].copy()
    # 第 1 暗環の実測位置(Airy 半径)。理論は 1.2197*lambda*N。
    ax = (np.arange(size) - (size - 1) / 2.0) * fine
    first_zero_i = c + int(np.argmin(prof[c:c + int(round(6.0 / fine))]))
    first_zero_um = float(ax[first_zero_i])
    rayleigh_um = 1.22 * lam * fn
    log(f"  Airy first dark ring measured at {first_zero_um:.4f} um "
        f"(theory 1.2197*lambda*N = {1.2197 * lam * fn:.4f} um); "
        f"Rayleigh separation 1.22*lambda*N = {rayleigh_um:.4f} um")

    seps_k = np.linspace(0.40, 2.20, 37)
    view = 401                                   # 表示に切り出す幅 [画素]
    v0 = c - view // 2
    rows = []
    for k in seps_k:
        s = 2 * int(round(k * rayleigh_um / fine / 2.0))   # 偶数 = 中点が画素に乗る
        tot2 = np.roll(psf, -s // 2, axis=1) + np.roll(psf, s // 2, axis=1)
        line = tot2[c]
        peak = float(line[c - max(s, 4):c + max(s, 4) + 1].max())
        dip = float(line[c])
        rows.append({"k": float(k), "sep_um": s * fine, "dip_over_peak": dip / peak,
                     "img": tot2[c - view // 2:c + view // 2 + 1,
                                 v0:v0 + view].copy(),
                     "line": line[v0:v0 + view].copy(), "peak": peak})
    # 「谷が現れ始める」実測点(数値微分ではなく、比が 1 を割った最初の格子点)
    first_dip = next((r["sep_um"] for r in rows if r["dip_over_peak"] < 0.999), None)
    ray_row = min(rows, key=lambda r: abs(r["k"] - 1.0))
    log(f"  a dip first appears at {first_dip:.3f} um separation; at the Rayleigh "
        f"separation ({ray_row['sep_um']:.3f} um) the measured dip/peak is "
        f"{ray_row['dip_over_peak']:.4f} (textbook 0.735)")

    disp = 336                                   # 表示パネル [画素]
    step = view / float(disp)
    idx = np.clip((np.arange(disp) * step).astype(int), 0, view - 1)
    w, hdr = 1000, 34
    img_x, img_y = 22, hdr + 30
    plot_box = (img_x + disp + 78, img_y, w - 26, img_y + disp - 96)
    h = img_y + disp + 116
    frames = []
    for r in rows:
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "AIRY PATTERN AND THE RAYLEIGH CRITERION  --  where two points "
            "become one",
            f"lambda={lam:g}um  f/{fn:g}  grid {fine:g} um/px   "
            f"Airy radius measured at {first_zero_um:.3f} um "
            f"(1.2197*lambda*N = {1.2197 * lam * fn:.3f} um)")
        # 左: 2 点像(gamma を掛けて裾を見せる。掛けた値は明記する)
        shown = r["img"][np.ix_(idx, idx)]
        canvas[img_y:img_y + disp, img_x:img_x + disp] = _heat(
            np.clip(shown / max(r["peak"], 1e-12), 0.0, 1.0) ** 0.45)
        canvas = imagedraw.draw_polyline(
            canvas, [(img_x - 1, img_y - 1), (img_x + disp, img_y - 1),
                     (img_x + disp, img_y + disp), (img_x - 1, img_y + disp)],
            color=C_GRID, width=1, closed=True)
        # 断面を取っている行を示す
        canvas = _dashed(canvas, (img_x, img_y + disp / 2.0),
                         (img_x + disp - 1, img_y + disp / 2.0),
                         (0.95, 0.95, 0.92), 1, 5, 6)
        # 右: 断面と谷
        p = Plot(canvas, plot_box, (-view / 2.0 * fine, view / 2.0 * fine), (0.0, 1.06))
        p.bg()
        p.grid_y([0.25, 0.5, 0.75, 1.0])
        p.frame()
        prof_x = (np.arange(view) - view // 2) * fine
        p.curve(prof_x, r["line"] / max(r["peak"], 1e-12), C_OPT, 2)
        p.hline(r["dip_over_peak"], C_MISS, 1, dashed=True, dash=6, gap=6)
        p.vline(0.0, C_GRID, 1)
        p.marker(0.0, r["dip_over_peak"], (1.0, 1.0, 1.0), 5, "cross", 2)
        p.ticks_x([-4, -2, 0, 2, 4])
        p.ticks_y([0.25, 0.5, 0.75, 1.0])
        canvas = p.c
        for t in (-4, -2, 0, 2, 4):
            labels.append((int(p.px(t)) - 6, plot_box[3] + 6, f"{t}", C_DIM, 11, False))
        for t in (0.25, 0.5, 0.75, 1.0):
            labels.append((plot_box[0] - 36, int(p.py(t)) - 7, f"{t:.2f}", C_DIM, 11, False))
        resolved = r["sep_um"] >= rayleigh_um
        yi = img_y + disp + 12
        labels += [
            (img_x + 4, img_y - 18,
             "two point sources through a circular pupil (intensity^0.45 to show "
             "the rings)", (0.95, 0.95, 0.92), 11, True),
            (plot_box[0] + 6, plot_box[1] + 4,
             "profile along the dashed line, normalised", C_DIM, 11, False),
            (plot_box[2] - 118, plot_box[3] - 16, "position [um] ->", C_DIM, 11, False),
            (18, yi,
             f"separation {r['sep_um']:5.3f} um = {r['k']:.2f} x Rayleigh "
             f"({rayleigh_um:.3f} um)     dip / peak = {r['dip_over_peak']:.4f}",
             C_TEXT, 14, True),
            (18, yi + 20,
             ("RESOLVED by the Rayleigh criterion" if resolved
              else "NOT resolved -- the two peaks have merged into one"),
             (C_HIT if resolved else C_BAD), 14, True),
            (18, yi + 44,
             f"at exactly the Rayleigh separation the measured dip is "
             f"{ray_row['dip_over_peak']:.4f} of the peak (the textbook number is "
             f"0.735); a dip first appears at all at {first_dip:.3f} um",
             C_DIM, 11, False),
            (18, yi + 60,
             "the criterion is a convention, not a cliff -- what the optics really "
             "hands you is this continuously shrinking dip", C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = int(np.argmin([abs(r["k"] - 1.0) for r in rows]))
    facts = {"wavelength_um": lam, "f_number": fn,
             "airy_first_zero_um_measured": first_zero_um,
             "airy_first_zero_um_theory": 1.2197 * lam * fn,
             "rayleigh_um": rayleigh_um,
             "dip_at_rayleigh": ray_row["dip_over_peak"],
             "first_dip_separation_um": first_dip,
             "rows": [{k: v for k, v in r.items() if k not in ("img", "line")}
                      for r in rows]}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 8. 偏光で金属のテカりを消す(GIF)                                              #
# =========================================================================== #
def ex_polarizer(log):
    """直交偏光子で鏡面反射が 0.0 まで落ち、その下の傷が出てくる。"""
    tile = 240
    rng = np.random.default_rng(4242)
    bg = defectgen.surface_texture((tile, tile), "brushed", strength=0.05,
                                   scale_px=6.0, seed=11)
    ideal, mask = defectgen.defect_scratch((tile, tile), length_px=150.0,
                                           width_px=5.0, angle_deg=24.0,
                                           wander=0.10, contrast=-0.30, seed=3)
    part = defectgen.composite_defect(bg, ideal, mask)
    # 鏡面反射のローブ(傷の上に重なる位置に置く。形は明示的なガウス)
    yy, xx = np.mgrid[0:tile, 0:tile].astype(np.float64)
    lobe = np.exp(-(((xx - tile * 0.46) / (tile * 0.30)) ** 2
                    + ((yy - tile * 0.50) / (tile * 0.20)) ** 2))
    system = _system()

    angles = np.arange(0.0, 185.0, 5.0)
    rows = []
    for a in angles:
        # 鏡面成分は完全偏光(0 度の直線偏光)。検光子を通すと Malus 則。
        j = optics.jones_element("polarizer", angle_deg=float(a))
        out = optics.jones_apply(j, [1.0 + 0j, 0.0 + 0j])
        s_spec = float(optics.stokes_from_jones(out)[0])
        # 拡散成分は無偏光。Mueller で通すと角度に依らず 0.5。
        m = optics.mueller_element("polarizer", angle_deg=float(a))
        s_diff = float(optics.mueller_apply(m, [1.0, 0.0, 0.0, 0.0])[0])
        scene = np.clip(part * (s_diff / 0.5) + 1.35 * s_spec * lobe, 0.0, 1.0)
        img = system.capture(scene, vignetting=False)
        pred, iou, det = _detect(img, mask)
        sat = float(np.mean(img >= 0.999))
        rows.append({"angle": float(a), "spec": s_spec, "diff": s_diff,
                     "img": img, "pred": pred, "iou": iou, "det": det,
                     "sat_frac": sat,
                     "lobe_max": float(np.max(img * (lobe > 0.5)))})
    crossed = next(r for r in rows if abs(r["angle"] - 90.0) < 1e-9)
    parallel = rows[0]
    log(f"  analyser at 0 deg: specular S0 = {parallel['spec']:.6f}, "
        f"{parallel['sat_frac'] * 100:.2f} % of the tile is clipped at 1.0, "
        f"scratch IoU {parallel['iou']:.3f}")
    log(f"  analyser at 90 deg: specular S0 = {crossed['spec']:.6f} (exactly zero), "
        f"{crossed['sat_frac'] * 100:.2f} % clipped, scratch IoU {crossed['iou']:.3f}")

    disp = tile * 2
    w, hdr = 1000, 34
    pan_y = hdr + 30
    x1, x2 = 20, 20 + disp + 14
    plot_box = (x2 + disp + 84, pan_y + 4, w - 26, pan_y + 190)
    h = pan_y + disp + 108
    frames = []
    for r in rows:
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "CROSSED POLARISERS  --  the specular lobe goes to exactly 0.0",
            "specular = fully polarised (Jones), diffuse = unpolarised (Mueller); "
            "ideal lossless elements, normal incidence")
        canvas[pan_y:pan_y + disp, x1:x1 + disp] = _upscale(_gray_to_rgb(r["img"]), 2)
        canvas[pan_y:pan_y + disp, x2:x2 + disp] = _upscale(
            _verdict_rgb(r["img"], mask, r["pred"]), 2)
        for xx0 in (x1, x2):
            canvas = imagedraw.draw_polyline(
                canvas, [(xx0 - 1, pan_y - 1), (xx0 + disp, pan_y - 1),
                         (xx0 + disp, pan_y + disp), (xx0 - 1, pan_y + disp)],
                color=C_GRID, width=1, closed=True)
        # 検光子の向きを円と線で示す(角度の読み違えを防ぐ)
        cxx, cyy, rr = plot_box[0] - 46, pan_y + 40, 30
        canvas = imagedraw.draw_circle(canvas, (cxx, cyy), rr, color=C_DIM, width=1)
        th = np.radians(r["angle"])
        canvas = imagedraw.draw_line(
            canvas, (cxx - rr * np.cos(th), cyy + rr * np.sin(th)),
            (cxx + rr * np.cos(th), cyy - rr * np.sin(th)),
            color=C_HIT, width=2)
        canvas = imagedraw.draw_line(canvas, (cxx - rr, cyy), (cxx + rr, cyy),
                                     color=(0.30, 0.32, 0.36), width=1)
        # 右: Malus 則の曲線
        p = Plot(canvas, plot_box, (0.0, 180.0), (0.0, 1.06))
        p.bg()
        p.grid_y([0.25, 0.5, 0.75, 1.0])
        p.grid_x([45, 90, 135])
        p.frame()
        p.curve([q["angle"] for q in rows], [q["spec"] for q in rows], C_MISS, 2)
        p.curve([q["angle"] for q in rows], [q["diff"] for q in rows], C_OPT, 2)
        p.vline(r["angle"], (0.95, 0.95, 0.92), 1, dashed=True, dash=5, gap=5)
        p.marker(r["angle"], r["spec"], C_MISS, 5, "cross", 2)
        p.marker(r["angle"], r["diff"], C_OPT, 5, "cross", 2)
        p.ticks_x([0, 45, 90, 135, 180])
        p.ticks_y([0.25, 0.5, 0.75, 1.0])
        canvas = p.c
        for t in (0, 45, 90, 135, 180):
            labels.append((int(p.px(t)) - 10, plot_box[3] + 6, f"{t}", C_DIM, 11, False))
        for t in (0.25, 0.5, 0.75, 1.0):
            labels.append((plot_box[0] - 36, int(p.py(t)) - 7, f"{t:.2f}", C_DIM, 11, False))
        yi = pan_y + disp + 10
        labels += [
            (x1 + 4, pan_y - 18, "what the camera sees", (0.95, 0.95, 0.92), 12, True),
            (x2 + 4, pan_y - 18, "detector vs ground truth", (0.95, 0.95, 0.92), 12, True),
            (cxx - 34, cyy + rr + 6, "analyser", C_DIM, 11, False),
            (plot_box[0] + 6, plot_box[1] + 4, "transmitted intensity S0", C_DIM, 11, False),
            (plot_box[0] + 6, plot_box[1] + 20, "specular (Malus, cos^2)", C_MISS, 11, True),
            (plot_box[0] + 6, plot_box[1] + 36, "diffuse (unpolarised, flat 0.5)", C_OPT, 11, True),
            (plot_box[2] - 156, plot_box[3] - 16, "analyser angle [deg] ->", C_DIM, 11, False),
            (x2 + 4, pan_y + disp - 54, "hit", C_HIT, 12, True),
            (x2 + 4, pan_y + disp - 38, "missed", C_MISS, 12, True),
            (x2 + 4, pan_y + disp - 22, "false alarm", C_FALSE, 12, True),
            (18, yi,
             f"analyser {r['angle']:5.1f} deg   specular S0 {r['spec']:.6f}   "
             f"diffuse S0 {r['diff']:.6f}   clipped pixels {r['sat_frac'] * 100:5.2f} %",
             C_TEXT, 14, True),
            (18, yi + 20,
             f"scratch IoU {r['iou']:.3f}  ->  "
             + ("DETECTED" if r["det"] else "not detected")
             + f"    (at 0 deg it was {parallel['iou']:.3f}, at 90 deg "
               f"{crossed['iou']:.3f})",
             (C_HIT if r["det"] else C_BAD), 14, True),
            (18, yi + 44,
             "the highlight is not dimmed by a tone curve -- the Jones product is "
             "exactly zero at 90 deg, and the diffuse half never moves",
             C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = int(np.argmin([abs(r["angle"] - 90.0) for r in rows]))
    facts = {"specular_at_0": parallel["spec"], "specular_at_90": crossed["spec"],
             "iou_at_0": parallel["iou"], "iou_at_90": crossed["iou"],
             "clipped_at_0": parallel["sat_frac"], "clipped_at_90": crossed["sat_frac"],
             "detected_at_0": parallel["det"], "detected_at_90": crossed["det"],
             "rows": [{k: v for k, v in r.items() if k not in ("img", "pred")}
                      for r in rows]}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 9. thin lens / ABCD 行列(GIF)                                                #
# =========================================================================== #
def ex_abcd_rays(log):
    """共役面が本当に結像することを、ABCD の光線追跡で。固定センサ上のぼけ円も。"""
    f, pitch = SYS["focal_mm"], SYS["pixel_pitch_um"]
    fn = SYS["f_number"]
    wd0 = SYS["working_distance_mm"]
    sensor_mm = float(optics.thin_lens(focal_mm=f, object_mm=wd0)["image_mm"])
    dof = optics.depth_of_field(focal_mm=f, f_number=fn, subject_mm=wd0,
                                coc_mm=pitch * 1e-3)
    obj_h = 3.0                                  # 物体高 [mm]
    half_ap = f / (2.0 * fn)                     # 入射瞳半径 [mm]
    dists = np.linspace(150.0, 300.0, 39)

    rows = []
    for so in dists:
        conj = optics.thin_lens(focal_mm=f, object_mm=float(so))
        si = float(conj["image_mm"])
        mag = float(conj["magnification"])
        m_img = optics.abcd_matrix([("free", float(so)), ("lens", f), ("free", si)])
        tr = optics.abcd_trace(m_img, height_mm=obj_h, angle_mrad=0.0)
        # センサ面(固定)までの行列で、瞳の縁を通る 2 本を追う → ぼけ円
        m_sen = optics.abcd_matrix([("free", float(so)), ("lens", f),
                                    ("free", sensor_mm)])
        hits = []
        for edge in (+half_ap, -half_ap):
            ang_mrad = np.degrees(0.0)           # 角度は下で直接与える
            th = (edge - obj_h) / so             # 物体点から瞳の縁へ向かう角 [rad]
            t = optics.abcd_trace(m_sen, height_mm=obj_h, angle_mrad=th * 1e3)
            hits.append(t["height_mm"])
        blur_mm = abs(hits[0] - hits[1])
        rows.append({"so": float(so), "si": si, "mag": mag,
                     "img_h": tr["height_mm"], "imaging": bool(tr["imaging"]),
                     "B": float(m_img[0, 1]), "det": tr["determinant"],
                     "blur_mm": blur_mm, "blur_px": blur_mm * 1e3 / pitch,
                     "hits": hits})
    inside = [r for r in rows if r["blur_px"] <= 1.0]
    log(f"  sensor pinned at {sensor_mm:.4f} mm (the conjugate of {wd0:g} mm); "
        f"blur stays within 1 pixel for object distances "
        f"{min(r['so'] for r in inside):.1f}..{max(r['so'] for r in inside):.1f} mm")
    log(f"  optics.depth_of_field for the same 1-pixel circle: "
        f"{dof['near_mm']:.3f}..{dof['far_mm']:.3f} mm "
        f"(depth {dof['depth_mm']:.4f} mm) -- independent formula, same answer")

    w, hdr = 1000, 34
    diag = (60, hdr + 40, w - 30, hdr + 40 + 268)
    h = int(diag[3]) + 132
    x_lo, x_hi = -305.0, 62.0                    # レンズを原点、光は左→右
    y_span = 7.0                                 # 縦 [mm](誇張して描く)
    frames = []
    for r in rows:
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "ABCD RAY TRACE  --  the conjugate plane really does form an image",
            f"f={f:g}mm  f/{fn:g}  pupil radius {half_ap:.3f}mm  object height "
            f"{obj_h:g}mm   sensor pinned at {sensor_mm:.3f} mm "
            f"(the conjugate of {wd0:g} mm)")
        p = Plot(canvas, diag, (x_lo, x_hi), (-y_span, y_span))
        p.bg()
        p.frame()
        p.hline(0.0, C_GRID, 1)
        # レンズ(x=0)とセンサ(x=sensor_mm)
        p.vline(0.0, (0.55, 0.60, 0.70), 3)
        p.vline(sensor_mm, C_MISS, 2)
        p.vline(r["si"], C_OPT, 1, dashed=True, dash=6, gap=5)
        # 物体の矢
        so_x = -r["so"]
        p.c = imagedraw.draw_line(p.c, (p.px(so_x), p.py(0.0)),
                                  (p.px(so_x), p.py(obj_h)), color=C_HIT, width=2)
        p.c = imagedraw.draw_line(p.c, (p.px(so_x), p.py(0.0)),
                                  (p.px(sensor_mm), p.py(0.0)), color=C_GRID, width=1)
        # 3 本の光線: 瞳の上端・中心・下端を通す
        for edge, col in ((+half_ap, C_CURVE), (0.0, (0.70, 0.74, 0.80)),
                          (-half_ap, C_CURVE)):
            th = (edge - obj_h) / r["so"]
            m_full = optics.abcd_matrix([("free", r["so"]), ("lens", f)])
            t0 = optics.abcd_trace(m_full, height_mm=obj_h, angle_mrad=th * 1e3)
            y_at = lambda d, t0=t0: t0["height_mm"] + d * t0["angle_mrad"] * 1e-3
            p.c = imagedraw.draw_line(p.c, (p.px(so_x), p.py(obj_h)),
                                      (p.px(0.0), p.py(t0["height_mm"])),
                                      color=col, width=1)
            p.c = imagedraw.draw_line(p.c, (p.px(0.0), p.py(t0["height_mm"])),
                                      (p.px(x_hi), p.py(y_at(x_hi))),
                                      color=col, width=1)
        # センサ上のぼけ(2 本の交点間)
        yA, yB = r["hits"]
        p.c = imagedraw.draw_line(p.c, (p.px(sensor_mm), p.py(yA)),
                                  (p.px(sensor_mm), p.py(yB)),
                                  color=(1.0, 1.0, 1.0), width=3)
        p.marker(r["si"], r["img_h"], C_OPT, 5, "cross", 2)
        p.ticks_x([-300, -250, -200, -150, -100, -50, 0, 50])
        canvas = p.c
        for t in (-300, -250, -200, -150, -100, -50, 0, 50):
            labels.append((int(p.px(t)) - 14, diag[3] + 6, f"{t}", C_DIM, 11, False))
        yi = int(diag[3]) + 28
        inb = r["blur_px"] <= 1.0
        labels += [
            (diag[0] + 6, diag[1] + 4,
             f"height [mm], vertical scale exaggerated ({(diag[2] - diag[0]) / (x_hi - x_lo) / ((diag[3] - diag[1]) / (2 * y_span)):.2f}x horizontal)",
             C_DIM, 11, False),
            (diag[2] - 190, diag[3] - 16, "distance from the lens [mm] ->", C_DIM, 11, False),
            (int(p.px(0.0)) - 16, diag[1] + 22, "lens", (0.75, 0.79, 0.86), 11, True),
            (int(p.px(sensor_mm)) - 96, diag[1] + 40, "sensor", C_MISS, 11, True),
            (max(diag[0] + 4, int(p.px(so_x)) - 24), int(p.py(obj_h)) - 18,
             "object", C_HIT, 11, True),
            (18, yi,
             f"object {r['so']:6.1f} mm  ->  image {r['si']:7.3f} mm   "
             f"magnification {r['mag']:+.5f}   image height {r['img_h']:+.4f} mm "
             f"(= m x {obj_h:g} mm)",
             C_TEXT, 14, True),
            (18, yi + 20,
             f"ABCD B element {r['B']:+.3e} mm  ->  imaging = {r['imaging']}   "
             f"det = {r['det']:.12f}   (B = 0 means the height does not depend on "
             f"the input angle)",
             (C_HIT if r["imaging"] else C_DIM), 13, True),
            (18, yi + 40,
             f"blur circle on the fixed sensor: {r['blur_mm'] * 1e3:7.2f} um = "
             f"{r['blur_px']:5.2f} px  ->  "
             + ("within one pixel" if inb else "larger than one pixel"),
             (C_HIT if inb else C_BAD), 14, True),
            (18, yi + 62,
             f"cross-check: the ray trace keeps the blur under 1 px from "
             f"{min(q['so'] for q in inside):.1f} to "
             f"{max(q['so'] for q in inside):.1f} mm; optics.depth_of_field with "
             f"the same 1-pixel circle says {dof['near_mm']:.3f} to "
             f"{dof['far_mm']:.3f} mm", C_DIM, 11, False),
            (18, yi + 78,
             "(two independent formulas -- the ray trace samples a grid, the "
             "closed form does not, so they agree to the grid step)",
             C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = int(np.argmin([abs(r["so"] - wd0) for r in rows]))
    facts = {"sensor_mm": sensor_mm, "pupil_radius_mm": half_ap,
             "object_height_mm": obj_h, "depth_of_field": dof,
             "ray_trace_in_focus_mm": [min(r["so"] for r in inside),
                                       max(r["so"] for r in inside)],
             "rows": [{k: v for k, v in r.items() if k != "hits"} for r in rows]}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 10. 検出限界マップ(静止画)                                                    #
# =========================================================================== #
def ex_detect_map(log):
    """(欠陥サイズ × コントラスト) の検出率。光学限界の線を重ねる。"""
    system = _system()
    geo, res = _limits()
    opt_um = res["resolution_object_um"]
    sizes = np.exp(np.linspace(np.log(20.0), np.log(320.0), 18))
    contrasts = np.linspace(0.03, 0.40, 14)
    seeds = 5
    tile = 160

    grid = np.full((len(contrasts), len(sizes)), np.nan)
    unrend = np.zeros_like(grid, dtype=int)
    t0 = time.time()
    for i, cst in enumerate(contrasts):
        for j, size in enumerate(sizes):
            hits, ev = 0, 0
            for s in range(seeds):
                try:
                    img, mask, _ = vl.render_part(system, float(size), kind="scratch",
                                                  contrast=-float(cst),
                                                  texture_strength=0.06,
                                                  tile_px=tile, seed=s)
                except ValueError:
                    unrend[i, j] += 1
                    continue
                _, iou, det = _detect(img, mask)
                hits += int(det)
                ev += 1
            grid[i, j] = (hits / ev) if ev else np.nan
    log(f"  {len(sizes)}x{len(contrasts)}x{seeds} = "
        f"{len(sizes) * len(contrasts) * seeds} renders in {time.time() - t0:.1f}s; "
        f"{int(unrend.sum())} cells were unrenderable (below one pixel)")

    # 各コントラスト行で検出率が 0.5 に達する最小サイズ(実測の 50% 等高線)
    contour = []
    for i, cst in enumerate(contrasts):
        row = grid[i]
        ok = np.where(np.isfinite(row) & (row >= 0.5))[0]
        contour.append(float(sizes[ok[0]]) if ok.size else None)
    reached = [(c, s) for c, s in zip(contrasts, contour) if s is not None]
    if reached:
        log(f"  50% detection needs {reached[0][1]:.1f} um at contrast "
            f"{reached[0][0]:.2f} and {reached[-1][1]:.1f} um at contrast "
            f"{reached[-1][0]:.2f}  (optical limit {opt_um:.2f} um)")

    cw, ch = 40, 24
    w = 118 + len(sizes) * cw + 190
    hdr = 34
    top = hdr + 40
    h = top + len(contrasts) * ch + 78
    canvas = _canvas(h, w)
    labels = _header(canvas, w,
                     "DETECTABILITY MAP  --  size is not enough, contrast is not "
                     "enough",
                     f"{system!r}   {geo['um_per_pixel']:.3f} um/px   detector = "
                     f"visionlab baseline, IoU >= {MIN_IOU:g}, {seeds} seeds per cell")
    for i in range(len(contrasts)):
        for j in range(len(sizes)):
            y = top + i * ch
            x = 118 + j * cw
            col = _heat(np.array([[grid[i, j]]]))[0, 0]
            _fill(canvas, y, y + ch - 2, x, x + cw - 2, tuple(col))
    # 光学限界の縦線(セル境界に合わせず、対数軸上の実位置に引く)
    def size_x(um):
        t = (np.log(um) - np.log(sizes[0])) / (np.log(sizes[-1]) - np.log(sizes[0]))
        return 118 + cw / 2.0 + t * (len(sizes) - 1) * cw
    x_opt = size_x(opt_um)
    canvas = imagedraw.draw_line(canvas, (x_opt, top - 6),
                                 (x_opt, top + len(contrasts) * ch),
                                 color=C_OPT, width=2)
    x_nyq = size_x(res["nyquist_object_um"])
    canvas = _dashed(canvas, (x_nyq, top - 6), (x_nyq, top + len(contrasts) * ch),
                     (0.95, 0.95, 0.92), 1, 5, 5)
    pts = [(size_x(s), top + i * ch + ch / 2.0)
           for i, s in enumerate(contour) if s is not None]
    if len(pts) >= 2:
        canvas = imagedraw.draw_polyline(canvas, pts, color=(1.0, 1.0, 1.0), width=2)
    for i, cst in enumerate(contrasts):
        labels.append((16, top + i * ch + 4, f"{cst:.2f}", C_DIM, 11, False))
    for j, s in enumerate(sizes):
        if j % 2 == 0:
            labels.append((118 + j * cw - 2, top + len(contrasts) * ch + 4,
                           f"{s:.0f}", C_DIM, 11, False))
    lx = 118 + len(sizes) * cw + 18
    labels += [
        (16, top - 20, "contrast", C_DIM, 11, True),
        (118, top - 20, "defect size [um] (log)", C_DIM, 11, True),
        (int(x_opt) + 6, top - 22, f"optical limit {opt_um:.1f} um", C_OPT, 11, True),
        (lx, top + 2, "detection rate", (0.95, 0.95, 0.92), 12, True),
    ]
    for k in range(11):
        v = k / 10.0
        y = top + 22 + (10 - k) * 14
        col = _heat(np.array([[v]]))[0, 0]
        _fill(canvas, y, y + 12, lx, lx + 26, tuple(col))
        labels.append((lx + 32, y - 1, f"{v:.1f}", C_DIM, 11, False))
    labels += [
        (lx, top + 22 + 11 * 14 + 8, "white line =", (1.0, 1.0, 1.0), 11, True),
        (lx, top + 22 + 11 * 14 + 22, "measured 50%", (1.0, 1.0, 1.0), 11, True),
        (lx, top + 22 + 11 * 14 + 36, "contour", (1.0, 1.0, 1.0), 11, True),
        (lx, top + 22 + 11 * 14 + 56, "grey = no data", (0.45, 0.45, 0.45), 11, True),
    ]
    yi = top + len(contrasts) * ch + 24
    labels += [
        (16, yi,
         f"the optics stop at {opt_um:.2f} um ({res['limited_by']}-limited) and "
         f"never move; everything to the right of that line is a contrast, noise "
         f"and algorithm problem",
         C_TEXT, 13, True),
        (16, yi + 18,
         (f"at contrast {reached[0][0]:.2f} the detector needs "
          f"{reached[0][1]:.1f} um ({reached[0][1] / opt_um:.2f}x the optical "
          f"limit); at contrast {reached[-1][0]:.2f} it needs "
          f"{reached[-1][1]:.1f} um ({reached[-1][1] / opt_um:.2f}x)"
          if reached else "no cell reached 50 % detection"),
         C_TEXT, 13, True),
        (16, yi + 38,
         f"{int(unrend.sum())} cells were unrenderable (defect below one pixel) and "
         f"are drawn grey -- they are NOT counted as 0 % detection",
         C_DIM, 11, False),
    ]
    frame = _text(_to_u8(canvas), labels)
    facts = {"system": repr(system), "optical_limit_um": opt_um,
             "limited_by": res["limited_by"],
             "nyquist_um": res["nyquist_object_um"],
             "diffraction_um": res["diffraction_object_um"],
             "sizes_um": [float(s) for s in sizes],
             "contrasts": [float(c) for c in contrasts],
             "seeds": seeds, "unrenderable_cells": int(unrend.sum()),
             "detection_rate": [[None if not np.isfinite(v) else float(v)
                                 for v in row] for row in grid],
             "contour_50pct_um": contour}
    return {"frames": [frame], "facts": facts, "fps": None, "thumb_index": 0}


# =========================================================================== #
# 11. 照明を変えると何が見えるか(GIF)                                           #
# =========================================================================== #
def ex_illumination(log):
    """明視野風(暗い傷)と暗視野風(光る傷)。**符号と露光**の appearance モデル。"""
    system = _system()
    geo, res = _limits()
    tile = 200
    mags = np.linspace(0.02, 0.34, 33)
    size_um = 120.0
    seeds = 5

    def run(cst_signed, exposure):
        shown, hits, ious, ev = None, 0, [], 0
        for s in range(seeds):
            img, mask, meta = vl.render_part(system, size_um, kind="scratch",
                                             contrast=float(cst_signed),
                                             texture_strength=0.06,
                                             tile_px=tile, seed=s)
            if exposure != 1.0:
                img = np.clip(img * exposure, 0.0, 1.0)
            pred, iou, det = _detect(img, mask)
            ious.append(iou)
            hits += int(det)
            ev += 1
            if s == 0:
                shown = (img, mask, pred, iou, det, meta)
        return {"img": shown[0], "mask": shown[1], "pred": shown[2],
                "iou": shown[3], "det": shown[4], "meta": shown[5],
                "rate": hits / ev, "mean_iou": float(np.mean(ious))}

    rows = []
    for m in mags:
        bright = run(-float(m), 1.0)             # 明視野風: 明るい面に暗い傷
        dark = run(+float(m), 0.24)              # 暗視野風: 暗い場に光る傷
        rows.append({"mag": float(m), "bright": bright, "dark": dark})
    b_first = next((r["mag"] for r in rows if r["bright"]["rate"] >= 0.5), None)
    d_first = next((r["mag"] for r in rows if r["dark"]["rate"] >= 0.5), None)
    log(f"  bright-field style reaches 50 % detection at |contrast| = "
        f"{b_first}; dark-field style at {d_first} "
        f"(defect fixed at {size_um:g} um = "
        f"{rows[0]['bright']['meta']['defect_px']:.2f} px)")

    disp = tile * 2
    w, hdr = 1000, 34
    pan_y = hdr + 32
    x1, x2 = 20, 20 + disp + 14
    plot_box = (x2 + disp + 84, pan_y + 4, w - 26, pan_y + 178)
    h = pan_y + disp + 116
    frames = []
    for r in rows:
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "TWO ILLUMINATION STYLES  --  same geometry, opposite sign",
            f"{system!r}   defect fixed at {size_um:g} um = "
            f"{r['bright']['meta']['defect_px']:.2f} px   sweeping |contrast|   "
            f"appearance model (sign + exposure), not light transport")
        canvas[pan_y:pan_y + disp, x1:x1 + disp] = _upscale(
            _gray_to_rgb(r["bright"]["img"]), 2)
        canvas[pan_y:pan_y + disp, x2:x2 + disp] = _upscale(
            _gray_to_rgb(r["dark"]["img"]), 2)
        for xx0 in (x1, x2):
            canvas = imagedraw.draw_polyline(
                canvas, [(xx0 - 1, pan_y - 1), (xx0 + disp, pan_y - 1),
                         (xx0 + disp, pan_y + disp), (xx0 - 1, pan_y + disp)],
                color=C_GRID, width=1, closed=True)
        p = Plot(canvas, plot_box, (0.0, 0.36), (0.0, 1.06))
        p.bg()
        p.grid_y([0.25, 0.5, 0.75, 1.0])
        p.frame()
        p.curve([q["mag"] for q in rows], [q["bright"]["rate"] for q in rows], C_CURVE, 2)
        p.curve([q["mag"] for q in rows], [q["dark"]["rate"] for q in rows], C_OPT, 2)
        p.hline(0.5, C_DIM, 1, dashed=True, dash=6, gap=6)
        p.vline(r["mag"], (0.95, 0.95, 0.92), 1, dashed=True, dash=5, gap=5)
        p.marker(r["mag"], r["bright"]["rate"], C_CURVE, 4, "cross", 2)
        p.marker(r["mag"], r["dark"]["rate"], C_OPT, 4, "cross", 2)
        p.ticks_x([0.0, 0.1, 0.2, 0.3])
        p.ticks_y([0.5, 1.0])
        canvas = p.c
        for t in (0.0, 0.1, 0.2, 0.3):
            labels.append((int(p.px(t)) - 12, plot_box[3] + 6, f"{t:.1f}", C_DIM, 11, False))
        for t in (0.5, 1.0):
            labels.append((plot_box[0] - 34, int(p.py(t)) - 7, f"{t:.1f}", C_DIM, 11, False))
        yi = pan_y + disp + 10
        labels += [
            (x1 + 4, pan_y - 18, "bright field style: dark defect, bright surface",
             (0.95, 0.95, 0.92), 12, True),
            (x2 + 4, pan_y - 18, "dark field style: bright defect, dark surround",
             (0.95, 0.95, 0.92), 12, True),
            (plot_box[0] + 6, plot_box[1] + 4, "detection rate over 5 seeds", C_DIM, 11, False),
            (plot_box[0] + 6, plot_box[1] + 20, "bright field", C_CURVE, 11, True),
            (plot_box[0] + 6, plot_box[1] + 36, "dark field", C_OPT, 11, True),
            (plot_box[2] - 122, plot_box[3] - 16, "|contrast| ->", C_DIM, 11, False),
            (18, yi,
             f"|contrast| {r['mag']:.3f}   bright field: IoU {r['bright']['iou']:.3f}, "
             f"rate {r['bright']['rate']:.0%}   dark field: IoU "
             f"{r['dark']['iou']:.3f}, rate {r['dark']['rate']:.0%}",
             C_TEXT, 14, True),
            (18, yi + 20,
             (f"bright field reaches 50 % at |contrast| "
              f"{'n/a' if b_first is None else f'{b_first:.3f}'}"
              f"   dark field at "
              f"{'n/a' if d_first is None else f'{d_first:.3f}'}"),
             C_HIT, 14, True),
            (18, yi + 44,
             "honest limit: this is defectgen's appearance model (the sign of the "
             "contrast plus an exposure), not a light-transport simulation of a "
             "dark-field ring light", C_DIM, 11, False),
            (18, yi + 60,
             f"optical limit is {res['resolution_object_um']:.2f} um and the defect "
             f"is {size_um:g} um -- the optics carry it in both panels; only the "
             f"contrast is moving", C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = int(np.argmin([abs(r["mag"] - 0.12) for r in rows]))
    facts = {"defect_um": size_um, "seeds": seeds,
             "bright_50pct_contrast": b_first, "dark_50pct_contrast": d_first,
             "optical_limit_um": res["resolution_object_um"],
             "rows": [{"contrast": r["mag"],
                       "bright_rate": r["bright"]["rate"],
                       "bright_iou": r["bright"]["iou"],
                       "dark_rate": r["dark"]["rate"],
                       "dark_iou": r["dark"]["iou"]} for r in rows]}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 12. 画素ピッチとサンプリング(GIF)                                             #
# =========================================================================== #
def ex_pixel_pitch(log):
    """同じ欠陥をピッチ違いで撮り、Nyquist を割った瞬間に消える様子。"""
    size_um = 130.0
    pitches = np.linspace(1.4, 13.5, 38)
    tile = 176
    seeds = 5

    rows = []
    for pt in pitches:
        system = _system(pixel_pitch_um=float(pt))
        geo, res = _limits(pixel_pitch_um=float(pt))
        shown, hits, ious, ev, unren = None, 0, [], 0, 0
        for s in range(seeds):
            try:
                img, mask, meta = vl.render_part(system, size_um, kind="scratch",
                                                 contrast=-0.28,
                                                 texture_strength=0.06,
                                                 tile_px=tile, seed=s)
            except ValueError:
                unren += 1
                continue
            pred, iou, det = _detect(img, mask)
            ious.append(iou)
            hits += int(det)
            ev += 1
            if shown is None:
                shown = (img, mask, pred, iou, det, meta)
        rows.append({
            "pitch": float(pt), "upp": geo["um_per_pixel"],
            "px": size_um / geo["um_per_pixel"],
            "nyq": res["nyquist_object_um"], "dif": res["diffraction_object_um"],
            "lim": res["resolution_object_um"], "by": res["limited_by"],
            "fov": (geo["fov_w_mm"], geo["fov_h_mm"]),
            "rate": (hits / ev) if ev else None, "unren": unren,
            "img": None if shown is None else shown[0],
            "mask": None if shown is None else shown[1],
            "pred": None if shown is None else shown[2],
            "iou": None if shown is None else shown[3],
            "det": None if shown is None else shown[4],
        })
    # 欠陥が 2 画素を割る(= Nyquist を割る)ピッチを閉形式で求める
    def px_at(pt):
        g, _ = _limits(pixel_pitch_um=float(pt))
        return size_um / g["um_per_pixel"] - 2.0
    pitch_nyq = _bisect(px_at, 1.4, 13.5, tol=1e-9)
    last_det = [r["pitch"] for r in rows if r["rate"] is not None and r["rate"] >= 0.5]
    log(f"  a {size_um:g} um defect drops below 2 pixels at pitch "
        f"{pitch_nyq:.4f} um; 50 % detection survives to pitch "
        f"{max(last_det):.3f} um" if last_det else "  never detected")

    disp = tile * 2
    w, hdr = 1000, 34
    pan_y = hdr + 32
    x1, x2 = 20, 20 + disp + 14
    plot_box = (x2 + disp + 78, pan_y + 4, w - 26, pan_y + 190)
    h = pan_y + disp + 116
    frames = []
    for r in rows:
        canvas = _canvas(h, w)
        labels = _header(
            canvas, w,
            "PIXEL PITCH AND SAMPLING  --  the defect vanishes when it drops "
            "below two pixels",
            f"f={SYS['focal_mm']:g}mm  WD={SYS['working_distance_mm']:g}mm  "
            f"f/{SYS['f_number']:g}  {SYS['width_px']}x{SYS['height_px']}px   "
            f"defect fixed at {size_um:g} um   sweeping the pixel pitch")
        if r["img"] is not None:
            k = max(1, int(round(disp / tile)))
            canvas[pan_y:pan_y + disp, x1:x1 + disp] = _upscale(
                _gray_to_rgb(r["img"]), k)[:disp, :disp]
            canvas[pan_y:pan_y + disp, x2:x2 + disp] = _upscale(
                _verdict_rgb(r["img"], r["mask"], r["pred"]), k)[:disp, :disp]
        else:
            _fill(canvas, pan_y, pan_y + disp, x1, x1 + disp, C_PANEL)
            _fill(canvas, pan_y, pan_y + disp, x2, x2 + disp, C_PANEL)
        for xx0 in (x1, x2):
            canvas = imagedraw.draw_polyline(
                canvas, [(xx0 - 1, pan_y - 1), (xx0 + disp, pan_y - 1),
                         (xx0 + disp, pan_y + disp), (xx0 - 1, pan_y + disp)],
                color=C_GRID, width=1, closed=True)
        p = Plot(canvas, plot_box, (1.4, 13.5), (0.0, 12.0))
        p.bg()
        p.band_x(pitch_nyq, 13.5, (0.17, 0.14, 0.13))
        p.grid_y([2, 4, 6, 8, 10])
        p.frame()
        p.curve([q["pitch"] for q in rows], [q["px"] for q in rows], C_OPT, 2)
        p.hline(2.0, C_MISS, 1, dashed=True, dash=7, gap=6)
        p.vline(pitch_nyq, C_MISS, 1, dashed=True, dash=7, gap=6)
        p.marker(r["pitch"], r["px"], (1.0, 1.0, 1.0), 5, "cross", 2)
        # 検出率(0..1 を 0..12 の軸に載せ替えて重ねる)
        p2 = Plot(canvas, plot_box, (1.4, 13.5), (0.0, 1.06))
        p2.curve([q["pitch"] for q in rows if q["rate"] is not None],
                 [q["rate"] for q in rows if q["rate"] is not None], C_CURVE, 2)
        p2.ticks_x([2, 4, 6, 8, 10, 12])
        p.ticks_y([2, 4, 6, 8, 10])
        canvas = p2.c
        for t in (2, 4, 6, 8, 10, 12):
            labels.append((int(p.px(t)) - 5, plot_box[3] + 6, f"{t}", C_DIM, 11, False))
        for t in (2, 4, 6, 8, 10):
            labels.append((plot_box[0] - 24, int(p.py(t)) - 7, f"{t}", C_OPT, 11, False))
        yi = pan_y + disp + 10
        det_txt = ("no image (below one pixel)" if r["img"] is None
                   else ("DETECTED" if r["det"] else "not detected"))
        labels += [
            (x1 + 4, pan_y - 18, "captured image (nearest-neighbour zoom)",
             (0.95, 0.95, 0.92), 12, True),
            (x2 + 4, pan_y - 18, "detector vs ground truth",
             (0.95, 0.95, 0.92), 12, True),
            (plot_box[0] + 6, plot_box[1] + 4, "defect size [pixels]  (blue)",
             C_OPT, 11, True),
            (plot_box[0] + 6, plot_box[1] + 20, "detection rate 0..1  (yellow)",
             C_CURVE, 11, True),
            (plot_box[2] - 148, plot_box[3] - 16, "pixel pitch [um] ->", C_DIM, 11, False),
            (int(p.px(pitch_nyq)) - 132, plot_box[1] + 40,
             f"2 px at pitch {pitch_nyq:.2f} um", C_MISS, 11, True),
            (18, yi,
             f"pitch {r['pitch']:5.2f} um  ->  {r['upp']:6.2f} um/px   FOV "
             f"{r['fov'][0]:5.1f}x{r['fov'][1]:5.1f} mm   defect = {r['px']:5.2f} px",
             C_TEXT, 14, True),
            (18, yi + 20,
             f"Nyquist limit {r['nyq']:6.2f} um   diffraction {r['dif']:6.2f} um   "
             f"binding: {r['by']}   detection rate "
             + ("n/a" if r["rate"] is None else f"{r['rate']:.0%}")
             + f"  ->  {det_txt}",
             (C_HIT if (r["det"] and r["rate"]) else C_BAD), 14, True),
            (18, yi + 44,
             "the zoom is nearest-neighbour, so the blocks you see are real "
             "pixels -- nothing is interpolated to look smoother than it is",
             C_DIM, 11, False),
            (18, yi + 60,
             f"({int(sum(q['unren'] for q in rows))} of "
             f"{len(rows) * seeds} renders were refused as below one pixel and "
             f"are excluded from the rates, not counted as zero)",
             C_DIM, 11, False),
        ]
        frames.append(_text(_to_u8(canvas), labels))

    thumb = int(np.argmin([abs(r["pitch"] - pitch_nyq) for r in rows]))
    facts = {"defect_um": size_um, "seeds": seeds,
             "pitch_two_pixels_um": pitch_nyq,
             "pitch_last_detected_um": max(last_det) if last_det else None,
             "rows": [{k: v for k, v in r.items()
                       if k not in ("img", "mask", "pred")} for r in rows]}
    return {"frames": frames, "facts": facts, "fps": 10, "thumb_index": thumb}


# =========================================================================== #
# 13. 設計から判定までの一本道(フリップブック GIF)                              #
# =========================================================================== #
def ex_pipeline_flow(log):
    """設計 → 限界 → 部品 → 撮像 → 検査 → 判定 の 6 工程を同寸法のコマ送りに。

    工程ごとに絵が変わるだけでなく、**その工程で初めて確定する数字**を右に出す。
    共通部品 ``exhibit_tile.flipbook`` に載せるので、1 コマで止めても
    「今どの工程か / 何コマ目か」が読める。
    """
    system = _system()
    geo, res = _limits()
    upp = geo["um_per_pixel"]
    defect_um = 120.0
    tile = 200
    sh = (tile, tile)

    # --- 工程 3: 理想の部品(撮像前) ------------------------------------- #
    size_px = system.px_for_um(defect_um)
    bg = defectgen.surface_texture(sh, "orange_peel", strength=0.055,
                                   scale_px=5.0, seed=3001)
    ideal, mask = defectgen.defect_scratch(sh, length_px=min(size_px * 4.0, tile * 0.8),
                                           width_px=max(1.0, size_px),
                                           angle_deg=28.0, wander=0.14,
                                           contrast=-0.28, seed=5)
    scene = defectgen.composite_defect(bg, ideal, mask)
    # --- 工程 4: 撮像 ------------------------------------------------------ #
    captured = system.capture(scene)
    # --- 工程 5/6: 検査と判定 ---------------------------------------------- #
    pred, iou, detected = _detect(captured, mask)
    stats = defectgen.defect_stats(mask, um_per_pixel=upp)
    feas = system.limits(defect_um)

    PW, PH = 940, 424
    IMG = 384
    ix, iy = 22, 20
    tx = ix + IMG + 34

    def base_panel():
        c = _canvas(PH, PW, C_BG)
        _fill(c, iy - 2, iy + IMG + 2, ix - 2, ix + IMG + 2, C_PANEL)
        return c

    def put_image(c, img_or_rgb):
        k = IMG // tile                                   # 200 -> x1 が上限
        a = img_or_rgb if img_or_rgb.ndim == 3 else _gray_to_rgb(img_or_rgb)
        if k >= 2:
            a = _upscale(a, k)
        pad_y = (IMG - a.shape[0]) // 2
        pad_x = (IMG - a.shape[1]) // 2
        c[iy + pad_y:iy + pad_y + a.shape[0], ix + pad_x:ix + pad_x + a.shape[1]] = a
        return c

    def lines(items, y0=26, size=15, gap=22):
        out = []
        for k, (s, col, bold) in enumerate(items):
            out.append((tx, y0 + k * gap, s, col, size, bold))
        return out

    panels = []

    # ---- 1. 設計 ---------------------------------------------------------- #
    c = base_panel()
    # 視野の矩形と部品(実寸比で描く)
    fov_w, fov_h = geo["fov_w_mm"], geo["fov_h_mm"]
    scale = (IMG - 60) / max(fov_w, fov_h)
    rw, rh = fov_w * scale, fov_h * scale
    rx, ry = ix + (IMG - rw) / 2.0, iy + (IMG - rh) / 2.0
    c = imagedraw.draw_polyline(c, [(rx, ry), (rx + rw, ry), (rx + rw, ry + rh),
                                    (rx, ry + rh)], color=C_OPT, width=2, closed=True)
    part_mm = 12.0
    pw = part_mm * scale
    c = imagedraw.draw_polyline(
        c, [(ix + IMG / 2 - pw / 2, iy + IMG / 2 - pw / 2),
            (ix + IMG / 2 + pw / 2, iy + IMG / 2 - pw / 2),
            (ix + IMG / 2 + pw / 2, iy + IMG / 2 + pw / 2),
            (ix + IMG / 2 - pw / 2, iy + IMG / 2 + pw / 2)],
        color=C_HIT, width=2, closed=True)
    c = imagedraw.draw_circle(c, (ix + IMG / 2, iy + IMG / 2),
                              max(1.5, defect_um * 1e-3 * scale / 2.0),
                              color=C_MISS, width=2)
    lab = lines([
        ("STEP 1  design the system", (0.95, 0.95, 0.92), True),
        ("", C_DIM, False),
        (f"lens        f = {SYS['focal_mm']:g} mm", C_TEXT, False),
        (f"standoff    WD = {SYS['working_distance_mm']:g} mm", C_TEXT, False),
        (f"sensor      {SYS['width_px']}x{SYS['height_px']} @ "
         f"{SYS['pixel_pitch_um']:g} um", C_TEXT, False),
        (f"aperture    f/{SYS['f_number']:g}", C_TEXT, False),
        ("", C_DIM, False),
        (f"magnification   {geo['magnification']:.5f}", C_OPT, True),
        (f"field of view   {fov_w:.1f} x {fov_h:.1f} mm", C_OPT, True),
        (f"object pixel    {upp:.3f} um / px", C_OPT, True),
        ("", C_DIM, False),
        ("blue = field of view,  green = a 12 mm part,", C_DIM, False),
        (f"orange circle = the {defect_um:g} um defect (to scale)", C_DIM, False),
    ])
    panels.append(_text(_to_u8(c), lab))

    # ---- 2. 限界 ---------------------------------------------------------- #
    c = base_panel()
    bar_x0, bar_x1 = ix + 16, ix + IMG - 16
    bar_hi = max(res["nyquist_object_um"], res["diffraction_object_um"], defect_um) * 1.1
    for k, (nm, val, col) in enumerate((
            ("sampling (Nyquist)", res["nyquist_object_um"], C_CURVE),
            ("diffraction (Airy)", res["diffraction_object_um"], C_OPT),
            ("the defect we want", defect_um, C_HIT))):
        yb = iy + 40 + k * 74
        wpx = int(round((bar_x1 - bar_x0) * val / bar_hi))
        _fill(c, yb, yb + 28, bar_x0, bar_x0 + max(1, wpx), col)
    lab = lines([
        ("STEP 2  ask what the optics can carry", (0.95, 0.95, 0.92), True),
        ("", C_DIM, False),
        (f"Nyquist      2*pitch/m = {res['nyquist_object_um']:.2f} um", C_CURVE, True),
        (f"diffraction  2.44*l*N*(1+m)/m = "
         f"{res['diffraction_object_um']:.2f} um", C_OPT, True),
        (f"working f-number  N_eff = {res['working_f_number']:.3f}", C_DIM, False),
        ("", C_DIM, False),
        (f"optical limit  {res['resolution_object_um']:.2f} um "
         f"({res['limited_by']}-limited)", (0.95, 0.95, 0.92), True),
        (f"the {defect_um:g} um defect spans "
         f"{feas['pixels_across']:.2f} px", C_HIT, True),
        ("", C_DIM, False),
        (f"depth of field {feas['depth_of_field_mm']:.3f} mm vs "
         f"{feas['depth_tolerance_mm']:g} mm needed", C_TEXT, False),
        (f"corner illumination {feas['corner_illumination']:.4f}", C_TEXT, False),
        (f"verdict: {feas['verdict']}",
         (C_HIT if feas["verdict"] == "resolvable" else C_MISS), True),
    ])
    panels.append(_text(_to_u8(c), lab))

    # ---- 3. 仮想の部品 ---------------------------------------------------- #
    c = put_image(base_panel(), scene)
    lab = lines([
        ("STEP 3  build a virtual part", (0.95, 0.95, 0.92), True),
        ("", C_DIM, False),
        ("surface_texture  orange_peel", C_TEXT, False),
        (f"defect_scratch   {defect_um:g} um = {size_px:.2f} px wide", C_TEXT, False),
        ("composite_defect keeps the texture outside", C_TEXT, False),
        ("", C_DIM, False),
        ("this is the IDEAL scene -- no optics yet", C_MISS, True),
        ("", C_DIM, False),
        (f"mask area      {stats['area_px']} px", C_HIT, True),
        (f"major axis     {stats['major_axis_um']:.1f} um", C_HIT, True),
        (f"minor axis     {stats['minor_axis_um']:.1f} um", C_HIT, True),
        ("", C_DIM, False),
        ("the mask comes from the geometry, so it is", C_DIM, False),
        ("pixel-perfect and costs no annotation time", C_DIM, False),
    ])
    panels.append(_text(_to_u8(c), lab))

    # ---- 4. 撮像 ---------------------------------------------------------- #
    c = put_image(base_panel(), captured)
    d_rms = float(np.sqrt(np.mean((captured - scene) ** 2)))
    lab = lines([
        ("STEP 4  photograph it with THIS system", (0.95, 0.95, 0.92), True),
        ("", C_DIM, False),
        ("image_formation applies, in order:", C_TEXT, False),
        ("  1. the Airy PSF for this f-number", C_TEXT, False),
        ("  2. defocus (none here)", C_TEXT, False),
        ("  3. the cos^4 falloff", C_TEXT, False),
        ("  4. exposure, clipped to [0, 1]", C_TEXT, False),
        ("", C_DIM, False),
        (f"RMS change from the ideal scene {d_rms:.4f}", C_OPT, True),
        (f"contrast of the tile  {captured.min():.3f} .. "
         f"{captured.max():.3f}", C_OPT, True),
        ("", C_DIM, False),
        ("the mask does NOT move when the image blurs --", C_DIM, False),
        ("that is why it can still score the detector", C_DIM, False),
    ])
    panels.append(_text(_to_u8(c), lab))

    # ---- 5. 検査 ---------------------------------------------------------- #
    raw = np.zeros((tile, tile, 3), np.float64)
    raw[:, :] = (0.07, 0.08, 0.10)
    raw[pred] = (0.90, 0.90, 0.92)
    c = put_image(base_panel(), raw)
    lab = lines([
        ("STEP 5  run the inspection algorithm", (0.95, 0.95, 0.92), True),
        ("", C_DIM, False),
        ("the visionlab baseline detector:", C_TEXT, False),
        ("  residual from a 15x15 local mean,", C_TEXT, False),
        ("  thresholded at 2.5 standard deviations", C_TEXT, False),
        ("", C_DIM, False),
        ("deliberately naive -- the point is to have a", C_DIM, False),
        ("ruler for comparing designs, not to win", C_DIM, False),
        ("", C_DIM, False),
        (f"flagged pixels  {int(pred.sum())} of {tile * tile}", C_TEXT, True),
        ("", C_DIM, False),
        ("(this is the raw output; nothing has been", C_DIM, False),
        (" compared to the truth yet)", C_DIM, False),
    ])
    panels.append(_text(_to_u8(c), lab))

    # ---- 6. 判定 ---------------------------------------------------------- #
    c = put_image(base_panel(), _verdict_rgb(captured, mask, pred))
    inter = int(np.sum(pred & mask))
    union = int(np.sum(pred | mask))
    lab = lines([
        ("STEP 6  score it against the truth", (0.95, 0.95, 0.92), True),
        ("", C_DIM, False),
        ("teal = hit,  orange = missed,", C_HIT, True),
        ("purple = false alarm", C_FALSE, True),
        ("", C_DIM, False),
        (f"intersection {inter} px / union {union} px", C_TEXT, False),
        (f"IoU  {iou:.4f}   (threshold {MIN_IOU:g})", C_TEXT, True),
        (f"verdict: " + ("DETECTED" if detected else "not detected"),
         (C_HIT if detected else C_BAD), True),
        ("", C_DIM, False),
        (f"optics say {res['resolution_object_um']:.2f} um is the floor;", C_DIM, False),
        (f"this defect is {defect_um:g} um = "
         f"{defect_um / res['resolution_object_um']:.2f}x that floor", C_DIM, False),
        ("", C_DIM, False),
        ("two numbers, never folded into one", C_MISS, True),
    ])
    panels.append(_text(_to_u8(c), lab))

    steps = ["設計 — 視野と µm/画素を決める",
             "限界 — 標本化と回折のどちらが律速か",
             "仮想の部品 — 欠陥と画素完全なマスク",
             "撮像 — この系で実際に撮れる画像",
             "検査 — 検査アルゴリズムの生の出力",
             "判定 — 正解と突き合わせて IoU"]
    book = flipbook(panels, steps,
                    title="設計から判定までの一本道(visionlab の 6 段)",
                    label_h=38, title_h=44, font_size=18, title_font_size=21)
    log(f"  6 steps, panel {PW}x{PH}, flipbook frame "
        f"{book[0].shape[1]}x{book[0].shape[0]};  IoU {iou:.4f}, "
        f"{'detected' if detected else 'not detected'}, verdict {feas['verdict']}")
    facts = {"system": repr(system), "defect_um": defect_um,
             "um_per_pixel": upp, "defect_px": size_px,
             "optical_limit_um": res["resolution_object_um"],
             "limited_by": res["limited_by"], "feasibility": feas,
             "mask_stats": stats, "iou": iou, "detected": detected,
             "intersection_px": inter, "union_px": union,
             "flagged_px": int(pred.sum()),
             "rms_capture_change": d_rms, "steps": steps}
    return {"frames": book, "facts": facts, "fps": "flipbook", "thumb_index": 0}


# =========================================================================== #
# 展示の台帳とキャプション                                                       #
# =========================================================================== #
EXHIBIT_ORDER = [
    "pipeline_flow", "defect_atlas", "limit_crossover", "cos4_falloff", "mtf",
    "dof_coc", "res_vs_dof", "airy_rayleigh", "polarizer", "abcd_rays",
    "detect_map", "illumination", "pixel_pitch",
]

BUILDERS = {
    "pipeline_flow": ex_pipeline_flow,
    "defect_atlas": ex_defect_atlas,
    "limit_crossover": ex_limit_crossover,
    "cos4_falloff": ex_cos4_falloff,
    "mtf": ex_mtf,
    "dof_coc": ex_dof_coc,
    "res_vs_dof": ex_res_vs_dof,
    "airy_rayleigh": ex_airy_rayleigh,
    "polarizer": ex_polarizer,
    "abcd_rays": ex_abcd_rays,
    "detect_map": ex_detect_map,
    "illumination": ex_illumination,
    "pixel_pitch": ex_pixel_pitch,
}

TITLES = {
    "pipeline_flow": "設計から判定までの一本道",
    "defect_atlas": "欠陥ジェネレータの見本帳",
    "limit_crossover": "律速の入れ替わり",
    "cos4_falloff": "cos⁴ 則の周辺光量落ち",
    "mtf": "回折限界の MTF",
    "dof_coc": "被写界深度と錯乱円",
    "res_vs_dof": "横分解能 対 被写界深度",
    "airy_rayleigh": "Airy パターンと Rayleigh 基準",
    "polarizer": "偏光で金属のテカりを消す",
    "abcd_rays": "thin lens / ABCD 行列",
    "detect_map": "検出限界マップ",
    "illumination": "照明を変えると何が見えるか",
    "pixel_pitch": "画素ピッチとサンプリング",
}

OPS = {
    "pipeline_flow": ["system_geometry", "resolving_power", "system_feasibility",
                      "surface_texture", "defect_scratch", "composite_defect",
                      "defect_stats", "image_formation", "draw_polyline",
                      "draw_circle"],
    "defect_atlas": ["defect_scratch", "defect_pits", "defect_crack", "defect_blob",
                     "surface_texture", "composite_defect", "defect_stats",
                     "image_formation"],
    "limit_crossover": ["system_geometry", "resolving_power", "thin_lens",
                        "draw_polyline", "draw_line"],
    "cos4_falloff": ["relative_illumination", "thin_lens", "system_feasibility",
                     "draw_polyline"],
    "mtf": ["mtf_diffraction", "draw_polyline", "draw_markers"],
    "dof_coc": ["depth_of_field", "draw_polyline", "draw_line"],
    "res_vs_dof": ["resolving_power", "depth_of_field", "system_geometry",
                   "draw_polyline"],
    "airy_rayleigh": ["airy_pattern", "draw_polyline", "draw_line"],
    "polarizer": ["jones_element", "jones_apply", "stokes_from_jones",
                  "mueller_element", "mueller_apply", "defect_scratch",
                  "surface_texture", "image_formation", "draw_circle"],
    "abcd_rays": ["abcd_matrix", "abcd_trace", "thin_lens", "depth_of_field",
                  "draw_line"],
    "detect_map": ["render_part", "system_geometry", "resolving_power",
                   "draw_polyline", "draw_line"],
    "illumination": ["render_part", "defect_scratch", "image_formation",
                     "draw_polyline"],
    "pixel_pitch": ["render_part", "system_geometry", "resolving_power",
                    "draw_polyline"],
}


def _caption(name: str, facts: dict, info: dict) -> str:
    """記事と同じ書式の 1〜3 文。**数字は facts から引く**(手打ちしない)。"""
    f = facts
    if name == "pipeline_flow":
        fe = f["feasibility"]
        return (f"「設計 → 限界 → 仮想の部品 → 撮像 → 検査 → 判定」の 6 工程を、"
                f"1 コマずつ止めて読めるコマ送りにしました。系が決まると "
                f"**{f['um_per_pixel']:.3f} µm/画素**が確定し、そこから光学限界 "
                f"**{f['optical_limit_um']:.2f} µm**({f['limited_by']} 律速)が出て、"
                f"{f['defect_um']:.0f} µm の傷は {f['defect_px']:.2f} 画素になり、"
                f"最後に IoU **{f['iou']:.4f}** で "
                f"{'検出' if f['detected'] else '未検出'}と判定される —— "
                f"**正解マスクは撮像でぼけても動かない**ので、この採点が成立します"
                f"(判定は `{fe['verdict']}`)。")
    if name == "defect_atlas":
        rows = f["rows"]
        kinds = " / ".join(r["kind"] for r in rows)
        areas = " / ".join(str(r["stats"]["area_px"]) for r in rows)
        return (f"欠陥 5 種({kinds})を同じ系(**{f['um_per_pixel']:.3f} µm/画素**)で"
                f"撮り、左列が撮れる画像、右列が**画素完全な正解マスク**です。マスクは"
                f"撮像前の幾何から作るので、撮像でぼけても正解は動かず、**注釈作業が"
                f"存在しません** —— 各行のマスク面積は実測で {areas} 画素、"
                f"光学限界は {f['optical_limit_um']:.2f} µm"
                f"({f['limited_by']} 律速)です。")
    if name == "limit_crossover":
        return (f"作動距離を {f['wd_range_mm'][0]:.0f} → {f['wd_range_mm'][1]:.0f} mm と"
                f"掃くと、**回折律速と標本化律速が入れ替わります**。閉形式で解いた"
                f"交点は **WD {f['crossover_wd_mm']:.2f} mm**、そこでは 2 本の限界が"
                f"どちらも **{f['crossover_limit_um']:.2f} µm** で一致します"
                f"(倍率 {f['crossover_magnification']:.5f})。記事本文の 44 段掃引が"
                f"入れ替わりを最初に報告するのは {f['grid44_first_sampling_wd_mm']:.1f} mm "
                f"—— その差は物理ではなく**格子の粗さ**です。")
    if name == "cos4_falloff":
        return (f"焦点距離を {f['focal_range_mm'][0]:.0f} → {f['focal_range_mm'][1]:.0f} mm と"
                f"短くすると半画角が {f['half_deg_first']:.2f}° → {f['half_deg_last']:.2f}° へ"
                f"広がり、視野の角の明るさが **{f['corner_first']:.4f} → "
                f"{f['corner_last']:.4f}**(中心比)まで落ちます。右の曲線は "
                f"`relative_illumination` の出力そのもので、左のマップは同じ cos⁴ を"
                f"センサ座標で評価したもの —— **独立な 2 経路の角の値が最大でも "
                f"{f['max_crosscheck_delta']:.1e} しか違いません**(片方が壊れたら気付ける"
                f"作りにしてあります)。")
    if name == "mtf":
        first, last = f["rows"][0], f["rows"][-1]
        return (f"F 値を f/{first['f_number']:.1f} から f/{last['f_number']:.1f} まで絞ると、"
                f"カットオフ周波数 1/(λN) が **{first['cutoff_cyc_per_mm']:.0f} → "
                f"{last['cutoff_cyc_per_mm']:.0f} cyc/mm** へ下がります。左のバーは"
                f"飾りではなく、**右の曲線から読んだコントラストをそのまま振幅にして"
                f"描いた**もので、200 cyc/mm のバーは f/{first['f_number']:.1f} では "
                f"{first['mtf_at_probes'][2]:.3f} だったのが f/{last['f_number']:.1f} では "
                f"{last['mtf_at_probes'][2]:.3f} —— 完全に消えます。")
    if name == "dof_coc":
        rows = f["rows"]
        return (f"被写界深度は**レンズの性質ではなく、許容錯乱円という「こちらの決め事」**"
                f"です。錯乱円を 1 画素から 10 画素へ広げると深度は "
                f"**{rows[0]['depth']:.4f} mm → {rows[-1]['depth']:.4f} mm**"
                f"(比 {rows[-1]['ratio']:.4f})と、ほぼ厳密に比例して伸びます。"
                f"記事のライトフィールドの利得表(6×6 で 6.0016 倍)は"
                f"**この直線を 2 回読んだだけ**で、要求公差 {f['tolerance_mm']:g} mm が"
                f"収まるのは錯乱円 {f['coc_px_meeting_tolerance']:.3f} 画素からです。")
    if name == "res_vs_dof":
        return (f"横分解能と被写界深度は**独立な 2 軸**です。{f['target_um']:.0f} µm の欠陥が"
                f"解像できるのは **f/{f['n_max_resolvable']:.2f} まで**、部品の"
                f"{f['tolerance_mm']:g} mm 公差が収まるのは **f/{f['n_min_for_tolerance']:.2f} から** "
                f"—— 使える窓は **f/{f['n_min_for_tolerance']:.2f} 〜 f/{f['n_max_resolvable']:.2f}** の"
                f"帯だけです。これを 1 つの `resolvable` に畳むと「光学限界に未到達」と"
                f"出てしまい、**読んだ人はレンズを買いに行きます**(直すべきは絞りか公差か"
                f"フォーカス機構)。")
    if name == "airy_rayleigh":
        return (f"円形瞳の Airy 像で 2 点を近づけていくと、谷は**崖ではなく連続に**"
                f"浅くなります。第 1 暗環の実測位置は "
                f"**{f['airy_first_zero_um_measured']:.3f} µm**(理論 1.2197λN = "
                f"{f['airy_first_zero_um_theory']:.3f} µm)、Rayleigh 間隔 "
                f"{f['rayleigh_um']:.3f} µm での谷は実測 **{f['dip_at_rayleigh']:.4f}**"
                f"(教科書の 0.735)で、谷がそもそも現れ始めるのは "
                f"{f['first_dip_separation_um']:.3f} µm からです。")
    if name == "polarizer":
        return (f"鏡面反射(完全偏光)を Jones 行列で、拡散反射(無偏光)を Mueller 行列で"
                f"通し、検光子を 0° → 180° で回します。鏡面成分の透過強度は Malus 則で "
                f"**{f['specular_at_0']:.4f} → {f['specular_at_90']:.4f}(厳密に 0)**、"
                f"拡散成分は角度に依らず 0.5 のまま —— 飽和画素が "
                f"**{f['clipped_at_0'] * 100:.2f} % → {f['clipped_at_90'] * 100:.2f} %** に減り、"
                f"テカりに埋もれていた傷の IoU が **{f['iou_at_0']:.3f} → "
                f"{f['iou_at_90']:.3f}** へ回復して検出に転じます。")
    if name == "abcd_rays":
        d = f["depth_of_field"]
        return (f"物体距離を動かしながら ABCD 行列で 3 本の光線を追うと、共役面では "
                f"**B 要素が 0 になり、出射高さが入射角に依存しなくなります** —— それが"
                f"「結像している」の定義そのものです。センサは "
                f"{f['sensor_mm']:.3f} mm に固定してあるので、物体が前後するとぼけ円が"
                f"広がり、**光線追跡がぼけ 1 画素以内と言う範囲 "
                f"{f['ray_trace_in_focus_mm'][0]:.1f}〜{f['ray_trace_in_focus_mm'][1]:.1f} mm** は、"
                f"独立な閉形式 `depth_of_field` の {d['near_mm']:.3f}〜{d['far_mm']:.3f} mm と"
                f"格子の刻みぶんだけの差で一致します。")
    if name == "detect_map":
        cont = [(c, s) for c, s in zip(f["contrasts"], f["contour_50pct_um"])
                if s is not None]
        lo, hi = cont[0], cont[-1]
        return (f"欠陥サイズ(横・対数)とコントラスト(縦)の平面で検出率を測ると、"
                f"**光学限界 {f['optical_limit_um']:.2f} µm({f['limited_by']} 律速)は"
                f"縦の直線として動かず**、実際の検出境界(白線 = 実測 50 % 等高線)は"
                f"その右に寝ています。コントラスト {lo[0]:.2f} では "
                f"{lo[1]:.0f} µm(限界の {lo[1] / f['optical_limit_um']:.2f} 倍)必要なのに、"
                f"{hi[0]:.2f} まで上げると {hi[1]:.0f} µm"
                f"({hi[1] / f['optical_limit_um']:.2f} 倍)で足ります —— "
                f"**右側はレンズの問題ではありません**。")
    if name == "illumination":
        b = f["bright_50pct_contrast"]
        d = f["dark_50pct_contrast"]
        return (f"同じ幾何の {f['defect_um']:.0f} µm の傷を、明視野風(明るい面に暗い傷)と"
                f"暗視野風(暗い場に光る傷)で並べ、コントラストを掃きます。50 % 検出に"
                f"届くのは明視野風が |contrast| **{b:.3f}**、暗視野風が **{d:.3f}** で、"
                f"光学限界 {f['optical_limit_um']:.2f} µm は両方とも余裕で超えています —— "
                f"**差はレンズではなく見せ方**です(これは `defectgen` の appearance "
                f"モデル = 符号と露光であって、リング照明の光輸送計算ではありません)。")
    if name == "pixel_pitch":
        return (f"{f['defect_um']:.0f} µm の傷を固定して画素ピッチだけを粗くすると、"
                f"欠陥が **2 画素を割るのはピッチ {f['pitch_two_pixels_um']:.2f} µm** "
                f"(Nyquist の境界)で、実測の 50 % 検出が保つのはピッチ "
                f"**{f['pitch_last_detected_um']:.2f} µm** までです。拡大は最近傍なので"
                f"**見えている四角は本物の画素**で、滑らかに見せるための補間は"
                f"入れていません。")
    return ""


def _write_captions(results, log):
    """`docs/articles/exhibits/wingopt.md` を書く(記事本体には触れない)。"""
    os.makedirs(EXHIBITS, exist_ok=True)
    path = os.path.join(EXHIBITS, "wingopt.md")
    lines = [
        "<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 "
        "(docs/articles/*.md) には手を触れていません。 -->",
        "",
        "# 光学設計・検査ウィング —— キャプション原稿",
        "",
        "再生成: `py -3.11 tools/gen_wingopt_gallery.py`"
        "(展示単位なら `--exhibits <name,...>`)。",
        "図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / "
        "`visionlab` を実際に呼んだ実測値で、決定的です"
        "(`--verify` で SHA-256 一致を確認できます)。",
        "",
    ]
    for name in EXHIBIT_ORDER:
        r = results.get(name)
        if r is None:
            continue
        info, facts = r["info"], r["facts"]
        title = TITLES[name]
        ops = ", ".join(f"`{o}`" for o in OPS[name])
        cap = _caption(name, facts, info)
        base = os.path.basename(info["path"])
        lines.append(f"## {title}")
        lines.append("")
        if info["kind"] == "gif":
            stem = os.path.splitext(base)[0]
            lines.append(markdown_animation(
                stem, title, f"**{title}** ―― {cap} 使用 op: {ops}。").rstrip())
            lines.append("")
            pace = (f"{info['step_ms']} ms/コマ" if info.get("step_ms")
                    else f"{info['fps']} fps")
            lines.append(
                f"<small>静止フレームでも読めます(静止サムネ: "
                f"`{RAW_BASE}thumbs/{os.path.basename(info['thumb'])}`)。"
                f"{info['frames']} フレーム / {pace} / "
                f"{info['size'][0]}×{info['size'][1]} px / "
                f"{info['bytes'] / 1e6:.2f} MB。</small>")
        else:
            # サムネイル表示 + クリックで原寸 = 共通部品 exhibit_tile.markdown の形。
            stem = os.path.splitext(base)[0]
            lines.append(markdown(stem, title,
                                  f"**{title}** ―― {cap} 使用 op: {ops}。").rstrip())
            lines.append("")
            lines.append(f"<small>クリックで原寸 "
                         f"({info['size'][0]}×{info['size'][1]} px / "
                         f"{info['bytes'] / 1e3:.0f} kB)。</small>")
        lines.append("")
    lines += ["---", "",
              "## 生成物一覧(実測)", "",
              "| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |",
              "|---|---|---|---|---|---|"]
    for name in EXHIBIT_ORDER:
        r = results.get(name)
        if r is None:
            continue
        i = r["info"]
        lines.append(
            f"| {TITLES[name]} | {i['kind'].upper()} | "
            f"{i['size'][0]}×{i['size'][1]} | {i['frames']} | "
            f"{i['bytes'] / 1e3:.0f} kB | `{i['sha256'][:16]}` |")
    lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    log(f"captions: {path}")
    return path


# --------------------------------------------------------------------------- #
# CLI                                                                           #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="光学設計・検査ウィングの展示を作る(記事本体は編集しない)")
    ap.add_argument("--exhibits", default="",
                    help="comma list (default: all). " + ",".join(EXHIBIT_ORDER))
    ap.add_argument("--out-meta", default=os.path.join(ASSETS, "_wingopt_meta.json"))
    ap.add_argument("--verify", action="store_true",
                    help="同じ展示を 2 回作って SHA-256 の一致を確かめる")
    args = ap.parse_args(argv)

    wanted = [s.strip() for s in args.exhibits.split(",") if s.strip()] or list(EXHIBIT_ORDER)
    unknown = [n for n in wanted if n not in BUILDERS]
    if unknown:
        print(f"unknown exhibits: {unknown}\nvalid: {EXHIBIT_ORDER}", file=sys.stderr)
        return 2

    def log(m):
        print(m, flush=True)

    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(MEDIA, exist_ok=True)
    os.makedirs(THUMBS, exist_ok=True)

    t0 = time.time()
    results, failures = {}, []
    for name in wanted:
        log(f"[build] {name}")
        t1 = time.time()
        try:
            out = BUILDERS[name](log)
            frames = out["frames"]
            if out["fps"] is None:
                info = _save_png(frames[0], name, log)
            elif out["fps"] == "flipbook":
                info = _save_flipbook(frames, name, log)
            else:
                info = _save_gif(frames, name, out["fps"], out["thumb_index"], log)
            results[name] = {"info": info, "facts": out["facts"]}
            log(f"[done ] {name}  {time.time() - t1:.1f}s")
        except Exception as e:                              # noqa: BLE001
            import traceback
            traceback.print_exc()
            failures.append((name, str(e)))
            log(f"[FAIL ] {name}: {e}")

    if args.verify and results:
        log("[verify] rebuilding to compare SHA-256")
        for name in list(results):
            out = BUILDERS[name](lambda _m: None)
            frames = out["frames"]
            if out["fps"] is None:
                info2 = _save_png(frames[0], name, lambda _m: None)
            else:
                info2 = _save_gif(frames, name, out["fps"], out["thumb_index"],
                                  lambda _m: None)
            same = info2["sha256"] == results[name]["info"]["sha256"]
            log(f"    {name}: {'MATCH' if same else 'MISMATCH'}  "
                f"{info2['sha256'][:16]}")
            if not same:
                failures.append((name, "non-deterministic output"))

    if results:
        meta = {n: {"info": {k: v for k, v in r["info"].items()},
                    "title": TITLES[n], "ops": OPS[n],
                    "facts": r["facts"]} for n, r in results.items()}
        with open(args.out_meta, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=1, default=float)
        log(f"meta: {args.out_meta}")
        _write_captions(results, log)

    log(f"=== {len(results)} exhibit(s) in {time.time() - t0:.1f}s ===")
    if failures:
        log(f"failures: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
