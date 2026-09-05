---
op: optical_flow_magnitude_stream
dim: videostream
category: flow
in: video
out: video
examples: [video_streaming]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# optical_flow_magnitude_stream — VIDEOSTREAM `flow` op

- **データ種**: `video` → `video`
- **呼び出し**: `import videostream; videostream.optical_flow_magnitude_stream(video, **flow_kwargs) -> 'np.ndarray'` (または `opsvideostream.get("optical_flow_magnitude_stream")`)

## 使い方

Per-frame dense flow speed against the previous frame → ``(T, H, W)`` (``video``).

Zero first frame; frames ``1..T−1`` equal :func:`videops.optical_flow_sequence`
shifted by one, computed with one frame of state.

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

## 型が繋がる次の op(`video` を入力に取れる)

[temporal_median_window](../window/temporal_median_window.md) · [moving_average_window](../window/moving_average_window.md) · [background_subtraction_window](../window/background_subtraction_window.md) · [frame_difference_causal](../recursive/frame_difference_causal.md) · [exponential_background](../recursive/exponential_background.md) · [exponential_foreground](../recursive/exponential_foreground.md) · [running_mean_std](../recursive/running_mean_std.md) · [motion_history_image](../motion/motion_history_image.md)

## 同カテゴリ(`flow`)

—

---
*Provenance: videostream.py — VIDEOSTREAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
