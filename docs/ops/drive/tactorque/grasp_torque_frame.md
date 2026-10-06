---
op: grasp_torque_frame
dim: drive
category: tactorque
in: image2d × image2d × scalar × scalar × scalar × scalar × scalar × scalar
out: table
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# grasp_torque_frame — DRIVE `tactorque` op

- **データ種**: `image2d × image2d × scalar × scalar × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.grasp_torque_frame(m_ref, m_cur, dark: 'float', pitch_px: 'float', r_px: 'float', pitch: 'float', G: 'float', nu: 'float', a: 'float | None' = None, window=None, coef: 'float | None' = None, P: 'float | None' = None, mu: 'float | None' = None, torsion_model: 'str' = 'partial_slip') -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.grasp_torque_frame(m_ref, m_cur, dark: 'float', pitch_px: 'float', r_px: 'float', pitch: 'float', G: 'float', nu: 'float', a: 'float | None' = None, window=None, coef: 'float | None' = None, P: 'float | None' = None, mu: 'float | None' = None, torsion_model: 'str' = 'partial_slip') -> 'dict'`、台帳から引くなら `opsdrive.get("grasp_torque_frame")`)

## 使い方

像から 1 回で: 基準・現在のマーカー像(:func:`tacslip.marker_image`)→ :func:`tacslip.marker_track` → m 単位の場 → :func:`torque_decompose`。
``pitch_px``・``r_px`` = マーカー格子と半径 [px]、``pitch`` = m/px、``window`` は [px] の (cx, cy, R)。マーカー 1 個あたりの面積 = (pitch_px·pitch)²、
発散の近傍半径 = 1.5 ピッチ。``P``・``mu``・``torsion_model`` はねじりの換算(:func:`torque_decompose`、既定は Hertz 接触の部分滑りで
P と mu が要る、平頭押し込み子は ``"no_slip"``)。返り = torque_decompose の表 + ``track``(matched・n0・n1・p0・u [px])。
**Raises** ValueError: 追跡の対応が 9 個未満(双極子に足りない)、pitch ≤ 0、torque_decompose の ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tactorque`)

[punch_pressure](punch_pressure.md) · [punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [ellipse_pressure_shifted](ellipse_pressure_shifted.md) · [pressure_first_moment](pressure_first_moment.md) · [boussinesq_kernel](boussinesq_kernel.md) · [boussinesq_surface_displacement](boussinesq_surface_displacement.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
