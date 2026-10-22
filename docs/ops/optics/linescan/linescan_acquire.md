---
op: linescan_acquire
dim: optics
category: linescan
in: image2d
out: table
examples: [poc_tdi_linescan]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# linescan_acquire — OPTICS `linescan` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.linescan_acquire(web=None, stages=8, photons_per_stage=200.0, eta=0.6, sigma_d=20.0, K=0.1, architecture='charge', full_well_e=None, dark_e=0.0, sync_error=0.0, yaw_deg=0.0, weave_px=0.0, weave_period_lines=200.0, encoder=False, encoder_error=None, lines=None, width=None, lens=None, noise=True, order=3, samples_per_px=4.0, oversample=1, seed=0)` (実装を直接呼ぶなら `import linescan; linescan.linescan_acquire(web=None, stages=8, photons_per_stage=200.0, eta=0.6, sigma_d=20.0, K=0.1, architecture='charge', full_well_e=None, dark_e=0.0, sync_error=0.0, yaw_deg=0.0, weave_px=0.0, weave_period_lines=200.0, encoder=False, encoder_error=None, lines=None, width=None, lens=None, noise=True, order=3, samples_per_px=4.0, oversample=1, seed=0)`、台帳から引くなら `opsoptics.get("linescan_acquire")`)

## 使い方

反射率の地図 *web* を搬送しながら TDI ラインスキャンで撮る(``table``)。

*web*: 2-D の反射率 [0, 1] (行 = 流れ方向 MD、列 = 幅方向 CD)。**1 行 = 公称の 1 ライン、1 列 = 1 画素**の格子。
センサ(幅 *width* 画素、既定 = web の幅から余白を除いた分)は web の中央を見る。

運動の模型(出力ライン k・段 s・段の中の時刻 u ∈ [0, 1)、τ = k + s + u):
  web の進み ``T(τ) = ∫(1 + ε)``(``sync_error`` がスカラなら一定、1-D ならライン周期ごと —— 長さは
  lines + stages 以上)、電荷の位置 ``r = s + u``(1 周期に 1 行)、蛇行 ``w(τ) = weave_px·sin(2πτ/周期)``。
  web の行 = T(τ) − r·cos θ − x·sin θ、web の列 = x·cos θ − r·sin θ − w(τ)(x はセンサ中央からの画素)。
  θ = 0・一定 ε なら行は k(1 + ε) + (s + u)ε —— ``optscene.linescan_capture`` と同じ規約で、N 段で
  N·|ε| 画素の掃引(``tdi_sync_mtf`` の閉形式)。``encoder=True`` は web の進みからライン周期を作る
  (速度の誤差が消え、ε = *encoder_error*(既定 None = 0、エンコーダの分解能の誤差)だけが残る —— ``encoder=False`` で
  渡すと効かないので ValueError)。ヨーと蛇行は残る。

*oversample*(奇数、既定 1): web が 1 画素あたり何 web 画素で描かれているか。1 より大きいと、画素の開口
(oversample × oversample の箱)を掛けてから標本を取る —— 細かい正弦波の板で MTF を測るときは補間の誤差が
結果に混ざらないよう 5 などにする(3 次スプラインでも 0.4 c/px では補間だけで 2 割落ちる)。

時間積分は τ の一様な標本で取り、標本数は 1 段の道のり(滑り + 蛇行)から ``samples_per_px`` 点/画素で決める
(完全同期なら 1 点で厳密)。補間は ``order``(1 = 双線形、3 = 3 次スプライン、前置フィルタは 1 回だけ)。

雑音(``noise=True``、EMVA 1288 の線形模型): 平均電子 μ_e = Σ 段 ημ_p·R(+ 暗電流 *dark_e*/段)を Poisson
1 回で引き(Poisson の和は Poisson —— 厳密)、``charge`` は読み出し σ_d を 1 回、``digital`` は分散 Nσ_d² と
量子化 N/12 DN² を正規雑音で(各段の丸めの近似)。``full_well_e``(既定 None = 飽和なし)は電荷加算では
合計に、デジタル加算では 1 段の平均に掛ける。返す画像は DN = K·e(ADC の上限では切らない)。

*lens*: ``linescan_lens_columns`` の結果(列ごとの相対照度とガウスのぼけ)。光学像は運動の前に決まるので、
ぼけと照度は地図に掛けてから搬送する(同じ列は同じぼけ —— 像高はセンサの列で決まる)。

返り値 dict: ``image`` (lines, width) DN / ``mean_e``(雑音なしの期待電子)/ ``line_rows``(各ラインの
段の中央が見る web の行 [web 画素]、センサ中央の列で)/ ``col0``(センサの列 0 が見る web の列 [web 画素])/ ``slip_scan`` /
``slip_cross`` / ``smear_scan_px`` / ``smear_cross_px`` / ``samples`` / ``stages`` / ``architecture``。

**Raises** ``ValueError``: web が 2-D の有限な [0, 1] でない / 段数・ライン数が範囲外 / ε が範囲外か長さ不足 /
encoder=False で encoder_error を渡した / oversample が偶数 /
掃引・蛇行・ヨーで標本が web の外に出る(黙って端を繰り返さない)/ lens の列数が width と違う。

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

- [poc_tdi_linescan](../../../../examples/poc_tdi_linescan.py) — `py -3.11 examples/poc_tdi_linescan.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`linescan`)

[tdi_snr](tdi_snr.md) · [tdi_sync_mtf](tdi_sync_mtf.md) · [lens_field_profile](lens_field_profile.md) · [linescan_lens_columns](linescan_lens_columns.md) · [linescan_lens_example](linescan_lens_example.md)

---
*Provenance: linescan.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
