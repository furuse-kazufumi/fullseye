"""F5 合成デモ — op を段組み/文のように繋ぐ(画像チェーン + 知覚の段組み).

統一 registry(F2)の op を、①文のように読める Image チェーンと ②汎用 Pipeline の
2 形態で合成する(§7)。両者は同じ registry・同じ F3 メタを使い、結果は一致する。

  PYTHONPATH=. py -3.11 spikes/unified_pipeline_demo.py
"""
from __future__ import annotations
import os, sys, warnings
import numpy as np
warnings.simplefilter("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs  # noqa: E402


def demo_image_chain():
    print("── ① 画像チェーン(文のように読める・§7)──")
    img = np.random.default_rng(0).random((64, 80)).astype(float)
    out = fs.Image(img).median().sobel_amp().invert()   # 平滑 → エッジ → 反転
    print("  fs.Image(img).median().sobel_amp().invert()")
    print(f"  → {out}")
    print(f"    履歴 {out.history} / 出力 {np.asarray(out.value).shape} / 有限 {np.isfinite(out.value).all()}")


def demo_perception_staging():
    print("\n── ② 知覚の段組み(evis 歩行知覚と同じ流れ)──")
    # 段差地形の点群 → 高さ場 → 段差エッジ(walker2d の視覚適応で使った知覚)
    xs = np.arange(1, 5, 0.8)
    gx, gy = np.meshgrid(np.linspace(0, 5, 300), np.linspace(-0.3, 0.3, 20))
    z = np.zeros_like(gx)
    for x in xs:
        z[np.abs(gx - x) < 0.06] = 0.08
    cloud = np.column_stack([gx.ravel(), gy.ravel(), z.ravel()])
    # Image 鎖(tuple 出力の elevation_map は先頭 grid を鎖の値にする)
    grid_img = fs.Image(cloud).elevation_map(cell=0.03, agg="max")
    slope = grid_img.slope_map(cell=0.03)
    print("  fs.Image(cloud).elevation_map(...).slope_map(...)")
    print(f"  → {slope}  勾配中央値 {np.nanmedian(np.asarray(slope.value)):.1f}°")


def demo_pipeline_introspection():
    print("\n── ③ 汎用 Pipeline と introspection(F3 共有)──")
    img = np.random.default_rng(0).random((64, 80)).astype(float)
    p = fs.pipeline("median", "sobel_amp", "invert")
    print(f"  {p}")
    print(f"  steps  = {p.steps}")
    print(f"  render_hint = {p.render_hint}")
    d = p.describe()
    print(f"  describe: {d['n_stages']} 段 / chain = {d['chain']}")
    # 中間出力も取れる(trace)
    _, mids = p.run(img, trace=True)
    print(f"  trace: 入力+各段 = {len(mids)} スナップショット")
    # ④ 画像チェーンと汎用 Pipeline は一致
    chain = fs.Image(img).median().sobel_amp().invert()
    same = np.allclose(np.asarray(p.run(img)), np.asarray(chain.value))
    print(f"\n── ④ Image チェーン == Pipeline: {same} ──")


def main():
    print("== Fullseye F5 合成デモ(単一 registry の op を段組み)==")
    demo_image_chain()
    demo_perception_staging()
    demo_pipeline_introspection()


if __name__ == "__main__":
    main()
