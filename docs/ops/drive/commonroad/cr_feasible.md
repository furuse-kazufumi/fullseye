---
op: cr_feasible
dim: drive
category: commonroad
in: table
out: table
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# cr_feasible — DRIVE `commonroad` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cr_feasible(run, *, params=None, tol=(0.02, 0.02, 0.03)) -> 'dict'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.cr_feasible(run, *, params=None, tol=(0.02, 0.02, 0.03)) -> 'dict'`、台帳から引くなら `opsdrive.get("cr_feasible")`)

## 使い方

運動学の実現可能性(採点器 ``solution_feasible`` と同じ考え方の第 2 実装)。

各遷移で記録した u から :func:`ks_step` を回し、次の状態と |Δx|, |Δy| < tol[0], tol[1]、|Δψ| < tol[2] か、u が制限内か
(δ̇ ∈ [ddelta_min, ddelta_max]、|a| ≤ a_max)、摩擦円 a² + (v ψ̇)² ≤ a_max² か(ψ̇ = v/l_wb tan δ)。

返り値 ``{"feasible", "max_pos_err", "max_psi_err", "violations": [(k, reason)], "n_transitions"}``。

**Raises** ``ValueError``: run が cr_drive の物でない、tol が 3 要素でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`commonroad`)

[cr_synthetic](cr_synthetic.md) · [cr_read](cr_read.md) · [cr_route](cr_route.md) · [ks_step](ks_step.md) · [cr_drive](cr_drive.md) · [cr_drive_sweep](cr_drive_sweep.md) · [cr_collision](cr_collision.md) · [cr_solution_xml](cr_solution_xml.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
