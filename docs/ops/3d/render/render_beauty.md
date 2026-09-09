---
op: render_beauty
dim: 3d
category: render
in: mesh
out: rgbimage
examples: [anatomical_hand, render_beauty]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# render_beauty — 3D `render` op

- **データ種**: `mesh` → `rgbimage`
- **呼び出し**: `import fullseye as fs; fs.ledger.render_beauty(V, F, *, pose=None, intrinsics=None, size: 'int' = 512, ss: 'int' = 2, light: 'Sequence[float]' = (0.3, 0.4, 1.0), albedo: 'Sequence[float]' = (0.8, 0.8, 0.85), material: 'str' = 'plastic', matcap=None, ambient: 'float' = 0.12, ao: 'bool' = True, ground_shadow: 'bool' = True, tonemap: 'str' = 'reinhard', background: 'Sequence[float]' = (0.1, 0.11, 0.13), exposure: 'float' = 1.0, shininess: 'Optional[float]' = None, ao_samples: 'int' = 32, shadow_res: 'int' = 512, penumbra: 'float' = 2.5, shadow_samples: 'int' = 12, shadow_pcf: 'int' = 1, brdf: 'str' = 'phong', brdf_params=None, shadow_method: 'str' = 'map', sun_angular_diameter_deg: 'float' = 0.0, self_illumination: 'float' = 0.0, albedo_variation: 'float' = 0.0, albedo_scale=None, seed: 'int' = 0, smooth_normals: 'bool' = False, bump=None, vertex_normals=None, vertex_albedo=None, surface: 'str' = 'none', surface_params=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import render_beauty; render_beauty.render_beauty(V, F, *, pose=None, intrinsics=None, size: 'int' = 512, ss: 'int' = 2, light: 'Sequence[float]' = (0.3, 0.4, 1.0), albedo: 'Sequence[float]' = (0.8, 0.8, 0.85), material: 'str' = 'plastic', matcap=None, ambient: 'float' = 0.12, ao: 'bool' = True, ground_shadow: 'bool' = True, tonemap: 'str' = 'reinhard', background: 'Sequence[float]' = (0.1, 0.11, 0.13), exposure: 'float' = 1.0, shininess: 'Optional[float]' = None, ao_samples: 'int' = 32, shadow_res: 'int' = 512, penumbra: 'float' = 2.5, shadow_samples: 'int' = 12, shadow_pcf: 'int' = 1, brdf: 'str' = 'phong', brdf_params=None, shadow_method: 'str' = 'map', sun_angular_diameter_deg: 'float' = 0.0, self_illumination: 'float' = 0.0, albedo_variation: 'float' = 0.0, albedo_scale=None, seed: 'int' = 0, smooth_normals: 'bool' = False, bump=None, vertex_normals=None, vertex_albedo=None, surface: 'str' = 'none', surface_params=None) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("render_beauty")`)

## 使い方

メッシュを全品質層合成で「映える静止 3D」1 枚に描く → RGB ``(size, size, 3)`` float [0,1]。

