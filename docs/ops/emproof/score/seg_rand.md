---
op: seg_rand
dim: emproof
category: score
in: labels2d × labels2d
out: table
examples: [poc_em_split_merge_score]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# seg_rand — EMPROOF `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_rand(a, b, ignore_label=None)` (実装を直接呼ぶなら `import segcompare; segcompare.seg_rand(a, b, ignore_label=None)`、台帳から引くなら `opsemproof.get("seg_rand")`)

## 使い方

Rand index, adjusted Rand index and the adapted Rand error (CREMI / SNEMI).

With ``n_ij`` the contingency table, ``a_i`` / ``b_j`` its row and column sums and ``N``
the pixel count:

  * ``rand_index`` = fraction of pixel pairs on which the two agree (same/different);
  * ``adjusted_rand_index`` = Hubert & Arabie's chance-corrected version (1 = identical,
    about 0 = independent);
  * ``adapted_rand_error`` = 1 - F over **pairs of distinct pixels**: pair ``precision`` =
    (sum n_ij^2 - N) / (sum b_j^2 - N) — of the pairs the candidate puts together, the
    fraction the truth also puts together — and ``recall`` = (sum n_ij^2 - N) /
    (sum a_i^2 - N) (Arganda-Carreras et al. 2015). The ``- N`` removes each pixel's pair
    with itself. scikit-image's ``adapted_rand_error`` returns the same error, but its
    ``precision`` is divided by the **truth** pairs (its code sums the rows of the
    truth-by-test table), i.e. it is this ``recall``; its docstring says otherwise.

**Raises** ``ValueError``: as :func:`seg_contingency`; fewer than 2 counted pixels.

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_split_merge_score](../../../../examples/poc_em_split_merge_score.py) — `py -3.11 examples/poc_em_split_merge_score.py`

## 型が繋がる次の op(`table` を入力に取れる)

[seg_synapse_partners](../wiring/seg_synapse_partners.md) · [seg_wiring_variation](../wiring/seg_wiring_variation.md) · [seg_synapse_nri](../wiring/seg_synapse_nri.md) · [seg_wiring_exposure](../wiring/seg_wiring_exposure.md)

## 同カテゴリ(`score`)

[seg_contingency](seg_contingency.md) · [seg_variation_of_information](seg_variation_of_information.md)

---
*Provenance: segcompare.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
