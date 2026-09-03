---
op: keypoints_to_image2d
dim: reprconv
category: keypoint
in: keypoints
out: image2d
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# keypoints_to_image2d — REPRCONV `keypoint` op

- **データ種**: `keypoints` → `image2d`
- **呼び出し**: `import reprconv; reprconv.keypoints_to_image2d(keypoints, shape=(64, 64))` (または `opsreprconv.get("keypoints_to_image2d")`)

## 使い方

画像座標 ``(N,2) = (u, v)`` → 計数画像 ``(H, W)``。``keypoints`` の 2 つ目の出口。

``round(v)`` を行、``round(u)`` を列として 1 ずつ加算する。**画素格子への
量子化が損失**で、:func:`keypoints_from_image2d` と往復すると位置が
最大 0.5 画素ずれる(よく離れた 225 点での実測: **軸あたり** RMS 0.2835 px =
一様量子化の理論値 1/sqrt(12) = 0.2887 と一致。2-D 距離では sqrt(2) 倍の
0.4009 px で、理論 sqrt(2/12) = 0.4082)。
★ここも一度間違えた: 2-D 距離の実測を 1-D の理論値と並べて「0.29 のはずが
0.40 だ」と読みかけた —— 軸ごとの量と距離の量を混ぜると、正しい実装が
誤っているように見える。
近接した点は連結成分として融合するので、往復で点数も減りうる
(実測: 60 点をランダムに置くと 54 点)。

範囲外の点は**黙って捨てない** —— 捨てると「検出が減った」のか
「画像が小さすぎた」のかが区別できなくなる。

Args:
    keypoints: (N, 2) の (u, v)。
    shape: (H, W)。
Returns:
    (H, W) float64 の計数画像。
Raises:
    ValueError: 形状不正 / 非有限 / 範囲外の点がある / shape が上限超。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[keypoints_from_image2d](keypoints_from_image2d.md)

## 同カテゴリ(`keypoint`)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [points_zyx_to_keypoints_uv](points_zyx_to_keypoints_uv.md) · [keypoints_from_image2d](keypoints_from_image2d.md) · [position_to_points](position_to_points.md) · [points_to_position](points_to_position.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
