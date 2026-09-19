# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""n-ary の一覧(op_names(include_nary=))、list_ops の knobs 欄、CLI apply --input2、index の 4 段表示
(GenSpark 第 18〜20 報の統合チケット N60 / I1、2026-09-20)。

n-ary op は呼べるのに ``op_names()`` に無く、``a`` / ``b`` が効くかは op ノートの文にしか無かった。
CLI からは 2 入力の op を呼ぶ手段が無かった。
"""
from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api  # noqa: E402
import fullseye as fs  # noqa: E402
import imgevolve  # noqa: E402
import ops  # noqa: E402


def _nary_names() -> set[str]:
    return {o.name for o in api._nary_by_name().values()}


def test_op_names_default_is_the_one_input_registry_unchanged():
    names = fs.op_names()
    assert names == sorted(o.name for o in ops.REGISTRY)
    assert not (set(names) & _nary_names())                       # 既定に nary は混ざらない(索引の門 931 の定義)


def test_op_names_include_nary_adds_exactly_the_nary_tier():
    names, both = fs.op_names(), fs.op_names(include_nary=True)
    assert both == sorted(both) and len(both) == len(set(both))
    assert set(both) - set(names) == _nary_names() and _nary_names()
    assert "add_image" in both and "add_image" not in names
    assert {r["name"] for r in fs.list_ops() if r["tier"] == "nary"} == _nary_names()   # list_ops と同じ集合


def test_every_list_ops_row_carries_a_knobs_summary():
    rows = fs.list_ops()
    assert rows and all("knobs" in r for r in rows)
    measured = [r for r in rows if r["knobs"] is not None]
    docs = json.load(open(os.path.join(ROOT, "docs", "op_knob.json"), encoding="utf-8"))
    determined = {r["op"] for r in docs if r.get("status") == "determined"}
    assert {r["name"] for r in measured} == determined & {r["name"] for r in rows}
    assert len(measured) > 400                                   # 中身の量を別に数える(一致の門は空を通す)
    for r in measured:
        k = r["knobs"]
        assert set(k) == {"a", "b", "breakpoints"} and k["a"] in ("continuous", "discrete", "unused")
        assert isinstance(k["b"], bool) and all(isinstance(x, float) for x in k["breakpoints"])
    by = {r["name"]: r["knobs"] for r in rows}
    assert by["add_noise_distribution"] == {"a": "continuous", "b": True, "breakpoints": []}
    assert by["abs_image"]["a"] == "unused" and by["abs_image"]["b"] is False
    unmeasured = [n for n, k in by.items() if k is None]
    assert unmeasured                                            # 未計測は None であって「効かない」ではない
    assert fs.knob_summary("abs_image") == by["abs_image"] and fs.knob_summary("no_such_op_xyz") is None


def test_the_shipped_knob_table_equals_the_docs_copy():
    import fullseye.mcp.catalog as C
    pkg = json.load(open(os.path.join(ROOT, "fullseye", "data", C.PKG_KNOBS), encoding="utf-8"))
    doc = json.load(open(os.path.join(ROOT, "docs", "op_knob.json"), encoding="utf-8"))
    assert pkg == doc, "fullseye/data/op_knob.json が docs/op_knob.json と違う —— `py -3.11 tools/gen_mcp_data.py`"
    assert isinstance(pkg, list) and len(pkg) > 400
    toml = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    assert '"data/op_knob.json"' in toml                          # wheel に載る(門は配布物側から)


def _run_cli(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["fullseye"] + list(argv))
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = imgevolve.main()
    return rc, buf.getvalue()


@pytest.fixture
def two_images(tmp_path):
    cv2 = pytest.importorskip("cv2")
    rng = np.random.default_rng(7)
    a, b = rng.random((24, 24)), rng.random((24, 24)) * 0.5
    pa, pb = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    cv2.imwrite(pa, (a * 255).astype(np.uint8))
    cv2.imwrite(pb, (b * 255).astype(np.uint8))
    return pa, pb, str(tmp_path / "out.png")


def test_cli_apply_input2_runs_an_nary_op(monkeypatch, two_images):
    import cv2
    pa, pb, out = two_images
    rc, text = _run_cli(monkeypatch, ["apply", "add_image", pa, out, "--input2", pb])
    assert rc == 0 and "applied add_image" in text and os.path.exists(out)
    got = cv2.imread(out, cv2.IMREAD_GRAYSCALE)
    xa = cv2.imread(pa, cv2.IMREAD_GRAYSCALE).astype(np.float64) / 255.0
    xb = cv2.imread(pb, cv2.IMREAD_GRAYSCALE).astype(np.float64) / 255.0
    want = np.clip(np.asarray(fs.apply([xa, xb], "add_image", on_error="raise")) * 255, 0, 255).astype(np.uint8)
    assert got.shape == want.shape and np.abs(got.astype(int) - want.astype(int)).max() <= 1


def test_cli_apply_nary_without_input2_says_what_to_pass(monkeypatch, two_images):
    pa, _pb, out = two_images
    with pytest.raises(SystemExit) as ei:
        _run_cli(monkeypatch, ["apply", "add_image", pa, out])
    msg = str(ei.value)
    assert "--input2" in msg and "add_image" in msg and "2 inputs" in msg


def test_cli_apply_unary_with_input2_is_refused(monkeypatch, two_images):
    pa, pb, out = two_images
    with pytest.raises(SystemExit) as ei:
        _run_cli(monkeypatch, ["apply", "gaussian", pa, out, "--input2", pb])
    assert "one input" in str(ei.value) and "--input2" in str(ei.value)
    assert not os.path.exists(out)


def test_cli_index_prints_the_four_tiers(monkeypatch, tmp_path):
    fake = {"n_ops": 4, "tiers": {"color": 1, "ledger": 1, "nary": 1, "registry": 1},
            "ops": [{"name": "w", "tier": "registry"}, {"name": "x", "tier": "nary"},
                    {"name": "y", "tier": "ledger"}, {"name": "z", "tier": "color"}]}
    monkeypatch.setattr(imgevolve, "_build_op_index", lambda: fake)
    out = str(tmp_path / "idx.json")
    rc, text = _run_cli(monkeypatch, ["index", "--out", out])
    assert rc == 0
    line = [ln for ln in text.splitlines() if ln.startswith("[index]")][0]
    assert "4 ops (registry 1 / nary 1 / ledger 1 / color 1)" in line     # 4 段を名前つきで、この順に
    assert json.load(open(out, encoding="utf-8"))["tiers"] == fake["tiers"]
