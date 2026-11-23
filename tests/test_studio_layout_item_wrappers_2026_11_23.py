"""Studio が Qt の配置の項目(QWidgetItem / QSpacerItem)の wrapper を残さない事の回帰試験(2026-11-23)。

原因(Windows / Python 3.11 の native crash、Linux CI の SIGABRT の連鎖): Qt の配置の項目は QObject ではないので、
Qt が消しても PySide は知らない。Python から ``layout.itemAt(i)`` を呼ぶと PySide はその項目の wrapper を作り、
しかも配置の子として持ち続ける(``addownership-item-at``)。項目が Qt に消された後も wrapper は shiboken の
wrapper の表にその番地のまま残り、同じ番地に後から作られた物(検索の一覧の QListWidgetItem)が消える時に
``Shiboken::Object::destroy`` が解放済みの wrapper を ``releaseWrapper`` に渡して落ちた
(``op_list.clear()`` ← ``apply_language`` ← 言語の切り替え。密度の掛け直しが窓の全ての配置を itemAt で歩いていた)。
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ROOT = Path(__file__).resolve().parents[1]
#: 子プロセスの上限(窓を作らない小さな試験。遅い CI でも余る値)。
_CHILD_TIMEOUT_SECONDS = 180
#: 子プロセスで並べるラベルの数(消した項目の番地が、後の項目に再使用される機会)。
_LABELS_IN_CHILD = 200
#: 子プロセスで作る一覧の項目の数(消えた配置の項目の番地に当たるまで作る上限)。
_LIST_ITEMS_IN_CHILD = 20000
#: 言語の切り替えの後に待つ秒数(遅延の削除と再描画が落ち着くまで)。
_PUMP_SECONDS = 0.2

# 密度の掛け直し(言語・配色の切り替えのたびに走る)の後で配置の部品を消し、同じ番地に一覧の項目を作って消す。
# 直す前: 密度の掛け直しが残した項目の wrapper の番地に一覧の項目が入り、clear() で落ちた(Windows で 4 個目)。
_DENSITY_THEN_REUSE_CHILD = r"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shiboken6
from PySide6 import QtCore, QtWidgets

import studio

LABELS = int(sys.argv[1])
LIST_ITEMS = int(sys.argv[2])
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def qt_made_item_addresses():
    return {shiboken6.getCppPointer(w)[0] for w in shiboken6.getAllValidWrappers()
            if isinstance(w, QtWidgets.QLayoutItem) and not isinstance(w, QtCore.QObject)
            and not shiboken6.createdByPython(w)}


host = QtWidgets.QWidget()
outer = QtWidgets.QVBoxLayout(host)
row = QtWidgets.QHBoxLayout()
outer.addLayout(row)
labels = [QtWidgets.QLabel("x%d" % i) for i in range(LABELS)]
for i, label in enumerate(labels):
    (row if i % 2 else outer).addWidget(label)
outer.addStretch(1)
before = qt_made_item_addresses()
studio._apply_density(host)
kept = qt_made_item_addresses() - before
print("kept", len(kept), flush=True)
for label in labels:
    label.deleteLater()
del label, labels
QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
app.processEvents()
lw = QtWidgets.QListWidget()
landed = 0
for _ in range(LIST_ITEMS):
    item = QtWidgets.QListWidgetItem("r")
    lw.addItem(item)
    landed += shiboken6.getCppPointer(item)[0] in kept
del item
print("landed", landed, flush=True)
lw.clear()
print("survived", flush=True)
"""


@pytest.fixture(scope="module")
def qapp():
    from PySide6 import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "studio.ini"))


def _qt_made_layout_items():
    """PySide に登録されている、Qt が作った配置の項目の wrapper(Python で作った物と QLayout は除く)。"""
    from PySide6 import QtCore, QtWidgets
    import shiboken6

    return [w for w in shiboken6.getAllValidWrappers()
            if isinstance(w, QtWidgets.QLayoutItem) and not isinstance(w, QtCore.QObject)
            and not shiboken6.createdByPython(w)]


def _pump(app, seconds=_PUMP_SECONDS):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)


def _close_window(win):
    win.close_guard = lambda: True
    win.quiesce()
    win.close()


