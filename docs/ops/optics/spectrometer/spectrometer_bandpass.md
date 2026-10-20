---
op: spectrometer_bandpass
dim: optics
category: spectrometer
in: table
out: table
examples: [poc_spectrometer_illumination]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# spectrometer_bandpass — OPTICS `spectrometer` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spectrometer_bandpass(design, slit_width_um=25.0, pixel_um=14.0, input_na=0.1, wavelengths_nm=None, slit_height_mm=1.0, pupil='circular')` (実装を直接呼ぶなら `import gratingspec; gratingspec.spectrometer_bandpass(design, slit_width_um=25.0, pixel_um=14.0, input_na=0.1, wavelengths_nm=None, slit_height_mm=1.0, pupil='circular')`、台帳から引くなら `opsoptics.get("spectrometer_bandpass")`)

## 使い方

分光器の帯域の幅(装置関数の FWHM)を、スリット・画素・回折から波長ごとに出す。

design: :func:`czerny_turner_design` の表。
slit_width_um: 入口スリットの幅 w。0 は理想の点(回折と画素だけが残る)。
pixel_um: 検出器の画素の幅(分散方向)。0 は理想の連続の検出器。
input_na: スリットに入る光の NA(コリメータで平行になったビームの直径 D = 2 f_col tan(asin NA) を決め、
  照らされた溝の数 N = D / (d cos α) と回折の線幅を決める)。
wavelengths_nm: 評価する波長(None なら帯域の 5 点)。
slit_height_mm: スリットの高さ(エタンデュだけに効く)。
pupil: ``"circular"``(円いビーム、既定)/ ``"rectangular"``(一様に照らした矩形 = 教科書の mN)。

返り値(table、波長ごとの配列):

* ``slit_image_um`` —— w' = w (f_cam / f_col)(cos α / cos β)(Palmer (8-11a)、焦点面の上、収差なし)。
* ``reciprocal_dispersion_nm_per_mm`` —— P = d cos β / (|m| f_cam)(焦点面の上)。
* ``slit_image_flat_um`` / ``reciprocal_dispersion_flat_nm_per_mm`` / ``obliquity_factor`` —— カメラの軸に
  垂直な平らな検出器の上(局所の倍率 1 / cos²(β − β_c)、:func:`czerny_turner_design` の写像 x = f tan(β − β_c)
  と同じ)。装置関数と FWHM はこちらで作る。積 w' P(スリットで決まる帯域)はどちらでも同じ。
* ``slit_limited_nm`` (= w d cos α / (|m| f_col)、β に依らない) / ``pixel_limited_nm`` (= p P) /
  ``palmer_bandpass_nm`` (= P sup(w', p)、Palmer (8-12)) / ``diffraction_fwhm_nm``(回折だけの FWHM)/
  ``rayleigh_limit_nm`` (= λ / (|m| N))。
* ``fwhm_um`` / ``fwhm_nm`` —— 装置関数(回折 ⊗ スリットの像 ⊗ 画素)の FWHM。
* ``resolving_power`` (= λ / FWHM) / ``grating_resolving_power`` (= |m| N) / ``pixels_per_fwhm``。
* ``regime`` —— 最も幅の大きい寄与(``"slit"`` / ``"pixel"`` / ``"diffraction"``)。
* ``line_shapes`` —— 波長ごとの装置関数 pairs(Δλ [nm], 最大 1 に正規化)。
* ``etendue_mm2sr`` —— スリットの面積 × π NA²(スループットはこれに比例する。w と分解能の取引)。

**Raises** ``ValueError``: 設計の表でない、帯域の外の波長、NA が (0, 0.95] の外、幅が負、瞳の名前の誤り。

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

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`spectrometer`)

[grating_dispersion](grating_dispersion.md) · [czerny_turner_design](czerny_turner_design.md) · [spectrometer_slit_image](spectrometer_slit_image.md) · [spectrometer_spectrum](spectrometer_spectrum.md)

---
*Provenance: gratingspec.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
