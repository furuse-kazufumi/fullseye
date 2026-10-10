---
op: kendama_params
dim: drive
category: kendama
in: 
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# kendama_params — DRIVE `kendama` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.kendama_params(preset: 'str' = 'jka_16_2', *, trick: 'str' = 'ozara', ball_radius: 'float' = None, mass: 'float' = 0.075, string: 'float' = 0.39, cup_radius_big: 'float' = None, cup_depth: 'float' = None, ken_length: 'float' = None, width: 'float' = None, rho: 'float' = 1.2, cd=0.4, cup_offset=None, tie_offset=None, cup_axis=None, g: 'float' = 9.81) -> 'dict'` (実装を直接呼ぶなら `import kendama; kendama.kendama_params(preset: 'str' = 'jka_16_2', *, trick: 'str' = 'ozara', ball_radius: 'float' = None, mass: 'float' = 0.075, string: 'float' = 0.39, cup_radius_big: 'float' = None, cup_depth: 'float' = None, ken_length: 'float' = None, width: 'float' = None, rho: 'float' = 1.2, cd=0.4, cup_offset=None, tie_offset=None, cup_axis=None, g: 'float' = 9.81) -> 'dict'`、台帳から引くなら `opsdrive.get("kendama_params")`)

## 使い方

けん玉の表。既定 = ``preset="jka_16_2"``(玉 60 mm、横幅 70 mm、全長 180 mm は日本けん玉協会の公表値、けんの高さ 160 mm と
皿 42 / 38 / 35 mm はユーザー提供の JKA 16-2 型の説明(一次資料は未確認))。``"recommended_large_cup"`` = 大皿 49 mm・穴 24 mm。

鍵: ``ball_radius`` 0.030、``string`` 0.39(糸 = 推奨 38〜40 cm)、``pendulum_length`` = 糸 + 玉の半径(結び目 → 玉の中心、
玉の糸穴は大きな穴の反対側と置く)、``cup_radius_big`` / ``cup_radius_base`` / ``cup_radius_small``(縁の半径)、``cup_depth``
(大皿の深さ。既定 = 縁に乗った玉の下端の沈み r_b − √(r_b² − r_c²) + 1.5 mm = 玉が底に触れない深さ、と置く仮定)、``ken_length``(けんの高さ = けん先 → 中皿の縁、160 mm)、``width``(大皿の縁 〜 小皿の縁、70 mm)、
``hole_radius`` / ``hole_depth``(玉の大きな穴。深さ = けん + 玉 − 全長 = 40 mm)、``total_length``(組み立ての全長 = けん + 玉 − 穴の深さ)、
``cross_radius`` / ``ken_radius`` / ``spike_length`` / ``cross_from_tip``(仮定)、``mass``(玉、仮定 75 g)・``ken_mass``(仮定 70 g)。
技 ``trick``(:data:`KENDAMA_TRICKS`: "ozara" 大皿 / "kozara" 小皿 / "chuzara" 中皿 / "ろうそく" = "rousoku")が姿勢を決める:
``R_ken``(けんの局所座標 → 世界: 局所はけん先 +x・大皿 +z・原点 = 皿胴の中心)、``grip``(持つ所、局所)、受ける皿
``catch_cup``("big" / "small" / "base")。そこから手元(= 持つ所)に対する ``cup_offset``(受ける皿の縁の中心)、``cup_axis``
(受ける皿の軸、世界)、``tie_offset``(皿胴の糸穴: 局所 (0, −cross_radius, 0))、``top_offset``(けん玉のいちばん高い所)、
``cup_radius``(受ける皿の縁の半径)を出す。けんと皿胴は 1 つの剛体(姿勢は技ごとに固定、手元は並進)。
``cup_offset`` / ``tie_offset`` / ``cup_axis`` を渡すとその値で上書き(0 を渡すと点のけん = 支点 = 皿 = 手元: 定理の門)。
``catch_window`` = 0.003 m: :func:`kendama_simulate` は玉の中心が「縁に乗る高さ h_c から 3 mm 以内」に下りてきた瞬間を捕球とする
(玉が縁に触れた = 着地。縁から 1.5 r_b 上の窓に入っただけでは捕らない: 頂点が窓の中だと頂点で「捕れて」しまう —— 測って退けた)。
``rho``/``cd`` = 空気密度・抗力係数(rho = 0 で真空: 定理の門はこれで走らせる)。

fail-closed: 未知の preset、寸法 ≤ 0、皿の縁 ≥ 玉(縁で受けられない = けん玉ではない)、横幅 < 大皿の直径、糸 ≤ 玉の半径、
穴の深さが (0, 玉の直径) の外、けん先の太さが穴に入らない、は ValueError。
返り値には派生量 ``"cup_rest_height"`` = √(r_b² − r_c²)(受ける皿の縁に乗った玉の中心の高さ)、``"bp"``(:func:`ballistics.ball_params`、中実球)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendama`)

[elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md) · [swing_up_apex](swing_up_apex.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
