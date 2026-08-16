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
    assert "gauss_filter" in tip and "image → image" in tip and "a:" in tip


def test_op_arg_roles_and_signature_detail():
    """v18.7 P2: the operator panel can now answer 'what do the arguments do?'
    — curated knob roles for common ops + the implementation source as a universal
    fallback (honest: shows exactly how a and b are used)."""
    a_role, b_role = studio.op_arg_roles("gaussian")
    assert a_role and "σ" in a_role                 # a controls the Gaussian sigma
    src = studio.op_impl_source("gaussian")
    assert "gaussian_filter" in src and "a" in src  # source shows a's actual use
    row = {"name": "gaussian", "halcon": "gauss_filter", "category": "smoothing",
           "in_sort": "image", "out_sort": "image"}
    detail = studio.op_signature_detail(row)
    assert "knob a" in detail and "impl:" in detail and "gauss_filter" in detail
    # an unknown op is handled gracefully
    assert studio.op_arg_roles("no_such_op_xyz") == (None, None)
    assert studio.op_impl_source("no_such_op_xyz") == ""
    # a real but uncurated op still gets a signature (impl source), never crashes
    other = next(n for n in studio.api.op_names() if n not in ("gaussian",))
    d2 = studio.op_signature_detail({"name": other, "halcon": "", "category": "x",
                                     "in_sort": "image", "out_sort": "image"})
    assert "knob a" in d2


def test_general_tier_row_is_readonly_signature():
    # P1.5b: the general-algorithm tier (algo.py) shows in the op browser as a
    # read-only seq/scalar op — _op_row falls back to it, and the signature/tooltip
    # say "general-algorithm" + provenance + how to run it, not image knobs.
    row = studio._op_row("gauss_solve")
    assert row is not None and row["backend"] == "general"
    assert row["category"] == "algo:numeric" and row["in_sort"] == "seq"
    detail = studio.op_signature_detail(row)
    assert "general-algorithm" in detail and "algo run gauss_solve" in detail
    assert "partial pivoting" in detail          # provenance shown
    tip = studio.op_tooltip(row)
    assert "general-algorithm" in tip and "algo run gauss_solve" in tip
    # an image op is unaffected (no backend key -> the normal image signature)
    img = studio._op_row("gaussian")
    assert "backend" not in img and "knob a" in studio.op_signature_detail(img)
    # a genuinely unknown name is still None
    assert studio._op_row("no_such_op_xyz") is None


def test_op_browser_general_tier_is_readonly_offscreen():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtCore, QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])  # noqa: F841
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    op_list, btns = win._op_list, win._op_buttons
    names = [op_list.item(i).data(QtCore.Qt.UserRole) for i in range(op_list.count())]
    assert "gaussian" in names                   # image ops present
    assert "strfind" in names and "gauss_solve" in names   # general tier shown in the browser
    # selecting a general op makes the image-pipeline actions read-only
    op_list.setCurrentRow(names.index("strfind"))
    assert not btns["insert"].isEnabled()
    assert not btns["run_once"].isEnabled() and not btns["help"].isEnabled()
    # selecting an image op re-enables them
    op_list.setCurrentRow(names.index("gaussian"))
    assert btns["insert"].isEnabled() and btns["run_once"].isEnabled()
    # the pipeline model rejects a general op even if one is forced in by name
    with pytest.raises(KeyError):
        _model.add_stage("strfind")              # not an image-pipeline op


def test_hdev_program_rejects_general_tier_op():
    # P1.5b review: the code parser / autocomplete / Help picker must use IMAGE-only
    # names, so a general-algorithm op cannot become a valid image-pipeline token (which
    # apply_program would write straight into model.stages, bypassing add_stage's KeyError
    # backstop). An image op still parses; a general op is rejected with an error.
    import algo
    names = studio.api.op_names()                       # image REGISTRY names (what the window uses)
    assert not (set(names) & set(algo.algo_names()))    # no general op is a valid program token
    stages, errs = studio.parse_hdev_program("gaussian (0.4, 0.5)", names)
    assert not errs and stages[0][0] == "gaussian"
    for gop in ("strfind", "gauss_solve", "quicksort"):
        st, er = studio.parse_hdev_program(f"{gop} (0.5, 0.5)", names)
        assert er and not st, f"general op {gop!r} must be rejected by the image code parser"


def test_program_editor_and_help_exclude_general_tier_offscreen():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtCore, QtWidgets

    import algo
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])  # noqa: F841
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    # the browser SHOWS the general tier (read-only) ...
    shown = [win._op_list.item(i).data(QtCore.Qt.UserRole) for i in range(win._op_list.count())]
    assert set(algo.algo_names()) <= set(shown)
    # ... but the code parser / autocomplete / Help picker names EXCLUDE it
    assert "gaussian" in win._op_names
    assert not (set(win._op_names) & set(algo.algo_names()))


def test_region_overlay_display_mode():
    """v18.7 P4b: 'region overlay' blends a binary region onto the source image
    (HDevelop's dev_display of a region on the current image)."""
    import numpy as np
    base = np.linspace(0, 1, 64 * 64).reshape(64, 64)          # grayscale source
    region = np.zeros((64, 64)); region[20:40, 20:40] = 1.0    # a binary region
    out = studio.apply_display(region, "region overlay", base=base)
    assert out.ndim == 3 and out.shape[:2] == (64, 64)          # RGB overlay
    inside = out[25:35, 25:35]
    assert inside[..., 0].mean() > inside[..., 2].mean()        # amber = more red than blue
    # no base -> falls back to the raw region (no crash)
    assert studio.apply_display(region, "region overlay", base=None).ndim == 2


