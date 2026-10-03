---
op: erf
dim: math
category: numerics
in: signal
out: signal
examples: [numerics_tour, poc_battery_electrode_breathing, poc_change_detection_misreg, poc_crack_width_timeseries, poc_dic_strain, poc_die_tilt_tsv_overlay, poc_dimensional_inspection, poc_exoplanet_transit, poc_fresco_craquelure, poc_mri_bias_field, poc_search_sweep_width, poc_settlement_significance, poc_star_astrometry, representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# erf — MATH `numerics` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.erf(x) -> 'np.ndarray'` (実装を直接呼ぶなら `import mathnumerics; mathnumerics.erf(x) -> 'np.ndarray'`、台帳から引くなら `opsmath.get("erf")`)

## 使い方

誤差関数 erf(x) = (2/√π) ∫_0^x e^{−t²} dt。

正規分布の累積や、ぼけたエッジ(ガウスで畳んだ段差)の形そのもの: 幅 σ のガウスでぼけた段差は
½(1 + erf(x / (σ√2)))。門: 奇関数、erf(∞) = 1、導関数 = (2/√π) e^{−x²}、Gauss 求積による積分と一致。

## ファミリ共通の入力契約(fail-closed)

mathops の全 op は入力を検証してから計算する(黙って通さない):

- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。
- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。
- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。
- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。
- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は `mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。

## 詳しい使い方ガイド

- [math_metrology ファミリ ガイド](../guides/math_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [numerics_tour](../../../../examples/numerics_tour.py) — `py -3.11 examples/numerics_tour.py`
- [poc_battery_electrode_breathing](../../../../examples/poc_battery_electrode_breathing.py) — `py -3.11 examples/poc_battery_electrode_breathing.py`
- [poc_change_detection_misreg](../../../../examples/poc_change_detection_misreg.py) — `py -3.11 examples/poc_change_detection_misreg.py`
- [poc_crack_width_timeseries](../../../../examples/poc_crack_width_timeseries.py) — `py -3.11 examples/poc_crack_width_timeseries.py`
- [poc_dic_strain](../../../../examples/poc_dic_strain.py) — `py -3.11 examples/poc_dic_strain.py`
- [poc_die_tilt_tsv_overlay](../../../../examples/poc_die_tilt_tsv_overlay.py) — `py -3.11 examples/poc_die_tilt_tsv_overlay.py`
- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`
- [poc_exoplanet_transit](../../../../examples/poc_exoplanet_transit.py) — `py -3.11 examples/poc_exoplanet_transit.py`
- [poc_fresco_craquelure](../../../../examples/poc_fresco_craquelure.py) — `py -3.11 examples/poc_fresco_craquelure.py`
- [poc_mri_bias_field](../../../../examples/poc_mri_bias_field.py) — `py -3.11 examples/poc_mri_bias_field.py`
- [poc_search_sweep_width](../../../../examples/poc_search_sweep_width.py) — `py -3.11 examples/poc_search_sweep_width.py`
- [poc_settlement_significance](../../../../examples/poc_settlement_significance.py) — `py -3.11 examples/poc_settlement_significance.py`
- [poc_star_astrometry](../../../../examples/poc_star_astrometry.py) — `py -3.11 examples/poc_star_astrometry.py`
- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](../stats/stat_describe.md) · [stat_histogram](../stats/stat_histogram.md) · [stat_zscore](../stats/stat_zscore.md) · [interp_linear](../interp_poly/interp_linear.md) · [interp_cubic](../interp_poly/interp_cubic.md) · [interp_scattered](../interp_poly/interp_scattered.md)

## 同カテゴリ(`numerics`)

[erfc](erfc.md) · [bessel](bessel.md) · [gauss_quadrature](gauss_quadrature.md) · [gauss_cubature](gauss_cubature.md) · [chebyshev_coeffs_nd](chebyshev_coeffs_nd.md) · [chebyshev_eval_nd](chebyshev_eval_nd.md) · [low_discrepancy](low_discrepancy.md) · [chebyshev_nodes](chebyshev_nodes.md)

---
*Provenance: mathnumerics.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
