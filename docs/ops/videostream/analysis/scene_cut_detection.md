---
op: scene_cut_detection
dim: videostream
category: analysis
in: video
out: table
examples: [video_streaming]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# scene_cut_detection — VIDEOSTREAM `analysis` op

- **データ種**: `video` → `table`
- **呼び出し**: `import videostream; videostream.scene_cut_detection(video, bins: 'int' = 64, threshold: 'float' = 0.3) -> 'dict'` (または `opsvideostream.get("scene_cut_detection")`)

## 使い方

Shot-boundary chi-square histogram distance over a clip → ``{"distance", "cut", "n"}`` (``table``).

``distance[t]`` is the chi-square distance of frame ``t``'s histogram to
frame ``t−1``'s (``distance[0] = 0``); ``cut[t]`` is ``distance[t] > threshold``.
Streaming form: one histogram of state, no frames kept.

## 詳しい使い方ガイド

- [video_streaming ファミリ ガイド](../guides/video_streaming.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [mv_cables](../../optics/guides/mv_cables.md) — ケーブル（規格・速度・給電・ロボットケーブル）
- [mv_frame_grabbers](../../optics/guides/mv_frame_grabbers.md) — フレームグラバーボード（光学系ではないが、撮れるかを決める）
- [mv_standards](../../optics/guides/mv_standards.md) — カメラインターフェースの規格と団体

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [video_streaming](../../../../examples/video_streaming.py) — `py -3.11 examples/video_streaming.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`analysis`)

—

---
*Provenance: videostream.py — VIDEOSTREAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
