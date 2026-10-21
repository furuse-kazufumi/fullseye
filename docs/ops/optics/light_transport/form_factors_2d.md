---
op: form_factors_2d
dim: optics
category: light_transport
in: table
out: matrix
examples: [poc_interreflection_fringe_error, poc_itof_multifreq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# form_factors_2d — OPTICS `light_transport` op

- **データ種**: `table` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.form_factors_2d(profile)` (実装を直接呼ぶなら `import lighttransport; lighttransport.form_factors_2d(profile)`、台帳から引くなら `opsoptics.get("form_factors_2d")`)

## 使い方

Patch-to-patch form factors of a concave 2-D (extruded) cross-section by Hottel's crossed-strings rule.

For strips ``i`` and ``j`` of an extruded surface that see each other
unobstructed (always true on a concave cross-section),
``F_ij = [(crossed strings) − (uncrossed strings)] / (2 L_i)`` — the
fraction of the energy leaving strip ``i`` that lands on strip ``j``.
Exact (no quadrature); reciprocity ``L_i F_ij = L_j F_ji`` holds by
construction, ``F_ii = 0`` for flat patches, and each row plus the
form factor to the opening sums to 1 (the closed polygon is an enclosure).

*profile* is a ``table`` from :func:`groove_profile`. Returns the
``(P, P)`` matrix (``matrix``).

**Raises** ``ValueError``: *profile* is not a ``groove_profile`` table or
its vertices are not a concave function ``z(x)``.

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

- [poc_interreflection_fringe_error](../../../../examples/poc_interreflection_fringe_error.py) — `py -3.11 examples/poc_interreflection_fringe_error.py`
- [poc_itof_multifreq](../../../../examples/poc_itof_multifreq.py) — `py -3.11 examples/poc_itof_multifreq.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[abcd_trace](../geometric/abcd_trace.md) · [emva_filter_distortion](../sensorchar/emva_filter_distortion.md) · [mueller_apply](../polarization/mueller_apply.md) · [mueller_checks](../polarization/mueller_checks.md) · [equirect_rotate](../omni360/equirect_rotate.md) · [pixel_shift_capture](../pixelshift/pixel_shift_capture.md) · [pixel_shift_merge](../pixelshift/pixel_shift_merge.md) · [pixel_shift_motion_mask](../pixelshift/pixel_shift_motion_mask.md)

## 同カテゴリ(`light_transport`)

[groove_profile](groove_profile.md) · [transport_matrix_radiosity](transport_matrix_radiosity.md) · [high_frequency_patterns](high_frequency_patterns.md) · [render_transport](render_transport.md) · [separate_direct_global](separate_direct_global.md) · [fringe_multipath_phase_error](fringe_multipath_phase_error.md) · [predict_fringe_phase_error](predict_fringe_phase_error.md) · [micro_phase_decode](micro_phase_decode.md)

---
*Provenance: lighttransport.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