def test_hdev_program_syntax_and_control_flow():
    """v18.7 P5: HDevelop-style program parsing — `op (a, b)`, `*`/`#` comments,
    `for N ... endfor` (loop unrolling) and `if ... else ... endif` (constant branch)."""
    names = studio.api.op_names()
    # paren syntax + terse syntax + * and # comments
    stages, errs = studio.parse_hdev_program(
        "* a comment\ngaussian (0.4, 0.5)\nsobel_mag 0.5 0.5   # inline\n", names)
    assert not errs and [s[0] for s in stages] == ["gaussian", "sobel_mag"]
    assert abs(stages[0][1] - 0.4) < 1e-6 and abs(stages[0][2] - 0.5) < 1e-6
    # for-loop unrolls the block N times
    st2, e2 = studio.parse_hdev_program("for 3\n  gaussian (0.5, 0.5)\nendfor", names)
    assert not e2 and len(st2) == 3 and all(s[0] == "gaussian" for s in st2)
    # if/else picks a branch by a constant condition
    st3, _ = studio.parse_hdev_program("if 1\n gaussian 0.5 0.5\nelse\n invert 0.5 0.5\nendif", names)
    assert [s[0] for s in st3] == ["gaussian"]
    st4, _ = studio.parse_hdev_program("if 0\n gaussian 0.5 0.5\nelse\n invert 0.5 0.5\nendif", names)
    assert [s[0] for s in st4] == ["invert"]
    # comparison condition + nested for
    st5, _ = studio.parse_hdev_program("if 2 > 1\n otsu 0.5 0.5\nendif", names)
    assert [s[0] for s in st5] == ["otsu"]
    st6, e6 = studio.parse_hdev_program("for 2\n for 2\n  invert 0.5 0.5\n endfor\nendfor", names)
    assert not e6 and len(st6) == 4
    # unsupported / malformed -> clear errors
    assert any("while" in e for e in studio.parse_hdev_program("while 1\n gaussian 0.5 0.5\nendwhile", names)[1])
    assert any("endfor" in e for e in studio.parse_hdev_program("for 3\n gaussian 0.5 0.5", names)[1])
    assert any("unknown op" in e for e in studio.parse_hdev_program("bogus_op (0.1, 0.2)", names)[1])


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
    # File / Edit / View / Run / Windows / Help
    # File / Edit / View / Run / Window / Tools / Help
    assert win.menuBar() is not None and len(win.menuBar().actions()) == 7
    menu_titles = [a.text() for a in win.menuBar().actions()]
    assert "&Window" in menu_titles and "&Tools" in menu_titles
    assert "&Windows" not in menu_titles         # singular per HIG, not the OS plural
    assert callable(win._flash)


def test_dockable_layout_and_program_editor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    # every tool panel is a dockable/floatable window reachable from the Windows menu
    for key in ("operators", "pipeline", "display", "program"):
        assert key in win._docks
        assert win._docks[key].isFloatable() if hasattr(win._docks[key], "isFloatable") else True
    assert isinstance(win.centralWidget(), QtWidgets.QMdiArea)     # graphics workspace
    assert callable(win._new_graphics_window) and callable(win._reset_layout)
    # multiple graphics windows can be opened (HDevelop allows several)
    n0 = len(win._graphics_windows)
    win._new_graphics_window()
    assert len(win._graphics_windows) == n0 + 1
    # the program/code editor round-trips code <-> pipeline and validates input
    prog = win._program
    prog["edit"].setPlainText("gaussian 0.4 0.5\nsobel_mag 0.5 0.5\n# a comment\notsu")
    prog["apply"]()
    assert [s[0] for s in model.stages] == ["gaussian", "sobel_mag", "otsu"]
    _stages, errs = prog["parse"]("gaussian 0.4 0.5\nbogus_op 0.1")
    assert errs and "bogus_op" in errs[0]
    # a breakpoint stops the timed run and records per-line timings
    prog["edit"].breakpoints = {2}
    prog["run"](True)
    assert set(prog["edit"].timings) == {1, 2} and prog["edit"]._exec_line == 2


def test_variables_window_lists_and_displays_stage_outputs():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for op, a, b in (("gaussian", 0.4, 0.5), ("sobel_mag", 0.5, 0.5), ("otsu", 0.5, 0.5)):
        model.add_stage(op, a, b)
    v = win._variables
    v["refresh"]()
    # input + one row per stage, each labelled with the output sort (otsu -> region)
    labels = [v["list"].item(i).text() for i in range(v["list"].count())]
    assert v["list"].count() == 4
    assert labels[0].startswith("input") and "region" in labels[-1]
    n0 = len(win._graphics_windows)
    v["list"].setCurrentRow(3); v["display"](True)     # display a variable in a new graphics window
    assert len(win._graphics_windows) == n0 + 1


def test_i18n_from_file_and_dedicated_help_dialog():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # localisation data comes from studio_assets/i18n.json (not hardcoded), en is the base
    assert "en" in studio.LANGUAGES and set(studio.LANGUAGES) >= {"en", "ja", "zh"}
    assert studio.TOOLTIPS_I18N, "tooltips should load from the i18n file"
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    b = win._buttons["save_result"]
    en = b.toolTip()
    win._apply_language("ja"); ja = b.toolTip()
    win._apply_language("zh"); zh = b.toolTip()
    win._apply_language("en")
    assert ja != en and zh != en and b.toolTip() == en   # switches and restores
    # op help is HTML, with a dedicated dialog + related-op / sample-load anchors
    html = studio.op_help_html("gaussian", "en", {"in_sort": "image", "out_sort": "image"})
    assert "<h2" in html and ("sample:" in html or "Load this pipeline" in html) and "op:" in html
    win._help["show"]("gaussian")
    assert win._help["dialog"].isVisible()
    # an operator with no authored file still gets a generated card (no crash)
    assert "<h2" in studio.op_help_html("percentile", "en", {"in_sort": "image", "out_sort": "image"})


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


