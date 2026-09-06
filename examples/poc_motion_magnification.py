# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""構造物の微小振動を映像から測る —— モーション拡大は「測る」役に立つのか。

EXTEND: 実際の構造物映像に差し替えるなら、合成クリップを作っている
``make_clip`` を「読み込んだフレーム列を ``(T, H, W)`` float64 に積む」処理に
置き換える。そのとき効いてくるのは道具ではなく撮り方で、順に:

* **三脚は必須**。ここで測っている量は 0.02 画素 = 1/50 画素である。手持ちの
  カメラは容易にその 100 倍揺れるので、被写体の振動は完全に埋もれる。三脚に
  載せ、シャッターは有線かセルフタイマーで切り、床の振動を拾わない位置に置く。
  照明のちらつき(商用電源 50/60 Hz とその分周)は輝度の周期変動として乗り、
  帯域が重なると振動と区別できないので直流点灯にする。
* **それでも残るカメラ揺れは引き算する**。画面内に「絶対に動かないと分かって
  いる物」(地面に固定した治具、遠景の構造物)を一緒に写し込み、そのブロックの
  変位を ``phase_displacement`` で測って被写体の変位から引く。この PoC の第 2 章
  が示すとおり、位相相関も位相計測も**視野全体の剛体運動と被写体の振動を区別
  しない**ので、参照ブロックを写し込んでおくこと自体が唯一の分離手段になる。
  参照が無い映像は後処理では救えない。
* **スケール(px→mm)は撮影時に決める**。被写体面に既知寸法のターゲット(校正
  板、スケールバー)を**振動する面と同じ距離**に置いて 1 枚撮り、
  ``mm_per_px = 既知長さ_mm / 測った長さ_px`` を出す。焦点距離とワーキング
  ディスタンスから計算しても良いが、レンズの歪曲と主点のずれで数 % 外す。
  面が光軸に対して傾いていると倍率が画面内で変わるので、その場合は
  ``calib`` 族のホモグラフィで平面に正対させてから測る。斜め撮影のまま
  一定の ``mm_per_px`` を掛けるのが一番よくある間違い。

この PoC が示すこと:

1. **拡大率どおりか** —— 既知振幅 0.02 / 0.1 / 0.5 px、既知周波数 3.7 Hz の
   振動を合成し、拡大後の変位が厳密に α·d になるかを、motionmag と無関係な
   経路(既知の格子ビンの DFT 位相)で読んで突き合わせる。
2. **ゼロ点を置く** —— 「拡大しない生の映像から位相相関で測る」を対照に置く。
   **結論は正直に言って「拡大は測定の役に立たない」**。無雑音では両者とも
   1e-15、雑音下でも(しきい値をまともに選べば)位相相関は位相計測に並ぶ。
   拡大してから測って α で割っても誤差は縮まない —— 位相を α 倍すると
   帯域内の雑音も同じ α 倍されるからで、これは実装の質ではなく原理。
   拡大は**人間に見せるため**の道具である。
   ただし位相計測が原理的に勝つ場面が 2 つある: (a) 位相相関のしきい値を外すと
   1 桁誤るのに対し位相計測にはそのノブが無い、(b) 運動が視野内で**空間的に
   変わる**場合、位相相関は「剛体変位ひとつ」しか返せず、片持ち梁の実測では
   0.30 px と 0.00 px の平均 0.15 px という**どこにも存在しない数**を返す。
3. **周波数の選択性はクリップ長で決まる** —— 3.7 Hz が DFT ビンに乗るとき
   帯域外応答は -293 dB、乗らないとき隣の帯域が -3.3 dB しか落ちない。
   時間帯域通過は理想ブリックウォールなので、選択性を壊すのはフィルタでは
   なく「T·f/fps を整数にしなかったこと」。
4. **壊れる境界を数字で** —— 拡大の線形性は位相増分 (α-1)·k·d が π に届く
   ところで崩れる。振幅を振って表にした。

★ この PoC が出した道具の穴は末尾の「道具の穴」節にまとめてある。

    py -3.11 examples/poc_motion_magnification.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import motionmag as M  # noqa: E402

# --------------------------------------------------------------------------- #
# 実験の設定                                                                    #
# --------------------------------------------------------------------------- #
H = W = 64                  # 関心領域(ROI)。振動を測るのは画角全体ではない
T = 100                     # フレーム数
FPS = 37.0                  # 3.7 Hz が T*f/fps = 10 でちょうどビンに乗る
FREQ = 3.7                  # 構造物の共振周波数 [Hz]
BAND = (3.0, 4.5)           # 通過帯域 [Hz]
LAM_X, LAM_Y = 8.0, 16.0    # 表面テクスチャの縞波長 [px](別オクターブにする)
CYC_X = int(round(W / LAM_X))          # 横方向 8 周期
K_X = 2.0 * np.pi * CYC_X / W          # = 0.7854 rad/px
CONTRAST = 0.4

