---
op: spectrometer_slit_image
dim: optics
category: spectrometer
in: table
out: table
examples: [poc_spectrometer_illumination]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# spectrometer_slit_image — OPTICS `spectrometer` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spectrometer_slit_image(design, slit_height_mm=2.0, wavelengths_nm=None, n_points=21, rule='vector')` (実装を直接呼ぶなら `import gratingspec; gratingspec.spectrometer_slit_image(design, slit_height_mm=2.0, wavelengths_nm=None, n_points=21, rule='vector')`、台帳から引くなら `opsoptics.get("spectrometer_slit_image")`)

## 使い方

長いスリットの像を 3 次元で追い、smile(線の曲がり)と keystone(空間倍率の色ずれ)を出す。

design: :func:`czerny_turner_design` の表。slit_height_mm: スリットの長さ(溝の向き)。
wavelengths_nm: 評価する波長(None なら帯域の 5 点)。n_points: スリットに沿った標本数(奇数にすると中心を含む)。
rule: ``"vector"``(3 次元の格子の式、既定)/ ``"scalar"``(面内の式を流用する**壊した模型**。
  門の探針で、smile の閉形式から外れることを確かめるために残してある)。

返り値(table):

* ``x_mm`` / ``y_mm`` —— (波長, スリットの点) の像の位置(検出器の中心 = λ_c の中心光線)。
* ``smile_um`` —— スリットの端の像の x − 中心の像の x(波長ごと、正 = 長い波長の側)。
* ``smile_closed_um`` —— y'² (sin α + sin β) / (2 f_cam cos β)(放物線の近似)。
* ``curvature_radius_mm`` —— ρ = f_cam cos β / (sin α + sin β)。
* ``keystone_um`` —— スリットの端の像の y − 中心波長での y(波長ごと)。
  ``keystone_closed_um`` = y'(λ_c) (1 / cos(β − β_c) − 1)。
* ``anamorphic_trace`` / ``anamorphic_closed`` —— スリットの幅方向の倍率 dx'/dx_s を追跡と閉形式
  (f_cam / f_col)(cos α / cos β) / cos²(β − β_c)(平らな検出器)で。

**Raises** ``ValueError``: 設計の表でない、帯域の外、高さ ≤ 0、rule の名前の誤り、伝わらない光。

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

[grating_dispersion](grating_dispersion.md) · [czerny_turner_design](czerny_turner_design.md) · [spectrometer_bandpass](spectrometer_bandpass.md) · [spectrometer_spectrum](spectrometer_spectrum.md)

---
*Provenance: gratingspec.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
