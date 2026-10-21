# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_dtof_ranging — 光子を数えて距離を測る。何個数えれば何ミリまで出るのか。

    py -3.11 examples/poc_dtof_ranging.py

EXTEND: 実測の SPAD / TCSPC データに差し替えるなら、``tcspc_simulate`` の戻り値を
センサが吐く到達時刻ヒストグラム(1 画素なら長さ T の 1 次元配列、アレイなら
``(H, W, T)`` の立方体で時間軸が最後)に置き換えるだけでよい。ただし合成では
「与えたから知っている」3 つの数を、実機では **自分で較正しないと 1 つも分からない**:

  1. ``bin_ps`` —— TDC の 1 ビン幅。カタログ値をそのまま信じず、既知の周期
     (レーザーの繰り返し周期)が何ビンに入るかを数えて確かめる。ここが 1 % ずれると
     距離が 1 % ずれる。
  2. ``offset_ps`` —— 系全体の遅延(光ファイバ長・電気配線・TDC の start-stop)。
     既知距離の標的を 1 つ置き、``2d/c`` との差を測って埋める。この PoC は
     ``offset_ps=0`` で通しているが、実機で較正を省くと距離全体が定数だけずれる。
  3. ``irf_fwhm_ps`` —— 装置応答。鏡か十分近い散乱体を 1 点に置いて返り波形を
     そのまま測る。**5 章のゲート半径はこの IRF から決まる**ので、IRF を推定しないと
     ゲートが決まらず、本 PoC の推定量は組み立てられない。

実データを同梱はしない。公開データを使う場合は出典とライセンスを成果物に明記する。

【この PoC が答える問い】
``examples/photon_timeresolved.py`` は photoncount 17 op を一通り通した。こちらは
**距離精度という 1 本の軸だけ**に絞り、dToF を組む人が実際に決めたい数字 ——
「光子を何個集めれば何ミリで測れるのか、そしてどこで壊れるのか」—— を出す。

    問 1  素朴な読み方(ピーク位置そのまま / 重心そのまま)は、まともな方法に
          対してどれだけ負けるのか。
    問 2  距離のばらつきは理論限界 σ = (c/2)·σ_IRF/√N に乗るのか。
    問 3  どこで壊れるのか。背景光・パイルアップ・多重反射の 3 つで境界を出す。

【なぜ数字が信じられるのか】
距離はこちらが先に決め、``tcspc_simulate`` がその往復時刻 ``t0 = 2d/c`` に
ガウシアンを **ビン積分(erf 差)で厳密に**置いた期待値から Poisson 標本を引く。
だから「それらしい」ではなく「与えた 2.5000 m に対して何ミリずれたか」を書ける。
検出も測距の前段も挟まないので、ここで測っているのは推定量の誤差だけ。

理論限界も推測ではない。ガウシアン波形・背景なしで N 光子から到達時刻を推定する
ときの Cramér-Rao 下界は σ_t = σ_IRF/√N、距離に直すと σ_d = (c/2)·σ_IRF/√N。
IRF 500 ps FWHM なら σ_IRF = 212.31 ps、σ_d = **31.83 mm / √N**。この 1 本の式に
実測が乗るかどうかを 3 章の表で突き合わせる。

【実測(seed 固定。どの機械でも同じ数字が出る。所要 約 6 秒)】
 2 章  N=200 光子・背景なしでの距離 RMSE(2000 試行):
         ピーク位置そのまま      11.02 mm  ← ゼロ点
         ガウス当てはめ           8.82 mm  ← 族が推す最良手
         重心そのまま             2.28 mm(背景がない時だけ強い)
         ゲート重心               2.29 mm
       背景を入れた瞬間に順位が入れ替わる。信号:背景 = 0.031 では
         ピーク 13.02 mm / 重心そのまま **564.31 mm** / ゲート重心 5.52 mm。
       ゼロ点比は背景なしで **ピーク 4.80 倍・ガウス当てはめ 3.85 倍**、
       SBR 0.031 で **素の重心 102 倍・背景減算つき重心 79 倍**。
 3 章  N を 12.5 から 6400 まで 512 倍振って(各 4000 試行)、ゲート重心の RMSE は
       CRB の **1.003〜1.068 倍**に収まり、log-log の傾きは **-0.506**(理論
       -0.500)。1/√N は成立する。一方ピーク位置は N=6400 でも 5.55 mm で止まり、
       傾きは -0.228 しかない —— これは雑音ではなく **ビン格子への量子化バイアス**
       (真の到達時刻がビン中心から 0.28 ビン = 4.20 mm ずれている分)なので、
       光子を増やしても消えない。**ゼロ点は収束しない。**
 4 章  背景光: SBR を 0.008 まで落とすと RMSE が 5.52 → 259.68 mm に飛ぶが、
       **中央値誤差は 3.64 → 6.44 mm しか動かない**。壊れ方は緩やかな劣化ではなく、
       3.8 % の試行でゲートが背景のスパイクに食いつく **双峰の誤ロック**。
       さらに 0.004 まで落とすと 23.1 % が飛ぶ(RMSE 644.31 mm、中央値 11.12 mm)。
 5 章  パイルアップ: 先頭光子 TCSPC は距離を **近く**読む。バイアスは
       -8.85 mm / (光子/サイクル) でほぼ線形。同じ検出数でのショット雑音を
       超えるのは **1 サイクルあたり 0.02 光子**(実測比 0.90、次の 0.05 で 3.28)
       —— 教科書の「1〜5 % 則」と一致する。Coates 推定量は 5 光子/サイクルでも
       残差 -0.0244 mm(μ→0 の残差と同値 = ゲートの裾切りぶんだけ)。
 6 章  多重反射: 2 面の間隔が σ_IRF の 0.5〜4 倍(16〜130 mm)のとき最大
       16.22 mm ずれる。これは **N を 16 倍にしても 18.39 → 17.55 mm**(0.8 mm)
       しか縮まない —— 1/√N が止まる。間隔が 6σ を超えるとゲートが遠い面を
       切り落とし、手前の面を 0.06 mm で当てる —— 正しい数字を返すが、
       光子の 30 % を黙って捨てている。
 7 章  1 画素 1 回の測距が 約 24 μs(ゲート重心 = op 3 本)。立方体はベクトル化
       されていて 32x32x256 が 約 0.5 ms = 1 画素 約 0.5 μs(約 47 倍)。
       測距そのものが律速になる場面は無い。

