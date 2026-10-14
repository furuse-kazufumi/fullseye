---
op: chromatic_confocal_probe
dim: optics
category: confocal
in: 
out: table
examples: [poc_chromatic_confocal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# chromatic_confocal_probe — OPTICS `confocal` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.chromatic_confocal_probe(surfaces=None, stop: 'int' = 0, wl_min_nm: 'float' = 450.0, wl_max_nm: 'float' = 700.0, n_points: 'int' = 26) -> 'dict'` (実装を直接呼ぶなら `import chromconf; chromconf.chromatic_confocal_probe(surfaces=None, stop: 'int' = 0, wl_min_nm: 'float' = 450.0, wl_max_nm: 'float' = 700.0, n_points: 'int' = 26) -> 'dict'`、台帳から引くなら `opsoptics.get("chromatic_confocal_probe")`)

## 使い方

対物レンズの処方から、波長 → 焦点位置の較正表(虹のものさしの目盛)を作る。

処方 *surfaces* は :func:`raytrace.lens_system` と同じ形(dict か (R, t, n[, k[, ap]]) の列、
硝材は名前で材料表を引く)。**平行光で入射**し、絞り(*stop* 番目の面)の ``ap`` がビーム半径。
既定は :data:`DEFAULT_PROBE_SURFACES`(重フリントの非球面単レンズ、f ≈ 16 mm、ビーム半径 2.5 mm)。

各波長で: 近軸の後側焦点距離(raytrace.paraxial_trace)、像側 NA、縁の光線の焦点との差
(縦球面収差 LSA、実光線)、そして **鏡を置いて応答のピークを読む較正**(縦球面収差を入れた軸応答の
ピーク位置。無収差なら近軸焦点と一致、収差があればおよそ LSA/2 ずれる)。

返り値の dict(JSON にできる): ``wavelength_nm`` / ``paraxial_um``(近軸焦点、較正の原点から)/
``calibration_um``(鏡で較正したピーク位置、最短波長で 0)/ ``lsa_um`` / ``na`` /
``efl_mm`` / ``fwhm_um``(収差込みの鏡面応答の FWHM)/ ``fwhm_closed_um``(無収差の閉形式)/
``peak_response``(無収差に対するピークの高さ)/ ``dz_dlambda_um_per_nm``(較正表の傾き)/
``range_um``(較正の範囲)/ ``range_paraxial_um`` / ``working_distance_mm``(最短波長の近軸焦点、
最終面から)/ ``origin_mm``(z = 0 の位置、最終面から)/ ``beam_radius_mm`` / ``surfaces``。

wl_min_nm / wl_max_nm / n_points: 較正する帯域と点数(4〜1024、等間隔)。

**Raises** ``ValueError``: 処方の誤り(raytrace がそのまま名指しする)、帯域が硝材の表の外、
縁の光線のけられ・全反射、焦点が無い(発散系)、**較正表が波長に対して単調でない**(同じ位置に
2 つの波長が合う = 高さが一意に決まらない)。

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

[confocal_axial_response](confocal_axial_response.md) · [chromatic_confocal_spectrum](chromatic_confocal_spectrum.md) · [chromatic_confocal_peaks](chromatic_confocal_peaks.md) · [chromatic_confocal_readout](chromatic_confocal_readout.md) · [chromatic_confocal_limits](chromatic_confocal_limits.md)

---
*Provenance: chromconf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
