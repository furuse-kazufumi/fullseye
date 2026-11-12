# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_pyedit_vars_qt — 変数の一覧・ウォッチ・値の中身の部品(Qt)と、浮いた窓の入れ物。

部品は全部 ``QWidget``(入れ物を選ばない)。ドックにそのまま入れても、``FloatingFrame``(モードレスの浮いた窓)に
入れてもよい。

* ``ValueTree``       — 値の木(名前・型・形・値、遅延展開、変わった印、サムネイル、値の編集、右クリック)。
* ``VariablesPanel``  — 絞り込み + 木 + 空の状態の案内 + 画像のプレビュー。
* ``ValueInspector``  — 1 つの変数の中身(複数枚を同時に開ける。追従 / 固定のピンに対応)。
* ``WatchPanel``      — ウォッチの式(足す・消す・並べ替え・評価・変わった印・画像のサムネイル)。
* ``VarsWatchWidget`` — 上の 2 つを縦に並べた物。
* ``ArrayTableDialog`` / ``HistogramDialog`` — 数の配列を表で / ヒストグラムで見る(モードレス)。
* ``FloatingFrame`` / ``FloatingRegistry`` — 浮いた窓の入れ物(Esc で閉じる・位置と大きさを覚える・ピン・題に対象の名前)。

