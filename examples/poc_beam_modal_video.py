# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""動画から構造物の固有振動数・減衰比・モード形状を同定する —— f は最後まで生き残り、ζ が最初に嘘をつく。

橋・煙突・鉄塔・配管のようにセンサを貼れない構造物を、**カメラだけで**構造ヘルス
モニタリングする仕事です。動画から出したいのは 3 つ: 固有振動数 f_n、減衰比 ζ_n、
モード形状 φ_n(x)。同じ変位時系列から出るのに、**この 3 つは同じ条件で壊れません**。

EXTEND: 実写に差し替えるなら :func:`make_clip` が返す辞書の ``video``
(``(T, H, W)`` float、0〜1)を撮影フレーム列に、``stations``(梁に沿った測点の
列)を画面上の測点座標に置き換えます。**真値の代わりになるのは加速度計 1〜2 点の
同時計測**で、それが無いなら f_n は信じてよいが ζ_n は信じてはいけない、というのが
この PoC の結論です。撮り方で効くのは (1) 画面内に**絶対に動かない背景**を写し込む
(手ぶれの差し引きに要る。第 5 節で示すとおり無いと ζ が壊れる)、(2) 照明は直流点灯
(商用電源の 100/120 Hz は fps に折り返して**真のモードの上に落ちる fps が存在する**、
第 4 節)、(3) fps は最高次モードの 2 倍以上(Nyquist、第 4 節でその通りに折り返る)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(梁の縁 1 画素の輝度 FFT)でも f_1 は当たる**(誤差 +0.001 Hz)。
   だが輝度は照明ちらつきの折り返し線(100 Hz → fps 128 で 28.0 Hz)を**振動と
   同じ大きさで**拾い、モード形状は符号を持たない(MAC: モード 1 0.90 / モード 2
   0.56 / モード 3 0.48)。「周波数が出た」と「モードが同定できた」は別物。
2. ★**f_n は 3 モードとも 0.03 Hz 以内**(位相法・PIV とも、fps 128 / 2 s)。
   ところが同じ時系列から出した **ζ_1 は 3 通りの方法で 3 通りの答え**:
   半値幅 0.0714(真値の 3.6 倍)/ 包絡線の対数勾配 0.0206 / 減衰正弦波の
   当てはめ 0.0201(真値 0.02)。半値幅の 3.6 倍は雑音ではなく**窓長 2 s の
   分解能の下限**で、予測(矩形窓の主ローブ 0.886/T → ζ 下限 0.074)と一致。
3. ★★**振幅を 0.02 → 2 px で掃引すると壊れる順番が量ごとに違う**。位相法では
   MAC_3 が 0.05 px で先に落ち(0.98 → 0.63)、ζ_1 は 0.05 px で 2 倍の誤差
   (包絡線法 0.0106)、f_1 は 0.02 px でも 0.02 Hz 以内。PIV(窓 16 px)は
   0.1 px 以下で ζ が壊れ、0.02 px では MAC_2 が 0.85 まで落ちる。
   **f_n が合っていても ζ は 2 倍違う** —— 崖の順番は MAC_3 → ζ → MAC_2 → f。
4. ★**位相法の返す wrap_limit_px(0.32 px)は崖の位置を予測しなかった**。
   予想は「0.32 px で位相が巻いて壊れる」、実測は 2.0 px まで f_1 誤差 0.01 Hz・
   MAC_1 0.999 で壊れない。返り値の限界値は局所空間周波数の最大(雑音画素)で
   決まっていて、実際の崖は模様の波長で決まる。
5. **fps を落とすとモード 2(18.80 Hz)は Nyquist で予測どおりに折り返る**:
   fps 32 → 13.20 Hz、24 → 5.20 Hz(予測 |f_2 − k·fps| と一致、誤差 0.02 Hz 以内)。
   折り返した線は f_1 と区別がつかない —— fps 24 では 5.2 Hz の線を
   「新しいモード」と読んでしまう。★照明の折り返しは fps 48.5 で
   **ちょうど 3.00 Hz = f_1 に落ちる**。輝度のゼロ点は ζ_1 を 0.0005 と報告し
   (ちらつきは減衰しないので)、位相法は 0.0184 で生き残る(ちらつきは輝度の
   掛け算で位相を動かさない —— 位相法の dy スペクトルでのちらつき線は
   モード 1 の 0.7 %)。
6. **対照群で原因を分ける**(A_1 = 0.1 px、全部入りに対して 1 要因ずつ止める):
   手ぶれを引かないと ζ_1 は 0.0201 → 0.0294(手ぶれ 2.3 Hz が帯域内に居る)、
   雑音を止めると MAC_3 が 0.98 → 1.000、ちらつき・ローリングシャッターは
   f/ζ/MAC のどれも動かさない(予測: 行遅延 2.8 ms はモード 3 で 0.94 rad の
   位相差だが行方向に平均すると振幅 4 % の減りにしかならない)。

【グラウンドトゥルース】
片持ち梁(Euler–Bernoulli)の閉形式: β_n L = 1.87510 / 4.69409 / 7.85476、
f_n = f_1·(β_n/β_1)²、φ_n(x) = cosh βx − cos βx − σ_n(sinh βx − sin βx)。
3 モードの自由減衰 q_n(t) = A_n e^{−ζ_n ω_n t} cos(ω_dn t + θ_n) を重ねた
横変位 w(x, t) で、模様つきの梁を**閉形式のテクスチャ(余弦の和)を
連続座標で評価**して描く(補間なし = サブピクセルの真値が厳密)。
雑音・照明ちらつき(100 Hz 乗算)・手ぶれ(全画面並進)・ローリングシャッター
(行ごとの時刻遅延)は合成時に**別々のスイッチ**で入れる。

来歴(公開文献のみ): Euler–Bernoulli 梁のモード = Blevins, "Formulas for
Natural Frequency and Mode Shape" (1979)。MAC = Allemang & Brown (1982)。
半値幅法・対数減衰率 = Ewins, "Modal Testing" (2000)。位相ベースの変位計測 =
Wadhwa et al., SIGGRAPH 2013 / Chen et al., J. Sound Vib. 345 (2015)。
PIV のサブピクセル 3 点フィット = Raffel et al., "Particle Image Velocimetry"
(2018)。ローリングシャッターの時間ずれ = Liang et al., IEEE TIP 17 (2008)。

    py -3.11 examples/poc_beam_modal_video.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
