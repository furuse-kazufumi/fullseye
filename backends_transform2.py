"""Domain / coordinate transform image operators (registry cluster ``tf_``).

Every operator maps a 2-D gray image to a 2-D gray image (``in_sort == out_sort
== "image"``) and implements the GENUINE algorithm named below. None of these
names is a real MVTec HALCON operator that is currently uncovered:

  * ``log_polar`` / ``radon_sinogram`` / ``steerable_filter`` /
    ``phase_congruency`` / ``gradient_domain_reintegrate`` are NOT present in
    ``data/halcon_graph.json`` at all, so no coverage claim is possible.
  * ``census_transform`` and ``rank_transform`` are the stereo-vision
    (Zabih & Woodfill 1994) non-parametric local transforms. Neither string is
    in ``data/halcon_graph.json`` -- HALCON's ``rank_image`` / ``rank_rect1`` are
    a *rank-order filter* (a different operator, already covered), NOT the
    relative-rank census/rank transform implemented here. So both carry
    ``halcon == ""`` -- an honest "new capability, no HALCON analog".

Contract: ``fn(v, a, b)`` takes a 2-D float64 image in [0,1] plus two evolution
knobs ``a, b`` in [0,1] and returns a finite 2-D float64 image in [0,1].
Deterministic, fail-soft (never raises on the canonical battery; the ``_safe``
wrapper degrades a raised op to a benign clipped input).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:  # noqa: BLE001 - fail-soft per op contract
            out = None
        return sanitize(out, v, out_sort)

    return w


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _img(v):
    """Coerce input to a finite 2-D float64 image in [0,1] (fail-soft)."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


def _signed01(x):
    """Map a signed response to [0,1] with the zero-crossing pinned at 0.5."""
    x = np.asarray(x, np.float64)
    m = float(np.max(np.abs(x))) if x.size else 0.0
    if m <= 1e-12:
        return np.full(x.shape, 0.5, np.float64)
    return np.clip(x / (2.0 * m) + 0.5, 0.0, 1.0)


def _unit01(x):
    """Rescale any finite array to [0,1] by its own min/max (flat -> zeros)."""
    x = np.asarray(x, np.float64)
    lo = float(np.min(x)) if x.size else 0.0
    hi = float(np.max(x)) if x.size else 0.0
    if hi - lo <= 1e-12:
        return np.zeros(x.shape, np.float64)
    return (x - lo) / (hi - lo)


# 8-neighbour offsets (row, col), fixed order -> stable bit weights 2**0..2**7
_NB8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


# --------------------------------------------------------------------------- #
# operators                                                                    #
# --------------------------------------------------------------------------- #
def tf_log_polar(v, a, b):
    """log_polar: resample the image on a log-polar grid about its centre.

    Output row = log-radius (log-spaced from ~1px to ``rmax``), output column =
    angle (0..2pi). A scaling of the source about the centre becomes a vertical
    (row) shift and a rotation becomes a horizontal (column) shift -- the defining
    property of the log-polar transform. ``a`` scales the maximum sampled radius;
    ``b`` adds a rotation offset (an angular shift) to demonstrate rotation ->
    column-shift."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 3 or W < 3:
        return x
    cy = (H - 1) / 2.0
    cx = (W - 1) / 2.0
    rmax = 0.5 * min(H, W) * (0.4 + 0.6 * float(np.clip(a, 0.0, 1.0)))
    rmax = max(rmax, 2.0)
    rmin = 1.0
    i = np.arange(H, dtype=np.float64)
    rr = rmin * (rmax / rmin) ** (i / (H - 1))              # log-spaced radii
    j = np.arange(W, dtype=np.float64)
    th = 2.0 * np.pi * (j / W) + 2.0 * np.pi * float(np.clip(b, 0.0, 1.0))
    R, TH = np.meshgrid(rr, th, indexing="ij")             # HxW
    ys = cy + R * np.sin(TH)
    xs = cx + R * np.cos(TH)
    out = ndimage.map_coordinates(
        x, np.vstack([ys.ravel(), xs.ravel()]),
        order=1, mode="constant", cval=0.0,
    )
    return np.clip(out.reshape(H, W), 0.0, 1.0)


def tf_radon_sinogram(v, a, b):
    """radon_sinogram: the Radon transform rendered as an HxW sinogram image.

    Row ``i`` is the parallel-beam projection at angle ``theta_i`` (the image
    rotated by ``theta_i`` and summed down its columns); the W columns index the
    detector position. ``a`` sets the angular span (limited-angle tomography:
    span = 180deg * (0.25 + 0.75*a)); ``b`` is unused. The sinogram is rescaled
    to [0,1]. A rotationally symmetric object gives angle-independent (identical)
    rows; an off-centre point traces the classic sine wave."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 3 or W < 3:
        return x
    span = 180.0 * (0.25 + 0.75 * float(np.clip(a, 0.0, 1.0)))
    angles = np.linspace(0.0, span, H, endpoint=False)
    sino = np.empty((H, W), np.float64)
    for k, ang in enumerate(angles):
        rot = ndimage.rotate(
            x, float(ang), reshape=False, order=1, mode="constant", cval=0.0,
        )
        sino[k, :] = rot.sum(axis=0)
    return _unit01(sino)


