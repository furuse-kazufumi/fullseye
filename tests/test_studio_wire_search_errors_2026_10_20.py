"""Studio slice 4: purpose search and actionable failures are wired to Qt."""
import os

import numpy as np
import pytest

import studio

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app():
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _window(value=None):
    _app()
    studio.ERROR_HOOK = lambda *_args: None
    studio._UI_LANG["code"] = "en"
    return studio.build_window(studio.PipelineModel(
        studio.demo_image(48) if value is None else value))


def test_search_is_grouped_for_region_and_image_and_has_bridge(monkeypatch):
    win, model = _window(np.eye(48, dtype=bool))
    ui = win._search_ui
    ui["search_now"]("小さい領域を消す")
    rows = ui["rows"]()
    applicable = rows["applicable"]
    assert applicable
    assert any(r["name"] == "remove_small" for r in applicable)
    bridge = [r for r in rows["needs_preprocessing"] if r["name"] == "sk_area_opening"]
    assert len(bridge) == 1 and "→" in bridge[0]["text"]
    model.set_image(studio.demo_image(48))
    ui["search_now"]("小さい領域を消す")
    rows2 = ui["rows"]()
    assert [r["name"] for r in rows2["applicable"]] != [r["name"] for r in rows["applicable"]]
    win.close()


def test_search_debounce_zero_recovery_try_once_and_unavailable(monkeypatch):
    win, model = _window()
    ui = win._search_ui
    calls = []
    real = studio.search_grouped

    def counted(*args, **kwargs):
        calls.append((args, kwargs))
        if args and args[0] == "zzzzzz-no-result":
            return {"applicable": [], "needs_preprocessing": [], "other": []}
        if args and args[0] == "unavailable-case":
            return {"applicable": [{"name": "missing_op", "label": "Missing", "in_sort": "image",
                                     "out_sort": "image", "why": ["name"], "tier": "unavailable",
                                     "bridge": []}], "needs_preprocessing": [], "other": []}
        return real(*args, **kwargs)
    monkeypatch.setattr(studio, "search_grouped", counted)
    for text in ("g", "ga", "gau", "gaus", "gauss", "gaussi", "gaussian", "gaussian ", "gaussian b", "gaussian bl"):
        ui["edit"].setText(text)
    _app().processEvents()
    ui["timer"].timeout.emit()
    assert calls
    limits = [c[1].get("k", 20) for c in calls]
    assert limits
    assert len(calls) <= 2 and max(limits) <= 40
    ui["search_now"]("zzzzzz-no-result")
    assert len(ui["chips"]()) >= 1
    before = len(calls)
    ui["chips"]()[0].click()
    assert len(calls) > before
    nstage = len(model.stages)
    op_calls = []
    monkeypatch.setattr(studio.api, "apply", lambda value, name, a, b: op_calls.append(name) or value)
    ui["search_now"]("gaussian")
    ui["try"]("gaussian")
    assert op_calls == ["gaussian"] and len(model.stages) == nstage
    ui["search_now"]("unavailable-case")
    unavailable = ui["rows"]()["applicable"]
    assert len(unavailable) == 1 and not unavailable[0]["try_button"].isEnabled()
    win.close()


def test_report_error_formats_sections_status_and_log(monkeypatch):
    win, _model = _window()
    left, right = np.zeros((12, 20)), np.zeros((8, 10))
    exc = ValueError("left/right must be equal-shape 2-D arrays")
    win._report_error("stereo", exc, op_name="disparity_map", stage_index=1,
                      inputs={"left": left, "right": right})
    item = win._problems_list.item(win._problems_list.count() - 1)
    text = item.text()
    assert "Cause" in text and "Place" in text and "What you can do next" in text
    assert "20×12" in text and "10×8" in text
    buttons = win._problem_buttons(item)
    assert {b.property("action_kind") for b in buttons} >= {
        "reselect_input", "show_inputs_side_by_side", "open_log"}
    assert win.statusBar().currentMessage()
    buttons[[b.property("action_kind") for b in buttons].index("open_log")].click()
    assert "equal-shape" in win._last_error_log.toPlainText()
    win.close()


def test_nan_report_contains_count_and_all_rendered_kinds_are_allowed():
    win, _model = _window()
    value = np.array([1.0, np.nan, np.inf])
    win._report_error("run", ValueError("input has non-finite values"), op_name="spc_cusum",
                      stage_index=0, inputs=[value])
    item = win._problems_list.item(win._problems_list.count() - 1)
    assert "2" in item.text() and "Cause" in item.text()
    import studio_errors
    assert {b.property("action_kind") for b in win._problem_buttons(item)} <= studio_errors.ACTION_KINDS
    win.close()
