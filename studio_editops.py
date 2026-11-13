# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_editops — コードエディタの編集操作の計算(Qt なし): 矩形選択・複数カーソル・行の操作・括弧。

Studio のコードエディタ(``QPlainTextEdit``)へ後付けする編集操作のうち、**画面に依らない部分**をここに置く。
Qt の側(``studio_editops_qt``)は、キーとマウスをここの関数へ渡し、返ってきた編集(``Edit``)を文書へ当てるだけ。

一番壊れやすいのは「見た目の桁 ↔ 文字の位置」の変換なので、ここに切り出して単体で試験する。

桁の数え方(決めた事)
--------------------
* 位置は **Python の文字(コードポイント)の番号**。Qt は UTF-16 の単位で数えるので、境目で
  ``cp_to_u16`` / ``u16_to_cp`` を通す(絵文字など BMP の外の文字は UTF-16 で 2 単位)。
* 1 つの **まとまり**(``Cell``)= 基底の文字 + 後ろに付く結合文字・異体字セレクタ・ZWJ で繋がる絵文字・
  国旗(地域指示記号 2 つ)。カーソルも箱の端も、まとまりの途中には置かない。
* 幅: 全角(``unicodedata.east_asian_width`` が W / F)= 2 桁、それ以外 = 1 桁、タブ = 次のタブ位置まで。
  結合文字などは 0 桁(前のまとまりに含める)。曖昧幅(A。※ ○ → α など)は書体で変わるので、
  ``Columns.ambiguous`` に「その書体で全角に出るか」を答える関数を渡す(無ければ 1 桁)。
* 箱の端がまとまりの途中(全角の真ん中・タブの途中)に来たら **近い方の境目** へ寄せる(同じ距離なら左)。
  VS Code の ``columnFromVisibleColumn`` と同じ規則。
* 行が箱の左端に届かない時、その行は**箱に入れない**(仮想の空白は作らない。打っても空白で埋めない)。
  全部の行が届かない時だけ、全部の行の行末にカーソルを置く。VS Code と同じ。
  (VS Code と違う所: 箱の端が全角の真ん中に来た行も箱から外さない。日本語の行が黙って抜けるのを避ける。)
