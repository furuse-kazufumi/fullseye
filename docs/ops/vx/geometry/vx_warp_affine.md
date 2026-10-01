---
op: vx_warp_affine
dim: vx
category: geometry
in: image2d × matrix
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# vx_warp_affine — VX `geometry` op

- **データ種**: `image2d × matrix` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_warp_affine(image, matrix, *, interpolation, border, constant_value=0)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_warp_affine(image, matrix, *, interpolation, border, constant_value=0)`、台帳から引くなら `opsvx.get("vx_warp_affine")`)

## 使い方

アフィン変換(3.56 節)。**逆写像**: 出力の画素 (x, y) は入力の (x0, y0) から取る(REQ-0498):
``x0 = M[0,0]·x + M[0,1]·y + M[0,2]``、``y0 = M[1,0]·x + M[1,1]·y + M[1,2]``。

*matrix*: 数学の並びの 2×3(1 行目が x0 の係数 a, b, c)。★規格の C の宣言は ``mat[3][2] = { {a,d}, {b,e}, {c,f} }``
(転置した並び)—— C の配列をそのまま渡すと形が (3, 2) になるので止める。*interpolation*(必須): ``"nearest"`` / ``"bilinear"``。
*border*(必須): ``"constant"``(*constant_value* で埋める)/ ``"undefined"``(0 で埋める、値は規格上未定義)。

**Raises** ``ValueError``: U8 の 2-D でない / matrix が 2×3 の有限でない / interpolation・border が一覧に無い。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[vx_sobel3x3](../gradient/vx_sobel3x3.md) · [vx_magnitude](../gradient/vx_magnitude.md) · [vx_phase](../gradient/vx_phase.md) · [vx_table_lookup](../pixel/vx_table_lookup.md) · [vx_histogram](../pixel/vx_histogram.md) · [vx_nonmax_suppression](../suppress/vx_nonmax_suppression.md) · [vx_warp_perspective](vx_warp_perspective.md) · [vx_remap](vx_remap.md)

## 同カテゴリ(`geometry`)

[vx_warp_perspective](vx_warp_perspective.md) · [vx_remap](vx_remap.md)

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
