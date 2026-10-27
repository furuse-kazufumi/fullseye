"""Studio slice 3 (2026-10-20): 値を並べて試す・A を固定して B と比べる・拡大の同期。

A: 選んだ段のノブの前後の値 3 (or 5) 通りを、キャッシュした前段の結果から、その段だけ走らせて並べる帯。
B: 「A として固定」(凍結した読み取り専用の結果)と、生きている結果 B を、並べる / スワイプ / 点滅 / 差で見る。
C: 拡大・移動・カーソル位置を、複数のビューで同期する(ViewSyncGroup)。
"""
import json

import numpy as np
import pytest

import api
import imgio
import studio

_OPS3 = ["sobel_amp", "gaussian", "invert"]


@pytest.fixture(autouse=True)
def _restore_ui_language():
    """``studio._UI_LANG["code"] = "ja"`` を直接書く試験があるので、終わりに元へ戻す(プロセス全体の状態)。"""
    prev = studio._UI_LANG["code"]
    yield
    studio._UI_LANG["code"] = prev


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


def _model3():
    m = studio.PipelineModel(studio.demo_image(48))
    for n in _OPS3:
        m.add_stage(n, 0.4, 0.5)
    return m


def _window3():
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for n in _OPS3:
        model.add_stage(n, 0.4, 0.5)
    model.step_states()                                   # run first: the list rebuild itself never computes
    win._refresh_stage_list(select=1)                     # stage 2 = gaussian, whose a is σ in px
    return win, model


@pytest.fixture(autouse=True)
def _no_modal_confirm(monkeypatch):
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda parent, title, text: True)
    yield
    studio._UI_LANG["code"] = "en"


def _spec(op, letter="a"):
    return studio.param_specs.spec_for(op)[letter]


# ------------------------------ A: candidate values ------------------------------ #
def test_a1_continuous_candidates_step_around_the_current_and_stay_in_range():
    sp = _spec("gaussian")                                # σ 0.3 .. 3.0 px, step 0.01
    c = studio.knob_candidates(sp, 0.4, 3)
    assert len(c) == 3 and [x["current"] for x in c] == [False, True, False]
    disp = [studio.param_specs.knob_to_display(sp, x["knob"]) for x in c]
    assert disp[1] == pytest.approx(0.3 + 0.4 * 2.7)
    assert disp[1] - disp[0] == pytest.approx(disp[2] - disp[1])
    assert disp[2] - disp[1] == pytest.approx(0.27)       # 1/10 of the 2.7 range (larger than the 0.01 step)
    assert c[1]["knob"] == 0.4 and "px" in c[1]["text"]
    assert len(studio.knob_candidates(sp, 0.4, 5)) == 5
    for k in (0.0, 0.02, 1.0, 0.97):                      # at the ends the window slides back in, never out
        for n in (3, 5):
            cc = studio.knob_candidates(sp, k, n)
            assert len(cc) == n
            assert all(0.0 <= x["knob"] <= 1.0 for x in cc)
            assert any(x["current"] for x in cc)
            assert [x["knob"] for x in cc] == sorted(x["knob"] for x in cc)
    assert studio.knob_candidates(sp, 0.0, 3)[0]["knob"] == 0.0


def test_a1b_log_choice_int_bool_unused_candidates():
    log = dict(studio.param_specs.GENERIC_FLOAT, min=0.1, max=100.0, map="log", step=0.01)
    c = studio.knob_candidates(log, 0.5, 3)
    d = [studio.param_specs.knob_to_display(log, x["knob"]) for x in c]
    assert d[1] / d[0] == pytest.approx(d[2] / d[1])      # geometric spacing, not arithmetic
    assert d[1] / d[0] == pytest.approx(1000 ** 0.1)
    ch = _spec("median")                                  # kernel 3 5 7 9
    cur = studio.param_specs.display_to_knob(ch, 1)
    c = studio.knob_candidates(ch, cur, 3)
    assert [x["text"] for x in c] == ["3 px", "5 px", "7 px"] and c[1]["current"]
    c0 = studio.knob_candidates(ch, studio.param_specs.display_to_knob(ch, 0), 3)
    assert [x["text"] for x in c0] == ["3 px", "5 px", "7 px"]       # the first choice: the window slides, no 'index -1'
    assert len(studio.knob_candidates(ch, cur, 5)) == 4            # only four kernels exist: never invented values
    it = [v for v in studio.param_specs.PARAM_SPECS.values() if v.get("a", {}).get("kind") == "int"][0]["a"]
    ci = studio.knob_candidates(it, 0.5, 3)
    shown = [studio.param_specs.knob_to_display(it, x["knob"]) for x in ci]
    assert shown == sorted(set(shown)) and all(it["min"] <= v <= it["max"] for v in shown)
    bools = [sp[k] for sp in studio.param_specs.PARAM_SPECS.values() for k in "ab" if sp.get(k, {}).get("kind") == "bool"]
    assert bools, "no bool knob spec found: the bool case would be untested"
    bo = bools[0]
    cb = studio.knob_candidates(bo, 0.0, 3)
    assert [x["current"] for x in cb] == [True, False] and len(cb) == 2
    assert studio.knob_candidates(_spec("otsu"), 0.5, 3) == []       # an unused knob has nothing to try


