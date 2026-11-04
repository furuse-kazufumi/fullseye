"""Regression gates for the adversarial review of the entry contract (contract, 2026-11-05).

The question behind most items is the same: one input, many doors. ``fullseye.apply`` refuses a
NaN frame, converts uint8 by /255 (recorded, or refused under strict) and checks knobs; the other
doors (``run_pipeline`` / ``FullseyeEngine.run`` / ``run_cached`` / ``fullseye.Image`` /
``fullseye.Pipeline`` / MCP ``fullseye_apply`` / MCP ``fullseye_pipeline``) must give the same
answer for the same input. The table test sends one input through all eight doors and compares
each with ``apply`` (the oracle is ``apply`` on the float /255 frame, not the door itself).
"""
from __future__ import annotations

import json
import math
import tracemalloc

import numpy as np
import pytest

import api
import backend_safe
import engine
import fssystem
import fullseye as fs
from studio_result import StageCache

pytestmark = pytest.mark.filterwarnings("ignore")

RNG = np.random.default_rng(20261105)
X = RNG.random((24, 24))


# --------------------------------------------------------------------------- #
# the eight doors                                                              #
# --------------------------------------------------------------------------- #
def _mcp():
    from fullseye.mcp import server as S
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    return S, Catalog.load(), HandleStore()


_MCP = {}


def _mcp_call(tool, x, op):
    if not _MCP:
        _MCP["S"], _MCP["cat"], _MCP["store"] = _mcp()
    S, cat, store = _MCP["S"], _MCP["cat"], _MCP["store"]
    env = fs.to_jsonable(x, "image")
    h = S.call_tool("fullseye_import_json", {"envelope": env}, cat, store)["structuredContent"]["handle"]
    args = {"handle": h, "op": op} if tool == "fullseye_apply" else {"handle": h, "stages": [{"op": op}]}
    try:
        r = S.call_tool(tool, args, cat, store)
    except Exception as e:                       # ArgError = refused before running
        raise ValueError(str(e)) from None
    if r.get("isError"):
        raise ValueError(r["content"][0]["text"])
    sc = r["structuredContent"]
    handle = sc.get("handle") or (sc.get("outputs") or [{}])[-1].get("handle")
    if handle is None:                           # pipeline: last stage record
        handle = [s for s in sc["stages"] if s.get("handle")][-1]["handle"]
    return np.asarray(store.get(handle)[1])


DOORS = {
    "apply": lambda x, op: fs.apply(x, op),
    "run_pipeline": lambda x, op: fs.run_pipeline(x, [op]),
    "engine.run": lambda x, op: fs.FullseyeEngine([op]).run(x),
    "engine.run_cached": lambda x, op: fs.FullseyeEngine([op]).run_cached(x, StageCache()),
    "unified.Image": lambda x, op: getattr(fs.Image(x), op)().value,
    "unified.Pipeline": lambda x, op: fs.Pipeline([op]).run(x),
    "mcp.apply": lambda x, op: _mcp_call("fullseye_apply", x, op),
    "mcp.pipeline": lambda x, op: _mcp_call("fullseye_pipeline", x, op),
}
STRICT_ONLY = {"mcp.apply", "mcp.pipeline"}        # MCP always runs fail-closed


def _outcome(fn, *args):
    try:
        return "ok", np.asarray(fn(*args), np.float64)
    except (ValueError, TypeError) as e:
        return "refused", str(e)


@pytest.mark.parametrize("door", sorted(DOORS))
def test_every_door_refuses_nan_and_strict_uint8_and_matches_apply(door):
    """C1 / C2 (+ the doors fixed earlier): same input, same verdict at every entry."""
    assert len(DOORS) == 8
    fn = DOORS[door]
    u8 = np.full((16, 16), 200, np.uint8)
    nan = X.copy()
    nan[5, 5] = np.nan
    # NaN: refused whatever the policy
    kind, _ = _outcome(fn, nan, "gaussian")
    assert kind == "refused", door
    # uint8 under strict: refused (the contract is float64 in [0, 1])
    with fs.strict_mode():
        kind, _ = _outcome(fn, u8, "gaussian")
    assert kind == "refused", door
    # in-contract float: the same numbers as apply
    kind, got = _outcome(fn, X, "gaussian")
    assert kind == "ok", (door, got)
    assert np.allclose(got, fs.apply(X, "gaussian"), atol=1e-12), door
    if door in STRICT_ONLY:
        return
    # uint8 under the default policy: converted /255 -- equal to apply on the float frame
    kind, got = _outcome(fn, u8, "gaussian")
    assert kind == "ok", door
    assert np.allclose(got, fs.apply(u8.astype(np.float64) / 255.0, "gaussian"), atol=1e-12), door
    assert got.dtype == np.float64


