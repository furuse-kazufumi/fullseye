"""Fullseye Studio の Python コードエディタ ―― IDE 級の編集機能を載せた QPlainTextEdit。

機能:
  - 行番号 / 現在行ハイライト / Python シンタックス強調 / 括弧自動補完
  - 入力補完(jedi があれば実補完、無ければ キーワード + バッファ内語)   … Ctrl+Space / 自動
  - 定義へジャンプ(jedi)                                              … F12 / Ctrl+クリック
  - 矩形(列)選択 と 矩形コピー/カット/貼り付け                         … Alt+ドラッグ → Ctrl+C/X/V
  - オートインデント(: の後で増、Enter で継承)/ Tab=4スペース

Studio が無い環境でも import できるよう、PySide6 が無ければ ImportError を上げるだけ。
"""
from __future__ import annotations
import builtins
import keyword

from PySide6 import QtCore, QtGui, QtWidgets

try:
    import jedi
except Exception:
    jedi = None


# ─────────────────────────── シンタックス強調 ─────────────────────────── #
class PyHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        def fmt(color, bold=False, italic=False):
            f = QtGui.QTextCharFormat(); f.setForeground(QtGui.QColor(color))
            if bold:
                f.setFontWeight(QtGui.QFont.Weight.Bold)
            if italic:
                f.setFontItalic(True)
            return f
        self._kw = fmt("#c586c0", bold=True)
        self._builtin = fmt("#4ec9b0")
        self._defname = fmt("#dcdcaa")
        self._num = fmt("#b5cea8")
        self._str = fmt("#ce9178")
        self._com = fmt("#6a9955", italic=True)
        self._deco = fmt("#569cd6")
        self._rules = []
        for w in keyword.kwlist:
            self._rules.append((QtCore.QRegularExpression(rf"\b{w}\b"), self._kw))
        for w in dir(builtins):
            if not w.startswith("_"):
                self._rules.append((QtCore.QRegularExpression(rf"\b{w}\b"), self._builtin))
        self._rules.append((QtCore.QRegularExpression(r"\b[A-Za-z_]\w*(?=\s*\()"), self._defname))
        self._rules.append((QtCore.QRegularExpression(r"\b\d+\.?\d*\b"), self._num))
        self._rules.append((QtCore.QRegularExpression(r"@\w+"), self._deco))
        self._rules.append((QtCore.QRegularExpression(r"'[^']*'|\"[^\"]*\""), self._str))
        self._rules.append((QtCore.QRegularExpression(r"#[^\n]*"), self._com))

    def highlightBlock(self, text):
        for rx, f in self._rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), f)


