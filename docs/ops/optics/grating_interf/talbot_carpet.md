---
op: talbot_carpet
dim: optics
category: grating_interf
in: 
out: table
examples: [grating_interferometry, poc_grating_interferometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# talbot_carpet — OPTICS `grating_interf` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.talbot_carpet(period_um=4.0, wavelength_nm=None, energy_kev=None, grating='pi', duty=0.5, z_max_mm=None, n_z=241, n_x=128, n_periods=2, n_harmonics=63, model='exact')` (実装を直接呼ぶなら `import gratinginterf; gratinginterf.talbot_carpet(period_um=4.0, wavelength_nm=None, energy_kev=None, grating='pi', duty=0.5, z_max_mm=None, n_z=241, n_x=128, n_periods=2, n_harmonics=63, model='exact')`、台帳から引くなら `opsoptics.get("talbot_carpet")`)

## 使い方

タルボ絨毯: 2 値の格子(位相 π / 位相 π/2 / 吸収)の後ろの強度 I(x, z) を、回折次数の和で閉形式に出す。

格子 1 周期の透過 t(x)(線の幅の割合 duty で t_a、残りで t_b)のフーリエ係数 c_n は閉形式
c_n = (t_a − t_b)(1 − e^{−2πi n·duty})/(2πi n)、c_0 = t_a·duty + t_b(1 − duty)。平面波で照らした場は
u(x, z) = Σ c_n e^{2πi n x/p} e^{i k_z(n) z}。
model:
  ``"exact"``     k_z = 2π √(1/λ² − n²/p²)(角スペクトルの厳密な伝搬。1/λ < |n|/p の次数はエバネッセントで減衰)。
  ``"paraxial"``  k_z ≈ 2π/λ − πλ n²/p²(Fresnel)。z_T = 2p²/λ で強度が z = 0 と厳密に同じになる(自己像)。
                  z_max での 1 次の位相誤差 πλ³z/(4p⁴)… が 0.1 rad を超えるときは拒否する(``"exact"`` を使う)。
縞の可視度 ``visibility``(z ごと)は、縞の周期の次数 h(位相 π の格子は h = 2 = 周期 p/2、他は h = 1)の
強度の係数 2|I_h|/I_0 で、係数の積から直接出す(x の標本化に依らない)。方形波の縞が完全に結ぶと 4/π。

z_max_mm: None ならタルボ長 z_T = 2p²/λ の 1 周期分。n_harmonics: 和を打ち切る次数 N(係数は 1/n で減るので、
角の Gibbs の波打ちは残る —— 図用。距離と可視度は打ち切りにほぼ依らない)。

返り値 dict: ``intensity``(n_z, n_x)/ ``z_mm`` / ``x_um`` / ``visibility``(n_z)/ ``fringe_harmonic``(h)/
``talbot_length_mm`` / ``self_image_mm``(`talbot_grating_design` の分数タルボ距離のうち z_max までのもの)/
``wavelength_nm`` / ``model`` / ``paraxial_phase_error_rad``(z_max での 1 次の近軸の位相誤差)。
**Raises** ValueError: 正でない周期・波長・z_max、wavelength_nm と energy_kev の両方、未知の grating・model、
duty が (0, 1) の外、n_z・n_x・n_periods・n_harmonics が範囲の外、近軸の誤差が大きすぎる。

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

[talbot_grating_design](talbot_grating_design.md) · [grating_stepping_simulate](grating_stepping_simulate.md) · [grating_three_image_retrieve](grating_three_image_retrieve.md) · [darkfield_scatter_relation](darkfield_scatter_relation.md) · [talbot_source_visibility](talbot_source_visibility.md) · [grating_step_period_estimate](grating_step_period_estimate.md) · [dpc_integrate](dpc_integrate.md)

---
*Provenance: gratinginterf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
