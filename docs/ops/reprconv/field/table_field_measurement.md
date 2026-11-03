---
op: table_field_measurement
dim: reprconv
category: field
in: table
out: measurement
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# table_field_measurement — REPRCONV `field` op

- **データ種**: `table` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.table_field_measurement(table, key)` (実装を直接呼ぶなら `import reprconv; reprconv.table_field_measurement(table, key)`、台帳から引くなら `opsreprconv.get("table_field_measurement")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

表 ``table`` の 1 欄 → 数 1 個 ``measurement``。例: ``label_extent`` の ``width``。

値が要素 1 個の有限な数(スカラーか長さ 1 の配列)であることを確かめる。

Args:
    table: 欄の名前 → 値の dict。
    key: 欄の名前。
Returns:
    float。
Raises:
    ValueError: dict でない / 欄が無い / 要素が 1 個でない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`field`)

[table_field_image2d](table_field_image2d.md) · [table_field_signal](table_field_signal.md) · [table_field_matrix](table_field_matrix.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
