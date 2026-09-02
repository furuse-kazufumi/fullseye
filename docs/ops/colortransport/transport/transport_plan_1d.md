---
op: transport_plan_1d
dim: colortransport
category: transport
in: signal × signal
out: transport_plan
examples: [color_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# transport_plan_1d — COLORTRANSPORT `transport` op

- **データ種**: `signal × signal` → `transport_plan`
- **呼び出し**: `import colortransport; colortransport.transport_plan_1d(u_values, v_values)` (または `opscolortransport.get("transport_plan_1d")`)

## 使い方

1 次元の厳密な輸送計画(北西隅則)。``(n, m)`` の質量行列を返す。

行和が ``1/n``、列和が ``1/m`` になる ―― これは**構成上厳密**で、
数値誤差以外でずれることはない(テストで固定)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`

## 型が繋がる次の op(`transport_plan` を入力に取れる)

[transport_cost](../plan_use/transport_cost.md) · [apply_transport](../plan_use/apply_transport.md)

## 同カテゴリ(`transport`)

[wasserstein_1d](wasserstein_1d.md) · [sinkhorn](sinkhorn.md) · [sinkhorn_distance](sinkhorn_distance.md) · [sinkhorn_divergence](sinkhorn_divergence.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
