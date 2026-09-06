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
   振動を合成し、拡大後の映像を (a) 既知格子ビンの DFT 位相、(b)「同じ振幅を
   本当に α 倍動かした理想クリップ」との突き合わせ、の 2 経路で検証する。
   狭帯域の被写体では **α = 200 まで機械精度で厳密**だった。
2. **ゼロ点を置く** —— 「拡大しない生の映像から位相相関で測る」を対照に置く。
   **結論は正直に言って「拡大は測定の役に立たない」**。無雑音では両者とも
   1e-15、雑音下でもしきい値をまともに選べば位相相関は位相計測に並ぶ。
   拡大してから測って α で割っても誤差は縮まない —— 帯域内の位相を α 倍
   すると帯域内の雑音も同じ α 倍されるからで、実装の質ではなく原理。
   拡大は**人間に見せるため**の道具である。
   ただし位相計測が勝つ場面が 2 つある: (a) 位相相関のしきい値を外すと 1 桁
   誤るのに対し位相計測にはそのノブが無い、(b) 運動が視野内で**空間的に変わる**
   場合、位相相関は剛体変位ひとつしか返せず、片持ち梁の実測では 0.30 px と
   0.00 px の面積平均 0.15 px という**どこにも存在しない数**を返す。
3. **周波数の選択性はクリップ長で決まる** —— 3.7 Hz が DFT ビンに乗るとき
   帯域外応答は -300 dB、乗らないとき隣の帯域が -3.5 dB しか落ちない。
   時間帯域通過は理想ブリックウォールなので、選択性を壊すのはフィルタでは
   なく「T·f/fps を整数にしなかったこと」。帯域外に置いたはずの 12.0 Hz
   の運動が α=20 で 1.074 倍に増幅される、という形でも表に出る。
4. **壊れる境界を数字で** —— 拡大率をいくら上げても壊れない。壊すのは
   (a) 入力振幅が J0(k·A) の第 1 零点 = 3.0619 px を越えること、
   (b) 被写体テクスチャが広帯域であること(利得が最大 13 % 不足する。
   同じ映像でも「測る」ほうは 0.3 % 以内で当たる)、(c) 雑音。

★ この PoC が出した道具の穴 3 件は末尾の「道具の穴」節にまとめてある。

    py -3.11 examples/poc_motion_magnification.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import motionmag as M  # noqa: E402

# --------------------------------------------------------------------------- #
# 実験の設定                                                                    #
# --------------------------------------------------------------------------- #
H = W = 64                  # 関心領域(ROI)。振動を測るのは画角全体ではない
T = 100                     # フレーム数
FPS = 37.0                  # 3.7 Hz が T*f/fps = 10 でちょうどビンに乗る
FREQ = 3.7                  # 構造物の共振周波数 [Hz]
BAND = (3.0, 4.5)           # 通過帯域 [Hz]
LAM_X, LAM_Y = 8.0, 16.0    # 表面テクスチャの縞波長 px。別オクターブにする
CYC_X = int(round(W / LAM_X))          # 横方向 8 周期
K_X = 2.0 * np.pi * CYC_X / W          # = 0.7854 rad/px
CONTRAST = 0.4

AMPS = (0.02, 0.1, 0.5)     # 検証する既知振幅 [px]


def surface(h=H, w=W, lam_x=LAM_X, lam_y=LAM_Y, contrast=CONTRAST, offset=0.5):
    """構造物表面のテクスチャ。2 軸の格子で、2 軸は別オクターブに置く。

    同じ波長にすると横縞と縦縞が同じ副帯域に落ち、局所位相が「2 成分の和の
    位相」になって変位に線形でなくなる(motionmag 側の docstring が実測 6.1 %
    の誤差として記録している条件)。その広帯域版は第 4 章 c で扱う。"""
    cx = max(1, int(round(w / lam_x)))
    cy = max(1, int(round(h / lam_y)))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    return offset + 0.5 * contrast * (np.cos(2.0 * np.pi * cx * xx / w)
                                      + np.cos(2.0 * np.pi * cy * yy / h))


def rough_surface(smooth_sigma, seed=3, h=H, w=W, contrast=0.4, offset=0.5):
    """広帯域テクスチャ(等方雑音をガウス平滑)。実物の塗装面・鋳肌に近い。

    *smooth_sigma* が大きいほど空間周波数が低いほうへ寄り、1 本の副帯域に
    同居する成分が増える —— 位相ベース処理の狭帯域条件が破れる向き。"""
    rng = np.random.default_rng(seed)
    fv = np.fft.fftfreq(h)[:, None]
    fu = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2.0 * (np.pi * smooth_sigma) ** 2 * (fu ** 2 + fv ** 2))
    s = np.real(np.fft.ifft2(np.fft.fft2(rng.normal(0.0, 1.0, (h, w))) * g))
    return offset + contrast * s / np.abs(s).max()


