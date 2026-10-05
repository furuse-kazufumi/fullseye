---
op: contact_radius_fit
dim: drive
category: tacsim
in: normalmap × matrix × matrix × scalar × scalar
out: table
examples: [poc_peg_insertion_tactile, poc_tacsim_elastic_membrane]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# contact_radius_fit — DRIVE `tacsim` op

- **データ種**: `normalmap × matrix × matrix × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.contact_radius_fit(normals, X, Y, R: 'float', pitch: 'float', centre_xy=None) -> 'dict'` (実装を直接呼ぶなら `import tacsim; tacsim.contact_radius_fit(normals, X, Y, R: 'float', pitch: 'float', centre_xy=None) -> 'dict'`、台帳から引くなら `opsdrive.get("contact_radius_fit")`)

## 使い方

法線場の**半径方向スロープ分布**に Hertz のスロープ模型 dh/dr(r; a) を 1 パラメータ a で当てて接触半径を読む。

模型: 内側 r/R、外側 (2/πR)[r arcsin(a/r) − a √(1 − a²/r²)] (導出、r = a で a/R に連続)。高さの積分を通らないので
FFT 積分の振幅減衰・有限窓の遠方場・高さの基準(オフセット)の影響を受けない。a は [0.2, 3] × 粗い初期値の格子で SSE
(ビンの個数で重み)を最小化し、放物線で副格子に詰める。``centre_xy`` は (x, y)[m]、省略なら法線から高さを積分して重心。
返り: ``a``、``delta`` = a²/R、``rms``(スロープの残差)、``r``・``slope``・``model``(分布)、``centre_xy``。
**Raises** ``ValueError``: R, pitch ≤ 0、形が合わない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`
- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