H, W = 60, 192              # 画面 [px]
X0, L = 8.0, 160.0          # 固定端の x と梁の長さ [px]
YC, HB = 30.0, 8.0          # 梁の中心行と半厚 [px](16 px 厚)
F1 = 3.0                    # モード 1 の固有振動数 [Hz]
ZETA = (0.02, 0.01, 0.005)  # 減衰比 ζ_n(真値)
AMP_RATIO = (1.0, 0.4, 0.15)  # モード n の先端振幅 / A_1
THETA = (0.3, 1.1, 2.0)     # 初期位相 [rad]
FPS = 128.0                 # 基準 fps
DUR = 2.0                   # 動画の長さ [s]
NOISE = 0.02                # カメラ雑音の σ(輝度 0〜1)
FLICKER_HZ, FLICKER_M = 100.0, 0.05     # 照明ちらつき(100 Hz 全波整流、5 %)
SHAKE = ((0.8, 0.10, 0.07), (2.3, 0.12, 0.05))   # 手ぶれ (Hz, y 振幅 px, x 振幅 px)
RS_FRAC = 0.9               # ローリングシャッター: 全行読み出しがフレーム周期の 90 %
N_ST = 12                   # 梁に沿った測点数
SEED = 7
BETA_L = (1.87510407, 4.69409113, 7.85475744)
FN = tuple(F1 * (b / BETA_L[0]) ** 2 for b in BETA_L)   # 3.00 / 18.80 / 52.64 Hz
BAND = (0.5, 60.0)          # 位相法の通過帯域 [Hz](fps 128 のとき。手ぶれ 0.8 Hz も帯域内に入れる)


# --------------------------------------------------------------------------- #
# 真値 —— 片持ち梁の閉形式                                                     #
# --------------------------------------------------------------------------- #
def mode_shapes(x: np.ndarray) -> np.ndarray:
    """片持ち梁のモード形状 ``(3, len(x))``。``x`` は固定端からの距離 / L。"""
    out = []
    for bl in BETA_L:
        s = (np.cosh(bl) + np.cos(bl)) / (np.sinh(bl) + np.sin(bl))
        b = bl * x
        phi = np.cosh(b) - np.cos(b) - s * (np.sinh(b) - np.sin(b))
        out.append(phi / np.abs(phi).max())
    return np.asarray(out)


def modal_coord(t: np.ndarray, a1: float, n: int) -> np.ndarray:
    """モード n の自由減衰 q_n(t)(先端振幅 a1·AMP_RATIO[n])。"""
    w = 2.0 * np.pi * FN[n]
    z = ZETA[n]
    return a1 * AMP_RATIO[n] * np.exp(-z * w * t) * np.cos(w * np.sqrt(1 - z * z) * t + THETA[n])


def deflection(xn: np.ndarray, t: np.ndarray, a1: float) -> np.ndarray:
    """横変位 w(x, t) ``(len(t), len(x))``。``xn`` は正規化座標(0〜1)。"""
    phi = mode_shapes(xn)
    return sum(modal_coord(t, a1, n)[:, None] * phi[n][None, :] for n in range(3))


def _texture(rng, k: int, lam_lo: float, lam_hi: float, rms: float):
    """余弦の和で作る閉形式テクスチャ(連続座標で評価できる)。"""
    lam = rng.uniform(lam_lo, lam_hi, k)
    ang = rng.uniform(0, np.pi, k)
    kx, ky = 2 * np.pi / lam * np.cos(ang), 2 * np.pi / lam * np.sin(ang)
    ph = rng.uniform(0, 2 * np.pi, k)
    amp = rms * np.sqrt(2.0 / k)

    def f(x, y):
        return sum(amp * np.cos(kx[i] * x + ky[i] * y + ph[i]) for i in range(k))
    return f


def make_clip(a1: float, fps: float = FPS, noise: float = NOISE, flicker: bool = True,
              shake: bool = True, rolling: bool = True, seed: int = SEED) -> dict:
    """梁の自由減衰振動の動画と真値を返す。妨害は**別々のスイッチ**で入れる。"""
    rng = np.random.default_rng(seed)
    T = int(round(DUR * fps))
    t = np.arange(T) / fps
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    beam_tex = _texture(rng, 24, 5.0, 14.0, 0.14)
    bg_tex = _texture(rng, 24, 6.0, 16.0, 0.08)
    xn = np.clip((xx - X0) / L, 0.0, 1.0)
    on_beam_x = ((xx >= X0) & (xx <= X0 + L)).astype(np.float64)
    # ローリングシャッター: 行 y の露光時刻は t + y·τ
    tau = RS_FRAC / fps / H if rolling else 0.0
    sx = np.zeros(T)
    sy = np.zeros(T)
    if shake:
        for fq, ay, ax in SHAKE:
            sy += ay * np.sin(2 * np.pi * fq * t + 0.4)
            sx += ax * np.sin(2 * np.pi * fq * t + 1.9)
    video = np.empty((T, H, W))
    phi = mode_shapes(xn[0])
    for i in range(T):
        ty = t[i] + yy * tau                       # 行ごとの時刻 (H, W)
        w = np.zeros((H, W))
        for n in range(3):
            wn = 2 * np.pi * FN[n]
            z = ZETA[n]
            q = a1 * AMP_RATIO[n] * np.exp(-z * wn * ty) * np.cos(wn * np.sqrt(1 - z * z) * ty + THETA[n])
            w += q * phi[n][None, :]
        # 手ぶれも行時刻で評価(全画面の並進)
        shx = shy = 0.0
        if shake:
            shx = sum(ax * np.sin(2 * np.pi * fq * ty + 1.9) for fq, ay, ax in SHAKE)
            shy = sum(ay * np.sin(2 * np.pi * fq * ty + 0.4) for fq, ay, ax in SHAKE)
        xs, ys = xx - shx, yy - shy                # 手ぶれ後の場面座標
        dist = np.abs(ys - YC - w * on_beam_x) - HB
        mask = on_beam_x / (1.0 + np.exp(np.clip(dist / 0.5, -40, 40)))   # 柔らかい縁
        img = (0.5 + bg_tex(xs, ys)) * (1 - mask) + (0.5 + beam_tex(xs, ys - w)) * mask
        if flicker:
            img = img * (1.0 + FLICKER_M * np.sin(2 * np.pi * FLICKER_HZ * ty + 0.7))
        video[i] = img
    if noise > 0:
        video += noise * rng.standard_normal(video.shape)
    st_x = X0 + L * (np.arange(1, N_ST + 1) / N_ST) - 3.0   # 測点(先端は縁から 3 px 内側)
    st_xn = (st_x - X0) / L
    return {"video": np.clip(video, 0, 1), "t": t, "fps": fps, "T": T, "a1": a1,
            "stations": st_x, "phi_true": mode_shapes(st_xn),
            "w_true": deflection(st_xn, t, a1), "shake": (sx, sy),
            "flicker_alias": min(abs(FLICKER_HZ - k * fps) for k in range(0, 8))}


