---
op: tb_project_cylindrical
dim: 2d
category: typed
in: points
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# tb_project_cylindrical — 2D `typed` op

- **データ種**: `points` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_project_cylindrical", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tb_project_cylindrical: input → output](../../_fig/tb_project_cylindrical.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tb_project_cylindrical: knob a sweep](../../_fig/tb_project_cylindrical.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tb_project_cylindrical: knob b sweep](../../_fig/tb_project_cylindrical.b.jpg)

**段階**(前置きの op → この op。左から順):

![tb_project_cylindrical: stages](../../_fig/tb_project_cylindrical.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tb_project_cylindrical: other inputs](../../_fig/tb_project_cylindrical.inputs.jpg)

## 使い方

円柱レンジ画像へ投影 (z_bins, h_res)。方位角(列)× z(行)、画素=水平半径 ρ=hypot(x,y)。

    球面投影が仰角で層を切るのに対し、円柱投影は**高さ z を等間隔に切る**(壁/柱/回廊の展開に向く)。
    画素値は z 軸からの水平距離 ρ(円柱上の点が一定になる自然な不変量)。空セル=0, 近い点優先(最小 ρ)。
    z_range=(z_min,z_max) 未指定なら点群の [z.min, z.max] を採用。z 幅ゼロは fail-closed(ValueError)。
    行 0 = 上端(z=z_max)。z_range 外、z 軸上(ρ=0)、非有限座標の点は落とす。

2-D 進化レジストリへ橋渡しした 3d の op ``project_cylindrical``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``h_res``(既定 1024)、``b`` が ``z_bins``(既定 64)を振る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_points 0.50 0.50
tb_project_cylindrical 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `project_cylindrical` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [curvilinear_proj](../../../../examples_3d/curvilinear_proj.py) — `py -3.11 examples_3d/curvilinear_proj.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
