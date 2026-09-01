---
op: lf_to_mla
dim: lightfield
category: decode
in: lightfield
out: image2d
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_to_mla — LIGHTFIELD `decode` op

- **データ種**: `lightfield` → `image2d`
- **呼び出し**: `import lightfield; lightfield.lf_to_mla(lf)` (または `opslightfield.get("lf_to_mla")`)

## 使い方

Re-interleave a light field into a microlens-array raw frame (exact inverse).

Inverse of :func:`lf_from_mla` with ``offset=(0, 0)``: the returned frame has
shape ``(H*V, W*U)`` and puts ``L[v, u, t, s]`` back at raw pixel
``(t*V + v, s*U + u)``. ``lf_from_mla(lf_to_mla(L), (V, U))`` returns ``L``
bit-for-bit (verified with ``np.array_equal``), which is the cheapest
possible check that the decode's index arithmetic has no off-by-one.

**Raises** ``ValueError``: *lf* not 4-D / non-finite / over the shape and
element caps (see :func:`lf_from_mla`), and a raw frame whose side would
exceed ``MAX_SPATIAL * MAX_ANGULAR``.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[lf_from_mla](lf_from_mla.md) · [lf_disparity_to_depth](../depth/lf_disparity_to_depth.md) · [lf_all_in_focus](../depth/lf_all_in_focus.md)

## 同カテゴリ(`decode`)

[lf_from_mla](lf_from_mla.md) · [lf_stats](lf_stats.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
