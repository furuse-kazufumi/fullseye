# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_visionlab_video — マシンビジョン仮想環境(``visiondesign``/``defectgen``/
``visionlab``)の**動画デモ**を作る。記事に貼れる GIF + mp4 + サムネイル JPG。

作る動画は 2 本で、どちらも「**数字が絵と一緒に動く**」ことを狙っている。表に
並べた µm の列を眺めても、検査系の限界は身体に入らない。掃引しながら画像と
判定が同時に変わるのを見ると、「どこで見えなくなるのか」が一目で分かる。

  1. ``visionlab_sweep``  — 系を固定して**欠陥サイズを掃引**する。左が撮像画像、
     右が検査器の出力と正解マスクの重ね合わせ、下が IoU の曲線。曲線には
     ``visiondesign.resolving_power`` が返す**光学の限界**を縦線で刻んである。
     小さいうちは何も検出できず、ある大きさで**急に検出され始める**。その閾値が
     光学限界のどれだけ右にあるか — それがこの動画の全部である。
  2. ``visionlab_design`` — 欠陥サイズを固定して**作動距離を掃引**する。同じ
     100 µm の傷が、離れるほど画素数を失い、やがて原理的にも解けなくなる。
     下の曲線は光学限界 [µm] そのもので、欠陥サイズの水平線と**交差する点**が
     「このレンズでここまで」の境界になる。

**数字はすべて実際に関数を呼んで得た実測値**である。決め打ちの閾値も、手で
書いた µm も無い(オーバーレイの文字列は毎フレーム計算結果を整形しただけ)。
seed は固定なので、同じコマンドは同じフレームを返す。

描画は Fullseye 自身の ``imagedraw`` op(``draw_line``/``draw_polyline``/
``draw_circle``/``draw_markers``)と numpy 合成で組む。**文字だけは** Fullseye に
テキスト描画 op が無いため PIL の ``ImageDraw.text`` を使う(数値ラベル専用)。
書き出しは ``video.write_video``(mp4=imageio-ffmpeg / GIF=Pillow 経路)で、
**GIF と mp4 は同一のフレーム列**から書く(撮り直さない)。書き出し後に読み戻して
フレーム数が期待と一致することを強制検証する(一致しなければ例外)。

使い方::

    py -3.11 tools/gen_visionlab_video.py                 # 両方
    py -3.11 tools/gen_visionlab_video.py --clips sweep   # 片方だけ
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Callable

import numpy as np

# スクリプト直実行(py tools/gen_visionlab_video.py)でも動くよう repo ルートを
# sys.path に足す(自動で載るのは tools/ だけのため)。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import imagedraw                                          # Fullseye の描画 op
import video                                              # Fullseye の書き出し
import visiondesign as vd
import visionlab as vl

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_MEDIA_DIR = os.path.join(_ROOT, "docs", "articles", "assets", "media")

# --------------------------------------------------------------------------- #
# 版面(すべて偶数に落ちるよう組む — H.264 は幅高さが偶数でないと詰む)          #
# --------------------------------------------------------------------------- #
TILE_PX = 192          # 生成タイルの一辺 [px]
SCALE = 2              # 表示倍率(最近傍。4 画素の傷を「4 画素」として見せる)
PANEL = TILE_PX * SCALE
MARGIN, GAP = 12, 16
HUD_H = 30             # 上端の系の諸元
INFO_H = 46            # パネル直下の実測値行(2 行)
PLOT_H = 128           # 曲線パネルの高さ
AXIS_H = 22            # 目盛りラベル
W = MARGIN + PANEL + GAP + PANEL + MARGIN            # 808
PANEL_Y = HUD_H + 6
INFO_Y = PANEL_Y + PANEL
PLOT_Y = INFO_Y + INFO_H
H = PLOT_Y + PLOT_H + AXIS_H + 6                     # 640
PLOT_X0, PLOT_X1 = 74, W - 22

