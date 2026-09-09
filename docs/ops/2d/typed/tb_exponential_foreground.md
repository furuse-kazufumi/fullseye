---
op: tb_exponential_foreground
dim: 2d
category: typed
in: video
out: video
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# tb_exponential_foreground — 2D `typed` op

- **データ種**: `video` → `video`
- **呼び出し**: `fullseye.apply(img, "tb_exponential_foreground", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tb_exponential_foreground: input → output](../../_fig/tb_exponential_foreground.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tb_exponential_foreground: knob a sweep](../../_fig/tb_exponential_foreground.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tb_exponential_foreground: knob b sweep](../../_fig/tb_exponential_foreground.b.jpg)

**段階**(前置きの op → この op。左から順):

![tb_exponential_foreground: stages](../../_fig/tb_exponential_foreground.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tb_exponential_foreground: other inputs](../../_fig/tb_exponential_foreground.inputs.jpg)

**動き**(GIF: フレーム / 視点 / スライスを順に。静止の図が完成形で、GIF は補助):

![tb_exponential_foreground: animation](../../_fig/tb_exponential_foreground.gif)

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

2-D 進化レジストリへ橋渡しした videostream の op ``exponential_foreground``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。``a`` が ``alpha``(既定 0.05)、``b`` が ``threshold``(既定 0.1)を振る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_video 0.50 0.50
tb_exponential_foreground 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `exponential_foreground` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [video_streaming](../../../../examples/video_streaming.py) — `py -3.11 examples/video_streaming.py`

## 型が繋がる次の op(`video` を入力に取れる)

[identity](../misc/identity.md) · [tb_temporal_bandpass](tb_temporal_bandpass.md) · [tb_temporal_band_power](tb_temporal_band_power.md) · [tb_temporal_median_window](tb_temporal_median_window.md) · [tb_moving_average_window](tb_moving_average_window.md) · [tb_background_subtraction_window](tb_background_subtraction_window.md) · [tb_frame_difference_causal](tb_frame_difference_causal.md) · [tb_exponential_background](tb_exponential_background.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
