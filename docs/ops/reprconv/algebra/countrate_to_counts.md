---
op: countrate_to_counts
dim: reprconv
category: algebra
in: countrate
out: counts
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# countrate_to_counts — REPRCONV `algebra` op

- **データ種**: `countrate` → `counts`
- **呼び出し**: `import reprconv; reprconv.countrate_to_counts(countrate, gate_s=0.001)` (または `opsreprconv.get("countrate_to_counts")`)

## 使い方

計数レート ``[Hz]`` → 計数 ``counts``。``countrate`` の出口(**可逆**)。

**単位が変換の全内容**: ``[1/s] * [s] = [1]``。``gate_s`` は積算窓の秒数で、
既定 1 ms。``counts`` は「時間 bin ごとの光子数」の型なので、レート列を
そのまま counts と名乗らせると**桁が 7 つずれたまま黙って通る**
(``TYPE_CHECKS`` はどちらも「非負の 1-D」としか見ていない)。

:func:`counts_to_countrate` と往復して実測 max|Δ| = 9.3e-10(値域が 1e3-1e7 Hz なので
**相対** 1e-16 = 倍精度の丸め 1 単位ぶん。絶対値だけ見ると大きく見えるので、
レートのように桁が広い量は相対で言う)。

Args:
    countrate: (N,) の非負レート [Hz]。
    gate_s: 積算窓 [s]。> 0。
Returns:
    (N,) float64 の非負計数。
Raises:
    ValueError: 負のレート / gate_s <= 0 / 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`counts` を入力に取れる)

[counts_to_countrate](counts_to_countrate.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [matrix_to_angle](matrix_to_angle.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [shift_to_vector](shift_to_vector.md) · [vector_to_shift](vector_to_shift.md) · [cscalar_to_polar](cscalar_to_polar.md) · [polar_to_cscalar](polar_to_cscalar.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