# --------------------------------------------------------------------------- #
# 推定器 —— ゼロ点(輝度)/ 位相法 / PIV                                        #
# --------------------------------------------------------------------------- #
def _bg_rows() -> np.ndarray:
    """梁が決して入らない背景の行(手ぶれの参照)。

    画面の上下 8 行は使わない —— 位相法の dy は画面の縁で 0.33〜0.96 倍に
    落ちる(道具の穴 (f)、実測)。
    """
    return np.r_[9:15, H - 15:H - 9]


def stations_phase(clip: dict, correct_shake: bool = True, band=BAND) -> dict:
    """位相法(``phase_displacement``)で梁の測点ごとの dy(t) を出す。"""
    v = clip["video"]
    fps = clip["fps"]
    hi = min(band[1], 0.49 * fps)
    fld = fs.ledger.phase_displacement(v, band[0], hi, fps)
    wgt = fld["weight"] * fld["valid"]
    dy = fld["dy"]
    rows = slice(int(YC - HB + 4), int(YC + HB - 4))     # 梁の内側 8 行(A_1 = 2 px でも出ない)
    out = np.zeros((clip["T"], N_ST))
    for i, x in enumerate(clip["stations"]):
        c = slice(int(round(x)) - 3, int(round(x)) + 2)
        wg = wgt[rows, c]
        out[:, i] = (dy[:, rows, c] * wg[None]).sum(axis=(1, 2)) / max(wg.sum(), 1e-12)
    br = _bg_rows()
    wg = wgt[br]
    bg = (dy[:, br] * wg[None]).sum(axis=(1, 2)) / max(wg.sum(), 1e-12)
    if correct_shake:
        out = out - bg[:, None]
    return {"u": out, "bg": bg, "wrap_limit_px": fld["wrap_limit_px"], "x": clip["stations"]}


def stations_piv(clip: dict, correct_shake: bool = True) -> dict:
    """PIV(``piv_cross_correlate``、窓 16 px)で梁の測点ごとの dy(t) を出す。

    梁の行だけを切り出して 1 行ぶんの窓列にする(窓に背景が混ざると相関の
    山が静止側へ引かれる)。手ぶれは背景の切り出しで別に測る。台帳の
    ``piv_cross_correlate`` は ``info``(窓中心)を返さないので、窓中心は
    ``start + (window-1)/2`` を自分で組む。
    """
    v = clip["video"]
    r0, r1 = int(YC - HB), int(YC + HB)
    beam = v[:, r0:r1]
    bg_top = v[:, 2:14]
    win = 16
    ref = beam[0]
    T = clip["T"]
    dy = None
    for i in range(T):
        fl = np.asarray(fs.ledger.piv_cross_correlate(ref, beam[i], window=win, overlap=0.5))
        if dy is None:
            dy = np.zeros((T, fl.shape[2]))
        dy[i] = fl[0, 0]
    cols = np.arange(dy.shape[1]) * (win // 2) + (win - 1) / 2.0
    bg = np.zeros(T)
    if correct_shake:
        ref_b = bg_top[0]
        for i in range(T):
            fl = np.asarray(fs.ledger.piv_cross_correlate(ref_b, bg_top[i], window=12, overlap=0.5))
            bg[i] = fl[0].mean()
        dy = dy - bg[:, None]
    # 梁の上にある窓だけ(固定端の窓は φ≈0 で分母に効かないので外す)
    keep = (cols >= X0 + 0.15 * L) & (cols <= X0 + L - 4)
    xn = (cols[keep] - X0) / L
    return {"u": dy[:, keep], "x": cols[keep], "phi_true": mode_shapes(xn),
            "w_true": deflection(xn, clip["t"], clip["a1"]), "bg": bg}


def zero_point(clip: dict) -> dict:
    """ゼロ点: 梁の上縁 1 画素の輝度時系列(測点ごと)。

    現場の人がやるとおり「縁のいちばんコントラストの強い画素」を選ぶ: 上縁
    ±1 行のうち、時間平均画像の縦勾配が最大の行。
    """
    v = clip["video"]
    mean = v.mean(axis=0)
    grad = np.abs(np.gradient(mean, axis=0))
    r0 = int(YC - HB)
    cols = []
    for x in clip["stations"]:
        c = int(round(x))
        row = r0 - 1 + int(np.argmax(grad[r0 - 1:r0 + 2, c]))
        cols.append(v[:, row, c])
    u = np.stack(cols, axis=1)
    return {"u": u - u.mean(axis=0), "x": clip["stations"]}


# --------------------------------------------------------------------------- #
# スペクトルの読み取り —— f_n / 半値幅 / 複素振幅                               #
# --------------------------------------------------------------------------- #
def spectrum_peak(u: np.ndarray, fps: float, f_guess: float, tol: float, pad: int = 16) -> dict:
    """``f_guess ± tol`` の中で最大のピークを放物線補間で読む。"""
    n = len(u)
    m = n * pad
    spec = np.fft.rfft(u - u.mean(), m)
    fr = np.fft.rfftfreq(m, 1.0 / fps)
    mag = np.abs(spec)
    sel = (fr >= f_guess - tol) & (fr <= f_guess + tol)
    idx = np.nonzero(sel)[0]
    k = idx[np.argmax(mag[idx])]
    if 0 < k < len(mag) - 1:
        a, b, c = np.log(mag[k - 1] + 1e-300), np.log(mag[k] + 1e-300), np.log(mag[k + 1] + 1e-300)
        d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
    else:
        d = 0.0
    f_hat = (k + d) * fps / m
    # 半値幅(-3 dB)
    half = mag[k] / np.sqrt(2.0)
    lo = k
    while lo > 0 and mag[lo] > half:
        lo -= 1
    hi = k
    while hi < len(mag) - 1 and mag[hi] > half:
        hi += 1
    width = (hi - lo) * fps / m
    return {"f": f_hat, "amp": 2.0 * mag[k] / n, "width": width,
            "zeta_hp": width / (2.0 * f_hat), "cplx": spec[k], "bin": k}


def line_amplitude(u: np.ndarray, fps: float, f0: float) -> float:
    """周波数 f0 の線の片側振幅(ビン中心の DFT、窓なし)。"""
    n = len(u)
    k = int(round(f0 * n / fps))
    return 2.0 * abs(np.fft.rfft(u - u.mean())[k]) / n


def bandpass_1d(u: np.ndarray, fps: float, f_lo: float, f_hi: float) -> np.ndarray:
    """1-D 時系列を ``temporal_bandpass``(理想帯域通過)に通す。

    op は「4×4 以上のフレーム」を要求するので、同じ時系列を 4×4 に敷き詰めて
    渡し、1 画素ぶんを取り出す(道具の穴 (d))。
    """
    n = len(u)
    # 減衰する信号は先頭と末尾で値が違う(周期的でない)。そのまま DFT に掛けると
    # 継ぎ目の段差が帯域内に漏れて包絡線を歪めるので、偶関数で折り返して繋ぐ。
    ext = np.concatenate([u[::-1], u, u[::-1]])
    v = np.broadcast_to(ext.reshape(-1, 1, 1), (3 * n, 4, 4))
    return np.asarray(fs.temporal_bandpass(np.ascontiguousarray(v), f_lo, f_hi, fps))[n:2 * n, 0, 0]


def damping_envelope(u: np.ndarray, fps: float, f_hat: float, half_band: float) -> float:
    """包絡線(Hilbert)の対数勾配から ζ。"""
    x = bandpass_1d(u, fps, max(0.5, f_hat - half_band), min(0.49 * fps, f_hat + half_band))
    env = np.asarray(fs.envelope(x))
    t = np.arange(len(u)) / fps
    sel = (t >= 0.12) & (t <= DUR - 0.35)
    slope = np.polyfit(t[sel], np.log(np.maximum(env[sel], 1e-12)), 1)[0]
    return float(-slope / (2 * np.pi * f_hat))


def damping_fit(u: np.ndarray, fps: float, f_hat: float, half_band: float) -> tuple[float, float]:
    """減衰正弦波 A e^{-ζωt} cos(ω_d t + θ) の非線形最小二乗 → (ζ, f)。"""
    x = bandpass_1d(u, fps, max(0.5, f_hat - half_band), min(0.49 * fps, f_hat + half_band))
    t = np.arange(len(u)) / fps

    def model(p):
        a, z, f, th = p
        w = 2 * np.pi * f
        return a * np.exp(-abs(z) * w * t) * np.cos(w * np.sqrt(max(1 - z * z, 1e-9)) * t + th)

    best = None
    for th0 in (0.0, 1.5, 3.0, 4.5):
        p0 = (2.0 * np.abs(x).max(), 0.01, f_hat, th0)
        r = least_squares(lambda p: model(p) - x, p0, max_nfev=400)
        if best is None or r.cost < best.cost:
            best = r
    return float(abs(best.x[1])), float(best.x[2])


def mode_shape(U: np.ndarray, fps: float, f_hat: float) -> np.ndarray:
    """測点ごとの複素振幅 → 先端の位相に揃えた実モード形状(最大値 1)。"""
    n = U.shape[0]
    m = n * 16
    k = int(round(f_hat * m / fps))
    X = np.fft.rfft(U - U.mean(axis=0), m, axis=0)[k]
    ref = X[-1] / max(abs(X[-1]), 1e-300)
    phi = np.real(X * np.conj(ref))
    return phi / max(np.abs(phi).max(), 1e-300)


def mac(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) ** 2 / (np.dot(a, a) * np.dot(b, b)))


