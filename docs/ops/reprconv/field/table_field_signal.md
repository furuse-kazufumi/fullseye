---
op: table_field_signal
dim: reprconv
category: field
in: table
out: signal
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# table_field_signal — REPRCONV `field` op

- **データ種**: `table` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.table_field_signal(table, key)` (実装を直接呼ぶなら `import reprconv; reprconv.table_field_signal(table, key)`、台帳から引くなら `opsreprconv.get("table_field_signal")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

表 ``table`` の 1 欄 → 1-D 配列 ``signal``。CSV の 1 列や dict の系列を信号の op へ渡す。

1-D の有限な数値列であることを確かめる((n,1) / (1,n) は 1-D に直す。それ以外の 2-D は拒否)。

Args:
    table: 欄の名前 → 値の dict(``table_read_csv`` の返りなら ``columns`` から読む)。
    key: 欄の名前。
Returns:
    (n,) float64。
Raises:
    ValueError: dict でない / 欄が無い / 1-D に直せない / 非有限 / 空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`field`)

[table_field_image2d](table_field_image2d.md) · [table_field_matrix](table_field_matrix.md) · [table_field_measurement](table_field_measurement.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
