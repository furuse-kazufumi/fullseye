"""Codegen (beta) — the generated Python pipeline must reproduce the runtime
(ops.run_genome) EXACTLY, including feature/contour finals that must not be
clipped to [0,1] (the old bug clamped a blob count of 7 to 1.0)."""
import importlib.util
import json

import numpy as np

import codegen
import ops

_OPMAP = {o.name: o for o in ops.REGISTRY}


def _final_genome(want_sort, seed=0, tries=4000):
    rng = np.random.default_rng(seed)
    for _ in range(tries):
        g = rng.random(ops.GENOME_LEN)
        nz = [s for s in ops.decode(g) if s.op != "identity"]
        if nz and _OPMAP[nz[-1].op].out_sort == want_sort:
            return g
    return None


def _emit_and_load(g, tmp_path, name="t"):
    (tmp_path / f"champion_{name}.json").write_text(
        json.dumps({"genome": [float(v) for v in g], "pipeline": name}), encoding="utf-8")
    info = codegen.emit(name, tmp_path)
    spec = importlib.util.spec_from_file_location("gen_" + name, str(tmp_path / f"gen_{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return info, mod


def test_source_mirrors_runtime_conditional_clip(tmp_path):
    g = _final_genome("image")
    if g is None:
        g = np.full(ops.GENOME_LEN, 0.1)
    _emit_and_load(g, tmp_path)
    src = (tmp_path / "gen_t.py").read_text(encoding="utf-8")
    # the clip is runtime-conditional (2-D/3-D arrays only), matching ops._apply
    assert "isinstance(_v, np.ndarray) and _v.ndim in (2, 3)" in src


def test_feature_final_matches_runtime_and_is_not_clipped(tmp_path):
    g = _final_genome("feature")
    assert g is not None, "expected to find a feature-final genome"
    info, mod = _emit_and_load(g, tmp_path)
    assert info["final_out_sort"] == "feature"
    img = np.clip(np.random.default_rng(1).random((32, 32)), 0, 1)
    ref = ops.run_genome(np.asarray(g, np.float64), img)
    got = mod.pipeline(img.astype(np.float64))
    assert np.ndim(ref) == 0 and np.ndim(got) == 0        # scalar, NOT coerced to an image
    assert abs(float(ref) - float(got)) < 1e-9             # exact runtime reproduction


def test_image_final_matches_runtime(tmp_path):
    g = _final_genome("image")
    assert g is not None
    info, mod = _emit_and_load(g, tmp_path)
    assert info["final_out_sort"] == "image"
    img = np.clip(np.random.default_rng(2).random((32, 32)), 0, 1)
    ref = ops.run_genome(np.asarray(g, np.float64), img)
    got = mod.pipeline(img.astype(np.float64))
    assert np.allclose(ref, got, atol=1e-9)


# --------------------------------------------------------------------------- #
# C backend: the inter-stage clip of ops._apply must be emitted after every stage
# (2026-09-03 review F1: an unclipped unsharp fed raw values to the next C stage
# while codegen still reported c_fully_supported).
# --------------------------------------------------------------------------- #
def _t_for(sort, name):
    cands = ops._candidates(sort)
    return ([c.name for c in cands].index(name) + 0.5) / len(cands)


def genome_for(specs):
    """A genome whose decoded non-identity stages are exactly ``specs`` = [(op, a, b), ...]."""
    g, sort = [], ops.IMAGE
    for name, a, b in specs:
        g += [_t_for(sort, name), a, b]
        sort = ops._BY_NAME[name].out_sort
    while len(g) < 3 * ops.N_SLOTS:
        g += [_t_for(sort, "identity"), 0.5, 0.5]
    got = [s.op for s in ops.decode(g) if s.op != "identity"]
    assert got == [n for n, _, _ in specs], got
    return g


def test_c_backend_emits_clamp_after_every_image_stage(tmp_path):
    ga = 0.7 / 2.7                                            # gaussian sigma 1.0
    g = genome_for([("unsharp", 1.0, 0.0), ("gaussian", ga, 0.5), ("threshold", 0.5, 0.5)])
    info, _ = _emit_and_load(g, tmp_path)
    assert info["c_fully_supported"] is True
    body = [ln.strip() for ln in (tmp_path / "gen_t.c").read_text(encoding="utf-8").splitlines()
            if ln.startswith("    ") and "identity" not in ln]
    # every emitted op statement is immediately followed by the runtime's clip
    assert body == ["sharpen(buf, w, h, 1.500000f, 0.500000f);", "clamp01(buf, w, h);",
                    "gaussian(buf, w, h, 1.000000f);", "clamp01(buf, w, h);",
                    "threshold(buf, w, h, 0.500000f);", "clamp01(buf, w, h);"]


def test_c_backend_identity_stages_get_no_clamp(tmp_path):
    g = genome_for([("gaussian", 0.5, 0.5)])
    _emit_and_load(g, tmp_path)
    src = (tmp_path / "gen_t.c").read_text(encoding="utf-8")
    assert src.count("clamp01(buf, w, h);") == 1              # one real stage -> one clip
    assert src.count("/* identity */") == ops.N_SLOTS - 1
