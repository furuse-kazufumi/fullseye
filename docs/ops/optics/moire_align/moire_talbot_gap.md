---
op: moire_talbot_gap
dim: optics
category: moire_align
in: 
out: table
examples: [poc_moire_alignment, poc_moire_screen]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# moire_talbot_gap — OPTICS `moire_align` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.moire_talbot_gap(p_mask_um=2.0, wavelength_um=0.55, gap_um=10.0, duty=0.5, samples=512)` (実装を直接呼ぶなら `import moirealign; moirealign.moire_talbot_gap(p_mask_um=2.0, wavelength_um=0.55, gap_um=10.0, duty=0.5, samples=512)`、台帳から引くなら `opsoptics.get("moire_talbot_gap")`)

## 使い方

近接ギャップの Talbot 効果: マスクの格子の像が、ギャップの先でどれだけ・どちらの符号で残るか。

近接露光ではマスクとウェハの間にギャップ g があり、マスクの格子を通った光はウェハに届くまでに回折する。
縞の振幅はマスクの像の基本波(1/p の成分)に比例するので、その振幅の gap = 0 に対する比を返す。
対称な格子ではこの比は**実数**で、ギャップによって符号が反転する(反転 = 縞が半周期ずれる = 読みが p/2 跳ぶ)。
Talbot 長 z_T = 2p²/λ(近軸)で像は元に戻り、z_T/2 で半周期ずれた像になる。
伝搬は ``optics.angular_spectrum_propagate``(近軸近似を使わない)なので、z_T は近軸の値からわずかにずれる。

返り値: dict(contrast_ratio(符号つき)、phase_rad(0 か π)、talbot_length_um(近軸 2p²/λ)、
fundamental(複素の基本波係数)、fundamental_at_contact)。
**Raises** ValueError: 正でないピッチ・波長、負のギャップ、duty が (0, 1) の外、p < λ(伝搬する回折次数が無い)。

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

- [poc_moire_alignment](../../../../examples/poc_moire_alignment.py) — `py -3.11 examples/poc_moire_alignment.py`
- [poc_moire_screen](../../../../examples/poc_moire_screen.py) — `py -3.11 examples/poc_moire_screen.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`moire_align`)

[moire_magnification](moire_magnification.md) · [moire_overlay_image](moire_overlay_image.md) · [moire_phase](moire_phase.md) · [moire_phase_to_shift](moire_phase_to_shift.md) · [moire_differential_shift](moire_differential_shift.md) · [moire_mark_read](moire_mark_read.md) · [moire_phase_crlb](moire_phase_crlb.md)

---
*Provenance: moirealign.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