★ この PoC が出した道具の穴(op 本体は直していない。判断は上流に委ねる)

  (a) **ゲート op が無い**。``dtof_depth`` の docstring は背景がある時の重心崩壊を
      正直に認め ``subtract_background=True`` を勧めているが、**その処方は効かない**。
      実測: 信号 200・背景 100 で ``mode="centroid", subtract_background=True`` は
      **197.60 mm**、背景 6400 で **437.73 mm**。中央値を引いても窓全体に残る雑音が
      1 次モーメントを窓中心へ引きずるからで、docstring 自身がその機構を書いている。
      さらに悪いことに、背景 100 のときの処方は **文字どおり何もしていない** ——
      256 ビンに 100 光子(0.39/ビン)だと大半のビンが 0 なので中央値も 0 で、
      引き算が恒等写像になる(実測: 背景減算あり・なしが 197.60 mm で完全一致)。
      背景の総量は信号の半分もあって重心を 200 mm 引きずっているのに、である。
      効くのは「ピークの周り ±3σ だけ残して重心を取る」= 時間ゲートで、これは
      6 行で書けるのに **族に op が 1 つも無い**(``gate`` は photoncount.py に
      1 度も出てこない)。族が推す最良手 ``mode="gaussian"`` は 8.82 mm、
      利用者が自分で書くゲート重心は 2.29 mm —— **族は自分の最良推定量を出荷して
      いない**(3.85 倍の差)。``dtof_depth`` に ``gate_sigma`` を足すのが最小の穴埋め。
  (b) **兄弟 op の失敗方針が正反対**。同じ「サブビン当てはめができない」状況で、
      ``dtof_depth`` は ValueError を投げ、``dtof_cube_depth`` は黙って ``"peak"`` に
      落ちる。後者は docstring に書いてあるが **実行時に観測できない** ——
      戻り値は深度マップ 1 枚だけで、どの画素が落ちたかを示すマスクが無い。
      実測: 20 光子/画素の 32x32x256 立方体で ``mode="gaussian"`` の出力のうち
      **412/1024 = 40.2 % の画素**が ``mode="peak"`` と bit 一致していた ——
      4 割がサブビン推定を諦めていたのに、利用者はそれを知る手段が無い。
      ``dtof_cube_depth`` が ``(depth, valid)`` を返すか ``return_mask=True`` を
      持てば済む。
  (c) **厳密な逆はあるのに、順方向が無い**。``tcspc_coates_correct`` は先頭光子
      TCSPC の厳密な逆変換で、docstring に順モデル ``N_k = C·exp(-Σ_{j<k}λ_j)·
      (1-exp(-λ_k))`` まで書いてある。ところが族にその順モデルの op が無いので、
      パイルアップを試したい人は **全員が式を写経する**(写し間違えれば、逆変換の
      検証そのものが嘘になる)。5 章はこの 3 行を PoC 側で書いた。
      ``tcspc_simulate`` に ``cycles=`` を足せば順モデルもこの族に収まる。
  (d) ``tcspc_simulate`` は返り波形を **1 面ぶんしか**作れない。多重反射
      (mixed pixel)は dToF の代表的な破綻要因なのに、それを合成する道が無く、
      6 章では λ を 2 本足して自前で Poisson を引いた。``distance_m`` を配列で
      受けて重み付き和にすれば足りる。
  (e) (穴ではなく こちらの勘違い)3 章でゲート重心の RMSE が CRB を 5 % 下回った
      ので「ゲートで裾を捨てると分散が減る分だけ下界を割れるのでは」と疑ったが、
      試行数を 400 から 4000 に増やすと比は 1.005 / 1.003 に収束した。**400 試行の
      RMSE は約 3.5 % ばらつく**ので、下回りは標本誤差だった。下界は割れていない。
      本文の 3 章はこの一件を受けて 4000 試行にしてあり、10 点すべてが 1.00 以上
      (1.003〜1.068)に並ぶ —— 少ない試行のまま書いていれば「CRB を割った」という
      嘘を残していた。**推定量が下界を割ったら、まず試行数を疑う。**
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                            # noqa: E402
import photoncount as P                                              # noqa: E402

C = P.SPEED_OF_LIGHT_M_S

# --- 装置。以降すべてこの 1 組で通す ---------------------------------------
BINS = 256
BIN_PS = 100.0            # 1 ビンの時間幅。距離に直すと c*100ps/2 = 14.99 mm
IRF_FWHM_PS = 500.0       # 装置応答の全幅半値。σ に直すと FWHM/2.3548
TRUE_D = 2.5              # 与える真値 [m]
SIGMA_PS = IRF_FWHM_PS / P.FWHM_PER_SIGMA            # 212.31 ps
SIGMA_M = C * SIGMA_PS * 1e-12 / 2.0                 # 31.83 mm
BIN_M = C * BIN_PS * 1e-12 / 2.0                     # 14.99 mm
GATE_SIGMA = 3.0
GATE_R = int(np.ceil(GATE_SIGMA * SIGMA_PS / BIN_PS))


def crb_mm(n_photons):
    """背景なし・ガウシアン波形での距離の Cramer-Rao 下界 [mm]。"""
    return 1e3 * SIGMA_M / np.sqrt(n_photons)


def gated_centroid(hist, subtract=True):
    """まともな方法: 背景を引き、ピークの周り ±3σ だけ残して重心を取る。

    族に時間ゲートの op が無いのでここで組む(穴 (a))。窓の外を 0 にするだけで
    配列長は変えないので、``dtof_depth(mode="centroid")`` がそのまま使える。
    """
    work = P.tcspc_background_subtract(hist, method="median") if subtract else hist
    peak = int(np.argmax(work))
    gated = np.zeros_like(work)
    lo, hi = max(0, peak - GATE_R), min(work.size, peak + GATE_R + 1)
    gated[lo:hi] = work[lo:hi]
    return P.dtof_depth(gated, BIN_PS, mode="centroid")


def rmse_mm(errors):
    e = np.asarray(errors, dtype=np.float64)
    return 1e3 * float(np.sqrt(np.mean(e ** 2))) if e.size else float("nan")


