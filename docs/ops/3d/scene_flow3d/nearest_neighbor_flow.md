---
op: nearest_neighbor_flow
dim: 3d
category: scene_flow3d
in: points × points
out: flow_scattered
examples: [scene_flow_rigid]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# nearest_neighbor_flow — 3D `scene_flow3d` op

- **データ種**: `points × points` → `flow_scattered`
- **呼び出し**: `import fullseye as fs; fs.ledger.nearest_neighbor_flow(pts0, pts1) -> 'np.ndarray'` (実装を直接呼ぶなら `import scene_flow3d; scene_flow3d.nearest_neighbor_flow(pts0, pts1) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("nearest_neighbor_flow")`)

## 使い方

各点 pts0 から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す。

``pts0`` の各点 p について ``pts1`` 中の最近傍 q を cKDTree で求め、変位
``q - p`` を返す。要素数は N != M でよい。変位が局所点間隔より十分小さい
とき(小さな運動)にのみ「点 i の真の対応先」を当てる — 大変位では最近傍が
別点に張り付く(honest な限界、正則化には :func:`smooth_flow` を併用)。

Args:
    pts0: (N, 3) 時刻 0 の点群。
    pts1: (M, 3) 時刻 1 の点群。
Returns:
    (N, 3) 変位ベクトル場(pts0 と同じ行順)。
Raises:
    ValueError: 形状不正、または pts0 が非空なのに pts1 が空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [scene_flow_rigid](../../../../examples_3d/scene_flow_rigid.py) — `py -3.11 examples_3d/scene_flow_rigid.py`

## 型が繋がる次の op(`flow_scattered` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`scene_flow3d`)

[rigid_flow](rigid_flow.md) · [smooth_flow](smooth_flow.md)

---
*Provenance: scene_flow3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
