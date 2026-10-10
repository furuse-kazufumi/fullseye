---
op: contact_radius_fit_pixelwise
dim: drive
category: tacsim
in: normalmap × matrix × matrix × scalar × scalar
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# contact_radius_fit_pixelwise — DRIVE `tacsim` op

- **データ種**: `normalmap × matrix × matrix × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.contact_radius_fit_pixelwise(normals, X, Y, R: 'float', a0: 'float', centre_xy=(0.0, 0.0), r_max_over_a: 'float' = 2.5, excl_px: 'float' = 1.5) -> 'dict'` (実装を直接呼ぶなら `import tacsim; tacsim.contact_radius_fit_pixelwise(normals, X, Y, R: 'float', a0: 'float', centre_xy=(0.0, 0.0), r_max_over_a: 'float' = 2.5, excl_px: 'float' = 1.5) -> 'dict'`、台帳から引くなら `opsdrive.get("contact_radius_fit_pixelwise")`)

## 使い方

接触半径を**画素ごと**の半径方向スロープに Hertz のスロープ模型 dh/dr(r; a) を連続の a で当てて読む(:func:`contact_radius_fit`
のビンを使わない版。``a0`` はその粗い値)。

:func:`contact_radius_fit` は半径ビン(幅 = 画素ピッチ)の平均に当てるので、a が画素ピッチをまたぐたびに偏りの符号が変わる
(P = 3.5 / 4.0 / 4.5 N で −0.04 / +0.31 / −0.02 %)。P の値そのものは 0.3 % で十分でも、2 枚の差(把持の 2 本指の F_x = P_L − P_R)
では P̂ の**傾き** dP̂/dP が効き、ビン版は傾きを 40 % 狂わせた(pegtactile の PoC で測った)。ここでは r < ``r_max_over_a``·a0 の
画素をそのまま使い、縁 r ≈ a0 の ±``excl_px`` 画素は捨てる —— スロープは r = a で微分が不連続(外側に平方根の尖り)で、
画素と縁の位置関係で値が揺れ、残すと a が画素ピッチの周期で揺れる。SSE(a) を黄金分割(初期区間 [0.8, 1.2]·a0、40 回)で最小化。
``centre_xy`` は既知の中心 (x, y)、単位 m。返り ``a``・``delta`` = a²/R・``rms``(スロープの残差)・``n``(使った画素数)。
**Raises** ``ValueError``: R, a0 ≤ 0、形が合わない、使える画素が 16 未満。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
