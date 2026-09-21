# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 生きている組織の 3D+t を古典手法だけで「短い 3D 動画像」にする ―― 増幅・流れ・補間・高さ場、全部に真値

動画生成 AI は「もっともらしい動き」を発明する。この PoC は内容を発明しない代わりに、族 ``live4d``
(14 op、numpy + scipy のみ)で **実在する動きを見える形にする** 4 つの道を、真値つきの合成系列で数字に固定する。

**主張は 4 つ、どれも真値と比べる**:

1. **増幅**: 半径が 0.1 voxel(目に見えない)だけ拍動する殻を ``volseq_magnify_motion``(Eulerian の線形拡大)で
   8 倍にすると、読み取った半径の振幅は 8 倍 ± 25 % になり、周期は変わらない。
2. **流れ**: 既知の速さで分かれる 2 つの塊の変位場(``vol_flow_3d``、3 次元 Lucas–Kanade)は、勾配のある場所で
   真値の速さと 10 % 以内で合う。軌跡(``volseq_pathline_render``)は時刻の色で 1 枚の立体になる。
3. **補間**: 2 倍のフレームレートで作った系列を半分に間引き、``volseq_interpolate_flow`` で埋めた中間フレームは、
   抜いた真のフレームに対して単純な線形ブレンドより誤差が小さい(並進する塊で 40 % 未満)。
4. **高さ場**: 焦点掃引の時系列(動く山)から ``focus_sweep_height_video`` が起こした高さは真値と半枚以内。

図:
1. ``beating_orbit``(GIF): 拍動する殻を時間を進めながら回す。左 = 元(拍動が見えない)、右 = 8 倍に増幅。
2. ``radius_trace``: 半径の時間変化 —— 元 / 増幅後 / 真値 × 8。
3. ``pathlines``: 分かれる塊の軌跡の立体(時刻の色: 青 = 始め → 赤 = 終わり)と、回す GIF ``pathlines_orbit``。
4. ``interpolation``: 抜いた真のフレーム / 線形ブレンド / 流れで補間(最大値投影)、誤差は数表 ``numbers``。
5. ``focus_surface``(GIF): 焦点掃引の時系列から起こした陰影つきの高さ場の動画。
6. ``numbers``: 上の全部の数字。

実データ: Cell Tracking Challenge の 3D+t(``FULLSEYE_CTC_DIR`` にある ``Fluo-N3DH-CHO/01/t000.tif`` … )が手元に
あれば ``volseq_render_orbit`` と ``volseq_pathline_render`` を同じ経路で通す(図 7、生データは commit しない。
無ければ飛ばして合成だけ)。