class _LineNumberArea(QtWidgets.QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._ed = editor

    def sizeHint(self):
        return QtCore.QSize(self._ed.line_number_width(), 0)

    def paintEvent(self, ev):
        self._ed.paint_line_numbers(ev)


# ─────────────────────────── エディタ本体 ─────────────────────────── #
class CodeEditor(QtWidgets.QPlainTextEdit):
    goto_requested = QtCore.Signal(str, int)     # (path, line) 定義が別ファイルのとき

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QtGui.QFont("Consolas", 10))
        self.setTabStopDistance(4 * QtGui.QFontMetricsF(self.font()).horizontalAdvance(" "))
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self._lna = _LineNumberArea(self)
        self.blockCountChanged.connect(lambda _: self._update_lna_width())
        self.updateRequest.connect(self._update_lna)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_lna_width(); self._highlight_current_line()
        self._hl = PyHighlighter(self.document())
        # 補完
        self._completer = QtWidgets.QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self._completer.activated.connect(self._insert_completion)
        # 矩形(列)選択
        self._block_anchor = None       # (line, col)
        self._block_pos = None
        self._block_sel = False

    # ---- 行番号 ----
    def line_number_width(self):
        digits = max(3, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_lna_width(self):
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_lna(self, rect, dy):
        if dy:
            self._lna.scroll(0, dy)
        else:
            self._lna.update(0, rect.y(), self._lna.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_lna_width()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        cr = self.contentsRect()
        self._lna.setGeometry(cr.left(), cr.top(), self.line_number_width(), cr.height())

    def paint_line_numbers(self, ev):
        p = QtGui.QPainter(self._lna)
        p.fillRect(ev.rect(), QtGui.QColor("#161a24"))
        blk = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(blk).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(blk).height()
        cur = self.textCursor().blockNumber()
        while blk.isValid() and top <= ev.rect().bottom():
            if blk.isVisible() and bottom >= ev.rect().top():
                n = blk.blockNumber()
                p.setPen(QtGui.QColor("#c8ccd4" if n == cur else "#5a6070"))
                p.drawText(0, int(top), self._lna.width() - 6,
                           self.fontMetrics().height(),
                           int(QtCore.Qt.AlignmentFlag.AlignRight), str(n + 1))
            blk = blk.next()
            top = bottom
            bottom = top + self.blockBoundingRect(blk).height()

    def _highlight_current_line(self):
        sels = []
        if not self.isReadOnly():
            sel = QtWidgets.QTextEdit.ExtraSelection()
            sel.format.setBackground(QtGui.QColor("#1d2230"))
            sel.format.setProperty(QtGui.QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor(); sel.cursor.clearSelection()
            sels.append(sel)
        sels += self._block_selection_extras()
        self.setExtraSelections(sels)

    # ---- 補完(jedi 優先) ----
    def _word_prefix(self):
        c = self.textCursor(); c.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
        return c.selectedText()

    def _completions(self):
        line = self.textCursor().blockNumber() + 1
        col = self.textCursor().positionInBlock()
        if jedi is not None:
            try:
                sc = jedi.Script(code=self.toPlainText())
                return [c.name for c in sc.complete(line, col)][:80]
            except Exception:
                pass
        # フォールバック: キーワード + バッファ内の識別子
        import re
        words = set(keyword.kwlist) | {w for w in dir(builtins) if not w.startswith("_")}
        words |= set(re.findall(r"[A-Za-z_]\w+", self.toPlainText()))
        pre = self._word_prefix()
        return sorted(w for w in words if w.startswith(pre) and w != pre)[:80]

    def _trigger_completion(self):
        comps = self._completions()
        if not comps:
            self._completer.popup().hide(); return
        self._completer.setModel(QtCore.QStringListModel(comps, self._completer))
        self._completer.setCompletionPrefix(self._word_prefix())
        cr = self.cursorRect()
        cr.setWidth(self._completer.popup().sizeHintForColumn(0)
                    + self._completer.popup().verticalScrollBar().sizeHint().width() + 20)
        self._completer.complete(cr)

    def _insert_completion(self, text):
        c = self.textCursor(); c.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
        c.insertText(text)
        self.setTextCursor(c)

    # ---- 定義へジャンプ(jedi) ----
    def goto_definition(self):
        if jedi is None:
            return
        line = self.textCursor().blockNumber() + 1
        col = self.textCursor().positionInBlock()
        try:
            defs = jedi.Script(code=self.toPlainText()).goto(line, col, follow_imports=True)
        except Exception:
            return
        if not defs:
            return
        d = defs[0]
        if d.module_path and str(d.module_path) not in ("", "None") and d.line:
            # 同一バッファなら移動、別ファイルはシグナル
            self.goto_requested.emit(str(d.module_path), int(d.line))
        if d.line:
            self._move_to_line(int(d.line), int(d.column or 0))

    def _move_to_line(self, line, col=0):
        blk = self.document().findBlockByNumber(max(0, line - 1))
        if blk.isValid():
            c = QtGui.QTextCursor(blk)
            c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                           QtGui.QTextCursor.MoveMode.MoveAnchor, col)
            self.setTextCursor(c); self.centerCursor()

    # ---- 矩形(列)選択 ----
    def _pos_to_lc(self, pos):
        c = self.cursorForPosition(pos)
        return c.blockNumber(), c.positionInBlock()

    def _block_ranges(self):
        """block 選択を (line, col0, col1) の行リストに。"""
        if not (self._block_anchor and self._block_pos):
            return []
        (l0, c0), (l1, c1) = self._block_anchor, self._block_pos
        lo, hi = sorted((l0, l1)); ca, cb = sorted((c0, c1))
        return [(ln, ca, cb) for ln in range(lo, hi + 1)]

    def _block_selection_extras(self):
        out = []
        for ln, ca, cb in self._block_ranges():
            blk = self.document().findBlockByNumber(ln)
            if not blk.isValid():
                continue
            n = len(blk.text())
            cur = QtGui.QTextCursor(blk)
            cur.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                             QtGui.QTextCursor.MoveMode.MoveAnchor, min(ca, n))
            cur.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                             QtGui.QTextCursor.MoveMode.KeepAnchor, max(0, min(cb, n) - min(ca, n)))
            sel = QtWidgets.QTextEdit.ExtraSelection()
            sel.format.setBackground(QtGui.QColor("#264f78"))
            sel.cursor = cur
            out.append(sel)
        return out

    def mousePressEvent(self, ev):
        mods = ev.modifiers()
        if mods & QtCore.Qt.KeyboardModifier.ControlModifier and jedi is not None:
            self.setTextCursor(self.cursorForPosition(ev.position().toPoint()))
            self.goto_definition(); return
        if mods & QtCore.Qt.KeyboardModifier.AltModifier:
            self._block_sel = True
            self._block_anchor = self._pos_to_lc(ev.position().toPoint())
            self._block_pos = self._block_anchor
            self._highlight_current_line(); return
        self._block_sel = False; self._block_anchor = self._block_pos = None
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._block_sel:
            self._block_pos = self._pos_to_lc(ev.position().toPoint())
            self._highlight_current_line(); return
        super().mouseMoveEvent(ev)

    def _block_text(self):
        lines = []
        for ln, ca, cb in self._block_ranges():
            t = self.document().findBlockByNumber(ln).text()
            lines.append(t[ca:cb])
        return "\n".join(lines)

    def _block_delete(self):
        cur = self.textCursor(); cur.beginEditBlock()
        for ln, ca, cb in reversed(self._block_ranges()):
            blk = self.document().findBlockByNumber(ln)
            c = QtGui.QTextCursor(blk); n = len(blk.text())
            c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                           QtGui.QTextCursor.MoveMode.MoveAnchor, min(ca, n))
            c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                           QtGui.QTextCursor.MoveMode.KeepAnchor, max(0, min(cb, n) - min(ca, n)))
            c.removeSelectedText()
        cur.endEditBlock()
        self._block_anchor = self._block_pos = None

    def _block_paste(self):
        text = QtWidgets.QApplication.clipboard().text()
        rows = text.split("\n")
        rng = self._block_ranges()
        col = rng[0][1] if rng else self.textCursor().positionInBlock()
        start_line = rng[0][0] if rng else self.textCursor().blockNumber()
        cur = self.textCursor(); cur.beginEditBlock()
        for i, row in enumerate(rows):
            ln = start_line + i
            while self.document().blockCount() <= ln:      # 行が足りなければ足す
                end = QtGui.QTextCursor(self.document().lastBlock())
                end.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock)
                end.insertText("\n")
            blk = self.document().findBlockByNumber(ln)
            c = QtGui.QTextCursor(blk); n = len(blk.text())
            c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                           QtGui.QTextCursor.MoveMode.MoveAnchor, min(col, n))
            c.insertText(row)
        cur.endEditBlock()

    # ---- キー入力(補完 / インデント / 矩形 / 括弧) ----
    def keyPressEvent(self, ev):
        popup = self._completer.popup()
        if popup.isVisible() and ev.key() in (
                QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter,
                QtCore.Qt.Key.Key_Tab, QtCore.Qt.Key.Key_Escape,
                QtCore.Qt.Key.Key_Up, QtCore.Qt.Key.Key_Down):
            ev.ignore(); return                       # popup に処理させる
        mods = ev.modifiers(); key = ev.key()
        ctrl = mods & QtCore.Qt.KeyboardModifier.ControlModifier
        # 矩形が有効なとき Ctrl+C/X と Ctrl+V を横取り
        if self._block_ranges():
            if ctrl and key == QtCore.Qt.Key.Key_C:
                QtWidgets.QApplication.clipboard().setText(self._block_text()); return
            if ctrl and key == QtCore.Qt.Key.Key_X:
                QtWidgets.QApplication.clipboard().setText(self._block_text()); self._block_delete(); return
        if ctrl and key == QtCore.Qt.Key.Key_V and self._block_ranges():
            self._block_paste(); return
        if key == QtCore.Qt.Key.Key_F12:
            self.goto_definition(); return
        if ctrl and key == QtCore.Qt.Key.Key_Space:
            self._trigger_completion(); return
        # Tab = 4 スペース
        if key == QtCore.Qt.Key.Key_Tab and not (mods & QtCore.Qt.KeyboardModifier.ShiftModifier):
            self.insertPlainText("    "); return
        # Enter = インデント継承(+ ":" の後は増)
        if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            line = self.textCursor().block().text()
            indent = line[:len(line) - len(line.lstrip())]
            if line.rstrip().endswith(":"):
                indent += "    "
            super().keyPressEvent(ev); self.insertPlainText(indent); return
        # 括弧自動補完
        pairs = {"(": ")", "[": "]", "{": "}"}
        if ev.text() in pairs and not self.textCursor().hasSelection():
            super().keyPressEvent(ev)
            self.insertPlainText(pairs[ev.text()])
            c = self.textCursor(); c.movePosition(QtGui.QTextCursor.MoveOperation.Left)
            self.setTextCursor(c); return
        super().keyPressEvent(ev)
        # 入力に応じて補完を自動表示(識別子 2 文字以上)
        if ev.text() and (ev.text().isalnum() or ev.text() in "._"):
            if len(self._word_prefix()) >= 2:
                self._trigger_completion()
            else:
                popup.hide()
