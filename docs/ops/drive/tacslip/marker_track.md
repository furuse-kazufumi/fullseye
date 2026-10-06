---
op: marker_track
dim: drive
category: tacslip
in: image2d × image2d × scalar × scalar × scalar
out: table
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# marker_track — DRIVE `tacslip` op

- **データ種**: `image2d × image2d × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.marker_track(m_ref, m_cur, dark: 'float', pitch_px: 'float', r_px: 'float', piv: 'bool' = False) -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.marker_track(m_ref, m_cur, dark: 'float', pitch_px: 'float', r_px: 'float', piv: 'bool' = False) -> 'dict'`、台帳から引くなら `opsdrive.get("marker_track")`)

## 使い方

基準・荷重後のマーカー像(:func:`marker_image`)から変位ベクトル場: 検出(:func:`marker_detect`、2 枚)→ 連続性で対応
(:func:`marker_match_grow`)→ ``u`` = p1 − p0 [px]。返り ``p0``・``p1``・``u``(各 (M, 2))、``matched``、``n0``・``n1``。
``piv=True`` なら :func:`pivops.piv_cross_correlate` の場(第 2 実装、探索 ±0.12 窓)を ``piv_flow``・``piv_info``・``piv_at``(点列で標本化する
関数)として付ける。**Raises** ValueError: 2 枚の形が違う。

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