def test_a2_variants_run_only_the_stage_from_the_cached_prefix(monkeypatch):
    m = _model3()
    m.step_states()
    counts = _counting(monkeypatch, _OPS3)
    before_len, before_status = m.cache_len(), list(m.cache_status())
    cands = studio.knob_candidates(_spec("gaussian"), 0.4, 3)
    res = m.run_variants(1, "a", [c["knob"] for c in cands])
    assert counts == {"sobel_amp": 0, "gaussian": 3, "invert": 0}    # 3 candidates = exactly 3 runs of stage 2's op
    assert [e for _v, e in res] == [None, None, None]
    assert m.cache_len() == before_len and m.cache_status() == before_status
    assert m.stages[1][1] == 0.4                                      # the user's pipeline is untouched
    cur = m.result_upto(1)
    assert np.array_equal(res[1][0], cur)                             # the middle one IS the current result
    assert not np.array_equal(res[0][0], res[2][0])
    ref = studio.PipelineModel(m.image)                               # and each one equals a fresh full run
    for k in (0, 2):
        ref.stages = [["sobel_amp", 0.4, 0.5], ["gaussian", cands[k]["knob"], 0.5], ["invert", 0.4, 0.5]]
        assert np.array_equal(res[k][0], ref.result_upto(1))
    m.set_bypass(1, True)
    with pytest.raises(ValueError):
        m.run_variants(1, "a", [0.5])
    with pytest.raises(IndexError):
        m.run_variants(7, "a", [0.5])


def test_a2b_a_failing_candidate_does_not_blank_the_others():
    m = _model3()
    res = m.run_variants(1, "a", [0.4, float("nan"), 0.6])
    assert res[0][1] is None and res[2][1] is None and res[1][0] is None and res[1][1] is not None


def test_a3_apply_display_range_stretches_before_the_mode():
    v = np.linspace(2.0, 6.0, 16).reshape(4, 4)
    g = studio.apply_display(v, "gray", vmin=2.0, vmax=6.0)
    assert g.min() == pytest.approx(0.0) and g.max() == pytest.approx(1.0)
    assert np.array_equal(studio.apply_display(v, "gray"), v)         # without a range: exactly as before
    reg = (np.arange(16).reshape(4, 4) % 2).astype(float)
    base = np.full((4, 4), 0.3)
    a = studio.apply_display(reg, "region overlay", base=base, vmin=0.0, vmax=9.0)
    b = studio.apply_display(reg, "region overlay", base=base)
    assert np.array_equal(a, b)                                       # a region is not stretched out of being a region
    assert studio.shared_display_range(np.array([1.0, 3.0]), np.array([[-2.0, np.nan]]), "x", None) == (-2.0, 3.0)
    assert studio.shared_display_range(np.full((2, 2), 0.5)) == (0.5, 1.5)
    assert studio.shared_display_range("x", None) is None


def test_a4_strip_is_lazy_shares_one_display_range_and_keeps_only_small_pixmaps(monkeypatch):
    from PySide6 import QtGui
    win, model = _window3()
    counts = _counting(monkeypatch, _OPS3)
    strip = win._strip
    assert not strip["toggle"].isChecked() and strip["body"].isHidden()
    model.set_knobs(1, a=0.45)
    strip["refresh"]()                                                # collapsed: nothing is computed
    assert counts == {"sobel_amp": 0, "gaussian": 0, "invert": 0}
    calls = []
    real = studio.apply_display

    def rec(val, mode, base=None, draw=None, vmin=None, vmax=None):
        calls.append((np.asarray(val).shape, vmin, vmax))
        return real(val, mode, base=base, draw=draw, vmin=vmin, vmax=vmax)
    model.step_states()
    base_counts = dict(counts)
    cands = studio.knob_candidates(_spec("gaussian"), 0.45, 3)
    expect = studio.shared_display_range(*[v for v, _e in model.run_variants(1, "a", [c["knob"] for c in cands])])
    counts.update(base_counts)
    n_cache = model.cache_len()
    monkeypatch.setattr(studio, "apply_display", rec)
    strip["toggle"].setChecked(True)                                  # expanding is what computes
    after = {k: counts[k] - base_counts[k] for k in counts}
    assert after == {"sobel_amp": 0, "gaussian": 3, "invert": 0}
    assert len(calls) == 3 and len({(c[1], c[2]) for c in calls}) == 1
    assert (calls[0][1], calls[0][2]) == expect and calls[0][1] is not None
    assert model.cache_len() == n_cache
    th = strip["thumbs"]
    assert len(th) == 3 and all(isinstance(p, QtGui.QPixmap) and not p.isNull() for p in th)
    assert all(p.width() <= 160 and p.height() <= 120 for p in th)   # small pixmaps only
    assert not any(isinstance(v, np.ndarray) and v.size > 1000 for v in vars(win).get("_strip", {}).values())
    assert len(strip["values"]) == 3 and sum(1 for x in strip["values"] if x["current"]) == 1
    strip["count"].setCurrentIndex(strip["count"].findData(5))
    assert len(strip["thumbs"]) == 5


