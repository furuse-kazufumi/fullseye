"""Fullseye Script — a small HDevelop/HDevEngine-flavoured interpreter.

This is a *real* interpreted language (not the old flat (op, a, b) pipeline), so a
rule-based image-processing algorithm can actually be written: named variables,
real control flow that branches on *measured* values, per-object iteration, and
I/O. It is the language layer the Studio's Program window runs.

Design (increment I-2 — the language runs on fslib's typed L1 model):
  * Values are typed by their class, never guessed from pixel content:
      - control : number / string / tuple (Python float/int/str + a flat list
                  whose ``+`` is HALCON element-wise; ``[t1, t2]`` concatenates)
      - iconic  : ``fslib.FImage`` (pixels + declared value range + domain) /
                  ``fslib.Region`` / ``fslib.ObjectSet``.  The sort is *carried*
                  by the type (a threshold means the same thing on every frame),
                  and an iconic value has no truth value, so ``if (Region)`` and
                  ``if (Image = 0)`` are type errors rather than silent .any()s.
  * Vision builtins delegate to fslib operators (one implementation per op, with
    profile-selectable backends) — there is no second copy of the pixel work.
  * Statements: assignment ``Name := expr``, bare op/procedure calls, and control
    flow ``if/elseif/else/endif``, ``for V := a to b [by s] ... endfor``,
    ``while (c) ... endwhile``, ``repeat ... until (c)``, ``break``, ``continue``.
  * Expressions: numbers, 'strings', tuples ``[a, b, c]``, names, indexing
    ``t[i]``, calls ``f(a, b)``, arithmetic ``+ - * / %``, comparison
    ``< > <= >= = # (!=)``, logical ``and or not``, unary ``-``.
  * Vision vocabulary (``BUILTINS``) takes REAL parameters (a threshold is 0.4,
    not a normalized knob) so algorithms read naturally. Any registered fullseye
    op is *also* callable as ``op(Input, a, b)`` for the long tail.
  * ``run(...)`` walks the AST over an ``Env``; ``run(..., trace=cb)`` calls back
    after each top-level statement so the Studio can step and show live variables.

Syntax note: HDevelop's output-parameter call form (``read_image(Image, 'f')``)
needs a per-operator signature table; increment 1 uses the universal assignment
form ``Image := read_image('f')`` (C/C++-like), which the target accepts. The
control-flow / tuple / ``:=`` syntax is HDevelop-flavoured.
"""
from __future__ import annotations

import math
import os
import re

import numpy as np
from scipy import ndimage as ndi

import fslib
from fslib import FImage, ObjectSet, Region

#: Nesting cap shared by the parser (parentheses / unary chains / block depth)
#: and the evaluator (AST depth).  A script over this limit gets an FScriptError
#: with a line, never a bare RecursionError from the Python stack.
MAX_NESTING = 200


# --------------------------------------------------------------------------- #
# Errors + source positions
# --------------------------------------------------------------------------- #
class FScriptError(Exception):
    """A parse or run error carrying the 1-based source line."""

    def __init__(self, msg: str, line: int = 0):
        super().__init__(msg)
        self.msg = msg
        self.line = line

    def __str__(self):
        return "line %d: %s" % (self.line, self.msg) if self.line else self.msg


# --------------------------------------------------------------------------- #
# Lexer
# --------------------------------------------------------------------------- #
_KEYWORDS = {"if", "elseif", "else", "endif", "for", "to", "by", "endfor",
             "while", "endwhile", "repeat", "until", "break", "continue",
             "and", "or", "not", "true", "false"}
# multi-char operators first so ':=' / '<=' win over ':' / '<'
_OPS = [":=", "<=", ">=", "==", "!=", "<", ">", "=", "#", "+", "-", "*", "/",
        "%", "(", ")", "[", "]", ",", ":"]
_ASCII_DIGITS = "0123456789"
#: The numeral grammar: ``12`` / ``1.5`` / ``1.`` / ``.5`` / ``1e-3`` / ``2.5E+4``.
_NUM_RE = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


class Tok:
    __slots__ = ("kind", "val", "line")

    def __init__(self, kind, val, line):
        self.kind = kind      # 'num' 'str' 'name' 'kw' 'op' 'nl' 'eof'
        self.val = val
        self.line = line

    def __repr__(self):
        return "Tok(%s,%r,L%d)" % (self.kind, self.val, self.line)


def _at_line_start(src: str, i: int) -> bool:
    """True when only whitespace precedes ``src[i]`` on its line."""
    j = i - 1
    while j >= 0 and src[j] in " \t\r":
        j -= 1
    return j < 0 or src[j] == "\n"


def tokenize(src: str):
    toks = []
    line = 1
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "\n":
            toks.append(Tok("nl", "\n", line)); line += 1; i += 1; continue
        if c in " \t\r":
            i += 1; continue
        if c == "*" and _at_line_start(src, i):
            # HDevelop's comment marker is a *whole-line* '*'.  Mid-expression a
            # '*' is multiplication — treating it as a comment there silently
            # truncated the expression and returned a wrong value instead of an
            # error, which is the one failure mode an inspection language must
            # never have.
            while i < n and src[i] != "\n":
                i += 1
            continue
        if c == "#" and (i + 1 >= n or not src[i + 1].isdigit()):
            # '#' is HDevelop's "not equal"; only treat as a comment when it is
            # clearly a line comment (followed by space / letter, not a value).
            nxt = src[i + 1] if i + 1 < n else ""
            if nxt not in "" and not nxt.isdigit() and nxt not in "([":
                # ambiguous — keep as the '#' (not-equal) operator, handled below
                pass
        if c == "'":                                   # 'string'
            # A string literal lives on ONE line; the only escapes are \' and
            # \\ (any other backslash is literal, so Windows paths read as
            # written).  A line break inside the quotes is an unterminated
            # string — otherwise a missing quote silently swallowed the next
            # statement(s) into the literal.
            j = i + 1
            buf = []
            while j < n and src[j] != "'":
                if src[j] == "\n":
                    raise FScriptError("unterminated string (a string literal "
                                       "cannot span a line break)", line)
                if src[j] == "\\" and j + 1 < n and src[j + 1] in "'\\":
                    buf.append(src[j + 1]); j += 2; continue
                buf.append(src[j]); j += 1
            if j >= n:
                raise FScriptError("unterminated string", line)
            toks.append(Tok("str", "".join(buf), line)); i = j + 1; continue
        if c in _ASCII_DIGITS or (c == "." and i + 1 < n and src[i + 1] in _ASCII_DIGITS):
            # ASCII digits only: str.isdigit() also accepts '３' and '²', which
            # int() then either converted silently or blew up with a raw
            # ValueError.  The scanned text must match the numeral grammar
            # exactly, so '1.2.3' / '2e' / '1e5e3' are errors with a line.
            j = i
            while j < n and (src[j] in _ASCII_DIGITS or src[j] in ".eE" or
                             (src[j] in "+-" and j > i and src[j - 1] in "eE")):
                j += 1
            text = src[i:j]
            if not _NUM_RE.fullmatch(text):
                raise FScriptError("bad number literal %r" % text, line)
            val = float(text) if any(k in text for k in ".eE") else int(text)
            if isinstance(val, float) and not math.isfinite(val):
                raise FScriptError("number literal %r is out of range" % text, line)
            toks.append(Tok("num", val, line))
            i = j; continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            toks.append(Tok("kw" if word in _KEYWORDS else "name", word, line))
            i = j; continue
        for op in _OPS:
            if src.startswith(op, i):
                toks.append(Tok("op", op, line)); i += len(op); break
        else:
            raise FScriptError("unexpected character %r" % c, line)
    toks.append(Tok("eof", None, line))
    return toks


