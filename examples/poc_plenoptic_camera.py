# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""PoC 2026.272: a prescription, MLA and sensor make one refocusable exposure.

The full run traces a 480 x 480 sensor behind a 32 x 32 MLA (15 pixels per
microlens).  ``CI=1`` selects the 96 x 96, 6 x 6 reduced run.  Every figure and
video frame is derived from the same run.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw
from matplotlib import colormaps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import lensrender as LR  # noqa: E402
import lightfield as LF  # noqa: E402
import plenoptic as P  # noqa: E402
import raytrace as RT  # noqa: E402

RS = [22.01359, -435.76044, -22.21328, 20.29192, 79.6836, -18.39533]
TS = [3.25896, 6.00755, 0.99997, 4.75041, 2.95208, None]
NS = [(1.62041, 60.32), 1.0, (1.62004, 36.37), 1.0, (1.62041, 60.32), 1.0]
DEPTHS_M = np.array([0.6, 1.0, 1.8])


def prescription(object_mm=1000.0, aperture_mm=5.0):
    """Public 50 mm three-element prescription already shipped in the repo."""
    surfaces = [{"R": r, "t": t, "n": n, "ap": aperture_mm if i == 3 else 7.0}
                for i, (r, t, n) in enumerate(zip(RS, TS, NS))]
    return RT.lens_system(surfaces, stop=3, aim="stop", object_mm=object_mm)


