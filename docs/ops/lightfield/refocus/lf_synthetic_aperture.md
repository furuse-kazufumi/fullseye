---
op: lf_synthetic_aperture
dim: lightfield
category: refocus
in: lightfield
out: image2d
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_synthetic_aperture — LIGHTFIELD `refocus` op

- **データ種**: `lightfield` → `image2d`
- **呼び出し**: `import lightfield; lightfield.lf_synthetic_aperture(lf, slope=0.0, mask=None, *, reduce='mean', interp='linear', edge='nearest')` (または `opslightfield.get("lf_synthetic_aperture")`)

## 使い方

Refocus through a shaped aperture — and, with ``reduce="median"``, through occluders.

Same shift-and-add geometry as :func:`lf_refocus`, with two additions:

  * *mask* — a ``(V, U)`` weight array from :func:`lf_aperture_mask` (or your
    own). A small mask is a stopped-down aperture: less defocus blur, less
    light. ``None`` weights every view equally.
  * *reduce* — how the aligned views are combined. ``mean`` is the classical
    (and linear) synthetic aperture. ``median`` is the interesting one: when
    a foreground occluder covers a *minority* of the views at a pixel, the
    median rejects it and the background behind it is reconstructed —
    looking through a fence, or through a rack of parts. ``max`` / ``min``
    are the order-statistic extremes, useful for specular / shadow work.
    ``median``, ``max`` and ``min`` use the mask only to *select* views
    (weight > 0), because an order statistic has no meaningful weighting;
    that is stated here rather than silently ignoring the weights.

The see-through result is not a metaphor. When **fewer than half** the views
are blocked at a hidden pixel, more than half of them carry the identical
background sample and the median is that sample **exactly**. Measured
2026-09-01 on a 9x9x64x64 field with an occluder covering 25% of the centre
view at slope 3.0 (blocking at most 46% of the views at any hidden pixel):
RMS against the true, hidden background was **0.0** for ``median`` and
0.159 for ``mean``, with the centre view itself at 0.280. Push the coverage
to 35% (up to 60% of views blocked) and the guarantee is gone — the median
lands at 0.133, worse than nothing.

Returns a ``(H, W)`` 2-D image.

**Raises** ``ValueError``: *lf* not a valid light field, a *mask* whose
shape is not ``(V, U)`` or which is non-finite / negative / selects no view,
a non-finite or over-large *slope*, unknown *reduce* / *interp* / *edge*.

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

[lf_refocus](lf_refocus.md) · [lf_focal_stack](lf_focal_stack.md) · [lf_aperture_mask](lf_aperture_mask.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
