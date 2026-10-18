---
op: lens_element_drawing
dim: optics
category: drawing
in: table
out: table
examples: [poc_optics_drawings]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# lens_element_drawing — OPTICS `drawing` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lens_element_drawing(system, element=0, tolerances=None, outer_diameter_mm=None, clear_aperture_mm=None, chamfer_mm=0.2, irregularity_fringes=None, surface_imperfections=None, stress_birefringence=20.0, bubbles='1/3x0.16', inhomogeneity='2/1;1', trials=200, seed=0, radius_tolerance='radius', plane_power_fringes=2.0, scale=None, title=None)` (実装を直接呼ぶなら `import optdraw; optdraw.lens_element_drawing(system, element=0, tolerances=None, outer_diameter_mm=None, clear_aperture_mm=None, chamfer_mm=0.2, irregularity_fringes=None, surface_imperfections=None, stress_birefringence=20.0, bubbles='1/3x0.16', inhomogeneity='2/1;1', trials=200, seed=0, radius_tolerance='radius', plane_power_fringes=2.0, scale=None, title=None)`、台帳から引くなら `opsoptics.get("lens_element_drawing")`)

## 使い方

単レンズの製作図(``table``、図の dict)—— ISO 10110 の表記で、断面図と 3 分割のデータ欄と表題欄。

*system* の *element* 番目のガラス(前から 0, 1, …)を描く。データ欄は左が第 1 面、右が第 2 面、中央が材料:

* 面: ``R``(曲率半径、凸は CX・凹は CC、平面は ∞)と公差、``⌀e``(有効径)、``3/A(B)``(面形状の公差:
  A = 曲率の誤差による sag の誤差、B = 不規則性、どちらも λ = 546.07 nm の干渉縞の本数。R の公差を寸法で
  書くときは A を ``-`` にする —— ISO 10110-5 の慣行)、``4/σ``(面の傾き = 偏心の公差、分)、``5/N×A``
  (表面のきず)。
* 材料: ``n_d`` と ``ν_d``(式で評価した値。社名の硝材名は書かない)と公差、``0/``(応力複屈折 nm/cm)、
  ``1/``(泡と異物)、``2/``(不均質と脈理)。
* 図: 中心厚と公差、外径と公差、面取り(保護面取り)、光軸。

公差は ``raytrace.tolerance_analysis`` の公差の辞書(*tolerances*、既定は同じ既定値 ``radius_pct`` 0.5 /
``thickness_mm`` 0.05 / ``index`` 0.001 / ``tilt_deg`` 0.05)から写す: 中心厚 ±``thickness_mm``、``n_d``
±``index``、``4/`` = ``tilt_deg`` × 60 分、曲率の公差 ``radius_pct`` は R の ± と、有効径の縁での sag の差
``|sag(R(1 ± p)) − sag(R)|`` を縞の本数(1 本 = λ/2)にする。*radius_tolerance* = ``"radius"``(既定)は
R の欄に ±ΔR を書いて ``3/-(B)`` とし、縞の換算は注記に残す。``"fringes"`` は R を公称値だけにして
``3/A(B)`` の A に縞の本数を書く。B(不規則性、*irregularity_fringes*)の既定は ``"radius"`` で 1、
``"fringes"`` で A/4(最低 0.5)。平面は曲率の公差が無いので、A は *plane_power_fringes*(既定 2 本)。同じ公差で ``tolerance_analysis`` を回した EFL の 5〜95 % の幅を注記に入れる(*trials* 回、
*seed*)—— 図の公差が光学系の何を動かすかを製作図に残すため。

返り値の ``values``: ``R1`` / ``R2`` / ``center_thickness`` / ``outer_diameter`` / ``clear_aperture`` /
``nd`` / ``vd`` / ``fringes_power`` / ``tilt_arcmin`` / ``efl`` / ``efl_p5`` / ``efl_p95``。平面の ``R`` と、分散の
無い媒質の ``vd`` は ``inf``(非有限は契約、``lens_system`` の規約どおり)。
接合レンズ群(面が 3 つ以上のガラスの連続)は 1 枚の組図にする: 断面に各レンズと接合面、データ欄は面ごとの R・
有効径と、レンズごとの材料(n_d・ν_d)と中心厚(``values`` の ``R`` / ``center_thickness`` / ``nd`` / ``vd`` は
列)。非球面・円錐面は ISO 10110-12 の sag の表(高さ h と sag z(h)、式と係数)を図に足し、``values`` の
``sag_tables`` に同じ数を残す(門は図から読み戻して ``raytrace`` の sag の式と突き合わせる)。

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

- [poc_optics_drawings](../../../../examples/poc_optics_drawings.py) — `py -3.11 examples/poc_optics_drawings.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`drawing`)

[lens_section_drawing](lens_section_drawing.md) · [vision_setup_drawing](vision_setup_drawing.md) · [drawing_svg](drawing_svg.md) · [drawing_dxf](drawing_dxf.md) · [drawing_raster](drawing_raster.md) · [svg_entities](svg_entities.md) · [dxf_entities](dxf_entities.md) · [noncoaxial_drawing](noncoaxial_drawing.md)

---
*Provenance: optdraw.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
