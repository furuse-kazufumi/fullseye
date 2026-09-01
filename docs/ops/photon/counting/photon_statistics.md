---
op: photon_statistics
dim: photon
category: counting
in: image2d
out: table
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# photon_statistics — PHOTON `counting` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import photoncount; photoncount.photon_statistics(counts)` (または `opsphoton.get("photon_statistics")`)

## 使い方

Poisson statistics of a photon-count frame: is it really shot-noise limited?

Returns a dict: ``mean`` · ``variance`` (population, ``ddof=0``) ·
``fano_factor`` ``= variance / mean`` (**1 for a Poisson process**) ·
``snr_poisson`` ``= sqrt(mean)`` (the theoretical photon-limited SNR) ·
``snr_measured`` ``= mean / std`` (what this frame actually achieved) ·
``total_counts`` · ``n_samples`` · ``zero_fraction`` (the fraction of pixels
that saw no photon at all — the honest measure of "photon starved";
``exp(-lambda)`` for a flat field) · ``max_counts``.

**The Fano factor is evidence of Poisson statistics only on a flat field.**
On a structured scene the scene's own spatial variance dominates and the
ratio is large and meaningless — this op computes the number, it cannot tell
you which situation you are in. Measured on the test scenes: a flat
``lambda = 100`` field (512x512, seed 0) gives 1.001089; the same detector
looking at a linear ramp from 20 to 180 photons gives 22.4102. Both are
"correct" and only one of them means anything.

**Raises** ``ValueError``: negative, non-finite or non-2-D *counts*, fewer
than 2 pixels (no variance), an all-zero frame (``fano_factor`` would be
``0/0`` — say "no photons were detected" instead of returning NaN), and a
frame with exactly zero variance (``snr_measured`` would be ``inf``; for
``n >= 2`` a constant frame is not a Poisson realisation but a synthetic
constant, i.e. an input mistake).

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`counting`)

[photon_sample](photon_sample.md) · [photon_uncertainty](photon_uncertainty.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
