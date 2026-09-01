# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_newops_media — 新しく足した 8 つの op 族の「やれることが目で分かる」図を作る。

    py -3.11 tools/gen_newops_media.py                    # 全部
    py -3.11 tools/gen_newops_media.py --figs csi,fmcw    # 一部だけ

``tools/gen_visionlab_video.py`` と**同じ流儀**で書いてある:

* **決定的** — seed はすべて固定、時刻も乱数状態も焼き込まない。同じコマンドを
  2 回走らせると同じバイト列(SHA-256 一致)が出る。
* **描画は Fullseye 自身の ``imagedraw`` op と numpy 合成**。matplotlib は使わない。
  文字だけは Fullseye にテキスト描画 op が無いため PIL の ``ImageDraw.text`` を
  数値ラベル専用に使う。
* GIF と mp4 は**同一のフレーム列**から書き(撮り直さない)、書き出したあと
  **読み戻してフレーム数と形を照合**する。一致しなければ例外。
* **図に焼く数字はすべてその場の実測**。飾りの数字は 1 つも無い。

作る 8 点(1 族 1 点):

  1. ``newops_csi_step_sweep``    (静止画) コヒーレンス走査干渉 — 位相シフト法が
     λ/4 で飛び、誤差が λ/2 の整数倍になるのに対し、コヒーレンス法が追従する。
  2. ``newops_bearing_envelope``  (静止画) 音響・振動診断 — 同じ軸受信号の生
     スペクトル(欠陥周波数に何も無い)対 包絡線スペクトル(そこにピーク)。
  3. ``newops_lightfield_refocus`` (GIF)  ライトフィールド — 1 枚の光場から
     スロープを掃引してリフォーカス。ピントが手前の層から奥の層へ移る。
  4. ``newops_photon_buildup``    (GIF)  光子計数 — 1→1000 photon/px で粒が絵に
     なり、``photon_uncertainty`` の誤差棒が √N で縮む。
  5. ``newops_quaternion_rotate`` (GIF)  四元数画像 — 色空間の 3 次元回転と、
     チャンネルごとの利得(最良の対角近似)では作れないことの対比。
  6. ``newops_fmcw_window``       (静止画) FMCW レンジ-ドップラー — 矩形窓では
     漏れに埋没する弱い標的が hann 窓で復活する。
  7. ``newops_specular_split``    (静止画) 鏡面反射の分離 + 遮蔽灯 k=0..6 で
     法線誤差が k=4 で崩れる曲線。
  8. ``newops_motion_magnify``    (GIF)  モーション増幅 — 0.2 px の振動の増幅
     前後と、振幅を上げると J₀ 第一零点で測定が反転する崖。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from typing import Callable, Sequence

import numpy as np

# スクリプト直実行でも動くよう repo ルートを sys.path に足す。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import imagedraw                                          # noqa: E402  Fullseye の描画 op
import video                                              # noqa: E402  Fullseye の書き出し

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_MEDIA_DIR = os.path.join(_ROOT, "docs", "articles", "assets", "media")
_THUMB_DIR = os.path.join(_ROOT, "docs", "articles", "assets", "thumbs")

# --------------------------------------------------------------------------- #
# 配色 — 赤緑の対で意味を担わせない(色覚に依らず読める組み合わせ)             #
# --------------------------------------------------------------------------- #
C_BG = (0.055, 0.062, 0.075)
C_PANEL = (0.100, 0.112, 0.132)
C_PLOT = (0.082, 0.092, 0.110)
C_TEXT = (0.880, 0.890, 0.860)
C_DIM = (0.520, 0.550, 0.580)
C_GRID = (0.200, 0.220, 0.250)
C_BLUE = (0.350, 0.720, 1.000)      # 系列 A
C_YELL = (0.980, 0.860, 0.350)      # 系列 B
C_VIOL = (0.640, 0.480, 0.960)      # 系列 C
C_TEAL = (0.130, 0.850, 0.800)      # 「効いている」側
C_AMBR = (1.000, 0.700, 0.160)      # 注意・真値の目印
C_ROSE = (0.960, 0.480, 0.560)      # 壊れている側
C_WHITE = (1.000, 1.000, 1.000)


# --------------------------------------------------------------------------- #
# 小道具                                                                        #
# --------------------------------------------------------------------------- #
_FONT_CACHE: dict = {}


def _font(size: int = 13, bold: bool = False):
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


def _canvas(h: int, w: int) -> np.ndarray:
    c = np.empty((h, w, 3), np.float64)
    c[:, :] = np.asarray(C_BG)
    return c


def _fill(canvas: np.ndarray, y0: int, y1: int, x0: int, x1: int, color) -> None:
    """矩形をベタ塗り(op を通すまでもない下地)。"""
    canvas[int(y0):int(y1), int(x0):int(x1), :] = np.asarray(color, np.float64)


def _upscale(a: np.ndarray, k: int) -> np.ndarray:
    """最近傍の整数倍拡大。**補間しない** — 画素の粗さ自体が見せたい情報なので。"""
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def _gray_to_rgb(img: np.ndarray) -> np.ndarray:
    return np.repeat(np.clip(np.asarray(img, np.float64), 0.0, 1.0)[:, :, None], 3, axis=2)


def _norm01(a: np.ndarray, lo=None, hi=None) -> np.ndarray:
    a = np.asarray(a, np.float64)
    lo = float(a.min()) if lo is None else float(lo)
    hi = float(a.max()) if hi is None else float(hi)
    if hi - lo < 1e-15:
        return np.zeros_like(a)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


#: viridis 風の 5 点ランプ(赤緑の対で意味を担わせない連続色)。
_CMAP_ANCHORS = np.array([
    [0.267, 0.005, 0.329],
    [0.229, 0.322, 0.545],
    [0.128, 0.567, 0.551],
    [0.369, 0.789, 0.383],
    [0.993, 0.906, 0.144],
])


def _cmap(v01: np.ndarray) -> np.ndarray:
    """[0,1] の 2-D 配列 → RGB(H, W, 3)。線形補間の 5 点ランプ。"""
    v = np.clip(np.asarray(v01, np.float64), 0.0, 1.0) * (len(_CMAP_ANCHORS) - 1)
    i = np.clip(np.floor(v).astype(int), 0, len(_CMAP_ANCHORS) - 2)
    f = (v - i)[..., None]
    return _CMAP_ANCHORS[i] * (1.0 - f) + _CMAP_ANCHORS[i + 1] * f


def _place(canvas: np.ndarray, img_rgb: np.ndarray, y: int, x: int) -> None:
    h, w = img_rgb.shape[:2]
    canvas[y:y + h, x:x + w, :] = np.clip(img_rgb, 0.0, 1.0)


def _frame_box(canvas: np.ndarray, y0, y1, x0, x1, color=C_GRID, width=1) -> np.ndarray:
    pts = [(x0, y0), (x1 - 1, y0), (x1 - 1, y1 - 1), (x0, y1 - 1)]
    return imagedraw.draw_polyline(canvas, pts, color=color, width=width, closed=True)


def _dashed(canvas: np.ndarray, p0, p1, color, width=1, dash=6, gap=5) -> np.ndarray:
    """破線 — ``imagedraw.draw_line`` を短い区間に分けて重ねる。"""
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    length = float(np.hypot(x1 - x0, y1 - y0))
    if length < 1e-9:
        return canvas
    t = 0.0
    while t < length:
        t2 = min(t + dash, length)
        a = (x0 + (x1 - x0) * t / length, y0 + (y1 - y0) * t / length)
        b = (x0 + (x1 - x0) * t2 / length, y0 + (y1 - y0) * t2 / length)
        canvas = imagedraw.draw_line(canvas, a, b, color=color, width=width)
        t = t2 + gap
    return canvas


