# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Closed-loop camera calibration through a designed lens.

    py -3.11 examples/lens_calibration_loop_demo.py

``lensimage.calibration_views`` projects a planar chessboard-like target through
the prescription (pinhole of the EFL + the lens's traced radial distortion) at
six poses and returns the ``(row, col)`` corner lists ``calib.camera_calibration``
consumes. Comparing the recovered intrinsics with ``K_true`` closes the loop:

* paraboloid mirror (no distortion): fx = fy = EFL/pitch to 1e-6, reprojection 0;
* plano-convex singlet on a wide sensor (barrel −0.6 % at the corner): the focal
  length is biased and the reprojection RMS is non-zero — what a real chart shows;
* the real-glass doublet with 0.3 px corner noise: the bias a detector's noise adds.

EXTEND: pass your prescription, sensor and target; feed the returned points to
``calib.camera_calibration`` (or to your own solver); compare against ``K_true``
and the ``distortion`` polynomial to decide whether a radial model is needed.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import calib  # noqa: E402
import lensimage  # noqa: E402
import raytrace as RT  # noqa: E402


def report(name, v):
    k = calib.camera_calibration(v["object_points"], v["image_points"])
    fx_t = v["K_true"]["fx"]
    print("%-28s EFL %.3f mm  fx_true %.2f px  recovered fx %.2f fy %.2f (bias %.2e)  cx %.2f cy %.2f  "
          "reproj max %.2e px  max distortion %.4f %%" %
          (name, v["efl"], fx_t, k["fx"], k["fy"], abs(k["fx"] - fx_t) / fx_t, k["cx"], k["cy"],
           max(k["reproj_rms"]), v["distortion"]["max_distortion_pct"]))
    return k


def main():
    para = lensimage.calibration_views(RT.example_system("paraboloid"), image_size=(800, 1000), pixel_pitch_um=5.0)
    k0 = report("paraboloid (no distortion)", para)
    assert abs(k0["fx"] - para["K_true"]["fx"]) / para["K_true"]["fx"] < 1e-6
    singlet = RT.lens_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5},
                              {"R": float("inf"), "t": None, "n": 1.0}], stop=0)
    sv = lensimage.calibration_views(singlet, image_size=(2000, 3000), pixel_pitch_um=10.0)
    k1 = report("singlet, wide sensor", sv)
    assert max(k1["reproj_rms"]) > max(k0["reproj_rms"])
    dv = lensimage.calibration_views(RT.example_system("catalog_doublet"), noise_px=0.3, seed=1)
    report("catalog doublet + 0.3 px noise", dv)
    print("poses:", [(p["rx_deg"], p["ry_deg"], p["rz_deg"], round(p["visible_fraction"], 2)) for p in dv["poses"]])
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
