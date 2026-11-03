---
op: hdr_dynamic_range
dim: optics
category: hdr
in: 
out: table
gpu: なし
examples: [poc_hdr_glossy_metal_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# hdr_dynamic_range — OPTICS `hdr` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.hdr_dynamic_range(exposures, eta=0.6, K=0.1, sigma_d_e=8.0, dark_offset_dn=4.0, bits=8, full_well_e=None, n_frames=400, n_levels=97, decades=None, seed=0)` (実装を直接呼ぶなら `import hdrfusion; hdrfusion.hdr_dynamic_range(exposures, eta=0.6, K=0.1, sigma_d_e=8.0, dark_offset_dn=4.0, bits=8, full_well_e=None, n_frames=400, n_levels=97, decades=None, seed=0)`、台帳から引くなら `opsoptics.get("hdr_dynamic_range")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Measured dynamic range of an HDR capture (EMVA 1288 definition) with its closed form (``table``).

シミュで実測: 放射輝度の等比の階段(``n_levels`` 段、各段 ``n_frames`` 画素 = 繰り返し)を
:func:`hdr_exposure_series_simulate`(線形、γ = 1)で露出の列に撮り、
:func:`hdr_merge`(``weight="linear"``、真の線形の逆応答)で合成し、段ごとに SNR = 平均 / 標準偏差。
  * ``L_min``: SNR が 1 を切る放射輝度(EMVA 1288 の絶対感度しきい値の HDR 版)。
  * ``L_sat``: 最短の露出の出力の**分散が最大**になる放射輝度(EMVA の飽和の定義)を、粗い
    階段で見つけた最大の段のまわりを細かい階段で測り直して決める。
  * ``dr = L_sat / L_min``、``dr_db = 20 log10``、``dr_bits = log2``。
閉形式(並べて返す): 低い側は全露出の和の SNR = 1 ——
:func:`sensorchar.emva_sensitivity_threshold` に ``σ_d → √P σ_d``、``K → K/√P`` を入れた
``μ_p.min`` を ``Σ t`` で割る。高い側は最短の露出が ``2^bits − 1``(または満杯)に届く放射輝度。
露出 1 枚ならそのまま :func:`sensorchar.emva_dynamic_range`。

Measured in simulation (EMVA 1288 definitions: SNR = 1 and the maximum of the variance), with
the closed form side by side. The closed-form saturation is the maximum of the variance of a
clipped Gaussian ``min(N(μ, σ²(μ)), c)`` with ``σ² = K²(σ_d² + μ_e) + 1/12`` (exact censored-
normal moments); ``L_clip_closed_form`` is the plain clip point of the mean, about 5 % higher
(measured). ★Full-well clipping is approximated as a DN clip at ``offset + K·full_well``.

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

- [poc_hdr_glossy_metal_inspection](../../../../examples/poc_hdr_glossy_metal_inspection.py) — `py -3.11 examples/poc_hdr_glossy_metal_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`hdr`)

[camera_response_debevec](camera_response_debevec.md) · [camera_response_robertson](camera_response_robertson.md) · [camera_response_linear](camera_response_linear.md) · [hdr_merge](hdr_merge.md) · [exposure_fusion_mertens](exposure_fusion_mertens.md) · [hdr_exposure_series_simulate](hdr_exposure_series_simulate.md) · [hdr_radiance_error](hdr_radiance_error.md)

---
*Provenance: hdrfusion.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