# 配色(赤緑対で意味を担わせない = 色覚に依らず読める組み合わせ)
C_BG = (0.055, 0.062, 0.075)
C_PANEL_BG = (0.10, 0.11, 0.13)
C_TEXT = (0.86, 0.87, 0.84)
C_DIM = (0.52, 0.55, 0.58)
C_HIT = (0.13, 0.85, 0.80)        # 正解 ∩ 検出(当たり)
C_MISS = (1.00, 0.70, 0.16)       # 正解のみ(見逃し)
C_FALSE = (0.58, 0.42, 0.90)      # 検出のみ(誤検出)
C_OPTICAL = (0.35, 0.72, 1.00)    # 光学の限界
C_CURVE = (0.98, 0.86, 0.35)      # IoU 曲線
C_THRESH = (0.60, 0.62, 0.66)     # 判定閾値の水平線

MIN_IOU = 0.1                     # inspection_sweep の既定と同じ判定閾値
SEEDS = 5                         # 1 フレームあたりの試行数(検出率の分母)


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


def _fill(canvas: np.ndarray, y0: int, y1: int, x0: int, x1: int, color) -> None:
    """矩形をベタ塗り(numpy 合成。op を通すまでもない下地)。"""
    canvas[y0:y1, x0:x1, :] = np.asarray(color, np.float64)


