---
op: weave_normals
dim: optics
category: surface
in: 
out: normalmap
examples: [machined_metal_and_materials]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# weave_normals — OPTICS `surface` op

- **データ種**: `なし` → `normalmap`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import surfacelib; surfacelib.weave_normals(shape, warp_px=8.0, weft_px=8.0, depth=0.25, angle_deg=0.0) -> 'np.ndarray'` (または `opsoptics.get("weave_normals")`)

## 使い方

織り目の法線場(布・カーボンファイバー・金網)。直交する 2 周期の畝。

shape: (H, W)。warp_px / weft_px: 経糸 / 緯糸の間隔 [px]。depth: 畝の深さ。
angle_deg: 織りの向き [deg]。

返り値: (H, W, 3) の単位法線場。**2 方向に周期がある**のが要点(FFT に 2 本の
ピークが立つ、テストで確認)。カーボンは warp/weft を変えて綾織りにする。

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

- [machined_metal_and_materials](../../../../examples/machined_metal_and_materials.py) — `py -3.11 examples/machined_metal_and_materials.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[grating_rgb](../appearance/grating_rgb.md) · [thin_film_rgb](../appearance/thin_film_rgb.md) · [ward_anisotropic](../appearance/ward_anisotropic.md) · [micro_normals](../finish/micro_normals.md) · [blast_normals](../finish/blast_normals.md) · [finish_shade](../finish/finish_shade.md) · [oren_nayar](../material/oren_nayar.md) · [clearcoat_shade](../material/clearcoat_shade.md)

## 同カテゴリ(`surface`)

[metallic_flake_normals](metallic_flake_normals.md) · [wood_grain](wood_grain.md) · [corrosion_mask](corrosion_mask.md) · [rough_transmission](rough_transmission.md)

---
*Provenance: surfacelib.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
