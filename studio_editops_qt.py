# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_editops_qt — コードエディタの編集操作(Qt): 矩形選択・複数カーソル・行の操作・括弧・桁の目安の線。

既にある ``QPlainTextEdit``(Studio の ``ProgramEditor`` / ``CodeEditor`` / ``PyEditor``)へ **後から取り付ける**::

    import studio_editops_qt as eq
    ops = eq.install(editor, tr=tr, settings=settings_getter)     # 取り付け(2 度呼んでも 1 つ)
    ops.populate_menu(edit_menu)                                  # メニューへ同じ入口を足す(任意)
    eq.uninstall(editor)                                          # 外す(元の振る舞いへ戻る)

エディタの部品(クラス)は変えない。キーとマウスはイベントフィルタで受け、計算は ``studio_editops``(Qt なし)。

取り付けで変わる所(``install`` を呼ばないエディタは 1 つも変わらない)
* キー(既定は ``studio_editops.KEYMAP``。キーの設定で変えた今のキーは ``apply_bindings`` で受ける)と Alt + ドラッグ。補完の窓が出ている間の Tab / Enter / Esc / 上下は窓へ譲る。
* 箱の見た目は行ごとの ``ExtraSelection``。エディタの持ち主(``ProgramEditor._highlight`` や ``PyEditAssist``)が
  ``setExtraSelections`` を呼ぶたびに消えないよう、**この 1 つのエディタの** ``setExtraSelections`` を包み、
  持ち主の印の後ろに箱の印を足す(クラスは触らない。``uninstall`` で外れる)。
* 幅 0 の箱(複数行のカーソル)と桁の目安の線は、ビューポートに重ねた透明な部品(マウスは素通し)が描く。
* 右クリックのメニューに「矩形選択」「行の操作」「エディタの表示」を足す。