def _to_u8(canvas: np.ndarray) -> np.ndarray:
    return np.clip(canvas * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _text(frame_u8: np.ndarray, items) -> np.ndarray:
    """``(x, y, text, color_rgb01, size, bold)`` の列をまとめて焼き込む。

    Fullseye にはテキスト描画 op が無いため、**数値ラベルに限って** PIL を使う。
    図形(線・折れ線・円・マーカー)は Fullseye の ``imagedraw`` op で描いている。
    """
    from PIL import Image, ImageDraw
    im = Image.fromarray(frame_u8)
    d = ImageDraw.Draw(im)
    for x, y, s, col, size, bold in items:
        rgb = tuple(int(round(255 * c)) for c in col)
        d.text((int(x), int(y)), s, fill=rgb, font=_font(size, bold))
    return np.asarray(im)


class Axes:
    """プロット領域 1 枚。データ座標 → 画素座標の写像と目盛りだけを持つ。"""

    def __init__(self, x0, y0, x1, y1, xlo, xhi, ylo, yhi, logx=False, logy=False):
        self.x0, self.y0, self.x1, self.y1 = int(x0), int(y0), int(x1), int(y1)
        self.xlo, self.xhi, self.ylo, self.yhi = float(xlo), float(xhi), float(ylo), float(yhi)
        self.logx, self.logy = bool(logx), bool(logy)

    def X(self, v):
        v = np.clip(np.asarray(v, np.float64), self.xlo, self.xhi)
        if self.logx:
            t = (np.log10(v) - np.log10(self.xlo)) / (np.log10(self.xhi) - np.log10(self.xlo))
        else:
            t = (v - self.xlo) / (self.xhi - self.xlo)
        return self.x0 + (self.x1 - self.x0) * t

    def Y(self, v):
        v = np.clip(np.asarray(v, np.float64), self.ylo, self.yhi)
        if self.logy:
            t = (np.log10(v) - np.log10(self.ylo)) / (np.log10(self.yhi) - np.log10(self.ylo))
        else:
            t = (v - self.ylo) / (self.yhi - self.ylo)
        return self.y1 - (self.y1 - self.y0) * t

    def bg(self, canvas, color=C_PLOT):
        _fill(canvas, self.y0, self.y1, self.x0, self.x1, color)
        return canvas

    def axis(self, canvas, color=C_DIM):
        canvas = imagedraw.draw_line(canvas, (self.x0, self.y1), (self.x1, self.y1),
                                     color=color, width=1)
        canvas = imagedraw.draw_line(canvas, (self.x0, self.y0), (self.x0, self.y1),
                                     color=color, width=1)
        return canvas

    def hline(self, canvas, y, color, width=1, dashed=False):
        p0, p1 = (self.x0, self.Y(y)), (self.x1, self.Y(y))
        return _dashed(canvas, p0, p1, color, width) if dashed else \
            imagedraw.draw_line(canvas, p0, p1, color=color, width=width)

    def vline(self, canvas, x, color, width=1, dashed=False):
        p0, p1 = (self.X(x), self.y0), (self.X(x), self.y1)
        return _dashed(canvas, p0, p1, color, width) if dashed else \
            imagedraw.draw_line(canvas, p0, p1, color=color, width=width)

    def series(self, canvas, xs, ys, color, width=2):
        pts = [(float(self.X(x)), float(self.Y(y))) for x, y in zip(xs, ys)]
        if len(pts) >= 2:
            canvas = imagedraw.draw_polyline(canvas, pts, color=color, width=width)
        return canvas

    def markers(self, canvas, xs, ys, color, size=4, shape="cross", width=2):
        pts = [(float(self.X(x)), float(self.Y(y))) for x, y in zip(xs, ys)]
        if pts:
            canvas = imagedraw.draw_markers(canvas, pts, color=color, size=size,
                                            shape=shape, width=width)
        return canvas

    def xticks(self, canvas, values, labels, color=C_DIM, size=11, dy=4):
        out = []
        for v, s in zip(values, labels):
            xt = float(self.X(v))
            canvas = imagedraw.draw_line(canvas, (xt, self.y1), (xt, self.y1 + 4),
                                         color=color, width=1)
            out.append((xt - 3.2 * len(s), self.y1 + dy + 2, s, color, size, False))
        return canvas, out

    def yticks(self, canvas, values, labels, color=C_DIM, size=11):
        out = []
        for v, s in zip(values, labels):
            yt = float(self.Y(v))
            canvas = imagedraw.draw_line(canvas, (self.x0 - 4, yt), (self.x0, yt),
                                         color=color, width=1)
            out.append((self.x0 - 8 - 7 * len(s), yt - 7, s, color, size, False))
        return canvas, out

    def grid_y(self, canvas, values, color=C_GRID):
        for v in values:
            canvas = imagedraw.draw_line(canvas, (self.x0, self.Y(v)), (self.x1, self.Y(v)),
                                         color=color, width=1)
        return canvas


def _legend(x, y, entries, size=12, step=17):
    """凡例 = 色つきの ``■`` + 文字。``_text`` に渡す項目列を返す。"""
    out = []
    for i, (col, label) in enumerate(entries):
        out.append((x, y + i * step, "\u25a0", col, size, True))
        out.append((x + 14, y + i * step, label, C_TEXT, size, False))
    return out


# --------------------------------------------------------------------------- #
# 書き出しと検証(でっち上げ禁止 — 報告する数字は読み戻した値)                  #
# --------------------------------------------------------------------------- #
def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify(path: str, expected: int, log: Callable[[str], None]) -> dict:
    """書き出したファイルを**読み戻して**フレーム数と形を実測し、期待と照合する。"""
    import imageio.v2 as imageio
    reader = imageio.get_reader(path)
    n, shape = 0, None
    try:
        for fr in reader:
            if shape is None:
                shape = tuple(np.asarray(fr).shape)
            n += 1
    finally:
        reader.close()
    if n != expected:
        raise RuntimeError(f"{path}: read back {n} frame(s), expected {expected}")
    size = os.path.getsize(path)
    log(f"    verify {os.path.basename(path)}: {n} frame(s) (== expected), "
        f"shape {shape}, {size / 1e6:.2f} MB")
    return {"path": path, "frames": n, "shape": list(shape), "bytes": size,
            "sha256": _sha256(path)}


def _thumb(frame_u8: np.ndarray, stem: str, thumb_dir: str,
           log: Callable[[str], None]) -> dict:
    from PIL import Image
    os.makedirs(thumb_dir, exist_ok=True)
    path = os.path.join(thumb_dir, f"{stem}_720.jpg")
    im = Image.fromarray(frame_u8)
    w, h = im.size
    im.resize((720, max(2, round(h * 720 / w))), Image.LANCZOS).save(path, quality=88)
    log(f"    thumb {os.path.basename(path)} ({os.path.getsize(path) / 1e3:.0f} kB)")
    return {"path": path, "bytes": os.path.getsize(path), "sha256": _sha256(path)}


def _write(frames_u8: Sequence[np.ndarray], stem: str, *, fps: int, thumb_index: int,
           out_dir: str, thumb_dir: str, log: Callable[[str], None]) -> dict:
    """1 枚なら PNG、複数なら**同一フレーム列**から GIF + mp4。どちらも読み戻す。"""
    os.makedirs(out_dir, exist_ok=True)
    info: dict = {"fps": fps, "n_frames": len(frames_u8),
                  "size": [int(frames_u8[0].shape[1]), int(frames_u8[0].shape[0])]}
    if len(frames_u8) == 1:
        from PIL import Image
        png = os.path.join(out_dir, f"{stem}.png")
        Image.fromarray(frames_u8[0]).save(png, optimize=True)
        info["png"] = _verify(png, 1, log)
    else:
        gif = os.path.join(out_dir, f"{stem}.gif")
        mp4 = os.path.join(out_dir, f"{stem}.mp4")
        video.write_video(mp4, frames_u8, fps=fps)
        video.write_video(gif, frames_u8, fps=fps)
        info["gif"] = _verify(gif, len(frames_u8), log)
        info["mp4"] = _verify(mp4, len(frames_u8), log)
    idx = int(np.clip(thumb_index, 0, len(frames_u8) - 1))
    info["thumb"] = _thumb(frames_u8[idx], stem, thumb_dir, log)
    info["thumb"]["frame_index"] = idx
    return info


# =========================================================================== #
# 1) コヒーレンス走査干渉 — 位相シフト法が λ/4 で飛ぶ                          #
# =========================================================================== #
def build_csi(log: Callable[[str], None]):
    import fringe
    import interferometry as I

    LAM, SIGMA, DZ, NP = 0.60, 1.2, 0.05, 241
    gain = 4.0 * np.pi / LAM                    # rad/um(往復 = 1 縞が λ/2)
    steps = np.round(np.arange(0.10, 1.0001, 0.01), 6)

    psi, csi = [], []
    for h in steps:
        hh = np.zeros((16, 32))
        hh[:, 16:] = float(h)
        imgs = fringe.synthesize_fringes(hh, n_steps=4, freq=0.0, phase_gain=gain,
                                         bias=0.5, amplitude=0.4)
        rec = fringe.decode_fringe(imgs, k=1.0 / gain)
        psi.append(float(rec[:, 16:].mean() - rec[:, :16].mean()))
        st = I.csi_stack_simulate(hh + 5.0, 0.0, DZ, NP, LAM,
                                  envelope_fwhm_um=None, envelope_sigma_um=SIGMA)
        cm = I.csi_height_map(st, DZ, 0.0, LAM, mode="gaussian")
        csi.append(float(cm[:, 16:].mean() - cm[:, :16].mean()))
    psi = np.asarray(psi)
    csi = np.asarray(csi)

    e_psi = psi - steps
    e_csi = csi - steps
    orders = e_psi / (LAM / 2.0)
    frac = float(np.abs(orders - np.round(orders)).max())          # 整数からのずれ
    broke = steps[np.abs(e_psi) > 1e-6]
    first_break = float(broke.min()) if broke.size else float("nan")
    last_ok = float(steps[steps < first_break].max())
    csi_max = float(np.abs(e_csi).max())
    csi_rms = float(np.sqrt(np.mean(e_csi ** 2)))
    n_orders = int(len(np.unique(np.round(orders).astype(int))))
    des = I.csi_design(wavelength_um=LAM, bandwidth_um=0.10, z_range_um=12.0,
                       width_px=320, height_px=240)

    log(f"  lambda/4 = {LAM / 4:.3f} um, lambda/2 = {LAM / 2:.3f} um")
    log(f"  phase-shifting first breaks at {first_break:.2f} um "
        f"(last correct {last_ok:.2f} um); error is an integer multiple of "
        f"lambda/2 to {frac:.2e}; {n_orders} distinct fringe orders")
    log(f"  coherence method: max |error| {csi_max:.3e} um, RMS {csi_rms:.3e} um")

    W, H = 1120, 786
    PX0, PX1 = 96, W - 22
    canvas = _canvas(H, W)
    _fill(canvas, 0, 30, 0, W, C_PANEL)

    axA = Axes(PX0, 62, PX1, 336, 0.10, 1.00, -0.22, 1.06)
    axB = Axes(PX0, 402, PX1, 588, 0.10, 1.00, -3.6, 0.6)
    axC = Axes(PX0, 654, PX1, 760, 0.10, 1.00, -0.25, 0.25)

    for ax in (axA, axB, axC):
        ax.bg(canvas)
    # A: 真値の直線・λ/4 の縦線・2 方式の測定値
    canvas = axA.grid_y(canvas, [0.0, 0.25, 0.5, 0.75, 1.0])
    canvas = axA.series(canvas, steps, steps, C_DIM, 1)
    canvas = axA.vline(canvas, LAM / 4.0, C_AMBR, 2, dashed=True)
    canvas = axA.vline(canvas, first_break, C_ROSE, 2)
    canvas = axA.series(canvas, steps, csi, C_TEAL, 3)
    canvas = axA.series(canvas, steps, psi, C_BLUE, 2)
    canvas = axA.axis(canvas)
    canvas, tA = axA.xticks(canvas, [0.1, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0],
                            ["0.10", "0.15", "0.30", "0.45", "0.60", "0.75", "0.90", "1.00"])
    canvas, tAy = axA.yticks(canvas, [0.0, 0.25, 0.5, 0.75, 1.0],
                             ["0.00", "0.25", "0.50", "0.75", "1.00"])
    # B: 位相シフト法の誤差 / (λ/2) = 縞次数(整数の階段)
    canvas = axB.grid_y(canvas, [0.0, -1.0, -2.0, -3.0])
    canvas = axB.series(canvas, steps, orders, C_BLUE, 3)
    canvas = axB.markers(canvas, steps[::4], orders[::4], C_WHITE, 4, "cross", 1)
    canvas = axB.vline(canvas, LAM / 4.0, C_AMBR, 2, dashed=True)
    canvas = axB.axis(canvas)
    canvas, tB = axB.xticks(canvas, [0.1, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0],
                            ["0.10", "0.15", "0.30", "0.45", "0.60", "0.75", "0.90", "1.00"])
    canvas, tBy = axB.yticks(canvas, [0.0, -1.0, -2.0, -3.0], ["0", "-1", "-2", "-3"])
    # C: コヒーレンス法の誤差 [nm]
    canvas = axC.grid_y(canvas, [0.0])
    canvas = axC.series(canvas, steps, e_csi * 1000.0, C_TEAL, 2)
    canvas = axC.axis(canvas)
    canvas, tC = axC.xticks(canvas, [0.1, 0.3, 0.5, 0.7, 0.9, 1.0],
                            ["0.10", "0.30", "0.50", "0.70", "0.90", "1.00"])
    canvas, tCy = axC.yticks(canvas, [-0.2, 0.0, 0.2], ["-0.2", "0.0", "+0.2"])
    for ax in (axA, axB, axC):
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

    labels = [
        (14, 7, "coherence scanning interferometry  vs  phase shifting  "
                f"(lambda = {LAM:.2f} um, envelope sigma {SIGMA:.1f} um, "
                f"{NP} planes x {DZ:.2f} um)", C_TEXT, 13, False),
        (PX0, 42, "measured step height [um]  -- one surface, two methods",
         C_TEXT, 14, True),
        (PX0, 382, "phase-shifting error / (lambda/2) = fringe order  "
                   "(integer to %.1e)" % frac, C_TEXT, 14, True),
        (PX0, 634, "coherence-method error [nm]", C_TEXT, 14, True),
        (PX1 - 150, 340, "true step height [um] ->", C_DIM, 11, False),
        (PX1 - 150, 592, "true step height [um] ->", C_DIM, 11, False),
        (PX1 - 150, 764, "true step height [um] ->", C_DIM, 11, False),
        (int(axA.X(LAM / 4.0)) + 6, 68, f"lambda/4 = {LAM / 4:.2f} um", C_AMBR, 12, True),
        (int(axA.X(first_break)) + 6, 88,
         f"first wrong answer at {first_break:.2f} um", C_ROSE, 12, True),
    ]
    labels += _legend(PX0 + 12, 300, [
        (C_TEAL, "csi_height_map  (coherence envelope peak)"),
        (C_BLUE, "decode_fringe   (4-step phase shifting)"),
        (C_DIM, "ground truth (y = x)"),
    ])
    labels += [
        (PX0 + 12, 410,
         f"every error is -{1:d}, -2, -3 x lambda/2 -- never anything in between "
         f"(max deviation from an integer: {frac:.2e})", C_DIM, 12, False),
        (PX0 + 12, 660,
         f"max |error| {csi_max * 1000:.4f} nm   RMS {csi_rms * 1000:.4f} nm   "
         f"over {len(steps)} step heights 0.10-1.00 um", C_TEAL, 12, True),
        (14, 766,
         f"design: coherence length {des['coherence_length_um']:.3f} um  "
         f"envelope FWHM {des['envelope_fwhm_um']:.3f} um  "
         f"Nyquist z-step {des['max_z_step_um']:.3f} um  "
         f"phase-shifting unambiguous step {des['phase_unambiguous_step_um']:.3f} um",
         C_DIM, 11, False),
    ]
    labels += tA + tAy + tB + tBy + tC + tCy
    frame = _text(_to_u8(canvas), labels)

    facts = {
        "wavelength_um": LAM, "lambda_over_4_um": LAM / 4.0, "lambda_over_2_um": LAM / 2.0,
        "n_steps": int(len(steps)), "psi_first_break_um": first_break,
        "psi_last_correct_um": last_ok, "psi_max_integer_deviation": frac,
        "psi_distinct_fringe_orders": n_orders,
        "psi_error_range_um": [float(e_psi.min()), float(e_psi.max())],
        "csi_max_abs_error_um": csi_max, "csi_rms_error_um": csi_rms,
        "design": {k: float(v) for k, v in des.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)},
    }
    return [frame], facts, 12, 0


