---
op: pad_tactile_frame
dim: drive
category: pegtactile
in: scalar × signal × table
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# pad_tactile_frame — DRIVE `pegtactile` op

- **データ種**: `scalar × signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pad_tactile_frame(P: 'float', q_uv, pad: 'dict', ctx=None, noise: 'float' = 0.0, seed: 'int' = 0, torsion: 'float' = 0.0, torsion_model: 'str' = 'partial_slip') -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.pad_tactile_frame(P: 'float', q_uv, pad: 'dict', ctx=None, noise: 'float' = 0.0, seed: 'int' = 0, torsion: 'float' = 0.0, torsion_model: 'str' = 'partial_slip') -> 'dict'`、台帳から引くなら `opsdrive.get("pad_tactile_frame")`)

## 使い方

パッド 1 枚の合成像: Hertz 押し込みの陰影(:func:`tacsim.membrane_render_rgb`)+ 変位で中心を移したマーカー
(:func:`tacslip.membrane_render_markers`、補間で歪めない)。``noise`` は画素の正規雑音の σ。
返り ``rgb``(マーカー入り、(n, n, 3))、``shading``(マーカー無し = 力の読み取り用、実機はマーカーの除去が要る)、``pts``
(マーカー中心の真値 [px])、``truth``(P・q・φ・Q・c/a・滑りの印・a・ねじり・ねじりの模型と全滑りの印)。ねじりの場の模型は
``torsion_model``(既定 ``"partial_slip"``、:func:`pad_marker_displacement`)。**Raises** ValueError: P ≤ 0、noise < 0、綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_read](pad_tactile_read.md) · [contact_candidates](contact_candidates.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
