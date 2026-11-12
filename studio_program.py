# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Fullseye Studio の Program 欄を **本物の Python** として走らせる、Qt に依らない実行系。

設計の正本は ``docs/STUDIO_PROGRAM_LANGUAGE.md``。ここは要点だけ:

* Program 欄の記法は 2 つ。従来の **HDevelop 風**(段の列が正本。``op (a, b)``・``for N``…)と、
  横に足した **Python 風**(本物の Python)。どちらかは :func:`detect_syntax` が自動で見分け、
  1 行目の ``# python`` / ``# hdevelop`` で明示もできる。1 つのプログラムで混ぜることはできない。
* Python 風は ``compile`` して前置き(prelude)の名前空間で ``exec`` する。前置きは op 名の関数
  (``gaussian(img, 0.4)``)・``img``・``show``・``op``・``pipeline``・``np``・``fs`` を用意し、
  op の関数は呼ばれるたびに記録(:class:`CallRecord`)を残す。この記録が Studio の「段の列」になる。
* ``sys.settrace`` で行ごとにブレークポイント・1 行実行・停止の要求・時間の上限を扱う。
* op の呼び出しは (op 名, つまみ, 入力の中身の指紋) でメモ化する(:class:`OpMemo`)。
* 書き出し(:func:`export_python_script`)は「前置きの import + Program の文面 + 入出力の数行」で、
  ``py -3.11 file.py 入力画像`` で同じ結果になる(前置き ``fullseye.studio_prelude`` は同じ記録層を使う)。
* 本物の Python を実行するので、ファイル・プロジェクト・MCP から来たプログラムは ``trusted=False``
  で渡し、確認が済むまで実行しない(:func:`run_program` は理由を返すだけ)。
"""
from __future__ import annotations

import ast
import builtins
import contextlib
import contextvars
import hashlib
import importlib
import io
import json
import keyword
import math
import os
import re
import sys
import threading
import time
import weakref
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

import numpy as np

__all__ = [
    "SYNTAX_PYTHON", "SYNTAX_HDEVELOP", "PROGRAM_FILENAME", "DEFAULT_TIME_LIMIT_S",
    "CallRecord", "VarInfo", "ProgramResult", "Advice", "OpMemo", "Recorder", "Pipeline",
    "detect_syntax", "run_program", "program_digest", "TrustStore",
    "hdev_to_python", "python_to_hdev", "export_python_script", "advise_program",
    "prelude_exports", "prelude_collisions", "prelude_namespace", "op_table", "memo_eligible",
    "fingerprint", "describe_value", "pipeline_search_dirs", "close_program_windows", "needs_gui_thread",
    "Problem", "check_program", "checker_backends", "complete", "hover", "apply_fix", "CONFIGS",
    "run_file", "evaluate", "STARTER_PROGRAM",
]

SYNTAX_PYTHON = "python"
SYNTAX_HDEVELOP = "hdevelop"

#: ``compile`` に渡すファイル名。トレースと例外の行番号はこの名前の枠だけを Program の行と見なす。
PROGRAM_FILENAME = "<studio-program>"

#: 時間の上限の既定(秒)。行ごとに見るので、C の中で回っている重い op の途中では止まらない。
DEFAULT_TIME_LIMIT_S = 30.0

#: 起動時に Program 欄へ入れる Python の例(既定のモードは Python、設計書 §1)。同梱の画像を読み、op 4 つ・
#: 変数・if を 1 つずつ使う。実行すると絵(show)と段の列(記録)が出る。画面の文と同じく英語で書く。
STARTER_PROGRAM = """# python
# Fullseye Studio - press F5 (Run): the picture and the stage list appear.
import sample_images                       # images that ship with Fullseye
img = sample_images.load("coins")          # delete this line to use the image open in Studio
img = gaussian(img, 0.3)                   # 1. smooth
mask = otsu(img)                           # 2. bright parts -> region
n = blob_count(mask)                       # 3. count the blobs (a number)
print("blobs:", n)
if n > 10:
    mask = opening_circle(mask, 0.3)       # 4a. many specks: remove the small ones
else:
    mask = fill_holes(mask)                # 4b. few blobs: fill their holes
