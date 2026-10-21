---
op: feat_image_vector
dim: multivar
category: features
in: images
out: table
examples: [multivar_inspection_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# feat_image_vector — MULTIVAR `features` op

- **データ種**: `images` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.feat_image_vector(images=None, features=('mean', 'std', 'p01', 'p99', 'rms_contrast', 'michelson_contrast', 'grad_energy', 'laplacian_var'), data_range=None, unit='DN', roi=None) -> 'dict'` (実装を直接呼ぶなら `import multivar; multivar.feat_image_vector(images=None, features=('mean', 'std', 'p01', 'p99', 'rms_contrast', 'michelson_contrast', 'grad_energy', 'laplacian_var'), data_range=None, unit='DN', roi=None) -> 'dict'`、台帳から引くなら `opsmultivar.get("feat_image_vector")`)

## 使い方

Images -> feature table ``{"matrix" (N, F), "names", "units", ...}``, one row per image.

The bridge from pictures to the multivariate ops: each image becomes a row of named
numbers with units, ready for :func:`mv_pca` / :func:`mv_pls` / :func:`rsm_fit`.
Features (see :data:`FEATURES`): ``mean, std, p01, p50, p99, rms_contrast,
michelson_contrast, grad_energy, laplacian_var`` need no range;
``saturated_fraction, dark_fraction, entropy_bits`` need ``data_range=(lo, hi)`` —
the range of the *sensor or format* (e.g. (0, 4095) for 12-bit), which the data
cannot tell: the brightest pixel of a dim image is not the white level. It is
therefore **required, never inferred**, and pixels outside it are refused (the
range given is then wrong).

``unit`` names the grey-level unit (``"DN"`` by default) used in the unit strings.
``roi=(r0, r1, c0, c1)`` restricts every feature to that window (same for all images).

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [multivar_inspection_tour](../../../../examples/multivar_inspection_tour.py) — `py -3.11 examples/multivar_inspection_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`features`)

—

---
*Provenance: multivar.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
