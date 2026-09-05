---
op: render_optscene
dim: optics
category: scene
in: table × table × table
out: rgbimage
examples: [virtual_machine_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# render_optscene — OPTICS `scene` op

- **データ種**: `table × table × table` → `rgbimage`
- **呼び出し**: `import optscene; optscene.render_optscene(scene, camera, lights, ambient: 'float' = 0.0, depth: 'int' = 2, shadows: 'bool' = True, supersample: 'int' = 1, adaptive: 'bool' = False, light_samples: 'int' = None, edge_threshold: 'float' = 0.06, saturate_at: 'float' = None, wavelength_nm: 'float' = 550.0, environment=None, environment_gain: 'float' = 1.0, environment_samples: 'int' = 12) -> 'np.ndarray'` (または `opsoptics.get("render_optscene")`)

## 使い方

**検査用**に撮る: 実在の照明器具を物理単位で置き直接光を数える(真値つき)。

見た目を作るための多重反射・環境光は入れない。きれいな絵が要るなら
:func:`render_studio` ―― **作り方が違う別の op** で、取り違えると測光の
根拠が濁る。返り値は線形 RGB の放射輝度 (H, W, 3)、トーンマップ前。

``lights`` は ``illumdesign.light_source`` の結果(1 つでも並べてもよい)。
``ambient`` は一様な環境光、``depth`` は誘電体を通す再帰の深さ、
``shadows=False`` で落ち影を切る(速いが、影がある前提の検査には使えない)。
``supersample`` は 1 画素あたりの標本を n×n に増やす ―― 実際の画素は面積を
積分するので、縁や加工目の階段状のギザギザはこれで消える(コストは n² 倍)。

大量生成のための 3 つのつまみ(**速度は生成器の機能**):
  * ``adaptive=True`` ―― まず 1 標本で撮り、**幾何の縁と輝度勾配が大きい画素だけ**
    を n×n に割る。平坦な面には標本を捨てないので、縁の質を保ったまま速くなる。
  * ``light_samples`` ―― 面光源の発光点をこの数へ間引く(重みで明るさを補正)。
    落ちるのは影の縁の柔らかさで、明るさの絶対値ではない。
  * ``saturate_at`` ―― この輝度を超える画素は精細化しない(どうせ白飛びする)。

``wavelength_nm`` は光源の波長。面粗さ σ の面が鏡面として返す割合
exp(-(4πσcosθ/λ)²) に入るので、**同じ面でも波長で見え方が変わる**。
広帯域(ハロゲン)なら数波長で撮って足す、レーザーなら単一波長で撮る。

``environment`` を渡すと、**見せる絵の作り方をここに混ぜられる**: 金属の異方性
ローブで環境を引いた分を ``environment_gain`` 倍して足す。ブラシ目の金属が
金属に見えるのは環境が目に沿って引き伸ばされて映るからで、点光源だけでは硬い
縞にしかならない(2026-09-05 のユーザー着眼)。既定は off ―― 測光の根拠が要る
検査画像に、見た目のための項を黙って混ぜないため。``optscene.env_studio`` を
渡すのが手軽で、自前の関数((...,3) 方向 -> (...,) 明るさ)でもよい。

表示用に丸めたい場合は自分で ``**(1/2.2)`` する。実レンズの歪曲・PSF・
周辺光量・センサ雑音を足すには ``lensimage.render_through_lens`` を後段に、
量子化と読み出し雑音だけなら ``sensor_capture`` を後段に掛ける。

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

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[clearcoat_shade](../material/clearcoat_shade.md) · [wetness](../material/wetness.md) · [defocus_blur](defocus_blur.md) · [diffraction_blur](diffraction_blur.md) · [sensor_capture](sensor_capture.md)

## 同カテゴリ(`scene`)

[scene_material](scene_material.md) · [scene_plane](scene_plane.md) · [scene_sphere](scene_sphere.md) · [scene_box](scene_box.md) · [scene_cylinder](scene_cylinder.md) · [surface_defect](surface_defect.md) · [surface_finish](surface_finish.md) · [random_defects](random_defects.md)

---
*Provenance: optscene.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
