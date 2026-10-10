---
op: vx_nonlinear_filter
dim: vx
category: filter
in: image2d × matrix
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# vx_nonlinear_filter — VX `filter` op

- **データ種**: `image2d × matrix` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.vx_nonlinear_filter(image, mask, *, function, border, constant_value=0, origin=None)` (実装を直接呼ぶなら `import vxcore; vxcore.vx_nonlinear_filter(image, mask, *, function, border, constant_value=0, origin=None)`、台帳から引くなら `opsvx.get("vx_nonlinear_filter")`)

## 使い方

非線形フィルタ(3.38 節): マスクの真の画素の値の中央値 / 最小(収縮)/ 最大(膨張)(REQ-0325・0330)。

*function*: ``"median"`` / ``"min"`` / ``"max"``(vx_non_linear_filter_e)。*mask*: 2-D の bool(BOX / CROSS / DISK / OTHER の
どれでも)。*origin*: マスクの原点 (行, 列)(VX_MATRIX_ORIGIN、既定は中央 ``(rows // 2, cols // 2)``)。
*border*(必須): ``"replicate"`` / ``"constant"`` / ``"undefined"``(端は 0 で埋めて計算する —— 値は規格上未定義)。
★マスクの画素数が偶数のときの中央値は規格に無い —— 昇順に並べた ``n // 2`` 番目(上側の中央値、scipy の median_filter と同じ)を取る。
REQ-0327: 9×9 までのマスクは必ず扱う(この実装に上限は無い)。

**Raises** ``ValueError``: U8 の 2-D でない / function が一覧に無い / mask が 2-D の bool でない・空 / origin がマスクの外。

## 詳しい使い方ガイド

- [openvx_ports ファミリ ガイド](../guides/openvx_ports.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[vx_sobel3x3](../gradient/vx_sobel3x3.md) · [vx_magnitude](../gradient/vx_magnitude.md) · [vx_phase](../gradient/vx_phase.md) · [vx_table_lookup](../pixel/vx_table_lookup.md) · [vx_histogram](../pixel/vx_histogram.md) · [vx_nonmax_suppression](../suppress/vx_nonmax_suppression.md) · [vx_warp_affine](../geometry/vx_warp_affine.md) · [vx_warp_perspective](../geometry/vx_warp_perspective.md)

## 同カテゴリ(`filter`)

—

---
*Provenance: vxcore.py — VX operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
