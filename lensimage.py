# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensimage — image formation through a *designed* lens, and synthetic defect datasets.

``raytrace`` answers the designer's questions (where is the image, how big is
the blur, what does the wavefront look like). This module closes the loop the
author asked for — *"build an optical system in a pseudo-physical space and
generate defect images for AI training"* — by turning a prescription into the
**picture a sensor behind that lens would record**:

* :func:`psf_from_opd` — the diffraction PSF of the real, aberrated pupil: the
  pupil function ``P = mask · exp(i 2π W)`` is built from the ray-traced OPD
  (``raytrace.opd_samples``, *W* in waves), zero-padded and Fourier transformed
  (incoherent imaging: ``PSF = |FFT(P)|²``). The sample spacing in the image
  plane is ``λ·F#/oversample`` with the working f-number ``1/(2·NA_image)``
  from :func:`raytrace.paraxial_trace`; with *pixel_pitch_um* the PSF is
  **area-integrated** onto detector pixels (not point-sampled).
* :func:`distortion_map` — real chief rays at several field heights versus the
  paraxial (``f·tanθ`` / ``m·H``) positions, a radial polynomial fit, and the
  inverse remap grid a renderer needs.
* :func:`render_through_lens` — the whole chain: ideal irradiance on the sensor
  → distortion (inverse remap) → spatially varying blur (a ``zones×zones``
  lattice of field-point PSFs, blended with bilinear weights) → relative
  illumination (traced vignetting × cos⁴) → exposure to electrons, shot noise,
  read noise, quantisation.
* :func:`defect_dataset` — ``defectgen`` defects on a ``surface_texture``
  background rendered through the lens, **with the mask pushed through the same
  distortion** (but not the blur) so annotations stay aligned; optional PNG +
  ``annotations.json`` output.

Honest limits: incoherent, monochromatic imaging at the system wavelength (no
chromatic PSF unless you call it per wavelength and add the results); the
field-dependent PSF is a ``zones×zones`` interpolation, and each off-axis PSF is
the +y-field PSF rotated to the tile's azimuth (a rotationally symmetric lens
assumption — decentred / tilted prescriptions get only the +y PSF); relative
illumination counts traced rays (vignetting) times cos⁴ (obliquity) — no pupil
aberration weighting; the sensor is a linear, uniform, noise-only model (no
crosstalk, no PRNU, no colour filter array). Every input is validated
fail-closed (``ValueError``) and every random draw comes from ``seed``.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

import defectgen
import photoncount
import raytrace as RT

__all__ = ["psf_from_opd", "psf_field_grid", "distortion_map", "render_through_lens",
           "defect_dataset", "MAX_PUPIL_SAMPLES", "MAX_IMAGE_PIXELS"]

INF = float("inf")
#: largest pupil grid (per side) the auto-sampler will grow to before refusing
MAX_PUPIL_SAMPLES = 512
#: largest image (pixels) render_through_lens / defect_dataset accept
MAX_IMAGE_PIXELS = 1 << 24
#: Nyquist rule for the pupil phase: at most this many waves between neighbours
_MAX_WAVES_PER_SAMPLE = 0.4
_MODEL_CACHE: dict = {}


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def _system(system):
    if not isinstance(system, dict) or "surfaces" not in system or "stop" not in system:
        raise ValueError("expected the dict returned by raytrace.lens_system(), got %r"
                         % type(system).__name__)
    RT.paraxial_trace(system)                       # validates the prescription too
    return system


def _num(x, name, lo=None, hi=None):
    if isinstance(x, (bool, str)) or x is None:
        raise ValueError("%s must be a number, got %r" % (name, x))
    try:
        v = float(x)
    except (TypeError, ValueError) as e:
        raise ValueError("%s must be a number, got %r" % (name, x)) from e
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (name, x))
    if lo is not None and v < lo:
        raise ValueError("%s must be >= %r, got %r" % (name, lo, x))
    if hi is not None and v > hi:
        raise ValueError("%s must be <= %r, got %r" % (name, hi, x))
    return v


def _int(x, name, lo, hi):
    if isinstance(x, bool) or not isinstance(x, (int, np.integer)):
        raise ValueError("%s must be an integer, got %r" % (name, x))
    v = int(x)
    if not lo <= v <= hi:
        raise ValueError("%s must be in [%d, %d], got %d" % (name, lo, hi, v))
    return v


