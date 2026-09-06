---
op: tb_farthest_point_sampling
dim: 2d
category: typed
in: points
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tb_farthest_point_sampling — 2D `typed` op

- **データ種**: `points` → `signal`
- **呼び出し**: `fullseye.apply(img, "tb_farthest_point_sampling", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tb_farthest_point_sampling: input → output](../../_fig/tb_farthest_point_sampling.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tb_farthest_point_sampling: knob a sweep](../../_fig/tb_farthest_point_sampling.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![tb_farthest_point_sampling: stages](../../_fig/tb_farthest_point_sampling.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tb_farthest_point_sampling: other inputs](../../_fig/tb_farthest_point_sampling.inputs.jpg)

## 使い方

測地距離での最遠点サンプリング(均等間引き)。→ 選択インデックス列 (n,) int。

    ``start`` を最初の代表点にし、「既に選んだ点集合への測地距離が最大の点」を 1 つずつ追加する
    貪欲法(FPS)。距離は ``knn_graph(points, k)`` の無向 kNN グラフ上の Dijkstra で測り、既選択
    集合への距離は各代表点の単源距離の要素ごと最小 ``mind`` として保持、代表点を 1 つ足すたびに
    ``mind = min(mind, d_new)`` で更新する。代表点 1 つにつき Dijkstra 1 回なので計算量は n 回分の
    単源最短路。乱数は使わず決定的。

    - ``points``: (N,3) 点群。``n``: 欲しい点数。``N`` を超えると ``N`` に、負なら 0 に丸める
      (0 なら空配列)。
    - ``k``: kNN グラフの近傍数(既定 8)。``start``: 最初の代表点(``start % N`` で範囲内に折り返す)。
    - 返り値は選んだ順の添字列(先頭が ``start``)。``points[idx]`` で代表点群になる。

    罠: グラフが複数の連結成分に分かれていると、不達の点は距離 ``inf`` なので未到達の成分が先に
    選ばれる(argmax が ``inf`` を拾う)。「離れた塊から先に取る」挙動になるので、成分ごとに
    均等に間引きたいなら ``euclidean_cluster`` 等で分けてから使う。

2-D 進化レジストリへ橋渡しした 3d の op ``farthest_point_sampling``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``k``(既定 8)を振る。``b`` は未使用。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_points 0.50 0.50
tb_farthest_point_sampling 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `farthest_point_sampling` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [geodesic_distance](../../../../examples_3d/geodesic_distance.py) — `py -3.11 examples_3d/geodesic_distance.py`
- [pointcloud_downsampling](../../../../examples_3d/pointcloud_downsampling.py) — `py -3.11 examples_3d/pointcloud_downsampling.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[identity](../misc/identity.md) · [tb_create_funct_1d_array](tb_create_funct_1d_array.md) · [tb_smooth_funct_1d_gauss](tb_smooth_funct_1d_gauss.md) · [tb_smooth_funct_1d_mean](tb_smooth_funct_1d_mean.md) · [tb_derivate_funct_1d](tb_derivate_funct_1d.md) · [tb_integrate_funct_1d](tb_integrate_funct_1d.md) · [tb_zero_crossings_funct_1d](tb_zero_crossings_funct_1d.md) · [tb_abs_funct_1d](tb_abs_funct_1d.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
