---
op: cscalar_to_polar
dim: reprconv
category: algebra
in: cscalar
out: pairs
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# cscalar_to_polar — REPRCONV `algebra` op

- **データ種**: `cscalar` → `pairs`
- **呼び出し**: `import reprconv; reprconv.cscalar_to_polar(cscalar)` (または `opsreprconv.get("cscalar_to_polar")`)

## 使い方

複素スカラ → 極形式 ``pairs (1,2) = [|z|, arg z[度]]``。``cscalar`` の出口。

``cplx_contour_integral`` / ``cplx_cauchy_value`` が返す複素スカラは、
``measurement``(実スカラのみ)へ混ぜると下流が生 TypeError で落ちるので
型が分かれている。極形式の対にすると 1-D 語彙へ渡せる。

**角度は度**。:func:`polar_to_cscalar` と往復して実測 max|Δ| = 8.9e-16。

Args:
    cscalar: complex(または複素 0-d 配列)。
Returns:
    (1, 2) float64。
Raises:
    ValueError: 複素スカラでない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[angles_to_normals](../direction/angles_to_normals.md) · [shape_index_to_curvature](../curvature/shape_index_to_curvature.md) · [pairs_to_signal](../pairs/pairs_to_signal.md) · [pairs_to_image2d](../pairs/pairs_to_image2d.md) · [pairs_to_table](../pairs/pairs_to_table.md) · [polar_to_cscalar](polar_to_cscalar.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [matrix_to_angle](matrix_to_angle.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [shift_to_vector](shift_to_vector.md) · [vector_to_shift](vector_to_shift.md) · [polar_to_cscalar](polar_to_cscalar.md) · [countrate_to_counts](countrate_to_counts.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
