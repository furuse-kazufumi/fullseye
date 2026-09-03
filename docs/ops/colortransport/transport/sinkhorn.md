---
op: sinkhorn
dim: colortransport
category: transport
in: signal × signal × matrix
out: transport_plan
examples: [color_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# sinkhorn — COLORTRANSPORT `transport` op

- **データ種**: `signal × signal × matrix` → `transport_plan`
- **呼び出し**: `import colortransport; colortransport.sinkhorn(a, b, cost, reg=0.05, n_iter=2000, tol=1e-09)` (または `opscolortransport.get("sinkhorn")`)

## 使い方

エントロピー正則化つき最適輸送の計画(Cuturi, NIPS 2013)。

**厳密解ではない。** ``reg`` を小さくすると厳密解に近づくが、同時に
数値的に不安定になる(指数がアンダーフローする)。``reg`` を下げると
厳密解との差が縮むこと自体をテストで固定してある。

Returns
-------
ndarray
    ``(n, m)`` の輸送計画。行和・列和は ``a`` / ``b`` に一致する
    (``tol`` まで)。収束しなければ ``RuntimeError`` ―― 収束しないまま
    最後の反復を返すと、行和が合っていない計画が黙って下流へ流れる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`

## 型が繋がる次の op(`transport_plan` を入力に取れる)

[transport_cost](../plan_use/transport_cost.md) · [apply_transport](../plan_use/apply_transport.md)

## 同カテゴリ(`transport`)

[wasserstein_1d](wasserstein_1d.md) · [transport_plan_1d](transport_plan_1d.md) · [sinkhorn_distance](sinkhorn_distance.md) · [sinkhorn_divergence](sinkhorn_divergence.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
