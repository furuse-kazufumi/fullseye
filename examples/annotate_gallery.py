# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""annotate_gallery — 図注(annotate)op を一枚の図に全部使い、**真値と突き合わせる**。

    py -3.11 examples/annotate_gallery.py
    py -3.11 examples/annotate_gallery.py --save out/annotate_gallery.png

【用途(分かりやすく)】
この repo の図は 141 点あるが、それを作る 6 本の生成器は「文字の下敷き」「矢印」
「凡例」「カラーバー」「目盛り」「拡大の差し込み」を**各自で手書き**していた。
:mod:`annotate` はそれを 1 か所に集めた層で、ここではその全 op を使って
4 枚のパネルを組み、**描いた結果を測り直して閉形式と一致するか**を確かめる。

【グラウンドトゥルース(beat-the-null)】
1. スケールバーの画素長 == ``round(length / units_per_pixel)``(誤差 0 画素)。
2. 目盛りの列 == ``axes`` の閉形式の丸め(誤差 0 画素)。
3. α 重ねの結果 == ``a*f + (1-a)*b``(最大絶対誤差 0.0)。
4. 凡例の箱の高さ == ``2*pad + n*row_h + (n-1)*gap``(誤差 0 画素)。

つまり「それらしい絵」ではなく、**測って合う絵**であることを示す。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as A          # noqa: E402
import palette                # noqa: E402

PH, PW = 260, 380             # パネルは非正方(row/col の取り違えが形で出る)


def _scene():
    """合成シーン ―― 傾いた帯と 2 つの円板(位置は既知)。"""
    yy, xx = np.mgrid[0:PH, 0:PW]
    base = 0.10 + 0.06 * np.sin(xx / 23.0) * np.cos(yy / 31.0)
    disk1 = ((xx - 110) ** 2 + (yy - 90) ** 2) < 34 ** 2
    disk2 = ((xx - 250) ** 2 + (yy - 165) ** 2) < 26 ** 2
    band = np.abs((yy - 0.35 * xx) - 40) < 9
    img = np.stack([base] * 3, axis=-1)
    img[band] = (0.30, 0.30, 0.36)
    img[disk1 | disk2] = (0.62, 0.62, 0.68)
    return np.clip(img, 0.0, 1.0), (disk1 | disk2), band


def panel_measure():
    """パネル 1 — 計測の図: マスク重ね・引き出し線・点のラベル・スケールバー。"""
    img, disks, _ = _scene()
    out = A.overlay_mask(img, disks, "right", alpha=0.45, outline=2)
    out = A.leader_line(out, (96, 234), (110, 90), text="円板 A", cap="dot", cap_size=4,
                        font_size=12)
    out = A.label_points(out, [(110, 90), (250, 165)], ["1", "2"], marker_size=6,
                         color="emphasis", font_size=12)
    out = A.scale_bar(out, 100.0, 0.5, unit="µm", anchor="rb", margin=16,
                      color=(0.95, 0.95, 0.97), thickness=5)
    out = A.text_box(out, "計測(マスク + 引き出し線 + スケールバー)", (10, 10),
                     anchor="lt", font_size=13)
    return out


def panel_plot():
    """パネル 2 — グラフ: 軸・格子・目盛り・折れ線・散布(matplotlib を使わない)。"""
    img = np.full((PH, PW, 3), 0.07)
    ax = A.axes_transform((52, 40, 300, 175), (0.0, 10.0), (-1.0, 1.0))
    img = A.grid_lines(img, ax, color="neutral", alpha=0.28)
    img = A.axes_frame(img, ax, color="neutral", width=1)
    img = A.ticks(img, ax, tick_len=5, font_size=10)
    x = np.linspace(0.0, 10.0, 120)
    img = A.plot_series(img, ax, x, np.sin(x), kind="line", color="reference", width=2)
    xs = np.linspace(0.4, 9.6, 10)
    img = A.plot_series(img, ax, xs, np.cos(xs), kind="scatter", color="emphasis",
                        marker_size=3)
    img = A.legend_box(img, [("reference", "sin x"), ("emphasis", "cos x")], (346, 46),
                       anchor="rt", markers=True, font_size=11, swatch=11, pad=6)
    img = A.text_box(img, "グラフ(軸・目盛り・格子はこの層の仕事)", (10, 10),
                     anchor="lt", font_size=13)
    return img


