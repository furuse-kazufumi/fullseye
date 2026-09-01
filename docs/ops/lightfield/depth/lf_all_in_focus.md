---
op: lf_all_in_focus
dim: lightfield
category: depth
in: lightfield × image2d
out: image2d
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_all_in_focus — LIGHTFIELD `depth` op

- **データ種**: `lightfield × image2d` → `image2d`
- **呼び出し**: `import lightfield; lightfield.lf_all_in_focus(lf, slope_map, levels=None, *, n_levels=16, interp='linear', edge='nearest')` (または `opslightfield.get("lf_all_in_focus")`)

## 使い方

Composite one everywhere-sharp image by refocusing each pixel at its own slope.

Builds a focal stack at *levels* and, for every pixel, takes the slice whose
level is closest to ``slope_map`` there. This is the "2-D image" half of what
a plenoptic camera delivers, at the full depth range rather than the depth of
field of one focus setting.

*levels* controls which refocus planes are actually rendered, and the
``None`` default has two documented branches — a continuous slope map has
one distinct value per pixel, and rendering a refocus plane for each of
those would be tens of thousands of full-frame shifts:

  * if *slope_map* holds at most *n_levels* distinct values (the case when
    it came from :func:`lf_depth_from_focus` with ``subpixel=False``), those
    exact values are used and the composite is exact;
  * otherwise the map's range is quantised to *n_levels* evenly spaced
    planes (default 16), which is a real approximation: a pixel whose true
    slope falls between two planes is refocused at the nearer one. Pass
    *levels* explicitly — e.g. the sweep you handed
    :func:`lf_depth_from_focus` — when that matters.

Returns a ``(H, W)`` 2-D image.

**Raises** ``ValueError``: *lf* not a valid light field, a *slope_map* that
is not 2-D / not ``(H, W)`` / non-finite, *levels* empty or over the stack
caps, *n_levels* outside ``[1, MAX_STACK_SLICES]``, unknown *interp* /
*edge*.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[lf_from_mla](../decode/lf_from_mla.md) · [lf_disparity_to_depth](lf_disparity_to_depth.md)

## 同カテゴリ(`depth`)

[lf_depth_from_focus](lf_depth_from_focus.md) · [lf_epi_slope](lf_epi_slope.md) · [lf_disparity_to_depth](lf_disparity_to_depth.md) · [lf_plenoptic_design](lf_plenoptic_design.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
