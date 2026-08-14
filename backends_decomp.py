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
    if f.size < 4:
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
    downsampled scale (<= work_max) for a bounded number of SVDs, then resized
    back (the low-rank/sparse split is scale-tolerant).  Returns (L, S) with the
    original shape.
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
    sv = np.linalg.svd(M, compute_uv=False)
    nrm2 = float(sv[0]) if sv.size else 0.0
    lam = (0.5 + 1.5 * float(a)) / np.sqrt(max(m, n))
    if nrm2 < 1e-12:                       # constant / empty image -> all low-rank
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
        S = ndimage.zoom(S, (H / S.shape[0], W / S.shape[1]), order=1)
        L = L[:H, :W]
        S = S[:H, :W]
        if L.shape != (H, W):              # zoom rounding guard
            L = np.resize(L, (H, W))
            S = np.resize(S, (H, W))
    return L, S


# --------------------------------------------------------------------------- #
# operators                                                                    #
# --------------------------------------------------------------------------- #
def dc_structure_texture(v, a, b):
    """Structure / cartoon part of the image (TV-L2, Chambolle)."""
    return _tv_structure(_img(v), a)


def dc_texture_residual(v, a, b):
    """Texture / detail layer = input - structure, centred at 0.5.

    ``structure + (texture - 0.5) == input`` wherever neither layer saturates.
    """
    img = _img(v)
    u = _tv_structure(img, a)
    return np.clip((img - u) + 0.5, 0.0, 1.0)


def dc_rpca_lowrank(v, a, b):
    """Robust-PCA low-rank (background) part."""
    img = _img(v)
    L, _ = _rpca(img, a)
    return np.clip(L, 0.0, 1.0)


def dc_rpca_sparse(v, a, b):
    """Robust-PCA sparse (defect / anomaly) residual = input - low-rank, at 0.5."""
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
def _safe(fn):
    """Wrap so an op never raises on odd input; degrade to a clipped copy."""
    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:  # noqa: BLE001  # fail-soft: an op must never raise
            out = None
        if out is None:
            return _img(v)
        arr = np.asarray(out, np.float64)
        arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
        return np.clip(arr, 0.0, 1.0)
    return w


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