def _image(a, name="image"):
    if isinstance(a, (str, bytes, dict)):
        raise ValueError("%s must be a 2-D array, got %r" % (name, type(a).__name__))
    arr = np.asarray(a)
    if arr.dtype.kind not in "fiub":
        raise ValueError("%s must be numeric, got dtype %r" % (name, arr.dtype))
    arr = arr.astype(np.float64)
    if arr.ndim != 2 or arr.shape[0] < 2 or arr.shape[1] < 2:
        raise ValueError("%s must be a 2-D array of at least 2x2, got shape %r" % (name, arr.shape))
    if arr.size > MAX_IMAGE_PIXELS:
        raise ValueError("%s has %d pixels, above MAX_IMAGE_PIXELS=%d" % (name, arr.size, MAX_IMAGE_PIXELS))
    if not np.isfinite(arr).all():
        raise ValueError("%s contains non-finite values" % name)
    if arr.min() < 0.0:
        raise ValueError("%s is an irradiance and must be non-negative (min %g)" % (name, arr.min()))
    return arr


def _shape(size, name="image_size"):
    try:
        h, w = int(size[0]), int(size[1])
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s must be a (height, width) pair, got %r" % (name, size))
    if h < 2 or w < 2 or h * w > MAX_IMAGE_PIXELS:
        raise ValueError("%s must be at least 2x2 and at most %d pixels, got %r" % (name, MAX_IMAGE_PIXELS, size))
    return h, w


def _working_fno(para):
    if para["na_image"] > 0 and math.isfinite(para["na_image"]):
        return 1.0 / (2.0 * para["na_image"])
    if math.isfinite(para["fno"]) and para["fno"] > 0:
        return para["fno"]
    raise ValueError("the system has no finite image-space f-number (afocal or degenerate)")


# --------------------------------------------------------------------------- #
# PSF
# --------------------------------------------------------------------------- #
def _pupil(system, field, size, wavelength_um):
    """Pupil mask and OPD (waves) on a size x size grid; NaN-free."""
    px, py, w, valid = RT.opd_samples(system, field=field, size=size, wavelength_um=wavelength_um)
    n = int(size)
    mask = valid.reshape(n, n)
    W = np.where(valid, w, 0.0).reshape(n, n)
    if mask.sum() < 16:
        raise ValueError("fewer than 16 rays reach the image plane at field %r (vignetted / TIR)" % field)
    return mask, W


def _max_phase_step(mask, W):
    """Largest OPD difference (waves) between neighbouring valid pupil samples."""
    both_x = mask[:, 1:] & mask[:, :-1]
    both_y = mask[1:, :] & mask[:-1, :]
    dx = np.abs(W[:, 1:] - W[:, :-1])[both_x]
    dy = np.abs(W[1:, :] - W[:-1, :])[both_y]
    return float(max(dx.max() if dx.size else 0.0, dy.max() if dy.size else 0.0))


def _auto_size(system, field, wavelength_um):
    """Pupil grid size that samples the phase at <= 0.4 waves per step."""
    n0 = 32
    mask, W = _pupil(system, field, n0, wavelength_um)
    step = _max_phase_step(mask, W)                      # waves per (2/(n0-1)) of rho
    grad = step * (n0 - 1) / 2.0                          # waves per unit rho
    need = int(math.ceil(grad * 2.0 / _MAX_WAVES_PER_SAMPLE)) + 1
    return int(min(MAX_PUPIL_SAMPLES, max(64, need)))


def _psf_core(system, field=None, size=None, wavelength_um=None, oversample=4):
    """Fine-grid PSF: returns (psf, psf_unaberrated, dx_um, n_pupil)."""
    _system(system)
    field = system["field"] if field is None else _num(field, "field")
    wl = system["wavelength_um"] if wavelength_um is None else _num(wavelength_um, "wavelength_um", lo=1e-3)
    oversample = _int(oversample, "oversample", 1, 64)
    if size is None:
        size = _auto_size(system, field, wl)
    size = _int(size, "size", 8, MAX_PUPIL_SAMPLES)
    mask, W = _pupil(system, field, size, wl)
    step = _max_phase_step(mask, W)
    if step > 0.5:
        raise ValueError("pupil phase changes %.2f waves between samples at size=%d (aliased); "
                         "use size >= %d or size=None (auto)" % (step, size, int(size * step / _MAX_WAVES_PER_SAMPLE) + 1))
    M = (size - 1) * oversample
    if M % 2:
        M += 1
    if M > 8192:
        raise ValueError("FFT grid %d too large; reduce size or oversample" % M)
    para = RT.paraxial_trace(system)
    fno = _working_fno(para)
    dx_um = wl * fno * (size - 1) / M                     # image-plane sample spacing
    P = mask * np.exp(2j * math.pi * W)
    pad = np.zeros((M, M), np.complex128)
    pad[:size, :size] = P
    psf = np.abs(np.fft.fftshift(np.fft.fft2(pad))) ** 2
    pad[:size, :size] = mask
    ref = np.abs(np.fft.fftshift(np.fft.fft2(pad))) ** 2
    return psf, ref, dx_um, size


