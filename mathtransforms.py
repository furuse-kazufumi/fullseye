# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mathtransforms — フーリエ以外の積分変換(Abel / Hankel / Laplace)と s 領域の線形系。

2026-10-03 の棚卸しで、FFT・DCT・Radon・Riesz は揃っているのに **Laplace 変換の系統が 1 本も無く**、
Abel・Hankel も無いことが分かった(全 2,590 op + facade 3,274 名を綴りを変えて検索)。
`laplace` op は HALCON のラプラシアン(2 階微分)で、`transfer_function` 系は周波数領域の H(f) —— どちらも別物。

ここに置くもの(すべて numpy + scipy だけ):

* **Abel 変換** —— 軸対称な分布 f(r) を横から見た投影 A(y) = 2∫_y^R f(r) r / √(r²−y²) dr。
  炎・プラズマ・速度マップ像は「投影しか撮れない軸対称物体」で、逆 Abel が断層化そのもの。
  逆変換は 2 通り持つ(微分の求積 / 殻を剥く)—— 1 つしか無い逆問題は答えを検算できない。
* **Hankel 変換** —— 軸対称な関数の 2 次元フーリエ変換は、動径の Hankel 変換 1 本に落ちる。
  quasi-discrete Hankel transform(Guizar-Sicairos & Gutiérrez-Vega 2004)で、核が**対合**(2 回で恒等)。
* **Laplace 変換と s 領域の線形系** —— 有理伝達関数 H(s) = num/den の極・零点、周波数応答(Bode)、
  インパルス/ステップ応答、Tustin(双一次)変換による離散化、数値逆ラプラス(固定 Talbot)。
  応答は「部分分数」でなく**拡大行列の指数関数**で厳密に解く(重根・積分器でも分岐が要らない)。

門(閉じた式と定理だけ。記憶から写した公表値は使わない):
  Abel: ガウス exp(−r²/σ²) ↔ √π σ exp(−y²/σ²) / Hankel: exp(−π r²) は自己双対、核 T·T = I /
  Laplace: 変換対(1/(s+a) ↔ e^{−at} など)と、Talbot ↔ 行列指数の 2 経路一致 / Tustin: 前歪みした周波数で応答が一致。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import interpolate, linalg, special

__all__ = [
    "abel_transform", "abel_inverse", "abel_inverse_image", "abel_revolve",
    "hankel_transform",
    "tf_poles_zeros", "tf_freq_response", "tf_impulse_response", "tf_step_response",
    "tf_bilinear", "laplace_inverse_talbot", "laplace_inverse_func",
    "dct_transform", "wavelet_filters", "dwt_transform", "dwt_inverse",
]


# ---------------------------------------------------------------------------- #
# Abel
# ---------------------------------------------------------------------------- #
def _radial_grid(f, dr):
    f = np.asarray(f, dtype=np.float64).ravel()
    if f.size < 4:
        raise ValueError("abel: 動径の標本は 4 点以上が要る(得たのは %d)" % f.size)
    if not np.all(np.isfinite(f)):
        raise ValueError("abel: 入力に NaN/inf がある")
    dr = float(dr)
    if not dr > 0:
        raise ValueError("abel: dr は正(得たのは %r)" % dr)
    return f, dr, np.arange(f.size) * dr


