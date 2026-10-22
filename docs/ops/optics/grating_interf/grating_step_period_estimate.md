---
op: grating_step_period_estimate
dim: optics
category: grating_interf
in: images
out: table
examples: [grating_interferometry, poc_grating_interferometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# grating_step_period_estimate — OPTICS `grating_interf` op

- **データ種**: `images` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.grating_step_period_estimate(stack, p_min=None, p_max=None, p_step=0.05, region=None, min_visibility=0.05)` (実装を直接呼ぶなら `import gratinginterf; gratinginterf.grating_step_period_estimate(stack, p_min=None, p_max=None, p_step=0.05, region=None, min_visibility=0.05)`、台帳から引くなら `opsoptics.get("grating_step_period_estimate")`)

## 使い方

位相ステップの画像列から「1 周期が何ステップか」(P)を、正弦をあてた残差の最小で推定する。

実際の装置では、格子を動かす量の較正のずれや「1 周期の両端を含む走査」で、1 周期のステップ数 P が
撮った枚数 N と一致しない。P を間違えると縞の位相・振幅の読みが系統的に狂う(``grating_three_image_retrieve`` の
``fit_residual_*`` が大きくなる)。この op は P を p_min..p_max(既定 N − 2 .. N + 2)で p_step 刻みに振り、
region の画素で I_k = a + b cos(φ − 2πk/P) をあてた残差の RMS / 平均を、画素について二乗平均した値が最小の P を返す。
残差は 9 桁に丸めて比べ、同点は小さい P を取る(argmin が同点で返す位置が、丸めの屑で OS ごとに変わらないように)。

region: (y0, y1, x0, x1) の画素の範囲(試料の無い空気・基準の画素を選ぶ)。None は全画素。
min_visibility: 残差に数える画素の縞の可視度の下限(P = N で一度あてた振幅 / 平均)。格子の欠陥・影・試料の
縁など、縞の弱い画素は正弦の残差が雑音だけになって P の判定を薄めるので、数に入れない。

次のときは値を返さずに拒否する(fail-closed):
  * N < 5(未知数 3 + P に対して残差の自由度が足りない)
  * 可視度が min_visibility 以上の画素が 1 つも無い(縞が無い)
  * 最小が探索の範囲の端(本当の最小は外にあるかもしれない)
  * 残差の最大 / 最小が 1.1 未満(曲線が平らで P が決まらない。判定の定数で、つまみではない)

返り値 dict: ``steps_per_period``(P)/ ``n_steps``(N)/ ``p_grid`` / ``residual``(各 P の残差)/
``residual_min`` / ``residual_at_n``(P = N の残差。N が格子に無ければ None)/ ``visibility_median``
(数に入れた画素の)/ ``n_pixels``(数に入れた画素の数)/ ``resolution``(= p_step)。
**Raises** ValueError: 上の拒否、画像列が 3-D でない・NaN/Inf、region が画像の外、p_min ≥ p_max、
p_step ≤ 0、格子が 2000 点を超える。

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

[talbot_grating_design](talbot_grating_design.md) · [grating_stepping_simulate](grating_stepping_simulate.md) · [grating_three_image_retrieve](grating_three_image_retrieve.md) · [darkfield_scatter_relation](darkfield_scatter_relation.md) · [talbot_carpet](talbot_carpet.md) · [talbot_source_visibility](talbot_source_visibility.md) · [dpc_integrate](dpc_integrate.md)

---
*Provenance: gratinginterf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
