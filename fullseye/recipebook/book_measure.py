"""Measurement-side coverage recipes (ledger ops, python executors).

Families: segmentation, annotate, gfx2d, generative, imgmetrics, imgforensics, shape2d, shapestat,
profile, blob, colortransport, vx, measure1d, roughness, quat, codematch, residue, aoi, text.

Every sample below is synthetic with a closed-form answer (a disk's area, a bar's width, a known
shift, a known noise sigma, a known colour rotation ...). Sample names carry the ``ms_`` prefix.
"""
from __future__ import annotations

import math

import numpy as np

from fullseye.recipebook.common import disk_image, rng


# ---- helpers ---------------------------------------------------------------------------------
def _texture(n: int, seed: int, corr: float = 3.0) -> np.ndarray:
    """Smooth random texture in [0.2, 0.8] (white noise low-passed by a Gaussian in Fourier space)."""
    g = np.random.default_rng(seed)
    w = g.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    k = np.exp(-2.0 * (np.pi * corr) ** 2 * (fx ** 2 + fy ** 2))
    t = np.real(np.fft.ifft2(np.fft.fft2(w) * k))
    t = (t - t.min()) / (t.max() - t.min())
    return 0.2 + 0.6 * t


def _srgb_gray_lstar(v: float) -> float:
    """CIE L* of an sRGB grey level v in [0, 1] (D65, Y_white = 1) — independent of the library."""
    lin = v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    f = lin ** (1.0 / 3.0) if lin > (6 / 29) ** 3 else lin / (3 * (6 / 29) ** 2) + 4 / 29
    return 116.0 * f - 16.0


def _touching_disks(variant: int, n: int = 96, r: float = 12.0, step: float = 18.0):
    k = 2 + int(variant)
    yy, xx = np.mgrid[0:n, 0:n]
    m = np.zeros((n, n), bool)
    for i in range(k):
        m |= ((yy - 48) ** 2 + (xx - (24 + step * i)) ** 2) <= r * r
    img = 0.15 + 0.7 * m + 0.02 * rng(variant, 31).standard_normal((n, n))
    return np.clip(img, 0, 1), k


# ---- samples ---------------------------------------------------------------------------------
def ms_blobs(variant):
    """k = 3 + variant separated disks (common blobs_image, re-exported under the book prefix)."""
    from fullseye.recipebook.common import blobs_image
    return blobs_image(variant)


def ms_touching(variant):
    img, k = _touching_disks(variant)
    return {"value": img, "aux": {}, "truth": {"count": k}}


def ms_disk_gt(variant):
    s = disk_image(variant)
    t = s["truth"]
    n = s["value"].shape[0]
    yy, xx = np.mgrid[0:n, 0:n]
    gt = (((yy - t["row"]) ** 2 + (xx - t["col"]) ** 2) <= t["radius"] ** 2).astype(np.int32)
    return {"value": s["value"], "aux": {"gt": gt}, "truth": dict(t, gt_area=int(gt.sum()))}


def ms_two_level(variant):
    lo, hi = (0.2, 0.7) if variant == 0 else (0.3, 0.9)
    n = 96
    yy, xx = np.mgrid[0:n, 0:n]
    m = ((yy - 48) ** 2 + (xx - 48) ** 2) <= (20 + 6 * variant) ** 2
    img = np.where(m, hi, lo) + 0.02 * rng(variant, 32).standard_normal((n, n))
    return {"value": img, "aux": {}, "truth": {"mid": 0.5 * (lo + hi)}}


def ms_edge(variant):
    """Vertical step edge at column 20 + 6·v (sharp, little noise); truth = subpixel edge column c - 0.5."""
    n = 64
    c = 20 + 6 * int(variant)
    img = np.full((n, n), 0.2)
    img[:, c:] = 0.8
    img = np.clip(img + 0.01 * rng(variant, 33).standard_normal((n, n)), 0, 1)
    return {"value": img, "aux": {"shape": (n, n)}, "truth": {"edge_col": c - 0.5}}


def ms_bar(variant):
    """Bright bar of width 11 + 4·v px starting at column 18; scale 0.05 mm/px; truth = width px / mm."""
    n = 64
    w = 11 + 4 * int(variant)
    img = np.full((n, n), 0.2)
    img[:, 18:18 + w] = 0.8
    img = np.clip(img + 0.01 * rng(variant, 34).standard_normal((n, n)), 0, 1)
    return {"value": img, "aux": {"shape": (n, n), "mm_per_px": 0.05},
            "truth": {"width_px": float(w), "width_mm": 0.05 * w}}


def ms_hole(variant):
    """Disk (common disk_image) plus a nominal reference circle off by (+1, -1) px and +2 px radius."""
    s = disk_image(variant)
    t = s["truth"]
    aux = {"row": t["row"] + 1.0, "col": t["col"] - 1.0, "r": t["radius"] + 2.0, "mm_per_px": 0.02}
    return {"value": s["value"], "aux": aux, "truth": dict(t, radius_mm=0.02 * t["radius"])}


def ms_u8_edge(variant):
    """8-bit step edge at column 24 shifted by an affine warp of +5 / +9 px; truth = new edge column."""
    n = 64
    img = np.full((n, n), 51, np.uint8)
    img[:, 24:] = 204
    shift = 5.0 + 4.0 * variant
    M = np.array([[1.0, 0.0, -shift], [0.0, 1.0, 0.0]])
    return {"value": img, "aux": {"M": M, "shape": (n, n)}, "truth": {"edge_col": 23.5 + shift}}


def ms_u8_two_level(variant):
    """8-bit image: n_dark pixels at 50, the rest at 200; aux = inverting LUT; truth = bin counts."""
    n = 64
    k = 20 + 12 * int(variant)            # dark columns
    img = np.full((n, n), 200, np.uint8)
    img[:, :k] = 50
    lut = (255 - np.arange(256)).astype(np.uint8)
    # after inversion: 50 -> 205 (bin 12 of 16), 200 -> 55 (bin 3 of 16)
    return {"value": img, "aux": {"lut": lut},
            "truth": {"n_dark": float(n * k), "n_bright": float(n * (n - k))}}


def ms_bayer(variant):
    """RGGB mosaic of a uniform colour patch with a 0.05 black pedestal; truth = gray-world gains."""
    col = (0.6, 0.4, 0.2) if variant == 0 else (0.3, 0.5, 0.45)
    n = 32
    raw = np.zeros((n, n))
    raw[0::2, 0::2] = col[0]
    raw[0::2, 1::2] = col[1]
    raw[1::2, 0::2] = col[1]
    raw[1::2, 1::2] = col[2]
    off = 0.05
    return {"value": off + raw * (1.0 - off), "aux": {"offset": off},
            "truth": {"g_r": col[1] / col[0], "g_b": col[1] / col[2]}}


def ms_shading(variant):
    """Flat-field frame with radial fall-off and a scene of reflectance 0.5 | 1.0 shot through it."""
    n = 48
    yy, xx = np.mgrid[0:n, 0:n]
    fall = 0.5 if variant == 0 else 0.3
    flat = 0.9 * (1 - fall * ((yy - 24) ** 2 + (xx - 24) ** 2) / (2 * 24 ** 2))
    refl = np.where(xx < 24, 0.5, 1.0)
    return {"value": flat, "aux": {"raw": flat * refl}, "truth": {"flat_mean": float(flat.mean()), "flat_half": 0.5 * float(flat.mean())}}


def ms_ca(variant):
    """Rule-90 elementary CA from one cell: live cells after n steps = 2**popcount(n)."""
    steps = 5 if variant == 0 else 7
    return {"value": None, "aux": {"steps": steps},
            "truth": {"live": float(2 ** bin(steps).count("1"))}}


def ms_sem_slope(variant):
    """Height field: flat left half, plane of gradient g on the right; SEM brightness = base·sec(atan g)."""
    g = 0.5 if variant == 0 else 1.0
    n = 48
    xx = np.mgrid[0:n, 0:n][1].astype(float)
    h = np.where(xx >= 24, g * (xx - 24), 0.0)
    return {"value": h, "aux": {}, "truth": {"bright": 0.25 * math.sqrt(1 + g * g)}}


