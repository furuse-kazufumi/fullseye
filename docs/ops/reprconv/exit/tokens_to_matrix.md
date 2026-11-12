---
op: tokens_to_matrix
dim: reprconv
category: exit
in: tokens
out: matrix
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# tokens_to_matrix — REPRCONV `exit` op

- **データ種**: `tokens` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.tokens_to_matrix(tokens)` (実装を直接呼ぶなら `import reprconv; reprconv.tokens_to_matrix(tokens)`、台帳から引くなら `opsreprconv.get("tokens_to_matrix")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

トークン列 ``tokens (T, d)`` → 一般の行列 ``matrix (T, d)``。``tokens`` 型の出口。

中身は変えない(写しを返す)。``tokens`` を ``matrix`` と分けてあるのは、**入る側**で
転置した (d, T) が黙って通るのを防ぐため(``opsllmcore`` の docstring)で、出る側は
一般の行列として扱ってよい —— SVD・条件数・ノルムなど ``matrix`` の op がそのまま掛かる
(例: 注意の出力の実効次数を ``mat_cond`` で見る)。逆向き(``matrix`` → ``tokens``)は
軸の順を確かめようがないので作らない。

Args:
    tokens: (T, d) の有限な実数列。
Returns:
    (T, d) float64。
Raises:
    ValueError: 2-D でない / 非有限 / 空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[matrix_to_descriptor](../descriptor/matrix_to_descriptor.md) · [matrix_to_angle](../algebra/matrix_to_angle.md) · [matrix_to_rot_scale](../algebra/matrix_to_rot_scale.md)

## 同カテゴリ(`exit`)

[pose_to_matrix](pose_to_matrix.md) · [pairs_peak_x](pairs_peak_x.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
