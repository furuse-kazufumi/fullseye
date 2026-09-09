---
op: angle_between_lines
dim: 3d
category: geometry
in: primitive
out: measurement
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# angle_between_lines — 3D `geometry` op

- **データ種**: `primitive` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.angle_between_lines(d1, d2)` (実装を直接呼ぶなら `import match3d; match3d.angle_between_lines(d1, d2)`、台帳から引くなら `ops3d.get("angle_between_lines")`)

## 使い方

2 直線方向のなす鋭角(度)。

``arccos(|d̂1·d̂2|)`` を度で返す(float)。絶対値を取るので **[0, 90]**(向きの前後を区別しない。
鈍角側が要るなら ``180 −`` する)。``d1``, ``d2`` は方向ベクトル(長さは問わない、内部で単位化)、
数値の 2 または 3 ベクトルで次元の混在は ValueError。零ベクトルは 90 が返る。
用途: ``fit_line_3d`` / ``line_from_2points`` の方向同士の平行度・直角度チェック(0 に近いほど
平行、90 に近いほど直交)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`geometry`)

[line_from_2points](line_from_2points.md) · [plane_from_3points](plane_from_3points.md) · [angle_3points](angle_3points.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md) · [distance_line_line](distance_line_line.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
