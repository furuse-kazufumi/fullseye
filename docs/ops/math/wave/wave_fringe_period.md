---
op: wave_fringe_period
dim: math
category: wave
in: image2d
out: measurement
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# wave_fringe_period — MATH `wave` op

- **データ種**: `image2d` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.wave_fringe_period(image, axis=1)` (実装を直接呼ぶなら `import mathops; mathops.wave_fringe_period(image, axis=1)`、台帳から引くなら `opsmath.get("wave_fringe_period")`)

## 使い方

The period of a striped image, measured back out of it (pixels).

Takes the mean profile along *axis*, removes the mean, and reads the dominant
frequency from the FFT with a **parabolic interpolation** on the log spectrum,
so the answer is not quantised to the FFT bin.

★**Why this earns its place**: it closes the loop on :func:`wave_two_slit` and
on any halftone or grating image — the period predicted by the closed form and
the period measured from the pixels are two different computations.

Returns a ``measurement``: the period in pixels.

**Raises** ``ValueError``: not a 2-D array; fewer than 8 samples along *axis*;
non-finite values; a profile with no variation (a flat image has no period).

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

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`wave`)

[wave_membrane_mode](wave_membrane_mode.md) · [wave_mode_frequencies](wave_mode_frequencies.md) · [wave_nodal_lines](wave_nodal_lines.md) · [wave_two_slit](wave_two_slit.md) · [wave_grating_orders](wave_grating_orders.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
