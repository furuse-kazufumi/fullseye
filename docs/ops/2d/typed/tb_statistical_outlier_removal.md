---
op: tb_statistical_outlier_removal
dim: 2d
category: typed
in: points
out: points
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tb_statistical_outlier_removal — 2D `typed` op

- **データ種**: `points` → `points`
- **呼び出し**: `fullseye.apply(img, "tb_statistical_outlier_removal", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

各点の k 近傍平均距離が大域的に外れる点を除去する(統計的外れ値除去)。

    点ごとに「最も近い k 個(自分自身は除く)までの平均距離」を測り、その全点分布の
    ``mean + std_ratio*std`` を超える点を飛び点とみなして落とす。まばらな飛び点の掃除に
    有効で、密な面上の点は残る。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        入力点群。
    k : int
        近傍数(既定 16)。点数が少なければ内部で ``n-1`` に丸める。
    std_ratio : float
        しきい値の緩さ。大きいほど残りやすい(除去が緩い)。

    Returns
    -------
    filtered : ndarray, shape (M, 3)
        生き残った点(元の順序を保持)。
    keep_mask : ndarray of bool, shape (N,)
        各入力点を残すか(True=残す)。``points[keep_mask]`` が ``filtered`` に等しい。

    Notes
    -----
    点数 < 3 では統計が立たないため、全点を残す(graceful)。

2-D 進化レジストリへ橋渡しした 3d の op ``statistical_outlier_removal``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``k``(既定 16)、``b`` が ``std_ratio``(既定 2)を振る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`points` を入力に取れる)

[identity](../misc/identity.md) · [tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
