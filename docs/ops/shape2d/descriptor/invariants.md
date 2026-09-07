---
op: invariants
dim: shape2d
category: descriptor
in: efdmodel
out: pairs
examples: [shape2d_morph_descriptor_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# invariants — SHAPE2D `descriptor` op

- **データ種**: `efdmodel` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.invariants(model, scale_invariant=True)` (実装を直接呼ぶなら `import fourierdesc; fourierdesc.invariants(model, scale_invariant=True)`、台帳から引くなら `opsshape2d.get("invariants")`)

## 使い方

回転・平行移動・始点・(任意で)スケールに不変な形状記述子((N,2))。

各高調波の楕円の (長軸, 短軸) = 特異値を並べたもの。DC を含まないので平行移動に
不変、特異値なので空間回転と始点シフトに不変、第1高調波の長軸で割ればスケール
不変。形状マッチング(:func:`descriptor_distance`)の土台。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape2d_morph_descriptor_tour](../../../../examples/shape2d_morph_descriptor_tour.py) — `py -3.11 examples/shape2d_morph_descriptor_tour.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[elliptic_fourier](elliptic_fourier.md) · [fourier_smooth](fourier_smooth.md) · [add_frame_corners](../morph/add_frame_corners.md) · [warp_tps_image](../morph/warp_tps_image.md) · [warp_piecewise_affine](../morph/warp_piecewise_affine.md) · [morph](../morph/morph.md) · [morph_sequence](../morph/morph_sequence.md)

## 同カテゴリ(`descriptor`)

[elliptic_fourier](elliptic_fourier.md) · [reconstruct](reconstruct.md) · [normalize](normalize.md) · [descriptor_distance](descriptor_distance.md) · [fourier_smooth](fourier_smooth.md) · [from_xld](from_xld.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