def test_remove_keeps_a_neighbour_selected():
    """Codex #11: after deleting a stage the operation target is kept — the neighbour
    (the stage now at the deleted index, or the new last one) is selected, so the knobs
    describe that surviving stage rather than being left with nothing selected."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu")
    win, model = studio.build_window(m)
    win._stage_list.setCurrentRow(1)                     # select the last stage -> knobs live
    sa, sb = win._knob_sliders
    assert sa.isEnabled() and sb.isEnabled()
    win._actions["remove"].trigger()                     # remove it
    # neighbour (now the last, index 0) stays selected; knobs describe it
    assert win._stage_list.currentRow() == 0
    assert sa.isEnabled() and sb.isEnabled()
    win._actions["remove"].trigger()                     # remove the last remaining stage
    # nothing left -> no selection, knobs off
    assert win._stage_list.currentRow() == -1
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


def test_dev_update_gates_and_resumes_display():
    """HDevelop dev_update_{window,var,pc,time}: turning updates off suppresses the
    auto-refresh (the display cost), turning them back on refreshes to the current
    state (as HDevelop updates when execution stops). Backs View > Display updates and
    the script ops dev_update_off/on."""
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu")
    win, model = studio.build_window(m)
    win._stage_list.setCurrentRow(0)
    st = win._state
    sa, _sb = win._knob_sliders

    # window ON (default): a knob tick renders
    n0 = st["renders"]
    sa.setValue(sa.value() + 5)
    assert st["renders"] > n0
    win._knob_timer.stop()

    # window OFF: the same edit still updates the model but does NOT render
    win._set_dev_update("window", False)
    assert st["dev_update"]["window"] is False
    assert win._dev_update_actions["window"].isChecked() is False
    n1 = st["renders"]
    a_before = model.stages[0][1]
    sa.setValue(sa.value() + 5)
    win._knob_timer.stop()
    assert st["renders"] == n1                       # display frozen
    assert model.stages[0][1] != a_before            # the edit itself still happened

    # turning it back on refreshes to the current state exactly once
    win._set_dev_update("window", True)
    assert st["renders"] == n1 + 1
    assert win._dev_update_actions["window"].isChecked() is True

    # 'all' toggles every flag and the toolbar mirror
    win._set_dev_update("all", False)
    assert all(v is False for v in st["dev_update"].values())
    assert win._dev_update_actions["_toolbar"].isChecked() is False
    assert win._dev_update_actions["pc"].isChecked() is False
    assert win._update_label.text() != ""            # a frozen display is surfaced, not silent
    win._set_dev_update("all", True)
    assert all(v is True for v in st["dev_update"].values())
    assert win._dev_update_actions["_toolbar"].isChecked() is True
    assert win._update_label.text() == ""            # cleared when everything auto-updates


def test_dev_directives_recognized_excluded_and_extracted():
    """HDevelop dev_* display directives in a Program are recognized (not 'unknown op'),
    excluded from the pipeline stages, and extractable in source order; an unsupported
    dev_ op is an honest error."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    parse = win._program["parse"]
    stages, errs = parse("dev_update_off ()\ngaussian (0.5, 0.5)\n"
                         "dev_set_part (0, 0, 20, 20)\ndev_update_on ()")
    assert not errs
    assert [s[0] for s in stages] == ["gaussian"]          # dev_* are directives, not stages
    _s, e2 = parse("dev_bogus ('x')")
    assert any("unsupported dev_" in x for x in e2)
    dirs = studio.extract_dev_directives(
        "dev_update_window ('off')\ngaussian 0.5 0.5\ndev_set_part (1, 2, 30, 40)")
    assert dirs == [("dev_update_window", ["off"]), ("dev_set_part", [1.0, 2.0, 30.0, 40.0])]


def test_apply_program_applies_dev_update_directives():
    """A Program's dev_update_off/on set the session display flags on apply."""
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    win._program["edit"].setPlainText("dev_update_off ()\ngaussian (0.5, 0.5)")
    win._program["apply"]()
    assert [s[0] for s in model.stages] == ["gaussian"]
    assert all(v is False for v in win._state["dev_update"].values())    # dev_update_off applied
    win._program["edit"].setPlainText("dev_update_on ()\ngaussian (0.5, 0.5)")
    win._program["apply"]()
    assert all(v is True for v in win._state["dev_update"].values())


def test_dev_set_part_zooms_current_view():
    """dev_set_part(Row1,Col1,Row2,Col2) fits the current view to that image part;
    a smaller part zooms in further; a negative value fits the whole image."""
    from PySide6 import QtGui
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(64)))
    view = win._current_view()
    view.set_pixmap(QtGui.QPixmap(64, 64))                 # deterministic content
    win._set_part(0, 0, 63, 63)
    m_full = view.transform().m11()
    win._set_part(0, 0, 8, 8)                              # small part -> more zoom
    m_zoom = view.transform().m11()
    assert m_zoom > m_full
    win._set_part(-1, -1, -1, -1)                          # fit whole, must not crash
    assert view.transform().m11() == pytest.approx(m_full, rel=0.05)


def test_dev_set_lut_and_clear_window_directives():
    """dev_set_lut(name) maps a HALCON LUT name to a Studio display mode (only known
    ones are honoured); dev_clear_window() clears the current graphics window."""
    from PySide6 import QtGui
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    win._apply_dev_directives("dev_set_lut ('jet')")
    assert win._display_actions["jet"].isChecked()
    prev = next(m for m, a in win._display_actions.items() if a.isChecked())
    win._apply_dev_directives("dev_set_lut ('temperature_no_such')")     # unknown -> no-op
    assert next(m for m, a in win._display_actions.items() if a.isChecked()) == prev
    view = win._current_view()
    view.set_pixmap(QtGui.QPixmap(16, 16))
    assert not view._item.pixmap().isNull()
    win._apply_dev_directives("dev_clear_window ()")
    assert view._item.pixmap().isNull()


def test_system_settings_get_set_persist_and_fail_closed():
    """HALCON set_system-style config: thread_num applies to OpenCV, operator_timeout
    is stored, an unknown parameter is fail-closed, and the settings persist."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    import cv2
    win._set_system_param("thread_num", 3)
    assert cv2.getNumThreads() == 3
    assert win._get_system_param("thread_num") == 3
    assert win._set_system_param("operator_timeout", 250) == 250
    assert win._get_system_param("operator_timeout") == 250
    assert win._state["system"]["operator_timeout_ms"] == 250
    assert win._get_system_param("check") == "on"          # runtime is fail-closed
    with pytest.raises(ValueError):
        win._set_system_param("operator_timeout", -1)
    with pytest.raises(ValueError):                        # unknown name -> fail-closed
        win._set_system_param("bogus_param", 1)
    with pytest.raises(ValueError):
        win._get_system_param("bogus_param")
    # persistence: a fresh window restores the stored timeout (offscreen QSettings = in-memory)
    win2, _ = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    assert win2._get_system_param("operator_timeout") == 250


def test_system_settings_dialog_constructs_headless():
    """Tools > System settings builds without blocking (exec stubbed to Cancel)."""
    from PySide6 import QtWidgets
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    orig = QtWidgets.QDialog.exec
    QtWidgets.QDialog.exec = lambda self: QtWidgets.QDialog.Rejected
    try:
        win._open_system_settings()
    finally:
        QtWidgets.QDialog.exec = orig
    assert win._system_dialog is not None
    assert win._act_system_settings.text().startswith("System settings")


def test_set_system_program_directive():
    """HALCON set_system(param, value) in a Program is a config directive (not a
    pipeline stage) and applies the setting."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    stages, errs = win._program["parse"]("set_system ('thread_num', 2)\ngaussian (0.5, 0.5)")
    assert not errs
    assert [s[0] for s in stages] == ["gaussian"]         # set_system is a directive, not a stage
    win._apply_dev_directives("set_system ('operator_timeout', 300)")
    assert win._get_system_param("operator_timeout") == 300
    assert studio.extract_dev_directives("set_system ('thread_num', 4)") == \
        [("set_system", ["thread_num", 4.0])]


