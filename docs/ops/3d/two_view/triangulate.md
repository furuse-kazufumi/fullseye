---
op: triangulate
dim: 3d
category: two_view
in: image2d × image2d
out: points
examples: [sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# triangulate — 3D `two_view` op

- **データ種**: `image2d × image2d` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.triangulate(pts1, pts2, P1, P2)` (実装を直接呼ぶなら `import twoview; twoview.triangulate(pts1, pts2, P1, P2)`、台帳から引くなら `ops3d.get("triangulate")`)

## 使い方

DLT 三角測量: 2 視点の対応点 + 射影行列 → 3D 点。→ (N,3)。

**無限遠点は ``NaN`` で返す**(``±inf`` にはしない)。同次座標の第 4 成分が 0 =
2 本の視線が平行で、その対応は有限の 3-D 点を決めない。以前はそのまま割って
``±inf`` を出していたが、それだと下流の cheirality 判定 ``depth > 0`` が
**``inf`` を「カメラ前方」として数える**(``inf > 0`` は ``True``)。
:func:`recover_pose` は 4 つの (R, t) 候補のうち前方点が最多のものを選ぶので、
無限遠点が票を持つと候補選択が静かに歪む。``NaN`` なら比較が ``False`` になり、
数えられずに済む(2026-09-02、chain_fuzz が到達して発覚)。

ほぼ平行だが厳密には平行でない対応は、**大きな有限値**として返る。これは
NaN では拾えないので、呼び手側で距離の妥当性を見る必要がある。

Raises ValueError: 点が (N,2) でない/非有限/対応数不一致。

補足:
- ``P1``, ``P2`` は (3,4) の射影行列(``K[R|t]``)。対応点はその P と同じ画素座標系の (N,2)。cam1 を基準にするなら ``P1 = K1[I|0]``。
- 各点ごとに 4×4 の係数行列を SVD する Python ループ(点数に比例)。返り値は float64 (N,3)。
- 深度の正負(cheirality)は検査しない。前後判定が要るなら結果の z と ``R X + t`` の z を見る(``recover_pose`` が内部で行う)。
- 解の単位は P の並進 t と同じ。``recover_pose`` 由来の P なら |t|=1 のスケール。
- 決定論的。(N,2) でない・非有限・点数不一致は ``ValueError``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`two_view`)

[fundamental_8point](fundamental_8point.md) · [essential_8point](essential_8point.md) · [recover_pose](recover_pose.md) · [sampson_distance](sampson_distance.md)

---
*Provenance: twoview.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