# --------------------------------------------------------------------------- #
# AST
# --------------------------------------------------------------------------- #
class Node:
    line = 0
    paren = False        # set when the expression was written inside ( ... )


class Num(Node):
    def __init__(self, v, line): self.v = v; self.line = line


class Str(Node):
    def __init__(self, v, line): self.v = v; self.line = line


class Bool(Node):
    def __init__(self, v, line): self.v = v; self.line = line


class Name(Node):
    def __init__(self, name, line): self.name = name; self.line = line


class TupleLit(Node):
    def __init__(self, items, line): self.items = items; self.line = line


class Index(Node):
    def __init__(self, base, idx, line): self.base = base; self.idx = idx; self.line = line


class Call(Node):
    def __init__(self, name, args, line): self.name = name; self.args = args; self.line = line


class BinOp(Node):
    def __init__(self, op, a, b, line): self.op = op; self.a = a; self.b = b; self.line = line


class UnOp(Node):
    def __init__(self, op, a, line): self.op = op; self.a = a; self.line = line


class Assign(Node):
    def __init__(self, target, expr, line): self.target = target; self.expr = expr; self.line = line


class ExprStmt(Node):
    def __init__(self, expr, line): self.expr = expr; self.line = line


class If(Node):
    def __init__(self, branches, orelse, line):
        self.branches = branches            # list of (cond, body)
        self.orelse = orelse                # body or None
        self.line = line


class For(Node):
    def __init__(self, var, start, stop, step, body, line):
        self.var = var; self.start = start; self.stop = stop
        self.step = step; self.body = body; self.line = line


class While(Node):
    def __init__(self, cond, body, line): self.cond = cond; self.body = body; self.line = line


class Repeat(Node):
    def __init__(self, body, cond, line): self.body = body; self.cond = cond; self.line = line


class Break(Node):
    def __init__(self, line): self.line = line


class Continue(Node):
    def __init__(self, line): self.line = line


