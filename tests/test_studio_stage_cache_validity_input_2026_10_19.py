"""Studio slice 1 (2026-10-19): ステージ結果キャッシュ(A)・妥当性フラグ(B)・入力参照の保存(C)。

A: 段ごとの結果をキャッシュし、ノブを動かした段とその後ろだけ再計算する。
B: ``ran`` / ``valid`` / ``reasons`` を分けて持つ。Studio は報告するだけで、op の数値問題を直さない。
C: プロジェクト保存が入力画像の参照(path / sha256 / shape / dtype)を持つ。
"""
import hashlib
import json
import os

import numpy as np
import pytest

import api
import studio

_OPS4 = ["gaussian", "sobel_amp", "invert", "otsu"]


def _counting(monkeypatch, names):
    """``ops.RT`` の各 op を呼び出し回数つきの包みに差し替える(本物の計算はそのまま)。"""
    counts = {n: 0 for n in names}
    for n in names:
        real = api._ops.RT[n]

        def wrap(v, a, b, _real=real, _n=n):
            counts[_n] += 1
            return _real(v, a, b)
        monkeypatch.setitem(api._ops.RT, n, wrap)
    return counts


def _app():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _model4():
    m = studio.PipelineModel(studio.demo_image(48))
    for n in _OPS4:
        m.add_stage(n, 0.4, 0.5)
    return m


# ------------------------------- A: cache -------------------------------- #
def test_a1_knob_change_recomputes_only_from_that_stage(monkeypatch):
    m = _model4()
    counts = _counting(monkeypatch, _OPS4)
    m.result_upto(3)
    assert counts == {n: 1 for n in _OPS4}
    m.set_knobs(2, a=0.7)
    m.result_upto(3)
    assert counts == {"gaussian": 1, "sobel_amp": 1, "invert": 2, "otsu": 2}
    assert m.cache_status() == ["cached", "cached", "computed", "computed"]
    m.result_upto(3)                                   # nothing changed: all served from cache
    assert counts == {"gaussian": 1, "sobel_amp": 1, "invert": 2, "otsu": 2}
    assert m.cache_status() == ["cached"] * 4
    assert m.last_cache_hits == (True, True, True, True)


def test_a1b_set_knobs_on_stage0_recomputes_everything(monkeypatch):
    m = _model4()
    counts = _counting(monkeypatch, _OPS4)
    m.result_upto(3)
    m.set_knobs(0, b=0.2)
    m.result_upto(3)
    assert counts == {"gaussian": 2, "sobel_amp": 2, "invert": 2, "otsu": 2}


def test_a1c_step_states_and_times_are_one_forward_walk(monkeypatch):
    m = _model4()
    counts = _counting(monkeypatch, _OPS4)
    st = m.step_states()
    tm = m.step_times()
    assert len(st) == 4
    assert tm
    assert counts == {n: 1 for n in _OPS4}              # O(n): each stage ran exactly once
    assert all(isinstance(t, float) for t in tm)


def test_a2_cached_equals_fresh_bit_identical():
    img = studio.demo_image(64)
    ops = ["gaussian", "sobel_amp", "invert", "gaussian", "otsu"]
    m = studio.PipelineModel(img)
    for n in ops:
        m.add_stage(n, 0.3, 0.5)
    m.result_upto(4)
    m.set_knobs(1, a=0.6)
    m.set_knobs(3, a=0.8, b=0.4)
    cached = m.result_upto(4)
    fresh = studio.PipelineModel(img)
    fresh.stages = [list(s) for s in m.stages]
    ref = fresh.result_upto(4)
    assert np.array_equal(cached, ref)
    for i in range(5):                                  # every intermediate too
        assert np.array_equal(m.result_upto(i), fresh.result_upto(i))
    assert np.array_equal(ref, api.run_pipeline(img, [tuple(s) for s in m.stages]))


def test_a3_set_image_invalidates_everything(monkeypatch):
    m = _model4()
    counts = _counting(monkeypatch, _OPS4)
    m.result_upto(3)
    m.set_image(studio.demo_image(48) * 0.5)
    m.result_upto(3)
    assert counts == {n: 2 for n in _OPS4}
    assert m.cache_status() == ["computed"] * 4


