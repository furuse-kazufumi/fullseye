---
op: frame_axis
dim: reprconv
category: structure
in: frame
out: normals
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# frame_axis — REPRCONV `structure` op

- **データ種**: `frame` → `normals`
- **呼び出し**: `import fullseye as fs; fs.ledger.frame_axis(frame, axis='tangent')` (実装を直接呼ぶなら `import reprconv; reprconv.frame_axis(frame, axis='tangent')`、台帳から引くなら `opsreprconv.get("frame_axis")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Frenet 標構 ``frame`` → 1 本の軸の単位ベクトル列 ``normals (N,3)``。``frame`` 型の出口。

``frenet_frame`` の返り ``(T, N, B)``(各 (N,3))から ``axis`` の 1 本を取り出す:
``"tangent"`` = 接線 T、``"normal"`` = 主法線 N、``"binormal"`` = 陪法線 B。
取り出した列は点ごとの単位ベクトルなので ``normals`` 型に載る
(``normals_to_angles`` / ``normals_to_egi`` などがそのまま掛かる)。

``frenet_frame`` は直線区間で N・B がほぼゼロベクトルになる(向き不定)。ここでは
**長さ 0.5 未満の行を拒否**する(黙って単位ベクトルのふりをさせない)。
直線を含む曲線で N/B を使うなら、先に ``fit_spline_curve`` で滑らかにするか接線だけを使う。

Args:
    frame: ``(T, N, B)`` の 3-tuple、各 (N,3)。
    axis: ``"tangent"`` / ``"normal"`` / ``"binormal"``。
Returns:
    (N, 3) float64、各行は単位長(``frenet_frame`` が正規化した値そのまま)。
Raises:
    ValueError: 3-tuple でない / 形がそろわない / axis が不正 / 長さ 0.5 未満の行がある。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[normals_to_angles](../direction/normals_to_angles.md) · [normals_to_egi](../direction/normals_to_egi.md)

## 同カテゴリ(`structure`)

[knn_graph_to_conn_graph](knn_graph_to_conn_graph.md) · [pointmap_to_points](pointmap_to_points.md) · [match_component](match_component.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
