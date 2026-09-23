---
op: wave_grating_orders
dim: math
category: wave
in: 
out: table
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# wave_grating_orders — MATH `wave` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.wave_grating_orders(pitch_um=1.6, wavelength_nm=550.0, sin_in=0.0, orders=(-2, -1, 1, 2))` (実装を直接呼ぶなら `import mathops; mathops.wave_grating_orders(pitch_um=1.6, wavelength_nm=550.0, sin_in=0.0, orders=(-2, -1, 1, 2))`、台帳から引くなら `opsmath.get("wave_grating_orders")`)

## 使い方

Where a grating sends each order: ``d (sin_out - sin_in) = m lambda`` solved for the angle.

The companion to the existing ``grating_wavelengths`` (which solves the same
identity for *lambda*): given the pitch and the wavelength, this returns the
outgoing direction of each order, and marks the orders that are
**evanescent** — ``|sin_out| > 1`` means that order does not propagate, which
is why a CD shows fewer colours at grazing incidence.

★**Why this earns its place**: the two ops invert one another, so a round trip
must return the wavelength it started from; and the angles can be compared
against the peak positions of a *simulated* far field (the existing
``fraunhofer_pattern`` of a real grating aperture), which knows nothing about
the grating equation.

Returns a ``table``: ``order``, ``sin_out``, ``angle_deg`` (NaN when
evanescent), ``propagates``.

**Raises** ``ValueError``: non-positive pitch or wavelength; ``|sin_in| > 1``;
order 0 alone with no others (it is always the specular direction — allowed,
but a caller asking only for it probably meant something else); non-finite input.

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

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md)

## 同カテゴリ(`wave`)

[wave_membrane_mode](wave_membrane_mode.md) · [wave_mode_frequencies](wave_mode_frequencies.md) · [wave_nodal_lines](wave_nodal_lines.md) · [wave_two_slit](wave_two_slit.md) · [wave_fringe_period](wave_fringe_period.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