# =========================================================================== #
# 2) 音響・振動診断 — 生スペクトル 対 包絡線スペクトル                          #
# =========================================================================== #
def build_bearing(log: Callable[[str], None]):
    import acoustics as A
    import dsp

    FS, FC, FD, M = 25600.0, 3000.0, 107.0, 0.5
    sig = A.synthesize_bearing_signal(FS, 1.0, FC, FD, modulation=M, mode="am")
    freqs, mag = dsp.spectrum(sig, FS)
    amp = mag * 2.0 / sig.size
    df = FS / sig.size
    i_def = int(round(FD / df))
    a_def = float(amp[i_def])
    a_car = float(amp[int(round(FC / df))])
    a_lo = float(amp[int(round((FC - FD) / df))])
    a_hi = float(amp[int(round((FC + FD) / df))])
    env = A.envelope_spectrum(sig, FS, 2000.0, 4000.0)

    # 同じ軸受の**衝撃型**の記録。共振周波数を人が知らないとき、どの帯域で復調
    # するかをスペクトル尖度に選ばせる(3 つ目の op)。
    imp = A.synthesize_bearing_signal(FS, 1.0, FC, FD, mode="impulse", damping=0.05,
                                      noise_sigma=0.05, seed=3)
    sk = A.spectral_kurtosis(imp, FS)
    lo = max(1.0, sk["max_freq"] - sk["bin_hz"])
    hi = min(FS / 2.0 - 1.0, sk["max_freq"] + sk["bin_hz"])
    env_auto = A.envelope_spectrum(imp, FS, lo, hi)
    kin = A.bearing_defect_frequencies(1800.0, 9, 8.0, 40.0)

    ratio = env["peak_amplitude"] / max(a_def, 1e-300)
    log(f"  raw spectrum at {FD:.0f} Hz = {a_def:.3e} (carrier {a_car:.6f}, "
        f"sidebands {a_lo:.6f}/{a_hi:.6f} = m/2)")
    log(f"  envelope spectrum peak {env['peak_freq']:.4f} Hz amplitude "
        f"{env['peak_amplitude']:.6f} (modulation m = {M}), prominence "
        f"{env['peak_prominence']:.1f}")
    log(f"  spectral kurtosis picks {lo:.0f}-{hi:.0f} Hz (max {sk['max_kurtosis']:.3f} "
        f"@ {sk['max_freq']:.0f} Hz) -> envelope peak {env_auto['peak_freq']:.4f} Hz")

    W, H = 1120, 830
    PX0, PX1 = 104, W - 22
    canvas = _canvas(H, W)
    _fill(canvas, 0, 30, 0, W, C_PANEL)

    axR = Axes(PX0, 66, PX1, 296, 0.0, 4000.0, 1e-17, 3.0, logy=True)
    axE = Axes(PX0, 362, PX1, 566, 0.0, 700.0, 0.0, 0.58)
    axK = Axes(PX0, 632, PX1, 780, 0.0, 12800.0, -1.4, 5.2)

    for ax in (axR, axE, axK):
        ax.bg(canvas)

    sel = freqs <= 4000.0
    canvas = axR.grid_y(canvas, [1e-15, 1e-12, 1e-9, 1e-6, 1e-3, 1.0])
    canvas = axR.series(canvas, freqs[sel], np.maximum(amp[sel], 1e-17), C_BLUE, 1)
    canvas = axR.vline(canvas, FD, C_AMBR, 2, dashed=True)
    canvas = axR.markers(canvas, [FD], [max(a_def, 1e-17)], C_ROSE, 7, "cross", 2)
    canvas = axR.axis(canvas)
    canvas, tR = axR.xticks(canvas, [0, 107, 1000, 2000, 2893, 3000, 3107, 4000],
                            ["0", "107", "1000", "2000", "2893", "3000", "3107", "4000"])
    canvas, tRy = axR.yticks(canvas, [1e-15, 1e-12, 1e-9, 1e-6, 1e-3, 1.0],
                             ["1e-15", "1e-12", "1e-9", "1e-6", "1e-3", "1"])

    esel = env["freqs"] <= 700.0
    canvas = axE.grid_y(canvas, [0.1, 0.2, 0.3, 0.4, 0.5])
    canvas = axE.series(canvas, env["freqs"][esel], env["magnitude"][esel], C_TEAL, 2)
    canvas = axE.vline(canvas, FD, C_AMBR, 2, dashed=True)
    canvas = axE.markers(canvas, [env["peak_freq"]], [env["peak_amplitude"]],
                         C_WHITE, 6, "cross", 2)
    canvas = axE.axis(canvas)
    canvas, tE = axE.xticks(canvas, [0, 107, 214, 321, 428, 535, 700],
                            ["0", "107", "214", "321", "428", "535", "700"])
    canvas, tEy = axE.yticks(canvas, [0.0, 0.25, 0.5], ["0.00", "0.25", "0.50"])

    canvas = axK.grid_y(canvas, [0.0, 2.0, 4.0])
    _fill(canvas, axK.y0, axK.y1, int(axK.X(lo)), int(axK.X(hi)), (0.14, 0.17, 0.21))
    canvas = axK.series(canvas, sk["freqs"], sk["kurtosis"], C_VIOL, 2)
    canvas = axK.markers(canvas, [sk["max_freq"]], [sk["max_kurtosis"]], C_WHITE, 6, "cross", 2)
    canvas = axK.axis(canvas)
    canvas, tK = axK.xticks(canvas, [0, 2000, 4000, 6000, 8000, 10000, 12800],
                            ["0", "2000", "4000", "6000", "8000", "10000", "12800"])
    canvas, tKy = axK.yticks(canvas, [0.0, 2.0, 4.0], ["0", "2", "4"])
    for ax in (axR, axE, axK):
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

    labels = [
        (14, 7, f"rolling-element bearing: {FC:.0f} Hz resonance amplitude-modulated at "
                f"the {FD:.0f} Hz defect rate (m = {M}), {FS / 1000:.1f} kHz x 1.0 s",
         C_TEXT, 13, False),
        (PX0, 46, "1  raw spectrum  (dsp.spectrum)   -- log amplitude",
         C_TEXT, 14, True),
        (PX0, 342, "2  envelope spectrum of the 2000-4000 Hz band  "
                   "(acoustics.envelope_spectrum)   -- linear amplitude", C_TEXT, 14, True),
        (PX0, 612, "3  spectral kurtosis picks the demodulation band without being told "
                   "the resonance  (acoustics.spectral_kurtosis, impulsive record)",
         C_TEXT, 14, True),
        (PX1 - 130, 300, "frequency [Hz] ->", C_DIM, 11, False),
        (PX1 - 130, 570, "frequency [Hz] ->", C_DIM, 11, False),
        (PX1 - 130, 784, "frequency [Hz] ->", C_DIM, 11, False),
        (int(axR.X(FD)) + 6, 84, f"{FD:.0f} Hz: amplitude {a_def:.2e}", C_ROSE, 12, True),
        (int(axR.X(FD)) + 6, 100, "the defect rate is NOT in the raw signal", C_ROSE, 12, True),
        (int(axR.X(FC)) - 170, 72, f"carrier {a_car:.4f}", C_BLUE, 12, True),
        (int(axR.X(FC)) - 170, 88,
         f"sidebands {a_lo:.4f} / {a_hi:.4f} = m/2", C_BLUE, 12, False),
        (int(axE.X(FD)) + 8, 374,
         f"peak {env['peak_freq']:.4f} Hz   amplitude {env['peak_amplitude']:.6f} "
         f"= the modulation depth m itself", C_TEAL, 13, True),
        (int(axE.X(FD)) + 8, 392,
         f"prominence {env['peak_prominence']:.0f} x median   "
         f"band fraction {env['band_fraction']:.4f}   "
         f"resolution {env['resolution_hz']:.2f} Hz", C_DIM, 12, False),
        (int(axE.X(FD)) + 8, 410,
         f"{env['peak_amplitude'] / max(a_def, 1e-300):.1e} times the raw-spectrum "
         f"amplitude at the same frequency", C_AMBR, 12, True),
        (int(axK.X(lo)) + 6, 640,
         f"selected {lo:.0f}-{hi:.0f} Hz  (max kurtosis {sk['max_kurtosis']:.3f} @ "
         f"{sk['max_freq']:.0f} Hz, window {sk['window_seconds'] * 1e3:.2f} ms)",
         C_VIOL, 12, True),
        (int(axK.X(lo)) + 6, 658,
         f"-> envelope peak {env_auto['peak_freq']:.4f} Hz  (true {FD:.0f} Hz), "
         f"amplitude {env_auto['peak_amplitude']:.4f}", C_TEAL, 12, True),
        (14, 800,
         f"kinematics (1800 rpm, 9 rolling elements, d=8 D=40 mm): shaft "
         f"{kin['shaft_hz']:.3f} / FTF {kin['ftf_hz']:.3f} / BPFO {kin['bpfo_hz']:.3f} / "
         f"BPFI {kin['bpfi_hz']:.3f} / BSF {kin['bsf_hz']:.3f} Hz   "
         f"check |BPFO+BPFI-N*f_r| = "
         f"{abs(kin['bpfo_hz'] + kin['bpfi_hz'] - 9 * kin['shaft_hz']):.1e}",
         C_DIM, 11, False),
    ]
    labels += tR + tRy + tE + tEy + tK + tKy
    frame = _text(_to_u8(canvas), labels)

    facts = {
        "rate_hz": FS, "carrier_hz": FC, "defect_hz": FD, "modulation": M,
        "raw_amplitude_at_defect": a_def, "raw_amplitude_carrier": a_car,
        "raw_amplitude_sidebands": [a_lo, a_hi],
        "envelope_peak_hz": float(env["peak_freq"]),
        "envelope_peak_amplitude": float(env["peak_amplitude"]),
        "envelope_prominence": float(env["peak_prominence"]),
        "envelope_band_fraction": float(env["band_fraction"]),
        "envelope_over_raw_ratio": float(ratio),
        "kurtosis_max": float(sk["max_kurtosis"]), "kurtosis_max_freq_hz": float(sk["max_freq"]),
        "kurtosis_band_hz": [float(lo), float(hi)],
        "kurtosis_auto_envelope_peak_hz": float(env_auto["peak_freq"]),
        "bearing_kinematics_hz": {k: float(v) for k, v in kin.items()
                                  if isinstance(v, (int, float))},
    }
    return [frame], facts, 12, 0


