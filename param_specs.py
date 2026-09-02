"""Per-operator knob PRESENTATION specs for Fullseye Studio (additive, optional).

Every 2-D op takes two knobs ``a, b`` in [0, 1]; the op maps each knob to its real
parameter internally (``gaussian``: ``sigma = 0.3 + 2.7*a``; ``median``: kernel
``(3, 5, 7, 9)[min(3, int(a*4))]``; ``reg_erode``: ``iterations = 1 + int(a*3)``).
The registry carries no metadata about those mappings, so a UI can only offer the
same two anonymous 0..1 sliders for every op.

This module is the missing metadata layer. A spec describes how a knob is SHOWN
(label, displayed range / unit, integer snapping, choice names) — the value that
reaches the op stays the 0..1 float, so nothing else in the system changes.

Spec dict keys::

    label    str    short name of the parameter ("blur σ")
    kind     "float" | "int" | "choice" | "bool" | "unused"
    min/max  displayed range (float / int kinds)
    step     display step (float); decimals are derived from it
    choices  list of display names (choice kind)
    unit     str | None  ("px", "°", "×", "cyc/px" …)
    map      how the 0..1 knob maps to the display value:
               "linear"  d = min + knob*(max-min)                (float; int -> round)
               "log"     d = min * (max/min)**knob               (float)
               "floor"   d = min + int(knob*(max-min))           (int: op uses int(a*N))
               "bucket"  i = min(n-1, int(knob*n))               (choice / int: equal buckets)
    true_if  ">=0.5" | ">0.5"  (bool kind: which comparison the op source uses)
    doc      one-line explanation (unit / meaning)
    source   the op-source expression the spec was transcribed from (provenance)

Two tables feed :func:`spec_for`:

* :data:`PARAM_SPECS` — HAND-WRITTEN from the op source (``ops.py`` and a few
  backends). Each entry names the source formula; ``tests/test_studio_params.py``
  re-derives the op's own mapping (importing the private helpers ``ops._k`` /
  ``ops._it`` and the literal formulas) and asserts :func:`knob_to_display`
  reproduces it, so the table cannot silently drift from the implementation.
* :func:`seed_from_docs` — LABEL-ONLY seeds mined from op docstrings and the per-op
  notes under ``docs/ops/**/<op>.md``. A seeded spec keeps the generic 0..1 float
  presentation and only contributes the label/doc text (an honest "what does a do"
  without inventing a range). At the time of writing the generated per-op notes
  carry no "Parameters" section, so in practice the docstrings are the source.
"""
from __future__ import annotations

import functools
import math
import os
import re
from typing import Any, Optional

# --------------------------------------------------------------------------- #
# generic / unused
# --------------------------------------------------------------------------- #
GENERIC_FLOAT: dict[str, Any] = {
    "label": "", "kind": "float", "min": 0.0, "max": 1.0, "step": 0.001,
    "choices": None, "unit": None, "map": "linear", "doc": "raw knob (0..1)",
    "source": None,
}
UNUSED: dict[str, Any] = {
    "label": "(unused)", "kind": "unused", "min": 0.0, "max": 1.0, "step": 0.001,
    "choices": None, "unit": None, "map": "linear",
    "doc": "this op does not read this knob", "source": None,
}


def _spec(label, kind="float", lo=0.0, hi=1.0, step=0.01, unit=None, map_="linear",
          choices=None, doc="", source=None, true_if=">=0.5"):
    """Build a complete spec dict (every key present, so consumers need no .get())."""
    d = {"label": label, "kind": kind, "min": lo, "max": hi, "step": step,
         "choices": list(choices) if choices else None, "unit": unit, "map": map_,
         "doc": doc, "source": source}
    if kind == "bool":
        d["true_if"] = true_if
    if kind == "choice":
        d["min"], d["max"] = 0, len(d["choices"]) - 1
        d["map"] = "bucket"
    return d


def _lin(label, lo, hi, step=0.01, unit=None, doc="", source=None):
    return _spec(label, "float", float(lo), float(hi), step, unit, "linear", doc=doc, source=source)


def _int_floor(label, lo, hi, unit=None, doc="", source=None):
    # op source: lo + int(knob * (hi - lo))  — the top value only at knob == 1.0
    return _spec(label, "int", int(lo), int(hi), 1, unit, "floor", doc=doc, source=source)


