# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""GenSpark 第 55 報(0.2.1 の再測定、2026-09-20): strict_mode() が全経路で効く(N199)/ op_run の引数順と registry op の
案内(N200)/ `python -m fullseye`(N150)/ CLI index が同梱索引との差を理由つきで言い、wheel の中に書かない(N198 / N115)。
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import warnings
from contextlib import redirect_stdout

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api  # noqa: E402
import backend_safe as bs  # noqa: E402
import fullseye as fs  # noqa: E402
import imgevolve  # noqa: E402

GRAY = np.random.default_rng(0).random((32, 32))


def test_strict_mode_makes_every_guard_raise():
    fs.clear_fallbacks()
    with fs.strict_mode():
        with pytest.raises(ValueError, match="expects a color"):
            fs.apply(GRAY, "access_channel")                      # 入力型の門(以前は台帳に記録して素通り)
        with pytest.raises(ValueError, match="expects a image"):
            fs.apply(np.linspace(0, 1, 40), "sobel_amp")
        assert api._policy(None) == "raise" and api._policy("fallback") == "fallback"   # 明示は文脈より強い
    assert api._policy(None) == "fallback"                        # 文脈を抜けたら既定に戻る
    assert not [e for e in fs.fallbacks() if e["source"] == "input"]
    prev = bs.set_strict(True)
    try:
        assert api._policy(None) == "raise"
    finally:
        bs.set_strict(prev)


def test_op_run_explains_the_argument_order_and_registry_ops():
    with pytest.raises(TypeError, match=r"first argument is the op name.*op_run\(name, <input>"):
        fs.op_run(GRAY, "gaussian")
    with pytest.raises(ValueError, match=r"not in any ledger.*registry op.*fullseye\.apply\(img, 'gaussian'\)"):
        fs.op_run("gaussian", GRAY)
    with pytest.raises(ValueError, match=r"unknown op 'no_such_op_xyz' \(not in any ledger\)$"):
        fs.op_run("no_such_op_xyz")


def test_python_dash_m_fullseye_is_the_cli():
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run([sys.executable, "-m", "fullseye", "--version"], capture_output=True, text=True,
                       encoding="utf-8", env=env, cwd=ROOT, timeout=120)
    assert r.returncode == 0 and r.stdout.strip() == "fullseye %s" % fs.__version__, (r.returncode, r.stdout, r.stderr[-200:])
    r = subprocess.run([sys.executable, "-m", "fullseye", "--help"], capture_output=True, text=True,
                       encoding="utf-8", env=env, cwd=ROOT, timeout=120)
    assert r.returncode == 0 and "usage:" in r.stdout and "index" in r.stdout


def test_index_names_the_difference_from_the_shipped_copy(monkeypatch, tmp_path):
    out = tmp_path / "idx.json"
    monkeypatch.setattr(sys, "argv", ["fullseye", "index", "--out", str(out)])
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = imgevolve.main()
    text = buf.getvalue()
    assert rc == 0 and out.exists()
    n = json.loads(out.read_text(encoding="utf-8"))["n_ops"]
    assert "[index] %d ops" % n in text
    assert ("matches the shipped index" in text) or ("missing here" in text and "[index]   missing:" in text), text


def test_index_default_output_never_lands_inside_an_installed_package(monkeypatch, tmp_path):
    assert imgevolve._index_default_out() == os.path.join(imgevolve.HERE, "docs", "OP_INDEX.json")
    monkeypatch.setattr(imgevolve, "HERE", str(tmp_path))          # docs/ の無い場所 = wheel の site-packages
    (tmp_path / "work").mkdir()
    monkeypatch.chdir(tmp_path / "work")
    assert imgevolve._index_default_out() == os.path.join(os.getcwd(), "OP_INDEX.json")
    assert not imgevolve._index_default_out().startswith(str(tmp_path) + os.sep + "docs")


def test_unified_pipeline_points_knob_tuples_to_run_pipeline():
    with pytest.raises(TypeError, match="run_pipeline"):
        fs.Pipeline([("gaussian", 0.5, 0.5)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert fs.run_pipeline(GRAY, [("gaussian", 0.5, 0.5)]).shape == GRAY.shape
