---
op: film_thickness_map
dim: optics
category: film
in: images
out: table
examples: [poc_thin_film_reflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# film_thickness_map — OPTICS `film` op

- **データ種**: `images` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.film_thickness_map(images, wavelengths_nm=(450.0, 500.0, 550.0, 600.0, 650.0, 700.0), film='SIO2', substrate='SI', thickness_min_nm=0.0, thickness_max_nm=1500.0, mode='spectral', under=(), ambiguity_rms=0.01, step_nm=1.0, normalize=False, chunk=4096)` (実装を直接呼ぶなら `import filmoptics; filmoptics.film_thickness_map(images, wavelengths_nm=(450.0, 500.0, 550.0, 600.0, 650.0, 700.0), film='SIO2', substrate='SI', thickness_min_nm=0.0, thickness_max_nm=1500.0, mode='spectral', under=(), ambiguity_rms=0.01, step_nm=1.0, normalize=False, chunk=4096)`、台帳から引くなら `opsoptics.get("film_thickness_map")`)

## 使い方

分光画像(帯域ごとの反射率)か RGB 画像から、画素ごとの膜厚を出す(早見表 + 放物線の精密化)。

images:          (B, H, W) の帯域画像の列。``mode="spectral"`` なら各帯域は ``wavelengths_nm`` の波長での
                 反射率(狭帯域の分光カメラ)、``mode="srgb"`` なら B = 3 で :func:`film_color` と同じ
                 線形 sRGB(D65・CIE 1931 の等色関数、Luther 条件を満たす理想の RGB カメラ)。
wavelengths_nm:  分光モードの帯域の中心 [nm] (B 個、昇順)。srgb モードでは使わない。
film / substrate / under: 積層(材料表の鍵)。最上層 ``film`` の厚さを求める。
thickness_min_nm / thickness_max_nm / step_nm: 早見表の膜厚の範囲と刻み。
ambiguity_rms:     「同じくらい合う候補」の閾: 画素の RMS 残差が最良 + この値以下の局所解を数える。
                 既定 0.01 は反射率 1 % の雑音の目安。
normalize:       True なら画素と早見表をどちらも長さ 1 に揃えてから比べる(明るさ = 照明・露出・反射率の倍率が
                 分からないときに、色の向き(分光の形)だけで照合する)。rmse は長さ 1 の単位になる。
chunk:           1 回に照合する画素の数(メモリの上限)。

返り値 dict: thickness (H, W) / rmse (H, W) / n_candidates (H, W)(閾の中に入った局所解の数。
  ★1 より大きい画素は**色(帯域)だけでは膜厚が決まらない** —— RGB では色が膜厚について周期的に繰り返すので
  ここが 2 以上になる)/ lut_thickness_nm(早見表の膜厚)。

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

- [poc_thin_film_reflectometry](../../../../examples/poc_thin_film_reflectometry.py) — `py -3.11 examples/poc_thin_film_reflectometry.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`film`)

[multilayer_reflectance](multilayer_reflectance.md) · [film_color](film_color.md) · [film_thickness_fft](film_thickness_fft.md) · [film_thickness_fit](film_thickness_fit.md)

---
*Provenance: filmoptics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
