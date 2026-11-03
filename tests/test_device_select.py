"""装置の選択(VRAM・許可リストの道・経路と理由の開示)の門 / Device selection: VRAM, allow-list path, disclosure.

GPU が無くても走る門は常に走る(CUDA の有無・空き VRAM・CuPy の有無は差し替えて分岐だけを見る)。
実 GPU が要る門は ``@pytest.mark.gpu`` + skipif。
"""
from __future__ import annotations

import numpy as np
import pytest

import api
import device_policy

RULES = device_policy.load_rules()
SHADOW = device_policy.shadow_rows()
BIG = (2048, 2048)
SMALL = (64, 64)
HUGE = (8192, 8192)          # 形だけ(配列は作らない)。どの op の損益分岐よりも大きい


@pytest.fixture
def gpu_box(monkeypatch):
    """CUDA が在り、空き VRAM が十分な機械のふり(実 GPU には触らない)。"""
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.delenv("FULLSEYE_GPU_MIN_FREE_MB", raising=False)
    monkeypatch.setattr(api, "cuda_available", lambda: True)
    monkeypatch.setattr(device_policy, "_query_free_mb", lambda: 30000.0)
    monkeypatch.setattr(device_policy, "_VRAM_CACHE", [])
    monkeypatch.setattr(api, "_SHADOW_USABLE", [True])


def _accel_op():
    """損益分岐の閾値が一辺 64 より大きい手書き GPU 経路の op。"""
    return max(RULES["ops"], key=lambda o: RULES["ops"][o]["min_pixels"])


def _listed(list_name, in_sort="image"):
    rows = {r["name"]: r for r in api._rows()}
    accelerated = api._gpu_op_names()
    return sorted(op for op, row in SHADOW.items()
                  if row["list"] == list_name and op in rows and rows[op]["in_sort"] == in_sort
                  and op not in accelerated and row.get("min_elements") == BIG[0] * BIG[1]
                  and api.find_op(op) is not None)


def _not_listed():
    accelerated = api._gpu_op_names()
    return next(r["name"] for r in api._rows()
                if r["in_sort"] == "image" and r["name"] not in accelerated and r["name"] not in SHADOW
                and api.find_op(r["name"]) is not None)


# ---- VRAM ------------------------------------------------------------------------------------------
def test_min_free_mb_reads_the_environment(monkeypatch):
    monkeypatch.delenv("FULLSEYE_GPU_MIN_FREE_MB", raising=False)
    assert device_policy.min_free_mb() == device_policy.DEFAULT_MIN_FREE_MB
    for raw, want in (("512", 512), ("0", 0), ("1.5e3", 1500), ("-3", device_policy.DEFAULT_MIN_FREE_MB),
                      ("lots", device_policy.DEFAULT_MIN_FREE_MB)):
        monkeypatch.setenv("FULLSEYE_GPU_MIN_FREE_MB", raw)
        assert device_policy.min_free_mb() == want, raw


def test_auto_picks_cpu_when_vram_is_low(gpu_box, monkeypatch):
    op = _accel_op()
    monkeypatch.setattr(device_policy, "_query_free_mb", lambda: 500.0)
    dec = api.explain_device("auto", stages=(op,), shape=HUGE)
    assert (dec["resolved"], dec["device"], dec["path"], dec["reason"]) == ("cpu", "cpu", "cpu", "vram_low")
    assert dec["vram_free_mb"] == 500.0 and dec["vram_min_free_mb"] == device_policy.DEFAULT_MIN_FREE_MB
    assert api.resolve_device("auto") == "cpu"                 # 仕事の中身が無い auto も同じ
    monkeypatch.setenv("FULLSEYE_GPU_MIN_FREE_MB", "400")
    device_policy._VRAM_CACHE.clear()
    assert api.explain_device("auto", stages=(op,), shape=HUGE)["path"] == "accel"
    monkeypatch.setenv("FULLSEYE_GPU_MIN_FREE_MB", "0")         # 0 = 判定しない
    assert api.resolve_device("auto") == "cuda"


