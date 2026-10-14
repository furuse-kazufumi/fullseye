---
op: chromatic_confocal_spectrum
dim: optics
category: confocal
in: table
out: pairs
examples: [poc_chromatic_confocal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# chromatic_confocal_spectrum — OPTICS `confocal` op

- **データ種**: `table` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.chromatic_confocal_spectrum(probe, surface_um: 'float' = 500.0, stack=(), substrate='AL', source=None, detector=None, wl_step_nm: 'float' = 0.5, tilt_deg: 'float' = 0.0, roughness_nm: 'float' = 0.0, spectrometer_fwhm_nm: 'float' = 0.0, photons_per_peak: 'float' = 0.0, read_noise: 'float' = 0.0, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import chromconf; chromconf.chromatic_confocal_spectrum(probe, surface_um: 'float' = 500.0, stack=(), substrate='AL', source=None, detector=None, wl_step_nm: 'float' = 0.5, tilt_deg: 'float' = 0.0, roughness_nm: 'float' = 0.0, spectrometer_fwhm_nm: 'float' = 0.0, photons_per_peak: 'float' = 0.0, read_noise: 'float' = 0.0, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsoptics.get("chromatic_confocal_spectrum")`)

## 使い方

面の位置と層構成から、クロマティック共焦点の戻りスペクトルを合成する(順モデル)。

戻りスペクトル S(λ) = 光源(λ) × 検出器(λ) × Σ_界面 [反射率 × 往復の透過 × 傾き・粗さ ×
共焦点の軸応答(界面の見かけの位置 − 近軸焦点(λ); λ, NA(λ), LSA(λ))]、それを分光器の
応答(ガウス、FWHM)でぼかし、光子のショット雑音と読出し雑音を足す。

probe: :func:`chromatic_confocal_probe` の dict。波長の格子は較正の帯域を *wl_step_nm* で刻む。
surface_um: 最上面の位置(較正表の z、µm)。
stack: 最上面の下の透明な層の列 ``((材料, 厚さ µm), ...)``。材料は材料表の名前(:data:`GLASS_CROWN` /
    ``"PMMA"`` / ``"WATER"`` …)か屈折率の数。k があれば往復の吸収 exp(−4πk·2t/λ) が入る。
substrate: 最下層の下の媒質(材料表の名前 —— ``"AL"`` / ``"AU"`` / ``"CU"`` / ``"SI"`` … —— か数、
    空気なら 1.0)。界面の反射率は両側の複素屈折率から垂直入射の Fresnel |(m₁ − m₂)/(m₁ + m₂)|²。
source / detector: 光源の分光分布と検出器の分光感度(pairs、帯域を覆うこと)。None は平坦。
tilt_deg: 面の傾き(全界面に共通)。鏡面成分は瞳との重なりの割合だけ戻る(sin 2θ ≥ 2NA で 0)。
roughness_nm: 面の粗さ σ(RMS)。最上面の鏡面成分は exp(−(4πσ/λ)²)、残りは Lambert で NA² だけ
    戻り、点物体の応答で広がる。
spectrometer_fwhm_nm: 分光器の線幅(0 は理想)。
photons_per_peak: 0 なら雑音なしの期待値(最大を 1 に規格化)。正なら最大が平均この光子数になる
    ように拡大し、Poisson のショット雑音を足す。read_noise: 読出し雑音(光子数の単位の σ)。
seed: 雑音の乱数の種(整数)。

返り値: pairs(λ [nm], 強度)。負は 0 に切る(分光器は負の光を読まない)。
**Raises** ``ValueError``: probe の形の誤り、帯域を覆わない source / detector、層の厚さ ≤ 0、
材料表の区間外の波長、どの界面にも焦点が合わない(全部の界面が較正の範囲外)。

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

- [poc_chromatic_confocal](../../../../examples/poc_chromatic_confocal.py) — `py -3.11 examples/poc_chromatic_confocal.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[mtf50](../imaging/mtf50.md) · [energy_to_photons](../spectral/energy_to_photons.md) · [spectral_product](../spectral/spectral_product.md) · [spectral_integral](../spectral/spectral_integral.md) · [spectral_stats](../spectral/spectral_stats.md) · [film_thickness_fft](../film/film_thickness_fft.md) · [film_thickness_fit](../film/film_thickness_fit.md) · [chromatic_confocal_peaks](chromatic_confocal_peaks.md)

## 同カテゴリ(`confocal`)

[chromatic_confocal_probe](chromatic_confocal_probe.md) · [confocal_axial_response](confocal_axial_response.md) · [chromatic_confocal_peaks](chromatic_confocal_peaks.md) · [chromatic_confocal_readout](chromatic_confocal_readout.md) · [chromatic_confocal_limits](chromatic_confocal_limits.md)

---
*Provenance: chromconf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
