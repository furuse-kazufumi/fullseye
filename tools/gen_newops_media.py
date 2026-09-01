# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_newops_media — 新しく足した op 族の「やれることが目で分かる」デモを作る。

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
* すべて**動く図**にしてある(掃引・収束・視点移動・時間発展)。止まって見ても
  分かるよう、軸・単位・凡例は毎フレーム焼き込む。

作る 10 点:

  1. ``newops_csi_step_sweep``      段差を 0.10→1.00 um で掃引。位相シフト法が
     λ/4 で飛び、誤差が λ/2 の整数倍になるのに対しコヒーレンス法が追従する。
  2. ``newops_bearing_envelope``    復調帯域を 400→11800 Hz で掃引。共振を含む
     帯域に来た瞬間だけ、生スペクトルに無い欠陥周波数が包絡線に立つ。
  3. ``newops_lightfield_refocus``  1 枚の光場からスロープ掃引でリフォーカス。
  4. ``newops_lightfield_parallax`` 同じ光場で**視点だけ**を周回させる(視差)。
  5. ``newops_photon_buildup``      1→1000 photon/px。粒が絵になり、誤差棒が √N。
  6. ``newops_quaternion_rotate``   色空間の 3 次元回転 vs 最良の対角近似。
  7. ``newops_fmcw_window``         弱い標的の真の高さを -18→-54 dB で掃引し、
     矩形窓が漏れの床で頭打ちになるのに hann が追従するのを見る。
  8. ``newops_specular_split``      ハイライトを動かしながら鏡面/拡散に分ける。
  9. ``newops_photometric_shadow``  遮蔽灯 k=0→6。k=4 で頑健版も崩れる。
 10. ``newops_motion_magnify``      0.2 px の振動の増幅前後 + J₀ 第一零点の崖。
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

#: 見た目の異常(軸の入れ替わり・符号反転・off-by-one・NaN・フレーム重複)を
#: 見つけたらここに積む。op は直さず、最後にまとめて報告する。
ANOMALIES: list = []


def _flag(where: str, message: str) -> None:
    ANOMALIES.append(f"{where}: {message}")
    print(f"    [ANOMALY] {where}: {message}", flush=True)


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
    c = np.empty((int(h), int(w), 3), np.float64)
    c[:, :] = np.asarray(C_BG)
    return c


def _fill(canvas: np.ndarray, y0, y1, x0, x1, color) -> None:
    """矩形をベタ塗り(op を通すまでもない下地)。"""
    canvas[int(y0):int(y1), int(x0):int(x1), :] = np.asarray(color, np.float64)


def _upscale(a: np.ndarray, k: int) -> np.ndarray:
    """最近傍の整数倍拡大。**補間しない** — 画素の粗さ自体が見せたい情報なので。"""
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def _gray_to_rgb(img: np.ndarray) -> np.ndarray:
    return np.repeat(np.clip(np.asarray(img, np.float64), 0.0, 1.0)[:, :, None], 3, axis=2)


def _check_display(name: str, a: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """表示前の見張り: NaN/inf と、レンジ外に落ちて黒/白に潰れる画素を数える。"""
    a = np.asarray(a, np.float64)
    bad = int((~np.isfinite(a)).sum())
    if bad:
        _flag(name, f"{bad} non-finite pixel(s) would have been displayed silently")
        a = np.nan_to_num(a, nan=lo, posinf=hi, neginf=lo)
    clipped = float(((a < lo) | (a > hi)).mean())
    if clipped > 0.02:
        _flag(name, f"{clipped:.1%} of the pixels fall outside the display range "
                    f"[{lo:g}, {hi:g}] and would saturate")
    return a


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


def _colourbar(canvas, y0, y1, x0, x1, flip=False):
    """縦の色見本(下=0、上=1)。``_cmap`` と同じランプであることを保証する。"""
    n = int(y1 - y0)
    ramp = np.linspace(1.0, 0.0, n) if not flip else np.linspace(0.0, 1.0, n)
    bar = _cmap(np.repeat(ramp[:, None], int(x1 - x0), axis=1))
    canvas[int(y0):int(y1), int(x0):int(x1), :] = bar
    return canvas


def _place(canvas: np.ndarray, img_rgb: np.ndarray, y: int, x: int) -> None:
    h, w = img_rgb.shape[:2]
    canvas[int(y):int(y) + h, int(x):int(x) + w, :] = np.clip(img_rgb, 0.0, 1.0)


def _frame_box(canvas, y0, y1, x0, x1, color=C_GRID, width=1):
    pts = [(x0, y0), (x1 - 1, y0), (x1 - 1, y1 - 1), (x0, y1 - 1)]
    return imagedraw.draw_polyline(canvas, pts, color=color, width=width, closed=True)


def _dashed(canvas, p0, p1, color, width=1, dash=6, gap=5):
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
        # 反転軸(lo > hi)でも効くよう、clip は min/max に直してから当てる。
        # np.clip(v, lo, hi) は lo > hi のとき黙って hi を返すので、全点が
        # 端に貼り付いた図になる(実際にそれで 1 度騙された)。
        v = np.clip(np.asarray(v, np.float64), min(self.xlo, self.xhi),
                    max(self.xlo, self.xhi))
        if self.logx:
            t = (np.log10(v) - np.log10(self.xlo)) / (np.log10(self.xhi) - np.log10(self.xlo))
        else:
            t = (v - self.xlo) / (self.xhi - self.xlo)
        return self.x0 + (self.x1 - self.x0) * t

    def Y(self, v):
        v = np.clip(np.asarray(v, np.float64), min(self.ylo, self.yhi),
                    max(self.ylo, self.yhi))
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

    def band(self, canvas, xa, xb, color):
        _fill(canvas, self.y0, self.y1, int(round(float(self.X(xa)))),
              max(int(round(float(self.X(xa)))) + 1, int(round(float(self.X(xb))))), color)
        return canvas

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

    def xticks(self, canvas, values, labels, color=C_DIM, size=11, dy=6):
        out = []
        for v, s in zip(values, labels):
            xt = float(self.X(v))
            canvas = imagedraw.draw_line(canvas, (xt, self.y1), (xt, self.y1 + 4),
                                         color=color, width=1)
            out.append((xt - 3.2 * len(s), self.y1 + dy, s, color, size, False))
        return canvas, out

    def yticks(self, canvas, values, labels, color=C_DIM, size=11):
        out = []
        for v, s in zip(values, labels):
            yt = float(self.Y(v))
            canvas = imagedraw.draw_line(canvas, (self.x0 - 4, yt), (self.x0, yt),
                                         color=color, width=1)
            out.append((self.x0 - 9 - 6.6 * len(s), yt - 7, s, color, size, False))
        return canvas, out

    def grid_y(self, canvas, values, color=C_GRID):
        for v in values:
            canvas = imagedraw.draw_line(canvas, (self.x0, self.Y(v)), (self.x1, self.Y(v)),
                                         color=color, width=1)
        return canvas


def _legend(x, y, entries, size=12, step=17):
    """凡例 = 色つきの四角 + 文字。``_text`` に渡す項目列を返す。"""
    out = []
    for i, (col, label) in enumerate(entries):
        out.append((x, y + i * step, "\u25a0", col, size, True))
        out.append((x + 15, y + i * step, label, C_TEXT, size, False))
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


def _check_frames(stem: str, frames: Sequence[np.ndarray]) -> None:
    """アニメーションの見張り: 形が揃っているか、連続フレームが重複していないか。"""
    shapes = {f.shape for f in frames}
    if len(shapes) != 1:
        _flag(stem, f"frames have mixed shapes {sorted(shapes)}")
    if len(frames) < 2:
        return
    dup = [i for i in range(1, len(frames))
           if np.array_equal(frames[i], frames[i - 1])]
    if dup:
        _flag(stem, f"{len(dup)} duplicated frame(s) at indices {dup[:8]}"
                    f"{' ...' if len(dup) > 8 else ''} (the animation stalls there)")


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


def _write(frames_u8, stem: str, *, fps: int, thumb_index: int, out_dir: str,
           thumb_dir: str, log: Callable[[str], None]) -> dict:
    """**同一フレーム列**から GIF + mp4(1 枚なら PNG)。どちらも読み戻して照合。"""
    os.makedirs(out_dir, exist_ok=True)
    _check_frames(stem, frames_u8)
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
        if info["gif"]["bytes"] > 3.0e6:
            _flag(stem, f"GIF is {info['gif']['bytes'] / 1e6:.2f} MB (> 3 MB budget)")
    idx = int(np.clip(thumb_index, 0, len(frames_u8) - 1))
    info["thumb"] = _thumb(frames_u8[idx], stem, thumb_dir, log)
    info["thumb"]["frame_index"] = idx
    return info


# =========================================================================== #
# 1) コヒーレンス走査干渉 — 段差の掃引(GIF)                                   #
# =========================================================================== #
def build_csi(log):
    import fringe
    import interferometry as I

    LAM, SIGMA, DZ, NP = 0.60, 1.2, 0.05, 241
    BASE = 5.0
    gain = 4.0 * np.pi / LAM                    # rad/um(往復 = 1 縞が λ/2)
    fine = np.round(np.arange(0.10, 1.0001, 0.01), 6)

    psi, csi = [], []
    for h in fine:
        hh = np.zeros((16, 32))
        hh[:, 16:] = float(h)
        imgs = fringe.synthesize_fringes(hh, n_steps=4, freq=0.0, phase_gain=gain,
                                         bias=0.5, amplitude=0.4)
        rec = fringe.decode_fringe(imgs, k=1.0 / gain)
        psi.append(float(rec[:, 16:].mean() - rec[:, :16].mean()))
        st = I.csi_stack_simulate(hh + BASE, 0.0, DZ, NP, LAM,
                                  envelope_fwhm_um=None, envelope_sigma_um=SIGMA)
        cm = I.csi_height_map(st, DZ, 0.0, LAM, mode="gaussian")
        csi.append(float(cm[:, 16:].mean() - cm[:, :16].mean()))
    psi, csi = np.asarray(psi), np.asarray(csi)

    e_psi, e_csi = psi - fine, csi - fine
    orders = e_psi / (LAM / 2.0)
    frac = float(np.abs(orders - np.round(orders)).max())
    broke = fine[np.abs(e_psi) > 1e-6]
    first_break = float(broke.min()) if broke.size else float("nan")
    last_ok = float(fine[fine < first_break].max())
    csi_max, csi_rms = float(np.abs(e_csi).max()), float(np.sqrt(np.mean(e_csi ** 2)))
    n_orders = int(len(np.unique(np.round(orders).astype(int))))
    des = I.csi_design(wavelength_um=LAM, bandwidth_um=0.10, z_range_um=12.0,
                       width_px=320, height_px=240)
    if abs(des["max_z_step_um"] - LAM / 4.0) > 1e-12:
        _flag("csi", f"Nyquist z-step {des['max_z_step_um']} != lambda/4 {LAM / 4}")

    log(f"  lambda/4 = {LAM / 4:.3f} um, lambda/2 = {LAM / 2:.3f} um")
    log(f"  phase shifting is exact to {last_ok:.2f} um and first breaks at "
        f"{first_break:.2f} um; the error is an integer multiple of lambda/2 to "
        f"{frac:.2e} ({n_orders} distinct fringe orders)")
    log(f"  coherence method: max |error| {csi_max:.3e} um, RMS {csi_rms:.3e} um")

    # z 走査の生信号(段差の両側)— アニメで見せる「測っているもの」そのもの
    z = DZ * np.arange(NP)
    steps = np.round(np.linspace(0.10, 1.00, 28), 6)
    idx = [int(np.argmin(np.abs(fine - s))) for s in steps]

    W = 920
    HUD = 28
    axA = Axes(78, 58, W - 14, 232, 0.10, 1.00, -0.22, 1.06)
    axB = Axes(78, 268, W - 14, 382, 0.10, 1.00, -3.6, 0.6)
    axZ = Axes(78, 436, W - 14, 552, 3.6, 8.8, -0.14, 0.95)
    H = 630

    out = []
    for k, s in enumerate(steps):
        i = idx[k]
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)

        for ax in (axA, axB, axZ):
            ax.bg(canvas)
        # A: 真値の直線・λ/4 の縦線・2 方式の測定値(掃引済みの所まで濃く)
        canvas = axA.grid_y(canvas, [0.0, 0.25, 0.5, 0.75, 1.0])
        canvas = axA.series(canvas, fine, fine, C_DIM, 1)
        canvas = axA.vline(canvas, LAM / 4.0, C_AMBR, 2, dashed=True)
        canvas = axA.series(canvas, fine, csi, (0.07, 0.35, 0.34), 2)
        canvas = axA.series(canvas, fine, psi, (0.16, 0.31, 0.44), 1)
        canvas = axA.series(canvas, fine[:i + 1], csi[:i + 1], C_TEAL, 3)
        canvas = axA.series(canvas, fine[:i + 1], psi[:i + 1], C_BLUE, 2)
        canvas = axA.markers(canvas, [fine[i], fine[i]], [csi[i], psi[i]], C_WHITE, 5, "cross", 2)
        canvas = axA.axis(canvas)
        canvas, tA = axA.xticks(canvas, [0.1, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0],
                                ["0.10", "0.15", "0.30", "0.45", "0.60", "0.75", "0.90", "1.00"])
        canvas, tAy = axA.yticks(canvas, [0.0, 0.25, 0.5, 0.75, 1.0],
                                 ["0.00", "0.25", "0.50", "0.75", "1.00"])
        # B: 位相シフト法の誤差 / (λ/2) = 縞次数(整数の階段)
        canvas = axB.grid_y(canvas, [0.0, -1.0, -2.0, -3.0])
        canvas = axB.series(canvas, fine, orders, (0.16, 0.31, 0.44), 1)
        canvas = axB.series(canvas, fine[:i + 1], orders[:i + 1], C_BLUE, 3)
        canvas = axB.markers(canvas, [fine[i]], [orders[i]], C_WHITE, 5, "cross", 2)
        canvas = axB.vline(canvas, LAM / 4.0, C_AMBR, 2, dashed=True)
        canvas = axB.axis(canvas)
        canvas, tB = axB.xticks(canvas, [0.1, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0],
                                ["0.10", "0.15", "0.30", "0.45", "0.60", "0.75", "0.90", "1.00"])
        canvas, tBy = axB.yticks(canvas, [0.0, -1.0, -2.0, -3.0], ["0", "-1", "-2", "-3"])

        # Z: そのとき実際に取れている 2 本の走査信号と包絡線
        sig_lo = I.csi_signal_simulate(BASE, 0.0, DZ, NP, LAM, envelope_fwhm_um=None,
                                       envelope_sigma_um=SIGMA)
        sig_hi = I.csi_signal_simulate(BASE + float(s), 0.0, DZ, NP, LAM,
                                       envelope_fwhm_um=None, envelope_sigma_um=SIGMA)
        env_lo = I.csi_envelope(sig_lo, remove_bias=True)
        env_hi = I.csi_envelope(sig_hi, remove_bias=True)
        p_lo = I.csi_peak_position(sig_lo, DZ, 0.0, LAM, mode="gaussian")
        p_hi = I.csi_peak_position(sig_hi, DZ, 0.0, LAM, mode="gaussian")
        canvas = axZ.series(canvas, z, sig_lo - 0.5 + 0.32, (0.20, 0.40, 0.55), 1)
        canvas = axZ.series(canvas, z, sig_hi - 0.5 + 0.32, (0.45, 0.32, 0.20), 1)
        canvas = axZ.series(canvas, z, env_lo + 0.32, C_BLUE, 2)
        canvas = axZ.series(canvas, z, env_hi + 0.32, C_AMBR, 2)
        canvas = axZ.vline(canvas, p_lo, C_BLUE, 1, dashed=True)
        canvas = axZ.vline(canvas, p_hi, C_AMBR, 1, dashed=True)
        canvas = axZ.axis(canvas)
        canvas, tZ = axZ.xticks(canvas, [4.0, 5.0, 6.0, 7.0, 8.0],
                                ["4.0", "5.0", "6.0", "7.0", "8.0"])
        for ax in (axA, axB, axZ):
            canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        frame = _to_u8(canvas)
        wrong = abs(psi[i] - fine[i]) > 1e-6
        labels = [
            (14, 6, f"coherence scanning interferometry vs 4-step phase shifting  "
                    f"(lambda {LAM:.2f} um, envelope sigma {SIGMA:.1f} um, "
                    f"{NP} planes x {DZ:.2f} um)", C_TEXT, 12, False),
            (78, 40, "measured step height [um] -- one surface, two methods",
             C_TEXT, 13, True),
            (78, 250, f"phase-shifting error / (lambda/2) = fringe order "
                      f"(integer to {frac:.1e})", C_TEXT, 13, True),
            (78, 418, f"what is actually measured: the z-scan signal on both sides of the "
                      f"step (peaks {p_lo:.4f} and {p_hi:.4f} um)", C_TEXT, 13, True),
            (axA.x1 - 152, axA.y1 + 22, "true step height [um] ->", C_DIM, 11, False),
            (axB.x1 - 152, axB.y1 + 22, "true step height [um] ->", C_DIM, 11, False),
            (axZ.x1 - 148, axZ.y1 - 18, "scan position z [um] ->", C_DIM, 11, False),
            (int(axA.X(LAM / 4.0)) + 6, axA.y1 - 34, f"lambda/4 = {LAM / 4:.2f} um",
             C_AMBR, 11, True),
            (14, H - 52,
             f"true step {s:5.3f} um    coherence {csi[i]:+8.5f} um "
             f"(error {e_csi[i]:+.2e})    phase shifting {psi[i]:+8.5f} um "
             f"(error {e_psi[i]:+.4f} = {orders[i]:+.3f} x lambda/2)",
             (C_ROSE if wrong else C_TEAL), 13, True),
            (14, H - 34,
             ("phase shifting has returned a plausible, finite, WRONG number since "
              f"{first_break:.2f} um -- no exception, no NaN"
              if wrong else
              f"below lambda/4 both agree; phase shifting starts lying at "
              f"{first_break:.2f} um"), C_DIM, 12, False),
            (14, H - 16,
             f"coherence method over the sweep: max |error| {csi_max * 1000:.4f} nm, "
             f"RMS {csi_rms * 1000:.4f} nm over {len(fine)} step heights  |  coherence "
             f"length {des['coherence_length_um']:.3f} um", C_DIM, 11, False),
        ]
        labels += _legend(axA.x1 - 356, axA.y0 + 6, [
            (C_TEAL, "csi_height_map (coherence envelope peak)"),
            (C_BLUE, "decode_fringe (4-step phase shifting)"),
            (C_DIM, "ground truth y = x"),
        ])
        labels += _legend(axZ.x0 + 10, axZ.y0 + 4, [
            (C_BLUE, f"low side, surface {BASE:.2f} um"),
            (C_AMBR, f"high side, surface {BASE + s:.2f} um"),
        ])
        labels += tA + tAy + tB + tBy + tZ
        out.append(_text(frame, labels))

    facts = {
        "wavelength_um": LAM, "lambda_over_4_um": LAM / 4.0, "lambda_over_2_um": LAM / 2.0,
        "n_fine_steps": int(len(fine)), "n_frames": int(len(steps)),
        "psi_first_break_um": first_break, "psi_last_correct_um": last_ok,
        "psi_max_integer_deviation": frac, "psi_distinct_fringe_orders": n_orders,
        "psi_error_range_um": [float(e_psi.min()), float(e_psi.max())],
        "csi_max_abs_error_um": csi_max, "csi_rms_error_um": csi_rms,
        "design": {k: float(v) for k, v in des.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)},
    }
    return out, facts, 6, int(np.argmin(np.abs(steps - 0.5)))