def identify(est: dict, fps: float, phi_true: np.ndarray, half_bands=(1.5, 2.5, 4.0)) -> dict:
    """1 つの推定器の測点時系列から f_n / ζ_n(3 法)/ MAC_n を出す。"""
    U = est["u"]
    tip = U[:, -1]
    out = {"f": [], "zeta_hp": [], "zeta_env": [], "zeta_fit": [], "mac": [], "amp": []}
    for n in range(3):
        if FN[n] >= 0.49 * fps:
            for key in out:
                out[key].append(np.nan)
            continue
        pk = spectrum_peak(tip, fps, FN[n], tol=max(1.0, 0.1 * FN[n]))
        z_env = damping_envelope(tip, fps, pk["f"], half_bands[n])
        z_fit, _ = damping_fit(tip, fps, pk["f"], half_bands[n])
        phi = mode_shape(U, fps, pk["f"])
        out["f"].append(pk["f"])
        out["zeta_hp"].append(pk["zeta_hp"])
        out["zeta_env"].append(z_env)
        out["zeta_fit"].append(z_fit)
        out["mac"].append(mac(phi, phi_true[n]))
        out["amp"].append(pk["amp"])
        out["phi%d" % (n + 1)] = phi
    return out


# --------------------------------------------------------------------------- #
# 1. ゼロ点 —— 1 画素の輝度 FFT                                                  #
# --------------------------------------------------------------------------- #
def section_zero_point(clip: dict) -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— 梁の縁 1 画素の輝度 FFT(A_1 = %.2f px、fps %.0f)" % (clip["a1"], clip["fps"]))
    print("=" * 78)
    z = zero_point(clip)
    tip = z["u"][:, -1]
    n = len(tip)
    fr = np.fft.rfftfreq(n, 1.0 / clip["fps"])
    mag = 2 * np.abs(np.fft.rfft(tip)) / n
    top = np.argsort(mag[1:])[::-1][:4] + 1
    print("  輝度スペクトルの上位 4 線 [Hz]:", ", ".join("%.2f" % fr[k] for k in top))
    pk = spectrum_peak(tip, clip["fps"], FN[0], 1.0)
    alias = clip["flicker_alias"]
    a_mode = line_amplitude(tip, clip["fps"], FN[0])
    a_flk = line_amplitude(tip, clip["fps"], alias)
    print("  f_1: 真値 %.3f Hz → ピーク %.3f Hz(誤差 %+.3f Hz)" % (FN[0], pk["f"], pk["f"] - FN[0]))
    print("  照明 %.0f Hz の折り返し(予測 |%.0f − k·fps| = %.1f Hz)の線 %.4f、モード 1 の線 %.4f"
          " → 比 %.2f" % (FLICKER_HZ, FLICKER_HZ, alias, a_flk, a_mode, a_flk / a_mode))
    macs = []
    for m in range(3):
        pkm = spectrum_peak(tip, clip["fps"], FN[m], max(1.0, 0.1 * FN[m]))
        phi = mode_shape(z["u"], clip["fps"], pkm["f"])
        macs.append(mac(phi, clip["phi_true"][m]))
    print("  輝度から作ったモード形状の MAC: モード 1 %.2f / 2 %.2f / 3 %.2f"
          "(縁の輝度勾配の符号が模様で入れ替わる)" % tuple(macs))
    figs.save_plot("zero_point_spectrum",
                   [("縁 1 画素の輝度", fr[1:], mag[1:])],
                   xlabel="周波数 [Hz]", ylabel="輝度の片側振幅",
                   title="ゼロ点: 輝度 FFT(%.1f Hz の線は照明 %.0f Hz の折り返し)" % (alias, FLICKER_HZ),
                   xlim=(0, clip["fps"] / 2))
    return {"f1": pk["f"], "flicker_ratio": a_flk / a_mode, "mac": macs, "alias": alias}


