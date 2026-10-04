---
op: membrane_shear_field
dim: drive
category: tacslip
in: table × table × matrix × matrix × table
out: table
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# membrane_shear_field — DRIVE `tacslip` op

- **データ種**: `table × table × matrix × matrix × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.membrane_shear_field(hz: 'dict', mp: 'dict', X, Y, kern: 'dict') -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.membrane_shear_field(hz: 'dict', mp: 'dict', X, Y, kern: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("membrane_shear_field")`)

## 使い方

膜表面の変位場: Mindlin のトラクション q(r) を Cerruti 核で畳んだ接線変位 ``ux``・``uy`` と、法線荷重の半径変位 ``urx``・``ury``
(:func:`hertz_surface_ur` を x, y に分けたもの)[m]、``q``、固着/滑りのマスク ``mask_stick``(r ≤ c)・``mask_slip``(c < r ≤ a)、``r``。
X, Y は格子の座標 [m] (中心が原点)。**Raises** ValueError: X と Y の形が違う、kern の n と合わない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_markers](membrane_markers.md) · [displace_markers](displace_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
