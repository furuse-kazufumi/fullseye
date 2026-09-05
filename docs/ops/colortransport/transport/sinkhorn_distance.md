---
op: sinkhorn_distance
dim: colortransport
category: transport
in: signal × signal × matrix
out: scalar
examples: [color_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# sinkhorn_distance — COLORTRANSPORT `transport` op

- **データ種**: `signal × signal × matrix` → `scalar`
- **呼び出し**: `import colortransport; colortransport.sinkhorn_distance(a, b, cost, reg=0.05, **kw)` (または `opscolortransport.get("sinkhorn_distance")`)

## 使い方

正則化つき輸送費 ``<plan, cost>``。**厳密な距離ではない**。

正則化のぶん系統的に偏るので、自分自身との「距離」も 0 にならない
(そのずれ幅はテストに実測で残してある)。1 次元で厳密が要るときは
:func:`wasserstein_1d`。

## 背景知識ガイド(この op の手前にある物理・規約)

- [colorimetry](../../2d/guides/colorimetry.md) — 測色と分光の知識 — 色は「分光 × 光源 × 観測者」でしか決まらない

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`transport`)

[wasserstein_1d](wasserstein_1d.md) · [transport_plan_1d](transport_plan_1d.md) · [sinkhorn](sinkhorn.md) · [sinkhorn_divergence](sinkhorn_divergence.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
