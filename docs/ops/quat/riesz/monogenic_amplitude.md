---
op: monogenic_amplitude
dim: quat
category: riesz
in: qimage
out: image2d
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# monogenic_amplitude — QUAT `riesz` op

- **データ種**: `qimage` → `image2d`
- **呼び出し**: `import quatimage; quatimage.monogenic_amplitude(qimage) -> 'np.ndarray'` (または `opsquat.get("monogenic_amplitude")`)

## 使い方

Local amplitude ``sqrt(f^2 + R1^2 + R2^2)`` of a monogenic signal. → (H, W).

The local contrast at the signal's scale, and the confidence map for
:func:`monogenic_phase` / :func:`monogenic_orientation`, which mean nothing
where this is at the rounding floor. **Raw / unnormalised** (a contrast is a
metric quantity), in the same spirit as ``complexops.cx_magnitude``.

For a unit-contrast grating at the band centre it is exactly 1.0 (measured
spread 8.9e-16 over a 64x64 frame) and, unlike a squared oriented-filter
response, it is *isotropic*: rotating the grating does not change it.
Measured over eight grid-exact orientations the amplitude spans
``[0.99999999999999911, 1.0000000000000011]`` — a total spread of 2.0e-15
across all of them, which is the isotropy claim as a number.

**Raises** ``ValueError``: the input is not a valid quaternion field, or its
``k`` component is non-zero (see :func:`_require_monogenic`).

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[riesz_transform](riesz_transform.md) · [monogenic_signal](monogenic_signal.md)

## 同カテゴリ(`riesz`)

[riesz_transform](riesz_transform.md) · [monogenic_signal](monogenic_signal.md) · [monogenic_phase](monogenic_phase.md) · [monogenic_orientation](monogenic_orientation.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
