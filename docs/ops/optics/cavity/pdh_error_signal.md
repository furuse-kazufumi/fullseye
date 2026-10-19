---
op: pdh_error_signal
dim: optics
category: cavity
in: 
out: pairs
examples: [poc_gw_detector_pseudo_simulation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# pdh_error_signal — OPTICS `cavity` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.pdh_error_signal(length_m: 'float' = 1.0, *, itm_transmittance: 'float' = 0.01, etm_transmittance: 'float' = 0.01, mod_freq_hz: 'float' = 20000000.0, mod_depth: 'float' = 1.08, power_w: 'float' = 1.0, span_linewidths: 'float' = 6.0, n_points: 'int' = 1201) -> 'np.ndarray'` (実装を直接呼ぶなら `import cavityoptics; cavityoptics.pdh_error_signal(length_m: 'float' = 1.0, *, itm_transmittance: 'float' = 0.01, etm_transmittance: 'float' = 0.01, mod_freq_hz: 'float' = 20000000.0, mod_depth: 'float' = 1.08, power_w: 'float' = 1.0, span_linewidths: 'float' = 6.0, n_points: 'int' = 1201) -> 'np.ndarray'`、台帳から引くなら `opsoptics.get("pdh_error_signal")`)

## 使い方

Pound-Drever-Hall 誤差信号 ε(δ) を、共振からの離調 δ [Hz] の関数として ``pairs`` で返す。

Parameters
----------
length_m : float
    共振器長 L [m]。
itm_transmittance, etm_transmittance : float
    鏡の強度透過率(損失なし)。
mod_freq_hz : float
    位相変調周波数 Ω/2π [Hz]。線幅より十分大きいと傾きが Black の式 15 に乗る。
mod_depth : float
    変調指数 β。搬送波 ``P_c = J₀(β)²P``、側帯波 ``P_s = J₁(β)²P``(β = 1.08 で ``P_c·P_s`` 最大)。
power_w : float
    入射光量 P [W]。
span_linewidths : float
    表示する離調の範囲(線幅の何倍まで、±)。
n_points : int
    点数(奇数なら δ = 0 を含む)。

Returns
-------
numpy.ndarray
    ``(n_points, 2)``: 列 0 = 離調 δ [Hz]、列 1 = ε [W]
    ``= 2√(P_c P_s)·Im[F(δ)F*(δ+Ω) − F*(δ)F(δ−Ω)]``。

Notes
-----
門(``tests``): 反対称 ``ε(−δ) = −ε(δ)``(1e-12)、``ε(0) = 0``、対称共振器
(T₁ = T₂)で Ω ≫ δν のとき共振近傍の傾き ``dε/dδ = −8√(P_c P_s)/δν``(Black 2001 式 15)に
1 % 以内。側帯波が共振に乗る ``δ = ±Ω`` 付近の小さな山も含めて返す(表示範囲が届けば)。

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

- [poc_gw_detector_pseudo_simulation](../../../../examples/poc_gw_detector_pseudo_simulation.py) — `py -3.11 examples/poc_gw_detector_pseudo_simulation.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[mtf50](../imaging/mtf50.md) · [energy_to_photons](../spectral/energy_to_photons.md) · [spectral_product](../spectral/spectral_product.md) · [spectral_integral](../spectral/spectral_integral.md) · [spectral_stats](../spectral/spectral_stats.md) · [kubelka_munk_reflectance](../spectral/kubelka_munk_reflectance.md) · [hyperspectral_capture](../spectral/hyperspectral_capture.md) · [film_thickness_fft](../film/film_thickness_fft.md)

## 同カテゴリ(`cavity`)

[fabry_perot_response](fabry_perot_response.md) · [cavity_strain_transfer](cavity_strain_transfer.md) · [michelson_dc_readout](michelson_dc_readout.md) · [quantum_noise_budget](quantum_noise_budget.md)

---
*Provenance: cavityoptics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