# =========================================================================== #
# 2) 音響・振動診断 — 復調帯域の掃引(GIF)                                     #
# =========================================================================== #
def build_bearing(log):
    import acoustics as A
    import dsp

    FS, FC, FD, M = 25600.0, 3000.0, 107.0, 0.5
    sig = A.synthesize_bearing_signal(FS, 1.0, FC, FD, modulation=M, mode="am")
    freqs, mag = dsp.spectrum(sig, FS)
    amp = mag * 2.0 / sig.size
    df = FS / sig.size
    if abs(df - 1.0) > 1e-9:
        _flag("bearing", f"spectrum resolution {df} Hz is not 1 Hz; the bin indices "
                         f"used for the annotations assume 1 Hz")
    a_def = float(amp[int(round(FD / df))])
    a_car = float(amp[int(round(FC / df))])
    a_lo = float(amp[int(round((FC - FD) / df))])
    a_hi = float(amp[int(round((FC + FD) / df))])

    BW = 2000.0
    centres = np.round(np.linspace(1200.0, 11600.0, 30), 3)
    peaks, amps, envs, bands = [], [], [], []
    for c in centres:
        lo = max(1.0, float(c) - BW / 2.0)
        hi = min(FS / 2.0 - 1.0, float(c) + BW / 2.0)
        e = A.envelope_spectrum(sig, FS, lo, hi)
        bands.append((lo, hi))
        envs.append(e)
        j = int(round(FD / e["resolution_hz"]))
        amps.append(float(e["magnitude"][j]))
        peaks.append(float(e["peak_freq"]))
    amps = np.asarray(amps)
    hit = np.array([abs(p - FD) < 0.5 for p in peaks])
    best = int(np.argmax(amps))

    # 同じ軸受の衝撃型の記録では、共振を知らなくても尖度が帯域を選ぶ
    imp = A.synthesize_bearing_signal(FS, 1.0, FC, FD, mode="impulse", damping=0.05,
                                      noise_sigma=0.05, seed=3)
    sk = A.spectral_kurtosis(imp, FS)
    k_lo = max(1.0, sk["max_freq"] - sk["bin_hz"])
    k_hi = min(FS / 2.0 - 1.0, sk["max_freq"] + sk["bin_hz"])
    env_auto = A.envelope_spectrum(imp, FS, k_lo, k_hi)
    kin = A.bearing_defect_frequencies(1800.0, 9, 8.0, 40.0)

    log(f"  raw spectrum at {FD:.0f} Hz = {a_def:.3e} (carrier {a_car:.6f}, "
        f"sidebands {a_lo:.6f} / {a_hi:.6f} = m/2)")
    log(f"  band sweep {centres[0]:.0f} -> {centres[-1]:.0f} Hz (width {BW:.0f}): the "
        f"{FD:.0f} Hz line is found in {int(hit.sum())} of {len(centres)} bands; best "
        f"amplitude {amps[best]:.6f} at centre {centres[best]:.0f} Hz "
        f"(modulation m = {M})")
    log(f"  spectral kurtosis on the impulsive record picks {k_lo:.0f}-{k_hi:.0f} Hz "
        f"(max {sk['max_kurtosis']:.3f} @ {sk['max_freq']:.0f} Hz) -> envelope peak "
        f"{env_auto['peak_freq']:.4f} Hz")

    W, HUD = 940, 28
    axR = Axes(92, 60, W - 14, 218, 0.0, 12800.0, 1e-17, 3.0, logy=True)
    axE = Axes(92, 264, W - 14, 400, 0.0, 700.0, 0.0, 0.58)
    axP = Axes(92, 452, W - 14, 556, 1000.0, 11800.0, 1e-17, 1.2, logy=True)
    H = 634

    out = []
    for i, c in enumerate(centres):
        lo, hi = bands[i]
        e = envs[i]
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        for ax in (axR, axE, axP):
            ax.bg(canvas)

        canvas = axR.band(canvas, lo, hi, (0.15, 0.19, 0.25))
        canvas = axR.grid_y(canvas, [1e-15, 1e-12, 1e-9, 1e-6, 1e-3, 1.0])
        canvas = axR.series(canvas, freqs, np.maximum(amp, 1e-17), C_BLUE, 1)
        canvas = axR.vline(canvas, FD, C_AMBR, 1, dashed=True)
        canvas = axR.markers(canvas, [FD], [max(a_def, 1e-17)], C_ROSE, 7, "cross", 2)
        canvas = axR.axis(canvas)
        canvas, tR = axR.xticks(canvas, [0, 2000, 3000, 4000, 6000, 8000, 10000, 12800],
                                ["0", "2000", "3000", "4000", "6000", "8000", "10000", "12800"])
        canvas, tRy = axR.yticks(canvas, [1e-15, 1e-12, 1e-9, 1e-6, 1e-3, 1.0],
                                 ["1e-15", "1e-12", "1e-9", "1e-6", "1e-3", "1"])

        sel = e["freqs"] <= 700.0
        canvas = axE.grid_y(canvas, [0.1, 0.2, 0.3, 0.4, 0.5])
        canvas = axE.series(canvas, e["freqs"][sel], e["magnitude"][sel], C_TEAL, 2)
        canvas = axE.vline(canvas, FD, C_AMBR, 1, dashed=True)
        canvas = axE.markers(canvas, [FD], [amps[i]], C_WHITE, 6, "cross", 2)
        canvas = axE.axis(canvas)
        canvas, tE = axE.xticks(canvas, [0, 107, 214, 321, 428, 535, 700],
                                ["0", "107", "214", "321", "428", "535", "700"])
        canvas, tEy = axE.yticks(canvas, [0.0, 0.25, 0.5], ["0.00", "0.25", "0.50"])

        canvas = axP.grid_y(canvas, [1e-15, 1e-10, 1e-5, 1.0])
        canvas = axP.hline(canvas, M, C_AMBR, 1, dashed=True)
        canvas = axP.series(canvas, centres[:i + 1], np.maximum(amps[:i + 1], 1e-17),
                            C_TEAL, 2)
        canvas = axP.markers(canvas, [c], [max(amps[i], 1e-17)], C_WHITE, 5, "cross", 2)
        canvas = axP.axis(canvas)
        canvas, tP = axP.xticks(canvas, [2000, 4000, 6000, 8000, 10000],
                                ["2000", "4000", "6000", "8000", "10000"])
        canvas, tPy = axP.yticks(canvas, [1e-15, 1e-10, 1e-5, 1.0],
                                 ["1e-15", "1e-10", "1e-5", "1"])
        for ax in (axR, axE, axP):
            canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        frame = _to_u8(canvas)
        found = hit[i]
        labels = [
            (14, 6, f"bearing: a {FC:.0f} Hz resonance amplitude-modulated at the "
                    f"{FD:.0f} Hz defect rate (m = {M}), {FS / 1000:.1f} kHz x 1.0 s   "
                    f"-- sweeping the demodulation band", C_TEXT, 12, False),
            (92, 42, "1  raw spectrum (dsp.spectrum), log amplitude -- shaded = the "
                     "band being demodulated", C_TEXT, 13, True),
            (92, 246, "2  envelope spectrum of that band (acoustics.envelope_spectrum), "
                      "linear amplitude", C_TEXT, 13, True),
            (92, 434, f"3  amplitude found at {FD:.0f} Hz vs where the band sits",
             C_TEXT, 13, True),
            (axR.x1 - 128, axR.y1 + 22, "frequency [Hz] ->", C_DIM, 11, False),
            (axE.x1 - 128, axE.y1 + 22, "frequency [Hz] ->", C_DIM, 11, False),
            (axP.x1 - 168, axP.y1 - 20, "demodulation band centre [Hz] ->", C_DIM, 11, False),
            (int(axR.X(FD)) + 8, axR.y0 + 4,
             f"{FD:.0f} Hz: {a_def:.1e}", C_ROSE, 11, True),
            (int(axR.X(FD)) + 8, axR.y0 + 18,
             "not a component", C_ROSE, 11, True),
            (axR.x1 - 386, axR.y0 + 4,
             f"carrier {a_car:.4f}   sidebands {a_lo:.4f} / {a_hi:.4f} = m/2",
             C_BLUE, 11, True),
            (14, H - 56,
             f"band {lo:6.0f} - {hi:6.0f} Hz    peak {e['peak_freq']:8.3f} Hz    "
             f"amplitude at {FD:.0f} Hz = {amps[i]:.6f}    prominence "
             f"{e['peak_prominence']:8.1f}    band fraction {e['band_fraction']:.4f}",
             (C_TEAL if found else C_DIM), 13, True),
            (14, H - 38,
             (f"the {FD:.0f} Hz line is there -- amplitude {amps[i]:.4f} against "
              f"{a_def:.1e} in the raw spectrum ({amps[i] / max(a_def, 1e-300):.1e} x)"
              if found else
              f"nothing at {FD:.0f} Hz: this band carries only "
              f"{e['band_fraction']:.1e} of the record. The band IS the analysis."),
             (C_TEAL if found else C_ROSE), 12, True),
            (14, H - 20,
             f"choosing it without knowing the resonance: spectral_kurtosis on the "
             f"impulsive record of the same bearing picks {k_lo:.0f}-{k_hi:.0f} Hz "
             f"(max {sk['max_kurtosis']:.3f} @ {sk['max_freq']:.0f} Hz) -> envelope peak "
             f"{env_auto['peak_freq']:.4f} Hz", C_DIM, 11, False),
        ]
        labels += tR + tRy + tE + tEy + tP + tPy
        out.append(_text(frame, labels))

    facts = {
        "rate_hz": FS, "carrier_hz": FC, "defect_hz": FD, "modulation": M,
        "raw_amplitude_at_defect": a_def, "raw_amplitude_carrier": a_car,
        "raw_amplitude_sidebands": [a_lo, a_hi],
        "band_width_hz": BW, "band_centres_hz": [float(v) for v in centres],
        "amplitude_at_defect_per_band": [float(v) for v in amps],
        "bands_that_found_the_defect": int(hit.sum()),
        "best_band_centre_hz": float(centres[best]),
        "best_amplitude": float(amps[best]),
        "kurtosis_max": float(sk["max_kurtosis"]),
        "kurtosis_max_freq_hz": float(sk["max_freq"]),
        "kurtosis_band_hz": [float(k_lo), float(k_hi)],
        "kurtosis_auto_envelope_peak_hz": float(env_auto["peak_freq"]),
        "bearing_kinematics_hz": {k: float(v) for k, v in kin.items()
                                  if isinstance(v, (int, float))},
    }
    return out, facts, 5, best