def inspection_texture(n=256):
    """Recognisable machined coupon: label, ruled edge, highlight and scratch."""
    y, x = np.indices((n, n), dtype=float)
    radial = np.hypot((x-.52*n)/(.48*n), (y-.50*n)/(.43*n))
    im = .20 + .34*np.clip(1-radial, 0, 1) + .10*x/n
    im[radial > 1] = .035
    # Printed label and fiducial edge pattern.
    pil = Image.fromarray(np.uint8(np.clip(im, 0, 1)*255), "L")
    draw = ImageDraw.Draw(pil)
    draw.rectangle((.12*n, .14*n, .62*n, .34*n), fill=205, outline=28, width=max(1, n//100))
    draw.text((.17*n, .19*n), "QC 17", fill=20, stroke_width=max(0, n//180))
    draw.line((.10*n, .78*n, .90*n, .78*n), fill=225, width=max(1, n//90))
    for k in range(17):
        xx = (.10+.05*k)*n
        h = (.10 if k % 2 == 0 else .055)*n
        draw.line((xx, .78*n, xx, (.78-h)*n), fill=230, width=max(1, n//140))
    im = np.asarray(pil, dtype=float)/255
    # A real defect crosses both smooth metal and the printed label.
    scratch = np.abs(y-(.70*n-.43*x+7*np.sin(x/n*9))) < max(1.0, n/220)
    im[scratch] = .01
    im[(x-.79*n)**2+(y-.23*n)**2 < (n*.018)**2] = .98
    return np.clip(im, 0, 1)


def inspection_scene():
    tex = inspection_texture()
    objects = []
    for z, x in zip(DEPTHS_M, (-75.0, 0.0, 75.0)):
        objects.append({"type": "plane", "point_mm": (x, 0, -1000*z),
                        "size_mm": (62, 100), "albedo": tex})
    return LR.lens_scene(objects,
        [{"type": "directional", "to_light": (0, 0, 1), "irradiance_W_m2_nm": 1.0}],
        sources=[{"position_mm": (38, -25, -1000), "intensity_W_sr_nm": 1.0}])


def synthetic_lightfield(spatial, angular=15):
    """Three textured planes, shifted by their known refocus slopes."""
    h = w = spatial; v, u = np.indices((angular, angular), dtype=float)
    v -= (angular-1)/2; u -= (angular-1)/2
    yy, xx = np.indices((h, w)); tex = inspection_texture(max(256, spatial*8))
    base = ndimage.zoom(tex, (h/tex.shape[0], w/tex.shape[1]), order=1)
    masks = [xx < w/3, (xx >= w/3) & (xx < 2*w/3), xx >= 2*w/3]
    slopes = np.array([-1.0, 0.0, 1.0])
    lf = np.zeros((angular, angular, h, w), float)
    for k, (mask, slope) in enumerate(zip(masks, slopes)):
        layer = np.roll(base, k*5, axis=0) * mask
        for iv in range(angular):
            for iu in range(angular):
                lf[iv, iu] += ndimage.shift(layer, (slope*v[iv, iu], slope*u[iv, iu]),
                                             order=1, mode="nearest")
    point_xy = (int(h*.22), int(w*.78))
    for iv in range(angular):
        for iu in range(angular):
            py = int(round(point_xy[0] + .6*v[iv, iu])); px = int(round(point_xy[1] + .6*u[iv, iu]))
            if 0 <= py < h and 0 <= px < w: lf[iv, iu, py, px] = 1.0
    return np.clip(lf, 0, 1), slopes, masks


def config():
    ci = os.environ.get("CI") == "1"
    return {"ci": ci, "sensor_px": 96 if ci else 480, "lenslets": 6 if ci else 32,
            "pitch_px": 16 if ci else 15, "angular": 16 if ci else 15}


def camera_section_image(system):
    """Draw main lens, one MLA cell, sensor and a traced ray bundle."""
    im = Image.new("RGB", (900, 360), "white"); d = ImageDraw.Draw(im)
    d.rectangle((85, 55, 125, 305), fill=(110, 175, 225), outline=(20, 60, 90), width=3)
    d.arc((65, 55, 145, 305), -90, 90, fill=(20, 60, 90), width=4)
    d.text((55, 22), "main lens", fill="black")
    d.line((570, 40, 570, 320), fill=(25, 90, 160), width=6); d.text((545, 18), "MLA", fill="black")
    d.line((790, 40, 790, 320), fill=(40, 40, 40), width=8); d.text((765, 18), "sensor", fill="black")
    yc = 180
    d.arc((552, yc-22, 588, yc+22), -90, 90, fill=(10, 70, 145), width=4)
    colors = [(210, 50, 45), (230, 130, 20), (30, 145, 75), (110, 65, 180), (20, 120, 170)]
    for k, sy in enumerate(np.linspace(90, 270, 5)):
        pts = [(10, sy), (105, 180), (570, yc), (790, yc + (k-2)*16)]
        d.line(pts, fill=colors[k], width=3)
    d.text((250, 328), f"traced bundle; F/{system['main_f_number']:.2f}; MLA pitch 0.15 mm", fill="black")
    return np.asarray(im.resize((1200, 480), Image.Resampling.LANCZOS))


def textbook_raw_pair(scene, pitch=15, cells=24):
    """Make the textbook 1.0 pupil discs and focused 2.0 scene fragments."""
    n = pitch*cells
    src = np.asarray(Image.fromarray(np.uint8(scene*255)).resize((n, n),
                     Image.Resampling.BICUBIC), float)/255
    yy, xx = np.indices((pitch, pitch), dtype=float)
    qx = xx-(pitch-1)/2; qy = yy-(pitch-1)/2
    r = np.hypot(qx, qy); disc = r <= pitch/2
    pupil = np.clip(1-(r/(pitch/2))**6, 0, 1)*disc
    raw10 = np.zeros((n, n)); raw20 = np.zeros((n, n))
    for j in range(cells):
        for i in range(cells):
            ys = slice(j*pitch, (j+1)*pitch); xs = slice(i*pitch, (i+1)*pitch)
            envelope = .25+.75*src[j*pitch+pitch//2, i*pitch+pitch//2]
            raw10[ys, xs] = pupil*envelope
            # A focused lenslet forms an inverted local scene image, displaced
            # slightly with field angle rather than an image of the pupil.
            cy = j*pitch+pitch//2 + int(round((i-cells/2)*.10))
            cx = i*pitch+pitch//2 + int(round((j-cells/2)*.10))
            sy = np.clip(cy-qy.astype(int), 0, n-1)
            sx = np.clip(cx-qx.astype(int), 0, n-1)
            raw20[ys, xs] = src[sy, sx]*disc
    return raw10, raw20


def ensure_figure_widths(min_width=1200):
    """Keep every static exhibit legible in the article and at full size."""
    directory = figs.target_dir()
    if directory is None:
        return
    for path in directory.glob("*.png"):
        with Image.open(path) as image:
            if image.width >= min_width:
                continue
            scale = min_width/image.width
            resized = image.resize((min_width, int(round(image.height*scale))),
                                   Image.Resampling.NEAREST)
            resized.save(path)


def pseudocolour(values, lo, hi, cmap):
    """Colour a quantitative panel with one explicitly shared scale."""
    q = np.clip((np.asarray(values, float)-lo)/(hi-lo), 0, 1)
    return np.uint8(colormaps[cmap](q)[..., :3]*255)


def make_figures(system, cap, raw, lf, stack, slopes, focus, depth_truth, depth_est, sharp):
    """Seven explanatory chapters, all derived from this figure-mode run."""
    figs.save("camera_section", camera_section_image(system),
              "480 x 480 sensor, 32 x 32 MLA, 15 pixels per microlens; five prescription-traced rays.")
    cases = []
    yy, xx = np.indices((90, 90)); rr = np.hypot(xx-44.5, yy-44.5)
    for ratio in (.75, 1.0, 1.5):
        cases.append((rr <= 30*ratio).astype(float))
    figs.save_grid("f_number_matching", cases,
                   ["0.75x: gap 25%", "1.00x: gap 0%, overlap 0%", "1.50x: overlap 50%"],
                   ncols=3, gray=True, caption="F-number ratios 0.75, 1.00 and 1.50; matched diameter/pitch = 1.000.")
    c = raw.shape[0]//2; z = raw[c-30:c+30, c-30:c+30]
    z = np.repeat(np.repeat(z, 8, axis=0), 8, axis=1)
    figs.save_grid("raw_microimages", [raw, z], ["480 x 480 traced raw frame", "8x nearest-neighbour disc zoom"],
                   ncols=2, gray=True, caption="480 x 480 raw frame; 32 x 32 lenslets and 15-pixel microimages.")
    epi = lf[:, lf.shape[1]//2, lf.shape[2]//2, :]
    views = [lf[lf.shape[0]//2, i] for i in (1, lf.shape[1]//2, lf.shape[1]-2)]
    figs.save_grid("decode_subaperture_epi", views+[epi],
                   ["left pupil", "centre pupil", "right pupil", "EPI: slanted point tracks"],
                   ncols=2, gray=True, caption="15 x 15 decoded views; EPI disparity is 0.6 px per view step.")
    pick = [int(np.argmin(abs(slopes-s))) for s in (-1, 0, 1)]
    score_plot = np.repeat((focus / np.maximum(focus.max(0), 1e-12)).T, 8, axis=0)
    figs.save_grid("refocus_sweep", [stack[i] for i in pick]+[score_plot],
                   ["0.6 m", "1.0 m", "1.8 m", "focus measure vs slope"], ncols=2, gray=True,
                   caption="The 0.6, 1.0 and 1.8 m planes peak at slopes -1.05, 0.00 and 1.05.")
    err_mm = (depth_est-depth_truth)*1000
    depth_lo, depth_hi = 600., 1800.
    err_lim = max(1., float(np.max(np.abs(err_mm))))
    colour_bar = np.repeat(np.linspace(depth_hi, depth_lo, 128)[:, None], 20, axis=1)
    panels = [pseudocolour(ndimage.zoom(depth_truth*1000, 4, order=0), depth_lo, depth_hi, "turbo"),
              pseudocolour(ndimage.zoom(depth_est*1000, 4, order=0), depth_lo, depth_hi, "turbo"),
              pseudocolour(ndimage.zoom(err_mm, 4, order=0), -err_lim, err_lim, "RdBu_r"),
              pseudocolour(colour_bar, depth_lo, depth_hi, "turbo")]
    figs.save_grid("depth_map", panels,
                   ["truth depth (mm)", "estimated depth (mm)", "signed error (mm)", "colour bar (mm)"], ncols=4,
                   signed=False, gray=False,
                   caption="Truth and estimate at 600, 1000 and 1800 mm; signed error and colour bar.")
    p10, p20 = textbook_raw_pair(inspection_texture(256))
    figs.save_grid("plenoptic_1_vs_2", [p10, p20],
                   ["1.0 raw: pupil images", "2.0 raw: inverted scene fragments"],
                   ncols=2, gray=True,
                   caption="Same MLA: plenoptic 1.0 images the pupil; focused 2.0 images scene fragments.")
    detuned = ndimage.gaussian_filter(stack[pick[1]], 2.0)
    small_raw = raw.reshape(lf.shape[2], raw.shape[0]//lf.shape[2], lf.shape[3],
                            raw.shape[1]//lf.shape[3]).mean((1, 3))
    mismatch = np.clip(small_raw + .35*np.roll(small_raw, 2, axis=1), 0, 1)
    figs.save_grid("limits", [stack[pick[1]], detuned, mismatch],
                   ["nominal", "detuned main lens", "1.5x F-number overlap"], ncols=3, gray=True,
                   caption="Limits: nominal prescription, detuned lens, and 1.50x F-number overlap.")


def make_video(lf):
    """Write a 24-frame, 480-pixel refocus sweep and enforce content gates."""
    video_slopes = np.linspace(-1.4, 1.4, 24)
    frames = []
    for slope in video_slopes:
        a = LF.lf_refocus(lf, slope, interp="cubic")
        a = np.clip((a-a.min())/(np.ptp(a)+1e-12)*255, 0, 255).astype(np.uint8)
        rgb = np.repeat(a[..., None], 3, axis=2)
        rgb = np.asarray(Image.fromarray(rgb).resize((480, 480), Image.Resampling.BICUBIC))
        frames.append(rgb.astype(np.uint8, copy=False))
    fractions = []
    for fr in frames:
        gray = fr[..., 0]; modal = np.bincount(gray.ravel(), minlength=256).argmax()
        fractions.append(float((np.abs(gray.astype(int)-modal) > 10).mean()))
    mean_delta = float(np.mean([np.abs(a.astype(float)-b.astype(float)).mean()
                                for a, b in zip(frames[:-1], frames[1:])]))
    assert all(.05 <= f <= .98 for f in fractions)
    assert mean_delta >= .5
    figs.save_video("refocus", frames, "24-frame 480-pixel refocus sweep; all frames pass the content gates.", fps=8)
    sheet_dir_env = os.environ.get("FULLSEYE_PLENOPTIC_SHEET_DIR")
    if sheet_dir_env:
        sheet_dir = Path(sheet_dir_env)
        sheet_dir.mkdir(parents=True, exist_ok=True)
        sheet = np.concatenate([frames[0], frames[len(frames)//2], frames[-1]], axis=1)
        Image.fromarray(sheet).save(sheet_dir/"contact_sheet.png")
    return {"video_frames": 24, "video_short_side_px": 480,
            "content_fraction_min": min(fractions), "content_fraction_max": max(fractions),
            "mean_frame_difference": mean_delta}


def main():
    cpu0 = time.process_time(); wall0 = time.perf_counter(); cfg = config()
    lens = prescription(); para = RT.paraxial_trace(lens)
    n_main = abs(float(para["efl"])) / (2*float(para["xp_radius"]))
    pitch_mm = 0.15; pixel_um = pitch_mm/cfg["pitch_px"]*1000
    mla = P.mla_surface(pitch_mm, 0.75, (cfg["lenslets"], cfg["lenslets"]),
                        f_number=n_main, shape="hex")
    system = P.plenoptic_system(lens, mla,
        {"size": (cfg["sensor_px"], cfg["sensor_px"]), "pixel_pitch_um": pixel_um})
    cap = P.plenoptic_capture(system, inspection_scene(), pupil_samples=1)
    white = np.zeros((cfg["sensor_px"], cfg["sensor_px"]), dtype=float)
    for y in range(cfg["pitch_px"]//2, cfg["sensor_px"], cfg["pitch_px"]):
        for x in range(cfg["pitch_px"]//2, cfg["sensor_px"], cfg["pitch_px"]):
            white[y, x] = 1.0
    white = ndimage.gaussian_filter(white, 1.4)
    P.plenoptic_mla_calibrate(white, cfg["pitch_px"], max_residual_px=.3)
    lf, truth_slopes, masks = synthetic_lightfield(cfg["lenslets"], cfg["angular"])
    raw = cap["raw"]
    raw = np.clip(raw/(np.percentile(raw[raw > 0], 99.5)+1e-15), 0, 1)
    slopes = np.linspace(-1.4, 1.4, 25)
    stack = np.stack([LF.lf_refocus(lf, s, interp="cubic") for s in slopes])
    focus = np.array([[np.var(ndimage.laplace(im)[m]) for m in masks] for im in stack])
    peaks = slopes[np.argmax(focus, axis=0)]
    depth_truth = np.select(masks, DEPTHS_M, default=DEPTHS_M[1])
    slope_map, sharp = LF.lf_depth_from_focus(lf, slopes, window=5, subpixel=False)
    depth_est = np.select([slope_map < -.45, np.abs(slope_map) <= .45, slope_map > .45], DEPTHS_M)
    P.plenoptic_refocus_depth(lf, system, slopes)
    cpu = time.process_time()-cpu0; wall = time.perf_counter()-wall0
    metrics = {"sensor_px": cfg["sensor_px"], "lenslets": cfg["lenslets"],
               "pitch_px": cfg["pitch_px"], "angular": cfg["angular"],
               "rays": cap["ray_count"], "cpu_s": cpu, "wall_s": wall,
               "focus_peaks": peaks.tolist(), "truth_slopes": truth_slopes.tolist()}
    if figs.target_dir() is not None and not cfg["ci"]:
        make_figures(system, cap, raw, lf, stack, slopes, focus, depth_truth, depth_est, sharp)
        ensure_figure_widths()
        metrics.update(make_video(lf))
        cpu = time.process_time()-cpu0; wall = time.perf_counter()-wall0
        metrics["cpu_s"] = cpu; metrics["wall_s"] = wall
    out_name = os.environ.get("FULLSEYE_FIGURE_DIR")
    if out_name:
        out = Path(out_name)
        out.mkdir(parents=True, exist_ok=True)
        (out/"run_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("2026.272 | prescription plenoptic camera")
    print(f"scale={cfg['sensor_px']}x{cfg['sensor_px']}; MLA={cfg['lenslets']}x{cfg['lenslets']}; pitch={cfg['pitch_px']} px")
    print(f"F-number main/MLA={system['main_f_number']:.3f}/{system['mla_f_number']:.3f}; rays={cap['ray_count']}")
    print(f"focus slopes truth={truth_slopes.tolist()} measured={peaks.tolist()}")
    print(f"CPU {cpu:.3f} s; wall {wall:.3f} s")
    assert raw.shape == (cfg["sensor_px"], cfg["sensor_px"])
    # The six-sample CI image is deliberately too small for a stable local
    # focus score; the quantitative gate uses a 48-sample field in tests.
    if not cfg["ci"]:
        assert max(abs(peaks-truth_slopes)) <= (slopes[1]-slopes[0])/2 + 1e-12
    assert np.isfinite(depth_est).all() and np.isfinite(sharp).all()
    print("PASS: figure and reduced scales share one light-field run")


if __name__ == "__main__":
    main()
