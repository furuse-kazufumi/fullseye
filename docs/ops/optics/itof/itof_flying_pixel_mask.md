---
op: itof_flying_pixel_mask
dim: optics
category: itof
in: depth
out: image2d
examples: [poc_itof_multifreq, tof_realdata]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# itof_flying_pixel_mask — OPTICS `itof` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.itof_flying_pixel_mask(depth, threshold_m=0.04, rel_threshold=0.0, radius=1, plateau_ratio=0.5, depth_sigma=None, n_sigma=3.0)` (実装を直接呼ぶなら `import itof; itof.itof_flying_pixel_mask(depth, threshold_m=0.04, rel_threshold=0.0, radius=1, plateau_ratio=0.5, depth_sigma=None, n_sigma=3.0)`、台帳から引くなら `opsoptics.get("itof_flying_pixel_mask")`)

## 使い方

距離の図 → フライングピクセル(前景と背景の**間に浮いた**画素)の印 ``(H, W)``(1.0 = 浮いている)。

画素の視野が段差をまたぐと、iToF は 2 つの位相のフェーザ和を返し、距離は前景と背景の**間**に出る
(段差の縁に沿って宙に浮いた点の列ができる)。ある方向(横・縦・2 つの斜め)の両側 ±r 画素の距離
``a``・``b`` に対して、次の 3 つがそろったとき印をつける:

1. ``d`` が**両者の間**にある(``(d − a)(d − b) < 0``)。
2. 両側との差がどちらも閾値 ``τ = max(threshold_m, rel_threshold · d, n_sigma · σ_d)`` を越える。*depth_sigma*
   (画素ごとの距離の雑音、:func:`itof_phase_amplitude` の ``depth_sigma`` から作る)を渡すと、信号の弱い所
   (遠い床・暗い印刷)で雑音を段差と取り違えない。
3. **両側が平らな台地**: その先の ±2r 画素との差 ``|a − a₂|``・``|b − b₂|`` が、それぞれ ``|d − a|``・``|d − b|`` の
   *plateau_ratio* 倍以下。★斜面(床を浅い角度で見る・傾いた面)は 1・2 を満たしてしまうが、斜面なら
   ``|a − a₂| ≈ |d − a|``(同じ傾きが続く)なので 3 で落ちる。段差の縁の混合は、両側が前景と背景の平らな面なので残る。

r = 1〜*radius* を全部見る(縁の混合が 2 画素に広がる場合)。段差の上の正しい画素(前景か背景のどちらかに等しい)は、
片側との差が 0 なので印がつかない。★幅 1〜2 画素の細い物(線・棒)は両側が背景で「間」にならないので、この判定では
拾えない。

**Raises** ``ValueError``: depth が 2 次元でない・非有限 / 閾値が負・両方 0 / radius が 1〜4 でない /
plateau_ratio が (0, 1] でない / depth_sigma の形が合わない・負 / n_sigma が負。

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
- [tof_realdata](../../../../examples/tof_realdata.py) — `py -3.11 examples/tof_realdata.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [encircled_energy](../imaging/encircled_energy.md) · [ensquared_energy](../imaging/ensquared_energy.md) · [energy_radii](../imaging/energy_radii.md) · [mtf_tangential_sagittal](../imaging/mtf_tangential_sagittal.md)

## 同カテゴリ(`itof`)

[itof_capture](itof_capture.md) · [itof_phase_amplitude](itof_phase_amplitude.md) · [itof_noise_budget](itof_noise_budget.md) · [itof_unwrap_multifreq](itof_unwrap_multifreq.md) · [itof_unwrap_error_rate](itof_unwrap_error_rate.md) · [itof_multipath_separate](itof_multipath_separate.md) · [itof_wiggling_correct](itof_wiggling_correct.md)

---
*Provenance: itof.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