def abel_transform(f, dr: float = 1.0, *, n_quad: int = 64) -> np.ndarray:
    """軸対称な分布 f(r)(r = 0, dr, 2dr, … の標本)を投影 A(y) に写す(前向き Abel 変換)。

    A(y) = 2 ∫_y^R f(r) r / √(r² − y²) dr。r = √(y² + u²) と置くと A(y) = 2 ∫_0^{√(R²−y²)} f(√(y²+u²)) du
    になり、y = r の特異点が消える(被積分関数は滑らか)。f は 3 次スプラインで補間し、
    u の積分は Gauss–Legendre ``n_quad`` 点。R の外では f = 0 とみなす。

    門: f = exp(−r²/σ²) なら A(y) = √π σ exp(−y²/σ²)(R が十分大きいとき)。
    返り値は f と同じ長さ・同じ格子(y = 0, dr, 2dr, …)。
    """
    f, dr, r = _radial_grid(f, dr)
    R = r[-1]
    spl = interpolate.CubicSpline(r, f, bc_type=((1, 0.0), "not-a-knot"))   # f'(0) = 0(軸対称)
    x, w = np.polynomial.legendre.leggauss(int(n_quad))
    out = np.zeros_like(f)
    for i, y in enumerate(r):
        U = math.sqrt(max(R * R - y * y, 0.0))
        if U == 0.0:
            continue
        u = 0.5 * U * (x + 1.0)
        out[i] = 2.0 * 0.5 * U * float(np.dot(w, spl(np.sqrt(y * y + u * u))))
    return out


def _onion_matrix(n, dr):
    """殻(半径 [r−dr/2, r+dr/2] で f 一定)を弦の長さで投影する上三角行列。"""
    edges = (np.arange(n + 1) - 0.5).clip(min=0.0) * dr
    y = np.arange(n) * dr
    Y = y[:, None]
    lo, hi = edges[None, :-1], edges[None, 1:]
    chord = lambda a: np.sqrt(np.clip(a * a - Y * Y, 0.0, None))        # noqa: E731
    return 2.0 * (chord(hi) - chord(np.maximum(lo, Y)))


def abel_inverse(A, dr: float = 1.0, *, method: str = "derivative", n_quad: int = 64) -> np.ndarray:
    """投影 A(y) から軸対称な分布 f(r) を戻す(逆 Abel 変換 = 軸対称物体の断層化)。

    * ``"derivative"`` —— f(r) = −(1/π) ∫_r^R A'(y) / √(y² − r²) dy。y = √(r² + u²) と置いて特異点を消し、
      A を 3 次スプラインで微分する。滑らかな投影には精度が高いが、**微分が雑音を増幅する**:
      雑音の誤差は標本間隔 dr に反比例して増える(2026-10-03 実測、雑音 1%: 標本数 80 → 640 で
      平均誤差 0.027 → 0.237、両対数の傾き ≈ 1)。粗い格子ではこちらが良い。
    * ``"onion"`` —— 殻を剥く: f を半径 dr の殻ごとに一定とみなし、弦の長さの上三角行列を外側から解く。
      解像度は殻の幅で決まり、微分を取らないぶん雑音の増え方が緩い(同じ実測で 0.036 → 0.100、傾き ≈ 1/2)。
      **細かい格子の実測ではこちら**(n=640 で微分の 2.4 分の 1)、粗い格子(n≈80)では逆転する。

    2 つは独立な離散化なので、**同じ投影に両方を当てて食い違いを見る**のが検算になる。
    門: A(y) = √π σ exp(−y²/σ²) から f(r) = exp(−r²/σ²)。
    """
    A, dr, y = _radial_grid(A, dr)
    if method == "onion":
        M = _onion_matrix(A.size, dr)
        return linalg.solve_triangular(M, A, lower=False)
    if method != "derivative":
        raise ValueError("abel_inverse: method は 'derivative' か 'onion'(得たのは %r)" % (method,))
    R = y[-1]
    spl = interpolate.CubicSpline(y, A, bc_type=((1, 0.0), "not-a-knot"))
    dA = spl.derivative()
    x, w = np.polynomial.legendre.leggauss(int(n_quad))
    out = np.zeros_like(A)
    for i, r in enumerate(y):
        U = math.sqrt(max(R * R - r * r, 0.0))
        if U == 0.0:
            continue
        u = 0.5 * U * (x + 1.0)
        yy = np.sqrt(r * r + u * u)
        g = dA(yy) / yy                                    # A'(y)/y は y→0 でも有限(A は偶関数)
        out[i] = -(1.0 / math.pi) * 0.5 * U * float(np.dot(w, g))
    return out


