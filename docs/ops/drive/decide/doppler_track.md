---
op: doppler_track
dim: drive
category: decide
in: signal
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# doppler_track — DRIVE `decide` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.doppler_track(signal, fs, *, f_high: 'float' = 960.0, f_low: 'float' = 770.0, c: 'float' = 343.0, smooth: 'float' = 0.005, guard: 'float' = 0.01, edge: 'float' = 0.05, v_tol: 'float' = 1.0, verdict_window: 'float' = 0.5) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.doppler_track(signal, fs, *, f_high: 'float' = 960.0, f_low: 'float' = 770.0, c: 'float' = 343.0, smooth: 'float' = 0.005, guard: 'float' = 0.01, edge: 'float' = 0.05, v_tol: 'float' = 1.0, verdict_window: 'float' = 0.5) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("doppler_track")`)

## 使い方

サイレンの音から瞬時周波数を推定し、近づいている / 遠ざかっているを判定する。

1. 解析信号(FFT の Hilbert 変換)の位相差 → 瞬時周波数 f(t) = arg(z[n+1] z̄[n]) fs / 2π。
2. 幅 ``smooth`` 秒の移動中央値。
3. 各時刻で公称の 2 音(``f_high`` / ``f_low``)のうち比が近い方を「発した音」とみなし、ドップラー係数
   D = f / f_nom、視線速度 v_r = c (1 − 1/D)(``doppler_shift`` を v_r について解いたもの)。
4. 音が切り替わる所(中央値の跳び > 20 Hz)の前後 ``guard`` 秒と、両端 ``edge`` 秒は無効(``valid`` = False)。
5. 判定: 最後の ``verdict_window`` 秒の有効な v_r の中央値が +v_tol より大 → ``"approaching"``、−v_tol より小 →
   ``"receding"``、間 → ``"abeam"``。``state`` は各時刻の同じ判定(無効な所は ``"unknown"``)。

公称音の取り違えの限界: 振り分けの境目は幾何平均 √(f_h f_l)。低い音が近づいて境目を越えるのは
v_r = c (1 − √(f_l/f_h))、高い音が遠ざかって越えるのは v_r = −c (√(f_h/f_l) − 1)。960/770 Hz では
+35.8 m/s(129 km/h)と −40.0 m/s。これより速い視線速度は取り違える(テストで固定)。

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
