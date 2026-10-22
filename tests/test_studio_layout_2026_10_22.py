"""Studio slice 10: work modes preserve work while changing panel layout."""
import time

import pytest

import studio_layout as layout


def test_presets_have_known_panels_and_requested_large_surfaces():
    assert set(layout.MODES) == {"build", "compare", "inspect", "code"}
    assert [layout.MODES[key].large for key in layout.MODES] == ["result", "ab", "display", "program"]
    for mode in layout.MODES.values():
        assert mode.visible <= layout.PANELS.keys()
        assert mode.collapsed <= layout.PANELS.keys()
        assert mode.large in mode.visible


def test_mode_specific_overrides_win_and_do_not_leak():
    state = layout.set_override(layout.LayoutState(), "variables", visible=True)
    assert state.panels["variables"]["visible"]
    state = layout.apply_mode(state, "code")
    assert not state.panels["variables"]["visible"]
    state = layout.apply_mode(state, "build")
    assert state.panels["variables"]["visible"]


def test_focus_image_restores_flags_exactly():
    state = layout.set_override(layout.LayoutState(), "pipeline", visible=True, collapsed=True)
    before = {key: dict(value) for key, value in state.panels.items()}
    focused = layout.toggle_focus_image(state)
    assert focused.focus_image
    assert [key for key, value in focused.panels.items() if value["visible"]] == ["result"]
    restored = layout.toggle_focus_image(focused)
    assert restored.panels == before and not restored.focus_image


def test_search_uses_japanese_and_english_aliases():
    assert layout.find_panels("ヒストグラム") == ["display"]
    assert layout.find_panels("histogram") == ["display"]
    assert "ab" in layout.find_panels("結果比較")


def test_json_round_trip_missing_defaults_and_unknown_ids_rejected():
    state = layout.set_override(layout.apply_mode(layout.LayoutState(), "inspect"),
                                "program", visible=True)
    assert layout.from_json(layout.to_json(state)) == state
    minimal = layout.from_json('{"mode":"code"}')
    assert minimal.panels == layout.apply_mode(layout.LayoutState(), "code").panels
    for value, name in [('{"mode":"mystery"}', "mystery"),
                        ('{"mode":"build","panels":{"ghost":{}}}', "ghost"),
                        ('{"mode":"build","overrides":{"build":{"ghost":{}}}}', "ghost")]:
        with pytest.raises(ValueError, match=name):
            layout.from_json(value)
    with pytest.raises(ValueError, match="ghost"):
        layout.set_override(layout.LayoutState(), "ghost", visible=True)


def test_gui_modes_focus_and_search_are_model_neutral(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtCore, QtGui, QtWidgets
    import studio

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window(); win.show()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        app.processEvents(); time.sleep(0.01)
        if win.isVisible():
            break
    assert set(win._layout_panels) == set(layout.PANELS)
    assert set(win._docks) == set(layout.PANELS) - {"result"}
    result = win._state["result"]
    dirty = win._state["dirty"]
    generation = win._run_controller.generation
    for mode_id, mode in layout.MODES.items():
        win._set_work_mode(mode_id); app.processEvents()
        for panel, dock in win._docks.items():
            flags = win._layout_state.panels[panel]
            assert dock.isVisible() == (flags["visible"] and not flags["collapsed"])
        assert win._state["result"] is result
        assert win._state["dirty"] == dirty
        assert win._run_controller.generation == generation
    before = {panel: dock.isVisible() for panel, dock in win._docks.items()}
    win._toggle_focus_image(True); app.processEvents()
    assert not any(dock.isVisible() for dock in win._docks.values())
    QtWidgets.QApplication.sendEvent(win, QtGui.QKeyEvent(
        QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier))
    app.processEvents()
    assert {panel: dock.isVisible() for panel, dock in win._docks.items()} == before
    dialog = win._find_panel_dialog(); dialog.findChild(QtWidgets.QLineEdit).setText("histogram")
    app.processEvents()
    assert dialog.findChild(QtWidgets.QListWidget).count() == 1
    dialog.close(); win.quiesce(); win.close_guard = lambda: True; win.close(); app.processEvents()