show(mask)
"""

#: 実行の構成。Debug = 行フックあり(既定)、Release = 速さ優先(行フックなし)。
CONFIGS = ("debug", "release")

#: 「測るだけ」の出力 sort。この op は流れ(今の画像)を変えず、値だけを返す。
MEASURE_SORTS = frozenset({"feature", "match"})

#: 前置きが予約する名前(op の関数としては出さない)。
PRELUDE_RESERVED = ("img", "image", "show", "op", "pipeline", "current_pipeline", "load_pipeline", "ui", "show_window",
                    "np", "fs", "studio_input", "studio_output", "print")

#: 1 行目の印。``# python`` / ``# fullseye: python`` / ``# hdevelop`` / ``# fullseye: hdevelop``。
_MARKER_RE = re.compile(r"^\s*#\s*(?:fullseye\s*:\s*)?(python|hdevelop)\s*$", re.IGNORECASE)

#: 乱数・時刻・外部状態に依る op の実装に現れる語(メモ化しない側へ倒す印)。
_NONDET_RE = re.compile(r"random|default_rng|\brng\b|seed|time\.time|perf_counter|datetime|"
                        r"open\(|write_image|imwrite|savefig|np\.save|urlopen|requests\.")
#: 名前だけで乱数・副作用と分かる op。
_NONDET_NAME_RE = re.compile(r"noise|random|rand_|_rand|jitter|dither|shuffle|bootstrap|"
                             r"ransac|sample|augment|aug_|monte|mc_|stochastic|perturb|write|save")


# --------------------------------------------------------------------------- #
# op の台帳                                                                     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OpInfo:
    """1 つの op の、記録層が使う性質。"""
    name: str
    in_sort: str
    out_sort: str
    arity: int


_OP_TABLE: dict | None = None
_MEMO_OK: dict = {}
_TABLE_LOCK = threading.Lock()


def op_table() -> dict:
    """画像の op(general 層を除く)の ``name -> OpInfo``。最初の呼び出しで api から作って覚える。"""
    global _OP_TABLE
    with _TABLE_LOCK:
        if _OP_TABLE is None:
            import api
            tab = {}
            for r in api.list_ops():
                if r.get("backend") == "general":
                    continue
                tab[r["name"]] = OpInfo(r["name"], str(r.get("in_sort")), str(r.get("out_sort")),
                                        int(r.get("arity") or 1))
            _OP_TABLE = tab
        return _OP_TABLE


def memo_eligible(name: str) -> bool:
    """op *name* の結果をメモ化してよいか。分からなければ False(計算し直す側)。

    名前で乱数・副作用と分かるもの、実装のソース(``_safe`` などの包みを外した本体)に乱数・時刻・
    ファイル書き込みの語が現れるもの、ソースが読めないもの、n-ary(本体が別の層)は False。
    呼び出した先の補助関数までは読まないので、確実ではない(設計書「メモ化」の節)。"""
    if name in _MEMO_OK:
        return _MEMO_OK[name]
    ok = False
    try:
        info = op_table().get(name)
        if info is not None and info.arity == 1 and not _NONDET_NAME_RE.search(name):
            import inspect
            import api
            fn = api._resolve(name).fn
            body = inspect.unwrap(fn)
            if body is fn and getattr(fn, "__closure__", None):
                inner = [c.cell_contents for c in fn.__closure__ if callable(c.cell_contents)]
                if inner:
                    body = inspect.unwrap(inner[0])
            src = inspect.getsource(body)
            ok = not _NONDET_RE.search(src)
    except Exception:                                # noqa: BLE001 -- 分からない = メモ化しない
        ok = False
    _MEMO_OK[name] = ok
    return ok


def _directive_names() -> set:
    """HDevelop 風の表示指示(dev_* / disp_* / set_system)。前置きでは記録するだけの関数になる。"""
    import studio
    return set(studio._DEV_DIRECTIVES) | set(studio._DISP_DIRECTIVES) | set(studio._CONFIG_DIRECTIVES)


def prelude_collisions(names: Iterable[str] | None = None) -> dict:
    """前置きで **関数として出せない** op 名と理由(``name -> reason``)。

    理由: Python の予約語・ソフト予約語、組み込み名(``min``・``abs`` …)、前置きの予約名、
    識別子にならない名前、表示指示と同名。これらは ``op("名前", x, a, b)`` で呼ぶ。"""
    names = list(op_table()) if names is None else list(names)
    try:
        directives = _directive_names()
    except Exception:                                # noqa: BLE001
        directives = set()
    out = {}
    for n in names:
        if not n.isidentifier():
            out[n] = "not an identifier"
        elif keyword.iskeyword(n):
            out[n] = "python keyword"
        elif keyword.issoftkeyword(n):
            out[n] = "python soft keyword"
        elif n in dir(builtins):
            out[n] = "python builtin"
        elif n in PRELUDE_RESERVED:
            out[n] = "prelude name"
        elif n in directives:
            out[n] = "display directive"
    return out


def prelude_exports() -> list:
    """前置きが関数として出す op 名(衝突するものを除く)。"""
    bad = prelude_collisions()
    return [n for n in op_table() if n not in bad]


# --------------------------------------------------------------------------- #
# 値の指紋とメモ化                                                              #
# --------------------------------------------------------------------------- #
def _content_hash(v) -> str | None:
    """中身の SHA-256(engine._input_hash と同じ。1024×1024 float64 で約 2 ms)。数えられなければ None。"""
    try:
        import engine
        return engine._input_hash(v)
    except Exception:                                # noqa: BLE001 -- object 配列など
        return None


def fingerprint(v, memo: "OpMemo | None" = None) -> str | None:
    """値 *v* の指紋。同じ中身なら同じ文字列、数えられなければ None(=メモ化しない)。

    * 記録層が作った読み取り専用の配列は「由来の指紋」(作った呼び出しの鍵)を使う —— 画素を読まない。
    * それ以外の配列(numpy で作った物・書き換えできる物)は毎回中身を SHA-256 で読む。
    * 数・文字列・None はそのまま、list / tuple / dict は中身を辿る。"""
    if isinstance(v, (bool, int, float, str, type(None), np.generic)):
        return "s:%s:%r" % (type(v).__name__, v.item() if isinstance(v, np.generic) else v)
    if isinstance(v, np.ndarray):
        if memo is not None and not v.flags.writeable:
            fp = memo.provenance(v)
            if fp is not None:
                return fp
        h = _content_hash(v)
        if h is None:
            return None
        if memo is not None and not v.flags.writeable:
            memo.remember(v, "c:" + h)
        return "c:" + h
    if isinstance(v, (list, tuple)):
        parts = [fingerprint(x, memo) for x in v]
        return None if any(p is None for p in parts) else "%s[%s]" % (type(v).__name__, ",".join(parts))
    if isinstance(v, dict):
        try:
            items = sorted(v.items(), key=lambda kv: repr(kv[0]))
        except Exception:                            # noqa: BLE001
            return None
        parts = []
        for k, x in items:
            p = fingerprint(x, memo)
            if p is None:
                return None
            parts.append("%r=%s" % (k, p))
        return "dict{%s}" % ",".join(parts)
    return None


class OpMemo:
    """op の呼び出しのメモ(実行をまたいで残す)。鍵 = (op, a, b, 入力の指紋…, device)。

    値の置き場は ``studio_result.StageCache``(PipelineModel の段のキャッシュと同じ LRU・同じ上限
    ``CACHE_BUDGET_BYTES``)。由来の指紋は ``id`` + weakref で引く(配列が消えたら引けない)。"""

    def __init__(self, budget_bytes: int | None = None):
        import studio_result
        self._store = studio_result.StageCache(studio_result.CACHE_BUDGET_BYTES
                                               if budget_bytes is None else budget_bytes)
        self._prov: dict = {}
        self.hits = 0
        self.misses = 0

    def provenance(self, arr) -> str | None:
        rec = self._prov.get(id(arr))
        if rec is not None and rec[0]() is arr:
            return rec[1]
        return None

    def remember(self, arr, fp: str) -> None:
        try:
            ref = weakref.ref(arr)
        except TypeError:
            return
        self._prov[id(arr)] = (ref, fp)
        if len(self._prov) > 4096:                   # 死んだ参照を掃く
            self._prov = {k: r for k, r in self._prov.items() if r[0]() is not None}

    def get(self, key):
        if key in self._store:
            self.hits += 1
            return True, self._store.get(key)
        return False, None

    def put(self, key, value, ms: float) -> None:
        self.misses += 1
        self._store.put(key, value, ms)

    def stats(self) -> dict:
        d = dict(self._store.stats())
        d.update(hits=self.hits, misses=self.misses)
        return d

    def clear(self) -> None:
        self._store.clear()
        self._prov.clear()
        self.hits = self.misses = 0


def _key_digest(key) -> str:
    return "p:" + hashlib.sha256(repr(key).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# 記録                                                                          #
# --------------------------------------------------------------------------- #
@dataclass
class CallRecord:
    """op の呼び出し 1 回の記録 = Studio の段 1 つ。"""
    index: int
    op: str
    a: float
    b: float
    line: int
    inputs: list                      # [(kind, shape), ...] 入力ごと。省いた入力は "flow" と書く
    out_sort: str
    out_shape: tuple | None
    ms: float
    cached: bool
    device: str = "cpu"
    measured: bool = False            # 測るだけの op(流れを変えない)
    bypass: bool = False              # HDevelop 風の「# bypassed:」の段
    pipeline: str | None = None       # パイプラインとして呼んだ中の段なら、その名前
    pipeline_step: int | None = None  # そのパイプラインの何段目か(1 始まり)
    implicit_input: bool = False      # 入力を省いて「今の流れ」に掛けた
    value: Any = None                 # 結果の参照

    def stage(self) -> tuple:
        return (self.op, self.a, self.b)


class ProgramOpError(ValueError):
    """op の呼び方の誤り(入力の数、つまみの型、未知の op …)。Program の行番号は呼び出し元から取る。"""


class ProgramStopped(BaseException):
    """settrace の中から実行を止める。``except Exception`` では捕まらない(BaseException)。"""

    def __init__(self, reason: str, line: int):
        super().__init__(reason, line)
        self.reason = reason
        self.line = line


def _kind_of(v, rec: "Recorder | None" = None) -> str:
    if isinstance(v, np.ndarray):
        if rec is not None:
            s = rec.sort_of(v)
            if s:
                return s
        return "ndarray"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, np.integer)):
        return "int"
    if isinstance(v, (float, np.floating)):
        return "float"
    return type(v).__name__


def _shape_of(v):
    return tuple(int(s) for s in v.shape) if isinstance(v, np.ndarray) else None


def _is_knob(v) -> bool:
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_))


class Recorder:
    """op の呼び出しを記録し、流れ(今の画像)と ``show`` を持つ。Studio の実行と書き出しの両方が使う。"""

    def __init__(self, memo: OpMemo | None = None, device: str = "cpu", program_filename: str | None = None):
        self.memo = memo
        self.device = device
        self.program_filename = program_filename
        self.calls: list[CallRecord] = []
        self.clamped: list[str] = []
        self.directives: list[tuple] = []
        self.input = None
        self.flow = None
        self.flow_sort = "image"
        self.flow_line = 0
        self.shown = None
        self.shown_set = False
        self.shown_line = 0
        self.current_stages: list = []
        #: show_window で開いた窓(実行の終わり・停止で close_program_windows が閉じる)
        self.windows: list = []
        #: Release の構成で止める場所 = op の呼び出しの境目(Debug は settrace の行フックが止める)
        self.stop_event = None
        self.deadline: float | None = None
        self.time_limit_s: float | None = None
        #: load_pipeline の相対パスを探す場所(None = engine.load_pipeline の既定)
        self.search_dirs: list | None = None
        self._sorts: dict = {}
        self._pipe_ctx = None

    # -- 値の型 -- #
    def set_input(self, image) -> np.ndarray:
        """入力を読み取り専用の view にして流れの起点にする(Studio の元の配列は書き換えない)。"""
        arr = np.asarray(image)
        view = arr.view()
        view.flags.writeable = False
        self.input = self.flow = view
        self.flow_sort = "image"
        self._note_sort(view, "image")
        return view

    def _note_sort(self, v, sort):
        if isinstance(v, np.ndarray):
            try:
                self._sorts[id(v)] = (weakref.ref(v), sort)
            except TypeError:
                pass

    def sort_of(self, v) -> str | None:
        rec = self._sorts.get(id(v))
        if rec is not None and rec[0]() is v:
            return rec[1]
        return None

    # -- 呼び出し元の行 -- #
    def caller_line(self) -> int:
        here = (os.path.abspath(__file__).lower(),)
        f = sys._getframe(1)
        fallback = 0
        while f is not None:
            fn = f.f_code.co_filename
            if self.program_filename is not None:
                if fn == self.program_filename:
                    return f.f_lineno
            else:
                low = os.path.abspath(fn).lower() if not fn.startswith("<") else fn
                if low not in here and not low.endswith("studio_prelude.py"):
                    return f.f_lineno
            if fallback == 0 and (fn == PROGRAM_FILENAME or fn == self.program_filename):
                fallback = f.f_lineno
            f = f.f_back
        return fallback

    def check_stop(self, line: int) -> None:
        """op の呼び出しの境目で、停止の要求と時間の上限を見る(Release の構成の止める場所)。"""
        if self.stop_event is not None and self.stop_event.is_set():
            raise ProgramStopped("stop_requested", line)
        if self.deadline is not None and time.perf_counter() > self.deadline:
            raise ProgramStopped("time_limit", line)

    # -- op の呼び出し -- #
    def bind(self, name: str, args: tuple, a_kw, b_kw) -> tuple:
        """位置引数を「入力…, つまみ…」に分け、``(inputs, a, b, implicit)`` を返す。誤りは ProgramOpError。"""
        info = op_table().get(name)
        if info is None:
            raise ProgramOpError("unknown op %r" % (name,))
        inputs, knobs = [], []
        for i, v in enumerate(args):
            if _is_knob(v):
                knobs.append(v)
            elif knobs:
                raise ProgramOpError("%s: argument %d must be a number (inputs come first, then a, b)"
                                     % (name, i + 1))
            elif isinstance(v, (str, bool, type(None))):
                raise ProgramOpError("%s: argument %d (%r) is neither an input nor a number"
                                     % (name, i + 1, v))
            else:
                inputs.append(v)
        if len(knobs) > 2:
            raise ProgramOpError("%s takes at most 2 knobs (a, b), got %d" % (name, len(knobs)))
        a = knobs[0] if len(knobs) > 0 else None
        b = knobs[1] if len(knobs) > 1 else None
        if a_kw is not None:
            if a is not None:
                raise ProgramOpError("%s: a given twice" % name)
            a = a_kw
        if b_kw is not None:
            if b is not None:
                raise ProgramOpError("%s: b given twice" % name)
            b = b_kw
        vals = []
        for key, val in (("a", a), ("b", b)):
            if val is None:
                val = 0.5
            if not _is_knob(val):
                raise ProgramOpError("%s: %s must be a number, got %r" % (name, key, val))
            val = float(val)
            if not math.isfinite(val):
                raise ProgramOpError("%s: %s must be finite, got %r" % (name, key, val))
            if not 0.0 <= val <= 1.0:
                used = max(0.0, min(1.0, val))
                if "%.6g" % val != "%.6g" % used:
                    self.clamped.append("line %d: %s %s=%.6g → %.6g"
                                        % (self.caller_line(), name, key, val, used))
                val = used
            vals.append(val)
        implicit = False
        if not inputs:
            if info.arity != 1:
                raise ProgramOpError("%s takes %d inputs, e.g. %s(x, y)" % (name, info.arity, name))
            inputs = [self.flow]
            implicit = True
        if len(inputs) != info.arity:
            raise ProgramOpError("%s takes %d input(s), got %d" % (name, info.arity, len(inputs)))
        return inputs, vals[0], vals[1], implicit

    def _compute(self, name, inputs, a, b, info):
        import api
        x = inputs[0] if info.arity == 1 else list(inputs)
        try:
            return api.apply(x, name, a, b, device=self.device)
        except ValueError as e:
            if "read-only" not in str(e):
                raise
            # op が入力へ書き込んでいた: 書ける写しで計算し直す(読み取り専用はメモの安全のため)
            xs = [np.array(v, copy=True) if isinstance(v, np.ndarray) else v for v in inputs]
            return api.apply(xs[0] if info.arity == 1 else xs, name, a, b, device=self.device)

    def call(self, name: str, args: tuple = (), a=None, b=None) -> Any:
        """op を 1 回呼ぶ(前置きの op 関数の本体)。記録・メモ化・流れの更新をする。"""
        info = op_table().get(name)
        if info is None:
            raise ProgramOpError("unknown op %r — see the Operators list (or op(\"name\", ...))" % (name,))
        line = self.caller_line()
        self.check_stop(line)
        inputs, a, b, implicit = self.bind(name, args, a, b)
        key = None
        if self.memo is not None and memo_eligible(name):
            fps = [fingerprint(v, self.memo) for v in inputs]
            if all(p is not None for p in fps):
                key = (name, a, b, tuple(fps), self.device)
        t0 = time.perf_counter()
        cached = False
        value = None
        if key is not None:
            cached, value = self.memo.get(key)
        if not cached:
            value = self._compute(name, inputs, a, b, info)
            if isinstance(value, np.generic):
                value = value.item()
            if isinstance(value, np.ndarray) and value.flags.writeable:
                value.flags.writeable = False
        ms = (time.perf_counter() - t0) * 1000.0
        if key is not None and not cached:
            self.memo.put(key, value, ms)
            if isinstance(value, np.ndarray):
                self.memo.remember(value, _key_digest(key))
        measured = info.out_sort in MEASURE_SORTS
        self._note_sort(value, info.out_sort)
        ctx = self._pipe_ctx
        rec = CallRecord(index=len(self.calls), op=name, a=a, b=b, line=line,
                         inputs=[("flow" if implicit else _kind_of(v, self), _shape_of(v)) for v in inputs],
                         out_sort=info.out_sort, out_shape=_shape_of(value), ms=round(ms, 3),
                         cached=cached, device=self.device, measured=measured,
                         pipeline=ctx[0] if ctx else None, pipeline_step=ctx[1] if ctx else None,
                         implicit_input=implicit, value=value)
        self.calls.append(rec)
        if not measured:
            self.flow, self.flow_sort, self.flow_line = value, info.out_sort, line
        return value

    def show(self, x):
        self.shown, self.shown_set, self.shown_line = x, True, self.caller_line()
        return x

    def directive(self, name: str, args: tuple):
        self.directives.append((name, args, self.caller_line()))

    def output(self) -> tuple:
        """最後に見せる値と、その出どころ(``"show line N"`` / ``"last op line N"`` / ``"input"``)。"""
        if self.shown_set:
            return self.shown, "show line %d" % self.shown_line
        for rec in reversed(self.calls):
            if not rec.measured and not rec.bypass:
                return rec.value, "last op line %d" % rec.line
        return self.input, "input"


#: いま記録している Recorder。前置きの関数はここへ記録する(Studio の実行中は Studio の物)。
_ACTIVE: contextvars.ContextVar = contextvars.ContextVar("studio_program_recorder", default=None)
_STANDALONE: Recorder | None = None


def active_recorder() -> Recorder:
    """前置きの関数が記録する先。Studio の実行中でなければ、単独で走るスクリプト用の Recorder。"""
    rec = _ACTIVE.get()
    if rec is not None:
        return rec
    global _STANDALONE
    if _STANDALONE is None:
        _STANDALONE = Recorder(memo=OpMemo())
    return _STANDALONE


# --------------------------------------------------------------------------- #
# パイプライン                                                                  #
# --------------------------------------------------------------------------- #
def _norm_stages(stages) -> list:
    out = []
    for i, s in enumerate(stages, 1):
        if isinstance(s, str):
            s = (s,)
        if not isinstance(s, (list, tuple)) or not 1 <= len(s) <= 3 or not isinstance(s[0], str):
            raise ProgramOpError("pipeline stage %d must be (\"op\", a, b), got %r" % (i, s))
        name = s[0]
        a = s[1] if len(s) > 1 else 0.5
        b = s[2] if len(s) > 2 else 0.5
        if name not in op_table():
            raise ProgramOpError("pipeline stage %d: unknown op %r" % (i, name))
        out.append((name, a, b))
    return out


class Pipeline:
    """段の列をひとまとまりで扱う。``p(x)`` は ``fullseye.run_pipeline(x, p.stages)`` と同じ意味・同じ結果。

    中の各段は記録に載り(``pipeline`` = 名前、``pipeline_step`` = 何段目)、メモ化も効く。
    段は ``("op", a, b)`` の組(``a``・``b`` は省略可)か op 名の文字列。op の関数は使わない
    (``gaussian(0.4)`` は「今の流れ」に掛ける実行なので、段の部品にすると紛らわしい)。
    ファイルから読んだ物(``load_pipeline``)は ``source`` に ``engine.PipelineFile`` を持ち、
    ``save`` はその形(切った段・directives・pinned)を保ったまま書く。"""

    def __init__(self, stages, name: str = "pipeline", source=None):
        self.stages = _norm_stages(stages)
        self.name = str(name)
        self.source = source

    def __repr__(self):
        return "Pipeline(%r, %d stages)" % (self.name, len(self.stages))

    def __len__(self):
        return len(self.stages)

    def __call__(self, x=None):
        return self.run(x)

    def _run(self, x, stages, keep_steps):
        import api
        rec = active_recorder()
        v = rec.flow if x is None else x
        if not stages:
            return [] if keep_steps else v
        ops_ = [api._resolve(n) for n, _a, _b in stages]
        api._check_chain_sorts(ops_, where="pipeline %r" % self.name)   # run_pipeline と同じ検査
        prev = rec._pipe_ctx
        steps = []
        try:
            for i, (n, a, b) in enumerate(stages):
                rec._pipe_ctx = (self.name, i + 1)
                v = _pipeline_stage(rec, v, n, a, b, first=(i == 0))
                steps.append(v)
        finally:
            rec._pipe_ctx = prev
        return steps if keep_steps else v

    def run(self, x=None, upto: int | None = None):
        """段 ``0..upto`` を走らせる(既定: 全段)。``x`` を省くと今の流れに掛ける。"""
        stages = self.stages
        if upto is not None:
            if isinstance(upto, bool) or not isinstance(upto, int) or not 0 <= upto < len(self.stages):
                raise ValueError("upto=%r: must be a stage index 0..%d" % (upto, len(self.stages) - 1))
            stages = self.stages[:upto + 1]
        return self._run(x, stages, False)

    def run_stepwise(self, x=None) -> list:
        """段ごとの結果の列(``FullseyeEngine.run_stepwise`` と同じ形)。"""
        return self._run(x, self.stages, True)

    def save(self, path: str) -> None:
        """Studio のパイプラインファイル(JSON)として書く。"""
        import engine
        src = self.source if self.source is not None else engine.PipelineFile(
            [list(s) for s in self.stages], name=self.name)
        src.save(path)


def _pipeline_stage(rec: Recorder, v, name, a, b, first):
    """パイプラインの 1 段 = ``api.run_pipeline(v, [(name, a, b)], coerce=first)``(Studio の _run_stage と同じ)。"""
    import api
    info = op_table()[name]
    line = rec.caller_line()
    rec.check_stop(line)
    key = None
    if rec.memo is not None and memo_eligible(name):
        fp = fingerprint(v, rec.memo)
        if fp is not None:
            key = ("pipe", name, float(a), float(b), fp, bool(first), rec.device)
    t0 = time.perf_counter()
    cached, value = (rec.memo.get(key) if key is not None else (False, None))
    if not cached:
        value = api.run_pipeline(v, [(name, a, b)], coerce=first, device=rec.device)
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, np.ndarray) and value.flags.writeable:
            value.flags.writeable = False
    ms = (time.perf_counter() - t0) * 1000.0
    if key is not None and not cached:
        rec.memo.put(key, value, ms)
        if isinstance(value, np.ndarray):
            rec.memo.remember(value, _key_digest(key))
    rec._note_sort(value, info.out_sort)
    ctx = rec._pipe_ctx
    rc = CallRecord(index=len(rec.calls), op=name, a=float(a), b=float(b), line=line,
                    inputs=[(_kind_of(v, rec), _shape_of(v))], out_sort=info.out_sort,
                    out_shape=_shape_of(value), ms=round(ms, 3), cached=cached, device=rec.device,
                    measured=info.out_sort in MEASURE_SORTS, pipeline=ctx[0], pipeline_step=ctx[1],
                    value=value)
    rec.calls.append(rc)
    if not rc.measured:
        rec.flow, rec.flow_sort, rec.flow_line = value, info.out_sort, line
    return value


#: プロジェクトのフォルダの中でパイプラインを置く場所(標準の並び images / pipelines / programs / params / results)。
#: 正本は別の担当の ``studio_project.py`` の種類の表になる予定で、それが入ったら :data:`PROJECT_SUBDIR_RESOLVER`
#: に「種類 → フォルダ名」を引く関数を差し込む(この段の差し込み口)。
PROJECT_PIPELINES_SUBDIR = "pipelines"
PROJECT_SUBDIR_RESOLVER: Callable[[str], str] | None = None


def pipeline_search_dirs(project_dir: str | None = None, program_dir: str | None = None) -> list:
    """``load_pipeline("x.json")`` の相対パスを探す場所の順: プロジェクトのフォルダが分かればその
    ``pipelines/`` → 実行中のプログラムのファイルの場所 → 作業フォルダ。"""
    out = []
    if project_dir:
        sub = PROJECT_SUBDIR_RESOLVER("pipeline") if PROJECT_SUBDIR_RESOLVER else PROJECT_PIPELINES_SUBDIR
        out.append(os.path.join(project_dir, sub))
    if program_dir:
        out.append(program_dir)
    out.append(os.getcwd())
    seen, uniq = set(), []
    for d in out:
        key = os.path.normcase(os.path.abspath(d))
        if key not in seen:
            seen.add(key)
            uniq.append(d)
    return uniq


def _load_pipeline(name: str) -> Pipeline:
    """``fullseye.load_pipeline`` と同じ物を読み、記録つきの :class:`Pipeline` にして返す。

    相対パスは :func:`pipeline_search_dirs` の順(プロジェクトの ``pipelines/`` → プログラムのファイルの場所 →
    作業フォルダ)、単独のスクリプトでは「スクリプトの場所 → 今の作業場所」の順に探す。"""
    import engine
    rec = active_recorder()
    pf = engine.load_pipeline(name, search_dirs=rec.search_dirs)
    return Pipeline([tuple(s) for s in pf.stages], name=pf.name, source=pf)


# --------------------------------------------------------------------------- #
# 前置きの名前空間                                                              #
# --------------------------------------------------------------------------- #
def _make_op_fn(name: str) -> Callable:
    def fn(*args, a=None, b=None):
        return active_recorder().call(name, args, a, b)
    fn.__name__ = name
    fn.__qualname__ = name
    fn.__doc__ = "Fullseye op %r: %s(x, a, b) — x omitted = the current flow." % (name, name)
    return fn


def _make_directive_fn(name: str) -> Callable:
    def fn(*args):
        active_recorder().directive(name, args)
    fn.__name__ = name
    return fn


def _op(name, *args, a=None, b=None):
    """名前で op を呼ぶ逃げ道(組み込み名・予約語と衝突する op、名前を変数で持つとき)。"""
    if not isinstance(name, str):
        raise ProgramOpError("op(name, ...): name must be a string, got %r" % (name,))
    return active_recorder().call(name, args, a, b)


def _show(x):
    """*x* を最後に画面へ出す値にする(最後の ``show`` が勝つ)。*x* を返す。"""
    return active_recorder().show(x)


def _pipeline(stages, name: str = "pipeline") -> Pipeline:
    """``pipeline([("gaussian", 0.4), ("otsu",)])`` — 段の列を組む。``p(img)`` で走る。"""
    return Pipeline(stages, name=name)


def _current_pipeline() -> Pipeline:
    """Studio の画面で組んだ今のパイプライン(従来のモードの段の列。切った段は除く)。"""
    rec = active_recorder()
    return Pipeline(rec.current_stages, name="current")


def _studio_input(path: str | None = None):
    """入力の画像。Studio の中では Studio の画像、単独では ``sys.argv[1]``(.npy はそのまま読む)。"""
    rec = active_recorder()
    if _ACTIVE.get() is not None and rec.input is not None:
        return rec.input
    if path is None:
        if len(sys.argv) < 2:
            raise SystemExit("usage: %s INPUT_IMAGE [OUTPUT]" % os.path.basename(sys.argv[0]))
        path = sys.argv[1]
    if path.lower().endswith(".npy"):
        arr = np.load(path, allow_pickle=False)
    else:
        import fullseye
        arr = fullseye.read_image(path)
    return rec.set_input(arr)


def _studio_set_current_pipeline(stages) -> None:
    """書き出したスクリプトが、Studio の今のパイプラインを埋め込むのに使う。"""
    active_recorder().current_stages = [tuple(s) for s in stages]


def _studio_output(path: str | None = None) -> str | None:
    """最後に見せる値を書く(単独のとき)。Studio の中では何もしない。``.npy`` ならそのまま保存。"""
    rec = active_recorder()
    if _ACTIVE.get() is not None:
        return None
    value, _src = rec.output()
    if path is None:
        path = sys.argv[2] if len(sys.argv) > 2 else "pipeline_result.png"
    if path.lower().endswith(".npy") or not isinstance(value, np.ndarray):
        if not path.lower().endswith(".npy"):
            path = os.path.splitext(path)[0] + ".npy"
        np.save(path, np.asarray(value), allow_pickle=False)
    else:
        import fullseye
        fullseye.write_image(path, value)
    print(path)
    return path


def prelude_namespace(include_heavy: bool = True) -> dict:
    """前置きが用意する名前の辞書(``from fullseye.studio_prelude import *`` で入る物と同じ)。"""
    ns: dict = {}
    for n in prelude_exports():
        ns[n] = _make_op_fn(n)
    try:
        for d in sorted(_directive_names()):
            if d.isidentifier() and not keyword.iskeyword(d):
                ns[d] = _make_directive_fn(d)
    except Exception:                                # noqa: BLE001
        pass
    ns.update(op=_op, show=_show, pipeline=_pipeline, current_pipeline=_current_pipeline,
              load_pipeline=_load_pipeline, studio_input=_studio_input, studio_output=_studio_output,
              studio_set_current_pipeline=_studio_set_current_pipeline, np=np,
              ui=_ui, show_window=_show_window)
    if include_heavy:
        import fullseye
        ns["fs"] = fullseye
    return ns


# --------------------------------------------------------------------------- #
# 記法の見分け                                                                  #
# --------------------------------------------------------------------------- #
_HDEV_ONLY = [
    (re.compile(r"^\*(?![A-Za-z_(])"), "'*' comment"),      # `*a, b = x`(Python の展開)は除く
    (re.compile(r"^(endif|endfor|endwhile)\b", re.I), "'end…' keyword"),
    (re.compile(r":="), "':=' assignment"),
    (re.compile(r"^(if|elseif|while|for)\b(?!.*:\s*(#.*)?$)", re.I), "block opener without ':'"),
    (re.compile(r"^else\s*$", re.I), "'else' without ':'"),
]
_PY_ONLY = [
    (re.compile(r"^(if|elif|while|for|def|class|with|try)\b.*:\s*(#.*)?$"), "block opener with ':'"),
    (re.compile(r"^(else|try|finally)\s*:\s*$"), "'else:'"),
    (re.compile(r"^[A-Za-z_][\w, ]*\s*(\+|-|\*|/)?=(?!=)"), "'x = …' assignment"),
    (re.compile(r"^(import|from)\s+\w"), "import"),
]


def _first_code_line(text: str):
    for n, raw in enumerate(text.splitlines(), 1):
        if raw.strip():
            return n, raw
    return 0, ""


def _is_plain_hdev_tree(tree: ast.Module) -> bool:
    """文が全部「名前(定数…)」か「名前」だけ = HDevelop 風としても同じ意味に読める。"""
    for st in tree.body:
        if not isinstance(st, ast.Expr):
            return False
        v = st.value
        if isinstance(v, ast.Name):
            continue
        if not (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and not v.keywords):
            return False
        directive = v.func.id.startswith(("dev_", "disp_", "set_system"))
        for arg in v.args:
            node = arg.operand if isinstance(arg, ast.UnaryOp) and isinstance(arg.op, (ast.USub, ast.UAdd)) else arg
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
                continue
            if isinstance(node, ast.Name) and (directive or node.id.lower() in ("nan", "inf", "infinity")):
                continue                              # HDevelop 風は float('nan') と読んで行番号つきで断る
            return False
    return True


def detect_syntax(text: str) -> tuple:
    """``(syntax, errors)``。syntax は ``"python"`` か ``"hdevelop"``。

    1. 最初の空でない行が ``# python`` / ``# hdevelop``(``# fullseye: …`` も可)ならそれ。
    2. ``ast.parse`` が通り、文が全部「op 名(定数…)」の形なら hdevelop(どちらで読んでも同じ段の列)。
       それ以外で通れば python。
    3. 通らないとき: HDevelop だけの印と Python だけの印が両方あれば「混ざっている」誤り(行番号つき)。
       Python だけの印があれば python(構文の誤りは実行時に行番号つきで出る)。それ以外は hdevelop。"""
    n, first = _first_code_line(text)
    m = _MARKER_RE.match(first)
    if m:
        return m.group(1).lower(), []
    # 1) 行の印を先に見る(`* note` や素の `endif` は Python としても構文が通ってしまうため)
    names = op_table()
    hd = py = None
    for ln, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        line_hd = None
        for rx, what in _HDEV_ONLY:
            if rx.search(s):
                line_hd = (ln, what)
                break
        else:
            w = re.match(r"([A-Za-z_]\w*)\s+([^\s(=])", s)
            if w and w.group(1) in names:
                line_hd = (ln, "terse 'op a b' call")
        if line_hd is not None:
            hd = hd or line_hd
            continue                                  # HDevelop の印の行は Python の印に数えない
        if py is None:
            for rx, what in _PY_ONLY:
                if rx.search(s):
                    py = (ln, what)
                    break
    if hd and py:
        return (SYNTAX_HDEVELOP, ["line %d: HDevelop-style %s and line %d: Python-style %s are mixed — "
                                  "one program uses one syntax (put '# python' or '# hdevelop' on line 1)"
                                  % (hd[0], hd[1], py[0], py[1])])
    if hd:
        return SYNTAX_HDEVELOP, []
    # 2) 印が無ければ構文木で決める
    try:
        tree = ast.parse(text, PROGRAM_FILENAME)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        tree = None
    if tree is not None:
        return (SYNTAX_HDEVELOP if _is_plain_hdev_tree(tree) else SYNTAX_PYTHON), []
    return (SYNTAX_PYTHON if py else SYNTAX_HDEVELOP), []


# --------------------------------------------------------------------------- #
# 実行の結果                                                                    #
# --------------------------------------------------------------------------- #
@dataclass
class VarInfo:
    """変数の表の 1 行。"""
    name: str
    kind: str
    shape: tuple | None
    summary: str


def describe_value(v, rec: Recorder | None = None) -> tuple:
    """``(kind, shape, summary)``。画像は型と形(``image 512×512 float64``)、小さい値は中身。"""
    kind = _kind_of(v, rec)
    shape = _shape_of(v)
    if isinstance(v, np.ndarray):
        dims = "×".join(str(s) for s in v.shape)
        if v.size <= 16:
            return kind, shape, "%s %s %s" % (kind, dims, np.array2string(v, precision=4, threshold=16))
        return kind, shape, "%s %s %s" % (kind, dims, v.dtype)
    if isinstance(v, (bool, int, float, np.generic, type(None))):
        return kind, None, repr(v.item() if isinstance(v, np.generic) else v)
    if isinstance(v, str):
        r = repr(v)
        return kind, None, r if len(r) <= 60 else r[:57] + "…'"
    if isinstance(v, (list, tuple, dict, set)):
        r = repr(v)
        head = "%s[%d]" % (type(v).__name__, len(v))
        return kind, None, head + (" " + r if len(r) <= 60 else "")
    if isinstance(v, Pipeline):
        return "pipeline", None, "%s: %s" % (v.name, " → ".join(s[0] for s in v.stages))
    if callable(v):
        return "function", None, getattr(v, "__name__", "function")
    return kind, None, type(v).__name__


@dataclass
class ProgramResult:
    """:func:`run_program` の結果。"""
    syntax: str
    ran: bool = False
    not_run_reason: str | None = None
    calls: list = field(default_factory=list)
    output: Any = None
    output_sort: str | None = None
    output_source: str = "input"
    variables: list = field(default_factory=list)
    values: dict = field(default_factory=dict)
    stdout: str = ""
    errors: list = field(default_factory=list)
    error_line: int | None = None
    stopped: str | None = None
    stopped_line: int | None = None
    clamped: list = field(default_factory=list)
    directives: list = field(default_factory=list)
    lines_run: int = 0
    elapsed_s: float = 0.0
    memo_hits: int = 0
    windows: list = field(default_factory=list)
    config: str = "debug"
    notes: list = field(default_factory=list)       # 誤りではない知らせ(「Release では止まらない」など)
    filename: str = PROGRAM_FILENAME                 # 実行したファイル(Program 欄なら <studio-program>)
    error_file: str | None = None                    # 例外の場所のファイル(error_line と組で (ファイル, 行))
    namespace: dict | None = None                    # 実行後の名前空間(対話の窓が evaluate で使う)

    @property
    def ok(self) -> bool:
        return self.ran and not self.errors and self.stopped is None

    def stages(self) -> list:
        """記録した段の列 ``[(op, a, b), …]``(実行の順。HDevelop 風では切った段も含む)。"""
        return [c.stage() for c in self.calls]

    def stage_lines(self) -> list:
        return [c.line for c in self.calls]


def _err_line_from_tb(tb, filename: str = PROGRAM_FILENAME) -> int | None:
    """トレースバックの中で、実行したファイル *filename* の最も深い枠の行番号。"""
    line = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == filename:
            line = tb.tb_lineno
        tb = tb.tb_next
    return line


def _err_location(tb, filename: str, user_dirs) -> tuple:
    """例外の場所 ``(ファイル, 行)``: 利用者のファイル(実行したファイル、または *user_dirs* の下の .py)の
    最も深い枠。複数ファイルのプロジェクトで、import した自分のモジュールの中の誤りもそこを指す。"""
    dirs = [os.path.normcase(os.path.abspath(d)) for d in user_dirs if d]
    best = (filename, None)
    while tb is not None:
        fn = tb.tb_frame.f_code.co_filename
        if fn == filename:
            best = (fn, tb.tb_lineno)
        elif not fn.startswith("<"):
            low = os.path.normcase(os.path.abspath(fn))
            if any(low.startswith(d + os.sep) for d in dirs):
                best = (fn, tb.tb_lineno)
        tb = tb.tb_next
    return best


class _Tracer:
    """``sys.settrace`` の本体: Program の枠の 'line' だけを見る。"""

    def __init__(self, time_limit_s, breakpoints, skip_hits, max_lines, stop_event,
                 filename: str = PROGRAM_FILENAME):
        self.filename = filename
        self.t0 = time.perf_counter()
        self.time_limit_s = time_limit_s
        self.breakpoints = set(int(b) for b in (breakpoints or ()))
        self.skip_hits = int(skip_hits)
        self.max_lines = max_lines
        self.stop_event = stop_event
        self.lines = 0
        self.hits = 0
        self.sticky: ProgramStopped | None = None

    def global_trace(self, frame, event, arg):
        if frame.f_code.co_filename != self.filename:
            return None
        return self.local_trace

    def local_trace(self, frame, event, arg):
        if event != "line":
            return self.local_trace
        ln = frame.f_lineno
        if self.sticky is not None:                  # 一度止めたら、捕まえられても次の行でまた止める
            raise ProgramStopped(self.sticky.reason, ln)
        if self.stop_event is not None and self.stop_event.is_set():
            self._stop("stop_requested", ln)
        if self.time_limit_s is not None and time.perf_counter() - self.t0 > self.time_limit_s:
            self._stop("time_limit", ln)
        if ln in self.breakpoints:
            self.hits += 1
            if self.hits > self.skip_hits:
                self._stop("breakpoint", ln)
        if self.max_lines is not None and self.lines >= self.max_lines:
            self._stop("step", ln)
        self.lines += 1
        return self.local_trace

    def _stop(self, reason, ln):
        self.sticky = ProgramStopped(reason, ln)
        raise self.sticky


def _hdev_run(text: str, image, names, result: ProgramResult, current_stages) -> ProgramResult:
    """従来の HDevelop 風: 今の解析器で段の列を作り、Studio の ``_run_stage`` と同じ呼び方で走らせる。"""
    import api
    import studio
    names = list(op_table()) if names is None else list(names)
    stages, errs, lines = studio.parse_hdev_program_lines(text, names)
    result.clamped = studio.hdev_last_clamped()
    if errs:
        result.errors = list(errs)
        m = re.match(r"line (\d+):", errs[0])
        result.error_line = int(m.group(1)) if m else None
        return result
    rec = Recorder()
    rec.current_stages = list(current_stages or [])
    if image is not None:
        v = rec.set_input(image)
    else:
        v = None
    t_all = time.perf_counter()
    for i, (st, ln) in enumerate(zip(stages, lines)):
        name, a, b = st[0], float(st[1]), float(st[2])
        bypass = studio._is_bypassed(st)
        info = op_table().get(name)
        out_sort = info.out_sort if info else "?"
        value, ms = None, 0.0
        if image is not None and not bypass:
            t0 = time.perf_counter()
            try:
                value = api.run_pipeline(v, [(name, a, b)], coerce=(i == 0))
            except Exception as e:                   # noqa: BLE001 -- 行番号つきで返す
                result.errors = ["line %d: %s failed: %s: %s" % (ln, name, type(e).__name__, e)]
                result.error_line = ln
                break
            ms = (time.perf_counter() - t0) * 1000.0
            v = value
        elif bypass:
            value = v
        rec.calls.append(CallRecord(index=i, op=name, a=a, b=b, line=ln, inputs=[(_kind_of(v), _shape_of(v))],
                                    out_sort=out_sort, out_shape=_shape_of(value), ms=round(ms, 3),
                                    cached=False, measured=False, bypass=bypass, value=value))
    result.calls = rec.calls
    result.ran = image is not None
    result.elapsed_s = time.perf_counter() - t_all
    result.output = v
    result.output_source = "last op line %d" % rec.calls[-1].line if rec.calls else "input"
    return result


#: プロジェクトのフォルダの中でプログラム(.py)を置く場所。``import`` の探し場所に一時的に足す。
PROJECT_PROGRAMS_SUBDIR = "programs"


def _push_sys_path(dirs) -> tuple:
    """*dirs* を ``sys.path`` の先頭へ一時的に足す。戻すための ``(足した物, 前からあった module 名)``。"""
    added = []
    for d in reversed([os.path.abspath(x) for x in dirs if x]):
        if d not in sys.path:
            sys.path.insert(0, d)
            added.append(d)
    return added, set(sys.modules)


def _pop_sys_path(token) -> None:
    """:func:`_push_sys_path` の逆。足した道を外し、その道から読み込んだ利用者のモジュールを ``sys.modules``
    から外す(前からあった物は残す)。"""
    added, before = token
    for d in added:
        try:
            sys.path.remove(d)
        except ValueError:
            pass
    if not added:
        return
    roots = [os.path.normcase(d) + os.sep for d in added]
    for name in [n for n in sys.modules if n not in before]:
        f = getattr(sys.modules.get(name), "__file__", None)
        if f and any(os.path.normcase(os.path.abspath(f)).startswith(r) for r in roots):
            del sys.modules[name]


def run_file(path: str, image, **kw) -> ProgramResult:
    """ファイルを実行の対象にする(:func:`run_program` の ``filename=`` と同じ)。本文はファイルから読む。"""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return run_program(text, image, filename=path, **kw)


def evaluate(source: str, namespace, *, trusted: bool = True) -> dict:
    """実行後の名前空間 *namespace*(``ProgramResult`` か ``ProgramResult.namespace``)で式か文を評価する
    (対話の窓の入口)。``{"value", "stdout", "error", "calls"}`` を返す。op の呼び出しはその実行の記録に足る。
    式なら値を返し、文(代入など)なら実行して ``value`` は None。誤りは ``"line N: Type: msg"``。"""
    ns = getattr(namespace, "namespace", namespace)
    if ns is None:
        return {"value": None, "stdout": "", "error": "no namespace: run the program first (keep_namespace=True)",
                "calls": []}
    if not trusted:
        return {"value": None, "stdout": "", "error": "not run: untrusted input", "calls": []}
    rec = ns.get("__studio_recorder__") or Recorder()
    out = io.StringIO()
    ns["print"] = _capture_print(out)
    n0 = len(rec.calls)
    token = _ACTIVE.set(rec)
    try:
        try:
            code = compile(source, "<studio-console>", "eval")
            is_expr = True
        except SyntaxError:
            code = compile(source, "<studio-console>", "exec")
            is_expr = False
        value = eval(code, ns) if is_expr else (exec(code, ns), None)[1]   # noqa: S307,S102 -- 利用者が打った物
        err = None
    except SyntaxError as e:
        value, err = None, "line %d: SyntaxError: %s" % (e.lineno or 1, e.msg)
    except Exception as e:                           # noqa: BLE001
        value = None
        err = "line %d: %s: %s" % (_err_line_from_tb(e.__traceback__, "<studio-console>") or 1, type(e).__name__, e)
    finally:
        _ACTIVE.reset(token)
    return {"value": value, "stdout": out.getvalue(), "error": err, "calls": rec.calls[n0:]}


def _capture_print(buf: io.StringIO) -> Callable:
    """プログラムの ``print`` を *buf* へ(``file=`` を渡した呼び出しはそのまま本物の print へ)。"""
    def print_(*args, sep=" ", end="\n", file=None, flush=False):
        if file is not None:
            return builtins.print(*args, sep=sep, end=end, file=file, flush=flush)
        buf.write((" " if sep is None else sep).join(str(a) for a in args) + ("\n" if end is None else end))
        return None
    print_.__name__ = "print"
    return print_


# --------------------------------------------------------------------------- #
# Qt の窓(GUI スレッドへの橋の差し込み口)                                       #
# --------------------------------------------------------------------------- #
#: Studio が差し込む GUI スレッドへの橋。``call(fn, *args) -> 結果``(GUI スレッドで実行して待つ)と
#: ``close(widget)`` を持つ物。この モジュールは Qt を import しない(橋は Studio 側の薄い層)。
GUI_BRIDGE = None

#: GUI スレッドで回すべきプログラム(Qt を直接 import する物)の印にする top-level のモジュール名。
QT_MODULES = ("PySide6", "PySide2", "PyQt5", "PyQt6", "shiboken6", "pyqtgraph", "qtpy")


def _qt_application():
    """もう import されている Qt の QApplication.instance()(Qt を新しく import しない)。無ければ None。"""
    for mod in ("PySide6.QtWidgets", "PyQt6.QtWidgets", "PyQt5.QtWidgets", "PySide2.QtWidgets"):
        m = sys.modules.get(mod)
        if m is not None:
            try:
                app = m.QApplication.instance()
            except Exception:                        # noqa: BLE001
                app = None
            if app is not None:
                return app
    return None


def _ui(fn: Callable, *args):
    """``fn(*args)`` を GUI スレッドで実行して結果を返す。Studio の中では橋(:data:`GUI_BRIDGE`)を通る。
    Studio の外では、QApplication があり今が main スレッドならそのまま呼ぶ。無ければ分かる文で断る。"""
    if GUI_BRIDGE is not None:
        return GUI_BRIDGE.call(fn, *args)
    if _qt_application() is None:
        raise RuntimeError("ui(): no Qt application is running — this needs Studio, or create one first "
                           "(app = QApplication.instance() or QApplication([]))")
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("ui(): Qt widgets can only be made on the GUI (main) thread, and no bridge is installed")
    return fn(*args)


def _show_window(make_widget: Callable):
    """``make_widget()`` で作った窓を GUI スレッドで出し、実行の記録に残す(実行の終わり・停止で閉じられる)。"""
    def make_and_show():
        w = make_widget()
        w.show()
        return w
    w = _ui(make_and_show)
    active_recorder().windows.append(w)
    return w


def close_program_windows(result_or_windows) -> int:
    """プログラムが :func:`show_window` で開いた窓を閉じる(実行の終わり・停止・Studio の終了で取り残さない)。
    閉じた数を返す。"""
    wins = getattr(result_or_windows, "windows", result_or_windows) or []
    n = 0
    for w in list(wins):
        try:
            if GUI_BRIDGE is not None:
                GUI_BRIDGE.call(w.close)
            else:
                w.close()
            n += 1
        except Exception:                            # noqa: BLE001 -- もう閉じている窓
            pass
    if isinstance(wins, list):
        wins.clear()
    return n


def needs_gui_thread(text: str) -> bool:
    """プログラムが Qt を直接 import するか(構文木で見る)。する物は GUI スレッドで回す(設計書 §17 の案 C)。"""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for x in ast.walk(tree):
        if isinstance(x, ast.Import):
            if any(al.name.split(".")[0] in QT_MODULES for al in x.names):
                return True
        elif isinstance(x, ast.ImportFrom) and x.module and x.module.split(".")[0] in QT_MODULES:
            return True
    return False


def _variables(ns: dict, base: dict, rec: Recorder) -> tuple:
    rows, values = [], {}
    for k, v in ns.items():
        if k.startswith("_") or k in ("__builtins__",):
            continue
        if k in base and base[k] is v:
            continue                                 # 前置きの名前(書き換えていない物)
        if type(v).__name__ == "module":
            continue
        kind, shape, summ = describe_value(v, rec)
        rows.append(VarInfo(k, kind, shape, summ))
        values[k] = v
    return rows, values


def run_program(text: str, image=None, *, trusted: bool = True, syntax: str | None = None,
                memo: OpMemo | None = None, names: Sequence[str] | None = None,
                time_limit_s: float | None = DEFAULT_TIME_LIMIT_S, breakpoints: Iterable[int] = (),
                skip_hits: int = 0, max_lines: int | None = None, stop_event: threading.Event | None = None,
                current_stages: Sequence | None = None, device: str = "cpu",
                program_dir: str | None = None, project_dir: str | None = None,
                config: str = "debug", filename: str | None = None,
                keep_namespace: bool = True) -> ProgramResult:
    """Program 欄の文面を走らせる。

    * HDevelop 風: 今の ``studio.parse_hdev_program_lines`` の段の列を、Studio と同じ呼び方で走らせる
      (``image`` が None なら解析だけ)。信頼の確認は要らない(任意のコードを含まない)。
    * Python 風: ``trusted`` が False なら実行せずに理由を返す。True なら ``compile`` して前置きの
      名前空間で ``exec`` し、settrace で ``breakpoints``(``skip_hits`` 回までは通過)・``max_lines``
      (1 行実行)・``stop_event``・``time_limit_s`` を扱う。``memo`` を渡すと op の呼び出しを
      実行をまたいでメモ化する。``current_stages`` は ``current_pipeline()`` が返す段の列。
    * ``config``: ``"debug"``(既定。行フックあり: ブレークポイント・1 行実行・行の境目で止める)か
      ``"release"``(行フックなし。止めるのは op の呼び出しの境目と時間の上限だけ。ブレークポイントと
      1 行実行は効かず、渡されていれば ``notes`` に 1 行入れる)。記録・メモ化・結果は両方で同じ。
    * ``filename``: 実行の対象のファイル(Program 欄なら省く = ``<studio-program>``)。トレース・例外の行は
      このファイルの物。実行の間だけ、そのファイルの場所(``program_dir``、省けばファイルの場所)と
      プロジェクトの ``programs/`` を ``sys.path`` の先頭に足し、終わったら戻す(複数ファイルの
      プロジェクトで ``import`` が効く)。その間に読み込んだ利用者のモジュールは実行の後に
      ``sys.modules`` から外す(直して走り直すと新しい中身が読まれる)。
    * ``keep_namespace``: 実行後の名前空間を ``ProgramResult.namespace`` に残す(:func:`evaluate` が使う)。"""
    if config not in CONFIGS:
        raise ValueError("config must be one of %s, got %r" % (", ".join(CONFIGS), config))
    syn, errs = (syntax, []) if syntax else detect_syntax(text)
    result = ProgramResult(syntax=syn, config=config)
    if errs:
        result.errors = errs
        m = re.match(r"line (\d+):", errs[0])
        result.error_line = int(m.group(1)) if m else None
        return result
    if syn == SYNTAX_HDEVELOP:
        return _hdev_run(text, image, names, result, current_stages)
    if not trusted:
        result.not_run_reason = ("not run: this Python program came from a file, project or automation and "
                                 "will execute on this PC — confirm it first (digest %s)" % program_digest(text)[:12])
        return result
    if image is None:
        result.errors = ["line 1: a Python program needs an input image"]
        result.error_line = 1
        return result
    code_name = os.path.abspath(filename) if filename else PROGRAM_FILENAME
    result.filename = code_name
    if filename and program_dir is None:
        program_dir = os.path.dirname(code_name)
    try:
        code = compile(text, code_name, "exec")
    except SyntaxError as e:
        result.errors = ["line %d: SyntaxError: %s" % (e.lineno or 0, e.msg)]
        result.error_line = e.lineno
        return result
    except (ValueError, MemoryError, RecursionError) as e:
        result.errors = ["line 1: cannot compile: %s" % e]
        result.error_line = 1
        return result
    rec = Recorder(memo=memo, device=device, program_filename=code_name)
    rec.current_stages = list(current_stages or [])
    rec.search_dirs = pipeline_search_dirs(project_dir=project_dir, program_dir=program_dir)
    inp = rec.set_input(image)
    base = prelude_namespace()
    ns = dict(base)
    ns.update(__name__="__studio_program__", __builtins__=builtins, img=inp, image=inp)
    if filename:
        ns["__file__"] = code_name
    ns["__studio_recorder__"] = rec
    tracer = _Tracer(time_limit_s, breakpoints, skip_hits, max_lines, stop_event, filename=code_name)
    user_dirs = [d for d in (program_dir, os.path.join(project_dir, PROJECT_PROGRAMS_SUBDIR) if project_dir else None)
                 if d]
    release = config == "release"
    if release:
        rec.stop_event = stop_event
        rec.time_limit_s = time_limit_s
        rec.deadline = None if time_limit_s is None else time.perf_counter() + time_limit_s
        bps = sorted(set(int(b) for b in (breakpoints or ())))
        if bps:
            result.notes.append("Release does not stop at breakpoints (lines %s) — switch to Debug to use them"
                                % ", ".join(str(b) for b in bps))
        if max_lines is not None:
            result.notes.append("Release cannot step line by line — switch to Debug")
    out = io.StringIO()
    # print はプログラムの名前空間の中だけで取り込む(sys.stdout を差し替えると、作業スレッドで回している間に
    # Studio 本体や他のスレッドの出力まで取り込んでしまう)。file= を渡した print はそのまま。
    ns["print"] = _capture_print(out)
    hits0 = memo.hits if memo is not None else 0
    token = _ACTIVE.set(rec)                         # contextvar = スレッドごと(どのスレッドから呼ばれても混ざらない)
    old_trace = sys.gettrace()                       # settrace も呼んだスレッドだけに効く
    path_token = _push_sys_path(user_dirs)
    t0 = time.perf_counter()
    try:
        if not release:
            sys.settrace(tracer.global_trace)
        try:
            exec(code, ns)                           # noqa: S102 -- 本物の Python(trusted のときだけ)
        finally:
            if not release:
                sys.settrace(old_trace)
        result.ran = True
    except ProgramStopped as e:
        result.ran = True
        result.stopped, result.stopped_line = e.reason, e.line
        if e.reason == "time_limit":
            result.errors = ["line %d: stopped: time limit %.3g s exceeded" % (e.line, time_limit_s)]
            result.error_line = e.line
        elif e.reason == "stop_requested":
            result.errors = ["line %d: stopped on request" % e.line]
            result.error_line = e.line
    except SystemExit as e:
        result.ran = True
        ln = _err_line_from_tb(e.__traceback__, code_name) or 0
        result.errors = ["line %d: the program called exit(%r)" % (ln, e.code)]
        result.error_line = ln
    except Exception as e:                           # noqa: BLE001 -- 行番号つきで返す
        result.ran = True
        result.error_file, deep_line = _err_location(e.__traceback__, code_name, user_dirs)
        ln = _err_line_from_tb(e.__traceback__, code_name) or 0
        if result.error_file != code_name and deep_line is not None:
            result.notes.append("the error is in %s line %d (called from line %d)"
                                % (result.error_file, deep_line, ln))
        else:
            result.error_file = code_name
        msg = "line %d: %s: %s" % (ln, type(e).__name__, e)
        if isinstance(e, ModuleNotFoundError) and getattr(e, "name", None):
            # 入っていない物は ImportError をそのまま見せ、入れ方を 1 行で言う(Studio と同じ Python へ)
            msg += " — install it into Studio's Python: \"%s\" -m pip install %s" % (sys.executable,
                                                                                     e.name.split(".")[0])
        result.errors = [msg]
        result.error_line = ln
    finally:
        _ACTIVE.reset(token)
        if sys.gettrace() is not old_trace:
            sys.settrace(old_trace)
        _pop_sys_path(path_token)
    result.elapsed_s = time.perf_counter() - t0
    result.lines_run = tracer.lines
    result.stdout = out.getvalue()
    result.calls = rec.calls
    result.clamped = rec.clamped
    result.directives = rec.directives
    result.windows = rec.windows
    result.output, result.output_source = rec.output()
    result.output_sort = rec.sort_of(result.output) if isinstance(result.output, np.ndarray) else _kind_of(result.output)
    result.variables, result.values = _variables(ns, base, rec)
    if keep_namespace:
        result.namespace = ns
    result.memo_hits = (memo.hits - hits0) if memo is not None else 0
    return result


# --------------------------------------------------------------------------- #
# 信頼                                                                          #
# --------------------------------------------------------------------------- #
def program_digest(text: str) -> str:
    """プログラムの文面の SHA-256(改行を \\n に揃えてから)。確認の状態はこの値で覚える。"""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


class TrustStore:
    """「この PC で実行してよい」と確認したプログラムの digest の集合(VS Code の Workspace Trust と同じ考え)。

    ``path`` を渡すと JSON に残す。手で打ったプログラムは ``origin="typed"`` で常に信頼する。
    ファイル・プロジェクト・MCP・自動操作から来た物は、確認が済んだ digest だけを信頼する。"""

    TRUSTED_ORIGINS = frozenset({"typed"})

    def __init__(self, path: str | None = None):
        self.path = path
        self._d: set = set()
        if path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    self._d = set(json.load(fh).get("trusted", []))
            except (OSError, ValueError):
                self._d = set()                      # 壊れた台帳は空 = 信頼しない側

    def is_trusted(self, text: str, origin: str) -> bool:
        if origin in self.TRUSTED_ORIGINS:
            return True
        return program_digest(text) in self._d

    def trust(self, text: str) -> str:
        d = program_digest(text)
        self._d.add(d)
        if self.path:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump({"trusted": sorted(self._d)}, fh)
        return d


# --------------------------------------------------------------------------- #
# HDevelop 風 <-> Python 風                                                     #
# --------------------------------------------------------------------------- #
def _py_cond(cond: str) -> str:
    """HDevelop の定数の条件を Python の式へ。``studio._hdev_eval_cond`` と同じ真偽になる時だけ式を残す。"""
    import studio
    want = studio._hdev_eval_cond(cond)
    expr = cond.strip().replace("#", "!=")
    expr = re.sub(r"(?<![<>=!])=(?!=)", "==", expr)
    try:
        tree = ast.parse(expr, mode="eval")
        ok_nodes = (ast.Expression, ast.Compare, ast.Constant, ast.UnaryOp, ast.USub, ast.UAdd,
                    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Load)
        if all(isinstance(n, ok_nodes) for n in ast.walk(tree)):
            got = bool(eval(compile(tree, "<cond>", "eval"), {"__builtins__": {}}, {}))  # noqa: S307 -- 数の定数だけ
            if got == want:
                return expr + ":"
    except Exception:                                # noqa: BLE001
        pass
    return "%s:  # was: if %s" % (want, cond.strip())


def _py_call(name: str) -> str:
    return name if name not in prelude_collisions([name]) else 'op, "%s"' % name


def hdev_to_python(text: str, names: Sequence[str] | None = None) -> tuple:
    """HDevelop 風を Python 風へ書き換える。``(python_text, errors)``。**行の数と位置は変えない**
    (行 N の段は書き換えた後も行 N にある。ブレークポイントがそのまま使える)。

    ``op (a, b)`` → ``img = op(img, a, b)`` / ``for N`` → ``for _ in range(N):`` /
    ``if c`` → ``if c:``(``=`` → ``==``、``#`` → ``!=``。数の比較でなければ HDevelop と同じ真偽の定数)/
    ``else`` → ``else:`` / ``endfor``・``endif`` → コメント / ``*`` コメント → ``#`` /
    ``# bypassed: …`` はそのまま(Python 風に切った段は無い)/ 表示指示は呼び出しのまま。
    中身の無いブロックは開く行に ``: pass`` を付ける。"""
    import studio
    names = list(op_table()) if names is None else list(names)
    _st, errs, _ln = studio.parse_hdev_program_lines(text, names)
    if errs:
        return "", list(errs)
    raw_lines = text.splitlines()
    out = list(raw_lines)
    depth = 0
    stack = []                                       # [(kind, out_index, has_body)]
    nameset = set(names)
    for i, raw in enumerate(raw_lines):
        s = raw.strip()
        ind = "    " * depth
        if not s:
            out[i] = ""
            continue
        if s.startswith("*"):
            out[i] = ind + "#" + s[1:]
            continue
        if re.match(r"#\s*bypassed:", s) or s.startswith("#"):
            out[i] = ind + s
            continue
        code = studio._hdev_strip_comment(raw)
        tail = s[len(code):].strip() if s.startswith(code) else ""
        tail = ("  " + tail) if tail else ""
        head = code.split()[0].lower()
        if head in ("for", "if") and stack:
            stack[-1][2] = True                      # 入れ子のブロックも外のブロックの中身
        if head == "for":
            count = int(float(code.split()[1]))
            out[i] = ind + "for _ in range(%d):" % count + tail
            stack.append(["for", i, False])
            depth += 1
        elif head == "if":
            out[i] = ind + "if %s" % _py_cond(code[2:]) + tail
            stack.append(["if", i, False])
            depth += 1
        elif head == "else":
            top = stack[-1]
            if not top[2]:
                out[top[1]] = _add_pass(out[top[1]])
            top[1], top[2] = i, False
            out[i] = "    " * (depth - 1) + "else:" + tail
        elif head in ("endfor", "endif"):
            top = stack.pop()
            if not top[2]:
                out[top[1]] = _add_pass(out[top[1]])
            depth -= 1
            out[i] = "    " * depth + "# " + head + tail
        else:
            if stack:
                stack[-1][2] = True
            op_head = studio._dev_op_head(code)
            if op_head.startswith(("dev_", "disp_")) or op_head in studio._CONFIG_DIRECTIVES:
                c = code if "(" in code else code + " ()"
                try:
                    call = ast.parse(c.strip(), mode="eval").body
                    if isinstance(call, ast.Call) and any(isinstance(x, ast.Name) for x in call.args):
                        # HDevelop の素の語の引数(`dev_set_lut (gray)`)は Python では文字列にする
                        call.args = [ast.Constant(x.id) if isinstance(x, ast.Name) else x for x in call.args]
                        c = ast.unparse(call)
                except SyntaxError:
                    return "", ["line %d: cannot convert the directive %r" % (i + 1, code)]
                out[i] = ind + c + tail
                continue
            if "(" in code and code.endswith(")"):
                name = code[:code.index("(")].strip()
                inner = code[code.index("(") + 1:-1].strip()
                args = [p.strip() for p in inner.split(",")] if inner else []
            else:
                parts = code.split()
                name, args = parts[0], parts[1:]
            if name not in nameset:
                return "", ["line %d: unknown op '%s'" % (i + 1, name)]
            vals = [repr(float(x)) if x != "" else "0.5" for x in args[:2]]
            target = "op(%r, img%s)" % (name, "".join(", " + v for v in vals)) \
                if name in prelude_collisions([name]) else "%s(img%s)" % (name, "".join(", " + v for v in vals))
            out[i] = ind + "img = " + target + tail
    if stack:
        return "", ["line %d: block not closed" % (stack[-1][1] + 1)]
    first = _first_code_line(text)[1]
    body = "\n".join(out)
    if _MARKER_RE.match(first or ""):
        return body, ["line 1: has a '# hdevelop' marker — remove it before converting"]
    return body, []


def _add_pass(line: str) -> str:
    code, sep, comment = line.partition("  #")
    return code + " pass" + (sep + comment if sep else "")


def python_to_hdev(text: str) -> tuple:
    """分岐・ループの無い Python 風を、従来の段の列(HDevelop 風)へ戻す。``(hdev_text, errors)``。

    戻せる文: ``img = op(img, 定数…)``(毎行同じ変数)・入力を省いた ``op(定数…)``・表示指示の呼び出し・
    コメント・空行・最後の ``show(img)``。測るだけの op は最後の文でだけ許す(途中にあると、従来のモードでは
    次の段がその数を受け取り、Python 風では画像を受け取るので意味が変わる)。戻せない文は行番号つきの理由。"""
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return "", ["line %d: SyntaxError: %s" % (e.lineno or 0, e.msg)]
    lines = text.splitlines()
    out = list(lines)
    errs = []
    var = None
    tab = op_table()
    code_lines = set()
    stmts = tree.body
    for k, st in enumerate(stmts):
        ln = st.lineno
        if st.end_lineno != st.lineno:
            errs.append("line %d: a statement spanning several lines cannot go back" % ln)
            continue
        code_lines.add(ln)
        call, target = None, None
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            target, call = st.targets[0].id, st.value
        elif isinstance(st, ast.Expr):
            call = st.value
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            errs.append("line %d: only op calls can go back to the stage list (%s)" % (ln, type(st).__name__))
            continue
        fname = call.func.id
        args = list(call.args)
        if fname == "op" and args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
            fname = args[0].value
            args = args[1:]
        if fname == "show" and k == len(stmts) - 1 and target is None:
            out[ln - 1] = "* " + lines[ln - 1].strip()
            continue
        if fname.startswith(("dev_", "disp_", "set_system")) and target is None:
            out[ln - 1] = lines[ln - 1].strip()
            continue
        if fname not in tab:
            errs.append("line %d: '%s' is not an op" % (ln, fname))
            continue
        if args and isinstance(args[0], ast.Name):
            if target is None or args[0].id != target:
                errs.append("line %d: the input must be the variable the result is assigned to" % ln)
                continue
            if var is None:
                var = target
            if target != var:
                errs.append("line %d: uses '%s' but earlier lines use '%s'" % (ln, target, var))
                continue
            args = args[1:]
        elif target is not None:
            errs.append("line %d: give the input explicitly: %s = %s(%s, …)" % (ln, target, fname, target))
            continue
        knobs = []
        for a in args:
            node = a.operand if isinstance(a, ast.UnaryOp) and isinstance(a.op, ast.USub) else a
            if not (isinstance(node, ast.Constant) and _is_knob(node.value)):
                errs.append("line %d: knobs must be number literals to go back" % ln)
                break
            knobs.append(-float(node.value) if node is not a else float(node.value))
        else:
            kw = {k.arg: k.value for k in call.keywords}
            for key in ("a", "b"):
                if key in kw:
                    node = kw[key]
                    if not (isinstance(node, ast.Constant) and _is_knob(node.value)):
                        errs.append("line %d: knobs must be number literals to go back" % ln)
                    else:
                        while len(knobs) < (1 if key == "a" else 2):
                            knobs.append(0.5)
                        knobs[0 if key == "a" else 1] = float(node.value)
            if set(kw) - {"a", "b"}:
                errs.append("line %d: unknown keyword" % ln)
            if tab[fname].out_sort in MEASURE_SORTS and k != len(stmts) - 1:
                errs.append("line %d: the measuring op %s must be the last statement to go back" % (ln, fname))
            if tab[fname].arity != 1:
                errs.append("line %d: %s takes %d inputs; the stage list has one flow" % (ln, fname, tab[fname].arity))
            out[ln - 1] = "%s (%s)" % (fname, ", ".join(repr(x) for x in knobs)) if knobs else "%s ()" % fname
    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if i not in code_lines and s and not s.startswith("#"):
            pass                                     # 続きの行は上で拒否済み
        if _MARKER_RE.match(s) and s.lower().endswith("python"):
            out[i - 1] = "* (was Python)"
    if errs:
        return "", errs
    return "\n".join(out), []


# --------------------------------------------------------------------------- #
# 書き出し                                                                      #
# --------------------------------------------------------------------------- #
def export_python_script(text: str, current_stages: Sequence | None = None) -> str:
    """Python 風のプログラムを、単独で走るスクリプトにする(前置きの import + 文面 + 入出力の数行)。

    ``py -3.11 script.py INPUT [OUTPUT]`` で、Studio の実行系と同じ結果になる(同じ記録層を通る)。
    HDevelop 風は ``PipelineModel.export_standalone`` の担当なので ValueError。"""
    syn, errs = detect_syntax(text)
    if errs:
        raise ValueError(errs[0])
    if syn != SYNTAX_PYTHON:
        raise ValueError("an HDevelop-style program is exported by the pipeline exporter (export_standalone)")
    head = ["# Fullseye Studio Program (Python) — exported.",
            "# Run: py -3.11 this.py INPUT_IMAGE [OUTPUT]   (.npy in = the array as is, .npy out = exact values)",
            "from fullseye.studio_prelude import *   # op functions, img, show, op, pipeline, np, fs",
            ""]
    if current_stages:
        head.append("studio_set_current_pipeline(%r)" % ([tuple(s[:3]) for s in current_stages],))
    head += ["img = image = studio_input()",
             "# ---- Program ----"]
    tail = ["# ---- end of Program ----", "studio_output()"]
    return "\n".join(head) + "\n" + text.rstrip("\n") + "\n" + "\n".join(tail) + "\n"


# --------------------------------------------------------------------------- #
# 助言(構文木を見る。実行結果は変えない)                                       #
# --------------------------------------------------------------------------- #
@dataclass
class Advice:
    """構文木から読めた改善の提案。``fixed_text`` は「適用」を押したときの文面(出せない時は None)。"""
    line: int
    kind: str              # "unused_result" / "loop_invariant" / "duplicate" / "type_mismatch"
    message: str
    fixed_text: str | None = None


_DYNAMIC_NAMES = frozenset({"globals", "locals", "vars", "eval", "exec", "compile", "setattr", "getattr",
                            "delattr", "__import__"})


def _names_loaded(nodes) -> set:
    out = set()
    for n in nodes:
        for x in ast.walk(n):
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load):
                out.add(x.id)
    return out


def _names_stored(nodes) -> set:
    out = set()
    for n in nodes:
        for x in ast.walk(n):
            if isinstance(x, ast.Name) and isinstance(x.ctx, (ast.Store, ast.Del)):
                out.add(x.id)
            elif isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.add(x.name)
            elif isinstance(x, (ast.Import, ast.ImportFrom)):
                for al in x.names:
                    out.add((al.asname or al.name).split(".")[0])
    return out


def advise_program(text: str) -> list:
    """Python 風のプログラムの構文木から、行番号つきの助言を返す。誤った助言を出さない側に倒す:

    * プログラムが ``globals``・``exec`` など動的に名前を触る物・``global``・``del``・``import`` を使うなら何も出さない。
    * 関数・クラスの中は見ない。op の名前を上書きしている変数は op と見なさない。
    * (a) 結果が使われない op: 測るだけの op の結果を、どこからも読まない変数に入れている時だけ
      (画像の op は流れと最後の表示を変えるので出さない)。トップレベルの 1 行の文なら消した文面を返す。
    * (b) ループの中で毎回同じ引数の op: 引数が定数か、ループの中で代入されない変数だけ、入力を省いていない、
      メモ化できる op、ループの中に属性の呼び出し・添字への代入・関数の呼び出し(op 以外)が無い時。
    * (c) 同じ op の呼び出しが同じブロックに 2 回: 間で引数の変数が代入されない、入力を省いていない、メモ化できる op。
    * (d) 型の合わない繋ぎ: 1 回しか代入されない変数の sort が、受ける op の入力 sort と合わない時。"""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    tab = op_table()
    qt = _qt_binding_advice(tree)
    for x in ast.walk(tree):
        if isinstance(x, (ast.Global, ast.Nonlocal, ast.Delete, ast.Import, ast.ImportFrom)):
            return qt
        if isinstance(x, ast.Name) and x.id in _DYNAMIC_NAMES:
            return qt
    shadowed = _names_stored(tree.body)
    ops_ok = {n for n in tab if n not in shadowed}

    def op_of(call):
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
            if call.func.id in ops_ok:
                return call.func.id
            if call.func.id == "op" and "op" not in shadowed and call.args and \
                    isinstance(call.args[0], ast.Constant) and call.args[0].value in ops_ok:
                return call.args[0].value
        return None

    def explicit_input(call):
        args = call.args[1:] if call.func.id == "op" else call.args
        return bool(args) and not (isinstance(args[0], ast.Constant) or
                                   (isinstance(args[0], ast.UnaryOp) and isinstance(args[0].operand, ast.Constant)))

    def simple_args(call):
        for a in list(call.args) + [k.value for k in call.keywords]:
            if isinstance(a, ast.UnaryOp):
                a = a.operand
            if not isinstance(a, (ast.Constant, ast.Name)):
                return False
        return True

    advice: list[Advice] = []
    lines = text.splitlines()
    all_loads = _names_loaded(tree.body)

    # (a) 結果が使われない、測るだけの op
    def scan_block(body, top):
        for st in body:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                name = op_of(st.value)
                tgt = st.targets[0].id
                if name and tab[name].out_sort in MEASURE_SORTS and tgt not in all_loads:
                    fixed = None
                    if top and st.lineno == st.end_lineno:
                        fixed = "\n".join(l for i, l in enumerate(lines, 1) if i != st.lineno)
                    advice.append(Advice(st.lineno, "unused_result",
                                         "the result of %s (%s) is never read — the measurement can be removed"
                                         % (name, tgt), fixed))
            for sub in ("body", "orelse"):
                if isinstance(st, (ast.If, ast.For, ast.While)) and getattr(st, sub, None):
                    scan_block(getattr(st, sub), False)
    scan_block(tree.body, True)

    # (b) ループの中で毎回同じ引数の op(関数の中のループは見ない。中の節の集合を 1 回だけ作る)
    in_func = {id(n) for f in ast.walk(tree) if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
               for n in ast.walk(f) if n is not f}
    for loop in ast.walk(tree):
        if not isinstance(loop, (ast.For, ast.While)):
            continue
        if id(loop) in in_func:
            continue
        stored = _names_stored(loop.body) | (_names_stored([loop.target]) if isinstance(loop, ast.For) else set())
        risky = False
        for x in ast.walk(loop):
            if isinstance(x, ast.Attribute) or (isinstance(x, ast.Subscript) and isinstance(x.ctx, ast.Store)):
                risky = True
            if isinstance(x, ast.Call) and op_of(x) is None and not (
                    isinstance(x.func, ast.Name) and x.func.id in ("range", "len", "abs", "min", "max", "round",
                                                                   "int", "float", "print", "show")):
                risky = True
        if risky:
            continue
        for x in ast.walk(loop):
            name = op_of(x)
            if not name or not explicit_input(x) or not simple_args(x) or not memo_eligible(name):
                continue
            used = _names_loaded([x])
            if used & stored:
                continue
            advice.append(Advice(x.lineno, "loop_invariant",
                                 "%s is called with the same arguments on every pass of the loop at line %d — "
                                 "compute it once before the loop (the memo already avoids recomputing it)"
                                 % (name, loop.lineno)))

    # (c) 同じブロックの中の重複
    def dup_block(body):
        seen = {}
        for st in body:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            calls = [x for x in ast.walk(st) if op_of(x)] if not isinstance(st, (ast.If, ast.For, ast.While)) else []
            for c in calls:
                name = op_of(c)
                if not explicit_input(c) or not simple_args(c) or not memo_eligible(name):
                    continue
                key = ast.dump(c)
                if key in seen:
                    advice.append(Advice(c.lineno, "duplicate",
                                         "same %s call as line %d — reuse that result" % (name, seen[key][0])))
                else:
                    seen[key] = (c.lineno, _names_loaded([c]))
            stored = _names_stored([st])
            seen = {k: v for k, v in seen.items() if not (v[1] & stored)}
            if isinstance(st, (ast.If, ast.For, ast.While)):
                dup_block(st.body)
                dup_block(st.orelse)
                seen = {k: v for k, v in seen.items() if not (v[1] & _names_stored([st]))}
    dup_block(tree.body)

    # (d) 型の合わない繋ぎ(1 回しか代入されない変数だけ)
    import engine
    assign_count: dict = {}
    for x in ast.walk(tree):
        if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store):
            assign_count[x.id] = assign_count.get(x.id, 0) + 1
    sorts = {}
    if assign_count.get("img", 0) == 0:
        sorts["img"] = "image"
    if assign_count.get("image", 0) == 0:
        sorts["image"] = "image"
    for st in tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            name = op_of(st.value)
            if name and assign_count.get(st.targets[0].id) == 1:
                sorts[st.targets[0].id] = tab[name].out_sort
    for x in ast.walk(tree):
        name = op_of(x)
        if not name or tab[name].arity != 1 or not explicit_input(x):
            continue
        first = (x.args[1:] if x.func.id == "op" else x.args)[0]
        if isinstance(first, ast.Name) and first.id in sorts:
            have, want = sorts[first.id], tab[name].in_sort
            if not engine._compatible(have, want) and not (have == "image" and want == "region"):
                # 画像 → 領域は api.apply の coerce が 0.5 で二値にする(誤った助言にしない)
                advice.append(Advice(x.lineno, "type_mismatch",
                                     "%s takes %s but %s is %s — convert first" % (name, want, first.id, have)))
    advice += qt
    advice.sort(key=lambda a: (a.line, a.kind))
    return advice


def _qt_binding_advice(tree) -> list:
    """Studio は PySide6 で動いている。PyQt5 / PyQt6 / PySide2 を同じプロセスへ import すると落ちることがある
    (同じ Qt の型を 2 つの束縛が持つ)。止めはせず、行番号つきで知らせる。"""
    out = []
    for x in ast.walk(tree):
        names = []
        if isinstance(x, ast.Import):
            names = [al.name.split(".")[0] for al in x.names]
        elif isinstance(x, ast.ImportFrom) and x.module:
            names = [x.module.split(".")[0]]
        for n in names:
            if n in ("PyQt5", "PyQt6", "PySide2"):
                out.append(Advice(x.lineno, "qt_binding_mix",
                                  "%s in the same process as Studio's PySide6 can crash — use PySide6 "
                                  "(the APIs are nearly the same)" % n))
    return out


# --------------------------------------------------------------------------- #
# 書いている最中の指摘(実行しない): check_program                                #
# --------------------------------------------------------------------------- #
@dataclass
class Problem:
    """エディタの波線と Problems の欄に出す 1 件。形は固定(別の枝のエディタ機能が読む)。

    * ``line`` / ``end_line`` は 1 始まり、``col`` / ``end_col`` は 0 始まり(``ast`` と同じ。文字単位)。
    * ``severity``: ``"error"`` / ``"warning"`` / ``"hint"``。
    * ``code``: 安定した短い識別子(訳の鍵。``message`` / ``hint`` は英語が正で、Studio が ``tr()`` を通す)。
    * ``params``: 文に埋め込んだ値(訳した文に埋め直すため)。
    * ``fix``: 機械で直せるときだけ ``{"line", "col", "end_line", "end_col", "text"}``(その範囲を ``text`` に置き換える)。"""
    line: int
    col: int
    end_line: int
    end_col: int
    severity: str
    code: str
    message: str
    hint: str = ""
    fix: dict | None = None
    params: dict = field(default_factory=dict)


#: 全角の記号 → ASCII(日本語の入力のまま打った括弧・カンマ・引用符・空白)。文字列とコメントの中は対象外。
FULLWIDTH = {"（": "(", "）": ")", "［": "[", "］": "]", "｛": "{", "｝": "}", "，": ",", "、": ",",
             "：": ":", "；": ";", "＝": "=", "＋": "+", "－": "-", "＊": "*", "／": "/", "＜": "<",
             "＞": ">", "＂": '"', "＇": "'", "“": '"', "”": '"', "‘": "'", "’": "'", "　": " ",
             "．": ".", "！": "!", "＃": "#"}
_JS_LITERALS = {"true": "True", "false": "False", "null": "None", "none": "None", "nil": "None",
                "TRUE": "True", "FALSE": "False", "NULL": "None"}
_NO_DISCARD_WARN = {"show", "ui", "show_window", "print", "studio_input", "studio_output",
                    "studio_set_current_pipeline"}
_PRELUDE_NAME_CACHE: set | None = None


def _prelude_names() -> set:
    """前置きが名前空間に入れる名前(op・指示・道具)。一度だけ作って覚える(op の関数は作らない)。"""
    global _PRELUDE_NAME_CACHE
    if _PRELUDE_NAME_CACHE is None:
        names = set(prelude_exports())
        try:
            names |= {d for d in _directive_names() if d.isidentifier()}
        except Exception:                            # noqa: BLE001
            pass
        names |= {"op", "show", "pipeline", "current_pipeline", "load_pipeline", "studio_input",
                  "studio_output", "studio_set_current_pipeline", "np", "fs", "ui", "show_window",
                  "img", "image", "print", "__name__", "__file__", "__builtins__"}
        _PRELUDE_NAME_CACHE = names
    return _PRELUDE_NAME_CACHE


def _P(line, col, end_line, end_col, sev, code, msg, hint="", fix=None, **params) -> Problem:
    return Problem(int(line), max(0, int(col)), int(end_line), max(0, int(end_col)), sev, code, msg, hint, fix, params)


def _code_spans(text: str):
    """各行の「コードの部分」(文字列・コメントの外)の文字の位置を返す: ``{line: set(col)}``。
    字句解析の失敗に強い簡易版(1 行・3 重引用符の文字列、# のコメント)。"""
    out = {}
    in_triple = None
    for ln, raw in enumerate(text.splitlines(), 1):
        cols = set()
        i, n = 0, len(raw)
        quote = None
        while i < n:
            ch = raw[i]
            if in_triple:
                if raw.startswith(in_triple, i):
                    i += 3
                    in_triple = None
                    continue
                i += 1
                continue
            if quote:
                if ch == "\\":
                    i += 2
                    continue
                if ch == quote or (quote in ('"', "'") and ch in "“”‘’" and False):
                    quote = None
                i += 1
                continue
            if raw.startswith('"""', i) or raw.startswith("'''", i):
                in_triple = raw[i:i + 3]
                i += 3
                continue
            if ch in ("'", '"'):
                quote = ch
                i += 1
                continue
            if ch in ("#", "＃"):
                break
            cols.add(i)
            i += 1
        out[ln] = cols
    return out


def _fullwidth_problems(text: str) -> list:
    spans = _code_spans(text)
    out = []
    for ln, raw in enumerate(text.splitlines(), 1):
        for col in sorted(spans.get(ln, ())):
            ch = raw[col]
            if ch in FULLWIDTH:
                rep = FULLWIDTH[ch]
                out.append(_P(ln, col, ln, col + 1, "error", "fullwidth_char",
                              "Full-width character '%s' (U+%04X) — Python needs the ASCII '%s'" % (ch, ord(ch), rep),
                              "Switch the input method to half-width, or apply the fix",
                              {"line": ln, "col": col, "end_line": ln, "end_col": col + 1, "text": rep},
                              char=ch, ascii=rep))
    return out


def _pipeline_lines_in_python(lines: list) -> list:
    """Python のモードに混じったパイプラインの書き方の行(``endfor``・``* コメント``・``:=``・``op a b``)。"""
    out = []
    names = op_table()
    for ln, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        hit = (re.match(r"(endif|endfor|endwhile)\b", s, re.I) or re.match(r"\*(?![A-Za-z_(])", s)
               or (":=" in s and re.match(r"[A-Za-z_]\w*\s*:=", s)))
        w = re.match(r"([A-Za-z_]\w*)\s+([^\s(=])", s)
        if hit or (w and w.group(1) in names):
            out.append(_P(ln, len(raw) - len(raw.lstrip()), ln, len(raw), "error", "mixed_syntax",
                          "This line is written in the pipeline syntax, but the program is Python",
                          "Use 'Convert to Python' (or write it as Python: img = gaussian(img, 0.4))"))
    return out


def _open_bracket_before(lines: list, line: int):
    """*line* の前の行までで閉じていない括弧の、いちばん外側の ``(行, 列, 括弧)``(無ければ None)。
    文字列・コメントの中は数えない(:func:`_code_spans`)。"""
    spans = _code_spans("\n".join(lines[:max(0, line - 1)]))
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for ln in range(1, line):
        raw = lines[ln - 1]
        for col in sorted(spans.get(ln, ())):
            ch = raw[col]
            if ch in "([{":
                stack.append((ln, col, ch))
            elif ch in pairs:
                if stack and stack[-1][2] == pairs[ch]:
                    stack.pop()
                else:
                    return None                       # 合わない閉じ括弧は別の誤り
    return stack[0] if stack else None


def _syntax_problem(e: SyntaxError, lines: list) -> Problem:
    """SyntaxError をよくある間違いの平易な文とヒントに言い換える(当てはまらなければ Python の文のまま)。"""
    ln = e.lineno or 1
    col = max(0, (e.offset or 1) - 1)
    end_ln = getattr(e, "end_lineno", None) or ln
    end_col = getattr(e, "end_offset", None) or 0
    end_col = max(col + 1, end_col - 1) if end_ln == ln else max(0, end_col - 1)
    raw = lines[ln - 1] if 0 < ln <= len(lines) else ""
    code_part = raw.split("#", 1)[0].rstrip()
    s = code_part.strip()
    msg = e.msg or "invalid syntax"
    if isinstance(e, TabError):
        return _P(ln, 0, ln, len(raw), "error", "tabs_spaces", "Tabs and spaces are mixed in the indentation",
                  "Indent with 4 spaces only")
    if isinstance(e, IndentationError):
        return _P(ln, 0, ln, len(raw) - len(raw.lstrip()), "error", "indentation",
                  "Indentation is off: %s" % msg, "Lines in the same block start at the same column; "
                  "the line after a ':' is indented by 4 spaces", detail=msg)
    m = re.match(r"(else|el)\s+if\b", s)
    if m:
        c0 = raw.index(s)
        return _P(ln, c0, ln, c0 + m.end(), "error", "else_if", "'else if' is written 'elif' in Python",
                  "Replace 'else if' with 'elif'", {"line": ln, "col": c0, "end_line": ln, "end_col": c0 + m.end(),
                                                    "text": "elif"})
    for bad, good in (("&&", "and"), ("||", "or")):
        if bad in code_part:
            c0 = code_part.index(bad)
            return _P(ln, c0, ln, c0 + 2, "error", "c_operator", "'%s' is written '%s' in Python" % (bad, good),
                      "Replace '%s' with '%s'" % (bad, good),
                      {"line": ln, "col": c0, "end_line": ln, "end_col": c0 + 2, "text": " %s " % good if False else good},
                      bad=bad, good=good)
    mnot = re.search(r"(?<![!<>=])!(?!=)", code_part)
    if mnot:
        c0 = mnot.start()
        return _P(ln, c0, ln, c0 + 1, "error", "c_operator", "'!' is written 'not' in Python",
                  "Replace '!x' with 'not x'", {"line": ln, "col": c0, "end_line": ln, "end_col": c0 + 1, "text": "not "},
                  bad="!", good="not")
    opener = _open_bracket_before(lines, ln)
    if opener is not None:
        # 前の行で開いた括弧が閉じていないと、Python は次の行の別の場所を指す。開いた場所を言う
        oln, ocol, br = opener
        close = {"(": ")", "[": "]", "{": "}"}[br]
        return _P(oln, ocol, oln, ocol + 1, "error", "unclosed_bracket",
                  "'%s' opened on line %d is never closed" % (br, oln), "Add the matching '%s'" % close,
                  bracket=br, open_line=oln)
    if "Maybe you meant '==' or ':=' instead of '='" in msg and re.match(r"(if|elif|while)\b", s):
        m2 = re.search(r"(?<![=!<>:])=(?!=)", code_part[col:]) if col < len(code_part) else None
        if m2:
            c0 = col + m2.start()
            return _P(ln, c0, ln, c0 + 1, "error", "assign_in_condition",
                      "'=' assigns; to compare use '=='", "Write 'if x == 1:'",
                      {"line": ln, "col": c0, "end_line": ln, "end_col": c0 + 1, "text": "=="})
    if code_part.endswith("{") or s.startswith("}"):
        return _P(ln, col, ln, len(code_part), "error", "brace_block",
                  "Python marks blocks with ':' and indentation, not '{' '}'",
                  "End the line with ':' and indent the block by 4 spaces")
    if msg.startswith("expected ':'") or re.match(r"(if|elif|while|for|def|class|with|try|else|except|finally)\b", s) \
            and not code_part.endswith(":") and "never closed" not in msg:
        if re.match(r"(if|elif|while|for|def|class|with|try|else|except|finally)\b", s):
            c1 = len(code_part)
            return _P(ln, c1, ln, c1, "error", "missing_colon",
                      "A ':' is missing at the end of this line", "Add ':' after the condition",
                      {"line": ln, "col": c1, "end_line": ln, "end_col": c1, "text": ":"})
    if "was never closed" in msg:
        br = msg[1] if len(msg) > 1 else "("
        close = {"(": ")", "[": "]", "{": "}"}.get(br, ")")
        return _P(ln, col, ln, col + 1, "error", "unclosed_bracket",
                  "'%s' opened on line %d is never closed" % (br, ln), "Add the matching '%s'" % close,
                  bracket=br, open_line=ln)
    if msg.startswith("unmatched") or "does not match opening parenthesis" in msg:
        return _P(ln, col, ln, col + 1, "error", "unmatched_bracket", "This closing bracket has no opening one: %s" % msg,
                  "Remove it or add the opening bracket", detail=msg)
    if msg.startswith("unterminated string") or msg.startswith("unterminated triple-quoted"):
        return _P(ln, col, ln, len(raw), "error", "unclosed_string", "This string is never closed",
                  "Add the closing quote on the same line")
    if "Perhaps you forgot a comma" in msg:
        return _P(ln, col, end_ln, end_col, "error", "missing_comma", "A ',' seems to be missing between items",
                  "Separate the items with ','")
    return _P(ln, col, end_ln, end_col, "error", "syntax_error", "Syntax error: %s" % msg, "", detail=msg)


def _bound_names(tree) -> set:
    """プログラムのどこかで束縛される名前(代入・for・with・except・import・def・class・引数・walrus・global・内包表記)。"""
    out = set()
    for x in ast.walk(tree):
        if isinstance(x, ast.Name) and isinstance(x.ctx, (ast.Store, ast.Del)):
            out.add(x.id)
        elif isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(x.name)
        elif isinstance(x, (ast.Import, ast.ImportFrom)):
            for al in x.names:
                if al.name != "*":
                    out.add((al.asname or al.name).split(".")[0])
        elif isinstance(x, ast.arg):
            out.add(x.arg)
        elif isinstance(x, ast.ExceptHandler) and x.name:
            out.add(x.name)
        elif isinstance(x, (ast.Global, ast.Nonlocal)):
            out.update(x.names)
        elif hasattr(ast, "MatchAs") and isinstance(x, (ast.MatchAs, ast.MatchStar)) and getattr(x, "name", None):
            out.add(x.name)
    return out


def _has_star_import(tree) -> bool:
    return any(isinstance(x, ast.ImportFrom) and any(al.name == "*" for al in x.names)
               and (x.module or "") != "fullseye.studio_prelude" for x in ast.walk(tree))


def _undefined_problem(lineno, col, end_lineno, end_col, name, candidates) -> Problem:
    """未定義の名前 1 件(JS 風の true/null は書き換え、近い名前があれば「もしかして」の fix)。"""
    fix_txt = _JS_LITERALS.get(name)
    if fix_txt:
        return _P(lineno, col, end_lineno, end_col, "error", "js_literal",
                  "'%s' is written '%s' in Python" % (name, fix_txt), "Replace with '%s'" % fix_txt,
                  {"line": lineno, "col": col, "end_line": end_lineno, "end_col": end_col, "text": fix_txt},
                  name=name, good=fix_txt)
    import difflib
    near = difflib.get_close_matches(name, candidates, n=1, cutoff=0.75)
    if near:
        return _P(lineno, col, end_lineno, end_col, "error", "undefined_name",
                  "'%s' is not defined — did you mean '%s'?" % (name, near[0]), "Replace with '%s'" % near[0],
                  {"line": lineno, "col": col, "end_line": end_lineno, "end_col": end_col, "text": near[0]},
                  name=name, suggestion=near[0])
    return _P(lineno, col, end_lineno, end_col, "error", "undefined_name", "'%s' is not defined" % name,
              "Assign it before this line, or check the spelling", name=name)


def _try_import(name: str):
    """任意の依存を import する(無い・塞がれている = None)。結果は覚えない(試験が塞げるように)。"""
    try:
        return importlib.import_module(name)
    except Exception:                                # noqa: BLE001 -- ImportError / 壊れた入り方
        return None


#: pyflakes の知らせ → code と重さ(よくある物だけ平易な文。それ以外は元の文のまま "pyflakes_<名前>")
_PYFLAKES_MAP = {
    "UnusedImport": ("unused_import", "warning", "Imported but never used", "Remove the import"),
    "UnusedVariable": ("unused_variable", "warning", "Assigned but never used (inside a function)",
                       "Remove it, or use it"),
    "RedefinedWhileUnused": ("redefined_unused", "warning", "Defined again before the first one was used",
                             "Rename one of them"),
    "ImportShadowedByLoopVar": ("shadowed_import", "warning", "A loop variable hides an import", "Rename the loop variable"),
}
_PYFLAKES_SKIP = {"ImportStarUsed", "ImportStarUsage", "ImportStarNotPermitted"}


def _pyflakes_problems(pf_checker_mod, tree, known: set, candidates) -> list:
    """pyflakes(任意の依存)の知らせ。前置きの名前は ``builtins=`` で「定義済み」と教える(行はずらさない)。"""
    w = pf_checker_mod.Checker(tree, filename=PROGRAM_FILENAME, builtins=set(known) | set(dir(builtins)))
    out = []
    for m in sorted(w.messages, key=lambda m: (m.lineno, getattr(m, "col", 0))):
        cls = type(m).__name__
        if cls in _PYFLAKES_SKIP:
            continue
        col = getattr(m, "col", 0) or 0
        text = m.message % m.message_args
        if cls == "UnusedImport" and "fullseye.studio_prelude" in text:
            continue                                  # 前置きの名前は builtins= で教えているので「使われない」に見える
        if cls in ("UndefinedName", "UndefinedLocal", "UndefinedExport"):
            name = m.message_args[0]
            out.append(_undefined_problem(m.lineno, col, m.lineno, col + len(str(name)), name, candidates))
            continue
        code, sev, msg, hint = _PYFLAKES_MAP.get(cls, ("pyflakes_" + re.sub(r"(?<!^)([A-Z])", r"_\1", cls).lower(),
                                                       "warning", None, ""))
        out.append(_P(m.lineno, col, m.lineno, col + 1, sev, code,
                      ("%s: %s" % (msg, text)) if msg else text, hint, detail=text))
    return out


def _name_problems(tree, known: set, pyflakes_mod=None) -> list:
    out = []
    if _has_star_import(tree):
        return out                                   # 他のモジュールの * は中身が分からない(誤検出しない)
    bound = _bound_names(tree)
    defined = bound | known | set(dir(builtins))
    candidates = sorted(defined)
    seen = set()
    if pyflakes_mod is not None:
        out += _pyflakes_problems(pyflakes_mod, tree, known, candidates)
    for x in (ast.walk(tree) if pyflakes_mod is None else ()):
        if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and x.id not in defined:
            key = (x.lineno, x.id)
            if key in seen:
                continue
            seen.add(key)
            out.append(_undefined_problem(x.lineno, x.col_offset, x.end_lineno, x.end_col_offset, x.id, candidates))
    # 分岐の片側でしか代入されない名前を、トップレベルの後ろの文で読む → warning(確実でないので error にしない)
    if any(isinstance(x, (ast.Global, ast.Nonlocal)) for x in ast.walk(tree)):
        return out
    sure: set = set()

    def stores(nodes):
        s = set()
        for n in nodes:
            for x in ast.walk(n):
                if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store):
                    s.add(x.id)
                elif isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    s.add(x.name)
                elif isinstance(x, (ast.Import, ast.ImportFrom)):
                    s.update((al.asname or al.name).split(".")[0] for al in x.names if al.name != "*")
        return s

    def loads_outside_scopes(node):
        todo = [node]
        while todo:
            n = todo.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
                              ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                continue
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                yield n
            todo.extend(ast.iter_child_nodes(n))

    maybe: set = set()
    for st in tree.body:
        if isinstance(st, ast.If):
            for x in loads_outside_scopes(st.test):
                if x.id in maybe and x.id not in sure and x.id in bound and x.id not in known:
                    out.append(_P(x.lineno, x.col_offset, x.end_lineno, x.end_col_offset, "warning", "maybe_undefined",
                                  "'%s' is only assigned on one side of an earlier 'if'" % x.id,
                                  "Assign it before the 'if', or in both branches", name=x.id))
            a, b = stores(st.body), stores(st.orelse)
            sure |= a & b
            maybe |= (a | b) - (a & b)
            continue
        if not isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.For, ast.While,
                               ast.With, ast.Try)):
            for x in loads_outside_scopes(st):
                if x.id in maybe and x.id not in sure and x.id not in known:
                    out.append(_P(x.lineno, x.col_offset, x.end_lineno, x.end_col_offset, "warning", "maybe_undefined",
                                  "'%s' is only assigned on one side of an earlier 'if'" % x.id,
                                  "Assign it before the 'if', or in both branches", name=x.id))
        sure |= stores([st])
    return out


