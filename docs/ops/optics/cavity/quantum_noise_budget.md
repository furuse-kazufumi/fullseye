---
op: quantum_noise_budget
dim: optics
category: cavity
in: 
out: table
examples: [poc_gw_detector_pseudo_simulation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# quantum_noise_budget — OPTICS `cavity` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.quantum_noise_budget(power_w: 'float' = 5200.0, mirror_mass_kg: 'float' = 40.0, length_m: 'float' = 3994.5, wavelength_nm: 'float' = 1064.0, *, itm_transmittance: 'float' = 0.014, f_min_hz: 'float' = 5.0, f_max_hz: 'float' = 5000.0, n_points: 'int' = 400) -> 'dict'` (実装を直接呼ぶなら `import cavityoptics; cavityoptics.quantum_noise_budget(power_w: 'float' = 5200.0, mirror_mass_kg: 'float' = 40.0, length_m: 'float' = 3994.5, wavelength_nm: 'float' = 1064.0, *, itm_transmittance: 'float' = 0.014, f_min_hz: 'float' = 5.0, f_max_hz: 'float' = 5000.0, n_points: 'int' = 400) -> 'dict'`、台帳から引くなら `opsoptics.get("quantum_noise_budget")`)

## 使い方

通常の(信号再利用なし)Fabry-Perot Michelson の量子雑音 —— 散射・輻射圧・標準量子限界。

Parameters
----------
power_w : float
    ビームスプリッタに入る光量 I₀ [W] (aLIGO 設計: 125 W × 出力再利用 ≈ 5.2 kW)。
mirror_mass_kg : float
    試験質量 m [kg] (aLIGO 40 kg)。
length_m : float
    腕の長さ L [m]。
wavelength_nm : float
    波長 [nm]。
itm_transmittance : float
    入力鏡の強度透過率 T(腕共振器の半値半幅 ``γ = Tc/4L`` [rad/s] を決める)。
f_min_hz, f_max_hz : float
    周波数範囲(対数等間隔)。
n_points : int
    点数。

Returns
-------
dict
    ``f_hz``(配列)、振幅スペクトル密度 [1/√Hz] の配列 ``shot`` / ``radiation_pressure`` /
    ``sql`` / ``total``(``√(S_shot + S_rp)``)、``kappa``(Kimble の K(Ω))、
    スカラ ``gamma_rad_s`` / ``pole_hz`` / ``i_sql_w``(``I_SQL = mL²γ⁴/4ω₀``)/
    ``power_ratio`` = I₀/I_SQL / ``f_sql_touch_hz``(K = 1 で総和が SQL に触れる周波数、
    無ければ ``None``)/ ``arm_power_w``(循環光量 ≈ ``I₀·2/T`` の目安)。

Notes
-----
Kimble, Levin, Matsko, Thorne & Vyatchanin, *Phys. Rev. D* 65, 022002 (2001) 式 (16)–(20):
``h_SQL² = 8ħ/(mΩ²L²)``、``K = 2(I₀/I_SQL)γ⁴/(Ω²(γ²+Ω²))``、``S_shot = h_SQL²/2K``、
``S_rp = K h_SQL²/2``。門: ``S_shot·S_rp = h_SQL⁴/4``(光量に依らない恒等式)、
``S_total ≥ h_SQL²`` で等号は K = 1 だけ。I₀ = I_SQL のとき K(γ) = 1 なので ``f_sql_touch_hz``
= γ/2π。aLIGO の設計感度は信号再利用と熱雑音を含むのでこの曲線とは形が違う ——
``examples/poc_gw_detector_pseudo_simulation.py`` が設計曲線と第二実装(gwinc)に当てる。

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

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`cavity`)

[fabry_perot_response](fabry_perot_response.md) · [cavity_strain_transfer](cavity_strain_transfer.md) · [michelson_dc_readout](michelson_dc_readout.md) · [pdh_error_signal](pdh_error_signal.md)

---
*Provenance: cavityoptics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