def _kernel(doc="odd kernel size (3, 5, 7 or 9 px) — ops._k(a)"):
    # ops._k(a) = (3, 5, 7, 9)[min(3, int(a * 4))]: four equal-width buckets
    return _spec("kernel", "choice", choices=["3", "5", "7", "9"], unit="px", doc=doc,
                 source="(3, 5, 7, 9)[min(3, int(a * 4))]")


def _iters(doc="morphology iterations 1..4 — ops._it(a)"):
    # ops._it(a) = 1 + int(a * 3)
    return _int_floor("iterations", 1, 4, doc=doc, source="1 + int(a * 3)")


_SIGMA = "σ"
_DEG = "°"

# --------------------------------------------------------------------------- #
# HAND-WRITTEN specs (each verified against the op source; see the tests)
# --------------------------------------------------------------------------- #
PARAM_SPECS: dict[str, dict[str, dict[str, Any]]] = {
    # ---- smoothing / rank / grey morphology (ops.py) ----
    "gaussian": {"a": _lin("blur " + _SIGMA, 0.3, 3.0, 0.01, "px",
                           "Gaussian σ = 0.3 + 2.7·a", "0.3 + 2.7 * a"),
                 "b": UNUSED},
    "mean_box": {"a": _kernel("box (uniform) filter size"), "b": UNUSED},
    "median": {"a": _kernel("median filter size"), "b": UNUSED},
    "min_filter": {"a": _kernel("minimum filter size"), "b": UNUSED},
    "max_filter": {"a": _kernel("maximum filter size"), "b": UNUSED},
    "percentile": {"a": _kernel("percentile filter size"),
                   "b": _int_floor("percentile", 5, 95, "%", "rank percentile 5..95",
                                   "int(5 + 90 * b)")},
    "gerode": {"a": _kernel("grey erosion size"), "b": UNUSED},
    "gdilate": {"a": _kernel("grey dilation size"), "b": UNUSED},
    "gopen": {"a": _kernel("grey opening size"), "b": UNUSED},
    "gclose": {"a": _kernel("grey closing size"), "b": UNUSED},
    "tophat": {"a": _kernel("white top-hat size"), "b": UNUSED},
    "bothat": {"a": _kernel("black top-hat size"), "b": UNUSED},
    "morph_grad": {"a": _kernel("morphological gradient size"), "b": UNUSED},
    "std_filter": {"a": _kernel("local std-dev window"), "b": UNUSED},
    "bilateral": {"a": _lin("spatial " + _SIGMA, 1.0, 4.0, 0.01, "px",
                            "spatial σ = 1 + 3·a", "1.0 + 3.0 * a"),
                  "b": _lin("range " + _SIGMA, 0.05, 0.45, 0.001, None,
                            "range (intensity) σ = 0.05 + 0.4·b", "0.05 + 0.4 * b")},
    "unsharp": {"a": _lin("amount", 0.0, 1.5, 0.01, "×", "sharpen gain k = 1.5·a", "1.5 * a"),
                "b": _lin("radius " + _SIGMA, 0.5, 2.0, 0.01, "px",
                          "blur σ of the mask = 0.5 + 1.5·b", "0.5 + 1.5 * b")},
    # ---- edges ----
    "sobel_mag": {"a": UNUSED, "b": UNUSED},
    "laplace": {"a": UNUSED, "b": UNUSED},
    "prewitt_mag": {"a": UNUSED, "b": UNUSED},
    "roberts_mag": {"a": UNUSED, "b": UNUSED},
    "grad_dir": {"a": UNUSED, "b": UNUSED},
    "dog": {"a": _lin(_SIGMA + "1 (fine)", 0.5, 2.5, 0.01, "px", "inner σ = 0.5 + 2·a", "0.5 + 2.0 * a"),
            "b": _lin(_SIGMA + "2 (coarse)", 1.0, 5.0, 0.01, "px", "outer σ = 1 + 4·b", "1.0 + 4.0 * b")},
    "log": {"a": _lin(_SIGMA, 0.5, 3.0, 0.01, "px", "Laplacian-of-Gaussian σ = 0.5 + 2.5·a",
                      "0.5 + 2.5 * a"), "b": UNUSED},
    "corner_response": {"a": _lin("window " + _SIGMA, 0.5, 2.5, 0.01, "px",
                                  "Harris integration σ = 0.5 + 2·a", "0.5 + 2.0 * a"),
                        "b": UNUSED},
    # ---- grey-value transforms ----
    "gamma": {"a": _lin("gamma", 0.5, 2.0, 0.01, None, "γ = 0.5 + 1.5·a (γ<1 brightens)",
                        "0.5 + 1.5 * a"), "b": UNUSED},
    "invert": {"a": UNUSED, "b": UNUSED},
    "scale_clip": {"a": _lin("contrast", 0.5, 2.0, 0.01, "×", "gain = 0.5 + 1.5·a", "0.5 + 1.5 * a"),
                   "b": _lin("brightness", -0.5, 0.5, 0.01, None, "offset = b − 0.5", "b - 0.5")},
    "equalize": {"a": UNUSED, "b": UNUSED},
    "sigmoid": {"a": _lin("gain", 4.0, 16.0, 0.1, None, "slope = 4 + 12·a", "4.0 + 12.0 * a"),
                "b": _lin("centre", 0.2, 0.8, 0.01, None, "midpoint = 0.2 + 0.6·b", "0.2 + 0.6 * b")},
    "lowpass": {"a": _lin("cutoff", 0.05, 0.45, 0.001, "cyc/px", "FFT cutoff = 0.05 + 0.4·a",
                          "0.05 + 0.4 * a"), "b": UNUSED},
    "highpass": {"a": _lin("cutoff", 0.02, 0.32, 0.001, "cyc/px", "FFT cutoff = 0.02 + 0.3·a",
                           "0.02 + 0.3 * a"), "b": UNUSED},
    "clahe": {"a": _int_floor("tiles", 2, 5, "×", "tile grid nb×nb, nb = 2 + int(3·a)", "2 + int(a * 3)"),
              "b": _spec("clip limit", "float", 1.0, 256.0, 0.5, "×", "log",
                         doc="clip limit as a multiple of the mean bin count = 256^b "
                             "(1 = flat, 256 = plain AHE)", source="256.0 ** b")},
    "gabor": {"a": _lin("orientation", 0.0, 180.0, 0.5, _DEG, "θ = π·a (rad) = 180°·a", "180.0 * a"),
              "b": _lin("frequency", 0.1, 0.4, 0.001, "cyc/px", "f = 0.1 + 0.3·b", "0.1 + 0.3 * b")},
    # ---- segmentation ----
    "threshold": {"a": _lin("level", 0.0, 1.0, 0.001, None, "keep v > a", "a"), "b": UNUSED},
    "otsu": {"a": UNUSED, "b": UNUSED},
    "dyn_threshold": {"a": _kernel("local-mean window"),
                      "b": _lin("offset", -0.2, 0.2, 0.001, None, "v > mean + (b−0.5)·0.4",
                                "(b - 0.5) * 0.4")},
    "adaptive_gauss_thresh": {"a": _lin("local " + _SIGMA, 1.0, 4.0, 0.01, "px",
                                        "Gaussian window σ = 1 + 3·a", "1.0 + 3.0 * a"),
                              "b": _lin("offset", -0.15, 0.15, 0.001, None,
                                        "v > blur + (b−0.5)·0.3", "(b - 0.5) * 0.3")},
    "canny": {"a": _lin("smooth " + _SIGMA, 0.5, 2.0, 0.01, "px", "pre-blur σ = 0.5 + 1.5·a",
                        "0.5 + 1.5 * a"),
              "b": _lin("edge threshold", 0.1, 0.6, 0.001, None, "gradient > 0.1 + 0.5·b",
                        "0.1 + 0.5 * b")},
    "local_max": {"a": _kernel("maximum-filter window"),
                  "b": _lin("min value", 0.3, 0.7, 0.001, None, "peak must exceed 0.3 + 0.4·b",
                            "0.3 + 0.4 * b")},
    "edges_sub_pix": {"a": _lin("gradient threshold", 0.15, 0.65, 0.001, None,
                                "edge band = gradient > 0.15 + 0.5·a", "0.15 + 0.5 * a"),
                      "b": UNUSED},
    "decode_barcode": {"a": _lin("dark level", 0.3, 0.7, 0.001, None, "bar = v < 0.3 + 0.4·a",
                                 "0.3 + 0.4 * a"), "b": UNUSED},
    # ---- binary region morphology ----
    "reg_erode": {"a": _iters("binary erosion iterations"), "b": UNUSED},
    "reg_dilate": {"a": _iters("binary dilation iterations"), "b": UNUSED},
    "reg_open": {"a": _iters("binary opening iterations"), "b": UNUSED},
    "reg_close": {"a": _iters("binary closing iterations"), "b": UNUSED},
    "convex_fill": {"a": _int_floor("iterations", 3, 6, doc="closing iterations = _it(a) + 2",
                                    source="1 + int(a * 3) + 2"), "b": UNUSED},
    "fill_holes": {"a": UNUSED, "b": UNUSED},
    "select_largest": {"a": UNUSED, "b": UNUSED},
    "remove_small": {"a": _lin("min area", 0.01, 0.16, 0.001, "of image",
                               "keep components ≥ (0.01 + 0.15·a)·pixels", "0.01 + 0.15 * a"),
                     "b": UNUSED},
    "invert_region": {"a": UNUSED, "b": UNUSED},
    "dist_transform": {"a": UNUSED, "b": UNUSED},
    "region_boundary": {"a": UNUSED, "b": UNUSED},
    "blob_count": {"a": UNUSED, "b": UNUSED},
    "area_frac": {"a": UNUSED, "b": UNUSED},
    "classify_shape": {"a": UNUSED, "b": UNUSED},
    # ---- contours ----
    "select_contours": {"a": _int_floor("min points", 3, 43, "pts", "keep contours with ≥ 3 + int(40·a) points",
                                        "3 + int(a * 40)"), "b": UNUSED},
    "smooth_contours": {"a": _int_floor("half-width", 1, 4, "pts", "moving-average half-width 1 + int(3·a)",
                                        "1 + int(a * 3)"), "b": UNUSED},
    "contours_to_region": {"a": _int_floor("dilation", 1, 3, "px", "rasterised contour dilated 1 + int(2·a)",
                                           "1 + int(a * 2)"), "b": UNUSED},
    "fit_line_contours": {"a": UNUSED, "b": UNUSED},
    "count_contours": {"a": UNUSED, "b": UNUSED},
    "total_length": {"a": UNUSED, "b": UNUSED},
    # ---- geometry ----
    "rotate_img": {"a": _lin("angle", -45.0, 45.0, 0.5, _DEG, "rotation = −45° + 90°·a (a=0.5 → 0°)",
                             "-45 + 90 * a"), "b": UNUSED},
    "rescale_img": {"a": _lin("scale", 0.7, 1.3, 0.01, "×", "isotropic factor s = 0.7 + 0.6·a",
                              "0.7 + 0.6 * a"),
                    "b": _spec("interpolation", "choice",
                               choices=["nearest (0)", "bilinear (1)", "cubic (3)", "cubic (3)"],
                               doc="spline order (0, 1, 3, 3)[min(3, int(4·b))]",
                               source="(0, 1, 3, 3)[min(3, int(b * 4))]")},
    "affine_warp": {"a": _lin("angle", -20.0, 20.0, 0.5, _DEG, "rotation = −20° + 40°·a", "-20 + 40 * a"),
                    "b": _lin("shear", -0.2, 0.2, 0.001, None, "shear = (b − 0.5)·0.4", "(b - 0.5) * 0.4")},
    # ---- misc / matching ----
    "identity": {"a": UNUSED, "b": UNUSED},
    "ncc_locate": {"a": UNUSED, "b": UNUSED},
    "shape_locate": {"a": UNUSED, "b": UNUSED},
    # ---- volumes ----
    "vol_gaussian": {"a": _lin("blur " + _SIGMA, 0.3, 3.0, 0.01, "vx", "σ = 0.3 + 2.7·a", "0.3 + 2.7 * a"),
                     "b": UNUSED},
    "vol_median": {"a": UNUSED, "b": UNUSED},
    "vol_threshold": {"a": _lin("level", 0.0, 1.0, 0.001, None, "keep v > a", "a"), "b": UNUSED},
    "vol_reg_dilate": {"a": _int_floor("iterations", 1, 4, doc="6-neighbour dilation iterations",
                                       source="max(1, 1 + int(a * 3))"), "b": UNUSED},
    "vol_reg_erode": {"a": _int_floor("iterations", 1, 4, doc="6-neighbour erosion iterations",
                                      source="max(1, 1 + int(a * 3))"), "b": UNUSED},
    "vol_dilation_ball": {"a": _int_floor("radius", 1, 4, "vx", "ball radius 1 + int(3·a)", "1 + int(a * 3)"),
                          "b": UNUSED},
    "vol_erosion_ball": {"a": _int_floor("radius", 1, 4, "vx", "ball radius 1 + int(3·a)", "1 + int(a * 3)"),
                         "b": UNUSED},
    "vol_opening_ball": {"a": _int_floor("radius", 1, 4, "vx", "ball radius 1 + int(3·a)", "1 + int(a * 3)"),
                         "b": UNUSED},
    "vol_mip": {"a": UNUSED, "b": UNUSED},
    "vol_count": {"a": UNUSED, "b": UNUSED},
    # ---- bool knobs (backends) ----
    "aug_barrel": {"a": _lin("distortion k", 0.0, 0.6, 0.001, None, "|k| = 0.6·a (0 = none)", "0.6 * a"),
                   "b": _spec("pincushion", "bool", doc="off = barrel (b < 0.5), on = pincushion (b ≥ 0.5)",
                              source="1.0 if b < 0.5 else -1.0", true_if=">=0.5")},
    "aug_rolling_shutter": {"a": _lin("peak shift", 0.0, 0.25, 0.001, "×W", "max row shift = 0.25·W·a",
                                      "0.25 * a"),
                            "b": _spec("pan left", "bool", doc="off = shift right (b < 0.5), on = left",
                                       source="1.0 if b < 0.5 else -1.0", true_if=">=0.5")},
    "tm_fbp_reconstruct": {"a": UNUSED,
                           "b": _spec("Shepp-Logan filter", "bool",
                                      doc="off = Ram-Lak ramp (b < 0.5), on = Shepp-Logan (b ≥ 0.5)",
                                      source='"ramp" if b < 0.5 else "shepp-logan"', true_if=">=0.5")},
    "sg_region_growing_seeded": {"a": _lin("tolerance", 0.0, 1.0, 0.001, None, "|v − seed| ≤ a", "a"),
                                 "b": _spec("8-connected", "bool", doc="off = 4-connected, on = 8 (b > 0.5)",
                                            source="2 if b > 0.5 else 1", true_if=">0.5")},
}


