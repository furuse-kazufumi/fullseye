"""Studio input affordance (2026-09-03): per-op knob specs (param_specs), the
spec-driven knob widgets, right-click menus on every display view, secondary
graphics-window symmetry, operator-window -> program-line insertion, and the
small menu/formatting items.

The hand-written specs are checked AGAINST THE OP SOURCE: ``ops._k`` / ``ops._it``
are imported and the literal formulas from ops.py re-typed here, so a spec that
drifts from the implementation fails loudly rather than mislabelling a slider."""
from __future__ import annotations

import math
import os

import numpy as np
import pytest

import api
import ops
import param_specs as PS
import studio

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app():
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    studio.ERROR_HOOK = lambda *a: None
    studio.CONFIRM_HOOK = lambda *a: True
    return app


GRID = np.linspace(0.0, 1.0, 201)

# op -> {letter: python formula transcribed from ops.py / the backend source}
_FLOAT_FORMULAS = {
    "gaussian": {"a": lambda k: 0.3 + 2.7 * k},
    "gamma": {"a": lambda k: 0.5 + 1.5 * k},
    "scale_clip": {"a": lambda k: 0.5 + 1.5 * k, "b": lambda k: k - 0.5},
    "unsharp": {"a": lambda k: 1.5 * k, "b": lambda k: 0.5 + 1.5 * k},
    "bilateral": {"a": lambda k: 1.0 + 3.0 * k, "b": lambda k: 0.05 + 0.4 * k},
    "dog": {"a": lambda k: 0.5 + 2.0 * k, "b": lambda k: 1.0 + 4.0 * k},
    "sigmoid": {"a": lambda k: 4.0 + 12.0 * k, "b": lambda k: 0.2 + 0.6 * k},
    "lowpass": {"a": lambda k: 0.05 + 0.4 * k},
    "highpass": {"a": lambda k: 0.02 + 0.3 * k},
    "log": {"a": lambda k: 0.5 + 2.5 * k},
    "canny": {"a": lambda k: 0.5 + 1.5 * k, "b": lambda k: 0.1 + 0.5 * k},
    "local_max": {"b": lambda k: 0.3 + 0.4 * k},
    "dyn_threshold": {"b": lambda k: (k - 0.5) * 0.4},
    "adaptive_gauss_thresh": {"a": lambda k: 1.0 + 3.0 * k, "b": lambda k: (k - 0.5) * 0.3},
    "corner_response": {"a": lambda k: 0.5 + 2.0 * k},
    "rotate_img": {"a": lambda k: -45 + 90 * k},
    "rescale_img": {"a": lambda k: 0.7 + 0.6 * k},
    "affine_warp": {"a": lambda k: -20 + 40 * k, "b": lambda k: (k - 0.5) * 0.4},
    "gabor": {"a": lambda k: math.degrees(math.pi * k), "b": lambda k: 0.1 + 0.3 * k},
    "threshold": {"a": lambda k: k},
    "edges_sub_pix": {"a": lambda k: 0.15 + 0.5 * k},
    "decode_barcode": {"a": lambda k: 0.3 + 0.4 * k},
    "remove_small": {"a": lambda k: 0.01 + 0.15 * k},
    "clahe": {"b": lambda k: 256.0 ** k},
    "vol_gaussian": {"a": lambda k: 0.3 + 2.7 * k},
    "vol_threshold": {"a": lambda k: k},
    "aug_barrel": {"a": lambda k: 0.6 * k},
    "aug_rolling_shutter": {"a": lambda k: 0.25 * k},
    "sg_region_growing_seeded": {"a": lambda k: k},
}
_INT_FORMULAS = {
    "percentile": {"b": lambda k: int(5 + 90 * k)},
    "clahe": {"a": lambda k: 2 + int(k * 3)},
    "select_contours": {"a": lambda k: 3 + int(k * 40)},
    "smooth_contours": {"a": lambda k: 1 + int(k * 3)},
    "contours_to_region": {"a": lambda k: 1 + int(k * 2)},
    "convex_fill": {"a": lambda k: ops._it(k) + 2},
    "vol_reg_dilate": {"a": lambda k: max(1, 1 + int(k * 3))},
    "vol_reg_erode": {"a": lambda k: max(1, 1 + int(k * 3))},
    "vol_dilation_ball": {"a": lambda k: 1 + int(k * 3)},
    "vol_erosion_ball": {"a": lambda k: 1 + int(k * 3)},
    "vol_opening_ball": {"a": lambda k: 1 + int(k * 3)},
}
_KERNEL_OPS = ("mean_box", "median", "min_filter", "max_filter", "percentile", "gerode", "gdilate",
               "gopen", "gclose", "tophat", "bothat", "morph_grad", "std_filter", "dyn_threshold",
               "local_max")
