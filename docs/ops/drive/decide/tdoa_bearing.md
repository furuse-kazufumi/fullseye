---
op: tdoa_bearing
dim: drive
category: decide
in: signal × signal
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# tdoa_bearing — DRIVE `decide` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tdoa_bearing(sig_left, sig_right, fs, mic_spacing, *, c: 'float' = 343.0, upsample: 'int' = 16) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.tdoa_bearing(sig_left, sig_right, fs, mic_spacing, *, c: 'float' = 343.0, upsample: 'int' = 16) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("tdoa_bearing")`)

## 使い方

2 本のマイク(左 = +y、右 = −y、間隔 ``mic_spacing``)の到着時間差から音源の方位(遠方近似)。

    Δt = t_右 − t_左(左に先に着けば正)、 sin θ = c Δt / d、θ = 前方からの角(左が正)

Δt は相互相関 Σ right[n] left[n − k] の最大(周波数領域で 0 を詰めて ``upsample`` 倍に補間し、さらに放物線)。
探す範囲は物理的にありうる |Δt| ≤ d/c に限る。前後(θ と π − θ)は区別できない。

返り値: ``delay``(秒)、``bearing_rad`` / ``bearing_deg``、``sin_theta``(クリップ前)、``ambiguous``
(主な周波数 f_peak で d > c/(2 f_peak) なら True = 相関の山が 1/f ごとに並び範囲内に 2 つ入りうる)、``f_peak``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`decide`)

[mirror_reflection_matrix](mirror_reflection_matrix.md) · [mirror_virtual_camera](mirror_virtual_camera.md) · [mirror_aim_normal](mirror_aim_normal.md) · [convex_mirror_fov](convex_mirror_fov.md) · [mirror_blind_zone](mirror_blind_zone.md) · [check_sequence_score](check_sequence_score.md) · [signal_phase_plan](signal_phase_plan.md) · [signal_state](signal_state.md)

---
*Provenance: drivedecide.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
