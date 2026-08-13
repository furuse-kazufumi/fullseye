"""Fullseye Studio — an HDevelop-style visual pipeline workbench (PySide6).

Interactively build an operator pipeline, tune each stage's two knobs, watch the
intermediate result update live, and export the pipeline as a `--ops` string or as
Python. It is a thin front-end over the `fullseye` API; the pipeline logic lives in
`PipelineModel` (no Qt) so it can be tested headless.

    py -3.11 studio.py            # or: fullseye-studio  (installed console script)

Left: searchable operator browser. Centre: the pipeline (add/remove/reorder) with
a,b sliders for the selected stage. Right: the image after the selected stage.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import api
import imgio


# --------------------------------------------------------------------------- #
# Headless pipeline logic (no Qt) — unit-testable.
# --------------------------------------------------------------------------- #
class PipelineModel:
    """An ordered list of (op, a, b) stages applied to a base image."""

    def __init__(self, image=None):
        self.image = None if image is None else np.asarray(image, np.float64)
        self.stages: list[list] = []          # [ [name, a, b], ... ]

    # -- editing --
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

    # -- evaluation --
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

    # -- export --
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
    bars (headless — used by the Studio's histogram panel, testable on its own)."""
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
    """Sort-aware inspection of a pipeline result — the Studio's variable / image /
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


# --------------------------------------------------------------------------- #
# Qt view (imported lazily so `import studio` works without a display).
# --------------------------------------------------------------------------- #
def _to_qimage(arr, QtGui):
    """numpy image/region/color -> QImage (scalar/contour finals handled by caller)."""
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


def build_window(model=None):
    """Construct (but do not exec) the main window. Returns (window, model)."""
    from PySide6 import QtWidgets, QtGui, QtCore

    model = model or PipelineModel(demo_image())

    win = QtWidgets.QMainWindow()
    win.setWindowTitle("Fullseye Studio")
    win.resize(1180, 720)
    central = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
    win.setCentralWidget(central)

    # -- left: operator browser --
    left = QtWidgets.QWidget(); lv = QtWidgets.QVBoxLayout(left)
    search = QtWidgets.QLineEdit(); search.setPlaceholderText("search operators...")
    op_list = QtWidgets.QListWidget()
    lv.addWidget(QtWidgets.QLabel("Operators (double-click to add)"))
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

    # -- right: image view + histogram + info --
    right = QtWidgets.QWidget(); rv = QtWidgets.QVBoxLayout(right)
    view = QtWidgets.QLabel("(load an image or use the synthetic demo)")
    view.setAlignment(QtCore.Qt.AlignCenter); view.setMinimumSize(360, 360)
    view.setStyleSheet("background:#202020;color:#aaa;")
    hist_view = QtWidgets.QLabel(); hist_view.setFixedHeight(72)
    hist_view.setStyleSheet("background:#181818;")
    info = QtWidgets.QLabel(""); info.setWordWrap(True)
    b_load = QtWidgets.QPushButton("Load image..."); b_demo = QtWidgets.QPushButton("Synthetic demo")
    b_save = QtWidgets.QPushButton("Save result...")
    rload = QtWidgets.QHBoxLayout()
    rload.addWidget(b_load); rload.addWidget(b_demo); rload.addWidget(b_save)
    rv.addLayout(rload); rv.addWidget(view, 1)
    rv.addWidget(QtWidgets.QLabel("Histogram")); rv.addWidget(hist_view); rv.addWidget(info)
    state = {"result": None}

    central.addWidget(left); central.addWidget(mid); central.addWidget(right)
    central.setSizes([300, 340, 540])

    # -- behaviour --
    def selected_index():
        return stage_list.currentRow()

    def refresh_stage_list():
        stage_list.blockSignals(True)
        stage_list.clear()
        for name, a, b in model.stages:
            stage_list.addItem(f"{name}  (a={a:.2f}, b={b:.2f})")
        stage_list.blockSignals(False)

    def show_result():
        idx = selected_index()
        val = model.result_upto(idx if idx >= 0 else len(model.stages) - 1)
        if isinstance(val, np.ndarray) and val.ndim in (2, 3):
            qi = _to_qimage(val, QtGui)
            if qi is not None:
                pm = QtGui.QPixmap.fromImage(qi).scaled(
                    view.width(), view.height(), QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation)
                view.setPixmap(pm)
            info.setText(f"array {val.shape}  range [{float(np.nanmin(val)):.3f}, "
                         f"{float(np.nanmax(val)):.3f}]")
            state["result"] = val
            g = val if val.ndim == 2 else imgio.ensure_gray(val)
            hq = _to_qimage(histogram_image(np.clip(g, 0, 1)), QtGui)
            if hq is not None:
                hist_view.setPixmap(QtGui.QPixmap.fromImage(hq).scaled(
                    max(hist_view.width(), 256), 72, QtCore.Qt.IgnoreAspectRatio,
                    QtCore.Qt.SmoothTransformation))
        elif isinstance(val, dict):
            view.setText("(contour result)")
            info.setText(f"contour: {len(val.get('cs', []))} contours")
            state["result"] = None; hist_view.clear()
        else:
            view.setText(str(val))
            info.setText("feature (scalar) result")
            state["result"] = None; hist_view.clear()

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
            refresh_stage_list(); stage_list.setCurrentRow(i)
            show_result()

    def add_op(item):
        model.add_stage(item.data(QtCore.Qt.UserRole))
        refresh_stage_list(); stage_list.setCurrentRow(len(model.stages) - 1)
        show_result()

    def remove():
        i = selected_index()
        if 0 <= i < len(model.stages):
            model.remove_stage(i); refresh_stage_list(); show_result()

    def move(delta):
        i = selected_index(); j = i + delta
        if 0 <= i < len(model.stages) and 0 <= j < len(model.stages):
            model.move_stage(i, j); refresh_stage_list(); stage_list.setCurrentRow(j); show_result()

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
        dlg = QtWidgets.QDialog(win); dlg.setWindowTitle("Export")
        v = QtWidgets.QVBoxLayout(dlg)
        te = QtWidgets.QPlainTextEdit()
        te.setPlainText("--ops \"" + model.ops_string() + "\"\n\n" + model.export_python())
        te.setReadOnly(True); v.addWidget(te)
        dlg.resize(560, 360); dlg.exec()

    op_list.itemDoubleClicked.connect(add_op)
    stage_list.currentRowChanged.connect(lambda _=None: on_stage_selected())
    sa.valueChanged.connect(on_knob); sb.valueChanged.connect(on_knob)
    b_rm.clicked.connect(remove)
    b_up.clicked.connect(lambda: move(-1)); b_dn.clicked.connect(lambda: move(1))
    b_load.clicked.connect(load_image); b_demo.clicked.connect(use_demo)
    b_save.clicked.connect(save_result)
    b_export.clicked.connect(export)

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
