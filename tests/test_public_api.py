"""Public-API stability contract for Fullseye.

This is the mechanism that keeps Fullseye **consumable by other projects as it keeps
growing**: the full suite fails if a name other projects depend on is silently
removed or renamed, or if the ``fullseye`` facade stops re-exporting the public API
that ``api.py`` declares. Adding new ops/functions is always fine (additive); the
contract only guards against breaking the existing consumer-facing surface.

If you intentionally rename/remove a public function, update GOLDEN below in the
same commit — that makes the breaking change explicit and reviewable."""
import fullseye
import api


# Consumer-critical entry points that must never silently disappear. Grouped by the
# capability a downstream project (onocollo / evis / hillco / xct / mcp-3d ...) relies on.
GOLDEN = [
    # op library + pipeline designer
    "apply", "run_pipeline", "find_op", "list_ops", "op_names", "RT", "REGISTRY", "version",
    "FullseyeEngine", "FullseyeGraph",
    # camera geometry (2D<->3D backbone)
    "intrinsic_matrix", "project_points", "backproject", "depth_to_points",
    "normals_from_depth", "triangulate", "solve_pnp", "recover_pose", "essential_matrix",
    "undistort_points", "stereo_rectify", "rodrigues",
    # stereo depth
    "disparity_map", "disparity_sgm", "disparity_census", "depth_from_disparity",
    "reproject_to_points", "disparity_confidence",
    # point cloud + segmentation + registration + 6-DoF pose + grasp
    "estimate_normals", "voxel_downsample", "fit_plane_ransac", "remove_ground",
    "euclidean_clusters", "obb", "kabsch", "icp", "register", "find_surface_pose",
    "grasps_from_mesh", "force_closure",
    # terrain / locomotion / occupancy (walking)
    "elevation_map", "traversability", "foothold_candidates", "slope_map",
    "support_polygon", "com_support_margin", "gait_phase",
    "occupancy_grid_2d", "inflate_obstacles", "clearance_map", "line_of_sight",
    # motion / ego-motion / odometry / features
    "optical_flow_lk", "scene_flow", "time_to_contact", "looming",
    "rgbd_odometry", "integrate_trajectory", "trajectory_error", "match_keypoints",
    # 3-D / volumes / mesh / spectral / complex
    "read_mesh", "render_mesh", "read_volume", "vol_frangi", "cx_fft", "phase_unwrap",
    "read_envi", "spec_index",
    # I/O + visualization
    "read_image", "write_image", "to_float01", "colorize_depth", "save", "load",
    # 3-D metrology fits — (depth,row,col) analogue of the 2-D fits (numpy-only, always present)
    "fit_line3", "fit_plane3", "fit_sphere3", "fit_circle3",
    "smallest_box3", "smallest_box3_axis", "fit_box3", "smallest_sphere3", "inner_box3",
]


def test_facade_imports_and_has_version():
    assert isinstance(fullseye.__version__, str) and fullseye.__version__
    assert callable(fullseye.version)


def test_golden_public_names_present_and_usable():
    missing = [n for n in GOLDEN if not hasattr(fullseye, n)]
    assert not missing, "consumer-critical public names went missing: %s" % missing
    # functions must stay callable / classes constructible-referenced
    not_usable = [n for n in GOLDEN
                  if n not in ("RT", "REGISTRY") and not callable(getattr(fullseye, n))]
    assert not not_usable, "public names present but not callable: %s" % not_usable


def test_all_names_resolve():
    # every name the facade advertises in __all__ must actually be importable
    unresolved = [n for n in fullseye.__all__ if not hasattr(fullseye, n)]
    assert not unresolved, "fullseye.__all__ advertises missing names: %s" % unresolved


def test_no_duplicate_exports():
    dupes = sorted({n for n in fullseye.__all__ if fullseye.__all__.count(n) > 1})
    assert not dupes, "duplicate entries in fullseye.__all__: %s" % dupes


def test_facade_reexports_api_public_surface():
    # the fullseye facade is THE public entry point; it must re-export everything
    # api.py declares public, so consumers can rely on `import fullseye` alone.
    fs_names = set(fullseye.__all__) | {n for n in dir(fullseye) if not n.startswith("_")}
    dropped = [n for n in api.__all__ if n not in fs_names]
    assert not dropped, "fullseye facade stopped re-exporting api public names: %s" % dropped


def test_op_library_still_works():
    # the most-used consumer call path must keep working end to end
    import numpy as np
    frame = np.clip(np.random.default_rng(0).random((24, 28)), 0, 1)
    out = fullseye.apply(frame, "gaussian", 0.6, 0.5)
    assert out.shape == frame.shape
    assert len(fullseye.op_names()) > 300           # the catalog is non-trivial and intact


def test_facade_imports_without_torch():
    """The facade must stay importable on a numpy-only install — torch is optional.
    The numpy-only 3-D metrology (measure3d fits + inner_box3) works, and — since
    the 2026-08-30 fix that removed the hard torch imports from feat_* — the 3-D
    registry (ops3d / pipeline3d) now imports fully WITHOUT torch: only the
    torch-backed descriptor ops refuse at call time with a clear ImportError.
    This is a strictly stronger contract than the old one (ops3d degraded to
    None), and it is what keeps `pip install fullseye` (no extras) usable."""
    import os
    import subprocess
    import sys
    import textwrap
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = textwrap.dedent(
        """
        import sys, importlib.abc
        class _Block(importlib.abc.MetaPathFinder):
            def find_spec(self, name, path, target=None):
                if name.split('.')[0] in ('torch', 'kornia'):
                    raise ImportError('blocked ' + name)
                return None
        sys.meta_path.insert(0, _Block())
        import numpy as np
        import fullseye as fs
        T = np.array([[0., 0, 0], [1, 1, 0], [1, 0, 1], [0, 1, 1]])
        assert abs(fs.smallest_box3(T)['volume'] - 1.0) < 1e-6, 'smallest_box3 broken w/o torch'
        V = np.zeros((6, 7, 8), bool); V[1:5, 1:6, 1:7] = True
        assert fs.inner_box3(V)['volume'] == 4 * 5 * 6, 'inner_box3 broken w/o torch'
        assert callable(fs.fit_plane3), 'fit_plane3 missing w/o torch'
        # 3-D toolkit now survives a torch-less install (2026-08-30): the registry
        # imports and lists ops; only torch-backed ops refuse (clearly) on call.
        assert fs.ops3d is not None and fs.pipeline3d is not None, '3-D toolkit lost w/o torch'
        assert len(fs.ops3d.list_ops()) > 0, '3-D registry empty w/o torch'
        try:
            fs.ops3d.get('harris3d_keypoints')(np.zeros((8, 8, 8)))
            raise SystemExit('expected a clear ImportError for a torch-backed op')
        except ImportError as e:
            assert 'fullseye[gpu]' in str(e), str(e)
        print('OK')
        """
    )
    env = dict(os.environ, PYTHONPATH=root, PYTHONUTF8="1")
    r = subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "OK" in r.stdout, f"stdout={r.stdout!r}\nstderr={r.stderr!r}"
