---
op: largedef_c1_coefficient
dim: drive
category: tacdome
in: scalar
out: scalar
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# largedef_c1_coefficient — DRIVE `tacdome` op

- **データ種**: `scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.largedef_c1_coefficient(n: 'float', reading: 'str' = 'derived') -> 'float'` (実装を直接呼ぶなら `import tacdome; tacdome.largedef_c1_coefficient(n: 'float', reading: 'str' = 'derived') -> 'float'`、台帳から引くなら `opsdrive.get("largedef_c1_coefficient")`)

## 使い方

式 (3) の 1 次の係数 c₁: ``"derived"`` = 2n/(1+n)(導出)、``"printed"`` = (4+2n)/(1+n)(原文の活字)、``"memo"`` = 2/(1+n)。

**Raises** ``ValueError``: 知らない読み、n が [1, 3] の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_contact](large_deformation_contact.md) · [large_deformation_inverse](large_deformation_inverse.md) · [mdr_spring_bed](mdr_spring_bed.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
