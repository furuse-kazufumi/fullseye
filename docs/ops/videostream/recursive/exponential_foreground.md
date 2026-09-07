---
op: exponential_foreground
dim: videostream
category: recursive
in: video
out: video
examples: [video_streaming]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# exponential_foreground — VIDEOSTREAM `recursive` op

- **データ種**: `video` → `video`
- **呼び出し**: `import fullseye as fs; fs.ledger.exponential_foreground(video, alpha: 'float' = 0.05, threshold: 'float' = 0.1) -> 'np.ndarray'` (実装を直接呼ぶなら `import videostream; videostream.exponential_foreground(video, alpha: 'float' = 0.05, threshold: 'float' = 0.1) -> 'np.ndarray'`、台帳から引くなら `opsvideostream.get("exponential_foreground")`)

## 使い方

Foreground masks ``|frame − exponential background| > threshold`` → 0/1 ``(T, H, W)`` (``video``).

``exponential_background`` と同じ指数移動平均 ``bg += α (frame - bg)`` を回し、
各フレームで **更新後の** ``bg`` との差 ``|frame - bg| > threshold`` を 1 にする。
先頭フレームは ``bg`` の初期化に使われ差が 0 なので、``t = 0`` は全画素 0。

- ``video``: ``(T, H, W)`` 配列か 2-D フレームの list。整数 dtype は最大値で
  ``[0, 1]`` に正規化、float はクリップ。NaN/Inf は ``ValueError``。
- ``alpha``: ``[0, 1]``。大きいほど背景が速く追従し、止まった物体は
  約 ``1/α`` 枚で消える。1 だと ``bg == frame`` になり常に全画素 0。
- ``threshold``: ``[0, 1]`` の強度単位。**全画素共通の絶対閾**なので、暗部の
  雑音と明部の雑音を同じ閾で切ることになる。
- 返り値: ``(T, H, W)`` float64 の 0 / 1。
- 失敗: ``ValueError``。

画素ごとの分散で閾を決めたいなら ``running_gaussian_foreground``。ゴーストの
無い動き検出なら ``three_frame_difference``。

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

[temporal_median_window](../window/temporal_median_window.md) · [moving_average_window](../window/moving_average_window.md) · [background_subtraction_window](../window/background_subtraction_window.md) · [frame_difference_causal](frame_difference_causal.md) · [exponential_background](exponential_background.md) · [running_mean_std](running_mean_std.md) · [optical_flow_magnitude_stream](../flow/optical_flow_magnitude_stream.md) · [motion_history_image](../motion/motion_history_image.md)

## 同カテゴリ(`recursive`)

[frame_difference_causal](frame_difference_causal.md) · [exponential_background](exponential_background.md) · [running_mean_std](running_mean_std.md)

---
*Provenance: videostream.py — VIDEOSTREAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
