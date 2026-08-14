"""Ground-truth tests for the DAG pipeline runtime (graphengine.py).

A DAG's output is checked against the same ops composed by hand, so branching and
merging are verified exactly, not just for non-crashing."""
import numpy as np
import pytest

import graphengine
import fullseye as fs
import imgops_nary

_NARY = {o.name: o for o in imgops_nary.build_nary()}


def _img(seed=0):
    from scipy import ndimage
    return np.clip(ndimage.gaussian_filter(np.random.default_rng(seed).random((40, 48)), 1.0), 0, 1)


def test_diamond_branch_and_merge():
    img = _img()
    g = graphengine.FullseyeGraph("diamond")
    g.add("blur", "gaussian", ["$in"], a=0.6)
    g.add("resid", "abs_diff_image", ["$in", "blur"])   # merge: raw vs blurred
    out = g.run(img)
    # hand-compute
    blur = fs.RT["gaussian"](img, 0.6, 0.5)
    resid = _NARY["abs_diff_image"].fn([img, blur], 0.5, 0.5)
    assert np.allclose(out["blur"], blur)
    assert np.allclose(out["resid"], resid)
    assert np.allclose(g.run(img, terminal="resid"), resid)


def test_two_external_inputs():
    a, b = _img(1), _img(2)
    g = graphengine.FullseyeGraph()
    g.add("sum", "add_image", ["left", "right"])
    out = g.run({"left": a, "right": b}, terminal="sum")
    assert np.allclose(out, _NARY["add_image"].fn([a, b], 0.5, 0.5))


def test_missing_input_raises():
    g = graphengine.FullseyeGraph()
    g.add("sum", "add_image", ["left", "right"])
    with pytest.raises(ValueError):
        g.run({"left": _img()})            # 'right' missing


def test_cycle_detected():
    g = graphengine.FullseyeGraph()
    g.add("a", "gaussian", ["b"])
    g.add("b", "gaussian", ["a"])          # a<->b cycle
    with pytest.raises(ValueError):
        g.topological_order()


def test_validate_flags_bad_ops():
    g = graphengine.FullseyeGraph()
    g.add("x", "not_a_real_op", ["$in"])
    g.add("y", "add_image", ["$in"])       # n-ary given 1 input
    probs = g.validate()
    msgs = " ".join(p["msg"] for p in probs)
    assert "unknown op" in msgs and "needs 2 inputs" in msgs


def test_topological_order_linear_chain():
    g = graphengine.FullseyeGraph()
    g.add("c", "gaussian", ["b"])
    g.add("b", "gaussian", ["a"])
    g.add("a", "gaussian", ["$in"])
    order = g.topological_order()
    assert order.index("a") < order.index("b") < order.index("c")


def test_roundtrip_dict_and_run_matches():
    img = _img(3)
    g = graphengine.FullseyeGraph("rt")
    g.add("blur", "gaussian", ["$in"], a=0.4)
    g.add("edge", "sobel_amp", ["blur"])
    g2 = graphengine.FullseyeGraph.from_dict(g.to_dict())
    assert np.allclose(g.run(img, terminal="edge"), g2.run(img, terminal="edge"))


def test_to_python_runs():
    img = _img(4)
    g = graphengine.FullseyeGraph("gtest")
    g.add("blur", "gaussian", ["$in"], a=0.5)
    g.add("resid", "abs_diff_image", ["$in", "blur"])
    code = g.to_python()
    ns = {}
    exec(code, ns)                          # noqa: S102 - generated code smoke test
    v = ns["gtest"](**{"$in": img})
    assert np.allclose(v["resid"], g.run(img, terminal="resid"))
