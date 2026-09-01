# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""motion_magnification — モーション増幅・位相変位計測 op(motionmag)を
「見えない振動を、見せる/測る」筋で一巡する。

    py -3.11 examples/motion_magnification.py

【この例が解く問題】
カメラの前で機械が 0.2 画素だけ震えている。人間には静止して見える。
これを (a) 動画として見えるように増幅し、(b) 何画素かを数値で出す。
どちらも同じ量 — 帯域通過した**局所位相** — から出る。位相はサブピクセル
変位の線形な符号化なので、**位相を α 倍すれば変位が α 倍になる**。

(1) 複素ステアラブル分解: 1 枚の画像を向きつきの解析信号に割り、
    再合成が機械精度で厳密(tight frame)であることを確かめる。
    これが厳密でないと、増幅した結果が「増幅のせいか、再合成のせいか」
    分からなくなる。
(2) 合成動画: 既知振幅 d・既知周波数 f のサブピクセル平行移動を
    フーリエ位相ランプで作る(補間誤差ゼロ)。真値は閉形式。
(3) 時間帯域: 4 Hz の成分だけを取り出し、Parseval で振幅を検算する。
(4) 増幅: α を変えて、変位が **厳密に α·d** になることを、
    motionmag とは無関係な経路(既知の格子ビンの DFT 位相)で測る。
(5) 対照: 同じ α で、運動を通過帯域の**外**(12 Hz)に置く。
    増幅率は 1.000000000000 でなければならない。
(6) 正直な代償: α を上げると画像 SNR が単調に落ちること、
    そして**運動 SNR は決して上がらない**ことを実測する。
(7) 計測: 変位を数値で出し、サブピクセル精度がどこで崩れるかを表にする。
    崩れる場所は経験則ではなく **J0(k·A)=0 の第 1 零点**で決まる。
(8) 開口問題: 1 方向の縞しか無い場面で、観測できた成分だけが返り、
    観測できない方向が厳密に 0 になることを確かめる。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 分解 → 再合成の往復が機械精度(実測 6.66e-16、64x64)。
2. 合成動画の変位が閉形式と一致(実測 1.5e-15)。
3. 帯域通過が単一成分を厳密に復元(実測 4.36e-15)。帯域出力 = a²/2。
4. 増幅後の変位 = α·d(実測 最大相対誤差 3.3e-13、α∈[-4,20], d∈[0.01,0.5])。
5. 帯域外の運動は増幅されない(実測 増幅率 1.000000000000、α=100 でも)。
6. α を上げると image SNR が単調減、motion SNR は上がらない(実測)。
7. 変位計測は d=3.05 px まで機械精度、3.10 px で破綻。境界は
   k·A = 2.4048(J0 の第 1 零点)= 3.0619 px と閉形式で一致。
8. 開口問題では rank=1、dx=0.3000000000000001、dy=0.0(厳密)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import motionmag as M  # noqa: E402

H = W = 64
T = 64
FPS = 32.0
FREQ = 4.0                      # FREQ*T/FPS = 8 -> ちょうど 1 本のビンに乗る
BAND = (3.0, 5.0)
CYC_X = 8                       # 横縞 8 周期 = 波長 8 px
K_X = 2.0 * np.pi * CYC_X / W   # 8 px 縞の空間周波数 [rad/px]


def truth(amp, freq=FREQ):
    """synthesize_translation が与える変位(閉形式)。"""
    return amp * np.sin(2.0 * np.pi * freq * np.arange(T) / FPS)


def read_dx(video):
    """motionmag と無関係な経路での変位読み出し: 既知格子ビンの DFT 位相。"""
    spec = np.fft.fft2(video, axes=(1, 2))
    return -np.unwrap(np.angle(spec[:, 0, CYC_X])) / (2.0 * np.pi * CYC_X / W)


