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
GALLERY_DIR = os.path.join(REPO, "examples_3d", "_gallery")

SEED = 20260830  # 全生成で固定する乱数種 (再現性) / fixed seed for reproducibility


def _ensure_dirs() -> None:
    os.makedirs(SOURCES_DIR, exist_ok=True)


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

    print("\n== summary ==")
    for path in [physical["path"], vision["path"], *heroes]:
        size = os.path.getsize(path)
        print(f"{path}  ({size/1024:.1f} KiB)")
    if physical["skipped"]:
        print("skipped physical-AI panels:")
        for title, module, reason in physical["skipped"]:
            print(f"  - {title} ({module}): {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
