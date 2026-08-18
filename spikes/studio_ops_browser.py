"""Fullseye Studio — 統一 registry から 600 op を自動列挙・自動実行・描画自動選択(F6 核).

要件 F6: 「同一メタ(F3)から Studio が op を自動列挙・パラメータ UI 生成・実行」を、
本セッションの統一 registry(unified.py / fs.vision_ops)から driven で実現する 2 プリミティブ:

  render_by_hint(result, hint, fig)   … render_hint で 2D/3D 描画を自動選択(F6 の可視化核)
  synthesize_args(op)                 … F3 の自然な param 名から合成入力を作る(自動実行の核)

これにより GUI(studio_app.py)は 600 op を「発見し・メタを見て・その場で走らせて描く」ことができる。
本モジュールは GUI 非依存(matplotlib Figure だけ)なので headless で検証・被統合できる。
"""
from __future__ import annotations

import inspect
import warnings

import numpy as np

warnings.simplefilter("ignore")

import fullseye as fs                       # noqa: E402
ops = fs.vision_ops                          # 統一 registry(F2/F3)


# ── 合成入力(F3 の自然 param 名から) ─────────────────────────────────────────── #
def _syn_image(h=48, w=64, seed=0):
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    img = gaussian_filter(rng.random((h, w)), 1.2)
    img[12:28, 16:40] += 0.5                              # 明ブロック
    return np.clip(img, 0, 1)


def _syn_region(h=48, w=64):
    m = np.zeros((h, w), bool); m[12:28, 16:40] = True
    return m


def _syn_contour(shape=(64, 64)):
    t = np.linspace(0, 2 * np.pi, 60)
    arr = np.column_stack([32 + 16 * np.sin(t), 32 + 16 * np.cos(t)])
    return {"shape": shape, "cs": [arr]}


def _syn_cloud(n=300, seed=0):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n); th = np.pi * (1 + 5 ** 0.5) * i
    return np.column_stack([np.sin(phi) * np.cos(th), np.sin(phi) * np.sin(th), np.cos(phi)])


def _syn_points2d(n=30, seed=0):
    rng = np.random.default_rng(seed)
    return rng.uniform(0, 40, (n, 2))


def _syn_matrix(n=3):
    return np.eye(3) + 0.05 * np.arange(9).reshape(3, 3)


def _syn_signal(n=40):
    return np.sin(np.linspace(0, 6, n)) * 0.5 + 0.5


def _syn_images(k=3):
    return [_syn_image(seed=s) for s in range(k)]


def _syn_points2d_n(n=12):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([20 + 10 * np.sin(t), 20 + 10 * np.cos(t)])


def _syn_cam_par():
    return {"fx": 500.0, "fy": 500.0, "cx": 32.0, "cy": 24.0}


def _syn_pose():
    T = np.eye(4); T[:3, 3] = [0.1, 0.0, 2.0]; return T


def _syn_quat():
    return np.array([1.0, 0.0, 0.0, 0.0])


def _syn_dualquat():
    return np.array([1.0, 0, 0, 0, 0, 0, 0, 0.0])


def _syn_se():
    return np.ones((3, 3), bool)


def _syn_line():
    return (10.0, 5.0, 10.0, 35.0)


def _syn_vfield():
    return np.zeros((32, 32))


