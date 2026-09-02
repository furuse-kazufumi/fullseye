"""Regression tests for the 2026-09-02 Studio logic review (findings F1-F11).

Drives ``build_window()`` offscreen with QSettings redirected to a temp dir and the
modal hooks stubbed, the same harness the reviewer's reproducers used."""
import json
import math
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import api
import studio


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    from PySide6 import QtCore, QtWidgets
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope,
                             str(tmp_path_factory.mktemp("qsettings")))
    a = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    studio.ERROR_HOOK = lambda *a: None
    studio.CONFIRM_HOOK = lambda *a: True
    return a


@pytest.fixture
def win(app):
    w, model = studio.build_window()
    w.show()
    model.set_image(studio.demo_image(64))
    yield w, model
    w._knob_timer.stop()
    w.close()


def _apply(win, text):
    ed = win._program["edit"]
    ed.setPlainText(text)
    win._program["apply"]()


def _status(win):
    return win._program["status"]().text()


# ----------------------------------------------------------------- F1 tuples
def test_f1_knob_after_apply_program_edits_model(app, win):
    w, model = win
    _apply(w, "gaussian (0.5, 0.5)\notsu (0.5, 0.5)")
    assert all(isinstance(s, list) for s in model.stages)
    w._step_to(1)
    w._state["dirty"] = False
    sa, _sb = w._knob_sliders
    sa.setValue(90)
    app.processEvents()
    assert model.stages[1][1] == pytest.approx(0.9)
    assert w._state["dirty"] is True


def test_f1_model_normalises_every_loader_to_lists():
    m = studio.PipelineModel(studio.demo_image(32))
    m.stages = [("gaussian", 0.4, 0.5), ("otsu", "0.5", 1)]
    assert m.stages == [["gaussian", 0.4, 0.5], ["otsu", 0.5, 1.0]]
    m.set_knobs(0, a=0.7)                                # no TypeError on a tuple
    assert m.stages[0] == ["gaussian", 0.7, 0.5]


# ----------------------------------------------------------------- F2 line map
def test_f2_breakpoint_and_cursor_use_editor_lines_with_directives(app, win):
    w, model = win
    prog = ("set_system ('thread_num', 0)\ndev_set_color ('cyan')\n"
            "gaussian (0.4, 0.5)\notsu (0.5, 0.5)\ninvert (0.5, 0.5)\n")
    _apply(w, prog)
    ed = w._program["edit"]
    lines = ed.toPlainText().splitlines()
    gauss_line = next(i + 1 for i, l in enumerate(lines) if l.startswith("gaussian"))
    ed.breakpoints = {gauss_line}                         # gutter click on 'gaussian'
    w._program["run"](True)
    app.processEvents()
    assert ed._exec_line == gauss_line
    assert w._stage_list.currentRow() == 0
    assert set(ed.timings) == {gauss_line}                # timings on op lines only
    assert "breakpoint" in _status(w)
    # Continue resumes at the next op line and the cursor lands on an op line
    ed.breakpoints.clear()
    w._program["continue"]()
    assert ed._exec_line == gauss_line + 2
    assert lines[ed._exec_line - 1].startswith("invert")
    # Step from the start lands on the first op line, not on a directive line
    ed.clear_exec()
    w._program["step"]()
    assert ed._exec_line == gauss_line


def test_f2_parser_reports_source_line_per_stage():
    st, errs, lines = studio.parse_hdev_program_lines(
        "* c\ndev_update_off ()\nfor 2\n gaussian 0.5 0.5\nendfor\notsu 0.5 0.5", ["gaussian", "otsu"])
    assert not errs
    assert [s[0] for s in st] == ["gaussian", "gaussian", "otsu"]
    assert lines == [4, 4, 6]


# ----------------------------------------------------------------- F3 knobs
def test_f3_slider_b_leaves_knob_a_untouched(app, win):
    w, model = win
    model.stages = [["gaussian", 0.29, 0.57]]
    w._step_to(0)
    sa, sb = w._knob_sliders
    assert sa.value() == 29                               # round, not truncate
    sb.setValue(60)
    app.processEvents()
    assert model.stages[0][1] == 0.29
    assert model.stages[0][2] == pytest.approx(0.60)