def test_layout_entries_read_every_kind_of_item_and_keep_none(qapp):
    from PySide6 import QtCore, QtWidgets
    import studio_theme

    host = QtWidgets.QWidget()
    outer = QtWidgets.QVBoxLayout(host)
    a, b = QtWidgets.QLabel("a"), QtWidgets.QPushButton("b")
    inner = QtWidgets.QHBoxLayout()
    outer.addWidget(a)
    outer.addLayout(inner)
    inner.addWidget(b)
    outer.addStretch(1)
    outer.addSpacing(7)
    entries = studio_theme.layout_entries(outer)
    assert [e.index for e in entries] == [0, 1, 2, 3]
    assert entries[0].widget is a and entries[0].layout is None and not entries[0].spacer
    assert entries[1].widget is None and entries[1].layout is inner
    assert entries[2].spacer and bool(entries[2].expanding & QtCore.Qt.Vertical)      # the stretch grows
    assert entries[3].spacer and not (entries[3].expanding & QtCore.Qt.Vertical)      # a fixed gap does not
    assert entries[3].size_hint.height() == 7
    assert [e.widget for e in studio_theme.layout_entries(inner)] == [b]
    assert studio_theme.layout_widgets(outer) == [a]                                  # direct items only
    assert studio_theme.layout_widgets(inner) == [b]
    assert _qt_made_layout_items() == []                                              # nothing left behind


def test_the_flow_row_holds_items_made_in_python(qapp):
    from PySide6 import QtCore, QtWidgets
    import shiboken6
    import studio_pymode

    host = QtWidgets.QWidget()
    outer = QtWidgets.QVBoxLayout(host)
    row = studio_pymode._FlowRow(spacing=4)
    outer.addLayout(row)                       # added first: PySide then parents nothing of the row to outer
    buttons = [QtWidgets.QToolButton() for _ in range(3)]
    for b in buttons:
        row.addWidget(b)
    row.addStretch(1)
    assert row.count() == 4 and all(shiboken6.createdByPython(row.itemAt(i)) for i in range(row.count()))
    assert [row.itemAt(i).widget() for i in range(3)] == buttons
    host.resize(400, 80)
    host.show()
    _pump(qapp)
    buttons[1].deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    _pump(qapp)
    assert row.count() == 3 and [row.itemAt(i).widget() for i in range(2)] == [buttons[0], buttons[2]]
    assert row.sizeHint().isValid() and row.heightForWidth(60) > 0
    assert _qt_made_layout_items() == []
    host.close()


def test_the_window_keeps_no_qt_made_layout_item_wrappers(qapp):
    """直す前: 窓を作って言語を 2 回切り替えると、Qt が作った配置の項目の wrapper が数百個、表に残っていた。"""
    import studio

    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    try:
        win.resize(1400, 860)
        win.show()
        _pump(qapp)
        assert _qt_made_layout_items() == []                  # after the build
        win._apply_language("ja")
        _pump(qapp)
        win._search_ui["search_now"]("gauss")                # search rows: boxes with their own layouts
        _pump(qapp)
        edit = win._search_ui["edit"]
        edit.blockSignals(True)
        edit.setText("")
        edit.blockSignals(False)
        win._apply_language("en")                             # clears the search rows and walks every layout
        _pump(qapp)
        assert _qt_made_layout_items() == []                  # after the language switches
    finally:
        _close_window(win)


def test_a_layout_item_freed_after_the_density_pass_does_not_crash_a_later_list(tmp_path):
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
        [sys.executable, "-c", _DENSITY_THEN_REUSE_CHILD, str(_LABELS_IN_CHILD), str(_LIST_ITEMS_IN_CHILD)],
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
    assert "kept 0" in result.stdout, result.stdout[-400:]


def test_a_closed_and_deleted_window_leaves_no_top_level_widget(qapp):
    """直す前: 窓を閉じて消しても、処理の一覧の引数の行(KnobRow)の置かれない名前のラベル 2 枚が残った(窓ごとに 2 枚)。"""
    from PySide6 import QtCore, QtWidgets
    import shiboken6
    import studio
    import studio_keymap_qt

    def top_levels_by_cpp_address():
        return {shiboken6.getCppPointer(w)[0]: w for w in QtWidgets.QApplication.topLevelWidgets()}

    def describe(address, widget):
        parent = widget.parent()
        parent_probe = None if parent is None else (
            type(parent).__name__, parent.objectName(), shiboken6.getCppPointer(parent)[0])
        return {
            "class": type(widget).__name__,
            "objectName": widget.objectName(),
            "cpp_address": address,
            "createdByPython": shiboken6.createdByPython(widget),
            "windowFlags": int(widget.windowFlags()),
            "parent": parent_probe,
            "children_count": len(widget.children()),
        }

    def deleted_pump():
        for _ in range(3):
            QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
            qapp.processEvents()

    warm, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))   # one-time caches first
    _close_window(warm)
    warm.deleteLater()
    deleted_pump()
    # C++ 所有の widget は列挙ごとに別の Python wrapper を得るため id(wrapper) は安定しない。
    before = set(top_levels_by_cpp_address())
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    win.show()
    _pump(qapp)
    _close_window(win)
    win.deleteLater()
    del win
    deleted_pump()
    after = top_levels_by_cpp_address()
    probes = {shiboken6.getCppPointer(w)[0] for w in studio_keymap_qt._PROBE_FIELDS}  # one per process
    left = {address: w for address, w in after.items() if address not in before and address not in probes}
    assert left == {}, [describe(address, w) for address, w in left.items()]
