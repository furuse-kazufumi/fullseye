---
op: mindlin_fit
dim: drive
category: tacslip
in: table × matrix × matrix
out: table
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# mindlin_fit — DRIVE `tacslip` op

- **データ種**: `table × matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mindlin_fit(model: 'dict', pts_px, u_m, n_coarse: 'int' = 101, n_fine: 'int' = 41, rigid: 'bool' = False) -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.mindlin_fit(model: 'dict', pts_px, u_m, n_coarse: 'int' = 101, n_fine: 'int' = 41, rigid: 'bool' = False) -> 'dict'`、台帳から引くなら `opsdrive.get("mindlin_fit")`)

## 使い方

マーカー位置 pts_px (M, 2) [px] と変位 u_m (M, 2) [m] に (c/a, μP) を当てる: c/a を粗く走査 → 最良の周りを細かく、μP は各 c で
線形最小二乗。返り ``c_over_a``・``q_ratio`` = 1 − (c/a)³・``muP``・``Q``・``mu``(= μP/P)・``rms_m``・``shift_m``。
``rigid=True`` は剛体シフト (tx, ty) も自由にする —— 試作では**逆効果**だった(外側 900 点の 1/r の尾と縮退して c/a が 0.028 ずれる)ので
既定は切る。実機のドリフトは接触の外の遠方マーカーで別途引くのが筋。真の変位で当てると c/a の誤差 0.001、画像からの追跡では 0.011
(重心の pixel-locking が共通モードで乗る)。**Raises** ValueError: 形の不一致、点が 3 個未満。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
