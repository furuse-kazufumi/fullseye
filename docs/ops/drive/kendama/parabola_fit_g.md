---
op: parabola_fit_g
dim: drive
category: kendama
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# parabola_fit_g — DRIVE `kendama` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.parabola_fit_g(t, P, *, g: 'float' = 9.81, t_ref: 'float' = None) -> 'dict'` (実装を直接呼ぶなら `import kendama; kendama.parabola_fit_g(t, P, *, g: 'float' = 9.81, t_ref: 'float' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("parabola_fit_g")`)

## 使い方

重力 g(−z)を既知とした放物線 p(t) = p_r + v_r (t − t_ref) − ½ g (t − t_ref)² ẑ を最小二乗で当てる(未知 6 = 位置と速度)。

``t`` (N,)、``P`` (N, 3)(NaN の行は飛ばす)。``t_ref`` 既定 = 使った最後の時刻(= その瞬間の状態を返す)。各軸は
[1, t − t_ref] の線形最小二乗(z は ½ g (t − t_ref)² を足してから)。返り値 ``{"p", "v", "t_ref", "rms" (残差の RMS [m]),
"n"}``。有効な点が 2 未満・時刻が全部同じ・g ≤ 0 は ValueError。真空の正確な標本なら (p, v) を丸め誤差で戻す(門)。

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
