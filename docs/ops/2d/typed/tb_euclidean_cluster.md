---
op: tb_euclidean_cluster
dim: 2d
category: typed
in: points
out: volume
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_euclidean_cluster — 2D `typed` op

- **データ種**: `points` → `volume`
- **呼び出し**: `fullseye.apply(img, "tb_euclidean_cluster", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

半径 tol の近接グラフの連結成分で距離クラスタリング(-1=ノイズ)。

    互いに ``tol`` 以内の点を(推移的に)同一クラスタへ束ねる。空間的に離れた物体が
    別クラスタになる(接地面除去後の「どの塊が掴める物か」の分離に使う)。連結成分のうち
    ``min_size`` 未満のものはノイズとして -1。ラベルはクラスタサイズ降順で 0,1,2,...
    (決定論)。

    Args:
        points: (N,3) 点群。
        tol: 同一クラスタとみなす近接半径(距離、要 > 0)。
        min_size: これ未満の連結成分はノイズ(-1)。

    Returns:
        labels: (N,) int。0..(n_clusters-1) がクラスタ、-1 がノイズ。空入力は shape (0,)。

2-D 進化レジストリへ橋渡しした 3d の op ``euclidean_cluster``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``min_size``(既定 10)を振る。``b`` は未使用。

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
