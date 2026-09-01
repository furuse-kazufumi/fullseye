---
op: quat_image_multiply
dim: quat
category: algebra
in: qimage × qimage
out: qimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# quat_image_multiply — QUAT `algebra` op

- **データ種**: `qimage × qimage` → `qimage`
- **呼び出し**: `import quatimage; quatimage.quat_image_multiply(qimage, other, side) -> 'np.ndarray'` (または `opsquat.get("quat_image_multiply")`)

## 使い方

Hamilton product of a quaternion image with a quaternion or a field. → (H, W, 4).

``side="left"`` computes ``other * qimage``; ``side="right"`` computes
``qimage * other``. **There is no default** — see :func:`_require_side`. The
two results are genuinely different objects, not a sign convention: measured
on a standard-normal ``(32, 32, 4)`` field against a unit rotor,
``max|left - right| = 3.143`` and ``mean|left - right| = 0.4948`` on data
whose own extreme is 3.372 — that is, the two answers differ by as much as
the data itself. Neither raises, neither is NaN, and both look like a
perfectly good quaternion image.

*other* is either a single quaternion (a ``(4,)`` array-like) or a full
``(H, W, 4)`` field of the same shape; anything else is refused rather than
broadcast, because NumPy would happily broadcast a ``(H, 4)`` array along the
wrong axis and produce an image-shaped answer to a different question.

**Raises** ``ValueError``: either input is not a valid quaternion field;
*other* is neither ``(4,)`` nor exactly ``qimage``'s shape; *side* is not
``'left'`` / ``'right'``.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`qimage` を入力に取れる)

[quaternion_to_rgb](../convert/quaternion_to_rgb.md) · [quat_norm](../convert/quat_norm.md) · [quat_conjugate_image](quat_conjugate_image.md) · [quat_normalize_image](quat_normalize_image.md) · [monogenic_amplitude](../riesz/monogenic_amplitude.md) · [monogenic_phase](../riesz/monogenic_phase.md) · [monogenic_orientation](../riesz/monogenic_orientation.md) · [quat_color_rotate](../color/quat_color_rotate.md)

## 同カテゴリ(`algebra`)

[quat_conjugate_image](quat_conjugate_image.md) · [quat_normalize_image](quat_normalize_image.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
