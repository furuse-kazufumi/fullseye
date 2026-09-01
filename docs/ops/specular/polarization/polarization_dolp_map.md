---
op: polarization_dolp_map
dim: specular
category: polarization
in: polsweep
out: image2d
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# polarization_dolp_map — SPECULAR `polarization` op

- **データ種**: `polsweep` → `image2d`
- **呼び出し**: `import specularity; specularity.polarization_dolp_map(images, angles_deg=(0.0, 45.0, 90.0, 135.0), max_violation_frac=0.0)` (または `opsspecular.get("polarization_dolp_map")`)

## 使い方

Degree of linear polarisation, per pixel. → (H, W) in [0, 1].

``sqrt(S1^2 + S2^2) / S0``, from the same sinusoid fit as
:func:`polarization_separate`. It answers the question that decides whether
a polariser is worth mounting at all: **1** means the light at that pixel is
fully linearly polarised and a crossed analyser extinguishes it completely,
**0** means the polariser will only cost you a stop of exposure.

Being a ratio, it is invariant to exposure: scaling every frame by 1e-4,
1e4 or 1e8 moves it by at most 3.9e-16 (measured), which is what makes it
comparable across a production line where the lamps age. Not *bit*-
identical — the least-squares fit rounds differently at a different scale —
and the difference between "invariant" and "bit-identical" is the kind of
claim this library measures rather than asserts.

Pixels with zero total radiance have no degree of polarisation (every ratio
would be 0/0) and are returned as 0.0 rather than as NaN; that is a
convention, and it is stated here because a NaN spreading into a
thresholding routine is exactly the silent failure this library refuses.

**Raises** ``ValueError``: as :func:`polarization_separate`.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[polarization_render](polarization_render.md)

## 同カテゴリ(`polarization`)

[polarization_render](polarization_render.md) · [polarization_separate](polarization_separate.md) · [polarization_stokes](polarization_stokes.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
