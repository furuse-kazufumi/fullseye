---
op: quat_normalize_image
dim: quat
category: algebra
in: qimage
out: qimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# quat_normalize_image — QUAT `algebra` op

- **データ種**: `qimage` → `qimage`
- **呼び出し**: `import quatimage; quatimage.quat_normalize_image(qimage) -> 'np.ndarray'` (または `opsquat.get("quat_normalize_image")`)

## 使い方

Per-pixel normalisation to unit modulus. → (H, W, 4).

**Fail-closed on a zero pixel.** A quaternion image routinely contains exact
zeros — a black pixel is ``(0,0,0,0)`` — so the case is not hypothetical, and
a zero quaternion has no direction to normalise towards. It is refused by
name, with the count and the first offending pixel's row and column in the
message, rather than divided by ``norm + eps``: that idiom returns zero, and
a zero used as a rotor becomes the **identity rotation** with no exception
and no NaN to mark it. (``pose_quat.quat_normalize`` did exactly that until
2026-09-01 and now fail-closes too; see :func:`quat_color_rotate`.)

**Raises** ``ValueError``: any pixel has modulus 0.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`qimage` を入力に取れる)

[quaternion_to_rgb](../convert/quaternion_to_rgb.md) · [quat_norm](../convert/quat_norm.md) · [quat_conjugate_image](quat_conjugate_image.md) · [quat_image_multiply](quat_image_multiply.md) · [monogenic_amplitude](../riesz/monogenic_amplitude.md) · [monogenic_phase](../riesz/monogenic_phase.md) · [monogenic_orientation](../riesz/monogenic_orientation.md) · [quat_color_rotate](../color/quat_color_rotate.md)

## 同カテゴリ(`algebra`)

[quat_conjugate_image](quat_conjugate_image.md) · [quat_image_multiply](quat_image_multiply.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