# --------------------------------------------------------------------------- #
# Parser (recursive descent, Pratt-style expressions)
# --------------------------------------------------------------------------- #
class Parser:
    def __init__(self, toks):
        self.toks = toks
        self.i = 0
        self.loop_depth = 0      # > 0 while parsing a for/while/repeat body
        self.depth = 0           # nesting of blocks + expressions (MAX_NESTING)

    def _enter(self, line):
        self.depth += 1
        if self.depth > MAX_NESTING:
            raise FScriptError("nesting too deep (limit %d)" % MAX_NESTING, line)

    def _leave(self):
        self.depth -= 1

    def _peek(self):
        return self.toks[self.i]

    def _next(self):
        t = self.toks[self.i]; self.i += 1; return t

    def _at_op(self, val):
        t = self._peek()
        return t.kind == "op" and t.val == val

    def _at_kw(self, *words):
        t = self._peek()
        return t.kind == "kw" and t.val in words

    def _eat_newlines(self):
        while self._peek().kind == "nl":
            self.i += 1

    def _expect_op(self, val):
        t = self._next()
        if not (t.kind == "op" and t.val == val):
            raise FScriptError("expected '%s'" % val, t.line)
        return t

    def _expect_end_of_stmt(self):
        t = self._peek()
        if t.kind in ("nl", "eof"):
            if t.kind == "nl":
                self.i += 1
        else:
            raise FScriptError("unexpected %r after statement" % (t.val,), t.line)

    # -- program / block ---------------------------------------------------- #
    def parse_program(self):
        body = self._parse_block(())
        if self._peek().kind != "eof":
            raise FScriptError("unexpected %r" % (self._peek().val,), self._peek().line)
        return body

    def _parse_block(self, terminators):
        self._enter(self._peek().line)
        try:
            stmts = []
            while True:
                self._eat_newlines()
                t = self._peek()
                if t.kind == "eof":
                    break
                if t.kind == "kw" and t.val in terminators:
                    break
                stmts.append(self._parse_stmt())
            return stmts
        finally:
            self._leave()

    def _parse_loop_body(self, terminators):
        self.loop_depth += 1
        try:
            return self._parse_block(terminators)
        finally:
            self.loop_depth -= 1

    def _parse_stmt(self):
        t = self._peek()
        if t.kind == "kw":
            if t.val == "if":
                return self._parse_if()
            if t.val == "for":
                return self._parse_for()
            if t.val == "while":
                return self._parse_while()
            if t.val == "repeat":
                return self._parse_repeat()
            if t.val in ("break", "continue"):
                # Outside a loop there is nothing to break out of; the old
                # parser accepted it and the bare _Break exception escaped run().
                if self.loop_depth == 0:
                    raise FScriptError("'%s' outside loop" % t.val, t.line)
                self._next(); self._expect_end_of_stmt()
                return (Break if t.val == "break" else Continue)(t.line)
            raise FScriptError("unexpected keyword '%s'" % t.val, t.line)
        # assignment  Name := expr   or   Name[i] := expr   or bare expression
        if t.kind == "name":
            save = self.i
            target = self._parse_postfix()          # Name, Name[idx], or a call
            if self._at_op(":="):
                self._next()
                if not (isinstance(target, Name) or
                        (isinstance(target, Index) and isinstance(target.base, Name))):
                    raise FScriptError("assignment target must be a name or Name[i]", t.line)
                expr = self._parse_expr()
                self._expect_end_of_stmt()
                return Assign(target, expr, t.line)
            self.i = save                            # not an assignment -> expression stmt
        expr = self._parse_expr()
        self._expect_end_of_stmt()
        return ExprStmt(expr, expr.line)

    def _parse_if(self):
        line = self._next().line                     # 'if'
        cond = self._parse_cond()
        body = self._parse_block(("elseif", "else", "endif"))
        branches = [(cond, body)]
        orelse = None
        while self._at_kw("elseif"):
            self._next()
            c = self._parse_cond()
            b = self._parse_block(("elseif", "else", "endif"))
            branches.append((c, b))
        if self._at_kw("else"):
            self._next()
            orelse = self._parse_block(("endif",))
        if not self._at_kw("endif"):
            raise FScriptError("missing 'endif'", line)
        self._next(); self._expect_end_of_stmt()
        return If(branches, orelse, line)

    def _parse_cond(self):
        """The header condition of if/elseif/while/until, up to the end of the
        line.

        HDevelop writes ``if (cond)``; the parentheses are an ordinary grouping,
        so ``if (X = 1) or (Y = 1)`` is one condition.  A parenthesised header
        may only continue with ``and`` / ``or`` — ``if (X = 1) -1`` used to parse
        the ``-1`` as the first body statement (the condition silently lost
        nothing, but the body gained a statement the author never wrote), and
        as an arithmetic continuation it would compute ``true - 1 = 0``.  Both
        are now "unexpected after statement".
        """
        if self._at_op("("):
            t = self._peek()
            left = self._parse_primary()             # the ( ... ) group
            while self._at_kw("and", "or"):
                op = self._next().val
                right = self._parse_expr(self._BINPREC[op] + 1)
                left = BinOp(op, left, right, t.line)
            cond = left
        else:
            cond = self._parse_expr()
        self._expect_end_of_stmt()
        return cond

    def _parse_for(self):
        line = self._next().line                     # 'for'
        var = self._next()
        if var.kind != "name":
            raise FScriptError("'for' needs a loop variable", line)
        self._expect_op(":=")
        start = self._parse_expr()
        if not self._at_kw("to"):
            raise FScriptError("'for' needs 'to'", line)
        self._next()
        stop = self._parse_expr()
        step = None
        if self._at_kw("by"):
            self._next(); step = self._parse_expr()
        self._expect_end_of_stmt()                   # the header ends the line
        body = self._parse_loop_body(("endfor",))
        if not self._at_kw("endfor"):
            raise FScriptError("missing 'endfor'", line)
        self._next(); self._expect_end_of_stmt()
        return For(var.val, start, stop, step, body, line)

    def _parse_while(self):
        line = self._next().line
        cond = self._parse_cond()
        body = self._parse_loop_body(("endwhile",))
        if not self._at_kw("endwhile"):
            raise FScriptError("missing 'endwhile'", line)
        self._next(); self._expect_end_of_stmt()
        return While(cond, body, line)

    def _parse_repeat(self):
        line = self._next().line
        body = self._parse_loop_body(("until",))
        if not self._at_kw("until"):
            raise FScriptError("missing 'until'", line)
        self._next()
        cond = self._parse_cond()
        return Repeat(body, cond, line)

    # -- expressions (precedence climbing) ---------------------------------- #
    _BINPREC = {"or": 1, "and": 2, "=": 3, "==": 3, "!=": 3, "#": 3, "<": 3,
                ">": 3, "<=": 3, ">=": 3, "+": 4, "-": 4, "*": 5, "/": 5, "%": 5}

    _COMPARE = frozenset(("=", "==", "!=", "#", "<", ">", "<=", ">="))
    _NOT_PREC = 3                       # 'not' binds looser than comparison (like Python)

    def _parse_expr(self, min_prec=0):
        self._enter(self._peek().line)
        try:
            return self._parse_expr_inner(min_prec)
        finally:
            self._leave()

    def _parse_expr_inner(self, min_prec):
        # 'not' is a low-precedence prefix (looser than comparison): `not a = b`
        # is `not (a = b)`, not `(not a) = b`.  Unary '-' stays tight (_parse_unary).
        t0 = self._peek()
        if t0.kind == "kw" and t0.val == "not" and min_prec <= self._NOT_PREC:
            self._next()
            left = UnOp("not", self._parse_expr(self._NOT_PREC), t0.line)
        else:
            left = self._parse_unary()
        while True:
            t = self._peek()
            op = None
            if t.kind == "op" and t.val in self._BINPREC:
                op = t.val
            elif t.kind == "kw" and t.val in ("and", "or"):
                op = t.val
            if op is None or self._BINPREC[op] < min_prec:
                break
            # Comparisons do not chain: `0 <= X <= 10` would silently parse as
            # `(0 <= X) <= 10` and return a wrong boolean — forbidden by the
            # language's no-silent-wrong rule.  Require parentheses: a
            # comparison the author wrapped in ( ... ) is an explicit operand,
            # so `(X > 3) = true` is fine.
            if (op in self._COMPARE and isinstance(left, BinOp)
                    and left.op in self._COMPARE and not left.paren):
                raise FScriptError("chained comparison '%s' is ambiguous; "
                                   "parenthesise (e.g. (0 <= X) and (X <= 10))" % op, t.line)
            self._next()
            right = self._parse_expr(self._BINPREC[op] + 1)
            left = BinOp(op, left, right, t.line)
        return left

    def _parse_unary(self):
        t = self._peek()
        if t.kind == "op" and t.val == "-":
            self._next()
            self._enter(t.line)
            try:
                return UnOp(t.val, self._parse_unary(), t.line)
            finally:
                self._leave()
        return self._parse_postfix()

    def _parse_postfix(self):
        node = self._parse_primary()
        while self._at_op("["):
            lb = self._next().line
            idx = self._parse_expr()
            self._expect_op("]")
            node = Index(node, idx, lb)
        return node

    def _parse_primary(self):
        t = self._next()
        if t.kind == "num":
            return Num(t.val, t.line)
        if t.kind == "str":
            return Str(t.val, t.line)
        if t.kind == "kw" and t.val in ("true", "false"):
            return Bool(t.val == "true", t.line)
        if t.kind == "op" and t.val == "(":
            e = self._parse_expr()
            self._expect_op(")")
            e.paren = True                           # remembered for the chain check
            return e
        if t.kind == "op" and t.val == "[":
            items = []
            if not self._at_op("]"):
                items.append(self._parse_expr())
                while self._at_op(","):
                    self._next(); items.append(self._parse_expr())
            self._expect_op("]")
            return TupleLit(items, t.line)
        if t.kind == "name":
            if self._at_op("("):                     # function / op call
                self._next()
                args = []
                if not self._at_op(")"):
                    args.append(self._parse_expr())
                    while self._at_op(","):
                        self._next(); args.append(self._parse_expr())
                self._expect_op(")")
                return Call(t.val, args, t.line)
            return Name(t.val, t.line)
        raise FScriptError("unexpected %r" % (t.val,), t.line)