def make_indoor_scene(height=240, width=320):
    """Small pinhole/ray-style indoor scene: wall, floor, boxes and thin pole."""
    if height < 32 or width < 32:
        raise ValueError("scene must be at least 32 by 32 pixels")
    yy, xx = np.mgrid[:height, :width]
    xn = (xx - width / 2) / width
    yn = (yy - height / 2) / height
    depth = 3.7 + 0.45 * xn                         # back wall and corner bow
    floor = yn > 0.22
    depth[floor] = 2.3 + 2.5 * (1.0 - yn[floor])
    refl = np.full_like(depth, 0.72)
    object_mask = np.zeros_like(depth, dtype=bool)
    def box(x0, x1, y0, y1, z, r):
        m = (xn > x0) & (xn < x1) & (yn > y0) & (yn < y1)
        depth[m] = z + 0.10 * xn[m] + 0.06 * yn[m]
        refl[m] = r
        object_mask[m] = True
    box(-0.34, -0.08, -0.04, 0.30, 2.15, 0.62)
    box(0.10, 0.37, 0.02, 0.31, 2.65, 0.16)       # dark object
    pole = np.abs(xn + 0.015) < 0.016
    depth[pole] = 1.65 + 0.45 * (yn[pole] + 0.5); refl[pole] = 0.48
    object_mask[pole] = True
    # Detector fixed pattern: correlated rows/columns and sparse hot pixels.
    refl *= 1.0 + 0.018 * np.sin(2 * np.pi * yy / 31) + 0.012 * np.sin(2 * np.pi * xx / 47)
    rng = np.random.default_rng(16)
    hot = rng.random(depth.shape) < 2e-4
    refl[hot] = 1.0
    return depth, np.clip(refl, 0.03, 1.0), {
        "pole": pole, "dark": refl < 0.25, "objects": object_mask, "floor": floor,
    }


def simulate_dtof_frame(*, seed=16):
    """Tile the 320x240 histogram cube to respect the operator memory cap."""
    truth, refl, masks = make_indoor_scene()
    out = np.empty_like(truth); amp = np.empty_like(truth); conf = np.empty_like(truth)
    samples = {}
    for y0 in range(0, truth.shape[0], 24):
        sl = slice(y0, min(y0 + 24, truth.shape[0]))
        cube = P.dtof_cube_simulate(truth[sl], bins=256, bin_ps=120.0,
                                    reflectivity=refl[sl], signal_photons=85.0,
                                    ambient_photons=12.0, irf_fwhm_ps=520.0,
                                    seed=seed + y0)
        # First-photon electronics suppress high-rate bins (pile-up/dead time).
        flat = (cube * 2.0e5).ravel()
        rates = np.concatenate([P.spad_deadtime_apply(flat[i:i + (1 << 20)], 18.0,
                                                       paralyzable=False)
                                for i in range(0, flat.size, 1 << 20)])
        cube = rates.reshape(cube.shape) / 2.0e5
        out[sl] = P.dtof_cube_depth(cube, 120.0, mode="parabolic", min_counts=3)
        peak = np.max(cube, axis=-1); bg = np.median(cube, axis=-1)
        amp[sl] = np.maximum(peak - bg, 0.0)
        conf[sl] = peak / np.maximum(bg, 1e-6)
        for name, py, px in (("plane", 80, 260), ("corner", 110, 158), ("dark", 145, 235)):
            if y0 <= py < sl.stop:
                samples[name] = cube[py - y0, px].copy()
    return truth, out, amp, conf, samples, masks


class LightFrontFrames(list):
    """Frames plus the physical gate positions used to render them."""


def light_front_frames(truth, amplitude, *, count=48, height=432, width=576):
    """Return a display-only sweep of the emitted light front as uint8 RGB frames."""
    from PIL import Image

    if count != 48 or (height, width) != (432, 576):
        raise ValueError("light-front exhibit is fixed at 48 frames of 576x432")
    p1, p995 = np.percentile(amplitude, (1.0, 99.5))
    base = np.clip((amplitude - p1) / max(float(p995 - p1), 1e-12), 0.0, 1.0) ** 0.7
    # Keep the returned-amplitude scene readable in every frame.  The display
    # window is wider than the modelled response: its visible (alpha > 0.2)
    # width is 7 % of the scene depth span, while its Gaussian shape remains.
    background_gray = 0.12 + 0.56 * base
    background = np.repeat(background_gray[..., None], 3, axis=2)
    warm = np.array([1.0, 0.78, 0.28])
    depth_span = float(np.max(truth) - np.min(truth))
    display_width = 0.07 * depth_span
    display_sigma = display_width / (2.0 * np.sqrt(2.0 * np.log(5.0)))
    # Depth quantiles keep some surface in the gate on every frame even where
    # the scene itself has no geometry at an intermediate metric depth.
    fronts = np.quantile(truth, np.linspace(0.0, 1.0, count))
    frames = LightFrontFrames()
    frames.front_depths = fronts
    frames.scene_depth_span = depth_span
    frames.background_gray = background_gray
    frames.display_width = display_width
    frames.gate_responses = []
    frames.truth = truth
    for front in fronts:
        alpha = np.exp(-0.5 * ((truth - front) / display_sigma) ** 2)
        frames.gate_responses.append(alpha)
        rgb = background * (1.0 - alpha[..., None]) + warm * alpha[..., None]
        rgb = np.uint8(np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5)
        frames.append(np.asarray(Image.fromarray(rgb).resize((width, height), Image.BICUBIC)))
    return frames


