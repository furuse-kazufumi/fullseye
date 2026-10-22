---
op: itof_wiggling_correct
dim: optics
category: itof
in: table
out: table
examples: [poc_itof_multifreq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# itof_wiggling_correct — OPTICS `itof` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.itof_wiggling_correct(phase, frequencies_hz=None, waveform='square', n_phases=4, calibration=None, n_harmonics=2)` (実装を直接呼ぶなら `import itof; itof.itof_wiggling_correct(phase, frequencies_hz=None, waveform='square', n_phases=4, calibration=None, n_harmonics=2)`、台帳から引くなら `opsoptics.get("itof_wiggling_correct")`)

## 使い方

高調波による周期誤差(wiggling)を補正した位相と距離。``table`` を返す。

変調と復調が矩形波だと、相関は三角波(``waveform="square"``)になり、K 段の推定は奇数次の高調波を基本波に
折り返す。4 段なら真の位相 φ が第 1 象限にあるとき ``u = 2φ/π`` として推定は ``atan(u / (1 − u))`` になり、
誤差は周期 π/2 で波打つ(最大 ±0.071 rad 程度、20 MHz で ±8.5 cm)。

* 模型(*calibration* なし): *waveform* の相関で「真の位相 → 推定の位相」の表を作り(単調でなければ拒否)、逆に引く。
* 較正(*calibration* = ``(measured_phase, true_phase)``、同じ周波数の 1-D の組): 誤差 ``e(φ_m)`` を
  ``c_0 + Σ_{j=1..J} (a_j cos(jKφ_m) + b_j sin(jKφ_m))``(周期 2π/K の調和、J = *n_harmonics*)で最小二乗に当て、
  ``φ_m − e(φ_m)`` を返す(c_0 は距離のオフセット = 系の遅延)。

*phase* は :func:`itof_phase_amplitude` の表か、``(F, ...)`` の位相の配列(周波数ごとに同じ補正)。

返す ``dict``: ``phase``(補正後、[0, 2π))、``depth``(周波数が分かれば、折り返したまま)、``correction``(足した量)、
``model``(``"lut"`` か ``"fit"``)、``coefficients``(較正のとき)、``fit_rms``(較正の残差 [rad])。

**Raises** ``ValueError``: 位相が非有限 / waveform が不正・推定が単調でない / 較正の組の形が合わない・
未知数より少ない / n_harmonics が 1〜8 でない。

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

[itof_capture](itof_capture.md) · [itof_phase_amplitude](itof_phase_amplitude.md) · [itof_noise_budget](itof_noise_budget.md) · [itof_unwrap_multifreq](itof_unwrap_multifreq.md) · [itof_unwrap_error_rate](itof_unwrap_error_rate.md) · [itof_multipath_separate](itof_multipath_separate.md) · [itof_flying_pixel_mask](itof_flying_pixel_mask.md)

---
*Provenance: itof.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
