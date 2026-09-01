---
op: lf_center_view
dim: lightfield
category: views
in: lightfield
out: image2d
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_center_view — LIGHTFIELD `views` op

- **データ種**: `lightfield` → `image2d`
- **呼び出し**: `import lightfield; lightfield.lf_center_view(lf, mode='average')` (または `opslightfield.get("lf_center_view")`)

## 使い方

The centre viewpoint — the ordinary 2-D image a plenoptic camera also gives.

For odd ``V`` and ``U`` the centre is a single view and both modes return it
exactly. For an **even** axis the centre falls *between* two views, and this
operator does not pretend otherwise:

  * ``mode="average"`` (default) returns the mean of the 2 (or 4) views
    straddling the centre — the correctly-centred estimate for a Lambertian
    scene, at the cost of a slight blur proportional to the disparity.
  * ``mode="nearest"`` returns the single view at ``floor((N-1)/2)``, which
    is sharp but sits half an angular step off centre; every disparity
    measured against it carries that half-step bias.

Returns a ``(H, W)`` 2-D image.

**Raises** ``ValueError``: *lf* not a valid light field, unknown *mode*.

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

[lf_subaperture](lf_subaperture.md) · [lf_views](lf_views.md) · [lf_epi](lf_epi.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
