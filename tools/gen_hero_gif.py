#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_hero_gif — README / GitHub Pages の**扉絵アニメーション**を作る。

出力は 2 つだけ::

    docs/articles/assets/fullseye_hero.gif          # 960x360 のループ動画
    docs/articles/assets/fullseye_hero_poster.png   # その 1 フレーム目(静止代替)

**方針(``tools/gen_banner.py`` と同じ)**: モックアップ・手描き・AI 生成画像を
一切使わない。全フレームが Fullseye の op を実際に通した出力である。外部データも
同梱しない —— 入力はすべてこのスクリプトの中で numpy と Fullseye の合成 op から
組み立てる。図注・ラベル・軸・折れ線も Fullseye の annotate 族
(``text_box`` / ``axes_transform`` / ``plot_series`` / ``axes_frame`` / ``ticks``)
で描き、matplotlib のような外部の作図ライブラリは使わない。書き出しは
``fullseye.write_video``(``.gif`` は Pillow 経路)で、自前のエンコーダは書かない。

**6 幕構成**(幕ごとに必ずパラメータが動く。静止画のクロスフェード集にしない)::

    1 エッジと方位     部品が回りながら sobel_amp のしきい値が動く
    2 連結成分         面積しきい値を上げると残る物体が減っていく
    3 サブピクセル計測 キャリパーがテーパ軸の上を走り、測った幅が伸びる
    4 3-D              smooth-union の丸め半径 k が動き、視点が 1 周する
    5 点群             クラスタ許容距離 tol が動き、視点が 1 周する
    6 光学             ダブレットのデフォーカスを通し抜け、コントラストが山を描く

**決定論**: 乱数はすべて固定 seed の ``RandomState``。2 回走らせると GIF は
バイト一致する(``--out`` に別名を渡して SHA-256 を比べれば確かめられる)。

**容量のための調整(4 MB 上限に対して実際にやったこと)**:

* (a) 色数を落とした —— 全フレームを **RGB 各 6 段(6^3 = 216 色)に一様量子化**
  してから書き出す。216 <= 256 なので Pillow の GIF パレットはこの色をそのまま
  取り、① LZW が効いて容量が落ち、② **ポスター PNG が GIF の 1 フレーム目と
  ビット単位で一致する**(24 bit PNG と 8 bit GIF の往復で色が動かない)。
  副作用として陰影に段が出る —— 3-D の球面と光学パネルで見える。隠さず書く。
  ``--levels`` で段数を変えられる(7 以上は 256 色を超え、Pillow が独自に
  再量子化するのでポスター一致が壊れる。既定の 6 から上げないこと)。
* (b) フレーム数は 1 幕 22 枚 + 幕間クロスフェード 5 枚 x 6 = **162 枚**
  (fps 12 = 13.5 秒)。仕様の 120〜170 枚の範囲内で下寄りに取ってある。
* (c) 寸法は 960x360 のまま落としていない。

使い方::

    py -3.11 tools/gen_hero_gif.py
    py -3.11 tools/gen_hero_gif.py --out /tmp/again.gif      # 決定論の確認用
    py -3.11 tools/gen_hero_gif.py --acts edges,blobs        # 幕を絞って試す
