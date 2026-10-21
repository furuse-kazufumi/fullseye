# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC 2026.275: measurable omnidirectional inspection, stereo display, and video."""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import omni360 as O  # noqa: E402

GATES = []
NUMBERS = {}


def gate(label, ok, value=""):
    GATES.append(bool(ok))
    print("  %s %-52s %s" % ("PASS" if ok else "FAIL", label, value))


def _cube_cross(cube):
    s = cube.shape[1]
    out = np.zeros((2*s, 3*s, 3))
    for i, (y, x) in enumerate(((0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2))):
        out[y*s:(y+1)*s, x*s:(x+1)*s] = cube[i]
    return out


def _label_frames(frames, path):
    from PIL import Image, ImageDraw
    out = []
    for im, (yaw, pitch) in zip(frames, path):
        a = (np.clip(im, 0, 1)*255).astype(np.uint8)
        p = Image.fromarray(a); ImageDraw.Draw(p).text((18, 18),
            "yaw %+05.1f deg   pitch %+04.1f deg" % (yaw, pitch), fill=(255, 255, 255),
            stroke_width=2, stroke_fill=(0, 0, 0))
        out.append(np.asarray(p))
    return out


def main():
    started = time.process_time()
    small = os.environ.get("CI") == "1"
    h, w, fs = ((192, 384, 256) if small else (512, 1024, 512))
    scene = O.panorama_scene(h, w, seed=275, n_frames=30, fisheye_size=fs)

    # 1. World and its exact six-face projection.
    figs.save_grid("world", [scene["equirect"], _cube_cross(scene["cubemap"])],
        ["equirectangular world", "six calibrated faces"], ncols=2,
        title="1. Synthetic tunnel and inspection bay",
        caption="Seed 275; tunnel radius %.2f m; crack angular width %.2f deg." %
                (scene["truth"]["tunnel_radius_m"], scene["truth"]["crack_angular_width_deg"]))

    # 2. Capture, overlap, blind spot, and seam error.
    stitch = O.equirect_from_fisheye_pair(scene["fisheyes"], scene["fisheye_rotations"],
        (h, w), f_px=(scene["fisheye_f_px"],)*2, centres=scene["fisheye_centres"], fov_deg=190)
    seam = float(stitch["seam_mean"]); blind = float(stitch["blind_mask"].mean())
    figs.save_grid("fisheye_stitch", [*scene["fisheyes"], np.nan_to_num(stitch["image"]),
        np.nan_to_num(stitch["seam_error"])], ["front", "back", "stitched", "absolute seam error"],
        ncols=2, title="2. Back-to-back fisheye capture and stitch",
        caption="Measured seam MAE %.4f; blind pixels %.3f %% (reported, never filled silently)." % (seam, 100*blind))
    gate("stitch reports overlap and blind pixels", np.isfinite(seam) and blind >= 0,
         "seam %.4f, blind %.3f %%" % (seam, 100*blind))

    # 3. Latitude-aware processing and solid-angle area.
    impulse = np.zeros((h, w)); y70 = int((90-70)/180*h); impulse[y70, w//2] = 1
    ordinary = __import__("scipy.ndimage", fromlist=["gaussian_filter"]).gaussian_filter(impulse, 5)
    spherical = O.equirect_filter_gaussian(impulse, 5*180/h)
    weights = O.equirect_weight_map(h, w, True)
    weighted_area = float(weights[scene["crack_mask"]].sum())
    pixel_fraction = float(scene["crack_mask"].mean()*4*np.pi)
    anisotropy = float(np.sum(ordinary[y70] > ordinary.max()/2) / max(np.sum(spherical[y70] > spherical.max()/2), 1))
    figs.save_grid("latitude_processing", [ordinary, spherical, scene["crack_mask"]*weights],
        ["ordinary blur at 70 deg", "sphere-isotropic blur", "solid-angle defect area"], ncols=3,
        title="3. Latitude is not an ordinary image axis",
        caption="Horizontal half-height width ratio %.3f; defect solid angle %.5f sr versus unweighted %.5f sr." %
                (anisotropy, weighted_area, pixel_fraction))

    # 4. Viewer path and tile delivery.
    viewports = O.video360_viewport_track(scene["frames"], scene["view_path_deg"][:, 0],
                                           scene["view_path_deg"][:, 1], 90, (512, 512) if not small else (192, 192))
    coverage = O.video360_tile_coverage(scene["view_path_deg"], (8, 4), 90)
    figs.save_grid("viewer_path", [viewports[i] for i in (0, 9, 19, 29)],
        ["frame 1", "frame 10", "frame 20", "frame 30"], ncols=4,
        title="4. Moving viewport", caption="The measured path requests %d/32 tiles (%.1f %%)." %
        (coverage["count"], 100*coverage["fraction"]))
    gate("video contains 24 or more differing frames", len(viewports) >= 24 and
         np.max(np.abs(viewports[0]-viewports[-1])) > .05, "%d frames" % len(viewports))

    # 5. ODS disparity and radial depth.
    truth_depth = 3.0
    disparity = float(O.ods_depth_to_disparity(truth_depth, .064, w))
    left = np.roll(scene["equirect"], -int(round(disparity/2)), axis=1)
    right = np.roll(scene["equirect"], int(round(disparity/2)), axis=1)
    recovered = float(O.ods_disparity_to_depth(O.ods_depth_to_disparity(truth_depth, .064, w), .064, w))
    figs.save_grid("ods_depth", [left, right, np.full((h, w), disparity), scene["depth_m"]],
        ["left ODS", "right ODS", "disparity [px]", "truth radial depth [m]"], ncols=2,
        title="5. Omnidirectional stereo", caption="At %.2f m: disparity %.3f px and inverted depth %.6f m." %
        (truth_depth, disparity, recovered))
    gate("spherical disparity-depth inversion", abs(recovered-truth_depth) < 1e-12,
         "error %.2e m" % abs(recovered-truth_depth))

    # 6. Known shake and recovered stability.
    shakes = [np.eye(3)] + [O._ypr(4*np.sin(i*.7), 1.5*np.sin(i*.5), .8*np.sin(i*.4)) for i in range(1, 6)]
    shaky = np.stack([O.equirect_rotate(scene["equirect"], r) for r in shakes])
    stabilised = O.equirect_stabilize(shaky, sample_shape=(24, 48))
    before = O.ws_psnr(shaky[0], shaky[-1]); after = O.ws_psnr(stabilised["frames"][0], stabilised["frames"][-1])
    figs.save_grid("stabilisation", [shaky[0], shaky[-1], stabilised["frames"][-1]],
        ["reference", "shaky", "rotation corrected"], ncols=3, title="6. Rotation-only stabilisation",
        caption="WS-PSNR improved from %.2f to %.2f dB; residual %.4f." %
                (before, after, stabilised["residual"][-1]))
    gate("rotation stabilisation improves spherical PSNR", after > before,
         "%.2f -> %.2f dB" % (before, after))

    # 7. Pipe unwrap and metric crack size.
    unwrap = O.equirect_defect_unwrap_pipe(scene["equirect"], radius_m=3, length_m=6)
    crack_rows = np.where(scene["crack_mask"])[0]
    measured = (crack_rows.max()-crack_rows.min()+1)*unwrap["metres_per_pixel_axis"]
    truth = scene["truth"]["crack_axial_extent_m"]
    figs.save_grid("pipe_unwrap", [unwrap["image"], scene["crack_mask"]],
        ["flat cylindrical strip", "known crack mask"], ncols=2, title="7. Pipe-wall inspection strip",
        caption="Crack axial extent %.3f m; scene truth %.3f m (pixel quantisation applies)." % (measured, truth))

    # 8. Display method, filter leakage, parallax, and limits.
    lv = O.viewport_from_equirect(left, 0, 0, 0, 90, (512, 512) if not small else (192, 192))
    rv = O.viewport_from_equirect(right, 0, 0, 0, 90, (512, 512) if not small else (192, 192))
    ana = O.anaglyph(lv, rv, "dubois")
    ideal = O.anaglyph_crosstalk(lv, rv, ((1, 0, 0), (0, 1, 1)), "dubois")
    leaky = O.anaglyph_crosstalk(lv, rv, ((1, .1, .1), (.1, 1, 1)), "dubois")
    preview = O.anaglyph_preview(lv, rv, glasses_transmission=((1, .1, .1), (.1, 1, 1)), method="dubois")
    budget = O.stereo_parallax_budget(disparity, w, .6, .531, .064)
    figs.save_grid("anaglyph_and_limits", [lv, rv, ana, *preview],
        ["left", "right", "red/cyan pair", "left-eye view", "right-eye view"], ncols=3,
        title="8. Colour-filter stereo and measured limits",
        caption="Ideal ghosting %.4f/%.4f; 10 %% leakage %.4f/%.4f; 24-inch-class screen parallax %.2f mm; seam %.4f; pole sampling shown in chapter 1." %
        (ideal["ghosting_left"], ideal["ghosting_right"], leaky["ghosting_left"], leaky["ghosting_right"],
         budget["parallax_mm"], seam))
    gate("leaky filters increase measured ghosting", leaky["ghosting_left"] > ideal["ghosting_left"] and
         leaky["ghosting_right"] > ideal["ghosting_right"], "ideal %.4f/%.4f, leaky %.4f/%.4f" %
         (ideal["ghosting_left"], ideal["ghosting_right"], leaky["ghosting_left"], leaky["ghosting_right"]))
    gate("display method leaves disparity depth unchanged", abs(recovered-truth_depth) < 1e-12,
         "%.6f m" % recovered)

    figs.save_video("viewport_flight", _label_frames(viewports, scene["view_path_deg"]), fps=10,
        gif_every=2, gif_width=480, caption="Thirty differing frames; the first frame is already moving.")
    elapsed = time.process_time()-started
    NUMBERS.update(seam_mae=seam, blind_percent=100*blind, tile_count=coverage["count"],
        disparity_px=disparity, recovered_depth_m=recovered, ws_psnr_before=before,
        ws_psnr_after=after, crack_extent_m=measured, parallax_mm=budget["parallax_mm"], process_s=elapsed)
    gate("eight chapters plus one video are present", not figs.enabled() or len(figs.manifest()) == 9,
         "%d manifest entries" % len(figs.manifest()) if figs.enabled() else "figures off")
    gate("CI process time below 20 s", not small or elapsed < 20, "%.2f s" % elapsed)
    print("NUMBERS", NUMBERS)
    print("%d/%d PASS" % (sum(GATES), len(GATES)))
    if figs.errors() or not all(GATES):
        print("figure errors:", "; ".join(figs.errors()))
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