# --------------------------------------------------------------------------- #
# 2. 基準条件の同定 —— f は当たる、ζ は方法で 3 通り                            #
# --------------------------------------------------------------------------- #
def section_identify(clip: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) 位相法と PIV で f_n / ζ_n / MAC_n(A_1 = %.2f px、全妨害入り、手ぶれ補正あり)" % clip["a1"])
    print("=" * 78)
    ph = stations_phase(clip)
    pv = stations_piv(clip)
    r_ph = identify(ph, clip["fps"], clip["phi_true"])
    r_pv = identify(pv, clip["fps"], pv["phi_true"])
    print("  真値:  f = %.3f / %.3f / %.3f Hz,  ζ = %.4f / %.4f / %.4f" % (*FN, *ZETA))
    rows = []
    for name, r in (("位相法", r_ph), ("PIV", r_pv)):
        print("  %s" % name)
        for n in range(3):
            print("    モード %d: f %.3f Hz (%+.3f)  ζ 半値幅 %.4f / 包絡線 %.4f / 当てはめ %.4f  MAC %.3f"
                  % (n + 1, r["f"][n], r["f"][n] - FN[n], r["zeta_hp"][n], r["zeta_env"][n],
                     r["zeta_fit"][n], r["mac"][n]))
            rows.append([name, str(n + 1), "%.3f" % FN[n], "%+.3f" % (r["f"][n] - FN[n]),
                         "%.4f" % ZETA[n], "%.4f" % r["zeta_hp"][n], "%.4f" % r["zeta_env"][n],
                         "%.4f" % r["zeta_fit"][n], "%.3f" % r["mac"][n]])
    # 半値幅の分解能の下限(矩形窓の主ローブ -3 dB 幅 ≈ 0.886/T)
    floor = 0.886 / DUR / (2 * FN[0])
    print("  ★半値幅の ζ_1 は真値の %.1f 倍。予測: 窓長 %.0f s の分解能下限 0.886/T/(2 f_1) = %.4f"
          % (r_ph["zeta_hp"][0] / ZETA[0], DUR, floor))
    # 手ぶれの推定精度
    sx, sy = clip["shake"]
    err_ph = np.sqrt(np.mean((ph["bg"] - ph["bg"].mean() - (sy - sy.mean())) ** 2))
    err_pv = np.sqrt(np.mean((pv["bg"] - pv["bg"].mean() - (sy - sy.mean())) ** 2))
    print("  手ぶれ(背景から)の RMS 誤差: 位相法 %.4f px / PIV %.4f px(手ぶれの RMS %.3f px)"
          % (err_ph, err_pv, sy.std()))
    tip_err_ph = np.sqrt(np.mean((ph["u"][:, -1] - ph["u"][:, -1].mean()
                                  - (clip["w_true"][:, -1] - clip["w_true"][:, -1].mean())) ** 2))
    print("  先端変位の RMS 誤差(位相法、手ぶれ補正後)%.4f px" % tip_err_ph)

    figs.save_table("identification",
                    ["推定器", "モード", "f 真値 Hz", "f 誤差 Hz", "ζ 真値", "ζ 半値幅", "ζ 包絡線",
                     "ζ 当てはめ", "MAC"], rows,
                    title="同じ時系列から出した ζ が方法で 3 通り(f は全部当たる)")
    t = clip["t"]
    figs.save_plot("tip_waveform",
                   [("真値", t, clip["w_true"][:, -1]),
                    ("位相法(手ぶれ補正後)", t, ph["u"][:, -1] - ph["u"][:, -1].mean()),
                    ("PIV", t, pv["u"][:, -1] - pv["u"][:, -1].mean())],
                   xlabel="時間 [s]", ylabel="先端の変位 [px]",
                   title="先端の変位波形(3 モードの自由減衰)")
    n = clip["T"]
    fr = np.fft.rfftfreq(n * 4, 1.0 / clip["fps"])
    sp = 2 * np.abs(np.fft.rfft(ph["u"][:, -1] - ph["u"][:, -1].mean(), n * 4)) / n
    figs.save_plot("tip_spectrum",
                   [("位相法の先端変位", fr[1:], sp[1:])],
                   xlabel="周波数 [Hz]", ylabel="片側振幅 [px]",
                   title="変位スペクトル: 3.00 / 18.80 / 52.64 Hz の 3 モード")
    xs = (clip["stations"] - X0) / L
    figs.save_plot("mode_shapes",
                   [("φ1 真値", xs, clip["phi_true"][0]), ("φ1 位相法", xs, r_ph["phi1"]),
                    ("φ2 真値", xs, clip["phi_true"][1]), ("φ2 位相法", xs, r_ph["phi2"]),
                    ("φ3 位相法", xs, r_ph["phi3"])],
                   xlabel="固定端からの距離 x/L", ylabel="モード形状(先端 = ±1)",
                   title="モード形状の同定(MAC %.3f / %.3f / %.3f)" % tuple(r_ph["mac"]))
    return {"phase": r_ph, "piv": r_pv, "floor": floor, "shake_err": (err_ph, err_pv),
            "tip_err": tip_err_ph, "wrap": ph["wrap_limit_px"]}


# --------------------------------------------------------------------------- #
# 3. 崖 —— 振幅を掃引すると壊れる順番が量ごとに違う                             #
# --------------------------------------------------------------------------- #
AMPS = (0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0)


