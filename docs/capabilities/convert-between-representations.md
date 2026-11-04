---
id: convert-between-representations
title: 画像を点・点群・体積・メッシュ・グラフへ渡して戻す
title_en: Carry an image through points, point clouds, volumes, meshes and graphs — and back
category: 組み立てる
ops: [keypoints_from_image2d, keypoints_to_image2d, keypoints_uv_to_points, points_zyx_to_keypoints_uv, pointmap_to_points, points_to_gaussians, correlation_score, score_to_position, knn_graph_to_conn_graph, labels_to_indices, select_points]
examples: [poc_bga_ball_type_roundtrip, representation_roundtrip, representation_conversion, type_connectivity_tour]
version: 0.2.0
inputs: [image2d]
pipeline: [keypoints_from_image2d, keypoints_uv_to_points, knn_graph, knn_graph_to_conn_graph, graph_components]
alternatives: [keypoints_rowcol_to_uv, depth_to_organized_points, voxel_to_mesh, graph_laplacian_spectrum, points_to_position]
limits: keypoints_from_image2d は 8 近傍の連結成分の重心なので、隣り合う画素に落ちた 2 点は 1 点に融合する(画素の往復が bit 一致なのは整数位置で離れた点だけ)。points は (z, y, x)、pointmap_to_points の返りは (x, y, z) で、取り違えても例外は出ない。gaussians_to_voxel は 3σ 打ち切りで質量が 1 にならない(0.99911、箱の極限 0.99192)。体積の相関は循環相関で、縁で切れたガウシアンはずれのピークを 1 voxel 動かしうる。
calibration: 画素・voxel の実寸は変換の外で持つ(op は格子の添字で計算する)。gaussians_to_voxel は origin と spacing を必ず渡す —— 既定の刻み 1 は世界座標をそのまま添字にする。
---

# 画像を点・点群・体積・メッシュ・グラフへ渡して戻す

## できること

1 枚の画像から、明るい塊を点(keypoints)にし、高さを載せて 3-D の点群にし、点ごとのガウシアンにして体積(voxel)にし、等値面のメッシュや近傍のグラフへ渡します。逆向きも揃っていて、点群 → keypoints → 計数画像、体積の相関 → 位置 → 画像と戻れます。どの変換も**軸の約束を op 名に書いて**あり(`keypoints_uv_to_points` は (u, v) → (z, y, x))、往復できるものは bit 一致、できないものは何が落ちるかを `opsreprconv.roundtrips()` が宣言しています。

## What it does

Turns the bright blobs of one image into keypoints, lifts them to a 3-D point cloud with a height, spreads each point into a Gaussian and samples a voxel volume, and hands that to an iso-surface mesh or a nearest-neighbour graph. The reverse direction exists as well: point cloud → keypoints → count image, and volume correlation → position → image. Every conversion spells its axis convention in its name (`keypoints_uv_to_points` is (u, v) → (z, y, x)); the reversible ones round-trip bit for bit, and `opsreprconv.roundtrips()` declares what the others lose.

## 向くところ / 向かないところ

**向く**: 「数える・位置を出す・つながりを見る・ずれを測る」を、それぞれ向いた型でやりたいとき(`poc_bga_ball_type_roundtrip`: 欠け 1 個の BGA 71 球を keypoints・メッシュのオイラー標数・グラフの 3 つで数えて全部 71、既知のずれは体積の相関のピークに厳密に立つ)。変換を挟んでも保たれるべき量(個数・質量・位相)で鎖の正しさを確かめたいとき。

**向かない**: ★くっついた塊を分けること —— 8 近傍の連結成分は融合した 2 点を 1 点にする(分けるなら先に `watershed` など)。★点群の列の流儀が分からないもの —— `pointmap_to_points` は (x, y, z)、`points_zyx_to_keypoints_uv` は (z, y, x) を期待し、取り違えても例外は出ない(`poc_bga_ball_type_roundtrip` で 15360 画素が左端の 4 列に積もった)。

## 推奨パイプライン

`keypoints_from_image2d` → `keypoints_uv_to_points` → `knn_graph` → `knn_graph_to_conn_graph` → `graph_components`

画像の塊を点にし、z を載せて点群にし、k 近傍のグラフを隣接行列にして連結成分を数える。成分の数はラプラシアンの 0 固有値の数(`graph_laplacian_spectrum`)と独立に一致するはずで、それを門にする。体積へ渡すなら `points_to_gaussians` → `gaussians_to_voxel`(opsreprconv 版、`opsreprconv.call` で呼ぶ)→ `voxel_to_mesh`。

## 代替

(row, col) の点は `keypoints_rowcol_to_uv` で (u, v) にしてから渡す。高さ画像を全画素の点群にするなら `depth_to_organized_points` → `pointmap_to_points`(列を (z, y, x) に反転してから)。体積の形は `voxel_to_mesh` → `mesh_volume`、つながりの別解は `graph_laplacian_spectrum`、点群の代表 1 点は `points_to_position`。

## 限界

- 8 近傍の融合: 隣り合う画素の 2 点は 1 点になり、重心が中間へ動く。画素の往復が bit 一致なのは整数位置でよく離れた点だけ(ランダムな 60 点では 54 点に減る)。
- 軸の流儀: points は (z, y, x)、pointmap は (x, y, z)、keypoints は (u, v) = (列, 行)。取り違えは例外にならない。
- ガウシアンの打ち切り: 3σ では質量 0.99911(箱が floor/ceil で最大 1 voxel 広がるので、極限 0.99192 より大きい)。6σ で 1 − 1.4e-10。
- 相関は循環: 縁で切れたガウシアンがあると、ずらした体積が元の体積の整数ずらしにならず、ピークが動く(z の格子を足りなくしたら 1 voxel ずれた)。
- メッシュの体積は marching cubes で過小(刻み 1 voxel で −1.20 %、0.25 で −0.020 %)。
- `gaussians_to_voxel` は ops3d(match3d、点群を受ける)と opsreprconv(gaussians を受ける)で**同名の別物**。`fs.ledger` は ops3d 版を返す。

## 実寸校正

op は格子の添字で計算するので、画素・voxel の実寸は変換の外で持つ。`gaussians_to_voxel` には origin と spacing を必ず渡す(既定の刻み 1 は世界座標をそのまま添字にする)。高さ画像の正射の pointmap は x, y が画素、z が高さの単位なので、単位の混在に注意。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs
import opsreprconv

R = opsreprconv.call
img = np.zeros((40, 60))
truth = [(10, 10), (10, 20), (10, 30), (30, 40), (30, 50)]   # (row, col)、2 つの群
for r, c in truth:
    img[r, c] = 1.0
kp = R("keypoints_from_image2d", img)                         # (u, v)
pts = R("keypoints_uv_to_points", kp, z=0.0)                  # (z, y, x)
back = R("keypoints_to_image2d", R("points_zyx_to_keypoints_uv", pts), shape=img.shape)
idx, dist = fs.ledger.knn_graph(pts, k=1)
comp = fs.ledger.graph_components(R("knn_graph_to_conn_graph", (idx, dist), weight="binary"))
print(len(kp), "points; image round trip:", bool(np.array_equal(back, img)),
      "; components:", int(comp.max()) + 1)
```
