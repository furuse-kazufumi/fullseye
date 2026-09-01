---
op: pairs_to_table
dim: reprconv
category: pairs
in: pairs
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# pairs_to_table — REPRCONV `pairs` op

- **データ種**: `pairs` → `table`
- **呼び出し**: `import reprconv; reprconv.pairs_to_table(pairs)` (または `opsreprconv.get("pairs_to_table")`)

## 使い方

対 ``(N,2)`` → 要約 ``table``。**一方向**。

``x_uniform`` は「列 0 が等間隔か」の判定で、これが False の対を
:func:`pairs_to_signal` に通すと x が黙って落ちる(上の docstring 参照)。
判定は最大差分と最小差分の比で行い、閾値は 1e-9(相対)。

Args:
    pairs: (N, 2)。
Returns:
    dict(``n`` / ``x_min`` / ``x_max`` / ``y_min`` / ``y_max`` /
    ``y_mean`` / ``x_uniform`` / ``x_step``(等間隔のときのみ) /
    ``pearson_r``(N >= 2 かつ両列が定数でないとき))。
Raises:
    ValueError: 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`pairs`)

[pairs_to_signal](pairs_to_signal.md) · [pairs_to_image2d](pairs_to_image2d.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
