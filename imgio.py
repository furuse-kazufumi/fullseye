"""Input/output enrichment for fullseye — coercion, colormap visualisation, and
export helpers so other projects can *feed* varied inputs and *see / save* the
results without pulling in matplotlib.

Core (coercion + colormaps + overlays + PLY) is numpy-only. File save/load uses
opencv-python if present, else Pillow, else raises a clear error.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "to_float01", "to_uint8", "ensure_gray", "ensure_color", "normalize",
    "apply_cmap", "colorize_depth", "colorize_disparity", "colorize_labels",
    "colorize_height", "shaded_relief", "overlay_mask", "save", "load", "save_ply",
    "COLORMAPS",
]

# A library of false-colour palettes (HDevelop-style pseudo-colour). Sequential
# ones are control-point ramps; a few are analytic. All are approximations of the
# well-known public-domain maps, chosen to read as distinct, legible palettes.
_LUTS = {
    "viridis": [[0.267, 0.005, 0.329], [0.283, 0.141, 0.458], [0.254, 0.265, 0.530],
                [0.207, 0.372, 0.553], [0.164, 0.471, 0.558], [0.128, 0.567, 0.551],
                [0.135, 0.659, 0.518], [0.267, 0.749, 0.441], [0.478, 0.821, 0.318],
                [0.741, 0.873, 0.150], [0.993, 0.906, 0.144]],
    "turbo": [[0.19, 0.07, 0.23], [0.27, 0.31, 0.84], [0.11, 0.56, 0.99],
              [0.07, 0.79, 0.75], [0.30, 0.92, 0.44], [0.71, 0.96, 0.22],
              [0.95, 0.76, 0.16], [0.98, 0.47, 0.12], [0.85, 0.20, 0.05], [0.63, 0.07, 0.02]],
    "magma": [[0.0, 0.0, 0.02], [0.1, 0.06, 0.2], [0.28, 0.06, 0.4], [0.5, 0.12, 0.42],
              [0.72, 0.2, 0.33], [0.9, 0.36, 0.24], [0.98, 0.6, 0.35], [0.99, 0.8, 0.55],
              [0.99, 0.99, 0.75]],
    "plasma": [[0.05, 0.03, 0.53], [0.35, 0.0, 0.65], [0.6, 0.13, 0.6], [0.8, 0.3, 0.47],
               [0.93, 0.47, 0.33], [0.99, 0.65, 0.2], [0.96, 0.83, 0.14], [0.94, 0.98, 0.13]],
    "inferno": [[0.0, 0.0, 0.02], [0.15, 0.04, 0.24], [0.4, 0.07, 0.35], [0.65, 0.17, 0.28],
                [0.87, 0.35, 0.14], [0.98, 0.6, 0.06], [0.99, 0.85, 0.35], [0.99, 1.0, 0.9]],
    "cividis": [[0.0, 0.13, 0.3], [0.0, 0.3, 0.5], [0.3, 0.45, 0.55], [0.55, 0.58, 0.55],
                [0.78, 0.72, 0.45], [1.0, 0.9, 0.2]],
    "terrain": [[0.2, 0.2, 0.6], [0.0, 0.6, 1.0], [0.0, 0.8, 0.4], [0.9, 0.9, 0.5],
                [0.6, 0.45, 0.35], [1.0, 1.0, 1.0]],
    "ocean": [[0.0, 0.0, 0.0], [0.0, 0.15, 0.35], [0.0, 0.4, 0.55], [0.3, 0.7, 0.8],
              [0.75, 0.95, 1.0]],
    "coolwarm": [[0.23, 0.30, 0.75], [0.55, 0.6, 0.85], [0.87, 0.87, 0.87],
                 [0.9, 0.6, 0.5], [0.71, 0.02, 0.15]],       # diverging (blue-white-red)
}
COLORMAPS = ("gray", "jet", "viridis", "turbo", "magma", "plasma", "inferno",
             "cividis", "hot", "cool", "hsv", "terrain", "ocean", "coolwarm", "spring", "bone")


# ---- input coercion -------------------------------------------------------- #
def to_float01(x):
    """Coerce an image-like to float64 in [0, 1].

    Handles uint8/uint16 (divide by dtype max), bool (0/1), and float (passed
    through — assumed already normalised). PIL images and file paths are read if
    the optional backend is available.
    """
    if isinstance(x, str):
        return load(x)
    if type(x).__module__.startswith("PIL"):
        x = np.asarray(x)
    a = np.asarray(x)
    if a.dtype == bool:
        return a.astype(np.float64)
    if a.dtype.kind in "ui":
        return a.astype(np.float64) / float(np.iinfo(a.dtype).max)
    return a.astype(np.float64)


def to_uint8(x):
    """Clip a [0, 1] array to uint8 [0, 255]."""
    return np.clip(np.asarray(x, np.float64) * 255.0, 0, 255).astype(np.uint8)


def normalize(x, vmin=None, vmax=None):
    """Linearly rescale finite values to [0, 1] over [vmin, vmax] (auto if None).
    Non-finite entries are left as-is (callers usually mask them)."""
    a = np.asarray(x, np.float64)
    fin = np.isfinite(a)
    if not fin.any():
        return np.zeros_like(a)
    lo = float(a[fin].min()) if vmin is None else float(vmin)
    hi = float(a[fin].max()) if vmax is None else float(vmax)
    if hi <= lo:
        hi = lo + 1.0
    return (a - lo) / (hi - lo)


def ensure_gray(x):
    a = np.asarray(x, np.float64)
    if a.ndim == 3 and a.shape[-1] == 3:
        return a @ np.array([0.299, 0.587, 0.114])
    return a


def ensure_color(x):
    a = np.asarray(x, np.float64)
    if a.ndim == 2:
        return np.repeat(a[:, :, None], 3, axis=2)
    return a


# ---- colormaps (numpy-only) ------------------------------------------------ #
def _lut(t, ctrl):
    ctrl = np.asarray(ctrl, np.float64)
    k = len(ctrl)
    pos = np.clip(t, 0, 1) * (k - 1)
    i0 = np.clip(np.floor(pos).astype(int), 0, k - 1)
    i1 = np.clip(i0 + 1, 0, k - 1)
    f = (pos - i0)[..., None]
    return ctrl[i0] * (1 - f) + ctrl[i1] * f


def _jet(t):
    t = np.clip(t, 0, 1)
    r = np.clip(1.5 - np.abs(4 * t - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * t - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * t - 1), 0, 1)
    return np.stack([r, g, b], axis=-1)


def _hsv(t):
    h = np.clip(t, 0, 1) * 6.0
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    v = np.ones_like(t); p = np.zeros_like(t); q = 1 - f
    cond = [i == 0, i == 1, i == 2, i == 3, i == 4, i == 5]
    r = np.select(cond, [v, q, p, p, f, v])
    g = np.select(cond, [f, v, v, q, p, p])
    b = np.select(cond, [p, p, f, v, v, q])
    return np.stack([r, g, b], axis=-1)


_LUTS["bone"] = [[0.0, 0.0, 0.0], [0.33, 0.33, 0.46], [0.66, 0.78, 0.78], [1.0, 1.0, 1.0]]

_ANALYTIC = {
    "gray": lambda t: np.repeat(t[..., None], 3, axis=-1),
    "jet": _jet,
    "hot": lambda t: np.stack([np.clip(3 * t, 0, 1), np.clip(3 * t - 1, 0, 1),
                               np.clip(3 * t - 2, 0, 1)], axis=-1),
    "cool": lambda t: np.stack([t, 1 - t, np.ones_like(t)], axis=-1),
    "spring": lambda t: np.stack([np.ones_like(t), t, 1 - t], axis=-1),
    "hsv": _hsv,
}


def apply_cmap(x, name: str = "viridis", vmin=None, vmax=None, invalid=(0, 0, 0)):
    """Map a scalar field to an (H, W, 3) RGB image in [0, 1] using a false-colour
    palette (see ``COLORMAPS``).

    Values are normalised over [vmin, vmax] (auto from finite data if None).
    Non-finite cells (e.g. ``inf`` in a depth map) are painted *invalid*.
    """
    a = np.asarray(x, np.float64)
    fin = np.isfinite(a)
    t = normalize(np.where(fin, a, 0.0), vmin, vmax)
    if name in _ANALYTIC:
        rgb = _ANALYTIC[name](t)
    elif name in _LUTS:
        rgb = _lut(t, _LUTS[name])
    else:
        raise ValueError("unknown colormap %r (have %s)" % (name, COLORMAPS))
    rgb = np.clip(rgb, 0, 1).copy()
    rgb[~fin] = np.asarray(invalid, np.float64)
    return rgb


def colorize_depth(depth, name="viridis"):
    """Colourise a depth map; ``inf``/unknown -> black."""
    return apply_cmap(depth, name=name)


def colorize_disparity(disp, name="jet"):
    return apply_cmap(disp, name=name)


def shaded_relief(heightmap, azimuth: float = 315.0, altitude: float = 45.0, z: float = 1.0):
    """Hillshade of a height map -> gray [0,1] shaded surface (a pseudo-3-D view of
    a height/depth image). *azimuth*/*altitude* are the light direction in degrees."""
    h = np.asarray(heightmap, np.float64)
    if not np.isfinite(h).all():
        fill = float(np.nanmin(h[np.isfinite(h)])) if np.isfinite(h).any() else 0.0
        h = np.where(np.isfinite(h), h, fill)
    gy, gx = np.gradient(h * float(z))
    slope = np.pi / 2 - np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az = np.deg2rad(360.0 - azimuth + 90.0)
    alt = np.deg2rad(altitude)
    shade = (np.sin(alt) * np.sin(slope)
             + np.cos(alt) * np.cos(slope) * np.cos(az - aspect))
    return np.clip(shade, 0, 1)


def colorize_height(heightmap, name="terrain", relief=True, azimuth=315.0, altitude=45.0):
    """False-colour a height map and (optionally) modulate it by hillshade so the
    surface reads as 2.5-D. Returns an (H, W, 3) RGB image."""
    rgb = apply_cmap(heightmap, name=name)
    if relief:
        sh = shaded_relief(heightmap, azimuth, altitude)[..., None]
        rgb = np.clip(rgb * (0.4 + 0.6 * sh), 0, 1)
    return rgb


def colorize_labels(labels, seed: int = 0):
    """Distinct random colour per positive label; label 0 (background) -> black."""
    lab = np.asarray(labels).astype(int)
    n = int(lab.max())
    rng = np.random.default_rng(seed)
    cols = rng.random((n + 1, 3))
    cols[0] = 0.0
    return cols[np.clip(lab, 0, n)]


def overlay_mask(image, mask, color=(1.0, 0.0, 0.0), alpha: float = 0.5):
    """Blend *color* onto *image* where *mask* is set (mask > 0.5)."""
    img = ensure_color(image).copy()
    m = np.asarray(mask) > 0.5
    col = np.asarray(color, np.float64)
    img[m] = (1 - alpha) * img[m] + alpha * col
    return np.clip(img, 0, 1)


# ---- file save / load ------------------------------------------------------ #
def _cv2():
    try:
        import cv2
        return cv2
    except Exception:
        return None


def save(path: str, arr) -> None:
    """Save an image/region/color array (or a colourised scalar field) to *path*.

    2-D arrays already in [0, 1] save as grayscale; 3-D (H,W,3) save as RGB; a
    2-D array with values outside [0, 1] is colourised (viridis) first.
    """
    a = np.asarray(arr, np.float64)
    if a.ndim == 2 and (a.min() < -1e-9 or a.max() > 1 + 1e-9 or not np.isfinite(a).all()):
        a = apply_cmap(a)
    u8 = to_uint8(a)
    cv2 = _cv2()
    if cv2 is not None:
        bgr = u8[:, :, ::-1] if u8.ndim == 3 else u8
        cv2.imwrite(path, bgr)
        return
    try:
        from PIL import Image
        Image.fromarray(u8).save(path)
    except Exception as e:  # pragma: no cover
        raise RuntimeError("save needs opencv-python or Pillow: %s" % e)


def load(path: str, color: bool = False):
    """Load *path* as float64 [0, 1] (grayscale by default)."""
    cv2 = _cv2()
    if cv2 is not None:
        flag = cv2.IMREAD_COLOR if color else cv2.IMREAD_GRAYSCALE
        im = cv2.imread(path, flag)
        if im is None:
            raise FileNotFoundError(path)
        if color:
            im = im[:, :, ::-1]
        return im.astype(np.float64) / 255.0
    try:
        from PIL import Image
        im = Image.open(path)
        im = im.convert("RGB") if color else im.convert("L")
        return np.asarray(im, np.float64) / 255.0
    except Exception as e:  # pragma: no cover
        raise RuntimeError("load needs opencv-python or Pillow: %s" % e)


def save_ply(path: str, points, colors=None) -> None:
    """Write an ASCII PLY point cloud. *points* (N,3); *colors* optional (N,3) in [0,1]."""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    n = len(P)
    lines = ["ply", "format ascii 1.0", "element vertex %d" % n,
             "property float x", "property float y", "property float z"]
    C = None
    if colors is not None:
        C = np.clip(np.asarray(colors, np.float64) * 255, 0, 255).astype(int)
        lines += ["property uchar red", "property uchar green", "property uchar blue"]
    lines.append("end_header")
    body = []
    for i in range(n):
        if C is not None:
            body.append("%g %g %g %d %d %d" % (P[i, 0], P[i, 1], P[i, 2],
                                               C[i, 0], C[i, 1], C[i, 2]))
        else:
            body.append("%g %g %g" % (P[i, 0], P[i, 1], P[i, 2]))
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(lines + body) + "\n")
