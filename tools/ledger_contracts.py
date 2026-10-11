# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Contract probe for EVERY typed-ledger op (the index's ``ledger`` tier).

Each ledger op is called on representative inputs built from its declared input sorts
and judged on four contracts:

1. ``raises``           -- it runs without raising.  A ``ValueError`` is a typed refusal
                           (what the existing ledger gates accept), recorded separately as
                           ``refused`` because the op was then never exercised.
2. ``nonfinite``        -- numeric output is finite (ops in
                           ``chain_fuzz.NONFINITE_BY_CONTRACT`` are exempt by contract).
3. ``sort``             -- the output (after ``ADAPTERS``) passes the declared out-sort
                           predicate ``chain_fuzz.TYPE_CHECKS[out]``.
4. ``nondeterministic`` -- two calls on deep copies of the same arguments return
                           identical values.

Plus the reach checks ``refused`` / ``no_input`` / ``unbindable``: an op the probe could
not exercise is NOT silently dropped; it is a debt row like any other failure.

Inputs reuse the chain fuzzer (``tools/chain_fuzz``): its generators seed a type pool,
its ``OP_ARG_BUILDERS`` / ``_bind_args`` bind the arguments, and sorts that have no
generator are filled by the **declared** producer (``type_recipes``) -- chosen from the
ledger declarations alone, never from which op happened to succeed, so the inputs do
not drift with the environment.

An op whose optional backend is missing (``ImportError`` / ``NotImplementedError``, or
an upstream producer missing for that reason) is ``skip`` with the reason -- neither a
pass nor a failure, so the committed debt does not differ by environment.

