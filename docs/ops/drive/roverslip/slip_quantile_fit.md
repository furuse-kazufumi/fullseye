---
op: slip_quantile_fit
dim: drive
category: roverslip
in: signal × signal
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# slip_quantile_fit — DRIVE `roverslip` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.slip_quantile_fit(slopes, slips, quantiles=None, n_knots: 'int' = 6, smooth: 'float' = 0.001, iters: 'int' = 200, calibrate: 'float' = 0.25, level: 'float' = 0.9, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.slip_quantile_fit(slopes, slips, quantiles=None, n_knots: 'int' = 6, smooth: 'float' = 0.001, iters: 'int' = 200, calibrate: 'float' = 0.25, level: 'float' = 0.9, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("slip_quantile_fit")`)

## 使い方

斜面の角 → 滑り率の分位点回帰(区分線形の基底、ピンボール損失を IRLS で、2 階差分の弱い罰則)。

``quantiles`` の既定は 0.05, 0.10, …, 0.95 の 19 段。節点は角の分位点に ``n_knots`` 個(データの疎な端に
節点を置きすぎない)。当てはめの後、角ごとに分位点の曲線を並べ替えて交差を消す(rearrangement)。
雑音が角で変わってもその角の帯の幅が追従する —— ガウス過程の一様な雑音との違い。
``calibrate`` > 0 なら、データのその割合を較正用に取り分けて(``seed`` で決まる無作為の分割)残りで当てはめ、
両側 ``level`` の帯の幅を共形予測で補正する(Romano, Patterson & Candès 2019 の CQR: 較正点ごとに
``E = max(下端 − y, y − 上端)`` を取り、その ``⌈(n + 1) level⌉ / n`` 分位点だけ帯を両側に広げる / 狭める)。
交換可能なデータなら帯の被覆は有限標本で ``level`` 以上(角ごとの被覆ではなく全体の被覆の保証)。
IRLS の分位点回帰は標本の中で帯を狭く見積もりがち(試作の測りで名目 90 % に 82〜91 %)なので既定で入れる。
返り値 ``{"kind": "quantile", "quantiles", "knots", "coef": (段, 節点), "conformal": {level: 幅の補正}}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
