---
op: lf_refocus
dim: lightfield
category: refocus
in: lightfield
out: image2d
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_refocus — LIGHTFIELD `refocus` op

- **データ種**: `lightfield` → `image2d`
- **呼び出し**: `import lightfield; lightfield.lf_refocus(lf, slope=0.0, *, interp='linear', edge='nearest')` (または `opslightfield.get("lf_refocus")`)

## 使い方

Shift-and-add refocus: the synthetic-aperture image focused at *slope*.

Every view ``(v, u)`` is shifted by ``(-s*(v - v_c), -s*(u - u_c))`` — the
**minus** undoes the parallax of a point at slope ``s`` — and the shifted
views are averaged. Points at that slope add coherently and stay sharp;
everything else is smeared by an amount proportional to its slope
difference times the angular baseline. ``slope=0`` is the plane the array
was already focused on and returns the plain average of the views.

Ground truth it reproduces exactly (pinned in ``tests/test_lightfield.py``):
a single-layer field synthesised at slope ``s0`` and refocused at ``s0``
with ``edge="wrap"`` and an integer ``s0`` returns the original texture to
5.6e-16; sweeping the slope, the variance of the result peaks at ``s0``
(measured exactly on the sweep grid in all 18 texture/slope combinations
listed in the module docstring), and refocusing at ``-s0`` does *not* —
which is the check that catches a flipped shift sign.

Returns a ``(H, W)`` 2-D image.

**Raises** ``ValueError``: *lf* not a valid light field, a non-finite or
over-large *slope* (:data:`MAX_ABS_SLOPE`), unknown *interp* / *edge*.

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

[lf_focal_stack](lf_focal_stack.md) · [lf_aperture_mask](lf_aperture_mask.md) · [lf_synthetic_aperture](lf_synthetic_aperture.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