def _op_call_problems(tree, known_ops: set, shadowed: set) -> list:
    out = []
    tab = op_table()

    def which_op(c):
        if not isinstance(c, ast.Call) or not isinstance(c.func, ast.Name):
            return None, []
        if c.func.id in known_ops and c.func.id not in shadowed:
            return c.func.id, list(c.args)
        if c.func.id == "op" and "op" not in shadowed and c.args and isinstance(c.args[0], ast.Constant) \
                and isinstance(c.args[0].value, str):
            name = c.args[0].value
            if name not in tab:
                return "?" + name, []
            return name, list(c.args[1:])
        return None, []

    def num(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) \
                and isinstance(node.operand.value, (int, float)) and not isinstance(node.operand.value, bool):
            return -float(node.operand.value)
        return None

    for st in ast.walk(tree):
        for c in ([st] if isinstance(st, ast.Call) else []):
            name, args = which_op(c)
            if name is None:
                continue
            if name.startswith("?"):
                import difflib
                near = difflib.get_close_matches(name[1:], list(tab), n=1, cutoff=0.75)
                a0 = c.args[0]
                out.append(_P(a0.lineno, a0.col_offset, a0.end_lineno, a0.end_col_offset, "error", "unknown_op",
                              "There is no op named '%s'%s" % (name[1:], " — did you mean '%s'?" % near[0] if near else ""),
                              "Check the Operators list", ({"line": a0.lineno, "col": a0.col_offset + 1,
                                                            "end_line": a0.end_lineno, "end_col": a0.end_col_offset - 1,
                                                            "text": near[0]} if near else None),
                              name=name[1:], suggestion=near[0] if near else ""))
                continue
            info = tab[name]
            nums = [num(a) for a in args]
            first_num = next((i for i, v in enumerate(nums) if v is not None), len(args))
            n_inputs, knobs = first_num, args[first_num:]
            if any(isinstance(a, ast.Starred) for a in args) or any(k.arg is None for k in c.keywords):
                continue                              # *args / **kw は数えられない
            if len(knobs) > 2:
                out.append(_P(c.lineno, c.col_offset, c.end_lineno, c.end_col_offset, "error", "too_many_args",
                              "%s takes at most 2 knobs (a, b) after its input(s), got %d" % (name, len(knobs)),
                              "Remove the extra numbers", name=name, count=len(knobs)))
            if info.arity >= 2 and n_inputs == 0:
                out.append(_P(c.lineno, c.col_offset, c.end_lineno, c.end_col_offset, "error", "missing_inputs",
                              "%s takes %d inputs, e.g. %s(x, y)" % (name, info.arity, name),
                              "Pass the inputs before the knobs", name=name, arity=info.arity))
            elif len(args) > info.arity + 2:
                # 変数はつまみ(数)か入力か構文からは分からないので、入力 + つまみ 2 つを超える時だけ確実に誤り
                out.append(_P(c.lineno, c.col_offset, c.end_lineno, c.end_col_offset, "error", "too_many_args",
                              "%s takes %d input(s) and at most 2 knobs, got %d arguments"
                              % (name, info.arity, len(args)),
                              "Remove the extra arguments", name=name, count=len(args)))
            for k in c.keywords:
                if k.arg not in ("a", "b"):
                    out.append(_P(k.value.lineno, k.value.col_offset, k.value.end_lineno, k.value.end_col_offset,
                                  "error", "unknown_keyword", "%s has no keyword '%s' (only a= and b=)" % (name, k.arg),
                                  "Use a= or b=", name=name, keyword=k.arg))
            labelled = list(zip(("a", "b"), knobs)) + [(k.arg, k.value) for k in c.keywords if k.arg in ("a", "b")]
            for label, node in labelled:
                v = num(node)
                if v is not None and math.isfinite(v) and not 0.0 <= v <= 1.0:
                    used = max(0.0, min(1.0, v))
                    out.append(_P(node.lineno, node.col_offset, node.end_lineno, node.end_col_offset, "warning",
                                  "knob_out_of_range",
                                  "knob outside 0..1, will run with the nearest limit: %s %s=%.6g → %.6g"
                                  % (name, label, v, used), "Knobs a and b are 0..1 (the op maps them to its range)",
                                  {"line": node.lineno, "col": node.col_offset, "end_line": node.end_lineno,
                                   "end_col": node.end_col_offset, "text": "%.6g" % used},
                                  name=name, knob=label, value=v, used=used))
    # 戻り値を捨てている op 呼び出し(測るだけの op、または入力を明示した画像の op を文として書いた)
    for st in ast.walk(tree):
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
            name, args = which_op(st.value)
            if not name or name.startswith("?") or name in _NO_DISCARD_WARN:
                continue
            info = tab[name]
            explicit = bool(args) and num(args[0]) is None
            if info.out_sort in MEASURE_SORTS:
                out.append(_P(st.lineno, st.col_offset, st.end_lineno, st.end_col_offset, "warning", "result_discarded",
                              "The result of %s is thrown away" % name, "Assign it: n = %s(...)" % name, name=name))
            elif explicit:
                out.append(_P(st.lineno, st.col_offset, st.end_lineno, st.end_col_offset, "warning", "result_discarded",
                              "The result of %s is not assigned (only the current flow and the display change)" % name,
                              "Assign it: x = %s(...)" % name, name=name))
    return out


