"""Fullseye Studio: headless PipelineModel logic + an offscreen Qt smoke test."""
import json
import os

import numpy as np
import pytest

import studio


def test_pipeline_model_build_and_evaluate():
    m = studio.PipelineModel(studio.demo_image(64))
    m.add_stage("gaussian", 0.4, 0.5)
    m.add_stage("sobel_amp", 0.5, 0.5)
    m.add_stage("otsu", 0.4, 0.5)
    assert len(m.stages) == 3
    # intermediate result after stage 0 differs from the final (region) result
    mid = m.result_upto(0)
    out = m.output()
    assert mid.shape == (64, 64)
    assert set(np.unique(out)).issubset({0.0, 1.0})           # otsu -> binary


def test_pipeline_model_edit_and_export():
    m = studio.PipelineModel(studio.demo_image(48))
    i = m.add_stage("gaussian")
    m.add_stage("otsu")
    m.set_knobs(i, a=0.7, b=0.3)
    assert m.stages[i] == ["gaussian", 0.7, 0.3]
    m.move_stage(0, 1)
    assert m.ops_string() == "otsu,gaussian"
    m.remove_stage(0)
    assert m.ops_string() == "gaussian"
    py = m.export_python()
    assert "fullseye.run_pipeline" in py and "gaussian" in py


def test_add_unknown_op_raises():
    m = studio.PipelineModel(studio.demo_image(32))
    with pytest.raises(KeyError):
        m.add_stage("no_such_op")


def test_result_upto_negative_is_raw_image():
    m = studio.PipelineModel(studio.demo_image(32))
    m.add_stage("invert")
    assert np.allclose(m.result_upto(-1), m.image)            # before any stage


def test_histogram_image():
    h = studio.histogram_image(studio.demo_image(64))
    assert h.shape == (64, 256)
    assert 0.0 <= h.min() and h.max() <= 1.0
    assert studio.histogram_image(np.full((32, 32), 0.5)).sum() > 0   # constant -> a bar
    assert studio.histogram_image(np.array([[np.inf, np.nan]])).sum() == 0  # no finite data


def test_inspect_result_by_sort():
    img = studio.demo_image(32)
    di = studio.inspect_result(img)
    assert di["kind"] == "image" and di["shape"] == (32, 32)
    region = (img > 0.6).astype(float)
    dr = studio.inspect_result(region)
    assert dr["kind"] == "region" and "regions" in dr and "area_fraction" in dr
    assert studio.inspect_result(3.5)["kind"] == "feature"
    assert studio.inspect_result({"cs": [1, 2]})["n_contours"] == 2


def test_model_load_recipe():
    import recipes
    m = studio.PipelineModel(studio.demo_image(48))
    name = recipes.names()[3]
    m.load_recipe(name)
    assert m.ops_string() == ",".join(s[0] for s in recipes.stages(name))


def test_apply_display_modes():
    img = studio.demo_image(32)
    assert studio.apply_display(img, "gray") is img
    assert studio.apply_display(img, "viridis").shape == (32, 32, 3)
    assert studio.apply_display(img, "shaded relief").shape == (32, 32)
    assert studio.apply_display(img, "height (color)").shape == (32, 32, 3)


def test_step_states_and_summary():
    m = studio.PipelineModel(studio.demo_image(32))
    m.add_stage("gaussian"); m.add_stage("otsu")
    ss = m.step_states()
    assert len(ss) == 2 and ss[0]["op"] == "gaussian"
    assert ss[1]["state"]["kind"] == "region"
    assert "region" in studio.step_summary(ss[1]["state"])
    assert "mean" in studio.step_summary(ss[0]["state"])


def test_pipeline_save_load_dict():
    m = studio.PipelineModel(studio.demo_image(32))
    m.add_stage("gaussian", 0.4, 0.5); m.add_stage("otsu", 0.3, 0.5)
    m2 = studio.PipelineModel(studio.demo_image(32))
    m2.load_dict(m.to_dict())
    assert m2.stages == m.stages and m2.ops_string() == m.ops_string()