def parse(src: str):
    try:
        return Parser(tokenize(src)).parse_program()
    except RecursionError:                           # belt and braces behind MAX_NESTING
        raise FScriptError("nesting too deep (limit %d)" % MAX_NESTING)


#: fscript builtins that dispatch to a fslib registry op — used by the Runtime
#: load-time readiness check to map a recipe's calls onto backends to verify.
#: Only builtins that actually go through ``fslib._dispatch`` belong here:
#: ``area_center`` is intentionally absent (``_b_area_center`` computes the
#: centroid from ``Region.runs()`` in pure numpy and never dispatches, so mapping
#: it to ``measure_all`` would wrongly demand a cv2 backend on a cv2-less line).
FSLIB_OP_FOR_BUILTIN = {
    "gauss_image": "gauss", "threshold": "threshold", "connection": "connection",
    "select_shape": "measure_all",
}


def used_op_names(program) -> set:
    """Every function/operator name called anywhere in a parsed program.

    Walks the AST collecting ``Call`` names so a Runtime can check, before it
    becomes READY, that every operator a recipe uses has a working backend.
    """
    names: set = set()
    stack = [program]
    _CHILDREN = ("items", "base", "idx", "a", "b", "args", "expr", "target",
                 "start", "stop", "step", "cond", "body", "orelse", "branches")
    while stack:
        node = stack.pop()
        if node is None:
            continue
        if isinstance(node, (list, tuple)):
            stack.extend(node)
            continue
        if isinstance(node, Call):
            names.add(node.name)
        for attr in _CHILDREN:
            child = getattr(node, attr, None)
            if child is not None:
                stack.append(child)
    return names


# --------------------------------------------------------------------------- #
# Values / environment
# --------------------------------------------------------------------------- #
def value_kind(v) -> str:
    """Classify a value for the Variable window: 'image' / 'region' / 'object'
    / 'control'.

    The sort is read from the *type*, never guessed from pixel content.  A grey
    image that happens to be binary is still an image (defect 5); the previous
    ``np.unique(v).size <= 2`` heuristic silently reclassified it as a region.
    """
    if isinstance(v, FImage):
        return "image"
    if isinstance(v, Region):
        return "region"
    if isinstance(v, ObjectSet):
        return "object"
    if isinstance(v, np.ndarray):
        # A raw array only reaches here before it is wrapped (e.g. a value handed
        # to value_kind directly).  Classify by declared dtype, not by how many
        # distinct values it happens to contain.
        return "region" if v.dtype == bool else "image"
    return "control"


class Env:
    """Variable environment + call context (built-ins, registry ops, base dir)."""

    def __init__(self, base_dir=None):
        self.vars = {}
        self.base_dir = base_dir
        self.trace = None

    def kinds(self):
        return {k: value_kind(v) for k, v in self.vars.items()}


class _Break(Exception):
    def __init__(self, line=0):
        super().__init__(); self.line = line


class _Continue(Exception):
    def __init__(self, line=0):
        super().__init__(); self.line = line


def _scalar(v):
    """HALCON: a scalar is a length-1 tuple.  Unwrap ``[x]`` to ``x``."""
    if isinstance(v, list) and len(v) == 1:
        return v[0]
    return v


def _as_number(v, what, line=0):
    """A user value that must be a number (int/float; a length-1 tuple unwraps).

    Every ``int(x)`` / ``float(x)`` on a script value used to be a raw Python
    coercion: ``'x'`` blew up with a bare ValueError, ``[0.5]`` with a TypeError,
    and ``'12'`` was quietly accepted.  The language must say what it wanted.
    """
    v = _scalar(v)
    if isinstance(v, bool) or isinstance(v, (int, float, np.integer, np.floating)):
        return v
    raise FScriptError("%s must be a number, got %s" % (what, _describe(v)), line)


def _as_index(v, n, what, line=0):
    """Validate a tuple/string index: integral (a float only if it is a whole
    number), non-negative, and inside ``[0, n)``.  Never a raw ValueError."""
    v = _scalar(v)
    if isinstance(v, bool):
        raise FScriptError("%s must be an integer, got a boolean" % what, line)
    if isinstance(v, (float, np.floating)):
        if not float(v).is_integer():
            raise FScriptError("%s must be an integer, got %r" % (what, v), line)
        v = int(v)
    if not isinstance(v, (int, np.integer)):
        raise FScriptError("%s must be an integer, got %s" % (what, _describe(v)), line)
    v = int(v)
    if v < 0:
        raise FScriptError("%s must not be negative (got %d); tuples are 0-based, "
                           "there is no negative indexing" % (what, v), line)
    if v >= n:
        raise FScriptError("%s %d out of range (length %d)" % (what, v, n), line)
    return v


def _describe(v) -> str:
    if isinstance(v, str):
        return "string %r" % v
    if isinstance(v, list):
        return "tuple of length %d" % len(v)
    return type(v).__name__