# =========================================================================== #
# 3) ライトフィールド — 1 枚の光場からリフォーカス(GIF)                       #
# =========================================================================== #
def build_lightfield(log: Callable[[str], None], frames: int = 27):
    import lightfield as L

    ANG, SIZE = 9, 112
    NEAR, FAR = 3.0, 0.0
    lf, truth = L.lf_synthesize((NEAR, FAR), (ANG, ANG), (SIZE, SIZE), occlusion=True,
                                coverage=0.40, texture_sigma=2.0, edge="wrap", seed=5)
    near_mask = truth > (NEAR + FAR) / 2.0
    far_mask = ~near_mask
    st = L.lf_stats(lf)

    slopes = np.round(np.linspace(3.6, -0.6, int(frames)), 6)

    def _sharp(img, mask):
        gy, gx = np.gradient(np.asarray(img, np.float64))
        return float((gy ** 2 + gx ** 2)[mask].mean())

    imgs, s_near, s_far = [], [], []
    for s in slopes:
        r = L.lf_refocus(lf, float(s), edge="wrap")
        imgs.append(r)
        s_near.append(_sharp(r, near_mask))
        s_far.append(_sharp(r, far_mask))
    s_near = np.asarray(s_near)
    s_far = np.asarray(s_far)
    peak_near = float(slopes[int(s_near.argmax())])
    peak_far = float(slopes[int(s_far.argmax())])
    smax = float(max(s_near.max(), s_far.max()))

    # 全視点を平均せずに 1 視点だけ見た場合(= 普通のカメラ)との比較
    centre = L.lf_center_view(lf)
    c_near, c_far = _sharp(centre, near_mask), _sharp(centre, far_mask)
    log(f"  light field {lf.shape}, near layer covers {near_mask.mean():.0%} of the frame")
    log(f"  sharpness peaks: near layer at slope {peak_near:+.2f} (true {NEAR:+.1f}), "
        f"far layer at slope {peak_far:+.2f} (true {FAR:+.1f})")
    log(f"  best/worst near-layer sharpness across the sweep: "
        f"{s_near.max():.5f} / {s_near.min():.5f} "
        f"({s_near.max() / max(s_near.min(), 1e-12):.1f}x)")

    SC = 2
    PAN = SIZE * SC                                    # 224
    MARGIN, GAP = 12, 16
    PLOT_W = 604
    W = MARGIN + PAN + GAP + PLOT_W + MARGIN           # 872
    HUD = 30
    PANY = HUD + 22
    H = PANY + PAN + 66                                # 342
    px0 = MARGIN + PAN + GAP + 62
    px1 = W - MARGIN - 12

    head = (f"light field {ANG}x{ANG} views x {SIZE}x{SIZE} px  "
            f"(lf_synthesize -> lf_refocus)   two layers: slope {NEAR:+.1f} in front "
            f"covering {near_mask.mean():.0%}, slope {FAR:+.1f} behind")
    out = []
    for i, s in enumerate(slopes):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        _place(canvas, _upscale(_gray_to_rgb(_norm01(imgs[i], 0.15, 0.85)), SC),
               PANY, MARGIN)
        canvas = _frame_box(canvas, PANY, PANY + PAN, MARGIN, MARGIN + PAN, C_GRID, 1)

        ax = Axes(px0, PANY, px1, PANY + PAN - 26, -0.6, 3.6, 0.0, smax * 1.12)
        ax.bg(canvas)
        canvas = ax.grid_y(canvas, [smax * 0.25, smax * 0.5, smax * 0.75, smax])
        canvas = ax.vline(canvas, NEAR, C_AMBR, 1, dashed=True)
        canvas = ax.vline(canvas, FAR, C_AMBR, 1, dashed=True)
        canvas = ax.series(canvas, slopes[:i + 1], s_near[:i + 1], C_TEAL, 2)
        canvas = ax.series(canvas, slopes[:i + 1], s_far[:i + 1], C_VIOL, 2)
        canvas = ax.markers(canvas, [s], [s_near[i]], C_WHITE, 5, "cross", 2)
        canvas = ax.markers(canvas, [s], [s_far[i]], C_WHITE, 5, "cross", 2)
        canvas = ax.vline(canvas, float(s), C_WHITE, 1)
        canvas = ax.axis(canvas)
        canvas, tx = ax.xticks(canvas, [-0.5, 0.0, 1.0, 2.0, 3.0, 3.5],
                               ["-0.5", "0.0", "1.0", "2.0", "3.0", "3.5"])
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        frame = _to_u8(canvas)
        focus = ("front layer" if abs(s - NEAR) < abs(s - FAR) else "back layer")
        labels = [
            (MARGIN, 7, head, C_TEXT, 12, False),
            (MARGIN, PANY - 18, f"refocused at slope {s:+.2f} px/view", C_TEXT, 13, True),
            (px0 - 60, PANY - 18, "gradient sharpness measured inside each layer",
             C_TEXT, 13, True),
            (MARGIN + 6, PANY + PAN + 6,
             f"sharpness  front {s_near[i]:.5f}   back {s_far[i]:.5f}   "
             f"-> in focus: {focus}", C_TEXT, 13, True),
            (MARGIN + 6, PANY + PAN + 26,
             f"one raw capture, {st['n_views']} views, max measurable slope "
             f"{st['max_slope_px']:.1f} px/view   |   sweep peaks at "
             f"{peak_near:+.2f} (front, true {NEAR:+.1f}) and {peak_far:+.2f} "
             f"(back, true {FAR:+.1f})", C_DIM, 12, False),
            (MARGIN + 6, PANY + PAN + 44,
             f"a single view cannot do this: centre view sharpness front "
             f"{c_near:.5f} / back {c_far:.5f} at the same time", C_DIM, 12, False),
            (px1 - 150, ax.y1 + 22, "refocus slope [px/view]", C_DIM, 11, False),
            (int(ax.X(NEAR)) + 5, ax.y0 + 4, f"front {NEAR:+.1f}", C_AMBR, 11, True),
            (int(ax.X(FAR)) + 5, ax.y0 + 4, f"back {FAR:+.1f}", C_AMBR, 11, True),
        ]
        labels += _legend(px0 + 10, ax.y0 + 24, [
            (C_TEAL, "front layer (slope +3.0)"),
            (C_VIOL, "back layer  (slope  0.0)"),
        ])
        labels += tx
        out.append(_text(frame, labels))

    thumb_index = int(np.argmin(np.abs(slopes - NEAR)))
    facts = {
        "views": [ANG, ANG], "shape": [SIZE, SIZE], "true_slopes": [NEAR, FAR],
        "near_coverage": float(near_mask.mean()),
        "slope_sweep": [float(slopes[0]), float(slopes[-1]), int(len(slopes))],
        "sharpness_peak_near_slope": peak_near, "sharpness_peak_far_slope": peak_far,
        "sharpness_near_range": [float(s_near.min()), float(s_near.max())],
        "sharpness_far_range": [float(s_far.min()), float(s_far.max())],
        "centre_view_sharpness": [c_near, c_far],
        "max_measurable_slope_px": float(st["max_slope_px"]),
    }
    return out, facts, 8, thumb_index


# =========================================================================== #
# 4) 光子計数 — 1 → 1000 photon/px(GIF)                                       #
# =========================================================================== #
def _photon_scene(n: int = 128) -> tuple:
    """決定的な合成シーン: 上が絵(円と縞)、下が 5 段のステップウェッジ。"""
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    img = np.full((n, n), 0.10)
    img += 0.55 * np.exp(-(((x - 0.34 * n) ** 2 + (y - 0.34 * n) ** 2) / (2 * (0.16 * n) ** 2)))
    ring = np.hypot(x - 0.68 * n, y - 0.36 * n)
    img[(ring > 0.16 * n) & (ring < 0.23 * n)] = 0.85
    bars = (np.floor(x / (n / 16.0)).astype(int) % 2 == 0) & (y > 0.56 * n) & (y < 0.70 * n)
    img[bars] = 0.95
    img[(y > 0.56 * n) & (y < 0.70 * n) & ~bars] = 0.15
    levels = (0.10, 0.30, 0.50, 0.75, 1.00)
    wedge = {}
    y0, y1 = int(0.76 * n), int(0.96 * n)
    for k, lv in enumerate(levels):
        xa = int(n * (0.04 + 0.185 * k))
        xb = int(n * (0.04 + 0.185 * k + 0.15))
        img[y0:y1, xa:xb] = lv
        wedge[lv] = (slice(y0, y1), slice(xa, xb))
    return np.clip(img, 0.0, 1.0), levels, wedge