def test_downsample_grid():
    g = studio._downsample_grid(np.zeros((300, 400)), max_side=100)
    assert max(g.shape) <= 160


def test_perception_model_two_frame_views():
    import studio
    from scipy import ndimage
    rng = np.random.default_rng(0)
    a = np.clip(ndimage.gaussian_filter(rng.random((64, 80)), 1.3), 0, 1)
    b = ndimage.shift(a, (0.0, 3.0), order=1, mode="nearest")   # a horizontal shift
    pm = studio.PerceptionModel(frame_b=b)
    for mode in studio.PerceptionModel.MODES:
        rgb = pm.view(mode, a)
        assert rgb.ndim == 3 and rgb.shape[2] == 3
        assert np.isfinite(rgb).all() and rgb.min() >= 0.0 and rgb.max() <= 1.0


def test_perception_model_requires_matching_second_frame():
    import studio
    import pytest
    a = np.zeros((16, 16))
    pm = studio.PerceptionModel()
    with pytest.raises(ValueError):
        pm.view("optical flow", a)                 # no frame B loaded
    pm.set_frame_b(np.zeros((8, 8)))
    with pytest.raises(ValueError):
        pm.view("optical flow", a)                 # size mismatch


def test_qt_window_builds_offscreen():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(64)))
    model.add_stage("gaussian")
    win, model2 = studio.build_window()      # default demo image
    assert win is not None and model2 is not None


def test_op_detail_and_tooltip():
    row = {"name": "gaussian", "halcon": "gauss_filter", "category": "filter",
           "in_sort": "image", "out_sort": "image"}
    d = studio.op_detail(row)
    assert "gaussian" in d and "image → image" in d and "gauss_filter" in d
    # an op with no HALCON alias -> no "HALCON:" suffix
    row2 = dict(row, halcon="")
    assert "HALCON" not in studio.op_detail(row2)
    tip = studio.op_tooltip(row)
    assert "gauss_filter" in tip and "filter" in tip and "knobs" in tip


def test_window_actions_and_shortcuts():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    acts = win._actions
    for key in ("open_image", "save_result", "export", "remove", "fit",
                "run_all", "clear", "about"):
        assert key in acts and acts[key] is not None
    # keyboard shortcuts are actually assigned
    assert acts["open_image"].shortcut().toString() == "Ctrl+O"
    assert acts["run_all"].shortcut().toString() in ("Ctrl+Return", "Ctrl+Enter")
    assert win.menuBar() is not None and len(win.menuBar().actions()) == 5
    assert callable(win._flash)


def test_clear_action_empties_pipeline():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu")
    win, model = studio.build_window(m)
    assert len(model.stages) == 2
    win._actions["clear"].trigger()
    assert model.stages == []


def test_remove_disables_knobs():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu")
    win, model = studio.build_window(m)
    win._stage_list.setCurrentRow(1)                     # select a stage -> knobs live
    sa, sb = win._knob_sliders
    assert sa.isEnabled() and sb.isEnabled()
    win._actions["remove"].trigger()                     # remove the selected stage
    # selection is gone -> knobs must not still describe a deleted stage
    assert not sa.isEnabled() and not sb.isEnabled()


def test_reset_shows_raw_image():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    import numpy as np
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("invert")                                # a visibly different single stage
    win, model = studio.build_window(m)
    win._actions["run_all"].trigger()                    # show the final (inverted) result
    win._actions["reset"].trigger()                      # Reset must show the RAW image
    assert win._state["view_raw"] is True
    assert np.allclose(win._state["raw"], model.result_upto(-1))   # the pre-pipeline image


def test_stage_list_drag_reorder_enabled():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert win._stage_list.dragDropMode() == QtWidgets.QAbstractItemView.InternalMove


def test_scalar_result_shows_message_not_crash():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("otsu"); m.add_stage("count_obj")        # -> region -> scalar feature
    win, model = studio.build_window(m)
    win._stage_list.setCurrentRow(1)                     # select the feature stage
    # a non-raster (scalar) result shows a message, not an image, and does not crash
    assert win._state["result"] is None


