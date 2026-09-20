---
op: points_activity_video
dim: conngraph
category: activity
in: points × matrix
out: rgbvideo
examples: [poc_eye_to_brain, poc_malecns_activity_wave]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# points_activity_video — CONNGRAPH `activity` op

- **データ種**: `points × matrix` → `rgbvideo`
- **呼び出し**: `import fullseye as fs; fs.ledger.points_activity_video(P: 'Any', X: 'Any', colors: 'Any' = None, size: 'int' = 480, aspect: 'float' = 0.75, pitch: 'float' = 15.0, yaw_start: 'float' = 0.0, yaw_span: 'float' = 360.0, substeps: 'int' = 1, point_px: 'int' = 2, gain: 'float' = 100.0, background: 'Any' = None, views: 'Any' = None) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.points_activity_video(P: 'Any', X: 'Any', colors: 'Any' = None, size: 'int' = 480, aspect: 'float' = 0.75, pitch: 'float' = 15.0, yaw_start: 'float' = 0.0, yaw_span: 'float' = 360.0, substeps: 'int' = 1, point_px: 'int' = 2, gain: 'float' = 100.0, background: 'Any' = None, views: 'Any' = None) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("points_activity_video")`)

## 使い方

点群に活動を載せて回す色動画 (F, H, W, 3)、値 [0, 1]。F = T × substeps、H = size、W = size × aspect。

``views`` に (yaw, pitch) の並び(度)を渡すと**回さずに**、その方向から見たコマを横に並べる
(W = views 数 × size × aspect + 4 px の隙間、yaw_start / yaw_span は使わない)。同じ瞬間を
複数の方向から見比べる用(例: 背側 (0, 0) / 側面 (90, 0) / 体軸方向 (0, 90))。

``P`` = (n, 3) の座標、``X`` = (T, n) の状態列(reservoir_states)。コマ k は時刻 k / substeps の
状態(隣り合うステップの線形補間)を、yaw = yaw_start + yaw_span × k / F のカメラで正射影する。
明るさ b = log1p(gain · |x| / max|X|) / log1p(gain) —— **尺度は全コマで 1 つ**(コマごとに伸ばすと
動いていないものがちらつく)。ノードの色 = ``colors``((n, 3)、[0, 1]、None なら白)× (0.2 + 0.8 b)、
b > 0.5 のノードは一回り大きく明るく塗る。``background`` は (m, 3) の点群を薄い灰で先に敷く
(脳の全 soma の上に選んだノードを載せる、など)。画角は P と background を合わせた箱で決める。
出力は F×H×W×3 ≤ MAX_VIDEO_ELEMENTS(2^27)に制限する。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_eye_to_brain](../../../../examples/poc_eye_to_brain.py) — `py -3.11 examples/poc_eye_to_brain.py`
- [poc_malecns_activity_wave](../../../../examples/poc_malecns_activity_wave.py) — `py -3.11 examples/poc_malecns_activity_wave.py`

## 型が繋がる次の op(`rgbvideo` を入力に取れる)

—

## 同カテゴリ(`activity`)

[graph_activation_latency](graph_activation_latency.md) · [graph_activity_spread](graph_activity_spread.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