def panel_labels():
    """パネル 3 — ラベル図: 色ラベル重ね・カラーバー・角度と図形。"""
    img = np.full((PH, PW, 3), 0.08)
    lab = np.zeros((PH, PW), np.int32)
    yy, xx = np.mgrid[0:PH, 0:PW]
    for i, (cx, cy, r) in enumerate(((70, 90, 34), (150, 150, 30), (240, 80, 38)), start=1):
        lab[((xx - cx) ** 2 + (yy - cy) ** 2) < r ** 2] = i
    out = A.overlay_labels(img, lab, alpha=0.75)
    out = A.color_bar(out, palette.diverging_lut(128), (330, 44, 14, 150),
                      vmin=-2.5, vmax=2.5, unit="σ", font_size=10)
    out = A.rounded_rect(out, (24, 190, 150, 52), radius=10, color="baseline", width=2)
    out = A.arc(out, (100.0, 216.0), 22.0, 200.0, 340.0, color="emphasis", width=3)
    out = A.ellipse(out, (240.0, 200.0), (44.0, 22.0), 25.0, color="reference", width=2)
    out = A.filled_polygon(out, [(196, 128), (232, 140), (206, 168)], color="wrong", alpha=0.8)
    out = A.text_box(out, "ラベル・LUT 凡例・図形", (10, 10), anchor="lt", font_size=13)
    return out


def panel_zoom():
    """パネル 4 — 拡大の差し込み + 矢印 + 交差線。"""
    img, _, _ = _scene()
    out = A.crosshair(img, (110, 90), color="emphasis", gap=10, extent=48, width=1)
    out = A.zoom_inset(out, (86, 66, 48, 36), (190, 30), factor=3, color="emphasis",
                       width=2, connect=True)
    out = A.arrow(out, (60, 240), (150, 196), color="wrong", width=2)
    out = A.text_box(out, "拡大 x3(最近傍 = 画素をそのまま見せる)", (10, 10),
                     anchor="lt", font_size=13)
    return out


# ------------------------------------------------------------------ #
# ground truth — 描いた絵を測り直す
# ------------------------------------------------------------------ #

def _check_scale_bar():
    """バーの画素長 == round(length / units_per_pixel)。"""
    length, upp = 100.0, 0.5
    canvas = np.zeros((60, 300, 3))
    out = A.scale_bar(canvas, length, upp, unit="µm", xy=(10, 50), anchor="lb",
                      color=(1.0, 1.0, 1.0), thickness=4, label=False)
    drawn = int(np.flatnonzero(np.isclose(out[..., 0], 1.0).any(axis=0)).size)
    return drawn, int(round(length / upp))


def _check_ticks():
    """目盛りの列 == data_to_pixel の丸め。"""
    ax = A.axes_transform((20, 10, 161, 61), (0.0, 8.0), (0.0, 1.0))
    canvas = np.zeros((120, 220, 3))
    out = A.ticks(canvas, ax, xticks=[0.0, 2.0, 4.0, 6.0, 8.0], yticks=[],
                  color=(1.0, 1.0, 1.0), tick_len=6, label=False, width=1)
    band = out[71:76, :, 0]
    cols = np.flatnonzero(np.isclose(band, 1.0).any(axis=0))
    want, _ = A.data_to_pixel(ax, np.array([0.0, 2.0, 4.0, 6.0, 8.0]), np.zeros(5))
    return int(np.abs(cols - np.round(want).astype(int)).max()), cols.size