def translate(base, dx_series, dy_series=None):
    """フーリエ位相ランプによる厳密な平行移動 -> ``(T, H, W)``。

    格子は格子上で周期的なので、位相ランプは**補間誤差ゼロ**の帯域制限
    シフトそのもの。したがって与えた ``dx_series`` が機械精度で真値になる。
    ``synthesize_translation`` と同じ手口で、任意の変位波形を与えられる点だけ
    が違う(複数成分を重ねるのと、理想拡大クリップを作るのにいる)。"""
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
# 検証のための 3 つの読み出し経路(いずれも motionmag の外側)                   #
# --------------------------------------------------------------------------- #
def read_dx_oracle(video):
    """既知の格子ビンの DFT 位相から変位を読む -> ``(T,)`` px。

    格子の周期数 CYC_X を**知っている**前提の読み出しなので、増幅の検算には
    使えるが計測手法の対照にはならない(第 2 章のゼロ点は別に用意する)。
    時間方向に unwrap するので、フレーム間の位相増分が π を超えると壊れる。
    その境界は :func:`unwrap_limit_px` で計算して表に旗を立てる。"""
    spec = np.fft.fft2(np.asarray(video, np.float64), axes=(1, 2))
    return -np.unwrap(np.angle(spec[:, 0, CYC_X])) / K_X


def unwrap_limit_px(freq=FREQ, fps=FPS):
    """oracle 読み出しが耐えられる振幅の上限 [px]。

    正弦運動 A·sin(2 pi f t/fps) のフレーム間差分は最大 A·2 pi f/fps、その位相は
    k 倍。これが pi を超えると ``np.unwrap`` が別の枝を選ぶ。"""
    return np.pi / (K_X * 2.0 * np.pi * freq / fps)


def fidelity_error(magnified, base, disp, alpha):
    """拡大結果と「本当に α 倍動いた理想クリップ」の帯域内 RMS 相対差。

    位相 unwrap を使わないので大振幅でも壊れず、「増幅が実際の運動の代わりに
    なっているか」を映像そのもので問う。0 なら区別がつかない。"""
    ideal = translate(base, alpha * np.asarray(disp, np.float64))
    bm = M.temporal_bandpass(magnified, *BAND, FPS)
    bi = M.temporal_bandpass(ideal, *BAND, FPS)
    den = float(np.sqrt(np.mean(bi ** 2)))
    num = float(np.sqrt(np.mean((bm - bi) ** 2)))
    return num / den if den > 0.0 else num


def phase_correlation_series(video, keep_frac=0.05, ref=0):
    """ゼロ点: 生映像から位相相関でフレームごとの剛体変位 -> ``(T, 2)`` px。

    フレーム ``ref`` との交差パワースペクトル ``F_t conj(F_ref)`` の位相は
    平行移動 dx, dy に対して ``-2 pi (u dx + v dy)`` の平面になる。強度の
    大きいビンだけを残し ``|F_ref|^2`` を重みにした最小二乗でその平面の傾きを
    解く —— サブピクセル位相相関の素直な実装で、拡大も帯域通過も使わない。

    ``keep_frac`` は「どのビンを信じるか」のしきい値(``|F_ref|`` の最大値に
    対する比)。**この値が結果を左右する**ことは第 2 章 c で表にした。"""
    v = np.asarray(video, np.float64)
    t, h, w = v.shape
    spec = np.fft.fft2(v, axes=(1, 2))
    ref_spec = spec[ref]
    mag = np.abs(ref_spec).copy()
    mag[0, 0] = 0.0                       # DC は変位の情報を持たない
    keep = mag > keep_frac * mag.max()
    if int(keep.sum()) < 2:
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
    """正弦の振幅を RMS 経由で推定。整数周期なら標本化によらず不偏。"""
    return float(np.sqrt(2.0) * np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)))


def amp_peak(x):
    """振幅を尖頭値で推定。標本が山を踏み外すと過小、リンギングで過大。"""
    return float(np.abs(np.asarray(x, np.float64)).max())


def rel(measured, truth):
    return abs(measured - truth) / abs(truth) if truth else abs(measured)


