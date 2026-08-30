"""Generate real Fullseye Studio screenshots for the Qiita article (dev tool).

Honest-disclosure discipline: every image is a genuine ``widget.grab()`` (or
``Q3DSurface.renderToImage``) of the live Studio UI built by ``studio.build_window()``
— no mockups, no compositing. Re-run this script to regenerate them all:

    py -3.11 tools/gen_studio_screenshots.py            # all shots
    py -3.11 tools/gen_studio_screenshots.py --shot main  # one shot (subprocess mode)

Shots (written to docs/articles/assets/, with *_thumb.jpg 720px thumbnails):

  * ``studio_main.png``       — main window: coins sample + "Segment — blob / coin"
                                recipe applied, result displayed (offscreen grab).
  * ``studio_3d_surface.png`` — the rotatable Q3DSurface view Studio opens with
                                Ctrl+3, fed a real depth render of the Itokawa
                                Gaskell shape model (needs a real GL context, so
                                this shot runs on the native platform and uses
                                ``renderToImage`` — the same GL scene the mouse
                                rotates/zooms in the app).
  * ``studio_python_editor.png`` — the tabbed Python Editor with a real 3-D worked
                                example loaded and executed (F5), output streamed.
  * ``studio_3d_examples.png``— the 3-D Examples gallery (105 worked examples on
                                real Itokawa / skeleton-CT data) after a real Run.
  * ``studio_3d_ops.png``     — the 3-D Operators reference with a generated help page.

Each grab is validated (size + pixel variance) so a blank/black frame fails loudly
instead of shipping.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

OUT_DIR = os.path.join(_ROOT, "docs", "articles", "assets")

# shot name -> (needs_real_gl, description)
SHOTS = {
    "main":        (False, "Studio main window with a sample pipeline applied"),
    "surface3d":   (True,  "Ctrl+3 rotatable 3-D surface (Q3DSurface) of an Itokawa depth render"),
    "editor":      (False, "Python Editor (tabs + F5 run console)"),
    "examples3d":  (False, "3-D Examples gallery dialog after a real Run"),
    "ops3d":       (False, "3-D Operators reference dialog"),
}
FILENAMES = {
    "main": "studio_main.png",
    "surface3d": "studio_3d_surface.png",
    "editor": "studio_python_editor.png",
    "examples3d": "studio_3d_examples.png",
    "ops3d": "studio_3d_ops.png",
}


def _validate_and_thumb(path: str) -> None:
    """Fail loudly on a blank/black grab; otherwise write a 720px JPG thumbnail."""
    import numpy as np
    from PIL import Image
    im = Image.open(path).convert("RGB")
    a = np.asarray(im)
    if a.std() < 8.0:
        raise SystemExit("REJECT %s: near-uniform image (std=%.2f) — blank grab" % (path, a.std()))
    w, h = im.size
    if w < 600 or h < 400:
        raise SystemExit("REJECT %s: too small (%dx%d)" % (path, w, h))
    tw = 720
    th = max(1, round(h * tw / w))
    thumb = im.resize((tw, th), Image.LANCZOS)
    tpath = os.path.splitext(path)[0] + "_thumb.jpg"
    thumb.save(tpath, "JPEG", quality=85)
    print("OK  %s (%dx%d, std=%.1f)  thumb=%s" % (path, w, h, a.std(), os.path.basename(tpath)))


def _pump(app, n=8, ms=40):
    from PySide6 import QtCore, QtWidgets
    for _ in range(n):
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, ms)


def _build_offscreen_studio():
    """Build the Studio window on the offscreen platform with modals stubbed."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # the offscreen platform ships no system fonts (all text renders as tofu boxes);
    # point its freetype font database at the real Windows fonts so grabs are readable
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    from PySide6 import QtWidgets
    import studio
    studio.CONFIRM_HOOK = lambda *a, **k: True      # never block on a confirm modal
    studio.ERROR_HOOK = lambda parent, title, text: print("STUDIO ERROR:", title, text)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window()
    return app, win, model


def _wait_proc(app, holder, attr="_proc", timeout_s=120):
    """Pump the event loop until the dialog's QProcess finishes (F5 run)."""
    import time
    t0 = time.time()
    while getattr(holder, attr, None) is not None:
        _pump(app, 2, 50)
        if time.time() - t0 > timeout_s:
            raise SystemExit("run did not finish within %ds" % timeout_s)


