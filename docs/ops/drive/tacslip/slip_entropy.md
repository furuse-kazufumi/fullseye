---
op: slip_entropy
dim: drive
category: tacslip
in: signal
out: scalar
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# slip_entropy — DRIVE `tacslip` op

- **データ種**: `signal` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.slip_entropy(mag, bins: 'int' = 16, vmax=None) -> 'float'` (実装を直接呼ぶなら `import tacslip; tacslip.slip_entropy(mag, bins: 'int' = 16, vmax=None) -> 'float'`、台帳から引くなら `opsdrive.get("slip_entropy")`)

## 使い方

変位の大きさ |u| の列のヒストグラム(bins 本、範囲 [0, vmax] —— 省略時は最大値)の Shannon エントロピーを ln(bins) で正規化(0..1)。
Yuan 2017 の滑りの指標: 固着核が縮んで滑り環の勾配に乗るマーカーが増えると上がる。**Raises** ValueError: 点が無い、bins < 2。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