# =========================================================================== #
# 3/4) ライトフィールド — リフォーカスと視差                                    #
# =========================================================================== #
_LF_CACHE: dict = {}


def _lightfield():
    if "lf" not in _LF_CACHE:
        import lightfield as L
        ANG, SIZE, NEAR, FAR = 9, 112, 3.0, 0.0
        lf, truth = L.lf_synthesize((NEAR, FAR), (ANG, ANG), (SIZE, SIZE),
                                    occlusion=True, coverage=0.40, texture_sigma=2.0,
                                    edge="wrap", seed=5)
        _LF_CACHE["lf"] = (lf, truth, ANG, SIZE, NEAR, FAR)
    return _LF_CACHE["lf"]


def _shift_of(a: np.ndarray, b: np.ndarray, limit: int) -> tuple:
    """``b`` を ``a`` に重ねる整数シフト ``(dy, dx)`` を FFT 相互相関で測る。

    規約は runtime に自己検定してある(``_shift_selftest``)。
    """
    A = np.fft.fft2(a - a.mean())
    B = np.fft.fft2(b - b.mean())
    cc = np.real(np.fft.ifft2(A * np.conj(B)))
    n, m = cc.shape
    k = np.arange(-limit, limit + 1)
    sub = cc[np.ix_(k % n, k % m)]
    p = np.unravel_index(int(np.argmax(sub)), sub.shape)
    # ifft(A conj(B)) のピークは -shift に立つ(b = roll(a, s) のとき n = -s)。
    # 符号は _shift_selftest が np.roll で毎回確かめる。
    return -int(k[p[0]]), -int(k[p[1]])


def _shift_selftest() -> bool:
    """既知の ``np.roll`` で符号・軸の規約を確かめる(取り違え検出)。"""
    rng = np.random.default_rng(0)
    a = rng.random((64, 64))
    for dy, dx in ((3, -5), (-2, 7)):
        b = np.roll(a, (dy, dx), axis=(0, 1))
        got = _shift_of(a, b, 12)
        if got != (dy, dx):
            _flag("_shift_of", f"roll({dy},{dx}) measured as {got} -- the "
                               f"cross-correlation convention is not (dy, dx)")
            return False
    return True


def build_lightfield(log, frames: int = 26):
    import lightfield as L

    lf, truth, ANG, SIZE, NEAR, FAR = _lightfield()
    near_mask = truth > (NEAR + FAR) / 2.0
    far_mask = ~near_mask
    st = L.lf_stats(lf)
    LO, HI = float(lf.min()), float(lf.max())
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
    s_near, s_far = np.asarray(s_near), np.asarray(s_far)
    peak_near = float(slopes[int(s_near.argmax())])
    peak_far = float(slopes[int(s_far.argmax())])
    smax = float(max(s_near.max(), s_far.max()))
    if abs(peak_near - NEAR) > (slopes[0] - slopes[1]) * 1.01:
        _flag("lightfield", f"front-layer sharpness peaks at slope {peak_near}, not at "
                            f"the synthesised {NEAR} -- possible sign/axis mix-up")
    if abs(peak_far - FAR) > (slopes[0] - slopes[1]) * 1.01:
        _flag("lightfield", f"back-layer sharpness peaks at slope {peak_far}, not at "
                            f"the synthesised {FAR}")

    centre = L.lf_center_view(lf)
    c_near, c_far = _sharp(centre, near_mask), _sharp(centre, far_mask)
    log(f"  light field {lf.shape}; the front layer covers {near_mask.mean():.0%}")
    log(f"  sharpness peaks: front at slope {peak_near:+.2f} (synthesised {NEAR:+.1f}), "
        f"back at {peak_far:+.2f} (synthesised {FAR:+.1f})")
    log(f"  front-layer sharpness across the sweep {s_near.min():.5f} .. "
        f"{s_near.max():.5f} ({s_near.max() / max(s_near.min(), 1e-12):.1f}x)")

    SC, MARGIN, GAP = 2, 12, 16
    PAN = SIZE * SC
    PLOT_W = 604
    W = MARGIN + PAN + GAP + PLOT_W + MARGIN
    HUD = 28
    PANY = HUD + 22
    H = PANY + PAN + 68
    px0, px1 = MARGIN + PAN + GAP + 72, W - MARGIN - 12
    head = (f"one light field, {ANG}x{ANG} views of {SIZE}x{SIZE} px "
            f"(lf_refocus): slope {NEAR:+.1f} in front over "
            f"{near_mask.mean():.0%} of the frame, slope {FAR:+.1f} behind")

    out = []
    for i, s in enumerate(slopes):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        shown = _check_display("lightfield refocus", imgs[i], LO, HI)
        _place(canvas, _upscale(_gray_to_rgb(_norm01(shown, LO, HI)), SC), PANY, MARGIN)
        canvas = _frame_box(canvas, PANY, PANY + PAN, MARGIN, MARGIN + PAN)

        ax = Axes(px0, PANY, px1, PANY + PAN - 26, -0.6, 3.6, 0.0, smax * 1.12)
        ax.bg(canvas)
        canvas = ax.grid_y(canvas, [smax * 0.25, smax * 0.5, smax * 0.75, smax])
        canvas = ax.vline(canvas, NEAR, C_AMBR, 1, dashed=True)
        canvas = ax.vline(canvas, FAR, C_AMBR, 1, dashed=True)
        canvas = ax.series(canvas, slopes[:i + 1], s_near[:i + 1], C_TEAL, 2)
        canvas = ax.series(canvas, slopes[:i + 1], s_far[:i + 1], C_VIOL, 2)
        canvas = ax.markers(canvas, [s, s], [s_near[i], s_far[i]], C_WHITE, 5, "cross", 2)
        canvas = ax.vline(canvas, float(s), C_WHITE, 1)
        canvas = ax.axis(canvas)
        canvas, tx = ax.xticks(canvas, [-0.5, 0.0, 1.0, 2.0, 3.0, 3.5],
                               ["-0.5", "0.0", "1.0", "2.0", "3.0", "3.5"])
        canvas, ty = ax.yticks(canvas, [0.0, smax * 0.5, smax],
                               ["0.000", f"{smax * 0.5:.3f}", f"{smax:.3f}"])
        tx = tx + ty
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        focus = "front layer" if abs(s - NEAR) < abs(s - FAR) else "back layer"
        labels = [
            (MARGIN, 6, head, C_TEXT, 12, False),
            (MARGIN, PANY - 18, f"refocused at slope {s:+.2f} px/view", C_TEXT, 13, True),
            (px0 - 60, PANY - 18, "gradient sharpness measured inside each layer",
             C_TEXT, 13, True),
            (MARGIN + 4, PANY + PAN + 6,
             f"sharpness  front {s_near[i]:.5f}   back {s_far[i]:.5f}   -> in focus: "
             f"{focus}", C_TEXT, 13, True),
            (MARGIN + 4, PANY + PAN + 26,
             f"sweep peaks at {peak_near:+.2f} (front, synthesised {NEAR:+.1f}) and "
             f"{peak_far:+.2f} (back, synthesised {FAR:+.1f});  {st['n_views']} views",
             C_DIM, 12, False),
            (MARGIN + 4, PANY + PAN + 44,
             f"a single photograph cannot do this: the centre view is stuck at "
             f"front {c_near:.5f} / back {c_far:.5f} at the same time", C_DIM, 12, False),
            (px1 - 152, ax.y1 + 22, "refocus slope [px/view]", C_DIM, 11, False),
            (int(ax.X(NEAR)) + 5, ax.y0 + 4, f"front {NEAR:+.1f}", C_AMBR, 11, True),
            (int(ax.X(FAR)) + 5, ax.y0 + 4, f"back {FAR:+.1f}", C_AMBR, 11, True),
        ]
        labels += _legend(px0 + 10, ax.y0 + 24, [
            (C_TEAL, "front layer (slope +3.0)"),
            (C_VIOL, "back layer  (slope  0.0)")])
        labels += tx
        out.append(_text(_to_u8(canvas), labels))

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
    return out, facts, 7, int(np.argmin(np.abs(slopes - NEAR)))


