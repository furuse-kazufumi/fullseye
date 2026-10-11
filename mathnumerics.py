# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mathnumerics — 数値計算の古典(求積・低食い違い列・Chebyshev・シンプレクティック積分)と特殊関数。

2026-10-03 の棚卸しで、どの層にも op が無かった有名な道具を足す(numpy + scipy だけ):

* **Gauss 求積**(Legendre / Hermite / Laguerre / Chebyshev)—— n 点で 2n−1 次の多項式まで**厳密**。
* **低食い違い列**(Halton / Sobol)—— 乱数より「隙間と塊」が少ない点列。積分誤差の減り方が N^{−1/2} より速い。
* **Chebyshev 点と重心補間**—— 等間隔の多項式補間は端で暴れる(Runge 現象)。Chebyshev 点なら収束する。
* **シンプレクティック積分(速度 Verlet)**—— 長時間でもエネルギー誤差が有界で、時間を逆に回すと元に戻る。
  比較のため陽的 Euler と RK4 も同じ入口で選べる(失敗例を隣に置くため)。
* **特殊関数**(誤差関数・Bessel 関数)—— 値そのものは scipy.special だが、型つきの op として呼べ、
  恒等式(奇関数性・導関数・Wronskian)で検算できる形で出す。

門(閉じた式と定理だけ。表から写した値は使わない)は ``tests/test_mathnumerics.py``。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import special

__all__ = [
    "bessel", "erf", "erfc",
    "chebyshev_nodes", "interp_barycentric", "chebyshev_coeffs_nd", "chebyshev_eval_nd",
    "gauss_quadrature", "gauss_cubature",
    "low_discrepancy",
    "integrate_hamiltonian",
]


# ---------------------------------------------------------------------------- #
# 特殊関数
# ---------------------------------------------------------------------------- #
def _real(x, name):
    a = np.asarray(x, dtype=np.float64)
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: 入力に NaN/inf がある" % name)
    return a


def erf(x) -> np.ndarray:
    """誤差関数 erf(x) = (2/√π) ∫_0^x e^{−t²} dt。

    正規分布の累積や、ぼけたエッジ(ガウスで畳んだ段差)の形そのもの: 幅 σ のガウスでぼけた段差は
    ½(1 + erf(x / (σ√2)))。門: 奇関数、erf(∞) = 1、導関数 = (2/√π) e^{−x²}、Gauss 求積による積分と一致。
    """
    return special.erf(_real(x, "erf"))


def erfc(x) -> np.ndarray:
    """相補誤差関数 erfc(x) = 1 − erf(x)。大きな x で 1 − erf を引き算すると桁落ちするので別に持つ
    (x = 10 で 1 − erf は 0 になるが erfc は 2.1e−45)。"""
    return special.erfc(_real(x, "erfc"))


def bessel(x, order: float = 0, kind: str = "j") -> np.ndarray:
    """Bessel 関数。``kind`` = ``"j"``(第 1 種 J)/ ``"y"``(第 2 種 Y)/ ``"i"``・``"k"``(変形)。

    円い膜の振動・円い開口の回折(Airy = J₁)・円筒の熱伝導に出る。門: Wronskian
    J_{ν+1}(x)Y_ν(x) − J_ν(x)Y_{ν+1}(x) = 2/(πx)、漸化式 J_{ν−1} + J_{ν+1} = (2ν/x) J_ν。
    Y と K は x > 0 のみ(原点で発散する)。
    """
    x = _real(x, "bessel")
    fn = {"j": special.jv, "y": special.yv, "i": special.iv, "k": special.kv}.get(kind)
    if fn is None:
        raise ValueError("bessel: kind は 'j' / 'y' / 'i' / 'k'(得たのは %r)" % (kind,))
    if kind in ("y", "k") and np.any(x <= 0):
        raise ValueError("bessel: kind=%r は x > 0 のみ(原点で発散する)" % kind)
    return fn(float(order), x)


