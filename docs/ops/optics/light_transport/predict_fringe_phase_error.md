---
op: predict_fringe_phase_error
dim: optics
category: light_transport
in: table
out: table
gpu: なし
examples: [poc_interreflection_fringe_error]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# predict_fringe_phase_error — OPTICS `light_transport` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.predict_fringe_phase_error(transport, period=16.0, triangulation_deg=20.0, projector_width=None, irradiance=1.0)` (実装を直接呼ぶなら `import lighttransport; lighttransport.predict_fringe_phase_error(transport, period=16.0, triangulation_deg=20.0, projector_width=None, irradiance=1.0)`、台帳から引くなら `opsoptics.get("predict_fringe_phase_error")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Predict, per camera pixel, the fringe-phase bias and height error that interreflection causes in phase-shifting profilometry, from the light-transport matrix.

A sinusoid of *period* projector pixels illuminates patch ``i`` with the
complex amplitude ``ζ_i = n_i·d · mean_footprint(e^{i 2π x / period})``.
The camera sees ``Z = T (irradiance · ζ)``; its direct part is
``ρ_i · irradiance · ζ_i`` and the rest is the global phasor. The decoded
phase is the argument of the sum (:func:`fringe_multipath_phase_error`).
The height error follows from ``u = x cos β − z sin β``:
``Δz = −Δu / sin β`` with ``Δu = bias · period · pitch / (2π)``
(*pitch* = projector pixel in scene units).

*transport* from :func:`transport_matrix_radiosity`;
*projector_width* (default: the number of patches) must match the pattern
width given to :func:`render_transport` for the two to agree.

Returns a dict (a ``table``): ``bias`` (rad, (P,)), ``height_error``
(scene units, (P,)), ``direct_amplitude``, ``direct_phase``,
``global_amplitude``, ``global_phase``, ``ratio``, ``worst_case``,
``pitch`` and ``x`` (patch centres).

**Raises** ``ValueError``: not a transport table; *period* ``<= 2``;
*triangulation_deg* outside ``(0, 80]`` or a shadowed patch;
*projector_width* not an integer in ``[2, 1<<16]``; *irradiance* ``<= 0``.

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

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`light_transport`)

[groove_profile](groove_profile.md) · [form_factors_2d](form_factors_2d.md) · [transport_matrix_radiosity](transport_matrix_radiosity.md) · [high_frequency_patterns](high_frequency_patterns.md) · [render_transport](render_transport.md) · [separate_direct_global](separate_direct_global.md) · [fringe_multipath_phase_error](fringe_multipath_phase_error.md) · [micro_phase_decode](micro_phase_decode.md)

---
*Provenance: lighttransport.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
