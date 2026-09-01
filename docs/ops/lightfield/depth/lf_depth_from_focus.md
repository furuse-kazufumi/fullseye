---
op: lf_depth_from_focus
dim: lightfield
category: depth
in: lightfield
out: image2d
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_depth_from_focus — LIGHTFIELD `depth` op

- **データ種**: `lightfield` → `image2d`
- **呼び出し**: `import lightfield; lightfield.lf_depth_from_focus(lf, slopes=(-2.0, -1.0, 0.0, 1.0, 2.0), *, window=9, measure='laplacian', subpixel=True, interp='linear', edge='nearest')` (または `opslightfield.get("lf_depth_from_focus")`)

## 使い方

Per-pixel slope from the **sharpness peak** across the refocus sweep.

Refocus at every slope in *slopes*, measure local sharpness (*measure*:
``laplacian`` = summed modified Laplacian, the classical depth-from-focus
operator; ``variance`` = local variance; ``gradient`` = local gradient
energy) in a ``window x window`` neighbourhood, and take the slope at which
each pixel is sharpest. With ``subpixel=True`` (default) the peak is refined
by fitting a parabola through the winning sample and its two neighbours on a
**uniformly** spaced sweep — on a non-uniform sweep the refinement is
skipped rather than applied with the wrong spacing.

Unbiased where :func:`lf_epi_slope` is not: measured 2026-09-01 on a
5x5x64x64 synthetic field over a 121-point sweep from -3 to +3, the argmax
landed **exactly** on the true slope in 18 of 18 combinations (true slopes
0.0, +0.5, +1.0, +1.5, +2.0, -1.0 crossed with texture sigma 1.5 / 3.0 /
5.0 px), and the sub-pixel refinement left every one of them unmoved. Its
resolution, though, is whatever you put in *slopes* — it cannot see a plane
you never refocused on.

Returns ``(slope_map, sharpness)``: the ``(H, W)`` map of estimated slopes
(in px per angular step) and the ``(H, W)`` peak focus-measure value, which
is the honest confidence — a textureless pixel has no sharpness peak, gets
an essentially arbitrary slope, and its ``sharpness`` is ~0. Threshold on it
rather than trusting the map everywhere.

**Raises** ``ValueError``: *lf* not a valid light field, *slopes* empty /
over :data:`MAX_STACK_SLICES` / over :data:`MAX_STACK_ELEMENTS` / containing
a non-finite or over-large value, an even or non-positive *window*, unknown
*measure* / *interp* / *edge*.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[lf_from_mla](../decode/lf_from_mla.md) · [lf_disparity_to_depth](lf_disparity_to_depth.md) · [lf_all_in_focus](lf_all_in_focus.md)

## 同カテゴリ(`depth`)

[lf_epi_slope](lf_epi_slope.md) · [lf_disparity_to_depth](lf_disparity_to_depth.md) · [lf_all_in_focus](lf_all_in_focus.md) · [lf_plenoptic_design](lf_plenoptic_design.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
