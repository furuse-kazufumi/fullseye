---
op: transport_cost
dim: colortransport
category: plan_use
in: transport_plan × matrix
out: scalar
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# transport_cost — COLORTRANSPORT `plan_use` op

- **データ種**: `transport_plan × matrix` → `scalar`
- **呼び出し**: `import colortransport; colortransport.transport_cost(plan, cost)` (または `opscolortransport.get("transport_cost")`)

## 使い方

輸送計画の総費用 ``<plan, cost>``。**計画を消費する**側の op。

計画は「行和・列和が周辺分布に一致する」という意味を持つ行列で、普通の
``matrix`` として扱うと質量保存が黙って壊れる。ここは計画としての検査
(非負・和が 1 前後)を通してから費用を出す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`plan_use`)

[apply_transport](apply_transport.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
