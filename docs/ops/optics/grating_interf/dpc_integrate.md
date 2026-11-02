---
op: dpc_integrate
dim: optics
category: grating_interf
in: table
out: table
gpu: なし
examples: [grating_interferometry, poc_grating_interferometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# dpc_integrate — OPTICS `grating_interf` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dpc_integrate(dpc_rad, pixel_um, distance_mm, analyzer_period_um, wavelength_nm=None, energy_kev=None, axis=1, baseline='left', baseline_px=8, delta=None)` (実装を直接呼ぶなら `import gratinginterf; gratinginterf.dpc_integrate(dpc_rad, pixel_um, distance_mm, analyzer_period_um, wavelength_nm=None, energy_kev=None, axis=1, baseline='left', baseline_px=8, delta=None)`、台帳から引くなら `opsoptics.get("dpc_integrate")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

微分位相(縞の位相のずれ φ)を格子の感度の向きに積分して、波面の位相 Φ [rad] に戻す。

屈折角 α = φ·p2/(2π d)(Weitkamp ら 2005 の式 1)、∂Φ/∂x = (2π/λ)·α。画素の中で平均した α を
画素の幅で足すと、画素の境界での Φ が出る(``np.cumsum``)。返すのは隣り合う境界の平均(画素の中心)。
dpc_rad は 2-D の図か、``grating_three_image_retrieve`` の返り値(表。``dpc_rad`` を取り出す)。
delta(屈折率の 1 からのずれ δ)を渡すと、投影の厚さ t = −Φ·λ/(2π δ) [µm] も返す。

積分の定数(と、基準と試料の間の格子のずれによる微分位相の一定のずれ)は baseline で決める:
  ``"left"``  各行の最初の baseline_px 画素(試料の無い縁)で Φ = 0
  ``"both"``  両端の baseline_px 画素で Φ = 0 になるように、行ごとに一次式を引く
              (微分位相の一定のずれ = 位相の傾きを消す。試料が両端に掛からないことが前提)
  ``"none"``  何も引かない(最初の境界で Φ = 0)

★折り返し(fail-closed): 微分位相は (−π, π] に折り返されている。本当の φ が π を超えた画素では
隣と 2π 近く跳ぶ。積分の向きに隣り合う画素の差が π(Itoh の条件。数学で決まる値なのでつまみにしない)を超える画素が
1 つでもあれば、どれだけ足すべきか決まらないので値を返さずに拒否する(縞の位相を大きくしない ——
距離 d を短くするか、細かい画素で撮る)。NaN(``grating_three_image_retrieve`` の無効画素)も拒否する。
正直な限界: 折り返しは「隣との跳び」でしか見えない。平らな背景の隣にある 1 画素だけが π を超え、折り返した値が
背景と π 以内に収まる場合(縁の 1 画素など)は、折り返した図だけからは見分けられない(本当の跳びが π を超える
= 標本化が足りない、という Itoh の条件の外)。

返り値 dict: ``phase_rad``(H, W)/ ``thickness_um``(δ があるとき)/ ``refraction_urad`` /
``max_jump_rad``(実測の隣との差の最大)/ ``baseline``。
**Raises** ValueError: 2-D でない・NaN/Inf、正でない画素・距離・周期・波長、wavelength_nm と energy_kev の両方 / どちらも無い、
axis が 0/1 でない、未知の baseline、baseline_px が幅の半分を超える、δ ≤ 0、隣との差が π を超える。

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

[talbot_grating_design](talbot_grating_design.md) · [grating_stepping_simulate](grating_stepping_simulate.md) · [grating_three_image_retrieve](grating_three_image_retrieve.md) · [darkfield_scatter_relation](darkfield_scatter_relation.md) · [talbot_carpet](talbot_carpet.md) · [talbot_source_visibility](talbot_source_visibility.md) · [grating_step_period_estimate](grating_step_period_estimate.md)

---
*Provenance: gratinginterf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