_ITER_OPS = ("reg_erode", "reg_dilate", "reg_open", "reg_close")
_BOOL_FORMULAS = {
    "aug_barrel": {"b": lambda k: not (k < 0.5)},
    "aug_rolling_shutter": {"b": lambda k: not (k < 0.5)},
    "tm_fbp_reconstruct": {"b": lambda k: not (k < 0.5)},
    "sg_region_growing_seeded": {"b": lambda k: k > 0.5},
}


# --------------------------------------------------------------------------- #
# pure mapping
# --------------------------------------------------------------------------- #
def test_every_hand_spec_names_a_registered_op_and_is_complete():
    for name, both in PS.PARAM_SPECS.items():
        assert api.find_op(name) is not None, name
        for letter in ("a", "b"):
            sp = both[letter]
            for key in ("label", "kind", "min", "max", "step", "choices", "unit", "map", "doc", "source"):
                assert key in sp, (name, letter, key)
            assert sp["kind"] in ("float", "int", "choice", "bool", "unused")
            if sp["kind"] != "unused":
                assert sp["source"], "hand spec without a source formula: %s.%s" % (name, letter)


def test_round_trip_for_every_hand_spec():
    """knob -> display -> knob -> display is stable for every kind/map."""
    for name, both in PS.PARAM_SPECS.items():
        for letter in ("a", "b"):
            sp = both[letter]
            for k in GRID:
                d = PS.knob_to_display(sp, k)
                k2 = PS.display_to_knob(sp, d)
                assert 0.0 <= k2 <= 1.0
                d2 = PS.knob_to_display(sp, k2)
                if isinstance(d, float):
                    assert abs(d - d2) < 1e-9, (name, letter, k, d, d2)
                else:
                    assert d == d2, (name, letter, k, d, d2)
            # and display values that the op can actually show come back exactly
            if sp["kind"] == "int":
                for d in range(int(sp["min"]), int(sp["max"]) + 1):
                    assert PS.knob_to_display(sp, PS.display_to_knob(sp, d)) == d, (name, letter, d)
            if sp["kind"] == "choice":
                for i in range(len(sp["choices"])):
                    assert PS.knob_to_display(sp, PS.display_to_knob(sp, i)) == i


def test_float_specs_reproduce_the_op_formulas():
    for name, per in _FLOAT_FORMULAS.items():
        for letter, f in per.items():
            sp = PS.PARAM_SPECS[name][letter]
            assert sp["kind"] == "float", (name, letter)
            for k in GRID:
                assert PS.knob_to_display(sp, k) == pytest.approx(f(k), abs=1e-9), (name, letter, k)
            assert PS.knob_to_display(sp, 0.0) == pytest.approx(sp["min"])
            assert PS.knob_to_display(sp, 1.0) == pytest.approx(sp["max"])


def test_int_specs_reproduce_the_op_formulas():
    for name, per in _INT_FORMULAS.items():
        for letter, f in per.items():
            sp = PS.PARAM_SPECS[name][letter]
            assert sp["kind"] == "int", (name, letter)
            for k in GRID:
                assert PS.knob_to_display(sp, k) == f(k), (name, letter, k)


def test_kernel_choice_specs_reproduce_ops_k():
    """The (3, 5, 7, 9) kernel table is ops._k; the choice index must land on it."""
    for name in _KERNEL_OPS:
        sp = PS.PARAM_SPECS[name]["a"]
        assert sp["kind"] == "choice" and sp["choices"] == ["3", "5", "7", "9"], name
        for k in GRID:
            assert int(sp["choices"][PS.knob_to_display(sp, k)]) == ops._k(k), (name, k)
        for size in (3, 5, 7, 9):
            i = sp["choices"].index(str(size))
            assert ops._k(PS.display_to_knob(sp, i)) == size


