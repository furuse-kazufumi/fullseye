# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""raw_to_display_isp — Bayer の生フレームを表示画像にする ISP 段を、閉じた式で順に掛ける。

    py -3.11 examples/raw_to_display_isp.py
    FULLSEYE_FIGURE_DIR=out/figs py -3.11 examples/raw_to_display_isp.py

【この例が示すこと】
カメラの ISP(Image Signal Processor)が RAW から RGB を作るまでの典型 8 段を、
fullseye の gfx2d 台帳 ``isp`` の op で組む:

    黒レベル(BLC) → 欠陥画素(DPC) → 周辺減光(LSC) → ホワイトバランス(AWB, RAW 側)
    → デモザイク(双線形) → 色補正行列(CCM) → 色相・彩度 → 明るさ・コントラスト

【真値】シーンは自分で作る(1 次の RGB 平面)。そこに色かぶり・周辺減光・露出・台座・
欠陥画素を**既知の量で**植えて RAW にし、段を外していって元の RGB に戻るかを数字で見る。

★各段は閉じた式なので「何をしたか」が全部言える。学習 ISP のように綺麗にはならないが、
検査用途では「段ごとに何が起きたか説明できる」ことの方が要る。

EXTEND: 実カメラなら ``raw`` を読み込み、``pattern`` をセンサに合わせ、flat は白い板を撮る。
CCM はカラーチャートから最小二乗で求める(この例では既知行列を与える)。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

PATTERN = "RGGB"


def scene(h=96, w=128):
    """1 次の RGB 平面 + 淡い円(検査対象らしい形)。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    rgb = np.stack([0.30 + 0.004 * xx + 0.002 * yy, 0.45 - 0.002 * xx + 0.003 * yy,
                    0.25 + 0.003 * xx + 0.001 * yy], axis=-1)
    disc = ((yy - h / 2) ** 2 + (xx - w / 2) ** 2) < (h / 4) ** 2
    rgb[disc] *= np.array([1.3, 0.9, 0.8])
    return np.clip(rgb, 0.0, 1.0)


def mosaic(rgb, pattern):
    pos = fs.gfx2d._bayer_offsets(pattern)
    raw = np.zeros(rgb.shape[:2])
    for ch, k in (("R", 0), ("G1", 1), ("G2", 1), ("B", 2)):
        r, c = pos[ch]
        raw[r::2, c::2] = rgb[r::2, c::2, k]
    return raw


def main() -> int:
    rgb = scene()
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    shade = 1.0 - 0.35 * (((yy - (h - 1) / 2) / (h / 2)) ** 2 + ((xx - (w - 1) / 2) / (w / 2)) ** 2)
    cast = np.array([0.65, 1.0, 0.8])                          # 電球色の照明で R・B が弱い
    black, white = 0.04, 0.92
    raw = mosaic(np.clip(rgb * cast, 0, 1), PATTERN) * shade * (white - black) + black
    rng = np.random.default_rng(0)
    dead = [(rng.integers(0, h), rng.integers(0, w)) for _ in range(12)]
    for i, (r, c) in enumerate(dead):
        raw[r, c] = 1.0 if i % 2 == 0 else 0.0
    flat = np.full((h, w), 0.6) * shade * (white - black) + black   # 白い板を撮った flat

    # 1. 黒レベル: 台座 0.04 を引き、白 0.92 を 1 に。
    x = fs.raw_black_level(raw, black, white=white, pattern=PATTERN)
    # 2. 欠陥画素: 同色 8 近傍と閾値以上ずれた画素を中央値で置く。
    m = fs.raw_dead_pixel_mask(x, 0.15)
    x = fs.raw_dead_pixel_correct(x, 0.15)
    print("1-2. 黒レベル → 欠陥画素: 見つけた欠陥 %d / 植えた %d" % (int(m.sum()), len(dead)))
    assert int(m.sum()) == len(dead), int(m.sum())
    # 3. 周辺減光: flat から色ごとの利得地図。
    gain = fs.lens_shading_gain(fs.raw_black_level(flat, black, white=white, pattern=PATTERN), pattern=PATTERN)
    x = fs.lens_shading_correct(x, gain)
    print("3. 周辺減光: 利得 %.2f〜%.2f" % (gain.min(), gain.max()))
    # 4. ホワイトバランス(RAW 側): デモザイク前に gray-world の利得を掛ける。
    pre = fs.raw_demosaic_bilinear(x, PATTERN)
    gains = fs.awb_gains(pre, "gray_world")
    x = fs.raw_apply_gains(x, gains, PATTERN)
    print("4. AWB(gray-world): 利得 R %.3f  G %.3f  B %.3f(植えたかぶりの逆 = %s)" % (
        gains[0], gains[1], gains[2], np.round(cast[1] / cast, 3).tolist()))
    print("   ★一致しないのが正しい: gray-world は「場面の平均が灰」を仮定するが、この場面は平均が灰でない。"
          "段の限界を数字で見せる(白い板を撮って white_patch にするか、灰の基準を置く)")
    # 5. デモザイク(双線形)。
    out = fs.raw_demosaic_bilinear(x, PATTERN)
    # 6. CCM(既知。実務ではカラーチャートから最小二乗)。
    ccm = np.array([[1.5, -0.35, -0.15], [-0.2, 1.4, -0.2], [0.05, -0.45, 1.4]])
    graded = fs.color_correction_matrix(out, ccm)
    # 7-8. 色相・彩度、明るさ・コントラスト(見た目の仕上げ。真値比較はここでは行わない)。
    final = fs.brightness_contrast(fs.hue_saturation(graded, 0.0, 1.1), 0.0, 1.05)

    # 真値との比較: 段 5 までは「かぶり・減光・台座・欠陥を外した rgb」に戻るはず。
    ref = rgb / rgb.reshape(-1, 3).mean(axis=0) * out.reshape(-1, 3).mean(axis=0)   # 露出は不定なので平均で合わせる
    d = np.abs(out[3:-3, 3:-3] - ref[3:-3, 3:-3])
    p95, mx = float(np.percentile(d, 95)), float(d.max())
    print("5. デモザイク後と真値の差(縁 3 画素を除く): 95 %% 点 %.3e / 最大 %.3e" % (p95, mx))
    print("   最大は円の縁(色の段差)に出る双線形デモザイクのジッパー —— 閉じた式の限界で、値を隠さない")
    assert p95 < 2e-2, p95

    figs.save_grid("raw_to_display_isp",
                   [raw, m, gain, out, graded, final],
                   ["RAW(台座・減光・かぶり・欠陥)", "欠陥画素の地図", "周辺減光の利得", "AWB + デモザイク",
                    "+ CCM", "+ 色相彩度・明暗"],
                   ncols=3, gray=[True, True, False, False, False, False],
                   caption="Bayer RAW → 表示画像。全段が閉じた式で、植えた劣化を順に外す")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
