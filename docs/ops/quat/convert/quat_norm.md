---
op: quat_norm
dim: quat
category: convert
in: qimage
out: image2d
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# quat_norm — QUAT `convert` op

- **データ種**: `qimage` → `image2d`
- **呼び出し**: `import quatimage; quatimage.quat_norm(qimage) -> 'np.ndarray'` (または `opsquat.get("quat_norm")`)

## 使い方

Per-pixel quaternion modulus ``|q| = sqrt(w^2+x^2+y^2+z^2)``. → (H, W).

**Raw / unnormalised**, following ``complexops.cx_magnitude``: a modulus is a
metric quantity and routinely exceeds one (a QFT spectrum's DC term is huge).
For a colour quaternion it is the colour *magnitude* — the length of the RGB
vector, i.e. luminance in the L2 sense; for a monogenic signal it is the
local amplitude and :func:`monogenic_amplitude` is the name that says so.
Use ``imgio.normalize`` for a displayable view.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[riesz_transform](../riesz/riesz_transform.md) · [monogenic_signal](../riesz/monogenic_signal.md)

## 同カテゴリ(`convert`)

[rgb_to_quaternion](rgb_to_quaternion.md) · [quaternion_to_rgb](quaternion_to_rgb.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
