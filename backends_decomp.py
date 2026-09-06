"""Image DECOMPOSITION operators (registry cluster ``decomp``, name prefix ``dc_``).

Each operator separates a single gray image into physically meaningful components
— the workhorse of industrial surface inspection, where a *defect* is precisely
the part of the image that does NOT belong to the smooth / low-rank / illuminated
background model.  Every op is a GENUINE algorithm; none reproduces a specific
MVTec HALCON operator, so ``Op.halcon`` is ``""`` throughout (these add new
capability, they are not a coverage claim):

  dc_structure_texture   TV-L2 (Rudin-Osher-Fatemi) structure / cartoon part,
                         via Chambolle's dual projection.  a = smoothness weight.
  dc_texture_residual    the TEXTURE / detail layer = input - structure, centred
                         at gray 0.5 (the defect layer for inspection).
  dc_rpca_lowrank        robust-PCA (Principal Component Pursuit) LOW-RANK part
                         via alternating singular-value + element soft-threshold.
                         a = sparsity/rank threshold.
  dc_rpca_sparse         the SPARSE (defect / anomaly) residual = input - low-rank,
                         centred at 0.5.
  dc_retinex             single-scale retinex  log(I) - log(Gauss_sigma(I)),
                         fixed log-domain gain -> [0,1].  a = scale, b = gain.
                         Illumination-invariant reflectance.
  dc_local_contrast_norm local contrast normalisation  (I - mean_w) / (std_w),
                         centred at 0.5.  a = window.
  dc_homomorphic         homomorphic filter — high-emphasis of log(I) in the
                         Fourier domain (illumination flatten).  a = cutoff.

Contract: ``fn(v, a, b)`` maps a 2-D float64 image in [0,1] + two knobs a,b in
[0,1] to a 2-D float64 image in [0,1].  Deterministic, finite, fail-soft.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import fsthreads

_EPS = 1e-3


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _img(v):
    """Coerce to a finite 2-D float64 image in [0,1] (fail-soft)."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:                       # accidental colour -> luma
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    if x.ndim != 2:
        x = x.reshape(1, -1)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


def _win(a, lo=3, hi=15):
    """Odd window size in [lo, hi] driven by a in [0,1]."""
    w = int(round(lo + a * (hi - lo)))
    if w % 2 == 0:
        w += 1
    return max(lo, min(hi, w))


# --- total-variation (ROF) structure via Chambolle's projection ------------ #
def _fwd_grad(u):
    gx = np.zeros_like(u)
    gy = np.zeros_like(u)
    gx[:, :-1] = u[:, 1:] - u[:, :-1]
    gy[:-1, :] = u[1:, :] - u[:-1, :]
    return gx, gy


def _bwd_div(px, py):
    d = np.zeros_like(px)
    d[:, 1:-1] += px[:, 1:-1] - px[:, :-2]
    d[:, 0] += px[:, 0]
    d[:, -1] += -px[:, -2]
    d[1:-1, :] += py[1:-1, :] - py[:-2, :]
    d[0, :] += py[0, :]
    d[-1, :] += -py[-2, :]
    return d


def _tv_structure(img, a, n_iter=120, tau=0.125):
    """ROF/TV-L2 denoise (Chambolle 2004 dual): returns the clipped cartoon part.

    Minimises  ||u-f||^2/(2*weight) + TV(u).  Larger ``weight`` -> smoother
    (more cartoon).  a in [0,1] maps to weight in ~[0.02, 0.30].
    """
    f = np.asarray(img, np.float64)
    if f.size < 4 or min(f.shape) < 2:
        # A 1xN / Nx1 strip has no 2-D divergence (``_bwd_div`` indexes [-2]);
        # the sort-correct degenerate answer is "all structure": u == f, so the
        # texture residual is exactly 0.5.  Raising here made the fail-soft
        # wrapper hand back the INPUT as the "texture" (2026-09-02 review).
        return np.clip(f, 0.0, 1.0)
    weight = 0.02 + 0.28 * float(a)
    px = np.zeros_like(f)
    py = np.zeros_like(f)
    for _ in range(n_iter):
        d = _bwd_div(px, py) - f / weight
        gx, gy = _fwd_grad(d)
        gn = np.sqrt(gx * gx + gy * gy)
        denom = 1.0 + tau * gn
        px = (px + tau * gx) / denom
        py = (py + tau * gy) / denom
    u = f - weight * _bwd_div(px, py)
    return np.clip(u, 0.0, 1.0)


# --- robust PCA (Principal Component Pursuit, inexact ALM) ------------------ #
def _soft(x, t):
    return np.sign(x) * np.maximum(np.abs(x) - t, 0.0)