# ---------------------------------------------------------------------------- #
# Gauss 求積
# ---------------------------------------------------------------------------- #
_GAUSS = {
    "legendre": (np.polynomial.legendre.leggauss, "∫_{−1}^{1} f(x) dx"),
    "hermite": (np.polynomial.hermite.hermgauss, "∫ f(x) e^{−x²} dx(全実数)"),
    "laguerre": (np.polynomial.laguerre.laggauss, "∫_0^∞ f(x) e^{−x} dx"),
    "chebyshev": (np.polynomial.chebyshev.chebgauss, "∫_{−1}^{1} f(x) / √(1−x²) dx"),
}


def gauss_quadrature(n: int, kind: str = "legendre", a: float | None = None, b: float | None = None) -> dict:
    """n 点の Gauss 求積の節点と重み。∫ f ≈ Σ w_k f(x_k)。

    n 点で **2n−1 次までの多項式を厳密に**積分する(等間隔の台形則は 1 次まで)。
    ``kind="legendre"`` は区間 [a, b] へ写せる(既定 [−1, 1])。他の kind は重み関数込みの積分(``integral`` 参照)。
    門: 2n−1 次の単項式は厳密、2n 次は厳密でない(両向き)。
    """
    n = int(n)
    if not 1 <= n <= 200:
        raise ValueError("gauss_quadrature: n は 1..200(得たのは %d)" % n)
    if kind not in _GAUSS:
        raise ValueError("gauss_quadrature: kind は %s(得たのは %r)" % (sorted(_GAUSS), kind))
    fn, what = _GAUSS[kind]
    x, w = fn(n)
    if kind == "legendre" and (a is not None or b is not None):
        a = -1.0 if a is None else float(a)
        b = 1.0 if b is None else float(b)
        if not b > a:
            raise ValueError("gauss_quadrature: b > a が要る")
        x = 0.5 * (b - a) * x + 0.5 * (b + a)
        w = 0.5 * (b - a) * w
        what = "∫_{%g}^{%g} f(x) dx" % (a, b)
    elif a is not None or b is not None:
        raise ValueError("gauss_quadrature: 区間 [a, b] を写せるのは kind='legendre' だけ")
    return {"nodes": np.asarray(x), "weights": np.asarray(w), "integral": what,
            "exact_degree": 2 * n - 1, "kind": kind}


def gauss_cubature(n: int, dim: int = 2, a=-1.0, b=1.0) -> dict:
    """Gauss–Legendre のテンソル積で、箱 [a, b]^dim(a, b は軸ごとでも可)の求積の節点 (n^dim, dim) と重み。

    画像の画素平均・ボリュームの体積積分・PSF の積分に。各軸で 2n−1 次までの多項式の積を**厳密に**積分する
    (門: x^p y^q で p, q <= 2n−1 は厳密、どれかが 2n で誤差)。点の数は n^dim なので高次元では急に増える
    (dim > 6 では低食い違い列の方が向く)。
    """
    n, dim = int(n), int(dim)
    if not (1 <= dim <= 6 and 1 <= n and n ** dim <= 2_000_000):
        raise ValueError("gauss_cubature: 1 <= dim <= 6、n^dim <= 2e6")
    lo = np.broadcast_to(np.asarray(a, dtype=np.float64), (dim,))
    hi = np.broadcast_to(np.asarray(b, dtype=np.float64), (dim,))
    if np.any(hi <= lo):
        raise ValueError("gauss_cubature: 各軸で b > a")
    x, w = np.polynomial.legendre.leggauss(n)
    axes = [0.5 * (hi[d] - lo[d]) * x + 0.5 * (hi[d] + lo[d]) for d in range(dim)]
    wts = [0.5 * (hi[d] - lo[d]) * w for d in range(dim)]
    grids = np.meshgrid(*axes, indexing="ij")
    W = np.ones_like(grids[0])
    for d in range(dim):
        W = W * np.meshgrid(*[wts[k] if k == d else np.ones(n) for k in range(dim)], indexing="ij")[d]
    return {"nodes": np.stack([g_.ravel() for g_ in grids], axis=1), "weights": W.ravel(),
            "exact_degree_per_axis": 2 * n - 1}


# ---------------------------------------------------------------------------- #
# 低食い違い列
# ---------------------------------------------------------------------------- #
_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53)