_SYN = {
    "image": _syn_image, "image1": _syn_image, "image2": _syn_image,
    "image_1": _syn_image, "image_2": _syn_image, "img": _syn_image,
    "source": _syn_image, "ref_image": _syn_image, "reference": _syn_image,
    "template": _syn_image, "left": _syn_image, "right": _syn_image,
    "disp": _syn_image, "disparity_image": _syn_image, "depth_image": _syn_image,
    "vfield_row": _syn_vfield, "vfield_col": _syn_vfield,
    "grad_row": _syn_vfield, "grad_col": _syn_vfield,
    "region": _syn_region, "seed_region": _syn_region, "ref_region": _syn_region,
    "region1": _syn_region, "region2": _syn_region, "sub": _syn_region,
    "contour": _syn_contour, "contour1": _syn_contour, "contour2": _syn_contour,
    "points": _syn_cloud, "point_cloud": _syn_cloud, "cloud": _syn_cloud,
    "points_a": _syn_cloud, "points_b": _syn_cloud, "model_points": _syn_cloud,
    "scene_points": _syn_cloud, "src": _syn_cloud,
    "points1": _syn_points2d_n, "points2": _syn_points2d_n,
    "src_points": _syn_points2d_n, "dst_points": _syn_points2d_n,
    "image_points": _syn_points2d_n,
    "images": _syn_images, "feature_images": _syn_images, "phase_images": _syn_images,
    "y": _syn_signal, "y1": _syn_signal, "y2": _syn_signal, "hist": _syn_signal,
    "M": _syn_matrix, "H": _syn_matrix, "A": _syn_matrix, "matrix": _syn_matrix,
    "homography": _syn_matrix, "hom_mat2d": _syn_matrix, "hom_mat3d": _syn_pose,
    "cam_par": _syn_cam_par, "K": _syn_matrix, "K1": _syn_matrix,
    "pose": _syn_pose, "R": _syn_matrix, "quat": _syn_quat, "q": _syn_quat,
    "dq": _syn_dualquat, "dual_quat": _syn_dualquat, "se": _syn_se,
    "line": _syn_line, "line1": _syn_line, "line2": _syn_line, "seg": _syn_line,
    "lut": _syn_signal,
}
# スカラー系 param のデフォルト(F3 の default が無い必須引数向け)
_SCALAR = {"row": 32.0, "col": 32.0, "column": 32.0, "radius": 12.0, "ra": 14.0, "rb": 8.0,
           "phi": 0.3, "length1": 12.0, "length2": 8.0, "sigma": 1.0, "value": 0.5,
           "thresh": 0.3, "tol": 0.1, "size": 12.0, "width": 48, "height": 48,
           "row1": 8, "col1": 8, "row2": 30, "col2": 40, "focal": 500.0, "baseline": 0.1,
           "disparity": 5.0, "kappa": 1e-4, "level": 0.3, "r1": 10.0, "c1": 5.0,
           "r2": 10.0, "c2": 35.0, "cx": 32.0, "cy": 24.0, "shape": (48, 64),
           "center": (32.0, 32.0), "t": 0.0, "x": 20.0, "index": 0, "axis": 2}


def synthesize_args(op):
    """op の F3 param 名から合成入力を作る。作れない必須引数があれば None(=自動実行不可)。"""
    args = []
    for name, default, kind in op.params:
        if kind == "var":
            continue
        if name in _SYN:
            args.append(_SYN[name]())
        elif default is not inspect.Parameter.empty:
            break                                        # 以降はデフォルトに任せる
        elif name in _SCALAR:
            args.append(_SCALAR[name])
        else:
            return None                                  # 未知の必須引数=自動実行不可
    return args


# ── 描画ディスパッチャ(render_hint → 2D/3D 自動選択) ─────────────────────────── #
def render_by_hint(result, hint, fig, title=""):
    """op の出力を render_hint に従って Figure へ描く(F6 の可視化核)。"""
    fig.clear()
    try:
        if hint == "image":
            _render_image(result, fig)
        elif hint == "region":
            _render_region(result, fig)
        elif hint == "contour":
            _render_contour(result, fig)
        elif hint == "point_cloud":
            _render_cloud(result, fig)
        elif hint == "pose":
            _render_pose(result, fig)
        elif hint in ("matrix", "matches", "scalar"):
            _render_text(result, fig, hint)
        else:
            _render_text(result, fig, hint)
    except Exception as e:  # noqa: BLE001 — 描画失敗はカードにフォールバック
        _render_text(f"{type(e).__name__}: {e}", fig, "error")
    if title:
        fig.suptitle(title, fontsize=9)
    return fig


def _as_image(r):
    if isinstance(r, np.ndarray) and r.ndim in (2, 3):
        return r
    if isinstance(r, dict):
        for k in ("image", "row_map", "anomaly_map", "depth", "dZ", "abs"):
            if k in r and np.ndim(r[k]) == 2:
                return np.asarray(r[k], float)
    return None


def _render_image(r, fig):
    im = _as_image(r)
    ax = fig.add_subplot(111)
    if im is None:
        return _render_text(r, fig, "image")
    if im.ndim == 3:
        ax.imshow(np.clip(im, 0, 1))
    else:
        ax.imshow(im, cmap="gray")
    ax.axis("off")


def _render_region(r, fig):
    ax = fig.add_subplot(111)
    m = r if isinstance(r, np.ndarray) else np.asarray(r)
    ax.imshow(m.astype(float), cmap="viridis"); ax.axis("off")


