---
op: brdf_hapke
dim: 3d
category: render
in: normalmap
out: image2d
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# brdf_hapke — 3D `render` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.brdf_hapke(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0), w: 'float' = 0.42, g: 'float' = -0.35, B0: 'float' = 0.87, h: 'float' = 0.01, roughness_deg: 'float' = 26.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import render_shade; render_shade.brdf_hapke(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0), w: 'float' = 0.42, g: 'float' = -0.35, B0: 'float' = 0.87, h: 'float' = 0.01, roughness_deg: 'float' = 26.0) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("brdf_hapke")`)

## 使い方

Hapke 反射則(対向効果 + 多重散乱 + 巨視的粗さ θ̄)で法線マップを陰影付けし I/F ``(H, W)`` を返す。

既定値はイトカワの S 型典型値(Kitazato et al. 2008): w=0.42, g=−0.35, B0=0.87,
h=0.01, θ̄=26°。位相角は ``light``/``view`` から一定値として求める(平行光・正射影近似)。
fail-closed: 各パラメータの範囲外・法線形状不正は ``ValueError``。

:func:`brdf_shade` の ``model='hapke'`` の薄い包みで、各画素の ``μ0 = clip(N·L,0,1)``、
``μ = clip(N·V,0,1)`` と、画面全体で一定の位相角 ``g = arccos(L·V)``(ラジアン)を
:func:`hapke_reflectance` に渡し、``I/F = π·r`` を返す。``r`` は
``(w/4π)·μ0e/(μ0e+μe)·[(1+B(g))P(g) + H(μ0e)H(μe) − 1]·S`` で、多重散乱項 H は常に有効。

- ``normals``: float ``(H, W, 3)``、長さ 0 = 背景(出力 0)。単位化は内部で行う。
- ``light`` / ``view``: 面→光源、面→視点の方向(内部で単位化、ゼロ長は ``ValueError``)。
- ``w``: 単一散乱アルベド ``(0, 1]``。
- ``g``: Henyey-Greenstein の非対称パラメータ、``(−1, 1)`` の開区間。負で後方散乱。
- ``B0`` / ``h``: 対向効果(opposition surge)の振幅と角幅。``B0 > 0`` なのに ``h == 0`` は
  ``ValueError``。``B0 = 0`` で対向効果なし。
- ``roughness_deg``: 巨視的粗さ θ̄ を **度** で与える(内部で rad に変換)。0 で粗さ補正なし
  (μ0e=μ0, μe=μ, S=1)。負・非有限は ``ValueError``。

返り値は float64 ``(H, W)`` の I/F で、``[0,1]`` に正規化しない(負値は 0 に切る)。
影(他の面による遮蔽)は含まないので、必要なら ``cast_shadow`` / ``shadow_raycast`` の
可視性マップを掛ける(``render_regolith`` は ``shadow_raycast`` と組み合わせる)。
μ0 か μ が 0 以下の画素は 0。

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