def _radical_inverse(i, base):
    out = np.zeros(i.shape, dtype=np.float64)
    f = 1.0 / base
    k = i.copy()
    while np.any(k > 0):
        out += f * (k % base)
        k //= base
        f /= base
    return out


def low_discrepancy(n: int, dim: int = 2, kind: str = "halton", *, skip: int = 0, seed: int | None = None) -> np.ndarray:
    """[0, 1)^dim の低食い違い点列 (n, dim)。

    * ``"halton"`` —— 座標ごとに異なる素数を基数にした van der Corput 列(自前の実装、決定的)。
      ``skip`` 個を読み飛ばす(先頭の 0 を避けるなら 1)。高次元(> 8 程度)では座標間に縞が出るので注意。
    * ``"sobol"`` —— scipy.stats.qmc.Sobol(``seed`` を与えるとスクランブル)。n は 2 の冪が最良。
    * ``"random"`` —— 比較用の一様乱数(``seed`` 必須、再現性のため)。

    門: なめらかな関数の積分誤差は乱数の N^{−1/2} より速く減る / 星形食い違い量が乱数より小さい。
    """
    n, dim = int(n), int(dim)
    if not (1 <= n <= 10_000_000 and 1 <= dim <= len(_PRIMES)):
        raise ValueError("low_discrepancy: 1 <= n <= 1e7、1 <= dim <= %d" % len(_PRIMES))
    if kind == "halton":
        i = np.arange(int(skip), int(skip) + n, dtype=np.int64)
        return np.stack([_radical_inverse(i, _PRIMES[d]) for d in range(dim)], axis=1)
    if kind == "sobol":
        from scipy.stats import qmc
        eng = qmc.Sobol(d=dim, scramble=seed is not None, seed=seed)
        if skip:
            eng.fast_forward(int(skip))
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")                 # n が 2 の冪でないときの UserWarning
            return eng.random(n)
    if kind == "random":
        if seed is None:
            raise ValueError("low_discrepancy: kind='random' は seed を必ず渡す(再現性)")
        return np.random.default_rng(seed).random((n, dim))
    raise ValueError("low_discrepancy: kind は 'halton' / 'sobol' / 'random'(得たのは %r)" % (kind,))


# ---------------------------------------------------------------------------- #
# Chebyshev 点と重心補間
# ---------------------------------------------------------------------------- #
def chebyshev_nodes(n: int, a: float = -1.0, b: float = 1.0, kind: int = 2) -> np.ndarray:
    """区間 [a, b] の Chebyshev 点 n 個(昇順)。

    ``kind=2``(既定)は端点を含む Chebyshev–Lobatto 点 x_k = cos(kπ/(n−1))、``kind=1`` は端点を含まない
    Chebyshev–Gauss 点 cos((2k+1)π/(2n))。端に向かって密になり、多項式補間の暴れ(Runge 現象)を抑える。
    """
    n = int(n)
    if n < 2:
        raise ValueError("chebyshev_nodes: n は 2 以上")
    if not float(b) > float(a):
        raise ValueError("chebyshev_nodes: b > a が要る")
    k = np.arange(n)
    if kind == 2:
        t = np.cos(k * math.pi / (n - 1))
    elif kind == 1:
        t = np.cos((2 * k + 1) * math.pi / (2 * n))
    else:
        raise ValueError("chebyshev_nodes: kind は 1 か 2")
    return np.sort(0.5 * (float(b) - float(a)) * t + 0.5 * (float(b) + float(a)))


