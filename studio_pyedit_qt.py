# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_pyedit_qt — Python エディタの部品(Qt): 色分け・補完の窓・シグネチャ・ホバー・括弧・強調。

使い方は 2 通り(どちらも studio.py を変えずに部品だけで動く)。

    1. 既存の ``QPlainTextEdit``(``CodeEditor`` / ``ProgramEditor``)へ後付けする::

           assist = PyEditAssist(editor, provider=default_provider(...), theme="dark", tr=tr)
           assist.set_breakpoints({3}); assist.set_executing(5); assist.set_errors({7: "unknown op"})

    2. 行番号とブレークポイントの印つきの ``PyEditor`` をそのまま使う(``PyEditor(...).assist`` が上と同じ物)。

補完の窓は、フォーカスを奪わない小さな窓(``Qt.Tool`` + ``WindowDoesNotAcceptFocus``)で、キーは編集欄の
イベントフィルタで受ける(Up / Down / Tab / Enter / Esc / Ctrl+Space)。

行の高さ: 一覧・木・表の行は「文字の高さ + ``ROW_EXTRA_PX``」にそろえる(Windows 11 の Qt の様式は行に上下
14 px の余白を足すので、``::item { height }`` で詰める。padding では縮まない)。
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from PySide6 import QtCore, QtGui, QtWidgets

import studio_pyedit_complete as comp
import studio_pyedit_syntax as syn
from studio_pyedit_i18n import identity_tr

#: 一覧・木・表の行の高さ = 文字の高さ + この値。部品の全部がここから出す(1 つの定数)。
ROW_EXTRA_PX = 4


def row_height(font_or_metrics) -> int:
    """行の高さ(px)。``QFont`` か ``QFontMetrics``(``QWidget.font()`` を渡してよい)。"""
    fm = font_or_metrics if isinstance(font_or_metrics, QtGui.QFontMetrics) else QtGui.QFontMetrics(font_or_metrics)
    return fm.height() + ROW_EXTRA_PX


def compact_rows(widget: QtWidgets.QWidget) -> int:
    """``widget``(木・表・一覧)の行を「文字の高さ + ROW_EXTRA_PX」に詰める。返り値は行の高さ。"""
    h = row_height(widget.font())
    qss = ("QTreeView::item, QTableView::item, QListView::item { height: %dpx; }" % h)
    base = re.sub(r"/\*rows\*/.*?/\*end-rows\*/", "", widget.styleSheet(), flags=re.S)
    widget.setStyleSheet(base + "/*rows*/" + qss + "/*end-rows*/")
    if isinstance(widget, QtWidgets.QTableView):
        widget.verticalHeader().setDefaultSectionSize(h)
        widget.verticalHeader().setMinimumSectionSize(h)
    return h


def _qcolor(c: str) -> QtGui.QColor:
    return QtGui.QColor(c)


# --------------------------------------------------------------------------- #
# 色分け
# --------------------------------------------------------------------------- #
class BlockData(QtGui.QTextBlockUserData):
    """ブロックごとの字句と括弧(再走査せずに括弧の対応・同じ名前の強調を作るため)。"""

    def __init__(self, tokens, brackets):
        super().__init__()
        self.tokens = tokens
        self.brackets = brackets


class PythonHighlighter(QtGui.QSyntaxHighlighter):
    """``studio_pyedit_syntax`` の走査で塗る ``QSyntaxHighlighter``。複数行の文字列は ``blockState`` で持つ。"""

    def __init__(self, document: QtGui.QTextDocument, theme: syn.Theme, lexer: syn.LineLexer):
        super().__init__(document)
        self.lexer = lexer
        self._theme = theme
        self._fmts: dict = {}
        self._build_formats()

    def _build_formats(self) -> None:
        self._fmts = {}
        for cat, st in self._theme.styles.items():
            f = QtGui.QTextCharFormat()
            f.setForeground(_qcolor(st.color))
            if st.bold:
                f.setFontWeight(QtGui.QFont.Weight.Bold)
            if st.italic:
                f.setFontItalic(True)
            if st.underline:
                f.setFontUnderline(True)
            self._fmts[cat] = f

    def set_theme(self, theme: syn.Theme) -> None:
        self._theme = theme
        self._build_formats()
        self.rehighlight()

    def set_vocabulary(self, ops: Iterable, prelude: Iterable) -> None:
        self.lexer.ops = frozenset(ops)
        self.lexer.prelude = frozenset(prelude)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        prev = self.previousBlockState()
        toks, state = self.lexer.scan(text, prev if prev > 0 else 0)
        fm = self._fmts
        for a, b, cat in toks:
            if cat == "name":
                continue
            f = fm.get(cat)
            if f is not None:
                self.setFormat(a, b - a, f)
        self.setCurrentBlockState(state)
        self.setCurrentBlockUserData(BlockData(toks, syn.brackets_of(toks, text)))


