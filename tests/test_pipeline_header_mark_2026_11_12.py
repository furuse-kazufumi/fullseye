# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""パイプラインのファイルの版の印(``fullseye_pipeline``)の検査(2026-11-12)。

定義ファイルの読み書きの棚卸し(DEFS_IO_SURVEY §4-D)で、``fullseye_pipeline`` が 99 でも ``"banana"`` でも、別の種類
``fullseye_graph`` のファイルでも受理されると分かった。読み手(Engine の from_dict / load・CLI の run・Studio の検証と開く・
studio_lite)を**それぞれの入口から**試す。形式は変えない: 印の無い古いファイルは今までどおり読む。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import engine  # noqa: E402
import studio  # noqa: E402
from studio_lite import core as lite  # noqa: E402

_ST = [["gaussian", 0.5, 0.5]]
BAD = {
    "v99": {"fullseye_pipeline": 99, "stages": _ST},
    "banana": {"fullseye_pipeline": "banana", "stages": _ST},
    "float_1": {"fullseye_pipeline": 1.0, "stages": _ST},
    "bool_true": {"fullseye_pipeline": True, "stages": _ST},
    "none_value": {"fullseye_pipeline": None, "stages": _ST},
    "graph_file": {"fullseye_graph": 1, "name": "g", "nodes": []},
    "graph_with_stages": {"fullseye_graph": 1, "stages": _ST},
}
GOOD = {
    "current": {"fullseye_pipeline": 1, "name": "p", "stages": _ST},
    "legacy_no_mark": {"stages": _ST},
}


def _engine_from_dict(d, tmp_path):
    return engine.FullseyeEngine.from_dict(d)


def _engine_load(d, tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return engine.FullseyeEngine.load(str(p))


def _engine_instance_load(d, tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return engine.FullseyeEngine(["gaussian"]).load(str(p))


def _cli_run(d, tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "imgevolve.py"), "run", str(p), "--describe"], capture_output=True,
                       text=True, cwd=str(ROOT), env={**os.environ, "PYTHONUTF8": "1"}, timeout=180)
    if r.returncode != 0:
        raise ValueError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "rc=%d" % r.returncode)
    return r.stdout


def _studio_validate(d, tmp_path):
    return studio.validate_pipeline_dict(d)


def _studio_open(d, tmp_path):
    """Studio の「Open pipeline」が呼ぶ ``PipelineModel.load_dict``。"""
    return studio.PipelineModel().load_dict(d, recompute_pins=False)


def _studio_lite(d, tmp_path):
    return lite.load_recipe(json.dumps(d))


READERS = {"Engine.from_dict": _engine_from_dict, "Engine.load": _engine_load,
           "Engine.load(instance)": _engine_instance_load, "studio.validate_pipeline_dict": _studio_validate,
           "PipelineModel.load_dict": _studio_open, "studio_lite.load_recipe": _studio_lite}
_FAST = [k for k in READERS]


@pytest.mark.parametrize("reader", sorted(READERS))
@pytest.mark.parametrize("case", sorted(BAD))
def test_each_reader_refuses_a_bad_mark(reader, case, tmp_path):
    with pytest.raises(ValueError) as ei:
        READERS[reader](BAD[case], tmp_path)
    msg = str(ei.value)
    assert "expected" in msg and ("fullseye_pipeline" in msg), msg  # 何を期待したか
    if case == "graph_file" or case == "graph_with_stages":
        assert "fullseye_graph" in msg and "graph file" in msg, msg   # 何が来たか
    elif case == "banana":
        assert "'banana'" in msg and "str" in msg, msg
    elif case == "v99":
        assert "99" in msg, msg


@pytest.mark.parametrize("reader", sorted(READERS))
@pytest.mark.parametrize("case", sorted(GOOD))
def test_each_reader_still_reads_current_and_legacy_files(reader, case, tmp_path):
    out = READERS[reader](GOOD[case], tmp_path)
    if reader.startswith("Engine"):
        assert [s[0] for s in out.stages] == ["gaussian"]
    elif reader == "studio.validate_pipeline_dict":
        assert out == [["gaussian", 0.5, 0.5]]
    elif reader == "studio_lite.load_recipe":
        assert json.loads(out)["stages"] == [["gaussian", 0.5, 0.5]]


@pytest.mark.parametrize("case", ["v99", "banana", "graph_file"])
def test_cli_run_refuses_a_bad_mark_and_reads_a_good_one(case, tmp_path):
    with pytest.raises(ValueError, match="expected"):
        _cli_run(BAD[case], tmp_path)


def test_cli_run_reads_current_and_legacy_files(tmp_path):
    for d in GOOD.values():
        assert "gaussian" in _cli_run(d, tmp_path)


def test_engine_to_dict_and_studio_save_still_round_trip():
    """書き出す側(to_dict / Studio の to_dict)の印は 1 のまま、読み戻せる。"""
    eng = engine.FullseyeEngine(["gaussian", "otsu"])
    d = eng.to_dict()
    assert d["fullseye_pipeline"] == 1 and type(d["fullseye_pipeline"]) is int
    assert [s[0] for s in engine.FullseyeEngine.from_dict(d).stages] == ["gaussian", "otsu"]
    m = studio.PipelineModel()
    m.load_dict(d, recompute_pins=False)
    assert m.to_dict()["fullseye_pipeline"] == 1


def test_a_refused_open_leaves_the_current_pipeline_untouched():
    m = studio.PipelineModel()
    m.load_dict({"fullseye_pipeline": 1, "stages": [["gaussian", 0.3, 0.3]]}, recompute_pins=False)
    before = [list(s) for s in m.stages]
    with pytest.raises(ValueError):
        m.load_dict(BAD["v99"], recompute_pins=False)
    assert [list(s) for s in m.stages] == before


def test_pinned_snapshots_inside_a_file_are_not_mark_checked():
    """ピンの段は印の無い ``{"stages": ...}`` を ``validate_pipeline_dict`` に通す(内部の呼び方)。印の検査で壊れない。"""
    assert studio.validate_pipeline_dict({"stages": _ST}) == [["gaussian", 0.5, 0.5]]


def test_check_pipeline_header_unit():
    f = engine.check_pipeline_header
    assert f({"fullseye_pipeline": 1}) is None
    assert f({"stages": []}) is None
    assert f([1, 2]) is None            # dict でない入力は読み手が自分の言葉で断る
    assert f({"fullseye_pipeline": 1, "fullseye_kind": "anything"}) is None  # 別担当の封筒の鍵は見ない
    with pytest.raises(ValueError, match="got 2 .int."):
        f({"fullseye_pipeline": 2}, where="x")
    with pytest.raises(ValueError, match="^x: expected"):
        f({"fullseye_graph": 1}, where="x")
