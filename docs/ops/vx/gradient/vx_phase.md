---
op: vx_phase
dim: vx
category: gradient
in: image2d × image2d
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# vx_phase — VX `gradient` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_phase(gx, gy, *, mapping)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_phase(gx, gy, *, mapping)`、台帳から引くなら `opsvx.get("vx_phase")`)

## 使い方

勾配の位相(3.41 節): ϕ = atan2(gy, gx) を 0 ≤ ϕ < 2π に移し、0〜255 に写す(REQ-0364)。出力 U8。

*mapping*(必須): 規格は写し方の丸めを書いていない。``"floor"`` = ⌊ϕ·256/(2π)⌋(0 ≤ 値 ≤ 255 が自動で成り立つ)、
``"round"`` = ⌊ϕ·256/(2π) + 0.5⌋ mod 256(2π の手前は 0 に巻く)。gx = gy = 0 の画素は atan2 の約束で ϕ = 0。

**Raises** ``ValueError``: S16 の 2-D でない / 形が違う / mapping が一覧に無い。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[vx_sobel3x3](vx_sobel3x3.md) · [vx_magnitude](vx_magnitude.md) · [vx_table_lookup](../pixel/vx_table_lookup.md) · [vx_histogram](../pixel/vx_histogram.md) · [vx_nonmax_suppression](../suppress/vx_nonmax_suppression.md)

## 同カテゴリ(`gradient`)

[vx_sobel3x3](vx_sobel3x3.md) · [vx_magnitude](vx_magnitude.md)

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
