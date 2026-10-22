---
op: grating_three_image_retrieve
dim: optics
category: grating_interf
in: images × images
out: table
examples: [grating_interferometry, poc_grating_interferometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# grating_three_image_retrieve — OPTICS `grating_interf` op

- **データ種**: `images × images` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.grating_three_image_retrieve(sample_stack, reference_stack=None, steps_per_period_sample=None, steps_per_period_reference=None, min_visibility=0.02, distance_mm=None, analyzer_period_um=None, reference_exposure=1.0)` (実装を直接呼ぶなら `import gratinginterf; gratinginterf.grating_three_image_retrieve(sample_stack, reference_stack=None, steps_per_period_sample=None, steps_per_period_reference=None, min_visibility=0.02, distance_mm=None, analyzer_period_um=None, reference_exposure=1.0)`、台帳から引くなら `opsoptics.get("grating_three_image_retrieve")`)

## 使い方

位相ステップの 2 組(試料あり・試料なし)から、透過・微分位相・暗視野の 3 枚を分ける。

各画素で I_k = a·(1 + V·cos(φ − 2πk/P)) をあて(P = 1 周期のステップ数。None は N 等分)、
透過 T = a_s/a_r、微分位相 φ = wrap(φ_s − φ_r)、暗視野 D = V_s/V_r を返す(Pfeiffer ら 2008,
Nature Materials 7, 134 の定義)。P = N のときは ``fringe.wrapped_phase`` と ``fringe.modulation``
(N 段の位相シフトの標準式)をそのまま使い、P ≠ N(1 周期の両端を含む走査など)は 3 項の最小二乗。
2 組のステップ数は違ってよい(各組を別々にあてる)。

reference_stack が None なら、試料の画像列だけから a・V・φ を返す(比は取らない)。
distance_mm と analyzer_period_um を渡すと、屈折角 α = φ·p2/(2π d) [µrad] も返す。
reference_exposure: 基準を試料の何倍の露光(1 枚あたりの光子数)で撮ったか。透過は a_s/(a_r/reference_exposure)。
暗視野と微分位相は比と差なので露光に依らない(透過だけが露光の比で化ける)。
min_visibility: 基準の可視度がこれ未満の画素(格子の欠陥・影)は位相が決まらないので NaN にし、数を返す。
全画素が NaN になるときは値を返さずに拒否する。

返り値 dict: ``transmission`` / ``dpc_rad`` / ``darkfield``(いずれも (H, W)、無効画素は NaN)/
``visibility_sample`` / ``visibility_reference`` / ``refraction_urad``(幾何があるとき)/
``fit_residual_sample`` / ``fit_residual_reference``(正弦をあてた残差の RMS / 平均の中央値。
1 周期のステップ数を間違えると大きくなる)/ ``n_invalid``。
**Raises** ValueError: 画像列が 3-D でない・3 枚未満・NaN/Inf、2 組の画素の形が違う、P ≤ 0、
P が小さすぎて正弦が分けられない、有効な画素が 1 つも無い、幾何の片方だけ、正でない reference_exposure。

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

[talbot_grating_design](talbot_grating_design.md) · [grating_stepping_simulate](grating_stepping_simulate.md) · [darkfield_scatter_relation](darkfield_scatter_relation.md) · [talbot_carpet](talbot_carpet.md) · [talbot_source_visibility](talbot_source_visibility.md) · [grating_step_period_estimate](grating_step_period_estimate.md) · [dpc_integrate](dpc_integrate.md)

---
*Provenance: gratinginterf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
