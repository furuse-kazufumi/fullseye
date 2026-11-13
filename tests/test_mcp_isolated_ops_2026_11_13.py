# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""台帳 op(光学・照明・合成の入口・px→mm)を MCP の pipeline から、隔離した子プロセスで走らせる。

2026-11-13 の検証(AI の役で MCP を使った)で、optics 次元の op は MCP から 1 つも実行できなかった
(全部「not executable in MCP; call from Python」)。ここで見るのは:

- 子プロセスの上限(時間・メモリ)と砂場(ファイル・ネット・子プロセス)が効く事、
- 引数が台帳の仕様で検査され、合わない値は 1 段も走らせずに断られる事、
- 照明の op・合成の入口・px→mm が、道具(fullseye_pipeline)だけで呼べ、結果に単位と意味が付く事、
- OP_GRAPH に「隔離して走らせる」と書いた op が、**全部**、書いてある見本のとおりに MCP から走る事。
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fullseye.mcp import server as S                              # noqa: E402
from fullseye.mcp.catalog import Catalog                          # noqa: E402
from fullseye.mcp.handles import HandleStore                      # noqa: E402
from fullseye.mcp.opworker import (OpWorker, OpWorkerError,       # noqa: E402
                                   close_worker, decode_tree, encode_tree)
from fullseye.opsearch import _graph                              # noqa: E402

#: 検証(2026-11-13)で AI が照明の候補として引いた 17 op。全部「not executable in MCP」だった。
ILLUMINATION = ("light_source", "irradiance_map", "illumination_uniformity", "defect_contrast", "lighting_sweep",
                "illumination_design", "solid_angle_light", "solid_angle_boundaries", "solid_angle_brightness",
                "solid_angle_sweep", "solid_angle_render", "illumination_train", "illumination_field",
                "coaxial_illumination", "darkfield_scatter_relation", "illumination_visibility", "dome_contact_image")
#: レンズ・センサの選定に使う op(焦点距離・絞り・被写界深度・MTF・センサの寸法)
LENS_AND_SENSOR = ("lens_spec", "lens_catalog", "sensor_spec", "sensor_catalog", "sensor_diagonal_mm", "optical_camera",
                   "thin_lens", "depth_of_field", "telecentric_lens", "magnification_vs_depth", "mtf50")
ENTRY_POINTS = ("bottle_image", "pixel_to_world", "binocular_disparity_ms")
FIXTURE = {"ledger_module": "mcp_worker_fixture_ledger", "ledger_table": "TABLE", "data_names": []}


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


@pytest.fixture()
def store(tmp_path):
    return HandleStore(thumb_dir=str(tmp_path / "thumb"))


@pytest.fixture(scope="module")
def worker():
    w = OpWorker()
    yield w
    w.close()


@pytest.fixture(scope="module", autouse=True)
def _close_shared_worker():
    yield
    close_worker()


def _edges():
    return {e["op"]: e for e in _graph()["edges"]}


def _isolated_edges():
    return {name: e for name, e in _edges().items() if (e.get("executor") or {}).get("isolation") == "worker"}


def _run(cat, store, stages, **extra):
    return S.call_tool("fullseye_pipeline", dict(stages=stages, **extra), cat, store)


# --------------------------------------------------------------------------- 子プロセスの上限と砂場
def test_tree_codec_round_trips_tables_without_pickle(tmp_path):
    value = {"a": np.arange(12, dtype=np.float32).reshape(3, 4), "big": np.zeros((600, 600)), "t": (1, 2.5, "x"),
             "n": None, "f": float("inf"), "c": 1 + 2j, "s": np.float32(1.5), 3: [True, 7]}
    tree = encode_tree(value, str(tmp_path))
    json.dumps(tree)                                              # JSON にできる木である
    back = decode_tree(json.loads(json.dumps(tree)), str(tmp_path))
    assert back["a"].dtype == np.float32 and np.array_equal(back["a"], value["a"])
    assert back["big"].shape == (600, 600) and back["t"] == (1, 2.5, "x") and back["n"] is None
    assert back["f"] == float("inf") and back["c"] == 1 + 2j and back["3"] == [True, 7]
    assert isinstance(back["s"], np.float32)
    with pytest.raises(TypeError):
        encode_tree({"o": object()}, str(tmp_path))
    with pytest.raises(TypeError):
        encode_tree(np.array(["a", object()], dtype=object), str(tmp_path))
    with pytest.raises(ValueError):
        decode_tree({"t": "n", "file": "../outside.npy"}, str(tmp_path))


