---
op: emva_bspline_regression
dim: optics
category: sensorchar
in: signal × signal
out: table
examples: [poc_emva1288_in_camera_processing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# emva_bspline_regression — OPTICS `sensorchar` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.emva_bspline_regression(x, y, n_intervals=8, x_max=None, x_eval=None)` (実装を直接呼ぶなら `import sensorchar; sensorchar.emva_bspline_regression(x, y, n_intervals=8, x_max=None, x_eval=None)`、台帳から引くなら `opsoptics.get("emva_bspline_regression")`)

## 使い方

3 次 B-スプラインの最小二乗の当てはめと、その傾き(General 6.6 節、式 44〜49)。

区間 [0, x_max] を P 等分(Δ = x_max/P)、基底 f_p(x) = β₃(x/Δ − (p − 1))(p = 0..P+2 の P + 3 個、式 44・46)。
係数 a_p は Σ_q (Σ_p a_p f_p(x_q) − y_q)² の最小(式 47、Q > P + 3 点が要る)。傾きは
Σ_p a_p β₃'(x/Δ − (p − 1)) / Δ(式 48 に連鎖律の 1/Δ を足した —— 本文は正規化した変数での傾き)。
General は「露光の段数が推奨どおりなら 6〜8 区間」と書く。

*x_max*: 省略すると max(x)。*x_eval*: 当てはめを評価する追加の点(区間 [0, x_max] の中だけ —— 外挿しない)。
返り値 ``{"coef", "n_intervals", "x_max", "delta", "fit", "slope", "residual_rms", "x_eval", "fit_eval", "slope_eval"}``。

**Raises** ``ValueError``: 1-D でない・長さが違う / NaN・inf / P が 1 以上の整数でない / 点が P + 3 以下 /
x が [0, x_max] の外 / 区間に点が無く係数が決まらない(計画行列の階数が P + 3 未満)/ x_eval が区間の外。

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_emva1288_in_camera_processing](../../../../examples/poc_emva1288_in_camera_processing.py) — `py -3.11 examples/poc_emva1288_in_camera_processing.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`sensorchar`)

[emva_pair_statistics](emva_pair_statistics.md) · [emva_photon_transfer](emva_photon_transfer.md) · [emva_quantum_efficiency](emva_quantum_efficiency.md) · [emva_linearity_error](emva_linearity_error.md) · [emva_snr_curve](emva_snr_curve.md) · [emva_sensitivity_threshold](emva_sensitivity_threshold.md) · [emva_dynamic_range](emva_dynamic_range.md) · [emva_dark_current](emva_dark_current.md)

---
*Provenance: sensorchar.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
