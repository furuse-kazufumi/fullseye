# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""raytrace._intersect_conic picks the root on the vertex sheet (2026-10-18).

Found while gating the .zmx reader against optiland: in a telephoto lens a surface of R = -14.5 mm
26 mm behind the stop made **every** ray "vignetted" -- the ray starts inside the sphere's z range,
and the old rule "smallest |t|" picked the back of the sphere (t < 0). The physical hit is on the
sheet that contains the vertex, (1+k) c z <= 1. Truth: the closed-form sag of the hit point.
"""
import math

import numpy as np
import pytest

import raytrace as RT


def _sag(c, k, r):
    return c * r * r / (1.0 + math.sqrt(1.0 - (1.0 + k) * c * c * r * r))


@pytest.mark.parametrize("R,k,gap", [(-14.5, 0.0, 26.0), (-14.5, 0.0, 10.0), (-20.0, -0.5, 30.0), (-8.0, 0.4, 12.0),
                                     (14.5, 0.0, 26.0), (-30.0, -2.0, 50.0)])
@pytest.mark.parametrize("y", [0.5, 3.0, 6.0])
def test_hit_lies_on_the_vertex_sheet(R, k, gap, y):
    s = RT.lens_system([{"R": math.inf, "t": gap, "n": 1.0, "ap": 10.0},
                        {"R": R, "t": 5.0, "n": 1.5, "k": k}, {"R": math.inf, "t": 30.0, "n": 1.0}], stop=0)
    r = RT.trace_rays(s, np.array([[0.0, y, -1.0]]), np.array([[0.0, 0.0, 1.0]]))
    assert r["valid"][0]
    z_hit = r["points"][0, 2, 2]
    assert z_hit == pytest.approx(gap + _sag(1.0 / R, k, y), abs=1e-12)


def test_oblique_ray_starting_inside_the_sphere_range():
    s = RT.lens_system([{"R": math.inf, "t": 26.0, "n": 1.0, "ap": 10.0},
                        {"R": -14.5, "t": 5.0, "n": 1.5}, {"R": math.inf, "t": 30.0, "n": 1.0}], stop=0)
    d = np.array([0.0, math.sin(0.05), math.cos(0.05)])
    r = RT.trace_rays(s, np.array([[0.0, 1.0, 0.0]]), d[None])
    P = r["points"][0, 2]
    c = -1.0 / 14.5
    assert P[2] - 26.0 == pytest.approx(_sag(c, 0.0, math.hypot(P[0], P[1])), abs=1e-12)
    assert P[2] > 20.0                                        # not the back of the sphere near z = 6.9
