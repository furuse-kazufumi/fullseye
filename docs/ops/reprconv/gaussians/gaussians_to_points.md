---
op: gaussians_to_points
dim: reprconv
category: gaussians
in: gaussians
out: points
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# gaussians_to_points — REPRCONV `gaussians` op

- **データ種**: `gaussians` → `points`
- **呼び出し**: `import reprconv; reprconv.gaussians_to_points(gaussians)` (または `opsreprconv.get("gaussians_to_points")`)

## 使い方

``gaussians`` → 中心の点群 ``(N,3)``。``gaussians`` の出口(**中心は可逆**)。

Args:
    gaussians: ``mu`` / ``sigma`` / ``w`` を持つ dict。
Returns:
    (N, 3) float64(``mu`` のコピー)。
Raises:
    ValueError: キー欠落 / 形状不整合 / sigma <= 0 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_zyx_to_keypoints_uv](../keypoint/points_zyx_to_keypoints_uv.md) · [points_to_position](../keypoint/points_to_position.md) · [select_points](../index/select_points.md) · [flow_apply](../flow/flow_apply.md) · [points_to_gaussians](points_to_gaussians.md)

## 同カテゴリ(`gaussians`)

[points_to_gaussians](points_to_gaussians.md) · [gaussians_to_voxel](gaussians_to_voxel.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