def test_dev_region_draw_style_directives():
    """dev_set_draw / dev_set_color / dev_set_line_width change how a region result is
    drawn in the 'region overlay' display mode (HDevelop visualization ops)."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    win._apply_dev_directives(
        "dev_set_draw ('margin')\ndev_set_color ('red')\ndev_set_line_width (3)")
    d = win._state["draw"]
    assert d["mode"] == "margin"
    assert d["color"] == (1.0, 0.0, 0.0)
    assert d["line_width"] == 3
    win._apply_dev_directives("dev_set_draw ('fill')")
    assert win._state["draw"]["mode"] == "fill"


def test_apply_display_region_margin_vs_fill():
    """apply_display colours fewer pixels for a 'margin' region (boundary only) than a
    'fill' region, and both are non-empty."""
    base = np.zeros((40, 40), float)
    reg = np.zeros((40, 40), float); reg[10:30, 10:30] = 1.0        # a 20x20 filled square
    fill = studio.apply_display(reg, "region overlay", base=base,
                                draw={"mode": "fill", "color": (1, 0, 0), "alpha": 0.5})
    margin = studio.apply_display(reg, "region overlay", base=base,
                                  draw={"mode": "margin", "color": (1, 0, 0), "alpha": 0.5,
                                        "line_width": 1})
    n_fill = int((fill[..., 0] > 0.1).sum())
    n_margin = int((margin[..., 0] > 0.1).sum())
    assert 0 < n_margin < n_fill


def test_dev_disp_text_annotation():
    """dev_disp_text adds text annotations to the current window; a fresh render (or
    dev_clear_window) clears them, and it is a directive, not a pipeline stage."""
    from PySide6 import QtGui
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    view = win._current_view()
    view.set_pixmap(QtGui.QPixmap(48, 48))
    win._apply_text_directives("dev_disp_text ('OK', 5, 10)\ndev_disp_text ('pass')")
    assert len(view._text_items) == 2
    view.set_pixmap(QtGui.QPixmap(48, 48))                  # a fresh render clears stale text
    assert len(view._text_items) == 0
    stages, errs = win._program["parse"]("gaussian (0.5, 0.5)\ndev_disp_text ('hi', 2, 2)")
    assert not errs and [s[0] for s in stages] == ["gaussian"]   # directive, not a stage
    win._disp_text(3, 3, "x")
    assert len(view._text_items) == 1
    view.clear()
    assert len(view._text_items) == 0


def test_region_style_menu_syncs_with_draw_state():
    """View > Region style checkmarks track state['draw'] (set from menu or directive)."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    assert win._draw_mode_actions["fill"].isChecked()          # default
    win._set_draw_style(mode="margin", color=(0.0, 1.0, 0.0))
    assert win._draw_mode_actions["margin"].isChecked()
    assert win._draw_color_actions["green"].isChecked()
    assert win._state["draw"]["mode"] == "margin"


def test_sample_images_and_dev_visual_demo():
    """The collected license-clean sample images load, and the dev_* visualization
    demo loads a real image + a Program that actually USES the dev_* ops."""
    import sample_images
    assert "coins" in sample_images.names() and "blobs" in sample_images.names()
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    win._load_sample_image("blobs")
    assert model.image is not None and model.image.shape[:2] == (256, 256)
    win._load_visual_demo()
    assert [s[0] for s in model.stages] == ["gaussian", "otsu"]     # dev_* are directives
    assert win._state["draw"]["mode"] == "margin"                   # dev_set_draw applied
    assert win._state["draw"]["color"] == (0.0, 1.0, 1.0)           # dev_set_color('cyan')


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


def test_layout_presets_save_apply_delete():
    """v18.6 window freedom: named layout presets round-trip (save -> apply -> delete)
    and the Windows ▸ Layouts menu rebuilds to expose saved presets."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert callable(win._save_layout_preset) and callable(win._apply_layout_preset)
    assert win._save_layout_preset("wide-graphics") is True
    assert "wide-graphics" in win._preset_store
    # a blank name is rejected; unknown names apply/delete to False (no crash)
    assert win._save_layout_preset("   ") is False
    assert win._apply_layout_preset("wide-graphics") is True
    assert win._apply_layout_preset("nope") is False
    # the Layouts menu rebuilt without error and exposes the saved preset as flat
    # apply/delete actions (built-ins are always present too)
    texts = [a.text() for a in win._layouts_menu.actions()]
    assert "Balanced (default)" in texts and "Save current layout as…" in texts
    assert "Apply layout: wide-graphics" in texts
    assert "Delete layout: wide-graphics" in texts
    assert win._delete_layout_preset("wide-graphics") is True
    assert "Apply layout: wide-graphics" not in [a.text() for a in win._layouts_menu.actions()]
    assert "wide-graphics" not in win._preset_store
    assert win._delete_layout_preset("wide-graphics") is False


def test_builtin_layout_arrangements():
    """Built-in layouts deterministically arrange the tool docks (hide/show state is
    independent of top-level visibility, so it is assertable offscreen)."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    win._apply_builtin_layout("Graphics focus")
    assert win._docks["operators"].isHidden() and win._docks["display"].isHidden()
    assert not win._docks["pipeline"].isHidden()
    win._apply_builtin_layout("Code focus")
    assert win._docks["operators"].isHidden() and not win._docks["program"].isHidden()
    win._apply_builtin_layout("Balanced (default)")
    assert not any(win._docks[k].isHidden()
                   for k in ("operators", "pipeline", "display", "program", "variables"))


