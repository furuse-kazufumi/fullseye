---
op: tb_statistical_outlier_removal
dim: 2d
category: typed
in: points
out: points
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tb_statistical_outlier_removal — 2D `typed` op

- **データ種**: `points` → `points`
- **呼び出し**: `fullseye.apply(img, "tb_statistical_outlier_removal", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tb_statistical_outlier_removal: input → output](../../_fig/tb_statistical_outlier_removal.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tb_statistical_outlier_removal: knob a sweep](../../_fig/tb_statistical_outlier_removal.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tb_statistical_outlier_removal: knob b sweep](../../_fig/tb_statistical_outlier_removal.b.jpg)

**段階**(前置きの op → この op。左から順):

![tb_statistical_outlier_removal: stages](../../_fig/tb_statistical_outlier_removal.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tb_statistical_outlier_removal: other inputs](../../_fig/tb_statistical_outlier_removal.inputs.jpg)

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

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_points 0.50 0.50
tb_statistical_outlier_removal 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `statistical_outlier_removal` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [pcl_geodesic](../../../../examples_3d/pcl_geodesic.py) — `py -3.11 examples_3d/pcl_geodesic.py`

## 型が繋がる次の op(`points` を入力に取れる)

[identity](../misc/identity.md) · [tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
