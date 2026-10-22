---
op: emva_general_sensitivity
dim: optics
category: sensorgeneral
in: signal × signal × signal
out: table
examples: [poc_emva1288_in_camera_processing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# emva_general_sensitivity — OPTICS `sensorgeneral` op

- **データ種**: `signal × signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.emva_general_sensitivity(mu_p, mu_y, var_y, mu_y_dark, var_y_dark, mu_p_sat, n_intervals=8)` (実装を直接呼ぶなら `import sensorgeneral; sensorgeneral.emva_general_sensitivity(mu_p, mu_y, var_y, mu_y_dark, var_y_dark, mu_p_sat, n_intervals=8)`、台帳から引くなら `opsoptics.get("emva_general_sensitivity")`)

## 使い方

特性曲線・入力 SNR・絶対感度しきい値・DR・光子単位の暗雑音(General 2.1〜2.4・6.6〜6.8 節)。

*mu_p*: 露光段ごとの画素あたりの平均光子数。*mu_y*, *var_y*: 同じ露光の 2 枚から出した平均と時間分散(式 16・18、
:func:`sensorchar.emva_pair_statistics`)。*mu_y_dark*, *var_y_dark*: 暗画像の同じ量。*mu_p_sat*: 飽和の露光
(0.1〜0.2 % の画素が最大値になる露光、6.7 節)。0 ≤ μ_p ≤ μ_p.sat の点だけを使う。

手順:
1. 特性曲線 μ_y − μ_y.dark = R(μ_p) を [0, μ_p.sat] を P 等分した 3 次 B-スプラインで当て、各点の傾き ∂μ_y/∂μ_p
   と暗い所の傾き R_d = ∂μ_y/∂μ_p|μ_p=0(式 25)を出す(6.6 節)。
2. 出力 SNR_y = (μ_y − μ_y.dark)/σ_y(式 7)、入力 SNR_p = μ_p |∂μ_y/∂μ_p| / σ_y(式 10)、理想 √μ_p(式 15)。
3. 逆の関係 μ_p(SNR_p) を同じ区間数の B-スプラインで当て、SNR_p = 1 の露光を μ_p.min とする(6.8 節)。測った
   SNR_p が 1 以下の点を含まなければ拒む(外挿になる。付録 D.1 は SNR ≈ 1 の露光を含めよと書く)。
3'. 照合用(**規格の手順ではない**): SNR_p が 1 をまたぐ隣の 2 点の間を log-log の直線で補間した ``mu_p_min_local``。
   規格の逆回帰は [0, SNR_max] 全体を P 等分した区間の 3 次で当てるので、SNR ≈ 1 の近くの点の雑音を拾いやすい
   (2 万画素の合成センサで乱数 6 通り: 逆回帰 ±5 %、局所の補間 ±1 %)。
4. SNR_max = 測った SNR_p の最大(6.8 節。線形でないと飽和の露光で最大とは限らない)、DR = μ_p.sat/μ_p.min(式 21)。
5. 暗雑音 [光子] σ_d = √(σ²_y.dark − σ²_q)/R_d(General の式 50)。σ²_y.dark < 0.24 DN² なら推定せず上限 0.40/R_d
   (式 51)。

返り値 ``{"slope", "Rd", "snr_y", "snr_p", "snr_p_ideal", "mu_p_min", "mu_p_min_local", "snr_max", "mu_p_at_snr_max", "DR", "DR_dB",
"sigma_d_p", "sigma_d_p_upper", "sigma_d_valid", "used", "fit", "n_intervals"}``。
★η・K・電子の単位の量は**返さない**(General では測れない、6.7 節)。

**Raises** ``ValueError``: 長さが違う / μ_p.sat が正でない / 区間に点が足りない(B-スプラインの拒否)/ 傾きが 0 の点 /
分散が正でない点 / SNR_p ≤ 1 の点が無い / var_y_dark が負。

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

## 同カテゴリ(`sensorgeneral`)

[emva_general_nonuniformity](emva_general_nonuniformity.md) · [emva_general_relative_qe](emva_general_relative_qe.md)

---
*Provenance: sensorgeneral.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