def _rpca(img, a, max_iter=60, work_max=64):
    """Split M = L + S (low-rank + sparse) via inexact ALM PCP (Lin/Chen/Ma 2010).

    a scales the sparsity penalty lambda around the canonical 1/sqrt(max(m,n));
    larger a -> sparser S / higher-rank L.  Large images are decomposed at a
    downsampled scale (<= work_max) for a bounded number of SVDs.  Only the
    LOW-RANK part is scale-tolerant, so only L is solved at low resolution and
    resized back; the sparse part is then re-derived at FULL resolution as the
    residual ``S = soft(M0 - L_up, lam/mu_final)`` (one more PCP S-step against
    the upsampled background).  Zooming the low-resolution S instead (the
    2026-09-02 defect) smeared every 1-px defect across the zoom footprint and
    lost ~3/4 of its amplitude — 30/40 point defects vanished on a 144² image.
    Returns (L, S) with the original shape.
    """
    M0 = np.asarray(img, np.float64)
    H, W = M0.shape
    scaled = False
    if max(H, W) > work_max:
        factor = work_max / float(max(H, W))
        M = ndimage.zoom(M0, factor, order=1)
        scaled = True
    else:
        M = M0
    m, n = M.shape
    if m == 0 or n == 0:
        return M0.copy(), np.zeros_like(M0)
    # ★BLAS のスレッド上限をループの**外に 1 回**掛ける。ここは work_max=64 に
    # 抑えた正方行列を最大 60 回 SVD する場所で、この repo で分解時間の大半を
    # 使う(スイート 1 回で 30.7 秒 / 分解合計 31.4 秒、svd 23,987 回 = 98%)。
    # 64x64 の SVD は 24 スレッドだと 1 スレッドの 3.9 倍遅い —— 分解の中の GEMM が
    # 小さすぎて同期の費用が計算量を上回るため(表は fsthreads の docstring)。
    # 1 回ごとに囲むと仕掛けの 2.4us を 60 回払うので、ループの外に置く。
    with fsthreads.for_decomposition(min(m, n)):
        sv = np.linalg.svd(M, compute_uv=False)
        nrm2 = float(sv[0]) if sv.size else 0.0
        lam = (0.5 + 1.5 * float(a)) / np.sqrt(max(m, n))
        if nrm2 < 1e-12:                   # constant / empty image -> all low-rank
            return M0.copy(), np.zeros_like(M0)
        nrm_inf = float(np.max(np.abs(M))) / lam
        Y = M / max(nrm2, nrm_inf)
        mu = 1.25 / nrm2
        rho = 1.5
        mu_max = mu * 1e7
        S = np.zeros_like(M)
        L = np.zeros_like(M)
        normM = float(np.linalg.norm(M, "fro"))
        for _ in range(max_iter):
            U, s, Vt = np.linalg.svd(M - S + Y / mu, full_matrices=False)
            s_t = _soft(s, 1.0 / mu)
            rank = int((s_t > 0).sum())
            L = (U[:, :rank] * s_t[:rank]) @ Vt[:rank]
            S = _soft(M - L + Y / mu, lam / mu)
            Z = M - L - S
            Y = Y + mu * Z
            mu = min(mu * rho, mu_max)
            if float(np.linalg.norm(Z, "fro")) <= 1e-7 * (normM + 1e-12):
                break
    if scaled:
        L = ndimage.zoom(L, (H / L.shape[0], W / L.shape[1]), order=1)
        L = L[:H, :W]
        if L.shape != (H, W):              # zoom rounding guard
            L = np.resize(L, (H, W))
        # Sparse part at FULL resolution: the residual against the upsampled
        # background, soft-thresholded at the level the converged ALM used for
        # its last S-update (lam/mu is ~0 after convergence, so this is the
        # genuine per-pixel residual, not a blurred copy of the low-res S).
        S = _soft(M0 - L, lam / mu)
    return L, S


