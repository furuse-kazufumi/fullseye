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

    def ops_string(self):
        return ",".join(s[0] for s in self.stages)

    def export_python(self):
        lines = ["import fullseye, numpy as np", "", "def pipeline(frame):",
                 "    return fullseye.run_pipeline(frame, ["]
        for name, a, b in self.stages:
            lines.append(f"        ({name!r}, {a:.3f}, {b:.3f}),")
        lines += ["    ])"]
        return "\n".join(lines) + "\n"


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


# Dark, modern IDE theme (QSS). Accent is a warm "bullseye" coral.
THEME = """
QWidget { background:#1e1f26; color:#d7d9e0; font-size:12px; }
QLabel { color:#9aa0ad; }
QLineEdit,QComboBox,QPlainTextEdit,QListWidget { background:#262832; border:1px solid #33353f;
    border-radius:6px; padding:4px; selection-background-color:#ff6b4a; }
QListWidget::item:selected { background:#ff6b4a; color:#141414; }
QPushButton { background:#2d2f3a; border:1px solid #3a3d49; border-radius:6px; padding:6px 10px; }
QPushButton:hover { background:#3a3d49; border-color:#ff6b4a; }
QPushButton:pressed { background:#ff6b4a; color:#141414; }
QComboBox::drop-down { border:none; width:18px; }
QSlider::groove:horizontal { height:6px; background:#33353f; border-radius:3px; }
QSlider::handle:horizontal { width:16px; background:#ff6b4a; border-radius:8px; margin:-6px 0; }
QSlider::sub-page:horizontal { background:#ff6b4a; border-radius:3px; }
QScrollBar:vertical { background:#1e1f26; width:12px; margin:0; }
QScrollBar::handle:vertical { background:#3a3d49; border-radius:6px; min-height:24px; }
QScrollBar::add-line,QScrollBar::sub-line { height:0; }
QSplitter::handle { background:#33353f; }
"""


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

        def set_pixmap(self, pm):
            self._item.setPixmap(pm)
            self._scene.setSceneRect(QtCore.QRectF(pm.rect()))

        def clear(self):
            self._item.setPixmap(QtGui.QPixmap())

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


