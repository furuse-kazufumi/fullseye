---
op: temporal_median_window
dim: videostream
category: window
in: video
out: video
examples: [video_streaming]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# temporal_median_window — VIDEOSTREAM `window` op

- **データ種**: `video` → `video`
- **呼び出し**: `import videostream; videostream.temporal_median_window(video, window: 'int' = 5) -> 'np.ndarray'` (または `opsvideostream.get("temporal_median_window")`)

## 使い方

Causal per-pixel median over the last *window* frames → ``(T, H, W)`` (``video``).

Frame ``t`` uses frames ``max(0, t−window+1) .. t``. The streaming
:class:`TemporalMedianWindow` gives the same frames one at a time with a
ring of *window* frames instead of the whole clip in memory.

## 詳しい使い方ガイド

- [video_streaming ファミリ ガイド](../guides/video_streaming.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [video_streaming](../../../../examples/video_streaming.py) — `py -3.11 examples/video_streaming.py`

## 型が繋がる次の op(`video` を入力に取れる)

[moving_average_window](moving_average_window.md) · [background_subtraction_window](background_subtraction_window.md) · [frame_difference_causal](../recursive/frame_difference_causal.md) · [exponential_background](../recursive/exponential_background.md) · [exponential_foreground](../recursive/exponential_foreground.md) · [running_mean_std](../recursive/running_mean_std.md) · [optical_flow_magnitude_stream](../flow/optical_flow_magnitude_stream.md) · [motion_history_image](../motion/motion_history_image.md)

## 同カテゴリ(`window`)

[moving_average_window](moving_average_window.md) · [background_subtraction_window](background_subtraction_window.md)

---
*Provenance: videostream.py — VIDEOSTREAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
