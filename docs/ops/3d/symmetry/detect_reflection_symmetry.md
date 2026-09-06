---
op: detect_reflection_symmetry
dim: 3d
category: symmetry
in: points
out: primitive
examples: [dl_mesh_symmetry, itokawa_symmetry_honest, reflection_symmetry, symmetry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# detect_reflection_symmetry — 3D `symmetry` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import symmetry3d; symmetry3d.detect_reflection_symmetry(points)` (または `ops3d.get("detect_reflection_symmetry")`)

## 使い方

PCA 主軸を法線とする候補平面(重心通過)から最良の反射対称面を選ぶ。

→ dict{plane_point, plane_normal, score, all_scores, margin}。
score が小さいほど対称。

★ **``score`` だけで採否を決めない。``margin`` を見ること**(2026-09-06 追加)。
``margin`` は 2 位と 1 位の score の差で、**候補が団子なら答えはくじ引き**
である、という警告になる。実測(1500 点):

==================  ========  ========  =========
形状                best      2 位      margin
==================  ========  ========  =========
箱(鏡映面が 3 枚)     0.9397    0.9499     0.0102
角柱つきの箱          0.9876    0.9918     0.0043
球                    1.0490    1.0551     0.0062
一様乱数の立方体      1.0608    1.3435     0.2828
==================  ========  ========  =========

対称面が複数ある形ほど margin は小さい —— これは不具合ではなく、そういう形
だという情報である。点群位置合わせの PoC が同じ構造を測っていて、PCA の
候補は**素の直方体で 83 % が反転した象限を掴む**が、そのとき先に潰れるのは
残差ではなく候補どうしの margin だった(0.42 → 0.066 → 0.039)。**残差でなく
margin で採否を見る**、が両方に共通する結論。

★ **``score`` は 0 に近づかない。** 厳密に対称な形でも点の間隔が床を作る
(上の表で箱が 0.94)。「0 に近いか」ではなく「同じ形を鏡映せずに測った値」や
「点間隔」と比べること。

★ **候補は PCA の 3 軸だけ**。真の対称面が主軸のどれとも一致しない形では
見つからず、しかも黙って 3 つのうち最良を返す。密に振った候補が要るなら
``reflection_symmetry_score`` を直接掃引すること。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dl_mesh_symmetry](../../../../examples_3d/dl_mesh_symmetry.py) — `py -3.11 examples_3d/dl_mesh_symmetry.py`
- [itokawa_symmetry_honest](../../../../examples_3d/itokawa_symmetry_honest.py) — `py -3.11 examples_3d/itokawa_symmetry_honest.py`
- [reflection_symmetry](../../../../examples_3d/reflection_symmetry.py) — `py -3.11 examples_3d/reflection_symmetry.py`
- [symmetry](../../../../examples_3d/symmetry.py) — `py -3.11 examples_3d/symmetry.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`symmetry`)

[detect_rotational_symmetry](detect_rotational_symmetry.md) · [reflect_points](reflect_points.md) · [reflection_symmetry_score](reflection_symmetry_score.md)

---
*Provenance: symmetry3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
