# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""FullseyeEngine: インスタンスに対する load / from_ops / from_dict、dict 段、upto の範囲(GenSpark 第 16 報 N37/N39/N40/N41)。

``e = FullseyeEngine(); e.load(path)`` は classmethod が新しいエンジンを返して捨てられ、``e`` は空のまま
run が入力を返し describe が [] だった(第三者は「JSON を検証せず黙って結果を返す」と観測)。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import engine  # noqa: E402

IMG = np.random.default_rng(3).random((16, 16))


def test_load_on_an_instance_loads_into_it(tmp_path):
    p = str(tmp_path / "p.json")
    engine.FullseyeEngine.from_ops("gaussian,otsu").save(p)
    e = engine.FullseyeEngine()
    assert e.load(p) is e
    assert e.op_names() == ["gaussian", "otsu"] and len(e.describe()) == 2
    assert set(np.unique(e.run(IMG))) <= {0.0, 1.0}                 # 本当に走る
    e2 = engine.FullseyeEngine.load(p)                                # classmethod の呼び方も従来どおり
    assert e2.op_names() == ["gaussian", "otsu"]


def test_from_ops_and_from_dict_work_on_instances_and_from_ops_takes_a_list():
    e = engine.FullseyeEngine()
    assert e.from_ops(["gaussian", "otsu"]) is e and len(e) == 2
    e3 = engine.FullseyeEngine()
    assert e3.from_dict({"stages": [["gaussian", 0.3, 0.5]]}) is e3 and e3.stages == [["gaussian", 0.3, 0.5]]
    assert engine.FullseyeEngine.from_ops("gaussian, otsu").op_names() == ["gaussian", "otsu"]


def test_dict_stages_are_understood_and_bad_stage_types_are_refused():
    e = engine.FullseyeEngine([{"op": "gaussian", "a": 0.3}, "otsu", ("sobel_amp", 0.2, 0.7)])
    assert e.stages == [["gaussian", 0.3, 0.5], ["otsu", 0.5, 0.5], ["sobel_amp", 0.2, 0.7]]
    with pytest.raises(ValueError, match="stage 0"):
        engine.FullseyeEngine([{"sigma": 2}])                        # 以前は "{'sigma': 2}" という op 名になっていた
    with pytest.raises(ValueError, match="stage 1"):
        engine.FullseyeEngine(["gaussian", 42])
    with pytest.raises(ValueError, match="stage 0"):
        engine.FullseyeEngine([""])


def test_unknown_op_in_a_loaded_pipeline_is_reported_by_validate_and_raises_on_run(tmp_path):
    import json
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"fullseye_pipeline": 1, "name": "p", "stages": ["gaussian", "no_such_op_xyz"]}), encoding="utf-8")
    e = engine.FullseyeEngine()
    e.load(str(p))
    errs = [pr for pr in e.validate() if pr["severity"] == "error"]
    assert errs and "no_such_op_xyz" in errs[0]["message"]
    with pytest.raises(KeyError):
        e.run(IMG)


def test_upto_is_an_inclusive_stage_index_and_out_of_range_is_refused():
    e = engine.FullseyeEngine.from_ops("gaussian,sobel_amp,otsu")
    first = e.run(IMG, upto=0)
    assert first.shape == IMG.shape and not np.array_equal(first, IMG)   # 段 0 だけ走る(入力そのままではない)
    assert np.array_equal(e.run(IMG, upto=2), e.run(IMG))
    for bad in (3, 9, -1):
        with pytest.raises(ValueError, match="upto"):
            e.run(IMG, upto=bad)


def test_to_python_carries_the_ops_string_and_a_coding_line():
    src = engine.FullseyeEngine.from_ops("gaussian,otsu").to_python()
    lines = src.splitlines()
    assert lines[0] == "# -*- coding: utf-8 -*-" and '# --ops "gaussian,otsu"' in lines[1]
    compile(src, "<generated>", "exec")
