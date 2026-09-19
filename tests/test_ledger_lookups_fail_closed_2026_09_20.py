# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""台帳の引き方は fail-closed(GenSpark 第 15・16 報、2026-09-20): producers / consumers の未知 sort(N68)、
presets の未知 op(N69)、write_wav の path と Wave_write の後始末(N71)、入口の関門の可視性(N67)、
退化入力の契約が方針ごとに一様であること(N72 / N73)。
"""
from __future__ import annotations

import os
import subprocess
import sys
import warnings

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import dsp  # noqa: E402
import fullseye as fs  # noqa: E402
import opassist as A  # noqa: E402
import ops  # noqa: E402


def test_producers_and_consumers_refuse_unknown_sorts_and_op_names():
    assert "normalmap" in A.known_sorts() and fs.op_sorts() == A.known_sorts()
    assert A.producers("normalmap") and A.consumers("normalmap")
    for fn in (A.producers, A.consumers):
        with pytest.raises(ValueError, match="unknown sort"):
            fn("no_such_sort")
        with pytest.raises(ValueError, match="op name, not a sort"):
            fn("gaussian")                                   # registry op
        with pytest.raises(ValueError, match="op name, not a sort"):
            fn("grating_rgb")                                # ledger op
    # 既知の型で産む op が無いのは正当な空(型が無いのとは別の答え)
    assert all(isinstance(A.producers(s), list) for s in A.known_sorts()[:5])


def test_presets_refuse_unknown_ops_and_are_empty_for_known_ops_without_presets():
    with pytest.raises(ValueError, match="not in any ledger"):
        A.presets("no_such_op_xyz")
    with pytest.raises(ValueError, match="not in any ledger"):
        fs.op_presets("gaussian")                            # registry op は台帳の外
    assert A.presets("read_wav") == {}
    assert A.presets("grating_rgb")                          # 実在の規格値の表


def test_write_wav_path_is_not_a_data_input_in_the_ledger():
    spec = {p["name"]: p for p in A.param_spec("write_wav")}
    assert spec["path"]["kind"] != "data" and spec["path"]["required"] is True
    assert spec["x"]["kind"] == "data" and spec["x"]["sort"] == "signal"
    rspec = {p["name"]: p for p in A.param_spec("read_wav")}
    assert rspec["path"]["kind"] == "data" and rspec["path"]["sort"] == "file"   # 読む側の path はデータ
    args, kw = A.sample_input("write_wav")
    assert isinstance(args[0], np.ndarray) and "path" not in kw or kw.get("path") is None


def test_write_wav_refuses_a_non_path_before_touching_the_file(tmp_path):
    sig = np.linspace(-0.5, 0.5, 64)
    with pytest.raises(TypeError, match="second argument"):
        dsp.write_wav(sig, sig)
    with pytest.raises(TypeError, match="path is None"):
        dsp.write_wav(None, sig)
    with pytest.raises(TypeError, match="path is None"):
        dsp.read_wav(None)
    with pytest.raises(TypeError, match="path is None"):
        dsp.read_audio(None)
    with pytest.raises(TypeError, match="is None"):
        dsp._require_finite(None)
    p = tmp_path / "ok.wav"
    dsp.write_wav(p, sig)                                    # PathLike も通る
    x, rate = dsp.read_wav(str(p))
    assert x.shape == (64,) and rate == 44100 and abs(x - sig).max() < 1e-3


def test_no_ignored_exception_leaks_to_stderr_when_write_wav_is_misused():
    code = ("import sys; sys.path.insert(0, %r); import numpy as np, dsp, opassist as oa\n"
            "sig = np.zeros(8)\n"
            "for call in (lambda: dsp.write_wav(sig, sig), lambda: oa.op_run('write_wav'), lambda: dsp.read_wav(None)):\n"
            "    try: call()\n"
            "    except Exception as e: print(type(e).__name__)\n" % ROOT)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-500:]
    assert "Exception ignored" not in r.stderr and "Wave_write" not in r.stderr, r.stderr[-500:]
    assert r.stdout.split() == ["TypeError", "TypeError", "TypeError"], r.stdout


def test_list_ops_rows_expose_the_native_guard():
    by = {r["name"]: r for r in fs.list_ops()}
    for name, why in ops.NATIVE_CRASHES_ON_DEGENERATE.items():
        assert by[name]["native_guard"] == why and why
    assert {"cv_cc_count", "xsitk_minmax_curv_flow", "xsk3_h_minima", "xsk_random_walker"} <= set(ops.NATIVE_CRASHES_ON_DEGENERATE)
    assert by["gaussian"]["native_guard"] is None
    assert all("native_guard" in r for r in fs.list_ops() if r["tier"] == "registry")


@pytest.mark.parametrize("name", ["cv_cc_count", "xsitk_minmax_curv_flow", "xsk3_h_minima", "xsk_random_walker", "gaussian", "area_center"])
@pytest.mark.parametrize("shape", [(0, 0), (4, 0)])
def test_empty_input_contract_is_uniform_across_ops(name, shape):
    """N72 / N73: raise なら全 op が同じ 1 文、fallback なら全 op が台帳に記録して sort の既定値を返す。"""
    pytest.importorskip("cv2") if name.startswith("cv_") else None
    if name not in {o.name for o in ops.REGISTRY}:
        pytest.skip("backend for %s not installed" % name)
    with pytest.raises(ValueError, match=r"op '%s': empty input \(shape" % name):
        fs.apply(np.zeros(shape), name, on_error="raise")
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fs.apply(np.zeros(shape), name)
    assert out is not None
    assert any(e["name"] == name and "empty input" in e["error"] for e in fs.fallbacks())


def test_native_guards_still_refuse_non_finite_input_with_the_reason():
    for name in ("xsitk_minmax_curv_flow", "xsk_random_walker"):
        if name not in {o.name for o in ops.REGISTRY}:
            pytest.skip("backend for %s not installed" % name)
        x = np.random.default_rng(0).random((32, 32))
        x[3, 3] = np.nan
        with pytest.raises(ValueError, match="非有限"):
            fs.apply(x, name, on_error="raise")