走らせ方: ``py -3.11 examples/poc_live4d.py``(図は ``out/figures/poc_live4d/``)。
"""
from __future__ import annotations

import glob
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
SHAPE = (20, 28, 28) if REDUCED else (28, 40, 40)
T = 16 if REDUCED else 24
PERIOD = 8.0
AMP = 0.1                      # 目に見えない拍動(voxel)
ALPHA = 8.0
SPEED = 0.75                   # 分かれる塊の速さ(voxel/frame)
SIZE = 200 if REDUCED else 256
DEPTH = 64 if REDUCED else 96


def _grids(shape):
    return np.meshgrid(*[np.arange(n) - (n - 1) / 2.0 for n in shape], indexing="ij")


def radius_of(vol: np.ndarray) -> float:
    """殻の半径の読み取り(明るさで重みづけた中心からの距離)。"""
    zz, yy, xx = _grids(vol.shape)
    d = np.sqrt(zz ** 2 + yy ** 2 + xx ** 2)
    w = np.clip(vol, 0.0, None)
    return float((w * d).sum() / w.sum())


def weighted_flow(d: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """勾配のある場所で重みづけた変位の平均(平坦部の流れは決まらないので数えない)。"""
    g = np.linalg.norm(np.stack(np.gradient(ref)), axis=0)
    w = g / g.sum()
    return np.array([(d[i] * w).sum() for i in range(3)])


def focus_sweep_series(n_frames: int, Z: int = 11, Y: int = 40, X: int = 40, seed: int = 0):
    """動く山の焦点掃引: 高さ h(y, x, t) の面にテクスチャがあり、z 面ごとに |z − h| に応じてぼける。真値 = h。"""
    from scipy import ndimage as ndi
    rng = np.random.default_rng(seed)
    tex = ndi.gaussian_filter(rng.random((Y, X)), 0.7)
    yy, xx = np.mgrid[0:Y, 0:X]
    blurred = [ndi.gaussian_filter(tex, 0.3 + 0.9 * k) for k in range(Z)]
    series, truth = [], []
    for t in range(n_frames):
        cx = X * 0.25 + (X * 0.5) * t / max(n_frames - 1, 1)
        h = 2.5 + 5.0 * np.exp(-((yy - Y / 2) ** 2 + (xx - cx) ** 2) / (2 * (0.18 * X) ** 2))
        stack = np.empty((Z, Y, X))
        for z in range(Z):
            k = np.clip(np.rint(np.abs(z - h)).astype(int), 0, Z - 1)
            stack[z] = np.choose(k, blurred)
        series.append(stack)
        truth.append(h)
    return np.stack(series), np.stack(truth)


def ctc_series(max_t: int = 12, step: int = 4):
    """Cell Tracking Challenge の 3D+t(手元にあれば)。16 bit の多ページ TIFF を PIL で読み、y/x を step で間引く。"""
    root = os.environ.get("FULLSEYE_CTC_DIR") or os.path.join(
        os.environ.get("FULLSEYE_DATA_DIR", os.path.join(os.path.expanduser("~"), ".cache", "fullseye")), "ctc")
    files = sorted(glob.glob(os.path.join(root, "Fluo-N3DH-CHO", "01", "t*.tif")))[:max_t]
    if REDUCED or not files:
        return None, None
    try:
        from PIL import Image
    except ImportError:
        return None, None
    vols = []
    for f in files:
        im = Image.open(f)
        planes = []
        try:
            while True:
                planes.append(np.asarray(im, dtype=np.float64)[::step, ::step])
                im.seek(im.tell() + 1)
        except EOFError:
            pass
        vols.append(np.stack(planes))
    S = np.stack(vols)
    lo, hi = np.percentile(S, 1.0), np.percentile(S, 99.7)
    return np.clip((S - lo) / (hi - lo), 0.0, 1.0), "Fluo-N3DH-CHO/01 (%d volumes of %s, y/x 1/%d)" % (S.shape[0], S.shape[1:], step)


def main() -> int:
    t0 = time.time()
    L = fs.ledger
    rows = []

    # 1. 増幅 ------------------------------------------------------------------
    shell = L.volseq_synth_beating(SHAPE, n_frames=T, period=PERIOD, amplitude=AMP, radius=min(SHAPE) * 0.3, noise=0.0)
    r_lo, r_hi = 0.5 / PERIOD, 1.5 / PERIOD                     # 基本波(1/PERIOD)を含み、倍音(2/PERIOD)を含まない帯域
    big = L.volseq_magnify_motion(shell, alpha=ALPHA, f_lo=r_lo, f_hi=r_hi, fps=1.0, sigma=0.0)
    r0 = np.array([radius_of(shell[t]) for t in range(T)])
    r1 = np.array([radius_of(big[t]) for t in range(T)])
    amp0, amp1 = (r0.max() - r0.min()) / 2, (r1.max() - r1.min()) / 2
    gain = amp1 / amp0
    k0 = int(np.argmax(np.abs(np.fft.rfft(r0 - r0.mean()))[1:])) + 1
    k1 = int(np.argmax(np.abs(np.fft.rfft(r1 - r1.mean()))[1:])) + 1
    print("DATA: synthetic beating shell %s x %d frames, radius amplitude %.2f voxel (period %.0f frames)" % (SHAPE, T, AMP, PERIOD))
    print("magnify alpha=%.0f: read amplitude %.3f -> %.3f voxel = gain %.2f (period bin %d -> %d)" % (ALPHA, amp0, amp1, gain, k0, k1))
    assert 0.75 * ALPHA < gain < 1.25 * ALPHA, gain
    assert k0 == k1
    rows.append(("magnify: displacement gain (alpha = %.0f)" % ALPHA, "%.2f" % gain, "%.0f" % ALPHA))

    # 2. 流れと軌跡 -------------------------------------------------------------
    split = T // 3
    div = L.volseq_synth_dividing(SHAPE, n_frames=T, split_frame=split, speed=SPEED, sigma=0.09 * min(SHAPE))
    t_read = T - 2                                              # 離れてからの並進で読む
    d = L.vol_flow_3d(div[t_read], div[t_read + 1])
    xx = _grids(SHAPE)[2]
    right = xx > 0
    fr = weighted_flow(d * right[None], div[t_read] * right)
    fl = weighted_flow(d * (~right)[None], div[t_read] * ~right)
    print("flow on the dividing blob (t=%d -> %d): right half dx %+.3f (truth %+.2f), left half dx %+.3f (truth %+.2f)"
          % (t_read, t_read + 1, fr[2], SPEED, fl[2], -SPEED))
    assert abs(fr[2] - SPEED) < 0.1 * SPEED and abs(fl[2] + SPEED) < 0.1 * SPEED, (fr, fl)
    rows.append(("flow: speed of the right / left blob (voxel/frame)", "%+.3f / %+.3f" % (fr[2], fl[2]), "%+.2f / %+.2f" % (SPEED, -SPEED)))

    # 3. 補間 ------------------------------------------------------------------
    # 2 倍のレートの系列(分かれた後、塊が視野の中に留まる区間だけ)を半分に間引いて埋める。
    # 1 コマの動きを塊の大きさ(σ = 2.5 voxel)に対して振る —— 補間が線形ブレンドに勝つのは、動きが塊の
    # 大きさを越えてブレンドが二重像になる領域だけ(小さな動きではブレンドで足り、warp の再標本化が損)。
    SIG = 2.5
    regimes = []
    for v_fine in (0.25, 0.5, 1.0, 1.5, 2.5):
        fine = L.volseq_synth_dividing((20, 32, 80), n_frames=13, split_frame=0, speed=v_fine, sigma=SIG)[4:]
        coarse, held = fine[::2], fine[1::2]
        interp = L.volseq_interpolate_flow(coarse, factor=2)
        e_flow = float(np.sqrt(((interp[1::2] - held) ** 2).mean()))
        e_blend = float(np.sqrt(((0.5 * (coarse[:-1] + coarse[1:]) - held) ** 2).mean()))
        e_hold = float(np.sqrt(((coarse[:-1] - held) ** 2).mean()))
        regimes.append((2 * v_fine, e_flow, e_blend, e_hold, coarse, held, interp))
        print("interpolate x2, motion per coarse step %.1f voxel (%.1f sigma): RMSE flow %.4f | linear blend %.4f | repeat previous %.4f"
              % (2 * v_fine, 2 * v_fine / SIG, e_flow, e_blend, e_hold))
    step_big, err_flow, err_blend, err_hold, coarse, held, interp = regimes[-1]
    assert err_flow < 0.4 * err_blend, (err_flow, err_blend)
    assert all(r[1] < r[3] for r in regimes)                 # どの動きでも「前のフレームを繰り返す」よりは良い
    rows.append(("interpolate at %.0f voxel / step (%.0f sigma): RMSE flow / blend / repeat" % (step_big, step_big / SIG),
                 "%.4f / %.4f / %.4f" % (err_flow, err_blend, err_hold), "flow < 0.4 x blend"))
    rows.append(("interpolate at %.1f voxel / step (%.1f sigma): RMSE flow / blend" % (regimes[0][0], regimes[0][0] / SIG),
                 "%.4f / %.4f" % (regimes[0][1], regimes[0][2]), "blend is enough below ~1 sigma"))
    fine_s = L.volseq_synth_beating(SHAPE, n_frames=2 * T - 1, period=2 * PERIOD, amplitude=2.0, radius=min(SHAPE) * 0.3)
    interp_s = L.volseq_interpolate_flow(fine_s[::2], factor=2)
    es_flow = float(np.sqrt(((interp_s[1::2] - fine_s[1::2]) ** 2).mean()))
    es_blend = float(np.sqrt(((0.5 * (fine_s[::2][:-1] + fine_s[::2][1:]) - fine_s[1::2]) ** 2).mean()))
    print("interpolate x2 on the beating shell (radial motion): RMSE flow %.4f | linear blend %.4f" % (es_flow, es_blend))
    rows.append(("interpolate (beating shell): RMSE flow / blend", "%.4f / %.4f" % (es_flow, es_blend), "reported, not asserted"))

    # 4. 高さ場 ----------------------------------------------------------------
    sweep, h_true = focus_sweep_series(6 if REDUCED else 10)
    h = L.focus_sweep_height_video(sweep, window=5)
    h_err = float(np.sqrt(((h - h_true) ** 2).mean()))
    print("focus sweep %s: height RMSE %.3f planes (truth = moving bump, 11 planes)" % (sweep.shape, h_err))
    assert h_err < 0.5, h_err
    rows.append(("focus sweep: height RMSE (planes)", "%.3f" % h_err, "< 0.5"))

    # 5. 実データ(あれば) ---------------------------------------------------------
    real, real_src = ctc_series()
    if real is not None:
        print("DATA: %s (raw data never committed)" % real_src)
        rows.append(("real data", real_src, "-"))

    # 図 -----------------------------------------------------------------------
    if figs.enabled():
        nf = 24 if REDUCED else 36
        loops = 2
        o0 = L.volseq_render_orbit(shell, n_frames=nf, loops=loops, size=SIZE, depth_samples=DEPTH, floor=0.15)
        o1 = L.volseq_render_orbit(np.clip(big, 0.0, None), n_frames=nf, loops=loops, size=SIZE, depth_samples=DEPTH, floor=0.15)
        figs.save_gif("beating_orbit", np.concatenate([o0, o1], axis=2), fps=8.0,
                      caption="a shell whose radius beats by %.1f voxel, orbited while time advances (%d beats per turn): left = as measured (the beat is invisible), right = motion magnified x%.0f by volseq_magnify_motion" % (AMP, loops * T / PERIOD, ALPHA))
        tt = np.arange(T)
        figs.save_plot("radius_trace", [("measured", tt, r0 - r0.mean()), ("magnified x%.0f" % ALPHA, tt, r1 - r1.mean()),
                                        ("truth x %.0f" % ALPHA, tt, ALPHA * AMP * np.sin(2 * np.pi * tt / PERIOD))],
                       xlabel="frame", ylabel="radius - mean (voxel)", title="radius read from the volumes",
                       caption="radius of the shell read from each volume: the measured beat (%.2f voxel) is below one voxel; after magnification it follows alpha x truth" % AMP)
        img = L.volseq_pathline_render(div, n_seeds=80 if REDUCED else 120, size=SIZE, static_alpha=0.04, trail_sigma=0.5, seed=3)
        figs.save("pathlines", img, caption="pathlines of particles carried by the 3-D flow of the dividing blob, coloured by time (blue = start, red = end); the faint grey is the first volume")
        orb = L.volseq_pathline_orbit(div, n_frames=nf, n_seeds=80 if REDUCED else 120, size=SIZE, static_alpha=0.04, trail_sigma=0.5, seed=3)
        figs.save_gif("pathlines_orbit", orb, fps=8.0, caption="the same pathlines orbited: two straight bundles leaving the split point at +/-%.2f voxel/frame" % SPEED)
        mid = len(held) // 2
        panels = [held[mid].max(axis=0), (0.5 * (coarse[mid] + coarse[mid + 1])).max(axis=0), interp[2 * mid + 1].max(axis=0)]
        figs.save_grid("interpolation", panels, captions=["held-out true frame", "linear blend (ghosting)", "flow interpolation"],
                       ncols=3, gray=True, caption="a frame removed from a 2x-rate series (motion %.0f voxel = %.0f sigma per step) re-created two ways (max projections): the linear blend shows two ghosts per blob, the flow interpolation one blob at the right place (RMSE %.4f vs %.4f)" % (step_big, step_big / SIG, err_flow, err_blend))
        steps = np.array([r[0] / SIG for r in regimes])
        figs.save_plot("interpolation_regimes", [("flow interpolation", steps, np.array([r[1] for r in regimes])),
                                                 ("linear blend", steps, np.array([r[2] for r in regimes])),
                                                 ("repeat previous frame", steps, np.array([r[3] for r in regimes]))],
                       xlabel="motion per step (sigma of the blob)", ylabel="RMSE vs held-out frame", title="when does flow interpolation pay?",
                       caption="error of the re-created frames against the removed ones, as the motion per step grows: below about one blob width a linear blend is as good (the warp's resampling costs a little), above it the blend ghosts and the flow interpolation wins")
        surf = L.focus_sweep_surface_video(sweep, window=5, zscale=1.5)
        figs.save_gif("focus_surface", surf, fps=4.0, caption="height field recovered from a focus sweep series (a moving bump, 11 planes), shaded and coloured by height (blue = low, red = high); RMSE %.2f planes" % h_err)
        if real is not None:
            ro = L.volseq_render_orbit(real, n_frames=nf, loops=1, size=SIZE, depth_samples=DEPTH, floor=0.2, percentile=99.8)
            figs.save_gif("ctc_orbit", ro, fps=8.0, caption="%s: the live volumes orbited while time advances (intensity as opacity)" % real_src)
            try:
                rp = L.volseq_pathline_render(real, n_seeds=150, size=SIZE, static_alpha=0.06, trail_sigma=0.5, seed=3, min_speed=0.2)
                figs.save("ctc_pathlines", rp, caption="%s: pathlines of the 3-D flow between consecutive volumes, coloured by time" % real_src)
            except ValueError as e:
                print("ctc pathlines skipped:", e)
        figs.save_table("numbers", ["quantity", "read", "truth / bar"], rows, title="live4d PoC numbers",
                        caption="every number above, next to its truth")
        assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
