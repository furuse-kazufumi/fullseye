---
op: oct_layer_thickness
dim: optics
category: oct
in: table
out: table
examples: [poc_industrial_oct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# oct_layer_thickness — OPTICS `oct` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.oct_layer_thickness(ascan, n_group=None, n_interfaces=None, min_snr_db=12.0, z_range_um=None, min_separation_um=None, min_separation_fwhm=1.4, min_prominence_db=0.0, dynamic_range_db=80.0)` (実装を直接呼ぶなら `import octscan; octscan.oct_layer_thickness(ascan, n_group=None, n_interfaces=None, min_snr_db=12.0, z_range_um=None, min_separation_um=None, min_separation_fwhm=1.4, min_prominence_db=0.0, dynamic_range_db=80.0)`、台帳から引くなら `opsoptics.get("oct_layer_thickness")`)

## 使い方

A スキャンの界面のピーク → **層の光学厚と物理厚**(``table``)。分離できない・見えないときは拒否する。

ピーク: 雑音の rms(``oct_ascan`` の noise_sigma)の ``min_snr_db`` 上を超える極大(``dsp.find_peaks``、
間隔 ≥ ``min_separation_um``、既定は軸分解能 0.44 λ0²/Δλ の 0.8 倍)を、``n_interfaces`` 本(強い順に
選んで深さ順に並べる)。位置は ``dsp.peak_subbin(mode="gauss")``(ガウスの頂点 = 対数放物線で厳密)。
光学厚 = 隣の界面の光路の差、物理厚 = 光学厚 / n_g。``n_group`` は層ごとの群屈折率(数・``materials``
の名前・{"n", "n_group"} の模型)、None なら光学厚だけ。

拒否(ValueError): 見えた界面が ``n_interfaces`` より少ない(薄すぎて 2 本が 1 本に融合した / 散乱で
下の界面が雑音に沈んだ / 深さ範囲の外)、または隣の界面の間隔が点像の幅(``oct_ascan`` の psf_fwhm_um、窓込み)
の ``min_separation_fwhm`` 倍より狭い —— 2 つの点像が重なると互いの頂点を引き寄せ、干渉で形も歪むので、
分離して**見えても**厚さは偏る(1.4 倍で偏りが 1 % を切る —— PoC ``poc_industrial_oct`` の掃引)。
``dynamic_range_db``: 探す範囲の最大のピークよりこれ以上弱い極大は数えない(窓の副ローブと数値の床 ——
雑音の無い合成や SNR が 100 dB を超える強い面では、雑音の床の上に副ローブが「界面」として立つ)。
``min_prominence_db`` > 0 なら、ピークが周りの谷から立つ高さ(``scipy.signal.peak_prominences``、探す範囲の
中だけで数える)がそれ未満のものを界面と数えない —— 強く散乱する層(白の塗装)の中は滑らかに減衰する
連続体で、その揺らぎの小さな極大を「下の面」と読まないため。
メッセージに見えた本数と分解能を書く。
返り値: dict(kind="oct_layers", z_opt_um(界面)、peak_db、optical_thickness_um、group_index、
thickness_um、resolution_um、snr_db・prominence_db(界面ごと)、separation_limit_um(受け入れる最小の光学厚
= min_separation_fwhm × 点像の幅)、min_thickness_um(それを層ごとの群屈折率で割った、測れる最も薄い物理厚))。

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

- [poc_industrial_oct](../../../../examples/poc_industrial_oct.py) — `py -3.11 examples/poc_industrial_oct.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`oct`)

[oct_design](oct_design.md) · [oct_dispersion_broadening](oct_dispersion_broadening.md) · [oct_interferogram](oct_interferogram.md) · [oct_bscan_simulate](oct_bscan_simulate.md) · [oct_from_spectra](oct_from_spectra.md) · [oct_k_linearize](oct_k_linearize.md) · [oct_dispersion_estimate](oct_dispersion_estimate.md) · [oct_dispersion_compensate](oct_dispersion_compensate.md)

---
*Provenance: octscan.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