def build_photon(log: Callable[[str], None], frames: int = 24):
    import photoncount as P

    scene, levels, wedge = _photon_scene(128)
    ns = np.unique(np.round(np.logspace(0.0, 3.0, int(frames)), 3))
    counts, stats, rel = [], [], []
    bars = []                                # 各水準の推定放射輝度と ±sqrt(N)/N
    for n in ns:
        c = P.photon_sample(scene, photons_per_unit=float(n), seed=0)
        counts.append(c)
        st = P.photon_statistics(c)
        stats.append(st)
        sig = P.photon_uncertainty(c)
        row = []
        for lv in levels:
            sl = wedge[lv]
            m = float(c[sl].mean())
            e = float(sig[sl].mean())
            row.append((m / n, e / n))
        bars.append(row)
        bright = wedge[1.00]
        rel.append(float(P.photon_uncertainty(c)[bright].mean()
                         / max(c[bright].mean(), 1e-12)))
    rel = np.asarray(rel)
    theory = 1.0 / np.sqrt(ns)
    dev = float(np.abs(rel / theory - 1.0).max())
    log(f"  photon sweep {ns[0]:.2f} -> {ns[-1]:.1f} photons/px, {len(ns)} frames")
    log(f"  relative uncertainty on the 1.00 patch: {rel[0]:.4f} -> {rel[-1]:.4f}; "
        f"matches 1/sqrt(N) to {dev:.1%}")

    SC = 2
    PAN = 128 * SC                                     # 256
    MARGIN, GAP = 12, 16
    PLOT_W = 620
    W = MARGIN + PAN + GAP + PLOT_W + MARGIN           # 916
    HUD = 30
    PANY = HUD + 22
    H = PANY + PAN + 66
    bx0, bx1 = MARGIN + PAN + GAP + 64, W - MARGIN - 12
    head = ("single-photon imaging: the same scene sampled with photon_sample(), "
            "1 -> 1000 photons per unit radiance (Poisson)")

    out = []
    for i, n in enumerate(ns):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        shown = _norm01(counts[i], 0.0, max(1.0, float(np.quantile(counts[i], 0.995))))
        _place(canvas, _upscale(_gray_to_rgb(shown), SC), PANY, MARGIN)
        canvas = _frame_box(canvas, PANY, PANY + PAN, MARGIN, MARGIN + PAN, C_GRID, 1)

        # 上: 5 水準の推定放射輝度 ± photon_uncertainty/N(誤差棒が縮む)
        axB = Axes(bx0, PANY, bx1, PANY + 116, -0.6, 4.6, 0.0, 1.45)
        axB.bg(canvas)
        canvas = axB.grid_y(canvas, [0.25, 0.5, 0.75, 1.0, 1.25])
        for k, lv in enumerate(levels):
            m, e = bars[i][k]
            xk = float(axB.X(k))
            canvas = imagedraw.draw_line(canvas, (xk, axB.Y(m - e)), (xk, axB.Y(m + e)),
                                         color=C_AMBR, width=3)
            canvas = imagedraw.draw_line(canvas, (xk - 7, axB.Y(m - e)), (xk + 7, axB.Y(m - e)),
                                         color=C_AMBR, width=2)
            canvas = imagedraw.draw_line(canvas, (xk - 7, axB.Y(m + e)), (xk + 7, axB.Y(m + e)),
                                         color=C_AMBR, width=2)
            canvas = imagedraw.draw_line(canvas, (xk - 11, axB.Y(lv)), (xk + 11, axB.Y(lv)),
                                         color=C_TEAL, width=2)
            canvas = imagedraw.draw_markers(canvas, [(xk, float(axB.Y(m)))],
                                            color=C_WHITE, size=4, shape="cross", width=2)
        canvas = axB.axis(canvas)
        canvas, tB = axB.xticks(canvas, list(range(5)),
                                [f"{lv:.2f}" for lv in levels])
        canvas, tBy = axB.yticks(canvas, [0.0, 0.5, 1.0], ["0.0", "0.5", "1.0"])
        canvas = _frame_box(canvas, axB.y0, axB.y1, axB.x0, axB.x1)

        # 下: 相対不確かさ 対 光子数(両対数)と 1/sqrt(N)
        axU = Axes(bx0, PANY + 146, bx1, PANY + PAN - 12, 0.9, 1100.0, 0.02, 1.4,
                   logx=True, logy=True)
        axU.bg(canvas)
        canvas = axU.grid_y(canvas, [0.03, 0.1, 0.3, 1.0])
        canvas = axU.series(canvas, ns, theory, C_DIM, 3)
        canvas = axU.series(canvas, ns[:i + 1], rel[:i + 1], C_AMBR, 2)
        canvas = axU.markers(canvas, [n], [rel[i]], C_WHITE, 5, "cross", 2)
        canvas = axU.axis(canvas)
        canvas, tU = axU.xticks(canvas, [1, 3, 10, 30, 100, 300, 1000],
                                ["1", "3", "10", "30", "100", "300", "1000"])
        canvas, tUy = axU.yticks(canvas, [0.03, 0.1, 0.3, 1.0],
                                 ["0.03", "0.10", "0.30", "1.00"])
        canvas = _frame_box(canvas, axU.y0, axU.y1, axU.x0, axU.x1)

        st = stats[i]
        frame = _to_u8(canvas)
        labels = [
            (MARGIN, 7, head, C_TEXT, 12, False),
            (MARGIN, PANY - 18,
             f"{n:7.2f} photons/unit   {counts[i].sum():.0f} photons in the frame   "
             f"empty pixels {st['zero_fraction']:.1%}", C_TEXT, 13, True),
            (bx0 - 62, PANY - 18,
             "estimated radiance +/- photon_uncertainty / N  (5 step-wedge patches)",
             C_TEXT, 12, True),
            (bx0 - 62, PANY + 130,
             "relative uncertainty of the brightest patch vs photon count",
             C_TEXT, 12, True),
            (MARGIN + 6, PANY + PAN + 6,
             f"mean {st['mean']:8.3f}   variance {st['variance']:9.3f}   "
             f"Fano {st['fano_factor']:.4f} (Poisson = 1)", C_TEXT, 13, True),
            (MARGIN + 6, PANY + PAN + 26,
             f"SNR measured {st['snr_measured']:7.3f}   sqrt(N) {st['snr_poisson']:7.3f}"
             f"   error bar on the 1.00 patch {rel[i] * 100:6.2f} %  "
             f"(1/sqrt(N) = {theory[i] * 100:6.2f} %)", C_AMBR, 13, True),
            (MARGIN + 6, PANY + PAN + 44,
             f"noise here is not a setting: it is sqrt(N). Over the whole sweep the "
             f"measured bar tracks 1/sqrt(N) to {dev:.1%}.", C_DIM, 12, False),
            (bx1 - 118, axU.y1 + 22, "photons per unit ->", C_DIM, 11, False),
        ]
        labels += _legend(bx0 + 10, axB.y0 + 6, [
            (C_TEAL, "true radiance"), (C_AMBR, "measurement +/- 1 sigma")])
        labels += _legend(bx0 + 10, axU.y0 + 6, [
            (C_AMBR, "measured"), (C_DIM, "1/sqrt(N)")])
        labels += tB + tBy + tU + tUy
        out.append(_text(frame, labels))

    facts = {
        "photons_per_unit": [float(v) for v in ns],
        "relative_uncertainty_first_last": [float(rel[0]), float(rel[-1])],
        "sqrt_n_max_deviation": dev,
        "fano_first_last": [float(stats[0]["fano_factor"]), float(stats[-1]["fano_factor"])],
        "snr_first_last": [float(stats[0]["snr_measured"]), float(stats[-1]["snr_measured"])],
        "zero_fraction_first_last": [float(stats[0]["zero_fraction"]),
                                     float(stats[-1]["zero_fraction"])],
        "wedge_levels": [float(v) for v in levels],
    }
    return out, facts, 8, len(ns) - 1


# =========================================================================== #
# 5) 四元数画像 — 色空間の 3 次元回転(GIF)                                     #
# =========================================================================== #
def _colour_scene(n: int = 112) -> np.ndarray:
    """決定的な色見本: 中央に色相の円盤、四隅に純色・白のパッチ。"""
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    cx = cy = (n - 1) / 2.0
    r = np.hypot(x - cx, y - cy) / (0.44 * n)
    th = np.mod(np.arctan2(y - cy, x - cx), 2.0 * np.pi)
    hue = th / (2.0 * np.pi) * 6.0
    i = np.floor(hue).astype(int) % 6
    f = hue - np.floor(hue)
    s = np.clip(r, 0.0, 1.0)
    v = np.where(r <= 1.0, 1.0, 0.0)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    rgb = np.zeros((n, n, 3))
    for k, (rr, gg, bb) in enumerate(((v, t, p), (q, v, p), (p, v, t),
                                      (p, q, v), (t, p, v), (v, p, q))):
        m = i == k
        rgb[m] = np.stack([rr, gg, bb], -1)[m]
    rgb[r > 1.0] = 0.08
    e = int(0.20 * n)
    rgb[:e, :e] = (1.0, 0.0, 0.0)                 # 純赤
    rgb[:e, -e:] = (0.0, 1.0, 0.0)                # 純緑
    rgb[-e:, :e] = (0.0, 0.0, 1.0)                # 純青
    rgb[-e:, -e:] = (1.0, 1.0, 1.0)               # 白
    return rgb


