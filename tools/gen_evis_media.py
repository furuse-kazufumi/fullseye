"""Generate article media: Fullseye ops running on real evis experiment footage.

The evis musculoskeletal humanoid (evis_chopstick project) captured 241 frames of
binocular vision (IPD 64 mm / fovy 60 deg, rendered from the robot's own eye
cameras) while its 48-joint hand strikes chopsticks at a bean (ChopMimic scene).
This script feeds those REAL captured frames through Fullseye's registered ops
and renders honest, verifiable videos for the Qiita overview article:

  stereo : eyeL/eyeR pair -> fs.disparity_sgm -> fs.speckle_filter ->
           fs.fill_disparity -> fs.colorize_disparity / fs.depth_from_disparity
           -> fs.colorize_depth.  Per-frame the bean's distance estimated from
           the Fullseye disparity is compared against the simulator ground
           truth stored in chop_vision_meta.json (validation printed at end).
  track  : chopstick-tip camera -> green-margin channel -> fs.segment_objects
           -> fs.draw_objects, with the tracked bean centroid trail.  Validated
           against the ground-truth bean pixel centroid in the meta file.
  legacy : re-encode one existing evis gif (700-muscle activation heatmap) to
           H.264 mp4 for the article (no Fullseye processing - honest label).

Source frames are read from C:/dev/projects/evis_chopstick/out/chop_vision_frames
READ-ONLY (nothing there is modified).  Outputs land in
docs/articles/assets/media/evis_*.mp4 plus stills/thumbs in docs/articles/assets/.

Run:  py -3.11 tools/gen_evis_media.py --subjects stereo,track,legacy
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import imageio.v2 as iio  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import fullseye as fs  # noqa: E402

EVIS = Path("C:/dev/projects/evis_chopstick/out")
FRAMES = EVIS / "chop_vision_frames"
META = EVIS / "chop_vision_meta.json"
MEDIA = ROOT / "docs" / "articles" / "assets" / "media"
ASSETS = ROOT / "docs" / "articles" / "assets"
LEGACY_GIF = Path(
    "C:/dev/projects/onocollo-complete/docs/qiita/20260822_g1_evis/evis_muscle_heatmap.gif"
)

HUD_H = 28
FONT = None


def _font(size=13):
    global FONT
    if FONT is None:
        try:
            FONT = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", size)
        except OSError:
            FONT = ImageFont.load_default()
    return FONT


def _hud(width: int, text: str) -> np.ndarray:
    """Dark HUD bar with the op-chain / measurement text."""
    bar = Image.new("RGB", (width, HUD_H), (24, 26, 30))
    d = ImageDraw.Draw(bar)
    d.text((8, 6), text, fill=(220, 220, 210), font=_font())
    return np.asarray(bar)


def _label(img: np.ndarray, text: str) -> np.ndarray:
    """Small caption strip drawn onto the top-left of a panel."""
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    tw = d.textlength(text, font=_font(12))
    d.rectangle([2, 2, 8 + tw, 18], fill=(24, 26, 30))
    d.text((5, 4), text, fill=(240, 240, 230), font=_font(12))
    return np.asarray(im)


def _u8(a: np.ndarray) -> np.ndarray:
    if a.dtype == np.uint8:
        return a
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def _writer(path: Path, fps: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    return iio.get_writer(
        str(path), fps=fps, codec="libx264", quality=7,
        pixelformat="yuv420p", macro_block_size=2,
    )


def _stills(frame_u8: np.ndarray, stem: str):
    """Representative still (png) + 720px-wide thumb (jpg q85)."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    still = ASSETS / f"{stem}_still.png"
    thumb = ASSETS / f"{stem}_thumb.jpg"
    im = Image.fromarray(frame_u8)
    im.save(still)
    w, h = im.size
    im.resize((720, max(2, round(h * 720 / w))), Image.LANCZOS).save(
        thumb, quality=85)
    print(f"  still -> {still}\n  thumb -> {thumb}")


