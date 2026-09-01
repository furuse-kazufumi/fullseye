# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wingvox_gallery — 記事の「ボクセルの色分けウィング」展示を作る。

``tools/gen_wing1d_gallery.py`` と同じ流儀:

  * **数字はすべてその場で op を呼んで得た実測値**。図に焼く値に決め打ちは 1 つも無い。
  * **描画は fullseye の op と numpy 合成のみ**(``volcolor`` / ``volops`` /
    ``render3d`` / ``imagedraw``)。**matplotlib は使わない**。文字だけは
    fullseye にテキスト描画 op が無いため PIL の ``ImageDraw.text``(数値ラベル専用)。
  * **決定的**。乱数は seed 固定、幾何も固定なので、同じコマンドは同じバイト列を
    返す(``--verify`` で 2 回生成して SHA-256 を突き合わせる)。
  * **止まった 1 コマでも意味が分かる**ように、各コマに何を見ているかと現在値を焼く。

展示は 7 点(GIF 5 / PNG 2):

  1. ``slice_flow``     GIF  色分けしたボクセルのスライス送り(**主役**)
  2. ``flicker``        GIF  ちらつきの対比 ―― 左「断面ごとに色付け」/ 右「ボリュームで色付け」
  3. ``connectivity``   PNG  6 / 18 / 26 連結で成分数が変わる(タイル)
  4. ``sieve``          GIF  体積でふるいにかける ―― 残った粒子の色は動かない
  5. ``overlay_alpha``  GIF  元のグレー CT に色ラベルを重ねる(α 掃引)
  6. ``mesh_turntable`` GIF  色付きメッシュのターンテーブル
  7. ``legend``         PNG  凡例つきの計測表(どの色がどの粒子で、体積は幾つか)

使い方::

    py -3.11 tools/gen_wingvox_gallery.py
    py -3.11 tools/gen_wingvox_gallery.py --only slice_flow,flicker
    py -3.11 tools/gen_wingvox_gallery.py --verify        # 決定性の検査
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

from scipy import ndimage                             # noqa: E402  2-D ラベリング(対比用)

import imgio                                          # noqa: E402  2-D の色分け(対比の左側)
import render3d                                       # noqa: E402  marching cubes / ラスタライズ
import volcolor as VC                                 # noqa: E402  本題
import volops                                         # noqa: E402  3-D 連結成分

from exhibit_tile import (contact_sheet, flipbook, markdown,      # noqa: E402
                          markdown_animation, save_animation, save_exhibit)

ASSETS = os.path.join(_ROOT, "docs", "articles", "assets")
MEDIA = os.path.join(ASSETS, "media")
EXHIBITS = os.path.join(_ROOT, "docs", "articles", "exhibits")

SEED = 0
SPACING = (0.50, 0.20, 0.20)        # mm/voxel。z だけ粗い = 実際の CT でよくある形
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\meiryo.ttc",
    r"C:\Windows\Fonts\YuGothM.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
)

BG = (0.055, 0.062, 0.075)
FG = (0.92, 0.92, 0.94)
MUTED = (0.60, 0.60, 0.66)
ACCENT = (0.38, 0.66, 1.00)


# --------------------------------------------------------------------------- #
# 素材(決定的)                                                                #
# --------------------------------------------------------------------------- #
def particle_volume(shape=(24, 48, 48)):
    """16 個の粒子(球)を格子状に置いた合成 CT ボリューム(2 値)。

    半径は 2.0 - 4.8 voxel、z 中心は 4 段。断面ごとに現れる粒子の数と並びが変わる
    ので、「断面ごとに色を付け直す」と番号が振り直されて色が動く ―― 展示 2 の題材。
    """
    D, H, W = shape
    z, y, x = np.indices(shape).astype(np.float64)
    vol = np.zeros(shape)
    for gy in range(4):
        for gx in range(4):
            k = gy * 4 + gx
            cy, cx = 6.0 + gy * 12.0, 6.0 + gx * 12.0
            cz = 5.0 + (k % 4) * 4.5
            r = 2.0 + (k % 5) * 0.7
            vol[((z - cz) ** 2 + (y - cy) ** 2 + (x - cx) ** 2) <= r * r] = 1.0
    return vol


def grey_ct(binary, seed: int = 3):
    """粒子が明るく、背景に粒状ノイズが乗ったグレー CT(決定的)。"""
    rng = np.random.default_rng(seed)
    soft = ndimage.gaussian_filter(binary, 0.8)
    return np.clip(0.22 + 0.10 * rng.standard_normal(binary.shape) + 0.45 * soft, 0.0, 1.0)


def touching_pair(kind: str):
    """角だけ / 稜線だけで触れる 2 つの立方体(connectivity の題材)。"""
    v = np.zeros((11, 11, 11))
    v[2:6, 2:6, 2:6] = 1.0
    if kind == "corner":
        v[6:10, 6:10, 6:10] = 1.0       # 頂点 1 点だけを共有
    else:
        v[6:10, 6:10, 2:6] = 1.0        # 稜線を共有
    return v


# --------------------------------------------------------------------------- #
# 描画ヘルパ(PIL は文字だけ)                                                   #
# --------------------------------------------------------------------------- #
def _font(size: int):
    from PIL import ImageFont
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _up(rgb, k: int):
    """最近傍で k 倍に拡大(ボクセルの粒を残す ―― 補間すると格子の話が消える)。"""
    return np.repeat(np.repeat(np.asarray(rgb, np.float64), k, axis=0), k, axis=1)


def _canvas(h: int, w: int, colour=BG):
    return np.tile(np.asarray(colour, np.float64), (h, w, 1))


def _paste(dst, src, top: int, left: int):
    h, w = src.shape[:2]
    dst[top:top + h, left:left + w, :] = src
    return dst


