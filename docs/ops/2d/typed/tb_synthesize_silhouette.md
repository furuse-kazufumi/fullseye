---
op: tb_synthesize_silhouette
dim: 2d
category: typed
in: points
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tb_synthesize_silhouette — 2D `typed` op

- **データ種**: `points` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_synthesize_silhouette", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

3-D 点群を (K,R,t) カメラへ射影し占有画素 True のシルエット(H,W bool)を返す。

    GT 生成用。``points`` (N,3) を ``X_cam = R X + t`` で射影し、depth>0 かつ画像内に
    落ちた画素を True にする。疎な点群では射影像に穴が空くため、既定で穴埋め
    (``fill``, scipy.ndimage.binary_fill_holes)して中身の詰まった前景マスクにする。
    さらに ``dilate`` 画素だけ膨張させ「pixel が少しでも物体に触れれば前景」という
    被覆(coverage)意味のシルエットにする — これが visual hull の recall(物体 voxel を
    取りこぼさない)を離散化誤差の下でも保証するための保守側の丸め。

    Parameters
    ----------
    points : (N, 3) array_like  ワールド座標の点群(物体表面/内部のサンプル)。
    K : (3, 3)  内部パラメータ。
    R, t : (3, 3), (3,)  ワールド->カメラの回転・並進。
    size : (H, W)  出力画像サイズ。
    fill : bool  射影像の穴を埋めて solid にする(既定 True)。
    dilate : int  被覆マージンとして膨張させる画素数(既定 1、0 で無効)。

    Returns
    -------
    (H, W) bool ndarray  前景 True のシルエット。

2-D 進化レジストリへ橋渡しした 3d の op ``synthesize_silhouette``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。この op に調整点は無く、``a`` も ``b`` も使われない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
