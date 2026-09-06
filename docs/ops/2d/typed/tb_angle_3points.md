---
op: tb_angle_3points
dim: 2d
category: typed
in: points
out: feature
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tb_angle_3points — 2D `typed` op

- **データ種**: `points` → `feature`
- **呼び出し**: `fullseye.apply(img, "tb_angle_3points", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

*図なし: 型は届くが、汎用の合成入力では定義域が合わない —— 3 点(頂点 b と両端)を取る op で、(N,3) の点群は定義域の外。下の「実行できる例」で使い方を見ること。*

## 使い方

3 点のなす角(頂点 b、度)。∠ABC。

    ``arccos(û·v̂)``(``u = a − b``, ``v = c − b``)を度で返す(float)。値は **[0, 180]** で符号は
    無い(2-D でも回転の向きは区別しない)。引数は数値の 2 または 3 ベクトル、次元の混在は
    ValueError。``a == b`` か ``c == b`` だと零ベクトルの内積 0 で 90 が返る(例外は出ない)。
    内積は [−1,1] に clip するので数値誤差で NaN にはならない。
    用途: 曲げ角・関節角の計測、``fit_line_3d`` で得た 2 直線の交点まわりの角度。

2-D 進化レジストリへ橋渡しした 3d の op ``angle_3points``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。この op に調整点は無く、``a`` も ``b`` も使われない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `angle_3points` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
