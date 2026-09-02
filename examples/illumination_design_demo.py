# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Illumination design for an inspection station: lights → irradiance → defect contrast.

    py -3.11 examples/illumination_design_demo.py

1. ``light_source`` builds ring / dome / bar / coaxial / backlight emitter sets;
   ``irradiance_map`` puts the inverse-square × cos^m × cos law on the part plane
   (checked against ``I0 cos⁴θ / h²`` for a Lambertian point source) and
   ``illumination_uniformity`` reports min/max, CV and edge fall-off — the dome
   is uniform, the low ring is not.
2. ``defect_contrast`` — a 10° facet (a scratch flank) on a glossy surface under a
   low ring (dark field) versus a high ring (bright field); pigment contrast and
   how coaxial glare on a mirror-like surface dilutes it.
3. ``lighting_sweep`` — contrast versus ring elevation; on a mirror-like surface the
   peak sits at ``90° − 2 × slope`` (the facet mirrors the light into the camera).
4. ``illumination_design`` — the ranked candidate table for (surface, defect),
   with the rule of thumb it agrees or disagrees with.

EXTEND: describe your surface as ``{"albedo", "roughness", "f0"}`` (or a preset),
your defect as a facet slope, put the camera where it is, and read the
``ranking`` — then feed the winning ``light_source`` to ``irradiance_map`` with a
``height`` relief of the real part to see the image-plane illumination.
"""
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import illumdesign as ID  # noqa: E402


def main():
    # 1. lights and irradiance --------------------------------------------------------
    pt = ID.light_source("point", height_mm=100.0, intensity=1.0)
    irr = ID.irradiance_map(pt, size_mm=(80, 80), shape=(41, 41))
    edge = (0.5 / 41 - 0.5) * 80.0                                   # corner pixel centre (x = y = -39.02)
    cos_corner = 100.0 / math.sqrt(2 * edge ** 2 + 100.0 ** 2)
    print("point source: centre %.3e, corner %.3e (cos^4 law predicts %.3e)" %
          (irr[20, 20], irr[0, 0], cos_corner ** 4 / 1e4))
    assert abs(irr[0, 0] - cos_corner ** 4 / 1e4) < 1e-12
    dome = ID.light_source("dome", radius_mm=150.0, n=400)
    low = ID.light_source("ring", radius_mm=60.0, height_mm=15.0, n=24)
    high = ID.light_source("ring", radius_mm=60.0, height_mm=160.0, n=24)
    for name, lt in (("dome", dome), ("ring 14deg", low), ("ring 69deg", high)):
        u = ID.illumination_uniformity(ID.irradiance_map(lt, size_mm=(50, 50), shape=(48, 48)))
        print("%-11s uniformity %.3f  cv %.3f  edge/centre %.3f" % (name, u["uniformity"], u["cv"], u["edge_falloff"]))
    assert ID.illumination_uniformity(ID.irradiance_map(dome, size_mm=(50, 50), shape=(48, 48)))["uniformity"] > 0.9

    # a bump on the part under a one-sided bar light: the facing flank brightens
    bar = ID.light_source("bar", radius_mm=100.0, height_mm=20.0, n=9, length_mm=60.0)
    ys = (0.5 - (np.arange(41) + 0.5) / 41) * 20.0
    xs = ((np.arange(41) + 0.5) / 41 - 0.5) * 20.0
    X, Y = np.meshgrid(xs, ys)
    bump = 0.5 * np.exp(-(X * X + Y * Y) / 8.0)
    flat = ID.irradiance_map(bar, size_mm=(20, 20), shape=(41, 41))
    relief = ID.irradiance_map(bar, size_mm=(20, 20), shape=(41, 41), height=bump)
    print("bump under a bar light: facing flank x%.2f, far flank x%.2f of the flat irradiance" %
          (relief[16, 20] / flat[16, 20], relief[24, 20] / flat[24, 20]))

    # 2. defect contrast -----------------------------------------------------------------
    for name, lt in (("dark field (ring 14deg)", low), ("bright field (ring 69deg)", high)):
        dc = ID.defect_contrast(lt, surface="glossy", slopes_deg=[2.0, 5.0, 10.0, 20.0])
        row = {r["slope_deg"]: round(r["max_abs"], 3) for r in dc["per_slope"]}
        print("%-26s regime=%-12s facet contrast by slope %s  pigment %.3f" %
              (name, dc["regime"], row, dc["pigment"]))
    coax = ID.light_source("coaxial", radius_mm=60.0, height_mm=150.0, n=16)
    matte = ID.defect_contrast(coax, surface="matte", slopes_deg=[5.0])
    mirror = ID.defect_contrast(coax, surface="mirror", slopes_deg=[5.0])
    print("coaxial light, pigment at half albedo: matte %.3f (1/3 without glare) vs mirror-like %.3f" %
          (matte["pigment"], mirror["pigment"]))
    assert mirror["pigment"] < matte["pigment"]

    # 3. sweep ----------------------------------------------------------------------------
    for slope in (10.0, 20.0):
        sw = ID.lighting_sweep(surface="mirror", slope_deg=slope, radius_mm=60.0, camera_height_mm=1000.0,
                               elevations_deg=[float(v) for v in range(30, 90, 2)])
        best = sw[int(np.argmax(sw[:, 1])), 0]
        print("mirror-like surface, %2.0f deg facet: best ring elevation %.0f deg (closed form 90-2s = %.0f)" %
              (slope, best, 90.0 - 2.0 * slope))
        assert abs(best - (90.0 - 2.0 * slope)) <= 2.0

    # 4. design table ----------------------------------------------------------------------
    # note: a *smooth* 10 deg facet does not light up in dark field (it mirrors the low light
    # away from the camera); the "dark field shows scratches" rule is about their rough flanks,
    # which is the "scatter" class — and for that class a large coaxial source can score higher
    # (rough patch dark on a uniform glare). The table says so with numbers instead of folklore.
    for surface, defect in (("glossy", "scatter"), ("glossy", "topographic"), ("mirror", "topographic"),
                            ("matte", "pigment"), ("matte", "edge")):
        d = ID.illumination_design(surface=surface, defect=defect, slope_deg=10.0)
        top = d["ranking"][0]
        print("%-7s %-11s -> %-24s score %.3f  rule: %-24s %s" %
              (surface, defect, d["recommended"], top["score"], d["rule_of_thumb"],
               "agree" if d["agrees_with_rule"] else "DISAGREE (read the table)"))
    assert ID.illumination_design(surface="glossy", defect="scatter")["recommended"] in ("ring_dark_field_20deg", "coaxial")
    e = ID.illumination_design(surface="matte", defect="edge")
    assert e["recommended"] == "backlight"
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