``py -3.11 tools/ledger_contracts.py --write`` rewrites ``docs/LEDGER_CONTRACT_DEBT.json``
from a fresh probe.  Use it only to SHRINK the debt after fixing ops: the gate
(``tests/test_ledger_contracts.py``) refuses new debt.
"""
from __future__ import annotations

import copy
import importlib
import json
import numbers
import os
import random
import sys
import time
import warnings
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DEBT = os.path.join(ROOT, "docs", "LEDGER_CONTRACT_DEBT.json")

#: The judged contracts (the keys of the debt ledger), in report order.
CHECKS = ("refused", "no_input", "unbindable", "raises", "nonfinite", "sort",
          "nondeterministic")

_SEED = 20261011

#: Reason categories per check (``category()`` maps a failure detail onto one of these;
#: ``raises`` is ``raw_<ExceptionType>``).
CATEGORIES = {
    "refused": {"valueerror_on_probe"},
    "no_input": {"no_producer_value"},
    "unbindable": {"no_hint", "builder_raised"},
    "raises": {"raw_*"},
    "nonfinite": {"undocumented_nan_inf"},
    "sort": {"out_sort_mismatch", "returned_none", "adapter_failed"},
    "nondeterministic": {"global_rng", "fresh_state", "other"},
}

#: Size-only keyword overrides for the probe (measured 2026-10-11): these knobs scale the
#: work, not the meaning, and without them two ops took 40 s of an 82 s probe --
#: ``video_cube_orbit`` renders 36 frames of 256^2 by default (14.8 s per call) and
#: ``render_beauty`` 512^2 with 2x supersampling (5.0 s per call).
SIZE_OVERRIDES = {
    "video_cube_orbit": {"n_frames": 4, "size": 48},
    "render_beauty": {"size": 96},
}

#: Ops whose ``None`` return is the documented contract, not a sort lie (the ``sort`` check
#: accepts ``None`` for exactly these; the gate also checks that each one really returned
#: ``None`` or was skipped, so the set cannot grow into a blanket waiver).
NONE_BY_CONTRACT = {
    "integrate": "updates the TSDF volume in place (signature -> None; returning a copy would "
                 "allocate a volume per frame)",
    "intersect_planes": "parallel planes have no line (docstring: 'parallel -> None'); the "
                        "fuzzer's adversarial half draws the same vector twice",
    "world_move": "moves object i of the world dict in place (-> None)",
    "ball_set_pose": "sets the pose of object i of the world dict in place (-> None)",
    "ken_set_pose": "sets the pose of object i of the world dict in place (-> None)",
    "string_set": "re-meshes the string of object i in place (-> None)",
    "world_pose_humanoid": "poses humanoid i of the world dict in place (-> None)",
    "tid2013_root": "None when the TID2013 data is not unpacked (docstring; the data is not in "
                    "the repo and the probe clears FULLSEYE_TID2013_DATA)",
}

#: Result fields that are wall-clock measurements, documented as varying per call. They
#: are dropped before the determinism comparison -- and ONLY these fields of these ops.
VOLATILE_FIELDS = {
    "tid2013_evaluate": ("seconds",),     # run time of the evaluation (docstring)
    # per-image ``meta`` timings, read by dataset_throughput (docstring)
    "inspection_dataset": ("seconds", "seconds_render", "seconds_labels", "pixels_per_second"),
}

#: Environment variables that point ops at local datasets. Cleared while probing so a
#: developer machine with a dataset unpacked judges the same as CI (no dataset).
_DATASET_ENV = ("FULLSEYE_TID2013_DATA", "FULLSEYE_AIRHOCKEY_DATA", "FULLSEYE_DATA_DIR",
                "FULLSEYE_KENNEY_DIR")


def _cf():
    import chain_fuzz
    return chain_fuzz


def ledger_ops():
    """The index's ledger tier as ``[(name, ledger_module, in_sorts, out_sort, fn)]``.

    Enumerated exactly like ``docs/OP_INDEX.json`` (``api.ledger_rows``: the first family
    wins a duplicated name; names taken by the registry / n-ary tiers are not ledger rows),
    and the callable is taken from the row's own ledger table.
    """
    import api
    import opassist
    tables = dict(opassist._LEDGERS)
    out = []
    for r in api.ledger_rows():
        mod = importlib.import_module(r["ledger"])
        meta = getattr(mod, tables[r["ledger"]])[r["name"]]
        out.append((r["name"], r["ledger"], list(meta["in"]), meta["out"], meta["func"]))
    return out


# --------------------------------------------------------------------------- #
# value helpers                                                                #
# --------------------------------------------------------------------------- #
def _to_numpy(v):
    """torch tensors compare / scan as numpy; everything else unchanged."""
    if type(v).__module__.startswith("torch") and hasattr(v, "detach"):
        return v.detach().cpu().numpy()
    return v


def nonfinite(v, depth=0):
    """True when *v* holds a NaN / Inf anywhere a number lives (arrays, scalars,
    containers, plain objects' attributes)."""
    if depth > 6:
        return False
    v = _to_numpy(v)
    if isinstance(v, np.ndarray):
        if v.dtype.kind in "fc":
            return not bool(np.isfinite(v).all())
        if v.dtype.kind == "O":
            return any(nonfinite(x, depth + 1) for x in v.flat)
        return False
    if isinstance(v, (bool, np.bool_, numbers.Integral)):
        return False
    if isinstance(v, numbers.Number):
        try:
            return not bool(np.isfinite(v))
        except TypeError:
            return False
    if isinstance(v, dict):
        return any(nonfinite(x, depth + 1) for x in v.values())
    if isinstance(v, (list, tuple)):
        return any(nonfinite(x, depth + 1) for x in v)
    d = getattr(v, "__dict__", None)
    if isinstance(d, dict) and not callable(v) and not isinstance(v, type):
        return any(nonfinite(x, depth + 1) for x in d.values())
    return False


#: "this pair cannot be compared reliably" (counted and reported, never a pass or fail).
UNCOMPARABLE = "uncomparable"


def same(a, b, depth=0):
    """Structural equality: ``True`` / ``False`` / :data:`UNCOMPARABLE`."""
    if depth > 8:
        return True
    a, b = _to_numpy(a), _to_numpy(b)
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        if not (isinstance(a, np.ndarray) and isinstance(b, np.ndarray)):
            return False
        if a.shape != b.shape or a.dtype != b.dtype:
            return False
        if a.dtype.kind == "O":
            return _all_same(list(a.flat), list(b.flat), depth)
        if a.dtype.kind in "fc":
            return bool(np.array_equal(a, b, equal_nan=True))
        return bool(np.array_equal(a, b))
    num = (numbers.Number, np.bool_)
    if type(a) is not type(b) and not (isinstance(a, num) and isinstance(b, num)):
        return False
    if a is None or isinstance(a, (str, bytes, bool, np.bool_, numbers.Integral)):
        return bool(a == b)
    if isinstance(a, numbers.Number):
        if a != a and b != b:                    # both NaN
            return True
        return bool(a == b)
    if isinstance(a, dict):
        if set(a) != set(b):
            return False
        return _all_same([a[k] for k in a], [b[k] for k in a], depth)
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return False
        return _all_same(list(a), list(b), depth)
    if isinstance(a, (set, frozenset)):
        return a == b
    if callable(a):
        return getattr(a, "__qualname__", None) == getattr(b, "__qualname__", None)
    d = getattr(a, "__dict__", None)
    if isinstance(d, dict):
        return same(d, getattr(b, "__dict__", None), depth + 1)
    try:
        r = a == b
        if isinstance(r, (bool, np.bool_)):
            return bool(r)
    except Exception:                            # noqa: BLE001 - foreign objects
        pass
    return UNCOMPARABLE


def _all_same(xs, ys, depth):
    unc = False
    for x, y in zip(xs, ys):
        r = same(x, y, depth + 1)
        if r is False:
            return False
        unc = unc or r is UNCOMPARABLE
    return UNCOMPARABLE if unc else True


def optional_missing(exc):
    """The environment lacks an optional backend (not a defect of the op)."""
    return isinstance(exc, (ImportError, NotImplementedError))


def _rng(name):
    return np.random.default_rng((_SEED, zlib.crc32(name.encode("utf-8"))))


# --------------------------------------------------------------------------- #
# binding                                                                      #
# --------------------------------------------------------------------------- #
class Unbound(Exception):
    """No argument list could be built for the op (a gap of the probe, recorded)."""


def _io_builders():
    """The 3 ledger ops the chain fuzzer leaves out (``category == "io"``: files).

    Probed with a WAV the probe itself writes into the scratch cwd (``_scratch_cwd``).
    """
    def wav(pool, rng):
        import dsp
        p = "ledger_contract_probe.wav"
        dsp.write_wav(p, 0.5 * np.sin(np.linspace(0, 40 * np.pi, 800)), 8000)
        return [p], {}
    return {
        "read_wav": wav,
        "read_audio": wav,
        "write_wav": lambda pool, rng: (
            ["ledger_contract_probe_out.wav", 0.5 * np.sin(np.linspace(0, 20 * np.pi, 400))], {}),
    }


# --------------------------------------------------------------------------- #
# probe-local builders (2026-10-11)                                            #
# --------------------------------------------------------------------------- #
# The ``refused`` debt is mostly the PROBE's fault, not the op's: a ``table`` from the
# pool is a generic {pre, post} dict, but ``paraxial_trace`` wants the dict
# ``lens_system()`` returns and says so (a typed refusal -- the op is right). These
# builders hand each op the value its own docstring names, built by the documented
# producer, so the op is exercised instead of refusing. They live here (not in
# ``chain_fuzz.OP_ARG_BUILDERS``) so the fuzzer's adversarial mix and its pinned
# findings do not move. A tuple is ``(args, kwargs)``; a list is the data arguments
# only (the rest is bound by the usual hints).
def _optics_kit():
    import illumdesign
    import optscene as OS
    cam = OS.optical_camera(resolution=(24, 24), working_distance_mm=120.0)
    scene = [OS.scene_plane(0.0), OS.scene_sphere((0.0, 0.0, 6.0), 6.0)]
    light = illumdesign.light_source(kind="ring", radius_mm=60.0, height_mm=80.0, n=8)
    return OS, cam, scene, light


def _lens(name="singlet"):
    import raytrace
    return raytrace.example_system(name)


def _labels3d():
    lab = np.zeros((12, 12, 12), np.int64)
    lab[1:5, 1:5, 1:5] = 1
    lab[6:11, 2:6, 6:11] = 2
    lab[2:6, 7:11, 7:10] = 3
    return lab


def _srgb(rng, shape=(16, 16, 3)):
    return np.clip(rng.random(shape), 0.0, 1.0)


def _tex(rng):
    """A fixed smooth texture (seeded by a constant, so a and b differ only by the shift)."""
    g = np.random.default_rng(7).random((64, 64))
    from scipy import ndimage
    return ndimage.gaussian_filter(g, 1.0)


def _rot(rng):
    q, r = np.linalg.qr(rng.standard_normal((3, 3)))
    q = q * np.sign(np.diag(r))
    return q * np.sign(np.linalg.det(q))


def _optics_builders():
    def lens_first(**kw):
        return lambda pool, rng: ([_lens()], dict(kw))

    def os_call(make):
        def b(pool, rng):
            OS, cam, scene, light = _optics_kit()
            return make(OS, cam, scene, light, rng)
        return b

    def layout(OS, light):
        return OS.vision_layout(OS.sensor_spec(resolution=(24, 24)),
                                OS.lens_spec(f_number=4.0), [light],
                                scene=[OS.scene_plane(0.0)])

    out = {
        # lens prescriptions (raytrace / lensopt / lensimage)
        "paraxial_trace": lens_first(), "seidel_coefficients": lens_first(),
        "spot_stats": lens_first(rings=3), "spot_diagram": lens_first(rings=3),
        "tolerance_analysis": lens_first(trials=4, rings=3),
        "wavefront_from_opd": lens_first(size=16), "ray_fan": lens_first(n=9),
        "opd_map": lens_first(size=16), "chromatic_shift": lens_first(rings=3),
        "optimize_lens": lens_first(iterations=2, rings=2),
        "merit_function": lens_first(rings=2), "psf_from_opd": lens_first(),
        "distortion_map": lens_first(image_size=(32, 32)),
        "calibration_views": lens_first(image_size=(64, 64)),
        "render_through_lens": lambda pool, rng: (
            [rng.random((32, 32)), _lens()], {}),
        # illumination designs
        "irradiance_map": lambda pool, rng: ([_optics_kit()[3]], {"shape": (16, 16)}),
        "defect_contrast": lambda pool, rng: ([_optics_kit()[3]], {"n_azimuth": 4}),
        # optical scenes
        "camera_rays": os_call(lambda OS, cam, sc, li, rng: ([cam], {})),
        "render_optscene": os_call(lambda OS, cam, sc, li, rng: ([sc, cam, [li]], {})),
        "optscene_depth": os_call(lambda OS, cam, sc, li, rng: ([sc, cam], {})),
        "optscene_mask": os_call(lambda OS, cam, sc, li, rng: ([sc, cam], {"index": 1})),
        "optscene_defect_mask": os_call(lambda OS, cam, sc, li, rng: ([sc, cam], {})),
        "optscene_instances": os_call(lambda OS, cam, sc, li, rng: ([sc, cam], {})),
        "render_studio": os_call(lambda OS, cam, sc, li, rng: ([sc, cam], {"samples": 2, "depth": 1})),
        "linescan_capture": os_call(lambda OS, cam, sc, li, rng: ([sc, cam, [li]], {"lines": 8})),
        "inspection_dataset": os_call(lambda OS, cam, sc, li, rng: ([sc, cam, [li]], {"n": 2})),
        "dataset_throughput": os_call(lambda OS, cam, sc, li, rng: (
            [OS.inspection_dataset(sc, cam, [li], n=2)], {})),
        "defocus_blur": os_call(lambda OS, cam, sc, li, rng: (
            [_srgb(rng, (24, 24, 3)), OS.optscene_depth(sc, cam), cam], {})),
        "diffraction_blur": os_call(lambda OS, cam, sc, li, rng: ([_srgb(rng, (24, 24, 3)), cam], {})),
        "trace_rays": os_call(lambda OS, cam, sc, li, rng: (
            [sc, np.tile([0.0, 0.0, 50.0], (8, 1)),
             np.tile([0.0, 0.0, -1.0], (8, 1)) + 0.05 * rng.standard_normal((8, 3))], {})),
        "illumination_visibility": os_call(lambda OS, cam, sc, li, rng: (
            [sc, np.column_stack([rng.uniform(-20, 20, (8, 2)), np.zeros(8)]), li], {})),
        "surface_defect": os_call(lambda OS, cam, sc, li, rng: ([sc[0], rng.random((24, 24))], {})),
        "surface_finish": os_call(lambda OS, cam, sc, li, rng: ([sc[0]], {"shape": (32, 32)})),
        "random_defects": os_call(lambda OS, cam, sc, li, rng: ([sc[0]], {})),
        "scene_difference": os_call(lambda OS, cam, sc, li, rng: (
            [OS.scene_box((0.0, 0.0, 5.0), (5.0, 5.0, 5.0)), OS.scene_sphere((0.0, 0.0, 10.0), 3.0)], {})),
        "scene_sphere": os_call(lambda OS, cam, sc, li, rng: ([(0.0, 0.0, 5.0), 5.0], {})),
        "scene_box": os_call(lambda OS, cam, sc, li, rng: ([(0.0, 0.0, 5.0), (4.0, 4.0, 4.0)], {})),
        "scene_cylinder": os_call(lambda OS, cam, sc, li, rng: ([(0.0, 0.0, 5.0), 4.0, 3.0], {})),
        "sensor_diagonal_mm": os_call(lambda OS, cam, sc, li, rng: ([OS.sensor_spec()], {})),
        "covers_sensor": os_call(lambda OS, cam, sc, li, rng: (
            [OS.lens_spec(f_number=4.0, image_circle_mm=16.0), OS.sensor_spec()], {})),
        "lens_spec": lambda pool, rng: ([], {"f_number": 4.0}),
        "optical_budget": lambda pool, rng: ([], {"f_number": 4.0}),
        "interface_budget": os_call(lambda OS, cam, sc, li, rng: ([OS.sensor_spec()], {})),
        "vision_layout": os_call(lambda OS, cam, sc, li, rng: (
            [OS.sensor_spec(resolution=(24, 24)), OS.lens_spec(f_number=4.0), [li]], {})),
        "layout_capture": os_call(lambda OS, cam, sc, li, rng: (
            [layout(OS, li)], {"supersample": 1})),
    }
    return out


def _array_builders():
    def lab3(*extra):
        return lambda pool, rng: ([_labels3d()] + [e(rng) for e in extra], {})
    spd = lambda rng: (lambda a: a @ a.T + 3.0 * np.eye(4))(rng.standard_normal((4, 4)))  # noqa: E731
    return {
        # 3-D label volumes (the pool's labels are 2-D half the time)
        "vol_colorize_labels": lab3(), "vol_label_shape_stats": lab3(),
        "vol_label_legend": lab3(), "vol_select_labels": lab3(),
        "vol_labels_to_meshes": lab3(), "vol_label_volume_render": lab3(),
        "vol_region_props": lab3(), "vol_nearest_label": lab3(),
        "vol_label_overlay": lambda pool, rng: ([rng.random((12, 12, 12)), _labels3d()], {}),
        "skeleton_graph3d": lambda pool, rng: ([_labels3d() > 0], {}),
        "vol_resize": lambda pool, rng: ([rng.random((12, 12, 12))], {"factor": 0.5}),
        # sRGB must lie in [0, 1]
        "rgb_to_lab": lambda pool, rng: ([_srgb(rng)], {}),
        "rgb_to_xyz": lambda pool, rng: ([_srgb(rng)], {}),
        "delta_e_map": lambda pool, rng: ([_srgb(rng), _srgb(rng)], {}),
        "color_transfer": lambda pool, rng: ([_srgb(rng), _srgb(rng)], {}),
        # square / structured matrices
        "mat_lu": lambda pool, rng: ([rng.standard_normal((5, 5)) + 5.0 * np.eye(5)], {}),
        "mat_qr": lambda pool, rng: ([rng.standard_normal((6, 4))], {}),
        "mat_cholesky": lambda pool, rng: ([spd(rng)], {}),
        "mat_eig": lambda pool, rng: ([rng.standard_normal((5, 5))], {}),
        "mat_expm": lambda pool, rng: ([0.3 * rng.standard_normal((4, 4))], {}),
        "mat_logm": lambda pool, rng: ([spd(rng)], {}),
        "se3_exp": lambda pool, rng: ([0.3 * rng.standard_normal(6)], {}),
        "se3_log": lambda pool, rng: ([np.block([[_rot(rng), rng.standard_normal((3, 1))],
                                                 [np.zeros((1, 3)), np.ones((1, 1))]])], {}),
        "color_correction_matrix": lambda pool, rng: (
            [_srgb(rng), np.eye(3) + 0.05 * rng.standard_normal((3, 3))], {}),
        "rgb_apply_gains": lambda pool, rng: ([_srgb(rng), rng.uniform(0.5, 2.0, 3)], {}),
        "raw_apply_gains": lambda pool, rng: ([rng.random((16, 16)), rng.uniform(0.5, 2.0, 4)], {}),
        "chebyshev_eval_nd": lambda pool, rng: (
            [__import__("mathnumerics").chebyshev_coeffs_nd(rng.random((6, 5))),
             rng.uniform(-1.0, 1.0, (10, 2))], {}),
        "delaunay_triangulate": lambda pool, rng: ([rng.random((20, 2))], {}),
        "nurbs_curve": lambda pool, rng: ([rng.random((6, 2))], {"n": 40}),
        "nurbs_revolve": lambda pool, rng: ([np.column_stack([1.0 + rng.random(5), np.linspace(0, 1, 5)])],
                                            {"n": (12, 12)}),
        "hist_distance": lambda pool, rng: ([rng.random(16) + 0.1, rng.random(16) + 0.1], {}),
        "stat_chi2_gof": lambda pool, rng: ([rng.integers(5, 30, 8).astype(float)], {}),
        "lomb_scargle": lambda pool, rng: (
            [np.sort(rng.uniform(0, 10, 60)), np.sin(np.linspace(0, 20, 60)), np.linspace(0.05, 2.0, 40)], {}),
        "hankel_transform": lambda pool, rng: (
            [np.linspace(0.0, 5.0, 64), np.exp(-np.linspace(0.0, 5.0, 64) ** 2)], {"n": 64}),
        "ms_ssim": lambda pool, rng: ([rng.random((48, 48)), rng.random((48, 48))],
                                      {"weights": (0.5, 0.5), "win_size": 7}),
        "piv_multipass": lambda pool, rng: (
            [_tex(rng), np.roll(_tex(rng), 1, 0)], {"windows": (32, 16)}),
    }


def _batch2_builders():
    """Second batch (2026-10-11): one-line inputs in the units / ranges the docstrings state."""
    nm = lambda: np.linspace(400.0, 700.0, 31)                       # noqa: E731
    cos_i = lambda rng: np.linspace(0.05, 1.0, 16)                   # noqa: E731
    H = np.linspace(1.0, 100.0, 12)                                  # exposure steps
    mu_y = 10.0 + 2.0 * H                                            # linear response [DN]
    airfoil = lambda: (lambda t: np.column_stack(                    # noqa: E731
        [0.5 + 0.5 * np.cos(t), 0.08 * np.sin(t) * (1.0 + 0.3 * np.cos(t))]))(
            np.linspace(0.0, 2.0 * np.pi, 120, endpoint=False))

    def pose6(rng):
        return np.concatenate([0.2 * rng.standard_normal(3), rng.standard_normal(3)])

    def T(rng):
        return np.block([[_rot(rng), rng.standard_normal((3, 1))], [np.zeros((1, 3)), np.ones((1, 1))]])

    def ot(rng):
        a = rng.random(6) + 0.1
        b = rng.random(5) + 0.1
        x, y = np.linspace(0, 1, 6), np.linspace(0, 1, 5)
        return a / a.sum(), b / b.sum(), (x[:, None] - y[None, :]) ** 2

    def ot_sq(rng):
        a = rng.random(6) + 0.1
        b = rng.random(6) + 0.1
        x = np.linspace(0, 1, 6)
        return a / a.sum(), b / b.sum(), (x[:, None] - x[None, :]) ** 2

    def plan(rng):
        import colortransport
        a, b, c = ot(rng)
        return colortransport.sinkhorn(a, b, c), c

    def ula(rng):
        import mathspectral
        return mathspectral.ula_snapshots((10.0, -20.0), n_elements=8, n_snapshots=64)

    return {
        # ★探針の 32×32 だと目盛の文字幅が書体で変わり、手元(Windows の書体)は右に 3 px はみ出して
        #   拒否・CI(代替書体)は収まって通る —— 環境で判定が割れた(2026-10-11)。余白を取って両方で通す。
        "annotate_colorbar": lambda pool, rng: ((np.full((96, 128), 0.5), np.outer(np.linspace(0.0, 1.0, 96), np.ones(128)),
                                                 (8, 8, 12, 80)), {}),
        # optics: physical ranges (cos in [0, 1], wavelengths in nm, path >= 0)
        "fresnel_dielectric": lambda pool, rng: ([cos_i(rng)], {}),
        "fresnel_conductor": lambda pool, rng: ([cos_i(rng), 0.2, 3.0], {}),
        "slab_transmittance": lambda pool, rng: ([cos_i(rng)], {}),
        "rough_transmission": lambda pool, rng: ([cos_i(rng)], {}),
        "cie_xyz_from_wavelength": lambda pool, rng: ([nm()], {}),
        "thin_film_reflectance": lambda pool, rng: ([nm()], {}),
        "prism_min_deviation_deg": lambda pool, rng: ([nm()], {}),
        "beer_lambert_transmittance": lambda pool, rng: ([np.linspace(0.0, 50.0, 16)], {}),
        "metal_optical_constants": lambda pool, rng: ([], {"metal": "al", "wavelength_nm": nm()}),
        "spectrum_to_srgb": lambda pool, rng: ([nm(), rng.random(31)], {}),
        "grating_wavelengths": lambda pool, rng: ([1.6, 0.0, 0.45], {}),
        "mueller_checks": lambda pool, rng: ([np.eye(4)], {}),
        "veiling_glare_index": lambda pool, rng: (
            [rng.random((32, 32)), np.pad(np.ones((8, 8), bool), 12), ~np.pad(np.ones((16, 16), bool), 8)], {}),
        "mtf50": lambda pool, rng: ([np.column_stack([np.linspace(0, 0.5, 26), np.exp(-np.linspace(0, 0.5, 26) / 0.2)])], {}),
        # EMVA 1288: a linear camera
        "emva_photon_transfer": lambda pool, rng: ([mu_y, 0.5 * (mu_y - 10.0) + 4.0, 10.0, 4.0, mu_y[-1] * 1.05], {}),
        "emva_quantum_efficiency": lambda pool, rng: ([5.0 * H, mu_y, 10.0, mu_y[-1] * 1.05, 0.5], {}),
        "emva_linearity_error": lambda pool, rng: ([H, mu_y + 0.1 * np.sin(H), 10.0, mu_y[-1] * 1.05], {}),
        "emva_snr_curve": lambda pool, rng: ([np.linspace(1.0, 1e4, 20), 0.6, 3.0, 0.5], {}),
        "emva_sensitivity_threshold": lambda pool, rng: ([0.6, 3.0, 0.5], {}),
        "emva_dynamic_range": lambda pool, rng: ([5e4, 10.0], {}),
        "emva_defect_pixels": lambda pool, rng: ([100.0 + rng.standard_normal((32, 32)), 16, 3.0], {}),
        "emva_dark_current": lambda pool, rng: ([np.linspace(0.01, 0.06, 6), 10.0 + 30.0 * np.linspace(0.01, 0.06, 6), 0.5], {}),
        "emva_spatial_nonuniformity": lambda pool, rng: (
            [10.0 + rng.standard_normal((4, 16, 16)), 200.0 + 3.0 * rng.standard_normal((4, 16, 16)), 0.5], {}),
        # transport (shapes that agree)
        "sinkhorn": lambda pool, rng: (list(ot(rng)), {}),
        "sinkhorn_distance": lambda pool, rng: (list(ot(rng)), {}),
        "sinkhorn_divergence": lambda pool, rng: (list(ot_sq(rng)), {}),
        "transport_cost": lambda pool, rng: (list(plan(rng)), {}),
        "apply_transport": lambda pool, rng: ([plan(rng)[0], rng.random(5)], {}),
        # geometry / poses
        "distance_segment_segment": lambda pool, rng: ([rng.standard_normal(3) for _ in range(4)], {}),
        "relative_pose": lambda pool, rng: ([pose6(rng), pose6(rng)], {}),
        "rotation_translation_error": lambda pool, rng: ([T(rng), T(rng)], {}),
        "dem_ecef_to_geodetic": lambda pool, rng: (
            [np.array([[6378137.0, 0.0, 0.0], [0.0, 6378137.0, 100.0], [4.0e6, 3.0e6, 3.5e6]])], {}),
        # representation conversions
        "indices_to_labels": lambda pool, rng: ([np.array([0, 3, 5, 7])], {}),
        "select_points": lambda pool, rng: ([rng.random((10, 3)), np.array([0, 3, 5, 7])], {}),
        "polar_to_cscalar": lambda pool, rng: ([np.array([[2.0, 0.5]])], {}),
        "shape_index_to_curvature": lambda pool, rng: ([np.column_stack([np.linspace(-0.9, 0.9, 8), np.ones(8)])], {}),
        "curvature_to_shape_index": lambda pool, rng: ([np.column_stack([rng.random(8) + 0.5, rng.random(8)])], {}),
        "curvature_to_table": lambda pool, rng: ([np.column_stack([rng.random(8) + 0.5, rng.random(8)])], {}),
        # math / statistics
        "interp_scattered": lambda pool, rng: (
            [rng.random((40, 2)), rng.random(40), 0.2 + 0.6 * rng.random((10, 2))], {}),
        "stat_ttest_paired": lambda pool, rng: ([rng.random(12), rng.random(12) + 0.1], {}),
        "laplace_inverse_talbot": lambda pool, rng: ([np.array([1.0]), np.array([1.0, 1.0]), np.linspace(0.1, 3.0, 8)], {}),
        "crlb_gaussian": lambda pool, rng: ([np.linspace(-3, 3, 41), np.array([1.0, 0.0, 1.0])], {}),
        "ula_snapshots": lambda pool, rng: ([], {"angles_deg": (10.0, -20.0), "n_snapshots": 64}),
        "music_doa": lambda pool, rng: ([ula(rng)["X"] if isinstance(ula(rng), dict) else ula(rng)], {"n_sources": 2}),
        "esprit_doa": lambda pool, rng: ([ula(rng)["X"] if isinstance(ula(rng), dict) else ula(rng)], {"n_sources": 2}),
        "sun_position": lambda pool, rng: ([35.68, 139.77, 1.7e9 + 3600.0 * np.arange(6)], {}),
        # sections, monogenic signals, attention
        "profile_sides": lambda pool, rng: ([airfoil()], {}),
        "profile_thickness": lambda pool, rng: ([airfoil()], {}),
        "profile_camber": lambda pool, rng: ([airfoil()], {}),
        "profile_trailing_edge_gap": lambda pool, rng: ([airfoil()], {}),
        "monogenic_amplitude": lambda pool, rng: ([__import__("quatimage").monogenic_signal(_tex(rng)[:32, :32])], {}),
        "monogenic_phase": lambda pool, rng: ([__import__("quatimage").monogenic_signal(_tex(rng)[:32, :32])], {}),
        "monogenic_orientation": lambda pool, rng: ([__import__("quatimage").monogenic_signal(_tex(rng)[:32, :32])], {}),
        "kv_cache_decode": lambda pool, rng: ([rng.standard_normal((1, 8)), rng.standard_normal((6, 8)),
                                               rng.standard_normal((6, 8))], {}),
        "attention_grouped": lambda pool, rng: ([rng.standard_normal((6, 8)), rng.standard_normal((6, 4)),
                                                 rng.standard_normal((6, 4))], {"n_heads": 2, "n_kv_heads": 1}),
    }


def probe_builders():
    """Every probe-local builder (name -> builder)."""
    out = dict(_optics_builders())
    out.update(_array_builders())
    out.update(_batch2_builders())
    return out


def bind(name, fn, ins, pool, cf, extra):
    """→ ``(args, kwargs)``; raises :class:`Unbound` (or the builder's own exception)."""
    args, kwargs = _bind_raw(name, fn, ins, pool, cf, extra)
    kwargs.update(SIZE_OVERRIDES.get(name, {}))
    return args, kwargs


def _bind_raw(name, fn, ins, pool, cf, extra):
    rng = _rng(name)
    if name in extra:
        args, kwargs = extra[name](pool, rng)
        return _bind_rest(name, fn, list(args), dict(kwargs), cf, rng)
    if name in cf.OP_ARG_BUILDERS:
        bound = cf.OP_ARG_BUILDERS[name](pool, rng)
        if isinstance(bound, list):
            bound = cf._bind_args(name, fn, bound, rng)
        if bound is None:
            raise Unbound("OP_ARG_BUILDERS / hints could not build the arguments")
        return list(bound[0]), dict(bound[1])
    gens = sorted(cf.make_generators())
    data = []
    for t in ins:
        if t == "any":
            t = gens[int(rng.integers(len(gens)))]
        data.append(pool[t][0])
    bound = cf._bind_args(name, fn, data, rng)
    if bound is None:
        raise Unbound("a required argument has no hint (PARAM_HINTS / OP_PARAM_HINTS)")
    return list(bound[0]), dict(bound[1])


def _bind_rest(name, fn, args, kwargs, cf, rng):
    """Bind the required parameters a builder left open (op hint, then name hint)."""
    import inspect
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return args, kwargs
    for p in params[len(args):]:
        if p.kind not in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY) or p.name in kwargs \
                or p.default is not inspect.Parameter.empty:
            continue
        hint = cf.OP_PARAM_HINTS.get((name, p.name)) or cf.PARAM_HINTS.get(p.name)
        val = hint(rng) if hint is not None else None
        if val is None:
            raise Unbound("a required argument has no hint: %s" % p.name)
        kwargs[p.name] = val
    return args, kwargs