def test_a5_roi_renders_only_that_rectangle(monkeypatch):
    win, model = _window3()
    strip = win._strip
    strip["toggle"].setChecked(True)
    win._set_roi((4, 6, 36, 30))                                      # x0, y0, x1, y1 (image pixels)
    assert win._state["roi"] == (4, 6, 36, 30)
    calls = []
    real = studio.apply_display

    def rec(val, mode, base=None, draw=None, vmin=None, vmax=None):
        calls.append(np.asarray(val).shape)
        return real(val, mode, base=base, draw=draw, vmin=vmin, vmax=vmax)
    monkeypatch.setattr(studio, "apply_display", rec)
    strip["refresh"]()
    assert calls == [(24, 32)] * 3                                    # 24 rows x 32 columns, not the 48 x 48 frame
    win._set_roi(None)
    calls.clear()
    strip["refresh"]()
    assert calls == [(48, 48)] * 3
    win._set_roi((0, 0, 1, 1))                                        # a 1-pixel box is not a region: ignored
    assert win._state["roi"] is None


def test_a5b_shift_drag_on_the_main_view_sets_the_roi():
    from PySide6 import QtCore, QtGui
    win, model = _window3()
    view = win._main_view
    view.resize(400, 300)
    view.fit()
    P = QtCore.QPointF

    def ev(t, x, y, btn, mods):
        return QtGui.QMouseEvent(t, P(x, y), P(x, y), P(x, y), btn, btn, mods)
    L, S = QtCore.Qt.LeftButton, QtCore.Qt.ShiftModifier
    view.mousePressEvent(ev(QtCore.QEvent.MouseButtonPress, 100, 80, L, S))
    view.mouseMoveEvent(ev(QtCore.QEvent.MouseMove, 220, 200, L, S))
    view.mouseReleaseEvent(ev(QtCore.QEvent.MouseButtonRelease, 220, 200, L, S))
    x0, y0, x1, y1 = win._state["roi"]
    assert 0 <= x0 < x1 <= 48 and 0 <= y0 < y1 <= 48
    p0, p1 = view.mapToScene(100, 80), view.mapToScene(220, 200)
    assert abs(x0 - int(p0.x())) <= 1 and abs(y1 - int(p1.y())) <= 1
    view.mousePressEvent(ev(QtCore.QEvent.MouseButtonPress, 100, 80, L, S))      # a Shift+click clears it
    view.mouseReleaseEvent(ev(QtCore.QEvent.MouseButtonRelease, 100, 80, L, S))
    assert win._state["roi"] is None


def test_a6_choosing_a_candidate_changes_nothing_adopt_applies_it_through_the_knob_path():
    win, model = _window3()
    studio._UI_LANG["code"] = "ja"
    strip = win._strip
    strip["toggle"].setChecked(True)
    vals = strip["values"]
    n_undo = len(win._undo_stack)
    assert all(not b.isEnabled() for b in strip["adopt"])             # nothing chosen yet
    strip["cells"][2].click()                                         # choose the third
    assert strip["chosen"] == 2 and model.stages[1][1] == 0.4
    assert len(win._undo_stack) == n_undo                             # clicking a picture changes nothing
    assert [b.isEnabled() for b in strip["adopt"]] == [False, False, True]
    strip["adopt"][2].click()
    assert model.stages[1][1] == vals[2]["knob"]
    assert len(win._undo_stack) == n_undo + 1                         # one undo entry, not one per tick
    lab = win._undo_stack[-1].label
    assert "σ" in lab and "変更" in lab
    win._undo()
    assert model.stages[1][1] == 0.4 and len(win._undo_stack) == n_undo
    assert strip["chosen"] is None


