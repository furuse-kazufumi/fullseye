---
op: running_gaussian_foreground
dim: videostream
category: background
in: video
out: video
examples: [video_streaming]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# running_gaussian_foreground — VIDEOSTREAM `background` op

- **データ種**: `video` → `video`
- **呼び出し**: `import videostream; videostream.running_gaussian_foreground(video, alpha: 'float' = 0.02, k: 'float' = 2.5, var_init: 'float' = 0.01, selective: 'bool' = True) -> 'np.ndarray'` (または `opsvideostream.get("running_gaussian_foreground")`)

## 使い方

Adaptive single-Gaussian foreground masks per frame → 0/1 ``(T, H, W)`` (``video``).

Per-pixel mean/variance background (Wren *Pfinder*); foreground is
``> k`` standard deviations from the mean. The first frame is all background.

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

[temporal_median_window](../window/temporal_median_window.md) · [moving_average_window](../window/moving_average_window.md) · [background_subtraction_window](../window/background_subtraction_window.md) · [frame_difference_causal](../recursive/frame_difference_causal.md) · [exponential_background](../recursive/exponential_background.md) · [exponential_foreground](../recursive/exponential_foreground.md) · [running_mean_std](../recursive/running_mean_std.md) · [optical_flow_magnitude_stream](../flow/optical_flow_magnitude_stream.md)

## 同カテゴリ(`background`)

[running_gaussian_background](running_gaussian_background.md)

---
*Provenance: videostream.py — VIDEOSTREAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
