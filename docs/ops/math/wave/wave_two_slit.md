---
op: wave_two_slit
dim: math
category: wave
in: 
out: image2d
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# wave_two_slit — MATH `wave` op

- **データ種**: `なし` → `image2d`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.wave_two_slit(wavelength_nm=550.0, slit_sep_um=20.0, distance_mm=200.0, shape=(256, 512), pixel_um=5.0, slit_width_um=2.0)` (実装を直接呼ぶなら `import mathops; mathops.wave_two_slit(wavelength_nm=550.0, slit_sep_um=20.0, distance_mm=200.0, shape=(256, 512), pixel_um=5.0, slit_width_um=2.0)`、台帳から引くなら `opsmath.get("wave_two_slit")`)

## 使い方

Two-slit interference on a screen — built from the physics, not the fringe formula.

Each slit is treated as a line source of the given width; the screen intensity
is ``|sum over slit of exp(i k R) / sqrt(R)|**2`` with ``R`` the true distance
from each source point. **The textbook spacing ``lambda D / d`` is nowhere in
this computation** — which is the point: it is then available as an
independent prediction to check the picture against.

★**Why this earns its place**: :func:`wave_fringe_period` measures the period
of the produced image, and it must land on ``lambda D / d`` (in pixels,
``lambda D / (d * pixel)``). Two ways to the same number, only one of which
was used to draw.

Returns an ``image2d`` normalised to a peak of 1.

**Raises** ``ValueError``: non-positive wavelength, separation, distance,
pixel or width; a grid over the cap; a geometry so coarse that fewer than
three fringes fit on the screen (reported, not silently aliased).

Limits: scalar, monochromatic, far-from-paraxial geometries are not modelled;
the slits are lines, so there is no vertical structure.

## ファミリ共通の入力契約(fail-closed)

mathops の全 op は入力を検証してから計算する(黙って通さない):

- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。
- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。
- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。
- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。
- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は `mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。

## 詳しい使い方ガイド

- [math_metrology ファミリ ガイド](../guides/math_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[wave_fringe_period](wave_fringe_period.md)

## 同カテゴリ(`wave`)

[wave_membrane_mode](wave_membrane_mode.md) · [wave_mode_frequencies](wave_mode_frequencies.md) · [wave_nodal_lines](wave_nodal_lines.md) · [wave_fringe_period](wave_fringe_period.md) · [wave_grating_orders](wave_grating_orders.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
