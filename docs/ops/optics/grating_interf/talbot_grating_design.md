---
op: talbot_grating_design
dim: optics
category: grating_interf
in: 
out: table
examples: [grating_interferometry, poc_grating_interferometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# talbot_grating_design — OPTICS `grating_interf` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.talbot_grating_design(period_um=4.0, wavelength_nm=None, energy_kev=None, grating='pi', order=1, source_distance_mm=None)` (実装を直接呼ぶなら `import gratinginterf; gratinginterf.talbot_grating_design(period_um=4.0, wavelength_nm=None, energy_kev=None, grating='pi', order=1, source_distance_mm=None)`、台帳から引くなら `opsoptics.get("talbot_grating_design")`)

## 使い方

格子干渉計の幾何: 第 1 格子の自己像の距離(分数タルボ距離)、縞と分析格子の周期、線源格子の周期(閉形式)。

第 1 格子(周期 period_um = p1)を通った波は、ある距離で格子の像(またはその周期の半分の像)を結ぶ。
その距離に周期の合った吸収格子(分析格子)を置き、どちらかの格子を 1 周期ずらしながら撮ると、各画素で
縞の正弦が取れる。この op はその距離と周期を返す。

grating:
  ``"pi"``         位相 π の格子(線の幅が周期の半分)。縞の周期 p1/2、距離 d_m = (m − 1/2)·p1²/(4λ)
                   (Weitkamp ら 2005, Opt. Express 13, 6296 の式 2)。
  ``"pi_half"``    位相 π/2 の格子。縞の周期 p1、d_m = (m − 1/2)·p1²/λ。
  ``"absorption"`` 吸収格子。縞の周期 p1、d_m = m·p1²/λ(m = 2 がタルボ長 z_T = 2p1²/λ)。
order: m(1 以上の整数)。
source_distance_mm: 線源から第 1 格子までの距離 L。None は平面波(L = ∞)。有限なら距離は
d' = L·d/(L − d) に伸び(同じ文献)、縞は M = (L + d')/L 倍に拡大される。L ≤ d では自己像が結ばれない
(分母が 0 以下)ので拒否する。

返り値 dict:
  ``wavelength_nm`` / ``talbot_length_mm``(z_T = 2p1²/λ、平面波)/ ``distance_plane_mm``(d_m)/
  ``distance_mm``(d'、円錐ビームで伸びた距離。平面波なら d_m と同じ)/ ``magnification``(M)/
  ``fringe_period_um``(第 1 格子の直後での縞の周期)/ ``analyzer_period_um``(p2 = M × 縞の周期)/
  ``source_grating_period_um``(Lau の条件 p0 = p2·L/d'、Pfeiffer ら 2006。平面波なら None)/
  ``angular_sensitivity``(縞の位相 / 屈折角 = 2π d'/p2 [rad/rad])/
  ``correlation_length_um``(暗視野の自己相関長 ξ = λ d'/p2)/
  ``relative_bandwidth``(縞の振幅が 0 になるまでの波長の幅 Δλ/λ = 1/(2m − 1)。位相 π の格子だけ。
  Weitkamp ら 2005 の式 3。他の格子は None)。

例(公表値): 14.4 keV、p1 = 4 µm、位相 π、m = 1 → d = 23.2 mm、p2 = 2 µm(平面波。Weitkamp ら 2005 の図 4 の装置)。
**Raises** ValueError: 正でない周期・波長、wavelength_nm と energy_kev の両方(どちらも無ければ 28 keV)、未知の grating、
order が 1..1000 の外、L ≤ d。

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

[grating_stepping_simulate](grating_stepping_simulate.md) · [grating_three_image_retrieve](grating_three_image_retrieve.md) · [darkfield_scatter_relation](darkfield_scatter_relation.md) · [talbot_carpet](talbot_carpet.md) · [talbot_source_visibility](talbot_source_visibility.md) · [grating_step_period_estimate](grating_step_period_estimate.md) · [dpc_integrate](dpc_integrate.md)

---
*Provenance: gratinginterf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