def test_explicit_cuda_and_environment_outrank_the_vram_check(gpu_box, monkeypatch):
    op = _accel_op()
    monkeypatch.setattr(device_policy, "_query_free_mb", lambda: 1.0)
    dec = api.explain_device("cuda", stages=(op,), shape=SMALL)
    assert (dec["resolved"], dec["device"], dec["path"]) == ("cuda", "cuda", "accel")
    monkeypatch.setenv("FULLSEYE_DEVICE", "cuda")
    dec = api.explain_device("auto", stages=(op,), shape=SMALL)
    assert (dec["resolved"], dec["path"], dec["source"]) == ("cuda", "accel", "FULLSEYE_DEVICE")
    monkeypatch.setenv("FULLSEYE_DEVICE", "cpu")
    dec = api.explain_device("cuda", stages=(op,), shape=BIG)
    assert (dec["resolved"], dec["reason"], dec["source"]) == ("cpu", "env_cpu", "FULLSEYE_DEVICE")


def test_unreadable_vram_is_not_judged(gpu_box, monkeypatch):
    monkeypatch.setattr(device_policy, "_query_free_mb", lambda: None)
    dec = api.explain_device("auto", stages=(_accel_op(),), shape=HUGE)
    assert dec["device"] == "cuda" and dec["vram_free_mb"] is None


def test_vram_query_is_cached_for_a_second(monkeypatch):
    calls = []
    monkeypatch.setattr(device_policy, "_query_free_mb", lambda: calls.append(1) or 9000.0)
    monkeypatch.setattr(device_policy, "_VRAM_CACHE", [])
    for _ in range(50):
        device_policy.free_vram_mb()
    assert len(calls) == 1


