---
op: psf_from_opd
dim: optics
category: imaging_sim
in: table
out: image2d
examples: [lens_defect_dataset_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# psf_from_opd — OPTICS `imaging_sim` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import lensimage; lensimage.psf_from_opd(system, field=None, size=None, wavelength_um=None, pixel_pitch_um=None, oversample=4)` (または `opsoptics.get("psf_from_opd")`)

## 使い方

Diffraction PSF of the real, aberrated pupil (``image2d``, sums to 1).

The pupil function ``P = mask · exp(i·2π·W)`` comes from
:func:`raytrace.opd_samples` (*W* in waves on a ``size × size`` grid over the
exit pupil; ``size=None`` picks a grid that keeps the phase below 0.4 waves
per sample, up to :data:`MAX_PUPIL_SAMPLES`; an explicit *size* that aliases
is refused). The PSF is ``|FFT(P)|²`` on a zero-padded grid whose sample
spacing is ``λ·F#·(size−1)/M ≈ λ·F#/oversample`` with the working
f-number ``F# = 1/(2·NA_image)`` from :func:`raytrace.paraxial_trace`.
With *pixel_pitch_um* the fine PSF is **area-integrated** onto detector
pixels of that pitch (each fine sample is binned into the pixel it falls
in; the pitch must not be finer than the sample spacing).

Ground truth (``tests/test_lensimage.py``): an unaberrated pupil (the
singlet stopped to a 1 mm semi-aperture) gives the Airy pattern — first
dark ring at ``1.22·λ·F#`` within 3 %, 83.8 % ± 1 % of the energy inside
it; the f/4 singlet (11 waves of spherical aberration) has a Strehl ratio
below 0.05 (peak versus the unaberrated peak of the same pupil).

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

- [mv_cables](../guides/mv_cables.md) — ケーブル（規格・速度・給電・ロボットケーブル）
- [mv_cameras](../guides/mv_cameras.md) — 産業用カメラメーカー（センサとの紐付け・ラインスキャン / TDI）
- [mv_frame_grabbers](../guides/mv_frame_grabbers.md) — フレームグラバーボード（光学系ではないが、撮れるかを決める）
- [mv_image_sensors](../guides/mv_image_sensors.md) — 産業用イメージセンサ（現行品中心）
- [mv_standards](../guides/mv_standards.md) — カメラインターフェースの規格と団体
- [virtual_machine_vision](../guides/virtual_machine_vision.md) — 仮想マシンビジョン — パラメータの洗い出しとオブジェクト模型

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lens_defect_dataset_demo](../../../../examples/lens_defect_dataset_demo.py) — `py -3.11 examples/lens_defect_dataset_demo.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [illumination_uniformity](../illumination/illumination_uniformity.md) · [render_through_lens](render_through_lens.md) · [surface_defect](../scene/surface_defect.md) · [defocus_blur](../scene/defocus_blur.md)

## 同カテゴリ(`imaging_sim`)

[distortion_map](distortion_map.md) · [render_through_lens](render_through_lens.md) · [defect_dataset](defect_dataset.md) · [calibration_views](calibration_views.md)

---
*Provenance: lensimage.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
