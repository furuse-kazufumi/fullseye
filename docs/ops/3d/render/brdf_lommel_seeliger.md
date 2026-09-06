---
op: brdf_lommel_seeliger
dim: 3d
category: render
in: normalmap
out: image2d
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# brdf_lommel_seeliger — 3D `render` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import render_shade; render_shade.brdf_lommel_seeliger(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0), w: 'float' = 0.42) -> 'np.ndarray'` (または `ops3d.get("brdf_lommel_seeliger")`)

## 使い方

Lommel-Seeliger 反射則(縁まで明るいレゴリス)で法線マップを陰影付けし I/F ``(H, W)`` を返す。

Lambert(``phong_shade`` の拡散項)は縁(μ→0)で 0 になるが、Lommel-Seeliger は
μ0/(μ0+μ) なので縁でも μ0 のまま明るく、小惑星・月の「平坦な円盤」の見えになる。
``w`` = 単一散乱アルベド。fail-closed(法線形状・w の範囲)。

計算は :func:`brdf_shade` の ``model='lommel_seeliger'`` と同一で、各画素について
``μ0 = clip(N·L, 0, 1)``、``μ = clip(N·V, 0, 1)`` を取り、
``I/F = π · (w/4π) · μ0/(μ0+μ)``(= ``(w/4)·μ0/(μ0+μ)``)を返す。μ0 か μ が 0 以下の画素
(光の当たらない面・視線に背く面)は 0。

- ``normals``: float ``(H, W, 3)``。長さ 0 のベクトルは背景とみなし出力 0
  (``render3d.render_mesh`` の ``normals`` をそのまま渡せる)。単位化は内部で行う。
- ``light`` / ``view``: 面→光源、面→視点へ向かう方向ベクトル(内部で単位化)。カメラは
  ``-Z`` を見る規約なので既定 ``view=(0,0,1)``。平行光・正射影近似で、方向は画面内で一定。
- ``w``: 単一散乱アルベド、``(0, 1]`` 以外は ``ValueError``。

返り値は float64 ``(H, W)`` の I/F。正射影で ``light == view``(位相角 0)なら
μ0 = μ で全前景が ``w/8`` の一様値になる。値は ``[0, w/4)`` に収まり ``[0,1]`` へ
正規化しない。ハイライトを扱いたければ ``phong_shade``、対向効果・粗さまで入れたければ
``brdf_hapke`` を使う。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md)

---
*Provenance: render_shade.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
