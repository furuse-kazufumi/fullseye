---
id: optics-drawings
title: 光学系の図面(レンズ断面図・撮像系の設置図・単レンズの製作図を SVG / DXF で)
title_en: Optical drawings (lens layouts, vision-setup drawings and ISO 10110 element drawings as SVG / DXF)
category: 描く
ops: [lens_section_drawing, vision_setup_drawing, lens_element_drawing, drawing_svg, drawing_dxf, drawing_raster, svg_entities, dxf_entities]
examples: [poc_optics_drawings]
version: 0.6.1
inputs: [table]
pipeline: [lens_section_drawing, drawing_svg, drawing_dxf, svg_entities, dxf_entities]
alternatives: [vision_setup_drawing, lens_element_drawing, drawing_raster, paraxial_trace, tolerance_analysis]
limits: 鏡・傾き・偏心のある処方の断面図、接合レンズと非球面の製作図は描かない(ValueError)。製作図の ISO 10110 の表記は公開の解説で確かめた範囲。設置図の鏡筒とカメラ本体の大きさは仮の寸法で、作動距離は物体から主点まで(薄肉の模型)。
calibration: 図は計算値そのものを実寸の mm で描くので、尺度の校正は要らない。SVG は紙の大きさ = 図 × 縮尺(100 % 表示・印刷で縮尺どおり)、DXF はモデル空間の 1 単位 = 1 mm。
---

# 光学系の図面(レンズ断面図・撮像系の設置図・単レンズの製作図を SVG / DXF で)

## できること

`raytrace` の処方(`lens_system` の table)と `optscene.vision_layout` の撮像系から、打ち合わせと製作に使う図を出します。`lens_section_drawing` はレンズの子午断面図で、面は処方の円錐 + 非球面の sag、コバと平らな座、絞り、像面、視野ごとに色を分けた実光線(絞りを狙って追跡するので、入射瞳が無限遠のテレセンでも描けます)、EFL・BFL・全長・像高の寸法線、処方表を描きます。`vision_setup_drawing` は側面図と上面図で、カメラ・視野の錐・作動距離・被写界深度の帯と、照明 5 種(リング・ドーム・バー・同軸・バックライト)の位置と仰角を寸法つきで描きます。`lens_element_drawing` は単レンズの製作図で、ISO 10110 の 3 分割の表(左の面・材料・右の面)に R・有効径・3/ 4/ 5/、n_d・ν_d と 0/ 1/ 2/ を書き、公差は `tolerance_analysis` の公差の辞書から写して EFL の Monte-Carlo の幅を注記に残します。

`drawing_svg` は stdlib だけで SVG を書き、紙の大きさが図 × 縮尺なので 100 % 表示・印刷で縮尺どおりです。`drawing_dxf` は DXF R12(AC1009)の ASCII を書き、層・線種(一点鎖線・破線)つきで CAD に持ち込めます。`svg_entities` / `dxf_entities` は書いた図から座標と文字を読み戻し、`drawing_raster` は matplotlib(任意依存)で画像にします。

PoC `poc_optics_drawings` は、図を書いたファイルから読み戻した面の座標・光線の折れ点・寸法の数字を、球面の sag の閉形式・`raytrace.chief_ray`・`paraxial_trace`・教科書の Cooke triplet の公表 EFL と突き合わせ、壊した図で門が赤になることも確かめます。

## What it does

Eight ops in `optdraw` (category `drawing` of `opsoptics`) that draw what the optics ops compute: a meridional lens layout from a `raytrace` prescription (conic + aspheric sags, edges, stop, image plane, real rays aimed at the stop and coloured by field, EFL / BFL / track / image-height dimensions, a prescription table), a side + top view of a machine-vision setup from `vision_layout` (field-of-view cone, working distance, depth-of-field band, five light families with positions and elevation angles), and an ISO 10110-style element drawing whose tolerances come from the `tolerance_analysis` dictionary. Writers for SVG and DXF R12 use only the standard library; readers bring coordinates and text back so the gates score the written file, not the picture.

## 向くところ / 向かないところ

**向く**: 光学系の打ち合わせ資料、検査装置の設置図(作動距離・視野・照明の角度)のたたき台、レンズの製作の見積りに出す単レンズの図、CAD(DXF)への持ち込み、計算結果と図の数字を一致させたままの資料づくり。

**向かない**: ★鏡・傾き・偏心のある処方の断面図、接合レンズや非球面の製作図(ISO 10110-12 の sag の表)は描きません(ValueError)。製作図の表記は公開の解説で確かめた範囲で、規格の全項目(6/ のレーザー損傷、コーティング)は欄だけです。設置図の鏡筒とカメラ本体の大きさは `lens_spec` に無いので仮の寸法、作動距離は薄肉の模型どおり物体から主点までです。

## 推奨パイプライン

`lens_section_drawing` → `drawing_svg` → `drawing_dxf` → `svg_entities` → `dxf_entities`

`raytrace.lens_system` の処方から `lens_section_drawing` で断面図の dict を組み → `drawing_svg` で打ち合わせ用の SVG → `drawing_dxf` で CAD に持ち込む DXF → `svg_entities` / `dxf_entities` で書いたファイルを読み戻し、面の座標と寸法の数字を計算値に突き合わせる(図を配る前の検査)。

## 代替

装置の設置図は `vision_setup_drawing`(`optscene.vision_layout` から)、単レンズの製作図は `lens_element_drawing`(公差は `tolerance_analysis` の辞書)。画像が要るなら `drawing_raster`(matplotlib 任意)。数だけでよいなら `paraxial_trace` と `tolerance_analysis`。

## 限界

- 鏡・傾き・偏心のある処方は子午断面の 2-D 図に正しく載らないので拒否する。
- 製作図は単レンズの球面・平面だけ(接合レンズ、ISO 10110-12 の非球面の sag の表は無い)。
- DXF の文字は ASCII と ⌀ ° ± だけ(それ以外の文字は ValueError、∞ は INF と書く)。

## 実寸校正

図は実寸の mm で描くので校正は要らない。SVG は `width` / `height` が紙の mm(図 × 縮尺)、DXF はモデル空間の 1 単位が 1 mm。

## 最初の 1 本

```python
import optdraw as OD
import raytrace as RT

system = RT.lens_system([{"R": 51.68, "t": 5.0, "n": "BK7", "ap": 12.5},
                         {"R": float("inf"), "t": None, "n": 1.0}], stop=0, field=5.0)
d = OD.lens_section_drawing(system)                  # 子午断面図(図の dict)
open("singlet.svg", "w", encoding="utf-8").write(OD.drawing_svg(d))
open("singlet.dxf", "w", encoding="ascii", newline="").write(OD.drawing_dxf(d))
print(round(d["values"]["efl"], 2))                  # 100.0
```