def build_window(model=None):
    """Construct (but do not exec) the main window. Returns (window, model)."""
    from PySide6 import QtWidgets, QtGui, QtCore

    model = model or PipelineModel(demo_image())
    win = QtWidgets.QMainWindow()
    win.setWindowTitle("Fullseye Studio")
    win.resize(1300, 820)
    win.setStyleSheet(THEME)
    root = QtWidgets.QWidget(); rootlay = QtWidgets.QVBoxLayout(root)
    rootlay.setContentsMargins(0, 0, 0, 0); rootlay.setSpacing(0)
    header = QtWidgets.QLabel("  Fullseye Studio  -  image pipeline workbench")
    header.setStyleSheet("font-size:16px; font-weight:700; color:#ff6b4a; padding:10px 14px;"
                         "background:#181920; border-bottom:1px solid #33353f;")
    central = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
    rootlay.addWidget(header); rootlay.addWidget(central, 1)
    win.setCentralWidget(root)

    # -- left: operator browser + samples --
    left = QtWidgets.QWidget(); lv = QtWidgets.QVBoxLayout(left)
    lv.addWidget(QtWidgets.QLabel("Sample pipelines"))
    samples = QtWidgets.QComboBox(); samples.addItem("-- load a sample --")
    for nm in recipes.names():
        samples.addItem(nm)
    lv.addWidget(samples)
    lv.addWidget(QtWidgets.QLabel("Operators (double-click to add)"))
    search = QtWidgets.QLineEdit(); search.setPlaceholderText("search operators...")
    op_list = QtWidgets.QListWidget()
    lv.addWidget(search); lv.addWidget(op_list)
    all_ops = api.list_ops()

    def refill_ops():
        kw = search.text().lower()
        op_list.clear()
        for r in all_ops:
            hay = (r["name"] + " " + (r["halcon"] or "") + " " + r["category"]).lower()
            if kw and kw not in hay:
                continue
            it = QtWidgets.QListWidgetItem(f"{r['name']}  [{r['in_sort']}->{r['out_sort']}]")
            it.setData(QtCore.Qt.UserRole, r["name"])
            op_list.addItem(it)
    refill_ops()
    search.textChanged.connect(refill_ops)

    # -- centre: pipeline + knobs --
    mid = QtWidgets.QWidget(); mv = QtWidgets.QVBoxLayout(mid)
    stage_list = QtWidgets.QListWidget()
    btns = QtWidgets.QHBoxLayout()
    b_rm = QtWidgets.QPushButton("Remove"); b_up = QtWidgets.QPushButton("Up"); b_dn = QtWidgets.QPushButton("Down")
    btns.addWidget(b_rm); btns.addWidget(b_up); btns.addWidget(b_dn)
    sa = QtWidgets.QSlider(QtCore.Qt.Horizontal); sa.setRange(0, 100)
    sb = QtWidgets.QSlider(QtCore.Qt.Horizontal); sb.setRange(0, 100)
    la = QtWidgets.QLabel("a: 0.50"); lb = QtWidgets.QLabel("b: 0.50")
    b_export = QtWidgets.QPushButton("Export (ops string + Python)")
    mv.addWidget(QtWidgets.QLabel("Pipeline")); mv.addWidget(stage_list)
    mv.addLayout(btns)
    mv.addWidget(la); mv.addWidget(sa); mv.addWidget(lb); mv.addWidget(sb)
    mv.addWidget(b_export)

    # -- right: zoomable image view + zoom controls + histogram + inspector --
    right = QtWidgets.QWidget(); rv = QtWidgets.QVBoxLayout(right)
    top = QtWidgets.QHBoxLayout()
    b_load = QtWidgets.QPushButton("Load image..."); b_demo = QtWidgets.QPushButton("Synthetic demo")
    b_save = QtWidgets.QPushButton("Save result...")
    top.addWidget(b_load); top.addWidget(b_demo); top.addWidget(b_save)
    ImageView = _image_view_class(QtWidgets, QtGui, QtCore)
    view = ImageView()
    zoom = QtWidgets.QHBoxLayout()
    b_zin = QtWidgets.QPushButton("Zoom +"); b_zout = QtWidgets.QPushButton("Zoom -")
    b_fit = QtWidgets.QPushButton("Fit"); b_11 = QtWidgets.QPushButton("1:1")
    for w_ in (b_zin, b_zout, b_fit, b_11):
        zoom.addWidget(w_)
    hist_view = QtWidgets.QLabel(); hist_view.setFixedHeight(70); hist_view.setStyleSheet("background:#181818;")
    inspector = QtWidgets.QPlainTextEdit(); inspector.setReadOnly(True); inspector.setFixedHeight(140)
    inspector.setStyleSheet("font-family:Consolas,monospace;")
    rv.addLayout(top); rv.addWidget(view, 1); rv.addLayout(zoom)
    rv.addWidget(QtWidgets.QLabel("Histogram")); rv.addWidget(hist_view)
    rv.addWidget(QtWidgets.QLabel("Inspector (variable / image / region)")); rv.addWidget(inspector)

    central.addWidget(left); central.addWidget(mid); central.addWidget(right)
    central.setSizes([320, 320, 620])
    state = {"result": None}

    # -- behaviour --
    def selected_index():
        return stage_list.currentRow()

    def refresh_stage_list(select=None):
        stage_list.blockSignals(True)
        stage_list.clear()
        for name, a, b in model.stages:
            stage_list.addItem(f"{name}  (a={a:.2f}, b={b:.2f})")
        stage_list.blockSignals(False)
        if select is not None and 0 <= select < len(model.stages):
            stage_list.setCurrentRow(select)

    def show_result():
        idx = selected_index()
        val = model.result_upto(idx if idx >= 0 else len(model.stages) - 1)
        inspector.setPlainText(format_inspection(inspect_result(val)))
        if isinstance(val, np.ndarray) and val.ndim in (2, 3):
            qi = _to_qimage(val, QtGui)
            if qi is not None:
                view.set_pixmap(QtGui.QPixmap.fromImage(qi)); view.fit()
            state["result"] = val
            g = val if val.ndim == 2 else imgio.ensure_gray(val)
            hq = _to_qimage(histogram_image(np.clip(g, 0, 1)), QtGui)
            if hq is not None:
                hist_view.setPixmap(QtGui.QPixmap.fromImage(hq).scaled(
                    max(hist_view.width(), 256), 70, QtCore.Qt.IgnoreAspectRatio,
                    QtCore.Qt.SmoothTransformation))
        else:
            view.clear(); hist_view.clear(); state["result"] = None

    def on_stage_selected():
        i = selected_index()
        if 0 <= i < len(model.stages):
            _, a, b = model.stages[i]
            sa.blockSignals(True); sb.blockSignals(True)
            sa.setValue(int(a * 100)); sb.setValue(int(b * 100))
            sa.blockSignals(False); sb.blockSignals(False)
            la.setText(f"a: {a:.2f}"); lb.setText(f"b: {b:.2f}")
        show_result()

    def on_knob(_=None):
        i = selected_index()
        if 0 <= i < len(model.stages):
            model.set_knobs(i, a=sa.value() / 100.0, b=sb.value() / 100.0)
            la.setText(f"a: {sa.value()/100:.2f}"); lb.setText(f"b: {sb.value()/100:.2f}")
            refresh_stage_list(select=i)
            show_result()

    def add_op(item):
        model.add_stage(item.data(QtCore.Qt.UserRole))
        refresh_stage_list(select=len(model.stages) - 1)
        show_result()

    def load_sample(idx):
        if idx <= 0:
            return
        model.load_recipe(samples.itemText(idx))
        refresh_stage_list(select=len(model.stages) - 1)
        show_result()

    def remove():
        i = selected_index()
        if 0 <= i < len(model.stages):
            model.remove_stage(i); refresh_stage_list(); show_result()

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

    op_list.itemDoubleClicked.connect(add_op)
    samples.currentIndexChanged.connect(load_sample)
    stage_list.currentRowChanged.connect(lambda _=None: on_stage_selected())
    sa.valueChanged.connect(on_knob); sb.valueChanged.connect(on_knob)
    b_rm.clicked.connect(remove); b_up.clicked.connect(lambda: move(-1)); b_dn.clicked.connect(lambda: move(1))
    b_load.clicked.connect(load_image); b_demo.clicked.connect(use_demo); b_save.clicked.connect(save_result)
    b_export.clicked.connect(export)
    b_zin.clicked.connect(lambda: view.zoom(1.25)); b_zout.clicked.connect(lambda: view.zoom(0.8))
    b_fit.clicked.connect(view.fit); b_11.clicked.connect(view.reset_zoom)

    refresh_stage_list(); show_result()
    return win, model


def main() -> int:
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win, _ = build_window()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