引数:
  * ``V, F``        頂点 (N,3) と三角形 (M,3)。
  * ``pose``        4x4 object->camera(``render3d.look_at``)。None で ``auto_view``。
  * ``intrinsics``  3x3 ピンホール ``K``(**目標 ``size`` 用**、内部で ``ss`` 倍にスケール)。
  * ``size``        出力の一辺(正方)。``ss``  スーパーサンプリング倍率(整数 >= 1)。
  * ``light``       **ワールド座標**の光源方向(シーン→光源)。陰影と接地影で共有。
  * ``albedo``      物体の反射色 RGB。``material``  ``'plastic'`` | ``'metal'`` | ``'matcap'``。
  * ``matcap``      ``material='matcap'`` のとき必須の lit-sphere テクスチャ ``(h,w[,C])``。
  * ``ambient``     環境光係数。``ao``  アンビエントオクルージョンを掛けるか。
  * ``ground_shadow`` 地面平面 + 接地影を焼き込むか。
  * ``tonemap``     ``'reinhard'`` | ``'aces'`` | ``'none'``。``background``  背景色 RGB。
  * ``exposure``    トーンマップ前の露出。``shininess``  光沢(None でマテリアル既定)。
  * ``ao_samples`` / ``shadow_res`` / ``penumbra`` / ``shadow_samples``
                    品質・速度のチューニング(接地影のソフトさ等)。
                    **``penumbra`` は光源の角半径 [度]** で、半影の幅はおよそ
                    「遮蔽物の高さ × tan(penumbra)」。既定の 2.5 度は、地面から
                    1 単位の高さの物体で半影が **1〜2 画素**にしかならない
                    (2026-09-02 実測: 320px の絵で半影は 283/102400 画素、
                    値の種類は ``shadow_samples+1`` の 7 段だけ)。柔らかい影が
                    欲しいなら 10 度前後まで上げ、段が見えないよう
                    ``shadow_samples`` も一緒に増やす。
  * ``shadow_pcf``  shadow map を引くときに混ぜる近傍半径 [texel] (既定 1 = 3x3)。
                    1 点参照だと影の境目が texel に量子化されて階段になる。
                    実測(地面の上だけで測った隣接画素の最大変化):
                    既定 2.5 度・12 本・pcf=0 相当で **0.667**、
                    12 度・24 本・pcf=1 で **0.176**(1/6 を超える段は 123→2)。

  * ``brdf``        物体の反射則。``'phong'``(既定 = 従来どおり Lambert 拡散 + cos^n 鏡面)/
                    ``'lambert'`` / ``'lommel_seeliger'`` / ``'hapke'``(惑星測光、
                    ``render_shade.brdf_shade``)。phong 以外では鏡面を切り、``albedo`` は
                    平均 1 に正規化した**色味**として掛ける(明るさは ``brdf_params`` の
                    単一散乱アルベド ``w`` が決める。二重に掛けない)。
  * ``brdf_params`` ``dict``(``w, g, B0, h, roughness_deg, multiple_scattering``)。
  * ``shadow_method`` ``'map'``(既定 = shadow map + PCF)/ ``'raycast'``
                    (``render_shadow.shadow_raycast``、階段・acne 無し)。
  * ``sun_angular_diameter_deg`` raycast 時の光源視直径(太陽 0.53°)。半影の幅は
                    「遮蔽物までの距離 × tan(視直径/2)」= 小惑星では数 cm(硬い影)。
  * ``self_illumination`` 地形からの一回反射の近似係数(既定 0)。
                    ``bounce = 係数 × albedo色 × (1 − AO) × 照らされた面の平均放射輝度``
                    ―― 遮蔽された半球の分だけ隣の地形が見えており、その地形が平均的な
                    明るさで光っているという近似(相互反射の厳密解ではない、要 ``ao=True``)。
                    宇宙では環境光が無いので ``ambient=0`` とこれで影の底が決まる。
  * ``bump``        ``dict(wavelengths, amplitudes[, seed, nyquist, fade, complement_edges])``
                    → 物体画素の陰影法線を :func:`render3d.bump_normals_fbm`(値ノイズ高さ場の
                    勾配)で摂動する。幾何(depth/影/AO)は不変。``complement_edges=True``
                    なら画素直下のメッシュ局所辺長を重心補間して渡し、変位の帯域ゲートの
                    **補集合**だけを bump にする(同じ波長を二重に足さない)。

fail-closed: 形状不正・非有限・空・``ss<1``・不正 ``material``/``tonemap``・不正な色/光/露出は
``ValueError``。決定的(乱数なし)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [anatomical_hand](../../../../examples_3d/anatomical_hand.py) — `py -3.11 examples_3d/anatomical_hand.py`
- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md)

---
*Provenance: render_beauty.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
