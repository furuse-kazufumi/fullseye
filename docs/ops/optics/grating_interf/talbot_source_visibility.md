---
op: talbot_source_visibility
dim: optics
category: grating_interf
in: 
out: table
examples: [grating_interferometry, poc_grating_interferometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# talbot_source_visibility — OPTICS `grating_interf` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.talbot_source_visibility(source_width_um, source_distance_mm, distance_mm, analyzer_period_um, profile='uniform', source_grating_period_um=None, duty=None, n_slits=None, wavelength_nm=None)` (実装を直接呼ぶなら `import gratinginterf; gratinginterf.talbot_source_visibility(source_width_um, source_distance_mm, distance_mm, analyzer_period_um, profile='uniform', source_grating_period_um=None, duty=None, n_slits=None, wavelength_nm=None)`、台帳から引くなら `opsoptics.get("talbot_source_visibility")`)

## 使い方

線源の大きさと線源格子(Lau の条件)で、縞の可視度が何倍に落ちるか(閉形式、非干渉の和)。

線源の 1 点が格子の線に直交する向きに s ずれると、分析格子の上の縞は s·d/L だけ逆向きにずれる
(L = 線源から第 1 格子、d = 第 1 格子から分析格子)。互いに干渉しない点の縞を足すので、可視度の倍率は
線源の分布のフーリエ変換を周波数 d/(L p2) で読んだ値になる(Pfeiffer ら 2006, Nature Physics 2, 258):
  ``"uniform"`` 幅 w:          |sinc(π w d/(L p2))|(sinc x = sin x / x)
  ``"gaussian"`` 半値全幅 w:   exp(−2π² σ² d²/(L² p2²))、σ = w/(2√(2 ln 2))
線源格子(周期 p0、開口の割合 duty、開口 n_slits 本)を置くと、各開口は幅 duty·p0 の一様な線源、開口の並びは
配列の因子 |sin(N β)/(N sin β)|、β = π p0 d/(L p2) を掛ける。β が π の整数倍(Lau の条件 p0 = p2·L/d)で
すべての開口の縞が重なり、可視度は開口 1 本の |sinc(π duty)|(duty = 0.5 で 2/π)まで戻る。
n_slits が None なら round(w/p0)(焦点 w に入る開口の数、1 以上)。線源格子はガウスの焦点とは組まない(拒否)。
duty(開口の割合)は線源格子があるときだけ意味を持つ(None は 0.5)。線源格子なしで duty か n_slits を渡すと、
黙って無視せずに拒否する(線源格子の周期を渡し忘れた呼び出しを見逃さない)。

wavelength_nm を渡すと、第 1 格子での横のコヒーレンス長 l_c = λ L/w [µm] も返す。

返り値 dict: ``visibility_factor`` / ``slit_factor`` / ``array_factor``(線源格子なしは 1)/
``lau_period_um``(p2·L/d)/ ``lau_ratio``(p0 / Lau の周期、線源格子なしは None)/ ``n_slits`` /
``projected_blur_um``(w·d/L、分析格子の上での線源の影の幅)/ ``coherence_length_um``(λ があるとき)。
**Raises** ValueError: 正でない幅・距離・周期、未知の profile、ガウスと線源格子の組、duty が (0, 1] の外、
n_slits が 1..100000 の外、線源格子なしでの duty・n_slits。

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

- [grating_interferometry](../../../../examples/grating_interferometry.py) — `py -3.11 examples/grating_interferometry.py`
- [poc_grating_interferometry](../../../../examples/poc_grating_interferometry.py) — `py -3.11 examples/poc_grating_interferometry.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`grating_interf`)

[talbot_grating_design](talbot_grating_design.md) · [grating_stepping_simulate](grating_stepping_simulate.md) · [grating_three_image_retrieve](grating_three_image_retrieve.md) · [darkfield_scatter_relation](darkfield_scatter_relation.md) · [talbot_carpet](talbot_carpet.md) · [grating_step_period_estimate](grating_step_period_estimate.md) · [dpc_integrate](dpc_integrate.md)

---
*Provenance: gratinginterf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
