# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""plsim —— フォトルミネッセンス(PL)像の「キャリア拡散の PSF」を閉形式の真値つきで作る。

Si ウェハや太陽電池の PL 像は、励起で作った過剰キャリア Δn が**拡散してから**光る。
だから像には光学の PSF のほかに、**拡散長 L = √(Dτ) で決まるもう 1 つの PSF** が掛かる。
細い溝・転位・粒界が「見える/見えない」は、この拡散 PSF と欠陥の種類で決まる ——
ここが本 module の主題で、作った像は他の PoC の真値つき合成入力にもなる
(``opsgenerative`` 族の方針そのまま。``semsim`` が SEM で担った役を PL で担う)。

物理(低注入・定常・面内 2 次元。教科書的な少数キャリア拡散方程式を、採点できる最小形に
落としたもの):

    D ∇²Δn − Δn/τ − σ(x,y) Δn = −G(x,y),      PL ∝ Δn

  * ``G`` は励起(生成)の場、``σ`` は欠陥による**追加の**再結合率の場(1/s)。
  * 点源の解(グリーン関数)は ``Δn(r) = (G/2πD)·K₀(r/L)``、``L = √(Dτ)``。
    面積分は ``∫K₀(r/L) dA = 2πL²`` なので、総量はちょうど ``G·τ``(**門 1**)。
  * 長さを画素、時間を τ で測ると方程式は ``L²∇²u − (1 + k)u = −g``(``u = Δn/(G₀τ)``、
    ``g = G/G₀``、``k = στ``)。入力は無次元の 2 枚の画像で済む。

閉形式の真値(``tests/test_plsim.py`` が確かめる):

  1. **総量**: 拡散 PSF(``pl_diffusion_psf``)の総和は 1(= ``G·τ``)。半分の質量が入る
     半径は ``r½ = 1.2572·L``(``1 − x·K₁(x) = 1/2`` の根)で、**L を 2 倍にすると 2 倍**。
  2. **一様**: 一様な励起・欠陥なし → 像は厳密に一様(``u = 1``、Neumann 境界で解の構造から)。
  3. **影の溝**(生成の欠け、幅 w、再結合は増えない): 中心のコントラストは連続では
     ``1 − exp(−w/2L)``、格子の上では厳密に ``1 − 2ρ^{m+1}/(1+ρ)``(``w = 2m+1``、
     ``ρ + 1/ρ = 2 + 1/L²``)。**w ≪ L では ≈ w/2L で消える**(拡散が影を埋める)。
  4. **沈みの溝**(再結合の線、再結合速度 S): ``Δn = Gτ[1 − A·exp(−|x|/L)]``、
     ``A = SL/(SL + 2D)``(Donolato 型の粒界コントラスト)。**L が長いほど深く・広く**
     見える(供給を上回って吸う)—— 影とは逆向き。格子の 1 画素の沈みは厳密に
     ``A = k/(k + L²(1−ρ²)/ρ)``。

この違いが設計規則になる: 拡散長の長い良質なウェハほど**影(励起・発光の欠け)は隠れ、
沈み(再結合活性な欠陥)は目立つ**。同じ式は蛍光顕微鏡の拡散や、ロックインサーモグラフィの
熱拡散長 ``μ = √(2α/ω)`` にもそのまま移る(``K₀`` の核は同形)。

