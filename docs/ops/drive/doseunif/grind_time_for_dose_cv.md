---
op: grind_time_for_dose_cv
dim: drive
category: doseunif
in: signal × signal × scalar × scalar
out: table
examples: [poc_dose_uniformity_from_grinding]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# grind_time_for_dose_cv — DRIVE `doseunif` op

- **データ種**: `signal × signal × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.grind_time_for_dose_cv(t, d63, dose_mg: 'float', density: 'float', target_cv: 'float | None' = None, pass_probability: 'float | None' = None, law: 'str' = 'best', k_accept: 'float' = 2.4, limit_av: 'float' = 15.0, n_units: 'int' = 10, ref_range=(98.5, 101.5), n_mc: 'int' = 20000, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import doseunif; doseunif.grind_time_for_dose_cv(t, d63, dose_mg: 'float', density: 'float', target_cv: 'float | None' = None, pass_probability: 'float | None' = None, law: 'str' = 'best', k_accept: 'float' = 2.4, limit_av: 'float' = 15.0, n_units: 'int' = 10, ref_range=(98.5, 101.5), n_mc: 'int' = 20000, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("grind_time_for_dose_cv")`)

## 使い方

モーメント径 D63 の時間変化に粉砕則を当て、含量の CV が目標まで下がるのに要る粉砕時間を逆算する。

``t``: 粉砕時間(エネルギーの代わり、:mod:`grind` の約束)、``d63``: その時点の D63 [µm] (:func:`dose_cv_from_sizes` の ``d63``。
D50 でなく D63 を使うのは、CV が D63 だけで決まり分布の形の仮定が要らないから —— 粉砕則を D63 に当てるのは D50 に当てるのと同じく仮定)。
目標: ``target_cv`` を直接、または ``pass_probability`` = 10 個の第 1 段に合格する確率(χ² の閉形式、平均のずれを無視した上限)から
``CV = (L1/k) √((n−1)/χ²_p(n−1)) / 100``。どちらも無ければ ``L1/k/100``(= 0.0625、「AV ≤ 15 相当」の目安、合格はおよそ半分)。
必要な D63 は ``(CV² D / c)^{1/3}``(Poisson、c = πρ/6)。3 則(kick / bond / rittinger)全部で時間を出し、``law="best"`` は
log の rms が最小の則、名前を渡せばその則。則による違いは ``t_req_by_law`` と ``t_req_spread`` に(模型の不確かさとして読む)。
返り: ``t_req``、``law``、``d63_req``、``target_cv``、``t_req_by_law``、``t_req_spread``(min, max)、``extrapolated``(t_req が測った範囲を超える)・
``extrap_ratio``、``already_met``(最初の点で既に目標以下)、``cv_observed``(各点の CV)、``pass_probability_chi2``(目標の CV での
上限)・``pass_probability_mc``(平均のずれの項も入れた Monte Carlo、正規近似)、``fits``(:func:`grind.comminution_law_fit` の要約)。
**Raises** ValueError: 点が 3 未満・非正・長さ違い、target と pass_probability の両方、範囲外の確率・CV、綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dose_uniformity_from_grinding](../../../../examples/poc_dose_uniformity_from_grinding.py) — `py -3.11 examples/poc_dose_uniformity_from_grinding.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`doseunif`)

[dose_cv_lognormal](dose_cv_lognormal.md) · [dose_cv_from_sizes](dose_cv_from_sizes.md)

---
*Provenance: doseunif.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
