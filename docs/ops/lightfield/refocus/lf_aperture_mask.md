---
op: lf_aperture_mask
dim: lightfield
category: refocus
in: 
out: image2d
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_aperture_mask — LIGHTFIELD `refocus` op

- **データ種**: `` → `image2d`
- **呼び出し**: `import lightfield; lightfield.lf_aperture_mask(angular=(5, 5), shape='circle', *, radius=None, inner=0.0, sigma=None, normalize=True)` (または `opslightfield.get("lf_aperture_mask")`)

## 使い方

Angular weighting mask — the synthetic aperture you stop down or shape.

Returns a ``(V, U)`` 2-D array of per-view weights, indexed the same way as
the light field's angular axes, for :func:`lf_synthetic_aperture`. The
radius is measured in **angular steps** from the centre ``((V-1)/2,
(U-1)/2)``, so ``radius=0`` selects the single centre view (an infinitely
small aperture: everything in focus, no light) and the default
``radius = max(V-1, U-1)/2`` is the largest circle that fits.

  * ``circle``   — hard-edged disc, the physical iris.
  * ``square``   — Chebyshev disc; separable, the cheapest to reason about.
  * ``gaussian`` — apodised pupil (``sigma`` in angular steps, default
    ``radius/2``); no ringing in the defocus PSF.
  * ``annulus``  — ring between *inner* and *radius*; a coded aperture whose
    defocus PSF has more high-frequency content, which is what makes
    depth-from-defocus work better.

With ``normalize=True`` (default) the weights sum to exactly 1, so a masked
reduction is a weighted **mean** and its result is directly comparable with
:func:`lf_refocus`. Set it to ``False`` to keep 0/1 selection weights.

**Raises** ``ValueError``: an angular shape outside ``[1, MAX_ANGULAR]``, a
negative *radius* / *inner* / *sigma*, ``inner >= radius``, an unknown
*shape*, and — explicitly rather than returning a field of zeros — a mask
that selects **no** view at all (an opaque aperture), which would make every
downstream weighted mean a 0/0.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[lf_from_mla](../decode/lf_from_mla.md) · [lf_disparity_to_depth](../depth/lf_disparity_to_depth.md) · [lf_all_in_focus](../depth/lf_all_in_focus.md)

## 同カテゴリ(`refocus`)

[lf_refocus](lf_refocus.md) · [lf_focal_stack](lf_focal_stack.md) · [lf_synthetic_aperture](lf_synthetic_aperture.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