# --------------------------------------------------------------------------- #
# 候補の窓
# --------------------------------------------------------------------------- #
_MARK_COLORS = {            # 種類の印の背景(暗・明どちらでも白い字が読める濃さ)
    "op": "#0f8f80", "variable": "#3d6fd1", "function": "#8a5cd6", "class": "#b0701c", "module": "#7a4ea0",
    "keyword": "#a35a00", "param": "#4a8f3c", "snippet": "#c0488a", "attribute": "#5a6b8c", "file": "#6b7280",
}


class _ItemDelegate(QtWidgets.QStyledItemDelegate):
    """候補の 1 行: 種類の印(1 文字)・名前・右に 1 行の説明。"""

    def __init__(self, parent, theme_getter: Callable, height: int):
        super().__init__(parent)
        self._theme = theme_getter
        self._h = height

    def sizeHint(self, option, index):
        return QtCore.QSize(option.rect.width(), self._h)

    def paint(self, painter, option, index):
        c: comp.Completion = index.data(QtCore.Qt.UserRole)
        th = self._theme()
        painter.save()
        r = option.rect
        sel = bool(option.state & QtWidgets.QStyle.State_Selected)
        painter.fillRect(r, _qcolor(th.selection_bg if sel else th.bg))
        fg = _qcolor(th.selection_fg if sel else th.fg)
        muted = _qcolor(th.selection_fg if sel else th.gutter_fg)
        s = r.height() - 4
        badge = QtCore.QRect(r.left() + 3, r.top() + 2, s, s)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(_qcolor(_MARK_COLORS.get(c.kind, "#555")))
        painter.drawRoundedRect(badge, 3, 3)
        painter.setPen(_qcolor("#ffffff"))
        f = painter.font()
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(badge, QtCore.Qt.AlignCenter, comp.KIND_MARK.get(c.kind, "?"))
        f.setBold(False)
        painter.setFont(f)
        x = badge.right() + 6
        name_w = painter.fontMetrics().horizontalAdvance(c.name)
        painter.setPen(fg)
        painter.drawText(QtCore.QRect(x, r.top(), r.right() - x, r.height()), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, c.name)
        if c.detail:
            dx = x + name_w + 14
            avail = r.right() - dx - 6
            if avail > 20:
                painter.setPen(muted)
                el = painter.fontMetrics().elidedText(c.detail, QtCore.Qt.ElideRight, avail)
                painter.drawText(QtCore.QRect(dx, r.top(), avail, r.height()), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, el)
        painter.restore()