def test_a7_strip_says_why_it_is_empty_for_a_bypassed_stage_or_an_unused_knob():
    win, model = _window3()
    strip = win._strip
    strip["toggle"].setChecked(True)
    strip["which"].setCurrentIndex(strip["which"].findData("b"))      # gaussian's b is unused
    assert strip["thumbs"] == [] and strip["message"].text()
    strip["which"].setCurrentIndex(strip["which"].findData("a"))
    model.set_bypass(1, True)
    strip["refresh"]()
    assert strip["thumbs"] == [] and strip["message"].text()


# ------------------------------ B: pin A, compare B ------------------------------ #
def test_b1_pin_freezes_stages_output_and_validity_read_only():
    m = _model3()
    m.set_bypass(2, True)
    p = m.pin(note="before")
    assert [list(s) for s in p.stages] == [list(s) for s in m.stages]
    assert p.stages[2].bypass is True
    assert isinstance(p.array, np.ndarray) and p.array.flags.writeable is False
    assert np.array_equal(p.array, m.output()) and p.array is not m.output()
    assert p.note == "before" and p.kind == "image" and p.error is None
    m.stages[0][1] = 0.9                                              # editing the model does not touch the pin
    assert p.stages[0][1] == 0.4
    with pytest.raises(ValueError):
        p.array[0, 0] = 1.0
    assert studio.PipelineModel().pins == []
    with pytest.raises(ValueError):
        studio.PipelineModel().pin()


def test_b2_a_pinned_array_never_changes_when_the_pipeline_runs_again():
    m = _model3()
    p = m.pin()
    mine = p.array.copy()
    for a in (0.1, 0.9, 0.5):
        m.set_knobs(0, a=a)
        m.set_knobs(1, a=1 - a)
        m.output()
    m.image = studio.demo_image(48) * 0.5                             # even a new input image
    m.output()
    assert np.array_equal(p.array, mine) and p.array.flags.writeable is False
    m.set_bypass(1, True)
    m.output()
    assert np.array_equal(p.array, mine)


def test_b3_what_changed_lists_exactly_the_edits_in_order():
    studio._UI_LANG["code"] = "en"
    m = _model3()
    p = m.pin()
    assert m.diff_pin(p) == []                                        # nothing edited: nothing listed
    m.set_knobs(1, a=0.8)                                             # knob changed
    m.set_bypass(0, True)                                             # bypassed
    m.add_stage("otsu", 0.5, 0.5)                                     # added
    d = m.diff_pin(p)
    assert [(e["kind"], e["index"], e["op"]) for e in d] == [
        ("bypass", 1, "sobel_amp"), ("knob", 2, "gaussian"), ("added", 4, "otsu")]
    knob = d[1]
    assert knob["knob"] == "a" and knob["old"] == "1.38 px" and knob["new"] == "2.46 px"    # the knob's own unit
    assert "1.38 px" in knob["text"] and "2.46 px" in knob["text"] and "→" in knob["text"]
    m.remove_stage(3)
    m.remove_stage(2)                                                 # invert removed
    kinds = [(e["kind"], e["op"]) for e in m.diff_pin(p)]
    assert kinds == [("bypass", "sobel_amp"), ("knob", "gaussian"), ("removed", "invert")]
    m.set_bypass(0, False)
    m.set_knobs(1, a=0.4)
    assert [(e["kind"], e["op"]) for e in m.diff_pin(p)] == [("removed", "invert")]
    m.set_knobs(1, a=0.4 + 1e-15)
    assert [(e["kind"], e["op"]) for e in m.diff_pin(p)] == [("removed", "invert")]   # rounding dust is not an edit


def test_b3b_an_inserted_stage_does_not_make_the_later_stages_look_edited():
    m = _model3()
    p = m.pin()
    m.stages.insert(0, studio._normalise_stage(["invert", 0.5, 0.5]))
    d = m.diff_pin(p)
    assert [(e["kind"], e["index"], e["op"]) for e in d] == [("added", 1, "invert")]


