---
op: emva_highpass
dim: optics
category: sensorchar
in: image2d
out: table
examples: [poc_emva1288_in_camera_processing, poc_emva1288_sensor]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# emva_highpass — OPTICS `sensorchar` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.emva_highpass(image, method='r4', line_scan=False)` (実装を直接呼ぶなら `import sensorchar; sensorchar.emva_highpass(image, method='r4', line_scan=False)`、台帳から引くなら `opsoptics.get("emva_highpass")`)

## 使い方

照明のむらを除く高域フィルタ(8.1 節。旧版は付録 C.5 の式 84〜87)。

8.1 節: 「7 × 7 の箱、11 × 11 の箱、3 × 3 の二項を順にかけて平滑化し、元の画像から引く」。DSNU・PRNU(式 66・67)、
スペクトログラム(8.6 節)、欠陥画素のヒストグラム(8.8 節)はこの画像から求める(縦横の断面 8.7 節だけはかけない)。
*method* ``"r4"``(既定、Release 4.0)/ ``"r3.1"``(付録 C.5: 5 × 5 の箱を引く、式 84)。
*line_scan*: ``"r3.1"`` だけ —— 横 5 × 1 の箱(付録 C.5 の線カメラ)。r4 の線カメラ版は本文に無いので拒む。

端: 平滑化が完全に定義される内側だけを返す(r4 は各辺 9 画素、r3.1 は 2 画素を落とす)。r3.1 の「上下左右 2 本を
捨てる」は付録 C.5 の文。r4 の 9 画素は本文に書かれていない —— 3 つのフィルタの半幅の和 3 + 5 + 1 から導いた。

白い雑音の分散の利得(``white_variance_gain`` = Σh²、h = δ − 平滑化)は**カーネルから厳密に**数える。r3.1 では
1 − 1/25 = 0.96(本文の式 86 は 0.92、標準偏差を 0.96 で割れと書く —— 二乗が一つ多い。線カメラは
1 − 1/5 = 0.80 に対し本文の式 87 は 0.64)。列・行の模様(片方向にだけ変わる)は 1-D の利得
``white_variance_gain_col`` / ``_row`` で減る。``transfer`` は波数 k̃ = 0..1(ナイキストで 1)の 1-D の伝達関数。

返り値 ``{"kind": "emva_highpass", "image", "smoothed", "method", "border", "white_variance_gain",
"white_variance_gain_col", "white_variance_gain_row", "standard_std_divisor", "transfer_k", "transfer"}``
(``standard_std_divisor`` は付録 C.5 が書く割る数 0.96 / 0.80、r4 は None)。

**Raises** ``ValueError``: 2-D の実数でない / NaN・inf / method が違う / r4 で line_scan / 画像がカーネルより小さい。

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

- [poc_emva1288_in_camera_processing](../../../../examples/poc_emva1288_in_camera_processing.py) — `py -3.11 examples/poc_emva1288_in_camera_processing.py`
- [poc_emva1288_sensor](../../../../examples/poc_emva1288_sensor.py) — `py -3.11 examples/poc_emva1288_sensor.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`sensorchar`)

[emva_pair_statistics](emva_pair_statistics.md) · [emva_photon_transfer](emva_photon_transfer.md) · [emva_quantum_efficiency](emva_quantum_efficiency.md) · [emva_linearity_error](emva_linearity_error.md) · [emva_snr_curve](emva_snr_curve.md) · [emva_sensitivity_threshold](emva_sensitivity_threshold.md) · [emva_dynamic_range](emva_dynamic_range.md) · [emva_dark_current](emva_dark_current.md)

---
*Provenance: sensorchar.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
