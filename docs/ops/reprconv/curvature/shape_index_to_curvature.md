---
op: shape_index_to_curvature
dim: reprconv
category: curvature
in: pairs
out: curvature
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# shape_index_to_curvature — REPRCONV `curvature` op

- **データ種**: `pairs` → `curvature`
- **呼び出し**: `import reprconv; reprconv.shape_index_to_curvature(pairs)` (または `opsreprconv.get("shape_index_to_curvature")`)

## 使い方

形状指数と曲がり ``(N,2)`` → 主曲率 ``(N,2)``。:func:`curvature_to_shape_index` の逆。

theta = pi*S/2 として ``k1 = C(sin+cos)``, ``k2 = C(sin-cos)``。
(S, C) の定義式を解いた閉形式で、近似も反復も入っていない。

Args:
    pairs: (N, 2) の ``[S, C]``。
Returns:
    (N, 2) float64 の ``[k1, k2]``(k1 >= k2)。
Raises:
    ValueError: |S| > 1 / C < 0 / 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`curvature` を入力に取れる)

[curvature_to_shape_index](curvature_to_shape_index.md) · [curvature_to_table](curvature_to_table.md)

## 同カテゴリ(`curvature`)

[curvature_to_shape_index](curvature_to_shape_index.md) · [curvature_to_table](curvature_to_table.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
