---
op: darkfield_scatter_relation
dim: optics
category: grating_interf
in: 
out: table
examples: [grating_interferometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# darkfield_scatter_relation — OPTICS `grating_interf` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.darkfield_scatter_relation(darkfield=None, sigma_urad=None, distance_mm=23.2, analyzer_period_um=2.0, thickness_mm=None, wavelength_nm=None)` (実装を直接呼ぶなら `import gratinginterf; gratinginterf.darkfield_scatter_relation(darkfield=None, sigma_urad=None, distance_mm=23.2, analyzer_period_um=2.0, thickness_mm=None, wavelength_nm=None)`、台帳から引くなら `opsoptics.get("darkfield_scatter_relation")`)

## 使い方

暗視野 D(可視度の比)と、散乱角の分布の広がり σ の換算(ガウス散乱の公表式)。

散乱角の分布がガウス(標準偏差 σ、格子の線に直交する向きの成分)なら、縞の可視度は
D = exp(−2π² σ² d²/p2²)(Strobl 2014, Sci. Rep. 4, 7243 の式 7 をガウスで積分した形 =
Bech ら 2010, Phys. Med. Biol. 55, 5529 の線拡散係数の式)。d は試料(第 1 格子)から分析格子までの距離、
p2 は分析格子の周期。逆に σ = (p2/(π d √2))·√(−ln D)。

darkfield と sigma_urad のどちらか一方を渡す(スカラーか配列)。
thickness_mm を渡すと線拡散係数 ε = σ²/t [µrad²/mm] を返す(σ² が厚さに比例する、という仮定の下で)。
wavelength_nm を渡すと自己相関長 ξ = λ d/p2 [µm] を返す(暗視野が感じる構造の大きさの目安)。

配列の D で (0, 1] の外の画素(雑音で 1 を超えた・0 以下)は σ を NaN にして数を ``n_invalid`` に返す。
スカラーで (0, 1] の外なら拒否する(黙って 0 や負の σ を返さない)。

返り値 dict: ``darkfield`` / ``sigma_urad`` / ``diffusion_coeff_urad2_per_mm``(t があるとき)/
``correlation_length_um``(λ があるとき)/ ``angular_sensitivity``(2π d/p2)/ ``n_invalid``。
**Raises** ValueError: darkfield と sigma_urad の両方 / どちらも無い、σ < 0、スカラーの D が (0, 1] の外、
正でない距離・周期・厚さ・波長、NaN/Inf。

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

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`grating_interf`)

[talbot_grating_design](talbot_grating_design.md) · [grating_stepping_simulate](grating_stepping_simulate.md) · [grating_three_image_retrieve](grating_three_image_retrieve.md) · [talbot_carpet](talbot_carpet.md) · [talbot_source_visibility](talbot_source_visibility.md) · [grating_step_period_estimate](grating_step_period_estimate.md) · [dpc_integrate](dpc_integrate.md)

---
*Provenance: gratinginterf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