# --------------------------------------------------------------------------- #
# operators                                                                    #
# --------------------------------------------------------------------------- #
def dc_structure_texture(v, a, b):
    """Structure / cartoon part of the image (TV-L2, Chambolle).

    画像を「構造(cartoon)+テクスチャ」に分け、構造側を返す。ROF/TV-L2 モデル
    ``min_u ||u - f||^2 / (2*weight) + TV(u)`` を Chambolle(2004)の双対射影法で
    固定 120 反復(``tau=0.125``)解く。``weight = 0.02 + 0.28*a`` で、``a`` が
    大きいほど滑らか(平坦な区画が広がり、細かい模様が消える)、``a=0`` でも
    ごく弱い平滑が入る。``b`` は未使用。

    入力は 2 次元 float64・[0,1] に揃える(3 次元はチャネル平均、NaN→0、
    ±Inf→1/0)。返り値は入力と同形の float64、[0,1] に clip。飽和しない限り
    ``dc_structure_texture + (dc_texture_residual - 0.5) == 入力`` が成り立つ。
    1xN / Nx1 など 2 次元の発散が定義できない極小画像は入力をそのまま返す
    (構造=入力、テクスチャ=0.5)。例外時は fail-soft で入力のクリップ版が返り、
    backend_safe の台帳に記録される(strict モードでは再送出)。

    ガウスぼかしと違ってエッジ(段差)は保ち、模様・ノイズだけを落とす。反復数が
    固定なので大きな画像では収束しきらないことがある(残りはテクスチャ側に出る)。
    テクスチャ側だけが欲しければ ``dc_texture_residual``。周期模様の除去や
    欠陥検出の前処理として使い、後段に ``threshold`` や ``dyn_threshold``。
    背景が低ランク(縞・グラデーション)なら ``dc_rpca_lowrank`` も候補。
    """
    return _tv_structure(_img(v), a)


def dc_texture_residual(v, a, b):
    """Texture / detail layer = input - structure, centred at 0.5.

    ``structure + (texture - 0.5) == input`` wherever neither layer saturates.
    """
    img = _img(v)
    u = _tv_structure(img, a)
    return np.clip((img - u) + 0.5, 0.0, 1.0)


def dc_rpca_lowrank(v, a, b):
    """Robust-PCA low-rank (background) part.

    画像行列 ``M`` を ``M = L + S``(低ランク ``L`` + スパース ``S``)に分解する
    Principal Component Pursuit を inexact ALM(Lin/Chen/Ma 2010)で解き、``L``
    を返す。スパース項の重みは ``λ = (0.5 + 1.5*a) / sqrt(max(m, n))``(``m, n``
    は分解時の行列寸法)で、``a`` が大きいほど ``S`` が疎になり、その分 ``L`` に
    残る成分(ランク)が増える。``a=0`` では ``λ`` が小さく、ほとんどの変動が
    ``S`` に吸われて ``L`` はのっぺりする。``b`` は未使用。反復は最大 60 回、
    収束判定は ``||M - L - S||_F <= 1e-7 * ||M||_F``。

    長辺が 64 を超える画像は 64 に縮小して分解し、``L`` だけを線形補間で元の
    大きさに戻す(低ランク部は縮小に耐えるため)。入力は [0,1] の 2 次元 float64
    に揃え(3 次元はチャネル平均)、返り値も同形・[0,1] に clip。全零画像は入力を
    そのまま返す。BLAS のスレッド数は分解中だけ ``fsthreads`` で絞る(小行列の
    SVD ではスレッドが多いほど遅いため)。例外時は fail-soft で入力のクリップ版が
    返り、台帳に記録される。

    「行や列にわたって繰り返す構造」(縞、グラデーション、周期パターン)を背景と
    みなす分解なので、単一の 2 次元画像でも織物・シート・ディスプレイ画素などの
    周期背景から孤立欠陥を分離するのに向く。自然画像のような非周期背景では
    ``L`` は単なる低ランク近似で、意味のある背景にならない。対になる欠陥側は
    ``dc_rpca_sparse``(``L + (S - 0.5) == 入力``)。エッジ保存の平滑で構造を
    取りたいなら ``dc_structure_texture``。
    """
    img = _img(v)
    L, _ = _rpca(img, a)
    return np.clip(L, 0.0, 1.0)


def dc_rpca_sparse(v, a, b):
    """Robust-PCA sparse (defect / anomaly) residual = input - low-rank, at 0.5.

    ``dc_rpca_lowrank`` と同じ inexact ALM の PCP 分解 ``M = L + S`` を行い、
    スパース項 ``S`` を 0.5 を中心に置いて返す(``clip(S + 0.5, 0, 1)``)。背景と
    同じ画素は 0.5、背景より明るい孤立点は 0.5 より上、暗い点は下に出る符号つき
    残差で、飽和しない範囲で ``dc_rpca_lowrank + (この出力 - 0.5) == 入力``。
    ``a`` はスパース重み ``λ = (0.5 + 1.5*a)/sqrt(max(m, n))`` で、大きいほど
    ``S`` が疎(小さな残差は 0 に丸められ、はっきりした欠陥だけ残る)、``a=0``
    ではほぼ全画素に残差が出る。``b`` は未使用。

    長辺 64 超の画像は縮小して ``L`` を解き、``S`` は元解像度で
    ``S = soft(M0 - L_up, λ/μ_final)`` として作り直す(縮小した ``S`` を拡大
    すると 1 画素欠陥がにじんで振幅を失うため)。入力は [0,1] の 2 次元に揃え、
    返り値は同形 float64、[0,1]。全零画像では ``S = 0`` で一様 0.5。例外時は
    fail-soft で入力のクリップ版が返り、台帳に記録される。

    後段では ``|出力 - 0.5|`` が欠陥の強さなので、``threshold`` 系の op で 0.5 から
    離れた画素を拾う(明側・暗側のどちらを拾うかはしきい値の向きで決まる)。周期
    背景(織物・格子・ディスプレイ)上の点欠陥・傷の検出向けで、非周期背景では
    残差に背景の凹凸がそのまま混ざる。
    """
    img = _img(v)
    _, S = _rpca(img, a)
    return np.clip(S + 0.5, 0.0, 1.0)


