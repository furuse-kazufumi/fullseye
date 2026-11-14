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


#: 状態の色の予備(studio_theme が無い時)。琥珀 = 注意・違う、赤 = 誤り。押せる物と枠には使わない(設計書 P14-2)。
_STATE_RGB = {"warn": (232, 163, 61), "err": (217, 83, 79)}


def _theme_colour(role: str) -> QtGui.QColor | None:
    """studio_theme の役割の色。import できない木・その役割が無い時は None。"""
    try:
        import studio_theme  # noqa: PLC0415  (見た目の枝の役割の表。無い木でも窓は動く)
        c = QtGui.QColor(studio_theme.colour(role))
        if c.isValid():
            return c
    except (ImportError, AttributeError, KeyError, TypeError, ValueError):
        pass
    return None


def _state_colour(role: str) -> QtGui.QColor:
    """状態の色(``"warn"`` / ``"err"``)。studio_theme が import できればその役割の色、できなければ予備の色。"""
    c = _theme_colour(role)
    return c if c is not None else QtGui.QColor(*_STATE_RGB[role])


def _mix(a: QtGui.QColor, b: QtGui.QColor, t: float) -> QtGui.QColor:
    return QtGui.QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                        round(a.blue() + (b.blue() - a.blue()) * t))


# --------------------------------------------------------------------------- #
# アイコン(資産ファイルなし。パレットの文字の色で線を引く)
# --------------------------------------------------------------------------- #
def _draw_pixmap(name: str, color: QtGui.QColor, px: int = _ICON_PX) -> QtGui.QPixmap:
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
    return pm


def _draw_icon(name: str, color: QtGui.QColor, px: int = _ICON_PX, off: QtGui.QColor | None = None) -> QtGui.QIcon:
    """絵 1 つの QIcon。``off`` を渡すと、押せない時の絵をその色で持つ(設計書 P04-4: 無効は絵を off の色)。"""
    ic = QtGui.QIcon(_draw_pixmap(name, color, px))
    if off is not None:
        ic.addPixmap(_draw_pixmap(name, off, px), QtGui.QIcon.Disabled)
    return ic


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