def abel_inverse_image(image, dr: float = 1.0, *, center: float | None = None, method: str = "onion") -> dict:
    """軸対称な物体を横から撮った**画像**(縦 = 対称軸の向き、横 = 軸からの距離)を、行ごとに逆 Abel して断面画像にする。

    炎・プラズマ・噴流の写真は、奥行き方向に足し合わさった投影しか写らない。各行を中心列で左右に分け、
    2 つの半分を平均してから(左右の非対称を均す)逆 Abel する。``center`` は対称軸の列(既定 = 明るさの重心、
    行ごとではなく画像全体で 1 本)。返り値 ``{"slice", "center", "asymmetry"}`` —— slice は (H, R) の f(z, r)、
    asymmetry は左右の半分の差の大きさ(0 に近いほど軸対称の仮定が成り立つ)。
    門: 3-D のガウスの塊の投影から、断面のガウスが戻る(閉じた式)。
    """
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] < 8 or not np.all(np.isfinite(a)):
        raise ValueError("abel_inverse_image: 有限な 2-D 画像(横 8 画素以上)")
    H, W = a.shape
    if center is None:
        prof = np.clip(a, 0, None).sum(axis=0)
        center = float(np.sum(prof * np.arange(W)) / max(prof.sum(), 1e-300))
    c = float(center)
    R = int(min(c, W - 1 - c))
    if R < 4:
        raise ValueError("abel_inverse_image: 対称軸が端に寄りすぎ(半径 %d 画素)" % R)
    xs = np.arange(R + 1, dtype=np.float64)
    cols = np.arange(W, dtype=np.float64)
    right = np.stack([np.interp(c + xs, cols, row) for row in a])
    left = np.stack([np.interp(c - xs, cols, row) for row in a])
    half = 0.5 * (left + right)
    asym = float(np.abs(left - right).mean() / max(np.abs(half).mean(), 1e-300))
    sl = np.stack([abel_inverse(row, dr, method=method) for row in half])
    return {"slice": sl, "center": c, "asymmetry": asym}


def abel_revolve(slice_rows, dr: float = 1.0) -> np.ndarray:
    """断面 f(z, r)((H, R)、r = 0, dr, …)を対称軸のまわりに回して 3-D ボリューム (H, 2R−1, 2R−1) にする。

    ``abel_inverse_image`` と組むと、1 枚の写真から軸対称な物体の 3-D の分布が戻る。
    門: できたボリュームを横に足し合わせる(投影する)と、元の投影画像に戻る(往復)。
    """
    s = np.asarray(slice_rows, dtype=np.float64)
    if s.ndim != 2 or s.shape[1] < 2 or not np.all(np.isfinite(s)):
        raise ValueError("abel_revolve: (H, R) の有限な断面")
    H, R = s.shape
    g = np.arange(-(R - 1), R, dtype=np.float64)
    rr = np.hypot(g[:, None], g[None, :])
    r = np.arange(R, dtype=np.float64)
    vol = np.stack([np.interp(rr, r, row, right=0.0) for row in s])
    return vol