def test_palette_filter_ranking():
    labels = ["op: gaussian", "▸ Open image", "op: median", "op: gauss_deriv"]
    got = [labels[i] for i in studio.palette_filter(labels, "gauss")]
    assert "op: gaussian" in got and "op: gauss_deriv" in got
    assert "op: median" not in got                       # non-matching filtered out
    assert studio.palette_filter(labels, "") == list(range(len(labels)))  # empty -> all
    # prefix beats word-start beats bare substring
    order = studio.palette_filter(["gaussian", "a gaussian", "xgaussian"], "gauss")
    assert order[0] == 0


def test_command_palette_action_wired():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert "palette" in win._actions
    assert win._actions["palette"].shortcut().toString() == "Ctrl+P"


def test_shortcut_table_dedup_and_drop_empty():
    items = [("Open image…", "Ctrl+O"), ("About", ""),
             ("Open image…", "Ctrl+O"), ("Fit", "Ctrl+0")]
    rows = studio.shortcut_table(items)
    assert ("Open image", "Ctrl+O") in rows and ("Fit", "Ctrl+0") in rows
    assert all(sc for _, sc in rows)            # empties dropped
    assert len(rows) == 2                         # duplicate collapsed


def test_shortcuts_help_action_wired():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert "shortcuts" in win._actions
    assert win._actions["shortcuts"].shortcut().toString() == "F1"


def test_sample_code_helper():
    import recipes
    name = recipes.names()[0]
    ops, py = studio.sample_code(name)
    assert isinstance(ops, str) and ops                      # a comma-joined ops string
    compile(py, "<sample>", "exec")                          # the Python is valid
    assert "run_pipeline" in py
    assert studio.sample_code("no such recipe") is None


def test_help_op_reference_and_samples_wired():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert "op_reference" in win._actions and "samples" in win._actions
    assert win._actions["op_reference"].shortcut().toString() == "Shift+F1"


def test_step_states_robust_to_failing_stage():
    # a stage that raises must not blank the whole step summary (silent-bug fix)
    m = studio.PipelineModel(studio.demo_image(32))
    m.stages = [["gaussian", 0.5, 0.5], ["nope_op", 0.5, 0.5]]   # 2nd op unknown
    ss = m.step_states()                                          # must NOT raise
    assert len(ss) == 2
    assert ss[0]["state"]["kind"] != "error"                     # good stage still summarized
    assert ss[1]["state"]["kind"] == "error"                     # bad stage flagged
    assert "ERROR" in studio.step_summary(ss[1]["state"])


def test_problems_panel_flags_unknown_op():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    m = studio.PipelineModel(studio.demo_image(32))
    m.stages = [["gaussian", 0.5, 0.5], ["nope_op", 0.5, 0.5]]
    win, _ = studio.build_window(m)
    texts = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert any("nope_op" in t for t in texts)


def test_problems_panel_clean_says_no_problems():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    m = studio.PipelineModel(studio.demo_image(32))
    m.add_stage("gaussian"); m.add_stage("otsu")
    win, _ = studio.build_window(m)
    texts = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert texts == ["no problems"]