def hand_written_ops() -> list[str]:
    """Names of ops with a hand-written (source-verified) spec."""
    return sorted(PARAM_SPECS)


# --------------------------------------------------------------------------- #
# mapping helpers (pure functions; round-trip tested)
# --------------------------------------------------------------------------- #
def _clamp01(x) -> float:
    x = float(x)
    if not math.isfinite(x):
        return 0.0
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def decimals_for(step) -> int:
    """Display decimals implied by a step (0.01 -> 2, 0.5 -> 1, 1 -> 0)."""
    try:
        s = float(step)
    except (TypeError, ValueError):
        return 3
    if s <= 0 or not math.isfinite(s):
        return 3
    d = 0
    while d < 6 and abs(round(s * 10 ** d) - s * 10 ** d) > 1e-9:
        d += 1
    return d


def knob_to_display(spec: dict, knob: float):
    """Map a 0..1 knob to the value the user sees (float / int / choice index / bool).

    Reproduces the op's own mapping for hand-written specs (asserted by the tests):
    ``"floor"`` ints are ``min + int(knob*(max-min))`` exactly as ``1 + int(a*3)``;
    ``"bucket"`` choices are ``min(n-1, int(knob*n))`` exactly as ``ops._k``."""
    k = _clamp01(knob)
    kind = spec.get("kind", "float")
    lo, hi = spec.get("min", 0.0), spec.get("max", 1.0)
    m = spec.get("map", "linear")
    if kind == "bool":
        return (k > 0.5) if spec.get("true_if") == ">0.5" else (k >= 0.5)
    if kind == "choice":
        n = len(spec.get("choices") or [])
        if n == 0:
            return 0
        return min(n - 1, int(k * n))
    if kind == "int":
        lo, hi = int(lo), int(hi)
        if m == "floor":
            return lo + int(k * (hi - lo))
        if m == "bucket":
            n = hi - lo + 1
            return lo + min(n - 1, int(k * n))
        return lo + int(round(k * (hi - lo)))
    # float / unused
    lo, hi = float(lo), float(hi)
    if m == "log" and lo > 0 and hi > 0:
        return lo * (hi / lo) ** k
    return lo + k * (hi - lo)


