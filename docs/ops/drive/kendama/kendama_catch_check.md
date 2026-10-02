---
op: kendama_catch_check
dim: drive
category: kendama
in: table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# kendama_catch_check — DRIVE `kendama` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.kendama_catch_check(kp: 'dict', p_ball, v_ball, cup_center, cup_axis=(0.0, 0.0, 1.0), v_cup=(0.0, 0.0, 0.0), v_rel_max: 'float' = 1.0, window: 'float' = None) -> 'dict'` (実装を直接呼ぶなら `import kendama; kendama.kendama_catch_check(kp: 'dict', p_ball, v_ball, cup_center, cup_axis=(0.0, 0.0, 1.0), v_cup=(0.0, 0.0, 0.0), v_rel_max: 'float' = 1.0, window: 'float' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("kendama_catch_check")`)

## 使い方

玉(半径 r_b)が皿(縁の半径 r_c < r_b、縁の中心 cup_center、軸 cup_axis、速度 v_cup)に乗る幾何の判定。

縁に乗った玉の中心は縁の面から h_c = √(r_b² − r_c²) 上、静的な安定条件は横ずれ ≤ r_c。:func:`ballistics.cup_catch_check`
(皿 > 玉が前提)を有効な皿(半径 r_c + r_b、中心を軸方向に h_c 上げる)で呼ぶ → 横ずれ ≤ r_c、縁の面からの高さ
h_c ≤ h ≤ h_c + 1.5 r_b、皿に対する相対速さ ≤ v_rel_max。さらに **下から昇ってくる玉(相対速度の軸成分 > 0)は受けない**
(皿は上からしか受けられない。支点 = 皿の中心の簡略化では昇る玉が皿の位置を通り抜けるため必要)。
``window`` を渡すと高さの窓を「縁に最初に触れる高さ」+ window 以下に狭める(着地の判定: :func:`kendama_simulate` は
kp["catch_window"])。横ずれ δ の玉は √(r_b² − (r_c − δ)²)(δ = 0 で h_c)で縁に触れる —— 中心からずれた玉は縁の片側に
先に触れ、皿の中へ転がり込む(横ずれ ≤ r_c なら受けたとする)。
縁の半径は kp["cup_radius"] (受ける皿、無ければ大皿)。返り値 ``{"caught", "lateral", "height" (縁の面から), "speed" (相対), "descending"}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