# --------------------------------------------------------------------------- #
# Regression tests for the 2026-08-14 UI review (docs/STUDIO_REVIEW_2026_08_14.md)
# --------------------------------------------------------------------------- #
def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _slider_handle_amber_px(enabled):
    """Render a themed QSlider and count AMBER (enabled-handle) pixels."""
    from PySide6 import QtWidgets, QtGui, QtCore
    app = _app()
    w = QtWidgets.QWidget()
    w.setStyleSheet(studio.THEME)
    lay = QtWidgets.QVBoxLayout(w)
    s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    s.setRange(0, 100); s.setValue(50); s.setEnabled(enabled)
    lay.addWidget(s)
    w.resize(200, 60); w.show(); app.processEvents()
    img = w.grab().toImage().convertToFormat(QtGui.QImage.Format_RGB32)
    arr = np.frombuffer(img.constBits(), np.uint8).reshape(
        img.height(), img.bytesPerLine() // 4, 4)
    amber = ((np.abs(arr[:, :, 2].astype(int) - 0xF5) < 12)
             & (np.abs(arr[:, :, 1].astype(int) - 0xA5) < 12)
             & (np.abs(arr[:, :, 0].astype(int) - 0x24) < 12))
    w.hide()
    return int(amber.sum())


def test_disabled_slider_handle_actually_reads_disabled():
    """V2: `QSlider:disabled::handle:horizontal` never matched (Qt QSS wants the
    sub-control BEFORE the pseudo-state), so a disabled knob still painted the
    amber 'live' handle."""
    _app()
    assert "QSlider::handle:horizontal:disabled" in studio.THEME
    assert "QSlider:disabled::handle:horizontal" not in studio.THEME   # the broken form
    assert _slider_handle_amber_px(enabled=True) > 0                   # enabled: amber
    assert _slider_handle_amber_px(enabled=False) == 0                 # disabled: not amber


def test_theme_has_visible_focus_indicators():
    """C12/V1: the blanket `* { outline:none; }` erased every focus ring."""
    assert "* { outline:none; }" not in studio.THEME
    for sel in ("QPushButton:focus", "QToolButton:focus", "QListWidget:focus",
                "QComboBox:focus", "QLineEdit:focus", "QSlider::handle:horizontal:focus"):
        assert sel in studio.THEME, sel


def test_validate_pipeline_dict_rejects_malformed_payloads():
    """C11/H: a bad pipeline file must raise a readable ValueError, not IndexError."""
    good = {"fullseye_pipeline": 1, "stages": [["gaussian", 0.4, 0.5]]}
    assert studio.validate_pipeline_dict(good) == [["gaussian", 0.4, 0.5]]
    for bad in ([], {"stages": [["gaussian"]]}, {"stages": "abc"}, {"stages": [None]},
                {"nope": 1}, {"stages": [["gaussian", "x", 0.5]]},
                {"stages": [["no_such_op", 0.5, 0.5]]}, {"stages": [[7, 0.5, 0.5]]}):
        with pytest.raises(ValueError):
            studio.validate_pipeline_dict(bad)


def test_load_dict_keeps_current_pipeline_on_bad_payload():
    """H: validation happens into a temporary list -> the live pipeline survives."""
    m = studio.PipelineModel(studio.demo_image(32))
    m.add_stage("gaussian"); m.add_stage("otsu")
    before = [list(s) for s in m.stages]
    with pytest.raises(ValueError):
        m.load_dict({"stages": [["gaussian"]]})
    assert m.stages == before


def test_truncate_shortens_long_error_text():
    """C13/P9: raw backend errors must not be pasted whole into a tooltip."""
    assert studio.truncate("short") == "short"
    long = "x" * 500
    assert len(studio.truncate(long)) == 160
    assert studio.truncate(long).endswith("…")
    assert studio.truncate("a\n  b\tc") == "a b c"          # whitespace collapsed


def test_failing_stage_tooltip_is_truncated():
    _app()
    m = studio.PipelineModel(studio.demo_image(32))
    m.stages = [["gaussian", .5, .5], ["nope_" + "x" * 400, .5, .5]]
    win, _ = studio.build_window(m)
    assert len(win._stage_list.item(1).toolTip()) < 200
    assert all(len(win._problems_list.item(i).text()) < 220
               for i in range(win._problems_list.count()))


def test_knob_tick_costs_one_pipeline_evaluation():
    """C2: a knob tick used to run step_states() (every prefix, O(n^2)) plus two
    renders. It must now cost exactly one evaluation, with the summaries debounced."""
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    for _ in range(6):
        m.add_stage("gaussian")
    win, model = studio.build_window(m)
    win._stage_list.setCurrentRow(3)
    calls = {"n": 0}
    orig = model.result_upto
    model.result_upto = lambda i: (calls.__setitem__("n", calls["n"] + 1), orig(i))[1]
    sa, sb = win._knob_sliders
    sa.setValue(sa.value() + 7)
    assert calls["n"] == 1, "expected 1 pipeline evaluation per knob tick, got %d" % calls["n"]
    assert model.stages[3][1] == pytest.approx(sa.value() / 100.0)
    assert win._state["dirty"] is True
    # the debounce timer carries the (expensive) per-stage summary refresh
    assert win._knob_timer.isActive()
    win._knob_timer.stop()


def test_mutations_render_exactly_once():
    """C3: refresh_stage_list() used to re-select the row with signals unblocked,
    so every edit rendered twice (currentRowChanged + the caller's show_result)."""
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("invert"); m.add_stage("otsu")
    win, model = studio.build_window(m)
    win._stage_list.setCurrentRow(1)
    for label, act in (("move_up", "move_up"), ("move_down", "move_down")):
        win._state["renders"] = 0
        win._actions[act].trigger()
        assert win._state["renders"] == 1, "%s rendered %d times" % (label, win._state["renders"])
    win._state["renders"] = 0
    win._actions["remove"].trigger()
    assert win._state["renders"] == 1


def test_actions_track_selection_and_result():
    """C7: Remove/Up/Down need a selected stage; Save-result/3D need a raster."""
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for key in ("remove", "move_up", "move_down"):
        assert not win._actions[key].isEnabled()            # empty pipeline, no selection
    assert not win._buttons["remove"].isEnabled()
    assert not win._actions["export"].isEnabled()           # nothing to export
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("invert")
    win, model = studio.build_window(m)
    win._stage_list.setCurrentRow(0)
    assert win._actions["remove"].isEnabled()
    assert not win._actions["move_up"].isEnabled()          # already first
    assert win._actions["move_down"].isEnabled()
    win._stage_list.setCurrentRow(1)
    assert win._actions["move_up"].isEnabled()
    assert not win._actions["move_down"].isEnabled()        # already last
    assert win._actions["save_result"].isEnabled()          # a raster result is displayed
    assert win._buttons["surface_3d"].isEnabled()


def test_scalar_result_disables_save_and_3d():
    """C7: a scalar feature is not saveable/3D-able -> those must go dim."""
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("otsu"); m.add_stage("count_obj")
    win, _ = studio.build_window(m)
    win._stage_list.setCurrentRow(1)
    assert win._state["result"] is None
    assert not win._actions["save_result"].isEnabled()
    assert not win._actions["surface_3d"].isEnabled()


def test_editing_shortcuts_are_scoped_to_the_pipeline_list():
    """C8/P10: Ctrl+Up / Ctrl+Down were WindowShortcut and fired while the user
    was typing in the operator search box (a QLineEdit does not claim them)."""
    from PySide6 import QtCore
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu")
    win, model = studio.build_window(m)
    scoped = win._stage_list.actions()
    for key in ("remove", "move_up", "move_down", "step", "reset"):
        act = win._actions[key]
        assert act.shortcutContext() == QtCore.Qt.WidgetWithChildrenShortcut, key
        assert act in scoped, key
    # global (menu/toolbar) actions keep window scope
    for key in ("open_image", "save_result", "export", "clear", "palette", "run_all"):
        assert win._actions[key].shortcutContext() == QtCore.Qt.WindowShortcut, key
    # the action is still owned by its menu (menu entry unchanged) as well as by
    # the pipeline list, and still works when triggered directly
    assoc = {type(o).__name__ for o in win._actions["remove"].associatedObjects()}
    assert "QMenu" in assoc and "QListWidget" in assoc, assoc
    win._stage_list.setCurrentRow(1)
    win._actions["remove"].trigger()
    assert model.ops_string() == "gaussian"


def test_command_palette_runs_the_command_once():
    """C9/P11: a double-click emits BOTH itemDoubleClicked and itemActivated; both
    were wired to run_sel(), so the chosen command ran twice."""
    from PySide6 import QtWidgets
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    orig_exec = QtWidgets.QDialog.exec
    QtWidgets.QDialog.exec = lambda self: None          # open the palette non-modally
    try:
        win._actions["palette"].trigger()
    finally:
        QtWidgets.QDialog.exec = orig_exec
    pal = win._palette
    pal["edit"].setText("op: gaussian")
    lst = pal["list"]
    assert lst.count() >= 1
    lst.setCurrentRow(0)
    before = len(model.stages)
    lst.itemDoubleClicked.emit(lst.item(0))             # what one real double-click
    lst.itemActivated.emit(lst.item(0))                 # delivers to the widget
    pal["run"]()                                        # and an extra explicit run
    assert len(model.stages) == before + 1
    assert pal["state"]["ran"] is True


def test_dirty_flag_and_confirm_before_destructive_replace():
    """C6/P4: clearing / loading over an edited pipeline used to discard it silently."""
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu")
    win, model = studio.build_window(m)
    assert win._state["dirty"] is False                 # freshly built == clean
    assert win._confirm_discard("x") is True            # nothing to lose -> no prompt
    win._stage_list.setCurrentRow(0)
    win._actions["move_down"].trigger()                 # a mutation
    assert win._state["dirty"] is True

    asked = []
    orig = studio.CONFIRM_HOOK
    studio.CONFIRM_HOOK = lambda parent, title, text: (asked.append(title), False)[1]
    try:
        win._actions["clear"].trigger()                 # user says "cancel"
        assert asked, "no confirmation was requested"
        assert len(model.stages) == 2, "pipeline was cleared despite cancelling"
        studio.CONFIRM_HOOK = lambda parent, title, text: True
        win._actions["clear"].trigger()                 # user says "discard"
        assert model.stages == []
    finally:
        studio.CONFIRM_HOOK = orig


def test_close_event_is_vetoed_while_dirty():
    """C6/P4: closing the window with unsaved edits must ask first."""
    from PySide6 import QtGui, QtWidgets
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu")
    win, model = studio.build_window(m)
    win._stage_list.setCurrentRow(0)
    win._actions["move_down"].trigger()
    orig = studio.CONFIRM_HOOK
    studio.CONFIRM_HOOK = lambda parent, title, text: False      # "cancel"
    try:
        ev = QtGui.QCloseEvent(); ev.accept()
        QtWidgets.QApplication.sendEvent(win, ev)
        assert not ev.isAccepted(), "close was not vetoed while dirty"
        studio.CONFIRM_HOOK = lambda parent, title, text: True   # "discard"
        ev = QtGui.QCloseEvent(); ev.accept()
        QtWidgets.QApplication.sendEvent(win, ev)
        assert ev.isAccepted()
    finally:
        studio.CONFIRM_HOOK = orig


def test_file_io_errors_are_reported_not_raised(tmp_path, monkeypatch):
    """C5/P5: a missing image / malformed JSON / unwritable path must not crash."""
    from PySide6 import QtWidgets
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian")
    win, model = studio.build_window(m)
    errs = win._state["errors"]
    monkeypatch.setattr(studio, "ERROR_HOOK", lambda *a: None)   # no modal in tests

    missing = str(tmp_path / "no_such.png")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (missing, "")))
    win._actions["open_image"].trigger()                          # must not raise
    assert errs and "Could not open image" in errs[-1][0]

    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not json", encoding="utf-8")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(bad), "")))
    win._actions["open_pipeline"].trigger()
    assert "Could not open pipeline" in errs[-1][0]
    assert model.ops_string() == "gaussian"                       # pipeline intact

    schema = tmp_path / "schema.json"
    schema.write_text('{"stages": [["gaussian"]]}', encoding="utf-8")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(schema), "")))
    win._actions["open_pipeline"].trigger()
    assert "Could not open pipeline" in errs[-1][0]
    assert model.ops_string() == "gaussian"

    # imgio.save() delegates to cv2.imwrite(), which returns False rather than
    # raising on a bad path, so force a real exception to exercise the wrapper.
    out_png = str(tmp_path / "out.png")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (out_png, "")))
    monkeypatch.setattr(studio.imgio, "save",
                        lambda p, a: (_ for _ in ()).throw(OSError("disk on fire")))
    win._stage_list.setCurrentRow(0)
    assert win._state["result"] is not None
    win._actions["save_result"].trigger()
    assert "Could not save result" in errs[-1][0]

    # save_pipeline uses open()/json directly, which does raise on a missing dir

    unpipe = str(tmp_path / "nope_dir" / "p.json")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (unpipe, "")))
    win._actions["save_pipeline"].trigger()
    assert "Could not save pipeline" in errs[-1][0]


