# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""draw_annotate — ラスタ描画で合成GTシーンを作り、検出器で回収して結果を描き返す。

    py -3.11 examples/draw_annotate.py
    py -3.11 examples/draw_annotate.py --save out.png

【用途(分かりやすく)】
``imagedraw`` で **既知の位置・大きさの部品(円)を描いた合成シーン**を作り、それを
検出パイプライン(``detect.segment_objects``)に渡して部品を回収する。描いた真値と
検出結果を突き合わせれば、検出器を「答えの分かるテスト画像」で検証できる。最後に
検出した重心へ ``imagedraw`` で十字を描き返す=**描画→検出→注釈**の一連の流れ。

【グラウンドトゥルース(beat-the-null)】
1. 描いた円の数 == 検出された部品の数(白紙なら 0=偽陽性を出さない)。
2. 各検出重心は、描いた真の中心の近傍にある。
3. 検出された部品は「円」なので circularity が高い(1.0 近傍)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import imagedraw as D          # noqa: E402
import detect                  # noqa: E402  (fullseye の連結成分・領域特徴)

H, W = 180, 240


def main(save=None):
    # --- 1) 描画: 既知の部品(円)を合成シーンに焼く ---
    scene = np.zeros((H, W))
    parts = [(40, 45, 16), (120, 55, 20), (190, 60, 14), (90, 130, 18)]  # (x, y, r)
    for x, y, r in parts:
        scene = D.draw_circle(scene, (x, y), r, color=1.0, fill=True)
    print(f"描画: 既知の円 {len(parts)} 個を合成シーンに焼き込み(中心・半径は真値)。")

    # --- 2) 別の画像処理がその結果を消費: 部品を検出 ---
    objs = detect.segment_objects(scene, threshold="none", min_area=20)
    print(f"検出: detect.segment_objects が部品 {len(objs)} 個を回収。")

    # --- 3) GT: 数・位置・形の一致(白紙は0=偽陽性なし) ---
    assert len(objs) == len(parts), f"部品数が不一致(検出 {len(objs)} != 真値 {len(parts)})"
    assert len(detect.segment_objects(np.zeros((H, W)), threshold="none", min_area=20)) == 0, \
        "白紙から偽陽性を検出した"
    det = sorted((o["centroid"][1], o["centroid"][0], o) for o in objs)  # (x, y, obj)
    want = sorted(parts)
    for (dx, dy, o), (wx, wy, wr) in zip(det, want):
        assert abs(dx - wx) < 3 and abs(dy - wy) < 3, f"重心ズレ ({dx:.0f},{dy:.0f}) vs ({wx},{wy})"
        assert o["circularity"] > 0.85, f"円らしくない circularity={o['circularity']:.2f}"
    print("GT: 数・重心・circularity すべて真値と一致(白紙は0)。")

    # --- 4) 検出結果を描き返す(描画→検出→注釈の環)---
    vis = np.stack([scene, scene, scene], axis=-1)
    for o in objs:
        cy, cx = o["centroid"]
        vis = D.draw_markers(vis, [(cx, cy)], color=(0, 1, 0), size=8, shape="cross", width=2)

    print("\nPASS: 描いた既知シーンを検出器が正しく回収し(数・位置・形が一致)、"
          "検出重心を描き返した。draw は検出パイプラインのGTテスト画像生成と結果注釈に使える。")

    if save:
        from PIL import Image
        Image.fromarray((vis * 255).astype(np.uint8)).save(save)
        print(f"saved: {save}")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default=None)
    args = ap.parse_args()
    raise SystemExit(main(save=args.save))
