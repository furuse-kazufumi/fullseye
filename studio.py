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


def apply_display(val, mode):
    """Map a 2-D result to an RGB image for the chosen display mode: 'gray', any
    false-colour palette name, 'shaded relief', or 'height (color)'. Non-2-D or
    already-color results are returned unchanged. (Headless, testable.)"""
    if not isinstance(val, np.ndarray) or val.ndim != 2:
        return val
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
QDockWidget::title {{ background:#12141b; padding:3px 8px; border-bottom:1px solid #262b38;
    text-transform:uppercase; letter-spacing:1px; }}
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
    a_role, b_role = op_arg_roles(row["name"])
    knobs = ("a: %s\nb: %s" % (a_role or "(op-dependent)", b_role or "(op-dependent)")
             if (a_role or b_role) else "a, b are the two knobs (each 0..1); meaning depends on the op")
    return ("%s\nHALCON alias: %s\ncategory: %s\nsort: %s → %s\n%s"
            % (row["name"], row.get("halcon") or "(none)", row["category"],
               row["in_sort"], row["out_sort"], knobs))


def _op_row(name):
    """Look up an op and return a ``list_ops``-shaped dict, or None."""
    op = api.find_op(name)
    if op is None:
        return None
    return {"name": op.name, "halcon": op.halcon, "category": op.category,
            "in_sort": op.in_sort, "out_sort": op.out_sort}


def sample_code(name):
    """``(ops_string, python_source)`` for a sample recipe — the 'Sample Code' view
    (author-in-Studio, run-anywhere). Returns None for an unknown recipe. Qt-free."""
    st = recipes.stages(name)
    if st is None:
        return None
    eng = engine.FullseyeEngine([(op, a, b) for (op, a, b) in st], name=name)
    return eng.to_ops(), eng.to_python()


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


def show_3d_surface(heightmap, parent=None):
    """Open a rotatable 3-D surface plot of a height/depth image (Q3DSurface).
    Best-effort: returns the container widget, or None if 3-D isn't available."""
    try:
        from PySide6.QtDataVisualization import (Q3DSurface, QSurface3DSeries,
                                                 QSurfaceDataProxy, QSurfaceDataItem)
        from PySide6 import QtGui, QtWidgets
    except Exception:
        return None
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
    surface = Q3DSurface()
    surface.addSeries(series)
    container = QtWidgets.QWidget.createWindowContainer(surface, parent)
    container.setMinimumSize(560, 460)
    container.setWindowTitle("Fullseye Studio - 3D surface")
    container.show()
    return container


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
            self.hover_cb = None                     # set by build_window

        def set_pixmap(self, pm):
            self._item.setPixmap(pm)
            self._scene.setSceneRect(QtCore.QRectF(pm.rect()))

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

        def clear(self):
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
    return ImageView


def _group(QtWidgets, title, inner_layout):
    """A titled section card (QGroupBox) wrapping *inner_layout*."""
    g = QtWidgets.QGroupBox(title)
    g.setLayout(inner_layout)
    return g


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
    return langs, data.get("tooltips", {}) or {}, data.get("guide", {}) or {"en": ""}


LANGUAGES, TOOLTIPS_I18N, HELP_I18N = _load_i18n()