def gen_stereo(meta: dict, fps: int = 20, step: int = 1):
    """eyeL | Fullseye SGM disparity | Fullseye metric depth, with live bean-range
    readout (Fullseye estimate vs simulator ground truth)."""
    f_half = meta["f_px_full"] / 2.0          # frames on disk are 320x240 (half res)
    baseline_mm = meta["ipd_mm"]              # 64.0
    frames = meta["frames"]
    out = MEDIA / "evis_stereo_fullseye.mp4"
    wr = _writer(out, fps)
    errs, n_valid = [], 0
    rep = None
    for fr in frames[::step]:
        k = fr["k"]
        L = iio.imread(FRAMES / f"eyel_{k:04d}.png")[..., :3]
        R = iio.imread(FRAMES / f"eyer_{k:04d}.png")[..., :3]
        Lg = L.mean(-1) / 255.0
        Rg = R.mean(-1) / 255.0
        disp_raw = fs.disparity_sgm(Lg, Rg, max_disp=40, window=5)
        # display map: cleaned + hole-filled; measurement uses disp_raw because
        # the bean region (~14 px at half res) is smaller than the speckle
        # min_size and would be invalidated, leaving background disparity.
        disp, valid = fs.speckle_filter(disp_raw, max_diff=1.0, min_size=60)
        disp = fs.fill_disparity(disp, valid)
        disp_col = _u8(fs.colorize_disparity(disp))
        depth_mm = fs.depth_from_disparity(disp, focal=f_half, baseline=baseline_mm,
                                           min_disp=0.5)
        depth_col = _u8(fs.colorize_depth(np.clip(depth_mm, 250.0, 2500.0)))

        # --- validation: bean range from Fullseye disparity vs ground truth ---
        hud_extra = "bean not in view"
        vis_both = min(fr.get("eyeL_n", 0), fr.get("eyeR_n", 0)) >= 10
        if fr.get("eyeL_c") and fr.get("true_Z_mm") and vis_both:
            bx, by = fr["eyeL_c"][0] / 2.0, fr["eyeL_c"][1] / 2.0
            iy, ix = int(round(by)), int(round(bx))
            win = disp_raw[max(0, iy - 3):iy + 4, max(0, ix - 3):ix + 4]
            d_med = float(np.median(win)) if win.size else 0.0
            if d_med > 0.5:
                est = f_half * baseline_mm / d_med
                true = fr["true_Z_mm"]
                err = abs(est - true) / true * 100.0
                errs.append(err)
                n_valid += 1
                hud_extra = f"bean {est:5.0f}mm  truth {true:5.0f}mm  err {err:4.1f}%"
        hud = _hud(L.shape[1] * 3,
                   "fullseye: disparity_sgm > speckle_filter > fill_disparity > "
                   f"depth_from_disparity   t={fr['t']:5.2f}s   {hud_extra}")
        row = np.concatenate([
            _label(L, "evis left eye (real capture)"),
            _label(disp_col, "fullseye disparity"),
            _label(depth_col, "fullseye depth"),
        ], axis=1)
        frame = np.concatenate([row, hud], axis=0)
        wr.append_data(frame)
        if k == 60:
            rep = frame
    wr.close()
    print(f"stereo -> {out}  ({out.stat().st_size/1e6:.1f} MB)")
    if errs:
        e = np.array(errs)
        print(f"  VALIDATION: bean range vs truth on {n_valid}/{len(frames[::step])} "
              f"frames  median err {np.median(e):.2f}%  p90 {np.percentile(e, 90):.2f}%  "
              f"max {np.max(e):.2f}%  frames within 5%: {(e < 5).mean()*100:.1f}%")
    if rep is not None:
        _stills(rep, "evis_stereo_fullseye")


