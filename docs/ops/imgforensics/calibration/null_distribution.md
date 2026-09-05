---
op: null_distribution
dim: imgforensics
category: calibration
in: signal
out: table
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# null_distribution — IMGFORENSICS `calibration` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import imgforensics; imgforensics.null_distribution(values)` (または `opsimgforensics.get("null_distribution")`)

## 使い方

**改竄が無い**と分かっている標本から、証拠量の帰無分布をまとめる。

この族は一貫して判定を返さない。それは正しいが、そのままだと利用者は
``PCE 1832`` のような数値を渡されて**解釈する手段が無い**。かといって
しきい値を同梱すると嘘になる ―― 分離点は枚数・解像度・圧縮率・被写体で
動くので、出荷時に決められる値ではない。

そこで**利用者自身の清浄データから分布を測る**。同梱するのは「しきい値」
ではなく「しきい値の測り方」で、それなら条件が変わっても正しいままでいる。

Parameters
----------
values : array_like
    改竄が無いと分かっている組で測った証拠量(``hash_distance`` や
    ``fingerprint_correlate()["pce"]`` など)。**同じ条件**で集めること。

Returns
-------
dict
    ``n`` / ``mean`` / ``std`` / ``min`` / ``max`` / ``quantiles``
    (5, 25, 50, 75, 95, 99 パーセンタイル)。標本が少ないと裾は測れない
    ので ``n < 20`` は ``caveats`` に出す(黙って外挿しない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`table` を入力に取れる)

[evidence_quantile](evidence_quantile.md)

## 同カテゴリ(`calibration`)

[evidence_quantile](evidence_quantile.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
