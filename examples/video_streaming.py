# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""video_streaming — 1 フレームずつ流して動画を処理する(videostream 族)。

    py -3.11 examples/video_streaming.py

【この例が解く問題】
固定カメラの前を小さな物体が横切る。録画は長く、全フレームをメモリに積めない
(1080p 1 秒 = float64 475 MB)。**リングバッファ(直近 N 枚)と状態つき op**で
1 フレームずつ処理し、(a) 背景から物体を切り出し、(b) その位置と速度を追い、
(c) 一括版(videops)と同じ答えになることを既知の真値で確かめる。

【流れ】
1. 合成クリップ: 既知の速度 (vx, vy) 画素/フレームで動く円盤 + ノイズ。
2. ``VideoPipeline([gaussian, BackgroundSubtractionWindow])`` を uint8 で流す
   (リングは uint8 のまま = float64 の 1/8)。マスクの重心から速度を推定し真値と照合。
3. 台帳 op(一括版)= ストリーム版 をフレーム単位で一致確認
   (``temporal_median_window`` / ``moving_average_window`` /
   ``background_subtraction_window`` / ``frame_difference_causal`` /
   ``exponential_background`` / ``exponential_foreground`` /
   ``running_mean_std`` / ``optical_flow_magnitude_stream``)。
4. 第 2 波 op を既知の真値で確認: ``motion_history_image``(値 1 の前線が円盤上、
   後ろに減衰する軌跡)/ ``motion_energy_image``(= MHI>0)/
   ``three_frame_difference``(二連続差分の AND = 二フレーム差分の部分集合 =
   ゴースト除去)/ ``running_gaussian_foreground``(画素ごとの k-σ で円盤を切り出し、
   静止背景は静か)/ ``temporal_bilateral``(静止シーンをノイズ除去、動きは残す)/
   ``deflicker``(輝度脈動を打ち消す)/ ``scene_cut_detection``(ヒストグラム距離で
   ハードカットを検出)。

EXTEND: ``fs.iter_frames("clip.mp4", dtype="uint8")`` を frames に差し替えれば
実動画で同じパイプラインが動く。段は文字列(台帳 op)/状態つき op/任意の callable
を混ぜてよい。
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import videostream as VS  # noqa: E402
import videops  # noqa: E402
import opsvideostream  # noqa: E402


