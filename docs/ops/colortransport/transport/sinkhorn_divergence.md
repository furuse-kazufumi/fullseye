---
op: sinkhorn_divergence
dim: colortransport
category: transport
in: signal × signal × matrix
out: scalar
examples: [color_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# sinkhorn_divergence — COLORTRANSPORT `transport` op

- **データ種**: `signal × signal × matrix` → `scalar`
- **呼び出し**: `import colortransport; colortransport.sinkhorn_divergence(a, b, cost, cost_aa=None, cost_bb=None, reg=0.05, **kw)` (または `opscolortransport.get("sinkhorn_divergence")`)

## 使い方

**偏りを打ち消した** Sinkhorn 距離(Genevay, Peyré & Cuturi, AISTATS 2018)。

``S(a,b) - (S(a,a) + S(b,b)) / 2``。:func:`sinkhorn_distance` は正則化のぶん
系統的に上振れし、**自分自身との「距離」が 0 にならない**(実測 reg=0.2 で
0.05 超)。同じ偏りを自分自身との距離から引くと相殺され、**自分自身との値が
0 に戻る** ―― TRIZ でいう釣り合い(反作用で打ち消す)そのもの。

``cost_aa`` / ``cost_bb`` は ``a`` 同士・``b`` 同士の費用行列。1 点集合を
自分自身と比べる意味なので、**省略すると ``cost`` が正方のときだけ**
それを流用する(非正方で省略したら例外 ―― 適当な行列で埋めると、
引き算する量が別物になり、打ち消したつもりで別の偏りが載る)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`transport`)

[wasserstein_1d](wasserstein_1d.md) · [transport_plan_1d](transport_plan_1d.md) · [sinkhorn](sinkhorn.md) · [sinkhorn_distance](sinkhorn_distance.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