def _call(fn, args, kwargs):
    # deep copies: an op that writes into its input (``integrate`` is in-place by design)
    # must not change what the second call -- or the next op -- sees.
    a, k = copy.deepcopy(args), copy.deepcopy(kwargs)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(*a, **k)


# --------------------------------------------------------------------------- #
# one op                                                                       #
# --------------------------------------------------------------------------- #
def probe_one(name, ins, out, fn, pool, cf=None, extra=None):
    """Probe one op → ``{"status", "check", "detail", "sec", "result"}``.

    ``status`` is ``ok`` / ``fail`` / ``skip``; for ``fail``, ``check`` is the list of
    failed contracts (names from :data:`CHECKS`).
    """
    cf = _cf() if cf is None else cf
    extra = dict(_io_builders(), **probe_builders()) if extra is None else extra
    lack = sorted({t for t in ins if t != "any" and not pool.get(t)})
    if lack and name not in extra:
        return {"status": "fail", "check": ["no_input"],
                "detail": "no value of sort %s" % ", ".join(lack)}
    try:
        args, kwargs = bind(name, fn, ins, pool, cf, extra)
    except Unbound as e:
        return {"status": "fail", "check": ["unbindable"], "detail": str(e)}
    except Exception as e:                       # noqa: BLE001 - a builder broke
        if optional_missing(e):
            return {"status": "skip", "detail": "optional backend missing while binding: "
                    "%s: %s" % (type(e).__name__, str(e)[:120])}
        return {"status": "fail", "check": ["unbindable"],
                "detail": "argument builder raised %s: %s" % (type(e).__name__, str(e)[:120])}
    t0 = time.perf_counter()
    try:
        res = _call(fn, args, kwargs)
    except Exception as e:                       # noqa: BLE001 - the point of the probe
        if optional_missing(e):
            return {"status": "skip", "detail": "optional backend missing: %s: %s"
                    % (type(e).__name__, str(e)[:120])}
        if isinstance(e, ValueError):
            return {"status": "fail", "check": ["refused"],
                    "detail": "ValueError: %s" % str(e)[:160]}
        return {"status": "fail", "check": ["raises"],
                "detail": "%s: %s" % (type(e).__name__, str(e)[:160])}
    sec = time.perf_counter() - t0
    adapter = cf.ADAPTERS.get(name)
    if adapter is not None:
        try:
            res = adapter(res)
        except Exception as e:                   # noqa: BLE001
            return {"status": "fail", "check": ["sort"], "sec": sec,
                    "detail": "sort: result adapter failed: %s: %s"
                    % (type(e).__name__, str(e)[:120])}
    failures = []
    if name not in cf.NONFINITE_BY_CONTRACT and nonfinite(res):
        failures.append(("nonfinite", "NaN/Inf in the output"))
    pred = cf.TYPE_CHECKS.get(out)
    if res is None and name in NONE_BY_CONTRACT:
        pass                                     # documented "no result" (see NONE_BY_CONTRACT)
    elif res is None:
        failures.append(("sort", "declared %r but returned None" % out))
    elif pred is None:
        failures.append(("sort", "declared sort %r has no predicate in TYPE_CHECKS" % out))
    else:
        try:
            ok = bool(pred(res))
        except Exception:                        # noqa: BLE001 - a predicate that chokes = mismatch
            ok = False
        if not ok:
            failures.append(("sort", "declared %r but returned %s%s" % (
                out, type(res).__name__, getattr(res, "shape", ""))))
    eq = True
    try:
        res2 = _call(fn, args, kwargs)
        if adapter is not None:
            res2 = adapter(res2)
        eq = same(_stable(name, res), _stable(name, res2))
    except Exception as e:                       # noqa: BLE001
        failures.append(("nondeterministic", "other: the second identical call raised "
                         "%s: %s" % (type(e).__name__, str(e)[:100])))
    else:
        if eq is False:
            failures.append(("nondeterministic", why_nondeterministic(fn, args, kwargs, adapter)))
    v = {"status": "ok", "sec": sec, "result": res, "comparable": eq is not UNCOMPARABLE,
         "returned_none": res is None}
    if failures:
        v.update(status="fail", check=[c for c, _ in failures],
                 detail="; ".join("%s: %s" % f for f in failures))
    return v


