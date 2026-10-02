---
op: clothoid_points
dim: drive
category: lateral
in: 
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# clothoid_points — DRIVE `lateral` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.clothoid_points(length: 'float', s, *, kappa0: 'float' = 0.0, kappa1: 'float' = 0.0, start=(0.0, 0.0), heading0: 'float' = 0.0) -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.clothoid_points(length: 'float', s, *, kappa0: 'float' = 0.0, kappa1: 'float' = 0.0, start=(0.0, 0.0), heading0: 'float' = 0.0) -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("clothoid_points")`)

## 使い方

曲率が弧長に一次 κ(s) = κ₀ + (κ₁ − κ₀) s / length の曲線(クロソイドの一部。κ₀ = κ₁ なら円弧・直線)の点。

``s``: 0 ≤ s ≤ length の弧長(配列)。``start``・``heading0``: 始点と始点の向き。左へ曲がる曲率を正。
クロソイドの部分は標準形(A² = 1/|dκ/ds|)をフレネル積分で写し、始点・向きに合わせて回す(数値積分を使わない)。
返り値: ``points`` (N, 2)、``heading`` (N,)、``curvature`` (N,)、``A``(クロソイドのパラメータ、円弧・直線は inf)。

**Raises** ``ValueError``: length ≤ 0、s が範囲外、非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