def tf_steerable_filter(v, a, b):
    """steerable_filter: oriented first-derivative-of-Gaussian response.

    The steerable G1 basis: the derivative of a Gaussian at orientation
    ``theta = a*pi`` is ``cos(theta)*Gx + sin(theta)*Gy`` where Gx, Gy are the
    x/y partial derivatives of the Gaussian-smoothed image. ``b`` sets the
    Gaussian sigma. The signed response is mapped to [0,1] (0.5 = zero), so its
    deviation from 0.5 peaks on edges whose gradient matches ``theta``."""
    x = _img(v)
    if x.shape[0] < 2 or x.shape[1] < 2:
        return x
    sigma = 0.8 + 3.0 * float(np.clip(b, 0.0, 1.0))
    gx = ndimage.gaussian_filter(x, sigma, order=(0, 1), mode="nearest")
    gy = ndimage.gaussian_filter(x, sigma, order=(1, 0), mode="nearest")
    theta = float(np.clip(a, 0.0, 1.0)) * np.pi
    resp = np.cos(theta) * gx + np.sin(theta) * gy
    return _signed01(resp)


def tf_phase_congruency(v, a, b):
    """phase_congruency: a simplified monogenic phase-congruency feature map.

    Multi-scale radial log-Gabor bandpass responses (even part) plus their Riesz
    (monogenic odd) components are accumulated; phase congruency is
    ``|sum of the (even, odd1, odd2) energy vectors| / (sum of amplitudes)``.
    Because both numerator and denominator scale linearly with image gain and the
    log-Gabor filters carry no DC, the result is invariant to affine illumination
    change. ``a`` is a noise threshold (fraction of mean energy); ``b`` scales the
    base wavelength. Peaks at edges/lines where the phases align."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 4 or W < 4:
        return x
    u = np.fft.fftfreq(W)[None, :]
    w = np.fft.fftfreq(H)[:, None]
    radius = np.sqrt(u * u + w * w)
    radius[0, 0] = 1.0                                     # avoid /0 for Riesz
    riesz_x = 1j * u / radius
    riesz_y = 1j * w / radius
    F = np.fft.fft2(x)
    n_scale = 4
    min_wave = 3.0 * (0.5 + float(np.clip(b, 0.0, 1.0)))
    mult = 2.1
    sigma_onf = 0.55
    ln_son2 = 2.0 * np.log(sigma_onf) ** 2
    sum_e = np.zeros((H, W), np.float64)
    sum_h1 = np.zeros((H, W), np.float64)
    sum_h2 = np.zeros((H, W), np.float64)
    sum_an = np.zeros((H, W), np.float64)
    for s in range(n_scale):
        wavelength = min_wave * (mult ** s)
        f0 = 1.0 / wavelength
        lg = np.exp(-(np.log((radius + 1e-12) / f0) ** 2) / ln_son2)
        lg[0, 0] = 0.0                                     # kill DC
        flg = F * lg
        even = np.fft.ifft2(flg).real
        h1 = np.fft.ifft2(flg * riesz_x).real
        h2 = np.fft.ifft2(flg * riesz_y).real
        sum_e += even
        sum_h1 += h1
        sum_h2 += h2
        sum_an += np.sqrt(even * even + h1 * h1 + h2 * h2)
    energy = np.sqrt(sum_e * sum_e + sum_h1 * sum_h1 + sum_h2 * sum_h2)
    thresh = float(np.clip(a, 0.0, 1.0)) * float(energy.mean())
    energy = np.maximum(energy - thresh, 0.0)
    pc = energy / (sum_an + 1e-8)
    return np.clip(pc, 0.0, 1.0)


def tf_gradient_domain_reintegrate(v, a, b):
    """gradient_domain_reintegrate: threshold the gradient, then Poisson-reintegrate.

    The forward gradient (gx, gy) is computed, gradient vectors whose magnitude is
    below a threshold ``t = a * max|grad|`` are zeroed (small texture/noise
    gradients discarded, strong edges kept), and the image is reconstructed from
    the modified gradient field by solving the Poisson equation
    ``lap f = div(g)`` with an FFT solver. With ``a == 0`` every gradient is kept
    and the original image is recovered (up to a constant); with ``a > 0`` flat
    regions are flattened while edges survive -- an edge-preserving gradient-domain
    filter. ``b`` is unused. Output rescaled to [0,1]."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 3 or W < 3:
        return x
    # forward differences (periodic)
    gx = np.roll(x, -1, axis=1) - x
    gy = np.roll(x, -1, axis=0) - x
    mag = np.hypot(gx, gy)
    mmax = float(mag.max())
    if mmax > 1e-12:
        t = float(np.clip(a, 0.0, 1.0)) * mmax
        keep = mag >= t
        gx = gx * keep
        gy = gy * keep
    # divergence via backward differences (adjoint of forward diff)
    div = (gx - np.roll(gx, 1, axis=1)) + (gy - np.roll(gy, 1, axis=0))
    # Poisson solve in the Fourier domain (periodic BC)
    wy = 2.0 * np.pi * np.fft.fftfreq(H)[:, None]
    wx = 2.0 * np.pi * np.fft.fftfreq(W)[None, :]
    denom = (2.0 * np.cos(wy) - 2.0) + (2.0 * np.cos(wx) - 2.0)
    denom[0, 0] = 1.0                                      # DC handled separately
    fhat = np.fft.fft2(div) / denom
    fhat[0, 0] = 0.0                                       # zero-mean solution
    f = np.fft.ifft2(fhat).real
    return _unit01(f + float(x.mean()))


