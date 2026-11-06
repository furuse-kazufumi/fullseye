---
op: camera_response_robertson
dim: optics
category: hdr
in: images
out: table
gpu: なし
examples: [poc_hdr_glossy_metal_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# camera_response_robertson — OPTICS `hdr` op

- **データ種**: `images` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_response_robertson(images, exposures, levels=256, max_iter=30, tol=1e-06, max_pixels=200000)` (実装を直接呼ぶなら `import hdrfusion; hdrfusion.camera_response_robertson(images, exposures, levels=256, max_iter=30, tol=1e-06, max_pixels=200000)`、台帳から引くなら `opsoptics.get("camera_response_robertson")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Inverse camera response by Robertson, Borman & Stevenson's alternating estimate (``table``).

``E_i = Σ_j w(Z_ij) t_j I(Z_ij) / Σ_j w(Z_ij) t_j²``(放射輝度)と
``I(m) = mean{ t_j E_i : Z_ij = m }``(逆応答)を交互に、``I((L−1)/2) = 1`` で正規化して
相対変化が ``tol`` を切るまで。重みはガウス ``exp(−4 (z − c)²/c²)`` で、両端の段(0 と L−1 =
真っ黒と飽和)は 0(放射輝度の式が ``w t²`` で重むので、端に残る小さな重みでも飽和した長い露出が
支配する —— 実測)。画素は ``max_pixels`` 個
まで等間隔に間引く(決定的)。観測の無い段は隣の段から線形補間。

Returns the same table as :func:`camera_response_debevec` (``method="robertson"``, with
``iterations`` and ``converged``). ★``max_iter=30`` follows OpenCV's ``CalibrateRobertson``
default. With noisy data the fixed point is biased near both ends (censored pixels just below
saturation / just above the dark offset): measured on a 5-exposure EMVA series, the ln error at
level 240 grows from −0.03 (20 iterations) to −0.25 (500) while mid levels stay within 0.02 —
more iterations is not better. Debevec's smoothness prior does not drift this way. The scale is fixed by ``I(mid) = 1`` (``g(mid) = 0``).

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

- [poc_hdr_glossy_metal_inspection](../../../../examples/poc_hdr_glossy_metal_inspection.py) — `py -3.11 examples/poc_hdr_glossy_metal_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`hdr`)

[camera_response_debevec](camera_response_debevec.md) · [camera_response_linear](camera_response_linear.md) · [hdr_merge](hdr_merge.md) · [exposure_fusion_mertens](exposure_fusion_mertens.md) · [hdr_exposure_series_simulate](hdr_exposure_series_simulate.md) · [hdr_radiance_error](hdr_radiance_error.md) · [hdr_dynamic_range](hdr_dynamic_range.md)

---
*Provenance: hdrfusion.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
