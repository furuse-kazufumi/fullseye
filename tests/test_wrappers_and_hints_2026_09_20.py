# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""0.2.2 第 4 陣(2026-09-20): Image の器を剥がす(N188 / N171)、台帳 op の入力不足は 1 文(N122)、`algo run` の --seq 無しを
拒む(N187)、`op_find` の doc をノートで埋める(N119 / N162)、`FullseyeGraph.add` の既定入力(N167 / N180)。"""
from __future__ import annotations

import io
import os
import sys
import warnings
from contextlib import redirect_stdout

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fullseye as fs  # noqa: E402
import graphengine  # noqa: E402
import imgevolve  # noqa: E402

IMG = np.random.default_rng(0).random((32, 32))
RGB = np.random.default_rng(1).random((16, 16, 3))


def test_apply_and_run_pipeline_and_to_json_unwrap_the_image_wrapper():
    ref = fs.apply(IMG, "gaussian")
    assert np.allclose(fs.apply(fs.Image(IMG), "gaussian"), ref)
    assert np.allclose(fs.run_pipeline(fs.Image(IMG), ["gaussian"]), ref)
    assert fs.to_json(fs.Image(IMG), "image") == fs.to_json(IMG, "image")
    with pytest.raises(TypeError, match="at least one dimension"):
        fs.apply(object(), "gaussian")                                  # 器でない物は今までどおり止まる


def test_op_run_names_the_missing_input_instead_of_a_raw_type_error():
    with pytest.raises(ValueError, match=r"missing input\(s\) top \(rgb\).*op_run\('blend_mode', <rgb>, <rgb>\)"):
        fs.op_run("blend_mode", RGB)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out, _ = fs.op_run("blend_mode", RGB, RGB)                     # 揃えば走る
    assert np.asarray(out).shape == RGB.shape


def _cli(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["fullseye"] + list(argv))
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = imgevolve.main()
    return rc, buf.getvalue()


def test_algo_run_without_seq_is_refused_with_the_example(monkeypatch):
    with pytest.raises(SystemExit, match=r"run needs --seq.*algo run quicksort --seq 3,1,2"):
        _cli(monkeypatch, ["algo", "run", "quicksort"])
    rc, out = _cli(monkeypatch, ["algo", "run", "quicksort", "--seq", "3,1,2"])
    assert rc == 0 and "1.0" in out and "3.0" in out


def test_op_find_doc_is_filled_from_the_op_note():
    hits = fs.op_find("gaussian")
    top = hits[0]
    assert top["op"] == "gaussian" and top["doc"], top
    empty = [h["op"] for h in fs.op_find("gauss") if h.get("call") == "apply" and not h["doc"]]   # registry 側だけ(台帳の doc は別件 N89)
    assert not empty, "doc が空の op: %s" % empty[:5]
    assert top["match"] == "exact"
    assert all(h["match"] == "doc" for h in fs.op_find("equidistant")), "説明文だけの当たりは doc と名乗る"
    assert {h["match"] for h in hits} <= {"exact", "name", "stem", "doc"}


def test_graph_add_defaults_to_the_external_input_and_empty_graph_is_identity():
    g = graphengine.FullseyeGraph()
    assert set(g.run(IMG)) == {"$in"}                                  # 空グラフ = 何も走らず入力だけ
    g.add("n1", "gaussian")                                            # inputs 省略 = "$in"
    out = g.run(IMG)
    assert set(out) == {"$in", "n1"} and np.allclose(out["n1"], fs.apply(IMG, "gaussian"))
    with pytest.raises(ValueError, match="no inputs"):
        graphengine.FullseyeGraph().add("n1", "gaussian", [])