"""
from __future__ import annotations

# repo をそのまま clone した状態(pip install -e . 前)でも動くようにする。
# gen_banner.py と同じ理由 —— 裸の起動コマンドを docs が載せているため。
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import argparse
import copy
import hashlib
import time
from pathlib import Path

import numpy as np

import fullseye as fs

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "articles" / "assets"
GIF_PATH = ASSETS / "fullseye_hero.gif"
POSTER_PATH = ASSETS / "fullseye_hero_poster.png"

# --------------------------------------------------------------------------- #
# 版面                                                                          #
# --------------------------------------------------------------------------- #
W, H = 960, 360
TOP_H = 26                      # 上帯(作品名・pip install。全幕で不変)
BOT_H = 34                      # 下帯(幕の題と使った op 名)
CONTENT_H = H - TOP_H - BOT_H   # 300
PANEL = 288                     # 正方パネルの一辺(24 + 288*3 + 24*2 + 24 = 960)
PANEL_X = (24, 336, 648)
PANEL_Y = TOP_H + 6

FPS = 12
FRAMES_PER_ACT = 22
FADE = 5
LEVELS = 6                      # RGB 各チャンネルの量子化段数(6^3 = 216 色)

BG = 0.955                      # 明るい地。GIF の平坦部が伸び、平均輝度も稼げる
PANEL_BG = 1.0
INK = (0.16, 0.17, 0.19)


# --------------------------------------------------------------------------- #
# 小道具                                                                        #
# --------------------------------------------------------------------------- #
def _rgb(a):
    """(H,W) か (H,W,3) を (H,W,3) float [0,1] に揃える。"""
    a = np.asarray(a, float)
    if a.ndim == 2:
        a = np.repeat(a[:, :, None], 3, axis=2)
    return np.clip(a, 0.0, 1.0)


def _fit(a, size=PANEL):
    """パネル一辺に最近傍で合わせる(拡大縮小は整数比でなくてよい)。"""
    a = _rgb(a)
    h, w = a.shape[:2]
    if (h, w) == (size, size):
        return a
    ri = np.clip((np.arange(size) * (h / size)).astype(int), 0, h - 1)
    ci = np.clip((np.arange(size) * (w / size)).astype(int), 0, w - 1)
    return a[ri][:, ci]


def _content():
    return np.full((CONTENT_H, W, 3), BG, float)


def _place(canvas, img, ix, y=6, size=PANEL):
    """パネル ix(0/1/2)に画像を置き、細い枠を引く。"""
    x = PANEL_X[ix]
    canvas[y:y + size, x:x + size] = _fit(img, size)
    pts = [(x - 1, y - 1), (x + size, y - 1), (x + size, y + size), (x - 1, y + size)]
    return fs.draw_polyline(canvas, pts, color=(0.72, 0.74, 0.76), width=1, closed=True)


def _wide_rect(ix0, ix1):
    """パネル ix0..ix1 をまたぐ矩形 (x, y, w, h)。"""
    x = PANEL_X[ix0]
    w = PANEL_X[ix1] + PANEL - x
    return x, 6, w, PANEL


def _cap(canvas, ix, text, size=PANEL, y=6):
    """パネル左下の図注(fullseye の text_box)。"""
    return fs.text_box(canvas, text, (PANEL_X[ix] + 7, y + size - 7), anchor="lb",
                       font_size=13, box_alpha=0.78, box_color=(1.0, 1.0, 1.0),
                       text_color=INK, min_contrast=1.05)


def _plot_panel(canvas, rect, xlim, ylim, xlabel, ylabel):
    """白い作図パネル(枠 + 目盛り)を置き、axes 辞書を返す。"""
    x, y, w, h = rect
    canvas[y:y + h, x:x + w] = PANEL_BG
    canvas = fs.draw_polyline(canvas, [(x - 1, y - 1), (x + w, y - 1), (x + w, y + h),
                                       (x - 1, y + h)], color=(0.72, 0.74, 0.76),
                              width=1, closed=True)
    inner = (x + 52, y + 20, w - 72, h - 54)
    axes = fs.axes_transform(inner, xlim, ylim)
    canvas = fs.axes_frame(canvas, axes, color=(0.55, 0.57, 0.60), width=1, box=False)
    canvas = fs.ticks(canvas, axes, xticks=fs.nice_ticks(*xlim, 4),
                      yticks=fs.nice_ticks(*ylim, 4), color=(0.55, 0.57, 0.60),
                      font_size=10, text_color=INK)
    canvas = fs.text_box(canvas, xlabel, (x + w // 2, y + h - 6), anchor="cb",
                         font_size=11, box_alpha=0.0, text_color=INK, min_contrast=1.05)
    canvas = fs.text_box(canvas, ylabel, (x + 6, y + 8), anchor="lt",
                         font_size=11, box_alpha=0.0, text_color=INK, min_contrast=1.05)
    return canvas, axes


def _base_frame(title, ops):
    """上帯・下帯を焼いた台紙(幕ごとに 1 枚だけ作って使い回す)。"""
    f = np.full((H, W, 3), BG, float)
    f[:TOP_H] = 0.13
    f[H - BOT_H:] = 0.965
    f = fs.text_box(f, "fullseye", (22, TOP_H // 2), anchor="lm", font_size=16,
                    box_alpha=0.0, text_color=(0.95, 0.96, 0.97), min_contrast=1.05)
    f = fs.text_box(f, "numpy-native image / 3-D operators  ·  pip install fullseye",
                    (W - 22, TOP_H // 2), anchor="rm", font_size=13, box_alpha=0.0,
                    text_color=(0.72, 0.76, 0.80), min_contrast=1.05)
    f = fs.draw_line(f, (0, H - BOT_H), (W - 1, H - BOT_H), color=(0.80, 0.82, 0.84), width=1)
    f = fs.text_box(f, title, (22, H - BOT_H // 2), anchor="lm", font_size=15,
                    box_alpha=0.0, text_color=INK, min_contrast=1.05)
    f = fs.text_box(f, ops, (W - 22, H - BOT_H // 2), anchor="rm", font_size=12,
                    box_alpha=0.0, text_color=(0.38, 0.40, 0.43), min_contrast=1.05)
    return f


def _compose(base, contents):
    out = []
    for c in contents:
        f = base.copy()
        f[TOP_H:TOP_H + CONTENT_H] = c
        out.append(f)
    return out


def _crossfade(a, b, n=FADE):
    """a の最終フレーム → b の先頭フレームを n 枚で繋ぐ(両端は含まない)。"""
    return [(1.0 - w) * a + w * b for w in (np.arange(1, n + 1) / (n + 1.0))]


def _quantize(frames, levels=LEVELS):
    """RGB 各チャンネルを ``levels`` 段へ一様量子化(容量対策 (a) / 上の docstring)。"""
    q = float(levels - 1)
    return [np.round(np.clip(f, 0.0, 1.0) * q) / q for f in frames]


# --------------------------------------------------------------------------- #
# 幕 1 — エッジと方位                                                           #
# --------------------------------------------------------------------------- #
def _plate(size, ang):
    """回る合成部品(穴・キー溝・歯つき)。2 倍で作って平均 = アンチエイリアス。"""
    ss = 2
    n = size * ss
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    x = (xx - (n - 1) / 2.0) / (n / 2.0)
    y = (yy - (n - 1) / 2.0) / (n / 2.0)
    ca, sa = np.cos(ang), np.sin(ang)
    u, v = ca * x + sa * y, -sa * x + ca * y
    img = np.full((n, n), 0.10)
    img[(np.abs(u) ** 4 + np.abs(v) ** 4) < 0.70 ** 4] = 0.80
    r = np.hypot(u, v)
    th = np.arctan2(v, u)
    img[(r > 0.50) & (r < 0.63) & (np.sin(th * 18.0) > 0.2)] = 0.42
    for hu, hv in ((0.44, 0.44), (-0.44, 0.44), (0.44, -0.44), (-0.44, -0.44)):
        img[(u - hu) ** 2 + (v - hv) ** 2 < 0.095 ** 2] = 0.16
    img[r < 0.23] = 0.18
    img[(np.abs(u) < 0.05) & (v > 0.18) & (v < 0.40)] = 0.18
    return img.reshape(size, ss, size, ss).mean(axis=(1, 3))


def act_edges(nf):
    scenes = [_plate(224, 2.0 * np.pi * i / nf) for i in range(nf)]
    amps = [fs.op.sobel_amp(s) for s in scenes]
    dirs = [fs.op.sobel_dir(s) for s in scenes]
    amax = max(float(a.max()) for a in amps)            # 全フレーム共通の正規化
    out = []
    for i in range(nf):
        # しきい値は 1 周期の sin で往復 = 幕の中で閉じる
        thr = 0.22 + 0.16 * np.sin(2.0 * np.pi * i / nf)
        a = amps[i] / amax
        c = _content()
        c = _place(c, scenes[i], 0)
        edge = np.where(a > thr, 0.10, 0.99)
        c = _place(c, edge, 1)
        hue = fs.apply_cmap(dirs[i], "hsv", vmin=0.0, vmax=1.0)
        hue = np.where((a > 0.10)[:, :, None], hue, 0.99)
        c = _place(c, hue, 2)
        c = _cap(c, 0, "(a) 合成シーン  回転 %3.0f°" % (360.0 * i / nf))
        c = _cap(c, 1, "(b) sobel_amp > %.3f" % thr)
        c = _cap(c, 2, "(c) sobel_dir を色相に")
        out.append(c)
    return out, "1 / 6  エッジと方位 — 勾配の強さと向き", "op.sobel_amp · op.sobel_dir · apply_cmap"


# --------------------------------------------------------------------------- #
# 幕 2 — 連結成分                                                               #
# --------------------------------------------------------------------------- #
def _blob_scene(size=256):
    rs = np.random.RandomState(20260906)
    img = np.full((size, size), 0.10)
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    for _ in range(90):                                  # 丸い部品
        r = rs.uniform(4.0, 15.0)
        cy, cx = rs.uniform(r + 2, size - r - 2, 2)
        img[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = 0.85
    for _ in range(14):                                  # 細長い切り粉
        cy, cx = rs.uniform(20, size - 20, 2)
        ang = rs.uniform(0, np.pi)
        L, hw = rs.uniform(14, 34), rs.uniform(1.2, 2.2)
        s = (yy - cy) * np.sin(ang) + (xx - cx) * np.cos(ang)
        d = -(yy - cy) * np.cos(ang) + (xx - cx) * np.sin(ang)
        img[(np.abs(s) < L / 2) & (np.abs(d) < hw)] = 0.85
    return img


def act_blobs(nf):
    img = _blob_scene()
    lab = fs.ledger.blob_label(img > 0.5)
    feat = fs.ledger.blob_features(lab)
    amax = float(np.max(feat["area"]))
    thrs = np.linspace(1.0, 0.62 * amax, nf)
    sels = [fs.ledger.blob_select(lab, "area", vmin=float(t)) for t in thrs]
    counts = [int(s.max()) for s in sels]
    all_view = fs.ledger.blob_overlay(img, lab)
    out = []
    for i in range(nf):
        c = _content()
        c = _place(c, all_view, 0)
        c = _place(c, fs.ledger.blob_overlay(img, sels[i]), 1)
        c, ax = _plot_panel(c, _wide_rect(2, 2), (0.0, float(thrs[-1])),
                            (0.0, float(counts[0]) * 1.08),
                            "面積のしきい値 [px²]", "残った物体")
        c = fs.plot_series(c, ax, thrs[:i + 1], np.asarray(counts[:i + 1], float),
                           kind="line", color="emphasis", width=2)
        c = _cap(c, 0, "(a) blob_label — %d 個" % feat["n"])
        c = _cap(c, 1, "(b) blob_select area ≥ %.0f px² — %d 個" % (thrs[i], counts[i]))
        out.append(c)
    return out, "2 / 6  連結成分 — 測って選ぶ", "blob_label · blob_features · blob_select · blob_overlay"


# --------------------------------------------------------------------------- #
# 幕 3 — サブピクセル計測                                                       #
# --------------------------------------------------------------------------- #
BAR_ANG = np.deg2rad(14.0)      # 画面上の軸の傾き(+col から +row 向きが正)


def _taper_scene(size=256):
    """テーパのついた明るい軸。幅は軸に沿って線形に太る(= 測る意味がある)。"""
    ss = 2
    n = size * ss
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    cy = cx = (n - 1) / 2.0
    sa, ca = np.sin(BAR_ANG), np.cos(BAR_ANG)
    s = (yy - cy) * sa + (xx - cx) * ca          # 軸方向
    d = -(yy - cy) * ca + (xx - cx) * sa         # 幅方向
    half = ss * (13.0 + 11.0 * (s / (ss * 100.0) + 1.0) / 2.0)
    img = np.full((n, n), 0.14)
    img += 0.05 * (yy / n)                        # ゆるい照明むら
    img[(np.abs(d) < half) & (np.abs(s) < ss * 100.0)] = 0.86
    rs = np.random.RandomState(4242)
    img += rs.normal(0.0, 0.010, img.shape)
    return np.clip(img.reshape(size, ss, size, ss).mean(axis=(1, 3)), 0.0, 1.0)


def act_caliper(nf):
    img = _taper_scene()
    size = img.shape[0]
    cy = cx = (size - 1) / 2.0
    sa, ca = np.sin(BAR_ANG), np.cos(BAR_ANG)
    phi = BAR_ANG + np.pi / 2.0                   # 軸に直交する測定線
    # 軸に沿って -78 → +78 px を往復(幕の中で閉じる)
    travel = 78.0 * np.sin(2.0 * np.pi * np.arange(nf) / nf)
    widths, views, profs = [], [], []
    for t in travel:
        r0, c0 = cy + t * sa, cx + t * ca
        m = fs.ledger.gen_measure_rectangle2(r0, c0, phi, 34.0, 5.0, img.shape)
        pairs = fs.ledger.measure_pairs(img, m, sigma=1.0, threshold=0.10)
        edges = fs.ledger.measure_pos(img, m, sigma=1.0, threshold=0.10)
        widths.append(float(pairs[0]["width"]) if pairs else np.nan)
        # 測定矩形の外形と検出エッジを描く(すべて fullseye の描画 op)
        v = _rgb(img)
        hs, hc = np.sin(phi), np.cos(phi)
        L2, W2 = 34.0, 5.0
        corners = [(c0 + L2 * hc - W2 * hs, r0 + L2 * hs + W2 * hc),
                   (c0 + L2 * hc + W2 * hs, r0 + L2 * hs - W2 * hc),
                   (c0 - L2 * hc + W2 * hs, r0 - L2 * hs - W2 * hc),
                   (c0 - L2 * hc - W2 * hs, r0 - L2 * hs + W2 * hc)]
        v = fs.draw_polyline(v, corners, color=(0.98, 0.62, 0.05), width=1, closed=True)
        v = fs.draw_line(v, (c0 - L2 * hc, r0 - L2 * hs), (c0 + L2 * hc, r0 + L2 * hs),
                         color=(0.98, 0.62, 0.05), width=1)
        if edges:
            pts = [(e["col"], e["row"]) for e in edges]
            v = fs.draw_markers(v, pts, color=(0.05, 0.45, 0.85), size=7, shape="cross",
                                width=2)
        views.append(v)
        profs.append(fs.line_profile(img, (r0 - L2 * hs, c0 - L2 * hc),
                                     (r0 + L2 * hs, c0 + L2 * hc), num=69))
    wa = np.asarray(widths, float)
    out = []
    for i in range(nf):
        c = _content()
        c = _place(c, views[i], 0)
        p = profs[i]
        c, ax = _plot_panel(c, _wide_rect(1, 1), (0.0, float(len(p) - 1)), (0.0, 1.0),
                            "測定線上の位置 [px]", "グレー値")
        c = fs.plot_series(c, ax, np.arange(len(p), dtype=float), np.clip(p, 0.0, 1.0),
                           kind="line", color="reference", width=2)
        c, ax2 = _plot_panel(c, _wide_rect(2, 2), (0.0, float(nf - 1)),
                             (float(np.nanmin(wa)) - 2.0, float(np.nanmax(wa)) + 2.0),
                             "フレーム", "測った幅 [px]")
        c = fs.plot_series(c, ax2, np.arange(i + 1, dtype=float), wa[:i + 1],
                           kind="line", color="emphasis", width=2)
        c = _cap(c, 0, "(a) キャリパー phi=%.0f°  走査 %+.0f px" % (np.rad2deg(phi), travel[i]))
        c = _cap(c, 1, "(b) measure_pos — エッジ %d 点" % int(np.sum(np.isfinite(p)) > 0
                                                            and len(fs.ledger.measure_pos(
                                                                img, fs.ledger.gen_measure_rectangle2(
                                                                    cy + travel[i] * sa,
                                                                    cx + travel[i] * ca,
                                                                    phi, 34.0, 5.0, img.shape),
                                                                sigma=1.0, threshold=0.10))))
        c = _cap(c, 2, "(c) measure_pairs — 幅 %.2f px" % wa[i])
        out.append(c)
    return out, "3 / 6  サブピクセル計測 — 測定線とキャリパー", \
        "gen_measure_rectangle2 · measure_pos · measure_pairs · line_profile"


# --------------------------------------------------------------------------- #
# 幕 4 — 3-D(SDF → マーチングキューブス → レンダ)                              #
# --------------------------------------------------------------------------- #
def act_sdf3d(nf):
    n = 56
    lin = np.linspace(-1.25, 1.25, n)
    grid = np.stack(np.meshgrid(lin, lin, lin, indexing="ij"), axis=-1)
    sph = fs.ledger.sphere_sdf(grid, (0.0, 0.0, -0.18), 0.66)
    box = fs.ledger.box_sdf(grid, (0.0, 0.0, 0.46), (0.40, 0.40, 0.40))
    out = []
    for i in range(nf):
        t = i / nf
        k = 0.18 + 0.13 * np.sin(2.0 * np.pi * t)        # 継ぎ目の丸め半径が動く
        fld = fs.ledger.sdf_smooth_union(sph, box, float(k))
        V, F = fs.marching_cubes(fld, level=0.0)
        # 視点は 1 周(端で戻らないので幕がループする)
        az = 2.0 * np.pi * t
        rad = 1.9 * n
        eye = (n / 2 + rad * np.cos(az), n / 2 + rad * np.sin(az), n / 2 + 0.85 * n)
        pose = fs.look_at(eye, (n / 2, n / 2, n / 2), up=(0, 0, 1))
        K = fs.intrinsics_from_fov(38.0, PANEL, PANEL)
        beauty = fs.ledger.render_beauty(V, F, pose=pose, intrinsics=K, size=PANEL, ss=2,
                                         light=(0.5, -0.7, 0.9), albedo=(0.62, 0.66, 0.72),
                                         material="plastic", ao=True, ground_shadow=False,
                                         background=(1.0, 1.0, 1.0), tonemap="aces")
        pts = fs.mesh_sample_points(V, F, n=9000, method="area", seed=0)
        # look_at は -Z を見る OpenGL 流。project_points は +Z が前なので y/z を反転する
        flip = np.diag([1.0, -1.0, -1.0])
        depth = fs.ledger.render_point_depth(pts, K, (PANEL, PANEL),
                                             R=flip @ pose[:3, :3], t=flip @ pose[:3, 3])
        dv = np.where(depth > 0, depth, np.nan)
        lo, hi = 1.25 * n, 2.75 * n
        dimg = fs.apply_cmap(dv, "viridis", vmin=lo, vmax=hi, invalid=(1.0, 1.0, 1.0))
        sl = fld[:, :, n // 2]
        sv = fs.apply_cmap(sl, "coolwarm", vmin=-0.7, vmax=0.7)
        c = _content()
        c = _place(c, sv, 0)
        c = _place(c, beauty, 1)
        c = _place(c, dimg, 2)
        c = _cap(c, 0, "(a) SDF 断面  k = %.3f" % k)
        c = _cap(c, 1, "(b) render_beauty  方位 %3.0f°  三角形 %d" % (np.rad2deg(az), len(F)))
        c = _cap(c, 2, "(c) 表面サンプルの深度")
        out.append(c)
    return out, "4 / 6  3-D — 距離場から三角形へ", \
        "sphere_sdf · box_sdf · sdf_smooth_union · marching_cubes · render_beauty"


# --------------------------------------------------------------------------- #
# 幕 5 — 点群(地面除去 → クラスタリング)                                       #
# --------------------------------------------------------------------------- #
def _lidar_scene():
    rs = np.random.RandomState(1234)
    ground = np.column_stack([rs.uniform(-3.2, 3.2, 3600), rs.uniform(-3.2, 3.2, 3600),
                              rs.normal(0.0, 0.006, 3600)])
    objs = []
    for (ox, oy), (rad, hgt) in zip([(-1.5, 0.9), (1.3, -0.7), (0.3, 1.9), (-1.0, -1.7)],
                                    [(0.34, 0.95), (0.48, 0.62), (0.26, 1.25), (0.40, 0.75)]):
        m = 620
        th = rs.uniform(0.0, 2.0 * np.pi, m)
        z = rs.uniform(0.0, hgt, m)
        objs.append(np.column_stack([ox + rad * np.cos(th) + rs.normal(0, 0.01, m),
                                     oy + rad * np.sin(th) + rs.normal(0, 0.01, m), z]))
    return np.vstack([ground] + objs)


def act_pointcloud(nf):
    pts = _lidar_scene()
    nonground, gmask = fs.remove_ground(pts, thresh=0.05, iters=120, seed=0)
    tols = 0.16 + 0.10 * np.sin(2.0 * np.pi * np.arange(nf) / nf)   # 幕の中で閉じる
    clusters = [fs.euclidean_clusters(nonground, tol=float(t), min_size=60) for t in tols]
    ncl = [len(c) for c in clusters]
    palette = fs.colorize_labels(np.arange(1, 9, dtype=np.int32)[None, :], seed=3)[0]
    K = fs.intrinsics_from_fov(42.0, PANEL, PANEL)
    flip = np.diag([1.0, -1.0, -1.0])
    out = []
    for i in range(nf):
        az = 2.0 * np.pi * i / nf
        eye = (6.4 * np.cos(az), 6.4 * np.sin(az), 3.4)
        pose = fs.look_at(eye, (0.0, 0.0, 0.45), up=(0, 0, 1))
        R, t = flip @ pose[:3, :3], flip @ pose[:3, 3]

        def uv_of(p):
            u, z = fs.project_points(p, K, R=R, t=t)
            ok = (z > 0) & (u[:, 0] > 1) & (u[:, 0] < PANEL - 2) & \
                 (u[:, 1] > 1) & (u[:, 1] < PANEL - 2)
            return u[ok], z[ok]

        raw = np.full((PANEL, PANEL, 3), 1.0)
        u, _ = uv_of(pts)
        raw = fs.draw_markers(raw, u, color=(0.42, 0.45, 0.50), size=1, shape="dot")
        seg = np.full((PANEL, PANEL, 3), 1.0)
        ug, _ = uv_of(pts[gmask])
        seg = fs.draw_markers(seg, ug, color=(0.84, 0.85, 0.87), size=1, shape="dot")
        for j, idx in enumerate(clusters[i]):
            uc, _ = uv_of(nonground[idx])
            if len(uc) == 0:
                continue
            seg = fs.draw_markers(seg, uc, color=tuple(palette[j % 8]), size=2, shape="dot")
        c = _content()
        c = _place(c, raw, 0)
        c = _place(c, seg, 1)
        c, ax = _plot_panel(c, _wide_rect(2, 2), (0.0, float(nf - 1)), (0.0, max(ncl) + 1.0),
                            "フレーム(tol が往復する)", "クラスタ数")
        c = fs.plot_series(c, ax, np.arange(i + 1, dtype=float),
                           np.asarray(ncl[:i + 1], float), kind="line",
                           color="emphasis", width=2)
        c = _cap(c, 0, "(a) 生の点群 %d 点" % len(pts))
        c = _cap(c, 1, "(b) euclidean_clusters tol=%.3f m — %d 個" % (tols[i], ncl[i]))
        out.append(c)
    return out, "5 / 6  点群 — 地面を外してかたまりに切る", \
        "remove_ground · euclidean_clusters · project_points · colorize_labels"


# --------------------------------------------------------------------------- #
# 幕 6 — 光学(ダブレットのデフォーカス通し抜け)                                 #
# --------------------------------------------------------------------------- #
def _siemens(size=224):
    ss = 2
    n = size * ss
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    cy = cx = (n - 1) / 2.0
    r = np.hypot(yy - cy, xx - cx) / (n / 2.0)
    th = np.arctan2(yy - cy, xx - cx)
    img = np.full((n, n), 0.06)
    img[(r < 0.92) & (np.sin(th * 20.0) > 0.0)] = 0.95
    img[r < 0.10] = 0.95
    return img.reshape(size, ss, size, ss).mean(axis=(1, 3))


def act_optics(nf):
    target = _siemens()
    base = fs.example_system("doublet")
    bfl = fs.paraxial_trace(base)["bfl"]
    # 焦点を通り抜ける = -1.6 → +1.6 mm。sin 掃引で幕の中を往復して閉じる
    dz = 1.6 * np.sin(2.0 * np.pi * np.arange(nf) / nf)
    imgs, contrast = [], []
    for d in dz:
        sysd = copy.deepcopy(base)
        sysd["image_mm"] = float(bfl + d)
        im = fs.render_through_lens(target, sysd, pixel_pitch_um=5.5, field_of_view=3.0,
                                    zones=3)
        imgs.append(im)
        contrast.append(float(fs.stat_describe(im.ravel())["std"]))
    vmax = max(float(a.max()) for a in imgs)             # 全フレーム共通の露出
    cmax = max(contrast)
    out = []
    for i in range(nf):
        c = _content()
        c = _place(c, target, 0)
        c = _place(c, np.clip(imgs[i] / vmax, 0.0, 1.0), 1)
        c, ax = _plot_panel(c, _wide_rect(2, 2), (-1.7, 1.7), (0.0, cmax * 1.12),
                            "デフォーカス [mm]", "RMS コントラスト")
        order = np.argsort(dz[:i + 1])
        c = fs.plot_series(c, ax, dz[:i + 1][order],
                           np.asarray(contrast[:i + 1], float)[order],
                           kind="scatter", color="emphasis", marker_size=3)
        c = _cap(c, 0, "(a) 理想像(シーメンススター)")
        c = _cap(c, 1, "(b) render_through_lens  Δz = %+.2f mm" % dz[i])
        out.append(c)
    return out, "6 / 6  光学 — ダブレットを通した像", \
        "example_system · paraxial_trace · render_through_lens · stat_describe"


ACTS = {
    "edges": act_edges,
    "blobs": act_blobs,
    "caliper": act_caliper,
    "sdf3d": act_sdf3d,
    "pointcloud": act_pointcloud,
    "optics": act_optics,
}
ORDER = ("edges", "blobs", "caliper", "sdf3d", "pointcloud", "optics")


# --------------------------------------------------------------------------- #
def build(names, nf):
    acts = []
    for name in names:
        t0 = time.time()
        contents, title, ops = ACTS[name](nf)
        acts.append(_compose(_base_frame(title, ops), contents))
        print("  幕 %-11s %2d 枚  %5.1f s" % (name, len(contents), time.time() - t0))
    frames = []
    for i, seq in enumerate(acts):
        frames.extend(seq)
        nxt = acts[(i + 1) % len(acts)]                  # 最後は先頭へ戻す = ループ
        frames.extend(_crossfade(seq[-1], nxt[0]))
    return frames


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(GIF_PATH), help="GIF の出力先")
    ap.add_argument("--poster", default=None, help="ポスター PNG の出力先(既定は out と同名)")
    ap.add_argument("--acts", default=",".join(ORDER), help="幕をカンマ区切りで指定")
    ap.add_argument("--frames", type=int, default=FRAMES_PER_ACT, help="1 幕のフレーム数")
    ap.add_argument("--fps", type=float, default=FPS)
    ap.add_argument("--levels", type=int, default=LEVELS, help="RGB 各チャンネルの量子化段数")
    a = ap.parse_args(argv)

    names = [n.strip() for n in a.acts.split(",") if n.strip()]
    bad = [n for n in names if n not in ACTS]
    if bad:
        raise SystemExit("未知の幕: %s (使えるのは %s)" % (", ".join(bad), ", ".join(ORDER)))

    out = Path(a.out)
    poster = Path(a.poster) if a.poster else out.with_name(out.stem + "_poster.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    frames = _quantize(build(names, a.frames), a.levels)
    print("  合計 %d 枚 / %.1f 秒(fps %g)  生成 %.1f s"
          % (len(frames), len(frames) / a.fps, a.fps, time.time() - t0))

    fs.write_video(str(out), frames, fps=a.fps)
    # ポスターは書き出した GIF の 1 フレーム目そのもの(= 静止表示と動画が食い違わない)
    first = fs.read_frames(str(out), gray=False, max_frames=1, dtype="uint8")[0]
    fs.write_image(str(poster), first)

    size_mb = out.stat().st_size / 1e6
    print("  %s  %.2f MB" % (out, size_mb))
    print("  %s  %.0f kB" % (poster, poster.stat().st_size / 1e3))
    print("  sha256(gif) = %s" % hashlib.sha256(out.read_bytes()).hexdigest())
    if size_mb > 4.0:
        print("  ⚠ 4 MB を超えている —— --levels を下げるか --frames を減らすこと")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
