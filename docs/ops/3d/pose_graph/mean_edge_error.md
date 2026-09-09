---
op: mean_edge_error
dim: 3d
category: pose_graph
in: pose
out: measurement
examples: [sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# mean_edge_error — 3D `pose_graph` op

- **データ種**: `pose` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.mean_edge_error(poses, edges)` (実装を直接呼ぶなら `import pose_graph; pose_graph.mean_edge_error(poses, edges)`、台帳から引くなら `ops3d.get("mean_edge_error")`)

## 使い方

エッジ残差の RMS(姿勢グラフの整合度)。→ scalar。

各エッジ ``(i, j, rvec_meas, t_meas[, w_rot, w_trans])`` について、予測相対姿勢 ``T_i⁻¹ ∘ T_j`` と
計測 ``(rvec_meas, t_meas)`` の食い違い ``measured⁻¹ ∘ predicted`` を回転ベクトル 3 成分 + 並進
3 成分の 6 次元残差にし(それぞれ ``sqrt(w_rot)``、``sqrt(w_trans)`` を掛ける。重み省略時は 1)、
全エッジ・全成分をまとめた 2 乗平均平方根を返す。``optimize_pose_graph`` の返り値 ``rmse`` と
同じ量で、最適化前後の比較に使う。

- ``poses``: (N,6) にリシェイプできる ``[rvec | t]``(world←body)。
- ``edges``: 上記タプルのリスト。空なら 0.0 を返す。

注意: 回転成分(rad)と並進成分(座標の単位)を同じ配列で平均するため、値の次元は混在する。
並進のスケールが大きいシーンでは並進項が支配的になるので、単位を揃えたいときは ``w_rot`` /
``w_trans`` で重み付けする。エッジ添字の範囲検証はこの関数では行わない(負の添字は numpy の
折り返しで別ノードを黙って参照する。``optimize_pose_graph`` は検証する)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`pose_graph`)

[optimize_pose_graph](optimize_pose_graph.md) · [relative_pose](relative_pose.md)

---
*Provenance: pose_graph.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
