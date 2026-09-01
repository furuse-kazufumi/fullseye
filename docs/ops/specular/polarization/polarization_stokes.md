---
op: polarization_stokes
dim: specular
category: polarization
in: polsweep
out: stokes
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# polarization_stokes — SPECULAR `polarization` op

- **データ種**: `polsweep` → `stokes`
- **呼び出し**: `import specularity; specularity.polarization_stokes(images, angles_deg=(0.0, 45.0, 90.0, 135.0), max_violation_frac=0.0)` (または `opsspecular.get("polarization_stokes")`)

## 使い方

The scene-integrated Stokes vector of a polariser sweep. → (4,), ready for :func:`optics.stokes_analyze`.

Stokes parameters are linear in radiance, so the spatial mean of the frames
has a Stokes vector that is the mean of the per-pixel ones — the vector a
non-imaging polarimeter looking at the whole field would report. Fitting
``I(t) = 0.5 (S0 + S1 cos 2t + S2 sin 2t)`` gives ``(S0, S1, S2)`` directly.

**S3 is always exactly 0, and that is a limitation, not a measurement.** A
set of linear analysers cannot see circular polarisation; a quarter-wave
plate is needed. The returned vector is therefore the linear part of the
truth, and :func:`optics.stokes_analyze` will report ``handedness="linear"``
for it no matter what the scene actually did. Returning an invented ``S3``
would be worse, and returning a 3-vector would break the Stokes contract the
optics family is built on.

The result satisfies that contract by construction — ``S0 >= sqrt(S1^2 +
S2^2 + S3^2)``, i.e. degree of polarisation at most 1 — because the same
non-negativity check that guards :func:`polarization_separate` is exactly
the condition for it. That is why ``optics.stokes_analyze`` accepts the
output without a further test.

**Raises** ``ValueError``: as :func:`polarization_separate`.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`stokes` を入力に取れる)

—

## 同カテゴリ(`polarization`)

[polarization_render](polarization_render.md) · [polarization_separate](polarization_separate.md) · [polarization_dolp_map](polarization_dolp_map.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
