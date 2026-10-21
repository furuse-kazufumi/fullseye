import numpy as np
import pytest

import graphinv
import mesh_props
import meshrepair
import recon3d
import video


class TestP051:
    def test_p051_components_identical_on_many_tiny_parts(self):
        n = 200
        vertices = np.arange((4 * n + 1) * 3, dtype=float).reshape(-1, 3)
        q = np.arange(4 * n).reshape(n, 4)
        faces = np.concatenate((q[:, [0, 1, 2]], q[:, [0, 3, 1]],
                                q[:, [0, 2, 3]], q[:, [1, 3, 2]]))
        got = meshrepair.components(vertices, faces)
        assert len(got) == n
        for i, (v, f) in enumerate(got):
            np.testing.assert_array_equal(v, vertices[q[i]])
            np.testing.assert_array_equal(np.sort(f, axis=1),
                                          np.sort([[0, 1, 2], [0, 3, 1],
                                                   [0, 2, 3], [1, 3, 2]], axis=1))

    def test_p051_single_component_and_isolated_vertex(self):
        v = np.arange(15, dtype=float).reshape(5, 3)
        out = meshrepair.components(v, np.array([[0, 2, 1], [1, 2, 3]]))
        assert len(out) == 1
        np.testing.assert_array_equal(out[0][0], v[:4])
        np.testing.assert_array_equal(out[0][1], [[0, 2, 1], [1, 2, 3]])


class TestP013:
    def test_p013_vertex_normals_fast_close_and_default_exact(self):
        v = np.array([[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0],
                      [0, 0, 1]], dtype=float)
        f = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
        exact = mesh_props.vertex_normals((v, f))
        np.testing.assert_array_equal(exact, mesh_props.vertex_normals((v, f), "exact"))
        np.testing.assert_allclose(mesh_props.vertex_normals((v, f), "fast"), exact,
                                   rtol=1e-12, atol=1e-12)
        with pytest.raises(ValueError):
            mesh_props.vertex_normals((v, f), "unknown")


class TestP044:
    @pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
    def test_p044_float_direct_matches_default(self, dtype):
        top = np.iinfo(dtype).max
        rgb = np.array([[[top, 0, 0], [0, top, 0], [0, 0, top], [0, 1, 3]]], dtype=dtype)
        rgba = np.concatenate((rgb, np.full((1, 4, 1), top, dtype=dtype)), axis=2)
        for frame in (rgb, rgba):
            np.testing.assert_allclose(video._coerce(frame, True, gray_backend="float_direct"),
                                       video._coerce(frame, True), rtol=0, atol=1e-12)


class TestP047:
    @pytest.mark.xfail(strict=True, reason="grouped refit rejected: max diff 5.96e-08; 1.99 s vs 0.261 s")
    def test_p047_grouped_refit_rejected_by_gate(self):
        import inspect
        import specularity
        assert "refit_method" in inspect.signature(specularity.photometric_stereo_robust).parameters


class TestP033:
    @pytest.mark.parametrize("size", [48, 49])
    def test_p033_fast_winding_preserves_iso_voxels(self, size):
        u = np.linspace(0, 2 * np.pi, 40, endpoint=False)
        v = np.linspace(0, np.pi, 20)
        uu, vv = np.meshgrid(u, v)
        p = np.c_[np.sin(vv).ravel() * np.cos(uu).ravel(),
                  np.sin(vv).ravel() * np.sin(uu).ravel(), np.cos(vv).ravel()]
        gp, _, _, _ = recon3d._grid_coords(p, size, 5)
        idx = np.clip(np.rint(gp).astype(np.int64), 0, size - 1)
        exact = recon3d._winding_indicator(gp, p, size, 1.0, idx, "exact")
        fast = recon3d._winding_indicator(gp, p, size, 1.0, idx, "fast")
        np.testing.assert_array_equal(exact >= 0.5, fast >= 0.5)
        assert np.max(np.abs(exact - fast)) <= 1e-12


class TestP052:
    @pytest.mark.parametrize("directed", [False, True])
    def test_p052_cycle_expression_exact_on_random_graphs(self, directed):
        for seed in range(30):
            rng = np.random.default_rng(seed)
            m = (rng.random((30, 30)) < 0.15).astype(np.int64)
            np.fill_diagonal(m, 0)
            if not directed:
                m = np.maximum(m, m.T)
            old = int(np.trace(m @ m @ m)) // 3
            new = int(np.sum((m @ m) * m.T)) // 3
            assert new == old
