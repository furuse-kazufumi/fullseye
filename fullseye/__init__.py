"""fullseye — evolvable HALCON-parity image-operator library + pipeline designer.

Public package facade. Import this from any project::

    import fullseye
    out = fullseye.apply(frame, "gauss_filter")        # numpy in, numpy out
    seg = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])

The engine modules (``ops``, ``backends*``, ``evolve``, ``scale`` ...) live one
directory up as flat modules for historical reasons; this facade puts that
directory on ``sys.path`` and re-exports the stable API defined in ``api.py``.
Everything here works on numpy arrays with no file I/O (see :func:`apply`).
"""
from __future__ import annotations

import os
import sys
import warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# The extended backends run a wavelet transform at build() time which emits a
# benign pywt boundary UserWarning; keep the consumer's import clean.
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from api import (  # noqa: E402,F401
        apply, run_pipeline, find_op, list_ops, op_names, categories,
        read_image, write_image, RT, REGISTRY, __version__, version,
        stereo, disparity_map, depth_from_disparity, reproject_to_points,
        terrain, elevation_map, traversability, foothold_score, fill_gaps,
        imgio, to_float01, to_uint8, apply_cmap, colorize_depth,
        colorize_disparity, colorize_labels, colorize_height, shaded_relief,
        overlay_mask, save, load, save_ply, COLORMAPS,
        detect, segment_objects, object_descriptor, nearest_prototype, draw_objects,
        registration, kabsch, icp, apply_transform,
        pose, pose_descriptor, skeleton_nodes, principal_axis,
        recipes, recipe,
    )

__all__ = [
    "apply", "run_pipeline", "find_op", "list_ops", "op_names", "categories",
    "read_image", "write_image", "RT", "REGISTRY", "__version__", "version",
    "stereo", "disparity_map", "depth_from_disparity", "reproject_to_points",
    "terrain", "elevation_map", "traversability", "foothold_score", "fill_gaps",
    "imgio", "to_float01", "to_uint8", "apply_cmap", "colorize_depth",
    "colorize_disparity", "colorize_labels", "overlay_mask", "save", "load", "save_ply",
    "detect", "segment_objects", "object_descriptor", "nearest_prototype", "draw_objects",
    "registration", "kabsch", "icp", "apply_transform",
    "pose", "pose_descriptor", "skeleton_nodes", "principal_axis",
    "recipes", "recipe",
]
