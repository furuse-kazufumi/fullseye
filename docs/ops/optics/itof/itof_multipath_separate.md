---
op: itof_multipath_separate
dim: optics
category: itof
in: table
out: table
examples: [poc_itof_multifreq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# itof_multipath_separate — OPTICS `itof` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.itof_multipath_separate(phasors, frequencies_hz=None, n_paths=2, pencil=None)` (実装を直接呼ぶなら `import itof; itof.itof_multipath_separate(phasors, frequencies_hz=None, n_paths=2, pencil=None)`、台帳から引くなら `opsoptics.get("itof_multipath_separate")`)

## 使い方

等間隔の多周波で測ったフェーザ → 経路ごとの距離と強さ(行列ペンシル)。``table`` を返す。

画素に経路 p(距離 d_p、強さ a_p)の光が入ると、周波数 f のフェーザは
``m(f) = Σ_p a_p e^{i 4π f d_p / c}``。周波数が等間隔 ``f_k = f_0 + kΔf`` なら
``m_k = Σ_p α_p z_p^k``(``z_p = e^{i 4π Δf d_p / c}``、``α_p = a_p e^{i 4π f_0 d_p / c}``)という減衰しない
指数の和になり、行列ペンシル(Hua & Sarkar 1990)で z_p が閉形式に出る:

1. 粗い距離 ``d_p = arg(z_p) · c / (4π Δf)``(周期 ``c/(2Δf)`` の剰余)。
2. Vandermonde の最小二乗で α_p。``|α_p|`` が強さ。
3. 細かい距離: 中央の周波数 ``f_c`` を原点にした ``arg(α_p)`` は周期 ``c/(2f_c)`` の剰余を教えるので、粗い距離に
   最も近い次数を選んで精密化する(粗い距離の誤差が ``c/(4 f_c)`` を越えると次数を誤る —— 雑音が大きいときは
   ``depth_coarse`` も見ること)。

経路は距離の近い順に並べる。経路が 1 本しか無い画素では、2 本目の強さが 0 近くに出る。
★分けられるのは、2 つの経路の距離の差がおおよそ帯域の分解能 ``c / (2 F Δf)`` より大きいときだけ
(等間隔 F 周波数の幅が帯域)。それより近い経路は雑音があると 1 本に潰れる。

*phasors* は :func:`itof_phase_amplitude` の表(``phasor`` と周波数を使う)か、複素の ``(F, ...)`` 配列。
*pencil* はペンシルの幅 L(既定 F // 2、``n_paths <= L <= F − n_paths``)。

返す ``dict``: ``depth`` ``(P, ...)``、``depth_coarse``、``amplitude`` ``(P, ...)``、``residual``(当てはめの相対残差)、
``ambiguity_coarse``(``c/(2Δf)``)、``resolution``(``c/(2FΔf)``)。

**Raises** ``ValueError``: 周波数が等間隔でない・2·n_paths 個未満 / 形が合わない / n_paths が 1〜8 でない /
pencil が範囲外 / 画素数が上限を超える。

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

[itof_capture](itof_capture.md) · [itof_phase_amplitude](itof_phase_amplitude.md) · [itof_noise_budget](itof_noise_budget.md) · [itof_unwrap_multifreq](itof_unwrap_multifreq.md) · [itof_unwrap_error_rate](itof_unwrap_error_rate.md) · [itof_flying_pixel_mask](itof_flying_pixel_mask.md) · [itof_wiggling_correct](itof_wiggling_correct.md)

---
*Provenance: itof.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
