# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""PoC 2026.272: a prescription, MLA and sensor make one refocusable exposure.

The full run traces a 480 x 480 sensor behind a 32 x 32 MLA (15 pixels per
microlens).  ``CI=1`` selects the 96 x 96, 6 x 6 reduced run.  Every figure and
video frame is decoded from the captured raw frame. Explanatory diagrams are
labelled as conceptual rather than counted as validation.

Truth does not come from the slope-to-distance formula it checks.  Rays are
traced *forward* from an object point through the prescription
(``raytrace.trace_rays``); where each crosses the exit pupil fixes the view that
sees it and where it crosses the MLA fixes its lenslet, so the parallax per view
is measured, not derived.  Before 2026-11-04 the PoC's only metric-depth gate
round-tripped the conversion through its own inverse, and it passed while the
conversion was 1/angular_step**2 (~3000x) wrong: the planes' "true slopes" were
printed as +712 / 0 / -448 lenslets per view against a measured 0 / 0 / 0.
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
from PIL import Image, ImageDraw, ImageFont
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
    # The label is sized to the box (PIL's built-in default is an 11 px bitmap
    # font, invisible on a 256 px coupon -- 2026-11-04).
    font = ImageFont.load_default(size=max(8, int(round(.13*n))))
    draw.text((.17*n, .17*n), "QC 17", fill=20, font=font, stroke_width=max(0, n//180))
    draw.line((.10*n, .78*n, .90*n, .78*n), fill=225, width=max(1, n//90))
    for k in range(17):
        xx = (.10+.05*k)*n
        h = (.10 if k % 2 == 0 else .055)*n     # already in pixels
        draw.line((xx, .78*n, xx, .78*n-h), fill=230, width=max(1, n//140))
    im = np.asarray(pil, dtype=float)/255
    # A real defect crosses both smooth metal and the printed label.
    scratch = np.abs(y-(.70*n-.43*x+7*np.sin(x/n*9))) < max(1.0, n/220)
    im[scratch] = .01
    im[(x-.79*n)**2+(y-.23*n)**2 < (n*.018)**2] = .98
    return np.clip(im, 0, 1)


def _image_plane_z(lens):
    """Global z of the last vertex, the MLA (nominal image) plane and the exit pupil."""
    para = RT.paraxial_trace(lens)
    z_last = float(sum(s["t"] for s in lens["surfaces"][:-1]))
    image_mm = lens["image_mm"] if lens["image_mm"] is not None else float(para["image_mm"])
    return z_last, z_last+float(image_mm), z_last+float(para["xp_position"]), para


def chief_ray_scale(lens, depth_m):
    """MLA-plane position per object-plane position, from one forward-traced chief ray."""
    _, z_img, _, para = _image_plane_z(lens)
    x_obj = 1e-3*depth_m*1000
    o = np.array([[x_obj, 0.0, -1000.0*depth_m]])
    d = np.array([[0.0, 0.0, float(para["ep_position"])]])-o
    d /= np.linalg.norm(d)
    tr = RT.trace_rays(lens, o, d)
    q = tr["points"][0, -2]; v = tr["dirs"][0, -1]
    return float((q[0]+(z_img-q[2])/v[2]*v[0])/x_obj)


def scene_layout(lens, half_width_mm):
    """Centre and size of each plane so the sensor sees them in its left, middle and right thirds."""
    third = 2*half_width_mm/3
    layout = []
    for z, centre_s in zip(DEPTHS_M, (-third, 0.0, third)):
        k = chief_ray_scale(lens, z)
        layout.append({"depth_m": float(z), "centre_mm": centre_s/k,
                       "size_mm": (1.3*third/abs(k), 2.2*half_width_mm/abs(k)), "scale": k})
    return layout


def inspection_scene(lens=None, half_width_mm=2.4):
    tex = inspection_texture()
    lens = prescription() if lens is None else lens
    objects = []
    for item in scene_layout(lens, half_width_mm):
        objects.append({"type": "plane", "point_mm": (item["centre_mm"], 0, -1000*item["depth_m"]),
                        "size_mm": item["size_mm"], "albedo": tex})
    return LR.lens_scene(objects,
        [{"type": "directional", "to_light": (0, 0, 1), "irradiance_W_m2_nm": 1.0}],
        sources=[{"position_mm": (38, -25, -1000), "intensity_W_sr_nm": 1.0}])


def truth_depth_map(system, calibration, lf_shape, layout):
    """Nearest plane on each decoded sample's chief ray (NaN where it sees background)."""
    H, W = system["sensor_size"]; pp = system["pixel_pitch_mm"]
    B = np.asarray(calibration["basis_px"], float); org = np.asarray(calibration["origin_px"], float)
    inv = np.linalg.inv(B)
    corners = np.array([[0, 0], [W-1, 0], [0, H-1], [W-1, H-1]])
    lo = np.ceil(((corners-org)@inv).min(0)).astype(int)
    jj, ii = np.indices(lf_shape[2:])
    base = org+(ii[..., None]+lo[0])*B[0]+(jj[..., None]+lo[1])*B[1]
    xs = (base[..., 0]-(W-1)/2)*pp; ys = (base[..., 1]-(H-1)/2)*pp
    depth = np.full(lf_shape[2:], np.nan)
    for item in sorted(layout, key=lambda d: -d["depth_m"]):      # nearest plane last wins
        k = item["scale"]; w, h = item["size_mm"]
        inside = (np.abs(xs/k-item["centre_mm"]) <= w/2) & (np.abs(ys/k) <= h/2)
        depth[inside] = item["depth_m"]
    return depth


def depth_to_slope(system, depth_m, views):
    """Paraxial slope (lenslets per decoded view) of an object at *depth_m*.

    The forward form of ``plenoptic_refocus_depth``: Newton's equation gives the
    image shift ``delta`` behind the MLA; a view step moves the exit-pupil
    coordinate by ``dX = (pitch/views)*xp_radius/(microimage_diameter/2)``; the
    MLA crossing then moves by ``dX*delta/(D+delta)`` with ``D`` the exit-pupil
    distance.  (Before 2026-11-04 this was ``delta/(angular_step*pitch)``.)
    """
    lens = system["main_lens"]
    _, z_img, z_xp, para = _image_plane_z(lens)
    f = float(para["efl"]); bfl = float(para["bfl"]); ffl = float(para["ffl"])
    image0 = z_img-_image_plane_z(lens)[0]
    x = -np.asarray(depth_m, float)*1000-ffl
    delta = bfl-f*f/x-image0
    p = system["mla"]["pitch_mm"]
    dX = (p/views)*float(para["xp_radius"])/(system["microimage_diameter_mm"]/2)
    return (dX/p)*delta/((z_img-z_xp)+delta)


def traced_slope(system, depth_m, views, pupil_extent=1.0):
    """Measured truth: lenslets of MLA parallax per decoded view from forward-traced rays.

    Rays from an on-axis point at *depth_m* fill the entrance pupil and run
    through the prescription.  The exit-pupil crossing of each image-space ray is
    the pupil coordinate a decoded view selects; its MLA crossing is the
    lenslet.  The returned slope is the line fit over the pupil positions the
    *views* views sample, so it includes the lens's spherical aberration;
    ``pupil_extent=1e-3`` shrinks the fit to the paraxial zone.
    """
    lens = system["main_lens"]
    _, z_img, z_xp, para = _image_plane_z(lens)
    obj = np.array([0.0, 0.0, -1000.0*depth_m])
    xe = np.linspace(-.97, .97, 389)*float(para["ep_radius"])
    d = np.column_stack([xe, np.zeros_like(xe), np.full_like(xe, float(para["ep_position"]))])-obj
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    tr = RT.trace_rays(lens, np.repeat(obj[None], len(xe), 0), d)
    q = tr["points"][tr["valid"], -2]; v = tr["dirs"][tr["valid"], -1]
    uv = (q[:, 0]+(z_xp-q[:, 2])/v[:, 2]*v[:, 0])/float(para["xp_radius"])
    x_mla = q[:, 0]+(z_img-q[:, 2])/v[:, 2]*v[:, 0]
    order = np.argsort(uv)
    p = system["mla"]["pitch_mm"]
    k = (np.arange(views)-(views-1)/2)*pupil_extent
    uv_k = (k*p/views)/(system["microimage_diameter_mm"]/2)
    if not (uv[order][0] < uv_k[0] and uv_k[-1] < uv[order][-1]):
        raise AssertionError("traced pupil does not cover the decoded views")
    return float(np.polyfit(k, np.interp(uv_k, uv[order], x_mla[order])/p, 1)[0])


def old_depth_to_slope(system, depth_m):
    """The pre-2026-11-04 relation, kept only as the broken probe of the truth gate."""
    z = np.asarray(depth_m, float)*1000
    f = abs(float(RT.paraxial_trace(system["main_lens"])["efl"]))
    z0 = float(system["main_lens"]["object_mm"]); image0 = f*z0/(z0-f)
    step = (system["pixel_pitch_mm"]/system["mla_to_sensor_mm"])*system["mla"]["pitch_mm"]
    return (1/(1/f-1/z)-image0)/step


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
    d.text((250, 328), f"conceptual rays; F/{system['main_f_number']:.2f}; MLA pitch 0.15 mm", fill="black")
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


def make_figures(system, cap, raw, lf, stack, slopes, focus, depth_truth, depth_est, sharp, info):
    """Seven explanatory chapters, all derived from this figure-mode run."""
    figs.save("camera_section", camera_section_image(system),
              "Conceptual diagram (not a validation gate): main lens, MLA, sensor and five illustrative rays.")
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
    tl, tm, tr = info["truth_slopes"]
    figs.save_grid("decode_subaperture_epi", views+[epi],  # gray-ok: EPI の傾斜軌跡を示す輝度像であり深度場ではない
                   ["left pupil", "centre pupil", "right pupil", "EPI: slanted point tracks"],
                   ncols=2, gray=True,
                   caption=(f"{lf.shape[0]} x {lf.shape[1]} decoded views; ray-traced parallax "
                            f"{tl:+.3f} / {tm:+.3f} / {tr:+.3f} lenslets per view at 0.6 / 1.0 / 1.8 m."))
    peaks = info["focus_peaks"]
    pick = [int(np.argmin(abs(slopes-s))) for s in peaks]
    score_plot = np.repeat((focus / np.maximum(focus.max(0), 1e-12)).T, 8, axis=0)
    figs.save_grid("refocus_sweep", [stack[i] for i in pick]+[score_plot],
                   [f"{z:.1f} m: slope {slopes[i]:+.3f}" for z, i in zip(DEPTHS_M, pick)]
                   + ["focus measure vs slope"], ncols=2, gray=True,
                   caption=(f"Measured focus peaks {peaks[0]:+.3f} / {peaks[1]:+.3f} / {peaks[2]:+.3f} "
                            f"vs ray-traced {tl:+.3f} / {tm:+.3f} / {tr:+.3f} lenslets per view."))
    seen = np.isfinite(depth_truth)
    err_mm = np.where(seen, (depth_est-np.where(seen, depth_truth, 0))*1000, 0.0)
    depth_truth = np.where(seen, depth_truth, np.nan)
    depth_lo, depth_hi = 500., 2000.
    err_lim = max(1., float(np.percentile(np.abs(err_mm[seen]), 95)))
    colour_bar = np.repeat(np.linspace(depth_hi, depth_lo, 128)[:, None], 20, axis=1)
    panels = [pseudocolour(ndimage.zoom(np.nan_to_num(depth_truth, nan=0.0)*1000, 4, order=0),
                           depth_lo, depth_hi, "turbo"),
              pseudocolour(ndimage.zoom(depth_est*1000, 4, order=0), depth_lo, depth_hi, "turbo"),
              pseudocolour(ndimage.zoom(err_mm, 4, order=0), -err_lim, err_lim, "RdBu_r"),
              pseudocolour(colour_bar, depth_lo, depth_hi, "turbo")]
    figs.save_grid("depth_map", panels,
                   ["truth depth (mm)", "estimated depth (mm)", "signed error (mm)", "colour bar (mm)"], ncols=4,
                   signed=False, gray=False,
                   caption=("Ray-traced truth vs focus-sweep estimate; median error "
                            + " / ".join(f"{e*1000:+.0f} mm" for e in info["depth_median_error_m"])
                            + " at 0.6 / 1.0 / 1.8 m (paraxial relation; spherical aberration)."))
    p10, p20 = textbook_raw_pair(inspection_texture(256))
    figs.save_grid("plenoptic_1_vs_2", [p10, p20],
                   ["1.0 raw: pupil images", "2.0 raw: inverted scene fragments"],
                   ncols=2, gray=True,
                   caption="Same MLA: plenoptic 1.0 images the pupil; focused 2.0 images scene fragments.")
    detuned = ndimage.gaussian_filter(stack[pick[1]], 2.0)
    # One lenslet per block; the decoder drops the partial lenslet at the frame
    # edge, so crop the block means to the decoded spatial shape.
    cell = raw.shape[0]//system["mla"]["n_lenslets"][0]
    nb = raw.shape[0]//cell
    small_raw = raw[:nb*cell, :nb*cell].reshape(nb, cell, nb, cell).mean((1, 3))
    small_raw = small_raw[:lf.shape[2], :lf.shape[3]]
    mismatch = np.clip(small_raw + .35*np.roll(small_raw, 2, axis=1), 0, 1)
    figs.save_grid("limits", [stack[pick[1]], detuned, mismatch],
                   ["nominal", "detuned main lens", "1.5x F-number overlap"], ncols=3, gray=True,
                   caption="Limits, illustrative (blur and shifted-copy models, not traced): "
                           "nominal, detuned main lens, 1.50x F-number overlap.")


def make_video(lf):
    """Write a 24-frame, 480-pixel refocus sweep and enforce content gates."""
    video_slopes = np.linspace(-.45, .45, 24)
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
                        f_number=n_main, shape="square")
    system = P.plenoptic_system(lens, mla,
        {"size": (cfg["sensor_px"], cfg["sensor_px"]), "pixel_pitch_um": pixel_um})
    half_width = cfg["sensor_px"]*pixel_um*1e-3/2
    layout = scene_layout(lens, half_width)
    cap = P.plenoptic_capture(system, inspection_scene(lens, half_width), pupil_samples=1)
    # ``white_image`` is the matching optical flat returned by this capture.
    # A finite white object is not a flat field: its projected boundaries and
    # overlaps bias the detected microimage peaks at full resolution.
    calibration=P.plenoptic_mla_calibrate(cap["white_image"],cfg["pitch_px"],max_residual_px=.3)
    raw = cap["raw"]
    raw = np.clip(raw/(np.percentile(raw[raw > 0], 99.5)+1e-15), 0, 1)
    lf=P.plenoptic_decode(raw,calibration,angular=(cfg["angular"],cfg["angular"]))
    views = lf.shape[1]
    # Truth from forward-traced rays (full pupil, with aberration) and its
    # paraxial limit; neither reads the slope-to-distance relation.
    truth_slopes = np.array([traced_slope(system, z, views) for z in DEPTHS_M])
    paraxial_truth = np.array([traced_slope(system, z, views, 1e-3) for z in DEPTHS_M])
    paraxial_formula = depth_to_slope(system, DEPTHS_M, views)
    depth_truth = truth_depth_map(system, calibration, lf.shape, layout)
    masks = [ndimage.binary_erosion(depth_truth == z, iterations=2) for z in DEPTHS_M]
    slopes = np.round(np.linspace(-.4, .4, 33), 12)
    stack = np.stack([LF.lf_refocus(lf, s, interp="cubic") for s in slopes])
    focus = np.array([[np.var(ndimage.laplace(im)[m]) if m.any() else 0.0 for m in masks]
                      for im in stack])
    peaks = slopes[np.argmax(focus, axis=0)]
    # interp="cubic": the linear default pulls fractional slopes toward 0
    # (lightfield.lf_depth_from_focus docstring, measured 2026-11-04).
    slope_map, sharp = LF.lf_depth_from_focus(lf, slopes, window=5, interp="cubic")
    depth_est=P.plenoptic_refocus_depth(lf,system,slope_map)["depth_m"]
    region_slope = [float(np.median(slope_map[m])) if m.any() else float("nan") for m in masks]
    depth_median_error = [float(np.median(depth_est[m]))-z if m.any() else float("nan")
                          for m, z in zip(masks, DEPTHS_M)]
    holdout=np.array([.75,1.3])
    holdout_slopes=np.array([traced_slope(system, z, views, 1e-3) for z in holdout])
    holdout_back=P.plenoptic_refocus_depth(lf,system,holdout_slopes)["depth_m"]
    cpu = time.process_time()-cpu0; wall = time.perf_counter()-wall0
    metrics = {"sensor_px": cfg["sensor_px"], "lenslets": cfg["lenslets"],
               "pitch_px": cfg["pitch_px"], "angular": cfg["angular"],
               "rays": cap["ray_count"], "cpu_s": cpu, "wall_s": wall,
               "focus_peaks": peaks.tolist(), "truth_slopes": truth_slopes.tolist(),
               "paraxial_truth_slopes": paraxial_truth.tolist(),
               "paraxial_formula_slopes": paraxial_formula.tolist(),
               "pre_fix_formula_slopes": old_depth_to_slope(system, DEPTHS_M).tolist(),
               "region_median_slopes": region_slope, "region_pixels": [int(m.sum()) for m in masks],
               "depth_median_error_m": depth_median_error,
               "source_id":"captured_raw->flat_field_calibration->plenoptic_decode",
               "holdout_depth_m":holdout.tolist(),"holdout_abs_error_m":np.abs(holdout_back-holdout).tolist()}
    if figs.target_dir() is not None and not cfg["ci"]:
        make_figures(system, cap, raw, lf, stack, slopes, focus, depth_truth, depth_est, sharp, metrics)
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
    print("ray-traced slope (full pupil) = " + " / ".join(f"{s:+.4f}" for s in truth_slopes)
          + " lenslets/view at 0.6 / 1.0 / 1.8 m")
    print("ray-traced slope (paraxial)   = " + " / ".join(f"{s:+.4f}" for s in paraxial_truth)
          + "; paraxial formula = " + " / ".join(f"{s:+.4f}" for s in paraxial_formula))
    print("pre-fix formula               = " + " / ".join(f"{s:+.1f}" for s in old_depth_to_slope(system, DEPTHS_M)))
    print("measured focus peak           = " + " / ".join(f"{s:+.4f}" for s in peaks)
          + "; region median slope = " + " / ".join(f"{s:+.4f}" for s in region_slope))
    print("region median depth error     = " + " / ".join(f"{e*1000:+.1f} mm" for e in depth_median_error)
          + "; holdout |error| = " + " / ".join(f"{e*1000:.3f} mm" for e in np.abs(holdout_back-holdout)))
    print(f"CPU {cpu:.3f} s; wall {wall:.3f} s")
    assert raw.shape == (cfg["sensor_px"], cfg["sensor_px"])
    assert np.isfinite(depth_est).all() and np.isfinite(sharp).all()
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    # Gate 1 (every run): the paraxial relation equals the paraxial limit of the
    # forward-traced rays, and metric depth inverts traced (not formula) slopes.
    assert np.max(np.abs(paraxial_formula-paraxial_truth)) <= 1e-3*np.max(np.abs(paraxial_truth))
    assert np.max(np.abs(holdout_back-holdout)/holdout) < 1e-3
    # Broken probe: the pre-fix relation is two orders of magnitude off the rays.
    assert np.max(np.abs(old_depth_to_slope(system, DEPTHS_M))) > 100*np.max(np.abs(truth_slopes))
    # Gate 2 (full run; six lenslets are too few for a regional focus score):
    # the decoded field's own parallax, measured by its focus peak and by the
    # regional median of the depth-from-focus map, matches the traced full-pupil
    # truth within 0.03 lenslets/view (about 18 % of the 0.6 m and 1.8 m
    # parallax -- a unit or baseline error of that size turns it red), the three
    # planes are told apart in order, and metric depth stays within 20 %.  The
    # remaining offset is honest: the sharpness peak of an aberrated ray fan is
    # not exactly its least-squares line, and the depth relation is paraxial.
    if not cfg["ci"]:
        assert all(m.sum() >= 30 for m in masks), [int(m.sum()) for m in masks]
        assert np.all(np.abs(peaks-truth_slopes) <= .03), (peaks, truth_slopes)
        assert np.all(np.abs(np.array(region_slope)-truth_slopes) <= .03), (region_slope, truth_slopes)
        assert region_slope[0] > region_slope[1] > region_slope[2]
        assert np.all(np.abs(np.array(depth_median_error)/DEPTHS_M) < .2), depth_median_error
    print("PASS: captured raw causally feeds decoded EPI, refocus and continuous depth")


if __name__ == "__main__":
    main()