def test_worker_returns_tables_and_survives_many_jobs(worker):
    for scale in (1.0, 2.0, 3.0):
        value, info = worker.run(dict(FIXTURE, key="table"), [], {"scale": scale}, time_limit_s=30, max_rss=1 << 30)
        assert value["height_mm"] == 3.0 * scale and value["image"].shape == (64, 48)
        assert value["tuple"] == (1, 2.5, "x") and np.isnan(value["bad"]) and info["elapsed_s"] >= 0.0
    value, _info = worker.run(dict(FIXTURE, key="scratch_write"), [], {}, time_limit_s=30, max_rss=1 << 30)
    assert value == {"ok": True}


def test_worker_stops_an_op_at_the_time_limit_and_recovers(worker):
    with pytest.raises(OpWorkerError) as err:
        worker.run(dict(FIXTURE, key="sleep"), [], {"seconds": 60.0}, time_limit_s=1.0, max_rss=1 << 30)
    assert err.value.reason == "time_limit"
    value, _info = worker.run(dict(FIXTURE, key="table"), [], {}, time_limit_s=30, max_rss=1 << 30)
    assert value["height_mm"] == 6.0                               # 子を作り直して次の仕事を受ける


def test_worker_stops_an_op_at_the_memory_limit_and_recovers(worker):
    with pytest.raises(OpWorkerError) as err:
        worker.run(dict(FIXTURE, key="allocate"), [], {"mebibytes": 1024}, time_limit_s=60, max_rss=128 << 20)
    assert err.value.reason == "memory_limit"
    value, _info = worker.run(dict(FIXTURE, key="allocate"), [], {"mebibytes": 8}, time_limit_s=60, max_rss=512 << 20)
    assert value["sum"] == float(8 << 17)


def test_worker_refuses_files_network_and_processes(worker, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    cases = {"write_outside": {"target": str(tmp_path / "new.txt")}, "read_outside": {"target": str(outside)},
             "remove_outside": {"target": str(outside)}, "connect": {}, "spawn": {}}
    seen = {}
    for key, kwargs in cases.items():
        with pytest.raises(OpWorkerError) as err:
            worker.run(dict(FIXTURE, key=key), [], kwargs, time_limit_s=30, max_rss=1 << 30)
        seen[key] = (err.value.reason, err.value.error_type)
    assert seen == {key: ("op_error", "PermissionError") for key in cases}
    assert outside.read_text(encoding="utf-8") == "secret" and not (tmp_path / "new.txt").exists()
    with pytest.raises(OpWorkerError) as err:
        worker.run(dict(FIXTURE, key="object_result"), [], {}, time_limit_s=30, max_rss=1 << 30)
    assert err.value.reason == "unsupported_value"


def test_worker_scratch_folder_is_removed_on_close():
    w = OpWorker()
    w.run(dict(FIXTURE, key="table"), [], {}, time_limit_s=30, max_rss=1 << 30)
    tmp = w._tmp
    assert os.path.isdir(tmp)
    w.close()
    assert not os.path.exists(tmp)


# --------------------------------------------------------------------------- OP_GRAPH の印
def test_illumination_and_entry_point_ops_are_executable_in_mcp():
    edges = _edges()
    wanted = ILLUMINATION + LENS_AND_SENSOR + ENTRY_POINTS
    assert len(ILLUMINATION) == 17
    missing = [n for n in wanted if not edges[n].get("verified_executable")]
    assert not missing, missing
    isolated = _isolated_edges()
    assert len(isolated) >= 300                                   # 実測の台帳が黙って縮んでいない
    optics = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                         "docs", "OP_INDEX.json"), encoding="utf-8"))["ops"]
    optics_names = {r["name"] for r in optics if r.get("dim") == "optics"}
    assert len(optics_names) >= 500
    assert len(optics_names & set(isolated)) >= 150


def test_isolated_edges_never_take_file_or_callable_arguments():
    isolated = _isolated_edges()
    assert len(isolated) >= 300
    bad = []
    for name, edge in isolated.items():
        for row in edge["parameter_schema"]:
            if row["kind"] not in ("number", "int", "bool", "choice", "text"):
                bad.append((name, row["name"], row["kind"]))
            if row["name"] in ("path", "filename", "file", "url", "callback", "out_path"):
                bad.append((name, row["name"], "io name"))
    assert not bad, bad[:10]


