---
op: curvature_to_shape_index
dim: reprconv
category: curvature
in: curvature
out: pairs
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# curvature_to_shape_index — REPRCONV `curvature` op

- **データ種**: `curvature` → `pairs`
- **呼び出し**: `import reprconv; reprconv.curvature_to_shape_index(curvature)` (または `opsreprconv.get("curvature_to_shape_index")`)

## 使い方

主曲率 ``(N,2)`` → 形状指数と曲がり ``(N,2)`` の ``pairs``。``curvature`` の出口。

Koenderink & van Doorn, *Surface shape and curvature scales*, Image and
Vision Computing 10(8) 1992 の (S, C):

    S = (2/pi) * atan2(k1 + k2, k1 - k2)      (k1 >= k2, S in [-1, 1])
    C = sqrt((k1^2 + k2^2) / 2)               (曲がりの大きさ)

**除算でなく atan2 で書いてある**のが要点で、球状臍点 (k1 == k2) でも
平面 (k1 == k2 == 0) でもゼロ除算にならず、:func:`shape_index_to_curvature`
との往復が**全域で厳密**になる(実測 max|Δ| = 4.6e-16)。教科書の
``atan((k1+k2)/(k1-k2))`` をそのまま実装すると臍点で NaN が出て、
その NaN が下流で「暗い画素」に化ける。

S = -1 は杯、0 は鞍、+1 は帽子。C は形と独立な「どれだけ曲がっているか」。

**入力順の情報だけは戻らない**: (k2, k1) の順で渡しても内部で k1 >= k2 へ
並べ替えるので、往復すると必ず降順で返る(向きの規約であり、値の損失ではない)。

Args:
    curvature: (N, 2) の ``[k1, k2]``、または 2 本の等長 1-D のタプル
        (``principal_curvatures`` の素の返りがこれ)。
Returns:
    (N, 2) float64。列 0 = S in [-1, 1]、列 1 = C >= 0。
Raises:
    ValueError: 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[angles_to_normals](../direction/angles_to_normals.md) · [shape_index_to_curvature](shape_index_to_curvature.md) · [pairs_to_signal](../pairs/pairs_to_signal.md) · [pairs_to_image2d](../pairs/pairs_to_image2d.md) · [pairs_to_table](../pairs/pairs_to_table.md) · [polar_to_cscalar](../algebra/polar_to_cscalar.md)

## 同カテゴリ(`curvature`)

[shape_index_to_curvature](shape_index_to_curvature.md) · [curvature_to_table](curvature_to_table.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