def test_save_pipeline_clears_the_dirty_flag(tmp_path, monkeypatch):
    from PySide6 import QtWidgets
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu")
    win, model = studio.build_window(m)
    win._stage_list.setCurrentRow(0)
    win._actions["move_down"].trigger()
    assert win._state["dirty"] is True
    out = tmp_path / "pipe.json"
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(out), "")))
    win._actions["save_pipeline"].trigger()
    assert win._state["dirty"] is False
    assert studio.validate_pipeline_dict(json.loads(out.read_text(encoding="utf-8"))) == model.stages


def test_perception_error_reaches_problems_and_inspector():
    """C15: a perception failure was only a 6-second status-bar flash."""
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    win._perception["run"]()                        # no frame B loaded -> ValueError
    texts = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert any("perception" in t for t in texts), texts
    assert "perception failed" in win._inspector.toPlainText()
    # a successful run clears it again
    from scipy import ndimage
    a = model.image
    win._perception["model"].set_frame_b(ndimage.shift(a, (0.0, 2.0), order=1, mode="nearest"))
    win._perception["mode"].setCurrentText("optical flow")
    win._perception["run"]()
    texts = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
    assert not any("perception" in t for t in texts), texts


def test_show_result_survives_a_display_failure(monkeypatch):
    """C4: only the pipeline call was guarded — inspect/display/histogram ran
    unguarded on backend output and could escape the Qt callback."""
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian")
    win, model = studio.build_window(m)
    monkeypatch.setattr(studio, "ERROR_HOOK", lambda *a: None)
    monkeypatch.setattr(studio, "apply_display",
                        lambda v, mode: (_ for _ in ()).throw(ValueError("boom in display")))
    win._stage_list.setCurrentRow(-1)
    win._stage_list.setCurrentRow(0)                 # must not raise out of the slot
    assert any("Display error" in t for t, _ in win._state["errors"])
    assert "display error" in win._inspector.toPlainText()


