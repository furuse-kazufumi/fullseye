---
op: keypoints_from_image2d
dim: reprconv
category: keypoint
in: image2d
out: keypoints
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# keypoints_from_image2d — REPRCONV `keypoint` op

- **データ種**: `image2d` → `keypoints`
- **呼び出し**: `import reprconv; reprconv.keypoints_from_image2d(image2d, threshold=0.0)` (または `opsreprconv.get("keypoints_from_image2d")`)

## 使い方

計数/応答画像 ``(H, W)`` → 画像座標 ``(N,2) = (u, v)``。往復の戻り路。

``> threshold`` の画素を 8 近傍で連結成分に分け、各成分の**強度重み付き
重心**を返す。重み付きにするのは、副画素の情報が残っている応答画像
(相関ピーク等)で往復誤差を量子化以下へ落とせるようにするため。

**8 近傍の連結が損失の主犯**である点に注意: 隣り合う画素に落ちた 2 点は
1 つの成分に融合し、重心が 2 点の中間へ動く。``selftest`` は
「よく離れた点だけの量子化誤差」と「融合を含む全体」を**別々に**測る
(混ぜると量子化の理論値 0.2887 px と比較できなくなる)。

Args:
    image2d: (H, W) の実画像。
    threshold: この値を超えた画素だけを拾う。
Returns:
    (N, 2) float64 の (u, v)。行順は ``scipy.ndimage.label`` のラベル順。
Raises:
    ValueError: 2-D でない / 非有限 / 閾値を超える画素が 1 つも無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [keypoints_to_image2d](keypoints_to_image2d.md)

## 同カテゴリ(`keypoint`)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [points_zyx_to_keypoints_uv](points_zyx_to_keypoints_uv.md) · [keypoints_to_image2d](keypoints_to_image2d.md) · [position_to_points](position_to_points.md) · [points_to_position](points_to_position.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