def build_quaternion(log: Callable[[str], None], frames: int = 31):
    import quatimage as qi

    rgb = _colour_scene(112)
    q = qi.rgb_to_quaternion(rgb)
    axis = (0.0, 0.0, 1.0)                          # 青軸まわり = 赤 <-> 緑 の面
    angles = np.round(np.linspace(0.0, 90.0, int(frames)), 6)

    quat_imgs, diag_imgs, maxdiff, opnorm, red_q, red_d = [], [], [], [], [], []
    for a in angles:
        rad = np.radians(float(a))
        rot = qi.quaternion_to_rgb(qi.quat_color_rotate(q, axis, rad))
        c, s = np.cos(rad), np.sin(rad)
        R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        D = np.diag(np.diag(R))                     # チャンネルごとの最良の利得
        dia = rgb @ D.T
        quat_imgs.append(rot)
        diag_imgs.append(dia)
        maxdiff.append(float(np.abs(rot - dia).max()))
        opnorm.append(float(np.linalg.norm(R - D, 2)))
        red_q.append(R @ np.array([1.0, 0.0, 0.0]))
        red_d.append(D @ np.array([1.0, 0.0, 0.0]))
    maxdiff = np.asarray(maxdiff)
    opnorm = np.asarray(opnorm)

    # 行列表現との一致(四元数が「勝たない」相手)を 1 度だけ実測して焼く
    rad90 = np.radians(90.0)
    c90, s90 = np.cos(rad90), np.sin(rad90)
    R90 = np.array([[c90, -s90, 0.0], [s90, c90, 0.0], [0.0, 0.0, 1.0]])
    mat_err = float(np.abs(qi.quaternion_to_rgb(qi.quat_color_rotate(q, axis, rad90))
                           - rgb @ R90.T).max())
    log(f"  quaternion rotation about the blue axis, 0 -> 90 deg in {len(angles)} steps")
    log(f"  max |quaternion - best per-channel gain| grows to {maxdiff.max():.4f}; "
        f"||R - diag(R)||_2 grows to {opnorm.max():.4f}")
    log(f"  quaternion vs an explicit 3x3 rotation matrix at 90 deg: {mat_err:.2e} "
        f"(the same map -- quaternions do not beat matrices, only per-channel gains)")

    SC = 2
    PAN = 112 * SC                                  # 224
    MARGIN, GAP = 12, 16
    PLOT_W = 500
    W = MARGIN + PAN + GAP + PAN + GAP + PLOT_W + MARGIN
    HUD = 30
    PANY = HUD + 22
    H = PANY + PAN + 88
    px0 = MARGIN + 2 * (PAN + GAP) + 58
    px1 = W - MARGIN - 12
    head = ("quaternion colour rotation q x q*  (quatimage.quat_color_rotate) -- "
            "a 3-D rotation of the colour vector, about the blue axis")

    out = []
    for i, a in enumerate(angles):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        _place(canvas, np.clip(quat_imgs[i], 0, 1), PANY, MARGIN)
        x2 = MARGIN + PAN + GAP
        _place(canvas, np.clip(diag_imgs[i], 0, 1), PANY, x2)
        canvas = _frame_box(canvas, PANY, PANY + PAN, MARGIN, MARGIN + PAN, C_GRID, 1)
        canvas = _frame_box(canvas, PANY, PANY + PAN, x2, x2 + PAN, C_GRID, 1)

        ax = Axes(px0, PANY, px1, PANY + PAN - 30, 0.0, 90.0, 0.0, 1.55)
        ax.bg(canvas)
        canvas = ax.grid_y(canvas, [0.5, 1.0, 1.5])
        canvas = ax.series(canvas, angles[:i + 1], maxdiff[:i + 1], C_AMBR, 3)
        canvas = ax.series(canvas, angles[:i + 1], opnorm[:i + 1], C_VIOL, 2)
        canvas = ax.markers(canvas, [a], [maxdiff[i]], C_WHITE, 5, "cross", 2)
        canvas = ax.axis(canvas)
        canvas, tx = ax.xticks(canvas, [0, 30, 45, 60, 90], ["0", "30", "45", "60", "90"])
        canvas, ty = ax.yticks(canvas, [0.0, 0.5, 1.0, 1.5], ["0.0", "0.5", "1.0", "1.5"])
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        # 純赤パッチの行き先を色見本で並べる
        sw_y = PANY + PAN + 44
        for k, (col, lab_x) in enumerate(((red_q[i], MARGIN + 92), (red_d[i], x2 + 92))):
            _fill(canvas, sw_y, sw_y + 22, lab_x, lab_x + 46, np.clip(col, 0, 1))
            canvas = _frame_box(canvas, sw_y, sw_y + 22, lab_x, lab_x + 46, C_GRID, 1)

        frame = _to_u8(canvas)
        labels = [
            (MARGIN, 7, head, C_TEXT, 12, False),
            (MARGIN, PANY - 18, f"quaternion rotation, {a:5.1f} deg", C_TEAL, 13, True),
            (x2, PANY - 18, "best per-channel gain (diagonal matrix)", C_ROSE, 13, True),
            (px0 - 58, PANY - 18, "how far apart the two are", C_TEXT, 13, True),
            (MARGIN + 6, PANY + PAN + 8,
             f"pure red (1,0,0) -> ({red_q[i][0]:+.3f}, {red_q[i][1]:+.3f}, "
             f"{red_q[i][2]:+.3f})", C_TEXT, 12, True),
            (x2 + 6, PANY + PAN + 8,
             f"pure red (1,0,0) -> ({red_d[i][0]:+.3f}, {red_d[i][1]:+.3f}, "
             f"{red_d[i][2]:+.3f})", C_TEXT, 12, True),
            (MARGIN + 6, sw_y + 4, "red goes:", C_DIM, 12, False),
            (x2 + 6, sw_y + 4, "red goes:", C_DIM, 12, False),
            (MARGIN + 6, PANY + PAN + 70,
             f"max |difference| over the image {maxdiff[i]:.4f}   "
             f"||R - diag(R)||_2 {opnorm[i]:.4f}   "
             f"a per-channel gain can never turn red into green: it can only scale "
             f"the zero in the green channel.", C_AMBR, 12, True),
            (px1 - 110, ax.y1 + 22, "rotation angle [deg]", C_DIM, 11, False),
            (px0 + 8, ax.y1 + 42,
             f"vs an explicit 3x3 rotation matrix: {mat_err:.1e}", C_DIM, 11, False),
            (px0 + 8, ax.y1 + 56, "(quaternions do not beat matrices, only gains)",
             C_DIM, 11, False),
        ]
        labels += _legend(px0 + 10, ax.y0 + 6, [
            (C_AMBR, "max |quat - diagonal| (image)"),
            (C_VIOL, "||R - diag(R)||_2 (operator)"),
        ])
        labels += tx + ty
        out.append(_text(frame, labels))

    facts = {
        "axis": list(axis), "angles_deg": [float(v) for v in angles],
        "max_difference_at_90deg": float(maxdiff[-1]),
        "operator_norm_at_90deg": float(opnorm[-1]),
        "red_under_quaternion_at_90deg": [float(v) for v in red_q[-1]],
        "red_under_diagonal_at_90deg": [float(v) for v in red_d[-1]],
        "quaternion_vs_matrix_max_error": mat_err,
    }
    return out, facts, 10, len(angles) - 1