# --------------------------------------------------------------------------- #
def shot_main(out_path: str) -> None:
    from PySide6 import QtWidgets
    app, win, model = _build_offscreen_studio()
    win.resize(1680, 1000)
    win.show(); _pump(app, 12)
    # real UI path: load the bundled coins sample image, then pick the
    # "Segment — blob / coin" recipe from the SAMPLE PIPELINES combo (the
    # currentIndexChanged handler loads it into the pipeline + Program panel).
    win._load_sample_image("coins"); _pump(app, 6)
    combos = [cb for cb in win.findChildren(QtWidgets.QComboBox)
              if cb.count() and cb.itemText(0).startswith("— load a sample")]
    assert combos, "sample-pipelines combo not found"
    combo = combos[0]
    target = [i for i in range(combo.count())
              if combo.itemText(i) == "Segment — blob / coin"]
    assert target, "recipe 'Segment — blob / coin' not in combo"
    combo.setCurrentIndex(target[0]); _pump(app, 20)
    # tune the sample through the Program panel (the normal Studio workflow): the
    # shipped recipe's Otsu mask merges the bright top band into one blob on this
    # image, so open the discs and drop border-touching regions -> 21 clean coins.
    win._program["edit"].setPlainText(
        "gaussian (0.300, 0.000)\n"
        "otsu (0.500, 0.500)\n"
        "opening_circle (0.600, 0.500)\n"
        "sk_clear_border (0.500, 0.500)\n")
    win._program["apply"](); _pump(app, 20)
    # HDevelop-style region overlay (the segmented coins painted over the input)
    disp = [cb for cb in win.findChildren(QtWidgets.QComboBox)
            if any(cb.itemText(i) == "region overlay" for i in range(cb.count()))]
    if disp:
        disp[0].setCurrentText("region overlay"); _pump(app, 10)
    win._actions["fit"].trigger(); _pump(app, 10)      # Ctrl+0: fit image to the view
    win.grab().save(out_path)


def shot_editor(out_path: str) -> None:
    app, win, model = _build_offscreen_studio()
    win.show(); _pump(app, 8)
    import examples3d
    # open two real worked examples as tabs, run the curvature one (F5 path)
    code_a = examples3d.code("itokawa_curvature")
    code_b = examples3d.code("itokawa_pose_canonical")
    win._act_pyedit.trigger()          # Tools > Python Editor… (creates dialog + scratch tab)
    _pump(app, 8)
    pe = win._pyedit
    dlg = pe["dlg"]
    # replace the scratch tab contents with the real curvature example, add a 2nd tab
    pe["open_tab"](code_a, "itokawa_curvature.py")
    pe["open_tab"](code_b, "itokawa_pose_canonical.py")
    tabs = pe["tabs"]
    tabs.setCurrentIndex(tabs.count() - 2)          # focus the curvature tab
    _pump(app, 4)
    dlg.resize(1500, 950); _pump(app, 6)
    pe["run"]()                                     # F5: run in a subprocess
    _wait_proc(app, dlg)
    _pump(app, 8)
    dlg.grab().save(out_path)


def shot_examples3d(out_path: str) -> None:
    from PySide6 import QtCore, QtWidgets
    app, win, model = _build_offscreen_studio()
    win.show(); _pump(app, 8)
    win._act_3d_examples.trigger(); _pump(app, 8)
    dlg = win._ex3d_dlg
    lst = dlg.findChildren(QtWidgets.QListWidget)[0]
    # select the Itokawa curvature worked example (real JAXA Hayabusa data)
    for r in range(lst.count()):
        if lst.item(r).data(QtCore.Qt.UserRole) == "itokawa_curvature":
            lst.setCurrentRow(r); break
    _pump(app, 6)
    dlg.resize(1500, 900); _pump(app, 6)
    # really run it so the Output tab shows the ground-truth output (honest)
    for b in dlg.findChildren(QtWidgets.QPushButton):
        if b.text() in ("Run", "running…"):
            b.click(); break
    _wait_proc(app, dlg)
    _pump(app, 8)
    dlg.grab().save(out_path)


