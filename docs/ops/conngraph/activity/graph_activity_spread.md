---
op: graph_activity_spread
dim: conngraph
category: activity
in: matrix × points × labels
out: table
examples: [poc_malecns_activity_wave]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# graph_activity_spread — CONNGRAPH `activity` op

- **データ種**: `matrix × points × labels` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_activity_spread(X: 'Any', P: 'Any', source: 'Any', thresh: 'float' = 0.1) -> 'dict[str, np.ndarray]'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_activity_spread(X: 'Any', P: 'Any', source: 'Any', thresh: 'float' = 0.1) -> 'dict[str, np.ndarray]'`、台帳から引くなら `opsconngraph.get("graph_activity_spread")`)

## 使い方

活動がどこまで広がったかの時系列の表: 列 step / mean_distance / active_fraction / source_fraction。

``X`` = (T, n) の状態列、``P`` = (n, 3) の座標、``source`` = 刺激したノードの指示子(長さ n の
整数、非零 = 刺激。1 つ以上)。
mean_distance[t] = Σ|x_i(t)| ‖P_i − c‖ / Σ|x_i(t)|(c = 刺激ノードの重心、|x| で重みづけた
活動の平均距離、単位は P と同じ。活動が全零のステップは 0)。
active_fraction[t] = |x_i(t)| ≥ 全体最大 × thresh のノードの割合。
source_fraction[t] = 活動のうち刺激ノードにある分 Σ_source |x| / Σ|x|(全零なら 0)。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_malecns_activity_wave](../../../../examples/poc_malecns_activity_wave.py) — `py -3.11 examples/poc_malecns_activity_wave.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`activity`)

[graph_activation_latency](graph_activation_latency.md) · [points_activity_video](points_activity_video.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