def _render_contour(r, fig):
    ax = fig.add_subplot(111)
    css = r.get("cs", []) if isinstance(r, dict) else []
    if not css and isinstance(r, np.ndarray) and r.ndim == 2 and r.shape[1] == 2:
        css = [r]
    for arr in css:
        arr = np.asarray(arr)
        if len(arr):
            ax.plot(arr[:, 1], arr[:, 0], lw=1.5)
    ax.set_aspect("equal"); ax.invert_yaxis()


def _render_cloud(r, fig):
    pts = r
    if isinstance(r, dict):
        pts = r.get("points", r.get("points_3d", r.get("point_3d")))
    pts = np.asarray(pts, float)
    ax = fig.add_subplot(111, projection="3d")
    if pts.ndim == 2 and pts.shape[1] == 3:
        ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=4, c=pts[:, 2], cmap="viridis")
    ax.view_init(24, -60)


def _render_pose(r, fig):
    ax = fig.add_subplot(111, projection="3d")
    R = np.eye(3); t = np.zeros(3)
    if isinstance(r, np.ndarray) and r.shape == (4, 4):
        R, t = r[:3, :3], r[:3, 3]
    elif isinstance(r, dict):
        R = np.asarray(r.get("R", np.eye(3))); t = np.asarray(r.get("t", np.zeros(3))).ravel()[:3]
    for k, col in enumerate("rgb"):
        v = R @ np.eye(3)[:, k]
        ax.plot([t[0], t[0] + v[0]], [t[1], t[1] + v[1]], [t[2], t[2] + v[2]], color=col, lw=2)
    ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.5, 1.5); ax.set_zlim(-1.5, 1.5); ax.view_init(22, -60)


def _render_text(r, fig, hint):
    ax = fig.add_subplot(111); ax.axis("off")
    if isinstance(r, dict):
        lines = [f"{k}: {np.asarray(v).shape if hasattr(v,'shape') else _short(v)}" for k, v in r.items()]
        txt = "\n".join(lines[:12])
    elif isinstance(r, np.ndarray):
        txt = f"ndarray shape={r.shape}\n{np.array2string(r, precision=3, threshold=40)}"
    else:
        txt = _short(r)
    ax.text(0.03, 0.97, f"[{hint}]\n{txt}", va="top", ha="left", family="monospace", fontsize=8)


def _short(v):
    s = repr(v)
    return s if len(s) < 200 else s[:200] + " …"


def run_op(op, fig=None):
    """op を合成入力で実行し(可能なら)結果と Figure を返す。自動実行不可なら (None, reason)。"""
    from matplotlib.figure import Figure
    args = synthesize_args(op)
    if args is None:
        return None, "auto-input 不可(専用入力が要る)"
    try:
        result = op(*args)
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"
    fig = fig or Figure(figsize=(4, 3))
    render_by_hint(result, op.render_hint, fig, title=f"{op.namespace}.{op.name}")
    return result, fig


def coverage_report():
    """honest な自動実行カバレッジ: 600 op 中いくつが合成入力で走り描けるか。"""
    from matplotlib.figure import Figure
    ran, no_input, errored = 0, 0, 0
    err_samples = []
    for name in ops.list():
        op = ops[name]
        res, info = run_op(op, Figure(figsize=(2, 2)))
        if isinstance(info, str):
            if "auto-input" in info:
                no_input += 1
            else:
                errored += 1
                if len(err_samples) < 12:
                    err_samples.append((name, info))
        else:
            ran += 1
    return {"total": len(ops), "auto_ran": ran, "needs_input": no_input,
            "errored": errored, "err_samples": err_samples}


if __name__ == "__main__":
    print("== Fullseye Studio op-browser: 自動実行カバレッジ(honest)==")
    rep = coverage_report()
    print(f"総 {rep['total']}  自動実行 OK {rep['auto_ran']}  "
          f"専用入力要 {rep['needs_input']}  実行時エラー {rep['errored']}")
    print(f"→ 合成入力だけで {rep['auto_ran']}/{rep['total']} "
          f"({100*rep['auto_ran']/rep['total']:.0f}%) が Studio で即実行・描画できる")
    if rep["err_samples"]:
        print("エラー例(要調整):")
        for n, e in rep["err_samples"]:
            print(f"  {n}: {e}")