def test_iteration_int_specs_reproduce_ops_it():
    for name in _ITER_OPS:
        sp = PS.PARAM_SPECS[name]["a"]
        assert sp["kind"] == "int" and (sp["min"], sp["max"]) == (1, 4), name
        for k in GRID:
            assert PS.knob_to_display(sp, k) == ops._it(k), (name, k)
        for it in (1, 2, 3, 4):
            assert ops._it(PS.display_to_knob(sp, it)) == it


def test_rescale_interpolation_choice_matches_source_table():
    sp = PS.PARAM_SPECS["rescale_img"]["b"]
    for k in GRID:
        order = (0, 1, 3, 3)[min(3, int(k * 4))]
        assert "(%d)" % order in sp["choices"][PS.knob_to_display(sp, k)], k


def test_bool_specs_reproduce_source_comparisons():
    for name, per in _BOOL_FORMULAS.items():
        for letter, f in per.items():
            sp = PS.PARAM_SPECS[name][letter]
            assert sp["kind"] == "bool"
            for k in GRID:
                assert PS.knob_to_display(sp, k) == f(k), (name, letter, k)
            assert PS.display_to_knob(sp, True) == 1.0 and PS.display_to_knob(sp, False) == 0.0


def test_specs_agree_with_the_ops_themselves():
    """Stronger than transcription: run the op and the underlying library call with
    the DISPLAYED parameter — they must produce the same pixels."""
    from scipy import ndimage
    img = studio.demo_image(40)
    for k in (0.0, 0.13, 0.5, 0.77, 1.0):
        sig = PS.knob_to_display(PS.PARAM_SPECS["gaussian"]["a"], k)
        assert np.allclose(api.apply(img, "gaussian", k, 0.5), ndimage.gaussian_filter(img, sigma=sig))
        ksp = PS.PARAM_SPECS["median"]["a"]
        size = int(ksp["choices"][PS.knob_to_display(ksp, k)])
        assert np.allclose(api.apply(img, "median", k, 0.5), ndimage.median_filter(img, size=size))
        ang = PS.knob_to_display(PS.PARAM_SPECS["rotate_img"]["a"], k)
        want = np.clip(ndimage.rotate(img, angle=ang, reshape=False, mode="reflect"), 0, 1)
        assert np.allclose(api.apply(img, "rotate_img", k, 0.5), want)
        region = (img > 0.5).astype(float)
        it = PS.knob_to_display(PS.PARAM_SPECS["reg_erode"]["a"], k)
        want = ndimage.binary_erosion(region > 0.5, iterations=it).astype(float)
        assert np.array_equal(api.apply(region, "reg_erode", k, 0.5), want)
        lvl = PS.knob_to_display(PS.PARAM_SPECS["threshold"]["a"], k)
        assert np.array_equal(api.apply(img, "threshold", k, 0.5), (img > lvl).astype(float))


def test_generic_fallback_and_helpers():
    g = PS.spec_for("no_such_op_xyz")
    assert PS.is_generic(g["a"]) and PS.is_generic(g["b"])
    assert PS.knob_to_display(g["a"], 0.37) == pytest.approx(0.37)
    assert PS.display_to_knob(g["a"], 0.37) == pytest.approx(0.37)
    assert PS.decimals_for(0.01) == 2 and PS.decimals_for(0.5) == 1 and PS.decimals_for(1) == 0
    assert PS.format_display(PS.PARAM_SPECS["gaussian"]["a"], 0.29) == "1.08 px"
    assert PS.format_display(PS.PARAM_SPECS["median"]["a"], 0.6) == "7 px"
    assert PS.format_display(PS.PARAM_SPECS["reg_erode"]["a"], 0.5) == "2"
    assert PS.format_display(PS.PARAM_SPECS["aug_barrel"]["b"], 0.9) == "on"
    assert PS.format_display(PS.UNUSED, 0.5) == "–"
    assert PS.spec_label(PS.PARAM_SPECS["gaussian"]["a"], "a") == "a · blur σ"
    assert PS.spec_label(PS.UNUSED, "b") == "b (–)"
    assert PS.spec_label(PS.GENERIC_FLOAT, "a") == "a"
    # out-of-range / non-finite input is clamped, never raises
    assert PS.knob_to_display(PS.PARAM_SPECS["gaussian"]["a"], 7.0) == pytest.approx(3.0)
    assert PS.display_to_knob(PS.PARAM_SPECS["gaussian"]["a"], float("nan")) == 0.0
    assert len(PS.hand_written_ops()) >= 60


