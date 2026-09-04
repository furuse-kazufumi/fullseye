# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""render_beauty(vertex_normals=...): caller-supplied smooth normals for the mesh.

Contract: (1) explicitly passing the very normals the default smooth path computes
reproduces that render to float rounding (the hook unit-normalises its input, which
moves already-unit vectors by an ulp; there is no other side path);
(2) a different normal field changes only the shading, not the silhouette;
(3) wrong shape / non-finite values are refused (fail-closed).
"""
from __future__ import annotations

import numpy as np
import pytest

import render3d
import render_beauty as rb


def _sphere_mesh(subdiv=2):
    import importlib.util, os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "examples_3d", "render_beauty.py")
    spec = importlib.util.spec_from_file_location("ex_rb", p)
    ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
    return ex.icosphere(1.0, subdiv)


def _kw():
    pose = render3d.look_at([3.0, -3.0, 2.0], [0, 0, 0], up=(0, 0, 1))
    K = render3d.intrinsics_from_fov(35.0, 96, 96)
    return dict(pose=pose, intrinsics=K, size=96, ss=1, ao=False, ground_shadow=False,
                material="plastic", albedo=(0.8, 0.5, 0.3), smooth_normals=True)


def test_explicit_default_normals_reproduce_the_smooth_render():
    V, F = _sphere_mesh()
    base = rb.render_beauty(V, F, **_kw())
    vn = render3d._vertex_normals(V, F)
    again = rb.render_beauty(V, F, vertex_normals=vn, **_kw())
    # the hook re-normalises (robust API); already-unit normals move by ~1 ulp
    np.testing.assert_allclose(again, base, rtol=0, atol=1e-13)


def test_analytic_sphere_normals_change_shading_not_silhouette():
    V, F = _sphere_mesh()
    kw = _kw()
    face_based = rb.render_beauty(V, F, **kw)
    analytic = rb.render_beauty(V, F, vertex_normals=V / np.linalg.norm(V, axis=1, keepdims=True), **kw)
    assert not np.array_equal(face_based, analytic)             # shading did change
    bg = np.array(kw.get("background", (0.10, 0.11, 0.13)))
    sil_a = np.any(np.abs(face_based - bg) > 1e-9, axis=-1)
    sil_b = np.any(np.abs(analytic - bg) > 1e-9, axis=-1)
    np.testing.assert_array_equal(sil_a, sil_b)                  # geometry untouched


def test_bad_vertex_normals_are_refused():
    V, F = _sphere_mesh()
    with pytest.raises(ValueError):
        rb.render_beauty(V, F, vertex_normals=np.ones((3, 3)), **_kw())      # wrong count
    bad = np.ones((len(V), 3)); bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        rb.render_beauty(V, F, vertex_normals=bad, **_kw())                  # non-finite


# --- vertex_albedo: per-vertex RGB (vertex painting) ------------------------- #
def test_constant_vertex_albedo_reproduces_uniform_albedo():
    V, F = _sphere_mesh()
    kw = _kw()
    base = rb.render_beauty(V, F, **kw)
    va = np.tile(np.asarray(kw["albedo"], float), (len(V), 1))
    same = rb.render_beauty(V, F, vertex_albedo=va, **kw)
    np.testing.assert_allclose(same, base, rtol=0, atol=1e-12)


def test_two_colour_mesh_shows_both_colours_and_keeps_silhouette():
    V, F = _sphere_mesh()
    kw = _kw()
    va = np.where((V[:, 0] > 0)[:, None], [0.9, 0.2, 0.2], [0.2, 0.3, 0.9])   # red / blue halves
    img = rb.render_beauty(V, F, vertex_albedo=va, **kw)
    base = rb.render_beauty(V, F, **kw)
    bg = np.array((0.10, 0.11, 0.13))
    sil = np.any(np.abs(base - bg) > 1e-9, axis=-1)
    np.testing.assert_array_equal(np.any(np.abs(img - bg) > 1e-9, axis=-1), sil)
    obj = img[sil]
    assert (obj[:, 0] > obj[:, 2]).any() and (obj[:, 2] > obj[:, 0]).any()   # red-ish and blue-ish pixels


def test_bad_vertex_albedo_is_refused():
    V, F = _sphere_mesh()
    with pytest.raises(ValueError):
        rb.render_beauty(V, F, vertex_albedo=np.ones((5, 3)), **_kw())
    with pytest.raises(ValueError):
        rb.render_beauty(V, F, vertex_albedo=np.full((len(V), 3), 1.5), **_kw())   # out of [0,1]
