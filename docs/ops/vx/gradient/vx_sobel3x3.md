---
op: vx_sobel3x3
dim: vx
category: gradient
in: image2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# vx_sobel3x3 — VX `gradient` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_sobel3x3(image, *, border, constant_value=0)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_sobel3x3(image, *, border, constant_value=0)`、台帳から引くなら `opsvx.get("vx_sobel3x3")`)

## 使い方

Sobel 3×3(3.46 節): G_x = [[−1,0,1],[−2,0,2],[−1,0,1]]、G_y = [[−1,−2,−1],[0,0,0],[1,2,1]] (REQ-0415)を相関として当てる。

*image*: U8。*border*(必須): ``"replicate"`` / ``"constant"``(*constant_value* で埋める)/ ``"undefined"``(端 1 画素は
規格上未定義 —— 0 を入れ、``valid`` の外として返す)。

返り値 ``{"gx": S16, "gy": S16, "valid": (y0, y1, x0, x1)}``(U8 の 3×3 Sobel は |値| ≤ 1020 なので S16 で飽和しない)。

**Raises** ``ValueError``: 2-D の U8 でない / border が一覧に無い / constant_value が 0〜255 の外。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`gradient`)

[vx_magnitude](vx_magnitude.md) · [vx_phase](vx_phase.md)

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