def test_a4_move_stage_invalidates_from_min_index(monkeypatch):
    m = _model4()
    m.stages = [["gaussian", 0.4, 0.5], ["gaussian", 0.5, 0.5], ["invert", 0.4, 0.5],
                ["invert", 0.5, 0.5]]
    counts = _counting(monkeypatch, ["gaussian", "invert"])
    m.result_upto(3)
    assert counts == {"gaussian": 2, "invert": 2}
    m.move_stage(3, 2)                                 # swaps the two invert stages
    m.result_upto(3)
    assert m.cache_status() == ["cached", "cached", "computed", "computed"]
    assert counts == {"gaussian": 2, "invert": 4}
    m.move_stage(1, 0)                                 # from index 0
    m.result_upto(3)
    assert m.cache_status() == ["computed"] * 4


def test_a4b_other_edits_invalidate_from_the_affected_index():
    m = _model4()
    m.result_upto(3)
    m.remove_stage(2)
    m.result_upto(2)
    assert m.cache_status() == ["cached", "cached", "computed"]
    j = m.duplicate_stage(0)
    m.result_upto(j + 2)
    assert m.cache_status()[0] == "cached"
    assert m.cache_status()[1] == "computed"
    m.load_recipe(next(iter(studio.recipes.names())))
    assert m.cache_len() == 0


def test_a5_failing_stage_does_not_poison_earlier_stages(monkeypatch):
    monkeypatch.setenv("FULLSEYE_ON_ERROR", "raise")    # the facade would otherwise fall back silently
    m = _model4()

    def boom(v, a, b):
        raise RuntimeError("boom in invert")
    m.result_upto(1)
    monkeypatch.setitem(api._ops.RT, "invert", boom)
    with pytest.raises(RuntimeError) as e1:
        m.result_upto(3)
    with pytest.raises(RuntimeError) as e2:
        m.result_upto(3)
    assert "boom in invert" in str(e1.value) and str(e1.value) == str(e2.value)
    assert m.cache_len() == 2                           # stages 0 and 1 survived
    ok = m.result_upto(1)
    assert isinstance(ok, np.ndarray)
    assert m.cache_status()[:2] == ["cached", "cached"]
    states = m.step_states()
    assert [s["state"]["kind"] == "error" for s in states] == [False, False, True, True]
    assert [s["state"].get("ran") for s in states] == [True, True, False, False]


def test_a6_cache_does_not_grow_on_repeated_knob_drags():
    m = _model4()
    m.result_upto(3)
    for k in range(50):
        m.set_knobs(2, a=0.2 + 0.01 * k)
        m.result_upto(3)
        assert m.cache_len() <= len(m.stages)
    assert m.cache_len() == 4


def test_a7_direct_stage_list_mutation_cannot_serve_stale_results():
    m = _model4()
    m.result_upto(3)
    m.stages[1][1] = 0.9                               # bypasses set_knobs on purpose
    fresh = studio.PipelineModel(studio.demo_image(48))
    fresh.stages = [list(s) for s in m.stages]
    assert np.array_equal(m.result_upto(3), fresh.result_upto(3))
    assert m.cache_status() == ["cached", "computed", "computed", "computed"]


def test_a8_policy_change_is_part_of_the_key(monkeypatch):
    m = _model4()
    counts = _counting(monkeypatch, _OPS4)
    m.result_upto(3)
    monkeypatch.setenv("FULLSEYE_ON_ERROR", "raise")
    m.result_upto(3)
    assert counts == {n: 2 for n in _OPS4}


# --------------------------- B: validity flag ---------------------------- #
def _nan_invert(monkeypatch):
    real = api._ops.RT["invert"]

    def nan_invert(v, a, b):
        out = np.array(real(v, a, b), dtype=np.float64)
        out[0, :3] = np.nan
        return out
    monkeypatch.setitem(api._ops.RT, "invert", nan_invert)


def test_b1_plain_arrays_are_judged_only_when_clearly_bad():
    ok = np.linspace(0, 1, 16).reshape(4, 4)
    assert studio.assess_validity(ok) == (None, [])            # no information: never "OK"
    bad = ok.copy()
    bad[0, :2] = np.nan
    bad[1, 0] = np.inf
    v, why = studio.assess_validity(bad)
    assert v is False and any("3 non-finite" in w for w in why)
    v, why = studio.assess_validity(np.full((4, 4), 0.5))
    assert v is False and any("constant" in w for w in why)
    v, why = studio.assess_validity(np.zeros((0, 3)))
    assert v is False and any("empty" in w for w in why)
    assert studio.assess_validity(np.ones((5, 5)) > 0.5)[0] is None   # an all-ones region is not a verdict