def _integrate_pixels(psf, dx_um, pitch_um, normalise=True):
    """Area-integrate a fine PSF (spacing dx_um, centre at M//2) onto pixels of *pitch_um*."""
    M = psf.shape[0]
    if dx_um > pitch_um * (1.0 + 1e-9):
        raise ValueError("PSF sample spacing %.3g um is coarser than the pixel pitch %.3g um; "
                         "raise oversample" % (dx_um, pitch_um))
    x = (np.arange(M) - M // 2) * dx_um
    k = np.floor(x / pitch_um + 0.5).astype(int)
    half = int(max(abs(k.min()), abs(k.max())))
    K = 2 * half + 1
    idx = k + half
    out = np.zeros((K, K))
    np.add.at(out, (idx[:, None], idx[None, :]), psf)
    if normalise:
        s = out.sum()
        if s <= 0:
            raise ValueError("the PSF has no energy")
        out /= s
    return out


def psf_from_opd(system, field=None, size=None, wavelength_um=None, pixel_pitch_um=None, oversample=4):
    """Diffraction PSF of the real, aberrated pupil (``image2d``, sums to 1).

    The pupil function ``P = mask · exp(i·2π·W)`` comes from
    :func:`raytrace.opd_samples` (*W* in waves on a ``size × size`` grid over the
    exit pupil; ``size=None`` picks a grid that keeps the phase below 0.4 waves
    per sample, up to :data:`MAX_PUPIL_SAMPLES`; an explicit *size* that aliases
    is refused). The PSF is ``|FFT(P)|²`` on a zero-padded grid whose sample
    spacing is ``λ·F#·(size−1)/M ≈ λ·F#/oversample`` with the working
    f-number ``F# = 1/(2·NA_image)`` from :func:`raytrace.paraxial_trace`.
    With *pixel_pitch_um* the fine PSF is **area-integrated** onto detector
    pixels of that pitch (each fine sample is binned into the pixel it falls
    in; the pitch must not be finer than the sample spacing).

    Ground truth (``tests/test_lensimage.py``): an unaberrated pupil (the
    singlet stopped to a 1 mm semi-aperture) gives the Airy pattern — first
    dark ring at ``1.22·λ·F#`` within 3 %, 83.8 % ± 1 % of the energy inside
    it; the f/4 singlet (11 waves of spherical aberration) has a Strehl ratio
    below 0.05 (peak versus the unaberrated peak of the same pupil).
    """
    psf, _ref, dx, _n = _psf_core(system, field, size, wavelength_um, oversample)
    if pixel_pitch_um is None:
        return psf / psf.sum()
    pitch = _num(pixel_pitch_um, "pixel_pitch_um", lo=1e-6)
    return _integrate_pixels(psf, dx, pitch)


def psf_field_grid(system, fields=(0.0, 2.0, 4.0), size=None, wavelength_um=None,
                   pixel_pitch_um=None, oversample=4):
    """PSFs at several field points (``table``): ``fields``, ``psfs`` (list of
    image2d, each summing to 1), ``strehl`` (peak / unaberrated peak on the fine
    grid), ``sample_um`` (fine spacing), ``rms_spot_mm`` (from
    :func:`raytrace.spot_stats`) and ``fno``."""
    _system(system)
    try:
        fl = [_num(f, "field") for f in fields]
    except TypeError as e:
        raise ValueError("fields must be an iterable of numbers, got %r" % (fields,)) from e
    if not fl:
        raise ValueError("fields must not be empty")
    pitch = None if pixel_pitch_um is None else _num(pixel_pitch_um, "pixel_pitch_um", lo=1e-6)
    out = {"fields": fl, "psfs": [], "strehl": [], "sample_um": [], "rms_spot_mm": [],
           "fno": _working_fno(RT.paraxial_trace(system))}
    for f in fl:
        psf, ref, dx, _n = _psf_core(system, f, size, wavelength_um, oversample)
        out["strehl"].append(float(psf.max() / ref.max()))
        out["sample_um"].append(float(dx))
        out["psfs"].append(psf / psf.sum() if pitch is None else _integrate_pixels(psf, dx, pitch))
        out["rms_spot_mm"].append(float(RT.spot_stats(system, field=f)["rms_radius"]))
    return out


# --------------------------------------------------------------------------- #
# distortion
# --------------------------------------------------------------------------- #
def _chief_image_y(system, field, para):
    P, D, _ = RT._launch(system, np.array([0.0]), np.array([0.0]), field, para)
    tr = RT.trace_rays(system, P, D)
    if not tr["valid"][0]:
        raise ValueError("the chief ray at field %r does not reach the image plane (vignetted / TIR); "
                         "reduce the sensor size or the field" % field)
    return float(tr["points"][0, -1, 1])


def _ideal_radius(para, field, obj_inf):
    if obj_inf:
        return abs(para["efl"] * math.tan(math.radians(field)))
    return abs(para["magnification"] * field)


def _field_for_radius(para, r_mm, obj_inf):
    """Sensor radius (mm) -> field value (deg for infinity, object height mm otherwise)."""
    if obj_inf:
        return math.degrees(math.atan(r_mm / abs(para["efl"])))
    if para["magnification"] == 0 or not math.isfinite(para["magnification"]):
        raise ValueError("the system has no finite magnification for a finite object")
    return r_mm / abs(para["magnification"])


def distortion_map(system, image_size=(256, 256), pixel_pitch_um=5.5, fields=None, order=2):
    """Real chief-ray height versus the paraxial one, and the remap grid (``table``).

    Fields (degrees for an object at infinity, object heights in mm otherwise)
    default to 9 values from the axis to the sensor corner
    (``hypot(H, W)/2 · pitch``). For each, the real chief ray is traced to the
    image plane (``r_real``) and compared with the ideal height ``f·tanθ``
    (or ``m·H``); ``distortion_pct = (r_real − r_ideal)/r_ideal · 100`` —
    negative is barrel. A radial polynomial ``r_real = r(1 + k1 r² + k2 r⁴ …)``
    (*order* even terms) is fitted and inverted on a dense table to build
    ``grid_rows`` / ``grid_cols`` — for every **real** sensor pixel, the
    fractional ideal-image pixel it sees (the inverse remap a renderer feeds to
    ``scipy.ndimage.map_coordinates``). ``max_distortion_pct`` is at the
    corner. A paraboloid mirror with the stop on it and any system on axis give
    zero; the plano-convex singlet (stop on the lens) is measured at −1.1 %
    (barrel) at the corner of a 256 × 5.5 µm sensor (pinned in the tests).
    """
    _system(system)
    h, w = _shape(image_size)
    pitch = _num(pixel_pitch_um, "pixel_pitch_um", lo=1e-6)
    order = _int(order, "order", 1, 4)
    para = RT.paraxial_trace(system)
    obj_inf = system["object_mm"] == INF
    if not math.isfinite(para["efl"]):
        raise ValueError("afocal system: no image-plane distortion to map")
    r_corner = 0.5 * math.hypot(h, w) * pitch * 1e-3
    if fields is None:
        fmax = _field_for_radius(para, r_corner, obj_inf)
        fl = np.linspace(0.0, fmax, 9).tolist()
    else:
        try:
            fl = sorted(abs(_num(f, "field")) for f in fields)
        except TypeError as e:
            raise ValueError("fields must be an iterable of numbers, got %r" % (fields,)) from e
        if len(fl) < 2:
            raise ValueError("at least two fields are needed (the axis and one off-axis point)")
    r_ideal = np.array([_ideal_radius(para, f, obj_inf) for f in fl])
    r_real = np.array([abs(_chief_image_y(system, f, para)) for f in fl])
    with np.errstate(divide="ignore", invalid="ignore"):
        pct = np.where(r_ideal > 1e-12, (r_real - r_ideal) / r_ideal * 100.0, 0.0)
    nz = r_ideal > 1e-12
    if nz.sum() < 1:
        raise ValueError("all fields are on axis; give at least one off-axis field")
    powers = [2 * k + 1 for k in range(1, order + 1)]
    A = np.stack([r_ideal[nz] ** p for p in powers], 1)
    coef, *_ = np.linalg.lstsq(A, r_real[nz] - r_ideal[nz], rcond=None)
    # dense inverse table on [0, 1.2 r_max]
    r_max = max(float(r_ideal.max()), r_corner) * 1.2 + 1e-9
    rd = np.linspace(0.0, r_max, 4096)
    rr = rd + sum(c * rd ** p for c, p in zip(coef, powers))
    if np.any(np.diff(rr) <= 0):
        raise ValueError("the fitted distortion polynomial is not monotone up to %.3g mm; "
                         "reduce the field or the polynomial order" % r_max)
    yy = (np.arange(h) - (h - 1) / 2.0) * pitch * 1e-3
    xx = (np.arange(w) - (w - 1) / 2.0) * pitch * 1e-3
    Y, X = np.meshgrid(yy, xx, indexing="ij")
    R = np.hypot(Y, X)
    R_ideal = np.interp(R, rr, rd)
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(R > 1e-12, R_ideal / R, 1.0)
    grid_rows = (Y * scale) / (pitch * 1e-3) + (h - 1) / 2.0
    grid_cols = (X * scale) / (pitch * 1e-3) + (w - 1) / 2.0
    return {"fields": fl, "r_ideal_mm": r_ideal.tolist(), "r_real_mm": r_real.tolist(),
            "distortion_pct": pct.tolist(), "max_distortion_pct": float(pct[-1]),
            "coefficients": coef.tolist(), "powers": powers, "efl": para["efl"],
            "magnification": para["magnification"], "image_size": (h, w),
            "pixel_pitch_um": pitch, "grid_rows": grid_rows, "grid_cols": grid_cols}


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def _relative_illumination(system, para, fields, obj_inf, rings=6):
    """Traced transmission (valid-ray fraction, normalised to the axis) x cos^4."""
    base = None
    out = []
    for f in fields:
        b = RT.ray_bundle(system, field=f, rings=rings)
        frac = float(b["valid"].mean())
        if base is None:
            base = frac if frac > 0 else 1.0
        cos4 = math.cos(math.radians(f)) ** 4 if obj_inf else 1.0
        out.append(frac / base * cos4)
    return out


def _noise_params(noise):
    d = {"full_well": 20000.0, "read_e": 3.0, "bits": 12, "exposure": 1.0, "dark_e": 0.0}
    if noise is None or noise is False:
        return None
    if noise is True:
        return d
    if not isinstance(noise, dict):
        raise ValueError("noise must be None, True or a dict, got %r" % type(noise).__name__)
    for k, v in noise.items():
        if k not in d:
            raise ValueError("unknown noise key %r (choose from %s)" % (k, sorted(d)))
        d[k] = v
    d["full_well"] = _num(d["full_well"], "full_well", lo=1.0)
    d["read_e"] = _num(d["read_e"], "read_e", lo=0.0)
    d["exposure"] = _num(d["exposure"], "exposure", lo=0.0)
    d["dark_e"] = _num(d["dark_e"], "dark_e", lo=0.0)
    d["bits"] = _int(d["bits"], "bits", 1, 16)
    return d


def _lens_model(system, shape, pitch, zones, fov, size, oversample, illumination):
    """Everything about the lens that does not depend on the image (cached)."""
    key = (json.dumps(system, sort_keys=True, default=str), shape, pitch, zones, fov, size, oversample, illumination)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    h, w = shape
    para = RT.paraxial_trace(system)
    obj_inf = system["object_mm"] == INF
    if oversample is None:                      # >= 2 PSF samples per pixel
        oversample = int(max(4, math.ceil(2.0 * system["wavelength_um"] * _working_fno(para) / pitch)))
    r_corner = 0.5 * math.hypot(h, w) * pitch * 1e-3
    dist = distortion_map(system, (h, w), pitch)
    # fov: the sensor corner is declared to see this field -> the ideal image is
    # a zoomed copy of the input (zoom < 1 shrinks the picture onto the sensor)
    zoom = 1.0
    if fov is not None:
        r_fov = _ideal_radius(para, fov, obj_inf)
        if r_fov <= 0:
            raise ValueError("field_of_view must be > 0")
        zoom = r_corner / r_fov
    # tile centres and their PSFs (one per distinct radius, rotated per azimuth)
    cy = (np.arange(zones) + 0.5) * h / zones - 0.5
    cx = (np.arange(zones) + 0.5) * w / zones - 0.5
    tiles = []
    by_radius = {}
    for iy in range(zones):
        for ix in range(zones):
            dy = (cy[iy] - (h - 1) / 2.0) * pitch * 1e-3
            dx = (cx[ix] - (w - 1) / 2.0) * pitch * 1e-3
            r = math.hypot(dx, dy)
            rk = round(r, 9)
            if rk not in by_radius:
                f = _field_for_radius(para, r, obj_inf)
                psf, _ref, dxs, _n = _psf_core(system, f, size, None, oversample)
                by_radius[rk] = _integrate_pixels(psf, dxs, pitch)
            base = by_radius[rk]
            if r > 1e-12:
                from scipy import ndimage
                ang = math.degrees(math.atan2(dx, dy))
                k = ndimage.rotate(base, -ang, reshape=False, order=1, mode="constant", cval=0.0)
                k = np.clip(k, 0.0, None)
                k /= k.sum()
            else:
                k = base
            tiles.append({"cy": float(cy[iy]), "cx": float(cx[ix]), "psf": k, "radius_mm": r})
    # relative illumination on a radial table
    rs = np.linspace(0.0, r_corner, 9)
    fl = [_field_for_radius(para, r, obj_inf) for r in rs]
    if illumination == "traced":
        ri = _relative_illumination(system, para, fl, obj_inf)
    elif illumination == "cos4":
        ri = [math.cos(math.radians(f)) ** 4 if obj_inf else 1.0 for f in fl]
    else:
        ri = [1.0] * len(fl)
    yy = (np.arange(h) - (h - 1) / 2.0) * pitch * 1e-3
    xx = (np.arange(w) - (w - 1) / 2.0) * pitch * 1e-3
    Y, X = np.meshgrid(yy, xx, indexing="ij")
    ri_map = np.interp(np.hypot(Y, X), rs, ri)
    model = {"dist": dist, "zoom": zoom, "tiles": tiles, "ri_map": ri_map, "ri_table": ri,
             "ri_fields": fl, "para": para, "shape": (h, w), "pitch": pitch, "zones": zones}
    if len(_MODEL_CACHE) > 32:
        _MODEL_CACHE.clear()
    _MODEL_CACHE[key] = model
    return model


def _remap(image, model, order=1):
    from scipy import ndimage
    h, w = model["shape"]
    z = model["zoom"]
    rows = (model["dist"]["grid_rows"] - (h - 1) / 2.0) / z + (h - 1) / 2.0
    cols = (model["dist"]["grid_cols"] - (w - 1) / 2.0) / z + (w - 1) / 2.0
    return ndimage.map_coordinates(image, [rows, cols], order=order, mode="constant", cval=0.0)


def _blur(image, model):
    from scipy.signal import fftconvolve
    h, w = model["shape"]
    tiles = model["tiles"]
    if len(tiles) == 1:
        return np.clip(fftconvolve(image, tiles[0]["psf"], mode="same"), 0.0, None)
    yy = np.arange(h)[:, None]
    xx = np.arange(w)[None, :]
    th, tw = h / model["zones"], w / model["zones"]
    acc = np.zeros((h, w))
    wsum = np.zeros((h, w))
    for t in tiles:
        wt = np.clip(1.0 - np.abs(yy - t["cy"]) / th, 0.0, None) * np.clip(1.0 - np.abs(xx - t["cx"]) / tw, 0.0, None)
        if not np.any(wt):
            continue
        acc += wt * fftconvolve(image, t["psf"], mode="same")
        wsum += wt
    return np.clip(acc / np.where(wsum > 0, wsum, 1.0), 0.0, None)


def _sensor(irr, nz, seed):
    e = np.clip(irr, 0.0, None)
    counts = photoncount.photon_sample(e, photons_per_unit=nz["full_well"] * nz["exposure"],
                                       dark_rate=nz["dark_e"], seed=seed)
    rng = np.random.default_rng(int(seed) + 1)
    if nz["read_e"] > 0:
        counts = counts + rng.normal(0.0, nz["read_e"], counts.shape)
    levels = (1 << nz["bits"]) - 1
    dn = np.floor(counts / nz["full_well"] * levels + 0.5)
    return np.clip(dn, 0, levels) / levels


def render_through_lens(image, system, pixel_pitch_um=5.5, field_of_view=None, zones=3, noise=None,
                        seed=0, illumination="traced", size=None, oversample=None):
    """Render an ideal irradiance image as the sensor behind *system* would record it (``image2d``).

    *image* (H×W, non-negative) is the ideal (paraxial) image on a sensor of
    *pixel_pitch_um* pixels centred on the optical axis; with *field_of_view*
    (half field to the sensor corner: degrees for an object at infinity,
    object height in mm otherwise) the picture is first zoomed so the corner
    sees that field. Pipeline: (a) inverse distortion remap
    (:func:`distortion_map` grid, ``scipy.ndimage.map_coordinates`` order 1);
    (b) spatially varying blur — a ``zones×zones`` lattice of tile centres,
    each with its own pixel-integrated :func:`psf_from_opd` (the +y-field PSF
    rotated to the tile azimuth), blended with bilinear (tent) weights so
    seams vanish; (c) relative illumination: ``"traced"`` = fraction of the
    field's ray bundle that reaches the image (vignetting, from
    :func:`raytrace.ray_bundle`) normalised to the axis, times cos⁴ (obliquity,
    objects at infinity only), ``"cos4"`` = the classic law alone, ``"none"``;
    (d) sensor, when *noise* is ``True`` or a dict ``{"full_well": 20000,
    "read_e": 3.0, "bits": 12, "exposure": 1.0, "dark_e": 0.0}``: electrons =
    irradiance × exposure × full_well, Poisson shot noise
    (:func:`photoncount.photon_sample`), Gaussian read noise, quantisation to
    *bits*, returned as DN/(2^bits − 1). With ``noise=None`` the float
    irradiance is returned untouched (deterministic; the noisy path is
    deterministic for a given *seed* too).

    *oversample* defaults to whatever keeps at least 2 PSF samples per pixel
    (``max(4, ceil(2·λ·F#/pitch))``). Ground truth: a δ image through the
    f/2 paraboloid gives the pixel-integrated Airy PSF; a checkerboard through
    it comes back undistorted (correlation > 0.99); energy is conserved to 1 %
    with illumination off; noise off is bit-reproducible.
    """
    img = _image(image)
    _system(system)
    pitch = _num(pixel_pitch_um, "pixel_pitch_um", lo=1e-6)
    zones = _int(zones, "zones", 1, 16)
    if illumination not in ("traced", "cos4", "none"):
        raise ValueError("illumination must be 'traced', 'cos4' or 'none', got %r" % (illumination,))
    fov = None if field_of_view is None else _num(field_of_view, "field_of_view", lo=1e-9)
    nz = _noise_params(noise)
    seed = _int(seed, "seed", 0, 2 ** 31 - 1)
    if oversample is None:
        para = RT.paraxial_trace(system)
        oversample = int(max(4, math.ceil(2.0 * system["wavelength_um"] * _working_fno(para) / pitch)))
    oversample = _int(oversample, "oversample", 1, 64)
    if size is not None:
        size = _int(size, "size", 8, MAX_PUPIL_SAMPLES)
    model = _lens_model(system, img.shape, pitch, zones, fov, size, oversample, illumination)
    out = _remap(img, model)
    out = _blur(out, model)
    out = out * model["ri_map"]
    if nz is None:
        return out
    return _sensor(out, nz, seed)


# --------------------------------------------------------------------------- #
# dataset
# --------------------------------------------------------------------------- #
_KINDS = ("scratch", "pits", "crack", "blob")


def _draw_defect(kind, shape, rng):
    h, w = shape
    s = int(rng.integers(0, 2 ** 31 - 1))
    d = min(h, w)
    if kind == "scratch":
        p = {"length_px": float(rng.uniform(0.25, 0.6) * d), "width_px": float(rng.uniform(2.0, 6.0)),
             "angle_deg": float(rng.uniform(0.0, 180.0)), "contrast": float(rng.uniform(-0.45, -0.2))}
        img, m = defectgen.defect_scratch(shape, seed=s, **p)
    elif kind == "pits":
        p = {"count": int(rng.integers(5, 30)), "radius_px": float(rng.uniform(2.0, 5.0)),
             "contrast": float(rng.uniform(-0.45, -0.2))}
        img, m = defectgen.defect_pits(shape, seed=s, **p)
    elif kind == "crack":
        p = {"length_px": float(rng.uniform(0.2, 0.5) * d), "width_px": float(rng.uniform(1.5, 4.0)),
             "angle_deg": float(rng.uniform(0.0, 180.0)), "contrast": float(rng.uniform(-0.5, -0.25))}
        img, m = defectgen.defect_crack(shape, seed=s, **p)
    elif kind == "blob":
        p = {"radius_px": float(rng.uniform(0.04, 0.1) * d), "roughness": float(rng.uniform(0.2, 0.5)),
             "contrast": float(rng.uniform(0.15, 0.35)) * float(rng.choice([-1.0, 1.0]))}
        img, m = defectgen.defect_blob(shape, seed=s, **p)
    else:
        raise ValueError("unknown defect kind %r (choose from %s)" % (kind, _KINDS))
    p["seed"] = s
    return img, m, p


def _bbox(mask):
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]


