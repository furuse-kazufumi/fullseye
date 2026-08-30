# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_article_assets — Qiita 総集編記事「Fullseye 総集編」向けのデモ素材(PNG)を生成する.
Generate demo PNG assets for the "Fullseye retrospective" Qiita article.

目的(かみくだき) / Purpose:
  記事に載せる「出来ることが見える」実出力画像を作る。**モックアップ禁止** —
  fullseye 自身の op / demo 関数を実際に実行して得た本物の出力だけを使う
  (honest disclosure 規律。memory `feedback_benchmark_honest_disclosure` 準拠)。
  We build "you can see what it does" images for the article. **No mockups** —
  every panel is the real output of an actual fullseye op/demo call. Anything
  that doesn't run cleanly is skipped, and the skip is logged (never silently
  faked).

生成物 / Outputs (docs/articles/assets/):
  physical_ai_montage.png  -- Physical AI センサ・シム 6 パネル 2x3 モンタージュ
                               (LiDAR / stereo / event camera / focus stack /
                               polarization / camera+IMU fusion — 各モジュールの
                               既存 run_*_demo() をそのまま実行)
  vision_ops_montage.png   -- 2D 古典ビジョン op 6 パネル 2x3 モンタージュ
                               (入力 -> 平滑 -> エッジ -> 二値化 -> 連結成分 ->
                               輪郭抽出+計測、fullseye.apply() 経由)
  render_beauty_hero.png / hand_hero.png / gear_hero.png /
  showcase_turntable_itokawa.gif
                            -- examples_3d/_gallery/ の既存 hero 画像のコピー
  _sources/*.png            -- モンタージュの元になった各センサー demo のフルサイズ
                               中間出力(honest な来歴保持のため残す)

Run:  py -3.11 tools/gen_article_assets.py
"""
from __future__ import annotations

import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

ASSETS_DIR = os.path.join(REPO, "docs", "articles", "assets")
SOURCES_DIR = os.path.join(ASSETS_DIR, "_sources")
THUMBS_DIR = os.path.join(ASSETS_DIR, "thumbs")
GALLERY_DIR = os.path.join(REPO, "examples_3d", "_gallery")

SEED = 20260830  # 全生成で固定する乱数種 (再現性) / fixed seed for reproducibility

THUMB_WIDTH = 720  # Qiita 記事に貼るサムネの目標幅(px)。元画像がこれより狭ければ拡大しない。


def _ensure_dirs() -> None:
    os.makedirs(SOURCES_DIR, exist_ok=True)
    os.makedirs(THUMBS_DIR, exist_ok=True)


# --------------------------------------------------------------------------- #
# 1) Physical AI センサ・シミュレーション モンタージュ                              #
#    Physical AI sensor-simulation montage                                    #
# --------------------------------------------------------------------------- #
def build_physical_ai_montage(log=print) -> dict:
    """6 種のセンサ・シムを実際に走らせ、その本物の出力を 2x3 グリッドへ並べる.

    Actually runs 6 sensor-simulation demos (each module's existing
    ``run_*_demo`` facade, which renders a real MuJoCo scene and processes it)
    and lays their real output images out on a 2x3 grid. Nothing here is drawn
    by hand — every pixel came out of an op/demo call.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import event_camera
    import focus_stack
    import lidar_sim
    import polar_cam
    import sensor_fusion
    import stereo_sim

    def _fusion_caption(r: dict) -> str:
        rmse = r["rmse_m"]
        return (f"Kalman-fused RMSE {rmse['kalman_fused']*100:.1f}cm "
                f"(vs. position-only {rmse['position_sensor_only']*100:.1f}cm)")

    jobs = [
        ("LiDAR — range image to 3D point cloud", "lidar_sim.py",
         lambda out: lidar_sim.run_lidar_demo(out, log=log),
         lambda r: f"{r['n_points']} pts, {r['channels']}ch, hit-ratio {r['hit_ratio']*100:.0f}%"),
        ("Stereo depth — block matching", "stereo_sim.py",
         lambda out: stereo_sim.run_stereo_demo(out, log=log),
         lambda r: f"depth corr {r['depth_corr']:.2f}, median err {r['median_err_m']*100:.1f}cm"),
        ("Event camera (DVS) — per-pixel change events", "event_camera.py",
         lambda out: event_camera.run_event_demo(out, log=log),
         lambda r: f"{r['n_events']:,} events, edge-corr {r['edge_corr']:.2f}"),
        ("Focus stacking — depth-from-focus", "focus_stack.py",
         lambda out: focus_stack.run_focus_stack_demo(out, log=log),
         lambda r: f"sharpness x{r['sharpness_gain']:.2f}, depth corr {r['depth_focus_corr']:.2f}"),
        ("Polarization camera — DoLP / AoLP", "polar_cam.py",
         lambda out: polar_cam.run_polar_demo(out, log=log),
         lambda r: f"mean DoLP {r['mean_dolp']:.2f}, Stokes round-trip {r['stokes_roundtrip']:.2f}"),
        ("Camera + IMU sensor fusion — Kalman filter", "sensor_fusion.py",
         lambda out: sensor_fusion.run_fusion_demo(out, log=log),
         _fusion_caption),
    ]

    panels = []
    skipped = []
    for title, src_module, run_fn, caption_fn in jobs:
        out_png = os.path.join(SOURCES_DIR, f"src_{os.path.splitext(src_module)[0]}.png")
        try:
            result = run_fn(out_png)
        except Exception as exc:  # honest skip, not a silent mock substitute
            skipped.append((title, src_module, str(exc)))
            log(f"[skip] {title} ({src_module}): {exc}")
            continue
        panels.append((title, src_module, out_png, caption_fn(result)))

    if not panels:
        raise RuntimeError("physical_ai_montage: every sensor demo failed, nothing to render")

    n = len(panels)
    ncols = 3 if n > 4 else 2
    nrows = -(-n // ncols)  # ceil
    bg, fg, muted = "#0b0d12", "#e7e9ee", "#8b91a0"
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.2 * ncols, 4.1 * nrows), facecolor=bg)
    axes = axes.ravel() if n > 1 else [axes]
    for ax, (title, src_module, out_png, caption) in zip(axes, panels):
        img = plt.imread(out_png)
        ax.imshow(img)
        ax.axis("off")
        ax.set_title(title, color=fg, fontsize=11, pad=8)
        ax.text(0.5, -0.03, f"{src_module} — {caption}", transform=ax.transAxes,
                ha="center", va="top", color=muted, fontsize=8.5)
    for ax in axes[len(panels):]:
        ax.axis("off")

    fig.suptitle("Fullseye — Physical AI sensor simulation (real outputs, not mockups)",
                 color=fg, fontsize=15, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out_path = os.path.join(ASSETS_DIR, "physical_ai_montage.png")
    fig.savefig(out_path, dpi=118, facecolor=bg)
    plt.close(fig)
    log(f"physical_ai_montage: {out_path} | panels={len(panels)} skipped={len(skipped)}")
    return {"path": out_path, "n_panels": len(panels), "skipped": skipped}


# --------------------------------------------------------------------------- #
# 2) 2D 古典ビジョン op モンタージュ / classical 2D vision-op montage           #
# --------------------------------------------------------------------------- #
def build_vision_ops_montage(log=print) -> dict:
    """coins サンプル画像に古典 2D op チェーンを実際に適用し 2x3 で並べる.

    Runs a real classical-vision chain via ``fullseye.apply`` on the bundled
    "coins" sample image: input -> gaussian smoothing -> Sobel edge magnitude
    -> Otsu threshold -> connected components -> sub-pixel contour extraction
    with overlay + measured stats. Every panel is a real op call, no synthetic
    drawing beyond the contour overlay (which draws the op's own XLD output).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import ndimage

    import fullseye
    import imgio
    import sample_images as si

    img = si.load("coins")                                    # real bundled sample (BSD/skimage.data)
    smoothed = fullseye.apply(img, "gaussian", a=0.3, b=0.0)
    edges = fullseye.apply(smoothed, "sobel_amp")
    region = fullseye.apply(smoothed, "otsu")
    labels, n_components = ndimage.label(region > 0.5)
    labels_rgb = imgio.colorize_labels(labels)

    # a=0.7 の select_contours 閾値(長さ>=31px)で各コインの外周を拾い、内部の
    # 彫刻テクスチャ由来の短い contour を落とす(短いまま重ねると円盤が塗り潰しに
    # 見えてしまうため — honest な可視化のための閾値選定であり、数値自体は捏造しない)。
    # a=0.7 keeps only long contours (>=31px) so each coin's outer boundary shows
    # cleanly instead of being swamped by short engraving-texture edges.
    contour_edges = fullseye.apply(smoothed, "edges_sub_pix", a=0.2, b=0.0)
    contours = fullseye.apply(contour_edges, "select_contours", a=0.7, b=0.0)
    cs = contours.get("cs", [])
    n_contours = len(cs)
    # XLD 出力は path-ordered ではなく走査順の点集合なので、線でつなぐと隣接しない
    # 点同士を結んで塗り潰しに見える。点そのものを焼き込む(実データを歪めない)。
    # The XLD points are raster-scan ordered, not path-ordered, so connecting them
    # with lines draws spurious chords; stamp the real edge points directly instead.
    H, W = contours["shape"]
    contour_mask = np.zeros((H, W), dtype=bool)
    for c in cs:
        rr = np.clip(np.round(np.asarray(c)[:, 0]).astype(int), 0, H - 1)
        cc = np.clip(np.round(np.asarray(c)[:, 1]).astype(int), 0, W - 1)
        contour_mask[rr, cc] = True
    contour_mask = ndimage.binary_dilation(contour_mask, iterations=1)
    overlay = imgio.ensure_color(img).copy()
    overlay[contour_mask] = [1.0, 0.25, 0.2]
    areas = ndimage.sum(np.ones_like(labels), labels, index=np.arange(1, n_components + 1))
    mean_area = float(areas.mean()) if n_components else 0.0

    panels = [
        ("Input — sample image", img, "gray",
         f"coins.png, {img.shape[1]}x{img.shape[0]}"),
        ("Gaussian smoothing", smoothed, "gray",
         "op: gaussian"),
        ("Edge magnitude — Sobel", edges, "magma",
         "op: sobel_amp"),
        ("Segmentation — Otsu threshold", region, "gray",
         "op: otsu"),
        ("Connected components", labels_rgb, None,
         f"{n_components} components (scipy.ndimage.label on otsu region)"),
        ("Sub-pixel contours + measurement", overlay, None,
         f"{n_contours} contours, mean blob area {mean_area:.0f} px "
         f"(op: edges_sub_pix -> select_contours)"),
    ]

    bg, fg, muted = "#0b0d12", "#e7e9ee", "#8b91a0"
    fig, axes = plt.subplots(2, 3, figsize=(6.2 * 3, 4.6 * 2), facecolor=bg)
    axes = axes.ravel()
    for ax, (title, arr, cmap, caption) in zip(axes, panels):
        ax.imshow(arr, cmap=cmap)
        ax.axis("off")
        ax.set_title(title, color=fg, fontsize=11, pad=8)
        ax.text(0.5, -0.04, caption, transform=ax.transAxes,
                ha="center", va="top", color=muted, fontsize=8.5)

    fig.suptitle("Fullseye — classical 2D vision ops (real op chain, not a mockup)",
                 color=fg, fontsize=15, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_path = os.path.join(ASSETS_DIR, "vision_ops_montage.png")
    fig.savefig(out_path, dpi=100, facecolor=bg)
    plt.close(fig)
    log(f"vision_ops_montage: {out_path} | components={n_components} contours={n_contours}")
    return {"path": out_path, "n_components": int(n_components), "n_contours": n_contours}


# --------------------------------------------------------------------------- #
# 3) 既存 hero 画像のコピー / copy existing hero renders                        #
# --------------------------------------------------------------------------- #
def copy_hero_assets(log=print) -> list:
    """examples_3d/_gallery/ の既存 hero 画像・showcase gif を assets/ へコピーする.

    These are pre-existing, already-real renders from the 3D gallery — copied
    verbatim (no edits) so the article has a self-contained asset directory.
    """
    names = ["render_beauty_hero.png", "hand_hero.png", "gear_hero.png",
             "showcase_turntable_itokawa.gif"]
    copied = []
    for name in names:
        src = os.path.join(GALLERY_DIR, name)
        dst = os.path.join(ASSETS_DIR, name)
        if not os.path.exists(src):
            log(f"[skip] hero asset missing: {src}")
            continue
        shutil.copyfile(src, dst)
        copied.append(dst)
        log(f"copied: {name} -> {dst}")
    return copied


# --------------------------------------------------------------------------- #
# 3b) イトカワ実点群 3D op モンタージュ / Itokawa real-pointcloud 3D-op montage  #
# --------------------------------------------------------------------------- #
def build_itokawa_montage(log=print) -> dict:
    """小惑星 25143 Itokawa の実点群に fullseye の 3D op を実際に適用し 2x2 で並べる.

    データ: studio_assets/sample_3d/itokawa_points.npy — JAXA はやぶさ / Gaskell 形状
    モデル由来の実測点群(float32, 3000点)。examples_3d/itokawa_*.py と同じ計算を直接
    呼び出す(curvature3d / match3d / metrics3d)。**モックアップ禁止** — 各パネルの
    数値はその場で実行して得た本物の結果であり、でっち上げではない。

    Runs real fullseye 3D ops on the actual Itokawa point cloud (not a mockup mesh)
    and lays 4 panels out on a 2x2 grid: (1) a "beauty" scatter of the raw shape,
    (2) surface curvature (curvature3d.curvedness), (3) ICP self-registration
    before/after (match3d.icp_point2point_3d), (4) PCA canonical-pose axes
    (match3d.moment_axes). Each caption carries a real measured number from that
    op call — same math as examples_3d/itokawa_*.py, called directly here.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (3D projection registration)
    from scipy.spatial import cKDTree
    from scipy.spatial.transform import Rotation

    import curvature3d  # principal_curvatures / curvedness(局所二次曲面フィット)
    import match3d       # icp_point2point_3d / moment_axes
    import metrics3d     # pose_error

    bg, fg, muted = "#0b0d12", "#e7e9ee", "#8b91a0"

    def _style_3d_ax(ax):
        """3D 軸のパネル背景・グリッド・目盛りをモンタージュのダーク配色に揃える."""
        ax.set_facecolor(bg)
        for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
            pane.set_facecolor(bg)
            pane.set_edgecolor(bg)
        ax.grid(False)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass  # 古い matplotlib では box_aspect 非対応(無くても崩れない)

    data_path = os.path.join(REPO, "studio_assets", "sample_3d", "itokawa_points.npy")
    if not os.path.exists(data_path):
        log(f"[skip] itokawa_montage: data missing: {data_path}")
        return {"path": None, "n_panels": 0, "skipped": [("itokawa_montage", "all", "data missing")]}

    import numpy as np
    pts = np.load(data_path).astype(np.float64)
    pts = pts - pts.mean(axis=0)
    extent = pts.max(axis=0) - pts.min(axis=0)
    diag = float(np.linalg.norm(extent))

    panels = []
    skipped = []

    # --- パネル1: 見栄えレンダ(実点群を岩石色でscatter)/ beauty scatter ---
    try:
        fig = plt.figure(figsize=(6, 6), facecolor=bg)
        ax = fig.add_subplot(111, projection="3d")
        _style_3d_ax(ax)
        r = np.linalg.norm(pts, axis=1)
        ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=r, cmap="copper", s=4, linewidths=0)
        ax.view_init(elev=18, azim=35)
        fig.tight_layout()
        out_png = os.path.join(SOURCES_DIR, "src_itokawa_beauty.png")
        fig.savefig(out_png, dpi=112, facecolor=bg)
        plt.close(fig)
        caption = (f"{len(pts)} pts, extent {extent[0]:.0f}x{extent[1]:.0f}x{extent[2]:.0f} m "
                   "(JAXA Hayabusa / Gaskell shape model, real point cloud)")
        panels.append(("Itokawa — raw point cloud", "itokawa_points.npy", out_png, caption))
    except Exception as exc:
        skipped.append(("beauty scatter", "itokawa_points.npy", str(exc)))
        log(f"[skip] itokawa beauty panel: {exc}")

    # --- パネル2: 曲率(curvature3d.curvedness)/ surface curvature ---
    try:
        cv = curvature3d.curvedness(pts, k=20)
        tree = cKDTree(pts)
        _, idx = tree.query(pts, k=6)
        neigh_mean = cv[idx[:, 1:]].mean(axis=1)
        coh = float(np.corrcoef(cv, neigh_mean)[0, 1])   # 近傍相関(実在表面なら高い)
        cv_mean, cv_std = float(np.mean(cv)), float(np.std(cv))
        vlo, vhi = np.percentile(cv, [2, 98])              # 外れ値でスケールが潰れないよう clip

        fig = plt.figure(figsize=(6, 6), facecolor=bg)
        ax = fig.add_subplot(111, projection="3d")
        _style_3d_ax(ax)
        ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=cv, cmap="inferno",
                   vmin=vlo, vmax=vhi, s=4, linewidths=0)
        ax.view_init(elev=18, azim=35)
        fig.tight_layout()
        out_png = os.path.join(SOURCES_DIR, "src_itokawa_curvature.png")
        fig.savefig(out_png, dpi=112, facecolor=bg)
        plt.close(fig)
        caption = (f"curvedness mean {cv_mean:.4f} / std {cv_std:.4f}, "
                   f"neighbor coherence r={coh:.2f} (op: curvature3d.curvedness)")
        panels.append(("Surface curvature", "curvature3d.py", out_png, caption))
    except Exception as exc:
        skipped.append(("curvature", "curvature3d.py", str(exc)))
        log(f"[skip] itokawa curvature panel: {exc}")

    # --- パネル3: ICP 自己位置合わせ before/after / self-registration ---
    try:
        rng = np.random.default_rng(0)
        R_gt = Rotation.from_rotvec(np.array([0.2, 0.5, 0.84]) /
                                     np.linalg.norm([0.2, 0.5, 0.84]) *
                                     np.radians(30.0)).as_matrix()
        noise_sigma = 0.004 * diag
        scan = pts @ R_gt.T + rng.normal(0.0, noise_sigma, pts.shape)
        R, t, info = match3d.icp_point2point_3d(scan, pts, iters=80)
        R = R.detach().cpu().numpy()
        t = t.detach().cpu().numpy()
        aligned = scan @ R.T + t
        rot_deg, _ = metrics3d.pose_error(R, np.zeros(3), R_gt.T, np.zeros(3))
        rmse = float(info["rmse"])

        # figsize は最終モンタージュのセル比(7.5:6.6 ≈ 1.14:1)に近づけ、aspect='auto' で
        # 引き伸ばす際の歪みを最小化する(他の正方形パネルとの見た目バランス合わせ)。
        fig = plt.figure(figsize=(9.0, 7.9), facecolor=bg)
        ax1 = fig.add_subplot(121, projection="3d")
        _style_3d_ax(ax1)
        ax1.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=muted, s=3, alpha=0.5, linewidths=0)
        ax1.scatter(scan[:, 0], scan[:, 1], scan[:, 2], c="#ff5555", s=3, linewidths=0)
        ax1.set_title("Before ICP", color=fg, fontsize=10)
        ax1.view_init(elev=18, azim=35)
        ax2 = fig.add_subplot(122, projection="3d")
        _style_3d_ax(ax2)
        ax2.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=muted, s=3, alpha=0.5, linewidths=0)
        ax2.scatter(aligned[:, 0], aligned[:, 1], aligned[:, 2], c="#55ff99", s=3, linewidths=0)
        ax2.set_title("After ICP", color=fg, fontsize=10)
        ax2.view_init(elev=18, azim=35)
        fig.tight_layout()
        out_png = os.path.join(SOURCES_DIR, "src_itokawa_register.png")
        fig.savefig(out_png, dpi=112, facecolor=bg)
        plt.close(fig)
        caption = (f"ICP: rot err {rot_deg:.3f} deg, RMSE {rmse:.2f} m "
                   "(op: match3d.icp_point2point_3d, 30 deg unknown rotation + sensor noise)")
        panels.append(("Self-registration (ICP)", "match3d.py", out_png, caption))
    except Exception as exc:
        skipped.append(("self-register", "match3d.py", str(exc)))
        log(f"[skip] itokawa register panel: {exc}")

    # --- パネル4: 正準姿勢(match3d.moment_axes の主軸)/ canonical pose axes ---
    try:
        c0, axes0, vals0 = match3d.moment_axes(pts)
        q = (pts - c0) @ axes0
        skew = np.mean(q ** 3, axis=0)
        sign = np.where(skew >= 0.0, 1.0, -1.0)
        q = q * sign
        ratio = float(vals0[0] / vals0[1])

        # 未知回転を掛けてから主軸を回復できるか(honest な数値の裏取り)
        R_unknown = Rotation.from_rotvec(np.array([0.30, 0.70, 0.60]) /
                                         np.linalg.norm([0.30, 0.70, 0.60]) *
                                         np.radians(50.0)).as_matrix()
        pts_rot = pts @ R_unknown.T
        _, axes1, _ = match3d.moment_axes(pts_rot)
        cos_axes = [abs(float(np.dot(axes1[:, i], R_unknown @ axes0[:, i]))) for i in range(3)]

        fig = plt.figure(figsize=(6, 6), facecolor=bg)
        ax = fig.add_subplot(111, projection="3d")
        _style_3d_ax(ax)
        ax.scatter(q[:, 0], q[:, 1], q[:, 2], c=muted, s=4, alpha=0.6, linewidths=0)
        axis_len = np.sqrt(vals0) * 0.8
        colors = ["#ff5555", "#55ff99", "#55aaff"]
        for i in range(3):
            d = np.zeros(3); d[i] = 1.0
            ax.quiver(0, 0, 0, d[0] * axis_len[i], d[1] * axis_len[i], d[2] * axis_len[i],
                      color=colors[i], linewidth=2.2)
        ax.view_init(elev=18, azim=35)
        fig.tight_layout()
        out_png = os.path.join(SOURCES_DIR, "src_itokawa_pose.png")
        fig.savefig(out_png, dpi=112, facecolor=bg)
        plt.close(fig)
        caption = (f"principal-axis ratio {ratio:.2f}:1, axis recovery under 50deg unknown "
                   f"rotation |cos|>= {min(cos_axes):.4f} (op: match3d.moment_axes)")
        panels.append(("Canonical pose (PCA axes)", "match3d.py", out_png, caption))
    except Exception as exc:
        skipped.append(("pose canonical", "match3d.py", str(exc)))
        log(f"[skip] itokawa pose panel: {exc}")

    if not panels:
        raise RuntimeError("itokawa_montage: every panel failed, nothing to render")

    n = len(panels)
    ncols = 2
    nrows = -(-n // ncols)  # ceil
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.5 * ncols, 6.6 * nrows), facecolor=bg)
    axes = axes.ravel() if n > 1 else [axes]
    for ax, (title, src_module, out_png, caption) in zip(axes, panels):
        img = plt.imread(out_png)
        # aspect='auto': 各パネルPNGの縦横比(正方形1枚 vs before/after横並び2枚)がまちまちなので、
        # 元比率を保存すると空白が生まれる。グリッドセルいっぱいに引き伸ばして埋める。
        # source PNGs have mixed aspect ratios (square vs. wide before/after pair); stretch
        # to fill the grid cell instead of letterboxing so every panel reads at the same size.
        ax.imshow(img, aspect="auto")
        ax.axis("off")
        ax.set_title(title, color=fg, fontsize=12, pad=8)
        ax.text(0.5, -0.02, f"{src_module} — {caption}", transform=ax.transAxes,
                ha="center", va="top", color=muted, fontsize=8.5, wrap=True)
    for ax in axes[len(panels):]:
        ax.axis("off")

    fig.suptitle("Fullseye — asteroid 25143 Itokawa, real point cloud (3D ops, not a mockup)",
                 color=fg, fontsize=15, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out_path = os.path.join(ASSETS_DIR, "itokawa_montage.png")
    fig.savefig(out_path, dpi=118, facecolor=bg)
    plt.close(fig)
    log(f"itokawa_montage: {out_path} | panels={len(panels)} skipped={len(skipped)}")
    return {"path": out_path, "n_panels": len(panels), "skipped": skipped}


# --------------------------------------------------------------------------- #
# 4) 記事貼付け用サムネイル(幅720px)/ article thumbnails (720px wide)          #
# --------------------------------------------------------------------------- #
def build_thumbnails(log=print) -> list:
    """記事に貼るモンタージュ/hero 画像から幅 720px のサムネを作る.

    フルサイズは GitHub 側(docs/GALLERY.md)で見せ、Qiita 記事にはこの軽量サムネだけを
    貼ってメモリ負荷を下げる。アスペクト比は維持し、元画像が 720px より狭い場合は
    拡大しない(honest — 存在しない解像度をでっち上げない)。PIL の LANCZOS でリサイズ、
    PNG optimize=True で保存する。
    """
    from PIL import Image

    names = ["physical_ai_montage.png", "vision_ops_montage.png", "render_beauty_hero.png",
             "itokawa_montage.png"]
    thumbs = []
    for name in names:
        src = os.path.join(ASSETS_DIR, name)
        if not os.path.exists(src):
            log(f"[skip] thumbnail source missing: {src}")
            continue
        stem = os.path.splitext(name)[0]
        dst = os.path.join(THUMBS_DIR, f"{stem}_720.png")
        with Image.open(src) as im:
            im = im.convert("RGB")
            target_w = min(THUMB_WIDTH, im.width)  # never upscale
            target_h = round(im.height * target_w / im.width)
            thumb = im.resize((target_w, target_h), Image.LANCZOS)
            thumb.save(dst, format="PNG", optimize=True)
        size_kb = os.path.getsize(dst) / 1024
        log(f"thumbnail: {dst} | {target_w}x{target_h} ({size_kb:.1f} KiB)")
        thumbs.append(dst)
    return thumbs


def main() -> int:
    import numpy as np
    np.random.seed(SEED)

    _ensure_dirs()
    print(f"== gen_article_assets (seed={SEED}) ==")

    print("\n-- 1) physical_ai_montage --")
    physical = build_physical_ai_montage()

    print("\n-- 2) vision_ops_montage --")
    vision = build_vision_ops_montage()

    print("\n-- 3) hero copies --")
    heroes = copy_hero_assets()

    print("\n-- 3b) itokawa_montage --")
    itokawa = build_itokawa_montage()

    print("\n-- 4) thumbnails (720px) --")
    thumbs = build_thumbnails()

    print("\n== summary ==")
    all_paths = [physical["path"], vision["path"], *heroes]
    if itokawa["path"]:
        all_paths.append(itokawa["path"])
    all_paths.extend(thumbs)
    for path in all_paths:
        size = os.path.getsize(path)
        print(f"{path}  ({size/1024:.1f} KiB)")
    if physical["skipped"]:
        print("skipped physical-AI panels:")
        for title, module, reason in physical["skipped"]:
            print(f"  - {title} ({module}): {reason}")
    if itokawa["skipped"]:
        print("skipped itokawa panels:")
        for title, module, reason in itokawa["skipped"]:
            print(f"  - {title} ({module}): {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
