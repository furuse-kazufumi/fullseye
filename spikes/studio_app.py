"""Fullseye Studio — 最小骨組み(PySide6 + matplotlib 埋め込み).

ユーザーの理想(2026-08-18):「私が走らせて実際に動いている姿が見れる環境」の GUI 版。
HDevelop 風の 3 ペイン: 左=サンプル一覧(domain 別) / 中=コード編集 / 右=描画ペイン。
**サンプルを選ぶ→コードが出る→Run で即描画。コードを編集して Run すれば結果が変わる**
(= HDevelop の肝。exec ベースの素朴実装だが「書く→走らせる→見る」ループが閉じる)。

  実行(GUI):   PYTHONPATH=. py -3.11 spikes/studio_app.py
  smoke(無表示): PYTHONPATH=. QT_QPA_PLATFORM=offscreen py -3.11 spikes/studio_app.py --smoke

★棲み分け(既存 spike と一貫): vision=fullseye が計算 / sim-source=物理が供給。
★これは additive な spike(既存 809 op 無変更・throwaway 可)。将来 packages/studio/ へ昇格。
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

import matplotlib
from matplotlib import font_manager
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PySide6 import QtWidgets, QtGui, QtCore

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lidar_adapter_spike as _sim  # noqa: E402
import unified_api_spike as _vis  # noqa: E402
import fullseye as fs  # noqa: E402

# 日本語フォント(既定 DejaVu Sans は CJK 無し)。
for _jp in ("Yu Gothic", "Meiryo", "MS Gothic"):
    if _jp in {f.name for f in font_manager.fontManager.ttflist}:
        matplotlib.rcParams["font.family"] = _jp
        break
matplotlib.rcParams["axes.unicode_minus"] = False


def synthetic_scene(h: int = 96, w: int = 128) -> np.ndarray:
    """エッジがはっきり見える合成グレー画像(矩形 2 + 円)。"""
    img = np.full((h, w), 0.15)
    img[20:50, 24:60] = 0.8
    img[55:80, 80:112] = 0.55
    yy, xx = np.mgrid[0:h, 0:w]
    img[(yy - 40) ** 2 + (xx - 96) ** 2 < 14 ** 2] = 0.95
    return img


def box_surface(nx: int = 8, half=(0.15, 0.1, 0.12)) -> np.ndarray:
    """箱の 6 面に点を撒いた表面点群(PPF 6-DoF pose のモデル/シーン用)。"""
    u = np.linspace(-1, 1, nx)
    a, b = np.meshgrid(u, u)
    a, b, o = a.ravel(), b.ravel(), np.ones(nx * nx)
    hx, hy, hz = half
    faces = [
        np.column_stack([a * hx, b * hy, o * hz]), np.column_stack([a * hx, b * hy, -o * hz]),
        np.column_stack([a * hx, o * hy, b * hz]), np.column_stack([a * hx, -o * hy, b * hz]),
        np.column_stack([o * hx, a * hy, b * hz]), np.column_stack([-o * hx, a * hy, b * hz]),
    ]
    return np.unique(np.vstack(faces), axis=0)


def stereo_pair(h: int = 64, w: int = 96, bg_disp: int = 3, fg_disp: int = 9):
    """既知視差の合成ステレオ対(前景ブロックほど大きくずれる=近い)。texture 有りで SGM が効く。"""
    rng = np.random.default_rng(1)
    tex = rng.random((h, w + fg_disp + 4))
    left = tex[:, fg_disp + 4:fg_disp + 4 + w].copy()
    right = np.roll(tex, bg_disp, axis=1)[:, fg_disp + 4:fg_disp + 4 + w].copy()
    fg = (slice(18, 46), slice(30, 66))                       # 近い前景ブロック
    right[fg] = np.roll(tex, fg_disp, axis=1)[:, fg_disp + 4:fg_disp + 4 + w][fg]
    return left, right


# ── サンプル(name, domain, 実行可能コード)──────────────────────────────────── #
# コードは名前空間(fig/np/fs/Image/sim/LidarPattern/SCENE/synthetic_scene)の下で exec され、
# fig に subplot を足して描画する契約。編集して Run すれば結果が変わる。
_IMAGE_CHAIN = '''\
# vision: 画像チェーン(sigma / level スライダで即再描画。コード編集も可)
img = synthetic_scene()
chain = [
    ("input",                 img),
    (f"gaussian({sigma:.2f})", Image(img).gaussian(sigma).array),
    ("sobel",                 Image(img).gaussian(sigma).sobel().array),
    (f"threshold({level:.2f})", Image(img).gaussian(sigma).sobel().threshold(level).array),
]
for i, (title, arr) in enumerate(chain):
    ax = fig.add_subplot(2, 2, i + 1)
    ax.imshow(arr, cmap="gray", vmin=0, vmax=1)
    ax.set_title(title, fontsize=9); ax.axis("off")
'''

_CLOUD_PERCEIVE = '''\
# vision: 点群から床を除去して物体クラスタを取り出す(cluster_tol スライダ)
rng = np.random.default_rng(0)
xs, ys = np.meshgrid(np.linspace(-1, 1, 30), np.linspace(-1, 1, 30))
floor = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
blob = rng.normal([0.4, 0.4, 0.5], 0.03, (60, 3))
pts = np.vstack([floor + rng.normal(0, 0.002, floor.shape), blob])
ng, gmask = fs.remove_ground(pts, thresh=0.03)
clusters = fs.euclidean_clusters(ng, tol=cluster_tol, min_size=5)
ax = fig.add_subplot(111, projection="3d")
ax.scatter(pts[gmask][:, 0], pts[gmask][:, 1], pts[gmask][:, 2], s=2, c="0.7")
for idx in clusters:
    c = ng[idx]; ax.scatter(c[:, 0], c[:, 1], c[:, 2], s=12)
    cen = fs.centroid(c); ax.scatter(*cen, s=120, marker="*", edgecolor="k")
ax.set_title(f"床除去 {int(gmask.sum())} 点 -> 物体 {len(clusters)}", fontsize=9)
'''

_SIM_LIDAR = '''\
# sim-source: 物理エンジンから LiDAR 1 スキャン(h_res / v_res スライダで解像度可変)
scene = sim.MuJoCo(SCENE)
pts = scene.lidar(origin=(0, 0, 1.0), pattern=LidarPattern(h_res=h_res, v_res=v_res))
ax = fig.add_subplot(111, projection="3d")
ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=2, c=pts[:, 2], cmap="viridis")
ax.scatter(0, 0, 1.0, s=80, marker="^", color="red")
ax.set_xlim(-3, 3); ax.set_ylim(-3, 3); ax.set_zlim(0, 1.2); ax.view_init(28, -60)
ax.set_title(f"LiDAR {h_res}x{v_res} -> ヒット {len(pts)} 点(真値)", fontsize=9)
'''

_SIM_TO_VISION = '''\
# sim-source -> vision: LiDAR 点群を fullseye 知覚 op に渡す分業ループ
import matplotlib.pyplot as _plt
scene = sim.MuJoCo(SCENE)
pts = scene.lidar(origin=(0, 0, 1.0))                    # 物理が供給
ng, gmask = fs.remove_ground(pts, thresh=ground_thresh)  # fullseye が計算
clusters = fs.euclidean_clusters(ng, tol=cluster_tol, min_size=5)
ax = fig.add_subplot(111, projection="3d")
ax.scatter(pts[gmask][:, 0], pts[gmask][:, 1], pts[gmask][:, 2], s=1, c="0.7")
cols = _plt.cm.tab10(np.linspace(0, 1, max(len(clusters), 1)))
for i, idx in enumerate(clusters):
    c = ng[idx]; ax.scatter(c[:, 0], c[:, 1], c[:, 2], s=8, color=cols[i])
    cen = fs.centroid(c); ax.scatter(*cen, s=140, marker="*", color=cols[i], edgecolor="k")
ax.scatter(0, 0, 1.0, s=80, marker="^", color="red")
ax.set_xlim(-3, 3); ax.set_ylim(-3, 3); ax.set_zlim(0, 1.2); ax.view_init(28, -60)
ax.set_title(f"sim LiDAR -> 床除去 -> 物体 {len(clusters)}", fontsize=9)
'''

_IMAGE_HWV = '''\
# vision (hwv 風): 入力画像に検出領域を重ねて表示(HDevelop の "display object over image")
# 画像上をマウスで hover するとステータスバーに画素座標と値が出ます(HWindow のピクセル検査)。
img = synthetic_scene()
edges = Image(img).gaussian(sigma).sobel().threshold(level).array
ax = fig.add_subplot(111)
ax.imshow(img, cmap="gray", vmin=0, vmax=1)
overlay = np.zeros((*edges.shape, 4))
overlay[edges > 0] = (1.0, 0.25, 0.1, 0.9)     # 検出エッジ領域を赤で重畳
ax.imshow(overlay)
ax.set_title(f"入力 + 検出領域(sigma={sigma:.2f}, level={level:.2f}) — hover で画素値", fontsize=9)
ax.axis("off")
'''

_POSE_6DOF = '''\
# vision: PPF で 6-DoF 姿勢推定(evis 把持の核心)。モデル箱を既知回転で置いたシーンに当てる
model = box_surface()
th = np.radians(rot_deg)
Rt = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1.0]])
tt = np.array([0.4, 0.2, 0.5])
rng = np.random.default_rng(0)
scene = model @ Rt.T + tt + rng.normal(0, noise, model.shape)
pose = fs.find_surface_pose(model, scene)                 # {R, t, rmse, votes, inlier_fraction}
R, t = pose["R"], pose["t"]
ax = fig.add_subplot(111, projection="3d")
ax.scatter(scene[:, 0], scene[:, 1], scene[:, 2], s=6, c="0.6")
for k, col in enumerate("rgb"):                            # 推定フレーム軸を描く
    v = R @ np.eye(3)[:, k] * 0.25
    ax.plot([t[0], t[0] + v[0]], [t[1], t[1] + v[1]], [t[2], t[2] + v[2]], color=col, lw=2)
ang = np.degrees(np.arccos(np.clip((np.trace(R.T @ Rt) - 1) / 2, -1, 1)))
ax.set_title(f"6-DoF pose  角度誤差 {ang:.1f}deg  inlier {pose['inlier_fraction']:.2f}", fontsize=9)
ax.set_xlim(0, 0.8); ax.set_ylim(0, 0.6); ax.set_zlim(0.2, 0.9); ax.view_init(24, -60)
'''

_STEREO_DEPTH = '''\
# vision: ステレオ視差(SGM)。左右画像から disparity を計算(近い前景ほど大きい)
left, right = stereo_pair()
disp = fs.disparity_sgm(left, right, max_disp=max_disp, window=5)
ax1 = fig.add_subplot(1, 2, 1); ax1.imshow(left, cmap="gray"); ax1.set_title("left", fontsize=9); ax1.axis("off")
ax2 = fig.add_subplot(1, 2, 2)
im = ax2.imshow(disp, cmap="turbo"); ax2.set_title("disparity (SGM)", fontsize=9); ax2.axis("off")
fig.colorbar(im, ax=ax2, fraction=0.046)
'''

# 各サンプル: name, domain, code, params[(name, lo, hi, default, is_int)]
SAMPLES = [
    {"name": "image.chain", "domain": "vision", "code": _IMAGE_CHAIN,
     "params": [("sigma", 0.2, 4.0, 1.4, False), ("level", 0.05, 0.6, 0.25, False)]},
    {"name": "image.hwv", "domain": "vision", "code": _IMAGE_HWV,
     "params": [("sigma", 0.2, 4.0, 1.4, False), ("level", 0.05, 0.6, 0.25, False)]},
    {"name": "cloud.perceive", "domain": "vision", "code": _CLOUD_PERCEIVE,
     "params": [("cluster_tol", 0.05, 0.3, 0.1, False)]},
    {"name": "pose.6dof", "domain": "vision", "code": _POSE_6DOF,
     "params": [("rot_deg", 0.0, 60.0, 25.0, False), ("noise", 0.0, 0.02, 0.005, False)]},
    {"name": "stereo.depth", "domain": "vision", "code": _STEREO_DEPTH,
     "params": [("max_disp", 8, 24, 16, True)]},
    {"name": "sim.lidar", "domain": "sim-source", "code": _SIM_LIDAR,
     "params": [("h_res", 30, 200, 120, True), ("v_res", 6, 40, 24, True)]},
    {"name": "sim.to_vision", "domain": "sim-source", "code": _SIM_TO_VISION,
     "params": [("ground_thresh", 0.01, 0.1, 0.03, False), ("cluster_tol", 0.1, 0.5, 0.25, False)]},
]


class _ParamSlider(QtWidgets.QWidget):
    """float/int を扱う 1 パラメータのスライダ + 現在値ラベル(HDevelop 風の即応 UI)。"""

    def __init__(self, spec, on_change) -> None:
        super().__init__()
        self.name, self.lo, self.hi, default, self.is_int = spec
        self._on_change = on_change
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setValue(self._to_slider(default))
        self.label = QtWidgets.QLabel()
        self._update_label()
        self.slider.valueChanged.connect(self._changed)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QtWidgets.QLabel(self.name), 2)
        lay.addWidget(self.slider, 5)
        lay.addWidget(self.label, 2)

    def _to_slider(self, v):
        return int(round((v - self.lo) / (self.hi - self.lo) * 1000))

    def value(self):
        v = self.lo + self.slider.value() / 1000 * (self.hi - self.lo)
        return int(round(v)) if self.is_int else v

    def _update_label(self):
        v = self.value()
        self.label.setText(f"{v}" if self.is_int else f"{v:.3f}")

    def _changed(self):
        self._update_label()
        self._on_change()


class StudioWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fullseye Studio (prototype)")
        self.resize(1240, 680)
        self._by_name = {s["name"]: s for s in SAMPLES}
        self._sliders: list[_ParamSlider] = []
        self._suspend = False  # スライダ再構築中の連鎖 run 抑止

        # 左: サンプル一覧(domain 別ツリー)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["samples"])
        self.tree.setMinimumWidth(200)
        groups: dict[str, QtWidgets.QTreeWidgetItem] = {}
        for s in SAMPLES:
            if s["domain"] not in groups:
                g = QtWidgets.QTreeWidgetItem(self.tree, [s["domain"]])
                g.setExpanded(True)
                groups[s["domain"]] = g
            item = QtWidgets.QTreeWidgetItem(groups[s["domain"]], [s["name"]])
            item.setData(0, 0x0100, s["name"])  # Qt.UserRole = sample name
        self.tree.itemSelectionChanged.connect(self._on_select)

        # 中: コード編集 + パラメータパネル + Run
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setFont(QtGui.QFont("Consolas", 10))
        self.editor.setMinimumWidth(360)
        self.param_box = QtWidgets.QGroupBox("parameters(動かすと即再描画)")
        self.param_form = QtWidgets.QVBoxLayout(self.param_box)
        run_btn = QtWidgets.QPushButton("Run  ▶")
        run_btn.clicked.connect(self._run)
        mid = QtWidgets.QWidget()
        ml = QtWidgets.QVBoxLayout(mid)
        ml.addWidget(QtWidgets.QLabel("code(編集して Run)"))
        ml.addWidget(self.editor, 3)
        ml.addWidget(self.param_box)
        ml.addWidget(run_btn)

        # 右: matplotlib 描画ペイン
        self.figure = Figure(figsize=(5, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)  # hwv 風ピクセル検査
        right = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(right)
        rl.addWidget(NavigationToolbar2QT(self.canvas, right))
        rl.addWidget(self.canvas)

        split = QtWidgets.QSplitter()
        split.addWidget(self.tree)
        split.addWidget(mid)
        split.addWidget(right)
        split.setSizes([200, 400, 620])
        self.setCentralWidget(split)
        self.statusBar().showMessage("サンプルを選んで Run")

        self.tree.setCurrentItem(groups["vision"].child(0))

    def _on_hover(self, event) -> None:
        """hwv 風: 画像(AxesImage)上の hover で画素座標と値をステータスバーに表示。"""
        ax = event.inaxes
        if ax is None or not ax.images or event.xdata is None:
            return
        arr = ax.images[0].get_array()          # 最下層(=元画像)の配列
        col, row = int(round(event.xdata)), int(round(event.ydata))
        if 0 <= row < arr.shape[0] and 0 <= col < arr.shape[1]:
            v = arr[row, col]
            vs = f"{float(v):.3f}" if np.ndim(v) == 0 else np.array2string(np.asarray(v), precision=2)
            self.statusBar().showMessage(f"hwv  pixel (x={col}, y={row})  value={vs}")

    def _current_sample(self):
        items = self.tree.selectedItems()
        if items and items[0].data(0, 0x0100):
            return self._by_name.get(items[0].data(0, 0x0100))
        return None

    def _rebuild_params(self, sample) -> None:
        self._suspend = True
        for sl in self._sliders:
            sl.setParent(None)
        self._sliders.clear()
        for spec in sample.get("params", []):
            sl = _ParamSlider(spec, self._run)
            self.param_form.addWidget(sl)
            self._sliders.append(sl)
        self.param_box.setVisible(bool(self._sliders))
        self._suspend = False

    def _on_select(self) -> None:
        sample = self._current_sample()
        if sample:
            self.editor.setPlainText(sample["code"])
            self._rebuild_params(sample)
            self._run()

    def _run(self) -> None:
        if self._suspend:
            return
        code = self.editor.toPlainText()
        self.figure.clear()
        ns = {
            "fig": self.figure, "np": np, "fs": fs,
            "Image": _vis.Image, "sim": _sim.sim, "LidarPattern": _sim.LidarPattern,
            "SCENE": _sim.SCENE, "synthetic_scene": synthetic_scene,
        }
        for sl in self._sliders:            # スライダ値を名前空間へ注入
            ns[sl.name] = sl.value()
        try:
            exec(code, ns)  # noqa: S102 — ローカル GUI・ユーザー自身のコード
            self.canvas.draw()
            self.statusBar().showMessage("Run OK  |  " + "  ".join(
                f"{sl.name}={sl.value()}" for sl in self._sliders))
        except Exception:
            self.statusBar().showMessage("Run 失敗(下部トレース)")
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.02, 0.98, traceback.format_exc(), fontsize=7, va="top", family="monospace")
            ax.axis("off")
            self.canvas.draw()


def _smoke() -> int:
    """無表示で全サンプルを描画実行し、例外が無いことを確認(CI/検証用)。"""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win = StudioWindow()
    ok = 0
    for s in SAMPLES:
        win.editor.setPlainText(s["code"])
        win._rebuild_params(s)
        win._run()
        msg = win.statusBar().currentMessage()
        print(f"  {s['name']:16s} -> {msg}")
        ok += msg.startswith("Run OK")
    out = Path(__file__).resolve().parent / "out_gallery" / "studio_app_smoke.png"
    out.parent.mkdir(exist_ok=True)
    win.figure.savefig(out, dpi=110)
    print(f"[smoke] {ok}/{len(SAMPLES)} OK, last render -> {out}")
    app.quit()
    return 0 if ok == len(SAMPLES) else 1


def main() -> None:
    if "--smoke" in sys.argv:
        raise SystemExit(_smoke())
    app = QtWidgets.QApplication(sys.argv)
    win = StudioWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