def test_c1_unified_knobs_and_sort_chain_follow_apply():
    """C1: knob type / non-finite / range and the sort chain, as apply and run_pipeline say."""
    with pytest.raises(ValueError, match="non-finite"):
        fs.Image(X).threshold(a=float("nan"))
    with pytest.raises(TypeError):
        fs.Image(X).threshold(a="0.3")
    with fs.strict_mode():
        with pytest.raises(ValueError, match="outside 0..1"):
            fs.Image(X).threshold(a=5.0)
    with pytest.raises(ValueError, match="type mismatch"):
        fs.run_pipeline(X, ["gaussian", "vol_gaussian"])
    with pytest.raises(ValueError, match="type mismatch"):
        fs.Pipeline(["gaussian", "vol_gaussian"]).run(X)
    # the uint8 conversion is recorded in the ledger by the unified doors too
    fs.clear_fallbacks()
    fs.Image(np.full((8, 8), 200, np.uint8)).gaussian()
    assert any(e["source"] == "input" for e in fs.fallbacks())
    # trace: one value per stage, the last one equal to run_pipeline
    out, vals = fs.Pipeline(["gaussian", "invert"]).run(X, trace=True)
    assert len(vals) == 3 and np.array_equal(out, fs.run_pipeline(X, ["gaussian", "invert"]))


# --------------------------------------------------------------------------- #
# C3 / C4 / C13  one reading of a stage                                         #
# --------------------------------------------------------------------------- #
BAD_STAGES = (
    {"op": "threshold", "A": 0.9},                 # typo'd knob key
    ("threshold", {"A": 0.9}),
    ("threshold", 0.9, 0.5, 0.1),                  # a 4th element
    ("threshold", {"a": "0.9"}),                   # str knob in the dict forms
    {"op": "threshold", "a": "0.9"},
    ("threshold", "0.9"),
    {"op": "threshold", "a": np.array([0.9])},
)


@pytest.mark.parametrize("stage", BAD_STAGES, ids=repr)
def test_c3_c4_engine_and_run_pipeline_refuse_the_same_stage(stage):
    with pytest.raises(TypeError):
        fs.run_pipeline(X, [stage])
    with pytest.raises(TypeError):
        fs.FullseyeEngine([stage])
    with pytest.raises(TypeError):
        engine.pipeline_states([stage], X)
    with pytest.raises(TypeError):
        fs.FullseyeEngine.from_dict({"stages": [stage]})


def test_c4_bool_knob_is_one_rule_in_every_form():
    ref = fs.apply(X, "threshold", True)               # apply: bool -> 1.0
    assert np.array_equal(ref, fs.apply(X, "threshold", 1.0))
    forms = (("threshold", True), {"op": "threshold", "a": True}, ("threshold", {"a": True}))
    assert len(forms) == 3
    for st in forms:
        assert np.array_equal(fs.run_pipeline(X, [st]), ref), st
        assert np.array_equal(fs.FullseyeEngine([st]).run(X), ref), st


def test_c13_pipeline_states_reads_the_five_forms_like_run_pipeline():
    forms = (("threshold", 0.9), ("threshold", {"a": 0.9}), {"op": "threshold", "a": 0.9},
             {"a": 0.9, "op": "threshold"}, ["threshold", 0.9, 0.5])
    assert len(forms) == 5
    for st in forms:
        rows = engine.pipeline_states([st], X)
        assert [(r["op"], r["a"], r["b"], r["ran"]) for r in rows] == [("threshold", 0.9, 0.5, True)], st


