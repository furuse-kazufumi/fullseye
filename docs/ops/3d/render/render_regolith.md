---
op: render_regolith
dim: 3d
category: render
in: mesh
out: rgbimage
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# render_regolith — 3D `render` op

- **データ種**: `mesh` → `rgbimage`
- **呼び出し**: `import fullseye as fs; fs.ledger.render_regolith(V, F, *, pose=None, intrinsics=None, size: 'int' = 512, ss: 'int' = 2, sun: 'Sequence[float]' = (0.3, 0.4, 1.0), w: 'float' = 0.42, g: 'float' = -0.35, B0: 'float' = 0.87, h: 'float' = 0.01, roughness_deg: 'float' = 26.0, sun_angular_diameter_deg: 'float' = 0.53, shadow_samples: 'int' = 4, ao_samples: 'int' = 32, tint: 'Sequence[float]' = (1.0, 0.97, 0.93), self_illumination: 'float' = 1.0, exposure='auto', albedo_variation: 'float' = 0.12, seed: 'int' = 0, smooth_normals: 'bool' = True, background: 'Sequence[float]' = (0.0, 0.0, 0.0), bump=None, vertex_normals=None, vertex_albedo=None, exposure_target: 'float' = 0.45) -> 'np.ndarray'` (実装を直接呼ぶなら `import render_beauty; render_beauty.render_regolith(V, F, *, pose=None, intrinsics=None, size: 'int' = 512, ss: 'int' = 2, sun: 'Sequence[float]' = (0.3, 0.4, 1.0), w: 'float' = 0.42, g: 'float' = -0.35, B0: 'float' = 0.87, h: 'float' = 0.01, roughness_deg: 'float' = 26.0, sun_angular_diameter_deg: 'float' = 0.53, shadow_samples: 'int' = 4, ao_samples: 'int' = 32, tint: 'Sequence[float]' = (1.0, 0.97, 0.93), self_illumination: 'float' = 1.0, exposure='auto', albedo_variation: 'float' = 0.12, seed: 'int' = 0, smooth_normals: 'bool' = True, background: 'Sequence[float]' = (0.0, 0.0, 0.0), bump=None, vertex_normals=None, vertex_albedo=None, exposure_target: 'float' = 0.45) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("render_regolith")`)

## 使い方

小惑星のレゴリスを物理ベース(Hapke + 太陽視直径のレイキャスト影 + 環境光ゼロ)で描く → RGB ``(size,size,3)``。

:func:`render_beauty` の合成:
  * 反射則 = Hapke(``w, g, B0, h, roughness_deg``; 既定はイトカワの S 型典型値)。
  * 影 = ``render_shadow.shadow_raycast``(視直径 ``sun_angular_diameter_deg``、既定 0.53° =
    太陽。半影は幾何どおり数 cm なので事実上ハード影)。地面(台座)は置かない。
  * 環境光 0(宇宙に空光は無い)。影の底は地形の一回反射近似 ``self_illumination`` だけ。
  * トーン = 線形(AMICA の 8bit 画像に合わせ、露出 × クリップ)。``exposure='auto'`` は
    物体画素の 99.5 パーセンタイルが 0.95 に来る露出(決定的)。``exposure='median'`` は
    **照らされた面の中央値**(物体画素のうち 99.5 % 点の 30 % 以上の画素の中央値)が
    ``exposure_target``(既定 0.45)に来る露出 —— 2026-09-03 の hero が「露出過多で
    白いジャガイモ」になった対策(99.5 % 点合わせは縁まで明るい Lommel-Seeliger 面で
    中央値が 0.7 超まで上がる)。クリップ率は呼び手が測る(hero は < 0.5 % を要求)。
  * ``smooth_normals=True``: 頂点法線の Phong 補間で陰影を滑らかにする(幾何・影は不変)。
  * ``albedo_variation``: アルベドの空間むら(既定 12 %、Saito et al. 2006 の明暗地形)。
  * ``bump``: :func:`render_beauty` の ``bump``(サブファセット起伏の陰影法線摂動)。
``tint`` は平均 1 に正規化した色味。fail-closed: 引数は下位 op が検証、``exposure`` は
``'auto'`` / ``'median'`` か正の数。決定的(乱数なし)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md)

---
*Provenance: render_beauty.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
