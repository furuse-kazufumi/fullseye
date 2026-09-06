---
op: hough_plane_3d
dim: 3d
category: detect
in: voxel
out: primitive
gpu: true
examples: [detect_primitives_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hough_plane_3d — 3D `detect` op

- **データ種**: `voxel` → `primitive`
- **呼び出し**: `import match3d; match3d.hough_plane_3d(vol, device='cpu', ndir=200, nd=128, mc=0.0, iso=0.5, tol=1.0)` (または `ops3d.get("hough_plane_3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

平面検出(2D Hough 直線の 3D リフト)。勾配=法線を使い (法線 n, 距離 d) 空間へ投票。

薄い境界面の各 voxel が自分の法線方向ビンと d=n·p に投票 → ピーク=支配平面。法線は勝ちビン内
の実法線平均で精緻化、d は投影のモード。点群/voxel の地面・壁の抽出に。返り値 (n(3,), d, inliers, total)。

手順: ``(vol > iso)`` の 1 voxel 厚の境界面(占有 voxel のうち 3³ erosion で消えるもの)を取り、
その voxel の単位勾配(``sobel3d``、``mc`` は生出力への閾値)を法線 ``n`` にする。``n`` は軸 0
成分が非負になるよう半球へ畳み、``d = n·p``(``p`` は整数 voxel index ``(z,y,x)``)。``ndir``
本の参照方向(26 以下は 26 近傍、それ以上は fibonacci 球)と ``nd`` 個の d ビンに投票し、
最多ビンの実法線平均で n を、その n への射影ヒストグラムのモード近傍の中央値で d を精緻化する。
返り値 ``(n(3,), d, inliers, total)``: ``n`` は **(z,y,x) 順**の単位法線(numpy float32)、
平面は ``n·(z,y,x) = d``(voxel 単位)。``inliers`` は ``|n·p − d| < tol`` の境界 voxel 数、
``total`` は境界 voxel の総数(inliers/total が支配平面の占める割合)。
- 境界 voxel が 10 未満なら **None を返す**(例外ではない)。
- 密度 voxel は ``iso`` で 2 値化される(個数密度なら 0.5 で「1 点以上」)。
- 1 枚しか返さない。複数平面はインライアを除いて再実行するか、点群なら ``plane_segmentation``
/ ``ransac_plane``。
後段: ``distance_point_plane`` / ``angle_between_planes`` で計測。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [detect_primitives_3d](../../../../examples_3d/detect_primitives_3d.py) — `py -3.11 examples_3d/detect_primitives_3d.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`detect`)

[hough_sphere_3d](hough_sphere_3d.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