# --------------------------------------------------------------------------- #
# seeding from docs / docstrings
# --------------------------------------------------------------------------- #
def test_seed_from_docs_mines_docstrings_label_only():
    seeded = PS.seed_from_docs()
    assert len(seeded) >= 30                       # backend docstrings ("``a`` sets the ...")
    for name, both in seeded.items():
        for letter in ("a", "b"):
            sp = both[letter]
            assert sp["kind"] in ("float", "unused")
            if sp["kind"] == "float":
                assert PS.is_generic(sp)            # a seed never invents a range
            if sp["label"] and sp["kind"] == "float":
                assert sp["source"] in ("docstring", "docs/ops")
    only = PS.seeded_ops()
    assert only and all(n not in PS.PARAM_SPECS for n in only)
    assert "aug_motion_blur" in seeded             # "``a`` sets the streak length ..."
    assert seeded["aug_motion_blur"]["a"]["label"]
    assert seeded["tm_fbp_reconstruct"]["a"]["kind"] == "unused" or \
        PS.PARAM_SPECS["tm_fbp_reconstruct"]["a"]["kind"] == "unused"   # "``a`` is unused"
    # spec_for prefers the hand table, then the seed, then generic
    assert PS.spec_for("gaussian")["a"]["kind"] == "float" and PS.spec_for("gaussian")["a"]["unit"] == "px"
    assert PS.spec_for(only[0])["a"]["label"] or PS.spec_for(only[0])["b"]["label"]


def test_seed_from_docs_reads_a_parameters_section(tmp_path):
    root = tmp_path / "ops"
    (root / "2d" / "x").mkdir(parents=True)
    (root / "2d" / "x" / "gaussian.md").write_text(
        "# gaussian\n\n## Parameters\n\n- **a**: blur radius in px\n- ``b`` — unused\n\n## Other\n",
        encoding="utf-8")
    seeded = PS.seed_from_docs(names=["gaussian"], docs_root=str(root))
    assert seeded["gaussian"]["a"]["label"] == "blur radius in px"
    assert seeded["gaussian"]["a"]["source"] == "docs/ops"
    assert seeded["gaussian"]["b"]["kind"] == "unused"
    assert PS.seed_from_docs(names=["no_such_op"], docs_root=str(root)) == {}


def test_step_summary_and_row_formatting():
    assert studio.fmt_num(12.0) == "12" and studio.fmt_num(0.41234) == "0.412"
    assert studio.fmt_shape((64, 64)) == "64×64"
    s = studio.step_summary({"kind": "image", "shape": (64, 64), "mean": 0.41234})
    assert s == "image 64×64 mean=0.412"
    assert studio.step_summary({"kind": "feature", "value": 3.0}) == "feature = 3"
    assert studio.stage_knob_text("gaussian", 0.29, 0.5) == "blur σ=1.08 px, b=–"
    assert studio.stage_knob_text("median", 0.6, 0.5) == "kernel=7 px, b=–"
    assert studio.stage_knob_text("no_such_op", 0.5, 0.25) == "a=0.50, b=0.25"


# --------------------------------------------------------------------------- #
# Studio widgets
# --------------------------------------------------------------------------- #
def _generic_op():
    """An image op with NO spec at all (hand or seeded): the generic two-knob look."""
    seeded = set(PS.seeded_ops())
    for r in api.list_ops():
        n = r["name"]
        if n not in PS.PARAM_SPECS and n not in seeded and r.get("backend") != "general" \
                and r["in_sort"] == "image" and r["out_sort"] == "image" \
                and api.find_op(n) is not None:
            return n
    pytest.skip("no generic image op")


def _build(*stages):
    _app()
    m = studio.PipelineModel(studio.demo_image(48))
    for st in stages:
        m.add_stage(*st)
    win, model = studio.build_window(m)
    win.show()
    return win, model


