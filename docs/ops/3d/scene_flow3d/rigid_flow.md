---
op: rigid_flow
dim: 3d
category: scene_flow3d
in: points × points
out: pose
examples: [scene_flow_rigid]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# rigid_flow — 3D `scene_flow3d` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import scene_flow3d; scene_flow3d.rigid_flow(pts0, pts1, max_iter: 'int' = 20) -> 'dict'` (または `ops3d.get("rigid_flow")`)
- **台帳経由の戻り値**: `fullseye.ledger.rigid_flow(...)` は**宣言 out 型 `pose` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.rigid_flow.raw(...)`、または `scene_flow3d.rigid_flow` を直接呼ぶ。

## 使い方

pts0 -> pts1 を説明する単一剛体運動を最近傍対応 + Kabsch(ICP 風)で推定。

恒等変換から出発し、毎反復で現姿勢の点群から ``pts1`` への最近傍対応を取り、
:func:`registration.kabsch` で閉形式に (R, t) を求めて累積する。対応 index が
前反復と一致(= 収束)するか ``max_iter`` で停止する。収束判定は index の
安定性のみに依存するため**スケール不変**(絶対 epsilon を使わない)。

Args:
    pts0: (N, 3) 時刻 0 の点群(N >= 3、回転を一意に決めるため)。
    pts1: (M, 3) 時刻 1 の点群(M >= 1、N と一致不要)。
    max_iter: ICP 反復上限。
Returns:
    dict: ``{"R": (3,3) 回転, "t": (3,) 並進, "rmse": 整合後の点-最近傍
    RMS 距離}``。R は真の回転(det=+1)。rmse は実測値(詐称なし)。
Raises:
    ValueError: 形状不正、pts0 < 3 点、または pts1 が空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [scene_flow_rigid](../../../../examples_3d/scene_flow_rigid.py) — `py -3.11 examples_3d/scene_flow_rigid.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`scene_flow3d`)

[nearest_neighbor_flow](nearest_neighbor_flow.md) · [smooth_flow](smooth_flow.md)

---
*Provenance: scene_flow3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