# --------------------------------------------------------------------------- #
# Interpreter
# --------------------------------------------------------------------------- #
class Interp:
    def __init__(self, env: Env, max_steps=2_000_000):
        self.env = env
        self.steps = 0
        self.max_steps = max_steps
        self.depth = 0                  # evaluator nesting (MAX_NESTING)

    def run_program(self, body):
        """Run a whole program.  The parser already rejects ``break`` /
        ``continue`` outside a loop; this is the defensive net for an AST that
        was built by hand, so the private signal never escapes as a bare
        exception."""
        try:
            return self.run(body)
        except _Break as e:
            raise FScriptError("'break' outside loop", e.line)
        except _Continue as e:
            raise FScriptError("'continue' outside loop", e.line)
        except RecursionError:
            raise FScriptError("nesting too deep (limit %d)" % MAX_NESTING)

    def run(self, body):
        for stmt in body:
            self._exec(stmt)
            if isinstance(stmt, (Assign, ExprStmt)) and self.env.trace:
                self.env.trace(stmt.line, self.env)
        return self.env

    # -- statements --------------------------------------------------------- #
    def _exec(self, node):
        self.steps += 1
        if self.steps > self.max_steps:
            raise FScriptError("step limit exceeded (possible infinite loop)", getattr(node, "line", 0))
        m = getattr(self, "_st_" + type(node).__name__, None)
        if m is None:
            raise FScriptError("cannot execute %s" % type(node).__name__, getattr(node, "line", 0))
        return m(node)

    def _st_Assign(self, node):
        val = self._eval(node.expr)
        if isinstance(node.target, Name):
            # Tuples are values, not references: `B := A` copies, so a later
            # `B[0] := 9` cannot reach into A (or into a seeded input).
            self.env.vars[node.target.name] = list(val) if isinstance(val, list) else val
        elif isinstance(node.target, Index) and isinstance(node.target.base, Name):
            name = node.target.base.name
            if name not in self.env.vars:
                raise FScriptError("undefined variable '%s'" % name, node.line)
            base = self.env.vars[name]
            if not isinstance(base, list):
                raise FScriptError("cannot index-assign into %s '%s' (only a tuple)"
                                   % (_describe(base), name), node.line)
            if isinstance(val, list):
                raise FScriptError("Name[i] := expr needs a scalar (tuples are flat); "
                                   "got a tuple of length %d" % len(val), node.line)
            i = _as_index(self._eval(node.target.idx), len(base), "index", node.line)
            base[i] = val
        else:
            raise FScriptError("invalid assignment target", node.line)

    def _st_ExprStmt(self, node):
        self._eval(node.expr)

    def _st_If(self, node):
        for cond, body in node.branches:
            if _truth(self._eval(cond), cond.line or node.line):
                self.run(body)
                return
        if node.orelse is not None:
            self.run(node.orelse)

    def _tick(self, line):
        # Count each loop iteration so an EMPTY-body loop (whose body runs zero
        # statements, so _exec never increments) is still bounded — otherwise
        # `while (1 = 1)\nendwhile` hangs forever, bypassing the step limit.
        self.steps += 1
        if self.steps > self.max_steps:
            raise FScriptError("step limit exceeded (possible infinite loop)", line)

    def _st_For(self, node):
        start = _as_number(self._eval(node.start), "'for' start", node.line)
        stop = _as_number(self._eval(node.stop), "'for' stop", node.line)
        step = (_as_number(self._eval(node.step), "'for' step", node.line)
                if node.step is not None else 1)
        if step == 0:
            raise FScriptError("'for' step must not be 0", node.line)
        i = start
        while (step > 0 and i <= stop) or (step < 0 and i >= stop):
            self._tick(node.line)
            self.env.vars[node.var] = i
            try:
                self.run(node.body)
            except _Break:
                break
            except _Continue:
                pass
            i += step

    def _st_While(self, node):
        while _truth(self._eval(node.cond), node.cond.line or node.line):
            self._tick(node.line)
            try:
                self.run(node.body)
            except _Break:
                break
            except _Continue:
                continue

    def _st_Repeat(self, node):
        while True:
            self._tick(node.line)
            try:
                self.run(node.body)
            except _Break:
                break
            except _Continue:
                pass
            if _truth(self._eval(node.cond), node.cond.line or node.line):
                break

    def _st_Break(self, node):
        raise _Break(node.line)

    def _st_Continue(self, node):
        raise _Continue(node.line)

    # -- expressions -------------------------------------------------------- #
    def _eval(self, node):
        m = getattr(self, "_ev_" + type(node).__name__, None)
        if m is None:
            raise FScriptError("cannot evaluate %s" % type(node).__name__, getattr(node, "line", 0))
        # A left-deep chain (`1+1+...+1`, thousands of terms) is shallow to
        # parse but deep to evaluate; cap it here so the answer is an
        # FScriptError with a line, not a RecursionError.
        self.depth += 1
        try:
            if self.depth > MAX_NESTING:
                raise FScriptError("expression nesting too deep (limit %d)" % MAX_NESTING,
                                   getattr(node, "line", 0))
            return m(node)
        finally:
            self.depth -= 1

    def _ev_Num(self, n): return n.v

    def _ev_Str(self, n): return n.v

    def _ev_Bool(self, n): return n.v

    def _ev_TupleLit(self, n):
        # HALCON's ``[...]`` builds a tuple by *flattening*: ``[Rows, x]`` appends
        # x to the tuple Rows.  Concatenation therefore has its own syntax,
        # leaving ``+`` free to be element-wise (defect 3).
        out = []
        for x in n.items:
            v = self._eval(x)
            if isinstance(v, list):
                out.extend(v)
            else:
                out.append(v)
        return out

    def _ev_Name(self, n):
        if n.name in self.env.vars:
            return self.env.vars[n.name]
        raise FScriptError("undefined variable '%s'" % n.name, n.line)

    def _ev_Index(self, n):
        base = self._eval(n.base)
        idx = self._eval(n.idx)
        if not isinstance(base, (list, str)):
            raise FScriptError("cannot index %s (only a tuple or a string)"
                               % _describe(base), n.line)
        return base[_as_index(idx, len(base), "index", n.line)]

    def _ev_UnOp(self, n):
        v = self._eval(n.a)
        if n.op == "-":
            if isinstance(v, list):                   # element-wise, like HALCON
                return [-_as_number(x, "operand of unary '-'", n.line) for x in v]
            return -_as_number(v, "operand of unary '-'", n.line)
        if n.op == "not":
            return not _truth(v, n.line)
        raise FScriptError("bad unary op %s" % n.op, n.line)

    def _ev_BinOp(self, n):
        if n.op in ("and", "or"):                    # short-circuit
            a = self._eval(n.a)
            if n.op == "and":
                return _truth(a, n.line) and _truth(self._eval(n.b), n.line)
            return _truth(a, n.line) or _truth(self._eval(n.b), n.line)
        a, b = self._eval(n.a), self._eval(n.b)
        if n.op in _COMPARE_OPS and (isinstance(a, _ICONIC) or isinstance(b, _ICONIC)):
            # Defect 5: comparing an iconic value against a scalar yields an array,
            # which a condition then collapses with .any() — so `if (Image = 0)`
            # read as "any pixel is 0".  Element-wise iconic comparison must be
            # reduced explicitly, never used as a predicate.
            raise FScriptError(
                "cannot compare an iconic value with '%s'; reduce it first "
                "(e.g. area(R), count_obj(Objects), mean_gray(Image))" % n.op, n.line)
        if n.op in ("+", "-", "*", "/", "%") and (isinstance(a, _ICONIC) or isinstance(b, _ICONIC)):
            # Arithmetic on an iconic value (image/region/raw array) is not the
            # language's business — call an operator.  Previously only '+' was
            # guarded, so `Image * 0.0` on a raw 3-channel array slipped through
            # as silent numpy pixel math.
            raise FScriptError("cannot do arithmetic ('%s') on iconic values in the "
                               "language; call an operator instead" % n.op, n.line)
        try:
            if n.op in _ARITH_OPS:
                fn = _ARITH_OPS[n.op]
                if isinstance(a, list) or isinstance(b, list):
                    return _tuple_op(fn, n.op, a, b, n.line)   # HALCON element-wise
                return _scalar_op(fn, n.op, a, b, n.line)
            # comparisons: a length-1 tuple is its scalar; whole tuples compare
            # as tuples (equal length + equal elements), never lexicographically
            # against a scalar.
            a, b = _scalar(a), _scalar(b)
            if isinstance(a, list) != isinstance(b, list) and n.op not in ("=", "==", "!=", "#"):
                raise FScriptError("cannot compare a tuple of length %d with a scalar using '%s'"
                                   % (len(a) if isinstance(a, list) else len(b), n.op), n.line)
            if n.op in ("=", "=="): return a == b
            if n.op in ("!=", "#"): return a != b
            if n.op == "<": return a < b
            if n.op == ">": return a > b
            if n.op == "<=": return a <= b
            if n.op == ">=": return a >= b
        except FScriptError as e:
            if not e.line:
                e.line = n.line
            raise
        except (TypeError, ValueError, ZeroDivisionError) as e:
            raise FScriptError("bad operation %s: %s" % (n.op, e), n.line)
        raise FScriptError("bad binary op %s" % n.op, n.line)

    def _ev_Call(self, n):
        args = [self._eval(a) for a in n.args]
        fn = BUILTINS.get(n.name)
        try:
            if fn is not None:
                try:
                    return fn(self.env, *args)
                except FScriptError:
                    raise
                except Exception as e:                # surface a clean line-tagged error
                    raise FScriptError("%s: %s" % (n.name, e), n.line)
            # long-tail: any registered fullseye op, called as op(Input, a=.5, b=.5)
            op_out = _call_registry_op(n.name, args)
        except FScriptError as e:
            if not e.line:                            # builtins raise without a line
                e.line = n.line
            raise
        if op_out is not _NO_OP:
            return op_out
        raise FScriptError("unknown function/operator '%s'" % n.name, n.line)


