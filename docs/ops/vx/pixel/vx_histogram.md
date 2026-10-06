---
op: vx_histogram
dim: vx
category: pixel
in: image2d
out: pairs
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# vx_histogram — VX `pixel` op

- **データ種**: `image2d` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_histogram(image, *, num_bins, offset, range_)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_histogram(image, *, num_bins, offset, range_)`、台帳から引くなら `opsvx.get("vx_histogram")`)

## 使い方

ヒストグラム(3.26 節): 画素値 I は ``i = (I − offset) × numBins / range`` の升に入る(offset ≤ I < offset + range、REQ-0230)。
範囲外の画素は数えない。整数の割り算(切り捨て)で升を決める。

返り値 ``(num_bins, 2)`` の pairs: 列 0 = 升の下端の画素値(offset + i·range/numBins)、列 1 = 数。

**Raises** ``ValueError``: U8 の 2-D でない / num_bins・range_ が正でない / num_bins > range_ / offset が負。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`pixel`)

[vx_table_lookup](vx_table_lookup.md)

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
