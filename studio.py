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

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import api
import imgio
import recipes
import flow          # v14 perception panel
import motion
import stereo
import terrain


# --------------------------------------------------------------------------- #
# Headless pipeline logic (no Qt) — unit-testable.
# --------------------------------------------------------------------------- #
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
        step-through debugger shows — the object/variable state at every step."""
        out = []
        for i in range(len(self.stages)):
            op, a, b = self.stages[i]
            out.append({"index": i, "op": op, "a": a, "b": b,
                        "state": inspect_result(self.result_upto(i))})
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
        self.stages = [[s[0], float(s[1]), float(s[2])] for s in d.get("stages", [])]


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
* {{ outline:none; }}
QWidget {{ background:{NAVY_0}; color:{TEXT}; font-size:12px;
    font-family:"Segoe UI","Yu Gothic UI","Meiryo",system-ui,sans-serif; }}
QMainWindow, QDialog {{ background:{NAVY_0}; }}
QLabel {{ color:{TEXT}; background:transparent; }}
QLabel[muted="true"] {{ color:{MUTED}; }}
QLabel[hint="true"] {{ color:{MUTED}; font-family:Consolas,"Cascadia Mono",monospace; }}

QMenuBar {{ background:#12141b; color:#c7cbd6; border-bottom:1px solid #262b38; padding:2px 6px; }}
QMenuBar::item {{ background:transparent; padding:6px 12px; border-radius:6px; }}
QMenuBar::item:selected {{ background:{NAVY_2}; color:{TEAL_HI}; }}
QMenu {{ background:{NAVY_1}; border:1px solid {LINE}; border-radius:8px; padding:6px; }}
QMenu::item {{ padding:6px 28px 6px 14px; border-radius:6px; }}
QMenu::item:selected {{ background:{TEAL}; color:{INK}; }}
QMenu::separator {{ height:1px; background:{LINE}; margin:6px 8px; }}

QToolBar {{ background:#12141b; border:none; border-bottom:1px solid #262b38; spacing:6px; padding:6px 10px; }}
QToolButton {{ background:{NAVY_2}; border:1px solid {LINE}; border-radius:7px; padding:6px 12px; color:{TEXT}; }}
QToolButton:hover {{ border-color:{TEAL}; color:{TEAL_HI}; }}
QToolButton:pressed {{ background:{TEAL}; color:{INK}; }}
QToolButton[accent="true"] {{ background:{TEAL}; color:{INK}; border:none; font-weight:700; }}
QToolButton[accent="true"]:hover {{ background:{TEAL_HI}; }}

QGroupBox {{ background:{NAVY_1}; border:1px solid #262b38; border-radius:10px;
    margin-top:14px; padding:12px 10px 10px 10px; }}
QGroupBox::title {{ subcontrol-origin:margin; subcontrol-position:top left; left:12px; top:1px;
    padding:2px 8px; color:{AMBER}; font-size:10px; font-weight:700; letter-spacing:1px; }}

QLineEdit,QComboBox,QPlainTextEdit,QListWidget,QSpinBox {{ background:{NAVY_2};
    border:1px solid {LINE}; border-radius:7px; padding:5px 8px;
    selection-background-color:{TEAL}; selection-color:{INK}; }}
QLineEdit:focus,QComboBox:focus,QPlainTextEdit:focus,QListWidget:focus {{ border-color:{TEAL}; }}
QListWidget::item {{ padding:5px 6px; border-radius:5px; }}
QListWidget::item:hover {{ background:#232a36; }}
QListWidget::item:selected {{ background:{TEAL}; color:{INK}; }}
QComboBox::drop-down {{ border:none; width:22px; }}
QComboBox QAbstractItemView {{ background:{NAVY_1}; border:1px solid {LINE}; border-radius:8px;
    selection-background-color:{TEAL}; selection-color:{INK}; outline:none; }}

QPushButton {{ background:{NAVY_2}; border:1px solid {LINE}; border-radius:7px; padding:7px 12px; color:{TEXT}; }}
QPushButton:hover {{ background:#262b38; border-color:{TEAL}; }}
QPushButton:pressed {{ background:{TEAL}; color:{INK}; }}
QPushButton:disabled {{ color:#5b6270; border-color:#232734; background:#191c25; }}
QPushButton[accent="true"] {{ background:{TEAL}; color:{INK}; border:none; font-weight:700; }}
QPushButton[accent="true"]:hover {{ background:{TEAL_HI}; }}

QSlider::groove:horizontal {{ height:6px; background:{LINE}; border-radius:3px; }}
QSlider::handle:horizontal {{ width:16px; background:{AMBER}; border-radius:8px; margin:-6px 0; }}
QSlider::handle:horizontal:hover {{ background:#ffb841; }}
QSlider::sub-page:horizontal {{ background:{TEAL}; border-radius:3px; }}
QSlider:disabled::handle:horizontal {{ background:#4a4f5c; }}

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


def op_tooltip(row) -> str:
    """Multi-line tooltip for an operator list item / stage."""
    return ("%s\nHALCON alias: %s\ncategory: %s\nsort: %s → %s\n"
            "a, b are the two knobs (each 0..1); their meaning depends on the op"
            % (row["name"], row.get("halcon") or "(none)", row["category"],
               row["in_sort"], row["out_sort"]))


def _op_row(name):
    """Look up an op and return a ``list_ops``-shaped dict, or None."""
    op = api.find_op(name)
    if op is None:
        return None
    return {"name": op.name, "halcon": op.halcon, "category": op.category,
            "in_sort": op.in_sort, "out_sort": op.out_sort}


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


def build_window(model=None):
    """Construct (but do not exec) the main window. Returns (window, model).

    The window is a QMainWindow with a menu bar (all actions + keyboard
    shortcuts), a branded toolbar, a status bar (hover read-out + transient
    messages), and three titled panels: Operators, Pipeline/Knobs, and the
    Image/Perception/Inspector column."""
    from PySide6 import QtWidgets, QtGui, QtCore

    model = model or PipelineModel(demo_image())
    win = QtWidgets.QMainWindow()
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
    act_about = _act("About Fullseye Studio", None, "About this application")

    mb = win.menuBar()
    m = mb.addMenu("&File")
    m.addAction(act_open_img); m.addAction(act_demo); m.addSeparator()
    m.addAction(act_save_res); m.addSeparator()
    m.addAction(act_open_pipe); m.addAction(act_save_pipe); m.addAction(act_export)
    m.addSeparator(); m.addAction(act_quit)
    m = mb.addMenu("&Edit")
    m.addAction(act_remove); m.addAction(act_up); m.addAction(act_down)
    m.addSeparator(); m.addAction(act_clear)
    m = mb.addMenu("&View")
    m.addAction(act_zin); m.addAction(act_zout); m.addAction(act_fit); m.addAction(act_11)
    m.addSeparator(); m.addAction(act_3d)
    m = mb.addMenu("&Run")
    m.addAction(act_reset); m.addAction(act_step); m.addAction(act_runall)
    m = mb.addMenu("&Help")
    m.addAction(act_about)

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

    central = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
    win.setCentralWidget(central)

    status = win.statusBar()
    readout = QtWidgets.QLabel("hover over the image for pixel coordinates + value")
    readout.setProperty("hint", True)
    status.addWidget(readout)

    def flash(msg):
        status.showMessage(msg, 6000)

    # -- left: operator browser + samples ------------------------------------ #
    left = QtWidgets.QWidget(); lv = QtWidgets.QVBoxLayout(left); lv.setSpacing(10)
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
    op_hint = QtWidgets.QLabel("double-click to insert  ·  hover for details")
    op_hint.setProperty("muted", True)
    olay = QtWidgets.QVBoxLayout()
    olay.addWidget(cat); olay.addWidget(search); olay.addWidget(op_list, 1); olay.addWidget(op_hint)
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
    mid = QtWidgets.QWidget(); mv = QtWidgets.QVBoxLayout(mid); mv.setSpacing(10)
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
    play = QtWidgets.QVBoxLayout(); play.addWidget(stage_list, 1)
    erow = QtWidgets.QHBoxLayout(); erow.addWidget(b_rm); erow.addWidget(b_up); erow.addWidget(b_dn)
    srow = QtWidgets.QHBoxLayout(); srow.addWidget(b_reset); srow.addWidget(b_step); srow.addWidget(b_runall)
    play.addLayout(erow); play.addLayout(srow)
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
    right = QtWidgets.QWidget(); rv = QtWidgets.QVBoxLayout(right); rv.setSpacing(10)
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
    rv.addWidget(_group(QtWidgets, "IMAGE", ilay), 1)

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

    central.addWidget(left); central.addWidget(mid); central.addWidget(right)
    central.setSizes([340, 360, 640]); central.setStretchFactor(2, 1)
    state = {"result": None, "raw": None, "view_raw": False, "reordering": False}
    pmodel = PerceptionModel()

    # -- behaviour --
    def selected_index():
        return stage_list.currentRow()

    def refresh_stage_list(select=None):
        state["reordering"] = True                    # suppress the drag-reorder handler
        stage_list.blockSignals(True)
        stage_list.clear()
        try:
            states = model.step_states()
        except Exception:
            states = []
        for i, (name, a, b) in enumerate(model.stages):
            summ = step_summary(states[i]["state"]) if i < len(states) else ""
            it = QtWidgets.QListWidgetItem(f"{i + 1}. {name} (a={a:.2f},b={b:.2f})  ->  {summ}")
            it.setData(QtCore.Qt.UserRole, i)         # model index, for drag-reorder mapping
            stage_list.addItem(it)
        stage_list.blockSignals(False)
        state["reordering"] = False
        if select is not None and 0 <= select < len(model.stages):
            stage_list.setCurrentRow(select)

    def on_rows_moved(*_):
        """A drag-reorder inside the stage list -> permute model.stages to match."""
        if state.get("reordering"):
            return
        order = [stage_list.item(r).data(QtCore.Qt.UserRole) for r in range(stage_list.count())]
        if len(order) == len(model.stages) and set(order) == set(range(len(model.stages))):
            model.stages = [model.stages[i] for i in order]
            refresh_stage_list(select=stage_list.currentRow())
            on_stage_selected()

    def show_result():
        idx = selected_index()
        if idx < 0 and state.get("view_raw"):
            val = model.result_upto(-1)               # Reset -> the pre-pipeline raw image
        else:
            val = model.result_upto(idx if idx >= 0 else len(model.stages) - 1)
        insp = format_inspection(inspect_result(val))
        if isinstance(val, np.ndarray) and val.ndim == 2 and _is_binary(val) and val.any():
            try:
                import detect
                objs = detect.segment_objects(val, threshold="none", min_area=1)
                if objs:
                    insp += "\n\nRegion features:\n" + detect.feature_table(objs)
            except Exception:
                pass
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
            view.clear(); hist_view.clear(); state["result"] = None; state["raw"] = None

    def on_stage_selected():
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
            la.setText(f"a: {a:.2f}"); lb.setText(f"b: {b:.2f}")
            row = _op_row(name)
            stage_detail.setText(op_detail(row) if row else name)
        else:
            stage_detail.setText("select a stage to tune its knobs")
        show_result()

    def on_knob(_=None):
        i = selected_index()
        if 0 <= i < len(model.stages):
            model.set_knobs(i, a=sa.value() / 100.0, b=sb.value() / 100.0)
            la.setText(f"a: {sa.value()/100:.2f}"); lb.setText(f"b: {sb.value()/100:.2f}")
            refresh_stage_list(select=i)
            show_result()

    def add_op(item):
        i = selected_index()
        model.add_stage(item.data(QtCore.Qt.UserRole))       # appended at the end
        newpos = len(model.stages) - 1
        if 0 <= i < newpos:                                  # insert just after the selected stage
            model.move_stage(newpos, i + 1); newpos = i + 1
        refresh_stage_list(select=newpos)
        show_result()

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
        model.load_recipe(samples.itemText(idx))
        refresh_stage_list(select=len(model.stages) - 1)
        show_result()

    def remove():
        i = selected_index()
        if 0 <= i < len(model.stages):
            model.remove_stage(i)
            refresh_stage_list()
            on_stage_selected()          # selection is now -1 -> disable knobs, clear detail

    def move(delta):
        i = selected_index(); j = i + delta
        if 0 <= i < len(model.stages) and 0 <= j < len(model.stages):
            model.move_stage(i, j); refresh_stage_list(select=j); show_result()

    def load_image():
        path, _ = QtWidgets.QFileDialog.getOpenFileName(win, "Open image", "",
                                                        "Images (*.png *.jpg *.bmp *.tif)")
        if path:
            model.set_image(imgio.load(path)); show_result()

    def use_demo():
        model.set_image(demo_image()); show_result()

    def save_result():
        if state["result"] is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(win, "Save result", "result.png",
                                                        "PNG (*.png);;All files (*)")
        if path:
            imgio.save(path, state["result"])

    def export():
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Export"); v = QtWidgets.QVBoxLayout(dlg)
        te = QtWidgets.QPlainTextEdit()
        te.setPlainText('--ops "' + model.ops_string() + '"\n\n' + model.export_python())
        te.setReadOnly(True); v.addWidget(te); dlg.resize(560, 360); dlg.exec()

    def clear_pipe():
        model.stages = []
        refresh_stage_list(); on_stage_selected(); show_result()
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

    # operator browser filters
    search.textChanged.connect(refill_ops); cat.currentIndexChanged.connect(refill_ops)
    # pipeline + knobs
    op_list.itemDoubleClicked.connect(add_op)
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
    b_reset.clicked.connect(lambda: step_to(0))
    b_step.clicked.connect(lambda: step_to(min(selected_index() + 1, len(model.stages) - 1)))
    b_runall.clicked.connect(lambda: step_to(len(model.stages) - 1))
    # menu / toolbar actions (share the same handlers as the buttons)
    act_open_img.triggered.connect(load_image); act_demo.triggered.connect(use_demo)
    act_save_res.triggered.connect(save_result); act_export.triggered.connect(export)
    act_quit.triggered.connect(win.close)
    act_remove.triggered.connect(remove)
    act_up.triggered.connect(lambda: move(-1)); act_down.triggered.connect(lambda: move(1))
    act_clear.triggered.connect(clear_pipe)
    act_zin.triggered.connect(lambda: view.zoom(1.25)); act_zout.triggered.connect(lambda: view.zoom(0.8))
    act_fit.triggered.connect(view.fit); act_11.triggered.connect(view.reset_zoom)
    act_reset.triggered.connect(lambda: step_to(0))
    act_step.triggered.connect(lambda: step_to(min(selected_index() + 1, len(model.stages) - 1)))
    act_runall.triggered.connect(lambda: step_to(len(model.stages) - 1))
    act_about.triggered.connect(show_about)

    def open_3d():
        raw = state.get("raw")
        if isinstance(raw, np.ndarray):
            g = raw if raw.ndim == 2 else imgio.ensure_gray(raw)
            win._surf = show_3d_surface(g, None)
    b_3d.clicked.connect(open_3d); act_3d.triggered.connect(open_3d)

    def load_frame_b():
        path, _ = QtWidgets.QFileDialog.getOpenFileName(win, "Open frame B", "",
                                                        "Images (*.png *.jpg *.bmp *.tif)")
        if path:
            pmodel.set_frame_b(imgio.load(path))
            flash("frame B loaded: " + os.path.basename(path))

    def run_perception():
        try:
            rgb = pmodel.view(percep_mode.currentText(), model.image)
        except Exception as e:                                # missing/mismatched frame B, etc.
            flash("perception: " + str(e)); return
        qi = _to_qimage(rgb, QtGui)
        if qi is not None:
            view.set_pixmap(QtGui.QPixmap.fromImage(qi)); view.fit()
        view.set_data(rgb)
        state["result"] = rgb; state["raw"] = rgb
        inspector.setPlainText("perception: %s  ->  RGB %s" % (percep_mode.currentText(), rgb.shape))
    b_loadb.clicked.connect(load_frame_b); b_percep.clicked.connect(run_perception)

    def save_pipe():
        import json
        path, _ = QtWidgets.QFileDialog.getSaveFileName(win, "Save pipeline", "pipeline.json",
                                                        "JSON (*.json)")
        if path:
            open(path, "w", encoding="utf-8").write(json.dumps(model.to_dict(), indent=2))

    def open_pipe():
        import json
        path, _ = QtWidgets.QFileDialog.getOpenFileName(win, "Open pipeline", "", "JSON (*.json)")
        if path:
            model.load_dict(json.loads(open(path, encoding="utf-8").read()))
            refresh_stage_list(select=len(model.stages) - 1); show_result()
    b_savep.clicked.connect(save_pipe); b_openp.clicked.connect(open_pipe)
    act_save_pipe.triggered.connect(save_pipe); act_open_pipe.triggered.connect(open_pipe)

    def on_hover(x, y, v):
        if np.ndim(v) == 0:
            readout.setText(f"x={x}  y={y}   value={float(v):.4f}")
        else:
            readout.setText(f"x={x}  y={y}   RGB=({float(v[0]):.3f},{float(v[1]):.3f},{float(v[2]):.3f})")
    view.hover_cb = on_hover

    win._perception = {"model": pmodel, "mode": percep_mode, "run": run_perception}
    win._flash = flash
    win._actions = {
        "open_image": act_open_img, "demo": act_demo, "save_result": act_save_res,
        "open_pipeline": act_open_pipe, "save_pipeline": act_save_pipe, "export": act_export,
        "quit": act_quit, "remove": act_remove, "move_up": act_up, "move_down": act_down,
        "clear": act_clear, "zoom_in": act_zin, "zoom_out": act_zout, "fit": act_fit,
        "actual_size": act_11, "surface_3d": act_3d, "reset": act_reset, "step": act_step,
        "run_all": act_runall, "about": act_about,
    }
    refresh_stage_list(); on_stage_selected(); show_result()
    return win, model


def main() -> int:
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win, _ = build_window()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