def test_primary_controls_have_accessible_names():
    """C13/P8: screen readers had nothing but the (often empty) visual label."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    sa, sb = win._knob_sliders
    assert sa.accessibleName() and sb.accessibleName()
    assert win._stage_list.accessibleName() and win._problems_list.accessibleName()
    for b in win._buttons.values():
        assert b.accessibleName(), b.text()


def test_drag_reorder_keeps_model_in_step_with_the_view():
    """C10/P3: the reviewers called the UserRole remap race-prone. Exercise the
    exact call QListWidget.dropEvent makes (model().moveRow) for every single-row
    move and assert the model order always equals the visible order."""
    from PySide6 import QtCore
    _app()
    ops = ["gaussian", "invert", "sobel_amp", "otsu", "median"]
    bad = []
    for src in range(len(ops)):
        for dst in range(len(ops) + 1):
            m = studio.PipelineModel(studio.demo_image(32))
            for op in ops:
                m.add_stage(op)
            win, model = studio.build_window(m)
            sl = win._stage_list
            sl.setCurrentRow(src)
            if not sl.model().moveRow(QtCore.QModelIndex(), src, QtCore.QModelIndex(), dst):
                continue
            visual = ",".join(sl.item(r).text().split(". ")[1].split(" (")[0]
                              for r in range(sl.count()))
            if visual != model.ops_string():
                bad.append((src, dst, visual, model.ops_string()))
    assert not bad, bad
