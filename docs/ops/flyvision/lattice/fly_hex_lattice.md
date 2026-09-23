---
op: fly_hex_lattice
dim: flyvision
category: lattice
in: 
out: table
examples: [poc_fly_optomotor_steering, poc_fly_vision, poc_print_registration]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# fly_hex_lattice — FLYVISION `lattice` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_hex_lattice(radius=15, dphi_deg=4.63, az0_deg=0.0, el0_deg=0.0, geometry='regular')` (実装を直接呼ぶなら `import flyvision; flyvision.fly_hex_lattice(radius=15, dphi_deg=4.63, az0_deg=0.0, el0_deg=0.0, geometry='regular')`、台帳から引くなら `opsflyvision.get("fly_hex_lattice")`)

## 使い方

Hexagonal ommatidial lattice: viewing directions of a compound eye.

A hexagon of ``n = 3*radius*(radius+1)+1`` ommatidia on axial coordinates
``(u, v)`` with ``-radius <= u <= radius`` and
``max(-radius, -radius-u) <= v <= min(radius, radius-u)`` (u outer, v inner),
each given an azimuth, an elevation and a unit viewing direction in body
coordinates (x forward, y left, z up; ``az = atan2(y, x)`` left positive,
``el = asin(z)``).

``geometry="regular"``:  ``az = az0 + dphi*(v + u/2)``,
``el = el0 + dphi*(sqrt(3)/2)*u`` — an isotropic hexagon.
``geometry="boxeye"``:   the pixel-grid distortion of the connectome-derived
models, ``pixel (y, x) = (13*(u + v/2), 13*v)`` with ``13 px = dphi``, so
``az = az0 - v*dphi`` and ``el = el0 - (u + v/2)*dphi``; the diagonal neighbour
is 1.118x the axial spacing.

radius:    the hexagon radius in ommatidia.
dphi_deg:  the inter-ommatidial angle in degrees.
az0_deg / el0_deg: the direction of the lattice centre (the optical axis).
geometry:  one of :data:`GEOMETRIES`.

Returns a dict ``{"uv": (n,2) int, "az_rad": (n,), "el_rad": (n,),
"dirs": (n,3) unit vectors, "dphi_rad": float, "geometry": str}``.

Ground truth: ``n == 3*radius*(radius+1)+1`` exactly, every ``dirs`` row is a
unit vector, and for ``"boxeye"`` the ratio of the diagonal to the axial
nearest-neighbour angular spacing is 1.118 (both pinned in the tests).

**Raises** ``ValueError``: a *radius* outside ``[1, MAX_LATTICE_RADIUS]``, a
non-positive *dphi_deg*, a non-real / non-finite / string / bool angle, and an
unknown *geometry*.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`
- [poc_fly_vision](../../../../examples/poc_fly_vision.py) — `py -3.11 examples/poc_fly_vision.py`
- [poc_print_registration](../../../../examples/poc_print_registration.py) — `py -3.11 examples/poc_print_registration.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_matched_filter](../selfmotion/fly_matched_filter.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_eye_merge](../selfmotion/fly_eye_merge.md) · [fly_hex_resample](../sample/fly_hex_resample.md) · [fly_hs_readout](../integrate/fly_hs_readout.md)

## 同カテゴリ(`lattice`)

—

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
