---
op: tb_indices_to_labels
dim: 2d
category: typed
in: signal
out: volume
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_indices_to_labels — 2D `typed` op

- **データ種**: `signal` → `volume`
- **呼び出し**: `fullseye.apply(img, "tb_indices_to_labels", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

添字 ``(N,)`` → 選択マスク ``labels``。``indices`` の出口(**可逆**)。

    ``max(indices) + 1`` 長の 1-D ラベル配列を作り、選ばれた位置に 1 を置く。
    ``indices -> labels -> indices`` は **bit 一致**(重複と順序を除く)。
    逆向き ``labels -> indices -> labels`` は**末尾の背景を落とす**
    (長さが ``max_index + 1`` に切り詰まる)—— これは情報の損失であって
    バグではないので、:func:`labels_to_indices` の docstring に量を書いてある。

    Args:
        indices: (N,) の非負整数配列。
    Returns:
        (max + 1,) の int64 ラベル配列(選択 = 1、背景 = 0)。
    Raises:
        ValueError: 1-D でない / 負 / 空 / 上限超。

2-D 進化レジストリへ橋渡しした reprconv の op ``indices_to_labels``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。この op に調整点は無く、``a`` も ``b`` も使われない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`volume` を入力に取れる)

[identity](../misc/identity.md) · [vol_gaussian](../3d/vol_gaussian.md) · [vol_median](../3d/vol_median.md) · [vol_erode](../3d/vol_erode.md) · [vol_dilate](../3d/vol_dilate.md) · [vol_threshold](../3d/vol_threshold.md) · [vol_reg_dilate](../3d/vol_reg_dilate.md) · [vol_reg_erode](../3d/vol_reg_erode.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