@pytest.mark.parametrize("key,bad,good", [
    ("converged", False, True),
    ("valid", False, True),
    ("guf_valid", np.array([False]), np.array([True])),
    ("ok", False, True),
    ("success", False, True),
])
def test_b2_explicit_validity_keys_are_wired(key, bad, good):
    v, why = studio.assess_validity({key: bad, "x": 1.0})
    assert v is False and why and key in " ".join(why)
    assert studio.assess_validity({key: good, "x": 1.0}) == (True, [])


def test_b2b_status_and_iteration_limit_and_reasons():
    assert studio.assess_validity({"status": "max_iter"})[0] is False
    assert studio.assess_validity({"status": "diverged"})[0] is False
    assert studio.assess_validity({"status": "converged"}) == (True, [])
    assert studio.assess_validity({"status": "primary", "value": "x"}) == (None, [])   # a source tag, not a verdict
    v, why = studio.assess_validity({"n_iter": 50, "max_iter": 50})
    assert v is False and "max_iter" in " ".join(why)
    assert studio.assess_validity({"n_iter": 12, "max_iter": 50}) == (None, [])
    v, why = studio.assess_validity({"guf_valid": np.array([False]), "invalid_reasons": ["stationary_point"]})
    assert v is False and "stationary_point" in " ".join(why)
    v, why = studio.assess_validity({"valid": np.zeros((3, 3), bool)})            # a mask with no valid entry
    assert v is False
    assert studio.assess_validity({"valid": np.array([[True, False]])}) == (None, [])
    v, why = studio.assess_validity({"converged": True, "ok": False})             # False wins
    assert v is False
    assert studio.assess_validity({}) == (None, [])


def test_b3_step_states_keep_ran_valid_reasons_separate(monkeypatch):
    clean = _model4()
    cs = clean.step_states()
    assert len(cs) == 4
    assert all(s["state"]["ran"] is True for s in cs)
    assert all(s["state"]["valid"] is None and s["state"]["reasons"] == [] for s in cs[:2])
    _nan_invert(monkeypatch)
    m = _model4()
    ms = m.step_states()
    assert ms[1]["state"]["valid"] is None
    assert ms[2]["state"]["ran"] is True and ms[2]["state"]["valid"] is False
    assert len(ms[2]["state"]["reasons"]) == 1
    assert any("non-finite" in r for r in ms[2]["state"]["reasons"])
    assert ms[2]["state"]["kind"] != "error"            # a warning, not an error


def test_b4_nonfinite_is_never_blanked_in_table_text():
    txt = studio._describe_value(np.array([1.0, np.nan, 3.0, np.inf]))
    assert "2 non-finite" in txt
    assert "non-finite" in studio._describe_value(np.array([np.nan, np.nan]))
    d = studio.inspect_result({"t": np.array([0.5, np.nan])})
    assert "1 non-finite" in d["fields"]["t"]