def check_program(text: str, *, known_ops: Iterable[str] | None = None, lang: str = "en",
                  syntax: str | None = None) -> list:
    """書いている最中の指摘(**実行しない**: ``compile`` と ``ast`` だけ、import もしない)。``list[Problem]``。

    パイプラインの書き方(HDevelop 風)の文面は、その解析器の誤りを ``pipeline_syntax`` として返す。
    構文の誤りがあるときは構文の誤り(と全角の記号)だけを返す(連鎖する指摘を出さない)。同じ行の同じ code は 1 件。
    *lang* は今は英語だけ(文は ``code`` と ``params`` で Studio が訳す)。*syntax* を渡すとそのモードとして
    検査する(エディタはモードを知っている。Python のモードで ``if x`` と書けば「':' が無い」と言う)。"""
    lines = text.splitlines()
    known_ops = set(op_table() if known_ops is None else known_ops)
    syn, mixed = (syntax, []) if syntax else detect_syntax(text)
    if mixed:
        m = re.match(r"line (\d+):", mixed[0])
        ln = int(m.group(1)) if m else 1
        return [_P(ln, 0, ln, len(lines[ln - 1]) if 0 < ln <= len(lines) else 0, "error", "mixed_syntax",
                   "This line is written in the pipeline syntax, but the program is Python",
                   "Use 'Convert to Python' (or write it as Python: img = gaussian(img, 0.4))", detail=mixed[0])]
    if syn == SYNTAX_HDEVELOP:
        import studio
        _st, errs, _ln = studio.parse_hdev_program_lines(text, sorted(known_ops))
        out = []
        for e in errs:
            m = re.match(r"line (\d+): (.*)", e) or re.match(r".*\(opened at line (\d+)\)()", e)
            ln = int(m.group(1)) if m else 1
            out.append(_P(ln, 0, ln, len(lines[ln - 1]) if 0 < ln <= len(lines) else 0, "error",
                          "pipeline_syntax", e, ""))
        return out
    problems = _fullwidth_problems(text)
    if syntax == SYNTAX_PYTHON:
        problems += _pipeline_lines_in_python(lines)
    try:
        tree = ast.parse(text, PROGRAM_FILENAME)
        compile(tree, PROGRAM_FILENAME, "exec", dont_inherit=True)   # break の外れなど、compile の段の誤りも拾う
    except SyntaxError as e:
        sp_ = _syntax_problem(e, lines)
        if any(p.line == sp_.line for p in problems):
            return problems                          # 全角の記号が原因(同じ行の同じ原因は 1 件)
        return problems + [sp_] + _parso_more_errors(text, {p.line for p in problems} | {sp_.line})
    except (ValueError, RecursionError, MemoryError) as e:
        return problems + [_P(1, 0, 1, 0, "error", "syntax_error", "Cannot read the program: %s" % e)]
    shadowed = _bound_names(tree)
    known = _prelude_names() | known_ops
    problems += _name_problems(tree, known, _try_import("pyflakes.checker"))
    problems += _op_call_problems(tree, known_ops, shadowed)
    for line_no, raw in enumerate(lines, 1):
        code_part = raw.split("#", 1)[0].rstrip()
        if code_part.endswith(";") and not code_part.strip().startswith(("'", '"')):
            c = len(code_part) - 1
            problems.append(_P(line_no, c, line_no, c + 1, "hint", "semicolon", "A ';' at the end of a line is not needed",
                               "Remove it", {"line": line_no, "col": c, "end_line": line_no, "end_col": c + 1, "text": ""}))
    for adv in advise_program(text):
        problems.append(_P(adv.line, 0, adv.line, len(lines[adv.line - 1]) if 0 < adv.line <= len(lines) else 0,
                           "hint" if adv.kind != "qt_binding_mix" else "warning", adv.kind, adv.message))
    mixed_lines = {p.line for p in problems if p.code == "mixed_syntax"}
    problems = [p for p in problems if p.code == "mixed_syntax" or p.line not in mixed_lines]   # 原因は 1 件
    uniq, seen = [], set()
    for p in problems:
        key = (p.line, p.code)
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    order = {"error": 0, "warning": 1, "hint": 2}
    uniq.sort(key=lambda p: (order.get(p.severity, 3), p.line, p.col))
    return uniq


