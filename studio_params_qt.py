# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_params_qt — パラメータの束を並べて見る・直す窓(Qt。モードレス)。

中身は ``studio_params_model.ParamsModel``(Qt なし)。ここは見せ方だけを持つ。

* ``ParamsPanel``  — ``QWidget``。上に細い道具の帯(アイコン + ツールヒント)、中央に木つきの表(行 = キーの階層、
  列 = 束)、下に状態の 1 行。ドックにも浮いた窓にも入る。
* ``ParamsWindow`` — ``ParamsPanel`` を入れたモードレスの窓(Esc で閉じる・位置と大きさを覚える・未保存なら聞く)。
* ``show_params_window`` — Studio から呼ぶ入口(同じ親なら 2 枚目を作らず、既にある窓へ列を足して前に出す)。

単独でも開ける::

    python -m studio_params_qt [--lang ja] rig_day.json rig_night.yaml rig_lab.xml

見た目の決まり: 行の高さ = 文字 + 4 px、アイコンだけのボタンは 24 px の正方形で間は 4 px、色は Qt のパレットから
出す。差のあるセルは色を付けるが、**色だけに頼らない**(行の印 ≠ / ◌ / ≈、セルの小さな印、片方に無いセルは斜線)。
画面の文は全部 ``tr`` を通す(対訳は ``studio_assets/studio_params_i18n.json``。Studio の ``tr`` を渡してもよい)。
"""
from __future__ import annotations

import inspect
import json
import os
import sys
from typing import Any, Callable, Sequence

from PySide6 import QtCore, QtGui, QtWidgets

import studio_params_model as M

__all__ = ["ParamsPanel", "ParamsWindow", "show_params_window", "main", "ROW_EXTRA_PX", "BUTTON_PX", "GAP_PX",
           "MARK_DIFFER", "MARK_PARTIAL", "MARK_NOTATION", "MARK_USED"]

#: 行の高さ = 文字の高さ + これ。
ROW_EXTRA_PX = 4
#: アイコンだけのボタンの一辺と、隣り合う押せる物の間。
BUTTON_PX = 24
GAP_PX = 4
_ICON_PX = 16
_INDENT_PX = 12
_CELL_MARK_PX = 8

#: 行の印(色に頼らない)。違う / 一部の束に無い / 値は同じで書き方が違う / 直前の実行が読んだ。
MARK_DIFFER = "≠"
MARK_PARTIAL = "◌"
MARK_NOTATION = "≈"
MARK_USED = "▸"

#: 値の型の、画面での呼び名(英語が正)。
KIND_LABELS = {"bool": "true / false", "int": "whole number", "float": "number", "quantity": "number with a unit",
               "str": "text", "list": "list"}

_SETTINGS_GROUP = "params_window"
_FILTER = "*.json *.toml *.yaml *.yml *.xml"

Qt = QtCore.Qt


def _default_settings() -> QtCore.QSettings:
    """Studio と同じ設定の置き場(``FULLSEYE_STUDIO_SETTINGS`` が指す ini があればそちら)。"""
    ini = os.environ.get("FULLSEYE_STUDIO_SETTINGS", "")
    if ini:
        return QtCore.QSettings(ini, QtCore.QSettings.IniFormat)
    return QtCore.QSettings("Fullseye", "Studio")


def _mix(a: QtGui.QColor, b: QtGui.QColor, t: float) -> QtGui.QColor:
    return QtGui.QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                        round(a.blue() + (b.blue() - a.blue()) * t))


# --------------------------------------------------------------------------- #
# アイコン(資産ファイルなし。パレットの文字の色で線を引く)
# --------------------------------------------------------------------------- #
def _draw_icon(name: str, color: QtGui.QColor, px: int = _ICON_PX) -> QtGui.QIcon:
    r = 2
    pm = QtGui.QPixmap(px * r, px * r)
    pm.setDevicePixelRatio(r)
    pm.fill(Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    pen = QtGui.QPen(color)
    pen.setWidthF(1.5)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    s = px / 16.0

    def P(x: float, y: float) -> QtCore.QPointF:
        return QtCore.QPointF(x * s, y * s)

    def line(*pts: float) -> None:
        poly = QtGui.QPolygonF([P(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)])
        p.drawPolyline(poly)

    def arrow_arc(flip: bool) -> None:
        rect = QtCore.QRectF(3 * s, 4.5 * s, 10 * s, 9 * s)
        p.drawArc(rect, (20 if flip else 160) * 16, (140 if flip else -140) * 16)
        if flip:
            line(9.5, 3.2, 12.6, 6.4, 8.6, 7.6)
        else:
            line(6.5, 3.2, 3.4, 6.4, 7.4, 7.6)

    if name == "open":                     # フォルダ
        line(2, 12.5, 2, 4, 6, 4, 7.5, 5.5, 14, 5.5, 14, 12.5, 2, 12.5)
    elif name == "add":                    # 列 + 足す
        line(3, 3, 3, 13)
        line(6.5, 3, 6.5, 13)
        line(11.5, 5, 11.5, 11)
        line(8.5, 8, 14.5, 8)
    elif name == "remove":                 # 列 + 外す
        line(3, 3, 3, 13)
        line(6.5, 3, 6.5, 13)
        line(9, 8, 14.5, 8)
    elif name == "save":                   # フロッピー
        line(2.5, 2.5, 11, 2.5, 13.5, 5, 13.5, 13.5, 2.5, 13.5, 2.5, 2.5)
        line(5, 2.5, 5, 6, 10, 6, 10, 2.5)
        line(5, 13.5, 5, 9.5, 11, 9.5, 11, 13.5)
    elif name == "saveas":                 # フロッピー + 鉛筆
        line(2.5, 2.5, 9, 2.5, 11.5, 5, 11.5, 7)
        line(2.5, 2.5, 2.5, 13.5, 7, 13.5)
        line(5, 2.5, 5, 6, 8.5, 6)
        line(9, 13.8, 9.6, 11.4, 13.4, 7.6, 15, 9.2, 11.2, 13, 9, 13.8)
    elif name == "reload":                 # 回る矢印
        p.drawArc(QtCore.QRectF(3 * s, 3 * s, 10 * s, 10 * s), 40 * 16, 280 * 16)
        line(9.2, 2.2, 12.4, 3.6, 11.4, 6.8)
    elif name == "undo":
        arrow_arc(False)
    elif name == "redo":
        arrow_arc(True)
    elif name == "copy":                   # 列から列へ
        line(3, 3, 3, 13)
        line(13, 3, 13, 13)
        line(5, 8, 11, 8)
        line(8.8, 5.6, 11.2, 8, 8.8, 10.4)
    elif name == "diff":                   # ≠
        line(3.5, 6, 12.5, 6)
        line(3.5, 10, 12.5, 10)
        line(10.5, 3, 5.5, 13)
    elif name == "search":
        p.drawEllipse(P(7, 7), 4 * s, 4 * s)
        line(10, 10, 13.5, 13.5)
    elif name == "celldiff":               # セルの角の印(三角)
        p.setBrush(color)
        p.drawPolygon(QtGui.QPolygonF([P(3, 3), P(13, 3), P(3, 13)]))
    else:
        raise ValueError("unknown icon %r" % name)
    p.end()
    return QtGui.QIcon(pm)


# --------------------------------------------------------------------------- #
# 確認の窓(設計書 P09: 出すのは Undo で戻せない時だけ・既定と Esc はキャンセル・ボタンは tr を通した動詞・
# Qt の標準ボタンを使わない・作る関数と見せる関数を分ける)
# --------------------------------------------------------------------------- #
#: ボタンの役割の鍵 → Qt の役割(左右の並びは役割で Qt に任せる。手で並べない)。
_CONFIRM_ROLES = {
    "save": QtWidgets.QMessageBox.AcceptRole, "reload": QtWidgets.QMessageBox.AcceptRole,
    "discard": QtWidgets.QMessageBox.DestructiveRole, "overwrite": QtWidgets.QMessageBox.DestructiveRole,
    "run": QtWidgets.QMessageBox.DestructiveRole, "cancel": QtWidgets.QMessageBox.RejectRole,
}
#: 未保存の窓の動詞: 操作 → (題 = 操作の名前, 保存して<動詞>, 保存せずに<動詞>)。英語が正(tr で訳す)。
UNSAVED_VERBS = {
    "close": ("Close", "Save and close", "Close without saving"),
    "open": ("Open", "Save and open", "Open without saving"),
    "remove": ("Remove column", "Save and remove", "Remove without saving"),
}
#: 確認の種類(設計書 P09-2 の kind)ごとのボタン [(役割の鍵, 英語の文)]。run の動詞は呼ぶ所が渡す。
CHANGED_BUTTONS = (("reload", "Reload"), ("overwrite", "Overwrite anyway"), ("cancel", "Cancel"))


def _label(text: str) -> str:
    """ボタンに出す文('&' をニーモニックにしない = '&&')。"""
    return text.replace("&", "&&")


def _build_confirm_box(parent: QtWidgets.QWidget | None, title: str, text: str, buttons: Sequence[tuple[str, str]],
                       details: str = "") -> QtWidgets.QMessageBox:
    """確認の箱を**作る**(見せない)。``buttons`` = [(役割の鍵, 画面の文)](文は tr を通した物)。

    標準ボタンは使わない(全部 addButton)。既定のボタン(Enter)と Esc は ``"cancel"`` のボタン。ボタンには
    property ``fsRole`` = 役割の鍵を付ける(押された物の答えと、門が数える時の目印)。``"cancel"`` が無ければ
    ``ValueError``(キャンセルできない確認は作らない)。"""
    keys = [k for k, _s in buttons]
    if "cancel" not in keys or len(set(keys)) != len(keys) or any(k not in _CONFIRM_ROLES for k in keys):
        raise ValueError("a confirm box needs distinct known roles and a cancel button: %r" % (keys,))
    box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, title, text, QtWidgets.QMessageBox.NoButton, parent)
    box.setTextFormat(Qt.PlainText)
    if details:
        box.setInformativeText(details)
    cancel = None
    for key, label in buttons:
        b = box.addButton(_label(label), _CONFIRM_ROLES[key])
        b.setProperty("fsRole", key)
        if key == "cancel":
            cancel = b
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    return box


def _exec_confirm_box(box: QtWidgets.QMessageBox) -> str:
    """作った箱を**見せて**答えを待つ。押したボタンの役割の鍵(閉じただけ・知らない物は ``"cancel"``)。"""
    box.exec()
    hit = box.clickedButton()
    role = hit.property("fsRole") if hit is not None else None
    return role if isinstance(role, str) and role in _CONFIRM_ROLES else "cancel"


def _accepts_kind(fn: Callable[..., Any]) -> bool:
    """``fn`` が新しい形の confirm_action(``kind=`` / ``buttons=`` を受ける)か。"""
    try:
        params = inspect.signature(fn).parameters.values()
    except (TypeError, ValueError):
        return False
    names = {p.name for p in params}
    return "kind" in names or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params)


_ROLE_NAMES = {"accept": QtWidgets.QMessageBox.AcceptRole, "destructive": QtWidgets.QMessageBox.DestructiveRole,
               "reject": QtWidgets.QMessageBox.RejectRole}


def _answer_key(got: Any, buttons: Sequence[tuple[str, str]]) -> str:
    """親の confirm_action の答えを、こちらの役割の鍵にする。分からない答えは ``"cancel"``(fail-closed)。

    受ける形: 役割の鍵の文字 / Qt の役割(QMessageBox.ButtonRole か、その名前 accept / destructive / reject)/
    真偽(2 択の時だけ。真 = キャンセルでない方)。"""
    keys = [k for k, _s in buttons]
    if isinstance(got, bool):
        others = [k for k in keys if k != "cancel"]
        return others[0] if got and len(others) == 1 else "cancel"
    if isinstance(got, str) and got in keys:
        return got
    role = _ROLE_NAMES.get(got.lower()) if isinstance(got, str) else got
    if isinstance(role, QtWidgets.QMessageBox.ButtonRole):
        hits = [k for k in keys if _CONFIRM_ROLES[k] == role]
        if len(hits) == 1:
            return hits[0]
    return "cancel"


class _ElideLabel(QtWidgets.QLabel):
    """1 行に収まらなければ末尾を … にするラベル(全文はツールヒント)。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.setTextFormat(Qt.PlainText)

    def set_full_text(self, text: str) -> None:
        self._full = text
        self.setToolTip(text)
        self._apply()

    def full_text(self) -> str:
        return self._full

    def _apply(self) -> None:
        self.setText(self.fontMetrics().elidedText(self._full, Qt.ElideRight, max(0, self.width() - 2)))

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        super().resizeEvent(ev)
        self._apply()


