"""Qt-free display-range handling for the Studio image viewer."""

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

import imgio


_MODES = {"auto_each", "shared", "manual"}
_COLORMAPS = {"gray", "viridis"}


@dataclass(frozen=True)
class DisplayRange:
    mode: str = "auto_each"
    lo: float | None = None
    hi: float | None = None
    percentile: tuple[float, float] | None = None
    colormap: str = "gray"
    constant: bool = False


@dataclass(frozen=True)
class DisplayInfo:
    nan_count: int
    inf_count: int
    under_count: int
    over_count: int
    lo: float
    hi: float
    colormap: str
    note: str

    @property
    def warning(self):
        parts = []
        outside = self.under_count + self.over_count
        if outside:
            parts.append("レンジ外 {:,} 画素(下 {:,} / 上 {:,})".format(
                outside, self.under_count, self.over_count))
        if self.nan_count or self.inf_count:
            parts.append("NaN {:,} / Inf {:,} 画素".format(self.nan_count, self.inf_count))
        return " / ".join(parts)


def _validate(rng):
    if not isinstance(rng, DisplayRange):
        raise ValueError("display range must be a DisplayRange")
    if rng.mode not in _MODES:
        raise ValueError("unknown display range mode: %r" % rng.mode)
    if rng.colormap not in _COLORMAPS:
        raise ValueError("unknown colormap: %r" % rng.colormap)
    if rng.percentile is not None:
        try:
            p_lo, p_hi = map(float, rng.percentile)
        except (TypeError, ValueError):
            raise ValueError("invalid percentile: %r" % (rng.percentile,)) from None
        if not (np.isfinite(p_lo) and np.isfinite(p_hi) and 0 <= p_lo < p_hi <= 100):
            raise ValueError("invalid percentile: %r" % (rng.percentile,))
    return rng


def _finite_range(images, percentile):
    finite = [np.asarray(image).ravel() for image in images]
    finite = [values[np.isfinite(values)] for values in finite]
    finite = [values for values in finite if values.size]
    if not finite:
        return 0.0, 0.0
    values = np.concatenate(finite)
    if percentile is None:
        return float(np.min(values)), float(np.max(values))
    lo, hi = np.percentile(values, percentile)
    return float(lo), float(hi)


def resolve_range(images, rng):
    """Resolve automatic ranges; ``auto_each`` returns one range per image."""
    rng = _validate(rng)
    arrays = [np.asarray(image) for image in images]
    if rng.mode == "manual":
        if rng.lo is None or rng.hi is None or not np.isfinite(rng.lo) or not np.isfinite(rng.hi):
            raise ValueError("manual range lo and hi must be finite")
        if rng.lo >= rng.hi:
            raise ValueError("manual range requires lo < hi")
        return replace(rng, lo=float(rng.lo), hi=float(rng.hi), constant=False)
    if not arrays:
        raise ValueError("images must not be empty")
    if rng.mode == "auto_each":
        answer = []
        for image in arrays:
            lo, hi = _finite_range([image], rng.percentile)
            answer.append(replace(rng, lo=lo, hi=hi, constant=lo == hi))
        return answer
    lo, hi = _finite_range(arrays, rng.percentile)
    return replace(rng, lo=lo, hi=hi, constant=lo == hi)


def _viridis_table():
    # Compact polynomial approximation by Simon Garnier, distributed under CC0.
    x = np.linspace(0.0, 1.0, 256)
    stops = np.array([[68, 1, 84], [59, 82, 139], [33, 145, 140],
                      [94, 201, 98], [253, 231, 37]], dtype=float)
    pos = x * (len(stops) - 1)
    left = np.minimum(pos.astype(int), len(stops) - 2)
    frac = (pos - left)[:, None]
    return np.rint(stops[left] * (1 - frac) + stops[left + 1] * frac).astype(np.uint8)


_VIRIDIS = _viridis_table()


