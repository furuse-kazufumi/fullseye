---
op: reflect_points
dim: 3d
category: symmetry
in: points
out: points
examples: [reflection_symmetry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# reflect_points — 3D `symmetry` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.reflect_points(points, plane_point, plane_normal)` (実装を直接呼ぶなら `import symmetry3d; symmetry3d.reflect_points(points, plane_point, plane_normal)`、台帳から引くなら `ops3d.get("reflect_points")`)

## 使い方

点群を平面(点 plane_point・法線 plane_normal)で鏡映。→ (N,3)。

各点 p の平面からの符号付き距離 ``d = (p - plane_point) · n``(n は正規化した法線)を取り、
``p' = p - 2 d n`` を返す(Householder 鏡映)。平面上の点は動かず、平面の両側の点が入れ替わる。
点の並び順は保たれるので ``p'[i]`` は ``p[i]`` の鏡像。座標の単位はそのまま。

- ``points``: (N,3) の配列(float に変換)。形状検証はしない。
- ``plane_point``: 平面上の 1 点 (3,)。``plane_normal``: 法線 (3,)(長さは任意、内部で正規化。
  符号は結果に影響しない)。

注意: 法線はノルムに 1e-12 を足して割るため、ゼロベクトルを渡しても例外にならず点群がほぼ
そのまま返る(fail-closed ではない)。``reflection_symmetry_score`` /
``detect_reflection_symmetry`` の内部で使うほか、検出した対称面で欠損側を埋める(鏡像を元の
点群に連結する)形状補完にも使える。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [reflection_symmetry](../../../../examples_3d/reflection_symmetry.py) — `py -3.11 examples_3d/reflection_symmetry.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`symmetry`)

[detect_reflection_symmetry](detect_reflection_symmetry.md) · [detect_rotational_symmetry](detect_rotational_symmetry.md) · [reflection_symmetry_score](reflection_symmetry_score.md)

---
*Provenance: symmetry3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