def _upscale(a: np.ndarray, k: int) -> np.ndarray:
    """最近傍の整数倍拡大。**補間しない** — 画素の粗さ自体が見せたい情報なので。"""
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def _gray_to_rgb(img: np.ndarray) -> np.ndarray:
    return np.repeat(np.clip(np.asarray(img, np.float64), 0.0, 1.0)[:, :, None], 3, axis=2)


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
    図形(線・円・マーカー・折れ線)は Fullseye の ``imagedraw`` op で描いている。
    """
    from PIL import Image, ImageDraw
    im = Image.fromarray(frame_u8)
    d = ImageDraw.Draw(im)
    for x, y, s, col, size, bold in items:
        rgb = tuple(int(round(255 * c)) for c in col)
        d.text((x, y), s, fill=rgb, font=_font(size, bold))
    return np.asarray(im)


def _mask_centroid_extent(mask: np.ndarray):
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return None
    cy, cx = float(ys.mean()), float(xs.mean())
    ext = float(max(ys.max() - ys.min(), xs.max() - xs.min())) * 0.5
    return cy, cx, ext


# --------------------------------------------------------------------------- #
# パネル 2 枚(撮像 / 判定の重ね合わせ)                                          #
# --------------------------------------------------------------------------- #
def _capture_panel(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """左 — その光学系で実際に撮れる画像。欠陥の在り処だけ円で指し示す。

    円は ``imagedraw.draw_circle``(Fullseye op)。小さい欠陥は文字どおり見えない
    ので、「見えないこと」を確認できるよう位置は常に示す。"""
    panel = _upscale(_gray_to_rgb(img), SCALE)
    ce = _mask_centroid_extent(mask)
    if ce is not None:
        cy, cx, ext = ce
        r = max(14.0, ext * SCALE + 10.0)
        panel = imagedraw.draw_circle(panel, (cx * SCALE, cy * SCALE), r,
                                      color=C_MISS, width=2)
    return panel


def _verdict_panel(img: np.ndarray, mask: np.ndarray, pred: np.ndarray) -> np.ndarray:
    """右 — 検査器の出力と正解の重ね合わせ。3 色で当たり/見逃し/誤検出を分ける。"""
    base = _gray_to_rgb(img) * 0.38
    hit = pred & mask
    miss = mask & ~pred
    false = pred & ~mask
    base[false] = np.asarray(C_FALSE) * 0.75
    base[miss] = np.asarray(C_MISS)
    base[hit] = np.asarray(C_HIT)
    return _upscale(base, SCALE)


# --------------------------------------------------------------------------- #
# 曲線パネル(log 軸)                                                           #
# --------------------------------------------------------------------------- #
def _logx(value: float, lo: float, hi: float) -> float:
    v = float(np.clip(value, lo, hi))
    return PLOT_X0 + (PLOT_X1 - PLOT_X0) * (np.log10(v) - np.log10(lo)) / (
        np.log10(hi) - np.log10(lo))


def _ploty(value: float, lo: float, hi: float, y0: int, y1: int) -> float:
    v = float(np.clip(value, lo, hi))
    return y1 - (y1 - y0) * (v - lo) / (hi - lo)


# --------------------------------------------------------------------------- #
# 動画 1: 欠陥サイズの掃引                                                       #
# --------------------------------------------------------------------------- #
def _measure(system, size_um: float, kind: str, contrast: float,
             texture_strength: float, seeds: int):
    """1 サイズぶんの実測 — 表示用の 1 枚 + seeds 枚ぶんの検出率/平均 IoU。

    表示するのは seed 0 の 1 枚。判定の統計は seeds 枚から取る(1 枚の当たり外れ
    でグラフが跳ねると、閾値がどこにあるのか読めなくなるため)。"""
    shown = None
    ious, hits, evaluated = [], 0, 0
    for s in range(seeds):
        try:
            img, mask, meta = vl.render_part(
                system, float(size_um), kind=kind, contrast=contrast,
                texture_strength=texture_strength, tile_px=TILE_PX, seed=s)
        except ValueError:
            continue                                    # 1 画素未満 = 描けない
        pred = vl._default_detector(img)
        inter = float(np.sum(pred & mask))
        union = float(np.sum(pred | mask))
        iou = inter / union if union > 0 else 0.0
        ious.append(iou)
        hits += int(iou >= MIN_IOU)
        evaluated += 1
        if s == 0:
            shown = (img, mask, pred, meta, iou)
    if shown is None:
        return None
    img, mask, pred, meta, iou0 = shown
    return {
        "defect_um": float(size_um), "defect_px": float(meta["defect_px"]),
        "img": img, "mask": mask, "pred": pred, "iou": float(iou0),
        "mean_iou": float(np.mean(ious)), "evaluated": evaluated,
        "detection_rate": hits / evaluated if evaluated else None,
        "detected": bool(iou0 >= MIN_IOU),
    }


def _sweep_plot(canvas: np.ndarray, rows, i: int, lo: float, hi: float,
                optical_um: float, det_start_um):
    """下段 — IoU 対 欠陥サイズ(log 軸)。光学限界と判定閾値を線で刻む。"""
    y0, y1 = PLOT_Y + 8, PLOT_Y + PLOT_H - 10
    iou_hi = 0.5
    _fill(canvas, PLOT_Y, PLOT_Y + PLOT_H, MARGIN, W - MARGIN, C_PANEL_BG)
    # 光学限界より左 = 原理的に情報が無い領域(帯で示す)
    x_opt = _logx(optical_um, lo, hi)
    _fill(canvas, y0, y1, PLOT_X0, int(round(x_opt)), (0.16, 0.13, 0.13))
    if det_start_um is not None:
        # 光学は届いているのに検出されない帯(= レンズではなくアルゴリズムの領域)
        _fill(canvas, y0, y1, int(round(x_opt)),
              int(round(_logx(det_start_um, lo, hi))), (0.13, 0.15, 0.19))
    # 軸
    canvas = imagedraw.draw_line(canvas, (PLOT_X0, y1), (PLOT_X1, y1),
                                 color=C_DIM, width=1)
    canvas = imagedraw.draw_line(canvas, (PLOT_X0, y0), (PLOT_X0, y1),
                                 color=C_DIM, width=1)
    # 判定閾値 IoU=0.1 の水平破線
    yt = _ploty(MIN_IOU, 0.0, iou_hi, y0, y1)
    canvas = _dashed(canvas, (PLOT_X0, yt), (PLOT_X1, yt), C_THRESH, 1, 5, 4)
    # 光学限界の縦線(実線 = 計算で出た値)
    canvas = imagedraw.draw_line(canvas, (x_opt, y0), (x_opt, y1),
                                 color=C_OPTICAL, width=2)
    # 実測の検出開始サイズ(判った時点から出す)
    if det_start_um is not None:
        xd = _logx(det_start_um, lo, hi)
        canvas = _dashed(canvas, (xd, y0), (xd, y1), C_CURVE, 2, 7, 5)
    # 目盛り
    for t in (20, 30, 50, 100, 200, 400):
        if lo <= t <= hi:
            xt = _logx(float(t), lo, hi)
            canvas = imagedraw.draw_line(canvas, (xt, y1), (xt, y1 + 4),
                                         color=C_DIM, width=1)
    # 曲線(現在フレームまで)
    pts = [(_logx(r["defect_um"], lo, hi),
            _ploty(r["mean_iou"], 0.0, iou_hi, y0, y1)) for r in rows[:i + 1]]
    if len(pts) >= 2:
        canvas = imagedraw.draw_polyline(canvas, pts, color=C_CURVE, width=2)
    canvas = imagedraw.draw_markers(canvas, [pts[-1]], color=(1.0, 1.0, 1.0),
                                    size=5, shape="cross", width=2)
    return canvas, (y0, y1, iou_hi)


def build_sweep_frames(*, focal_mm=35.0, working_distance_mm=200.0,
                       pixel_pitch_um=3.45, f_number=4.0, width_px=2448,
                       height_px=2048, depth_tolerance_mm=0.5, kind="scratch",
                       contrast=-0.25, texture_strength=0.06, lo_um=20.0,
                       hi_um=400.0, frames=48, seeds=SEEDS,
                       log: Callable[[str], None] = print):
    """欠陥サイズを対数間隔で掃引したフレーム列を作る。→ ``(frames_u8, facts)``。"""
    system = vl.VisionSystem(focal_mm=focal_mm,
                             working_distance_mm=working_distance_mm,
                             pixel_pitch_um=pixel_pitch_um, width_px=width_px,
                             height_px=height_px, f_number=f_number,
                             depth_tolerance_mm=depth_tolerance_mm)
    geo = system.geometry()
    res = vd.resolving_power(pixel_pitch_um, f_number, geo["magnification"],
                             system.wavelength_um)
    optical_um = float(res["resolution_object_um"])
    grid = np.logspace(np.log10(lo_um), np.log10(hi_um), int(frames))

    log(f"  {system!r}")
    log(f"  optical limit {optical_um:.2f} um ({res['limited_by']}-limited), "
        f"{geo['um_per_pixel']:.2f} um/px")

    rows = []
    for size in grid:
        m = _measure(system, float(size), kind, contrast, texture_strength, seeds)
        if m is None:                                   # 全 seed で描けなかった
            raise RuntimeError(f"{size:.1f} um: every seed was unrenderable — "
                               "narrow the sweep range")
        rows.append(m)

    detected_sizes = [r["defect_um"] for r in rows
                      if r["detection_rate"] is not None and r["detection_rate"] >= 0.5]
    det_start = min(detected_sizes) if detected_sizes else None
    det_row = next((r for r in rows if det_start is not None
                    and r["defect_um"] == det_start), None)
    log(f"  detection starts at {det_start if det_start is None else round(det_start, 1)} um"
        + ("" if det_row is None else
           f"  ({det_row['defect_px']:.2f} px, mean IoU {det_row['mean_iou']:.3f}, "
           f"rate {det_row['detection_rate']:.0%})"))

    head = (f"f={focal_mm:g}mm  WD={working_distance_mm:g}mm  f/{f_number:g}  "
            f"pitch={pixel_pitch_um:g}um  {width_px}x{height_px}px   ->   "
            f"{geo['um_per_pixel']:.2f} um/px   FOV "
            f"{geo['fov_w_mm']:.1f}x{geo['fov_h_mm']:.1f} mm")

    out = []
    for i, r in enumerate(rows):
        canvas = np.zeros((H, W, 3), np.float64)
        canvas[:, :] = np.asarray(C_BG)
        _fill(canvas, 0, HUD_H, 0, W, (0.09, 0.10, 0.12))
        # 2 枚のパネル
        canvas[PANEL_Y:PANEL_Y + PANEL, MARGIN:MARGIN + PANEL] = \
            _capture_panel(r["img"], r["mask"])
        x2 = MARGIN + PANEL + GAP
        canvas[PANEL_Y:PANEL_Y + PANEL, x2:x2 + PANEL] = \
            _verdict_panel(r["img"], r["mask"], r["pred"])
        # 掃引がどこまで来たかを示す帯(パネル直下)
        _fill(canvas, INFO_Y, INFO_Y + INFO_H, MARGIN, W - MARGIN, (0.085, 0.095, 0.115))
        # 曲線
        canvas, (py0, py1, iou_hi) = _sweep_plot(
            canvas, rows, i, lo_um, hi_um, optical_um,
            det_start if (det_start is not None and r["defect_um"] >= det_start) else None)

        frame = _to_u8(canvas)
        detected = r["detected"]
        verdict = system.limits(r["defect_um"])["verdict"]
        labels = [
            (MARGIN, 8, head, C_TEXT, 12, False),
            (MARGIN + 6, PANEL_Y + 6, "captured image", (0.95, 0.95, 0.92), 13, True),
            (x2 + 6, PANEL_Y + 6, "detector vs ground truth", (0.95, 0.95, 0.92), 13, True),
            (x2 + 6, PANEL_Y + PANEL - 56, "hit", C_HIT, 12, True),
            (x2 + 6, PANEL_Y + PANEL - 40, "missed", C_MISS, 12, True),
            (x2 + 6, PANEL_Y + PANEL - 24, "false alarm", C_FALSE, 12, True),
            (MARGIN + 8, INFO_Y + 5,
             f"defect {r['defect_um']:6.1f} um = {r['defect_px']:5.2f} px"
             f"    optical limit {optical_um:5.1f} um ({res['limited_by']}-limited)"
             f"    optics: {verdict}",
             C_TEXT, 14, True),
            (MARGIN + 8, INFO_Y + 25,
             f"IoU {r['iou']:.3f}   detection rate {r['detection_rate']:.0%}"
             f" of {r['evaluated']} seeds   ->  "
             + ("DETECTED" if detected else "not detected"),
             (C_HIT if detected else C_DIM), 14, True),
            (MARGIN + 4, py0 + 2, "IoU", C_DIM, 11, False),
            (PLOT_X0 - 30, int(_ploty(0.5, 0.0, iou_hi, py0, py1)) - 6, "0.5", C_DIM, 11, False),
            (PLOT_X0 - 30, int(_ploty(MIN_IOU, 0.0, iou_hi, py0, py1)) - 6, "0.1", C_THRESH, 11, False),
            (PLOT_X0 - 30, int(py1) - 12, "0.0", C_DIM, 11, False),
            (PLOT_X1 - 100, py0 + 2, "defect size [um] ->", C_DIM, 11, False),
            (int(_logx(optical_um, lo_um, hi_um)) + 4, py0 + 2,
             f"optical limit {optical_um:.1f} um", C_OPTICAL, 11, True),
            (PLOT_X0 + 4, py1 - 14, "no information", (0.80, 0.52, 0.48), 10, False),
        ]
        for t in (20, 30, 50, 100, 200, 400):
            if lo_um <= t <= hi_um:
                labels.append((int(_logx(float(t), lo_um, hi_um)) - 8,
                               PLOT_Y + PLOT_H - 2, f"{t}", C_DIM, 11, False))
        if det_start is not None and r["defect_um"] >= det_start:
            labels.append((int(_logx(det_start, lo_um, hi_um)) + 4, py0 + 18,
                           f"detection starts {det_start:.0f} um", C_CURVE, 11, True))
            labels.append((int(_logx(optical_um, lo_um, hi_um)) + 4, py0 + 34,
                           "<- optics carry it here, the detector does not",
                           (0.62, 0.70, 0.80), 11, False))
        out.append(_text(frame, labels))

    facts = {
        "system": repr(system), "geometry": geo, "resolving_power": res,
        "optical_limit_um": optical_um, "limited_by": res["limited_by"],
        "detection_start_um": det_start,
        "detection_start_px": None if det_row is None else det_row["defect_px"],
        "detection_start_iou": None if det_row is None else det_row["mean_iou"],
        "detection_start_rate": None if det_row is None else det_row["detection_rate"],
        "thumb_index": 0 if det_row is None else rows.index(det_row),
        "rows": [{k: v for k, v in r.items() if k not in ("img", "mask", "pred")}
                 for r in rows],
        "kind": kind, "seeds": seeds, "grid_um": [float(g) for g in grid],
    }
    return out, facts


# --------------------------------------------------------------------------- #
# 動画 2: 設計(作動距離)の掃引                                                  #
# --------------------------------------------------------------------------- #
def build_design_frames(*, focal_mm=35.0, pixel_pitch_um=3.45, f_number=4.0,
                        width_px=2448, height_px=2048, depth_tolerance_mm=0.5,
                        defect_um=100.0, kind="scratch", contrast=-0.25,
                        texture_strength=0.06, wd_lo=120.0, wd_hi=700.0,
                        frames=44, seeds=SEEDS, log: Callable[[str], None] = print):
    """作動距離を掃引 — **同じ 100 µm の傷**が離れるほど画素を失う様子。

    下段は光学限界 [µm] 対 作動距離。欠陥サイズの水平線と交差する所から先は
    「原理的に解けない」。検出はそのずっと手前で落ちる。→ ``(frames_u8, facts)``。
    """
    wds = np.linspace(wd_lo, wd_hi, int(frames))
    rows = []
    for wd in wds:
        system = vl.VisionSystem(focal_mm=focal_mm, working_distance_mm=float(wd),
                                 pixel_pitch_um=pixel_pitch_um, width_px=width_px,
                                 height_px=height_px, f_number=f_number,
                                 depth_tolerance_mm=depth_tolerance_mm)
        geo = system.geometry()
        res = vd.resolving_power(pixel_pitch_um, f_number, geo["magnification"],
                                 system.wavelength_um)
        m = _measure(system, defect_um, kind, contrast, texture_strength, seeds)
        rows.append({
            "wd_mm": float(wd), "geo": geo, "res": res,
            "optical_um": float(res["resolution_object_um"]),
            "verdict": system.limits(defect_um)["verdict"],
            "m": m,
        })

    optical = [r["optical_um"] for r in rows]
    det_ok = [r for r in rows
              if r["m"] is not None and r["m"]["detection_rate"] is not None
              and r["m"]["detection_rate"] >= 0.5]
    det_last_wd = max(r["wd_mm"] for r in det_ok) if det_ok else None
    opt_cross = next((r["wd_mm"] for r in rows if r["optical_um"] > defect_um), None)
    log(f"  defect fixed at {defect_um:g} um, WD {wd_lo:g}->{wd_hi:g} mm")
    log(f"  optical limit {optical[0]:.1f} -> {optical[-1]:.1f} um; "
        f"crosses the defect size at WD ~{opt_cross}")
    log(f"  detection survives to WD ~{det_last_wd} mm")

    o_lo, o_hi = float(min(optical)), float(max(optical))
    y0, y1 = PLOT_Y + 8, PLOT_Y + PLOT_H - 10
    x_of = lambda wd: PLOT_X0 + (PLOT_X1 - PLOT_X0) * (wd - wd_lo) / (wd_hi - wd_lo)

    out = []
    for i, r in enumerate(rows):
        canvas = np.zeros((H, W, 3), np.float64)
        canvas[:, :] = np.asarray(C_BG)
        _fill(canvas, 0, HUD_H, 0, W, (0.09, 0.10, 0.12))
        m = r["m"]
        x2 = MARGIN + PANEL + GAP
        if m is not None:
            canvas[PANEL_Y:PANEL_Y + PANEL, MARGIN:MARGIN + PANEL] = \
                _capture_panel(m["img"], m["mask"])
            canvas[PANEL_Y:PANEL_Y + PANEL, x2:x2 + PANEL] = \
                _verdict_panel(m["img"], m["mask"], m["pred"])
        else:                                            # 1 画素未満 = 描けない
            _fill(canvas, PANEL_Y, PANEL_Y + PANEL, MARGIN, MARGIN + PANEL, C_PANEL_BG)
            _fill(canvas, PANEL_Y, PANEL_Y + PANEL, x2, x2 + PANEL, C_PANEL_BG)
        _fill(canvas, INFO_Y, INFO_Y + INFO_H, MARGIN, W - MARGIN, (0.085, 0.095, 0.115))
        # 下段: 光学限界 [um] 対 作動距離
        _fill(canvas, PLOT_Y, PLOT_Y + PLOT_H, MARGIN, W - MARGIN, C_PANEL_BG)
        if opt_cross is not None:
            _fill(canvas, y0, y1, int(round(x_of(opt_cross))), PLOT_X1, (0.16, 0.13, 0.13))
        canvas = imagedraw.draw_line(canvas, (PLOT_X0, y1), (PLOT_X1, y1), color=C_DIM, width=1)
        canvas = imagedraw.draw_line(canvas, (PLOT_X0, y0), (PLOT_X0, y1), color=C_DIM, width=1)
        y_def = _ploty(defect_um, o_lo, o_hi, y0, y1)
        canvas = _dashed(canvas, (PLOT_X0, y_def), (PLOT_X1, y_def), C_MISS, 2, 7, 5)
        pts = [(x_of(rr["wd_mm"]), _ploty(rr["optical_um"], o_lo, o_hi, y0, y1))
               for rr in rows[:i + 1]]
        if len(pts) >= 2:
            canvas = imagedraw.draw_polyline(canvas, pts, color=C_OPTICAL, width=2)
        canvas = imagedraw.draw_markers(canvas, [pts[-1]], color=(1.0, 1.0, 1.0),
                                        size=5, shape="cross", width=2)
        for t in np.linspace(wd_lo, wd_hi, 5):
            canvas = imagedraw.draw_line(canvas, (x_of(t), y1), (x_of(t), y1 + 4),
                                         color=C_DIM, width=1)

        frame = _to_u8(canvas)
        geo = r["geo"]
        detected = bool(m is not None and m["detected"])
        head = (f"f={focal_mm:g}mm  f/{f_number:g}  pitch={pixel_pitch_um:g}um  "
                f"{width_px}x{height_px}px   defect fixed at {defect_um:g} um   "
                f"-- sweeping the working distance")
        labels = [
            (MARGIN, 8, head, C_TEXT, 12, False),
            (MARGIN + 6, PANEL_Y + 6, "captured image", (0.95, 0.95, 0.92), 13, True),
            (x2 + 6, PANEL_Y + 6, "detector vs ground truth", (0.95, 0.95, 0.92), 13, True),
            (MARGIN + 8, INFO_Y + 5,
             f"WD {r['wd_mm']:6.1f} mm   {geo['um_per_pixel']:6.2f} um/px   "
             f"FOV {geo['fov_w_mm']:5.1f}x{geo['fov_h_mm']:5.1f} mm   "
             f"defect = {defect_um / geo['um_per_pixel']:5.2f} px",
             C_TEXT, 14, True),
            (MARGIN + 8, INFO_Y + 25,
             f"optical limit {r['optical_um']:6.1f} um ({r['res']['limited_by']}-limited)"
             f"   optics: {r['verdict']}   " +
             ("no image (below one pixel)" if m is None else
              f"IoU {m['iou']:.3f}  rate {m['detection_rate']:.0%}  -> " +
              ("DETECTED" if detected else "not detected")),
             (C_HIT if detected else C_DIM), 14, True),
            (MARGIN + 2, y0 + 2, "optical", C_DIM, 10, False),
            (MARGIN + 2, y0 + 14, "limit[um]", C_DIM, 10, False),
            (PLOT_X0 - 34, int(y0) - 2, f"{o_hi:.0f}", C_DIM, 11, False),
            (PLOT_X0 - 34, int(y1) - 12, f"{o_lo:.0f}", C_DIM, 11, False),
            (PLOT_X0 + 6, int(y_def) - 14, f"defect {defect_um:g} um", C_MISS, 11, True),
            (PLOT_X1 - 128, y0 + 2, "working distance [mm] ->", C_DIM, 11, False),
        ]
        for t in np.linspace(wd_lo, wd_hi, 5):
            labels.append((int(x_of(t)) - 12, PLOT_Y + PLOT_H - 2, f"{t:.0f}", C_DIM, 11, False))
        if opt_cross is not None:
            labels.append((int(x_of(opt_cross)) + 4, y0 + 2,
                           "not resolvable beyond here", C_OPTICAL, 11, True))
        out.append(_text(frame, labels))

    thumb_index = 0
    if det_last_wd is not None:
        thumb_index = max(i for i, r in enumerate(rows) if r["wd_mm"] == det_last_wd)
    facts = {
        "defect_um": defect_um, "wd_range_mm": (wd_lo, wd_hi),
        "optical_um_first": optical[0], "optical_um_last": optical[-1],
        "optical_cross_wd_mm": opt_cross, "detection_last_wd_mm": det_last_wd,
        "um_per_pixel_first": rows[0]["geo"]["um_per_pixel"],
        "um_per_pixel_last": rows[-1]["geo"]["um_per_pixel"],
        "thumb_index": thumb_index, "kind": kind, "seeds": seeds,
    }
    return out, facts


# --------------------------------------------------------------------------- #
# 書き出しと検証                                                                 #
# --------------------------------------------------------------------------- #
def _verify(path: str, expected: int, log: Callable[[str], None]):
    """書き出したファイルを**読み戻して**フレーム数と形を実測し、期待と照合する。

    一致しなければ ``RuntimeError``(でっち上げ禁止 — 報告する数字は読み戻した値)。
    """
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
    log(f"    verify {os.path.basename(path)}: {n} frames (== expected), "
        f"shape {shape}, {size / 1e6:.2f} MB")
    return {"path": path, "frames": n, "shape": shape, "bytes": size}


def _write_clip(frames_u8, stem: str, *, fps: int, thumb_index: int,
                out_dir: str, log: Callable[[str], None]) -> dict:
    """**同一フレーム列**から GIF + mp4 + サムネイル JPG を書く(撮り直さない)。"""
    os.makedirs(out_dir, exist_ok=True)
    gif = os.path.join(out_dir, f"{stem}.gif")
    mp4 = os.path.join(out_dir, f"{stem}.mp4")
    thumb = os.path.join(out_dir, f"{stem}_thumb.jpg")

    video.write_video(mp4, frames_u8, fps=fps)
    video.write_video(gif, frames_u8, fps=fps)
    info = {"gif": _verify(gif, len(frames_u8), log),
            "mp4": _verify(mp4, len(frames_u8), log)}

    from PIL import Image
    idx = int(np.clip(thumb_index, 0, len(frames_u8) - 1))
    im = Image.fromarray(frames_u8[idx])
    w, h = im.size
    im.resize((720, max(2, round(h * 720 / w))), Image.LANCZOS).save(thumb, quality=88)
    info["thumb"] = {"path": thumb, "bytes": os.path.getsize(thumb),
                     "frame_index": idx}
    log(f"    thumb {os.path.basename(thumb)} from frame {idx} "
        f"({info['thumb']['bytes'] / 1e3:.0f} kB)")
    info["fps"] = fps
    return info


# --------------------------------------------------------------------------- #
# CLI                                                                           #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="visionlab の動画デモ(欠陥サイズ掃引 / 作動距離掃引)")
    ap.add_argument("--clips", default="sweep,design",
                    help="comma list of sweep,design (default both)")
    ap.add_argument("--sweep-frames", type=int, default=48)
    ap.add_argument("--design-frames", type=int, default=44)
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--seeds", type=int, default=SEEDS)
    ap.add_argument("--out", default=_MEDIA_DIR)
    args = ap.parse_args(argv)

    clips = {c.strip() for c in args.clips.split(",") if c.strip()}
    unknown = clips - {"sweep", "design"}
    if unknown:
        print(f"unknown clips: {sorted(unknown)} (valid: sweep, design)", file=sys.stderr)
        return 2

    def log(m):
        print(m, flush=True)

    t0 = time.time()
    results = {}
    if "sweep" in clips:
        log("[build] visionlab_sweep (defect size sweep)")
        frames, facts = build_sweep_frames(frames=args.sweep_frames,
                                           seeds=args.seeds, log=log)
        info = _write_clip(frames, "visionlab_sweep", fps=args.fps,
                           thumb_index=facts["thumb_index"], out_dir=args.out, log=log)
        results["sweep"] = {"info": info, "facts": facts}
    if "design" in clips:
        log("[build] visionlab_design (working-distance sweep)")
        frames, facts = build_design_frames(frames=args.design_frames,
                                            seeds=args.seeds, log=log)
        info = _write_clip(frames, "visionlab_design", fps=args.fps,
                           thumb_index=facts["thumb_index"], out_dir=args.out, log=log)
        results["design"] = {"info": info, "facts": facts}

    log(f"=== done in {time.time() - t0:.1f}s ===")
    for name, r in results.items():
        i = r["info"]
        log(f"  {name}: gif {i['gif']['bytes'] / 1e6:.2f}MB  "
            f"mp4 {i['mp4']['bytes'] / 1e6:.2f}MB  "
            f"{i['gif']['frames']} frames  {i['gif']['shape']}  fps={i['fps']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