class CompletionPopup(QtWidgets.QFrame):
    """候補の窓(左に一覧、右に選んでいる候補の詳しい説明)。フォーカスは編集欄に残る。"""

    accepted = QtCore.Signal(object)          # Completion

    def __init__(self, editor: QtWidgets.QPlainTextEdit, theme_getter: Callable, tr: Callable = identity_tr):
        super().__init__(editor.window(), QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._editor = editor
        self._theme = theme_getter
        self._tr = tr
        self.setObjectName("pyeditCompletionPopup")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)
        lay.setSpacing(1)
        self.list = QtWidgets.QListWidget(self)
        self.list.setFocusPolicy(QtCore.Qt.NoFocus)
        self.list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.list.setUniformItemSizes(True)
        self.list.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._rh = compact_rows(self.list)
        self.list.setItemDelegate(_ItemDelegate(self.list, theme_getter, self._rh))
        self.list.setMinimumWidth(340)
        self.list.itemClicked.connect(lambda it: self.accepted.emit(it.data(QtCore.Qt.UserRole)))
        self.list.currentItemChanged.connect(lambda *_: self._show_doc())
        lay.addWidget(self.list)
        self.doc = QtWidgets.QLabel(self)
        self.doc.setWordWrap(True)
        self.doc.setTextFormat(QtCore.Qt.RichText)
        self.doc.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.doc.setFixedWidth(300)
        self.doc.setMargin(6)
        lay.addWidget(self.doc)
        self.apply_theme()

    def apply_theme(self) -> None:
        th = self._theme()
        self.setStyleSheet("#pyeditCompletionPopup{background:%s;border:1px solid %s;}"
                           "QListWidget{background:%s;color:%s;border:0;}"
                           "QLabel{background:%s;color:%s;}" % (th.gutter_bg, th.gutter_fg, th.bg, th.fg, th.current_line_bg, th.fg))
        self.list.setStyleSheet(self.list.styleSheet())
        compact_rows(self.list)

    # ---- 中身 ----
    def set_items(self, items: list) -> None:
        self.list.clear()
        for c in items:
            it = QtWidgets.QListWidgetItem(c.name)
            it.setData(QtCore.Qt.UserRole, c)
            self.list.addItem(it)
        if items:
            self.list.setCurrentRow(0)
        shown = min(len(items), 10)
        self.list.setFixedHeight(self._rh * max(shown, 1) + 2)
        self._show_doc()

    def current(self):
        it = self.list.currentItem()
        return it.data(QtCore.Qt.UserRole) if it is not None else None

    def step(self, delta: int) -> None:
        """選択を ``delta`` 行動かす(QWidget.move と取り違えないよう名前を分ける)。"""
        n = self.list.count()
        if n:
            self.list.setCurrentRow(max(0, min(n - 1, self.list.currentRow() + delta)))

    def _show_doc(self) -> None:
        c = self.current()
        if c is None:
            self.doc.hide()
            return
        body = c.full_doc()
        if body.strip() == c.detail.strip():
            body = ""                                       # 1 行の説明と同じ物を 2 度出さない
        lines = [x for x in body.split("\n")] if body else []
        head = "<b>%s</b> <span style='color:%s'>%s</span>" % (html.escape(c.name), self._theme().gutter_fg,
                                                                html.escape(self._tr(c.kind)))
        text = head
        if c.detail:
            text += "<br>" + html.escape(c.detail)
        if lines:
            more = "<br><br>" + "<br>".join(html.escape(x) for x in lines[:14])
            text += more
        self.doc.setText(text)
        self.doc.show()
        self.adjustSize()

    def show_at(self, rect: QtCore.QRect) -> None:
        """``rect`` は編集欄の座標のカーソルの矩形。画面からはみ出すなら上に出す。"""
        self.adjustSize()
        pos = self._editor.viewport().mapToGlobal(rect.bottomLeft())
        scr = QtGui.QGuiApplication.screenAt(pos) or QtGui.QGuiApplication.primaryScreen()
        geo = scr.availableGeometry()
        w, h = self.sizeHint().width(), self.sizeHint().height()
        x = min(pos.x(), geo.right() - w)
        y = pos.y() + 2
        if y + h > geo.bottom():
            y = self._editor.viewport().mapToGlobal(rect.topLeft()).y() - h - 2
        self.move(max(geo.left(), x), max(geo.top(), y))
        self.show()


class SignatureTip(QtWidgets.QFrame):
    """シグネチャの案内。今の引数を太字にし、その引数の意味(op ならつまみの役割・範囲・単位)を下に出す。"""

    def __init__(self, editor: QtWidgets.QPlainTextEdit, theme_getter: Callable, tr: Callable = identity_tr):
        super().__init__(editor.window(), QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._editor, self._theme, self._tr = editor, theme_getter, tr
        self.setObjectName("pyeditSignatureTip")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 3, 6, 3)
        self.label = QtWidgets.QLabel(self)
        self.label.setTextFormat(QtCore.Qt.RichText)
        self.label.setWordWrap(False)
        lay.addWidget(self.label)
        self.apply_theme()

    def apply_theme(self) -> None:
        th = self._theme()
        self.setStyleSheet("#pyeditSignatureTip{background:%s;border:1px solid %s;}QLabel{color:%s;}"
                           % (th.current_line_bg, th.gutter_fg, th.fg))

    def html_for(self, sig: comp.Signature, active: int | None) -> str:
        th = self._theme()
        parts = []
        for text, bold in sig.segments(active):
            t = html.escape(text)
            parts.append("<b style='color:%s;text-decoration:underline'>%s</b>" % (th.styles["op"].color, t) if bold else t)
        out = "".join(parts)
        if active is not None and 0 <= active < len(sig.params) and sig.params[active].doc:
            out += "<br><span style='color:%s'>%s</span>" % (th.gutter_fg, html.escape(sig.params[active].doc))
        if sig.summary:
            out += "<br><span style='color:%s'>%s</span>" % (th.gutter_fg, html.escape(sig.summary))
        return out

    def show_for(self, sig: comp.Signature, active: int | None, rect: QtCore.QRect) -> None:
        self.label.setText(self.html_for(sig, active))
        self.adjustSize()
        pos = self._editor.viewport().mapToGlobal(rect.topLeft())
        self.move(pos.x(), pos.y() - self.sizeHint().height() - 2)
        self.show()


