# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Lens optimisation with real glass: catalogue → chromatic shift → damped least squares.

    py -3.11 examples/lens_optimize_demo.py

What it shows (every number is checked against a closed form or a pinned
measurement, so the script doubles as a self-test):

1. ``glass_catalog`` / ``sellmeier`` — real Sellmeier curves (N-BK7, N-SF2, fused
   silica …) whose d-line index and Abbe number match the data sheet; ``glass``
   remains the 2-term Cauchy *model* for when only (nd, vd) is known.
2. ``chromatic_shift`` — the singlet's F–C focal shift (~1.5 mm) versus the real-glass
   doublet's (< 0.4 mm), plus the polychromatic RMS spot on one image plane.
3. ``bend_singlet`` — Coddington's minimum-spherical-aberration shape factor in
   closed form, and ``optimize_lens`` re-discovering it from an equiconvex start
   with the EFL held at 100 mm.
4. ``optimize_lens`` finding the Descartes hyperboloid (``k = −n²``) that makes a
   plano-convex singlet stigmatic, then the same correction with polynomial
   aspheric coefficients (``A4`` converges to ``k c³/8``).
5. ``merit_function`` — the residual the optimiser minimises, evaluated on the
   real-glass doublet over three fields and three wavelengths, and
   ``chief_ray`` for the image height of one field.

EXTEND: pass your own prescription dict list to ``lens_system`` (radii,
thicknesses, catalogue names, ``k``, ``asph``), choose the variables
(``"R0"``, ``"t1"``, ``"k1"``, ``"A4_1"``…), fields and wavelengths, and read
``optimize_lens(...)["variables"]`` for the final prescription.
"""
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import lensopt  # noqa: E402
import raytrace as RT  # noqa: E402

INF = float("inf")


def main():
    # 1. real glass ----------------------------------------------------------------
    bk7 = RT.glass_catalog("N-BK7")
    print("catalogue:", ", ".join(RT.glass_catalog()))
    print("N-BK7  nd=%.5f vd=%.2f  (data sheet 1.51680 / 64.17)" % (bk7["nd"], bk7["vd"]))
    assert abs(bk7["nd"] - 1.51680) < 1e-4 and abs(bk7["vd"] - 64.17) < 0.1
    custom = RT.sellmeier(*bk7["sellmeier"], name="my-BK7")      # any maker's constants
    assert abs(custom["nd"] - bk7["nd"]) < 1e-12
    model = RT.glass(1.5168, 64.17)                                # the Cauchy model
    print("Cauchy model vs Sellmeier at F line: %.5f vs %.5f" %
          (RT.refractive_index(model, RT.WL_F), RT.refractive_index("N-BK7", RT.WL_F)))

    # 2. chromatic shift -------------------------------------------------------------
    single = RT.chromatic_shift(RT.lens_system())
    doublet = RT.example_system("catalog_doublet")
    doub = RT.chromatic_shift(doublet)
    print("axial colour F-C: singlet %.3f mm, N-BK7/N-SF2 doublet %.3f mm" %
          (single["axial_color"], doub["axial_color"]))
    print("polychromatic RMS spot: singlet %.4f mm, doublet %.4f mm" %
          (single["rms_polychromatic"], doub["rms_polychromatic"]))
    assert abs(doub["axial_color"]) < abs(single["axial_color"]) / 4

    # 3. bending a singlet -------------------------------------------------------------
    cod = lensopt.bend_singlet(100.0, 1.5168, 2.0, 5.0)
    print("Coddington shape factor q=%.4f  R1=%.2f R2=%.2f  rms=%.2e mm" %
          (cod["shape_factor"], cod["R1"], cod["R2"], cod["rms_spot"]))
    eq = lensopt.bend_singlet(100.0, 1.5168, 2.0, 5.0, shape_factor=0.0)
    r = lensopt.optimize_lens(eq["system"], variables=["R0", "R1"], efl_target=100.0)
    R1, R2 = r["variables"][0]["final"], r["variables"][1]["final"]
    q = (R2 + R1) / (R2 - R1)
    print("optimiser from equiconvex: q=%.4f rms %.2e -> %.2e mm, EFL %.4f, %d iterations" %
          (q, r["rms_initial"], r["rms_final"], r["efl_final"], r["iterations"]))
    assert abs(q - 0.73) < 0.03 and abs(r["efl_final"] - 100.0) < 1e-3

    # 4. aspheres ----------------------------------------------------------------------
    n = RT.refractive_index("N-BK7")
    pc = RT.lens_system([{"R": INF, "t": 5.0, "n": "N-BK7", "ap": 12.5},
                         {"R": -(n - 1.0) * 100.0, "t": None, "n": 1.0}], stop=0)
    rk = lensopt.optimize_lens(pc, variables=["k1"], efl_target=100.0)
    print("conic: k1 -> %.4f (Descartes -n^2 = %.4f), rms %.2e -> %.1e mm" %
          (rk["variables"][0]["final"], -n * n, rk["rms_initial"], rk["rms_final"]))
    assert abs(rk["variables"][0]["final"] + n * n) < 1e-3
    ra = lensopt.optimize_lens(pc, variables=["A4_1", "A6_1", "A8_1"], efl_target=100.0, iterations=60)
    a4 = ra["variables"][0]["final"]
    c = 1.0 / (-(n - 1.0) * 100.0)
    print("polynomial: A4=%.4e (k c^3/8 = %.4e), A6=%.2e, A8=%.2e, rms %.1e mm" %
          (a4, -n * n * c ** 3 / 8, ra["variables"][1]["final"], ra["variables"][2]["final"], ra["rms_final"]))
    assert abs(a4 - (-n * n * c ** 3 / 8)) / abs(a4) < 0.01
    stig = RT.example_system("asphere")
    print("example_system('asphere') rms spot %.1e mm (stigmatic)" % RT.spot_stats(stig)["rms_radius"])

    # 5. merit over fields / wavelengths ------------------------------------------------
    doublet["field"] = 3.0
    m = lensopt.merit_function(doublet, wavelengths=[RT.WL_F, RT.WL_D, RT.WL_C])
    print("doublet merit %.4f, rms by field %s, EFL %.3f" %
          (m["merit"], {k: round(v, 4) for k, v in m["rms_by_field"].items()}, m["efl"]))
    ro = lensopt.optimize_lens(doublet, variables=["R0", "R1", "R2"], wavelengths=[RT.WL_F, RT.WL_D, RT.WL_C])
    print("after DLS on three radii: rms %.4f -> %.4f mm (EFL held %.3f -> %.3f)" %
          (ro["rms_initial"], ro["rms_final"], ro["efl_initial"], ro["efl_final"]))
    assert ro["rms_final"] < ro["rms_initial"]
    cr = RT.chief_ray(ro["system"], field=3.0)
    print("chief ray at 3 deg lands at y=%.4f mm (f tan 3deg = %.4f)" %
          (cr["image_y"], ro["efl_final"] * math.tan(math.radians(3.0))))
    assert cr["valid"] and abs(cr["image_y"] - ro["efl_final"] * math.tan(math.radians(3.0))) < 0.05
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