def to_display(img, rng):
    """Map a scalar array to RGB without changing the source array."""
    info = range_info(img, rng)
    rng = replace(_validate(rng), lo=info.lo, hi=info.hi)
    arr = np.asarray(img)
    finite = np.isfinite(arr)
    if rng.hi == rng.lo:
        indices = np.full(arr.shape, 128, dtype=np.uint8)
    else:
        safe = np.where(finite, arr, rng.lo)
        scaled = np.clip((safe - rng.lo) / (rng.hi - rng.lo), 0, 1)
        indices = np.minimum(np.rint(scaled * 256), 255).astype(np.uint8)
    if rng.colormap == "gray":
        rgb = np.repeat(indices[..., None], 3, axis=2)
    else:
        rgb = _VIRIDIS[indices]
    rgb = np.array(rgb, copy=True)
    return mark_nonfinite(rgb, arr), info


def range_info(img, rng):
    """Return range/count metadata for a 2-D scalar array without rendering it."""
    rng = _validate(rng)
    if rng.lo is None or rng.hi is None:
        resolved = resolve_range([img], rng)
        rng = resolved[0] if isinstance(resolved, list) else resolved
    arr = np.asarray(img)
    if arr.ndim != 2:
        raise ValueError("display image must be a 2-D array")
    finite = np.isfinite(arr)
    nan = np.isnan(arr)
    inf = np.isinf(arr)
    under = finite & (arr < rng.lo)
    over = finite & (arr > rng.hi)
    return DisplayInfo(int(nan.sum()), int(inf.sum()), int(under.sum()), int(over.sum()),
                       float(rng.lo), float(rng.hi), rng.colormap,
                       "表示処理のみ: %s、元データは変更していません" % rng.colormap)


def mark_nonfinite(rgb_uint8, img):
    """Paint non-finite source pixels magenta in an RGB uint8 rendering, in place."""
    rgb = np.asarray(rgb_uint8)
    arr = np.asarray(img)
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("display rendering must be an (H, W, 3) uint8 array")
    if arr.ndim != 2 or rgb.shape[:2] != arr.shape:
        raise ValueError("display rendering and source image shapes must match")
    rgb[~np.isfinite(arr)] = (255, 0, 255)
    return rgb


def pixel_readout(img, rng, y, x):
    """Return original and display values at an array coordinate."""
    arr = np.asarray(img)
    if not (0 <= y < arr.shape[0] and 0 <= x < arr.shape[1]):
        return None
    rng = _validate(rng)
    if rng.lo is None or rng.hi is None:
        resolved = resolve_range([arr], rng)
        rng = resolved[0] if isinstance(resolved, list) else resolved
    value = arr[y, x]
    if np.isnan(value):
        original, shown = "NaN", None
    elif np.isinf(value):
        original, shown = float(value), None
    else:
        original = value.item()
        shown = (128 if rng.hi == rng.lo else min(int(np.rint(np.clip(
            (float(value) - rng.lo) / (rng.hi - rng.lo), 0, 1) * 256)), 255))
    return {"value": original, "display_value": shown, "lo": float(rng.lo),
            "hi": float(rng.hi), "dtype": str(arr.dtype),
            "note": "表示値は表示処理後の値で、元データではありません"}


def save_outputs(img, rng, path_stem, what, *, display_rgb=None, overwrite=False):
    """Save exact numeric data, its current RGB rendering, or both."""
    if what not in {"raw", "display", "both"}:
        raise ValueError("unknown save choice: %r" % what)
    stem = Path(path_stem)
    paths = []
    if what in {"raw", "both"}:
        paths.append(stem.with_suffix(".npy"))
    if what in {"display", "both"}:
        paths.append(stem.with_suffix(".png"))
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        raise ValueError("output already exists: %s" % existing[0])
    stem.parent.mkdir(parents=True, exist_ok=True)
    if what in {"raw", "both"}:
        np.save(paths[0], np.asarray(img), allow_pickle=False)
    if what in {"display", "both"}:
        display_path = paths[-1]
        if display_rgb is None:
            rgb, _ = to_display(img, rng)
        else:
            rgb = np.asarray(display_rgb)
        imgio.save(str(display_path), rgb)
    return paths
