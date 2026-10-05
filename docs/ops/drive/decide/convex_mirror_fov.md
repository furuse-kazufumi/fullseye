---
op: convex_mirror_fov
dim: drive
category: decide
in: 
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# convex_mirror_fov — DRIVE `decide` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.convex_mirror_fov(radius, aperture, eye_distance) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.convex_mirror_fov(radius, aperture, eye_distance) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("convex_mirror_fov")`)

## 使い方

凸面鏡(球面、半径 ``radius``、開口の直径 ``aperture``)を軸上 ``eye_distance``(頂点から)の眼で見たときの視野角。

厳密(軸を含む断面): h = a/2、α = asin(h/R)、s = R − sqrt(R² − h²)、β = atan(h/(D + s))、
**全視野角 = 2(β + 2α)**。``radius = inf`` は平面鏡 2 atan(h/D)。
近軸: ≈ a (1/D + 2/R)(誤差は h³ の桁。h/R ≲ 0.2 かつ h/D ≲ 0.2 で相対誤差が数 % 以内が目安)。

返り値: ``fov_rad`` / ``fov_deg``(厳密)、``fov_paraxial_rad``、``flat_fov_rad``(同じ開口の平面鏡)、
``widening``(= fov / flat_fov、凸面で何倍広く見えるか)、``edge_tilt_rad`` = α、``eye_angle_rad`` = β。
h ≥ R(半球より大きい開口)は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`decide`)

[mirror_reflection_matrix](mirror_reflection_matrix.md) · [mirror_virtual_camera](mirror_virtual_camera.md) · [mirror_aim_normal](mirror_aim_normal.md) · [mirror_blind_zone](mirror_blind_zone.md) · [check_sequence_score](check_sequence_score.md) · [signal_phase_plan](signal_phase_plan.md) · [signal_state](signal_state.md) · [predict_amber_onset](predict_amber_onset.md)

---
*Provenance: drivedecide.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
