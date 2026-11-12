# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_program_i18n — 実行系と検査(``studio_program``)が作る英語の文を、UI の言語へ直す(Qt なし)。

``studio_program`` の文(``ProgramResult.errors`` / ``notes``、``check_program`` の ``Problem.message`` / ``hint``、
``advise_program`` の助言)は**英語が正**で、値を埋めた後の文字列として返る(API の利用者・試験・ログはそのまま
英語を読む)。画面に出す所(``studio_pymode``)だけがここを通す:

    localize("line 3: stopped on request", tr)   ->  "3 行目: 要求により停止しました"

やり方: :data:`TEMPLATES` に ``studio_program`` の書式文字列(``%s`` / ``%d`` …を含む英語)を並べ、文をその
型に当てはめて値を取り出し、``tr(型)`` の訳に同じ順で埋め直す。訳は ``studio_assets/studio_pyedit_i18n.json``
(ja・zh・tw・ko・de)。表に無い言語(hi など)・型に当たらない文(Python 自身の例外の文など)は**英語のまま**
返す(壊れた訳より原文)。

決まり:

* 型は ``studio_program.py`` の書式文字列と**同じ文字列**(試験が源のファイルを読んで、型がそこに在ること・
  検査の文が全部型に当たることを数える。源の文を変えたら試験が落ちる)。
* 訳は値の**順番を変えない**(``%s`` の並びが英語と同じ)。
* ``line N`` の言い方は 1 つの型(``"line %d"``)で、:func:`line_number_of` は全言語の言い方から行番号を読む
  (出力の欄の行を押してその行へ飛ぶ道が、言語を変えても切れない)。