def _check_alpha():
    """α 重ね == a*f + (1-a)*b(最大絶対誤差)。"""
    rng = np.random.default_rng(7)
    base = rng.uniform(0.0, 1.0, (80, 130, 3))
    mask = np.zeros((80, 130), bool)
    mask[20:60, 30:100] = True
    alpha = 0.37
    got = A.overlay_mask(base, mask, "wrong", alpha)
    col = np.asarray(palette.role_color("wrong"), np.float64)
    want = base.copy()
    want[mask] = alpha * col + (1.0 - alpha) * base[mask]
    return float(np.abs(got - want).max())


def _check_legend_height():
    """凡例の高さ == 2*pad + n*row_h + (n-1)*gap。"""
    pad, gap, swatch, fs, n = 8, 4, 14, 13, 4
    rows = [("right", f"row {i}") for i in range(n)]
    row_h = max(swatch, A.measure_text("row 0", font_size=fs)["height"])
    want = 2 * pad + n * row_h + (n - 1) * gap
    canvas = np.zeros((200, 240, 3))
    out = A.legend_box(canvas, rows, (6, 6), swatch=swatch, row_gap=gap, pad=pad,
                       font_size=fs, box_color=(1.0, 1.0, 1.0), box_alpha=1.0, border=0)
    drawn = int(np.flatnonzero((out[..., 0] > 0.5).any(axis=1)).size)
    return drawn, want


def run():
    """4 枚のパネルを組み、真値との一致を返す。"""
    panels = [panel_measure(), panel_plot(), panel_labels(), panel_zoom()]
    sheet = A.panel_grid(
        panels,
        labels=["1. 計測 (mask/leader/scale bar)", "2. グラフ (axes/ticks/series)",
                "3. ラベル (labels/color bar/shapes)", "4. 拡大 (zoom inset/arrow)"],
        ncols=2, pad=12, label_h=30, background=0.04, font_size=14,
        title="annotate — 図注の層 (25 op)")

    bar_px, bar_want = _check_scale_bar()
    tick_err, tick_n = _check_ticks()
    alpha_err = _check_alpha()
    leg_px, leg_want = _check_legend_height()
    return {
        "sheet": sheet,
        "scale_bar_px": bar_px, "scale_bar_want": bar_want,
        "scale_bar_px_error": bar_px - bar_want,
        "tick_px_error": tick_err, "tick_count": tick_n,
        "alpha_max_abs_error": alpha_err,
        "legend_height_px": leg_px, "legend_height_want": leg_want,
        "legend_height_error": leg_px - leg_want,
    }


def main(save=None):
    r = run()
    print(f"合成: 4 パネル -> {r['sheet'].shape[1]}x{r['sheet'].shape[0]} px のシート。")
    print(f"1) スケールバー: 描画 {r['scale_bar_px']} px / 真値 "
          f"{r['scale_bar_want']} px (100 µm を 0.5 µm/px で) -> 誤差 {r['scale_bar_px_error']} px")
    print(f"2) 目盛り: {r['tick_count']} 本の列位置と閉形式の最大差 = {r['tick_px_error']} px")
    print(f"3) α 重ね: |描画 - (a*f+(1-a)*b)| の最大 = {r['alpha_max_abs_error']}")
    print(f"4) 凡例の高さ: 描画 {r['legend_height_px']} px / 閉形式 "
          f"{r['legend_height_want']} px -> 誤差 {r['legend_height_error']} px")

    assert r["scale_bar_px_error"] == 0, "スケールバーが物理長と合っていない"
    assert r["tick_px_error"] == 0, "目盛りが閉形式とずれている"
    assert r["alpha_max_abs_error"] == 0.0, "α 合成が式と一致しない"
    assert r["legend_height_error"] == 0, "凡例の高さが要素数と合っていない"

    print("\nPASS: 図注 op が描いた絵は、測り直しても閉形式と一致した"
          "(スケールバー・目盛り・α 合成・凡例の高さの 4 点で誤差ゼロ)。")
    if save:
        from PIL import Image
        Path(save).parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.round(r["sheet"] * 255.0).astype(np.uint8)).save(save)
        print(f"saved: {save}")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default=None)
    args = ap.parse_args()
    raise SystemExit(main(save=args.save))
