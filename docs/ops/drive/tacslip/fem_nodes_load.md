---
op: fem_nodes_load
dim: drive
category: tacslip
in: text × text
out: table
examples: [poc_tacsim_marker_shear, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# fem_nodes_load — DRIVE `tacslip` op

- **データ種**: `text × text` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fem_nodes_load(dirpath: 'str', name: 'str') -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.fem_nodes_load(dirpath: 'str', name: 'str') -> 'dict'`、台帳から引くなら `opsdrive.get("fem_nodes_load")`)

## 使い方

有限要素の表面節点テキスト(Robo-Touch/Taxim リポジトリ同梱、MIT ライセンス)を 3 本読む: ``<dirpath>/<name>_{x,y,z}.txt``、
タブ区切り・1 行ヘッダ ``Node Number / X Location (m) / Y Location (m) / Z Location (m) / Directional Deformation (m)``、単位 m。
3 本は同じ節点集合で最終列だけがその方向の変位。返り ``id``・``X``・``Y``・``Z``・``dx``・``dy``・``dz``(各 (N,))、``n``、``name``。
**Raises** FileNotFoundError: ファイルが無い。ValueError: ヘッダが違う、列が 5 本でない、3 本の節点座標が一致しない(fail-closed)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
