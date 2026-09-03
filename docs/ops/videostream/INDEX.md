# VIDEOSTREAM operator help — 16 ops in 8 categories

自動生成(`tools/opdocs.py toc`)。フォルダ階層 `docs/ops/videostream/<category>/<op>.md` を走査。

## ファミリ使い方ガイド(用途→op の教材)

- [video_streaming](guides/video_streaming.md) — 動画ストリーミング(video streaming)— 1 フレームずつ流して処理する 使い方ガイド

## カテゴリ

### analysis (1)

[scene_cut_detection](analysis/scene_cut_detection.md)

### background (2)

[running_gaussian_background](background/running_gaussian_background.md) · [running_gaussian_foreground](background/running_gaussian_foreground.md)

### denoise (1)

[temporal_bilateral](denoise/temporal_bilateral.md)

### flow (1)

[optical_flow_magnitude_stream](flow/optical_flow_magnitude_stream.md)

### motion (3)

[motion_energy_image](motion/motion_energy_image.md) · [motion_history_image](motion/motion_history_image.md) · [three_frame_difference](motion/three_frame_difference.md)

### recursive (4)

[exponential_background](recursive/exponential_background.md) · [exponential_foreground](recursive/exponential_foreground.md) · [frame_difference_causal](recursive/frame_difference_causal.md) · [running_mean_std](recursive/running_mean_std.md)

### restore (1)

[deflicker](restore/deflicker.md)

### window (3)

[background_subtraction_window](window/background_subtraction_window.md) · [moving_average_window](window/moving_average_window.md) · [temporal_median_window](window/temporal_median_window.md)

---
© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
