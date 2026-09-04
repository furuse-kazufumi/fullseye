---
op: running_mean_std
dim: videostream
category: recursive
in: video
out: table
examples: [video_streaming]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# running_mean_std — VIDEOSTREAM `recursive` op

- **データ種**: `video` → `table`
- **呼び出し**: `import videostream; videostream.running_mean_std(video) -> 'dict'` (または `opsvideostream.get("running_mean_std")`)

## 使い方

Welford per-pixel mean / population std over the clip → ``{"mean", "std", "n"}`` (``table``).

Equals ``video.mean(0)`` / ``video.std(0)`` but needs two images of state,
not the clip — the streaming form for a recording that never ends.

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

## 同カテゴリ(`recursive`)

[frame_difference_causal](frame_difference_causal.md) · [exponential_background](exponential_background.md) · [exponential_foreground](exponential_foreground.md)

---
*Provenance: videostream.py — VIDEOSTREAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
