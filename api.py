"""fullseye / imgevolve — stable programmatic API for other projects.

This is the surface another project imports. It works on **numpy arrays**
(no file I/O required), so a robotics/vision pipeline can hand imgevolve a frame
and get a measured result back::

    import fullseye                       # or: import api
    import numpy as np
    frame = np.random.rand(480, 640)      # float64 gray in [0, 1]
    edges = fullseye.apply(frame, "sobel_amp")          # HALCON name or op name
    seg   = fullseye.apply(frame, "otsu")               # image -> region (binary)
    n     = fullseye.apply(seg,   "count_obj")          # region -> feature (scalar)
    out   = fullseye.run_pipeline(frame, ["gauss_filter", "sobel_amp", "otsu"])

Operators are resolved by their op **name** first, then by HALCON alias (the same
rule the CLI uses), so both ``"gauss_filter"`` (HALCON) and ``"gaussian"`` (op
name) work. ``a`` and ``b`` are the two knobs, each in ``[0, 1]``.

Sorts (an op's declared input/output type):
  image  H*W float64 in [0, 1]      region  H*W in {0, 1}
  color  H*W*3 RGB float64          feature scalar float (returned as a Python float)
  contour XLD dict {"shape", "cs"}  volume  D*H*W stack

Discover ops with :func:`list_ops` / :func:`op_names`, or the CLI
(``py -3.11 imgevolve.py ops --search edge``).
"""
from __future__ import annotations

import os
import sys
from typing import Iterable, Sequence

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import ops as _ops  # noqa: E402  (the engine registry; imports its backends on load)
import stereo  # noqa: E402  (numpy+scipy depth building blocks)
import terrain  # noqa: E402  (elevation map / traversability)
import imgio  # noqa: E402  (coercion / colormap visualisation / export)
import detect  # noqa: E402  (object segmentation / description / identification)
import registration  # noqa: E402  (rigid point-cloud registration: Kabsch + ICP)
import pose  # noqa: E402  (silhouette posture descriptors)
import flow  # noqa: E402  (dense optical flow: two-frame motion)
import motion  # noqa: E402  (flow analysis: energy / dominant / segmentation)
import recipes  # noqa: E402  (curated sample pipelines)
import measure  # noqa: E402  (line profiles / distance / angle)
from stereo import (  # noqa: E402,F401
    disparity_map, disparity_subpixel, lr_consistency,
    depth_from_disparity, reproject_to_points,
)
from measure import line_profile, distance, angle  # noqa: E402,F401
from registration import kabsch, icp, apply_transform, pca_align, register  # noqa: E402,F401
from pose import pose_descriptor, skeleton_nodes, principal_axis  # noqa: E402,F401
from flow import (  # noqa: E402,F401
    optical_flow_lk, optical_flow_hs, warp_by_flow, flow_magnitude, flow_angle,
)
from motion import (  # noqa: E402,F401
    frame_motion_energy, dominant_motion, flow_from_model, residual_motion,
    motion_segments,
)
from terrain import (  # noqa: E402,F401
    elevation_map, traversability, foothold_score, fill_gaps,
    ground_surface, ground_plane, detect_obstacles,
)
from imgio import (  # noqa: E402,F401
    to_float01, to_uint8, apply_cmap, colorize_depth, colorize_disparity,
    colorize_labels, colorize_height, colorize_flow, shaded_relief, overlay_mask,
    save, load, save_ply, COLORMAPS,
)
from detect import segment_objects, object_descriptor, nearest_prototype, draw_objects  # noqa: E402,F401

__all__ = [
    "apply", "run_pipeline", "find_op", "list_ops", "op_names",
    "categories", "read_image", "write_image", "RT", "REGISTRY", "version",
    "stereo", "disparity_map", "disparity_subpixel", "lr_consistency",
    "depth_from_disparity", "reproject_to_points",
    "terrain", "elevation_map", "traversability", "foothold_score", "fill_gaps",
    "ground_surface", "ground_plane", "detect_obstacles",
    "imgio", "to_float01", "to_uint8", "apply_cmap", "colorize_depth",
    "colorize_disparity", "colorize_labels", "colorize_height", "colorize_flow",
    "shaded_relief", "overlay_mask", "save", "load", "save_ply", "COLORMAPS",
    "detect", "segment_objects", "object_descriptor", "nearest_prototype", "draw_objects",
    "registration", "kabsch", "icp", "apply_transform", "pca_align", "register",
    "pose", "pose_descriptor", "skeleton_nodes", "principal_axis",
    "flow", "optical_flow_lk", "optical_flow_hs", "warp_by_flow",
    "flow_magnitude", "flow_angle",
    "recipes", "recipe", "measure", "line_profile", "distance", "angle",
]


def recipe(name):
    """Look up a curated sample pipeline by name (see ``fullseye.recipes``)."""
    return recipes.get(name)

__version__ = "0.1.0"


def version() -> str:
    return __version__