#: 構文の誤りを何件まで出すか(1 つの誤りから連鎖した物を出しすぎない)。
MAX_SYNTAX_ERRORS = 5


def _parso_more_errors(text: str, skip_lines: set) -> list:
    """parso(任意の依存)があれば、壊れたコードでも読めるので 2 件目以降の構文の誤りを足す(別の行だけ)。"""
    parso = _try_import("parso")
    if parso is None:
        return []
    try:
        grammar = parso.load_grammar()
        errs = list(grammar.iter_errors(grammar.parse(text, error_recovery=True)))
    except Exception:                                # noqa: BLE001
        return []
    out, lines_seen = [], set(skip_lines)
    first = min(skip_lines) if skip_lines else 0
    for e in sorted(errs, key=lambda e: e.start_pos):
        ln, col = e.start_pos
        # 連鎖を出さない: 最初の誤りの行とその次の行、字下げの誤り(ブロックが壊れた結果)は数えない
        if ln in lines_seen or ln <= first + 1 or "indent" in e.message.lower():
            continue
        lines_seen.add(ln)
        eln, ecol = e.end_pos
        out.append(_P(ln, col, eln, max(ecol, col + 1) if eln == ln else ecol, "error", "syntax_error",
                      "Syntax error: %s" % e.message, "", detail=e.message, source="parso"))
        if len(out) >= MAX_SYNTAX_ERRORS - 1:
            break
    return out


