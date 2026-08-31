"""Fullseye Studio — an HDevelop-style visual pipeline workbench (PySide6).

Interactively build an operator pipeline, tune each stage's two knobs, watch the
intermediate result update live with zoom/pan, inspect the current value
(variable / image / region check), load ready-made sample pipelines, and export the
pipeline as a `--ops` string or as Python. It is a thin front-end over the
`fullseye` API; the pipeline logic (`PipelineModel`), the inspector
(`inspect_result`) and the sample library (`recipes`) are Qt-free and unit-tested.

    py -3.11 studio.py            # or: fullseye-studio  (installed console script)
"""
from __future__ import annotations

import inspect
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import api
import imgio
import recipes
import engine        # pipeline validation (Problems panel) — diagnose_stages
import flow          # v14 perception panel
import motion
import stereo
import terrain


# --------------------------------------------------------------------------- #
# Headless pipeline logic (no Qt) — unit-testable.
# --------------------------------------------------------------------------- #
def truncate(text, limit=160):
    """Shorten *text* for a tooltip / list row so a 5-line backend traceback can
    not blow up the widget. Qt-free -> unit-tested."""
    s = " ".join(str(text).split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def validate_pipeline_dict(d):
    """Validate a loaded pipeline payload and return ``[[op, a, b], ...]``.

    Raises :class:`ValueError` with a human-readable message when the payload is
    malformed (not an object, ``stages`` missing/not a list, a stage that is not
    a 3-element sequence, a non-numeric knob) or names an operator that does not
    exist in the registry. The caller gets a fully-built list, so a bad file can
    never leave a half-applied pipeline behind. Qt-free -> unit-tested."""
    if not isinstance(d, dict):
        raise ValueError("not a pipeline file (expected a JSON object, got %s)"
                         % type(d).__name__)
    raw = d.get("stages")
    if raw is None:
        raise ValueError("not a pipeline file (no 'stages' key)")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("'stages' must be a list, got %s" % type(raw).__name__)
    out = []
    for i, s in enumerate(raw):
        if isinstance(s, str) or not isinstance(s, (list, tuple)) or len(s) != 3:
            raise ValueError("stage %d must be [op, a, b], got %r" % (i + 1, truncate(s, 60)))
        name = s[0]
        if not isinstance(name, str):
            raise ValueError("stage %d: operator name must be text, got %r"
                             % (i + 1, truncate(name, 40)))
        if api.find_op(name) is None:
            raise ValueError("stage %d: unknown operator %r" % (i + 1, name))
        try:
            a, b = float(s[1]), float(s[2])
        except (TypeError, ValueError):
            raise ValueError("stage %d (%s): knobs a, b must be numbers" % (i + 1, name))
        out.append([name, a, b])
    return out


# UI hooks, module-level so a headless test can stub the modal dialogs.
def _default_error(parent, title, text):                      # pragma: no cover - GUI
    from PySide6 import QtWidgets
    QtWidgets.QMessageBox.critical(parent, title, text)


def _default_confirm(parent, title, text):                    # pragma: no cover - GUI
    from PySide6 import QtWidgets
    btn = QtWidgets.QMessageBox.question(
        parent, title, text,
        QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
        QtWidgets.QMessageBox.Cancel)
    return btn == QtWidgets.QMessageBox.Discard


ERROR_HOOK = _default_error       # (parent, title, text) -> None
CONFIRM_HOOK = _default_confirm   # (parent, title, text) -> bool (True = go ahead)
KNOB_DEBOUNCE_MS = 160            # coalesce knob drags before re-running step_states


class PipelineModel:
    """An ordered list of (op, a, b) stages applied to a base image."""

    def __init__(self, image=None):
        self.image = None if image is None else np.asarray(image, np.float64)
        self.stages: list[list] = []          # [ [name, a, b], ... ]

    def set_image(self, arr):
        self.image = np.asarray(arr, np.float64)

    def add_stage(self, name, a=0.5, b=0.5):
        if api.find_op(name) is None:
            raise KeyError(name)
        self.stages.append([name, float(a), float(b)])
        return len(self.stages) - 1

    def remove_stage(self, i):
        del self.stages[i]

    def move_stage(self, i, j):
        self.stages.insert(j, self.stages.pop(i))

    def duplicate_stage(self, i):
        """Insert a copy of stage i right after it; return the new stage's index."""
        self.stages.insert(i + 1, list(self.stages[i]))
        return i + 1

    def set_knobs(self, i, a=None, b=None):
        if a is not None:
            self.stages[i][1] = float(a)
        if b is not None:
            self.stages[i][2] = float(b)

    def load_recipe(self, name):
        """Replace the pipeline with a named sample recipe (see `recipes`)."""
        st = recipes.stages(name)
        if st is None:
            raise KeyError(name)
        self.stages = [[op, float(a), float(b)] for (op, a, b) in st]

    def result_upto(self, idx):
        """The value after applying stages[0 .. idx] (idx = -1 -> the raw image)."""
        if self.image is None:
            return None
        if idx < 0 or not self.stages:
            return self.image
        prefix = [tuple(s) for s in self.stages[: idx + 1]]
        return api.run_pipeline(self.image, prefix)

    def output(self):
        return self.result_upto(len(self.stages) - 1)

    def step_states(self):
        """Per-step state for step execution: for each stage, the op, its knobs and
        an inspection of the intermediate result after that stage. This is what a
        step-through debugger shows — the object/variable state at every step.

        A stage that raises records an ``{"kind": "error"}`` state instead of
        aborting the whole list, so one bad stage does not blank the rest."""
        out = []
        for i in range(len(self.stages)):
            op, a, b = self.stages[i]
            try:
                state = inspect_result(self.result_upto(i))
            except Exception as e:                       # this op failed on its input
                state = {"kind": "error", "message": str(e)}
            out.append({"index": i, "op": op, "a": a, "b": b, "state": state})
        return out

    def step_times(self):
        """Accurate per-stage wall-clock in ms, aligned with self.stages.

        Applies each stage once to the previous stage's result (O(n)), so each number
        is that stage's own cost — a bottleneck read-out for the pipeline list. Kept
        separate from step_states (which owns the inspection states) so the correctness
        path is untouched; a stage that raises records None and stops the timing.
        """
        import time
        if self.image is None or not self.stages:
            return []
        out = []
        img = self.image
        for st in self.stages:
            if img is None:
                out.append(None); continue
            t0 = time.perf_counter()
            try:
                img = api.run_pipeline(img, [tuple(st)])
                out.append(round((time.perf_counter() - t0) * 1000.0, 1))
            except Exception:
                out.append(None); img = None
        return out

    def ops_string(self):
        return ",".join(s[0] for s in self.stages)

    def export_python(self):
        lines = ["import fullseye, numpy as np", "", "def pipeline(frame):",
                 "    return fullseye.run_pipeline(frame, ["]
        for name, a, b in self.stages:
            lines.append(f"        ({name!r}, {a:.3f}, {b:.3f}),")
        lines += ["    ])"]
        return "\n".join(lines) + "\n"

    def to_dict(self):
        return {"fullseye_pipeline": 1, "stages": [[op, a, b] for op, a, b in self.stages]}

    def load_dict(self, d):
        """Replace the pipeline from a saved dict.

        The payload is validated into a temporary list first (see
        :func:`validate_pipeline_dict`), so a malformed file raises
        :class:`ValueError` and leaves the current pipeline untouched."""
        self.stages = validate_pipeline_dict(d)


class PerceptionModel:
    """Headless logic for the Studio v14 perception panel.

    Given frame A (Studio's current image) and a second loaded frame B, render a
    colourised view of a two-frame perception op (optical flow, moving-region
    overlay, stereo depth, stereo terrain). Qt-free -> unit-testable."""

    MODES = ("optical flow", "motion overlay", "stereo depth", "stereo terrain")

    def __init__(self, frame_b=None):
        self.frame_b = None if frame_b is None else np.asarray(frame_b, np.float64)

    def set_frame_b(self, arr):
        self.frame_b = None if arr is None else np.asarray(arr, np.float64)

    def view(self, mode, frame_a):
        """Return an (H, W, 3) RGB visualization for *mode*. Raises ValueError if a
        second frame is missing or the two frames disagree in size."""
        if frame_a is None:
            raise ValueError("no frame A (load or generate an image first)")
        a = imgio.ensure_gray(np.asarray(frame_a, np.float64))
        if self.frame_b is None:
            raise ValueError("load a second frame (B) first")
        b = imgio.ensure_gray(self.frame_b)
        if a.shape != b.shape:
            raise ValueError("frame A %s and B %s must be the same size" % (a.shape, b.shape))
        if mode == "optical flow":
            u, v = flow.optical_flow_lk(a, b, levels=3)
            return imgio.colorize_flow(u, v)
        if mode == "motion overlay":
            u, v = flow.optical_flow_lk(a, b, levels=3)
            thr = max(0.5, float(motion.frame_motion_energy(u, v)))
            mask, _ = motion.motion_segments(u, v, threshold=thr, min_area=20)
            return imgio.overlay_mask(a, mask, color=(1.0, 0.25, 0.0))
        if mode == "stereo depth":
            disp = stereo.disparity_map(a, b, max_disp=16, block=9)
            depth = stereo.depth_from_disparity(disp, focal=100.0, baseline=0.1)
            return imgio.colorize_depth(depth)
        if mode == "stereo terrain":
            disp = stereo.disparity_map(a, b, max_disp=16, block=9)
            depth = stereo.depth_from_disparity(disp, focal=100.0, baseline=0.1)
            pts = stereo.reproject_to_points(depth, fx=100.0, fy=100.0)
            world = np.stack([pts[:, 0], pts[:, 2], -pts[:, 1]], axis=1)
            grid, _ = terrain.elevation_map(world, cell=0.5, agg="max")
            return imgio.colorize_height(terrain.fill_gaps(grid))
        raise ValueError("unknown perception mode: %r" % (mode,))


def demo_image(n=256):
    """A synthetic scene with edges, blobs and gradients to play with."""
    y, x = np.mgrid[0:n, 0:n]
    img = 0.5 + 0.3 * np.sin(x / 18.0) * np.cos(y / 22.0)
    img[n // 5: n // 3, n // 5: n // 2] = 0.95            # bright block
    img[(y - 3 * n // 4) ** 2 + (x - n // 3) ** 2 < (n // 10) ** 2] = 0.1   # dark disk
    return np.clip(img, 0, 1)


def histogram_image(arr, bins=64, w=256, h=64):
    """Render the intensity histogram of a [0,1] image as a (h, w) gray image with
    bars (headless -- used by the Studio's histogram panel, testable on its own)."""
    a = np.asarray(arr, np.float64)
    a = a[np.isfinite(a)]
    out = np.zeros((h, w), np.float64)
    if a.size == 0:
        return out
    hist, _ = np.histogram(np.clip(a, 0, 1), bins=bins, range=(0, 1))
    if hist.max() > 0:
        hist = hist / hist.max()
    for i in range(bins):
        col0 = int(i * w / bins)
        col1 = int((i + 1) * w / bins)
        top = int((1 - hist[i]) * (h - 1))
        out[top:h, col0:max(col1, col0 + 1)] = 1.0
    return out


def _is_binary(a):
    u = np.unique(a[np.isfinite(a)]) if a.size else a
    return u.size <= 2 and set(np.round(u, 6).tolist()).issubset({0.0, 1.0})


def inspect_result(val):
    """Sort-aware inspection of a pipeline result -- the Studio's variable / image /
    region checker. Returns a dict of human-readable fields (headless, testable)."""
    if isinstance(val, np.ndarray) and val.ndim in (2, 3):
        fin = np.isfinite(val)
        kind = "color" if val.ndim == 3 else ("region" if _is_binary(val) else "image")
        d = {"kind": kind, "shape": tuple(int(s) for s in val.shape), "dtype": str(val.dtype),
             "min": round(float(np.nanmin(val)), 4) if fin.any() else float("nan"),
             "max": round(float(np.nanmax(val)), 4) if fin.any() else float("nan"),
             "mean": round(float(np.nanmean(val)), 4) if fin.any() else float("nan"),
             "nonfinite": int((~fin).sum())}
        if kind == "region":
            from scipy import ndimage
            m = val > 0.5
            lab, n = ndimage.label(m, structure=np.ones((3, 3), int))
            d["regions"] = int(n)
            d["area_px"] = int(m.sum())
            d["area_fraction"] = round(float(m.mean()), 4)
            if n:
                sizes = ndimage.sum(np.ones_like(lab, float), lab, range(1, n + 1))
                d["largest_region_px"] = int(sizes.max())
        return d
    if isinstance(val, dict):
        return {"kind": "contour", "n_contours": int(len(val.get("cs", [])))}
    if val is None:
        return {"kind": "none"}
    return {"kind": "feature", "value": round(float(np.asarray(val).reshape(-1)[0]), 6)}


def image_info_summary(d):
    """One-line status-bar summary of a pipeline result (shape / dtype / value range).

    Always-visible orientation about what is on screen, complementing the fuller
    Inspector panel. Headless + testable (mirrors inspect_result's dict)."""
    k = d.get("kind")
    if k in ("image", "color", "region"):
        shp = "×".join(str(v) for v in d.get("shape", ()))
        out = "%s %s [%.3g, %.3g]" % (shp, d.get("dtype", "?"), d.get("min"), d.get("max"))
        if k == "region":
            out += " · %d obj" % d.get("regions", 0)
        if d.get("nonfinite"):
            out += " · %d non-finite" % d["nonfinite"]
        return out
    if k == "feature":
        return "scalar = %s" % d.get("value")
    if k == "contour":
        return "contours ×%d" % d.get("n_contours", 0)
    return "no image"


def format_inspection(d):
    return "\n".join(f"{k}: {v}" for k, v in d.items())


def step_summary(st):
    """One-line state summary for a step's result (for the pipeline/step list)."""
    k = st.get("kind")
    if k in ("image", "color"):
        return f"{k} {st['shape']} mean={st['mean']}"
    if k == "region":
        return f"region: {st['regions']} obj, area={st['area_fraction']}"
    if k == "feature":
        return f"feature = {st['value']}"
    if k == "contour":
        return f"contour x{st['n_contours']}"
    if k == "error":
        return "ERROR: " + str(st.get("message", ""))[:48]
    return str(k)


def apply_display(val, mode, base=None, draw=None):
    """Map a 2-D result to an RGB image for the chosen display mode: 'gray', any
    false-colour palette name, 'shaded relief', 'height (color)', or 'region overlay'
    (blend a binary region onto *base* — HDevelop dev_display of a region on the
    current image). *draw* (optional) is the HDevelop dev_set_draw/dev_set_color/
    dev_set_line_width style {mode:'fill'|'margin', color, line_width, alpha} for the
    region overlay; None = the default amber fill. Non-2-D or already-color results
    are returned unchanged. (Headless, testable.)"""
    if not isinstance(val, np.ndarray) or val.ndim != 2:
        return val
    if mode == "region overlay":
        if _is_binary(val) and isinstance(base, np.ndarray) and base.shape[:2] == val.shape:
            d = draw or {}
            return imgio.overlay_mask(base, val, color=d.get("color", (0.96, 0.62, 0.14)),
                                      alpha=d.get("alpha", 0.5), mode=d.get("mode", "fill"),
                                      line_width=d.get("line_width", 1))
        return val                        # not a region, or no matching base -> raw
    if mode in ("gray", None):
        return val
    if mode == "shaded relief":
        return imgio.shaded_relief(val)
    if mode == "height (color)":
        return imgio.colorize_height(val, name="terrain")
    if mode in imgio.COLORMAPS:
        return imgio.apply_cmap(val, name=mode)
    return val


def _downsample_grid(hm, max_side=140):
    """Downsample a height map for a 3-D surface (headless, testable)."""
    h = np.asarray(hm, np.float64)
    if not np.isfinite(h).all():
        fill = float(np.nanmin(h[np.isfinite(h)])) if np.isfinite(h).any() else 0.0
        h = np.where(np.isfinite(h), h, fill)
    ry = max(1, h.shape[0] // max_side)
    rx = max(1, h.shape[1] // max_side)
    return h[::ry, ::rx]


# Dark, modern IDE design system (QSS). The palette is taken from the Fullseye
# brand mark (assets/fullseye.ico): deep navy ground, a teal primary accent for
# interaction/selection, and an amber secondary for section titles / knob handles
# — the "bullseye" that the whole product is named for.
NAVY_0, NAVY_1, NAVY_2 = "#14161d", "#1b1e28", "#232734"
LINE = "#2c313f"
TEXT, MUTED = "#e2e5ec", "#8b91a0"
TEAL, TEAL_HI = "#17b8a6", "#22d3bf"
AMBER = "#f5a524"
INK = "#0c1116"


# --------------------------------------------------------------------------- #
# Feature inspection (HDevelop-style) — headless cores, no Qt.
#
# 2-D: per-region shape/gray features backed by the existing implementations
# (detect.segment_objects for shape, image_gray.gray_features for gray stats —
# no new feature math lives here). 3-D: per-cluster features backed by
# pcseg.aabb / pcseg.obb. Both feed the Feature-inspection dialog (Ctrl+F5)
# and are unit-tested against known shapes.
# --------------------------------------------------------------------------- #

#: Selectable 2-D region features -> (source, human unit). Each is read from a
#: detect.segment_objects record or (``*_gray``) from image_gray.gray_features.
REGION_FEATURES = ("area", "row", "col", "width", "height", "circularity",
                   "perimeter", "eccentricity", "extent", "solidity",
                   "orientation_deg", "equiv_diameter",
                   "mean_gray", "deviation_gray", "min_gray", "max_gray")

#: The gray-value subset of REGION_FEATURES (needs the source image).
GRAY_REGION_FEATURES = ("mean_gray", "deviation_gray", "min_gray", "max_gray")


def region_feature_objects(result, min_area=1):
    """Label a 2-D pipeline result into per-region records for feature inspection.

    A binary (region) result keeps its own labeling (``threshold='none'``); a
    gray image is auto-segmented with Otsu — the HDevelop-workalike design choice
    here is *auto-labeling* rather than disabling the tool on gray input, so
    Feature inspection always has something honest to show (the info line in the
    dialog states which path was taken). Returns ``(objects, mode)`` where
    *objects* is the ``detect.segment_objects`` record list (largest first) and
    *mode* is ``'labels'`` (binary input) or ``'otsu'`` (auto-segmented).
    """
    import detect
    arr = np.asarray(result, np.float64)
    if arr.ndim != 2:
        raise ValueError("region_feature_objects: expected a 2-D array, got shape %s"
                         % (arr.shape,))
    mode = "labels" if _is_binary(arr) else "otsu"
    thr = "none" if mode == "labels" else "otsu"
    return detect.segment_objects(arr, threshold=thr, min_area=int(min_area)), mode


def region_feature_table(objs, names, image=None):
    """Build the feature table for segmented regions -> ``(headers, rows)``.

    *objs* is the record list from :func:`region_feature_objects`; *names* is an
    iterable of feature names (unknown names are silently dropped, gray features
    are dropped when *image* is None or its shape mismatches the masks). The
    first column is always the region label ``#``. Values are floats rounded to
    4 decimals (NaN when a backend could not provide the feature). Headless.
    """
    import image_gray
    names = [n for n in names if n in REGION_FEATURES]
    if image is None:
        names = [n for n in names if n not in GRAY_REGION_FEATURES]
    else:
        image = np.asarray(image, np.float64)
    headers = ["#"] + list(names)
    rows = []
    for o in objs:
        if image is not None and any(n in GRAY_REGION_FEATURES for n in names):
            if image.shape == o["mask"].shape:
                g = image_gray.gray_features(image, o["mask"])
            else:
                g = {}
        else:
            g = {}
        y0, x0, y1, x1 = o["bbox"]
        vals = {
            "area": o.get("area"), "row": o["centroid"][0], "col": o["centroid"][1],
            "width": float(x1 - x0), "height": float(y1 - y0),
            "circularity": o.get("circularity"), "perimeter": o.get("perimeter"),
            "eccentricity": o.get("eccentricity"), "extent": o.get("extent"),
            "solidity": o.get("solidity"),
            "orientation_deg": (float(np.degrees(o["orientation"]))
                                if np.isfinite(o.get("orientation", np.nan)) else float("nan")),
            "equiv_diameter": o.get("equiv_diameter"),
            "mean_gray": g.get("mean"), "deviation_gray": g.get("deviation"),
            "min_gray": g.get("min"), "max_gray": g.get("max"),
        }
        row = [float(o["label"])]
        for n in names:
            v = vals.get(n)
            row.append(round(float(v), 4) if v is not None and np.isfinite(v) else float("nan"))
        rows.append(row)
    return headers, rows


def feature_table_csv(headers, rows):
    """Serialise a feature table to CSV text (for 'Copy as CSV'). Headless."""
    out = [",".join(str(h) for h in headers)]
    for r in rows:
        cells = []
        for v in r:
            if isinstance(v, float):
                cells.append("%d" % v if float(v).is_integer() and np.isfinite(v) else "%s" % v)
            else:
                cells.append(str(v))
        out.append(",".join(cells))
    return "\n".join(out)


def region_label_at(objs, row, col):
    """Index into *objs* of the region covering pixel (*row*, *col*), or None.

    The reverse lookup behind 'click the image -> select the table row'.
    """
    r, c = int(row), int(col)
    for i, o in enumerate(objs):
        m = o["mask"]
        if 0 <= r < m.shape[0] and 0 <= c < m.shape[1] and m[r, c]:
            return i
    return None


def region_highlight_rgb(base, objs, selected=None):
    """Render the region-highlight overlay -> RGB float (H, W, 3) in [0, 1].

    *base* is the grayscale source (or the binary result itself); all regions get
    a faint teal tint so the labeling is visible, and *selected* (an index into
    *objs*) is overlaid in the Studio amber accent while every other region is
    dimmed — the two visual answers to "which row is which region". Headless.
    """
    b = np.clip(np.asarray(base, np.float64), 0.0, 1.0)
    if b.ndim == 3:
        rgb = b[..., :3].copy()
    else:
        rgb = np.stack([b, b, b], axis=-1)
    teal = np.array([0.09, 0.72, 0.65])
    amber = np.array([0.96, 0.65, 0.14])
    for i, o in enumerate(objs):
        m = o["mask"]
        if m.shape != rgb.shape[:2]:
            continue
        if selected is None:
            rgb[m] = rgb[m] * 0.70 + teal * 0.30
        elif i == selected:
            rgb[m] = rgb[m] * 0.35 + amber * 0.65
        else:
            rgb[m] = rgb[m] * 0.35 + teal * 0.12          # dim the non-selected regions
    return np.clip(rgb, 0.0, 1.0)


#: Per-cluster 3-D features (all derived from pcseg.aabb / pcseg.obb — nothing new).
CLUSTER_FEATURES = ("n_points", "centroid_x", "centroid_y", "centroid_z",
                    "extent_x", "extent_y", "extent_z",
                    "obb_length", "obb_width", "obb_height", "obb_volume")


def cluster_feature_table(points, clusters, names=None):
    """Feature table for point-cloud clusters -> ``(headers, rows)``.

    *clusters* is a list of index arrays (``pcseg.euclidean_clusters`` output).
    Features: point count, centroid, axis-aligned extent (``pcseg.aabb``) and
    oriented-bounding-box dimensions/volume (``pcseg.obb``; the OBB dims are the
    sorted full side lengths, volume their product). A cluster too small for an
    OBB (< 2 points) reports NaN for the OBB columns. First column = cluster id
    (1-based, matching the display). Headless, unit-tested on known boxes.
    """
    import pcseg
    P = np.asarray(points, np.float64)
    names = [n for n in (names or CLUSTER_FEATURES) if n in CLUSTER_FEATURES]
    headers = ["#"] + list(names)
    rows = []
    for ci, idx in enumerate(clusters, 1):
        Q = P[np.asarray(idx, int)]
        cen = Q.mean(axis=0) if Q.shape[0] else np.full(3, np.nan)
        try:
            lo, hi = pcseg.aabb(Q)
            ext = hi - lo
        except Exception:
            ext = np.full(3, np.nan)
        try:
            box = pcseg.obb(Q)
            dims = np.sort(2.0 * np.asarray(box["extents"], np.float64))[::-1]
            vol = float(np.prod(dims))
        except Exception:
            dims = np.full(3, np.nan); vol = float("nan")
        vals = {"n_points": float(Q.shape[0]),
                "centroid_x": cen[0], "centroid_y": cen[1], "centroid_z": cen[2],
                "extent_x": ext[0], "extent_y": ext[1], "extent_z": ext[2],
                "obb_length": dims[0], "obb_width": dims[1], "obb_height": dims[2],
                "obb_volume": vol}
        row = [float(ci)]
        for n in names:
            v = vals[n]
            row.append(round(float(v), 4) if np.isfinite(v) else float("nan"))
        rows.append(row)
    return headers, rows


def suggest_cluster_tol(points, k_med=3.0, sample=2000, seed=0):
    """A starting Euclidean-cluster tolerance for an unknown cloud: *k_med* x the
    median nearest-neighbour distance of (up to) *sample* points. Purely a UI
    default for the Feature-inspection 3-D tab — the user owns the final value.
    Headless."""
    from scipy.spatial import cKDTree
    P = np.asarray(points, np.float64).reshape(-1, 3)
    if P.shape[0] < 2:
        return 0.05
    if P.shape[0] > sample:
        P = P[np.random.default_rng(seed).choice(P.shape[0], sample, replace=False)]
    d, _ = cKDTree(P).query(P, k=2)
    med = float(np.median(d[:, 1]))
    return round(float(k_med) * med, 6) if med > 0 else 0.05


def demo_cluster_cloud(seed=0, n_per=400):
    """A synthetic 3-cluster point cloud for the 3-D demos/tests: three Gaussian
    blobs (std 0.4) centred 10 apart -> ``(points (3*n_per, 3), true_k=3)``."""
    rng = np.random.default_rng(seed)
    centers = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 5.0]])
    P = np.concatenate([c + rng.normal(scale=0.4, size=(int(n_per), 3)) for c in centers])
    return P, 3


# --------------------------------------------------------------------------- #
# Interactive 3-D viewer — headless camera math + software rasteriser.
#
# Method choice (measured 2026-08-30, RTX 5090 / GL 4.6 available): a QOpenGLWidget
# path (plan A) renders fastest but is dead under QT_QPA_PLATFORM=offscreen (CI)
# and fragile over Remote Desktop; Q3DScatter (plan B) has no mesh support and
# slow per-item proxies >50k points. The software rasteriser below measures
# (steady-state median, size=480, re-measured 2026-08-30) 66 ms/frame at 200k
# points (≈15 fps) and ~350 ms at 1M. Honest reading: comfortably interactive
# at this repo's data sizes (Itokawa ≈ 25k vertices), usable at 200k, and NOT
# interactive at 1M full resolution — which is why the viewer decimates to
# DRAG_BUDGET points during drags/wheel zooms and re-renders full on release.
# The SAME code path runs in tests, offscreen and over RDP. So the viewer is
# software-rendered with the camera math kept headless; a GL backend can be
# swapped in later without touching the interaction model.
# --------------------------------------------------------------------------- #
def viewer3d_camera(yaw_deg, pitch_deg):
    """Turntable orbit camera -> world-to-view rotation (3, 3).

    Rows are the view axes in world coordinates: right, down (screen y) and
    forward. yaw spins about the world z axis, pitch tilts toward it; both in
    degrees. ``yaw=0, pitch=0`` looks along +y with +z up on screen. Headless.
    """
    ya, pa = np.radians(float(yaw_deg)), np.radians(float(pitch_deg))
    cy, sy = np.cos(ya), np.sin(ya)
    cp, sp = np.cos(pa), np.sin(pa)
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
    rx = np.array([[1.0, 0.0, 0.0], [0.0, sp, -cp], [0.0, cp, sp]])
    return rx @ rz


def viewer3d_project(points, cam, center, radius, zoom, pan, size):
    """Project world points through the orbit camera -> ``(xy (n, 2), depth (n,))``.

    Orthographic: view = cam @ (P - center); screen xy maps the +/-radius view
    box into *size* pixels scaled by *zoom* and shifted by *pan* (pixels);
    depth is the view-space forward coordinate (larger = FARTHER from the
    camera — the camera sits on the negative forward side looking along +forward).
    Headless — the unit tests pin known vertices to known screen positions.
    """
    P = np.asarray(points, np.float64).reshape(-1, 3)
    V = (P - np.asarray(center, np.float64)) @ np.asarray(cam, np.float64).T
    s = 0.45 * float(size) * float(zoom) / max(float(radius), 1e-12)
    xy = V[:, :2] * s
    xy[:, 0] += size / 2.0 + float(pan[0])
    xy[:, 1] += size / 2.0 + float(pan[1])
    return xy, V[:, 2]


def volume_to_shell_points(vol, spacing=(1.0, 1.0, 1.0), max_points=2_000_000):
    """A (D, H, W) volume -> walkable boundary-shell point cloud. Headless.

    The bridge that lets the 3-D viewer (and the first-person walkthrough) open
    a CT/MRI volume directly: Otsu-threshold the volume, keep only the
    *boundary shell* of the foreground (volops.vol_boundary — the memory-frugal
    surface representation), and return the shell voxels as physical
    ``(z, y, x)`` points plus per-point grayscale colors from the original
    intensities. An over-large volume is mean-pooled down (factor-of-2 steps)
    until the shell fits *max_points* — decimation is reported in the returned
    info dict, never silent. Downsampling stops once the smallest axis reaches
    8 voxels (further pooling would destroy the surface), so with an extreme
    *max_points* the returned cloud can still exceed the budget — check
    ``info["n_points"]``.

    Returns ``(P, C, info)``: points (N, 3) float64 in physical units, colors
    (N, 3) in [0, 1], and ``info = {"shape", "downsampled_by", "threshold",
    "n_points"}``. Raises ``ValueError`` on a non-3-D or constant volume (no
    surface exists to walk around)."""
    import volops                                 # lazy: keep studio import light
    v = np.ascontiguousarray(vol, dtype=np.float64)
    if v.ndim != 3:
        raise ValueError("volume must be 3-D (D, H, W), got %d-D" % (v.ndim,))
    if not np.isfinite(v).all():
        raise ValueError("volume has non-finite voxels (NaN/Inf) — refusing")
    if float(v.max()) == float(v.min()):
        raise ValueError("volume is constant — no surface to display")
    sp = np.asarray([float(s) for s in spacing], dtype=np.float64)
    orig_shape = v.shape                          # BEFORE any downsampling
    factor = 1
    while True:
        # Otsu threshold via histogram (float64 accumulation, 256 bins)
        hist, edges = np.histogram(v.ravel(), bins=256)
        w = hist.astype(np.float64)
        centers = (edges[:-1] + edges[1:]) / 2.0
        w0 = np.cumsum(w)
        w1 = w0[-1] - w0
        m0 = np.cumsum(w * centers)
        mu0 = np.divide(m0, w0, out=np.zeros_like(m0), where=w0 > 0)
        mu1 = np.divide(m0[-1] - m0, w1, out=np.zeros_like(m0), where=w1 > 0)
        between = w0 * w1 * (mu0 - mu1) ** 2
        thr = float(centers[int(np.argmax(between))])
        mask = (v > thr).astype(np.float64)
        if not mask.any() or mask.all():          # degenerate split: fall back to mean
            thr = float(v.mean())
            mask = (v > thr).astype(np.float64)
        shell = volops.vol_boundary(mask, connectivity=6)
        n = int(shell.sum())
        if n <= max_points or min(v.shape) <= 8:
            break
        v = volops.volume_downsample(v, 2, mode="mean")
        sp = sp * 2.0
        factor *= 2
    idx = np.argwhere(shell > 0.5)
    if not len(idx):
        raise ValueError("no boundary voxels above the Otsu threshold %.4g" % thr)
    P = idx.astype(np.float64) * sp
    vals = v[idx[:, 0], idx[:, 1], idx[:, 2]]
    lo, hi = float(vals.min()), float(vals.max())
    g = (vals - lo) / (hi - lo) if hi > lo else np.full(len(vals), 0.7)
    C = np.repeat((0.25 + 0.75 * g)[:, None], 3, axis=1)   # dark-to-light gray
    # orig_shape, not v.shape: v has been reassigned by downsampling, so for a
    # list-like input `v.shape` here would misreport the DOWNSAMPLED shape
    info = {"shape": tuple(int(s) for s in orig_shape),
            "downsampled_by": factor, "threshold": thr,
            "n_points": len(P)}
    return P, C, info


def viewer3d_camera_fp(yaw_deg, pitch_deg):
    """First-person camera -> world-to-view rotation (3, 3).

    Same row convention as :func:`viewer3d_camera` (right, down-screen,
    forward) and — deliberately — the same rotation math: yaw spins about the
    world z axis, positive pitch tilts the LOOK direction up toward +z.
    ``yaw=0, pitch=0`` looks along +y with +z up on screen. The eye position is
    NOT part of the rotation; :func:`viewer3d_project_persp` subtracts it.
    Headless."""
    return viewer3d_camera(yaw_deg, pitch_deg)


def viewer3d_fp_axes(yaw_deg, pitch_deg):
    """WASD movement basis for the first-person camera -> (forward, right, up).

    forward is the full look direction (fly-style, pitch included — a museum
    walkthrough wants to glide toward whatever is being looked at), right is
    the horizontal strafe axis (independent of pitch by construction: the
    camera's right row never leaves the ground plane), up is world +z.
    Headless — unit tested against known yaw/pitch."""
    cam = viewer3d_camera_fp(yaw_deg, pitch_deg)
    return cam[2].copy(), cam[0].copy(), np.array([0.0, 0.0, 1.0])


#: first-person movement keys -> direction in the (forward, right, up) basis of
#: :func:`viewer3d_fp_axes` (module-level so the headless math is testable).
FP_MOVES = {"W": (1, 0, 0), "S": (-1, 0, 0), "A": (0, -1, 0), "D": (0, 1, 0),
            "E": (0, 0, 1), "Q": (0, 0, -1), "Space": (0, 0, 1)}

#: first-person vertical field of view (degrees): bounds, entrance default and
#: the per-keypress step for the +/- (or [ ]) keys.
FP_FOV_MIN, FP_FOV_MAX = 40.0, 100.0
FP_FOV_DEFAULT, FP_FOV_STEP = 70.0, 5.0


def fp_fov_adjust(fov_deg, delta_deg):
    """One +/- keypress on the first-person FOV: add *delta_deg* and clamp into
    ``[FP_FOV_MIN, FP_FOV_MAX]``. Headless — unit tested at both bounds."""
    return float(np.clip(float(fov_deg) + float(delta_deg), FP_FOV_MIN, FP_FOV_MAX))


def fp_move_vector(pressed, yaw_deg, pitch_deg):
    """World-space walk direction for a SET of held movement keys -> (3,) float.

    Sums the :data:`FP_MOVES` entries over *pressed* (unknown names are
    ignored) in the (forward, right, up) basis of :func:`viewer3d_fp_axes` —
    W+S cancels to zero, W+D walks the diagonal. The smooth-walk timer calls
    this every tick and multiplies by the per-tick step, replacing the old
    reliance on the OS key auto-repeat. Headless."""
    fwd, right, up = viewer3d_fp_axes(yaw_deg, pitch_deg)
    v = np.zeros(3)
    for name in pressed:
        d = FP_MOVES.get(name)
        if d is not None:
            v = v + fwd * d[0] + right * d[1] + up * d[2]
    return v


def fp_visible_edge_mask(edges, visible):
    """Near-plane clip for the first-person wireframe: keep only edges whose
    BOTH endpoints are visible. A segment with one endpoint at/behind the eye
    must be dropped whole — that endpoint's projected xy is meaningless (a
    negative view z would mirror it across the frame centre), so drawing the
    segment would smear a line through the view. edges (E, 2) int indices,
    visible (n,) bool -> (E,) bool mask. Headless."""
    E = np.asarray(edges, int)
    vis = np.asarray(visible, bool)
    if E.size == 0:
        return np.zeros((0,), bool)
    return vis[E[:, 0]] & vis[E[:, 1]]


def viewer3d_project_persp(points, cam, eye, fov_deg, size, near=1e-6):
    """Perspective projection through a first-person camera ->
    ``(xy (n, 2), depth (n,), visible (n,) bool)``.

    view = cam @ (P - eye); the vertical field of view *fov_deg* sets the focal
    length ``f = (size/2) / tan(fov/2)`` and screen xy is the classic
    ``view.xy * f / view.z`` about the frame centre. depth is the view-space
    forward coordinate; *visible* is the near-plane clip ``depth > near`` —
    points at or behind the eye MUST be dropped (their xy is meaningless and a
    negative z would mirror them across the centre). Headless — the unit tests
    pin forward points to the frame centre and reject points behind the eye."""
    P = np.asarray(points, np.float64).reshape(-1, 3)
    V = (P - np.asarray(eye, np.float64)) @ np.asarray(cam, np.float64).T
    z = V[:, 2]
    visible = z > float(near)
    f = 0.5 * float(size) / np.tan(np.radians(float(fov_deg)) / 2.0)
    zs = np.where(visible, z, 1.0)                # dummy divisor for clipped points
    xy = V[:, :2] * (f / zs)[:, None]
    xy += float(size) / 2.0
    return xy, z, visible


def _splat_points(img, xi, yi, colors, px):
    """Paint *px*-square splats onto *img* (h, w, 3) in array order (later wins).

    Bit-identical to the naive per-offset bounds-masked fancy assignment the
    renderers used to inline (pinned by a unit test against that reference),
    but measured ~2x cheaper at 250k points: splats that cannot touch the
    canvas are dropped ONCE up front, and the survivors paint into a canvas
    padded by ``px - 1`` on every side, so the px*px offset passes need no
    per-offset bounds mask and no per-offset gather. Ordering is preserved
    throughout (boolean filtering is stable, each pass assigns in the same
    array order), so the painter's algorithm outcome — including which
    duplicate index wins a pixel — is unchanged. In-place; returns *img*."""
    h, w = img.shape[:2]
    keep = (xi >= 1 - px) & (xi <= w - 1) & (yi >= 1 - px) & (yi <= h - 1)
    if not keep.all():
        xi, yi, colors = xi[keep], yi[keep], colors[keep]
    if xi.size == 0:
        return img
    if px == 1:
        img[yi, xi] = colors
        return img
    pad = px - 1
    big = np.empty((h + 2 * pad, w + 2 * pad, 3), img.dtype)
    big[pad:pad + h, pad:pad + w] = img
    ys, xs = yi + pad, xi + pad
    for dy in range(px):
        for dx in range(px):
            big[ys + dy, xs + dx] = colors
    img[:] = big[pad:pad + h, pad:pad + w]
    return img


def render_points_frame(points, colors=None, yaw=35.0, pitch=25.0, zoom=1.0,
                        pan=(0.0, 0.0), size=480, point_px=2,
                        center=None, radius=None, background=(0.070, 0.078, 0.106)):
    """Software-rasterise a point cloud -> RGB float (size, size, 3) in [0, 1].

    Depth-sorted splats (far painted first) of *point_px* square pixels; *colors*
    is (n, 3) in [0, 1] or None for a height (world z) viridis ramp via
    imgio.apply_cmap. This single function is the render core of the interactive
    viewer, the cluster preview AND the tests/screenshots — one code path, no
    drift. Headless (numpy only).
    """
    P = np.asarray(points, np.float64).reshape(-1, 3)
    size = int(size)
    img = np.empty((size, size, 3), np.float64)
    img[:] = np.asarray(background, np.float64)
    if P.shape[0] == 0:
        return img
    # drop non-finite vertices up front: NaN/inf points cannot be splatted and
    # would otherwise emit a RuntimeWarning per frame from the float->int cast
    # (and poison the auto center/radius). Colors follow their points.
    finite = np.isfinite(P).all(axis=1)
    if not finite.all():
        P = P[finite]
        if colors is not None:
            ca = np.asarray(colors, np.float64).reshape(-1, 3)
            colors = ca[finite] if ca.shape[0] == finite.shape[0] else ca
        if P.shape[0] == 0:
            return img
    if center is None:
        center = 0.5 * (P.min(axis=0) + P.max(axis=0))
    if radius is None:
        radius = float(np.linalg.norm(P - center, axis=1).max()) or 1.0
    if colors is None:
        z = P[:, 2]
        span = float(z.max() - z.min())
        t = (z - z.min()) / span if span > 0 else np.zeros_like(z)
        colors = imgio.apply_cmap(t.reshape(1, -1), name="viridis")[0]
    C = np.clip(np.asarray(colors, np.float64).reshape(-1, 3), 0.0, 1.0)
    if C.shape[0] != P.shape[0]:
        C = np.broadcast_to(C[:1], (P.shape[0], 3)).copy()
    xy, depth = viewer3d_project(P, viewer3d_camera(yaw, pitch), center, radius, zoom, pan, size)
    # painter's algorithm: paint far first so NEAR splats win. depth is the view
    # forward coordinate (larger = farther), so descending depth = far -> near.
    order = np.argsort(depth)[::-1]
    xi = np.floor(xy[order, 0]).astype(int)
    yi = np.floor(xy[order, 1]).astype(int)
    Co = C[order]
    px = max(1, int(point_px))
    for dy in range(px):
        for dx in range(px):
            xs, ys = xi + dx, yi + dy
            ok = (xs >= 0) & (xs < size) & (ys >= 0) & (ys < size)
            img[ys[ok], xs[ok]] = Co[ok]
    return img


def render_points_frame_fp(points, colors=None, eye=(0.0, 0.0, 0.0), yaw=0.0,
                           pitch=0.0, fov_deg=70.0, size=480, point_px=2,
                           radius=None, background=(0.070, 0.078, 0.106)):
    """First-person software-rasterise -> RGB float (size, size, 3) in [0, 1].

    The walkthrough twin of :func:`render_points_frame`: same splat approach,
    but through :func:`viewer3d_project_persp` (perspective is the whole point
    of the mode — parallax and size-with-distance are what make a cloud feel
    like a place instead of a chart). Two cheap depth cues on top:

    * brightness fades with distance (linear toward ``4 * radius``, floored so
      far geometry stays legible against the navy background);
    * points nearer than ``0.8 * radius`` splat one pixel larger — painted as a
      second pass AFTER all farther points, which keeps the painter's algorithm
      globally correct (every near point is in front of every far point).

    *radius* is the scene scale for the cues (auto from the data if None).
    Headless (numpy only) — the same code path runs in tests and in the widget.
    """
    P = np.asarray(points, np.float64).reshape(-1, 3)
    size = int(size)
    img = np.empty((size, size, 3), np.float64)
    img[:] = np.asarray(background, np.float64)
    if P.shape[0] == 0:
        return img
    finite = np.isfinite(P).all(axis=1)           # same NaN policy as the orbit path
    if not finite.all():
        P = P[finite]
        if colors is not None:
            ca = np.asarray(colors, np.float64).reshape(-1, 3)
            colors = ca[finite] if ca.shape[0] == finite.shape[0] else ca
        if P.shape[0] == 0:
            return img
    if radius is None:
        c = 0.5 * (P.min(axis=0) + P.max(axis=0))
        radius = float(np.linalg.norm(P - c, axis=1).max()) or 1.0
    radius = max(float(radius), 1e-12)
    if colors is None:
        z = P[:, 2]
        span = float(z.max() - z.min())
        t = (z - z.min()) / span if span > 0 else np.zeros_like(z)
        colors = imgio.apply_cmap(t.reshape(1, -1), name="viridis")[0]
    C = np.clip(np.asarray(colors, np.float64).reshape(-1, 3), 0.0, 1.0)
    if C.shape[0] != P.shape[0]:
        C = np.broadcast_to(C[:1], (P.shape[0], 3)).copy()
    # near plane scales with the scene (radius is floored at 1e-12 above, so
    # this is always > 0). It must NOT have an absolute floor: a cloud of
    # extent < ~1e-9 world units would then be entirely near-clipped (the eye
    # stands 1.5 * radius out, so max depth is ~2.5 * radius) and the FP view
    # would go permanently blank while the scale-free orbit view shows it fine.
    xy, depth, visible = viewer3d_project_persp(
        P, viewer3d_camera_fp(yaw, pitch), eye, fov_deg, size,
        near=1e-3 * radius)
    if not visible.any():
        return img
    xy, depth, C = xy[visible], depth[visible], C[visible]
    # depth cue 1: brightness attenuation with distance
    C = C * np.clip(1.0 - depth / (4.0 * radius), 0.30, 1.0)[:, None]
    px = max(1, int(point_px))
    near_thr = 0.8 * radius
    # far pass (base size) then near pass (base+1): each pass sorted far->near,
    # and the passes themselves are ordered far->near by the fixed threshold.
    for sel, p in ((depth >= near_thr, px), (depth < near_thr, px + 1)):
        if not sel.any():
            continue
        order = np.argsort(depth[sel])[::-1]
        xi = np.floor(xy[sel][order, 0]).astype(int)
        yi = np.floor(xy[sel][order, 1]).astype(int)
        Co = C[sel][order]
        for dy in range(p):
            for dx in range(p):
                xs, ys = xi + dx, yi + dy
                ok = (xs >= 0) & (xs < size) & (ys >= 0) & (ys < size)
                img[ys[ok], xs[ok]] = Co[ok]
    return img


def cluster_colors(n_points, clusters, selected=None):
    """Per-point colors for a clustered cloud -> (n_points, 3) float.

    Unclustered points are dark gray; clusters cycle a categorical palette.
    With *selected* set, that cluster gets the amber accent and every other
    point is dimmed — the viewer-side half of table-row -> cluster highlight.
    Headless."""
    palette = np.array([[0.09, 0.72, 0.65], [0.38, 0.55, 0.91], [0.61, 0.44, 0.86],
                        [0.30, 0.75, 0.42], [0.85, 0.42, 0.55], [0.80, 0.72, 0.35]])
    C = np.full((int(n_points), 3), 0.32, np.float64)
    for i, idx in enumerate(clusters):
        C[np.asarray(idx, int)] = palette[i % len(palette)]
    if selected is not None and 0 <= int(selected) < len(clusters):
        C *= 0.28                                    # dim everything ...
        C[np.asarray(clusters[int(selected)], int)] = [0.96, 0.65, 0.14]   # ... except the pick
    return C


def mesh_vertex_normals(V, F):
    """Area-weighted vertex normals (n, 3), unit length, for lambert shading.

    Face normals accumulated onto their vertices — the standard construction
    (same math as render3d's face normals, aggregated per vertex). Headless."""
    V = np.asarray(V, np.float64); F = np.asarray(F, int)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    ln = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.where(ln > 1e-12, ln, 1.0)


def validate_mesh_faces(V, F):
    """Fail-closed sanity check for a loaded triangle mesh: faces must be (m, 3)
    integer indices inside ``[0, len(V))``. Returns ``(V, F)`` as float64/int
    arrays; raises ValueError on a corrupt mesh (out-of-range or negative
    indices, wrong shape) so callers can log+flash instead of crashing later
    inside the renderer. Headless."""
    V = np.asarray(V, np.float64).reshape(-1, 3)
    F = np.asarray(F, int)
    if F.size:
        if F.ndim != 2 or F.shape[1] != 3:
            raise ValueError("mesh faces must be (m, 3), got shape %s" % (F.shape,))
        lo, hi = int(F.min()), int(F.max())
        if lo < 0 or hi >= V.shape[0]:
            raise ValueError("corrupt mesh: face index %d out of range for %d vertices"
                             % (lo if lo < 0 else hi, V.shape[0]))
    return V, F


def mesh_edges(F, cap=60000):
    """Unique undirected edges (E, 2) of a triangle mesh, or None when the count
    exceeds *cap* (the wireframe overlay skips itself rather than crawl)."""
    F = np.asarray(F, int)
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    e = np.unique(np.sort(e, axis=1), axis=0)
    return None if e.shape[0] > int(cap) else e

THEME = f"""
QWidget {{ background:{NAVY_0}; color:{TEXT}; font-size:12px;
    font-family:"Segoe UI","Yu Gothic UI","Meiryo",system-ui,sans-serif; }}
QMainWindow, QDialog {{ background:{NAVY_0}; }}
QLabel {{ color:{TEXT}; background:transparent; }}
QLabel[muted="true"] {{ color:{MUTED}; }}
QLabel[hint="true"] {{ color:{MUTED}; font-family:Consolas,"Cascadia Mono",monospace; }}

QMenuBar {{ background:#12141b; color:#c7cbd6; border-bottom:1px solid #262b38; padding:1px 4px; }}
QMenuBar::item {{ background:transparent; padding:3px 9px; border-radius:4px; }}
QMenuBar::item:selected {{ background:{NAVY_2}; color:{TEAL_HI}; }}
QMenu {{ background:{NAVY_1}; border:1px solid {LINE}; border-radius:5px; padding:3px; }}
QMenu::item {{ padding:4px 24px 4px 12px; border-radius:4px; }}
QMenu::item:selected {{ background:{TEAL}; color:{INK}; }}
QMenu::separator {{ height:1px; background:{LINE}; margin:4px 6px; }}

QToolBar {{ background:#12141b; border:none; border-bottom:1px solid #262b38; spacing:3px; padding:2px 6px; }}
QToolButton {{ background:{NAVY_2}; border:1px solid {LINE}; border-radius:4px; padding:3px 9px; color:{TEXT}; }}
QToolButton:hover {{ border-color:{TEAL}; color:{TEAL_HI}; }}
QToolButton:pressed {{ background:{TEAL}; color:{INK}; }}
QToolButton[accent="true"] {{ background:{TEAL}; color:{INK}; border:none; font-weight:700; }}
QToolButton[accent="true"]:hover {{ background:{TEAL_HI}; }}
QToolButton:focus {{ border:1px solid {TEAL_HI}; padding:3px 9px; }}

/* Dockable tool windows (VS/HDevelop-style). Compact title bars, square-ish. */
QDockWidget {{ titlebar-close-icon:none; titlebar-normal-icon:none;
    font-size:11px; color:{MUTED}; }}
QDockWidget::title {{ background:#161922; padding:7px 8px; border:1px solid #262b38;
    border-bottom:2px solid {TEAL}; text-transform:uppercase; letter-spacing:1px;
    text-align:left; }}
QDockWidget::title:hover {{ background:{NAVY_2}; }}
QDockWidget::close-button, QDockWidget::float-button {{
    background:transparent; border:none; padding:0; icon-size:12px; }}
QMdiArea {{ background:{NAVY_0}; }}
QMdiSubWindow {{ background:{NAVY_1}; }}
QMdiSubWindow > QWidget {{ border:1px solid #262b38; }}

QGroupBox {{ background:{NAVY_1}; border:1px solid #262b38; border-radius:6px;
    margin-top:9px; padding:6px 7px 7px 7px; }}
QGroupBox::title {{ subcontrol-origin:margin; subcontrol-position:top left; left:8px; top:0px;
    padding:0px 6px; color:{AMBER}; font-size:10px; font-weight:700; letter-spacing:1px; }}

QLineEdit,QComboBox,QPlainTextEdit,QListWidget,QSpinBox {{ background:{NAVY_2};
    border:1px solid {LINE}; border-radius:4px; padding:2px 7px;
    selection-background-color:{TEAL}; selection-color:{INK}; }}
QLineEdit:focus,QComboBox:focus,QPlainTextEdit:focus,QListWidget:focus,QSpinBox:focus {{
    border:1px solid {TEAL_HI}; }}
QListWidget::item {{ padding:2px 6px; border-radius:3px; }}
QListWidget::item:hover {{ background:#232a36; }}
QListWidget::item:selected {{ background:{TEAL}; color:{INK}; }}
QComboBox::drop-down {{ border:none; width:18px; }}
QComboBox QAbstractItemView {{ background:{NAVY_1}; border:1px solid {LINE}; border-radius:5px;
    selection-background-color:{TEAL}; selection-color:{INK}; outline:none; }}

QPushButton {{ background:{NAVY_2}; border:1px solid {LINE}; border-radius:4px; padding:3px 10px; color:{TEXT}; }}
QPushButton:hover {{ background:#262b38; border-color:{TEAL}; }}
QPushButton:pressed {{ background:{TEAL}; color:{INK}; }}
QPushButton:disabled {{ color:#5b6270; border-color:#232734; background:#191c25; }}
QPushButton[accent="true"] {{ background:{TEAL}; color:{INK}; border:none; font-weight:700; }}
QPushButton[accent="true"]:hover {{ background:{TEAL_HI}; }}
/* Visible keyboard focus. A blanket universal-selector outline reset used to erase
   the focus ring on every widget, leaving keyboard users with no idea where focus
   was; each interactive widget now carries an explicit teal :focus border. */
QPushButton:focus {{ border:1px solid {TEAL_HI}; padding:3px 10px; }}
QTabBar::tab {{ background:{NAVY_1}; color:{MUTED}; padding:3px 10px; border:1px solid #262b38;
    border-bottom:none; border-top-left-radius:4px; border-top-right-radius:4px; }}
QTabBar::tab:selected {{ background:{NAVY_2}; color:{TEAL_HI}; }}

QSlider::groove:horizontal {{ height:6px; background:{LINE}; border-radius:3px; }}
QSlider::handle:horizontal {{ width:16px; background:{AMBER}; border-radius:8px; margin:-6px 0; }}
QSlider::handle:horizontal:hover {{ background:#ffb841; }}
QSlider::sub-page:horizontal {{ background:{TEAL}; border-radius:3px; }}
/* Qt QSS orders the sub-control BEFORE the pseudo-state. Writing the state first
   (widget-state, then sub-control) silently never matches, which is why a disabled
   slider used to keep painting the enabled-looking amber handle. */
QSlider::handle:horizontal:disabled {{ background:#3d424e; }}
QSlider::sub-page:horizontal:disabled {{ background:#2a2f3b; }}
QSlider::groove:horizontal:disabled {{ background:#232734; }}
QSlider::handle:horizontal:focus {{ border:2px solid {TEAL_HI}; }}

QScrollBar:vertical {{ background:transparent; width:12px; margin:2px; }}
QScrollBar::handle:vertical {{ background:{LINE}; border-radius:6px; min-height:28px; }}
QScrollBar::handle:vertical:hover {{ background:#3a4152; }}
QScrollBar:horizontal {{ background:transparent; height:12px; margin:2px; }}
QScrollBar::handle:horizontal {{ background:{LINE}; border-radius:6px; min-width:28px; }}
QScrollBar::add-line,QScrollBar::sub-line {{ height:0; width:0; }}
QSplitter::handle {{ background:#262b38; }}
QSplitter::handle:horizontal {{ width:2px; }}
QStatusBar {{ background:#12141b; color:{MUTED}; border-top:1px solid #262b38; }}
QStatusBar QLabel {{ color:{MUTED}; }}
QStatusBar::item {{ border:none; }}
QToolTip {{ background:{INK}; color:{TEXT}; border:1px solid {TEAL}; border-radius:6px; padding:6px 8px; }}
"""

_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fullseye.ico")


def op_detail(row) -> str:
    """One-line human description of an operator (a ``list_ops`` row dict).

    Shows what the op does at a glance: its name, the sort transform it performs,
    its category and — when it mirrors a HALCON operator — the HALCON alias. Used
    for the selected-stage label and (via :func:`op_tooltip`) list tooltips."""
    hal = ("  ·  HALCON: " + row["halcon"]) if row.get("halcon") else ""
    return "%s   [%s → %s]  ·  %s%s" % (
        row["name"], row["in_sort"], row["out_sort"], row["category"], hal)


# Curated, human-readable roles for the two knobs a, b of common ops — so the
# operator panel can answer "what do these arguments do?" at a glance. Ops not
# listed fall back to the implementation source (op_impl_source), which is honest
# and universal (it shows exactly how a and b are used). "" means the knob is unused.
_ARG_ROLES = {
    "gaussian": ("blur amount — Gaussian σ = 0.3 + 2.7·a", ""),
    "mean_box": ("box size (odd kernel from a)", ""),
    "median": ("kernel size (odd, from a)", ""),
    "min_filter": ("kernel size (from a)", ""),
    "max_filter": ("kernel size (from a)", ""),
    "gamma": ("gamma = 0.5 + 1.5·a (a<0.5 brightens)", ""),
    "invert": ("", ""),
    "scale_clip": ("contrast scale = 0.5 + 1.5·a", "brightness offset = b − 0.5"),
    "threshold": ("threshold level (a, on 0..1)", ""),
    "unsharp": ("sharpen amount = 1.5·a", "radius = 0.5 + 1.5·b"),
    "sobel_mag": ("", ""),
    "bilateral": ("spatial σ (from a)", "range/edge σ (from b)"),
    "clahe": ("clip limit (from a)", "tile size (from b)"),
    "otsu": ("", ""),
}


def op_arg_roles(name):
    """Best-effort (a_role, b_role) description for an op's two knobs. Curated for
    common ops; ('', '') stays generic. Returns (None, None) if the op is unknown."""
    if api.find_op(name) is None:
        return (None, None)
    return _ARG_ROLES.get(name, ("", ""))


def op_impl_source(name):
    """The operative expression of an op's implementation (honest, universal answer
    to 'what do a and b do'): e.g. gaussian -> 'gaussian_filter(v, sigma=0.3 + 2.7 * a)'.
    Empty string if the source is unavailable (C-extension, lambda without source)."""
    op = api.find_op(name)
    if op is None:
        return ""
    try:
        src = " ".join(inspect.getsource(op.fn).split())
    except (OSError, TypeError):
        return ""
    body = src.split("return ", 1)
    return (body[1] if len(body) == 2 else src)[:220]


def op_signature_detail(row) -> str:
    """Rich multi-line signature for the operator panel: the sort/category/HALCON
    line, each knob's role, and the implementation expression. Answers the user's
    'the arguments can't be judged' by showing exactly what a and b control."""
    if row.get("backend") == "general":
        # general-algorithm tier: a seq/scalar op, NOT an image-pipeline op. Show its
        # signature + provenance and how to run it (via the CLI), read-only.
        return ("%s   [%s → %s]\ngeneral-algorithm tier (%s) — a seq/scalar op, not an "
                "image-pipeline op\nprovenance: %s\nrun via CLI:  py -3.11 imgevolve.py "
                "algo run %s --seq ..."
                % (row["name"], row["in_sort"], row["out_sort"], row["category"],
                   row.get("provenance") or "(none)", row["name"]))
    lines = [op_detail(row)]
    a_role, b_role = op_arg_roles(row["name"])
    lines.append("knob a — %s" % (a_role if a_role else "(unused)" if a_role == "" else "see impl"))
    lines.append("knob b — %s" % (b_role if b_role else "(unused)" if b_role == "" else "see impl"))
    src = op_impl_source(row["name"])
    if src:
        lines.append("impl: %s" % src)
    return "\n".join(lines)


def op_tooltip(row) -> str:
    """Multi-line tooltip for an operator list item / stage."""
    if row.get("backend") == "general":
        return ("%s\ngeneral-algorithm tier (%s) — seq/scalar, not an image op\n"
                "sort: %s → %s\nprovenance: %s\nrun via CLI: imgevolve.py algo run %s"
                % (row["name"], row["category"], row["in_sort"], row["out_sort"],
                   row.get("provenance") or "(none)", row["name"]))
    a_role, b_role = op_arg_roles(row["name"])
    knobs = ("a: %s\nb: %s" % (a_role or "(op-dependent)", b_role or "(op-dependent)")
             if (a_role or b_role) else "a, b are the two knobs (each 0..1); meaning depends on the op")
    return ("%s\nHALCON alias: %s\ncategory: %s\nsort: %s → %s\n%s"
            % (row["name"], row.get("halcon") or "(none)", row["category"],
               row["in_sort"], row["out_sort"], knobs))


# --- HDevelop-style program syntax (parser is module-level + headless-testable) --- #
def _hdev_strip_comment(line):
    """Strip an HDevelop comment: a whole-line `*` comment, or an inline `#`."""
    s = line.strip()
    if s.startswith("*"):
        return ""
    return s.split("#", 1)[0].strip()


def _hdev_parse_op(line, lineno, errs, names):
    """Parse one operator statement — HDevelop `op (a, b)` or the terse `op a b`.
    Returns (name, a, b) clamped to [0,1], or None (appending an error)."""
    line = line.strip()
    if "(" in line and line.endswith(")"):
        name = line[:line.index("(")].strip()
        inner = line[line.index("(") + 1:-1].strip()
        args = [p.strip() for p in inner.split(",")] if inner else []
    else:
        parts = line.split()
        name, args = parts[0], parts[1:]
    if name not in names:
        errs.append("line %d: unknown op '%s'" % (lineno, name)); return None
    try:
        a = float(args[0]) if len(args) > 0 and args[0] != "" else 0.5
        b = float(args[1]) if len(args) > 1 and args[1] != "" else 0.5
    except ValueError:
        errs.append("line %d: args must be numbers" % lineno); return None
    return (name, max(0.0, min(1.0, a)), max(0.0, min(1.0, b)))


def _hdev_eval_cond(expr):
    """Evaluate a constant if-condition: a number (0=false) or `x <cmp> y` with
    numeric constants (< > <= >= = == != #). Unknown -> True (include the block)."""
    expr = expr.strip().replace("#", "!=")
    for sym, fn in (("<=", lambda a, b: a <= b), (">=", lambda a, b: a >= b),
                    ("==", lambda a, b: a == b), ("!=", lambda a, b: a != b),
                    ("<", lambda a, b: a < b), (">", lambda a, b: a > b),
                    ("=", lambda a, b: a == b)):
        if sym in expr:
            try:
                left, right = expr.split(sym, 1)
                return bool(fn(float(left), float(right)))
            except ValueError:
                return True
    try:
        return float(expr) != 0.0
    except ValueError:
        return True


def parse_hdev_program(text, names):
    """Parse an HDevelop-style program into a flat list of (op, a, b) stages.

    Supports operator calls (`op (a, b)` or `op a b`), `*`/`#` comments, and control
    flow that expands statically into the linear pipeline:
      * `for N ... endfor`               — repeat the block N times (loop unrolling)
      * `if <const-cond> ... [else ...] endif` — pick a branch by a constant test
    `while`/`elseif` are reported as unsupported (they need runtime control variables
    the flat pipeline model does not have). Returns (stages, errors)."""
    names = set(names)
    errs = []
    toks = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = _hdev_strip_comment(raw)
        if not line:
            continue
        head = line.split()[0].lower()
        kind = head if head in ("for", "endfor", "if", "else", "elseif",
                                "endif", "while", "endwhile") else "op"
        toks.append((kind, line, n))

    pos = [0]

    def expect(kw, openln):
        if pos[0] < len(toks) and toks[pos[0]][0] == kw:
            pos[0] += 1
        else:
            errs.append("missing '%s' (opened at line %d)" % (kw, openln))

    def parse_block(terminators):
        out = []
        while pos[0] < len(toks):
            kind, line, n = toks[pos[0]]
            if kind in terminators:
                return out
            pos[0] += 1
            if kind == "for":
                try:
                    count = int(float(line.split()[1]))
                except (IndexError, ValueError):
                    errs.append("line %d: 'for' needs a count, e.g. 'for 3'" % n); count = 0
                body = parse_block(("endfor",))
                expect("endfor", n)
                out += body * max(0, count)
            elif kind == "if":
                cond = _hdev_eval_cond(line[2:].strip())
                then_body = parse_block(("else", "endif"))
                else_body = []
                if pos[0] < len(toks) and toks[pos[0]][0] == "else":
                    pos[0] += 1
                    else_body = parse_block(("endif",))
                expect("endif", n)
                out += then_body if cond else else_body
            elif kind == "while":
                errs.append("line %d: 'while' not supported — use 'for N'" % n)
                parse_block(("endwhile",)); expect("endwhile", n)
            elif kind in ("endfor", "endif", "endwhile", "else", "elseif"):
                errs.append("line %d: unexpected '%s'" % (n, kind))
            else:  # op — or a dev_*/set_system directive, which is not a pipeline stage
                head = _dev_op_head(line)
                if (head.startswith("dev_") or head in _CONFIG_DIRECTIVES
                        or head.startswith("disp_")):
                    if head.startswith("dev_") and head not in _DEV_DIRECTIVES:
                        errs.append("line %d: unsupported dev_ operator '%s'" % (n, head))
                    if head.startswith("disp_") and head not in _DISP_DIRECTIVES:
                        errs.append("line %d: unsupported disp_ operator '%s'" % (n, head))
                    continue                       # applied via extract_dev_directives
                st = _hdev_parse_op(line, n, errs, names)
                if st:
                    out.append(st)
        return out

    stages = parse_block(())
    return stages, errs


#: HDevelop dev_* operators Fullseye Studio honours as display DIRECTIVES — they set
#: display state (update on/off, display range); they are NOT image pipeline stages.
#: See docs/HDEVELOP_DEV_OPS.md.
_DEV_DIRECTIVES = {"dev_update_window", "dev_update_var", "dev_update_pc",
                   "dev_update_time", "dev_update_off", "dev_update_on", "dev_set_part",
                   "dev_set_lut", "dev_clear_window",
                   "dev_set_draw", "dev_set_color", "dev_set_line_width", "dev_disp_text",
                   # window management (user spec 2026-08-30: multi-window scripts must
                   # be able to open / select / place graphics windows, like HDevelop)
                   "dev_open_window", "dev_set_window", "dev_set_window_extents",
                   "dev_close_window"}

#: HALCON colour names -> RGB in [0,1], for dev_set_color.
_HALCON_COLORS = {
    "red": (1.0, 0.0, 0.0), "green": (0.0, 1.0, 0.0), "blue": (0.0, 0.0, 1.0),
    "yellow": (1.0, 1.0, 0.0), "cyan": (0.0, 1.0, 1.0), "magenta": (1.0, 0.0, 1.0),
    "white": (1.0, 1.0, 1.0), "black": (0.0, 0.0, 0.0), "orange": (0.96, 0.62, 0.14),
    "gray": (0.5, 0.5, 0.5), "grey": (0.5, 0.5, 0.5),
}

#: Non-dev_ HALCON config operators Studio honours as program directives (set global
#: system parameters; not image pipeline stages). See docs/HDEVELOP_DEV_OPS.md (F).
_CONFIG_DIRECTIVES = {"set_system"}

#: HALCON Graphics-chapter disp_* operators Studio honours as program directives.
#: 2-D: disp_image / disp_region show a pipeline variable in the CURRENT graphics
#: window (arg = 1-based stage number; omitted/0 = the final result). 3-D:
#: disp_points3d / disp_mesh3d open (slot-reuse like dev_open_window) an
#: interactive 3-D viewer window on the same handle system; the arg is a file
#: path (mesh.read_points / mesh.read_mesh formats). disp_object_model_3d is the
#: honest HALCON-parity alias: it dispatches on the file (faces -> mesh, else
#: points). All are display directives — never image pipeline stages.
_DISP_DIRECTIVES = {"disp_image", "disp_region",
                    "disp_points3d", "disp_mesh3d", "disp_object_model_3d"}


def _dev_op_head(line):
    """The operator name of a program line ('dev_set_part' from
    'dev_set_part (0, 0, -1, -1)'), lowercased; '' if the line has no leading name."""
    m = re.match(r"\s*([A-Za-z_]\w*)", line)
    return m.group(1).lower() if m else ""


def _parse_dev_args(line):
    """Parse a dev_* directive's arguments into a list of float/str (numbers become
    float, quoted or bare words stay str). Accepts both 'op (a, b)' and 'op a b'."""
    if "(" in line:
        body = line.split("(", 1)[1].rsplit(")", 1)[0]
    else:
        parts = line.split(None, 1)
        body = parts[1] if len(parts) > 1 else ""
    args = []
    # quoted strings are single tokens — 'coins segmented' must NOT split into two args
    # (the shipped dev_* demo passes a two-word caption; splitting broke its text + row)
    for tok in re.findall(r"'[^']*'|\"[^\"]*\"|[^,\s]+", body.strip()):
        t = tok.strip("'\"")
        if not t:
            continue
        try:
            args.append(float(t))
        except ValueError:
            args.append(t)
    return args


def extract_dev_directives(text):
    """Scan an HDevelop program for supported dev_* display directives, in source
    order → list of (name, args). Comments are stripped; image-stage lines are left
    to :func:`parse_hdev_program`."""
    out = []
    for raw in text.splitlines():
        line = _hdev_strip_comment(raw)
        if line and _dev_op_head(line) in (_DEV_DIRECTIVES | _CONFIG_DIRECTIVES
                                           | _DISP_DIRECTIVES):
            out.append((_dev_op_head(line), _parse_dev_args(line)))
    return out


def _op_row(name):
    """Look up an op and return a ``list_ops``-shaped dict, or None.

    Falls back to the opt-in general-algorithm tier (``algo.py``); those rows carry
    ``backend == "general"`` so the UI shows them read-only (a different seq/scalar
    computational model, not an image-pipeline op)."""
    op = api.find_op(name)
    if op is not None:
        return {"name": op.name, "halcon": op.halcon, "category": op.category,
                "in_sort": op.in_sort, "out_sort": op.out_sort}
    try:
        import algo
        aop = algo.find_algo(name)
    except Exception:  # noqa: BLE001 - general tier is optional
        aop = None
    if aop is not None:
        return {"name": aop.name, "halcon": None, "category": "algo:" + aop.category,
                "in_sort": aop.in_sort, "out_sort": aop.out_sort,
                "backend": "general", "provenance": aop.provenance, "desc": aop.doc}
    return None


#: Sample image the dev_* visualization demo loads (a collected, license-clean image).
HDEV_VISUAL_DEMO_IMAGE = "coins"

#: An HDevelop-style program that actually USES the dev_* visualization directives:
#: segment the coins, then draw the region as a coloured outline with a text label.
HDEV_VISUAL_DEMO = (
    "* Fullseye Studio - HDevelop dev_* visualization demo (image: coins)\n"
    "* Segment the coins, then show the region as a cyan outline with a label.\n"
    "set_system ('thread_num', 0)\n"
    "gaussian (0.4, 0.5)\n"
    "otsu (0.5, 0.5)\n"
    "dev_set_lut ('region overlay')\n"
    "dev_set_draw ('margin')\n"
    "dev_set_color ('cyan')\n"
    "dev_set_line_width (2)\n"
    "dev_disp_text ('coins segmented', 14, 14)\n"
)


def sample_code(name):
    """``(ops_string, python_source)`` for a sample recipe — the 'Sample Code' view
    (author-in-Studio, run-anywhere). Returns None for an unknown recipe. Qt-free."""
    st = recipes.stages(name)
    if st is None:
        return None
    eng = engine.FullseyeEngine([(op, a, b) for (op, a, b) in st], name=name)
    # two-tier rule: every sample ships BOTH forms - one-shot AND staged
    # (copy a single stage / branch between stages with your own if/for)
    return eng.to_ops(), eng.to_python() + chr(10) + chr(10) + eng.to_python_staged()


def sample_thumb_path(name):
    """Absolute path to the pre-rendered result thumbnail (input -> output PNG) for
    sample recipe *name*, or ``None`` if absent. Files live in
    ``studio_assets/sample_thumbs/<slug>.png`` — regenerate with
    ``py -3.11 tools/gen_sample_thumbs.py``. Qt-free -> unit-tested."""
    slug = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "studio_assets", "sample_thumbs", slug + ".png")
    return p if os.path.exists(p) else None


def shortcut_table(items):
    """``[(label, shortcut_str), ...]`` -> the non-empty, de-duplicated rows for a
    keyboard-shortcut reference (label trimmed of trailing ellipsis). Qt-free ->
    unit-tested."""
    seen = set()
    rows = []
    for label, sc in items:
        sc = (sc or "").strip()
        if not sc:
            continue
        key = (label, sc)
        if key in seen:
            continue
        seen.add(key)
        rows.append((str(label).replace("…", "").strip(), sc))
    return rows


def palette_filter(labels, query):
    """Rank *labels* for the command palette by a substring *query*.

    Prefix matches rank above word-start matches above bare substrings, then by
    match position and shorter label. Returns indices into *labels*, best first;
    an empty query keeps the original order. Qt-free -> unit-tested."""
    q = str(query).lower().strip()
    if not q:
        return list(range(len(labels)))
    scored = []
    for i, lbl in enumerate(labels):
        h = str(lbl).lower()
        pos = h.find(q)
        if pos < 0:
            continue
        if h.startswith(q):
            rank = 0
        elif any(sep + q in h for sep in (" ", ":", "▸")):
            rank = 1
        else:
            rank = 2
        scored.append(((rank, pos, len(h)), i))
    scored.sort(key=lambda s: s[0])
    return [i for _, i in scored]


def _looks_binary(x) -> bool:
    return np.unique(np.asarray(x)).size <= 2


def holdout_metric(out, gt):
    """An honest comparison metric for one holdout pair: IoU for equal-shape binary
    masks, PSNR (dB) for equal-shape intensity images, or None when the pair cannot be
    compared (different shapes / non-image sorts) — so nothing is over-claimed."""
    out = np.asarray(out); gt = np.asarray(gt)
    if out.ndim not in (2, 3) or out.shape != gt.shape:
        return None
    o = out.astype(np.float64); g = gt.astype(np.float64)
    if _looks_binary(o) and _looks_binary(g):
        ob = o > (o.max() * 0.5 if o.max() else 0.5)
        gb = g > (g.max() * 0.5 if g.max() else 0.5)
        union = np.logical_or(ob, gb).sum()
        return float(np.logical_and(ob, gb).sum() / union) if union else 1.0

    def _norm(x):
        m = x.max()
        return x / m if m > 1.0 else x
    mse = float(np.mean((_norm(o) - _norm(g)) ** 2))
    return 99.0 if mse <= 1e-12 else float(10.0 * np.log10(1.0 / mse))


def run_holdout(stages, image_paths, gt_paths=None):
    """Run the current pipeline over a holdout / validation image set (Codex #12).

    Returns a summary dict: per-image ``results`` (path / ok / error / out_shape / ms /
    metric) plus aggregates (n, n_ok, n_err, mean_ms, mean_metric, metric_kind). This is
    the honest 'does this pipeline hold up on unseen images' check that imgevolve gates
    on — ground truth is optional; without it only ran/failed + timing are reported.
    Qt-free -> unit-tested."""
    import time
    results = []
    metric_kind = None
    for i, p in enumerate(image_paths):
        rec = {"path": p, "ok": False, "error": "", "ms": 0.0, "out_shape": None, "metric": None}
        gt = gt_paths[i] if (gt_paths and i < len(gt_paths) and gt_paths[i]) else None
        try:
            img = api.read_image(p)
            t0 = time.perf_counter()
            out = api.run_pipeline(img, list(stages))
            rec["ms"] = (time.perf_counter() - t0) * 1000.0
            rec["ok"] = True
            rec["out_shape"] = tuple(np.shape(out))
            if gt is not None:
                m = holdout_metric(out, api.read_image(gt))
                rec["metric"] = m
                if m is not None:
                    metric_kind = "IoU" if _looks_binary(np.asarray(out)) else "PSNR(dB)"
        except Exception as e:                    # a bad image / op failure must not abort the batch
            rec["error"] = str(e)
        results.append(rec)
    ok = [r for r in results if r["ok"]]
    metrics = [r["metric"] for r in ok if r["metric"] is not None]
    return {
        "n": len(results), "n_ok": len(ok), "n_err": len(results) - len(ok),
        "mean_ms": (sum(r["ms"] for r in ok) / len(ok)) if ok else 0.0,
        "mean_metric": (sum(metrics) / len(metrics)) if metrics else None,
        "metric_kind": metric_kind, "results": results,
    }


def _opengl_available() -> bool:
    """True only if a *valid* OpenGL context can actually be created.

    ``Q3DSurface`` assumes a live GL context and **segfaults** (a native access
    violation, not a catchable Python exception) when one cannot be made — the
    ``QT_QPA_PLATFORM=offscreen`` test/CI platform, a software-only build, or a
    thin Remote-Desktop session with no GPU acceleration. We therefore probe
    before ever touching QtDataVisualization: create a throwaway
    ``QOffscreenSurface`` + ``QOpenGLContext`` and only report success if the
    context is real and can be made current. ``QOpenGLContext.create()`` returns
    False (it does not crash) when GL is unavailable, so the probe itself is safe."""
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return False
    try:
        from PySide6 import QtGui, QtWidgets
        if QtWidgets.QApplication.instance() is None:
            return False
        surf = QtGui.QOffscreenSurface()
        surf.create()
        if not surf.isValid():
            return False
        ctx = QtGui.QOpenGLContext()
        if not ctx.create():
            surf.destroy()
            return False
        ok = bool(ctx.makeCurrent(surf))
        if ok:
            ctx.doneCurrent()
        surf.destroy()
        return ok
    except Exception:
        return False


def show_3d_surface(heightmap, parent=None):
    """Open a rotatable 3-D surface plot of a height/depth image (Q3DSurface).
    Best-effort: returns the container widget, or None if 3-D isn't available."""
    if not _opengl_available():          # Q3DSurface segfaults without a real GL context
        return None
    try:
        from PySide6.QtDataVisualization import Q3DSurface
        from PySide6 import QtWidgets
    except Exception:
        return None
    series = _build_surface3d_series(heightmap)
    surface = Q3DSurface()
    surface.addSeries(series)
    container = QtWidgets.QWidget.createWindowContainer(surface, parent)
    container.setMinimumSize(560, 460)
    container.setWindowTitle("Fullseye Studio - 3D surface")
    container.show()
    return container


def _build_surface3d_series(heightmap):
    """高さ場から QSurface3DSeries(地形風グラデーション付き)を構築して返す。

    Ctrl+3 ビューとスクリーンショット生成(tools/gen_studio_screenshots.py)が
    同一コード経路を通るための共有ヘルパー — 撮影用に別実装を持つと実機と
    見た目が乖離する。GL 前提の呼び出し側専用(offscreen では呼ばない)。"""
    from PySide6.QtDataVisualization import (QSurface3DSeries, QSurfaceDataProxy,
                                             QSurfaceDataItem)
    from PySide6 import QtGui
    h = _downsample_grid(heightmap)
    ny, nx = h.shape
    proxy = QSurfaceDataProxy()
    rows = []
    for i in range(ny):
        row = []
        for j in range(nx):
            row.append(QSurfaceDataItem(QtGui.QVector3D(float(j), float(h[i, j]), float(i))))
        rows.append(row)
    proxy.resetArray(rows)
    series = QSurface3DSeries(proxy)
    series.setDrawMode(QSurface3DSeries.DrawSurface)
    try:
        # 高さ連動の地形風グラデーション(低=深青 → 緑 → 砂色 → 頂=白)。
        # cosmetic なので API 差異で失敗しても表示自体は落とさない(fail-soft)。
        from PySide6.QtDataVisualization import Q3DTheme
        grad = QtGui.QLinearGradient()
        grad.setColorAt(0.0, QtGui.QColor(28, 58, 138))
        grad.setColorAt(0.35, QtGui.QColor(38, 158, 118))
        grad.setColorAt(0.65, QtGui.QColor(228, 198, 92))
        grad.setColorAt(1.0, QtGui.QColor(248, 248, 248))
        series.setBaseGradient(grad)
        style = getattr(getattr(Q3DTheme, "ColorStyle", Q3DTheme),
                        "ColorStyleRangeGradient")
        series.setColorStyle(style)
    except Exception:
        pass
    return series


# --------------------------------------------------------------------------- #
# Qt view (imported lazily so `import studio` works without a display).
# --------------------------------------------------------------------------- #
def _to_qimage(arr, QtGui):
    a = np.asarray(arr)
    if a.ndim == 2:
        u8 = np.ascontiguousarray(imgio.to_uint8(np.clip(a, 0, 1)))
        h, w = u8.shape
        return QtGui.QImage(u8.data, w, h, w, QtGui.QImage.Format_Grayscale8).copy()
    if a.ndim == 3 and a.shape[2] == 3:
        u8 = np.ascontiguousarray(imgio.to_uint8(np.clip(a, 0, 1)))
        h, w, _ = u8.shape
        return QtGui.QImage(u8.data, w, h, 3 * w, QtGui.QImage.Format_RGB888).copy()
    return None


def _image_view_class(QtWidgets, QtGui, QtCore):
    """A zoom/pan image viewer (wheel = zoom at cursor, drag = pan)."""
    class ImageView(QtWidgets.QGraphicsView):
        def __init__(self):
            super().__init__()
            self._scene = QtWidgets.QGraphicsScene(self)
            self.setScene(self._scene)
            self._item = self._scene.addPixmap(QtGui.QPixmap())
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
            self.setBackgroundBrush(QtGui.QColor("#202020"))
            self.setMinimumSize(380, 380)
            self.setMouseTracking(True)
            self._data = None
            self._text_items = []                    # dev_disp_text annotations (scene items)
            self.hover_cb = None                     # set by build_window
            self.click_cb = None                     # optional pixel-click callback (x, y)
            self._press_pos = None                   # to tell a click from a pan drag

        def set_pixmap(self, pm):
            self.clear_text()                        # a fresh render starts without stale annotations
            self._item.setPixmap(pm)
            self._scene.setSceneRect(QtCore.QRectF(pm.rect()))

        def disp_text(self, row, col, text, color=(1.0, 1.0, 1.0)):
            """dev_disp_text: add a text annotation at image (row, col) on the current
            window. Persists over the pixmap until the next render or dev_clear_window."""
            item = self._scene.addText(str(text))
            item.setDefaultTextColor(QtGui.QColor.fromRgbF(*[float(c) for c in color[:3]]))
            item.setPos(float(col), float(row))      # scene is (x=col, y=row)
            self._text_items.append(item)
            return item

        def clear_text(self):
            for it in self._text_items:
                try:
                    self._scene.removeItem(it)
                except Exception:
                    pass
            self._text_items = []

        def set_data(self, arr):
            self._data = np.asarray(arr) if arr is not None else None

        def mouseMoveEvent(self, e):
            super().mouseMoveEvent(e)
            if self._data is not None and self.hover_cb is not None:
                p = self.mapToScene(e.position().toPoint())
                x, y = int(p.x()), int(p.y())
                h, w = self._data.shape[:2]
                if 0 <= x < w and 0 <= y < h:
                    self.hover_cb(x, y, self._data[y, x])

        def mousePressEvent(self, e):
            self._press_pos = e.position().toPoint()
            super().mousePressEvent(e)

        def mouseReleaseEvent(self, e):
            # A CLICK (press+release without a pan drag) maps to an image pixel and
            # fires click_cb — the Feature-inspection dialog uses it for
            # "click a region -> select its table row". A drag (ScrollHandDrag pan)
            # moves further than the 4-px slop and is NOT a click.
            super().mouseReleaseEvent(e)
            pos = e.position().toPoint()
            if (self.click_cb is not None and self._data is not None
                    and self._press_pos is not None
                    and (pos - self._press_pos).manhattanLength() <= 4):
                p = self.mapToScene(pos)
                x, y = int(p.x()), int(p.y())
                h, w = self._data.shape[:2]
                if 0 <= x < w and 0 <= y < h:
                    self.click_cb(x, y)
            self._press_pos = None

        def clear(self):
            self.clear_text()
            self._item.setPixmap(QtGui.QPixmap())
            self._data = None

        def set_message(self, text):
            """Show a centred message instead of an image (empty / non-raster state)."""
            w = max(self.viewport().width(), 420)
            h = max(self.viewport().height(), 300)
            pm = QtGui.QPixmap(w, h)
            pm.fill(QtGui.QColor("#12141b"))
            p = QtGui.QPainter(pm)
            p.setPen(QtGui.QColor("#8b91a0"))
            f = p.font(); f.setPointSize(13); p.setFont(f)
            p.drawText(pm.rect(), QtCore.Qt.AlignCenter, text)
            p.end()
            self.set_pixmap(pm)
            self._data = None
            self.reset_zoom()

        def wheelEvent(self, e):
            f = 1.25 if e.angleDelta().y() > 0 else 0.8
            self.scale(f, f)

        def zoom(self, f):
            self.scale(f, f)

        def reset_zoom(self):
            self.resetTransform()

        def fit(self):
            if not self._item.pixmap().isNull():
                self.fitInView(self._item, QtCore.Qt.KeepAspectRatio)

        def set_pixmap_keep_view(self, pm):
            """Swap the pixmap but KEEP the current zoom/pan when the image geometry is
            unchanged (a re-render after a knob tweak). Returns True if the view was
            preserved, False if the size changed (the caller should then fit())."""
            same = (not self._item.pixmap().isNull()
                    and self._item.pixmap().size() == pm.size())
            t = self.transform()
            hs = self.horizontalScrollBar().value()
            vs = self.verticalScrollBar().value()
            self.set_pixmap(pm)
            if same:
                self.setTransform(t)
                self.horizontalScrollBar().setValue(hs)
                self.verticalScrollBar().setValue(vs)
                return True
            return False

        def set_part(self, r1, c1, r2, c2):
            """dev_set_part: show the image part with corners (Row1,Col1)-(Row2,Col2)
            in HALCON (row, col) order. Any negative value fits the whole image (a
            Studio convenience for 'reset to full'). Scene coords are (x=col, y=row)
            because the pixmap is placed 1:1, so the part maps directly to a QRectF."""
            if self._item.pixmap().isNull():
                return
            if min(r1, c1, r2, c2) < 0:
                self.fit(); return
            rect = QtCore.QRectF(float(min(c1, c2)), float(min(r1, r2)),
                                 float(abs(c2 - c1)) or 1.0, float(abs(r2 - r1)) or 1.0)
            self.fitInView(rect, QtCore.Qt.KeepAspectRatio)
    return ImageView


def _viewer3d_class(QtWidgets, QtGui, QtCore):
    """The interactive 3-D viewer widget (point clouds + meshes).

    Software-rasterised on purpose — see the method-choice note above
    :func:`viewer3d_camera`: the same numpy render path runs on GL-less
    platforms (offscreen CI, thin Remote Desktop) and is fully unit-testable,
    at measured interactive rates for this repo's data sizes. Interaction:
    left-drag orbits (turntable), wheel zooms at the view centre, middle- or
    Shift-drag pans, ``R`` resets the home view, ``W`` toggles the mesh
    wireframe overlay. ``F`` toggles a first-person walkthrough mode
    (museum-style): WASD moves (fly along the look direction), Q/E/Space move
    down/up, Shift quadruples the step, left-drag looks around (mouse-look —
    pointer lock is fragile in Qt, drag-look is not), middle-/Shift-drag
    strafes in the view plane, the wheel adjusts the walk speed and ``R``
    returns to the walkthrough entrance; orbit state is untouched while
    walking, so ``F`` again resumes the orbit view exactly where it was.
    Meshes draw as lambert-shaded vertex splats (vertex
    normals x view-direction light) plus an optional QPainter wireframe; very
    large clouds decimate uniformly to ``DRAG_BUDGET`` points during a drag or
    a wheel-zoom burst (the HUD then shows the honest "preview N pts" count)
    and re-render at full resolution on release / shortly after the last tick.
    """
    class Viewer3D(QtWidgets.QWidget):
        DRAG_BUDGET = 250000                   # points rendered per frame while interacting

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMinimumSize(320, 300)
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.setMouseTracking(False)
            self._P = np.zeros((0, 3))          # displayed points (mesh: its vertices)
            self._colors = None                 # explicit per-point colors, or None
            self._F = None                      # mesh faces, or None for a cloud
            self._V = None                      # mesh vertices proper (wireframe)
            self._VN = None                     # normals for the splat cloud
            self._edges = None                  # mesh wireframe edges (or None)
            self._wire = False
            self._clusters = []                 # index arrays for highlight mode
            self._selected = None               # highlighted cluster index
            self._center = np.zeros(3); self._radius = 1.0
            self._yaw, self._pitch, self._zoom = 35.0, 25.0, 1.0
            self._pan = [0.0, 0.0]
            self._fp = False                    # first-person walkthrough mode (F key)
            self._fp_yaw, self._fp_pitch = 0.0, 0.0
            self._eye = np.zeros(3)             # first-person camera position (world)
            self._fp_speed = 1.0                # walk-speed multiplier (wheel)
            self._drag = None                   # (mode, last QPoint) while a button is down
            self._frame = None                  # last rendered numpy frame (tests/screenshots)
            self._n_drawn = 0                   # points actually splatted last frame (HUD honesty)
            self._wheeling = False              # True during a wheel-zoom burst (decimated preview)
            self._wheel_timer = QtCore.QTimer(self)
            self._wheel_timer.setSingleShot(True)
            self._wheel_timer.setInterval(180)  # full re-render shortly after the last tick
            self._wheel_timer.timeout.connect(self._end_wheel)
            self.info = {"kind": "empty", "n_points": 0}

        # ---- data ----------------------------------------------------------- #
        def set_points(self, points, colors=None):
            """Show a point cloud (n, 3); *colors* (n, 3) in [0, 1] or None for a
            height ramp. Resets clusters/mesh state, keeps the camera."""
            self._P = np.asarray(points, np.float64).reshape(-1, 3)
            self._colors = None if colors is None else np.asarray(colors, np.float64)
            self._F = self._VN = self._edges = self._V = None
            self._clusters, self._selected = [], None
            self._refit(); self.info = {"kind": "points", "n_points": int(self._P.shape[0])}
            self._repaint()

        def set_mesh(self, V, F):
            """Show a triangle mesh: lambert-shaded splats + optional wireframe.

            The splat cloud is the vertices PLUS the face centroids (with face
            normals), which roughly doubles the surface sample density — a
            24.5k-vertex Itokawa reads as a surface instead of a dot sprinkle,
            still well inside the measured software-render budget."""
            Va = np.asarray(V, np.float64).reshape(-1, 3)
            self._F = np.asarray(F, int)
            fc = Va[self._F].mean(axis=1)                 # face centroids
            fn = np.cross(Va[self._F[:, 1]] - Va[self._F[:, 0]],
                          Va[self._F[:, 2]] - Va[self._F[:, 0]])
            ln = np.linalg.norm(fn, axis=1, keepdims=True)
            fn = fn / np.where(ln > 1e-12, ln, 1.0)
            self._V = Va                                  # true vertices (wireframe)
            self._P = np.concatenate([Va, fc])
            self._VN = np.concatenate([mesh_vertex_normals(Va, self._F), fn])
            self._edges = mesh_edges(self._F)
            self._colors = None
            self._clusters, self._selected = [], None
            self._refit()
            self.info = {"kind": "mesh", "n_points": int(Va.shape[0]),
                         "n_faces": int(self._F.shape[0]),
                         "wireframe_available": self._edges is not None}
            self._repaint()

        def set_clusters(self, clusters, selected=None):
            """Color the current cloud by cluster membership (3-D feature
            inspection); *selected* highlights one cluster and dims the rest."""
            self._clusters = list(clusters)
            self._selected = selected
            self._repaint()

        def set_selected_cluster(self, i):
            self._selected = i
            self._repaint()

        def _refit(self):
            P = self._P[np.isfinite(self._P).all(axis=1)] if self._P.size else self._P
            if P.shape[0]:
                self._center = 0.5 * (P.min(axis=0) + P.max(axis=0))
                self._radius = float(np.linalg.norm(P - self._center, axis=1).max()) or 1.0
            else:
                self._center = np.zeros(3); self._radius = 1.0

        # ---- rendering ------------------------------------------------------ #
        def _point_colors(self, idx=None):
            """Per-point colors; *idx* restricts the computation to that index
            subset so the interaction-decimated path never does O(N) lighting."""
            if self._clusters:
                C = cluster_colors(self._P.shape[0], self._clusters, self._selected)
                return C if idx is None else C[idx]
            if self._VN is not None:
                VN = self._VN if idx is None else self._VN[idx]
                cam = (viewer3d_camera_fp(self._fp_yaw, self._fp_pitch) if self._fp
                       else viewer3d_camera(self._yaw, self._pitch))
                lam = np.clip(VN @ -cam[2], 0.0, 1.0) * 0.82 + 0.16
                return lam[:, None] * np.array([0.78, 0.82, 0.88])
            if self._colors is None or idx is None:
                return self._colors
            return self._colors[idx] if self._colors.shape[0] == self._P.shape[0] \
                else self._colors

        def frame_rgb(self):
            """Render the current view -> RGB float array (the paintEvent core,
            exposed headless-style for tests and screenshots)."""
            size = max(64, min(self.width(), self.height()) or 480)
            P = self._P
            idx = None
            if ((self._drag is not None or self._wheeling)
                    and P.shape[0] > self.DRAG_BUDGET):
                # Uniform pick of exactly DRAG_BUDGET indices, chosen BEFORE the
                # color/lighting pass (no O(N) per-frame work while interacting).
                # A plain stride [::ceil(N/budget)] can undershoot the budget
                # badly (500,001 pts -> stride 3 -> 166,667 drawn); linspace
                # keeps the count honest at the advertised budget.
                idx = np.linspace(0, P.shape[0] - 1, self.DRAG_BUDGET).astype(np.intp)
                P = P[idx]
            C = self._point_colors(idx)
            self._n_drawn = int(P.shape[0])
            if self._fp:
                return render_points_frame_fp(
                    P, colors=C, eye=self._eye, yaw=self._fp_yaw,
                    pitch=self._fp_pitch, fov_deg=70.0, size=size, point_px=2,
                    radius=self._radius)
            return render_points_frame(
                P, colors=C, yaw=self._yaw, pitch=self._pitch, zoom=self._zoom,
                pan=self._pan, size=size, point_px=2,
                center=self._center, radius=self._radius)

        def _repaint(self):
            self._frame = None
            self.update()

        def paintEvent(self, ev):
            if self._frame is None:
                self._frame = self.frame_rgb()
            qi = _to_qimage(self._frame, QtGui)
            p = QtGui.QPainter(self)
            p.fillRect(self.rect(), QtGui.QColor(NAVY_0))
            if qi is not None:
                # centred, unscaled (frame is already sized to the short side)
                x0 = (self.width() - qi.width()) // 2
                y0 = (self.height() - qi.height()) // 2
                p.drawImage(x0, y0, qi)
                if (self._wire and self._edges is not None and self._drag is None
                        and not self._fp):    # wire overlay is orbit-projected only
                    size = qi.width()
                    xy, _ = viewer3d_project(
                        self._P, viewer3d_camera(self._yaw, self._pitch),
                        self._center, self._radius, self._zoom, self._pan, size)
                    pen = QtGui.QPen(QtGui.QColor(23, 184, 166, 90)); pen.setWidthF(1.0)
                    p.setPen(pen)
                    for a, b in self._edges:
                        p.drawLine(QtCore.QPointF(x0 + xy[a, 0], y0 + xy[a, 1]),
                                   QtCore.QPointF(x0 + xy[b, 0], y0 + xy[b, 1]))
            dec = (" · preview %d pts" % self._n_drawn
                   if 0 < self._n_drawn < self._P.shape[0] else "")
            head = ("%s · %d pts%s%s"
                    % (self.info.get("kind"), self.info.get("n_points", self._P.shape[0]),
                       (" · %d faces" % self.info["n_faces"]) if self._F is not None else "",
                       dec))
            if self._fp:
                hint = (head + " · walk x%.2g   WASD=move · Q/E/Space=down/up"
                        " · Shift=fast · drag=look · wheel=speed · R=entrance · F=orbit"
                        % self._fp_speed)
            else:
                hint = (head + "   drag=orbit · wheel=zoom · shift/middle-drag=pan"
                        " · R=reset · F=walk%s"
                        % (" · W=wire" if self._edges is not None else ""))
            p.setPen(QtGui.QColor(MUTED))
            p.drawText(8, self.height() - 8, hint)
            p.end()

        # ---- interaction ---------------------------------------------------- #
        def reset_view(self):
            self._yaw, self._pitch, self._zoom = 35.0, 25.0, 1.0
            self._pan = [0.0, 0.0]
            self._repaint()

        def toggle_first_person(self):
            """F key: orbit <-> first-person walkthrough. Entering places the
            eye at the walkthrough entrance; leaving resumes the orbit camera
            untouched (its yaw/pitch/zoom/pan are never written while walking)."""
            self._fp = not self._fp
            if self._fp:
                self._fp_home()
            self._repaint()

        def _fp_home(self):
            """Walkthrough entrance: continue the current orbit line of sight —
            same yaw/pitch, eye on the scene perimeter at ``1.5 * radius`` from
            the centre, looking at the centre (the toggle reads as 'step into
            the view you were orbiting', not a camera jump)."""
            self._fp_yaw, self._fp_pitch = self._yaw, self._pitch
            cam = viewer3d_camera_fp(self._fp_yaw, self._fp_pitch)
            self._eye = self._center - cam[2] * (1.5 * self._radius)
            self._fp_speed = 1.0

        def _fp_step(self, modifiers):
            """Per-keypress walk distance: scene-proportional (radius/50) times
            the wheel speed multiplier, x4 with Shift held."""
            boost = 4.0 if modifiers & QtCore.Qt.ShiftModifier else 1.0
            return self._radius / 50.0 * self._fp_speed * boost

        def mousePressEvent(self, e):
            mode = ("pan" if (e.button() == QtCore.Qt.MiddleButton
                              or e.modifiers() & QtCore.Qt.ShiftModifier) else "orbit")
            self._drag = (mode, e.position().toPoint())

        def mouseMoveEvent(self, e):
            if self._drag is None:
                return
            mode, last = self._drag
            pos = e.position().toPoint()
            dx, dy = pos.x() - last.x(), pos.y() - last.y()
            if self._fp:
                if mode == "orbit":               # mouse-look: drag right turns right,
                    self._fp_yaw = (self._fp_yaw + 0.35 * dx) % 360.0      # drag up looks up
                    self._fp_pitch = float(np.clip(self._fp_pitch - 0.35 * dy, -89.0, 89.0))
                else:                             # strafe in the view plane (grab-the-world)
                    _fwd, right, up = viewer3d_fp_axes(self._fp_yaw, self._fp_pitch)
                    s = self._radius / 300.0
                    self._eye = self._eye - right * (dx * s) + up * (dy * s)
            elif mode == "orbit":
                self._yaw = (self._yaw + 0.5 * dx) % 360.0
                self._pitch = float(np.clip(self._pitch + 0.5 * dy, -89.0, 89.0))
            else:
                self._pan[0] += dx; self._pan[1] += dy
            self._drag = (mode, pos)
            self._repaint()

        def mouseReleaseEvent(self, e):
            self._drag = None
            self._repaint()                       # full-resolution re-render after a drag

        def wheelEvent(self, e):
            f = 1.25 if e.angleDelta().y() > 0 else 0.8
            if self._fp:
                # walking: the wheel tunes the WASD step size (HUD shows the
                # multiplier) — the view itself does not change, no re-render race
                self._fp_speed = float(np.clip(self._fp_speed * f, 0.05, 50.0))
                self._repaint()
                return
            self._zoom = float(np.clip(self._zoom * f, 0.02, 500.0))
            if self._P.shape[0] > self.DRAG_BUDGET:
                # same decimated preview as a drag; a short timer restores the
                # full-resolution render once the wheel burst ends
                self._wheeling = True
                self._wheel_timer.start()
            self._repaint()

        def _end_wheel(self):
            self._wheeling = False
            self._repaint()                       # full-resolution re-render after zooming

        def resizeEvent(self, e):
            super().resizeEvent(e)
            self._repaint()                       # frame is sized to the widget: re-render

        #: first-person movement keys -> direction in the (forward, right, up)
        #: basis of :func:`viewer3d_fp_axes` (class-level so tests can read it)
        FP_MOVES = {"W": (1, 0, 0), "S": (-1, 0, 0), "A": (0, -1, 0), "D": (0, 1, 0),
                    "E": (0, 0, 1), "Q": (0, 0, -1), "Space": (0, 0, 1)}

        def keyPressEvent(self, e):
            if e.key() == QtCore.Qt.Key_F:
                self.toggle_first_person()
                return
            if self._fp:
                name = {QtCore.Qt.Key_W: "W", QtCore.Qt.Key_S: "S",
                        QtCore.Qt.Key_A: "A", QtCore.Qt.Key_D: "D",
                        QtCore.Qt.Key_E: "E", QtCore.Qt.Key_Q: "Q",
                        QtCore.Qt.Key_Space: "Space"}.get(e.key())
                if name is not None:
                    fwd, right, up = viewer3d_fp_axes(self._fp_yaw, self._fp_pitch)
                    df, dr, du = self.FP_MOVES[name]
                    self._eye = self._eye + (fwd * df + right * dr + up * du) \
                        * self._fp_step(e.modifiers())
                    if self._P.shape[0] > self.DRAG_BUDGET:
                        # walking burst = same decimated preview as a wheel-zoom
                        # burst; full re-render shortly after the last step
                        self._wheeling = True
                        self._wheel_timer.start()
                    self._repaint()
                elif e.key() == QtCore.Qt.Key_R:
                    self._fp_home()
                    self._repaint()
                else:
                    super().keyPressEvent(e)
                return
            if e.key() == QtCore.Qt.Key_R:
                self.reset_view()
            elif e.key() == QtCore.Qt.Key_W and self._edges is not None:
                self._wire = not self._wire
                self._repaint()
            else:
                super().keyPressEvent(e)
    return Viewer3D


#: Strong references to top-level viewers opened by :func:`disp_points3d` /
#: :func:`disp_mesh3d`. Under an EXISTING QApplication the call returns
#: non-blocking; a caller that discards the return value must still get a live
#: window (matplotlib-figure semantics), so the widget is registered here and
#: removed again when its window closes (event filter below).
_DISP3D_KEEPALIVE = []


def _disp3d_can_create_app():
    """Whether creating a QApplication is plausibly safe (Qt ABORTS the process
    when no display/platform plugin is available, so guessing wrong is fatal):
    an explicit ``QT_QPA_PLATFORM`` counts as the user's choice; Windows/macOS
    always have a display server; other unixes need DISPLAY/WAYLAND_DISPLAY."""
    if os.environ.get("QT_QPA_PLATFORM"):
        return True
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _disp3d_viewer(kind, *args, title=None, parent=None, block=True):
    """Shared implementation of the public disp_* 3-D API (single code path).

    Headless-safe contract: with no QApplication AND no way to safely create
    one (offscreen platform, or no display detected — see
    :func:`_disp3d_can_create_app`) the call records what WOULD have been shown
    and returns that info dict (no window, no abort — CI/tests). With a
    running QApplication (Studio, tests) it shows the window, registers it in
    ``_DISP3D_KEEPALIVE`` (so discarding the return value does NOT let GC close
    it) and returns the ``Viewer3D`` widget non-blocking. With no QApplication
    on a real display it creates one and — with ``block=True`` (default) —
    runs a nested ``app.exec()`` until the window closes (deliberate
    matplotlib-``show`` semantics for plain scripts); pass ``block=False`` to
    return immediately (the caller then owns running the event loop)."""
    try:
        from PySide6 import QtWidgets, QtGui, QtCore
    except Exception:
        return {"kind": kind, "shown": False, "reason": "PySide6 unavailable"}
    app = QtWidgets.QApplication.instance()
    offscreen = os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    if app is None and (offscreen or not _disp3d_can_create_app()):
        n = int(np.asarray(args[0], np.float64).reshape(-1, 3).shape[0])
        reason = "offscreen, no app" if offscreen else "no display, no app"
        return {"kind": kind, "shown": False, "n_points": n, "reason": reason}
    created = False
    if app is None:
        app = QtWidgets.QApplication([])
        created = True
    w = _viewer3d_class(QtWidgets, QtGui, QtCore)(parent)
    if kind == "mesh":
        w.set_mesh(args[0], args[1])
    else:
        w.set_points(args[0], colors=args[1] if len(args) > 1 else None)
    w.setWindowTitle(title or ("Fullseye Studio - 3D viewer (%s)" % kind))
    w.resize(640, 560)

    class _CloseWatch(QtCore.QObject):
        """Drops the keepalive reference when the viewer window closes."""
        def eventFilter(self, obj, ev):
            if ev.type() == QtCore.QEvent.Close:
                try:
                    _DISP3D_KEEPALIVE.remove(obj)
                except ValueError:
                    pass
            return False

    w.installEventFilter(_CloseWatch(w))          # parented to w — lives as long as w
    _DISP3D_KEEPALIVE.append(w)
    w.show()
    w.info["shown"] = True
    if created and not offscreen and block:
        app.exec()                                # standalone script: block until closed
    return w


def disp_points3d(points, colors=None, title=None, parent=None, block=True):
    """Open the interactive 3-D viewer on a point cloud (HALCON
    ``disp_object_model_3d`` workalike; the Studio program-directive
    ``disp_points3d ('file')`` and this function share one viewer). *points* is
    (n, 3); *colors* optional (n, 3) in [0, 1]. See :func:`_disp3d_viewer` for
    the headless-safe return contract. Under an existing QApplication the
    window stays open even if the return value is discarded (module keepalive,
    released on close). From a plain script (no QApplication) the call blocks
    in a nested event loop until the window closes — matplotlib-``show``
    semantics; pass ``block=False`` to opt out and drive the loop yourself."""
    return _disp3d_viewer("points", points, colors, title=title, parent=parent,
                          block=block)


def disp_mesh3d(V, F, title=None, parent=None, block=True):
    """Open the interactive 3-D viewer on a triangle mesh (lambert vertex
    shading, ``W`` toggles wireframe). Same contract as :func:`disp_points3d`
    (keepalive registry, ``block=`` opt-out)."""
    return _disp3d_viewer("mesh", V, F, title=title, parent=parent, block=block)


def _group(QtWidgets, title, inner_layout):
    """A titled section card (QGroupBox) wrapping *inner_layout*."""
    g = QtWidgets.QGroupBox(title)
    g.setLayout(inner_layout)
    return g


_ICON_CACHE = {}


def _icon(QtGui, QtCore, name, color=TEXT, px=40):
    """Crisp monochrome line-icon (no asset files) drawn on a 20×20 grid.

    Returns a themed :class:`QIcon` so the toolbars can be **icon-only** (no text
    labels — tooltips carry the meaning). Rendered at 2× and marked HiDPI so it
    stays sharp when Qt scales it down to an 18 px button icon. Cached per
    (name, color, px) since the same glyph is reused across many buttons."""
    key = (name, color, px)
    hit = _ICON_CACHE.get(key)
    if hit is not None:
        return hit
    r = 2
    pm = QtGui.QPixmap(px * r, px * r)
    pm.setDevicePixelRatio(r)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    s = px / 20.0
    col = QtGui.QColor(color)
    pen = QtGui.QPen(col); pen.setWidthF(1.8 * s)
    pen.setCapStyle(QtCore.Qt.RoundCap); pen.setJoinStyle(QtCore.Qt.RoundJoin)
    p.setPen(pen); p.setBrush(QtCore.Qt.NoBrush)

    def P(x, y):
        return QtCore.QPointF(x * s, y * s)

    def L(x1, y1, x2, y2):
        p.drawLine(P(x1, y1), P(x2, y2))

    def rect(x, y, w, h, rad=0.0):
        rr = QtCore.QRectF(x * s, y * s, w * s, h * s)
        p.drawRoundedRect(rr, rad * s, rad * s) if rad else p.drawRect(rr)

    def ell(x, y, w, h, fill=False):
        if fill:
            p.setBrush(col)
        p.drawEllipse(QtCore.QRectF(x * s, y * s, w * s, h * s))
        p.setBrush(QtCore.Qt.NoBrush)

    def poly(pts, fill=False, close=False):
        pp = QtGui.QPolygonF([P(a, b) for a, b in pts])
        if fill:
            p.setBrush(col); p.drawPolygon(pp); p.setBrush(QtCore.Qt.NoBrush)
        elif close:
            p.drawPolygon(pp)
        else:
            p.drawPolyline(pp)

    def arc(x, y, w, h, start, span):
        p.drawArc(QtCore.QRectF(x * s, y * s, w * s, h * s), int(start * 16), int(span * 16))

    def glyph(txt, size=11):
        f = p.font(); f.setPixelSize(int(size * s)); f.setBold(True); p.setFont(f)
        p.drawText(QtCore.QRectF(0, 0, px, px), QtCore.Qt.AlignCenter, txt)

    if name == "open":                                   # folder
        poly([(3, 15), (3, 7), (8, 7), (9.5, 9), (17, 9), (17, 15)], close=True)
    elif name == "save":                                 # floppy disk
        rect(4, 4, 12, 12, 1.2); rect(7, 4, 4.5, 3.6); rect(6.5, 10.5, 7, 4.5)
    elif name == "image":                                # framed picture
        rect(4, 5, 12, 10, 1.2); ell(6.3, 7, 2.2, 2.2)
        poly([(5, 14), (9, 9.5), (11, 12), (13, 10), (15, 14)])
    elif name == "demo":                                 # sparkle (synthetic)
        poly([(8, 3), (9.2, 6.8), (13, 8), (9.2, 9.2), (8, 13), (6.8, 9.2), (3, 8), (6.8, 6.8)], fill=True)
        poly([(15, 12), (15.7, 14.3), (18, 15), (15.7, 15.7), (15, 18), (14.3, 15.7), (12, 15), (14.3, 14.3)], fill=True)
    elif name == "play":                                 # single triangle
        poly([(7, 5), (7, 15), (15, 10)], fill=True)
    elif name == "playplay":                             # run-all: two triangles
        poly([(5, 5), (5, 15), (11, 10)], fill=True); poly([(11, 5), (11, 15), (17, 10)], fill=True)
    elif name == "playone":                              # run-once: play in circle
        ell(3, 3, 14, 14); poly([(8, 7), (8, 13), (13.5, 10)], fill=True)
    elif name == "step":                                 # skip-forward: play + bar
        poly([(6, 5), (6, 15), (13, 10)], fill=True); L(15, 5, 15, 15)
    elif name == "reset":                                # skip-back: bar + left triangle
        L(5, 5, 5, 15); poly([(15, 5), (15, 15), (8, 10)], fill=True)
    elif name == "up":                                   # chevron up
        poly([(5, 12.5), (10, 7), (15, 12.5)])
    elif name == "down":                                 # chevron down
        poly([(5, 7.5), (10, 13), (15, 7.5)])
    elif name == "trash":                                # trash can
        L(4, 6, 16, 6); rect(8, 3.6, 4, 2.2, 0.6)
        poly([(5.6, 6), (6.6, 16.2), (13.4, 16.2), (14.4, 6)])
        L(8.6, 8.4, 8.6, 14); L(11.4, 8.4, 11.4, 14)
    elif name == "zin":                                  # magnifier +
        ell(4, 4, 9, 9); L(12, 12, 16.5, 16.5); L(8.5, 6, 8.5, 11); L(6, 8.5, 11, 8.5)
    elif name == "zout":                                 # magnifier −
        ell(4, 4, 9, 9); L(12, 12, 16.5, 16.5); L(6, 8.5, 11, 8.5)
    elif name == "fit":                                  # frame corners (fit to window)
        L(4, 7, 4, 4); L(4, 4, 7, 4); L(16, 7, 16, 4); L(16, 4, 13, 4)
        L(4, 13, 4, 16); L(4, 16, 7, 16); L(16, 13, 16, 16); L(16, 16, 13, 16)
    elif name == "actual":                               # 1:1 = square + centre pixel
        rect(6, 6, 8, 8, 1.0); ell(9.2, 9.2, 1.6, 1.6, fill=True)
    elif name == "export":                               # up-out of tray (share/export)
        poly([(4, 11), (4, 16), (16, 16), (16, 11)]); L(10, 3.5, 10, 12)
        poly([(7, 6.5), (10, 3.5), (13, 6.5)])
    elif name == "apply":                                # check mark
        poly([(4.5, 10.5), (8.5, 14.5), (16, 5)])
    elif name == "sync":                                 # circular arrows
        arc(5, 5, 10, 10, 55, 250); poly([(14.5, 4.5), (15.2, 8), (11.8, 7)])
    elif name == "cube":                                 # isometric cube (3-D)
        poly([(10, 3.5), (16, 7), (10, 10.5), (4, 7)], close=True)
        L(4, 7, 4, 13.5); L(16, 7, 16, 13.5); L(10, 10.5, 10, 16.5)
        L(4, 13.5, 10, 16.5); L(16, 13.5, 10, 16.5)
    elif name == "plus":                                 # add
        L(10, 5, 10, 15); L(5, 10, 15, 10)
    elif name == "help":                                 # circled question mark
        ell(4, 4, 12, 12); glyph("?", 10)
    elif name == "eye":                                  # perception / view
        poly([(4, 10), (7, 6.5), (13, 6.5), (16, 10)]); poly([(4, 10), (7, 13.5), (13, 13.5), (16, 10)])
        ell(8.3, 8, 3.4, 3.4, fill=True)
    elif name == "more":                                 # vertical ellipsis (popup menu)
        ell(9.2, 4.2, 1.7, 1.7, fill=True); ell(9.2, 9.2, 1.7, 1.7, fill=True); ell(9.2, 14.2, 1.7, 1.7, fill=True)
    elif name == "grid":                                 # sample gallery
        rect(4, 4, 5, 5, 0.8); rect(11, 4, 5, 5, 0.8); rect(4, 11, 5, 5, 0.8); rect(11, 11, 5, 5, 0.8)
    else:                                                # honest fallback: a dot
        ell(8.5, 8.5, 3, 3, fill=True)
    p.end()
    ic = QtGui.QIcon(pm)
    _ICON_CACHE[key] = ic
    return ic


# --------------------------------------------------------------------------- #
# Tooltip / hint + guide localisation, and per-operator HTML help.              #
# The DATA lives in files under studio_assets/ (edit there, not here):          #
#   • studio_assets/i18n.json      tooltips + quick-guide, per language          #
#   • studio_assets/op_help/*.html rich per-operator help (args/usage/samples)   #
# New languages are added in i18n.json ('languages' map) with NO code change;    #
# English is always the base/fallback. Missing entries fall back gracefully.     #
# --------------------------------------------------------------------------- #
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_assets")


def _load_i18n():
    try:
        with open(os.path.join(_ASSETS, "i18n.json"), encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    langs = dict(data.get("languages") or {})
    if "en" not in langs:                      # English is always available as the base
        langs = {"en": "English", **langs}
    return (langs, data.get("tooltips", {}) or {}, data.get("guide", {}) or {"en": ""},
            data.get("strings", {}) or {})


LANGUAGES, TOOLTIPS_I18N, HELP_I18N, STRINGS_I18N = _load_i18n()

#: current UI language (module-level so `tr` works in any nested scope; the value is
#: switched by build_window's apply_language and mirrors win._lang).
_UI_LANG = {"code": "en"}


def tr(text):
    """UI 文字列を i18n テーブル(studio_assets/i18n.json の 'strings')で現在言語へ。

    英語がキー=ベース言語(tooltips と同じ規約)。テーブルに無い文字列・未訳の言語は
    **英語のまま**(graceful fallback — 壊れた翻訳より原文)。翻訳の追加はコード変更
    なしで i18n.json だけ(ユーザー仕様 2026-08-30: 対訳はテーブルとして一箇所に)。"""
    if _UI_LANG["code"] == "en" or not text:
        return text
    return STRINGS_I18N.get(text, {}).get(_UI_LANG["code"], text)


def op_help_html(name, lang="en", meta=None, dim="2d"):
    """Rich HTML help for one operator. Lookup order (see studio_assets/op_help/):
      1. op_help/<name>.<lang>.html   language-specific
      2. op_help/<name>.html          default (English)
      3. a generated card from the op's registry metadata (no file needed).
    The HTML may use anchors ``op:<name>`` (jump to a related op) and
    ``sample:<url-encoded ops>`` / ``run:<...>`` (load/run a sample pipeline).

    ``dim="3d"`` delegates to :func:`op_help_html_3d` (point-cloud / mesh / volume
    modality, looked up under op_help/3d/) so a single dim-aware entry point serves
    both operator registries — 2-D and 3-D op names can collide (e.g. ``fill_holes``),
    so the modality must be passed, not inferred from the name."""
    if dim == "3d":
        return op_help_html_3d(name, meta)
    base = os.path.join(_ASSETS, "op_help")
    for fn in ("%s.%s.html" % (name, lang), "%s.html" % name):
        p = os.path.join(base, fn)
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return f.read()
            except Exception:
                break
    m = meta or {}
    if m.get("backend") == "general":
        # general-algorithm tier: a seq/scalar op run via the CLI, NOT an image op with a/b knobs.
        # (op_signature_detail / op_tooltip / add_op / apply_program already guard on this; the help
        # CARD was the one path that fell through to the false "Two knobs a, b" text — review finding.)
        def _esc(s):
            return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        sig = _esc(op_signature_detail(m)).replace("\n", "<br>")
        desc = _esc(m.get("desc") or "")
        return ("<h2 style='color:#f5a524;margin:0 0 4px 0'>%s "
                "<span style='color:#8b91a0;font-size:11px'>· general-algorithm tier</span></h2>"
                "<p style='color:#8b91a0'><b>%s</b></p>"
                "<p style='font-family:monospace;font-size:11px'>%s</p>"
                "<p style='color:#8b91a0;font-size:11px'>A <b>seq/scalar</b> op — not an image "
                "operator: it has no a/b knobs and does not enter the pipeline. Run it from the CLI "
                "(<code>py -3.11 imgevolve.py algo run %s --seq ...</code>) or via "
                "<code>fullseye.run_algo(\"%s\", [...])</code>.</p>"
                % (_esc(name), desc, sig, _esc(name), _esc(name)))
    halcon = (" · HALCON: %s" % m["halcon"]) if m.get("halcon") else ""
    sorts = "%s → %s" % (m.get("in_sort", "?"), m.get("out_sort", "?"))
    return ("<h2 style='color:#f5a524;margin:0 0 4px 0'>%s "
            "<span style='color:#8b91a0;font-size:11px'>· %s%s</span></h2>"
            "<p style='color:#8b91a0'><b>%s</b></p>"
            "<p>Two knobs <b>a</b>, <b>b</b> in [0,1] tune this operator; hover the knob "
            "sliders for their live values.</p>"
            "<p style='color:#8b91a0;font-size:11px'>No authored help yet — add "
            "<code>studio_assets/op_help/%s.html</code> (args / usage / sample code / "
            "related-op links). See op_help/README.md.</p>"
            % (name, m.get("category", "operator"), halcon, sorts, name))


def op_help_html_3d(name, meta=None):
    """Rich HTML help for one 3-D operator (point-cloud / mesh / volume modality).

    Reads ``op_help/3d/<name>.html`` — bulk-generated from the Markdown corpus
    (``docs/ops/3d/**/*.md``) by ``tools/opdocs.py`` — and falls back to a small card
    built from the ops3d registry metadata if that file is absent. Kept separate from
    :func:`op_help_html` because 2-D and 3-D op names can collide (e.g. ``fill_holes``),
    so the two help sets live in different directories and are looked up by modality."""
    p = os.path.join(_ASSETS, "op_help", "3d", "%s.html" % name)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass

    def _e(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    m = meta or {}
    ins = m.get("in", "?")
    ins = " × ".join(ins) if isinstance(ins, (list, tuple)) else ins
    return ("<h2 style='color:#f5a524;margin:0 0 4px 0'>%s "
            "<span style='color:#8b91a0;font-size:11px'>· %s · 3D</span></h2>"
            "<p style='color:#8b91a0'><b>%s → %s</b></p>"
            "<p>%s</p>"
            "<p style='color:#8b91a0;font-size:11px'>No authored help yet — run "
            "<code>py -3.11 tools/opdocs.py html</code> to generate 3-D help from "
            "<code>docs/ops/3d/</code>.</p>"
            % (_e(name), _e(m.get("category", "operator")), _e(ins),
               _e(m.get("out", "?")), _e(m.get("doc") or "")))


def _python_highlighter_class(QtGui, QtCore):
    """Python syntax-highlighter factory for the Python Editor (keywords / strings /
    comments / numbers / def-class names / decorators). Triple-quoted
    strings are tracked across blocks with ``setCurrentBlockState`` (1 = inside
    ``'''``, 2 = inside ``\"\"\"``) so editing inside a docstring re-highlights.
    Known honest limitation: an opener that itself sits inside a one-line string
    or comment is still treated as an opener (lightweight lexer, not a parser)."""
    import keyword

    def _fmt(color, bold=False, italic=False):
        f = QtGui.QTextCharFormat()
        f.setForeground(QtGui.QColor(color))
        if bold:
            f.setFontWeight(QtGui.QFont.Bold)
        if italic:
            f.setFontItalic(True)
        return f

    class PythonHighlighter(QtGui.QSyntaxHighlighter):
        def __init__(self, doc):
            super().__init__(doc)
            self._str_fmt = _fmt("#9ece6a")
            self._rules = [
                (re.compile(r"\b(?:%s)\b" % "|".join(keyword.kwlist)),
                 _fmt("#e0af68", bold=True)),                                # keywords
                (re.compile(r"\b(?:self|cls)\b"), _fmt("#ff9e64")),
                (re.compile(r"\b\d+(?:\.\d*)?(?:[eE][+-]?\d+)?\b"), _fmt("#ff9e64")),
                (re.compile(r"(?:(?<=\bdef\s)|(?<=\bclass\s))\w+"),
                 _fmt("#7dcfff", bold=True)),
                (re.compile(r"@\w+(?:\.\w+)*"), _fmt("#bb9af7")),            # decorators
                (re.compile(r"'[^'\n]*'|\"[^\"\n]*\""), self._str_fmt),      # 1-line strings
                (re.compile(r"#[^\n]*"), _fmt("#565f89", italic=True)),      # comments
            ]

        def highlightBlock(self, text):
            for rx, fmt in self._rules:
                for m in rx.finditer(text):
                    self.setFormat(m.start(), m.end() - m.start(), fmt)
            # -- triple-quoted strings span blocks (they overwrite the rule pass) --
            self.setCurrentBlockState(0)
            pos, state = 0, max(0, self.previousBlockState())
            while pos <= len(text):
                if state:
                    quote = "'''" if state == 1 else '"""'
                    end = text.find(quote, pos)
                    if end < 0:
                        self.setFormat(pos, len(text) - pos, self._str_fmt)
                        self.setCurrentBlockState(state)
                        return
                    self.setFormat(pos, end + 3 - pos, self._str_fmt)
                    pos, state = end + 3, 0
                else:
                    cands = [(i, st) for i, st in ((text.find("'''", pos), 1),
                                                   (text.find('"""', pos), 2)) if i >= 0]
                    if not cands:
                        return
                    pos, state = min(cands)

    return PythonHighlighter


def _code_editor_class(QtWidgets, QtGui, QtCore):
    """Editable Python code-editor widget factory for the Python Editor: monospace
    font, a line-number gutter, Tab -> 4 spaces, and auto-indent on Enter (copies
    the previous line's leading whitespace, one extra level after a trailing ':').
    Kept separate from :class:`ProgramEditor`, whose gutter carries pipeline-only
    state (breakpoints / per-stage timings) that has no meaning for a script."""

    class _Gutter(QtWidgets.QWidget):
        def __init__(self, editor):
            super().__init__(editor)
            self._editor = editor

        def sizeHint(self):
            return QtCore.QSize(self._editor.gutter_width(), 0)

        def paintEvent(self, ev):
            self._editor.paint_gutter(ev)

    class CodeEditor(QtWidgets.QPlainTextEdit):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
            try:                                   # System settings: editor font size
                pt = int(QtCore.QSettings("Fullseye", "Studio").value("ui/mono_font_pt", 10))
            except (TypeError, ValueError):
                pt = 10
            f = QtGui.QFont("Consolas"); f.setStyleHint(QtGui.QFont.Monospace)
            f.setPointSize(max(6, min(pt, 32)))
            self.setFont(f)
            # the app-level QSS also styles QPlainTextEdit fonts; a widget-level rule
            # outranks it so the configured size actually takes effect
            self.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace; "
                               "font-size:%dpt;" % max(6, min(pt, 32)))
            self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
            self._gutter = _Gutter(self)
            self.blockCountChanged.connect(lambda _n: self._update_gutter_width())
            self.updateRequest.connect(self._update_gutter)
            self._update_gutter_width()

        def gutter_width(self):
            digits = max(2, len(str(max(1, self.blockCount()))))
            return 14 + self.fontMetrics().horizontalAdvance("9") * digits

        def _update_gutter_width(self):
            self.setViewportMargins(self.gutter_width(), 0, 0, 0)

        def _update_gutter(self, rect, dy):
            if dy:
                self._gutter.scroll(0, dy)
            else:
                self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
            if rect.contains(self.viewport().rect()):
                self._update_gutter_width()

        def resizeEvent(self, ev):
            super().resizeEvent(ev)
            cr = self.contentsRect()
            self._gutter.setGeometry(QtCore.QRect(cr.left(), cr.top(),
                                                  self.gutter_width(), cr.height()))

        def paint_gutter(self, ev):
            p = QtGui.QPainter(self._gutter)
            p.fillRect(ev.rect(), QtGui.QColor("#12141b"))
            p.setPen(QtGui.QColor("#565f89"))
            block = self.firstVisibleBlock()
            n = block.blockNumber()
            top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            while block.isValid() and top <= ev.rect().bottom():
                bh = self.blockBoundingRect(block).height()
                if block.isVisible() and top + bh >= ev.rect().top():
                    p.drawText(0, int(top), self._gutter.width() - 8,
                               self.fontMetrics().height(),
                               QtCore.Qt.AlignRight, str(n + 1))
                block = block.next(); top += bh; n += 1

        def keyPressEvent(self, ev):
            if ev.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                cur = self.textCursor()
                line = cur.block().text()[: cur.positionInBlock()]
                indent = line[: len(line) - len(line.lstrip())]
                if line.rstrip().endswith(":"):
                    indent += "    "
                super().keyPressEvent(ev)
                if indent:
                    self.insertPlainText(indent)
                return
            if ev.key() == QtCore.Qt.Key_Tab and not ev.modifiers():
                self.insertPlainText("    ")
                return
            super().keyPressEvent(ev)

    return CodeEditor


def _program_editor_class(QtWidgets, QtGui, QtCore):
    """A HDevelop/VS-style program editor widget factory.

    Features: a line-number + breakpoint gutter (click to toggle a breakpoint),
    per-line execution timing shown in the gutter, a current-execution-line
    highlight, and op-name autocomplete (IntelliSense). The editable text is the
    pipeline as one ``op a b`` statement per line; ``#`` starts a comment."""

    class _Gutter(QtWidgets.QWidget):
        def __init__(self, editor):
            super().__init__(editor)
            self._editor = editor

        def sizeHint(self):
            return QtCore.QSize(self._editor.gutter_width(), 0)

        def paintEvent(self, ev):
            self._editor.paint_gutter(ev)

        def mousePressEvent(self, ev):
            self._editor.gutter_click(ev)

    class ProgramEditor(QtWidgets.QPlainTextEdit):
        BREAK = "#e5484d"

        def __init__(self, words=(), parent=None):
            super().__init__(parent)
            self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
            f = QtGui.QFont("Consolas"); f.setStyleHint(QtGui.QFont.Monospace); f.setPointSize(10)
            self.setFont(f)
            self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
            self.breakpoints = set()          # 1-based line numbers
            self.timings = {}                 # 1-based line -> milliseconds (float)
            self._exec_line = -1
            self._gutter = _Gutter(self)
            self.blockCountChanged.connect(lambda _n: self._update_gutter_width())
            self.updateRequest.connect(self._update_gutter)
            self.cursorPositionChanged.connect(self._highlight)
            self._update_gutter_width()
            self._highlight()
            # --- IntelliSense: op-name completion popup ---
            self._completer = QtWidgets.QCompleter(sorted(set(words)), self)
            self._completer.setWidget(self)
            self._completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            self._completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            self._completer.activated.connect(self._insert_completion)

        # -- gutter geometry / painting --
        def gutter_width(self):
            digits = max(2, len(str(max(1, self.blockCount()))))
            num = self.fontMetrics().horizontalAdvance("9") * digits
            return 16 + num + 62          # dot + number + "  123.4ms"

        def _update_gutter_width(self):
            self.setViewportMargins(self.gutter_width(), 0, 0, 0)

        def _update_gutter(self, rect, dy):
            if dy:
                self._gutter.scroll(0, dy)
            else:
                self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
            if rect.contains(self.viewport().rect()):
                self._update_gutter_width()

        def resizeEvent(self, ev):
            super().resizeEvent(ev)
            cr = self.contentsRect()
            self._gutter.setGeometry(QtCore.QRect(cr.left(), cr.top(),
                                                  self.gutter_width(), cr.height()))

        def paint_gutter(self, ev):
            p = QtGui.QPainter(self._gutter)
            p.fillRect(ev.rect(), QtGui.QColor("#12141b"))
            block = self.firstVisibleBlock()
            n = block.blockNumber()
            top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            bottom = top + self.blockBoundingRect(block).height()
            fm = self.fontMetrics()
            w = self._gutter.width()
            numw = 16 + fm.horizontalAdvance("9") * max(2, len(str(max(1, self.blockCount()))))
            while block.isValid() and top <= ev.rect().bottom():
                if block.isVisible() and bottom >= ev.rect().top():
                    ln = n + 1
                    if ln in self.breakpoints:      # breakpoint dot
                        p.setBrush(QtGui.QColor(self.BREAK)); p.setPen(QtCore.Qt.NoPen)
                        p.drawEllipse(3, int(top) + (fm.height() - 8) // 2, 8, 8)
                    p.setPen(QtGui.QColor("#e5484d" if ln == self._exec_line else "#6b7280"))
                    p.drawText(0, int(top), numw, fm.height(),
                               QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, str(ln))
                    ms = self.timings.get(ln)
                    if ms is not None:              # per-line execution time
                        p.setPen(QtGui.QColor("#17b8a6"))
                        p.drawText(0, int(top), w - 4, fm.height(),
                                   QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, "%.1fms" % ms)
                block = block.next()
                top = bottom
                bottom = top + self.blockBoundingRect(block).height()
                n += 1
            p.end()

        def gutter_click(self, ev):
            block = self.firstVisibleBlock()
            n = block.blockNumber()
            top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            bottom = top + self.blockBoundingRect(block).height()
            y = ev.position().y() if hasattr(ev, "position") else ev.y()
            while block.isValid():
                if top <= y <= bottom:
                    ln = n + 1
                    self.breakpoints.symmetric_difference_update({ln})
                    self._gutter.update()
                    return
                block = block.next(); n += 1
                top = bottom; bottom = top + self.blockBoundingRect(block).height()

        # -- highlights --
        def set_exec_line(self, ln):
            self._exec_line = int(ln)
            self._highlight()
            self._gutter.update()

        def clear_exec(self):
            self._exec_line = -1
            self.timings = {}
            self._highlight(); self._gutter.update()

        def set_timings(self, timings):
            self.timings = dict(timings or {})
            self._gutter.update()

        def _highlight(self):
            sels = []
            cur = QtWidgets.QTextEdit.ExtraSelection()
            cur.format.setBackground(QtGui.QColor("#1f2430"))
            cur.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            cur.cursor = self.textCursor(); cur.cursor.clearSelection()
            sels.append(cur)
            if self._exec_line > 0:
                doc = self.document()
                blk = doc.findBlockByNumber(self._exec_line - 1)
                if blk.isValid():
                    ex = QtWidgets.QTextEdit.ExtraSelection()
                    ex.format.setBackground(QtGui.QColor("#14342f"))
                    ex.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
                    c = self.textCursor(); c.setPosition(blk.position()); c.clearSelection()
                    ex.cursor = c
                    sels.append(ex)
            self.setExtraSelections(sels)

        # -- autocomplete --
        def _text_under_cursor(self):
            c = self.textCursor(); c.select(QtGui.QTextCursor.WordUnderCursor)
            return c.selectedText()

        def _insert_completion(self, completion):
            c = self.textCursor()
            extra = len(completion) - len(self._completer.completionPrefix())
            c.movePosition(QtGui.QTextCursor.Left); c.movePosition(QtGui.QTextCursor.EndOfWord)
            c.insertText(completion[len(completion) - extra:])
            self.setTextCursor(c)

        def keyPressEvent(self, ev):
            comp = self._completer
            if comp.popup().isVisible() and ev.key() in (
                    QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return, QtCore.Qt.Key_Escape,
                    QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab):
                ev.ignore(); return
            super().keyPressEvent(ev)
            prefix = self._text_under_cursor()
            if len(prefix) >= 2 and prefix[0].isalpha():
                if prefix != comp.completionPrefix():
                    comp.setCompletionPrefix(prefix)
                    comp.popup().setCurrentIndex(comp.completionModel().index(0, 0))
                cr = self.cursorRect()
                cr.setWidth(comp.popup().sizeHintForColumn(0)
                            + comp.popup().verticalScrollBar().sizeHint().width())
                comp.complete(cr)
            else:
                comp.popup().hide()

    return ProgramEditor


def build_window(model=None):
    """Construct (but do not exec) the main window. Returns (window, model).

    The window is a QMainWindow with a menu bar (all actions + keyboard
    shortcuts), a branded toolbar, a status bar (hover read-out + transient
    messages), and three titled panels: Operators, Pipeline/Knobs, and the
    Image/Perception/Inspector column."""
    from PySide6 import QtWidgets, QtGui, QtCore

    def _tbtn(icon_name, tip, *, accent=False, menu=None, w=30):
        """A compact **icon-only** tool button (no text label — the tooltip and
        accessibleName carry the meaning). ``menu`` attaches a popup so rarely-used
        actions live behind one small button instead of a row of wide ones."""
        b = QtWidgets.QToolButton()
        b.setIcon(_icon(QtGui, QtCore, icon_name, INK if accent else TEXT))
        b.setIconSize(QtCore.QSize(18, 18))
        b.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        b.setToolTip(tip); b.setAccessibleName(tip)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setFixedSize(w, 28)
        if accent:
            b.setProperty("accent", True)
        if menu is not None:
            b.setMenu(menu)
            b.setPopupMode(QtWidgets.QToolButton.InstantPopup)
            b.setFixedSize(w + 8, 28)                     # room for the ▾ arrow
        return b

    model = model or PipelineModel(demo_image())

    class StudioWindow(QtWidgets.QMainWindow):
        """Main window that refuses to close on unsaved pipeline edits.

        ``close_guard`` is installed below; it returns False to veto the close."""
        close_guard = None

        def closeEvent(self, ev):
            guard = self.close_guard
            if guard is not None and not guard():
                ev.ignore()
                return
            try:                              # remember window position + panel layout
                if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
                    s = QtCore.QSettings("Fullseye", "Studio")
                    s.setValue("geometry", self.saveGeometry())
                    s.setValue("windowState", self.saveState())
                    s.setValue("layout_version", "3")
            except Exception:
                pass
            ev.accept()

        # -- drag-and-drop: drop an image or a pipeline .json onto the window to load it --
        drop_handler = None

        def dragEnterEvent(self, ev):
            md = ev.mimeData()
            if self.drop_handler is not None and md.hasUrls() \
                    and any(u.isLocalFile() for u in md.urls()):
                ev.acceptProposedAction()
            else:
                ev.ignore()

        def dropEvent(self, ev):
            md = ev.mimeData()
            paths = ([u.toLocalFile() for u in md.urls() if u.isLocalFile()]
                     if md.hasUrls() else [])
            if self.drop_handler is not None and paths:
                self.drop_handler(paths)
                ev.acceptProposedAction()
            else:
                ev.ignore()

    win = StudioWindow()
    win.setWindowTitle("Fullseye Studio")
    win.setAcceptDrops(True)
    win.resize(1320, 860)
    win.setStyleSheet(THEME)
    if os.path.exists(_ICON_PATH):
        win.setWindowIcon(QtGui.QIcon(_ICON_PATH))

    # ---- actions (keyboard-first; wired to the closures at the end) ---------- #
    def _act(text, shortcut=None, tip=None):
        a = QtGui.QAction(text, win)
        if shortcut:
            a.setShortcut(QtGui.QKeySequence(shortcut))
        if tip:
            a.setToolTip(tip); a.setStatusTip(tip)
        return a

    act_open_img = _act("Open image…", "Ctrl+O", "Load an image file as the base frame")
    act_demo = _act("Synthetic demo", None, "Load the built-in synthetic demo scene")
    act_save_res = _act("Save result…", "Ctrl+S", "Save the displayed result as a PNG")
    act_copy_res = _act("Copy result image", None, "Copy the displayed result image to the clipboard")
    act_open_pipe = _act("Open pipeline…", "Ctrl+Shift+O", "Load a pipeline from JSON")
    act_save_pipe = _act("Save pipeline…", "Ctrl+Shift+S", "Save the pipeline to JSON")
    act_export = _act("Export…", "Ctrl+E", "Export as an --ops string and Python code")
    act_quit = _act("Quit", "Ctrl+Q", "Close Fullseye Studio")
    act_remove = _act("Remove stage", "Del", "Remove the selected pipeline stage")
    act_up = _act("Move stage up", "Ctrl+Up", "Move the selected stage earlier")
    act_down = _act("Move stage down", "Ctrl+Down", "Move the selected stage later")
    act_clear = _act("Clear pipeline", "Ctrl+Shift+Backspace", "Remove all stages")
    act_dup = _act("Duplicate stage", "Ctrl+D", "Insert a copy of the selected stage after it")
    act_top = _act("Move stage to top", "Ctrl+Shift+Up", "Move the selected stage to the front")
    act_bottom = _act("Move stage to bottom", "Ctrl+Shift+Down", "Move the selected stage to the end")
    act_focus_search = _act("Focus operator search", "Ctrl+F", "Jump to the operator search box")
    act_undo = _act("Undo", "Ctrl+Z", "Undo the last pipeline edit")
    act_redo = _act("Redo", "Ctrl+Shift+Z", "Redo the last undone pipeline edit")
    act_undo.setEnabled(False); act_redo.setEnabled(False)
    act_zin = _act("Zoom in", "Ctrl+=", "Zoom the image in")
    act_zout = _act("Zoom out", "Ctrl+-", "Zoom the image out")
    act_fit = _act("Fit to window", "Ctrl+0", "Fit the image to the view")
    act_11 = _act("Actual size (1:1)", "Ctrl+1", "Reset zoom to 1:1")
    act_3d = _act("3D surface", "Ctrl+3", "Open a rotatable 3-D surface of the result")
    act_reset = _act("Reset to start", "Home", "Show the raw image (before stage 1)")
    act_step = _act("Step forward", "Ctrl+Right", "Advance one pipeline stage")
    act_runall = _act("Run all", "Ctrl+Return", "Show the final pipeline result")
    act_holdout = _act("Validate on holdout…", "Ctrl+H",
                       "Run the current pipeline over a folder of validation images and report results")
    act_palette = _act("Command palette…", "Ctrl+P", "Run any operator or action by name")
    act_featins = _act("Feature inspection…", "Ctrl+F5",
                       "Per-region / per-cluster feature table with two-way highlight "
                       "(rows ↔ image / 3-D view)")
    act_viewer3d = _act("3D viewer…", "Ctrl+4",
                        "Open the interactive 3-D viewer (point cloud / mesh file, "
                        "orbit / zoom / pan)")
    act_shortcuts = _act("Keyboard shortcuts", "F1", "Show all keyboard shortcuts")
    act_op_help = _act("Operator reference…", "Shift+F1", "Browse every operator with its sorts + HALCON alias")
    act_samples = _act("Samples & code…", None, "Load a sample pipeline and see its code")
    act_about = _act("About Fullseye Studio", None, "About this application")

    # Menu bar — standard IDE semantics, one home per concern (simple + multifunctional):
    # File = document I/O, Edit = pipeline-stage edits, View = display, Run = execution,
    # Window = panels/graphics/layout (submenus, not a flat wall), Tools = cross-cutting,
    # Help = reference. Display/screen concerns live under View, never File.
    mb = win.menuBar()
    # Retain every QMenu on the window: a menu returned by addMenu() that keeps no
    # Python owner is shiboken-collected (its C++ object is deleted), which empties
    # the menu. win._menus is the single owner for all top-level menus + submenus.
    win._menus = {}

    def _menu(parent, title, key):
        # Explicit-parent QMenu + a retained reference. The bare addMenu(str)
        # overload can have its returned QMenu's C++ object collected by shiboken
        # (which silently empties the menu); constructing with a parent hands Qt
        # ownership so the submenu survives. Used for every menu and submenu.
        mm = QtWidgets.QMenu(title, parent)
        parent.addMenu(mm)
        win._menus[key] = mm
        return mm

    m = _menu(mb, "&File", "file")
    m.addAction(act_open_img); m.addAction(act_demo)          # image in
    m.addSeparator()
    m.addAction(act_open_pipe); m.addAction(act_save_pipe); m.addAction(act_export)  # pipeline docs
    win._recent_menu = _menu(m, "Open Recent", "recent")     # populated by _rebuild_recent_menu()
    m.addAction(act_samples)                                  # sample pipelines + code gallery
    sample_img_menu = _menu(m, "Sample images", "sample_images")   # collected license-clean images
    try:
        import sample_images as _si
        for _nm in _si.names():
            _a = QtGui.QAction(_nm, win)
            _a.triggered.connect(lambda _=False, nm=_nm: win._load_sample_image(nm))
            sample_img_menu.addAction(_a)
    except Exception:
        pass
    act_visual_demo = QtGui.QAction("dev_* visualization demo", win)   # sample that USES dev_* ops
    act_visual_demo.triggered.connect(lambda: win._load_visual_demo())
    m.addAction(act_visual_demo); win._act_visual_demo = act_visual_demo
    act_2d_examples = QtGui.QAction("2-D Examples…", win)   # 2D 幾何op 事例ギャラリー
    act_2d_examples.setToolTip("Browse the 2-D geometric-vision worked examples "
                               "(morph / shape descriptors / drawing), run and copy their code")
    m.addAction(act_2d_examples); win._act_2d_examples = act_2d_examples
    act_3d_examples = QtGui.QAction("3-D Examples…", win)   # ops3d 事例ギャラリー(実データ)
    act_3d_examples.setToolTip("Browse the 3-D vision worked examples "
                               "(real Itokawa / skeleton-CT / synthetic) and copy their code")
    m.addAction(act_3d_examples); win._act_3d_examples = act_3d_examples
    act_3d_ops = QtGui.QAction("3-D Operators…", win)   # ops3d リファレンス(help ページ閲覧)
    act_3d_ops.setToolTip("Browse all 3-D operators (point-cloud / mesh / volume) with their "
                          "generated help pages and type-compatible neighbours")
    m.addAction(act_3d_ops); win._act_3d_ops = act_3d_ops
    act_pyedit = QtGui.QAction("Python Editor…", win)   # Qt Creator 風の編集+実行環境
    act_pyedit.setToolTip("Edit and run Python scripts against the repo — open any worked "
                          "example as editable code, F5 to run in a subprocess")
    m.addAction(act_pyedit); win._act_pyedit = act_pyedit
    m.addSeparator()
    m.addAction(act_save_res); m.addAction(act_copy_res)      # result out
    m.addSeparator(); m.addAction(act_quit)
    m = _menu(mb, "&Edit", "edit")
    m.addAction(act_undo); m.addAction(act_redo)
    m.addSeparator()
    m.addAction(act_remove); m.addAction(act_dup)
    m.addAction(act_up); m.addAction(act_down)
    m.addAction(act_top); m.addAction(act_bottom)
    m.addSeparator(); m.addAction(act_clear)
    menu_view = _menu(mb, "&View", "view")
    menu_view.addAction(act_zin); menu_view.addAction(act_zout)
    menu_view.addSeparator(); menu_view.addAction(act_fit); menu_view.addAction(act_11)
    menu_view.addSeparator()          # Display mode submenu + 3D surface appended once the display combo exists
    m = _menu(mb, "&Run", "run")
    m.addAction(act_reset); m.addAction(act_step)
    m.addSeparator(); m.addAction(act_runall)
    m.addSeparator(); m.addAction(act_holdout)
    menu_windows = _menu(mb, "&Window", "window")   # panels / graphics / layout submenus (filled after docks)
    menu_tools = _menu(mb, "&Tools", "tools")
    menu_tools.addAction(act_palette)                         # cross-cutting command launcher (was under Run)
    menu_tools.addAction(act_featins)                         # HDevelop-style feature inspection (2D+3D)
    menu_tools.addSeparator()
    act_system_settings = QtGui.QAction("System settings…", win)   # HALCON set_system-style config
    act_system_settings.setShortcut("Ctrl+,")                      # standard preferences shortcut
    act_system_settings.triggered.connect(lambda: win._open_system_settings())
    menu_tools.addAction(act_system_settings)
    win._act_system_settings = act_system_settings
    menu_tools.addSeparator()
    act_physical_ai = QtGui.QAction("Physical AI: evis RL walk (Fullseye perception)…", win)
    act_physical_ai.setToolTip("Play the GPU-learned evis walk as Fullseye perceives it "
                               "(RGB · depth · DVS events)")
    act_physical_ai.triggered.connect(lambda: win._open_physical_ai_viewer())
    menu_tools.addAction(act_physical_ai)
    win._act_physical_ai = act_physical_ai
    menu_tools.addSeparator()
    lang_menu = _menu(menu_tools, "Language / 言語 / 语言", "language")  # UI/help language = a preference, not Help
    m = _menu(mb, "&Help", "help")
    m.addAction(act_op_help); m.addAction(act_samples); m.addSeparator()
    act_guide = _act("Quick guide (en/ja/zh)", "Shift+F2", "A short guide in the selected language")
    m.addAction(act_guide)
    m.addSeparator()
    act_feedback = QtGui.QAction("Feedback / Report an issue…", win)
    act_feedback.setToolTip("Open the GitHub issue tracker — bug reports, operator "
                            "requests and accuracy/honesty reports all have templates")
    _FEEDBACK_URL = "https://github.com/furuse-kazufumi/fullseye/issues"
    act_feedback.triggered.connect(
        lambda _=False: QtGui.QDesktopServices.openUrl(QtCore.QUrl(_FEEDBACK_URL)))
    win._act_feedback = act_feedback; win._feedback_url = _FEEDBACK_URL
    m.addAction(act_feedback); m.addSeparator()
    m.addAction(act_shortcuts); m.addSeparator(); m.addAction(act_about)

    # ---- branded toolbar (icon-only; tooltips carry the meaning) ------------- #
    tb = QtWidgets.QToolBar(); tb.setMovable(False); tb.setFloatable(False)
    tb.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
    tb.setIconSize(QtCore.QSize(18, 18))
    win.addToolBar(tb)
    if os.path.exists(_ICON_PATH):
        brand = QtWidgets.QLabel()
        brand.setPixmap(QtGui.QIcon(_ICON_PATH).pixmap(22, 22))
        brand.setStyleSheet("padding:0 6px;")
        tb.addWidget(brand)
    title = QtWidgets.QLabel("Fullseye Studio")
    title.setStyleSheet("font-size:15px; font-weight:800; color:%s; padding:0 4px;" % AMBER)
    tb.addWidget(title)
    spacer = QtWidgets.QWidget()
    spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    tb.addWidget(spacer)
    # Primary actions get a themed icon so the icon-only toolbar reads at a glance;
    # tooltips (already set on each action) name them.
    for _a, _ic in ((act_demo, "demo"), (act_open_img, "open"), (act_runall, "playplay"),
                    (act_export, "export")):
        _a.setIcon(_icon(QtGui, QtCore, _ic, TEXT))
        tb.addAction(_a)

    # Central document area = an MDI workspace of graphics windows (HDevelop-style:
    # multiple image/result windows the user can open, tile, cascade and float).
    mdi = QtWidgets.QMdiArea()
    mdi.setViewMode(QtWidgets.QMdiArea.SubWindowView)
    mdi.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    mdi.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    win.setCentralWidget(mdi)
    win.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks
                       | QtWidgets.QMainWindow.AllowTabbedDocks
                       | QtWidgets.QMainWindow.AnimatedDocks
                       | QtWidgets.QMainWindow.GroupedDragging)   # finer/free re-dock targets
    win.setDockNestingEnabled(True)                              # split any area freely
    for _area in (QtCore.Qt.TopDockWidgetArea, QtCore.Qt.BottomDockWidgetArea,
                  QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.RightDockWidgetArea):
        win.setTabPosition(_area, QtWidgets.QTabWidget.North)
    win.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtWidgets.QTabWidget.North)
    win._mdi = mdi
    win._graphics_windows = []

    status = win.statusBar()
    readout = QtWidgets.QLabel("hover over the image for pixel coordinates + value")
    readout.setProperty("hint", True)
    status.addWidget(readout)
    win._img_info = QtWidgets.QLabel("")                 # always-visible shape/dtype/range
    win._img_info.setProperty("hint", True)
    win._img_info.setToolTip("current result: shape · dtype · value range")
    status.addPermanentWidget(win._img_info)

    def flash(msg):
        status.showMessage(msg, 6000)

    # -- left: operator browser + samples ------------------------------------ #
    left = QtWidgets.QWidget(); lv = QtWidgets.QVBoxLayout(left); lv.setSpacing(6)
    lv.setContentsMargins(6, 6, 6, 6)
    samples = QtWidgets.QComboBox(); samples.addItem("— load a sample —")
    # size to ~10 chars, not the widest recipe name, so the compact panel can be narrow
    samples.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
    samples.setMinimumContentsLength(10)
    for nm in recipes.names():
        samples.addItem(nm)
    samples.setToolTip("Pick a ready-made sample — it loads into the pipeline and its code appears "
                       "in the Program panel")
    b_browse_samples = _tbtn("grid", "Browse the sample gallery — preview each sample's code before loading it")
    s_hint = QtWidgets.QLabel("pick one → loads into the pipeline + Program panel")
    s_hint.setProperty("muted", True); s_hint.setWordWrap(True)
    slay = QtWidgets.QVBoxLayout()
    srow = QtWidgets.QHBoxLayout(); srow.addWidget(samples, 1); srow.addWidget(b_browse_samples)
    slay.addLayout(srow); slay.addWidget(s_hint)
    lv.addWidget(_group(QtWidgets, "SAMPLE PIPELINES", slay))

    all_ops = api.list_ops(include_algo=True)   # + the opt-in general-algorithm tier (read-only)
    cat = QtWidgets.QComboBox(); cat.addItem("all categories")
    cat.addItems(sorted({r["category"] for r in all_ops}))
    cat.setToolTip("Filter operators by category")
    cat.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
    cat.setMinimumContentsLength(10)                       # narrow: don't size to the widest category
    search = QtWidgets.QLineEdit(); search.setPlaceholderText("search / autocomplete operators…")
    search.setClearButtonEnabled(True)
    search.setToolTip("Filter by op name, HALCON alias or category")
    op_list = QtWidgets.QListWidget()
    op_list.setToolTip("Double-click an operator to insert it into the pipeline")
    op_hint = QtWidgets.QLabel("set a, b · Insert into pipeline or Run once · double-click = insert")
    op_hint.setWordWrap(True)                             # wrap: a long hint must not force a wide panel
    op_hint.setProperty("muted", True)
    op_param = QtWidgets.QLabel("select an operator to see its signature")
    op_param.setProperty("hint", True); op_param.setWordWrap(True)
    op_param.setToolTip("The selected operator's input→output sorts, HALCON alias and what each knob does")
    op_param.setMinimumHeight(92)
    # HDevelop-style operator entry: pick an op, set its two args, then Insert into
    # the pipeline OR Run once (single-shot) and see the result in a graphics window.
    op_a_spin = QtWidgets.QDoubleSpinBox(); op_a_spin.setRange(0.0, 1.0)
    op_a_spin.setSingleStep(0.05); op_a_spin.setDecimals(2); op_a_spin.setValue(0.5)
    op_b_spin = QtWidgets.QDoubleSpinBox(); op_b_spin.setRange(0.0, 1.0)
    op_b_spin.setSingleStep(0.05); op_b_spin.setDecimals(2); op_b_spin.setValue(0.5)
    op_a_spin.setToolTip("Argument a (0..1) used by Insert and Run once — its meaning is shown above")
    op_b_spin.setToolTip("Argument b (0..1) used by Insert and Run once")
    b_insert = _tbtn("plus", "Insert operator into the pipeline with a, b (Enter / double-click)", accent=True)
    b_insert.setEnabled(False)
    b_run_once = _tbtn("playone", "Run once on the loaded image — pipeline NOT changed "
                       "(HDevelop single-step execution)")
    b_run_once.setEnabled(False)
    b_help = _tbtn("help", "Operator help (image-processing details)")
    b_help.setEnabled(False)
    olay = QtWidgets.QVBoxLayout()
    olay.addWidget(cat); olay.addWidget(search); olay.addWidget(op_list, 1)
    olay.addWidget(op_param)
    argrow = QtWidgets.QHBoxLayout()
    lbl_a = QtWidgets.QLabel("a"); lbl_b = QtWidgets.QLabel("b")
    lbl_a.setToolTip("Argument a — the label shows its role for the selected operator")
    lbl_b.setToolTip("Argument b — the label shows its role for the selected operator")
    lbl_a.setMinimumWidth(96); lbl_b.setMinimumWidth(96)     # room for the role name
    argrow.addWidget(lbl_a); argrow.addWidget(op_a_spin, 1)
    argrow.addWidget(lbl_b); argrow.addWidget(op_b_spin, 1)
    olay.addLayout(argrow)
    oprow = QtWidgets.QHBoxLayout()
    oprow.addWidget(b_insert); oprow.addWidget(b_run_once); oprow.addWidget(b_help); oprow.addStretch(1)
    olay.addLayout(oprow); olay.addWidget(op_hint)
    lv.addWidget(_group(QtWidgets, "OPERATORS", olay), 1)

    def refill_ops():
        kw = search.text().lower(); c = cat.currentText()
        op_list.clear()
        for r in all_ops:
            if c != "all categories" and r["category"] != c:
                continue
            hay = r.get("_search")
            if hay is None:
                # search the same vocabulary the generated sample comments use
                # (category, HALCON counterpart, signal sorts) PLUS the op docstring,
                # so a word seen in any sample comment finds the related operators
                doc = ""
                try:
                    _fn = getattr(api.find_op(r["name"]), "fn", None)
                    doc = " ".join(((getattr(_fn, "__doc__", "") or "").split())[:40])
                except Exception:
                    pass
                hay = r["_search"] = " ".join(
                    [r["name"], r.get("halcon") or "", r["category"],
                     r.get("in_sort", ""), r.get("out_sort", ""), r.get("tier", ""),
                     doc]).lower()
            if kw and kw not in hay:
                continue
            it = QtWidgets.QListWidgetItem(f"{r['name']}   [{r['in_sort']} → {r['out_sort']}]")
            it.setData(QtCore.Qt.UserRole, r["name"])
            it.setToolTip(op_tooltip(r))
            op_list.addItem(it)
    refill_ops()

    # -- centre: pipeline + knobs + export ----------------------------------- #
    mid = QtWidgets.QWidget(); mv = QtWidgets.QVBoxLayout(mid); mv.setSpacing(6)
    mv.setContentsMargins(6, 6, 6, 6)
    stage_list = QtWidgets.QListWidget()
    stage_list.setToolTip("The pipeline. Each row: op, knobs, and the result state after that stage.\n"
                          "Drag a row to reorder, or use ↑/↓ (Ctrl+↑ / Ctrl+↓).")
    stage_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
    stage_list.setDefaultDropAction(QtCore.Qt.MoveAction)
    b_rm = _tbtn("trash", "Remove the selected stage (Del)")
    b_up = _tbtn("up", "Move the selected stage earlier (Ctrl+Up)")
    b_dn = _tbtn("down", "Move the selected stage later (Ctrl+Down)")
    b_reset = _tbtn("reset", "Show the raw image, before stage 1 (Home)")
    b_step = _tbtn("step", "Advance one stage (Ctrl+Right)")
    b_runall = _tbtn("playplay", "Run all — show the final result (Ctrl+Enter)", accent=True)
    problems_list = QtWidgets.QListWidget()
    problems_list.setFixedHeight(74)
    problems_list.setToolTip("Pipeline problems (unknown op / sort mismatch / runtime error).\n"
                             "Double-click to jump to the offending stage.")
    play = QtWidgets.QVBoxLayout(); play.addWidget(stage_list, 1)
    erow = QtWidgets.QHBoxLayout()                       # one compact icon strip: edit | run
    for _b in (b_rm, b_up, b_dn):
        erow.addWidget(_b)
    erow.addSpacing(10); erow.addStretch(1)
    for _b in (b_reset, b_step, b_runall):
        erow.addWidget(_b)
    play.addLayout(erow)
    problems_label = QtWidgets.QLabel("Problems"); problems_label.setProperty("muted", True)
    play.addWidget(problems_label); play.addWidget(problems_list)
    mv.addWidget(_group(QtWidgets, "PIPELINE", play), 1)

    stage_detail = QtWidgets.QLabel("select a stage to tune its knobs")
    stage_detail.setWordWrap(True); stage_detail.setProperty("hint", True)
    sa = QtWidgets.QSlider(QtCore.Qt.Horizontal); sa.setRange(0, 100); sa.setEnabled(False)
    sb = QtWidgets.QSlider(QtCore.Qt.Horizontal); sb.setRange(0, 100); sb.setEnabled(False)
    sa.setToolTip("Knob a (0..1) — meaning depends on the selected op")
    sb.setToolTip("Knob b (0..1) — meaning depends on the selected op")
    la = QtWidgets.QLabel("a: 0.50"); lb = QtWidgets.QLabel("b: 0.50")
    spin_a = QtWidgets.QDoubleSpinBox(); spin_a.setRange(0.0, 1.0)
    spin_a.setSingleStep(0.01); spin_a.setDecimals(3); spin_a.setEnabled(False)
    spin_a.setToolTip("Knob a — type an exact value (0..1)")
    spin_b = QtWidgets.QDoubleSpinBox(); spin_b.setRange(0.0, 1.0)
    spin_b.setSingleStep(0.01); spin_b.setDecimals(3); spin_b.setEnabled(False)
    spin_b.setToolTip("Knob b — type an exact value (0..1)")
    _ra = QtWidgets.QHBoxLayout(); _ra.addWidget(sa, 1); _ra.addWidget(spin_a)
    _rb = QtWidgets.QHBoxLayout(); _rb.addWidget(sb, 1); _rb.addWidget(spin_b)
    klay = QtWidgets.QVBoxLayout()
    klay.addWidget(stage_detail); klay.addWidget(la); klay.addLayout(_ra)
    klay.addWidget(lb); klay.addLayout(_rb)
    mv.addWidget(_group(QtWidgets, "SELECTED STAGE · KNOBS", klay))

    b_export = _tbtn("export", "Export this pipeline as an --ops string and Python (Ctrl+E)")
    b_savep = _tbtn("save", "Save pipeline to JSON (Ctrl+Shift+S)")
    b_openp = _tbtn("open", "Open a pipeline from JSON (Ctrl+Shift+O)")
    xrow = QtWidgets.QHBoxLayout()
    xrow.addWidget(b_openp); xrow.addWidget(b_savep); xrow.addWidget(b_export); xrow.addStretch(1)
    mv.addWidget(_group(QtWidgets, "EXPORT & I/O", xrow))

    # -- right: image view + display + perception + analysis ------------------ #
    right = QtWidgets.QWidget(); rv = QtWidgets.QVBoxLayout(right); rv.setSpacing(6)
    rv.setContentsMargins(6, 6, 6, 6)
    b_load = _tbtn("open", "Open an image file (Ctrl+O)")
    b_demo = _tbtn("demo", "Load the synthetic demo scene (Ctrl+D)")
    b_save = _tbtn("save", "Save the displayed result (Ctrl+S)")
    ImageView = _image_view_class(QtWidgets, QtGui, QtCore)
    Viewer3D = _viewer3d_class(QtWidgets, QtGui, QtCore)
    win._viewer3d_class = Viewer3D               # for tests / feature-inspection dialog
    view = ImageView()
    b_zin = _tbtn("zin", "Zoom in (Ctrl+=)")
    b_zout = _tbtn("zout", "Zoom out (Ctrl+-)")
    b_fit = _tbtn("fit", "Fit to window (Ctrl+0)")
    b_11 = _tbtn("actual", "Actual size 1:1 (Ctrl+1)")
    ilay = QtWidgets.QVBoxLayout()
    # One thin icon strip above the view: file I/O · | · zoom — so the image itself
    # owns almost all of the panel (roomy display, per user direction).
    itop = QtWidgets.QHBoxLayout()
    for w_ in (b_load, b_demo, b_save):
        itop.addWidget(w_)
    itop.addSpacing(8)
    _vline = QtWidgets.QFrame(); _vline.setFrameShape(QtWidgets.QFrame.VLine)
    _vline.setStyleSheet("color:%s;" % LINE); itop.addWidget(_vline); itop.addSpacing(8)
    for w_ in (b_zin, b_zout, b_fit, b_11):
        itop.addWidget(w_)
    itop.addStretch(1)
    ilay.addLayout(itop); ilay.addWidget(view, 1)
    ilay.setContentsMargins(4, 4, 4, 4); ilay.setSpacing(4)
    image_panel = QtWidgets.QWidget(); image_panel.setLayout(ilay)
    image_panel.setObjectName("graphics_primary")
    image_panel.setMinimumSize(320, 260)

    display = QtWidgets.QComboBox()
    display.addItems(["gray", "region overlay", "shaded relief", "height (color)"]
                     + [c for c in imgio.COLORMAPS if c != "gray"])
    display.setToolTip("How to render the 2-D result: gray, region overlay (a region drawn "
                       "on the source image), a false-colour palette, shaded relief, or height")
    b_3d = _tbtn("cube", "Rotatable 3-D surface of the result (Ctrl+3)")
    b_loadb = _tbtn("open", "Load a second frame B for two-frame perception (flow / stereo)")
    percep_mode = QtWidgets.QComboBox(); percep_mode.addItems(list(PerceptionModel.MODES))
    percep_mode.setToolTip("Two-frame perception mode")
    b_percep = _tbtn("eye", "Run the selected perception mode on frames A + B", accent=True)
    dlay = QtWidgets.QVBoxLayout()
    drow = QtWidgets.QHBoxLayout()
    drow.addWidget(QtWidgets.QLabel("Display:")); drow.addWidget(display, 1); drow.addWidget(b_3d)
    prow = QtWidgets.QHBoxLayout()
    prow.addWidget(b_loadb); prow.addWidget(percep_mode, 1); prow.addWidget(b_percep)
    dlay.addLayout(drow); dlay.addLayout(prow)
    rv.addWidget(_group(QtWidgets, "DISPLAY & PERCEPTION", dlay))

    hist_view = QtWidgets.QLabel(); hist_view.setFixedHeight(64)
    hist_view.setStyleSheet("background:#12141b; border:1px solid #262b38; border-radius:6px;")
    inspector = QtWidgets.QPlainTextEdit(); inspector.setReadOnly(True); inspector.setFixedHeight(150)
    inspector.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
    alay = QtWidgets.QVBoxLayout()
    hl = QtWidgets.QLabel("Histogram"); hl.setProperty("muted", True)
    il = QtWidgets.QLabel("Inspector (variable / image / region)"); il.setProperty("muted", True)
    alay.addWidget(hl); alay.addWidget(hist_view); alay.addWidget(il); alay.addWidget(inspector)
    rv.addWidget(_group(QtWidgets, "ANALYSIS", alay))

    # -- program / code editor (HDevelop program window) --------------------- #
    ProgEdit = _program_editor_class(QtWidgets, QtGui, QtCore)
    # IMAGE ops only for the HDevelop program parser / autocomplete / Operator-Help
    # picker: the general-algorithm tier is shown READ-ONLY in the browser (all_ops),
    # but it is a seq/scalar model that must not be a valid image-pipeline token — else
    # `op (a,b)` code would enter the pipeline via apply_program (which bypasses the
    # add_stage KeyError backstop) and Help would mislabel it as a knob-tunable op.
    op_names = [r["name"] for r in all_ops if r.get("backend") != "general"]
    code_edit = ProgEdit(op_names)
    code_edit.setToolTip("Edit the pipeline as HDevelop-style code: `op (a, b)` (or `op a b`), "
                         "`*`/`#` comments, and control flow `for N … endfor` / `if … else … endif`.\n"
                         "Type for autocomplete; click the gutter to toggle a breakpoint; Step / Run (timed).")
    c_run = _tbtn("play", "Run every line, timing each; stops at a breakpoint (Ctrl+Shift+Return)", accent=True)
    c_cont = _tbtn("playplay", "Continue: resume from the execution line to the next "
                   "breakpoint / end (HDevelop F5 — pause via breakpoints, resume here)")
    c_step = _tbtn("step", "Execute one more line and show its result (F10)")
    c_reset = _tbtn("reset", "Clear the run highlight and per-line timings")
    c_apply = _tbtn("apply", "Apply → parse the code and replace the pipeline")
    c_sync = _tbtn("sync", "Sync ← regenerate the code from the current pipeline")
    code_status = QtWidgets.QLabel("ready"); code_status.setProperty("hint", True)
    code_w = QtWidgets.QWidget(); cvl = QtWidgets.QVBoxLayout(code_w)
    cvl.setContentsMargins(4, 4, 4, 4); cvl.setSpacing(4)
    crow = QtWidgets.QHBoxLayout()
    for _cb in (c_run, c_cont, c_step, c_reset, c_apply, c_sync):
        crow.addWidget(_cb)
    crow.addStretch(1)
    cvl.addLayout(crow); cvl.addWidget(code_edit, 1); cvl.addWidget(code_status)

    # -- variables & objects window (HDevelop variable window) --------------- #
    var_list = QtWidgets.QListWidget()
    var_list.setToolTip("Every pipeline variable: the input frame and each stage's output.\n"
                        "Select one to inspect it; the buttons display it in a graphics window.")
    var_inspect = QtWidgets.QPlainTextEdit(); var_inspect.setReadOnly(True)
    var_inspect.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
    v_disp = _tbtn("image", "Display the selected variable in a NEW graphics window")
    v_here = _tbtn("eye", "Display the selected variable in the CURRENT graphics window "
                   "(double-clicking the variable does the same)")
    var_w = QtWidgets.QWidget(); vvl = QtWidgets.QVBoxLayout(var_w)
    vvl.setContentsMargins(4, 4, 4, 4); vvl.setSpacing(4)
    vrow = QtWidgets.QHBoxLayout()
    vrow.addWidget(v_disp); vrow.addWidget(v_here); vrow.addStretch(1)
    vvl.addWidget(var_list, 1); vvl.addLayout(vrow); vvl.addWidget(var_inspect, 1)

    # -- watch expressions (debugger-style, user spec 2026-08-30: the variable window
    #    was "a bit weak") — arbitrary expressions re-evaluated live against the
    #    SELECTED variable on every selection / pipeline change. --
    watch_table = QtWidgets.QTableWidget(0, 2)
    watch_table.setHorizontalHeaderLabels(["expression", "value"])
    watch_table.horizontalHeader().setStretchLastSection(True)
    watch_table.verticalHeader().setVisible(False)
    watch_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    watch_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    watch_table.setToolTip("Watch expressions, re-evaluated live against the SELECTED variable.\n"
                           "`v` = selected variable's value, `np` = numpy, `img` = input frame.\n"
                           "e.g.  v.mean()   np.percentile(v, 99)   (v > 0.5).sum()")
    watch_input = QtWidgets.QLineEdit()
    watch_input.setPlaceholderText("add watch…  (v = selected variable, np = numpy)")
    watch_input.setClearButtonEnabled(True)
    w_add = QtWidgets.QPushButton("+"); w_add.setFixedWidth(28)
    w_add.setToolTip("Add the expression as a watch (Enter in the box does the same)")
    w_del = QtWidgets.QPushButton("−"); w_del.setFixedWidth(28)
    w_del.setToolTip("Remove the selected watch row")
    wrow = QtWidgets.QHBoxLayout()
    wrow.addWidget(watch_input, 1); wrow.addWidget(w_add); wrow.addWidget(w_del)
    vvl.addLayout(wrow); vvl.addWidget(watch_table, 1)

    # ---- dockable tool windows (VS / HDevelop-style, all movable/floatable) ---- #
    def _mk_dock(title, widget, objname):
        d = QtWidgets.QDockWidget(title, win)
        d.setObjectName(objname)
        d.setWidget(widget)
        d.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable
                      | QtWidgets.QDockWidget.DockWidgetFloatable
                      | QtWidgets.QDockWidget.DockWidgetClosable)
        d.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        # NOTE: we deliberately keep Qt's native dock title (not an OS window frame).
        # Dragging the Qt title is what shows the drop-guide rectangles and lets a panel
        # be re-docked at any edge / tabbed / split. A native OS frame moves freely but
        # kills those drop guides. The title bar is made tall + grabbable via the QSS.
        return d

    dock_ops = _mk_dock("Operators", left, "dock_operators")
    dock_pipe = _mk_dock("Pipeline · Parameters", mid, "dock_pipeline")
    dock_disp = _mk_dock("Display · Analysis", right, "dock_display")
    dock_code = _mk_dock("Program (code)", code_w, "dock_program")
    dock_vars = _mk_dock("Variables & Objects", var_w, "dock_variables")
    # Default layout (user-directed 2026-08-15): the IMAGE (central MDI) is the largest
    # surface, the Program (script code) is the second, and op selection + Variables /
    # Objects are compact panels ("small size", mostly floated / shown on demand).
    #   • Image = central, maximised → top-left, largest.
    #   • Program (code) = a wide BOTTOM strip (code wants width, not a narrow column) →
    #     second-largest; kept under the image only (setCorner) so it doesn't span the
    #     op/var column.
    #   • Operators / Variables & Objects / Pipeline·Params / Display·Analysis = a single
    #     narrow RIGHT column, tabbed → compact and out of the way.
    win.setCorner(QtCore.Qt.BottomLeftCorner, QtCore.Qt.BottomDockWidgetArea)
    win.setCorner(QtCore.Qt.BottomRightCorner, QtCore.Qt.RightDockWidgetArea)  # right col runs full height
    win.setCorner(QtCore.Qt.TopRightCorner, QtCore.Qt.RightDockWidgetArea)
    win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock_code)    # Program = wide bottom strip (2nd largest)
    win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_ops)      # op selection = compact right column
    win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_vars)
    win.tabifyDockWidget(dock_ops, dock_vars)                       # Variables tabbed behind Operators
    win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_pipe)
    win.tabifyDockWidget(dock_ops, dock_pipe)                       # Pipeline·Params tabbed in
    win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_disp)
    win.tabifyDockWidget(dock_ops, dock_disp)                       # Display·Analysis tabbed in
    dock_ops.raise_()
    # The inspection panels (Variables & Objects, Pipeline·Params, Display·Analysis) are
    # on-demand — the user keeps them undocked / shown only when needed — so they start
    # hidden and the image owns the workspace. Toolbar + Window ▸ Panels toggles bring
    # each back. Operators stays (compact) since it is the primary build tool.
    for _d in (dock_vars, dock_pipe, dock_disp):
        _d.hide()
    win.resizeDocks([dock_ops], [420], QtCore.Qt.Horizontal)        # narrow right column → image keeps the rest
    win.resizeDocks([dock_code], [300], QtCore.Qt.Vertical)         # wide bottom code strip = 2nd largest
    win._docks = {"operators": dock_ops, "pipeline": dock_pipe, "display": dock_disp,
                  "program": dock_code, "variables": dock_vars}
    # On-demand panels + less-common actions live behind ONE small popup menu button
    # (per user direction: prefer popup menus, keep buttons small) instead of a row of
    # wide toggles. Each panel toggle's text is the panel name; checking it shows it.
    tb.addSeparator()
    _more_menu = QtWidgets.QMenu("More", win)
    win._more_menu = _more_menu                          # retain (shiboken ownership)
    _panels_sub = QtWidgets.QMenu("Panels", _more_menu); win._more_menu_panels = _panels_sub
    for _d in (dock_vars, dock_disp, dock_pipe, dock_ops, dock_code):
        _panels_sub.addAction(_d.toggleViewAction())
    _more_menu.addMenu(_panels_sub)
    _more_menu.addSeparator()
    for _a in (act_palette, act_holdout, act_samples, act_op_help, act_shortcuts, act_about):
        _more_menu.addAction(_a)
    b_more = _tbtn("more", "More — panels, command palette, help", menu=_more_menu)
    tb.addWidget(b_more)

    # ---- central graphics workspace: the primary image window ------------------ #
    gsub = mdi.addSubWindow(image_panel)
    gsub.setWindowTitle("Graphics 1")
    gsub.setObjectName("graphics_sub_1")
    win._graphics_windows.append(gsub)

    # The primary graphics sub-window is the HDevelop-style *resident* window: it
    # hosts the always-present image view AND the global Load/Demo/Save/Zoom
    # controls, so it must never be closed — closing it would destroy those
    # controls and blank the display (and a queued action-sync would then poke at
    # freed QPushButtons). An event filter vetoes its Close event, covering every
    # path: the sub-window close button, its system-menu "Close", and Ctrl+W.
    # Extra windows opened via new_graphics_window stay freely closable.
    class _ResidentCloseGuard(QtCore.QObject):
        def eventFilter(self, obj, ev):
            if ev.type() == QtCore.QEvent.Close:
                ev.ignore()
                flash("the primary graphics window stays open (resident view)")
                return True
            return False
    _resident_guard = _ResidentCloseGuard(win)
    gsub.installEventFilter(_resident_guard)
    win._resident_guard = _resident_guard          # keep a Python owner (shiboken)
    win._primary_gsub = gsub

    # HDevelop "current window" model: every graphics window has a stable handle
    # number (never reused), and there is always exactly one *current* window —
    # the target for a variable double-click / Run once, like dev_set_window +
    # dev_display. It defaults to the resident primary window and follows the
    # active MDI sub-window as the user clicks between windows.
    gsub._fs_handle = 1
    win._gfx_handle_seq = 1
    win._current_gfx = gsub

    def new_graphics_window(pixmap=None, title=None, widget=None):
        """Open another graphics window (HDevelop allows several). Shows a snapshot
        of the current display by default, or a supplied pixmap (e.g. a variable),
        or embeds *widget* (a Viewer3D — the 3-D viewer rides the SAME window
        numbering, cap and dev_set_window machinery as the 2-D windows).
        Capped by set_system('max_graphics_windows') — at the cap, no new window is
        opened (flash + returns None), so a looping program cannot flood the MDI."""
        alive = [s for s in win._graphics_windows if s in mdi.subWindowList()]
        cap = int(state["system"].get("max_graphics_windows", 256))
        if len(alive) >= cap:
            flash("graphics window limit reached (%d) — close one, or raise it via "
                  "set_system('max_graphics_windows', n)" % cap)
            return None
        win._gfx_handle_seq += 1
        h = win._gfx_handle_seq
        if widget is not None:
            gv = widget
        else:
            gv = ImageView()
            try:
                gv.set_pixmap(pixmap if pixmap is not None else view._item.pixmap())
                gv.fit()
            except Exception:
                pass
        sub = mdi.addSubWindow(gv)
        sub._fs_handle = h
        sub.setWindowTitle(title or ("Graphics %d" % h))
        sub.resize(440, 360)
        sub.show()
        win._graphics_windows.append(sub)
        win._current_gfx = sub                     # a freshly opened window becomes current
        _update_current_indicator()
        win._flash and win._flash("opened %s" % sub.windowTitle())
        return sub
    win._new_graphics_window = new_graphics_window

    # -- current-window helpers (which ImageView does "display" write to) ------- #
    def _graphics_view_of(sub):
        """The ImageView a graphics sub-window draws into. The primary window nests
        its view inside image_panel (return the shared `view`); every extra window
        *is* an ImageView."""
        if sub is win._primary_gsub:
            return view
        w = sub.widget() if sub is not None else None
        return w if isinstance(w, ImageView) else None

    def _current_view():
        """The ImageView of the current window, healing a stale pointer back to the
        resident primary window if the current one was closed."""
        sub = win._current_gfx
        if sub is None or sub not in win._graphics_windows:
            win._current_gfx = win._primary_gsub
            return view
        v = _graphics_view_of(sub)
        return v if v is not None else view

    def _current_handle():
        sub = win._current_gfx
        if sub is None or sub not in win._graphics_windows:
            return 1
        return getattr(sub, "_fs_handle", 1)

    def _update_current_indicator():
        lbl = getattr(win, "_current_label", None)
        if lbl is not None:
            lbl.setText("current: Graphics %d" % _current_handle())

    def _set_current_gfx(sub):
        """Follow the active MDI sub-window: clicking a graphics window makes it the
        current target (HDevelop dev_set_window)."""
        if sub is not None and sub in win._graphics_windows:
            win._current_gfx = sub
            _update_current_indicator()

    # a small permanent status-bar readout of the current window's handle
    win._current_label = QtWidgets.QLabel("current: Graphics 1")
    win._current_label.setProperty("hint", True)
    win.statusBar().addPermanentWidget(win._current_label)
    # a permanent indicator when display updates are OFF, so a frozen display never
    # reads as a broken one (HDevelop dev_update_off state).
    win._update_label = QtWidgets.QLabel("")
    win._update_label.setStyleSheet("QLabel{color:%s;}" % AMBER)
    win.statusBar().addPermanentWidget(win._update_label)
    mdi.subWindowActivated.connect(_set_current_gfx)
    win._current_view = _current_view
    win._current_handle = _current_handle
    win._set_current_gfx = _set_current_gfx

    # ---- Window menu: 3 submenus (Panels / Graphics windows / Layout) ----------- #
    # Consolidated so the menu is a short, scannable list of groups, not a flat wall
    # of ~15 items (the v18.6 overload the user flagged). Panels/Graphics filled here;
    # Float/Detach/Layout items are appended to these same submenus further below.
    act_newgfx = _act("New graphics window", "Ctrl+G", "Open another image / result window")
    act_tile = _act("Tile graphics windows", None, "Tile the open graphics windows")
    act_cascade = _act("Cascade graphics windows", None, "Cascade the open graphics windows")
    act_reset_layout = _act("Reset panel layout", None, "Restore the default tool-panel layout")
    menu_panels = _menu(menu_windows, "Panels", "panels")
    for _d in (dock_ops, dock_pipe, dock_disp, dock_code, dock_vars):
        menu_panels.addAction(_d.toggleViewAction())
    menu_panels.addSeparator()             # Float all/Dock all + per-panel Float appended below
    menu_graphics = _menu(menu_windows, "Graphics windows", "graphics")
    menu_graphics.addAction(act_newgfx)
    menu_graphics.addSeparator()
    menu_graphics.addAction(act_tile); menu_graphics.addAction(act_cascade)
    menu_graphics.addSeparator()           # Detach/Reattach appended below
    win._dock_menu = menu_panels           # later milestones append their docks here
    win._menu_panels = menu_panels
    win._menu_graphics = menu_graphics
    act_newgfx.triggered.connect(lambda: new_graphics_window())
    act_tile.triggered.connect(mdi.tileSubWindows)
    act_cascade.triggered.connect(mdi.cascadeSubWindows)

    def reset_layout():
        if getattr(win, "_default_state", None) is not None:
            win.restoreState(win._default_state)
        for _d in win._docks.values():
            _d.show()
    act_reset_layout.triggered.connect(reset_layout)
    win._reset_layout = reset_layout
    state = {"result": None, "raw": None, "view_raw": False, "reordering": False,
             "dirty": False, "code_dirty": False, "errors": [], "perception_error": None,
             "renders": 0, "image_path": None, "pipe_path": None,
             # HDevelop dev_update_{window,var,pc,time}: whether the graphics window,
             # variable window, execution cursor and per-line timings auto-update during
             # editing/execution. Turn off to make many edits (or a heavy run) without the
             # display cost; turning back on refreshes to the current state (as HDevelop
             # updates when execution stops). See docs/HDEVELOP_DEV_OPS.md.
             "dev_update": {"window": True, "var": True, "pc": True, "time": True},
             # HALCON set_system-style global config (Tools > System settings): OpenCV
             # worker threads (thread_num, affects interactive op speed) and a SOFT
             # per-stage operator timeout in ms (0 = off; a slow stage is flagged — native
             # ops cannot be hard-interrupted, same honest limit as fsruntime). Fullseye's
             # runtime error mode is always fail-closed. See docs/HDEVELOP_DEV_OPS.md (F).
             "system": {"threads": 0, "operator_timeout_ms": 0,
                        # 開ける graphics window の上限(dev_open_window / Ctrl+G / 変数表示の
                        # 全経路に効く fail-closed ガード。System settings 画面か
                        # set_system('max_graphics_windows', N) で変更可)
                        "max_graphics_windows": 256},
             # HDevelop dev_set_draw / dev_set_color / dev_set_line_width: how a region
             # result is drawn over the source in the 'region overlay' display mode.
             "draw": {"mode": "fill", "color": (0.96, 0.62, 0.14), "line_width": 1, "alpha": 0.5}}
    pmodel = PerceptionModel()

    # -- behaviour --
    def selected_index():
        return stage_list.currentRow()

    def mark_dirty():
        """Record that the in-memory pipeline no longer matches anything on disk."""
        state["dirty"] = True
        _set_title()

    def _set_title():
        """Window title = <pipeline>* — <image> — Fullseye Studio (star = unsaved)."""
        pp = state.get("pipe_path"); ip = state.get("image_path")
        star = "*" if (state.get("dirty") and model.stages) else ""
        seg = (os.path.basename(pp) if pp else "untitled") + star
        if ip:
            seg += " — " + os.path.basename(ip)
        win.setWindowTitle(seg + " — Fullseye Studio")
    win._set_title = _set_title

    def report_error(title, text):
        """Surface a recoverable failure: status bar + a modal via ERROR_HOOK.

        Also appended to ``state['errors']`` so a headless test can assert on it
        without stubbing the dialog."""
        state["errors"].append((title, str(text)))
        flash("%s: %s" % (title, truncate(text, 120)))
        try:
            ERROR_HOOK(win, title, str(text))
        except Exception:                 # a stubbed/absent dialog must never crash us
            pass

    def confirm_discard(title, what="the current pipeline"):
        """True if it is OK to throw away unsaved work — unsaved pipeline stages OR
        unapplied Program-editor edits (Codex #9). When neither is pending, no prompt."""
        pipe_dirty = state["dirty"] and bool(model.stages)
        code_dirty = bool(state.get("code_dirty"))
        # Python Editor の未保存タブも数える(アプリ終了経路のデータ損失防止)。
        # Count unsaved Python-Editor tabs too — the app-quit path must not
        # silently discard them (only per-tab close prompted before this fix).
        ed_dirty = 0
        pe = getattr(win, "_pyedit", None)
        if pe is not None:
            tabs = pe.get("tabs")
            if tabs is not None:
                ed_dirty = sum(1 for i in range(tabs.count())
                               if getattr(tabs.widget(i), "_dirty", False))
        if not (pipe_dirty or code_dirty or ed_dirty):
            return True
        parts = []
        if pipe_dirty:
            parts.append("%d unsaved stage(s)" % len(model.stages))
        if code_dirty:
            parts.append("unapplied Program edits")
        if ed_dirty:
            parts.append("%d unsaved editor tab(s)" % ed_dirty)
        return bool(CONFIRM_HOOK(
            win, title, "%s has %s.\nDiscard them?" % (what.capitalize(), " and ".join(parts))))

    def refresh_stage_list(select=None):
        """Rebuild the stage rows (and the Problems panel).

        Never renders the image: the row is selected with the list's signals still
        blocked and the knob panel is synced explicitly, so every caller renders
        exactly once afterwards instead of twice (once via currentRowChanged and
        once via its own show_result())."""
        state["reordering"] = True                    # suppress the drag-reorder handler
        stage_list.blockSignals(True)
        stage_list.clear()
        try:
            states = model.step_states()
        except Exception:
            states = []
        try:
            times = model.step_times()
        except Exception:
            times = []
        for i, (name, a, b) in enumerate(model.stages):
            st = states[i]["state"] if i < len(states) else {}
            summ = step_summary(st) if st else ""
            ms = times[i] if i < len(times) else None
            tstr = ("  ·  %.1f ms" % ms) if isinstance(ms, (int, float)) else ""
            it = QtWidgets.QListWidgetItem(f"{i + 1}. {name} (a={a:.2f},b={b:.2f})  ->  {summ}{tstr}")
            it.setData(QtCore.Qt.UserRole, i)         # model index, for drag-reorder mapping
            row = _op_row(name)
            it.setToolTip(op_tooltip(row) if row else name)
            if st.get("kind") == "error":             # mark a stage that raised at runtime
                it.setForeground(QtGui.QColor(AMBER))
                it.setToolTip("runtime error: " + truncate(st.get("message", "")))
            stage_list.addItem(it)
        if stage_list.count() == 0:                     # onboarding: guide the empty state
            hint = QtWidgets.QListWidgetItem(
                "— empty — double-click an operator, or drop an image/.json here, to start —")
            hint.setFlags(QtCore.Qt.NoItemFlags)        # non-selectable hint
            hint.setForeground(QtGui.QColor(MUTED))
            stage_list.addItem(hint)
        if select is not None and 0 <= select < len(model.stages):
            stage_list.setCurrentRow(select)           # still blocked -> no extra render
        stage_list.blockSignals(False)
        state["reordering"] = False
        refresh_problems(states)
        sync_stage_ui()
        getattr(win, "_code_sync", lambda: None)()   # keep the program (code) view in sync

    def refresh_problems(states=None):
        """Populate the Problems list: static validation (unknown op / sort mismatch,
        via engine.diagnose_stages) + runtime errors (a stage that raised) + the last
        perception failure (which used to be a status-bar flash you could easily miss)."""
        problems_list.clear()
        probs = list(engine.diagnose_stages(model.stages))     # static checks
        if states:
            for s in states:                                    # runtime errors
                if s.get("state", {}).get("kind") == "error":
                    probs.append({"index": s["index"], "op": s["op"], "severity": "error",
                                  "message": "runtime: " + truncate(s["state"].get("message", ""))})
        probs.sort(key=lambda p: (p["index"], 0 if p["severity"] == "error" else 1))
        for p in probs:
            mark = "✕" if p["severity"] == "error" else "!"
            it = QtWidgets.QListWidgetItem("%s stage %d (%s): %s"
                                           % (mark, p["index"] + 1,
                                              truncate(p.get("op", "?"), 40),
                                              truncate(p["message"])))
            it.setData(QtCore.Qt.UserRole, p["index"])
            it.setForeground(QtGui.QColor(AMBER if p["severity"] == "error" else "#c9a227"))
            problems_list.addItem(it)
        perr = state.get("perception_error")
        if perr:
            it = QtWidgets.QListWidgetItem("✕ perception (%s): %s" % (perr[0], truncate(perr[1])))
            it.setData(QtCore.Qt.UserRole, -1)
            it.setForeground(QtGui.QColor(AMBER))
            problems_list.addItem(it)
        if not probs and not perr:
            hint = QtWidgets.QListWidgetItem("no problems")
            hint.setForeground(QtGui.QColor(MUTED))
            hint.setData(QtCore.Qt.UserRole, -1)
            problems_list.addItem(hint)

    def on_rows_moved(*_):
        """A drag-reorder inside the stage list -> permute model.stages to match."""
        if state.get("reordering"):
            return
        order = [stage_list.item(r).data(QtCore.Qt.UserRole) for r in range(stage_list.count())]
        if len(order) == len(model.stages) and set(order) == set(range(len(model.stages))):
            push_undo()
            model.stages = [model.stages[i] for i in order]
            mark_dirty()
            refresh_stage_list(select=stage_list.currentRow())
            show_result()

    def _render():
        idx = selected_index()
        try:
            if idx < 0 and state.get("view_raw"):
                val = model.result_upto(-1)           # Reset -> the pre-pipeline raw image
            else:
                val = model.result_upto(idx if idx >= 0 else len(model.stages) - 1)
        except Exception as e:                        # a bad/unknown op in the chain
            view.set_message("Pipeline error\n\n%s\n\n(see the Problems list)" % str(e))
            inspector.setPlainText("pipeline error: %s" % e)
            win._img_info.setText("pipeline error")
            hist_view.clear(); state["result"] = None; state["raw"] = None
            return
        d = inspect_result(val)
        win._img_info.setText(image_info_summary(d))
        insp = format_inspection(d)
        if isinstance(val, np.ndarray) and val.ndim == 2 and _is_binary(val) and val.any():
            try:
                import detect
                objs = detect.segment_objects(val, threshold="none", min_area=1)
                if objs:
                    insp += "\n\nRegion features:\n" + detect.feature_table(objs)
            except Exception as e:
                # Best-effort enrichment only: the region table is a bonus on top of
                # a result that is already correct and displayable, and `detect`'s
                # backends can raise anything (optional deps, degenerate labelings).
                # Swallowing keeps a cosmetic extra from blanking a good result, but
                # we say so in one line instead of failing silently.
                insp += "\n\n(region features unavailable: %s)" % truncate(e, 80)
        inspector.setPlainText(insp)
        if isinstance(val, np.ndarray) and val.ndim in (2, 3):
            shown = apply_display(val, display.currentText(), base=model.image,  # region overlay uses the source
                                  draw=state["draw"])                            # dev_set_draw/color/line_width
            qi = _to_qimage(shown, QtGui)
            if qi is not None:
                pm = QtGui.QPixmap.fromImage(qi)
                # keep the user's zoom/pan across re-renders (knob tweaks / stage steps);
                # only refit when a NEW image was loaded (state['fit_next']) or the size changed.
                if state.pop("fit_next", False):
                    view.set_pixmap(pm); view.fit()
                elif not view.set_pixmap_keep_view(pm):
                    view.fit()
            view.set_data(val)
            state["result"] = shown
            state["raw"] = val
            g = val if val.ndim == 2 else imgio.ensure_gray(val)
            hq = _to_qimage(histogram_image(np.clip(g, 0, 1)), QtGui)
            if hq is not None:
                hist_view.setPixmap(QtGui.QPixmap.fromImage(hq).scaled(
                    max(hist_view.width(), 256), 70, QtCore.Qt.IgnoreAspectRatio,
                    QtCore.Qt.SmoothTransformation))
        else:
            kind = d.get("kind")
            if kind == "feature":
                view.set_message("Result is a scalar feature\n\nvalue = %s\n\n(see the Inspector below)"
                                 % d.get("value"))
            elif kind == "contour":
                view.set_message("Result is a contour set (%d contour(s))\n\nno raster preview"
                                 % d.get("n_contours", 0))
            elif kind == "none":
                view.set_message("No image loaded\n\nuse File ▸ Open image  or  Synthetic demo")
            else:
                view.set_message("Nothing to display")
            hist_view.clear(); state["result"] = None; state["raw"] = None

    def show_result():
        """Render the current result. The whole body is guarded, not just the
        pipeline call: inspect_result / apply_display / _to_qimage / histogram_image
        all run on backend output and can raise on a degenerate array (e.g. a
        0-size result under 'shaded relief'). An exception escaping here used to
        escape the Qt callback entirely."""
        if not state["dev_update"]["window"]:
            return                            # dev_update_window('off'): no auto-display
        state["renders"] += 1
        try:
            _render()
        except Exception as e:
            view.set_message("Display error\n\n%s\n\n(see the Problems list)" % truncate(e, 200))
            inspector.setPlainText("display error: %s" % e)
            hist_view.clear(); state["result"] = None; state["raw"] = None
            report_error("Display error", e)
        update_actions()

    def _enable(cond, *widgets):
        """Set the enabled state, tolerating a widget whose C++ object was torn
        down. Some controls (e.g. b_save lives inside the primary graphics
        window) can be destroyed when a graphics window is detached/closed, yet a
        queued ``currentRowChanged`` still fires this sync afterwards — calling
        ``setEnabled`` on the dead QPushButton would raise
        ``RuntimeError: Internal C++ object already deleted`` and (via the slot)
        spam the console / abort the update. Skipping dead widgets keeps the
        surviving controls in sync instead."""
        for w in widgets:
            try:
                w.setEnabled(bool(cond))
            except RuntimeError:
                pass                      # widget was deleted (torn-down window) — skip it

    def update_actions():
        """Keep every action/button that needs a selection or a displayable result
        in step with the current state, so the UI never offers a dead command."""
        i = selected_index()
        n = len(model.stages)
        has_sel = 0 <= i < n
        has_res = isinstance(state.get("result"), np.ndarray)
        _enable(has_sel, act_remove, b_rm)
        _enable(has_sel and i > 0, act_up, b_up)
        _enable(has_sel and i < n - 1, act_down, b_dn)
        _enable(has_res, act_save_res, b_save, act_3d, b_3d)
        _enable(n > 0, act_export, b_export, act_save_pipe, b_savep, act_clear)
        _enable(n > 0, act_step, b_step, act_runall, b_runall)

    def sync_stage_ui():
        """Sync the knob sliders / stage description / action states to the current
        selection. Does not render — callers own exactly one show_result()."""
        i = selected_index()
        valid = 0 <= i < len(model.stages)
        if valid:
            state["view_raw"] = False                 # selecting a stage leaves the raw view
        sa.setEnabled(valid); sb.setEnabled(valid)
        spin_a.setEnabled(valid); spin_b.setEnabled(valid)
        if valid:
            name, a, b = model.stages[i]
            sa.blockSignals(True); sb.blockSignals(True)
            sa.setValue(int(a * 100)); sb.setValue(int(b * 100))
            sa.blockSignals(False); sb.blockSignals(False)
            spin_a.blockSignals(True); spin_b.blockSignals(True)
            spin_a.setValue(a); spin_b.setValue(b)
            spin_a.blockSignals(False); spin_b.blockSignals(False)
            row = _op_row(name)
            a_role, b_role = op_arg_roles(name)
            la.setText("a: %.2f%s" % (a, ("  ·  " + a_role) if a_role else ""))
            lb.setText("b: %.2f%s" % (b, ("  ·  " + b_role) if b_role else ""))
            stage_detail.setText(op_signature_detail(row) if row else name)
        else:
            stage_detail.setText("select a stage to tune its knobs")
        update_actions()

    def on_stage_selected():
        sync_stage_ui()
        show_result()
        # step-through frontier: grey out variables past the current stage (Codex #8).
        # Guarded because early build-time selections fire before the helper is defined.
        getattr(win, "_mark_variable_frontier", lambda: None)()

    def on_knob(_=None):
        """A knob tick: update the model + the live preview only.

        The per-stage summaries (model.step_states(), which re-runs every prefix and
        is therefore O(n^2) in the number of stages) are debounced onto a timer, so
        dragging a slider costs one pipeline evaluation per tick instead of n + 2."""
        i = selected_index()
        if 0 <= i < len(model.stages):
            if getattr(win, "_knob_drag_base", None) is None:
                # first tick of a drag: capture the PRE-drag pipeline once; the settled
                # handler turns it into a single undo entry (drags coalesce)
                win._knob_drag_base = [list(st) for st in model.stages]
            model.set_knobs(i, a=sa.value() / 100.0, b=sb.value() / 100.0)
            la.setText(f"a: {sa.value()/100:.2f}"); lb.setText(f"b: {sb.value()/100:.2f}")
            spin_a.blockSignals(True); spin_a.setValue(sa.value() / 100.0); spin_a.blockSignals(False)
            spin_b.blockSignals(True); spin_b.setValue(sb.value() / 100.0); spin_b.blockSignals(False)
            mark_dirty()
            show_result()
            knob_timer.start(KNOB_DEBOUNCE_MS)

    def on_spin(_=None):
        """Precise numeric knob entry: the spin boxes are the exact source and the
        coarse sliders follow (without re-triggering on_knob). Shares on_knob's
        drag-coalescing undo + debounced-summary tail."""
        i = selected_index()
        if 0 <= i < len(model.stages):
            a, b = spin_a.value(), spin_b.value()
            sa.blockSignals(True); sb.blockSignals(True)
            sa.setValue(int(round(a * 100))); sb.setValue(int(round(b * 100)))
            sa.blockSignals(False); sb.blockSignals(False)
            if getattr(win, "_knob_drag_base", None) is None:
                win._knob_drag_base = [list(st) for st in model.stages]
            model.set_knobs(i, a=a, b=b)
            la.setText(f"a: {a:.3f}"); lb.setText(f"b: {b:.3f}")
            mark_dirty()
            show_result()
            knob_timer.start(KNOB_DEBOUNCE_MS)

    def on_knob_settled():
        """Debounce tail: refresh the summaries + commit ONE undo entry for the drag."""
        i = selected_index()
        refresh_stage_list(select=i if 0 <= i < len(model.stages) else None)
        base = getattr(win, "_knob_drag_base", None)
        win._knob_drag_base = None
        if base is not None and base != [list(st) for st in model.stages]:
            win._undo_stack.append(base)
            if len(win._undo_stack) > _UNDO_CAP:
                del win._undo_stack[0]
            win._redo_stack.clear()
            _sync_undo_actions()

    knob_timer = QtCore.QTimer(win)
    knob_timer.setSingleShot(True)
    knob_timer.timeout.connect(on_knob_settled)

    # ---- undo / redo of pipeline edits (Codex #10) -------------------------- #
    # History of pipeline snapshots (each = a list of (op, a, b) tuples). Every
    # mutating action snapshots the CURRENT pipeline via push_undo() *before*
    # changing it; undo/redo swap between the stacks. A fresh edit forks history
    # (clears redo). Knob drags coalesce: the pre-drag state is captured on the
    # first tick and committed as one entry when the drag settles.
    win._undo_stack = []
    win._redo_stack = []
    win._knob_drag_base = None
    _UNDO_CAP = 100

    def _sync_undo_actions():
        act_undo.setEnabled(bool(win._undo_stack))
        act_redo.setEnabled(bool(win._redo_stack))

    def _snapshot():
        # DEEP copy: each stage is a mutable [op, a, b] list that set_knobs edits in
        # place — a shallow list(model.stages) shared the inner lists, so dragging a
        # knob silently rewrote every snapshot already in the undo/redo stacks.
        return [list(st) for st in model.stages]

    def push_undo():
        win._undo_stack.append(_snapshot())
        if len(win._undo_stack) > _UNDO_CAP:
            del win._undo_stack[0]
        win._redo_stack.clear()
        _sync_undo_actions()

    def _restore_stages(stages):
        model.stages = [list(st) for st in stages]
        mark_dirty()
        refresh_stage_list(select=(len(model.stages) - 1) if model.stages else None)
        show_result()
        _sync_undo_actions()

    def undo():
        if not win._undo_stack:
            return
        win._redo_stack.append(_snapshot())
        _restore_stages(win._undo_stack.pop())
        flash("undo (%d more)" % len(win._undo_stack))

    def redo():
        if not win._redo_stack:
            return
        win._undo_stack.append(_snapshot())
        _restore_stages(win._redo_stack.pop())
        flash("redo (%d more)" % len(win._redo_stack))
    win._undo = undo
    win._redo = redo
    win._push_undo = push_undo

    def add_op(item):
        name = item.data(QtCore.Qt.UserRole)
        row = _op_row(name)
        if row and row.get("backend") == "general":     # double-click on a read-only general op
            flash("‘%s’ is a general-algorithm op (seq/scalar) — run it via CLI: "
                  "imgevolve.py algo run %s" % (name, name))
            return
        push_undo()
        i = selected_index()
        # insert with the args entered in the operator panel (HDevelop-style)
        model.add_stage(name, op_a_spin.value(), op_b_spin.value())
        newpos = len(model.stages) - 1
        if 0 <= i < newpos:                                  # insert just after the selected stage
            model.move_stage(newpos, i + 1); newpos = i + 1
        mark_dirty()
        refresh_stage_list(select=newpos)
        show_result()

    def run_op_once():
        """HDevelop single-step: apply the selected operator ONCE with the a, b from
        the operator panel to the loaded image, and show the result in a graphics
        window. The pipeline is NOT modified (a scratch preview)."""
        cur = op_list.currentItem()
        if cur is None:
            return
        name = cur.data(QtCore.Qt.UserRole)
        row = _op_row(name)
        if row and row.get("backend") == "general":
            flash("‘%s’ is a general-algorithm op (seq/scalar) — run it via CLI: "
                  "imgevolve.py algo run %s" % (name, name))
            return
        base = model.image
        if base is None:
            flash("load an image first (File ▸ Open image / Synthetic demo)")
            return
        a, b = op_a_spin.value(), op_b_spin.value()
        try:
            out = api.apply(base, name, a, b)
        except Exception as e:
            report_error("Run once", e)
            return
        title = "%s (a=%.2f, b=%.2f)" % (name, a, b)
        pm = None
        if isinstance(out, np.ndarray) and out.ndim in (2, 3):
            qi = _to_qimage(apply_display(out, display.currentText()), QtGui)
            pm = QtGui.QPixmap.fromImage(qi) if qi is not None else None
        if pm is not None:
            cur = win._current_gfx
            if cur is None or cur is win._primary_gsub or cur not in win._graphics_windows:
                # default (current = the resident main window): open a fresh scratch
                # window so the single-shot preview never clobbers the pipeline result
                new_graphics_window(pm, title)
                flash("ran %s once — result in a new graphics window (pipeline unchanged)" % name)
            else:
                # a secondary window is current: reuse it (HDevelop dev_display) so
                # repeated Run-once tuning doesn't spawn a new window every time
                v = _current_view()
                v.set_pixmap(pm); v.fit(); v.set_data(out)
                flash("ran %s once → Graphics %d (pipeline unchanged)" % (name, _current_handle()))
        else:                                   # scalar feature / contour: no raster preview
            d = inspect_result(out)
            flash("ran %s once → %s (pipeline unchanged)" % (name, d.get("value", d.get("kind", "result"))))
        win._last_run_once = {"op": name, "a": a, "b": b, "result": out}
    win._run_op_once = run_op_once
    win._op_arg_spins = (op_a_spin, op_b_spin)
    win._op_list = op_list
    win._op_buttons = {"insert": b_insert, "run_once": b_run_once, "help": b_help}
    win._op_list = op_list            # exposed for tests (verify the general tier is read-only)
    win._search = search              # exposed for tests (keyboard op insertion)
    win._op_names = op_names          # image-only names fed to the code parser / help picker

    def _select_var_row(row):
        """Highlight a variable in the Variable window (step-execution sync)."""
        if 0 <= row < var_list.count():
            var_list.setCurrentRow(row)
    win._select_var_row = _select_var_row

    def step_to(i):
        if not (0 <= i < len(model.stages)):
            return
        if stage_list.count() != len(model.stages):          # self-heal a desynced UI list
            refresh_stage_list(select=i)
        stage_list.setCurrentRow(i)                          # triggers show_result for that step
        _select_var_row(i + 1)                               # sync: highlight this step's output var
        flash("step %d/%d — %s (showing this stage's result)"
              % (i + 1, len(model.stages), model.stages[i][0]))
    win._step_to = step_to

    def reset_to_raw():
        """Show the pre-pipeline (raw) image — the start of the step-through."""
        state["view_raw"] = True
        if stage_list.currentRow() == -1:
            on_stage_selected()                             # no row change -> refresh explicitly
        else:
            stage_list.setCurrentRow(-1)                    # currentRowChanged -> on_stage_selected

    def load_sample(idx):
        if idx <= 0:
            return
        if not confirm_discard("Load sample pipeline"):
            samples.blockSignals(True); samples.setCurrentIndex(0); samples.blockSignals(False)
            return
        try:
            snap = [list(st) for st in model.stages]
            model.load_recipe(samples.itemText(idx))
        except Exception as e:
            report_error("Sample pipeline", e); return
        win._undo_stack.append(snap)          # only a SUCCESSFUL load forks history
        if len(win._undo_stack) > _UNDO_CAP:
            del win._undo_stack[0]
        win._redo_stack.clear(); _sync_undo_actions()
        mark_dirty()
        refresh_stage_list(select=len(model.stages) - 1)
        show_result()
        flash("loaded sample '%s' — its code is now in the Program panel" % samples.itemText(idx))
        try:                                  # surface the code so the sample is easy to read/run
            win._docks["program"].show(); win._docks["program"].raise_()
        except Exception:
            pass

    def remove():
        i = selected_index()
        if 0 <= i < len(model.stages):
            push_undo()
            model.remove_stage(i)
            mark_dirty()
            n = len(model.stages)
            # keep a neighbour selected so the operation target isn't lost after a
            # delete (Codex #11) — the stage now at i, or the new last one
            sel = min(i, n - 1) if n > 0 else None
            refresh_stage_list(select=sel)
            show_result()

    def move(delta):
        i = selected_index(); j = i + delta
        if 0 <= i < len(model.stages) and 0 <= j < len(model.stages):
            push_undo()
            model.move_stage(i, j); mark_dirty()
            refresh_stage_list(select=j); show_result()

    def duplicate_stage_ui():
        i = selected_index()
        if 0 <= i < len(model.stages):
            push_undo()
            j = model.duplicate_stage(i); mark_dirty()
            refresh_stage_list(select=j); show_result()

    def move_to_end(to_top):
        i = selected_index(); n = len(model.stages)
        if not (0 <= i < n):
            return
        j = 0 if to_top else n - 1
        if j != i:
            push_undo()
            model.move_stage(i, j); mark_dirty()
            refresh_stage_list(select=j); show_result()

    def _load_image_path(path):
        try:
            arr = imgio.load(path)                # missing / undecodable / permission
        except Exception as e:
            report_error("Could not open image", "%s\n\n%s" % (path, e)); return False
        model.set_image(arr)
        state["image_path"] = os.path.abspath(path)
        state["fit_next"] = True                      # a new image should fit the view
        _push_recent(path); _set_title()
        flash("loaded " + os.path.basename(path))
        show_result()
        return True

    def load_image():
        path, _ = QtWidgets.QFileDialog.getOpenFileName(win, "Open image", "",
                                                        "Images (*.png *.jpg *.bmp *.tif)")
        if path:
            _load_image_path(path)

    def use_demo():
        model.set_image(demo_image()); state["fit_next"] = True; show_result()

    def load_sample_image(name):
        """Load one of the collected, license-clean sample images (sample_images.py)."""
        try:
            import sample_images
            model.set_image(sample_images.load(name))
        except Exception as e:
            report_error("Could not load sample image", "%s\n\n%s" % (name, e)); return
        state["fit_next"] = True
        flash("loaded sample image: " + name); show_result()
    win._load_sample_image = load_sample_image

    def load_visual_demo():
        """dev_* visualization demo: load the coins sample image and a Program that
        actually USES the HDevelop dev_set_draw / dev_set_color / dev_disp_text ops."""
        load_sample_image(HDEV_VISUAL_DEMO_IMAGE)
        code_edit.setPlainText(HDEV_VISUAL_DEMO)
        apply_program()
        try:
            win._docks["program"].show(); win._docks["program"].raise_()
        except Exception:
            pass
        flash("loaded dev_* visualization demo")
    win._load_visual_demo = load_visual_demo

    def save_result():
        if state["result"] is None:
            flash("nothing to save — run the pipeline first"); return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(win, "Save result", "result.png",
                                                        "PNG (*.png);;All files (*)")
        if not path:
            return
        try:
            imgio.save(path, state["result"])     # permission / bad extension / full disk
        except Exception as e:
            report_error("Could not save result", "%s\n\n%s" % (path, e)); return
        # Ctrl+S saves a PNG of the RESULT; the dirty '*' tracks the PIPELINE. If the
        # pipeline has unsaved edits, say which key saves it so the star isn't a mystery.
        if state.get("dirty") and model.stages:
            flash("saved %s  ·  (Ctrl+Shift+S saves the pipeline itself)" % os.path.basename(path))
        else:
            flash("saved " + os.path.basename(path))

    def copy_result():
        if state.get("result") is None:
            flash("nothing to copy — run the pipeline first"); return
        qi = _to_qimage(state["result"], QtGui)
        if qi is not None:
            QtWidgets.QApplication.clipboard().setImage(qi)
            flash("copied result image to clipboard")

    def export():
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Export"); v = QtWidgets.QVBoxLayout(dlg)
        tag_dialog(dlg, "editor")
        text = '--ops "' + model.ops_string() + '"\n\n' + model.export_python()
        te = QtWidgets.QPlainTextEdit(); te.setPlainText(text); te.setReadOnly(True)
        te.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
        v.addWidget(te)
        row = QtWidgets.QHBoxLayout(); row.addStretch(1)
        b_copy = QtWidgets.QPushButton("Copy"); b_copy.setToolTip("Copy the export text to the clipboard")
        b_savepy = QtWidgets.QPushButton("Save .py…"); b_savepy.setProperty("accent", True)
        b_savepy.setToolTip("Save the runnable pipeline as a Python file")
        row.addWidget(b_copy); row.addWidget(b_savepy); v.addLayout(row)

        def _copy_export():
            QtWidgets.QApplication.clipboard().setText(text)
            flash("copied export to the clipboard")

        def _save_py():
            path, _ = QtWidgets.QFileDialog.getSaveFileName(dlg, "Save pipeline as Python",
                                                            "pipeline.py", "Python (*.py)")
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(model.export_python())
            except Exception as e:
                report_error("Could not save Python", "%s\n\n%s" % (path, e)); return
            flash("saved " + os.path.basename(path))
        b_copy.clicked.connect(_copy_export); b_savepy.clicked.connect(_save_py)
        dlg.setModal(False); win._export_dlg = dlg    # non-modal: keep working while it is open
        dlg.resize(560, 400); dlg.show()

    def clear_pipe():
        if not confirm_discard("Clear pipeline"):
            return
        push_undo()
        model.stages = []
        state["pipe_path"] = None
        mark_dirty()
        refresh_stage_list(); show_result()
        flash("pipeline cleared")

    _IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

    def _show_holdout_report(summary):
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Holdout validation")
        tag_dialog(dlg, "editor")
        v = QtWidgets.QVBoxLayout(dlg)
        head = "%d image(s): %d ran, %d failed · mean %.1f ms" % (
            summary["n"], summary["n_ok"], summary["n_err"], summary["mean_ms"])
        if summary["mean_metric"] is not None:
            head += " · mean %s %.3f" % (summary["metric_kind"], summary["mean_metric"])
        lbl = QtWidgets.QLabel(head); lbl.setStyleSheet("font-weight:700;"); v.addWidget(lbl)
        kind = summary["metric_kind"] or "metric"
        tbl = QtWidgets.QTableWidget(len(summary["results"]), 4)
        tbl.setHorizontalHeaderLabels(["image", "status", "ms", kind])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        for r, rec in enumerate(summary["results"]):
            tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(os.path.basename(rec["path"])))
            status = "ok" if rec["ok"] else ("error: " + rec["error"][:60])
            it = QtWidgets.QTableWidgetItem(status)
            if not rec["ok"]:
                it.setForeground(QtGui.QColor(AMBER))
            tbl.setItem(r, 1, it)
            tbl.setItem(r, 2, QtWidgets.QTableWidgetItem("%.1f" % rec["ms"]))
            tbl.setItem(r, 3, QtWidgets.QTableWidgetItem("" if rec["metric"] is None else "%.3f" % rec["metric"]))
        tbl.resizeColumnsToContents(); tbl.horizontalHeader().setStretchLastSection(True)
        v.addWidget(tbl)
        note = QtWidgets.QLabel("Honest note: a metric is only shown when an aligned ground-truth "
                               "folder was given and shapes match; otherwise this is a ran/failed + "
                               "timing check.")
        note.setWordWrap(True); note.setProperty("muted", True); v.addWidget(note)
        okb = QtWidgets.QPushButton("Close"); okb.setProperty("accent", True); okb.clicked.connect(dlg.accept)
        v.addWidget(okb, 0, QtCore.Qt.AlignRight)
        dlg.resize(600, 480)
        win._holdout_dialog = dlg
        dlg.exec()

    def show_holdout():
        """HDevelop-style batch validation: run the current pipeline over a folder of
        holdout images (+ an optional aligned ground-truth folder) and report results —
        imgevolve's honest 'does it generalise to unseen images' gate, in the UI."""
        if not model.stages:
            flash("build a pipeline first, then validate it on a holdout set"); return
        folder = QtWidgets.QFileDialog.getExistingDirectory(win, "Holdout image folder")
        if not folder:
            return
        try:
            names = sorted(f for f in os.listdir(folder) if f.lower().endswith(_IMG_EXTS))
        except OSError as e:
            report_error("Holdout folder", e); return
        paths = [os.path.join(folder, f) for f in names]
        if not paths:
            flash("no images (%s) in that folder" % "/".join(e[1:] for e in _IMG_EXTS)); return
        gt_dir = QtWidgets.QFileDialog.getExistingDirectory(
            win, "Ground-truth folder (optional — Cancel to skip)")
        gt_paths = None
        if gt_dir:
            gt_paths = [os.path.join(gt_dir, n) if os.path.exists(os.path.join(gt_dir, n)) else None
                        for n in names]
        summary = run_holdout(model.stages, paths, gt_paths)
        win._last_holdout = summary
        flash("holdout: %d ran, %d failed%s" % (
            summary["n_ok"], summary["n_err"],
            ("" if summary["mean_metric"] is None
             else " · mean %s %.3f" % (summary["metric_kind"], summary["mean_metric"]))))
        _show_holdout_report(summary)
    win._show_holdout = show_holdout
    win._show_holdout_report = _show_holdout_report
    act_holdout.triggered.connect(show_holdout)

    def show_about():
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("About Fullseye Studio")
        tag_dialog(dlg, "system")
        v = QtWidgets.QVBoxLayout(dlg)
        row = QtWidgets.QHBoxLayout()
        if os.path.exists(_ICON_PATH):
            ic = QtWidgets.QLabel(); ic.setPixmap(QtGui.QIcon(_ICON_PATH).pixmap(64, 64))
            ic.setStyleSheet("padding:4px 12px 4px 4px;"); row.addWidget(ic, 0, QtCore.Qt.AlignTop)
        txt = QtWidgets.QLabel(
            "<b style='font-size:16px; color:%s'>Fullseye Studio</b><br>"
            "<span style='color:%s'>image pipeline workbench · v%s</span><br><br>"
            "Interactively build, tune, step through and export fullseye image-operator "
            "pipelines — then evolve and codegen HALCON-parity operators.<br><br>"
            "<span style='color:%s'>Part of the FullSense ecosystem.</span>"
            % (AMBER, MUTED, api.version(), MUTED))
        txt.setTextFormat(QtCore.Qt.RichText); txt.setWordWrap(True); row.addWidget(txt, 1)
        v.addLayout(row)
        ok = QtWidgets.QPushButton("Close"); ok.setProperty("accent", True); ok.clicked.connect(dlg.accept)
        v.addWidget(ok, 0, QtCore.Qt.AlignRight)
        dlg.resize(480, 220); dlg.exec()

    def show_shortcuts():
        rows = shortcut_table([(a.text(), a.shortcut().toString()) for a in win._actions.values()])
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Keyboard shortcuts")
        tag_dialog(dlg, "reference")
        v = QtWidgets.QVBoxLayout(dlg)
        tbl = QtWidgets.QTableWidget(len(rows), 2)
        tbl.setHorizontalHeaderLabels(["Action", "Shortcut"])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for r, (lbl, sc) in enumerate(rows):
            tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(lbl))
            tbl.setItem(r, 1, QtWidgets.QTableWidgetItem(sc))
        tbl.resizeColumnsToContents()
        tbl.horizontalHeader().setStretchLastSection(True)
        v.addWidget(tbl)
        ok = QtWidgets.QPushButton("Close"); ok.setProperty("accent", True); ok.clicked.connect(dlg.accept)
        v.addWidget(ok, 0, QtCore.Qt.AlignRight)
        dlg.resize(460, 540); dlg.exec()

    def show_op_reference():
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Operator reference")
        tag_dialog(dlg, "reference")
        v = QtWidgets.QVBoxLayout(dlg)
        srch = QtWidgets.QLineEdit(); srch.setPlaceholderText("search operators…")
        srch.setClearButtonEnabled(True)
        lst = QtWidgets.QListWidget()
        detail = QtWidgets.QPlainTextEdit(); detail.setReadOnly(True); detail.setFixedHeight(96)
        detail.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
        rows = api.list_ops()

        def refill(_=None):
            kw = srch.text().lower(); lst.clear()
            for r in rows:
                hay = r.get("_search")
                if hay is None:
                    # search the same vocabulary the generated sample comments use
                    # (category, HALCON counterpart, signal sorts) PLUS the op docstring,
                    # so a word seen in any sample comment finds the related operators
                    doc = ""
                    try:
                        _fn = getattr(api.find_op(r["name"]), "fn", None)
                        doc = " ".join(((getattr(_fn, "__doc__", "") or "").split())[:40])
                    except Exception:
                        pass
                    hay = r["_search"] = " ".join(
                        [r["name"], r.get("halcon") or "", r["category"],
                         r.get("in_sort", ""), r.get("out_sort", ""), r.get("tier", ""),
                         doc]).lower()
                if kw and kw not in hay:
                    continue
                it = QtWidgets.QListWidgetItem(op_detail(r)); it.setData(QtCore.Qt.UserRole, r)
                lst.addItem(it)

        def show_detail(_=None):
            it = lst.currentItem()
            if it is not None:
                detail.setPlainText(op_tooltip(it.data(QtCore.Qt.UserRole)))
        srch.textChanged.connect(refill); lst.currentRowChanged.connect(lambda _=None: show_detail())
        refill()
        cnt = QtWidgets.QLabel("%d operators" % len(rows)); cnt.setProperty("muted", True)
        v.addWidget(srch); v.addWidget(lst, 1); v.addWidget(cnt); v.addWidget(detail)
        ok = QtWidgets.QPushButton("Close"); ok.setProperty("accent", True); ok.clicked.connect(dlg.accept)
        v.addWidget(ok, 0, QtCore.Qt.AlignRight)
        dlg.resize(560, 580); dlg.exec()

    # dialog frame colors by FUNCTION (user spec: tell windows apart at a glance).
    # One hue per category — viewers teal, references amber, editors violet, system gray.
    _DLG_KIND_COLORS = {
        "viewer": "#2dd4bf",      # 表示系(3D/アニメ/Physical AI)
        "reference": "#f59e0b",   # リファレンス(op help / shortcuts / samples)
        "editor": "#a78bfa",      # 編集・実行系(export / holdout / palette)
        "system": "#64748b",      # 設定・情報系(settings / about)
    }

    def tag_dialog(dlg, kind, backend=None):
        """Mark a dialog's FUNCTION with a colored frame and, for display windows,
        state WHAT the view is based on in the title (user spec: the title must say
        MuJoCo / matplotlib / ... — the habit matters once RViz/Gazebo sources join).
        Unknown kind falls back to the system gray; never raises."""
        try:
            color = _DLG_KIND_COLORS.get(kind, _DLG_KIND_COLORS["system"])
            dlg.setStyleSheet((dlg.styleSheet() or "")
                              + "QDialog { border: 2px solid %s; }" % color)
            if backend:
                dlg.setWindowTitle(dlg.windowTitle() + "  [%s]" % backend)
        except Exception:
            pass                                   # cosmetics must never break a dialog

    def persist_dialog_geometry(dlg, key, default_size=(820, 540)):
        # Remember a dialog's position/size across close/reopen AND across sessions
        # (user spec — on multi-display setups the second screen placement must stick).
        # Same QSettings store as the main window; the test suite redirects it to a
        # temp INI, so this stays hermetic under pytest.
        sset = QtCore.QSettings("Fullseye", "Studio")
        geo = sset.value("dialogs/%s_geometry" % key)
        if geo is not None:
            dlg.restoreGeometry(geo)
            # a remembered position can be OFF-SCREEN today (monitor unplugged,
            # resolution changed) — pull it back into the visible area (user spec):
            # "visible" means a usable slab of the title bar, not a 1-px sliver
            fg = dlg.frameGeometry()
            vis = any(sc.availableGeometry().intersected(fg).width() >= 80
                      and sc.availableGeometry().intersected(fg).height() >= 40
                      for sc in QtGui.QGuiApplication.screens())
            if not vis:
                avail = QtGui.QGuiApplication.primaryScreen().availableGeometry()
                dlg.resize(min(fg.width(), avail.width()),
                           min(fg.height(), avail.height()))
                dlg.move(avail.center() - dlg.rect().center())
        else:
            dlg.resize(*default_size)
        orig_close = dlg.closeEvent

        def _close(ev):
            QtCore.QSettings("Fullseye", "Studio").setValue(
                "dialogs/%s_geometry" % key, dlg.saveGeometry())
            orig_close(ev)
        dlg.closeEvent = _close

    def show_samples():
        # Sequential-browsing gallery (user spec): open samples one after another,
        # filter by word, close what you don't need, COPY the code you do — in either
        # form (one-shot function or the staged, stage-by-stage twin). Non-modal on
        # purpose: on a multi-display setup it can stay open on another screen while
        # Studio keeps working (same idea as "Float all panels").
        if getattr(win, "_samples_dlg", None) is not None:
            win._samples_dlg.show(); win._samples_dlg.raise_(); win._samples_dlg.activateWindow()
            return
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Samples & code")
        tag_dialog(dlg, "reference")
        dlg.setModal(False)                        # lives beside Studio, not on top of it
        h = QtWidgets.QHBoxLayout(dlg)
        filt = QtWidgets.QLineEdit()
        filt.setPlaceholderText("filter samples… (name or ops words)")
        lst = QtWidgets.QListWidget()

        def refill(_=None):
            # filter by recipe NAME or by words in its ops string, so "otsu" or
            # "bilateral" finds every sample that uses that operator
            kw = filt.text().lower()
            lst.clear()
            for nm in recipes.names():
                ops = (sample_code(nm) or ("", ""))[0].lower()
                if not kw or kw in nm.lower() or kw in ops:
                    lst.addItem(nm)
            if lst.count():
                lst.setCurrentRow(0)
            else:
                code.setPlainText("")
        filt.textChanged.connect(refill)

        code = QtWidgets.QPlainTextEdit(); code.setReadOnly(True)
        code.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
        dlg._code_hl = _python_highlighter_class(QtGui, QtCore)(code.document())
        thumb = QtWidgets.QLabel()                 # pre-rendered result (input -> output)
        thumb.setAlignment(QtCore.Qt.AlignCenter)
        thumb.setToolTip("Pre-rendered result of this sample on a bundled sample image "
                         "(left: input, right: output) — regenerate with "
                         "tools/gen_sample_thumbs.py")
        thumb.setVisible(False)

        def preview(_=None):
            it = lst.currentItem()
            if it is not None:
                sc = sample_code(it.text())
                code.setPlainText(('--ops "%s"' % sc[0] + chr(10) * 2 + sc[1]) if sc else "")
                tp = sample_thumb_path(it.text())  # show the result image when we have one
                if tp:
                    pm = QtGui.QPixmap(tp)
                    if not pm.isNull():
                        thumb.setPixmap(pm.scaledToWidth(
                            min(520, pm.width()), QtCore.Qt.SmoothTransformation))
                        thumb.setVisible(True)
                        return
                thumb.clear(); thumb.setVisible(False)
        lst.currentRowChanged.connect(lambda _=None: preview())

        def copy_code(staged):
            # clipboard hand-off is the point of the gallery: browse -> copy -> use.
            # staged=False copies the one-shot function, True the *_staged twin.
            it = lst.currentItem()
            if it is None:
                return
            sc = sample_code(it.text())
            if not sc:
                return
            cut = sc[1].rindex("import fullseye")   # the staged form's own header
            text = (sc[1][cut:] if staged else sc[1][:cut].rstrip() + chr(10))
            QtWidgets.QApplication.clipboard().setText(text)
            flash("copied %s form of '%s' to the clipboard"
                  % ("staged" if staged else "one-shot", it.text()))

        def load_sample():
            # keep the dialog OPEN after loading — sequential browsing means the user
            # may load one, look at Studio, come back and try the next
            it = lst.currentItem()
            if it is None:
                return
            if not confirm_discard("Load sample pipeline"):
                return
            try:
                model.load_recipe(it.text())
            except Exception as e:
                report_error("Sample pipeline", e); return
            mark_dirty()
            refresh_stage_list(select=len(model.stages) - 1); show_result()
            flash("loaded sample '%s' — the gallery stays open" % it.text())

        left = QtWidgets.QVBoxLayout()
        lbl = QtWidgets.QLabel("Sample pipelines"); lbl.setProperty("muted", True)
        b_load = QtWidgets.QPushButton("Load into Studio"); b_load.setProperty("accent", True)
        b_load.clicked.connect(load_sample)
        left.addWidget(lbl); left.addWidget(filt); left.addWidget(lst, 1); left.addWidget(b_load)
        right = QtWidgets.QVBoxLayout()
        clbl = QtWidgets.QLabel("Code (ops string + one-shot + staged)")
        clbl.setProperty("muted", True)
        right.addWidget(thumb)                    # result preview sits above the code
        row = QtWidgets.QHBoxLayout()
        b_copy1 = QtWidgets.QPushButton("Copy one-shot")
        b_copy2 = QtWidgets.QPushButton("Copy staged")
        b_copy1.setToolTip("Copy the single-call pipeline function to the clipboard")
        b_copy2.setToolTip("Copy the stage-by-stage form (splice single stages, add if/for)")
        b_copy1.clicked.connect(lambda: copy_code(False))
        b_copy2.clicked.connect(lambda: copy_code(True))
        row.addWidget(b_copy1); row.addWidget(b_copy2); row.addStretch(1)
        right.addWidget(clbl); right.addWidget(code, 1); right.addLayout(row)
        h.addLayout(left, 1); h.addLayout(right, 2)
        refill()
        persist_dialog_geometry(dlg, "samples")    # position remembered across sessions
        win._samples_dlg = dlg                     # reuse; hidden on close, shown on reopen
        dlg.show()

    def show_3d_ops():
        # 3-D operator reference: browse all ops3d operators (point-cloud / mesh / volume) with
        # their generated help pages (op_help/3d/<name>.html, single-sourced from the
        # docs/ops/3d Markdown corpus by tools/opdocs.py). Separate from the 2-D op reference
        # because the two modalities carry different sorts and 2-D/3-D op names can collide
        # (e.g. fill_holes). Related-op links (op3d:) navigate within this dialog; example3d:
        # links show the worked-example source.
        if getattr(win, "_ops3d_dlg", None) is not None:
            win._ops3d_dlg.show(); win._ops3d_dlg.raise_(); win._ops3d_dlg.activateWindow()
            return
        try:
            import ops3d as O3
        except Exception as e:
            report_error("3-D operators", e); return
        reg = O3.OPS3D
        names = sorted(reg.keys())
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("3-D Operators — Fullseye 3D vision")
        tag_dialog(dlg, "reference"); dlg.setModal(False)
        h = QtWidgets.QHBoxLayout(dlg)

        def _kind(v):
            return " × ".join(v) if isinstance(v, (list, tuple)) else str(v)

        left = QtWidgets.QVBoxLayout()
        lbl = QtWidgets.QLabel("3-D operators (%d) — point-cloud / mesh / volume" % len(names))
        lbl.setProperty("muted", True)
        filt = QtWidgets.QLineEdit(); filt.setPlaceholderText("filter by name / category / kind…")
        filt.setClearButtonEnabled(True)
        lst = QtWidgets.QListWidget()

        def refill(_=None):
            q = filt.text().strip().lower(); lst.clear()
            for n in names:
                info = reg[n]
                hay = (n + " " + info["category"] + " " + _kind(info["in"]) + " "
                       + str(info["out"]) + " " + (info.get("doc") or "")).lower()
                if q and q not in hay:
                    continue
                it = QtWidgets.QListWidgetItem("[%s] %s  ·  %s → %s"
                                               % (info["category"], n, _kind(info["in"]), info["out"]))
                it.setData(QtCore.Qt.UserRole, n); lst.addItem(it)
            if lst.count():
                lst.setCurrentRow(0)
        filt.textChanged.connect(refill)
        left.addWidget(lbl); left.addWidget(filt); left.addWidget(lst, 1)

        br = QtWidgets.QTextBrowser(); br.setOpenLinks(False); br.setOpenExternalLinks(False)

        def show3d(n):
            if n:
                br.setHtml(op_help_html_3d(n, reg.get(n)))

        def _select(n):
            for row in range(lst.count()):
                if lst.item(row).data(QtCore.Qt.UserRole) == n:
                    lst.blockSignals(True); lst.setCurrentRow(row); lst.blockSignals(False)
                    break

        def _anchor(url):
            s = url.toString()
            if s.startswith("op3d:"):            # jump to a type-compatible / same-category 3-D op
                n = s[5:]
                if n in reg:
                    _select(n); show3d(n)
            elif s.startswith("example3d:"):     # show a worked-example's source
                ex = s.split(":", 1)[1]
                p = os.path.join(os.path.dirname(_ASSETS), "examples_3d", ex + ".py")
                if os.path.exists(p):
                    try:
                        with open(p, encoding="utf-8") as f:
                            src = f.read()
                        esc = src.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        br.setHtml("<h2 style='color:#f5a524'>%s</h2>"
                                   "<p style='color:#8b91a0'>実行できる検証済みサンプル · "
                                   "<code>py -3.11 examples_3d/%s.py</code></p>"
                                   "<pre style='background:#12141b;border:1px solid #2c313f;"
                                   "padding:6px;color:#22d3bf'>%s</pre>" % (ex, ex, esc))
                    except Exception:
                        pass
                else:
                    flash("example source not found: examples_3d/%s.py" % ex)
        br.anchorClicked.connect(_anchor)
        lst.currentRowChanged.connect(
            lambda _=None: show3d(lst.currentItem().data(QtCore.Qt.UserRole)) if lst.currentItem() else None)

        h.addLayout(left, 1); h.addWidget(br, 2)
        refill()
        if lst.count():
            show3d(lst.currentItem().data(QtCore.Qt.UserRole))
        dlg.resize(940, 620)
        win._ops3d_dlg = dlg
        win._ops3d = {"dialog": dlg, "list": lst, "browser": br, "show": show3d}
        dlg.show(); dlg.raise_(); dlg.activateWindow()

    def show_3d_examples():
        # 3-D toolkit gallery: browse the ops3d worked examples (real Itokawa / skeleton-CT /
        # synthetic data), read each one's ground-truth-checked code, RUN it in place to see the
        # ground-truth output, or copy it to run standalone (py -3.11 examples_3d/<id>.py). The
        # 3-D ops are a different modality (point clouds / meshes / volumes) than the 2-D image
        # pipeline, so these are runnable code samples, not loaded into the pipeline. Sourced
        # from the examples3d registry (validate()-checked).
        if getattr(win, "_ex3d_dlg", None) is not None:
            win._ex3d_dlg.show(); win._ex3d_dlg.raise_(); win._ex3d_dlg.activateWindow()
            return
        try:
            import examples3d as EX
        except Exception as e:
            report_error("3-D examples", e); return
        repo_root = os.path.dirname(os.path.abspath(EX.__file__))
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("3-D Examples — Fullseye 3D vision")
        tag_dialog(dlg, "reference"); dlg.setModal(False)
        h = QtWidgets.QHBoxLayout(dlg)

        # -- left: filter + list (grouped by task) --
        meta = {}
        rows = []
        for task, ids in EX.by_task().items():
            for i in ids:
                e = EX.get(i); meta[i] = e
                rows.append((i, task, "[%s] %s" % (task, e["name"])))
        left = QtWidgets.QVBoxLayout()
        lbl = QtWidgets.QLabel("3-D examples (%d) — real Itokawa / skeleton-CT / synthetic" % len(EX.names()))
        lbl.setProperty("muted", True)
        filt = QtWidgets.QLineEdit(); filt.setPlaceholderText("filter by name / task / data…")
        filt.setClearButtonEnabled(True)
        lst = QtWidgets.QListWidget()
        def refill_list(_=None):
            q = filt.text().strip().lower()
            lst.clear()
            for i, task, disp in rows:
                e = meta[i]
                hay = (disp + " " + e["data"] + " " + e["summary"]).lower()
                if q and q not in hay:
                    continue
                it = QtWidgets.QListWidgetItem(disp)
                it.setData(QtCore.Qt.UserRole, i); lst.addItem(it)
            if lst.count(): lst.setCurrentRow(0)
        filt.textChanged.connect(refill_list)
        left.addWidget(lbl); left.addWidget(filt); left.addWidget(lst, 1)

        # -- right: summary + Code/Output tabs + Run/Copy --
        right = QtWidgets.QVBoxLayout()
        summ = QtWidgets.QLabel(); summ.setWordWrap(True); summ.setProperty("muted", True)
        tabs = QtWidgets.QTabWidget()
        code = QtWidgets.QPlainTextEdit(); code.setReadOnly(True)
        code.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
        dlg._code_hl = _python_highlighter_class(QtGui, QtCore)(code.document())
        out = QtWidgets.QPlainTextEdit(); out.setReadOnly(True)
        out.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
        out.setPlaceholderText("press Run to execute this example and see its ground-truth output here")
        tabs.addTab(code, "Code"); tabs.addTab(out, "Output")
        status = QtWidgets.QLabel("ready"); status.setProperty("hint", True)
        b_run = QtWidgets.QPushButton("Run"); b_run.setProperty("accent", True)
        b_copy = QtWidgets.QPushButton("Copy code")
        btnrow = QtWidgets.QHBoxLayout()
        btnrow.addWidget(status, 1); btnrow.addWidget(b_copy); btnrow.addWidget(b_run)
        right.addWidget(summ); right.addWidget(tabs, 1); right.addLayout(btnrow)

        def preview(_=None):
            it = lst.currentItem()
            if it is None: return
            i = it.data(QtCore.Qt.UserRole); e = meta[i]
            _nl = chr(10)
            summ.setText(e["name"] + "  ·  data: " + e["data"] + _nl + e["summary"]
                         + _nl + "実行: py -3.11 examples_3d/" + i + ".py")
            try: code.setPlainText(EX.code(i))
            except Exception: code.setPlainText("")
        lst.currentRowChanged.connect(lambda _=None: preview())

        def copy_code():
            it = lst.currentItem()
            if it is None: return
            i = it.data(QtCore.Qt.UserRole)
            try:
                QtWidgets.QApplication.clipboard().setText(EX.code(i))
                flash("copied 3-D example '%s' to the clipboard" % i)
            except Exception as e:
                report_error("copy", e)
        b_copy.clicked.connect(copy_code)

        b_edit = QtWidgets.QPushButton("Open in editor")
        b_edit.setToolTip("Load this example into the Python Editor as editable, runnable code")
        btnrow.insertWidget(1, b_edit)

        def edit_code():
            it = lst.currentItem()
            if it is None: return
            i = it.data(QtCore.Qt.UserRole)
            try:
                show_python_editor(EX.code(i), i + ".py")
            except Exception as e:
                report_error("editor", e)
        b_edit.clicked.connect(lambda _=False: edit_code())

        b_mdiw = QtWidgets.QPushButton("Open in window")
        b_mdiw.setToolTip("Open this example's code as its own MDI window — open several "
                          "samples side by side and copy fragments between them")
        btnrow.insertWidget(1, b_mdiw)

        def win_code():
            it = lst.currentItem()
            if it is None: return
            i = it.data(QtCore.Qt.UserRole)
            try:
                open_code_window(i + ".py", EX.code(i))
            except Exception as e:
                report_error("code window", e)
        b_mdiw.clicked.connect(lambda _=False: win_code())

        def run_example():
            # Run the selected example in a subprocess (QProcess = non-blocking; the GUI stays
            # responsive) and stream its ground-truth output into the Output tab. Uses the same
            # interpreter that runs Studio, with the repo on PYTHONPATH.
            it = lst.currentItem()
            if it is None or getattr(dlg, "_proc", None) is not None:
                return
            i = it.data(QtCore.Qt.UserRole)
            tabs.setCurrentWidget(out)
            out.setPlainText("$ py examples_3d/%s.py%s%s" % (i, chr(10), chr(10)))
            status.setText("running…")
            proc = QtCore.QProcess(dlg)
            proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            proc.setWorkingDirectory(repo_root)
            env = QtCore.QProcessEnvironment.systemEnvironment()
            env.insert("PYTHONPATH", repo_root + os.pathsep + env.value("PYTHONPATH"))
            env.insert("PYTHONUTF8", "1")
            proc.setProcessEnvironment(env)
            def on_out():
                out.moveCursor(QtGui.QTextCursor.End)
                out.insertPlainText(bytes(proc.readAll()).decode("utf-8", "replace"))
                out.moveCursor(QtGui.QTextCursor.End)
            def on_done(code_, _st=None):
                on_out()
                ok = (code_ == 0)
                status.setText("PASS ✓" if ok else "FAIL (exit %d)" % code_)
                dlg._proc = None
                b_run.setEnabled(True); b_run.setText("Run")
            proc.readyRead.connect(on_out)
            proc.finished.connect(on_done)
            dlg._proc = proc
            b_run.setEnabled(False); b_run.setText("running…")
            proc.start(sys.executable, [EX.path(i)])
        b_run.clicked.connect(run_example)

        h.addLayout(left, 1); h.addLayout(right, 2)
        refill_list()
        if lst.count(): lst.setCurrentRow(0); preview()
        persist_dialog_geometry(dlg, "ex3d"); win._ex3d_dlg = dlg
        win._localize(dlg); dlg.show()

    def show_2d_examples():
        # 2-D geometric-vision gallery: browse the examples2d worked examples (morph / shape
        # descriptors / drawing), read each one's ground-truth-checked code, RUN it in place to
        # see the ground-truth output, or copy it to run standalone (py -3.11 examples/<id>.py).
        # These take operator-provided data (e.g. morph landmarks), so they are runnable code
        # samples, not loaded into the single-image pipeline. Sourced from examples2d (validate()).
        if getattr(win, "_ex2d_dlg", None) is not None:
            win._ex2d_dlg.show(); win._ex2d_dlg.raise_(); win._ex2d_dlg.activateWindow()
            return
        try:
            import examples2d as EX
        except Exception as e:
            report_error("2-D examples", e); return
        repo_root = os.path.dirname(os.path.abspath(EX.__file__))
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("2-D Examples — Fullseye 2D geometric vision")
        tag_dialog(dlg, "reference"); dlg.setModal(False)
        h = QtWidgets.QHBoxLayout(dlg)
        meta = {}; rows = []
        for task, ids in EX.by_task().items():
            for i in ids:
                e = EX.get(i); meta[i] = e
                rows.append((i, task, "[%s] %s" % (task, e["name"])))
        left = QtWidgets.QVBoxLayout()
        lbl = QtWidgets.QLabel("2-D examples (%d) — morph / shape / drawing / signal / spline" % len(EX.names()))
        lbl.setProperty("muted", True)
        filt = QtWidgets.QLineEdit(); filt.setPlaceholderText("filter by name / task / data…")
        filt.setClearButtonEnabled(True)
        lst = QtWidgets.QListWidget()

        def refill_list(_=None):
            q = filt.text().strip().lower(); lst.clear()
            for i, task, disp in rows:
                e = meta[i]; hay = (disp + " " + e["data"] + " " + e["summary"]).lower()
                if q and q not in hay:
                    continue
                it = QtWidgets.QListWidgetItem(disp); it.setData(QtCore.Qt.UserRole, i); lst.addItem(it)
            if lst.count(): lst.setCurrentRow(0)
        filt.textChanged.connect(refill_list)
        left.addWidget(lbl); left.addWidget(filt); left.addWidget(lst, 1)

        right = QtWidgets.QVBoxLayout()
        summ = QtWidgets.QLabel(); summ.setWordWrap(True); summ.setProperty("muted", True)
        tabs = QtWidgets.QTabWidget()
        code = QtWidgets.QPlainTextEdit(); code.setReadOnly(True)
        code.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
        dlg._code_hl = _python_highlighter_class(QtGui, QtCore)(code.document())
        out = QtWidgets.QPlainTextEdit(); out.setReadOnly(True)
        out.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
        out.setPlaceholderText("press Run to execute this example and see its ground-truth output here")
        tabs.addTab(code, "Code"); tabs.addTab(out, "Output")
        status = QtWidgets.QLabel("ready"); status.setProperty("hint", True)
        b_run = QtWidgets.QPushButton("Run"); b_run.setProperty("accent", True)
        b_copy = QtWidgets.QPushButton("Copy code")
        btnrow = QtWidgets.QHBoxLayout()
        btnrow.addWidget(status, 1); btnrow.addWidget(b_copy); btnrow.addWidget(b_run)
        right.addWidget(summ); right.addWidget(tabs, 1); right.addLayout(btnrow)

        def preview(_=None):
            it = lst.currentItem()
            if it is None: return
            i = it.data(QtCore.Qt.UserRole); e = meta[i]; _nl = chr(10)
            summ.setText(e["name"] + "  ·  data: " + e["data"] + _nl + e["summary"]
                         + _nl + "実行: py -3.11 examples/" + i + ".py")
            try: code.setPlainText(EX.code(i))
            except Exception: code.setPlainText("")
        lst.currentRowChanged.connect(lambda _=None: preview())

        def copy_code():
            it = lst.currentItem()
            if it is None: return
            i = it.data(QtCore.Qt.UserRole)
            try:
                QtWidgets.QApplication.clipboard().setText(EX.code(i))
                flash("copied 2-D example '%s' to the clipboard" % i)
            except Exception as e:
                report_error("copy", e)
        b_copy.clicked.connect(copy_code)

        b_edit = QtWidgets.QPushButton("Open in editor")
        b_edit.setToolTip("Load this example into the Python Editor as editable, runnable code")
        btnrow.insertWidget(1, b_edit)

        def edit_code():
            it = lst.currentItem()
            if it is None: return
            i = it.data(QtCore.Qt.UserRole)
            try:
                show_python_editor(EX.code(i), i + ".py")
            except Exception as e:
                report_error("editor", e)
        b_edit.clicked.connect(lambda _=False: edit_code())

        b_mdiw = QtWidgets.QPushButton("Open in window")
        b_mdiw.setToolTip("Open this example's code as its own MDI window — open several "
                          "samples side by side and copy fragments between them")
        btnrow.insertWidget(1, b_mdiw)

        def win_code():
            it = lst.currentItem()
            if it is None: return
            i = it.data(QtCore.Qt.UserRole)
            try:
                open_code_window(i + ".py", EX.code(i))
            except Exception as e:
                report_error("code window", e)
        b_mdiw.clicked.connect(lambda _=False: win_code())

        def run_example():
            it = lst.currentItem()
            if it is None or getattr(dlg, "_proc", None) is not None:
                return
            i = it.data(QtCore.Qt.UserRole)
            tabs.setCurrentWidget(out)
            out.setPlainText("$ py examples/%s.py%s%s" % (i, chr(10), chr(10)))
            status.setText("running…")
            proc = QtCore.QProcess(dlg)
            proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            proc.setWorkingDirectory(repo_root)
            env = QtCore.QProcessEnvironment.systemEnvironment()
            env.insert("PYTHONPATH", repo_root + os.pathsep + env.value("PYTHONPATH"))
            env.insert("PYTHONUTF8", "1")
            proc.setProcessEnvironment(env)
            def on_out():
                out.moveCursor(QtGui.QTextCursor.End)
                out.insertPlainText(bytes(proc.readAll()).decode("utf-8", "replace"))
                out.moveCursor(QtGui.QTextCursor.End)
            def on_done(code_, _st=None):
                on_out(); ok = (code_ == 0)
                status.setText("PASS ✓" if ok else "FAIL (exit %d)" % code_)
                dlg._proc = None; b_run.setEnabled(True); b_run.setText("Run")
            proc.readyRead.connect(on_out); proc.finished.connect(on_done)
            dlg._proc = proc; b_run.setEnabled(False); b_run.setText("running…")
            proc.start(sys.executable, [EX.path(i)])
        b_run.clicked.connect(run_example)

        h.addLayout(left, 1); h.addLayout(right, 2)
        refill_list()
        if lst.count(): lst.setCurrentRow(0); preview()
        persist_dialog_geometry(dlg, "ex2d"); win._ex2d_dlg = dlg
        win._localize(dlg); dlg.show()

    def show_python_editor(code_text=None, name_hint=None):
        # Qt Creator / HDevelop-style Python workbench: a MULTI-DOCUMENT (tabbed) editor
        # + run console, so a worked example (or any fullseye script) can be opened,
        # modified and executed as-is — and, like HDevelop's main + sub-scripts, several
        # scripts stay open and editable at once (user spec 2026-08-30). Scripts run in
        # a subprocess (QProcess = non-blocking, GUI stays responsive) with the repo on
        # PYTHONPATH, exactly like the example galleries' Run buttons.
        if getattr(win, "_pyedit_dlg", None) is not None:
            d = win._pyedit_dlg
            d.show(); d.raise_(); d.activateWindow()
            if code_text is not None:
                win._pyedit["open_tab"](code_text, name_hint)
            return
        repo_root = os.path.dirname(os.path.abspath(__file__))
        dlg = QtWidgets.QDialog(win); tag_dialog(dlg, "reference"); dlg.setModal(False)
        v = QtWidgets.QVBoxLayout(dlg)
        CodeEditor = _code_editor_class(QtWidgets, QtGui, QtCore)
        Highlighter = _python_highlighter_class(QtGui, QtCore)
        tabs_ed = QtWidgets.QTabWidget()
        tabs_ed.setTabsClosable(True); tabs_ed.setMovable(True)
        tabs_ed.setDocumentMode(True)
        out = QtWidgets.QPlainTextEdit(); out.setReadOnly(True)
        out.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
        out.setPlaceholderText("Run (F5) executes the CURRENT tab with the repo on PYTHONPATH; "
                               "output streams here")
        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        split.addWidget(tabs_ed); split.addWidget(out)
        split.setStretchFactor(0, 3); split.setStretchFactor(1, 1)
        status = QtWidgets.QLabel("ready"); status.setProperty("hint", True)
        b_new = QtWidgets.QPushButton("New")
        b_open = QtWidgets.QPushButton("Open…")
        b_save = QtWidgets.QPushButton("Save")
        b_saveas = QtWidgets.QPushButton("Save as…")
        b_samples = QtWidgets.QToolButton(); b_samples.setText("Samples ▾")
        b_samples.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        b_stop = QtWidgets.QPushButton("Stop"); b_stop.setEnabled(False)
        b_run = QtWidgets.QPushButton("Run (F5)"); b_run.setProperty("accent", True)
        btnrow = QtWidgets.QHBoxLayout()
        for w in (b_new, b_open, b_save, b_saveas, b_samples):
            btnrow.addWidget(w)
        btnrow.addWidget(status, 1); btnrow.addWidget(b_stop); btnrow.addWidget(b_run)
        v.addLayout(btnrow); v.addWidget(split, 1)
        dlg._proc = None

        def cur_editor():
            return tabs_ed.currentWidget()             # a CodeEditor page, or None

        def _tab_title(ed):
            name = os.path.basename(ed._path) if ed._path else (ed._hint or "untitled.py")
            return name + (" *" if ed._dirty else "")

        def _sync_tab(ed):
            i = tabs_ed.indexOf(ed)
            if i >= 0:
                tabs_ed.setTabText(i, _tab_title(ed))
            if ed is tabs_ed.currentWidget():
                dlg.setWindowTitle("Python Editor — %s" % _tab_title(ed))

        def open_tab(text, hint=None, path=None):
            # every document is its own tab (HDevelop main + sub-scripts); nothing is
            # ever replaced, so no discard-confirm is needed
            ed = CodeEditor()
            ed._hl = Highlighter(ed.document())
            ed._path = path; ed._hint = hint; ed._dirty = False
            ed.setPlainText(text)
            ed.textChanged.connect(lambda ed=ed: _mark_dirty(ed))
            tabs_ed.setCurrentIndex(tabs_ed.addTab(ed, _tab_title(ed)))
            _sync_tab(ed)
            return ed

        def _mark_dirty(ed):
            if not ed._dirty:
                ed._dirty = True; _sync_tab(ed)

        def close_tab(i):
            ed = tabs_ed.widget(i)
            if ed is None:
                return
            if ed._dirty and ed.toPlainText().strip():
                r = QtWidgets.QMessageBox.question(
                    dlg, "Discard changes?",
                    "'%s' has unsaved changes — close anyway?" % _tab_title(ed),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if r != QtWidgets.QMessageBox.Yes:
                    return
            tabs_ed.removeTab(i); ed.deleteLater()
        tabs_ed.tabCloseRequested.connect(close_tab)
        tabs_ed.currentChanged.connect(
            lambda _i: (cur_editor() is not None) and _sync_tab(cur_editor()))

        def new_file():
            open_tab("# Fullseye scratch — the repo is on PYTHONPATH (import fullseye works).\n"
                     "import numpy as np\n"
                     "import fullseye\n"
                     "\n"
                     "img = np.zeros((64, 64), dtype=np.uint8)\n"
                     "img[16:48, 16:48] = 200\n"
                     "out = fullseye.apply(img, 'gaussian', 1.2, 0.0)\n"
                     "print('mean after gaussian:', float(out.mean()))\n",
                     "untitled.py")

        def save_to(path):
            ed = cur_editor()
            if ed is None:
                return False
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(ed.toPlainText())
            except Exception as e:
                report_error("save", e); return False
            ed._path = path; ed._dirty = False; _sync_tab(ed)
            flash("saved " + os.path.basename(path))
            return True

        def do_save_as():
            ed = cur_editor()
            if ed is None:
                return
            p, _f = QtWidgets.QFileDialog.getSaveFileName(
                dlg, "Save Python file",
                os.path.join(repo_root, ed._hint or "untitled.py"), "Python (*.py)")
            if p:
                save_to(p)

        def do_save():
            ed = cur_editor()
            if ed is None:
                return
            if ed._path:
                save_to(ed._path)
            else:
                do_save_as()

        def open_path(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                report_error("open", e); return
            open_tab(text, os.path.basename(path), path=path)

        def do_open():
            p, _f = QtWidgets.QFileDialog.getOpenFileName(
                dlg, "Open Python file", repo_root, "Python (*.py)")
            if p:
                open_path(p)

        # -- Samples menu: every 2-D / 3-D worked example, grouped by task. Each opens
        #    as a NEW TAB without a path, so Save routes to Save-as (a shipped,
        #    validate()-checked example can never be overwritten by accident). --
        smenu = QtWidgets.QMenu(dlg)
        for label, modname in (("2-D examples", "examples2d"), ("3-D examples", "examples3d")):
            try:
                EXm = __import__(modname)
            except Exception:
                continue
            sub = smenu.addMenu(label)
            for task, ids in EXm.by_task().items():
                tsub = sub.addMenu(task)
                for i in ids:
                    tsub.addAction("%s — %s" % (i, EXm.get(i)["name"]),
                                   (lambda i=i, EXm=EXm:
                                    open_tab(EXm.code(i), i + ".py")))
        b_samples.setMenu(smenu)

        def run_code():
            ed = cur_editor()
            if dlg._proc is not None or ed is None:
                return
            text = ed.toPlainText()
            if not text.strip():
                flash("nothing to run — the editor is empty"); return
            script = ed._path
            scratch = None                    # set when running from a temp copy
            if script is None or ed._dirty:
                # unsaved buffers run from a scratch copy — Run never forces a Save
                import tempfile
                d = os.path.join(tempfile.gettempdir(), "fullseye_studio")
                try:
                    os.makedirs(d, exist_ok=True)
                    script = scratch = os.path.join(d, "scratch_%d.py" % os.getpid())
                    with open(script, "w", encoding="utf-8") as f:
                        f.write(text)
                except Exception as e:
                    report_error("run", e); return
            out.setPlainText("$ py %s\n\n" % os.path.basename(script))
            status.setText("running…")
            proc = QtCore.QProcess(dlg)
            proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            proc.setWorkingDirectory(repo_root)
            env = QtCore.QProcessEnvironment.systemEnvironment()
            env.insert("PYTHONPATH", repo_root + os.pathsep + env.value("PYTHONPATH"))
            env.insert("PYTHONUTF8", "1")
            # UI 言語をライブラリ層(fsi18n)へ伝播 — スクリプトが出す fsi18n.msg()
            # 経由のメッセージが Studio の言語設定に追従する(docs/I18N.md)
            env.insert("FULLSEYE_LANG", getattr(win, "_lang", "en"))
            proc.setProcessEnvironment(env)
            def on_out():
                out.moveCursor(QtGui.QTextCursor.End)
                out.insertPlainText(bytes(proc.readAll()).decode("utf-8", "replace"))
                out.moveCursor(QtGui.QTextCursor.End)
            def on_done(code_, st=None):
                on_out()
                if st == QtCore.QProcess.CrashExit:
                    status.setText("stopped")
                elif code_ == 0:
                    status.setText("PASS ✓ (exit 0)")
                else:
                    status.setText("FAIL (exit %d)" % code_)
                dlg._proc = None
                b_run.setEnabled(True); b_stop.setEnabled(False)
                if scratch is not None:       # 実行済みスクラッチは残さない(コード残留防止)
                    try:
                        os.remove(scratch)
                    except OSError:
                        pass
            proc.readyRead.connect(on_out); proc.finished.connect(on_done)
            # System settings can point Run at another interpreter (venv etc.);
            # a broken path is refused up-front (fail-closed) instead of a cryptic
            # QProcess failure.
            interp = str(QtCore.QSettings("Fullseye", "Studio")
                         .value("pyedit/interpreter", "") or "").strip()
            if interp and not os.path.isfile(interp):
                report_error("run", "configured interpreter not found: %s" % interp)
                dlg._proc = None; b_run.setEnabled(True); b_stop.setEnabled(False)
                return
            dlg._proc = proc; b_run.setEnabled(False); b_stop.setEnabled(True)
            proc.start(interp or sys.executable, [script])

        def stop_code():
            if dlg._proc is not None:
                dlg._proc.kill()

        b_new.clicked.connect(lambda _=False: new_file())
        b_open.clicked.connect(lambda _=False: do_open())
        b_save.clicked.connect(lambda _=False: do_save())
        b_saveas.clicked.connect(lambda _=False: do_save_as())
        b_run.clicked.connect(lambda _=False: run_code())
        b_stop.clicked.connect(lambda _=False: stop_code())
        QtGui.QShortcut(QtGui.QKeySequence("F5"), dlg, run_code)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), dlg, do_save)

        win._pyedit = {"dlg": dlg, "tabs": tabs_ed, "editor": cur_editor, "output": out,
                       "status": status, "run": run_code, "stop": stop_code,
                       "open_tab": open_tab, "close_tab": close_tab, "save_to": save_to,
                       "open_path": open_path, "new": new_file}
        if code_text is not None:
            open_tab(code_text, name_hint)
        else:
            new_file()
        persist_dialog_geometry(dlg, "pyedit", default_size=(920, 660))
        win._pyedit_dlg = dlg
        win._localize(dlg)                     # register + translate this lazy dialog
        dlg.show()

    def open_code_window(title, text):
        # A read-only, syntax-highlighted CODE window inside the MDI area — the sample-
        # browsing counterpart of a graphics window (user spec 2026-08-30: comparing
        # several samples and copying fragments between them is everyday work in an
        # MDI IDE). Non-singleton: open as many as needed; Window-menu tile/cascade
        # applies; select any fragment and Ctrl+C copies it.
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w); v.setContentsMargins(4, 4, 4, 4); v.setSpacing(4)
        ed = QtWidgets.QPlainTextEdit(); ed.setReadOnly(True)
        ed.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        f = QtGui.QFont("Consolas"); f.setStyleHint(QtGui.QFont.Monospace); f.setPointSize(10)
        ed.setFont(f)
        ed.setPlainText(text)
        w._hl = _python_highlighter_class(QtGui, QtCore)(ed.document())
        hint = QtWidgets.QLabel("select any fragment — Ctrl+C copies it")
        hint.setProperty("hint", True)
        b_copy = QtWidgets.QPushButton("Copy all")
        b_edit = QtWidgets.QPushButton("Open in editor")
        row = QtWidgets.QHBoxLayout()
        row.addWidget(hint, 1); row.addWidget(b_copy); row.addWidget(b_edit)
        v.addWidget(ed, 1); v.addLayout(row)

        def _copy_all(_=False):
            QtWidgets.QApplication.clipboard().setText(ed.toPlainText())
            flash("copied '%s' to the clipboard" % title)
        b_copy.clicked.connect(_copy_all)
        b_edit.clicked.connect(lambda _=False: show_python_editor(ed.toPlainText(), title))
        sub = mdi.addSubWindow(w)
        sub.setWindowTitle(title)
        sub.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        sub.resize(520, 480)
        win._code_windows = [s for s in getattr(win, "_code_windows", [])
                             if s in mdi.subWindowList()]
        win._code_windows.append(sub)
        win._localize(sub)
        sub.show()
        return sub

    def add_op_by_name(n):
        row = _op_row(n)
        if row and row.get("backend") == "general":     # palette: general ops are run-via-CLI only
            flash("‘%s’ is a general-algorithm op (seq/scalar) — run it via CLI: "
                  "imgevolve.py algo run %s" % (n, n))
            return
        push_undo()
        model.add_stage(n)
        mark_dirty()
        refresh_stage_list(select=len(model.stages) - 1)
        show_result()

    def show_palette():
        # actions first, then samples, recent files, then every operator — run by name,
        # keyboard-only. Disabled (context-unavailable) actions are skipped so the palette
        # never offers a command that would silently no-op.
        items = [("▸ " + a.text().replace("…", "").strip(), a.trigger)
                 for a in win._actions.values() if a is not act_palette and a.isEnabled()]
        items += [("sample: " + nm, (lambda idx=i + 1: load_sample(idx)))
                  for i, nm in enumerate(recipes.names())]
        items += [("recent: " + os.path.basename(p), (lambda p=p: _open_recent(p)))
                  for p in _recent_paths()]
        items += [("op: " + r["name"], (lambda n=r["name"]: add_op_by_name(n))) for r in all_ops]
        labels = [lbl for lbl, _ in items]
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Command palette")
        tag_dialog(dlg, "editor")
        v = QtWidgets.QVBoxLayout(dlg)
        ed = QtWidgets.QLineEdit(); ed.setPlaceholderText("type an action or operator…  (Enter to run)")
        lst = QtWidgets.QListWidget()
        v.addWidget(ed); v.addWidget(lst)

        def refill(_=None):
            lst.clear()
            for i in palette_filter(labels, ed.text())[:200]:
                it = QtWidgets.QListWidgetItem(labels[i])
                it.setData(QtCore.Qt.UserRole, i)
                lst.addItem(it)
            if lst.count():
                lst.setCurrentRow(0)

        # A double-click on a QListWidget emits BOTH doubleClicked and activated, so
        # wiring run_sel() to both ran the chosen command twice (two stages inserted
        # per click). Keep a single activation path and latch it against re-entry.
        pal = {"ran": False}

        def run_sel():
            if pal["ran"]:
                return
            it = lst.currentItem() or (lst.item(0) if lst.count() else None)
            if it is not None:
                pal["ran"] = True
                idx = it.data(QtCore.Qt.UserRole)
                dlg.accept()
                items[idx][1]()

        ed.textChanged.connect(refill)
        ed.returnPressed.connect(run_sel)
        lst.itemActivated.connect(lambda _=None: run_sel())   # covers Enter AND double-click
        refill(); dlg.resize(560, 440); ed.setFocus()
        win._palette = {"filter": palette_filter, "labels": labels, "run": run_sel,
                        "edit": ed, "list": lst, "state": pal}
        dlg.exec()

    # operator browser filters
    search.textChanged.connect(refill_ops); cat.currentIndexChanged.connect(refill_ops)

    # HDevelop-style autocomplete: typing shows op-name candidates in a popup; picking
    # one clears the category filter, filters the list to it, and selects it.
    op_completer = QtWidgets.QCompleter([r["name"] for r in all_ops], win)
    op_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
    op_completer.setFilterMode(QtCore.Qt.MatchContains)
    op_completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
    search.setCompleter(op_completer)

    def _select_op_in_list(name):
        for i in range(op_list.count()):
            if op_list.item(i).data(QtCore.Qt.UserRole) == name:
                op_list.setCurrentRow(i); op_list.scrollToItem(op_list.item(i)); return True
        return False

    def on_op_completed(name):
        cat.setCurrentIndex(0)          # "all categories" so the picked op is visible
        search.setText(name)            # fires refill_ops synchronously
        _select_op_in_list(name)
    op_completer.activated[str].connect(on_op_completed)
    win._op_completer = op_completer
    win._select_op_in_list = _select_op_in_list
    # pipeline + knobs
    def _knob_label(letter, role, curated):
        """The a/b label text for the selected op: its role's short name when known,
        "(–)" when the op curates the knob as genuinely unused, else the bare letter
        (an un-curated op may still use the knob, so we never claim it is unused)."""
        if role:                                  # a curated, non-empty role
            short = role
            for sep in ("—", "=", "("):
                short = short.split(sep)[0]
            short = short.strip()[:16]
            return "%s · %s" % (letter, short) if short else letter
        if curated and role == "":                # curated AND explicitly empty = unused
            return "%s (–)" % letter
        return letter                             # un-curated op: keep it generic

    def on_op_selected(cur, _prev=None):
        if cur is None:
            op_param.setText("select an operator to see its signature")
            lbl_a.setText("a"); lbl_b.setText("b")
            op_a_spin.setEnabled(True); op_b_spin.setEnabled(True)
            b_insert.setEnabled(False); b_help.setEnabled(False); b_run_once.setEnabled(False); return
        name = cur.data(QtCore.Qt.UserRole)
        row = _op_row(name)
        op_param.setText(op_signature_detail(row) if row else cur.text())
        if row and row.get("backend") == "general":
            # general-algorithm tier: read-only in the image UI (different seq/scalar
            # model). No a/b knobs, and Insert / Run once / Help are image-pipeline
            # actions that don't apply — run it via the CLI instead.
            lbl_a.setText("a"); lbl_b.setText("b")
            op_a_spin.setEnabled(False); op_b_spin.setEnabled(False)
            b_insert.setEnabled(False); b_help.setEnabled(False); b_run_once.setEnabled(False)
            return
        curated = name in _ARG_ROLES
        a_role, b_role = op_arg_roles(name)
        lbl_a.setText(_knob_label("a", a_role, curated))
        lbl_b.setText(_knob_label("b", b_role, curated))
        # only disable a knob we KNOW is unused (curated ""); never for un-curated ops
        op_a_spin.setEnabled(not (curated and a_role == ""))
        op_b_spin.setEnabled(not (curated and b_role == ""))
        lbl_a.setToolTip(a_role or ("(unused by %s)" % name if curated else "argument a"))
        lbl_b.setToolTip(b_role or ("(unused by %s)" % name if curated else "argument b"))
        b_insert.setEnabled(True); b_help.setEnabled(True); b_run_once.setEnabled(True)
    op_list.currentItemChanged.connect(on_op_selected)
    win._op_arg_labels = (lbl_a, lbl_b)
    b_insert.clicked.connect(
        lambda: add_op(op_list.currentItem()) if op_list.currentItem() is not None else None)
    b_run_once.clicked.connect(run_op_once)
    # itemActivated fires on BOTH Enter and double-click (one signal), so keyboard-only
    # pipeline building works and there is no double-insert from wiring two signals.
    op_list.itemActivated.connect(add_op)

    def _insert_searched_op():
        """Enter in the search box inserts the highlighted (or first) filtered op."""
        it = op_list.currentItem() or (op_list.item(0) if op_list.count() else None)
        if it is not None:
            add_op(it)
    search.returnPressed.connect(_insert_searched_op)

    def jump_to_problem(item):
        idx = item.data(QtCore.Qt.UserRole)
        if idx is not None and 0 <= idx < len(model.stages):
            stage_list.setCurrentRow(idx)
    # single-click as well as double-click / Enter navigates to the failing stage.
    problems_list.itemClicked.connect(jump_to_problem)
    problems_list.itemActivated.connect(jump_to_problem)
    samples.currentIndexChanged.connect(load_sample)
    stage_list.currentRowChanged.connect(lambda _=None: on_stage_selected())
    sa.valueChanged.connect(on_knob); sb.valueChanged.connect(on_knob)
    spin_a.valueChanged.connect(on_spin); spin_b.valueChanged.connect(on_spin)
    display.currentIndexChanged.connect(lambda _=None: show_result())
    # buttons
    b_rm.clicked.connect(remove); b_up.clicked.connect(lambda: move(-1)); b_dn.clicked.connect(lambda: move(1))
    b_load.clicked.connect(load_image); b_demo.clicked.connect(use_demo); b_save.clicked.connect(save_result)
    b_export.clicked.connect(export)
    b_zin.clicked.connect(lambda: view.zoom(1.25)); b_zout.clicked.connect(lambda: view.zoom(0.8))
    b_fit.clicked.connect(view.fit); b_11.clicked.connect(view.reset_zoom)
    b_reset.clicked.connect(reset_to_raw)
    b_step.clicked.connect(lambda: step_to(min(selected_index() + 1, len(model.stages) - 1)))
    b_runall.clicked.connect(lambda: step_to(len(model.stages) - 1))
    stage_list.model().rowsMoved.connect(on_rows_moved)     # drag-reorder -> permute model
    # menu / toolbar actions (share the same handlers as the buttons)
    act_open_img.triggered.connect(load_image); act_demo.triggered.connect(use_demo)
    act_save_res.triggered.connect(save_result); act_export.triggered.connect(export)
    act_copy_res.triggered.connect(copy_result)
    act_quit.triggered.connect(win.close)
    act_remove.triggered.connect(remove)
    act_up.triggered.connect(lambda: move(-1)); act_down.triggered.connect(lambda: move(1))
    act_clear.triggered.connect(clear_pipe)
    act_dup.triggered.connect(duplicate_stage_ui)
    act_top.triggered.connect(lambda: move_to_end(True))
    act_bottom.triggered.connect(lambda: move_to_end(False))
    act_focus_search.triggered.connect(lambda: (search.setFocus(), search.selectAll()))
    act_undo.triggered.connect(undo); act_redo.triggered.connect(redo)
    act_zin.triggered.connect(lambda: view.zoom(1.25)); act_zout.triggered.connect(lambda: view.zoom(0.8))
    act_fit.triggered.connect(view.fit); act_11.triggered.connect(view.reset_zoom)
    act_reset.triggered.connect(reset_to_raw)
    act_step.triggered.connect(lambda: step_to(min(selected_index() + 1, len(model.stages) - 1)))
    act_runall.triggered.connect(lambda: step_to(len(model.stages) - 1))

    # Debugger-style function keys that fire ANYWHERE in the window. The Ctrl+Arrow
    # step/run keys above are deliberately scoped to the pipeline list so they do
    # not fire while you type in the operator search box; function keys never clash
    # with typing, so these are WindowShortcut — press F6 to step from any panel,
    # F5 to run all, Shift+F5 to reset, exactly like a debugger.
    def _do_step():
        step_to(min(selected_index() + 1, len(model.stages) - 1))

    def _do_run_all():
        step_to(len(model.stages) - 1)

    act_dbg_run = _act("Run all (F5)", "F5", "Run the whole pipeline to the final result (debugger Run)")
    act_dbg_step = _act("Step (F6)", "F6", "Advance one pipeline stage (debugger Step) — works from any panel")
    act_dbg_reset = _act("Reset to start (Shift+F5)", "Shift+F5", "Show the raw image — restart the step-through")
    win._menus["run"].addSeparator()
    for _a, _fn in ((act_dbg_run, _do_run_all), (act_dbg_step, _do_step), (act_dbg_reset, reset_to_raw)):
        _a.setShortcutContext(QtCore.Qt.WindowShortcut)   # fires app-wide, not only on the pipeline list
        _a.triggered.connect(_fn)
        win.addAction(_a)                                 # keep the shortcut active even without a menu
        win._menus["run"].addAction(_a)                   # discoverable in the Run menu
    # (registered into win._actions below, once that dict exists)
    # -- program / code editor wiring (parse <-> pipeline, timed run, step) ---- #
    import time as _time

    def program_text_from_model():
        if not model.stages:
            return ("* empty pipeline — type ops here (HDevelop syntax), e.g.:\n"
                    "* gaussian (0.4, 0.5)\n* sobel_mag (0.5, 0.5)\n* otsu (0.5, 0.5)\n"
                    "* control flow:  for 3 ... endfor   ·   if 1 ... else ... endif")
        return "\n".join("%s (%.3f, %.3f)" % (n, a, b) for (n, a, b) in model.stages)

    def sync_program():
        # Never clobber what the user is typing OR unapplied edits (Codex #9): the
        # editor keeps the user's code until they Apply it or Reset — a pipeline
        # change no longer silently overwrites hand-written, not-yet-applied code.
        if code_edit.hasFocus() or state.get("code_dirty"):
            return
        code_edit.blockSignals(True)
        # 適用済みの dev_* / set_system 行は残す(モデル再生成で消さない)。HDevelop の
        # プログラム同様、表示ディレクティブはプログラムの一部。位置は先頭へ正規化される
        # (honest limit: op 行間の元位置までは復元しない — ディレクティブは適用順不問)。
        # Keep applied dev_*/set_system lines across model-driven rewrites; they are
        # normalised to the top (their exact interleaving is not round-tripped).
        dev_lines = state.get("dev_lines") or []
        body = program_text_from_model()
        code_edit.setPlainText("\n".join(dev_lines) + "\n" + body if dev_lines else body)
        code_edit.blockSignals(False)
        code_edit.clear_exec()
        state["code_dirty"] = False

    def _on_code_changed():
        # A real user edit (sync_program blocks signals around its own setPlainText,
        # so this only fires for typing) → mark the Program as having unapplied edits.
        state["code_dirty"] = True
        code_status.setText("● unapplied edits — Apply to run, or Reset to discard")
    code_edit.textChanged.connect(_on_code_changed)

    def parse_program(text):
        # HDevelop-style syntax: op (a, b) / op a b, * and # comments, for/endfor and
        # if/else/endif control flow (expanded into the flat pipeline).
        return parse_hdev_program(text, op_names)

    def apply_program():
        text = code_edit.toPlainText()        # capture first: refresh_stage_list rewrites the editor
        stages, errs = parse_program(text)
        if errs:
            code_status.setText("✕ " + "  ·  ".join(errs[:3]))
            flash("code has %d error(s)" % len(errs))
            return
        # defense-in-depth: even though op_names excludes the general tier (so the parser
        # already rejects such a token), never let a general-algorithm op reach the image
        # pipeline via this path, which writes model.stages directly (no add_stage backstop).
        general = [s[0] for s in stages if (_op_row(s[0]) or {}).get("backend") == "general"]
        if general:
            code_status.setText("✕ general-algorithm op(s) can't run in an image pipeline: "
                                + ", ".join(general[:3]))
            flash("‘%s’ is a general-algorithm op (seq/scalar) — run it via CLI: "
                  "imgevolve.py algo run %s" % (general[0], general[0]))
            return
        push_undo()
        model.stages = list(stages)
        mark_dirty()
        state["code_dirty"] = False           # the edits are now applied to the pipeline
        # dev_* / set_system 行を退避 — sync_program の再生成後もエディタに残す
        # (以前は Apply でディレクティブ行が消え、再 Apply の意味が変わっていた)
        state["dev_lines"] = [ln.rstrip() for ln in text.splitlines()
                              if ln.strip().startswith(("dev_", "set_system", "disp_"))]
        code_edit.clear_exec()                # 旧実行位置は新パイプラインと不整合 — Continue の誤表示防止
        code_status.setText("applied %d stage(s)" % len(stages))
        refresh_stage_list(select=(len(stages) - 1) if stages else None)
        apply_dev_directives(text, reclaim_stale=True)   # state/style directives — pre-render; stale program windows reclaimed
        show_result()
        apply_text_directives(text)           # dev_disp_text annotations — drawn on top of the render

    def run_program(stop_at_breakpoints=True):
        try:
            v = model.result_upto(-1)     # the raw base image
        except Exception as e:
            code_status.setText("cannot run: %s" % e); return
        timings, last, hit_bp = {}, -1, False
        for i, (name, a, b) in enumerate(model.stages):
            fn = api.RT.get(name)
            if fn is None:
                break
            t0 = _time.perf_counter()
            try:
                v = fn(v, a, b)
            except Exception:
                pass
            timings[i + 1] = (_time.perf_counter() - t0) * 1000.0
            last = i
            if stop_at_breakpoints and (i + 1) in code_edit.breakpoints:
                hit_bp = True
                break
        if state["dev_update"]["time"]:
            code_edit.set_timings(timings)     # dev_update_time
        if state["dev_update"]["pc"]:
            code_edit.set_exec_line(last + 1)  # dev_update_pc: execution cursor
        if 0 <= last < len(model.stages):
            stage_list.setCurrentRow(last)     # show the result up to the reached line
        tmo = state["system"]["operator_timeout_ms"]
        slow = [ln for ln, ms in timings.items() if tmo and ms > tmo]   # soft set_operator_timeout
        code_status.setText("ran %d line(s) in %.1f ms%s%s"
                            % (len(timings), sum(timings.values()),
                               "  · stopped at breakpoint" if hit_bp else "",
                               ("  · %d stage(s) over %d ms timeout" % (len(slow), tmo)) if slow else ""))

    def step_program():
        cur = code_edit._exec_line
        nxt = (cur + 1) if cur >= 1 else 1
        if not model.stages:
            code_status.setText("no stages to step"); return
        nxt = max(1, min(nxt, len(model.stages)))
        try:
            v = model.result_upto(-1)
            tmap = dict(code_edit.timings)
            for i in range(nxt):
                name, a, b = model.stages[i]
                fn = api.RT.get(name)
                t0 = _time.perf_counter()
                v = fn(v, a, b) if fn else v
                if i == nxt - 1:
                    tmap[nxt] = (_time.perf_counter() - t0) * 1000.0
            if state["dev_update"]["time"]:
                code_edit.set_timings(tmap)
        except Exception:
            pass
        if state["dev_update"]["pc"]:
            code_edit.set_exec_line(nxt)       # dev_update_pc
        stage_list.setCurrentRow(nxt - 1)
        code_status.setText("stepped to line %d" % nxt)

    def continue_program():
        # HDevelop F5 semantics (user spec 2026-08-30: pause / resume / restart-from-line
        # freedom): resume from the CURRENT execution line — not line 1 — to the next
        # breakpoint or the end. A gutter breakpoint is the "pause"; this is the "resume";
        # run_from() below is the "restart from an arbitrary line".
        if not model.stages:
            code_status.setText("no stages to run"); return
        start = max(code_edit._exec_line, 0)            # 1-based last-executed line (0 = none)
        try:
            v = model.result_upto(start - 1)            # recompute state up to that line
        except Exception as e:
            code_status.setText("cannot continue: %s" % e); return
        timings = dict(code_edit.timings); last = start - 1; hit_bp = False
        for i in range(start, len(model.stages)):
            name, a, b = model.stages[i]
            fn = api.RT.get(name)
            if fn is None:
                break
            t0 = _time.perf_counter()
            try:
                v = fn(v, a, b)
            except Exception:
                pass
            timings[i + 1] = (_time.perf_counter() - t0) * 1000.0
            last = i
            if (i + 1) in code_edit.breakpoints:
                hit_bp = True
                break
        if state["dev_update"]["time"]:
            code_edit.set_timings(timings)
        if state["dev_update"]["pc"]:
            code_edit.set_exec_line(last + 1)
        if 0 <= last < len(model.stages):
            stage_list.setCurrentRow(last)
        code_status.setText("continued line %d → %d%s"
                            % (start + 1, last + 1,
                               "  · stopped at breakpoint" if hit_bp else ""))

    def run_from(line):
        # restart execution AT `line` (1-based): position the cursor before it, continue
        code_edit.set_exec_line(max(0, int(line) - 1))
        continue_program()

    c_apply.clicked.connect(apply_program)
    c_sync.clicked.connect(sync_program)
    c_run.clicked.connect(lambda: run_program(True))
    c_cont.clicked.connect(lambda: continue_program())
    c_step.clicked.connect(step_program)
    def reset_program():
        state["code_dirty"] = False           # discard unapplied edits, restore code from the pipeline
        sync_program()
        code_edit.clear_exec()
        code_status.setText("ready")
    c_reset.clicked.connect(reset_program)
    win._program = {"edit": code_edit, "apply": apply_program, "run": run_program,
                    "step": step_program, "continue": continue_program, "run_from": run_from,
                    "parse": parse_program, "text": program_text_from_model}

    # -- variables & objects window wiring (inspect / display any stage output) - #
    def _var_entries():
        ents = [("input", -1, "image")]
        try:
            states = model.step_states()
        except Exception:
            states = []
        for i, (name, a, b) in enumerate(model.stages):
            kind = states[i]["state"].get("kind", "?") if i < len(states) else "?"
            ents.append(("%d: %s" % (i + 1, name), i, kind))
        return ents

    def show_variable_inspection():
        it = var_list.currentItem()
        if it is None:
            var_inspect.setPlainText(""); refresh_watches(); return
        try:
            val = model.result_upto(it.data(QtCore.Qt.UserRole))
            var_inspect.setPlainText(format_inspection(inspect_result(val)))
        except Exception as e:
            var_inspect.setPlainText("inspect error: %s" % e)
        refresh_watches()

    # -- watch-expression evaluation (widgets built next to var_inspect above) -- #
    _WATCH_BUILTINS = {"abs": abs, "len": len, "min": min, "max": max, "sum": sum,
                       "round": round, "float": float, "int": int, "bool": bool}

    def _save_watches():
        exprs = [watch_table.item(r, 0).text() for r in range(watch_table.rowCount())]
        QtCore.QSettings("Fullseye", "Studio").setValue("watch/expressions", exprs)

    def refresh_watches():
        # every watch row is evaluated against the SELECTED variable; a failing
        # expression shows its error in place (never crashes the panel).
        it = var_list.currentItem()
        val = None
        if it is not None:
            try:
                val = model.result_upto(it.data(QtCore.Qt.UserRole))
            except Exception:
                val = None
        env = {"v": val, "np": np, "img": model.image}
        for r in range(watch_table.rowCount()):
            expr = watch_table.item(r, 0).text()
            try:
                # a local debugger-style watch window: the expressions are the user's
                # own, evaluated in-process on purpose (same trust level as the CLI)
                res = eval(expr, {"__builtins__": _WATCH_BUILTINS}, env)
                if isinstance(res, np.ndarray):
                    txt = ("%s %s mean=%.5g" % ("×".join(str(s) for s in res.shape),
                                                res.dtype, float(np.nanmean(res)))
                           if res.size else "empty array")
                else:
                    txt = repr(res)
            except Exception as e:
                txt = "⚠ %s" % e
            cell = QtWidgets.QTableWidgetItem(str(txt)[:200])
            cell.setToolTip(str(txt))
            watch_table.setItem(r, 1, cell)

    def add_watch(expr=None, persist=True):
        expr = (expr if isinstance(expr, str) else watch_input.text()).strip()
        if not expr:
            return
        r = watch_table.rowCount(); watch_table.insertRow(r)
        watch_table.setItem(r, 0, QtWidgets.QTableWidgetItem(expr))
        watch_input.clear()
        if persist:
            _save_watches()
        refresh_watches()

    def del_watch():
        r = watch_table.currentRow()
        if r >= 0:
            watch_table.removeRow(r); _save_watches(); refresh_watches()

    w_add.clicked.connect(lambda _=False: add_watch())
    watch_input.returnPressed.connect(add_watch)
    w_del.clicked.connect(lambda _=False: del_watch())
    _saved_watches = QtCore.QSettings("Fullseye", "Studio").value("watch/expressions") or []
    if isinstance(_saved_watches, str):           # QSettings round-trips a 1-list as str
        _saved_watches = [_saved_watches]
    for _e in _saved_watches:
        add_watch(str(_e), persist=False)
    win._watch = {"table": watch_table, "input": watch_input, "add": add_watch,
                  "remove": del_watch, "refresh": refresh_watches}

    _VAR_THUMB = 44

    def _contour_icon(xld):
        """Thumbnail for an XLD contour set ``{"shape": (H,W), "cs": [Nx2 (row,col)]}``:
        the polylines scaled into the ``_VAR_THUMB`` box, so a contour variable reads
        as iconic (its geometry is visible) as HDevelop's Variable window shows XLD —
        rather than an opaque 'control' with no preview."""
        cs = xld.get("cs") or []
        shp = xld.get("shape") or (1, 1)
        H, W = max(int(shp[0]), 1), max(int(shp[1]), 1)
        pm = QtGui.QPixmap(_VAR_THUMB, _VAR_THUMB)
        pm.fill(QtGui.QColor(NAVY_1))                 # match the panel background
        if cs:
            p = QtGui.QPainter(pm)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            pen = QtGui.QPen(QtGui.QColor(TEAL)); pen.setWidthF(1.2); p.setPen(pen)
            s = (_VAR_THUMB - 2) / max(H, W)          # uniform scale, keep aspect, 1px margin
            ox, oy = (_VAR_THUMB - s * W) / 2.0, (_VAR_THUMB - s * H) / 2.0
            for c in cs:
                try:
                    pts = np.asarray(c, float)
                except Exception:
                    continue                      # a ragged/malformed contour entry is skipped
                if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 2:
                    continue
                poly = QtGui.QPolygonF([QtCore.QPointF(ox + pts[i, 1] * s, oy + pts[i, 0] * s)
                                        for i in range(pts.shape[0])])   # (row,col)->(x,y)
                p.drawPolyline(poly)
            p.end()
        return QtGui.QIcon(pm)                         # empty XLD -> honest blank thumbnail

    def _var_icon(val):
        """A small thumbnail for an iconic variable: image/region shows its raster
        shape, a contour (XLD) shows its polylines. None for control scalars."""
        if isinstance(val, np.ndarray) and val.ndim in (2, 3):
            qi = _to_qimage(apply_display(val, display.currentText()), QtGui)
            if qi is not None:
                pm = QtGui.QPixmap.fromImage(qi).scaled(
                    _VAR_THUMB, _VAR_THUMB, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                return QtGui.QIcon(pm)
        elif isinstance(val, dict) and "cs" in val:
            return _contour_icon(val)
        return None

    def refresh_variables():
        if not state["dev_update"]["var"]:
            return                            # dev_update_var('off'): variable window frozen
        sel = var_list.currentRow()
        var_list.blockSignals(True); var_list.clear()
        var_list.setIconSize(QtCore.QSize(_VAR_THUMB, _VAR_THUMB))
        for label, idx, kind in _var_entries():
            try:
                val = model.result_upto(idx)
            except Exception:
                val = None
            ic = _var_icon(val)                      # iconic vars get a shape thumbnail
            iconic = ic is not None
            it = QtWidgets.QListWidgetItem("%s   %s · %s" % (label, kind, "iconic" if iconic else "control"))
            it.setData(QtCore.Qt.UserRole, idx)
            if ic is not None:
                it.setIcon(ic)
            var_list.addItem(it)
        var_list.setCurrentRow(sel if 0 <= sel < var_list.count() else var_list.count() - 1)
        var_list.blockSignals(False)
        _mark_variable_frontier()
        show_variable_inspection()

    def _mark_variable_frontier():
        """Grey out variables whose stage output lies past the current execution
        frontier (the selected stage) so that, during step-through, not-yet-reached
        outputs read as *pending* instead of already-present (Codex #8). Row 0 = the
        raw input (always live); stage i's output is live once the frontier reaches i."""
        frontier = stage_list.currentRow()             # -1 = only the raw input is live
        for r in range(var_list.count()):
            it = var_list.item(r)
            idx = it.data(QtCore.Qt.UserRole)
            pending = isinstance(idx, int) and idx > frontier
            it.setForeground(QtGui.QColor(MUTED) if pending else QtGui.QBrush())
            base = it.text().split("   ", 1)
            tag = base[1] if len(base) == 2 else ""
            want = (tag.replace(" · pending", "") + (" · pending" if pending else ""))
            if want != tag:
                it.setText("%s   %s" % (base[0], want))
    win._mark_variable_frontier = _mark_variable_frontier

    def display_variable(target="current"):
        """Show the selected variable (HDevelop: double-click iconic → current window).

        ``target``: ``"current"`` = the active graphics window (dev_display),
        ``"new"`` = a fresh window, ``"main"`` = the resident primary view.
        Legacy booleans are accepted (``True`` → new window, ``False`` → main)."""
        if target is True:
            target = "new"
        elif target is False:
            target = "main"
        it = var_list.currentItem()
        if it is None:
            return
        try:
            val = model.result_upto(it.data(QtCore.Qt.UserRole))
        except Exception as e:
            flash("cannot display: %s" % e); return
        if isinstance(val, np.ndarray) and val.ndim in (2, 3):
            qi = _to_qimage(apply_display(val, display.currentText()), QtGui)
            pm = QtGui.QPixmap.fromImage(qi) if qi is not None else None
            if pm is None:
                flash("cannot render variable"); return
            vtitle = "var %s" % it.text().split("  ", 1)[0]
            if target == "new":
                new_graphics_window(pm, title=vtitle)
            else:
                v = view if target == "main" else _current_view()
                v.set_pixmap(pm); v.fit(); v.set_data(val)
                where = "Graphics %d" % (_current_handle() if target == "current" else 1)
                flash("displayed %s in %s" % (vtitle, where))
        else:
            flash("variable is not iconic — see the inspector")

    var_list.currentRowChanged.connect(lambda _r: show_variable_inspection())
    var_list.itemDoubleClicked.connect(lambda _it: display_variable("current"))  # HDevelop: → current window
    v_disp.clicked.connect(lambda: display_variable("new"))
    v_here.clicked.connect(lambda: display_variable("current"))
    win._variables = {"list": var_list, "refresh": refresh_variables, "display": display_variable}
    win._contour_icon = _contour_icon                # exposed for the headless thumbnail test

    # -- dedicated Operator Help dialog (HTML: args / usage / sample code / links) - #
    help_browser = QtWidgets.QTextBrowser()
    help_browser.setOpenLinks(False)          # custom op:/sample:/run: anchors handled below
    help_browser.setStyleSheet("QTextBrowser{background:#1b1e28;border:1px solid #2c313f;}")
    help_dialog = QtWidgets.QDialog(win)       # dedicated, non-modal (good for multi-monitor)
    help_dialog.setWindowTitle("Operator help — Fullseye Studio")
    help_dialog.resize(560, 640)
    _hdl = QtWidgets.QVBoxLayout(help_dialog)
    _htop = QtWidgets.QHBoxLayout()
    hd_back = QtWidgets.QPushButton("◀"); hd_back.setToolTip("Back")
    hd_fwd = QtWidgets.QPushButton("▶"); hd_fwd.setToolTip("Forward")
    help_pick = QtWidgets.QComboBox(); help_pick.setEditable(True)
    # "Jump to any operator's help" spans BOTH registries. 3-D ops are suffixed "  (3D)" so a
    # name shared by a 2-D and a 3-D op (e.g. fill_holes) stays unambiguous; the display text
    # maps back to (dim, name) for dim-aware help dispatch via show_op_help.
    _help_entries = {n: ("2d", n) for n in op_names}
    _help_d3 = []
    try:
        import ops3d as _o3
        for _n in sorted(_o3.OPS3D):
            _disp = "%s  (3D)" % _n
            _help_entries[_disp] = ("3d", _n); _help_d3.append(_disp)
    except Exception:
        pass
    help_pick.addItems(list(op_names) + _help_d3)
    help_pick.setToolTip("Jump to any operator's help (2-D image ops + 3-D point/mesh/volume ops)")
    hd_copy = QtWidgets.QPushButton("Copy sig")
    hd_copy.setToolTip("Copy this operator's signature to the clipboard")
    _htop.addWidget(hd_back); _htop.addWidget(hd_fwd); _htop.addWidget(help_pick, 1); _htop.addWidget(hd_copy)
    _hdl.addLayout(_htop); _hdl.addWidget(help_browser, 1)

    def show_op_help(name, dim="2d"):
        if not name:
            return
        if dim == "3d":
            try:
                import ops3d as _o3
                row = _o3.OPS3D.get(name)
            except Exception:
                row = None
            help_browser.setHtml(op_help_html(name, dim="3d", meta=row))
            disp = "%s  (3D)" % name
        else:
            row = _op_row(name) or {"in_sort": "?", "out_sort": "?"}
            help_browser.setHtml(op_help_html(name, getattr(win, "_lang", "en"), row))
            disp = name
        i = help_pick.findText(disp)
        if i >= 0:
            help_pick.blockSignals(True); help_pick.setCurrentIndex(i); help_pick.blockSignals(False)
        help_dialog.show(); help_dialog.raise_(); help_dialog.activateWindow()

    def _help_anchor(url):
        s = url.toString()
        if s.startswith("op3d:"):              # related 3-D operator link
            show_op_help(s[5:], "3d")
        elif s.startswith("op:"):              # related-operator link (2-D)
            show_op_help(s[3:])
        elif s.startswith("sample:") or s.startswith("run:"):   # load a sample pipeline
            import urllib.parse as _up
            code = _up.unquote(s.split(":", 1)[1])
            code_edit.setPlainText(code)
            apply_program()
            if s.startswith("run:"):
                run_program(True)
            try:
                win._docks["program"].show(); win._docks["program"].raise_()
            except Exception:
                pass
            flash("loaded sample pipeline from help")
        elif s.startswith("guide2d:"):          # family usage guide (generated from docs/ops/2d/guides)
            fam = s.split(":", 1)[1]
            p = os.path.join(_ASSETS, "op_help", "guide_%s.html" % fam)
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        help_browser.setHtml(f.read())
                    flash("opened family guide: " + fam)
                except Exception:
                    pass
            else:
                flash("guide not built: run `py -3.11 tools/opdocs.py html`")
        elif s.startswith("example2d:") or s.startswith("example3d:"):   # worked-example source
            scheme, ex = s.split(":", 1)
            sub = "examples_3d" if scheme == "example3d" else "examples"
            p = os.path.join(os.path.dirname(_ASSETS), sub, ex + ".py")
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        src = f.read()
                    esc = src.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    help_browser.setHtml(
                        "<h2 style='color:#f5a524'>%s</h2>"
                        "<p style='color:#8b91a0'>実行できる検証済みサンプル · "
                        "<code>py -3.11 %s/%s.py</code></p>"
                        "<pre style='background:#12141b;border:1px solid #2c313f;padding:6px;"
                        "color:#22d3bf'>%s</pre>" % (ex, sub, ex, esc))
                    flash("opened example source: " + ex)
                except Exception:
                    pass
            else:
                flash("example source not found: %s/%s.py" % (sub, ex))

    help_browser.anchorClicked.connect(_help_anchor)
    # entries map display-text -> (dim, name); show_op_help takes (name, dim), so pass them
    # in that order (unpacking the tuple directly would swap them: name<-dim, dim<-name).
    help_pick.currentTextChanged.connect(
        lambda t: show_op_help(_help_entries[t][1], _help_entries[t][0]) if t in _help_entries else None)
    def _copy_help_sig():
        t = help_pick.currentText()
        entry = _help_entries.get(t)
        if entry and entry[0] == "3d":         # 3-D op: signature from the ops3d registry
            try:
                import ops3d as _o3, inspect as _insp
                info = _o3.OPS3D.get(entry[1]) or {}
                fn = info.get("func")
                sig = str(_insp.signature(fn)) if fn is not None else "(...)"
                QtWidgets.QApplication.clipboard().setText("%s.%s%s" % (info.get("module", ""), entry[1], sig))
                flash("copied signature: " + entry[1] + " (3D)")
            except Exception:
                pass
            return
        row = _op_row(t)
        if row:
            QtWidgets.QApplication.clipboard().setText(op_signature_detail(row))
            flash("copied signature: " + t)
    hd_copy.clicked.connect(_copy_help_sig)
    hd_back.clicked.connect(help_browser.backward)
    hd_fwd.clicked.connect(help_browser.forward)
    b_help.clicked.connect(
        lambda: show_op_help(op_list.currentItem().data(QtCore.Qt.UserRole)) if op_list.currentItem() else None)
    win._help = {"dialog": help_dialog, "browser": help_browser, "show": show_op_help,
                 "pick": help_pick, "entries": _help_entries}

    def sync_panels():
        sync_program(); refresh_variables()
    win._code_sync = sync_panels
    sync_panels()

    # right-click context menus (dev-IDE density: act where you point) --------- #
    def _ctx_menu(widget, actions_fn):
        widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        def _show(pos):
            items = actions_fn()
            if not items:
                return
            menu = QtWidgets.QMenu(widget)
            for label, cb in items:
                if label == "---":
                    menu.addSeparator()
                else:
                    menu.addAction(label).triggered.connect(cb)
            menu.exec(widget.mapToGlobal(pos))
        widget.customContextMenuRequested.connect(_show)
        return actions_fn                       # returned for tests / reuse

    def _op_ctx():
        cur = op_list.currentItem()
        if cur is None:
            return []
        name = cur.data(QtCore.Qt.UserRole)
        return [("Insert into pipeline", lambda: add_op(cur)),
                ("Run once (preview)", run_op_once),
                ("---", None),
                ("Operator help…", lambda: show_op_help(name))]

    def _stage_ctx():
        i = stage_list.currentRow()
        if not (0 <= i < len(model.stages)):
            return []
        return [("Run to here", lambda: step_to(i)),
                ("Run from here", lambda: win._program["run_from"](i + 1)),
                ("Continue (to breakpoint / end)", lambda: win._program["continue"]()),
                ("---", None),
                ("Remove stage", remove),
                ("Move up", lambda: move(-1)),
                ("Move down", lambda: move(1))]

    def inspect_variable_popup():
        # right-click "show me the contents" (user spec 2026-08-30): a self-contained
        # popup with the full inspection, percentiles and a value preview — no need to
        # hunt for the docked inspector panel.
        it = var_list.currentItem()
        if it is None:
            return
        try:
            val = model.result_upto(it.data(QtCore.Qt.UserRole))
        except Exception as e:
            report_error("inspect", e); return
        lines = [format_inspection(inspect_result(val))]
        if isinstance(val, np.ndarray) and val.ndim in (2, 3):
            plane = val if val.ndim == 2 else val[..., 0]
            fin = plane[np.isfinite(plane)]
            if fin.size:
                qs = np.percentile(fin, [1, 25, 50, 75, 99])
                lines.append("")
                lines.append("percentiles 1/25/50/75/99: "
                             + "  ".join("%.5g" % q for q in qs))
            with np.printoptions(precision=4, threshold=200, linewidth=96,
                                 suppress=True):
                lines.append("")
                lines.append("top-left 6×6 preview:")
                lines.append(str(plane[:6, :6]))
        dlgv = QtWidgets.QDialog(win)
        dlgv.setWindowTitle("Variable — %s" % it.text().strip().splitlines()[0])
        tag_dialog(dlgv, "reference"); dlgv.setModal(False)
        lay = QtWidgets.QVBoxLayout(dlgv)
        te = QtWidgets.QPlainTextEdit(); te.setReadOnly(True)
        te.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
        te.setPlainText(chr(10).join(lines))
        lay.addWidget(te)
        dlgv.resize(480, 400); dlgv.show()
        win._last_var_popup = dlgv                    # test / scripting hook
        return dlgv

    def _var_ctx():
        if var_list.currentItem() is None:
            return []
        return [("Inspect in popup…", inspect_variable_popup),
                ("---", None),
                ("Display → current window", lambda: display_variable("current")),
                ("Display → new window", lambda: display_variable("new")),
                ("---", None),
                ("Inspect (panel)", show_variable_inspection)]

    win._ctx = {"operators": _ctx_menu(op_list, _op_ctx),
                "pipeline": _ctx_menu(stage_list, _stage_ctx),
                "variables": _ctx_menu(var_list, _var_ctx)}
    win._variables["popup"] = inspect_variable_popup     # right-click "Inspect in popup…"

    act_palette.triggered.connect(show_palette)
    act_shortcuts.triggered.connect(show_shortcuts)
    act_op_help.triggered.connect(
        lambda: show_op_help((op_list.currentItem().data(QtCore.Qt.UserRole))
                             if op_list.currentItem() else (op_names[0] if op_names else "")))
    act_samples.triggered.connect(show_samples)
    act_3d_examples.triggered.connect(show_3d_examples)
    act_3d_ops.triggered.connect(show_3d_ops)
    act_2d_examples.triggered.connect(show_2d_examples)
    act_pyedit.triggered.connect(lambda _=False: show_python_editor())
    b_browse_samples.clicked.connect(show_samples)       # sample gallery reachable from the panel
    win._samples = samples
    win._browse_samples = b_browse_samples
    win._show_samples = show_samples
    act_about.triggered.connect(show_about)

    def open_3d():
        raw = state.get("raw")
        if not isinstance(raw, np.ndarray):
            flash("load an image first — 3-D surface needs a height/depth map")
            return
        g = raw if raw.ndim == 2 else imgio.ensure_gray(raw)
        surf = show_3d_surface(g, win)
        win._surf = surf
        if surf is None:                 # GL-less env (offscreen / Remote Desktop / no GPU)
            flash("3-D surface needs OpenGL — unavailable in this display session")
    b_3d.clicked.connect(open_3d); act_3d.triggered.connect(open_3d)

    # ---- interactive 3-D viewer (View ▸ 3D viewer, Ctrl+4, disp_* directives) --- #
    _POINT_FILE_FILTER = ("3-D data (*.ply *.pcd *.xyz *.txt *.pts *.asc *.obj *.stl "
                          "*.off *.npy *.npz "
                          "*.nii *.nii.gz *.nrrd *.nhdr *.mha *.mhd *.tif *.tiff *.dcm)"
                          ";;All files (*)")
    _VOLUME_EXTS = (".nii", ".gz", ".nrrd", ".nhdr", ".mha", ".mhd",
                    ".tif", ".tiff", ".dcm")

    def _load_3d_file(path):
        """Load a 3-D file -> ``('mesh', V, F, None)`` or ``('points', P, None, C)``.
        A mesh format with real faces opens as a mesh; a **volume** format
        (DICOM/NIfTI/NRRD/MetaImage/TIFF stack via volio) opens as its
        Otsu-threshold boundary shell — physical-unit points ready for the
        walkthrough (a museum-piece view of a CT straight from the file
        dialog). Anything else (or a mesh read failure) falls back to its
        points. Raises on an unreadable file."""
        import mesh as meshmod
        ext = os.path.splitext(str(path))[1].lower()
        if ext in _VOLUME_EXTS:
            import volio                          # lazy: SimpleITK etc. optional
            vol, meta = volio.read_volume(str(path))
            P, C, info = volume_to_shell_points(vol, spacing=meta.spacing_mm)
            flash("volume %s -> shell %s pts (thr %.4g%s)"
                  % ("x".join(str(s) for s in info["shape"]), f"{info['n_points']:,}",
                     info["threshold"],
                     ", 1/%d 間引き" % info["downsampled_by"]
                     if info["downsampled_by"] > 1 else ""))
            return "points", P, None, C
        if ext == ".npy":                          # a saved 3-D array is a volume
            arr = np.load(str(path), allow_pickle=False)
            if arr.ndim == 3:                      # point files are (N, 3) = 2-D
                P, C, _info = volume_to_shell_points(arr)
                return "points", P, None, C
        if ext in (".obj", ".off", ".stl", ".ply"):
            try:
                V, F = meshmod.read_mesh(path)[:2]
                if np.asarray(F).size:
                    V, F = validate_mesh_faces(V, F)   # corrupt faces -> points fallback
                    return "mesh", V, F, None
            except Exception:
                pass                              # no faces / points-only file -> cloud
        P, C = meshmod.read_points(path, with_colors=True)
        return "points", P, None, C

    def open_viewer3d_window(data=None, title=None):
        """Open a Viewer3D on the graphics-window system (same numbering / cap /
        dev_set_window as every 2-D window). *data* = ('mesh', V, F, None) or
        ('points', P, None, colors); None shows the synthetic demo cloud."""
        v3 = Viewer3D()
        if data is None:
            P, _k = demo_cluster_cloud()
            v3.set_points(P)
            title = title or "3D viewer (demo cloud)"
        elif data[0] == "mesh":
            v3.set_mesh(data[1], data[2])
        else:
            v3.set_points(data[1], colors=data[3])
        sub = new_graphics_window(title=title or "3D viewer", widget=v3)
        if sub is None:                           # window cap — new_graphics_window flashed
            v3.deleteLater()
            return None
        sub._fs_viewer3d = v3
        sub.resize(560, 480)
        return sub

    def open_viewer3d(path=None):
        """View ▸ 3D viewer (Ctrl+4): pick a point-cloud/mesh file; Cancel opens
        the synthetic demo cloud so the viewer is explorable immediately."""
        if path is None:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                win, "Open 3-D data (Cancel = demo cloud)", "", _POINT_FILE_FILTER)
        if not path:
            return open_viewer3d_window(None)
        try:
            data = _load_3d_file(path)
        except Exception as e:
            report_error("3D viewer", e)
            return None
        sub = open_viewer3d_window(data, title="3D viewer — %s" % os.path.basename(str(path)))
        if sub is not None:
            flash("3D viewer: %s (%s, %d pts)" % (os.path.basename(str(path)),
                                                  data[0], data[1].shape[0]))
        return sub

    act_viewer3d.triggered.connect(lambda _=False: open_viewer3d())
    menu_view.addAction(act_viewer3d)
    win._open_viewer3d = open_viewer3d
    win._open_viewer3d_window = open_viewer3d_window

    # ---- Feature inspection (Tools ▸ Feature inspection, Ctrl+F5) --------------- #
    def show_feature_inspection():
        """HDevelop 'Feature Inspection' workalike, 2-D + 3-D in one dialog.

        2-D tab: the current pipeline result is labeled (a binary result keeps its
        own components; a gray result is auto-segmented with Otsu — stated in the
        info line), features are chosen from a checklist, and the table and image
        highlight each other both ways (row select -> region highlighted, image
        click -> row selected). 3-D tab: load a cloud (or the demo), cluster with
        pcseg.euclidean_clusters, get per-cluster features and an embedded
        interactive Viewer3D where the selected row's cluster is highlighted.
        Non-modal; all math is in the headless region_/cluster_ helpers."""
        old = getattr(win, "_feat_dlg", None)
        if old is not None:
            # destroy (not just hide) the previous dialog: its closures hold the
            # feat dict (base image, clouds, tables — can be hundreds of MB), so
            # every Ctrl+F5 reopen must release the old one instead of stacking.
            try:
                old.close()
                old.deleteLater()
            except Exception:
                pass
            win._feat_dlg = None
        dlg = QtWidgets.QDialog(win)
        # closing the dialog (X / dlg.close()) deletes it — same leak-avoidance:
        # a closed inspection must not keep its feature data alive invisibly.
        dlg.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        def _feat_dlg_destroyed(*_a, _d=dlg):
            if getattr(win, "_feat_dlg", None) is _d:
                win._feat_dlg = None
        dlg.destroyed.connect(_feat_dlg_destroyed)
        dlg.setWindowTitle("Feature inspection")
        tag_dialog(dlg, "viewer"); dlg.setModal(False)
        outer = QtWidgets.QVBoxLayout(dlg)
        tabs = QtWidgets.QTabWidget(); outer.addWidget(tabs)
        feat = {"objs": [], "headers": [], "rows": [], "base": None,
                "P": None, "colors": None, "clusters": [],
                "headers3": [], "rows3": []}

        # ------------------------- 2-D regions tab --------------------------- #
        w2 = QtWidgets.QWidget(); h2 = QtWidgets.QHBoxLayout(w2)
        left2 = QtWidgets.QVBoxLayout()
        info2 = QtWidgets.QLabel(); info2.setProperty("muted", True); info2.setWordWrap(True)
        checks = QtWidgets.QListWidget(); checks.setMaximumWidth(190)
        default_on = {"area", "row", "col", "width", "height", "circularity", "mean_gray"}
        for name in REGION_FEATURES:
            it = QtWidgets.QListWidgetItem(name)
            it.setFlags(it.flags() | QtCore.Qt.ItemIsUserCheckable)
            it.setCheckState(QtCore.Qt.Checked if name in default_on else QtCore.Qt.Unchecked)
            checks.addItem(it)
        table = QtWidgets.QTableWidget(); table.setSortingEnabled(True)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        iv = ImageView()
        b_csv2 = QtWidgets.QPushButton("Copy as CSV")
        b_refresh = QtWidgets.QPushButton("Refresh from result")
        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(b_refresh); row2.addStretch(1); row2.addWidget(b_csv2)
        left2.addWidget(info2)
        mid2 = QtWidgets.QHBoxLayout()
        mid2.addWidget(checks); mid2.addWidget(table, 1)
        left2.addLayout(mid2, 1); left2.addLayout(row2)
        h2.addLayout(left2, 3); h2.addWidget(iv, 2)
        tabs.addTab(w2, "2-D regions")

        def _checked_names():
            return [checks.item(i).text() for i in range(checks.count())
                    if checks.item(i).checkState() == QtCore.Qt.Checked]

        def _selected_obj_index():
            r = table.currentRow()
            if r < 0:
                return None
            it = table.item(r, 0)
            return None if it is None else it.data(QtCore.Qt.UserRole)

        def _render_2d(selected=None):
            base = feat["base"]
            if base is None:
                iv.set_message("no 2-D result to inspect\n\nrun a pipeline, then Refresh")
                return
            rgb = region_highlight_rgb(base, feat["objs"], selected)
            qi = _to_qimage(rgb, QtGui)
            if qi is not None:
                pm = QtGui.QPixmap.fromImage(qi)
                if not iv.set_pixmap_keep_view(pm):
                    iv.fit()
            iv.set_data(rgb)

        def _fill_table():
            names = _checked_names()
            base = feat["base"]
            gray = base if (isinstance(base, np.ndarray) and base.ndim == 2) else None
            headers, rows = region_feature_table(feat["objs"], names, image=gray)
            feat["headers"], feat["rows"] = headers, rows
            table.setSortingEnabled(False)
            table.clear()
            table.setColumnCount(len(headers)); table.setRowCount(len(rows))
            table.setHorizontalHeaderLabels(headers)
            for r, row in enumerate(rows):
                for c, v in enumerate(row):
                    it = QtWidgets.QTableWidgetItem()
                    it.setData(QtCore.Qt.EditRole, int(v) if c == 0 else float(v))
                    if c == 0:
                        it.setData(QtCore.Qt.UserRole, r)      # objs index rides the label cell
                    table.setItem(r, c, it)
            table.setSortingEnabled(True)
            table.resizeColumnsToContents()

        MAX_REGIONS = 500                        # table/HUD runaway guard (freeze prevention)

        def _refresh_2d():
            raw = state.get("raw")
            if isinstance(raw, np.ndarray) and raw.ndim == 2:
                try:
                    # speckle guard: scale the minimum region area with the image
                    # (~20 ppm, floor 1 px) so a noisy segmentation cannot flood
                    # the table with thousands of 1-px regions and freeze the UI
                    min_area = max(1, int(round(raw.size * 2e-5)))
                    objs, seg = region_feature_objects(raw, min_area=min_area)
                except Exception as e:
                    objs, seg = [], "error: %s" % truncate(e, 60)
                total = len(objs)
                if total > MAX_REGIONS:          # objects come largest-first
                    objs = objs[:MAX_REGIONS]
                feat["objs"] = objs
                img = model.image
                feat["base"] = (img if isinstance(img, np.ndarray) and img.ndim == 2
                                and img.shape == raw.shape else raw)
                note = ("" if total <= MAX_REGIONS
                        else "  ·  showing the largest %d of %d regions"
                             % (MAX_REGIONS, total))
                info2.setText("%d region(s) from the current result (%s)%s  ·  "
                              "click a row to highlight its region; click the image "
                              "to select its row"
                              % (len(objs), "binary labeling" if seg == "labels"
                                 else "gray input, auto-Otsu" if seg == "otsu" else seg,
                                 note))
            else:
                feat["objs"], feat["base"] = [], None
                info2.setText("no 2-D result — load an image / run a pipeline, then Refresh")
            _fill_table()
            _render_2d(None)

        def _on_row_selected():
            _render_2d(_selected_obj_index())

        def _on_image_click(x, y):
            idx = region_label_at(feat["objs"], y, x)
            if idx is None:
                table.clearSelection()
                _render_2d(None)
                return
            for r in range(table.rowCount()):
                it = table.item(r, 0)
                if it is not None and it.data(QtCore.Qt.UserRole) == idx:
                    table.selectRow(r); table.scrollToItem(it)
                    break

        def _copy_csv2():
            QtWidgets.QApplication.clipboard().setText(
                feature_table_csv(feat["headers"], feat["rows"]))
            flash("feature table copied as CSV (%d rows)" % len(feat["rows"]))

        table.itemSelectionChanged.connect(_on_row_selected)
        iv.click_cb = _on_image_click
        checks.itemChanged.connect(lambda _it: (_fill_table(), _render_2d(_selected_obj_index())))
        b_refresh.clicked.connect(lambda _=False: _refresh_2d())
        b_csv2.clicked.connect(lambda _=False: _copy_csv2())

        # ------------------------- 3-D clusters tab -------------------------- #
        w3 = QtWidgets.QWidget(); v3l = QtWidgets.QVBoxLayout(w3)
        bar3 = QtWidgets.QHBoxLayout()
        b_load3 = QtWidgets.QPushButton("Load point cloud…")
        b_demo3 = QtWidgets.QPushButton("Demo clusters")
        tol_spin = QtWidgets.QDoubleSpinBox(); tol_spin.setDecimals(4)
        tol_spin.setRange(0.0001, 10000.0); tol_spin.setValue(0.05)
        tol_spin.setPrefix("tol "); tol_spin.setToolTip(
            "Euclidean cluster tolerance (pcseg.euclidean_clusters); auto-suggested "
            "from the cloud's nearest-neighbour spacing on load")
        min_spin = QtWidgets.QSpinBox(); min_spin.setRange(1, 1000000); min_spin.setValue(10)
        min_spin.setPrefix("min "); min_spin.setToolTip("Minimum cluster size (points)")
        b_clu = QtWidgets.QPushButton("Cluster"); b_clu.setProperty("accent", True)
        b_csv3 = QtWidgets.QPushButton("Copy as CSV")
        for wdg in (b_load3, b_demo3, tol_spin, min_spin, b_clu):
            bar3.addWidget(wdg)
        bar3.addStretch(1); bar3.addWidget(b_csv3)
        info3 = QtWidgets.QLabel("load a cloud (or Demo clusters) — Studio's 3-D examples run "
                                 "as subprocesses, so this tab works from files / demo data")
        info3.setProperty("muted", True); info3.setWordWrap(True)
        split3 = QtWidgets.QHBoxLayout()
        table3 = QtWidgets.QTableWidget(); table3.setSortingEnabled(True)
        table3.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table3.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table3.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        v3 = Viewer3D()
        split3.addWidget(table3, 3); split3.addWidget(v3, 2)
        v3l.addLayout(bar3); v3l.addWidget(info3); v3l.addLayout(split3, 1)
        tabs.addTab(w3, "3-D clusters")

        def _recluster():
            P = feat["P"]
            if P is None:
                info3.setText("no cloud loaded — Load point cloud… or Demo clusters")
                return
            import pcseg
            try:
                clusters = pcseg.euclidean_clusters(P, tol=float(tol_spin.value()),
                                                    min_size=int(min_spin.value()))
            except Exception as e:
                report_error("clustering", e); return
            feat["clusters"] = clusters
            headers, rows = cluster_feature_table(P, clusters)
            feat["headers3"], feat["rows3"] = headers, rows
            table3.setSortingEnabled(False)
            table3.clear()
            table3.setColumnCount(len(headers)); table3.setRowCount(len(rows))
            table3.setHorizontalHeaderLabels(headers)
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    it = QtWidgets.QTableWidgetItem()
                    it.setData(QtCore.Qt.EditRole, int(val) if c == 0 else float(val))
                    if c == 0:
                        it.setData(QtCore.Qt.UserRole, r)
                    table3.setItem(r, c, it)
            table3.setSortingEnabled(True)
            table3.resizeColumnsToContents()
            v3.set_points(P, colors=feat["colors"])
            v3.set_clusters(clusters)
            info3.setText("%d cluster(s) of %d points (tol %.4g, min %d) — select a row "
                          "to highlight its cluster in the viewer"
                          % (len(clusters), P.shape[0], tol_spin.value(), min_spin.value()))

        def _set_cloud(P, colors=None, label=""):
            feat["P"] = np.asarray(P, np.float64).reshape(-1, 3)
            feat["colors"] = colors
            try:
                tol_spin.setValue(float(suggest_cluster_tol(feat["P"])))
            except Exception:
                pass
            info3.setText("%s: %d points — press Cluster" % (label or "cloud", feat["P"].shape[0]))
            v3.set_points(feat["P"], colors=colors)
            _recluster()

        def _load_cloud():
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                dlg, "Open point cloud", "", _POINT_FILE_FILTER)
            if not path:
                return
            try:
                kind, A, F_, C = _load_3d_file(path)
            except Exception as e:
                report_error("point cloud", e); return
            _set_cloud(A, colors=C, label=os.path.basename(path))

        def _on_row3_selected():
            r = table3.currentRow()
            it = table3.item(r, 0) if r >= 0 else None
            v3.set_selected_cluster(None if it is None else it.data(QtCore.Qt.UserRole))

        def _copy_csv3():
            QtWidgets.QApplication.clipboard().setText(
                feature_table_csv(feat["headers3"], feat["rows3"]))
            flash("cluster table copied as CSV (%d rows)" % len(feat["rows3"]))

        b_load3.clicked.connect(lambda _=False: _load_cloud())
        b_demo3.clicked.connect(lambda _=False: _set_cloud(demo_cluster_cloud()[0],
                                                           label="demo clusters"))
        b_clu.clicked.connect(lambda _=False: _recluster())
        table3.itemSelectionChanged.connect(_on_row3_selected)
        b_csv3.clicked.connect(lambda _=False: _copy_csv3())

        dlg._feat = {"tabs": tabs, "table": table, "checks": checks, "view": iv,
                     "refresh": _refresh_2d, "click": _on_image_click,
                     "copy_csv": _copy_csv2, "state": feat,
                     "table3": table3, "viewer3": v3, "set_cloud": _set_cloud,
                     "recluster": _recluster, "copy_csv3": _copy_csv3,
                     "tol": tol_spin, "min_size": min_spin}
        _refresh_2d()
        win._feat_dlg = dlg
        win._localize(dlg)
        persist_dialog_geometry(dlg, "featinspect", (1020, 620))
        dlg.show()
        return dlg

    act_featins.triggered.connect(lambda _=False: show_feature_inspection())
    win._feature_inspection = {"open": show_feature_inspection,
                               "dialog": lambda: getattr(win, "_feat_dlg", None)}

    # View ▸ Display mode — colour-map the result, mirrored with the Display combo
    # (was previously reachable only from the right panel). Menu <-> combo stay in sync.
    disp_menu = _menu(menu_view, "Display mode", "display_mode")
    _disp_group = QtGui.QActionGroup(win); _disp_group.setExclusive(True)
    win._display_actions = {}

    def _set_display_mode(mode):
        i = display.findText(mode)
        if i >= 0:
            display.setCurrentIndex(i)             # fires currentIndexChanged -> show_result

    for _mode in [display.itemText(i) for i in range(display.count())]:
        _a = QtGui.QAction(_mode, win); _a.setCheckable(True); _disp_group.addAction(_a)
        disp_menu.addAction(_a); win._display_actions[_mode] = _a
        _a.triggered.connect(lambda _=False, mo=_mode: _set_display_mode(mo))

    def _sync_display_menu(text=None):
        a = win._display_actions.get(text if text is not None else display.currentText())
        a and a.setChecked(True)
    display.currentTextChanged.connect(_sync_display_menu)
    _sync_display_menu()
    menu_view.addSeparator(); menu_view.addAction(act_3d)
    win._display_menu = disp_menu
    win._set_display_mode = _set_display_mode

    # View ▸ Display updates — HDevelop dev_update_{window,var,pc,time}: gate whether the
    # graphics window / variable window / execution cursor / per-line timings auto-update
    # while editing or running. Turn all off to make many edits (or a heavy run) without
    # the display cost, then back on to refresh to the current state (HDevelop updates when
    # execution stops). This is HDevelop's op-level answer to display cost; see
    # docs/HDEVELOP_DEV_OPS.md. The same flags back the script ops dev_update_* / dev_update_off|on.
    menu_view.addSeparator()
    upd_menu = _menu(menu_view, "Display updates", "display_updates")
    win._dev_update_actions = {}
    _UPD_LABELS = {"window": "Graphics window", "var": "Variable window",
                   "pc": "Program counter", "time": "Operator timings"}

    def _sync_dev_update_actions():
        for k in ("window", "var", "pc", "time"):
            a = win._dev_update_actions.get(k)
            if a is not None:
                a.blockSignals(True); a.setChecked(state["dev_update"][k]); a.blockSignals(False)
        tb_a = win._dev_update_actions.get("_toolbar")
        all_on = all(state["dev_update"].values())
        if tb_a is not None:
            tb_a.blockSignals(True); tb_a.setChecked(all_on); tb_a.blockSignals(False)
        lbl = getattr(win, "_update_label", None)
        if lbl is not None:                       # surface a frozen display, never silently
            off = [k for k, v in state["dev_update"].items() if not v]
            lbl.setText("" if all_on else "updates off: " + ",".join(off))

    def set_dev_update(kind, on):
        """dev_update_{window,var,pc,time} / dev_update_off|on: set a display-update flag
        (or ``"all"``); when re-enabled, refresh so the current state becomes visible."""
        on = bool(on)
        keys = list(state["dev_update"]) if kind == "all" else [kind]
        for k in keys:
            if k in state["dev_update"]:
                state["dev_update"][k] = on
        _sync_dev_update_actions()
        if on:                                    # HDevelop refreshes when updates resume
            if "window" in keys:
                show_result()
            if "var" in keys:
                refresh_variables()
        return on
    win._set_dev_update = set_dev_update

    for _k in ("window", "var", "pc", "time"):
        _a = QtGui.QAction(_UPD_LABELS[_k], win); _a.setCheckable(True); _a.setChecked(True)
        _a.triggered.connect(lambda on, k=_k: set_dev_update(k, on))
        upd_menu.addAction(_a); win._dev_update_actions[_k] = _a
    upd_menu.addSeparator()
    _a_off = QtGui.QAction("All off  (dev_update_off)", win)
    _a_off.triggered.connect(lambda: set_dev_update("all", False))
    _a_on = QtGui.QAction("All on  (dev_update_on)", win)
    _a_on.triggered.connect(lambda: set_dev_update("all", True))
    upd_menu.addAction(_a_off); upd_menu.addAction(_a_on)
    # Toolbar quick-toggle: on = everything auto-updates, off = display frozen for speed.
    act_upd = QtGui.QAction("Auto-update", win); act_upd.setCheckable(True); act_upd.setChecked(True)
    act_upd.setToolTip("Auto-update the display (HDevelop dev_update). Uncheck to edit / run "
                       "without the display cost, then check to refresh.")
    act_upd.triggered.connect(lambda on: set_dev_update("all", on))
    tb.addAction(act_upd); win._dev_update_actions["_toolbar"] = act_upd

    def _set_part(r1, c1, r2, c2):
        """dev_set_part: set the displayed image part of the CURRENT graphics window."""
        _current_view().set_part(r1, c1, r2, c2)
    win._set_part = _set_part

    def set_draw_style(mode=None, color=None, line_width=None):
        """dev_set_draw / dev_set_color / dev_set_line_width: how a region result is
        drawn over the source in the 'region overlay' display mode. Re-renders so the
        change is visible."""
        if mode in ("fill", "margin"):
            state["draw"]["mode"] = mode
        if color is not None:
            state["draw"]["color"] = color
        if line_width is not None:
            state["draw"]["line_width"] = max(1, int(line_width))
        for m, a in getattr(win, "_draw_mode_actions", {}).items():   # reflect in View > Region style
            a.setChecked(state["draw"]["mode"] == m)
        for cn, a in getattr(win, "_draw_color_actions", {}).items():
            a.setChecked(state["draw"]["color"] == _HALCON_COLORS[cn])
        show_result()
    win._set_draw_style = set_draw_style

    # View ▸ Region style — HDevelop dev_set_draw / dev_set_color for the region overlay
    menu_view.addSeparator()
    style_menu = _menu(menu_view, "Region style", "region_style")
    _draw_group = QtGui.QActionGroup(win); _draw_group.setExclusive(True)
    win._draw_mode_actions = {}
    for _m, _lbl in (("fill", "Fill"), ("margin", "Margin (outline)")):
        _a = QtGui.QAction(_lbl, win); _a.setCheckable(True); _a.setChecked(_m == "fill")
        _draw_group.addAction(_a); style_menu.addAction(_a); win._draw_mode_actions[_m] = _a
        _a.triggered.connect(lambda _=False, m=_m: set_draw_style(mode=m))
    color_menu = _menu(style_menu, "Color", "region_color")
    _color_group = QtGui.QActionGroup(win); _color_group.setExclusive(True)
    win._draw_color_actions = {}
    for _cn in ("orange", "red", "green", "blue", "yellow", "cyan", "magenta", "white"):
        _a = QtGui.QAction(_cn.capitalize(), win); _a.setCheckable(True); _a.setChecked(_cn == "orange")
        _color_group.addAction(_a); color_menu.addAction(_a); win._draw_color_actions[_cn] = _a
        _a.triggered.connect(lambda _=False, cn=_cn: set_draw_style(color=_HALCON_COLORS[cn]))
    win._region_style_menu = style_menu

    def apply_dev_directives(text, reclaim_stale=False):
        """Apply a program's dev_* display directives (source order): dev_update_* /
        dev_update_off|on set the display-update flags; dev_set_part zooms the current
        view; dev_set_lut/dev_clear_window drive the current window. Studio's runner
        batches stage evaluation, so these set the SESSION display state (the last
        value of each wins) rather than executing inline per line. Honest limit:
        unlike the pipeline stages (which honour if/for), dev_* directives are applied
        UNCONDITIONALLY — a dev_* inside a not-taken branch still fires. Put them at
        top level. The frozen-display state is surfaced by the status-bar indicator.
        Window management: dev_open_window (row, col, w, h) opens/places a graphics
        window and makes it current; dev_set_window (handle) selects one by handle;
        dev_set_window_extents (row, col, w, h) moves/resizes the current window
        (-1 keeps a value); dev_close_window closes the current one (the resident
        primary window is close-protected). Windows opened by the program are keyed
        to their source-order slot, so RE-Applying the same program repositions the
        SAME windows instead of multiplying them. See docs/HDEVELOP_DEV_OPS.md.

        disp_* directives (HALCON Graphics chapter): disp_image (n) / disp_region (n)
        draw stage n's output (1-based; omitted = final result) into the CURRENT
        graphics window — a 3-D current window redirects to the primary view.
        disp_points3d ('file') / disp_mesh3d ('file') / disp_object_model_3d ('file')
        open the interactive 3-D viewer on the graphics-window system, slot-keyed
        like dev_open_window so a re-Apply reuses the same windows. Every disp_*
        is recorded in state['disp_log'] (headless-testable; a load failure is
        logged + flashed, never raised)."""
        open_slot = 0
        d3_slot = 0

        def _log_disp(name, args, ok, **extra):
            rec = {"op": name, "args": list(args), "ok": bool(ok)}
            rec.update(extra)
            state.setdefault("disp_log", []).append(rec)

        def _disp_2d(name, args):
            try:
                # docstring contract: 1-based stage number; omitted OR 0 (or any
                # non-positive value) = the FINAL result. int(args[0]) - 1 alone
                # would turn 0 into -1 = the raw input image, breaking the contract.
                n = int(args[0]) if args and isinstance(args[0], float) else 0
                idx = (n - 1) if n >= 1 else len(model.stages) - 1
                val = model.result_upto(idx)
            except Exception as e:
                _log_disp(name, args, False, error=truncate(e, 80))
                flash("%s: %s" % (name, truncate(e, 80)))
                return
            if name == "disp_region":
                shown = apply_display(val, "region overlay", base=model.image,
                                      draw=state["draw"])
            else:
                shown = apply_display(val, display.currentText(), base=model.image,
                                      draw=state["draw"])
            ok = False
            if isinstance(shown, np.ndarray) and shown.ndim in (2, 3):
                qi = _to_qimage(shown, QtGui)
                if qi is not None:
                    gv = _current_view()
                    gv.set_pixmap(QtGui.QPixmap.fromImage(qi)); gv.fit()
                    gv.set_data(val if isinstance(val, np.ndarray) else shown)
                    ok = True
            _log_disp(name, args, ok, stage=idx + 1)

        def _disp_3d(name, args, slot):
            path = str(args[0]) if args else ""
            if path and not os.path.isabs(path):
                # a relative path in a user's program means "relative to where I
                # ran Studio" (process cwd) — resolve there first; fall back to
                # the studio.py directory only when the cwd candidate is missing
                # (keeps shipped demo programs working from any cwd).
                cand = os.path.abspath(path)
                if not os.path.exists(cand):
                    alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
                    if os.path.exists(alt):
                        cand = alt
                path = cand
            sub = next((s for s in win._graphics_windows
                        if s in mdi.subWindowList()
                        and getattr(s, "_fs_disp3d_slot", None) == slot), None)
            try:
                if not path:
                    raise ValueError("%s needs a file path argument" % name)
                if name == "disp_mesh3d":
                    import mesh as meshmod
                    V, F = validate_mesh_faces(*meshmod.read_mesh(path)[:2])
                    data = ("mesh", V, F, None)
                elif name == "disp_points3d":
                    import mesh as meshmod
                    P, C = meshmod.read_points(path, with_colors=True)
                    data = ("points", P, None, C)
                else:                              # disp_object_model_3d: dispatch on file
                    data = _load_3d_file(path)
                # showing is inside the try too: a mesh that passed loading but
                # still breaks the viewer (degenerate arrays etc.) must fail
                # soft (log+flash), never crash the whole directive pass.
                if sub is not None:                # re-Apply: reuse the slot's window
                    v3 = getattr(sub, "_fs_viewer3d", None)
                    if v3 is not None:
                        (v3.set_mesh(data[1], data[2]) if data[0] == "mesh"
                         else v3.set_points(data[1], colors=data[3]))
                    win._current_gfx = sub
                    _update_current_indicator()
                else:
                    sub = open_viewer3d_window(
                        data, title="3D viewer (program %d)" % slot)
                    if sub is None:                # window cap — already flashed
                        _log_disp(name, args, False, error="graphics window limit")
                        return
                    sub._fs_disp3d_slot = slot
            except Exception as e:
                _log_disp(name, args, False, error=truncate(e, 100))
                flash("%s: %s" % (name, truncate(e, 100)))
                return
            _log_disp(name, args, True, kind=data[0],
                      n_points=int(np.asarray(data[1]).shape[0]))

        for name, args in extract_dev_directives(text):
            if name == "dev_update_off":
                set_dev_update("all", False)
            elif name == "dev_update_on":
                set_dev_update("all", True)
            elif name in ("dev_update_window", "dev_update_var",
                          "dev_update_pc", "dev_update_time"):
                on = not (args and str(args[0]).lower() in ("off", "0", "0.0", "false"))
                set_dev_update(name[len("dev_update_"):], on)
            elif name == "dev_set_part" and len(args) >= 4:
                try:
                    _set_part(int(args[0]), int(args[1]), int(args[2]), int(args[3]))
                except (TypeError, ValueError):
                    pass
            elif name == "dev_set_lut" and args:
                lut = str(args[0]).lower()             # map a HALCON LUT name to a Studio display mode
                match = next((m for m in win._display_actions
                              if m.lower() == lut or lut in m.lower()), None)
                if match is not None:
                    win._set_display_mode(match)       # only Studio's display-mode LUTs are honoured
            elif name == "dev_clear_window":
                _current_view().clear()
            elif name == "dev_set_draw" and args:
                set_draw_style(mode=str(args[0]).lower())      # 'fill' | 'margin'
            elif name == "dev_set_color" and args:
                col = _HALCON_COLORS.get(str(args[0]).lower())
                if col is not None:
                    set_draw_style(color=col)
            elif name == "dev_set_line_width" and args:
                try:
                    set_draw_style(line_width=int(args[0]))
                except (TypeError, ValueError):
                    pass
            elif name == "set_system" and len(args) >= 2:
                try:
                    _set_system_param(str(args[0]), args[1])   # HALCON set_system(param, value)
                except (TypeError, ValueError):
                    pass
            elif name == "dev_open_window":
                open_slot += 1
                try:
                    r, c = int(args[0]), int(args[1])
                    w_, h_ = int(args[2]), int(args[3])
                except (IndexError, TypeError, ValueError):
                    r = c = 0; w_, h_ = 440, 360
                sub = next((s for s in win._graphics_windows
                            if s in mdi.subWindowList()
                            and getattr(s, "_fs_directive_slot", None) == open_slot), None)
                if sub is None:
                    sub = new_graphics_window(title="Graphics (program %d)" % open_slot)
                    if sub is None:                    # window cap reached — skip placement
                        continue
                    sub._fs_directive_slot = open_slot
                else:
                    win._current_gfx = sub
                    _update_current_indicator()
                sub.move(max(0, c), max(0, r))
                sub.resize(max(80, w_), max(60, h_))
            elif name == "dev_set_window" and args:
                try:
                    hd = int(args[0])
                except (TypeError, ValueError):
                    hd = -1
                target = next((s for s in win._graphics_windows
                               if s in mdi.subWindowList()
                               and getattr(s, "_fs_handle", None) == hd), None)
                if target is not None:
                    win._current_gfx = target
                    _update_current_indicator()
            elif name == "dev_set_window_extents" and len(args) >= 4:
                sub = win._current_gfx
                if sub is not None and sub in mdi.subWindowList():
                    try:
                        r, c, w_, h_ = (int(a) for a in args[:4])
                    except (TypeError, ValueError):
                        r = c = w_ = h_ = -1
                    g = sub.geometry()
                    sub.move(c if c >= 0 else g.x(), r if r >= 0 else g.y())
                    sub.resize(w_ if w_ > 0 else g.width(), h_ if h_ > 0 else g.height())
            elif name == "dev_close_window":
                sub = win._current_gfx
                if sub is win._primary_gsub:
                    flash("the primary graphics window stays open (resident view)")
                elif sub is not None and sub in mdi.subWindowList():
                    sub.close()
                    win._current_gfx = win._primary_gsub
                    _update_current_indicator()
            elif name in ("disp_image", "disp_region"):
                _disp_2d(name, args)
            elif name in ("disp_points3d", "disp_mesh3d", "disp_object_model_3d"):
                d3_slot += 1
                _disp_3d(name, args, d3_slot)
            # dev_disp_text is a DRAW directive applied after the render (apply_text_directives)
        # ディレクティブ数が減った再 Apply で取り残される旧スロット窓を回収(窓リーク防止)。
        # フルプログラムの Apply 経路のみ(reclaim_stale=True)— スニペットの直接適用で
        # プログラム窓を誤回収しないため。
        # A re-Apply that reaches FEWER dev_open_window slots must close the stale
        # ones; only the full-program Apply path opts in, so applying a snippet
        # directly never garbage-collects the program's windows.
        if reclaim_stale:
            for sub in list(win._graphics_windows):
                slot = getattr(sub, "_fs_directive_slot", None)
                slot3 = getattr(sub, "_fs_disp3d_slot", None)
                stale = ((slot is not None and slot > open_slot)
                         or (slot3 is not None and slot3 > d3_slot))
                if stale and sub in mdi.subWindowList():
                    sub.close()
                    if win._current_gfx is sub:
                        win._current_gfx = win._primary_gsub
                        _update_current_indicator()
    win._apply_dev_directives = apply_dev_directives

    def apply_text_directives(text):
        """dev_disp_text: annotations drawn AFTER the pipeline render (a fresh render
        clears them first), so the text sits on top of the result. Separated from the
        state/style directives, which are applied before the render."""
        for name, args in extract_dev_directives(text):
            if name == "dev_disp_text" and args:
                label = str(args[0])
                row = int(args[1]) if len(args) > 1 and isinstance(args[1], float) else 12
                col = int(args[2]) if len(args) > 2 and isinstance(args[2], float) else 12
                color = (_HALCON_COLORS.get(str(args[3]).lower(), (1.0, 1.0, 1.0))
                         if len(args) > 3 else state["draw"]["color"])
                _current_view().disp_text(row, col, label, color)
    win._apply_text_directives = apply_text_directives
    win._disp_text = lambda row, col, s, color=(1.0, 1.0, 1.0): _current_view().disp_text(row, col, s, color)

    # -- HALCON set_system-style global configuration (Tools > System settings) ----- #
    def _cv2_mod():
        try:
            import cv2
            return cv2
        except Exception:
            return None

    def _persist_system():
        s = QtCore.QSettings("Fullseye", "Studio"); s.beginGroup("system")
        s.setValue("threads", int(state["system"]["threads"]))
        s.setValue("operator_timeout_ms", int(state["system"]["operator_timeout_ms"]))
        s.setValue("max_graphics_windows", int(state["system"]["max_graphics_windows"]))
        s.endGroup()

    def _get_system_param(name):
        """get_system: read a HALCON-style system parameter (live where applicable)."""
        if name in ("thread_num", "threads"):
            cv2 = _cv2_mod()
            return int(cv2.getNumThreads()) if cv2 is not None else int(state["system"]["threads"])
        if name in ("operator_timeout", "operator_timeout_ms"):
            return int(state["system"]["operator_timeout_ms"])
        if name == "max_graphics_windows":
            return int(state["system"]["max_graphics_windows"])
        if name in ("check", "error_check"):
            return "on"            # Fullseye's runtime is fail-closed (industrial refuses degraded ops)
        raise ValueError("unknown system parameter %r; known: thread_num, operator_timeout, "
                         "max_graphics_windows, check" % (name,))

    def _set_system_param(name, value):
        """set_system: set a HALCON-style system parameter (fail-closed on an unknown name)."""
        if name in ("thread_num", "threads"):
            n = int(value)
            cv2 = _cv2_mod()
            if cv2 is not None:
                cv2.setNumThreads(n)            # 0 = OpenCV default (all cores); affects op speed
            state["system"]["threads"] = n
            _persist_system()
            return n
        if name in ("operator_timeout", "operator_timeout_ms"):
            ms = int(value)
            if ms < 0:
                raise ValueError("operator_timeout must be >= 0 (0 = off)")
            state["system"]["operator_timeout_ms"] = ms
            _persist_system()
            return ms
        if name == "max_graphics_windows":
            n = int(value)
            if n < 1:
                raise ValueError("max_graphics_windows must be >= 1")
            state["system"]["max_graphics_windows"] = n
            _persist_system()
            return n
        raise ValueError("unknown system parameter %r; known: thread_num, operator_timeout, "
                         "max_graphics_windows" % (name,))
    win._set_system_param = _set_system_param
    win._get_system_param = _get_system_param

    def _apply_mono_font(pt):
        """Apply the monospace editor font size to every live code surface (the
        pipeline program editor + open Python Editor tabs) and persist it; a new
        CodeEditor picks the persisted value up on construction."""
        pt = max(6, min(int(pt), 32))
        QtCore.QSettings("Fullseye", "Studio").setValue("ui/mono_font_pt", pt)
        for ed in [code_edit] + ([win._pyedit["tabs"].widget(i)
                                  for i in range(win._pyedit["tabs"].count())]
                                 if getattr(win, "_pyedit", None) else []):
            f = ed.font(); f.setPointSize(pt); ed.setFont(f)
            # widget-level rule outranks the app QSS (which pins QPlainTextEdit fonts)
            ed.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace; "
                             "font-size:%dpt;" % pt)
            ed.setTabStopDistance(4 * ed.fontMetrics().horizontalAdvance(" "))
        return pt
    win._apply_mono_font = _apply_mono_font
    try:        # apply the persisted size to the program editor at startup
        _apply_mono_font(int(QtCore.QSettings("Fullseye", "Studio")
                             .value("ui/mono_font_pt", 10)))
    except (TypeError, ValueError):
        pass

    def open_system_settings():
        # Preferences hub (Tools menu / Ctrl+,) — the parameters a vision IDE needs at
        # hand: execution (threads / timeout), windows (cap), display defaults (LUT /
        # region draw), and the developer surface (editor font / run interpreter).
        dlg = QtWidgets.QDialog(win)
        dlg.setWindowTitle("System settings — Fullseye Studio")
        tag_dialog(dlg, "system")
        # -- category tree (left, whole-picture overview) + one page per category
        #    (right), Qt Creator preferences style (user spec 2026-08-30) --
        root = QtWidgets.QVBoxLayout(dlg)
        body = QtWidgets.QHBoxLayout()
        cat_tree = QtWidgets.QTreeWidget(); cat_tree.setHeaderHidden(True)
        cat_tree.setFixedWidth(180)
        stack = QtWidgets.QStackedWidget()

        def _settings_page(title, rows):
            pg = QtWidgets.QWidget(); f = QtWidgets.QFormLayout(pg)
            for lab, wdg in rows:
                f.addRow(tr(lab), wdg)
            i = stack.addWidget(pg)
            it = QtWidgets.QTreeWidgetItem([tr(title)])
            it.setData(0, QtCore.Qt.UserRole, i)
            cat_tree.addTopLevelItem(it)
            return pg
        th = QtWidgets.QSpinBox(); th.setRange(0, 256); th.setValue(_get_system_param("thread_num"))
        th.setToolTip("set_system('thread_num'): OpenCV worker threads (0 = default / all). "
                      "Affects interactive operator speed.")
        to = QtWidgets.QSpinBox(); to.setRange(0, 600000); to.setSuffix(" ms")
        to.setValue(_get_system_param("operator_timeout"))
        to.setToolTip("set_operator_timeout: SOFT per-stage timeout — a slower stage is flagged "
                      "in Run status (native ops cannot be hard-interrupted; 0 = off).")
        mw = QtWidgets.QSpinBox(); mw.setRange(1, 4096)
        mw.setValue(_get_system_param("max_graphics_windows"))
        mw.setToolTip("set_system('max_graphics_windows'): cap on open graphics windows.\n"
                      "Guards every path (dev_open_window scripts, Ctrl+G, variable display) "
                      "so a looping program cannot flood the MDI.")
        sset = QtCore.QSettings("Fullseye", "Studio")
        dmode = QtWidgets.QComboBox(); dmode.addItems(sorted(win._display_actions))
        cur_mode = next((m for m, a in win._display_actions.items() if a.isChecked()),
                        None)
        if cur_mode is not None:
            dmode.setCurrentText(cur_mode)
        dmode.setToolTip("Default display mode (LUT) — applied now and restored on startup.")
        drawm = QtWidgets.QComboBox(); drawm.addItems(["fill", "margin"])
        drawm.setCurrentText(str(state["draw"].get("mode", "fill")))
        drawm.setToolTip("dev_set_draw default: how a region result is painted over the image.")
        drawlw = QtWidgets.QSpinBox(); drawlw.setRange(1, 9)
        drawlw.setValue(int(state["draw"].get("line_width", 1)))
        drawlw.setToolTip("dev_set_line_width default for the margin draw mode.")
        fpt = QtWidgets.QSpinBox(); fpt.setRange(6, 32)
        fpt.setValue(int(sset.value("ui/mono_font_pt", 10)))
        fpt.setToolTip("Monospace font size for the program editor, Python Editor tabs "
                       "and code windows.")
        interp = QtWidgets.QLineEdit(str(sset.value("pyedit/interpreter", "") or ""))
        interp.setPlaceholderText(sys.executable + "   (empty = this Studio's Python)")
        interp.setToolTip("Interpreter used by the Python Editor's Run. Empty = the Python "
                          "running Studio. A non-existent path is refused (fail-closed).")
        chk = QtWidgets.QLabel("fail-closed  (the runtime refuses degraded operators)")
        chk.setStyleSheet("QLabel{color:%s;}" % MUTED)
        _settings_page("Execution", [("Threads (thread_num)", th),
                                     ("Operator timeout", to),
                                     ("Error checking (set_check)", chk)])
        _settings_page("Windows", [("Max graphics windows", mw)])
        _settings_page("Display", [("Default display mode", dmode),
                                   ("Region draw (dev_set_draw)", drawm),
                                   ("Region line width", drawlw)])
        _settings_page("Editor", [("Editor font size", fpt),
                                  ("Python Editor interpreter", interp)])
        cat_tree.currentItemChanged.connect(
            lambda it, _prev=None: it is not None
            and stack.setCurrentIndex(it.data(0, QtCore.Qt.UserRole)))
        cat_tree.setCurrentItem(cat_tree.topLevelItem(0))
        body.addWidget(cat_tree); body.addWidget(stack, 1)
        root.addLayout(body, 1)
        bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        root.addWidget(bb)
        dlg.resize(640, 420)
        dlg._tree = cat_tree; dlg._stack = stack     # test / scripting hooks
        win._system_dialog = dlg               # for headless tests
        # NOTE: no win._localize here — this dialog is rebuilt per-open with tr() at
        # build time; registering tr()-produced text would poison the English baseline
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            _set_system_param("thread_num", th.value())
            _set_system_param("operator_timeout", to.value())
            _set_system_param("max_graphics_windows", mw.value())
            win._set_display_mode(dmode.currentText())
            sset.setValue("display/default_mode", dmode.currentText())
            set_draw_style(mode=drawm.currentText(), line_width=drawlw.value())
            sset.setValue("draw/mode", drawm.currentText())
            sset.setValue("draw/line_width", drawlw.value())
            _apply_mono_font(fpt.value())
            ip = interp.text().strip()
            if ip and not os.path.isfile(ip):
                report_error("Python Editor interpreter",
                             "not a file (kept previous): %s" % ip)
            else:
                sset.setValue("pyedit/interpreter", ip)
            flash("settings applied (threads %d · timeout %d ms · windows ≤%d · font %dpt)"
                  % (th.value(), to.value(), mw.value(), fpt.value()))
    win._open_system_settings = open_system_settings

    def _latest_evis_perception():
        """Newest evis Fullseye-perception GIF (<module>/out/evis_fullseye*.gif), or None."""
        import glob
        base = os.path.dirname(os.path.abspath(__file__))     # cwd-independent, like every asset
        cands = glob.glob(os.path.join(base, "out", "evis_fullseye*.gif"))
        try:
            cands.sort(key=os.path.getmtime)
        except OSError:                                       # a file vanished mid-sort
            cands = [c for c in cands if os.path.exists(c)]
            cands.sort(key=os.path.getmtime)
        return cands[-1] if cands else None

    def open_physical_ai_viewer():
        """Play the GPU-learned evis walk as Fullseye perceives it (RGB | depth | DVS events).
        The control policy is trained on the GPU (MJX-PPO torque twin); Fullseye supplies the
        vision. Non-modal; shows a hint if no perception GIF has been generated yet."""
        gif = _latest_evis_perception()
        prev = getattr(win, "_physical_ai_dialog", None)
        if prev is not None:
            try:
                prev.close(); prev.deleteLater()             # one live viewer at a time
            except RuntimeError:
                pass                                          # already deleted by Qt
        dlg = QtWidgets.QDialog(win)
        dlg.setAttribute(QtCore.Qt.WA_DeleteOnClose)          # closing frees dialog + movie
        dlg.setWindowTitle("Physical AI — evis RL walk, perceived by Fullseye")
        tag_dialog(dlg, "viewer", backend="MuJoCo offscreen render")
        lay = QtWidgets.QVBoxLayout(dlg)
        cap = QtWidgets.QLabel("GPU-learned evis (MJX-PPO torque policy) → Fullseye vision: "
                               "RGB · depth · DVS events")
        cap.setWordWrap(True); cap.setProperty("hint", True); lay.addWidget(cap)
        view = QtWidgets.QLabel(); view.setAlignment(QtCore.Qt.AlignCenter)
        view.setMinimumSize(880, 320); lay.addWidget(view)
        if gif and os.path.exists(gif):
            mv = QtGui.QMovie(gif)
            view.setMovie(mv); mv.start()
            dlg._movie = mv                     # keep a reference so the animation is not GC'd
            dlg.finished.connect(mv.stop)       # a closed viewer must stop decoding frames
            cap.setText(cap.text() + f"   —   {os.path.basename(gif)}")
        else:
            view.setText("知覚 GIF は未生成です。\n学習チェックポイントから "
                         "fullseye3d.evis_rl_perceive(qpos_npy) を実行すると生成されます。")
        win._physical_ai_dialog = dlg            # for headless tests
        dlg.resize(920, 430)
        dlg.show()                               # non-modal so Studio stays usable
        return dlg
    win._open_physical_ai_viewer = open_physical_ai_viewer
    win._latest_evis_perception = _latest_evis_perception

    # restore persisted system settings. QSettings is NOT in-memory under offscreen —
    # it always hits the real user store; the test suite redirects QSettings to a
    # temporary INI (conftest fixture) so tests stay hermetic.
    _s_sys = QtCore.QSettings("Fullseye", "Studio"); _s_sys.beginGroup("system")
    _sv_to, _sv_th = _s_sys.value("operator_timeout_ms"), _s_sys.value("threads")
    _sv_mw = _s_sys.value("max_graphics_windows")
    _s_sys.endGroup()
    if _sv_to is not None:
        try:
            state["system"]["operator_timeout_ms"] = int(_sv_to)
        except (TypeError, ValueError):
            pass
    if _sv_th is not None:
        try:
            _set_system_param("thread_num", int(_sv_th))
        except (TypeError, ValueError):
            pass
    if _sv_mw is not None:
        try:
            state["system"]["max_graphics_windows"] = max(1, int(_sv_mw))
        except (TypeError, ValueError):
            pass
    # restore the display / draw preferences chosen in System settings
    _s_pref = QtCore.QSettings("Fullseye", "Studio")
    _pv_mode = _s_pref.value("display/default_mode")
    if _pv_mode and str(_pv_mode) in win._display_actions:
        win._set_display_mode(str(_pv_mode))
    _pv_draw = _s_pref.value("draw/mode")
    if _pv_draw in ("fill", "margin"):
        set_draw_style(mode=str(_pv_draw))
    _pv_lw = _s_pref.value("draw/line_width")
    if _pv_lw is not None:
        try:
            set_draw_style(line_width=max(1, min(int(_pv_lw), 9)))
        except (TypeError, ValueError):
            pass

    def load_frame_b():
        path, _ = QtWidgets.QFileDialog.getOpenFileName(win, "Open frame B", "",
                                                        "Images (*.png *.jpg *.bmp *.tif)")
        if not path:
            return
        try:
            arr = imgio.load(path)
        except Exception as e:
            report_error("Could not open frame B", "%s\n\n%s" % (path, e)); return
        pmodel.set_frame_b(arr)
        flash("frame B loaded: " + os.path.basename(path))

    def run_perception():
        """Run a two-frame perception mode. A failure now lands in the Problems
        panel and the Inspector as well — a 6-second status-bar flash was far too
        easy to miss, leaving the user with a stale image and no explanation."""
        mode = percep_mode.currentText()
        try:
            rgb = pmodel.view(mode, model.image)
        except Exception as e:                                # missing/mismatched frame B, etc.
            state["perception_error"] = (mode, str(e))
            inspector.setPlainText("perception failed (%s):\n\n%s" % (mode, e))
            flash("perception: " + truncate(e, 120))
            refresh_problems(None)
            return
        state["perception_error"] = None
        qi = _to_qimage(rgb, QtGui)
        if qi is not None:
            view.set_pixmap(QtGui.QPixmap.fromImage(qi)); view.fit()
        view.set_data(rgb)
        state["result"] = rgb; state["raw"] = rgb
        inspector.setPlainText("perception: %s  ->  RGB %s" % (mode, rgb.shape))
        refresh_problems(None)
        update_actions()
    b_loadb.clicked.connect(load_frame_b); b_percep.clicked.connect(run_perception)

    def save_pipe():
        import json
        path, _ = QtWidgets.QFileDialog.getSaveFileName(win, "Save pipeline", "pipeline.json",
                                                        "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:     # permission / bad path / full disk
                fh.write(json.dumps(model.to_dict(), indent=2))
        except Exception as e:
            report_error("Could not save pipeline", "%s\n\n%s" % (path, e)); return
        state["dirty"] = False                                # now matches a file on disk
        state["pipe_path"] = os.path.abspath(path)
        _push_recent(path); _set_title()
        flash("saved " + os.path.basename(path))

    def _open_pipe_path(path):
        import json
        if not confirm_discard("Open pipeline"):
            return
        try:
            with open(path, encoding="utf-8") as fh:          # missing / permission
                data = json.loads(fh.read())                  # malformed JSON
            snap = [list(st) for st in model.stages]
            model.load_dict(data)                             # schema + op-name validation
            win._undo_stack.append(snap)                      # fork history only on success
            if len(win._undo_stack) > _UNDO_CAP:
                del win._undo_stack[0]
            win._redo_stack.clear(); _sync_undo_actions()
        except Exception as e:
            # load_dict validates into a temporary list before assigning, so the
            # pipeline currently on screen survives a bad file untouched.
            report_error("Could not open pipeline", "%s\n\n%s" % (path, e)); return
        state["pipe_path"] = os.path.abspath(path)
        state["dirty"] = False                            # freshly loaded == matches the file
        refresh_stage_list(select=len(model.stages) - 1); show_result()
        _push_recent(path); _set_title()
        flash("loaded " + os.path.basename(path))

    def open_pipe():
        path, _ = QtWidgets.QFileDialog.getOpenFileName(win, "Open pipeline", "", "JSON (*.json)")
        if path:
            _open_pipe_path(path)

    # drag-and-drop dispatcher: image file -> base frame, .json -> pipeline.
    _DROP_IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

    def _handle_drop(paths):
        f = paths[0]
        ext = os.path.splitext(f)[1].lower()
        if ext in _DROP_IMG_EXTS:
            _load_image_path(f)
        elif ext == ".json":
            _open_pipe_path(f)
        else:
            flash("drop: unsupported file '%s' — drop an image or a .json pipeline"
                  % os.path.basename(f))
    win.drop_handler = _handle_drop

    # -- recent files (QSettings-backed): File > Open Recent ------------------- #
    _RECENT_KEY = "recent_files"
    _RECENT_MAX = 10

    def _recent_paths():
        v = QtCore.QSettings("Fullseye", "Studio").value(_RECENT_KEY, [])
        return [x for x in (v or []) if isinstance(x, str)]

    def _save_recent(paths):
        QtCore.QSettings("Fullseye", "Studio").setValue(_RECENT_KEY, paths[:_RECENT_MAX])
        _rebuild_recent_menu()

    def _push_recent(path):
        ap = os.path.abspath(path)
        keep = [x for x in _recent_paths() if os.path.normcase(x) != os.path.normcase(ap)]
        _save_recent([ap] + keep)

    def _open_recent(path):
        if not os.path.exists(path):
            flash("recent file no longer exists: " + os.path.basename(path))
            _save_recent([x for x in _recent_paths()
                          if os.path.normcase(x) != os.path.normcase(os.path.abspath(path))])
            return
        _handle_drop([path])

    def _rebuild_recent_menu():
        menu = getattr(win, "_recent_menu", None)
        if menu is None:
            return
        menu.clear()
        paths = _recent_paths()
        if not paths:
            a = menu.addAction("(no recent files)"); a.setEnabled(False); return
        for pth in paths:
            a = menu.addAction(os.path.basename(pth)); a.setToolTip(pth)
            a.triggered.connect(lambda _=False, x=pth: _open_recent(x))
        menu.addSeparator()
        menu.addAction("Clear recent").triggered.connect(lambda: _save_recent([]))
    win._rebuild_recent_menu = _rebuild_recent_menu

    b_savep.clicked.connect(save_pipe); b_openp.clicked.connect(open_pipe)
    act_save_pipe.triggered.connect(save_pipe); act_open_pipe.triggered.connect(open_pipe)

    def on_hover(x, y, v):
        if np.ndim(v) == 0:
            readout.setText(f"x={x}  y={y}   value={float(v):.4f}")
        else:
            readout.setText(f"x={x}  y={y}   RGB=({float(v[0]):.3f},{float(v[1]):.3f},{float(v[2]):.3f})")
    view.hover_cb = on_hover

    # ---- keyboard-shortcut scoping ----------------------------------------- #
    # These edit/step keys used to be WindowShortcut: Ctrl+Up / Ctrl+Down fired
    # while the user was typing in the operator search box (QLineEdit only claims
    # Del / Home / Ctrl+Right for itself), and Home hijacked "go to first row" in
    # the operator list. Binding them to the pipeline list with
    # WidgetWithChildrenShortcut keeps the *menu items*, the toolbar and the
    # buttons working exactly as before — only the bare key press is now scoped.
    for _a in (act_remove, act_dup, act_up, act_down, act_top, act_bottom, act_step, act_reset):
        _a.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        stage_list.addAction(_a)

    # ---- accessibility ------------------------------------------------------ #
    la.setBuddy(sa); lb.setBuddy(sb)
    for _w, _n in ((sa, "knob a (0 to 1)"), (sb, "knob b (0 to 1)"),
                   (stage_list, "pipeline stages"), (op_list, "operator list"),
                   (search, "search operators"), (cat, "operator category filter"),
                   (samples, "sample pipelines"), (display, "display colour map"),
                   (percep_mode, "perception mode"), (problems_list, "pipeline problems"),
                   (inspector, "inspector"), (hist_view, "histogram"),
                   (view, "image view"), (readout, "pixel read-out"),
                   (b_rm, "remove stage"), (b_up, "move stage up"), (b_dn, "move stage down"),
                   (b_reset, "reset to raw image"), (b_step, "step forward"),
                   (b_runall, "run all stages"), (b_export, "export pipeline"),
                   (b_savep, "save pipeline"), (b_openp, "open pipeline"),
                   (b_load, "load image"), (b_demo, "synthetic demo"),
                   (b_save, "save result"), (b_3d, "3D surface"),
                   (b_loadb, "load frame B"), (b_percep, "run perception"),
                   (b_zin, "zoom in"), (b_zout, "zoom out"),
                   (b_fit, "fit to window"), (b_11, "actual size")):
        _w.setAccessibleName(_n)
        if not _w.toolTip():
            _w.setToolTip(_n)

    win.close_guard = lambda: confirm_discard("Quit Fullseye Studio")
    win._perception = {"model": pmodel, "mode": percep_mode, "run": run_perception}
    win._flash = flash
    win._state = state                                   # for tests / headless driving
    win._knob_sliders = (sa, sb)
    win._knob_timer = knob_timer
    win._stage_list = stage_list
    win._problems_list = problems_list
    win._inspector = inspector
    win._update_actions = update_actions
    win._confirm_discard = confirm_discard
    win._buttons = {"remove": b_rm, "up": b_up, "down": b_dn, "save_result": b_save,
                    "export": b_export, "surface_3d": b_3d, "step": b_step,
                    "run_all": b_runall, "reset": b_reset, "save_pipeline": b_savep}
    win._actions = {
        "open_image": act_open_img, "demo": act_demo, "save_result": act_save_res,
        "copy_result": act_copy_res,
        "open_pipeline": act_open_pipe, "save_pipeline": act_save_pipe, "export": act_export,
        "quit": act_quit, "remove": act_remove, "move_up": act_up, "move_down": act_down,
        "clear": act_clear, "undo": act_undo, "redo": act_redo,
        "zoom_in": act_zin, "zoom_out": act_zout, "fit": act_fit,
        "actual_size": act_11, "surface_3d": act_3d, "reset": act_reset, "step": act_step,
        "run_all": act_runall, "holdout": act_holdout, "palette": act_palette, "shortcuts": act_shortcuts,
        "feature_inspection": act_featins, "viewer_3d": act_viewer3d,
        "op_reference": act_op_help, "samples": act_samples, "about": act_about,
        "dbg_run": act_dbg_run, "dbg_step": act_dbg_step, "dbg_reset": act_dbg_reset,
        "duplicate_stage": act_dup, "move_top": act_top, "move_bottom": act_bottom,
        "focus_search": act_focus_search,
    }
    win.addAction(act_focus_search)          # app-wide Ctrl+F -> operator search
    # -- multi-monitor: pop every tool panel out as its own top-level window --- #
    def float_all_panels(floating=True):
        for d in win._docks.values():
            d.setFloating(floating)
        if win._flash:
            win._flash("panels floated for multi-display" if floating else "panels re-docked")
    act_float_all = _act("Float all panels (multi-display)", None,
                         "Detach every tool panel to its own window — move them across monitors")
    act_dock_all = _act("Dock all panels", None, "Re-dock every floated tool panel")
    menu_panels.addAction(act_float_all); menu_panels.addAction(act_dock_all)
    act_float_all.triggered.connect(lambda: float_all_panels(True))
    act_dock_all.triggered.connect(lambda: float_all_panels(False))
    win._float_all_panels = float_all_panels

    # -- per-panel float control (finer than all-or-nothing float) ------------ #
    def float_panel(name, floating=True):
        """Float (or re-dock) a single tool panel — cross-monitor freedom without
        detaching every panel at once."""
        d = win._docks.get(name)
        if d is None:
            return False
        d.setFloating(bool(floating))
        if floating:
            d.show()
        return True
    win._float_panel = float_panel

    # -- graphics windows: detach out of the MDI workspace into standalone ----- #
    win._detached_graphics = []

    def detach_graphics(sub=None):
        """Pop a graphics window out of the MDI workspace into an independent
        top-level window (HDevelop-style). The image view keeps rendering; it just
        lives outside the workspace now. Returns the new top-level window."""
        try:
            sub = sub or mdi.activeSubWindow()
            if sub is None:                        # offscreen has no 'active' one
                live = [s for s in win._graphics_windows if s in mdi.subWindowList()]
                sub = live[-1] if live else None
            if sub is None:
                win._flash and win._flash("no graphics window to detach")
                return None
            inner = sub.widget()
            if inner is not None and inner.objectName() == "graphics_primary":
                # The primary window hosts the resident image view AND the global
                # Load / Demo / Save / Zoom controls. Detaching it (and later
                # closing the detached top-level) would destroy those controls and
                # leave update_actions poking at freed QPushButtons. It is the
                # HDevelop-style resident "current" window — keep it in the workspace.
                win._flash and win._flash("the primary graphics window stays in the workspace")
                return None
            title = sub.windowTitle()
            mdi.removeSubWindow(sub)                # reparents inner to no parent
            if sub in win._graphics_windows:
                win._graphics_windows.remove(sub)
            sub.deleteLater()
            top = QtWidgets.QMainWindow(win)
            top.setWindowFlag(QtCore.Qt.Window, True)
            top.setWindowTitle((title or "Graphics") + " — detached")
            top.setStyleSheet(THEME)
            if os.path.exists(_ICON_PATH):
                top.setWindowIcon(QtGui.QIcon(_ICON_PATH))
            if inner is not None:
                top.setCentralWidget(inner)
            top.resize(480, 400)
            top.show()
            win._detached_graphics.append(top)
            win._flash and win._flash("detached %s from the workspace" % (title or "graphics"))
            return top
        except Exception as e:                     # never let a window op crash the app
            report_error("Detach graphics", e)
            return None
    win._detach_graphics = detach_graphics

    def reattach_graphics(top=None):
        """Return a detached graphics window to the MDI workspace."""
        try:
            top = top or (win._detached_graphics[-1] if win._detached_graphics else None)
            if top is None:
                win._flash and win._flash("no detached graphics window to reattach")
                return None
            inner = top.takeCentralWidget()
            title = top.windowTitle().replace(" — detached", "")
            if top in win._detached_graphics:
                win._detached_graphics.remove(top)
            top.close(); top.deleteLater()
            if inner is None:
                return None
            sub = mdi.addSubWindow(inner)
            win._gfx_handle_seq += 1
            sub._fs_handle = win._gfx_handle_seq        # a reattached window gets a fresh handle
            sub.setWindowTitle(title or ("Graphics %d" % sub._fs_handle))
            sub.resize(440, 360); sub.show()
            win._graphics_windows.append(sub)
            win._flash and win._flash("reattached %s to the workspace" % (title or "graphics"))
            return sub
        except Exception as e:
            report_error("Reattach graphics", e)
            return None
    win._reattach_graphics = reattach_graphics

    # -- named layout presets (save / apply / delete) + built-in arrangements -- #
    win._preset_store = {}          # name -> (geometry: QByteArray, state: QByteArray)

    def _persist_presets():
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return                                 # tests keep presets in-memory only
        try:
            s = QtCore.QSettings("Fullseye", "Studio")
            s.beginGroup("layout_presets"); s.remove("")
            for nm, (geo, st) in win._preset_store.items():
                s.beginGroup(nm)
                s.setValue("geometry", geo); s.setValue("state", st)
                s.endGroup()
            s.endGroup()
        except Exception:
            pass

    def save_layout_preset(name):
        """Capture the current window geometry + full dock/toolbar arrangement under
        *name* (persisted via QSettings unless offscreen). Overwrites a same-named one."""
        name = (name or "").strip()
        if not name:
            return False
        win._preset_store[name] = (win.saveGeometry(), win.saveState())
        _persist_presets(); win._rebuild_layouts_menu()
        win._flash and win._flash("saved layout '%s'" % name)
        return True
    win._save_layout_preset = save_layout_preset

    def apply_layout_preset(name):
        item = win._preset_store.get(name)
        if item is None:
            return False
        geo, st = item
        try:
            if geo is not None:
                win.restoreGeometry(geo)
            if st is not None:
                win.restoreState(st)
        except Exception as e:
            report_error("Apply layout", e); return False
        win._flash and win._flash("applied layout '%s'" % name)
        return True
    win._apply_layout_preset = apply_layout_preset

    def delete_layout_preset(name):
        if name in win._preset_store:
            del win._preset_store[name]
            _persist_presets(); win._rebuild_layouts_menu()
            win._flash and win._flash("deleted layout '%s'" % name)
            return True
        return False
    win._delete_layout_preset = delete_layout_preset

    # built-in deterministic arrangements (no saved state needed)
    def layout_balanced():
        win._reset_layout()                        # restore factory state + show all docks
        win._flash and win._flash("layout: balanced (default)")

    def layout_graphics_focus():
        for k in ("operators", "display", "program", "variables"):
            win._docks[k].hide()
        win._docks["pipeline"].show()
        try:
            subs = [s for s in win._graphics_windows if s in mdi.subWindowList()]
            target = mdi.activeSubWindow() or (subs[-1] if subs else None)
            target and target.showMaximized()
        except Exception:
            pass
        win._flash and win._flash("layout: graphics focus")

    def layout_code_focus():
        for k in ("operators", "display"):
            win._docks[k].hide()
        for k in ("pipeline", "program", "variables"):
            win._docks[k].show()
        win._docks["program"].raise_()
        win._flash and win._flash("layout: code focus")

    win._builtin_layouts = {"Balanced (default)": layout_balanced,
                            "Graphics focus": layout_graphics_focus,
                            "Code focus": layout_code_focus}
    win._apply_builtin_layout = lambda nm: (win._builtin_layouts.get(nm) or (lambda: None))()

    layouts_menu = _menu(menu_windows, "Layout", "layout")

    def _prompt_save_layout():
        try:
            name, ok = QtWidgets.QInputDialog.getText(win, "Save layout", "Layout name:")
            if ok and str(name).strip():
                save_layout_preset(str(name).strip())
        except Exception:
            pass

    def _rebuild_layouts_menu():
        # Flat actions only (no nested QMenu): a submenu returned by addMenu(str)
        # has no Python owner and shiboken deletes it once the local ref drops —
        # flat actions are owned by layouts_menu and survive clear()/rebuild.
        layouts_menu.clear()
        for nm, fn in win._builtin_layouts.items():
            layouts_menu.addAction(nm).triggered.connect(lambda _=False, f=fn: f())
        layouts_menu.addSeparator()
        layouts_menu.addAction("Save current layout as…").triggered.connect(_prompt_save_layout)
        if win._preset_store:
            layouts_menu.addSeparator()
            for nm in sorted(win._preset_store):
                layouts_menu.addAction("Apply layout: %s" % nm).triggered.connect(
                    lambda _=False, n=nm: apply_layout_preset(n))
            for nm in sorted(win._preset_store):
                layouts_menu.addAction("Delete layout: %s" % nm).triggered.connect(
                    lambda _=False, n=nm: delete_layout_preset(n))
    win._rebuild_layouts_menu = _rebuild_layouts_menu
    win._layouts_menu = layouts_menu

    # per-panel float as flat items in Panels (avoids a 3rd nesting level) + reset
    menu_panels.addSeparator()
    for _k, _lbl in (("operators", "Operators"), ("pipeline", "Pipeline · Parameters"),
                     ("display", "Display · Analysis"), ("program", "Program (code)"),
                     ("variables", "Variables & Objects")):
        menu_panels.addAction("Float: %s" % _lbl).triggered.connect(
            lambda _=False, k=_k: float_panel(k, True))
    menu_panels.addSeparator()
    menu_panels.addAction(act_reset_layout)
    # graphics detach/reattach live under the Graphics windows submenu
    act_detach = _act("Detach graphics window", "Ctrl+Shift+D",
                      "Pop the active graphics window out of the workspace into its own window")
    act_reattach = _act("Reattach graphics window", None,
                        "Return a detached graphics window to the workspace")
    menu_graphics.addAction(act_detach); menu_graphics.addAction(act_reattach)
    act_detach.triggered.connect(lambda: detach_graphics())
    act_reattach.triggered.connect(lambda: reattach_graphics())
    win._actions["detach_graphics"] = act_detach
    win._actions["reattach_graphics"] = act_reattach

    # load persisted presets, then build the Layouts menu
    try:
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            s = QtCore.QSettings("Fullseye", "Studio"); s.beginGroup("layout_presets")
            for nm in s.childGroups():
                s.beginGroup(nm); geo = s.value("geometry"); st = s.value("state"); s.endGroup()
                if geo is not None or st is not None:
                    win._preset_store[nm] = (geo, st)
            s.endGroup()
    except Exception:
        pass
    _rebuild_layouts_menu()
    _rebuild_recent_menu()
    _set_title()

    # -- tooltip / label / message localisation (en / ja / zh) ---------------- #
    # Same pattern for both: snapshot the ENGLISH baseline after construction, then
    # swap through the i18n.json tables on language switch. Labels use the 'strings'
    # table (user spec 2026-08-30: 対訳はテーブルで一箇所に). Lazily-built dialogs
    # register their subtree via win._localize(root).
    win._tt_en = {w: w.toolTip() for w in win.findChildren(QtWidgets.QWidget) if w.toolTip()}
    win._label_en = {}
    win._lang = "en"
    _UI_LANG["code"] = "en"                    # a fresh window starts from the base language
    win._lang_actions = {}

    def _collect_labels(root):
        """(obj -> (setter-kind, english-text)) for the translatable chrome under
        *root*: actions, menus, buttons, group boxes and STATIC labels. Dynamic
        status labels (property hint/muted) are excluded so a language switch never
        clobbers a live status message."""
        out = {}
        for a in root.findChildren(QtGui.QAction):
            if a.text():
                out[a] = ("text", a.text())
        for w in root.findChildren(QtWidgets.QMenu):
            if w.title():
                out[w] = ("title", w.title())
        for w in root.findChildren(QtWidgets.QGroupBox):
            if w.title():
                out[w] = ("title", w.title())
        for w in root.findChildren(QtWidgets.QPushButton):
            if w.text():
                out[w] = ("text", w.text())
        for w in root.findChildren(QtWidgets.QToolButton):
            if w.text():
                out[w] = ("text", w.text())
        for w in root.findChildren(QtWidgets.QLabel):
            if w.text() and not w.property("hint") and not w.property("muted") \
                    and "<" not in w.text():          # skip rich-text / dynamic labels
                out[w] = ("text", w.text())
        return out
    win._label_en.update(_collect_labels(win))

    def _apply_labels(objs=None):
        for obj, (kind, en) in list((objs or win._label_en).items()):
            try:
                txt = en if win._lang == "en" else STRINGS_I18N.get(en, {}).get(win._lang, en)
                (obj.setTitle if kind == "title" else obj.setText)(txt)
            except Exception:
                pass                                   # a deleted widget is skipped

    def _apply_tooltips(items=None):
        for w, en in list((items or win._tt_en).items()):
            try:
                w.setToolTip(en if win._lang == "en"
                             else TOOLTIPS_I18N.get(en, {}).get(win._lang, en))
            except Exception:
                pass

    def localize(root):
        """Register a lazily-built dialog/window subtree for localisation and apply
        the current language to it immediately (English snapshot = first sight)."""
        tips = {w: w.toolTip() for w in root.findChildren(QtWidgets.QWidget)
                if w.toolTip() and w not in win._tt_en}
        labels = {o: v for o, v in _collect_labels(root).items() if o not in win._label_en}
        win._tt_en.update(tips)
        win._label_en.update(labels)
        _apply_tooltips(tips)
        _apply_labels(labels)
        return root
    win._localize = localize

    def apply_language(lang):
        win._lang = lang if lang in ("en", "ja", "zh") else "en"
        _UI_LANG["code"] = win._lang
        _apply_tooltips()
        _apply_labels()
        for code, a in win._lang_actions.items():
            a.setChecked(code == win._lang)
        try:
            if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
                QtCore.QSettings("Fullseye", "Studio").setValue("lang", win._lang)
        except Exception:
            pass
    win._apply_language = apply_language

    # Data-driven from studio_assets/i18n.json 'languages' — add a language there,
    # no code change. English is always present as the base.
    _lang_group = QtGui.QActionGroup(win); _lang_group.setExclusive(True)
    for _code, _label in LANGUAGES.items():
        _a = QtGui.QAction(_label, win); _a.setCheckable(True); _lang_group.addAction(_a)
        lang_menu.addAction(_a); win._lang_actions[_code] = _a
        _a.triggered.connect(lambda _checked=False, c=_code: apply_language(c))
    win._lang_actions.get("en") and win._lang_actions["en"].setChecked(True)

    def show_guide():
        try:
            QtWidgets.QMessageBox.information(win, "Fullseye Studio — guide",
                                             HELP_I18N.get(win._lang, HELP_I18N["en"]))
        except Exception:
            pass
    act_guide.triggered.connect(show_guide)
    win._show_guide = show_guide

    try:                                     # restore the remembered language
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            _lang = QtCore.QSettings("Fullseye", "Studio").value("lang")
            if _lang in ("en", "ja", "zh"):
                apply_language(_lang)
    except Exception:
        pass

    # Default (factory) panel layout — captured before any saved layout is applied,
    # so "Reset panel layout" always has somewhere to go back to.
    win._default_state = win.saveState()
    try:                                     # restore the user's remembered geometry + layout
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            s = QtCore.QSettings("Fullseye", "Studio")
            geo = s.value("geometry")
            # Only reuse a saved dock layout from the SAME layout version. The current
            # default (v3: image-dominant central, Program tall on the right, op/var
            # panels compact) differs from older saves, so a stale windowState is
            # ignored and the new default shows.
            st = s.value("windowState") if str(s.value("layout_version")) == "3" else None
            if geo:
                win.restoreGeometry(geo)
            if st:
                win.restoreState(st)
    except Exception:
        pass
    try:
        gsub.showMaximized()                 # the primary graphics window fills the workspace
    except Exception:
        pass

    # -- compact icon buttons (the user asked for icons, not words) ----------- #
    # Give every push-button a themed icon (icon + short label) so the toolbars read
    # as an IDE, not a wall of text. Icons come from the Qt style (no asset files).
    _sty = win.style(); _SP = QtWidgets.QStyle
    _icon_for = [
        ("open image", _SP.SP_DialogOpenButton), ("open pipeline", _SP.SP_DialogOpenButton),
        ("load frame", _SP.SP_DialogOpenButton), ("load image", _SP.SP_DialogOpenButton),
        ("save result", _SP.SP_DialogSaveButton), ("save pipeline", _SP.SP_DialogSaveButton),
        ("synthetic demo", _SP.SP_FileDialogContentsView), ("demo", _SP.SP_FileDialogContentsView),
        ("run all", _SP.SP_MediaPlay), ("run (timed)", _SP.SP_MediaPlay), ("run once", _SP.SP_MediaPlay),
        ("run", _SP.SP_MediaPlay), ("step", _SP.SP_MediaSeekForward), ("reset", _SP.SP_MediaSkipBackward),
        ("↑ up", _SP.SP_ArrowUp), ("↓ down", _SP.SP_ArrowDown), ("remove", _SP.SP_TrashIcon),
        ("help", _SP.SP_MessageBoxQuestion), ("browse with code", _SP.SP_DirOpenIcon),
        ("export", _SP.SP_FileDialogDetailedView), ("apply", _SP.SP_DialogApplyButton),
        ("sync", _SP.SP_BrowserReload), ("3d surface", _SP.SP_FileDialogInfoView),
        ("insert", _SP.SP_ArrowRight), ("display → new", _SP.SP_FileDialogNewFolder),
        ("display → main", _SP.SP_DesktopIcon), ("zoom +", _SP.SP_ArrowUp),
        ("zoom −", _SP.SP_ArrowDown), ("fit", _SP.SP_BrowserReload),
    ]
    for _b in win.findChildren(QtWidgets.QPushButton):
        _t = _b.text().lower()
        for _kw, _sp in _icon_for:
            if _kw in _t:
                try:
                    _b.setIcon(_sty.standardIcon(_sp))   # icon + keep the label (findable)
                    _b.setCursor(QtCore.Qt.PointingHandCursor)
                except Exception:
                    pass
                break

    refresh_stage_list(); show_result()      # refresh_stage_list syncs the knob panel
    state["dirty"] = False                   # a freshly-built window has nothing to lose
    state["renders"] = 0
    return win, model


def main() -> int:
    import faulthandler
    import traceback
    from PySide6 import QtWidgets
    # Crash log: pythonw has no console, so capture both C++/Qt segfaults (faulthandler)
    # and Python exceptions (excepthook) to studio_crash.log next to this file.
    _log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_crash.log")
    try:
        faulthandler.enable(open(_log, "w", encoding="utf-8"))
    except Exception:
        pass

    def _hook(t, v, tb):
        try:
            with open(_log, "a", encoding="utf-8") as fh:
                traceback.print_exception(t, v, tb, file=fh)
        except Exception:
            pass
        sys.__excepthook__(t, v, tb)
    sys.excepthook = _hook

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win, _ = build_window()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