def test_query_never_imports_torch_or_cupy(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setitem(sys.modules, "cupy", None)
    assert device_policy._query_free_mb() is None


# ---- 経路と理由 -------------------------------------------------------------------------------------
def test_reasons_on_a_cpu_host(monkeypatch):
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(api, "cuda_available", lambda: False)
    assert api.explain_device("auto", stages=("gaussian",), shape=BIG)["reason"] == "no_cuda"
    dec = api.explain_device("cuda", stages=("gaussian",), shape=BIG)
    assert (dec["resolved"], dec["device"], dec["reason"]) == ("cuda", "cpu", "no_cuda")   # N117: 入口で拒まない
    assert api.explain_device("cpu", stages=("gaussian",), shape=BIG)["reason"] == "requested_cpu"


def test_crossover_and_not_listed(gpu_box):
    op = _accel_op()
    dec = api.explain_device("auto", stages=(op,), shape=SMALL)
    assert (dec["device"], dec["path"], dec["reason"]) == ("cpu", "cpu", "crossover")
    other = _not_listed()
    dec = api.explain_device("auto", stages=(other,), shape=BIG)
    assert (dec["resolved"], dec["reason"]) == ("cpu", "not_listed")
    dec = api.explain_device("cuda", stages=(other,), shape=BIG)
    assert (dec["resolved"], dec["device"], dec["reason"]) == ("cuda", "cpu", "not_listed")


def test_allow_list_single_needs_the_measured_size_under_auto(gpu_box):
    op = _listed("ops")[0]
    dec = api.explain_device("auto", stages=(op,), shape=BIG)
    assert (dec["resolved"], dec["device"], dec["path"]) == ("cuda", "cuda", "allow_single")
    dec = api.explain_device("auto", stages=(op,), shape=(1024, 1024))
    assert (dec["resolved"], dec["reason"]) == ("cpu", "below_measured_size")
    # 明示の cuda は大きさを問わない
    assert api.explain_device("cuda", stages=(op,), shape=SMALL)["path"] == "allow_single"


def test_allow_list_without_cupy(gpu_box, monkeypatch):
    monkeypatch.setattr(api, "_SHADOW_USABLE", [False])
    op = _listed("ops")[0]
    assert api.explain_device("auto", stages=(op,), shape=BIG)["reason"] == "no_cupy"
    dec = api.explain_device("cuda", stages=(op,), shape=BIG)
    assert (dec["resolved"], dec["device"], dec["reason"]) == ("cuda", "cpu", "no_cupy")


def test_resident_ops_only_inside_a_chain(gpu_box):
    resident = _listed("resident_ops")
    assert len(resident) >= 2
    a, b = resident[:2]
    assert api.explain_device("auto", stages=(a,), shape=BIG)["reason"] == "chain_only"
    dec = api.explain_device("auto", stages=(a, b), shape=BIG)
    assert dec["device"] == "cuda"
    assert [s["path"] for s in dec["stages"]] == ["allow_resident", "allow_resident"]
    # 孤立した常駐の段(隣が GPU 経路でない)は CPU
    dec = api.explain_device("auto", stages=(a, _not_listed(), b), shape=BIG)
    assert [s["reason"] for s in dec["stages"]] == ["chain_only", "not_listed", "chain_only"]
    assert dec["device"] == "cpu"


def test_plan_paths_demotes_isolated_chain_ops():
    shadow = {"r": {"list": "resident_ops", "min_elements": 1}, "p": {"list": "pipeline_ops", "min_elements": 1},
              "s": {"list": "ops", "min_elements": 1}}
    plan = device_policy.plan_paths(["r", "x", "s", "p", "acc"], (8, 8), accelerated={"acc"}, shadow=shadow,
                                    auto=True, shadow_usable=True)
    assert plan == [("cpu", "chain_only"), ("cpu", "not_listed"), ("allow_single", None),
                    ("allow_pipeline", None), ("accel", None)]


def test_gpu_paths_summary_for_the_ai():
    accel_op = _accel_op()
    info = device_policy.gpu_paths(accel_op, accelerated={accel_op})
    assert info["accel"] and info["kinds"] == ["accel"]
    assert info["auto_gpu_min_pixels"] == RULES["ops"][accel_op]["min_pixels"]
    op = _listed("ops")[0]
    info = device_policy.gpu_paths(op)
    assert (info["accel"], info["allow_list"], info["kinds"]) == (False, "ops", ["allow_single"])
    assert info["ratio"] >= 5.0 and info["auto_gpu_min_pixels"] == BIG[0] * BIG[1]
    none = device_policy.gpu_paths("no_such_op")
    assert none["kinds"] == [] and none["auto_gpu_min_pixels"] is None


def test_shadow_table_matches_the_allow_list():
    """許可リストの全行が表に載り、枠と倍率が写されている(写し間違いを別経路で数える)。"""
    import gpu_shadow
    assert len(SHADOW) >= 500
    for list_name, rows in (("ops", gpu_shadow.allowed_ops()), ("resident_ops", gpu_shadow.resident_ops()),
                            ("pipeline_ops", gpu_shadow.pipeline_ops())):
        for op, row in rows.items():
            mine = SHADOW[op]
            if mine["list"] != list_name:
                continue
            ratio = row["ratio"] if list_name == "ops" else row["ratio_resident"]
            assert mine["ratio"] == pytest.approx(ratio, abs=1e-3), op
    assert sum(r["min_elements"] is not None for r in SHADOW.values()) >= 500


# ---- 実行: apply / run_pipeline が許可リストの道を通る ------------------------------------------------
def test_apply_auto_runs_the_allow_list_path(gpu_box, monkeypatch):
    import gpu_shadow
    op = _listed("ops")[0]
    calls = []

    def fake(name, v, a, b):
        calls.append(name)
        return np.zeros_like(v)

    monkeypatch.setattr(gpu_shadow, "run_allowed", fake)
    api.reset_gpu()
    out = api.apply(np.full(BIG, 0.5), op, device="auto")
    assert calls == [op] and float(out.max()) == 0.0
    assert api.last_device_decision()["path"] == "allow_single"
    api.apply(np.full((256, 256), 0.5), op, device="auto")      # 測った大きさ未満は CPU
    assert calls == [op]
    assert api.last_device_decision()["reason"] == "below_measured_size"


def test_allow_list_failure_is_recorded_and_runs_on_cpu(gpu_box, monkeypatch):
    import gpu_shadow
    op = _listed("ops")[0]

    def broken(name, v, a, b):
        raise RuntimeError("simulated CuPy failure")

    monkeypatch.setattr(gpu_shadow, "run_allowed", broken)
    api.reset_gpu()
    api.clear_fallbacks()
    image = np.random.default_rng(3).random((256, 256))
    expected = api.apply(image, op, device="cpu")
    out = api.apply(image, op, device="cuda")
    assert np.array_equal(out, expected)
    assert any(r.get("name") == op and r.get("source") == "gpu" for r in api.fallbacks())
    api.reset_gpu()
    with pytest.raises(RuntimeError, match="simulated CuPy failure"):
        api.apply(image, op, device="cuda", on_error="raise")
    api.reset_gpu()


def test_run_pipeline_puts_listed_stages_on_the_shadow_segment(gpu_box, monkeypatch):
    import gpu_shadow
    a, b = _listed("resident_ops")[:2]
    seen = []

    def fake_chain(stages, imgs):
        seen.append([st.op for st in stages])
        return [np.asarray(im) for im in imgs]

    monkeypatch.setattr(gpu_shadow, "run_chain", fake_chain)
    image = np.full(BIG, 0.25)
    out = api.run_pipeline(image, [a, b], device="auto", on_error="raise")
    assert seen == [[a, b]]
    assert np.array_equal(out, image)
    dec = api.last_device_decision()
    assert dec["device"] == "cuda" and dec["path"] == "allow_resident"


def test_bridge_ignores_shadow_paths_of_the_wrong_length():
    import accel_bridge
    import ops
    stages = [ops.stage("gaussian", 0.3, 0.5), ops.stage("clahe", 0.5, 0.5)]
    assert [k for k, _ in accel_bridge.plan(stages, shadow=["accel"])] == [k for k, _ in accel_bridge.plan(stages)]


def test_run_chain_refuses_unlisted_stages():
    import gpu_shadow
    import ops
    with pytest.raises(gpu_shadow.GpuAutoError, match="allow-list"):
        gpu_shadow.run_chain([ops.stage(_not_listed(), 0.5, 0.5)], [np.zeros((4, 4))])


# ---- MCP: 選んだ結果を見せる ------------------------------------------------------------------------
def _store_with(image):
    from fullseye.mcp.handles import HandleStore
    store = HandleStore(roots=[], max_bytes=100_000_000)
    return store, store.put(image, sort="image", provenance=[])["handle"]


def test_mcp_apply_reports_path_and_reason(monkeypatch):
    from fullseye.mcp import Catalog, call_tool
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    store, h = _store_with(np.random.default_rng(0).random((32, 32)))
    res = call_tool("fullseye_apply", {"handle": h, "op": "gaussian", "vision": "none", "device": "cpu"},
                    Catalog.load(), store)
    acc = res["structuredContent"]["acceleration"]
    assert {"requested", "device", "approximate"} <= set(acc)              # 既存の欄は残る
    assert (acc["device"], acc["path"], acc["reason"]) == ("cpu", "cpu", "requested_cpu")
    monkeypatch.setattr(api, "cuda_available", lambda: False)
    res = call_tool("fullseye_apply", {"handle": h, "op": "gaussian", "vision": "none"}, Catalog.load(), store)
    acc = res["structuredContent"]["acceleration"]
    assert (acc["requested"], acc["device"], acc["reason"]) == ("auto", "cpu", "no_cuda")


def test_mcp_pipeline_reports_each_stage(monkeypatch):
    from fullseye.mcp import Catalog, call_tool
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(api, "cuda_available", lambda: False)
    store, h = _store_with(np.random.default_rng(1).random((32, 32)))
    res = call_tool("fullseye_pipeline", {"handle": h, "vision": "none",
                                          "stages": [{"op": "gaussian"}, {"op": "sobel_mag"}]},
                    Catalog.load(), store)
    acc = res["structuredContent"]["acceleration"]
    assert acc["device"] == "cpu" and acc["n_transfers"] == 0 and acc["reason"] == "no_cuda"
    assert [s["op"] for s in acc["stages"]] == ["gaussian", "sobel_mag"]
    assert all(s["path"] == "cpu" for s in acc["stages"])


def test_mcp_pipeline_counts_one_round_trip_per_gpu_stage(gpu_box, monkeypatch):
    """MCP の pipeline は段ごとに apply を呼ぶ: GPU で走った段ごとに往復 1 回。"""
    from fullseye.mcp import Catalog, call_tool
    monkeypatch.setattr(api, "_try_accel", lambda op, v, a, b, device: v)
    store, h = _store_with(np.random.default_rng(2).random((1100, 1100)))
    res = call_tool("fullseye_pipeline", {"handle": h, "vision": "none",
                                          "stages": [{"op": "gaussian"}, {"op": "clahe"}]},
                    Catalog.load(), store)
    acc = res["structuredContent"]["acceleration"]
    by_op = {s["op"]: s for s in acc["stages"]}
    assert by_op["gaussian"]["path"] == "accel" and by_op["gaussian"]["device"] == "cuda"
    assert by_op["clahe"]["device"] == "cpu" and by_op["clahe"]["reason"] == "below_measured_size"
    assert acc["n_transfers"] == 2 and acc["path"] == "mixed"


def test_mcp_describe_carries_gpu_paths():
    from fullseye.mcp import Catalog, call_tool
    op = _listed("ops")[0]
    res = call_tool("fullseye_describe", {"kind": "op", "name": op}, Catalog.load())
    info = res["structuredContent"]["description"]["op"]["gpu_paths"]
    assert info["allow_list"] == "ops" and info["kinds"] == ["allow_single"]
    res = call_tool("fullseye_describe", {"kind": "op", "name": "gaussian"}, Catalog.load())
    assert res["structuredContent"]["description"]["op"]["gpu_paths"]["accel"] is True


# ---- 実 GPU ---------------------------------------------------------------------------------------
def _cuda():
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.gpu
@pytest.mark.skipif(not _cuda(), reason="CUDA is unavailable")
def test_real_gpu_decision_and_vram(monkeypatch):
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.delenv("FULLSEYE_GPU_MIN_FREE_MB", raising=False)
    monkeypatch.setattr(device_policy, "_VRAM_CACHE", [])
    import torch
    torch.zeros(1, device="cuda")
    free = device_policy.free_vram_mb()
    assert free is not None and free > 0
    op = _accel_op()
    image = np.random.default_rng(5).random((1024, 1024))
    dec = api.explain_device("auto", stages=(op,), shape=image.shape)
    assert dec["path"] == "accel" and dec["vram_free_mb"] is not None
    out = api.apply(image, op, device="auto", on_error="raise")
    ref = api.apply(image, op, device="cpu", on_error="raise")
    assert out.shape == ref.shape


@pytest.mark.gpu
@pytest.mark.skipif(not _cuda(), reason="CUDA is unavailable")
def test_real_gpu_allow_list_path_matches_cpu(monkeypatch):
    import gpu_shadow
    if not gpu_shadow.available():
        pytest.skip("CuPy cannot see the GPU")
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    op = _listed("ops")[0]
    image = np.random.default_rng(6).random((256, 256))
    api.reset_gpu()
    api.clear_fallbacks()
    out = api.apply(image, op, device="cuda", on_error="raise")
    assert api.last_device_decision()["path"] == "allow_single"
    ref = api.apply(image, op, device="cpu", on_error="raise")
    assert np.max(np.abs(np.asarray(out, np.float64) - np.asarray(ref, np.float64))) < 5e-3
