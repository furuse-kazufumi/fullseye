---
op: fly_vogel_lattice
dim: flyvision
category: lattice
in: 
out: table
examples: [poc_zebra_stripes_fly_eye]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# fly_vogel_lattice — FLYVISION `lattice` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_vogel_lattice(radius=15, dphi_deg=4.63, az0_deg=0.0, el0_deg=0.0, density_power=0.5, angle_deg=np.float64(137.50776405003785))` (実装を直接呼ぶなら `import flyvision; flyvision.fly_vogel_lattice(radius=15, dphi_deg=4.63, az0_deg=0.0, el0_deg=0.0, density_power=0.5, angle_deg=np.float64(137.50776405003785))`、台帳から引くなら `opsflyvision.get("fly_vogel_lattice")`)

## 使い方

A Fibonacci (Vogel-spiral) compound eye: the same ommatidia count and the
same mean spacing as the hexagonal eye, no lattice at all.

Point ``k`` sits at the angular radius ``rho_k = rho_max ((k + 1/2)/n)^p`` from
the optical axis and at the position angle ``k * angle_deg`` around it — the
arrangement of sunflower florets (Vogel 1979), here on the sphere. The
ommatidia count is the hexagon's ``n = 3 radius (radius + 1) + 1`` and
``rho_max`` is solved so that the **mean nearest-neighbour angle equals
dphi_deg**, which makes the two eyes directly comparable: same number of
samples, same average density, and only the *arrangement* differs. The
reciprocal of a hexagonal lattice is six sharp points, so a texture past its
Nyquist limit folds into one sharp false stripe (moire); the Vogel spiral
has no reciprocal lattice, so the same texture folds into a ring of weak
noise — the question the zebra PoC asks is which an eye would rather have.

radius / dphi_deg / az0_deg / el0_deg: as :func:`fly_hex_lattice`.
density_power: ``p`` in ``(0, 1]``. ``0.5`` is uniform density; above it the
    centre is denser (a fovea / acute zone: density ∝ k^(1 - 2p)), below it
    the rim is.
angle_deg: the divergence angle, the golden angle by default.

Returns a lattice dict with the keys of :func:`fly_hex_lattice` — ``"uv"``
holds ``(k, 0)``, the spiral index, so ``(0, 0)`` is still the ommatidium
nearest the axis — plus ``"geometry": "vogel"``, ``"rho_rad"`` (the angular
radius of each ommatidium), ``"nn_rad"`` (its nearest-neighbour angle) and
``"density_power"``. The ops that need a *hexagonal neighbour*
(:func:`fly_t4t5_field`, :func:`fly_flow_from_directions`) refuse it; the
ops that need only directions (:func:`fly_view_plane_texture`,
:func:`fly_expansion_readout`, :func:`lattice_moire_peak`,
:func:`fly_matched_filter`, :func:`fly_egomotion_from_flow`) take it.

Ground truth (pinned in the tests): ``n == 3 radius (radius + 1) + 1``, every
direction is a unit vector, ``mean(nn_rad) == dphi`` to 1e-6, the
coefficient of variation of the nearest-neighbour angle at ``p = 0.5`` is
0.012 (below 0.03; a hexagon's is 0, and ``p = 0.65`` gives 0.14), and the
Delaunay triangulation of the gnomonic projection has a mean degree within
0.5 of 6 (5.85 for 721 ommatidia; the deficit is the rim).

**Raises** ``ValueError``: a *radius* outside ``[2, MAX_LATTICE_RADIUS]``, a
non-positive *dphi_deg*, a *density_power* outside ``(0, 1]``, a non-finite
angle, and a divergence angle that is a multiple of 360 (all points on one
ray).

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_zebra_stripes_fly_eye](../../../../examples/poc_zebra_stripes_fly_eye.py) — `py -3.11 examples/poc_zebra_stripes_fly_eye.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_matched_filter](../selfmotion/fly_matched_filter.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_eye_merge](../selfmotion/fly_eye_merge.md) · [fly_view_plane_texture](../stimulus/fly_view_plane_texture.md) · [fly_hex_resample](../sample/fly_hex_resample.md) · [fly_expansion_readout](../looming/fly_expansion_readout.md)

## 同カテゴリ(`lattice`)

[fly_hex_lattice](fly_hex_lattice.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