def dc_retinex(v, a, b):
    """Single-scale retinex reflectance: log(I) - log(Gauss_sigma(I)) -> [0,1].

    Fixed log-domain gain (b) about mid-gray, NOT per-image min-max (which would
    re-inflate an already-flat image); a sets the Gaussian scale.
    """
    img = _img(v)
    if img.size < 2:
        return np.full_like(img, 0.5)
    sigma = 1.0 + float(a) * 0.5 * min(img.shape)
    g = ndimage.gaussian_filter(img, sigma, mode="reflect")
    r = np.log(img + _EPS) - np.log(g + _EPS)
    gain = 1.0 + 4.0 * float(b)            # log-units that map to +/-0.5
    return np.clip(0.5 + r / (2.0 * gain), 0.0, 1.0)


def dc_local_contrast_norm(v, a, b):
    """Local contrast normalisation: (I - mean_w) / (std_w + eps), centred at 0.5.

    a sets the window; b raises the std floor (suppresses flat-region noise gain).
    """
    img = _img(v)
    w = _win(a)
    mu = ndimage.uniform_filter(img, size=w, mode="reflect")
    var = ndimage.uniform_filter(img * img, size=w, mode="reflect") - mu * mu
    sd = np.sqrt(np.maximum(var, 0.0))
    floor = 0.02 + 0.18 * float(b)
    hp = (img - mu) / (sd + floor)
    return np.clip(0.5 + 0.25 * hp, 0.0, 1.0)


def dc_homomorphic(v, a, b):
    """Homomorphic filter: high-emphasis of log(I) in the Fourier domain -> [0,1].

    Attenuates low frequencies (illumination) and boosts high frequencies
    (reflectance detail).  a sets the cutoff radius; b the high/low gain spread.
    """
    img = _img(v)
    H, W = img.shape
    if H < 2 or W < 2:
        return img
    logi = np.log(img + _EPS)
    fu = np.fft.fftfreq(H)[:, None]
    fv = np.fft.fftfreq(W)[None, :]
    d2 = fu * fu + fv * fv
    d0 = 0.01 + 0.12 * float(a)            # normalized cutoff
    gl = 0.4                               # low-freq gain (<1 -> flatten illum.)
    gh = 1.5 + 1.5 * float(b)              # high-freq gain (>1 -> boost detail)
    filt = (gh - gl) * (1.0 - np.exp(-d2 / (2.0 * d0 * d0))) + gl
    out_log = np.fft.ifft2(np.fft.fft2(logi) * filt).real
    out = np.exp(out_log) - _EPS
    lo, hi = float(out.min()), float(out.max())
    if hi - lo < 1e-9:
        return np.full_like(img, 0.5)
    return np.clip((out - lo) / (hi - lo), 0.0, 1.0)


# --------------------------------------------------------------------------- #
# registry                                                                     #
# --------------------------------------------------------------------------- #
def _finish_clip01(out, v):
    arr = np.asarray(out, np.float64)
    arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(arr, 0.0, 1.0)


def _safe(fn):
    """Wrap so an op never raises on odd input; degrade to a clipped copy.

    Delegates to the shared, RECORDING guard (backend_safe.guard) with this
    backend's own post-processing kept bit-identical: failure -> ``_img(v)``,
    success -> nan_to_num + clip to [0,1].
    """
    from backend_safe import guard
    return guard(fn, "image", on_fail=_img, finish=_finish_clip01)


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    defs = [
        ("dc_structure_texture", "decomposition", "", dc_structure_texture),
        ("dc_texture_residual", "decomposition", "", dc_texture_residual),
        ("dc_rpca_lowrank", "decomposition", "", dc_rpca_lowrank),
        ("dc_rpca_sparse", "decomposition", "", dc_rpca_sparse),
        ("dc_retinex", "decomposition", "", dc_retinex),
        ("dc_local_contrast_norm", "decomposition", "", dc_local_contrast_norm),
        ("dc_homomorphic", "decomposition", "", dc_homomorphic),
    ]
    return [Op(name, cat, hal, IMAGE, IMAGE, _safe(fn)) for (name, cat, hal, fn) in defs]
