---
op: clothoid_design
dim: drive
category: lateral
in: 
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# clothoid_design — DRIVE `lateral` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.clothoid_design(radius: 'float', length: 'float', speed: 'Optional[float]' = None) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.clothoid_design(radius: 'float', length: 'float', speed: 'Optional[float]' = None) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("clothoid_design")`)

## 使い方

直線 → 円(半径 R)を長さ L のクロソイドで繋ぐときの量。

返り値: ``A`` = √(R L)、``end_angle`` τ = L/(2R)、``end_point``(終点の (x, y)、フレネル積分)、``shift``
ΔR = y_end − R(1 − cos τ)(円が直線から離れる量。近似 L²/(24R))、``lateral_jerk``(速さ v を与えたとき
v³/(R L) [m/s³] = Shortt 式の P)、``min_length_3s``(v を与えたとき 3 秒の走行長 3v [m])。

**Raises** ``ValueError``: R ≤ 0、L ≤ 0、v ≤ 0。

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