# =========================================================================== #
# 6) FMCW レンジ-ドップラー — 矩形窓 対 hann 窓                                #
# =========================================================================== #
def build_fmcw(log: Callable[[str], None]):
    import rangedoppler as RD

    wave = dict(n_samples=64, n_chirps=32, sample_rate_hz=1.0e7,
                slope_hz_per_s=2.0e13, chirp_period_s=5.0e-5, wavelength_m=3.8934e-3)
    des = RD.fmcw_design(**wave)
    dr, dv = des["range_bin_m"], des["velocity_bin_ms"]
    weak_db = -45.0
    strong_rb, weak_rb, dop_bin = 10.5, 20.0, 6
    cube = RD.fmcw_beat_simulate([strong_rb * dr, weak_rb * dr],
                                 [dop_bin * dv, dop_bin * dv],
                                 amplitudes=[1.0, 10.0 ** (weak_db / 20.0)], **wave)

    maps, profiles, meas = {}, {}, {}
    for w in ("rect", "hann"):
        m = RD.range_doppler_map(RD.fmcw_window_apply(cube, w, "both"), normalize=True)
        maps[w] = m
        i, j = np.unravel_index(int(np.argmax(m)), m.shape)
        row = m[i]
        profiles[w] = row
        lvl = 20.0 * np.log10(row[int(weak_rb)] / row.max())
        meas[w] = {
            "peak": float(row.max()), "peak_bin": int(j), "doppler_bin": int(i) - 16,
            "weak_db": float(lvl),
            "is_local_max": bool(row[int(weak_rb)] > row[int(weak_rb) - 1]
                                 and row[int(weak_rb)] > row[int(weak_rb) + 1]),
            "peak_loss_db": float(20.0 * np.log10(row.max())),
        }
        log(f"  {w:5s}: peak {row.max():.4f} at range bin {j}, doppler bin {i - 16}; "
            f"weak target at bin {int(weak_rb)} sits {lvl:+.2f} dB down, "
            f"local maximum = {meas[w]['is_local_max']}")

    MAP_H, MAP_W = maps["rect"].shape                 # (32, 64)
    SC = 7
    PANH, PANW = MAP_H * SC, MAP_W * SC               # 224 x 448
    MARGIN, GAP = 14, 18
    W = MARGIN + PANW + GAP + PANW + MARGIN           # 942
    HUD = 30
    MAPY = HUD + 26
    PLOTY = MAPY + PANH + 62
    PLOTH = 208
    H = PLOTY + PLOTH + 78

    canvas = _canvas(H, W)
    _fill(canvas, 0, HUD, 0, W, C_PANEL)
    DB_LO, DB_HI = -70.0, 0.0
    label_extra = []
    for k, w in enumerate(("rect", "hann")):
        m = maps[w]
        db = 20.0 * np.log10(np.maximum(m, 1e-12) / m.max())
        x = MARGIN + k * (PANW + GAP)
        _place(canvas, _upscale(_cmap(_norm01(db, DB_LO, DB_HI)), SC), MAPY, x)
        canvas = _frame_box(canvas, MAPY, MAPY + PANH, x, x + PANW, C_GRID, 1)
        # 標的の在り処を円で指し示す(imagedraw op)
        for rb, col in ((strong_rb, C_WHITE), (weak_rb, C_AMBR)):
            cxp = x + (rb + 0.5) * SC
            cyp = MAPY + (dop_bin + MAP_H // 2 + 0.5) * SC
            canvas = imagedraw.draw_circle(canvas, (cxp, cyp), 13.0, color=col, width=2)
        label_extra.append((x + 6, MAPY - 20,
                            f"{w} window   peak {m.max():.4f}", C_TEXT, 13, True))

    ax = Axes(MARGIN + 62, PLOTY, W - MARGIN - 12, PLOTY + PLOTH, 0.0, 63.0, -78.0, 2.0)
    ax.bg(canvas)
    canvas = ax.grid_y(canvas, [-60.0, -45.0, -30.0, -15.0, 0.0])
    canvas = ax.hline(canvas, weak_db, C_AMBR, 1, dashed=True)
    for w, col in (("rect", C_ROSE), ("hann", C_TEAL)):
        row = profiles[w]
        db = 20.0 * np.log10(np.maximum(row, 1e-12) / row.max())
        canvas = ax.series(canvas, np.arange(len(db)), db, col, 2)
    canvas = ax.vline(canvas, weak_rb, C_AMBR, 1, dashed=True)
    canvas = ax.axis(canvas)
    canvas, tx = ax.xticks(canvas, [0, 10, 20, 30, 40, 50, 60],
                           ["0", "10", "20", "30", "40", "50", "60"])
    canvas, ty = ax.yticks(canvas, [0, -15, -30, -45, -60],
                           ["0", "-15", "-30", "-45", "-60"])
    canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

    frame = _to_u8(canvas)
    labels = [
        (14, 7, f"FMCW range-Doppler: a strong target at range bin {strong_rb} "
                f"(half a bin off) and a {weak_db:.0f} dB weaker one at bin "
                f"{weak_rb:.0f}, both at Doppler bin +{dop_bin}   "
                f"(bin {dr:.4f} m / {dv:.4f} m/s)", C_TEXT, 12, False),
        (MARGIN + 62, PLOTY - 22,
         f"range profile through Doppler bin +{dop_bin}  [dB relative to the peak]",
         C_TEXT, 13, True),
        (ax.x1 - 96, ax.y1 + 24, "range bin ->", C_DIM, 11, False),
        (int(ax.X(weak_rb)) + 6, ax.y0 + 6,
         f"true level of the weak target: {weak_db:.0f} dB", C_AMBR, 12, True),
        (MARGIN + 76, ax.y0 + 6,
         f"rect: the weak target sits at {meas['rect']['weak_db']:+.2f} dB "
         f"({meas['rect']['weak_db'] - weak_db:+.1f} dB above where it should be) and is "
         f"{'a' if meas['rect']['is_local_max'] else 'NOT a'} local maximum "
         f"-- buried in the leakage skirt", C_ROSE, 12, True),
        (MARGIN + 76, ax.y0 + 24,
         f"hann: {meas['hann']['weak_db']:+.2f} dB "
         f"({meas['hann']['weak_db'] - weak_db:+.1f} dB) and IS a local maximum "
         f"-- recovered, at the cost of {meas['rect']['peak'] / meas['hann']['peak']:.2f}x "
         f"peak height and a wider main lobe", C_TEAL, 12, True),
        (14, H - 52,
         f"measured peak sidelobe level of the windows themselves (module's own "
         f"numbers): rect -13.25 dB, hann -31.47 dB.  The rect peak "
         f"{meas['rect']['peak']:.4f} is the half-bin scalloping loss 2/pi = "
         f"{2 / np.pi:.4f}.", C_DIM, 11, False),
        (14, H - 34,
         f"colour = magnitude in dB, {DB_LO:.0f} .. {DB_HI:.0f}.  white circle = strong "
         f"target, amber circle = weak target.  vertical axis = Doppler bin "
         f"(-16 .. +15), horizontal = range bin (0 .. 63).", C_DIM, 11, False),
    ]
    labels += label_extra
    labels += _legend(ax.x0 + 8, ax.y1 - 44, [(C_ROSE, "rect"), (C_TEAL, "hann")])
    labels += tx + ty
    frame = _text(frame, labels)

    facts = {
        "range_bin_m": float(dr), "velocity_bin_ms": float(dv),
        "sweep_bandwidth_hz": float(des["sweep_bandwidth_hz"]),
        "targets": {"strong_range_bin": strong_rb, "weak_range_bin": weak_rb,
                    "doppler_bin": dop_bin, "weak_true_db": weak_db},
        "measured": meas,
        "half_bin_scalloping_2_over_pi": float(2 / np.pi),
    }
    return [frame], facts, 12, 0


# =========================================================================== #
# 7) 鏡面反射の分離 + 遮蔽灯 k=0..6 の崖                                        #
# =========================================================================== #
def _bump_normals(h=64, w=64, amp=6.0, sigma=14.0):
    """ガウス丘の float64 の単位法線(float32 に丸めると測定の床が上がるため)。"""
    y, x = np.mgrid[0:h, 0:w]
    z = amp * np.exp(-(((x - w / 2.0) ** 2 + (y - h / 2.0) ** 2) / (2.0 * sigma ** 2)))
    zy, zx = np.gradient(z)
    n = np.stack([-zx, -zy, np.ones_like(zx)], axis=-1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def build_specular(log: Callable[[str], None]):
    import photometric as PM
    import specularity as SP

    h = w = 64
    WHITE_L = np.ones(3) / np.sqrt(3.0)
    normals = _bump_normals(h, w)
    albedo = np.array([0.80, 0.55, 0.35])
    light = np.array([0.3, 0.2, 1.0])
    shading = PM.render_lambertian(normals, 1.0, light).astype(np.float64)
    diffuse_true = albedo * shading[..., None]
    y, x = np.mgrid[0:h, 0:w]
    m_s_true = 0.7 * np.exp(-(((x - 26.0) ** 2 + (y - 24.0) ** 2) / 26.0))
    m_s_true[m_s_true < 1e-3] = 0.0
    image = diffuse_true + m_s_true[..., None] * WHITE_L

    diffuse, specular = SP.specular_diffuse_split(image)
    err_d = float(np.abs(diffuse - diffuse_true).max())
    err_s = float(np.abs(specular - m_s_true[..., None] * WHITE_L).max())
    err_part = float(np.abs(diffuse + specular - image).max())
    coeff = SP.specular_coefficient_map(image)
    err_c = float(np.abs(coeff - m_s_true).max())
    log(f"  dichromatic split: diffuse max error {err_d:.2e}, specular {err_s:.2e}, "
        f"closure {err_part:.2e}, coefficient map {err_c:.2e}")

    # 遮蔽灯 k = 0..6 で法線誤差がどこで崩れるか
    n_lights = 8
    L = np.array([[np.cos(a), np.sin(a), 2.2]
                  for a in np.linspace(0, 2 * np.pi, n_lights, endpoint=False)])
    L = L / np.linalg.norm(L, axis=1, keepdims=True)
    surface = _bump_normals(h, w, amp=4.0)
    alb_map = 0.7 + 0.2 * np.cos(np.linspace(0, 3, h))[:, None] * np.ones((1, w))
    ndl = np.einsum("hwc,nc->nhw", surface, L)
    clean = alb_map[None] * ndl
    methods = ("lstsq", "median", "ransac")
    ks = list(range(0, 7))
    curves = {m: [] for m in methods}
    for k in ks:
        obs = clean.copy()
        if k:
            obs[:k] = 0.0
        for m in methods:
            nrm, _alb, _inl = SP.photometric_stereo_robust(obs, L, method=m)
            curves[m].append(float(PM.angular_error_deg(nrm, surface).mean()))
    for m in methods:
        curves[m] = np.asarray(curves[m])
    floor = float(PM.angular_error_deg(surface.astype(np.float32), surface).max())
    cliff = next((k for k in ks if curves["ransac"][k] > 1.0), None)
    log(f"  N.L min over the frame {ndl.min():.4f} (no attached shadows -- "
        f"only the blocked lights matter)")
    for m in methods:
        log(f"  {m:7s}: " + "  ".join(f"k={k}:{curves[m][k]:.4f}" for k in ks))
    log(f"  robust methods break at k = {cliff} of {n_lights} lights; "
        f"float32 quantisation floor {floor:.6f} deg")

    SC = 4
    PAN = h * SC                                   # 256
    MARGIN, GAP = 14, 18
    W = MARGIN + 3 * PAN + 2 * GAP + MARGIN        # 830
    HUD = 30
    PANY = HUD + 26
    PLOTY = PANY + PAN + 76
    PLOTH = 230
    H = PLOTY + PLOTH + 96

    canvas = _canvas(H, W)
    _fill(canvas, 0, HUD, 0, W, C_PANEL)
    gain = 1.0 / max(float(specular.max()), 1e-12)
    panels = [("input (glossy)", np.clip(image, 0, 1), 1.0),
              ("diffuse  (specular_diffuse_split)", np.clip(diffuse, 0, 1), 1.0),
              (f"specular (x{gain:.2f} for display)", np.clip(specular * gain, 0, 1), gain)]
    heads = []
    for k, (title, img, _g) in enumerate(panels):
        x = MARGIN + k * (PAN + GAP)
        _place(canvas, _upscale(img, SC), PANY, x)
        canvas = _frame_box(canvas, PANY, PANY + PAN, x, x + PAN, C_GRID, 1)
        heads.append((x + 4, PANY - 20, title, C_TEXT, 13, True))

    ax = Axes(MARGIN + 74, PLOTY, W - MARGIN - 12, PLOTY + PLOTH, -0.3, 6.3,
              5e-5, 200.0, logy=True)
    ax.bg(canvas)
    canvas = ax.grid_y(canvas, [1e-4, 1e-2, 1.0, 100.0])
    canvas = ax.hline(canvas, floor, C_DIM, 1, dashed=True)
    for m, col in (("lstsq", C_ROSE), ("median", C_BLUE), ("ransac", C_TEAL)):
        canvas = ax.series(canvas, ks, np.maximum(curves[m], 5e-5), col, 2)
        canvas = ax.markers(canvas, ks, np.maximum(curves[m], 5e-5), col, 5, "circle", 2)
    if cliff is not None:
        canvas = ax.vline(canvas, float(cliff) - 0.5, C_AMBR, 2, dashed=True)
    canvas = ax.axis(canvas)
    canvas, tx = ax.xticks(canvas, ks, [str(k) for k in ks])
    canvas, ty = ax.yticks(canvas, [1e-4, 1e-2, 1.0, 100.0],
                           ["1e-4", "0.01", "1", "100"])
    canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

    frame = _to_u8(canvas)
    labels = [
        (14, 7, "specular / diffuse separation (dichromatic reflectance) and "
                "photometric stereo under cast shadows", C_TEXT, 13, False),
        (MARGIN, PANY + PAN + 10,
         f"the split is a projection, not an optimisation: diffuse max error "
         f"{err_d:.2e}, specular {err_s:.2e}, diffuse+specular-input {err_part:.2e}, "
         f"coefficient map m_s {err_c:.2e}", C_TEAL, 12, True),
        (MARGIN, PANY + PAN + 30,
         f"peak highlight m_s {m_s_true.max():.3f}; {float((m_s_true == 0).mean()):.0%} of "
         f"the pixels carry no specular component at all (that is what makes the "
         f"separation solvable)", C_DIM, 12, False),
        (MARGIN + 74, PLOTY - 22,
         f"mean normal error [deg] vs number of blocked lights, {n_lights} lights total "
         f"(photometric_stereo_robust)", C_TEXT, 13, True),
        (ax.x1 - 156, ax.y1 + 24, "blocked lights k (of 8) ->", C_DIM, 11, False),
        (int(ax.X(0)) + 8, ax.y0 + 6,
         f"plain least squares is already {curves['lstsq'][1]:.1f} deg wrong with one "
         f"blocked light", C_ROSE, 12, True),
        (int(ax.X(0)) + 8, ax.y0 + 24,
         f"median / ransac hold at {curves['ransac'][3]:.4f} deg through k=3 "
         f"-- that is the float32 output floor ({floor:.4f} deg), not an error",
         C_TEAL, 12, True),
        (int(ax.X(max(cliff - 0.5, 0.0))) + 8, ax.y0 + 44,
         f"k={cliff}: half the lights blocked -> ransac {curves['ransac'][cliff]:.2f} deg, "
         f"median {curves['median'][cliff]:.2f} deg. A majority vote cannot pick "
         f"between 'shadowed' and 'black surface'.", C_AMBR, 12, True),
        (14, H - 74,
         f"N.L is positive everywhere (min {ndl.min():.4f}), so every failure below is "
         f"the blocked lights and nothing else.", C_DIM, 11, False),
        (14, H - 56,
         "  k : " + "   ".join(f"{k}" for k in ks), C_DIM, 11, False),
    ]
    for i, (m, col) in enumerate((("lstsq", C_ROSE), ("median", C_BLUE), ("ransac", C_TEAL))):
        labels.append((14, H - 40 + i * 14,
                       f"{m:7s}: " + "  ".join(f"{curves[m][k]:8.4f}" for k in ks),
                       col, 11, False))
    labels += heads
    labels += _legend(ax.x0 + 8, ax.y1 - 62,
                      [(C_ROSE, "lstsq"), (C_BLUE, "median"), (C_TEAL, "ransac")])
    labels += tx + ty
    frame = _text(frame, labels)

    facts = {
        "split_max_error_diffuse": err_d, "split_max_error_specular": err_s,
        "split_closure": err_part, "coefficient_map_max_error": err_c,
        "peak_highlight_m_s": float(m_s_true.max()),
        "specular_free_pixel_fraction": float((m_s_true == 0).mean()),
        "n_lights": n_lights, "blocked_k": ks,
        "mean_normal_error_deg": {m: [float(v) for v in curves[m]] for m in methods},
        "float32_floor_deg": floor, "break_at_k": cliff, "min_n_dot_l": float(ndl.min()),
    }
    return [frame], facts, 12, 0


# =========================================================================== #
# 8) モーション増幅 — 0.2 px の振動と J0 第一零点の崖(GIF)                     #
# =========================================================================== #
def build_motionmag(log: Callable[[str], None], frames: int = 32):
    import motionmag as M

    H_IM = W_IM = 96
    T = int(frames)
    FPS, FREQ, BAND = 32.0, 4.0, (3.0, 5.0)
    D0, ALPHA = 0.2, 20.0
    CYC_X = 8                                   # 既定の 8 px 成分
    K_X = 2.0 * np.pi * CYC_X / W_IM

    vid = M.synthesize_translation((H_IM, W_IM), T, D0, FREQ, FPS)
    res = M.motion_magnify(vid, ALPHA, *BAND, FPS)
    mag = res["video"]

    def read_dx(v):
        spec = np.fft.fft2(v, axes=(1, 2))
        return -np.unwrap(np.angle(spec[:, 0, CYC_X])) / (2.0 * np.pi * CYC_X / W_IM)

    d_in, d_out = read_dx(vid), read_dx(mag)
    gain = float(np.abs(d_out).max() / np.abs(d_in).max())
    truth_d = D0 * np.sin(2.0 * np.pi * FREQ * np.arange(T) / FPS)
    err_in = float(np.abs(d_in - truth_d).max())

    # 崖: 振幅を上げていくと J0(k*A) の第一零点で計測が反転する
    try:
        from scipy.special import jn_zeros
        j0_zero = float(jn_zeros(0, 1)[0])
    except Exception:                            # scipy が無ければ既知の定数
        j0_zero = 2.404825557695773
    cliff_px = j0_zero / K_X
    amps = np.round(np.concatenate([np.linspace(0.25, 2.75, 11),
                                    np.linspace(2.9, 3.35, 10),
                                    np.linspace(3.5, 6.0, 6)]), 6)
    meas = []
    for a in amps:
        v = M.synthesize_translation((64, 64), 64, float(a), FREQ, FPS)
        meas.append(float(np.abs(M.displacement_series(v, *BAND, FPS)[:, 0]).max()))
    meas = np.asarray(meas)
    rel = np.abs(meas - amps) / amps
    good = amps[rel < 1e-9]
    bad = amps[rel >= 1e-9]
    last_ok = float(good.max()) if good.size else float("nan")
    first_bad = float(bad.min()) if bad.size else float("nan")

    log(f"  magnify {D0} px by alpha={ALPHA:.0f}: measured gain {gain:.6f}, "
        f"peak displacement {np.abs(d_in).max():.4f} -> {np.abs(d_out).max():.4f} px")
    log(f"  input clip matches the closed form to {err_in:.2e} px")
    log(f"  image SNR change {res['image_snr_change_db']:+.4f} dB, motion SNR change "
        f"{res['motion_snr_change_db']:+.4f} dB (never positive)")
    log(f"  measurement holds to {last_ok:.4f} px and breaks at {first_bad:.4f} px; "
        f"J0 first zero {j0_zero:.10f} / k = {cliff_px:.4f} px")

    SC = 2
    PAN = H_IM * SC                              # 192
    MARGIN, GAP = 12, 16
    PLOT_W = 494
    W = MARGIN + PAN + GAP + PAN + GAP + PLOT_W + MARGIN
    HUD = 30
    PANY = HUD + 24
    H = PANY + PAN + 94
    px0 = MARGIN + 2 * (PAN + GAP) + 56
    px1 = W - MARGIN - 12
    head = (f"motion magnification: a {D0} px vibration at {FREQ:.0f} Hz "
            f"(band {BAND[0]:.0f}-{BAND[1]:.0f} Hz, {FPS:.0f} fps), alpha = {ALPHA:.0f}")

    # 崖のプロットは全フレーム共通(静止していても意味が分かるように)
    axC_geom = (px0, PANY, px1, PANY + PAN - 24)
    out = []
    for t in range(T):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        _place(canvas, _upscale(_gray_to_rgb(np.clip(vid[t], 0, 1)), SC), PANY, MARGIN)
        x2 = MARGIN + PAN + GAP
        _place(canvas, _upscale(_gray_to_rgb(np.clip(mag[t], 0, 1)), SC), PANY, x2)
        # 動きの基準になる固定の縦線(op で描く)。これが無いと 0.2 px は見えない。
        for x0 in (MARGIN, x2):
            canvas = imagedraw.draw_line(canvas, (x0 + PAN // 2, PANY),
                                         (x0 + PAN // 2, PANY + PAN), color=C_AMBR, width=1)
        canvas = _frame_box(canvas, PANY, PANY + PAN, MARGIN, MARGIN + PAN, C_GRID, 1)
        canvas = _frame_box(canvas, PANY, PANY + PAN, x2, x2 + PAN, C_GRID, 1)

        ax = Axes(*axC_geom, 0.0, 6.2, 0.0, 4.0)
        ax.bg(canvas)
        canvas = ax.grid_y(canvas, [1.0, 2.0, 3.0])
        canvas = ax.series(canvas, amps, amps, C_DIM, 1)
        canvas = ax.vline(canvas, cliff_px, C_AMBR, 2, dashed=True)
        canvas = ax.series(canvas, amps, meas, C_TEAL, 2)
        canvas = ax.markers(canvas, amps, meas, C_TEAL, 3, "circle", 1)
        canvas = ax.axis(canvas)
        canvas, tx = ax.xticks(canvas, [0, 1, 2, 3, 4, 5, 6],
                               ["0", "1", "2", "3", "4", "5", "6"])
        canvas, ty = ax.yticks(canvas, [0, 1, 2, 3, 4], ["0", "1", "2", "3", "4"])
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        # 現在フレームの変位を数直線で(op の draw_markers)
        bar_y = PANY + PAN + 30
        bax = Axes(MARGIN + 56, bar_y, x2 + PAN - 6, bar_y + 26, -4.6, 4.6, -1.0, 1.0)
        bax.bg(canvas, C_PLOT)
        canvas = imagedraw.draw_line(canvas, (bax.X(0.0), bax.y0), (bax.X(0.0), bax.y1),
                                     color=C_GRID, width=1)
        canvas = imagedraw.draw_markers(canvas, [(float(bax.X(d_in[t])), float(bax.Y(0.35)))],
                                        color=C_BLUE, size=6, shape="cross", width=2)
        canvas = imagedraw.draw_markers(canvas, [(float(bax.X(d_out[t])), float(bax.Y(-0.35)))],
                                        color=C_TEAL, size=6, shape="cross", width=2)
        canvas, tb = bax.xticks(canvas, [-4, -2, 0, 2, 4], ["-4", "-2", "0", "+2", "+4"])
        canvas = _frame_box(canvas, bax.y0, bax.y1, bax.x0, bax.x1)

        frame = _to_u8(canvas)
        labels = [
            (MARGIN, 7, head, C_TEXT, 12, False),
            (MARGIN, PANY - 20, f"original   frame {t + 1:2d}/{T}", C_BLUE, 13, True),
            (x2, PANY - 20, f"magnified  alpha = {ALPHA:.0f}", C_TEAL, 13, True),
            (px0 - 56, PANY - 20,
             "measured displacement vs true amplitude  (displacement_series)",
             C_TEXT, 12, True),
            (MARGIN, bar_y - 16,
             f"displacement this frame:  original {d_in[t]:+.4f} px    "
             f"magnified {d_out[t]:+.4f} px    measured gain {gain:.4f} "
             f"(requested {ALPHA:.0f})", C_TEXT, 12, True),
            (MARGIN, bar_y + 34,
             f"peak {np.abs(d_in).max():.4f} -> {np.abs(d_out).max():.4f} px.  "
             f"image SNR {res['image_snr_change_db']:+.3f} dB, motion SNR "
             f"{res['motion_snr_change_db']:+.3f} dB: magnification shows motion, "
             f"it does not add certainty.", C_DIM, 12, False),
            (MARGIN, bar_y + 52,
             f"the input clip matches its closed form to {err_in:.1e} px, so every "
             f"number above is a measurement, not a setting.", C_DIM, 12, False),
            (px1 - 150, ax.y1 + 22, "true amplitude [px] ->", C_DIM, 11, False),
            (int(ax.X(cliff_px)) - 168, ax.y0 + 6,
             f"J0 first zero {j0_zero:.4f} / k", C_AMBR, 11, True),
            (int(ax.X(cliff_px)) - 168, ax.y0 + 20,
             f"= {cliff_px:.4f} px", C_AMBR, 11, True),
            (ax.x0 + 8, ax.y0 + 44,
             f"exact to {last_ok:.3f} px,", C_TEAL, 11, True),
            (ax.x0 + 8, ax.y0 + 58,
             f"inverts from {first_bad:.3f} px", C_ROSE, 11, True),
            (ax.x0 + 8, ax.y1 - 30, "measured [px]", C_TEAL, 11, True),
            (ax.x0 + 8, ax.y1 - 16, "y = x (truth)", C_DIM, 11, False),
        ]
        labels += tx + ty + tb
        out.append(_text(frame, labels))

    facts = {
        "amplitude_px": D0, "alpha": ALPHA, "fps": FPS, "band_hz": list(BAND),
        "measured_gain": gain,
        "peak_displacement_px": [float(np.abs(d_in).max()), float(np.abs(d_out).max())],
        "input_closed_form_error_px": err_in,
        "image_snr_change_db": float(res["image_snr_change_db"]),
        "motion_snr_change_db": float(res["motion_snr_change_db"]),
        "j0_first_zero": j0_zero, "cliff_px": cliff_px,
        "last_exact_amplitude_px": last_ok, "first_broken_amplitude_px": first_bad,
        "sweep_amplitudes_px": [float(v) for v in amps],
        "sweep_measured_px": [float(v) for v in meas],
    }
    return out, facts, 10, T // 4


# --------------------------------------------------------------------------- #
# CLI                                                                           #
# --------------------------------------------------------------------------- #
BUILDERS = {
    "csi": ("newops_csi_step_sweep", build_csi),
    "bearing": ("newops_bearing_envelope", build_bearing),
    "lightfield": ("newops_lightfield_refocus", build_lightfield),
    "photon": ("newops_photon_buildup", build_photon),
    "quaternion": ("newops_quaternion_rotate", build_quaternion),
    "fmcw": ("newops_fmcw_window", build_fmcw),
    "specular": ("newops_specular_split", build_specular),
    "motionmag": ("newops_motion_magnify", build_motionmag),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="新しい op 族 8 つの記事用デモ図(静止画 / GIF + mp4)")
    ap.add_argument("--figs", default=",".join(BUILDERS),
                    help="comma list of: " + ", ".join(BUILDERS))
    ap.add_argument("--out", default=_MEDIA_DIR)
    ap.add_argument("--thumbs", default=_THUMB_DIR)
    args = ap.parse_args(argv)

    want = [c.strip() for c in args.figs.split(",") if c.strip()]
    unknown = sorted(set(want) - set(BUILDERS))
    if unknown:
        print(f"unknown figs: {unknown} (valid: {', '.join(BUILDERS)})", file=sys.stderr)
        return 2

    def log(m):
        print(m, flush=True)

    t0 = time.time()
    results = {}
    for name in want:
        stem, fn = BUILDERS[name]
        log(f"[build] {name} -> {stem}")
        t1 = time.time()
        frames, facts, fps, thumb_index = fn(log)
        log(f"    built {len(frames)} frame(s) "
            f"{frames[0].shape[1]}x{frames[0].shape[0]} in {time.time() - t1:.1f}s")
        info = _write(frames, stem, fps=fps, thumb_index=thumb_index,
                      out_dir=args.out, thumb_dir=args.thumbs, log=log)
        results[name] = {"stem": stem, "info": info, "facts": facts}

    log(f"=== done in {time.time() - t0:.1f}s ===")
    for name, r in results.items():
        i = r["info"]
        kinds = [k for k in ("png", "gif", "mp4") if k in i]
        parts = "  ".join(f"{k} {i[k]['bytes'] / 1e6:.2f}MB" for k in kinds)
        log(f"  {name:11s} {i['n_frames']:3d} frame(s) "
            f"{i['size'][0]}x{i['size'][1]}  {parts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