"""
from __future__ import annotations

import re
from typing import Callable

#: 行の言い方(``line 3``)。訳の鍵でもある。
LINE_LABEL = "line %d"

#: 行番号を前に付けた文の本体の型(``"line %d: " + 本体`` の形で出る物)。
LINE_BODY_TEMPLATES = (
    "stopped on request",
    "stopped: time limit %.3g s exceeded",
    "the program called exit(%r)",
    "a Python program needs an input image",
    "cannot compile: %s",
    "breakpoint condition %r could not be evaluated (%s: %s) — stopped there",
    "HDevelop-style %s and line %d: Python-style %s are mixed — one program uses one syntax "
    "(put '# python' or '# hdevelop' on line 1)",
)

#: 文全体の型(実行の結果の errors / notes、選んだ行の実行)。
RUN_TEMPLATES = (
    "not run: this Python program came from a file, project or automation and will execute on this PC — "
    "confirm it first (digest %s)",
    "could not stop the program after %s within %.1f s — it is inside a long call (C code, time.sleep, a big "
    "numpy operation) or keeps catching the stop; it goes on running in the background and its results are ignored",
    "abandoned run: see studio_program.abandoned_runs()",
    "restored after the run: %s",
    "Release does not stop at breakpoints (lines %s) — switch to Debug to use them",
    "Release cannot step line by line — switch to Debug",
    "the error is in %s line %d (called from line %d)",
    "%s — install it into Studio's Python: \"%s\" -m pip install %s",
    "stopped: time limit",
    "stopped: on request",
    "stopped",
    "could not stop the selected lines within %.1f s — they go on running in the background and their results "
    "are ignored",
    "no namespace: run the program first (keep_namespace=True)",
    "not run: untrusted input",
)

#: 値として埋まる短い句(「止められなかった」の理由)。
ARG_TEMPLATES = (
    "time limit %.3g s",
    "a stop request",
)

#: 検査(check_program)の文と直し方。
CHECK_TEMPLATES = (
    "Syntax error: %s",
    "Cannot read the program: %s",
    "'%s' is not defined",
    "'%s' is not defined — did you mean '%s'?",
    "Assign it before this line, or check the spelling",
    "Replace with '%s'",
    "Tabs and spaces are mixed in the indentation",
    "Indent with 4 spaces only",
    "Indentation is off: %s",
    "Lines in the same block start at the same column; the line after a ':' is indented by 4 spaces",
    "'%s' is written '%s' in Python",
    "Replace '%s' with '%s'",
    "'%s' opened on line %d is never closed",
    "Add the matching '%s'",
    "Python marks blocks with ':' and indentation, not '{' '}'",
    "End the line with ':' and indent the block by 4 spaces",
    "This closing bracket has no opening one: %s",
    "Remove it or add the opening bracket",
    "This string is never closed",
    "Add the closing quote on the same line",
    "A ',' seems to be missing between items",
    "Separate the items with ','",
    "'=' assigns; to compare use '=='",
    "Write 'if x == 1:'",
    "A ':' is missing at the end of this line",
    "Add ':' after the condition",
    "This line is written in the pipeline syntax, but the program is Python",
    "Use 'Convert to Python' (or write it as Python: img = gaussian(img, 0.4))",
    "A ';' at the end of a line is not needed",
    "Remove it",
    "Full-width character '%s' (U+%04X) — Python needs the ASCII '%s'",
    "Switch the input method to half-width, or apply the fix",
    "There is no op named '%s'",
    "There is no op named '%s' — did you mean '%s'?",
    "Check the Operators list",
    "%s takes at most 2 knobs (a, b) after its input(s), got %d",
    "Remove the extra numbers",
    "%s takes %d inputs, e.g. %s(x, y)",
    "Pass the inputs before the knobs",
    "%s takes %d input(s) and at most 2 knobs, got %d arguments",
    "Remove the extra arguments",
    "%s has no keyword '%s' (only a= and b=)",
    "Use a= or b=",
    "knob outside 0..1, will run with the nearest limit: %s %s=%.6g → %.6g",
    "Knobs a and b are 0..1 (the op maps them to its range)",
    "The result of %s is thrown away",
    "Assign it: n = %s(...)",
    "The result of %s is not assigned (only the current flow and the display change)",
    "Assign it: x = %s(...)",
    "'%s' is only assigned on one side of an earlier 'if'",
    "Assign it before the 'if', or in both branches",
    "Imported but never used: %s",
    "Remove the import",
    "Assigned but never used (inside a function): %s",
    "Remove it, or use it",
    "Defined again before the first one was used: %s",
    "Rename one of them",
    "A loop variable hides an import: %s",
    "Rename the loop variable",
)

#: 助言(advise_program)。
ADVICE_TEMPLATES = (
    "the result of %s (%s) is never read — the measurement can be removed",
    "%s is called with the same arguments on every pass of the loop at line %d — compute it once before the "
    "loop (the memo already avoids recomputing it)",
    "same %s call as line %d — reuse that result",
    "%s takes %s but %s is %s — convert first",
    "%s in the same process as Studio's PySide6 can crash — use PySide6 (the APIs are nearly the same)",
)

#: 訳の表に在るべき全部の型(試験が数える)。
TEMPLATES = ((LINE_LABEL,) + LINE_BODY_TEMPLATES + RUN_TEMPLATES + ARG_TEMPLATES + CHECK_TEMPLATES
             + ADVICE_TEMPLATES)

_PLACEHOLDER = re.compile(r"%(?:0\d+X|\.\d+[gf]|[sdr])")
_LINE_PREFIX = re.compile(r"line (\d+): (.*)\Z", re.S)


def placeholders(template: str) -> list:
    """型の中の値の入れ場所(``%s`` / ``%d`` / ``%r`` / ``%.3g`` / ``%04X`` …)を出る順に。"""
    return _PLACEHOLDER.findall(template)


def _group_for(ph: str) -> str:
    if ph == "%d":
        return r"(-?\d+)"
    if ph.endswith("X"):
        return r"([0-9A-Fa-f]+)"
    if ph.endswith(("g", "f")):
        return r"([-+0-9.eEinfa]+)"
    return r"(.*?)"


def _compile(template: str):
    parts, pos = [], 0
    for m in _PLACEHOLDER.finditer(template):
        parts.append(re.escape(template[pos:m.start()]))
        parts.append(_group_for(m.group(0)))
        pos = m.end()
    parts.append(re.escape(template[pos:]))
    return re.compile("".join(parts) + r"\Z", re.S)


def _literal_len(template: str) -> int:
    return len(_PLACEHOLDER.sub("", template))


def _ordered(templates) -> list:
    """固定の文字が多い型を先に(``'%s' is not defined — did you mean '%s'?`` が ``'%s' is not defined`` より先)。"""
    uniq = list(dict.fromkeys(templates))
    return [(t, _compile(t)) for t in sorted(uniq, key=_literal_len, reverse=True)]


_BODY = _ordered(LINE_BODY_TEMPLATES + RUN_TEMPLATES + CHECK_TEMPLATES + ADVICE_TEMPLATES)
_ARGS = _ordered(ARG_TEMPLATES)


def _fill(translated: str, groups) -> str | None:
    """訳した型に、取り出した値を出る順に埋める。入れ場所の数が合わなければ None(原文を返させる)。"""
    if len(placeholders(translated)) != len(groups):
        return None
    it = iter(groups)
    return _PLACEHOLDER.sub(lambda _m: next(it), translated)


def _match(text: str, table, tr: Callable, nested: bool) -> str | None:
    for template, rx in table:
        m = rx.match(text)
        if m is None:
            continue
        translated = tr(template)
        if translated == template:
            return None                              # 未訳の言語: 原文のまま
        groups = [(_match(g, _ARGS, tr, False) or g) if nested else g for g in m.groups()]
        return _fill(translated, groups)
    return None


def line_label(line: int, tr: Callable) -> str:
    """``line 3`` を今の言語で(``3 行目`` / ``第 3 行`` / ``Zeile 3`` …)。"""
    t = tr(LINE_LABEL)
    return (t if placeholders(t) == ["%d"] else LINE_LABEL) % int(line)


def localize(text: str, tr: Callable) -> str:
    """``studio_program`` の英語の文 *text* を ``tr`` の言語へ。型に当たらなければそのまま返す。

    ``line N: …`` の形は、行の言い方と本体を別々に直す(本体が Python の例外の文なら、行の言い方だけが変わる)。"""
    if not text or not isinstance(text, str):
        return text
    m = _LINE_PREFIX.match(text)
    if m is not None:
        body = m.group(2)
        return "%s: %s" % (line_label(int(m.group(1)), tr), _match(body, _BODY, tr, True) or body)
    return _match(text, _BODY, tr, True) or text


_LINE_PATTERNS: list | None = None


def _line_patterns() -> list:
    """全言語の「行 N」の言い方を読む正規表現(英語 + 訳の表の ``"line %d"`` の行)。"""
    global _LINE_PATTERNS
    if _LINE_PATTERNS is None:
        forms = [LINE_LABEL]
        try:
            import studio_pyedit_i18n as pi
            forms += [v for v in pi.load_table().get(LINE_LABEL, {}).values() if isinstance(v, str)]
        except Exception:                            # noqa: BLE001 -- 表が読めなくても英語の形は読める
            pass
        pats = []
        for f in dict.fromkeys(forms):
            if f.count("%d") != 1:
                continue
            a, b = f.split("%d")
            pats.append(re.compile((r"\b" if a[:1].isascii() and a[:1].isalpha() else "") + re.escape(a) + r"(\d+)"
                                   + re.escape(b)))
        _LINE_PATTERNS = pats
    return _LINE_PATTERNS


def line_number_of(text: str) -> int | None:
    """文の中の最初の「行 N」(どの言語の言い方でも)の N。無ければ None。"""
    best = None
    for rx in _line_patterns():
        m = rx.search(text or "")
        if m is not None and (best is None or m.start() < best[0]):
            best = (m.start(), int(m.group(1)))
    return best[1] if best else None
