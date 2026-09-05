---
op: flow_speed
dim: reprconv
category: flow
in: flow_scattered
out: signal
examples: [representation_conversion, representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# flow_speed — REPRCONV `flow` op

- **データ種**: `flow_scattered` → `signal`
- **呼び出し**: `import reprconv; reprconv.flow_speed(flow)` (または `opsreprconv.get("flow_speed")`)

## 使い方

散在フロー ``(N,3)`` → 速さの ``signal`` ``(N,)``。散在 ``flow`` の出口。

**一方向**(向きを捨てる)。密フローを渡すと fail-closed —— 同じ ``flow``
という型名の下に別物が 2 つ入っているため、受け側で必ず選ばせる。

Args:
    flow: (N, 3) の変位ベクトル場。
Returns:
    (N,) float64。
Raises:
    ValueError: 散在フローでない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`
- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`flow`)

[flow_magnitude](flow_magnitude.md) · [flow_to_rgbimage](flow_to_rgbimage.md) · [flow_apply](flow_apply.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
