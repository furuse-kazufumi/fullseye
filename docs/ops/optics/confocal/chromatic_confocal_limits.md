---
op: chromatic_confocal_limits
dim: optics
category: confocal
in: table
out: table
gpu: なし
examples: [poc_chromatic_confocal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# chromatic_confocal_limits — OPTICS `confocal` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.chromatic_confocal_limits(probe, layer_material=None, tilt_max_deg: 'float' = 30.0, n_tilt: 'int' = 61) -> 'dict'` (実装を直接呼ぶなら `import chromconf; chromconf.chromatic_confocal_limits(probe, layer_material=None, tilt_max_deg: 'float' = 30.0, n_tilt: 'int' = 61) -> 'dict'`、台帳から引くなら `opsoptics.get("chromatic_confocal_limits")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

較正表から、測定範囲・軸方向分解能・戻る傾きの上限・最小の膜厚を閉形式で出す。

* ``range_um`` —— 較正表の端から端(焦点ずれの総量)。
* ``fwhm_closed_um`` / ``fwhm_um`` —— 鏡面応答の FWHM(無収差の閉形式 0.4430 λ/(1 − cos α) と、
  縦球面収差込みの数値)を帯域の両端と中央で。``range_over_fwhm`` は目盛の数(範囲 / 中央の FWHM)。
* ``max_tilt_deg`` —— 鏡面の傾きの上限(各波長の NA で sin 2θ = 2NA)。最小(最も厳しい)値。
* ``tilt_return`` —— 中央の波長の NA で、傾き 0〜*tilt_max_deg* に対する戻る光の割合(pairs)。
* ``min_thickness_um`` —— 等しい 2 つの鏡面応答が Sparrow の基準で分かれる見かけの間隔
  (:data:`SPARROW_FRACTION` × FWHM)に、層の n(λ) と平板の球面収差の補正を掛けた最小の厚さ
  (中央の波長)。干渉を入れない強度の重なりだけの限界(モジュールの開示を参照)。

**Raises** ``ValueError``: probe の形の誤り、材料表の外、tilt_max_deg が (0, 89] の外。

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

- [poc_chromatic_confocal](../../../../examples/poc_chromatic_confocal.py) — `py -3.11 examples/poc_chromatic_confocal.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`confocal`)

[chromatic_confocal_probe](chromatic_confocal_probe.md) · [confocal_axial_response](confocal_axial_response.md) · [chromatic_confocal_spectrum](chromatic_confocal_spectrum.md) · [chromatic_confocal_peaks](chromatic_confocal_peaks.md) · [chromatic_confocal_readout](chromatic_confocal_readout.md)

---
*Provenance: chromconf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
