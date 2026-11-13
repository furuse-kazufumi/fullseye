# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_keymap — Fullseye Studio のキーの割り当て(Qt なし): 登録簿・型・利用者の上書き・当たりの判定・保存の形。

利用者がショートカットキーを自分で決められるようにする部品のうち、**画面に依らない部分**をここに置く。
Qt の側(``studio_keymap_qt``)は、ここで決めたキーを本物の ``QAction`` / ``QShortcut`` / エディタの部品へ
配るだけ。メニューの右に出るキー・F1 の一覧・設定の窓・文書の表は、どれもここの 1 つの表から引く。

決めた事
--------
* **コマンドの ID** は英語の snake_case(Studio の ``win._actions`` の鍵をそのまま使う)。ID の無かった物は
  棚卸し(2026-11-13)の名前の付け方で決めた(``image_focus``・``work_mode_build`` など)。矩形選択の部品の
  操作は ``editops_<操作>``(``.`` を ``_`` に。コマンドパレットの鍵と同じ)。
* **範囲**(``SCOPES``)はキーが効く場所。範囲どうしの重なりは ``PLACES``(フォーカスのある所 → そこで同時に
  効く範囲)で表す。Qt の表(QAction / QShortcut)どうしが 1 か所で同じキーを持つと Qt はどちらも撃たないので
  **当たり(error)**。部品が自分で先に受ける範囲(Program 欄・エディタ・検索欄・3-D 表示)は、窓全体の同じ
  キーより先に取るだけなので **隠す(info)**。同じエディタの部品どうしは error(片方が黙って負ける)。
* **型(プリセット)** は 2 つ。``visual_studio`` = Studio の既定(今までのキーそのまま)、``vscode`` = VS Code の
  慣例(エディタの Ctrl+D = 次の一致を足す、行の複製 = Shift+Alt+Down など)。型は既定の差分として持つ。
* **保存するのは利用者の上書きだけ**(型との差分)。キーを外した事は空の並びで明示する。設定の 1 つの鍵
  (``SETTINGS_KEY``)に JSON で書く。読めない・壊れた分は捨てて知らせ、起動は止めない(型違い・深い入れ子・
  重なった鍵でも例外を出さない)。**起動では書き直さない**: 利用者が変えて保存する時に、使えなかった元の文字列を
  ``BACKUP_KEY`` に残してから書く。新しい版の設定(``version`` が大きい)は読まずに残す。
* **書き出し・読み込み** も同じ JSON。読み込みは fail-closed(型・鍵・ID・キー・当たりのどれか 1 つでも駄目なら
  何も当てない)。
* **2 打鍵の和音**(``Ctrl+K, Ctrl+S``)は Qt の表で動く範囲(窓全体・段の一覧・別窓)だけ。エディタの部品は
  1 打ずつ判定しているので、和音は受けない(状態を持つ判定が要る。``SCOPES[...].chords``)。
