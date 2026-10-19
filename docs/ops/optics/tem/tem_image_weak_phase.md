---
op: tem_image_weak_phase
dim: optics
category: tem
in: image2d
out: image2d
examples: [poc_tem_ctf_thon_rings]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# tem_image_weak_phase — OPTICS `tem` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.tem_image_weak_phase(potential, pixel_A=1.0, kv=300.0, cs_mm=2.7, defocus_A=10000.0, astig_A=0.0, astig_angle_deg=None, amplitude_contrast=0.07, phase_shift_deg=0.0, alpha_mrad=0.0, focal_spread_A=0.0, aperture_A_inv=None, mode='linear', dose_e_per_A2=None, seed=0)` (実装を直接呼ぶなら `import temsim; temsim.tem_image_weak_phase(potential, pixel_A=1.0, kv=300.0, cs_mm=2.7, defocus_A=10000.0, astig_A=0.0, astig_angle_deg=None, amplitude_contrast=0.07, phase_shift_deg=0.0, alpha_mrad=0.0, focal_spread_A=0.0, aperture_A_inv=None, mode='linear', dose_e_per_A2=None, seed=0)`、台帳から引くなら `opsoptics.get("tem_image_weak_phase")`)

## 使い方

投影ポテンシャル v_z [V Å] から TEM の明視野像(平均 1 の強度、``image2d``)。

``mode="linear"``: 弱位相物体近似 I = 1 + 2 F⁻¹[ F(σ v_z) · CTF · E ] / √(1 − w²)(位相が 1 rad より十分小さいとき)。
``mode="coherent"``: 透過関数 exp(iσ v_z − a σ v_z)(a = w / √(1 − w²))を ``coherent.coherent_image`` に
瞳 = 開口 × e^{iχ} × 包絡(準コヒーレント)で渡す —— 位相が大きいと線形の像からずれる(その差が弱位相近似の誤差)。
``aperture_A_inv`` は対物絞りの半径 [Å⁻¹] (None = 無し)。``dose_e_per_A2`` を与えると画素あたり
dose × 画素面積 の電子の Poisson 雑音を足し、平均 1 に戻して返す(``seed`` で決まる)。

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

- [poc_tem_ctf_thon_rings](../../../../examples/poc_tem_ctf_thon_rings.py) — `py -3.11 examples/poc_tem_ctf_thon_rings.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [encircled_energy](../imaging/encircled_energy.md) · [ensquared_energy](../imaging/ensquared_energy.md) · [energy_radii](../imaging/energy_radii.md) · [mtf_tangential_sagittal](../imaging/mtf_tangential_sagittal.md)

## 同カテゴリ(`tem`)

[tem_wavelength](tem_wavelength.md) · [tem_scherzer](tem_scherzer.md) · [tem_ctf](tem_ctf.md) · [tem_ctf_profile](tem_ctf_profile.md) · [tem_projected_potential](tem_projected_potential.md) · [tem_amorphous_film](tem_amorphous_film.md) · [tem_multislice](tem_multislice.md) · [tem_power_spectrum](tem_power_spectrum.md)

---
*Provenance: temsim.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
