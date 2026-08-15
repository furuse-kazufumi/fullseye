"""Fullseye Script — a small HDevelop/HDevEngine-flavoured interpreter.

This is a *real* interpreted language (not the old flat (op, a, b) pipeline), so a
rule-based image-processing algorithm can actually be written: named variables,
real control flow that branches on *measured* values, per-object iteration, and
I/O. It is the language layer the Studio's Program window runs.

Design (increment 1):
  * Values are typed dynamically:
      - control : number / string / tuple (Python float/int/str/list)
      - iconic  : an image or a region  (a numpy array; a region is a boolean mask)
      - object  : a *tuple of regions*  (connected components / selected blobs)
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

import numpy as np


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
            j = i + 1
            buf = []
            while j < n and src[j] != "'":
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j + 1]); j += 2; continue
                buf.append(src[j]); j += 1
            if j >= n:
                raise FScriptError("unterminated string", line)
            toks.append(Tok("str", "".join(buf), line)); i = j + 1; continue
        if c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit()):
            j = i
            while j < n and (src[j].isdigit() or src[j] in ".eE" or
                             (src[j] in "+-" and j > i and src[j - 1] in "eE")):
                j += 1
            text = src[i:j]
            toks.append(Tok("num", float(text) if any(k in text for k in ".eE") else int(text), line))
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
            if t.val == "break":
                self._next(); self._expect_end_of_stmt(); return Break(t.line)
            if t.val == "continue":
                self._next(); self._expect_end_of_stmt(); return Continue(t.line)
            raise FScriptError("unexpected keyword '%s'" % t.val, t.line)
        # assignment  Name := expr   or   Name[i] := expr   or bare expression
        if t.kind == "name":
            save = self.i
            target = self._parse_primary()          # Name or Name[idx]
            if self._at_op(":="):
                self._next()
                expr = self._parse_expr()
                self._expect_end_of_stmt()
                return Assign(target, expr, t.line)
            self.i = save                            # not an assignment -> expression stmt
        expr = self._parse_expr()
        self._expect_end_of_stmt()
        return ExprStmt(expr, expr.line)

    def _parse_if(self):
        line = self._next().line                     # 'if'
        cond = self._parse_paren_cond()
        body = self._parse_block(("elseif", "else", "endif"))
        branches = [(cond, body)]
        orelse = None
        while self._at_kw("elseif"):
            self._next()
            c = self._parse_paren_cond()
            b = self._parse_block(("elseif", "else", "endif"))
            branches.append((c, b))
        if self._at_kw("else"):
            self._next()
            orelse = self._parse_block(("endif",))
        if not self._at_kw("endif"):
            raise FScriptError("missing 'endif'", line)
        self._next(); self._expect_end_of_stmt()
        return If(branches, orelse, line)

    def _parse_paren_cond(self):
        # HDevelop uses parentheses around conditions; accept with or without.
        if self._at_op("("):
            self._next()
            c = self._parse_expr()
            self._expect_op(")")
        else:
            c = self._parse_expr()
        return c

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
        body = self._parse_block(("endfor",))
        if not self._at_kw("endfor"):
            raise FScriptError("missing 'endfor'", line)
        self._next(); self._expect_end_of_stmt()
        return For(var.val, start, stop, step, body, line)

    def _parse_while(self):
        line = self._next().line
        cond = self._parse_paren_cond()
        body = self._parse_block(("endwhile",))
        if not self._at_kw("endwhile"):
            raise FScriptError("missing 'endwhile'", line)
        self._next(); self._expect_end_of_stmt()
        return While(cond, body, line)

    def _parse_repeat(self):
        line = self._next().line
        body = self._parse_block(("until",))
        if not self._at_kw("until"):
            raise FScriptError("missing 'until'", line)
        self._next()
        cond = self._parse_paren_cond()
        self._expect_end_of_stmt()
        return Repeat(body, cond, line)

    # -- expressions (precedence climbing) ---------------------------------- #
    _BINPREC = {"or": 1, "and": 2, "=": 3, "==": 3, "!=": 3, "#": 3, "<": 3,
                ">": 3, "<=": 3, ">=": 3, "+": 4, "-": 4, "*": 5, "/": 5, "%": 5}

    def _parse_expr(self, min_prec=0):
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
            self._next()
            right = self._parse_expr(self._BINPREC[op] + 1)
            left = BinOp(op, left, right, t.line)
        return left

    def _parse_unary(self):
        t = self._peek()
        if (t.kind == "op" and t.val == "-") or (t.kind == "kw" and t.val == "not"):
            self._next()
            return UnOp(t.val, self._parse_unary(), t.line)
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
    return Parser(tokenize(src)).parse_program()


# --------------------------------------------------------------------------- #
# Values / environment
# --------------------------------------------------------------------------- #
def value_kind(v) -> str:
    """Classify a value for the Variable window: 'image' / 'region' / 'object'
    (a tuple of regions) / 'control'."""
    if isinstance(v, np.ndarray):
        if v.ndim == 2 and _is_region(v):
            return "region"
        return "image"
    if isinstance(v, list) and v and all(isinstance(x, np.ndarray) for x in v):
        return "object"
    return "control"


def _is_region(v) -> bool:
    return v.dtype == bool or (v.ndim == 2 and np.unique(v).size <= 2)


class Env:
    """Variable environment + call context (built-ins, registry ops, base dir)."""

    def __init__(self, base_dir=None):
        self.vars = {}
        self.base_dir = base_dir
        self.trace = None

    def kinds(self):
        return {k: value_kind(v) for k, v in self.vars.items()}


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


# --------------------------------------------------------------------------- #
# Interpreter
# --------------------------------------------------------------------------- #
class Interp:
    def __init__(self, env: Env, max_steps=2_000_000):
        self.env = env
        self.steps = 0
        self.max_steps = max_steps

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
            self.env.vars[node.target.name] = val
        elif isinstance(node.target, Index):
            base = self._eval(node.target.base)
            idx = int(self._eval(node.target.idx))
            if not isinstance(base, list):
                raise FScriptError("cannot index-assign a non-tuple", node.line)
            base[idx] = val
        else:
            raise FScriptError("invalid assignment target", node.line)

    def _st_ExprStmt(self, node):
        self._eval(node.expr)

    def _st_If(self, node):
        for cond, body in node.branches:
            if _truth(self._eval(cond)):
                self.run(body)
                return
        if node.orelse is not None:
            self.run(node.orelse)

    def _st_For(self, node):
        start = self._eval(node.start)
        stop = self._eval(node.stop)
        step = self._eval(node.step) if node.step is not None else 1
        if step == 0:
            raise FScriptError("'for' step must not be 0", node.line)
        i = start
        while (step > 0 and i <= stop) or (step < 0 and i >= stop):
            self.env.vars[node.var] = i
            try:
                self.run(node.body)
            except _Break:
                break
            except _Continue:
                pass
            i += step

    def _st_While(self, node):
        while _truth(self._eval(node.cond)):
            try:
                self.run(node.body)
            except _Break:
                break
            except _Continue:
                continue

    def _st_Repeat(self, node):
        while True:
            try:
                self.run(node.body)
            except _Break:
                break
            except _Continue:
                pass
            if _truth(self._eval(node.cond)):
                break

    def _st_Break(self, node):
        raise _Break()

    def _st_Continue(self, node):
        raise _Continue()

    # -- expressions -------------------------------------------------------- #
    def _eval(self, node):
        m = getattr(self, "_ev_" + type(node).__name__, None)
        if m is None:
            raise FScriptError("cannot evaluate %s" % type(node).__name__, getattr(node, "line", 0))
        return m(node)

    def _ev_Num(self, n): return n.v

    def _ev_Str(self, n): return n.v

    def _ev_Bool(self, n): return n.v

    def _ev_TupleLit(self, n): return [self._eval(x) for x in n.items]

    def _ev_Name(self, n):
        if n.name in self.env.vars:
            return self.env.vars[n.name]
        raise FScriptError("undefined variable '%s'" % n.name, n.line)

    def _ev_Index(self, n):
        base = self._eval(n.base)
        idx = self._eval(n.idx)
        try:
            return base[int(idx)]
        except (TypeError, IndexError, KeyError) as e:
            raise FScriptError("cannot index %s: %s" % (type(base).__name__, e), n.line)

    def _ev_UnOp(self, n):
        v = self._eval(n.a)
        if n.op == "-":
            return -v
        if n.op == "not":
            return not _truth(v)
        raise FScriptError("bad unary op %s" % n.op, n.line)

    def _ev_BinOp(self, n):
        if n.op in ("and", "or"):                    # short-circuit
            a = self._eval(n.a)
            if n.op == "and":
                return _truth(a) and _truth(self._eval(n.b))
            return _truth(a) or _truth(self._eval(n.b))
        a, b = self._eval(n.a), self._eval(n.b)
        try:
            if n.op == "+":
                if isinstance(a, list) or isinstance(b, list):   # tuple concat
                    return (a if isinstance(a, list) else [a]) + (b if isinstance(b, list) else [b])
                return a + b
            if n.op == "-": return a - b
            if n.op == "*": return a * b
            if n.op == "/": return a / b
            if n.op == "%": return a % b
            if n.op in ("=", "=="): return a == b
            if n.op in ("!=", "#"): return a != b
            if n.op == "<": return a < b
            if n.op == ">": return a > b
            if n.op == "<=": return a <= b
            if n.op == ">=": return a >= b
        except (TypeError, ZeroDivisionError) as e:
            raise FScriptError("bad operation %s: %s" % (n.op, e), n.line)
        raise FScriptError("bad binary op %s" % n.op, n.line)

    def _ev_Call(self, n):
        args = [self._eval(a) for a in n.args]
        fn = BUILTINS.get(n.name)
        if fn is not None:
            try:
                return fn(self.env, *args)
            except FScriptError:
                raise
            except Exception as e:                    # surface a clean line-tagged error
                raise FScriptError("%s: %s" % (n.name, e), n.line)
        # long-tail: any registered fullseye op, called as op(Input, a=.5, b=.5)
        op_out = _call_registry_op(n.name, args)
        if op_out is not _NO_OP:
            return op_out
        raise FScriptError("unknown function/operator '%s'" % n.name, n.line)


def _truth(v) -> bool:
    if isinstance(v, np.ndarray):
        return bool(v.any())
    if isinstance(v, list):
        return len(v) > 0
    return bool(v)


# --------------------------------------------------------------------------- #
# Built-in vision vocabulary (REAL parameters)
# --------------------------------------------------------------------------- #
def _to_gray(img):
    img = np.asarray(img, dtype=np.float64)
    if img.ndim == 3:
        img = img[..., :3].mean(axis=2)
    return img


def _norm01(img):
    img = np.asarray(img, dtype=np.float64)
    m = img.max()
    return img / m if m > 1.0 else img


def _as_mask(region):
    r = np.asarray(region)
    return r > (0.5 if r.max() <= 1.0 else r.max() * 0.5) if r.dtype != bool else r


def _b_read_image(env, path):
    import os
    p = str(path)
    if env.base_dir and not os.path.isabs(p):
        cand = os.path.join(env.base_dir, p)
        if os.path.exists(cand):
            p = cand
    import imgio
    return _norm01(imgio.load(p))


def _b_rgb1_to_gray(env, img):
    return _to_gray(img)


def _b_gauss_image(env, img, sigma):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(np.asarray(img, dtype=np.float64), float(sigma))


def _b_mean_image(env, img, radius):
    from scipy.ndimage import uniform_filter
    k = max(1, int(2 * float(radius) + 1))
    return uniform_filter(np.asarray(img, dtype=np.float64), k)


def _b_invert_image(env, img):
    a = _norm01(img)
    return 1.0 - a


def _b_threshold(env, img, lo, hi):
    a = _norm01(_to_gray(img)) if np.asarray(img).ndim == 3 else _norm01(img)
    return (a >= float(lo)) & (a <= float(hi))


def _b_binary_threshold(env, img):
    """Otsu auto-threshold -> region (bright objects)."""
    a = _norm01(_to_gray(img)) if np.asarray(img).ndim == 3 else _norm01(img)
    hist, edges = np.histogram(a, bins=256, range=(0.0, 1.0))
    p = hist.astype(np.float64) / max(1, hist.sum())
    omega = np.cumsum(p)
    mu = np.cumsum(p * (np.arange(256) + 0.5) / 256.0)
    mu_t = mu[-1]
    denom = omega * (1.0 - omega)
    denom[denom == 0] = 1e-12
    sigma_b = (mu_t * omega - mu) ** 2 / denom
    t = (np.argmax(sigma_b) + 0.5) / 256.0
    return a >= t


def _b_dilation(env, region, radius):
    from scipy.ndimage import binary_dilation, generate_binary_structure, iterate_structure
    st = iterate_structure(generate_binary_structure(2, 1), max(1, int(radius)))
    return binary_dilation(_as_mask(region), st)


def _b_erosion(env, region, radius):
    from scipy.ndimage import binary_erosion, generate_binary_structure, iterate_structure
    st = iterate_structure(generate_binary_structure(2, 1), max(1, int(radius)))
    return binary_erosion(_as_mask(region), st)


def _b_connection(env, region):
    """Split a region into its connected components — the object variable that a
    for-loop iterates and select_shape filters."""
    from scipy.ndimage import label
    lbl, k = label(_as_mask(region))
    return [(lbl == i) for i in range(1, k + 1)]


def _objects(x):
    if isinstance(x, list):
        return x
    if isinstance(x, np.ndarray):
        return [_as_mask(x)]
    raise ValueError("expected a region or object tuple")


def _b_count_obj(env, objects):
    return len(_objects(objects))


def _b_select_obj(env, objects, index):
    objs = _objects(objects)
    i = int(index)
    if not (0 <= i < len(objs)):
        raise ValueError("select_obj index %d out of range 0..%d" % (i, len(objs) - 1))
    return objs[i]


def _region_area(region):
    return int(np.count_nonzero(_as_mask(region)))


def _region_center(region):
    m = _as_mask(region)
    ys, xs = np.nonzero(m)
    if ys.size == 0:
        return (0, 0.0, 0.0)
    return (int(ys.size), float(ys.mean()), float(xs.mean()))


_FEATURES = {
    "area": lambda r: float(_region_area(r)),
    "row": lambda r: _region_center(r)[1],
    "column": lambda r: _region_center(r)[2],
    "width": lambda r: float(np.ptp(np.nonzero(_as_mask(r))[1]) + 1) if _region_area(r) else 0.0,
    "height": lambda r: float(np.ptp(np.nonzero(_as_mask(r))[0]) + 1) if _region_area(r) else 0.0,
}


def _b_area_center(env, region):
    return list(_region_center(region))


def _b_area(env, region):
    return float(_region_area(region))


def _b_select_shape(env, objects, feature, vmin, vmax):
    feat = _FEATURES.get(str(feature))
    if feat is None:
        raise ValueError("unknown feature '%s' (have: %s)" % (feature, ", ".join(_FEATURES)))
    lo, hi = float(vmin), float(vmax)
    return [r for r in _objects(objects) if lo <= feat(r) <= hi]


def _b_union_object(env, objects):
    objs = _objects(objects)
    if not objs:
        return np.zeros((1, 1), dtype=bool)
    out = np.zeros_like(objs[0], dtype=bool)
    for r in objs:
        out |= _as_mask(r)
    return out


def _b_mean_gray(env, img):
    return float(np.asarray(img, dtype=np.float64).mean())


def _b_max_gray(env, img):
    return float(np.asarray(img, dtype=np.float64).max())


def _b_min_gray(env, img):
    return float(np.asarray(img, dtype=np.float64).min())


def _b_region_to_image(env, region):
    return _as_mask(region).astype(np.float64)


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


def _call_registry_op(name, args):
    """Long-tail: call any registered fullseye op as op(Input, a=0.5, b=0.5).
    Returns _NO_OP when the name is not a registered op."""
    try:
        import api
    except Exception:
        return _NO_OP
    if api.find_op(name) is None:
        return _NO_OP
    if not args:
        raise FScriptError("op '%s' needs an input image/region" % name)
    img = args[0]
    a = float(args[1]) if len(args) > 1 else 0.5
    b = float(args[2]) if len(args) > 2 else 0.5
    return api.RT[name](np.asarray(img), a, b)


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
        env.vars.update(images)
    Interp(env, max_steps=max_steps).run(program)
    return env


def check(src: str):
    """Parse-only: return a list of error strings (empty when the script parses)."""
    try:
        parse(src)
        return []
    except FScriptError as e:
        return [str(e)]
