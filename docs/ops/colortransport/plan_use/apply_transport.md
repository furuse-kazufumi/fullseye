---
op: apply_transport
dim: colortransport
category: plan_use
in: transport_plan × signal
out: signal
examples: [color_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# apply_transport — COLORTRANSPORT `plan_use` op

- **データ種**: `transport_plan × signal` → `signal`
- **呼び出し**: `import colortransport; colortransport.apply_transport(plan, target_values)` (または `opscolortransport.get("apply_transport")`)

## 使い方

輸送計画で ``target_values`` を元の点へ引き戻す(重心写像)。

各行(送り元)について、運んだ質量で重み付けした行き先の値の平均を返す。
これが「計画を**使って絵を直す**」入口 ―― 計画を作るだけで使い道が無いと、
:func:`sinkhorn` の出力は台帳の袋小路になる(この repo が繰り返し踏んできた
「入口はあるが消費 op が無い型」の形)。

質量ゼロの行は行き先が無い ―― 0 で埋めると「黒い画素」が黙って混ざるので
``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[wasserstein_1d](../transport/wasserstein_1d.md) · [transport_plan_1d](../transport/transport_plan_1d.md) · [sinkhorn](../transport/sinkhorn.md) · [sinkhorn_distance](../transport/sinkhorn_distance.md) · [sinkhorn_divergence](../transport/sinkhorn_divergence.md)

## 同カテゴリ(`plan_use`)

[transport_cost](transport_cost.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