def test_c3_set_knobs_uses_the_same_type_rule():
    eng = fs.FullseyeEngine([("threshold", 0.5, 0.5)])
    with pytest.raises(TypeError):
        eng.set_knobs(0, a="0.9")
    eng.set_knobs(0, a=0.9)
    assert eng.get_knobs(0) == (0.9, 0.5)


# --------------------------------------------------------------------------- #
# C5  to_python cannot be made to run code                                      #
# --------------------------------------------------------------------------- #
def test_c5_to_python_refuses_unregistered_names_and_has_no_side_effect(tmp_path):
    import builtins
    evil = "gaussian\nimport builtins; builtins.FS_INJECTED_2026_11_05 = 1\n#"
    p = tmp_path / "edge.json"
    p.write_text(json.dumps({"fullseye_pipeline": 1, "name": "edge", "stages": [[evil, 0.5, 0.5]]}), encoding="utf-8")
    eng = fs.FullseyeEngine.load(str(p))
    for export in (eng.to_python, eng.to_python_staged):
        with pytest.raises(ValueError, match="not in the registry"):
            export()
    assert not hasattr(builtins, "FS_INJECTED_2026_11_05")
    # a sound pipeline: the --ops comment is one line, the script defines and runs the same pipeline
    ok = fs.FullseyeEngine([("gaussian", 0.3, 0.5), ("otsu", 0.5, 0.5)], name="edge")
    src = ok.to_python()
    assert src.splitlines()[1].startswith('# --ops "gaussian,otsu"')
    ns: dict = {}
    exec(compile(src, "exported.py", "exec"), ns)
    assert np.array_equal(ns["edge"](X), ok.run(X))


# --------------------------------------------------------------------------- #
# C6  run_cached = run, also on a warm cache                                    #
# --------------------------------------------------------------------------- #
def test_c6_template_is_part_of_the_cache_key():
    scene = RNG.random((64, 64))
    t_a, t_b = scene[10:20, 12:22].copy(), scene[40:50, 30:40].copy()
    eng = fs.FullseyeEngine([("ncc_locate", 0.5, 0.5)])
    cache = StageCache()
    try:
        fs.set_match_template(t_a)
        assert np.array_equal(eng.run_cached(scene, cache), eng.run(scene))
        fs.set_match_template(t_b)
        got = eng.run_cached(scene, cache)
        assert np.array_equal(got, eng.run(scene))
        assert (got[1], got[2]) == (45.0, 35.0)            # the centre of the true patch (40+5, 30+5)
    finally:
        fs.set_match_template(None)


def test_c6_warm_cache_keeps_entry_checks_and_ledger():
    u8 = np.full((16, 16), 200, np.uint8)
    eng = fs.FullseyeEngine([("gaussian", 0.5, 0.5)])
    cache = StageCache()
    eng.run_cached(u8, cache)
    fs.clear_fallbacks()
    eng.run_cached(u8, cache)                             # a hit
    assert [e["source"] for e in fs.fallbacks()] == ["input"]
    # strict + extra_checks: run refuses an out-of-range frame, so must a warm run_cached
    y = RNG.random((16, 16)) * 50
    c2 = StageCache()
    with fs.strict_mode():
        eng.run_cached(y, c2)
        with fssystem.system(extra_checks="on"):
            with pytest.raises(ValueError, match="contract"):
                eng.run(y)
            with pytest.raises(ValueError, match="contract"):
                eng.run_cached(y, c2)
    # a stage that degraded is recorded on every call, not only the first
    bad = fs.FullseyeEngine([("sk_area_opening", 0.5, 0.5)])
    z = np.full((2, 2), 0.5)
    fs.clear_fallbacks()
    bad.run(z)
    n_run = len(fs.fallbacks())
    c3 = StageCache()
    counts = []
    for _ in range(2):
        fs.clear_fallbacks()
        bad.run_cached(z, c3)
        counts.append(len(fs.fallbacks()))
    assert counts == [n_run, n_run]


