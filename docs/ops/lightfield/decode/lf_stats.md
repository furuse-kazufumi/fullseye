---
op: lf_stats
dim: lightfield
category: decode
in: lightfield
out: table
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_stats — LIGHTFIELD `decode` op

- **データ種**: `lightfield` → `table`
- **呼び出し**: `import lightfield; lightfield.lf_stats(lf)` (または `opslightfield.get("lf_stats")`)

## 使い方

Describe a light field: shape, angular centre, and the slope range it can carry.

Returns a dict — ``angular_v`` / ``angular_u`` · ``height`` / ``width`` ·
``n_views = V*U`` · ``center_v`` / ``center_u`` (``(N-1)/2``, a half-integer
when the axis is even, so ``center_is_a_view`` says whether a single view
actually sits at the centre) · ``min`` / ``max`` / ``mean`` of the samples ·
``max_slope_px``, the largest ``|s|`` for which the extreme view is still
displaced by less than half the frame, i.e. the honest limit of what this
array can measure (``min(H, W) / max(V-1, U-1, 1)``; reported as
``float(min(H, W))`` when the array has a single view in both directions,
since then no shift happens at all) · ``baseline_views``, the angular span
``(V-1, U-1)`` that any disparity is measured over.

**Raises** ``ValueError``: *lf* is not a finite 4-D array within the shape
and element caps.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`decode`)

[lf_from_mla](lf_from_mla.md) · [lf_to_mla](lf_to_mla.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