def checker_backends() -> list:
    """使える検査の道具の一覧。無い物は「何が使えていないか」を 1 行で言う(黙って機能が減らない)。"""
    rows = [{"name": "compile/ast/tokenize/difflib", "available": True, "version": sys.version.split()[0],
             "gives": "the first syntax error, Fullseye checks (op names, knobs, full-width, other-language "
                      "syntax, pipeline syntax), undefined names (lenient)", "missing": ""}]
    for name, gives, missing in (
            ("parso", "several syntax errors at once, with exact ranges",
             "only the first syntax error is shown (pip install parso)"),
            ("pyflakes", "undefined names in order, unused imports and variables, redefinitions",
             "undefined names are checked leniently and unused imports are not reported (pip install pyflakes)"),
            ("jedi", "completion, hover and signatures that also know numpy and installed packages",
             "completion and hover only know the prelude and Python built-ins (pip install jedi)")):
        mod = _try_import(name)
        rows.append({"name": name, "available": mod is not None,
                     "version": getattr(mod, "__version__", "") if mod is not None else "",
                     "gives": gives, "missing": "" if mod is not None else missing})
    return rows


# --------------------------------------------------------------------------- #
# 補完とホバー(jedi があれば jedi、無ければ前置きと組み込みの名前)              #
# --------------------------------------------------------------------------- #
_STUB_DIR: str | None = None
_STUB_MODULE = "_fullseye_studio_prelude_stub"