def interp_barycentric(xk, yk, x) -> np.ndarray:
    """点 (xk, yk) を通る多項式(次数 len−1)を、重心公式で x に評価する(Berrut & Trefethen 2004)。

    係数を経由しない(Vandermonde 行列は解かない)ので高次でも数値的に安定。等間隔点では
    **Runge 現象**(端の振動)がそのまま出る —— それは公式の欠陥ではなく、点の置き方の問題。
    門: 次数 len−1 以下の多項式は厳密に再現する。
    """
    xk = _real(xk, "interp_barycentric").ravel()
    yk = _real(yk, "interp_barycentric").ravel()
    x = _real(x, "interp_barycentric")
    if xk.shape != yk.shape or xk.size < 1:
        raise ValueError("interp_barycentric: xk と yk は同じ長さ(1 以上)")
    if np.unique(xk).size != xk.size:
        raise ValueError("interp_barycentric: xk に重複がある")
    d = xk[:, None] - xk[None, :]
    np.fill_diagonal(d, 1.0)
    # ★2026-10-07: 重みを差の直接の積で作ると、Chebyshev 1200 点や区間 [0, 1e-4] で
    # 積が 0 / inf に飛び全点 NaN になっていた。重みは共通の定数倍を除いて決まるので、
    # 対数で和を取り最大で正規化してから exp する(符号は別に数える)。
    logabs = np.sum(np.log(np.abs(d)), axis=1)
    sign = np.where(np.count_nonzero(d < 0, axis=1) % 2 == 1, -1.0, 1.0)
    w = sign * np.exp(np.min(logabs) - logabs)
    xs = x.ravel()
    diff = xs[:, None] - xk[None, :]
    exact = diff == 0
    with np.errstate(divide="ignore", invalid="ignore"):
        c = w[None, :] / diff
        val = (c @ yk) / c.sum(axis=1)
    hit = exact.any(axis=1)
    val[hit] = yk[np.argmax(exact[hit], axis=1)]
    return val.reshape(x.shape)


# ---------------------------------------------------------------------------- #
# ハミルトン系の時間積分(Verlet / Euler / RK4)
# ---------------------------------------------------------------------------- #
def _force(system, q, params):
    if system == "harmonic":                               # H = p²/2 + ω² q²/2
        w = float(params.get("omega", 1.0))
        return -w * w * q, 0.5 * w * w * float(q @ q)
    if system == "pendulum":                               # H = p²/2 − ω² cos q
        w = float(params.get("omega", 1.0))
        return -w * w * np.sin(q), float(-w * w * np.sum(np.cos(q)))
    if system == "kepler":                                 # H = |p|²/2 − μ/|q|(2-D)
        mu = float(params.get("mu", 1.0))
        r = float(np.linalg.norm(q))
        if r < 1e-12:
            raise ValueError("integrate_hamiltonian: kepler が原点に落ちた(dt を小さく)")
        return -mu * q / r ** 3, -mu / r
    raise ValueError("integrate_hamiltonian: system は 'harmonic' / 'pendulum' / 'kepler'(得たのは %r)" % (system,))