def test_stage_knob_widgets_follow_the_spec():
    """Pillar 1b: float -> unit spin + display-range slider, choice -> combo,
    int -> int spin snapping, bool -> checkbox; the model keeps the 0..1 knob."""
    generic = _generic_op()
    win, model = _build(("gaussian", 0.29, 0.5), ("median", 0.6, 0.5), ("reg_erode", 0.5, 0.5),
                        ("aug_barrel", 0.5, 0.2), (generic, 0.4, 0.6))
    ra, rb = win._knob_rows
    sl = win._stage_list
    try:
        sl.setCurrentRow(0)                                       # gaussian: σ = 0.3 + 2.7a
        assert ra.fspin.value() == pytest.approx(1.083, abs=1e-3) and ra.fspin.suffix() == " px"
        assert (ra.slider.minimum(), ra.slider.maximum()) == (0, 270) and ra.slider.value() == 78
        assert not ra.typed.isHidden() and ra.typed.currentWidget() is ra.fspin
        assert "blur σ" in ra.label.text() and "1.08 px" in ra.label.text()
        assert rb.spec["kind"] == "unused" and not rb.slider.isEnabled() and rb.raw.isEnabled()
        ra.fspin.setValue(2.0)                                    # typed σ -> knob (2.0-0.3)/2.7
        assert model.stages[0][1] == pytest.approx((2.0 - 0.3) / 2.7)
        assert model.stages[0][2] == 0.5                          # the other knob untouched
        assert ra.raw.value() == pytest.approx(0.63, abs=1e-3)
        ra.slider.setValue(0)                                     # slider -> σ 0.3 -> knob 0
        assert model.stages[0][1] == 0.0 and ra.fspin.value() == pytest.approx(0.3)
        ra.raw.setValue(1.0)                                      # raw spin stays the exact source
        assert model.stages[0][1] == 1.0 and ra.fspin.value() == pytest.approx(3.0)

        sl.setCurrentRow(1)                                       # median: kernel choice
        assert ra.typed.currentWidget() is ra.combo and ra.combo.count() == 4
        assert ra.combo.currentText() == "7 px" and ra.slider.isHidden()
        ra.combo.setCurrentIndex(3)
        assert ops._k(model.stages[1][1]) == 9

        sl.setCurrentRow(2)                                       # reg_erode: int 1..4
        assert ra.typed.currentWidget() is ra.ispin and ra.ispin.value() == 2
        assert (ra.slider.minimum(), ra.slider.maximum()) == (1, 4)
        ra.slider.setValue(4)
        assert ops._it(model.stages[2][1]) == 4 and ra.ispin.value() == 4
        ra.ispin.setValue(1)
        assert ops._it(model.stages[2][1]) == 1

        sl.setCurrentRow(3)                                       # aug_barrel: bool b
        assert rb.typed.currentWidget() is rb.check and rb.check.isChecked() is False
        rb.check.setChecked(True)
        assert model.stages[3][2] == 1.0
        assert model.stages[3][1] == 0.5

        sl.setCurrentRow(4)                                       # generic op: unchanged look
        assert ra.typed.isHidden() and rb.typed.isHidden()
        assert (ra.slider.minimum(), ra.slider.maximum()) == (0, 100)
        assert ra.slider.value() == 40 and ra.raw.value() == pytest.approx(0.4)
        ra.slider.setValue(70)
        assert model.stages[4][1] == pytest.approx(0.70)
        # rows show display units
        rows = [sl.item(i).text() for i in range(sl.count())]
        assert "blur σ=3.00 px" in rows[0] and "kernel=9 px" in rows[1] and "iterations=1" in rows[2]
        assert "pincushion=on" in rows[3] and "a=0.70" in rows[4]
    finally:
        win._knob_timer.stop(); win.close()


def test_operator_panel_typed_widgets_and_labels():
    from PySide6 import QtCore
    win, model = _build()
    ol = win._op_list
    ra, rb = win._op_knob_rows
    lbl_a, lbl_b = win._op_arg_labels
    a_spin, b_spin = win._op_arg_spins
    try:
        def select(op):
            idx = next(i for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == op)
            ol.setCurrentRow(idx)
        select("median")
        assert ra.typed.currentWidget() is ra.combo and lbl_a.text().startswith("a · kernel")
        assert lbl_b.text() == "b (–)" and not b_spin.isEnabled()
        a_spin.setValue(0.9)                                      # raw -> combo mirrors
        assert ra.combo.currentText() == "9 px"
        ra.combo.setCurrentIndex(0)                               # combo -> raw knob
        assert ops._k(a_spin.value()) == 3
        win._op_buttons["insert"].click()
        assert model.stages[-1][0] == "median" and ops._k(model.stages[-1][1]) == 3
        select("reg_erode")
        assert ra.typed.currentWidget() is ra.ispin and "iterations" in lbl_a.text()
    finally:
        win._knob_timer.stop(); win.close()


