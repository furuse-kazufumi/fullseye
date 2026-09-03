---
op: flow_apply
dim: reprconv
category: flow
in: points × flow_scattered
out: points
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# flow_apply — REPRCONV `flow` op

- **データ種**: `points × flow_scattered` → `points`
- **呼び出し**: `import reprconv; reprconv.flow_apply(points, flow)` (または `opsreprconv.get("flow_apply")`)

## 使い方

点群 ``(N,3)`` に散在フロー ``(N,3)`` を足す → ``points``。``flow`` の消費側。

``estimate_flow(a, b)`` が「a の各点から b の最近傍への変位」を返すので、
``flow_apply(a, estimate_flow(a, b))`` は **b の点のうち a から最近傍として
選ばれたもの**へ移る。往復が厳密になるのは対応が全単射のときだけで、
そうでなければ「a の 2 点が b の同じ点へ落ちる」ぶんだけ形が縮む
—— ``selftest`` はこの残差を数字で出す。

Args:
    points: (N, 3)。
    flow: (N, 3)。
Returns:
    (N, 3) float64。
Raises:
    ValueError: 行数不一致 / 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_zyx_to_keypoints_uv](../keypoint/points_zyx_to_keypoints_uv.md) · [points_to_position](../keypoint/points_to_position.md) · [select_points](../index/select_points.md) · [points_to_gaussians](../gaussians/points_to_gaussians.md)

## 同カテゴリ(`flow`)

[flow_magnitude](flow_magnitude.md) · [flow_to_rgbimage](flow_to_rgbimage.md) · [flow_speed](flow_speed.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
