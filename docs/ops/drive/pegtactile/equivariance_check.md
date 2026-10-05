---
op: equivariance_check
dim: drive
category: pegtactile
in: any × any × signal × scalar × signal
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# equivariance_check — DRIVE `pegtactile` op

- **データ種**: `any × any × signal × scalar × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.equivariance_check(render, op, angles, n: 'int', centre) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.equivariance_check(render, op, angles, n: 'int', centre) -> 'dict'`、台帳から引くなら `opsdrive.get("equivariance_check")`)

## 使い方

同変性の門の部品: 形を角 θ だけ回して描き(``render(θ)`` → 画像)、知覚 op(``op(画像)`` → (row, col, 向き))の答えが群の作用
どおりに変わるか。期待 = 位置は ``centre`` = (row, col) まわりに θ 回る、向きは θ 進む(mod 2π/n、n = 0 なら向きは比べない)。
返り ``pos_err_px``(最大)、``ang_err_deg``(最大、mod 2π/n の最短距離、比べなければ nan)、``rows``(角ごと)。
**Raises** ValueError: render・op が呼べない、角が 1 つも無い・有限でない、n < 0、centre が 2 成分でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
