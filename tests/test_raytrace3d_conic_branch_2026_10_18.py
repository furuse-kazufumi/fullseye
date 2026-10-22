# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""raytrace3d also takes the root on the vertex sheet (2026-10-18 integration).

``raytrace3d._trace`` intersects through ``raytrace._intersect_surface`` -> ``_intersect_conic``, so the
fix for "smallest |t| picks the back of a sphere" (found with the .zmx reader) reaches the non-coaxial
tracer without a second copy of the code. This gate keeps it that way: a telephoto layout (R = -14.5 mm,
26 mm behind the stop) must not vignette every ray, the hit must sit on the closed-form sag, and with the
OLD root choice swapped in the same layout must fail (proof the gate can fail).
"""
import math

import numpy as np
import pytest

import raytrace as RT
import raytrace3d as R3


def _sag(c, k, r):
    return c * r * r / (1.0 + math.sqrt(1.0 - (1.0 + k) * c * c * r * r))


def _old_intersect_conic(P, D, c, k):
    """The pre-2026-10-18 rule: take the root with the smaller |t|."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    L, M, N = D[:, 0], D[:, 1], D[:, 2]
    kk = 1.0 + k
    A = c * (L * L + M * M + kk * N * N)
    B = 2.0 * (c * (x * L + y * M + kk * z * N) - N)
    C = c * (x * x + y * y + kk * z * z) - 2.0 * z
    disc = B * B - 4.0 * A * C
    ok = disc >= 0
    sq = np.sqrt(np.where(ok, disc, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (-B - sq) / (2.0 * A)
        t2 = (-B + sq) / (2.0 * A)
    t = np.where(np.abs(t1) <= np.abs(t2), t1, t2)
    return np.where(ok, t, np.nan)


def _telephoto(extra=None):
    surf = {"R": -14.5, "t": 5.0, "n": 1.5}
    surf.update(extra or {})
    return R3.noncoaxial_system([{"R": math.inf, "t": 26.0, "n": 1.0, "ap": 10.0}, surf,
                                 {"R": math.inf, "t": 30.0, "n": 1.0}], stop=0, field=(0.0, 0.0))


@pytest.mark.parametrize("extra", [None, {"tilt": (0.4, 0.0)}, {"decenter": (0.0, 0.3)}])
def test_telephoto_layout_is_not_vignetted(extra):
    r = R3.noncoaxial_trace(_telephoto(extra), rings=3)
    f = r["fields"][0]
    assert f["n_vignetted"] == 0 and f["n_rays"] > 0


def test_hit_lies_on_the_vertex_sheet():
    r = R3.noncoaxial_trace(_telephoto(), rings=3)["fields"][0]
    pts = r["points"]                                          # (N, n+2, 3): start, surfaces..., image
    z_hit = pts[:, 2, 2]
    rr = np.hypot(pts[:, 2, 0], pts[:, 2, 1])
    want = 26.0 + np.array([_sag(-1.0 / 14.5, 0.0, x) for x in rr])
    assert np.allclose(z_hit, want, atol=1e-9)
    assert np.all(z_hit > 20.0)                                # not the back of the sphere (near z = 6.9)


def test_old_root_choice_fails_this_gate(monkeypatch):
    monkeypatch.setattr(RT, "_intersect_conic", _old_intersect_conic)
    r = R3.noncoaxial_trace(_telephoto(), rings=3)["fields"][0]
    assert r["n_vignetted"] > 0 or r["n_rays"] == 0            # the old rule loses (nearly) every ray
