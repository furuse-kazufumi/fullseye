"""Studio の破棄済み Qt オブジェクト参照による native crash の回帰試験。"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ROOT = Path(__file__).resolve().parents[1]
_CHILD_TIMEOUT_SECONDS = 120
_DELETED_TOOL_CHILD = r"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shiboken6
from PySide6 import QtWidgets

import studio

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
first, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
shiboken6.delete(first._buttons["save_result"])
second, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
second.show()
app.processEvents()
print("survived", flush=True)
"""


@pytest.fixture(scope="module")
def qapp():
    from PySide6 import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "studio.ini"))


def _close_window(win):
    win.close_guard = lambda: True
    win.quiesce()
    win.close()


def test_image_strip_forgets_a_deferred_deleted_tool(qapp):
    from PySide6 import QtCore, QtWidgets
    import shiboken6
    import studio
    import studio_panels

    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    try:
        rows = [row for row in studio_panels.panel_ledger(win)
                if row["kind"] == "image" and row["key"] == "graphics_1"]
        assert len(rows) == 1
        strip = rows[0]["strip"]
        button = win._panel_buttons["graphics_1"]["zoom_in"]
        assert any(item is button for item in strip.items())

        button.deleteLater()
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

        assert not shiboken6.isValid(button)
        assert all(item is not button for item in strip.items())
        assert strip.sizeHint().isValid()
    finally:
        _close_window(win)


def test_deleted_image_tool_does_not_crash_the_next_window(tmp_path):
    pytest.importorskip("PySide6")
    child_data = tmp_path / "child-data"
    child_data.mkdir()
    env = dict(
        os.environ,
        APPDATA=str(child_data),
        LOCALAPPDATA=str(child_data),
        FULLSEYE_STUDIO_SETTINGS=str(child_data / "studio.ini"),
        PYTHONPATH=str(_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
        PYTHONUTF8="1",
        QT_QPA_PLATFORM="offscreen",
    )
    result = subprocess.run(
        [sys.executable, "-c", _DELETED_TOOL_CHILD],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_CHILD_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0 and "survived" in result.stdout, (
        result.returncode,
        result.stdout[-400:],
        result.stderr[-1500:],
    )


def test_language_refill_discards_grouped_search_state(qapp):
    from PySide6 import QtCore
    import studio

    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    try:
        win._search_ui["search_now"]("gauss")
        assert sum(len(rows) for rows in win._search_ui["rows"]().values()) > 0
        rows_at_widget_destruction = []
        boxes = [entry["box"] for rows in win._search_ui["rows"]().values() for entry in rows]
        for box in boxes:
            box.destroyed.connect(
                lambda _obj=None: rows_at_widget_destruction.append(
                    sum(len(rows) for rows in win._search_ui["rows"]().values())
                )
            )
        edit = win._search_ui["edit"]
        edit.blockSignals(True)
        edit.setText("")
        edit.blockSignals(False)

        win._apply_language("ja")
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)   # the old row widgets go

        assert sum(len(rows) for rows in win._search_ui["rows"]().values()) == 0
        assert rows_at_widget_destruction and set(rows_at_widget_destruction) == {0}
        assert win._search_ui["chips"]() == []
        op_list = win._search_ui["list"]
        group_heads = [op_list.item(index) for index in range(op_list.count())
                       if op_list.item(index).data(QtCore.Qt.UserRole + 4) is not None]
        assert group_heads == []
    finally:
        win._apply_language("en")
        _close_window(win)