def _text(rgb, items, *, size: int = 16, where: str = "panel"):
    """``items`` = [(x, y, text, colour, anchor)] を焼き込む(PIL の text のみ)。

    枠からはみ出す文字は**書く前に例外**にする。端が切れた図は「壊れている」と
    機械にも見えない形で通ってしまい、記事に出るまで誰も気づかない。
    """
    from PIL import Image, ImageDraw

    _assert_fits(items, rgb.shape[1], size, where)
    im = Image.fromarray(np.round(np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB")
    dr = ImageDraw.Draw(im)
    cache = {}
    for x, y, txt, col, anchor in items:
        fs = size if len(col) == 3 else int(col[3])
        fnt = cache.setdefault(fs, _font(fs))
        dr.text((x, y), txt, font=fnt, anchor=anchor,
                fill=tuple(int(round(c * 255)) for c in col[:3]))
    return np.asarray(im, np.float64) / 255.0


def _swatch(rgb, x: int, y: int, w: int, h: int, colour, border=MUTED):
    rgb[y:y + h, x:x + w] = np.asarray(colour, np.float64)
    rgb[y:y + 1, x:x + w] = border
    rgb[y + h - 1:y + h, x:x + w] = border
    rgb[y:y + h, x:x + 1] = border
    rgb[y:y + h, x + w - 1:x + w] = border
    return rgb


def _frame_border(rgb, colour=(0.22, 0.24, 0.30)):
    rgb[0, :] = colour
    rgb[-1, :] = colour
    rgb[:, 0] = colour
    rgb[:, -1] = colour
    return rgb


def _text_width(txt: str, size: int) -> int:
    """PIL に実際に測らせる。目分量で決めると端が切れた図が黙って出る。"""
    from PIL import Image, ImageDraw

    dr = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    box = dr.textbbox((0, 0), txt, font=_font(size))
    return int(box[2] - box[0])


def _fit_size(txt: str, width: int, start: int, floor: int = 11) -> int:
    """*width* に収まる最大の字数(はみ出した図を作らないための機械的な保険)。"""
    s = int(start)
    while s > floor and _text_width(txt, s) > width - 8:
        s -= 1
    return s


def _assert_fits(items, width: int, default_size: int, where: str) -> None:
    """焼き込む文字が枠に収まっているかを**生成時に**検査する(fail-closed)。"""
    for x, _y, txt, col, anchor in items:
        size = default_size if len(col) == 3 else int(col[3])
        w = _text_width(txt, size)
        left = x if anchor[0] == "l" else (x - w // 2 if anchor[0] == "m" else x - w)
        if left < 0 or left + w > width:
            raise ValueError("%s: %r (%d px @ size %d) does not fit in %d px "
                             "(left=%d)" % (where, txt[:40], w, size, width, left))


# --------------------------------------------------------------------------- #
# 1) 色分けしたボクセルのスライス送り(主役)                                     #
# --------------------------------------------------------------------------- #
def ex_slice_flow(log):
    binary = particle_volume()
    labels, n = volops.vol_label(binary, connectivity=26)
    rgbvol = VC.vol_colorize_labels(labels, seed=SEED)
    stats = VC.vol_label_shape_stats(labels, spacing=SPACING)
    by_id = {s["label"]: s for s in stats}
    D, H, W = labels.shape
    k = 9
    pw = W * k
    pal = VC.vol_label_palette(int(labels.max()), seed=SEED)

    frames = []
    for z in range(D):
        sl = VC.vol_label_slice_rgb(rgbvol, z, "z")
        panel = _frame_border(_up(sl, k))
        canvas = _canvas(pw + 92, pw)
        _paste(canvas, panel, 0, 0)
        here = sorted(int(i) for i in np.unique(labels[z]) if i > 0)
        vol_mm3 = sum(by_id[i]["volume"] for i in here)
        # 断面に写っている粒子の色見本(ボリューム由来なので断面が変わっても不動)
        x = 8
        for i in here[:16]:
            _swatch(canvas, x, pw + 36, 18, 18, pal[i])
            x += 22
        canvas = _text(canvas, [
            (8, pw + 8, "z = %2d / %d   写る粒子 %2d 個   総体積 %6.3f mm3"
             % (z, D - 1, len(here), vol_mm3), FG + (16,), "la"),
            (8, pw + 62, "色はボリューム全体で 1 度だけ決めた ―― 断面が変わっても動かない",
             ACCENT + (14,), "la"),
        ], size=16, where="slice_flow")
        frames.append(canvas)

    title = "色分けしたボクセルの断面送り(16 粒子・26 連結)"
    book = flipbook(frames, ["z=%d" % z for z in range(D)], title=title,
                    title_font_size=_fit_size(title, pw, 24))
    info = save_animation(book, "wingvox_slice_flow", duration_ms=260, hold_last_ms=1200)
    facts = {"components": int(n), "slices": int(D), "shape": list(labels.shape),
             "spacing_mm": list(SPACING),
             "total_volume_mm3": round(sum(s["volume"] for s in stats), 4),
             "colours_per_component": 1,
             "ops": ["vol_label", "vol_colorize_labels", "vol_label_slice_rgb",
                     "vol_label_shape_stats", "vol_label_palette"]}
    return _info(info, "gif", "wingvox_slice_flow"), facts


# --------------------------------------------------------------------------- #
# 2) ちらつきの対比(この族の存在理由)                                          #
# --------------------------------------------------------------------------- #
def ex_flicker(log):
    binary = particle_volume()
    labels, n = volops.vol_label(binary, connectivity=26)
    rgbvol = VC.vol_colorize_labels(labels, seed=SEED)
    measured = VC.vol_label_color_flicker(binary, axis="z", seed=SEED)
    D, H, W = labels.shape
    k = 6
    pw, gap = W * k, 20
    struct = ndimage.generate_binary_structure(2, 2)

    # 各断面での「その粒子の色」を左右それぞれで求め、初出の色と違ったら 1 件と数える
    first_left, changed_slices, running = {}, [], 0
    left_frames, right_frames = [], []
    for z in range(D):
        lab2d, _ = ndimage.label(labels[z] > 0, structure=struct)
        left = imgio.colorize_labels(lab2d, seed=SEED)          # 断面ごとに色付け
        right = VC.vol_label_slice_rgb(rgbvol, z, "z")          # ボリュームで色付け
        hit = False
        for i in np.unique(labels[z]):
            i = int(i)
            if i == 0:
                continue
            px = left[labels[z] == i]
            uniq, cnt = np.unique(px, axis=0, return_counts=True)
            dom = tuple(uniq[np.lexsort((np.arange(len(uniq)), -cnt))[0]])
            if i not in first_left:
                first_left[i] = dom
            elif dom != first_left[i]:
                hit = True
        if hit:
            running += 1
            changed_slices.append(z)
        left_frames.append((left, hit, running))
        right_frames.append(right)

    frames = []
    for z in range(D):
        left, hit, running = left_frames[z]
        canvas = _canvas(pw + 88, pw * 2 + gap)
        _paste(canvas, _frame_border(_up(left, k),
                                     (0.75, 0.35, 0.20) if hit else (0.22, 0.24, 0.30)), 24, 0)
        _paste(canvas, _frame_border(_up(right_frames[z], k)), 24, pw + gap)
        canvas = _text(canvas, [
            (pw // 2, 8, "A 断面ごとに色付け", FG + (17,), "ma"),
            (pw + gap + pw // 2, 8, "B ボリュームで色付け", FG + (17,), "ma"),
            (pw // 2, pw + 34, "色が変わった断面 %2d / %2d" % (running, z + 1),
             ((1.0, 0.55, 0.35) if running else MUTED) + (16,), "ma"),
            (pw + gap + pw // 2, pw + 34, "色が変わった断面  0 / %2d" % (z + 1),
             (0.45, 0.85, 0.60, 16), "ma"),
            (pw // 2, pw + 58, "z = %d" % z, MUTED + (15,), "ma"),
            (pw + gap + pw // 2, pw + 58, "z = %d" % z, MUTED + (15,), "ma"),
        ], size=16, where="flicker")
        frames.append(canvas)

    title = "違うのは色を付ける順序だけ(同じパレット・同じ seed)"
    book = flipbook(frames, ["z=%d" % z for z in range(D)], title=title,
                    title_font_size=_fit_size(title, pw * 2 + gap, 24))
    info = save_animation(book, "wingvox_flicker", duration_ms=300, hold_last_ms=1800)
    facts = {"components": int(n), "slices": int(D),
             "per_slice_changed_slices": int(measured["slices_with_change"]),
             "per_slice_changed_pairs": int(measured["changed_pairs"]),
             "pairs_checked": int(measured["pairs_checked"]),
             "per_slice_changed_components": int(measured["changed_components"]),
             "flicker_rate_pct": round(100 * measured["flicker_rate"], 1),
             "volume_changed_slices": int(measured["volume_slices_with_change"]),
             "volume_changed_pairs": int(measured["volume_changed_pairs"]),
             "burned_in_running_total": int(running),
             "ops": ["vol_label", "vol_label_color_flicker", "vol_colorize_labels",
                     "vol_label_slice_rgb", "colorize_labels"]}
    assert running == measured["slices_with_change"], (running, measured)
    return _info(info, "gif", "wingvox_flicker"), facts


# --------------------------------------------------------------------------- #
# 3) connectivity 6 / 18 / 26                                                  #
# --------------------------------------------------------------------------- #
def ex_connectivity(log):
    panels, labels_txt, counts = [], [], {}
    k = 22
    for kind, jp in (("corner", "頂点接触"), ("edge", "稜線接触")):
        v = touching_pair(kind)
        counts[kind] = {}
        for c in (6, 18, 26):
            lab, nn = volops.vol_label(v, connectivity=c)
            counts[kind][c] = int(nn)
            # 2 つの塊がいちばん見える向き = 前面(y 軸)からの front 合成
            img = VC.vol_label_volume_render(lab, axis="y", mode="front", seed=SEED)
            panel = _canvas(v.shape[0] * k + 30, v.shape[2] * k)
            _paste(panel, _frame_border(_up(img, k)), 30, 0)
            panel = _text(panel, [(panel.shape[1] // 2, 5,
                                   "%d 連結 → %d 成分 / %d 色" % (c, nn, nn),
                                   FG + (17,), "ma")], size=17, where="connectivity")
            panels.append(panel)
            labels_txt.append("%s・%d 連結 = %d 成分" % (jp, c, nn))
    title = "斜めに接する 2 塊は、近傍の定義で 1 つにも 2 つにもなる"
    sheet = contact_sheet(panels, labels_txt, ncols=3, panel_px=280,
                          title=title, title_font_size=_fit_size(title, 3 * 280, 24))
    info = save_exhibit(sheet, "wingvox_connectivity")
    facts = {"corner": counts["corner"], "edge": counts["edge"],
             "note": "角接触は 26 だけが繋ぎ、稜線接触は 18 から繋がる",
             "ops": ["vol_label", "vol_label_volume_render", "vol_label_palette"]}
    return _info(info, "sheet", "wingvox_connectivity", ncols=3, panels=len(panels)), facts


# --------------------------------------------------------------------------- #
# 4) 体積でふるいにかける ―― 残った粒子の色は動かない                            #
# --------------------------------------------------------------------------- #
def ex_sieve(log):
    binary = particle_volume()
    labels, n = volops.vol_label(binary, connectivity=26)
    stats = VC.vol_label_shape_stats(labels, spacing=SPACING)
    rgbvol = VC.vol_colorize_labels(labels, seed=SEED)
    vols = sorted(s["volume"] for s in stats)
    thresholds = [0.0] + vols                       # 1 個ずつ落ちていく閾値の列
    k = 9
    base_front = VC.vol_label_volume_render(labels, "z", "front", seed=SEED)
    pw = base_front.shape[1] * k

    frames, rows = [], []
    for t in thresholds:
        kept_lab, kept = VC.vol_select_labels(labels, stats, min_volume=t)
        img = VC.vol_label_volume_render(kept_lab, "z", "front", seed=SEED)
        # 残った粒子の色が元と 1 画素も違わないことを毎コマ確かめる
        m = kept_lab > 0
        stable = bool(np.array_equal(rgbvol[m], VC.vol_colorize_labels(kept_lab,
                                                                      seed=SEED)[m]))
        rows.append({"min_volume_mm3": round(float(t), 4), "kept": int(kept.size),
                     "colours_unchanged": stable})
        canvas = _canvas(pw + 92, pw)
        _paste(canvas, _frame_border(_up(img, k)), 0, 0)
        canvas = _text(canvas, [
            (8, pw + 8, "min_volume = %6.3f mm3      残る粒子 %2d / %d"
             % (t, kept.size, n), FG + (16,), "la"),
            (8, pw + 36, "残った粒子の色は 1 画素も変わっていない: %s"
             % ("はい" if stable else "いいえ"),
             ((0.45, 0.85, 0.60) if stable else (1.0, 0.4, 0.3)) + (15,), "la"),
            (8, pw + 62, "relabel=False = 番号を振り直さない = パレットの行が動かない",
             MUTED + (14,), "la"),
        ], size=16, where="sieve")
        frames.append(canvas)

    title = "体積でふるいにかける(z 方向の front 合成)"
    book = flipbook(frames, ["min_volume=%.2f mm3" % t for t in thresholds],
                    title=title, title_font_size=_fit_size(title, pw, 24))
    info = save_animation(book, "wingvox_sieve", duration_ms=420, hold_last_ms=1600)
    facts = {"components": int(n), "steps": len(thresholds),
             "volumes_mm3": [round(v, 4) for v in vols],
             "all_colours_unchanged": all(r["colours_unchanged"] for r in rows),
             "sweep": rows,
             "ops": ["vol_label", "vol_label_shape_stats", "vol_select_labels",
                     "vol_label_volume_render", "vol_colorize_labels"]}
    return _info(info, "gif", "wingvox_sieve"), facts


# --------------------------------------------------------------------------- #
# 5) 元のグレー CT に色ラベルを重ねる(α 掃引)                                  #
# --------------------------------------------------------------------------- #
def ex_overlay_alpha(log):
    binary = particle_volume()
    labels, n = volops.vol_label(binary, connectivity=26)
    grey = grey_ct(binary)
    D, H, W = labels.shape
    z0 = int(np.argmax([(labels[z] > 0).sum() for z in range(D)]))
    fg = labels > 0
    base = VC.vol_label_overlay(grey, labels, seed=SEED, alpha=0.0)
    k = 9
    pw = W * k

    alphas = [round(0.1 * i, 2) for i in range(0, 11)]
    alphas = alphas + alphas[-2:0:-1]                   # 往復させる(端で止めない)
    frames, sweep = [], []
    for a in alphas:
        ov = VC.vol_label_overlay(grey, labels, seed=SEED, alpha=a)
        d_fg = float(np.abs(ov[fg] - base[fg]).mean())
        d_bg = float(np.abs(ov[~fg] - base[~fg]).mean())
        sweep.append({"alpha": a, "fg_mean_abs_diff": round(d_fg, 4),
                      "bg_mean_abs_diff": round(d_bg, 4)})
        sl = VC.vol_label_slice_rgb(ov, z0, "z")
        canvas = _canvas(pw + 92, pw)
        _paste(canvas, _frame_border(_up(sl, k)), 0, 0)
        canvas = _text(canvas, [
            (8, pw + 8, "alpha = %.2f   前景の変化 %.4f   背景の変化 %.4f"
             % (a, d_fg, d_bg), FG + (16,), "la"),
            (8, pw + 36, "下の CT が見えるところと、色が勝つところ", ACCENT + (15,), "la"),
            (8, pw + 62, "背景は alpha に依らず 0.0000 ―― 色はラベルの上にしか乗らない",
             MUTED + (14,), "la"),
        ], size=16, where="overlay_alpha")
        frames.append(canvas)

    shell = VC.vol_label_overlay(grey, labels, seed=SEED, alpha=1.0, mode="boundary")
    n_shell = int((shell != base).any(axis=3).sum())
    n_fill = int(fg.sum())
    book = flipbook(frames, ["alpha=%.2f" % a for a in alphas],
                    title="グレー CT に色ラベルを重ねる(断面 z=%d)" % z0)
    info = save_animation(book, "wingvox_overlay_alpha", duration_ms=110,
                          hold_last_ms=700)
    facts = {"slice": z0, "components": int(n), "frames": len(alphas),
             "sweep": sweep[:21],
             "bg_untouched_at_every_alpha": all(s["bg_mean_abs_diff"] == 0.0
                                                for s in sweep),
             "boundary_voxels": n_shell, "fill_voxels": n_fill,
             "boundary_share_pct": round(100 * n_shell / n_fill, 1),
             "ops": ["vol_label", "vol_label_overlay", "vol_label_slice_rgb"]}
    return _info(info, "gif", "wingvox_overlay_alpha"), facts


# --------------------------------------------------------------------------- #
# 6) 色付きメッシュのターンテーブル                                             #
# --------------------------------------------------------------------------- #
def ex_mesh_turntable(log):
    binary = particle_volume()
    labels, n = volops.vol_label(binary, connectivity=26)
    meshes = VC.vol_labels_to_meshes(labels, seed=SEED, spacing=SPACING, axes="xyz")
    tris = sum(int(m["faces"].shape[0]) for m in meshes)
    allV = np.concatenate([m["vertices"] for m in meshes])
    centre = 0.5 * (allV.min(axis=0) + allV.max(axis=0))
    radius = float(np.linalg.norm(allV - centre, axis=1).max())
    size = 300
    K = render3d.intrinsics_from_fov(38.0, size, size)
    dist = 1.30 * radius / np.tan(np.deg2rad(38.0) * 0.5)
    light = np.array([0.35, 0.45, 0.82])
    light = light / np.linalg.norm(light)

    frames = []
    n_az = 24
    for f in range(n_az):
        az = np.deg2rad(360.0 * f / n_az)
        el = np.deg2rad(22.0)
        eye = centre + dist * np.array([np.cos(el) * np.cos(az),
                                        np.cos(el) * np.sin(az), np.sin(el)])
        pose = render3d.look_at(eye, centre, up=(0.0, 0.0, 1.0))
        zbuf = np.full((size, size), np.inf)
        img = _canvas(size, size)
        for md in meshes:
            r = render3d.render_mesh(md["vertices"], md["faces"], pose=pose,
                                     intrinsics=K, width=size, height=size)
            hit = (r["silhouette"] > 0.5) & (r["depth"] < zbuf)
            if not hit.any():
                continue
            lam = np.clip(r["normals"] @ light, 0.0, 1.0)
            shade = (0.28 + 0.72 * lam)[..., None] * np.asarray(md["color"])
            img[hit] = np.clip(shade[hit], 0.0, 1.0)
            zbuf[hit] = r["depth"][hit]
        canvas = _canvas(size + 58, size)
        _paste(canvas, _frame_border(img), 0, 0)
        canvas = _text(canvas, [
            (6, size + 8, "方位 %3d 度   %d 粒子 / 三角形 %d 枚" % (
                int(round(np.rad2deg(az))), len(meshes), tris), FG, "la"),
            (6, size + 32, "色は断面図とまったく同じ ―― 同じパレットの同じ行",
             MUTED + (13,), "la"),
        ], size=15)
        frames.append(canvas)

    book = flipbook(frames, ["方位 %d 度" % int(round(360.0 * f / n_az))
                             for f in range(n_az)],
                    title="成分ごとに marching cubes をかけた色付きメッシュ")
    info = save_animation(book, "wingvox_mesh_turntable", duration_ms=110,
                          hold_last_ms=700)
    pal = VC.vol_label_palette(int(labels.max()), seed=SEED)
    facts = {"components": int(n), "meshes": len(meshes), "triangles": int(tris),
             "azimuth_steps": n_az, "render_px": size,
             "spacing_mm": list(SPACING),
             "colours_match_slices": bool(all(np.allclose(m["color"], pal[m["label"]])
                                              for m in meshes)),
             "ops": ["vol_label", "vol_labels_to_meshes", "look_at",
                     "intrinsics_from_fov", "render_mesh"]}
    return _info(info, "gif", "wingvox_mesh_turntable"), facts


# --------------------------------------------------------------------------- #
# 7) 凡例つきの計測表                                                           #
# --------------------------------------------------------------------------- #
def ex_legend(log):
    binary = particle_volume()
    labels, n = volops.vol_label(binary, connectivity=26)
    props = volops.vol_region_props(labels, spacing=SPACING, surface="faces")
    stats = {s["label"]: s for s in VC.vol_label_shape_stats(labels, spacing=SPACING)}
    legend = VC.vol_label_legend(labels, props, seed=SEED, measure="volume")

    row_h, head_h, foot_h = 26, 74, 60
    width = 760
    img = _canvas(head_h + row_h * len(legend) + foot_h, width)
    items = [
        (16, 12, "どの色がどの粒子か ―― 色だけの図は作らない", FG + (20,), "la"),
        (16, 42, "16 粒子・(24,48,48) voxel・spacing (0.50, 0.20, 0.20) mm・26 連結",
         MUTED + (14,), "la"),
        (58, head_h - 22, "ラベル", MUTED + (13,), "la"),
        (150, head_h - 22, "体積 mm3", MUTED + (13,), "la"),
        (250, head_h - 22, "全体比", MUTED + (13,), "la"),
        (340, head_h - 22, "等価直径 mm", MUTED + (13,), "la"),
        (470, head_h - 22, "球形度", MUTED + (13,), "la"),
        (560, head_h - 22, "伸長度", MUTED + (13,), "la"),
        (650, head_h - 22, "端に接する", MUTED + (13,), "la"),
    ]
    total_bar = 190.0
    for r in legend:
        y = head_h + row_h * (r["rank"] - 1)
        st = stats[r["label"]]
        pr = next(p for p in props if p["label"] == r["label"])
        _swatch(img, 16, y + 4, 30, 17, r["rgb"])
        img[y + 10:y + 16, 250:250 + int(round(total_bar * r["share"]))] = ACCENT
        items += [
            (58, y + 5, "%2d  %s" % (r["label"], r["hex"]), FG + (14,), "la"),
            (150, y + 5, "%7.4f" % r["value"], FG + (14,), "la"),
            (250 + total_bar + 8, y + 5, "%4.1f %%" % (100 * r["share"]),
             MUTED + (13,), "la"),
            (340, y + 5, "%6.3f" % st["equivalent_diameter"], FG + (14,), "la"),
            (470, y + 5, "%5.3f" % pr["sphericity"], FG + (14,), "la"),
            (560, y + 5, "%5.2f" % st["elongation"], FG + (14,), "la"),
            (650, y + 5, "はい" if st["touches_border"] else "いいえ",
             MUTED + (13,), "la"),
        ]
    fy = head_h + row_h * len(legend)
    items += [
        (16, fy + 8, "合計 %.4f mm3(比率の合計 %.6f)。体積は voxel 数 x %.4f mm3。"
         % (sum(r["value"] for r in legend), sum(r["share"] for r in legend),
            SPACING[0] * SPACING[1] * SPACING[2]), MUTED + (14,), "la"),
        (16, fy + 32, "球形度は volops.vol_region_props(surface='faces')、"
         "伸長度は volcolor.vol_label_shape_stats の sqrt(l1/l2)。",
         MUTED + (13,), "la"),
    ]
    img = _text(img, items)
    info = save_exhibit(img, "wingvox_legend")
    facts = {"components": int(n), "spacing_mm": list(SPACING),
             "total_volume_mm3": round(sum(r["value"] for r in legend), 4),
             "share_sum": round(sum(r["share"] for r in legend), 6),
             "voxel_volume_mm3": round(SPACING[0] * SPACING[1] * SPACING[2], 6),
             "largest": {"label": legend[0]["label"], "hex": legend[0]["hex"],
                         "volume_mm3": round(legend[0]["value"], 4)},
             "smallest": {"label": legend[-1]["label"], "hex": legend[-1]["hex"],
                          "volume_mm3": round(legend[-1]["value"], 4)},
             "sphericity_range": [round(min(p["sphericity"] for p in props), 3),
                                  round(max(p["sphericity"] for p in props), 3)],
             "ops": ["vol_label", "vol_region_props", "vol_label_shape_stats",
                     "vol_label_legend", "vol_label_palette"]}
    return _info(info, "still", "wingvox_legend"), facts


# --------------------------------------------------------------------------- #
# 生成物のメタ情報                                                              #
# --------------------------------------------------------------------------- #
def _info(raw: dict, kind: str, stem: str, ncols: int = 1, panels: int = 1):
    if kind == "gif":
        return {"kind": "gif", "stem": stem, "frames": raw["frames"],
                "shape": (raw["size"][1], raw["size"][0]),
                "bytes": raw["gif_bytes"], "sha256": raw["gif_sha256"],
                "ms": 0, "hold_ms": 0, "thumb_bytes": 0, "ncols": 1}
    return {"kind": kind, "stem": stem, "frames": panels,
            "shape": (raw["size"][1], raw["size"][0]),
            "bytes": raw["png_bytes"], "sha256": raw["png_sha256"],
            "thumb_bytes": raw["thumb_bytes"], "ncols": ncols, "ms": 0, "hold_ms": 0}


EXHIBIT_ORDER = [
    ("slice_flow", ex_slice_flow),
    ("flicker", ex_flicker),
    ("connectivity", ex_connectivity),
    ("sieve", ex_sieve),
    ("overlay_alpha", ex_overlay_alpha),
    ("mesh_turntable", ex_mesh_turntable),
    ("legend", ex_legend),
]

BUNDLING = {
    "slice_flow": "フリップブック GIF(断面が進む・寸法が揃っている)",
    "flicker": "フリップブック GIF(左右を 1 コマに合成して同時に進める)",
    "connectivity": "タイル(同じ被写体に近傍の定義違いを当てた 6 枚を比べる)",
    "sieve": "フリップブック GIF(閾値が進む)",
    "overlay_alpha": "フリップブック GIF(alpha を往復掃引)",
    "mesh_turntable": "フリップブック GIF(方位が進む)",
    "legend": "原寸 1 枚(表の数値が主役 ―― 縮めると読めない)",
}

CAPTIONS = {
    "slice_flow": {
        "ja": ("色分けしたボクセルの断面送り",
               lambda f: (
                   "%d 粒子を 26 連結でラベリングし、**ボリュームのまま**色を付けてから "
                   "%d 枚の断面へ切り出した。1 つの粒子は最初から最後まで 1 色 "
                   "(実測: 全 %d 成分の色数が 1)。spacing (%.2f, %.2f, %.2f) mm で "
                   "総体積 %.3f mm3。" % (f["components"], f["slices"], f["components"],
                                          *f["spacing_mm"], f["total_volume_mm3"]))),
        "en": ("Flipping through colour-coded voxel slices",
               lambda f: (
                   "%d particles labelled with 26-connectivity, coloured **as a volume** "
                   "and only then cut into %d slices. Each particle keeps one colour from "
                   "first slice to last (measured: all %d components have exactly one "
                   "colour). At a spacing of (%.2f, %.2f, %.2f) mm they total %.3f mm3."
                   % (f["components"], f["slices"], f["components"], *f["spacing_mm"],
                      f["total_volume_mm3"]))),
    },
    "flicker": {
        "ja": ("ちらつきの対比 ―― 違うのは色を付ける順序だけ",
               lambda f: (
                   "左は断面ごとに 2-D ラベリングして色を付けたもの。断面が変わるたびに"
                   "番号が振り直されるので、**%d / %d 断面**で少なくとも 1 粒子の色が変わる "
                   "((粒子, 断面) の変化 %d / %d 組 = %.1f %%、%d 粒子すべてが一度は変わる)。"
                   "右はボリュームで色を付けてから切ったもので、変化は **0 断面 / 0 組**。"
                   "同じパレット・同じ seed で、違うのは順序だけである。"
                   % (f["per_slice_changed_slices"], f["slices"],
                      f["per_slice_changed_pairs"], f["pairs_checked"],
                      f["flicker_rate_pct"], f["per_slice_changed_components"]))),
        "en": ("Flicker, side by side — the only difference is the order",
               lambda f: (
                   "On the left each slice is labelled in 2-D and coloured on its own, so the "
                   "numbering is redrawn every slice: on **%d of %d slices** at least one "
                   "particle changes colour (%d of %d (particle, slice) pairs = %.1f %%, and "
                   "all %d particles change at least once). On the right the volume is "
                   "coloured first and cut afterwards: **0 slices, 0 pairs**. Same palette, "
                   "same seed — only the order differs."
                   % (f["per_slice_changed_slices"], f["slices"],
                      f["per_slice_changed_pairs"], f["pairs_checked"],
                      f["flicker_rate_pct"], f["per_slice_changed_components"]))),
    },
    "connectivity": {
        "ja": ("6 / 18 / 26 連結 ―― 近傍の定義が成分数を決める",
               lambda f: (
                   "同じ 2 つの立方体でも、頂点 1 点だけで接している場合は "
                   "6 連結 %d 成分 / 18 連結 %d 成分 / 26 連結 **%d 成分**、"
                   "稜線で接している場合は %d / **%d** / %d となる。"
                   "色数は成分数にそのまま連動する ―― 融合すれば色が 1 つ減る。"
                   % (f["corner"][6], f["corner"][18], f["corner"][26],
                      f["edge"][6], f["edge"][18], f["edge"][26]))),
        "en": ("6 / 18 / 26 connectivity — the neighbourhood decides the count",
               lambda f: (
                   "The same two cubes: touching at a single corner they are %d components "
                   "under 6-connectivity, %d under 18 and **%d** under 26; touching along an "
                   "edge, %d / **%d** / %d. The number of colours follows the number of "
                   "components exactly — merge two blobs and one colour disappears."
                   % (f["corner"][6], f["corner"][18], f["corner"][26],
                      f["edge"][6], f["edge"][18], f["edge"][26]))),
    },
    "sieve": {
        "ja": ("体積でふるいにかけても、残った粒子の色は動かない",
               lambda f: (
                   "``min_volume`` を 0 から %.3f mm3 まで %d 段で上げ、粒子を 1 つずつ"
                   "落としていく。落ちた粒子は背景になるが、**残った粒子の色は 1 画素も"
                   "変わらない**(全 %d コマで実測・確認)。番号を振り直さない "
                   "(``relabel=False``)からで、振り直すとパレットの行が動いて色は総取り替えになる。"
                   % (max(f["volumes_mm3"]), f["steps"], f["steps"]))),
        "en": ("Sieving by volume without moving a single colour",
               lambda f: (
                   "``min_volume`` rises from 0 to %.3f mm3 in %d steps, dropping the "
                   "particles one at a time. Those that fall out become background, but "
                   "**the survivors do not change colour by a single pixel** (checked on all "
                   "%d frames). That holds because the labels are not renumbered "
                   "(``relabel=False``); renumbering shifts the palette rows and repaints "
                   "everything."
                   % (max(f["volumes_mm3"]), f["steps"], f["steps"]))),
    },
    "overlay_alpha": {
        "ja": ("元の CT に色ラベルを重ねる ―― α を掃引する",
               lambda f: (
                   "断面 z=%d で alpha を 0 から 1 へ往復させる。前景の平均変化は "
                   "0.0000 → %.4f と alpha に**直線**で比例し、**背景の変化は alpha に"
                   "依らず 0.0000**(色はラベルの上にしか乗らない)。輪郭だけ塗る "
                   "``mode='boundary'`` なら前景 %d ボクセルのうち %d(%.1f %%)しか"
                   "塗らないので、下の構造が完全に見える。"
                   % (f["slice"], f["sweep"][-1]["fg_mean_abs_diff"],
                      f["fill_voxels"], f["boundary_voxels"], f["boundary_share_pct"]))),
        "en": ("Overlaying colour labels on the original CT — sweeping alpha",
               lambda f: (
                   "At slice z=%d alpha sweeps from 0 to 1 and back. The mean change over "
                   "the foreground runs 0.0000 -> %.4f, **linear** in alpha, while the "
                   "**background never moves at any alpha (0.0000)** — colour only lands on "
                   "labelled voxels. In ``mode='boundary'`` only %d of the %d foreground "
                   "voxels (%.1f %%) are painted, so the structure underneath stays visible."
                   % (f["slice"], f["sweep"][-1]["fg_mean_abs_diff"],
                      f["boundary_voxels"], f["fill_voxels"], f["boundary_share_pct"]))),
    },
    "mesh_turntable": {
        "ja": ("色付きメッシュのターンテーブル",
               lambda f: (
                   "%d 個の成分それぞれの bbox 部分体に marching cubes をかけ、三角形 "
                   "%d 枚のメッシュ %d 個にした。頂点は spacing (%.2f, %.2f, %.2f) mm を"
                   "掛けた物理座標で、``render3d.render_mesh`` の z バッファで合成している。"
                   "**色は断面図とまったく同じパレットの同じ行**なので、切った絵と回した絵で"
                   "同じ粒子を目で追える。"
                   % (f["components"], f["triangles"], f["meshes"], *f["spacing_mm"]))),
        "en": ("A turntable of colour-coded meshes",
               lambda f: (
                   "Marching cubes runs on each component's padded bounding box, giving %d "
                   "meshes and %d triangles for the %d components. Vertices are in physical "
                   "coordinates (spacing (%.2f, %.2f, %.2f) mm) and the frames are composited "
                   "through ``render3d.render_mesh``'s z-buffer. **The colours are the same "
                   "palette rows as the slice views**, so the same particle can be followed "
                   "between the cut and the rotation."
                   % (f["meshes"], f["triangles"], f["components"], *f["spacing_mm"]))),
    },
    "legend": {
        "ja": ("凡例つきの計測表 ―― どの色がどの粒子か",
               lambda f: (
                   "色分けした図は、凡例が無ければ「きれいなだけ」で終わる。%d 粒子の色見本・"
                   "体積 mm3・全体比・等価直径・球形度・伸長度・視野端への接触を並べた。"
                   "総体積 %.4f mm3、比率の合計 %.6f。1 ボクセル = %.6f mm3。"
                   "最大は %s の %.4f mm3、最小は %s の %.4f mm3。"
                   % (f["components"], f["total_volume_mm3"], f["share_sum"],
                      f["voxel_volume_mm3"], f["largest"]["hex"],
                      f["largest"]["volume_mm3"], f["smallest"]["hex"],
                      f["smallest"]["volume_mm3"]))),
        "en": ("A measurement table with its legend — which colour is which particle",
               lambda f: (
                   "A colour-coded figure without a legend is merely decorative. This table "
                   "lists all %d particles: swatch, volume in mm3, share of the total, "
                   "equivalent diameter, sphericity, elongation and whether the particle "
                   "touches the field of view. Total %.4f mm3, shares summing to %.6f, one "
                   "voxel = %.6f mm3. The largest is %s at %.4f mm3, the smallest %s at "
                   "%.4f mm3."
                   % (f["components"], f["total_volume_mm3"], f["share_sum"],
                      f["voxel_volume_mm3"], f["largest"]["hex"],
                      f["largest"]["volume_mm3"], f["smallest"]["hex"],
                      f["smallest"]["volume_mm3"]))),
    },
}

INTRO = {
    "ja": [
        "生成元: `tools/gen_wingvox_gallery.py`(`py -3.11 tools/gen_wingvox_gallery.py`)。",
        "画像はすべて fullseye の op(`volcolor` / `volops` / `render3d`)と numpy 合成で",
        "描いており(matplotlib 不使用)、図に焼いた数値は 1 つ残らずその場で op を呼んで",
        "得た実測値である。乱数は seed 固定・幾何も固定なので再生成でバイト列が一致する",
        "(`--verify` で検査)。",
        "",
        "このウィングの主張は 1 つ ―― **3-D のラベルは、切る前に色を付けなければならない**。",
        "断面ごとに色を付けるとラベル番号が断面ごとに振り直され、同じ部品が層ごとに",
        "別の色になる。展示 2 がその差を本数で示す。",
    ],
    "en": [
        "Generated by `tools/gen_wingvox_gallery.py` (`py -3.11 tools/gen_wingvox_gallery.py`).",
        "Every image is drawn with fullseye's own ops (`volcolor` / `volops` / `render3d`)",
        "and numpy compositing — no matplotlib — and every number burned into a figure was",
        "measured by calling the op at generation time. Seeds and geometry are fixed, so a",
        "regeneration is byte-identical (checked with `--verify`).",
        "",
        "This wing makes one claim: **a 3-D labelling has to be coloured before it is cut.**",
        "Colour each slice on its own and the numbering is redrawn every slice, so the same",
        "part comes out a different colour layer by layer. Exhibit 2 counts that difference.",
    ],
}

TITLE = {"ja": "ボクセルの色分けウィング ―― 展示キャプション原稿",
         "en": "The Voxel-Colouring Wing — exhibit caption drafts"}


def _write_exhibit_md(results: dict, lang: str, log) -> str:
    """キャプション原稿を書く。記事本体(docs/articles/*.md)には一切触れない。"""
    os.makedirs(EXHIBITS, exist_ok=True)
    path = os.path.join(EXHIBITS, "wingvox.%s.md" % lang)
    gen = ("tools/gen_wingvox_gallery.py が自動生成。記事 md への挿入候補であり、"
           "このファイル自体は記事ではない。数値はすべて生成時の実測値。")
    lines = ["<!-- %s -->" % gen, "", "# %s" % TITLE[lang], ""] + INTRO[lang] + [""]
    lines += [
        "束ね方は `tools/exhibit_tile.py` の 3 種に従う。静止画の Markdown は"
        if lang == "ja" else
        "Bundling follows the three forms in `tools/exhibit_tile.py`. Stills are shown",
        "すべて **サムネイル表示 + クリックで原寸** の形で出してある。"
        if lang == "ja" else
        "as **a thumbnail linking to the full-size PNG**.",
        "",
    ]
    for i, (name, _) in enumerate(EXHIBIT_ORDER, start=1):
        if name not in results:
            continue
        info, facts = results[name]["info"], results[name]["facts"]
        title, text = CAPTIONS[name][lang]
        ops = ", ".join("`%s`" % o for o in facts["ops"])
        stem = info["stem"]
        tail = "使用 op: %s。" % ops if lang == "ja" else "Ops used: %s." % ops
        caption = "**%s** ―― %s %s" % (title, text(facts), tail)
        lines.append("## %d. %s" % (i, title))
        lines.append("")
        if info["kind"] == "gif":
            lines.append(markdown_animation(stem, title, caption).rstrip())
            lines.append("")
            lines.append("- GIF: `docs/articles/assets/media/%s.gif` (%d %s, %dx%d px, "
                         "%.2f MB)" % (stem, info["frames"],
                                       "コマ" if lang == "ja" else "frames",
                                       info["shape"][1], info["shape"][0],
                                       info["bytes"] / 1e6))
            lines.append("- %s: `docs/articles/assets/thumbs/%s_thumb.jpg`"
                         % ("サムネ" if lang == "ja" else "Thumbnail", stem))
        else:
            lines.append(markdown(stem, title, caption).rstrip())
            lines.append("")
            kind_txt = ({"sheet": "タイル", "still": "原寸 1 枚"}[info["kind"]]
                        if lang == "ja"
                        else {"sheet": "contact sheet", "still": "full size"}[info["kind"]])
            extra = (", %d %s / %d %s" % (info["frames"],
                                          "パネル" if lang == "ja" else "panels",
                                          info["ncols"],
                                          "列" if lang == "ja" else "columns")
                     if info["kind"] == "sheet" else "")
            lines.append("- PNG (%s): `docs/articles/assets/%s.png` (%dx%d px, %.0f kB%s)"
                         % (kind_txt, stem, info["shape"][1], info["shape"][0],
                            info["bytes"] / 1e3, extra))
            lines.append("- %s: `docs/articles/assets/%s_thumb.jpg` (%.0f kB)"
                         % ("サムネ(記事はこちらを表示)" if lang == "ja"
                            else "Thumbnail (shown in the article)",
                            stem, info["thumb_bytes"] / 1e3))
        lines.append("- %s: %s" % ("束ね方" if lang == "ja" else "Bundling",
                                   BUNDLING[name]))
        lines.append("- SHA-256: `%s`" % info["sha256"])
        lines.append("")
        lines.append("<details><summary>%s</summary>"
                     % ("この図に焼いた実測値" if lang == "ja"
                        else "The measured values burned into this figure"))
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps({k: v for k, v in facts.items() if k != "ops"},
                                indent=1, ensure_ascii=False, default=float))
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    log("[md] %s (%d bytes)" % (path, os.path.getsize(path)))
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default="", help="生成する展示をカンマ区切りで指定")
    ap.add_argument("--verify", action="store_true", help="2 回生成して SHA-256 を照合")
    ap.add_argument("--no-captions", action="store_true", help="キャプション原稿を書かない")
    args = ap.parse_args()

    def log(msg):
        print(msg, flush=True)

    want = ({s.strip() for s in args.only.split(",") if s.strip()}
            or {n for n, _ in EXHIBIT_ORDER})
    unknown = want - {n for n, _ in EXHIBIT_ORDER}
    if unknown:
        log("unknown exhibit(s): %s" % sorted(unknown))
        return 2
    os.makedirs(MEDIA, exist_ok=True)

    def build_all():
        out = {}
        for name, fn in EXHIBIT_ORDER:
            if name not in want:
                continue
            log("[build] %s" % name)
            t = time.time()
            info, facts = fn(log)
            out[name] = {"info": info, "facts": facts}
            log("    (%.1f s)" % (time.time() - t))
        return out

    t0 = time.time()
    results = build_all()
    if not args.no_captions:
        for lang in ("ja", "en"):
            _write_exhibit_md(results, lang, log)

    if args.verify:
        log("[verify] regenerating to check the bytes are identical")
        first = {n: results[n]["info"]["sha256"] for n in results}
        again = build_all()
        bad = [n for n in first if again[n]["info"]["sha256"] != first[n]]
        for n in sorted(first):
            same = again[n]["info"]["sha256"] == first[n]
            log("    %s %s  %s..." % ("OK  " if same else "DIFF", n, first[n][:16]))
        if bad:
            log("[verify] NOT deterministic: %s" % bad)
            return 1
        log("[verify] all %d outputs are byte-identical on regeneration" % len(first))

    log("=== done in %.1f s ===" % (time.time() - t0))
    total = 0
    for n, r in results.items():
        i = r["info"]
        total += i["bytes"]
        log("  %-16s %-6s %3d frame(s)  %dx%d  %6.3f MB  %s"
            % (n, i["kind"], i["frames"], i["shape"][1], i["shape"][0],
               i["bytes"] / 1e6, i["sha256"][:12]))
    log("  total %.2f MB in %d exhibits" % (total / 1e6, len(results)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
