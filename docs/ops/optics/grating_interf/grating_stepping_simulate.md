---
op: grating_stepping_simulate
dim: optics
category: grating_interf
in: image2d
out: images
examples: [grating_interferometry, poc_grating_interferometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# grating_stepping_simulate — OPTICS `grating_interf` op

- **データ種**: `image2d` → `images`
- **呼び出し**: `import fullseye as fs; fs.ledger.grating_stepping_simulate(transmission=None, dpc_rad=None, darkfield=None, n_steps=8, ref_visibility=0.25, ref_phase_rad=0.0, steps_per_period=None, flux=None, seed=0, shape=(64, 64))` (実装を直接呼ぶなら `import gratinginterf; gratinginterf.grating_stepping_simulate(transmission=None, dpc_rad=None, darkfield=None, n_steps=8, ref_visibility=0.25, ref_phase_rad=0.0, steps_per_period=None, flux=None, seed=0, shape=(64, 64))`、台帳から引くなら `opsoptics.get("grating_stepping_simulate")`)
- **台帳経由の戻り値**: `fullseye.ledger.grating_stepping_simulate(...)` は**宣言 out 型 `images` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.grating_stepping_simulate.raw(...)`、または `gratinginterf.grating_stepping_simulate` を直接呼ぶ。

## 使い方

透過・微分位相・暗視野の 3 枚の図から、位相ステップの画像列 (N, H, W) を作る(順モデル)。

各画素の k 枚目(k = 0..N−1)は I_k = flux·T·(1 + V0·D·cos(φ0 + φ − 2πk/P))。
T = transmission(吸収)、φ = dpc_rad(縞の位相のずれ = 微分位相。屈折角 α とは φ = 2π d α/p2)、
D = darkfield(可視度の比、1 = 散乱なし)、V0 = ref_visibility(試料なしの縞の可視度)、
φ0 = ref_phase_rad(格子のむらによる基準の位相。スカラーか図)、P = steps_per_period
(1 周期のステップ数。None は N = 1 周期を N 等分)。
3 枚とも None なら試料なし(基準)の画像列になる: T = 1、φ = 0、D = 1。
flux: None なら雑音なしの期待値(flux = 1)。数を渡すと、T = 1 の画素の 1 枚あたりの平均光子数として
Poisson 雑音を足した整数の計数を float で返す(seed で再現)。

返り値: (N, H, W) float64。``grating_three_image_retrieve`` に試料ありと基準の 2 組を渡すと 3 枚が戻る。
**Raises** ValueError: 図が 2-D でない / 形がそろわない / NaN・Inf、T < 0、D が [0, 1] の外、
V0 が (0, 1] の外、n_steps が 3..256 の外、P ≤ 0、flux ≤ 0。

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

## 型が繋がる次の op(`images` を入力に取れる)

[film_thickness_map](../film/film_thickness_map.md) · [equirect_stabilize](../omni360/equirect_stabilize.md) · [equirect_from_fisheye_pair](../omni360/equirect_from_fisheye_pair.md) · [equirect_from_perspectives](../omni360/equirect_from_perspectives.md) · [grating_three_image_retrieve](grating_three_image_retrieve.md) · [grating_step_period_estimate](grating_step_period_estimate.md) · [render_transport](../light_transport/render_transport.md) · [separate_direct_global](../light_transport/separate_direct_global.md)

## 同カテゴリ(`grating_interf`)

[talbot_grating_design](talbot_grating_design.md) · [grating_three_image_retrieve](grating_three_image_retrieve.md) · [darkfield_scatter_relation](darkfield_scatter_relation.md) · [talbot_carpet](talbot_carpet.md) · [talbot_source_visibility](talbot_source_visibility.md) · [grating_step_period_estimate](grating_step_period_estimate.md) · [dpc_integrate](dpc_integrate.md)

---
*Provenance: gratinginterf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
