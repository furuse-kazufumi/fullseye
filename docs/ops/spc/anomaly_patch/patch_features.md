---
op: patch_features
dim: spc
category: anomaly_patch
in: image2d
out: table
examples: [poc_patch_anomaly]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# patch_features — SPC `anomaly_patch` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.patch_features(image, patch=8, stride=4, scales=(1.0, 2.0, 4.0), groups=('gradient', 'gabor', 'lbp'), n_orient=4)` (実装を直接呼ぶなら `import anomaly_patch; anomaly_patch.patch_features(image, patch=8, stride=4, scales=(1.0, 2.0, 4.0), groups=('gradient', 'gabor', 'lbp'), n_orient=4)`、台帳から引くなら `opsspc.get("patch_features")`)

## 使い方

Classical patch features on a grid: one D-vector per patch (``table``).

``image`` is (H, W) or (H, W, 3). Pixel channels are computed at every Gaussian scale in
``scales`` (sigma, px) and averaged over ``patch`` x ``patch`` windows every ``stride`` px:
``intensity`` (smoothed mean), ``gradient`` (Gaussian-derivative magnitude and the
doubled-angle components |g|cos2t, |g|sin2t: the structure tensor), ``gabor`` (zero-mean
Gabor energy, wavelength 4 sigma, ``n_orient`` orientations), ``lbp`` (histogram of the 10
rotation-invariant uniform local binary patterns, radius = round(sigma)), ``color``
(red-green and yellow-blue opponents, needs a colour image). ``fourier`` is computed on the
raw patches, not per scale: the log share of a Hann-windowed patch's spectrum in three
radial bands. Returns ``features`` (gh, gw, D), ``names`` (D), ``grid`` (gh, gw), ``dim``
and the parameters.

Raises ``ValueError`` on an empty / non-finite / wrongly shaped image, an image smaller
than ``patch``, unknown groups, or ``color`` on a gray image.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_patch_anomaly](../../../../examples/poc_patch_anomaly.py) — `py -3.11 examples/poc_patch_anomaly.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`anomaly_patch`)

[patchdist_fit](patchdist_fit.md) · [patchdist_score](patchdist_score.md) · [patchbank_fit](patchbank_fit.md) · [patchbank_score](patchbank_score.md)

---
*Provenance: anomaly_patch.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