def _prelude_stub_dir() -> str:
    """jedi に前置きの名前を教える stub(op ごとの def と img・show …)を一時の場所に一度だけ書く。
    前置きの本物のモジュールは名前を実行時に作るので、jedi は静的に読めない。"""
    global _STUB_DIR
    if _STUB_DIR is not None and os.path.isfile(os.path.join(_STUB_DIR, _STUB_MODULE + ".py")):
        return _STUB_DIR
    import tempfile
    tab = op_table()
    names = sorted(prelude_exports())
    digest = hashlib.sha256(",".join(names).encode()).hexdigest()[:12]
    d = os.path.join(tempfile.gettempdir(), "fullseye_studio_stub_" + digest)
    os.makedirs(d, exist_ok=True)
    body = ["import numpy as np", "import fullseye as fs", "import numpy", "",
            "img: numpy.ndarray = ...", "image: numpy.ndarray = ...", "",
            "def show(x):\n    \"\"\"Show x as the final picture (the last show wins).\"\"\"\n    return x\n",
            "def op(name: str, *inputs, a: float = 0.5, b: float = 0.5):\n    \"\"\"Call an op by name.\"\"\"\n",
            "def pipeline(stages, name: str = 'pipeline'):\n    \"\"\"Build a stage list: pipeline([('gaussian', 0.4), ('otsu',)]).\"\"\"\n",
            "def load_pipeline(name: str):\n    \"\"\"Load a saved pipeline (.json) or a recipe by name.\"\"\"\n",
            "def current_pipeline():\n    \"\"\"The pipeline built in Studio's stage list.\"\"\"\n",
            "def ui(fn, *args):\n    \"\"\"Run fn(*args) on the GUI thread and return its result.\"\"\"\n",
            "def show_window(make_widget):\n    \"\"\"Make a Qt widget on the GUI thread, show it, keep it in the run's window list.\"\"\"\n"]
    for n in names:
        info = tab[n]
        ins = ", ".join("x%d" % i for i in range(1, info.arity + 1)) if info.arity > 1 else "x=None"
        body.append("def %s(%s, a: float = 0.5, b: float = 0.5):\n    \"\"\"Fullseye op %s: %s -> %s. "
                    "Knobs a, b are 0..1; leave x out to use the current flow.\"\"\"\n"
                    % (n, ins, n, info.in_sort, info.out_sort))
    tmp = os.path.join(d, _STUB_MODULE + ".py.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(body) + "\n")
    os.replace(tmp, os.path.join(d, _STUB_MODULE + ".py"))
    _STUB_DIR = d
    return d


_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _word_at(text: str, line: int, col: int) -> tuple:
    lines = text.split("\n")
    raw = lines[line - 1] if 0 < line <= len(lines) else ""
    start = col
    while start > 0 and (raw[start - 1].isalnum() or raw[start - 1] == "_"):
        start -= 1
    end = col
    while end < len(raw) and (raw[end].isalnum() or raw[end] == "_"):
        end += 1
    return raw[start:col], raw[start:end]


def _op_signature(name: str) -> str:
    info = op_table()[name]
    ins = ", ".join("x%d" % i for i in range(1, info.arity + 1)) if info.arity > 1 else "x"
    return "%s(%s, a=0.5, b=0.5)  # %s -> %s" % (name, ins, info.in_sort, info.out_sort)


def complete(text: str, line: int, col: int, limit: int = 50) -> list:
    """(line 1 始まり, col 0 始まり)での補完候補 ``[{"name", "type", "detail"}]``。jedi があれば jedi
    (前置きの stub を見せる。行は 1 行ずらして戻す)、無ければ前置き・組み込み・文面の中の名前の前方一致。"""
    jedi = _try_import("jedi")
    if jedi is not None:
        try:
            header = "from %s import *\n" % _STUB_MODULE
            proj = jedi.Project(path=os.getcwd(), added_sys_path=[_prelude_stub_dir()], smart_sys_path=False)
            script = jedi.Script(code=header + text, project=proj)
            out = []
            for c in script.complete(line + 1, col)[:limit]:
                out.append({"name": c.name, "type": c.type, "detail": c.description})
            return out
        except Exception:                            # noqa: BLE001 -- jedi が読めない文面は下の簡易版で
            pass
    prefix, _word = _word_at(text, line, col)
    pool = set(_prelude_names()) | set(dir(builtins)) | set(_IDENT_RE.findall(text))
    pool.discard(prefix)
    tab = op_table()
    out = []
    for n in sorted(p for p in pool if p.startswith(prefix) and not p.startswith("__")):
        kind = "op" if n in tab else ("builtin" if n in dir(builtins) else "name")
        out.append({"name": n, "type": kind, "detail": _op_signature(n) if n in tab else ""})
        if len(out) >= limit:
            break
    return out


def hover(text: str, line: int, col: int) -> dict | None:
    """(line, col) の名前の説明 ``{"name", "signature", "doc"}``(分からなければ None)。"""
    _prefix, word = _word_at(text, line, col)
    if not word:
        return None
    tab = op_table()
    if word in tab:
        info = tab[word]
        return {"name": word, "signature": _op_signature(word),
                "doc": "Fullseye op: %s -> %s. Knobs a, b are 0..1; leave the input out to use the current flow."
                       % (info.in_sort, info.out_sort)}
    jedi = _try_import("jedi")
    if jedi is not None:
        try:
            header = "from %s import *\n" % _STUB_MODULE
            proj = jedi.Project(path=os.getcwd(), added_sys_path=[_prelude_stub_dir()], smart_sys_path=False)
            names = jedi.Script(code=header + text, project=proj).help(line + 1, col)
            if names:
                n = names[0]
                sigs = n.get_signatures()
                return {"name": n.name, "signature": sigs[0].to_string() if sigs else "",
                        "doc": (n.docstring(raw=True) or "").strip().split("\n\n")[0]}
        except Exception:                            # noqa: BLE001
            pass
    if word in dir(builtins):
        doc = (getattr(builtins, word).__doc__ or "").strip().split("\n")[0]
        return {"name": word, "signature": "", "doc": doc}
    return None


def apply_fix(text: str, fix: dict) -> str:
    """:class:`Problem` の ``fix`` を文面に当てる(エディタが使うのと同じ置き換え。試験用にも)。"""
    lines = text.split("\n")
    a = sum(len(l) + 1 for l in lines[:fix["line"] - 1]) + fix["col"]
    b = sum(len(l) + 1 for l in lines[:fix["end_line"] - 1]) + fix["end_col"]
    return text[:a] + fix["text"] + text[b:]