def _stable(name, res):
    """*res* without the documented wall-clock fields (:data:`VOLATILE_FIELDS`)."""
    drop = VOLATILE_FIELDS.get(name)
    if not drop:
        return res

    def strip(x, depth=0):
        if depth > 4:
            return x
        if isinstance(x, dict):
            return {k: strip(v, depth + 1) for k, v in x.items() if k not in drop}
        if isinstance(x, list):
            return [strip(v, depth + 1) for v in x]
        return x
    return strip(res)


def why_nondeterministic(fn, args, kwargs, adapter):
    """Reason category: does seeding the global RNGs make the op repeatable?"""
    outs = []
    # the global RNG state is put back afterwards: seeding it here must not leak into
    # whatever runs next in the same process.
    np_state, py_state = np.random.get_state(), random.getstate()
    try:
        for _ in range(2):
            np.random.seed(_SEED & 0xFFFFFFFF)
            random.seed(_SEED)
            try:
                r = _call(fn, args, kwargs)
                outs.append(adapter(r) if adapter is not None else r)
            except Exception:                    # noqa: BLE001
                return "other: differs between calls (and raised when re-run seeded)"
    finally:
        np.random.set_state(np_state)
        random.setstate(py_state)
    if same(outs[0], outs[1]) is True:
        return "global_rng: repeatable only when np.random / random are seeded"
    return ("fresh_state: differs even with the global RNGs seeded "
            "(unseeded default_rng / clock / ordering)")


