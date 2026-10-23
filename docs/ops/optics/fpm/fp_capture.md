---
op: fp_capture
dim: optics
category: fpm
in: image2d × image2d
out: table
examples: [poc_fourier_ptychography]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# fp_capture — OPTICS `fpm` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fp_capture(amplitude, phase=None, pixel_um=0.325, wavelength_um=0.532, na_obj=0.1, downsample=4, led_pitch_mm=4.0, led_distance_mm=70.0, n_side=13, pupil_aberration=None, photons=4000.0, read_noise_e=2.0, darkfield_gain=8.0, cos_exponent=1.0, seed=0, led_offset_mm=(0.0, 0.0), led_rotation_deg=0.0, led_height_error_mm=0.0, height_um=None, pad_px=None)` (実装を直接呼ぶなら `import fourierptycho; fourierptycho.fp_capture(amplitude, phase=None, pixel_um=0.325, wavelength_um=0.532, na_obj=0.1, downsample=4, led_pitch_mm=4.0, led_distance_mm=70.0, n_side=13, pupil_aberration=None, photons=4000.0, read_noise_e=2.0, darkfield_gain=8.0, cos_exponent=1.0, seed=0, led_offset_mm=(0.0, 0.0), led_rotation_deg=0.0, led_height_error_mm=0.0, height_um=None, pad_px=None)`、台帳から引くなら `opsoptics.get("fp_capture")`)

## 使い方

LED アレイで斜めに照らした低解像の像の組を合成する(``table``、kind="fp_stack")。

物体 o = amplitude · e^{i phase}(``pixel_um`` の細かい格子、正方で一辺が ``downsample`` で割り切れる)。
LED ごとに o に傾いた平面波 e^{i2π(kx x + ky y)} を掛け(**画素の半端な k もそのまま**)、FFT → 中心を
低解像の大きさで切り出す → 瞳(円 NA_obj/λ × 収差)→ 逆 FFT → |·|²。視野の外の光が入るよう、物体を ``pad_px``
(既定 = 一辺の 1/4)だけ端の値で広げて描き、カメラの視野だけを切り出す(実際の試料は周期的でない)。

* ``height_um`` を渡すと**反射型**: 面の高さ h → 往復の位相 4πh/λ(垂直入射の近似)を ``phase`` に足す。
* LED の明るさ: 方位の Lambert 次数 m(``cos_exponent``)と距離の 2 乗の落ち → cos^(m+3)θ(中心で 1)。
* 露光: 明視野(NA_ill < NA_obj)は 1、暗視野は ``darkfield_gain`` 倍(暗視野を長く撮る実装の慣習)。
* 雑音: 背景 1 あたり ``photons`` 電子 × 露光 × 明るさの Poisson + 読み出し ``read_noise_e`` のガウス。
  乱数は ``seed`` の ``np.random.default_rng``。
* LED アレイのずれ(``led_offset_mm`` / ``led_rotation_deg`` / ``led_height_error_mm``)は**撮像にだけ**入れ、
  表の名目の ``kx`` / ``ky`` には入れない(真の値は ``kx_true`` / ``ky_true``)。
* 低解像の画素 = pixel_um · downsample が λ/(2 NA_obj) を超えると拒否(FP の標本化条件)。

返り値: dict(kind="fp_stack", images (K, n, n) 電子数、照明の NA の小さい順, exposure, led_brightness, photons,
read_noise_e, kx, ky, kx_true, ky_true, na_illumination, led_index, led_xyz_mm(名目), pixel_um(低解像),
wavelength_um, na_obj, pupil_true, na_synthetic_design, …)。

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

- [poc_fourier_ptychography](../../../../examples/poc_fourier_ptychography.py) — `py -3.11 examples/poc_fourier_ptychography.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`fpm`)

[fp_design](fp_design.md) · [fp_usaf_target](fp_usaf_target.md) · [fp_stack_from_images](fp_stack_from_images.md) · [fp_reconstruct](fp_reconstruct.md) · [fp_element_contrast](fp_element_contrast.md)

---
*Provenance: fourierptycho.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
