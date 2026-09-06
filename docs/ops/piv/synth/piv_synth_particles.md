---
op: piv_synth_particles
dim: piv
category: synth
in: 
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_synth_particles — PIV `synth` op

- **データ種**: `なし` → `image2d`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import pivops; pivops.piv_synth_particles(shape, density=0.02, diameter_px=2.5, seed=0, intensity=(0.6, 1.0), background=0.0)` (または `opspiv.get("piv_synth_particles")`)

## 使い方

トレーサ粒子を撒いた 1 枚を作る。返りは ``(image, positions)``。

粒子はガウス輝点(直径 = 1/e^2 幅ではなく**標準偏差の 2 倍**を
``diameter_px`` と呼ぶ、PIV の慣行)。位置は連続値なので、サブピクセルの
真値を持つ画像が作れる。

``density`` は 1 画素あたりの粒子数。PIV の経験則では**窓あたり 5-10 個**が
目安で、32x32 窓なら 0.005-0.01 に当たる。少なすぎると相関ピークが立たず、
多すぎると粒子像が重なって個々の対応が失われる。

Args:
    shape: ``(H, W)``。
    density: 画素あたりの粒子数(> 0)。
    diameter_px: 粒子像の直径 [px] (> 0)。
    seed: 乱数種。
    intensity: 粒子の明るさの範囲 ``(lo, hi)``。
    background: 一様な下駄。
Returns:
    ``(image (H, W) float64, positions (N, 2) の (row, col))``。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[piv_cross_correlate](../estimate/piv_cross_correlate.md) · [piv_multipass](../estimate/piv_multipass.md) · [piv_deform_pass](../estimate/piv_deform_pass.md)

## 同カテゴリ(`synth`)

[piv_synth_pair](piv_synth_pair.md) · [piv_synth_sequence](piv_synth_sequence.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
