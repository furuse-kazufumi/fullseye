---
op: film_color
dim: optics
category: film
in: 
out: table
gpu: なし
examples: [poc_thin_film_reflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# film_color — OPTICS `film` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.film_color(film='SIO2', substrate='SI', thickness_min_nm=0.0, thickness_max_nm=1000.0, n_points=101, under=(), angle_deg=0.0, na=0.0, wl_min_nm=380.0, wl_max_nm=780.0, ambient=1.0, exposure=1.0, illuminant=None)` (実装を直接呼ぶなら `import filmoptics; filmoptics.film_color(film='SIO2', substrate='SI', thickness_min_nm=0.0, thickness_max_nm=1000.0, n_points=101, under=(), angle_deg=0.0, na=0.0, wl_min_nm=380.0, wl_max_nm=780.0, ambient=1.0, exposure=1.0, illuminant=None)`、台帳から引くなら `opsoptics.get("film_color")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

膜厚を振ったときの干渉色(ウェハの色見本)。D65 の照明・CIE 1931 の等色関数で見た色を返す。

film:       膜の材料(材料表の鍵など)。``under`` があればその上に乗る最上層。
substrate:  基板。
thickness_min_nm / thickness_max_nm / n_points: 膜厚の格子。
under:      膜と基板の間の層 ``[(材料, 厚さ nm), ...]``(入射側から順)。
angle_deg / na / ambient: :func:`multilayer_reflectance` と同じ。
wl_min_nm / wl_max_nm: 色を積む波長の範囲(既定 380〜780 nm。材料表の範囲が足りなければ ValueError)。
exposure:   線形 sRGB に掛ける露出(見本を明るく見せたいとき。CIELAB と色相は露出 1 の値)。
illuminant: 照明の分光分布 ``pairs``(λ [nm], 相対値)。None は D65(``matappear`` の平滑近似)。
            白(反射率 1)が sRGB の白に落ちるよう同じ照明で正規化する(白色順応)。輝線の多い蛍光灯では
            厚い膜の色が残る —— 連続光では縞が帯域内で平均されて灰色に近づく。

返り値 dict:
  thickness_nm (N,) / reflectance (N, K) と wavelength_nm (K,) / linear_srgb (N, 3)(白 = 1、負は色域外)/
  srgb (N, 3)(ガンマ済み・0〜1 に切った表示用)/ lab (N, 3)(CIELAB、白 = D65)/ hue_deg (N,)(a*b* の色相角)/
  chroma (N,)。

★色は膜厚について**周期的に繰り返す**(SiO₂ on Si では光学的厚さ n d が約 λ/2 ≈ 190 nm 進むごとに似た色に戻る)
—— 色だけでは膜厚が一意に決まらない(:func:`film_thickness_map` の ``n_candidates``)。

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

[multilayer_reflectance](multilayer_reflectance.md) · [film_thickness_fft](film_thickness_fft.md) · [film_thickness_fit](film_thickness_fit.md) · [film_thickness_map](film_thickness_map.md)

---
*Provenance: filmoptics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
