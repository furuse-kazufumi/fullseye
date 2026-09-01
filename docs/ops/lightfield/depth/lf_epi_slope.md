---
op: lf_epi_slope
dim: lightfield
category: depth
in: lightfield
out: image2d
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_epi_slope — LIGHTFIELD `depth` op

- **データ種**: `lightfield` → `image2d`
- **呼び出し**: `import lightfield; lightfield.lf_epi_slope(lf, *, window=9, min_energy=1e-10)` (または `opslightfield.get("lf_epi_slope")`)

## 使い方

Per-pixel slope from the **EPI line orientation** (structure tensor, one pass).

A scene point traces a straight line in the epipolar-plane image
(:func:`lf_epi`), so along that line the intensity is constant:
``E_u + s * E_x = 0``. Accumulating that constraint over the whole angular
grid and a ``window x window`` spatial neighbourhood gives the closed-form
least-squares slope ``s = -(J_ux + J_vy) / (J_xx + J_yy)`` with
``J_ab = sum(E_a * E_b)`` — one pass over the light field, no sweep, both
the horizontal and vertical EPI directions pooled.

**This estimator is biased, and the bias is the reason to also run**
:func:`lf_depth_from_focus`. It is ordinary (not total) least squares on
finite differences, so it needs the EPI line to advance less than roughly
one texture correlation length per view. Measured 2026-09-01 on
5x5x64x64 synthetic fields, median over the interior: with texture
``sigma = 1.5`` px, true ``+1.00 -> +1.0004``, ``+0.50 -> +0.5285``,
``+1.50 -> +1.3018``, ``+2.00 -> +1.4614``; with ``sigma = 5.0`` px the same
slopes give ``+1.0003``, ``+0.5029``, ``+1.4827``, ``+1.9482``. Integer
slopes on a wrapped field come back within 4e-4 and ``s = 0`` is exact;
``|s| > 1`` is under-estimated, by 27% at ``s = 2`` on the roughest texture.
Use it as a fast dense initialiser, not as the final word.

Returns ``(slope_map, energy)``: the ``(H, W)`` slope map and the ``(H, W)``
gradient energy ``J_xx + J_yy`` that was the denominator. Pixels whose
energy is below *min_energy* have **no** measurable parallax (a flat patch
of sky); their slope is set to 0 and their energy reported as-is, so you
threshold on ``energy`` instead of being handed a plausible-looking number
divided by ~0.

**Raises** ``ValueError``: *lf* not a valid light field, an angular/spatial
shape where *neither* EPI direction carries information (the horizontal EPI
needs ``U >= 2`` **and** ``W >= 2``, the vertical needs ``V >= 2`` and
``H >= 2``), an even or non-positive *window*, a non-positive *min_energy*.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[lf_from_mla](../decode/lf_from_mla.md) · [lf_disparity_to_depth](lf_disparity_to_depth.md) · [lf_all_in_focus](lf_all_in_focus.md)

## 同カテゴリ(`depth`)

[lf_depth_from_focus](lf_depth_from_focus.md) · [lf_disparity_to_depth](lf_disparity_to_depth.md) · [lf_all_in_focus](lf_all_in_focus.md) · [lf_plenoptic_design](lf_plenoptic_design.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
