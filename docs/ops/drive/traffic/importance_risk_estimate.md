---
op: importance_risk_estimate
dim: drive
category: traffic
in: any
out: table
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# importance_risk_estimate — DRIVE `traffic` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.importance_risk_estimate(simulate_fn: 'Callable', base_rate: 'Callable', boosted_rate: 'Callable', n_runs: 'int', seed, *, x_max: 'float', boosted_rate_max: 'float', n_grid: 'int' = 20001) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.importance_risk_estimate(simulate_fn: 'Callable', base_rate: 'Callable', boosted_rate: 'Callable', n_runs: 'int', seed, *, x_max: 'float', boosted_rate_max: 'float', n_grid: 'int' = 20001) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("importance_risk_estimate")`)

## 使い方

出現率を上げた試行(率 λ')で事故を起こしやすくし、尤度比の重みで本来の率 λ の事故確率に戻す。

1 回の試行 = ``poisson_events(boosted_rate)`` で出現位置 x_1..x_N を引き、``simulate_fn(events, rng)`` が事故なら 1
(bool か [0, 1] の値)。重み(ポアソン過程の Radon–Nikodym 微分 dP_λ/dP_λ'):

    w = Π_i λ(x_i)/λ'(x_i) · exp(−(Λ − Λ')),   Λ = ∫λ, Λ' = ∫λ'(台形、n_grid 点)

推定 p̂ = mean(w · Y)、標準誤差 = std(w · Y)/sqrt(n)。``boosted_rate`` を ``base_rate`` と同じにすれば w ≡ 1 で
素朴なモンテカルロになる(門ではこれと、事故確率が閉形式で分かる simulate_fn とで比べる)。
λ > 0 なのに λ' = 0 の所があると推定が偏る(絶対連続でない)ので格子上で検査して ValueError。

戻り値 dict: ``estimate``, ``std_error``, ``per_run_var``(w·Y の標本分散)、``n_runs``, ``Lambda``, ``Lambda_boost``,
``mean_weight``(≈ 1 のはず。重みの健全性)、``ess``(有効標本数 (Σw)²/Σw²)、``hits``(Y > 0 の回数)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
