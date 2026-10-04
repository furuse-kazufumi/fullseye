---
op: puck_slide_predict
dim: drive
category: puck
in: signal × signal × table × scalar
out: table
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# puck_slide_predict — DRIVE `puck` op

- **データ種**: `signal × signal × table × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.puck_slide_predict(p0, v0, table: 'dict', t_end: 'float', *, model: 'str' = 'coulomb', max_bounces: 'int' = 50, goals: 'bool' = True, t0: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import puck; puck.puck_slide_predict(p0, v0, table: 'dict', t_end: 'float', *, model: 'str' = 'coulomb', max_bounces: 'int' = 50, goals: 'bool' = True, t0: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsdrive.get("puck_slide_predict")`)

## 使い方

パックの経路を閉形式で繋ぐ: 区間(壁から壁)ごとに向き一定・等減速、壁で :func:`puck_wall_bounce`。

時計: p₀・v₀ は時刻 ``t0``(既定 0)の状態、``t_end`` はそこからの長さ。区間の時刻と交点の時刻は **t0 を含む絶対時刻**
(速度推定の ``t_ref`` を t0 に渡せば交点の時刻がカメラの時計で出る)。
``model`` = "coulomb"(a = μg、停止あり)/ "viscous"(a = (c/m) v、Challenge の MJCF の減衰)/ "none"(摩擦なし)。
壁に当たる時刻は d(τ) = 必要距離 の閉形式解(二次方程式か対数)。``goals=True`` なら端の壁の |y| < goal_half は
ゴール(そこで終わる、event "goal")。速さが 0 になれば "stop"、時間切れは "end"。
返り値 ``{"segments": [{"t0","t1","p0","v0","u","s0","event"}, …], "t_end", "p_end", "v_end", "n_bounces", "events"}``。
経路の位置は :func:`puck_state_at`。鏡映法(:func:`puck_mirror_path`、摩擦なし・e = kₜ = 1)と 1e-9 で一致(門)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`puck`)

[puck_table](puck_table.md) · [puck_wall_bounce](puck_wall_bounce.md) · [puck_state_at](puck_state_at.md) · [puck_crossing_point](puck_crossing_point.md) · [puck_mirror_path](puck_mirror_path.md) · [puck_stop_distance](puck_stop_distance.md) · [puck_camera](puck_camera.md) · [puck_pinhole_camera](puck_pinhole_camera.md)

---
*Provenance: puck.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
