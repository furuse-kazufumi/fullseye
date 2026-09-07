---
op: visual_hull
dim: 3d
category: space_carving
in: images
out: voxel
examples: [space_carving]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# visual_hull — 3D `space_carving` op

- **データ種**: `images` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.visual_hull(silhouettes: 'Sequence[np.ndarray]', Ks: 'Sequence[np.ndarray]', Rs: 'Sequence[np.ndarray]', ts: 'Sequence[np.ndarray]', bounds: 'Bounds', res: 'int') -> 'np.ndarray'` (実装を直接呼ぶなら `import visualhull; visualhull.visual_hull(silhouettes: 'Sequence[np.ndarray]', Ks: 'Sequence[np.ndarray]', Rs: 'Sequence[np.ndarray]', ts: 'Sequence[np.ndarray]', bounds: 'Bounds', res: 'int') -> 'np.ndarray'`、台帳から引くなら `ops3d.get("visual_hull")`)

## 使い方

多視点シルエットの visual hull を voxel 占有として返す(:func:`carve` の別名)。

引数・返り値・例外は ``carve`` と完全に同じ(内部でそのまま ``carve`` を呼ぶだけ)。

- ``silhouettes``: 各カメラの前景マスク (H,W) bool を M 個並べたリスト(サイズはカメラごとに
  異なってよい)。
- ``Ks``/``Rs``/``ts``: 各カメラの内部行列 (3,3)・回転 (3,3)・並進 (3,)。射影規約は
  ``X_cam = R @ X_world + t``、``pixel = (K @ X_cam)[:2] / Z``(OpenCV 流)。画素は最近傍に丸める。
- ``bounds``: ``((xmin,xmax),(ymin,ymax),(zmin,zmax))`` の彫刻領域(各軸 max > min 必須)。
- ``res``: 各軸の voxel 分割数(正の整数)。voxel 総数 ``res**3``。

返り値は (res,res,res) bool。``indexing='ij'`` で軸は (x,y,z)、``vox[i,j,k]`` の中心は
``(xmin+(i+.5)dx, ymin+(j+.5)dy, zmin+(k+.5)dz)``。voxel が残る条件は、全カメラで「カメラ前方
(Z>0)・画像内・その画素がシルエット前景」を満たすこと(AND)。1 台でも外れれば削られる。

fail-closed: リスト長の不一致、カメラ 0 台、``res <= 0``、退化 bounds はすべて ``ValueError``
(0 台のときに「全 voxel 占有」を復元結果と偽って返さない)。

注意: visual hull は物体の上位集合で、どのカメラからも見えない凹みは埋まったまま残る。
シルエットは ``synthesize_silhouette`` のように 1 画素太らせた被覆マスクにしておくと、離散化
誤差で物体 voxel を削り落とす取りこぼしを避けられる。結果は ``voxel_to_mesh`` でメッシュ化、
``esdf`` の占有入力にもそのまま使える。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [space_carving](../../../../examples_3d/space_carving.py) — `py -3.11 examples_3d/space_carving.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`space_carving`)

[carve](carve.md) · [synthesize_silhouette](synthesize_silhouette.md)

---
*Provenance: visualhull.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