def ms_pl_psf(variant):
    return {"value": None, "aux": {"L": 3.0 + 2.0 * variant}, "truth": {"mass": 1.0}}


def ms_plot(variant):
    """Blank canvas + a line y = s·x on axes x∈[0,8], y∈[0,6] in the pixel rectangle (10,10,81,61)."""
    s = 0.5 + 0.25 * variant
    x = np.arange(9.0)
    y = s * x
    rect = (10, 10, 81, 61)
    py_last = 10 + 60 - (y[-1] - 0.0) / 6.0 * 60
    return {"value": np.zeros((96, 96)), "aux": {"x": x, "y": y, "rect": rect, "xlim": (0.0, 8.0),
                                                   "ylim": (0.0, 6.0)},
            "truth": {"px_last": 90.0, "py_last": float(py_last)}}


def ms_ellipse_canvas(variant):
    a, b = (20.0, 10.0) if variant == 0 else (24.0, 14.0)
    return {"value": np.zeros((64, 64)), "aux": {"center": (32, 30), "radii": (a, b)},
            "truth": {"area": math.pi * a * b}}


def ms_noisy_pair(variant):
    """Clean structured image and a copy with additive Gaussian noise σ = 0.03 / 0.06 (no clipping)."""
    n = 96
    sigma = 0.03 if variant == 0 else 0.06
    clean = 0.5 + 0.1 * np.sin(np.arange(n) / 5.0)[None, :] * np.ones((n, 1))
    noisy = clean + sigma * rng(variant, 35).standard_normal((n, n))
    return {"value": clean, "aux": {"noisy": noisy},
            "truth": {"psnr": 10 * math.log10(1.0 / sigma ** 2), "rmse": sigma}}


def ms_gray_pair(variant):
    """sRGB grey image: left half g1, right half g2; reference uniform g1; truth ΔE76 = |L*(g2) - L*(g1)|."""
    g1, g2 = (0.5, 0.4) if variant == 0 else (0.5, 0.7)
    n = 32
    img = np.full((n, n, 3), g1)
    img[:, n // 2:] = g2
    ref = np.full((n, n, 3), g1)
    return {"value": img, "aux": {"ref": ref},
            "truth": {"dL": abs(_srgb_gray_lstar(g2) - _srgb_gray_lstar(g1))}}


def ms_levels(variant):
    """k equally populated grey levels (k = 4 / 8) in vertical bands; MI(image, inverted) = log2 k bits."""
    k = 4 if variant == 0 else 8
    n = 96
    band = np.repeat(np.arange(k), n // k)
    img = np.tile(band / (k - 1.0), (n, 1))
    return {"value": img, "aux": {}, "truth": {"bits": math.log2(k)}}


def ms_watermark(variant):
    img = _texture(64, 40 + variant)
    bits = rng(variant, 36).integers(0, 2, 16).astype(bool)
    return {"value": img, "aux": {"bits": bits}, "truth": {"bits": bits}}


def ms_copymove(variant):
    """Smooth texture with a 16x16 patch copied from (10, 20) to (60, 60) / (50, 64)."""
    img = np.clip(0.5 + 0.2 * rng(variant, 37).standard_normal((96, 96)), 0, 1)
    dst = (60, 60) if variant == 0 else (50, 64)
    out = img.copy()
    out[dst[0]:dst[0] + 16, dst[1]:dst[1] + 16] = img[10:26, 20:36]
    return {"value": out, "aux": {}, "truth": {"drow": float(dst[0] - 10), "dcol": float(dst[1] - 20)}}


def ms_splice(variant):
    """Flat grey with noise σ=0.01, a block-aligned spliced patch with σ=0.04 (32x32 / 48x32 px)."""
    g = rng(variant, 38)
    img = 0.5 + 0.01 * g.standard_normal((96, 96))
    r0, r1, c0, c1 = (32, 64, 32, 64) if variant == 0 else (16, 64, 48, 80)
    img[r0:r1, c0:c1] = 0.5 + 0.04 * g.standard_normal((r1 - r0, c1 - c0))
    return {"value": img, "aux": {},
            "truth": {"area": float((r1 - r0) * (c1 - c0)), "row": (r0 + r1 - 1) / 2.0,
                      "col": (c0 + c1 - 1) / 2.0}}


def ms_circle_contour(variant):
    """Noisy closed contour of a circle of radius 15 / 20 px, (x, y) order, 200 points."""
    r = 15.0 + 5.0 * variant
    t = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    pts = np.column_stack([40 + r * np.cos(t), 40 + r * np.sin(t)])
    pts = pts + 0.3 * rng(variant, 39).standard_normal(pts.shape)
    return {"value": pts, "aux": {}, "truth": {"radius": r}}


def ms_tps_disk(variant):
    """Disk image + 5 control points moved by (dx, dy) = (3, 6) / (-4, 5) px; pairs are (x=col, y=row)."""
    s = disk_image(variant)
    d = np.array([3.0, 6.0]) if variant == 0 else np.array([-4.0, 5.0])
    src = np.array([[10, 10], [10, 86], [86, 10], [86, 86], [48, 48]], float)
    t = s["truth"]
    return {"value": s["value"], "aux": {"src": src, "dst": src + d},
            "truth": dict(t, row_moved=t["row"] + d[1], col_moved=t["col"] + d[0])}


def ms_shapefamily(variant):
    scale = (0.3, 0.12) if variant == 0 else (0.3, 0.2)
    rho = (scale[0] / scale[1]) ** 2
    return {"value": None, "aux": {"mode_scale": scale}, "truth": {"first": rho / (1 + rho)}}


def ms_landmarks(variant):
    """40 landmarks and a rotated (0.4 rad), scaled (x2), shifted copy with σ = 0.01 / 0.03 noise."""
    g = rng(variant, 41)
    P = g.standard_normal((40, 3))
    th = 0.4
    R = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1]])
    sigma = 0.01 if variant == 0 else 0.03
    Q = 2.0 * P @ R.T + 1.0 + sigma * g.standard_normal(P.shape)
    # after a 7-dof similarity fit the residual RMS per point is sqrt(3)σ·sqrt(1 - 7/(3N))
    return {"value": P, "aux": {"target": Q},
            "truth": {"rms": math.sqrt(3) * sigma * math.sqrt(1 - 7 / 120)}}


def ms_naca(variant):
    code = "0012" if variant == 0 else "0018"
    t = int(code[2:]) / 100.0
    amount = 0.002 if variant == 0 else 0.004
    return {"value": None, "aux": {"code": code, "amount": amount},
            "truth": {"le_radius": 1.1019 * t * t, "amount": amount}}


def ms_rgb_two(variant):
    """Two colour patches; rotating 120° about the grey axis maps (r, g, b) -> (b, r, g)."""
    left = (0.8, 0.1, 0.0) if variant == 0 else (0.2, 0.6, 0.1)
    right = (0.8, 0.0, 0.3) if variant == 0 else (0.5, 0.2, 0.7)
    img = np.zeros((16, 16, 3))
    img[:, :8] = left
    img[:, 8:] = right
    return {"value": img, "aux": {}, "truth": {"left_r": left[0], "left_g": left[1], "right_b": right[2]}}


def ms_grating(variant):
    ang = 30.0 if variant == 0 else 60.0
    th = math.radians(ang)
    yy, xx = np.mgrid[0:64, 0:64]
    img = 0.5 + 0.4 * np.cos(2 * np.pi * (xx * math.cos(th) + yy * math.sin(th)) / 8.0)
    return {"value": img, "aux": {}, "truth": {"theta": th}}


def ms_color_pair(variant):
    src = rng(variant, 42).uniform(0.2, 0.5, (32, 32, 3))
    hi = 0.9 if variant == 0 else 0.7
    ref = rng(variant, 43).uniform(0.4, hi, (32, 32, 3))
    return {"value": src, "aux": {"ref": ref}, "truth": {"ref_mean": float(ref.mean())}}


def ms_samples_1d(variant):
    """u = 101 evenly spaced values in [-2, 2]; v = scale·u + shift in shuffled order (monotone map)."""
    u = np.linspace(-2.0, 2.0, 101)
    scale, shift = (1.5, 2.0) if variant == 0 else (0.5, -1.0)
    v = scale * u + shift
    v = v[rng(variant, 44).permutation(v.size)]
    return {"value": u, "aux": {"v": v}, "truth": {"shift": shift, "std": scale * float(u.std())}}


