---
op: points_to_position
dim: reprconv
category: keypoint
in: points
out: position
examples: [representation_conversion, representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# points_to_position — REPRCONV `keypoint` op

- **データ種**: `points` → `position`
- **呼び出し**: `import reprconv; reprconv.points_to_position(points)` (または `opsreprconv.get("points_to_position")`)

## 使い方

点群 ``(N,3)`` → 重心 ``(z, y, x)``。**不可逆**(分布を捨てる)。

捨てた量は測れる: 重心まわりの RMS 距離が「1 点に潰したときに失った広がり」
そのもので、``selftest`` はこれを数字で出す。N = 1 のときだけ
:func:`position_to_points` との往復が bit 一致する。

Args:
    points: (N, 3) の (z, y, x)。
Returns:
    3-tuple の float (z, y, x)。
Raises:
    ValueError: 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`
- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`position` を入力に取れる)

[position_to_points](position_to_points.md)

## 同カテゴリ(`keypoint`)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [points_zyx_to_keypoints_uv](points_zyx_to_keypoints_uv.md) · [keypoints_to_image2d](keypoints_to_image2d.md) · [keypoints_from_image2d](keypoints_from_image2d.md) · [position_to_points](position_to_points.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