# ---------------------------------------------------------------------------- #
# Hankel(quasi-discrete、Guizar-Sicairos & Gutiérrez-Vega 2004)
# ---------------------------------------------------------------------------- #
def hankel_transform(r, f, *, r_max: float | None = None, order: int = 0, n: int = 256) -> dict:
    """p 次の Hankel 変換 F(ν) = 2π ∫_0^∞ f(r) J_p(2πνr) r dr を quasi-discrete 法で。

    ``(r, f)`` は動径の標本(r は昇順)。標本点 r_k へは線形補間で載せ、``r_max``(既定 = r の最大値)の外は 0。
    ``f`` に呼び出し可能を渡すと、標本点で直接評価する(``r`` は無視して ``r_max`` を必ず渡す)。
    標本点は r_k = j_k R / S(j_k は J_p の k 番目の零点、S = j_{n+1})、周波数 ν_k = j_k / (2πR)。
    この変換は核 T が**対合**(T·T = I)なので、同じ関数で逆変換もできる(``F`` を f として渡す)。

    門: exp(−π r²) は自己双対(F(ν) = exp(−π ν²))。0 次の Hankel 変換は軸対称な関数の
    2 次元フーリエ変換の動径断面に等しい。
    返り値: ``{"r", "f", "nu", "F", "T_involution_error"}``(最後は ‖T·T − I‖_max)。
    """
    p = int(order)
    if p < 0:
        raise ValueError("hankel_transform: order は 0 以上")
    n = int(n)
    if n < 8:
        raise ValueError("hankel_transform: n は 8 以上")
    if r_max is None:
        if callable(f):
            raise ValueError("hankel_transform: f が呼び出し可能なら r_max を渡す")
        r_max = float(np.max(r))
    R = float(r_max)
    if not R > 0:
        raise ValueError("hankel_transform: r_max は正")
    j = special.jn_zeros(p, n + 1)
    S = j[-1]
    jk = j[:-1]
    rin = r
    r = jk * R / S
    nu = jk / (2.0 * math.pi * R)
    V = S / (2.0 * math.pi * R)
    if callable(f):
        fr = np.asarray(f(r), dtype=np.float64)
    else:
        rr = np.asarray(rin, dtype=np.float64).ravel()
        ff = np.asarray(f, dtype=np.float64).ravel()
        if rr.shape != ff.shape or rr.size < 2 or np.any(np.diff(rr) <= 0):
            raise ValueError("hankel_transform: r と f は同じ長さ(2 以上)で r は狭義単調増加")
        fr = np.interp(r, rr, ff, right=0.0)
    if fr.shape != r.shape or not np.all(np.isfinite(fr)):
        raise ValueError("hankel_transform: f(r) が標本点で有限な実数配列にならない")
    Jp1 = np.abs(special.jv(p + 1, jk))
    T = 2.0 * special.jv(p, np.outer(jk, jk) / S) / (np.outer(Jp1, Jp1) * S)
    F1 = fr / Jp1 * R
    F2 = T @ F1
    F = F2 * Jp1 / V
    inv_err = float(np.abs(T @ T - np.eye(n)).max())
    return {"r": r, "f": fr, "nu": nu, "F": F, "T_involution_error": inv_err}


# ---------------------------------------------------------------------------- #
# s 領域の有理伝達関数 H(s) = num(s) / den(s)(係数は降べき、np.polyval と同じ並び)
# ---------------------------------------------------------------------------- #
def _tf(num, den):
    num = np.trim_zeros(np.atleast_1d(np.asarray(num, dtype=np.float64)), "f")
    den = np.trim_zeros(np.atleast_1d(np.asarray(den, dtype=np.float64)), "f")
    if den.size == 0:
        raise ValueError("伝達関数: 分母が 0")
    if num.size == 0:
        num = np.zeros(1)
    if not (np.all(np.isfinite(num)) and np.all(np.isfinite(den))):
        raise ValueError("伝達関数: 係数に NaN/inf がある")
    if num.size > den.size:
        raise ValueError("伝達関数: 分子の次数が分母より高い(非プロパー、%d > %d)" % (num.size - 1, den.size - 1))
    return num, den


def tf_poles_zeros(num, den) -> dict:
    """H(s) = num/den の極・零点・直流ゲイン・安定性。

    安定(漸近安定)= すべての極の実部 < 0。直流ゲインは H(0)(原点に極があれば inf)。
    """
    num, den = _tf(num, den)
    poles = np.roots(den) if den.size > 1 else np.zeros(0, complex)
    zeros = np.roots(num) if num.size > 1 else np.zeros(0, complex)
    d0 = den[-1]
    dc = float(num[-1] / d0) if d0 != 0 else math.inf
    return {"poles": poles, "zeros": zeros, "gain": float(num[0] / den[0]), "dc_gain": dc,
            "stable": bool(poles.size == 0 or np.all(poles.real < 0)),
            "order": int(den.size - 1)}


