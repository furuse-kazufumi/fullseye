---
op: rear_axle_path
dim: drive
category: lateral
in: any
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# rear_axle_path — DRIVE `lateral` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rear_axle_path(front_path, wheelbase: 'float', *, rear0=None) -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.rear_axle_path(front_path, wheelbase: 'float', *, rear0=None) -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("rear_axle_path")`)

## 使い方

前車軸の中心の折線の軌跡から、すべりなしで引かれる後車軸の中心の軌跡(区間ごとに厳密な追跡曲線)。

前が直線を Δ 進む間、棒(後 → 前)と直線のなす角 θ は tan(θ/2) = tan(θ₀/2) e^{−Δ/L}(厳密)。折線の頂点ごとに
これを繋ぐ。``rear0``: 後車軸の初めの位置(None なら最初の区間の向きに L だけ後ろ = 真っすぐ)。|前 − 後| = L を要求。
返り値: ``rear`` (N, 2)、``heading`` (N,)(車体の向き = 棒の向き)、``gamma`` (N,)(棒と前の進む向きのなす角、
左旋回で正)。

**Raises** ``ValueError``: 形の誤り、重複点、L ≤ 0、|前 − 後| ≠ L、θ₀ = π(後ろ向きに押す)。

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