def test_detach_and_reattach_graphics_window():
    """A *non-primary* graphics window can be popped OUT of the MDI workspace into an
    independent top-level window and returned. The primary (resident) window refuses
    to detach — it hosts the always-present view + the global controls."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    n_sub0 = len(win._graphics_windows)
    assert n_sub0 >= 1 and not win._detached_graphics
    # the resident primary window cannot be detached (that would take the global
    # Load/Demo/Save/Zoom controls out of the workspace and could destroy them)
    assert win._detach_graphics(win._primary_gsub) is None
    assert len(win._graphics_windows) == n_sub0 and not win._detached_graphics
    # a second, disposable graphics window detaches and reattaches cleanly
    sub2 = win._new_graphics_window()
    n_sub1 = len(win._graphics_windows)
    assert n_sub1 == n_sub0 + 1
    top = win._detach_graphics(sub2)
    assert top is not None and top.isWindow()               # a real independent window
    assert len(win._detached_graphics) == 1
    assert len(win._graphics_windows) == n_sub1 - 1
    sub = win._reattach_graphics()
    assert sub is not None and not win._detached_graphics
    assert len(win._graphics_windows) == n_sub1
    # reattaching with nothing detached is a safe no-op
    assert win._reattach_graphics() is None


def test_primary_graphics_window_is_resident_and_uncloseable():
    """The primary graphics sub-window is the HDevelop-style resident window: closing
    it (its close button / system menu / Ctrl+W all route through a Close event) is
    vetoed so the image view + global controls are never destroyed."""
    from PySide6 import QtGui, QtWidgets
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    gsub = win._primary_gsub
    assert gsub.widget().objectName() == "graphics_primary"
    # a Close request must be ignored and the window must stay in the MDI
    ev = QtGui.QCloseEvent()
    QtWidgets.QApplication.sendEvent(gsub, ev)
    assert not ev.isAccepted(), "primary graphics window close was not vetoed"
    assert gsub in win._mdi.subWindowList()
    # calling close() likewise leaves it open
    assert gsub.close() is False
    assert gsub in win._mdi.subWindowList()


def test_update_actions_survives_a_deleted_control():
    """A queued action-sync must not raise if one of the tracked controls' C++ object
    was torn down (a graphics window closing can destroy an embedded button)."""
    import shiboken6
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    b = win._buttons["save_result"]
    # force the C++ object away, mimicking a torn-down window's child button
    shiboken6.delete(b)
    assert not shiboken6.isValid(b)
    win._update_actions()                     # must not raise despite the dead button


def test_function_key_shortcuts_step_from_any_panel():
    """F5 / F6 / Shift+F5 drive run-all / step / reset like a debugger, and fire even
    when a non-pipeline widget (here the Program editor) holds focus — unlike the
    Ctrl+Arrow keys which are scoped to the pipeline list."""
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtTest import QTest
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu"); m.add_stage("sobel_mag")
    win, model = studio.build_window(m)
    win.show(); QtWidgets.QApplication.processEvents()
    assert win._actions["dbg_step"].shortcut() == QtGui.QKeySequence("F6")
    assert win._actions["dbg_run"].shortcut() == QtGui.QKeySequence("F5")
    assert win._actions["dbg_reset"].shortcut() == QtGui.QKeySequence("Shift+F5")
    # focus a NON-pipeline widget to prove the key works window-wide
    editor = win._program["edit"]
    editor.setFocus(); QtWidgets.QApplication.processEvents()
    win._stage_list.setCurrentRow(-1)
    QTest.keyClick(editor, QtCore.Qt.Key_F6); QtWidgets.QApplication.processEvents()
    assert win._stage_list.currentRow() == 0, "F6 did not step to stage 1"
    QTest.keyClick(editor, QtCore.Qt.Key_F6); QtWidgets.QApplication.processEvents()
    assert win._stage_list.currentRow() == 1, "F6 did not step to stage 2"
    QTest.keyClick(editor, QtCore.Qt.Key_F5); QtWidgets.QApplication.processEvents()
    assert win._stage_list.currentRow() == len(model.stages) - 1, "F5 did not run all"


def test_current_graphics_window_model():
    """HDevelop current-window model: a variable "current" display and Run once target
    the CURRENT graphics window (not always a fresh one), handles are stable + rising,
    and the current pointer follows freshly-opened windows and heals to the primary."""
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian"); m.add_stage("otsu")
    from PySide6 import QtCore
    win, model = studio.build_window(m)
    disp = win._variables["display"]; lst = win._variables["list"]
    win._variables["refresh"](); lst.setCurrentRow(1)          # an iconic variable
    # current defaults to the resident primary window (handle 1)
    assert win._current_gfx is win._primary_gsub and win._current_handle() == 1
    g0 = len(win._graphics_windows)
    disp("current")                                            # → current window, no new window
    assert len(win._graphics_windows) == g0
    # opening a window makes it current with a fresh, higher handle
    sub2 = win._new_graphics_window()
    assert win._current_gfx is sub2 and win._current_handle() == 2
    g1 = len(win._graphics_windows)
    disp("current")                                            # reuses the secondary window
    assert len(win._graphics_windows) == g1
    # Run once reuses the current (secondary) window instead of spawning one
    ol = win._op_list
    idx = next(i for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == "gaussian")
    ol.setCurrentRow(idx)
    win._run_op_once()
    assert len(win._graphics_windows) == g1
    # back on the primary, Run once opens a fresh scratch window (never clobbers the result)
    win._set_current_gfx(win._primary_gsub)
    assert win._current_handle() == 1
    win._run_op_once()
    assert len(win._graphics_windows) == g1 + 1
    # explicit "new" always opens a window
    disp("new")
    assert len(win._graphics_windows) == g1 + 2
    # legacy booleans still work (True→new, False→main view = no new window)
    g2 = len(win._graphics_windows)
    disp(False)
    assert len(win._graphics_windows) == g2


def test_default_layout_is_image_dominant():
    """v18.8 (user-directed): the image (central MDI) is the largest surface and the
    Program panel is the second; op selection + Variables/Objects are compact panels.
    Every tool dock sits in the RIGHT column so the image keeps the whole left+centre,
    Program is its own (tall) panel, and the op/var panels are tabbed together (short)."""
    from PySide6 import QtCore, QtWidgets
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert isinstance(win.centralWidget(), QtWidgets.QMdiArea)          # image workspace is central
    # Program (code) = wide bottom strip; Operators = compact right column (visible)
    assert win.dockWidgetArea(win._docks["program"]) == QtCore.Qt.BottomDockWidgetArea
    assert win.dockWidgetArea(win._docks["operators"]) == QtCore.Qt.RightDockWidgetArea
    assert not win._docks["program"].isHidden() and not win._docks["operators"].isHidden()
    # the inspection panels start HIDDEN (on-demand) so the image owns the workspace
    for key in ("variables", "pipeline", "display"):
        assert win.dockWidgetArea(win._docks[key]) == QtCore.Qt.RightDockWidgetArea, key
        assert win._docks[key].isHidden(), "%s should start hidden (on-demand)" % key
    # each on-demand panel has a toggle action (toolbar + Window ▸ Panels) to bring it back
    for key in ("variables", "pipeline", "display"):
        assert win._docks[key].toggleViewAction() is not None


def test_operator_arg_labels_reflect_selected_op():
    """v18.8 P2b': the a/b knob labels name each argument's role for the selected op,
    a knob the op curates as unused is disabled, and an un-curated op keeps generic
    (never-falsely-unused) labels — so the user can judge what a/b do before setting them."""
    from PySide6 import QtCore
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    ol = win._op_list
    lbl_a, lbl_b = win._op_arg_labels
    sa, sb = win._op_arg_spins

    def select(op):
        idx = next(i for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == op)
        ol.setCurrentRow(idx)

    select("gaussian")                     # a = blur amount (named), b unused
    assert "a ·" in lbl_a.text() and lbl_a.text() != "a"
    assert lbl_b.text() == "b (–)" and not sb.isEnabled() and sa.isEnabled()
    select("bilateral")                    # both used + named + enabled
    assert "a ·" in lbl_a.text() and "b ·" in lbl_b.text()
    assert sa.isEnabled() and sb.isEnabled()
    select("otsu")                         # curated as both-unused
    assert lbl_a.text() == "a (–)" and lbl_b.text() == "b (–)"
    assert not sa.isEnabled() and not sb.isEnabled()
    # an un-curated op keeps the plain letters and both knobs enabled
    noncur = next(ol.item(i).data(QtCore.Qt.UserRole) for i in range(ol.count())
                  if ol.item(i).data(QtCore.Qt.UserRole) not in studio._ARG_ROLES)
    select(noncur)
    assert lbl_a.text() == "a" and lbl_b.text() == "b"
    assert sa.isEnabled() and sb.isEnabled()


def test_program_editor_tracks_unapplied_edits():
    """Codex #9: hand-written Program edits are not silently lost — typing marks the
    editor dirty, a pipeline refresh won't overwrite it, the discard guard warns about
    it, and Apply clears the flag."""
    import studio as S
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    prog = win._program
    ed = prog["edit"]
    assert not win._state["code_dirty"]
    ed.setPlainText("gaussian (2, 0)\n")                      # simulate typing
    assert win._state["code_dirty"] is True
    model.add_stage("otsu")                                   # a pipeline change...
    win._code_sync()                                         # ...must NOT clobber the edits
    assert "gaussian (2, 0)" in ed.toPlainText()
    assert win._state["code_dirty"] is True
    orig = S.CONFIRM_HOOK; asked = []
    S.CONFIRM_HOOK = lambda p, t, txt: (asked.append(txt), False)[1]
    try:
        assert win._confirm_discard("Quit") is False         # guard fires...
        assert asked and "unapplied Program edits" in asked[-1]
    finally:
        S.CONFIRM_HOOK = orig
    prog["apply"]()                                           # applying clears the flag
    assert win._state["code_dirty"] is False


def test_step_through_marks_variable_frontier():
    """Codex #8: during step-through, variables for stages past the current step read as
    'pending' (greyed) so future outputs don't look already-computed."""
    from PySide6 import QtCore
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    ol, ins = win._op_list, win._op_buttons["insert"]
    for op in ("gaussian", "invert", "otsu"):
        idx = next(i for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == op)
        ol.setCurrentRow(idx); ins.click()
    win._variables["refresh"]()
    lst = win._variables["list"]                              # rows: 0=input,1=st0,2=st1,3=st2
    win._step_to(0)                                           # frontier = stage 0
    texts = [lst.item(r).text() for r in range(lst.count())]
    assert "pending" not in texts[0] and "pending" not in texts[1]   # input + stage0 live
    assert "pending" in texts[2] and "pending" in texts[3]           # stage1, stage2 pending
    win._step_to(2)                                           # advance the frontier to the end
    texts = [lst.item(r).text() for r in range(lst.count())]
    assert not any("pending" in t for t in texts)                    # all live now