AMPS = (0.02, 0.1, 0.5)     # 課題が指定する既知振幅 [px]


def surface(h=H, w=W, lam_x=LAM_X, lam_y=LAM_Y, contrast=CONTRAST, offset=0.5):
    """構造物表面のテクスチャ。2 軸の格子で、2 軸は別オクターブに置く。

    同じ波長にすると横縞と縦縞が同じ副帯域に落ち、局所位相が「2 成分の和の
    位相」になって変位に線形でなくなる(motionmag 側の docstring が実測 6.1 %
    の誤差として記録している条件)。"""
    cx = max(1, int(round(w / lam_x)))
    cy = max(1, int(round(h / lam_y)))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    return offset + 0.5 * contrast * (np.cos(2.0 * np.pi * cx * xx / w)
                                      + np.cos(2.0 * np.pi * cy * yy / h))


def translate(base, dx_series, dy_series=None):
    """フーリエ位相ランプによる厳密な平行移動 -> ``(T, H, W)``。

    格子は格子上で周期的なので、位相ランプは**補間誤差ゼロ**の帯域制限
    シフトそのもの。したがって与えた ``dx_series`` が機械精度で真値になる。
    ``synthesize_translation`` と同じ手口で、任意の変位波形を与えられる点だけ
    が違う(複数成分を重ねるのにいる)。"""
    dx_series = np.asarray(dx_series, np.float64)
    if dy_series is None:
        dy_series = np.zeros_like(dx_series)
    h, w = base.shape
    fv = np.fft.fftfreq(h)[:, None]
    fu = np.fft.fftfreq(w)[None, :]
    spec = np.fft.fft2(base)
    out = np.empty((dx_series.size, h, w), np.float64)
    for i, (dx, dy) in enumerate(zip(dx_series, dy_series)):
        out[i] = np.real(np.fft.ifft2(spec * np.exp(-2j * np.pi * (fu * dx + fv * dy))))
    return out


def waveform(amp, freq=FREQ, t=T, fps=FPS, phase=0.0):
    """振動の真値波形 d(t) [px]。"""
    return amp * np.sin(2.0 * np.pi * freq * np.arange(t) / fps + phase)


def make_clip(components, t=T, noise_sigma=0.0, seed=0, base=None):
    """成分 (振幅 px, 周波数 Hz, 位相 rad) の重ね合わせで揺れるクリップ。"""
    base = surface() if base is None else base
    d = np.zeros(t)
    for amp, freq, phase in components:
        d = d + waveform(amp, freq, t, FPS, phase)
    vid = translate(base, d)
    if noise_sigma > 0.0:
        vid = vid + np.random.default_rng(seed).normal(0.0, noise_sigma, vid.shape)
    return vid, d


# --------------------------------------------------------------------------- #
# motionmag と無関係な 2 つの読み出し経路                                        #
# --------------------------------------------------------------------------- #
def read_dx_oracle(video):
    """既知の格子ビンの DFT 位相から変位を読む -> ``(T,)`` px。

    格子の周期数 CYC_X を**知っている**前提の読み出しなので、増幅の検算には
    使えるが計測手法の対照にはならない(第 2 章のゼロ点は別に用意する)。
    時間方向に unwrap するので、フレーム間の位相増分が π を超えると壊れる。"""
    spec = np.fft.fft2(np.asarray(video, np.float64), axes=(1, 2))
    return -np.unwrap(np.angle(spec[:, 0, CYC_X])) / K_X


