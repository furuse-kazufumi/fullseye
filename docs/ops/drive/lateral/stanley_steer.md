---
op: stanley_steer
dim: drive
category: lateral
in: any
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# stanley_steer — DRIVE `lateral` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stanley_steer(front_pose, path, *, gain: 'float', speed, softening: 'float' = 0.0, max_steer: 'float' = inf, start_index=None, window: 'int' = 40) -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.stanley_steer(front_pose, path, *, gain: 'float', speed, softening: 'float' = 0.0, max_steer: 'float' = inf, start_index=None, window: 'int' = 40) -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("stanley_steer")`)

## 使い方

Stanley の舵角 δ = ψ_e + atan2(−k e, k_s + v)(前車軸の中心の横ずれ e は経路の左が正、ψ_e = 経路の向き − ψ)。

``front_pose``: (3,) または (N, 3)。``max_steer`` で切る(切ると :func:`stanley_straight_decay` の閉形式から外れる)。
返り値: ``steer``, ``lateral``, ``heading_error``, ``index``。

**Raises** ``ValueError``: 形の誤り、k ≤ 0、v < 0、k_s < 0、max_steer ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
