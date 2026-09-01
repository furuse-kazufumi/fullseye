---
op: quat_conjugate_image
dim: quat
category: algebra
in: qimage
out: qimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# quat_conjugate_image — QUAT `algebra` op

- **データ種**: `qimage` → `qimage`
- **呼び出し**: `import quatimage; quatimage.quat_conjugate_image(qimage) -> 'np.ndarray'` (または `opsquat.get("quat_conjugate_image")`)

## 使い方

Per-pixel quaternion conjugate ``(w, -x, -y, -z)``. → (H, W, 4).

Exact and involutive: ``quat_conjugate_image(quat_conjugate_image(q)) is q``
to the last bit (a sign flip is exact in IEEE 754). Agrees with
``pose_quat.quat_conjugate`` per pixel, asserted in the tests.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`qimage` を入力に取れる)

[quaternion_to_rgb](../convert/quaternion_to_rgb.md) · [quat_norm](../convert/quat_norm.md) · [quat_normalize_image](quat_normalize_image.md) · [quat_image_multiply](quat_image_multiply.md) · [monogenic_amplitude](../riesz/monogenic_amplitude.md) · [monogenic_phase](../riesz/monogenic_phase.md) · [monogenic_orientation](../riesz/monogenic_orientation.md) · [quat_color_rotate](../color/quat_color_rotate.md)

## 同カテゴリ(`algebra`)

[quat_normalize_image](quat_normalize_image.md) · [quat_image_multiply](quat_image_multiply.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
