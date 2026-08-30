---
op: em_skeleton
dim: 2d
category: region
in: region
out: region
examples: [gallery2d_region]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# em_skeleton — 2D `region` op

- **データ種**: `region` → `region`
- **呼び出し**: `fullseye.apply(img, "em_skeleton", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Eckhardt–Maderlechner 型の不変細線化(HALCON `skeleton` と同系統)。

    出典: U. Eckhardt, G. Maderlechner, "Invariant Thinning",
    Int. J. Pattern Recognition and AI 7:1115-1144 (1993)。実装規則は
    M. Couprie "Note on fifteen 2D parallel thinning algorithms" の EM93
    定義に従う(論文準拠のクリーンルーム実装。HALCON 実装との画素単位の
    一致は未検証):

      interior = 4 近傍がすべて前景の画素
      simple   = (8,4) 単純点(前景 8 連結成分 1 個 ∧ 接する背景 4 連結成分 1 個)
      perfect  = ある 4 方向の隣が interior で、その反対方向が背景
      「simple かつ perfect な画素を全部同時に消す」を不動点まで反復

    注: ノートの転記どおり「強(4)連結成分のみで simple を数える」と、
    並列削除が斜め橋を同時に落とし位相が壊れることを反例で実測したため、
    simple は標準の (8,4) 単純点にしてある(count_obj 等の既定 8 連結と同じ
    (8,4) 規約)。この点は原論文との異同が残る可能性があり、正直に記す。

    完全並列・対称(90 度回転/鏡映と可換)・位相保存・冪等。Zhang–Suen 系の
    `sk_skeleton` より枝を多く残す(実測 1.4〜1.5 倍の画素数 = Couprie の
    比較表で EM が対称・枝多である性格と整合)。ヒゲは `pruning` で後処理する
    流儀も HALCON と同じ。つまみ a, b は未使用。

## 詳しい使い方ガイド

- [gallery2d_region ファミリ ガイド](../guides/gallery2d_region.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_region](../../../../examples/gallery2d_region.py) — `py -3.11 examples/gallery2d_region.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](reg_erode.md) · [reg_dilate](reg_dilate.md) · [reg_open](reg_open.md) · [reg_close](reg_close.md) · [fill_holes](fill_holes.md) · [select_largest](select_largest.md) · [remove_small](remove_small.md)

## 同カテゴリ(`region`)

[reg_erode](reg_erode.md) · [reg_dilate](reg_dilate.md) · [reg_open](reg_open.md) · [reg_close](reg_close.md) · [fill_holes](fill_holes.md) · [select_largest](select_largest.md) · [remove_small](remove_small.md) · [invert_region](invert_region.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
