---
op: refract
dim: 3d
category: optics
in: vector × normals
out: normals
examples: [snell_refraction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# refract — 3D `optics` op

- **データ種**: `vector × normals` → `normals`
- **呼び出し**: `import fullseye as fs; fs.ledger.refract(d, n, eta1=1.0, eta2=1.5)` (実装を直接呼ぶなら `import match3d; match3d.refract(d, n, eta1=1.0, eta2=1.5)`、台帳から引くなら `ops3d.get("refract")`)

## 使い方

Snell 屈折(ベクトル形)。d=入射(面へ向かう), n=入射側外向き法線, 屈折率 eta1→eta2。

透明体を通る光線の曲がりを厳密に。全反射(TIR)なら None。ガラス/レンズ/水中の像歪み計算に。
契約は単一ベクトル。(N,3) バッチも通るが、**1 本でも TIR ならバッチ全体が None**
(per-ray マスクはしない)。★**バッチなら 1 本ずつ回すのではなく**
:func:`glassmirror.refract_rays` を使うこと —— あちらは光線ごとに TIR を判定して
``(方向, TIR マスク)`` を返す(TIR の光線は鏡面反射で埋める)。この関数は
「1 本でも欠けたら答えを出さない」fail-closed 側の口として残してある。

``d``, ``n`` は最後の軸をベクトルとして単位化する。``n`` は入射側(``d·n < 0`` になる向き)で
渡すこと。逆向きに渡すと ``cos θi`` が負になり、例外なく誤った方向が返る。返り値は単位ベクトル
(``eta·d + (eta·cosθi − cosθt)·n``、``eta = eta1/eta2``)。``eta1 == eta2`` なら ``d`` がそのまま
返る。角度で扱うなら ``snell_angle``、反射率は ``fresnel_reflectance(cos_i, eta1, eta2)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [snell_refraction](../../../../examples_3d/snell_refraction.py) — `py -3.11 examples_3d/snell_refraction.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](reflect.md) · [normal_consistency](../metrics/normal_consistency.md) · [ransac_cylinder](../robust_fit/ransac_cylinder.md) · [orient_normals](../normals_orient/orient_normals.md)

## 同カテゴリ(`optics`)

[reflect](reflect.md) · [fresnel_reflectance](fresnel_reflectance.md) · [normal_from_reflection](normal_from_reflection.md) · [snell_angle](snell_angle.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
