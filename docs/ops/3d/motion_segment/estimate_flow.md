---
op: estimate_flow
dim: 3d
category: motion_segment
in: points × points
out: flow_scattered
examples: [motion_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# estimate_flow — 3D `motion_segment` op

- **データ種**: `points × points` → `flow_scattered`
- **呼び出し**: `import fullseye as fs; fs.ledger.estimate_flow(pts0, pts1) -> 'np.ndarray'` (実装を直接呼ぶなら `import motion_seg3d; motion_seg3d.estimate_flow(pts0, pts1) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("estimate_flow")`)

## 使い方

pts0 の各点から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す(最近傍フロー)。

``pts0`` の各点 p について ``pts1`` 中の最近傍 q を cKDTree で求め、変位 ``q - p``
を返す。要素数は N != M でよい。変位が局所点間隔より十分小さい小運動でのみ「点 i の
真の対応先」を当てる(honest な最近傍の限界)。segment_rigid_motions が inlier 判定に
使う **観測フロー** を与える。

Args:
    pts0: (N, 3) 時刻 0 の点群。
    pts1: (M, 3) 時刻 1 の点群。
Returns:
    (N, 3) 変位ベクトル場(pts0 と同じ行順)。空 pts0 は (0, 3) を返す。
Raises:
    ValueError: 形状不正、または pts0 が非空なのに pts1 が空(最近傍が存在しない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_scene](../../../../examples_3d/motion_scene.py) — `py -3.11 examples_3d/motion_scene.py`

## 型が繋がる次の op(`flow_scattered` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`motion_segment`)

[segment_rigid_motions](segment_rigid_motions.md) · [fit_rigid](fit_rigid.md)

---
*Provenance: motion_seg3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