def tf_freq_response(num, den, w) -> dict:
    """周波数応答 H(jω)(Bode 線図の中身)。ω は rad/s。位相は連続に unwrap した度。"""
    num, den = _tf(num, den)
    w = np.asarray(w, dtype=np.float64).ravel()
    H = np.polyval(num, 1j * w) / np.polyval(den, 1j * w)
    return {"w": w, "H": H, "mag": np.abs(H), "mag_db": 20.0 * np.log10(np.abs(H) + 1e-300),
            "phase_deg": np.degrees(np.unwrap(np.angle(H)))}


def _state_space(num, den):
    """可制御標準形 (A, B, C, D)。分子と分母の次数が同じなら直達項 D を分ける。"""
    num, den = _tf(num, den)
    num, den = num / den[0], den / den[0]
    n = den.size - 1
    if n == 0:
        return np.zeros((0, 0)), np.zeros((0, 1)), np.zeros((1, 0)), float(num[-1])
    nb = np.concatenate([np.zeros(n + 1 - num.size), num])
    D = nb[0]
    b = nb[1:] - D * den[1:]                                # 直達を引いた残り(厳密にプロパー)
    A = np.zeros((n, n))
    A[0, :] = -den[1:]
    A[1:, :-1] = np.eye(n - 1)
    B = np.zeros((n, 1))
    B[0, 0] = 1.0
    C = b[None, :]
    return A, B, C, D


def tf_impulse_response(num, den, t) -> np.ndarray:
    """インパルス応答 h(t) = L⁻¹[H(s)](t)(厳密にプロパーな部分。直達項のデルタは返さない)。

    h(t) = C e^{At} B を行列指数で直接評価する(部分分数に頼らないので重根・原点の極でも分岐しない)。
    """
    A, B, C, _D = _state_space(num, den)
    t = np.asarray(t, dtype=np.float64).ravel()
    if A.size == 0:
        return np.zeros_like(t)
    return np.array([(C @ linalg.expm(A * ti) @ B).item() for ti in t])


def tf_step_response(num, den, t) -> np.ndarray:
    """単位ステップ応答 y(t) = L⁻¹[H(s)/s](t)。

    拡大行列 [[A, B], [0, 0]] の指数関数で ∫_0^t e^{Aτ} B dτ を厳密に得る(A が特異でも可)。
    門: 1/(s+a) → (1 − e^{−at})/a、2 次系 ω²/(s² + 2ζωs + ω²) の閉じた式。
    """
    A, B, C, D = _state_space(num, den)
    t = np.asarray(t, dtype=np.float64).ravel()
    n = A.shape[0]
    if n == 0:
        return np.full_like(t, D)
    M = np.zeros((n + 1, n + 1))
    M[:n, :n] = A
    M[:n, n:] = B
    out = np.empty_like(t)
    for k, ti in enumerate(t):
        E = linalg.expm(M * ti)
        out[k] = (C @ E[:n, n:]).item() + D
    return out


def tf_bilinear(num, den, fs: float = 1.0, *, prewarp_hz: float | None = None) -> dict:
    """Tustin(双一次)変換 s = K (z − 1)/(z + 1) で連続系を離散系に写す。

    K = 2·fs(素の Tustin)か、``prewarp_hz`` を与えると K = ω₀ / tan(ω₀ / (2 fs))
    (その周波数で連続系と離散系の応答が**厳密に一致**する。それ以外の周波数は tan で歪む)。
    返り値の係数は z の降べき(``np.polyval(num_z, z)``)。安定な連続系は安定な離散系になる(左半面 → 単位円内)。
    """
    num, den = _tf(num, den)
    fs = float(fs)
    if not fs > 0:
        raise ValueError("tf_bilinear: fs は正")
    if prewarp_hz is None:
        K = 2.0 * fs
    else:
        w0 = 2.0 * math.pi * float(prewarp_hz)
        if not 0 < w0 / (2 * fs) < math.pi / 2:
            raise ValueError("tf_bilinear: 前歪み周波数はナイキスト未満の正(得たのは %r Hz)" % (prewarp_hz,))
        K = w0 / math.tan(w0 / (2.0 * fs))
    n = den.size - 1
    zm, zp = np.array([1.0, -1.0]), np.array([1.0, 1.0])

    def _map(c):
        c = np.concatenate([np.zeros(n + 1 - c.size), c])
        acc = np.zeros(n + 1)
        for k, ck in enumerate(c):                          # ck s^{n-k} → ck K^{n-k} (z-1)^{n-k} (z+1)^k
            p = n - k
            term = np.array([ck * K ** p])
            for _ in range(p):
                term = np.convolve(term, zm)
            for _ in range(k):
                term = np.convolve(term, zp)
            acc = acc + term
        return acc

    bz, az = _map(num), _map(den)
    return {"num_z": bz / az[0], "den_z": az / az[0], "K": K, "fs": fs}