#: The sorts that have no truth value and cannot be compared element-wise as a
#: language predicate.  ``np.ndarray`` is included so a raw array that slips
#: through (e.g. a 3-channel image awaiting to_gray) is treated the same way.
_ICONIC = (FImage, Region, ObjectSet, np.ndarray)
_COMPARE_OPS = ("=", "==", "!=", "#", "<", ">", "<=", ">=")


def _truth(v, line=0) -> bool:
    if isinstance(v, _ICONIC):
        # Defect 4: an iconic value used as a condition was silently coerced with
        # ndarray.any().  The language forbids it — a condition must be a scalar
        # predicate, written explicitly.
        raise FScriptError(
            "an iconic value has no truth value in a condition; write an explicit "
            "predicate such as count_obj(Objects) > 0, area(R) > 0 or "
            "mean_gray(Image) > 0.5", line)
    if isinstance(v, list):
        # HALCON: a scalar IS a length-1 tuple, so `if ([0])` is `if (0)`.  Any
        # other length has no single truth value (the old `len(v) > 0` made
        # `if ([0])` true and `not [0]` false).
        if len(v) == 1:
            return _truth(v[0], line)
        raise FScriptError("a tuple of length %d has no truth value in a condition; "
                           "test one element or a reduction" % len(v), line)
    return bool(v)


_ARITH_OPS = {
    "+": lambda x, y: x + y, "-": lambda x, y: x - y, "*": lambda x, y: x * y,
    "/": lambda x, y: x / y, "%": lambda x, y: x % y,
}


def _scalar_op(fn, op, x, y, line=0):
    """One arithmetic step on two scalars.  ``str + str`` concatenates (HALCON);
    every other string arithmetic is an error — Python's ``'ab' * 3`` repetition
    is not a language feature and used to slip through unchanged."""
    if isinstance(x, str) or isinstance(y, str):
        if op == "+" and isinstance(x, str) and isinstance(y, str):
            return x + y
        raise FScriptError("cannot apply '%s' to %s and %s (only string + string "
                           "concatenates)" % (op, _describe(x), _describe(y)), line)
    return fn(x, y)


def _tuple_op(fn, op, a, b, line=0):
    """HALCON tuple arithmetic — element-wise with scalar broadcast, for every
    one of ``+ - * / %``.

    Defect 3: ``+`` concatenated (Python list ``+``); likewise ``[1,2] * 2`` was
    Python repetition ``[1,2,1,2]`` and ``- / %`` raised raw TypeErrors.  HALCON
    is element-wise for all of them; concatenation is the ``[t1, t2]`` literal.
    """
    la = a if isinstance(a, list) else [a]
    lb = b if isinstance(b, list) else [b]
    if len(la) == 1 and len(lb) != 1:
        la = la * len(lb)
    elif len(lb) == 1 and len(la) != 1:
        lb = lb * len(la)
    if len(la) != len(lb):
        raise FScriptError(
            "tuple '%s' needs equal lengths or a scalar (HALCON is element-wise); "
            "use [t1, t2] to concatenate" % op, line)
    return [_scalar_op(fn, op, x, y, line) for x, y in zip(la, lb)]


# --------------------------------------------------------------------------- #
# Built-in vision vocabulary (REAL parameters)
#
# Iconic values are the typed L1 sorts (FImage / Region / ObjectSet from
# ``fslib``); the pixel operators delegate to ``fslib`` so there is one
# implementation of each operator, not a second copy here.  What this layer adds
# is the *language* vocabulary and the coercion at the boundary — the type model
# is fslib's.
# --------------------------------------------------------------------------- #
def _range_for_dtype(dt) -> tuple[float, float]:
    """The declared value range for a raw array — read from the dtype (the sensor
    convention), never from the pixel content (defect 2)."""
    dt = np.dtype(dt)
    if dt.kind in "ui":
        return (0.0, float(np.iinfo(dt).max))
    return (0.0, 1.0)                       # float: the 0..1 sensor convention


def _wrap_array_as_image(a) -> FImage:
    a = np.asarray(a)
    if a.ndim != 2:
        raise FScriptError("expected a 2-D image; call to_gray first (got %dD)" % a.ndim)
    if a.dtype == bool:
        raise FScriptError("a boolean array is a region, not an image")
    return FImage(a, value_range=_range_for_dtype(a.dtype))


def _as_fimage(x) -> FImage:
    if isinstance(x, FImage):
        return x
    if isinstance(x, np.ndarray):
        return _wrap_array_as_image(x)
    raise FScriptError("expected an image, got %s" % type(x).__name__)


def _as_region(x) -> Region:
    if isinstance(x, Region):
        return x
    if isinstance(x, np.ndarray) and x.ndim == 2:
        return Region(x)
    raise FScriptError("expected a region, got %s (call connection/threshold first)"
                       % type(x).__name__)


def _as_objectset(x) -> ObjectSet:
    if isinstance(x, ObjectSet):
        return x
    raise FScriptError("expected an object set; call connection first, got %s"
                       % type(x).__name__)