# --------------------------------------------------------------------------- 道具だけで呼ぶ
def test_illumination_design_runs_from_the_pipeline_tool_without_a_handle(cat, store):
    r = _run(cat, store, [{"op": "illumination_design",
                           "params": {"surface": "glossy", "defect": "topographic", "slope_deg": 8.0}}])
    assert not r["isError"], r["content"][0]["text"]
    stage = r["structuredContent"]["stages"][0]
    assert stage["status"] == "ok" and stage["out_sort"] == "table" and stage["value_handle"]
    ranking = stage["value"]["ranking"]
    assert len(ranking) >= 3 and {"candidate", "score", "contrast"} <= set(ranking[0])
    assert stage["value"]["recommended"] and stage["param_units"] == {"slope_deg": "°"}
    assert stage["units"].get("best_ring_elevation_deg") == "°" and "Rank" in stage["meaning"]
    assert stage["isolated"]["time_limit_s"] > 0 and stage["isolated"]["memory_limit_bytes"] > 0
    text = r["content"][0]["text"]
    assert "ranking" in text and "recommended" in text and "illumination_design" in text


def test_light_source_feeds_defect_contrast_and_lighting_sweep_gives_pairs(cat, store):
    r = _run(cat, store, [{"op": "light_source", "params": {"kind": "ring", "radius_mm": 60.0, "height_mm": 30.0}},
                          {"op": "defect_contrast", "inputs": ["stage:1"], "params": {"surface": "glossy"}}])
    assert not r["isError"], r["content"][0]["text"]
    first, second = r["structuredContent"]["stages"]
    assert first["units"]["height_mm"] == "mm" and first["value"]["elevation_deg"] > 0
    assert second["status"] == "ok" and isinstance(second["value"], dict) and second["value"]
    sweep = _run(cat, store, [{"op": "lighting_sweep", "params": {"surface": "glossy", "slope_deg": 8.0}}])
    assert not sweep["isError"], sweep["content"][0]["text"]
    rec = sweep["structuredContent"]["stages"][0]
    meta, pairs = store.get(rec["handle"])
    assert meta["sort"] == "pairs" and pairs.ndim == 2 and pairs.shape[1] == 2 and len(pairs) >= 5


def test_bottle_image_gives_an_image_handle_the_next_pipeline_can_use(cat, store):
    r = _run(cat, store, [{"op": "bottle_image", "params": {
        "radius_mm": 30.0, "wall_mm": 2.0, "height_mm": 120.0, "fill_fraction": 0.6, "n_glass": 1.52,
        "n_liquid": 1.333, "pixel_pitch_um": 200.0}}])
    assert not r["isError"], r["content"][0]["text"]
    stage = r["structuredContent"]["stages"][0]
    fields = {f["key"]: f for f in stage["field_handles"]}
    assert fields["image"]["sort"] == "image" and fields["image"]["shape"] == [600, 345]
    assert stage["units"]["fill_z_mm"] == "mm" and stage["value"]["fill_fraction"] == 0.6
    nxt = S.call_tool("fullseye_pipeline", {"handle": fields["image"]["handle"],
                                            "stages": [{"op": "gaussian", "a": 0.2}]}, cat, store)
    assert not nxt["isError"], nxt["content"][0]["text"]
    assert nxt["structuredContent"]["out_sort"] == "image"


def test_pixel_to_world_takes_a_number_or_a_measuring_stage(cat, store):
    r = _run(cat, store, [{"op": "pixel_to_world", "params": {"value_px": 46.3, "mm_per_px": 0.02}}])
    assert not r["isError"], r["content"][0]["text"]
    stage = r["structuredContent"]["stages"][0]
    value = store.get(stage["value_handle"])[1]
    assert abs(float(np.asarray(value).reshape(-1)[0]) - 0.926) < 1e-9
    assert stage["param_units"]["mm_per_px"] == "mm/px"
    h = S.call_tool("fullseye_load_image", {"path": "coins"}, cat, store)["structuredContent"]["handle"]
    chain = S.call_tool("fullseye_pipeline", {"handle": h, "stages": [
        {"op": "otsu"}, {"op": "diameter_region"},
        {"op": "pixel_to_world", "params": {"value_px": {"ref": "stage:2"}, "mm_per_px": 0.5}}]}, cat, store)
    assert not chain["isError"], chain["content"][0]["text"]
    px = chain["structuredContent"]["stages"][1]["value"]
    mm = store.get(chain["structuredContent"]["stages"][2]["value_handle"])[1]
    assert abs(float(np.asarray(mm).reshape(-1)[0]) - 0.5 * float(np.asarray(px).reshape(-1)[0])) < 1e-9


