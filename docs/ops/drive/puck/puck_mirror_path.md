---
op: puck_mirror_path
dim: drive
category: puck
in: signal × signal × table × scalar
out: signal
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# puck_mirror_path — DRIVE `puck` op

- **データ種**: `signal × signal × table × scalar` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.puck_mirror_path(p0, v0, table: 'dict', t_end: 'float') -> 'np.ndarray'` (実装を直接呼ぶなら `import puck; puck.puck_mirror_path(p0, v0, table: 'dict', t_end: 'float') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("puck_mirror_path")`)

## 使い方

鏡映法(摩擦なし・e = kₜ = 1 専用): 直線 p₀ + v₀ t を壁の格子で折り返した位置を返す(第 2 実装、門の相手)。
ゴールは無視(壁として扱う)。返り値 = 終端位置 (2,)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`puck`)

[puck_table](puck_table.md) · [puck_wall_bounce](puck_wall_bounce.md) · [puck_slide_predict](puck_slide_predict.md) · [puck_state_at](puck_state_at.md) · [puck_crossing_point](puck_crossing_point.md) · [puck_stop_distance](puck_stop_distance.md) · [puck_camera](puck_camera.md) · [puck_pinhole_camera](puck_pinhole_camera.md)

---
*Provenance: puck.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
