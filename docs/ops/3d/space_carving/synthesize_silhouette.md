---
op: synthesize_silhouette
dim: 3d
category: space_carving
in: points
out: image2d
examples: [space_carving]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# synthesize_silhouette — 3D `space_carving` op

- **データ種**: `points` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.synthesize_silhouette(points, K, R, t, size: 'Tuple[int, int]', *, fill: 'bool' = True, dilate: 'int' = 1) -> 'np.ndarray'` (実装を直接呼ぶなら `import visualhull; visualhull.synthesize_silhouette(points, K, R, t, size: 'Tuple[int, int]', *, fill: 'bool' = True, dilate: 'int' = 1) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("synthesize_silhouette")`)

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

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [space_carving](../../../../examples_3d/space_carving.py) — `py -3.11 examples_3d/space_carving.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`space_carving`)

[carve](carve.md) · [visual_hull](visual_hull.md)

---
*Provenance: visualhull.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
