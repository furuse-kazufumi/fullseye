---
op: synapse_table_from_table
dim: reprconv
category: entry
in: table
out: synapse_table
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# synapse_table_from_table — REPRCONV `entry` op

- **データ種**: `table` → `synapse_table`
- **呼び出し**: `import fullseye as fs; fs.ledger.synapse_table_from_table(table, pre='pre', post='post', count=None)` (実装を直接呼ぶなら `import reprconv; reprconv.synapse_table_from_table(table, pre='pre', post='post', count=None)`、台帳から引くなら `opsreprconv.get("synapse_table_from_table")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

表 ``table``(列名 → 配列)→ シナプス表 ``synapse_table (m, 3)``。``synapse_table`` 型の入口。

コネクトームの公開データは CSV(``table_read_csv`` で ``table`` になる)で来るので、
その 3 列を ``(pre_id, post_id, count)`` の m×3 に詰め直す。``count`` を省くと 1
(シナプス 1 個 = 1 行の表)。``synapse_table`` を ``points`` と分けてある理由
(形が同じ (N,3) で、点群を渡すと座標が id として読まれる)を守るため、**id が
0 以上の整数であることをここで確かめる**(``graph_from_synapses`` と同じ規約)。

``table`` は 2 つの形を受ける: 列名 → 配列の dict そのものと、``table_read_csv`` の返り
``{"columns": {列名: 配列}, "units": ..., "meta": ...}``(列は ``columns`` から読む)。

Args:
    table: 列名 → 1-D 配列の dict、または ``table_read_csv`` の返り。
    pre, post: 前・後ニューロン id の列名。
    count: シナプス数の列名(None で全行 1)。
Returns:
    (m, 3) float64。
Raises:
    ValueError: dict でない / 列が無い / 長さがそろわない / id が 0 以上の整数でない /
        count が負か非有限 / 空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`synapse_table` を入力に取れる)

—

## 同カテゴリ(`entry`)

[indices_to_positions](indices_to_positions.md) · [jones_state](jones_state.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