"""
from __future__ import annotations

import json
import os
import unicodedata
from typing import Callable, Iterable, NamedTuple, Sequence

#: 既定のタブ幅(Studio のエディタは ``setTabStopDistance(4 * 空白の幅)``)。
TAB_WIDTH = 4
_ZWJ = "‍"
_BRACKETS = {"(": ")", "[": "]", "{": "}"}
_CLOSERS = {v: k for k, v in _BRACKETS.items()}


# --------------------------------------------------------------------------- #
# 見た目の桁 ↔ 文字の位置
# --------------------------------------------------------------------------- #
class Cell(NamedTuple):
    """1 つのまとまり。``start``/``end`` は文字の番号(end は含まない)、``col`` は左端の桁、``width`` は桁数。"""
    start: int
    end: int
    col: int
    width: int


def _is_extend(ch: str) -> bool:
    """前のまとまりに付く文字か(結合文字・書式文字・制御文字・ハングルの中声と終声・絵文字の肌色)。"""
    o = ord(ch)
    if o < 0x300:
        return o < 0x20 or 0x7F <= o < 0xA0 or o == 0xAD
    if unicodedata.category(ch) in ("Mn", "Me", "Mc", "Cf", "Cc"):
        return True
    return 0x1160 <= o <= 0x11FF or 0x1F3FB <= o <= 0x1F3FF


def char_width(ch: str) -> int:
    """1 文字の桁数(タブ以外)。全角 = 2、前に付く文字 = 0、それ以外 = 1。"""
    if len(ch) != 1:
        raise ValueError("1 文字を渡す(来たのは %r)" % (ch,))
    if ch == "\t":
        raise ValueError("タブの幅は位置で決まる。cells() を使う")
    if _is_extend(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _is_simple(text: str) -> bool:
    """1 文字 = 1 桁 = UTF-16 の 1 単位で済む行か(速い道)。"""
    return text.isascii() and text.isprintable()


class Columns(NamedTuple):
    """桁の数え方。``tab`` を受ける関数は、整数(タブ幅)の代わりにこれも受ける。

    ``ambiguous``: 曖昧幅の文字(``east_asian_width`` が A。※ ○ → α など)が**その書体で全角に出るか**を
    答える関数。書体で変わる(日本語の書体では全角、欧文の書体では半角)ので、Qt の側が実際の書体で測って渡す。
    ``None`` なら全部 1 桁。
    """
    tab: int = TAB_WIDTH
    ambiguous: Callable | None = None


def cells(text: str, tab=TAB_WIDTH) -> list:
    """行 ``text`` をまとまり(``Cell``)の並びにする。改行は含めない事。``tab`` はタブ幅か ``Columns``。"""
    ambiguous = None
    if isinstance(tab, Columns):
        tab, ambiguous = tab.tab, tab.ambiguous
    if tab < 1:
        raise ValueError("タブ幅は 1 以上(来たのは %r)" % (tab,))
    out: list = []
    col = 0
    join_next = False
    ri_open = False
    for i, ch in enumerate(text):
        if ch == "\t":
            w = tab - (col % tab)
            out.append([i, i + 1, col, w])
            col += w
            join_next = ri_open = False
            continue
        is_ri = 0x1F1E6 <= ord(ch) <= 0x1F1FF
        can_join = bool(out) and text[out[-1][0]] != "\t"
        if can_join and (_is_extend(ch) or join_next or (is_ri and ri_open)):
            out[-1][1] = i + 1
            if is_ri:
                ri_open = False
        else:
            # 地域指示記号(国旗の半分)は east_asian_width では N だが、絵文字として全角の幅で出る
            eaw = unicodedata.east_asian_width(ch)
            w = 2 if (is_ri or eaw in ("W", "F") or (eaw == "A" and ambiguous is not None and ambiguous(ch))) else 1
            out.append([i, i + 1, col, w])
            col += w
            ri_open = is_ri
        join_next = ch == _ZWJ
    return [Cell(*c) for c in out]


def text_width(text: str, tab: int = TAB_WIDTH) -> int:
    """行の見た目の桁数。"""
    if _is_simple(text):
        return len(text)
    cs = cells(text, tab)
    return cs[-1].col + cs[-1].width if cs else 0


def col_of(text: str, index: int, tab: int = TAB_WIDTH) -> int:
    """文字の位置 ``index`` の見た目の桁。まとまりの途中なら、そのまとまりの左端の桁。"""
    if index <= 0:
        return 0
    if _is_simple(text):
        return min(index, len(text))
    cs = cells(text, tab)
    for c in cs:
        if index < c.end:
            return c.col
    return cs[-1].col + cs[-1].width if cs else 0


def index_at_col(text: str, col: int, tab: int = TAB_WIDTH) -> int:
    """見た目の桁 ``col`` に一番近い境目の文字の位置(同じ距離なら左)。行末より右なら行末。"""
    if col <= 0:
        return 0
    if _is_simple(text):
        return min(col, len(text))
    for c in cells(text, tab):
        if col <= c.col:
            return c.start
        right = c.col + c.width
        if col < right:
            return c.end if (right - col) < (col - c.col) else c.start
    return len(text)


def snap_index(text: str, index: int) -> int:
    """``index`` がまとまりの途中なら、そのまとまりの先頭へ寄せる。"""
    index = max(0, min(index, len(text)))
    if _is_simple(text):
        return index
    for c in cells(text):
        if c.start < index < c.end:
            return c.start
    return index


def next_boundary(text: str, index: int) -> int:
    """``index`` より右の、一番近い境目(行末なら行末)。"""
    if index >= len(text):
        return len(text)
    if _is_simple(text):
        return index + 1
    for c in cells(text):
        if c.end > index:
            return c.end
    return len(text)


def prev_boundary(text: str, index: int) -> int:
    """``index`` より左の、一番近い境目(行頭なら 0)。"""
    if index <= 0:
        return 0
    if _is_simple(text):
        return min(index, len(text)) - 1
    best = 0
    for c in cells(text):
        if c.start < index:
            best = c.start
        else:
            break
    return best


def step_col(text: str, col: int, direction: int, tab: int = TAB_WIDTH) -> int:
    """箱の端を左右へ 1 つ動かした桁。文字の上ではまとまり 1 つ分、行末より右では 1 桁ずつ。"""
    cs = cells(text, tab)
    width = cs[-1].col + cs[-1].width if cs else 0
    if direction > 0:
        for c in cs:
            if c.col + c.width > col:
                return c.col + c.width
        return col + 1
    if col > width:
        return col - 1
    best = 0
    for c in cs:
        if c.col < col:
            best = c.col
    return best


def cp_to_u16(text: str, index: int) -> int:
    """文字の位置 → UTF-16 の単位の位置(Qt の ``positionInBlock``)。"""
    index = max(0, min(index, len(text)))
    if text.isascii():
        return index
    return index + sum(1 for ch in text[:index] if ch > "￿")


def u16_to_cp(text: str, units: int) -> int:
    """UTF-16 の単位の位置 → 文字の位置。サロゲートの途中なら、その文字の先頭。"""
    if units <= 0:
        return 0
    if text.isascii():
        return min(units, len(text))
    u = 0
    for i, ch in enumerate(text):
        step = 2 if ch > "￿" else 1
        if u + step > units:
            return i
        u += step
    return len(text)


def u16_len(text: str) -> int:
    """UTF-16 の単位で数えた長さ。"""
    return cp_to_u16(text, len(text))


def split_lines(text: str) -> tuple:
    """文面を行に分ける。``(行の並び, 改行の種類)``。CRLF・LF・CR のどれでも同じ行の並びになる。"""
    if "\r\n" in text:
        nl = "\r\n"
    elif "\r" in text and "\n" not in text:
        nl = "\r"
    else:
        nl = "\n"
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), nl


# --------------------------------------------------------------------------- #
# カーソル(複数)と編集
# --------------------------------------------------------------------------- #
class Caret(NamedTuple):
    """1 行の中の選択 1 つ。``anchor`` → ``pos``(文字の位置)。同じなら幅 0 のカーソル。"""
    line: int
    anchor: int
    pos: int

    @property
    def start(self) -> int:
        return min(self.anchor, self.pos)

    @property
    def end(self) -> int:
        return max(self.anchor, self.pos)

    @property
    def empty(self) -> bool:
        return self.anchor == self.pos


class Edit(NamedTuple):
    """1 行の中の置き換え 1 つ: ``line`` 行の ``start``〜``end`` を ``text`` にする。"""
    line: int
    start: int
    end: int
    text: str


def normalize_carets(carets: Iterable) -> list:
    """行・位置の順に並べ、重なったものを 1 つにする(同じ位置の幅 0 のカーソルも 1 つに)。"""
    out: list = []
    for c in sorted(carets, key=lambda c: (c.line, c.start, c.end)):
        if out and out[-1].line == c.line and (c.start < out[-1].end or (c.start == out[-1].start)
                                               or (c.empty and c.start == out[-1].end and out[-1].empty)):
            p = out[-1]
            s, e = min(p.start, c.start), max(p.end, c.end)
            out[-1] = Caret(p.line, s, e) if p.anchor <= p.pos else Caret(p.line, e, s)
        else:
            out.append(c)
    return out


def box_carets(lines: Sequence, a_line: int, a_col: int, c_line: int, c_col: int,
               tab: int = TAB_WIDTH) -> list:
    """箱(固定の角 ``a_line, a_col`` と動く角 ``c_line, c_col``。桁は見た目の桁)→ 行ごとの選択。

    箱の左端に届かない行は入れない。全部の行が届かなければ、全部の行の行末に幅 0 のカーソル。
    """
    lo, hi = min(a_line, c_line), max(a_line, c_line)
    lo, hi = max(0, lo), min(len(lines) - 1, hi)
    left, right = min(a_col, c_col), max(a_col, c_col)
    out = []
    for ln in range(lo, hi + 1):
        t = lines[ln]
        if text_width(t, tab) < left:
            continue
        s, e = index_at_col(t, left, tab), index_at_col(t, right, tab)
        out.append(Caret(ln, s, e) if a_col <= c_col else Caret(ln, e, s))
    if not out:
        out = [Caret(ln, len(lines[ln]), len(lines[ln])) for ln in range(lo, hi + 1)]
    return out


def plan_replace(carets: Sequence, texts: Sequence) -> tuple:
    """各選択を ``texts`` の対応する文で置き換える計画。``(編集の並び, 置き換えた後のカーソル)``。

    ``carets`` は ``normalize_carets`` 済み(行・位置の順、重なりなし)。文に改行が無ければ、
    返すカーソルは各々の文の直後(幅 0)。
    """
    if len(carets) != len(texts):
        raise ValueError("選択 %d 個に文 %d 個" % (len(carets), len(texts)))
    edits, out = [], []
    line, delta = None, 0
    for c, t in zip(carets, texts):
        if c.line != line:
            line, delta = c.line, 0
        edits.append(Edit(c.line, c.start, c.end, t))
        p = c.start + delta + len(t)
        out.append(Caret(c.line, p, p))
        delta += len(t) - (c.end - c.start)
    return edits, out


def plan_delete(lines: Sequence, carets: Sequence, backward: bool) -> tuple:
    """Delete(``backward=False``)/ Backspace(True)。選びがあればそれを、無ければ隣のまとまり 1 つを消す。

    行をまたいでは消さない(行末の Delete・行頭の Backspace は何もしない)。
    """
    grown = []
    for c in carets:
        if c.empty:
            t = lines[c.line]
            s = prev_boundary(t, c.pos) if backward else c.pos
            e = c.pos if backward else next_boundary(t, c.pos)
            grown.append(Caret(c.line, s, e))
        else:
            grown.append(c)
    grown = normalize_carets(grown)
    return plan_replace(grown, [""] * len(grown))


def paste_rows(clip: str, count: int) -> tuple:
    """貼り付ける文を ``count`` 個の選択へ配る。``(配り方, 文の並び)``。

    * ``"spread"``: 貼る物の行数 = 選択の数 → 行ごとに 1 つずつ。
    * ``"same"``: 貼る物が 1 行 → 全部の選択に同じ物。
    * ``"full"``: それ以外 → 全部の選択に、貼る物を丸ごと(改行を含む)。
    """
    rows, _nl = split_lines(clip)
    if len(rows) > 1 and rows[-1] == "":
        rows = rows[:-1]
    if len(rows) == count and count > 1:
        return "spread", rows
    if len(rows) <= 1:
        return "same", [rows[0] if rows else ""] * count
    return "full", ["\n".join(rows)] * count


def apply_edits(lines: Sequence, edits: Iterable) -> list:
    """編集を当てた新しい行の並び(元は変えない)。文に改行があれば行が増える。"""
    out = list(lines)
    for e in sorted(edits, key=lambda e: (e.line, e.start), reverse=True):
        t = out[e.line]
        out[e.line:e.line + 1] = (t[:e.start] + e.text + t[e.end:]).split("\n")
    return out


def shift_carets(carets: Sequence, edits: Iterable) -> list:
    """改行を含まない編集を当てた後の、カーソルの新しい位置(選びの向きと幅は保つ)。"""
    by_line: dict = {}
    for e in edits:
        by_line.setdefault(e.line, []).append(e)

    def move(line: int, i: int) -> int:
        d = 0
        for e in sorted(by_line.get(line, ()), key=lambda e: e.start):
            if i >= e.end:
                d += len(e.text) - (e.end - e.start)
            elif i > e.start:
                return e.start + d + len(e.text)
        return i + d

    return [Caret(c.line, move(c.line, c.anchor), move(c.line, c.pos)) for c in carets]


def move_carets(lines: Sequence, carets: Sequence, how: str, select: bool = False) -> list:
    """全部のカーソルを動かす。``how`` は ``left`` / ``right`` / ``home`` / ``end``。``select`` なら選びを伸ばす。"""
    out = []
    for c in carets:
        t = lines[c.line]
        if how == "left":
            p = c.start if (not select and not c.empty) else prev_boundary(t, c.pos)
        elif how == "right":
            p = c.end if (not select and not c.empty) else next_boundary(t, c.pos)
        elif how == "home":
            first = len(t) - len(t.lstrip(" \t"))
            p = 0 if c.pos == first else first
        elif how == "end":
            p = len(t)
        else:
            raise ValueError("動かし方は left / right / home / end(来たのは %r)" % (how,))
        out.append(Caret(c.line, c.anchor if select else p, p))
    return normalize_carets(out)


# --------------------------------------------------------------------------- #
# 行の操作
# --------------------------------------------------------------------------- #
def plan_indent(lines: Sequence, line_numbers: Iterable, width: int = 4) -> list:
    """行頭に空白 ``width`` 個を足す編集。空白だけの行・空行は触らない。"""
    return [Edit(ln, 0, 0, " " * width) for ln in sorted(set(line_numbers)) if lines[ln].strip()]


def plan_outdent(lines: Sequence, line_numbers: Iterable, width: int = 4) -> list:
    """行頭の字下げを 1 段(空白なら ``width`` 個まで、タブなら 1 個)外す編集。"""
    out = []
    for ln in sorted(set(line_numbers)):
        t = lines[ln]
        if t.startswith("\t"):
            n = 1
        else:
            n = 0
            while n < width and n < len(t) and t[n] == " ":
                n += 1
        if n:
            out.append(Edit(ln, 0, n, ""))
    return out


def plan_toggle_comment(lines: Sequence, line_numbers: Iterable, prefix: str = "#") -> list:
    """行コメントの付け外し。対象の行が全部コメントなら外し、1 行でも違えば全部に付ける。空行は触らない。

    付ける位置は、対象の行のうち一番浅い字下げの桁(行頭に寄せない: 字下げの中身が読める)。
    """
    if not prefix:
        raise ValueError("コメントの印が空")
    rows = [ln for ln in sorted(set(line_numbers)) if lines[ln].strip()]
    if not rows:
        return []
    if all(lines[ln].lstrip(" \t").startswith(prefix) for ln in rows):
        out = []
        for ln in rows:
            t = lines[ln]
            ind = len(t) - len(t.lstrip(" \t"))
            n = len(prefix) + (1 if t[ind + len(prefix):ind + len(prefix) + 1] == " " else 0)
            out.append(Edit(ln, ind, ind + n, ""))
        return out
    depth = min(len(lines[ln]) - len(lines[ln].lstrip(" \t")) for ln in rows)
    return [Edit(ln, depth, depth, prefix + " ") for ln in rows]


def reorder_lines(lines: Sequence, first: int, last: int, delta: int) -> tuple | None:
    """``first``〜``last`` 行を 1 行上(``delta=-1``)か下(``+1``)へ動かす。

    ``(置き換える最初の行, 最後の行, 新しい行の並び)``。端で動かせなければ ``None``。
    """
    if delta < 0:
        if first <= 0:
            return None
        return first - 1, last, list(lines[first:last + 1]) + [lines[first - 1]]
    if last >= len(lines) - 1:
        return None
    return first, last + 1, [lines[last + 1]] + list(lines[first:last + 1])


def strip_trailing_edits(lines: Sequence) -> list:
    """行末の空白とタブを落とす編集(全角の空白は落とさない: 文字列の中身かもしれない)。"""
    out = []
    for ln in range(len(lines)):
        t = lines[ln]
        k = len(t.rstrip(" \t"))
        if k < len(t):
            out.append(Edit(ln, k, len(t), ""))
    return out


def strip_trailing_text(text: str) -> str:
    """文面の各行の行末の空白とタブを落とす(改行の種類はそのまま)。"""
    rows, nl = split_lines(text)
    return nl.join(r.rstrip(" \t") for r in rows)


# --------------------------------------------------------------------------- #
# 語・次の一致・括弧
# --------------------------------------------------------------------------- #
def _is_word(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def word_at(text: str, index: int) -> tuple | None:
    """``index`` の所(または直前)の語の範囲 ``(start, end)``。語でなければ ``None``。"""
    index = max(0, min(index, len(text)))
    if not (index < len(text) and _is_word(text[index])):
        if index == 0 or not _is_word(text[index - 1]):
            return None
        index -= 1
    s = e = index
    while s > 0 and _is_word(text[s - 1]):
        s -= 1
    while e < len(text) and _is_word(text[e]):
        e += 1
    return s, e


def next_occurrence(lines: Sequence, needle: str, line: int, index: int, taken: Iterable = (),
                    whole_word: bool = False) -> tuple | None:
    """``(line, index)`` より後ろの、次の ``needle`` の位置 ``(行, 文字の位置)``。末尾まで行ったら先頭から。

    ``taken``(既に選んである ``(行, 位置)``)は飛ばす。大文字と小文字は区別する。
    """
    if not needle or "\n" in needle:
        return None
    skip = set(taken)
    n = len(lines)
    for k in range(n + 1):
        ln = (line + k) % n
        t = lines[ln]
        i = t.find(needle, index if k == 0 else 0)
        while i >= 0:
            wrapped_past_start = k == n and i >= index
            ok = (ln, i) not in skip and not wrapped_past_start
            if ok and whole_word:
                e = i + len(needle)
                ok = not (i > 0 and _is_word(t[i - 1])) and not (e < len(t) and _is_word(t[e]))
            if ok:
                return ln, i
            i = t.find(needle, i + 1)
    return None


def bracket_table(lines: Sequence, comment_prefix: str = "#") -> list:
    """行ごとの括弧の表 ``[[(文字の位置, 括弧), ...], ...]``。文字列とコメントの中の括弧は数えない。

    ``comment_prefix`` が ``#`` なら行の途中からのコメント(Python)。それ以外(パイプラインの ``*``)は、
    行頭(字下げの後)がその印の行を丸ごとコメントとして扱う。
    """
    out = []
    triple = None
    for ln in range(len(lines)):
        t = lines[ln]
        row: list = []
        out.append(row)
        if triple is None and comment_prefix and comment_prefix != "#" and t.lstrip(" \t").startswith(comment_prefix):
            continue
        i, n = 0, len(t)
        while i < n:
            if triple is not None:
                j = t.find(triple, i)
                if j < 0:
                    break
                i, triple = j + 3, None
                continue
            ch = t[i]
            if ch == "#" and comment_prefix == "#":
                break
            if ch in "\"'":
                if t.startswith(ch * 3, i):
                    triple = ch * 3
                    i += 3
                    continue
                i += 1
                while i < n and t[i] != ch:
                    i += 2 if t[i] == "\\" else 1
                i += 1
                continue
            if ch in _BRACKETS or ch in _CLOSERS:
                row.append((i, ch))
            i += 1
    return out


def match_bracket(table: Sequence, line: int, index: int) -> tuple | None:
    """カーソルの右(無ければ左)の括弧と、対応する括弧。``(行, 位置, 相手の行, 相手の位置)``。無ければ ``None``。"""
    if not 0 <= line < len(table):
        return None
    here = None
    for want in (index, index - 1):
        for i, ch in table[line]:
            if i == want:
                here = (i, ch)
                break
        if here:
            break
    if here is None:
        return None
    i0, ch = here
    if ch in _BRACKETS:
        other, depth = _BRACKETS[ch], 0
        for ln in range(line, len(table)):
            for i, c in table[ln]:
                if ln == line and i <= i0:
                    continue
                if c == ch:
                    depth += 1
                elif c == other:
                    if depth == 0:
                        return line, i0, ln, i
                    depth -= 1
        return None
    other, depth = _CLOSERS[ch], 0
    for ln in range(line, -1, -1):
        for i, c in reversed(table[ln]):
            if ln == line and i >= i0:
                continue
            if c == ch:
                depth += 1
            elif c == other:
                if depth == 0:
                    return line, i0, ln, i
                depth -= 1
    return None


# --------------------------------------------------------------------------- #
# キーの割り当て。この表は**既定**(Visual Studio 風の型)。利用者が変えた今のキーは studio_keymap の登録簿が
# 持ち、studio_editops_qt.apply_bindings で配る(2026-11-13)。Qt の側・文書・当たりの検査はここか登録簿から引く。
# --------------------------------------------------------------------------- #
class Binding(NamedTuple):
    """操作 1 つ。``when``: ``always`` = いつでも / ``box`` = 箱か複数カーソルがある時だけ /
    ``no_own_comment`` = エディタが自分の Ctrl+/ を持たない時だけ。"""
    command: str
    keys: tuple
    title: str
    group: str
    when: str = "always"


KEYMAP = (
    Binding("box.up", ("Shift+Alt+Up", "Ctrl+Alt+Up"), "Extend box selection up", "box"),
    Binding("box.down", ("Shift+Alt+Down", "Ctrl+Alt+Down"), "Extend box selection down", "box"),
    Binding("box.left", ("Shift+Alt+Left",), "Extend box selection left", "box"),
    Binding("box.right", ("Shift+Alt+Right",), "Extend box selection right", "box"),
    Binding("multi.add_next", ("Shift+Alt+.",), "Add next occurrence to the selection", "box"),
    Binding("box.cancel", ("Esc",), "Cancel box selection", "box", "box"),
    Binding("line.duplicate", ("Ctrl+D",), "Duplicate line", "line"),
    Binding("line.move_up", ("Alt+Up",), "Move line up", "line"),
    Binding("line.move_down", ("Alt+Down",), "Move line down", "line"),
    Binding("line.delete", ("Ctrl+Shift+K",), "Delete line", "line"),
    Binding("line.comment", ("Ctrl+/",), "Toggle line comment", "line", "no_own_comment"),
    Binding("line.indent", ("Tab",), "Indent", "line"),
    Binding("line.outdent", ("Shift+Tab",), "Outdent", "line"),
    Binding("bracket.jump", ("Ctrl+]",), "Go to matching bracket", "line"),
    Binding("edit.trim", (), "Trim trailing whitespace", "line"),
)

#: エディタの部品が QAction を通さずに自分で受けているキー(studio.py の ProgramEditor / CodeEditor と PyEditAssist)。
EDITOR_INTERNAL_KEYS = ("Ctrl+Space", "Ctrl+Return", "Ctrl+F", "Ctrl+H", "Ctrl+/", "F3", "Shift+F3", "Shift+F1",
                        "Ctrl++", "Ctrl+=", "Ctrl+-")

#: メニューと案内に出す文(英語が正)。対訳は ``studio_assets/studio_editops_i18n.json``。
MENU_BOX = "Box selection"
MENU_LINE = "Line operations"
MENU_DISPLAY = "Editor display"
ACT_HOWTO = "How to use box selection…"
ACT_RULERS = "Column rulers at 79 and 99"
ACT_TRIM_ON_SAVE = "Trim trailing whitespace on save"
MSG_NO_BRACKET = "no matching bracket"
MSG_NO_OCCURRENCE = "no other occurrence"
MSG_TRIMMED = "%d lines trimmed"
MSG_BOX = "box: %d lines"
#: 「矩形選択の使い方」の窓で、キーの設定で変えたキーを並べる前の 1 行。
MSG_KEYS_CHANGED = "Some keys were changed in the keyboard settings:"
HOWTO_TITLE = "Box selection"
HOWTO_TEXT = (
    "Box (column) selection\n"
    "\n"
    "Alt + drag: select a box\n"
    "Shift + Alt + arrow keys: grow or shrink the box\n"
    "Shift + Alt + click: a box from the cursor to the click\n"
    "Ctrl + Alt + Up / Down: add a cursor above / below\n"
    "Typing, Delete, Backspace, Tab: applied to every line of the box\n"
    "Ctrl + C / X / V: copy, cut and paste row by row\n"
    "Shift + Alt + . : add the next occurrence of the selected word\n"
    "Esc or a plain click: back to one cursor\n"
    "\n"
    "Columns are counted as they look: a full-width character is 2 columns and a tab runs to the next "
    "tab stop. Lines that do not reach the left edge of the box are left out."
)


#: コマンドパレットの別名(日本語と英語。studio.PALETTE_WORDS へ足す)。鍵は command_actions の名前。
PALETTE_WORDS = {
    "editops_box_up": "矩形 箱 列 縦 複数行 カーソル box column block rectangular multi cursor 選択",
    "editops_box_down": "矩形 箱 列 縦 複数行 カーソル box column block rectangular multi cursor 選択",
    "editops_box_left": "矩形 箱 列 box column block rectangular 選択",
    "editops_box_right": "矩形 箱 列 box column block rectangular 選択",
    "editops_multi_add_next": "複数カーソル 同じ語 次の一致 multi cursor next occurrence match 選択",
    "editops_box_cancel": "矩形 箱 解除 やめる cancel box escape",
    "editops_line_duplicate": "行 複製 コピー duplicate copy line",
    "editops_line_move_up": "行 移動 上 入れ替え move line up swap",
    "editops_line_move_down": "行 移動 下 入れ替え move line down swap",
    "editops_line_delete": "行 削除 消す delete remove line",
    "editops_line_comment": "コメント コメントアウト comment toggle",
    "editops_line_indent": "字下げ インデント indent tab",
    "editops_line_outdent": "字下げ インデント 戻す outdent unindent dedent",
    "editops_bracket_jump": "括弧 対応 かっこ 飛ぶ bracket parenthesis matching jump",
    "editops_edit_trim": "行末 空白 削除 末尾 trailing whitespace trim strip",
    "editops_howto": "矩形 箱 列 使い方 ヘルプ box column selection help how",
}


def ui_strings() -> tuple:
    """画面に出す英語の文の全部(対訳の表はこれと 1 対 1)。"""
    extra = (MENU_BOX, MENU_LINE, MENU_DISPLAY, ACT_HOWTO, ACT_RULERS, ACT_TRIM_ON_SAVE, MSG_NO_BRACKET,
             MSG_NO_OCCURRENCE, MSG_TRIMMED, MSG_BOX, HOWTO_TEXT, MSG_KEYS_CHANGED)
    seen, out = set(), []
    for s in tuple(b.title for b in KEYMAP) + extra:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return tuple(out)


_MOD_ORDER = ("Ctrl", "Shift", "Alt", "Meta")
_KEY_ALIASES = {"escape": "Esc", "esc": "Esc", "return": "Return", "enter": "Return", "del": "Del",
                "delete": "Del", "ins": "Ins", "insert": "Ins", "backtab": "Tab", "pgup": "PgUp",
                "pgdown": "PgDown", "pageup": "PgUp", "pagedown": "PgDown"}


def normalize_key(key: str) -> str:
    """キーの書き方をそろえる(``shift+ctrl+k`` → ``Ctrl+Shift+K``)。複数打鍵(``Ctrl+K, Ctrl+C``)は最初の 1 打。"""
    first = key.split(",")[0].strip()
    if not first:
        return ""
    if first.endswith("++"):
        parts, last = first[:-2].split("+"), "+"
    elif first == "+":
        parts, last = [], "+"
    else:
        *parts, last = first.split("+")
    mods = {p.strip().capitalize() for p in parts if p.strip()}
    if "Backtab" == last.strip().capitalize():
        mods.add("Shift")
    name = last.strip()
    name = _KEY_ALIASES.get(name.lower(), name.upper() if len(name) == 1 else name[:1].upper() + name[1:])
    return "+".join([m for m in _MOD_ORDER if m in mods] + [name])


def active_bindings(editor_has_comment: bool = False, include_box_only: bool = False,
                    keys: dict | None = None) -> list:
    """いま効かせる割り当て ``[(操作, キー)]``。``editor_has_comment`` ならエディタの Ctrl+/ を奪わない。

    ``keys`` は ``{操作: キーの並び}``(キーの設定で変えた今のキー)。載っていない操作は表の既定。
    """
    out = []
    for b in KEYMAP:
        if b.when == "no_own_comment" and editor_has_comment:
            continue
        if b.when == "box" and not include_box_only:
            continue
        current = b.keys if keys is None else keys.get(b.command, b.keys)
        out.extend((b.command, normalize_key(k)) for k in current)
    return out


def find_conflicts(bindings: Iterable, existing: Iterable) -> list:
    """当たり ``[(操作, キー, 相手)]``。``existing`` は ``(キー, 持ち主, エディタに効くか)`` の並び。"""
    table: dict = {}
    for key, owner, covers in existing:
        if covers:
            table.setdefault(normalize_key(key), []).append(owner)
    out = []
    for command, key in bindings:
        for owner in table.get(normalize_key(key), ()):
            out.append((command, normalize_key(key), owner))
    return out


# --------------------------------------------------------------------------- #
# 対訳
# --------------------------------------------------------------------------- #
#: 対訳を持つ言語(en は原文なので表には持たない)。
LANGS = ("en", "ja", "zh", "tw", "ko", "de")
_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_assets", "studio_editops_i18n.json")
_CACHE: dict = {}


def load_table(path: str | None = None) -> dict:
    """対訳の表 ``{英語の文: {言語: 訳}}``。読めない・壊れていれば ``ValueError``(黙って空にしない)。"""
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


def make_tr(lang: str | Callable = "en", table: dict | None = None, first: Callable | None = None) -> Callable:
    """``tr`` を作る。``lang`` は言語の符号か、呼ぶたびに今の言語を返す関数(言語の切り替えに追従する)。

    ``first`` があれば先にそれ(Studio の ``tr``)を試し、訳が無かった文だけこの部品の表で引く。
    表に無い文・未訳の言語は英語のまま返す。知らない言語の符号は ``ValueError``。
    """
    if not callable(lang) and lang not in LANGS:
        raise ValueError("言語は %s のどれか(来たのは %r)" % (" / ".join(LANGS), lang))

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
        tab = load_table() if table is None else table
        return tab.get(text, {}).get(code, text)

    return tr


def missing(table: dict | None = None) -> list:
    """``[(英語の文, 足りない言語)]``。画面に出す文の全部が 5 言語そろっていれば空。"""
    tab = load_table() if table is None else table
    out = []
    for key in ui_strings():
        row = tab.get(key)
        for lang in LANGS[1:]:
            if not isinstance(row, dict) or not str(row.get(lang, "")).strip():
                out.append((key, lang))
    return out
