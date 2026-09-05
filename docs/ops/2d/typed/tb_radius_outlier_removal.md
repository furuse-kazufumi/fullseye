---
op: tb_radius_outlier_removal
dim: 2d
category: typed
in: points
out: points
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_radius_outlier_removal — 2D `typed` op

- **データ種**: `points` → `points`
- **呼び出し**: `fullseye.apply(img, "tb_radius_outlier_removal", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

半径 radius 内の近傍数が min_neighbors 未満の点を除去する(孤立点除去)。

    各点を中心に半径 ``radius`` の球を張り、その中に居る他点の数が ``min_neighbors``
    に満たない点を「孤立した粒」として落とす。統計的手法より局所的・直接的で、
    センサの実スケールが分かっているときにしきい値を決めやすい。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        入力点群。
    radius : float
        近傍とみなす球の半径(> 0)。
    min_neighbors : int
        残すのに必要な近傍数(自分自身は数えない、既定 8)。

    Returns
    -------
    filtered : ndarray, shape (M, 3)
        生き残った点(元の順序を保持)。
    keep_mask : ndarray of bool, shape (N,)
        各入力点を残すか(True=残す)。

    Notes
    -----
    ``radius <= 0`` は ValueError。空入力は空を返す(graceful)。

2-D 進化レジストリへ橋渡しした 3d の op ``radius_outlier_removal``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``min_neighbors``(既定 8)を振る。``b`` は未使用。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`points` を入力に取れる)

[identity](../misc/identity.md) · [tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
