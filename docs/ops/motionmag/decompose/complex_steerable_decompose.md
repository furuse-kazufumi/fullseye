---
op: complex_steerable_decompose
dim: motionmag
category: decompose
in: image2d
out: table
examples: [motion_magnification]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# complex_steerable_decompose — MOTIONMAG `decompose` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import motionmag; motionmag.complex_steerable_decompose(image, scales: 'int' = 4, orientations: 'int' = 4) -> 'dict'` (または `opsmotionmag.get("complex_steerable_decompose")`)

## 使い方

Complex oriented sub-band decomposition of one frame -> ``dict``.

Splits the image into ``scales * orientations`` **analytic** sub-bands plus
three residuals (low-pass, high-pass and a small symmetric completion band).
Each sub-band is a full-resolution ``(H, W)`` complex array whose modulus is
the local contrast of that scale/orientation and whose argument is the local
**phase** — the quantity a translation shifts linearly, which is what the
rest of this module is built on. There is no spatial decimation: keeping
every band at full resolution costs memory but makes the frame exactly
invertible, and exactness is the point.

Returns ``{"bands": [complex (H, W), ...], "kinds": [...],
"centre_cycles_per_px": [...], "orientation_rad": [...], "shape": (H, W),
"scales": s, "orientations": k}``. ``kinds[j]`` is ``"band"`` for an oriented
sub-band and ``"lowpass"`` / ``"highpass"`` / ``"residual"`` otherwise;
``centre_cycles_per_px`` and ``orientation_rad`` are ``None`` for residuals,
which have no orientation and no single centre frequency.

Feed the whole dict back to :func:`complex_steerable_reconstruct`. Round trip
error, measured on a 64x64 random frame with the defaults, is
``max|out - in| = 6.66e-16``; on a 31x37 (odd, non-square) frame 7.22e-16;
and the worst over every ``scales`` in 1..8 crossed with every
``orientations`` in 1..16 on 32x32 is 7.77e-16 — the tight-frame construction
is exact, not approximate (see the notes on the self-conjugate grid points
in :func:`_filter_bank`).

References: Freeman & Adelson, IEEE PAMI 1991; Simoncelli & Freeman,
ICIP 1995; Portilla & Simoncelli, IJCV 2000.

## 詳しい使い方ガイド

- [motion_magnification ファミリ ガイド](../guides/motion_magnification.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_magnification](../../../../examples/motion_magnification.py) — `py -3.11 examples/motion_magnification.py`

## 型が繋がる次の op(`table` を入力に取れる)

[complex_steerable_reconstruct](complex_steerable_reconstruct.md)

## 同カテゴリ(`decompose`)

[complex_steerable_reconstruct](complex_steerable_reconstruct.md)

---
*Provenance: motionmag.py — MOTIONMAG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
