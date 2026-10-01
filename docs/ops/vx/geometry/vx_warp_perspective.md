---
op: vx_warp_perspective
dim: vx
category: geometry
in: image2d × matrix
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# vx_warp_perspective — VX `geometry` op

- **データ種**: `image2d × matrix` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_warp_perspective(image, matrix, *, interpolation, border, constant_value=0)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_warp_perspective(image, matrix, *, interpolation, border, constant_value=0)`、台帳から引くなら `opsvx.get("vx_warp_perspective")`)

## 使い方

射影変換(3.57 節)。逆写像: ``x0 = M[0]·(x, y, 1)``、``y0 = M[1]·(x, y, 1)``、``z0 = M[2]·(x, y, 1)``、
出力 (x, y) = 入力 (x0/z0, y0/z0)(REQ-0508)。z0 = 0 の画素は外として埋める。

*matrix*: 数学の並びの 3×3(規格の C の宣言 ``mat[3][3]`` は転置した並び)。他の引数は :func:`vx_warp_affine` と同じ。

**Raises** ``ValueError``: U8 の 2-D でない / matrix が 3×3 の有限でない / interpolation・border が一覧に無い。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[vx_sobel3x3](../gradient/vx_sobel3x3.md) · [vx_magnitude](../gradient/vx_magnitude.md) · [vx_phase](../gradient/vx_phase.md) · [vx_table_lookup](../pixel/vx_table_lookup.md) · [vx_histogram](../pixel/vx_histogram.md) · [vx_nonmax_suppression](../suppress/vx_nonmax_suppression.md) · [vx_warp_affine](vx_warp_affine.md) · [vx_remap](vx_remap.md)

## 同カテゴリ(`geometry`)

[vx_warp_affine](vx_warp_affine.md) · [vx_remap](vx_remap.md)

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
