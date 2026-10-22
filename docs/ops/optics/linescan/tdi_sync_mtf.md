---
op: tdi_sync_mtf
dim: optics
category: linescan
in: 
out: table
examples: [poc_tdi_linescan]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# tdi_sync_mtf — OPTICS `linescan` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.tdi_sync_mtf(frequency_cyc_px=None, stages=64, sync_error=0.0, yaw_deg=0.0)` (実装を直接呼ぶなら `import linescan; linescan.tdi_sync_mtf(frequency_cyc_px=None, stages=64, sync_error=0.0, yaw_deg=0.0)`、台帳から引くなら `opsoptics.get("tdi_sync_mtf")`)

## 使い方

TDI の同期ずれとヨー(斜行)が作るぼけの MTF(閉形式、``table``)。

TDI は電荷を 1 ライン周期に 1 行ずつ送り、被写体も同じだけ進めば N 段が同じ物点を足す。速度(または
ラインレート)の相対誤差 ε があると 1 段ごとに像が ε 画素ずつ滑り、N 段で **L = N·|ε| 画素**の一様な掃引になる。
一様な掃引の MTF は ``|sinc(f L)|``(``np.sinc`` = sin(πx)/(πx))—— 最初の零は f = 1/L。

ヨー角 θ(web の流れがセンサの走査軸から θ 傾く)では、web の軸で測った 1 段あたりの滑りが
流れ方向 ``(1 + ε) − cos θ``、幅方向 ``sin θ`` になる(電荷は走査軸に沿って動くので)。幅方向のぼけ
``N·|sin θ|`` 画素は**同期を完全にしても残る** —— エンコーダ同期では直らない。

*frequency_cyc_px*: 周波数 [cycles/画素] (既定 0〜0.5 を 51 点)。返り値 dict: ``frequency`` /
``mtf_scan``(流れ方向)/ ``mtf_cross``(幅方向)/ ``slip_scan`` / ``slip_cross``(1 段あたり [画素])/
``smear_scan_px`` / ``smear_cross_px``(N 段ぶん)/ ``first_zero_scan``(1/L、ぼけが無ければ None)。

★入れていないもの: 同期が完全でも電荷の送りが離散なので 1 画素ぶんの掃引(sinc(f))が残るが、これは
全条件に共通で、多相クロックでは減る。比べたい差は同期の側なので掛けていない。

**Raises** ``ValueError``: 周波数が負・非有限・1-D でない / 段数が範囲外 / |ε| > 0.5 / |θ| > 30°。

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

[tdi_snr](tdi_snr.md) · [linescan_acquire](linescan_acquire.md) · [lens_field_profile](lens_field_profile.md) · [linescan_lens_columns](linescan_lens_columns.md) · [linescan_lens_example](linescan_lens_example.md)

---
*Provenance: linescan.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