def test_stereo_disparity_runs_on_two_image_handles(cat, store):
    rng = np.random.default_rng(3)
    left = rng.random((48, 64))
    right = np.roll(left, -4, axis=1)
    hl = store.put(left, sort="image", provenance=[])["handle"]
    hr = store.put(right, sort="image", provenance=[])["handle"]
    r = S.call_tool("fullseye_pipeline", {"stages": [
        {"op": "binocular_disparity_ms", "inputs": [hl, hr], "params": {"max_disp": 8}}]}, cat, store)
    assert not r["isError"], r["content"][0]["text"]
    fields = {f["key"]: f for f in r["structuredContent"]["stages"][0]["field_handles"]}
    disparity = store.get(fields["disparity"]["handle"])[1]
    assert disparity.shape == (48, 64) and abs(float(np.median(disparity[8:-8, 12:-12])) - 4.0) <= 1.0


# --------------------------------------------------------------------------- 引数の検査(fail-closed)
@pytest.mark.parametrize("params, reason", [
    ({"surface": "../../etc/passwd"}, "parameter_type_mismatch"),
    ({"surface": "C:\\Windows"}, "parameter_type_mismatch"),
    ({"slope_deg": "ten"}, "parameter_type_mismatch"),
    ({"slope_deg": True}, "parameter_type_mismatch"),
    ({"slope_deg": [[[[[1.0]]]]]}, "parameter_type_mismatch"),
    ({"slope_deg": None}, "parameter_type_mismatch"),
    ({"no_such_argument": 1.0}, "unknown_parameter"),
    ({"slope_deg": {"nested": 1}}, "parameter_type_mismatch"),
])
def test_bad_arguments_are_refused_before_anything_runs(cat, store, params, reason):
    checked = S.validate_pipeline([{"op": "illumination_design", "params": params}], None, cat, store=store)
    assert not checked["valid"] and [e["reason"] for e in checked["errors"]] == [reason]
    r = _run(cat, store, [{"op": "illumination_design", "params": params}])
    assert r["isError"] and "stages" not in r.get("structuredContent", {"stages": []}) or r["isError"]


def test_values_the_op_itself_rejects_come_back_as_a_failed_stage_with_the_example(cat, store):
    r = _run(cat, store, [{"op": "illumination_design", "params": {"surface": "no such surface"}}])
    assert r["isError"]
    stage = r["structuredContent"]["stages"][0]
    assert stage["status"] == "failed" and stage["reason"] == "execution_failed"
    assert stage["error"]["type"] == "ValueError" and stage["example"]["stages"]


def test_time_limit_of_the_pipeline_tool_is_a_reported_resource_limit(cat, store, monkeypatch):
    import fullseye.mcp.opworker as W

    def too_slow(job, args, kwargs, *, time_limit_s, max_rss):
        raise OpWorkerError("time_limit", "the op ran longer than the %.0f s limit and was stopped" % time_limit_s)

    monkeypatch.setattr(W, "run_isolated", too_slow)
    r = _run(cat, store, [{"op": "illumination_design"}])
    assert r["isError"]
    stage = r["structuredContent"]["stages"][0]
    assert stage["reason"] == "resource_limit" and stage["error"]["limit"] == "time_limit"
    assert stage["error"]["time_limit_s"] == float(S.get_system("mcp_op_time_limit_s"))


def test_isolated_limits_follow_fssystem(cat, store):
    import fssystem
    with fssystem.system(mcp_op_time_limit_s=5, mcp_op_memory_limit_bytes=268435456):
        limits = S._isolated_limits()
    assert limits["time_limit_s"] == 5.0 and limits["memory_limit_bytes"] == 268435456


