---
id: lens-tolerancing
title: レンズの製造公差を、MTF と歩留まりで決める
title_en: Budget lens manufacturing tolerances by MTF and yield
category: 組み立てる
ops: [tolerance_table, tolerance_criteria, compensators, tolerance_monte_carlo, tolerance_sensitivity, tolerance_report, tolerance_table_zmx, tolerance_table_from_zmx]
examples: [poc_lens_tolerancing]
version: 0.7.0
inputs: [table]
pipeline: [tolerance_table, tolerance_criteria, tolerance_sensitivity, tolerance_monte_carlo, tolerance_report]
alternatives: [tolerance_analysis, through_focus_mtf, spot_stats]
limits: 面の非点不整は二つの低次非点成分です。測定した面形状マップそのものは扱いません。設計ファイルとの往復は NOTE TOLERANCE_ROW 形式です。逆感度は線形近似です。
calibration: 長さは mm、傾きは degree または arcminute、MTF は cycles/mm、波面 RMS は waves です。歩留まりには Wilson 95 % 区間を付けます。
---

# レンズの製造公差を、MTF と歩留まりで決める

## できること

`lenstol` は、曲率・厚み・屈折率・アッベ数・偏心・傾き・面の非点不整・くさび・レンズ群の偏心と傾きを、面または群ごとの行にします。一様分布、正規分布、±公差で切った正規分布を選べます。

## What it does

It turns per-surface and group manufacturing errors into sensitivity, compensated Monte Carlo, yield, histograms, and assembly travel.

## 向くところ / 向かないところ

量産前の公差配分と組立補償の見積もりに向きます。測定した全面形状マップの解析には向きません。

## 推奨パイプライン

使う op: `tolerance_table`, `tolerance_criteria`, `compensators`, `tolerance_monte_carlo`, `tolerance_sensitivity`, `tolerance_report`, `tolerance_table_zmx`, `tolerance_table_from_zmx`

推奨パイプライン: `tolerance_table` → `tolerance_criteria` → `tolerance_sensitivity` → `tolerance_monte_carlo` → `tolerance_report`

## 代替

単純な一様分布と EFL・RMS spot だけなら `tolerance_analysis` を使えます。

## 限界

限界: 面の非点不整は二つの低次非点成分です。測定した面形状マップそのものは扱いません。設計ファイルとの往復は、公開資料で native TOL 行の意味を十分に確認できなかったため、未知行として保持できる `NOTE TOLERANCE_ROW` 形式です。逆感度は線形近似と明記して返します。

## 実寸校正

実寸校正: 長さは mm、傾きは degree または arcminute、MTF は cycles/mm、波面 RMS は waves です。Monte Carlo の歩留まりには Wilson 95 % 区間を付けます。

## 最初の 1 本

```python
import lenstol
import raytrace

system = raytrace.example_system("singlet")
table = lenstol.tolerance_table(system, defaults={"radius_pct": 0.1})
criteria = lenstol.tolerance_criteria(rms_spot={"max": 0.1})
result = lenstol.tolerance_monte_carlo(system, table, criteria, trials=100, seed=7)
print(lenstol.tolerance_report(result))
```

動く例: `poc_lens_tolerancing`

## RAG recipes

```yaml
name: lens-file tolerance to worst-trial MTF
inputs: [lens-file]
pipeline: [lens_file_read, lens_file_system, tolerance_table, tolerance_monte_carlo, through_focus_mtf]
alternatives: [tolerance_sensitivity, render_scene_through_lens]
limits: the worst trial is the worst among the requested finite samples, not a global bound
sample: examples/lensfile_tolerance_worst_mtf.py
```

```yaml
name: optimised prescription to tolerance sensitivity
inputs: [table]
pipeline: [optimize_lens_operands, tolerance_table, tolerance_sensitivity]
alternatives: [merit_evaluate, tolerance_monte_carlo]
limits: central-difference sensitivity is local; use Monte Carlo outside the linear regime
sample: examples/optimized_lens_tolerance_sensitivity.py
```