def ms_sine_profile(variant):
    """Turned-surface profile: sine A = 1 / 1.5 µm, λ = 20 µm, dx = 0.5 µm, plus a curved form
    (tilt + bow) and one 3 µm-wide scratch 6A deep. Truth = Ra / Rq of the true roughness
    (sine + scratch, mean removed) computed directly with numpy — form must be removed by the filter,
    the scratch must not drag the mean line (robust filter) and stays in the roughness (ISO)."""
    A = 1.0 + 0.5 * variant
    x = np.arange(2048) * 0.5
    rough = A * np.sin(2 * np.pi * x / 20.0)
    rough[1000:1006] -= 6 * A
    form = 0.01 * x + 0.002 * (x - 500.0) ** 2 / 100.0
    q = rough - rough.mean()
    return {"value": rough + form, "aux": {"dx": 0.5},
            "truth": {"Ra": float(np.abs(q).mean()), "Rq": float(np.sqrt((q ** 2).mean()))}}


def ms_sine_surface(variant):
    """Areal height map 96x96 (dx = 1 µm): sine grating A = 0.5 / 0.8 µm, period 8 µm, on a tilted plane.
    After plane removal and the ISO 16610-21 Gaussian L-filter (λc = 24 µm) the grating keeps the
    closed-form transmission T = 1 - exp(-π (α λc / λ)²), α = sqrt(ln 2 / π): Sq = T·A/√2."""
    A = 0.5 + 0.3 * variant
    yy, xx = np.mgrid[0:96, 0:96].astype(float)
    z = A * np.sin(2 * np.pi * xx / 8.0) + 0.05 * xx - 0.03 * yy + 3.0
    alpha = math.sqrt(math.log(2) / math.pi)
    T = 1.0 - math.exp(-math.pi * (alpha * 24.0 / 8.0) ** 2)
    return {"value": z, "aux": {}, "truth": {"Sq": T * A / math.sqrt(2)}}


def ms_psd_surface(variant):
    """Self-affine surface synthesised from a PSD with analytic Sq = 0.5 / 0.8 µm (phases random,
    amplitudes fixed, so Sq does not depend on the seed)."""
    sq = 0.5 + 0.3 * variant
    return {"value": None, "aux": {"sq": sq}, "truth": {"Sq": sq}}


def ms_template(variant):
    """Smooth texture under an illumination change (gain 0.6, offset 0.2) + noise; template from the clean one."""
    img = _texture(96, 50 + variant)
    r0, c0 = (30, 40) if variant == 0 else (50, 20)
    tpl = img[r0:r0 + 24, c0:c0 + 24].copy()
    obs = 0.6 * img + 0.2 + 0.01 * rng(variant, 45).standard_normal(img.shape)
    return {"value": obs, "aux": {"tpl": tpl}, "truth": {"row": r0 + 12.0, "col": c0 + 12.0}}


def ms_crt_shift(variant):
    img = _texture(96, 60 + variant, corr=2.0)
    d = 13 if variant == 0 else 23
    return {"value": img, "aux": {"moved": np.roll(img, d, axis=1)}, "truth": {"d": float(d)}}


def ms_aoi(variant):
    """Reference texture; inspection frame = reference shifted by (dy, dx) and multiplied by a vignette."""
    ref = _texture(96, 70 + variant, corr=1.0)
    dy, dx = (3, 5) if variant == 0 else (-4, 7)
    yy, xx = np.mgrid[0:96, 0:96]
    flat = 0.5 + 0.4 * np.exp(-((yy - 48) ** 2 + (xx - 48) ** 2) / 3000.0)
    raw = np.roll(ref, (dy, dx), axis=(0, 1)) * flat
    return {"value": raw, "aux": {"flat": flat, "ref": ref}, "truth": {"dy": float(dy), "dx": float(dx)}}


def ms_strokes(variant):
    """White page with k dark vertical strokes of width w = 4 / 6 px (rows 16..48)."""
    w = 4 if variant == 0 else 6
    img = np.ones((64, 128))
    for i in range(4):
        c = 10 + 28 * i
        img[16:48, c:c + w] = 0.0
    return {"value": img, "aux": {}, "truth": {"width": float(w)}}


def ms_swt_field(variant):
    """Synthetic stroke-width field: k = 3 / 5 character-sized blobs of constant width 3 px."""
    k = 3 + 2 * variant
    m = np.zeros((48, 160))
    for i in range(k):
        c = 8 + 30 * i
        m[12:36, c:c + 10] = 3.0
    return {"value": m, "aux": {}, "truth": {"count": float(k)}}


def ms_swt_lines(variant):
    """Stroke-width field with n = 2 / 3 text lines of 4 glyph blobs (16 x 8 px, width 3 px) each.

    Lines start at row 8 and are 28 px apart (12 px of blank between lines: no vertical overlap), glyphs are
    6 px apart inside a line (well inside the 3 x height gap rule), so the line grouping is unambiguous."""
    n = 2 + variant
    m = np.zeros((8 + 28 * n, 96))
    for li in range(n):
        y0 = 8 + 28 * li
        for g in range(4):
            x0 = 6 + 14 * g
            m[y0:y0 + 16, x0:x0 + 8] = 3.0
    return {"value": m, "aux": {}, "truth": {"n_lines": n, "glyphs": 4, "line0_bottom": 24}}


SAMPLES = {
    "ms_blobs": ms_blobs, "ms_touching": ms_touching, "ms_disk_gt": ms_disk_gt, "ms_two_level": ms_two_level,
    "ms_edge": ms_edge, "ms_bar": ms_bar, "ms_hole": ms_hole, "ms_u8_edge": ms_u8_edge,
    "ms_u8_two_level": ms_u8_two_level, "ms_bayer": ms_bayer, "ms_shading": ms_shading, "ms_ca": ms_ca,
    "ms_sem_slope": ms_sem_slope, "ms_pl_psf": ms_pl_psf, "ms_plot": ms_plot,
    "ms_ellipse_canvas": ms_ellipse_canvas, "ms_noisy_pair": ms_noisy_pair, "ms_gray_pair": ms_gray_pair,
    "ms_levels": ms_levels, "ms_watermark": ms_watermark, "ms_copymove": ms_copymove, "ms_splice": ms_splice,
    "ms_circle_contour": ms_circle_contour, "ms_tps_disk": ms_tps_disk, "ms_shapefamily": ms_shapefamily,
    "ms_landmarks": ms_landmarks, "ms_naca": ms_naca, "ms_rgb_two": ms_rgb_two, "ms_grating": ms_grating,
    "ms_color_pair": ms_color_pair, "ms_samples_1d": ms_samples_1d, "ms_sine_profile": ms_sine_profile,
    "ms_sine_surface": ms_sine_surface, "ms_psd_surface": ms_psd_surface, "ms_template": ms_template, "ms_crt_shift": ms_crt_shift,
    "ms_aoi": ms_aoi, "ms_strokes": ms_strokes, "ms_swt_field": ms_swt_field, "ms_swt_lines": ms_swt_lines,
}


# ---- recipes ---------------------------------------------------------------------------------
_OTSU = {"op": "otsu", "a": 0.5, "b": 0.5}

