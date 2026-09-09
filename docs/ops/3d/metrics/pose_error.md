---
op: pose_error
dim: 3d
category: metrics
in: pose × pose
out: table
examples: [itokawa_self_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# pose_error — 3D `metrics` op

- **データ種**: `pose × pose` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pose_error(R_est, t_est, R_gt, t_gt)` (実装を直接呼ぶなら `import metrics3d; metrics3d.pose_error(R_est, t_est, R_gt, t_gt)`、台帳から引くなら `ops3d.get("pose_error")`)
- **台帳経由の戻り値**: `fullseye.ledger.pose_error(...)` は**宣言 out 型 `table` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.pose_error.raw(...)`、または `metrics3d.pose_error` を直接呼ぶ。

## 使い方

姿勢誤差 = (回転角[度], 並進ノルム)。登録結果の GT 比較。→ (rot_deg, trans_err)。

計算:
- 回転: ``dR = R_est.T @ R_gt`` の回転角 ``arccos((trace(dR) - 1) / 2)`` を度に
  直す(``cos`` は ``[-1, 1]`` にクリップして丸め誤差で NaN にしない)。値域
  ``[0, 180]`` 度。``R_est == R_gt`` なら 0。
- 並進: ``|t_est - t_gt|``(ユークリッドノルム、座標と同じ単位)。

引数: ``R_est``, ``R_gt`` は ``(3, 3)``、``t_est``, ``t_gt`` は長さ 3。float に
変換するだけで **形・直交性の検査はしない** — ``R`` が回転行列でない(反射・
スケール入り)と ``trace`` の式は意味を失い、``(3, 3)`` 以外は行列積の
``ValueError`` か無意味な値になる。``register_fpfh`` / ``icp_point2point_3d`` /
``register_cross`` の返り値 ``(R, t)`` と GT の ``(R, t)`` を、同じ慣習
(``dst ≈ src @ R.T + t``)で渡すこと。

返り値: ``(rot_deg, trans_err)`` の 2 つの ``float``。

注意: 並進誤差は回転誤差と結合している(原点から遠い対象では小さな回転誤差が
大きな並進誤差として現れる)。点群上の実効誤差を見るなら、変換後の雲同士を
``rmse_correspondence``(対応既知)か ``chamfer_distance`` で比べる。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_self_register](../../../../examples_3d/itokawa_self_register.py) — `py -3.11 examples_3d/itokawa_self_register.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`metrics`)

[chamfer_distance](chamfer_distance.md) · [hausdorff_distance](hausdorff_distance.md) · [m3c2_distance](m3c2_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [normal_consistency](normal_consistency.md) · [voxel_iou](voxel_iou.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