# --------------------------------------------------------------------------- #
# 後付けの制御役
# --------------------------------------------------------------------------- #
@dataclass
class Marks:
    """行の印。行番号は **1 始まり**(画面に出る番号。Problems や実行系と同じ)。"""
    breakpoints: set = field(default_factory=set)
    executing: int | None = None
    errors: dict = field(default_factory=dict)       # 行 → 理由


class PyEditAssist(QtCore.QObject):
    """``QPlainTextEdit`` に色分け・補完・シグネチャ・ホバー・括弧・同じ名前の強調・行の印を足す。"""

    completionAccepted = QtCore.Signal(str)           # 確定した候補の名前(よく使う物の学習に)

    def __init__(self, editor: QtWidgets.QPlainTextEdit, provider=None, theme: str = "dark",
                 tr: Callable = identity_tr, backend: str = "auto", usage: comp.UsageStats | None = None):
        super().__init__(editor)
        self.editor = editor
        self.provider = provider
        self._tr = tr
        self.usage = usage
        self.theme = syn.theme_by_name(theme)
        self.marks = Marks()
        self.external_selections: Callable[[], list] | None = None
        self.completion_enabled = True
        self.lexer = syn.LineLexer(backend)
        self.highlighter = PythonHighlighter(editor.document(), self.theme, self.lexer)
        self.popup = CompletionPopup(editor, lambda: self.theme, tr)
        self.popup.accepted.connect(self.accept_completion)
        self.tip = SignatureTip(editor, lambda: self.theme, tr)
        self._items: list = []
        self._prefix_len = 0
        self._pending: str | None = None
        self._bracket_cache: tuple = (-1, {}, [])
        self._deco_timer = QtCore.QTimer(self)
        self._deco_timer.setSingleShot(True)
        self._deco_timer.setInterval(30)
        self._deco_timer.timeout.connect(self.refresh_decorations)
        self._sig_timer = QtCore.QTimer(self)
        self._sig_timer.setSingleShot(True)
        self._sig_timer.setInterval(40)
        self._sig_timer.timeout.connect(self.update_signature)
        editor.installEventFilter(self)
        editor.viewport().installEventFilter(self)
        editor.cursorPositionChanged.connect(self._on_cursor)
        editor.textChanged.connect(self._on_text)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_app_state)
        editor.verticalScrollBar().valueChanged.connect(lambda _v: (self.popup.hide(), self._deco_timer.start()))
        self.apply_theme()
        self._sync_vocabulary()

    def _on_app_state(self, state) -> None:
        if state != QtCore.Qt.ApplicationActive:          # 別のアプリへ切り替えたら窓を閉じる
            self.popup.hide()
            self.tip.hide()

    # ---- 設定 ----
    def _sync_vocabulary(self) -> None:
        fb = getattr(self.provider, "fallback", self.provider)
        if hasattr(fb, "vocabulary"):
            try:
                ops, prelude = fb.vocabulary()
                self.highlighter.set_vocabulary(ops, prelude)
            except Exception:                                   # noqa: BLE001 — 語彙が引けなくても色分けは動く
                pass

    def set_provider(self, provider) -> None:
        self.provider = provider
        self._sync_vocabulary()

    def set_theme(self, name: str) -> None:
        self.theme = syn.theme_by_name(name)
        self.apply_theme()

    def apply_theme(self) -> None:
        th = self.theme
        self.editor.setStyleSheet(
            "QPlainTextEdit{background:%s;color:%s;selection-background-color:%s;selection-color:%s;}"
            % (th.bg, th.fg, th.selection_bg, th.selection_fg))
        self.highlighter.set_theme(th)
        self.popup.apply_theme()
        self.tip.apply_theme()
        self.editor.viewport().update()
        self.refresh_decorations()

    def set_breakpoints(self, lines: Iterable) -> None:
        self.marks.breakpoints = set(int(x) for x in lines)
        self.refresh_decorations()

    def set_executing(self, line: int | None) -> None:
        self.marks.executing = None if line is None else int(line)
        self.refresh_decorations()

    def set_errors(self, errors: Mapping) -> None:
        self.marks.errors = {int(k): str(v) for k, v in errors.items()}
        self.refresh_decorations()

    # ---- 装飾(extraSelections) ----
    def _sel(self, cursor: QtGui.QTextCursor, fmt: QtGui.QTextCharFormat) -> QtWidgets.QTextEdit.ExtraSelection:
        s = QtWidgets.QTextEdit.ExtraSelection()
        s.cursor = cursor
        s.format = fmt
        return s

    def _line_cursor(self, line1: int) -> QtGui.QTextCursor | None:
        blk = self.editor.document().findBlockByNumber(line1 - 1)
        if not blk.isValid():
            return None
        return QtGui.QTextCursor(blk)

    def _brackets(self) -> tuple:
        doc = self.editor.document()
        rev = doc.revision()
        if self._bracket_cache[0] != rev:
            per_line = []
            blk = doc.begin()
            while blk.isValid():
                ud = blk.userData()
                per_line.append(ud.brackets if isinstance(ud, BlockData) else [])
                blk = blk.next()
            pairs, bad = syn.match_brackets(per_line)
            self._bracket_cache = (rev, pairs, bad)
        return self._bracket_cache[1], self._bracket_cache[2]

    def refresh_decorations(self) -> None:
        th = self.theme
        ed = self.editor
        doc = ed.document()
        sels: list = []
        cur = ed.textCursor()
        # 今の行
        f = QtGui.QTextCharFormat()
        f.setBackground(_qcolor(th.current_line_bg))
        f.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        c = QtGui.QTextCursor(cur)
        c.clearSelection()
        sels.append(self._sel(c, f))
        # ブレークポイント・実行中・エラーの行(色 + 波線 + 行番号側の印)
        for ln in sorted(self.marks.breakpoints):
            lc = self._line_cursor(ln)
            if lc is not None:
                ff = QtGui.QTextCharFormat()
                ff.setBackground(_qcolor(th.breakpoint_bg))
                ff.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
                sels.append(self._sel(lc, ff))
        if self.marks.executing is not None:
            lc = self._line_cursor(self.marks.executing)
            if lc is not None:
                ff = QtGui.QTextCharFormat()
                ff.setBackground(_qcolor(th.exec_bg))
                ff.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
                sels.append(self._sel(lc, ff))
        for ln in sorted(self.marks.errors):
            blk = doc.findBlockByNumber(ln - 1)
            if not blk.isValid():
                continue
            text = blk.text()
            a = len(text) - len(text.lstrip())
            b = len(text.rstrip())
            if b <= a:
                a, b = 0, max(1, len(text))
            lc = QtGui.QTextCursor(blk)
            lc.setPosition(blk.position() + a)
            lc.setPosition(blk.position() + min(b, blk.length() - 1), QtGui.QTextCursor.KeepAnchor)
            ff = QtGui.QTextCharFormat()
            ff.setUnderlineStyle(QtGui.QTextCharFormat.WaveUnderline)
            ff.setUnderlineColor(_qcolor(th.error_line_color))
            ff.setBackground(_qcolor(th.error_bg))
            sels.append(self._sel(lc, ff))
        # 括弧
        blk = cur.block()
        ud = blk.userData()
        col = cur.positionInBlock()
        if isinstance(ud, BlockData):
            pairs, bad = self._brackets()
            bcol = syn.bracket_at_cursor(ud.brackets, col)
            if bcol is not None:
                key = (blk.blockNumber(), bcol)
                other = pairs.get(key)
                targets = [key, other] if other is not None else []
                for ln0, c0 in targets:
                    bb = doc.findBlockByNumber(ln0)
                    cc = QtGui.QTextCursor(bb)
                    cc.setPosition(bb.position() + c0)
                    cc.setPosition(bb.position() + c0 + 1, QtGui.QTextCursor.KeepAnchor)
                    ff = QtGui.QTextCharFormat()
                    ff.setBackground(_qcolor(th.bracket_match_bg))
                    ff.setFontWeight(QtGui.QFont.Weight.Bold)
                    sels.append(self._sel(cc, ff))
            for ln0, c0 in bad[:200]:                          # 対応の無い括弧は赤 + 波線(色だけに頼らない)
                bb = doc.findBlockByNumber(ln0)
                if not bb.isValid():
                    continue
                cc = QtGui.QTextCursor(bb)
                cc.setPosition(bb.position() + c0)
                cc.setPosition(bb.position() + c0 + 1, QtGui.QTextCursor.KeepAnchor)
                ff = QtGui.QTextCharFormat()
                ff.setForeground(_qcolor(th.bracket_bad_fg))
                ff.setUnderlineStyle(QtGui.QTextCharFormat.WaveUnderline)
                ff.setUnderlineColor(_qcolor(th.bracket_bad_fg))
                ff.setFontWeight(QtGui.QFont.Weight.Bold)
                sels.append(self._sel(cc, ff))
            # 同じ名前
            word = syn.name_at(ud.tokens, blk.text(), col)
            if word:
                sels.extend(self._occurrence_selections(word))
        if self.external_selections is not None:
            try:
                sels.extend(self.external_selections())
            except Exception:                                   # noqa: BLE001
                pass
        ed.setExtraSelections(sels)

    def _occurrence_selections(self, word: str) -> list:
        th = self.theme
        ed = self.editor
        out: list = []
        blk = ed.firstVisibleBlock()
        bottom = ed.viewport().height()
        n = 0
        while blk.isValid() and n < 400:
            top = ed.blockBoundingGeometry(blk).translated(ed.contentOffset()).top()
            if top > bottom:
                break
            ud = blk.userData()
            if isinstance(ud, BlockData):
                text = blk.text()
                for a, b in syn.occurrences(ud.tokens, text, word):
                    cc = QtGui.QTextCursor(blk)
                    cc.setPosition(blk.position() + a)
                    cc.setPosition(blk.position() + b, QtGui.QTextCursor.KeepAnchor)
                    ff = QtGui.QTextCharFormat()
                    ff.setBackground(_qcolor(th.occurrence_bg))
                    out.append(self._sel(cc, ff))
            blk = blk.next()
            n += 1
        return out

    # ---- イベント ----
    def _on_cursor(self) -> None:
        self._deco_timer.start()
        self._sig_timer.start()
        if self.popup.isVisible():
            cur = self.editor.textCursor()
            if cur.positionInBlock() < self._word_start_col():
                self.popup.hide()

    def _on_text(self) -> None:
        self._deco_timer.start()

    def _word_start_col(self) -> int:
        cur = self.editor.textCursor()
        before = cur.block().text()[:cur.positionInBlock()]
        return len(before) - len(comp.word_prefix(before))

    def eventFilter(self, obj, ev):
        et = ev.type()
        if obj is self.editor:
            if et == QtCore.QEvent.KeyPress:
                if self.popup.isVisible() and self._popup_key(ev):
                    return True
                if (ev.key() == QtCore.Qt.Key_Space and ev.modifiers() & QtCore.Qt.ControlModifier
                        and not ev.modifiers() & QtCore.Qt.ShiftModifier):
                    self.show_completions(force=True)
                    return True
                if ev.key() == QtCore.Qt.Key_Escape and self.tip.isVisible():
                    self.tip.hide()
                    return True
                self._pending = ev.text()
                QtCore.QTimer.singleShot(0, self._after_key)
            elif et == QtCore.QEvent.FocusOut and ev.reason() != QtCore.Qt.ActiveWindowFocusReason:
                self.popup.hide()                       # クリック・Tab で他へ移ったとき(窓の切り替えは下の app の状態で)
                self.tip.hide()
            elif et == QtCore.QEvent.Hide:
                self.popup.hide()
                self.tip.hide()
        elif obj is self.editor.viewport() and et == QtCore.QEvent.ToolTip:
            return self._hover(ev)
        return False

    def _popup_key(self, ev) -> bool:
        k = ev.key()
        if k == QtCore.Qt.Key_Down:
            self.popup.step(1)
        elif k == QtCore.Qt.Key_Up:
            self.popup.step(-1)
        elif k == QtCore.Qt.Key_PageDown:
            self.popup.step(8)
        elif k == QtCore.Qt.Key_PageUp:
            self.popup.step(-8)
        elif k in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and not ev.modifiers() & QtCore.Qt.ControlModifier:
            self.accept_completion(self.popup.current())
        elif k == QtCore.Qt.Key_Escape:
            self.popup.hide()
        else:
            return False
        return True

    def _after_key(self) -> None:
        typed, self._pending = self._pending or "", None
        if not self.completion_enabled or self.provider is None:
            return
        cur = self.editor.textCursor()
        before = cur.block().text()[:cur.positionInBlock()]
        if typed:
            trig = comp.auto_trigger(before, typed[-1])
            if trig == "paren":
                self.update_signature()
                self.show_completions()
            elif trig is not None:
                self.show_completions()
            elif self.popup.isVisible():
                self.popup.hide()
        elif self.popup.isVisible():                           # Backspace など: 開いていれば絞り直す
            self.show_completions()

    # ---- 補完 ----
    def _position(self) -> tuple:
        cur = self.editor.textCursor()
        return self.editor.toPlainText(), cur.blockNumber(), cur.positionInBlock()

    def show_completions(self, force: bool = False) -> bool:
        """候補を出す。出たら True。``force`` は Ctrl+Space(打ちかけが空でも出す)。"""
        if self.provider is None:
            return False
        text, line, col = self._position()
        try:
            items = self.provider.complete(text, line, col)
        except Exception:                                       # noqa: BLE001 — 供給元の失敗で入力を止めない
            items = []
        before = text.split("\n")[line][:col]
        self._prefix_len = len(comp.word_prefix(before))
        if not items:
            self.popup.hide()
            return False
        if not force and len(items) == 1 and items[0].name == comp.word_prefix(before) and items[0].kind != "param":
            self.popup.hide()
            return False
        self._items = items
        self.popup.set_items(items)
        rect = self.editor.cursorRect()
        wc = max(0, self._prefix_len)
        rect.translate(-self.editor.fontMetrics().horizontalAdvance("x") * wc, 0)
        self.popup.show_at(rect)
        return True

    def accept_completion(self, c) -> None:
        if c is None:
            return
        ed = self.editor
        cur = ed.textCursor()
        n = c.replace_len if c.replace_len is not None else self._prefix_len
        cur.beginEditBlock()
        for _ in range(n):
            cur.deletePreviousChar()
        start = cur.position()
        blk_text = cur.block().text()
        indent = blk_text[: len(blk_text) - len(blk_text.lstrip())]
        text = c.text.replace("\n", "\n" + indent)
        cur.insertText(text)
        off = c.cursor_offset
        if off is not None:
            adj = off + c.text[:off].count("\n") * len(indent)
            cur.setPosition(start + adj)
        cur.endEditBlock()
        ed.setTextCursor(cur)
        self.popup.hide()
        if self.usage is not None:
            self.usage.bump(c.name)
        self.completionAccepted.emit(c.name)

    # ---- シグネチャ ----
    def update_signature(self) -> None:
        if self.provider is None or not hasattr(self.provider, "signature"):
            return
        text, line, col = self._position()
        try:
            r = self.provider.signature(text, line, col)
        except Exception:                                       # noqa: BLE001
            r = None
        if not r:
            self.tip.hide()
            return
        sig, active = r
        self.tip.show_for(sig, active, self.editor.cursorRect())

    # ---- ホバー ----
    def _hover(self, ev) -> bool:
        ed = self.editor
        cur = ed.cursorForPosition(ev.pos())
        line1 = cur.blockNumber() + 1
        if line1 in self.marks.errors:
            QtWidgets.QToolTip.showText(ev.globalPos(), "⚠ " + self.marks.errors[line1], ed.viewport())
            return True
        if self.provider is None or not hasattr(self.provider, "hover"):
            return False
        try:
            h = self.provider.hover(ed.toPlainText(), cur.blockNumber(), cur.positionInBlock())
        except Exception:                                       # noqa: BLE001
            h = None
        if h is None:
            QtWidgets.QToolTip.hideText()
            return False
        body = "<b>%s</b>" % html.escape(h.title) + ("<br>" + html.escape(h.body) if h.body else "")
        QtWidgets.QToolTip.showText(ev.globalPos(), body, ed.viewport())
        return True


