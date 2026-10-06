---
op: hertzian_tangential_inner
dim: drive
category: tacslip
in: matrix × matrix × scalar × scalar × scalar × scalar
out: table
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# hertzian_tangential_inner — DRIVE `tacslip` op

- **データ種**: `matrix × matrix × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hertzian_tangential_inner(x, y, q0: 'float', a: 'float', G: 'float', nu: 'float') -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.hertzian_tangential_inner(x, y, q0: 'float', a: 'float', G: 'float', nu: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("hertzian_tangential_inner")`)

## 使い方

Hertz 形の接線トラクション q0√(1−r²/a²) が円内 r ≤ a に作る表面変位の閉形式(Johnson 1985 式 3.91)。
``ux`` = (πq0/32Ga)[4(2−ν)a² − (4−3ν)x² − (4−ν)y²]、``uy`` = (πq0/32Ga)·2νxy [m]。円の外では成り立たない(そこは畳み込みで)。
**Raises** ValueError: a, G ≤ 0、x と y の形が違う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md) · [displace_markers](displace_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
