---
op: spectrometer_spectrum
dim: optics
category: spectrometer
in: table × pairs
out: pairs
examples: [poc_spectrometer_illumination]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# spectrometer_spectrum — OPTICS `spectrometer` op

- **データ種**: `table × pairs` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.spectrometer_spectrum(design, spectrum, slit_width_um=25.0, pixel_um=14.0, input_na=0.1, max_order_multiple=3, higher_order_efficiency=0.3, longpass_nm=None, oversample=8, pupil='circular')` (実装を直接呼ぶなら `import gratingspec; gratingspec.spectrometer_spectrum(design, spectrum, slit_width_um=25.0, pixel_um=14.0, input_na=0.1, max_order_multiple=3, higher_order_efficiency=0.3, longpass_nm=None, oversample=8, pupil='circular')`、台帳から引くなら `opsoptics.get("spectrometer_spectrum")`)

## 使い方

入力スペクトル → 検出器の画素の読み(1 次の像に高次の像が重なる)。

design: :func:`czerny_turner_design` の表。spectrum: pairs(λ [nm] 昇順, 分光放射輝度 ≥ 0、nm あたり)。
slit_width_um / pixel_um / input_na / pupil: :func:`spectrometer_bandpass` と同じ(装置関数を決める)。
max_order_multiple: 設計の次数 m の何倍までの次数を足すか(1 = 高次なし、3 なら m, 2m, 3m)。
higher_order_efficiency: 高次の回折効率の 1 次に対する比(次数によらず一定の模型)。
longpass_nm: 入口のロングパスのフィルタの端(これより短い光を 0 にする。None = フィルタなし)。
oversample: 画素を何分割して像を置くか(畳み込みの精度)。

返り値: pairs(画素の中心の波長 [nm]、1 次の校正で、読み(nm あたりの放射輝度 × 帯域の幅の単位))。
装置関数は中心波長のもの(スリットの像と回折の幅の波長による変化は入れない —— 帯域ごとの幅は
:func:`spectrometer_bandpass` が出す)。

**Raises** ``ValueError``: 入力が粗すぎて装置関数の FWHM の 1/3 より細かく標本化されていない、
昇順でない・負・非有限のスペクトル、設計の表でない、引数の範囲外。

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

- [poc_spectrometer_illumination](../../../../examples/poc_spectrometer_illumination.py) — `py -3.11 examples/poc_spectrometer_illumination.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[mtf50](../imaging/mtf50.md) · [energy_to_photons](../spectral/energy_to_photons.md) · [spectral_product](../spectral/spectral_product.md) · [spectral_integral](../spectral/spectral_integral.md) · [spectral_stats](../spectral/spectral_stats.md) · [kubelka_munk_reflectance](../spectral/kubelka_munk_reflectance.md) · [hyperspectral_capture](../spectral/hyperspectral_capture.md) · [film_thickness_fft](../film/film_thickness_fft.md)

## 同カテゴリ(`spectrometer`)

[grating_dispersion](grating_dispersion.md) · [czerny_turner_design](czerny_turner_design.md) · [spectrometer_bandpass](spectrometer_bandpass.md) · [spectrometer_slit_image](spectrometer_slit_image.md)

---
*Provenance: gratingspec.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