def display_to_knob(spec: dict, shown) -> float:
    """Inverse of :func:`knob_to_display`: the 0..1 knob that shows as *shown*.

    For quantised kinds (int floor / bucket, choice) the knob returned is the CENTRE
    of the interval that displays as *shown* (and exactly 1.0 for the floor-map top
    value, which the op only reaches at ``a == 1``), so
    ``knob_to_display(spec, display_to_knob(spec, d)) == d`` always holds."""
    kind = spec.get("kind", "float")
    lo, hi = spec.get("min", 0.0), spec.get("max", 1.0)
    m = spec.get("map", "linear")
    if kind == "bool":
        return 1.0 if bool(shown) else 0.0
    if kind == "choice":
        n = len(spec.get("choices") or [])
        if n <= 1:
            return 0.0
        i = min(n - 1, max(0, int(shown)))
        return _clamp01((i + 0.5) / n)
    if kind == "int":
        lo, hi = int(lo), int(hi)
        d = min(hi, max(lo, int(round(float(shown)))))
        if hi == lo:
            return 0.0
        if m == "floor":
            n = hi - lo
            return 1.0 if d == hi else _clamp01((d - lo + 0.5) / n)
        if m == "bucket":
            n = hi - lo + 1
            return _clamp01((d - lo + 0.5) / n)
        return _clamp01((d - lo) / (hi - lo))
    lo, hi = float(lo), float(hi)
    v = float(shown)
    if not math.isfinite(v):
        return 0.0
    v = min(max(v, min(lo, hi)), max(lo, hi))
    if hi == lo:
        return 0.0
    if m == "log" and lo > 0 and hi > 0:
        return _clamp01(math.log(v / lo) / math.log(hi / lo))
    return _clamp01((v - lo) / (hi - lo))


