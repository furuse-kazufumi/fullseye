---
op: match_component
dim: reprconv
category: structure
in: match
out: measurement
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# match_component — REPRCONV `structure` op

- **データ種**: `match` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.match_component(match, index=0)` (実装を直接呼ぶなら `import reprconv; reprconv.match_component(match, index=0)`、台帳から引くなら `opsreprconv.get("match_component")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

``match`` 型(1-D の結果ベクトル)→ その 1 成分の ``measurement``。``match`` 型の出口。

2-D レジストリの ``match`` 型は「1 スカラーでは表せない複数の値」を 1 本のベクトルで運ぶ:
``area_center`` = (面積 [px], 重心の行 [px], 重心の列 [px])、``ncc_locate`` /
``shape_locate`` = (相関値, 行, 列)、``eccentricity`` = (Anisometry, Bulkiness,
StructureFactor) など。HALCON でも ``area_center`` の Row だけを次の処理に渡すように、
**成分を名指しで 1 つ取り出す**のがこの型の自然な出口。どの成分が何かは産んだ op の
docstring が決めている(ここでは解釈しない)。

Args:
    match: 1-D の有限な数値列(長さ >= 1)。0-D のスカラーは長さ 1 として受ける。
    index: 取り出す成分の番号(0 始まり)。負の番号は使えない(取り違えを防ぐため)。
Returns:
    float。
Raises:
    ValueError: 1-D でない / 非有限 / 空 / index が範囲外か整数でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`structure`)

[frame_axis](frame_axis.md) · [knn_graph_to_conn_graph](knn_graph_to_conn_graph.md) · [pointmap_to_points](pointmap_to_points.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