def test_b3c_a_changed_input_is_listed_first(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    imgio.save(str(a), studio.demo_image(48))
    imgio.save(str(b), studio.demo_image(48) * 0.5)
    m = studio.PipelineModel(imgio.load(str(a)))
    m.input_path = str(a)
    m.add_stage("gaussian", 0.4, 0.5)
    p = m.pin()
    assert p.input["sha256"] == studio.file_sha256(str(a))
    m.set_image(imgio.load(str(b)))
    m.input_path = str(b)
    m.set_knobs(0, a=0.7)
    d = m.diff_pin(p)
    assert [e["kind"] for e in d] == ["input", "knob"]
    assert d[0]["old"] == "a.png" and d[0]["new"] == "b.png"
    m.set_image(imgio.load(str(a)))
    m.input_path = str(a)
    assert [e["kind"] for e in m.diff_pin(p)] == ["knob"]             # the same file again: not a change


def test_b4_pins_round_trip_without_arrays_and_old_files_load_as_before(tmp_path):
    m = _model3()
    m.set_bypass(2, True)
    p = m.pin(note="first", display={"mode": "gray"})
    plain = studio.PipelineModel(m.image)
    for n in _OPS3:
        plain.add_stage(n, 0.4, 0.5)
    assert "pinned" not in plain.to_dict()                            # key only when used
    d = m.to_dict()
    assert list(d["pinned"][0]) == ["stages", "input", "display", "note"]
    assert d["pinned"][0]["stages"][2] == ["invert", 0.4, 0.5, True]
    assert "array" not in json.dumps(d) and len(json.dumps(d)) < 2000
    f = tmp_path / "p.json"
    f.write_text(json.dumps(d), encoding="utf-8")
    m2 = studio.PipelineModel(m.image)
    m2.load_dict(json.loads(f.read_text(encoding="utf-8")))
    assert len(m2.pins) == 1 and m2.pins[0].note == "first" and m2.pins[0].display == {"mode": "gray"}
    assert np.array_equal(m2.pins[0].array, p.array) and m2.pins[0].array.flags.writeable is False
    assert m2.pins[0].stages[2].bypass is True and m2.pins[0].error is None
    old = studio.PipelineModel(m.image)
    old.load_dict({"fullseye_pipeline": 1, "stages": [["gaussian", 0.4, 0.5]]})
    assert old.pins == [] and len(old.stages) == 1
    m2.load_dict({"fullseye_pipeline": 1, "stages": [["gaussian", 0.4, 0.5]]})
    assert m2.pins == []                                              # the pins belong to the document that was replaced
    for bad in ({"stages": [], "pinned": "x"}, {"stages": [], "pinned": [3]},
                {"stages": [], "pinned": [{"stages": [["nope_op", 0.5, 0.5]]}]},
                {"stages": [], "pinned": [{"stages": []}] * 3}):
        with pytest.raises(ValueError):
            studio.validate_pinned(bad)
        keep = list(m2.stages)
        with pytest.raises(ValueError):
            m2.load_dict(bad)
        assert m2.stages == keep                                      # a bad file leaves the project untouched


def test_b4b_a_pin_that_cannot_be_recomputed_is_kept_with_the_reason(tmp_path):
    img = tmp_path / "x.png"
    imgio.save(str(img), studio.demo_image(48))
    m = studio.PipelineModel(imgio.load(str(img)))
    m.input_path = str(img)
    m.load_dict({"fullseye_pipeline": 1, "stages": [["gaussian", 0.4, 0.5]],
                 "pinned": [{"stages": [["gaussian", 0.4, 0.5]],
                             "input": {"path": "other.png", "sha256": "0" * 64}, "display": {}, "note": ""}]})
    assert len(m.pins) == 1 and m.pins[0].array is None and m.pins[0].error
    m.pins[0].input = None                                            # unknown input: recomputed from the current one
    m.recompute_pins()
    assert m.pins[0].array is not None and m.pins[0].error is None
    m.image = None
    m.recompute_pins()
    assert m.pins[0].array is None and m.pins[0].error


def test_b5_at_most_two_pins_the_oldest_is_dropped():
    m = _model3()
    p1 = m.pin(note="1")
    p2 = m.pin(note="2")
    assert m.last_dropped_pin is None and m.pins == [p1, p2]
    p3 = m.pin(note="3")
    assert m.last_dropped_pin is p1 and m.pins == [p2, p3]
    assert m.drop_pin(0) is p2 and m.pins == [p3]


def test_b6_difference_images_absolute_signed_ratio():
    a = np.full((6, 6), 0.2)
    b = np.full((6, 6), 0.6)
    b[0, 0] = 0.2                                                     # one pixel unchanged
    ab = studio.difference_image(a, b, "absolute")
    assert ab["image"].shape == (6, 6, 3) and ab["scale"] == pytest.approx(0.4)
    assert not np.allclose(ab["image"][0, 0], ab["image"][3, 3])
    up, down = studio.difference_image(a, b, "signed"), studio.difference_image(b, a, "signed")
    assert up["scale"] == pytest.approx(down["scale"]) == pytest.approx(0.4)
    cm = imgio.apply_cmap(np.array([[-1.0, 0.0, 1.0]]), name="coolwarm", vmin=-1.0, vmax=1.0)[0]
    assert np.allclose(up["image"][3, 3], cm[2], atol=1e-6) and np.allclose(down["image"][3, 3], cm[0], atol=1e-6)
    assert up["image"][3, 3][0] > up["image"][3, 3][2] and down["image"][3, 3][2] > down["image"][3, 3][0]
    assert np.allclose(up["image"][0, 0], cm[1], atol=1e-6)                       # zero: the neutral middle, in both
    assert np.allclose(down["image"][0, 0], cm[1], atol=1e-6)
    r = studio.difference_image(a, b, "ratio")
    assert r["scale"] == pytest.approx(np.log2(3.0))
    z = a.copy()
    z[2, 2] = 0.0
    rz = studio.difference_image(z, b, "ratio")                       # a = 0: no ratio, painted black, not inf
    assert np.isfinite(rz["image"]).all() and np.allclose(rz["image"][2, 2], 0.0)
    rgb = np.dstack([a, a, a])
    assert studio.difference_image(rgb, rgb * 0.5, "absolute")["image"].shape == (6, 6, 3)
    with pytest.raises(ValueError):
        studio.difference_image(a, np.zeros((5, 6)))
    with pytest.raises(ValueError):
        studio.difference_image(a, {"x": 1})
    with pytest.raises(ValueError):
        studio.difference_image(a, b, "nope")


def _pin_window():
    win, model = _window3()
    win._docks["ab"].show()
    win._actions["pin_a"].trigger()
    return win, model


def test_b7_pin_action_exists_and_the_dock_starts_hidden_and_empty():
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert win._docks["ab"].isHidden()
    assert "pin_a" in win._actions
    shortcuts = [a.shortcut().toString() for a in win._actions.values() if not a.shortcut().isEmpty()]
    assert len(shortcuts) == len(set(shortcuts)), "a shortcut is used twice"
    win._docks["ab"].show()
    win._ab["refresh"]()
    assert win._ab["a"].pixmap() is None and not win._ab["restore"].isEnabled()
    assert win._ab["changes"].count() == 0
    model.image = None
    win._actions["pin_a"].trigger()                                   # nothing to pin is a message, not a crash
    assert model.pins == []
    assert "no image" in win.statusBar().currentMessage()


def test_b8_panes_share_one_display_range_from_a_and_b(monkeypatch):
    win, model = _pin_window()
    ab = win._ab
    model.set_knobs(1, a=0.9)
    model.set_bypass(2, True)
    calls = []
    real = studio.apply_display

    def rec(val, mode, base=None, draw=None, vmin=None, vmax=None):
        calls.append((vmin, vmax))
        return real(val, mode, base=base, draw=draw, vmin=vmin, vmax=vmax)
    monkeypatch.setattr(studio, "apply_display", rec)
    ab["set_mode"]("side")
    ab["refresh"]()
    expect = studio.shared_display_range(model.pins[0].array, model.output())
    assert len(calls) == 2 and set(calls) == {expect} and expect[0] is not None
    assert not np.array_equal(model.pins[0].array, model.output())
    assert ab["a"].pixmap() is not None and ab["b"].pixmap() is not None
    assert ab["a"].pixmap().toImage() != ab["b"].pixmap().toImage()


def test_b9_modes_swipe_blink_difference_and_the_blink_timer_stops_when_hidden():
    win, model = _pin_window()
    ab = win._ab
    model.set_knobs(1, a=0.9)
    ab["refresh"]()
    ab["set_mode"]("swipe")
    ab["swipe"].setValue(50)
    full = ab["a"].pixmap().toImage()
    assert ab["b"].isHidden()                                         # one composite picture, not two panes
    ab["swipe"].setValue(100)
    assert ab["a"].pixmap().toImage() != full                         # the boundary moved
    ab["swipe"].setValue(0)
    only_b = ab["a"].pixmap().toImage()
    assert only_b != full
    for kind in ("absolute", "signed", "ratio"):
        ab["set_mode"]("diff")
        ab["diff_kind"].setCurrentIndex(ab["diff_kind"].findData(kind))
        assert ab["a"].pixmap() is not None
        assert ab["info"].text()
    ab["set_mode"]("blink")
    assert ab["timer"].interval() == 500 and ab["timer"].isActive()
    img0 = ab["a"].pixmap().toImage()
    ab["tick"]()
    assert ab["a"].pixmap().toImage() != img0                         # it flips between A and B
    ab["tick"]()
    assert ab["a"].pixmap().toImage() == img0
    win._docks["ab"].hide()
    assert not ab["timer"].isActive()                                 # a hidden dock does not keep a timer running
    win._docks["ab"].show()
    assert ab["timer"].isActive()
    ab["set_mode"]("side")
    assert not ab["timer"].isActive()


def test_b10_different_sizes_refuse_swipe_and_difference_but_side_by_side_works():
    win, model = _pin_window()
    ab = win._ab
    model.set_image(studio.demo_image(32))
    ab["set_mode"]("diff")
    ab["refresh"]()
    assert ab["a"].pixmap() is None and "size" in ab["info"].text().lower()
    ab["set_mode"]("side")
    assert ab["a"].pixmap() is not None and ab["b"].pixmap() is not None


def test_b11_changes_list_restore_adopt_and_keep_both():
    studio._UI_LANG["code"] = "en"
    win, model = _pin_window()
    ab = win._ab
    pin = model.pins[0]
    a_stages = [list(s) for s in pin.stages]
    model.set_knobs(1, a=0.8)
    model.set_bypass(0, True)
    model.add_stage("otsu", 0.5, 0.5)
    ab["refresh"]()
    rows = [ab["changes"].item(i).text() for i in range(ab["changes"].count())]
    assert len(rows) == 3 and "sobel_amp" in rows[0] and "1.38 px" in rows[1] and "2.46 px" in rows[1] \
        and "otsu" in rows[2]
    live = [list(s) for s in model.stages]
    n_undo = len(win._undo_stack)
    ab["restore"].click()                                             # A に戻す
    assert [list(s) for s in model.stages] == a_stages and not model.is_bypassed(0)
    assert len(win._undo_stack) == n_undo + 1
    assert np.array_equal(model.output(), pin.array)
    assert len(model.pins) == 1                                       # A stays pinned
    win._undo()
    assert [list(s) for s in model.stages] == live and model.is_bypassed(0)
    ab["keep"].click()                                                # 両方残す: B becomes the second pin
    assert len(model.pins) == 2 and model.pins[0] is pin
    assert [list(s) for s in model.pins[1].stages] == live and model.pins[1].stages[0].bypass
    ab["keep"].click()                                                # a third one drops the oldest, and says so
    assert len(model.pins) == 2 and model.pins[0] is not pin
    assert "dropped" in win.statusBar().currentMessage() or "破棄" in win.statusBar().currentMessage()
    n = len(model.pins)
    stages_now = [list(s) for s in model.stages]
    ab["adopt"].click()                                               # B を採用: A goes, the current stays
    assert len(model.pins) == n - 1 and [list(s) for s in model.stages] == stages_now


def test_b12_pins_survive_save_and_open_and_an_unrecomputable_pin_is_a_problem(tmp_path, monkeypatch):
    win, model = _pin_window()
    img = tmp_path / "in.png"
    imgio.save(str(img), studio.demo_image(48))
    proj = tmp_path / "p.json"
    proj.write_text(json.dumps({
        "fullseye_pipeline": 1, "stages": [["gaussian", 0.4, 0.5]],
        "input": {"path": "in.png", "sha256": studio.file_sha256(str(img))},
        "pinned": [{"stages": [["gaussian", 0.4, 0.5]], "input": {"path": "gone.png", "sha256": "0" * 64},
                    "display": {}, "note": ""}]}), encoding="utf-8")
    win._open_pipe_path(str(proj))
    assert len(model.pins) == 1 and model.pins[0].array is None
    txt = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert any("A を再計算できません" in t for t in txt), txt
    win._ab["refresh"]()
    assert win._ab["a"].pixmap() is None                              # no picture for A, a message instead
    good = tmp_path / "q.json"
    model.pins[0].input = None
    model.recompute_pins()
    d = model.to_dict()
    good.write_text(json.dumps(d), encoding="utf-8")
    win._open_pipe_path(str(good))
    assert len(model.pins) == 1 and model.pins[0].array is not None
    txt = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert not any("再計算できません" in t for t in txt)


# ------------------------------ C: synchronised views ------------------------------ #
def _views(n=3):
    from PySide6 import QtGui, QtWidgets, QtCore
    _app()
    V = studio._sync_view_class(QtWidgets, QtGui, QtCore)
    g = studio.ViewSyncGroup()
    vs = []
    for _ in range(n):
        v = V()
        v.resize(300, 220)
        v.show()
        pm = QtGui.QPixmap(200, 160)
        pm.fill(QtGui.QColor("#446688"))
        v.set_source(pm)
        g.add(v)
        vs.append(v)
    QtWidgets.QApplication.processEvents()
    return g, vs


def _wheel(view, delta, x=150, y=110):
    from PySide6 import QtCore, QtGui
    ev = QtGui.QWheelEvent(QtCore.QPointF(x, y), QtCore.QPointF(x, y), QtCore.QPoint(0, 0),
                           QtCore.QPoint(0, delta), QtCore.Qt.NoButton, QtCore.Qt.NoModifier,
                           QtCore.Qt.NoScrollPhase, False)
    view.wheelEvent(ev)


def _move(view, x, y):
    from PySide6 import QtCore, QtGui
    P = QtCore.QPointF(x, y)
    view.mouseMoveEvent(QtGui.QMouseEvent(QtCore.QEvent.MouseMove, P, P, P, QtCore.Qt.NoButton,
                                          QtCore.Qt.NoButton, QtCore.Qt.NoModifier))


def test_c1_zoom_in_one_pane_replays_scale_and_scroll_offsets_in_the_others():
    g, (v1, v2, v3) = _views()
    assert len(g.members) == 3
    t0 = v1.transform().m11()
    for _ in range(3):
        _wheel(v1, 120, 60, 40)
    assert v1.transform().m11() > t0 * 1.9
    for v in (v2, v3):
        assert v.transform().m11() == v1.transform().m11() and v.transform().m22() == v1.transform().m22()
        assert v.horizontalScrollBar().value() == v1.horizontalScrollBar().value()
        assert v.verticalScrollBar().value() == v1.verticalScrollBar().value()
    assert v1.horizontalScrollBar().maximum() > 0
    v2.horizontalScrollBar().setValue(v2.horizontalScrollBar().value() // 2 + 7)   # a pan in another pane
    assert v1.horizontalScrollBar().value() == v2.horizontalScrollBar().value() == v3.horizontalScrollBar().value()
    _wheel(v3, -120, 100, 100)                                        # and zooming out from the third
    assert v1.transform().m11() == v3.transform().m11() == v2.transform().m11()


def test_c2_hover_puts_a_crosshair_at_the_same_image_coordinate_in_the_others():
    g, (v1, v2, v3) = _views()
    _wheel(v1, 120, 150, 110)
    _move(v1, 90, 70)
    p = v1.mapToScene(90, 70)
    assert v1.crosshair_pos() is None                                 # the pane you are in has its own cursor
    for v in (v2, v3):
        assert v.crosshair_pos() == (p.x(), p.y())
    _move(v2, 140, 100)
    q = v2.mapToScene(140, 100)
    assert v1.crosshair_pos() == (q.x(), q.y()) and v2.crosshair_pos() is None
    from PySide6 import QtCore
    v1.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
    assert v2.crosshair_pos() is None and v3.crosshair_pos() is None


def test_c3_removing_a_member_stops_the_replay():
    g, (v1, v2, v3) = _views()
    g.remove(v2)
    assert v2 not in g.members and len(g.members) == 2
    before = v2.transform().m11()
    _wheel(v1, 120)
    assert v2.transform().m11() == before != v1.transform().m11()
    assert v3.transform().m11() == v1.transform().m11()
    _move(v1, 80, 60)
    assert v2.crosshair_pos() is None and v3.crosshair_pos() is not None
    _wheel(v2, -120)                                                  # and the departed one no longer drives the others
    assert v1.transform().m11() == v3.transform().m11() != v2.transform().m11()


def test_c4_one_wheel_event_is_exactly_one_set_transform_on_each_other_member():
    g, (v1, v2, v3) = _views()
    calls = {id(v): 0 for v in (v1, v2, v3)}
    for v in (v1, v2, v3):
        orig = v.setTransform

        def counted(*a, _o=orig, _k=id(v), **k):
            calls[_k] += 1
            return _o(*a, **k)
        v.setTransform = counted
    _wheel(v1, 120, 70, 50)
    assert calls[id(v2)] == 1 and calls[id(v3)] == 1                  # no feedback loop, no double replay
    assert calls[id(v1)] == 0                                         # the source did its own scale itself
    _wheel(v1, 120, 70, 50)
    assert calls[id(v2)] == 2 and calls[id(v3)] == 2
    v1.horizontalScrollBar().setValue(v1.horizontalScrollBar().value() + 5)   # a pan replays offsets only
    assert calls[id(v2)] == 2


def test_c5_the_window_syncs_stage_in_out_the_ab_panes_and_optionally_the_main_view():
    win, model = _pin_window()
    g = win._sync_group
    cmp_ = win._compare
    members = g.members
    for v in (cmp_["left"], cmp_["right"], win._ab["a"], win._ab["b"]):
        assert v in members
    assert win._main_view not in members
    win._ab["sync_main"].setChecked(True)
    assert win._main_view in g.members
    win._ab["sync_main"].setChecked(False)
    assert win._main_view not in g.members
    cmp_["left"].resize(300, 220)
    cmp_["right"].resize(300, 220)
    win._docks["compare"].show()
    win._stage_list.setCurrentRow(2)
    assert cmp_["left"].pixmap() is not None and cmp_["right"].pixmap() is not None
    _wheel(cmp_["left"], 120, 100, 80)
    assert cmp_["right"].transform().m11() == cmp_["left"].transform().m11()
    assert win._ab["a"].transform().m11() == cmp_["left"].transform().m11()
