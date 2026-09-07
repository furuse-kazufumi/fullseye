---
op: background_subtraction_window
dim: videostream
category: window
in: video
out: video
examples: [video_streaming]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# background_subtraction_window — VIDEOSTREAM `window` op

- **データ種**: `video` → `video`
- **呼び出し**: `import fullseye as fs; fs.ledger.background_subtraction_window(video, window: 'int' = 5, threshold: 'float' = 0.1) -> 'np.ndarray'` (実装を直接呼ぶなら `import videostream; videostream.background_subtraction_window(video, window: 'int' = 5, threshold: 'float' = 0.1) -> 'np.ndarray'`、台帳から引くなら `opsvideostream.get("background_subtraction_window")`)

## 使い方

Causal window-median background → per-frame 0/1 foreground masks ``(T, H, W)`` (``video``).

フレーム ``t`` ごとに、直近 ``window`` 枚(``max(0, t-window+1) .. t``、**そのフレーム
自身を含む**)の画素ごとの中央値を背景 ``bg`` とし、``|frame_t - bg| > threshold``
を 1、それ以外を 0 にする。未来のフレームは見ない(因果的)ので、先頭では
枚数が足りないぶん窓が短い。

- ``video``: ``(T, H, W)`` の配列、または同形・同 dtype の 2-D フレームの list。
  uint8/uint16 は dtype の最大値で ``[0, 1]`` に、float はそのまま ``[0, 1]`` に
  クリップ。カラー ``(T, H, W, C)`` は受けない。NaN/Inf は ``ValueError``。
- ``window``: 1〜4096 の int(bool 不可)。1 だと背景 = 自分なので全画素 0。
  偶数枚のときの中央値は中間 2 値の平均。
- ``threshold``: ``[0, 1]`` の強度単位(uint8 なら ``/255`` 換算)。
- 返り値: ``(T, H, W)`` float64 の 0 / 1。
- 失敗: ``ValueError``(形・dtype・範囲・非有限)。

ゆっくり動く物体は ``window`` 枚以内に背景へ溶けるので、その場合は
``running_gaussian_foreground``(選択的更新)か ``exponential_foreground`` を。
背景そのものが要るなら ``temporal_median_window``。

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

[temporal_median_window](temporal_median_window.md) · [moving_average_window](moving_average_window.md) · [frame_difference_causal](../recursive/frame_difference_causal.md) · [exponential_background](../recursive/exponential_background.md) · [exponential_foreground](../recursive/exponential_foreground.md) · [running_mean_std](../recursive/running_mean_std.md) · [optical_flow_magnitude_stream](../flow/optical_flow_magnitude_stream.md) · [motion_history_image](../motion/motion_history_image.md)

## 同カテゴリ(`window`)

[temporal_median_window](temporal_median_window.md) · [moving_average_window](moving_average_window.md)

---
*Provenance: videostream.py — VIDEOSTREAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
