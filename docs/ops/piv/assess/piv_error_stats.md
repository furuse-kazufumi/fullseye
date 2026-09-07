---
op: piv_error_stats
dim: piv
category: assess
in: flow2d × flow2d
out: table
examples: [piv_field_analysis_tour, piv_flow_from_particles, poc_river_surface_velocity, poc_strain_history]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_error_stats — PIV `assess` op

- **データ種**: `flow2d × flow2d` → `table`
- **呼び出し**: `import pivops; pivops.piv_error_stats(flow, truth, trim=1)` (または `opspiv.get("piv_error_stats")`)

## 使い方

真値との差の内訳。**偏りと散らばりを分けて**返す。

どちらか一方だけを出すと、系統的にずれている実装が「誤差 0.3 px」として
通ってしまう。偏り(平均誤差)と散らばり(標準偏差)は別の原因を指す。

Args:
    flow: 推定 ``(2, h, w)``。
    truth: 同じ格子の真値 ``(2, h, w)``(:func:`piv_sample_at_windows` の返り)。
    trim: 外周から除く格子数。窓が画像の縁にかかると相関が落ちるので、
        既定で 1 列ぶん落とす。0 で全格子。
Returns:
    dict: ``bias_dy`` / ``bias_dx`` / ``std_dy`` / ``std_dx`` / ``rms``
    (2 成分合わせた二乗平均平方根) / ``median_abs`` / ``p95_abs`` /
    ``n_valid`` / ``n_total``。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`
- [piv_flow_from_particles](../../../../examples/piv_flow_from_particles.py) — `py -3.11 examples/piv_flow_from_particles.py`
- [poc_river_surface_velocity](../../../../examples/poc_river_surface_velocity.py) — `py -3.11 examples/poc_river_surface_velocity.py`
- [poc_strain_history](../../../../examples/poc_strain_history.py) — `py -3.11 examples/poc_strain_history.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`assess`)

[piv_sample_at_windows](piv_sample_at_windows.md) · [piv_peak_locking](piv_peak_locking.md) · [piv_time_statistics](piv_time_statistics.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