# --------------------------------------------------------------------------- #
def main():
    print("=== 0. 設定と、真値生成器そのものの検算 ===")
    print(f"  ROI {H}x{W} px / {T} frame / {FPS:g} fps / 共振 {FREQ:g} Hz")
    print(f"  3.7 Hz は DFT ビン {FREQ*T/FPS:.2f} 番(整数 = ビンに乗る)"
          f" / ビン間隔 {FPS/T:.4f} Hz")
    print(f"  表面テクスチャ 縞波長 {LAM_X:g} と {LAM_Y:g} px / "
          f"k_x = {K_X:.6f} rad/px")
    print(f"  位相の硬い上限 pi/k = {np.pi/K_X:.4f} px / "
          f"参照が反転する 2.4048/k = {2.4048/K_X:.4f} px")
    print(f"  通過帯域 {BAND[0]:g}-{BAND[1]:g} Hz / "
          f"oracle 読み出しの上限 {unwrap_limit_px():.2f} px")
    ref_clip = M.synthesize_translation((H, W), T, 0.1, FREQ, FPS,
                                        wavelength_px=(LAM_X, LAM_Y),
                                        contrast=CONTRAST)
    mine, _d = make_clip([(0.1, FREQ, 0.0)])
    print(f"  自作 translate と synthesize_translation の差 = "
          f"{np.abs(mine - ref_clip).max():.3e}(同じ位相ランプ = 完全一致)")
    print(f"  与えた変位と oracle 読み出しの差 = "
          f"{np.abs(read_dx_oracle(mine) - waveform(0.1)).max():.3e} px")

    # ---------------------------------------------------------------- #
    print("\n=== 1. 拡大率どおりか(既知振幅 x 拡大率)===")
    print("  検証は 2 経路。(A) 既知格子ビンの DFT 位相 = motionmag と無関係。")
    print("  (B) 忠実度誤差 = 本当に a 倍動かした理想クリップとの帯域内 RMS 差。")
    print(f"  {'真の d px':>10}{'alpha':>7}{'期待 a*d':>11}"
          f"{'(A) 実測 px':>14}{'(A) 実測/期待':>15}{'(B) 忠実度誤差':>16}")
    base = surface()
    lim = unwrap_limit_px()
    for d0 in AMPS:
        vid, disp = make_clip([(d0, FREQ, 0.0)])
        for alpha in (1.0, 2.0, 5.0, 10.0, 25.0):
            r = M.motion_magnify(vid, alpha, *BAND, FPS)
            meas = amp_rms(read_dx_oracle(r["video"]))
            fid = fidelity_error(r["video"], base, disp, alpha)
            note = "  <- (A) は unwrap 不能域" if alpha * d0 > lim else ""
            print(f"  {d0:>10.2f}{alpha:>7.0f}{alpha*d0:>11.4f}"
                  f"{meas:>14.6f}{meas/(alpha*d0):>15.8f}{fid:>16.2e}{note}")
    print("  → 0.02 px を 25 倍しても 1.00000000。忠実度誤差も 1e-14 台で、")
    print("     出力は「本当にその振幅で動いた映像」と区別がつかない。")
    print("     最後の行だけ (A) が外れるのは**読み出し側**の unwrap が先に")
    print(f"     壊れるためで(12.5 px > {lim:.2f} px)、(B) は 1e-14 のまま。")
    if figs.enabled():
        # 図: 1 行だけを時間方向に並べたスリット像(横 = 時間、縦 = 列)。
        #     0.5 px の振動では縞が真っ直ぐに見えるが、25 倍にするとうねりが
        #     目で見える。どちらも自分の値域で塗るので、違うのは形だけ。
        v05 = make_clip([(0.5, FREQ, 0.0)])[0]
        m25 = M.motion_magnify(v05, 25.0, *BAND, FPS)["video"]
        # 表示は最近傍で 3 倍に伸ばすだけ(標本を増やしてはいない)。
        def _zoom3(a):
            return np.repeat(np.repeat(a, 3, axis=0), 3, axis=1)

        figs.save_grid("slit_scan",
                       [_zoom3(v05[:, H // 2, :].T), _zoom3(m25[:, H // 2, :].T)],
                       ["生 0.5 px", "25 倍後"], ncols=1,
                       title="行 %d のスリット像(横 = %d フレーム、3 倍表示)"
                             % (H // 2, T),
                       caption="拡大が買っているのは人間の目。縞のうねりが "
                               "3.7 Hz の振動そのもの。")

    # ---------------------------------------------------------------- #
    print("\n=== 2. ゼロ点 —— 拡大しない生映像を位相相関で測る ===")
    print("  2a) 無雑音・単一周波数。両者とも真値に機械精度で一致する。")
    print(f"  {'真の d px':>10}{'位相相関(ゼロ点)':>22}{'相対誤差':>12}"
          f"{'位相計測':>16}{'相対誤差':>12}")
    for d0 in AMPS:
        vid, _ = make_clip([(d0, FREQ, 0.0)])
        pc = phase_correlation_series(vid)[:, 0]
        ps = M.displacement_series(vid, *BAND, FPS)[:, 0]
        print(f"  {d0:>10.2f}{amp_rms(pc):>22.10f}{rel(amp_rms(pc), d0):>12.2e}"
              f"{amp_rms(ps):>16.10f}{rel(amp_rms(ps), d0):>12.2e}")
    print("  → 引き分け。拡大を通していない生映像で 0.02 px が 1e-15 で出る。")

    print("\n  2b) 雑音を入れる。d = 0.1 px 固定。4 経路を並べる。")
    print("      (i) 位相相関 / (ii) 位相相関 + 同じ時間帯域通過 /")
    print("      (iii) 位相計測 / (iv) 10 倍に拡大してから測って 10 で割る")
    print(f"  {'sigma':>8}{'(i) 生':>12}{'(ii) +帯域':>14}{'(iii) 位相計測':>18}"
          f"{'(iv) 拡大後/10':>18}")
    d0 = 0.1
    err_plain = err_mag = None
    for sigma in (0.0, 0.001, 0.01, 0.05):
        vid, _ = make_clip([(d0, FREQ, 0.0)], noise_sigma=sigma, seed=11)
        pc = phase_correlation_series(vid)[:, 0]
        pcb = temporal_band(pc)
        ps = M.displacement_series(vid, *BAND, FPS)[:, 0]
        mg = M.motion_magnify(vid, 10.0, *BAND, FPS)["video"]
        pm = M.displacement_series(mg, *BAND, FPS)[:, 0] / 10.0
        if sigma == 0.01:
            err_plain, err_mag = rel(amp_rms(ps), d0), rel(amp_rms(pm), d0)
        print(f"  {sigma:>8.3f}{amp_rms(pc):>12.6f}{amp_rms(pcb):>14.6f}"
              f"{amp_rms(ps):>18.6f}{amp_rms(pm):>18.6f}")
    print("  → (iii) と (iv) はほぼ同じ数字。**拡大しても測定は良くならない**。")
    print("     帯域内の位相を alpha 倍すると帯域内の雑音も同じ alpha 倍される。")
    print("     motion_magnify 自身が motion_snr_change_db <= 0 として同じことを")
    print("     宣言しており、この PoC はそれを変位の側から独立に確かめた。")

    print("\n  2c) ゼロ点のしきい値感度。位相相関は keep_frac を外すと 1 桁誤る。")
    print(f"  {'sigma':>8}" + "".join(f"{f'keep={f:g}':>13}"
                                      for f in (0.001, 0.01, 0.05, 0.15))
          + f"{'位相計測':>16}")
    for sigma in (0.01, 0.05, 0.2):
        vid, _ = make_clip([(d0, FREQ, 0.0)], noise_sigma=sigma, seed=11)
        cells = [amp_rms(phase_correlation_series(vid, keep_frac=f)[:, 0])
                 for f in (0.001, 0.01, 0.05, 0.15)]
        ps = amp_rms(M.displacement_series(vid, *BAND, FPS)[:, 0])
        print(f"  {sigma:>8.3f}" + "".join(f"{c:>13.6f}" for c in cells)
              + f"{ps:>16.6f}")
    print("  → 真値は 0.100000。しきい値を低くすると雑音ビンの巻いた位相が")
    print("     最小二乗を 0 側に引き、sigma=0.2 では半分以下に潰れる。位相計測に")
    print("     同じ役目のノブは無い(副帯域の振幅重みが自動でそれをやる)。")
    print("     ゼロ点が並ぶのは「しきい値を正しく選べたとき」だけである。")

    print("\n  2d) ゼロ点が原理的に答えられない場合 —— 運動が空間で変わる")
    xx = np.arange(W)[None, :] * np.ones((H, 1))
    win = 1.0 / (1.0 + np.exp((xx - W * 0.5) / 1.5))     # 左 1 / 右 0
    moving = translate(base, waveform(0.30))
    fixed = np.repeat(base[None], T, axis=0)
    vid = win[None] * moving + (1.0 - win)[None] * fixed
    field = M.phase_displacement(vid, *BAND, FPS)
    dxf = field["dx"]
    prof = np.array([amp_rms(dxf[:, H // 2, c]) for c in range(W)])
    pc_rigid = amp_rms(phase_correlation_series(vid)[:, 0])
    print("      片持ち梁: 左半分が 0.30 px で振動、右半分(固定端)は 0.00 px")
    print(f"      位相計測の列プロファイル(8 列おき、行 {H//2}):")
    print("        " + " ".join(f"{v:.3f}" for v in prof[::8]))
    print(f"      自由端側 列 10 = {prof[10]:.5f} px(真 0.30)/ "
          f"固定端側 列 {W-10} = {prof[W-10]:.5f} px(真 0.00)")
    print(f"      ゼロ点(剛体を仮定する位相相関)= {pc_rigid:.5f} px")
    print("      → 0.30 と 0.00 の面積平均。**どこにも存在しない値**を 1 つ返す。")
    print("         振動モード形状が要るなら位相相関では原理的に届かない。")
    print("      注: 列 0 は FFT の周回境界で右端と隣接するため境界値になる。")
    # 図: この PoC でゼロ点が原理的に負ける唯一の場所。剛体を仮定する位相相関は
    #     1 本の水平線しか引けず、その値はどの列の真値とも違う。
    cols_ax = np.arange(W)
    figs.save_plot("beam_profile",
                   [("真値 0.30 x 窓", cols_ax, 0.30 * win[H // 2]),
                    ("位相計測(画素ごと)", cols_ax, prof),
                    ("ゼロ点 位相相関(剛体 1 値)", cols_ax,
                     np.full(W, pc_rigid))],
                   xlabel="列 [px]", ylabel="振幅 [px]",
                   title="片持ち梁 —— 左半分だけが 0.30 px で振動",
                   caption="剛体を仮定する位相相関が返す %.3f px は 0.30 と 0.00 の"
                           "面積平均で、どの列の真値とも違う。" % pc_rigid)

    print("\n  【第 2 章の結論(正直版)】")
    print("   ・拡大は測定精度を良くしない。0.02 px は生映像から直接測れる。")
    print("   ・雑音下で位相計測が勝って見えるのはしきい値の話で、ゼロ点を")
    print("     まともに調律すれば並ぶ。拡大の寄与はどちらでもゼロ。")
    print("   ・位相計測が本当に買っているのは精度ではなく (a) ノブの少なさと")
    print("     (b) 画素ごとの変位場。拡大が買っているのは**人間の目**だけ。")

    # ---------------------------------------------------------------- #
    print("\n=== 3. 周波数の選択性と漏話 ===")
    print("  帯域幅 1.5 Hz を固定して中心をずらす。真の振動は 3.7 Hz / 0.1 px。")
    sel = {}
    for t_len in (100, 105):
        cyc = FREQ * t_len / FPS
        tag = "ビンに乗る" if abs(cyc - round(cyc)) < 1e-9 else "ビンから外れる"
        print(f"\n  T={t_len} frame: 3.7 Hz = {cyc:.2f} bin({tag})"
              f" / ビン間隔 {FPS/t_len:.4f} Hz")
        vid, _ = make_clip([(0.1, FREQ, 0.0)], t=t_len)
        print(f"    {'帯域 Hz':>14}{'復元振幅 px':>15}{'相対応答 dB':>14}")
        for centre in (3.70, 4.45, 5.20, 6.00, 7.40, 2.20):
            lo, hi = centre - 0.75, centre + 0.75
            a = amp_rms(M.displacement_series(vid, lo, hi, FPS)[:, 0])
            db = 20.0 * np.log10(max(a, 1e-18) / 0.1)
            mark = "  <- 3.7 Hz を含む" if lo <= FREQ <= hi else ""
            sel[(t_len, centre)] = db
            print(f"    {f'{lo:.2f}-{hi:.2f}':>14}{a:>15.8f}{db:>14.2f}{mark}")
        vid2, _ = make_clip([(0.1, FREQ, 0.0), (0.4, 6.5, 0.7)], t=t_len)
        a37 = amp_rms(M.displacement_series(vid2, *BAND, FPS)[:, 0])
        a65 = amp_rms(M.displacement_series(vid2, 5.9, 7.1, FPS)[:, 0])
        leak = abs(a37 - 0.1)
        sel[("leak", t_len)] = leak
        print("    漏話試験(3.7 Hz 0.1 px と 6.5 Hz 0.4 px を同時に):")
        print(f"      3.7 Hz 帯 {a37:.8f} px(真 0.10)/ "
              f"6.5 Hz 帯 {a65:.8f} px(真 0.40)")
        print(f"      6.5 成分の 3.7 帯への漏れ = {leak:.3e} px = "
              f"{20*np.log10(max(leak,1e-18)/0.4):.1f} dB")
    figs.save_table("band_selectivity",
                    ["帯域中心 [Hz]", "T=100(オンビン)[dB]",
                     "T=105(オフビン)[dB]"],
                    [["%.2f" % c, "%.2f" % sel[(100, c)], "%.2f" % sel[(105, c)]]
                     for c in (2.20, 3.70, 4.45, 5.20, 6.00, 7.40)],
                    title="帯域外の落ち方は T*f/fps が整数かどうかで決まる",
                    caption="3.7 Hz を含む帯だけが 0 dB。オンビンなら帯域外は -300 dB"
                            "(丸め)、オフビンだと隣が -3.5 dB しか落ちない。",
                    col_w=170)
    print("\n  → 単一成分なら、ビンに乗っている限り帯域外は -300 dB(丸め)。")
    print("     選択性を殺すのはフィルタではなく**クリップ長**で、T*f/fps が")
    print("     整数から外れると隣の帯域が 3.5 dB しか落ちなくなる。")
    print("     実運用の作法: 共振周波数の見当をつけてから T と fps を選ぶ。")
    print("  → 漏話はオンビンでも完全にはゼロにならない(-78 dB)。時間帯域通過")
    print("     自体は厳密だが、位相は変位の**非線形**な関数なので、大きな")
    print("     6.5 Hz 成分が相互変調して 3.7 Hz 帯に混変調積を落とす。")
    print("     オフビンだとそれが -42 dB まで悪化する。")

    print("\n  3c) 帯域外の運動は拡大されない —— それもビンに乗っていれば")
    print(f"    {'運動の周波数':>14}{'ビン番号':>11}{'alpha=20 での利得':>20}")
    for f_out in (11.1, 12.0):
        v_out = make_clip([(0.5, f_out, 0.0)])[0]
        g = amp_rms(read_dx_oracle(
            M.motion_magnify(v_out, 20.0, *BAND, FPS)["video"])) / 0.5
        sel[("gain", f_out)] = g
        print(f"    {f_out:>13.1f} Hz{f_out*T/FPS:>11.2f}{g:>20.6f}")
    print("    → 11.1 Hz(30 ビン目ちょうど)は 1.000000 で素通し。同じ振幅を")
    print("       12.0 Hz(32.43 ビン)に置くと漏れが 3.0-4.5 Hz 帯に入り、")
    print("       通したつもりのない運動が 1.074 倍に**増幅**される。")

    print("\n  3d) 振幅を尖頭値で読むか RMS で読むかで答えが変わる")
    print(f"    {'T':>6}{'尖頭値 px':>13}{'誤差':>10}{'RMS 換算 px':>14}{'誤差':>10}")
    peaks = {}
    for t_len in (100, 105):
        vid, _ = make_clip([(0.1, FREQ, 0.0)], t=t_len)
        s = M.displacement_series(vid, *BAND, FPS)[:, 0]
        pk, rm = amp_peak(s), amp_rms(s)
        peaks[t_len] = (pk, rm)
        print(f"    {t_len:>6}{pk:>13.6f}{100*rel(pk,0.1):>9.1f}%"
              f"{rm:>14.6f}{100*rel(rm,0.1):>9.1f}%")
    print("    → T=100 では 10 標本/周期なので標本が山を踏み外し、尖頭値は")
    print("       cos(pi/10) = 0.951 倍に**過小**評価される(-4.9 %)。T=105 では")
    print("       ブリックウォールのリンギングが逆に尖頭値を +14 % 持ち上げる。")
    print("       整数周期なら RMS は標本化にもリンギングにも影響されない。")

    # ---------------------------------------------------------------- #
    print("\n=== 4. 壊れる条件 ===")
    print("  4a) 入力振幅を振る(alpha=3 固定)。位相計測と拡大の共通の崖。")
    print(f"    {'入力 d px':>11}{'k*d rad':>10}{'忠実度誤差':>14}"
          f"{'参照コヒーレンス':>18}{'計測 px':>12}{'計測 誤差':>12}")
    fid_by_d = {}
    for d0 in (0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 3.0, 3.05, 3.1, 3.5, 4.5, 6.0):
        vid, disp = make_clip([(d0, FREQ, 0.0)])
        r = M.motion_magnify(vid, 3.0, *BAND, FPS)
        fid = fidelity_error(r["video"], base, disp, 3.0)
        fid_by_d[d0] = fid
        f = M.phase_displacement(vid, *BAND, FPS)
        meas = amp_rms(M.displacement_series(vid, *BAND, FPS)[:, 0])
        flag = "  <- 崩壊" if fid > 1e-6 else ""
        print(f"    {d0:>11.3f}{K_X*d0:>10.4f}{fid:>14.2e}"
              f"{f['reference_coherence']:>18.5f}{meas:>12.6f}"
              f"{rel(meas, d0):>12.2e}{flag}")
    d_axis = sorted(fid_by_d)
    figs.save_plot("amplitude_cliff",
                   [("忠実度誤差", d_axis,
                     [np.log10(max(fid_by_d[d], 1e-16)) for d in d_axis])],
                   xlabel="入力振幅 d [px]", ylabel="log10 忠実度誤差",
                   title="崖は入力振幅にある(拡大率ではない)",
                   caption="3.05 px までは機械精度、3.10 px で崩壊。境界 2.4048/k = "
                           "%.4f px は J0 の第 1 零点。" % (2.4048 / K_X))
    print(f"    → 3.05 px は機械精度、3.10 px で崩壊。境界 = 2.4048/k = "
          f"{2.4048/K_X:.4f} px。")
    print("       これは位相の巻き pi/k = 4.00 px ではなく、時間平均の位相基準")
    print("       z_mean = c*J0(k*A) が J0 の第 1 零点で符号反転することによる。")
    print("       参照コヒーレンスが 1.00 から 0.50 まで単調に落ちるのが予告で、")
    print("       0.5 を切ったら結果を疑うべき。拡大と計測が同じ崖を共有する。")

    print("\n  4b) 拡大率を振る(d = 0.1 px 固定)。狭帯域では**崩れない**。")
    print(f"    {'alpha':>8}{'a*d px':>10}{'忠実度誤差':>14}{'band_power比':>14}"
          f"{'位相増分RMS':>14}{'linear_regime':>15}")
    fid_by_a = {}
    vid, disp = make_clip([(0.1, FREQ, 0.0)])
    for alpha in (2.0, 10.0, 40.0, 100.0, 200.0):
        r = M.motion_magnify(vid, alpha, *BAND, FPS)
        fid = fidelity_error(r["video"], base, disp, alpha)
        fid_by_a[alpha] = fid
        print(f"    {alpha:>8.0f}{alpha*0.1:>10.2f}{fid:>14.2e}"
              f"{r['band_power_ratio']:>14.6f}{r['phase_shift_rms_rad']:>14.4f}"
              f"{str(r['linear_regime']):>15}")
    print("    → alpha=200(上限)でも忠実度誤差は 1e-14。狭帯域の被写体では")
    print("       拡大率は線形性を壊さない。壊すのは入力振幅(4a)と")
    print("       テクスチャの帯域幅(4c)。")
    print("    ★ ただし band_power 比は 0.0009 まで落ち、linear_regime は False に")
    print("       なる。この 2 つは**誤差を測っていない**(下の 4e で証明する)。")

    print("\n  4c) 被写体テクスチャを広帯域にする —— ここで本当に線形性が崩れる")
    print(f"    {'平滑 sigma':>12}{'拡大 実測/期待':>17}{'利得不足':>11}"
          f"{'忠実度誤差':>13}{'計測 誤差(拡大せず)':>22}")
    d0, alpha = 0.2, 5.0
    disp = waveform(d0)
    gains = {}
    for sg in (0.6, 1.0, 1.5, 2.0, 3.0):
        rb = rough_surface(sg)
        v = translate(rb, disp)
        r = M.motion_magnify(v, alpha, *BAND, FPS)
        got = amp_rms(M.displacement_series(r["video"], *BAND, FPS)[:, 0])
        gain = got / (alpha * d0)
        gains[sg] = gain
        fid = fidelity_error(r["video"], rb, disp, alpha)
        m = amp_rms(M.displacement_series(v, *BAND, FPS)[:, 0])
        print(f"    {sg:>12.1f}{gain:>17.6f}{100*(1-gain):>10.2f}%"
              f"{fid:>13.4f}{100*rel(m, d0):>21.2f}%")
    print("    → 拡大の利得は最大 13 % 不足し、映像は理想並進から 12〜29 % ずれる。")
    print("       1 本の副帯域に複数の空間周波数が同居すると、その和の位相は")
    print("       変位に線形でなくなるため。位相ベース処理に内在する制約で、")
    print("       調整では消えない。")
    print("    → 同じ映像でも**計測**は 0.3 % 以内で当たる。副帯域ごとに局所")
    print("       周波数 k を測り直して最小二乗で解くので、広帯域でも崩れない。")
    print("       第 2 章の結論(測るなら拡大しない)がここでも裏から確認される。")

    print("\n  4d) 雑音。振幅が小さいほど早く壊れる。")
    print(f"    {'sigma':>8}" + "".join(f"{f'd={a:g}px 計測誤差':>18}" for a in AMPS))
    for sigma in (0.0, 0.001, 0.01, 0.05, 0.2):
        cells = []
        for d0 in AMPS:
            v, _ = make_clip([(d0, FREQ, 0.0)], noise_sigma=sigma, seed=5)
            cells.append(rel(amp_rms(M.displacement_series(v, *BAND, FPS)[:, 0]), d0))
        print(f"    {sigma:>8.3f}" + "".join(f"{100*c:>17.2f}%" for c in cells))
    print("    → 0.5 px は sigma=0.2 でも 1 桁 % に留まるが、0.02 px は")
    print("       sigma=0.01 で既に誤り始める。**測れる最小振幅は雑音が決める**。")
    print("       効くのは撮り直して sigma を下げることだけで、拡大率を上げても")
    print("       第 2 章のとおり何も改善しない。")

    print("\n  4e) band_power 比と linear_regime は誤差指標ではない(証明)")
    print(f"    {'d px':>7}{'alpha':>7}{'拡大の band_power比':>22}"
          f"{'理想並進の同じ比':>20}{'差':>10}")
    for d0, alpha in ((0.1, 10.0), (0.5, 5.0), (0.5, 10.0)):
        v, dd = make_clip([(d0, FREQ, 0.0)])
        r = M.motion_magnify(v, alpha, *BAND, FPS)
        ideal = translate(base, alpha * dd)
        p_in = M.band_snr(v, *BAND, FPS)["band_power"]
        p_id = M.band_snr(ideal, *BAND, FPS)["band_power"]
        ratio_ideal = p_id / (alpha * alpha * p_in)
        print(f"    {d0:>7.2f}{alpha:>7.0f}{r['band_power_ratio']:>22.6f}"
              f"{ratio_ideal:>20.6f}{abs(r['band_power_ratio']-ratio_ideal):>10.1e}")
    print("    → 完全に一致する。band_power 比が 1 から落ちるのは、**本物の**")
    print("       大振幅並進でも画素の輝度時系列が正弦でなくなるからであって、")
    print("       拡大が誤ったからではない。docstring は「1.0 = 完全に線形」と")
    print("       読ませるが、この量で拡大の正しさは判定できない。")

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
    print("     (phase_displacement と motion_magnify)が 1〜2 桁重い。16 本の")
    print("     副帯域それぞれにクリップ 1 本ぶんの複素 FFT が要るため。")
    print("     ゼロ点の位相相関はその 1/20 で済む —— 剛体変位を測るだけなら安い。")

    # ---------------------------------------------------------------- #
    print("\n=== 道具の穴(この PoC が出したもの。op 本体は直していない)===")
    print("  (1) band_power_ratio は「拡大が線形だったか」を測っていない。")
    print("      4e のとおり、同じ振幅で**本当に**動かした理想クリップの比と")
    print("      小数点以下まで一致する(0.856668 対 0.856668)。この量が 1 から")
    print("      離れるのは大振幅並進が画素輝度に高調波を作るからで、拡大の")
    print("      誤差ではない。docstring の「1.0 = perfectly linear」「shortfall")
    print("      は位相変調が高調波に捨てたエネルギー」という説明を素直に読むと、")
    print("      忠実度誤差 1e-14 の完璧な出力を不良と判定してしまう。")
    print("  (2) linear_regime も同じ理由で偽警報を出す。alpha=200 / d=0.1 px で")
    print("      False になるが、忠実度誤差は 2e-14。逆に 4c の広帯域テクスチャ")
    print("      では 12〜29 % ずれているのに True のままだった。真に危険なのは")
    print("      位相増分の大きさではなく**副帯域あたりの空間周波数の数**で、")
    print("      それを見る指標が返り値に無い。")
    print("  (3) 対象の周波数が DFT ビンから外れていることを誰も警告しない。")
    print("      3.7 Hz を T=105 で撮ると隣の帯域が 3.5 dB しか落ちず、漏話は")
    print("      -78 dB から -42 dB へ悪化し、尖頭値振幅は +14 % 過大に出る。")
    print("      さらに悪いのは 3c で、通過帯域の外に置いたはずの 12.0 Hz")
    print("      (32.43 ビン)の運動が alpha=20 で 1.074 倍に増幅された。")
    print("      「帯域外は素通し」という約束はビンに乗っている運動にしか")
    print("      成り立たない。例外も NaN も出ず、band_snr の band_bins からも")
    print("      読み取れない。_require_band はビンが 1 本でもあれば通す設計")
    print("      なので、ここに「ビン中心からの外れ量」を足せる余地がある。")

    # ---- 自己検査(速さは assert しない)---------------------------------- #
    # 1) 生成器が真値であること
    v = make_clip([(0.1, FREQ, 0.0)])[0]
    assert np.abs(v - M.synthesize_translation((H, W), T, 0.1, FREQ, FPS,
                                               wavelength_px=(LAM_X, LAM_Y),
                                               contrast=CONTRAST)).max() == 0.0
    assert np.abs(read_dx_oracle(v) - waveform(0.1)).max() < 1e-12
    # 2) 指定の 3 振幅が拡大率どおりに増幅されること(2 経路とも)
    for d0 in AMPS:
        clip_, disp_ = make_clip([(d0, FREQ, 0.0)])
        for a in (2.0, 5.0, 25.0):
            out = M.motion_magnify(clip_, a, *BAND, FPS)["video"]
            assert fidelity_error(out, base, disp_, a) < 1e-9, (d0, a)
            if a * d0 <= unwrap_limit_px():
                got = amp_rms(read_dx_oracle(out))
                assert rel(got, a * d0) < 1e-9, (d0, a, got)
    # 3) ゼロ点は無雑音で拡大経路と同等(= 拡大は測定を良くしない)
    for d0 in AMPS:
        clip_ = make_clip([(d0, FREQ, 0.0)])[0]
        e_null = rel(amp_rms(phase_correlation_series(clip_)[:, 0]), d0)
        e_meas = rel(amp_rms(M.displacement_series(clip_, *BAND, FPS)[:, 0]), d0)
        assert e_null < 1e-10 and e_meas < 1e-10, (d0, e_null, e_meas)
    # 4) 拡大してから測って alpha で割っても精度は上がらない(誤差比は 1 の桁)
    assert err_plain is not None and 0.2 < (err_mag / err_plain) < 5.0, \
        (err_plain, err_mag)
    # 5) 周波数選択性: オンビンなら帯域外は完全に落ち、オフビンでは落ちない
    assert sel[(100, 6.00)] < -200.0, sel[(100, 6.00)]
    assert sel[(105, 4.45)] > -10.0, sel[(105, 4.45)]
    # 6) 漏話はオンビンで -70 dB 以下、オフビンでその 1 桁上
    assert sel[("leak", 100)] < 1e-4 < sel[("leak", 105)], sel
    # 7) 尖頭値推定は標本化で偏る(RMS は偏らない)
    assert abs(peaks[100][0] / 0.1 - np.cos(np.pi / 10.0)) < 1e-6, peaks[100]
    assert rel(peaks[100][1], 0.1) < 1e-12, peaks[100]
    # 8) 崖: 3.05 px は通り 3.10 px は通らない
    assert fid_by_d[3.05] < 1e-9 < fid_by_d[3.1], (fid_by_d[3.05], fid_by_d[3.1])
    assert fid_by_d[0.001] < 1e-9 and fid_by_d[3.0] < 1e-9
    # 9) 拡大率は狭帯域では線形性を壊さない(alpha=200 まで)
    assert max(fid_by_a.values()) < 1e-9, fid_by_a
    # 10) 広帯域テクスチャでは拡大の利得が不足し、平滑が強いほど悪化する
    assert gains[3.0] < gains[1.0] < 0.99, gains
    assert (1.0 - gains[3.0]) > 0.05, gains
    # 11) 空間的に変わる運動: 場は分離でき、剛体仮定のゼロ点は平均を返す
    assert abs(prof[10] - 0.30) < 0.02 and prof[W - 10] < 0.02
    assert 0.10 < pc_rigid < 0.20
    # 12) 拡大は運動 SNR も画像 SNR も上げない(op 自身の申告と一致)
    noisy = make_clip([(0.1, FREQ, 0.0)], noise_sigma=0.01, seed=11)[0]
    r = M.motion_magnify(noisy, 10.0, *BAND, FPS)
    assert r["motion_snr_change_db"] <= 1e-9
    assert r["image_snr_change_db"] <= 1e-9
    # 13) 帯域外の運動は拡大されない —— ただしそれもビンに乗っている場合だけ。
    #     11.1 Hz は 30 ビン目ちょうどなので素通し(利得 1.0)。同じ振幅を
    #     12.0 Hz(32.43 ビン)に置くと漏れて 1.074 倍に増幅されてしまう。
    on_bin_out = make_clip([(0.5, 11.1, 0.0)])[0]
    g = amp_rms(read_dx_oracle(
        M.motion_magnify(on_bin_out, 20.0, *BAND, FPS)["video"])) / 0.5
    assert abs(g - 1.0) < 1e-9, g
    off_bin_out = make_clip([(0.5, 12.0, 0.0)])[0]
    g_off = amp_rms(read_dx_oracle(
        M.motion_magnify(off_bin_out, 20.0, *BAND, FPS)["video"])) / 0.5
    assert g_off > 1.05, g_off
    # 14) fail-closed: 帯域が Nyquist を超えたら拒否される
    try:
        M.displacement_series(v, 3.0, 100.0, FPS)
        raise AssertionError("Nyquist を超えた帯域が素通りした")
    except ValueError:
        pass

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
