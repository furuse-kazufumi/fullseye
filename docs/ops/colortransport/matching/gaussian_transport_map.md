---
op: gaussian_transport_map
dim: colortransport
category: matching
in: points × points
out: matrix
examples: [color_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# gaussian_transport_map — COLORTRANSPORT `matching` op

- **データ種**: `points × points` → `matrix`
- **呼び出し**: `import colortransport; colortransport.gaussian_transport_map(src_samples, ref_samples)` (または `opscolortransport.get("gaussian_transport_map")`)

## 使い方

2 つの点群を正規分布とみなしたときの Monge 写像 ``(A, b)``。

``x -> A (x - m1) + m2`` で、``A`` は
``S1^-1/2 (S1^1/2 S2 S1^1/2)^1/2 S1^-1/2``(Bures 幾何の閉じた形)。
**共分散ごと運ぶ**ので、チャネル間の相関が保たれる。

退化(片方の共分散が特異)では逆平方根が作れない ―― 疑似逆で誤魔化すと
「運べていないのに運んだ顔をした」写像になるので ``ValueError``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [colorimetry](../../2d/guides/colorimetry.md) — 測色と分光の知識 — 色は「分光 × 光源 × 観測者」でしか決まらない

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[sinkhorn](../transport/sinkhorn.md) · [sinkhorn_distance](../transport/sinkhorn_distance.md) · [sinkhorn_divergence](../transport/sinkhorn_divergence.md) · [transport_cost](../plan_use/transport_cost.md)

## 同カテゴリ(`matching`)

[histogram_match](histogram_match.md) · [color_transfer](color_transfer.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
