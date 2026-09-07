---
op: tb_plane_sdf
dim: 2d
category: typed
in: points
out: volume
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tb_plane_sdf — 2D `typed` op

- **データ種**: `points` → `volume`
- **呼び出し**: `fullseye.apply(img, "tb_plane_sdf", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

半空間(平面で切った側)の**厳密**な符号付き距離場(内側負・外側正)。

    ``sdf(p) = (p - point) · n̂``。法線 ``n̂`` の**指す側が外側(正)**で、反対側が内側。
    面取り(chamfer)・切断・「基板から上だけ」のような**片側だけを残す**演算に使う。
    ``sdf_intersect`` を重ねれば任意の凸多面体が作れる。ただし **max による交差は角の外側で
    厳密ではない**: 6 枚で直方体を作ると占有(``<= 0``)と内側の値は ``box_sdf`` に完全一致
    するが、外側は角の近くで最大 2.1(半辺 2 の箱・格子 0.25 で実測)だけ**過小評価**する
    —— CSG の標準的な性質で、距離そのものが要るなら ``box_sdf`` を使う。

    厳密性: 平面は全空間で勾配ノルム 1 なので、この値は**どこでも真の符号付き距離**
    (``box_sdf`` のように角で切り替わる場合分けが要らない)。

    引数と検証(``ValueError``):
    - ``grid``: 最終軸が 3 の float 配列 ``(..., 3)``(``grid_coords`` の出力または点列)。
    - ``point``: 平面上の 1 点(要素数 3)。
    - ``normal``: 平面の法線(要素数 3、**零ベクトル・NaN は拒否**)。長さは自動で 1 に
      正規化するので、大きさは結果に影響しない(向きだけが意味を持つ)。

    返り値: ``grid.shape[:-1]`` の float64。法線側で正、反対側で負、平面上で 0。

    使いどころ: ``sdf_subtract(part, plane_sdf(g, p, n))`` で「その平面より法線側を削る」。
    向きを逆にしたいときは ``normal`` の符号を反転する(``-sdf`` でも同じ)。

2-D 進化レジストリへ橋渡しした 3d の op ``plane_sdf``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。この op に調整点は無く、``a`` も ``b`` も使われない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `plane_sdf` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`

## 型が繋がる次の op(`volume` を入力に取れる)

[identity](../misc/identity.md) · [vol_gaussian](../3d/vol_gaussian.md) · [vol_median](../3d/vol_median.md) · [vol_erode](../3d/vol_erode.md) · [vol_dilate](../3d/vol_dilate.md) · [vol_threshold](../3d/vol_threshold.md) · [vol_reg_dilate](../3d/vol_reg_dilate.md) · [vol_reg_erode](../3d/vol_reg_erode.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