def integrate_hamiltonian(q0, p0, dt: float = 0.05, n_steps: int = 1000, *, system: str = "harmonic",
                          method: str = "verlet", **params) -> dict:
    """名前つきのハミルトン系(質量 1)を時間積分する。返り値 ``{"t","q","p","energy","energy_drift"}``。

    ``method``:
      * ``"verlet"`` —— 速度 Verlet(シンプレクティック・時間反転対称)。エネルギー誤差は O(dt²) で**有界**のまま
        振動し、長時間でも増えない。dt を負にして回すと元の状態に(丸め誤差まで)戻る。
      * ``"euler"`` —— 陽的 Euler(比較用の失敗例)。調和振動子ではエネルギーが毎ステップ (1 + ω²dt²) 倍に増え、
        位相空間で外向きの渦巻きになる。
      * ``"rk4"`` —— 古典的 4 次 Runge–Kutta。短時間はとても正確だが、シンプレクティックではないので
        エネルギーは長時間でゆっくり減り続ける(有界ではない)。

    ``system``: ``"harmonic"``(omega)/ ``"pendulum"``(omega)/ ``"kepler"``(mu、2-D)。
    門: Verlet のエネルギー誤差が有界 / 時間反転で戻る / Euler の増幅率が (1 + ω²dt²)^n。
    """
    q = np.atleast_1d(np.asarray(q0, dtype=np.float64)).copy()
    p = np.atleast_1d(np.asarray(p0, dtype=np.float64)).copy()
    if q.shape != p.shape or q.ndim != 1:
        raise ValueError("integrate_hamiltonian: q0 と p0 は同じ長さの 1-D")
    if system == "kepler" and q.size != 2:
        raise ValueError("integrate_hamiltonian: kepler は 2-D(q0, p0 は長さ 2)")
    dt = float(dt)
    n = int(n_steps)
    if dt == 0 or not math.isfinite(dt) or not 1 <= n <= 5_000_000:
        raise ValueError("integrate_hamiltonian: dt != 0(有限)、1 <= n_steps <= 5e6")
    if method not in ("verlet", "euler", "rk4"):
        raise ValueError("integrate_hamiltonian: method は 'verlet' / 'euler' / 'rk4'(得たのは %r)" % (method,))
    Q = np.empty((n + 1, q.size))
    P = np.empty((n + 1, q.size))
    E = np.empty(n + 1)

    def energy(q_, p_):
        return 0.5 * float(p_ @ p_) + _force(system, q_, params)[1]

    Q[0], P[0], E[0] = q, p, energy(q, p)
    f, _ = _force(system, q, params)
    for k in range(n):
        if method == "verlet":
            p_half = p + 0.5 * dt * f
            q = q + dt * p_half
            f, _ = _force(system, q, params)
            p = p_half + 0.5 * dt * f
        elif method == "euler":
            q, p = q + dt * p, p + dt * f
            f, _ = _force(system, q, params)
        else:
            def deriv(q_, p_):
                return p_, _force(system, q_, params)[0]
            k1q, k1p = deriv(q, p)
            k2q, k2p = deriv(q + 0.5 * dt * k1q, p + 0.5 * dt * k1p)
            k3q, k3p = deriv(q + 0.5 * dt * k2q, p + 0.5 * dt * k2p)
            k4q, k4p = deriv(q + dt * k3q, p + dt * k3p)
            q = q + dt / 6.0 * (k1q + 2 * k2q + 2 * k3q + k4q)
            p = p + dt / 6.0 * (k1p + 2 * k2p + 2 * k3p + k4p)
        Q[k + 1], P[k + 1], E[k + 1] = q, p, energy(q, p)
    return {"t": dt * np.arange(n + 1), "q": Q, "p": P, "energy": E,
            "energy_drift": float(np.max(np.abs(E - E[0])) / max(abs(E[0]), 1e-300)),
            "method": method, "system": system}


# ── Chebyshev 補間を N 次元に(テンソル積、DCT-I で係数)────────────────────────────────────────── #
_LETTERS = "abcdefgh"


def _box(box, d):
    if box is None:
        return np.array([[-1.0, 1.0]] * d)
    B = np.asarray(box, dtype=np.float64).reshape(-1, 2)
    if B.shape[0] == 1 and d > 1:
        B = np.repeat(B, d, axis=0)
    if B.shape != (d, 2) or np.any(B[:, 1] <= B[:, 0]):
        raise ValueError("chebyshev: box は軸ごとの (lo, hi) で lo < hi")
    return B


def chebyshev_coeffs_nd(values, box=None) -> dict:
    """テンソル積の Chebyshev–Lobatto 格子で標本化した値から、N 次元の Chebyshev 係数を求める(DCT-I)。

    Args:
        values: 形 (n1, …, nd) の配列。軸 i の標本は ``chebyshev_nodes(n_i, lo_i, hi_i)``(昇順)の上の値。
        box: 軸ごとの区間 [(lo, hi), …](省略で全軸 [−1, 1]、1 組なら全軸に共通)。

    Returns:
        ``coeffs`` (n1, …, nd): f ≈ Σ c[k] Π T_{k_i}(t_i)(t_i は [−1, 1] に写した座標)、``box``、
        ``decay`` = 軸ごとに |c| の最大を次数ごとに並べた列(滑らかな関数は幾何級数的に落ちる = スペクトル収束)、
        ``tail`` = 各軸の最後の 2 次数の |c| の最大(打ち切り誤差の目安。小さいほど点数が足りている)。

    門: 次数が各軸 n_i − 1 以下の多項式は厳密に再現する / 1/(a − x) 型の極を持つ関数の係数は
    ρ^−k(ρ = a + √(a² − 1)、Bernstein の楕円)で落ちる。画像では、照明むら・反りなどの**滑らかな面**を
    数十の係数で表す(多項式のべき基底は高次で悪条件、Chebyshev は安定)。
    """
    from scipy import fft as _fft
    V = np.asarray(values, dtype=np.float64)
    if V.ndim < 1 or V.ndim > len(_LETTERS) or min(V.shape) < 2 or not np.all(np.isfinite(V)):
        raise ValueError("chebyshev_coeffs_nd: 1〜8 次元、各軸 2 点以上の有限値")
    d = V.ndim
    B = _box(box, d)
    C = V[tuple(slice(None, None, -1) for _ in range(d))]          # 昇順 → cos(jπ/(n−1)) の降順
    for ax in range(d):
        n = C.shape[ax]
        C = _fft.dct(C, type=1, axis=ax) / (n - 1)
        idx = [slice(None)] * d
        for k in (0, n - 1):
            idx[ax] = k
            C[tuple(idx)] *= 0.5
    decay = [np.abs(np.moveaxis(C, ax, 0)).reshape(C.shape[ax], -1).max(axis=1) for ax in range(d)]
    tail = float(max(float(dc[-2:].max()) for dc in decay))
    return {"coeffs": C, "box": B, "decay": decay, "tail": tail}


