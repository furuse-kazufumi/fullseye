---
op: vx_table_lookup
dim: vx
category: pixel
in: image2d × signal
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# vx_table_lookup — VX `pixel` op

- **データ種**: `image2d × signal` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_table_lookup(image, table, *, offset=0)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_table_lookup(image, table, *, offset=0)`、台帳から引くなら `opsvx.get("vx_table_lookup")`)

## 使い方

表引き(3.47 節): 出力 = table[画素値 + offset] (REQ-0421)。U8 と S16 を受ける(REQ-0422)。出力の dtype は表の dtype。

*offset*: S16 の表は負の画素値を引くために中央を 0 に置く(VX_LUT_OFFSET、典型は 32768)。U8 は 0。
★表の外を引く画素があれば止める(黙って端に寄せない)。

**Raises** ``ValueError``: 画像が U8/S16 の 2-D でない / 表が 1-D でない・空 / 表の外を引く画素がある。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[vx_sobel3x3](../gradient/vx_sobel3x3.md) · [vx_magnitude](../gradient/vx_magnitude.md) · [vx_phase](../gradient/vx_phase.md) · [vx_histogram](vx_histogram.md) · [vx_nonmax_suppression](../suppress/vx_nonmax_suppression.md) · [vx_warp_affine](../geometry/vx_warp_affine.md) · [vx_warp_perspective](../geometry/vx_warp_perspective.md) · [vx_remap](../geometry/vx_remap.md)

## 同カテゴリ(`pixel`)

[vx_histogram](vx_histogram.md)

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
