---
op: sampling_alias_distance
dim: flyvision
category: alias
in: 
out: table
examples: [poc_zebra_stripes_fly_eye]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sampling_alias_distance — FLYVISION `alias` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sampling_alias_distance(period_m, pitch_deg, lattice='hex', view_angle_deg=0.0, acceptance_deg=0.0, obliquity='along')` (実装を直接呼ぶなら `import flyvision; flyvision.sampling_alias_distance(period_m, pitch_deg, lattice='hex', view_angle_deg=0.0, acceptance_deg=0.0, obliquity='along')`、台帳から引くなら `opsflyvision.get("sampling_alias_distance")`)

## 使い方

The distance beyond which a periodic target aliases on a sampling lattice.

A period *period_m* seen from distance ``d`` at viewing angle ``theta`` has
the angular period ``P cos^2(theta)/d`` (the cos^2 is the derivative of the
line-of-sight intercept; ``obliquity="across"`` — the period runs
perpendicular to the plane of obliquity — makes it a single cos). A lattice
of pitch *pitch_deg* resolves angular periods down to ``sqrt(3) * pitch``
(hexagonal: the inscribed circle of its Brillouin zone) or ``2 * pitch``
(square), so the target aliases once::

    d > period_m * cos^2(theta) / (sqrt(3) * pitch)      (hex)
    d > period_m * cos^2(theta) / (2 * pitch)            (square)

The same number is the **working-distance rule of an inspection camera**:
*pitch_deg* is the pixel's instantaneous field of view, *period_m* the pitch
of the display, mesh, weave or halftone being inspected, and beyond the
returned distance the picture carries a moire that is not in the part
(Petersen & Middleton 1962 for the lattice Nyquist regions).

period_m:  the target's spatial period, metres.
pitch_deg: the sample spacing — inter-ommatidial angle or pixel IFOV, degrees.
lattice:   one of :data:`SAMPLING_LATTICES`.
view_angle_deg: the obliquity of the line of sight, ``|theta| < 90``.
acceptance_deg: the FWHM of the Gaussian acceptance (or pixel blur), degrees;
           ``0`` means a delta sampler.
obliquity: one of :data:`OBLIQUITIES`.

Returns a dict ``{"distance_m", "nyquist_cycles_per_rad", "period_floor_deg",
"mtf_at_nyquist", "lattice", "view_angle_deg"}`` — the alias distance, the
lattice's Nyquist frequency, the smallest angular period it resolves, and the
acceptance's modulation transfer at that limit (1.0 for a delta sampler).

Ground truth (pinned in the tests): a 7 cm period on a 1.1-degree hexagonal
eye aliases beyond 2.105 m head-on and 0.526 m at 60 degrees; on a
4.63-degree eye beyond 0.500 m and 0.125 m; with a 1-degree acceptance the
hexagonal 1.1-degree eye keeps 0.375 of the contrast at Nyquist, the
8.23-degree acceptance of a 4.63-degree eye keeps 0.024.

**Raises** ``ValueError``: a non-positive *period_m* / *pitch_deg* (an empty
*period_m* is refused as not a number), a negative *acceptance_deg*, a
*view_angle_deg* at or beyond 90, and an unknown *lattice* / *obliquity*.

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

## 同カテゴリ(`alias`)

[lattice_moire_peak](lattice_moire_peak.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
