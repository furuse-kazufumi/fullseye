---
op: film_thickness_fit
dim: optics
category: film
in: pairs
out: table
examples: [poc_thin_film_reflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# film_thickness_fit — OPTICS `film` op

- **データ種**: `pairs` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.film_thickness_fit(spectrum, film='SIO2', substrate='SI', thickness_min_nm=0.0, thickness_max_nm=3000.0, under=(), angle_deg=0.0, na=0.0, fit_scale=False, ambient=1.0, roughness_nm=0.0)` (実装を直接呼ぶなら `import filmoptics; filmoptics.film_thickness_fit(spectrum, film='SIO2', substrate='SI', thickness_min_nm=0.0, thickness_max_nm=3000.0, under=(), angle_deg=0.0, na=0.0, fit_scale=False, ambient=1.0, roughness_nm=0.0)`、台帳から引くなら `opsoptics.get("film_thickness_fit")`)

## 使い方

反射スペクトルに転送行列のモデルをあてはめて膜厚を出す(非線形最小二乗、大域の格子探索 → 局所の精密化)。

spectrum:     ``pairs``(λ [nm], R)。
film / substrate / under: モデルの積層(材料表の鍵)。最上層 ``film`` の厚さを未知数にする。
thickness_min_nm / thickness_max_nm: 探す範囲。格子は位相が λ_min で π/8 進む刻み(局所解に落ちない)。
angle_deg / na / ambient / roughness_nm: 測定の条件(:func:`multilayer_reflectance` と同じ)。モデル側の
              条件を実測と違えると膜厚が偏る —— その偏りを測るのが PoC の章。
fit_scale:    True なら反射率の倍率 a も同時に(閉形式で)あてはめる(反射率の絶対値の校正が無い装置)。

返り値 dict: thickness_nm / rmse / scale / candidates(局所解の [(膜厚, rmse), ...] を rmse の昇順)/
  second_rmse_ratio(2 番目の候補の rmse ÷ 最良。1 に近いほど一意でない)。

★薄い膜(縞が 1 本未満)でも、絶対反射率の形から膜厚が決まる —— FFT 法が破綻する領域で使える。
ただし材料(n)を取り違えると、光学的厚さ n d を保ったまま d が n の比だけ偏る。

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

[multilayer_reflectance](multilayer_reflectance.md) · [film_color](film_color.md) · [film_thickness_fft](film_thickness_fft.md) · [film_thickness_map](film_thickness_map.md)

---
*Provenance: filmoptics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