def format_display(spec: dict, knob: float) -> str:
    """Human string of the displayed value, rounded to the spec's step, with unit."""
    kind = spec.get("kind", "float")
    unit = spec.get("unit") or ""
    d = knob_to_display(spec, knob)
    if kind == "unused":
        return "–"
    if kind == "bool":
        return "on" if d else "off"
    if kind == "choice":
        ch = spec.get("choices") or []
        s = ch[d] if 0 <= d < len(ch) else str(d)
        return (s + " " + unit).strip()
    if kind == "int":
        return ("%d %s" % (d, unit)).strip()
    dec = decimals_for(spec.get("step", 0.001))
    return ("%.*f %s" % (dec, d, unit)).strip()


def spec_label(spec: dict, letter: str) -> str:
    """'a · blur σ' / 'a (–)' / 'a' for a knob letter and its spec."""
    lab = spec.get("label") or ""
    if spec.get("kind") == "unused":
        return "%s (–)" % letter
    return "%s · %s" % (letter, lab) if lab else letter


# --------------------------------------------------------------------------- #
# docs / docstring seeding (label-only, honest)
# --------------------------------------------------------------------------- #
_DOC_PATTERNS = [
    # - ``a`` — text  /  ``a`` = text  /  ``b`` — **name** text
    re.compile(r"^\s*[-*]?\s*``([ab])``\s*(?:—|-|=|:|–)\s*(.+?)\s*$"),
    # - **a**: text  / a — text
    re.compile(r"^\s*[-*]?\s*\*\*([ab])\*\*\s*(?:—|-|=|:|–)\s*(.+?)\s*$"),
    re.compile(r"^\s*([ab])\s*(?:—|=|:)\s*(.+?)\s*$"),
]


