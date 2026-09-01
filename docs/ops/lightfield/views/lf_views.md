---
op: lf_views
dim: lightfield
category: views
in: lightfield
out: images
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_views — LIGHTFIELD `views` op

- **データ種**: `lightfield` → `images`
- **呼び出し**: `import lightfield; lightfield.lf_views(lf)` (または `opslightfield.get("lf_views")`)

## 使い方

The whole angular grid as a plain list of 2-D images (row-major over ``(v, u)``).

The bridge to the rest of fullseye: the returned ``list`` of ``V*U``
``(H, W)`` arrays is the ``images`` type, so multi-image operators
(registration, fusion, statistics, :mod:`focus_stack`'s machinery) consume a
light field with no adapter. Ordering is ``v`` outer, ``u`` inner, i.e.
``views[v*U + u] == lf[v, u]``; each entry is a copy, so mutating one does
not corrupt the field.

**Raises** ``ValueError``: *lf* is not a valid light field.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`images` を入力に取れる)

—

## 同カテゴリ(`views`)

[lf_subaperture](lf_subaperture.md) · [lf_center_view](lf_center_view.md) · [lf_epi](lf_epi.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
