---
op: dither
dim: gfx2d
category: post
in: image2d
out: image2d
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# dither — GFX2D `post` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import gfx2d; gfx2d.dither(img, levels=2, method='ordered', matrix_size=4)` (または `opsgfx2d.get("dither")`)

## 使い方

Quantise to ``levels`` values per channel while preserving the local mean.

``method``:

* ``"ordered"`` — Bayer threshold matrix of side ``matrix_size`` (a power of
  two, 2..16). **The mean error has a closed-form bound**: for a uniform
  patch the output mean is within ``0.5 / (matrix_size**2 * (levels-1))`` of
  the input, because the fraction of thresholds crossed is the input
  fraction rounded to the nearest ``1/matrix_size**2``. At the defaults
  (4, 2 levels) the bound is 0.03125; the suite checks it holds for 101 grey
  levels x 3 matrix sizes, with zero violations.
* ``"floyd_steinberg"`` — error diffusion with the 7/3/5/1 sixteenths of
  Floyd & Steinberg 1976, serial and directional.

Which method preserves the mean better depends on the image, and this
docstring will not pretend otherwise. Measured on a 128-step horizontal
ramp: ordered is **exact** (0.0) at 2, 3 and 4 levels and drifts to 1.1e-3
at 8 levels, while Floyd-Steinberg is 7.3e-4 at 2 levels and improves to
4.1e-5 at 16. Ordered wins where the level lattice divides the ramp, error
diffusion wins where it does not.

Accepts ``(H, W)`` or ``(H, W, 3|4)``; an alpha channel is quantised too,
because a dithered sprite with a smooth alpha is exactly the case that
motivates this.

Output values lie on the lattice ``k / (levels - 1)``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[shadow_cast_2d](../light/shadow_cast_2d.md)

## 同カテゴリ(`post`)

[bloom](bloom.md) · [vignette](vignette.md) · [chromatic_aberration](chromatic_aberration.md) · [film_grain](film_grain.md) · [color_lut](color_lut.md) · [color_grade](color_grade.md) · [palette_quantize](palette_quantize.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
