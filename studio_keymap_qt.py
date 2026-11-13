# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_keymap_qt — キーの割り当てを Studio の本物の窓へ配る(Qt)と、設定の窓「キーボードのショートカットの設定」。

Studio 本体への取り付けは 1 行::

    import studio_keymap_qt as kq
    win._keymap = kq.install(win, settings=_settings, tr=tr, lang=lambda: _UI_LANG.get("code", "en"),
                             palette_words=PALETTE_WORDS)

``install`` がする事
* 保存してあった利用者の上書きを読む(壊れた分は捨てて状態行で知らせる)。
* ``apply_keymap(win, keymap)``: 登録簿(``studio_keymap.COMMANDS``)のキーを、本物の ``QAction`` / 別窓の
  ``QShortcut`` / Program 欄 / 矩形選択の部品(``studio_editops_qt``)へ配る。メニューの右のキーは
  ``QAction.shortcut()`` から Qt が出すので、表示と実際のキーは同じ物になる。
* ID の無かった ``QAction``(Image focus など)を ``win._actions`` に ID で載せ、``objectName`` に ``keymap:<ID>``
  を入れる(パレットと F1 の表に出る)。右クリックのメニューにしか付いていなかった Ctrl+Shift+E は窓にも付ける
  (棚卸しで「どこから押しても効かない」と実測された物)。
* Program 欄: 欄の部品(``ProgramEditor._ide_action``)はキーを直接書いているので、その前にイベントフィルタを
  1 つ置き、変えたキーで同じ操作(``_ide_do``)を呼び、外したキーは欄に通さない(窓の同じキーが撃たれる)。
* 言語の切り替え・遅れて作られる窓(``win._localize``)に追従する。メニュー・ツールチップの文に既定のキーが
  書いてある所(``Run all (F5 / Ctrl+R)`` など)は、今のキーへ書き換える(``studio_keymap.retarget_text``)。
