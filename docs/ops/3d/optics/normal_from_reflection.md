---
op: normal_from_reflection
dim: 3d
category: optics
in: vector × vector
out: vector
examples: [sensor_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# normal_from_reflection — 3D `optics` op

- **データ種**: `vector × vector` → `vector`
- **呼び出し**: `import fullseye as fs; fs.ledger.normal_from_reflection(incident, reflected)` (実装を直接呼ぶなら `import match3d; match3d.normal_from_reflection(incident, reflected)`、台帳から引くなら `ops3d.get("normal_from_reflection")`)

## 使い方

入射+反射から鏡面の法線を復元(deflectometry)。n ∝ (r − d)、入射に逆らう向きへ。

既知パターンの反射を観測 → 面法線 → 積分して鏡面形状。鏡面(反射)物体の形状計測の要。

``incident``(面へ向かう入射方向)と ``reflected``(面から出る反射方向)を単位化し、
``n = unit(r − d)`` を **``n·d <= 0``(入射に逆らう=入射側外向き)** になるよう符号を決めて
返す(単位ベクトル)。``r == d`` なら零ベクトル。最後の軸をベクトルとするので ``(N,3)``
バッチも通る(符号判定は全体の内積和で 1 回だけ行う)。
用途: 既知パターンの反射像から画素ごとに法線を作り(法線マップ)、``integrate_normals`` で
高さに積分、``render_shaded`` で見た目を再現、``reflect`` で検算。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`

## 型が繋がる次の op(`vector` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](reflect.md) · [refract](refract.md) · [cast_shadow](../render/cast_shadow.md) · [shadow_raycast](../render/shadow_raycast.md) · [carve_look_at](../space_carving/carve_look_at.md) · [sample_surface](../superquadric/sample_surface.md)

## 同カテゴリ(`optics`)

[reflect](reflect.md) · [refract](refract.md) · [fresnel_reflectance](fresnel_reflectance.md) · [snell_angle](snell_angle.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
