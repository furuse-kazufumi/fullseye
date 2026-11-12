# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_pyedit_syntax — Studio の Python エディタの色分け(Qt なし)。

何をするか
    1 行ずつの字句の走査(``scan_line``)で、文字の範囲に「区分」を付ける。区分は
    keyword / builtin / string / interp(f 文字列の ``{`` ``}`` と書式)/ number / comment /
    decorator / def_name / class_name / self / operator / name / bracket、そして Fullseye ならではの
    op(公開されている op の名前)と prelude(Program の前置きが用意する名前)。
    ブレークポイントの行・実行中の行・エラーの行・括弧の対応・同じ名前の強調は、字句の区分とは別の
    「重ね」(``Theme`` の色)として Qt 側(studio_pyedit_qt)が描く。

土台と Pygments
    * 土台(``base``): このファイルの自前の行スキャナ。標準の ``keyword`` / ``builtins`` だけで動く。
      標準の ``tokenize`` を使わないのは、3.12 から f 文字列が部品に分かれて版で結果が変わるのと、
      1 行ずつ(複数行の文字列の状態を整数 1 つで持つ)走らせたいから。``tokenize`` は試験で
      文字列・コメント・数の位置の照合に使う。
    * Pygments(``pygments``): 入っていれば ``PythonLexer`` の結果を**同じ区分に写す**。入っていなくても
      見た目の区分は変わらない(試験で両者の区分が一致することを確かめている)。