* Tools メニューに「キーボードのショートカットの設定…」(既定 Ctrl+K, Ctrl+S)。
"""
from __future__ import annotations

import html
import json
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

import studio_editops_qt as eq
import studio_keymap as km

_K = QtCore.Qt
_MODS = _K.ShiftModifier | _K.ControlModifier | _K.AltModifier | _K.MetaModifier
_PURE = (_K.Key_Shift, _K.Key_Control, _K.Key_Alt, _K.Key_Meta, _K.Key_AltGr, _K.Key_CapsLock, _K.Key_NumLock,
         _K.Key_ScrollLock, _K.Key_unknown, _K.Key_Super_L, _K.Key_Super_R, _K.Key_Hyper_L, _K.Key_Hyper_R)
_PORTABLE = QtGui.QKeySequence.PortableText
#: Shift で別の記号になったキー → 元のキー(``>`` → ``.``)。US 配列の対(studio_editops_qt と同じ表)。
_UNSHIFT = {int(v): int(k) for k, v in eq._SHIFTED.items()}
#: キーの欄だけ等幅(利用者の決定: コードの書体は BIZ UDGothic)。
KEY_FONT_FAMILIES = ("BIZ UDGothic", "Consolas", "monospace")
#: Studio の THEME は ``QWidget { font-family: … }`` を全体に掛けるので、setFont だけでは書体が変わらない。
_KEY_FONT_QSS = "font-family: 'BIZ UDGothic', Consolas, monospace;"
_ERR, _WARN, _INFO = "#e5534b", "#d29922", "#8b98a9"


def _valid(obj) -> bool:
    try:
        import shiboken6                                       # noqa: PLC0415  (PySide6 に付いてくる)
        return obj is not None and shiboken6.isValid(obj)
    except ImportError:                                        # pragma: no cover
        return obj is not None


def _seq_text(seq: QtGui.QKeySequence) -> str | None:
    """QKeySequence → 登録簿の書き方(読めなければ None)。"""
    if seq.isEmpty():
        return None
    try:
        return km.normalize_sequence(seq.toString(_PORTABLE))
    except km.KeyParseError:
        return None


def event_keys(ev) -> list:
    """キーの出来事 → 当てはまり得るキーの書き方(先頭が記録に使う形)。

    Shift で変わる記号は元のキーに Shift を付けた形(``Shift+Alt+.``)を先に、Qt の届けた形
    (``Shift+Alt+>``)、Shift を除いた形(配列で Shift が要る ``Ctrl++``)も返す。テンキーの Enter は Return も。
    Shift を除いた形は **Shift で変わる記号が届いた時だけ**(2026-11-13 レビュー F4: F キーや ``/`` にも付けていたので、
    ``F2`` に変えたキーが ``Shift+F2`` も奪い、既定の表でも ``Ctrl+Shift+/`` が行をコメントにしていた)。
    """
    key, raw = int(ev.key()), ev.modifiers()
    if key in _PURE:
        return []
    mods = _K.NoModifier
    for flag in (_K.ControlModifier, _K.ShiftModifier, _K.AltModifier, _K.MetaModifier):
        if raw & flag:
            mods |= flag
    if key == _K.Key_Backtab:
        key, mods = int(_K.Key_Tab), mods | _K.ShiftModifier
    out: list = []

    def add(k, m):
        try:
            seq = QtGui.QKeySequence(QtCore.QKeyCombination(m, _K.Key(int(k))))
        except (ValueError, TypeError):
            return
        t = _seq_text(seq)
        if t and t not in out:
            out.append(t)

    shifted = bool(mods & _K.ShiftModifier) and not (int(_K.Key_A) <= key <= int(_K.Key_Z))
    if shifted and key in _UNSHIFT:
        add(_UNSHIFT[key], mods)
    add(key, mods)
    if shifted and key in _UNSHIFT:
        plain = _K.NoModifier
        for flag in (_K.ControlModifier, _K.AltModifier, _K.MetaModifier):
            if mods & flag:
                plain |= flag
        add(key, plain)
    if key == int(_K.Key_Enter):
        add(_K.Key_Return, mods)
    return out


def _qt_stripped(text: str) -> str:
    """QAction が文から作る既定のツールチップ(``&`` と ``...`` を除く。Qt の qt_strippedText と同じ)。"""
    s = text.replace("...", "")
    out, i = [], 0
    while i < len(s):
        if s[i] == "&":
            i += 1
            if i < len(s):
                out.append(s[i])
        else:
            out.append(s[i])
        i += 1
    return "".join(out).strip()


# --------------------------------------------------------------------------- #
# Program 欄: 欄が直接書いているキーの前に置く判定
# --------------------------------------------------------------------------- #
class _ProgramKeys(QtCore.QObject):
    """Program 欄(``ProgramEditor``)のイベントフィルタ。変えたキーで欄の操作を呼び、外した既定のキーは欄に通さない。

    ``help``(F1 = ここのヘルプ)は窓の help_here と同じ答えを出す(カーソルの下が op でなければ、選んだ段 / op /
    キーの一覧)。
    """

    def __init__(self, editor, win=None):
        super().__init__(editor)
        self.editor = editor
        self.win = win
        self.current: dict = {}
        self.bound: set = set()                                # 今キーが 1 つ以上ある操作
        self.managed = {c.ide for c in km.COMMANDS if c.ide and not c.fixed}
        self.defaults: dict = {}                               # 操作 → 型の既定のキー(どの型でも)
        for c in km.COMMANDS:
            if c.ide and not c.fixed:
                keys = set(self.defaults.get(c.ide, ())) | set(c.keys) | set(km.PROGRAM_EDITOR_HARD_KEYS.get(c.ide, ()))
                for over in km.PRESETS.values():
                    keys |= set(over.get(c.id, ()))
                self.defaults[c.ide] = keys
        editor.installEventFilter(self)

    def set_table(self, keymap: km.Keymap) -> None:
        self.current = {k: c.ide for c in km.COMMANDS if c.ide and not c.fixed for k in keymap.keys(c.id)}
        self.bound = set(self.current.values())

    def _editops_takes(self, ev) -> bool:
        ops = eq.get(self.editor)
        return ops is not None and ops._binding_for(ev) is not None

    def eventFilter(self, obj, ev):                             # noqa: N802 (Qt の名前)
        t = ev.type()
        if obj is not self.editor or t not in (QtCore.QEvent.ShortcutOverride, QtCore.QEvent.KeyPress):
            return False
        try:
            keys = event_keys(ev)
            for k in keys:
                name = self.current.get(k)
                if name:
                    if t == QtCore.QEvent.ShortcutOverride:
                        ev.accept()                            # 窓の同じキーより先に、この欄が受ける
                        return True
                    comp = getattr(obj, "_completer", None)
                    if comp is not None:
                        comp.popup().hide()
                    ctl = get(self.win) if self.win is not None else None
                    if name == "help" and ctl is not None:
                        ctl.help_here()                        # F1 = ここのヘルプ(窓と同じ答え)
                    elif name == "save":
                        if ctl is not None:
                            ctl.save_program()                 # Ctrl+S = プログラム / パイプラインの保存
                    else:
                        obj._ide_do(name)
                    return True
            ide = getattr(obj, "_ide_action", None)
            hard = ide(ev) if ide is not None else None
            if hard in self.managed and (hard not in self.bound
                                         or any(k in self.defaults.get(hard, ()) for k in keys)):
                if self._editops_takes(ev):
                    return False                               # 矩形選択の部品のキーになった: そちらへ
                return True                                    # 外した既定のキー: 欄に通さない(窓のキーが撃たれる)
        except Exception as exc:                               # noqa: BLE001 -- フィルタの中の例外は Qt を落とす
            print("studio_keymap_qt: %s: %s" % (type(exc).__name__, exc))
        return False


# --------------------------------------------------------------------------- #
# 本物の窓へ配る
# --------------------------------------------------------------------------- #
_SIGNATURES: dict = {}
for _c in km.COMMANDS:
    if _c.target.startswith("shortcut:"):
        _kind, _key = _c.target.split(":", 2)[1:]
        _SIGNATURES.setdefault(_kind, {})[km.normalize_sequence(_key)] = _c.id


class _State:
    """窓 1 つ分の覚え(``win._keymap_state``)。"""

    def __init__(self):
        self.targets: dict = {}
        self.text_base: dict = {}
        self.program: _ProgramKeys | None = None
        self.hooks = False
        self.keymap = km.Keymap()
        self.lang = None
        self.own: dict = {}
        self.registered: list = []
        self.on_lang: list = []


def _state(win) -> _State:
    st = getattr(win, "_keymap_state", None)
    if not isinstance(st, _State):
        st = _State()
        win._keymap_state = st
    return st


def _in_window(action: QtGui.QAction, win) -> bool:
    return any(isinstance(w, QtWidgets.QWidget) and eq._host_window(w) is win for w in action.associatedObjects())


def _find_label_action(win, english: str):
    for obj, rec in list(getattr(win, "_label_en", {}).items()):
        if isinstance(obj, QtGui.QAction) and isinstance(rec, tuple) and rec[1:] == (english,) and _valid(obj):
            return obj
    for a in win.findChildren(QtGui.QAction):
        if a.text() == english:
            return a
    return None


def _resolve(win, st: _State) -> None:
    acts = getattr(win, "_actions", None)
    if not isinstance(acts, dict):
        acts = {}
    for c in km.COMMANDS:
        if c.fixed or not c.target or c.target.startswith(("editops:", "shortcut:")):
            continue
        if any(_valid(o) for o in st.targets.get(c.id, ())):
            continue
        kind, _, arg = c.target.partition(":")
        obj = None
        if kind == "action":
            obj = acts.get(arg)
        elif kind == "label":
            obj = _find_label_action(win, arg)
        elif kind == "attr":
            obj = getattr(win, arg, None)
        elif kind == "work_mode":
            obj = (getattr(win, "_work_mode_actions", None) or {}).get(arg)
        elif kind == "own":
            obj = st.own.get(arg)
        if not isinstance(obj, QtGui.QAction):
            continue
        st.targets[c.id] = [obj]
        if not obj.objectName():
            obj.setObjectName("keymap:" + c.id)
        if kind != "action" and c.id not in acts and isinstance(getattr(win, "_actions", None), dict):
            win._actions[c.id] = obj                            # パレットと F1 の表に出す
            st.registered.append(c.id)
        if c.scope == "window" and not _in_window(obj, win):
            win.addAction(obj)                                 # メニューの都度作る右クリックにしか無かった物も窓で効く


def _scan_root(st: _State, root) -> int:
    """遅れて作られた窓(画像ビューア・Python エディタ)の QShortcut を見つけて ID を付ける。見つけた数。"""
    found = 0
    named: dict = {}
    unnamed: dict = {}
    for s in root.findChildren(QtGui.QShortcut):
        n = s.objectName()
        if n.startswith("keymap:") and n[7:] in km.BY_ID:
            named.setdefault(n[7:], []).append(s)
            continue
        t = _seq_text(s.key())
        if t:
            unnamed.setdefault(t, []).append(s)
    for _kind, sig in _SIGNATURES.items():
        if unnamed and set(sig) <= set(unnamed):
            for k, cid in sig.items():
                for s in unnamed.pop(k):
                    s.setObjectName("keymap:" + cid)
                    named.setdefault(cid, []).append(s)
    for cid, objs in named.items():
        lst = [o for o in st.targets.get(cid, []) if _valid(o)]
        for o in objs:
            if not any(o is x for x in lst):
                lst.append(o)
                found += 1
        st.targets[cid] = lst
    return found


def _set_keys(obj, keys: tuple) -> None:
    seqs = [QtGui.QKeySequence(k) for k in keys]
    if isinstance(obj, QtGui.QShortcut):
        obj.setKeys(seqs)
    else:
        obj.setShortcuts(seqs)


def _lang_code(st: _State, win) -> str:
    try:
        return (st.lang() if callable(st.lang) else None) or getattr(win, "_lang", "en") or "en"
    except Exception:                                          # noqa: BLE001
        return "en"


def _retarget(st: _State, obj: QtGui.QAction, pairs: list, lang: str) -> None:
    try:
        cur = (obj.text(), obj.toolTip(), obj.statusTip())
    except RuntimeError:
        return
    rec = st.text_base.get(id(obj))
    base = rec[1] if (rec is not None and rec[0] is obj and cur == rec[2]) else cur
    implicit_tip = base[1] == _qt_stripped(base[0])
    new = (km.retarget_text(base[0], pairs, lang), base[1] if implicit_tip else km.retarget_text(base[1], pairs, lang),
           km.retarget_text(base[2], pairs, lang))
    if new[0] != cur[0]:
        obj.setText(new[0])
    if not implicit_tip and new[1] != cur[1]:
        obj.setToolTip(new[1])
    if new[2] != cur[2]:
        obj.setStatusTip(new[2])
    st.text_base[id(obj)] = (obj, base, (obj.text(), obj.toolTip(), obj.statusTip()))


def _retarget_all(win, st: _State) -> None:
    lang = _lang_code(st, win)
    for c in km.COMMANDS:
        pairs = km.text_pairs(st.keymap, c.id) if not c.fixed else []
        changed = any(tuple(a) != tuple(b) for a, b in pairs)
        for obj in st.targets.get(c.id, ()):
            if isinstance(obj, QtGui.QAction) and _valid(obj) and (changed or id(obj) in st.text_base):
                _retarget(st, obj, pairs, lang)


def apply_keymap(win, keymap: km.Keymap, lang=None) -> dict:
    """``keymap`` のキーを窓 ``win`` の本物の入口へ配る。``{"applied": 数, "missing": [見つからない ID]}``。

    別窓の QShortcut は、その窓が作られた時(``win._localize``)に配る(まだ無い物は missing に数えない)。
    """
    st = _state(win)
    st.keymap = keymap
    if lang is not None:
        st.lang = lang
    _resolve(win, st)
    applied, missing = 0, []
    for c in km.COMMANDS:
        if c.fixed or c.target.startswith(("editops:", "filter:")):
            continue                                           # 矩形選択の部品・Program 欄のフィルタは下で配る
        objs = [o for o in st.targets.get(c.id, ()) if _valid(o)]
        if not objs:
            if not c.target.startswith("shortcut:"):
                missing.append(c.id)
            continue
        for o in objs:
            _set_keys(o, keymap.keys(c.id))
            applied += 1
    prog = getattr(win, "_program", None)
    edit = prog.get("edit") if isinstance(prog, dict) else None
    if edit is not None and hasattr(edit, "_ide_do"):
        if st.program is None or not _valid(st.program):
            st.program = _ProgramKeys(edit, win)
        st.program.set_table(keymap)
    eq.apply_bindings({c.target.split(":", 1)[1]: keymap.keys(c.id)
                       for c in km.COMMANDS if c.target.startswith("editops:")})
    _retarget_all(win, st)
    _install_hooks(win, st)
    return {"applied": applied, "missing": missing}


def _install_hooks(win, st: _State) -> None:
    if st.hooks:
        return
    st.hooks = True

    def after_language(*_a):
        for fn in list(st.on_lang):
            try:
                fn()
            except Exception as exc:                           # noqa: BLE001 -- 表示の付け直しが窓を壊さない
                print("studio_keymap_qt: %s: %s" % (type(exc).__name__, exc))
        _retarget_all(win, st)

    for a in (getattr(win, "_lang_actions", None) or {}).values():
        a.triggered.connect(after_language)                    # 言語の切り替え(Studio の処理の後に呼ばれる)
    orig = getattr(win, "_apply_language", None)
    if callable(orig):
        def apply_language(*args, **kw):
            r = orig(*args, **kw)
            after_language()
            return r
        win._apply_language = apply_language
    loc = getattr(win, "_localize", None)
    if callable(loc):
        def localize(root):
            r = loc(root)
            if _scan_root(st, root):
                for c in km.COMMANDS:
                    for o in st.targets.get(c.id, ()):
                        if isinstance(o, QtGui.QShortcut) and _valid(o) and o.parent() is root:
                            _set_keys(o, st.keymap.keys(c.id))
            return r
        win._localize = localize


_STRINGS: dict = {}
_FIELD_VERDICT: dict = {}
_PROBE_FIELDS: list = []


def _strings_table() -> dict:
    """Studio の訳の表 ``{英語: {言語: 訳}}``(読み込み済みの studio から。無ければ studio_assets/i18n.json)。"""
    mod = sys.modules.get("studio")
    tab = getattr(mod, "STRINGS_I18N", None) if mod is not None else None
    if isinstance(tab, dict):
        return tab
    if "file" not in _STRINGS:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_assets", "i18n.json")
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):                          # 訳が読めなくても、今の言語の分は数える
            data = {}
        data = data if isinstance(data, dict) else {}
        merged = {k: v for k, v in data.items() if k != "strings"}
        if isinstance(data.get("strings"), dict):              # 訳は上の段と "strings" の 2 か所にある
            merged.update(data["strings"])
        _STRINGS["file"] = merged
    return _STRINGS["file"]


def _mnemonic(title: str) -> str | None:
    return _seq_text(QtGui.QKeySequence.mnemonic(title)) if title else None


def _field_takes(key: str) -> bool:
    """テキスト欄(本物の QPlainTextEdit と QLineEdit の両方)が ``key`` を ShortcutOverride で先に取るか(実測)。

    取らない欄があれば、窓の同じキーが勝って、その欄の標準の操作が消える(2026-11-13 の実測: Ctrl+Backspace・
    Ctrl+Del・PgDown は両方とも取らない、Shift+Down・Up・Down・Return は 1 行の欄が取らない)。
    """
    if key in _FIELD_VERDICT:
        return _FIELD_VERDICT[key]
    if not _PROBE_FIELDS or not all(_valid(w) for w in _PROBE_FIELDS):
        pte = QtWidgets.QPlainTextEdit()
        pte.setPlainText("ab cd\nef gh")
        _PROBE_FIELDS[:] = [pte, QtWidgets.QLineEdit("ab cd")]
    seq = QtGui.QKeySequence(key)
    taken = seq.count() == 1
    if taken:
        comb = seq[0]
        for w in _PROBE_FIELDS:
            ev = QtGui.QKeyEvent(QtCore.QEvent.ShortcutOverride, comb.key(), comb.keyboardModifiers())
            ev.ignore()
            QtCore.QCoreApplication.sendEvent(w, ev)
            taken = taken and ev.isAccepted()
    _FIELD_VERDICT[key] = taken
    return taken


def _menu_entries(win, strings: dict | None = None) -> list:
    """メニューバーのニーモニック: 今の言語の物(範囲 menu_bar)と、他の言語の物(menu_bar_other、キーごとに 1 行)。"""
    mb = win.menuBar() if hasattr(win, "menuBar") else None
    if mb is None:
        return []
    labels = getattr(win, "_label_en", None) or {}
    table = strings if strings is not None else _strings_table()
    out, current, sources = [], set(), []
    for a in mb.actions():
        title = a.text()
        t = _mnemonic(title)
        if t:
            name = _qt_stripped(title)
            out.append(km.Entry("menu:" + name, t, "menu_bar", None, True, km.MSG_MENU_BAR % name, "menu"))
            current.add(t)
        menu = a.menu()
        rec = labels.get(menu) if menu is not None else None
        en = rec[1] if isinstance(rec, tuple) and len(rec) == 2 and isinstance(rec[1], str) else None
        if en is None and getattr(win, "_lang", "en") == "en":
            en = title
        sources.append(en)
    other: dict = {}
    for en in sources:
        if not en:
            continue
        row = table.get(en)
        row = row if isinstance(row, dict) else {}
        for lang, text in [("en", en)] + sorted((k, v) for k, v in row.items() if isinstance(v, str)):
            t = _mnemonic(text)
            if t and t not in current:
                name = "%s (%s)" % (_qt_stripped(text), lang)
                names = other.setdefault(t, [])
                if name not in names:
                    names.append(name)
    for t in sorted(other):
        names = ", ".join(other[t])
        out.append(km.Entry("menu_other:" + names, t, "menu_bar_other", None, True, km.MSG_MENU_OTHER % names,
                            "menu"))
    return out


def collect_fixed(win, strings: dict | None = None) -> list:
    """変えられないが当たりの検査に入れるキー: メニューバーのニーモニック(今の言語と他の言語)と、テキスト欄の
    標準のキー(欄が先に取る ``text`` / 窓のキーが勝つと欄の操作が消える ``text_lost``。本物の欄で実測)。"""
    out = _menu_entries(win, strings)
    seen = set()
    for key, owner, _covers in eq.builtin_text_keys():
        try:
            t = km.normalize_sequence(key)
        except km.KeyParseError:
            continue
        if t in seen:
            continue
        seen.add(t)
        name = owner.split(".")[-1]
        scope = "text" if _field_takes(t) else "text_lost"
        out.append(km.Entry("text:" + name, t, scope, None, True, km.MSG_TEXT_KEY % name))
    return out


# --------------------------------------------------------------------------- #
# 設定の窓
# --------------------------------------------------------------------------- #
class KeyRecorder(QtWidgets.QLineEdit):
    """押したキーを記録する欄。記録の間は窓のキーを撃たせない(ShortcutOverride を取る)。IME の文字は受けない。

    ``allow_chords`` の時、続けて押したもう 1 打は 2 打鍵のキー(3 打目で始めから)。そうでなければ毎回置き換える。
    修飾なしの Enter = 決める(``commit``)、Esc = 記録をやめる(空なら ``leave``)、Tab / Shift+Tab = フォーカス移動
    (VS Code のキーの記録と同じ)。``record_literally`` の後の 1 打だけは、Tab・Esc・Enter もそのまま記録する。
    """

    recorded = QtCore.Signal(str)
    commit = QtCore.Signal()
    leave = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("keymapRecorder")
        self.setReadOnly(True)
        self.setAttribute(_K.WA_InputMethodEnabled, False)
        self.allow_chords = True
        self._strokes: list = []
        self._literal = False
        self._placeholder = ""

    def record_literally(self, hint: str = "") -> None:
        """次の 1 打を、Tab・Esc・Enter も含めてそのまま記録する。"""
        self._literal = True
        self._placeholder = self.placeholderText()
        if hint:
            self.setPlaceholderText(hint)
        self.setFocus()

    def _end_literal(self) -> None:
        if self._literal:
            self._literal = False
            self.setPlaceholderText(self._placeholder)

    def _navigation(self, ev) -> bool:
        """記録しないキー(Tab の移動・Enter・Esc)なら処理して True。"""
        key, mods = int(ev.key()), ev.modifiers()
        hard = mods & (_K.ControlModifier | _K.AltModifier | _K.MetaModifier)
        if key in (int(_K.Key_Tab), int(_K.Key_Backtab)) and not hard:
            self.focusNextPrevChild(key == int(_K.Key_Tab) and not mods & _K.ShiftModifier)
            return True
        if hard or mods & _K.ShiftModifier:
            return False
        if key in (int(_K.Key_Return), int(_K.Key_Enter)):
            self.commit.emit()
            return True
        if key == int(_K.Key_Escape):
            if self._strokes:
                self.clear_keys()
            else:
                self.leave.emit()
            return True
        return False

    def sequence(self) -> str:
        return ", ".join(self._strokes)

    def clear_keys(self) -> None:
        self._strokes = []
        self.setText("")
        self.recorded.emit("")

    def event(self, ev):
        et = ev.type()
        if et == QtCore.QEvent.ShortcutOverride:
            ev.accept()
            return True
        if et == QtCore.QEvent.KeyPress:                       # QLineEdit の既定(Tab の移動など)へは渡さない
            if not self._literal and self._navigation(ev):
                return True
            self.keyPressEvent(ev)
            return True
        return super().event(ev)

    def keyPressEvent(self, ev):                               # noqa: N802 (Qt の名前)
        keys = event_keys(ev)
        if not keys or ev.isAutoRepeat():
            return
        self._end_literal()
        if self.allow_chords and len(self._strokes) == 1:
            self._strokes.append(keys[0])
        else:
            self._strokes = [keys[0]]
        self.setText(self.sequence())
        self.recorded.emit(self.sequence())

    def focusOutEvent(self, ev):                               # noqa: N802 (Qt の名前)
        self._end_literal()
        super().focusOutEvent(ev)

    def inputMethodEvent(self, ev):                            # noqa: N802 (Qt の名前)
        ev.ignore()                                            # 変換中の文字はキーとして記録しない


def _key_font(base: QtGui.QFont) -> QtGui.QFont:
    f = QtGui.QFont(base)
    f.setFamilies(list(KEY_FONT_FAMILIES))
    f.setStyleHint(QtGui.QFont.Monospace)
    return f


class KeyboardDialog(QtWidgets.QDialog):
    """「キーボードのショートカットの設定」(本体を止めない窓)。"""

    def __init__(self, ctl: "KeymapController"):
        super().__init__(ctl.win)
        self.ctl = ctl
        self.setObjectName("keymapDialog")
        self.setModal(False)
        self.confirm = self._confirm                           # 試験で差し替える(確認の窓)
        self.ask_open = self._ask_open
        self.ask_save = self._ask_save
        self.inform = self._inform
        self._rows: list = []
        self._cid: str | None = None
        self._build()
        self.retranslate()
        ctl.changed.connect(self.refill)

    # ---- 組み立て ---------------------------------------------------------- #
    def _build(self) -> None:
        tr = self.ctl.tr
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(4)
        self.preset_label = QtWidgets.QLabel()
        self.preset = QtWidgets.QComboBox()
        self.preset.setObjectName("keymapPreset")
        self.preset.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)   # 言語を変えても文が切れない
        self.preset.setFocusPolicy(_K.StrongFocus)
        self.preset.installEventFilter(self)                       # フォーカスの無い時のホイールで型を変えない
        for name in km.PRESETS:
            self.preset.addItem(tr(km.PRESET_TITLES[name]), name)
        self.preset.activated.connect(self._on_preset)
        self.load_note = QtWidgets.QLabel()                       # 起動の時に使えなかった設定(無ければ隠す)
        self.load_note.setObjectName("keymapLoadNote")
        self.load_note.setWordWrap(True)
        self.load_note.setTextFormat(_K.PlainText)
        self.load_note.setStyleSheet("color: %s;" % _WARN)
        self.load_note.hide()
        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("keymapSearch")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self._filter())
        top.addWidget(self.preset_label)
        top.addWidget(self.preset)
        top.addWidget(self.search, 1)
        lay.addLayout(top)
        lay.addWidget(self.load_note)
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setObjectName("keymapTable")
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        vh = self.table.verticalHeader()
        vh.setMinimumSectionSize(1)
        vh.setDefaultSectionSize(self.table.fontMetrics().height() + 4)   # 行の高さ = 文字 + 4 px
        # 交互の行は今の地の色に薄く重ねる(Studio の暗い地でも明るい地でも読める。パレットの既定の明るい色は使わない)
        self.table.setStyleSheet("QTableWidget { alternate-background-color: rgba(127, 127, 127, 26); }"
                                 " QTableWidget::item { padding: 0px 4px; }")
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        for col in (1, 2, 3):
            hh.setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_select)
        lay.addWidget(self.table, 1)
        self.no_match = QtWidgets.QLabel()                         # 検索が 0 件の時の例
        self.no_match.setObjectName("keymapNoMatch")
        self.no_match.setProperty("muted", True)
        self.no_match.hide()
        lay.addWidget(self.no_match)
        self.selected = QtWidgets.QLabel()
        self.selected.setObjectName("keymapSelected")
        self.current = QtWidgets.QLabel()
        self.current.setObjectName("keymapCurrent")
        self.current.setFont(_key_font(self.current.font()))
        self.current.setStyleSheet(_KEY_FONT_QSS)
        lay.addWidget(self.selected)
        lay.addWidget(self.current)
        rec = QtWidgets.QHBoxLayout()
        rec.setSpacing(4)
        self.record_label = QtWidgets.QLabel()
        self.recorder = KeyRecorder()
        self.recorder.setFont(_key_font(self.recorder.font()))
        self.recorder.setStyleSheet(_KEY_FONT_QSS)
        self.recorder.recorded.connect(self._on_recorded)
        self.recorder.commit.connect(self._on_commit)
        self.recorder.leave.connect(lambda: self.table.setFocus())
        self.b_clear = QtWidgets.QPushButton()
        self.b_clear.clicked.connect(lambda _=False: self.recorder.clear_keys())
        self.b_literal = QtWidgets.QPushButton()
        self.b_literal.setObjectName("keymapLiteral")
        self.b_literal.clicked.connect(lambda _=False: self.recorder.record_literally(self.ctl.tr(km.PH_LITERAL)))
        rec.addWidget(self.record_label)
        rec.addWidget(self.recorder, 1)
        rec.addWidget(self.b_clear)
        rec.addWidget(self.b_literal)
        lay.addLayout(rec)
        self.hint = QtWidgets.QLabel()
        self.hint.setProperty("muted", True)
        lay.addWidget(self.hint)
        self.status = QtWidgets.QLabel()
        self.status.setObjectName("keymapStatus")
        self.status.setWordWrap(True)
        self.status.setTextFormat(_K.RichText)
        lay.addWidget(self.status)
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(4)
        self.b_assign = QtWidgets.QPushButton()
        self.b_assign.setObjectName("keymapAssign")
        self.b_add = QtWidgets.QPushButton()
        self.b_add.setObjectName("keymapAdd")
        self.b_remove = QtWidgets.QPushButton()
        self.b_remove.setObjectName("keymapRemove")
        self.b_reset = QtWidgets.QPushButton()
        self.b_reset.setObjectName("keymapReset")
        for b, fn in ((self.b_assign, self.do_assign), (self.b_add, self.do_add), (self.b_remove, self.do_remove),
                      (self.b_reset, self.do_reset)):
            b.clicked.connect(lambda _=False, f=fn: f())
            row1.addWidget(b)
        row1.addStretch(1)
        lay.addLayout(row1)
        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(4)
        self.b_reset_all = QtWidgets.QPushButton()
        self.b_reset_all.setObjectName("keymapResetAll")
        self.b_import = QtWidgets.QPushButton()
        self.b_import.setObjectName("keymapImport")
        self.b_export = QtWidgets.QPushButton()
        self.b_export.setObjectName("keymapExport")
        self.b_close = QtWidgets.QPushButton()
        for b, fn in ((self.b_reset_all, self.do_reset_all), (self.b_import, self.do_import),
                      (self.b_export, self.do_export)):
            b.clicked.connect(lambda _=False, f=fn: f())
            row2.addWidget(b)
        row2.addStretch(1)
        self.b_close.clicked.connect(self.close)
        row2.addWidget(self.b_close)
        lay.addLayout(row2)
        self.resize(820, 600)

    def retranslate(self) -> None:
        """今の言語で文を付け直す(言語の切り替えの後にも呼ばれる)。"""
        tr = self.ctl.tr
        self.setWindowTitle(tr(km.DLG_TITLE))
        self.preset_label.setText(tr(km.LBL_PRESET))
        for i in range(self.preset.count()):
            self.preset.setItemText(i, tr(km.PRESET_TITLES[self.preset.itemData(i)]))
        self.preset.updateGeometry()
        self.no_match.setText(tr(km.MSG_NO_MATCH))
        self.search.setPlaceholderText(tr(km.PH_SEARCH))
        self.table.setHorizontalHeaderLabels([tr(km.COL_COMMAND), tr(km.COL_KEY), tr(km.COL_WHERE), tr(km.COL_CHANGED)])
        self.record_label.setText(tr(km.LBL_RECORD))
        self.recorder.setPlaceholderText(tr(km.PH_RECORD))
        for b, s in ((self.b_clear, km.BTN_CLEAR), (self.b_assign, km.BTN_ASSIGN), (self.b_add, km.BTN_ADD),
                     (self.b_remove, km.BTN_REMOVE), (self.b_reset, km.BTN_RESET), (self.b_reset_all, km.BTN_RESET_ALL),
                     (self.b_import, km.BTN_IMPORT), (self.b_export, km.BTN_EXPORT), (self.b_close, km.BTN_CLOSE),
                     (self.b_literal, km.BTN_LITERAL)):
            b.setText(tr(s))
        self.refill()

    def eventFilter(self, obj, ev):                             # noqa: N802 (Qt の名前)
        if obj is self.preset and ev.type() == QtCore.QEvent.Wheel and not self.preset.hasFocus():
            ev.ignore()
            return True                                        # 表を回すつもりのホイールで型の切り替えを聞かない
        return super().eventFilter(obj, ev)

    # ---- 表 ---------------------------------------------------------------- #
    def refill(self) -> None:
        """表を今のキーで作り直す(選んでいた行は保つ)。"""
        ctl, tr = self.ctl, self.ctl.tr
        keep = self._cid
        i = self.preset.findData(ctl.keymap.preset)
        if i >= 0 and i != self.preset.currentIndex():
            self.preset.blockSignals(True)
            self.preset.setCurrentIndex(i)
            self.preset.blockSignals(False)
        self._rows = ctl.rows()
        t = self.table
        t.blockSignals(True)
        t.setRowCount(len(self._rows))
        key_font = _key_font(t.font())
        muted = QtGui.QColor(_INFO)
        for r, (cid, title, keys, where, changed, fixed) in enumerate(self._rows):
            cells = (title, keys or tr(km.LBL_NONE), where, "●" if changed else "")
            for col, text in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(text)
                it.setData(_K.UserRole, cid)
                if col == 1:
                    it.setFont(key_font)
                if col == 3:
                    it.setTextAlignment(_K.AlignCenter)
                    if changed:
                        it.setToolTip(tr(km.MSG_CHANGED))
                if fixed:
                    it.setForeground(muted)
                    it.setToolTip(tr(km.MSG_FIXED))
                t.setItem(r, col, it)
        t.blockSignals(False)
        self._filter()
        self._show_load_note()
        self.b_reset_all.setEnabled(bool(ctl.keymap.overrides()))
        self.select(keep) if keep else self._show_detail()

    def _show_load_note(self) -> None:
        tr = self.ctl.tr
        parts = []
        for header, probs in ((km.MSG_LOAD_HEADER, [p for p in self.ctl.load_problems if p.level != "info"]),
                              (km.MSG_LANG_HEADER, list(self.ctl.lang_problems))):
            if probs:
                parts.append(tr(header) + "\n" + "\n".join("  " + self.ctl.describe(p) for p in probs[:12]))
        if not parts:
            self.load_note.hide()
            return
        self.load_note.setText("\n".join(parts))
        self.load_note.show()

    def _filter(self) -> None:
        shown = {r[0] for r in km.search(self._rows, self.search.text())}
        for r, row in enumerate(self._rows):
            self.table.setRowHidden(r, row[0] not in shown)
        self.no_match.setVisible(bool(self.search.text().strip()) and not shown)

    def visible_ids(self) -> list:
        """今の絞り込みで見えている行の ID(上から)。"""
        return [row[0] for r, row in enumerate(self._rows) if not self.table.isRowHidden(r)]

    def select(self, cid: str) -> bool:
        for r, row in enumerate(self._rows):
            if row[0] == cid:
                self.table.selectRow(r)
                self._scroll_to(cid)                           # 選んだ行を見える所へ(行を隠し直した直後は、並べ直しの後にもう一度)
                QtCore.QTimer.singleShot(0, lambda c=cid: self._scroll_to(c) if _valid(self) else None)
                self._cid = cid
                self._show_detail()
                return True
        return False

    def _scroll_to(self, cid: str) -> None:
        for r, row in enumerate(self._rows):
            if row[0] == cid and self.table.item(r, 0) is not None:
                self.table.scrollToItem(self.table.item(r, 0))
                return

    def _on_select(self) -> None:
        items = self.table.selectedItems()
        self._cid = items[0].data(_K.UserRole) if items else None
        self.recorder.clear_keys()
        self._show_detail()

    # ---- 選んだ行 ---------------------------------------------------------- #
    def _cmd(self):
        return km.BY_ID.get(self._cid) if self._cid else None

    def _show_detail(self) -> None:
        tr, c = self.ctl.tr, self._cmd()
        editable = c is not None and not c.fixed
        for w in (self.recorder, self.b_clear, self.b_literal, self.b_remove, self.b_reset):
            w.setEnabled(editable)
        self.b_reset.setEnabled(editable and self.ctl.keymap.is_changed(c.id))
        self.b_remove.setEnabled(editable and bool(self.ctl.keymap.keys(c.id)))
        if c is None:
            title = next((r[1] for r in self._rows if r[0] == self._cid), "") if self._cid else ""
            self.selected.setText(title or tr(km.MSG_PICK))
            self.current.setText("")
            self.hint.setText("")
            self.status.setText("")
            self.b_assign.setEnabled(False)
            self.b_add.setEnabled(False)
            return
        self.selected.setText("%s — %s" % (tr(c.title), tr(km.SCOPES[c.scope].title)))
        keys = self.ctl.keymap.keys(c.id)
        self.current.setText(tr(km.LBL_CURRENT) % (" / ".join(keys) or tr(km.LBL_NONE)))
        if c.fixed:
            self.hint.setText(tr(km.MSG_FIXED))
            self.status.setText("")
            self.b_assign.setEnabled(False)
            self.b_add.setEnabled(False)
            return
        self.recorder.allow_chords = km.SCOPES[c.scope].chords
        self.hint.setText(tr(km.HINT_CHORD if self.recorder.allow_chords else km.HINT_NO_CHORD) + " "
                          + tr(km.HINT_KEYS))
        self._on_recorded(self.recorder.sequence())

    def _render(self, probs: list) -> str:
        if not probs:
            return '<span style="color:%s">%s</span>' % (_INFO, html.escape(self.ctl.tr(km.MSG_NO_CONFLICT)))
        rows = []
        for p in sorted(probs, key=lambda p: {"error": 0, "warning": 1}.get(p.level, 2)):
            color = {"error": _ERR, "warning": _WARN}.get(p.level, _INFO)
            rows.append('<span style="color:%s">%s</span>' % (color, html.escape(self.ctl.describe(p))))
        return "<br>".join(rows)

    def problems_for(self, seq: str, add: bool = False) -> list:
        """記録したキー ``seq`` を割り当てたら(``add`` なら足したら)起きる事。"""
        c = self._cmd()
        if c is None or not seq:
            return []
        keys = (tuple(self.ctl.keymap.keys(c.id)) + (seq,)) if add else (seq,)
        return self.ctl.check(c.id, keys)

    def _removal(self, seq: str) -> str | None:
        """記録したキーが今のキーの 1 つで、他にもキーがあれば、そのキーだけを外す(「<キー> を外す」)。"""
        c = self._cmd()
        keys = self.ctl.keymap.keys(c.id) if c is not None else ()
        return seq if seq and seq in keys and len(keys) > 1 else None

    def _on_recorded(self, seq: str) -> None:
        c = self._cmd()
        if c is None or c.fixed:
            return
        one = self._removal(seq)
        self.b_remove.setText(self.ctl.tr(km.BTN_REMOVE_ONE) % one if one else self.ctl.tr(km.BTN_REMOVE))
        if not seq:
            cur = self.ctl.check(c.id, self.ctl.keymap.keys(c.id))
            notes = [p for p in cur if p.level != "error"]
            self.status.setText(self._render(notes) if notes else "")
            self.b_assign.setEnabled(False)
            self.b_add.setEnabled(False)
            return
        try:
            seq = km.normalize_sequence(seq)
        except km.KeyParseError:
            self.b_assign.setEnabled(False)
            self.b_add.setEnabled(False)
            return
        probs = self.problems_for(seq)
        cur = tuple(self.ctl.keymap.keys(c.id))
        if cur and cur != (seq,) and not any(p.level == "error" for p in probs):
            probs = list(probs) + [km.Problem("info", "replaces", c.id, seq, detail=" / ".join(cur))]
        self.status.setText(self._render(probs))
        self.b_assign.setEnabled(not any(p.level == "error" for p in probs))
        add_probs = self.problems_for(seq, add=True)
        self.b_add.setEnabled(seq not in self.ctl.keymap.keys(c.id) and not any(p.level == "error" for p in add_probs))

    # ---- 操作 -------------------------------------------------------------- #
    def do_assign(self) -> list:
        c, seq = self._cmd(), self.recorder.sequence()
        if c is None or not seq:
            return []
        probs = self.ctl.assign(c.id, (seq,))
        self._after(probs)
        return probs

    def do_add(self) -> list:
        c, seq = self._cmd(), self.recorder.sequence()
        if c is None or not seq:
            return []
        probs = self.ctl.assign(c.id, tuple(self.ctl.keymap.keys(c.id)) + (seq,))
        self._after(probs)
        return probs

    def _on_commit(self) -> None:
        """記録の欄の Enter: 割り当てられる時だけ割り当てる。"""
        if self.b_assign.isEnabled():
            self.do_assign()

    def do_remove(self) -> None:
        c = self._cmd()
        if c is not None and not c.fixed:
            one = self._removal(self.recorder.sequence())
            keys = tuple(k for k in self.ctl.keymap.keys(c.id) if k != one) if one else ()
            self._after(self.ctl.assign(c.id, keys))

    def do_reset(self) -> list:
        c = self._cmd()
        if c is None or c.fixed:
            return []
        probs = self.ctl.reset(c.id)                           # 当たるなら戻さずに相手を示す
        self._after(probs)
        return probs

    def _after(self, probs: list) -> None:
        if any(p.level == "error" for p in probs):
            self.status.setText(self._render(probs))
            return
        self.recorder.clear_keys()
        self.refill()
        notes = [p for p in probs if p.level != "error"]
        if notes:
            self.status.setText(self._render(notes))

    def do_reset_all(self) -> bool:
        tr = self.ctl.tr
        n = len(self.ctl.keymap.overrides())
        if not n:
            return False
        if not self.confirm(tr(km.TTL_RESET_ALL), tr(km.ASK_RESET_ALL) % n, tr(km.BTN_RESET_ALL_DO)):
            return False
        self.ctl.reset_all()
        return True

    def _on_preset(self, index: int) -> None:
        name = self.preset.itemData(index)
        if not self.switch_preset(name):
            self.refill()                                      # 断った: 元の型の表示へ

    def switch_preset(self, name: str) -> bool:
        """型を切り替える(確認の窓で、外れる上書きを先に知らせる)。"""
        tr = self.ctl.tr
        if name == self.ctl.keymap.preset:
            return True
        trial = self.ctl.keymap.copy()
        dropped = trial.switch_preset(name, self.ctl.fixed_entries(), self.ctl.places)
        text = tr(km.ASK_PRESET) % tr(km.PRESET_TITLES[name])
        if dropped:
            text += "\n\n" + tr(km.ASK_PRESET_DROP) % len(dropped) + "\n" + "\n".join(
                "  %s: %s" % (tr(km.BY_ID[cid].title), " / ".join(keys) or tr(km.LBL_NONE)) for cid, keys in dropped)
        if not self.confirm(tr(km.TTL_PRESET), text, tr(km.BTN_SWITCH)):
            return False
        self.ctl.switch_preset(name)
        return True

    def do_import(self) -> bool:
        tr = self.ctl.tr
        path = self.ask_open()
        if not path:
            return False
        new, probs = self.ctl.read_import(path)
        if new is None:
            self.inform(tr(km.BTN_IMPORT), tr(km.MSG_IMPORT_FAILED) + "\n" + "\n".join(
                "  " + self.ctl.describe(p) for p in probs if p.level == "error"))
            return False
        cur = self.ctl.keymap
        if cur.overrides() or cur.preset != km.DEFAULT_PRESET:   # 今の変更が消える: 置き換える前に聞く
            text = tr(km.ASK_IMPORT) % (len(cur.overrides()), len(new.overrides()))
            if new.preset != cur.preset:
                text += "\n" + tr(km.ASK_IMPORT_PRESET) % tr(km.PRESET_TITLES[new.preset])
            lost = [cid for cid in sorted(cur.overrides()) if new.keys(cid) != cur.keys(cid)
                    and not new.is_changed(cid)]
            if lost:
                text += "\n\n" + tr(km.ASK_IMPORT_LOST) + "\n" + "\n".join(
                    "  %s: %s" % (tr(km.BY_ID[cid].title), " / ".join(cur.keys(cid)) or tr(km.LBL_NONE))
                    for cid in lost[:20])
            if not self.confirm(tr(km.TTL_IMPORT), text, tr(km.BTN_REPLACE)):
                return False
        self.ctl.use_import(new)
        self.status.setText(html.escape(tr(km.MSG_IMPORTED) % len(self.ctl.keymap.overrides())))
        return True

    def do_export(self) -> bool:
        tr = self.ctl.tr
        path = self.ask_save()
        if not path:
            return False
        try:
            n = self.ctl.export_file(path)
        except OSError as exc:                                 # 書けない場所・使われているファイル
            self.inform(tr(km.BTN_EXPORT), tr(km.MSG_EXPORT_FAILED) % (
                os.path.basename(path), km._safe(exc.strerror or type(exc).__name__, 80)))
            self.status.setText("")
            return False
        self.status.setText(html.escape(tr(km.MSG_EXPORTED) % (n, os.path.basename(path))))
        return True

    # ---- 既定の確認の窓 ---------------------------------------------------- #
    def _confirm_box(self, title: str, text: str, action: str | None = None) -> tuple:
        """確認の窓(既定とエスケープはキャンセル。Enter だけでは取り返しのつかない事をしない)。``(窓, 実行のボタン)``。"""
        tr = self.ctl.tr
        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setWindowTitle(title)
        box.setText(text)
        ok = box.addButton(action or title, QtWidgets.QMessageBox.AcceptRole)
        cancel = box.addButton(tr(km.BTN_CANCEL), QtWidgets.QMessageBox.RejectRole)
        box.setDefaultButton(cancel)
        box.setEscapeButton(cancel)
        cancel.setFocus()
        return box, ok

    def _confirm(self, title: str, text: str, action: str | None = None) -> bool:
        box, ok = self._confirm_box(title, text, action)
        try:
            box.exec()
            return box.clickedButton() is ok
        finally:
            box.deleteLater()

    def _inform(self, title: str, text: str) -> None:
        QtWidgets.QMessageBox.warning(self, title, text)

    def _ask_open(self) -> str:
        return QtWidgets.QFileDialog.getOpenFileName(self, self.ctl.tr(km.BTN_IMPORT), "",
                                                     self.ctl.tr(km.FILE_FILTER))[0]

    def _ask_save(self) -> str:
        return QtWidgets.QFileDialog.getSaveFileName(self, self.ctl.tr(km.BTN_EXPORT), "fullseye-studio-keys.json",
                                                     self.ctl.tr(km.FILE_FILTER))[0]


# --------------------------------------------------------------------------- #
# 制御役(読み込み・保存・配る・設定の窓)
# --------------------------------------------------------------------------- #
class KeymapController(QtCore.QObject):
    """窓 1 つのキーの割り当ての持ち主(``win._keymap``)。変えたら保存して配る。"""

    changed = QtCore.Signal()

    def __init__(self, win, settings=None, tr=None, lang=None, flash=None, python_editor_editops=None, model=None):
        super().__init__(win)
        self.win = win
        self.model = model                                     # パイプライン(段の op の名前を引く。無ければ win._pymode.model)
        self._py_editops = python_editor_editops               # None = 今ある Python エディタの欄を見て決める
        self.lang_problems: list = []                          # 今の言語で効かない上書き(言語の切り替えの後)
        self._settings = settings
        self._lang = lang or (lambda: getattr(win, "_lang", "en"))
        self.tr = km.make_tr(self._lang, first=tr)
        self.flash = flash if flash is not None else getattr(win, "_flash", None)
        self.keymap = km.Keymap()
        self.load_problems: list = []
        self._loaded_raw: str | None = None                     # 起動の時に使えなかった元の文字列(保存の前に残す)
        self.dialog: KeyboardDialog | None = None

    # ---- 設定 -------------------------------------------------------------- #
    def store(self):
        if self._settings is None:
            return None
        try:
            return self._settings()
        except Exception:                                      # noqa: BLE001 -- 設定が読めなくてもキーは動く
            return None

    def load(self) -> list:
        """保存してあった上書きを読む。壊れた分は捨てて状態行に 1 行(数えるのは捨てた上書き)。何が来ても例外を出さない。

        起動では設定を書き直さない(版を戻した・新しい版の設定を消さない)。利用者が変えて保存する時に、使えなかった
        元の文字列を ``keymap/user.backup`` に残す。
        """
        s = self.store()
        try:
            value = s.value(km.SETTINGS_KEY) if s is not None else None
        except Exception:                                      # noqa: BLE001 -- 設定が読めなくてもキーは動く
            value = None
        if value is not None and not isinstance(value, str):
            value = repr(value)                                # 型の違う値(手で書き換えた設定)= 壊れている
        try:
            self.keymap, probs = km.from_settings_text(value, self.fixed_entries(), self.places)
        except Exception as exc:                               # noqa: BLE001 -- 何が来ても既定で起動する
            self.keymap, probs = km.Keymap(), [km.Problem("warning", "settings_broken", detail=type(exc).__name__)]
        self.load_problems = [p for p in probs if p.level != "info"]
        self._loaded_raw = value if self.load_problems else None
        text = self._load_message(probs)
        if text and self.flash:
            try:
                self.flash(text)
            except Exception:                                  # noqa: BLE001
                pass
        return probs

    def _load_message(self, probs: list) -> str | None:
        codes = {p.code for p in probs}
        if "settings_newer" in codes:
            return self.tr(km.MSG_LOAD_NEWER)
        if "settings_broken" in codes:
            return self.tr(km.MSG_LOAD_BROKEN)
        n = len(km.dropped_commands(probs))
        if n:
            return self.tr(km.MSG_LOAD_PROBLEM) % n
        if any(p.level == "error" for p in probs):
            return self.tr(km.MSG_LOAD_PART)
        return None                                            # 警告だけ(当てている): 起動では言わない。設定の窓で見せる

    def save(self) -> bool:
        s = self.store()
        if s is None:
            return False
        if self._loaded_raw is not None:                       # 起動の時に使えなかった元の文字列を 1 つ残してから書く
            s.setValue(km.BACKUP_KEY, self._loaded_raw)
            self._loaded_raw = None
        self.load_problems = []
        if self.keymap.overrides() or self.keymap.preset != km.DEFAULT_PRESET:
            s.setValue(km.SETTINGS_KEY, self.keymap.to_json())
        else:
            s.remove(km.SETTINGS_KEY)
        s.sync()
        return True

    # ---- 配る -------------------------------------------------------------- #
    def fixed_entries(self) -> list:
        return collect_fixed(self.win)

    @property
    def places(self) -> dict:
        """当たりを数える場所の表。Python エディタの窓に矩形選択の部品が本当に付いているかで選ぶ。"""
        attached = self._py_editops
        if attached is None:
            dlg = getattr(self.win, "_pyedit_dlg", None)
            attached = False
            if dlg is not None and _valid(dlg):
                attached = any(eq.get(e) is not None for e in dlg.findChildren(QtWidgets.QPlainTextEdit))
        return km.PLACES if attached else km.PLACES_PLAIN_PYTHON_EDITOR

    def recheck(self, flash: bool = True) -> list:
        """表全体を今の言語で調べ直す(言語の切り替えの後)。効かなくなった上書き(今の言語のメニューバーの
        ニーモニックと当たる等)を ``lang_problems`` に置き、``flash`` なら状態行に 1 行。上書きは外さない。"""
        try:
            probs = self.keymap.problems(self.fixed_entries(), self.places)
        except Exception as exc:                               # noqa: BLE001 -- 表示の付け直しが窓を壊さない
            print("studio_keymap_qt: %s: %s" % (type(exc).__name__, exc))
            probs = []
        over = self.keymap.overrides()
        mine = []
        for p in probs:
            if p.level != "error":
                continue
            for c in (p.command, p.other):
                if c in over:
                    q = km._as_seen_from(p, c)
                    if q not in mine:
                        mine.append(q)
        self.lang_problems = mine
        if flash and mine and self.flash:
            try:
                self.flash(self.tr(km.MSG_LANG_PROBLEM) % len({p.command for p in mine}))
            except Exception:                                  # noqa: BLE001
                pass
        return mine

    def apply(self) -> dict:
        report = apply_keymap(self.win, self.keymap, self._lang)
        self.changed.emit()
        return report

    def _commit(self) -> None:
        self.save()
        self.recheck(flash=False)
        self.apply()

    # ---- 変える ------------------------------------------------------------ #
    def check(self, cid: str, keys) -> list:
        return self.keymap.check(cid, keys, self.fixed_entries(), self.places)

    def assign(self, cid: str, keys) -> list:
        """``cid`` のキーを ``keys`` にする。当たり(error)があれば何も変えずに問題を返す。"""
        probs = self.keymap.assign(cid, keys, self.fixed_entries(), self.places)
        if not any(p.level == "error" for p in probs):
            self._commit()
        return probs

    def reset(self, cid: str) -> list:
        """``cid`` を型の既定に戻す。戻すと当たり(error)ができるなら戻さずに問題を返す(相手は勝手に外さない)。"""
        if not self.keymap.is_changed(cid):
            return []
        probs = self.keymap.check(cid, self.keymap.preset_keys(cid), self.fixed_entries(), self.places)
        if any(p.level == "error" for p in probs):
            return probs
        self.keymap.reset(cid)
        self._commit()
        return probs

    def reset_all(self) -> int:
        n = self.keymap.reset_all()
        self._commit()
        return n

    def switch_preset(self, name: str) -> list:
        dropped = self.keymap.switch_preset(name, self.fixed_entries(), self.places)
        self._commit()
        return dropped

    def export_file(self, path: str) -> int:
        """上書きを JSON に書き出す(LF、UTF-8)。一時ファイルに書いてから置き換える。書いた上書きの数。

        書けなければ ``OSError``(途中のファイルは残さない)。
        """
        tmp = path + ".tmp-%d" % os.getpid()
        try:
            with open(tmp, "wb") as fh:
                fh.write(self.keymap.to_json().encode("utf-8"))
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        return len(self.keymap.overrides())

    def import_file(self, path: str) -> tuple:
        """JSON を読み込んで当てる(確認なし。設定の窓は read_import → 確認 → use_import)。駄目なら何も変えず
        ``(False, problems)``。"""
        new, probs = self.read_import(path)
        if new is None:
            return False, probs
        self.use_import(new)
        return True, probs

    def use_import(self, new: km.Keymap) -> None:
        """読み込んだ表に置き換える。前の表(変えた物があれば)を keymap/user.previous に 1 世代残す。"""
        s = self.store()
        if s is not None and (self.keymap.overrides() or self.keymap.preset != km.DEFAULT_PRESET):
            s.setValue(km.PREVIOUS_KEY, self.keymap.to_json())
        self.keymap = new
        self._commit()

    def read_import(self, path: str) -> tuple:
        """JSON を読んで検査する(まだ当てない)。``(Keymap, 警告)`` か ``(None, problems)``。"""
        try:
            size = os.path.getsize(path)
            if size > km.MAX_IMPORT_BYTES:
                return None, [km.Problem("error", "too_big", detail="%d bytes" % size)]
            with open(path, "rb") as fh:
                data = fh.read(km.MAX_IMPORT_BYTES + 1)
        except OSError as exc:
            return None, [km.Problem("error", "bad_json", detail=str(exc)[:80])]
        return km.import_text(data, self.fixed_entries(), self.places)

    # ---- 表示 -------------------------------------------------------------- #
    def _fixed_title(self, e: km.Entry) -> str:
        kind = e.command.split(":", 1)[0]
        tmpl = {"menu": km.MSG_MENU_BAR, "menu_other": km.MSG_MENU_OTHER}.get(kind, km.MSG_TEXT_KEY)
        return self.tr(tmpl) % e.command.split(":", 1)[1]

    def rows(self, include_unbound: bool = True) -> list:
        """一覧の行(F1 の表・設定の窓)。今の言語のメニューバーのニーモニックも組み込みとして並べる。"""
        menu = [e._replace(title=self._fixed_title(e)) for e in self.fixed_entries() if e.scope == "menu_bar"]
        return km.shortcut_rows(self.keymap, self.tr, extra=menu, include_unbound=include_unbound)

    def describe(self, p: km.Problem) -> str:
        titles = {e.command: self._fixed_title(e) for e in self.fixed_entries()}
        return km.describe_problem(p, self.tr, titles)

    # ---- F1 = ここのヘルプ(D127) ----------------------------------------- #
    def _stage_or_op(self, focus) -> str | None:
        """段の一覧にフォーカスがあれば選んだ段の op、無ければ op の一覧で選んだ op、無ければ選んだ段の op。"""
        win = self.win
        model = self.model if self.model is not None else getattr(getattr(win, "_pymode", None), "model", None)
        stages = getattr(model, "stages", None) or []
        sl, ol = getattr(win, "_stage_list", None), getattr(win, "_op_list", None)
        stage_op = None
        if sl is not None:
            row = sl.currentRow()
            item = sl.currentItem()
            idx = item.data(_K.UserRole) if item is not None else None
            idx = idx if isinstance(idx, int) else row
            if 0 <= idx < len(stages):
                stage_op = stages[idx][0]
        if sl is not None and stage_op and (focus is sl or (focus is not None and sl.isAncestorOf(focus))):
            return stage_op
        if ol is not None and ol.currentItem() is not None:
            name = ol.currentItem().data(_K.UserRole)
            if name:
                return name
        return stage_op

    def help_here(self) -> str:
        """F1 = ここのヘルプ: コードの欄のカーソルの下の op / 選んだ段 / 選んだ op / 何も無ければキーの一覧。

        何を開いたか(``code:<op>`` / ``op:<op>`` / ``keys``)を返す。初回の枝の F1(07e66baa0a)と同じ順に、コードの欄を足した。
        """
        win = self.win
        show = (getattr(win, "_help", None) or {}).get("show")
        focus = QtWidgets.QApplication.focusWidget()
        prog = getattr(win, "_program", None)
        ed = prog.get("edit") if isinstance(prog, dict) else None
        if ed is not None and focus is not None and (focus is ed or ed.isAncestorOf(focus)):
            word = ed.word_under_cursor() if hasattr(ed, "word_under_cursor") else ""
            if word and word in (getattr(ed, "_words", None) or ()):
                opener = getattr(ed, "on_open_help", None) or show
                if callable(opener):
                    opener(word)
                    return "code:" + word
        name = self._stage_or_op(focus)
        if name and callable(show):
            show(name)
            return "op:" + name
        self.open_dialog()
        return "keys"

    def save_program(self) -> str:
        """コードの欄の Ctrl+S(D48): Python のモードならプログラム(pymode_save)、パイプラインのモードならパイプライン
        (save_pipeline)を保存する。撃った QAction の ID(撃てなければ空)。"""
        acts = getattr(self.win, "_actions", None) or {}
        pm = getattr(self.win, "_pymode", None)
        key = "pymode_save" if pm is not None and getattr(pm, "active", False) else "save_pipeline"
        a = acts.get(key)
        if isinstance(a, QtGui.QAction) and _valid(a) and a.isEnabled():
            a.trigger()
            return key
        if key == "save_pipeline" and self.flash:              # 空のパイプライン: 黙らずに言う
            try:
                self.flash(self.tr(km.MSG_NOTHING_TO_SAVE))
            except Exception:                                  # noqa: BLE001
                pass
        return ""

    def open_dialog(self) -> KeyboardDialog:
        """設定の窓を出す(2 度目は同じ窓を前へ)。"""
        if self.dialog is None or not _valid(self.dialog):
            self.dialog = KeyboardDialog(self)
            _state(self.win).on_lang.append(lambda: self.dialog.retranslate() if _valid(self.dialog) else None)
        self.dialog.refill()
        first = not self.dialog.isVisible()
        self.dialog.show()
        self.dialog.raise_()
        if first:
            self.dialog.search.setFocus()                      # 開いた時は検索欄(型の箱をキー 1 つで変えない)
        return self.dialog


def get(win) -> KeymapController | None:
    """窓に付いている KeymapController(無ければ None)。"""
    ctl = getattr(win, "_keymap", None)
    return ctl if isinstance(ctl, KeymapController) and _valid(ctl) else None


_PALETTE_WORDS = ("キー キーボード ショートカット 設定 割り当て 変更 keyboard shortcuts keys keybindings keymap "
                  "customize assign")
_PALETTE_HELP_WORDS = "ヘルプ ここ 説明 op help here f1 context"


def _take_over(action: QtGui.QAction, slot) -> None:
    """``action`` の受け手を全部外して ``slot`` だけにする(本体・他の枝の古い受け手を残さない)。"""
    import warnings                                            # noqa: PLC0415
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        try:
            action.triggered.disconnect()
        except (RuntimeError, TypeError):                      # 受け手が 1 つも無い
            pass
    action.triggered.connect(slot)


def _install_help(win, ctl: "KeymapController", st: _State, palette_words) -> None:
    """F1 = ここのヘルプ(help_here)と、キーの一覧(shortcuts)= 設定の窓を本物の窓へ付ける(D127・D19)。"""
    acts = getattr(win, "_actions", None)
    acts = acts if isinstance(acts, dict) else {}
    help_menu = (getattr(win, "_menus", None) or {}).get("help")
    adopted = next((acts[k] for k, cid in km.ADOPTED.items() if cid == "help_here"
                    and isinstance(acts.get(k), QtGui.QAction)), None)
    if adopted is not None:                                    # 初回の枝の F1 の QAction をそのまま使う
        a = adopted
    else:
        a = QtGui.QAction(ctl.tr(km.BY_ID["help_here"].title), win)
        a.setToolTip(ctl.tr(km.TIP_HELP_HERE))
        a.setStatusTip(ctl.tr(km.TIP_HELP_HERE))
        sc = acts.get("shortcuts")
        if help_menu is not None:
            before = sc if isinstance(sc, QtGui.QAction) and sc in help_menu.actions() else None
            help_menu.insertAction(before, a)
        win.addAction(a)
        st.on_lang.append(lambda: (a.setText(ctl.tr(km.BY_ID["help_here"].title)),
                                   a.setToolTip(ctl.tr(km.TIP_HELP_HERE)),
                                   a.setStatusTip(ctl.tr(km.TIP_HELP_HERE))) if _valid(a) else None)
    _take_over(a, lambda _=False: ctl.help_here())
    st.own["help_here"] = a
    for old, new in km.ABSORBED.items():                       # 意味を吸わせた本体の QAction: キーを外して隠す
        b = acts.pop(old, None)
        if isinstance(b, QtGui.QAction) and _valid(b):
            b.setShortcuts([])
            b.setVisible(False)
            b.setEnabled(False)
        if palette_words is not None and old in palette_words:
            palette_words[new] = (palette_words.get(new, "") + " " + palette_words[old]).strip()
    sc = acts.get("shortcuts")
    if isinstance(sc, QtGui.QAction):                          # キーの一覧 = 設定の窓(古いモーダルの表は出さない)
        _take_over(sc, lambda _=False: ctl.open_dialog())


def _install_image_focus(win, st: _State) -> None:
    """「画像だけを抜ける」(Esc)を、画像だけ(image_focus がチェック)の間だけ有効にする(D10。窓の Esc を食わない)。"""
    focus = next((o for o in st.targets.get("image_focus", ()) if isinstance(o, QtGui.QAction) and _valid(o)), None)
    leave = next((o for o in st.targets.get("leave_image_focus", ()) if isinstance(o, QtGui.QAction) and _valid(o)),
                 None)
    if focus is None or leave is None or not focus.isCheckable():
        return
    leave.setEnabled(focus.isChecked())
    focus.toggled.connect(lambda on: leave.setEnabled(bool(on)) if _valid(leave) else None)


def install(win, settings=None, tr=None, lang=None, flash=None, palette_words: dict | None = None,
            python_editor_editops: bool | None = None, model=None) -> KeymapController:
    """窓 ``win`` にキーの割り当てを取り付ける(2 度呼んでも 1 つ)。保存してあった上書きを読み、配る。

    ``settings``: ``QSettings`` を返す関数(``studio._settings``。無ければ覚えない)/ ``tr``: Studio の ``tr`` /
    ``lang``: 今の言語の符号を返す関数 / ``flash``: 状態行へ 1 行(無ければ ``win._flash``)/
    ``palette_words``: ``studio.PALETTE_WORDS``(パレットの別名を足す)/ ``python_editor_editops``: Python エディタの
    窓にも矩形選択の部品を付ける配線なら True(None = 開いている Python エディタを見て決める)/ ``model``: パイプライン
    (F1 で選んだ段の op を引く。無ければ ``win._pymode.model``)。
    """
    ctl = get(win)
    if ctl is not None:
        return ctl
    ctl = KeymapController(win, settings=settings, tr=tr, lang=lang, flash=flash,
                           python_editor_editops=python_editor_editops, model=model)
    win._keymap = ctl
    st = _state(win)
    a = QtGui.QAction(ctl.tr(km.ACT_SETTINGS), win)
    a.setObjectName("keymap:keyboard_settings")
    a.triggered.connect(lambda _=False: ctl.open_dialog())
    win.addAction(a)
    st.own["keyboard_settings"] = a
    tools = (getattr(win, "_menus", None) or {}).get("tools")
    if tools is not None:
        sys_act = getattr(win, "_act_system_settings", None)
        acts = tools.actions()
        idx = next((i for i, x in enumerate(acts) if x is sys_act), -1)
        tools.insertAction(acts[idx + 1] if 0 <= idx < len(acts) - 1 else None, a)
    st.on_lang.append(lambda: a.setText(ctl.tr(km.ACT_SETTINGS)) if _valid(a) else None)
    if palette_words is not None:
        palette_words.setdefault("keyboard_settings", _PALETTE_WORDS)
        palette_words.setdefault("help_here", _PALETTE_HELP_WORDS)
    _install_help(win, ctl, st, palette_words)
    st.on_lang.append(lambda: ctl.recheck(flash=True))       # 言語を変えたら、今の言語で効かない上書きを知らせる
    ctl.load()
    ctl.apply()
    _install_image_focus(win, st)
    return ctl