# --------------------------------------------------------------------------- #
# C7  the template gets the image's entry contract                              #
# --------------------------------------------------------------------------- #
def test_c7_template_nonfinite_and_dtype():
    scene = RNG.random((64, 64))
    t = scene[40:50, 30:40].copy()
    tn = t.copy()
    tn[5, 5] = np.nan
    for pol in ("fallback", "raise"):
        with pytest.raises(ValueError, match="NaN"):
            fs.apply(scene, "ncc_locate", template=tn, on_error=pol)
    tu = np.round(t * 255).astype(np.uint8)
    with pytest.raises(ValueError, match="uint8"):
        fs.apply(scene, "ncc_locate", template=tu, on_error="raise")
    fs.clear_fallbacks()
    got = fs.apply(scene, "ncc_locate", template=tu)
    assert np.array_equal(got, fs.apply(scene, "ncc_locate", template=tu / 255.0))
    assert any(e["source"] == "input" for e in fs.fallbacks())
    assert fs.apply(scene, "ncc_locate", template=tn, allow_nonfinite=True) is not None


# --------------------------------------------------------------------------- #
# C9  validation_kit: only (H, W, 3/4) is a colour image                        #
# --------------------------------------------------------------------------- #
def test_c9_validation_kit_refuses_stacks(tmp_path):
    from fullseye import validation_kit as vk
    frame = np.zeros((40, 40))
    frame[5:13, 5:13] = 1.0
    np.save(tmp_path / "stack.npy", np.stack([frame] * 3))
    with pytest.raises(vk.KitError, match="colour"):
        vk._load_image(str(tmp_path / "stack.npy"))
    rgb = np.stack([frame, frame * 0.5, frame * 0.25], axis=2)
    np.save(tmp_path / "rgb.npy", rgb)
    assert np.allclose(vk._load_image(str(tmp_path / "rgb.npy")), rgb.mean(axis=2))
    rgba = np.concatenate([rgb, np.ones((40, 40, 1))], axis=2)
    np.save(tmp_path / "rgba.npy", rgba)
    assert np.array_equal(vk._load_image(str(tmp_path / "rgba.npy")), vk._load_image(str(tmp_path / "rgb.npy")))


# --------------------------------------------------------------------------- #
# C10  a declared shape is checked before it is allocated                       #
# --------------------------------------------------------------------------- #
def test_c10_mcp_rle_is_refused_before_allocation():
    S, cat, store = _mcp()
    side = 6000
    env = {"fullseye_sort": "region", "version": 1,
           "payload": {"encoding": "rle", "shape": [side, side], "runs": [side * side]}}
    tracemalloc.start()
    try:
        with pytest.raises(Exception, match="limit"):
            S.call_tool("fullseye_import_json", {"envelope": env}, cat, store)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 16 * 2 ** 20                           # was 576 MB for this 116-byte request
    with pytest.raises(ValueError, match="limit"):
        fs.from_jsonable(env, max_pixels=10 ** 6)
    with pytest.raises(ValueError, match="limit"):
        fs.from_json(json.dumps(env), max_bytes=10 ** 6)
    small = {"fullseye_sort": "region", "version": 1, "payload": {"encoding": "rle", "shape": [3, 4], "runs": [5, 7]}}
    m, _ = fs.from_jsonable(small, max_pixels=12, max_bytes=96)
    assert m.shape == (3, 4) and m.sum() == 7


def test_c10_declared_shape_product_does_not_wrap():
    shape = [2 ** 62 + 1, 4]
    env = {"fullseye_sort": "matrix", "version": 1,
           "payload": {"encoding": "list", "shape": shape, "data": []}}
    assert int(np.prod(np.array(shape, np.int64))) == 4       # int64 wraps: the old reader wanted "4 values"
    with pytest.raises(ValueError, match=str(math.prod(shape))):
        fs.from_jsonable(env)


# --------------------------------------------------------------------------- #
# C11 / C12  n-ary apply: the same entry checks per input                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [np.zeros((0, 0)), RNG.random(16), RNG.random((2, 3, 4, 5))],
                         ids=["empty", "1-D", "4-D"])
def test_c11_nary_inputs_are_guarded_like_single_input(bad):
    with pytest.raises(ValueError):
        fs.apply(bad, "invert", on_error="raise")
    with pytest.raises(ValueError):
        fs.apply([bad, bad], "add_image", on_error="raise")


