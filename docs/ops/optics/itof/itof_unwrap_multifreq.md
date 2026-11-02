---
op: itof_unwrap_multifreq
dim: optics
category: itof
in: table
out: table
gpu: なし
examples: [poc_itof_multifreq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# itof_unwrap_multifreq — OPTICS `itof` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.itof_unwrap_multifreq(phase, frequencies_hz=None, weights=None, max_range_m=None, method='ml')` (実装を直接呼ぶなら `import itof; itof.itof_unwrap_multifreq(phase, frequencies_hz=None, weights=None, max_range_m=None, method='ml')`、台帳から引くなら `opsoptics.get("itof_unwrap_multifreq")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

複数の周波数の位相 → 距離(多周波アンラップ)。``table`` を返す。

周波数 f_i の位相 φ_i は距離を周期 ``p_i = c/(2 f_i)`` の剰余 ``r_i = φ_i p_i / (2π)`` で教える。周期の最小公倍数
``U = c / (2·gcd f)`` までが一意(非曖昧距離)。

* ``method="ml"``(既定)—— **最も高い周波数**(距離の誤差が最も小さい帯)の剰余を錨にして、その次数の仮説
  ``v = r_hi + k p_hi``(k = 0 … U/p_hi)を全部、フェーザの一致 ``Σ w_i cos(2π(v − r_i)/p_i)`` で採点し、最良の仮説を
  逆分散の重み平均で精密化する(仮説を全部試す最尤の復号。位相雑音が帯ごとに同じなら、錨の誤差が最も小さい)。
* ``method="crt"`` —— ``residue.residue_crt``(重みつきの頑健な中国剰余定理)にそのまま渡す。★``residue_crt`` は
  Wang–Xia(2010)の錨の選び方 —— 雑音の分散 p²/w が最小の帯、同分散なら剰余 mod Γ が円上の最小二乗の共通剰余に
  最も近い帯 —— で錨を選ぶので、位相雑音が帯ごとに同じ iToF でも ``"ml"`` と同等になる(PoC の合成 0.1161 対
  0.1160、実データ 0.131 対 0.131。以前の、常に最も長い周期を錨にする実装は 0.556 / 0.293 と大きく誤った)。
  保証(:func:`itof_unwrap_error_rate` の ``guaranteed_phase_rad``)の外の画素があると
  ``residue.ResidueBoundWarning`` を出す(値は返す)。
* ``method="beat"`` —— 2 周波だけ。うなりの位相 ``φ_1 − φ_2`` で粗い距離(周期 ``c/(2|f_1 − f_2|)``)を出し、
  各周波数の次数をそれに最も近く丸めて重み平均する(教科書の古典的な方法)。

*weights* の既定は、:func:`itof_phase_amplitude` の表なら ``A²/B``(∝ 1/σ_φ²)、配列なら全帯 1。
*max_range_m* で探す範囲 ``[0, max_range_m)`` を狭められる(非曖昧距離より広くは拒否)。

返す ``dict``: ``depth``、``order`` ``(F, ...)``(各周波数で何周目か)、``margin``(最良と次点の採点の差。小さい =
次数が際どい)、``score``、``residual`` ``(F, ...)`` [m]、``unambiguous_range``、``periods``、``method``。

**Raises** ``ValueError``: 周波数・位相の形が合わない / 周期が通約できない(非曖昧距離が有限でない)/
max_range_m が非曖昧距離より広い / beat で 2 周波でない / method が不正 / 仮説 × 画素が上限を超える。

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

[itof_capture](itof_capture.md) · [itof_phase_amplitude](itof_phase_amplitude.md) · [itof_noise_budget](itof_noise_budget.md) · [itof_unwrap_error_rate](itof_unwrap_error_rate.md) · [itof_multipath_separate](itof_multipath_separate.md) · [itof_flying_pixel_mask](itof_flying_pixel_mask.md) · [itof_wiggling_correct](itof_wiggling_correct.md)

---
*Provenance: itof.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