def section_amplitude_sweep(wrap_limit: float) -> dict:
    print("\n" + "=" * 78)
    print("3) 振幅の掃引 A_1 = %s px —— f / ζ / MAC はどこで壊れるか" % ", ".join("%g" % a for a in AMPS))
    print("=" * 78)
    print("  予想: 位相法は返り値 wrap_limit_px = %.3f px で位相が巻いて壊れる。PIV は小振幅で"
          "サブピクセルの床に沈む。" % wrap_limit)
    print("  A_1 px  推定器  f_1 誤差 Hz  ζ_1 包絡線  ζ_1 当てはめ   MAC_1   MAC_2   MAC_3")
    res = {"phase": [], "piv": []}
    for a1 in AMPS:
        clip = make_clip(a1)
        for name, est, phi in (("phase", stations_phase(clip), clip["phi_true"]),):
            r = identify(est, clip["fps"], phi)
            res[name].append(r)
        pv = stations_piv(clip)
        res["piv"].append(identify(pv, clip["fps"], pv["phi_true"]))
        for name, label in (("phase", "位相法"), ("piv", "PIV")):
            r = res[name][-1]
            print("  %5.2f   %-6s  %+9.3f    %8.4f    %8.4f     %.3f   %.3f   %.3f"
                  % (a1, label, r["f"][0] - FN[0], r["zeta_env"][0], r["zeta_fit"][0], *r["mac"]))

    def first_ok(name, key, ok):
        for a1, r in zip(AMPS, res[name]):
            if ok(r):
                return a1
        return np.nan
    thr = {}
    for name, label in (("phase", "位相法"), ("piv", "PIV")):
        thr[name] = {
            "f": first_ok(name, "f", lambda r: abs(r["f"][0] - FN[0]) < 0.05),
            "zeta": first_ok(name, "z", lambda r: abs(r["zeta_fit"][0] / ZETA[0] - 1) < 0.25),
            "mac2": first_ok(name, "m2", lambda r: r["mac"][1] > 0.95),
            "mac3": first_ok(name, "m3", lambda r: r["mac"][2] > 0.95)}
        print("  %s が合格し始める振幅 [px]: f_1(±0.05 Hz)%g / ζ_1(±25 %%)%g / MAC_2>0.95 %g / MAC_3>0.95 %g"
              % (label, thr[name]["f"], thr[name]["zeta"], thr[name]["mac2"], thr[name]["mac3"]))
    big = res["phase"][-1]
    print("  ★位相法は A_1 = %g px(先端 %.2f px、wrap_limit_px の %.1f 倍)でも f_1 誤差 %+.3f Hz、"
          "MAC_1 %.3f —— 予想の崖は来なかった。" % (AMPS[-1], AMPS[-1] * sum(AMP_RATIO),
                                                   AMPS[-1] * sum(AMP_RATIO) / wrap_limit,
                                                   big["f"][0] - FN[0], big["mac"][0]))
    figs.save_plot("cliff_frequency",
                   [("位相法", AMPS, [abs(r["f"][0] - FN[0]) for r in res["phase"]]),
                    ("PIV", AMPS, [abs(r["f"][0] - FN[0]) for r in res["piv"]])],
                   xlabel="モード 1 の先端振幅 A_1 [px]", ylabel="|f_1 の誤差| [Hz]",
                   title="f_1 は 0.02 px でも壊れない", kinds=["line", "line"])
    figs.save_plot("cliff_damping",
                   [("位相法 包絡線", AMPS, [r["zeta_env"][0] / ZETA[0] for r in res["phase"]]),
                    ("位相法 当てはめ", AMPS, [r["zeta_fit"][0] / ZETA[0] for r in res["phase"]]),
                    ("PIV 当てはめ", AMPS, [r["zeta_fit"][0] / ZETA[0] for r in res["piv"]]),
                    ("真値 (=1)", AMPS, [1.0] * len(AMPS))],
                   xlabel="モード 1 の先端振幅 A_1 [px]", ylabel="ζ_1 推定 / 真値",
                   title="ζ_1 は f_1 より先に壊れる(雑音の床が包絡線を平らにする)")
    figs.save_plot("cliff_mac",
                   [("位相法 MAC_2", AMPS, [r["mac"][1] for r in res["phase"]]),
                    ("位相法 MAC_3", AMPS, [r["mac"][2] for r in res["phase"]]),
                    ("PIV MAC_2", AMPS, [r["mac"][1] for r in res["piv"]]),
                    ("PIV MAC_3", AMPS, [r["mac"][2] for r in res["piv"]])],
                   xlabel="モード 1 の先端振幅 A_1 [px]", ylabel="MAC",
                   title="高次モードの形状が最初に崩れる")
    return {"res": res, "thr": thr}


# --------------------------------------------------------------------------- #
# 4. fps の掃引 —— Nyquist の折り返しと照明ちらつきの衝突                        #
# --------------------------------------------------------------------------- #
FPS_LIST = (128.0, 64.0, 48.5, 40.0, 32.0, 24.0)


def _alias(f: float, fps: float) -> float:
    k = round(f / fps)
    return abs(f - k * fps)


