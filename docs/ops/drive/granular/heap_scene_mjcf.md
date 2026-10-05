---
op: heap_scene_mjcf
dim: drive
category: granular
in: scalar × scalar
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# heap_scene_mjcf — DRIVE `granular` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.heap_scene_mjcf(n_spheres: 'int' = 1200, radius: 'float' = 0.004, *, mu_slide: 'float' = 0.16, mu_roll: 'float' = 0.09, density: 'float' = 2500.0, orifice_d: 'float' = 0.048, orifice_height: 'float' = 0.06, bin_radius: 'float' = 0.05, timestep: 'float' = 0.0015, base_roll: 'float' = 0.01, base_slide: 'float' = 1.0, solver_iterations: 'int' = 50, solver: 'str' = 'CG', cone: 'str' = 'elliptic', condim: 'int' = 6, contact_tc: 'float' = 0.006, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.heap_scene_mjcf(n_spheres: 'int' = 1200, radius: 'float' = 0.004, *, mu_slide: 'float' = 0.16, mu_roll: 'float' = 0.09, density: 'float' = 2500.0, orifice_d: 'float' = 0.048, orifice_height: 'float' = 0.06, bin_radius: 'float' = 0.05, timestep: 'float' = 0.0015, base_roll: 'float' = 0.01, base_slide: 'float' = 1.0, solver_iterations: 'int' = 50, solver: 'str' = 'CG', cone: 'str' = 'elliptic', condim: 'int' = 6, contact_tc: 'float' = 0.006, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("heap_scene_mjcf")`)

## 使い方

平底ホッパ(正方形の孔、辺 ``orifice_d``)に剛体球を積んだ場面の MJCF 文字列(**mujoco 不要**、台帳に載る)。

球は円筒ビン(半径 ``bin_radius``、底板は高さ ``orifice_height``)の中に層で積む。底板の孔から流れ落ちて平面に山を
作る(山が孔に届くと止まる —— 実際のホッパ下の山と同じ)。孔は 4 枚の板で囲った正方形(Beverloo の式は円孔の
D₀; 正方形は等価直径で比べる)。摩擦は ``(mu_slide, 0.005, mu_roll·R)``: MuJoCo の転がり摩擦係数は長さの単位
(トルク / 法線力)なので、DEM の無次元 μ_r(Sunday ほか 2020 の 0.09)に半径を掛ける。底板は **粗い台**(平面の
滑り摩擦 ``base_slide`` 既定 1.0、転がり ``base_roll`` [m] 既定 0.01; 安息角の実験で底に紙やすりを貼るのと同じ役)。
滑らかな台(μ 0.16)だと最初に落ちた球が転がって逃げ、山ができなかった(実測: 1,200 個が半径 0.15 m の単層に
広がった)。転がり抵抗は滑り摩擦の限界 μ_s g で飽和する(1 球の実測: 転がり係数 0.01 でも 0.1 でも 1 m/s から
0.32 m 走る = 減速 1.6 m/s²)ので、底を止めるのは滑り摩擦のほう。``contact_tc`` = 軟接触の時定数 [s] (solref)。
**2·timestep 以上に取る**: 0.004 s で timestep 2 ms(= 限界)、半径 3.5 mm・2,000 個が発散した(最大速度
12.6 m/s、実測)。解法は既定 CG + 楕円錐(Newton は密な山で 700 球が 280 s 超 → 打ち切り、実測)。

返り: ``xml``(文字列)、``positions``(初期中心 ``(n, 3)``)、``info``(n, radius, mu_slide, mu_roll, orifice_d, bin_radius,
orifice_height, timestep, mass_each, mass_total, column_top, bulk_density_bin)。
**Raises** ``ValueError``: ``contact_tc < 2 timestep`` / 孔がビンに収まらない / 球がビンに入らない / 解法・錐の綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
