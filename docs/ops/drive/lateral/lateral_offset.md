---
op: lateral_offset
dim: drive
category: lateral
in: any
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# lateral_offset — DRIVE `lateral` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lateral_offset(points, path, *, start_index=None, window: 'int' = 40) -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.lateral_offset(points, path, *, start_index=None, window: 'int' = 40) -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("lateral_offset")`)

## 使い方

点の、折線の経路に沿った弧長 s と横ずれ n(進行方向の左が正)。最も近い区間への射影。

``start_index``(点ごと、または 1 つ)を与えると、その区間の前後 ``window`` 区間だけを調べる(繰り返しを速くする。
窓の外に本当の最寄りがあると誤るので、点が少しずつ動くときに使う)。None なら全区間を調べる。
返り値: ``s``, ``n``, ``index``(区間)、``heading``(その区間の向き)。点 (2,) なら スカラー。

**Raises** ``ValueError``: 形の誤り、start_index が範囲外。

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