def _region_mask(reg: Region) -> np.ndarray:
    """Rebuild a dense mask from a Region's public run view — no private storage
    is touched, so this keeps working if Region moves to run-length encoding."""
    m = np.zeros(reg.shape, dtype=bool)
    for r, cb, ce in reg.runs():
        m[r, cb:ce] = True
    return m


def _region_area_center(reg: Region):
    """HALCON ``area_center`` -> [area, row, column], computed from the run view."""
    runs = reg.runs()
    if runs.shape[0] == 0:
        return [0.0, 0.0, 0.0]
    rows = runs[:, 0].astype(np.float64)
    cb = runs[:, 1].astype(np.float64)
    ce = runs[:, 2].astype(np.float64)          # exclusive
    w = ce - cb                                 # run widths
    area = float(w.sum())
    row_c = float((rows * w).sum() / area)
    col_c = float((((cb + ce - 1) * 0.5) * w).sum() / area)   # mean column over runs
    return [area, row_c, col_c]


#: Builtins that touch the file system.  They are part of the vetted vocabulary
#: for the Studio, but a judging recipe under the *industrial* profile must not
#: read files in the cycle (docs/FSCRIPT_DECISION.md 3.1 R4: no import / file
#: search / network inside a cycle) — fsruntime refuses them at load.
CYCLE_UNSAFE_BUILTINS = frozenset({"read_image"})


def _resolve_read_path(base_dir, p: str) -> str:
    """Confine a ``read_image`` path to ``base_dir``.

    Relative paths resolve against ``base_dir``; absolute paths are accepted only
    when they lie inside it.  ``..`` is resolved before the check, so
    ``'../../x.png'`` cannot climb out.  Without a ``base_dir`` there is nothing
    to confine to and the path is used as written (the caller opted out).
    """
    if not base_dir:
        return p
    root = os.path.realpath(base_dir)
    cand = os.path.realpath(p if os.path.isabs(p) else os.path.join(root, p))
    try:
        inside = os.path.commonpath([root, cand]) == root
    except ValueError:                                # different drives on Windows
        inside = False
    if not inside:
        raise FScriptError("read_image: path %r is outside the script's base "
                           "directory %r" % (p, base_dir))
    return cand


def _b_read_image(env, path):
    if not isinstance(path, str):
        raise FScriptError("read_image: path must be a string, got %s" % _describe(path))
    p = _resolve_read_path(env.base_dir, path)
    import imgio
    return _seed_value(imgio.load(p))


def _b_rgb1_to_gray(env, img):
    if isinstance(img, FImage):
        return img
    a = np.asarray(img, dtype=np.float64)
    if a.ndim == 3:
        a = a[..., :3].mean(axis=2)
    return FImage(a, value_range=(0.0, 1.0))


def _b_gauss_image(env, img, sigma):
    sigma = float(_as_number(sigma, "gauss_image sigma"))
    if not (sigma > 0):
        raise FScriptError("gauss_image sigma must be > 0, got %r" % sigma)
    return fslib.gauss(_as_fimage(img), sigma)


def _radius(r, what) -> int:
    """A morphology/filter radius: a non-negative whole number.  ``0`` is the
    identity; a negative or fractional radius is an error (``max(1, int(r))``
    used to turn -3, 0 and 0.4 all into 1 without a word)."""
    r = _as_number(r, what)
    if isinstance(r, (float, np.floating)):
        if not float(r).is_integer():
            raise FScriptError("%s must be a whole number of pixels, got %r" % (what, r))
        r = int(r)
    r = int(r)
    if r < 0:
        raise FScriptError("%s must not be negative, got %d" % (what, r))
    return r


def _b_mean_image(env, img, radius):
    img = _as_fimage(img)
    k = 2 * _radius(radius, "mean_image radius") + 1
    return img.with_pixels(ndi.uniform_filter(img.pixels.astype(np.float64), k))


def _b_invert_image(env, img):
    img = _as_fimage(img)
    lo, hi = img.value_range
    return img.with_pixels(lo + hi - img.pixels.astype(np.float64))    # reflect in range


def _b_threshold(env, img, lo, hi):
    """``threshold(Image, lo, hi)`` in the language's grey unit: a fraction of
    the image's declared value range (0 = range low, 1 = range high), the same
    unit ``mean_gray`` / ``min_gray`` / ``max_gray`` report in — so
    ``threshold(Image, mean_gray(Image), max_gray(Image))`` means the same on
    an 8-bit frame as on a float one."""
    return fslib.threshold(_as_fimage(img),
                           float(_as_number(lo, "threshold lo")),
                           float(_as_number(hi, "threshold hi")))


def _b_binary_threshold(env, img):
    """Otsu auto-threshold -> region (bright objects).

    Otsu is *meant* to adapt to the frame, so it derives its threshold from the
    histogram — but it does so on pixels normalised by the DECLARED range, not by
    the running maximum, so an out-of-range hot pixel does not rescale it."""
    img = _as_fimage(img)
    lo, hi = img.value_range
    a = np.clip((img.pixels.astype(np.float64) - lo) / (hi - lo), 0.0, 1.0)
    hist, _ = np.histogram(a, bins=256, range=(0.0, 1.0))
    p = hist.astype(np.float64) / max(1, hist.sum())
    omega = np.cumsum(p)
    mu = np.cumsum(p * (np.arange(256) + 0.5) / 256.0)
    mu_t = mu[-1]
    denom = omega * (1.0 - omega)
    denom[denom == 0] = 1e-12
    sigma_b = (mu_t * omega - mu) ** 2 / denom
    t = (np.argmax(sigma_b) + 0.5) / 256.0
    return Region(a >= t)


def _b_dilation(env, region, radius):
    from scipy.ndimage import binary_dilation, generate_binary_structure, iterate_structure
    reg = _as_region(region)
    r = _radius(radius, "dilation radius")
    if r == 0:
        return reg                                    # identity
    st = iterate_structure(generate_binary_structure(2, 1), r)
    return Region(binary_dilation(_region_mask(reg), st))


def _b_erosion(env, region, radius):
    from scipy.ndimage import binary_erosion, generate_binary_structure, iterate_structure
    reg = _as_region(region)
    r = _radius(radius, "erosion radius")
    if r == 0:
        return reg                                    # identity
    st = iterate_structure(generate_binary_structure(2, 1), r)
    return Region(binary_erosion(_region_mask(reg), st))


def _b_connection(env, region):
    """Split a region into its connected components — the ObjectSet a for-loop
    iterates and select_shape filters (label image + ids, no mask per blob)."""
    return fslib.connection(_as_region(region))


def _b_count_obj(env, objects):
    return len(_as_objectset(objects))


