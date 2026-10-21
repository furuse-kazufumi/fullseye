"""Studio slice 7: exported-Python round-trip verification."""
import numpy as np
import pytest

import studio
import studio_roundtrip as rt


def _model():
    model = studio.PipelineModel(studio.demo_image(24))
    model.add_stage("gaussian", 0.123456789, 0.5)
    model.add_stage("invert", 0.25, 0.75)
    return model


def test_exported_pipeline_matches_every_gui_stage_in_isolated_python():
    model = _model()
    gui = {i: model.result_upto(i) for i in range(len(model.stages))}
    exported = rt.run_exported(rt.export_script(model, {"sha256": "abc"}), model.image)
    report = rt.compare_results(gui, exported, atol=0, rtol=0, nan_policy="same_positions")
    assert report.ok
    assert report.first_mismatch is None
    assert set(exported) == {0, 1}


def test_one_line_per_op_and_changed_second_stage_is_located():
    model = _model()
    script = rt.export_script(model)
    assert script.count("fullseye.run_pipeline") == 2
    changed = script.replace("('invert', 0.25, 0.75)", "('sobel_amp', 0.25, 0.75)")
    gui = {i: model.result_upto(i) for i in range(2)}
    report = rt.compare_results(gui, rt.run_exported(changed, model.image), atol=0, rtol=0,
                                nan_policy="same_positions")
    assert not report.ok
    assert report.first_mismatch == 1


def test_nan_policies_are_explicit():
    gui = {0: np.array([1.0, np.nan])}
    other = {0: np.array([1.0, 2.0])}
    assert not rt.compare_results(gui, other, atol=0, rtol=0,
                                  nan_policy="same_positions").ok
    assert rt.compare_results(gui, other, atol=0, rtol=0, nan_policy="ignore").ok
    assert not rt.compare_results(gui, gui, atol=0, rtol=0, nan_policy="strict").ok
    with pytest.raises(ValueError):
        rt.compare_results(gui, other, atol=0, rtol=0, nan_policy="guess")


def test_dtype_difference_fails_even_when_values_match():
    report = rt.compare_results({0: np.ones(3, np.float32)}, {0: np.ones(3, np.float64)},
                                atol=0, rtol=0, nan_policy="same_positions")
    assert not report.ok
    assert report.stages[0].values_ok
    assert not report.stages[0].dtype_ok


def test_gui_exposes_roundtrip_action():
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window, _model_ = studio.build_window()
    assert window._actions["verify_exported"].isEnabled()
    window._actions["verify_exported"].trigger()
    app.processEvents()
    assert window._roundtrip_dlg.isVisible()
    window.close_guard = lambda: True
    window.close()