def test_f3_spin_a_leaves_precise_b_untouched(app, win):
    from PySide6 import QtWidgets
    w, model = win
    model.stages = [["gaussian", 0.5, 0.12345]]
    w._step_to(0)
    spa = [s for s in w.findChildren(QtWidgets.QDoubleSpinBox)
           if s.decimals() == 3 and s.maximum() == 1.0][0]
    spa.setValue(0.6)
    app.processEvents()
    assert model.stages[0] == ["gaussian", 0.6, 0.12345]


# ----------------------------------------------------------------- F4 raising stage
def _raising_pair():
    img = studio.demo_image(64)
    for c in [o.name for o in api._ops.REGISTRY if o.out_sort == "contour"][:6]:
        for second in ("gaussian", "otsu", "invert"):
            try:
                api.run_pipeline(img, [(c, .5, .5), (second, .5, .5)])
            except Exception:
                return c, second
    pytest.skip("no raising stage pair in this registry")


def test_f4_run_reports_failing_stage_and_stops_there(app, win):
    w, model = win
    c, second = _raising_pair()
    _apply(w, "%s (0.5, 0.5)\n%s (0.5, 0.5)\ninvert (0.5, 0.5)" % (c, second))
    ed = w._program["edit"]
    w._program["run"](True)
    app.processEvents()
    st = _status(w)
    assert st.startswith("✕") and second in st and "line 2" in st
    assert ed._exec_line == 2                             # cursor stops at the failing line
    assert 3 not in ed.timings                            # nothing past it was "run"
    probs = [w._problems.item(i).text() for i in range(w._problems.count())]
    assert any(second in p and "✕" in p for p in probs)
    # Step also names the failure instead of silently threading the stale value
    ed.clear_exec()
    w._program["step"](); w._program["step"]()
    assert _status(w).startswith("✕") and second in _status(w)


# ----------------------------------------------------------------- F5 aliases
def test_f5_alias_loaded_from_json_is_canonical_and_runs(app, win):
    w, model = win
    al = [(o.name, o.halcon) for o in api._ops.REGISTRY if o.halcon and o.halcon != o.name]
    name, alias = al[0]
    model.load_dict({"stages": [[alias, 0.5, 0.5]]})
    assert model.stages[0][0] == name                     # canonical name stored
    txt = w._program["text"]()
    assert name in txt
    _stages, errs = w._program["parse"](txt)
    assert not errs
    _apply(w, txt)
    w._program["run"](True)
    assert w._program["edit"]._exec_line == 1 and _status(w).startswith("ran 1")
    m = studio.PipelineModel()
    assert m.add_stage(alias) == 0 and m.stages[0][0] == name


# ----------------------------------------------------------------- F6 knob range
def test_f6_validator_rejects_out_of_range_and_non_finite():
    for bad in (1.5, -0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            studio.validate_pipeline_dict({"stages": [["gaussian", bad, 0.5]]})
        with pytest.raises(ValueError):
            studio.validate_pipeline_dict({"stages": [["gaussian", 0.5, bad]]})


def test_f6_full_precision_round_trip(app, win):
    w, model = win
    model.load_dict({"stages": [["gaussian", 0.12345, 0.5]]})
    txt = w._program["text"]()
    assert "0.12345" in txt
    st, errs = w._program["parse"](txt)
    assert not errs and st[0][1] == 0.12345
    assert "0.12345" in model.export_python()


# ----------------------------------------------------------------- F7 directive errors
def test_f7_bad_set_system_is_reported(app, win):
    w, model = win
    n0 = len(w._state["errors"])
    _apply(w, "set_system ('bogus_param', 1)\ngaussian (0.5, 0.5)")
    errs = w._state["errors"][n0:]
    assert errs and any("bogus_param" in t for _, t in errs)
    assert [s[0] for s in model.stages] == ["gaussian"]   # the pipeline itself still applied


# ----------------------------------------------------------------- F8 undo during debounce
def test_f8_undo_inside_knob_debounce_keeps_history_consistent(app, win):
    w, model = win
    _apply(w, "gaussian (0.5, 0.5)")
    w._step_to(0)
    sa, _sb = w._knob_sliders
    undo0 = len(w._undo_stack)
    sa.setValue(80); app.processEvents()                  # drag tick, timer pending
    w._undo()                                             # Ctrl+Z within the debounce
    assert len(w._redo_stack) == 1
    assert not w._knob_timer.isActive()
    w._knob_timer.timeout.emit(); app.processEvents()     # a late tail must be a no-op
    assert len(w._redo_stack) == 1
    assert len(w._undo_stack) == undo0 - 1


# ----------------------------------------------------------------- F9 '#' in quotes
def test_f9_hash_inside_quoted_directive_is_not_a_comment():
    d = studio.extract_dev_directives("dev_disp_text ('#1 coin', 14, 14)  # trailing")
    assert d == [("dev_disp_text", ["#1 coin", 14.0, 14.0])]
    assert studio._hdev_strip_comment("gaussian (0.5, 0.5) # note") == "gaussian (0.5, 0.5)"


# ----------------------------------------------------------------- F10 save raw
def test_f10_save_result_writes_pipeline_output_not_the_view(app, win, tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    import imgio
    w, model = win
    _apply(w, "otsu (0.5, 0.5)")
    w._set_display_mode("region overlay"); app.processEvents()
    st = w._state
    assert st["result"].shape != st["raw"].shape          # the view is RGB, the output 2-D
    out = tmp_path / "r.png"
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(out), "")))
    w._actions["save_result"].trigger()
    saved = imgio.load(str(out))
    assert saved.shape == st["raw"].shape
    view = tmp_path / "v.png"
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(view), "")))
    w._actions["save_view"].trigger()
    assert imgio.load(str(view)).ndim == 3