# --------------------------------------------------------------------------- #
# 木つきの表のモデル
# --------------------------------------------------------------------------- #
class ParamsTreeModel(QtCore.QAbstractItemModel):
    """行 = キーの階層、列 = [キー, 印, 束 1, 束 2, …]。"""

    rejected = QtCore.Signal(str)          #: 編集を断った理由(その言語で)
    edited = QtCore.Signal(object)         #: 編集が通った(Outcome)

    FIXED = 2                              # キーの列と印の列

    def __init__(self, model: M.ParamsModel, tr: Callable[[str], str], parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.m = model
        self.tr = tr
        self.diff_only = False
        self.query = ""
        self._top: list[M.Node] = []
        self._parent: dict[int, tuple[M.Node | None, int]] = {}
        self._rows: dict[str, M.Row] = {}
        self._agg: dict[int, tuple[int, int, bool]] = {}
        self._diff_brush: QtGui.QBrush | None = None
        self._missing_brush: QtGui.QBrush | None = None
        self._cell_icon: QtGui.QIcon | None = None
        self._bold: QtGui.QFont | None = None
        self.rebuild()

    # ---- 見た目の材料(パレットから) ----
    def set_palette(self, pal: QtGui.QPalette, font: QtGui.QFont) -> None:
        base, text = pal.color(QtGui.QPalette.Base), pal.color(QtGui.QPalette.Text)
        self._diff_brush = QtGui.QBrush(_mix(base, QtGui.QColor(232, 163, 61), 0.30))
        self._missing_brush = QtGui.QBrush(_mix(base, text, 0.30), Qt.BDiagPattern)
        self._cell_icon = _draw_icon("celldiff", _mix(base, text, 0.75), _CELL_MARK_PX)
        self._bold = QtGui.QFont(font)
        self._bold.setBold(True)

    # ---- 作り直し ----
    def rebuild(self) -> None:
        """木を作り直す(列・行の集まり・絞り込みが変わった時)。"""
        self.beginResetModel()
        self._top = self.m.tree(diff_only=self.diff_only, query=self.query)
        self._parent = {}
        self._index_nodes(self._top, None)
        self._sync_rows()
        self.endResetModel()

    def _index_nodes(self, nodes: list[M.Node], parent: M.Node | None) -> None:
        for i, n in enumerate(nodes):
            self._parent[id(n)] = (parent, i)
            if n.children:
                self._index_nodes(n.children, n)

    def _sync_rows(self) -> None:
        self._rows = {r.key: r for r in self.m.rows()}
        self._agg = {}
        for n in self._top:
            self._aggregate(n)

    def _aggregate(self, n: M.Node) -> tuple[int, int, bool]:
        if n.row is not None:
            r = self._rows.get(n.key, n.row)
            out = (int(r.status == "differ"), int(r.status == "partial"), r.used)
        else:
            d = p = 0
            u = False
            for ch in n.children:
                cd, cp, cu = self._aggregate(ch)
                d, p, u = d + cd, p + cp, u or cu
            out = (d, p, u)
        self._agg[id(n)] = out
        return out

    def sync(self) -> None:
        """値だけが変わった時(木の形は同じ): 行を読み直して全部を描き直させる。"""
        self._sync_rows()
        self._emit_changed(QtCore.QModelIndex())
        if self.columnCount():
            self.headerDataChanged.emit(Qt.Horizontal, 0, self.columnCount() - 1)

    def _emit_changed(self, parent: QtCore.QModelIndex) -> None:
        n = self.rowCount(parent)
        if not n:
            return
        self.dataChanged.emit(self.index(0, 0, parent), self.index(n - 1, self.columnCount() - 1, parent))
        for i in range(n):
            self._emit_changed(self.index(i, 0, parent))

    # ---- QAbstractItemModel ----
    def _node(self, index: QtCore.QModelIndex) -> M.Node | None:
        return index.internalPointer() if index.isValid() else None

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        pn = self._node(parent)
        nodes = self._top if pn is None else pn.children
        if not (0 <= row < len(nodes)) or not (0 <= column < self.columnCount()):
            return QtCore.QModelIndex()
        return self.createIndex(row, column, nodes[row])

    def parent(self, index: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:  # type: ignore[override]
        n = self._node(index)
        if n is None:
            return QtCore.QModelIndex()
        pn, _ = self._parent.get(id(n), (None, 0))
        if pn is None:
            return QtCore.QModelIndex()
        return self.createIndex(self._parent[id(pn)][1], 0, pn)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid() and parent.column() != 0:
            return 0
        pn = self._node(parent)
        return len(self._top) if pn is None else len(pn.children)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return self.FIXED + len(self.m.columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation != Qt.Horizontal:
            return None
        tr = self.tr
        if section == 0:
            if role == Qt.DisplayRole:
                return tr("Key")
            if role == Qt.ToolTipRole:
                return tr("Key: the name of the value. Sections fold.")
            return None
        if section == 1:
            if role == Qt.DisplayRole:
                return MARK_DIFFER
            if role == Qt.ToolTipRole:
                return self.legend()
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignCenter)
            return None
        col = self.m.columns[section - self.FIXED] if section - self.FIXED < len(self.m.columns) else None
        if col is None:
            return None
        if role == Qt.DisplayRole:
            return self.column_title(section - self.FIXED)
        if role == Qt.ToolTipRole:
            lines = [col.path or tr("not saved to a file yet")]
            if not col.writable:
                lines.append(tr(M.MESSAGES["edit.readonly"]) % (col.name,))
            for code, args, _block in self.m.save_losses(section - self.FIXED):
                lines.append(tr("On save:") + " " + (tr(M.MESSAGES[code]) % args))
            return "\n".join(lines)
        return None

    def column_title(self, i: int) -> str:
        """列の見出し: 束の名前 + 未保存の印 * + 読むだけの印。"""
        col = self.m.columns[i]
        t = col.name
        if not col.writable:
            t += " (" + self.tr("read-only") + ")"
        if col.dirty():
            t += " *"
        return t

    def legend(self) -> str:
        """印の説明(ツールヒント)。"""
        tr = self.tr
        return "\n".join([
            "%s  %s" % (MARK_DIFFER, tr("the bundles hold different values")),
            "%s  %s" % (MARK_PARTIAL, tr("not in every bundle")),
            "%s  %s" % (MARK_NOTATION, tr("same value, written differently")),
            "%s  %s" % (MARK_USED, tr("read by the last run")),
            "*  %s" % tr("changed, not saved yet (bold)"),
        ])

    def mark_text(self, n: M.Node) -> str:
        """印の列の文字。"""
        d, p, used = self._agg.get(id(n), (0, 0, False))
        out = ""
        if d:
            out += MARK_DIFFER
        if p:
            out += MARK_PARTIAL
        if n.row is not None:
            r = self._rows.get(n.key, n.row)
            if r.notation_differs:
                out += MARK_NOTATION
        if used:
            out += MARK_USED
        return out

    def _cell(self, index: QtCore.QModelIndex) -> tuple[M.Node | None, M.Row | None, int, Any]:
        n = self._node(index)
        ci = index.column() - self.FIXED
        if n is None or n.row is None or not 0 <= ci < len(self.m.columns):
            return n, None, ci, None
        r = self._rows.get(n.key, n.row)
        v = r.values[ci] if ci < len(r.values) else None
        return n, r, ci, v

    def cell_differs(self, key: str, ci: int) -> bool:
        """この行が「違う」で、このセルが最初の束(基準)の値と違うか。"""
        r = self._rows.get(key)
        if r is None or r.status != "differ" or ci >= len(r.values):
            return False
        return ci != 0 and not M.parambundle.values_equal(r.values[0], r.values[ci])

    def data(self, index: QtCore.QModelIndex, role: int = Qt.DisplayRole) -> Any:
        n = self._node(index)
        if n is None:
            return None
        c = index.column()
        tr = self.tr
        if c == 0:
            if role == Qt.DisplayRole:
                return n.label
            if role == Qt.ToolTipRole:
                return n.key
            return None
        if c == 1:
            if role == Qt.DisplayRole:
                return self.mark_text(n)
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignCenter)
            if role == Qt.ToolTipRole:
                d, p, _u = self._agg.get(id(n), (0, 0, False))
                if n.row is None:
                    return (tr("%d differing row(s) inside") % d + "\n" + tr("%d row(s) not in every bundle") % p
                            if d or p else None)
                return self.legend() if self.mark_text(n) else None
            return None
        n, r, ci, v = self._cell(index)
        if r is None:
            return None
        col = self.m.columns[ci]
        if role == Qt.DisplayRole:
            return "" if v is None else M.format_value(v)
        if role == Qt.EditRole:
            return "" if v is None else M.format_value(v)
        if role == Qt.CheckStateRole:
            return (Qt.Checked if v else Qt.Unchecked) if isinstance(v, bool) else None
        if role == Qt.BackgroundRole:
            if v is None:
                return self._missing_brush
            return self._diff_brush if r.status == "differ" else None
        if role == Qt.DecorationRole:
            return self._cell_icon if self.cell_differs(r.key, ci) else None
        if role == Qt.FontRole:
            return self._bold if col.cell_dirty(r.key) else None
        if role == Qt.ToolTipRole:
            if v is None:
                return tr("%s is not in %s") % (r.key, col.name)
            lines = ["%s  (%s)" % (r.key, tr(KIND_LABELS[M.kind_of(v)]))]
            if col.cell_dirty(r.key):
                saved = col.saved.get(r.key)
                lines.append(tr("saved value: %s") % ("" if saved is None else M.format_value(saved)))
            who = col.used.get(r.key)
            if who is not None:
                lines.append(tr("read by the last run") + (": " + ", ".join(who) if who else ""))
            if r.status == "differ":
                lines.append(MARK_DIFFER + " " + tr("the bundles hold different values"))
            elif r.notation_differs:
                lines.append(MARK_NOTATION + " " + tr("same value, written differently"))
            return "\n".join(lines)
        return None

    def flags(self, index: QtCore.QModelIndex) -> Qt.ItemFlags:
        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        n, r, ci, v = self._cell(index)
        if r is None or v is None or not self.m.columns[ci].writable:
            return f
        if isinstance(v, bool):
            return f | Qt.ItemIsUserCheckable
        return f | Qt.ItemIsEditable

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        n, r, ci, v = self._cell(index)
        if r is None or v is None:
            return False
        if role == Qt.CheckStateRole and isinstance(v, bool):
            checked = value is True or (not isinstance(value, bool) and value in (Qt.Checked, Qt.Checked.value))
            out = self.m.set_raw(ci, r.key, bool(checked))
        elif role == Qt.EditRole:
            if str(value) == M.format_value(v):
                return False                              # 触っただけ(変えていない)
            out = self.m.set_value(ci, r.key, str(value))
        else:
            return False
        if not out.ok:
            self.rejected.emit(out.text(self.tr))
            return False
        self.sync()
        self.edited.emit(out)
        return True


class _Delegate(QtWidgets.QStyledItemDelegate):
    """行の高さ = 文字 + 4 px。編集は枠なしの文字の欄(数もスピンでなく文字 + 検査)。"""

    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
        sz = super().sizeHint(option, index)
        return QtCore.QSize(sz.width(), option.fontMetrics.height() + ROW_EXTRA_PX)

    def createEditor(self, parent: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex) -> QtWidgets.QWidget:
        ed = QtWidgets.QLineEdit(parent)
        ed.setFrame(False)
        ed.setContentsMargins(0, 0, 0, 0)
        ed.setTextMargins(0, 0, 0, 0)
        return ed

    def setEditorData(self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex) -> None:
        editor.setText(index.data(Qt.EditRole) or "")      # type: ignore[attr-defined]
        editor.selectAll()                                  # type: ignore[attr-defined]

    def setModelData(self, editor: QtWidgets.QWidget, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex) -> None:
        model.setData(index, editor.text(), Qt.EditRole)    # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# パネル
# --------------------------------------------------------------------------- #
class ParamsPanel(QtWidgets.QWidget):
    """道具の帯 + 木つきの表 + 状態の 1 行。"""

    titleChanged = QtCore.Signal(str)
    changed = QtCore.Signal()

    #: 空の状態の案内(何をする場所か 1 行)。
    EMPTY_TEXT = ("Parameter bundles side by side: rows are keys, columns are files. Open JSON, TOML, YAML or XML "
                  "files, or drop them here.")

    def __init__(self, tr: Callable[[str], str] | None = None, parent: QtWidgets.QWidget | None = None,
                 model: M.ParamsModel | None = None, settings: Callable[[], Any] | None = None) -> None:
        super().__init__(parent)
        self.tr_ = tr or (lambda s: s)
        self.model = model or M.ParamsModel()
        self._settings = settings or _default_settings
        self._user_sized = False
        self.message_level = "info"
        self._fit_pending = False
        self._last_external: list[tuple[int, str]] = []
        # 聞く所は差し替えられる(試験・Studio の様式)。
        self.ask_unsaved: Callable[[list[str]], str] = self._ask_unsaved_box
        self.ask_losses: Callable[[str, list[str]], bool] = self._ask_losses_box
        self.ask_overwrite: Callable[[str, str], str] = self._ask_overwrite_box
        self.pick_open: Callable[[], list[str]] = self._pick_open_dialog
        self.pick_save: Callable[[int], str] = self._pick_save_dialog
        #: 親(Studio)の confirm_action(``set_confirm``)。None = 自前の箱(同じ形)。
        self._confirm_fn: Callable[..., Any] | None = None
        self._build()
        self.setAcceptDrops(True)
        self.refresh()

    # ---- 組み立て ----
    def _build(self) -> None:
        tr = self.tr_
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        self.bar = QtWidgets.QWidget(self)
        bl = QtWidgets.QHBoxLayout(self.bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(GAP_PX)
        color = self.palette().color(QtGui.QPalette.ButtonText)
        self.buttons: dict[str, QtWidgets.QToolButton] = {}

        def button(key: str, icon: str, name: str, what: str, slot: Callable[[], Any] | None, shortcut: str = "",
                   checkable: bool = False) -> QtWidgets.QToolButton:
            b = QtWidgets.QToolButton(self.bar)
            b.setIcon(_draw_icon(icon, color))
            b.setIconSize(QtCore.QSize(_ICON_PX, _ICON_PX))
            b.setFixedSize(BUTTON_PX, BUTTON_PX)
            b.setAutoRaise(True)
            b.setCheckable(checkable)
            b.setAccessibleName(tr(name))
            tip = "%s — %s" % (tr(name), tr(what))
            b.setToolTip(tip + (" (%s)" % shortcut if shortcut else ""))
            if slot is not None:
                (b.toggled if checkable else b.clicked).connect(slot)
            if shortcut:
                sc = QtGui.QShortcut(QtGui.QKeySequence(shortcut), self)
                sc.setContext(Qt.WidgetWithChildrenShortcut)
                sc.activated.connect(b.toggle if checkable else b.click)
            bl.addWidget(b)
            self.buttons[key] = b
            return b

        button("open", "open", "Open", "open parameter files in place of the ones shown", self.open_files, "Ctrl+O")
        button("add", "add", "Add column", "add parameter files beside the ones shown", self.add_files, "Ctrl+Shift+O")
        button("remove", "remove", "Remove column", "take the selected bundle out of the table (the file stays)",
               self.remove_current)
        bl.addSpacing(GAP_PX)
        button("save", "save", "Save", "write every changed bundle back to its file", self.save_all, "Ctrl+S")
        button("saveas", "saveas", "Save As", "write the selected bundle to a new JSON, YAML or XML file",
               self.save_current_as, "Ctrl+Shift+S")
        button("reload", "reload", "Reload", "read the selected bundle again from its file", self.reload_current)
        bl.addSpacing(GAP_PX)
        button("undo", "undo", "Undo", "take back the last change", self.undo, "Ctrl+Z")
        button("redo", "redo", "Redo", "apply the change again", self.redo, "Ctrl+Y")
        cp = button("copy", "copy", "Copy to column", "copy the selected value, or every differing value, to another bundle",
                    None)
        cp.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.copy_menu = QtWidgets.QMenu(cp)
        self.copy_menu.aboutToShow.connect(self._fill_copy_menu)
        cp.setMenu(self.copy_menu)
        bl.addSpacing(GAP_PX)
        button("diff", "diff", "Differences only", "show only the rows where the bundles differ", self.set_diff_only,
               "Ctrl+D", checkable=True)
        self.search = QtWidgets.QLineEdit(self.bar)
        self.search.setPlaceholderText(tr("Search keys"))
        self.search.setToolTip(tr("Search keys") + " — " + tr("show only the keys that contain this text") + " (Ctrl+F)")
        self.search.setAccessibleName(tr("Search keys"))
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(BUTTON_PX)
        self.search.setMinimumWidth(60)
        self.search.addAction(_draw_icon("search", color), QtWidgets.QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self.set_query)
        bl.addWidget(self.search, 1)
        sc = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        sc.setContext(Qt.WidgetWithChildrenShortcut)
        sc.activated.connect(lambda: (self.search.setFocus(), self.search.selectAll()))
        lay.addWidget(self.bar)

        self.stack = QtWidgets.QStackedWidget(self)
        # 空の状態: 何をする場所か 1 行、最初の一手 1 つ、例 1 つ。
        self.empty = QtWidgets.QWidget(self.stack)
        el = QtWidgets.QVBoxLayout(self.empty)
        el.setContentsMargins(6, 6, 6, 6)
        el.setSpacing(8)
        el.addStretch(1)
        self.empty_label = QtWidgets.QLabel(tr(self.EMPTY_TEXT), self.empty)
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignCenter)
        el.addWidget(self.empty_label)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(GAP_PX)
        row.addStretch(1)
        self.empty_open = QtWidgets.QPushButton(tr("Open files"), self.empty)
        self.empty_open.clicked.connect(self.open_files)
        self.empty_example = QtWidgets.QPushButton(tr("Open the example"), self.empty)
        self.empty_example.setToolTip(tr("Two bundles of the same rig (day and night) to try comparing and copying"))
        self.empty_example.clicked.connect(self.open_example)
        row.addWidget(self.empty_open)
        row.addWidget(self.empty_example)
        row.addStretch(1)
        el.addLayout(row)
        el.addStretch(1)
        self.stack.addWidget(self.empty)

        self.tree = QtWidgets.QTreeView(self.stack)
        self.tmodel = ParamsTreeModel(self.model, tr, self)
        self.tmodel.set_palette(self.palette(), self.font())
        self.tree.setModel(self.tmodel)
        self.tree.setItemDelegate(_Delegate(self.tree))
        self.tree.setUniformRowHeights(True)
        self.tree.setIndentation(_INDENT_PX)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed
                                  | QtWidgets.QAbstractItemView.AnyKeyPressed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.setFrameShape(QtWidgets.QFrame.NoFrame)
        # 行の高さ: Windows 11 の様式は行に上下の余白を足すので、::item の高さで詰める(委譲の sizeHint と同じ値)。
        self.tree.setStyleSheet("QTreeView::item { height: %dpx; padding: 0px; }" % self.row_height())
        hdr = self.tree.header()
        hdr.setMinimumSectionSize(20)
        hdr.setStretchLastSection(True)
        hdr.setSectionsMovable(False)
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setFixedHeight(self.row_height() + 2)
        hdr.installEventFilter(self)
        self.tree.viewport().installEventFilter(self)
        self.tree.setIconSize(QtCore.QSize(_CELL_MARK_PX, _CELL_MARK_PX))
        self.tree.selectionModel().currentChanged.connect(lambda *_: self._update_actions())
        self.tmodel.rejected.connect(self._on_rejected)
        self.tmodel.edited.connect(self._on_edited)
        self.stack.addWidget(self.tree)
        lay.addWidget(self.stack, 1)

        self.status = QtWidgets.QWidget(self)
        sl = QtWidgets.QHBoxLayout(self.status)
        sl.setContentsMargins(2, 0, 2, 0)
        sl.setSpacing(8)
        self.counts_label = QtWidgets.QLabel(self.status)
        self.counts_label.setTextFormat(Qt.PlainText)
        self.message_label = _ElideLabel(self.status)
        sl.addWidget(self.counts_label)
        sl.addWidget(self.message_label, 1)
        self.status.setFixedHeight(self.row_height())
        self.status.installEventFilter(self)
        lay.addWidget(self.status)

    def row_height(self) -> int:
        """行の高さ(px)= 文字の高さ + ``ROW_EXTRA_PX``。"""
        return self.fontMetrics().height() + ROW_EXTRA_PX

    # ---- 状態の表示 ----
    def title(self) -> str:
        """窓の題: 「パラメータ — a.json, b.yaml *」。"""
        tr = self.tr_
        names = [c.name + (" *" if c.dirty() else "") for c in self.model.columns]
        return tr("Parameters") + (" — " + ", ".join(names) if names else "")

    def counts_text(self, compact: bool = False) -> str:
        """状態の 1 行の左側(束の数、行の数、違う行の数、未保存の印)。``compact`` は狭い窓用(印 + 数だけ)。"""
        tr = self.tr_
        c = self.model.counts()
        parts = [tr("%d bundle(s)") % c["columns"]]
        if not c["columns"]:
            return parts[0]
        if compact:
            parts.append("%s %d" % (MARK_DIFFER, c["differ"]))
            if c["partial"]:
                parts.append("%s %d" % (MARK_PARTIAL, c["partial"]))
            if c["dirty"]:
                parts.append("* %d" % c["dirty"])
            return " \u00b7 ".join(parts)
        shown = len(self.model.rows(diff_only=self.tmodel.diff_only, query=self.tmodel.query))
        if shown != c["rows"]:
            parts.append(tr("%d of %d row(s)") % (shown, c["rows"]))
        else:
            parts.append(tr("%d row(s)") % c["rows"])
        parts.append("%s %s" % (MARK_DIFFER, tr("%d differ") % c["differ"]))
        if c["partial"]:
            parts.append("%s %s" % (MARK_PARTIAL, tr("%d not in every bundle") % c["partial"]))
        if c["dirty"]:
            parts.append("* " + tr("%d unsaved") % c["dirty"])
        return " · ".join(parts)

    def show_message(self, text: str, level: str = "info") -> None:
        """状態の 1 行の右側。``level`` = info / warn / error(形 + 語。色だけにしない)。"""
        mark = {"info": "", "warn": "▲ ", "error": "✕ "}[level]
        self.message_label.set_full_text(mark + text if text else "")
        self.message_level = level
        pal = self.message_label.palette()
        base = self.palette().color(QtGui.QPalette.WindowText)
        tone = {"info": base, "warn": _mix(base, QtGui.QColor(232, 163, 61), 0.6),
                "error": _mix(base, QtGui.QColor(217, 83, 79), 0.7)}[level]
        pal.setColor(QtGui.QPalette.WindowText, tone)
        self.message_label.setPalette(pal)

    def _outcome(self, out: M.Outcome) -> M.Outcome:
        text = out.text(self.tr_)
        notes = out.note_texts(self.tr_)
        if not out.ok:
            self.show_message("; ".join([text] + notes) if text else "", "error")
        else:
            self.show_message("; ".join(([text] if text else []) + notes), "warn" if notes and not text else "info")
        return out

    def _on_rejected(self, text: str) -> None:
        self.show_message(text, "error")
        idx = self.tree.currentIndex()
        if idx.isValid() and self.isVisible():
            QtWidgets.QToolTip.showText(self.tree.viewport().mapToGlobal(self.tree.visualRect(idx).bottomLeft()), text, self.tree)

    def _on_edited(self, out: M.Outcome) -> None:
        self._outcome(out)
        self._after_change(structure=bool(self.tmodel.diff_only), deferred=True)

    # ---- 作り直し ----
    def _expanded_keys(self) -> set[str] | None:
        if not self.tmodel._top:
            return None
        out: set[str] = set()

        def walk(parent: QtCore.QModelIndex) -> None:
            for i in range(self.tmodel.rowCount(parent)):
                idx = self.tmodel.index(i, 0, parent)
                n = idx.internalPointer()
                if n.children:
                    if self.tree.isExpanded(idx):
                        out.add(n.key)
                    walk(idx)

        walk(QtCore.QModelIndex())
        return out

    def _all_section_keys(self) -> set[str]:
        out: set[str] = set()

        def walk(nodes: list[M.Node]) -> None:
            for n in nodes:
                if n.children:
                    out.add(n.key)
                    walk(n.children)

        walk(self.tmodel._top)
        return out

    def refresh(self) -> None:
        """木を作り直して全部を描き直す(開いていた節・選んでいたセルは保つ)。"""
        before_sections = self._all_section_keys()
        expanded = self._expanded_keys()
        cur = self.current_cell()
        ncols = self.tmodel.columnCount()
        self.tmodel.rebuild()

        def walk(parent: QtCore.QModelIndex) -> None:
            for i in range(self.tmodel.rowCount(parent)):
                idx = self.tmodel.index(i, 0, parent)
                n = idx.internalPointer()
                if n.children:
                    self.tree.setExpanded(idx, expanded is None or n.key in expanded or n.key not in before_sections)
                    walk(idx)

        walk(QtCore.QModelIndex())
        if cur is not None:
            self.select_cell(cur[0], cur[1])
        self.stack.setCurrentWidget(self.tree if self.model.columns else self.empty)
        if ncols != self.tmodel.columnCount() or not self._user_sized:
            self._fit_columns()
        self._update_status()

    def _after_change(self, structure: bool = True, deferred: bool = False) -> None:
        if structure:
            if deferred:
                QtCore.QTimer.singleShot(0, self.refresh)
            else:
                self.refresh()
        else:
            self.tmodel.sync()
        self._update_status()

    def flush(self) -> None:
        """後回しにした作り直しを今やる(試験用)。"""
        self.refresh()

    def _apply_counts(self) -> None:
        """状態の行の左側を入れる。語つきの形が幅に収まらなければ、印 + 数だけの形にする(全文はツールヒント)。"""
        full = self.counts_text()
        room = self.status.width() - 4 - 8 - 40          # 枠の内側・間・右側の知らせに残す最小の幅
        fits = self.counts_label.fontMetrics().horizontalAdvance(full) <= room
        self.counts_label.setText(full if fits else self.counts_text(compact=True))
        self.counts_label.setToolTip(full + "\n" + self.tmodel.legend())

    def _update_status(self) -> None:
        self._apply_counts()
        self._update_actions()
        t = self.title()
        self.titleChanged.emit(t)
        self.changed.emit()

    def _update_actions(self) -> None:
        cur = self.current_column()
        col = self.model.columns[cur] if cur is not None else None
        has = bool(self.model.columns)
        self.buttons["remove"].setEnabled(col is not None)
        self.buttons["saveas"].setEnabled(col is not None)
        self.buttons["reload"].setEnabled(col is not None and col.path is not None)
        self.buttons["save"].setEnabled(self.model.is_dirty())
        self.buttons["undo"].setEnabled(self.model.can_undo())
        self.buttons["redo"].setEnabled(self.model.can_redo())
        self.buttons["copy"].setEnabled(len(self.model.columns) >= 2)
        self.buttons["diff"].setEnabled(has)
        self.search.setEnabled(has)

    def eventFilter(self, obj: QtCore.QObject, ev: QtCore.QEvent) -> bool:
        if obj is self.tree.header() and ev.type() == QtCore.QEvent.MouseButtonPress:
            self._user_sized = True                      # 見出しを掴んだ = 幅を自分で決めた。以後は等分に戻さない
        elif obj is self.status and ev.type() == QtCore.QEvent.Resize:
            self._apply_counts()
        elif obj is self.tree.viewport() and ev.type() == QtCore.QEvent.Resize and not self._user_sized:
            if not self._fit_pending:                    # 見出しの幅が決まってから(この通知の後)等分し直す
                self._fit_pending = True
                QtCore.QTimer.singleShot(0, self._fit_columns)
        return super().eventFilter(obj, ev)

    def _fit_columns(self) -> None:
        """キーの列は中身の幅(全体の 4 割まで)、印の列は細く、束の列は残りを等分。"""
        self._fit_pending = False
        n = len(self.model.columns)
        if not n:
            return
        hdr = self.tree.header()
        total = max(self.tree.viewport().width(), 200)
        fm = self.tree.fontMetrics()
        key_w = min(max(self.tree.sizeHintForColumn(0), fm.horizontalAdvance(self.tr_("Key")) + 16) + 8, int(total * 0.4))
        mark_w = fm.horizontalAdvance(MARK_DIFFER + MARK_PARTIAL + MARK_USED) + 10
        hdr.resizeSection(0, key_w)
        hdr.resizeSection(1, mark_w)
        each = max(40, (total - key_w - mark_w) // n)
        hdr.setStretchLastSection(False)                 # 入れ直すと、最後の列が残りの幅に合わせ直される
        for i in range(n):
            hdr.resizeSection(ParamsTreeModel.FIXED + i, each)
        hdr.setStretchLastSection(True)

    # ---- 選択 ----
    def current_cell(self) -> tuple[int, str] | None:
        """選んでいるセル (列の番号, キー)。束の列の葉でなければ None。"""
        idx = self.tree.currentIndex()
        if not idx.isValid():
            return None
        n = idx.internalPointer()
        ci = idx.column() - ParamsTreeModel.FIXED
        if n is None or n.row is None or not 0 <= ci < len(self.model.columns):
            return None
        return ci, n.key

    def current_column(self) -> int | None:
        """選んでいる列(束が 1 つならそれ)。"""
        idx = self.tree.currentIndex()
        ci = idx.column() - ParamsTreeModel.FIXED if idx.isValid() else -1
        if 0 <= ci < len(self.model.columns):
            return ci
        return 0 if len(self.model.columns) == 1 else None

    def index_of(self, col: int, key: str) -> QtCore.QModelIndex:
        """(列の番号, キー) の索引(絞り込みで見えていなければ無効な索引)。"""
        def walk(parent: QtCore.QModelIndex) -> QtCore.QModelIndex:
            for i in range(self.tmodel.rowCount(parent)):
                idx = self.tmodel.index(i, 0, parent)
                n = idx.internalPointer()
                if n.row is not None and n.key == key:
                    return self.tmodel.index(i, ParamsTreeModel.FIXED + col, parent)
                if n.children and (key.startswith(n.key + ".")):
                    hit = walk(idx)
                    if hit.isValid():
                        return hit
            return QtCore.QModelIndex()

        return walk(QtCore.QModelIndex())

    def select_cell(self, col: int, key: str) -> bool:
        """セルを選ぶ。見えていなければ False。"""
        idx = self.index_of(col, key)
        if not idx.isValid():
            return False
        self.tree.setCurrentIndex(idx)
        return True

    # ---- 開く・足す・外す ----
    def add_paths(self, paths: Sequence[str]) -> list[M.Outcome]:
        """ファイルを列として足す。読めなかった物は理由を状態の行に出す(読めた物は足す)。"""
        outs = [self.model.add_file(p) for p in paths]
        self.refresh()
        bad = [o for o in outs if not o.ok]
        if bad:
            self.show_message(" | ".join(o.text(self.tr_) for o in bad), "error")
        elif outs:
            self.show_message("", "info")
        return outs

    def open_files(self) -> None:
        """今の列を置き換えて開く(未保存があれば聞く)。"""
        paths = self.pick_open()
        if not paths or not self.confirm_discard(verb="open"):
            return
        while self.model.columns:
            self.model.remove_column(0)
        self.add_paths(paths)

    def add_files(self) -> None:
        """今の列の横に足す。"""
        paths = self.pick_open()
        if paths:
            self.add_paths(paths)

    def open_example(self) -> None:
        """例の 2 つの束を開く(ファイルは作らない)。"""
        for name, data in M.example_bundles():
            self.model.add_bundle(data, name)
        self.refresh()

    def remove_current(self) -> None:
        """選んでいる列を外す(未保存なら聞く)。"""
        ci = self.current_column()
        if ci is None:
            return
        if self.model.is_dirty(ci) and not self.confirm_discard([ci], verb="remove"):
            return
        self.model.remove_column(ci)
        self.refresh()

    def dragEnterEvent(self, ev: QtGui.QDragEnterEvent) -> None:
        if ev.mimeData().hasUrls() and any(os.path.splitext(u.toLocalFile())[1].lower() in M.FORMATS
                                           for u in ev.mimeData().urls()):
            ev.acceptProposedAction()

    def dropEvent(self, ev: QtGui.QDropEvent) -> None:
        paths = [u.toLocalFile() for u in ev.mimeData().urls() if u.isLocalFile()]
        if paths:
            ev.acceptProposedAction()
            self.add_paths(paths)

    # ---- 絞り込み ----
    def set_diff_only(self, on: bool) -> None:
        """違う行(と片方に無い行)だけにする。"""
        if self.buttons["diff"].isChecked() != bool(on):
            self.buttons["diff"].setChecked(bool(on))
            return
        self.tmodel.diff_only = bool(on)
        self.refresh()

    def set_query(self, text: str) -> None:
        """キーの検索。"""
        if self.search.text() != text:
            self.search.setText(text)
            return
        self.tmodel.query = text
        self.refresh()

    # ---- 直す ----
    def edit_cell(self, col: int, key: str, text: str) -> M.Outcome:
        """セルを文字から直す(窓の外から。試験・自動操作用)。断られたら理由が状態の行に出る。"""
        out = self._outcome(self.model.set_value(col, key, text))
        if out.ok:
            self._after_change(structure=bool(self.tmodel.diff_only))
        return out

    def undo(self) -> None:
        out = self.model.undo()
        if out.ok:
            self.show_message(self.tr_("undone: %s") % out.text(self.tr_), "info")
            self.refresh()
        else:
            self._outcome(out)

    def redo(self) -> None:
        out = self.model.redo()
        if out.ok:
            self.show_message(self.tr_("redone: %s") % out.text(self.tr_), "info")
            self.refresh()
        else:
            self._outcome(out)

    def copy_cell(self, key: str, src: int, dst: int) -> M.Outcome:
        """1 つの値を列から列へ写す。"""
        out = self._outcome(self.model.copy_value(key, src, dst))
        if out.ok:
            self.refresh()
        return out

    def copy_column(self, src: int, dst: int) -> M.Outcome:
        """違う値を全部、列から列へ写す。"""
        out = self.model.copy_column(src, dst)
        if out.ok:
            self.show_message(self.tr_("copied %d value(s) to %s") % (out.count, self.model.columns[dst].name), "info")
            self.refresh()
        else:
            self._outcome(out)
        return out

    def _copy_actions(self, menu: QtWidgets.QMenu) -> None:
        tr = self.tr_
        cur = self.current_cell()
        cols = self.model.columns
        if cur is not None and self.model.value(cur[0], cur[1]) is not None:
            src, key = cur
            for i, c in enumerate(cols):
                if i != src:
                    a = menu.addAction(tr("Copy %s to %s") % (key, c.name))
                    a.setEnabled(c.writable)
                    a.triggered.connect(lambda _=False, i=i, key=key, src=src: self.copy_cell(key, src, i))
            menu.addSeparator()
        src_col = self.current_column()
        if src_col is not None:
            for i, c in enumerate(cols):
                if i != src_col:
                    a = menu.addAction(tr("Copy every differing value from %s to %s") % (cols[src_col].name, c.name))
                    a.setEnabled(c.writable)
                    a.triggered.connect(lambda _=False, i=i, s=src_col: self.copy_column(s, i))
        if menu.isEmpty():
            a = menu.addAction(tr("Select a value first"))
            a.setEnabled(False)

    def _fill_copy_menu(self) -> None:
        self.copy_menu.clear()
        self._copy_actions(self.copy_menu)

    def _context_menu(self, pos: QtCore.QPoint) -> None:
        idx = self.tree.indexAt(pos)
        if idx.isValid():
            self.tree.setCurrentIndex(idx)
        menu = QtWidgets.QMenu(self.tree)
        self._copy_actions(menu)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # ---- 書く ----
    def save_column(self, i: int) -> bool:
        """列を書く。失われる物・外での変更があれば聞いてから進む。TOML とファイルの無い束は「名前を付けて保存」へ。"""
        col = self.model.columns[i]
        if col.path is None or not col.writable:
            return self.save_column_as(i)
        accept = force = False
        for _ in range(4):
            out = self.model.save(i, accept_losses=accept, force=force)
            if out.ok or not out.needs_confirm:
                break
            if out.code in ("save.external", "save.gone"):
                choice = self.ask_overwrite(col.name, out.text(self.tr_))
                if choice == "reload":
                    self.reload_column(i)
                    return False
                if choice != "overwrite":
                    self.show_message(self.tr_("not saved: %s") % col.name, "warn")
                    return False
                force = True
            else:
                if not self.ask_losses(col.name, out.note_texts(self.tr_)):
                    self.show_message(self.tr_("not saved: %s") % col.name, "warn")
                    return False
                accept = True
        self._outcome(out)
        self.refresh()
        return out.ok

    def save_column_as(self, i: int) -> bool:
        """列を別のファイルへ書く(形式は拡張子)。"""
        col = self.model.columns[i]
        path = self.pick_save(i)
        if not path:
            return False
        out = self.model.save_as(i, path)
        if not out.ok and out.needs_confirm:
            if not self.ask_losses(col.name, out.note_texts(self.tr_)):
                self.show_message(self.tr_("not saved: %s") % col.name, "warn")
                return False
            out = self.model.save_as(i, path, accept_losses=True)
        self._outcome(out)
        self.refresh()
        return out.ok

    def save_all(self) -> bool:
        """未保存の列を全部書く。1 つでも書けなければ False。"""
        ok = True
        for i in range(len(self.model.columns)):
            if self.model.is_dirty(i):
                ok = self.save_column(i) and ok
        return ok

    def save_current_as(self) -> None:
        ci = self.current_column()
        if ci is not None:
            self.save_column_as(ci)

    def reload_column(self, i: int) -> bool:
        out = self._outcome(self.model.reload(i))
        self.refresh()
        return out.ok

    def reload_current(self) -> None:
        ci = self.current_column()
        if ci is None:
            return
        if self.model.is_dirty(ci) and not self.confirm_discard([ci], verb="reload"):
            return
        self.reload_column(ci)

    def confirm_discard(self, cols: Sequence[int] | None = None, verb: str = "close") -> bool:
        """未保存の変更を手放してよいか(保存して<動詞> / 保存せずに<動詞> / キャンセル)。進んでよければ True。

        ``verb`` = close / open / remove(:data:`UNSAVED_VERBS`)、reload(保存しても意味が無いので
        [読み直す][キャンセル] の 2 択)。差し口 ``ask_unsaved`` を差し替えた時は、その答え(save / discard / cancel)を使う。"""
        idxs = [i for i in (cols if cols is not None else range(len(self.model.columns))) if self.model.is_dirty(i)]
        if not idxs:
            return True
        names = [self.model.columns[i].name for i in idxs]
        hook = self.ask_unsaved
        choice = self._ask_unsaved_box(names, verb) if hook == self._ask_unsaved_box else hook(names)
        if choice == "save":
            return all([self.save_column(i) for i in idxs])
        return choice == "discard"

    # ---- 外での変更 ----
    def check_external(self) -> list[tuple[int, str]]:
        """外で変わったファイルを調べ、あれば状態の行に出す。"""
        found = self.model.check_external()
        if found and found != self._last_external:
            tr = self.tr_
            msgs = [tr(M.MESSAGES["external.changed" if state == "changed" else "external.missing"])
                    % (self.model.columns[i].name,) for i, state in found]
            self.show_message("; ".join(msgs) + " — " + tr("Reload reads it again"), "warn")
        self._last_external = found
        return found

    # ---- 実行との連動 ----
    def mark_used(self, reports: Any, column: int | None = None) -> M.Outcome:
        """直前の実行が読んだキーに印(▸)を付ける。``reports`` は ``ParamReport`` かその並び、またはキーの並び。"""
        out = self._outcome(self.model.set_used(reports, column))
        self._after_change(structure=False)
        return out

    # ---- 聞く所(確認の窓は 1 つの形: 設計書 P09) ----
    def set_confirm(self, fn: Callable[..., Any] | None) -> None:
        """親(Studio)の ``confirm_action`` を受け取る。``None`` で自前の箱(同じ形)に戻す。

        新しい形 ``fn(parent, title, text, action, *, kind, buttons) -> 答え``: ``kind`` = unsaved / changed / run、
        ``buttons`` = [(役割の鍵, 画面の文)](文は tr 済み、並びは表示の順)。答えは役割の鍵・Qt の役割・真偽(2 択だけ)の
        どれでもよく、分からない答えはキャンセル。古い形 ``fn(parent, title, text, action) -> bool`` は 2 択(kind = run)
        だけを任せ、3 択は自前の箱で聞く(真偽では 3 つを言い分けられない)。"""
        self._confirm_fn = fn

    def confirm_function(self) -> Callable[..., Any] | None:
        """``set_confirm`` で受け取った関数(無ければ None)。"""
        return self._confirm_fn

    def _confirm(self, kind: str, title: str, text: str, buttons: Sequence[tuple[str, str]], action: str,
                 details: str = "") -> str:
        """確認を 1 回聞く。``buttons`` / ``title`` / ``action`` は英語の元の文(ここで tr を通す)。答え = 役割の鍵。"""
        tr = self.tr_
        shown = [(k, tr(s)) for k, s in buttons]
        fn = self._confirm_fn
        if fn is not None:
            if _accepts_kind(fn):
                body = text + ("\n\n" + details if details else "")
                return _answer_key(fn(self, tr(title), body, tr(action), kind=kind, buttons=list(shown)), shown)
            if len(shown) == 2:
                return _answer_key(fn(self, tr(title), text + ("\n\n" + details if details else ""), tr(action)),
                                   shown)
        box = _build_confirm_box(self, tr(title), text, shown, details)
        try:
            return _exec_confirm_box(box)
        finally:
            box.deleteLater()

    def _ask_unsaved_box(self, names: list[str], verb: str = "close") -> str:
        """未保存の束を手放す前に聞く: save / discard / cancel。"""
        tr = self.tr_
        if verb == "reload":
            text = tr("%s has unsaved changes; reloading reads the file again and drops them") % ", ".join(names)
            got = self._confirm("run", "Reload", text, (("run", "Reload"), ("cancel", "Cancel")), "Reload")
            return "discard" if got == "run" else "cancel"
        title, save, drop = UNSAVED_VERBS[verb]
        text = tr("%d bundle(s) have unsaved changes: %s") % (len(names), ", ".join(names))
        return self._confirm("unsaved", title, text, (("save", save), ("discard", drop), ("cancel", "Cancel")), title)

    def _ask_losses_box(self, name: str, lines: list[str]) -> bool:
        """保存で失われる物があれば聞く: それでも保存なら True。"""
        tr = self.tr_
        text = tr("Saving %s rewrites the whole file. These are not kept:") % name
        details = "\n".join("\u2022 " + s for s in lines)
        return self._confirm("run", "Save", text, (("run", "Save anyway"), ("cancel", "Cancel")), "Save anyway",
                             details) == "run"

    def _ask_overwrite_box(self, name: str, text: str) -> str:
        """読んだ後に外で変わった・消えたファイルへ保存する前に聞く: reload / overwrite / cancel。"""
        return self._confirm("changed", "Save", text, CHANGED_BUTTONS, "Overwrite anyway")

    def _start_dir(self) -> str:
        for c in self.model.columns:
            if c.path:
                return os.path.dirname(c.path)
        return str(self._settings().value(_SETTINGS_GROUP + "/last_dir", "") or "")

    def _pick_open_dialog(self) -> list[str]:
        tr = self.tr_
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, tr("Open parameter files"), self._start_dir(), "%s (%s)" % (tr("Parameters"), _FILTER))
        if paths:
            self._settings().setValue(_SETTINGS_GROUP + "/last_dir", os.path.dirname(paths[0]))
        return list(paths)

    def _pick_save_dialog(self, i: int) -> str:
        tr = self.tr_
        col = self.model.columns[i]
        start = col.path or os.path.join(self._start_dir(), col.name)
        if os.path.splitext(start)[1].lower() not in (".json", ".yaml", ".yml", ".xml"):
            start = os.path.splitext(start)[0] + ".json"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, tr("Save As"), start, "JSON (*.json);;YAML (*.yaml *.yml);;XML (*.xml)")
        return path


