---
op: complex_steerable_reconstruct
dim: motionmag
category: decompose
in: table
out: image2d
examples: [motion_magnification]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# complex_steerable_reconstruct — MOTIONMAG `decompose` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import motionmag; motionmag.complex_steerable_reconstruct(decomposition) -> 'np.ndarray'` (または `opsmotionmag.get("complex_steerable_reconstruct")`)

## 使い方

Invert :func:`complex_steerable_decompose` -> ``(H, W)`` real image.

Exact: the analysis bank is a tight frame after the divisor correction, so
the round trip is the identity up to floating-point rounding (measured
``6.66e-16`` maximum absolute error on a 64x64 random frame with the default
4 scales x 4 orientations). Editing a band before calling this — scaling its
phase, zeroing it — is how every other operator in this module works.

Refuses a dict whose bands do not match the declared shape or count, because
a partially edited decomposition would otherwise reconstruct something
plausible from the wrong frame size.

## 詳しい使い方ガイド

- [motion_magnification ファミリ ガイド](../guides/motion_magnification.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_magnification](../../../../examples/motion_magnification.py) — `py -3.11 examples/motion_magnification.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[complex_steerable_decompose](complex_steerable_decompose.md)

## 同カテゴリ(`decompose`)

[complex_steerable_decompose](complex_steerable_decompose.md)

---
*Provenance: motionmag.py — MOTIONMAG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