複数行の文字列の状態(ブロックの状態 = 整数)
    0 = 外、1..8 = 三連引用符の中。``1 + (引用符が " なら 1) + 2*(f 文字列) + 4*(raw)``。
    1 行を再描画して状態が変わらなければ、続きの行は再描画しない(Qt の QSyntaxHighlighter の作法)。

正直な限界
    * 三連引用符の f 文字列で ``{`` が行をまたいで開いたままの式は、次の行を文字列として塗る。
    * ``type X = ...``(3.12 の soft keyword)は塗らない。``match`` / ``case`` は行の形から判断する。
"""
from __future__ import annotations

import builtins
import keyword
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

#: 字句の区分(走査が付けるもの)。
LEXICAL = ("keyword", "builtin", "string", "interp", "number", "comment", "decorator",
           "def_name", "class_name", "self", "operator", "name", "bracket")
#: Fullseye の語彙で ``name`` を言い換える区分。
VOCAB = ("op", "prelude")
CATEGORIES = LEXICAL + VOCAB

Token = tuple  # (start, end, category)

_STRING_PREFIXES = frozenset({"r", "u", "b", "br", "rb", "f", "fr", "rf"})
_IDENT = re.compile(r"[^\W\d]\w*")
_NUM = re.compile(r"0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+"
                  r"|(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d[\d_]*)?[jJ]?")
_OPS = re.compile(r"->|:=|\*\*=?|//=?|<<=?|>>=?|!=|[-+*/%@&|^<>=]=?|~")
_BRACKETS = "()[]{}"
_BUILTIN_NAMES = frozenset(n for n in dir(builtins) if not n.startswith("_")
                           and n not in ("copyright", "credits", "exit", "quit", "license"))
_KEYWORDS = frozenset(keyword.kwlist)


def state_for(quote: str, is_f: bool, is_raw: bool) -> int:
    """三連引用符の中の状態の整数(1..8)。"""
    return 1 + (1 if quote == '"' else 0) + (2 if is_f else 0) + (4 if is_raw else 0)


def state_parts(state: int) -> tuple:
    """状態 → ``(引用符 3 文字, f か, raw か)``。0 は ``None``。"""
    if not state:
        return None
    s = state - 1
    return ('"""' if s & 1 else "'''", bool(s & 2), bool(s & 4))


# --------------------------------------------------------------------------- #
# 土台の行スキャナ
# --------------------------------------------------------------------------- #
class _Scan:
    """1 行ぶんの走査の作業場。"""

    __slots__ = ("text", "n", "out", "state_out", "first", "prev_kw", "prev_dot", "in_case", "open_str")

    def __init__(self, text: str):
        self.text = text
        self.n = len(text)
        self.out: list = []
        self.state_out = 0
        self.first = True        # この行の最初の字句か(match / case / decorator の判断)
        self.prev_kw = ""        # 直前の字句が def / class だったか
        self.prev_dot = False    # 直前の字句が属性アクセスの . だったか
        self.in_case = False     # case 文の行か(``case _:`` の _ を keyword にする)
        self.open_str = None     # 行末で閉じていない文字列 (開始の列, 引用符, f 文字列か)


def _emit(sc: _Scan, a: int, b: int, cat: str) -> None:
    if b > a:
        out = sc.out
        if out and out[-1][2] == cat and out[-1][1] == a and cat in ("string", "comment"):
            out[-1] = (out[-1][0], b, cat)
        else:
            out.append((a, b, cat))


def _scan_string_body(sc: _Scan, j: int, quote: str, is_f: bool, is_raw: bool, seg: int) -> tuple:
    """文字列の本体を ``j`` から走査する。``seg`` は今の「文字列の区間」の開始。
    返り値 ``(終わりの位置, 閉じたか)``。f 文字列では ``{...}`` の中を式として走査する。"""
    text, n = sc.text, sc.n
    ql = len(quote)
    while j < n:
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if text.startswith(quote, j):
            _emit(sc, seg, j + ql, "string")
            return j + ql, True
        if is_f and c == "{":
            if text.startswith("{{", j):
                j += 2
                continue
            _emit(sc, seg, j, "string")
            _emit(sc, j, j + 1, "interp")
            j = _scan_fexpr(sc, j + 1, quote)
            seg = j
            continue
        if is_f and c == "}" and text.startswith("}}", j):
            j += 2
            continue
        j += 1
    _emit(sc, seg, min(j, n), "string")
    return n, False


def _scan_fexpr(sc: _Scan, i: int, quote: str) -> int:
    """f 文字列の ``{`` の直後 ``i`` から、式・変換(``!r``)・書式(``:.2f``)・``}`` まで走査して、次の位置を返す。"""
    text, n = sc.text, sc.n
    i = _scan_code(sc, i, fexpr=True)
    if i < n and text[i] == "!" and i + 1 < n and text[i + 1] in "rsa":
        _emit(sc, i, i + 2, "interp")
        i += 2
    if i < n and text[i] == ":":
        _emit(sc, i, i + 1, "interp")
        i += 1
        seg = i
        while i < n and text[i] != "}":
            if text[i] == "{":                      # 書式の中の入れ子 {width}
                _emit(sc, seg, i, "string")
                _emit(sc, i, i + 1, "interp")
                i = _scan_fexpr(sc, i + 1, quote)
                seg = i
                continue
            if text.startswith(quote[0], i) and len(quote) == 1:
                break
            i += 1
        _emit(sc, seg, i, "string")
    if i < n and text[i] == "}":
        _emit(sc, i, i + 1, "interp")
        i += 1
    return i


def _soft_keyword_ok(sc: _Scan, word: str, end: int) -> bool:
    """``match`` / ``case`` を keyword として塗ってよいか(行頭で、後ろに式があり、行が : で終わる)。"""
    if not sc.first or word not in ("match", "case"):
        return False
    rest = sc.text[end:]
    stripped = rest.strip()
    if not stripped or stripped[0] in "=.,)]};:":
        return False
    code = re.sub(r"\s+#.*$", "", rest).rstrip()
    return code.endswith(":")


def _scan_code(sc: _Scan, i: int, fexpr: bool = False) -> int:
    """コードとして ``i`` から走査する。``fexpr`` のときは、深さ 0 の ``}`` ``:`` ``!r`` で止まる。"""
    text, n = sc.text, sc.n
    depth = 0
    while i < n:
        c = text[i]
        if c in " \t\f\r":
            i += 1
            continue
        if fexpr and depth == 0:
            if c == "}":
                return i
            if c == ":":
                return i
            if c == "=" and i + 1 < n and text[i + 1] in "}!:" and text[i - 1] not in "=!<>":
                _emit(sc, i, i + 1, "interp")           # f"{x=}" の = は書式の一部
                i += 1
                continue
            if c == "!" and i + 1 < n and text[i + 1] in "rsa" and (
                    i + 2 >= n or text[i + 2] in "}:"):
                return i
        if c == "#":
            _emit(sc, i, n, "comment")
            return n
        # -- 文字列(前置きつき)--
        if c in "'\"":
            i = _start_string(sc, i, i, "")
            sc.first = False
            sc.prev_kw = ""
            sc.prev_dot = False
            continue
        if c.isdigit() or (c == "." and i + 1 < n and text[i + 1].isdigit()):
            m = _NUM.match(text, i)
            _emit(sc, m.start(), m.end(), "number")
            i = m.end()
            sc.first = False
            sc.prev_kw = ""
            sc.prev_dot = False
            continue
        m = _IDENT.match(text, i)
        if m:
            word = m.group(0)
            e = m.end()
            if word.lower() in _STRING_PREFIXES and e < n and text[e] in "'\"" and not sc.prev_dot:
                i = _start_string(sc, i, e, word.lower())
                sc.first = False
                sc.prev_kw = ""
                continue
            if sc.prev_dot:
                cat = "name"
            elif word in _KEYWORDS or _soft_keyword_ok(sc, word, e):
                cat = "keyword"
                if word == "case":
                    sc.in_case = True
            elif word == "_" and sc.in_case:
                cat = "keyword"
            elif sc.prev_kw == "def":
                cat = "def_name"
            elif sc.prev_kw == "class":
                cat = "class_name"
            elif word in ("self", "cls"):
                cat = "self"
            elif word in _BUILTIN_NAMES:
                cat = "builtin"
            else:
                cat = "name"
            _emit(sc, i, e, cat)
            sc.prev_kw = word if (cat == "keyword" and word in ("def", "class")) else ""
            sc.first = False
            sc.prev_dot = False
            i = e
            continue
        if c == "@" and sc.first:
            m = re.compile(r"@\s*[^\W\d]\w*(?:\.[^\W\d]\w*)*").match(text, i)
            if m:
                _emit(sc, m.start(), m.end(), "decorator")
                i = m.end()
                sc.first = False
                continue
        if c in _BRACKETS:
            if c in "([{":
                depth += 1
            else:
                depth -= 1
            _emit(sc, i, i + 1, "bracket")
            i += 1
            sc.first = False
            sc.prev_kw = ""
            sc.prev_dot = False
            continue
        if c == ".":
            if text.startswith("...", i):
                i += 3                               # Ellipsis(区分なし。Pygments は . を 3 つの記号として扱う)
                sc.prev_dot = False
            else:
                sc.prev_dot = True
                i += 1
            sc.first = False
            sc.prev_kw = ""
            continue
        m = _OPS.match(text, i)
        if m:
            _emit(sc, m.start(), m.end(), "operator")
            i = m.end()
        else:
            i += 1                                  # , ; : など(区分なし)
        sc.first = False
        sc.prev_kw = ""
        sc.prev_dot = False
    return n


def _start_string(sc: _Scan, start: int, qpos: int, prefix: str) -> int:
    """``start`` から始まる文字列(前置き ``prefix``、引用符は ``qpos``)を走査して次の位置を返す。"""
    text, n = sc.text, sc.n
    q = text[qpos]
    is_f, is_raw = "f" in prefix, "r" in prefix
    if text.startswith(q * 3, qpos):
        quote = q * 3
    else:
        quote = q
    end, closed = _scan_string_body(sc, qpos + len(quote), quote, is_f, is_raw, start)
    if not closed:
        sc.open_str = (start, quote, is_f)
        if len(quote) == 3:
            sc.state_out = state_for(q, is_f, is_raw)
    return end


def scan_line_detail(text: str, state: int = 0) -> tuple:
    """土台の走査(詳細つき)。``(字句の列, 行末の状態, 閉じていない文字列)``。

    閉じていない文字列は ``(開始の列, 引用符, f 文字列か)`` か ``None``(補完が「文字列の中か」を知るのに使う)。"""
    sc = _Scan(text)
    i = 0
    parts = state_parts(state)
    if parts is not None:
        quote, is_f, is_raw = parts
        end, closed = _scan_string_body(sc, 0, quote, is_f, is_raw, 0)
        if not closed:
            return sc.out, state, (0, quote, is_f)
        sc.first = False
        i = end
    _scan_code(sc, i)
    return sc.out, sc.state_out, sc.open_str


def scan_line_base(text: str, state: int = 0) -> tuple:
    """土台の走査。``(字句の列, 行末の状態)``。字句は ``(開始, 終わり, 区分)``(``name`` と ``bracket`` も含む)。"""
    toks, st, _open = scan_line_detail(text, state)
    return toks, st


def triple_state_before(lines: Sequence, upto: int) -> int:
    """``lines[:upto]`` を走査した後の行の状態(0 または三連引用符の中)。

    三連引用符を含まない行は状態を変えないので、含む行だけを走査する(5,000 行でも 1 ms 台)。"""
    state = 0
    for k in range(min(upto, len(lines))):
        ln = lines[k]
        if "'''" in ln or '"""' in ln:
            state = scan_line_detail(ln, state)[1]
    return state


# --------------------------------------------------------------------------- #
# Pygments(任意)
# --------------------------------------------------------------------------- #
_PYG = {"mod": None, "lexer": None, "tried": False}


def pygments_available() -> bool:
    """Pygments を import できるか(結果は覚える。``reset_backend_cache`` で忘れる)。"""
    if not _PYG["tried"]:
        _PYG["tried"] = True
        try:
            from pygments.lexers.python import PythonLexer          # noqa: PLC0415
            _PYG["lexer"] = PythonLexer(stripnl=False, ensurenl=False)
            _PYG["mod"] = sys.modules["pygments"]
        except Exception:                                          # noqa: BLE001 — 無い・壊れている・塞がれている
            _PYG["lexer"] = None
    return _PYG["lexer"] is not None


def reset_backend_cache() -> None:
    """Pygments の有無の記憶を消す(試験で import を塞いだ後に使う)。"""
    _PYG.update(mod=None, lexer=None, tried=False)


def _pyg_category(ttype, value: str) -> str | None:
    from pygments.token import (Comment, Keyword, Name, Number, Operator, Punctuation, String)  # noqa: PLC0415
    if ttype in Keyword or ttype is Operator.Word:
        return "keyword"
    if ttype in Name.Builtin.Pseudo:
        if value in ("self", "cls"):
            return "self"
        return "builtin" if value in _BUILTIN_NAMES else "keyword"
    if ttype in Name.Builtin or ttype in Name.Exception:
        return "builtin" if value in _BUILTIN_NAMES else "name"
    if ttype in Name.Decorator:
        return "decorator"
    if ttype in Name.Function:
        return "def_name"
    if ttype in Name.Class:
        return "class_name"
    if ttype in Name:
        if value in ("self", "cls"):
            return "self"
        return "name"
    if ttype in String.Interpol:
        # %s / %(name)s と、普通の文字列の中の {2} {0!r} は書式の指定でなく文字列として塗る
        # (f 文字列の波括弧は Pygments が 1 文字ずつの字句にする)
        return "string" if value.startswith("%") or (value.startswith("{") and len(value) > 1) else "interp"
    if ttype in String:
        return "string"
    if ttype in Number:
        return "number"
    if ttype in Comment:
        return "comment"
    if ttype in Operator:
        return "operator"
    if ttype in Punctuation:
        return "bracket" if value in tuple(_BRACKETS) else None
    return None


def scan_line_pygments(text: str, state: int = 0) -> tuple:
    """Pygments の ``PythonLexer`` で 1 行を走査し、土台と同じ区分に写す。状態は土台の走査で求める
    (Pygments は状態を返さないので)。Pygments が使えなければ ``scan_line_base`` を返す。"""
    if not pygments_available():
        return scan_line_base(text, state)
    parts = state_parts(state)
    prefix = ""
    if parts is not None:
        quote, is_f, is_raw = parts
        prefix = ("r" if is_raw else "") + ("f" if is_f else "") + quote
    _t, state_out = scan_line_base(text, state)
    out: list = []
    off = len(prefix)
    for idx, ttype, value in _PYG["lexer"].get_tokens_unprocessed(prefix + text):
        a, b = idx - off, idx - off + len(value)
        if b <= 0:
            continue
        a = max(a, 0)
        b = min(b, len(text))
        if b <= a:
            continue
        cat = _pyg_category(ttype, value)
        if cat == "name" and value in _BUILTIN_NAMES and (a == 0 or text[a - 1] != "."):
            cat = "builtin"
        if cat is None or (cat == "operator" and value == "."):
            continue
        if cat == "name" and value in ("j", "J") and out and out[-1][2] == "number" and out[-1][1] == a:
            out[-1] = (out[-1][0], b, "number")         # 3j(Pygments は整数の虚数を 2 つに分ける)
            continue
        if cat in ("string", "comment") and out and out[-1][2] == cat and out[-1][1] == a:
            out[-1] = (out[-1][0], b, cat)
        else:
            out.append((a, b, cat))
    for i, (a, b, c) in enumerate(out):                 # __init__ のような魔法名は def の直後だけ def_name(土台と同じ)
        if c == "def_name":
            prev = out[i - 1] if i else None
            if not (prev and prev[2] == "keyword" and text[prev[0]:prev[1]] == "def"):
                out[i] = (a, b, "name")
    if state == 0:                                      # @a.b.c は 1 つの decorator(Pygments は . で分ける)
        m = re.match(r"\s*(@\s*[^\W\d]\w*(?:\.[^\W\d]\w*)*)", text)
        if m:
            da, db = m.start(1), m.end(1)
            out = [t for t in out if t[1] <= da or t[0] >= db]
            out.append((da, db, "decorator"))
            out.sort()
    return out, state_out


# --------------------------------------------------------------------------- #
# 語彙(op / prelude)の重ね
# --------------------------------------------------------------------------- #
_ATTR_OK = re.compile(r"(?<![\w.])(?:fs\.ledger\.|fs\.|ledger\.)$")


def refine(tokens: Sequence, text: str, ops: Iterable[str] = (), prelude: Iterable[str] = ()) -> list:
    """``name`` の字句を、op の名前なら ``op``、prelude の名前なら ``prelude`` に言い換える。

    属性(``x.gaussian``)は言い換えない。ただし ``fs.`` ``fs.ledger.`` ``ledger.`` の後ろは op として塗る。
    """
    ops = ops if isinstance(ops, (set, frozenset, dict)) else frozenset(ops)
    prelude = prelude if isinstance(prelude, (set, frozenset, dict)) else frozenset(prelude)
    if not ops and not prelude:
        return list(tokens)
    out = []
    for a, b, cat in tokens:
        if cat == "name":
            word = text[a:b]
            if a > 0 and text[a - 1] == "." and not _ATTR_OK.search(text[:a]):
                out.append((a, b, cat))
                continue
            if word in ops:
                cat = "op"
            elif word in prelude:
                cat = "prelude"
        out.append((a, b, cat))
    return out


# --------------------------------------------------------------------------- #
# 走査器(土台 / Pygments を選ぶ)
# --------------------------------------------------------------------------- #
@dataclass
class LineLexer:
    """1 行ずつの走査器。``backend`` は ``"auto"``(Pygments があれば使う)/ ``"base"`` / ``"pygments"``。"""
    backend: str = "auto"
    ops: frozenset = field(default_factory=frozenset)
    prelude: frozenset = field(default_factory=frozenset)

    def __post_init__(self):
        if self.backend not in ("auto", "base", "pygments"):
            raise ValueError("backend は auto / base / pygments のどれか(来たのは %r)" % (self.backend,))
        self.ops = frozenset(self.ops)
        self.prelude = frozenset(self.prelude)

    @property
    def active(self) -> str:
        """実際に使っている走査器の名前(``"base"`` か ``"pygments"``)。"""
        if self.backend == "base":
            return "base"
        return "pygments" if pygments_available() else "base"

    def scan(self, text: str, state: int = 0) -> tuple:
        fn: Callable = scan_line_pygments if self.active == "pygments" else scan_line_base
        toks, st = fn(text, state)
        if self.ops or self.prelude:
            toks = refine(toks, text, self.ops, self.prelude)
        return toks, st

    def scan_text(self, text: str) -> list:
        """全文を行ごとに走査する(試験・書き出し用)。返り値は行ごとの字句の列。"""
        res, st = [], 0
        for line in text.split("\n"):
            toks, st = self.scan(line, st)
            res.append(toks)
        return res


def char_categories(text: str, tokens: Sequence) -> list:
    """1 行の文字ごとの区分(空白は ``None``、区分の無い文字も ``None``)。区分の一致の試験用。"""
    cats = [None] * len(text)
    for a, b, cat in tokens:
        for k in range(a, min(b, len(text))):
            if not text[k].isspace():
                cats[k] = cat
    return cats


# --------------------------------------------------------------------------- #
# 括弧・同じ名前
# --------------------------------------------------------------------------- #
_PAIRS = {")": "(", "]": "[", "}": "{"}
_OPEN = "([{"


def brackets_of(tokens: Sequence, text: str) -> list:
    """1 行の括弧 ``[(列, 文字), ...]``(文字列・コメントの中の括弧は含まない)。"""
    return [(a, text[a]) for a, b, cat in tokens if cat == "bracket"]


def match_brackets(lines: Sequence) -> tuple:
    """全文の括弧の対応。``lines`` は行ごとの ``[(列, 文字), ...]``。

    返り値は ``(pairs, unmatched)``。``pairs`` は ``{(行, 列): (相手の行, 相手の列)}``(両向き)、
    ``unmatched`` は対応の無い括弧の ``[(行, 列), ...]``(閉じ忘れ・余分な閉じ・種類違い)。
    """
    stack: list = []
    pairs: dict = {}
    bad: list = []
    for ln, items in enumerate(lines):
        for col, ch in items:
            if ch in _OPEN:
                stack.append((ln, col, ch))
            else:
                if stack and stack[-1][2] == _PAIRS[ch]:
                    l0, c0, _ = stack.pop()
                    pairs[(l0, c0)] = (ln, col)
                    pairs[(ln, col)] = (l0, c0)
                else:
                    bad.append((ln, col))
    bad.extend((l0, c0) for l0, c0, _ in stack)
    return pairs, sorted(bad)


def bracket_at_cursor(items: Sequence, col: int) -> int | None:
    """カーソル(``col`` = 文字の間の位置)の隣の括弧の列。右隣を先に、無ければ左隣。"""
    cols = {c for c, _ in items}
    if col in cols:
        return col
    if col - 1 in cols:
        return col - 1
    return None


_NAMEY = ("name", "builtin", "self", "op", "prelude", "def_name", "class_name")


def name_at(tokens: Sequence, text: str, col: int) -> str | None:
    """カーソル(``col``)の下の名前(識別子の字句)。無ければ ``None``。"""
    for a, b, cat in tokens:
        if a <= col <= b and cat in _NAMEY:
            return text[a:b]
    return None


def occurrences(tokens: Sequence, text: str, word: str) -> list:
    """1 行の中の ``word`` の出現 ``[(開始, 終わり), ...]``(名前の字句だけ。文字列・コメントの中は含まない)。"""
    return [(a, b) for a, b, cat in tokens if cat in _NAMEY and text[a:b] == word]


# --------------------------------------------------------------------------- #
# 配色(明・暗)とコントラスト
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Style:
    """1 つの区分の見た目。色だけに頼らないよう、太字・斜体・下線も持つ。"""
    color: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    fg: str
    styles: dict
    current_line_bg: str
    occurrence_bg: str
    bracket_match_bg: str
    bracket_bad_fg: str
    breakpoint_bg: str
    exec_bg: str
    error_bg: str
    error_line_color: str          # 波線の色
    gutter_bg: str
    gutter_fg: str
    selection_bg: str
    selection_fg: str

    def style(self, cat: str) -> Style:
        return self.styles.get(cat) or self.styles["name"]

    def overlay_backgrounds(self) -> dict:
        """文字が重なりうる背景(コントラストの検査の対象)。"""
        return {"bg": self.bg, "current_line": self.current_line_bg, "occurrence": self.occurrence_bg,
                "bracket_match": self.bracket_match_bg, "breakpoint": self.breakpoint_bg,
                "exec": self.exec_bg, "error": self.error_bg}


THEMES = {
    "dark": Theme(
        name="dark", bg="#1b1e28", fg="#e2e5ec",
        styles={
            "name": Style("#e2e5ec"),
            "keyword": Style("#e8b363", bold=True),
            "builtin": Style("#86adf9"),
            "string": Style("#a9d476"),
            "interp": Style("#5fd7c4", bold=True),
            "number": Style("#ff9e64"),
            "comment": Style("#a3abc6", italic=True),
            "decorator": Style("#c3a6ff", italic=True),
            "def_name": Style("#7dcfff", bold=True),
            "class_name": Style("#ffd479", bold=True, underline=True),
            "self": Style("#f59ab6", italic=True),
            "operator": Style("#89ddff"),
            "bracket": Style("#c0c6d6"),
            "op": Style("#2ee0cb", bold=True),
            "prelude": Style("#d6a8ff"),
        },
        current_line_bg="#222634", occurrence_bg="#27324c", bracket_match_bg="#2b3a58",
        bracket_bad_fg="#ff6b6b", breakpoint_bg="#3c2128", exec_bg="#33311a", error_bg="#412020",
        error_line_color="#ff6b6b", gutter_bg="#12141b", gutter_fg="#8b91a0",
        selection_bg="#3b4f7a", selection_fg="#ffffff"),
    "light": Theme(
        name="light", bg="#fbfbfd", fg="#1f2430",
        styles={
            "name": Style("#1f2430"),
            "keyword": Style("#8a4b00", bold=True),
            "builtin": Style("#1a55b0"),
            "string": Style("#2f6b14"),
            "interp": Style("#00695c", bold=True),
            "number": Style("#a63d00"),
            "comment": Style("#566075", italic=True),
            "decorator": Style("#6a3fc0", italic=True),
            "def_name": Style("#005f80", bold=True),
            "class_name": Style("#7a5200", bold=True, underline=True),
            "self": Style("#b02a55", italic=True),
            "operator": Style("#00637f"),
            "bracket": Style("#3c4356"),
            "op": Style("#00695c", bold=True),
            "prelude": Style("#7a3db8"),
        },
        current_line_bg="#eef1f7", occurrence_bg="#e7eefc", bracket_match_bg="#dde6fa",
        bracket_bad_fg="#c4001a", breakpoint_bg="#fbe6e9", exec_bg="#f8f2cf", error_bg="#fbe3e3",
        error_line_color="#d0001e", gutter_bg="#eceef4", gutter_fg="#5d6577",
        selection_bg="#b9ccf2", selection_fg="#101420"),
}


def _lin(c: int) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _rgb(color: str) -> tuple:
    c = color.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        raise ValueError("色は #rrggbb の形(来たのは %r)" % (color,))
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def relative_luminance(color: str) -> float:
    """WCAG 2 の相対輝度。"""
    r, g, b = _rgb(color)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 2 のコントラスト比(1..21)。"""
    a, b = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


MIN_CONTRAST = 4.5


def contrast_report(theme: Theme) -> list:
    """``[(ラベル, 比)]``: 全区分の文字色 × 重なりうる背景、ガターの数字、選択範囲。比が低い順。"""
    rows = []
    for bgname, bg in theme.overlay_backgrounds().items():
        for cat, st in theme.styles.items():
            rows.append(("%s on %s" % (cat, bgname), contrast_ratio(st.color, bg)))
    rows.append(("gutter", contrast_ratio(theme.gutter_fg, theme.gutter_bg)))
    rows.append(("selection", contrast_ratio(theme.selection_fg, theme.selection_bg)))
    rows.append(("bracket_bad on bg", contrast_ratio(theme.bracket_bad_fg, theme.bg)))
    rows.append(("bracket_bad on current_line", contrast_ratio(theme.bracket_bad_fg, theme.current_line_bg)))
    rows.append(("error wave on bg", contrast_ratio(theme.error_line_color, theme.bg)))
    return sorted(rows, key=lambda r: r[1])


def theme_by_name(name: str) -> Theme:
    """``"dark"`` / ``"light"``。知らない名前は ``ValueError``(黙って暗にしない)。"""
    if name not in THEMES:
        raise ValueError("theme は %s のどれか(来たのは %r)" % (" / ".join(THEMES), name))
    return THEMES[name]
