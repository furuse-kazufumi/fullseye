---
op: pointmap_to_points
dim: reprconv
category: structure
in: pointmap
out: points
gpu: なし
examples: [poc_bga_ball_type_roundtrip, type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# pointmap_to_points — REPRCONV `structure` op

- **データ種**: `pointmap` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.pointmap_to_points(pointmap, drop_nonpositive_z=False)` (実装を直接呼ぶなら `import reprconv; reprconv.pointmap_to_points(pointmap, drop_nonpositive_z=False)`、台帳から引くなら `opsreprconv.get("pointmap_to_points")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

格子整列の 3-D 点 ``pointmap (H,W,3)`` → 点群 ``points (N,3)``。``pointmap`` 型の出口。

行優先(row-major)に並べ直し、**非有限の行は捨てる**(``pointmap`` では NaN が「その
画素は無効」の印なので、ここでは拒否せず落とす)。``drop_nonpositive_z=True`` は
``z <= 0`` の行も捨てる —— ``depth_to_organized_points`` のカメラ座標の pointmap は
無効深度 0 が原点に集まるので、その場合に使う(``depth_to_points`` と同じ規約になり、
同じ内部行列なら**同じ点が同じ順に**出る)。地心座標(``dem_geocentric_grid``)では
z が負になりうるので既定は False。列の意味(x, y, z)は入力のまま変えない。

Args:
    pointmap: (H, W, 3)。
    drop_nonpositive_z: True で z <= 0 の行も捨てる。
Returns:
    (N, 3) float64。
Raises:
    ValueError: (H, W, 3) でない / 空 / 有効な点が 1 つも残らない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_bga_ball_type_roundtrip](../../../../examples/poc_bga_ball_type_roundtrip.py) — `py -3.11 examples/poc_bga_ball_type_roundtrip.py`
- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_zyx_to_keypoints_uv](../keypoint/points_zyx_to_keypoints_uv.md) · [points_to_position](../keypoint/points_to_position.md) · [select_points](../index/select_points.md) · [flow_apply](../flow/flow_apply.md) · [points_to_gaussians](../gaussians/points_to_gaussians.md)

## 同カテゴリ(`structure`)

[frame_axis](frame_axis.md) · [knn_graph_to_conn_graph](knn_graph_to_conn_graph.md) · [match_component](match_component.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