# ----------------------------------------------------------------- F11 save_pipe
def test_f11_save_pipe_is_atomic_and_persists_directives(app, win, tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    w, model = win
    _apply(w, "dev_set_color ('cyan')\nset_system ('thread_num', 0)\ngaussian (0.5, 0.5)")
    out = tmp_path / "p.json"
    out.write_text("OLD", encoding="utf-8")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(out), "")))
    import builtins
    real_open = builtins.open

    def failing_open(path, *a, **k):
        if str(path) == str(out):                           # the final path is never opened
            raise AssertionError("save must write a temp file, then os.replace")
        return real_open(path, *a, **k)
    monkeypatch.setattr(builtins, "open", failing_open)
    w._actions["save_pipeline"].trigger()
    monkeypatch.setattr(builtins, "open", real_open)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["directives"] == ["dev_set_color ('cyan')", "set_system ('thread_num', 0)"]
    assert not [f for f in os.listdir(tmp_path) if f != "p.json"]   # no temp file left
    # reload into a fresh window: the editor shows exactly the saved program
    _apply(w, "dev_update_off ()\notsu (0.5, 0.5)")
    w._open_pipe_path(str(out))
    txt = w._program["edit"].toPlainText()
    assert "dev_set_color" in txt and "dev_update_off" not in txt and "gaussian" in txt
    # an old file without the key still loads; a malformed key is rejected
    m = studio.PipelineModel()
    m.load_dict({"stages": [["gaussian", 0.5, 0.5]]})
    assert m.directives == []
    with pytest.raises(ValueError):
        m.load_dict({"stages": [["gaussian", 0.5, 0.5]], "directives": "dev_set_color ('cyan')"})
    with pytest.raises(ValueError):
        m.load_dict({"stages": [["gaussian", 0.5, 0.5]], "directives": ["gaussian (0.5, 0.5)"]})


def test_f11_opening_json_without_directives_clears_stale_editor_lines(app, win, tmp_path):
    w, model = win
    _apply(w, "dev_set_color ('cyan')\ngaussian (0.5, 0.5)")
    pj = tmp_path / "other.json"
    pj.write_text(json.dumps({"fullseye_pipeline": 1, "stages": [["otsu", 0.5, 0.5]]}), encoding="utf-8")
    w.drop_handler([str(pj)]); app.processEvents()
    assert "dev_set_color" not in w._program["edit"].toPlainText()
    assert "directives" not in model.to_dict()             # old-shape file stays old-shape


# ----------------------------------------------------------------- except census
def test_example_preview_shows_read_error(app, win, monkeypatch):
    w, _model = win
    import examples as EX
    monkeypatch.setattr(EX, "code", lambda i: (_ for _ in ()).throw(OSError("boom")))
    dlg = w._open_examples_2d()
    if dlg is None:
        pytest.skip("examples dialog unavailable")
    lst, code = dlg._fs_list, dlg._fs_code
    if lst.count() == 0:
        pytest.skip("no examples registered")
    lst.setCurrentRow(0); app.processEvents()
    assert "boom" in code.toPlainText()
    dlg.close()
