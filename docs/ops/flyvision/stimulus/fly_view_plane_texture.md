---
op: fly_view_plane_texture
dim: flyvision
category: stimulus
in: table
out: signal
gpu: なし
examples: [poc_zebra_stripes_fly_eye]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# fly_view_plane_texture — FLYVISION `stimulus` op

- **データ種**: `table` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_view_plane_texture(lattice, distance_m, period_m, pattern='vertical', drho_deg=8.23, contrast=1.0, mean=0.5, lateral_m=(0.0, 0.0), phase_deg=0.0)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_view_plane_texture(lattice, distance_m, period_m, pattern='vertical', drho_deg=8.23, contrast=1.0, mean=0.5, lateral_m=(0.0, 0.0), phase_deg=0.0)`、台帳から引くなら `opsflyvision.get("fly_view_plane_texture")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

What each ommatidium sees of a periodic frontal surface — integrated analytically.

A plane at *distance_m* ahead of the eye (``x = distance_m`` in body
coordinates, texture in ``(y, z)``) carries a reflectance
``mean * (1 + contrast * s(y, z))`` with ``s`` in ``[-1, 1]``: stripes of
period *period_m* (``"vertical"`` modulates along y, ``"horizontal"`` along
z), a ``"checker"`` of that period, a pure ``"sine"``, a deterministic 1/f
``"pink"`` texture whose longest wavelength is *period_m* (24 plane waves
with amplitudes summing to 1, so its rms contrast is 0.18 of *contrast*),
or ``"grey"``.
Each ommatidium integrates the surface under a Gaussian acceptance of FWHM
*drho_deg* — **without rendering or resampling an image**. The texture is a
cosine series; a surface wave vector ``k`` becomes the angular wave vector
``J^T k`` at the ommatidium (``J`` the exact derivative of the line-of-sight
intercept), and a Gaussian acceptance multiplies each term by
``exp(-pi^2 drho^2 |J^T k|^2 / (4 ln2))``. That is the small-footprint
approximation :func:`fly_hex_resample` documents, applied term by term, with
no pixel grid in between.

lattice:   a :func:`fly_hex_lattice` or :func:`fly_vogel_lattice` result.
distance_m / period_m: the plane's distance and the texture period, metres.
pattern:   one of :data:`PLANE_PATTERNS`.
drho_deg:  the acceptance FWHM, degrees.
contrast:  the Michelson contrast of the texture, ``0 <= contrast <= 1``.
mean:      the mean reflectance (> 0).
lateral_m: the eye's ``(y, z)`` offset from the texture origin, metres — the
           fly's sideways position, which shifts the stripe phase.
phase_deg: an extra texture shift, in degrees of one period.

Returns a 1-D float64 signal of ``n`` ommatidial intensities (>= 0). An
ommatidium whose line of sight does not reach the plane (``d_x <= 0``) reads
*mean* — the surface is not in its field, and a texture at an infinite
distance has zero modulation anyway.

Square waves keep their odd harmonics up to where the acceptance has
attenuated them below 1e-6 (at most :data:`MAX_HARMONIC`); a checkerboard is
the product of two such series. The partial sum is then already smoothed, so
there is no Gibbs overshoot to clip; a ``maximum(., 0)`` guards rounding.

Ground truth (pinned in the tests): for ``pattern="sine"`` the amplitude at
the central ommatidium is ``contrast * mean * exp(-pi^2 drho^2 (D/P)^2 /
(4 ln2))`` with ``drho`` in radians, and at an ommatidium at azimuth
``theta`` the angular frequency is ``D/(P cos^2 theta)`` — both to 1e-9.

**Raises** ``ValueError``: a malformed *lattice* (an empty dict is refused —
it has none of the lattice keys), a non-positive *distance_m* / *period_m* /
*drho_deg* / *mean*, a *contrast* outside ``[0, 1]``, a *lateral_m* that is
not two finite numbers, a non-finite *phase_deg*, and an unknown *pattern*.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_zebra_stripes_fly_eye](../../../../examples/poc_zebra_stripes_fly_eye.py) — `py -3.11 examples/poc_zebra_stripes_fly_eye.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fly_hex_quantize](../sample/fly_hex_quantize.md) · [fly_emd_response](../motion/fly_emd_response.md) · [fly_lgmd_eta](../looming/fly_lgmd_eta.md) · [fly_tau_from_expansion](../looming/fly_tau_from_expansion.md) · [lattice_moire_peak](../alias/lattice_moire_peak.md) · [traj_tau_dot](../trajectory/traj_tau_dot.md) · [fly_dsi](../tuning/fly_dsi.md)

## 同カテゴリ(`stimulus`)

[fly_sky_1f](fly_sky_1f.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
