---
op: high_frequency_patterns
dim: optics
category: light_transport
in: 
out: images
examples: [poc_interreflection_fringe_error]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# high_frequency_patterns — OPTICS `light_transport` op

- **データ種**: `なし` → `images`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.high_frequency_patterns(shape=(1, 256), period=8, kind='stripes', fill=0.5, n_shifts=None, complement=False)` (実装を直接呼ぶなら `import lighttransport; lighttransport.high_frequency_patterns(shape=(1, 256), period=8, kind='stripes', fill=0.5, n_shifts=None, complement=False)`、台帳から引くなら `opsoptics.get("high_frequency_patterns")`)

## 使い方

Shifted high-frequency projector patterns: binary stripes with fill ratio α, a checkerboard, or phase-shifted sinusoids (one or several periods).

*shape* ``(H, W)`` is the projector frame; ``x`` is the column index.

* ``"stripes"`` — ``1`` where ``(x − s_k) mod period < α·period``, for
  shifts ``s_k = floor(k·period/n_shifts)``; *period* an integer ``>= 2``
  and ``α·period`` must be a whole number of pixels (the realised fill is
  then exactly α — a rounded fill would bias the separation). Default
  ``n_shifts = period`` (every pixel is lit and unlit at least once).
  *complement* appends ``1 − p`` for each pattern (Nayar et al. eq. 7).
* ``"checker"`` — squares of side ``period/2`` (``α = 0.5``), shifted by
  ``floor(k·period/n_shifts)`` in both axes (``n_shifts²`` images, default
  ``n_shifts = min(period, 5)``). Not a 2-D problem, so
  :func:`render_transport` refuses it; it is for real captures.
* ``"sinusoid"`` — ``0.5 + 0.5 cos(2π x / period − 2π n / N)``,
  ``n = 0..N−1``, ``N = n_shifts`` (default 4, ``>= 3``) — the sign
  convention of ``fringe.wrapped_phase``, which returns ``2π x / period``.
  *period* may be a sequence (a micro phase-shifting set): the stacks are
  concatenated in that order. *fill* must stay 0.5 here.

Returns a list of ``(H, W)`` float arrays in ``[0, 1]`` (``images``).

**Raises** ``ValueError``: bad *shape*; unknown *kind*; *period* out of
range (stripes/checker integer ``>= 2``, checker even; sinusoid ``> 2``);
*fill* outside ``(0, 1)`` or not a whole number of pixels per period
(checker and sinusoid: not 0.5); *n_shifts* out of range; *complement*
with a kind other than stripes.

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

## 型が繋がる次の op(`images` を入力に取れる)

[film_thickness_map](../film/film_thickness_map.md) · [equirect_stabilize](../omni360/equirect_stabilize.md) · [equirect_from_fisheye_pair](../omni360/equirect_from_fisheye_pair.md) · [equirect_from_perspectives](../omni360/equirect_from_perspectives.md) · [grating_three_image_retrieve](../grating_interf/grating_three_image_retrieve.md) · [grating_step_period_estimate](../grating_interf/grating_step_period_estimate.md) · [retardation_unwrap_multiwavelength](../photoelastic/retardation_unwrap_multiwavelength.md) · [render_transport](render_transport.md)

## 同カテゴリ(`light_transport`)

[groove_profile](groove_profile.md) · [form_factors_2d](form_factors_2d.md) · [transport_matrix_radiosity](transport_matrix_radiosity.md) · [render_transport](render_transport.md) · [separate_direct_global](separate_direct_global.md) · [fringe_multipath_phase_error](fringe_multipath_phase_error.md) · [predict_fringe_phase_error](predict_fringe_phase_error.md) · [micro_phase_decode](micro_phase_decode.md)

---
*Provenance: lighttransport.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
