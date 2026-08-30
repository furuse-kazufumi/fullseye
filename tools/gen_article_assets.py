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
  thumbs/*_720.jpg          -- 記事貼付け用 720px サムネ(JPEG quality=85。容量を JPG で
                               抑える方針。旧 PNG サムネは削除される)
  media/dvs_stream.mp4 / .gif
                            -- event_camera の DVS(イベントカメラ)シミュレーションを
                               フレーム単位で可視化した短尺動画(パン中に ON/OFF イベントが
                               流れる様子。event_camera._render_pan/_events と同一モデル)

Run:  py -3.11 tools/gen_article_assets.py
"""
from __future__ import annotations

import os
import shutil
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

ASSETS_DIR = os.path.join(REPO, "docs", "articles", "assets")
SOURCES_DIR = os.path.join(ASSETS_DIR, "_sources")
THUMBS_DIR = os.path.join(ASSETS_DIR, "thumbs")
MEDIA_DIR = os.path.join(ASSETS_DIR, "media")  # mp4/gif 動画置き場(GitHub blob リンク用)
GALLERY_DIR = os.path.join(REPO, "examples_3d", "_gallery")

SEED = 20260830  # 全生成で固定する乱数種 (再現性) / fixed seed for reproducibility

THUMB_WIDTH = 720  # Qiita 記事に貼るサムネの目標幅(px)。元画像がこれより狭ければ拡大しない。


def _ensure_dirs() -> None:
    os.makedirs(SOURCES_DIR, exist_ok=True)
    os.makedirs(THUMBS_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)


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
    """記事に貼るモンタージュ/hero 画像から幅 720px の JPG サムネを作る.

    フルサイズは GitHub 側(docs/GALLERY.md)で見せ、Qiita 記事にはこの軽量サムネだけを
    貼ってメモリ負荷を下げる。アスペクト比は維持し、元画像が 720px より狭い場合は
    拡大しない(honest — 存在しない解像度をでっち上げない)。PIL の LANCZOS でリサイズ、
    RGB 変換のうえ JPEG quality=85 で保存する(容量を JPG で抑える方針。旧 PNG サムネが
    残っていれば削除する)。
    """
    from PIL import Image

    names = ["physical_ai_montage.png", "vision_ops_montage.png", "render_beauty_hero.png",
             "itokawa_montage.png", "op_taxonomy.png", "halcon_coverage_chart.png",
             "op_sampler_2d.png", "op_sampler_3d.png"]
    thumbs = []
    for name in names:
        src = os.path.join(ASSETS_DIR, name)
        if not os.path.exists(src):
            log(f"[skip] thumbnail source missing: {src}")
            continue
        stem = os.path.splitext(name)[0]
        dst = os.path.join(THUMBS_DIR, f"{stem}_720.jpg")
        old_png = os.path.join(THUMBS_DIR, f"{stem}_720.png")
        if os.path.exists(old_png):
            os.remove(old_png)
            log(f"removed stale PNG thumbnail: {old_png}")
        with Image.open(src) as im:
            im = im.convert("RGB")
            target_w = min(THUMB_WIDTH, im.width)  # never upscale
            target_h = round(im.height * target_w / im.width)
            thumb = im.resize((target_w, target_h), Image.LANCZOS)
            thumb.save(dst, format="JPEG", quality=85, optimize=True)
        size_kb = os.path.getsize(dst) / 1024
        log(f"thumbnail: {dst} | {target_w}x{target_h} ({size_kb:.1f} KiB)")
        thumbs.append(dst)
    return thumbs


# --------------------------------------------------------------------------- #
# 5) DVS(event camera)イベントストリームの短尺動画 / DVS event-stream video     #
# --------------------------------------------------------------------------- #
def build_dvs_stream_video(log=print) -> dict:
    """event_camera の DVS シミュレーションをステップごとに可視化した短尺動画を作る.

    ``event_camera.run_event_demo()`` はイベント総数を1枚の静止画へ集計するだけだが、
    Physical AI 系は動画で見せたい(ユーザー方針)ので、内部の ``_render_pan()`` /
    ``_events()`` と**同一のログ輝度差分モデル**をステップごとに評価し、パン中に
    ON(明)/OFF(暗)イベントが実際に流れる様子を mp4 + 軽量 GIF(幅600px)にする。

    honest: フレームは ``event_camera._render_pan()`` が実際にレンダした MuJoCo パン
    シーンそのもの。イベント判定式(log差分・閾値 C・発火画素の reference reset)は
    ``event_camera._events()`` と同じ式をステップ実行するだけで、新しい乱数や捏造値は
    一切導入しない(seed 固定・MuJoCo レンダは決定的)。
    """
    import importlib.util
    if importlib.util.find_spec("mujoco") is None:
        log("[skip] dvs_stream: mujoco is not installed")
        return {"mp4": None, "gif": None, "skipped": "mujoco not installed"}

    import imageio.v2 as imageio
    import numpy as np
    from PIL import Image

    import event_camera as ec

    n_frames = 30
    res = 600  # GIF 幅600px 要件をそのまま満たす解像度でレンダ(アップスケール不要)
    C = 0.15
    frames = ec._render_pan(n_frames=n_frames, res=res, az0=110, az1=170)
    logs = [np.log(f.mean(axis=2) + 0.02) for f in frames]
    ref = logs[0]

    out_frames = []
    cum_total = 0
    for k in range(1, len(logs)):
        diff = logs[k] - ref
        pos = diff > C     # ON: 明るくなった画素
        neg = diff < -C    # OFF: 暗くなった画素
        cum_total += int(pos.sum() + neg.sum())
        ref = np.where(pos | neg, logs[k], ref)   # event_camera._events() と同じ reset

        base = frames[k]
        overlay = np.zeros_like(base)
        overlay[..., 1][pos] = 1.0; overlay[..., 2][pos] = 1.0   # ON -> teal
        overlay[..., 0][neg] = 1.0; overlay[..., 2][neg] = 1.0   # OFF -> magenta
        mask = pos | neg
        vis = base.copy()
        vis[mask] = 0.20 * base[mask] + 0.80 * overlay[mask]
        out_frames.append(np.clip(vis * 255.0 + 0.5, 0, 255).astype(np.uint8))

    log(f"dvs_stream: rendered {n_frames} pan frames -> {len(out_frames)} event frames, "
        f"cumulative events={cum_total}")

    mp4_path = os.path.join(MEDIA_DIR, "dvs_stream.mp4")
    imageio.mimwrite(mp4_path, out_frames, fps=8, codec="libx264", quality=8,
                      macro_block_size=1, pixelformat="yuv420p")
    mp4_size = os.path.getsize(mp4_path)
    log(f"dvs_stream mp4: {mp4_path} ({mp4_size / 1e6:.2f} MB)")

    gif_path = os.path.join(MEDIA_DIR, "dvs_stream.gif")
    gif_width = 600
    duration_ms = int(round(1000.0 / 8))
    gif_size = -1
    for colors in (256, 192, 128, 96, 64):
        pil_frames = []
        for f in out_frames:
            im = Image.fromarray(f, "RGB")
            if im.width != gif_width:
                gh = round(im.height * gif_width / im.width)
                im = im.resize((gif_width, gh), Image.LANCZOS)
            pil_frames.append(im.convert("P", palette=Image.ADAPTIVE, colors=colors))
        pil_frames[0].save(gif_path, save_all=True, append_images=pil_frames[1:],
                            duration=duration_ms, loop=0, disposal=2, optimize=True)
        gif_size = os.path.getsize(gif_path)
        if gif_size <= 2_000_000:
            break
        log(f"dvs_stream gif {gif_size / 1e6:.2f} MB > 2MB budget at colors={colors}, "
            f"retrying with fewer colors")
    log(f"dvs_stream gif: {gif_path} ({gif_size / 1e6:.2f} MB)")

    # honest verification: read both back and count real frames (捏造でないことの実測確認)
    mp4_reader = imageio.get_reader(mp4_path)
    mp4_n, mp4_shape = 0, None
    for fr in mp4_reader:
        if mp4_shape is None:
            mp4_shape = tuple(np.asarray(fr).shape)
        mp4_n += 1
    mp4_reader.close()

    gif_reader = imageio.get_reader(gif_path)
    gif_n, gif_shape = 0, None
    for fr in gif_reader:
        if gif_shape is None:
            gif_shape = tuple(np.asarray(fr).shape)
        gif_n += 1
    gif_reader.close()

    log(f"dvs_stream verify: mp4 {mp4_n} frames {mp4_shape} | gif {gif_n} frames {gif_shape}")
    return {
        "mp4": mp4_path, "mp4_bytes": mp4_size, "mp4_n": mp4_n, "mp4_shape": mp4_shape,
        "gif": gif_path, "gif_bytes": gif_size, "gif_n": gif_n, "gif_shape": gif_shape,
        "n_events": cum_total,
    }


# --------------------------------------------------------------------------- #
# 6) op 分類マップ(treemap)/ operator taxonomy treemap                        #
# --------------------------------------------------------------------------- #
def _squarify(sizes, x, y, w, h):
    """Squarified treemap layout (Bruls/Huizing/van Wijk 1999 algorithm).

    Minimal from-scratch reimplementation (no external ``squarify`` dependency
    installed in this env) — takes areas already normalised to sum to ``w*h``
    and returns a list of (x, y, dx, dy) rects in the same order as ``sizes``.
    """
    sizes = [float(s) for s in sizes]
    if not sizes:
        return []
    if len(sizes) == 1:
        return _squarify_layout(sizes, x, y, w, h)

    def worst(row, x, y, w, h):
        rects = _squarify_layout(row, x, y, w, h)
        return max(max(r[2] / r[3], r[3] / r[2]) for r in rects)

    i = 1
    while i < len(sizes) and worst(sizes[:i], x, y, w, h) >= worst(sizes[:i + 1], x, y, w, h):
        i += 1
    row = sizes[:i]
    rest = sizes[i:]
    row_rects = _squarify_layout(row, x, y, w, h)
    covered = sum(row)
    if w >= h:
        row_w = covered / h
        nx, ny, nw, nh = x + row_w, y, w - row_w, h
    else:
        row_h = covered / w
        nx, ny, nw, nh = x, y + row_h, w, h - row_h
    return row_rects + _squarify(rest, nx, ny, nw, nh)


def _squarify_layout(row, x, y, w, h):
    covered = sum(row)
    rects = []
    if w >= h:
        row_w = covered / h if h else 0.0
        cy = y
        for s in row:
            rh = s / row_w if row_w else 0.0
            rects.append((x, cy, row_w, rh))
            cy += rh
    else:
        row_h = covered / w if w else 0.0
        cx = x
        for s in row:
            rw = s / row_h if row_h else 0.0
            rects.append((cx, y, rw, row_h))
            cx += rw
    return rects


def _treemap_rects(counts: dict, x, y, w, h):
    """counts {label: n} -> list of (label, n, (rx, ry, rw, rh)), largest first."""
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    sizes = [float(v) for _, v in items]
    total = sum(sizes)
    area = w * h
    norm_sizes = [s * area / total for s in sizes]
    rects = _squarify(norm_sizes, x, y, w, h)
    return list(zip(labels, [v for _, v in items], rects))


def build_op_taxonomy(log=print) -> dict:
    """ops.py(2D)+ops3d.py(3D)の実レジストリからカテゴリ別 op 数を集計し treemap を描く.

    データは実 API から取得する(推測禁止): ``ops.REGISTRY``(2D, ``Op.category``)を
    op 名でデデュープした集合(``ops.RT`` と同じ 731 distinct — REGISTRY には同名
    op が category を跨いで再登録されているものが4件あり、後勝ちで数える)、
    ``ops3d.OPS3D``(3D, 265 op、``category`` フィールド)。合計が記事の実測値
    (731 / 265)と一致することをその場で assert する — 一致しなければ記事の数字か
    レジストリのどちらかが古いので、ここで気づけるようにしてある。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from collections import Counter

    import ops
    import ops3d

    # 2D: REGISTRY は同名 op が複数 category に再登録されているケースがあるため、
    # ops.RT (name -> fn, 後勝ち) と同じデデュープ規則で category を数える。
    name_to_cat = {}
    for op in ops.REGISTRY:
        name_to_cat[op.name] = op.category
    counts_2d = Counter(name_to_cat.values())
    n_2d = sum(counts_2d.values())
    assert n_2d == len(ops.RT), f"2D op count {n_2d} != len(ops.RT) {len(ops.RT)}"
    assert n_2d == 731, f"2D distinct op count drifted: {n_2d} (expected 731 per README/article)"
    assert len(counts_2d) == 46, f"2D category count drifted: {len(counts_2d)} (expected 46)"

    counts_3d = Counter(m["category"] for m in ops3d.OPS3D.values())
    n_3d = sum(counts_3d.values())
    assert n_3d == len(ops3d.OPS3D) == 265, f"3D op count drifted: {n_3d}"
    assert len(counts_3d) == 55, f"3D category count drifted: {len(counts_3d)} (expected 55)"

    bg, fg, muted = "#0b0d12", "#e7e9ee", "#8b91a0"
    fig, axes = plt.subplots(1, 2, figsize=(20, 11), facecolor=bg)

    def _draw(ax, counts, title, n_total, cmap_name):
        cmap = plt.get_cmap(cmap_name)
        items = _treemap_rects(counts, 0.0, 0.0, 100.0, 100.0)
        for i, (label, n, (rx, ry, rw, rh)) in enumerate(items):
            color = cmap(0.15 + 0.75 * (i / max(1, len(items) - 1)))
            ax.add_patch(plt.Rectangle((rx, ry), rw, rh, facecolor=color,
                                        edgecolor=bg, linewidth=1.4))
            # 小さすぎる矩形はラベルを省略(読めない文字の詰め込みを避ける)
            if rw > 6.0 and rh > 4.5:
                fontsize = 6.5 + 3.0 * min(1.0, (rw * rh) / 600.0)
                txt_color = "#0b0d12" if sum(color[:3]) > 1.6 else "#f2f2f2"
                ax.text(rx + rw / 2, ry + rh / 2, f"{label}\n{n}", ha="center", va="center",
                        color=txt_color, fontsize=fontsize, linespacing=1.3)
        ax.set_xlim(0, 100); ax.set_ylim(0, 100)
        ax.invert_yaxis()
        ax.axis("off")
        ax.set_title(f"{title}  —  {len(counts)} categories, {n_total} ops", color=fg, fontsize=14, pad=10)

    _draw(axes[0], counts_2d, "2D op registry (ops.py)", n_2d, "Blues")
    _draw(axes[1], counts_3d, "3D op registry (ops3d.py)", n_3d, "Oranges")

    fig.suptitle(f"Fullseye — operator taxonomy: {n_2d} 2D ops / {n_3d} 3D ops "
                 f"({n_2d + n_3d} total, measured from the live registry)",
                 color=fg, fontsize=16, y=0.995)
    fig.text(0.5, 0.01, "area = op count per category (squarified treemap, matplotlib, no mockup data)",
              ha="center", color=muted, fontsize=9)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    out_path = os.path.join(ASSETS_DIR, "op_taxonomy.png")
    fig.savefig(out_path, dpi=110, facecolor=bg)
    plt.close(fig)
    log(f"op_taxonomy: {out_path} | 2D {len(counts_2d)} cats / {n_2d} ops, "
        f"3D {len(counts_3d)} cats / {n_3d} ops")
    return {"path": out_path, "n_2d": n_2d, "n_3d": n_3d,
            "n_cats_2d": len(counts_2d), "n_cats_3d": len(counts_3d)}


# --------------------------------------------------------------------------- #
# 7) HALCON カバレッジ 章別バー / HALCON coverage bar chart by chapter        #
# --------------------------------------------------------------------------- #
def build_halcon_coverage_chart(log=print) -> dict:
    """章別 HALCON operator カバー率を実測して横棒で描く.

    ``fullseye/data/halcon_graph.json`` の ``covered`` フィールドは古い/別基準の
    スナップショットで、実際に読むと 252/2313 (10.9%) にしかならず記事の実測値
    (982/2313=42.5%、``docs/HALCON_COVERAGE.md`` の一次ソース)と一致しない
    (honest disclosure — 指示された参照先を鵜呑みにせず実データで確認した結果)。
    ``docs/HALCON_COVERAGE.md`` を実際に生成しているのは ``halcon_coverage.py``
    (``data/halcon_operators.json`` の実スクレイプ結果 + ``Op.halcon`` 突合)なので、
    それをその場で再実行して真の章別 covered/total を取り、記事に既に書かれている
    982/2313 の数字とも突き合わせて assert する。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import re

    import halcon_coverage as hc
    import ops

    data = hc.load_operators(hc.JSON_DEFAULT)
    a = hc.analyze(data, ops.REGISTRY)
    n_cov, n_real = len(a["covered"]), a["n_real"]
    pct = 100.0 * n_cov / n_real if n_real else 0.0

    # honest note: 章別 covered の合計は全体 covered 数と一致しない — 1 op が複数
    # chapter に属するケースがある(`op["chapters"]` はリスト)ため、章別に足し合わせると
    # 重複計上される。これは halcon_coverage.py 自体の per_chapter 仕様どおりで、
    # ここでは「グラフの各バーが analyze() の生データそのもの」であることだけ確認する。
    chapter_cov_sum = sum(cov for cov, _ in a["per_chapter"].values())
    assert chapter_cov_sum >= n_cov, (
        f"per-chapter covered sum {chapter_cov_sum} should be >= overall distinct covered {n_cov} "
        "(chapters overlap, so sum is expected to be >=, never <)")

    # 既に記事に書かれている数字(docs/HALCON_COVERAGE.md, README.md)とも一致するか確認。
    # チェックサム目的であって、ここから数字を「借りて」はいない(上のライブ計算が正)。
    md_path = os.path.join(REPO, "docs", "HALCON_COVERAGE.md")
    if os.path.exists(md_path):
        with open(md_path, encoding="utf-8") as fh:
            md_text = fh.read()
        m = re.search(r"maps to (\d+) / (\d+) HALCON operators \(([\d.]+)%\)", md_text)
        if m:
            doc_cov, doc_real, doc_pct = int(m.group(1)), int(m.group(2)), float(m.group(3))
            assert (doc_cov, doc_real) == (n_cov, n_real), (
                f"live measurement {n_cov}/{n_real} disagrees with docs/HALCON_COVERAGE.md "
                f"{doc_cov}/{doc_real} — the doc is stale, regenerate it with halcon_coverage.py")
            log(f"cross-check OK vs docs/HALCON_COVERAGE.md: {doc_cov}/{doc_real} ({doc_pct}%)")

    items = sorted(a["per_chapter"].items(), key=lambda kv: (kv[1][0] / kv[1][1] if kv[1][1] else 0.0),
                   reverse=True)
    chapters = [k for k, _ in items]
    covs = [v[0] for _, v in items]
    tots = [v[1] for _, v in items]
    ratios = [c / t if t else 0.0 for c, t in zip(covs, tots)]

    bg, fg, muted = "#0b0d12", "#e7e9ee", "#8b91a0"
    n = len(chapters)
    fig, ax = plt.subplots(figsize=(14, max(6.5, 0.34 * n)), facecolor=bg)
    ax.set_facecolor(bg)
    y = np.arange(n)
    bar_color = "#5aa9e6"
    ax.barh(y, ratios, color=bar_color, height=0.68)
    ax.set_yticks(y)
    ax.set_yticklabels(chapters, color=fg, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("coverage ratio (covered / total, per HALCON top-level chapter)", color=muted, fontsize=9)
    ax.tick_params(axis="x", colors=muted)
    for spine in ax.spines.values():
        spine.set_color(muted)
    ax.grid(axis="x", color=muted, alpha=0.25, linewidth=0.6)
    for yi, (c, t, r) in enumerate(zip(covs, tots, ratios)):
        ax.text(min(r + 0.015, 0.97), yi, f"{c}/{t}", va="center", ha="left",
                color=fg, fontsize=8)

    ax.set_title(f"Fullseye — HALCON operator coverage by chapter: "
                 f"{n_cov}/{n_real} operators ({pct:.1f}%)\n"
                 f"measured live from data/halcon_operators.json + Op.halcon",
                 color=fg, fontsize=13, pad=12)
    fig.tight_layout()
    out_path = os.path.join(ASSETS_DIR, "halcon_coverage_chart.png")
    fig.savefig(out_path, dpi=110, facecolor=bg)
    plt.close(fig)
    log(f"halcon_coverage_chart: {out_path} | {n_cov}/{n_real} ({pct:.1f}%), {n} chapters")
    return {"path": out_path, "n_covered": n_cov, "n_real": n_real, "pct": pct, "n_chapters": n}


# --------------------------------------------------------------------------- #
# 8) 2D op 出力サンプラー / 2D op output sampler (24 tiles, one per category) #
# --------------------------------------------------------------------------- #
def _pick_sampler_ops(registry, apply_fn, img, n=24, log=print):
    """カテゴリごとに REGISTRY 登録順で最初に「実際に動く」op を機械的に選ぶ.

    見た目で選ばない(honest な機械選択): REGISTRY を先頭から走査してカテゴリの
    初出順を記録し、各カテゴリの中で最初に ``apply_fn(img, op.name, ...)`` が
    例外なく通った op を採用する。動かない op(型の相性が悪い等)は同カテゴリ内
    の次候補へフォールバックし、カテゴリ全滅ならそのカテゴリごと飛ばす。
    """
    from collections import OrderedDict
    cat_order, cat_ops, seen = [], OrderedDict(), set()
    for op in registry:
        if op.category not in cat_ops:
            cat_ops[op.category] = []
            cat_order.append(op.category)
        if op.name in seen:
            continue
        seen.add(op.name)
        cat_ops[op.category].append(op)

    chosen, skipped = [], []
    for cat in cat_order:
        picked = None
        for op in cat_ops[cat]:
            try:
                out = apply_fn(img, op.name, a=0.5, b=0.5)
            except Exception as exc:
                skipped.append((cat, op.name, str(exc)))
                continue
            picked = (cat, op.name, out)
            break
        if picked is not None:
            chosen.append(picked)
        if len(chosen) >= n:
            break
    return chosen, skipped


def _render_sampler_tile(ax, cat, name, out, img_shape, bg, fg, muted, log=print):
    import numpy as np
    from scipy import ndimage

    caption = ""
    if isinstance(out, dict) and "cs" in out and "shape" in out:
        H, W = out["shape"]
        mask = np.zeros((H, W), dtype=bool)
        n_pts = 0
        for c in out["cs"]:
            c = np.asarray(c)
            if c.size == 0:
                continue
            rr = np.clip(np.round(c[:, 0]).astype(int), 0, H - 1)
            cc = np.clip(np.round(c[:, 1]).astype(int), 0, W - 1)
            mask[rr, cc] = True
            n_pts += len(rr)
        mask = ndimage.binary_dilation(mask, iterations=1)
        vis = np.full((H, W, 3), 0.08)
        vis[mask] = [1.0, 0.3, 0.2]
        ax.imshow(vis)
        caption = f"XLD contour dict: {len(out['cs'])} curves, {n_pts} pts"
    elif isinstance(out, np.ndarray) and out.ndim == 2 and out.shape == tuple(img_shape):
        lo, hi = float(out.min()), float(out.max())
        ax.imshow(out, cmap="gray", vmin=lo, vmax=hi if hi > lo else lo + 1e-6)
        caption = f"image [{lo:.2f}, {hi:.2f}]"
    elif isinstance(out, np.ndarray) and out.ndim == 3 and out.shape[-1] == 3:
        ax.imshow(np.clip(out, 0.0, 1.0))
        caption = f"color {out.shape[0]}x{out.shape[1]}"
    else:
        ax.imshow(np.full((10, 10), 0.07), cmap="gray", vmin=0, vmax=1)
        if isinstance(out, (float, int, np.floating, np.integer)):
            txt = f"{float(out):.4f}"
            caption = "feature (scalar)"
        else:
            arr = np.asarray(out).ravel()
            txt = "\n".join(f"{v:.3f}" for v in arr[:4])
            caption = f"feature (vector, shape={np.asarray(out).shape})"
        ax.text(0.5, 0.5, txt, ha="center", va="center", color="#ffd27a",
                fontsize=13, fontweight="bold", transform=ax.transAxes)
    ax.axis("off")
    ax.set_title(name, color=fg, fontsize=10, pad=5)
    ax.text(0.5, -0.05, f"[{cat}] {caption}", transform=ax.transAxes,
            ha="center", va="top", color=muted, fontsize=7.2)


def build_op_sampler_2d(log=print) -> dict:
    """coins サンプル画像へ 24 カテゴリ代表 op を実際に適用し 4x6 タイルで並べる.

    op は REGISTRY 登録順のカテゴリ初出順で、各カテゴリ最初に動く op を機械的に
    選ぶ(``_pick_sampler_ops``)。手描き無し・全タイルが ``fullseye.apply`` の
    本物の戻り値(image/region は画像、feature はスカラー数値焼き込み、contour は
    実 XLD 点の焼き込み)。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import fullseye
    import ops
    import sample_images as si

    img = si.load("coins")
    chosen, skipped = _pick_sampler_ops(ops.REGISTRY, fullseye.apply, img, n=24, log=log)
    if skipped:
        log(f"op_sampler_2d: {len(skipped)} op(s) skipped (raised on this input):")
        for cat, name, err in skipped[:10]:
            log(f"  - [{cat}] {name}: {err}")
    if len(chosen) < 24:
        log(f"[warn] op_sampler_2d: only {len(chosen)}/24 categories yielded a runnable op")

    bg, fg, muted = "#0b0d12", "#e7e9ee", "#8b91a0"
    ncols, nrows = 6, -(-len(chosen) // 6)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.0 * ncols, 3.55 * nrows), facecolor=bg)
    axes = axes.ravel()
    for ax, (cat, name, out) in zip(axes, chosen):
        _render_sampler_tile(ax, cat, name, out, img.shape, bg, fg, muted, log=log)
    for ax in axes[len(chosen):]:
        ax.axis("off")

    fig.suptitle(f"Fullseye — 2D op sampler: {len(chosen)} categories on `coins` "
                 f"(one representative op per category, real outputs)", color=fg, fontsize=15, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    out_path = os.path.join(ASSETS_DIR, "op_sampler_2d.png")
    fig.savefig(out_path, dpi=62, facecolor=bg)
    plt.close(fig)
    log(f"op_sampler_2d: {out_path} | {len(chosen)} tiles: "
        + ", ".join(f"{cat}:{name}" for cat, name, _ in chosen))
    return {"path": out_path, "n_tiles": len(chosen),
            "ops": [(cat, name) for cat, name, _ in chosen], "skipped": skipped}


# --------------------------------------------------------------------------- #
# 9) 3D op 出力サンプラー(余力枠)/ 3D op output sampler (bonus)             #
# --------------------------------------------------------------------------- #
def build_op_sampler_3d(log=print) -> dict:
    """Itokawa 実点群に 3D op(法線/曲率/ダウンサンプル/OBB/凸包)を適用し並べる.

    データ: studio_assets/sample_3d/itokawa_points.npy(実点群、build_itokawa_montage
    と同一ソース)。各 op は ``ops3d.get(name)`` 経由でそのまま呼ぶ(モックアップ禁止)。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    from mpl_toolkits.mplot3d.art3d import Line3DCollection

    import ops3d

    data_path = os.path.join(REPO, "studio_assets", "sample_3d", "itokawa_points.npy")
    if not os.path.exists(data_path):
        log(f"[skip] op_sampler_3d: data missing: {data_path}")
        return {"path": None, "n_tiles": 0}

    pts = np.load(data_path).astype(np.float64)
    pts = pts - pts.mean(axis=0)
    extent = pts.max(axis=0) - pts.min(axis=0)
    diag = float(np.linalg.norm(extent))

    bg, fg, muted = "#0b0d12", "#e7e9ee", "#8b91a0"

    def _style(ax):
        ax.set_facecolor(bg)
        for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
            pane.set_facecolor(bg); pane.set_edgecolor(bg)
        ax.grid(False)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass

    jobs = []

    def job_raw(ax):
        ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=np.linalg.norm(pts, axis=1),
                   cmap="copper", s=4, linewidths=0)
        return f"{len(pts)} pts (raw)"
    jobs.append(("Raw point cloud", "itokawa_points.npy", job_raw))

    def job_normals(ax):
        normals = ops3d.get("estimate_normals")(pts, k=20)
        step = max(1, len(pts) // 300)
        ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=muted, s=3, alpha=0.5, linewidths=0)
        ax.quiver(pts[::step, 0], pts[::step, 1], pts[::step, 2],
                  normals[::step, 0], normals[::step, 1], normals[::step, 2],
                  length=diag * 0.03, color="#55aaff", linewidth=0.6)
        return f"estimate_normals: {len(normals)} normals (k=20 nbhd), {len(pts[::step])} shown"
    jobs.append(("Point normals", "curvature3d.estimate_normals", job_normals))

    def job_shape_index(ax):
        si_vals = ops3d.get("shape_index")(pts, k=20)
        lo, hi = np.percentile(si_vals, [2, 98])
        ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=si_vals, cmap="coolwarm",
                  vmin=lo, vmax=hi, s=4, linewidths=0)
        return f"shape_index: mean {si_vals.mean():.3f}, std {si_vals.std():.3f} (Koenderink)"
    jobs.append(("Shape index", "curvature3d.shape_index", job_shape_index))

    def job_downsample(ax):
        voxel = diag / 25.0
        ds = ops3d.get("voxel_grid_downsample")(pts, voxel_size=voxel)
        ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=muted, s=2, alpha=0.25, linewidths=0)
        ax.scatter(ds[:, 0], ds[:, 1], ds[:, 2], c="#55ff99", s=8, linewidths=0)
        reduction = 100.0 * (1.0 - len(ds) / len(pts))
        return f"voxel_grid_downsample: {len(pts)} -> {len(ds)} pts ({reduction:.0f}% reduction, voxel={voxel:.1f}m)"
    jobs.append(("Voxel downsample", "pcl_filter.voxel_grid_downsample", job_downsample))

    def job_obb(ax):
        obb = ops3d.get("obb")(pts)
        ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=muted, s=3, alpha=0.4, linewidths=0)
        corners = obb["corners"]
        edges = [(0, 1), (0, 2), (1, 3), (2, 3), (4, 5), (4, 6), (5, 7), (6, 7),
                 (0, 4), (1, 5), (2, 6), (3, 7)]
        segs = [(corners[i], corners[j]) for i, j in edges]
        ax.add_collection3d(Line3DCollection(segs, colors="#ff5555", linewidths=1.3))
        ext = obb["extents"]
        return f"obb: extents {ext[0]:.0f}x{ext[1]:.0f}x{ext[2]:.0f} m (match3d.obb, oriented box)"
    jobs.append(("Oriented bounding box", "pcseg.obb", job_obb))

    def job_hull(ax):
        verts, faces = ops3d.get("convex_hull")(pts)
        ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=muted, s=2, alpha=0.3, linewidths=0)
        tri = verts[faces]
        ax.add_collection3d(Line3DCollection(
            np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]], axis=0),
            colors="#ffd27a", linewidths=0.35, alpha=0.7))
        return f"convex_hull: {len(verts)} verts, {len(faces)} tris (meshrepair.convex_hull)"
    jobs.append(("Convex hull", "meshrepair.convex_hull", job_hull))

    panels, skipped = [], []
    for title, src, job_fn in jobs:
        try:
            fig = plt.figure(figsize=(5.4, 5.4), facecolor=bg)
            ax = fig.add_subplot(111, projection="3d")
            _style(ax)
            caption = job_fn(ax)
            ax.view_init(elev=18, azim=35)
            fig.tight_layout()
            out_png = os.path.join(SOURCES_DIR, f"src_3dsampler_{src.split('.')[-1]}.png")
            fig.savefig(out_png, dpi=110, facecolor=bg)
            plt.close(fig)
            panels.append((title, src, out_png, caption))
        except Exception as exc:
            skipped.append((title, src, str(exc)))
            log(f"[skip] op_sampler_3d panel {title} ({src}): {exc}")

    if not panels:
        return {"path": None, "n_tiles": 0, "skipped": skipped}

    ncols = 3
    nrows = -(-len(panels) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.0 * ncols, 5.6 * nrows), facecolor=bg)
    axes = axes.ravel() if len(panels) > 1 else [axes]
    for ax, (title, src, out_png, caption) in zip(axes, panels):
        img = plt.imread(out_png)
        ax.imshow(img)
        ax.axis("off")
        ax.set_title(title, color=fg, fontsize=11, pad=6)
        ax.text(0.5, -0.03, f"{src} — {caption}", transform=ax.transAxes,
                ha="center", va="top", color=muted, fontsize=7.8, wrap=True)
    for ax in axes[len(panels):]:
        ax.axis("off")

    fig.suptitle("Fullseye — 3D op sampler on asteroid 25143 Itokawa (real point cloud, not a mockup)",
                 color=fg, fontsize=14.5, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_path = os.path.join(ASSETS_DIR, "op_sampler_3d.png")
    fig.savefig(out_path, dpi=110, facecolor=bg)
    plt.close(fig)
    log(f"op_sampler_3d: {out_path} | panels={len(panels)} skipped={len(skipped)}")
    return {"path": out_path, "n_tiles": len(panels), "skipped": skipped}


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

    print("\n-- 6) op_taxonomy (treemap) --")
    taxonomy = build_op_taxonomy()

    print("\n-- 7) halcon_coverage_chart --")
    halcon_chart = build_halcon_coverage_chart()

    print("\n-- 8) op_sampler_2d --")
    sampler_2d = build_op_sampler_2d()

    print("\n-- 9) op_sampler_3d (bonus) --")
    sampler_3d = build_op_sampler_3d()

    print("\n-- 4) thumbnails (720px JPG) --")
    thumbs = build_thumbnails()

    print("\n-- 5) dvs_stream video (event camera) --")
    dvs = build_dvs_stream_video()

    print("\n== summary ==")
    all_paths = [physical["path"], vision["path"], *heroes]
    if itokawa["path"]:
        all_paths.append(itokawa["path"])
    all_paths.append(taxonomy["path"])
    all_paths.append(halcon_chart["path"])
    all_paths.append(sampler_2d["path"])
    if sampler_3d.get("path"):
        all_paths.append(sampler_3d["path"])
    all_paths.extend(thumbs)
    for path in all_paths:
        size = os.path.getsize(path)
        print(f"{path}  ({size/1024:.1f} KiB)")
    if dvs.get("mp4"):
        print(f"{dvs['mp4']}  ({dvs['mp4_bytes']/1024:.1f} KiB, "
              f"{dvs['mp4_n']} frames, {dvs['mp4_shape']})")
        print(f"{dvs['gif']}  ({dvs['gif_bytes']/1024:.1f} KiB, "
              f"{dvs['gif_n']} frames, {dvs['gif_shape']})")
    elif dvs.get("skipped"):
        print(f"skipped dvs_stream: {dvs['skipped']}")
    if physical["skipped"]:
        print("skipped physical-AI panels:")
        for title, module, reason in physical["skipped"]:
            print(f"  - {title} ({module}): {reason}")
    if itokawa["skipped"]:
        print("skipped itokawa panels:")
        for title, module, reason in itokawa["skipped"]:
            print(f"  - {title} ({module}): {reason}")
    print(f"\nop_taxonomy: 2D {taxonomy['n_cats_2d']} cats/{taxonomy['n_2d']} ops, "
          f"3D {taxonomy['n_cats_3d']} cats/{taxonomy['n_3d']} ops")
    print(f"halcon_coverage: {halcon_chart['n_covered']}/{halcon_chart['n_real']} "
          f"({halcon_chart['pct']:.1f}%) across {halcon_chart['n_chapters']} chapters")
    print(f"op_sampler_2d: {sampler_2d['n_tiles']} tiles -> "
          + ", ".join(f"{c}:{n}" for c, n in sampler_2d["ops"]))
    if sampler_3d.get("path"):
        print(f"op_sampler_3d: {sampler_3d['n_tiles']} tiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
