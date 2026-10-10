---
op: insertion_grid_summary
dim: drive
category: pegsim
in: table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# insertion_grid_summary — DRIVE `pegsim` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.insertion_grid_summary(rows) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.insertion_grid_summary(rows) -> 'dict'`、台帳から引くなら `opsdrive.get("insertion_grid_summary")`)

## 使い方

成功率の格子を集計する: 行 = {eps_mm, tilt_deg, correct, success} の列から、補正あり/なし × ε₀ × θ₀ の成功率の表と、
「補正なしで全部成功する最大の ε₀」「補正ありの成功数 / 総数」。

返り: ``eps_mm``・``tilt_deg``(軸)、``rate``: {False: (n_eps, n_tilt) の配列, True: 同}、``n_runs``、``max_eps_all_ok``:
{correct: その補正で全 θ₀ が成功する最大の ε₀(無ければ None)}、``success_count``: {correct: (成功数, 総数)}。
**Raises** ``ValueError``: 行が空、鍵が欠ける。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
