"""Sensor / sim-to-real corruption and augmentation operators (registry cluster ``aug_``).

This cluster models the way a REAL camera degrades an ideal (simulated or clean)
image: photon shot noise, sensor read noise, fixed-pattern non-uniformity, motion
blur, lens vignetting, lateral chromatic aberration, rolling-shutter shear, JPEG
block artefacts, occlusion (cutout / random erasing) and radial lens distortion.
Chained together they form the classic *domain-randomisation* / sim-to-real
pipeline used to stress-test an evolved vision policy: a pipeline that only
survives on pristine input is not a pipeline you can deploy on a camera.

None of these operators reproduces a HALCON operator -- MVTec HALCON has no
sensor-degradation / augmentation family (it offers image *restoration*, not
deliberate corruption; there is no shot-noise, fixed-pattern-noise,
rolling-shutter, JPEG-block, cutout or barrel-distortion *synthesis* operator).
Every op therefore carries ``halcon = ""`` and makes NO coverage claim; this is a
brand-new capability.

  aug_shot_noise       Poisson (photon shot) noise, the fundamental quantum limit
                       of any photon-counting sensor: ``Poisson(v*K)/K`` with
                       photon scale ``K = 5 + 250*(1-a)``. a = signal level
                       (a=0 -> K=5, extremely noisy; a=1 -> K=255, near-clean).
                       b = a small dark-current offset added before counting.
  aug_read_noise       additive Gaussian read noise (amplifier / ADC noise) with
                       ``sigma = 0.005 + 0.15*a``; b mixes in a row-correlated
                       component (per-row bias, i.e. horizontal banding, the
                       signature of a shared row amplifier).
  aug_fixed_pattern    fixed-pattern noise (FPN / PRNU): a per-column plus
                       per-row static offset that does NOT change between frames.
                       a = amplitude ``0.02 + 0.2*a``; b = which fixed pattern
                       (the pattern is seeded from b, so it is stable per knob).
  aug_motion_blur      linear motion blur: convolution with a normalised line
                       (box) kernel. a = exposure-streak length
                       ``L = 3 + 20*a`` px (forced odd, clamped to the image),
                       b = streak angle ``b*180`` degrees.
  aug_vignette         radial lens vignetting following the natural cos^4 falloff
                       law, ``1/(1+(r/R)^2)^2``, centre-bright. a = strength
                       (0 = off, 1 = full cos^4), b = falloff radius R.
  aug_chromatic        lateral chromatic aberration proxy on a gray image: the
                       high-pass (edge) component is shifted by
                       ``1 + int(4*a)`` px and added back, producing the coloured
                       fringe's intensity signature at edges. b = fringe blend
                       amplitude. Flat areas are untouched (high-pass = 0).
  aug_rolling_shutter  rolling-shutter skew: a per-row horizontal shift linear in
                       the row index (rows are exposed at different times while
                       the scene pans). a = maximum shift ``0.25*W*a`` px,
                       b = pan direction (b < 0.5 -> one way, else the other).
  aug_jpeg_blocks      JPEG compression artefacts: 8x8 block DCT (scipy.fft.dctn),
                       quantisation with the standard JPEG luminance table scaled
                       by ``(1 + 40*a)/16``, then inverse DCT -- producing genuine
                       blocking and ringing. b shifts the 8x8 block grid phase
                       (``int(7*b)`` px), i.e. where the block seams land.
  aug_cutout           Cutout / random-erasing occlusion: a rectangular patch of
                       side ``a*min(H,W)`` is erased. b picks the (deterministic)
                       patch position AND the fill: b <= 0.5 -> black (0.0),
                       b > 0.5 -> mid-gray (0.5).
  aug_barrel           radial lens distortion, the standard division/polynomial
                       model ``r' = r*(1 + k*r^2)``: barrel when b < 0.5, pincushion
                       when b >= 0.5, with ``k = 0.6*a``. Resampled with bilinear
                       ``ndimage.map_coordinates`` (mode="reflect").

Determinism honesty: these ops are DETERMINISTIC given (a, b) -- the "random"
noise/pattern/position is a fixed realisation seeded from the knobs, not a fresh
draw per call. That is required by the registry contract (repeated calls must be
bit-identical for reproducible holdout scoring), but it means a single op call is
one fixed noise realisation, not per-call stochastic augmentation; sweep the
knobs to sample the noise ensemble.

Contract: ``fn(v, a, b)`` maps a 2-D float64 image in [0,1] (plus knobs
a,b in [0,1]) to a 2-D float64 image in [0,1]. Deterministic, finite, fail-soft
(never raises on the canonical battery); every output is refit to the input HxW.
"""
from __future__ import annotations