def section_fps_sweep() -> dict:
    print("\n" + "=" * 78)
    print("4) fps の掃引 —— モード 2(%.2f Hz)の折り返しと照明 %.0f Hz の折り返し" % (FN[1], FLICKER_HZ))
    print("=" * 78)
    print("  予測: 折り返し = |f − k·fps|。Nyquist fps/2 を切るとモード 2 は偽の低周波に化ける。")
    print("  fps    Nyq   f_2 予測  f_2 実測(位相法)  ちらつき予測  輝度の線/モード1  dy の線/モード1")
    rows, out = [], []
    for fps in FPS_LIST:
        clip = make_clip(0.1, fps=fps)
        ph = stations_phase(clip)
        tip = ph["u"][:, -1]
        pred2 = _alias(FN[1], fps)
        # 予測位置の ±1 Hz で最大の線を読む
        pk2 = spectrum_peak(tip, fps, pred2, 1.0)
        fa = clip["flicker_alias"]
        zp = zero_point(clip)["u"][:, -1]
        r_b = line_amplitude(zp, fps, fa) / line_amplitude(zp, fps, FN[0])
        r_d = line_amplitude(tip, fps, fa) / line_amplitude(tip, fps, FN[0])
        out.append({"fps": fps, "pred2": pred2, "meas2": pk2["f"], "alias": fa,
                    "ratio_b": r_b, "ratio_d": r_d, "clip": clip, "ph": ph})
        print("  %5.1f  %5.2f  %7.2f   %7.2f (%+.2f)      %6.2f        %6.3f            %6.4f"
              % (fps, fps / 2, pred2, pk2["f"], pk2["f"] - pred2, fa, r_b, r_d))
        rows.append(["%.1f" % fps, "%.2f" % (fps / 2), "%.2f" % pred2, "%.2f" % pk2["f"],
                     "%.2f" % fa, "%.3f" % r_b, "%.4f" % r_d])
    figs.save_table("fps_sweep",
                    ["fps", "Nyquist Hz", "f_2 折返し予測 Hz", "f_2 実測 Hz", "照明の折返し Hz",
                     "輝度: ちらつき線/モード1", "位相法 dy: ちらつき線/モード1"], rows,
                    title="Nyquist の折り返しは予測どおり。照明は fps 48.5 で f_1 に重なる")

    # ★衝突: fps 48.5 では照明の折り返しが f_1 = 3.00 Hz にぴったり乗る
    col = [o for o in out if o["fps"] == 48.5][0]
    clip, ph = col["clip"], col["ph"]
    fps = 48.5
    zp = zero_point(clip)["u"][:, -1]
    z_b = damping_envelope(zp, fps, FN[0], 1.5)
    z_d = damping_envelope(ph["u"][:, -1], fps, FN[0], 1.5)
    clip_nf = make_clip(0.1, fps=fps, flicker=False)
    z_b_nf = damping_envelope(zero_point(clip_nf)["u"][:, -1], fps, FN[0], 1.5)
    z_d_nf = damping_envelope(stations_phase(clip_nf)["u"][:, -1], fps, FN[0], 1.5)
    print("  ★fps 48.5: 照明の折り返し %.2f Hz = f_1。包絡線から出す ζ_1(真値 %.3f):" % (col["alias"], ZETA[0]))
    print("     輝度のゼロ点  ちらつき有 %.4f / 無 %.4f   (減衰しない線が乗ると ζ → 0)" % (z_b, z_b_nf))
    print("     位相法        ちらつき有 %.4f / 無 %.4f   (乗算のちらつきは位相を動かさない)" % (z_d, z_d_nf))
    n = clip["T"]
    fr = np.fft.rfftfreq(n * 4, 1.0 / fps)
    figs.save_plot("flicker_collision",
                   [("輝度(ちらつき有)", fr[1:], 2 * np.abs(np.fft.rfft(zp, n * 4))[1:] / n / max(np.abs(zp).max(), 1e-9)),
                    ("位相法 dy(ちらつき有)", fr[1:],
                     2 * np.abs(np.fft.rfft(ph["u"][:, -1] - ph["u"][:, -1].mean(), n * 4))[1:] / n
                     / max(np.abs(ph["u"][:, -1]).max(), 1e-9))],
                   xlabel="周波数 [Hz]", ylabel="振幅(最大値で正規化)",
                   title="fps 48.5: 照明 100 Hz の折り返しが 3.00 Hz = f_1 に重なる")
    return {"out": out, "zeta_collision": (z_b, z_b_nf, z_d, z_d_nf)}


# --------------------------------------------------------------------------- #
# 5. 対照群 —— 1 要因ずつ止める                                                 #
# --------------------------------------------------------------------------- #
def section_controls() -> dict:
    print("\n" + "=" * 78)
    print("5) 対照群(A_1 = 0.1 px、位相法)—— 全部入りから 1 要因ずつ止める")
    print("=" * 78)
    conds = [("全部入り", {}), ("雑音なし", {"noise": 0.0}), ("ちらつきなし", {"flicker": False}),
             ("手ぶれなし", {"shake": False}), ("ローリングシャッターなし", {"rolling": False})]
    print("  条件                       f_1 誤差 Hz  ζ_1 当てはめ  ζ_2 当てはめ  MAC_1   MAC_2   MAC_3  モード3振幅 px")
    rows, out = [], {}
    for name, kw in conds:
        clip = make_clip(0.1, **kw)
        r = identify(stations_phase(clip), clip["fps"], clip["phi_true"])
        out[name] = r
        print("  %-24s  %+9.3f    %8.4f     %8.4f    %.3f   %.3f   %.3f    %.4f"
              % (name, r["f"][0] - FN[0], r["zeta_fit"][0], r["zeta_fit"][1], *r["mac"], r["amp"][2]))
        rows.append([name, "%+.3f" % (r["f"][0] - FN[0]), "%.4f" % r["zeta_fit"][0],
                     "%.4f" % r["zeta_fit"][1], "%.3f" % r["mac"][0], "%.3f" % r["mac"][1],
                     "%.3f" % r["mac"][2], "%.4f" % r["amp"][2]])
    # 手ぶれを引かない(補正を止める)
    clip = make_clip(0.1)
    r = identify(stations_phase(clip, correct_shake=False), clip["fps"], clip["phi_true"])
    out["手ぶれ補正なし"] = r
    print("  %-24s  %+9.3f    %8.4f     %8.4f    %.3f   %.3f   %.3f    %.4f"
          % ("手ぶれ補正なし", r["f"][0] - FN[0], r["zeta_fit"][0], r["zeta_fit"][1], *r["mac"], r["amp"][2]))
    rows.append(["手ぶれ補正なし", "%+.3f" % (r["f"][0] - FN[0]), "%.4f" % r["zeta_fit"][0],
                 "%.4f" % r["zeta_fit"][1], "%.3f" % r["mac"][0], "%.3f" % r["mac"][1],
                 "%.3f" % r["mac"][2], "%.4f" % r["amp"][2]])
    # ローリングシャッターの予測: 梁 16 行ぶんの時刻差 Δt = 16·τ、モード 3 の位相差 ω3·Δt、
    # 行平均の振幅減衰 sinc(ω3·Δt/2)
    dt = (2 * HB - 4) * RS_FRAC / FPS / H
    ph3 = 2 * np.pi * FN[2] * dt
    gain = np.sin(ph3 / 2) / (ph3 / 2)
    a3_on, a3_off = out["全部入り"]["amp"][2], out["ローリングシャッターなし"]["amp"][2]
    print("  ローリングシャッターの予測: 梁の行をまたぐ時刻差 %.2f ms → モード 3 の位相差 %.2f rad、"
          "行平均の振幅は %.3f 倍(実測 %.3f 倍)" % (1e3 * dt, ph3, gain, a3_on / a3_off))
    print("  ★手ぶれを引かないと ζ_1 は %.4f → %.4f(%.1f Hz と %.1f Hz の手ぶれが帯域内に居る)"
          % (out["全部入り"]["zeta_fit"][0], r["zeta_fit"][0], SHAKE[0][0], SHAKE[1][0]))
    figs.save_table("controls", ["条件", "f_1 誤差 Hz", "ζ_1 当てはめ", "ζ_2 当てはめ", "MAC_1",
                                 "MAC_2", "MAC_3", "モード 3 振幅 px"], rows,
                    title="対照群: 効いたのは手ぶれ(ζ)と雑音(MAC_3)")
    return {"out": out, "rs_gain_pred": gain, "rs_gain_meas": a3_on / a3_off}