"""
from __future__ import annotations

import itertools
import json
import os
import re
import unicodedata
from typing import Callable, Iterable, NamedTuple, Sequence

import studio_editops as _eo

FORMAT = "fullseye-studio-keymap"
VERSION = 1
#: 設定(``studio._settings()``)の鍵。値は JSON の文字列 1 つ。
SETTINGS_KEY = "keymap/user"
#: 起動の時に使えなかった元の文字列(利用者が変えて保存する時に 1 つだけ残す)。
BACKUP_KEY = SETTINGS_KEY + ".backup"
DEFAULT_PRESET = "visual_studio"
#: 読み込みの上限(バイト)。キーの表はどんなに多くても数 KB。
MAX_IMPORT_BYTES = 256 * 1024
MAX_KEYS_PER_COMMAND = 4
MAX_STROKES = 2
#: JSON の入れ子の上限(キーの表は 3 段。これより深い物は読む前に断る = 再帰の上限に頼らない)。
MAX_DEPTH = 32


# --------------------------------------------------------------------------- #
# 範囲と場所
# --------------------------------------------------------------------------- #
class Scope(NamedTuple):
    """キーが効く範囲。``mech``: ``qt``(Qt の表で撃つ)/ ``filter``(部品が自分で先に受ける)/ ``text``
    (テキスト欄の標準のキー)。``group`` が同じ ``filter`` は同じ部品の上にある。"""
    name: str
    title: str
    mech: str
    group: str
    text_free: bool = False
    when: str | None = None
    chords: bool = False


SCOPES = {s.name: s for s in (
    Scope("window", "Main window", "qt", "main", chords=True),
    Scope("pipeline_list", "Pipeline stage list", "qt", "stage_list", chords=True),
    Scope("graphics_subwindow", "Graphics window", "qt", "graphics", chords=True),
    Scope("program_editor", "Program editor", "filter", "code_editor"),
    Scope("editor", "Code editors", "filter", "code_editor"),
    Scope("editor_box", "Code editors (box selection)", "filter", "code_editor", when="box"),
    Scope("editor_no_comment", "Code editors without their own comment key", "filter", "code_editor"),
    Scope("program_find", "Program find field", "filter", "find_field"),
    Scope("python_editor_window", "Python Editor window", "qt", "python_editor", chords=True),
    Scope("image_viewer_window", "Image Viewer window", "qt", "image_viewer", text_free=True, chords=True),
    Scope("view3d", "3-D view", "filter", "view3d", text_free=True),
    Scope("text", "Text fields", "text", "text"),
)}

#: フォーカスのある所 → (名前, そこで同時に効く範囲)。当たりはここで重なる範囲の間だけ数える。
PLACES = {
    "main": ("the main window", ("window",)),
    "text_field": ("text fields", ("window", "text")),
    "stage_list": ("the stage list", ("window", "pipeline_list")),
    "program_editor": ("the Program editor", ("window", "program_editor", "editor", "editor_box", "text")),
    "program_find": ("the Program find field", ("window", "program_find", "text")),
    "graphics": ("graphics windows", ("window", "graphics_subwindow")),
    "python_editor": ("the Python Editor", ("python_editor_window", "editor", "editor_box", "editor_no_comment",
                                            "text")),
    "image_viewer": ("the Image Viewer", ("image_viewer_window",)),
    "view3d": ("the 3-D view", ("view3d",)),
}


# --------------------------------------------------------------------------- #
# キーの書き方
# --------------------------------------------------------------------------- #
class KeyParseError(ValueError):
    """キーを読めない。``code`` は ``bad_key`` / ``too_many_strokes``。"""

    def __init__(self, code: str, key: str):
        super().__init__("%s: %r" % (code, key))
        self.code = code
        self.key = key


_MOD_ORDER = ("Ctrl", "Shift", "Alt", "Meta")
_MOD_NAMES = {"ctrl": "Ctrl", "control": "Ctrl", "strg": "Ctrl", "shift": "Shift", "umschalt": "Shift",
              "alt": "Alt", "meta": "Meta", "win": "Meta", "super": "Meta"}
_NAMED = {"esc": "Esc", "escape": "Esc", "tab": "Tab", "backspace": "Backspace", "return": "Return",
          "enter": "Enter", "ins": "Ins", "insert": "Ins", "del": "Del", "delete": "Del", "pause": "Pause",
          "print": "Print", "sysreq": "SysReq", "home": "Home", "end": "End", "left": "Left", "up": "Up",
          "right": "Right", "down": "Down", "pgup": "PgUp", "pageup": "PgUp", "pgdown": "PgDown",
          "pagedown": "PgDown", "space": "Space", "menu": "Menu"}
_FKEY = re.compile(r"^[Ff]([1-9]|[12][0-9]|3[0-5])$")


def _stroke(text: str) -> str:
    s = re.sub(r"\s*\+\s*", "+", text.strip())
    if not s:
        raise KeyParseError("bad_key", text)
    if s == "+":
        parts, last = [], "+"
    elif s.endswith("++"):
        parts, last = s[:-2].split("+"), "+"
    else:
        *parts, last = s.split("+")
    mods = set()
    for p in parts:
        m = _MOD_NAMES.get(p.lower())
        if m is None:
            raise KeyParseError("bad_key", text)
        mods.add(m)
    low = last.lower()
    if not last or low in _MOD_NAMES:
        raise KeyParseError("bad_key", text)
    if low == "backtab":
        mods.add("Shift")
        name = "Tab"
    elif low in _NAMED:
        name = _NAMED[low]
    elif _FKEY.match(last):
        name = "F" + last[1:]
    elif len(last) == 1 and last.isprintable() and not last.isspace() and ord(last) < 128:
        name = last.upper()
    else:
        raise KeyParseError("bad_key", text)
    return "+".join([m for m in _MOD_ORDER if m in mods] + [name])


def _split_strokes(text: str) -> list:
    """``Ctrl+K, Ctrl+S`` / ``ctrl+k ctrl+s``(VS Code の書き方)→ 打鍵の並び。``Ctrl+,`` のコンマはキー。"""
    text = re.sub(r"\s*\+\s*", "+", text)
    parts, cur = [], ""
    for ch in text:
        if ch == "," and cur.strip() and not cur.endswith("+"):
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    out = []
    for p in parts:
        out.extend(x for x in p.split() if x)
    return out


def normalize_sequence(text: str) -> str:
    """キーの書き方をそろえる(``shift+ctrl+k`` → ``Ctrl+Shift+K``、打鍵の間は ``, ``)。読めなければ KeyParseError。"""
    if not isinstance(text, str):
        raise KeyParseError("bad_key", repr(text))
    strokes = _split_strokes(text)
    if not strokes:
        raise KeyParseError("bad_key", text)
    if len(strokes) > MAX_STROKES:
        raise KeyParseError("too_many_strokes", text)
    return ", ".join(_stroke(s) for s in strokes)


def parse_keys(value) -> tuple:
    """``"F5|Ctrl+R"`` / ``["F5", "Ctrl+R"]`` → 正規化したキーの並び(順を保ち、同じ物は 1 つ)。"""
    items = value.split("|") if isinstance(value, str) else list(value)
    out = []
    for item in items:
        if isinstance(item, str) and not item.strip():
            continue
        k = normalize_sequence(item)
        if k not in out:
            out.append(k)
    return tuple(out)


def _split_stroke(stroke: str) -> tuple:
    """正規化した 1 打 → ``(修飾の並び, キー)``。"""
    mods, rest = [], stroke
    progressed = True
    while progressed:
        progressed = False
        for m in _MOD_ORDER:
            if rest.startswith(m + "+") and len(rest) > len(m) + 1:
                mods.append(m)
                rest = rest[len(m) + 1:]
                progressed = True
                break
    return mods, rest


_DE_MODS = {"Ctrl": "Strg", "Shift": "Umschalt"}
_DE_KEYS = {"Up": "Auf", "Down": "Ab", "Left": "Links", "Right": "Rechts", "Return": "Eingabe", "Enter": "Eingabe",
            "Del": "Entf", "Home": "Pos1", "End": "Ende", "Backspace": "Rücktaste", "Space": "Leertaste",
            "Ins": "Einfg"}


def display_key(key: str, lang: str = "en") -> str:
    """文の中に書く時のキーの文字。ドイツ語の文は ``Strg`` ``Umschalt`` ``Auf`` …(i18n.json の書き方に合わせる)。

    メニューの右と設定の窓は Qt の書き方(``Ctrl``)のまま(Studio は Qt の訳を読み込んでいない)。
    """
    if lang != "de":
        return key
    out = []
    for st in key.split(", "):
        mods, name = _split_stroke(st)
        out.append("+".join([_DE_MODS.get(m, m) for m in mods] + [_DE_KEYS.get(name, name)]))
    return ", ".join(out)


def _spellings(key: str) -> list:
    """文の中でこのキーを探す時の書き方の全部(修飾の順の入れ替え・Enter と Return・ドイツ語)。"""
    if ", " in key:
        return [key, display_key(key, "de")]
    mods, name = _split_stroke(key)
    names = {name}
    if name in ("Return", "Enter"):
        names |= {"Return", "Enter"}
    out = []
    for perm in itertools.permutations(mods):
        for n in sorted(names):
            for mod_map, key_map in ((None, None), (_DE_MODS, _DE_KEYS)):
                ms = [mod_map.get(m, m) if mod_map else m for m in perm]
                nn = key_map.get(n, n) if key_map else n
                s = "+".join(ms + [nn])
                if s not in out:
                    out.append(s)
    return out


# --------------------------------------------------------------------------- #
# 登録簿
# --------------------------------------------------------------------------- #
class Command(NamedTuple):
    """コマンド 1 つ。``keys`` は既定(Visual Studio 風の型)。``target`` は Qt の側が本物を探す手がかり
    (``action:<win._actions の鍵>`` / ``label:<英語の表示名>`` / ``attr:<窓の属性>`` / ``work_mode:<作業モード>`` /
    ``editops:<操作>`` / ``shortcut:<別窓>:<既定のキー>`` / ``own:<この部品が作る>``)。``fixed`` は変えられない
    (当たりの検査と一覧のためだけに載せる)。``mentions`` は表示の文がキーを書いている別のコマンド。
    ``own_title`` は表示名の訳をこの部品の表で引く(それ以外は Studio の訳の表)。"""
    id: str
    title: str
    scope: str
    keys: tuple = ()
    target: str = ""
    fixed: bool = False
    when: str | None = None
    mentions: tuple = ()
    ide: str = ""
    own_title: bool = False


def _c(cid, title, scope, keys="", target=None, **kw) -> Command:
    if target is None:
        target = "" if kw.get("fixed") else "action:" + cid
    return Command(cid, title, scope, parse_keys(keys), target, **kw)


def _editops_commands() -> tuple:
    scope_of = {"box": "editor_box", "no_own_comment": "editor_no_comment"}
    return tuple(Command(editops_id(b.command), b.title, scope_of.get(b.when, "editor"), parse_keys(list(b.keys)),
                         "editops:" + b.command) for b in _eo.KEYMAP)


def editops_id(command: str) -> str:
    """矩形選択の部品の操作の名前(``line.duplicate``)→ コマンドの ID(``editops_line_duplicate``)。"""
    return "editops_" + command.replace(".", "_")


_W, _P, _E = "window", "pipeline_list", "program_editor"
COMMANDS = (
    # ---- 窓全体: File ----
    _c("open_image", "Open image…", _W, "Ctrl+O"),
    _c("image_viewer", "Image Viewer…", _W, "Ctrl+Shift+I", "label:Image Viewer…"),
    _c("demo", "Synthetic demo", _W),
    _c("open_pipeline", "Open pipeline…", _W, "Ctrl+Shift+O"),
    _c("save_pipeline", "Save pipeline…", _W, "Ctrl+Shift+S"),
    _c("export", "Export…", _W, "Ctrl+E"),
    _c("code_to_editor", "Pipeline as code → editor", _W, "Ctrl+Shift+E", "label:Pipeline as code → editor"),
    _c("project_open", "Open folder…", _W),
    _c("project_new", "New project…", _W),
    _c("project_panel", "Project", _W, "Ctrl+Shift+J"),
    _c("samples", "Samples & code…", _W),
    _c("save_result", "Save result…", _W, "Ctrl+S"),
    _c("save_view", "Save view as shown…", _W),
    _c("copy_result", "Copy result image", _W),
    _c("quit", "Quit", _W, "Ctrl+Q"),
    _c("pymode_new", "New Python program", _W, "Ctrl+N"),
    _c("pymode_open", "Open Python program…", _W, "Ctrl+Alt+O"),
    _c("pymode_save", "Save Python program", _W, "Ctrl+Alt+S"),
    _c("pymode_save_as", "Save Python program as…", _W, "Ctrl+Alt+Shift+S"),
    # ---- 窓全体: Edit ----
    _c("undo", "Undo", _W, "Ctrl+Z"),
    _c("redo", "Redo", _W, "Ctrl+Shift+Z"),
    _c("pin_a", "Pin as A", _W, "Ctrl+Shift+A"),
    _c("clear", "Clear pipeline", _W, "Ctrl+Shift+Backspace"),
    _c("focus_search", "Focus operator search", _W, "Ctrl+F"),
    # ---- 窓全体: View ----
    _c("zoom_in", "Zoom in", _W, "Ctrl+="),
    _c("zoom_out", "Zoom out", _W, "Ctrl+-"),
    _c("fit", "Fit to window", _W, "Ctrl+0"),
    _c("actual_size", "Actual size (1:1)", _W, "Ctrl+Alt+1"),
    _c("surface_3d", "3D surface", _W, "Ctrl+Alt+3"),
    _c("viewer_3d", "3D viewer…", _W, "Ctrl+Alt+4"),
    # ---- 窓全体: Run ----
    _c("run_all", "Run all", _W, "Ctrl+Return", mentions=("dbg_run",)),
    _c("run_selection", "Run selected lines", _W, "Ctrl+Alt+Return"),
    _c("dbg_run", "Run all (from any panel)", _W, "F5|Ctrl+R", own_title=True),
    _c("dbg_step", "Step (from any panel)", _W, "F6", own_title=True),
    _c("dbg_reset", "Reset to start (from any panel)", _W, "Shift+F5", own_title=True),
    _c("batch_apply", "Apply to folder…", _W),
    _c("verify_exported", "Verify exported Python…", _W, "Ctrl+Shift+R"),
    _c("holdout", "Validate on holdout…", _W, "Ctrl+H"),
    _c("pymode_python", "Python mode", _W),
    _c("pymode_pipeline", "Pipeline mode", _W),
    _c("pymode_toggle", "Switch Python / Pipeline mode", _W, "Ctrl+Alt+M"),
    _c("pymode_convert", "Convert to Python", _W),
    _c("pymode_debug", "Debug", _W),
    _c("pymode_release", "Release", _W),
    _c("pymode_config_toggle", "Switch Debug / Release", _W, "Ctrl+Alt+D"),
    _c("pymode_example", "Open the Python example", _W),
    _c("pymode_clear_output", "Clear output", _W),
    _c("pymode_run", "Run Python program", _W, mentions=("dbg_run",)),
    _c("pymode_step", "Step one line", _W, mentions=("dbg_step",)),
    _c("pymode_stop", "Stop the program", _W, "Ctrl+F2"),
    _c("pymode_breakpoint", "Toggle breakpoint", _W, "F9"),
    _c("pymode_condition", "Breakpoint condition…", _W),
    # ---- 窓全体: Window ----
    _c("work_mode_build", "Build pipeline", _W, "Ctrl+1", "work_mode:build"),
    _c("work_mode_compare", "Compare results", _W, "Ctrl+2", "work_mode:compare"),
    _c("work_mode_inspect", "Inspect values", _W, "Ctrl+3", "work_mode:inspect"),
    _c("work_mode_code", "Make code", _W, "Ctrl+4", "work_mode:code"),
    _c("image_focus", "Image focus", _W, "F11", "label:Image focus", mentions=("leave_image_focus",)),
    _c("leave_image_focus", "Leave image focus", _W, "Esc", "label:Leave image focus"),
    _c("find_panel", "Find panel…", _W, "Ctrl+Shift+P", "label:Find panel…"),
    _c("new_graphics_window", "New graphics window", _W, "Ctrl+G", "label:New graphics window"),
    _c("detach_graphics", "Detach graphics window", _W, "Ctrl+Shift+D"),
    _c("reattach_graphics", "Reattach graphics window", _W),
    # ---- 窓全体: Tools ----
    _c("palette", "Command palette…", _W, "Ctrl+P"),
    _c("feature_inspection", "Feature inspection…", _W, "Ctrl+F5"),
    _c("ledger_run", "Run a ledger op…", _W, "Ctrl+Shift+L"),
    _c("system_settings", "System settings…", _W, "Ctrl+,", "attr:_act_system_settings"),
    _c("keyboard_settings", "Customize keyboard shortcuts…", _W, "Ctrl+K, Ctrl+S", "own:keyboard_settings",
       own_title=True),
    # ---- 窓全体: Help ----
    _c("editops_howto", _eo.ACT_HOWTO, _W),
    _c("op_reference", "Operator reference…", _W, "Shift+F1"),
    _c("quick_guide", "Quick guide (en/ja/zh)", _W, "Shift+F2", "label:Quick guide (en/ja/zh)"),
    _c("shortcuts", "Keyboard shortcuts", _W, "F1"),
    _c("about", "About Fullseye Studio", _W),
    # ---- 段の一覧(フォーカスがある時だけ) ----
    _c("remove", "Remove stage", _P, "Del"),
    _c("duplicate_stage", "Duplicate stage", _P, "Ctrl+D"),
    _c("bypass", "Bypass stage (on/off)", _P, "Ctrl+B"),
    _c("move_up", "Move stage up", _P, "Ctrl+Up"),
    _c("move_down", "Move stage down", _P, "Ctrl+Down"),
    _c("move_top", "Move stage to top", _P, "Ctrl+Shift+Up"),
    _c("move_bottom", "Move stage to bottom", _P, "Ctrl+Shift+Down"),
    _c("reset", "Reset to start", _P, "Home", mentions=("dbg_reset",)),
    _c("step", "Step forward", _P, "Ctrl+Right", mentions=("dbg_step",)),
    # ---- Program 欄(欄の部品が窓の同じキーより先に受ける) ----
    _c("program_find", "Find in Program", _E, "Ctrl+F", ide="find", mentions=("focus_search",)),
    _c("program_replace", "Replace in Program", _E, "Ctrl+H", ide="replace"),
    _c("program_find_next", "Find next in Program", _E, "F3", ide="next"),
    _c("program_find_prev", "Find previous in Program", _E, "Shift+F3", ide="prev"),
    _c("program_comment", "Comment / uncomment lines", _E, "Ctrl+/", ide="comment"),
    _c("program_font_bigger", "Bigger editor text", _E, "Ctrl++|Ctrl+=", ide="zoom_in"),
    _c("program_font_smaller", "Smaller editor text", _E, "Ctrl+-", ide="zoom_out"),
    _c("program_help_here", "Help for the operator under the cursor", _E, "Shift+F1", ide="help",
       mentions=("shortcuts",)),
) + _editops_commands() + (
    # ---- 別窓(窓を開いた時に作る QShortcut) ----
    _c("python_editor_run", "Run (Python Editor)", "python_editor_window", "F5", "shortcut:python_editor:F5",
       own_title=True),
    _c("python_editor_save", "Save (Python Editor)", "python_editor_window", "Ctrl+S",
       "shortcut:python_editor:Ctrl+S", own_title=True),
    _c("python_editor_ledger_op", "Ledger op for the word under the cursor (Python Editor)", "python_editor_window",
       "Ctrl+Shift+L", "shortcut:python_editor:Ctrl+Shift+L", own_title=True),
    _c("image_viewer_fit", "Fit (Image Viewer)", "image_viewer_window", "F", "shortcut:image_viewer:F",
       own_title=True),
    _c("image_viewer_actual_size", "1:1 (Image Viewer)", "image_viewer_window", "1", "shortcut:image_viewer:1",
       own_title=True),
    _c("image_viewer_next", "Next image (Image Viewer)", "image_viewer_window", "Right",
       "shortcut:image_viewer:Right", own_title=True),
    _c("image_viewer_previous", "Previous image (Image Viewer)", "image_viewer_window", "Left",
       "shortcut:image_viewer:Left", own_title=True),
    # ---- 組み込み(この版では変えられない。部品の中に直接書いてあるキー。当たりの検査と一覧のため) ----
    _c("fixed_program_run_selection", "Run the selected Program lines (with a selection)", _E, "Ctrl+Return",
       fixed=True, when="selection", own_title=True),
    _c("fixed_program_close_find", "Close the find bar (while it is open)", _E, "Esc", fixed=True,
       when="find_bar", own_title=True),
    _c("fixed_complete", "Complete the word (Python)", "editor", "Ctrl+Space", fixed=True, own_title=True),
    _c("fixed_find_close", "Find field: close", "program_find", "Esc", fixed=True, own_title=True),
    _c("fixed_find_next", "Find field: next match", "program_find", "F3|Return", fixed=True, own_title=True),
    _c("fixed_find_prev", "Find field: previous match", "program_find", "Shift+F3|Shift+Return", fixed=True,
       own_title=True),
    _c("fixed_find_switch", "Find field: find / replace", "program_find", "Ctrl+F|Ctrl+H", fixed=True,
       own_title=True),
    _c("fixed_view3d_first_person", "3-D view: first-person mode", "view3d", "F", fixed=True, own_title=True),
    _c("fixed_view3d_move", "3-D view: move (first person)", "view3d", "W|A|S|D|E|Q|Space", fixed=True,
       own_title=True),
    _c("fixed_view3d_fov", "3-D view: field of view", "view3d", "+|=|]|-|[", fixed=True, own_title=True),
    _c("fixed_view3d_reset", "3-D view: reset", "view3d", "R", fixed=True, own_title=True),
    _c("fixed_view3d_wireframe", "3-D view: wireframe", "view3d", "W", fixed=True, own_title=True),
    _c("fixed_mdi_close", "Close the graphics window (Qt)", "graphics_subwindow", "Ctrl+F4|Ctrl+W", fixed=True,
       own_title=True),
)
BY_ID = {c.id: c for c in COMMANDS}
if len(BY_ID) != len(COMMANDS):                                 # pragma: no cover -- 登録簿の書き損じ
    raise RuntimeError("コマンドの ID が重なっている")

#: 型(プリセット)= 既定(Visual Studio 風)との差分。
PRESETS = {
    "visual_studio": {},
    "vscode": {
        "palette": ("Ctrl+Shift+P", "F1"),
        "find_panel": ("Ctrl+P",),
        "shortcuts": ("Ctrl+K, Ctrl+R",),
        "dbg_step": ("F10",),
        "editops_box_up": ("Ctrl+Shift+Alt+Up", "Ctrl+Alt+Up"),
        "editops_box_down": ("Ctrl+Shift+Alt+Down", "Ctrl+Alt+Down"),
        "editops_box_left": ("Ctrl+Shift+Alt+Left",),
        "editops_box_right": ("Ctrl+Shift+Alt+Right",),
        "editops_multi_add_next": ("Ctrl+D",),
        "editops_line_duplicate": ("Shift+Alt+Down",),
        "editops_bracket_jump": ("Ctrl+Shift+\\",),
    },
}
PRESET_TITLES = {"visual_studio": "Visual Studio style (default)", "vscode": "VS Code style"}


def preset_keys(preset: str, cid: str) -> tuple:
    """型 ``preset`` での ``cid`` の既定のキー。"""
    over = PRESETS[preset]
    return tuple(over[cid]) if cid in over else BY_ID[cid].keys


# --------------------------------------------------------------------------- #
# 問題(当たり・読めないキー・予約のキー)
# --------------------------------------------------------------------------- #
class Problem(NamedTuple):
    """``level``: ``error``(当てない)/ ``warning``(当てるが知らせる)/ ``info``(知っておく事)。"""
    level: str
    code: str
    command: str = ""
    key: str = ""
    other: str = ""
    other_key: str = ""
    place: str = ""
    detail: str = ""


class Entry(NamedTuple):
    """当たりの検査の 1 行: どのコマンドの、どのキーが、どの範囲で効くか。"""
    command: str
    key: str
    scope: str
    when: str | None = None
    fixed: bool = False
    title: str = ""


_OS_TAKEN = {"Alt+Tab", "Shift+Alt+Tab", "Alt+Esc", "Ctrl+Esc", "Ctrl+Alt+Del", "Ctrl+Shift+Esc"}
_WARN_EXACT = {"Alt+F4": "warn_close", "Alt+Space": "warn_window_menu", "F10": "warn_menu_key",
               "Shift+F10": "warn_menu_key", "Print": "warn_print", "Alt+Print": "warn_print",
               "Ctrl+Alt+T": "warn_terminal", "Ctrl+Space": "warn_ime", "Shift+Space": "warn_ime",
               "Ctrl+Shift+Space": "warn_ime", "Ctrl+.": "warn_ime", "Alt+`": "warn_ime", "Ctrl+Shift+F": "warn_ime"}


def reserved(key: str) -> list:
    """OS・入力方式(IME)・配列がこのキーを先に取る事の一覧 ``[(level, code)]``(1 打目で判定)。"""
    first = key.split(", ")[0]
    mods, name = _split_stroke(first)
    if "Meta" in mods or first in _OS_TAKEN:
        return [("error", "os_taken")]
    out = []
    code = _WARN_EXACT.get(first)
    if code:
        out.append(("warning", code))
    if mods[:1] == ["Ctrl"] and "Alt" in mods:
        if name in ("Left", "Right", "Up", "Down") and mods == ["Ctrl", "Alt"]:
            out.append(("warning", "warn_rotate"))
        elif re.fullmatch(r"F([1-9]|1[0-2])", name) and mods == ["Ctrl", "Alt"]:
            out.append(("warning", "warn_vt"))
        elif len(name) == 1:
            out.append(("warning", "warn_altgr"))
    return out


def _plain_problem(key: str, scope: Scope) -> str | None:
    """修飾なしのキーが、その範囲で文字の入力を奪うか。奪うなら問題の符号。"""
    for st in key.split(", "):
        mods, name = _split_stroke(st)
        if "Ctrl" in mods or "Alt" in mods or "Meta" in mods:
            continue
        printable = len(name) == 1 or name in ("Space", "Return", "Enter")
        if printable and not scope.text_free:
            return "plain_key"
        if name == "Tab" and not (scope.text_free or scope.group == "code_editor"):
            return "plain_key"
    return None


def validate_keys(cid: str, keys: Sequence) -> list:
    """キーの並び ``keys``(正規化済み)を ``cid`` に付けてよいか(当たりは見ない)。"""
    cmd = BY_ID.get(cid)
    if cmd is None:
        return [Problem("error", "unknown_command", cid)]
    if cmd.fixed:
        return [Problem("error", "fixed_command", cid)]
    out = []
    if len(keys) > MAX_KEYS_PER_COMMAND:
        out.append(Problem("error", "too_many_keys", cid, detail=str(MAX_KEYS_PER_COMMAND)))
    scope = SCOPES[cmd.scope]
    for k in keys:
        if ", " in k and not scope.chords:
            out.append(Problem("error", "chord_not_here", cid, k))
        plain = _plain_problem(k, scope)
        if plain:
            out.append(Problem("error", plain, cid, k))
        for level, code in reserved(k):
            out.append(Problem(level, code, cid, k))
    return out


def _relation(a: str, b: str) -> str | None:
    if a == b:
        return "same"
    if a.startswith(b + ", ") or b.startswith(a + ", "):
        return "prefix"
    return None


def _severity(a: Entry, b: Entry, rel: str) -> tuple | None:
    sa, sb = SCOPES[a.scope], SCOPES[b.scope]
    if sa.mech == "qt" and sb.mech == "qt":
        return ("error", "ambiguous" if rel == "same" else "prefix")
    if sa.mech == "filter" and sb.mech == "filter":
        if sa.group != sb.group:
            return None
        wa, wb = a.when or sa.when, b.when or sb.when
        if wa and wb and wa != wb:
            return ("info", "shared")
        return ("error", "same_widget" if rel == "same" else "prefix")
    if sa.mech == "text" and sb.mech == "text":
        return None
    return ("info", "shadow")


_RANK = {"filter": 2, "text": 1, "qt": 0}


def find_conflicts(entries: Iterable, only: Iterable | None = None) -> list:
    """当たり ``[Problem]``。``only`` を渡すと、そのコマンドが関わる物だけ(``command`` がそのコマンドの側)。

    組み込み(``fixed``)どうしは数えない(今あって動いている。棚卸しで実測済み)。
    """
    entries = list(entries)
    only = set(only) if only is not None else None
    by_first: dict = {}
    for e in entries:
        by_first.setdefault(e.key.split(", ")[0], []).append(e)
    out, seen = [], set()
    for group in by_first.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if (a.fixed and b.fixed) or a.command == b.command:
                    continue
                if only is not None and a.command not in only and b.command not in only:
                    continue
                rel = _relation(a.key, b.key)
                if rel is None:
                    continue
                worst = None
                for place, (_title, scopes) in PLACES.items():
                    if a.scope in scopes and b.scope in scopes:
                        sev = _severity(a, b, rel)
                        if sev and (worst is None or (sev[0] == "error" and worst[0] != "error")):
                            worst = (sev[0], sev[1], place)
                if worst is None:
                    continue
                me, other = a, b
                if (only is not None and a.command not in only) or (only is None and a.fixed):
                    me, other = b, a
                code = worst[1]
                if code == "shadow" and _RANK[SCOPES[me.scope].mech] > _RANK[SCOPES[other.scope].mech]:
                    code = "shadows"                           # こちらが先に取る側(相手が隠れる)
                sig = (worst[0], code, me.command, me.key, other.command, other.key)
                if sig not in seen:
                    seen.add(sig)
                    out.append(Problem(worst[0], code, me.command, me.key, other.command, other.key, worst[2]))
    # どこへ行っても先に取られて、決して届かないキー
    for e in entries:
        if e.fixed or (only is not None and e.command not in only) or SCOPES[e.scope].mech != "qt":
            continue
        places = [p for p, (_t, scopes) in PLACES.items() if e.scope in scopes]
        blockers = []
        for p in places:
            scopes = PLACES[p][1]
            hit = [o for o in by_first.get(e.key.split(", ")[0], ()) if o.command != e.command and o.key == e.key
                   and o.scope in scopes and SCOPES[o.scope].mech != "qt" and not (o.when or SCOPES[o.scope].when)]
            if not hit:
                break
            blockers.append(hit[0])
        else:
            if blockers:
                out.append(Problem("error", "unreachable", e.command, e.key, blockers[0].command, blockers[0].key,
                                   places[0]))
    return out


# --------------------------------------------------------------------------- #
# 利用者のキーの表
# --------------------------------------------------------------------------- #
class Keymap:
    """型 + 利用者の上書き。上書きは型と違う物だけを持つ(``()`` = キーを外した)。"""

    def __init__(self, preset: str = DEFAULT_PRESET, overrides: dict | None = None):
        if preset not in PRESETS:
            raise ValueError("知らない型: %r" % (preset,))
        self.preset = preset
        self._over: dict = {}
        for cid, keys in (overrides or {}).items():
            self._set(cid, parse_keys(keys))

    def copy(self) -> "Keymap":
        k = Keymap(self.preset)
        k._over = dict(self._over)
        return k

    def __eq__(self, other) -> bool:
        return isinstance(other, Keymap) and other.preset == self.preset and other._over == self._over

    def __repr__(self) -> str:
        return "Keymap(%r, %r)" % (self.preset, self._over)

    def _set(self, cid: str, keys: tuple) -> None:
        if cid not in BY_ID or BY_ID[cid].fixed:
            raise ValueError("変えられないコマンド: %r" % (cid,))
        if keys == preset_keys(self.preset, cid):
            self._over.pop(cid, None)
        else:
            self._over[cid] = keys

    def keys(self, cid: str) -> tuple:
        """``cid`` の今のキー。"""
        if cid in self._over:
            return self._over[cid]
        return preset_keys(self.preset, cid)

    def preset_keys(self, cid: str) -> tuple:
        return preset_keys(self.preset, cid)

    def is_changed(self, cid: str) -> bool:
        """型から変えたか。"""
        return cid in self._over

    def overrides(self) -> dict:
        return dict(self._over)

    def entries(self, extra: Iterable = ()) -> list:
        """当たりの検査に渡す全部の行(組み込みと ``extra`` を含む)。"""
        out = []
        for c in COMMANDS:
            for k in self.keys(c.id):
                out.append(Entry(c.id, k, c.scope, c.when, c.fixed, c.title))
        out.extend(extra)
        return out

    def problems(self, extra: Iterable = ()) -> list:
        """表全体の問題(上書きのキーの検査 + 当たり)。"""
        out = []
        for cid, keys in self._over.items():
            out.extend(validate_keys(cid, keys))
        for c in COMMANDS:
            if not c.fixed:
                for k in self.keys(c.id):
                    out.extend(Problem(lv, code, c.id, k) for lv, code in reserved(k) if lv == "error")
        return out + find_conflicts(self.entries(extra))

    def check(self, cid: str, keys, extra: Iterable = ()) -> list:
        """``cid`` を ``keys`` にしたら何が起きるか(まだ当てない)。"""
        try:
            keys = parse_keys(keys)
        except KeyParseError as exc:
            return [Problem("error", exc.code, cid, exc.key)]
        out = validate_keys(cid, keys)
        if any(p.code in ("unknown_command", "fixed_command") for p in out):
            return out
        trial = self.copy()
        trial._set(cid, keys)
        return out + find_conflicts(trial.entries(extra), only={cid})

    def assign(self, cid: str, keys, extra: Iterable = ()) -> list:
        """``cid`` のキーを ``keys`` にする。error が 1 つでもあれば当てずに問題を返す(相手は勝手に外さない)。"""
        probs = self.check(cid, keys, extra)
        if not any(p.level == "error" for p in probs):
            self._set(cid, parse_keys(keys))
        return probs

    def reset(self, cid: str) -> bool:
        """``cid`` を型の既定に戻す。戻したら True。"""
        return self._over.pop(cid, None) is not None

    def reset_all(self) -> int:
        """全部を型の既定に戻す。戻した数。"""
        n = len(self._over)
        self._over = {}
        return n

    def switch_preset(self, name: str, extra: Iterable = ()) -> list:
        """型を変える(上書きは残す)。新しい型と当たる上書きは捨て、捨てた ``[(cid, keys)]`` を返す。"""
        if name not in PRESETS:
            raise ValueError("知らない型: %r" % (name,))
        trial = Keymap(name)
        for cid, keys in self._over.items():
            trial._set(cid, keys)
        dropped = []
        while True:
            errs = [p for p in find_conflicts(trial.entries(extra)) if p.level == "error"]
            victim = next((c for p in errs for c in (p.command, p.other) if c in trial._over), None)
            if victim is None:
                break
            dropped.append((victim, trial._over.pop(victim)))
        self.preset, self._over = trial.preset, trial._over
        return dropped

    def to_data(self) -> dict:
        return {"format": FORMAT, "version": VERSION, "preset": self.preset,
                "bindings": {cid: list(keys) for cid, keys in sorted(self._over.items())}}

    def to_json(self) -> str:
        """書き出し・設定の形(鍵の順は固定)。"""
        return json.dumps(self.to_data(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


_TOP_KEYS = {"format", "version", "preset", "bindings"}


def _read(data, strict: bool, extra: Iterable = ()) -> tuple:
    """読み込みの共通部。``strict`` なら問題が 1 つでもあれば ``(None, problems)``。"""
    probs = []
    if not isinstance(data, dict):
        return None, [Problem("error", "bad_type", detail="(top)")]
    if data.get("format") != FORMAT:
        return None, [Problem("error", "bad_format", detail=str(data.get("format"))[:60])]
    if data.get("version") != VERSION or isinstance(data.get("version"), bool):
        return None, [Problem("error", "bad_version", detail=str(data.get("version"))[:20])]
    unknown = sorted(set(data) - _TOP_KEYS)
    if unknown:
        probs.append(Problem("error", "bad_type", detail=", ".join(str(u)[:40] for u in unknown[:5])))
    preset = data.get("preset", DEFAULT_PRESET)
    if not (isinstance(preset, str) and preset in PRESETS):    # list / dict は ``in`` で TypeError になる
        probs.append(Problem("error", "unknown_preset", detail=str(preset)[:40]))
        preset = DEFAULT_PRESET
    km = Keymap(preset)
    binds = data.get("bindings", {})
    if not isinstance(binds, dict):
        probs.append(Problem("error", "bad_type", detail="bindings"))
        binds = {}
    if len(binds) > len(COMMANDS):
        return None, [Problem("error", "too_big", detail="%d bindings" % len(binds))]
    for cid in sorted(binds, key=str):
        val = binds[cid]
        if not isinstance(cid, str) or cid not in BY_ID:
            probs.append(Problem("error", "unknown_command", str(cid)[:60]))
            continue
        if BY_ID[cid].fixed:
            probs.append(Problem("error", "fixed_command", cid))
            continue
        if not isinstance(val, list) or not all(isinstance(v, str) for v in val):
            probs.append(Problem("error", "bad_type", cid, detail="bindings.%s" % cid))
            continue
        try:
            keys = parse_keys(val)
        except KeyParseError as exc:
            probs.append(Problem("error", exc.code, cid, exc.key[:40]))
            continue
        bad = validate_keys(cid, keys)
        probs.extend(p for p in bad if p.level != "info")
        if any(p.level == "error" for p in bad):
            continue
        km._set(cid, keys)
    # 当たり: 寛容に読む時は、当たった上書きを捨てる。厳しく読む時は全部を断る
    while True:
        errs = [p for p in find_conflicts(km.entries(extra)) if p.level == "error"]
        if not errs:
            break
        victim = next((c for p in errs for c in (p.command, p.other) if c in km._over), None)
        if victim is None:
            break
        for p in errs:                                         # 捨てる理由は必ず残す(相手を届かなくする側も)
            if victim in (p.command, p.other):
                q = _as_seen_from(p, victim)
                if q not in probs:
                    probs.append(q)
        del km._over[victim]
    if strict and any(p.level == "error" for p in probs):
        return None, probs
    return km, probs


def _as_seen_from(p: Problem, cid: str) -> Problem:
    """当たり ``p`` を ``cid`` の側から書き直す(``command`` = ``cid``)。届かなくなる相手は ``blocks``。"""
    if p.command == cid:
        return p
    code = {"unreachable": "blocks", "shadow": "shadows", "shadows": "shadow"}.get(p.code, p.code)
    return Problem(p.level, code, cid, p.other_key, p.command, p.key, p.place, p.detail)


def dropped_commands(probs: Iterable) -> list:
    """読み込みの問題のうち、捨てた上書きのコマンド(登録簿に無い ID も含む)。起動の知らせで数える物。"""
    return sorted({p.command for p in probs if p.level == "error" and p.command})


class _JsonRefused(ValueError):
    """読む前・読む時に断った JSON。``code`` は ``bad_json`` / ``bad_type``。"""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _depth(text: str) -> int:
    """JSON の文字列の入れ子の深さ(文字列の中の括弧は数えない)。"""
    depth = top = 0
    in_str = esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
            if depth > top:
                top = depth
                if top > MAX_DEPTH:
                    return top
        elif ch in "]}":
            depth -= 1
    return top


def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise _JsonRefused("bad_type", "duplicate: %s" % str(k)[:40])
        out[k] = v
    return out


def _loads(text: str):
    """JSON を読む。深すぎる入れ子・重なった鍵は ``_JsonRefused``(再帰の上限や後勝ちに頼らない)。"""
    if _depth(text) > MAX_DEPTH:
        raise _JsonRefused("bad_json", "nested more than %d levels" % MAX_DEPTH)
    try:
        return json.loads(text, object_pairs_hook=_no_duplicates)
    except RecursionError as exc:                              # pragma: no cover -- 上の深さの検査が先に断る
        raise _JsonRefused("bad_json", "nested too deeply") from exc


def from_settings_text(text, extra: Iterable = ()) -> tuple:
    """設定に覚えた文字列 → ``(Keymap, problems)``。壊れていても必ず Keymap を返し、例外を出さない(壊れた分は捨てる)。

    新しい版(``version`` が ``VERSION`` より大きい)の設定は読まずに既定を返す(``settings_newer``。元の値は残す)。
    """
    if text is None or text == "":
        return Keymap(), []
    if not isinstance(text, str):
        return Keymap(), [Problem("warning", "settings_broken", detail=type(text).__name__)]
    try:
        data = _loads(text)
    except _JsonRefused as exc:
        return Keymap(), [Problem("warning", "settings_broken", detail=exc.detail)]
    except ValueError as exc:
        return Keymap(), [Problem("warning", "settings_broken", detail="JSON: %s" % str(exc)[:80])]
    if isinstance(data, dict) and data.get("format") == FORMAT:
        ver = data.get("version")
        if isinstance(ver, int) and not isinstance(ver, bool) and ver > VERSION:
            return Keymap(), [Problem("warning", "settings_newer", detail=str(ver))]
    try:
        km, probs = _read(data, strict=False, extra=extra)
    except Exception as exc:                                   # noqa: BLE001 -- 何が来ても起動は止めない
        return Keymap(), [Problem("warning", "settings_broken", detail=type(exc).__name__)]
    if km is None:
        return Keymap(), [Problem("warning", "settings_broken", detail=probs[0].code if probs else "?")] + probs
    return km, probs


def import_text(data, extra: Iterable = ()) -> tuple:
    """書き出した JSON(文字列かバイト列)→ ``(Keymap, warnings)``。駄目なら ``(None, problems)``(何も当てない)。"""
    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    if len(raw) > MAX_IMPORT_BYTES:
        return None, [Problem("error", "too_big", detail="%d bytes" % len(raw))]
    try:
        obj = _loads(raw.decode("utf-8"))
    except _JsonRefused as exc:
        return None, [Problem("error", exc.code, detail=exc.detail)]
    except (UnicodeDecodeError, ValueError) as exc:
        return None, [Problem("error", "bad_json", detail=str(exc)[:80])]
    try:
        return _read(obj, strict=True, extra=extra)
    except Exception as exc:                                   # noqa: BLE001 -- 読み込みは知らせて断る(落ちない)
        return None, [Problem("error", "bad_type", detail=type(exc).__name__)]


# --------------------------------------------------------------------------- #
# 文の中のキーを今のキーへ(メニュー・ツールチップの文がキーを書いている所)
# --------------------------------------------------------------------------- #
_SEP = re.compile(r"\s*(?:/|,|、|;)\s*|\s+(?:or|oder|ou|または|或|或者|또는)\s+")


def retarget_text(text: str, pairs: Iterable, lang: str = "en") -> str:
    """``text`` の中の古いキーを今のキーへ書き換える。``pairs`` は ``(古いキーの並び, 新しいキーの並び)``。

    同じコマンドのキーが区切り(`` / `` ``, `` ``or`` …)で並んでいる所は 1 まとまりとして置き換える。
    新しいキーが無ければ、括弧ごと消す(括弧の中でなければ ``—``)。全部の組を一度に当てる(入れ替えても壊れない)。
    """
    if not text:
        return text
    runs = []
    for old, new in pairs:
        old, new = tuple(old), tuple(new)
        if old == new or not old:
            continue
        hits = []
        for k in old:
            for sp in _spellings(k):
                for m in re.finditer(r"(?<![A-Za-z0-9+])" + re.escape(sp) + r"(?![A-Za-z0-9])", text):
                    hits.append((m.start(), m.end()))
        merged: list = []                                      # [始め, 終わり, 区切り]
        for s, e in sorted(set(hits)):
            if merged and s < merged[-1][1]:
                merged[-1][1] = max(e, merged[-1][1])
            elif merged and _SEP.fullmatch(text[merged[-1][1]:s]):
                if merged[-1][2] is None:
                    merged[-1][2] = text[merged[-1][1]:s]
                merged[-1][1] = e
            else:
                merged.append([s, e, None])
        for s, e, sep in merged:
            runs.append((s, e, sep or " / ", new))
    if not runs:
        return text
    runs.sort()
    out, pos = [], 0
    for s, e, sep, new in runs:
        if s < pos:
            continue
        if new:
            out.append(text[pos:s])
            out.append(sep.join(display_key(k, lang) for k in new))
        elif s > 0 and text[s - 1] == "(" and text[e:e + 1] == ")":
            cut = s - 1
            while cut > pos and text[cut - 1] == " ":
                cut -= 1
            out.append(text[pos:cut])
            e += 1
        else:
            out.append(text[pos:s])
            out.append("—")
        pos = e
    out.append(text[pos:])
    return "".join(out)


def text_pairs(keymap: Keymap, cid: str) -> list:
    """コマンド ``cid`` の表示の文に当てる ``(既定のキー, 今のキー)`` の組(自分の分と ``mentions`` の分)。"""
    c = BY_ID[cid]
    return [(BY_ID[x].keys, keymap.keys(x)) for x in (cid,) + tuple(c.mentions) if x in BY_ID]


# --------------------------------------------------------------------------- #
# 一覧(F1 の表・設定の窓・文書)
# --------------------------------------------------------------------------- #
_SCOPE_ORDER = list(SCOPES)


def shortcut_rows(keymap: Keymap, tr: Callable = (lambda s: s), extra: Iterable = (),
                  include_unbound: bool = False) -> list:
    """``[(cid, 表示名, キーの文, 範囲の名前, 変えたか, 組み込みか)]``。範囲の順 → 表示名の順。"""
    rows = []
    for c in COMMANDS:
        keys = keymap.keys(c.id)
        if not keys and not include_unbound:
            continue
        rows.append((c.id, tr(c.title), " / ".join(keys), tr(SCOPES[c.scope].title), keymap.is_changed(c.id),
                     c.fixed))
    for e in extra:
        rows.append((e.command, tr(e.title) if e.title else e.command, e.key, tr(SCOPES[e.scope].title), False, True))
    order = {s: i for i, s in enumerate(_SCOPE_ORDER)}
    scope_of = {c.id: c.scope for c in COMMANDS}
    scope_of.update({e.command: e.scope for e in extra})
    rows.sort(key=lambda r: (order.get(scope_of.get(r[0], ""), 99), r[5], r[1].lower()))
    return rows


def search(rows: Sequence, query: str) -> list:
    """``shortcut_rows`` の行を語で絞る。語がキーとして読めれば、そのキーを持つ行も当たる(``ctrl+d``)。"""
    q = (query or "").strip()
    if not q:
        return list(rows)
    try:
        as_key = normalize_sequence(q) if "+" in q or _FKEY.match(q) or q.lower() in _NAMED else None
    except KeyParseError:
        as_key = None
    low = q.lower()
    out = []
    for r in rows:
        keys = [k.strip() for k in r[2].split(" / ") if k.strip()]
        if as_key is not None:                                 # キーとして読めた: そのキー(で始まる和音)を持つ行だけ
            if any(k == as_key or k.startswith(as_key + ", ") for k in keys):
                out.append(r)
            continue
        hay = " ".join((r[0], r[1], r[2], r[3], BY_ID[r[0]].title if r[0] in BY_ID else "")).lower()
        if all(w in hay for w in low.split()):
            out.append(r)
    return out


# --------------------------------------------------------------------------- #
# 画面の文と対訳
# --------------------------------------------------------------------------- #
ACT_SETTINGS = "Customize keyboard shortcuts…"
DLG_TITLE = "Customize keyboard shortcuts"
LBL_PRESET = "Preset"
PH_SEARCH = "Search by command, key or place (for example: duplicate, ctrl+d)"
COL_COMMAND = "Command"
COL_KEY = "Key"
COL_WHERE = "Where"
COL_CHANGED = "Changed"
LBL_CURRENT = "Current keys: %s"
LBL_NONE = "(none)"
LBL_RECORD = "New key"
PH_RECORD = "Click here, then press the keys"
HINT_CHORD = "A second key right after the first makes a two-stroke key. Clear starts over."
HINT_NO_CHORD = "One key at a time here (no two-stroke keys in editors)."
BTN_CLEAR = "Clear"
BTN_ASSIGN = "Assign"
BTN_ADD = "Add as another key"
BTN_REMOVE = "Remove keys"
BTN_RESET = "Reset to preset"
BTN_RESET_ALL = "Reset all…"
BTN_IMPORT = "Import…"
BTN_EXPORT = "Export…"
BTN_CLOSE = "Close"
MSG_FIXED = "Built in: cannot be changed here"
MSG_NO_CONFLICT = "No conflicts"
MSG_CHANGED = "Changed from the preset"
MSG_PICK = "Pick a command in the table"
TTL_RESET_ALL = "Reset all shortcuts"
ASK_RESET_ALL = "Reset all %d changed shortcuts to the preset? This cannot be undone."
TTL_PRESET = "Switch preset"
ASK_PRESET = "Switch to %s? Your own changes are kept."
ASK_PRESET_DROP = "%d of your changes conflict with this preset and will be dropped:"
MSG_IMPORTED = "Imported %d changed shortcuts"
MSG_IMPORT_FAILED = "The file was not imported (nothing was changed):"
MSG_EXPORTED = "Saved %d changed shortcuts to %s"
MSG_LOAD_PROBLEM = "Keyboard shortcuts: %d saved changes could not be used (Tools > Customize keyboard shortcuts)"
MSG_LOAD_PART = "Keyboard shortcuts: part of the saved settings could not be used (Tools > Customize keyboard shortcuts)"
MSG_LOAD_BROKEN = ("Keyboard shortcuts: the saved settings could not be read, so the preset is used "
                   "(Tools > Customize keyboard shortcuts)")
MSG_LOAD_NEWER = "Keyboard shortcuts: the saved settings are from a newer Studio; they are kept as they are and not used"
MSG_LOAD_HEADER = "Not used when Studio started:"
FILE_FILTER = "Fullseye Studio keys (*.json)"
#: 登録簿に無い組み込みの相手(当たりの文と一覧): メニューバーのニーモニック / テキスト欄の標準のキー。
MSG_MENU_BAR = "Menu bar: %s"
MSG_TEXT_KEY = "Text fields: %s"

MESSAGES = {
    "ambiguous": "%(key)s is also used by %(other)s: in %(place)s neither would work",
    "prefix": "%(key)s and %(other_key)s (%(other)s) begin with the same key: in %(place)s one could never be pressed",
    "same_widget": "%(key)s is also taken by %(other)s in the same editor",
    "unreachable": "%(key)s would never reach this command: %(other)s takes it first",
    "blocks": "%(key)s would take the key from %(other)s everywhere it works",
    "shadow": "In %(place)s, %(other)s takes %(key)s first",
    "shadows": "In %(place)s, this command takes %(key)s before %(other)s",
    "shared": "%(key)s is shared with %(other)s; each takes it only in its own situation",
    "chord_not_here": "%(key)s: two-stroke keys work only in window-wide places, not in editors",
    "too_many_strokes": "%(key)s: at most two strokes",
    "bad_key": "Cannot read the key %(key)s",
    "plain_key": "%(key)s without Ctrl or Alt would take typing here",
    "too_many_keys": "At most %(detail)s keys per command",
    "os_taken": "%(key)s is taken by the operating system",
    "warn_close": "%(key)s closes the window on Windows",
    "warn_window_menu": "%(key)s opens the window menu on Windows",
    "warn_menu_key": "%(key)s may move the focus to the menu bar",
    "warn_print": "%(key)s takes a screenshot on many systems",
    "warn_altgr": "On keyboards with AltGr (German, French, Polish …) %(key)s types a character",
    "warn_rotate": "Some graphics drivers rotate the screen with %(key)s; Linux desktops switch workspaces",
    "warn_vt": "On Linux %(key)s switches to a text console",
    "warn_terminal": "On many Linux desktops %(key)s opens a terminal",
    "warn_ime": "%(key)s is used by input methods (IME) to switch modes",
    "unknown_command": "Unknown command: %(command)s",
    "fixed_command": "%(command)s is built in and cannot be changed",
    "unknown_preset": "Unknown preset: %(detail)s",
    "bad_json": "Not a JSON file (%(detail)s)",
    "bad_format": "Not a Fullseye Studio key file (%(detail)s)",
    "bad_version": "Unsupported version: %(detail)s",
    "bad_type": "Wrong type or unknown field: %(detail)s",
    "too_big": "The file is too big (%(detail)s)",
    "settings_broken": "The saved shortcuts could not be read; the preset is used (%(detail)s)",
    "settings_newer": "The saved shortcuts are from a newer version (%(detail)s); they were kept and not used",
}


#: 書字方向を変える文字(表示の前に \uXXXX にする)。
_BIDI = set("\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


def _safe(text, limit: int = 40) -> str:
    """外から来た文字(ファイルの ID・キー・detail)を 1 行の安全な文にする。制御文字・書字方向の文字・行の区切りは
    ``\\uXXXX`` に置き換え、``limit`` 字で切る(偽の行や逆向きの文を作らせない)。"""
    out = []
    for ch in "" if text is None else str(text):
        if ch in _BIDI or unicodedata.category(ch) in ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"):
            out.append("\\u%04x" % ord(ch) if ord(ch) <= 0xFFFF else "\\U%08x" % ord(ch))
        else:
            out.append(ch)
    s = "".join(out)
    return s if len(s) <= limit else s[:limit - 1] + "…"


def describe_problem(p: Problem, tr: Callable = (lambda s: s), titles: dict | None = None) -> str:
    """問題 1 つを今の言語の 1 行にする(相手の名前と範囲を書く)。``titles`` は登録簿に無い相手
    (メニューバーのニーモニック・テキスト欄の標準のキー)の名前。"""
    def title(cid):
        c = BY_ID.get(cid)
        if c is None:
            got = (titles or {}).get(cid)
            return got if got is not None else _safe(cid)
        return "%s (%s)" % (tr(c.title), tr(SCOPES[c.scope].title))
    args = {"key": _safe(p.key), "other_key": _safe(p.other_key),
            "command": tr(BY_ID[p.command].title) if p.command in BY_ID else _safe(p.command),
            "other": title(p.other) if p.other else "", "detail": _safe(p.detail, 80),
            "place": tr(PLACES[p.place][0]) if p.place in PLACES else _safe(p.place)}
    tmpl = tr(MESSAGES.get(p.code, p.code))
    try:
        return tmpl % args
    except (KeyError, ValueError, TypeError):
        return MESSAGES.get(p.code, p.code) % args


def ui_strings() -> tuple:
    """この部品の対訳の表が持つ英語の文の全部(表はこれと 1 対 1)。"""
    fixed = [ACT_SETTINGS, DLG_TITLE, LBL_PRESET, PH_SEARCH, COL_COMMAND, COL_KEY, COL_WHERE, COL_CHANGED,
             LBL_CURRENT, LBL_NONE, LBL_RECORD, PH_RECORD, HINT_CHORD, HINT_NO_CHORD, BTN_CLEAR, BTN_ASSIGN, BTN_ADD,
             BTN_REMOVE, BTN_RESET, BTN_RESET_ALL, BTN_IMPORT, BTN_EXPORT, BTN_CLOSE, MSG_FIXED, MSG_NO_CONFLICT,
             MSG_CHANGED, MSG_PICK, TTL_RESET_ALL, ASK_RESET_ALL, TTL_PRESET, ASK_PRESET, ASK_PRESET_DROP,
             MSG_IMPORTED, MSG_IMPORT_FAILED, MSG_EXPORTED, MSG_LOAD_PROBLEM, FILE_FILTER, MSG_MENU_BAR, MSG_TEXT_KEY,
             MSG_LOAD_PART, MSG_LOAD_BROKEN, MSG_LOAD_NEWER, MSG_LOAD_HEADER]
    fixed += list(PRESET_TITLES.values()) + [s.title for s in SCOPES.values()] + [t for t, _s in PLACES.values()]
    fixed += list(MESSAGES.values()) + [c.title for c in COMMANDS if c.own_title]
    seen, out = set(), []
    for s in fixed:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return tuple(out)


LANGS = ("en", "ja", "zh", "tw", "ko", "de")
_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_assets", "studio_keymap_i18n.json")
_CACHE: dict = {}


def load_table(path: str | None = None) -> dict:
    """対訳の表 ``{英語: {言語: 訳}}``。読めない・壊れていれば ``ValueError``(黙って空にしない)。"""
    path = path or _TABLE_PATH
    if path in _CACHE:
        return _CACHE[path]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError("対訳の表を読めません: %s (%s)" % (os.path.basename(path), exc)) from exc
    strings = data.get("strings") if isinstance(data, dict) else None
    if not isinstance(strings, dict):
        raise ValueError("対訳の表に 'strings' がありません: %s" % os.path.basename(path))
    _CACHE[path] = strings
    return strings


def make_tr(lang="en", first: Callable | None = None, table: dict | None = None) -> Callable:
    """``tr`` を作る。``lang`` は言語の符号か、呼ぶたびに今の言語を返す関数。

    引く順: ``first``(Studio の ``tr``)→ 矩形選択の部品の表 → この部品の表。どれにも無ければ英語のまま。
    """
    if not callable(lang) and lang not in LANGS and lang != "hi":
        raise ValueError("言語は %s のどれか(来たのは %r)" % (" / ".join(LANGS), lang))
    editops_tr = _eo.make_tr(lang if callable(lang) else (lambda: lang))

    def tr(text: str) -> str:
        if not text:
            return text
        if first is not None:
            got = first(text)
            if got != text:
                return got
        code = lang() if callable(lang) else lang
        if code == "en" or code not in LANGS:
            return text
        got = editops_tr(text)
        if got != text:
            return got
        tab = load_table() if table is None else table
        return tab.get(text, {}).get(code, text)

    return tr


def missing(table: dict | None = None) -> list:
    """``[(英語, 足りない言語)]``。この部品の文の全部が 5 言語そろっていれば空。"""
    tab = load_table() if table is None else table
    out = []
    for key in ui_strings():
        row = tab.get(key)
        for lang in LANGS[1:]:
            if not isinstance(row, dict) or not str(row.get(lang, "")).strip():
                out.append((key, lang))
    return out