def build_parallax(log):
    """視点だけを動かす — 光場の角度方向。手前の層が奥より大きく動く。"""
    lf, truth, ANG, SIZE, NEAR, FAR = _lightfield()
    near_mask = truth > (NEAR + FAR) / 2.0
    ok = _shift_selftest()
    LO, HI = float(lf.min()), float(lf.max())
    c = (ANG - 1) // 2

    # 9x9 の外周を 1 周(重複フレームが出ない道順)
    ring = ([(0, u) for u in range(ANG)] + [(v, ANG - 1) for v in range(1, ANG)]
            + [(ANG - 1, u) for u in range(ANG - 2, -1, -1)]
            + [(v, 0) for v in range(ANG - 2, 0, -1)])
    centre = lf[c, c]
    rows = []
    for v, u in ring:
        view = lf[v, u]
        # 参照側だけを手前の層で切り出す(両側に同じ静止マスクを掛けると、
        # マスクどうしの相関が必ず (0,0) で勝ってしまい視差が消える)。
        dy, dx = _shift_of(centre * near_mask, view, 14)
        rows.append({"v": v, "u": u, "expect": (NEAR * (v - c), NEAR * (u - c)),
                     "measured": (dy, dx)})
    err = max(max(abs(r["measured"][0] - r["expect"][0]),
                  abs(r["measured"][1] - r["expect"][1])) for r in rows)
    if ok and err > 0.51:
        _flag("lightfield parallax",
              f"measured view shift disagrees with the closed form by up to {err:.2f} px "
              f"(expected s*(v-vc), s*(u-uc) with s={NEAR})")
    log(f"  orbiting {len(ring)} distinct sub-aperture views around the {ANG}x{ANG} array")
    log(f"  measured front-layer parallax matches s*(v-vc, u-uc) to {err:.2f} px "
        f"(max over the orbit)")

    SC, MARGIN, GAP = 2, 12, 16
    PAN = SIZE * SC
    GRID = 176
    PLOT = 300
    W = MARGIN + PAN + GAP + GRID + GAP + PLOT + MARGIN
    HUD = 28
    PANY = HUD + 22
    H = PANY + PAN + 86
    gx = MARGIN + PAN + GAP
    px = gx + GRID + GAP

    out = []
    for i, r in enumerate(rows):
        v, u = r["v"], r["u"]
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        view = _check_display("lightfield view", lf[v, u], LO, HI)
        _place(canvas, _upscale(_gray_to_rgb(_norm01(view, LO, HI)), SC), PANY, MARGIN)
        # 固定の十字 — これが無いと「視点が動いた」ことが 1 コマでは分からない
        canvas = imagedraw.draw_line(canvas, (MARGIN + PAN // 2, PANY),
                                     (MARGIN + PAN // 2, PANY + PAN), color=C_AMBR, width=1)
        canvas = imagedraw.draw_line(canvas, (MARGIN, PANY + PAN // 2),
                                     (MARGIN + PAN, PANY + PAN // 2), color=C_AMBR, width=1)
        canvas = _frame_box(canvas, PANY, PANY + PAN, MARGIN, MARGIN + PAN)

        # 視点格子(どの (v,u) を見ているか)
        _fill(canvas, PANY, PANY + GRID, gx, gx + GRID, C_PLOT)
        cell = GRID / ANG
        pts = [(gx + (uu + 0.5) * cell, PANY + (vv + 0.5) * cell)
               for vv in range(ANG) for uu in range(ANG)]
        canvas = imagedraw.draw_markers(canvas, pts, color=C_GRID, size=3,
                                        shape="square", width=1)
        path = [(gx + (rr["u"] + 0.5) * cell, PANY + (rr["v"] + 0.5) * cell)
                for rr in rows[:i + 1]]
        if len(path) >= 2:
            canvas = imagedraw.draw_polyline(canvas, path, color=C_VIOL, width=2)
        canvas = imagedraw.draw_markers(
            canvas, [(gx + (c + 0.5) * cell, PANY + (c + 0.5) * cell)],
            color=C_DIM, size=5, shape="cross", width=1)
        canvas = imagedraw.draw_markers(
            canvas, [(gx + (u + 0.5) * cell, PANY + (v + 0.5) * cell)],
            color=C_AMBR, size=7, shape="cross", width=2)
        canvas = _frame_box(canvas, PANY, PANY + GRID, gx, gx + GRID)

        # 実測シフト vs 閉形式
        # 縦軸は下向きが正(画像座標と同じ向き)。上向き正にすると、絵が下へ
        # 動いているのに点が上へ行く = 軸の反転になって読み手を騙す。
        ax = Axes(px + 40, PANY, px + PLOT, PANY + 196, -14, 14, 14, -14)
        ax.bg(canvas)
        canvas = ax.grid_y(canvas, [-12, -6, 0, 6, 12])
        canvas = imagedraw.draw_line(canvas, (ax.X(0), ax.y0), (ax.X(0), ax.y1),
                                     color=C_GRID, width=1)
        exp_pts = [(float(ax.X(rr["expect"][1])), float(ax.Y(rr["expect"][0])))
                   for rr in rows]
        canvas = imagedraw.draw_polyline(canvas, exp_pts, color=(0.30, 0.32, 0.36),
                                         width=1, closed=True)
        mea = [(float(ax.X(rr["measured"][1])), float(ax.Y(rr["measured"][0])))
               for rr in rows[:i + 1]]
        canvas = imagedraw.draw_markers(canvas, mea, color=C_TEAL, size=3,
                                        shape="square", width=1)
        canvas = imagedraw.draw_markers(
            canvas, [(float(ax.X(r["measured"][1])), float(ax.Y(r["measured"][0])))],
            color=C_WHITE, size=6, shape="cross", width=2)
        canvas = ax.axis(canvas)
        canvas, tx = ax.xticks(canvas, [-12, 0, 12], ["-12", "0", "+12"])
        canvas, ty = ax.yticks(canvas, [-12, 0, 12], ["-12", "0", "+12"])
        canvas = imagedraw.draw_line(canvas, (ax.x0, ax.Y(0)), (ax.x1, ax.Y(0)),
                                     color=C_GRID, width=1)
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        labels = [
            (MARGIN, 6, f"the same light field, moving only the viewpoint: "
                        f"sub-aperture view (v, u) of {ANG}x{ANG}", C_TEXT, 12, False),
            (MARGIN, PANY - 18, f"view (v, u) = ({v}, {u})", C_TEXT, 13, True),
            (gx, PANY - 18, "which view", C_TEXT, 13, True),
            (px + 28, PANY - 18, "front-layer shift [px]", C_TEXT, 13, True),
            (gx, PANY + GRID + 10, f"orbit step {i + 1:2d} / {len(rows)}", C_DIM, 12, False),
            (gx, PANY + GRID + 28, f"centre view ({c}, {c})", C_DIM, 12, False),
            (MARGIN, PANY + PAN + 6,
             f"front layer moves by (dy, dx) = ({r['measured'][0]:+d}, "
             f"{r['measured'][1]:+d}) px, closed form s*(v-vc, u-uc) = "
             f"({r['expect'][0]:+.0f}, {r['expect'][1]:+.0f}) px", C_TEAL, 13, True),
            (MARGIN, PANY + PAN + 26,
             f"the back layer (slope {FAR:+.1f}) does not move at all -- that "
             f"difference is the parallax", C_DIM, 12, False),
            (MARGIN, PANY + PAN + 44,
             f"over the orbit it matches the closed form to {err:.2f} px "
             f"(FFT correlation, sign self-tested on np.roll)", C_DIM, 12, False),
            (MARGIN, PANY + PAN + 62,
             "one exposure holds all 81 of these views; an ordinary camera keeps one.",
             C_DIM, 12, False),
            (ax.x1 - 92, ax.y1 + 22, "dx ->   dy down +", C_DIM, 11, False),
        ]
        labels += tx + ty
        out.append(_text(_to_u8(canvas), labels))

    facts = {
        "views": [ANG, ANG], "orbit_length": len(rows), "slope_front": NEAR,
        "max_parallax_error_px": float(err),
        "shift_convention_selftest_passed": bool(ok),
        "orbit": [{"v": r["v"], "u": r["u"], "expect": list(map(float, r["expect"])),
                   "measured": list(r["measured"])} for r in rows],
    }
    return out, facts, 8, 0


# =========================================================================== #
# 5) 光子計数 — 1 → 1000 photon/px                                             #
# =========================================================================== #
def _photon_scene(n: int = 128):
    """決定的な合成シーン: 上が絵(円と縞)、下が 5 段のステップウェッジ。"""
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    img = np.full((n, n), 0.10)
    img += 0.55 * np.exp(-(((x - 0.34 * n) ** 2 + (y - 0.32 * n) ** 2) / (2 * (0.15 * n) ** 2)))
    ring = np.hypot(x - 0.70 * n, y - 0.34 * n)
    img[(ring > 0.15 * n) & (ring < 0.22 * n)] = 0.85
    inbar = (y > 0.55 * n) & (y < 0.70 * n)
    bars = (np.floor(x / (n / 16.0)).astype(int) % 2 == 0) & inbar
    img[inbar] = 0.15
    img[bars] = 0.95
    levels = (0.10, 0.30, 0.50, 0.75, 1.00)
    wedge = {}
    y0, y1 = int(0.76 * n), int(0.96 * n)
    for k, lv in enumerate(levels):
        xa, xb = int(n * (0.04 + 0.19 * k)), int(n * (0.04 + 0.19 * k + 0.15))
        img[y0:y1, xa:xb] = lv
        wedge[lv] = (slice(y0, y1), slice(xa, xb))
    return np.clip(img, 0.0, 1.0), levels, wedge


def build_photon(log, frames: int = 24):
    import photoncount as P

    scene, levels, wedge = _photon_scene(128)
    ns = np.unique(np.round(np.logspace(0.0, 3.0, int(frames)), 3))
    counts, stats, rel, bars = [], [], [], []
    for n in ns:
        c = P.photon_sample(scene, photons_per_unit=float(n), seed=0)
        counts.append(c)
        stats.append(P.photon_statistics(c))
        sig = P.photon_uncertainty(c)
        if not np.allclose(sig, np.sqrt(c)):
            _flag("photon", "photon_uncertainty is not sqrt(counts)")
        bars.append([(float(c[wedge[lv]].mean()) / n, float(sig[wedge[lv]].mean()) / n)
                     for lv in levels])
        b = wedge[1.00]
        rel.append(float(sig[b].mean() / max(c[b].mean(), 1e-12)))
    rel = np.asarray(rel)
    theory = 1.0 / np.sqrt(ns)
    ratio = np.abs(rel / theory - 1.0)
    dev = float(ratio.max())
    dev_high = float(ratio[ns >= 10.0].max())
    log(f"  photon sweep {ns[0]:.2f} -> {ns[-1]:.1f} photons/unit, {len(ns)} frames")
    log(f"  relative uncertainty on the brightest patch {rel[0]:.4f} -> {rel[-1]:.4f}; "
        f"tracks 1/sqrt(N) to {dev_high:.1%} for N >= 10 photons "
        f"({dev:.1%} worst, at {ns[int(ratio.argmax())]:.2f} photons where "
        f"E[sqrt(X)] != sqrt(E[X]))")

    SC, MARGIN, GAP = 2, 12, 16
    PAN = 128 * SC
    PLOT_W = 620
    W = MARGIN + PAN + GAP + PLOT_W + MARGIN
    HUD = 28
    PANY = HUD + 22
    H = PANY + PAN + 68
    bx0, bx1 = MARGIN + PAN + GAP + 64, W - MARGIN - 12
    head = ("single-photon imaging: the same scene through photon_sample(), "
            "1 -> 1000 photons per unit radiance (Poisson, seed fixed)")

    out = []
    for i, n in enumerate(ns):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        top = max(1.0, float(np.quantile(counts[i], 0.995)))
        _place(canvas, _upscale(_gray_to_rgb(_norm01(counts[i], 0.0, top)), SC),
               PANY, MARGIN)
        canvas = _frame_box(canvas, PANY, PANY + PAN, MARGIN, MARGIN + PAN)

        axB = Axes(bx0, PANY, bx1, PANY + 116, -0.6, 4.6, 0.0, 1.45)
        axB.bg(canvas)
        canvas = axB.grid_y(canvas, [0.25, 0.5, 0.75, 1.0, 1.25])
        for k, lv in enumerate(levels):
            m, e = bars[i][k]
            xk = float(axB.X(k))
            canvas = imagedraw.draw_line(canvas, (xk, axB.Y(m - e)), (xk, axB.Y(m + e)),
                                         color=C_AMBR, width=3)
            for yy in (m - e, m + e):
                canvas = imagedraw.draw_line(canvas, (xk - 7, axB.Y(yy)),
                                             (xk + 7, axB.Y(yy)), color=C_AMBR, width=2)
            canvas = imagedraw.draw_line(canvas, (xk - 12, axB.Y(lv)),
                                         (xk + 12, axB.Y(lv)), color=C_TEAL, width=2)
            canvas = imagedraw.draw_markers(canvas, [(xk, float(axB.Y(m)))],
                                            color=C_WHITE, size=4, shape="cross", width=2)
        canvas = axB.axis(canvas)
        canvas, tB = axB.xticks(canvas, list(range(5)), [f"{lv:.2f}" for lv in levels])
        canvas, tBy = axB.yticks(canvas, [0.0, 0.5, 1.0], ["0.0", "0.5", "1.0"])
        canvas = _frame_box(canvas, axB.y0, axB.y1, axB.x0, axB.x1)

        axU = Axes(bx0, PANY + 148, bx1, PANY + PAN - 12, 0.9, 1100.0, 0.02, 1.4,
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
        labels = [
            (MARGIN, 6, head, C_TEXT, 12, False),
            (MARGIN, PANY - 18, f"{n:7.2f} photons/unit", C_TEXT, 13, True),
            (bx0 - 64, PANY - 18,
             "estimated radiance +/- photon_uncertainty / N   (5 step-wedge patches)",
             C_TEXT, 12, True),
            (bx0 - 64, PANY + 132,
             "relative uncertainty of the brightest patch vs photon count",
             C_TEXT, 12, True),
            (MARGIN + 4, PANY + PAN + 6,
             f"{counts[i].sum():9.0f} photons in the frame   empty pixels "
             f"{st['zero_fraction']:5.1%}   mean {st['mean']:8.3f}   variance "
             f"{st['variance']:9.3f}   Fano {st['fano_factor']:.4f} (Poisson = 1)",
             C_TEXT, 13, True),
            (MARGIN + 4, PANY + PAN + 26,
             f"SNR measured {st['snr_measured']:7.3f}   sqrt(N) {st['snr_poisson']:7.3f}"
             f"   error bar {rel[i] * 100:6.2f} %  (1/sqrt(N) = {theory[i] * 100:6.2f} %)",
             C_AMBR, 13, True),
            (MARGIN + 4, PANY + PAN + 44,
             f"the noise is not a setting here, it is sqrt(N): from 10 photons up the "
             f"measured bar tracks 1/sqrt(N) to {dev_high:.1%}; below that the rule "
             f"itself weakens ({dev:.1%} at {ns[0]:.0f} photon/px)", C_DIM, 12, False),
            (bx1 - 120, axU.y1 + 22, "photons per unit ->", C_DIM, 11, False),
        ]
        labels += _legend(bx0 + 10, axB.y0 + 4,
                          [(C_TEAL, "true radiance"), (C_AMBR, "measurement +/- 1 sigma")])
        labels += _legend(bx0 + 10, axU.y0 + 4, [(C_AMBR, "measured"), (C_DIM, "1/sqrt(N)")])
        labels += tB + tBy + tU + tUy
        out.append(_text(_to_u8(canvas), labels))

    facts = {
        "photons_per_unit": [float(v) for v in ns],
        "relative_uncertainty_first_last": [float(rel[0]), float(rel[-1])],
        "sqrt_n_max_deviation": dev, "sqrt_n_max_deviation_above_10": dev_high,
        "fano_first_last": [float(stats[0]["fano_factor"]), float(stats[-1]["fano_factor"])],
        "snr_first_last": [float(stats[0]["snr_measured"]), float(stats[-1]["snr_measured"])],
        "zero_fraction_first_last": [float(stats[0]["zero_fraction"]),
                                     float(stats[-1]["zero_fraction"])],
        "wedge_levels": [float(v) for v in levels],
    }
    return out, facts, 7, len(ns) - 1


# =========================================================================== #
# 6) 四元数画像 — 色空間の 3 次元回転                                           #
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
    for k, chans in enumerate(((v, t, p), (q, v, p), (p, v, t),
                               (p, q, v), (t, p, v), (v, p, q))):
        m = i == k
        rgb[m] = np.stack(chans, -1)[m]
    rgb[r > 1.0] = 0.08
    e = int(0.20 * n)
    rgb[:e, :e] = (1.0, 0.0, 0.0)
    rgb[:e, -e:] = (0.0, 1.0, 0.0)
    rgb[-e:, :e] = (0.0, 0.0, 1.0)
    rgb[-e:, -e:] = (1.0, 1.0, 1.0)
    return rgb


def build_quaternion(log, frames: int = 31):
    import quatimage as qi

    rgb = _colour_scene(112)
    q = qi.rgb_to_quaternion(rgb)
    axis = (0.0, 0.0, 1.0)
    angles = np.round(np.linspace(0.0, 90.0, int(frames)), 6)

    quat_imgs, diag_imgs, maxdiff, opnorm, red_q, red_d = [], [], [], [], [], []
    for a in angles:
        rad = np.radians(float(a))
        rot = qi.quaternion_to_rgb(qi.quat_color_rotate(q, axis, rad))
        c, s = np.cos(rad), np.sin(rad)
        R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        D = np.diag(np.diag(R))
        dia = rgb @ D.T
        quat_imgs.append(rot)
        diag_imgs.append(dia)
        maxdiff.append(float(np.abs(rot - dia).max()))
        opnorm.append(float(np.linalg.norm(R - D, 2)))
        red_q.append(R @ np.array([1.0, 0.0, 0.0]))
        red_d.append(D @ np.array([1.0, 0.0, 0.0]))
    maxdiff, opnorm = np.asarray(maxdiff), np.asarray(opnorm)

    rad90 = np.radians(90.0)
    R90 = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    got90 = qi.quaternion_to_rgb(qi.quat_color_rotate(q, axis, rad90))
    mat_err = float(np.abs(got90 - rgb @ np.array(
        [[np.cos(rad90), -np.sin(rad90), 0.0], [np.sin(rad90), np.cos(rad90), 0.0],
         [0.0, 0.0, 1.0]]).T).max())
    if mat_err > 1e-12:
        _flag("quaternion", f"quat_color_rotate differs from the equivalent 3x3 "
                            f"rotation matrix by {mat_err:.2e} (expected ~1e-16); "
                            f"check the rotation direction convention")
    red_at_90 = qi.quaternion_to_rgb(qi.quat_color_rotate(
        qi.rgb_to_quaternion(np.array([[[1.0, 0.0, 0.0]]])), axis, rad90))[0, 0]
    log(f"  rotation about the blue axis, 0 -> 90 deg in {len(angles)} steps")
    log(f"  pure red at 90 deg -> {np.round(red_at_90, 12).tolist()} (green)")
    log(f"  max |quaternion - best per-channel gain| grows to {maxdiff.max():.4f}; "
        f"||R - diag(R)||_2 to {opnorm.max():.4f}")
    log(f"  vs an explicit 3x3 rotation matrix: {mat_err:.2e} -- the same map "
        f"(quaternions beat per-channel gains, not matrices)")
    _ = R90

    SC, MARGIN, GAP = 2, 12, 16
    PAN = 112 * SC
    PLOT_W = 500
    W = MARGIN + 2 * (PAN + GAP) + PLOT_W + MARGIN
    HUD = 28
    PANY = HUD + 22
    H = PANY + PAN + 120
    px0, px1 = MARGIN + 2 * (PAN + GAP) + 58, W - MARGIN - 12
    head = ("quaternion colour rotation q x q* (quatimage.quat_color_rotate): a 3-D "
            "rotation of the colour vector about the blue axis")

    out = []
    for i, a in enumerate(angles):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        _place(canvas, np.clip(quat_imgs[i], 0, 1), PANY, MARGIN)
        x2 = MARGIN + PAN + GAP
        _place(canvas, np.clip(diag_imgs[i], 0, 1), PANY, x2)
        canvas = _frame_box(canvas, PANY, PANY + PAN, MARGIN, MARGIN + PAN)
        canvas = _frame_box(canvas, PANY, PANY + PAN, x2, x2 + PAN)

        ax = Axes(px0, PANY, px1, PANY + PAN - 30, 0.0, 90.0, 0.0, 1.55)
        ax.bg(canvas)
        canvas = ax.grid_y(canvas, [0.5, 1.0, 1.5])
        canvas = ax.series(canvas, angles[:i + 1], opnorm[:i + 1], C_VIOL, 4)
        canvas = ax.series(canvas, angles[:i + 1], maxdiff[:i + 1], C_AMBR, 2)
        canvas = ax.markers(canvas, [a], [maxdiff[i]], C_WHITE, 5, "cross", 2)
        canvas = ax.axis(canvas)
        canvas, tx = ax.xticks(canvas, [0, 30, 45, 60, 90], ["0", "30", "45", "60", "90"])
        canvas, ty = ax.yticks(canvas, [0.0, 0.5, 1.0, 1.5], ["0.0", "0.5", "1.0", "1.5"])
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        sw_y = PANY + PAN + 46
        for col, sx in ((red_q[i], MARGIN + 96), (red_d[i], x2 + 96)):
            _fill(canvas, sw_y, sw_y + 22, sx, sx + 48, np.clip(col, 0, 1))
            canvas = _frame_box(canvas, sw_y, sw_y + 22, sx, sx + 48)

        labels = [
            (MARGIN, 6, head, C_TEXT, 12, False),
            (MARGIN, PANY - 18, f"quaternion rotation, {a:5.1f} deg", C_TEAL, 13, True),
            (x2, PANY - 18, "per-channel gain (diagonal)", C_ROSE, 13, True),
            (px0 - 58, PANY - 18, "how far apart the two are", C_TEXT, 13, True),
            (MARGIN + 4, PANY + PAN + 8,
             f"red -> ({red_q[i][0]:+.3f}, {red_q[i][1]:+.3f}, {red_q[i][2]:+.3f})",
             C_TEXT, 12, True),
            (x2 + 4, PANY + PAN + 8,
             f"red -> ({red_d[i][0]:+.3f}, {red_d[i][1]:+.3f}, {red_d[i][2]:+.3f})",
             C_TEXT, 12, True),
            (MARGIN + 4, sw_y + 4, "red goes:", C_DIM, 12, False),
            (x2 + 4, sw_y + 4, "red goes:", C_DIM, 12, False),
            (MARGIN + 4, PANY + PAN + 76,
             f"max |difference| over the image {maxdiff[i]:.4f} = ||R - diag(R)||_2 "
             f"{opnorm[i]:.4f} to {abs(maxdiff[i] - opnorm[i]):.0e}", C_AMBR, 12, True),
            (MARGIN + 4, PANY + PAN + 94,
             f"the pure-red patch is the worst case: a per-channel gain can only scale "
             f"the zero already in its green channel.  Written as an explicit 3x3 "
             f"matrix the same rotation differs by {mat_err:.1e} -- quaternions beat "
             f"per-channel gains, not matrices.", C_DIM, 12, False),
            (px1 - 112, ax.y1 + 22, "rotation angle [deg]", C_DIM, 11, False),
        ]
        labels += _legend(px0 + 10, ax.y0 + 4, [
            (C_AMBR, "max |quat - diagonal| (image)"),
            (C_VIOL, "||R - diag(R)||_2 (operator)")])
        labels += tx + ty
        out.append(_text(_to_u8(canvas), labels))

    facts = {
        "axis": list(axis), "angles_deg": [float(v) for v in angles],
        "max_difference_at_90deg": float(maxdiff[-1]),
        "operator_norm_at_90deg": float(opnorm[-1]),
        "red_under_quaternion_at_90deg": [float(v) for v in red_q[-1]],
        "red_under_diagonal_at_90deg": [float(v) for v in red_d[-1]],
        "pure_red_image_at_90deg": [float(v) for v in red_at_90],
        "quaternion_vs_matrix_max_error": mat_err,
    }
    return out, facts, 9, len(angles) - 1


# =========================================================================== #
# 7) FMCW レンジ-ドップラー — 弱い標的の高さを掃引                              #
# =========================================================================== #
def build_fmcw(log, frames: int = 25):
    import rangedoppler as RD

    wave = dict(n_samples=64, n_chirps=32, sample_rate_hz=1.0e7,
                slope_hz_per_s=2.0e13, chirp_period_s=5.0e-5, wavelength_m=3.8934e-3)
    des = RD.fmcw_design(**wave)
    dr, dv = des["range_bin_m"], des["velocity_bin_ms"]
    strong_rb, weak_rb, dop = 10.5, 20, 6
    levels = np.round(np.linspace(-18.0, -54.0, int(frames)), 4)

    maps, profs, meas = [], [], []
    for db in levels:
        cube = RD.fmcw_beat_simulate([strong_rb * dr, weak_rb * dr], [dop * dv, dop * dv],
                                     amplitudes=[1.0, 10.0 ** (db / 20.0)], **wave)
        mm, pp, rr = {}, {}, {}
        for w in ("rect", "hann"):
            m = RD.range_doppler_map(RD.fmcw_window_apply(cube, w, "both"), normalize=True)
            i, j = np.unravel_index(int(np.argmax(m)), m.shape)
            if int(i) - m.shape[0] // 2 != dop:
                _flag("fmcw", f"peak Doppler bin {int(i) - m.shape[0] // 2} != requested "
                              f"{dop} (fftshift convention)")
            row = m[i]
            mm[w] = m
            pp[w] = row
            rr[w] = {"weak_db": float(20.0 * np.log10(row[weak_rb] / row.max())),
                     "peak": float(row.max()), "peak_bin": int(j),
                     "is_local_max": bool(row[weak_rb] > row[weak_rb - 1]
                                          and row[weak_rb] > row[weak_rb + 1])}
        maps.append(mm)
        profs.append(pp)
        meas.append(rr)
    rect_seen = [levels[k] for k in range(len(levels)) if meas[k]["rect"]["is_local_max"]]
    hann_seen = [levels[k] for k in range(len(levels)) if meas[k]["hann"]["is_local_max"]]
    rect_floor = float(np.median([meas[k]["rect"]["weak_db"]
                                  for k in range(len(levels)) if levels[k] < -35.0]))
    log(f"  weak-target sweep {levels[0]:.0f} -> {levels[-1]:.0f} dB")
    log(f"  rect: still a local maximum down to {min(rect_seen):.1f} dB "
        f"({len(rect_seen)}/{len(levels)} levels); below that it flattens onto the "
        f"leakage skirt at about {rect_floor:.1f} dB")
    log(f"  hann: a local maximum at {len(hann_seen)}/{len(levels)} levels, down to "
        f"{min(hann_seen):.1f} dB")

    SC = 6
    MAP_H, MAP_W = 32 * SC, 64 * SC             # 192 x 384
    W, HUD = 940, 28
    MAPY = HUD + 24
    x1p, x2p = 40, 40 + MAP_W + 52
    axP = Axes(100, MAPY + MAP_H + 46, W - 20, MAPY + MAP_H + 206, 0.0, 63.0, -78.0, 2.0)
    axT = Axes(100, axP.y1 + 62, W - 20, axP.y1 + 174, -56.0, -16.0, -60.0, -8.0)
    H = axT.y1 + 74
    DB_LO, DB_HI = -70.0, 0.0

    out = []
    for k, db in enumerate(levels):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        heads = []
        for w, xp in (("rect", x1p), ("hann", x2p)):
            m = maps[k][w]
            dbm = 20.0 * np.log10(np.maximum(m, 1e-12) / m.max())
            _place(canvas, _upscale(_cmap(_norm01(dbm, DB_LO, DB_HI)), SC), MAPY, xp)
            canvas = _frame_box(canvas, MAPY, MAPY + MAP_H, xp, xp + MAP_W)
            cy = MAPY + (dop + 16 + 0.5) * SC
            canvas = imagedraw.draw_circle(canvas, (xp + (strong_rb + 0.5) * SC, cy),
                                           12.0, color=C_WHITE, width=2)
            canvas = imagedraw.draw_circle(canvas, (xp + (weak_rb + 0.5) * SC, cy),
                                           12.0, color=C_AMBR, width=2)
            heads.append((xp + 2, MAPY - 20,
                          f"{w} window   peak {m.max():.4f}", C_TEXT, 13, True))

        axP.bg(canvas)
        canvas = axP.grid_y(canvas, [-60.0, -45.0, -30.0, -15.0, 0.0])
        canvas = axP.hline(canvas, float(db), C_AMBR, 1, dashed=True)
        for w, col in (("rect", C_ROSE), ("hann", C_TEAL)):
            row = profs[k][w]
            canvas = axP.series(canvas, np.arange(len(row)),
                                20.0 * np.log10(np.maximum(row, 1e-12) / row.max()), col, 2)
        canvas = axP.vline(canvas, float(weak_rb), C_AMBR, 1, dashed=True)
        canvas = axP.axis(canvas)
        canvas, tP = axP.xticks(canvas, [0, 10, 20, 30, 40, 50, 60],
                                ["0", "10", "20", "30", "40", "50", "60"])
        canvas, tPy = axP.yticks(canvas, [0, -15, -30, -45, -60],
                                 ["0", "-15", "-30", "-45", "-60"])
        canvas = _frame_box(canvas, axP.y0, axP.y1, axP.x0, axP.x1)

        axT.bg(canvas)
        canvas = axT.grid_y(canvas, [-50, -40, -30, -20, -10])
        canvas = axT.series(canvas, levels, levels, C_DIM, 1)
        for w, col in (("rect", C_ROSE), ("hann", C_TEAL)):
            ys = [meas[j][w]["weak_db"] for j in range(k + 1)]
            canvas = axT.series(canvas, levels[:k + 1], ys, col, 2)
            canvas = axT.markers(canvas, [db], [ys[-1]], C_WHITE, 4, "cross", 2)
        canvas = axT.axis(canvas)
        canvas, tT = axT.xticks(canvas, [-20, -30, -40, -50],
                                ["-20", "-30", "-40", "-50"])
        canvas, tTy = axT.yticks(canvas, [-10, -20, -30, -40, -50],
                                 ["-10", "-20", "-30", "-40", "-50"])
        canvas = _frame_box(canvas, axT.y0, axT.y1, axT.x0, axT.x1)

        r, hn = meas[k]["rect"], meas[k]["hann"]
        labels = [
            (14, 6, f"FMCW range-Doppler: a strong target at range bin {strong_rb} "
                    f"and a weak one at bin {weak_rb}, both at Doppler +{dop}  --  "
                    f"sweeping how weak  (bin {dr:.3f} m / {dv:.3f} m/s)",
             C_TEXT, 12, False),
            (100, axP.y0 - 22,
             f"range profile through Doppler bin +{dop}  [dB relative to the peak]",
             C_TEXT, 13, True),
            (100, axT.y0 - 22,
             "measured height of the weak target vs the height it was given [dB]",
             C_TEXT, 13, True),
            (axP.x1 - 100, axP.y1 + 22, "range bin ->", C_DIM, 11, False),
            (axT.x1 - 212, axT.y1 - 20, "true weak-target level [dB] ->", C_DIM, 11, False),
            (14, H - 56,
             f"weak target given {db:+6.1f} dB    rect reads {r['weak_db']:+7.2f} dB "
             f"({'local max' if r['is_local_max'] else 'NOT a local max'})    "
             f"hann reads {hn['weak_db']:+7.2f} dB "
             f"({'local max' if hn['is_local_max'] else 'NOT a local max'})",
             C_TEXT, 13, True),
            (14, H - 38,
             f"rect error {r['weak_db'] - db:+6.2f} dB, hann error "
             f"{hn['weak_db'] - db:+6.2f} dB.  Unwindowed, the answer stops depending on "
             f"the target once it is below the leakage skirt (about {rect_floor:.1f} dB) "
             f"-- and nothing warns you.", C_ROSE, 12, True),
            (14, H - 20,
             f"the cost of the window: peak height {r['peak']:.4f} -> {hn['peak']:.4f} "
             f"({r['peak'] / hn['peak']:.2f}x) and a wider main lobe.  The rect peak is "
             f"the half-bin scalloping loss 2/pi = {2 / np.pi:.4f}.", C_DIM, 11, False),
            (x1p + 2, MAPY + MAP_H + 6,
             f"colour = dB ({DB_LO:.0f}..{DB_HI:.0f}), rows = Doppler bin -16..+15, "
             f"columns = range bin 0..63;  white circle = strong, amber = weak",
             C_DIM, 11, False),
        ]
        labels += heads
        labels += _legend(axP.x0 + 8, axP.y1 - 44, [(C_ROSE, "rect"), (C_TEAL, "hann")])
        labels += _legend(axT.x0 + 8, axT.y0 + 4,
                          [(C_DIM, "y = x (a truthful reading)")])
        labels += tP + tPy + tT + tTy
        out.append(_text(_to_u8(canvas), labels))

    facts = {
        "range_bin_m": float(dr), "velocity_bin_ms": float(dv),
        "sweep_bandwidth_hz": float(des["sweep_bandwidth_hz"]),
        "strong_range_bin": strong_rb, "weak_range_bin": weak_rb, "doppler_bin": dop,
        "true_levels_db": [float(v) for v in levels],
        "rect_measured_db": [float(m["rect"]["weak_db"]) for m in meas],
        "hann_measured_db": [float(m["hann"]["weak_db"]) for m in meas],
        "rect_local_max_down_to_db": float(min(rect_seen)),
        "hann_local_max_down_to_db": float(min(hann_seen)),
        "rect_leakage_floor_db": rect_floor,
        "half_bin_scalloping_2_over_pi": float(2 / np.pi),
    }
    return out, facts, 6, len(levels) - 1


# =========================================================================== #
# 8/9) 鏡面反射の分離 と 遮蔽下のフォトメトリックステレオ                        #
# =========================================================================== #
def _bump_normals(h=64, w=64, amp=6.0, sigma=14.0):
    """ガウス丘の float64 の単位法線(float32 に丸めると測定の床が上がるため)。"""
    y, x = np.mgrid[0:h, 0:w]
    z = amp * np.exp(-(((x - w / 2.0) ** 2 + (y - h / 2.0) ** 2) / (2.0 * sigma ** 2)))
    zy, zx = np.gradient(z)
    n = np.stack([-zx, -zy, np.ones_like(zx)], axis=-1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def build_specular(log, frames: int = 24):
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

    ts = np.linspace(0.0, 2.0 * np.pi, int(frames), endpoint=False)
    rows = []
    for t in ts:
        cx = 32.0 + 16.0 * np.cos(t)
        cy = 26.0 + 10.0 * np.sin(t)
        peak = 0.45 + 0.30 * (0.5 + 0.5 * np.cos(t))
        m_s = peak * np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / 30.0))
        m_s[m_s < 1e-3] = 0.0
        img = diffuse_true + m_s[..., None] * WHITE_L
        dif, spec = SP.specular_diffuse_split(img)
        coeff = SP.specular_coefficient_map(img)
        rows.append({
            "cx": cx, "cy": cy, "peak": float(m_s.max()), "img": img,
            "dif": dif, "spec": spec, "coeff": coeff,
            "free": float((m_s == 0.0).mean()),
            "e_d": float(np.abs(dif - diffuse_true).max()),
            "e_s": float(np.abs(spec - m_s[..., None] * WHITE_L).max()),
            "e_c": float(np.abs(coeff - m_s).max()),
            "closure": float(np.abs(dif + spec - img).max()),
        })
    worst = {k: max(r[k] for r in rows) for k in ("e_d", "e_s", "e_c", "closure")}
    log(f"  moving highlight, {len(rows)} positions: worst diffuse error "
        f"{worst['e_d']:.2e}, specular {worst['e_s']:.2e}, coefficient map "
        f"{worst['e_c']:.2e}, closure {worst['closure']:.2e}")
    if worst["e_d"] > 1e-12:
        _flag("specular", f"diffuse recovery is only accurate to {worst['e_d']:.2e}; "
                          f"the docstring claims < 1e-14")

    SC, MARGIN, GAP = 3, 12, 16
    PAN = h * SC
    PLOT_W = 260
    W = MARGIN + 3 * (PAN + GAP) + PLOT_W + MARGIN
    HUD = 28
    PANY = HUD + 22
    H = PANY + PAN + 74
    px0 = MARGIN + 3 * (PAN + GAP) + 54
    head = ("dichromatic separation: one glossy image -> diffuse + specular "
            "(specular_diffuse_split); the highlight moves and changes strength")

    out = []
    for i, r in enumerate(rows):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        gain = 1.0 / max(float(r["spec"].max()), 1e-12)
        for k, (title, img) in enumerate((
                ("input (glossy)", np.clip(r["img"], 0, 1)),
                ("diffuse", np.clip(r["dif"], 0, 1)),
                (f"specular (x{gain:.2f})", np.clip(r["spec"] * gain, 0, 1)))):
            xp = MARGIN + k * (PAN + GAP)
            _place(canvas, _upscale(img, SC), PANY, xp)
            canvas = _frame_box(canvas, PANY, PANY + PAN, xp, xp + PAN)

        ax = Axes(px0, PANY, W - MARGIN - 12, PANY + PAN - 26, 0, len(rows) - 1,
                  1e-17, 1e-12, logy=True)
        ax.bg(canvas)
        canvas = ax.grid_y(canvas, [1e-16, 1e-15, 1e-14, 1e-13])
        canvas = ax.series(canvas, range(i + 1),
                           [max(rows[j]["e_d"], 1e-17) for j in range(i + 1)], C_TEAL, 2)
        canvas = ax.series(canvas, range(i + 1),
                           [max(rows[j]["e_s"], 1e-17) for j in range(i + 1)], C_VIOL, 2)
        canvas = ax.axis(canvas)
        canvas, tx = ax.xticks(canvas, [0, len(rows) // 2, len(rows) - 1],
                               ["0", f"{len(rows) // 2}", f"{len(rows) - 1}"])
        canvas, ty = ax.yticks(canvas, [1e-16, 1e-14],
                               ["1e-16", "1e-14"])
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        heads = [(MARGIN + k * (PAN + GAP) + 2, PANY - 18, t, C_TEXT, 13, True)
                 for k, t in enumerate(("input (glossy)", "diffuse",
                                        f"specular (x{gain:.2f} for display)"))]
        labels = [
            (MARGIN, 6, head, C_TEXT, 12, False),
            (px0 - 54, PANY - 18, "max error [linear units]", C_TEXT, 13, True),
            (MARGIN, PANY + PAN + 8,
             f"highlight at ({r['cx']:5.1f}, {r['cy']:5.1f}) px, peak m_s "
             f"{r['peak']:.3f}, {r['free']:.0%} of the pixels carry no specular "
             f"component", C_TEXT, 13, True),
            (MARGIN, PANY + PAN + 28,
             f"diffuse error {r['e_d']:.2e}   specular error {r['e_s']:.2e}   "
             f"coefficient map m_s {r['e_c']:.2e}   diffuse+specular-input "
             f"{r['closure']:.2e}", C_TEAL, 12, True),
            (MARGIN, PANY + PAN + 46,
             f"a projection onto the illuminant colour, not an optimisation -- which "
             f"is why it holds at machine precision as the highlight moves "
             f"(worst {worst['e_d']:.2e})", C_DIM, 12, False),
            (ax.x0 + 6, ax.y1 + 22, "frame ->", C_DIM, 11, False),
        ]
        labels += _legend(ax.x0 + 6, ax.y0 + 4,
                          [(C_TEAL, "diffuse"), (C_VIOL, "specular")])
        labels += heads + tx + ty
        out.append(_text(_to_u8(canvas), labels))

    facts = {
        "n_positions": len(rows),
        "worst_diffuse_error": worst["e_d"], "worst_specular_error": worst["e_s"],
        "worst_coefficient_error": worst["e_c"], "worst_closure": worst["closure"],
        "peak_m_s_range": [min(r["peak"] for r in rows), max(r["peak"] for r in rows)],
    }
    return out, facts, 8, int(0.75 * len(rows))


def build_photometric_shadow(log):
    import photometric as PM
    import specularity as SP

    h = w = 64
    n_lights = 8
    L = np.array([[np.cos(a), np.sin(a), 2.2]
                  for a in np.linspace(0, 2 * np.pi, n_lights, endpoint=False)])
    L = L / np.linalg.norm(L, axis=1, keepdims=True)
    surface = _bump_normals(h, w, amp=4.0)
    alb_map = 0.7 + 0.2 * np.cos(np.linspace(0, 3, h))[:, None] * np.ones((1, w))
    ndl = np.einsum("hwc,nc->nhw", surface, L)
    if ndl.min() <= 0.0:
        _flag("photometric", f"N.L goes negative (min {ndl.min():.4f}): attached "
                             f"shadows would confound the cast-shadow experiment")
    clean = alb_map[None] * ndl
    methods = ("lstsq", "median", "ransac")
    ks = list(range(0, 7))
    curves = {m: [] for m in methods}
    emaps = {m: [] for m in methods}
    inliers = {m: [] for m in methods}
    for k in ks:
        obs = clean.copy()
        if k:
            obs[:k] = 0.0
        for m in methods:
            nrm, _alb, inl = SP.photometric_stereo_robust(obs, L, method=m)
            e = PM.angular_error_deg(nrm, surface)
            curves[m].append(float(e.mean()))
            emaps[m].append(np.asarray(e, np.float64))
            inliers[m].append(float(inl[:k].mean()) if k else 1.0)
    for m in methods:
        curves[m] = np.asarray(curves[m])
    floor = float(PM.angular_error_deg(surface.astype(np.float32), surface).max())
    cliff = next((k for k in ks if curves["ransac"][k] > 1.0), None)
    for m in methods:
        log(f"  {m:7s}: " + "  ".join(f"k={k}:{curves[m][k]:.4f}" for k in ks))
    log(f"  robust methods break at k = {cliff} of {n_lights}; float32 output floor "
        f"{floor:.6f} deg; N.L min {ndl.min():.4f}")

    SC, MARGIN, GAP = 3, 12, 14
    PAN = h * SC                                    # 192
    TILE = 64
    PLOT_W = 292
    W = MARGIN + 3 * (PAN + GAP) + PLOT_W + MARGIN
    HUD = 28
    TILEY = HUD + 22
    MAPY = TILEY + TILE + 34
    H = MAPY + PAN + 92
    ERR_HI = 30.0

    out = []
    for k in ks:
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        obs = clean.copy()
        if k:
            obs[:k] = 0.0
        for n in range(n_lights):
            xt = MARGIN + n * (TILE + 6)
            _place(canvas, _gray_to_rgb(_norm01(obs[n], 0.0, float(clean.max()))),
                   TILEY, xt)
            canvas = _frame_box(canvas, TILEY, TILEY + TILE, xt, xt + TILE,
                                C_ROSE if n < k else C_GRID, 2 if n < k else 1)

        for j, m in enumerate(methods):
            xp = MARGIN + j * (PAN + GAP)
            _place(canvas, _upscale(_cmap(_norm01(emaps[m][k], 0.0, ERR_HI)), SC),
                   MAPY, xp)
            canvas = _frame_box(canvas, MAPY, MAPY + PAN, xp, xp + PAN)

        px0 = MARGIN + 3 * (PAN + GAP) + 56
        ax = Axes(px0, MAPY, W - MARGIN - 30, MAPY + PAN - 26, -0.3, 6.3,
                  5e-5, 200.0, logy=True)
        ax.bg(canvas)
        canvas = ax.grid_y(canvas, [1e-4, 1e-2, 1.0, 100.0])
        canvas = ax.hline(canvas, floor, C_DIM, 1, dashed=True)
        for m, col in (("lstsq", C_ROSE), ("median", C_BLUE), ("ransac", C_TEAL)):
            canvas = ax.series(canvas, ks[:k + 1],
                               np.maximum(curves[m][:k + 1], 5e-5), col, 2)
            canvas = ax.markers(canvas, ks[:k + 1],
                                np.maximum(curves[m][:k + 1], 5e-5), col, 5, "square", 2)
        canvas = ax.axis(canvas)
        canvas, tx = ax.xticks(canvas, ks, [str(v) for v in ks])
        canvas, ty = ax.yticks(canvas, [1e-4, 1e-2, 1.0, 100.0],
                               ["1e-4", "0.01", "1", "100"])
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)
        # 誤差マップの色見本
        cbx = W - MARGIN - 24
        canvas = _colourbar(canvas, MAPY, MAPY + PAN - 26, cbx, cbx + 12)
        canvas = _frame_box(canvas, MAPY, MAPY + PAN - 26, cbx, cbx + 12)

        broke = curves["ransac"][k] > 1.0
        labels = [
            (MARGIN, 6, f"photometric stereo under cast shadows: {n_lights} lights, "
                        f"blocking them one at a time  "
                        f"(specularity.photometric_stereo_robust)", C_TEXT, 12, False),
            (MARGIN, TILEY - 18,
             f"the {n_lights} observations -- {k} blocked (outlined)", C_TEXT, 13, True),
            (MARGIN, MAPY - 20, "normal error map [deg], 0 (dark) .. "
                                f"{ERR_HI:.0f}+ (bright)", C_TEXT, 13, True),
            (px0 - 56, MAPY - 20, "mean normal error [deg]", C_TEXT, 13, True),
            (cbx - 26, MAPY - 2, f"{ERR_HI:.0f}", C_DIM, 11, False),
            (cbx - 26, MAPY + PAN - 40, "0", C_DIM, 11, False),
        ]
        for j, (m, col) in enumerate((("lstsq", C_ROSE), ("median", C_BLUE),
                                      ("ransac", C_TEAL))):
            xp = MARGIN + j * (PAN + GAP)
            labels.append((xp + 2, MAPY + PAN + 6,
                           f"{m}  mean {curves[m][k]:9.4f} deg", col, 12, True))
            labels.append((xp + 2, MAPY + PAN + 24,
                           (f"blocked lights believed: {inliers[m][k]:.0%}"
                            if k else "no lights blocked"), C_DIM, 11, False))
        labels += [
            (MARGIN, MAPY + PAN + 48,
             f"k = {k} of {n_lights} blocked   ->   lstsq {curves['lstsq'][k]:8.4f} deg, "
             f"median {curves['median'][k]:8.4f} deg, ransac {curves['ransac'][k]:8.4f} deg",
             (C_ROSE if broke else C_TEAL), 13, True),
            (MARGIN, MAPY + PAN + 66,
             (f"half the lights are gone: 'shadowed' and 'black surface' are the "
              f"same model and a majority vote cannot choose -- the robust methods "
              f"break here, and that is disclosed rather than hidden."
              if broke else
              f"{curves['ransac'][k]:.4f} deg is the float32 output floor ({floor:.4f} "
              f"deg), not an error. Plain least squares is already "
              f"{curves['lstsq'][k]:.1f} deg wrong." if k else
              f"with every light visible all three agree at the float32 floor "
              f"({floor:.4f} deg). N.L stays positive (min {ndl.min():.4f}), so every "
              f"failure later is the blocked lights and nothing else."),
             C_DIM, 12, False),
            (ax.x1 - 152, ax.y1 + 22, "blocked lights k (of 8) ->", C_DIM, 11, False),
        ]
        labels += _legend(ax.x0 + 6, ax.y0 + 4,
                          [(C_ROSE, "lstsq"), (C_BLUE, "median"), (C_TEAL, "ransac")])
        labels += tx + ty
        out.append(_text(_to_u8(canvas), labels))

    facts = {
        "n_lights": n_lights, "blocked_k": ks,
        "mean_normal_error_deg": {m: [float(v) for v in curves[m]] for m in methods},
        "blocked_light_inlier_rate": {m: [float(v) for v in inliers[m]] for m in methods},
        "float32_floor_deg": floor, "break_at_k": cliff, "min_n_dot_l": float(ndl.min()),
    }
    return out, facts, 1, (cliff if cliff is not None else 0)


# =========================================================================== #
# 10) モーション増幅 — 0.2 px の振動と J0 第一零点の崖                          #
# =========================================================================== #
def build_motionmag(log, frames: int = 32):
    import motionmag as M

    H_IM = W_IM = 96
    T = int(frames)
    FPS, FREQ, BAND = 32.0, 4.0, (3.0, 5.0)
    D0, ALPHA = 0.2, 20.0
    # synthesize_translation の wavelength_px は **画素単位の波長**なので、
    # 空間周波数は画面幅に依らず k = 2*pi/lambda。DFT の何番目のビンに乗るかは
    # 幅に依るので、そこだけ W/lambda で数える(ここを 8 に決め打ちにすると、
    # 幅 64 以外で静かに間違う)。
    WAVELEN = 8.0
    K_X = 2.0 * np.pi / WAVELEN
    CYC_X = int(round(W_IM / WAVELEN))
    if abs(W_IM / WAVELEN - CYC_X) > 1e-9:
        _flag("motionmag", f"width {W_IM} is not a whole number of {WAVELEN} px "
                           f"periods; the DFT read-out bin would be off")

    vid = M.synthesize_translation((H_IM, W_IM), T, D0, FREQ, FPS)
    res = M.motion_magnify(vid, ALPHA, *BAND, FPS)
    mag = res["video"]

    def read_dx(v):
        """motionmag と無関係な経路での変位読み出し: 既知格子ビンの DFT 位相。"""
        spec = np.fft.fft2(v, axes=(1, 2))
        return -np.unwrap(np.angle(spec[:, 0, CYC_X])) / K_X

    d_in, d_out = read_dx(vid), read_dx(mag)
    gain = float(np.abs(d_out).max() / np.abs(d_in).max())
    truth_d = D0 * np.sin(2.0 * np.pi * FREQ * np.arange(T) / FPS)
    err_in = float(np.abs(d_in - truth_d).max())
    if err_in > 1e-11:
        _flag("motionmag", f"the synthesised clip departs from its closed form by "
                           f"{err_in:.2e} px (expected ~1e-15)")
    if abs(gain - ALPHA) / ALPHA > 0.02:
        _flag("motionmag", f"measured magnification {gain:.4f} vs requested {ALPHA}")

    try:
        from scipy.special import jn_zeros
        j0_zero = float(jn_zeros(0, 1)[0])
    except Exception:
        j0_zero = 2.404825557695773
    cliff_px = j0_zero / K_X
    amps = np.round(np.concatenate([np.linspace(0.25, 2.75, 11),
                                    np.linspace(2.90, 3.35, 10),
                                    np.linspace(3.50, 6.00, 6)]), 6)
    meas = np.asarray([
        float(np.abs(M.displacement_series(
            M.synthesize_translation((64, 64), 64, float(a), FREQ, FPS),
            *BAND, FPS)[:, 0]).max()) for a in amps])
    rel = np.abs(meas - amps) / amps
    good, bad = amps[rel < 1e-9], amps[rel >= 1e-9]
    last_ok = float(good.max()) if good.size else float("nan")
    first_bad = float(bad.min()) if bad.size else float("nan")
    if not (last_ok < cliff_px < first_bad):
        _flag("motionmag", f"the measured cliff ({last_ok:.4f} .. {first_bad:.4f} px) "
                           f"does not bracket the J0 first zero {cliff_px:.4f} px")

    log(f"  magnify {D0} px by alpha={ALPHA:.0f}: measured gain {gain:.6f}, peak "
        f"displacement {np.abs(d_in).max():.4f} -> {np.abs(d_out).max():.4f} px")
    log(f"  the input clip matches its closed form to {err_in:.2e} px")
    log(f"  image SNR {res['image_snr_change_db']:+.4f} dB, motion SNR "
        f"{res['motion_snr_change_db']:+.4f} dB (never positive)")
    log(f"  measurement is exact to {last_ok:.4f} px and inverts from {first_bad:.4f} px; "
        f"J0 first zero {j0_zero:.10f} / k = {cliff_px:.4f} px")

    SC, MARGIN, GAP = 2, 12, 16
    PAN = H_IM * SC
    PLOT_W = 494
    W = MARGIN + 2 * (PAN + GAP) + PLOT_W + MARGIN
    HUD = 28
    PANY = HUD + 22
    H = PANY + PAN + 124
    px0, px1 = MARGIN + 2 * (PAN + GAP) + 56, W - MARGIN - 12
    head = (f"motion magnification: a {D0} px vibration at {FREQ:.0f} Hz "
            f"(pass band {BAND[0]:.0f}-{BAND[1]:.0f} Hz, {FPS:.0f} fps), alpha = {ALPHA:.0f}")

    out = []
    for t in range(T):
        canvas = _canvas(H, W)
        _fill(canvas, 0, HUD, 0, W, C_PANEL)
        x2 = MARGIN + PAN + GAP
        for xp, clip in ((MARGIN, vid), (x2, mag)):
            _place(canvas, _upscale(_gray_to_rgb(np.clip(clip[t], 0, 1)), SC), PANY, xp)
            canvas = imagedraw.draw_line(canvas, (xp + PAN // 2, PANY),
                                         (xp + PAN // 2, PANY + PAN), color=C_AMBR, width=1)
            canvas = _frame_box(canvas, PANY, PANY + PAN, xp, xp + PAN)

        ax = Axes(px0, PANY, px1, PANY + PAN - 24, 0.0, 6.2, 0.0, 4.0)
        ax.bg(canvas)
        canvas = ax.grid_y(canvas, [1.0, 2.0, 3.0])
        canvas = ax.series(canvas, amps, amps, C_DIM, 1)
        canvas = ax.vline(canvas, cliff_px, C_AMBR, 2, dashed=True)
        canvas = ax.series(canvas, amps, meas, C_TEAL, 2)
        canvas = ax.markers(canvas, amps, meas, C_TEAL, 3, "square", 1)
        canvas = ax.axis(canvas)
        canvas, tx = ax.xticks(canvas, [0, 1, 2, 3, 4, 5, 6],
                               ["0", "1", "2", "3", "4", "5", "6"])
        canvas, ty = ax.yticks(canvas, [0, 1, 2, 3, 4], ["0", "1", "2", "3", "4"])
        canvas = _frame_box(canvas, ax.y0, ax.y1, ax.x0, ax.x1)

        bar_y = PANY + PAN + 34
        bax = Axes(MARGIN + 54, bar_y, x2 + PAN - 6, bar_y + 26, -4.6, 4.6, -1.0, 1.0)
        bax.bg(canvas, C_PLOT)
        canvas = imagedraw.draw_line(canvas, (bax.X(0.0), bax.y0), (bax.X(0.0), bax.y1),
                                     color=C_GRID, width=1)
        canvas = imagedraw.draw_markers(canvas, [(float(bax.X(d_in[t])), float(bax.Y(0.35)))],
                                        color=C_BLUE, size=6, shape="cross", width=2)
        canvas = imagedraw.draw_markers(canvas, [(float(bax.X(d_out[t])), float(bax.Y(-0.35)))],
                                        color=C_TEAL, size=6, shape="cross", width=2)
        canvas, tb = bax.xticks(canvas, [-4, -2, 0, 2, 4], ["-4", "-2", "0", "+2", "+4"])
        canvas = _frame_box(canvas, bax.y0, bax.y1, bax.x0, bax.x1)

        labels = [
            (MARGIN, 6, head, C_TEXT, 12, False),
            (MARGIN, PANY - 18, f"original   frame {t + 1:2d}/{T}", C_BLUE, 13, True),
            (x2, PANY - 18, f"magnified  alpha = {ALPHA:.0f}", C_TEAL, 13, True),
            (px0 - 56, PANY - 18,
             "measured displacement vs true amplitude (displacement_series)",
             C_TEXT, 12, True),
            (MARGIN, bar_y - 16,
             f"this frame: original {d_in[t]:+.4f} px   magnified {d_out[t]:+.4f} px   "
             f"measured gain {gain:.4f} (requested {ALPHA:.0f})", C_TEXT, 12, True),
            (MARGIN, bar_y + 50,
             f"peak {np.abs(d_in).max():.4f} -> {np.abs(d_out).max():.4f} px.  image SNR "
             f"{res['image_snr_change_db']:+.3f} dB, motion SNR "
             f"{res['motion_snr_change_db']:+.3f} dB: magnification shows motion, it "
             f"does not add certainty.", C_DIM, 12, False),
            (MARGIN, bar_y + 68,
             f"the input clip matches its closed form to {err_in:.1e} px, so every "
             f"number here is a measurement rather than a setting.", C_DIM, 12, False),
            (px1 - 152, ax.y1 + 22, "true amplitude [px] ->", C_DIM, 11, False),
            (int(ax.X(cliff_px)) - 172, ax.y0 + 4,
             f"J0 first zero {j0_zero:.4f} / k", C_AMBR, 11, True),
            (int(ax.X(cliff_px)) - 172, ax.y0 + 18, f"= {cliff_px:.4f} px", C_AMBR, 11, True),
            (ax.x0 + 8, ax.y0 + 44, f"exact to {last_ok:.3f} px,", C_TEAL, 11, True),
            (ax.x0 + 8, ax.y0 + 58, f"inverts from {first_bad:.3f} px", C_ROSE, 11, True),
            (ax.x0 + 8, ax.y1 - 32, "measured [px]", C_TEAL, 11, True),
            (ax.x0 + 8, ax.y1 - 18, "y = x (truth)", C_DIM, 11, False),
        ]
        labels += tx + ty + tb
        out.append(_text(_to_u8(canvas), labels))

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


# =========================================================================== #
# 束ねる展示 — 工程のフリップブックと、族の見本帳                                #
# =========================================================================== #
def build_lightfield_flow(log, out_dir: str, thumb_dir: str) -> dict:
    """生 MLA 画像 → 復号 → リフォーカス → 全焦点 → 深度 を 1 本のコマ送りに。

    ``exhibit_tile.flipbook`` は**寸法が揃っていること**を要求するので、各工程を
    同じ 336x336 の RGB パネルに揃えてから渡す(拡大は最近傍 = 画素の粗さを
    ごまかさない)。
    """
    sys.path.insert(0, _HERE)
    import lightfield as L
    from exhibit_tile import flipbook, markdown_animation, save_animation

    lf, truth, ANG, SIZE, NEAR, FAR = _lightfield()
    P = SIZE * 3                                       # 336
    raw = L.lf_to_mla(lf)
    decoded = L.lf_from_mla(raw, (ANG, ANG))
    exact = bool(np.array_equal(decoded, lf))
    if not exact:
        _flag("lightfield flow", "lf_to_mla -> lf_from_mla is not a bit-exact round trip")
    centre = L.lf_center_view(lf)
    near = L.lf_refocus(lf, NEAR, edge="wrap")
    far = L.lf_refocus(lf, FAR, edge="wrap")
    levels = tuple(np.round(np.linspace(-1.0, 4.0, 21), 6))
    slope_map, _conf = L.lf_depth_from_focus(lf, levels, edge="wrap", subpixel=False)
    aif = L.lf_all_in_focus(lf, slope_map, levels=levels, edge="wrap")

    def _sharp(img):
        gy, gx = np.gradient(np.asarray(img, np.float64))
        return float((gy ** 2 + gx ** 2).mean())

    slices = [_sharp(s) for s in L.lf_focal_stack(lf, levels, edge="wrap")]
    agree = float((np.abs(slope_map - truth) < 1e-9).mean())
    lo, hi = float(lf.min()), float(lf.max())
    BOARD = 660

    def _pad(img):
        """パネルを共通の版面に中央寄せ(flipbook は寸法一致を要求する)。"""
        out = np.zeros((P, BOARD, 3), np.float64)
        x = (BOARD - img.shape[1]) // 2
        out[:, x:x + img.shape[1]] = img
        return out

    panels = [
        _gray_to_rgb(_norm01(raw[:P, :P], lo, hi)),                       # 生 MLA(等倍)
        _upscale(_gray_to_rgb(_norm01(centre, lo, hi)), 3),
        _upscale(_gray_to_rgb(_norm01(near, lo, hi)), 3),
        _upscale(_gray_to_rgb(_norm01(far, lo, hi)), 3),
        _upscale(_gray_to_rgb(_norm01(aif, lo, hi)), 3),
        _upscale(_cmap(_norm01(slope_map, FAR - 0.5, NEAR + 0.5)), 3),
    ]
    for k, pan in enumerate(panels):
        if pan.shape[:2] != (P, P):
            _flag("lightfield flow", f"panel {k} is {pan.shape[:2]}, expected {(P, P)}")
    panels = [_pad(pan) for pan in panels]
    labels = [
        f"MLA 生画像(各点に {ANG}x{ANG} のレンズ像)",
        f"復号 → 中心視点(往復ビット一致 {exact})",
        f"リフォーカス {NEAR:+.1f} = 手前(鮮鋭度 {_sharp(near):.5f})",
        f"リフォーカス {FAR:+.1f} = 奥(鮮鋭度 {_sharp(far):.5f})",
        f"全焦点 {_sharp(aif):.5f} > 最良スライス {max(slices):.5f}",
        f"スロープ地図(真値と {agree:.1%} 一致)",
    ]
    book = flipbook(panels, labels,
                    title="ライトフィールド: 1 回の撮像から深度まで")
    info = save_animation(book, "newops_lightfield_flow")
    log(f"    flipbook newops_lightfield_flow: {info['frames']} frames "
        f"{info['size']}, {info['gif_bytes'] / 1e6:.2f} MB")
    log(f"    round trip bit-exact {exact}; all-in-focus {_sharp(aif):.5f} > best "
        f"slice {max(slices):.5f}; slope map agrees with the truth on {agree:.1%}")
    info["markdown"] = markdown_animation(
        "newops_lightfield_flow", "ライトフィールドの処理の流れ",
        f"1 回の撮像 → 復号 → リフォーカス → 全焦点 → 深度。往復はビット一致、"
        f"全焦点はどの単一スライスより鋭く({_sharp(aif):.5f} > {max(slices):.5f})、"
        f"スロープ地図は真値と {agree:.1%} 一致。使用 op: `lf_synthesize`, `lf_to_mla`, "
        f"`lf_from_mla`, `lf_center_view`, `lf_refocus`, `lf_depth_from_focus`, "
        f"`lf_all_in_focus`。")
    info["facts"] = {"round_trip_bit_exact": exact, "all_in_focus_sharpness": _sharp(aif),
                     "best_single_slice_sharpness": float(max(slices)),
                     "slope_map_agreement": agree, "panel_px": P}
    return info


def _sampler_label(name: str, f: dict) -> str:
    """見本帳のラベル。数字はすべて、その図を作ったときの実測値から引く。"""
    return {
        "csi": lambda: f"干渉計 — 位相法は {f['psi_first_break_um']:.2f} um で飛ぶ",
        "bearing": lambda: f"軸受 — 生 {f['raw_amplitude_at_defect']:.1e} → 包絡線 "
                           f"{f['best_amplitude']:.4f}",
        "lightfield": lambda: f"リフォーカス — 山は "
                              f"{f['sharpness_peak_near_slope']:+.1f} と "
                              f"{f['sharpness_peak_far_slope']:+.1f}",
        "parallax": lambda: f"視差 — 閉形式と {f['max_parallax_error_px']:.2f} px 一致",
        "photon": lambda: f"光子計数 — 誤差棒 {f['relative_uncertainty_first_last'][0]:.1%}"
                          f" → {f['relative_uncertainty_first_last'][1]:.1%}",
        "quaternion": lambda: f"四元数の色回転 — 対角との差 "
                              f"{f['max_difference_at_90deg']:.2f}",
        "fmcw": lambda: f"窓関数 — rect は {f['rect_leakage_floor_db']:.1f} dB で頭打ち",
        "specular": lambda: f"鏡面分離 — 最悪誤差 {f['worst_diffuse_error']:.1e}",
        "shadow": lambda: f"遮蔽下の法線 — k={f['break_at_k']} 灯で崩れる",
        "motionmag": lambda: f"モーション増幅 — "
                             f"{f['first_broken_amplitude_px']:.2f} px で反転",
    }[name]()


def build_sampler(log, results: dict) -> dict:
    """族の見本帳 — 各展示の代表 1 コマを 1 枚のタイルに束ねる。"""
    sys.path.insert(0, _HERE)
    from exhibit_tile import contact_sheet, markdown, save_exhibit

    order = [n for n in BUILDERS if n in results]
    panels = [results[n]["frame"] for n in order]
    labels = [_sampler_label(n, results[n]["facts"]) for n in order]
    sheet = contact_sheet(panels, labels, ncols=2, panel_px=460,
                          title="新しい 8 族の展示(各図の代表 1 コマ)")
    info = save_exhibit(sheet, "newops_family_sampler")
    log(f"    sampler newops_family_sampler: {info['size']}, "
        f"png {info['png_bytes'] / 1e6:.2f} MB, thumb {info['thumb_bytes'] / 1e3:.0f} kB")
    info["markdown"] = markdown(
        "newops_family_sampler", "新しい op 族の見本帳",
        "8 族 10 点の代表コマ。1 枚ずつ原寸で並べる代わりに束ねてある — "
        "各図の中身は本文のアニメーションで見てほしい。")
    return info


# --------------------------------------------------------------------------- #
# CLI                                                                           #
# --------------------------------------------------------------------------- #
BUILDERS = {
    "csi": ("newops_csi_step_sweep", build_csi),
    "bearing": ("newops_bearing_envelope", build_bearing),
    "lightfield": ("newops_lightfield_refocus", build_lightfield),
    "parallax": ("newops_lightfield_parallax", build_parallax),
    "photon": ("newops_photon_buildup", build_photon),
    "quaternion": ("newops_quaternion_rotate", build_quaternion),
    "fmcw": ("newops_fmcw_window", build_fmcw),
    "specular": ("newops_specular_split", build_specular),
    "shadow": ("newops_photometric_shadow", build_photometric_shadow),
    "motionmag": ("newops_motion_magnify", build_motionmag),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="新しい op 族の記事用デモ(すべて GIF + mp4)")
    ap.add_argument("--figs", default=",".join(BUILDERS),
                    help="comma list of: " + ", ".join(BUILDERS))
    ap.add_argument("--out", default=_MEDIA_DIR)
    ap.add_argument("--thumbs", default=_THUMB_DIR)
    ap.add_argument("--no-extras", action="store_true",
                    help="工程フリップブックと見本帳(束ねた展示)を作らない")
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
        results[name] = {"stem": stem, "info": info, "facts": facts,
                         "frame": frames[info["thumb"]["frame_index"]]}

    extras = {}
    if not args.no_extras:
        log("[build] flow -> newops_lightfield_flow (flipbook)")
        extras["flow"] = build_lightfield_flow(log, args.out, args.thumbs)
        if len(results) >= 3:
            log("[build] sampler -> newops_family_sampler (contact sheet)")
            extras["sampler"] = build_sampler(log, results)

    log(f"=== done in {time.time() - t0:.1f}s ===")
    for name, r in results.items():
        i = r["info"]
        kinds = [k for k in ("png", "gif", "mp4") if k in i]
        parts = "  ".join(f"{k} {i[k]['bytes'] / 1e6:.2f}MB" for k in kinds)
        log(f"  {name:11s} {i['n_frames']:3d} frame(s) "
            f"{i['size'][0]}x{i['size'][1]} fps={i['fps']}  {parts}")
    for name, i in extras.items():
        if "gif_bytes" in i:
            log(f"  {name:11s} {i['frames']:3d} frame(s) {i['size'][0]}x{i['size'][1]}"
                f"       gif {i['gif_bytes'] / 1e6:.2f}MB")
        else:
            log(f"  {name:11s}   1 sheet   {i['size'][0]}x{i['size'][1]}"
                f"       png {i['png_bytes'] / 1e6:.2f}MB")
    if ANOMALIES:
        log(f"--- {len(ANOMALIES)} anomaly/anomalies noticed while drawing ---")
        for a in ANOMALIES:
            log(f"  * {a}")
    else:
        log("--- no display anomalies noticed ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