def test_undo_redo_pipeline_edits():
    """Codex #10: pipeline edits (insert / remove) can be undone and redone, and a fresh
    edit forks history (clears the redo stack)."""
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    ol, ins = win._op_list, win._op_buttons["insert"]

    def insert(op):
        from PySide6 import QtCore
        idx = next(i for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == op)
        ol.setCurrentRow(idx); ins.click()

    insert("gaussian"); insert("otsu")
    assert [s[0] for s in model.stages] == ["gaussian", "otsu"]
    assert win._actions["undo"].isEnabled() and not win._actions["redo"].isEnabled()
    win._actions["undo"].trigger()                       # undo the otsu insert
    assert [s[0] for s in model.stages] == ["gaussian"]
    assert win._actions["redo"].isEnabled()
    win._actions["undo"].trigger()                       # undo the gaussian insert
    assert model.stages == []
    win._actions["redo"].trigger(); win._actions["redo"].trigger()   # redo both
    assert [s[0] for s in model.stages] == ["gaussian", "otsu"]
    # a fresh edit after an undo forks history: redo becomes unavailable
    win._actions["undo"].trigger()                       # -> [gaussian]
    insert("invert")
    assert [s[0] for s in model.stages] == ["gaussian", "invert"]
    assert not win._actions["redo"].isEnabled()
    # remove is undoable too
    win._stage_list.setCurrentRow(1); win._actions["remove"].trigger()
    assert [s[0] for s in model.stages] == ["gaussian"]
    win._actions["undo"].trigger()
    assert [s[0] for s in model.stages] == ["gaussian", "invert"]


def test_holdout_metric_psnr_and_iou():
    """holdout_metric: PSNR for intensity images, IoU for binary masks, None when the
    pair can't be compared (so nothing is over-claimed)."""
    import numpy as np
    g = np.linspace(0, 1, 256).reshape(16, 16)
    assert studio.holdout_metric(g, g) >= 90                      # identical intensity -> ~99 dB
    b = np.zeros((16, 16)); b[:8] = 1.0
    c = np.zeros((16, 16)); c[:8] = 1.0
    assert studio.holdout_metric(b, c) == 1.0                     # identical binary -> IoU 1
    d = np.zeros((16, 16)); d[:4] = 1.0
    assert 0 < studio.holdout_metric(b, d) < 1                    # partial overlap
    assert studio.holdout_metric(g, np.zeros((8, 8))) is None     # shape mismatch -> None