def laplace_inverse_talbot(num, den, t, *, M: int = 32) -> np.ndarray:
    """有理関数 F(s) = num(s)/den(s) の数値逆ラプラス変換(固定 Talbot 法)。

    厳密解は ``tf_impulse_response`` が行列指数で出すので、**2 つの独立な経路で同じ f(t) が出るか**が
    この op の検算になる。任意の F(s)(1/√s など)は ``laplace_inverse_func`` へ。
    """
    num, den = _tf(num, den)
    return laplace_inverse_func(lambda s: np.polyval(num, s) / np.polyval(den, s), t, M=M)


def laplace_inverse_func(F, t, *, M: int = 32) -> np.ndarray:
    """数値逆ラプラス変換(固定 Talbot 法、Abate & Valkó 2004 / Abate & Whitt 2006)。

    f(t) ≈ (r/M) [ ½ F(r) e^{rt} + Σ_{k=1}^{M−1} Re( e^{t S(θ_k)} F(S(θ_k)) (1 + iσ(θ_k)) ) ]、
    r = 2M/(5t)、θ_k = kπ/M、S(θ) = rθ(cot θ + i)、σ(θ) = θ + (θ cot θ − 1) cot θ。

    ``F`` は複素数 s(スカラーでも配列でも)を受けて F(s) を返す呼び出し可能。
    t > 0 のみ。精度は M と F の解析性で決まる(F が右半面の外に特異点を持つ・f が不連続だと落ちる)。
    倍精度の M は 20〜40 程度が目安(大きすぎると丸めで壊れる)。
    """
    if not callable(F):
        raise TypeError("laplace_inverse_func: F は呼び出し可能(F(s) を返す)")
    Ff = F
    t = np.asarray(t, dtype=np.float64).ravel()
    if np.any(t <= 0):
        raise ValueError("laplace_inverse: t > 0 のみ(t = 0 で r が発散する)")
    M = int(M)
    if M < 4:
        raise ValueError("laplace_inverse: M は 4 以上")
    th = np.arange(1, M) * math.pi / M
    cot = 1.0 / np.tan(th)
    sig = th + (th * cot - 1.0) * cot
    out = np.empty_like(t)
    for i, ti in enumerate(t):
        r = 2.0 * M / (5.0 * ti)
        S = r * th * (cot + 1j)
        val = 0.5 * np.real(Ff(complex(r))) * math.exp(r * ti)
        val += float(np.sum(np.real(np.exp(ti * S) * Ff(S) * (1.0 + 1j * sig))))
        out[i] = r / M * val
    return out


# ── 係数を返す直交変換: DCT と Daubechies のウェーブレット(N 次元) ─────────────────────────────── #
# 既存の xsp_dct / xmh_haar は「画像 → 見せるための画像」で、係数も逆変換も Parseval の門も無かった。
# ここは係数そのものを返し、逆変換で丸め誤差まで戻ることを門にする。2-D 画像・3-D ボリュームにそのまま効く。

