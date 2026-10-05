---
op: scoop_scene_mjcf
dim: drive
category: scoop
in: scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# scoop_scene_mjcf — DRIVE `scoop` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.scoop_scene_mjcf(n_spheres: 'int' = 500, radius: 'float' = 0.002, *, a: 'float' = 0.03, h: 'float' = 0.012, rim_height: 'float' = 0.1, mu_slide: 'float' = 0.16, mu_roll: 'float' = 0.09, density: 'float' = 2500.0, bowl_mu: 'float' = 0.5, tile: 'float' = 0.006, drop_gap: 'float' = 0.0003, timestep: 'float' = 0.0015, contact_tc: 'float' = 0.006, solver_iterations: 'int' = 50, solver: 'str' = 'CG', cone: 'str' = 'elliptic', condim: 'int' = 6, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.scoop_scene_mjcf(n_spheres: 'int' = 500, radius: 'float' = 0.002, *, a: 'float' = 0.03, h: 'float' = 0.012, rim_height: 'float' = 0.1, mu_slide: 'float' = 0.16, mu_roll: 'float' = 0.09, density: 'float' = 2500.0, bowl_mu: 'float' = 0.5, tile: 'float' = 0.006, drop_gap: 'float' = 0.0003, timestep: 'float' = 0.0015, contact_tc: 'float' = 0.006, solver_iterations: 'int' = 50, solver: 'str' = 'CG', cone: 'str' = 'elliptic', condim: 'int' = 6, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("scoop_scene_mjcf")`)

## 使い方

球冠の椀(縁の半径 ``a``、深さ ``h``、縁の高さ ``rim_height``)を薄板のタイルで張り、真上から剛体球を
``n_spheres`` 個を椀の中から格子で積んで放す場面の MJCF 文字列(**mujoco 不要**、台帳に載る)。

椀は内面が球(半径 ``R = (a² + h²) / 2h``)に接する厚さ 2 mm の板を、緯度の輪ごとに方位で並べる(``tile`` = 板の
目安の辺、隙間ができないよう 1.35 倍に重ねる)。球は底から千鳥の格子で層に積み(椀の内面から ``r + drop_gap``
離す)、縁より上は縁の円柱の中に積む —— 放すと縁より上の柱が崩れて山になり、あふれた球は縁から転がり落ちて床
(高さ 0)に散る。上から落とすと跳ねて椀の中身まで飛び出した(500 個中 172 個しか残らず山ができない、実測)ので、
すくい上げた直後の静かな状態を模す。摩擦の作法は granular の
``heap_scene_mjcf`` と同じ(転がり摩擦は無次元 μ_r × 半径)。
返り: ``xml``, ``positions``(初期中心)、``info``(n, radius, a, h, R, rim_height, bottom_height, mass_each, timestep,
n_tiles, V_struck)。**Raises** ``ValueError``: ``contact_tc < 2 timestep`` / ``h > a`` / 綴り違い / 球が入らない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
