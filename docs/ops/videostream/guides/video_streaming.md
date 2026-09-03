---
guide: video_streaming
dim: videostream
title: 動画ストリーミング(video streaming)— 1 フレームずつ流して処理する 使い方ガイド
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
---

# 動画ストリーミング(video streaming)— 1 フレームずつ流して処理する 使い方ガイド

## この族は何をする道具箱か

`videops` 族は動画を `(T, H, W)` の float64 配列として**一括**で受け取ります。1080p の 1 秒は 475 MB、状態を持つ op は表せません。カメラ・ロボットの眼・長時間録画は「全フレーム」を一度に渡してこないので、`videostream` 族(台帳 `opsvideostream.py`、16 op / 8 カテゴリ、モジュール `videostream.py`)は **1 フレームずつ**処理する形を op として持ちます。

- **リングバッファ `FrameRing(n)`** — 直近 n 枚だけを、**フレームの dtype のまま**保持(uint8 の 1080p を 5 枚で 10 MB。float64 一括の 1 秒は 475 MB)。形や dtype の違うフレームは**拒否**します(落ちたフレームが黙って窓を汚さない)。
- **状態つき op(`StatefulOp`、`push(frame) → 出力` / `reset()` / `state`)** — 第 1 波: `TemporalMedianWindow` / `MovingAverageWindow` / `BackgroundSubtractionWindow`(窓つき、因果)、`FrameDifference` / `ExponentialBackground` / `RunningStats`(状態 1〜2 枚の再帰形)、`OpticalFlowStream`(前フレーム保持の密な流れ)。第 2 波: `MotionHistoryImage`(動き履歴画像)/ `ThreeFrameDifference`(三フレーム差分)/ `RunningGaussianForeground`(画素ごと単一ガウス背景)/ `TemporalBilateral`(時間方向バイラテラル)/ `Deflicker`(輝度デフリッカ)/ `SceneCutDetection`(ショット境界)。
- **`VideoPipeline(stages)`** — 台帳 op の文字列(`"gaussian"` / `("gaussian", a, b)`、`api.apply` を通るので GPU 経路と fallback 台帳はそのまま)、状態つき op、任意の callable を混ぜて連ねる。`push(frame)` / `run(frames)` / `stats()`(1 フレームあたり ms、段ごとの時間、リングのバイト数)。
- **台帳 op(一括版)** — 第 1 波: `temporal_median_window` / `moving_average_window` / `background_subtraction_window` / `frame_difference_causal` / `exponential_background` / `exponential_foreground` / `running_mean_std` / `optical_flow_magnitude_stream`。第 2 波: `motion_history_image` / `motion_energy_image` / `three_frame_difference` / `running_gaussian_foreground` / `running_gaussian_background` / `temporal_bilateral` / `deflicker` / `scene_cut_detection`。実体は**ストリーミングクラスをクリップに沿って再生したもの**(`stream_replay`)なので、生の配信で 1 フレームずつ得た結果と台帳 op の結果は**フレーム単位で一致**します(`tests/test_videostream.py` と `examples/video_streaming.py` が固定)。

## 第 2 波の op(動き検出・適応背景・時間ノイズ除去・復元・ショット検出)

| op | 何をするか | 出典 |
|---|---|---|
| `motion_history_image` / `motion_energy_image` | 動き履歴画像(いま動いた所を 1、後ろへ `1/tau` ずつ減衰)/ その二値版(直近 tau で動いた所) | Bobick & Davis 2001 |
| `three_frame_difference` | 連続する二つのフレーム差分の AND。移動体の後ろに残る「ゴースト」を消す | Collins et al., VSAM 2000 |
| `running_gaussian_foreground` / `running_gaussian_background` | 画素ごとに平均・分散を持ち、平均から `k` 標準偏差を超えたら前景。閾値が画素ごとに雑音へ追従(固定閾値の `exponential_background` の上位) | Wren *Pfinder* 1997 |
| `temporal_bilateral` | 時間方向のバイラテラル。動いた画素は過去フレームの重みが落ちるので、平均化のようにゴーストを引かずに静止部だけ雑音除去 | — |
| `deflicker` | 各フレームの平均を緩やかな基準へ合わせて輝度の脈動を打ち消す(自動露出・商用電源のちらつき) | 動画復元 |
| `scene_cut_detection` | フレーム間ヒストグラムのカイ二乗距離。ハードカットで跳ねる。動き(画素は動くがヒストグラムは保つ)に強い | ショット境界検出 |

スループット(`--set video`、per-frame・ring メモリのみ、720p float64、非熱定常なので相対で読む): `deflicker` / `exponential_background` / `frame_difference_causal` は 100 fps 超、`motion_history_image` / `three_frame_difference` / `moving_average_window` は 30 fps 余裕、`running_gaussian_foreground` ~46 fps、per-画素中央値/窓を持つ `temporal_median_window` / `background_subtraction_window` / `temporal_bilateral` は 720p で 10〜15 fps(中央値・窓が重い、`docs/design/PERF_MEMORY_VIDEO_SURVEY.md` の median 所見どおり)。計測は `py -3.11 tools/bench_ops.py --set video --sizes 720p`。
- **読み込みの素通し** — `video.iter_frames(path, dtype="uint8")` はデコードした整数フレームを float64 に変換せず渡します(1080p の読み込みが 18 fps → 約 180 fps、`docs/design/PERF_MEMORY_VIDEO_SURVEY.md` §3.2)。灰色化は `gray_backend="auto"|"cv2"|"numpy"`(どちらも Rec. 601、丸めで 1 LSB 差)。

