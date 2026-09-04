---
op: scene_material
dim: optics
category: scene
in: 
out: table
examples: [virtual_machine_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# scene_material — OPTICS `scene` op

- **データ種**: `` → `table`
- **呼び出し**: `import optscene; optscene.scene_material(kind: 'str' = 'lambert', albedo=0.6, metal: 'str' = 'al', finish: 'str' = 'random', glass: 'str' = 'N-BK7', sigma_per_mm: 'float' = 0.0, roughness_um: 'float' = 0.05) -> 'dict'` (または `opsoptics.get("scene_material")`)

## 使い方

材質を 1 つ作る。``kind`` は lambert / conductor / dielectric の 3 種。

3 種しか無いのは**混ぜると黙って間違う**からで、増やすなら型を分ける
(拡散か・金属か・透明か で光線の行き先が根本的に変わる)。

lambert: ``albedo``(スカラまたは RGB 3 要素)だけを使う完全拡散。
conductor: ``metal``(``glassmirror.METALS``)の複素屈折率で色が決まり、
    ``finish``(``metalfinish.FINISHES``)で異方性ローブの幅が決まる。**色は指定しない**。
    ``roughness_um`` は面粗さ Rq [µm]。鏡面として返る割合が
    exp(-(4πσcosθ/λ)²) で決まる(Davies 1954 / Bennett-Porteus 1961)ので、
    鏡面(0.01 = 研磨)か拡散寄り(1.0 = 梨地)かはこの 1 つで決まる。
    **波長が式に入る**ので、同じ面でも光源の波長で見え方が変わる。
dielectric: ``glass``(``raytrace.glass_catalog()``)の Sellmeier 分散で屈折し、
    ``sigma_per_mm`` の Beer–Lambert で吸収する。

返り値: 上記を検証済みで格納した dict(他の scene_* op にそのまま渡す)。

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

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../../annotate/guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴
- [mv_cameras](../guides/mv_cameras.md) — 産業用カメラメーカー（センサとの紐付け・ラインスキャン / TDI）
- [mv_illumination_practice](../guides/mv_illumination_practice.md) — 照明の実務知識 — 波長・偏光・点灯方式・外光・安全
- [mv_image_sensors](../guides/mv_image_sensors.md) — 産業用イメージセンサ（現行品中心）
- [virtual_machine_vision](../guides/virtual_machine_vision.md) — 仮想マシンビジョン — パラメータの洗い出しとオブジェクト模型

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [virtual_machine_vision](../../../../examples/virtual_machine_vision.py) — `py -3.11 examples/virtual_machine_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md) · [spot_diagram](../design/spot_diagram.md)

## 同カテゴリ(`scene`)

[scene_plane](scene_plane.md) · [scene_sphere](scene_sphere.md) · [scene_box](scene_box.md) · [scene_cylinder](scene_cylinder.md) · [surface_defect](surface_defect.md) · [surface_finish](surface_finish.md) · [random_defects](random_defects.md) · [scene_difference](scene_difference.md)

---
*Provenance: optscene.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