def phase_correlation_series(video, keep_frac=0.05, ref=0):
    """ゼロ点: 生映像から位相相関でフレームごとの剛体変位 -> ``(T, 2)`` px。

    フレーム ``ref`` との交差パワースペクトル ``F_t conj(F_ref)`` の位相は
    平行移動 (dx, dy) に対して ``-2 pi (u dx + v dy)`` の平面になる。強度の
    大きいビンだけを残し、``|F_ref|^2`` を重みにした最小二乗でその平面の傾きを
    解く —— サブピクセル位相相関の素直な実装で、拡大も帯域通過も使わない。

    ``keep_frac`` は「どのビンを信じるか」のしきい値(``|F_ref|`` の最大値に
    対する比)。**この値が結果を左右する**ことは第 2 章で表にした。"""
    v = np.asarray(video, np.float64)
    t, h, w = v.shape
    spec = np.fft.fft2(v, axes=(1, 2))
    ref_spec = spec[ref]
    mag = np.abs(ref_spec).copy()
    mag[0, 0] = 0.0                       # DC は変位の情報を持たない
    keep = mag > keep_frac * mag.max()
    if keep.sum() < 2:
        raise ValueError("phase_correlation_series: 残ったビンが %d 本しかない"
                         % int(keep.sum()))
    fv = np.fft.fftfreq(h)[:, None] * np.ones((1, w))
    fu = np.ones((h, 1)) * np.fft.fftfreq(w)[None, :]
    u, vv = fu[keep], fv[keep]
    wgt = mag[keep] ** 2
    a00 = float((wgt * u * u).sum())
    a01 = float((wgt * u * vv).sum())
    a11 = float((wgt * vv * vv).sum())
    det = a00 * a11 - a01 * a01
    out = np.zeros((t, 2))
    for i in range(t):
        ph = np.angle(spec[i] * np.conj(ref_spec))[keep]
        b0 = -float((wgt * u * ph).sum()) / (2.0 * np.pi)
        b1 = -float((wgt * vv * ph).sum()) / (2.0 * np.pi)
        out[i, 0] = (a11 * b0 - a01 * b1) / det
        out[i, 1] = (a00 * b1 - a01 * b0) / det
    return out


def temporal_band(series, lo=BAND[0], hi=BAND[1], fps=FPS):
    """1-D 系列の理想帯域通過。ゼロ点に同じ帯域選択を与えるための対照。"""
    x = np.asarray(series, np.float64)
    n = x.shape[0]
    f = np.fft.fftfreq(n, d=1.0 / fps)
    m = (np.abs(f) >= lo) & (np.abs(f) <= hi)
    m[0] = False
    s = np.fft.fft(x, axis=0)
    s[~m] = 0.0
    return np.real(np.fft.ifft(s, axis=0))


def amp_rms(x):
    """正弦の振幅を RMS 経由で推定。尖頭値より雑音とリンギングに強い。"""
    return float(np.sqrt(2.0) * np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)))


def amp_peak(x):
    return float(np.abs(np.asarray(x, np.float64)).max())


def rel(measured, truth):
    return abs(measured - truth) / abs(truth) if truth else abs(measured)