# --------------------------------------------------------------------------- #
# 場面の図                                                                     #
# --------------------------------------------------------------------------- #
def scene_figures(clip: dict) -> None:
    v = clip["video"]
    big = make_clip(2.0, noise=0.0, flicker=False, shake=False, rolling=False)
    fld = fs.ledger.phase_displacement(v, BAND[0], BAND[1], clip["fps"])
    k = int(np.argmax(np.abs(clip["w_true"][:, -1])))
    figs.save_grid("scene",
                   [v[0], big["video"][0], fld["dy"][k] * fld["valid"], fld["weight"]],
                   ["フレーム 0(A_1 = %.2f px、雑音・ちらつき入り)" % clip["a1"],
                    "同じ梁を A_1 = 2 px で(妨害なし、見える大きさ)",
                    "位相法の dy 場 [px](先端が最大のフレーム)",
                    "位相法の重み |z|²(模様の無い所は票を持たない)"],
                   title="片持ち梁の振動を動画から測る場面(%d×%d px、%.0f fps、%.0f s)"
                   % (W, H, clip["fps"], DUR), ncols=2, signed=[False, False, True, False])
    frames = [v[i] for i in range(0, 8)]
    figs.save_grid("frames", frames, ["t = %.3f s" % (i / clip["fps"]) for i in range(8)],
                   title="最初の 8 フレーム(モード 3 の 1 周期 ≈ 2.4 フレーム)", ncols=4)


# --------------------------------------------------------------------------- #
# 6. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("6) 道具の穴(この PoC で motionmag / piv / dsp 族を使ってみて)")
    print("=" * 78)
    # (a) 台帳の piv_cross_correlate は info(窓中心・peak_ratio・valid_fraction)を落とす
    a = np.random.default_rng(0).random((16, 64))
    r = fs.ledger.piv_cross_correlate(a, a, window=16)
    assert isinstance(r, np.ndarray) and r.ndim == 3, type(r)
    print("  (a) fs.ledger.piv_cross_correlate は (flow, info) の flow だけを返す。窓中心"
          " rows/cols・peak_ratio・valid_fraction が公開経路から取れず、窓中心を呼び手が組んだ。")
    # (b) 減衰比を出す口が無い(半値幅・対数減衰率・当てはめ)
    assert not any(hasattr(fs, n) or hasattr(fs.ledger, n)
                   for n in ("damping_ratio", "log_decrement", "half_power_bandwidth"))
    print("  (b) 減衰比 ζ(半値幅 / 対数減衰率 / 減衰正弦波の当てはめ)を出す op が無い。"
          "この PoC の主題そのものなので自前で書いた。")
    # (c) MAC / モード形状の抽出が無い
    assert not any(hasattr(fs, n) or hasattr(fs.ledger, n) for n in ("modal_assurance", "mac"))
    print("  (c) MAC(modal assurance criterion)と測点列の複素振幅からモード形状を組む op が無い。")
    # (d) 1-D 時系列の理想帯域通過は temporal_bandpass を (T,1,1) に畳んで代用した
    x = np.sin(2 * np.pi * 3 * np.arange(256) / 128.0)
    y = bandpass_1d(x, 128.0, 2.0, 4.0)
    assert np.abs(y - x).max() < 1e-12
    print("  (d) 1-D の理想帯域通過が無い(dsp.bandpass は Butterworth で過渡応答が減衰に混ざる)。"
          "temporal_bandpass に (T,1,1) を渡して代用した —— 動く(誤差 %.0e)が名前が違う。" % np.abs(y - x).max())
    # (e) スペクトルのピークをサブビンで読む口(ゼロ埋め + 放物線補間)が無い
    print("  (e) スペクトルの線をサブビンで読む(ゼロ埋め + 放物線補間、半値幅)op が無い。"
          "dsp.spectrum は生の |rfft| を返すだけ。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.time()
    print("片持ち梁 %d px、f_n = %.2f / %.2f / %.2f Hz、ζ_n = %s、fps %.0f、%.0f s(%d フレーム)"
          % (L, *FN, ZETA, FPS, DUR, int(DUR * FPS)))
    base = make_clip(0.1)
    scene_figures(base)
    r1 = section_zero_point(base)
    r2 = section_identify(base)
    r3 = section_amplitude_sweep(r2["wrap"])
    r4 = section_fps_sweep()
    r5 = section_controls()
    section_tool_gaps()

    # ---- 所見を固定する検査 ------------------------------------------------ #
    ph, pv = r2["phase"], r2["piv"]
    assert all(abs(ph["f"][n] - FN[n]) < 0.05 for n in range(3)), ph["f"]
    assert all(abs(pv["f"][n] - FN[n]) < 0.05 for n in range(3)), pv["f"]
    assert abs(ph["zeta_fit"][0] / ZETA[0] - 1) < 0.15, ph["zeta_fit"]
    assert ph["zeta_hp"][0] > 2.5 * ZETA[0], "半値幅の分解能下限が消えた"
    assert abs(ph["zeta_hp"][0] - r2["floor"]) < 0.4 * r2["floor"]
    assert ph["mac"][0] > 0.99 and ph["mac"][1] > 0.95
    assert r1["mac"][1] < 0.8, "輝度のモード形状が符号を持つようになった"
    # 崖: 位相法は wrap_limit の外でも壊れない / 高次 MAC が先に落ちる
    thr = r3["thr"]
    big = r3["res"]["phase"][-1]
    assert abs(big["f"][0] - FN[0]) < 0.05 and big["mac"][0] > 0.99, "位相法が大振幅で壊れた"
    assert thr["phase"]["mac3"] >= thr["phase"]["f"], thr
    assert thr["phase"]["zeta"] >= thr["phase"]["f"], thr
    # fps: 折り返しは予測どおり
    for o in r4["out"]:
        assert abs(o["meas2"] - o["pred2"]) < 0.1, (o["fps"], o["meas2"], o["pred2"])
    zb, zbn, zd, zdn = r4["zeta_collision"]
    assert zb < 0.5 * ZETA[0] and abs(zd / ZETA[0] - 1) < 0.25, (zb, zd)
    # 対照群: 手ぶれを引かないと ζ_1 が動く
    c = r5["out"]
    assert abs(c["手ぶれ補正なし"]["zeta_fit"][0] - c["全部入り"]["zeta_fit"][0]) > 0.003
    assert abs(r5["rs_gain_meas"] - r5["rs_gain_pred"]) < 0.05

    print("\n所要 %.1f s" % (time.time() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", figs.errors())
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
