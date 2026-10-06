---
op: pad_context
dim: drive
category: pegtactile
in: table
out: table
examples: [poc_knife_tactile_toughness, poc_peg_insertion_tactile, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# pad_context — DRIVE `pegtactile` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pad_context(pad: 'dict', jitter_px: 'float' = 0.5, seed: 'int' = 7) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.pad_context(pad: 'dict', jitter_px: 'float' = 0.5, seed: 'int' = 7) -> 'dict'`、台帳から引くなら `opsdrive.get("pad_context")`)

## 使い方

膜の合成と読みで 1 回だけ作る道具: 画素中心の格子 (X, Y)、Cerruti 核、3 色の光源、無荷重の膜の背景とマーカーの基準像。

マーカーは ``jitter_px`` の一様ジッタで位相を散らす(印刷のばらつき程度)。**規則格子(0 px)は全マーカーが同じ副画素位相なので、
重心の pixel-locking が場全体の共通モードになり、せん断ゼロでも偽のせん断が出る**(PoC の門で 11 mN → 0.9 mN)。
``seed`` はジッタの乱数。返りの ``_model_cache``・``_sr_cache`` は読みの内部キャッシュ。**Raises** ValueError: jitter < 0。

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

[pad_params](pad_params.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md) · [contact_candidates](contact_candidates.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
