"""Fullseye Studio: headless PipelineModel logic + an offscreen Qt smoke test."""
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