## videops との違いは名前に出す

同じ名前で違う数を出す op は作りません。窓つき・因果の版は必ず別名です。

| videops(一括・全 T) | videostream(因果・直近 N) | 一致する条件 |
|---|---|---|
| `temporal_median`(全 T の中央値) | `temporal_median_window(video, window)` | `window == T` の最終フレーム |
| `moving_average`(中心窓・端複製) | `moving_average_window` | 内部フレームで 1 フレームずれて一致 |
| `background_subtraction` | `background_subtraction_window` | `window == T` の最終フレーム |
| `frame_difference`(T−1 枚) | `frame_difference_causal`(T 枚、先頭ゼロ) | 2 枚目以降 |
| `optical_flow_sequence`(T−1 枚) | `optical_flow_magnitude_stream`(T 枚) | 2 枚目以降 |

## ファミリ共通の契約(fail-closed)

- フレームは `(H, W)`(リングのみ `(H, W, C)` も可)。**最初のフレームが形と dtype を決め**、以後違うものは `ValueError`(`reset()` で新しいストリームを始める)。float の非有限は拒否。
- 受け付ける dtype は float64 `[0,1]`(ライブラリ契約)と `uint8` / `uint16` / `bool`。整数はリングに整数のまま置き、計算のときに `/255`・`/65535` で正直に換算。**出力は常に float64 契約**。uint8 の中央値は整数のまま取ってから割るので、float64 で計算した値と 1 ulp 以内で一致。
- 窓 op は**因果**(フレーム t は t−N+1 .. t だけを使う)。窓が埋まるまでは見えた分だけで計算(最初は 1 枚の窓)。
- 状態つき段が例外を出したら **状態をリセットして台帳に `source="stream"` で記録**(汚れた窓のまま続けない)。`on_error="raise"` なら再送出。既定(fail-soft)では、その段の出力は `None`。
- `window` は 1〜4096 の int(bool は拒否)、`alpha` / `threshold` は [0,1]。

## 代表的なパイプライン(op の繋がり)

```mermaid
flowchart LR
    S[iter_frames dtype=uint8<br/>or camera] --> P[VideoPipeline]
    P --> G["gaussian (台帳 op, api.apply)"]
    G --> B[BackgroundSubtractionWindow<br/>ring N=5]
    B --> M[mask → 重心・速度]
    S --> R[RunningStats<br/>状態 2 枚]
    R --> N[mean / std 画像]
    C[(T,H,W) clip] --> L[台帳 op temporal_median_window …<br/>= stream_replay]
    L --> E[フレーム単位で<br/>live と一致]
```

## 使い方

### 生の配信を流す

```python
import numpy as np
import videostream as VS

rng = np.random.default_rng(0)
frames = [np.round(rng.random((48, 64)) * 255).astype(np.uint8) for _ in range(20)]

pipe = VS.VideoPipeline([("gaussian", 0.15, 0.5), VS.BackgroundSubtractionWindow(5, 0.25)])
for mask in pipe.run(frames):            # 1 フレームずつ、mask は (H, W) の 0/1 float64
    pass
st = pipe.stats()
print(st["ms_per_frame"], st["ring_bytes"], st["stages"])
```

### 状態つき op を直接使う

```python
import numpy as np
import videostream as VS

op = VS.TemporalMedianWindow(5)          # 直近 5 枚の中央値、リングは入力 dtype のまま
u8 = np.zeros((48, 64), np.uint8)
med = op.push(u8)                        # (48, 64) float64
print(op.state["stored"], op.state["ring_bytes"])   # 1, 5*48*64 bytes
op.reset()                               # 新しいストリーム(形が変わってもよい)
```

### 台帳 op(一括)= ストリーム版

```python
import numpy as np
import opsvideostream, videostream as VS

clip = np.random.default_rng(1).random((12, 32, 32))
batch = opsvideostream.call("temporal_median_window", clip, window=5)
op = VS.TemporalMedianWindow(5)
live = np.stack([op.push(f) for f in clip])
assert np.abs(batch - live).max() == 0.0
```

## 数式

- 窓中央値: `y_t = median(x_{t−N+1}, …, x_t)`(t < N−1 では見えた分)。
- 指数背景: `bg_t = (1−α)·bg_{t−1} + α·x_t`、`bg_0 = x_0`。前景 `|x_t − bg_t| > θ`。
- Welford: `μ_n = μ_{n−1} + (x_n − μ_{n−1})/n`、`M2_n = M2_{n−1} + (x_n − μ_{n−1})(x_n − μ_n)`、母分散 `M2_n / n`(`video.std(0)` と一致)。

## 実装の根拠と限界(正直に)

- 動機と数字は `docs/design/PERF_MEMORY_VIDEO_SURVEY.md` §3(2026-09-03 実測。熱定常でない単日測定なので絶対値は 1.5〜2 倍の幅)。
- 窓中央値は毎フレーム `np.median` を窓全体に掛ける(O(N·HW))。N が大きいときの増分中央値(ヒストグラム法)は未実装。
- フレーム並列・GPU 常駐リング・タイル分割は同報告 §4 の (f)(g)(c) として後続。`VideoPipeline` の `device="cuda"` は各台帳 op に渡るが、リングは CPU に置かれる。
- `OpticalFlowStream` は `flow.optical_flow_lk` をそのまま呼ぶ(前フレーム 1 枚の状態)。