画面の文は全部、渡された ``tr`` を通す(対訳は ``studio_assets/studio_pyedit_i18n.json``)。
行の高さは ``studio_pyedit_qt.ROW_EXTRA_PX`` から出す。
"""
from __future__ import annotations

import html
import json
import time
from dataclasses import dataclass
from typing import Callable, MutableMapping

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

import studio_pyedit_values as V
from studio_pyedit_i18n import identity_tr
from studio_pyedit_qt import ROW_EXTRA_PX, compact_rows, row_height  # noqa: F401  (ROW_EXTRA_PX は再公開)

_THUMB = 16          # 行の中のサムネイル(行の高さ = 文字 + 4 に収まる大きさ)
_PREVIEW = 144       # 選んだ画像のプレビュー


def qimage_from_u8(a: np.ndarray) -> QtGui.QImage:
    """``thumbnail_u8`` の結果 → ``QImage``(配列の寿命に依らないようコピーする)。"""
    a = np.ascontiguousarray(a)
    if a.ndim == 2:
        h, w = a.shape
        return QtGui.QImage(a.data, w, h, w, QtGui.QImage.Format_Grayscale8).copy()
    h, w, _c = a.shape
    return QtGui.QImage(a.data, w, h, 3 * w, QtGui.QImage.Format_RGB888).copy()


def pixmap_for(value, size: int) -> QtGui.QPixmap | None:
    if not V.is_image_like(value):
        return None
    try:
        return QtGui.QPixmap.fromImage(qimage_from_u8(V.thumbnail_u8(value, size)))
    except Exception:                                           # noqa: BLE001
        return None


def _status_texts(tr) -> dict:
    return {"new": tr("new since the last stop"), "changed": tr("changed since the last stop")}


# --------------------------------------------------------------------------- #
# 値の木
# --------------------------------------------------------------------------- #
@dataclass
class _Node:
    label: str
    path: tuple
    value: object
    summary: V.Summary
    ancestors: tuple
    status: str = "same"
    loaded: bool = False
    cycle: bool = False
    explicit: tuple = ()


class _ValueDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, tree: "ValueTree"):
        super().__init__(tree)
        self._tree = tree

    def createEditor(self, parent, option, index):
        if index.column() != 3:
            return None
        item = self._tree.itemFromIndex(index)
        node = item.data(0, QtCore.Qt.UserRole) if item is not None else None
        if node is None or not node.summary.editable:
            return None
        return QtWidgets.QLineEdit(parent)

    def setEditorData(self, editor, index):
        item = self._tree.itemFromIndex(index)
        node = item.data(0, QtCore.Qt.UserRole)
        v = node.value
        if isinstance(v, np.generic):
            v = v.item()
        editor.setText(repr(v))
        editor.selectAll()

    def setModelData(self, editor, model, index):
        item = self._tree.itemFromIndex(index)
        self._tree._commit(item, editor.text())


class ValueTree(QtWidgets.QTreeWidget):
    """値の木。名前・型・形・値の 4 列。"""

    imageRequested = QtCore.Signal(str, object)
    inspectRequested = QtCore.Signal(str, tuple, object)
    watchRequested = QtCore.Signal(str)
    editRejected = QtCore.Signal(str)
    editCommitted = QtCore.Signal(tuple)
    currentNodeChanged = QtCore.Signal(object)

    def __init__(self, source=None, tr: Callable = identity_tr, limits: V.Limits = V.DEFAULT_LIMITS,
                 tracker: V.VariableTracker | None = None, parent=None):
        super().__init__(parent)
        self.source = source
        self._tr = tr
        self.limits = limits
        self.tracker = tracker if tracker is not None else V.VariableTracker()
        self._expanded: set = set()
        self._loading = False
        self._windows: list = []
        self._explicit: dict = {}
        self.setColumnCount(4)
        self.setHeaderLabels([tr("Name"), tr("Type"), tr("Shape"), tr("Value")])
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(False)
        self.setIconSize(QtCore.QSize(_THUMB, _THUMB))
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        self.setItemDelegate(_ValueDelegate(self))
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.itemExpanded.connect(self._on_expanded)
        self.itemCollapsed.connect(self._on_collapsed)
        self.currentItemChanged.connect(lambda cur, _prev: self.currentNodeChanged.emit(self.node_of(cur)))
        self.header().setStretchLastSection(True)
        self.setColumnWidth(0, 130)
        self.setColumnWidth(1, 90)
        self.setColumnWidth(2, 110)
        self.row_h = compact_rows(self)

    # ---- 構築 ----
    @staticmethod
    def node_of(item) -> "_Node | None":
        return item.data(0, QtCore.Qt.UserRole) if item is not None else None

    def set_roots(self, entries: list, begin_stop: bool = False) -> None:
        """``entries`` は ``[(名前, 値, 路)]``。展開の状態・選択を保って作り直す。"""
        tr = self._tr
        sel = None
        cur = self.currentItem()
        if cur is not None and self.node_of(cur) is not None:
            sel = self.node_of(cur).path
        if begin_stop:
            self.tracker.begin()
        self._loading = True
        self.setUpdatesEnabled(False)
        self.clear()
        for name, value, path in entries:
            st = self.tracker.status(path, value)
            node = self._make_node(name, path, value, (), st)
            item = self._make_item(node)
            self.addTopLevelItem(item)
        self._loading = False
        for i in range(self.topLevelItemCount()):
            it = self.topLevelItem(i)
            if self.node_of(it).path in self._expanded:
                it.setExpanded(True)
        if sel is not None:
            self._select_path(sel)
        self.setUpdatesEnabled(True)

    def _make_node(self, label, path, value, ancestors, status, cycle=False) -> _Node:
        summ = V.summarize(value, self.limits, self._tr)
        if cycle:
            summ = V.Summary(summ.kind, summ.type_name, self._tr("(circular reference)"), problem="circular")
        return _Node(label, tuple(path), value, summ, ancestors, status, False, cycle,
                     tuple(self._explicit.get(tuple(path), ())))

    def _make_item(self, node: _Node) -> QtWidgets.QTreeWidgetItem:
        tr = self._tr
        s = node.summary
        item = QtWidgets.QTreeWidgetItem()
        item.setData(0, QtCore.Qt.UserRole, node)
        mark = {"new": "+ ", "changed": "● "}.get(node.status, "")
        item.setText(0, mark + node.label)
        item.setText(1, s.type_name)
        shape = ""
        if s.shape is not None:
            shape = "×".join(str(x) for x in s.shape) or tr("scalar")
        elif s.length is not None:
            shape = tr("len %d") % s.length
        item.setText(2, shape)
        item.setText(3, s.text)
        tips = []
        if node.status in ("new", "changed"):
            tips.append(_status_texts(tr)[node.status])
            f = item.font(0)
            f.setBold(True)
            for c in (0, 3):
                item.setFont(c, f)
            item.setBackground(0, QtGui.QBrush(QtGui.QColor(70, 110, 190, 60)))
            item.setBackground(3, QtGui.QBrush(QtGui.QColor(70, 110, 190, 60)))
        if s.problem:
            tips.append(s.text)
            item.setIcon(3, self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning))
        if s.detail:
            tips.append(s.detail)
        if tips:
            item.setToolTip(3, "\n".join(tips))
            item.setToolTip(0, "\n".join(tips[:1]))
        if s.is_image:
            pm = pixmap_for(node.value, _THUMB * 2)
            if pm is not None:
                item.setIcon(3, QtGui.QIcon(pm.scaled(_THUMB, _THUMB, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)))
        if s.editable and (not node.path or node.path[-1][0] != "elem"):
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        if s.expandable and not node.cycle:
            item.addChild(QtWidgets.QTreeWidgetItem())          # 展開の矢印のための空の子
            item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
        return item

    def _load_children(self, item) -> None:
        node = self.node_of(item)
        if node is None or node.loaded:
            return
        node.loaded = True
        item.takeChildren()
        anc = node.ancestors + (id(node.value),)
        kids = V.children(node.value, ancestors=anc, explicit_attrs=node.explicit, limits=self.limits, tr=self._tr)
        for ch in kids:
            if ch.step is None:
                row = QtWidgets.QTreeWidgetItem([ch.label, "", "", ""])
                row.setFlags(QtCore.Qt.ItemIsEnabled)
                item.addChild(row)
                continue
            path = node.path + (ch.step,)
            st = self.tracker.status(path, ch.value)
            cn = self._make_node(ch.label, path, ch.value, anc, st, cycle=ch.cycle)
            ci = self._make_item(cn)
            if ch.note:
                ci.setText(3, ch.note)
            item.addChild(ci)
            if cn.path in self._expanded and not cn.cycle:
                ci.setExpanded(True)

    def _on_expanded(self, item) -> None:
        node = self.node_of(item)
        if node is not None:
            self._expanded.add(node.path)
            self._load_children(item)

    def _on_collapsed(self, item) -> None:
        node = self.node_of(item)
        if node is not None and not self._loading:
            self._expanded.discard(node.path)

    def _select_path(self, path: tuple) -> None:
        def walk(parent_count, getter):
            for i in range(parent_count):
                it = getter(i)
                n = self.node_of(it)
                if n is not None and n.path == path:
                    return it
                if n is not None and n.loaded and path[:len(n.path)] == n.path:
                    r = walk(it.childCount(), it.child)
                    if r is not None:
                        return r
            return None
        it = walk(self.topLevelItemCount(), self.topLevelItem)
        if it is not None:
            self.setCurrentItem(it)

    def expand_node(self, path: tuple) -> None:
        self._expanded.add(tuple(path))

    # ---- 編集 ----
    def _commit(self, item, text: str) -> None:
        node = self.node_of(item)
        tr = self._tr
        try:
            new = V.parse_edit(text, node.value, tr)
            if self.source is None:
                raise V.EditError(tr("this view is read-only"))
            self.source.set_value(node.path, new)
        except V.EditError as exc:
            self._reject(item, str(exc))
            return
        except Exception as exc:                                # noqa: BLE001 — 供給元の失敗も理由つきで断る
            self._reject(item, "%s: %s" % (type(exc).__name__, exc))
            return
        node.value = new
        node.summary = V.summarize(new, self.limits, tr)
        node.status = "changed"
        item.setText(3, node.summary.text)
        item.setForeground(3, QtGui.QBrush())
        item.setToolTip(3, _status_texts(tr)["changed"])
        self.editCommitted.emit(node.path)

    def _reject(self, item, msg: str) -> None:
        item.setForeground(3, QtGui.QBrush(QtGui.QColor("#ff6b6b")))
        item.setToolTip(3, "⚠ " + msg)
        self.editRejected.emit("⚠ " + msg)

    # ---- 右クリック ----
    def _menu(self, pos) -> None:
        item = self.itemAt(pos)
        node = self.node_of(item)
        if node is None:
            return
        tr = self._tr
        m = QtWidgets.QMenu(self)
        acts: dict = {}
        acts["copy_value"] = m.addAction(tr("Copy value"))
        acts["copy_expr"] = m.addAction(tr("Copy as expression"))
        if node.path:
            acts["watch"] = m.addAction(tr("Add to watch"))
        m.addSeparator()
        v = node.value
        if V.is_image_like(v):
            acts["image"] = m.addAction(tr("Open as image"))
        if isinstance(v, np.ndarray) and v.dtype.kind in "biuf" and v.ndim in (1, 2, 3) and v.size:
            acts["table"] = m.addAction(tr("View as table"))
            acts["hist"] = m.addAction(tr("View histogram"))
        acts["inspect"] = m.addAction(tr("Inspect in a window"))
        attrs = [n for n in V.candidate_attributes(v)][:40] if not isinstance(v, (dict, list, tuple, np.ndarray, str, int, float, bool)) else []
        sub = None
        if attrs:
            sub = m.addMenu(tr("Expand attribute (may run code)"))
            for n in attrs:
                sub.addAction(n).setData(("attr", n))
        chosen = m.exec(self.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if sub is not None and chosen.data() and chosen.data()[0] == "attr":
            key = node.path
            self._explicit[key] = tuple(self._explicit.get(key, ())) + (chosen.data()[1],)
            node.explicit = self._explicit[key]
            node.loaded = False
            self._load_children(item)
            item.setExpanded(True)
            return
        for k, a in acts.items():
            if a is chosen:
                self._do(k, node)
                return

    def _do(self, key: str, node: _Node) -> None:
        v = node.value
        label = V.path_to_expression(node.path) or node.label
        if key == "copy_value":
            QtWidgets.QApplication.clipboard().setText(self.value_text(v))
        elif key == "copy_expr":
            QtWidgets.QApplication.clipboard().setText(label)
        elif key == "watch":
            self.watchRequested.emit(label)
        elif key == "image":
            self.imageRequested.emit(label, v)
        elif key == "table":
            self.open_table(label, v)
        elif key == "hist":
            self.open_histogram(label, v)
        elif key == "inspect":
            self.inspectRequested.emit(label, node.path, v)

    def value_text(self, v) -> str:
        """「値をコピー」の文字列。配列は省略つきの形、他は ``repr``(時間の上限つき)。"""
        if isinstance(v, np.ndarray):
            return np.array2string(v, threshold=2000, edgeitems=4, max_line_width=120)
        st, val = V.run_with_timeout(lambda: repr(v), 0.25)
        if st == "ok" and isinstance(val, str):
            return val[:1_000_000]
        return V.summarize(v, self.limits, self._tr).text

    def open_table(self, label, v) -> None:
        dlg = ArrayTableDialog(label, v, self._tr, self.window())
        self._windows.append(dlg)
        dlg.show()

    def open_histogram(self, label, v) -> None:
        dlg = HistogramDialog(label, v, self._tr, self.window())
        self._windows.append(dlg)
        dlg.show()


# --------------------------------------------------------------------------- #
# 表・ヒストグラム(モードレス)
# --------------------------------------------------------------------------- #
class _ArrayModel(QtCore.QAbstractTableModel):
    def __init__(self, a: np.ndarray):
        super().__init__()
        self.a = a.reshape(a.shape[0], -1) if a.ndim > 2 else (a.reshape(-1, 1) if a.ndim == 1 else a)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return int(self.a.shape[0])

    def columnCount(self, parent=QtCore.QModelIndex()):
        return int(self.a.shape[1])

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            v = self.a[index.row(), index.column()]
            return ("%.6g" % v) if self.a.dtype.kind == "f" else str(v)
        if role == QtCore.Qt.TextAlignmentRole:
            return int(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return None


class ArrayTableDialog(QtWidgets.QDialog):
    """数の配列を表で見る(モードレス)。"""

    def __init__(self, name: str, a: np.ndarray, tr: Callable = identity_tr, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.setWindowTitle(tr("Table: %s") % name)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.table = QtWidgets.QTableView(self)
        self.table.setModel(_ArrayModel(a))
        compact_rows(self.table)
        self.table.horizontalHeader().setDefaultSectionSize(80)
        lay.addWidget(self.table)
        self.resize(560, 360)


def histogram_view_class():
    class HistogramView(QtWidgets.QWidget):
        def __init__(self, counts, edges, tr, parent=None):
            super().__init__(parent)
            self.counts, self.edges, self._tr = counts, edges, tr
            self.setMinimumSize(320, 180)

        def paintEvent(self, ev):
            p = QtGui.QPainter(self)
            pal = self.palette()
            p.fillRect(self.rect(), pal.base())
            w, h = self.width(), self.height()
            mx = float(self.counts.max()) or 1.0
            n = len(self.counts)
            bw = (w - 20) / n
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(pal.highlight())
            for i, c in enumerate(self.counts):
                bh = (h - 34) * float(c) / mx
                p.drawRect(QtCore.QRectF(10 + i * bw, h - 20 - bh, max(1.0, bw - 1), bh))
            p.setPen(pal.text().color())
            p.drawText(10, h - 5, "%.4g" % self.edges[0])
            txt = "%.4g" % self.edges[-1]
            p.drawText(w - 10 - p.fontMetrics().horizontalAdvance(txt), h - 5, txt)
            p.end()
    return HistogramView


class HistogramDialog(QtWidgets.QDialog):
    """数の配列のヒストグラム(モードレス)。"""

    def __init__(self, name: str, a: np.ndarray, tr: Callable = identity_tr, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.setWindowTitle(tr("Histogram: %s") % name)
        counts, edges, sampled = V.histogram_data(a)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.view = histogram_view_class()(counts, edges, tr, self)
        lay.addWidget(self.view)
        self.note = QtWidgets.QLabel(tr("computed from a sample of the elements") if sampled else
                                     tr("%d elements") % int(a.size), self)
        lay.addWidget(self.note)
        self.resize(420, 260)


# --------------------------------------------------------------------------- #
# 変数の一覧
# --------------------------------------------------------------------------- #
class _EmptyState(QtWidgets.QWidget):
    """空の状態の案内: 何をする場所か 1 行 + 最初の一手のボタン + 例を開くボタン(渡された物だけ)。"""

    def __init__(self, text: str, buttons: list, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.addStretch(1)
        self.label = QtWidgets.QLabel(text, self)
        self.label.setWordWrap(True)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        lay.addWidget(self.label)
        self.buttons = []
        for caption, tip, cb in buttons:
            b = QtWidgets.QPushButton(caption, self)
            b.setToolTip(tip)
            b.setAccessibleName(caption)
            b.clicked.connect(lambda _=False, f=cb: f())
            lay.addWidget(b, 0, QtCore.Qt.AlignCenter)
            self.buttons.append(b)
        lay.addStretch(1)


class VariablesPanel(QtWidgets.QWidget):
    """変数の一覧: 絞り込み + 木 + 画像のプレビュー + 空の状態。"""

    imageRequested = QtCore.Signal(str, object)
    inspectRequested = QtCore.Signal(str, tuple, object)
    watchRequested = QtCore.Signal(str)

    def __init__(self, source=None, tr: Callable = identity_tr, on_run: Callable | None = None,
                 on_open_example: Callable | None = None, limits: V.Limits = V.DEFAULT_LIMITS, parent=None):
        super().__init__(parent)
        self.source = source
        self._tr = tr
        self._limits = limits
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        bar = QtWidgets.QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 0)
        self.filter = QtWidgets.QLineEdit(self)
        self.filter.setPlaceholderText(tr("Filter by name or type"))
        self.filter.setToolTip(tr("Words match the name or the type. Prefix with type: or name: to look at one."))
        self.filter.setClearButtonEnabled(True)
        self.filter.setAccessibleName(tr("Filter variables"))
        self.show_all = QtWidgets.QCheckBox(tr("Functions and modules"), self)
        self.show_all.setToolTip(tr("Also list functions, classes, modules and names starting with _"))
        bar.addWidget(self.filter, 1)
        bar.addWidget(self.show_all)
        lay.addLayout(bar)
        self.stack = QtWidgets.QStackedWidget(self)
        self.tree = ValueTree(source, tr, limits, parent=self)
        buttons = []
        if on_run is not None:
            buttons.append((tr("Run the program"), tr("Run the program (names appear here after it runs)"), on_run))
        if on_open_example is not None:
            buttons.append((tr("Open an example"), tr("Open a short example program that makes some variables"), on_open_example))
        self.empty = _EmptyState(tr("Variables appear here after the program runs: each name with its type, shape and value. "
                                    "Arrays that look like images get a thumbnail."), buttons, self)
        self.stack.addWidget(self.tree)
        self.stack.addWidget(self.empty)
        lay.addWidget(self.stack, 1)
        self.preview = QtWidgets.QLabel(self)
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.setFixedHeight(_PREVIEW + 4)
        self.preview.setToolTip(tr("Preview of the selected image. Double-click to open it larger."))
        self.preview.hide()
        lay.addWidget(self.preview)
        self.message = QtWidgets.QLabel("", self)
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color:#ff6b6b;font-weight:bold;")
        self.message.hide()
        lay.addWidget(self.message)
        self.removed = QtWidgets.QLabel("", self)
        self.removed.setWordWrap(True)
        self.removed.hide()
        lay.addWidget(self.removed)
        self._entries: list = []
        self._current_image = None
        self.filter.textChanged.connect(lambda _t: self._rebuild())
        self.show_all.toggled.connect(lambda _b: self._rebuild())
        self.tree.currentNodeChanged.connect(self._on_node)
        self.tree.imageRequested.connect(self.imageRequested)
        self.tree.inspectRequested.connect(self.inspectRequested)
        self.tree.watchRequested.connect(self.watchRequested)
        self.tree.editRejected.connect(self._show_error)
        self.tree.editCommitted.connect(lambda _p: self.message.hide())
        self.preview.mouseDoubleClickEvent = lambda ev: (self.imageRequested.emit(*self._current_image)
                                                         if self._current_image else None)

    def set_source(self, source) -> None:
        self.source = source
        self.tree.source = source

    def refresh(self) -> None:
        """停止のたびに呼ぶ(前の停止と比べて、新しい・変わった・消えたの印を付ける)。"""
        snap = self.source.snapshot() if self.source is not None else {}
        self._entries = [V.Entry(n, v, V.summarize(v, self._limits, self._tr)) for n, v in V.namespace_items(snap)]
        self.message.hide()
        self._rebuild(begin_stop=True)

    def _rebuild(self, begin_stop: bool = False) -> None:
        shown = V.filter_entries(self._entries, self.filter.text(), self.show_all.isChecked())
        if begin_stop:
            pass
        self.tree.set_roots([(e.name, e.value, (("name", e.name),)) for e in shown], begin_stop=begin_stop)
        rem = self.tree.tracker.removed()
        if rem:
            self.removed.setText(self._tr("Removed since the last stop: %s") % ", ".join(rem))
            self.removed.show()
        else:
            self.removed.hide()
        self.stack.setCurrentWidget(self.tree if (self._entries or self.filter.text()) else self.empty)

    def _on_node(self, node) -> None:
        if node is not None and node.summary.is_image:
            pm = pixmap_for(node.value, _PREVIEW)
            if pm is not None:
                self.preview.setPixmap(pm.scaled(_PREVIEW, _PREVIEW, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation))
                self.preview.show()
                self._current_image = (V.path_to_expression(node.path) or node.label, node.value)
                return
        self.preview.hide()
        self._current_image = None

    def _show_error(self, msg: str) -> None:
        self.message.setText(msg)
        self.message.show()


# --------------------------------------------------------------------------- #
# 変数の中身(1 つ。複数枚を同時に開ける)
# --------------------------------------------------------------------------- #
class ValueInspector(QtWidgets.QWidget):
    """1 つの変数の中身。追従(本体の状態が変われば中身も変わる)と固定(ピン: その時点の物を見続ける)。"""

    imageRequested = QtCore.Signal(str, object)
    titleChanged = QtCore.Signal(str)

    def __init__(self, source, path: tuple, name: str | None = None, tr: Callable = identity_tr,
                 value=None, limits: V.Limits = V.DEFAULT_LIMITS, parent=None):
        super().__init__(parent)
        self._tr = tr
        self.source = source
        self.path = tuple(path)
        self.name = name or V.path_to_expression(self.path)
        self.pinned = False
        self._pinned_value = value
        self._has_pinned = value is not None
        self._limits = limits
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        self.header = QtWidgets.QLabel(self)
        self.header.setWordWrap(True)
        self.header.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        lay.addWidget(self.header)
        self.tree = ValueTree(source, tr, limits, parent=self)
        lay.addWidget(self.tree, 1)
        self.preview = QtWidgets.QLabel(self)
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.hide()
        lay.addWidget(self.preview)
        self.tree.imageRequested.connect(self.imageRequested)
        self.refresh()

    def title(self) -> str:
        tr = self._tr
        return ("%s: %s" % (tr("Value"), self.name)) + ((" " + tr("[pinned]")) if self.pinned else "")

    def set_pinned(self, pinned: bool) -> None:
        """ピン: 今の物に固定する(見ている値の参照をここで掴む)/ 外すと追従に戻る。"""
        if pinned and not self.pinned:
            try:
                ns = dict(V.namespace_items(self.source.snapshot()))
                self._pinned_value = V.resolve_path(ns, self.path)
                self._has_pinned = True
            except Exception:                                   # noqa: BLE001
                self._has_pinned = False
        self.pinned = bool(pinned)
        self.titleChanged.emit(self.title())
        self.refresh()

    def current_value(self):
        if self.pinned and self._has_pinned:
            return self._pinned_value, True
        try:
            ns = dict(V.namespace_items(self.source.snapshot()))
            return V.resolve_path(ns, self.path), True
        except Exception:                                       # noqa: BLE001
            return None, False

    def refresh(self) -> None:
        tr = self._tr
        v, ok = self.current_value()
        if not ok:
            self.header.setText("⚠ " + tr("this variable no longer exists: %s") % self.name)
            self.tree.set_roots([])
            self.preview.hide()
            return
        s = V.summarize(v, self._limits, tr)
        self.header.setText("<b>%s</b> · %s · %s" % (html.escape(self.name), html.escape(s.type_name), html.escape(s.text)))
        self.tree.expand_node(self.path)
        self.tree.set_roots([(self.name, v, self.path)], begin_stop=True)
        pm = pixmap_for(v, 256) if s.is_image else None
        if pm is not None:
            self.preview.setPixmap(pm)
            self.preview.show()
        else:
            self.preview.hide()


# --------------------------------------------------------------------------- #
# ウォッチ
# --------------------------------------------------------------------------- #
class WatchPanel(QtWidgets.QWidget):
    """ウォッチ: 式を足す・消す・並べ替える。停止中・実行後の名前空間で評価して値を出す。"""

    imageRequested = QtCore.Signal(str, object)
    changed = QtCore.Signal(list)                 # 式の並びが変わった(保存の合図)
    refreshed = QtCore.Signal()                   # 評価が全部終わった

    def __init__(self, namespace=None, tr: Callable = identity_tr, watch: V.WatchList | None = None,
                 timeout_s: float = 0.25, on_add_example: Callable | None = None, parent=None,
                 async_eval: bool = True):
        super().__init__(parent)
        self._tr = tr
        self.watch = watch if watch is not None else V.WatchList()
        self.evaluator = V.WatchEvaluator(namespace, timeout_s, tr)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        bar = QtWidgets.QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 0)
        self.input = QtWidgets.QLineEdit(self)
        self.input.setPlaceholderText(tr("Type an expression and press Enter, e.g. img.mean()"))
        self.input.setAccessibleName(tr("Watch expression"))
        bar.addWidget(self.input, 1)
        self.btn_add = self._button("＋", tr("Add the expression to the watch list (Enter)"), tr("Add"))
        self.btn_del = self._button("−", tr("Remove the selected expression"), tr("Remove"))
        self.btn_up = self._button("↑", tr("Move the selected expression up"), tr("Move up"))
        self.btn_down = self._button("↓", tr("Move the selected expression down"), tr("Move down"))
        self.btn_again = self._button("↻", tr("Evaluate the selected expression again (also when automatic evaluation was stopped)"),
                                      tr("Evaluate again"))
        for b in (self.btn_add, self.btn_del, self.btn_up, self.btn_down, self.btn_again):
            bar.addWidget(b)
        lay.addLayout(bar)
        self.stack = QtWidgets.QStackedWidget(self)
        self.table = QtWidgets.QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels([tr("Expression"), tr("Value")])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 160)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setIconSize(QtCore.QSize(_THUMB, _THUMB))
        self.row_h = compact_rows(self.table)
        buttons = []
        if on_add_example is not None:
            buttons.append((tr("Add an example"), tr("Add the expression img.mean() to the list"), on_add_example))
        self.empty = _EmptyState(tr("Watch expressions are re-evaluated every time the program stops or finishes. "
                                    "Type an expression above, or use \"Add to watch\" in the variable list."), buttons, self)
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.empty)
        lay.addWidget(self.stack, 1)
        self.preview = QtWidgets.QLabel(self)
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.hide()
        lay.addWidget(self.preview)
        self.input.returnPressed.connect(self.add_from_input)
        self.btn_add.clicked.connect(lambda _=False: self.add_from_input())
        self.btn_del.clicked.connect(lambda _=False: self.remove_selected())
        self.btn_up.clicked.connect(lambda _=False: self.move_selected(-1))
        self.btn_down.clicked.connect(lambda _=False: self.move_selected(1))
        self.btn_again.clicked.connect(lambda _=False: self.evaluate_again())
        self.table.itemChanged.connect(self._on_edit)
        self.table.currentCellChanged.connect(lambda *_: self._update_preview())
        self._results: dict = {}
        self._jobs: dict = {}
        self._auto_off: dict = {}
        self.async_eval = bool(async_eval)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._poll_jobs)
        self._building = False
        self._rebuild()

    def _button(self, glyph: str, tip: str, name: str) -> QtWidgets.QToolButton:
        b = QtWidgets.QToolButton(self)
        b.setText(glyph)
        b.setToolTip(tip)
        b.setAccessibleName(name)
        b.setAutoRaise(True)
        return b

    # ---- 式の操作 ----
    def add_expression(self, expr: str) -> bool:
        try:
            self.watch.add(expr)
        except ValueError:
            return False
        self._rebuild()
        self.refresh()
        self.changed.emit(list(self.watch.exprs))
        return True

    def add_from_input(self) -> None:
        if self.add_expression(self.input.text()):
            self.input.clear()

    def remove_selected(self) -> None:
        r = self.table.currentRow()
        if 0 <= r < len(self.watch.exprs):
            self.watch.remove(r)
            self._rebuild()
            self.refresh()
            self.changed.emit(list(self.watch.exprs))

    def move_selected(self, delta: int) -> None:
        r = self.table.currentRow()
        t = r + delta
        if 0 <= r < len(self.watch.exprs) and 0 <= t < len(self.watch.exprs):
            self.watch.move(r, t)
            self._rebuild()
            self.refresh()
            self.table.setCurrentCell(t, 0)
            self.changed.emit(list(self.watch.exprs))

    def _on_edit(self, item) -> None:
        if self._building or item.column() != 0:
            return
        r = item.row()
        new = item.text().strip()
        if not new:
            self.remove_selected()
            return
        if 0 <= r < len(self.watch.exprs):
            self.watch.exprs[r] = new
            self.refresh()
            self.changed.emit(list(self.watch.exprs))

    def set_expressions(self, exprs) -> None:
        self.watch = V.WatchList(exprs)
        self._rebuild()
        self.refresh()

    def dumps(self) -> str:
        """プロジェクトごとに保存する JSON(式の一覧)。"""
        return self.watch.dumps()

    def loads(self, text: str) -> None:
        self.watch = V.WatchList.loads(text)
        self._rebuild()
        self.refresh()

    def condition_evaluator(self) -> V.WatchEvaluator:
        """条件つきブレークポイントが使う、同じ評価器。"""
        return self.evaluator

    # ---- 表示 ----
    def _rebuild(self) -> None:
        self._building = True
        self.table.setRowCount(len(self.watch.exprs))
        for r, e in enumerate(self.watch.exprs):
            it = QtWidgets.QTableWidgetItem(e)
            it.setFlags(it.flags() | QtCore.Qt.ItemIsEditable)
            self.table.setItem(r, 0, it)
            vi = QtWidgets.QTableWidgetItem("")
            vi.setFlags(vi.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(r, 1, vi)
        self._building = False
        self.stack.setCurrentWidget(self.table if self.watch.exprs else self.empty)

    # ---- 評価(作業スレッド。UI を待たせない) ----
    def refresh(self) -> None:
        """式を評価し直す(停止・実行後に呼ぶ)。評価は作業スレッドで行い、結果が来るまで行に「評価中…」を出す。
        時間の上限を超えても止まらなかった式は「時間切れ(止められなかった)」と出し、以後は自動では評価し直さない
        (↻ で選んだ行だけ評価し直せる)。"""
        tr = self._tr
        if not self.async_eval:
            self._refresh_sync()
            return
        self._building = True
        for r, e in enumerate(self.watch.exprs):
            it = self.table.item(r, 1)
            if it is None:
                continue
            if e in self._auto_off:
                self._set_error_cell(it, self._auto_off[e], stuck=True)
                continue
            job = self._jobs.get(e)
            if job is not None and job.running:
                self._set_pending_cell(it)
                continue                                   # 前の評価がまだ走っている(重ねて始めない)
            self._set_pending_cell(it)
            self._jobs[e] = self.evaluator.start(e)
        self._building = False
        self._poll_jobs()
        if self._jobs:
            self._timer.start()

    def _refresh_sync(self) -> None:
        self._building = True
        for r, e in enumerate(self.watch.exprs):
            res = self.evaluator.evaluate(e)
            self._results[e] = res
            it = self.table.item(r, 1)
            if it is not None:
                self._apply_result(it, res)
        self._building = False
        self._update_preview()

    def _poll_jobs(self) -> None:
        if not self._jobs:
            self._timer.stop()
            return
        self._building = True
        for e, job in list(self._jobs.items()):
            res = job.poll()
            if res is None:
                continue
            del self._jobs[e]
            self._results[e] = res
            if res.stuck:
                self._auto_off[e] = res.error
            if e in self.watch.exprs:
                it = self.table.item(self.watch.exprs.index(e), 1)
                if it is not None:
                    self._apply_result(it, res)
        self._building = False
        if not self._jobs:
            self._timer.stop()
            self._update_preview()
            self.refreshed.emit()

    def wait_idle(self, timeout_s: float = 5.0) -> bool:
        """評価が全部終わるまでイベントを回して待つ(試験・スクリーンショット用)。終われば True。"""
        end = time.monotonic() + timeout_s
        app = QtWidgets.QApplication.instance()
        while self._jobs and time.monotonic() < end:
            if app is not None:
                app.processEvents()
            self._poll_jobs()
            time.sleep(0.01)
        return not self._jobs

    def evaluate_again(self) -> None:
        """選んだ行を評価し直す(自動の評価を止めた式も)。"""
        r = self.table.currentRow()
        if not (0 <= r < len(self.watch.exprs)):
            return
        e = self.watch.exprs[r]
        self._auto_off.pop(e, None)
        self._jobs.pop(e, None)
        it = self.table.item(r, 1)
        if it is not None:
            self._building = True
            self._set_pending_cell(it)
            self._building = False
        if self.async_eval:
            self._jobs[e] = self.evaluator.start(e)
            self._timer.start()
        else:
            self._refresh_sync()

    def _reset_cell(self, it) -> None:
        f = it.font()
        f.setBold(False)
        f.setItalic(False)
        it.setFont(f)
        it.setIcon(QtGui.QIcon())
        it.setForeground(QtGui.QBrush())

    def _set_pending_cell(self, it) -> None:
        self._reset_cell(it)
        f = it.font()
        f.setItalic(True)
        it.setFont(f)
        it.setText(self._tr("evaluating…"))
        it.setToolTip(self._tr("evaluating…"))
        it.setForeground(QtGui.QBrush(QtGui.QColor("#8b91a0")))

    def _set_error_cell(self, it, error: str, stuck: bool = False) -> None:
        self._reset_cell(it)
        it.setText("⚠ " + error)
        it.setForeground(QtGui.QBrush(QtGui.QColor("#ff6b6b")))
        tip = "⚠ " + error
        if stuck:
            tip += "\n" + self._tr("not re-evaluated automatically; select the row and press ↻ to try again")
        it.setToolTip(tip)

    def _apply_result(self, it, res) -> None:
        tr = self._tr
        if not res.ok:
            self._set_error_cell(it, res.error, stuck=res.stuck)
            return
        self._reset_cell(it)
        s = res.summary
        it.setText(("● " if res.changed else "") + s.text)
        it.setToolTip("%s\n%s" % (s.detail or s.text, (tr("changed since the last evaluation") if res.changed else "")))
        if res.changed:
            f = it.font()
            f.setBold(True)
            it.setFont(f)
        if s.is_image:
            pm = pixmap_for(res.value, _THUMB * 2)
            if pm is not None:
                it.setIcon(QtGui.QIcon(pm.scaled(_THUMB, _THUMB, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)))

    def _update_preview(self) -> None:
        r = self.table.currentRow()
        e = self.watch.exprs[r] if 0 <= r < len(self.watch.exprs) else None
        res = self._results.get(e)
        if res is not None and res.ok and res.summary is not None and res.summary.is_image:
            pm = pixmap_for(res.value, _PREVIEW)
            if pm is not None:
                self.preview.setPixmap(pm.scaled(_PREVIEW, _PREVIEW, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation))
                self.preview.show()
                return
        self.preview.hide()


class VarsWatchWidget(QtWidgets.QWidget):
    """変数の一覧 + ウォッチ(縦に並べる)。ドックにも浮いた窓にも入る。"""

    def __init__(self, source=None, tr: Callable = identity_tr, on_run: Callable | None = None,
                 on_open_example: Callable | None = None, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
        self.variables = VariablesPanel(source, tr, on_run, on_open_example, parent=self)
        ns = (lambda: dict(V.namespace_items(source.snapshot()))) if source is not None else {}
        self.watch = WatchPanel(ns, tr, on_add_example=lambda: self.watch.add_expression("img.mean()"), parent=self)
        self.splitter.addWidget(self.variables)
        self.splitter.addWidget(self.watch)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        lay.addWidget(self.splitter)
        self.variables.watchRequested.connect(self.watch.add_expression)

    def refresh(self) -> None:
        self.variables.refresh()
        self.watch.refresh()


# --------------------------------------------------------------------------- #
# 浮いた窓の入れ物
# --------------------------------------------------------------------------- #
def clamp_rect_to_screens(rect: tuple, screens: list, min_visible: int = 60) -> tuple:
    """``rect = (x, y, w, h)`` を、``screens``(``(x, y, w, h)`` の列)のどれかに最低 ``min_visible`` px 見えるよう戻す。
    どの画面にもかかっていなければ、最初の画面の左上寄りへ(大きさは画面に収める)。画面の構成が変わっても使える。"""
    x, y, w, h = rect
    if not screens:
        return rect
    for sx, sy, sw, sh in screens:
        ix = min(x + w, sx + sw) - max(x, sx)
        iy = min(y + h, sy + sh) - max(y, sy)
        if ix >= min_visible and iy >= min_visible:
            w, h = min(w, sw), min(h, sh)                          # 画面より大きければ収める
            return (max(sx, min(x, sx + sw - w)), max(sy, min(y, sy + sh - h)), w, h)
    sx, sy, sw, sh = screens[0]
    w, h = min(w, sw), min(h, sh)
    return (sx + min(40, max(0, sw - w)), sy + min(40, max(0, sh - h)), w, h)


class DictStore:
    """位置と大きさの置き場(``QSettings`` と同じ ``value`` / ``setValue``)。試験・単体用。"""

    def __init__(self):
        self.d: dict = {}

    def value(self, key, default=None):
        return self.d.get(key, default)

    def setValue(self, key, val):
        self.d[key] = val


class FloatingFrame(QtWidgets.QDialog):
    """モードレスの浮いた窓の入れ物。中身は任意の ``QWidget``。

    * Esc で閉じる / 位置と大きさを覚える(画面の外なら戻す)/ 本体の上に留まり、本体の終了に従う(親を持つ)。
    * ピン(「固定」): 中身が ``set_pinned`` を持てば追従を止める。固定中は題に印が付く。
    * 題 = 「対象の名前」(``title_base``)。中身が ``title()`` を持てばそれを使う。
    """

    closedWithState = QtCore.Signal(str)

    def __init__(self, content: QtWidgets.QWidget, key: str, title_base: str, store=None,
                 tr: Callable = identity_tr, parent=None, pinnable: bool = True):
        super().__init__(parent, QtCore.Qt.Window | QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinMaxButtonsHint)
        self.setModal(False)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self.key = key
        self.title_base = title_base
        self._store = store if store is not None else DictStore()
        self._tr = tr
        self.content = content
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        self.pin = None
        if pinnable:
            bar = QtWidgets.QHBoxLayout()
            bar.setContentsMargins(2, 0, 2, 0)
            self.pin = QtWidgets.QToolButton(self)
            self.pin.setCheckable(True)
            self.pin.setText(tr("Pin"))
            self.pin.setToolTip(tr("Pin: keep showing this value instead of following the current one"))
            self.pin.setAccessibleName(tr("Pin"))
            self.pin.toggled.connect(self._on_pin)
            bar.addWidget(self.pin)
            bar.addStretch(1)
            lay.addLayout(bar)
        lay.addWidget(content, 1)
        if hasattr(content, "titleChanged"):
            content.titleChanged.connect(self.setWindowTitle)
        self._update_title()
        self.restore()

    def _update_title(self) -> None:
        t = self.content.title() if hasattr(self.content, "title") else self.title_base
        self.setWindowTitle(t)

    def _on_pin(self, on: bool) -> None:
        if hasattr(self.content, "set_pinned"):
            self.content.set_pinned(on)
        else:
            self.setWindowTitle(self.title_base + ((" " + self._tr("[pinned]")) if on else ""))
        if self.pin is not None:
            self.pin.setText(self._tr("Pinned") if on else self._tr("Pin"))

    # ---- 位置と大きさ ----
    def _screens(self) -> list:
        return [(g.x(), g.y(), g.width(), g.height()) for g in (s.availableGeometry() for s in QtGui.QGuiApplication.screens())]

    def save(self) -> None:
        g = self.geometry()
        self._store.setValue("floating/" + self.key, json.dumps([g.x(), g.y(), g.width(), g.height()]))

    def restore(self, default_size: tuple = (420, 360)) -> None:
        raw = self._store.value("floating/" + self.key, None)
        try:
            x, y, w, h = json.loads(raw) if raw else (None,) * 4
        except (TypeError, ValueError):
            x = None
        if x is None:
            self.resize(*default_size)
            return
        x, y, w, h = clamp_rect_to_screens((int(x), int(y), int(w), int(h)), self._screens())
        self.setGeometry(x, y, w, h)

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(ev)

    def closeEvent(self, ev):
        self.save()
        self.closedWithState.emit(self.key)
        super().closeEvent(ev)

    def hideEvent(self, ev):
        self.save()
        super().hideEvent(ev)


class FloatingRegistry(QtCore.QObject):
    """開いている浮いた窓の管理。同じ物を 2 度開いたら既にある物を前に出す(複数枚を許す物は別の鍵で)。
    Window メニュー用に一覧・全部閉じる・本体の近くへ集める。"""

    changed = QtCore.Signal()

    def __init__(self, parent_window: QtWidgets.QWidget | None = None, store=None, tr: Callable = identity_tr):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.store = store if store is not None else DictStore()
        self._tr = tr
        self.frames: dict = {}

    def open(self, key: str, factory: Callable, title: str = "", pinnable: bool = True) -> FloatingFrame:
        fr = self.frames.get(key)
        if fr is not None:
            fr.show()
            fr.raise_()
            fr.activateWindow()
            return fr
        content = factory()
        fr = FloatingFrame(content, key, title or key, self.store, self._tr, self.parent_window, pinnable)
        fr.closedWithState.connect(self._on_closed)
        self.frames[key] = fr
        fr.show()
        self.changed.emit()
        return fr

    def open_unique(self, base_key: str, factory: Callable, title: str = "") -> FloatingFrame:
        """複数枚を許す物(変数の中身など): 鍵に通し番号を付け、題で区別する。"""
        n = 1
        while "%s#%d" % (base_key, n) in self.frames:
            n += 1
        return self.open("%s#%d" % (base_key, n), factory, title)

    def _on_closed(self, key: str) -> None:
        fr = self.frames.pop(key, None)
        if fr is not None:
            fr.deleteLater()
        self.changed.emit()

    def titles(self) -> list:
        return [fr.windowTitle() for fr in self.frames.values()]

    def close_all(self) -> None:
        for fr in list(self.frames.values()):
            fr.close()

    def gather(self, near: QtWidgets.QWidget | None = None) -> None:
        """全部を本体の近くへ集める(少しずつずらして並べる)。"""
        base = (near or self.parent_window)
        if base is None:
            return
        g = base.geometry()
        for i, fr in enumerate(self.frames.values()):
            fr.move(g.x() + 40 + 28 * i, g.y() + 60 + 28 * i)
            fr.raise_()

    def refresh_all(self) -> None:
        """追従する中身を最新にする(停止のたびに呼ぶ)。"""
        for fr in self.frames.values():
            c = fr.content
            if hasattr(c, "refresh") and not getattr(c, "pinned", False):
                c.refresh()