# --------------------------------------------------------------------------- #
def main():
    print("=== 0. 設定と、真値生成器そのものの検算 ===")
    print(f"  ROI {H}x{W} px / {T} frame / {FPS:g} fps / 共振 {FREQ:g} Hz")
    print(f"  3.7 Hz は DFT ビン {FREQ*T/FPS:.2f} 番(整数 = ビンに乗る)"
          f" / ビン間隔 {FPS/T:.4f} Hz")
    print(f"  表面テクスチャ 縞波長 ({LAM_X:g}, {LAM_Y:g}) px / "
          f"k_x = {K_X:.6f} rad/px / 位相巻き上限 pi/k = {np.pi/K_X:.4f} px")
    print(f"  通過帯域 {BAND[0]:g}-{BAND[1]:g} Hz")
    ref_clip = M.synthesize_translation((H, W), T, 0.1, FREQ, FPS,
                                        wavelength_px=(LAM_X, LAM_Y),
                                        contrast=CONTRAST)
    mine, _d = make_clip([(0.1, FREQ, 0.0)])
    print(f"  自作 translate と synthesize_translation の差 = "
          f"{np.abs(mine - ref_clip).max():.3e}(同じ位相ランプ = 完全一致)")
    print(f"  与えた変位と oracle 読み出しの差 = "
          f"{np.abs(read_dx_oracle(mine) - waveform(0.1)).max():.3e} px")

    # ---------------------------------------------------------------- #
    print("\n=== 1. 拡大率どおりか(振幅 x 拡大率)===")
    print("  実測は motionmag と無関係な経路(既知格子ビンの DFT 位相)で読む。")
    print(f"  {'真の d px':>10}{'alpha':>7}{'期待 a*d px':>13}"
          f"{'実測 px':>13}{'実測/期待':>12}{'band_power比':>13}")
    ratios = []
    for d0 in AMPS:
        vid, _ = make_clip([(d0, FREQ, 0.0)])
        for alpha in (1.0, 2.0, 5.0, 10.0, 25.0):
            r = M.motion_magnify(vid, alpha, *BAND, FPS)
            meas = amp_peak(read_dx_oracle(r["video"]))
            want = alpha * d0
            ratios.append(meas / want)
            print(f"  {d0:>10.2f}{alpha:>7.0f}{want:>13.4f}"
                  f"{meas:>13.6f}{meas/want:>12.8f}{r['band_power_ratio']:>13.6f}")
    print("  → 0.02 px を 25 倍しても比は 1.000000 台。拡大は変位に対して線形。")
    print("     band_power 比が 1 から落ちるところが非線形の入口(第 4 章)。")

    # ---------------------------------------------------------------- #
    print("\n=== 2. ゼロ点 —— 拡大しない生映像を位相相関で測る ===")
    print("  2a) 無雑音・単一周波数。両者とも真値に機械精度で一致する。")
    print(f"  {'真の d px':>10}{'位相相関(ゼロ点)':>20}{'相対誤差':>12}"
          f"{'位相計測':>14}{'相対誤差':>12}")
    for d0 in AMPS:
        vid, _ = make_clip([(d0, FREQ, 0.0)])
        pc = phase_correlation_series(vid)[:, 0]
        ps = M.displacement_series(vid, *BAND, FPS)[:, 0]
        print(f"  {d0:>10.2f}{amp_rms(pc):>20.10f}{rel(amp_rms(pc), d0):>12.2e}"
              f"{amp_rms(ps):>14.10f}{rel(amp_rms(ps), d0):>12.2e}")
    print("  → 引き分け。拡大を通していない生映像で 0.02 px が 1e-14 で出る。")

    print("\n  2b) 雑音を入れる。d = 0.1 px 固定。4 経路を並べる。")
    print("      (i) 位相相関 / (ii) 位相相関 + 同じ時間帯域通過 /")
    print("      (iii) 位相計測 / (iv) 10 倍に拡大してから測って 10 で割る")
    print(f"  {'sigma':>8}{'(i) 生':>12}{'(ii) +帯域':>13}{'(iii) 位相計測':>16}"
          f"{'(iv) 拡大後/10':>16}")
    d0 = 0.1
    for sigma in (0.0, 0.001, 0.01, 0.05):
        vid, _ = make_clip([(d0, FREQ, 0.0)], noise_sigma=sigma, seed=11)
        pc = phase_correlation_series(vid)[:, 0]
        pcb = temporal_band(pc)
        ps = M.displacement_series(vid, *BAND, FPS)[:, 0]
        mg = M.motion_magnify(vid, 10.0, *BAND, FPS)["video"]
        pm = M.displacement_series(mg, *BAND, FPS)[:, 0] / 10.0
        print(f"  {sigma:>8.3f}{amp_rms(pc):>12.6f}{amp_rms(pcb):>13.6f}"
              f"{amp_rms(ps):>16.6f}{amp_rms(pm):>16.6f}")
    print("  → (iii) と (iv) はほぼ同じ数字。**拡大しても測定は良くならない**。")
    print("     帯域内の位相を alpha 倍すると帯域内の雑音も同じ alpha 倍される。")
    print("     motion_magnify 自身が motion_snr_change_db <= 0 として同じことを")
    print("     返しており、この PoC はそれを変位の側から独立に確かめた。")

    print("\n  2c) ゼロ点のしきい値感度。位相相関は keep_frac を外すと 1 桁誤る。")
    print(f"  {'sigma':>8}" + "".join(f"{f'keep={f:g}':>13}"
                                      for f in (0.001, 0.01, 0.05, 0.15))
          + f"{'位相計測':>14}")
    for sigma in (0.01, 0.05, 0.2):
        vid, _ = make_clip([(d0, FREQ, 0.0)], noise_sigma=sigma, seed=11)
        cells = []
        for frac in (0.001, 0.01, 0.05, 0.15):
            cells.append(amp_rms(phase_correlation_series(vid, keep_frac=frac)[:, 0]))
        ps = amp_rms(M.displacement_series(vid, *BAND, FPS)[:, 0])
        print(f"  {sigma:>8.3f}" + "".join(f"{c:>13.6f}" for c in cells)
              + f"{ps:>14.6f}")
    print("  → 真値は 0.100000。しきい値を低くすると雑音ビンの巻いた位相が")
    print("     最小二乗を 0 側に引き、sigma=0.2 では 1/7 に潰れる。位相計測に")
    print("     同じ役目のノブは無い(副帯域の振幅重みが自動でそれをやる)。")
    print("     ゼロ点が勝つのは「しきい値を正しく選べたとき」だけである。")

    print("\n  2d) ゼロ点が原理的に答えられない場合 —— 運動が空間で変わる")
    base = surface()
    xx = np.arange(W)[None, :] * np.ones((H, 1))
    win = 1.0 / (1.0 + np.exp((xx - W * 0.5) / 1.5))     # 左 1 / 右 0
    moving = translate(base, waveform(0.30))
    fixed = np.repeat(base[None], T, axis=0)
    vid = win[None] * moving + (1.0 - win)[None] * fixed
    field = M.phase_displacement(vid, *BAND, FPS)
    dxf = field["dx"]
    prof = np.array([amp_rms(dxf[:, H // 2, c]) for c in range(W)])
    pc = amp_rms(phase_correlation_series(vid)[:, 0])
    print("      片持ち梁: 左半分が 0.30 px で振動、右半分(固定端)は 0.00 px")
    print(f"      位相計測の列プロファイル(8 列おき、行 {H//2}):")
    print("        " + " ".join(f"{v:.3f}" for v in prof[::8]))
    print(f"      自由端側 (列 10) = {prof[10]:.5f} px(真 0.30)/ "
          f"固定端側 (列 {W-10}) = {prof[W-10]:.5f} px(真 0.00)")
    print(f"      ゼロ点(剛体を仮定する位相相関)= {pc:.5f} px")
    print("      → 0.30 と 0.00 の面積平均。**どこにも存在しない値**を 1 つ返す。")
    print("         振動モード形状が要るなら位相相関では原理的に届かない。")
    print("      注: 列 0 は FFT の周回境界で右端と隣接するため境界値になる。")

    print("\n  【第 2 章の結論(正直版)】")
    print("   ・拡大は測定精度を良くしない。0.02 px は生映像から直接測れる。")
    print("   ・雑音下で位相計測が勝って見えるのはしきい値の話で、ゼロ点を")
    print("     まともに調律すれば並ぶ。拡大の寄与はどちらでもゼロ。")
    print("   ・位相計測が本当に買っているのは精度ではなく (a) ノブの少なさと")
    print("     (b) 画素ごとの変位場。拡大が買っているのは**人間の目**だけ。")

    # ---------------------------------------------------------------- #
    print("\n=== 3. 周波数の選択性と漏話 ===")
    print("  帯域幅 1.5 Hz を固定して中心をずらす。真の振動は 3.7 Hz / 0.1 px。")
    for t_len in (100, 105):
        cyc = FREQ * t_len / FPS
        tag = "ビンに乗る" if abs(cyc - round(cyc)) < 1e-9 else "ビンから外れる"
        print(f"\n  T={t_len} frame: 3.7 Hz = {cyc:.2f} bin({tag})"
              f" / ビン間隔 {FPS/t_len:.4f} Hz")
        vid, _ = make_clip([(0.1, FREQ, 0.0)], t=t_len)
        print(f"    {'帯域 Hz':>14}{'復元振幅 px':>14}{'相対応答 dB':>14}")
        for centre in (3.70, 4.45, 5.20, 6.00, 7.40, 2.20):
            lo, hi = centre - 0.75, centre + 0.75
            a = amp_rms(M.displacement_series(vid, lo, hi, FPS)[:, 0])
            db = 20.0 * np.log10(max(a, 1e-18) / 0.1)
            mark = "  <- 真の成分を含む帯域" if lo <= FREQ <= hi else ""
            print(f"    {f'{lo:.2f}-{hi:.2f}':>14}{a:>14.8f}{db:>14.2f}{mark}")
        # 漏話: 無関係な 6.5 Hz / 0.4 px を同時に振らせる
        vid2, _ = make_clip([(0.1, FREQ, 0.0), (0.4, 6.5, 0.7)], t=t_len)
        a37 = amp_rms(M.displacement_series(vid2, *BAND, FPS)[:, 0])
        a65 = amp_rms(M.displacement_series(vid2, 5.9, 7.1, FPS)[:, 0])
        leak = abs(a37 - 0.1)
        print(f"    漏話試験(3.7 Hz 0.1 px と 6.5 Hz 0.4 px を同時に):")
        print(f"      3.7 Hz 帯 {a37:.8f} px(真 0.10)/ "
              f"6.5 Hz 帯 {a65:.8f} px(真 0.40)")
        print(f"      6.5 成分の 3.7 帯への漏れ = {leak:.3e} px = "
              f"{20*np.log10(max(leak,1e-18)/0.4):.1f} dB")
    print("\n  → 時間帯域通過は理想ブリックウォールなので、ビンに乗っていれば")
    print("     帯域外は -290 dB(丸め)まで落ちる。落ちなくなる原因はフィルタ")
    print("     ではなく**クリップ長**で、T*f/fps が整数から外れると漏れが出る。")
    print("     実運用の作法: 共振周波数の見当をつけてから T と fps を選ぶ。")

    print("\n  3d) オフビンのとき、振幅を尖頭値で読むか RMS で読むかで答えが違う")
    print(f"    {'T':>6}{'尖頭値 px':>13}{'誤差':>10}{'RMS 換算 px':>14}{'誤差':>10}")
    for t_len in (100, 105):
        vid, _ = make_clip([(0.1, FREQ, 0.0)], t=t_len)
        s = M.displacement_series(vid, *BAND, FPS)[:, 0]
        pk, rm = amp_peak(s), amp_rms(s)
        print(f"    {t_len:>6}{pk:>13.6f}{100*rel(pk,0.1):>9.1f}%"
              f"{rm:>14.6f}{100*rel(rm,0.1):>9.1f}%")
    print("    → ブリックウォールのリンギングは尖頭値を持ち上げる。オフビンでは")
    print("       尖頭値が +16 % 高く出る一方 RMS 換算は -2.4 % に収まる。")
    print("       正弦の振幅は RMS から読むこと(尖頭値は雑音の 1 発でも動く)。")

    # ---------------------------------------------------------------- #
    print("\n=== 4. 壊れる条件 ===")
    print("  4a) 拡大の線形性。alpha=5 固定で振幅を振る。")
    print("      理屈: 加える位相増分は (alpha-1)*k*d。これが pi に届くと巻く。")
    print(f"      k = {K_X:.4f} rad/px なので境界は d = pi/((5-1)*k) = "
          f"{np.pi/(4*K_X):.4f} px")
    print(f"    {'d px':>9}{'(a-1)k d rad':>15}{'期待 5d px':>13}{'実測 px':>13}"
          f"{'実測/期待':>12}{'band_power比':>13}")
    alpha = 5.0
    lin = {}
    for d0 in (0.001, 0.01, 0.05, 0.1, 0.2, 0.4, 0.8, 1.0, 1.2):
        vid, _ = make_clip([(d0, FREQ, 0.0)])
        r = M.motion_magnify(vid, alpha, *BAND, FPS)
        meas = amp_peak(read_dx_oracle(r["video"]))
        lin[d0] = meas / (alpha * d0)
        flag = "" if abs(lin[d0] - 1.0) < 0.01 else "  <- 1 % 超の逸脱"
        print(f"    {d0:>9.3f}{(alpha-1)*K_X*d0:>15.4f}{alpha*d0:>13.4f}"
              f"{meas:>13.6f}{lin[d0]:>12.6f}{r['band_power_ratio']:>13.6f}"
              f"{flag}")
    print("    → 0.001 px から 0.4 px まで比は 1.0000。0.8 px を超えると崩れ、")
    print("       位相増分が pi に届く 1.0 px 付近で完全に外れる。閉形式どおり。")
    print("    注: この表の実測は時間方向 unwrap を使うので、拡大後の振幅が")
    print(f"       {np.pi/(K_X*2*np.pi*FREQ/FPS):.2f} px を超えると読み出し側が先に壊れる"
          "(表の範囲は内側)。")

    print("\n  4b) 拡大率を振る。d = 0.1 px 固定。")
    print(f"    {'alpha':>8}{'(a-1)k d rad':>15}{'実測/期待':>12}"
          f"{'band_power比':>13}{'位相増分RMS rad':>17}{'linear':>8}")
    d0 = 0.1
    vid, _ = make_clip([(d0, FREQ, 0.0)])
    for alpha in (2.0, 5.0, 10.0, 20.0, 40.0, 60.0):
        r = M.motion_magnify(vid, alpha, *BAND, FPS)
        meas = amp_peak(read_dx_oracle(r["video"]))
        print(f"    {alpha:>8.0f}{(alpha-1)*K_X*d0:>15.4f}"
              f"{meas/(alpha*d0):>12.6f}{r['band_power_ratio']:>13.6f}"
              f"{r['phase_shift_rms_rad']:>17.4f}{str(r['linear_regime']):>8}")
    print("    → alpha*d の積だけで決まる。0.1 px なら alpha=40 が境界")
    print(f"       (pi/(k*d) + 1 = {np.pi/(K_X*d0)+1:.1f})。振幅と拡大率は")
    print("       独立なノブではない。")

    print("\n  4c) 雑音。振幅が小さいほど早く壊れる。")
    print(f"    {'sigma':>8}" + "".join(f"{f'd={a:g}px':>14}" for a in AMPS))
    for sigma in (0.0, 0.001, 0.01, 0.05, 0.2):
        cells = []
        for d0 in AMPS:
            v, _ = make_clip([(d0, FREQ, 0.0)], noise_sigma=sigma, seed=5)
            cells.append(rel(amp_rms(M.displacement_series(v, *BAND, FPS)[:, 0]), d0))
        print(f"    {sigma:>8.3f}" + "".join(f"{100*c:>13.2f}%" for c in cells))
    print("    → 相対誤差。0.5 px は sigma=0.2 でも 1 % を切るが、0.02 px は")
    print("       sigma=0.01 で既に数 % 誤る。**測れる最小振幅は雑音が決める**。")
    print("       撮り直せるなら sigma を下げるのが唯一効く手で、拡大率を上げても")
    print("       第 2 章のとおり何も改善しない。")

    print("\n  4d) 計測側の崖(参考)。位相の基準が J0(k*A) の第 1 零点で反転する。")
    print(f"    {'d px':>9}{'k*d rad':>11}{'実測 px':>13}{'相対誤差':>12}"
          f"{'参照コヒーレンス':>18}")
    for d0 in (0.5, 2.0, 3.0, 3.2, 4.0):
        v, _ = make_clip([(d0, FREQ, 0.0)])
        s = M.displacement_series(v, *BAND, FPS)[:, 0]
        f = M.phase_displacement(v, *BAND, FPS)
        print(f"    {d0:>9.2f}{K_X*d0:>11.4f}{amp_rms(s):>13.6f}"
              f"{rel(amp_rms(s), d0):>12.2e}{f['reference_coherence']:>18.5f}")
    print(f"    → 境界 = 2.4048/k = {2.4048/K_X:.4f} px。参照コヒーレンスが 1 から")
    print("       落ちていくのが事前の警告になる(0.5 を切ったら疑う)。")

    # ---------------------------------------------------------------- #
    print("\n=== 5. 速度(この機械での実測)===")
    vid, _ = make_clip([(0.1, FREQ, 0.0)])
    print(f"  クリップ {T} frame x {H}x{W} px = {vid.size} 要素 / "
          f"4 scale x 4 orientation")
    for label, fn in (
            ("temporal_bandpass", lambda: M.temporal_bandpass(vid, *BAND, FPS)),
            ("temporal_band_power", lambda: M.temporal_band_power(vid, *BAND, FPS)),
            ("band_snr", lambda: M.band_snr(vid, *BAND, FPS)),
            ("phase_displacement", lambda: M.phase_displacement(vid, *BAND, FPS)),
            ("displacement_series", lambda: M.displacement_series(vid, *BAND, FPS)),
            ("motion_magnify", lambda: M.motion_magnify(vid, 5.0, *BAND, FPS)),
            ("ゼロ点(位相相関)", lambda: phase_correlation_series(vid)),
    ):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<22}{1e3*(time.perf_counter()-t0):>9.1f} ms")
    print("  → 時間方向だけの op は 1 桁 ms。ステアラブル束を作る 2 つ")
    print("     (phase_displacement / motion_magnify)が 2〜3 桁重い。16 本の")
    print("     副帯域それぞれにクリップ 1 本ぶんの複素 FFT が要るため。")
    print("     ゼロ点の位相相関はその 1/10 以下で済む —— 測るだけなら安い。")

    # ---------------------------------------------------------------- #
    print("\n=== 道具の穴(この PoC が出したもの)===")
    print("  (1) motion_magnify も phase_displacement も、クリップ長が")
    print("      T*f/fps を整数にしていないことを**警告しない**。3.7 Hz を")
    print("      T=105 で撮ると隣の帯域が -3.3 dB しか落ちず、尖頭値振幅は")
    print("      +16 % 過大に出る。例外も NaN も出ないので、気づく手掛かりが")
    print("      返り値の中に無い(_require_band はビンが 1 本でもあれば通す)。")
    print("      band_snr が返す band_bins からは推し量れない種類の穴。")
    print("  (2) displacement_series の返りは波形なので、そこから「振幅」を")
    print("      作るのは呼び出し側の仕事だが、尖頭値と RMS 換算でオフビン時に")
    print("      18 ポイント差がつく。docstring の精度表はすべて尖頭値で書かれて")
    print("      いて(オンビンなので一致する)、オフビンで尖頭値を使うと表の")
    print("      精度が出ないことがどこにも書かれていない。")
    print("  (3) motion_magnify の linear_regime は phase_shift_rms_rad < pi で")
    print("      判定するが、4b の実測では alpha=40(位相増分 3.06 rad)で")
    print("      linear_regime が True のまま実測比が 0.95 まで落ちる。真偽値の")
    print("      境界と、実用上 1 % を守れる境界は一致しない。band_power 比の")
    print("      ほうが早く警告するので、判定にはそちらを見るべき。")
    print("  ※ いずれも op 本体は直していない(この PoC は読むだけ)。")

    # ---- 自己検査(速さは assert しない)---------------------------------- #
    # 1) 生成器が真値であること
    v = make_clip([(0.1, FREQ, 0.0)])[0]
    assert np.abs(v - M.synthesize_translation((H, W), T, 0.1, FREQ, FPS,
                                               wavelength_px=(LAM_X, LAM_Y),
                                               contrast=CONTRAST)).max() == 0.0
    assert np.abs(read_dx_oracle(v) - waveform(0.1)).max() < 1e-12
    # 2) 指定の 3 振幅が拡大率どおりに増幅されること
    for d0 in AMPS:
        clip_ = make_clip([(d0, FREQ, 0.0)])[0]
        for a in (2.0, 5.0, 25.0):
            got = amp_peak(read_dx_oracle(M.motion_magnify(clip_, a, *BAND, FPS)["video"]))
            assert rel(got, a * d0) < 1e-6, (d0, a, got)
    # 3) ゼロ点は無雑音では拡大経路と同等以上(= 拡大は測定を良くしない)
    for d0 in AMPS:
        clip_ = make_clip([(d0, FREQ, 0.0)])[0]
        e_null = rel(amp_rms(phase_correlation_series(clip_)[:, 0]), d0)
        e_meas = rel(amp_rms(M.displacement_series(clip_, *BAND, FPS)[:, 0]), d0)
        assert e_null < 1e-10 and e_meas < 1e-10, (d0, e_null, e_meas)
    # 4) 拡大してから測って alpha で割っても精度は上がらない(誤差比 ~1)
    noisy = make_clip([(0.1, FREQ, 0.0)], noise_sigma=0.01, seed=11)[0]
    e_plain = rel(amp_rms(M.displacement_series(noisy, *BAND, FPS)[:, 0]), 0.1)
    mag = M.motion_magnify(noisy, 10.0, *BAND, FPS)["video"]
    e_mag = rel(amp_rms(M.displacement_series(mag, *BAND, FPS)[:, 0] / 10.0), 0.1)
    assert 0.5 < (e_mag / e_plain) < 2.0, (e_plain, e_mag)
    # 5) 周波数選択性: オンビンなら帯域外は完全に落ちる
    on_bin = make_clip([(0.1, FREQ, 0.0)])[0]
    assert amp_rms(M.displacement_series(on_bin, 5.9, 7.1, FPS)[:, 0]) < 1e-12
    # 6) 漏話: 6.5 Hz 0.4 px を足しても 3.7 Hz 帯の読みは動かない(オンビン)
    both = make_clip([(0.1, FREQ, 0.0), (0.4, 6.5, 0.7)])[0]
    assert rel(amp_rms(M.displacement_series(both, *BAND, FPS)[:, 0]), 0.1) < 1e-10
    # 7) 線形性の境界: 0.4 px までは 1 %、1.2 px では外れる
    assert abs(lin[0.4] - 1.0) < 0.01, lin[0.4]
    assert abs(lin[1.2] - 1.0) > 0.05, lin[1.2]
    # 8) 空間的に変わる運動: 場は分離でき、剛体仮定のゼロ点は平均を返す
    assert abs(prof[10] - 0.30) < 0.02 and prof[W - 10] < 0.02
    assert 0.10 < pc < 0.20
    # 9) 拡大は運動 SNR を上げない(op 自身の申告とも一致)
    r = M.motion_magnify(noisy, 10.0, *BAND, FPS)
    assert r["motion_snr_change_db"] <= 1e-9
    assert r["image_snr_change_db"] <= 1e-9
    # 10) 帯域外の運動は拡大されない
    off = make_clip([(0.5, 12.0, 0.0)])[0]
    g = amp_peak(read_dx_oracle(M.motion_magnify(off, 20.0, *BAND, FPS)["video"])) / 0.5
    assert abs(g - 1.0) < 1e-9, g
    # 11) fail-closed: 帯域が Nyquist を超えたら拒否される
    try:
        M.displacement_series(on_bin, 3.0, 100.0, FPS)
        raise AssertionError("Nyquist を超えた帯域が素通りした")
    except ValueError:
        pass

    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