IME: 箱がある間の未確定の文字は 1 つのカーソルの所に出し、**確定した時に全部の行へ入れる**(1 回の Undo)。
"""
from __future__ import annotations

import atexit
import traceback
import weakref
from typing import Callable

from PySide6 import QtCore, QtGui, QtWidgets

import studio_editops as eo

_K = QtCore.Qt
_MODS = _K.ShiftModifier | _K.ControlModifier | _K.AltModifier | _K.MetaModifier
_PURE_MODIFIER_KEYS = (_K.Key_Shift, _K.Key_Control, _K.Key_Alt, _K.Key_Meta, _K.Key_AltGr, _K.Key_CapsLock,
                       _K.Key_NumLock, _K.Key_ScrollLock)
_POPUP_KEYS = (_K.Key_Tab, _K.Key_Backtab, _K.Key_Return, _K.Key_Enter, _K.Key_Escape, _K.Key_Up, _K.Key_Down,
               _K.Key_PageUp, _K.Key_PageDown)
#: Shift を押すと別の記号になるキー(``Shift+Alt+.`` は ``>`` として届く)。US 配列の対。JIS などは要実機確認。
_SHIFTED = {_K.Key_Period: _K.Key_Greater, _K.Key_Slash: _K.Key_Question, _K.Key_BracketRight: _K.Key_BraceRight,
            _K.Key_BracketLeft: _K.Key_BraceLeft, _K.Key_Backslash: _K.Key_Bar, _K.Key_Comma: _K.Key_Less,
            _K.Key_Semicolon: _K.Key_Colon, _K.Key_Apostrophe: _K.Key_QuoteDbl, _K.Key_Minus: _K.Key_Underscore,
            _K.Key_Equal: _K.Key_Plus, _K.Key_QuoteLeft: _K.Key_AsciiTilde}
SETTINGS_PREFIX = "editops/"
DEFAULT_RULERS = (79, 99)
#: これより行の多い文書では、対応する括弧を探さない(強調も、飛ぶ操作も)。
MAX_BRACKET_LINES = 20000

_LIVE: "weakref.WeakSet" = weakref.WeakSet()
#: キーの設定(studio_keymap)で変えた今のキー ``{操作: キーの並び}``。None = 表の既定。``apply_bindings`` が書く。
_BINDINGS: dict | None = None


def _detach_all_at_exit() -> None:
    """プロセスの終わり: 生きている EditOps のイベントフィルタを外す(PyEditAssist と同じ理由: 終了の途中で
    Python へ呼び戻されないように)。"""
    for ops in list(_LIVE):
        try:
            ops.detach()
        except Exception:                                       # noqa: BLE001 -- 終了の途中は何も投げない
            pass


atexit.register(_detach_all_at_exit)


class _DocLines:
    """文書の行を、行番号で引ける並びとして見せる(文面全体を毎回コピーしない)。"""

    def __init__(self, doc: QtGui.QTextDocument):
        self._doc = doc

    def __len__(self) -> int:
        return self._doc.blockCount()

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[k] for k in range(*i.indices(len(self)))]
        n = len(self)
        if i < 0:
            i += n
        if not 0 <= i < n:
            raise IndexError(i)
        return self._doc.findBlockByNumber(i).text()

    def __iter__(self):
        blk = self._doc.begin()
        while blk.isValid():
            yield blk.text()
            blk = blk.next()


class _Overlay(QtWidgets.QWidget):
    """ビューポートに重ねる透明な部品: 桁の目安の線と、複数のカーソルを描く。マウスは下へ通す。"""

    def __init__(self, ops: "EditOps"):
        super().__init__(ops.editor)
        self._ops = weakref.ref(ops)
        self.setObjectName("editopsOverlay")
        self.setAttribute(_K.WA_TransparentForMouseEvents, True)
        self.setAttribute(_K.WA_NoSystemBackground, True)
        self.setFocusPolicy(_K.NoFocus)

    def paintEvent(self, ev):                                   # noqa: N802 (Qt の名前)
        ops = self._ops()
        if ops is not None:
            ops.paint_overlay(self)


def _alive(obj) -> bool:
    """Qt の物 ``obj`` の C++ 側がまだ生きているか。"""
    try:
        import shiboken6                                        # noqa: PLC0415  (PySide6 に付いてくる)
        return obj is not None and shiboken6.isValid(obj)
    except ImportError:                                         # pragma: no cover
        return obj is not None


def _key_table(bindings: dict | None = None) -> dict:
    """``(キー, 修飾)`` → 操作。``studio_editops.KEYMAP`` から作る(``bindings`` に載った操作はそのキー)。

    2 打鍵の和音はここでは受けない(1 打ずつ判定している。キーの登録簿の検査が和音を断る)。
    """
    out = {}
    for b in eo.KEYMAP:
        for ks in (b.keys if bindings is None else bindings.get(b.command, b.keys)):
            seq = QtGui.QKeySequence(ks)
            if seq.count() != 1:
                continue
            comb = seq[0]
            key, mods = comb.key(), comb.keyboardModifiers() & _MODS
            out[(_int(key), _int(mods))] = b
            if key in _SHIFTED and mods & _K.ShiftModifier:
                out[(_int(_SHIFTED[key]), _int(mods))] = b
    return out


def _int(value) -> int:
    """Qt の列挙・フラグ → int(辞書の鍵をそろえる)。"""
    return int(getattr(value, "value", value))


class EditOps(QtCore.QObject):
    """1 つのエディタに付く編集操作の制御役。``install(editor)`` で作る。"""

    #: 箱・複数カーソルの状態が変わった(選びの数)。
    selectionChanged = QtCore.Signal(int)

    def __init__(self, editor: QtWidgets.QPlainTextEdit, tr: Callable | None = None, settings: Callable | None = None,
                 comment_prefix: str | None = None, tab_width: int = eo.TAB_WIDTH, indent_width: int = 4,
                 clipboard=None, on_message: Callable | None = None, ambiguous_wide: bool | None = None):
        super().__init__(editor)
        self.editor = editor
        self.tr = tr or (lambda s: s)
        self._settings = settings
        self._comment_prefix = comment_prefix
        self._tab_width = int(tab_width)
        self._ambiguous_wide = ambiguous_wide
        self._amb_cache: tuple = (None, {})
        self.indent_width = int(indent_width)
        self._clipboard = clipboard
        self.on_message = on_message
        self._carets: list = []
        self._primary = 0
        self._rect: tuple | None = None
        self._word_mode: str | None = None
        self._dragging = False
        self._editing = False
        self._sending = False
        self._base: list = list(editor.extraSelections())
        self._idle: list = []
        self._saved_cursor_width: int | None = None
        self._bracket_cache: tuple = (-1, None, [])
        self._howto = None
        self._howto_close = None                                # 「使い方」の窓のボタン(訳を付け直す)
        #: 残るメニュー(Edit メニュー)に足した入口 ``[(QMenu か QAction, 種類, 元)]``。言語・キーの変更で付け直す。
        self._menu_items: list = []
        self._palette_howto = None
        self._menu = None
        #: イベントフィルタの中で起きた最後の例外(無ければ None)。試験と不具合の調べに使う。
        self.last_error: Exception | None = None
        self._bindings: dict | None = dict(_BINDINGS) if _BINDINGS else None
        self._keys = _key_table(self._bindings)
        self._palette_actions: dict = {}
        self.rulers = self._load_rulers()
        self.trim_on_save = self._load_bool("trim_on_save", False)
        self._overlay = _Overlay(self)
        self._on = True
        # この 1 つのエディタの setExtraSelections を包む(持ち主の印 + 箱の印)。クラスは変えない。
        editor.setExtraSelections = self._set_base_selections
        if type(editor).contextMenuEvent is not QtWidgets.QPlainTextEdit.contextMenuEvent:
            editor.createStandardContextMenu = self._standard_menu_with_ours   # 自前のメニューを持つエディタ
        editor.installEventFilter(self)
        editor.viewport().installEventFilter(self)
        editor.cursorPositionChanged.connect(self._on_cursor)
        editor.updateRequest.connect(self._on_update_request)
        editor.document().contentsChange.connect(self._on_contents_change)
        _LIVE.add(self)
        self._place_overlay()
        self._refresh()

    # ------------------------------------------------------------------ #
    # 取り付け・取り外し
    # ------------------------------------------------------------------ #
    def detach(self) -> None:
        """エディタから外す(フィルタ・包んだ関数・重ねた部品)。何度呼んでもよい。"""
        if not self._on:
            return
        self._on = False
        try:
            import shiboken6                                    # noqa: PLC0415  (PySide6 に付いてくる)
            alive = shiboken6.isValid(self.editor)
        except ImportError:
            alive = True
        if not alive:
            return
        try:
            ed = self.editor
            self._deactivate(move_cursor=False)
            ed.removeEventFilter(self)
            ed.viewport().removeEventFilter(self)
            for name in ("setExtraSelections", "createStandardContextMenu"):
                if name in vars(ed):
                    delattr(ed, name)
            for sig, slot in ((ed.cursorPositionChanged, self._on_cursor), (ed.updateRequest, self._on_update_request),
                              (ed.document().contentsChange, self._on_contents_change)):
                try:
                    sig.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass
            ed.setExtraSelections(self._base)
            self._overlay.hide()
            self._overlay.setParent(None)
            self._overlay.deleteLater()
            if self._howto is not None:
                self._howto.close()
        except RuntimeError:                                    # C++ 側が先に消えた
            pass

    # ------------------------------------------------------------------ #
    # 設定
    # ------------------------------------------------------------------ #
    def _store(self):
        if self._settings is None:
            return None
        try:
            return self._settings()
        except Exception:                                       # noqa: BLE001 -- 設定が読めなくても編集は動く
            return None

    def _load_bool(self, key: str, default: bool) -> bool:
        s = self._store()
        if s is None:
            return default
        v = s.value(SETTINGS_PREFIX + key)
        if v is None:
            return default
        return v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "yes", "on")

    def _load_rulers(self) -> tuple:
        s = self._store()
        v = None if s is None else s.value(SETTINGS_PREFIX + "rulers")
        if v is None:
            return DEFAULT_RULERS
        try:
            return tuple(sorted({int(x) for x in str(v).replace(" ", "").split(",") if x and 0 < int(x) < 1000}))
        except ValueError:
            return DEFAULT_RULERS

    def _save(self, key: str, value) -> None:
        s = self._store()
        if s is not None:
            s.setValue(SETTINGS_PREFIX + key, value)

    def set_rulers(self, columns) -> None:
        """桁の目安の線を出す桁(空なら出さない)。設定へ覚える。"""
        self.rulers = tuple(sorted({int(c) for c in columns}))
        self._save("rulers", ",".join(str(c) for c in self.rulers))
        self._overlay.update()

    def set_trim_on_save(self, on: bool) -> None:
        """保存の時に行末の空白を落とすか(既定は落とさない)。設定へ覚える。"""
        self.trim_on_save = bool(on)
        self._save("trim_on_save", "true" if self.trim_on_save else "false")

    def before_save(self) -> int:
        """保存する側が、保存の直前に呼ぶ。設定が入なら行末の空白を落とし、落とした行数を返す。"""
        return self.trim_trailing() if self.trim_on_save else 0

    # ------------------------------------------------------------------ #
    # 文書との行き来
    # ------------------------------------------------------------------ #
    def _is_wide(self, ch: str) -> bool:
        """曖昧幅の文字 ``ch`` が、今の書体で全角に出るか(実際の送り幅で測る。書体ごとに覚える)。"""
        if self._ambiguous_wide is not None:
            return bool(self._ambiguous_wide)
        font = self.editor.font()
        key = font.toString()
        if self._amb_cache[0] != key:
            self._amb_cache = (key, {})
        got = self._amb_cache[1].get(ch)
        if got is None:
            fm = QtGui.QFontMetricsF(font)
            got = fm.horizontalAdvance(ch) > 1.5 * fm.horizontalAdvance("0")
            self._amb_cache[1][ch] = got
        return got

    @property
    def cols(self) -> eo.Columns:
        """桁の数え方(タブ幅と、曖昧幅の文字の測り方)。"""
        return eo.Columns(self._tab_width, self._is_wide)

    def _lines(self) -> _DocLines:
        return _DocLines(self.editor.document())

    def _pos(self, line: int, index: int) -> int:
        blk = self.editor.document().findBlockByNumber(line)
        return blk.position() + eo.cp_to_u16(blk.text(), index)

    def _line_index(self, pos: int) -> tuple:
        blk = self.editor.document().findBlock(pos)
        return blk.blockNumber(), eo.u16_to_cp(blk.text(), pos - blk.position())

    def _cursor_caret(self) -> eo.Caret | None:
        """本物のカーソルの選び(1 行の中なら Caret、行をまたぐなら None)。"""
        cur = self.editor.textCursor()
        la, ia = self._line_index(cur.anchor())
        lp, ip = self._line_index(cur.position())
        return eo.Caret(lp, ia, ip) if la == lp else None

    def _selected_lines(self) -> tuple:
        """本物のカーソルの選びが掛かる行(最後の行の行頭で終わる選びは、その行を含めない)。"""
        cur = self.editor.textCursor()
        doc = self.editor.document()
        first = doc.findBlock(cur.selectionStart())
        last = doc.findBlock(cur.selectionEnd())
        if cur.hasSelection() and last.blockNumber() > first.blockNumber() and cur.selectionEnd() == last.position():
            last = last.previous()
        return first.blockNumber(), last.blockNumber()

    def _apply(self, edits) -> None:
        """編集を 1 回の Undo にまとめて文書へ当てる。"""
        edits = sorted(edits, key=lambda e: (e.line, e.start), reverse=True)
        if not edits:
            return
        doc = self.editor.document()
        cur = QtGui.QTextCursor(doc)
        self._editing = True
        cur.beginEditBlock()
        try:
            for e in edits:
                blk = doc.findBlockByNumber(e.line)
                t = blk.text()
                cur.setPosition(blk.position() + eo.cp_to_u16(t, e.start))
                cur.setPosition(blk.position() + eo.cp_to_u16(t, e.end), QtGui.QTextCursor.KeepAnchor)
                cur.insertText(e.text)
        finally:
            cur.endEditBlock()
            self._editing = False

    def _say(self, text: str) -> None:
        fn = self.on_message or getattr(self.editor, "on_message", None)
        if fn is not None:
            fn(text)

    def _read_only(self) -> bool:
        return self.editor.isReadOnly()

    @property
    def comment_prefix(self) -> str:
        return self._comment_prefix or getattr(self.editor, "comment_prefix", None) or "#"

    def _assist(self):
        """このエディタに付いている PyEditAssist(色分け・補完)。無ければ None。"""
        for ch in self.editor.children():
            if ch is not self and hasattr(ch, "popup") and hasattr(ch, "theme") and hasattr(ch, "active"):
                return ch
        return None

    def _assist_active(self) -> bool:
        a = self._assist()
        return bool(a is not None and a.active)

    def _popup_visible(self) -> bool:
        a = self._assist()
        if a is not None and a.active and a.popup.isVisible():
            return True
        comp = getattr(self.editor, "_completer", None)
        return bool(comp is not None and comp.popup().isVisible())

    def colors(self) -> dict:
        """箱・カーソル・線の色。Python のモードは色分けの配色の表、それ以外はパレット。"""
        a = self._assist()
        if a is not None and a.active:
            th = a.theme
            return {"sel_bg": QtGui.QColor(th.selection_bg), "sel_fg": QtGui.QColor(th.selection_fg),
                    "fg": QtGui.QColor(th.fg), "bg": QtGui.QColor(th.bg)}
        pal = self.editor.palette()
        return {"sel_bg": pal.color(QtGui.QPalette.Highlight), "sel_fg": pal.color(QtGui.QPalette.HighlightedText),
                "fg": pal.color(QtGui.QPalette.Text), "bg": pal.color(QtGui.QPalette.Base)}

    # ------------------------------------------------------------------ #
    # 箱・複数カーソルの状態
    # ------------------------------------------------------------------ #
    def active(self) -> bool:
        """箱か複数カーソルがあるか。"""
        return bool(self._carets)

    def carets(self) -> list:
        """今の選び(``studio_editops.Caret`` の並び。行・位置の順)。"""
        return list(self._carets)

    def box(self) -> tuple | None:
        """箱の角 ``(固定の行, 固定の桁, 動く行, 動く桁)``。箱でなければ None。"""
        return self._rect

    def selected_texts(self) -> list:
        """各選びの文(上から)。"""
        lines = self._lines()
        return [lines[c.line][c.start:c.end] for c in self._carets]

    def _set_carets(self, carets, primary: int | None = None, rect: tuple | None = None) -> None:
        carets = eo.normalize_carets(carets)
        if not carets:
            self._deactivate()
            return
        if len({c.line for c in carets}) != len({c.line for c in self._carets}):
            self._say(self.tr(eo.MSG_BOX) % len({c.line for c in carets}))     # 状態行へ: 何行を選んでいるか
        self._carets = carets
        self._primary = max(0, min(len(carets) - 1, len(carets) - 1 if primary is None else primary))
        self._rect = rect
        ed = self.editor
        if self._saved_cursor_width is None:
            self._saved_cursor_width = ed.cursorWidth()
            ed.setCursorWidth(0)                               # カーソルは全部、重ねた部品が描く
        c = carets[self._primary]
        cur = ed.textCursor()
        cur.setPosition(self._pos(c.line, c.pos))
        self._editing = True
        try:
            ed.setTextCursor(cur)
        finally:
            self._editing = False
        self._refresh()
        self.selectionChanged.emit(len(carets))

    def _deactivate(self, move_cursor: bool = True) -> None:
        if not self._carets:
            return
        c = self._carets[self._primary]
        self._carets, self._rect, self._dragging = [], None, False
        ed = self.editor
        if self._saved_cursor_width is not None:
            ed.setCursorWidth(self._saved_cursor_width)
            self._saved_cursor_width = None
        if move_cursor and c.line < ed.document().blockCount():
            cur = ed.textCursor()
            cur.setPosition(self._pos(c.line, c.anchor))
            cur.setPosition(self._pos(c.line, c.pos), QtGui.QTextCursor.KeepAnchor)
            self._editing = True
            try:
                ed.setTextCursor(cur)
            finally:
                self._editing = False
        self._refresh()
        self.selectionChanged.emit(0)

    def clear(self) -> None:
        """箱・複数カーソルをやめて、カーソル 1 つへ戻る(選びは主のカーソルの物を残す)。"""
        self._deactivate()

    def set_box(self, a_line: int, a_col: int, c_line: int, c_col: int) -> None:
        """箱を置く。桁は見た目の桁(全角 = 2)。``a`` が固定の角、``c`` が動く角。"""
        lines = self._lines()
        n = len(lines)
        a_line, c_line = max(0, min(n - 1, a_line)), max(0, min(n - 1, c_line))
        a_col, c_col = max(0, a_col), max(0, c_col)
        carets = eo.box_carets(lines, a_line, a_col, c_line, c_col, self.cols)
        primary = min(range(len(carets)), key=lambda i: abs(carets[i].line - c_line))
        self._set_carets(carets, primary, (a_line, a_col, c_line, c_col))
        self._ensure_line_visible(c_line)

    def _rect_from_primary(self) -> None:
        """編集の後: 箱の桁を主のカーソルの今の桁へ合わせ直す(行はそのまま)。"""
        if self._rect is None or not self._carets:
            return
        c = self._carets[self._primary]
        t = self._lines()[c.line]
        self._rect = (self._rect[0], eo.col_of(t, c.anchor, self.cols),
                      self._rect[2], eo.col_of(t, c.pos, self.cols))

    def box_move(self, dline: int, dcol: int) -> None:
        """箱の動く角を動かす(Shift+Alt+矢印)。箱が無ければ、今のカーソル(1 行の中の選び)から始める。"""
        lines = self._lines()
        if self._rect is None:
            c = self._carets[self._primary] if self._carets else self._cursor_caret()
            if c is None:
                ln, i = self._line_index(self.editor.textCursor().position())
                c = eo.Caret(ln, i, i)
            t = lines[c.line]
            rect = (c.line, eo.col_of(t, c.anchor, self.cols), c.line, eo.col_of(t, c.pos, self.cols))
        else:
            rect = self._rect
        al, ac, cl, cc = rect
        cl = max(0, min(len(lines) - 1, cl + dline))
        if dcol:
            cc = eo.step_col(lines[cl], cc, dcol, self.cols)
        self.set_box(al, ac, cl, cc)

    def _ensure_line_visible(self, line: int) -> None:
        ed = self.editor
        blk = ed.document().findBlockByNumber(line)
        if not blk.isValid():
            return
        top = ed.blockBoundingGeometry(blk).translated(ed.contentOffset()).top()
        h = ed.blockBoundingRect(blk).height()
        vh = ed.viewport().height()
        sb = ed.verticalScrollBar()
        if top < 0:
            sb.setValue(line)
        elif top + h > vh and h > 0:
            sb.setValue(sb.value() + int((top + h - vh) / h) + 1)

    def _after_edit(self, carets) -> None:
        primary = self._primary if len(carets) == len(self._carets) else None
        rect = self._rect
        self._set_carets(carets, primary, rect)
        self._rect_from_primary()

    # ------------------------------------------------------------------ #
    # 箱・複数カーソルに対する編集
    # ------------------------------------------------------------------ #
    def insert_text(self, text: str) -> None:
        """全部の選びを ``text`` で置き換える(選びが空なら、その位置に入れる)。1 回の Undo。"""
        if not self._carets or self._read_only():
            return
        edits, new = eo.plan_replace(self._carets, [text] * len(self._carets))
        self._apply(edits)
        self._after_edit(new)

    def delete(self, backward: bool = False) -> None:
        """Delete / Backspace。選びがあればそれを、無ければ隣の 1 文字(まとまり)を消す。"""
        if not self._carets or self._read_only():
            return
        edits, new = eo.plan_delete(self._lines(), self._carets, backward)
        self._apply(edits)
        self._after_edit(new)

    def _clip_text(self) -> str:
        cb = self._clipboard or QtWidgets.QApplication.clipboard()
        return cb.text()

    def _clip_set(self, text: str) -> None:
        cb = self._clipboard or QtWidgets.QApplication.clipboard()
        cb.setText(text)

    def copy(self) -> str:
        """選びを行ごとに改行で繋いでクリップボードへ。全部が幅 0 なら、その行を丸ごと。"""
        if not self._carets:
            return ""
        lines = self._lines()
        if all(c.empty for c in self._carets):
            rows = [lines[ln] for ln in sorted({c.line for c in self._carets})]
        else:
            rows = self.selected_texts()
        text = "\n".join(rows)
        self._clip_set(text)
        return text

    def cut(self) -> None:
        """コピーして消す。全部が幅 0 なら何も消さない。"""
        if not self._carets or self._read_only():
            return
        if all(c.empty for c in self._carets):
            self.copy()
            return
        self.copy()
        self.insert_text("")

    def paste(self) -> str:
        """貼り付け。配り方(``spread`` / ``same`` / ``full``。``studio_editops.paste_rows``)を返す。"""
        if not self._carets or self._read_only():
            return ""
        mode, texts = eo.paste_rows(self._clip_text(), len(self._carets))
        edits, new = eo.plan_replace(self._carets, texts)
        self._apply(edits)
        if mode == "full":                                     # 行が増えた: カーソルは 1 つへ戻す
            self._deactivate(move_cursor=False)
        else:
            self._after_edit(new)
        return mode

    def indent(self, outdent: bool = False) -> None:
        """字下げ。箱・複数カーソルがあればその行、無ければ選んだ行(選びが無ければカーソルの行)。"""
        if self._read_only():
            return
        lines = self._lines()
        if self._carets:
            rows = {c.line for c in self._carets}
        else:
            first, last = self._selected_lines()
            rows = set(range(first, last + 1))
        edits = (eo.plan_outdent if outdent else eo.plan_indent)(lines, rows, self.indent_width)
        if not edits:
            return
        self._apply(edits)
        if self._carets:
            self._after_edit(eo.shift_carets(self._carets, edits))

    def soft_tab(self) -> None:
        """Tab: 次の字下げの位置まで空白を入れる(選びがあれば置き換える)。"""
        if self._read_only():
            return
        w = self.indent_width
        if self._carets:
            lines = self._lines()
            texts = [" " * (w - eo.col_of(lines[c.line], c.start, self.cols) % w) for c in self._carets]
            edits, new = eo.plan_replace(self._carets, texts)
            self._apply(edits)
            self._after_edit(new)
            return
        cur = self.editor.textCursor()
        ln, i = self._line_index(cur.selectionStart())
        col = eo.col_of(self._lines()[ln], i, self.cols)
        cur.insertText(" " * (w - col % w))
        self.editor.setTextCursor(cur)

    def move(self, how: str, select: bool = False) -> None:
        """全部のカーソルを左右・行頭・行末へ動かす。"""
        if self._carets:
            new = eo.move_carets(self._lines(), self._carets, how, select)
            primary = self._primary if len(new) == len(self._carets) else None
            self._set_carets(new, primary, self._rect)
            self._rect_from_primary()

    def add_next_occurrence(self) -> bool:
        """選んでいる語の次の一致を選びに足す。選びが無ければ、まずカーソルの語を選ぶ。足せたら True。"""
        lines = self._lines()
        if not self._carets:
            c = self._cursor_caret()
            if c is None:
                return False
            if c.empty:
                w = eo.word_at(lines[c.line], c.pos)
                if w is None:
                    return False
                cur = self.editor.textCursor()
                cur.setPosition(self._pos(c.line, w[0]))
                cur.setPosition(self._pos(c.line, w[1]), QtGui.QTextCursor.KeepAnchor)
                self.editor.setTextCursor(cur)
                self._word_mode = lines[c.line][w[0]:w[1]]
                return True
            carets, primary = [eo.Caret(c.line, c.start, c.end)], 0
        else:
            carets, primary = list(self._carets), self._primary
        last = carets[primary]
        needle = lines[last.line][last.start:last.end]
        if not needle:
            return False
        taken = {(c.line, c.start) for c in carets}
        hit = eo.next_occurrence(lines, needle, last.line, last.end, taken, whole_word=(self._word_mode == needle))
        if hit is None:
            self._say(self.tr(eo.MSG_NO_OCCURRENCE))
            return False
        new = eo.Caret(hit[0], hit[1], hit[1] + len(needle))
        carets = eo.normalize_carets(carets + [new])
        self._set_carets(carets, carets.index(new), None)
        self._ensure_line_visible(new.line)
        return True

    # ------------------------------------------------------------------ #
    # 行の操作(カーソル 1 つの時)
    # ------------------------------------------------------------------ #
    def _replace_lines(self, first: int, last: int, new_lines) -> None:
        doc = self.editor.document()
        cur = QtGui.QTextCursor(doc)
        b0, b1 = doc.findBlockByNumber(first), doc.findBlockByNumber(last)
        self._editing = True
        cur.beginEditBlock()
        try:
            cur.setPosition(b0.position())
            cur.setPosition(b1.position() + b1.length() - 1, QtGui.QTextCursor.KeepAnchor)
            cur.insertText("\n".join(new_lines))
        finally:
            cur.endEditBlock()
            self._editing = False

    def _restore_selection(self, anchor: int, pos: int) -> None:
        cur = self.editor.textCursor()
        end = self.editor.document().characterCount() - 1
        cur.setPosition(max(0, min(end, anchor)))
        cur.setPosition(max(0, min(end, pos)), QtGui.QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cur)

    def duplicate_lines(self) -> None:
        """選んだ行(選びが無ければカーソルの行)を下へ複製する。カーソルは複製の側へ移る。"""
        if self._read_only():
            return
        self.clear()
        first, last = self._selected_lines()
        cur = self.editor.textCursor()
        a, p = cur.anchor(), cur.position()
        block = self._lines()[first:last + 1]
        self._replace_lines(first, last, block + block)
        delta = sum(eo.u16_len(t) + 1 for t in block)
        self._restore_selection(a + delta, p + delta)

    def move_lines(self, delta: int) -> bool:
        """選んだ行を 1 行上(-1)・下(+1)へ動かす。端なら何もしない。"""
        if self._read_only():
            return False
        self.clear()
        first, last = self._selected_lines()
        lines = self._lines()
        plan = eo.reorder_lines(lines, first, last, delta)
        if plan is None:
            return False
        cur = self.editor.textCursor()
        a, p = cur.anchor(), cur.position()
        shift = (eo.u16_len(lines[last + 1]) + 1) if delta > 0 else -(eo.u16_len(lines[first - 1]) + 1)
        self._replace_lines(plan[0], plan[1], plan[2])
        self._restore_selection(a + shift, p + shift)
        return True

    def delete_lines(self) -> None:
        """選んだ行(選びが無ければカーソルの行)を消す。"""
        if self._read_only():
            return
        self.clear()
        first, last = self._selected_lines()
        doc = self.editor.document()
        b0, b1 = doc.findBlockByNumber(first), doc.findBlockByNumber(last)
        cur = QtGui.QTextCursor(doc)
        if b1.next().isValid():
            cur.setPosition(b0.position())
            cur.setPosition(b1.next().position(), QtGui.QTextCursor.KeepAnchor)
        elif first > 0:
            prev = b0.previous()
            cur.setPosition(prev.position() + prev.length() - 1)
            cur.setPosition(b1.position() + b1.length() - 1, QtGui.QTextCursor.KeepAnchor)
        else:
            cur.select(QtGui.QTextCursor.Document)
        self._editing = True
        try:
            cur.removeSelectedText()
        finally:
            self._editing = False
        cur.movePosition(QtGui.QTextCursor.StartOfBlock)
        self.editor.setTextCursor(cur)

    def toggle_comment(self) -> int:
        """行コメントの付け外し。エディタが自分の ``toggle_comment`` を持てばそれを呼ぶ。触った行数を返す。"""
        own = getattr(self.editor, "toggle_comment", None)
        if own is not None:
            return int(own() or 0)
        if self._read_only():
            return 0
        self.clear()
        first, last = self._selected_lines()
        edits = eo.plan_toggle_comment(self._lines(), range(first, last + 1), self.comment_prefix)
        self._apply(edits)
        return len(edits)

    def trim_trailing(self) -> int:
        """全部の行の行末の空白を落とす(1 回の Undo)。落とした行数を返す。"""
        if self._read_only():
            return 0
        self.clear()
        edits = eo.strip_trailing_edits(self._lines())
        self._apply(edits)
        self._say(self.tr(eo.MSG_TRIMMED) % len(edits))
        return len(edits)

    def _brackets(self) -> list:
        doc = self.editor.document()
        key = (doc.revision(), self.comment_prefix)
        if self._bracket_cache[:2] != key:
            self._bracket_cache = (key[0], key[1], eo.bracket_table(self._lines(), self.comment_prefix))
        return self._bracket_cache[2]

    def matching_bracket(self) -> tuple | None:
        """カーソルの隣の括弧と相手 ``(行, 位置, 相手の行, 相手の位置)``。"""
        if self.editor.document().blockCount() > MAX_BRACKET_LINES:
            return None                                        # とても長い文書: 打つたびに全部を走査しない
        ln, i = self._line_index(self.editor.textCursor().position())
        return eo.match_bracket(self._brackets(), ln, i)

    def jump_to_bracket(self) -> bool:
        """対応する括弧の手前へ飛ぶ(もう一度押すと戻る)。無ければ状態行に 1 行。"""
        self.clear()
        m = self.matching_bracket()
        if m is None:
            self._say(self.tr(eo.MSG_NO_BRACKET))
            return False
        cur = self.editor.textCursor()
        cur.setPosition(self._pos(m[2], m[3]))
        self.editor.setTextCursor(cur)
        self.editor.ensureCursorVisible()
        return True

    # ------------------------------------------------------------------ #
    # 操作の入口(キー・メニュー・パレットが同じ所を通る)
    # ------------------------------------------------------------------ #
    def run(self, command: str) -> bool:
        """操作を名前で実行する(``studio_editops.KEYMAP`` の ``command``)。知らない名前は ``ValueError``。"""
        if command == "box.up":
            self.box_move(-1, 0)
        elif command == "box.down":
            self.box_move(1, 0)
        elif command == "box.left":
            self.box_move(0, -1)
        elif command == "box.right":
            self.box_move(0, 1)
        elif command == "box.cancel":
            self.clear()
        elif command == "multi.add_next":
            self.add_next_occurrence()
        elif command == "line.duplicate":
            self.duplicate_lines()
        elif command == "line.move_up":
            self.move_lines(-1)
        elif command == "line.move_down":
            self.move_lines(1)
        elif command == "line.delete":
            self.delete_lines()
        elif command == "line.comment":
            self.toggle_comment()
        elif command == "line.indent":
            self._tab(False)
        elif command == "line.outdent":
            self._tab(True)
        elif command == "bracket.jump":
            self.jump_to_bracket()
        elif command == "edit.trim":
            self.trim_trailing()
        else:
            raise ValueError("知らない操作: %r" % (command,))
        return True

    def _tab(self, back: bool) -> None:
        if back:
            self.indent(outdent=True)
        elif self._carets:
            if any(not c.empty for c in self._carets):
                self.indent()
            else:
                self.soft_tab()
        else:
            first, last = self._selected_lines()
            if last > first:
                self.indent()
            else:
                self.soft_tab()

    def _binding_for(self, ev) -> eo.Binding | None:
        key, mods = ev.key(), ev.modifiers() & _MODS
        if key == _K.Key_Backtab:
            key, mods = _K.Key_Tab, mods | _K.ShiftModifier
        b = self._keys.get((_int(key), _int(mods)))
        if b is None:
            return None
        if b.when == "box" and not self._carets:
            return None
        if b.when == "no_own_comment" and hasattr(self.editor, "toggle_comment"):
            return None
        return b

    def _legacy_completion_idle(self) -> bool:
        """op 名の古い補完(``ProgramEditor`` の QCompleter)が有効で、まだ窓が出ていないか。"""
        ed = self.editor
        comp = getattr(ed, "_completer", None)
        return bool(comp is not None and getattr(ed, "legacy_completion", False) and not comp.popup().isVisible())

    def _hide_popups(self) -> None:
        a = self._assist()
        if a is not None and a.popup.isVisible():
            a.popup.hide()
        comp = getattr(self.editor, "_completer", None)
        if comp is not None and comp.popup().isVisible():
            comp.popup().hide()

    def _handle_key(self, ev) -> bool:
        key = ev.key()
        mods = ev.modifiers() & _MODS
        plain = mods in (_K.NoModifier, _K.ShiftModifier)
        if key in _PURE_MODIFIER_KEYS:
            # 修飾キーだけの押下は文面を変えない。ProgramEditor はどのキーでもカーソル下の語の補完の窓を出すので、
            # そのまま渡すと Alt を押した時点で窓が開き、続く矢印キーを窓が取ってしまう。ここで止める。
            return self._legacy_completion_idle()
        if plain and key in _POPUP_KEYS and self._popup_visible():
            return False                                       # 補完の窓が受ける(修飾なしの Tab / Enter / Esc / 上下)
        b = self._binding_for(ev)
        if b is not None:
            self._hide_popups()
            self.run(b.command)
            return True
        if not self._carets:
            return False
        if ev.matches(QtGui.QKeySequence.Copy):
            self.copy()
        elif ev.matches(QtGui.QKeySequence.Cut):
            self.cut()
        elif ev.matches(QtGui.QKeySequence.Paste):
            self.paste()
        elif key in (_K.Key_Backspace, _K.Key_Delete) and plain:
            self.delete(backward=(key == _K.Key_Backspace))
        elif key in (_K.Key_Left, _K.Key_Right, _K.Key_Home, _K.Key_End) and plain:
            self.move({_K.Key_Left: "left", _K.Key_Right: "right", _K.Key_Home: "home", _K.Key_End: "end"}[key],
                      select=bool(mods & _K.ShiftModifier))
        else:
            text = ev.text()
            ctrl_only = bool(mods & _K.ControlModifier) != bool(mods & _K.AltModifier)
            if text and text.isprintable() and not ctrl_only and not mods & _K.MetaModifier:
                self.insert_text(text)
            else:
                self.clear()                                   # それ以外のキー: カーソル 1 つへ戻して、元の動作へ
                return False
        return True

    # ------------------------------------------------------------------ #
    # マウス
    # ------------------------------------------------------------------ #
    def _line_col_at(self, vp_pos: QtCore.QPoint) -> tuple:
        """ビューポートの座標 → ``(行, 見た目の桁)``。行末より右は、空白の幅で桁を数える。"""
        ed = self.editor
        cur = ed.cursorForPosition(vp_pos)
        blk = cur.block()
        t = blk.text()
        i = eo.u16_to_cp(t, cur.positionInBlock())
        col = eo.col_of(t, i, self.cols)
        if i >= len(t):
            x0 = ed.cursorRect(cur).x()
            w = QtGui.QFontMetricsF(ed.font()).horizontalAdvance(" ")
            if w > 0 and vp_pos.x() > x0:
                col += int((vp_pos.x() - x0) / w + 0.5)
        return blk.blockNumber(), col

    def _mouse(self, ev) -> bool:
        et = ev.type()
        if et == QtCore.QEvent.MouseButtonPress:
            mods = ev.modifiers() & _MODS
            if ev.button() == _K.LeftButton and mods in (_K.AltModifier, _K.AltModifier | _K.ShiftModifier):
                line, col = self._line_col_at(ev.position().toPoint())
                if mods & _K.ShiftModifier:
                    if self._rect is not None:
                        al, ac = self._rect[0], self._rect[1]
                    else:
                        ln, i = self._line_index(self.editor.textCursor().anchor())
                        al, ac = ln, eo.col_of(self._lines()[ln], i, self.cols)
                else:
                    al, ac = line, col
                self.editor.setFocus()
                self.set_box(al, ac, line, col)
                self._dragging = True
                return True
            if self._carets and ev.button() != _K.RightButton:
                self._deactivate(move_cursor=False)            # 普通のクリック: 箱をやめる(クリックは元の動作へ)
            return False
        if et == QtCore.QEvent.MouseMove and self._dragging:
            if not ev.buttons() & _K.LeftButton or self._rect is None:
                self._dragging = False
                return False
            line, col = self._line_col_at(ev.position().toPoint())
            if (line, col) != (self._rect[2], self._rect[3]):
                self.set_box(self._rect[0], self._rect[1], line, col)
            return True
        if et == QtCore.QEvent.MouseButtonRelease and self._dragging:
            self._dragging = False
            return True
        if et == QtCore.QEvent.MouseButtonDblClick and ev.modifiers() & _K.AltModifier:
            return True
        return False

    # ------------------------------------------------------------------ #
    # イベント
    # ------------------------------------------------------------------ #
    def eventFilter(self, obj, ev):                             # noqa: N802 (Qt の名前)
        if not self._on or self._sending:
            return False
        try:
            return self._filter(obj, ev)
        except Exception as exc:                                # noqa: BLE001 -- フィルタの中の例外は Qt を落とす
            self.last_error = exc                               # 隠さない: 標準エラーへ全文、状態行へ 1 行
            traceback.print_exc()
            self._say("editops: %s: %s" % (type(exc).__name__, exc))
            return False

    def _filter(self, obj, ev) -> bool:
        et = ev.type()
        ed = self.editor
        if obj is ed:
            if et == QtCore.QEvent.ShortcutOverride:
                plain = (ev.modifiers() & _MODS) in (_K.NoModifier, _K.ShiftModifier)
                if plain and ev.key() in _POPUP_KEYS and self._popup_visible():
                    return False
                if self._binding_for(ev) is not None:
                    ev.accept()                                # 窓の同じキーより先に、このエディタが受ける
                    return True
            elif et == QtCore.QEvent.KeyPress:
                return self._handle_key(ev)
            elif et == QtCore.QEvent.InputMethod and self._carets:
                commit = ev.commitString()
                if commit:
                    self._send(QtGui.QInputMethodEvent())       # 未確定の表示を消してから、全部の行へ入れる
                    self.insert_text(commit)
                else:
                    self._send(ev)                              # 未確定の文字: 主のカーソルの所に出すだけ(箱は保つ)
                return True
            elif et == QtCore.QEvent.Resize:
                QtCore.QTimer.singleShot(0, self._place_overlay)
            elif et == QtCore.QEvent.ContextMenu and self._own_context_menu():
                self._show_context_menu(ev.globalPos(), ed.viewport().mapFromGlobal(ev.globalPos()))
                return True
        elif obj is ed.viewport():
            if et in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseMove, QtCore.QEvent.MouseButtonRelease,
                      QtCore.QEvent.MouseButtonDblClick):
                return self._mouse(ev)
            if et in (QtCore.QEvent.Resize, QtCore.QEvent.Move):
                self._place_overlay()
            elif et == QtCore.QEvent.ContextMenu and self._own_context_menu():
                self._show_context_menu(ev.globalPos(), ev.pos())
                return True
        return False

    def _send(self, ev) -> None:
        """イベントをエディタへそのまま届ける(このフィルタは通さない。その間の文書の合図では箱をやめない)。"""
        was = self._editing
        self._sending = self._editing = True
        try:
            QtCore.QCoreApplication.sendEvent(self.editor, ev)
        finally:
            self._sending = False
            self._editing = was

    def _on_cursor(self) -> None:
        if not self._editing:
            self._refresh()

    def _on_update_request(self, _rect, _dy) -> None:
        self._overlay.update()

    def _on_contents_change(self, _pos, _removed, _added) -> None:
        if self._carets and not self._editing:
            self._deactivate(move_cursor=False)                # 他の所が文面を変えた: 古い位置は使わない

    # ------------------------------------------------------------------ #
    # 見た目(ExtraSelection と重ねた部品)
    # ------------------------------------------------------------------ #
    def _set_base_selections(self, selections) -> None:
        """エディタの持ち主が ``setExtraSelections`` を呼んだ: 覚えて、箱の印を後ろに足して出す。"""
        self._base = list(selections)
        self._push()

    def _push(self) -> None:
        QtWidgets.QPlainTextEdit.setExtraSelections(self.editor, self._base + self._idle + self.box_selections())

    def box_selections(self) -> list:
        """箱の印(幅のある選びごとに 1 つの ``ExtraSelection``)。"""
        if not self._carets:
            return []
        col = self.colors()
        fmt = QtGui.QTextCharFormat()
        fmt.setBackground(col["sel_bg"])
        fmt.setForeground(col["sel_fg"])
        out = []
        doc = self.editor.document()
        for c in self._carets:
            if c.empty:
                continue
            s = QtWidgets.QTextEdit.ExtraSelection()
            cur = QtGui.QTextCursor(doc)
            cur.setPosition(self._pos(c.line, c.start))
            cur.setPosition(self._pos(c.line, c.end), QtGui.QTextCursor.KeepAnchor)
            s.cursor = cur
            s.format = fmt
            out.append(s)
        return out

    def _idle_selections(self) -> list:
        """カーソル 1 つの時の印: 今の行(持ち主が描かないエディタだけ)と、対応する括弧(色分けが無い時だけ)。"""
        ed = self.editor
        out = []
        col = self.colors()
        if not (hasattr(ed, "_highlight") or self._assist() is not None):
            s = QtWidgets.QTextEdit.ExtraSelection()
            bg = col["bg"]
            fmt = QtGui.QTextCharFormat()
            fmt.setBackground(bg.lighter(130) if bg.lightness() < 128 else bg.darker(106))
            fmt.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            cur = ed.textCursor()
            cur.clearSelection()
            s.cursor = cur
            s.format = fmt
            out.append(s)
        if not self._assist_active() and not self._carets:
            m = self.matching_bracket()
            if m is not None:
                fmt = QtGui.QTextCharFormat()
                c2 = QtGui.QColor(col["sel_bg"])
                c2.setAlpha(110)
                fmt.setBackground(c2)
                fmt.setFontWeight(QtGui.QFont.Weight.Bold)
                for ln, i in ((m[0], m[1]), (m[2], m[3])):
                    s = QtWidgets.QTextEdit.ExtraSelection()
                    cur = QtGui.QTextCursor(ed.document())
                    cur.setPosition(self._pos(ln, i))
                    cur.setPosition(self._pos(ln, i + 1), QtGui.QTextCursor.KeepAnchor)
                    s.cursor = cur
                    s.format = fmt
                    out.append(s)
        return out

    def _refresh(self) -> None:
        self._idle = self._idle_selections()
        self._push()
        self._overlay.update()

    def _place_overlay(self) -> None:
        if not self._on:
            return
        self._overlay.setGeometry(self.editor.viewport().geometry())
        self._overlay.raise_()
        self._overlay.show()

    def char_advance(self) -> float:
        """半角 1 文字の送り幅(px)。桁の目安の線と、行末より右の桁の計算に使う。"""
        return QtGui.QFontMetricsF(self.editor.font()).horizontalAdvance("0" * 64) / 64.0

    def ruler_x(self, column: int) -> float:
        """桁 ``column`` の線の x(ビューポートの座標)。"""
        ed = self.editor
        return ed.contentOffset().x() + ed.document().documentMargin() + column * self.char_advance()

    def caret_rects(self) -> list:
        """各カーソルの矩形(ビューポートの座標)。"""
        ed = self.editor
        out = []
        for c in self._carets:
            cur = QtGui.QTextCursor(ed.document())
            cur.setPosition(self._pos(c.line, c.pos))
            r = ed.cursorRect(cur)
            out.append(QtCore.QRect(r.x(), r.y(), max(1, self._saved_cursor_width or 1), r.height()))
        return out

    def paint_overlay(self, widget: QtWidgets.QWidget) -> None:
        """重ねた部品の描画(桁の目安の線 → カーソル)。"""
        p = QtGui.QPainter(widget)
        col = self.colors()
        line = QtGui.QColor(col["fg"])
        line.setAlpha(46)
        h = widget.height()
        for c in self.rulers:
            x = int(round(self.ruler_x(c)))
            if 0 <= x < widget.width():
                p.fillRect(x, 0, 1, h, line)
        for r in self.caret_rects():
            if r.bottom() >= 0 and r.top() <= h:
                p.fillRect(r, col["fg"])
        p.end()

    # ------------------------------------------------------------------ #
    # メニュー(右クリック・Edit メニュー・コマンドパレット)
    # ------------------------------------------------------------------ #
    def _own_context_menu(self) -> bool:
        """右クリックのメニューをこちらで出すか(エディタが自前のメニューを持たず、既定の方針の時だけ)。"""
        ed = self.editor
        return (ed.contextMenuPolicy() == _K.DefaultContextMenu
                and type(ed).contextMenuEvent is QtWidgets.QPlainTextEdit.contextMenuEvent)

    def _standard_menu_with_ours(self, *args):
        menu = QtWidgets.QPlainTextEdit.createStandardContextMenu(self.editor, *args)
        self.populate_menu(menu, follow=False)                 # 毎回作るメニュー: 作る時の言語とキーで足りる
        return menu

    def build_context_menu(self, vp_pos: QtCore.QPoint | None = None) -> QtWidgets.QMenu:
        """右クリックのメニュー(エディタの標準の項目 + 矩形選択・行の操作・エディタの表示)。"""
        args = () if vp_pos is None else (vp_pos,)
        menu = QtWidgets.QPlainTextEdit.createStandardContextMenu(self.editor, *args)
        self.populate_menu(menu, follow=False)
        return menu

    def _show_context_menu(self, global_pos, vp_pos) -> None:
        menu = self.build_context_menu(vp_pos)
        self._menu = menu                                      # 出ている間、Python の側で持っておく
        menu.popup(global_pos)

    def keys_for(self, command: str) -> tuple:
        """操作 ``command`` の今のキー(キーの設定で変えていなければ表の既定)。"""
        for b in eo.KEYMAP:
            if b.command == command:
                if self._bindings is not None and command in self._bindings:
                    return tuple(self._bindings[command])
                return tuple(b.keys)
        raise ValueError("知らない操作: %r" % (command,))

    def set_bindings(self, bindings: dict | None) -> None:
        """今のキーを ``{操作: キーの並び}`` にする(None で表の既定)。メニュー・パレットの文もそろえる。"""
        known = {b.command for b in eo.KEYMAP}
        if bindings is not None:
            bad = sorted(set(bindings) - known)
            if bad:
                raise ValueError("知らない操作: %s" % ", ".join(bad))
            bindings = {c: tuple(k) for c, k in bindings.items()}
        self._bindings = bindings
        self._keys = _key_table(bindings)
        self.retranslate()                                     # 残るメニュー・パレット・「使い方」の文を今のキーで

    def _label(self, binding: eo.Binding) -> str:
        text = self.tr(binding.title)
        keys = self.keys_for(binding.command)
        return text + "\t" + keys[0] if keys else text

    def _tip(self, binding: eo.Binding) -> str:
        keys = self.keys_for(binding.command)
        return "%s (%s)" % (self.tr(binding.title), " / ".join(keys)) if keys else self.tr(binding.title)

    def _command_action(self, menu, binding: eo.Binding, follow: bool = False) -> QtGui.QAction:
        a = QtGui.QAction(self._label(binding), menu)
        menu.addAction(a)
        a.setObjectName("editops:" + binding.command)
        if self.keys_for(binding.command):
            a.setToolTip(self._tip(binding))
        a.triggered.connect(lambda _=False, c=binding.command: (self.editor.setFocus(), self.run(c)))
        if follow:
            self._menu_items.append((a, "binding", binding))
        return a

    def populate_menu(self, menu: QtWidgets.QMenu, follow: bool = True) -> list:
        """``menu`` に「矩形選択」「行の操作」「エディタの表示」の 3 つのサブメニューを足す。足したサブメニューを返す。

        ``follow``(既定): 足した入口を覚えておき、``retranslate``(言語の切り替え・キーの変更の後)で文とキーを
        付け直す。作ったまま残るメニュー(Edit メニュー)用。その場で作って捨てるメニューは ``follow=False``。
        """
        tr = self.tr
        menu.addSeparator()
        menu.setToolTipsVisible(True)
        box = QtWidgets.QMenu(tr(eo.MENU_BOX), menu)
        menu.addMenu(box)
        box.setObjectName("editops:menu.box")
        how = QtGui.QAction(tr(eo.ACT_HOWTO), box)
        box.addAction(how)
        how.setObjectName("editops:howto")
        how.triggered.connect(lambda _=False: self.show_howto())
        box.addSeparator()
        line = QtWidgets.QMenu(tr(eo.MENU_LINE), menu)
        menu.addMenu(line)
        line.setObjectName("editops:menu.line")
        for b in eo.KEYMAP:
            if b.when == "box" and not self._carets:
                continue
            self._command_action(box if b.group == "box" else line, b, follow)
        disp = QtWidgets.QMenu(tr(eo.MENU_DISPLAY), menu)
        menu.addMenu(disp)
        disp.setObjectName("editops:menu.display")
        r = QtGui.QAction(tr(eo.ACT_RULERS), disp)
        disp.addAction(r)
        r.setObjectName("editops:rulers")
        r.setCheckable(True)
        r.setChecked(bool(self.rulers))
        r.toggled.connect(lambda on: self.set_rulers(DEFAULT_RULERS if on else ()))
        t = QtGui.QAction(tr(eo.ACT_TRIM_ON_SAVE), disp)
        disp.addAction(t)
        t.setObjectName("editops:trim_on_save")
        t.setCheckable(True)
        t.setChecked(self.trim_on_save)
        t.toggled.connect(self.set_trim_on_save)
        for m in (box, line, disp):
            m.setToolTipsVisible(True)
        if follow:
            self._menu_items = [it for it in self._menu_items if _alive(it[0])]
            self._menu_items += [(box, "menu", eo.MENU_BOX), (line, "menu", eo.MENU_LINE),
                                 (disp, "menu", eo.MENU_DISPLAY), (how, "text", eo.ACT_HOWTO),
                                 (r, "text", eo.ACT_RULERS), (t, "text", eo.ACT_TRIM_ON_SAVE)]
        return [box, line, disp]

    def retranslate(self) -> int:
        """今の言語と今のキーで文を付け直す: 残るメニューに足した入口(``populate_menu``)・コマンドパレットの入口
        (``command_actions``)・出ている「使い方」の窓。言語の切り替えとキーの変更の後に呼ぶ(キーの部品
        ``studio_keymap_qt`` が呼ぶ。単体で使う時は本体の言語の切り替えの後に ``retranslate_all()``)。

        付け直したメニューの入口の数を返す(消えたメニューの入口は忘れる)。
        """
        keep = []
        for obj, kind, src in self._menu_items:
            if not _alive(obj):
                continue
            keep.append((obj, kind, src))
            if kind == "menu":
                obj.setTitle(self.tr(src))
            elif kind == "binding":
                obj.setText(self._label(src))
                obj.setToolTip(self._tip(src))
            else:
                obj.setText(self.tr(src))
        self._menu_items = keep
        for b in eo.KEYMAP:
            a = self._palette_actions.get(b.command)
            if a is None:
                continue
            if not _alive(a):                                   # QAction が先に消えた
                self._palette_actions.pop(b.command, None)
                continue
            a.setText(self.tr(b.title))
            a.setToolTip(self._tip(b))
        if self._palette_howto is not None and _alive(self._palette_howto):
            self._palette_howto.setText(self.tr(eo.ACT_HOWTO))
        if self._howto is not None and _alive(self._howto):
            self._fill_howto()
        return len(keep)

    def command_actions(self, parent: QtCore.QObject | None = None) -> dict:
        """コマンドパレットに載せる ``{名前: QAction}``(キーは付けない: キーはこの部品のフィルタが受ける)。"""
        out = {}
        for b in eo.KEYMAP:
            a = QtGui.QAction(self.tr(b.title), parent or self)
            a.setObjectName("editops:" + b.command)
            keys = self.keys_for(b.command)
            if keys:
                a.setToolTip("%s (%s)" % (self.tr(b.title), " / ".join(keys)))
            a.triggered.connect(lambda _=False, c=b.command: (self.editor.setFocus(), self.run(c)))
            out["editops_" + b.command.replace(".", "_")] = a
            self._palette_actions[b.command] = a
        a = QtGui.QAction(self.tr(eo.ACT_HOWTO), parent or self)
        a.setObjectName("editops:howto")
        a.triggered.connect(lambda _=False: self.show_howto())
        out["editops_howto"] = a
        self._palette_howto = a
        return out

    def howto_text(self) -> str:
        """「矩形選択の使い方」の文(今の言語)。キーの設定で変えたキーがあれば、末尾にその一覧を足す
        (本文は既定のキーで書いてある)。"""
        text = self.tr(eo.HOWTO_TEXT)
        changed = [b for b in eo.KEYMAP if self.keys_for(b.command) != tuple(b.keys)]
        if changed:
            text += "\n\n" + self.tr(eo.MSG_KEYS_CHANGED) + "\n" + "\n".join(
                "%s: %s" % (self.tr(b.title), " / ".join(self.keys_for(b.command)) or "—") for b in changed)
        return text

    def _fill_howto(self) -> None:
        self._howto.setWindowTitle(self.tr(eo.HOWTO_TITLE))
        self._howto.setText(self.howto_text())
        if self._howto_close is not None and _alive(self._howto_close):
            self._howto_close.setText(self.tr(eo.BTN_CLOSE))

    def show_howto(self) -> QtWidgets.QMessageBox:
        """「矩形選択の使い方」を、本体を止めない窓で出す(Esc で閉じる。2 度目は同じ窓を前へ)。

        ボタンは今の言語の「閉じる」(Qt の標準の Close は訳されない)。道具の窓なので Enter でボタンを押さない
        (既定のボタンにしない。設計書 P02-4・D95)。
        """
        if self._howto is None or not _alive(self._howto):
            box = QtWidgets.QMessageBox(self.editor.window())
            box.setObjectName("editopsHowto")
            box.setIcon(QtWidgets.QMessageBox.Information)
            close = box.addButton(self.tr(eo.BTN_CLOSE), QtWidgets.QMessageBox.RejectRole)
            close.setAutoDefault(False)
            close.setDefault(False)
            box.setEscapeButton(close)
            box.setModal(False)
            self._howto, self._howto_close = box, close
        self._fill_howto()
        self._howto.show()
        self._howto.raise_()
        return self._howto


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def get(editor: QtWidgets.QPlainTextEdit) -> EditOps | None:
    """``editor`` に付いている EditOps(無ければ None)。"""
    for ch in editor.children():
        if isinstance(ch, EditOps) and ch._on:
            return ch
    return None


def install(editor: QtWidgets.QPlainTextEdit, **options) -> EditOps:
    """``editor`` に編集操作を取り付ける。既に付いていれば、それを返す(2 つ目は作らない)。

    ``options``: ``tr``(文 → 今の言語の文)/ ``settings``(``QSettings`` を返す関数。無ければ設定は覚えない)/
    ``comment_prefix``(無ければエディタの ``comment_prefix``、それも無ければ ``#``)/ ``tab_width`` /
    ``indent_width`` / ``clipboard``(``text()`` と ``setText()`` を持つ物。試験用)/ ``on_message``(状態行へ 1 行)/
    ``ambiguous_wide``(曖昧幅の文字を全角として数えるか。``None`` = 今の書体で測る)。
    """
    return get(editor) or EditOps(editor, **options)


def retranslate_all() -> int:
    """今ある全部の EditOps の文を、今の言語と今のキーで付け直す(``EditOps.retranslate``)。付け直した EditOps の数。

    本体の言語の切り替えの後に呼ぶ(キーの部品 ``studio_keymap_qt`` を取り付けていれば、そちらが呼ぶ)。
    """
    n = 0
    for ops in list(_LIVE):
        if ops._on:
            ops.retranslate()
            n += 1
    return n


def apply_bindings(bindings: dict | None) -> int:
    """今ある全部の EditOps と、これから取り付ける EditOps のキーを ``{操作: キーの並び}`` にする。

    None で表の既定(``studio_editops.KEYMAP``)へ戻す。知らない操作の名前は ``ValueError``。
    キーの登録簿(``studio_keymap_qt.apply_keymap``)が呼ぶ。キーを付け替えた EditOps の数を返す。
    """
    global _BINDINGS
    if bindings is not None:
        known = {b.command for b in eo.KEYMAP}
        bad = sorted(set(bindings) - known)
        if bad:
            raise ValueError("知らない操作: %s" % ", ".join(bad))
        bindings = {c: tuple(k) for c, k in bindings.items()}
    _BINDINGS = bindings
    n = 0
    for ops in list(_LIVE):
        if ops._on:
            ops.set_bindings(bindings)
            n += 1
    return n


def uninstall(editor: QtWidgets.QPlainTextEdit) -> bool:
    """``editor`` から外す。付いていたら True。"""
    ops = get(editor)
    if ops is None:
        return False
    ops.detach()
    ops.setParent(None)
    ops.deleteLater()
    return True


# --------------------------------------------------------------------------- #
# キーの当たりの検査(既にあるショートカットを窓から全部集める)
# --------------------------------------------------------------------------- #
#: QPlainTextEdit が自分で受ける標準のキー(``QWidgetTextControl`` が見る物)。
_TEXT_STANDARD_KEYS = (
    "Undo", "Redo", "Cut", "Copy", "Paste", "Delete", "Backspace", "SelectAll", "InsertParagraphSeparator",
    "InsertLineSeparator", "MoveToNextChar", "MoveToPreviousChar", "MoveToNextWord", "MoveToPreviousWord",
    "MoveToNextLine", "MoveToPreviousLine", "MoveToStartOfLine", "MoveToEndOfLine", "MoveToStartOfBlock",
    "MoveToEndOfBlock", "MoveToStartOfDocument", "MoveToEndOfDocument", "MoveToNextPage", "MoveToPreviousPage",
    "SelectNextChar", "SelectPreviousChar", "SelectNextWord", "SelectPreviousWord", "SelectNextLine",
    "SelectPreviousLine", "SelectStartOfLine", "SelectEndOfLine", "SelectStartOfBlock", "SelectEndOfBlock",
    "SelectStartOfDocument", "SelectEndOfDocument", "SelectNextPage", "SelectPreviousPage", "DeleteStartOfWord",
    "DeleteEndOfWord", "DeleteEndOfLine", "DeleteCompleteLine",
)


def builtin_text_keys() -> list:
    """QPlainTextEdit の標準のキー ``[(キー, 持ち主, True)]``(この機械のプラットフォームの割り当て)。"""
    out = []
    for name in _TEXT_STANDARD_KEYS:
        sk = getattr(QtGui.QKeySequence.StandardKey, name)
        for ks in QtGui.QKeySequence.keyBindings(sk):
            out.append((ks.toString(QtGui.QKeySequence.PortableText), "QPlainTextEdit." + name, True))
    return out


def _host_window(w):
    """部品 ``w`` が属する窓。メニュー(それ自体が浮いた窓)はメニューバー・親の側へたどる。"""
    seen = 0
    while isinstance(w, QtWidgets.QMenu) and seen < 16:
        w = w.parentWidget()
        seen += 1
    return w.window() if isinstance(w, QtWidgets.QWidget) else None


def _covers(context, widgets, editor: QtWidgets.QWidget) -> bool:
    """その文脈のショートカットが、``editor`` にフォーカスがある時に効くか。

    窓全体(WindowShortcut)のキーは、**同じ窓**の物だけ(2026-11-13: 別窓の Python エディタ・画像ビューアの
    QShortcut を本体の Program 欄に効くと数えていた)。
    """
    if context == _K.ApplicationShortcut:
        return True
    if context == _K.WindowShortcut:
        win = editor.window()
        return any(_host_window(w) is win for w in widgets)
    if context == _K.WidgetShortcut:
        return any(w is editor for w in widgets)
    if context == _K.WidgetWithChildrenShortcut:
        return any(w is editor or (isinstance(w, QtWidgets.QWidget) and w.isAncestorOf(editor)) for w in widgets)
    return False


def collect_shortcuts(window: QtWidgets.QWidget, editor: QtWidgets.QWidget) -> list:
    """窓の中の全部の ``QAction`` と ``QShortcut`` のキー ``[(キー, 持ち主, editor に効くか)]``。

    この部品の入口(``editops:`` で始まる名前の QAction)は数えない。
    """
    out = []
    for a in window.findChildren(QtGui.QAction):
        if a.objectName().startswith("editops:"):
            continue
        for ks in a.shortcuts():
            if ks.isEmpty():
                continue
            widgets = [w for w in a.associatedObjects() if isinstance(w, QtWidgets.QWidget)]
            out.append((ks.toString(QtGui.QKeySequence.PortableText), a.text().replace("&", "") or a.objectName(),
                        _covers(a.shortcutContext(), widgets, editor)))
    for s in window.findChildren(QtGui.QShortcut):
        parent = s.parent()
        for ks in s.keys():
            if ks.isEmpty():
                continue
            out.append((ks.toString(QtGui.QKeySequence.PortableText), "QShortcut@%s" % type(parent).__name__,
                        _covers(s.context(), [parent], editor)))
    return out


def check_conflicts(window: QtWidgets.QWidget, editor: QtWidgets.QWidget) -> dict:
    """キーの当たりを調べる。``{"studio": [...], "internal": [...], "builtin": [...], "existing": 件数}``。

    * ``studio``: 窓のショートカット(QAction / QShortcut)と同じキー。**空でなければ割り当てを変える。**
    * ``internal``: エディタの部品が自分で受けているキー(``studio_editops.EDITOR_INTERNAL_KEYS``)と同じキー。
    * ``builtin``: QPlainTextEdit の標準のキーと同じキー(プラットフォームで違う)。
    """
    ops = get(editor)
    mine = eo.active_bindings(editor_has_comment=hasattr(editor, "toggle_comment"),
                              keys=ops._bindings if ops is not None else _BINDINGS)
    existing = collect_shortcuts(window, editor)
    return {
        "studio": eo.find_conflicts(mine, existing),
        "internal": eo.find_conflicts(mine, [(k, "editor", True) for k in eo.EDITOR_INTERNAL_KEYS]),
        "builtin": eo.find_conflicts(mine, builtin_text_keys()),
        "existing": len(existing),
    }