def test_holdout_validation_runs_pipeline_over_a_folder(tmp_path):
    """Codex #12: run_holdout applies the pipeline to a validation image set, reporting
    per-image ran/failed + timing (and a metric when aligned ground truth is given), and
    a bad image is recorded rather than aborting the batch."""
    import numpy as np
    imgdir = tmp_path / "val"; imgdir.mkdir()
    paths = []
    for i in range(3):
        p = str(imgdir / ("img%d.png" % i))
        studio.api.write_image(p, np.random.default_rng(i).random((32, 32)))
        paths.append(p)
    stages = [("gaussian", 0.4, 0.5)]
    s = studio.run_holdout(stages, paths)
    assert s["n"] == 3 and s["n_ok"] == 3 and s["n_err"] == 0
    assert s["mean_ms"] >= 0 and s["mean_metric"] is None         # no ground truth -> no metric
    s2 = studio.run_holdout(stages, paths + [str(imgdir / "missing.png")])
    assert s2["n_ok"] == 3 and s2["n_err"] == 1                   # bad path recorded, batch survived
    s3 = studio.run_holdout(stages, paths, gt_paths=paths)        # aligned ground truth
    assert s3["mean_metric"] is not None and s3["metric_kind"] in ("PSNR(dB)", "IoU")


def test_holdout_action_and_report_are_wired():
    """The Studio exposes a holdout action + a report renderer over the summary."""
    from PySide6 import QtCore, QtGui, QtWidgets
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert win._actions["holdout"].shortcut() == QtGui.QKeySequence("Ctrl+H")
    assert callable(win._show_holdout)
    # the report renderer builds a table from a summary (dismiss the modal via a timer)
    summary = {"n": 2, "n_ok": 1, "n_err": 1, "mean_ms": 1.2, "mean_metric": 0.5,
               "metric_kind": "IoU",
               "results": [{"path": "a.png", "ok": True, "error": "", "ms": 1.2, "metric": 0.5},
                           {"path": "b.png", "ok": False, "error": "boom", "ms": 0.0, "metric": None}]}
    QtCore.QTimer.singleShot(0, lambda: (win._holdout_dialog.accept()
                                         if getattr(win, "_holdout_dialog", None) else None))
    win._show_holdout_report(summary)
    assert win._holdout_dialog is not None


def test_3d_surface_degrades_without_opengl(monkeypatch):
    """Offscreen (and any GL-less display session) has no usable OpenGL context, where
    Q3DSurface would segfault. show_3d_surface must return None instead, and open_3d
    must report it rather than crash."""
    _app()
    assert studio._opengl_available() is False           # offscreen platform
    assert studio.show_3d_surface(studio.demo_image(32)) is None
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    win._flash("clear")
    win._actions["surface_3d"].trigger()                 # must not crash
    # a message was flashed telling the user 3-D needs OpenGL
    assert "OpenGL" in win.statusBar().currentMessage() or win._surf is None


def test_float_single_panel():
    """Per-panel float control floats/re-docks one tool panel at a time."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert win._float_panel("operators", True) is True
    assert win._docks["operators"].isFloating() is True
    assert win._float_panel("operators", False) is True
    assert win._docks["operators"].isFloating() is False
    assert win._float_panel("no-such-panel", True) is False


def test_window_menu_is_grouped_into_submenus():
    """v18.7: the once-overloaded Window menu is now 3 clean submenus, not a flat wall."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    wmenu = win._menus["window"]
    # derive submenus fresh from the parent at access time (a separately-stored
    # submenu wrapper can go stale under shiboken's multi-wrapper handling)
    sub_by_title = {a.text(): a.menu() for a in wmenu.actions() if a.menu()}
    assert list(sub_by_title) == ["Panels", "Graphics windows", "Layout"]
    assert not [a for a in wmenu.actions() if not a.menu() and not a.isSeparator()]  # nothing flat
    panel_items = [a.text() for a in sub_by_title["Panels"].actions()]
    assert "Float: Operators" in panel_items and "Float all panels (multi-display)" in panel_items
    assert "Reset panel layout" in panel_items
    gfx_items = [a.text() for a in sub_by_title["Graphics windows"].actions()]
    assert "New graphics window" in gfx_items and "Detach graphics window" in gfx_items


