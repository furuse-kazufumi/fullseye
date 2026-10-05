---
op: contact_radius_ring
dim: drive
category: tacsim
in: image2d × scalar
out: table
examples: [poc_tacscalib_sphere_lut, poc_tacsim_elastic_membrane]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# contact_radius_ring — DRIVE `tacsim` op

- **データ種**: `image2d × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.contact_radius_ring(h, pitch: 'float', n_az: 'int' = 72, step_px: 'float' = 0.25, r_max_px: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import tacsim; tacsim.contact_radius_ring(h, pitch: 'float', n_az: 'int' = 72, step_px: 'float' = 0.25, r_max_px: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("contact_radius_ring")`)

## 使い方

高さ場から接触半径 a を**模型なし**で読む: 接触縁 r = a は半径方向の傾き |∂h/∂r| が最大になる輪(Hertz では内側 r/R で
増え、外側は √ で急に落ちるカスプ)。方位角 ``n_az`` 本の半径線に沿って |∇h| を ``step_px`` 刻みで双線形補間し、各線の
ピークを放物線補間で副画素化 → 72 点に :func:`measure.fit_circle`(第 2 実装)と半径の中央値。

返り: ``a``(中央値 × pitch)[m]、``a_circle``(円当てはめの半径 × pitch)、``r_px``・``cy``・``cx``・``rms_px``(円)、
``radii_px``(方位角ごとのピーク半径)、``centre``(重心 (cy, cx))、``bias_px_per_a``(分解能の限界の目安 = −0.7 px / a、
双線形補間がカスプを約 1 px 平滑するので a が 14 px なら −5 %、21 px なら −3 % 内側に出る —— 実測値、模型なしの代償)。
しきい値の帯の重心(試作 v1)が 9 % 内側に寄った反省から、帯でなくピーク位置を使い、半径方向の傾きは h の双線形標本の
1 px スパン差分(np.gradient の 2 px より平滑が少ない)で取る。既定(``r_max_px=None``)は窓の縁 − 2 px まで探す。膜の裾の外側に
別のピーク(隣の接触・縁の影)がある実機の画像では ``r_max_px`` を明示すること。
**Raises** ``ValueError``: へこみが無い、pitch ≤ 0、探索半径が 2 px 未満(へこみが窓の縁に寄りすぎ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`
- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