def test_b5_problems_and_status_offscreen(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    _app()
    _nan_invert(monkeypatch)
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for n in _OPS4:
        model.add_stage(n, 0.4, 0.5)
    win._refresh_stage_list()
    probs = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    warn = [t for t in probs if t.startswith("⚠")]
    assert len(warn) == 1 and "stage 3 (invert)" in warn[0] and "non-finite" in warn[0]
    assert not any(t.startswith("✕") for t in probs)
    tip = win._stage_list.item(2).toolTip()
    assert "non-finite" in tip
    assert "⚠" in win._stage_list.item(2).text()
    assert "⚠" not in win._stage_list.item(0).text()
    win._do_run_all()
    msg = win.statusBar().currentMessage()
    assert "needs review" not in msg and "validity not judged" in msg   # only the final output is judged
    # run the NaN stage as the end of the pipeline
    model.remove_stage(3)
    win._refresh_stage_list()
    win._do_run_all()
    msg = win.statusBar().currentMessage()
    assert "Result: needs review" in msg and "non-finite" in msg
    monkeypatch.setitem(studio._UI_LANG, "code", "ja")
    win._do_run_all()
    assert "実行: 完了 / 結果: 要確認" in win.statusBar().currentMessage()
    win.close()


def test_b6_clean_pipeline_has_no_warning_rows_and_says_not_judged():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for n in ("gaussian", "sobel_amp"):
        model.add_stage(n, 0.4, 0.5)
    win._refresh_stage_list()
    probs = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert probs == ["no problems"]
    win._do_run_all()
    msg = win.statusBar().currentMessage()
    assert "validity not judged" in msg
    assert "OK" not in msg
    marks = [win._stage_list.item(i).text() for i in range(2)]
    assert len(marks) == 2
    assert all(("cache" in t or "calc" in t) for t in marks)
    win.close()


# ------------------------- C: input reference ---------------------------- #
def _write_image(path, seed=0):
    import imgio
    rng = np.random.default_rng(seed)
    arr = rng.random((12, 10))
    imgio.save(str(path), arr)
    return arr


def test_c1_roundtrip_with_tmp_path(tmp_path):
    p = tmp_path / "in.png"
    _write_image(p)
    m = studio.PipelineModel(studio.demo_image(16))
    m.add_stage("gaussian")
    m.input_path = str(p)
    d = m.to_dict()
    ref = d["input"]
    assert ref["path"] == str(p)
    assert ref["sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert ref["shape"] == [16, 16] and ref["dtype"] == "float64"
    d2 = json.loads(json.dumps(d))
    m2 = studio.PipelineModel(studio.demo_image(16))
    m2.load_dict(d2)
    assert m2.input_ref == ref
    res = studio.resolve_input_ref(m2.input_ref, str(tmp_path))
    assert res["status"] == "ok" and res["path"] == str(p) and res["message"] == ""


def test_c2_changed_file_is_a_nonfatal_warning(tmp_path):
    p = tmp_path / "in.png"
    _write_image(p, 0)
    ref = studio.input_reference(str(p), np.zeros((12, 10)))
    _write_image(p, 1)
    res = studio.resolve_input_ref(ref, str(tmp_path))
    assert res["status"] == "changed" and res["path"] == str(p)
    assert "input file changed since save" in res["message"]


def test_c3_missing_file_message(tmp_path):
    ref = {"path": str(tmp_path / "gone" / "in.png"), "sha256": "0" * 64, "shape": [2, 2], "dtype": "float64"}
    res = studio.resolve_input_ref(ref, str(tmp_path))
    assert res["status"] == "missing" and res["path"] is None
    assert res["message"] == "input not found: %s" % ref["path"]


def test_c4_relink_by_basename_next_to_the_json(tmp_path):
    orig = tmp_path / "old_place" / "in.png"
    orig.parent.mkdir()
    _write_image(orig)
    ref = studio.input_reference(str(orig), np.zeros((12, 10)))
    new_dir = tmp_path / "project"
    new_dir.mkdir()
    (new_dir / "in.png").write_bytes(orig.read_bytes())
    orig.unlink()
    res = studio.resolve_input_ref(ref, str(new_dir))
    assert res["status"] == "relinked" and res["path"] == str(new_dir / "in.png")
    assert "relinked" in res["message"]
    (new_dir / "in.png").write_bytes(b"different bytes")        # candidate exists but differs
    res = studio.resolve_input_ref(ref, str(new_dir))
    assert res["status"] == "changed" and "changed" in res["message"]


def test_c5_legacy_dict_loads_exactly_as_before():
    m = studio.PipelineModel(studio.demo_image(16))
    m.add_stage("gaussian")
    assert "input" not in m.to_dict()                          # no input_path -> byte-identical file
    legacy = {"fullseye_pipeline": 1, "stages": [["gaussian", 0.2, 0.3]]}
    m.load_dict(legacy)
    assert m.stages == [["gaussian", 0.2, 0.3]] and m.input_ref is None
    m.load_dict({"fullseye_pipeline": 1, "stages": [["gaussian", 0.2, 0.3]], "input": "garbage"})
    assert m.input_ref is None                                  # malformed reference: ignored, not fatal


def test_c6_open_pipe_offscreen_reports_in_problems(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    _app()
    p = tmp_path / "in.png"
    _write_image(p, 0)
    ref = studio.input_reference(str(p), np.zeros((12, 10)))
    spec = {"fullseye_pipeline": 1, "stages": [["gaussian", 0.2, 0.3]], "input": ref}
    pj = tmp_path / "proj.json"
    pj.write_text(json.dumps(spec), encoding="utf-8")
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(16)))
    win._open_pipe_path(str(pj))
    assert model.image.shape == (12, 10)                       # reloaded silently
    texts = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert texts == ["no problems"]
    _write_image(p, 1)                                         # now it differs
    win._open_pipe_path(str(pj))
    texts = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert texts
    assert any(t.startswith("⚠") and "input file changed since save" in t for t in texts)
    p.unlink()
    keep = model.image
    win._open_pipe_path(str(pj))
    texts = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert texts
    assert any("input not found: %s" % p in t for t in texts)
    assert model.image is keep                                 # kept the current image
    win.close()