def test_view_display_mode_menu_syncs_with_combo():
    """v18.7: colormap/display mode is reachable from View (was right-panel combo only)
    and the menu checkmark tracks the combo."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert win._display_menu is not None and "gray" in win._display_actions
    win._set_display_mode("gray")
    assert win._display_actions["gray"].isChecked()
    other = next(m for m in win._display_actions if m != "gray")
    win._set_display_mode(other)
    assert win._display_actions[other].isChecked() and not win._display_actions["gray"].isChecked()


def test_operator_panel_args_insert_and_run_once():
    """v18.7 P2b: the operator panel takes a, b arguments, inserts WITH them, and
    runs the op once (single-shot) showing the result in a graphics window without
    touching the pipeline (HDevelop operator-window flow)."""
    from PySide6 import QtCore
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    a_spin, b_spin = win._op_arg_spins
    ol = win._op_list
    idx = next(i for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == "gaussian")
    ol.setCurrentRow(idx)                                  # selecting enables insert + run-once
    assert win._op_buttons["insert"].isEnabled() and win._op_buttons["run_once"].isEnabled()
    a_spin.setValue(0.80); b_spin.setValue(0.30)
    # Insert uses the entered args
    n0 = len(model.stages)
    win._op_buttons["insert"].click()
    assert len(model.stages) == n0 + 1
    assert model.stages[-1][0] == "gaussian"
    assert abs(model.stages[-1][1] - 0.80) < 1e-6 and abs(model.stages[-1][2] - 0.30) < 1e-6
    # Run once = single-shot preview: opens a graphics window, pipeline unchanged
    g0 = len(win._graphics_windows); s0 = len(model.stages)
    win._run_op_once()
    assert len(win._graphics_windows) == g0 + 1        # result shown in a new graphics window
    assert len(model.stages) == s0                     # pipeline NOT modified
    assert win._last_run_once["op"] == "gaussian" and abs(win._last_run_once["a"] - 0.80) < 1e-6


def test_operator_autocomplete_selects_op():
    """v18.7 P2b: HDevelop-style autocomplete — the search field completes op names
    and picking a completion selects that operator in the list."""
    from PySide6 import QtCore
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    comp = win._op_completer
    assert comp is not None and comp.filterMode() == QtCore.Qt.MatchContains
    # the completion model covers real op names
    model_strs = [comp.model().data(comp.model().index(i, 0))
                  for i in range(comp.model().rowCount())]
    assert "gaussian" in model_strs
    # selecting a completion selects that op in the list
    assert win._select_op_in_list("gaussian") is True
    cur = win._op_list.currentItem()
    assert cur is not None and cur.data(QtCore.Qt.UserRole) == "gaussian"


def test_sample_pipeline_loads_and_gallery_reachable():
    """v18.7 P3: picking a sample loads it into the pipeline; the code gallery is
    reachable from the panel (not only the Help menu)."""
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    combo = win._samples
    assert combo.count() > 1                       # placeholder + real recipes
    win._state["dirty"] = False                    # nothing to discard -> no confirm dialog
    combo.setCurrentIndex(1)                        # fires load_sample
    assert len(model.stages) >= 1                   # the sample populated the pipeline
    assert win._browse_samples is not None and callable(win._show_samples)


def test_variable_window_thumbnails_and_iconic_control():
    """v18.7 P4a: iconic variables (image/region) show a shape thumbnail and are
    tagged iconic vs control — HDevelop's Variable Window model."""
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for op in ("gaussian", "otsu"):
        model.add_stage(op)
    v = win._variables
    v["refresh"]()
    lst = v["list"]
    n_icon = sum(1 for i in range(lst.count()) if not lst.item(i).icon().isNull())
    assert n_icon >= 2                                   # input + stage outputs are iconic
    texts = [lst.item(i).text() for i in range(lst.count())]
    assert any("iconic" in t for t in texts)


def test_contour_variable_gets_a_polyline_thumbnail():
    """A contour (XLD) variable is iconic in HDevelop — it now renders its polylines
    as a thumbnail instead of reading as an opaque 'control'. Non-null icon for a
    real contour set, still a (blank) icon for an empty one, and no crash on a
    degenerate contour (single point / wrong shape)."""
    import numpy as np
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    ci = win._contour_icon
    square = np.array([[4, 4], [4, 40], [40, 40], [40, 4], [4, 4]], float)   # (row,col)
    ic = ci({"shape": (48, 48), "cs": [square]})
    assert not ic.isNull()
    assert not ic.pixmap(44, 44).isNull()
    # empty XLD -> an honest blank thumbnail (still a valid icon, not None)
    assert not ci({"shape": (10, 10), "cs": []}).isNull()
    # degenerate contours must not crash the thumbnail
    assert not ci({"shape": (10, 10), "cs": [np.array([[1, 1]], float), np.zeros((0, 2))]}).isNull()


def test_contour_variable_is_tagged_iconic_in_the_list():
    """End-to-end: a pipeline ending in a contour op yields a variable row that is
    tagged 'iconic' and carries a (non-null) icon."""
    from PySide6 import QtCore
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    ol, ins = win._op_list, win._op_buttons["insert"]
    for op in ("otsu", "sk_find_contours"):
        idx = next((i for i in range(ol.count())
                    if ol.item(i).data(QtCore.Qt.UserRole) == op), None)
        if idx is None:
            import pytest
            pytest.skip("op %s not in registry" % op)
        ol.setCurrentRow(idx); ins.click()
    win._variables["refresh"]()
    lst = win._variables["list"]
    texts = [lst.item(i).text() for i in range(lst.count())]
    # the last variable is the contour output -> iconic, with an icon
    assert "iconic" in texts[-1]
    assert not lst.item(lst.count() - 1).icon().isNull()


def test_step_execution_syncs_variable_window():
    """v18.7 P4c: stepping to a stage highlights that stage's output variable in the
    Variable window (row 0 = input, row i+1 = stage i output) — HDevelop step sync."""
    from PySide6 import QtCore
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    ol, ins = win._op_list, win._op_buttons["insert"]
    for op in ("gaussian", "invert", "otsu"):
        idx = next(i for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == op)
        ol.setCurrentRow(idx); ins.click()
    win._step_to(1)
    assert win._stage_list.currentRow() == 1
    assert win._variables["list"].currentRow() == 2         # stage 1 output = variable row 2


def test_context_menus_on_lists():
    """v18.7 P4d: right-click context menus on the core lists (dev-IDE density —
    'act where you point', as the user asked)."""
    from PySide6 import QtCore
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    assert win._op_list.contextMenuPolicy() == QtCore.Qt.CustomContextMenu
    assert win._stage_list.contextMenuPolicy() == QtCore.Qt.CustomContextMenu
    assert win._variables["list"].contextMenuPolicy() == QtCore.Qt.CustomContextMenu
    # operator context menu offers insert / run-once / help when an op is selected
    idx = next(i for i in range(win._op_list.count())
               if win._op_list.item(i).data(QtCore.Qt.UserRole) == "gaussian")
    win._op_list.setCurrentRow(idx)
    olabels = [lbl for lbl, _ in win._ctx["operators"]()]
    assert "Run once (preview)" in olabels and any("Insert" in l for l in olabels)
    # pipeline context menu offers stage edits when a stage exists (add via the UI so
    # the stage list is populated, then select it)
    win._op_buttons["insert"].click()
    win._stage_list.setCurrentRow(0)
    slabels = [lbl for lbl, _ in win._ctx["pipeline"]()]
    assert "Remove stage" in slabels and "Run to here" in slabels
    # empty selection -> empty menu (no crash)
    win._op_list.setCurrentRow(-1)
    assert win._ctx["operators"]() == []


def test_tools_menu_holds_palette_and_language():
    """v18.7: Command palette (was in Run) and Language (was in Help) move to Tools."""
    _app()
    win, _ = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    ttexts = [a.text() for a in win._menus["tools"].actions()]
    assert any("palette" in t.lower() for t in ttexts)
    assert any("Language" in t for t in ttexts)
    assert not any("palette" in a.text().lower() for a in win._menus["run"].actions())
    assert not any("Language" in a.text() for a in win._menus["help"].actions())
