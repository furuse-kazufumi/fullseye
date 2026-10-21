---
op: encircled_energy
dim: optics
category: imaging
in: image2d
out: pairs
examples: [optical_design_metrics, poc_zoom_configurations]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# encircled_energy — OPTICS `imaging` op

- **データ種**: `image2d` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.encircled_energy(psf, pixel_pitch_um=1.0, samples=64, max_radius_um=None, centre='centroid')` (実装を直接呼ぶなら `import optics; optics.encircled_energy(psf, pixel_pitch_um=1.0, samples=64, max_radius_um=None, centre='centroid')`、台帳から引くなら `opsoptics.get("encircled_energy")`)

## 使い方

Encircled energy of a point-spread function: the fraction of the energy inside a circle of radius r.

The standard spot-quality curve of lens design (how much light lands inside a given pixel or fibre
core). *psf* is an ``image2d`` of non-negative samples on a grid of *pixel_pitch_um* (use the
``pixel_pitch_um`` argument of ``lensimage.psf_from_opd``, or the fine-grid spacing of
``pupil_psf``); the circle is centred on the energy centroid by default (*centre* = ``'centroid'``,
``'peak'``, ``'fft'`` for the fftshift origin, or a ``(row, col)`` pair in pixels). Edge pixels are
weighted by the exact area inside the circle, so the curve is smooth in r; a radius under about two
pixels is resolved only coarsely.

Returns a ``(samples, 2)`` float64 ``pairs`` array: column 0 the radius in micrometres from 0 to
*max_radius_um* (default the largest circle that fits in the array about the centre), column 1 the
fraction of the **array's** energy inside, in [0, 1], non-decreasing. Energy outside the array is
not known, so a PSF window that cuts the wings off reads high; keep the window several times the
spot.

Ground truth it reproduces: an unaberrated circular pupil gives the Airy pattern, whose encircled
energy is ``1 - J0(v)^2 - J1(v)^2`` with ``v = 2 pi r / (lambda N)``: 83.8 % at the first dark ring
(``r = 1.2197 lambda N``, Born and Wolf), 91.0 % at the second, 93.8 % at the third (measured in
``tests/test_optdesign_psf_metrics.py``).

**Raises** ``ValueError``: *psf* not 2-D / smaller than 3x3 / negative / zero energy / non-finite;
non-positive *pixel_pitch_um* or *max_radius_um*; *samples* outside ``[2, 4096]``; a radius that
leaves the array; a bad *centre*.

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

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために
- [mv_cameras](../guides/mv_cameras.md) — 産業用カメラメーカー（センサとの紐付け・ラインスキャン / TDI）
- [virtual_machine_vision](../guides/virtual_machine_vision.md) — 仮想マシンビジョン — パラメータの洗い出しとオブジェクト模型

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [optical_design_metrics](../../../../examples/optical_design_metrics.py) — `py -3.11 examples/optical_design_metrics.py`
- [poc_zoom_configurations](../../../../examples/poc_zoom_configurations.py) — `py -3.11 examples/poc_zoom_configurations.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[mtf50](mtf50.md) · [energy_to_photons](../spectral/energy_to_photons.md) · [spectral_product](../spectral/spectral_product.md) · [spectral_integral](../spectral/spectral_integral.md) · [spectral_stats](../spectral/spectral_stats.md) · [kubelka_munk_reflectance](../spectral/kubelka_munk_reflectance.md) · [hyperspectral_capture](../spectral/hyperspectral_capture.md) · [film_thickness_fft](../film/film_thickness_fft.md)

## 同カテゴリ(`imaging`)

[psf_to_mtf](psf_to_mtf.md) · [mtf_diffraction](mtf_diffraction.md) · [ensquared_energy](ensquared_energy.md) · [energy_radii](energy_radii.md) · [mtf_tangential_sagittal](mtf_tangential_sagittal.md) · [wavefront_stats](wavefront_stats.md) · [edge_spread](edge_spread.md) · [sfr_from_edge](sfr_from_edge.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
