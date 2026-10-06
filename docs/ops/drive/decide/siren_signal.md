---
op: siren_signal
dim: drive
category: decide
in: 
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# siren_signal — DRIVE `decide` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.siren_signal(duration: 'float', fs: 'float', *, f_high: 'float' = 960.0, f_low: 'float' = 770.0, period: 'float' = 1.3, source_start=(-60.0, 10.0), source_velocity=(15.0, 0.0), mics=((0.0, 0.0),), c: 'float' = 343.0, spreading: 'bool' = True, mic_velocity=(0.0, 0.0), mic_track=None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.siren_signal(duration: 'float', fs: 'float', *, f_high: 'float' = 960.0, f_low: 'float' = 770.0, period: 'float' = 1.3, source_start=(-60.0, 10.0), source_velocity=(15.0, 0.0), mics=((0.0, 0.0),), c: 'float' = 343.0, spreading: 'bool' = True, mic_velocity=(0.0, 0.0), mic_track=None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("siren_signal")`)

## 使い方

動く救急車のサイレン(二音の交互)を、止まっているマイクで聞いた音を合成する。

音源 p(τ) = ``source_start`` + ``source_velocity``·τ(2D、等速直線)、発する音は sin φ(τ)、φ は高い音 f_high と
低い音 f_low を ``period``/2 ずつ交互に鳴らす連続位相。マイク m が時刻 t に聞く音は、発音時刻 τ が

    c (t − τ) = |p(τ) − m|   ⇔   (c² − |u|²) s² + 2 (q·u) s − |q|² = 0,  s = t − τ ≥ 0,  q = p(t) − m

を満たすときの sin φ(τ)(振幅は ``spreading`` なら r_ref / r、r_ref = 最初の距離)。**ドップラーの式は使っていない**
(到着時刻の幾何だけ)ので、``doppler_track`` の門の独立な経路になる。

``mic_velocity`` = マイク(を載せた自車)の等速度(空気 = 地面に対して。風なし)。マイクは m(t) = m₀ + u_L t と動く。
上の式は q = p(t) − m(t) と置けば同じ形のまま成り立つ(c(t − τ) = |p(τ) − m(t)|、p(τ) = p(t) − u s)。
2 次方程式に入るのは **受信時のマイクの位置だけ**(音源は等速)なので、マイクは任意の道を動いてよい:
``mic_track`` = (位置 (k, n, 2), 速度 (k, n, 2))を標本ごとに与えると ``mics`` / ``mic_velocity`` の代わりに使う
(減速して左に寄る自車に載せたマイク。速度は dτ/dt の閉形式にだけ使う)。

返り値: ``t``(n,)、``signals``(マイク数, n)、``tau``(同)、``f_emit``(同、発した周波数)、``v_radial``(同、
**近づく向きの距離の変化率** −d|p(τ) − m(t)|/dt を「音源の視線速度に換算した値」c(1 − 1/D)、D = dτ/dt。マイクが
止まっていれば発音時の −ṙ と同じ)、``range_rate``(同、受信時の幾何の距離 |p(τ) − m(t)| の時間微分。負 = 近づく)、
``f_true``(同、= f_emit · dτ/dt。閉形式 dτ/dt = (c + r̂·u_L)/(c + r̂·u_S)、r̂ = (p(τ) − m(t))/r の単位ベクトル)。

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
