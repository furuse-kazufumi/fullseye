# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""draw_annotate — 画像に直接マーカー/線/円/輪郭を焼くラスタ描画(imagedraw)。

    py -3.11 examples/draw_annotate.py
    py -3.11 examples/draw_annotate.py --save out.png

【この例が示すこと】
作業者が指定した対応点(ランドマーク)を画像そのものに描き込む。これは
:mod:`imagemorph` のモーフに渡す対応点を『見て確認する』のに必要な作業で、
Fullseye の既定(gen_*_xld + dev_display オーバーレイ)とは別に、ピクセルへ直接
焼くラスタ描画 op(cv2.line/circle/drawMarker 相当を numpy で)を提供する。

【グラウンドトゥルース】
1. 描画は入力を破壊しない(元画像は不変)。
2. 指定した N 個のランドマークに描いたマーカーは、連結成分 N 個として、各々
   指定座標の近傍に現れる(=座標どおりに描けている)。
3. 線分は端点で確かに塗られ、線外は塗られない。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import imagedraw as D          # noqa: E402
import contours_xld as X       # noqa: E402

H = W = 200


def main(save=None):
    # 背景(なだらかなグラデーション)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    base = (0.15 + 0.5 * xx / W).clip(0, 1)
    base = np.stack([base, base, base], axis=-1)      # RGB

    # 作業者が指定した対応点(モーフに渡すのと同じ形式の (x,y) 点列)
    landmarks = np.array([[60, 80], [140, 80], [100, 120], [70, 155], [130, 155]], float)

    img = D.draw_markers(base, landmarks, color=(0, 1, 0), size=6, shape="cross", width=2)
    img = D.draw_polyline(img, [[40, 60], [160, 60], [165, 170], [35, 170]],
                          color=(1, 0.9, 0), width=2, closed=True)      # 顔枠
    img = D.draw_circle(img, (100, 100), 55, color=(1, 0, 0), width=2)  # 注目円
    ring = X.gen_circle_contour_xld(100, 100, 30, n=80, shape=(H, W))   # XLD 輪郭
    img = D.draw_contour(img, ring, color=(0.2, 0.4, 1.0), width=1)

    print(f"背景 {base.shape} に、指定ランドマーク {len(landmarks)} 点 + 顔枠 + 円 + XLD輪郭を描画。")

    # --- GT1: 入力を破壊していない ---
    assert np.abs(base - np.stack([(0.15 + 0.5 * xx / W).clip(0, 1)] * 3, -1)).max() < 1e-12, \
        "元画像が破壊されている"

    # --- GT2: マーカーが座標どおり N 個 ---
    green = (img[..., 1] > 0.6) & (img[..., 0] < 0.4) & (img[..., 2] < 0.4)
    lab, n = ndimage.label(green)
    print(f"緑マーカーの連結成分 = {n}(指定 {len(landmarks)} 点)")
    assert n == len(landmarks), f"マーカー数が一致しない({n} != {len(landmarks)})"
    # 各マーカーは対応ランドマークの近傍にある
    centers = ndimage.center_of_mass(green, lab, range(1, n + 1))     # (row,col)
    got = sorted((c, r) for r, c in centers)
    want = sorted((x, y) for x, y in landmarks)
    for (gx, gy), (wx, wy) in zip(got, want):
        assert abs(gx - wx) < 4 and abs(gy - wy) < 4, f"マーカー位置ズレ {gx,gy} vs {wx,wy}"

    # --- GT3: 線分の端点は塗られ、線外は塗られない ---
    L = D.draw_line(np.zeros((60, 60)), (5, 5), (50, 50), 1.0, 1)
    assert L[5, 5] > 0.5 and L[50, 50] > 0.5 and L[5, 55] < 0.5

    print("\nPASS: ラスタ描画は入力を壊さず、指定座標どおりにマーカー/線/円/輪郭を焼き込む。"
          "これで imagemorph に渡す対応点を画像上で確認できる。")

    if save:
        from PIL import Image
        Image.fromarray((img * 255).astype(np.uint8)).save(save)
        print(f"saved: {save}")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default=None)
    args = ap.parse_args()
    raise SystemExit(main(save=args.save))