def test_c11_nary_extra_checks_range_and_c12_image_unwrap():
    big = RNG.random((8, 8)) * 50
    with fssystem.system(extra_checks="on"):
        with pytest.raises(ValueError, match="contract"):
            fs.apply([big, big], "add_image", on_error="raise")
    y = RNG.random((24, 24))
    assert np.array_equal(fs.apply([fs.Image(X), fs.Image(y)], "add_image"), fs.apply([X, y], "add_image"))
    nan_img = X.copy()
    nan_img[0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        fs.apply([fs.Image(nan_img), fs.Image(y)], "add_image")


# --------------------------------------------------------------------------- #
# probes on the suspected items that turned out real / hardened                 #
# --------------------------------------------------------------------------- #
def test_mcp_apply_does_not_wipe_the_callers_ledger():
    S, cat, store = _mcp()
    h = S.call_tool("fullseye_import_json", {"envelope": fs.to_jsonable(X, "image")}, cat, store)["structuredContent"]["handle"]
    fs.clear_fallbacks()
    fs.apply(np.full((8, 8), 200, np.uint8), "gaussian")
    before = len(fs.fallbacks())
    assert before == 1
    r = S.call_tool("fullseye_apply", {"handle": h, "op": "gaussian"}, cat, store)
    assert len(fs.fallbacks()) == before
    assert r["structuredContent"]["degraded"] == []


def test_mcp_never_writes_a_nan_token():
    import io
    from fullseye.mcp import server as S
    buf = io.BytesIO()
    S.write_message(buf, {"jsonrpc": "2.0", "id": 7, "result": {"x": float("nan")}})
    body = buf.getvalue().split(b"\r\n\r\n", 1)[1]

    def _refuse(tok):
        raise AssertionError("non-finite token %s" % tok)
    msg = json.loads(body, parse_constant=_refuse)
    assert msg["id"] == 7 and msg["error"]["code"] == -32603
    store = _mcp()[2]
    assert S._pipeline_json_value({"v": float("nan")}, store, sort="feature", provenance=[]) is None
    assert S._pipeline_json_value({"v": 1.5}, store, sort="feature", provenance=[]) == {"v": 1.5}


# --------------------------------------------------------------------------- #
# C1 sibling: the imgevolve CLI apply / pipeline use the apply entry            #
# --------------------------------------------------------------------------- #
def _cli(monkeypatch, argv):
    import contextlib
    import io
    import sys
    import imgevolve
    monkeypatch.setattr(sys, "argv", ["fullseye"] + list(argv))
    with contextlib.redirect_stdout(io.StringIO()):
        return imgevolve.main()


def test_c1_cli_apply_and_pipeline_check_knobs_and_sort_chain(monkeypatch, tmp_path):
    cv2 = pytest.importorskip("cv2")
    src = str(tmp_path / "in.png")
    img = np.round(X * 255).astype(np.uint8)
    cv2.imwrite(src, img)
    out = str(tmp_path / "out.png")
    for knob in ("5", "nan"):
        with pytest.raises(ValueError):
            _cli(monkeypatch, ["apply", "threshold", src, out, "--a", knob])
        with pytest.raises(ValueError):
            _cli(monkeypatch, ["pipeline", src, out, "--ops", "gaussian,threshold", "--a", knob])
    with pytest.raises(ValueError, match="type mismatch"):
        _cli(monkeypatch, ["pipeline", src, out, "--ops", "gaussian,vol_gaussian"])
    # a sound call: the written file equals fullseye.apply on the same /255 frame
    assert _cli(monkeypatch, ["apply", "gaussian", src, out, "--a", "0.3"]) == 0
    ref = np.clip(fs.apply(img / 255.0, "gaussian", 0.3) * 255, 0, 255).astype(np.uint8)
    assert np.array_equal(cv2.imread(out, cv2.IMREAD_GRAYSCALE), ref)
    assert _cli(monkeypatch, ["pipeline", src, out, "--ops", "gaussian,invert", "--a", "0.3"]) == 0
    ref = np.clip(fs.run_pipeline(img / 255.0, ["gaussian", "invert"], a=0.3) * 255, 0, 255).astype(np.uint8)
    assert np.array_equal(cv2.imread(out, cv2.IMREAD_GRAYSCALE), ref)


# --------------------------------------------------------------------------- #
# C4 / C5 siblings: FullseyeGraph                                               #
# --------------------------------------------------------------------------- #
def test_graph_knob_type_rule_and_to_python_refuses_an_invalid_graph():
    import graphengine as G
    with pytest.raises(TypeError):
        G.FullseyeGraph.from_dict({"nodes": [{"id": "n", "op": "gaussian", "inputs": ["$in"], "a": "0.3"}]})
    bad = ({"nodes": [{"id": "n", "op": "no_such_op_xyz", "inputs": ["$in"]}]},
           {"nodes": [{"id": "n", "op": "gaussian", "inputs": ["$in"], "a": float("nan")}]})
    assert len(bad) == 2
    for d in bad:
        with pytest.raises(ValueError, match="refusing"):
            G.FullseyeGraph.from_dict(d).to_python()
    g = G.FullseyeGraph("g").add("blur", "gaussian", ["$in"], a=0.123456789)
    ns: dict = {}
    exec(compile(g.to_python(), "g.py", "exec"), ns)
    assert np.array_equal(ns["g"](**{"$in": X})["blur"], g.run(X, terminal="blur"))
    assert np.array_equal(g.run(X, terminal="blur"), fs.apply(X, "gaussian", 0.123456789))


# --------------------------------------------------------------------------- #
# round 2 (state): T1 / T8 run_cached, T3 / T4 MCP system params, T5 fssystem  #
# --------------------------------------------------------------------------- #
def test_t1_run_cached_hands_out_a_copy():
    cache = StageCache()
    eng = fs.FullseyeEngine(["gaussian", "invert"])
    ref = eng.run(X)
    out = eng.run_cached(X, cache)
    out[:] = 0.0                                          # the caller reuses the buffer
    again = fs.FullseyeEngine(["gaussian", "invert"]).run_cached(X, cache)
    assert again is not out and np.array_equal(again, ref)


def test_t8_run_cached_accepts_contour_inputs_and_keys_them_by_content():
    import op_probe
    c = op_probe.sample_input("contour")
    eng = fs.FullseyeEngine([("length_xld", 0.5, 0.5)])
    cache = StageCache()
    assert eng.run_cached(c, cache) == eng.run(c)
    shifted = {"shape": c["shape"], "cs": [np.asarray(p, np.float64) * 2.0 for p in c["cs"]]}
    assert eng.run_cached(shifted, cache) == eng.run(shifted) != eng.run(c)
    reordered = {"cs": c["cs"], "shape": c["shape"]}
    assert engine._input_hash(reordered) == engine._input_hash(c)
    with pytest.raises(TypeError):
        engine._input_hash(np.array([object()], dtype=object))


def test_t3_validate_tool_uses_pipeline_max_stages_like_the_pipeline_tool():
    S, cat, store = _mcp()
    h = S.call_tool("fullseye_import_json", {"envelope": fs.to_jsonable(X, "image")}, cat, store)["structuredContent"]["handle"]
    stages = [{"op": "gaussian"} for _ in range(40)]
    with fssystem.system(pipeline_max_stages=16):
        v = S.call_tool("fullseye_validate_pipeline", {"stages": stages, "start_sort": "image"}, cat, store)
        assert v["isError"] and v["structuredContent"]["valid"] is False
        assert [e["reason"] for e in v["structuredContent"]["errors"]][:1] == ["too_many_stages"]
        with pytest.raises(Exception, match="too_many_stages"):
            S.call_tool("fullseye_pipeline", {"handle": h, "stages": stages}, cat, store)
    v = S.call_tool("fullseye_validate_pipeline", {"stages": stages, "start_sort": "image"}, cat, store)
    assert not v["isError"]                               # default cap 64


def test_t4_response_budget_is_read_per_call():
    from fullseye.mcp import server as S
    big = {"x": "y" * 40000}
    with fssystem.system(mcp_response_budget=16000):
        tr = S.tool_result(json.dumps(big), big)
        assert "structuredContent" not in tr and tr["_meta"]["fullseye"]["limit"] == 16000
    assert "structuredContent" in S.tool_result(json.dumps(big), big)
