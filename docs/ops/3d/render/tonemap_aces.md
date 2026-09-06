---
op: tonemap_aces
dim: 3d
category: render
in: image2d
out: image2d
examples: [render_tonemap]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tonemap_aces — 3D `render` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import render_tonemap; render_tonemap.tonemap_aces(hdr, exposure: 'float' = 1.0) -> 'np.ndarray'` (または `ops3d.get("tonemap_aces")`)

## 使い方

ACES filmic 近似(Narkowicz 2015)で HDR を ``[0, 1]`` の LDR へ圧縮。→ float64。

``x = hdr * exposure`` に対し ``f(x) = x(a x + b) / (x(c x + d) + e)`` を適用する。
フィルム的な S 字カーブで暗部を持ち上げハイライトを緩やかに巻き取り、映像制作標準の
「見栄え」を出す。``x < ~7.24`` の範囲では狭義単調増加・出力 < 1(それ以上は 1 に
飽和しクリップ)。カラー ``(H, W, C)`` はチャンネル独立に写像する。

Args:
    hdr: HDR 画像。``(H, W)`` or ``(H, W, C)``、放射輝度 >= 0。
    exposure: 写像前に掛ける露出スケール(正)。
Returns:
    ``[0, 1]`` の float64 LDR 画像(入力と同形状)。
Raises:
    ValueError: 空/非有限/負の放射輝度、非正の exposition(fail-closed)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_tonemap](../../../../examples_3d/render_tonemap.py) — `py -3.11 examples_3d/render_tonemap.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md)

---
*Provenance: render_tonemap.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
