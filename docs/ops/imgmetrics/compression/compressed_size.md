---
op: compressed_size
dim: imgmetrics
category: compression
in: image2d
out: scalar
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# compressed_size — IMGMETRICS `compression` op

- **データ種**: `image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.compressed_size(a, compressor='lzma')` (または `opsimgmetrics.get("compressed_size")`)

## 使い方

配列を可逆圧縮したバイト数。``ncd`` の材料。

画像コーデックは**使わない** ―― 挟むとその実装の癖を測ってしまう。
stdlib の ``zlib`` / ``lzma`` のみ。dtype と shape の違いが結果を変える
ので、比べる 2 枚は同じ dtype・同じ shape であること。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`compression`)

[ncd](ncd.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
