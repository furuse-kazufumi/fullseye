---
op: fit_plane_3d
dim: 3d
category: geometry
in: points
out: primitive
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fit_plane_3d — 3D `geometry` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import match3d; match3d.fit_plane_3d(points)` (または `ops3d.get("fit_plane_3d")`)

## 使い方

点群 → 最小二乗平面(通過点=重心, 法線=最小主軸, 残差 RMS)。返り値 (point, normal, resid)。

``(N,3)`` の点群(列数 3 でない・3 点未満は ValueError)の重心 ``c`` と散布行列の最小固有値の
固有ベクトルを法線にする(直交距離の二乗和を最小化。``resid = sqrt(λ_min/N)`` = 面からの直交
距離の RMS)。``normal`` は単位ベクトルで **符号は任意**(外向きにするなら視点や重心との関係で
反転する)。3 点なら厳密に通る面で resid=0(BLAS の負の丸めは 0 に clamp)。
点が直線状(2 番目の固有値も 0)だと法線は不定。外れ値に弱い(``ransac_plane`` /
``plane_segmentation`` で先にインライアを取る)。3-D 専用。
後段: ``distance_point_plane`` / ``angle_between_planes`` / ``intersect_planes``、高さ場の
平面度なら ``surface_form_error(degree=1)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md) · [distance_line_line](distance_line_line.md) · [intersect_line_plane](intersect_line_plane.md)

## 同カテゴリ(`geometry`)

[line_from_2points](line_from_2points.md) · [plane_from_3points](plane_from_3points.md) · [angle_3points](angle_3points.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