def op_help_html(name, lang="en", meta=None):
    """Rich HTML help for one operator. Lookup order (see studio_assets/op_help/):
      1. op_help/<name>.<lang>.html   language-specific
      2. op_help/<name>.html          default (English)
      3. a generated card from the op's registry metadata (no file needed).
    The HTML may use anchors ``op:<name>`` (jump to a related op) and
    ``sample:<url-encoded ops>`` / ``run:<...>`` (load/run a sample pipeline)."""
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
            except Exception:
                pass
            ev.accept()

    win = StudioWindow()
    win.setWindowTitle("Fullseye Studio")
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
    act_demo = _act("Synthetic demo", "Ctrl+D", "Load the built-in synthetic demo scene")
    act_save_res = _act("Save result…", "Ctrl+S", "Save the displayed result as a PNG")
    act_open_pipe = _act("Open pipeline…", "Ctrl+Shift+O", "Load a pipeline from JSON")
    act_save_pipe = _act("Save pipeline…", "Ctrl+Shift+S", "Save the pipeline to JSON")
    act_export = _act("Export…", "Ctrl+E", "Export as an --ops string and Python code")
    act_quit = _act("Quit", "Ctrl+Q", "Close Fullseye Studio")
    act_remove = _act("Remove stage", "Del", "Remove the selected pipeline stage")
    act_up = _act("Move stage up", "Ctrl+Up", "Move the selected stage earlier")
    act_down = _act("Move stage down", "Ctrl+Down", "Move the selected stage later")
    act_clear = _act("Clear pipeline", "Ctrl+Shift+Backspace", "Remove all stages")
    act_zin = _act("Zoom in", "Ctrl+=", "Zoom the image in")
    act_zout = _act("Zoom out", "Ctrl+-", "Zoom the image out")
    act_fit = _act("Fit to window", "Ctrl+0", "Fit the image to the view")
    act_11 = _act("Actual size (1:1)", "Ctrl+1", "Reset zoom to 1:1")
    act_3d = _act("3D surface", "Ctrl+3", "Open a rotatable 3-D surface of the result")
    act_reset = _act("Reset to start", "Home", "Show the raw image (before stage 1)")
    act_step = _act("Step forward", "Ctrl+Right", "Advance one pipeline stage")
    act_runall = _act("Run all", "Ctrl+Return", "Show the final pipeline result")
    act_palette = _act("Command palette…", "Ctrl+P", "Run any operator or action by name")
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
    m.addSeparator()
    m.addAction(act_save_res)                                 # result out
    m.addSeparator(); m.addAction(act_quit)
    m = _menu(mb, "&Edit", "edit")
    m.addAction(act_remove); m.addAction(act_up); m.addAction(act_down)
    m.addSeparator(); m.addAction(act_clear)
    menu_view = _menu(mb, "&View", "view")
    menu_view.addAction(act_zin); menu_view.addAction(act_zout)
    menu_view.addSeparator(); menu_view.addAction(act_fit); menu_view.addAction(act_11)
    menu_view.addSeparator()          # Display mode submenu + 3D surface appended once the display combo exists
    m = _menu(mb, "&Run", "run")
    m.addAction(act_reset); m.addAction(act_step)
    m.addSeparator(); m.addAction(act_runall)
    menu_windows = _menu(mb, "&Window", "window")   # panels / graphics / layout submenus (filled after docks)
    menu_tools = _menu(mb, "&Tools", "tools")
    menu_tools.addAction(act_palette)                         # cross-cutting command launcher (was under Run)
    menu_tools.addSeparator()
    lang_menu = _menu(menu_tools, "Language / 言語 / 语言", "language")  # UI/help language = a preference, not Help
    m = _menu(mb, "&Help", "help")
    m.addAction(act_op_help); m.addAction(act_samples); m.addSeparator()
    act_guide = _act("Quick guide (en/ja/zh)", "Shift+F2", "A short guide in the selected language")
    m.addAction(act_guide)
    m.addSeparator()
    m.addAction(act_shortcuts); m.addSeparator(); m.addAction(act_about)

    # ---- branded toolbar ---------------------------------------------------- #
    tb = QtWidgets.QToolBar(); tb.setMovable(False); tb.setFloatable(False)
    tb.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
    win.addToolBar(tb)
    if os.path.exists(_ICON_PATH):
        brand = QtWidgets.QLabel()
        brand.setPixmap(QtGui.QIcon(_ICON_PATH).pixmap(22, 22))
        brand.setStyleSheet("padding:0 6px;")
        tb.addWidget(brand)
    title = QtWidgets.QLabel("Fullseye Studio")
    title.setStyleSheet("font-size:15px; font-weight:800; color:%s; padding:0 4px;" % AMBER)
    tb.addWidget(title)
    subtitle = QtWidgets.QLabel("image pipeline workbench")
    subtitle.setProperty("muted", True); subtitle.setStyleSheet("color:%s; padding-top:3px;" % MUTED)
    tb.addWidget(subtitle)
    spacer = QtWidgets.QWidget()
    spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    tb.addWidget(spacer)
    tb.addAction(act_demo); tb.addAction(act_open_img); tb.addAction(act_runall); tb.addAction(act_export)

    # Central document area = an MDI workspace of graphics windows (HDevelop-style:
    # multiple image/result windows the user can open, tile, cascade and float).
    mdi = QtWidgets.QMdiArea()
    mdi.setViewMode(QtWidgets.QMdiArea.SubWindowView)
    mdi.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    mdi.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    win.setCentralWidget(mdi)
    win.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks
                       | QtWidgets.QMainWindow.AllowTabbedDocks
                       | QtWidgets.QMainWindow.AnimatedDocks)
    win.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtWidgets.QTabWidget.North)
    win._mdi = mdi
    win._graphics_windows = []

    status = win.statusBar()
    readout = QtWidgets.QLabel("hover over the image for pixel coordinates + value")
    readout.setProperty("hint", True)
    status.addWidget(readout)

    def flash(msg):
        status.showMessage(msg, 6000)

    # -- left: operator browser + samples ------------------------------------ #
    left = QtWidgets.QWidget(); lv = QtWidgets.QVBoxLayout(left); lv.setSpacing(6)
    lv.setContentsMargins(6, 6, 6, 6)
    samples = QtWidgets.QComboBox(); samples.addItem("— load a sample —")
    for nm in recipes.names():
        samples.addItem(nm)
    samples.setToolTip("Replace the pipeline with a ready-made sample recipe")
    slay = QtWidgets.QVBoxLayout(); slay.addWidget(samples)
    lv.addWidget(_group(QtWidgets, "SAMPLE PIPELINES", slay))

    all_ops = api.list_ops()
    cat = QtWidgets.QComboBox(); cat.addItem("all categories")
    cat.addItems(sorted({r["category"] for r in all_ops}))
    cat.setToolTip("Filter operators by category")
    search = QtWidgets.QLineEdit(); search.setPlaceholderText("search operators…")
    search.setClearButtonEnabled(True)
    search.setToolTip("Filter by op name, HALCON alias or category")
    op_list = QtWidgets.QListWidget()
    op_list.setToolTip("Double-click an operator to insert it into the pipeline")
    op_hint = QtWidgets.QLabel("double-click / Enter to insert  ·  hover for details")
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
    b_insert = QtWidgets.QPushButton("Insert ▸")
    b_insert.setToolTip("Add the operator to the pipeline with the a, b below (Enter / double-click)")
    b_insert.setEnabled(False)
    b_run_once = QtWidgets.QPushButton("Run once ▷")
    b_run_once.setToolTip("Apply this operator ONCE with a, b to the loaded image and show the result in "
                          "a graphics window — the pipeline is NOT changed (HDevelop single-step execution)")
    b_run_once.setEnabled(False)
    b_help = QtWidgets.QPushButton("Help…")
    b_help.setToolTip("Show the selected operator's HTML help (image-processing details)")
    b_help.setEnabled(False)
    olay = QtWidgets.QVBoxLayout()
    olay.addWidget(cat); olay.addWidget(search); olay.addWidget(op_list, 1)
    olay.addWidget(op_param)
    argrow = QtWidgets.QHBoxLayout()
    argrow.addWidget(QtWidgets.QLabel("a")); argrow.addWidget(op_a_spin, 1)
    argrow.addWidget(QtWidgets.QLabel("b")); argrow.addWidget(op_b_spin, 1)
    olay.addLayout(argrow)
    oprow = QtWidgets.QHBoxLayout()
    oprow.addWidget(b_insert, 1); oprow.addWidget(b_run_once); oprow.addWidget(b_help)
    olay.addLayout(oprow); olay.addWidget(op_hint)
    lv.addWidget(_group(QtWidgets, "OPERATORS", olay), 1)

    def refill_ops():
        kw = search.text().lower(); c = cat.currentText()
        op_list.clear()
        for r in all_ops:
            if c != "all categories" and r["category"] != c:
                continue
            hay = (r["name"] + " " + (r["halcon"] or "") + " " + r["category"]).lower()
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
    b_rm = QtWidgets.QPushButton("Remove"); b_up = QtWidgets.QPushButton("↑ Up"); b_dn = QtWidgets.QPushButton("↓ Down")
    b_rm.setToolTip("Remove the selected stage (Del)")
    b_up.setToolTip("Move the selected stage earlier (Ctrl+Up)")
    b_dn.setToolTip("Move the selected stage later (Ctrl+Down)")
    b_reset = QtWidgets.QPushButton("⏮ Reset"); b_step = QtWidgets.QPushButton("Step ▶")
    b_runall = QtWidgets.QPushButton("Run all ▶▶"); b_runall.setProperty("accent", True)
    b_reset.setToolTip("Show the raw image (Home)")
    b_step.setToolTip("Advance one stage (Ctrl+Right)")
    b_runall.setToolTip("Show the final result (Ctrl+Enter)")
    problems_list = QtWidgets.QListWidget()
    problems_list.setFixedHeight(74)
    problems_list.setToolTip("Pipeline problems (unknown op / sort mismatch / runtime error).\n"
                             "Double-click to jump to the offending stage.")
    play = QtWidgets.QVBoxLayout(); play.addWidget(stage_list, 1)
    erow = QtWidgets.QHBoxLayout(); erow.addWidget(b_rm); erow.addWidget(b_up); erow.addWidget(b_dn)
    srow = QtWidgets.QHBoxLayout(); srow.addWidget(b_reset); srow.addWidget(b_step); srow.addWidget(b_runall)
    play.addLayout(erow); play.addLayout(srow)
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
    klay = QtWidgets.QVBoxLayout()
    klay.addWidget(stage_detail); klay.addWidget(la); klay.addWidget(sa)
    klay.addWidget(lb); klay.addWidget(sb)
    mv.addWidget(_group(QtWidgets, "SELECTED STAGE · KNOBS", klay))

    b_export = QtWidgets.QPushButton("Export (ops string + Python)…")
    b_savep = QtWidgets.QPushButton("Save pipeline…"); b_openp = QtWidgets.QPushButton("Open pipeline…")
    b_export.setToolTip("Copy this pipeline as an --ops string and Python (Ctrl+E)")
    xlay = QtWidgets.QVBoxLayout(); xlay.addWidget(b_export)
    xrow = QtWidgets.QHBoxLayout(); xrow.addWidget(b_savep); xrow.addWidget(b_openp)
    xlay.addLayout(xrow)
    mv.addWidget(_group(QtWidgets, "EXPORT & I/O", xlay))

    # -- right: image view + display + perception + analysis ------------------ #
    right = QtWidgets.QWidget(); rv = QtWidgets.QVBoxLayout(right); rv.setSpacing(6)
    rv.setContentsMargins(6, 6, 6, 6)
    b_load = QtWidgets.QPushButton("Load image…"); b_demo = QtWidgets.QPushButton("Synthetic demo")
    b_save = QtWidgets.QPushButton("Save result…")
    b_load.setToolTip("Open an image file (Ctrl+O)")
    b_demo.setToolTip("Load the synthetic demo scene (Ctrl+D)")
    b_save.setToolTip("Save the displayed result (Ctrl+S)")
    ImageView = _image_view_class(QtWidgets, QtGui, QtCore)
    view = ImageView()
    b_zin = QtWidgets.QPushButton("Zoom +"); b_zout = QtWidgets.QPushButton("Zoom −")
    b_fit = QtWidgets.QPushButton("Fit"); b_11 = QtWidgets.QPushButton("1:1")
    for _b, _t in ((b_zin, "Zoom in (Ctrl+=)"), (b_zout, "Zoom out (Ctrl+-)"),
                   (b_fit, "Fit to window (Ctrl+0)"), (b_11, "Actual size (Ctrl+1)")):
        _b.setToolTip(_t)
    ilay = QtWidgets.QVBoxLayout()
    itop = QtWidgets.QHBoxLayout(); itop.addWidget(b_load); itop.addWidget(b_demo); itop.addWidget(b_save)
    izoom = QtWidgets.QHBoxLayout()
    for w_ in (b_zin, b_zout, b_fit, b_11):
        izoom.addWidget(w_)
    ilay.addLayout(itop); ilay.addWidget(view, 1); ilay.addLayout(izoom)
    ilay.setContentsMargins(4, 4, 4, 4); ilay.setSpacing(4)
    image_panel = QtWidgets.QWidget(); image_panel.setLayout(ilay)
    image_panel.setObjectName("graphics_primary")
    image_panel.setMinimumSize(320, 260)

    display = QtWidgets.QComboBox()
    display.addItems(["gray", "shaded relief", "height (color)"]
                     + [c for c in imgio.COLORMAPS if c != "gray"])
    display.setToolTip("Colour-map the current 2-D result for display")
    b_3d = QtWidgets.QPushButton("3D surface"); b_3d.setToolTip("Rotatable 3-D surface (Ctrl+3)")
    b_loadb = QtWidgets.QPushButton("Load frame B…")
    b_loadb.setToolTip("Load a second frame for two-frame perception (flow / stereo)")
    percep_mode = QtWidgets.QComboBox(); percep_mode.addItems(list(PerceptionModel.MODES))
    percep_mode.setToolTip("Two-frame perception mode")
    b_percep = QtWidgets.QPushButton("Run"); b_percep.setToolTip("Run the selected perception mode on A + B")
    dlay = QtWidgets.QVBoxLayout()
    drow = QtWidgets.QHBoxLayout()
    drow.addWidget(QtWidgets.QLabel("Display:")); drow.addWidget(display, 1); drow.addWidget(b_3d)
    prow = QtWidgets.QHBoxLayout()
    prow.addWidget(b_loadb); prow.addWidget(percep_mode, 1); prow.addWidget(b_percep)
    dlay.addLayout(drow); dlay.addLayout(prow)
    rv.addWidget(_group(QtWidgets, "DISPLAY & PERCEPTION (v14)", dlay))

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
    op_names = [r["name"] for r in all_ops]
    code_edit = ProgEdit(op_names)
    code_edit.setToolTip("Edit the pipeline as code — one `op a b` per line (# starts a comment).\n"
                         "Type for autocomplete; click the gutter to toggle a breakpoint.")
    c_run = QtWidgets.QPushButton("▶ Run (timed)"); c_run.setProperty("accent", True)
    c_step = QtWidgets.QPushButton("Step ▶")
    c_reset = QtWidgets.QPushButton("⏹ Reset")
    c_apply = QtWidgets.QPushButton("Apply → pipeline")
    c_sync = QtWidgets.QPushButton("Sync ← pipeline")
    c_run.setToolTip("Run every line, timing each; stops at a breakpoint (Ctrl+Shift+Return)")
    c_step.setToolTip("Execute one more line and show its result (F10)")
    c_reset.setToolTip("Clear the run highlight and per-line timings")
    c_apply.setToolTip("Parse the code and replace the pipeline")
    c_sync.setToolTip("Regenerate the code from the current pipeline")
    code_status = QtWidgets.QLabel("ready"); code_status.setProperty("hint", True)
    code_w = QtWidgets.QWidget(); cvl = QtWidgets.QVBoxLayout(code_w)
    cvl.setContentsMargins(4, 4, 4, 4); cvl.setSpacing(4)
    crow = QtWidgets.QHBoxLayout()
    for _cb in (c_run, c_step, c_reset, c_apply, c_sync):
        crow.addWidget(_cb)
    crow.addStretch(1)
    cvl.addLayout(crow); cvl.addWidget(code_edit, 1); cvl.addWidget(code_status)

    # -- variables & objects window (HDevelop variable window) --------------- #
    var_list = QtWidgets.QListWidget()
    var_list.setToolTip("Every pipeline variable: the input frame and each stage's output.\n"
                        "Select one to inspect it; the buttons display it in a graphics window.")
    var_inspect = QtWidgets.QPlainTextEdit(); var_inspect.setReadOnly(True)
    var_inspect.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")
    v_disp = QtWidgets.QPushButton("Display → new window")
    v_here = QtWidgets.QPushButton("Display → main")
    v_disp.setToolTip("Open the selected variable in a new graphics window")
    v_here.setToolTip("Show the selected variable in the main graphics window")
    var_w = QtWidgets.QWidget(); vvl = QtWidgets.QVBoxLayout(var_w)
    vvl.setContentsMargins(4, 4, 4, 4); vvl.setSpacing(4)
    vrow = QtWidgets.QHBoxLayout()
    vrow.addWidget(v_disp); vrow.addWidget(v_here); vrow.addStretch(1)
    vvl.addWidget(var_list, 1); vvl.addLayout(vrow); vvl.addWidget(var_inspect, 1)

    # ---- dockable tool windows (VS / HDevelop-style, all movable/floatable) ---- #
    def _mk_dock(title, widget, objname):
        d = QtWidgets.QDockWidget(title, win)
        d.setObjectName(objname)
        d.setWidget(widget)
        d.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable
                      | QtWidgets.QDockWidget.DockWidgetFloatable
                      | QtWidgets.QDockWidget.DockWidgetClosable)
        d.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        return d

    dock_ops = _mk_dock("Operators", left, "dock_operators")
    dock_pipe = _mk_dock("Pipeline · Parameters", mid, "dock_pipeline")
    dock_disp = _mk_dock("Display · Analysis", right, "dock_display")
    win.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_ops)
    win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_pipe)
    win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_disp)
    win.splitDockWidget(dock_pipe, dock_disp, QtCore.Qt.Vertical)
    # Keep the central graphics workspace the dominant surface; tool docks stay narrow.
    win.resizeDocks([dock_ops, dock_pipe], [290, 330], QtCore.Qt.Horizontal)
    dock_code = _mk_dock("Program (code)", code_w, "dock_program")
    win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock_code)
    win.resizeDocks([dock_code], [210], QtCore.Qt.Vertical)
    dock_vars = _mk_dock("Variables & Objects", var_w, "dock_variables")
    win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock_vars)
    win.tabifyDockWidget(dock_code, dock_vars)
    dock_code.raise_()
    win._docks = {"operators": dock_ops, "pipeline": dock_pipe, "display": dock_disp,
                  "program": dock_code, "variables": dock_vars}

    # ---- central graphics workspace: the primary image window ------------------ #
    gsub = mdi.addSubWindow(image_panel)
    gsub.setWindowTitle("Graphics 1")
    gsub.setObjectName("graphics_sub_1")
    win._graphics_windows.append(gsub)

    def new_graphics_window(pixmap=None, title=None):
        """Open another graphics window (HDevelop allows several). Shows a snapshot
        of the current display by default, or a supplied pixmap (e.g. a variable)."""
        n = len(win._graphics_windows) + 1
        gv = ImageView()
        try:
            gv.set_pixmap(pixmap if pixmap is not None else view._item.pixmap())
            gv.fit()
        except Exception:
            pass
        sub = mdi.addSubWindow(gv)
        sub.setWindowTitle(title or ("Graphics %d" % n))
        sub.resize(440, 360)
        sub.show()
        win._graphics_windows.append(sub)
        win._flash and win._flash("opened %s" % sub.windowTitle())
        return sub
    win._new_graphics_window = new_graphics_window

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
             "dirty": False, "errors": [], "perception_error": None, "renders": 0}
    pmodel = PerceptionModel()

    # -- behaviour --
    def selected_index():
        return stage_list.currentRow()

    def mark_dirty():
        """Record that the in-memory pipeline no longer matches anything on disk."""
        state["dirty"] = True

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
        """True if it is OK to throw away unsaved pipeline edits."""
        if not state["dirty"] or not model.stages:
            return True
        return bool(CONFIRM_HOOK(
            win, title,
            "%s has %d unsaved stage(s).\nDiscard them?" % (what.capitalize(), len(model.stages))))

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
        for i, (name, a, b) in enumerate(model.stages):
            st = states[i]["state"] if i < len(states) else {}
            summ = step_summary(st) if st else ""
            it = QtWidgets.QListWidgetItem(f"{i + 1}. {name} (a={a:.2f},b={b:.2f})  ->  {summ}")
            it.setData(QtCore.Qt.UserRole, i)         # model index, for drag-reorder mapping
            row = _op_row(name)
            it.setToolTip(op_tooltip(row) if row else name)
            if st.get("kind") == "error":             # mark a stage that raised at runtime
                it.setForeground(QtGui.QColor(AMBER))
                it.setToolTip("runtime error: " + truncate(st.get("message", "")))
            stage_list.addItem(it)
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
            hist_view.clear(); state["result"] = None; state["raw"] = None
            return
        d = inspect_result(val)
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
            shown = apply_display(val, display.currentText())
            qi = _to_qimage(shown, QtGui)
            if qi is not None:
                view.set_pixmap(QtGui.QPixmap.fromImage(qi)); view.fit()
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
        state["renders"] += 1
        try:
            _render()
        except Exception as e:
            view.set_message("Display error\n\n%s\n\n(see the Problems list)" % truncate(e, 200))
            inspector.setPlainText("display error: %s" % e)
            hist_view.clear(); state["result"] = None; state["raw"] = None
            report_error("Display error", e)
        update_actions()

    def update_actions():
        """Keep every action/button that needs a selection or a displayable result
        in step with the current state, so the UI never offers a dead command."""
        i = selected_index()
        n = len(model.stages)
        has_sel = 0 <= i < n
        has_res = isinstance(state.get("result"), np.ndarray)
        for w in (act_remove, b_rm):
            w.setEnabled(has_sel)
        for w in (act_up, b_up):
            w.setEnabled(has_sel and i > 0)
        for w in (act_down, b_dn):
            w.setEnabled(has_sel and i < n - 1)
        for w in (act_save_res, b_save, act_3d, b_3d):
            w.setEnabled(has_res)
        for w in (act_export, b_export, act_save_pipe, b_savep, act_clear):
            w.setEnabled(n > 0)
        for w in (act_step, b_step, act_runall, b_runall):
            w.setEnabled(n > 0)

    def sync_stage_ui():
        """Sync the knob sliders / stage description / action states to the current
        selection. Does not render — callers own exactly one show_result()."""
        i = selected_index()
        valid = 0 <= i < len(model.stages)
        if valid:
            state["view_raw"] = False                 # selecting a stage leaves the raw view
        sa.setEnabled(valid); sb.setEnabled(valid)
        if valid:
            name, a, b = model.stages[i]
            sa.blockSignals(True); sb.blockSignals(True)
            sa.setValue(int(a * 100)); sb.setValue(int(b * 100))
            sa.blockSignals(False); sb.blockSignals(False)
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

    def on_knob(_=None):
        """A knob tick: update the model + the live preview only.

        The per-stage summaries (model.step_states(), which re-runs every prefix and
        is therefore O(n^2) in the number of stages) are debounced onto a timer, so
        dragging a slider costs one pipeline evaluation per tick instead of n + 2."""
        i = selected_index()
        if 0 <= i < len(model.stages):
            model.set_knobs(i, a=sa.value() / 100.0, b=sb.value() / 100.0)
            la.setText(f"a: {sa.value()/100:.2f}"); lb.setText(f"b: {sb.value()/100:.2f}")
            mark_dirty()
            show_result()
            knob_timer.start(KNOB_DEBOUNCE_MS)

    def on_knob_settled():
        """Debounce tail: refresh the stage summaries once the drag has stopped."""
        i = selected_index()
        refresh_stage_list(select=i if 0 <= i < len(model.stages) else None)

    knob_timer = QtCore.QTimer(win)
    knob_timer.setSingleShot(True)
    knob_timer.timeout.connect(on_knob_settled)

    def add_op(item):
        i = selected_index()
        # insert with the args entered in the operator panel (HDevelop-style)
        model.add_stage(item.data(QtCore.Qt.UserRole), op_a_spin.value(), op_b_spin.value())
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
            new_graphics_window(pm, title)
            flash("ran %s once — result in a new graphics window (pipeline unchanged)" % name)
        else:                                   # scalar feature / contour: no raster preview
            d = inspect_result(out)
            flash("ran %s once → %s (pipeline unchanged)" % (name, d.get("value", d.get("kind", "result"))))
        win._last_run_once = {"op": name, "a": a, "b": b, "result": out}
    win._run_op_once = run_op_once
    win._op_arg_spins = (op_a_spin, op_b_spin)
    win._op_list = op_list
    win._op_buttons = {"insert": b_insert, "run_once": b_run_once, "help": b_help}

    def step_to(i):
        if 0 <= i < len(model.stages):
            stage_list.setCurrentRow(i)                      # triggers show_result for that step

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
            model.load_recipe(samples.itemText(idx))
        except Exception as e:
            report_error("Sample pipeline", e); return
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
            model.remove_stage(i)
            mark_dirty()
            refresh_stage_list()         # selection is now -1 -> disable knobs, clear detail
            show_result()

    def move(delta):
        i = selected_index(); j = i + delta
        if 0 <= i < len(model.stages) and 0 <= j < len(model.stages):
            model.move_stage(i, j); mark_dirty()
            refresh_stage_list(select=j); show_result()

    def load_image():
        path, _ = QtWidgets.QFileDialog.getOpenFileName(win, "Open image", "",
                                                        "Images (*.png *.jpg *.bmp *.tif)")
        if not path:
            return
        try:
            arr = imgio.load(path)                # missing / undecodable / permission
        except Exception as e:
            report_error("Could not open image", "%s\n\n%s" % (path, e)); return
        model.set_image(arr)
        flash("loaded " + os.path.basename(path))
        show_result()

    def use_demo():
        model.set_image(demo_image()); show_result()

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
        flash("saved " + os.path.basename(path))

    def export():
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Export"); v = QtWidgets.QVBoxLayout(dlg)
        te = QtWidgets.QPlainTextEdit()
        te.setPlainText('--ops "' + model.ops_string() + '"\n\n' + model.export_python())
        te.setReadOnly(True); v.addWidget(te); dlg.resize(560, 360); dlg.exec()

    def clear_pipe():
        if not confirm_discard("Clear pipeline"):
            return
        model.stages = []
        mark_dirty()
        refresh_stage_list(); show_result()
        flash("pipeline cleared")

    def show_about():
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("About Fullseye Studio")
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
                hay = (r["name"] + " " + (r["halcon"] or "") + " " + r["category"]).lower()
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

    def show_samples():
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Samples & code")
        h = QtWidgets.QHBoxLayout(dlg)
        lst = QtWidgets.QListWidget()
        for nm in recipes.names():
            lst.addItem(nm)
        code = QtWidgets.QPlainTextEdit(); code.setReadOnly(True)
        code.setStyleSheet("font-family:Consolas,'Cascadia Mono',monospace;")

        def preview(_=None):
            it = lst.currentItem()
            if it is not None:
                sc = sample_code(it.text())
                code.setPlainText(('--ops "%s"\n\n%s' % sc) if sc else "")
        lst.currentRowChanged.connect(lambda _=None: preview())

        def load_and_close():
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
            dlg.accept()
        left = QtWidgets.QVBoxLayout()
        lbl = QtWidgets.QLabel("Sample pipelines"); lbl.setProperty("muted", True)
        b_load = QtWidgets.QPushButton("Load into Studio"); b_load.setProperty("accent", True)
        b_load.clicked.connect(load_and_close)
        left.addWidget(lbl); left.addWidget(lst, 1); left.addWidget(b_load)
        right = QtWidgets.QVBoxLayout()
        clbl = QtWidgets.QLabel("Code (ops string + Python)"); clbl.setProperty("muted", True)
        right.addWidget(clbl); right.addWidget(code, 1)
        h.addLayout(left, 1); h.addLayout(right, 2)
        if lst.count():
            lst.setCurrentRow(0)
        dlg.resize(740, 500); dlg.exec()

    def add_op_by_name(n):
        model.add_stage(n)
        mark_dirty()
        refresh_stage_list(select=len(model.stages) - 1)
        show_result()

    def show_palette():
        # actions first, then every operator — run by name, keyboard-only.
        items = [("▸ " + a.text().replace("…", "").strip(), a.trigger)
                 for a in win._actions.values() if a is not act_palette]
        items += [("op: " + r["name"], (lambda n=r["name"]: add_op_by_name(n))) for r in all_ops]
        labels = [lbl for lbl, _ in items]
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Command palette")
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
    # pipeline + knobs
    def on_op_selected(cur, _prev=None):
        if cur is None:
            op_param.setText("select an operator to see its signature")
            b_insert.setEnabled(False); b_help.setEnabled(False); b_run_once.setEnabled(False); return
        row = _op_row(cur.data(QtCore.Qt.UserRole))
        op_param.setText(op_signature_detail(row) if row else cur.text())
        b_insert.setEnabled(True); b_help.setEnabled(True); b_run_once.setEnabled(True)
    op_list.currentItemChanged.connect(on_op_selected)
    b_insert.clicked.connect(
        lambda: add_op(op_list.currentItem()) if op_list.currentItem() is not None else None)
    b_run_once.clicked.connect(run_op_once)
    op_list.itemDoubleClicked.connect(add_op)

    def jump_to_problem(item):
        idx = item.data(QtCore.Qt.UserRole)
        if idx is not None and 0 <= idx < len(model.stages):
            stage_list.setCurrentRow(idx)
    problems_list.itemDoubleClicked.connect(jump_to_problem)
    samples.currentIndexChanged.connect(load_sample)
    stage_list.currentRowChanged.connect(lambda _=None: on_stage_selected())
    sa.valueChanged.connect(on_knob); sb.valueChanged.connect(on_knob)
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
    act_quit.triggered.connect(win.close)
    act_remove.triggered.connect(remove)
    act_up.triggered.connect(lambda: move(-1)); act_down.triggered.connect(lambda: move(1))
    act_clear.triggered.connect(clear_pipe)
    act_zin.triggered.connect(lambda: view.zoom(1.25)); act_zout.triggered.connect(lambda: view.zoom(0.8))
    act_fit.triggered.connect(view.fit); act_11.triggered.connect(view.reset_zoom)
    act_reset.triggered.connect(reset_to_raw)
    act_step.triggered.connect(lambda: step_to(min(selected_index() + 1, len(model.stages) - 1)))
    act_runall.triggered.connect(lambda: step_to(len(model.stages) - 1))
    # -- program / code editor wiring (parse <-> pipeline, timed run, step) ---- #
    import time as _time

    def program_text_from_model():
        if not model.stages:
            return ("# empty pipeline — type ops here, one per line, e.g.:\n"
                    "# gaussian 0.4 0.5\n# sobel_mag 0.5 0.5\n# otsu 0.5 0.5")
        return "\n".join("%s %.3f %.3f" % (n, a, b) for (n, a, b) in model.stages)

    def sync_program():
        if code_edit.hasFocus():          # never clobber what the user is typing
            return
        code_edit.blockSignals(True)
        code_edit.setPlainText(program_text_from_model())
        code_edit.blockSignals(False)
        code_edit.clear_exec()

    def parse_program(text):
        stages, errs, names = [], [], set(op_names)
        for i, raw in enumerate(text.splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if parts[0] not in names:
                errs.append("line %d: unknown op '%s'" % (i, parts[0])); continue
            try:
                a = float(parts[1]) if len(parts) > 1 else 0.5
                b = float(parts[2]) if len(parts) > 2 else 0.5
            except ValueError:
                errs.append("line %d: knobs must be numbers" % i); continue
            stages.append((parts[0], max(0.0, min(1.0, a)), max(0.0, min(1.0, b))))
        return stages, errs

    def apply_program():
        stages, errs = parse_program(code_edit.toPlainText())
        if errs:
            code_status.setText("✕ " + "  ·  ".join(errs[:3]))
            flash("code has %d error(s)" % len(errs))
            return
        model.stages = list(stages)
        mark_dirty()
        code_status.setText("applied %d stage(s)" % len(stages))
        refresh_stage_list(select=(len(stages) - 1) if stages else None)
        show_result()

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
        code_edit.set_timings(timings)
        code_edit.set_exec_line(last + 1)
        if 0 <= last < len(model.stages):
            stage_list.setCurrentRow(last)     # show the result up to the reached line
        code_status.setText("ran %d line(s) in %.1f ms%s"
                            % (len(timings), sum(timings.values()),
                               "  · stopped at breakpoint" if hit_bp else ""))

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
            code_edit.set_timings(tmap)
        except Exception:
            pass
        code_edit.set_exec_line(nxt)
        stage_list.setCurrentRow(nxt - 1)
        code_status.setText("stepped to line %d" % nxt)

    c_apply.clicked.connect(apply_program)
    c_sync.clicked.connect(sync_program)
    c_run.clicked.connect(lambda: run_program(True))
    c_step.clicked.connect(step_program)
    c_reset.clicked.connect(lambda: (code_edit.clear_exec(), code_status.setText("ready")))
    win._program = {"edit": code_edit, "apply": apply_program, "run": run_program,
                    "step": step_program, "parse": parse_program, "text": program_text_from_model}

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
            var_inspect.setPlainText(""); return
        try:
            val = model.result_upto(it.data(QtCore.Qt.UserRole))
            var_inspect.setPlainText(format_inspection(inspect_result(val)))
        except Exception as e:
            var_inspect.setPlainText("inspect error: %s" % e)

    def refresh_variables():
        sel = var_list.currentRow()
        var_list.blockSignals(True); var_list.clear()
        for label, idx, kind in _var_entries():
            it = QtWidgets.QListWidgetItem("%s   · %s" % (label, kind))
            it.setData(QtCore.Qt.UserRole, idx)
            var_list.addItem(it)
        var_list.setCurrentRow(sel if 0 <= sel < var_list.count() else var_list.count() - 1)
        var_list.blockSignals(False)
        show_variable_inspection()

    def display_variable(new_window=True):
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
            if new_window:
                new_graphics_window(pm, title="var %s" % it.text().split("  ", 1)[0])
            else:
                view.set_pixmap(pm); view.fit(); view.set_data(val)
        else:
            flash("variable is not iconic — see the inspector")

    var_list.currentRowChanged.connect(lambda _r: show_variable_inspection())
    var_list.itemDoubleClicked.connect(lambda _it: display_variable(True))
    v_disp.clicked.connect(lambda: display_variable(True))
    v_here.clicked.connect(lambda: display_variable(False))
    win._variables = {"list": var_list, "refresh": refresh_variables, "display": display_variable}

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
    help_pick.addItems(op_names); help_pick.setToolTip("Jump to any operator's help")
    _htop.addWidget(hd_back); _htop.addWidget(hd_fwd); _htop.addWidget(help_pick, 1)
    _hdl.addLayout(_htop); _hdl.addWidget(help_browser, 1)

    def show_op_help(name):
        if not name:
            return
        row = _op_row(name) or {"in_sort": "?", "out_sort": "?"}
        help_browser.setHtml(op_help_html(name, getattr(win, "_lang", "en"), row))
        i = help_pick.findText(name)
        if i >= 0:
            help_pick.blockSignals(True); help_pick.setCurrentIndex(i); help_pick.blockSignals(False)
        help_dialog.show(); help_dialog.raise_(); help_dialog.activateWindow()

    def _help_anchor(url):
        s = url.toString()
        if s.startswith("op:"):                # related-operator link
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

    help_browser.anchorClicked.connect(_help_anchor)
    help_pick.currentTextChanged.connect(lambda t: show_op_help(t) if t in set(op_names) else None)
    hd_back.clicked.connect(help_browser.backward)
    hd_fwd.clicked.connect(help_browser.forward)
    b_help.clicked.connect(
        lambda: show_op_help(op_list.currentItem().data(QtCore.Qt.UserRole)) if op_list.currentItem() else None)
    win._help = {"dialog": help_dialog, "browser": help_browser, "show": show_op_help}

    def sync_panels():
        sync_program(); refresh_variables()
    win._code_sync = sync_panels
    sync_panels()

    act_palette.triggered.connect(show_palette)
    act_shortcuts.triggered.connect(show_shortcuts)
    act_op_help.triggered.connect(
        lambda: show_op_help((op_list.currentItem().data(QtCore.Qt.UserRole))
                             if op_list.currentItem() else (op_names[0] if op_names else "")))
    act_samples.triggered.connect(show_samples)
    act_about.triggered.connect(show_about)

    def open_3d():
        raw = state.get("raw")
        if isinstance(raw, np.ndarray):
            g = raw if raw.ndim == 2 else imgio.ensure_gray(raw)
            win._surf = show_3d_surface(g, None)
    b_3d.clicked.connect(open_3d); act_3d.triggered.connect(open_3d)

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
        flash("saved " + os.path.basename(path))

    def open_pipe():
        import json
        path, _ = QtWidgets.QFileDialog.getOpenFileName(win, "Open pipeline", "", "JSON (*.json)")
        if not path:
            return
        if not confirm_discard("Open pipeline"):
            return
        try:
            with open(path, encoding="utf-8") as fh:          # missing / permission
                data = json.loads(fh.read())                  # malformed JSON
            model.load_dict(data)                             # schema + op-name validation
        except Exception as e:
            # load_dict validates into a temporary list before assigning, so the
            # pipeline currently on screen survives a bad file untouched.
            report_error("Could not open pipeline", "%s\n\n%s" % (path, e)); return
        mark_dirty()
        refresh_stage_list(select=len(model.stages) - 1); show_result()
        flash("loaded " + os.path.basename(path))
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
    for _a in (act_remove, act_up, act_down, act_step, act_reset):
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
        "open_pipeline": act_open_pipe, "save_pipeline": act_save_pipe, "export": act_export,
        "quit": act_quit, "remove": act_remove, "move_up": act_up, "move_down": act_down,
        "clear": act_clear, "zoom_in": act_zin, "zoom_out": act_zout, "fit": act_fit,
        "actual_size": act_11, "surface_3d": act_3d, "reset": act_reset, "step": act_step,
        "run_all": act_runall, "palette": act_palette, "shortcuts": act_shortcuts,
        "op_reference": act_op_help, "samples": act_samples, "about": act_about,
    }
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
            sub.setWindowTitle(title or "Graphics")
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

    # -- tooltip / help localisation (en / ja / zh) --------------------------- #
    win._tt_en = {w: w.toolTip() for w in win.findChildren(QtWidgets.QWidget) if w.toolTip()}
    win._lang = "en"
    win._lang_actions = {}

    def apply_language(lang):
        win._lang = lang if lang in ("en", "ja", "zh") else "en"
        for w, en in win._tt_en.items():
            try:
                w.setToolTip(en if win._lang == "en"
                             else TOOLTIPS_I18N.get(en, {}).get(win._lang, en))
            except Exception:
                pass
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
            geo = s.value("geometry"); st = s.value("windowState")
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

    refresh_stage_list(); show_result()      # refresh_stage_list syncs the knob panel
    state["dirty"] = False                   # a freshly-built window has nothing to lose
    state["renders"] = 0
    return win, model


def main() -> int:
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win, _ = build_window()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