# --------------------------------------------------------------------------- #
# 窓
# --------------------------------------------------------------------------- #
class ParamsWindow(QtWidgets.QDialog):
    """モードレスの窓。Esc で閉じる・位置と大きさを覚える・未保存なら閉じる前に聞く・前に来たら外での変更を調べる。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None, tr: Callable[[str], str] | None = None,
                 settings: Callable[[], Any] | None = None, model: M.ParamsModel | None = None,
                 confirm: Callable[..., Any] | None = None) -> None:
        super().__init__(parent, Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinMaxButtonsHint)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._settings = settings or _default_settings
        self.panel = ParamsPanel(tr, self, model, self._settings)
        self.panel.set_confirm(confirm)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.panel)
        self.panel.titleChanged.connect(self.setWindowTitle)
        self.setWindowTitle(self.panel.title())
        self.setMinimumSize(320, 160)
        self._restore()

    # ---- 位置と大きさ・絞り込みの状態 ----
    def _restore(self) -> None:
        s = self._settings()
        raw = s.value(_SETTINGS_GROUP + "/geometry", None)
        try:
            x, y, w, h = [int(v) for v in json.loads(raw)] if raw else (None,) * 4
        except (TypeError, ValueError):
            x = None
        if x is None:
            self.resize(720, 420)
        else:
            w, h = max(320, w), max(160, h)
            screens = [sc.availableGeometry() for sc in QtGui.QGuiApplication.screens()]
            rect = QtCore.QRect(x, y, w, h)
            if screens and not any(g.intersects(rect.adjusted(40, 40, -40, -40)) for g in screens):
                g = screens[0]                                   # 画面の外なら戻す
                x, y = g.x() + 40, g.y() + 40
                w, h = min(w, g.width()), min(h, g.height())
            self.setGeometry(x, y, w, h)
        if str(s.value(_SETTINGS_GROUP + "/diff_only", "false")).lower() in ("true", "1"):
            self.panel.set_diff_only(True)

    def save_state(self) -> None:
        """位置・大きさ・絞り込み・開いていたファイルを設定に書く。"""
        s = self._settings()
        g = self.geometry()
        s.setValue(_SETTINGS_GROUP + "/geometry", json.dumps([g.x(), g.y(), g.width(), g.height()]))
        s.setValue(_SETTINGS_GROUP + "/diff_only", "true" if self.panel.tmodel.diff_only else "false")
        s.setValue(_SETTINGS_GROUP + "/files", json.dumps([c.path for c in self.panel.model.columns if c.path]))
        s.sync()

    def restore_session(self) -> list[M.Outcome]:
        """前に閉じた時に開いていたファイルをもう一度開く(今は無いファイルは理由を出して飛ばす)。"""
        raw = self._settings().value(_SETTINGS_GROUP + "/files", None)
        try:
            paths = [p for p in json.loads(raw) if isinstance(p, str)] if raw else []
        except (TypeError, ValueError):
            paths = []
        return self.panel.add_paths(paths) if paths else []

    def keyPressEvent(self, ev: QtGui.QKeyEvent) -> None:
        if ev.key() == Qt.Key_Escape:
            if self.panel.search.text():                 # 1 回目の Esc は検索を消す、2 回目で閉じる
                self.panel.search.clear()
                return
            self.reject()
            return
        if ev.key() in (Qt.Key_Return, Qt.Key_Enter):
            return                                       # QDialog の既定(Enter で閉じる)を止める
        super().keyPressEvent(ev)

    def changeEvent(self, ev: QtCore.QEvent) -> None:
        super().changeEvent(ev)
        if ev.type() == QtCore.QEvent.ActivationChange and self.isActiveWindow():
            self.panel.check_external()

    def hideEvent(self, ev: QtGui.QHideEvent) -> None:
        self.save_state()
        super().hideEvent(ev)

    def reject(self) -> None:
        """閉じる(Esc・窓の×・``close()`` は全部ここを通る)。未保存なら聞き、やめるなら開いたまま。"""
        if not self.panel.confirm_discard():
            return
        for i in range(len(self.panel.model.columns)):
            self.panel.model.revert(i)                   # 「捨てる」を選んだ変更を残さない(次に出した時は保存済みの値)
        self.panel.refresh()
        self.save_state()
        super().reject()


def show_params_window(parent: QtWidgets.QWidget | None = None, paths: Sequence[str] = (),
                       tr: Callable[[str], str] | None = None, settings: Callable[[], Any] | None = None,
                       confirm: Callable[..., Any] | None = None) -> ParamsWindow:
    """Studio から呼ぶ入口。同じ親の窓が既にあれば 2 枚目を作らず、``paths`` を列に足して前に出す。

    ``confirm`` = Studio の ``confirm_action``(確認の窓を Studio と同じ形にする。:meth:`ParamsPanel.set_confirm`)。"""
    win = getattr(parent, "_params_window", None) if parent is not None else None
    if not isinstance(win, ParamsWindow):
        win = ParamsWindow(parent, tr, settings, confirm=confirm)
        if parent is not None:
            parent._params_window = win             # type: ignore[attr-defined]
    elif confirm is not None:
        win.panel.set_confirm(confirm)
    if paths:
        win.panel.add_paths(list(paths))
    win.show()
    win.raise_()
    win.activateWindow()
    return win


def main(argv: Sequence[str] | None = None) -> int:
    """``python -m studio_params_qt [--lang ja] <ファイル…>``。ファイルを渡さなければ前に開いていた物を戻す。"""
    args = list(sys.argv[1:] if argv is None else argv)
    lang = None
    if "--lang" in args:
        i = args.index("--lang")
        if i + 1 >= len(args):
            print("--lang needs one of: " + " / ".join(M.LANGS), file=sys.stderr)
            return 2
        lang = args[i + 1]
        del args[i:i + 2]
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    if lang is None:
        lang = str(_default_settings().value("lang", "en") or "en")
    if lang not in M.LANGS:
        lang = "en"
    win = ParamsWindow(None, M.make_tr(lang))
    if args:
        win.panel.add_paths(args)
    else:
        win.restore_session()
    win.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