def _clean_label(text: str) -> str:
    t = re.sub(r"[`*]", "", text)
    t = t.split("(")[0].split("。")[0].split(".")[0]
    t = re.sub(r"\s+", " ", t).strip(" -—:=")
    return t[:40]


def _labels_from_text(text: str) -> dict[str, dict[str, str]]:
    """Extract {'a': {'label', 'doc'}, 'b': ...} from a docstring / markdown body."""
    out: dict[str, dict[str, str]] = {}
    for line in (text or "").splitlines():
        for pat in _DOC_PATTERNS:
            mm = pat.match(line)
            if mm:
                letter, body = mm.group(1), mm.group(2)
                if letter not in out and body:
                    out[letter] = {"label": _clean_label(body), "doc": re.sub(r"[`*]", "", body)[:200]}
                break
    return out


def _docs_root() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "ops")


def _find_op_note(name: str, root: Optional[str] = None) -> Optional[str]:
    root = root or _docs_root()
    if not os.path.isdir(root):
        return None
    target = name + ".md"
    for dirpath, _dirs, files in os.walk(root):
        if target in files:
            return os.path.join(dirpath, target)
    return None


def _parameters_section(md: str) -> str:
    """The body of a '## Parameters' / '## パラメータ' section, or '' if absent."""
    m = re.search(r"^##+\s*(Parameters|パラメータ|引数)\s*$(.*?)(?=^##\s|\Z)", md, re.S | re.M | re.I)
    return m.group(2) if m else ""