def gen_track(meta: dict, fps: int = 20, step: int = 1):
    """third-person context | tip camera with fs.segment_objects bean tracking."""
    frames = meta["frames"]
    out = MEDIA / "evis_bean_track_fullseye.mp4"
    wr = _writer(out, fps)
    trail: list[tuple[float, float]] = []
    n_det, px_errs = 0, []
    rep = None
    for fr in frames[::step]:
        k = fr["k"]
        tp = iio.imread(FRAMES / f"tp_{k:04d}.png")[..., :3] / 255.0
        tip = iio.imread(FRAMES / f"tip_{k:04d}.png")[..., :3] / 255.0
        green = np.clip(tip[..., 1] - np.maximum(tip[..., 0], tip[..., 2]), 0, 1)
        objs = fs.segment_objects(green, threshold=0.08, min_area=4)
        # the bean is the most circular candidate of plausible size
        objs = [o for o in objs if 15 <= o["area"] <= 2500]
        objs.sort(key=lambda o: -o["circularity"])
        bean = objs[:1]
        vis = fs.draw_objects(tip, bean, box_color=(1.0, 0.25, 0.25))
        vis = _u8(vis)
        hud_extra = "bean lost"
        if bean:
            cy, cx = bean[0]["centroid"]
            trail.append((cx, cy))
            n_det += 1
            if fr.get("tip_c"):
                # meta tip_c is (x, y) col-major from the original capture script
                gx, gy = fr["tip_c"][0], fr["tip_c"][1]
                px_errs.append(float(np.hypot(cx - gx, cy - gy)))
            hud_extra = f"bean px=({cx:5.1f},{cy:5.1f})  area {bean[0]['area']:.0f}"
        im = Image.fromarray(vis)
        d = ImageDraw.Draw(im)
        if len(trail) >= 2:
            d.line([(x, y) for x, y in trail[-90:]], fill=(255, 210, 60), width=2)
        vis = np.asarray(im)
        hud = _hud(480, "fullseye: segment_objects > draw_objects  (tip cam)   "
                        f"t={fr['t']:5.2f}s   {hud_extra}")
        row = np.concatenate([
            _label(_u8(tp), "third person (context)"),
            _label(vis, "fullseye bean tracking"),
        ], axis=1)
        frame = np.concatenate([row, hud], axis=0)
        # x1.5 upscale for readability
        h, w = frame.shape[:2]
        frame = np.asarray(Image.fromarray(frame).resize(
            (int(w * 1.5), int(h * 1.5)), Image.LANCZOS))
        wr.append_data(frame)
        if k == 60:
            rep = frame
    wr.close()
    print(f"track -> {out}  ({out.stat().st_size/1e6:.1f} MB)")
    n = len(frames[::step])
    print(f"  VALIDATION: bean detected {n_det}/{n} frames "
          f"({100*n_det/n:.1f}%)  centroid err vs truth: "
          f"median {np.median(px_errs):.2f}px  max {np.max(px_errs):.2f}px"
          if px_errs else "  VALIDATION: no ground-truth comparisons")
    if rep is not None:
        _stills(rep, "evis_bean_track_fullseye")


def gen_legacy(fps: int = 10):
    """Re-encode the existing 700-muscle activation heatmap gif to mp4 (no
    Fullseye processing - this clip only introduces the evis body itself)."""
    out = MEDIA / "evis_muscle_heatmap.mp4"
    rd = iio.get_reader(str(LEGACY_GIF))
    wr = _writer(out, fps)
    rep = None
    for i, f in enumerate(rd):
        f = np.asarray(f)[..., :3]
        h, w = f.shape[:2]
        f = f[:h - h % 2, :w - w % 2]
        wr.append_data(f)
        if i == 20:
            rep = f
    rd.close()
    wr.close()
    print(f"legacy -> {out}  ({out.stat().st_size/1e6:.1f} MB)")
    if rep is not None:
        _stills(rep, "evis_muscle_heatmap")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--subjects", default="stereo,track",
                    help="comma list from {stereo,track,legacy}")
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--step", type=int, default=1,
                    help="use every Nth source frame")
    args = ap.parse_args()
    subjects = [s.strip() for s in args.subjects.split(",") if s.strip()]
    meta = json.loads(META.read_text(encoding="utf-8"))
    for s in subjects:
        if s == "stereo":
            gen_stereo(meta, fps=args.fps, step=args.step)
        elif s == "track":
            gen_track(meta, fps=args.fps, step=args.step)
        elif s == "legacy":
            gen_legacy()
        else:
            raise SystemExit(f"unknown subject: {s}")


if __name__ == "__main__":
    main()
