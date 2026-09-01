---
op: lf_from_mla
dim: lightfield
category: decode
in: image2d
out: lightfield
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_from_mla — LIGHTFIELD `decode` op

- **データ種**: `image2d` → `lightfield`
- **呼び出し**: `import lightfield; lightfield.lf_from_mla(raw, angular=(5, 5), *, offset=(0, 0), crop=False)` (または `opslightfield.get("lf_from_mla")`)

## 使い方

Decode a microlens-array raw frame into a ``(V, U, H, W)`` light field.

The plenoptic sensor stores, for microlens ``(t, s)``, a ``V x U`` block of
pixels — one per direction through the main lens' exit pupil. So raw pixel
``(offset_y + t*V + v, offset_x + s*U + u)`` is exactly ``L[v, u, t, s]``:
the decode is a pure re-sort, no interpolation, no data invented.
:func:`lf_to_mla` inverts it **bit-exactly**.

*offset* is the integer position of the first whole microlens; a real MLA is
never aligned to pixel ``(0, 0)``. Sub-pixel MLA calibration is out of scope
(see the module docstring) — this operator works on an already-rectified
frame.

By default a raw frame whose usable size is not a whole multiple of the
microlens pitch is a ``ValueError``, because the alternative — quietly
dropping the last partial row of microlenses — shifts every subsequent
microlens centre and produces a light field that looks right and is wrong.
Pass ``crop=True`` to opt in to that crop explicitly.

**Raises** ``ValueError``: *raw* not 2-D or non-finite, *angular* outside
``[1, MAX_ANGULAR]``, a negative *offset*, an *offset* that leaves fewer
than one whole microlens, a size that is not a multiple of the pitch (unless
``crop=True``), a decoded sub-aperture image over :data:`MAX_SPATIAL` on a
side, and a decoded size over :data:`MAX_LF_ELEMENTS`.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`lightfield` を入力に取れる)

[lf_to_mla](lf_to_mla.md) · [lf_stats](lf_stats.md) · [lf_subaperture](../views/lf_subaperture.md) · [lf_center_view](../views/lf_center_view.md) · [lf_views](../views/lf_views.md) · [lf_epi](../views/lf_epi.md) · [lf_refocus](../refocus/lf_refocus.md) · [lf_focal_stack](../refocus/lf_focal_stack.md)

## 同カテゴリ(`decode`)

[lf_to_mla](lf_to_mla.md) · [lf_stats](lf_stats.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
