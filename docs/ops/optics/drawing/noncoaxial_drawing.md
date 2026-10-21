---
op: noncoaxial_drawing
dim: optics
category: drawing
in: table
out: table
examples: [poc_noncoaxial_optics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# noncoaxial_drawing — OPTICS `drawing` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.noncoaxial_drawing(system, fields=None, rays=3, view='yz', scale=None, title=None, profile_points=61, rotate_deg=0, overlays=None)` (実装を直接呼ぶなら `import optdraw; optdraw.noncoaxial_drawing(system, fields=None, rays=3, view='yz', scale=None, title=None, profile_points=61, rotate_deg=0, overlays=None)`、台帳から引くなら `opsoptics.get("noncoaxial_drawing")`)

## 使い方

折り返した系の断面図・設置図(``table``、図の dict)—— ``raytrace3d`` の系の面・鏡・半透鏡・像面・光線を、
大域の座標で子午面に投影して描く。

*system* は ``raytrace3d.noncoaxial_system`` の系(``raytrace.lens_system`` の処方も受ける)。*view* は投影面:
``"yz"``(横軸 = 大域の z、縦軸 = y。x 軸まわりの折り返しはこの面に載る)/ ``"zx"``(横軸 z、縦軸 x)。
面は局所の子午面の sag 曲線(``raytrace`` の円錐 + 非球面の式)を大域へ写して投影し、ガラスの群はコバの線で
閉じ、鏡は裏に斜線、半透鏡は ``BS`` の印。光軸は座標系の原点の折れ線(細い一点鎖線)、絞りは口径の外の刻み、
像面は像の座標系の線分(``image_tilt`` で傾く)、有限の物体は物面の線分(``object_tilt`` で傾く)。光線は視野
ごとに色を分け、絞りの上で等間隔に**絞りを狙った**実光線(``raytrace3d`` の Newton 法)。

*rotate_deg*(0 / 90 / 180 / 270)は紙の上で図を回す(同軸落射のように光が下から上へ進む装置を立てて描く)。
*overlays* は別の系(例: 照明の枝 = 半透鏡で反射する系)の列で、その光線を照明の光線の層に重ねて描く
(面は細線)。

寸法: 装置の占有の幅 ``W`` と高さ ``H``(面・像面・光線の外接矩形)。注記: 光路長(第 1 面 → 像面の軸の長さ)、
折り返しの角度。``values``: ``path_length`` / ``footprint`` / ``fold_angles_deg`` / 面ごとの大域の頂点
``surfaces`` / 光線の大域の折れ線 ``rays`` / ``image_center``。

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_noncoaxial_optics](../../../../examples/poc_noncoaxial_optics.py) — `py -3.11 examples/poc_noncoaxial_optics.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`drawing`)

[lens_section_drawing](lens_section_drawing.md) · [vision_setup_drawing](vision_setup_drawing.md) · [lens_element_drawing](lens_element_drawing.md) · [drawing_svg](drawing_svg.md) · [drawing_dxf](drawing_dxf.md) · [drawing_raster](drawing_raster.md) · [svg_entities](svg_entities.md) · [dxf_entities](dxf_entities.md)

---
*Provenance: optdraw.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