RECIPES = [
    # ---------------- blob ----------------
    {"name": "Inspect — count bright particles and their total area", "family": "blob", "task": "count",
     "task_class": "inspection", "halcon": "Regions", "input_sort": "image", "sample": "ms_blobs",
     "stages": [_OTSU, {"op": "blob_label", "kw": {"connectivity": 8}}, {"op": "blob_features"}],
     "expect": [{"get": ["n"], "equals": "count"}, {"get": ["area", "@sum"], "approx": "area_px", "rtol": 0.03}],
     "note": "particle / pellet / dust counting: Otsu binarization, connected-component labelling, then the "
             "per-blob feature table (area px², centroid, perimeter, circularity...). Separated disks: the count is "
             "exact and the summed area matches the painted pixels"},
    {"name": "Inspect — split touching particles with distance-transform seeds", "family": "blob",
     "task": "count", "task_class": "inspection", "halcon": "Regions", "input_sort": "image",
     "sample": "ms_touching",
     "stages": [_OTSU, {"op": "blob_label"}, {"op": "blob_distance", "args": ["$s1"]},
                {"op": "blob_seeds", "args": ["$s3"], "kw": {"h": 2.0}},
                {"op": "blob_split", "args": ["$s2", "$s4", "$s3"]}],
     "expect": [{"get": ["@max"], "equals": "count"}],
     "note": "touching round parts merge into one component; the Euclidean distance map has one peak per part, "
             "h-maxima (h = 2 px) of it give one seed per part, and the seeded split separates them inside the "
             "original mask. Overlapping disks r = 12 px, 18 px apart: 2 / 3 parts"},
    {"name": "Inspect — particle count with an honest lower/upper interval", "family": "blob",
     "task": "count", "task_class": "inspection", "halcon": "Regions", "input_sort": "image",
     "sample": "ms_touching",
     "stages": [_OTSU, {"op": "blob_count_interval"}],
     "expect": [{"get": ["count"], "equals": "count"}, {"get": ["lo"], "equals": "count"},
                {"get": ["hi"], "equals": "count"}],
     "note": "counting touching objects with an uncertainty interval: each component's distance-map peaks are "
             "classified clearly-in / clearly-out / ambiguous, so the op reports [lo, hi] and whether the count is "
             "determined (here the necks are deep enough that lo = hi = true count)"},
    # ---------------- segmentation ----------------
    {"name": "Inspect — score a segmentation against the ground-truth mask (Dice / Jaccard)",
     "family": "segmentation", "task": "score", "task_class": "inspection", "halcon": "Segmentation",
     "input_sort": "image", "sample": "ms_disk_gt",
     "stages": [_OTSU, {"op": "blob_label"}, {"op": "seg_dice_jaccard", "args": ["$prev", "$aux.gt"]}],
     "expect": [{"get": ["dice"], "between": [0.97, 1.0]}, {"get": ["size_true"], "equals": "gt_area"}],
     "note": "evaluate a segmentation result against an annotated label image: Dice = 2|A∩B|/(|A|+|B|), "
             "Jaccard = IoU. A bright disk (r = 18 / 24 px) thresholded by Otsu should overlap its true mask "
             "almost perfectly"},
    {"name": "Inspect — separate touching parts with marker-controlled watershed", "family": "segmentation",
     "task": "segment", "task_class": "inspection", "halcon": "Segmentation", "input_sort": "image",
     "sample": "ms_touching",
     "stages": [_OTSU, {"op": "blob_distance"}, {"op": "invert", "a": 0.5, "b": 0.5},
                {"op": "blob_seeds", "args": ["$s2"], "kw": {"h": 2.0}},
                {"op": "watersheds_marker", "args": ["$s3", "$s4"]}],
     "expect": [{"get": ["@max"], "equals": "count"}],
     "note": "classic watershed split: distance transform of the binary mask, inverted so each part is a basin, "
             "one marker per part from h-maxima, then flooding from the markers. Note the flood also assigns the "
             "background to the nearest marker (no mask argument), so read the label count, not the areas"},
    {"name": "Preprocess — automatic gray threshold between two intensity classes (ISODATA)",
     "family": "segmentation", "task": "threshold", "task_class": "preprocess", "halcon": "Segmentation",
     "input_sort": "image", "sample": "ms_two_level",
     "stages": [{"op": "gaussian", "a": 0.3, "b": 0.5}, {"op": "threshold_isodata"}],
     "expect": [{"get": ["threshold"], "approx": "mid", "atol": 0.03}],
     "note": "ISODATA / Ridler-Calvard iterative threshold: the fixed point where the threshold is the mean of "
             "the two class means. Two-level image (0.2|0.7 and 0.3|0.9) after light smoothing: the threshold "
             "lands at the midpoint of the levels"},
    # ---------------- measure1d ----------------
    {"name": "Measure — subpixel edge position along a caliper line", "family": "measure1d", "task": "measure",
     "task_class": "measurement", "halcon": "1D Measuring", "input_sort": "image", "sample": "ms_edge",
     "stages": [{"op": "gen_measure_rectangle2",
                 "kw": {"row": 32, "col": 32, "phi": 0.0, "length1": 20, "length2": 5, "shape": "$aux.shape"}},
                {"op": "measure_pos", "args": ["$in", "$prev"], "kw": {"sigma": 1.0, "threshold": 0.1}}],
     "expect": [{"get": [0, "col"], "approx": "edge_col", "atol": 0.05}, {"get": ["@len"], "equals": 1}],
     "note": "HALCON-style 1-D measuring: a rotated measure rectangle (41 px long, 5 px averaging width) across a "
             "vertical step edge, Gaussian-smoothed profile derivative, subpixel edge position (col, px). The step "
             "between columns c-1 and c sits at c - 0.5"},
    {"name": "Measure — width of a bright bar in millimetres (edge pair + scale)", "family": "measure1d",
     "task": "measure", "task_class": "measurement", "halcon": "1D Measuring", "input_sort": "image",
     "sample": "ms_bar",
     "stages": [{"op": "gen_measure_rectangle2",
                 "kw": {"row": 32, "col": 32, "phi": 0.0, "length1": 24, "length2": 5, "shape": "$aux.shape"}},
                {"op": "measure_pairs", "args": ["$in", "$prev"], "kw": {"sigma": 1.0, "threshold": 0.1}},
                {"op": "table_px_to_mm", "kw": {"mm_per_px": "$aux.mm_per_px"}}],
     "expect": [{"get": [0, "width"], "approx": "width_px", "atol": 0.1},
                {"get": [0, "width_mm"], "approx": "width_mm", "atol": 0.005}],
     "note": "gauge a strip / trace / slot width: rising + falling edge pair on a caliper line, width in px, then "
             "converted to mm with the calibrated pixel pitch (0.05 mm/px). Bar 11 / 15 px wide"},
    {"name": "Measure — hole radius and centre by circle metrology", "family": "measure1d", "task": "measure",
     "task_class": "measurement", "halcon": "2D Metrology", "input_sort": "image", "sample": "ms_hole",
     "stages": [{"op": "create_metrology_model"},
                {"op": "add_metrology_object_circle_measure", "args": ["$s1"],
                 "kw": {"row": "$aux.row", "col": "$aux.col", "radius": "$aux.r", "n": 40}},
                {"op": "apply_metrology_model", "args": ["$s1", "$in"], "kw": {"measure_length": 6.0}},
                {"op": "table_px_to_mm", "kw": {"mm_per_px": "$aux.mm_per_px"}}],
     "expect": [{"get": [0, "params", "radius"], "approx": "radius", "atol": 0.15},
                {"get": [0, "params", "row"], "approx": "row", "atol": 0.1},
                {"get": [0, "params", "col"], "approx": "col", "atol": 0.1}],
     "note": "2-D metrology of a round hole / pin: a nominal circle from the drawing (off by 1 px and 2 px in "
             "radius), 40 radial edge probes, least-squares circle refit, then the result table gets mm columns "
             "(0.02 mm/px). Disk r = 18 / 24 px"},
    # ---------------- vx ----------------
    {"name": "Preprocess — OpenVX affine warp, then gauge where the edge moved", "family": "vx",
     "task": "measure", "task_class": "preprocess", "halcon": "Transformations", "input_sort": "image",
     "sample": "ms_u8_edge",
     "stages": [{"op": "vx_warp_affine", "args": ["$in", "$aux.M"],
                 "kw": {"interpolation": "bilinear", "border": "constant", "constant_value": 0}},
                {"op": "gen_measure_rectangle2",
                 "kw": {"row": 32, "col": 32, "phi": 0.0, "length1": 20, "length2": 5, "shape": "$aux.shape"}},
                {"op": "measure_pos", "args": ["$s1", "$s2"], "kw": {"threshold": 10.0}}],
     "expect": [{"get": [0, "col"], "approx": "edge_col", "atol": 0.05}],
     "note": "OpenVX 1.3 warp-affine on an 8-bit frame (inverse mapping: output (x,y) samples input M·(x,y,1)); "
             "a translation of +5 / +9 px moves the step edge from 23.5 to 28.5 / 32.5, read back with a caliper"},
    {"name": "Preprocess — OpenVX look-up table, then 16-bin histogram", "family": "vx", "task": "histogram",
     "task_class": "preprocess", "halcon": "Filters", "input_sort": "image", "sample": "ms_u8_two_level",
     "stages": [{"op": "vx_table_lookup", "args": ["$in", "$aux.lut"]},
                {"op": "vx_histogram", "kw": {"num_bins": 16, "offset": 0, "range_": 256}}],
     "expect": [{"get": [12, 1], "approx": "n_dark", "atol": 0.5}, {"get": [3, 1], "approx": "n_bright", "atol": 0.5}],
     "note": "OpenVX table lookup (here an inverting LUT 255 - v, U8) then the integer-binned histogram "
             "(16 bins of 16 levels). Dark 50 -> 205 lands in bin 12, bright 200 -> 55 in bin 3; counts are the "
             "pixel numbers of each class"},
    # ---------------- gfx2d ----------------
    {"name": "Preprocess — raw Bayer ISP: black level, demosaic, gray-world white balance", "family": "gfx2d",
     "task": "isp", "task_class": "preprocess", "halcon": "Color", "input_sort": "image", "sample": "ms_bayer",
     "stages": [{"op": "raw_black_level", "kw": {"offsets": "$aux.offset", "white": 1.0, "pattern": "RGGB"}},
                {"op": "raw_demosaic_bilinear", "kw": {"pattern": "RGGB"}},
                {"op": "awb_gains", "kw": {"method": "gray_world"}}],
     "expect": [{"get": [0], "approx": "g_r", "rtol": 1e-6}, {"get": [1], "approx": 1.0, "atol": 1e-9},
                {"get": [2], "approx": "g_b", "rtol": 1e-6}],
     "note": "camera image-signal-processing front end on an RGGB mosaic: subtract the 0.05 pedestal and rescale, "
             "bilinear demosaic, then gray-world white-balance gains (g_R, 1, g_B) = (mean G / mean R, 1, "
             "mean G / mean B). A uniform colour patch gives the gains in closed form"},
    {"name": "Preprocess — lens-shading (vignetting) correction from a flat-field frame", "family": "gfx2d",
     "task": "flatfield", "task_class": "preprocess", "halcon": "Filters", "input_sort": "image",
     "sample": "ms_shading",
     "stages": [{"op": "lens_shading_gain"}, {"op": "lens_shading_correct", "args": ["$aux.raw", "$s1"]}],
     "expect": [{"get": ["@max"], "approx": "flat_mean", "rtol": 1e-6},
                {"get": ["@min"], "approx": "flat_half", "rtol": 1e-6}],
     "note": "shoot a uniform white target, build gain = mean/flat, multiply the scene frame by it: the radial "
             "fall-off disappears and the scene (reflectance 0.5 | 1.0) comes back as reflectance x mean(flat): max = mean(flat), "
             "min = mean(flat)/2"},
    # ---------------- generative ----------------
    {"name": "Simulate — rule-90 cellular automaton (Sierpinski) stepped and rendered", "family": "generative",
     "task": "simulate", "task_class": "simulation", "halcon": None, "input_sort": None, "sample": "ms_ca",
     "stages": [{"op": "perpetual_state", "kw": {"name": "elementary_ca", "size": 65, "rule": 90}, "call": "raw", "call_reason": "fs.ledger.perpetual_state is broken: its kwarg `name` collides with the ledger call(name, ...), TypeError (2026-11-03); the OP_GRAPH executor is called directly. TODO: drop call raw once fix/completeness-stage0-2026-11-03 (e5c854e28f, opassist calls the function directly on a name collision) is merged"},
                {"op": "perpetual_step", "kw": {"steps": "$aux.steps"}},
                {"op": "perpetual_render", "kw": {"cell": 1}}],
     "expect": [{"get": ["$s2", "row", "@sum"], "approx": "live", "atol": 0.5}],
     "note": "generative pattern stream: state -> step n -> render. From a single live cell, rule 90 grows "
             "Pascal's triangle mod 2, so the live cells in row n are exactly 2^popcount(n) (n = 5 -> 4, 7 -> 8) "
             "while the pattern has not reached the border"},
    {"name": "Simulate — SEM secondary-electron image of a sloped facet", "family": "generative",
     "task": "simulate", "task_class": "simulation", "halcon": None, "input_sort": "image",
     "sample": "ms_sem_slope",
     "stages": [{"op": "sem_render", "kw": {"pixel_nm": 1.0, "psf_px": 1.5, "base": 0.25}}],
     "expect": [{"get": ["@max"], "approx": "bright", "rtol": 1e-3}, {"get": ["@min"], "approx": 0.25, "atol": 1e-6}],
     "note": "scanning-electron-microscope look of a height field: flat areas at the base brightness, slopes "
             "brighter by sec θ (edge effect), beam PSF blur. Facet gradient 0.5 / 1.0 -> 0.25·sqrt(1+g²). "
             "Single stage: the family's renderers take a height field and nothing in this book produces one"},
    {"name": "Simulate — photoluminescence carrier-diffusion PSF", "family": "generative", "task": "simulate",
     "task_class": "simulation", "halcon": None, "input_sort": None, "sample": "ms_pl_psf",
     "stages": [{"op": "pl_diffusion_psf", "kw": {"diffusion_length_px": "$aux.L"}}],
     "expect": [{"get": ["@sum"], "approx": "mass", "atol": 5e-3}],
     "note": "Green's function K0(r/L)/(2πL²) of minority-carrier diffusion (solar-cell / wafer PL imaging) as "
             "an image kernel; total mass is analytically 1 (the 8L cut loses ~1.2e-3). L = 3 / 5 px. Single "
             "generator stage: it is the kernel other PL simulations convolve with"},
    # ---------------- annotate ----------------
    {"name": "Visualize — plot a measured series on data axes (data -> pixel mapping)", "family": "annotate",
     "task": "plot", "task_class": "visualization", "halcon": None, "input_sort": "image", "sample": "ms_plot",
     "stages": [{"op": "axes_transform", "kw": {"rect": "$aux.rect", "xlim": "$aux.xlim", "ylim": "$aux.ylim"}},
                {"op": "data_to_pixel", "args": ["$s1", "$aux.x", "$aux.y"]},
                {"op": "plot_series", "args": ["$in", "$s1", "$aux.x", "$aux.y"], "kw": {"kind": "line"}}],
     "expect": [{"get": ["$s2", 8, 0], "approx": "px_last", "atol": 1e-9},
                {"get": ["$s2", 8, 1], "approx": "py_last", "atol": 1e-9}],
     "note": "draw a measurement trend into a report image: closed-form axes (rect 81x61 px, x∈[0,8], y∈[0,6], "
             "y up), data -> pixel coordinates, then the line plot. The last point (8, 8s) maps to px = 90, "
             "py = 70 - 60·(8s/6)"},
    {"name": "Visualize — draw a filled ellipse marker and verify its pixel area", "family": "annotate",
     "task": "draw", "task_class": "visualization", "halcon": None, "input_sort": "image",
     "sample": "ms_ellipse_canvas",
     "stages": [{"op": "ellipse", "kw": {"center": "$aux.center", "radii": "$aux.radii", "fill": True}},
                _OTSU, {"op": "blob_label"}, {"op": "blob_features"}],
     "expect": [{"get": ["area", 0], "approx": "area", "rtol": 0.02}, {"get": ["n"], "equals": 1}],
     "note": "overlay drawing that must not lie about size: a filled ellipse (semi-axes 20x10 / 24x14 px) is "
             "drawn, re-segmented and measured; its area must be πab within rasterization (2 %)"},
    # ---------------- imgmetrics ----------------
    {"name": "Inspect — image fidelity report of a noisy capture (PSNR / RMSE with conditions)",
     "family": "imgmetrics", "task": "score", "task_class": "inspection", "halcon": None, "input_sort": "image",
     "sample": "ms_noisy_pair",
     "stages": [{"op": "compare_images", "args": ["$in", "$aux.noisy"], "kw": {"data_range": 1.0}},
                {"op": "metrics_table", "kw": {"order": ["psnr", "rmse"]}}],
     "expect": [{"get": [0, 1], "approx": "psnr", "atol": 0.2}, {"get": [1, 1], "approx": "rmse", "rtol": 0.03}],
     "note": "full-reference image quality: one call measures MSE/RMSE/PSNR/SSIM/MI/NCD and records the "
             "conditions (data_range, bins, SSIM window); the table keeps those condition rows next to the "
             "numbers. Additive noise σ = 0.03 / 0.06 on a unit range: PSNR = -20·log10 σ dB"},
    {"name": "Inspect — perceptual colour difference ΔE*ab against a reference colour", "family": "imgmetrics",
     "task": "color", "task_class": "inspection", "halcon": "Color", "input_sort": "rgbimage",
     "sample": "ms_gray_pair",
     "stages": [{"op": "rgb_to_lab"}, {"op": "rgb_to_lab", "args": ["$aux.ref"]},
                {"op": "delta_e_76", "args": ["$s1", "$s2"]}],
     "expect": [{"get": ["@max"], "approx": "dL", "atol": 0.05}, {"get": ["@min"], "approx": 0.0, "atol": 1e-6}],
     "note": "colour QC of a print / painted part: sRGB -> CIE L*a*b* (D65) for sample and reference, per-pixel "
             "ΔE76. For greys ΔE76 = |ΔL*| computed independently from the CIE formula (0.5 vs 0.4 / 0.7)"},
    {"name": "Inspect — mutual information of a multimodal pair (inverted contrast)", "family": "imgmetrics",
     "task": "score", "task_class": "analysis", "halcon": None, "input_sort": "image", "sample": "ms_levels",
     "stages": [{"op": "invert", "a": 0.5, "b": 0.5},
                {"op": "mutual_information", "args": ["$in", "$prev"], "kw": {"bins": 64}}],
     "expect": [{"get": [], "approx": "bits", "atol": 1e-6}],
     "note": "the similarity used for multimodal registration (CT/MR, visible/IR): MI is blind to an inverted "
             "intensity mapping, so an image vs its negative scores its full entropy, log2(k) bits for k equally "
             "populated levels (4 -> 2 bits, 8 -> 3 bits)"},
    # ---------------- imgforensics ----------------
    {"name": "Inspect — embed and blindly recover an integrity watermark", "family": "imgforensics",
     "task": "watermark", "task_class": "inspection", "halcon": None, "input_sort": "image",
     "sample": "ms_watermark",
     "stages": [{"op": "watermark_embed", "args": ["$in", "$aux.bits"], "kw": {"strength": 0.1}},
                {"op": "watermark_extract", "kw": {"n_bits": 16}}],
     "expect": [{"get": [], "equals": "bits"}],
     "note": "DWT-DCT mid-band coefficient-pair watermark (Hsu & Wu): 16 bits into a 64x64 image (capacity "
             "(32/8)² = 16), blind extraction without the original must return the same bits (BER 0)"},
    {"name": "Inspect — detect a copy-move forgery and its displacement", "family": "imgforensics",
     "task": "forensics", "task_class": "inspection", "halcon": None, "input_sort": "image",
     "sample": "ms_copymove",
     "stages": [{"op": "gaussian", "a": 0.3, "b": 0.5},
                {"op": "copy_move_regions", "kw": {"method": "block"}}],
     "expect": [{"get": [0, "offset", 0], "approx": "drow", "atol": 0.5},
                {"get": [0, "offset", 1], "approx": "dcol", "atol": 0.5}],
     "note": "image forensics: a 16x16 region is duplicated inside the same picture. Block-DCT matching "
             "(Fridrich 2003) groups identical blocks by shift vector; the dominant shift is the copy offset "
             "(row, col) px. Light smoothing first, as after a re-save"},
    {"name": "Inspect — locate a spliced patch with different sensor noise", "family": "imgforensics",
     "task": "forensics", "task_class": "inspection", "halcon": None, "input_sort": "image",
     "sample": "ms_splice",
     "stages": [{"op": "noise_inconsistency_map", "kw": {"block": 16}}, _OTSU, {"op": "blob_label"},
                {"op": "blob_features"}],
     "expect": [{"get": ["n"], "equals": 1}, {"get": ["area", 0], "approx": "area", "atol": 1.0},
                {"get": ["row", 0], "approx": "row", "atol": 0.5}, {"get": ["col", 0], "approx": "col", "atol": 0.5}],
     "note": "splicing detection: block-wise noise σ (Immerkær estimator, 16 px blocks) shows a step where a "
             "patch from another camera / exposure was pasted (σ 0.01 vs 0.04); Otsu on the σ map and blob "
             "features give the pasted area and its centre"},
    # ---------------- colortransport ----------------
    {"name": "Preprocess — colour transfer of a product photo to a reference look", "family": "colortransport",
     "task": "color", "task_class": "preprocess", "halcon": "Color", "input_sort": "rgbimage",
     "sample": "ms_color_pair",
     "stages": [{"op": "color_transfer", "args": ["$in", "$aux.ref"], "kw": {"method": "reinhard", "space": "rgb"}}],
     "expect": [{"get": ["@mean"], "approx": "ref_mean", "atol": 0.002}],
     "note": "Reinhard colour transfer (per-channel mean and std matched to the reference) so images from two "
             "cameras / light set-ups look alike before comparison; with no gamut clipping the result's mean "
             "equals the reference mean. Single stage: the op is the whole task"},
    {"name": "Measure — 1-D optimal transport plan between two sample sets", "family": "colortransport",
     "task": "transport", "task_class": "analysis", "halcon": None, "input_sort": "signal",
     "sample": "ms_samples_1d",
     "stages": [{"op": "transport_plan_1d", "args": ["$in", "$aux.v"]},
                {"op": "apply_transport", "args": ["$prev", "$aux.v"]}],
     "expect": [{"get": ["@mean"], "approx": "shift", "atol": 1e-9}, {"get": ["@std"], "approx": "std", "rtol": 1e-9}],
     "note": "exact 1-D optimal transport (monotone north-west-corner plan) from samples u to samples v, then "
             "the barycentric map pulls v back onto u: for v = s·u + c (shuffled) every u_i is sent to s·u_i + c, "
             "so the mapped mean is c and the std s·std(u). Used for histogram / intensity matching"},
    # ---------------- shape2d ----------------
    {"name": "Measure — radius of a round part from its contour (elliptic Fourier)", "family": "shape2d",
     "task": "measure", "task_class": "measurement", "halcon": "XLD", "input_sort": "pairs",
     "sample": "ms_circle_contour",
     "stages": [{"op": "fourier_smooth", "kw": {"keep": 5}}, {"op": "elliptic_fourier", "kw": {"n_harmonics": 5}},
                {"op": "invariants", "kw": {"scale_invariant": False}}],
     "expect": [{"get": [0, 0], "approx": "radius", "atol": 0.15}, {"get": [0, 1], "approx": "radius", "atol": 0.15}],
     "note": "contour shape descriptor: low-pass the noisy outline (keep 5 frequencies), Kuhl-Giardina elliptic "
             "Fourier coefficients, rotation/start-point invariant harmonic ellipse axes. For a circle the first "
             "harmonic's axes are both the radius (15 / 20 px). (For an ellipse they are NOT the geometric "
             "semi-axes: KG parametrises by arc length — a 20x10 ellipse gives 18.3 x 10.8)"},
    {"name": "Preprocess — thin-plate-spline warp from control points, check the part moved", "family": "shape2d",
     "task": "warp", "task_class": "preprocess", "halcon": "Transformations", "input_sort": "image",
     "sample": "ms_tps_disk",
     "stages": [{"op": "warp_tps_image", "args": ["$in", "$aux.src", "$aux.dst"]}, _OTSU, {"op": "blob_label"},
                {"op": "blob_features"}],
     "expect": [{"get": ["row", 0], "approx": "row_moved", "atol": 0.3},
                {"get": ["col", 0], "approx": "col_moved", "atol": 0.3}],
     "note": "image registration / morphing by thin-plate spline: control points (x = col, y = row) move by "
             "(3, 6) / (-4, 5) px, the image content follows; the disk's centroid after segmentation must move "
             "by the same vector"},
    # ---------------- shapestat ----------------
    {"name": "Analyze — statistical shape model: variance explained by the first mode", "family": "shapestat",
     "task": "model", "task_class": "analysis", "halcon": None, "input_sort": None, "sample": "ms_shapefamily",
     "stages": [{"op": "shape_synth_family",
                 "kw": {"n_shapes": 60, "n_points": 40, "n_modes": 2, "mode_scale": "$aux.mode_scale", "seed": 3}},
                {"op": "shape_pca", "kw": {"align": False}}, {"op": "shape_explained_variance"}],
     "expect": [{"get": [0], "approx": "first", "atol": 0.04}],
     "note": "point-distribution model (PCA of corresponding landmarks): a family with two known orthonormal "
             "modes of weights (0.3, 0.12) / (0.3, 0.2) gives first-mode share ρ/(1+ρ), ρ = (w1/w2)². "
             "align=False because Procrustes alignment removes size and eats mode 1 (documented); 60 shapes, "
             "sampling error of the share ~0.02"},
    {"name": "Inspect — form error after best-fit similarity alignment of landmarks", "family": "shapestat",
     "task": "align", "task_class": "inspection", "halcon": "3D Matching", "input_sort": "points",
     "sample": "ms_landmarks",
     "stages": [{"op": "procrustes_align", "args": ["$in", "$aux.target"]},
                {"op": "procrustes_distance", "args": ["$prev", "$aux.target"],
                 "kw": {"scaling": False, "normalize": False}}],
     "expect": [{"get": [], "approx": "rms", "rtol": 0.2}],
     "note": "align measured landmarks to the nominal ones (rotation 0.4 rad, scale 2, shift) with a Procrustes "
             "similarity fit, then the residual RMS per point is the form error; with isotropic noise σ it is "
             "√3σ·√(1-7/3N) (σ = 0.01 / 0.03, N = 40)"},
    # ---------------- profile ----------------
    {"name": "Inspect — airfoil blade profile deviation from the nominal NACA section", "family": "profile",
     "task": "inspect", "task_class": "inspection", "halcon": "2D Metrology", "input_sort": None,
     "sample": "ms_naca",
     "stages": [{"op": "profile_synth_naca4", "kw": {"code": "$aux.code"}},
                {"op": "profile_perturb", "kw": {"kind": "thicken", "amount": "$aux.amount"}},
                {"op": "profile_deviation", "args": ["$prev", "$s1"]}],
     "expect": [{"get": ["mean"], "approx": "amount", "atol": 0.0002}],
     "note": "turbine / fan blade inspection: nominal NACA 4-digit section, a measured copy uniformly thickened "
             "by 0.002 / 0.004 chord, signed normal deviation after chord alignment; the mean deviation returns "
             "the injected amount (units: chord = 1)"},
    {"name": "Measure — airfoil leading-edge radius", "family": "profile", "task": "measure",
     "task_class": "measurement", "halcon": "2D Metrology", "input_sort": None, "sample": "ms_naca",
     "stages": [{"op": "profile_synth_naca4", "kw": {"code": "$aux.code"}}, {"op": "profile_normalise"},
                {"op": "profile_leading_edge_radius"}],
     "expect": [{"get": [], "approx": "le_radius", "rtol": 0.02}],
     "note": "leading-edge radius of a blade section after normalising to unit chord; for NACA 00tt the design "
             "value is 1.1019·t² (t = 0.12 / 0.18 -> 0.0159 / 0.0357 chord)"},
    # ---------------- roughness ----------------
    {"name": "Measure — profile roughness Ra / Rq after a robust Gaussian filter (scratched, curved part)",
     "family": "roughness", "task": "measure", "task_class": "measurement", "halcon": None,
     "input_sort": "signal", "sample": "ms_sine_profile",
     "stages": [{"op": "robust_gaussian_profile", "kw": {"dx": "$aux.dx", "lambda_c": 80.0}},
                {"op": "profile_params", "kw": {"dx": "$aux.dx"}}],
     "expect": [{"get": ["Ra"], "approx": "Ra", "rtol": 0.01}, {"get": ["Rq"], "approx": "Rq", "rtol": 0.01}],
     "note": "ISO 16610-31 robust Gaussian regression filter (λc = 80 µm, Tukey biweight) separates the mean "
             "line (tilt + bow form) from the roughness without being dragged into a deep scratch, then ISO 4287 "
             "Ra / Rq. Feed marks: sine A = 1 / 1.5 µm, λ = 20 µm (passes the filter ~100 %), dx = 0.5 µm"},
    {"name": "Measure — profile roughness Ra / Rq after a robust spline filter", "family": "roughness",
     "task": "measure", "task_class": "measurement", "halcon": None, "input_sort": "signal",
     "sample": "ms_sine_profile",
     "stages": [{"op": "robust_spline_profile", "kw": {"dx": "$aux.dx", "lambda_c": 80.0}},
                {"op": "profile_params", "kw": {"dx": "$aux.dx"}}],
     "expect": [{"get": ["Ra"], "approx": "Ra", "rtol": 0.01}, {"get": ["Rq"], "approx": "Rq", "rtol": 0.01}],
     "note": "same scratched, curved profile through the robust spline mean-line filter (ISO 16610-32 style, "
             "λc = 80 µm) then Ra / Rq; the alternative to the Gaussian regression when the form is strongly "
             "curved"},
    {"name": "Measure — areal roughness Sq: form removal, Gaussian L-filter, ISO 25178 parameters",
     "family": "roughness", "task": "measure", "task_class": "measurement", "halcon": None,
     "input_sort": "depth", "sample": "ms_sine_surface",
     "stages": [{"op": "surface_form_remove", "kw": {"dx": 1.0, "order": 1}},
                {"op": "surface_filter", "kw": {"dx": 1.0, "lambda_c": 24.0, "end_effect": "reject"}},
                {"op": "surface_params", "kw": {"dx": 1.0}}],
     "expect": [{"get": ["Sq"], "approx": "Sq", "rtol": 0.002}],
     "note": "the full areal chain on a tilted height map: least-squares plane removal, ISO 16610-21 Gaussian "
             "L-filter λc = 24 µm (end regions rejected, 96 -> 60 px), then Sq/Sa/Sz...; a sine grating "
             "(A = 0.5 / 0.8 µm, period 8 µm) keeps Sq = T·A/√2 with the filter's closed-form transmission T"},
    {"name": "Measure — Sq of a synthetic self-affine surface (PSD synthesis + form removal)",
     "family": "roughness", "task": "measure", "task_class": "simulation", "halcon": None,
     "input_sort": None, "sample": "ms_psd_surface",
     "stages": [{"op": "surface_synth_psd",
                 "kw": {"n": 64, "dx": 1.0, "hurst": 0.5, "lambda_lo": 4.0, "lambda_hi": 16.0, "sq": "$aux.sq",
                        "seed": 1}},
                {"op": "surface_form_remove", "kw": {"dx": 1.0}},
                {"op": "surface_params", "kw": {"dx": 1.0}}],
     "expect": [{"get": ["Sq"], "approx": "Sq", "rtol": 0.003}],
     "note": "test surface with a known answer for a roughness pipeline: band 4-16 µm, Hurst 0.5, analytic "
             "Sq = 0.5 / 0.8 µm (seed-independent by Parseval); plane removal takes only ~0.1 % of it, so "
             "surface_params must return the target Sq"},
    # ---------------- quat ----------------
    {"name": "Preprocess — rotate colours about the grey axis (quaternion colour rotation)", "family": "quat",
     "task": "color", "task_class": "preprocess", "halcon": "Color", "input_sort": "rgbimage",
     "sample": "ms_rgb_two",
     "stages": [{"op": "rgb_to_quaternion"},
                {"op": "quat_color_rotate", "kw": {"axis_rgb": [1.0, 1.0, 1.0], "angle_rad": 2 * math.pi / 3}},
                {"op": "quaternion_to_rgb"}],
     "expect": [{"get": [0, 0, 1], "approx": "left_r", "atol": 1e-9}, {"get": [0, 0, 2], "approx": "left_g", "atol": 1e-9},
                {"get": [0, 12, 0], "approx": "right_b", "atol": 1e-9}],
     "note": "pure-quaternion colour pixels (Sangwine) rotated by q·v·q* about the grey axis by 120°: the hue "
             "rotates exactly, (r, g, b) -> (b, r, g), luminance axis untouched — a colour shift no channel-wise "
             "operation can express"},
    {"name": "Measure — local orientation of a grating with the monogenic signal", "family": "quat",
     "task": "measure", "task_class": "measurement", "halcon": "Texture", "input_sort": "image",
     "sample": "ms_grating",
     "stages": [{"op": "monogenic_signal", "kw": {"wavelength_px": 8.0}}, {"op": "monogenic_orientation"}],
     "expect": [{"get": ["@median"], "approx": "theta", "atol": 0.005}],
     "note": "texture / fibre / scratch direction: band-pass at the 8 px wavelength plus its Riesz pair (Felsberg "
             "& Sommer) gives orientation atan2(R2, R1) continuously, not quantised to a filter bank; grating at "
             "30° / 60° (rad, mod π)"},
    # ---------------- codematch ----------------
    {"name": "Inspect — locate a part template under an illumination change (orientation codes)",
     "family": "codematch", "task": "match", "task_class": "inspection", "halcon": "Matching",
     "input_sort": "image", "sample": "ms_template",
     "stages": [{"op": "gaussian", "a": 0.2, "b": 0.5}, {"op": "ocm_match", "args": ["$prev", "$aux.tpl"]}],
     "expect": [{"get": ["row"], "approx": "row", "atol": 0.5}, {"get": ["col"], "approx": "col", "atol": 0.5}],
     "note": "orientation-code matching (Ullah & Kaneko): gradient-direction codes are invariant to gain and "
             "offset, so a template cut from the reference still finds its place after a 0.6x gain + 0.2 offset "
             "and noise; returns the template centre (row, col)"},
    # ---------------- residue ----------------
    {"name": "Measure — large displacement from multi-wavelength phases (CRT unwrapping)", "family": "residue",
     "task": "measure", "task_class": "measurement", "halcon": None, "input_sort": "image",
     "sample": "ms_crt_shift",
     "stages": [{"op": "crt_displacement", "args": ["$in", "$aux.moved"]}],
     "expect": [{"get": ["d", "@median"], "approx": "d", "atol": 0.05}],
     "note": "phase-based displacement wraps at half a wavelength (8 px here); bands at coprime wavelengths "
             "5..16 px resolved by the Chinese remainder theorem recover 13 / 23 px shifts unambiguously. Single "
             "stage: both images are inputs and a registry pre-filter can only act on one"},
    # ---------------- aoi ----------------
    {"name": "Inspect — flat-field correct, then register the frame to the golden image", "family": "aoi",
     "task": "register", "task_class": "inspection", "halcon": "Matching", "input_sort": "image",
     "sample": "ms_aoi",
     "stages": [{"op": "flat_field_correct", "args": ["$in", "$aux.flat"]},
                {"op": "register_image", "args": ["$aux.ref", "$prev"]}],
     "expect": [{"get": ["dy"], "approx": "dy", "atol": 0.05}, {"get": ["dx"], "approx": "dx", "atol": 0.05},
                {"get": ["consistent"], "equals": True}],
     "note": "automated optical inspection front end: divide out the illumination vignette with a flat frame, "
             "then phase-correlation registration against the golden reference with a reliability verdict; "
             "shift (3, 5) / (-4, 7) px. The reference needs fine texture: on a very smooth one (Gaussian "
             "correlation ~3 px) the sub-pixel refinement biased an integer shift by 0.2 px"},
    # ---------------- text ----------------
    {"name": "Inspect — stroke width of printed characters (SWT)", "family": "text", "task": "ocr",
     "task_class": "inspection", "halcon": "OCR", "input_sort": "image", "sample": "ms_strokes",
     "stages": [{"op": "swt_map", "kw": {"dark_on_light": True}}],
     "expect": [{"get": ["swt", "@max"], "approx": "width", "atol": 0.1}],
     "note": "stroke width transform (Epshtein 2010): rays from each dark-stroke boundary across to the opposite "
             "edge write the stroke width (4 / 6 px) into every pixel on the ray — the cue for text detection and "
             "print-quality checks. Single stage: its table output cannot feed text_candidates (type gap)"},
    {"name": "Inspect — character candidates from a stroke-width field", "family": "text", "task": "ocr",
     "task_class": "inspection", "halcon": "OCR", "input_sort": "matrix", "sample": "ms_swt_field",
     "stages": [{"op": "text_candidates", "kw": {"min_area": 8}}],
     "expect": [{"get": ["boxes", "@len"], "equals": "count"}, {"get": ["n_components"], "equals": "count"}],
     "note": "connected components of constant stroke width with sane aspect and size are kept as character "
             "boxes [y0, x0, y1, x1]; a synthetic SWT field with 3 / 5 glyph-sized blobs. Single stage; the "
             "next recipe hands its table on to text_lines"},
    {"name": "Inspect — group character candidates into text lines", "family": "text", "task": "ocr",
     "task_class": "inspection", "halcon": "OCR", "input_sort": "matrix", "sample": "ms_swt_lines",
     "stages": [{"op": "text_candidates", "kw": {"min_area": 8}}, {"op": "text_lines"}],
     "expect": [{"get": ["lines", "@len"], "equals": "n_lines"}, {"get": ["members", 0, "@len"], "equals": "glyphs"},
                {"get": ["lines", 0, 2], "equals": "line0_bottom"}],
     "note": "text layout without a recogniser: character candidates (constant stroke width, sane size / aspect) "
             "are joined into lines when they overlap vertically by half the smaller height and sit within 3 "
             "heights horizontally (Epshtein 2010 grouping, overlap rule). The candidates table goes straight "
             "into text_lines; 2 / 3 lines of 4 glyphs each, line boxes [y0, x0, y1, x1]"},
]


