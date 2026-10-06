---
op: dose_cv_lognormal
dim: drive
category: doseunif
in: scalar × scalar × scalar × scalar
out: table
examples: [poc_dose_uniformity_from_grinding]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# dose_cv_lognormal — DRIVE `doseunif` op

- **データ種**: `scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dose_cv_lognormal(d_median: 'float', sigma_ln: 'float', dose_mg: 'float', density: 'float', basis: 'str' = 'number', method: 'str' = 'closed', sampling: 'str' = 'poisson', n_rep: 'int' = 2000, seed: 'int' = 0, max_draws: 'int' = 20000000) -> 'dict'` (実装を直接呼ぶなら `import doseunif; doseunif.dose_cv_lognormal(d_median: 'float', sigma_ln: 'float', dose_mg: 'float', density: 'float', basis: 'str' = 'number', method: 'str' = 'closed', sampling: 'str' = 'poisson', n_rep: 'int' = 2000, seed: 'int' = 0, max_draws: 'int' = 20000000) -> 'dict'`、台帳から引くなら `opsdrive.get("dose_cv_lognormal")`)

## 使い方

粒径が対数正規の粉から 1 回分(薬 ``dose_mg``)を取ったときの含量の CV(粒の数の揺らぎだけ)。

閉形式(モジュール冒頭の導出): ``CV² = c · D63³ / D``、c = πρ/6、``D63³ = d_g³ exp(13.5 σ²) = d_v³ exp(4.5 σ²)``。``basis``:
``"number"``(``d_median`` は個数基準の中央径 d_g、画像の粒の数え方)/ ``"volume"``(体積基準の中央径 d_v、レーザー回折の D50)。
``sampling``: ``"poisson"``(既定、粒の数 N が Poisson)/ ``"fixed_count"``(N = λ を丸めた整数に固定、``CV² = CV²_Poisson − 1/N``)。
``method="monte_carlo"``: 1 回分を ``n_rep`` 回作り(N を引き、N 個の径を対数正規から引いて質量を足す)標本の CV を返す —— 閉形式と
**独立な経路**(式を使わない)。標準誤差 ``cv_mc_se`` は 20 個の束の散らばりから。引く径の総数が ``max_draws`` を超えるなら
黙って減らさず ValueError(λ × n_rep を見て n_rep を減らすか閉形式を使う)。

返り: ``cv``(``method`` の値)、``cv_closed``、``particles_per_dose``(λ、fixed_count では整数 N)、``mean_particle_mg``、``d63``、
``d_number_median``・``d_volume_median`` [µm]、``basis``・``sampling``・``method``、Monte Carlo なら ``cv_mc``・``cv_mc_se``・``n_rep``・``draws``。
**Raises** ValueError: 正であるべき量が正でない、綴り違い、fixed_count で N < 2、Monte Carlo の総数が上限を超える。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dose_uniformity_from_grinding](../../../../examples/poc_dose_uniformity_from_grinding.py) — `py -3.11 examples/poc_dose_uniformity_from_grinding.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`doseunif`)

[dose_cv_from_sizes](dose_cv_from_sizes.md) · [grind_time_for_dose_cv](grind_time_for_dose_cv.md)

---
*Provenance: doseunif.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