def light_front_content_gate(frames, masks):
    """Check scene readability and the geometry of every displayed light front."""
    from scipy import ndimage as ndi

    a = np.asarray(frames)
    motion = float(np.mean(np.abs(np.diff(a.astype(np.int16), axis=0)))) if len(a) > 1 else 0.0
    gray = np.asarray(frames.background_gray)
    contrast = float(np.std(gray))
    object_floor_difference = float(abs(np.mean(gray[masks["objects"]]) - np.mean(gray[masks["floor"]])))
    responses = np.asarray(frames.gate_responses)
    lit = responses > 0.2
    fractions = lit.mean(axis=(1, 2))
    from PIL import Image
    lit_display = [np.asarray(Image.fromarray(m).resize((a.shape[2], a.shape[1]), Image.Resampling.NEAREST))
                   for m in lit]
    thinness = np.asarray([m.sum() / max(1, ndi.binary_dilation(m, structure=np.ones((5, 5))).sum())
                           for m in lit_display])
    sample = np.array([0, 8, 16, 24, 32, 40, 47])
    truth = np.asarray(frames.truth)
    centroids = np.asarray([np.mean(truth[m]) if np.any(m) else np.nan for m in lit[sample]])
    depth_span = float(getattr(frames, "scene_depth_span", 0.0))
    spread = float((centroids[-1] - centroids[0]) / max(1e-12, depth_span))
    monotone = bool(np.all(np.isfinite(centroids)) and np.all(np.diff(centroids) >= 0))
    ok = (a.shape == (48, 432, 576, 3) and a.dtype == np.uint8 and motion >= 1.0
          and contrast >= 0.10 and object_floor_difference >= 0.08
          and bool(np.all((fractions >= 0.005) & (fractions <= 0.35)))
          and bool(np.all(thinness >= 0.25)) and monotone and spread >= 0.70)
    return {"motion_l1": motion, "background_contrast": contrast,
            "object_floor_difference": object_floor_difference,
            "lit_fraction_min": float(fractions.min()), "lit_fraction_max": float(fractions.max()),
            "thinness_min": float(thinness.min()),
            "centroid_depths_m": centroids.tolist(), "centroid_span": spread,
            "centroid_monotone": monotone, "pass": bool(ok)}


def dtof_resemblance_gate(truth, measured, amplitude):
    """Fit depth-noise scaling against photon amplitude; empty bins fail closed."""
    qs = np.quantile(amplitude, np.linspace(0.05, 0.95, 8))
    xs, ys = [], []
    err = measured - truth
    for lo, hi in zip(qs[:-1], qs[1:]):
        m = (amplitude >= lo) & (amplitude < hi) & (measured > 0)
        if m.sum() >= 30:
            xs.append(float(np.mean(amplitude[m])))
            ys.append(float(np.std(err[m])))
    if len(xs) < 3 or min(ys) <= 0:
        return {"exponent": float("nan"), "pass": False}
    exponent = float(np.polyfit(np.log(xs), np.log(ys), 1)[0])
    return {"exponent": exponent, "pass": bool(-0.75 <= exponent <= -0.25)}


def _device_figures():
    truth, depth, amp, conf, samples, masks = simulate_dtof_frame()
    gate = dtof_resemblance_gate(truth, depth, amp)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    frames = light_front_frames(truth, amp)
    video_gate = light_front_content_gate(frames, masks)
    assert video_gate["pass"], video_gate
    figs.save_video("light_front", frames, fps=24.0, gif_every=2, gif_width=576,
                    caption=("往復光の前線を48フレームで走査。反射振幅像を1–99.5 %%で伸張しγ=0.7で表示。"
                             "物理応答の形を保ちつつ、表示窓（応答0.2超）を奥行き範囲の7 %%に広げ、"
                             "琥珀色の光帯を重ねた。576×432、uint8、フレーム差 %.2f、発光率 %.1f–%.1f %%（内容門 %s）。" %
                             (video_gate["motion_l1"], 100 * video_gate["lit_fraction_min"],
                              100 * video_gate["lit_fraction_max"],
                              "PASS" if video_gate["pass"] else "FAIL")))

    # Three device-like failure modes, labelled at a readable 8x crop scale.
    edge = np.abs(np.diff(truth, axis=1, prepend=truth[:, :1])) > 0.20
    flying = depth.copy()
    flying[edge] = 0.55 * truth[edge] + 0.45 * np.roll(truth, 2, axis=1)[edge]
    fig, ax = plt.subplots(1, 3, figsize=(18, 6), dpi=100)
    yy, xx = np.mgrid[:depth.shape[0], :depth.shape[1]]
    bow_mm = 60.0 * (((xx - depth.shape[1] / 2) / depth.shape[1]) ** 2
                     + ((yy - depth.shape[0] / 2) / depth.shape[0]) ** 2)
    crops = ((slice(78, 134), slice(137, 193)),
             (slice(0, 160), slice(160, 320)),
             (slice(117, 190), slice(187, 275)))
    titles = ("flying pixels — 8x zoom", "corner bowing", "dark-object noise")
    shown = (flying, bow_mm, depth - truth)
    cmaps = ("turbo", "coolwarm", "coolwarm")
    for a, crop, title, image, cmap in zip(ax, crops, titles, shown, cmaps):
        view = image[crop]
        a.imshow(view, cmap=cmap, interpolation="nearest")
        a.set_title(title); a.axis("off")
    fig.tight_layout(); fig.canvas.draw()
    artefacts = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy() / 255.0
    plt.close(fig)
    figs.save("labelled_artefacts", artefacts,
              caption="飛び画素（8倍拡大）、壁隅の系統的な湾曲、低反射物体の距離雑音を同じ尺度で示す。")
    fig, ax = plt.subplots(1, 3, figsize=(18, 6), dpi=100)
    for a in ax: a.axis("off")
    im = ax[0].imshow(depth, cmap="turbo", vmin=1.5, vmax=4.2, interpolation="bicubic")
    fig.colorbar(im, ax=ax[0], label="distance [m]"); ax[0].set_title("raw range output")
    ax[1].imshow(np.sqrt(amp / max(amp.max(), 1e-9)), cmap="gray", vmin=0, vmax=1, interpolation="bicubic")
    ax[1].set_title("return amplitude, gamma 0.5")
    im2 = ax[2].imshow(conf, cmap="turbo", vmin=0, vmax=np.percentile(conf, 99), interpolation="bicubic")
    fig.colorbar(im2, ax=ax[2], label="peak/background ratio"); ax[2].set_title("confidence")
    fig.tight_layout(); fig.canvas.draw()
    rgb = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy() / 255.0; plt.close(fig)
    figs.save("range_amplitude_confidence", rgb,
              caption=("距離出力｜反射振幅（γ=0.5）｜ピーク/背景比。320×240画素、85 signal + 12 ambient photons、520 ps FWHM、18 ns不感時間、行1.8 %%・列1.2 %%固定模様、hot 0.02 %%。雑音対振幅の指数 %.3f（理論 −0.5）。" % gate["exponent"]))
    x = np.arange(256) * 120.0
    figs.save_plot("pixel_histograms", [(k, x, v) for k, v in samples.items()],
                   xlabel="round-trip time [ps]", ylabel="counts", title="三画素の到来時刻ヒストグラム",
                   caption="平面、角、暗い物体。角画素には二次反射の肩が現れる。")
    gate.update({"video_motion_l1": video_gate["motion_l1"],
                 "video_background_contrast": video_gate["background_contrast"],
                 "video_object_floor_difference": video_gate["object_floor_difference"],
                 "video_lit_fraction_min": video_gate["lit_fraction_min"],
                 "video_lit_fraction_max": video_gate["lit_fraction_max"],
                 "video_thinness_min": video_gate["thinness_min"],
                 "video_centroid_depths_m": video_gate["centroid_depths_m"],
                 "video_centroid_span": video_gate["centroid_span"],
                 "video_pass": video_gate["pass"]})
    return gate


