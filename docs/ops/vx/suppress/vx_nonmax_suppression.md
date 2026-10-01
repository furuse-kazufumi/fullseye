---
op: vx_nonmax_suppression
dim: vx
category: suppress
in: image2d
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# vx_nonmax_suppression — VX `suppress` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_nonmax_suppression(image, *, window, mask=None)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_nonmax_suppression(image, *, window, mask=None)`、台帳から引くなら `opsvx.get("vx_nonmax_suppression")`)

## 使い方

非極大の抑制(3.39 節)。画素 (x, y) は、窓の中で**自分より前(上の行と、同じ行の左)の隣には ≥、後ろの隣には >** の
ときだけ残る(REQ-0337)。平らな頂上が 1 画素だけ残るのはこの非対称のため。*mask* の非ゼロ画素は比べず、そのまま残す
(他の画素の比較にも使わない、REQ-0336)。抑制した画素は U8 なら 0、S16 なら INT16_MIN(REQ-0335)。窓の外にはみ出す隣は比べない。

*window*(必須): 奇数の窓の一辺(3, 5, …)。

**Raises** ``ValueError``: U8/S16 の 2-D でない / window が 3 以上の奇数でない / mask の形が違う。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[vx_sobel3x3](../gradient/vx_sobel3x3.md) · [vx_magnitude](../gradient/vx_magnitude.md) · [vx_phase](../gradient/vx_phase.md) · [vx_table_lookup](../pixel/vx_table_lookup.md) · [vx_histogram](../pixel/vx_histogram.md)

## 同カテゴリ(`suppress`)

—

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