def defect_dataset(n=8, system=None, size=(256, 256), kinds=_KINDS, pixel_pitch_um=5.5,
                   noise=True, seed=0, out_dir=None, zones=3, field_of_view=None,
                   texture="orange_peel", max_defects=2):
    """Synthetic defect images through a designed lens, with aligned masks (``table``).

    Each of the *n* records draws 1–*max_defects* defects of the listed *kinds*
    (``defectgen`` scratch / pits / crack / blob with parameters sampled from
    *seed*) on a ``surface_texture`` background of *size*, renders the composite
    with :func:`render_through_lens` (*system* defaults to the cemented doublet
    of :func:`raytrace.example_system`; *noise* as there, default sensor
    noise on), and pushes **each defect's mask through the same distortion
    remap only** (nearest-neighbour, no blur) so the annotation sits where the
    blurred defect actually landed. A record is
    ``{"image", "mask", "defects": [{"kind", "params", "bbox" [x, y, w, h],
    "area"}], "lens": {"efl", "fno", "rms_spot_center", "rms_spot_corner",
    "max_distortion_pct"}, "seed"}`` with arrays, or with file paths when
    *out_dir* is given (``img_0000.png`` / ``mask_0000.png`` written with
    ``imgio.save`` plus a COCO-like ``annotations.json``: images, annotations
    with bbox/area/params, categories). Deterministic for *seed*; a defect
    that lands entirely outside the sensor after distortion is dropped from
    the annotations rather than reported with an empty box.
    """
    n = _int(n, "n", 1, 10000)
    shape = _shape(size, "size")
    if isinstance(kinds, str):
        kinds = (kinds,)
    kinds = tuple(kinds)
    if not kinds or any(k not in _KINDS for k in kinds):
        raise ValueError("kinds must be a non-empty subset of %s, got %r" % (_KINDS, kinds))
    max_defects = _int(max_defects, "max_defects", 1, 8)
    seed = _int(seed, "seed", 0, 2 ** 31 - 1)
    system = RT.example_system("doublet") if system is None else _system(system)
    pitch = _num(pixel_pitch_um, "pixel_pitch_um", lo=1e-6)
    if out_dir is not None:
        if not isinstance(out_dir, (str, os.PathLike)):
            raise ValueError("out_dir must be a path, got %r" % type(out_dir).__name__)
        os.makedirs(out_dir, exist_ok=True)
    para = RT.paraxial_trace(system)
    obj_inf = system["object_mm"] == INF
    r_corner = 0.5 * math.hypot(*shape) * pitch * 1e-3
    f_corner = _field_for_radius(para, r_corner, obj_inf)
    lens = {"efl": para["efl"], "fno": _working_fno(para),
            "rms_spot_center": RT.spot_stats(system)["rms_radius"],
            "rms_spot_corner": RT.spot_stats(system, field=f_corner)["rms_radius"]}
    rng = np.random.default_rng(seed)
    records, coco_imgs, coco_anns = [], [], []
    ann_id = 0
    model = None
    for i in range(n):
        bg = defectgen.surface_texture(shape, kind=texture, strength=float(rng.uniform(0.02, 0.08)),
                                       seed=int(rng.integers(0, 2 ** 31 - 1)))
        comp = bg
        defects = []
        for _ in range(int(rng.integers(1, max_defects + 1))):
            kind = str(rng.choice(kinds))
            dimg, dmask, params = _draw_defect(kind, shape, rng)
            comp = defectgen.composite_defect(comp, dimg, dmask)
            defects.append((kind, params, dmask))
        rec_seed = int(rng.integers(0, 2 ** 31 - 1))
        image = render_through_lens(comp, system, pitch, field_of_view=field_of_view, zones=zones,
                                    noise=noise, seed=rec_seed)
        if model is None:
            key_model = _lens_model(system, shape, pitch, zones,
                                    None if field_of_view is None else float(field_of_view),
                                    None, None, "traced")
            model = key_model
            lens["max_distortion_pct"] = model["dist"]["max_distortion_pct"]
        mask_all = np.zeros(shape, bool)
        anns = []
        for kind, params, dmask in defects:
            dm = _remap(dmask.astype(np.float64), model, order=0) > 0.5
            bb = _bbox(dm)
            if bb is None:
                continue
            mask_all |= dm
            anns.append({"kind": kind, "params": params, "bbox": bb, "area": int(dm.sum())})
        rec = {"image": image, "mask": mask_all, "defects": anns, "lens": dict(lens), "seed": rec_seed}
        if out_dir is not None:
            import imgio
            ip = os.path.join(out_dir, "img_%04d.png" % i)
            mp = os.path.join(out_dir, "mask_%04d.png" % i)
            imgio.save(ip, np.clip(image, 0.0, 1.0))
            imgio.save(mp, mask_all)
            rec["image"], rec["mask"] = ip, mp
            coco_imgs.append({"id": i, "file_name": os.path.basename(ip), "mask_file": os.path.basename(mp),
                              "width": shape[1], "height": shape[0]})
            for a in anns:
                coco_anns.append({"id": ann_id, "image_id": i, "category_id": _KINDS.index(a["kind"]) + 1,
                                  "bbox": a["bbox"], "area": a["area"], "params": a["params"], "iscrowd": 0})
                ann_id += 1
        records.append(rec)
    if out_dir is not None:
        ann = {"images": coco_imgs, "annotations": coco_anns,
               "categories": [{"id": k + 1, "name": name} for k, name in enumerate(_KINDS)],
               "lens": lens, "seed": seed, "pixel_pitch_um": pitch}
        with open(os.path.join(out_dir, "annotations.json"), "w", encoding="utf-8") as f:
            json.dump(ann, f, indent=1, ensure_ascii=False, default=float)
    return records
