---
op: riesz_transform
dim: quat
category: riesz
in: image2d
out: qimage
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# riesz_transform — QUAT `riesz` op

- **データ種**: `image2d` → `qimage`
- **呼び出し**: `import quatimage; quatimage.riesz_transform(image) -> 'np.ndarray'` (または `opsquat.get("riesz_transform")`)

## 使い方

The 2-D Riesz transform of an image, as a pure quaternion field. → (H, W, 4).

The isotropic generalisation of the Hilbert transform: a *pair* of filters
with frequency responses ``-i*u/|w|`` and ``-i*v/|w|``, returned as the
quaternion ``(0, R1 f, R2 f, 0)``. It is the 2-D object that has no complex
analogue — the 1-D analytic signal needs a direction to say which way "90
degrees later" is, and in 2-D there is no single direction, so the answer
needs two components and therefore an algebra with room for them.

Closed form, which is how this is tested rather than eyeballed
-------------------------------------------------------------
For a grating ``cos(2*pi*(u0*x + v0*y))`` sampled on the DFT grid,

    ``R1 = (u0/|w0|) * sin(2*pi*(u0*x + v0*y))``,
    ``R2 = (v0/|w0|) * sin(...)``

exactly. Measured over a table of eight grid-exact orientations from 0 to
159.4 degrees on a 64x64 frame, the largest absolute deviation from that
closed form is **6.1e-15**, and the orientation recovered through
:func:`monogenic_orientation` matches the grating's to **3.6e-15 rad** at
every one of them. There is no tolerance to choose.

Note the scalar component is 0, so this is the Riesz *transform* and not the
monogenic signal — feeding it to :func:`monogenic_phase` gives ``pi/2``
everywhere, correctly but uselessly. Use :func:`monogenic_signal`, which
keeps the band-pass image in the scalar slot.

**Raises** ``ValueError``: *image* is not a finite real ``(H, W)`` array with
``H, W >= 2``, or exceeds :data:`MAX_PIXELS`.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`qimage` を入力に取れる)

[quaternion_to_rgb](../convert/quaternion_to_rgb.md) · [quat_norm](../convert/quat_norm.md) · [quat_conjugate_image](../algebra/quat_conjugate_image.md) · [quat_normalize_image](../algebra/quat_normalize_image.md) · [quat_image_multiply](../algebra/quat_image_multiply.md) · [monogenic_amplitude](monogenic_amplitude.md) · [monogenic_phase](monogenic_phase.md) · [monogenic_orientation](monogenic_orientation.md)

## 同カテゴリ(`riesz`)

[monogenic_signal](monogenic_signal.md) · [monogenic_amplitude](monogenic_amplitude.md) · [monogenic_phase](monogenic_phase.md) · [monogenic_orientation](monogenic_orientation.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
