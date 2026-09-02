---
op: score_to_position
dim: reprconv
category: score
in: score
out: position
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# score_to_position — REPRCONV `score` op

- **データ種**: `score` → `position`
- **呼び出し**: `import reprconv; reprconv.score_to_position(score)` (または `opsreprconv.get("score_to_position")`)

## 使い方

``score`` volume → 最大値の位置 ``position (z, y, x)``。``score`` の出口。

整数格子上の argmax(副画素精緻化はしない —— それは既存の
``refine_peak_newton`` の仕事で、ここで真似ると 2 か所で別の答えが出る)。
**一方向**(1 つの位置から volume は戻せない)。

Args:
    score: (D, H, W)。
Returns:
    3-tuple の float (z, y, x)。
Raises:
    ValueError: 3-D でない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`position` を入力に取れる)

[position_to_points](../keypoint/position_to_points.md)

## 同カテゴリ(`score`)

[correlation_score](correlation_score.md) · [score_to_image2d](score_to_image2d.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