class _StripButton(QtWidgets.QToolButton):
    """列の 1 つのボタン(QAction を押す)。読み上げの名前は QAction の名前に追従する。"""

    def __init__(self, action: QtGui.QAction, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setDefaultAction(action)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setIconSize(QtCore.QSize(_ICON_PX, _ICON_PX))
        self.setFixedSize(BUTTON_PX, BUTTON_PX)
        self.setAutoRaise(True)
        # theme の QSS は QToolButton に左右 8 px の余白を置き、絵だけのボタンはこの宣言で余白を詰める(無いと絵が 4〜6 px に潰れる)。
        self.setProperty("iconOnly", True)
        self.setProperty("keepSize", True)             # 大きさは固定(theme の側で変えない)
        if action.menu() is not None:                  # メニューは QAction の menu() から出る(setMenu は既定の QAction を外す)
            self.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        action.changed.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        a = self.defaultAction()
        if a is not None:
            self.setAccessibleName(a.text().replace("&&", "&"))


class _ToolStrip(QtWidgets.QWidget):
    """道具の列の既定の部品: QAction の並びを、アイコンだけのボタンの横の 1 行か縦の 1 列にする。

    外の部品(収まらない時に送る ScrollStrip・折り返す列など)へ差し替える時の約束(:meth:`ParamsPanel.set_strip_widget`):

    * ``set_actions(items)`` — ``items`` = ``QAction`` か ``None``(群の区切り)の並び。同じ QAction を使う(複製しない。
      有効・押した状態・ツールヒント・キーは QAction が正本)。
    * ``set_orientation(o)`` — ``Qt.Horizontal`` = 横の 1 行、``Qt.Vertical`` = 縦の 1 列。
    * ``button_for(action)``(任意)— その QAction を押すボタン(試験と ``ParamsPanel.buttons`` の元)。

    この既定の部品は収まらない時の扱いを持たない(全部のボタンが見える長さを最小の大きさにする = 隠さない)。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._lay = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight, self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(GAP_PX)
        self._buttons: dict[int, _StripButton] = {}
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

    def set_actions(self, items: Sequence[QtGui.QAction | None]) -> None:
        while self._lay.count():
            w = self._lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._buttons = {}
        for a in items:
            if a is None:
                self._lay.addSpacing(GAP_PX)            # 群の間 = 4 + 4 = 8 px
                continue
            b = _StripButton(a, self)
            self._lay.addWidget(b)
            self._buttons[id(a)] = b

    def set_orientation(self, o: Qt.Orientation) -> None:
        self._lay.setDirection(QtWidgets.QBoxLayout.TopToBottom if o == Qt.Vertical else QtWidgets.QBoxLayout.LeftToRight)

    def orientation(self) -> Qt.Orientation:
        return Qt.Vertical if self._lay.direction() == QtWidgets.QBoxLayout.TopToBottom else Qt.Horizontal

    def button_for(self, action: QtGui.QAction) -> QtWidgets.QToolButton | None:
        return self._buttons.get(id(action))


#: 道具の列の向き(外から set_strip_side で選ぶ。自動で選ぶ規則は studio_panels の strip_side が持つ)。
STRIP_SIDES = ("top", "left")
#: 列の部品の objectName(全部のパネルで同じ名前で数える)。
STRIP_NAME = "panelStrip"


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
        #: 直前の setData で断った時の文(理由 — 例: 今の値)。通った・触っただけなら None。
        self.last_refusal: str | None = None
        #: その文を作る関数(tr → 文)。言語を切り替えた時に知らせの行を作り直すため。
        self.last_refusal_source: Callable[[Callable[[str], str]], str] | None = None
        self.rebuild()

    # ---- 見た目の材料(パレットから) ----
    def set_palette(self, pal: QtGui.QPalette, font: QtGui.QFont) -> None:
        base, text = pal.color(QtGui.QPalette.Base), pal.color(QtGui.QPalette.Text)
        self._diff_brush = QtGui.QBrush(_mix(base, _state_colour("warn"), 0.30))
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
        self.last_refusal = None
        self.last_refusal_source = None
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
            # 断る時は理由に例(この欄の今の値)を添える(設計書 P08-5「赤枠 + 理由 + 例」)。
            def refusal(tr: Callable[[str], str], out: M.Outcome = out, v: Any = v) -> str:
                return out.text(tr) + " — " + tr("example: %s") % M.format_value(v)

            self.last_refusal_source = refusal
            self.last_refusal = refusal(self.tr)
            self.rejected.emit(self.last_refusal)
            return False
        self.sync()
        self.edited.emit(out)
        return True


class _Tree(QtWidgets.QTreeView):
    """木つきの表。断った欄(property ``invalid`` = 真)は閉じない(設計書 P08-5「打った文字を消さずに欄に残す」)。

    確定を試みる道は 3 つある: 確定キー(Enter / Tab)、欄からフォーカスが外れた時(Qt の委譲の既定)、他のセルを選んだ時
    (表の currentChanged)。どの道も最後にここを通るので、ここで止める。閉じるのは Esc(取り消し)と、直して確定できた時。"""

    _ATTEMPTS = (QtWidgets.QAbstractItemView.DoubleClicked, QtWidgets.QAbstractItemView.EditKeyPressed,
                 QtWidgets.QAbstractItemView.AnyKeyPressed, QtWidgets.QAbstractItemView.AllEditTriggers)

    def closeEditor(self, editor: QtWidgets.QWidget, hint: QtWidgets.QAbstractItemDelegate.EndEditHint) -> None:
        if editor is not None and bool(editor.property("invalid")):
            if hint != QtWidgets.QAbstractItemDelegate.RevertModelCache:
                return
            editor.setProperty("invalid", False)        # 閉じた欄(消されるまで木に残る)を「断ったまま」に数えない
        super().closeEditor(editor, hint)

    def rejected_editors(self) -> list[QtWidgets.QLineEdit]:
        """断ったまま開いている欄(畳んだ節の中で見えない物も含む)。"""
        return [w for w in self.viewport().findChildren(QtWidgets.QLineEdit) if bool(w.property("invalid"))]

    def cancel_rejected(self) -> int:
        """断ったまま開いている欄を取り消して閉じる(値はそのまま)。閉じた数。"""
        eds = self.rejected_editors()
        for ed in eds:
            self.closeEditor(ed, QtWidgets.QAbstractItemDelegate.RevertModelCache)
        return len(eds)

    def _back_to_rejected(self, index: QtCore.QModelIndex) -> bool:
        """``index`` を編集しようとした時に、別のセルの断った欄が残っていれば、そこへフォーカスを戻して理由を出す(真)。
        見えない所(畳んだ節の中)に残った欄は取り消して、偽を返す(進んでよい)。"""
        held = self.rejected_editors()
        shown = [e for e in held if e.isVisible()]
        if not shown:
            if held:
                self.cancel_rejected()
            return False
        at = getattr(shown[0], "_fs_index", None)
        if at is not None and (at.row(), at.column(), at.parent()) == (index.row(), index.column(), index.parent()):
            return False
        shown[0].setFocus()
        QtWidgets.QToolTip.showText(shown[0].mapToGlobal(QtCore.QPoint(0, shown[0].height())), shown[0].toolTip(), shown[0])
        return True

    def edit(self, index: QtCore.QModelIndex,                                    # type: ignore[override]
             trigger: QtWidgets.QAbstractItemView.EditTrigger = QtWidgets.QAbstractItemView.AllEditTriggers,
             event: QtCore.QEvent | None = None) -> bool:
        """他のセルを編集しようとした時に断った欄が残っていれば、そこへ戻す(黙って始まらないままにしない)。"""
        if trigger in self._ATTEMPTS and self._back_to_rejected(index):
            return True
        return super().edit(index, trigger, event)

    def mouseDoubleClickEvent(self, ev: QtGui.QMouseEvent) -> None:
        # QTreeView は編集中の状態ではダブルクリックを捨てる(edit まで来ない)ので、ここでも戻す。
        if self._back_to_rejected(self.indexAt(ev.position().toPoint())):
            return
        super().mouseDoubleClickEvent(ev)


class _Delegate(QtWidgets.QStyledItemDelegate):
    """行の高さ = 文字 + 4 px。編集は枠なしの文字の欄(数もスピンでなく文字 + 検査)。

    確定(Enter / Tab・フォーカスが外れた時・他のセルを選んだ時)は ``setModelData`` の 1 か所。断られたら欄を閉じない:
    打った文字はそのまま、property ``invalid`` = 真で赤枠、ツールヒントに理由 + 例(設計書 P08-5。閉じないのは
    :class:`_Tree`)。打ち直すと印は消える。Esc は取り消し。"""

    _COMMIT_KEYS = {Qt.Key_Return: QtWidgets.QAbstractItemDelegate.NoHint,
                    Qt.Key_Enter: QtWidgets.QAbstractItemDelegate.NoHint,
                    Qt.Key_Tab: QtWidgets.QAbstractItemDelegate.EditNextItem,
                    Qt.Key_Backtab: QtWidgets.QAbstractItemDelegate.EditPreviousItem}

    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
        sz = super().sizeHint(option, index)
        return QtCore.QSize(sz.width(), option.fontMetrics.height() + ROW_EXTRA_PX)

    def createEditor(self, parent: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex) -> QtWidgets.QWidget:
        ed = QtWidgets.QLineEdit(parent)
        ed.setFrame(False)
        ed.setContentsMargins(0, 0, 0, 0)
        ed.setTextMargins(0, 0, 0, 0)
        ed.setProperty("invalid", False)
        ed._fs_index = QtCore.QPersistentModelIndex(index)  # type: ignore[attr-defined]
        ed.textChanged.connect(lambda _t, e=ed: self._mark(e, ""))
        return ed

    @staticmethod
    def _mark(editor: QtWidgets.QLineEdit, reason: str) -> None:
        """欄に断った印を付ける(``reason`` が空なら外す)。"""
        bad = bool(reason)
        if bool(editor.property("invalid")) == bad and editor.toolTip() == reason:
            return
        editor.setProperty("invalid", bad)
        if bad:
            c = _state_colour("err")
            editor.setStyleSheet("QLineEdit { border: 1px solid rgb(%d, %d, %d); }" % (c.red(), c.green(), c.blue()))
        else:
            editor.setStyleSheet("")
        editor.setToolTip(reason)

    def eventFilter(self, obj: QtCore.QObject, ev: QtCore.QEvent) -> bool:
        if (isinstance(obj, QtWidgets.QLineEdit) and ev.type() == QtCore.QEvent.KeyPress
                and ev.key() in self._COMMIT_KEYS and ev.modifiers() in (Qt.NoModifier, Qt.KeypadModifier, Qt.ShiftModifier)):
            idx = getattr(obj, "_fs_index", None)
            model = idx.model() if idx is not None and idx.isValid() else None
            if isinstance(model, ParamsTreeModel):
                self.setModelData(obj, model, model.index(idx.row(), idx.column(), idx.parent()))
                if bool(obj.property("invalid")):
                    QtWidgets.QToolTip.showText(obj.mapToGlobal(QtCore.QPoint(0, obj.height())), obj.toolTip(), obj)
                    return True                                  # 欄を閉じない(打った文字を残す)
                self.closeEditor.emit(obj, self._COMMIT_KEYS[ev.key()])
                return True
        return super().eventFilter(obj, ev)                      # フォーカスが外れた時は Qt の既定が setModelData を呼ぶ

    def setEditorData(self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex) -> None:
        """欄に表の値を入れる。表の描き直しでもう一度呼ばれた時、利用者が文字を変えた欄(打っている途中・断って残した
        文字)は上書きしない。"""
        text = index.data(Qt.EditRole) or ""
        loaded = getattr(editor, "_fs_loaded", None)
        if loaded is not None and editor.text() != loaded:  # type: ignore[attr-defined]
            return
        editor._fs_loaded = text                            # type: ignore[attr-defined]
        editor.setText(text)                                # type: ignore[attr-defined]
        editor.selectAll()                                  # type: ignore[attr-defined]

    def setModelData(self, editor: QtWidgets.QWidget, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex) -> None:
        """欄の文字で確定を試みる。断られたら欄に印(赤枠 + 理由)を付ける = その欄は閉じられない。"""
        model.setData(index, editor.text(), Qt.EditRole)    # type: ignore[attr-defined]
        refusal = model.last_refusal if isinstance(model, ParamsTreeModel) else None
        if refusal is not None and isinstance(editor, QtWidgets.QLineEdit):
            self._mark(editor, refusal)


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
    _theme_read = False                                  # 見える時に一度、theme の色を読んだか
    _theme_pending = False                               # 様式 / パレットが変わった後の読み直しを予約したか

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
        # 本体 = [縦の時の道具の列] + [検索の帯 / 表]。横の時は道具の列が検索の帯の左に入る(_place_strip)。
        self._body = QtWidgets.QHBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(2)
        self._column = QtWidgets.QVBoxLayout()
        self._column.setContentsMargins(0, 0, 0, 0)
        self._column.setSpacing(2)
        self.bar = QtWidgets.QWidget(self)
        self._bar_lay = QtWidgets.QGridLayout(self.bar)
        self._bar_lay.setContentsMargins(0, 0, 0, 0)
        self._bar_lay.setHorizontalSpacing(GAP_PX)
        self._bar_lay.setVerticalSpacing(2)
        color, off = self._icon_colours()
        #: 道具(1 機能 1 QAction)。鍵 → QAction。列の部品・キー・パネルの ≡ はどれもこの QAction を使う。
        self.tool_actions: dict[str, QtGui.QAction] = {}
        self._action_texts: dict[str, tuple[str, str, str]] = {}
        self._action_icons: dict[str, str] = {}
        self._message_src: Callable[[Callable[[str], str]], str] | None = None
        self._message_text = ""
        items: list[QtGui.QAction | None] = []

        def action(key: str, icon: str, name: str, what: str, slot: Callable[..., Any] | None, shortcut: str = "",
                   checkable: bool = False) -> QtGui.QAction:
            a = QtGui.QAction(self)
            a.setObjectName("params_" + key)
            a.setIcon(_draw_icon(icon, color, off=off))
            a.setCheckable(checkable)
            if shortcut:
                a.setShortcut(QtGui.QKeySequence(shortcut))
                a.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            if slot is not None:
                if checkable:
                    a.toggled.connect(slot)
                else:
                    a.triggered.connect(lambda _checked=False, f=slot: f())
            self.addAction(a)
            self.tool_actions[key] = a
            self._action_texts[key] = (name, what, shortcut)
            self._action_icons[key] = icon
            items.append(a)
            return a

        action("open", "open", "Open", "open parameter files in place of the ones shown", self.open_files, "Ctrl+O")
        action("add", "add", "Add column", "add parameter files beside the ones shown", self.add_files, "Ctrl+Shift+O")
        action("remove", "remove", "Remove column", "take the selected bundle out of the table (the file stays)",
               self.remove_current)
        items.append(None)
        action("save", "save", "Save", "write every changed bundle back to its file", self.save_all, "Ctrl+S")
        action("saveas", "saveas", "Save As", "write the selected bundle to a new JSON, YAML or XML file",
               self.save_current_as, "Ctrl+Shift+S")
        action("reload", "reload", "Reload", "read the selected bundle again from its file", self.reload_current)
        items.append(None)
        action("undo", "undo", "Undo", "take back the last change", self.undo, "Ctrl+Z")
        redo = action("redo", "redo", "Redo", "apply the change again", self.redo, "Ctrl+Y")
        redo.setShortcuts([QtGui.QKeySequence("Ctrl+Y"), QtGui.QKeySequence("Ctrl+Shift+Z")])  # 表示は Ctrl+Y(P08-2)
        cp = action("copy", "copy", "Copy to column", "copy the selected value, or every differing value, to another bundle",
                    None)
        self.copy_menu = QtWidgets.QMenu(self)
        self.copy_menu.aboutToShow.connect(self._fill_copy_menu)
        cp.setMenu(self.copy_menu)
        items.append(None)
        # キーは付けない(D90: Ctrl+D は Studio で「複製」。付けるなら [キー] の登録簿で決める)。帯のトグルだけ。
        action("diff", "diff", "Differences only", "show only the rows where the bundles differ", self.set_diff_only,
               checkable=True)
        self._strip_items = items
        self._apply_action_texts()
        self._strip_side = "top"
        self.strip: QtWidgets.QWidget = _ToolStrip(self)
        self.strip.setObjectName(STRIP_NAME)
        self.strip.set_actions(self._strip_items)    # type: ignore[attr-defined]
        #: 鍵 → 今の列の部品のボタン(部品が button_for を持つ時。試験と古い呼び出しの口。状態は QAction が正本)。
        self.buttons: dict[str, QtWidgets.QAbstractButton] = {}
        self.search = QtWidgets.QLineEdit(self.bar)
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(BUTTON_PX)
        self._search_icon = self.search.addAction(_draw_icon("search", color, off=off),
                                                  QtWidgets.QLineEdit.LeadingPosition)
        self._apply_search_texts()
        self._search_below = False
        self._replace_pending = False
        self._fit_search()
        self.search.textChanged.connect(self.set_query)
        sc = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        sc.setContext(Qt.WidgetWithChildrenShortcut)
        sc.activated.connect(lambda: (self.search.setFocus(), self.search.selectAll()))
        self._column.addWidget(self.bar)

        self.stack = QtWidgets.QStackedWidget(self)
        # 空の状態: 何をする場所か 1 行、最初の一手 1 つ、例 1 つ。
        self.empty = QtWidgets.QWidget(self.stack)
        el = QtWidgets.QVBoxLayout(self.empty)
        el.setContentsMargins(6, 6, 6, 6)
        el.setSpacing(8)
        el.addStretch(1)
        self.empty_label = QtWidgets.QLabel(self.empty)
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignCenter)
        el.addWidget(self.empty_label)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(GAP_PX)
        row.addStretch(1)
        self.empty_open = QtWidgets.QPushButton(self.empty)
        self.empty_open.clicked.connect(self.open_files)
        self.empty_example = QtWidgets.QPushButton(self.empty)
        self.empty_example.clicked.connect(self.open_example)
        self._apply_empty_texts()
        row.addWidget(self.empty_open)
        row.addWidget(self.empty_example)
        row.addStretch(1)
        el.addLayout(row)
        el.addStretch(1)
        self.stack.addWidget(self.empty)
        # 絞り込みで 0 行: 一覧の場所に「該当なし: "語"」と次の一手(設計書 P07-3)。
        self.no_match = QtWidgets.QWidget(self.stack)
        #: 該当なしの頁に最後に出した状態: 検索の語(違う行が無い時は "")、まだ出していなければ None。
        self._no_match_word: str | None = None
        nl = QtWidgets.QVBoxLayout(self.no_match)
        nl.setContentsMargins(6, 6, 6, 6)
        nl.setSpacing(8)
        nl.addStretch(1)
        self.no_match_label = QtWidgets.QLabel(self.no_match)
        self.no_match_label.setTextFormat(Qt.PlainText)
        self.no_match_label.setWordWrap(True)
        self.no_match_label.setAlignment(Qt.AlignCenter)
        nl.addWidget(self.no_match_label)
        nrow = QtWidgets.QHBoxLayout()
        nrow.addStretch(1)
        self.no_match_button = QtWidgets.QPushButton(self.no_match)
        self.no_match_button.clicked.connect(self._no_match_step)
        nrow.addWidget(self.no_match_button)
        nrow.addStretch(1)
        nl.addLayout(nrow)
        nl.addStretch(1)
        self.stack.addWidget(self.no_match)

        self.tree = _Tree(self.stack)
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
        self._column.addWidget(self.stack, 1)
        self._body.addLayout(self._column, 1)
        lay.addLayout(self._body, 1)
        self._place_strip()

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

    # ---- 道具の列(1 つの部品。向きと部品は外から変えられる) ----
    def _apply_action_texts(self) -> None:
        """道具の名前とツールヒント(「名前 — 何をするか (キー)」)を今の言語で入れ直す。"""
        tr = self.tr_
        for key, (name, what, shortcut) in self._action_texts.items():
            a = self.tool_actions[key]
            a.setText(_label(tr(name)))
            keys = a.shortcut().toString(QtGui.QKeySequence.NativeText) if shortcut else ""
            a.setToolTip("%s — %s" % (tr(name), tr(what)) + (" (%s)" % keys if keys else ""))

    def _apply_search_texts(self) -> None:
        tr = self.tr_
        self.search.setPlaceholderText(tr("Search keys"))
        self.search.setToolTip(tr("Search keys") + " — " + tr("show only the keys that contain this text") + " (Ctrl+F)")
        self.search.setAccessibleName(tr("Search keys"))

    def _apply_empty_texts(self) -> None:
        tr = self.tr_
        self.empty_label.setText(tr(self.EMPTY_TEXT))
        self.empty_open.setText(_label(tr("Open files")))
        self.empty_example.setText(_label(tr("Open the example")))
        self.empty_example.setToolTip(tr("Two bundles of the same rig (day and night) to try comparing and copying"))

    def set_tr(self, tr: Callable[[str], str]) -> None:
        """言語を切り替える: 窓に出ている文を全部、その言語で作り直す(設計書 P15-2)。中身(列・絞り込み・未保存)は変えない。"""
        self.tr_ = tr
        self.tmodel.tr = tr
        self._apply_action_texts()
        self._apply_search_texts()
        self._fit_search()
        self._apply_empty_texts()
        self._apply_no_match_texts()
        self._place_strip()                              # 検索の欄の最小幅が変わると段が変わる
        self.tmodel.sync()                               # 見出し・セルのツールヒント
        self.refresh()                                   # 数え方・題・該当なし・列の幅
        self._render_message()

    def _icon_colours(self) -> tuple[QtGui.QColor, QtGui.QColor]:
        """道具の絵の色(押せる時, 押せない時)。押せない時 = theme の役割 off、無ければ文字の色を地へ寄せた色。"""
        pal = self.palette()
        on = pal.color(QtGui.QPalette.ButtonText)
        off = _theme_colour("off")
        return on, off if off is not None else _mix(on, pal.color(QtGui.QPalette.Window), 0.55)

    def apply_theme(self) -> None:
        """状態の色(違うセル・注意・誤り)とアイコンの色を、今の theme とパレットから読み直す(設計書 P14-2)。

        外から呼ばなくてよい: 初めて見える時と、様式・パレットが変わった時(親の窓の QSS の差し替え = theme の切り替え)に
        パネルが自分で呼ぶ。作った時点では親の QSS がまだ当たっておらず、その時の白い地で色を決めると暗い theme で読めない。"""
        color, off = self._icon_colours()
        for key, icon in self._action_icons.items():
            self.tool_actions[key].setIcon(_draw_icon(icon, color, off=off))
        self._search_icon.setIcon(_draw_icon("search", color, off=off))
        self.tmodel.set_palette(self.tree.palette(), self.tree.font())
        self.tmodel.sync()
        self._render_message()

    def showEvent(self, ev: QtGui.QShowEvent) -> None:
        super().showEvent(ev)
        if not self._theme_read:                         # 子の部品まで磨かれた後(親の QSS の色がパレットに入っている)
            self._theme_read = True
            self.apply_theme()

    def changeEvent(self, ev: QtCore.QEvent) -> None:
        super().changeEvent(ev)
        if (ev.type() in (QtCore.QEvent.StyleChange, QtCore.QEvent.PaletteChange) and self._theme_read
                and not self._theme_pending):
            self._theme_pending = True                   # 子の部品の磨き直しが済んでから(この通知の後)1 回だけ読み直す
            QtCore.QTimer.singleShot(0, self, self._theme_changed)  # self が消えたら呼ばない

    def _theme_changed(self) -> None:
        self._theme_pending = False
        self.apply_theme()

    def _sync_buttons(self) -> None:
        find = getattr(self.strip, "button_for", None)
        self.buttons = {}
        if callable(find):
            for key, a in self.tool_actions.items():
                b = find(a)
                if b is not None:
                    self.buttons[key] = b

    def strip_actions(self) -> list[QtGui.QAction | None]:
        """道具の列に並べる QAction(``None`` = 群の区切り)。外の部品・パネルの ≡ はこれを使う。"""
        return list(self._strip_items)

    def strip_widget(self) -> QtWidgets.QWidget:
        """今の道具の列の部品(objectName ``"panelStrip"``)。"""
        return self.strip

    def strip_side(self) -> str:
        """道具の列の向き: ``"top"``(表の上に横の 1 行)/ ``"left"``(表の左に縦の 1 列)。"""
        return self._strip_side

    def set_strip_side(self, side: str) -> str:
        """道具の列の向きを外から変える(自動で選ぶ規則は呼ぶ側 = studio_panels の strip_side)。知らない向きは ValueError。"""
        if side not in STRIP_SIDES:
            raise ValueError("strip side must be one of %s (got %r)" % (" / ".join(STRIP_SIDES), side))
        if side != self._strip_side:
            self._strip_side = side
            self._place_strip()
        return side

    def set_strip_widget(self, widget: QtWidgets.QWidget) -> None:
        """道具の列の部品を差し替える(収まらない時に送る型・折り返す型を外の部品に任せる口)。

        ``widget`` は QWidget で ``set_actions`` と ``set_orientation`` を持つ事(:class:`_ToolStrip` の約束)。満たさなければ
        TypeError(黙って受けない)。前の部品はパネルから外して隠す(親なし。捨てるか使い直すかは呼ぶ側)。"""
        if not isinstance(widget, QtWidgets.QWidget) or not all(
                callable(getattr(widget, name, None)) for name in ("set_actions", "set_orientation")):
            raise TypeError("a strip must be a QWidget with set_actions(items) and set_orientation(o): %r" % (widget,))
        old = self.strip
        if widget is old:
            return
        self._unplace_strip()
        old.hide()
        old.setParent(None)
        widget.setParent(self)
        widget.setObjectName(STRIP_NAME)
        widget.set_actions(self._strip_items)        # type: ignore[attr-defined]
        self.strip = widget
        self._place_strip()
        widget.show()

    def _unplace_strip(self) -> None:
        for w in (self.strip, self.search):
            self._bar_lay.removeWidget(w)
        self._body.removeWidget(self.strip)

    def _place_strip(self) -> None:
        """道具の列と検索の欄を、今の向きの場所へ置く。"""
        self._unplace_strip()
        if self._strip_side == "left":
            self.strip.set_orientation(Qt.Vertical)   # type: ignore[attr-defined]
            self._body.insertWidget(0, self.strip, 0, Qt.AlignTop)
            self._bar_lay.addWidget(self.search, 0, 0, 1, 2)
            self._search_below = False
        else:
            self.strip.set_orientation(Qt.Horizontal)  # type: ignore[attr-defined]
            self._bar_lay.addWidget(self.strip, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
            self._search_below = self._search_needs_own_row()
            if self._search_below:                       # 狭い窓: 検索の欄は次の段に全幅で(切らない。D112)
                self._bar_lay.addWidget(self.search, 1, 0, 1, 2)
            else:
                self._bar_lay.addWidget(self.search, 0, 1)
        self._bar_lay.setColumnStretch(0, 0)
        self._bar_lay.setColumnStretch(1, 1)
        self.strip.updateGeometry()
        self._sync_buttons()                            # 向きでボタンを作り直す部品もある

    def _fit_search(self) -> None:
        """検索の欄の最小幅 = 置いた文字の幅 + 前のアイコンと × の分(言語を変えたら測り直す)。"""
        fm = self.search.fontMetrics()
        self.search.setMinimumWidth(max(80, fm.horizontalAdvance(self.search.placeholderText()) + 2 * _ICON_PX + 4 * GAP_PX))

    def _search_needs_own_row(self) -> bool:
        """横の道具の列の隣に、検索の欄が最小幅で収まらないか。"""
        room = self.width() - 4                          # 枠の内側(左右 2 px)
        need = self.strip.sizeHint().width() + GAP_PX + self.search.minimumWidth()
        return room < need

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        super().resizeEvent(ev)
        # 配置を当てている途中で中身を組み替えると Qt が落ちるので、組み替えは通知の後に 1 回だけ。
        if self._strip_side == "top" and self._search_needs_own_row() != self._search_below and not self._replace_pending:
            self._replace_pending = True
            QtCore.QTimer.singleShot(0, self, self._replace_after_resize)  # self が消えたら呼ばない

    def _replace_after_resize(self) -> None:
        self._replace_pending = False
        if self._strip_side == "top" and self._search_needs_own_row() != self._search_below:
            self._place_strip()

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
            shown = len(self.model.rows(diff_only=self.tmodel.diff_only, query=self.tmodel.query))
            if shown != c["rows"]:                       # 絞っている時は n / N(語なし)
                parts.append("%d / %d" % (shown, c["rows"]))
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

    def show_message(self, text: str | Callable[[Callable[[str], str]], str], level: str = "info") -> None:
        """状態の 1 行の右側。``level`` = info / warn / error(形 + 語。色だけにしない)。

        ``text`` は文か、文を作る関数(tr → 文)。関数で渡した知らせは、言語を切り替えた時に作り直す。"""
        self._message_src = text if callable(text) else None
        self._message_text = "" if callable(text) else text
        self.message_level = level
        self._render_message()

    def _render_message(self) -> None:
        """知らせの行を今の言語と色で描き直す(文を作る関数で渡された知らせは作り直し、文はそのまま)。"""
        level = self.message_level
        text = self._message_src(self.tr_) if self._message_src is not None else self._message_text
        mark = {"info": "", "warn": "▲ ", "error": "✕ "}[level]
        self.message_label.set_full_text(mark + text if text else "")
        pal = self.message_label.palette()
        base = self.palette().color(QtGui.QPalette.WindowText)
        tone = {"info": base, "warn": _mix(base, _state_colour("warn"), 0.6),
                "error": _mix(base, _state_colour("err"), 0.7)}[level]
        pal.setColor(QtGui.QPalette.WindowText, tone)
        self.message_label.setPalette(pal)
        # 親の窓の QSS(QLabel { color })はパレットに勝つので、状態の色はラベル自身の QSS でも言う(info は theme の文字の色)。
        self.message_label.setStyleSheet(
            "" if level == "info" else "QLabel { color: rgb(%d, %d, %d); }" % (tone.red(), tone.green(), tone.blue()))

    def _outcome(self, out: M.Outcome) -> M.Outcome:
        if not out.ok:
            self.show_message(lambda tr: "; ".join([out.text(tr)] + out.note_texts(tr)) if out.code else "", "error")
        else:
            self.show_message(lambda tr: "; ".join(([out.text(tr)] if out.code else []) + out.note_texts(tr)),
                              "warn" if out.notes and not out.code else "info")
        return out

    def _on_rejected(self, text: str) -> None:
        self.show_message(self.tmodel.last_refusal_source or text, "error")
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
        self.stack.setCurrentWidget(self._current_page())
        if ncols != self.tmodel.columnCount() or not self._user_sized:
            self._fit_columns()
        self._update_status()

    def _current_page(self) -> QtWidgets.QWidget:
        """一覧の場所に出す頁: 何も開いていない = 空の案内 / 絞り込みで 0 行 = 該当なし / それ以外 = 表。"""
        if not self.model.columns:
            return self.empty
        if self.tmodel.rowCount() == 0 and (self.tmodel.query or self.tmodel.diff_only):
            self._no_match_word = self.tmodel.query
            self._apply_no_match_texts()
            return self.no_match
        return self.tree

    def _apply_no_match_texts(self) -> None:
        """該当なしの頁の文(検索の語があれば「該当なし: "語"」、無ければ違う行が無い事)。"""
        tr = self.tr_
        word = self._no_match_word
        if word is None:
            return
        if word:
            self.no_match_label.setText(tr('No match: "%s"') % word)
            self.no_match_button.setText(_label(tr("Clear the search")))
        else:
            self.no_match_label.setText(tr("The bundles do not differ"))
            self.no_match_button.setText(_label(tr("Show every row")))

    def _no_match_step(self) -> None:
        """該当なしの次の一手: 検索を消す(検索で 0 行)/ 全部の行を出す(違う行だけで 0 行)。"""
        if self.tmodel.query:
            self.search.clear()
        else:
            self.set_diff_only(False)

    def _after_change(self, structure: bool = True, deferred: bool = False) -> None:
        if structure:
            if deferred:
                QtCore.QTimer.singleShot(0, self, self.refresh)     # self が消えたら呼ばない
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
        a = self.tool_actions
        a["remove"].setEnabled(col is not None)
        a["saveas"].setEnabled(col is not None)
        a["reload"].setEnabled(col is not None and col.path is not None)
        a["save"].setEnabled(self.model.is_dirty())
        a["undo"].setEnabled(self.model.can_undo())
        a["redo"].setEnabled(self.model.can_redo())
        a["copy"].setEnabled(len(self.model.columns) >= 2)
        a["diff"].setEnabled(has)
        self.search.setEnabled(has)

    def eventFilter(self, obj: QtCore.QObject, ev: QtCore.QEvent) -> bool:
        if obj is self.tree.header() and ev.type() == QtCore.QEvent.MouseButtonPress:
            self._user_sized = True                      # 見出しを掴んだ = 幅を自分で決めた。以後は等分に戻さない
        elif obj is self.status and ev.type() == QtCore.QEvent.Resize:
            self._apply_counts()
        elif obj is self.tree.viewport() and ev.type() == QtCore.QEvent.Resize and not self._user_sized:
            if not self._fit_pending:                    # 見出しの幅が決まってから(この通知の後)等分し直す
                self._fit_pending = True
                QtCore.QTimer.singleShot(0, self, self._fit_columns)  # self が消えたら呼ばない
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
            self.show_message(lambda tr: " | ".join(o.text(tr) for o in bad), "error")
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
        # 受けられない物も引き入れさせる: 落とした所で理由を言うため(黙って断らない。設計書 P12)。
        md = ev.mimeData()
        if md.hasUrls() or md.hasText():
            ev.acceptProposedAction()

    def dragMoveEvent(self, ev: QtGui.QDragMoveEvent) -> None:
        ev.acceptProposedAction()

    def dropEvent(self, ev: QtGui.QDropEvent) -> None:
        """束のファイルは列に足し、それ以外(画像・フォルダ・ネットの URL・ただの文字)は下の行に理由を出す。"""
        ev.acceptProposedAction()
        self.drop_paths(ev.mimeData())

    def drop_paths(self, md: QtCore.QMimeData) -> list[M.Outcome]:
        """落とされた物を振り分ける: 束のファイル(.json / .toml / .yaml / .yml / .xml)は足し、残りは理由を言う。"""
        urls = md.urls() if md.hasUrls() else []
        files = [u.toLocalFile() for u in urls if u.isLocalFile()]
        good = [f for f in files if os.path.splitext(f)[1].lower() in M.FORMATS and not os.path.isdir(f)]
        bad = [f for f in files if f not in good]
        outs = self.add_paths(good) if good else []
        names = ", ".join(os.path.basename(os.path.normpath(f)) or f for f in bad)
        not_files = len(files) < len(urls) or not urls

        def why(tr: Callable[[str], str]) -> str:
            parts = [o.text(tr) for o in outs if not o.ok]
            if names:
                parts.append(tr("not a parameter file: %s") % names + " (" + tr("open .json, .toml, .yaml / .yml or .xml") + ")")
            if not_files:
                parts.append(tr("only files can be dropped here") + " (" + tr("open .json, .toml, .yaml / .yml or .xml") + ")")
            return " | ".join(parts)

        if names or not_files or any(not o.ok for o in outs):
            self.show_message(why, "error" if any(not o.ok for o in outs) else "warn")
        return outs

    # ---- 絞り込み ----
    def set_diff_only(self, on: bool) -> None:
        """違う行(と片方に無い行)だけにする。"""
        if self.tool_actions["diff"].isChecked() != bool(on):
            self.tool_actions["diff"].setChecked(bool(on))         # toggled → もう一度ここへ来る
            return
        self.tmodel.diff_only = bool(on)
        self.show_message("", "info")                    # 前の表についての知らせを残さない(D112)
        self.refresh()

    def set_query(self, text: str) -> None:
        """キーの検索。"""
        if self.search.text() != text:
            self.search.setText(text)
            return
        self.tmodel.query = text
        self.show_message("", "info")                    # 前の表についての知らせを残さない(D112)
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
            self.show_message(lambda tr: tr("undone: %s") % out.text(tr), "info")
            self.refresh()
        else:
            self._outcome(out)

    def redo(self) -> None:
        out = self.model.redo()
        if out.ok:
            self.show_message(lambda tr: tr("redone: %s") % out.text(tr), "info")
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
            name = self.model.columns[dst].name
            self.show_message(lambda tr: tr("copied %d value(s) to %s") % (out.count, name), "info")
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
                    self.show_message(lambda tr, n=col.name: tr("not saved: %s") % n, "warn")
                    return False
                force = True
            else:
                if not self.ask_losses(col.name, out.note_texts(self.tr_)):
                    self.show_message(lambda tr, n=col.name: tr("not saved: %s") % n, "warn")
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
                self.show_message(lambda tr, n=col.name: tr("not saved: %s") % n, "warn")
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
            names = [(self.model.columns[i].name, state) for i, state in found]

            def changed(tr: Callable[[str], str]) -> str:
                msgs = [tr(M.MESSAGES["external.changed" if state == "changed" else "external.missing"]) % (name,)
                        for name, state in names]
                return "; ".join(msgs) + " — " + tr("Reload reads it again")

            self.show_message(changed, "warn")
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

    def set_tr(self, tr: Callable[[str], str]) -> None:
        """言語を切り替える(窓の題と、パネルの全部の文)。"""
        self.panel.set_tr(tr)
        self.setWindowTitle(self.panel.title())

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
            if self.panel.tree.cancel_rejected():        # 断ったまま残っている欄があれば、まずそれを取り消す
                return
            if self.panel.search.text():                 # 次の Esc は検索を消す、その次で閉じる
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
