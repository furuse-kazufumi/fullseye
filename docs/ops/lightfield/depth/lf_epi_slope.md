---
op: lf_epi_slope
dim: lightfield
category: depth
in: lightfield
out: image2d
gpu: なし
examples: [lightfield_depth, poc_lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# lf_epi_slope — LIGHTFIELD `depth` op

- **データ種**: `lightfield` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.lf_epi_slope(lf, *, window=9, min_energy=1e-10)` (実装を直接呼ぶなら `import lightfield; lightfield.lf_epi_slope(lf, *, window=9, min_energy=1e-10)`、台帳から引くなら `opslightfield.get("lf_epi_slope")`)
- **台帳経由の戻り値**: `fullseye.ledger.lf_epi_slope(...)` は**宣言 out 型 `image2d` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.lf_epi_slope.raw(...)`、または `lightfield.lf_epi_slope` を直接呼ぶ。
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Per-pixel slope from the **EPI line orientation** (structure tensor, refined by shearing).

A scene point traces a straight line in the epipolar-plane image
(:func:`lf_epi`), so along that line the intensity is constant:
``E_u + s * E_x = 0``. Accumulating that constraint over the whole angular
grid and a ``window x window`` spatial neighbourhood gives the closed-form
least-squares slope ``s = -(J_ux + J_vy) / (J_xx + J_yy)`` with
``J_ab = sum(E_a * E_b)`` — both the horizontal and vertical EPI directions
pooled.

**Why it is iterated (fixed 2026-11-03).** A finite difference across
views measures a displacement of ``s`` px per view, while a finite
difference across pixels measures one of 1 px; for a texture component of
angular frequency ``w`` the ratio is ``sin(w s) / sin(w)`` (the pre-fix
central differences), equal to ``s`` only at ``|s|`` in ``{0, 1}``. That
is the classic statement that the structure tensor is accurate only for
disparities in a small range around zero (Wanner & Goldluecke, CVPR 2012
and TPAMI 36(3) 2014, who handle larger ranges by **shearing** the light
field). So the estimator shears the field by an integer slope ``k``
(integer shifts: no resampling blur), measures the residual
``r = s - k``, sets ``k <- round(k + r)`` per pixel and repeats until no
pixel changes (at most :data:`EPI_MAX_ROUNDS` rounds, at most
:data:`EPI_MAX_SHEARS` distinct shears). The residual is measured with a
matched discretisation (adjacent-view difference against the mean of the
two views' Gaussian derivatives, inner scale :data:`EPI_INNER_SIGMA`), whose
error is ``O(r^3 w^2)`` with ``|r| <= 1/2``.

Measured 2026-11-03, median over the interior of single-layer
``lf_synthesize`` fields (64x64, ``edge="wrap"``), ``s`` in
``[-3, 3]`` in steps of 0.25: error <= 0.006 px for 5x5 and 9x9 views,
<= 0.007 px for 4x4 (even count) and <= 0.012 px for 3x3 and for a single
row of 6 views, at texture sigma 1.0 / 1.5 / 2.0 / 5.0 px, for windows
5 / 9 / 15 (the
pre-fix estimator read -1.388 for -1.5 at sigma 2 and 1.46 for 2.0 at
sigma 1.5). Integer slopes are exact to 1e-9 on a wrapped field.
**Valid range:** the shear ladder starts at ``k = 0``, so the first pass
must see the right sign and a non-vanishing magnitude: that holds for
``|s| <= 3`` at any texture correlation length >= 1 px, and (measured) up
to ``|s| = 8`` at sigma >= 2; at sigma 1 it **fails beyond |s| = 5**
(``s = 6`` read as 0.25 — the texture is aliased: it moves more than its
correlation length several times per view). Near an occlusion boundary the
window mixes two slopes (no estimator of a single orientation per window
can avoid that). With ``edge="nearest"`` input the outer ``|k|*(N-1)/2``
px of the frame see clamped border pixels.

Returns ``(slope_map, energy)``: the ``(H, W)`` slope map (centre-view
coordinates) and the ``(H, W)`` gradient energy ``J_xx + J_yy`` of the
unsheared field (the first pass's denominator). Pixels whose energy is
below *min_energy* have **no** measurable parallax (a flat patch of sky);
their slope is set to 0 and their energy reported as-is, so you threshold
on ``energy`` instead of being handed a plausible-looking number divided by
~0.

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
- [poc_lightfield_depth](../../../../examples/poc_lightfield_depth.py) — `py -3.11 examples/poc_lightfield_depth.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[lf_from_mla](../decode/lf_from_mla.md) · [lf_disparity_to_depth](lf_disparity_to_depth.md) · [lf_all_in_focus](lf_all_in_focus.md)

## 同カテゴリ(`depth`)

[lf_depth_from_focus](lf_depth_from_focus.md) · [lf_disparity_to_depth](lf_disparity_to_depth.md) · [lf_all_in_focus](lf_all_in_focus.md) · [lf_plenoptic_design](lf_plenoptic_design.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
