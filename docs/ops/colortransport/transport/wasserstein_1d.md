---
op: wasserstein_1d
dim: colortransport
category: transport
in: signal × signal
out: scalar
examples: [color_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# wasserstein_1d — COLORTRANSPORT `transport` op

- **データ種**: `signal × signal` → `scalar`
- **呼び出し**: `import colortransport; colortransport.wasserstein_1d(u_values, v_values, p=1, u_weights=None, v_weights=None)` (または `opscolortransport.get("wasserstein_1d")`)

## 使い方

1 次元の p-Wasserstein 距離。**厳密解**。

1 次元では最適輸送に閉じた形があり、累積分布の逆関数どうしの
``L^p`` 距離になる ―― 反復も近似も要らない。総当たりの割当問題
(``scipy.optimize.linear_sum_assignment``)と厳密に一致することを
テストで固定してある。

Parameters
----------
u_values, v_values : array_like
    標本(1 次元に潰される)。長さは違ってよい。
p : float
    次数。``p=1`` が Earth Mover 距離、``p=2`` が 2-Wasserstein。
u_weights, v_weights : array_like, optional
    標本ごとの重み(和は内部で 1 に正規化する)。

Returns
-------
float

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

[transport_plan_1d](transport_plan_1d.md) · [sinkhorn](sinkhorn.md) · [sinkhorn_distance](sinkhorn_distance.md) · [sinkhorn_divergence](sinkhorn_divergence.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
