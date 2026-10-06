---
op: symmetry_fold
dim: drive
category: pegsym
in: scalar × scalar
out: scalar
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# symmetry_fold — DRIVE `pegsym` op

- **データ種**: `scalar × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.symmetry_fold(angle: 'float', n: 'int') -> 'float'` (実装を直接呼ぶなら `import pegsym; pegsym.symmetry_fold(angle: 'float', n: 'int') -> 'float'`、台帳から引くなら `opsdrive.get("symmetry_fold")`)

## 使い方

角を n 回対称の商 SO(2)/C_n の代表 (−π/n, π/n] に畳む(n = 1 は (−π, π]、n = 0 = 円は 0)。群の恒等式
symmetry_fold(α + 2πk/n, n) = symmetry_fold(α, n) が門。**Raises** ValueError: n < 0、角が有限でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