def tf_census_transform(v, a, b):
    """census_transform: the 3x3 non-parametric census bit-signature image.

    For every pixel each of its 8 neighbours contributes one bit, set when the
    centre exceeds the neighbour by more than a *relative* tolerance
    ``a * |centre|`` (``a`` defaults the tolerance; ``b`` unused). The 8 bits form
    a value 0..255 rendered as [0,1]. Because the tolerance is relative and the
    comparison is on ordering only, the signature is invariant to a global gain
    (multiplying the image by any positive constant leaves every bit unchanged) --
    the robustness-to-gain property that makes census matching useful for stereo.
    Uses the raw (non-luma-collapsed) reflected border."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 2 or W < 2:
        return x
    pad = np.pad(x, 1, mode="reflect")
    centre = x
    tol = float(np.clip(a, 0.0, 1.0)) * np.abs(centre)
    code = np.zeros((H, W), np.float64)
    for k, (dr, dc) in enumerate(_NB8):
        nb = pad[1 + dr:1 + dr + H, 1 + dc:1 + dc + W]
        bit = (centre - nb) > tol
        code += bit.astype(np.float64) * float(1 << k)
    return code / 255.0


def tf_rank_transform(v, a, b):
    """rank_transform: the local rank of each pixel among its neighbours.

    Each pixel's value is the fraction of neighbours in a ``(2r+1)x(2r+1)`` window
    that it strictly exceeds (``r = 1 + round(a*2)``; ``b`` unused), i.e. its
    ordinal rank normalized to [0,1]. Like the census transform it depends only on
    pixel ordering, so it is invariant to a global gain: multiplying the image by
    any positive constant leaves every rank unchanged (robust to illumination gain
    for stereo/texture)."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 2 or W < 2:
        return x
    r = 1 + int(round(float(np.clip(a, 0.0, 1.0)) * 2))
    r = max(1, min(r, 3))
    pad = np.pad(x, r, mode="reflect")
    centre = x
    count = np.zeros((H, W), np.float64)
    n_nb = 0
    for dr in range(-r, r + 1):
        for dc in range(-r, r + 1):
            if dr == 0 and dc == 0:
                continue
            n_nb += 1
            nb = pad[r + dr:r + dr + H, r + dc:r + dc + W]
            count += (centre > nb).astype(np.float64)
    if n_nb == 0:
        return np.zeros((H, W), np.float64)
    return count / float(n_nb)


# --------------------------------------------------------------------------- #
# registry                                                                     #
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # every op is a NEW capability with no genuine uncovered HALCON analog -> halcon=""
    defs = [
        ("tf_log_polar", "geometry", "", tf_log_polar),
        ("tf_radon_sinogram", "transform", "", tf_radon_sinogram),
        ("tf_steerable_filter", "edges", "", tf_steerable_filter),
        ("tf_phase_congruency", "edges", "", tf_phase_congruency),
        ("tf_gradient_domain_reintegrate", "filtering", "", tf_gradient_domain_reintegrate),
        ("tf_census_transform", "texture", "", tf_census_transform),
        ("tf_rank_transform", "texture", "", tf_rank_transform),
    ]
    return [Op(n, c, h, IMAGE, IMAGE, _safe(f, IMAGE)) for (n, c, h, f) in defs]
