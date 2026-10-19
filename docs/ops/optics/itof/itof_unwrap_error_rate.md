---
op: itof_unwrap_error_rate
dim: optics
category: itof
in: 
out: table
examples: [poc_itof_multifreq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# itof_unwrap_error_rate — OPTICS `itof` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.itof_unwrap_error_rate(frequencies_hz=(80000000.0, 100000000.0, 120000000.0), phase_sigma_rad=0.05, max_range_m=None)` (実装を直接呼ぶなら `import itof; itof.itof_unwrap_error_rate(frequencies_hz=(80000000.0, 100000000.0, 120000000.0), phase_sigma_rad=0.05, max_range_m=None)`、台帳から引くなら `opsoptics.get("itof_unwrap_error_rate")`)

## 使い方

多周波アンラップ(最尤の復号)で次数(何周目か)を誤る確率の見積もり。``table`` を返す。

周波数を共通の基本周波数の整数倍 ``f_i = n_i f_g`` と書くと、非曖昧距離は ``U = c / (2 f_g)``、周期は ``p_i = U / n_i``。
折り返さない位相を並べたベクトルは距離 v に比例する直線 ``v·g``(``g_i = 2π/p_i``)の上にあり、折り返しは
これを ``2π m``(m は整数のベクトル)だけずらした平行な直線の族を作る。最尤の復号(:func:`itof_unwrap_multifreq` の
``"ml"``)が誤るのは、測った位相が別の直線 ``v·g + 2πm`` の方に近いとき。位相雑音 σ_i で割った空間での 2 本の
直線の距離を ``D_m`` とすると、その 2 仮説の誤りは ``Q(D_m / 2)``(ガウス)。

* ``union_bound`` = ``Σ_m Q(D_m/2)``(範囲内で出会う m すべての和。上界)、``nearest_term`` = ``max_m Q(D_m/2)``。
* Wang–Xia(2007)の保証: 周期を ``p_i = Γ M_i`` と書く(``Γ = U / lcm(n_i)``)。全周波数の剰余の誤差が ``Γ/4`` 未満なら
  次数は決して誤らない(最も長い周期を錨にする ``residue_crt`` の保証)。``guaranteed_phase_rad`` = 各周波数で
  その境界に当たる位相の誤差 ``2π (Γ/4) / p_i`` —— 低い周波数ほど小さい。

*phase_sigma_rad* はスカラ(全周波数で同じ)か周波数ごと。*max_range_m* は探す範囲(既定 U)。

返す ``dict``: ``unambiguous_range``、``periods``、``integers``(n_i)、``gamma``、``guaranteed_phase_rad``、
``union_bound``、``nearest_term``、``min_distance``(最小の D_m)、``offsets``(m の配列、``(M, F)``)、``distances``。

**Raises** ``ValueError``: 周波数が 2 個未満・通約できない・比が細かすぎる / σ が正でない・形が合わない /
max_range_m が U より広い。

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

- [poc_itof_multifreq](../../../../examples/poc_itof_multifreq.py) — `py -3.11 examples/poc_itof_multifreq.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`itof`)

[itof_capture](itof_capture.md) · [itof_phase_amplitude](itof_phase_amplitude.md) · [itof_noise_budget](itof_noise_budget.md) · [itof_unwrap_multifreq](itof_unwrap_multifreq.md) · [itof_multipath_separate](itof_multipath_separate.md) · [itof_flying_pixel_mask](itof_flying_pixel_mask.md) · [itof_wiggling_correct](itof_wiggling_correct.md)

---
*Provenance: itof.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
