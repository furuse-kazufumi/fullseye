---
op: curvature_to_table
dim: reprconv
category: curvature
in: curvature
out: table
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# curvature_to_table — REPRCONV `curvature` op

- **データ種**: `curvature` → `table`
- **呼び出し**: `import reprconv; reprconv.curvature_to_table(curvature)` (または `opsreprconv.get("curvature_to_table")`)

## 使い方

曲率 → 分布の要約 ``table``。**一方向**(統計は情報を捨てるのが仕事)。

(N,) の単独曲率も (N,2) の主曲率対も受ける —— 統計を出すだけなら対で
ある必要が無いため。``kind`` に受けた形を書き戻すので、下流は「対だったのか」
を後から判別できる。

Args:
    curvature: (N,) / (N, 2) / 2 本の等長 1-D のタプル。
Returns:
    dict。``kind`` / ``n`` / ``min`` / ``max`` / ``mean`` / ``rms`` /
    ``p05`` / ``p50`` / ``p95``、対なら ``gauss_mean``(K = k1*k2 の平均)と
    ``mean_curvature_mean``((k1+k2)/2 の平均)。
Raises:
    ValueError: 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`curvature`)

[curvature_to_shape_index](curvature_to_shape_index.md) · [shape_index_to_curvature](shape_index_to_curvature.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