# --------------------------------------------------------------------------- #
# 行番号・ブレークポイントの印つきの編集欄(そのまま使える版)
# --------------------------------------------------------------------------- #
class _Gutter(QtWidgets.QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._ed = editor

    def sizeHint(self):
        return QtCore.QSize(self._ed.gutter_width(), 0)

    def paintEvent(self, ev):
        self._ed.paint_gutter(ev)

    def mousePressEvent(self, ev):
        self._ed.gutter_click(ev)


class PyEditor(QtWidgets.QPlainTextEdit):
    """行番号・ブレークポイント(クリックで付け外し)・実行中の行の印・エラーの印つきの編集欄。
    印は色だけでなく形(● ▶ !)でも出す。"""

    breakpointToggled = QtCore.Signal(int, bool)       # 行(1 始まり), 付いたか

    def __init__(self, provider=None, theme: str = "dark", tr: Callable = identity_tr, parent=None, font_pt: int = 10):
        super().__init__(parent)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        f = QtGui.QFont("Consolas")
        f.setStyleHint(QtGui.QFont.Monospace)
        f.setPointSize(font_pt)
        self.setFont(f)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self._gutter = _Gutter(self)
        self.blockCountChanged.connect(lambda _n: self._update_gutter_width())
        self.updateRequest.connect(self._update_gutter)
        self._update_gutter_width()
        self.assist = PyEditAssist(self, provider, theme, tr)

    def gutter_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 30 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_gutter_width(self):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _update_gutter(self, rect, dy):
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        cr = self.contentsRect()
        self._gutter.setGeometry(QtCore.QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def paint_gutter(self, ev):
        th = self.assist.theme
        p = QtGui.QPainter(self._gutter)
        p.fillRect(ev.rect(), _qcolor(th.gutter_bg))
        blk = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(blk).translated(self.contentOffset()).top()
        fm = self.fontMetrics()
        m = self.assist.marks
        while blk.isValid() and top <= ev.rect().bottom():
            bh = self.blockBoundingRect(blk).height()
            if blk.isVisible() and top + bh >= ev.rect().top():
                ln = blk.blockNumber() + 1
                p.setPen(_qcolor(th.gutter_fg))
                p.drawText(0, int(top), self._gutter.width() - 6, fm.height(), QtCore.Qt.AlignRight, str(ln))
                cy = int(top) + fm.height() // 2
                if ln in m.breakpoints:
                    p.setPen(QtCore.Qt.NoPen)
                    p.setBrush(_qcolor(th.error_line_color))
                    p.drawEllipse(QtCore.QPoint(8, cy), 4, 4)
                if m.executing == ln:
                    p.setPen(_qcolor(th.styles["keyword"].color))
                    p.drawText(14, int(top), 12, fm.height(), QtCore.Qt.AlignCenter, "▶")
                if ln in m.errors:
                    p.setPen(_qcolor(th.error_line_color))
                    f = p.font()
                    f.setBold(True)
                    p.setFont(f)
                    p.drawText(14, int(top), 12, fm.height(), QtCore.Qt.AlignCenter, "!")
                    f.setBold(False)
                    p.setFont(f)
            blk = blk.next()
            top += bh
        p.end()

    def gutter_click(self, ev):
        blk = self.cursorForPosition(QtCore.QPoint(0, int(ev.position().y()))).block()
        ln = blk.blockNumber() + 1
        bps = set(self.assist.marks.breakpoints)
        if ln in bps:
            bps.discard(ln)
            on = False
        else:
            bps.add(ln)
            on = True
        self.assist.set_breakpoints(bps)
        self._gutter.update()
        self.breakpointToggled.emit(ln, on)

    def keyPressEvent(self, ev):
        if ev.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            cur = self.textCursor()
            line = cur.block().text()[: cur.positionInBlock()]
            indent = line[: len(line) - len(line.lstrip())]
            if line.rstrip().endswith(":"):
                indent += "    "
            super().keyPressEvent(ev)
            if indent:
                self.insertPlainText(indent)
            return
        if ev.key() == QtCore.Qt.Key_Tab and not ev.modifiers():
            self.insertPlainText("    ")
            return
        super().keyPressEvent(ev)
