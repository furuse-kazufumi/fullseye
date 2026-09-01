---
op: score_to_image2d
dim: reprconv
category: score
in: score
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# score_to_image2d — REPRCONV `score` op

- **データ種**: `score` → `image2d`
- **呼び出し**: `import reprconv; reprconv.score_to_image2d(score, axis=0)` (または `opsreprconv.get("score_to_image2d")`)

## 使い方

``score`` volume → 最大値投影 ``image2d``。``score`` の 2 つ目の出口。

指定軸に沿った最大値投影(MIP)。**一方向**。相関ピークが「どの面から見ても
1 本に見えるか」を確かめるのに使う —— 2 本見えたら対応が曖昧という意味。

Args:
    score: (D, H, W)。
    axis: 潰す軸(0/1/2)。
Returns:
    (H, W) 等の 2-D float64。
Raises:
    ValueError: 3-D でない / axis が範囲外 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[keypoints_from_image2d](../keypoint/keypoints_from_image2d.md)

## 同カテゴリ(`score`)

[correlation_score](correlation_score.md) · [score_to_position](score_to_position.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
