---
op: pure_pursuit_circle_offset
dim: drive
category: lateral
in: 
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# pure_pursuit_circle_offset — DRIVE `lateral` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.pure_pursuit_circle_offset(radius: 'float', lookahead: 'float', wheelbase: 'float', *, understeer: 'float' = 0.0, speed: 'float' = 0.0, params: 'Optional[dict]' = None) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.pure_pursuit_circle_offset(radius: 'float', lookahead: 'float', wheelbase: 'float', *, understeer: 'float' = 0.0, speed: 'float' = 0.0, params: 'Optional[dict]' = None) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("pure_pursuit_circle_offset")`)

## 使い方

定常円(半径 R)を pure pursuit(後車軸の中心を基準)で追うときの定常の円の半径 ρ と横ずれ ρ − R(外へ正)。

**運動学 + アンダーステア**(``params`` = None): 指令の舵角 δ = L κ_cmd に対し実際の曲率が κ_cmd / (1 + K v²/L)
になるとすると、同心円の定常で ρ = √(R² + (K v²/L) L_d²)(この版で導いた閉形式)。K = 0 なら ρ = R(横ずれ 0)。

**線形 2 輪等価モデル**(``params`` を与える。δ = atan(L κ_cmd)): 定常では車体の向きが後車軸の速度(円の接線)より
後軸の横すべり角 α_r = m l_f a_y / (C_r L) だけ内を向くので、注視点の見える角が α_r 減る。定常の関係
(δ = L/R_c + K u²/R_c、β、回転の中心)を重心の旋回半径 R_c の 1 変数の方程式にして二分法で解く(半閉形式)。
運動学の式はこの効果を落とすので横ずれを小さく見積もる(PoC では約半分)。

**Raises** ``ValueError``: R, L_d, L ≤ 0、注視点が円に届かない、1 + K v²/L ≤ 0、params で v ≤ 0.5。

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