# --------------------------------------------------------------------------- #
# every op                                                                     #
# --------------------------------------------------------------------------- #
def run(ops=None, verbose=False):
    """Probe every op → ``{name: verdict}`` (verdicts keep no results, to stay small).

    Ops run in index order, in rounds: an op whose input sort has no generator waits
    until the sort's **declared** producer has run and returned a value of that sort.
    """
    cf = _cf()
    ops = ledger_ops() if ops is None else ops
    gens = cf.make_generators()
    extra = dict(_io_builders(), **probe_builders())
    verdict = {}
    saved_env = {k: os.environ.pop(k) for k in _DATASET_ENV if k in os.environ}
    try:
        _run(ops, cf, gens, extra, verdict, verbose)
    finally:
        os.environ.update(saved_env)
    return verdict


def _run(ops, cf, gens, extra, verdict, verbose):
    with cf._scratch_cwd():
        base = np.random.default_rng(_SEED)
        pool = {t: [g(base)] for t, g in sorted(gens.items())}
        recipe = cf.type_recipes(list(ops), gens)
        producer = {t: r[-1] for t, r in recipe.items() if r}
        why_empty = {}                          # sort -> what its producer did instead
        pending = list(ops)
        while pending:
            progressed, rest = False, []
            for op in pending:
                name, _led, ins, out, fn = op
                if name not in extra and any(not pool.get(t) for t in ins if t != "any"):
                    rest.append(op)
                    continue
                v = probe_one(name, ins, out, fn, pool, cf, extra)
                res = v.pop("result", None)
                verdict[name] = v
                progressed = True
                if verbose:
                    print("%-4s %-38s %6.2fs %s" % (v["status"], name, v.get("sec", 0.0),
                                                    v.get("detail", "")[:100]), flush=True)
                if producer.get(out) == name and not pool.get(out):
                    bad = set(v.get("check") or ()) & {"sort", "nonfinite"}
                    if "sec" in v and not bad and v["status"] != "skip":
                        pool[out] = [res]
                    else:
                        why_empty[out] = "%s %s (%s)" % (name, v["status"], v.get("detail", ""))
            if not progressed:
                for name, _led, ins, _out, _fn in rest:
                    lack = sorted({t for t in ins if t != "any" and not pool.get(t)})
                    why = "; ".join("%s <- %s" % (t, why_empty.get(t, "no declared producer"))
                                    for t in lack)
                    if any(" skip " in why_empty.get(t, "") for t in lack):
                        verdict[name] = {"status": "skip",
                                         "detail": "upstream producer skipped: " + why}
                    else:
                        verdict[name] = {"status": "fail", "check": ["no_input"],
                                         "detail": "no value of sort %s: %s" % (", ".join(lack), why)}
                break
            pending = rest