def _b_select_obj(env, objects, index):
    objs = _as_objectset(objects)
    i = _as_index(index, len(objs), "select_obj index")
    try:
        return objs.region(i)
    except IndexError as e:
        raise FScriptError(str(e))


def _b_area_center(env, region):
    return _region_area_center(_as_region(region))


def _b_area(env, region):
    return float(_as_region(region).area())


def _b_select_shape(env, objects, feature, vmin, vmax):
    try:
        if not isinstance(feature, str):
            raise FScriptError("select_shape feature must be a string, got %s"
                               % _describe(feature))
        return fslib.select_shape(_as_objectset(objects), feature,
                                  float(_as_number(vmin, "select_shape min")),
                                  float(_as_number(vmax, "select_shape max")))
    except fslib.FsTypeError as e:
        raise FScriptError(str(e))


def _b_union_object(env, objects):
    objs = _as_objectset(objects)
    return Region(np.isin(objs.labels, objs.ids))


def _relative(img: FImage, value) -> float:
    """A pixel value in the language's grey unit: fraction of the declared range.

    ``threshold`` has always taken its bounds this way (``FImage.absolute``); the
    statistics used to report raw pixel units instead, so on an 8-bit frame
    ``threshold(Image, mean_gray(Image), max_gray(Image))`` compared 50 against
    a 0..1 scale and silently selected nothing.  One unit for both now."""
    lo, hi = img.value_range
    return (float(value) - lo) / (hi - lo)


def _b_mean_gray(env, img):
    img = _as_fimage(img)
    return _relative(img, img.pixels.mean())


def _b_max_gray(env, img):
    img = _as_fimage(img)
    return _relative(img, img.pixels.max())


def _b_min_gray(env, img):
    img = _as_fimage(img)
    return _relative(img, img.pixels.min())


def _b_region_to_image(env, region):
    return FImage(_region_mask(_as_region(region)).astype(np.float64),
                  value_range=(0.0, 1.0))


# name -> (env, *args) callable
BUILTINS = {
    "read_image": _b_read_image,
    "rgb1_to_gray": _b_rgb1_to_gray, "to_gray": _b_rgb1_to_gray,
    "gauss_image": _b_gauss_image, "mean_image": _b_mean_image,
    "invert_image": _b_invert_image,
    "threshold": _b_threshold, "binary_threshold": _b_binary_threshold,
    "dilation": _b_dilation, "erosion": _b_erosion,
    "connection": _b_connection,
    "count_obj": _b_count_obj, "select_obj": _b_select_obj,
    "area_center": _b_area_center, "area": _b_area,
    "select_shape": _b_select_shape, "union_object": _b_union_object,
    "mean_gray": _b_mean_gray, "max_gray": _b_max_gray, "min_gray": _b_min_gray,
    "region_to_image": _b_region_to_image,
}


_NO_OP = object()


def _seed_value(v):
    """Wrap a seeded / loaded value into the typed model.

    A raw 2-D array is an FImage whose range comes from its dtype (never from the
    content); a boolean array is a Region.  Values that are already typed pass
    through unchanged, and a 3-channel array is left raw for ``to_gray``.
    """
    if isinstance(v, (FImage, Region, ObjectSet)):
        return v
    if isinstance(v, np.ndarray):
        if v.ndim == 2 and v.dtype == bool:
            return Region(v)
        if v.ndim == 2:
            return _wrap_array_as_image(v)
    if isinstance(v, (list, tuple)):
        return list(v)                  # a seeded tuple is copied: the script never mutates the caller's list
    return v


def _unwrap_iconic(v):
    """The raw array behind an iconic value, for the registry long-tail."""
    if isinstance(v, FImage):
        return v.pixels
    if isinstance(v, Region):
        return _region_mask(v)
    return np.asarray(v)


def _wrap_registry_out(out, out_sort, inp):
    """Re-wrap a registry op's raw output into the typed model by declared sort."""
    if out_sort == "region":
        return out if isinstance(out, Region) else Region(np.asarray(out) > 0)
    if out_sort == "image":
        lo, hi = inp.value_range if isinstance(inp, FImage) else (0.0, 1.0)
        return FImage(np.asarray(out, dtype=np.float64), value_range=(lo, hi))
    if out_sort == "feature":
        arr = np.asarray(out)
        return float(arr) if arr.size == 1 else [float(x) for x in arr.ravel()]
    arr = np.asarray(out)
    if arr.ndim == 2:
        return Region(arr) if arr.dtype == bool else FImage(arr.astype(np.float64))
    return out


def _call_registry_op(name, args):
    """Long-tail: call any registered fullseye op as op(Input, a=0.5, b=0.5).
    Returns _NO_OP when the name is not a registered op."""
    try:
        import api
    except Exception:
        return _NO_OP
    op = api.find_op(name)
    if op is None:
        return _NO_OP
    if not args:
        raise FScriptError("op '%s' needs an input image/region" % name)
    # Every registered op is called as RT[name](input, a, b) — the registry has no
    # third knob.  A 4th argument used to be dropped in silence, so the op ran with
    # settings the script never wrote; say so instead.
    if len(args) > 3:
        raise FScriptError(
            "op '%s' takes at most 3 arguments (input, a, b); got %d"
            % (name, len(args)))
    inp = args[0]
    a = float(_as_number(args[1], "op '%s' argument a" % name)) if len(args) > 1 else 0.5
    b = float(_as_number(args[2], "op '%s' argument b" % name)) if len(args) > 2 else 0.5
    out = api.RT[name](_unwrap_iconic(inp), a, b)
    return _wrap_registry_out(out, getattr(op, "out_sort", None), inp)


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #
def run(src_or_program, images=None, base_dir=None, trace=None, max_steps=2_000_000):
    """Parse (if needed) and run a Fullseye script. ``images`` seeds named iconic
    variables (e.g. {'Image': arr}); ``base_dir`` resolves read_image paths;
    ``trace(line, env)`` is called after each top-level statement (for stepping).
    Returns the ``Env`` (``env.vars`` holds the resulting variables)."""
    program = parse(src_or_program) if isinstance(src_or_program, str) else src_or_program
    env = Env(base_dir=base_dir)
    env.trace = trace
    if images:
        for name, value in images.items():
            env.vars[name] = _seed_value(value)
    Interp(env, max_steps=max_steps).run_program(program)
    return env


def check(src: str):
    """Parse-only: return a list of error strings (empty when the script parses).

    Never raises: an editor calls this on every keystroke, so anything the
    parser lets escape (it should be nothing) is reported as text too."""
    try:
        parse(src)
        return []
    except FScriptError as e:
        return [str(e)]
    except Exception as e:                            # pragma: no cover - defensive
        return ["internal parser error: %s: %s" % (type(e).__name__, e)]
