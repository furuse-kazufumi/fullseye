---
op: marker_direction
dim: drive
category: balltrack
in: 
out: signal
examples: [poc_ball_bounce, poc_table_tennis_bounce, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# marker_direction — DRIVE `balltrack` op

- **データ種**: `なし` → `signal`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.marker_direction(marker_uv, center_uv, radius_px, K=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import balltrack; balltrack.marker_direction(marker_uv, center_uv, radius_px, K=None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("marker_direction")`)

## 使い方

像の中の模様の位置 (col, row) → 球面上の向き(カメラ系の単位ベクトル、前半球: x 右、y 上、z 手前)。

``K`` (3, 3) を渡すと**透視で厳密に**解く: 球の角半径 α = atan(半径 px / f) から中心までの距離(半径 1 として 1/sin α)と
中心の視線を出し、模様の画素の視線を球面と交差させ、交点の法線を返す。★K が無い形は円板を正射影とみなし、中心を通る
視線を z とする系で答える —— 球が光軸から外れていると系ごと回り、球が動く映像では視線の変化がそのまま見かけの回転になる
(0.6 m 先を 6 m/s で横切る球は 1 ms で視線が 0.01 rad 回り、1 コマの回転 0.15 rad に 7 % 上乗せされた。2026-09-30、
PoC ㉔ の近接カメラ)。K が無ければ従来どおり。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_bounce](../../../../examples/poc_table_tennis_bounce.py) — `py -3.11 examples/poc_table_tennis_bounce.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`balltrack`)

[ball_detect](ball_detect.md) · [ball_track](ball_track.md) · [kalman_ca](kalman_ca.md) · [triangulate_dlt](triangulate_dlt.md) · [track_triangulate](track_triangulate.md) · [bounce_detect](bounce_detect.md) · [spin_from_markers](spin_from_markers.md) · [spin_from_marker_sequence](spin_from_marker_sequence.md)

---
*Provenance: balltrack.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
