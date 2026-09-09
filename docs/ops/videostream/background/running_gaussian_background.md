---
op: running_gaussian_background
dim: videostream
category: background
in: video
out: video
examples: [video_streaming]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# running_gaussian_background — VIDEOSTREAM `background` op

- **データ種**: `video` → `video`
- **呼び出し**: `import fullseye as fs; fs.ledger.running_gaussian_background(video, alpha: 'float' = 0.02, k: 'float' = 2.5, var_init: 'float' = 0.01, selective: 'bool' = True) -> 'np.ndarray'` (実装を直接呼ぶなら `import videostream; videostream.running_gaussian_background(video, alpha: 'float' = 0.02, k: 'float' = 2.5, var_init: 'float' = 0.01, selective: 'bool' = True) -> 'np.ndarray'`、台帳から引くなら `opsvideostream.get("running_gaussian_background")`)

## 使い方

Adaptive single-Gaussian background (the running mean) per frame → ``(T, H, W)`` (``video``).

画素ごとに平均 ``mean`` と分散 ``var`` を持つ単一ガウス背景(Wren の Pfinder)を
回し、各フレーム後の ``mean`` を返す。前景判定は
``(frame - mean)^2 > k^2 var``。``selective=True``(既定)では前景と判定した画素の
``mean`` / ``var`` を**更新しない**ので、ゆっくり動く物体が背景に溶けない。
更新式は ``mean += α diff``、``var += α (diff^2 - var)``、``var`` の下限は 1e-4。

- ``video``: ``(T, H, W)`` 配列か 2-D フレームの list。整数は最大値で ``[0, 1]``
  に正規化、float はクリップ。NaN/Inf は ``ValueError``。
- ``alpha``: ``[0, 1]`` の学習率。既定 0.02(時定数およそ 50 枚)。
- ``k``: ``[0, 100]``。前景とみなす標準偏差の倍数。既定 2.5。
- ``var_init``: ``[1e-9, 1]``。先頭フレームでの分散の初期値(``[0, 1]`` 強度の 2 乗)。
  小さすぎると 2 枚目から全画素が前景になり、``selective`` で更新が止まる。
- ``selective``: 前景画素の更新を止めるか。``False`` なら全画素を常に更新。
- 返り値: ``(T, H, W)`` float64。``t = 0`` は先頭フレームそのもの。
- 失敗: ``ValueError``(形・dtype・各範囲)。

同じモデルの前景マスクは ``running_gaussian_foreground``(同じ引数で対にすると
フレームごとに整合する)。

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

[running_gaussian_foreground](running_gaussian_foreground.md)

---
*Provenance: videostream.py — VIDEOSTREAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
