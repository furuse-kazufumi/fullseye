# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""0.2.1 の仕上げ(GenSpark 第 28〜35 報、2026-09-20): PFM の既定は float(N120)、from_dict の stages=None(N107)、
device=cuda が無い環境の 1 文(N117)、apply に台帳名を渡したときの案内(N124)、accel の判定語に閾値(N116)、
README 冒頭の件数が索引と一致(N103)。
"""
from __future__ import annotations

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

import accel  # noqa: E402
import api  # noqa: E402
import engine  # noqa: E402
import fullseye as fs  # noqa: E402

X = np.random.default_rng(0).random((24, 24))


def test_pfm_default_write_is_float_and_round_trips(tmp_path):
    cv2 = pytest.importorskip("cv2")
    p = str(tmp_path / "d.pfm")
    fs.write_image(p, X)                                            # depth 未指定
    raw = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    assert raw.dtype == np.float32 and raw.max() <= 1.0 + 1e-6      # 0..255 を float に書いていない
    assert np.abs(fs.read_image(p) - X).max() < 1e-6
    assert np.abs(fs.read_image(p) - X).max() < 1e-6                # 上下順も含めて一致


def test_from_dict_refuses_none_and_scalar_stages_but_keeps_the_documented_forms():
    for bad in (None, 3, True):
        with pytest.raises(ValueError, match="must be a list"):
            engine.FullseyeEngine.from_dict({"stages": bad})
    assert engine.FullseyeEngine.from_dict({"stages": []}).stages == []            # 0 段は文書どおり恒等
    assert engine.FullseyeEngine.from_dict({"stages": "gaussian,otsu"}).op_names() == ["gaussian", "otsu"]
    with pytest.raises(ValueError, match="missing 'stages'"):
        engine.FullseyeEngine.from_dict({})


def test_device_cuda_without_a_gpu_is_explained_and_recorded(monkeypatch):
    torch = pytest.importorskip("torch")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    api.reset_gpu() if hasattr(api, "reset_gpu") else api._GPU_OPEN.clear()
    with pytest.raises(RuntimeError, match=r"device='cuda' requested but CUDA is not available here"):
        fs.apply(X, "gaussian", device="cuda", on_error="raise")
    api._GPU_OPEN.clear()
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fs.apply(X, "gaussian", device="cuda")
    assert out.shape == X.shape
    gpu = [e for e in fs.fallbacks() if e["name"] == "gaussian" and e.get("source") == "gpu"]
    assert gpu and "CUDA is not available here" in gpu[0]["error"] and "ran on the CPU" in gpu[0]["error"]
    api._GPU_OPEN.clear()


def test_apply_with_a_ledger_op_name_points_to_op_run():
    with pytest.raises(KeyError, match=r"typed-ledger operator.*op_run\('color_lut'"):
        fs.apply(X, "color_lut")
    with pytest.raises(KeyError, match="unknown operator"):
        fs.apply(X, "no_such_op_xyz")


def test_accel_parity_label_carries_its_threshold():
    assert accel.parity_flag(0.0) == "match(<0.005)" and accel.parity_flag(0.0002) == "match(<0.005)"
    assert accel.parity_flag(0.01).startswith("close(<") and accel.parity_flag(0.5).startswith("differ(>=")
    assert "exact" not in accel.parity_flag(0.0)


def test_readme_intro_counts_match_the_shipped_index():
    idx = json.load(open(os.path.join(ROOT, "docs", "OP_INDEX.json"), encoding="utf-8"))
    md = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    m = re.search(r"\((\d[\d,]*)\s*\n?operators in the machine-readable index", md)
    assert m, "README.md の冒頭に「N operators in the machine-readable index」が無い"
    assert int(m.group(1).replace(",", "")) == idx["n_ops"], "README.md 冒頭の op 数が索引(%d)と違う" % idx["n_ops"]
    t = idx["tiers"]
    assert "{:,} in the typed ledgers".format(t["ledger"]) in md
    assert "{:,} single-input 2-D operators".format(t["registry"] + t.get("color", 0)) in md
    assert md.count("{:,} operators in the machine-readable index".format(idx["n_ops"])) >= 1


def _cli(monkeypatch, argv):
    import io as _io
    from contextlib import redirect_stdout
    import imgevolve
    monkeypatch.setattr(sys, "argv", ["fullseye"] + list(argv))
    buf = _io.StringIO()
    with redirect_stdout(buf):
        rc = imgevolve.main()
    return rc, buf.getvalue()


def test_has_knows_the_ledger_and_algorithm_tiers(monkeypatch):
    rc, out = _cli(monkeypatch, ["has", "color_lut"])
    assert rc == 0 and "typed ledger" in out and "op_run('color_lut'" in out
    rc, out = _cli(monkeypatch, ["has", "gaussian"])
    assert rc == 0 and "tier=registry" in out
    try:
        import algo
        aname = algo.algo_names()[0]
    except Exception:
        aname = None
    if aname:
        rc, out = _cli(monkeypatch, ["has", aname])
        assert rc == 0 and "general-algorithm tier" in out and "algo run" in out
    rc, out = _cli(monkeypatch, ["has", "no_such_op_xyz"])
    assert rc == 1 and "unknown op" in out


def test_ops_search_folds_case_and_accents(monkeypatch):
    _, a = _cli(monkeypatch, ["ops", "--search", "otsu"])
    _, b = _cli(monkeypatch, ["ops", "--search", "ÖTSU"])
    assert a.splitlines()[-1] == b.splitlines()[-1] and "0 ops match" not in a


def test_pipeline_with_an_empty_ops_string_is_refused_with_a_sentence(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match="at least one op"):
        _cli(monkeypatch, ["pipeline", str(tmp_path / "a.png"), str(tmp_path / "o.png"), "--ops", ""])
