---
op: phase_correlation_shift
dim: fit
category: registration
in: image2d × image2d
out: table
examples: [fit_ops_from_knowhow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# phase_correlation_shift — FIT `registration` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.phase_correlation_shift(image1, image2, window: 'str | None' = 'hann', whitening: 'float' = 0.5, method: 'str' = 'parabolic') -> 'dict'` (実装を直接呼ぶなら `import filters_freq; filters_freq.phase_correlation_shift(image1, image2, window: 'str | None' = 'hann', whitening: 'float' = 0.5, method: 'str' = 'parabolic') -> 'dict'`、台帳から引くなら `opsfit.get("phase_correlation_shift")`)

## 使い方

2 枚の画像の位置合わせに必要なサブピクセル移動量を位相限定相関で求める。

The default ``method="parabolic"`` reuses the whitening-aware periodic
correlation surface from :func:`phase_correlation_fft` and refines its
integer peak independently along each axis with the wrapped three-point
parabola. ``method="upsample"`` instead uses scikit-image's 100x local
upsampled DFT and fails closed with ``MissingDependencyError`` when that
optional dependency is absent. On the fixed 96x112 truth gates, parabolic
errors are 0.166 px (Hann) / 0.172 px (no window), versus 0.010 px for
upsample with either window; the parabolic result is biased 0.166 / 0.171
px toward the integer grid. The sign convention is explicit: when
``image2 = shift(image1, d)``, the result is approximately ``-d``, so
``shift(image2, result)`` approximately equals ``image1``.
Returns ``row_shift``/``col_shift`` (also ``dy``/``dx``), ``peak`` and
``peak_ratio`` (largest peak divided by the best peak outside its 3x3
neighbourhood). Constant or relatively textureless inputs raise ``ValueError``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fit_ops_from_knowhow](../../../../examples/fit_ops_from_knowhow.py) — `py -3.11 examples/fit_ops_from_knowhow.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`registration`)

—

---
*Provenance: filters_freq.py — FIT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
