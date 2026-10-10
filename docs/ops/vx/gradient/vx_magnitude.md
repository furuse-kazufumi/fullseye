---
op: vx_magnitude
dim: vx
category: gradient
in: image2d × image2d
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# vx_magnitude — VX `gradient` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_magnitude(gx, gy)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_magnitude(gx, gy)`、台帳から引くなら `opsvx.get("vx_magnitude")`)

## 使い方

勾配の大きさ(3.31 節)。REQ-0270 の概念定義をそのまま: ``z = uint16(sqrt(double(uint32(x·x) + uint32(y·y))) + 0.5)``、
``mag = z > 32767 ? 32767 : z``。入力・出力とも S16。

**Raises** ``ValueError``: S16 の 2-D でない / 形が違う。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[vx_sobel3x3](vx_sobel3x3.md) · [vx_phase](vx_phase.md) · [vx_table_lookup](../pixel/vx_table_lookup.md) · [vx_histogram](../pixel/vx_histogram.md) · [vx_nonmax_suppression](../suppress/vx_nonmax_suppression.md) · [vx_warp_affine](../geometry/vx_warp_affine.md) · [vx_warp_perspective](../geometry/vx_warp_perspective.md) · [vx_remap](../geometry/vx_remap.md)

## 同カテゴリ(`gradient`)

[vx_sobel3x3](vx_sobel3x3.md) · [vx_phase](vx_phase.md)

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
