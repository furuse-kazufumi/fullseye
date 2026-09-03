---
op: hash_distance
dim: imgforensics
category: hash
in: phash × phash
out: measurement
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# hash_distance — IMGFORENSICS `hash` op

- **データ種**: `phash × phash` → `measurement`
- **呼び出し**: `import imgforensics; imgforensics.hash_distance(hash1, hash2) -> 'int'` (または `opsimgforensics.get("hash_distance")`)

## 使い方

2 つの知覚ハッシュのハミング距離(異なるビット数)。

**dtype と長さを検査して fail-closed** する。float の 1-D を受け取って
``!=`` で数えると、ほぼ確実に「全ビット違う」= 最大距離という
*もっともらしい* 値が出る —— それは型の取り違えであって画像の違いではない。

返りは Python の ``int``(``measurement`` 語彙)。ビット長で割った
正規化距離が欲しければ ``hash_distance(a, b) / a.size``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[evidence_quantile](../calibration/evidence_quantile.md)

## 同カテゴリ(`hash`)

[perceptual_hash](perceptual_hash.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