def test_insert_writes_program_line_at_cursor_and_keeps_stage_lines():
    """Pillar 4: the operator window's Insert is HDevelop's — the program gains
    `<op> (a, b)` (full-precision repr) at the cursor AND the pipeline the stage."""
    from PySide6 import QtCore
    win, model = _build(("gaussian", 0.5, 0.5), ("otsu", 0.5, 0.5))
    ed = win._program["edit"]
    ol = win._op_list
    a_spin, b_spin = win._op_arg_spins
    try:
        assert ed.toPlainText().splitlines() == ["gaussian (0.5, 0.5)", "otsu (0.5, 0.5)"]
        win._stage_list.setCurrentRow(0)                          # cursor follows -> line 1
        assert ed.textCursor().blockNumber() + 1 == 1
        idx = next(i for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == "median")
        ol.setCurrentRow(idx)
        a_spin.setValue(0.12345); b_spin.setValue(0.5)
        win._op_buttons["insert"].click()
        lines = ed.toPlainText().splitlines()
        assert lines == ["gaussian (0.5, 0.5)", "median (0.12345, 0.5)", "otsu (0.5, 0.5)"]
        assert [s[0] for s in model.stages] == ["gaussian", "median", "otsu"]
        assert model.stages[1][1] == pytest.approx(0.12345)
        assert win._state["stage_lines"] == [1, 2, 3]
        assert ed.textCursor().blockNumber() + 1 == 2             # cursor on the new line
        assert win._state["code_dirty"] is False
        # no selection -> the line goes after the last op
        win._stage_list.setCurrentRow(-1)
        win._place_program_cursor(ed.document().blockCount())
        win._op_buttons["insert"].click()
        assert ed.toPlainText().splitlines()[-1].startswith("median (") and model.stages[-1][0] == "median"
        assert win._state["stage_lines"] == [1, 2, 3, 4]
        # unapplied hand edits: the LINE is inserted at the cursor, the model waits for Apply
        ed.setPlainText("gaussian (0.5, 0.5)\n* note\n")
        assert win._state["code_dirty"] is True
        n = len(model.stages)
        win._place_program_cursor(1)
        win._op_buttons["insert"].click()
        assert ed.toPlainText().splitlines()[1].startswith("median (")
        assert len(model.stages) == n                            # untouched until Apply
        win._program["apply"]()
        assert [s[0] for s in model.stages] == ["gaussian", "median"]
    finally:
        win._knob_timer.stop(); win.close()


def _ctx_event(widget):
    from PySide6 import QtCore, QtGui
    p = QtCore.QPoint(12, 12)
    return QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, p, widget.mapToGlobal(p))