# --------------------------------------------------------------------------- 全数: 見本のとおりに MCP から走る
def _with_sample_handles(stages, isolated, store):
    """見本の段が読む have:<型> を、その段の op の見本の入力(opassist.sample_input)のハンドルに置き換える。

    handle は MCP で実際に来る形にする: 画像の列(seq<image>)は (T,H,W) の配列(fullseye_load_stack と同じ)、
    それ以外は前の段の op が返した値と同じく、見本の値をそのまま置く(配列に直さない)。"""
    import opassist
    out = []
    for stage in stages:
        stage = json.loads(json.dumps(stage))
        refs = stage.get("inputs", [])
        if any(ref.startswith("have:") for ref in refs):
            executor = isolated[stage["op"]]["executor"]
            values, _kwargs = opassist.sample_input(stage["op"])
            given = [v for n, v in zip(executor["data_names"], values) if n not in stage.get("params", {})]
            if len(given) != len(refs):
                raise ValueError("%s: %d sample inputs for %d refs" % (stage["op"], len(given), len(refs)))
            handles = []
            for n, (ref, value) in enumerate(zip(refs, given)):
                if ref.startswith("have:"):
                    sort = ref.split(":", 1)[1]
                    if sort in ("seq<image>", "images") and isinstance(value, (list, tuple)):
                        value = np.stack([np.asarray(v, dtype=np.float64) for v in value])
                    ref = store.put(value, sort=sort, provenance=[{"input": n}])["handle"]
                handles.append(ref)
            stage["inputs"] = handles
            stage["allow_reuse"] = True
        out.append(stage)
    return out


_SHARDS = 8


@pytest.mark.parametrize("shard", range(_SHARDS))
def test_every_isolated_op_runs_its_recorded_example_through_the_pipeline_tool(cat, tmp_path, shard):
    """OP_GRAPH に「隔離して走らせる」と書いた op を**全部**(8 片に分けて)、記録した見本のとおりに道具から走らせる。"""
    isolated = _isolated_edges()
    assert len(isolated) >= 300
    names = sorted(isolated)[shard::_SHARDS]
    assert len(names) >= len(isolated) // _SHARDS
    failures = []
    for name in names:
        edge = isolated[name]
        store = HandleStore(thumb_dir=str(tmp_path / "t"))
        args = {"stages": _with_sample_handles(edge["example"]["stages"], isolated, store), "vision": "none"}
        try:
            r = S.call_tool("fullseye_pipeline", args, cat, store)
        except S.ArgError as exc:
            failures.append((name, "ArgError", str(exc)[:160]))
            continue
        if r["isError"]:
            bad = next((s for s in r["structuredContent"].get("stages", []) if s.get("status") == "failed"), {})
            failures.append((name, bad.get("reason"), json.dumps(bad.get("error") or r["structuredContent"].get("errors"),
                                                                 ensure_ascii=False)[:200]))
    assert not failures, "%d of %d: %s" % (len(failures), len(names), failures[:8])


# --------------------------------------------------------------------------- 2026-11-13 の続き
def test_lens_spec_and_depth_of_field_run_with_units(cat, store):
    r = _run(cat, store, [{"op": "lens_spec", "params": {"focal_mm": 25.0, "f_number": 2.8}}])
    assert not r["isError"], r["content"][0]["text"]
    stage = r["structuredContent"]["stages"][0]
    assert stage["param_units"] == {"focal_mm": "mm"} and "focal_mm" in r["content"][0]["text"]
    dof = _run(cat, store, [{"op": "depth_of_field"}])
    assert not dof["isError"], dof["content"][0]["text"]


def test_apply_runs_a_ledger_op_through_the_same_checked_path(cat, store):
    h = S.call_tool("fullseye_load_image", {"path": "coins"}, cat, store)["structuredContent"]["handle"]
    r = S.call_tool("fullseye_apply", {"handle": h, "op": "illumination_design",
                                       "params": {"surface": "glossy", "slope_deg": 8.0}}, cat, store)
    assert not r["isError"], r["content"][0]["text"]
    assert r["structuredContent"]["stages"][0]["isolated"]["time_limit_s"] > 0
    with pytest.raises(S.ArgError, match="CPU only"):
        S.call_tool("fullseye_apply", {"handle": h, "op": "illumination_design", "device": "cuda"}, cat, store)
    with pytest.raises(S.ArgError, match="named params"):
        S.call_tool("fullseye_apply", {"handle": h, "op": "illumination_design", "a": 0.3}, cat, store)
    checked = S.validate_pipeline([{"op": "illumination_design", "params": {"slope_deg": "../x"}}], None, cat,
                                  store=store)
    assert [e["reason"] for e in checked["errors"]] == ["parameter_type_mismatch"]


