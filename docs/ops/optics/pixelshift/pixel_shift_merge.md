---
op: pixel_shift_merge
dim: optics
category: pixelshift
in: video × matrix
out: rgbimage
examples: [poc_pixel_shift, poc_simcal_pixel_shift]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# pixel_shift_merge — OPTICS `pixelshift` op

- **データ種**: `video × matrix` → `rgbimage`
- **呼び出し**: `import fullseye as fs; fs.ledger.pixel_shift_merge(frames, shifts, pattern='RGGB', scale=1, motion_threshold=0.0, noise_sigma=0.0)` (実装を直接呼ぶなら `import pixelshift; pixelshift.pixel_shift_merge(frames, shifts, pattern='RGGB', scale=1, motion_threshold=0.0, noise_sigma=0.0)`、台帳から引くなら `opsoptics.get("pixel_shift_merge")`)

## 使い方

ピクセルシフトの枚を、**公称の**シフトで格子へ振り分けて合わせる。補間はしない(同じ格子点の標本の平均だけ)。

*frames*: ``(N, H, W)`` の生の画像(:func:`pixel_shift_capture` の返り値、Bayer か白黒)。
*shifts*: ``(N, 2)`` の**公称の**シフト(:func:`pixel_shift_pattern` を ``error_px=0`` で)。1/scale 画素の格子に
乗っていなければ拒否する(任意のずれは ``astrostack.drizzle_resample``)。
*pattern*: Bayer の並び(``None`` = 白黒)。
*scale*: 1 = 同じ格子(1 画素シフト 4 枚 → 各画素に R・G・B)、2 = 半画素の格子(half4 / 16shot)。
*motion_threshold*: > 0 なら :func:`pixel_shift_motion_mask` で動いた格子点を見つけ、そこ(と 8 近傍)だけを
シフト (0, 0) の 1 枚から作った像(Bayer は ``gfx2d.raw_demosaic_bilinear``)に差し戻す —— 動いた所は
「ピクセルシフトしなかった」画質に戻るが、櫛状の破綻は消える。0 なら差し戻さない。
*noise_sigma*: 動き検出の雑音 σ(0 = 推定)。

返り値: ``(H·scale, W·scale, 3)``(Bayer)/ ``(H·scale, W·scale)``(白黒)の float64。

端の扱い: シフトのぶん、格子の端(最大シフトの幅)にはどの枚の標本も来ない色がある。そこは (0, 0) の 1 枚から
作った像で埋める(黙って 0 にしない)。**内側**に標本の来ない格子点・色があれば(例: 1 画素シフト 4 枚を
scale=2 で合わせる、2 枚だけの Bayer)、このシフト列では格子を埋められないので ``ValueError``。

**Raises** ``ValueError``: frames・shifts の形・非有限 / 格子に乗らないシフト / scale が 1〜4 でない /
内側の格子点に標本の来ない色がある / motion_threshold > 0 なのにシフト (0, 0) の枚が無い・動きを検出できない。

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

- [poc_pixel_shift](../../../../examples/poc_pixel_shift.py) — `py -3.11 examples/poc_pixel_shift.py`
- [poc_simcal_pixel_shift](../../../../examples/poc_simcal_pixel_shift.py) — `py -3.11 examples/poc_simcal_pixel_shift.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[clearcoat_shade](../material/clearcoat_shade.md) · [wetness](../material/wetness.md) · [defocus_blur](../scene/defocus_blur.md) · [diffraction_blur](../scene/diffraction_blur.md) · [sensor_capture](../scene/sensor_capture.md) · [pixel_shift_capture](pixel_shift_capture.md) · [false_color_metric](false_color_metric.md)

## 同カテゴリ(`pixelshift`)

[pixel_shift_pattern](pixel_shift_pattern.md) · [pixel_shift_capture](pixel_shift_capture.md) · [pixel_shift_motion_mask](pixel_shift_motion_mask.md) · [false_color_metric](false_color_metric.md) · [pixel_shift_resolution_budget](pixel_shift_resolution_budget.md)

---
*Provenance: pixelshift.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
