"""領域の解析の族(accel_label)の門 / Gates for the GPU region-analysis family.

* ラベル付けは scipy と**領域の集合として**一致する(番号の付け方に頼らず、成分ごとの画素の集合が 1 対 1)。
  加えて、根を昇順に並べた順位が scipy の番号と一致する(``argmax`` の同点の選び方が同じになる根拠)。
* 族の全 op(採否を問わず 37)が CPU の op と一致する: 領域は画素ごとに完全一致、特徴は相対 1e-9。
  torch の CPU で常に走る(GPU の無い CI でも)。実 GPU の門は ``@pytest.mark.gpu``。
* 採用の集合(``accel_label.ADOPTED``)は実測の台帳(``GPU_ACCEL_USE.json``)の ``use`` と同じで、台帳は
  ログから作り直したものと同じ。採用は一致・定数でない・単独 5 倍(single)/ 常駐 1 倍(pipeline)。
* 鎖の枠だけの手書き経路は、単独の呼び出し(明示の cuda でも)と孤立した段では GPU に送らない。
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

import accel
import api
import device_policy
import gpu_route
import ops

torch = pytest.importorskip("torch")
import accel_label as AL  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
USE = json.loads((ROOT / "fullseye" / "data" / "GPU_ACCEL_USE.json").read_text(encoding="utf-8"))
KNOBS = ((0.5, 0.5), (0.0, 0.5), (0.9, 0.2), (0.25, 0.75))


def _blobs(side, seed, p=0.5, sig=2.0):
    from scipy import ndimage
    g = ndimage.gaussian_filter(np.random.default_rng(seed).random((side, side)), sig)
    return (g > np.quantile(g, p)).astype(np.float64)


def _fixtures():
    from tools.bench_label_ops import spiral
    rng = np.random.default_rng(0)
    fx = [_blobs(64, 1), _blobs(64, 2, 0.75), _blobs(57, 3, 0.4, 1.0), (rng.random((48, 64)) > 0.6) * 1.0,
          np.zeros((24, 24)), np.ones((24, 24)), spiral(33), _blobs(64, 4, 0.85, 3.0)]
    gray = np.clip(_blobs(64, 5) * 0.7 + rng.random((64, 64)) * 0.3, 0, 1)      # 灰色(0.5 で切る)
    nan = _blobs(64, 6).copy()
    nan[5, 7] = np.nan
    return fx + [gray, nan]


FIXTURES = _fixtures()


@pytest.mark.parametrize("conn", [4, 8])
def test_label_is_the_same_partition_as_scipy(conn):
    from scipy import ndimage
    st = ndimage.generate_binary_structure(2, 2 if conn == 8 else 1)
    for f in FIXTURES:
        m = np.nan_to_num(f) > 0.5
        lab, n = ndimage.label(m, structure=st)
        L, _fidx = AL.label(torch.as_tensor(m[None]), conn)
        L = L[0].numpy()
        roots = sorted(np.unique(L[m]))
        assert len(roots) == n
        for k, r in enumerate(roots, 1):                    # 成分の集合が 1 対 1(順位も scipy と同じ)
            assert np.array_equal(lab == k, L == r)


def test_label_batches_do_not_mix_images():
    a, b = _blobs(32, 1), _blobs(32, 2)
    L, _ = AL.label(torch.as_tensor(np.stack([a, b]) > 0.5), 8)
    one, _ = AL.label(torch.as_tensor(b[None] > 0.5), 8)
    fg = b > 0.5
    assert np.array_equal(L[1].numpy()[fg] - 32 * 32, one[0].numpy()[fg])     # 2 枚目の根は 2 枚目の中
    assert (L[1].numpy()[~fg] == 2 * 32 * 32).all()                         # 背景は全体の番兵


@pytest.mark.parametrize("key", sorted(AL.table()))
def test_every_family_op_matches_the_cpu_op(key):
    fn, core, _h = AL.table()[key]
    reducer = key in AL.REDUCERS
    for f in FIXTURES:
        for a, b in KNOBS:
            ref = ops.RT[core](f.copy(), a, b)
            got = fn(torch.as_tensor(f[None, None].astype(np.float32)), a, b, "cpu")
            if reducer:
                g, r = np.asarray(got[0], np.float64), np.asarray(ref, np.float64)
                assert g.shape == r.shape and np.allclose(g, r, rtol=1e-9, atol=1e-12), (core, f.shape, a, b)
            else:
                g = got[0, 0].numpy().astype(np.float64)
                assert np.array_equal(g, np.clip(np.asarray(ref, np.float64), 0, 1)), (core, f.shape, a, b)


def test_nonfinite_input_keeps_the_cpu_contract():
    """CPU が NaN / inf を拒む op は、GPU の側でも拒む(0.5 以下として黙って数えない)。"""
    from backend_safe import strict_mode
    f = FIXTURES[-1]
    for core in ("select_largest", "blob_count", "area_center", "cv_cc_count"):
        key = "lbl_" + core
        fn = AL.table()[key][0]
        with strict_mode(True):
            with pytest.raises(Exception) as cpu_err:
                ops.RT[core](f.copy(), 0.5, 0.5)
            with pytest.raises(type(cpu_err.value)):
                fn(torch.as_tensor(f[None, None].astype(np.float32)), 0.5, 0.5, "cpu")


# ---- 採否と台帳 ----------------------------------------------------------------------------------
def test_adopted_set_is_the_measured_ledger():
    ops_ = USE["ops"]
    assert len(ops_) >= 37                                         # 族の全 op を測った(空を通さない)
    assert {op for op, r in ops_.items() if r["use"]} == set(AL.ADOPTED)
    for op, r in ops_.items():
        assert r["points"] >= 12, op                               # 4 入力 x 3 辺
        if r["use"] == "single":
            assert r["ok"] and r["nonconst"] and r["ratio_single"] >= 5.0, op
        elif r["use"] == "pipeline":
            assert r["ok"] and r["nonconst"] and r["ratio_single"] < 5.0 and r["ratio_resident"] >= 1.0, op
        else:
            assert r["rejected"], op
    assert set(AL.ADOPTED) <= {core for _k, (_f, core, _h) in AL.table().items()}


def test_ledger_is_regenerated_from_the_committed_log():
    from tools.bench_label_ops import build
    assert json.loads(json.dumps(build(), sort_keys=True)) == json.loads(json.dumps(USE, sort_keys=True))


def test_accel_table_carries_exactly_the_adopted_ops():
    cores = {core for key, (_f, core, _h) in accel.ACCEL.items() if key.startswith("lbl_")}
    assert cores == set(AL.ADOPTED)
    assert accel.REDUCERS == {k for k in AL.REDUCERS if k in accel.ACCEL}


def test_accel_parity_reports_the_family_as_matching():
    rows = {name: inter for name, _h, _full, inter in accel.parity("cpu") if name.startswith("lbl_")}
    assert len(rows) == len(AL.ADOPTED)
    assert all(v < accel.PARITY_TOL for v in rows.values()), rows


def test_reducer_runs_return_values_not_images():
    im = _blobs(40, 9)
    out = accel.run_batch("lbl_count_obj", [im, 1 - im], 0.5, 0.5, "cpu")
    assert [float(v) for v in out] == [float(ops.RT["count_obj"](im, .5, .5)), float(ops.RT["count_obj"](1 - im, .5, .5))]
    seg = accel.run_pipeline([("reg_dilate", 0.2, 0.0), ("lbl_count_obj", 0.5, 0.5)], [im], "cpu")
    assert float(seg[0]) == float(ops.RT["count_obj"](np.clip(ops.RT["reg_dilate"](im, 0.2, 0.0), 0, 1), .5, .5))
    with pytest.raises(ValueError, match="last step"):
        accel.run_pipeline([("lbl_count_obj", 0.5, 0.5), ("reg_dilate", 0.2, 0.0)], [im], "cpu")


# ---- 経路: 単独 / 鎖の枠 -------------------------------------------------------------------------
def _uses():
    return {op: r["use"] for op, r in USE["ops"].items() if r["use"]}


def test_routes_follow_the_measured_use():
    for op, use in _uses().items():
        assert gpu_route.route(op, "pipeline").kind == "accel", op
        if use == "single":
            assert gpu_route.route(op, "single").kind == "accel", op
        else:
            assert gpu_route.route(op, "single") is None, op          # 単独では選ばない
            assert gpu_route.route(op, "pipeline").use == "pipeline", op


@pytest.fixture
def gpu_box(monkeypatch):
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(api, "cuda_available", lambda: True)
    monkeypatch.setattr(device_policy, "_query_free_mb", lambda: 30000.0)
    monkeypatch.setattr(device_policy, "_VRAM_CACHE", [])
    monkeypatch.setattr(gpu_route, "_CACHE", {"shadow_usable": True})


def test_chain_only_accel_is_demoted_when_isolated(gpu_box):
    shape = (2048, 2048)
    dec = api.explain_device("auto", stages=("count_obj",), shape=shape)
    assert (dec["device"], dec["reason"]) == ("cpu", "chain_only")
    dec = api.explain_device("auto", stages=("otsu", "count_obj"), shape=shape)
    assert [s["path"] for s in dec["stages"]] == ["accel", "accel"]
    # 隣が CPU だけの段(sk_rolling_ball は GPU 経路なし)なら孤立
    dec = api.explain_device("auto", stages=("gaussian", "sk_rolling_ball", "threshold", "remove_small", "blob_count",
                                             "gaussian"), shape=shape)
    assert [s["path"] for s in dec["stages"]][:5] == ["accel", "cpu", "accel", "accel", "accel"]


def test_apply_never_sends_a_chain_only_op_alone(gpu_box, monkeypatch):
    calls = []
    monkeypatch.setattr(api, "_try_accel", lambda op, v, a, b, device: calls.append(op.name) or api._NOACCEL)
    im = _blobs(256, 3)
    for device in ("auto", "cuda"):
        out = api.apply(im, "count_obj", device=device)
        assert out == float(ops.RT["count_obj"](im, .5, .5))
        assert api.last_device_decision()["reason"] == "chain_only"
    assert calls == []


def test_bridge_keeps_a_demoted_stage_on_the_cpu():
    import accel_bridge
    stages = [ops.stage("gaussian", .3, .5), ops.stage("sk_rolling_ball", .5, .5), ops.stage("threshold", .5, .5),
              ops.stage("count_obj", .5, .5)]
    kinds = [k for k, _ in accel_bridge.plan(stages, shadow=["accel", "cpu", "accel", "accel"])]
    assert kinds == ["gpu", "cpu", "gpu"]
    kinds = [k for k, _ in accel_bridge.plan(stages[2:], shadow=["cpu", "cpu"])]
    assert kinds == ["cpu"]


def test_run_pipeline_on_the_bridge_matches_cpu_for_the_family_recipes(gpu_box):
    """torch の CPU で橋を通す(device="cuda" を装っても kernel は CPU の torch)。全段 GPU のレシピが CPU と同じ答え。"""
    import accel_bridge
    im = np.clip(_blobs(96, 7) * 0.6 + 0.2, 0, 1)
    for chain in (["gaussian", "otsu", "fill_up", "count_obj"], ["otsu", "sk_clear_border", "count_obj"],
                  ["gaussian", "otsu", "select_shape"], ["gaussian", "otsu", "fill_up", "remove_small"],
                  ["otsu", "area_center"]):
        stages = [ops.stage(n, .5, .5) for n in chain]
        got = accel_bridge.run(stages, [im], device="cpu")[0]
        ref = ops.run_stages(stages, im)
        segs = accel_bridge.plan(stages)
        assert [k for k, _ in segs] == ["gpu"], chain                 # 全段が 1 つの常駐区間
        np.testing.assert_allclose(np.asarray(got, np.float64), np.asarray(ref, np.float64), rtol=0, atol=0)


# ---- 実 GPU ------------------------------------------------------------------------------------
def _cuda():
    try:
        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.gpu
@pytest.mark.skipif(not _cuda(), reason="CUDA is unavailable")
def test_real_gpu_family_matches_cpu():
    for key, (fn, core, _h) in AL.table().items():
        if core not in AL.ADOPTED:
            continue
        reducer = key in AL.REDUCERS
        for f in FIXTURES:
            for a, b in KNOBS[:2]:
                ref = ops.RT[core](f.copy(), a, b)
                got = fn(torch.as_tensor(f[None, None].astype(np.float32), device="cuda"), a, b, "cuda")
                if reducer:
                    assert np.allclose(np.asarray(got[0], np.float64), np.asarray(ref, np.float64), rtol=1e-9), core
                else:
                    g = got[0, 0].cpu().numpy().astype(np.float64)
                    assert np.array_equal(g, np.clip(np.asarray(ref, np.float64), 0, 1)), core


@pytest.mark.gpu
@pytest.mark.skipif(not _cuda(), reason="CUDA is unavailable")
def test_real_gpu_pipeline_runs_the_count_recipe_on_one_segment(monkeypatch):
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setenv("FULLSEYE_GPU_MIN_FREE_MB", "0")
    im = np.clip(_blobs(1024, 8) * 0.6 + 0.2, 0, 1)
    chain = ["gaussian", "otsu", "fill_up", "count_obj"]
    got = api.run_pipeline(im, chain, device="cuda", on_error="raise")
    dec = api.last_device_decision()
    ref = api.run_pipeline(im, chain, device="cpu", on_error="raise")
    assert float(np.asarray(got).reshape(-1)[0]) == float(np.asarray(ref).reshape(-1)[0])
    assert dec["device"] == "cuda" and [s["path"] for s in dec["stages"]] == ["accel"] * 4
