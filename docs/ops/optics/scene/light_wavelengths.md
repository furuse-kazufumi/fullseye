---
op: light_wavelengths
dim: optics
category: scene
in: table
out: pairs
examples: [vision_layout_from_catalog]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# light_wavelengths — OPTICS `scene` op

- **データ種**: `table` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.light_wavelengths(light: 'dict', samples: 'int' = 5)` (実装を直接呼ぶなら `import optscene; optscene.light_wavelengths(light: 'dict', samples: 'int' = 5)`、台帳から引くなら `opsoptics.get("light_wavelengths")`)
- **台帳経由の戻り値**: `fullseye.ledger.light_wavelengths(...)` は**宣言 out 型 `pairs` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.light_wavelengths.raw(...)`、または `optscene.light_wavelengths` を直接呼ぶ。

## 使い方

光源のスペクトルを、撮像に使う数本の波長と重みに落とす。

レーザー = 1 本、LED = 狭帯域を数本、ハロゲン = 広帯域を数本。同じ面でも
波長で鏡面/散乱の配分が変わるので、広帯域は**重ね合わせて**撮るのが正しい。

スペクトルの形(2026-10-15 から実形状): LED は Ohno 2005 のモデル(``spectralrad.led_spectrum``、
半値全幅 = ``bandwidth_nm``、峰 ± 1.5 半値全幅で切る)、ハロゲンは Planck の黒体
(``spectralrad.blackbody_spectrum``、``color_temperature_k`` 既定 3000 K、峰は Wien の変位則で約 966 nm)を
``band_nm``(既定 380〜1100 nm、Si が感じる範囲)で切ったもの、レーザーは 1 本。``light_spec`` の
``band_nm`` で帯域を変えられる。2026-10-15 まではハロゲンを 600 ± 150 nm のガウスで代用していた
(3000 K の黒体の峰は 966 nm なので、近赤外の光の大半を落としていた)。

手順: 帯域を ``k = max(samples, 1)`` 個の等幅の区間に分け、各区間の**エネルギー**
∫ S(λ) dλ を重み、区間内のエネルギー重心を波長にする。重みは和が 1。``k == 1`` なら帯域全体の
重心 1 本(LED は峰、ハロゲンは重心)。レーザー・帯域 0 は ``λ`` 1 本・重み 1。
重みはエネルギーの割合で、光子数への換算(λ/hc)と QE は ``layout_capture(mode="spectral")`` が掛ける。

- ``light``: ``light_spec`` の結果(dict)。キーが無ければ既定値で進む(dict でなければ
  ``ValueError``。sort ``table`` の行リストが流れ込むのを止める)。
- ``samples``: 本数。既定 5。1 未満は 1 に丸める。
- 返り値: ``(wavelengths (k,), weights (k,))`` の 2 本の float64 配列(台帳の型 pairs へは
  ``opsoptics.call`` の adapter が (k, 2) に揃える)。

``layout_capture`` が ``spectral_samples`` 本でこれを呼び、波長ごとの結果を
この重みで足し合わせる。

空の入力(``light`` が空の dict)は ValueError。

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

- [vision_layout_from_catalog](../../../../examples/vision_layout_from_catalog.py) — `py -3.11 examples/vision_layout_from_catalog.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[mtf50](../imaging/mtf50.md) · [energy_to_photons](../spectral/energy_to_photons.md) · [spectral_product](../spectral/spectral_product.md) · [spectral_integral](../spectral/spectral_integral.md) · [spectral_stats](../spectral/spectral_stats.md) · [kubelka_munk_reflectance](../spectral/kubelka_munk_reflectance.md) · [hyperspectral_capture](../spectral/hyperspectral_capture.md) · [film_thickness_fft](../film/film_thickness_fft.md)

## 同カテゴリ(`scene`)

[scene_material](scene_material.md) · [scene_plane](scene_plane.md) · [scene_sphere](scene_sphere.md) · [scene_box](scene_box.md) · [scene_cylinder](scene_cylinder.md) · [surface_defect](surface_defect.md) · [surface_finish](surface_finish.md) · [random_defects](random_defects.md)

---
*Provenance: optscene.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