def test_device_argument_of_a_ledger_op_is_cpu_only(cat, store):
    edges = _isolated_edges()
    with_device = sorted(n for n, e in edges.items() if any(r["name"] == "device" for r in e["parameter_schema"]))
    assert len(with_device) >= 5
    for name in with_device:
        row = next(r for r in edges[name]["parameter_schema"] if r["name"] == "device")
        assert row["kind"] == "choice" and row["choices"] == ["cpu"], (name, row)
    assert S._check_isolated_param("radon_transform", {"name": "device", "kind": "text"}, "cuda")
    assert S._check_isolated_param("radon_transform", {"name": "device", "kind": "choice", "choices": ["cpu"]},
                                   "cpu") is None


def test_sequence_and_label_handles_are_reshaped_for_ledger_ops():
    frames = np.stack([np.full((4, 5), float(k)) for k in range(3)])
    assert S._stack_sequence(list(frames), "x").shape == (3, 4, 5)
    ragged = [np.zeros((4, 5)), np.zeros((4, 6))]
    assert S._stack_sequence(ragged, "x") is ragged                # 形が揃わない列はまとめない(後の検査が断る)
    labels = np.array([[0.0, 1.0], [2.0, 2.0]])
    out = S._integral_labels(labels)
    assert out.dtype.kind == "i" and np.array_equal(out, labels)
    fractional = np.array([[0.0, 0.5]])
    assert S._integral_labels(fractional) is fractional            # 丸めない: op 自身の検査に断らせる


def test_complex_values_come_back_as_real_and_imaginary_parts(cat, store):
    r = _run(cat, store, [{"op": "jones_state"}], vision="none")
    assert not r["isError"], r["content"][0]["text"]
    value = r["structuredContent"]["stages"][0]["value"]
    assert set(value) == {"re", "im"} and len(value["re"]) == len(value["im"]) == 2
    json.dumps(r["structuredContent"])


def test_array_arguments_recorded_by_the_probe_are_passed_as_arrays(cat, store):
    edges = _isolated_edges()
    assert "K" in edges["project_points"]["executor"]["array_params"]
    stages = json.loads(json.dumps(edges["pose_to_matrix"]["example"]["stages"]))
    pts = store.put(np.random.default_rng(0).normal(size=(64, 3)) + [0.0, 0.0, 5.0], sort="points",
                    provenance=[])["handle"]
    for st in stages:
        st["inputs"] = [pts if ref == "have:points" else ref for ref in st.get("inputs", [])]
        st["allow_reuse"] = True
    r = _run(cat, store, stages, vision="none")
    assert not r["isError"], r["content"][0]["text"]


def test_ops_mcp_cannot_run_say_why_and_what_to_do_instead(cat, store):
    from fullseye.opsearch import MCP_UNAVAILABLE_REASONS, mcp_unavailable
    info = mcp_unavailable("lens_file_read")
    assert info["reason"] == "io_parameter" and "file" in info["why"]
    instead = info["instead"]
    assert len(instead) >= 2
    assert any("fullseye.op_run('lens_file_read')" in x for x in instead)
    alternatives = info["executable_alternatives"]
    assert len(alternatives) >= 3
    assert all(_edges()[n]["verified_executable"] for n in alternatives)
    assert mcp_unavailable("illumination_design") is None
    h = S.call_tool("fullseye_load_image", {"path": "coins"}, cat, store)["structuredContent"]["handle"]
    with pytest.raises(S.ArgError) as err:
        S.call_tool("fullseye_apply", {"handle": h, "op": "lens_file_read"}, cat, store)
    text = str(err.value)
    assert "never touch files" in text and "op_run" in text and "近い名前: ['lens_file_read'" not in text
    checked = S.validate_pipeline([{"op": "lens_file_read"}], None, cat, store=store)
    err0 = checked["errors"][0]
    assert err0["reason"] == "not_executable_in_mcp" and err0["why"] and err0["instead"] and err0["candidates"]
    # 理由の符号は全部、人が読む文を持つ(OP_GRAPH に出てくる符号を全部数える)
    codes = {e.get("mcp_probe") or e.get("not_executable_in_mcp") for e in _edges().values()
             if not e.get("verified_executable")}
    assert len(codes) >= 5 and not (codes - set(MCP_UNAVAILABLE_REASONS)), codes - set(MCP_UNAVAILABLE_REASONS)
