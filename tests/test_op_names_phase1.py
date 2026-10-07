# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Canonical op names, phase 1 (opnames.py): aliases only, nothing renamed or removed.

What this file pins:

1. every canonical name reaches the SAME callable as its old name, in the door it was made for
   (registry -> api.find_op and the CLI, ledger -> fullseye.ledger and opassist, facade -> fullseye.<name>);
2. no canonical name collides with any name that already exists in any door;
3. old names still work exactly as before;
4. the alias tables are well formed (targets exist, no chains, RENAMED derived from the tables);
5. a ratchet: the set of names that mean different functions behind different doors does not grow,
   and shrinks only on purpose (remove the name from KNOWN_AMBIGUOUS in the same commit);
6. a lint for NEW names (American spelling, no one-word typed-ledger names) as a ratchet over today's names.

Why: 27 bare names meant different functions in different doors (fs.lowpass = 1-D Butterworth,
fs.op.lowpass = 2-D FFT). Mixing them never raises; it returns a plausible wrong answer.
"""
from __future__ import annotations

import importlib
import inspect
import json
import os
import re
import sys
import warnings

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api  # noqa: E402
import fullseye as fs  # noqa: E402
import opassist  # noqa: E402
import opnames  # noqa: E402
import ops  # noqa: E402
from conftest import requires_full_registry  # noqa: E402


# --------------------------------------------------------------------------- helpers
def _ident(f):
    """(module, qualname) of the innermost function, the identity used across doors."""
    try:
        u = inspect.unwrap(f)
    except Exception:  # noqa: BLE001 - a broken __wrapped__ chain: compare the object itself
        u = f
    mod = getattr(u, "__module__", None)
    qn = getattr(u, "__qualname__", None)
    if not mod or not qn:
        return ("id", str(id(u)))
    return (mod, qn)


_MODFUNC = re.compile(r"[A-Za-z_]\w*\.[A-Za-z_]\w*")


def _ledger_tables():
    out = {}
    for mod_name, table in opassist._LEDGERS:
        try:
            entries = getattr(importlib.import_module(mod_name), table, None)
        except Exception:  # noqa: BLE001 - optional-dependency ledger
            continue
        if isinstance(entries, dict):
            out[mod_name] = entries
    return out


def _tier_idents() -> dict:
    """name -> {door: {identity, ...}} over the four doors (registry mirrors in vision are skipped:
    ``fs.vision.<ns>.<registry op>`` is fs.apply under the same name, so it never disagrees)."""
    out: dict = {}

    def add(name, door, ident):
        out.setdefault(name, {}).setdefault(door, set()).add(ident)

    for o in ops.REGISTRY:
        add(o.name, "registry", _ident(o.fn))
    for _mod, entries in _ledger_tables().items():
        for n, e in entries.items():
            add(n, "ledger", _ident(e.get("func")))
    for n in fs.__all__:
        obj = getattr(fs, n, None)
        if callable(obj) and not inspect.isclass(obj) and not inspect.ismodule(obj):
            add(n, "facade", _ident(obj))
    reg = fs.vision._ensure()
    uops = reg._ops.items() if isinstance(reg._ops, dict) else ((u.name, u) for u in reg._ops)
    for n, op in uops:
        if op.provenance == "evolution":
            continue
        if isinstance(op.module, str) and _MODFUNC.fullmatch(op.module):
            add(n, "vision", tuple(op.module.split(".")))
        else:
            add(n, "vision", _ident(op.func))
    return out


def _all_canonicals() -> set:
    return (set(opnames.REGISTRY_ALIASES) | set(opnames.LEDGER_ALIASES)
            | set(opnames.FACADE_ALIASES) | set(opnames.VISION_ALIASES_PENDING))


def _old_names() -> set:
    return (set(opnames.REGISTRY_ALIASES.values())
            | {old for _m, old in opnames.LEDGER_ALIASES.values()}
            | set(opnames.FACADE_ALIASES.values())
            | {old for _ns, old in opnames.VISION_ALIASES_PENDING.values()})


# --------------------------------------------------------------------------- 1. resolution
@pytest.mark.parametrize("canon", sorted(opnames.REGISTRY_ALIASES))
def test_registry_canonical_reaches_the_same_op(canon):
    old = opnames.REGISTRY_ALIASES[canon]
    op_old = api.find_op(old)
    if op_old is None:
        pytest.skip("%s is not registered here (optional backend)" % old)
    assert api.find_op(canon) is op_old
    assert fs.find_op(canon) is op_old
    assert canon in fs.op and fs.op[canon] is not None
    # the CLI has its own resolver; it must agree
    import imgevolve
    assert imgevolve._find_op(ops, canon) is op_old


def test_registry_canonical_runs_end_to_end_like_the_old_name():
    img = np.random.default_rng(0).random((24, 28))
    for canon, old in (("image_fft_lowpass", "lowpass"), ("image_local_std", "local_std")):
        np.testing.assert_array_equal(fs.apply(img, canon, 0.3, 0.6), fs.apply(img, old, 0.3, 0.6))
        np.testing.assert_array_equal(fs.op[canon](img, a=0.3, b=0.6), fs.op[old](img, a=0.3, b=0.6))
    region = (img > 0.5).astype(float)
    np.testing.assert_array_equal(fs.apply(region, "region_fill_holes"), fs.apply(region, "fill_holes"))


def test_unknown_canonical_target_is_not_resolved_by_alias_text():
    # an alias resolves only to its own target; halcon / case folding still behave as before
    assert api.find_op("") is None and api.find_op("   ") is None
    assert api.find_op("IMAGE_FFT_LOWPASS") is api.find_op("lowpass")       # case folding reaches the alias
    assert api.find_op("image_fft_lowpass_x") is None


@pytest.mark.parametrize("canon", sorted(opnames.LEDGER_ALIASES))
def test_ledger_canonical_reaches_the_same_entry(canon):
    mod_name, old = opnames.LEDGER_ALIASES[canon]
    entries = _ledger_tables().get(mod_name)
    if entries is None:
        pytest.skip("ledger %s not importable here" % mod_name)
    assert old in entries, (canon, mod_name, old)
    entry = entries[old]
    assert canon in fs.ledger
    assert fs.ledger[canon].raw is entry["func"]
    got_mod, got_entry = opassist._ledger_entry(canon)
    assert got_mod == mod_name and got_entry is entry
    if opassist._ledger_entry(old)[0] == mod_name:            # the bare name reaches the same ledger
        assert opassist.presets(canon) == opassist.presets(old)
        assert ([s["name"] for s in opassist.param_spec(canon)]
                == [s["name"] for s in opassist.param_spec(old)])


def test_ledger_alias_pins_the_ledger_that_ledger_order_hides():
    # gaussians_to_voxel exists in ops3d AND opsreprconv; the bare name reaches ops3d only
    if "opsreprconv" not in _ledger_tables():
        pytest.skip("opsreprconv not importable here")
    import reprconv
    assert opassist._ledger_entry("gaussians_to_voxel")[0] == "ops3d"
    assert opassist._ledger_entry("gaussian_set_to_voxel")[0] == "opsreprconv"
    assert fs.ledger.gaussian_set_to_voxel.raw is reprconv.gaussians_to_voxel


def test_ledger_canonical_runs_end_to_end_like_the_old_name():
    t = np.linspace(0.0, 1.0, 400, endpoint=False)
    x = np.sin(2 * np.pi * 5 * t) + 0.3 * np.sin(2 * np.pi * 120 * t)
    a = fs.ledger.signal_lowpass(x, 400.0, 20.0)
    b = fs.ledger.lowpass(x, 400.0, 20.0)
    np.testing.assert_array_equal(np.asarray(a), np.asarray(b))
    r1, _n1 = fs.op_run("signal_lowpass", x, rate=400.0, cutoff=20.0)
    r0, _n0 = fs.op_run("lowpass", x, rate=400.0, cutoff=20.0)
    np.testing.assert_array_equal(np.asarray(r1), np.asarray(r0))
    info = fs.op_assist("signal_lowpass", measure=False)
    assert info["ledger"] == "ops1d" and info["params"] == fs.op_assist("lowpass", measure=False)["params"]


@pytest.mark.parametrize("canon", sorted(opnames.FACADE_ALIASES))
def test_facade_canonical_is_the_same_object(canon):
    old = opnames.FACADE_ALIASES[canon]
    assert hasattr(fs, old), old
    assert getattr(fs, canon) is getattr(fs, old)
    assert canon in fs.__all__


def test_facade_wrapper_alias_points_at_the_wrapped_function():
    # fs.mesh_to_points is a documented thin wrapper of mesh.sample_surface; its canonical is the
    # canonical of the wrapped function, and the two give the same samples.
    import mesh
    assert fs.mesh_sample_surface is mesh.sample_surface
    V = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    F = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    np.testing.assert_array_equal(fs.mesh_to_points(V, F, 50, seed=3), fs.mesh_sample_surface(V, F, 50, seed=3))
    assert opnames.RENAMED["mesh_to_points"]["facade"] == "mesh_sample_surface"


def test_facade_canonicals_are_bound_statically_and_listed_once():
    # fullseye/__init__.py binds them in a literal block (IDEs and static analysis see them);
    # the block must agree with the table both ways.
    src = open(os.path.join(ROOT, "fullseye", "__init__.py"), encoding="utf-8").read()
    bound = dict(re.findall(r"^(\w+) = (\w+)  # opnames$", src, re.M))
    assert bound == opnames.FACADE_ALIASES
    assert len(fs.__all__) == len(set(fs.__all__))


# --------------------------------------------------------------------------- 2. no collisions
def test_no_canonical_collides_with_an_existing_name():
    tiers = _tier_idents()
    reg = fs.vision._ensure()
    vision_names = set(reg._ops) if isinstance(reg._ops, dict) else {u.name for u in reg._ops}
    vision_names |= set(getattr(reg, "_ns", {}) or {})
    halcon = {o.halcon for o in ops.REGISTRY if o.halcon}
    idx = json.load(open(os.path.join(ROOT, "fullseye", "data", "OP_INDEX.json"), encoding="utf-8"))
    indexed = {o["name"] for o in idx["ops"]}
    # every door except the facade (the facade legitimately holds the canonical names bound by this phase)
    taken = {n for n, d in tiers.items() if set(d) - {"facade"}}
    taken |= vision_names | halcon | indexed | set(api._ALIAS_CANONICAL) | _old_names()
    bad = sorted(_all_canonicals() & taken)
    assert not bad, "canonical names collide with existing names: %s" % bad
    # facade side: a canonical present in the facade must be exactly the callable the table names.
    # (A ledger canonical may already be a facade name for the very same callable: signal_quantize.)
    for canon in sorted(_all_canonicals()):
        if not hasattr(fs, canon):
            continue
        obj = getattr(fs, canon)
        if canon in opnames.FACADE_ALIASES:
            assert obj is getattr(fs, opnames.FACADE_ALIASES[canon]), canon
        elif canon in opnames.LEDGER_ALIASES:
            mod_name, old = opnames.LEDGER_ALIASES[canon]
            entries = _ledger_tables().get(mod_name)
            if entries is not None:
                assert _ident(obj) == _ident(entries[old]["func"]), canon
        else:
            pytest.fail("canonical %r already exists in the facade as something else" % canon)


def test_canonicals_are_not_ambiguous_themselves():
    tiers = _tier_idents()
    amb = sorted(c for c in _all_canonicals()
                 if c in tiers and len({i for s in tiers[c].values() for i in s}) > 1)
    assert not amb, amb


# --------------------------------------------------------------------------- 3. old names still work
def test_old_names_still_resolve_in_every_door():
    for canon, old in opnames.REGISTRY_ALIASES.items():
        o = api.find_op(old)
        if o is not None:
            assert o.name == old
    for canon, (mod_name, old) in opnames.LEDGER_ALIASES.items():
        if mod_name in _ledger_tables():
            assert old in fs.ledger
    for canon, old in opnames.FACADE_ALIASES.items():
        assert callable(getattr(fs, old)) and old in fs.__all__
    # the bare ambiguous names keep their old meaning per door
    assert fs.lowpass.__module__ == "dsp"
    if api.find_op("lowpass") is not None:
        assert api.find_op("lowpass").name == "lowpass"


def test_registry_is_not_extended_by_aliases():
    names = [o.name for o in ops.REGISTRY]
    assert not (set(opnames.REGISTRY_ALIASES) & set(names))
    assert len(fs.op) == len(ops.REGISTRY) and set(dir(fs.op)) == set(names)


def test_ledger_listing_is_unchanged_by_aliases():
    names = set()
    for entries in _ledger_tables().values():
        names |= set(entries)
    assert set(dir(fs.ledger)) == names
    assert not (set(opnames.LEDGER_ALIASES) & names)


# --------------------------------------------------------------------------- 4. table integrity
def test_alias_tables_have_no_chains_and_no_self_aliases():
    canon = _all_canonicals()
    old = _old_names()
    assert not (canon & old), sorted(canon & old)
    for c, o in opnames.REGISTRY_ALIASES.items():
        assert c != o and o not in opnames.REGISTRY_ALIASES
    for c, (_m, o) in opnames.LEDGER_ALIASES.items():
        assert c != o and o not in opnames.LEDGER_ALIASES
    for c, o in opnames.FACADE_ALIASES.items():
        assert c != o and o not in opnames.FACADE_ALIASES
    ledger_modules = {m for m, _t in opassist._LEDGERS}
    assert {m for m, _o in opnames.LEDGER_ALIASES.values()} <= ledger_modules


def test_registry_alias_targets_exist_in_a_full_registry():
    requires_full_registry()
    names = {o.name for o in ops.REGISTRY}
    missing = sorted(o for o in opnames.REGISTRY_ALIASES.values() if o not in names)
    assert not missing, missing


def test_renamed_is_derived_from_the_tables():
    derived: dict = {}
    for c, o in opnames.REGISTRY_ALIASES.items():
        derived.setdefault(o, {})["registry"] = c
    for c, (m, o) in opnames.LEDGER_ALIASES.items():
        derived.setdefault(o, {})["ledger:" + m] = c
    for c, o in opnames.FACADE_ALIASES.items():
        derived.setdefault(o, {})["facade"] = c
    for c, (_ns, o) in opnames.VISION_ALIASES_PENDING.items():
        derived.setdefault(o, {})["vision"] = c
    renamed = {k: dict(v) for k, v in opnames.RENAMED.items()}
    # the one documented wrapper (mesh_to_points -> canonical of the function it wraps)
    wrapper = renamed.pop("mesh_to_points")
    assert wrapper.pop("facade") == "mesh_sample_surface"
    if wrapper:
        renamed["mesh_to_points"] = wrapper
    assert renamed == derived


def test_vision_pending_targets_exist():
    reg = fs.vision._ensure()
    for c, (ns, old) in opnames.VISION_ALIASES_PENDING.items():
        assert old in reg._ns.get(ns, {}), (c, ns, old)


def test_ambiguous_names_are_the_ratchet_list():
    assert set(opnames.AMBIGUOUS_NAMES) == set(KNOWN_AMBIGUOUS)


def test_ledger_warning_is_opt_in(monkeypatch):
    monkeypatch.delenv("FULLSEYE_WARN_AMBIGUOUS_NAMES", raising=False)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fs.ledger.lowpass                                     # noqa: B018 - default: silent
        fs.ledger.signal_lowpass                              # noqa: B018
    monkeypatch.setenv("FULLSEYE_WARN_AMBIGUOUS_NAMES", "1")
    with pytest.warns(FutureWarning, match="signal_lowpass"):
        fs.ledger.lowpass                                     # noqa: B018
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fs.ledger.signal_lowpass                              # noqa: B018 - canonical never warns
        fs.ledger.efd_normalize                               # noqa: B018
    monkeypatch.setenv("FULLSEYE_WARN_AMBIGUOUS_NAMES", "0")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fs.ledger.lowpass                                     # noqa: B018


# --------------------------------------------------------------------------- 5. ambiguity ratchet
#: Names that mean different functions behind different doors (2026-10-07 measurement, identity =
#: module.qualname of the innermost function). Each has canonical names in opnames.py. Remove a
#: name here in the same commit that makes it unambiguous (phase 2); never add one.
KNOWN_AMBIGUOUS = frozenset({
    "bit_not", "companding_mu_law", "cooc_feature_matrix", "depth_to_points", "distance_point_line",
    "estimate_normals", "farthest_point_sampling", "fill_holes", "flow_magnitude", "gaussians_to_voxel",
    "highpass", "inertia_tensor", "lidar_scan", "local_std", "lowpass", "mesh_to_points",
    "normals_from_depth", "overlay_mask", "photometric_stereo", "project_points", "recover_pose",
    "region_growing", "reprojection_error", "sample_surface", "surface_normals", "trace_rays",
    "triangulate",
})


def _ambiguous_now() -> set:
    return {n for n, t in _tier_idents().items() if len({i for s in t.values() for i in s}) > 1}


def test_same_name_different_function_does_not_grow():
    new = sorted(_ambiguous_now() - KNOWN_AMBIGUOUS)
    assert not new, (
        "new names mean different functions behind different doors: %s\n"
        "  pick a name with a dimension/object prefix (signal_ / image_ / mesh_ / points_ / depth_ / vol_)"
        " instead of reusing a name another door already has." % new)


def test_same_name_different_function_shrinks_only_on_purpose():
    requires_full_registry()
    stale = sorted(KNOWN_AMBIGUOUS - _ambiguous_now())
    assert not stale, ("no longer ambiguous: %s - remove from KNOWN_AMBIGUOUS (and opnames.AMBIGUOUS_NAMES)"
                       " in the same commit" % stale)


def test_every_ambiguous_name_has_a_canonical_for_every_non_halcon_side():
    covered = set(opnames.RENAMED)
    assert KNOWN_AMBIGUOUS <= covered, sorted(KNOWN_AMBIGUOUS - covered)


# --------------------------------------------------------------------------- 6. lint for new names
_BRITISH = re.compile(
    r"(^|_)(colour\w*|centre\w*|centred|neighbour\w*|grey\w*|labell\w*|modell\w*|fibre\w*|metre\w*|"
    r"behaviour\w*|analyse\w*|catalogue\w*|artefact\w*|"
    r"(normali|optimi|quanti|visuali|initiali|organi|summari|minimi|maximi|regulari|characteri|recogni|"
    r"synthesi|parameteri|vectori|binari|discreti|randomi|seriali|equali|stabili|polari|standardi|"
    r"generali|locali|special|utili|customi|categori|emphasi|digiti|rasteri|tokeni|lineari)"
    r"s(e|ed|es|ing|ation|ations|er))(_|$)")   # suffix required: "synthesis" / "emphasis" are American too

#: British spellings in today's names (all five have American canonical names in opnames.py).
KNOWN_BRITISH = frozenset({
    "cplx_domain_colour", "glyph_normalise", "hole_centre_from_rgbd", "neighbour_index_gaps",
    "profile_normalise",
})

#: One-word typed-ledger names today. Well-known terms (psnr, ssim, stft, erf ...) stay; the vague ones
#: have canonical names in opnames.py. New ledger ops must not add to this list.
KNOWN_ONE_WORD_LEDGER = frozenset({
    "aabb", "antialias", "arc", "arrow", "bandpass", "bessel", "blend", "bloom", "bounce", "canny3d",
    "carve", "cepstrum", "coherence", "crosshair", "cutout", "deflicker", "describe", "dither", "ellipse",
    "envelope", "erf", "erfc", "esdf", "fscore", "fsim", "fsimc", "fuse", "gicp", "glass", "gmsd",
    "gradient3d", "hessian3d", "highpass", "icosphere", "inflate", "integrate", "invariants", "iqft2",
    "istft", "jitter", "koschmieder", "lowpass", "morph", "mse", "mtf50", "ncd", "normalize", "obb",
    "perlin2", "premultiply", "project", "psnr", "qft2", "quantize", "quickshift", "reconstruct",
    "reflect", "refract", "reproject", "resample", "rms", "rmse", "sellmeier", "sinkhorn", "sobel3d",
    "spectrogram", "spectrum", "ssim", "stft", "ticks", "triangulate", "unpremultiply", "viewport",
    "vifp", "vignette", "wetness",
})


def _all_names() -> set:
    names = set(_tier_idents())
    names |= {o.halcon for o in ops.REGISTRY if o.halcon}
    return names


def test_lint_catches_what_it_claims():
    # the regex must fire on the known British names and stay quiet on American / unrelated words
    assert all(_BRITISH.search(n) for n in KNOWN_BRITISH)
    for ok in ("glyph_normalize", "cplx_domain_color", "analysis_table", "characteristic_curve",
               "specular_highlight", "grayscale_closing", "neighbor_index_gaps", "synthesis_filter",
               "emphasis_map", "specialty_glass"):
        assert not _BRITISH.search(ok), ok


def test_no_new_british_spelling():
    new = sorted(n for n in _all_names() if _BRITISH.search(n) and n not in KNOWN_BRITISH)
    assert not new, "use American spelling for new names: %s" % new


def test_no_new_one_word_ledger_name():
    ledger = set()
    for entries in _ledger_tables().values():
        ledger |= set(entries)
    new = sorted(n for n in ledger if "_" not in n and n not in KNOWN_ONE_WORD_LEDGER)
    assert not new, ("one-word typed-ledger names say too little - use <family>_<object>_<action>: %s" % new)


def test_known_lint_lists_shrink_only_on_purpose():
    requires_full_registry()
    names = _all_names()
    ledger = set()
    for entries in _ledger_tables().values():
        ledger |= set(entries)
    assert not (KNOWN_BRITISH - names), sorted(KNOWN_BRITISH - names)
    assert not (KNOWN_ONE_WORD_LEDGER - ledger), sorted(KNOWN_ONE_WORD_LEDGER - ledger)


def test_canonical_names_follow_the_guideline():
    bad = []
    for c in _all_canonicals():
        if not re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)+", c):
            bad.append((c, "needs >= 2 lowercase tokens"))
        if _BRITISH.search(c):
            bad.append((c, "British spelling"))
    assert not bad, bad
