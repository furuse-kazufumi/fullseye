---
op: matcap_shade
dim: 3d
category: render
in: normalmap × image2d
out: image2d
examples: [render_shade]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# matcap_shade — 3D `render` op

- **データ種**: `normalmap × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.matcap_shade(normals, matcap) -> 'np.ndarray'` (実装を直接呼ぶなら `import render_shade; render_shade.matcap_shade(normals, matcap) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("matcap_shade")`)

## 使い方

MatCap: 視空間法線を lit-sphere テクスチャに写して素材の見えを転写。→ ``(H, W[, C])``。

視空間の単位法線 ``(nx, ny)``(``[-1,1]``)をテクスチャ座標に写像し
(``u = (nx+1)/2``, ``v = (1−ny)/2``、行方向で y を反転)、``matcap`` 画像を
**双線形補間** で引く。ライト計算をせず、球にライティングして撮った 1 枚の素材見えを
任意形状へそのまま貼れる(金属・粘土・トゥーンなど)。

``matcap`` は正方に近い lit-sphere テクスチャ:
  * グレースケール ``(h, w)``      → 出力 ``(H, W)``
  * カラー ``(h, w, C)``(C 任意)  → 出力 ``(H, W, C)``

背景(長さ 0 の法線)は 0。テクスチャ座標は端でクランプ(球外縁の法線 ``|(nx,ny)|→1`` は
テクスチャ縁を指す)。

fail-closed: 形状不正・非有限・小さすぎる(``h,w < 2``)テクスチャは ``ValueError``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_shade](../../../../examples_3d/render_shade.py) — `py -3.11 examples_3d/render_shade.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [antialias](antialias.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: render_shade.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
