---
op: ttc_from_flow
dim: drive
category: ttc
in: image2d × image2d
out: table
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# ttc_from_flow — DRIVE `ttc` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ttc_from_flow(u, v, dt: 'float', *, foe=None, mask=None, min_speed: 'float' = 0.001, at_first_frame: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import drivettc; drivettc.ttc_from_flow(u, v, dt: 'float', *, foe=None, mask=None, min_speed: 'float' = 0.001, at_first_frame: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("ttc_from_flow")`)

## 使い方

光学流から τ(秒): ``{"tau_map", "tau", "n", "foe"}``。

:func:`sceneflow.time_to_contact`(画素ごと、コマ単位、FoE からの半径² / 半径方向の流れ)を秒に直す。
2 コマの差分の流れが返すのは **2 コマ目の時刻の τ**(``Z₁ / (Z₀ − Z₁)`` コマ)なので、``at_first_frame=True``
(既定)は 1 コマ足して最初のコマの τ にする(等速なら厳密、:func:`ttc_truth` と同じ時刻)。
``foe`` を省くと流れから推定する(:func:`sceneflow.focus_of_expansion`)。真の FoE は :func:`foe_from_motion`。
``tau`` は ``mask``(省略時は全画素)の中で有限・正の τ の中央値(無ければ ``inf``)、``n`` はその画素数。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ttc`)

[relative_motion](relative_motion.md) · [foe_from_motion](foe_from_motion.md) · [flow_from_depth_motion](flow_from_depth_motion.md) · [ttc_truth](ttc_truth.md) · [ttc_from_scale](ttc_from_scale.md) · [ttc_from_range](ttc_from_range.md) · [label_extent](label_extent.md) · [foe_from_flow](foe_from_flow.md)

---
*Provenance: drivettc.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
