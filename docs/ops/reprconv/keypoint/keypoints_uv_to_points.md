---
op: keypoints_uv_to_points
dim: reprconv
category: keypoint
in: keypoints
out: points
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# keypoints_uv_to_points — REPRCONV `keypoint` op

- **データ種**: `keypoints` → `points`
- **呼び出し**: `import reprconv; reprconv.keypoints_uv_to_points(keypoints, z=0.0)` (または `opsreprconv.get("keypoints_uv_to_points")`)

## 使い方

画像座標 ``(N,2) = (u, v)`` → 点群 ``(N,3) = (z, y, x)``。``keypoints`` の出口。

**op 名に軸の約束が書いてある**のは、この repo で ``keypoints`` を産む
``match3d.project_points`` が **(u, v) = (列, 行)** を返し、``points`` を産む
``fuse3d.to_points(voxel)`` が **(z, y, x)** を返すから —— 素直に「先頭 2 列」
として繋ぐと**例外も NaN も出ないまま行と列が入れ替わる**。ここでは
``y = v``、``x = u`` と明示的に入れ替えて渡す。

:func:`points_zyx_to_keypoints_uv` と往復して **bit 一致**(z を渡した向き)。

Args:
    keypoints: (N, 2) の (u, v)。
    z: 載せる平面の z(スカラ、または (N,) の配列)。
Returns:
    (N, 3) float64 の (z, y, x)。
Raises:
    ValueError: 形状不正 / 非有限 / z の長さ不一致。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_zyx_to_keypoints_uv](points_zyx_to_keypoints_uv.md) · [points_to_position](points_to_position.md) · [select_points](../index/select_points.md) · [flow_apply](../flow/flow_apply.md) · [points_to_gaussians](../gaussians/points_to_gaussians.md)

## 同カテゴリ(`keypoint`)

[points_zyx_to_keypoints_uv](points_zyx_to_keypoints_uv.md) · [keypoints_to_image2d](keypoints_to_image2d.md) · [keypoints_from_image2d](keypoints_from_image2d.md) · [position_to_points](position_to_points.md) · [points_to_position](points_to_position.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
