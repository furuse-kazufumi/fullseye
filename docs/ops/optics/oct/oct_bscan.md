---
op: oct_bscan
dim: optics
category: oct
in: table
out: image2d
examples: [poc_industrial_oct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# oct_bscan — OPTICS `oct` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.oct_bscan(spectra, window='hann', dc='reference', zero_pad=1, a2=0.0, a3=0.0, method='cubic', db_range=None, k_center=None)` (実装を直接呼ぶなら `import octscan; octscan.oct_bscan(spectra, window='hann', dc='reference', zero_pad=1, a2=0.0, a3=0.0, method='cubic', db_range=None, k_center=None)`、台帳から引くなら `opsoptics.get("oct_bscan")`)
- **台帳経由の戻り値**: `fullseye.ledger.oct_bscan(...)` は**宣言 out 型 `image2d` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.oct_bscan.raw(...)`、または `octscan.oct_bscan` を直接呼ぶ。

## 使い方

B スキャンの干渉スペクトルの束 → **断面像**(深さ × 横、``table``。台帳の宣言は 20 log10 の画像 image2d)。

各列を ``oct_k_linearize``(``method``)→ ``oct_ascan`` にかける。``dc``: "reference"(既定、参照腕だけの
スペクトルを引く)/ "mean"(参照を測っていない装置の常套手段 = 列の中央値を引く。★横に一様な界面 ——
平らな表面 —— の干渉縞も全列に共通なので**一緒に消え**、段差があると片側の深さに負の幽霊が出る)/
"reference+sample"(自己相関も消す)/ "none"。返り値: dict(kind="oct_bscan", image_db (Z, W)、z_um、x_um、noise_db
(雑音の rms の dB)、center_nm、bandwidth_nm)。``db_range`` = (下, 上) を渡すと image_db をその範囲に切る。

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

- [poc_industrial_oct](../../../../examples/poc_industrial_oct.py) — `py -3.11 examples/poc_industrial_oct.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [encircled_energy](../imaging/encircled_energy.md) · [ensquared_energy](../imaging/ensquared_energy.md) · [energy_radii](../imaging/energy_radii.md) · [mtf_tangential_sagittal](../imaging/mtf_tangential_sagittal.md)

## 同カテゴリ(`oct`)

[oct_design](oct_design.md) · [oct_dispersion_broadening](oct_dispersion_broadening.md) · [oct_interferogram](oct_interferogram.md) · [oct_bscan_simulate](oct_bscan_simulate.md) · [oct_from_spectra](oct_from_spectra.md) · [oct_k_linearize](oct_k_linearize.md) · [oct_dispersion_estimate](oct_dispersion_estimate.md) · [oct_dispersion_compensate](oct_dispersion_compensate.md)

---
*Provenance: octscan.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