def test_context_menus_on_every_display_view():
    """Pillar 2: right-click on the primary view, a secondary view and the 3-D viewer
    offers the same actions the toolbar / menus offer for that view (same QAction
    objects — no duplicated handlers)."""
    from PySide6 import QtWidgets
    win, model = _build(("gaussian", 0.5, 0.5))
    try:
        main = next(w for w in win.findChildren(QtWidgets.QGraphicsView) if w.accessibleName() == "image view")
        type(main).CONTEXT_MENU_EXEC = False
        main.contextMenuEvent(_ctx_event(main))
        acts = main._last_context_menu.actions()
        texts = [a.text() for a in acts if not a.isSeparator()]
        A = win._actions
        assert acts[0] is A["fit"] and A["actual_size"] in acts and A["zoom_in"] in acts \
            and A["zoom_out"] in acts and A["save_result"] in acts and A["save_view"] in acts \
            and A["copy_result"] in acts and A["surface_3d"] in acts
        assert "Display mode" in texts                            # the View > Display mode submenu
        # secondary graphics window: its own Fit / 1:1 / zoom / save / copy
        sub = win._new_graphics_window()
        gv = sub.widget()
        gv.contextMenuEvent(_ctx_event(gv))
        s_texts = [a.text() for a in gv._last_context_menu.actions() if not a.isSeparator()]
        assert s_texts == ["Fit to window", "Actual size (1:1)", "Zoom in", "Zoom out", "Save image…", "Copy image"]
        assert [a.text() for a in gv._last_context_menu.actions()][:4] == [A[k].text() for k in
                                                                            ("fit", "actual_size", "zoom_in", "zoom_out")]
        # 3-D viewer
        v3 = win._open_viewer3d_window()
        w3 = v3._fs_viewer3d
        type(w3).CONTEXT_MENU_EXEC = False
        w3.contextMenuEvent(_ctx_event(w3))
        t3 = [a.text().split("\t")[0] for a in w3._last_context_menu.actions() if not a.isSeparator()]
        assert t3 == ["Reset view", "First-person walkthrough (perspective)", "Wireframe", "Save screenshot…"]
        assert not w3.actions["wireframe"].isEnabled()             # a point cloud has no edges
        w3.actions["first_person"].trigger(); assert w3._fp is True
        w3.actions["reset_view"].trigger()
        w3.actions["first_person"].trigger(); assert w3._fp is False
        shots = []
        w3.screenshot_cb = lambda v: shots.append(v)
        w3.actions["screenshot"].trigger(); assert shots == [w3]
        # a mesh enables wireframe, and the action toggles it (same as the W key)
        import mesh as meshmod
        V, F = meshmod.make_cube() if hasattr(meshmod, "make_cube") else (
            np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1.0]]), np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]))
        w3.set_mesh(V, F)
        w3.build_context_menu()
        assert w3.actions["wireframe"].isEnabled()
        w3.actions["wireframe"].trigger(); assert w3._wire is True
    finally:
        win._knob_timer.stop(); win.close()


def test_secondary_graphics_window_symmetry():
    """Pillar 3: a secondary graphics window has Fit / 1:1 / zoom / Save controls
    (not just wheel zoom) and Fit changes the transform."""
    from PySide6 import QtGui
    win, model = _build(("gaussian", 0.5, 0.5))
    try:
        sub = win._new_graphics_window()
        gv = sub.widget()
        assert set(gv.tool_buttons) == {"fit", "actual_size", "zoom_in", "zoom_out", "save"}
        for key, b in gv.tool_buttons.items():
            assert b.defaultAction() is gv.actions[key] and b.isVisible()
        pm = QtGui.QPixmap(600, 400); pm.fill(QtGui.QColor("white"))
        gv.set_pixmap(pm)
        gv.actions["actual_size"].trigger()
        t0 = gv.transform()
        assert t0.m11() == 1.0
        gv.tool_buttons["zoom_in"].click()
        assert gv.transform().m11() == pytest.approx(1.25)
        gv.tool_buttons["fit"].click()
        assert gv.transform().m11() != pytest.approx(1.25)        # fit re-scaled the view
        assert gv.transform().m11() < 1.0                          # 600 px into a 440 px window
        saved = []
        gv.save_cb = lambda v: saved.append(v)
        gv.tool_buttons["save"].click()
        assert saved == [gv]
        assert win._save_secondary_view is not None
    finally:
        win._knob_timer.stop(); win.close()


def test_small_items_menu_find_unified_run_and_min_size():
    win, model = _build(("gaussian", 0.5, 0.5), ("invert", 0.5, 0.5), ("otsu", 0.5, 0.5))
    try:
        edit_actions = win._menus["edit"].actions()
        assert win._actions["focus_search"] in edit_actions          # Ctrl+F is in a menu now
        assert win._actions["focus_search"].shortcut().toString() == "Ctrl+F"
        # Run / Step / Reset: buttons and menu actions share one handler each
        win._stage_list.setCurrentRow(0)
        win._buttons["step"].click(); assert win._stage_list.currentRow() == 1
        win._actions["step"].trigger(); assert win._stage_list.currentRow() == 2
        win._buttons["reset"].click(); assert win._state["view_raw"] is True
        win._actions["run_all"].trigger(); assert win._stage_list.currentRow() == 2
        assert callable(win._do_step) and callable(win._do_run_all) and callable(win._do_reset)
        assert win.minimumWidth() >= 800 and win.minimumHeight() >= 500
    finally:
        win._knob_timer.stop(); win.close()
