---
op: vx_remap
dim: vx
category: geometry
in: image2d × matrix × matrix
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# vx_remap — VX `geometry` op

- **データ種**: `image2d × matrix × matrix` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_remap(image, map_x, map_y, *, interpolation, border, constant_value=0)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_remap(image, map_x, map_y, *, interpolation, border, constant_value=0)`、台帳から引くなら `opsvx.get("vx_remap")`)

## 使い方

remap(3.44 節): 出力 (x, y) = 入力 (map_x[y, x], map_y[y, x])(REQ-0392)。表は出力の形、座標は入力の画素の中心が整数。

**Raises** ``ValueError``: U8 の 2-D でない / map_x と map_y が同じ形の 2-D の実数でない / interpolation・border が一覧に無い。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[vx_sobel3x3](../gradient/vx_sobel3x3.md) · [vx_magnitude](../gradient/vx_magnitude.md) · [vx_phase](../gradient/vx_phase.md) · [vx_table_lookup](../pixel/vx_table_lookup.md) · [vx_histogram](../pixel/vx_histogram.md) · [vx_nonmax_suppression](../suppress/vx_nonmax_suppression.md) · [vx_warp_affine](vx_warp_affine.md) · [vx_warp_perspective](vx_warp_perspective.md)

## 同カテゴリ(`geometry`)

[vx_warp_affine](vx_warp_affine.md) · [vx_warp_perspective](vx_warp_perspective.md)

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