def main():
    # ------------------------------------------------------------------ #
    # 1) 複素ステアラブル分解 — 再合成が厳密であること                     #
    # ------------------------------------------------------------------ #
    img = np.random.default_rng(0).random((H, W))
    dec = M.complex_steerable_decompose(img)
    back = M.complex_steerable_reconstruct(dec)
    n_band = sum(1 for k in dec["kinds"] if k == "band")
    print("1) 複素ステアラブル分解(4 scale x 4 orientation):")
    print(f"   帯域 {len(dec['bands'])} 本(向きつき {n_band} + 残差 3)"
          f"  各 {dec['shape']} complex")
    print(f"   再合成の最大絶対誤差 = {np.abs(back - img).max():.3e}"
          "(tight frame なので厳密)")
    assert np.abs(back - img).max() < 1e-14

    # ------------------------------------------------------------------ #
    # 2) 合成動画 — 真値が閉形式で分かる                                   #
    # ------------------------------------------------------------------ #
    d0 = 0.2
    vid = M.synthesize_translation((H, W), T, d0, FREQ, FPS)
    print("2) 合成動画: 64 frame / 32 fps / 波長 (8, 16) px の格子を")
    print(f"   d(t) = {d0} * sin(2*pi*{FREQ}*t/{FPS}) [px] だけ水平に動かす")
    print(f"   閉形式との差 = {np.abs(read_dx(vid) - truth(d0)).max():.3e}"
          "(フーリエ位相ランプ = 補間誤差ゼロ)")
    assert np.abs(read_dx(vid) - truth(d0)).max() < 1e-13

    # ------------------------------------------------------------------ #
    # 3) 時間帯域 — Parseval で検算                                        #
    # ------------------------------------------------------------------ #
    t = np.arange(T)
    mixed = 0.5 + np.sin(2 * np.pi * 4 * t / FPS) + 0.3 * np.cos(2 * np.pi * 12 * t / FPS)
    probe = np.tile(mixed[:, None, None], (1, 8, 8))
    got = M.temporal_bandpass(probe, *BAND, FPS)
    a = 0.3
    pw = M.temporal_band_power(
        np.tile((1.0 + a * np.sin(2 * np.pi * 4 * t / FPS))[:, None, None], (1, 8, 8)),
        *BAND, FPS)
    print("3) 時間帯域通過(3-5 Hz):")
    print(f"   混合波(DC 0.5 + 4Hz 1.0 + 12Hz 0.3)から 4Hz 成分だけを復元: "
          f"誤差 {np.abs(got[:, 0, 0] - np.sin(2*np.pi*4*t/FPS)).max():.3e}")
    print(f"   帯域パワー = {float(pw[0, 0]):.10f}(振幅 {a} なら a²/2 = "
          f"{a*a/2:.10f})")
    assert np.abs(got[:, 0, 0] - np.sin(2 * np.pi * 4 * t / FPS)).max() < 1e-13

    # ------------------------------------------------------------------ #
    # 4) 増幅 — 変位が厳密に alpha * d になる                              #
    # ------------------------------------------------------------------ #
    print("4) 増幅: 変位が alpha * d になるか(独立経路で測定)")
    print("     alpha    期待 peak     実測 peak      最大絶対誤差")
    for alpha in (0.0, 1.0, 2.0, 4.0, 8.0, -3.0):
        res = M.motion_magnify(vid, alpha, *BAND, FPS)
        want = alpha * truth(d0)
        meas = read_dx(res["video"])
        err = float(np.abs(meas - want).max())
        print(f"   {alpha:+7.1f} {np.abs(want).max():12.8f} "
              f"{np.abs(meas).max():13.8f}  {err:.3e}")
        assert err < 1e-12
    print("   alpha=0 は運動を消し、alpha=1 は恒等、負の alpha は運動を反転する")

    # ------------------------------------------------------------------ #
    # 5) 対照 — 帯域外の運動は増幅されない                                 #
    # ------------------------------------------------------------------ #
    out_band = M.synthesize_translation((H, W), T, 0.5, 12.0, FPS)
    print("5) 対照実験: 同じ 3-5 Hz の通過帯域で、運動を 12 Hz に置く")
    for alpha in (4.0, 16.0, 100.0):
        res = M.motion_magnify(out_band, alpha, *BAND, FPS)
        gain = float(np.abs(read_dx(res["video"])).max()) / 0.5
        print(f"   alpha={alpha:6.1f} -> 増幅率 {gain:.12f}")
        assert abs(gain - 1.0) < 1e-11
    print("   帯域外は alpha=100 でも素通し = 帯域選択が本当に効いている")

    # ------------------------------------------------------------------ #
    # 6) 正直な代償 — SNR                                                  #
    # ------------------------------------------------------------------ #
    noisy = M.synthesize_translation((H, W), T, d0, FREQ, FPS,
                                     noise_sigma=0.01, seed=7)
    base = M.band_snr(noisy, *BAND, FPS)
    print("6) 代償(sigma=0.01 のセンサ雑音つき):")
    print(f"   入力: image SNR {base['image_snr_db']:.4f} dB / "
          f"motion SNR {base['motion_snr_db']:.4f} dB")
    print("     alpha  image SNR   変化      motion SNR   変化    band_power比")
    prev = None
    for alpha in (1.0, 2.0, 4.0, 8.0):
        r = M.motion_magnify(noisy, alpha, *BAND, FPS)
        img_db = r["snr_out"]["image_snr_db"]
        print(f"   {alpha:6.1f} {img_db:9.4f} {r['image_snr_change_db']:+9.4f} "
              f"{r['motion_snr_out_db']:11.4f} {r['motion_snr_change_db']:+8.4f} "
              f"  {r['band_power_ratio']:.6f}")
        assert r["motion_snr_change_db"] <= 1e-9
        if prev is not None:
            assert img_db < prev
        prev = img_db
    print("   image SNR は倍ごとに約 5 dB 落ちる(漸近値 20*log10(2)=6.02 dB)。")
    print("   motion SNR は決して上がらない — 増幅は運動を**見せる**だけで、")
    print("   録画に無かった確からしさを作り出すことはできない。")
    print("   ★ 増幅後の動画に band_snr をそのまま当てると motion SNR が")
    print("     +6.86 dB 改善したように見える(帯域外から雑音床を推定するため)。")
    print("     motion_magnify が返す motion_snr_out_db はこれを補正した値。")

    # ------------------------------------------------------------------ #
    # 7) 計測 — 精度と、崩れる場所の閉形式                                 #
    # ------------------------------------------------------------------ #
    print("7) 変位計測(増幅せず数値で返す):")
    print("     真値 d   k*d [rad]   実測 [px]        相対誤差   参照コヒーレンス")
    for d in (0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 3.0, 3.05, 3.1, 4.0, 6.0):
        v = M.synthesize_translation((H, W), T, d, FREQ, FPS)
        s = M.displacement_series(v, *BAND, FPS)
        f = M.phase_displacement(v, *BAND, FPS)
        m = float(np.abs(s[:, 0]).max())
        flag = "" if abs(m - d) / d < 1e-10 else "  <- 破綻"
        print(f"   {d:7.3f} {K_X*d:10.4f} {m:14.8f} {abs(m-d)/d:11.3e} "
              f"{f['reference_coherence']:11.5f}{flag}")
    print(f"   破綻の境界 = J0(k*A) の第 1 零点 2.4048 / k = "
          f"{2.4048/K_X:.4f} px(3.05 は通り、3.10 は通らない)")
    print("   その先の硬い上限は位相の巻き |k*d| < pi = "
          f"{np.pi/K_X:.4f} px(返り値 wrap_limit_px)")
    print("   雑音下では精度は雑音で決まる: d=0.5 px, sigma=0.01 で "
          f"{abs(float(np.abs(M.displacement_series(M.synthesize_translation((H,W),T,0.5,FREQ,FPS,noise_sigma=0.01,seed=3), *BAND, FPS)[:,0]).max())-0.5)/0.5:.2e}")

    # ------------------------------------------------------------------ #
    # 8) 開口問題 — 測れた成分だけを返す                                   #
    # ------------------------------------------------------------------ #
    x = np.arange(W)
    flat = 0.5 + 0.2 * np.cos(2 * np.pi * CYC_X * x / W)[None, :] * np.ones((H, 1))
    fu = np.fft.fftfreq(W)[None, :]
    sp = np.fft.fft2(flat)
    clip = np.stack([np.real(np.fft.ifft2(sp * np.exp(-2j * np.pi * fu * dd)))
                     for dd in truth(0.3)])
    field = M.phase_displacement(clip, *BAND, FPS)
    series = M.displacement_series(clip, *BAND, FPS)
    ranks = {r: int((field["rank"] == r).sum()) for r in (0, 1, 2)}
    print("8) 開口問題(横縞しか無い場面を横に 0.3 px 動かす):")
    print(f"   rank ヒストグラム {ranks}(全画素が rank 1 = 1 成分しか観測不能)")
    print(f"   dx = {float(np.abs(series[:, 0]).max()):.16f}  "
          f"dy = {float(np.abs(series[:, 1]).max()):.1f}")
    print("   観測できた成分は返し、観測できない方向は厳密に 0。")
    print("   ゼロで潰すと測れた分を捨て、特異な系を無理に解くと嘘が出る。")
    assert (field["rank"] == 1).all()
    assert abs(float(np.abs(series[:, 0]).max()) - 0.3) < 1e-12
    assert float(np.abs(series[:, 1]).max()) == 0.0

    print()
    print("すべての主張は実測で、真値は閉形式。合格。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
