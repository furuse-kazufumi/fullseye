---
op: points_zyx_to_keypoints_uv
dim: reprconv
category: keypoint
in: points
out: keypoints
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# points_zyx_to_keypoints_uv — REPRCONV `keypoint` op

- **データ種**: `points` → `keypoints`
- **呼び出し**: `import reprconv; reprconv.points_zyx_to_keypoints_uv(points)` (または `opsreprconv.get("points_zyx_to_keypoints_uv")`)

## 使い方

点群 ``(N,3) = (z, y, x)`` → 画像座標 ``(N,2) = (u, v)``。

:func:`keypoints_uv_to_points` の逆向き。**不可逆** —— z が落ちる。
落ちる量は測れる: 往復して戻ってこない値は z 列そのもので、
``selftest`` は「z の RMS = 落とした情報量」として数字で出す。

Args:
    points: (N, 3) の (z, y, x)。
Returns:
    (N, 2) float64 の (u, v) = (x, y)。
Raises:
    ValueError: 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [keypoints_to_image2d](keypoints_to_image2d.md)

## 同カテゴリ(`keypoint`)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [keypoints_to_image2d](keypoints_to_image2d.md) · [keypoints_from_image2d](keypoints_from_image2d.md) · [position_to_points](position_to_points.md) · [points_to_position](points_to_position.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