MISSING_OPS = [
    {"family": "text", "need": "take the SWT field (matrix) out of swt_map's table, or a text_candidates "
                               "that accepts swt_map's dict",
     "why": "swt_map -> table and text_candidates(matrix) do not connect; the detector pipeline "
            "swt -> candidates -> lines cannot be chained"},
    {"family": "vx", "need": "split vx_sobel3x3's {gx, gy} table into two S16 images (or a vx_sobel_magnitude)",
     "why": "vx_magnitude / vx_phase take two image2d, vx_sobel3x3 returns one table: the OpenVX gradient "
            "graph Sobel -> Magnitude -> NonMax cannot be chained"},
    {"family": "roughness", "need": "dominant wavelength (peak) of surface_psd's (frequency, PSD) pairs",
     "why": "feed-mark wavelength from an areal PSD needs an argmax-to-frequency read; no op converts the "
            "pairs to a scalar"},
    {"family": "segmentation", "need": "a mask argument (or a masked variant) for watersheds_marker",
     "why": "the flood assigns background pixels to the nearest marker, so region areas after a watershed "
            "split are wrong unless the mask is applied by another op (blob_split does that, but only with "
            "distance-map seeds)"},
]


FAILED_ATTEMPTS = [
    {"family": "text", "recipe": "Inspect — detect text: SWT then character candidates", "op": "text_candidates",
     "error": "swt_map returns table {swt, edges, ...}; text_candidates takes matrix (the swt field)",
     "cause": "type_gap"},
    {"family": "vx", "recipe": "Inspect — OpenVX gradient magnitude", "op": "vx_magnitude",
     "error": "vx_sobel3x3 returns table {gx, gy, valid}; vx_magnitude needs two image2d", "cause": "type_gap"},
]


#: 本ごとの日本語ノート(この本で足したレシピ。notes_ja.py の表と合わせて引く)。
NOTES_JA = {
    "Inspect — group character candidates into text lines":
        "文字候補を行にまとめる — 線幅が一定の文字候補の矩形を、縦に重なり横に近いものどうし繋いで"
        "テキストの行の矩形にする(認識器なし、Epshtein 2010 の行まとめ)。候補の表をそのまま渡す。",
}