def dct_transform(x, *, axes=None, inverse: bool = False) -> dict:
    """正規直交 DCT-II(``inverse=True`` で DCT-III = 逆変換)を N 次元で。

    Args:
        x: 任意次元の実配列(信号・画像・ボリューム)。
        axes: 変換する軸(省略で全軸)。
        inverse: True なら係数から元に戻す。

    Returns:
        ``coeffs``(同じ形)、``energy``(Σx²、正規直交なので変換の前後で同じ = Parseval)、
        ``compaction`` = 大きい順に並べた係数のエネルギーの累積割合(先頭 1% で何割を持つか、が JPEG の理由)。

    門は定義式 C[k, n] = √(2/N)·c_k·cos(π(2n+1)k / 2N) の行列と一致すること・逆変換で 1e-12 で戻ること。
    """
    from scipy import fft as _fft
    a = np.asarray(x, dtype=np.float64)
    if a.ndim == 0 or a.size == 0 or not np.all(np.isfinite(a)):
        raise ValueError("dct_transform: 有限値の 1 次元以上の配列")
    ax = tuple(range(a.ndim)) if axes is None else tuple(int(i) for i in np.atleast_1d(axes))
    y = (_fft.idctn if inverse else _fft.dctn)(a, type=2, axes=ax, norm="ortho")
    e = np.sort((y * y).ravel())[::-1]
    tot = float(e.sum())
    comp = np.cumsum(e) / tot if tot > 0 else np.ones_like(e)
    return {"coeffs": y, "energy": tot, "compaction": comp}


def _binom(n: int, k: int) -> int:
    return math.comb(n, k)


def wavelet_filters(order: int = 2) -> dict:
    """Daubechies の正規直交ウェーブレット dbN のフィルタを、教科書の構成(スペクトル分解)で作る。

    |H(ω)|² = cos^{2N}(ω/2)·P(sin²(ω/2))、P(y) = Σ_{k<N} C(N−1+k, k) y^k(Daubechies 1988)。P の根から単位円の
    内側の零点を選び、(1 + z⁻¹)^N と掛け合わせる。表を写さないので桁落ちの転記ミスが無い(門が値を確かめる)。

    Returns:
        ``lowpass`` h(長さ 2N、和 √2)、``highpass`` g[n] = (−1)^n h[2N−1−n]、``order``、
        ``vanishing_moments`` = N(次数 N−1 までの多項式を詳細係数で消す)。order=1 は Haar。
    """
    N = int(order)
    if not 1 <= N <= 10:
        raise ValueError("wavelet_filters: order は 1〜10(それより上はスペクトル分解の丸めが効く)")
    P = np.array([_binom(N - 1 + k, k) for k in range(N)], dtype=np.float64)    # y^0 .. y^{N-1}
    q = np.array([1.0])
    if N > 1:
        for yr in np.roots(P[::-1]):
            # y = (2 − z − 1/z)/4 → z² − (2 − 4y) z + 1 = 0、単位円の内側の根を取る
            zs = np.roots([1.0, -(2.0 - 4.0 * yr), 1.0])
            z = zs[np.argmin(np.abs(zs))]
            q = np.convolve(q, [1.0, -z])
        q = np.real_if_close(q, tol=1e6).real
    h = q
    for _ in range(N):
        h = np.convolve(h, [1.0, 1.0])
    h = h * (math.sqrt(2.0) / h.sum())
    L = h.size
    g = np.array([(-1) ** n * h[L - 1 - n] for n in range(L)])
    return {"lowpass": h, "highpass": g, "order": N, "vanishing_moments": N}