# ---- resolution ------------------------------------------------------------ #
def find_op(name: str):
    """Return the :class:`ops.Op` for *name*, or ``None``.

    Exact op name wins; only then the HALCON alias, preferring the canonical op
    (``name == halcon``) when several ops share an alias. Identical rule to the
    CLI's ``_find_op`` so programmatic and command-line resolution agree.
    """
    for o in _ops.REGISTRY:
        if o.name == name:
            return o
    hits = [o for o in _ops.REGISTRY if o.halcon == name]
    if not hits:
        return None
    for o in hits:
        if o.name == o.halcon:
            return o
    return hits[0]


def _resolve(name: str):
    op = find_op(name)
    if op is None:
        raise KeyError(
            "unknown operator %r — try op name or HALCON alias; "
            "list with fullseye.op_names() or `imgevolve.py has %s`" % (name, name)
        )
    return op


def _coerce_input(v, op):
    """Gently match the array to the op's declared input sort (opt-in)."""
    a = np.asarray(v)
    if op.in_sort == "region" and a.dtype.kind in "fiu":
        vals = np.unique(a)
        if vals.size > 2 or (vals.size and (vals.min() < 0.0 or vals.max() > 1.0)):
            return (a.astype(np.float64) > 0.5).astype(np.float64)
    return v


# ---- run ------------------------------------------------------------------- #
def apply(image, name: str, a: float = 0.5, b: float = 0.5, coerce: bool = True):
    """Apply one operator to *image* and return its raw output.

    image  -> image/region  : returns a float64 ndarray
    region -> feature        : returns a Python float (the scalar measurement)
    *      -> contour        : returns the XLD dict {"shape", "cs"}

    With ``coerce=True`` (default) a grayscale array handed to a ``region`` op is
    binarised at 0.5, matching the CLI. Pass ``coerce=False`` to feed the array
    through untouched.
    """
    op = _resolve(name)
    v = _coerce_input(image, op) if coerce else image
    out = _ops.RT[op.name](v, a, b)
    if op.out_sort == "feature":
        return float(np.asarray(out).reshape(-1)[0])
    return out


def run_pipeline(image, stages: Iterable, a: float = 0.5, b: float = 0.5,
                 coerce: bool = True):
    """Apply a sequence of operators, threading the array through each.

    *stages* is either a list of names (one shared ``a``/``b`` for the whole
    chain, like the CLI) **or** a list of ``(name, a, b)`` tuples for per-stage
    knobs — the latter is what you want when different stages need different
    tuning (the CLI cannot do this in a single call).
    """
    v = image
    first = True
    for st in stages:
        if isinstance(st, (tuple, list)):
            name, sa, sb = (list(st) + [a, b])[:3]
        else:
            name, sa, sb = st, a, b
        op = _resolve(name)
        if first:
            v = _coerce_input(v, op) if coerce else v
            first = False
        v = _ops.RT[op.name](v, sa, sb)
    return v


# ---- discovery ------------------------------------------------------------- #
def _rows():
    rows = [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sort,
             "out_sort": o.out_sort, "category": o.category, "tier": "registry"}
            for o in _ops.REGISTRY]
    try:
        import imgops_nary as _na
        rows += [{"name": o.name, "halcon": o.halcon, "in_sort": o.in_sorts[0],
                  "out_sort": o.out_sort, "category": "nary", "tier": "nary",
                  "arity": o.arity, "in_sorts": list(o.in_sorts)}
                 for o in _na.build_nary()]
    except Exception:
        pass
    return rows


def list_ops(sort: str | None = None, search: str | None = None) -> list[dict]:
    """Every operator as a uniform dict. Filter by input *sort* and/or *search*
    (substring over name/halcon/category)."""
    kw = (search or "").lower()
    out = []
    for r in _rows():
        if sort and r["in_sort"] != sort:
            continue
        hay = (r["name"] + " " + (r["halcon"] or "") + " " + r["category"]).lower()
        if kw and kw not in hay:
            continue
        out.append(r)
    return sorted(out, key=lambda r: (r["tier"], r["in_sort"], r["name"]))


def op_names() -> list[str]:
    """Sorted list of every registry op name (the identifiers :func:`apply` takes)."""
    return sorted(o.name for o in _ops.REGISTRY)


def categories() -> list[str]:
    return sorted({o.category for o in _ops.REGISTRY})


# ---- optional file helpers (cv2) ------------------------------------------- #
def read_image(path: str, sort: str = "image"):
    """Load *path* as a float64 array matching *sort* (needs opencv-python)."""
    import cv2
    if sort == "color":
        im = cv2.imread(path, cv2.IMREAD_COLOR)
        if im is None:
            raise FileNotFoundError(path)
        return im[:, :, ::-1].astype(np.float64) / 255.0
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        raise FileNotFoundError(path)
    g = im.astype(np.float64) / 255.0
    return (g > 0.5).astype(np.float64) if sort == "region" else g


def write_image(path: str, v) -> None:
    """Save a float64 image/region array to *path* (needs opencv-python)."""
    import cv2
    v = np.asarray(v)
    if v.ndim == 3 and v.shape[-1] == 3:
        out = np.clip(v * 255, 0, 255).astype(np.uint8)[:, :, ::-1]
    else:
        out = np.clip(np.asarray(v, np.float64) * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(path, out)


# convenience re-exports
RT = _ops.RT
REGISTRY = _ops.REGISTRY
