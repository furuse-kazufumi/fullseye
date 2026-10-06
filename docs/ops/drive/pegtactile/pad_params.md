---
op: pad_params
dim: drive
category: pegtactile
in: 
out: table
examples: [poc_knife_tactile_toughness, poc_peg_insertion_tactile, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# pad_params — DRIVE `pegtactile` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.pad_params(R: 'float' = 0.02, E: 'float' = 3000000.0, nu: 'float' = 0.48, mu: 'float' = 1.0, grip: 'float' = 4.0, w: 'float' = 0.005, grasp_below_top: 'float' = 0.008, fov: 'float' = 0.016, n: 'int' = 256, marker_pitch: 'float' = 0.0005, marker_r_px: 'float' = 2.5, dark: 'float' = 0.85, peg_mass: 'float' = 0.04, com_below_top: 'float' = 0.01425) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.pad_params(R: 'float' = 0.02, E: 'float' = 3000000.0, nu: 'float' = 0.48, mu: 'float' = 1.0, grip: 'float' = 4.0, w: 'float' = 0.005, grasp_below_top: 'float' = 0.008, fov: 'float' = 0.016, n: 'int' = 256, marker_pitch: 'float' = 0.0005, marker_r_px: 'float' = 2.5, dark: 'float' = 0.85, peg_mass: 'float' = 0.04, com_below_top: 'float' = 0.01425) -> 'dict'`、台帳から引くなら `opsdrive.get("pad_params")`)

## 使い方

指先パッドの表: ドームの半径 R、ゲルの E・ν、パッドとペグの摩擦 μ、把持力 G₀ [N]、指の半間隔 w(ペグの平取りの半幅)、
把持点のペグ上端からの距離、膜カメラの視野と画素数、マーカー(ピッチ・半径 [px]・濃さ)、ペグの質量と重心(pegfail の既定と同じ)。

寸法の根拠: G₀ = 4 N で a ≈ 2.5 mm(a/R 0.13、Hertz の範囲)、視野 16 mm ≥ 5a(tacsim の窓の条件)、マーカー 0.5 mm = 8 px。
返りに Hertz の複合弾性率 ``Es``・せん断弾性率 ``G``・画素ピッチ ``pitch``・把持だけの接触半径 ``a_grip`` を足す。
**Raises** ValueError: 正であるべき量が正でない、ν が [0, 0.5] の外、n < 64、マーカー間隔が 4 px 未満、
把持力の 1.5 倍で視野が 5a に足りない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`
- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md) · [contact_candidates](contact_candidates.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
