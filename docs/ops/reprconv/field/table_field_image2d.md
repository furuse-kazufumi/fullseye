---
op: table_field_image2d
dim: reprconv
category: field
in: table
out: image2d
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# table_field_image2d — REPRCONV `field` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.table_field_image2d(table, key)` (実装を直接呼ぶなら `import reprconv; reprconv.table_field_image2d(table, key)`、台帳から引くなら `opsreprconv.get("table_field_image2d")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

表 ``table`` の 1 欄 → 2-D 画像 ``image2d``。``table`` を返す op から画像を受ける op へのつなぎ。

``vx_sobel3x3`` の ``{gx, gy, valid}`` → ``vx_magnitude(gx, gy)``、``flow_from_depth_motion``
の ``{u, v, ...}`` → ``ttc_from_flow(u, v)`` のように、**dict を返す op の欄を名指しで取り出す**。
取り出した値が 2-D の有限な数値配列であることを確かめる(型の名前どおりの物しか通さない)。
bool の欄(``valid`` のような印)は 0/1 の float にする。

Args:
    table: 欄の名前 → 値の dict(``table_read_csv`` の返りなら ``columns`` から読む)。
    key: 欄の名前。
Returns:
    (H, W) の配列(dtype はそのまま。bool は float64)。
Raises:
    ValueError: dict でない / 欄が無い / 2-D でない / 非有限 / 空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[keypoints_from_image2d](../keypoint/keypoints_from_image2d.md)

## 同カテゴリ(`field`)

[table_field_signal](table_field_signal.md) · [table_field_matrix](table_field_matrix.md) · [table_field_measurement](table_field_measurement.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
