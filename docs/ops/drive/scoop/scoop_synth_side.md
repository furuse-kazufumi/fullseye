---
op: scoop_synth_side
dim: drive
category: scoop
in: scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# scoop_synth_side — DRIVE `scoop` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.scoop_synth_side(a_px: 'float', h_px: 'float', *, fill: 'float' = 1.0, heap_frac: 'float' = 0.0, phi_deg: 'float' = 30.0, pitch: 'float' = 0.0001, margin_px: 'int' = 10, supersample: 'int' = 8, noise: 'float' = 0.0, seed: 'int | None' = None) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.scoop_synth_side(a_px: 'float', h_px: 'float', *, fill: 'float' = 1.0, heap_frac: 'float' = 0.0, phi_deg: 'float' = 30.0, pitch: 'float' = 0.0001, margin_px: 'int' = 10, supersample: 'int' = 8, noise: 'float' = 0.0, seed: 'int | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("scoop_synth_side")`)

## 使い方

球冠の椀の中の粉を横から見た被覆率を合成する(軸対称、真値は閉形式)。

- ``fill`` ∈ (0, 1]: 底からの深さの割合 ``y = fill·h`` まで平らに満たす(``heap_frac`` > 0 なら 1 であること)。
- ``heap_frac`` ∈ [0, 1]: すり切りの上に、底面の半径 ``b = heap_frac·a``・安息角 φ の円錐(真ん中に注いで育つ山)。
- 返り: ``side``(透明な椀 = 中身が全部見える被覆率)、``side_above``(縁より上だけ = 金属の椀を横から見た像)、
  ``rim_row``(縁の高さの行境界: 行 ``rim_row`` から下が縁より下)、``axis_col``(軸の列座標、画素の端が整数)、
  ``truth``(``V`` [m³] 閉形式、``V_struck``, ``V_heap``, ``fill``, ``heap_frac``, ``phi_deg``)、``pitch``。
合成と :func:`revolution_volume_side` は同じ軸対称の模型なので、雑音なしの往復は **配管の検査**(独立な被験者は
:func:`two_view_volume` の楕円の山と MuJoCo の球)。**Raises** ``ValueError``: 範囲外、``fill < 1`` で山を載せた。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md) · [tilt_pour_rate](tilt_pour_rate.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
