---
op: itof_capture
dim: optics
category: itof
in: depth
out: table
examples: [poc_itof_multifreq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# itof_capture — OPTICS `itof` op

- **データ種**: `depth` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.itof_capture(depth, reflectivity=None, frequencies_hz=(20000000.0,), n_phases=4, signal_electrons=2000.0, demod_contrast=0.5, ambient_electrons=0.0, read_noise_e=0.0, waveform='sine', paths_depth=None, paths_amplitude=None, supersample=1, falloff_m=None, noise=True, seed=0)` (実装を直接呼ぶなら `import itof; itof.itof_capture(depth, reflectivity=None, frequencies_hz=(20000000.0,), n_phases=4, signal_electrons=2000.0, demod_contrast=0.5, ambient_electrons=0.0, read_noise_e=0.0, waveform='sine', paths_depth=None, paths_amplitude=None, supersample=1, falloff_m=None, noise=True, seed=0)`、台帳から引くなら `opsoptics.get("itof_capture")`)

## 使い方

距離の図 → 間接 ToF の生信号(周波数ごとに K 段のバケット、電子数)。``table``(``dict``)を返す。

画素(細かく描いた標本)ごとに、直接の経路(距離 *depth*、強さ ``signal_electrons · reflectivity``)と、
任意で余分な経路(*paths_depth* = 往復の経路長の半分 [m]、*paths_amplitude* = ``signal_electrons`` に掛ける強さ)が
入る。経路 p の位相は ``φ_p = 4π f d_p / c``。段 k(参照の位相 ``θ_k = 2πk/K``)のバケットの期待値は

    m_k = (Σ_p a_p + ambient) / K + demod_contrast · Σ_p a_p · corr(φ_p − θ_k) / K

(corr は *waveform*: ``"sine"`` なら cos、``"square"`` なら矩形どうしの相関 = 三角波、配列なら余弦の係数 c_1..c_N)。
つまり 1 回の測定(K 段の合計)に信号 ``a_p`` 電子と背景光 ``ambient_electrons`` 電子が入る。*noise* が真なら
各バケットに Poisson のショット雑音と、標準偏差 *read_noise_e* の正規の読み出し雑音を足す。

*supersample* = s > 1 なら *depth* などは**センサの s 倍の細かさ**で描いたものとみなし、s × s の標本の
バケットを平均して 1 画素にする(バケットは経路の光の線形和なので、これは画素の開口で光を足すのと同じ)。
前景と背景をまたぐ画素では 2 つの位相が混ざり、フライングピクセルが生まれる。
*falloff_m* を与えると直接の経路の強さに ``(falloff_m / depth)²``(逆二乗)を掛ける。

返す ``dict``: ``kind``(``"itof_raw"``)、``samples`` ``(F, K, H, W)``、``mean_samples``(雑音なしの期待値)、
``frequencies_hz``、``phase_offsets_rad``、``true_depth``(画素内の直接経路の距離の平均)、``mixed``(画素内の
距離の幅 [m])、``waveform``、``demod_contrast``、``read_noise_e``、``ambiguity_range`` ``(F,)``。

**Raises** ``ValueError``: depth が 2 次元でない・正でない・非有限 / reflectivity・経路の形が合わない・負 /
周波数が (0, 2 GHz] でない・重複 / n_phases が 3〜32 でない / demod_contrast が (0, 1] でない / 電子数が負 /
形が supersample で割り切れない / 画素数・経路数・計算量が上限を超える / waveform が不正。

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

[itof_phase_amplitude](itof_phase_amplitude.md) · [itof_noise_budget](itof_noise_budget.md) · [itof_unwrap_multifreq](itof_unwrap_multifreq.md) · [itof_unwrap_error_rate](itof_unwrap_error_rate.md) · [itof_multipath_separate](itof_multipath_separate.md) · [itof_flying_pixel_mask](itof_flying_pixel_mask.md) · [itof_wiggling_correct](itof_wiggling_correct.md)

---
*Provenance: itof.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
