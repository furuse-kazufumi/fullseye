---
op: flow_magnitude
dim: reprconv
category: flow
in: flow_dense
out: voxel
examples: [perception_on_video, representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# flow_magnitude — REPRCONV `flow` op

- **データ種**: `flow_dense` → `voxel`
- **呼び出し**: `import reprconv; reprconv.flow_magnitude(flow)` (または `opsreprconv.get("flow_magnitude")`)

## 使い方

密なシーンフロー ``(3,D,H,W)`` → 速さの体積 ``voxel (D,H,W)``。``flow`` の出口。

``sqrt(dz^2 + dy^2 + dx^2)``。**一方向**(向きを捨てるので戻せない)。
捨てた量は明示できる: 3 成分のうち 2 自由度ぶんの方向が消え、残るのは
大きさだけ。方向まで見たいときは :func:`flow_to_rgbimage`。

Args:
    flow: (3, D, H, W)。成分順は (dz, dy, dx)(``scene_flow_lk`` の約束)。
Returns:
    (D, H, W) float64。
Raises:
    ValueError: 密フローでない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [perception_on_video](../../../../examples/perception_on_video.py) — `py -3.11 examples/perception_on_video.py`
- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[correlation_score](../score/correlation_score.md)

## 同カテゴリ(`flow`)

[flow_to_rgbimage](flow_to_rgbimage.md) · [flow_speed](flow_speed.md) · [flow_apply](flow_apply.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