def category(check, detail):
    """A coarse, stable reason category for one failure (the detail text drifts)."""
    if check == "raises":
        return "raw_" + detail.split(":", 1)[0]
    if check == "nondeterministic":
        for part in detail.split("; "):
            if part.startswith("nondeterministic: "):
                return part[len("nondeterministic: "):].split(":", 1)[0]
        return "other"
    if check == "sort":
        if "returned None" in detail:
            return "returned_none"
        if "adapter failed" in detail:
            return "adapter_failed"
        return "out_sort_mismatch"
    if check == "nonfinite":
        return "undocumented_nan_inf"
    if check == "refused":
        return "valueerror_on_probe"
    if check == "unbindable":
        return "builder_raised" if "builder raised" in detail else "no_hint"
    if check == "no_input":
        return "no_producer_value"
    return "other"


def debt_from(verdict):
    """``{check: {op: reason_category}}`` -- the committed shape."""
    out = {c: {} for c in CHECKS}
    for name, v in sorted(verdict.items()):
        if v["status"] == "fail":
            for c in v["check"]:
                out[c][name] = category(c, v["detail"])
    return out


def known_category(check, cat):
    """Is *cat* one of the reason categories of *check*?"""
    if check == "raises":
        return isinstance(cat, str) and cat.startswith("raw_") and len(cat) > 4
    return cat in CATEGORIES.get(check, ())


