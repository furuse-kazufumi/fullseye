---
op: tem_ctf_correct
dim: optics
category: tem
in: image2d
out: image2d
examples: [poc_tem_ctf_thon_rings]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# tem_ctf_correct — OPTICS `tem` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.tem_ctf_correct(image, pixel_A=1.0, kv=300.0, cs_mm=2.7, defocus_A=10000.0, astig_A=None, astig_angle_deg=None, amplitude_contrast=0.07, phase_shift_deg=0.0, method='phase_flip', snr=None)` (実装を直接呼ぶなら `import temsim; temsim.tem_ctf_correct(image, pixel_A=1.0, kv=300.0, cs_mm=2.7, defocus_A=10000.0, astig_A=None, astig_angle_deg=None, amplitude_contrast=0.07, phase_shift_deg=0.0, method='phase_flip', snr=None)`、台帳から引くなら `opsoptics.get("tem_ctf_correct")`)

## 使い方

CTF の補正(``image2d``)。``method="phase_flip"``: F⁻¹[ F(I − ⟨I⟩) · sign(CTF) ] (位相反転、振幅はそのまま)/
``"wiener"``: F⁻¹[ F(I − ⟨I⟩) · CTF / (CTF² + 1/snr) ]。

補正後は正のポテンシャル(原子)が**明るく**写る向き(I − 1 ≈ 2 Φ CTF に sign(CTF) か CTF を掛けるので)。
焦点外れを間違えると、零点の外側で符号を逆に掛けて像が壊れる(PoC の探針)。包絡は掛けない(位相反転は振幅を
戻さない、ウィーナーは ``snr`` が高周波の増幅を抑える)。``snr`` はウィーナーだけの引数(None = 10、
位相反転に渡すと ValueError)。``astig_A`` / ``astig_angle_deg`` は None = 非点収差なし。

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

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [edge_spread](../imaging/edge_spread.md) · [veiling_glare_index](../imaging/veiling_glare_index.md) · [emva_pair_statistics](../sensorchar/emva_pair_statistics.md) · [emva_defect_pixels](../sensorchar/emva_defect_pixels.md)

## 同カテゴリ(`tem`)

[tem_wavelength](tem_wavelength.md) · [tem_scherzer](tem_scherzer.md) · [tem_ctf](tem_ctf.md) · [tem_ctf_profile](tem_ctf_profile.md) · [tem_projected_potential](tem_projected_potential.md) · [tem_amorphous_film](tem_amorphous_film.md) · [tem_image_weak_phase](tem_image_weak_phase.md) · [tem_multislice](tem_multislice.md)

---
*Provenance: temsim.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
