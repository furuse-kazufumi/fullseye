---
op: descriptor_distance
dim: shape2d
category: descriptor
in: efdmodel × efdmodel
out: measurement
examples: [contour_fourier, shape2d_morph_descriptor_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# descriptor_distance — SHAPE2D `descriptor` op

- **データ種**: `efdmodel × efdmodel` → `measurement`
- **呼び出し**: `import fourierdesc; fourierdesc.descriptor_distance(m1, m2, n_harmonics=None, scale_invariant=True)` (または `opsshape2d.get("descriptor_distance")`)

## 使い方

2 つの形状間の距離(小さいほど似た形)。回転/平行移動/始点/(任意で)スケール不変。

各高調波の楕円 (長軸, 短軸) 特異値不変量(:func:`invariants`)の L2 距離。
m1, m2 は :func:`elliptic_fourier` の出力 dict。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [contour_fourier](../../../../examples/contour_fourier.py) — `py -3.11 examples/contour_fourier.py`
- [shape2d_morph_descriptor_tour](../../../../examples/shape2d_morph_descriptor_tour.py) — `py -3.11 examples/shape2d_morph_descriptor_tour.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`descriptor`)

[elliptic_fourier](elliptic_fourier.md) · [reconstruct](reconstruct.md) · [invariants](invariants.md) · [normalize](normalize.md) · [fourier_smooth](fourier_smooth.md) · [from_xld](from_xld.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
