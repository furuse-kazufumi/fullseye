---
op: light_section_render
dim: optics
category: light_section
in: table × pairs
out: image2d
gpu: なし
examples: [poc_light_section_step_weld_floor]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# light_section_render — OPTICS `light_section` op

- **データ種**: `table × pairs` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.light_section_render(rig, profile, line_sigma_px=1.5, peak=1.0, background=0.0, noise=0.0, seed=0, sampling='point')` (実装を直接呼ぶなら `import lightsection; lightsection.light_section_render(rig, profile, line_sigma_px=1.5, peak=1.0, background=0.0, noise=0.0, seed=0, sampling='point')`、台帳から引くなら `opsoptics.get("light_section_render")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Image of the laser line on a surface profile seen by the rig's camera (``image2d``).

``profile`` は光面(世界 ``Y = 0``)上の断面 ``(x_mm, h_mm)`` の (K, 2) の並び(x は単調増加)。
各点を :func:`camera.project_points` で写し、画像の列ごとに断面の像の行 ``v(u)`` を線形補間し、
行の向きに σ = ``line_sigma_px`` のガウスの光条を描く(``sampling="point"`` = 画素中心の点標本、
``"pixel"`` = 画素の面積で積分した誤差関数の差)。断面の外の列は背景だけ。
``noise`` は加法ガウス雑音の標準偏差(``seed``)。

``profile`` is the (K, 2) cross-section ``(x_mm, h_mm)`` on the laser plane (x increasing).
The points are projected with :func:`camera.project_points`, the image row of the profile
``v(u)`` is linearly interpolated per column, and a Gaussian line of σ = ``line_sigma_px``
is drawn along the rows (``"point"`` = point samples at pixel centres, ``"pixel"`` = the
pixel-area integral). ★Limits: constant line width, no foreshortening, no defocus, no
self-occlusion (a step's shadow) and no inter-reflection; a profile whose image folds over
(``u`` not monotonic) is refused. The rig must carry ``R, t`` (made by
:func:`light_section_rig`).

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

- [poc_light_section_step_weld_floor](../../../../examples/poc_light_section_step_weld_floor.py) — `py -3.11 examples/poc_light_section_step_weld_floor.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [encircled_energy](../imaging/encircled_energy.md) · [ensquared_energy](../imaging/ensquared_energy.md) · [energy_radii](../imaging/energy_radii.md) · [mtf_tangential_sagittal](../imaging/mtf_tangential_sagittal.md)

## 同カテゴリ(`light_section`)

[laser_line_center_centroid](laser_line_center_centroid.md) · [laser_line_center_gauss](laser_line_center_gauss.md) · [laser_line_center_steger](laser_line_center_steger.md) · [light_section_rig](light_section_rig.md) · [light_section_targets](light_section_targets.md) · [light_plane_calibrate](light_plane_calibrate.md) · [light_section_profile](light_section_profile.md) · [light_section_scan](light_section_scan.md)

---
*Provenance: lightsection.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
