---
op: lf_epi
dim: lightfield
category: views
in: lightfield
out: image2d
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_epi — LIGHTFIELD `views` op

- **データ種**: `lightfield` → `image2d`
- **呼び出し**: `import lightfield; lightfield.lf_epi(lf, axis='u', index=0, view=None)` (または `opslightfield.get("lf_epi")`)

## 使い方

Epipolar-plane image — the slice whose **line slope is the disparity**.

An EPI is what makes a light field different from a pile of photographs: fix
one image row and one angular row, and every scene point traces a *straight
line* whose gradient ``dx/du`` is exactly its slope ``s``. Occlusion becomes
one line crossing in front of another, which is why EPI methods handle it
better than window matching.

  * ``axis="u"`` (horizontal): fix ``v = view`` (default: the centre row,
    ``(V-1)//2``) and image row ``y = index``; returns ``E[u, x]`` of shape
    ``(U, W)``.
  * ``axis="v"`` (vertical): fix ``u = view`` and image column ``x = index``;
    returns ``E[v, y]`` of shape ``(V, H)``.

**Raises** ``ValueError``: *lf* not a valid light field, unknown *axis*,
*index* outside the spatial extent, *view* outside the angular extent.

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

## 同カテゴリ(`views`)

[lf_subaperture](lf_subaperture.md) · [lf_center_view](lf_center_view.md) · [lf_views](lf_views.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