def seed_from_docs(names=None, docs_root: Optional[str] = None) -> dict[str, dict[str, dict]]:
    """Mine LABEL-ONLY specs from op docstrings and ``docs/ops/**/<op>.md``.

    Returns ``{op: {"a": spec, "b": spec}}`` for every op where at least one knob got
    a label. Each spec is the generic 0..1 float presentation (no invented range)
    carrying the extracted label/doc and ``source="docstring"`` / ``"docs/ops"``.
    Never raises: an op whose source or note cannot be read is simply skipped."""
    try:
        import api
    except Exception:                                   # pragma: no cover - import guard
        return {}
    if names is None:
        try:
            names = [r["name"] for r in api.list_ops()]
        except Exception:
            return {}
    seeded: dict[str, dict[str, dict]] = {}
    for name in names:
        found: dict[str, dict[str, str]] = {}
        src = None
        try:
            op = api.find_op(name)
            doc = getattr(getattr(op, "fn", None), "__doc__", None) or ""
        except Exception:
            doc = ""
        if doc:
            found = _labels_from_text(doc)
            src = "docstring" if found else None
        if not found:
            path = _find_op_note(name, docs_root)
            if path:
                try:
                    with open(path, encoding="utf-8") as fh:
                        sec = _parameters_section(fh.read())
                except OSError:
                    sec = ""
                if sec:
                    found = _labels_from_text(sec)
                    src = "docs/ops" if found else None
        if not found:
            continue
        entry = {}
        for letter in ("a", "b"):
            if letter in found:
                s = dict(GENERIC_FLOAT)
                s["label"] = found[letter]["label"]
                s["doc"] = found[letter]["doc"]
                s["source"] = src
                entry[letter] = s
            else:
                entry[letter] = dict(GENERIC_FLOAT)
        seeded[name] = entry
    return seeded


@functools.lru_cache(maxsize=1)
def _seeded_cache() -> dict[str, dict[str, dict]]:
    try:
        return seed_from_docs()
    except Exception:                                   # never let seeding break the UI
        return {}


def spec_for(op_name: str, seeded: bool = True) -> dict[str, dict[str, Any]]:
    """``{"a": spec, "b": spec}`` for an op: hand-written table first, then the
    docs/docstring seeds (label only), then the generic 0..1 float pair."""
    hand = PARAM_SPECS.get(op_name)
    if hand is not None:
        return {"a": dict(hand["a"]), "b": dict(hand["b"])}
    if seeded:
        s = _seeded_cache().get(op_name)
        if s is not None:
            return {"a": dict(s["a"]), "b": dict(s["b"])}
    return {"a": dict(GENERIC_FLOAT), "b": dict(GENERIC_FLOAT)}


def is_generic(spec: dict) -> bool:
    """True for the plain 0..1 float presentation (hand-written or seeded label aside)."""
    return (spec.get("kind") == "float" and float(spec.get("min", 0)) == 0.0
            and float(spec.get("max", 1)) == 1.0 and spec.get("map", "linear") == "linear"
            and not spec.get("unit"))


def seeded_ops() -> list[str]:
    """Ops that received a label from docs/docstrings (and have no hand-written spec)."""
    return sorted(n for n in _seeded_cache() if n not in PARAM_SPECS)
