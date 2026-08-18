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
import studio_ops_browser as _browser  # noqa: E402  (統一 registry から 600 op を自動列挙・実行・描画)
import viewer3d as _v3d  # noqa: E402  (Open3D 連携: 点群/6D pose の対話 3D ビューア=RViz2 相当)
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
    """既知視差の合成ステレオ対(前景ブロックほど大きくずれる=近い)。

    純ランダムだと SGM が誤マッチするので、テクスチャを軽く平滑化して局所的に一意にする
    (実ステレオでも smooth な自然テクスチャの方が対応が付きやすい)。"""
    from scipy import ndimage
    rng = np.random.default_rng(1)
    pad = fg_disp + 4
    tex = ndimage.gaussian_filter(rng.random((h, w + pad)), sigma=1.1)  # 平滑テクスチャ
    tex = (tex - tex.min()) / (tex.ptp() + 1e-9)
    left = tex[:, pad:pad + w].copy()
    right = np.roll(tex, bg_disp, axis=1)[:, pad:pad + w].copy()          # 背景=小視差
    fg = (slice(18, 46), slice(30, 66))                                  # 近い前景ブロック=大視差
    right[fg] = np.roll(tex, fg_disp, axis=1)[:, pad:pad + w][fg]
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

_GRASP_PIPELINE = '''\
# sim-source -> vision (evis 知覚パイプライン全体): LiDAR -> 床除去 -> クラスタ -> 各物体の
# 有向境界箱(OBB)で 6-DoF フレーム=把持候補。物理供給から把持姿勢まで一気通貫。
import matplotlib.pyplot as _plt
scene = sim.MuJoCo(SCENE)
pts = scene.lidar(origin=(0, 0, 1.0))
ng, gmask = fs.remove_ground(pts, thresh=ground_thresh)
clusters = fs.euclidean_clusters(ng, tol=0.25, min_size=6)
ax = fig.add_subplot(111, projection="3d")
ax.scatter(pts[gmask][:, 0], pts[gmask][:, 1], pts[gmask][:, 2], s=1, c="0.8")
cols = _plt.cm.tab10(np.linspace(0, 1, max(len(clusters), 1)))
widths = []
for i, idx in enumerate(clusters):
    c = ng[idx]; box = fs.obb(c); ctr = box["center"]
    ax.scatter(c[:, 0], c[:, 1], c[:, 2], s=7, color=cols[i])
    for k, ac in enumerate("rgb"):                       # OBB 軸=物体の 6-DoF フレーム
        v = box["axes"][:, k] * box["extents"][k] * axis_scale
        ax.plot([ctr[0], ctr[0]+v[0]], [ctr[1], ctr[1]+v[1]], [ctr[2], ctr[2]+v[2]], color=ac, lw=2)
    widths.append(2 * float(box["extents"].min()))       # 最小差し渡し=把持幅の目安
ax.scatter(0, 0, 1.0, s=80, marker="^", color="red")
ax.set_xlim(-3, 3); ax.set_ylim(-3, 3); ax.set_zlim(0, 1.2); ax.view_init(26, -60)
gw = ", ".join(f"{w:.2f}" for w in widths)
ax.set_title(f"grasp pipeline: {len(clusters)} 物体  把持幅[m]={gw}", fontsize=9)
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

_MORPHOLOGY = '''\
# vision: モルフォロジ(自然 API=下層 scipy 直呼び)。size スライダで構造要素サイズ可変
img = synthetic_scene()
noisy = img + (np.random.default_rng(0).random(img.shape) < noise) * 0.6   # 明ノイズを撒く
stages = [
    ("noisy input",              noisy),
    (f"opening({size})=ノイズ除去", Image(noisy).opening(size).array),
    (f"closing({size})=穴埋め",     Image(img).closing(size).array),
    (f"morph_gradient({size})=輪郭", Image(img).morph_gradient(size).array),
]
for i, (title, arr) in enumerate(stages):
    ax = fig.add_subplot(2, 2, i + 1)
    ax.imshow(arr, cmap="gray", vmin=0, vmax=1); ax.set_title(title, fontsize=9); ax.axis("off")
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
from scipy import ndimage
left, right = stereo_pair()
disp = fs.disparity_sgm(left, right, max_disp=max_disp, window=5)
disp_s = ndimage.median_filter(disp, size=5)              # 実 SGM 同様 speckle 除去
fg = disp[18:46, 30:66]; bg = np.r_[disp[:14].ravel(), disp[50:].ravel()]
ax1 = fig.add_subplot(1, 2, 1); ax1.imshow(left, cmap="gray"); ax1.set_title("left", fontsize=9); ax1.axis("off")
ax2 = fig.add_subplot(1, 2, 2)
im = ax2.imshow(disp_s, cmap="turbo")
ax2.set_title(f"disparity  前景 {np.median(fg):.1f} > 背景 {np.median(bg):.1f}", fontsize=9); ax2.axis("off")
fig.colorbar(im, ax=ax2, fraction=0.046)
'''

# 各サンプル: name, domain, code, params[(name, lo, hi, default, is_int)]
SAMPLES = [
    {"name": "image.chain", "domain": "vision", "code": _IMAGE_CHAIN,
     "params": [("sigma", 0.2, 4.0, 1.4, False), ("level", 0.05, 0.6, 0.25, False)]},
    {"name": "image.hwv", "domain": "vision", "code": _IMAGE_HWV,
     "params": [("sigma", 0.2, 4.0, 1.4, False), ("level", 0.05, 0.6, 0.25, False)]},
    {"name": "image.morphology", "domain": "vision", "code": _MORPHOLOGY,
     "params": [("size", 2, 9, 3, True), ("noise", 0.0, 0.1, 0.03, False)]},
    {"name": "cloud.perceive", "domain": "vision", "code": _CLOUD_PERCEIVE,
     "params": [("cluster_tol", 0.05, 0.3, 0.1, False)]},
    {"name": "pose.6dof", "domain": "vision", "code": _POSE_6DOF,
     "params": [("rot_deg", 0.0, 60.0, 25.0, False), ("noise", 0.0, 0.02, 0.005, False)]},
    {"name": "stereo.depth", "domain": "vision", "code": _STEREO_DEPTH,
     "params": [("max_disp", 8, 24, 16, True)]},
    {"name": "sim.lidar", "domain": "sim-source", "code": _SIM_LIDAR,
     "params": [("h_res", 30, 200, 120, True), ("v_res", 6, 40, 24, True)]},
    {"name": "sim.grasp_pipeline", "domain": "sim-source", "code": _GRASP_PIPELINE,
     "params": [("ground_thresh", 0.01, 0.1, 0.03, False), ("axis_scale", 1.0, 4.0, 2.0, False)]},
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
        self._active_op = None  # 統一 registry op を選択中なら UnifiedOp

        # 左: 検索ボックス + サンプル一覧(domain 別)+ 統一 registry の全 op 自動列挙(F6/F2)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("op 検索(名前 / doc / namespace)…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._on_search)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["samples / vision-ops"])
        self.tree.setMinimumWidth(220)
        self._reg_ops = {}
        self._first_item = None
        self._populate_tree("")
        self.tree.itemSelectionChanged.connect(self._on_select)
        left = QtWidgets.QWidget()
        left_l = QtWidgets.QVBoxLayout(left); left_l.setContentsMargins(0, 0, 0, 0)
        left_l.addWidget(self.search); left_l.addWidget(self.tree)

        # 中: コード編集 + パラメータパネル + Run
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setFont(QtGui.QFont("Consolas", 10))
        self.editor.setMinimumWidth(360)
        self.param_box = QtWidgets.QGroupBox("parameters(動かすと即再描画)")
        self.param_form = QtWidgets.QVBoxLayout(self.param_box)
        run_btn = QtWidgets.QPushButton("Run  ▶")
        run_btn.clicked.connect(self._run)
        # Open3D 対話 3D ビューア(点群/6D pose を mouse ナビ=RViz2 相当)
        self.open3d_btn = QtWidgets.QPushButton("Open in 3D (Open3D)  🧊")
        self.open3d_btn.clicked.connect(self._open3d)
        self.open3d_btn.setEnabled(False)
        self._last3d = None  # geometry list: 直近 op の 3D 化可能な出力
        self._last3d_title = None                # その op 名(3D 窓タイトル用)
        self.viewer_mgr = _v3d.ViewerManager()   # 開いている 3D 窓(別プロセス)を管理
        btn_row = QtWidgets.QWidget()
        bl = QtWidgets.QHBoxLayout(btn_row); bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(run_btn, 2); bl.addWidget(self.open3d_btn, 2)

        # 3D 窓マネージャ(一覧 / 選択を閉じる / 全部閉じる / 環境状態)
        self.win3d_box = QtWidgets.QGroupBox("3D 窓マネージャ")
        w3l = QtWidgets.QVBoxLayout(self.win3d_box)
        self.win3d_list = QtWidgets.QListWidget()
        self.win3d_list.setMaximumHeight(96)
        self.win3d_list.itemDoubleClicked.connect(lambda _: self._close_selected_3d())
        w3l.addWidget(self.win3d_list)
        w3btns = QtWidgets.QWidget()
        w3b = QtWidgets.QHBoxLayout(w3btns); w3b.setContentsMargins(0, 0, 0, 0)
        self.win3d_close_btn = QtWidgets.QPushButton("選択を閉じる")
        self.win3d_close_btn.clicked.connect(self._close_selected_3d)
        self.win3d_closeall_btn = QtWidgets.QPushButton("全部閉じる")
        self.win3d_closeall_btn.clicked.connect(self._close_all_3d)
        self.win3d_refresh_btn = QtWidgets.QPushButton("更新")
        self.win3d_refresh_btn.clicked.connect(self._refresh_3d_windows)
        w3b.addWidget(self.win3d_close_btn); w3b.addWidget(self.win3d_closeall_btn)
        w3b.addWidget(self.win3d_refresh_btn)
        w3l.addWidget(w3btns)
        self.win3d_status = QtWidgets.QLabel()
        self.win3d_status.setWordWrap(True)
        self.win3d_status.setStyleSheet("color:#888; font-size:11px;")
        w3l.addWidget(self.win3d_status)

        # sim-source パネル: 任意 MuJoCo モデル(MJCF)を 3D で見る(F6 sim ドメイン)
        self.sim_box = QtWidgets.QGroupBox("sim モデルを 3D で見る(MJCF)")
        sl = QtWidgets.QVBoxLayout(self.sim_box)
        self.sim_path = QtWidgets.QLineEdit()
        self.sim_path.setPlaceholderText(".xml (MJCF) のパスを入力 …")
        sl.addWidget(self.sim_path)
        sbtns = QtWidgets.QWidget()
        sb = QtWidgets.QHBoxLayout(sbtns); sb.setContentsMargins(0, 0, 0, 0)
        self.sim_mesh_btn = QtWidgets.QPushButton("実形状で見る 🧊")
        self.sim_mesh_btn.clicked.connect(lambda: self._view_mjcf("mesh"))
        self.sim_cloud_btn = QtWidgets.QPushButton("点群で見る 🧊")
        self.sim_cloud_btn.clicked.connect(lambda: self._view_mjcf("cloud"))
        sb.addWidget(self.sim_mesh_btn); sb.addWidget(self.sim_cloud_btn)
        sl.addWidget(sbtns)
        mid = QtWidgets.QWidget()
        ml = QtWidgets.QVBoxLayout(mid)
        ml.addWidget(QtWidgets.QLabel("code(編集して Run)"))
        ml.addWidget(self.editor, 3)
        ml.addWidget(self.param_box)
        ml.addWidget(btn_row)
        ml.addWidget(self.sim_box)
        ml.addWidget(self.win3d_box)
        self._refresh_3d_windows()

        # 右: matplotlib 描画ペイン
        self.figure = Figure(figsize=(5, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)  # hwv 風ピクセル検査
        right = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(right)
        rl.addWidget(NavigationToolbar2QT(self.canvas, right))
        rl.addWidget(self.canvas)

        split = QtWidgets.QSplitter()
        split.addWidget(left)
        split.addWidget(mid)
        split.addWidget(right)
        split.setSizes([220, 400, 620])
        self.setCentralWidget(split)
        self.statusBar().showMessage("サンプルを選んで Run")

        if self._first_item is not None:
            self.tree.setCurrentItem(self._first_item)

    def _populate_tree(self, filt: str = "") -> None:
        """ツリーを(検索語で絞って)再構築。samples + 統一 registry の op を namespace 別に。"""
        self.tree.clear()
        self._reg_ops = {}
        self._first_item = None
        q = (filt or "").strip().lower()
        # サンプル(名前/domain で絞る)
        groups: dict = {}
        for s in SAMPLES:
            if q and q not in s["name"].lower() and q not in s.get("domain", "").lower():
                continue
            if s["domain"] not in groups:
                g = QtWidgets.QTreeWidgetItem(self.tree, [s["domain"]]); g.setExpanded(True)
                groups[s["domain"]] = g
            it = QtWidgets.QTreeWidgetItem(groups[s["domain"]], [s["name"]])
            it.setData(0, 0x0100, s["name"])
            if self._first_item is None:
                self._first_item = it
        # 統一 registry の op(名前/doc/namespace で絞る = reg.find)
        reg = _browser.ops
        mset = {o.name for o in reg.find(q)} if q else None
        vcount = len(mset) if mset is not None else len(reg)
        vroot = QtWidgets.QTreeWidgetItem(self.tree, [f"vision-ops  ({vcount})"])
        vroot.setExpanded(bool(q))
        for ns in reg.namespaces():
            names = [n for n in reg.list(namespace=ns) if mset is None or n in mset]
            if not names:
                continue
            nsg = QtWidgets.QTreeWidgetItem(vroot, [f"{ns}  ({len(names)})"])
            nsg.setExpanded(bool(q))
            for name in names:
                key = f"op:{name}"
                self._reg_ops[key] = reg[name]
                it = QtWidgets.QTreeWidgetItem(nsg, [name])
                it.setData(0, 0x0100, key)
                if self._first_item is None:
                    self._first_item = it

    def _on_search(self, text: str) -> None:
        """検索語でツリーを絞り込む。"""
        self._populate_tree(text)
        n = len(self._reg_ops)
        self.statusBar().showMessage(f"検索 '{text}': {n} op 該当" if text else "検索クリア")

    def _open3d(self) -> None:
        """直近 op の 3D 出力を Open3D 対話ウィンドウで開く(mouse ナビ=RViz2 相当)。"""
        if not self._last3d:
            self.statusBar().showMessage("3D 化できる出力がありません(点群/6D pose を選択)")
            return
        if not _v3d.available():
            self.statusBar().showMessage("Open3D 未導入: pip install open3d")
            return
        # 別プロセスで起動し、マネージャで追跡(desktop 常用: 固めない/隔離/複数窓可)
        title = self._last3d_title or "Fullseye 3D"
        wid = self.viewer_mgr.launch(self._last3d, title=title)
        self._refresh_3d_windows()
        self.statusBar().showMessage(f"3D 窓を起動(#{wid}: {title})— Studio は操作継続可"
                                     if wid else "Open3D 起動失敗(desktop GL が要る)")

    def _refresh_3d_windows(self) -> None:
        """開いている 3D 窓の一覧を更新(死活プルーニング込み)+ 環境状態を表示。"""
        wins = self.viewer_mgr.windows()
        self.win3d_list.clear()
        for w in wins:
            self.win3d_list.addItem(f"#{w['id']}  {w['title']}   (pid {w['pid']})")
        has = bool(wins)
        self.win3d_close_btn.setEnabled(has)
        self.win3d_closeall_btn.setEnabled(has)
        if not _v3d.available():
            env = "環境: Open3D 未導入 → PLY 書き出しで外部ビューアへ(pip install open3d)"
        else:
            env = f"開いている窓: {len(wins)} 個  |  環境: desktop GL 窓 可(ダブルクリックで閉じる)"
        self.win3d_status.setText(env)

    def _close_selected_3d(self) -> None:
        """一覧で選択した 3D 窓を閉じる。"""
        row = self.win3d_list.currentRow()
        wins = self.viewer_mgr.windows()
        if 0 <= row < len(wins):
            self.viewer_mgr.close(wins[row]["id"])
            self._refresh_3d_windows()
            self.statusBar().showMessage("3D 窓を 1 つ閉じました")

    def _close_all_3d(self) -> None:
        """管理下の 3D 窓を全部閉じる。"""
        n = self.viewer_mgr.close_all()
        self._refresh_3d_windows()
        self.statusBar().showMessage(f"3D 窓を {n} 個閉じました")

    def _view_mjcf(self, mode: str) -> None:
        """MJCF を実形状(mesh)or 点群(cloud)で 3D 窓に表示(sim-source→viewer)。"""
        import os
        path = self.sim_path.text().strip().strip('"')
        if not path or not os.path.exists(path):
            self.statusBar().showMessage("MJCF (.xml) のパスが不正です")
            return
        if not _v3d.available():
            self.statusBar().showMessage("Open3D 未導入: pip install open3d")
            return
        try:
            src = fs.vision.sim.MuJoCo(path)
            name = os.path.basename(path)
            if mode == "mesh":
                geoms = src.scene_geometries()
                title = f"Fullseye 3D — {name}(実形状)"
            else:
                cloud = src.point_cloud(0) if src.cameras() else None
                if cloud is None:
                    self.statusBar().showMessage("このモデルに camera が無く点群にできません(実形状で表示を)")
                    src.close(); return
                geoms = _v3d.to_geometries(cloud, "point_cloud")
                title = f"Fullseye 3D — {name}(点群)"
            src.close()
        except Exception as e:  # noqa: BLE001
            self.statusBar().showMessage(f"MJCF 読み込み失敗: {e}")
            return
        wid = self.viewer_mgr.launch(geoms, title=title)
        self._refresh_3d_windows()
        self.statusBar().showMessage(f"3D 窓 #{wid}: {title}" if wid else "3D 起動失敗(desktop GL)")

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

    def _current_key(self):
        items = self.tree.selectedItems()
        return items[0].data(0, 0x0100) if items else None

    def _current_sample(self):
        key = self._current_key()
        return self._by_name.get(key) if key else None

    def _current_op(self):
        key = self._current_key()
        return self._reg_ops.get(key) if key else None

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
        self._active_op = None
        self._last3d = None
        self.open3d_btn.setEnabled(False)
        sample = self._current_sample()
        if sample:
            self.editor.setPlainText(sample["code"])
            self._rebuild_params(sample)
            self._run()
            return
        op = self._current_op()
        if op is not None:
            self._active_op = op
            d = op.as_dict()
            self.editor.setPlainText(
                f"# {op.namespace}.{op.name}  [render_hint={d['render_hint']}]\n"
                f"# {d['doc']}\n#\n# 統一 registry から自動実行(F6): 合成入力 + スライダ上書き。\n"
                f"# シグネチャ: {d['signature']}\n"
                f"result = fs.vision.{op.namespace}.{op.name}(...)\n"
                f"# → render_hint '{d['render_hint']}' で自動描画。")
            self._rebuild_params({"params": _browser.scalar_param_specs(op)})
            self._run()

    def _run(self) -> None:
        if self._suspend:
            return
        # 統一 registry op: 合成入力 + スライダ上書きで自動実行し render_hint 描画(F6)
        if self._active_op is not None:
            op = self._active_op
            overrides = {sl.name: sl.value() for sl in self._sliders}
            status, result = _browser.compute_op(op, overrides)
            self.figure.clear()
            if result is None:
                _browser._f3_card(op, self.figure,
                                  reason="専用入力が要る(create_* が生む model 等)"
                                  if "auto-input" in status else status)
            else:
                _browser.render_by_hint(result, op.render_hint, self.figure,
                                        title=f"{op.namespace}.{op.name}")
            # 3D 化可能(point_cloud/pose)なら Open3D ボタンを有効化
            geoms = _v3d.to_geometries(result, op.render_hint) if result is not None else []
            self._last3d = geoms
            self._last3d_title = f"Fullseye 3D — {op.namespace}.{op.name}"
            self.open3d_btn.setEnabled(bool(geoms))
            self.canvas.draw()
            tag = "  |  🧊 Open in 3D 可" if geoms else ""
            self.statusBar().showMessage(f"{op.namespace}.{op.name}  |  {status.split(':')[0]}{tag}")
            return
        code = self.editor.toPlainText()
        self.figure.clear()
        ns = {
            "fig": self.figure, "np": np, "fs": fs,
            "Image": _vis.Image, "sim": _sim.sim, "LidarPattern": _sim.LidarPattern,
            "SCENE": _sim.SCENE, "synthetic_scene": synthetic_scene,
            "box_surface": box_surface, "stereo_pair": stereo_pair,
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
    # 統一 registry op 経路(F6): 各名前空間の代表 op を自動実行・描画できるか
    reg = _browser.ops
    reg_ok = 0
    for ns in reg.namespaces():
        name = reg.list(namespace=ns)[0]
        win._active_op = reg[name]
        win._rebuild_params({"params": _browser.scalar_param_specs(reg[name])})
        win._run()
        msg = win.statusBar().currentMessage()
        reg_ok += "Run OK" in msg
        print(f"  op:{ns:11s} {name:28s} -> {msg.split('|')[-1].strip()}")
    win._active_op = None
    out = Path(__file__).resolve().parent / "out_gallery" / "studio_app_smoke.png"
    out.parent.mkdir(exist_ok=True)
    win.figure.savefig(out, dpi=110)
    cov = _browser.coverage_report()
    print(f"[smoke] samples {ok}/{len(SAMPLES)} OK  |  registry 代表 {reg_ok}/{reg.stats()['namespaces']} ns OK  "
          f"|  自動実行カバレッジ {cov['auto_ran']}/{cov['total']} ({100*cov['auto_ran']//cov['total']}%)")
    print(f"  last render -> {out}")
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