def new_violations(verdict, debt):
    """``[(check, op, detail)]`` for failures the debt ledger does not list."""
    out = []
    for name, v in sorted(verdict.items()):
        if v["status"] != "fail":
            continue
        for c in v["check"]:
            if name not in debt.get(c, {}):
                out.append((c, name, v["detail"]))
    return out


def stale_debt(verdict, debt):
    """``[(check, op, now)]`` for debt rows that no longer fail that check.

    A ``skip`` (backend missing here) is NOT a pass: the row stays, so the ledger is the
    same in every environment. A row for an op that left the ledger tier is stale.
    """
    out = []
    for c in CHECKS:
        for name in sorted(debt.get(c, {})):
            v = verdict.get(name)
            if v is None:
                out.append((c, name, "not in the ledger tier any more"))
            elif v["status"] == "skip":
                continue
            elif v["status"] == "ok" or c not in v["check"]:
                out.append((c, name, "%s %s" % (v["status"], v.get("check") or "")))
    return out


def executed(verdict):
    """Ops that returned a value (judged on finite / sort / determinism)."""
    reach = {"refused", "no_input", "unbindable", "raises"}
    return sorted(n for n, v in verdict.items() if "sec" in v
                  and not (v["status"] == "fail" and set(v["check"]) & reach))


