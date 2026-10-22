---
op: patchbank_fit
dim: spc
category: anomaly_patch
in: video
out: table
examples: [poc_patch_anomaly]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# patchbank_fit — SPC `anomaly_patch` op

- **データ種**: `video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.patchbank_fit(stack, patch=8, stride=4, scales=(1.0, 2.0, 4.0), groups=('gradient', 'gabor', 'lbp'), n_orient=4, coreset=0.1, proj_dim=32, position_weight=0.0, seed=0)` (実装を直接呼ぶなら `import anomaly_patch; anomaly_patch.patchbank_fit(stack, patch=8, stride=4, scales=(1.0, 2.0, 4.0), groups=('gradient', 'gabor', 'lbp'), n_orient=4, coreset=0.1, proj_dim=32, position_weight=0.0, seed=0)`、台帳から引くなら `opsspc.get("patchbank_fit")`)

## 使い方

Build a memory bank of good patch features, thinned by greedy k-centre covering (``table``).

``stack`` is (n, H, W) or (n, H, W, 3) of good images (n >= 1). Features are standardised
with the mean and the standard deviation of each dimension over all good patches. With
``position_weight`` > 0 the grid position (0..1 in each direction) times ``position_weight *
sqrt(D)`` is appended, so a patch is compared with good patches from nearby positions
(0 = position-free). ``coreset`` in (0, 1] is the fraction of patches kept: the greedy
k-centre cover picks, from a seeded start, always the patch farthest from the ones already
kept, measuring distances in a seeded random projection to ``proj_dim`` dimensions (None =
exact). The covering radius in that space after the selection is returned: the largest
distance from any good patch to the bank. ``coreset=1`` keeps everything (radius 0, no
selection, so ``seed`` and ``proj_dim`` have no effect).

Returns the model: ``bank`` (m, D'), ``mean`` / ``std`` (D), ``n_total`` patches, ``n_memory``,
``fraction``, ``covering_radius``, the feature parameters and ``image_shape``.

Raises ``ValueError`` for invalid parameters, a feature that is constant over all good patches,
or a stack that would exceed the memory guard.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_patch_anomaly](../../../../examples/poc_patch_anomaly.py) — `py -3.11 examples/poc_patch_anomaly.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`anomaly_patch`)

[patch_features](patch_features.md) · [patchdist_fit](patchdist_fit.md) · [patchdist_score](patchdist_score.md) · [patchbank_score](patchbank_score.md)

---
*Provenance: anomaly_patch.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
