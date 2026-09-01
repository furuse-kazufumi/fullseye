---
op: lf_focal_stack
dim: lightfield
category: refocus
in: lightfield
out: images
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_focal_stack — LIGHTFIELD `refocus` op

- **データ種**: `lightfield` → `images`
- **呼び出し**: `import lightfield; lightfield.lf_focal_stack(lf, slopes=(-2.0, -1.0, 0.0, 1.0, 2.0), *, interp='linear', edge='nearest')` (または `opslightfield.get("lf_focal_stack")`)

## 使い方

Refocus at every slope in *slopes* — a focal stack from one exposure.

Returns a ``list`` of ``(H, W)`` images (the ``images`` type), in the order
given, so :mod:`focus_stack`'s fusion and any multi-image operator applies
unchanged. The physical camera equivalent is racking the focus N times; here
it costs one exposure and ``len(slopes) * V * U`` image shifts.

**Raises** ``ValueError``: *lf* not a valid light field, *slopes* empty or
longer than :data:`MAX_STACK_SLICES`, any slope non-finite or over
:data:`MAX_ABS_SLOPE`, a stack larger than :data:`MAX_STACK_ELEMENTS`,
unknown *interp* / *edge*.

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

## 同カテゴリ(`refocus`)

[lf_refocus](lf_refocus.md) · [lf_aperture_mask](lf_aperture_mask.md) · [lf_synthetic_aperture](lf_synthetic_aperture.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
