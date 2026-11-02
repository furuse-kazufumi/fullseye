# -*- coding: utf-8 -*-
"""The mechanical GPU path: scoring rules, the allow-list and the shadow itself.

GPU の無い CI では判定規則と許可リストの門だけが走り、GPU の検査は skip する。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import gpu_auto_report as R  # noqa: E402
import gpu_auto_sweep as S  # noqa: E402
import gpu_shadow as G  # noqa: E402

ALLOW = json.loads((ROOT / "fullseye" / "data" / "gpu_auto_allow.json").read_text("utf-8"))


def _gpu():
    if os.environ.get("FULLSEYE_NO_GPU_TESTS"):
        return False
    lock = os.environ.get("FULLSEYE_GPU_LOCK")
    if lock and Path(lock).exists():
        return False
    return G.available()


needs_gpu = pytest.mark.skipif(not _gpu(), reason="CuPy / CUDA not available here")


# ---- the comparison must not pass on nothing ------------------------------------ #
def test_compare_catches_a_small_interior_difference():
    a = np.linspace(0, 1, 64 * 64).reshape(64, 64)
    b = a.copy()
    b[30, 30] += 0.02
    r = S.compare(a, b, np)
    assert not r["ok"] and r["rel"] > 0.01


def test_compare_ignores_the_border_only():
    a = np.linspace(0, 1, 64 * 64).reshape(64, 64)
    b = a.copy()
    b[0, 0] += 0.5
    assert S.compare(a, b, np)["ok"]
    b[10, 10] += 0.5
    assert not S.compare(a, b, np)["ok"]


def test_compare_reports_a_constant_output_as_not_informative():
    a = np.full((64, 64), 0.25)
    r = S.compare(a, a.copy(), np)
    assert r["ok"] and not r["nonconst"]


def test_compare_refuses_a_different_nan_mask():
    a = np.ones((8, 8))
    a[0, 0] = 2.0
    b = a.copy()
    b[3, 3] = np.nan
    r = S.compare(a, b, np)
    assert not r["ok"] and "nan-mask" in r["why"]


def test_compare_is_scale_free():
    """振れ幅 1e-3 の出力で 1e-4 の差は 10 % の差。絶対値で見ると素通りする。"""
    a = 1e-3 * np.linspace(0, 1, 20)
    b = a + 1e-4
    assert not S.compare(a, b, np)["ok"]


def test_compare_refuses_structure_changes():
    assert not S.compare({"a": 1.0}, {"b": 1.0}, np)["ok"]
    assert not S.compare([1.0, 2.0], [1.0], np)["ok"]
    assert not S.compare(np.ones(4), np.ones(5), np)["ok"]


# ---- classification: the order of the verdicts is the policy -------------------- #
def _cls(c, p=None, s=None):
    return R.classify(c, p, s, S.is_python_loop, S.MIN_RATIO)


OK = {"status": "ok", "lines": 30, "elems": 1024, "lines2": 30, "elems2": 4096}


def test_adopted_needs_parity_ratio_and_a_varying_output():
    p = {"status": "match"}
    s = {"status": "measured", "ratio": 6.0, "nonconst": True}
    assert _cls(OK, p, s)[0] == "adopted"
    assert _cls(OK, p, dict(s, ratio=4.99))[0] == "match_slow"
    assert _cls(OK, p, dict(s, nonconst=False))[0] == "match_slow"


def test_a_python_loop_is_never_adopted_whatever_the_ratio():
    c = dict(OK, lines=1000, lines2=4000)
    p = {"status": "match"}
    s = {"status": "measured", "ratio": 50.0, "nonconst": True}
    assert _cls(c, p, s)[0] == "python_loop"


def test_python_loop_rule_uses_the_growth_not_the_size():
    assert S.is_python_loop({"lines": 100, "elems": 1000, "lines2": 400, "elems2": 4000})
    assert not S.is_python_loop({"lines": 5000, "elems": 1000, "lines2": 5000, "elems2": 4000})
    assert S.is_python_loop({"lines": 600, "elems": 1000})      # 固定形: 1 回の比で見る
    assert not S.is_python_loop({"lines": 100, "elems": 1000})


def test_wrappers_and_exceptions_are_separated():
    assert _cls(dict(OK, libs={"cv2": 3}), {"status": "gpu_exception", "reason": "type_error"}) \
        == ("wrapper", "cv2")
    assert _cls(OK, {"status": "gpu_exception", "reason": "wrapper_skimage"}) \
        == ("wrapper", "skimage")
    assert _cls(OK, {"status": "gpu_exception", "reason": "numpy_cupy_mix"}) \
        == ("exception", "numpy_cupy_mix")


def test_unmeasured_is_never_counted_as_a_result():
    assert _cls(None)[0] == "unmeasured"
    assert _cls({"status": "no_probe"})[0] == "unmeasured"
    assert _cls(OK)[0] == "unmeasured"
    assert _cls(OK, {"status": "match"})[0] == "unmeasured"


def test_classify_exc_reads_cupy_messages():
    assert S.classify_exc(TypeError("Unsupported type <class 'numpy.ndarray'>")) == "numpy_cupy_mix"
    assert S.classify_exc(TypeError("Implicit conversion to a NumPy array is not allowed.")) \
        == "implicit_numpy"
    assert S.classify_exc(TypeError("Expected Ptr<cv::UMat> for argument 'src'")) == "wrapper_cv2"


# ---- allow-list ----------------------------------------------------------------- #
def test_allow_list_names_real_ops_at_or_over_the_gate():
    assert ALLOW["min_ratio"] >= 5.0
    idx = {r["name"] for r in json.loads((ROOT / "docs" / "OP_INDEX.json")
                                         .read_text("utf-8"))["ops"]}
    for name, row in ALLOW["ops"].items():
        assert name in idx, name
        assert row["ratio"] >= ALLOW["min_ratio"], name


def test_an_op_off_the_list_is_refused_not_run_on_the_cpu():
    with pytest.raises(G.GpuAutoError, match="allow-list"):
        G.run_allowed("no_such_op_on_the_list", np.zeros((4, 4)))


def test_the_default_path_never_imports_the_shadow():
    code = ("import sys, numpy as np, fullseye;"
            "fullseye.apply(np.zeros((8, 8)), 'gauss_filter', 0.5, 0.5);"
            "sys.exit(0 if 'gpu_shadow' not in sys.modules and 'cupy' not in sys.modules else 1)")
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    assert subprocess.run([sys.executable, "-c", code], env=env, timeout=120).returncode == 0


def test_seam_stays_on_the_plain_path_for_the_cpu_and_for_unlisted_ops():
    x = np.random.default_rng(0).random((32, 32))
    import fullseye
    want = fullseye.apply(x, "gauss_filter", 0.5, 0.5, device="cpu")
    assert np.array_equal(G.apply(x, "gauss_filter", 0.5, 0.5, device="cpu"), want)


# ---- the shadow itself (needs a device) ------------------------------------------ #
@needs_gpu
def test_shadow_leaves_the_real_modules_alone():
    import ops
    sh = G.get_shadow()
    m = sh.load("ops")
    assert ops.np is np
    assert m.np is not np
    assert m.RT is not ops.RT


@needs_gpu
def test_allow_listed_ops_match_the_cpu_on_a_structured_image():
    import op_probe
    import ops
    S_env = [n for n in ALLOW["ops"] if n in ops.RT][:12]
    if not S_env:
        pytest.skip("no registry op on the allow-list")
    for name in S_env:
        if ops._BY_NAME[name].in_sort != "image":
            continue
        x = op_probe.structured_image(128)
        got = G.run_allowed(name, x, 0.5, 0.5)
        want = ops.RT[name](x, 0.5, 0.5)
        r = S.compare(want, got, np)
        assert r["ok"], (name, r)
        assert r["nonconst"], name


@needs_gpu
def test_random_stream_is_numpy_s_on_the_shadow():
    sh = G.get_shadow()
    xp = sh.namespace("numpy")
    np.random.seed(3)
    a = G.to_cpu(xp.random.random(5))
    np.random.seed(3)
    b = np.random.random(5)
    assert np.array_equal(a, b)
    ga = G.to_cpu(xp.random.default_rng(7).normal(size=4))
    assert np.array_equal(ga, np.random.default_rng(7).normal(size=4))


@needs_gpu
def test_missing_twin_runs_on_the_cpu_and_is_counted():
    sh = G.get_shadow()
    sp = sh.namespace("scipy.spatial")
    G.STATS.reset()
    tree = sp.cKDTree(G.to_gpu(np.random.default_rng(0).random((20, 3))))
    d, _i = tree.query(G.to_gpu(np.zeros((2, 3))))
    assert G._is_gpu(d)
    assert sum(G.STATS.cpu_calls.values()) >= 2