型語彙(**新語はゼロ**): 入力・出力とも既存の ``image2d``(H×W の float)と ``table``。
"""
from __future__ import annotations

import numpy as np
from scipy import sparse as _sps
from scipy import special as _spc
from scipy.sparse import linalg as _spl

__all__ = ["pl_diffusion_psf", "pl_image_simulate", "pl_groove_visibility"]

#: 半分の質量が入る半径 r½/L。``1 − x·K₁(x) = 1/2`` の根(閉形式の定数、import 時に 1 回だけ解く)。
HALF_MASS_RADIUS_OVER_L = 1.2571513906775700

#: ``spsolve``(直接法)で解く未知数の上限。超えたら共役勾配法(対角前処理)。
_DIRECT_MAX = 160_000
#: 直接解に収まらない像の共役勾配の相対残差。公開のノブにはしない —— 直接解の像では
#: 何も変えない死にノブになる(2026-10-13 の探針で出た)。
_CG_RTOL = 1e-10


# --------------------------------------------------------------------------- #
# 入口の検査(fail-closed)                                                     #
# --------------------------------------------------------------------------- #
def _positive(v, name: str, op: str) -> float:
    f = float(v)
    if not np.isfinite(f) or f <= 0.0:
        raise ValueError("%s: %s must be a positive finite number, got %r" % (op, name, v))
    return f


def _nonneg(v, name: str, op: str) -> float:
    f = float(v)
    if not np.isfinite(f) or f < 0.0:
        raise ValueError("%s: %s must be a non-negative finite number, got %r" % (op, name, v))
    return f


def _as_map(a, name: str, op: str) -> np.ndarray:
    m = np.asarray(a, dtype=np.float64)
    if m.ndim != 2:
        raise ValueError("%s: %s must be 2-D (H, W), got shape %r" % (op, name, m.shape))
    if m.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if not np.isfinite(m).all():
        raise ValueError("%s: %s has non-finite values (NaN/Inf)" % (op, name))
    if (m < 0.0).any():
        raise ValueError("%s: %s must be non-negative" % (op, name))
    return m


def _grid_rho(L: float) -> float:
    """格子の減衰比 ρ(``ρ + 1/ρ = 2 + 1/L²`` の 0 < ρ < 1 の根)。``exp(−1/L)`` の格子版。"""
    b = 1.0 + 0.5 / (L * L)
    return b - np.sqrt(b * b - 1.0)


# --------------------------------------------------------------------------- #
# 1. 拡散 PSF(グリーン関数 K₀)                                                #
# --------------------------------------------------------------------------- #
def pl_diffusion_psf(diffusion_length_px: float = 8.0, size: int | None = None) -> np.ndarray:
    """キャリア拡散の PSF(2 次元のグリーン関数 K₀(r/L)/2πL²、総和 1)を画像で返す。

    Parameters
    ----------
    diffusion_length_px : float
        拡散長 ``L = √(Dτ)``[px]。
    size : int or None
        核の一辺(奇数)。``None`` なら ``2·ceil(8L)+1``(8L で切ると質量の欠けは
        ``8·K₁(8) ≈ 1.2e-3``)。

    Returns
    -------
    numpy.ndarray
        ``(size, size)`` の float64。中心画素は特異点 ``K₀(0) = ∞`` を**画素と同面積の円で
        平均した値** ``1 − (a/L)K₁(a/L)``(``a = 1/√π``)にして有限にしてある。

    Notes
    -----
    総和は解析的に 1(``∫K₀(r/L)dA = 2πL²``)。半分の質量が入る半径は ``1.2572·L``。
    これを ``generation`` に畳むと、欠陥の無い(``k = 0``)ときの ``pl_image_simulate`` と
    同じ像になる(境界の扱いを除く)。

    Examples
    --------
    >>> import numpy as np
    >>> k = pl_diffusion_psf(6.0)
    >>> k.shape
    (97, 97)
    >>> abs(float(k.sum()) - 1.0) < 5e-3            # 総量 = G·τ
    True
    >>> bool(k[48, 48] == k.max())                  # 中心が最大
    True
    """
    op = "pl_diffusion_psf"
    L = _positive(diffusion_length_px, "diffusion_length_px", op)
    if size is None:
        size = 2 * int(np.ceil(8.0 * L)) + 1
    size = int(size)
    if size < 3 or size % 2 == 0:
        raise ValueError("%s: size must be an odd integer >= 3, got %r" % (op, size))
    if size > 8191:
        raise ValueError("%s: size %d is too large (max 8191)" % (op, size))
    c = size // 2
    y, x = np.mgrid[-c:c + 1, -c:c + 1]
    r = np.hypot(x, y).astype(np.float64)
    k = np.zeros_like(r)
    nz = r > 0
    k[nz] = _spc.k0(r[nz] / L) / (2.0 * np.pi * L * L)
    a = 1.0 / np.sqrt(np.pi)                      # 画素と同面積の円の半径
    k[c, c] = 1.0 - (a / L) * _spc.k1(a / L)      # 中心: 円平均(面積 π a² = 1)
    return k


# --------------------------------------------------------------------------- #
# 2. PL 像の合成(定常拡散方程式を格子で解く)                                    #
# --------------------------------------------------------------------------- #
def _solve_diffusion(g: np.ndarray, k: np.ndarray, L: float, tol: float) -> np.ndarray:
    """``(1 + k) u − L² Δ_h u = g`` を Neumann 境界(流束 0)で解く。"""
    H, W = g.shape
    N = H * W
    L2 = L * L
    idx = np.arange(N).reshape(H, W)
    rows, cols, vals = [], [], []
    deg = np.zeros((H, W), dtype=np.float64)
    for di, dj in ((0, 1), (1, 0)):
        a = idx[: H - di, : W - dj].ravel()
        b = idx[di:, dj:].ravel()
        if a.size == 0:
            continue
        rows += [a, b]
        cols += [b, a]
        vals += [np.full(a.size, -L2), np.full(b.size, -L2)]
        np.add.at(deg, (slice(0, H - di), slice(0, W - dj)), 1.0)
        np.add.at(deg, (slice(di, H), slice(dj, W)), 1.0)
    diag = (1.0 + k + L2 * deg).ravel()
    rows.append(np.arange(N))
    cols.append(np.arange(N))
    vals.append(diag)
    M = _sps.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                        shape=(N, N))
    b = g.ravel()
    if N <= _DIRECT_MAX:
        u = _spl.spsolve(M, b)
    else:
        pre = _spl.LinearOperator((N, N), matvec=lambda v: v / diag, dtype=np.float64)
        u, info = _spl.cg(M, b, rtol=tol, maxiter=20_000, M=pre)
        if info != 0:
            raise RuntimeError("pl_image_simulate: conjugate gradient did not converge (info=%d)"
                               % info)
    return np.asarray(u, dtype=np.float64).reshape(H, W)


def pl_image_simulate(generation, sink=None, *, diffusion_length_px: float = 8.0,
                      optical_psf_px: float = 0.0, noise_rel: float = 0.0,
                      seed: int = 0) -> np.ndarray:
    """励起の場と再結合の場から PL 像を作る(定常拡散方程式の厳密解 + 光学 PSF + 雑音)。

    Parameters
    ----------
    generation : array_like
        励起(生成)の場 ``g = G/G₀``(H×W、≥ 0)。一様 1 が「欠陥なしの地」。影の溝は
        ここを 0 にして作る(生成が欠けるだけで再結合は増えない)。
    sink : array_like or None
        追加の再結合率の場 ``k = στ``(H×W、≥ 0、無次元)。``None`` は 0。沈みの溝・転位・
        粒界はここを正にして作る。再結合速度 S[長さ/時間]の線なら ``k·w = S·L²/D``(画素
        単位)。
    diffusion_length_px : float
        拡散長 ``L = √(Dτ)``[px]。
    optical_psf_px : float
        光学系の PSF(ガウシアン σ[px])。0 で無効。拡散 PSF の**後**に掛かる。
    noise_rel : float
        加法ガウス雑音の σ(欠陥なしの地 1 に対する相対値)。0 で決定論。
    seed : int
        雑音の種。直接解に収まらない像(160,000 画素超)は共役勾配(相対残差 1e-10 固定)。

    Returns
    -------
    numpy.ndarray
        ``(H, W)`` の float64。欠陥なし・一様励起なら厳密に 1。``u = Δn/(G₀τ)``。

    Notes
    -----
    境界は流束 0(Neumann)。だから一様な励起は端まで厳密に一様で、溝の採点に境界の
    暗化が混ざらない。方程式が線形なので ``generation`` の重ね合わせは像の重ね合わせ。

    Examples
    --------
    >>> import numpy as np
    >>> g = np.ones((1, 201)); g[0, 100] = 0.0            # 幅 1 px の影の溝
    >>> u = pl_image_simulate(g, diffusion_length_px=10.0)
    >>> rho = 1 + 0.5 / 100 - ((1 + 0.5 / 100) ** 2 - 1) ** 0.5
    >>> abs(float(1 - u[0, 100]) - (1 - 2 * rho / (1 + rho))) < 1e-9   # 格子の閉形式
    True
    >>> round(float(pl_image_simulate(np.ones((8, 8)))[3, 3]), 12)  # 一様 → 1(解法の丸めまで)
    1.0
    """
    op = "pl_image_simulate"
    g = _as_map(generation, "generation", op)
    if sink is None:
        k = np.zeros_like(g)
    else:
        k = _as_map(sink, "sink", op)
        if k.shape != g.shape:
            raise ValueError("%s: sink shape %r must match generation shape %r"
                             % (op, k.shape, g.shape))
    L = _positive(diffusion_length_px, "diffusion_length_px", op)
    psf = _nonneg(optical_psf_px, "optical_psf_px", op)
    nz = _nonneg(noise_rel, "noise_rel", op)

    u = _solve_diffusion(g, k, L, _CG_RTOL)
    if psf > 0.0:
        from scipy import ndimage as _ndi
        u = _ndi.gaussian_filter(u, psf, mode="nearest")
    if nz > 0.0:
        rng = np.random.default_rng(int(seed))
        u = u + rng.normal(0.0, nz, u.shape)
    return u


# --------------------------------------------------------------------------- #
# 3. 溝の見え方(閉形式)                                                        #
# --------------------------------------------------------------------------- #
def pl_groove_visibility(width_px: float = 3.0, diffusion_length_px: float = 8.0, *,
                         sink_velocity: float = 0.0, noise_rel: float = 0.01,
                         cnr_min: float = 1.0) -> dict:
    """溝の幅・拡散長・雑音から、影の溝と沈みの溝のコントラストと CNR を閉形式で返す(``table``)。

    Parameters
    ----------
    width_px : float
        溝の幅 w[px]。
    diffusion_length_px : float
        拡散長 L[px]。
    sink_velocity : float
        沈みの溝の再結合速度 ``s = S·px/D``(無次元、1 画素あたり)。0 なら沈みの項は 0。
    noise_rel : float
        像の雑音 σ(地 1 に対する相対値)。CNR = コントラスト / σ。
    cnr_min : float
        「見える」とする CNR の下限(既定 1 = 雑音と同じ深さ)。

    Returns
    -------
    dict
        ``contrast_shadow``(連続 ``1 − e^{−w/2L}``)/ ``contrast_shadow_grid``(w が奇数の
        整数なら格子の厳密値、そうでなければ ``None``)/ ``contrast_sink``(``sL/(sL+2)``)/
        ``fwhm_shadow_px`` / ``fwhm_sink_px``(``2L·ln2``)/ ``cnr_shadow`` / ``cnr_sink`` /
        ``visible_shadow`` / ``visible_sink`` / ``L_star_shadow_px``(この L **より長いと**
        影は CNR < cnr_min で消える)/ ``L_star_sink_px``(この L **より短いと**沈みは
        消える。``sink_velocity = 0`` か ``cnr_min·noise_rel ≥ 1`` なら境界が無いので
        ``None`` = どの L でも見えない)/ ``deficit_shadow_px``(影の欠け量の積分 = w、
        L によらない)。

    Notes
    -----
    影は ``w ≪ L`` で ``≈ w/2L`` と消え、沈みは L と共に深く広くなる。欠陥の種類で
    向きが逆なので、「拡散長が長いほど欠陥が隠れる」は影にだけ当てはまる。

    Examples
    --------
    >>> t = pl_groove_visibility(2.0, 20.0, sink_velocity=0.5, noise_rel=0.02)
    >>> round(t["contrast_shadow"], 4)
    0.0488
    >>> round(t["contrast_sink"], 4)
    0.8333
    >>> t["visible_shadow"], t["visible_sink"]
    (True, True)
    """
    op = "pl_groove_visibility"
    w = _positive(width_px, "width_px", op)
    L = _positive(diffusion_length_px, "diffusion_length_px", op)
    s = _nonneg(sink_velocity, "sink_velocity", op)
    sig = _positive(noise_rel, "noise_rel", op)
    cmin = _positive(cnr_min, "cnr_min", op)

    c_sh = 1.0 - np.exp(-w / (2.0 * L))
    grid = None
    if abs(w - round(w)) < 1e-12 and int(round(w)) % 2 == 1:
        m = (int(round(w)) - 1) // 2
        rho = _grid_rho(L)
        grid = 1.0 - 2.0 * rho ** (m + 1) / (1.0 + rho)
    c_sk = s * L / (s * L + 2.0) if s > 0.0 else 0.0
    # 影の沈みの横顔: |x| ≥ w/2 で exp(−|x|/L)·sinh(w/2L)。半値の位置から FWHM。
    half = 0.5 * c_sh
    x_half = L * np.log(2.0 * np.sinh(w / (2.0 * L)) / c_sh) if c_sh > 0 else 0.0
    fwhm_sh = 2.0 * max(x_half, 0.0) if x_half > 0 else w
    fwhm_sk = 2.0 * L * np.log(2.0)
    cnr_sh, cnr_sk = c_sh / sig, c_sk / sig
    thr = cmin * sig
    if thr < 1.0:
        L_sh = -w / (2.0 * np.log(1.0 - thr))                 # 1 − e^{−w/2L} = thr
        L_sk = (2.0 * thr / (s * (1.0 - thr))) if s > 0.0 else None   # sL/(sL+2) = thr
    else:
        L_sh, L_sk = 0.0, None
    return {
        "width_px": w, "diffusion_length_px": L, "sink_velocity": s, "noise_rel": sig,
        "contrast_shadow": float(c_sh), "contrast_shadow_grid": (None if grid is None else float(grid)),
        "contrast_sink": float(c_sk),
        "fwhm_shadow_px": float(fwhm_sh), "fwhm_sink_px": float(fwhm_sk),
        "half_depth_shadow": float(half),
        "cnr_shadow": float(cnr_sh), "cnr_sink": float(cnr_sk),
        "visible_shadow": bool(cnr_sh >= cmin), "visible_sink": bool(cnr_sk >= cmin),
        "L_star_shadow_px": float(L_sh), "L_star_sink_px": (None if L_sk is None else float(L_sk)),
        "deficit_shadow_px": float(w),
    }
