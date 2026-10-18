---
op: oct_bscan_boundaries
dim: optics
category: oct
in: image2d
out: table
examples: [poc_industrial_oct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# oct_bscan_boundaries — OPTICS `oct` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.oct_bscan_boundaries(image, n_boundaries=2, um_per_px=1.0, n_group=None, min_gap_px=4, max_jump_px=2, jump_penalty=0.0, smooth_sigma=1.0, mode='peak', top_px=None, bottom_px=None, reference_rows=None, offset_px=None)` (実装を直接呼ぶなら `import octscan; octscan.oct_bscan_boundaries(image, n_boundaries=2, um_per_px=1.0, n_group=None, min_gap_px=4, max_jump_px=2, jump_penalty=0.0, smooth_sigma=1.0, mode='peak', top_px=None, bottom_px=None, reference_rows=None, offset_px=None)`、台帳から引くなら `opsoptics.get("oct_bscan_boundaries")`)

## 使い方

B スキャンの**画像**から界面を横に辿る(``image2d`` → ``table``)。装置の出力の図にも使える。

各界面 = 列ごとに 1 行を選ぶ道で、隣の列との行の差 ≤ ``max_jump_px``、費用 = −(明るさの z 値)の和 +
``jump_penalty`` × |行の差| が最小のもの(動的計画法。網膜の層分割の Chiu ら 2010、塗膜の Dong ら 2016 と
同じ「最短路」の考え方の 1 本ずつ版)。``mode="peak"`` は明るさ(界面は明るい線)、``"edge"`` は下向きの
明るさの増え方(暗 → 明、散乱の多い層の上の面)。見つけた道の上下 ``min_gap_px`` は次の道で使わない。
探す範囲: ``top_px`` / ``bottom_px``(数か列ごとの (W,))、または ``reference_rows``(既に見つけた面、例えば
表面)からの相対 ``offset_px`` = (下限, 上限)。★相対で探すと、面と平行な界面に罰が掛からず、表面の傾きに
従わない平らな線 —— 自己相関のアーチファクト(層の光学厚の深さに水平に出る)—— は ``jump_penalty`` で
不利になる。行は明るさの放物線で行以下に詰める。

厚さ = 隣の界面の行の差 × ``um_per_px``(縦の 1 画素の µm、光路)÷ ``n_group``(層ごと、None なら光学厚)。
``reference_rows`` を渡したときは、それを 1 本目の界面として行の表に含める。
返り値: dict(kind="oct_boundaries", rows (n, W)、thickness_um (n − 1, W)、mean_um、std_um、contrast)。
画像が平ら・範囲が狭すぎて道が置けないときは拒否。

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

- [poc_industrial_oct](../../../../examples/poc_industrial_oct.py) — `py -3.11 examples/poc_industrial_oct.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`oct`)

[oct_design](oct_design.md) · [oct_dispersion_broadening](oct_dispersion_broadening.md) · [oct_interferogram](oct_interferogram.md) · [oct_bscan_simulate](oct_bscan_simulate.md) · [oct_from_spectra](oct_from_spectra.md) · [oct_k_linearize](oct_k_linearize.md) · [oct_dispersion_estimate](oct_dispersion_estimate.md) · [oct_dispersion_compensate](oct_dispersion_compensate.md)

---
*Provenance: octscan.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