def summary(verdict):
    debt = debt_from(verdict)
    status = {s: sum(1 for v in verdict.values() if v["status"] == s)
              for s in ("ok", "fail", "skip")}
    lines = ["ledger ops %d  %s" % (len(verdict), status)]
    for c in CHECKS:
        cats = {}
        for cat in debt[c].values():
            cats[cat] = cats.get(cat, 0) + 1
        lines.append("  %-17s %4d  %s" % (c, len(debt[c]), dict(sorted(cats.items()))))
    return "\n".join(lines)


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Contract probe for every typed-ledger op.")
    p.add_argument("--write", action="store_true",
                   help="rewrite docs/LEDGER_CONTRACT_DEBT.json (only to shrink it)")
    p.add_argument("--json", help="dump every verdict (with details) to this path")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    verdict = run(verbose=a.verbose)
    print(summary(verdict))
    print("(%.1f s)" % (time.perf_counter() - t0))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(verdict, f, ensure_ascii=False, indent=1, default=str)
    if a.write:
        write_debt(verdict)
    return 0


def write_debt(verdict):
    debt = debt_from(verdict)
    doc = {"_note": "型付き台帳の全 op に対する契約違反の既存分(tests/test_ledger_contracts.py の"
                    "ラチェット)。増えたら落ち、直って通るようになっても落ちる(= 縮むしかない)。"
                    "op 名 -> 理由の区分。詳細は py -3.11 tools/ledger_contracts.py -v で見る。",
           "_written": time.strftime("%Y-%m-%d"),
           "counts": {c: len(debt[c]) for c in CHECKS},
           "debt": debt}
    with open(DEBT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    sys.exit(main())