def shot_ops3d(out_path: str) -> None:
    from PySide6 import QtWidgets
    app, win, model = _build_offscreen_studio()
    win.show(); _pump(app, 8)
    win._act_3d_ops.trigger(); _pump(app, 10)
    dlg = win._ops3d["dialog"]
    # show a representative op's generated help page (registration/ICP family)
    lst = win._ops3d["list"]
    prefer = ("icp_register", "icp", "register_icp", "fpfh", "curvature3d")
    names = {}
    from PySide6 import QtCore
    for r in range(lst.count()):
        names[lst.item(r).data(QtCore.Qt.UserRole)] = r
    row = next((names[n] for n in prefer if n in names), 0)
    lst.setCurrentRow(row); _pump(app, 4)
    win._ops3d["show"](lst.item(row).data(QtCore.Qt.UserRole)); _pump(app, 8)
    dlg.resize(1500, 900); _pump(app, 8)
    dlg.grab().save(out_path)


def shot_surface3d(out_path: str) -> None:
    """The Ctrl+3 view: Q3DSurface of a real Itokawa depth render.

    Q3DSurface needs a real GL context (offscreen segfaults — see
    studio._opengl_available), so this shot runs on the native platform and uses
    QAbstract3DGraph.renderToImage: the same GL scene the user rotates/zooms with
    the mouse in the app, rendered to an FBO without flashing a window.
    """
    os.environ.pop("QT_QPA_PLATFORM", None)
    import numpy as np
    from PySide6 import QtWidgets
    import mesh
    import render3d
    import studio

    stl = os.path.join(_ROOT, "data", "sample_3d_cache", "itokawa_f0049152.stl")
    if not os.path.exists(stl):
        raise SystemExit("Itokawa STL cache missing: %s (run tools/gen_sample_3d.py itokawa)" % stl)
    V, F = mesh.read_mesh(stl)
    pose, K = render3d.auto_view(V, width=300, height=300)
    r = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=300, height=300)
    depth = np.asarray(r["depth"])
    cov = np.isfinite(depth)
    # height = camera-facing relief (near = high), background at the floor level
    h = np.zeros_like(depth)
    h[cov] = depth[cov].max() - depth[cov]
    heightmap = h * 1000.0                     # km -> m for readable axis labels

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    if not studio._opengl_available():
        raise SystemExit("no real GL context on this machine — surface3d shot impossible")

    from PySide6.QtDataVisualization import (Q3DSurface, QSurface3DSeries,
                                             QSurfaceDataProxy, QSurfaceDataItem)
    from PySide6 import QtGui, QtCore
    hm = studio._downsample_grid(heightmap)    # exactly what show_3d_surface plots
    ny, nx = hm.shape
    proxy = QSurfaceDataProxy()
    rows = []
    for i in range(ny):
        rows.append([QSurfaceDataItem(QtGui.QVector3D(float(j), float(hm[i, j]), float(i)))
                     for j in range(nx)])
    proxy.resetArray(rows)
    series = QSurface3DSeries(proxy)
    series.setDrawMode(QSurface3DSeries.DrawSurface)
    surface = Q3DSurface()
    surface.addSeries(series)
    # a mouse-rotated viewpoint (the same manipulation the user does by dragging)
    cam = surface.scene().activeCamera()
    cam.setCameraPosition(-135.0, 35.0, 130.0)     # azimuth, elevation, zoom%
    _pump(app, 6)
    img = surface.renderToImage(4, QtCore.QSize(1500, 950))
    if img.isNull():
        raise SystemExit("renderToImage returned a null image")
    img.save(out_path)


# --------------------------------------------------------------------------- #
def run_one(shot: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, FILENAMES[shot])
    {"main": shot_main, "editor": shot_editor, "examples3d": shot_examples3d,
     "ops3d": shot_ops3d, "surface3d": shot_surface3d}[shot](out_path)
    _validate_and_thumb(out_path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shot", choices=sorted(SHOTS), help="run ONE shot in this process")
    ap.add_argument("--only", help="comma-separated subset for the orchestrator")
    args = ap.parse_args()
    if args.shot:
        run_one(args.shot)
        return 0
    wanted = args.only.split(",") if args.only else list(SHOTS)
    failures = []
    for s in wanted:
        print("--- shot:", s, "-", SHOTS[s][1])
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--shot", s],
                           env=env, cwd=_ROOT)
        if p.returncode != 0:
            failures.append(s)
            print("FAILED:", s, "(exit %d)" % p.returncode)
    if failures:
        print("failed shots:", ", ".join(failures))
        return 1
    print("all shots done ->", OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
