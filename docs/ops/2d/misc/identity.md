---
op: identity
dim: 2d
category: misc
in: any
out: any
halcon: copy_image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# identity — 2D `misc` op

- **データ種**: `any` → `any`
- **呼び出し**: `fullseye.apply(img, "identity", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `copy_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

恒等写像。HALCON の ``copy_image``（Copy an image and allocate new memory for it.）に対応付けられているが、実装は新しいメモリを確保して複製する ``copy_image`` とは異なり、入力の配列をそのまま返すだけ（複製しない）。

``a``, ``b`` は未使用。sort が ``ANY``（image/region/feature いずれの入力にも一致）なのはこの op だけの特別扱いで、パイプラインの型を変えずに「何もしない」スロットを置くために使う（進化がスロット数を埋めたいだけのとき等）。値を作り直さず入力をそのまま返すため、呼び出し側で戻り値を書き換えると入力の配列も一緒に変わる点に注意。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md) · [percentile](../rank/percentile.md)

## 同カテゴリ(`misc`)

—

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