import numpy as np
from scipy import fft as sfft
from scipy import ndimage


# --------------------------------------------------------------------------- #
# safety wrapper (shared pattern with the other backends)                     #
# --------------------------------------------------------------------------- #
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
# small helpers                                                               #
# --------------------------------------------------------------------------- #
def _img(v):
    """Coerce input to a finite 2-D float64 image in [0,1] (fail-soft)."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:                       # accidental colour -> luma
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


def _k(x):
    """Clamp a knob into [0,1] as a plain finite float."""
    try:
        f = float(x)
    except Exception:  # noqa: BLE001 - knob may be a weird scalar
        return 0.0
    if not np.isfinite(f):
        return 0.0
    return min(1.0, max(0.0, f))


def _rng(a, b, salt=0):
    """A numpy Generator seeded DETERMINISTICALLY from the knobs.

    The registry forbids unseeded randomness (repeated calls must be
    bit-identical), so every stochastic op derives its seed from (a, b) only.
    """
    seed = int(_k(a) * 100000) * 7919 + int(_k(b) * 100000) * 104729 + 12345 + int(salt)
    return np.random.default_rng(abs(seed) % (2 ** 63 - 1))


def _odd(n, hi):
    """Nearest odd integer <= hi (and >= 1) -- kernel sizes clamped to the image."""
    n = int(max(1, round(n)))
    hi = int(max(1, hi))
    if n > hi:
        n = hi
    if n % 2 == 0:
        n -= 1
    return max(1, n)


def _fit(x, H, W):
    """Crop/pad (edge-replicate) a 2-D array to exactly (H, W)."""
    x = np.asarray(x, np.float64)
    h, w = x.shape[:2]
    if (h, w) == (H, W):
        return x
    out = np.zeros((H, W), np.float64)
    hh, ww = min(h, H), min(w, W)
    out[:hh, :ww] = x[:hh, :ww]
    if hh < H and hh > 0:
        out[hh:, :ww] = out[hh - 1, :ww]
    if ww < W and ww > 0:
        out[:, ww:] = out[:, ww - 1][:, None]
    return out


# standard JPEG (Annex K) luminance quantisation table -- the real thing.
_JPEG_LUMA_Q = np.array([
    [16, 11, 10, 16, 24, 40, 51, 61],
    [12, 12, 14, 19, 26, 58, 60, 55],
    [14, 13, 16, 24, 40, 57, 69, 56],
    [14, 17, 22, 29, 51, 87, 80, 62],
    [18, 22, 37, 56, 68, 109, 103, 77],
    [24, 35, 55, 64, 81, 104, 113, 92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103, 99],
], np.float64)


def _line_kernel(length, angle_deg):
    """Normalised linear motion-blur kernel of ``length`` px at ``angle_deg``."""
    L = int(max(1, length))
    if L % 2 == 0:
        L -= 1
    L = max(1, L)
    k = np.zeros((L, L), np.float64)
    c = L // 2
    th = np.deg2rad(float(angle_deg))
    dy, dx = -np.sin(th), np.cos(th)
    for t in range(-c, c + 1):
        r = int(round(c + t * dy))
        s = int(round(c + t * dx))
        if 0 <= r < L and 0 <= s < L:
            k[r, s] += 1.0
    tot = k.sum()
    if tot <= 1e-12:
        k[c, c] = 1.0
        tot = 1.0
    return k / tot


# --------------------------------------------------------------------------- #
# operators (module-level so tests can call them directly)                    #
# --------------------------------------------------------------------------- #
def aug_shot_noise(v, a, b):
    """Photon (Poisson) shot noise -- the quantum floor of every image sensor.

    The image is interpreted as a normalised photon rate, scaled by the photon
    scale ``K = 5 + 250*(1-a)``, sampled from a Poisson distribution and scaled
    back: ``Poisson(v*K)/K``. Low ``a`` = few photons = very noisy (SNR ~ sqrt(K)).
    ``b`` adds a small dark-current pedestal (``0.05*b`` in rate units) before
    counting, so even a pure-black frame shows dark noise. The RNG is seeded from
    (a, b) -> the realisation is fixed per knob setting."""
    x = _img(v)
    a, b = _k(a), _k(b)
    K = 5.0 + 250.0 * (1.0 - a)
    dark = 0.05 * b
    lam = np.clip(x + dark, 0.0, 2.0) * K
    lam = np.nan_to_num(lam, nan=0.0, posinf=K, neginf=0.0)
    rng = _rng(a, b, salt=1)
    counts = rng.poisson(lam).astype(np.float64)
    return np.clip(counts / K, 0.0, 1.0)


def aug_read_noise(v, a, b):
    """Additive Gaussian READ noise (amplifier + ADC noise), sigma-independent of
    signal (unlike shot noise). ``sigma = 0.005 + 0.15*a``. ``b`` mixes in a
    row-correlated component: a per-row bias of std ``0.5*b*sigma`` shared by the
    whole row, which is what a shared row amplifier / row-wise ADC produces
    (visible as horizontal banding). Seeded from (a, b)."""
    x = _img(v)
    a, b = _k(a), _k(b)
    H, W = x.shape[:2]
    sigma = 0.005 + 0.15 * a
    rng = _rng(a, b, salt=2)
    n = rng.normal(0.0, sigma, size=(H, W))
    if b > 1e-9:
        rows = rng.normal(0.0, 0.5 * b * sigma, size=(H, 1))
        n = n + rows                      # broadcast: whole-row bias
    return np.clip(x + n, 0.0, 1.0)


def aug_fixed_pattern(v, a, b):
    """Fixed-pattern noise (FPN / photo-response non-uniformity). Unlike read
    noise this pattern is STATIC across frames: a per-column offset plus a
    per-row offset, each drawn once and held. ``a`` sets the amplitude
    ``0.02 + 0.2*a``; ``b`` selects WHICH fixed pattern (the generator is seeded
    from b alone, so sweeping a changes only the strength of one pattern).
    Column FPN dominates (2/3 weight) as it does in CMOS column-parallel ADCs."""
    x = _img(v)
    a, b = _k(a), _k(b)
    H, W = x.shape[:2]
    amp = 0.02 + 0.2 * a
    rng = np.random.default_rng(int(b * 100000) * 104729 + 12345)
    col = rng.normal(0.0, 1.0, size=(1, W))
    row = rng.normal(0.0, 1.0, size=(H, 1))
    pattern = (2.0 / 3.0) * col + (1.0 / 3.0) * row
    return np.clip(x + amp * pattern, 0.0, 1.0)


def aug_motion_blur(v, a, b):
    """Linear motion blur: convolution with a normalised LINE (box) kernel, the
    point-spread function of a constant-velocity camera/scene pan during the
    exposure. ``a`` sets the streak length ``L = 3 + 20*a`` px (forced odd and
    clamped so the kernel never exceeds the image), ``b`` sets the streak angle
    ``b*180`` degrees. Border handling is ``reflect`` so the frame edge does not
    darken. Energy-preserving (kernel sums to 1)."""
    x = _img(v)
    a, b = _k(a), _k(b)
    H, W = x.shape[:2]
    L = _odd(3 + 20.0 * a, min(H, W))
    if L <= 1:
        return x
    k = _line_kernel(L, b * 180.0)
    out = ndimage.convolve(x, k, mode="reflect")
    return np.clip(out, 0.0, 1.0)


def aug_vignette(v, a, b):
    """Radial lens vignetting following the natural cos^4 falloff law. With
    ``r`` the normalised distance from the image centre and ``R = 0.35 + 1.15*b``
    the falloff radius, the transmission is
    ``cos(atan(r/R))^4 = 1/(1 + (r/R)^2)^2`` -- the textbook cos^4 law. ``a``
    blends it in: ``out = v * (1 - a + a*falloff)``, so a=0 is a no-op and a=1 is
    full vignetting. Centre stays brightest; strictly darkening, never amplifying."""
    x = _img(v)
    a, b = _k(a), _k(b)
    H, W = x.shape[:2]
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    scale = max(1e-6, np.hypot(max(cy, 1e-6), max(cx, 1e-6)))
    r = np.hypot(yy - cy, xx - cx) / scale          # 0 at centre, 1 at corner
    R = 0.35 + 1.15 * b
    fall = 1.0 / (1.0 + (r / R) ** 2) ** 2
    return np.clip(x * (1.0 - a + a * fall), 0.0, 1.0)


def aug_chromatic(v, a, b):
    """Lateral chromatic aberration proxy for a gray image. True lateral CA
    magnifies the colour channels differently, so edges gain a coloured fringe;
    on a single channel the observable signature is a SHIFTED copy of the edge
    (high-pass) energy superposed on the image. Here the high-pass
    ``v - gaussian(v, 1)`` is shifted by ``s = 1 + int(4*a)`` px horizontally and
    added back with amplitude ``0.1 + 0.9*b``. Flat regions have zero high-pass,
    so only edges fringe -- exactly the real behaviour."""
    x = _img(v)
    a, b = _k(a), _k(b)
    H, W = x.shape[:2]
    s = 1 + int(4.0 * a)
    s = int(min(s, max(1, W - 1))) if W > 1 else 0
    hp = x - ndimage.gaussian_filter(x, sigma=1.0, mode="nearest")
    if s > 0:
        hp = ndimage.shift(hp, (0.0, float(s)), order=1, mode="reflect")
    amp = 0.1 + 0.9 * b
    return np.clip(x + amp * hp, 0.0, 1.0)


def aug_rolling_shutter(v, a, b):
    """Rolling-shutter skew. A CMOS rolling shutter exposes rows sequentially, so
    a scene (or camera) panning horizontally shifts each row by an amount linear
    in its row index -- a pure horizontal shear. ``a`` sets the peak shift
    ``0.25*W*a`` px (the shear is centred so the middle row is unmoved),
    ``b`` sets the pan direction (b < 0.5 -> shift right with increasing row,
    otherwise left). Resampled bilinearly with reflecting borders."""
    x = _img(v)
    a, b = _k(a), _k(b)
    H, W = x.shape[:2]
    if H < 2 or W < 2 or a <= 1e-9:
        return x
    max_shift = 0.25 * W * a
    sign = 1.0 if b < 0.5 else -1.0
    frac = np.arange(H, dtype=np.float64) / float(H - 1) - 0.5   # -0.5 .. +0.5
    shift = sign * max_shift * frac                              # per-row shift
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    src_x = xx - shift[:, None]
    coords = np.vstack([yy.ravel(), src_x.ravel()])
    out = ndimage.map_coordinates(x, coords, order=1, mode="reflect")
    return np.clip(out.reshape(H, W), 0.0, 1.0)


def aug_jpeg_blocks(v, a, b):
    """JPEG blocking / ringing artefacts. The image (scaled to 0..255) is cut
    into 8x8 blocks, each transformed with an orthonormal 2-D DCT-II
    (``scipy.fft.dctn``), quantised with the STANDARD JPEG Annex-K luminance
    table scaled by ``(1 + 40*a)/16`` (a=0 -> near-lossless, a=1 -> heavy
    quantisation), then reconstructed with the inverse DCT. ``b`` shifts the 8x8
    block grid phase by ``int(7*b)`` px in both axes, i.e. moves where the block
    seams fall. Images that are not a multiple of 8 are edge-replicate padded and
    cropped back to HxW (so 4x4 inputs are handled)."""
    x = _img(v)
    a, b = _k(a), _k(b)
    H, W = x.shape[:2]
    off = int(7.0 * b)
    off_y = min(off, max(0, H - 1)) if H > 1 else 0
    off_x = min(off, max(0, W - 1)) if W > 1 else 0
    # phase shift = pad the top/left by `off`, then pad up to a multiple of 8.
    ph, pw = H + off_y, W + off_x
    bh = int(np.ceil(ph / 8.0)) * 8
    bw = int(np.ceil(pw / 8.0)) * 8
    pad = np.pad(x, ((off_y, bh - ph), (off_x, bw - pw)), mode="edge")
    blocks = (pad * 255.0).reshape(bh // 8, 8, bw // 8, 8)
    D = sfft.dctn(blocks, axes=(1, 3), norm="ortho")
    Q = _JPEG_LUMA_Q * ((1.0 + 40.0 * a) / 16.0)
    Q = np.maximum(Q, 1e-3)[None, :, None, :]
    Dq = np.round(D / Q) * Q
    rec = sfft.idctn(Dq, axes=(1, 3), norm="ortho").reshape(bh, bw) / 255.0
    out = rec[off_y:off_y + H, off_x:off_x + W]
    out = _fit(out, H, W)
    return np.clip(np.nan_to_num(out, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)


def aug_cutout(v, a, b):
    """Cutout / random-erasing occlusion (DeVries & Taylor 2017; Zhong et al.
    2020): a square patch of side ``max(1, a*min(H,W))`` is erased from the
    image, forcing a pipeline to survive partial occlusion instead of relying on
    one salient blob. ``b`` selects the (deterministic, seeded-from-b) patch
    position AND the fill value: b <= 0.5 -> black (0.0), b > 0.5 -> mid-gray
    (0.5). The patch is always fully inside the frame."""
    x = _img(v).copy()
    a, b = _k(a), _k(b)
    H, W = x.shape[:2]
    side = int(max(1, round(a * min(H, W))))
    side = min(side, min(H, W))
    rng = np.random.default_rng(int(b * 100000) * 104729 + 12345)
    top = int(rng.integers(0, H - side + 1))
    left = int(rng.integers(0, W - side + 1))
    x[top:top + side, left:left + side] = 0.0 if b <= 0.5 else 0.5
    return np.clip(x, 0.0, 1.0)


def aug_barrel(v, a, b):
    """Radial lens distortion using the standard polynomial model
    ``r_src = r*(1 + k*r^2)`` on normalised radius ``r`` (1 = image corner):
    BARREL (straight lines bow outwards) when ``b < 0.5``, PINCUSHION when
    ``b >= 0.5``, with ``k = 0.6*a`` (a=0 -> undistorted). The destination grid is
    inverse-mapped and resampled bilinearly with ``ndimage.map_coordinates``
    (``mode="reflect"``), so no pixel is left undefined. Output keeps HxW."""
    x = _img(v)
    a, b = _k(a), _k(b)
    H, W = x.shape[:2]
    if H < 2 or W < 2 or a <= 1e-9:
        return x
    k = 0.6 * a * (1.0 if b < 0.5 else -1.0)
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    scale = max(1e-6, np.hypot(max(cy, 1e-6), max(cx, 1e-6)))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    dy, dx = (yy - cy) / scale, (xx - cx) / scale
    r2 = dy * dy + dx * dx
    f = 1.0 + k * r2
    src_y = cy + dy * f * scale
    src_x = cx + dx * f * scale
    coords = np.vstack([src_y.ravel(), src_x.ravel()])
    out = ndimage.map_coordinates(x, coords, order=1, mode="reflect")
    return np.clip(out.reshape(H, W), 0.0, 1.0)


# --------------------------------------------------------------------------- #
# registry                                                                    #
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # halcon="" for every op: MVTec HALCON has no sensor-degradation /
    # augmentation family (shot noise, FPN, rolling shutter, JPEG blocking,
    # cutout and barrel-distortion SYNTHESIS have no HALCON equivalent), so this
    # whole cluster is a new capability and makes no coverage claim.
    defs = [
        ("aug_shot_noise", "augmentation", aug_shot_noise),
        ("aug_read_noise", "augmentation", aug_read_noise),
        ("aug_fixed_pattern", "augmentation", aug_fixed_pattern),
        ("aug_motion_blur", "augmentation", aug_motion_blur),
        ("aug_vignette", "augmentation", aug_vignette),
        ("aug_chromatic", "augmentation", aug_chromatic),
        ("aug_rolling_shutter", "augmentation", aug_rolling_shutter),
        ("aug_jpeg_blocks", "augmentation", aug_jpeg_blocks),
        ("aug_cutout", "augmentation", aug_cutout),
        ("aug_barrel", "augmentation", aug_barrel),
    ]
    return [Op(n, c, "", IMAGE, IMAGE, _safe(f, IMAGE)) for (n, c, f) in defs]
