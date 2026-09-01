---
op: nice_ticks
dim: annotate
category: plot
in: 
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# nice_ticks — ANNOTATE `plot` op

- **データ種**: `` → `signal`
- **呼び出し**: `import annotate; annotate.nice_ticks(lo, hi, n=5, scale='linear')` (または `opsannotate.get("nice_ticks")`)

## 使い方

[lo, hi] を覆う「切りのよい」目盛り値(1/2/5 × 10^k、**閉形式**)。

端は**含める**(``lo`` や ``hi`` がちょうど目盛りに乗るなら必ず出る)。
浮動小数の丸めで端が 1 個落ちる off-by-one を避けるため、判定には
``step*1e-9`` の許容を使う。

``scale='log'`` では 1/2/5 × 10^k の**十進の刻み**を返す(等間隔の刻みを
log 軸に置くと、目盛りが右へ行くほど潰れて読めなくなる)。

Raises
------
ValueError
    lo == hi、非有限、n < 1、log で lo か hi が 0 以下。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[data_to_pixel](data_to_pixel.md) · [plot_series](plot_series.md)

## 同カテゴリ(`plot`)

[axes_transform](axes_transform.md) · [data_to_pixel](data_to_pixel.md) · [axes_frame](axes_frame.md) · [grid_lines](grid_lines.md) · [ticks](ticks.md) · [plot_series](plot_series.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
