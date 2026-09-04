---
op: pairs_to_image2d
dim: reprconv
category: pairs
in: pairs
out: image2d
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# pairs_to_image2d — REPRCONV `pairs` op

- **データ種**: `pairs` → `image2d`
- **呼び出し**: `import reprconv; reprconv.pairs_to_image2d(pairs, shape=(64, 64))` (または `opsreprconv.get("pairs_to_image2d")`)

## 使い方

対 ``(N,2)`` → 散布密度画像 ``(H, W)``。``pairs`` の 3 つ目の出口。

列 0 を行方向、列 1 を列方向に、それぞれの最小-最大で正規化して bin へ落とす
(2-D ヒストグラム)。位相図・相関図として見るためのもので、**不可逆**
(bin 幅ぶんの量子化 + 正規化で絶対値のスケールを捨てる)。
捨てたスケールは戻せるように ``extent`` を…返さない —— 返すと ``image2d``
でなくなる。必要なら :func:`pairs_to_table` の ``x_min`` などを使う。

定数列(最小 == 最大)は 0.5 の位置へ集める(0 除算を避けるが、
それを「密度が中央に集中している」と読まれないよう、bin は 1 本だけ立つ)。

Args:
    pairs: (N, 2)。
    shape: (H, W)。
Returns:
    (H, W) float64、最大値 1.0 に正規化した密度。
Raises:
    ValueError: 形状不正 / 非有限 / shape が上限超。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[keypoints_from_image2d](../keypoint/keypoints_from_image2d.md)

## 同カテゴリ(`pairs`)

[pairs_to_signal](pairs_to_signal.md) · [pairs_to_table](pairs_to_table.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