def synth_clip(t=24, h=48, w=64, vx=1.5, vy=0.5, r=4.0, seed=0):
    """Moving disc on a textured static background, uint8 frames + true centres."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:h, :w]
    bg = 0.35 + 0.15 * np.sin(xx / 5.0) * np.cos(yy / 7.0)
    frames, centres = [], []
    for i in range(t):
        cx, cy = 10.0 + vx * i, 20.0 + vy * i
        f = bg + 0.02 * rng.standard_normal((h, w))
        f[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = 0.95
        frames.append(np.round(np.clip(f, 0, 1) * 255).astype(np.uint8))
        centres.append((cx, cy))
    return np.stack(frames), np.array(centres)


def main():
    u8, centres = synth_clip()
    t, h, w = u8.shape
    print("[1] clip: %d frames %dx%d uint8 (%.0f kB; float64 would be %.0f kB)"
          % (t, h, w, u8.nbytes / 1e3, u8.nbytes * 8 / 1e3))

    # 2. stream: per-frame facade op + stateful background subtraction ------------
    pipe = VS.VideoPipeline([("gaussian", 0.15, 0.5), VS.BackgroundSubtractionWindow(7, 0.25)])
    est = []
    for i, mask in enumerate(pipe.run(u8)):
        if mask.sum() > 0:
            yy, xx = np.nonzero(mask)
            est.append((i, xx.mean(), yy.mean()))
    st = pipe.stats()
    est = np.array(est)
    # velocity from the detected centroids (frames after the window has filled)
    sel = est[est[:, 0] >= 7]
    vx_hat = np.polyfit(sel[:, 0], sel[:, 1], 1)[0]
    vy_hat = np.polyfit(sel[:, 0], sel[:, 2], 1)[0]
    print("[2] stream pipeline %s: %.2f ms/frame, ring %d bytes (float64: gaussian runs first), %d frames with a detection"
          % (st["stages"], st["ms_per_frame"], st["ring_bytes"], len(est)))
    print("    velocity estimate (%.2f, %.2f) px/frame vs true (1.50, 0.50)" % (vx_hat, vy_hat))
    assert abs(vx_hat - 1.5) < 0.15 and abs(vy_hat - 0.5) < 0.15
    assert st["ring_bytes"] == 7 * h * w * 8      # the ring holds float64 here: gaussian runs first

    # 3. ledger ops (batch) == streaming classes, frame for frame ------------------
    f64 = u8.astype(np.float64) / 255.0
    pairs = [
        ("temporal_median_window", VS.TemporalMedianWindow(5), {"window": 5}),
        ("moving_average_window", VS.MovingAverageWindow(3), {"window": 3}),
        ("background_subtraction_window", VS.BackgroundSubtractionWindow(5, 0.2), {"window": 5, "threshold": 0.2}),
        ("frame_difference_causal", VS.FrameDifference(), {}),
        ("exponential_background", VS.ExponentialBackground(0.1), {"alpha": 0.1}),
        ("optical_flow_magnitude_stream", VS.OpticalFlowStream(), {}),
    ]
    for name, op, kw in pairs:
        batch = opsvideostream.call(name, u8, **kw)
        live = np.stack([op.push(fr) for fr in u8])
        err = np.abs(batch - live).max()
        print("    %-32s batch == live: max |diff| = %.1e" % (name, err))
        assert err == 0.0
    fg = VS.exponential_foreground(u8, 0.1, 0.3)
    stats = VS.running_mean_std(u8)
    assert np.allclose(stats["mean"], f64.mean(0)) and np.allclose(stats["std"], f64.std(0))
    print("    exponential_foreground: %d px flagged on the last frame; running_mean_std == numpy mean/std"
          % int(fg[-1].sum()))
    # uint8 ring vs float64 ring: identical answers, 8x less memory
    a = VS.temporal_median_window(u8, 5)
    b = VS.temporal_median_window(f64, 5)
    assert np.abs(a - b).max() < 1e-12                       # (m1+m2)/2/255 vs (m1/255+m2/255)/2: 1 ulp
    # whole-clip videops vs causal window: agree where they should (window == T on the last frame)
    assert np.allclose(VS.temporal_median_window(f64, t)[-1], videops.temporal_median(f64))
    assert np.allclose(VS.frame_difference_causal(f64)[1:], videops.frame_difference(f64))
    print("[3] uint8 ring == float64 ring (max diff < 1e-12); window==T reproduces videops on the last frame")

    # 4. wave 2: motion detection, adaptive background, temporal denoise, restore --
    # motion history: the value-1 pixels are *this frame's* motion (the disc edges),
    # so their centroid sits on the disc; older motion decays into a trail behind it
    mhi = VS.motion_history_image(f64, tau=8, threshold=0.25)
    assert mhi.min() >= 0.0 and mhi.max() <= 1.0
    front = np.isclose(mhi[12], 1.0)
    yy, xx = np.nonzero(front)
    assert front.any() and abs(xx.mean() - centres[12, 0]) < 8.0 and abs(yy.mean() - centres[12, 1]) < 8.0
    mei = VS.motion_energy_image(f64, tau=8, threshold=0.25)
    assert np.array_equal(mei, (mhi > 0).astype(np.float64))
    # three-frame difference is the AND of two consecutive frame differences, so it is
    # always a subset of the two-frame difference — that is exactly how it drops the
    # "ghost" a plain difference leaves behind a moving object.
    fd = VS.frame_difference_causal(f64) > 0.25
    tfd = VS.three_frame_difference(f64, threshold=0.25) > 0
    assert np.all(tfd[2:] <= fd[2:])
    print("[4] MHI value-1 front sits on the disc; MEI == (MHI>0); three_frame_diff subset of two-frame diff (ghost-free)")

    # adaptive single-Gaussian background: a bright disc on a noisy static scene is
    # foreground; the flat background is not (per-pixel k-sigma, not a fixed level)
    rgf = VS.running_gaussian_foreground(f64, alpha=0.02, k=3.0, var_init=1e-3)
    disc = (np.mgrid[:h, :w][1] - centres[-1, 0]) ** 2 + (np.mgrid[:h, :w][0] - centres[-1, 1]) ** 2 <= 16
    assert rgf[-1][disc].mean() > 0.5 and rgf[-1][~disc].mean() < 0.1
    rgb = VS.running_gaussian_background(f64, alpha=0.05)         # the learned mean image (the disc averaged out)
    assert rgb.shape == f64.shape and rgb[-1][~disc].std() < f64[:, ~disc].std()
    print("    running_gaussian_foreground: disc flagged, static background quiet; background() is the learned mean")

    # temporal bilateral denoise: recover a static noisy scene better than the raw
    truth = 0.35 + 0.15 * np.sin(np.mgrid[:h, :w][1] / 5.0) * np.cos(np.mgrid[:h, :w][0] / 7.0)
    static = np.clip(np.stack([truth + 0.06 * np.random.default_rng(k).standard_normal((h, w))
                               for k in range(9)]), 0, 1)
    den = VS.temporal_bilateral(static, window=5, sigma_t=3.0, sigma_r=0.2)
    assert np.abs(den[-1] - truth).mean() < np.abs(static[-1] - truth).mean()
    print("    temporal_bilateral denoises the static scene (closer to truth than the raw frame)")

    # deflicker: cancel a synthetic brightness pump; a hard cut is found by histogram
    flick = np.clip(f64 * (1.0 + 0.3 * (np.arange(t) % 2 - 0.5))[:, None, None], 0, 1)
    deflk = VS.deflicker(flick, alpha=0.1)
    assert deflk.mean((1, 2)).std() < flick.mean((1, 2)).std()
    cutclip = np.concatenate([f64[:t // 2], 1.0 - f64[t // 2:]])       # invert half -> a hard cut
    sc = VS.scene_cut_detection(cutclip, bins=32, threshold=0.3)
    assert sc["cut"][t // 2] and sc["distance"][t // 2] == sc["distance"].max()
    print("    deflicker cuts brightness pumping (%.3f -> %.3f std); scene_cut_detection found the cut at frame %d"
          % (flick.mean((1, 2)).std(), deflk.mean((1, 2)).std(), t // 2))
    print("ALL GT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
