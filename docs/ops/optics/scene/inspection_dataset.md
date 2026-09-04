---
op: inspection_dataset
dim: optics
category: scene
in: table × table × table
out: table
examples: [virtual_machine_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# inspection_dataset — OPTICS `scene` op

- **データ種**: `table × table × table` → `table`
- **呼び出し**: `import optscene; optscene.inspection_dataset(scene, camera, lights, n: 'int' = 8, seed: 'int' = 0, exposure_ms: 'float' = 10.0, bit_depth: 'int' = 8, jitter_mm: 'float' = 0.0, tilt_jitter_deg: 'float' = 0.0, intensity_jitter: 'float' = 0.0, depth: 'int' = 1, defects: 'dict' = None, supersample: 'int' = 1, adaptive: 'bool' = False, light_samples: 'int' = None, environment=None, environment_gain: 'float' = 1.0) -> 'list'` (または `opsoptics.get("inspection_dataset")`)

## 使い方

外観検査 AI の**学習画像を n 枚**、画素完全なラベル付きで生成する(検査用)。

同じ部品を、照明(``lights`` に複数渡すと 1 枚ごとに巡回)・置き方
(``jitter_mm`` の並進、``tilt_jitter_deg`` のカメラ傾き)・明るさ
(``intensity_jitter`` の相対ゆらぎ)を振って撮る = ドメインランダム化。

返り値は 1 枚あたり dict:
  ``image`` 量子化済み (H, W, 3) / ``defect_mask`` 欠陥の真値 /
  ``part_mask`` 部品の真値 / ``depth_mm`` 深度の真値 /
  ``meta`` 使った照明種別・露光・ゆらぎ量・欠陥ラベル(再現に必要な値をすべて)。

``defects`` に :func:`random_defects` の引数 dict を渡すと、**1 枚ごとに
欠陥を引き直す**(``scene`` の先頭を対象にする)。これが外観検査 AI の学習
データ生成そのもので、欠陥の種類・位置・大きさ・深さと照明が同時に振れる。

``seed`` を固定すれば決定的。**同じ欠陥でも照明を変えると見え方が変わる**
ことがこの生成器の要点で、だから照明を振った枚数が効く。

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

[scene_material](scene_material.md) · [scene_plane](scene_plane.md) · [scene_sphere](scene_sphere.md) · [scene_box](scene_box.md) · [scene_cylinder](scene_cylinder.md) · [surface_defect](surface_defect.md) · [surface_finish](surface_finish.md) · [random_defects](random_defects.md)

---
*Provenance: optscene.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
