---
op: reflect
dim: 3d
category: optics
in: vector × normals
out: normals
examples: [sensor_seg, snell_refraction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# reflect — 3D `optics` op

- **データ種**: `vector × normals` → `normals`
- **呼び出し**: `import fullseye as fs; fs.ledger.reflect(d, n)` (実装を直接呼ぶなら `import match3d; match3d.reflect(d, n)`、台帳から引くなら `ops3d.get("reflect")`)

## 使い方

入射方向 d を法線 n の面で鏡面反射。r = d − 2(d·n)n。

``d``, ``n`` は内部で単位化する(長さは問わない)ので、返り値 ``r`` も単位ベクトル。最後の軸を
ベクトルとみなすので ``(3,)`` でも ``(N,3)`` のバッチでも動く(2-D の ``(2,)`` も可)。``n`` の
向きは問わない(``n`` と ``−n`` で同じ ``r``)。``d`` は「面へ向かう」向き(光線の進行方向)で
渡す。零ベクトルは 1e-12 で割って 0 のまま返る(例外は出ない)。
用途: ``normal_from_reflection`` の逆問題、鏡面レンダの視線追跡(``refract`` と対)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`
- [snell_refraction](../../../../examples_3d/snell_refraction.py) — `py -3.11 examples_3d/snell_refraction.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [refract](refract.md) · [normal_consistency](../metrics/normal_consistency.md) · [ransac_cylinder](../robust_fit/ransac_cylinder.md) · [orient_normals](../normals_orient/orient_normals.md)

## 同カテゴリ(`optics`)

[refract](refract.md) · [fresnel_reflectance](fresnel_reflectance.md) · [normal_from_reflection](normal_from_reflection.md) · [snell_angle](snell_angle.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