def _analysis_axis(a, h, g, axis):
    a = np.moveaxis(a, axis, -1)
    n = a.shape[-1]
    if n % 2:
        raise ValueError("dwt_transform: 各段で変換する軸の長さは偶数(2^levels の倍数)")
    idx = (2 * np.arange(n // 2)[:, None] + np.arange(h.size)[None, :]) % n   # 周期境界 → 厳密に直交
    seg = a[..., idx]
    lo, hi = seg @ h, seg @ g
    return np.moveaxis(lo, -1, axis), np.moveaxis(hi, -1, axis)


def _synthesis_axis(lo, hi, h, g, axis):
    lo, hi = np.moveaxis(lo, axis, -1), np.moveaxis(hi, axis, -1)
    m = lo.shape[-1]
    n = 2 * m
    out = np.zeros(lo.shape[:-1] + (n,))
    idx = (2 * np.arange(m)[:, None] + np.arange(h.size)[None, :]) % n
    for j in range(h.size):                                   # 解析の転置(直交なので逆変換)
        out[..., idx[:, j]] += lo * h[j] + hi * g[j]          # 1 つの j の中では添字が重ならない
    return np.moveaxis(out, -1, axis)


def dwt_transform(x, *, order: int = 2, levels: int = 1, axes=None) -> dict:
    """Daubechies dbN の多段・N 次元の離散ウェーブレット変換(周期境界で厳密に正規直交)。

    Args:
        x: 実配列(1-D 信号・2-D 画像・3-D ボリューム)。変換する軸の長さは 2^levels の倍数。
        order: dbN の N(1 = Haar)。
        levels: 段数。各段で近似(全軸ローパス)をさらに分ける。
        axes: 変換する軸(省略で全軸)。

    Returns:
        ``approx`` 最後の近似、``details`` = 段ごとの dict(キーは軸ごとの 'a'/'d' の並び、例 2-D なら
        'ad'・'da'・'dd')、``energy_in``・``energy_out``(Parseval で一致)、``order``・``levels``・``axes``。
        ``dwt_inverse`` に丸ごと渡すと元に戻る。
    """
    a = np.asarray(x, dtype=np.float64)
    if a.ndim == 0 or a.size == 0 or not np.all(np.isfinite(a)):
        raise ValueError("dwt_transform: 有限値の 1 次元以上の配列")
    ax = tuple(range(a.ndim)) if axes is None else tuple(int(i) % a.ndim for i in np.atleast_1d(axes))
    lv = int(levels)
    if lv < 1:
        raise ValueError("dwt_transform: levels は 1 以上")
    for i in ax:
        if a.shape[i] % (2 ** lv):
            raise ValueError(f"dwt_transform: 軸 {i} の長さ {a.shape[i]} が 2^levels = {2 ** lv} の倍数でない")
    f = wavelet_filters(order)
    h, g = f["lowpass"], f["highpass"]
    details = []
    cur = a
    for _ in range(lv):
        bands = {"": cur}
        for i in ax:
            nb = {}
            for key, arr in bands.items():
                lo, hi = _analysis_axis(arr, h, g, i)
                nb[key + "a"], nb[key + "d"] = lo, hi
            bands = nb
        cur = bands.pop("a" * len(ax))
        details.append(bands)
    e_out = float((cur * cur).sum() + sum((v * v).sum() for d in details for v in d.values()))
    return {"approx": cur, "details": details, "energy_in": float((a * a).sum()), "energy_out": e_out,
            "order": f["order"], "levels": lv, "axes": ax}


def dwt_inverse(coeffs: dict) -> np.ndarray:
    """``dwt_transform`` の結果から元の配列に戻す(正規直交なので解析の転置)。"""
    if not isinstance(coeffs, dict) or not {"approx", "details", "order", "axes"} <= set(coeffs):
        raise ValueError("dwt_inverse: dwt_transform の戻り値(approx・details・order・axes)を渡す")
    f = wavelet_filters(coeffs["order"])
    h, g = f["lowpass"], f["highpass"]
    ax = tuple(coeffs["axes"])
    cur = np.asarray(coeffs["approx"], dtype=np.float64)
    for bands in reversed(coeffs["details"]):
        allb = dict(bands)
        allb["a" * len(ax)] = cur
        for depth in range(len(ax) - 1, -1, -1):
            i = ax[depth]
            nb = {}
            for key in {k[:depth] for k in allb}:
                nb[key] = _synthesis_axis(allb[key + "a"], allb[key + "d"], h, g, i)
            allb = nb
        cur = allb[""]
    return cur
