---
op: offtracking_circle
dim: drive
category: lateral
in: 
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# offtracking_circle — DRIVE `lateral` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.offtracking_circle(front_radius: 'float', wheelbase: 'float', arc_length, *, track: 'float' = 0.0, gamma0: 'float' = 0.0) -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.offtracking_circle(front_radius: 'float', wheelbase: 'float', arc_length, *, track: 'float' = 0.0, gamma0: 'float' = 0.0) -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("offtracking_circle")`)

## 使い方

内輪差の過渡(閉形式): 前車軸の中心が半径 R の円に入ってから弧長 s 進んだときの車の姿勢と内側の車輪の半径。

後車軸の中心は前車軸の中心を長さ L の棒で引く(すべりなし)。棒と前の速度のなす角 γ は dγ/ds = 1/R − sin γ / L。
a = 1/R、b = 1/L、k = √(b² − a²)、t± = (b ± k)/a(t− = tan(γ*/2)、sin γ* = L/R)とすると
Q = ((t+ − t₀)/(t− − t₀)) e^{k s}、tan(γ/2) = (Q t− − t+)/(Q − 1)。

``arc_length``: s ≥ 0(配列可)。``track``: 輪距 t(内側の車輪の位置に使う)。``gamma0``: 円に入るときの γ(0 = 直線から
まっすぐ入る、0 ≤ γ₀ < γ*)。返り値(s と同じ形): ``gamma``、``rear_radius``(後車軸の中心の半径
√(R² + L² − 2RL sin γ))、``front_inner_wheel_radius``・``rear_inner_wheel_radius``(内側の車輪の旋回中心からの距離)、
``offtracking``(前内輪 − 後内輪)、``steady``(s → ∞ の値の dict)。

**Raises** ``ValueError``: R ≤ L(定常が無い)、s < 0、γ₀ が範囲外、t/2 ≥ 後輪の半径。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [rear_axle_path](rear_axle_path.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
