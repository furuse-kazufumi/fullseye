---
op: polygon_area
dim: drive
category: japan
in: any
out: scalar
examples: [poc_driving_school, poc_thermal_drift_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# polygon_area — DRIVE `japan` op

- **データ種**: `any` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.polygon_area(poly: 'np.ndarray | Sequence[Sequence[float]]') -> 'float'` (実装を直接呼ぶなら `import driveplateau; driveplateau.polygon_area(poly: 'np.ndarray | Sequence[Sequence[float]]') -> 'float'`、台帳から引くなら `opsdrive.get("polygon_area")`)

## 使い方

単純多角形の符号つき面積(靴紐公式)。反時計回りで正。

Args:
    poly: (k,2) の頂点列。閉じていなくてよい。

Raises:
    ValueError: 形が (k,2) でない、k < 3、非有限値。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_thermal_drift_metrology](../../../../examples/poc_thermal_drift_metrology.py) — `py -3.11 examples/poc_thermal_drift_metrology.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](osm_parse.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md)

---
*Provenance: driveplateau.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