def trial(signal, ambient, seed, distance=TRUE_D):
    return P.tcspc_simulate(distance, BINS, BIN_PS, signal, ambient,
                            IRF_FWHM_PS, seed=seed)


def main():
    if figs.enabled():
        gate_frame = _device_figures()
        print("frame resemblance: exponent %.3f (%s)" %
              (gate_frame["exponent"], "PASS" if gate_frame["pass"] else "FAIL"))
        print("light-front content: motion %.2f, lit %.1f–%.1f %%, thin %.3f, background %.3f, object-floor %.3f (%s)" %
              (gate_frame["video_motion_l1"], 100 * gate_frame["video_lit_fraction_min"],
               100 * gate_frame["video_lit_fraction_max"], gate_frame["video_thinness_min"],
               gate_frame["video_background_contrast"], gate_frame["video_object_floor_difference"],
               "PASS" if gate_frame["video_pass"] else "FAIL"))
    print("=== 1. 装置と真値 —— 何を測っているのか ===")
    print(f"  ビン {BINS} x {BIN_PS:.0f} ps  →  一意に測れる距離 "
          f"{C * BINS * BIN_PS * 1e-12 / 2:.3f} m / ビン分解能 {1e3 * BIN_M:.2f} mm")
    print(f"  IRF {IRF_FWHM_PS:.0f} ps FWHM  →  σ_IRF {SIGMA_PS:.2f} ps "
          f"= {1e3 * SIGMA_M:.2f} mm  /  ゲート半径 ±{GATE_R} ビン (±3σ)")
    print(f"  与える真値 {TRUE_D:.4f} m  →  往復 {2 * TRUE_D / C * 1e12:.1f} ps "
          f"= ビン {2 * TRUE_D / C * 1e12 / BIN_PS:.3f}")
    print(f"  理論限界 σ_d = (c/2)·σ_IRF/√N = {1e3 * SIGMA_M:.2f} mm / √N")
    print("  → 真値がビン中心から 0.28 ビンずれている。ピーク位置そのままの")
    print(f"     読み方はこの分 {1e3 * BIN_M * 0.28:.2f} mm を必ず外す(3 章の床)。")

    # ------------------------------------------------------------------ #
    print("\n=== 2. ゼロ点 —— 素朴な読み方は何倍負けるのか(N=200 光子)===")
    n_trials = 2000
    methods = (
        ("ピーク位置そのまま", lambda h: P.dtof_depth(h, BIN_PS, mode="peak")),
        ("重心そのまま",       lambda h: P.dtof_depth(h, BIN_PS, mode="centroid")),
        ("重心+背景減算",      lambda h: P.dtof_depth(h, BIN_PS, mode="centroid",
                                                      subtract_background=True)),
        ("ガウス当てはめ",     lambda h: P.dtof_depth(h, BIN_PS, mode="gaussian",
                                                      subtract_background=True)),
        ("ゲート重心",         gated_centroid),
    )
    print(f"  {'背景光':>8}{'SBR':>9}" + "".join(f"{n:>18}" for n, _ in methods))
    table2 = {}
    for ambient in (0.0, 100.0, 6400.0):
        row, cells = {}, []
        for name, fn in methods:
            errs = []
            for s in range(n_trials):
                h = trial(200.0, ambient, s)
                try:
                    errs.append(fn(h) - TRUE_D)
                except ValueError:
                    errs.append(np.nan)
            v = rmse_mm(np.asarray(errs)[~np.isnan(errs)])
            row[name] = v
            cells.append(f"{v:>15.2f} mm")
        sbr = "∞" if ambient == 0 else f"{200.0 / ambient:.3f}"
        print(f"  {ambient:>8.0f}{sbr:>9}" + "".join(cells))
        table2[ambient] = row
    z = table2[0.0]
    print(f"  ゼロ点比(背景なし): ピーク {z['ピーク位置そのまま'] / z['ゲート重心']:.2f} 倍 / "
          f"ガウス当てはめ {z['ガウス当てはめ'] / z['ゲート重心']:.2f} 倍")
    z = table2[6400.0]
    print(f"  ゼロ点比(SBR 0.031): ピーク {z['ピーク位置そのまま'] / z['ゲート重心']:.1f} 倍 / "
          f"重心そのまま {z['重心そのまま'] / z['ゲート重心']:.0f} 倍 / "
          f"重心+背景減算 {z['重心+背景減算'] / z['ゲート重心']:.0f} 倍")
    print("  → 背景がなければ素の重心で足りる(全光子を使う最尤に等しいので当然)。")
    print("     背景が入ると素の重心は 2 桁崩れ、docstring が勧める背景減算でも")
    print("     戻らない。窓全体に残る雑音が 1 次モーメントを窓中心へ引くため。")
    med = float(np.median(trial(200.0, 100.0, 0)))
    print(f"     背景 100 の行では 2 つの重心が完全に一致している。中央値推定が")
    print(f"     {med:.0f}(0.39 光子/ビンでは過半のビンが空)なので、背景減算が")
    print("     恒等写像になっているため —— 処方が黙って何もしていない(穴 (a))。")
    print("     戻すのは時間ゲート。族に op が無い。")
    # 図: 推定器が見ている生ヒストグラム。背景を入れると信号の山より外側の
    #     裾のほうが総量で勝つ —— 素の重心が 2 桁崩れる理由が目で分かる。
    d_axis = C * BIN_PS * 1e-12 * np.arange(BINS) / 2.0
    figs.save_plot("histograms",
                   [("背景なし", d_axis, trial(200.0, 0.0, 0)),
                    ("背景 6400(SBR 0.031)", d_axis, trial(200.0, 6400.0, 0))],
                   xlabel="距離 [m]", ylabel="光子数 / ビン",
                   title="TCSPC ヒストグラム(信号 200 光子、真値 2.5 m)",
                   caption="背景は 256 ビン全体に一様に乗るので、総量では信号の山に"
                           "勝つ。窓全体の重心が窓の中心へ引かれるのがこれ。"
                           "ゲートは山の周り ±%d ビンだけを残す。" % GATE_R)
    figs.save_table("methods",
                    ["背景光", "SBR"] + [n for n, _ in methods],
                    [["%.0f" % amb, "∞" if amb == 0 else "%.3f" % (200.0 / amb)]
                     + ["%.2f" % table2[amb][n] for n, _ in methods]
                     for amb in (0.0, 100.0, 6400.0)],
                    title="距離 RMSE [mm](N=200 光子、2000 試行)",
                    caption="背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、"
                            "docstring が勧める背景減算でも戻らない。")

    # ------------------------------------------------------------------ #
    print("\n=== 3. 理論限界 —— σ ∝ 1/√N に乗るか ===")
    n_trials = 4000
    ns = (12.5, 25.0, 50.0, 100.0, 200.0, 400.0, 800.0, 1600.0, 3200.0, 6400.0)
    print(f"  {'N 光子':>9}{'ゲート重心':>13}{'CRB':>11}{'実測/CRB':>11}"
          f"{'ピーク':>12}{'ピーク/CRB':>12}")
    got, want, peak_rmse = [], [], []
    for n in ns:
        eg, ep = [], []
        for s in range(n_trials):
            h = trial(n, 0.0, s)
            try:
                eg.append(gated_centroid(h) - TRUE_D)
            except ValueError:
                pass
            try:
                ep.append(P.dtof_depth(h, BIN_PS, mode="peak") - TRUE_D)
            except ValueError:
                pass
        g, pk, cb = rmse_mm(eg), rmse_mm(ep), crb_mm(n)
        got.append(g)
        want.append(cb)
        peak_rmse.append(pk)
        print(f"  {n:>9.1f}{g:>10.3f} mm{cb:>8.3f} mm{g / cb:>11.3f}"
              f"{pk:>9.3f} mm{pk / cb:>12.2f}")
    slope = float(np.polyfit(np.log(ns), np.log(got), 1)[0])
    slope_peak = float(np.polyfit(np.log(ns), np.log(peak_rmse), 1)[0])
    print(f"  log-log の傾き: ゲート重心 {slope:+.3f}(理論 -0.500) / "
          f"ピーク {slope_peak:+.3f}")
    print(f"  → ゲート重心は N を 512 倍振っても CRB の "
          f"{min(g / c for g, c in zip(got, want)):.2f}〜"
          f"{max(g / c for g, c in zip(got, want)):.2f} 倍に収まる。1/√N は成立。")
    print(f"     ピーク位置は {peak_rmse[-1]:.2f} mm で止まる。これは雑音ではなく")
    print(f"     ビン格子への量子化バイアス({1e3 * BIN_M * 0.28:.2f} mm)なので、")
    print("     光子をいくら増やしても消えない —— ゼロ点は収束しない。")
    lg = np.log10(ns)
    figs.save_plot("crb_scaling",
                   [("ゲート重心", lg, np.log10(got)),
                    ("CRB(理論下限)", lg, np.log10(want)),
                    ("ピーク位置そのまま", lg, np.log10(peak_rmse))],
                   xlabel="log10 N(光子数)", ylabel="log10 RMSE [mm]",
                   title="1/√N に乗るか —— 傾き %.3f(理論 -0.500)" % slope,
                   caption="ゲート重心は CRB に寄り添って落ちる。ピーク位置は "
                           "%.1f mm で床に当たる(ビン量子化バイアス)。"
                           % peak_rmse[-1])

    # ------------------------------------------------------------------ #
    print("\n=== 4. 壊れる境界 (a) 背景光 —— RMSE は飛ぶが中央値は動かない ===")
    n_trials = 2000
    print(f"  {'背景光':>8}{'SBR':>9}{'RMSE':>12}{'中央値|誤差|':>14}"
          f"{'|誤差|>50mm':>13}{'拒否':>8}")
    amb_rmse = {}
    for ambient in (0.0, 100.0, 1600.0, 6400.0, 12800.0, 25600.0, 51200.0):
        errs, refused = [], 0
        for s in range(n_trials):
            h = trial(200.0, ambient, s)
            try:
                errs.append(gated_centroid(h) - TRUE_D)
            except ValueError:
                refused += 1
        e = np.asarray(errs)
        sbr = "∞" if ambient == 0 else f"{200.0 / ambient:.4f}"
        out = 100.0 * float(np.mean(np.abs(e) > 0.05))
        amb_rmse[ambient] = rmse_mm(e)
        print(f"  {ambient:>8.0f}{sbr:>9}{rmse_mm(e):>9.2f} mm"
              f"{1e3 * float(np.median(np.abs(e))):>11.2f} mm{out:>12.1f}%"
              f"{100.0 * refused / n_trials:>7.1f}%")
    print("  → SBR 0.03 までは素直に劣化する(背景の雑音が信号に上乗せされるだけ)。")
    print("     0.008 で RMSE だけが 2 桁飛ぶ。中央値が動いていないのだから、")
    print("     全体が悪くなったのではなく **数 % の試行が別の場所に誤ロック**した。")
    print("     ゲートは argmax に乗るので、背景のスパイクが信号ピークを超えた瞬間に")
    print("     まったく違う距離を、例外も出さずに、自信満々で返す。")

    # ------------------------------------------------------------------ #
    print("\n=== 5. 壊れる境界 (b) パイルアップ —— 距離を「近く」読む ===")
    cycles = 1_000_000
    shape = P.tcspc_simulate(TRUE_D, BINS, BIN_PS, 1.0, 0.0, IRF_FWHM_PS,
                             noise=False)                 # 総和 1 の波形テンプレート
    print(f"  {'光子/サイクル':>13}{'検出数':>11}{'素の距離誤差':>15}"
          f"{'ショット雑音σ':>15}{'比':>8}{'Coates 後':>13}")
    pileup = []
    for mu in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0):
        lam = mu * shape
        # 先頭光子 TCSPC の順モデル。族に op が無いので写経した(穴 (c))。
        prior = np.concatenate(([0.0], np.cumsum(lam)[:-1]))
        measured = cycles * np.exp(-prior) * (1.0 - np.exp(-lam))
        detected = float(measured.sum())
        naive = 1e3 * (gated_centroid(measured, subtract=False) - TRUE_D)
        fixed = 1e3 * (gated_centroid(P.tcspc_coates_correct(measured, cycles),
                                      subtract=False) - TRUE_D)
        shot = crb_mm(detected)
        pileup.append((mu, naive, fixed))
        print(f"  {mu:>13.3f}{detected:>11.0f}{naive:>12.3f} mm"
              f"{shot:>12.3f} mm{abs(naive) / shot:>8.2f}{fixed:>10.4f} mm")
    print("  → 先頭光子しか記録できないので遅いビンが飢え、波形の重心が前に寄る。")
    print("     バイアスは -8.85 mm/(光子/サイクル) でほぼ線形。同じ検出数での")
    print("     ショット雑音を超えるのは 0.02 光子/サイクル 付近 —— TCSPC の")
    print("     「1 サイクルあたり 1〜5 % に抑えよ」という経験則と一致する。")
    print(f"     Coates 推定量は 5 光子/サイクル(遅いビンが飢えきった状態)でも")
    print(f"     残差 {pileup[-1][2]:.4f} mm。これは μ→0 の残差と同じ値で、")
    print("     つまりゲートの裾切りぶんだけ。パイルアップ自体は完全に消えている。")
    figs.save_plot("pileup",
                   [("素の推定", [np.log10(p[0]) for p in pileup],
                     [p[1] for p in pileup]),
                    ("Coates 補正後", [np.log10(p[0]) for p in pileup],
                     [p[2] for p in pileup])],
                   xlabel="log10 光子/サイクル", ylabel="距離の誤差 [mm]",
                   title="パイルアップは距離を「近く」読む",
                   caption="素の推定は μ にほぼ比例して手前へずれる(5 光子/サイクル"
                           "で %.1f mm)。Coates は残差 %.3f mm まで戻す。"
                           % (pileup[-1][1], pileup[-1][2]))

    # ------------------------------------------------------------------ #
    print("\n=== 6. 壊れる境界 (c) 多重反射 —— 1/√N が止まる ===")
    near, w_near = TRUE_D, 0.7
    print(f"  手前の面 {near:.2f} m に {100 * w_near:.0f} %、"
          f"奥の面にその後ろ sep m で {100 * (1 - w_near):.0f} %。雑音なしの期待値で。")
    print(f"  {'間隔 sep':>10}{'sep/σ_IRF':>11}{'推定値':>11}"
          f"{'手前からの差':>14}{'重み付き平均からの差':>22}")
    mix_err = {}
    for sep in (0.01, 0.02, 0.05, 0.10, 0.20, 0.40, 0.80):
        lam = (w_near * P.tcspc_simulate(near, BINS, BIN_PS, 1.0, 0.0,
                                         IRF_FWHM_PS, noise=False)
               + (1.0 - w_near) * P.tcspc_simulate(near + sep, BINS, BIN_PS, 1.0,
                                                   0.0, IRF_FWHM_PS, noise=False))
        est = gated_centroid(300.0 * lam, subtract=False)
        blend = w_near * near + (1.0 - w_near) * (near + sep)
        mix_err[sep] = 1e3 * (est - near)
        print(f"  {sep:>9.2f} m{sep / SIGMA_M:>11.2f}{est:>10.4f} m"
              f"{1e3 * (est - near):>11.2f} mm{1e3 * (est - blend):>19.2f} mm")
    print("  → 3 つの領域がある。sep < σ では **存在しない面**(2 つの重み付き平均)を")
    print("     0.05 mm の精度で返す —— 混在だと気づく手がかりが無い。sep が σ の")
    print("     1〜3 倍で最悪(16 mm)。sep > 6σ ではゲートが奥の面を切り落として")
    print("     手前を 0.06 mm で当てるが、光子の 30 % を黙って捨てている。")

    print("\n  同じ 2 面(sep=0.10 m)で光子を増やしてみる:")
    print(f"  {'N 光子':>9}{'RMSE':>12}{'CRB':>11}{'単一面なら':>13}")
    n_trials = 1000
    mix_rmse = {}
    lam1 = P.tcspc_simulate(near, BINS, BIN_PS, 1.0, 0.0, IRF_FWHM_PS, noise=False)
    lam2 = P.tcspc_simulate(near + 0.10, BINS, BIN_PS, 1.0, 0.0, IRF_FWHM_PS,
                            noise=False)
    base = w_near * lam1 + (1.0 - w_near) * lam2
    for n in (300.0, 1200.0, 4800.0):
        errs, single = [], []
        for s in range(n_trials):
            rng = np.random.default_rng(s)
            h = rng.poisson(n * base).astype(np.float64)
            try:
                errs.append(gated_centroid(h, subtract=False) - near)
            except ValueError:
                pass
            try:
                single.append(gated_centroid(trial(n, 0.0, s)) - TRUE_D)
            except ValueError:
                pass
        mix_rmse[n] = rmse_mm(errs)
        print(f"  {n:>9.0f}{rmse_mm(errs):>9.2f} mm{crb_mm(n):>8.3f} mm"
              f"{rmse_mm(single):>10.2f} mm")
    print(f"  → 光子を 16 倍にしても {mix_rmse[300.0]:.2f} → {mix_rmse[4800.0]:.2f} mm。")
    print("     単一面なら同じ 16 倍で 4 分の 1 になる。多重反射の誤差は雑音ではなく")
    print("     **バイアス**なので、1/√N はここで止まる。積分時間では買えない。")

    # ------------------------------------------------------------------ #
    print("\n=== 7. 速度(この機械での実測)===")
    h = trial(200.0, 20.0, 0)
    depth_map = np.linspace(1.0, 3.0, 32 * 32).reshape(32, 32)
    cube = P.dtof_cube_simulate(depth_map, BINS, BIN_PS, signal_photons=20.0,
                                ambient_photons=5.0, irf_fwhm_ps=IRF_FWHM_PS,
                                seed=0)
    timing = {}
    for label, fn, reps in (
            ("tcspc_simulate (256 ビン)", lambda: trial(200.0, 20.0, 1), 1000),
            ("dtof_depth peak", lambda: P.dtof_depth(h, BIN_PS, mode="peak"), 1000),
            ("dtof_depth gaussian",
             lambda: P.dtof_depth(h, BIN_PS, mode="gaussian"), 1000),
            ("ゲート重心 (3 op)", lambda: gated_centroid(h), 1000),
            ("tcspc_coates_correct", lambda: P.tcspc_coates_correct(h, 100000), 1000),
            ("dtof_cube_depth 32x32x256",
             lambda: P.dtof_cube_depth(cube, BIN_PS, mode="gaussian"), 100)):
        t0 = time.perf_counter()
        for _ in range(reps):
            fn()
        dt = 1e3 * (time.perf_counter() - t0) / reps
        timing[label] = dt
        print(f"  {label:<28}{dt:>9.4f} ms/回")
    per_px = 1e3 * timing["dtof_cube_depth 32x32x256"] / cube[..., 0].size
    print(f"  → 1 画素を 1 回測るのに {1e3 * timing['ゲート重心 (3 op)']:.1f} μs。")
    print(f"     立方体はベクトル化されていて 1 画素あたり {per_px:.2f} μs まで落ちる")
    print(f"     ({1e3 * timing['ゲート重心 (3 op)'] / per_px:.0f} 倍)。測距そのものが律速になる場面は無い。")

    # ------------------------------------------------------------------ #
    print("\n=== 8. 道具の穴(数字で示す)===")
    g_cube = P.dtof_cube_depth(cube, BIN_PS, mode="gaussian")
    p_cube = P.dtof_cube_depth(cube, BIN_PS, mode="peak")
    fell_back = int(np.sum(g_cube == p_cube))
    print(f"  (b) dtof_cube_depth(mode='gaussian') の出力のうち "
          f"{fell_back}/{g_cube.size} = {100.0 * fell_back / g_cube.size:.1f} % が")
    print("      mode='peak' と bit 一致 = サブビン当てはめを諦めて黙って落ちた画素。")
    print("      docstring には書いてあるが、戻り値にマスクが無いので実行時には")
    print("      観測できない。1 次元版 dtof_depth は同じ状況で例外を投げる ——")
    print("      兄弟 op で失敗方針が正反対。")
    print(f"  (a) 族が推す最良手 ガウス当てはめ {table2[0.0]['ガウス当てはめ']:.2f} mm に対し、")
    print(f"      利用者が 6 行で書くゲート重心 {table2[0.0]['ゲート重心']:.2f} mm。"
          f"族は自分の最良推定量を出荷していない。")

    # ---- 自己検査(速さは assert しない)---------------------------------- #
    # 1) ゼロ点に勝っていること。負けているなら、そう書くべきなのでここで落とす。
    assert table2[0.0]["ゲート重心"] < table2[0.0]["ピーク位置そのまま"] / 3.0, \
        "背景なしでゲート重心がピーク位置に 3 倍差をつけられていない"
    assert table2[6400.0]["ゲート重心"] < table2[6400.0]["重心そのまま"] / 50.0, \
        "背景ありでゲート重心が素の重心に 50 倍差をつけられていない"
    assert table2[6400.0]["ゲート重心"] < table2[6400.0]["重心+背景減算"] / 50.0, \
        "docstring が勧める背景減算より 50 倍良い、という主張が崩れている"
    # 2) 理論限界。1/√N の傾きと、CRB からの外れ幅。
    assert abs(slope + 0.5) < 0.03, f"1/√N に乗っていない (傾き {slope})"
    ratios = [g / c for g, c in zip(got, want)]
    assert max(ratios) < 1.15 and min(ratios) > 0.85, \
        f"ゲート重心が CRB から外れた (比 {min(ratios):.3f}〜{max(ratios):.3f})"
    # 3) ゼロ点は収束しない(ビン量子化バイアスが残る)。
    assert peak_rmse[-1] > 0.9e3 * BIN_M * 0.28, \
        "ピーク位置の誤差がビン量子化バイアスを下回った(ありえない)"
    assert abs(slope_peak) < 0.25, \
        f"ピーク位置が 1/√N 相当で改善している (傾き {slope_peak})"
    # 4) 背景光の破綻: RMSE が飛ぶ一方で中央値は飛ばない、という形。
    assert amb_rmse[51200.0] > 20.0 * amb_rmse[6400.0], \
        "背景光を 8 倍にしても RMSE が飛ばない(誤ロックが再現していない)"
    # 5) パイルアップ: 素の推定は必ず近く読み、Coates は残差 0.05 mm 未満。
    for mu, naive, fixed in pileup:
        assert naive <= 0.0, f"パイルアップで距離が遠く出た (mu={mu}, {naive} mm)"
        assert abs(fixed) < 0.05, f"Coates 後の残差が大きい (mu={mu}, {fixed} mm)"
    assert pileup[-1][1] < -20.0, "5 光子/サイクルでもバイアスが 20 mm に届かない"
    # 6) 多重反射: sep~σ でビン 1 個ぶん外し、光子を増やしても縮まない。
    assert mix_err[0.10] > 0.9e3 * BIN_M, "sep=0.10 m でビン 1 個ぶん外していない"
    assert mix_rmse[4800.0] > 0.9 * mix_rmse[300.0], \
        "多重反射の誤差が光子数で縮んだ(バイアスではなく雑音だったことになる)"
    # 7) 道具の穴 (b) が再現していること。
    assert fell_back > g_cube.size // 4, \
        "立方体のサブビン落ちが再現しない(穴 (b) の主張を撤回すべき)"
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