def chebyshev_eval_nd(coeffs, points, box=None) -> np.ndarray:
    """``chebyshev_coeffs_nd`` の係数を点 (M, d) で評価する(各軸 T_k(t) = cos(k·arccos t))。

    ``points`` が d 本の 1-D 配列の組なら、その格子(外積)の上で評価して形 (m1, …, md) を返す。
    """
    # ★2026-10-11(台帳契約の門): 係数表でない table({pre, post} など)を渡すと生の
    #   KeyError: 'coeffs' が漏れていた。何が足りないかを名指しして拒否する(fail-closed)。
    if isinstance(coeffs, dict) and "coeffs" not in coeffs:
        raise ValueError("chebyshev_eval_nd: table has no 'coeffs' key (got keys %s) — "
                         "pass the dict from chebyshev_coeffs_nd or the coefficient array"
                         % sorted(map(str, coeffs)))
    C = np.asarray(coeffs["coeffs"] if isinstance(coeffs, dict) else coeffs, dtype=np.float64)
    d = C.ndim
    B = _box(coeffs.get("box") if isinstance(coeffs, dict) and box is None else box, d)

    def _T(x, ax):
        t = (2.0 * np.asarray(x, np.float64) - (B[ax, 0] + B[ax, 1])) / (B[ax, 1] - B[ax, 0])
        if np.any(np.abs(t) > 1 + 1e-12):
            raise ValueError("chebyshev_eval_nd: 点が box の外(外挿はしない)")
        return np.cos(np.arange(C.shape[ax])[None, :] * np.arccos(np.clip(t, -1, 1))[:, None])

    # ★2026-10-07: list も格子扱いしていたので、d 点 x d 次元の点列 [[x, y], [x, y]] が
    # ndarray なら点ごと、list なら外積格子と、同じ数値で答えが変わっていた。格子は tuple のみ
    # (文書の呼び方 ``(gx, gy)`` は tuple)、list は ndarray と同じく点 (M, d) として読む。
    if isinstance(points, tuple) and len(points) == d and all(np.ndim(p) == 1 for p in points):
        out = C
        for ax in range(d):
            out = np.tensordot(_T(points[ax], ax), out, axes=([1], [ax]))
            out = np.moveaxis(out, 0, ax)
        return out
    try:
        P = np.asarray(points, dtype=np.float64)
    except ValueError:                       # 長さの揃わない list(以前は格子扱いだった)
        raise ValueError(f"chebyshev_eval_nd: 点は (M, {d})(軸ごとの格子なら 1-D 配列 {d} 本の tuple)") from None
    if P.ndim == 1 and d == 1:
        P = P[:, None]
    if P.ndim != 2 or P.shape[1] != d:
        raise ValueError(f"chebyshev_eval_nd: 点は (M, {d})(軸ごとの格子なら 1-D 配列 {d} 本の tuple)")
    ks = _LETTERS[:d]
    spec = ks + "," + ",".join("m" + k for k in ks) + "->m"
    return np.einsum(spec, C, *[_T(P[:, ax], ax) for ax in range(d)], optimize=True)
