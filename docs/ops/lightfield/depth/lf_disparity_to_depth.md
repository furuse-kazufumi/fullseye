---
op: lf_disparity_to_depth
dim: lightfield
category: depth
in: image2d
out: depth
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_disparity_to_depth — LIGHTFIELD `depth` op

- **データ種**: `image2d` → `depth`
- **呼び出し**: `import lightfield; lightfield.lf_disparity_to_depth(slope, focal_px=1000.0, baseline=1.0, *, far_depth=None, min_slope=1e-06)` (または `opslightfield.get("lf_disparity_to_depth")`)

## 使い方

Slope (px per angular step) -> metric depth, the camera-array model.

For a rectified array of viewpoints spaced *baseline* apart with focal
length *focal_px* expressed **in pixels of the sub-aperture image**, a point
at distance ``Z`` shifts by ``|s| = focal_px * baseline / Z`` pixels per
step. Inverting: ``Z = focal_px * baseline / |s|``, returned in whatever
length unit *baseline* was given in (mm in, mm out).

Only ``|s|`` enters, deliberately. The *sign* of the slope says which side of
the focal plane a point is on, and which sign means "nearer" depends on how
the angular axis was oriented when the field was decoded — a convention this
module cannot know and refuses to guess. If your decode puts near objects at
negative slope, negate before calling.

*far_depth* is the fail-closed switch for the ``s -> 0`` pole (a point at
infinity has zero parallax). ``None`` (default) makes any ``|s| < min_slope``
a ``ValueError`` naming how many pixels were affected — mask them, or pass an
explicit saturation distance as *far_depth* and get that value there. There
is no silent ``inf`` and no silent clamp.

Accepts a scalar or any array; returns the same shape (a scalar in gives a
0-d array out, so downstream code has one type to handle).

**Raises** ``ValueError``: non-finite *slope* / *focal_px* / *baseline*, a
non-positive *focal_px* / *baseline* / *min_slope*, a negative *far_depth*,
and ``|slope| < min_slope`` anywhere when *far_depth* is ``None``.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`depth` を入力に取れる)

—

## 同カテゴリ(`depth`)

[lf_depth_from_focus](lf_depth_from_focus.md) · [lf_epi_slope](lf_epi_slope.md) · [lf_all_in_focus](lf_all_in_focus.md) · [lf_plenoptic_design](lf_plenoptic_design.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
