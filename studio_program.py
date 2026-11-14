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
import types
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
    "run_file", "evaluate", "STARTER_PROGRAM", "STARTER_PROGRAMS", "starter_program", "abandoned_runs",
    "program_threads",
]

SYNTAX_PYTHON = "python"
SYNTAX_HDEVELOP = "hdevelop"

#: ``compile`` に渡すファイル名。トレースと例外の行番号はこの名前の枠だけを Program の行と見なす。
PROGRAM_FILENAME = "<studio-program>"

#: 時間の上限の既定(秒)。行ごとに見るので、C の中で回っている重い op の途中では止まらない。
DEFAULT_TIME_LIMIT_S = 30.0

#: 起動時に Program 欄へ入れる Python の例(既定のモードは Python、設計書 §1)。同梱の画像を読み、op 4 つ・
#: 変数・if を 1 つずつ使う。実行すると絵(show)と段の列(記録)が出る。コメントと print の見出しは UI の言語で
#: 出す(:func:`starter_program`)。コードの行は全言語で同じ = 行番号も同じ。表に無い言語は英語。
_STARTER_TEXTS = {
    "en": ("Fullseye Studio - press F5 (Run): the picture and the stage list appear.",
           "images that ship with Fullseye", "delete this line to use the image open in Studio",
           "1. smooth", "2. bright parts -> region", "3. count the blobs (a number)", "blobs:",
           "4a. many specks: remove the small ones", "4b. few blobs: fill their holes"),
    "ja": ("Fullseye Studio - F5(実行)を押すと、絵と段の列が出ます。",
           "Fullseye に同梱の画像", "この行を消すと、Studio で開いている画像を使います",
           "1. 平滑化", "2. 明るい所 -> 領域", "3. 粒を数える(数)", "粒の数:",
           "4a. 細かい粒が多い: 小さい物を除く", "4b. 粒が少ない: 穴を埋める"),
    "zh": ("Fullseye Studio - 按 F5(运行):显示图像和步骤列表。",
           "Fullseye 自带的图像", "删除此行则使用 Studio 中打开的图像",
           "1. 平滑", "2. 亮的部分 -> 区域", "3. 数颗粒(一个数)", "颗粒数:",
           "4a. 细小颗粒多:去掉小的", "4b. 颗粒少:填充孔洞"),
    "tw": ("Fullseye Studio - 按 F5(執行):顯示影像和步驟列表。",
           "Fullseye 內附的影像", "刪除此行則使用 Studio 中開啟的影像",
           "1. 平滑", "2. 亮的部分 -> 區域", "3. 數顆粒(一個數)", "顆粒數:",
           "4a. 細小顆粒多:去掉小的", "4b. 顆粒少:填補孔洞"),
    "ko": ("Fullseye Studio - F5(실행)를 누르면 그림과 단계 목록이 나옵니다.",
           "Fullseye에 들어 있는 이미지", "이 줄을 지우면 Studio에서 연 이미지를 씁니다",
           "1. 평활화", "2. 밝은 부분 -> 영역", "3. 알갱이 세기(수)", "알갱이 수:",
           "4a. 잔 알갱이가 많음: 작은 것을 제거", "4b. 알갱이가 적음: 구멍을 메움"),
    "de": ("Fullseye Studio - F5 (Ausführen) drücken: Bild und Stufenliste erscheinen.",
           "Bilder, die Fullseye mitbringt", "diese Zeile löschen, um das in Studio geöffnete Bild zu nutzen",
           "1. glätten", "2. helle Teile -> Region", "3. Flecken zählen (eine Zahl)", "Flecken:",
           "4a. viele Sprenkel: die kleinen entfernen", "4b. wenige Flecken: Löcher füllen"),
}
_STARTER_COMMENT_COL = 43


def starter_program(lang: str = "en") -> str:
    """Program 欄の例(Python)を *lang* のコメントで返す。表に無い言語(hi など)は英語。"""
    t = _STARTER_TEXTS.get(lang) or _STARTER_TEXTS["en"]

    def row(code, comment):
        return code.ljust(_STARTER_COMMENT_COL) + "# " + comment
    return "\n".join([
        "# python",
        "# " + t[0],
        row("import sample_images", t[1]),
        row('img = sample_images.load("coins")', t[2]),
        row("img = gaussian(img, 0.3)", t[3]),
        row("mask = otsu(img)", t[4]),
        row("n = blob_count(mask)", t[5]),
        "print(%s, n)" % json.dumps(t[6], ensure_ascii=False),
        "if n > 10:",
        row("    mask = opening_circle(mask, 0.3)", t[7]),
        "else:",
        row("    mask = fill_holes(mask)", t[8]),
        "show(mask)",
        "",
    ])


#: 英語の例(今までの名前。試験と API の利用者が読む)。
STARTER_PROGRAM = starter_program("en")
#: 言語ごとの例 ``{言語: 文面}``(「手を付けていない例か」の判定にも使う)。
STARTER_PROGRAMS = {k: starter_program(k) for k in _STARTER_TEXTS}

#: 実行の構成。Debug = 行フックあり(既定)、Release = 速さ優先(行フックなし)。
CONFIGS = ("debug", "release")

#: 「測るだけ」の出力 sort。この op は流れ(今の画像)を変えず、値だけを返す。
MEASURE_SORTS = frozenset({"feature", "match"})

#: 前置きが予約する名前(op の関数としては出さない)。
PRELUDE_RESERVED = ("img", "image", "show", "op", "pipeline", "current_pipeline", "load_pipeline", "ui", "show_window",
                    "np", "fs", "studio_input", "studio_output", "print", "load_params")

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


def _is(v, cls) -> bool:
    """``isinstance`` の代わり: ``type(v)`` だけで決める。``isinstance`` は ``v.__class__`` を読むので、利用者の
    クラスがそれをプロパティにしていると利用者のコードが走る(実行の後・見張りの外で固まる)。"""
    return issubclass(type(v), cls)


def _tname(t) -> str:
    """型の名前(``type`` 自身の読み出しで。メタクラスの ``__name__`` のプロパティ = 利用者のコードを通さない)。"""
    try:
        n = type.__dict__["__name__"].__get__(t)     # type.__getattribute__ はメタクラスのプロパティを拾う
        return n if type(n) is str else "object"
    except Exception:                                # noqa: BLE001
        return "object"


def _tin(t, types_) -> bool:
    """*t* が *types_* のどれかと**同一**か。``t in (int, float)`` は ``==`` を呼ぶので、メタクラスの ``__eq__``
    (利用者のコード)が走る。同一性だけで比べる。"""
    for x in types_:
        if t is x:
            return True
    return False


#: 例外の属性は、型の記述子で直接読む(利用者の例外クラスの ``__getattribute__`` を通さない)。
_EXC_TRACEBACK = BaseException.__dict__["__traceback__"]
_EXIT_CODE = SystemExit.__dict__["code"]
_IMPORT_NAME = ImportError.__dict__["name"]


def _numpy_type(t) -> bool:
    """numpy 自身が定義した型か(利用者が派生した配列・スカラはメソッドを差し替えられるので別扱い)。"""
    try:
        mod = type.__dict__["__module__"].__get__(t)                       # メタクラスの属性の読み出しを通さない
    except Exception:                                                     # noqa: BLE001
        return False
    return type(mod) is str and mod.split(".")[0] == "numpy"


def _kind_of(v, rec: "Recorder | None" = None) -> str:
    if _is(v, np.ndarray):
        if rec is not None:
            s = rec.sort_of(v)
            if s:
                return s
        return "ndarray"
    if _is(v, bool):
        return "bool"
    if _is(v, (int, np.integer)):
        return "int"
    if _is(v, (float, np.floating)):
        return "float"
    return _tname(type(v))


def _shape_of(v):
    if not _is(v, np.ndarray):
        return None
    return tuple(int(s) for s in np.ndarray.shape.__get__(v))     # 派生した型の shape の差し替えを通さない


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
        #: ``show`` が呼ばれた回数(:func:`evaluate` が「この呼び出しの間に見せた物」を見分ける)。
        self.shown_n = 0
        self.current_stages: list = []
        #: show_window で開いた窓(実行の終わり・停止で close_program_windows が閉じる)
        self.windows: list = []
        #: Release の構成で止める場所 = op の呼び出しの境目(Debug は settrace の行フックが止める)
        self.stop_event = None
        self.deadline: float | None = None
        self.time_limit_s: float | None = None
        #: load_pipeline の相対パスを探す場所(None = engine.load_pipeline の既定)
        self.search_dirs: list | None = None
        #: load_params の相対パスを探す場所(None = 作業フォルダだけ)。2026-11-13 UI の繋ぎ
        self.param_dirs: list | None = None
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
        self.shown_n += 1
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


#: プロジェクトのフォルダの中でパラメータの束を置く場所(標準の並びの params/)。
PROJECT_PARAMS_SUBDIR = "params"


def params_search_dirs(project_dir: str | None = None, program_dir: str | None = None) -> list:
    """``load_params("rig.toml")`` の相対パスを探す場所の順(2026-11-13): プロジェクトの ``params/`` →
    実行中のプログラムのファイルの場所 → 作業フォルダ(:func:`pipeline_search_dirs` と同じ形)。"""
    out = []
    if project_dir:
        sub = PROJECT_SUBDIR_RESOLVER("params") if PROJECT_SUBDIR_RESOLVER else PROJECT_PARAMS_SUBDIR
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


def _load_params(name):
    """``fullseye.load_params`` と同じ物を読む。相対パスは :func:`params_search_dirs` の順に探し、
    見つからなければ探した場所を全部書いた ``FileNotFoundError``(黙って空の束にしない)。"""
    from fullseye import parambundle
    p = os.fspath(name)
    if os.path.isabs(p):
        return parambundle.load_params(p)
    rec = active_recorder()
    dirs = rec.param_dirs or [os.getcwd()]
    for d in dirs:
        cand = os.path.join(d, p)
        if os.path.isfile(cand):
            return parambundle.load_params(cand)
    raise FileNotFoundError("load_params(%r): not found in %s" % (p, "; ".join(dirs)))


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
    """*x* を最後に画面へ出す値にする(最後の ``show`` が勝つ)。*x* を返す。matplotlib の図(Figure)は、
    Agg で描いた画像にして出す(窓は開かない)。"""
    if _is_mpl_figure(x):
        active_recorder().show(_figure_to_array(x))
        return x
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
              ui=_ui, show_window=_show_window, load_params=_load_params)
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


#: 変数の表で中身を書く入れ物(完全一致の型だけ。派生した型は長さだけ)。
_PLAIN_CONTAINERS = (list, tuple, dict, set, frozenset)
_SUMMARY_ITEMS = 8
_SUMMARY_CHARS = 60


def _safe_text(v, depth: int = 0) -> str | None:
    """``repr(v)`` と同じ見た目の短い文字列を、**利用者のコードを呼ばずに**作る。作れない(長い・深い)なら None。

    数・文字列・numpy のスカラ・完全一致の list / tuple / dict / set だけ中身を書く。それ以外(利用者のクラスの物、
    派生した str や list)は ``<型の名前>``。入れ物は先頭 :data:`_SUMMARY_ITEMS` 個まで見て、それより多ければ None
    (10⁷ 要素の list でも全文を作らない)。"""
    t = type(v)
    if v is None or t is bool or t is float or t is complex:
        return repr(v)
    if t is int:
        return repr(v) if v.bit_length() < 256 else "<int %d bits>" % v.bit_length()
    if t is str or t is bytes:
        return repr(v) if len(v) <= _SUMMARY_CHARS else None
    if _is(v, np.generic) and _numpy_type(t):
        return repr(v.item()) if v.dtype.kind in "biuf" else "<%s>" % _tname(t)
    if t is np.ndarray:
        return "<ndarray %s>" % "×".join(str(s) for s in v.shape)
    if _tin(t, _PLAIN_CONTAINERS):
        if depth >= 2 or len(v) > _SUMMARY_ITEMS:
            return None
        if t is dict:
            parts = []
            for k, x in v.items():
                a, b = _safe_text(k, depth + 1), _safe_text(x, depth + 1)
                if a is None or b is None:
                    return None
                parts.append("%s: %s" % (a, b))
            return "{%s}" % ", ".join(parts)
        parts = [_safe_text(x, depth + 1) for x in v]
        if any(p is None for p in parts):
            return None
        body = ", ".join(parts)
        if t is list:
            return "[%s]" % body
        if t is tuple:
            return "(%s%s)" % (body, "," if len(parts) == 1 else "")
        if not parts:
            return "set()" if t is set else "frozenset()"
        return "{%s}" % body if t is set else "frozenset({%s})" % body
    return "<%s>" % _tname(t)


def describe_value(v, rec: Recorder | None = None) -> tuple:
    """``(kind, shape, summary)``。画像は型と形(``image 512×512 float64``)、小さい値は中身。

    **利用者のコードを呼ばない**(``__repr__`` / ``__str__`` / ``__len__`` / ``__class__`` のプロパティ)。実行の
    後・見張りの外で呼ばれるので、戻らない ``__repr__`` があると実行が終わらなくなる(2026-11-13 レビュー H2)。
    利用者のクラスの物は型の名前だけ、入れ物の中のそれは ``<型の名前>``。"""
    kind = _kind_of(v, rec)
    shape = _shape_of(v)
    t = type(v)
    if _is(v, np.ndarray):
        a = v if t is np.ndarray else np.ndarray.view(v, np.ndarray)      # 派生した型の表示の差し替えを通さない
        dims = "×".join(str(s) for s in a.shape)
        if a.size <= 16 and a.dtype.kind in "biufc":                      # object の配列は要素の repr を呼ぶので書かない
            return kind, shape, "%s %s %s" % (kind, dims, np.array2string(a, precision=4, threshold=16))
        return kind, shape, "%s %s %s" % (kind, dims, a.dtype)
    if v is None or t is bool or t is int or t is float or (_is(v, np.generic) and _numpy_type(t)):
        return kind, None, _safe_text(v) or _tname(t)
    if t is str:
        r = repr(v[:_SUMMARY_CHARS + 1])                                   # 長い文字列の全文の repr は作らない
        return kind, None, r if len(v) <= _SUMMARY_CHARS and len(r) <= _SUMMARY_CHARS else r[:57] + "…'"
    if _is(v, _PLAIN_CONTAINERS):
        base = next(b for b in _PLAIN_CONTAINERS if _is(v, b))
        head = "%s[%d]" % (_tname(t), base.__len__(v))                     # 派生した型の __len__ は呼ばない
        r = _safe_text(v) if _tin(t, _PLAIN_CONTAINERS) else None
        return kind, None, head + (" " + r if r is not None and len(r) <= _SUMMARY_CHARS else "")
    if t is Pipeline:
        return "pipeline", None, "%s: %s" % (v.name, " → ".join(s[0] for s in v.stages))
    if t is types.FunctionType or t is types.BuiltinFunctionType or t is types.MethodType:
        return "function", None, v.__name__
    if _is(v, type):
        return "function", None, _tname(v)
    if callable(v):
        return "function", None, _tname(t)
    return kind, None, _tname(t)


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
    #: 止まった所が関数の中のとき、その枠の局所変数(モジュールの階層で止まったら空)。
    #: 今までに print された文字数(``stdout`` は末尾 :data:`MAX_STDOUT_CHARS` 文字だけ。越えた分は捨てている)。
    stdout_total: int = 0
    locals: dict = field(default_factory=dict)
    #: 止まった所の呼び出しの積み重ね ``[(関数名, 行)]``(内側が先。Program のファイルの枠だけ)。
    stack: list = field(default_factory=list)

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
                 filename: str = PROGRAM_FILENAME, conditions=None, resume_after_lines: int = 0, clock=None):
        self.filename = filename
        #: 止まっていた時間を除いて時間の上限を数える時計(見張りと共有)。
        self.clock = clock if clock is not None else _Clock()
        #: ``on_pause(理由, 行, 枠) -> 指示``。あれば、ブレークポイント・1 行実行で例外を投げずに**その場で待つ**
        #: (戻り値 "continue" / "step" / "stop" か、``{"command", "breakpoints", "conditions"}``)。
        self.on_pause = None
        #: 最後に止まった所の局所変数と呼び出しの積み重ね(:class:`ProgramResult` の locals / stack)。
        self.locals: dict = {}
        self.stack: list = []
        #: 条件つきブレークポイント {行: 式}。式はその行の枠(globals / locals)で評価し、偽なら止めない。
        #: 評価できなければ止めて理由を ``notes`` へ(止めずに素通りさせない側 = fail-closed)。
        self.conditions = {int(k): str(v) for k, v in (conditions or {}).items() if str(v).strip()}
        #: 続行・1 行実行は「上から走り直す」(§4)。走り直しで、すでに通った行数までのブレークポイントは止めない。
        self.resume_after_lines = max(0, int(resume_after_lines or 0))
        self.notes: list = []
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
        if self.time_limit_s is not None \
                and time.perf_counter() - self.t0 - self.clock.paused_s > self.time_limit_s:
            self._stop("time_limit", ln)
        reason = None
        if ln in self.breakpoints and self.lines >= self.resume_after_lines and self._condition_holds(frame, ln):
            self.hits += 1
            if self.hits > self.skip_hits:
                reason = "breakpoint"
        if reason is None and self.max_lines is not None and self.lines >= self.max_lines:
            reason = "step"
        if reason is not None:
            self._pause(reason, frame, ln)
        self.lines += 1
        return self.local_trace

    def _pause(self, reason, frame, ln):
        """ブレークポイント・1 行実行で止まる。``on_pause`` があればその場で待ち、指示で続ける(この行はまだ
        実行していない: 戻ればこの行から続く)。無ければ今までどおり例外で実行を終える。"""
        self.locals, self.stack = _frame_locals(frame), _frame_stack(frame, self.filename)
        if self.on_pause is None:
            self._stop(reason, ln)
        cmd = self.on_pause(reason, ln, frame)
        if isinstance(cmd, dict):
            if cmd.get("breakpoints") is not None:
                self.breakpoints = set(int(b) for b in cmd["breakpoints"])
            if cmd.get("conditions") is not None:
                self.conditions = {int(k): str(v) for k, v in cmd["conditions"].items() if str(v).strip()}
            cmd = cmd.get("command")
        if cmd == "continue":
            self.max_lines = None
        elif cmd == "step":
            self.max_lines = self.lines + 1          # この行を実行して、次の行で止まる
        else:                                        # "stop"・知らない指示は止める側(走り続けさせない)
            self._stop("stop_requested", ln)

    def _condition_holds(self, frame, ln) -> bool:
        expr = self.conditions.get(ln)
        if not expr:
            return True
        try:
            return bool(eval(expr, frame.f_globals, frame.f_locals))   # noqa: S307 -- 利用者が書いた条件(本物の Python)
        except Exception as e:                       # noqa: BLE001 -- 評価できない条件では止めて理由を言う
            self.notes.append("line %d: breakpoint condition %r could not be evaluated (%s: %s) — stopped there"
                              % (ln, expr, type(e).__name__, e))
            return True

    def _stop(self, reason, ln):
        self.sticky = ProgramStopped(reason, ln)
        raise self.sticky


class _Clock:
    """実行の時計: ブレークポイントで待っていた時間(``paused_s``)は時間の上限に数えない。``paused`` の間、
    見張りは時間切れを撃たない(止める要求は撃つ)。"""

    def __init__(self):
        self.paused_s = 0.0
        self.paused = False


def _frame_locals(frame) -> dict:
    """止まった枠の局所変数の写し(モジュールの階層なら空 = 名前空間そのものなので重ねない)。"""
    if frame is None or frame.f_locals is frame.f_globals:
        return {}
    return {k: v for k, v in dict(frame.f_locals).items() if isinstance(k, str)}


def _frame_stack(frame, filename: str) -> list:
    """止まった所の呼び出しの積み重ね ``[(関数名, 行)]``(内側が先。Program のファイルの枠だけ)。"""
    out = []
    while frame is not None:
        if frame.f_code.co_filename == filename:
            out.append((frame.f_code.co_name, frame.f_lineno))
        frame = frame.f_back
    return out


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


#: 例外の文の上限(文字)。越えた分は切って、切った事を書く(20 MB の文が状態の欄やツールチップに入らない)。
MAX_ERROR_CHARS = 2000
#: 実行の後で結果を文字にする処理(例外の文・終了コード・変数の表)の時間の上限(秒)。作業スレッドの中・
#: 見張りの内側で行い、越えたら止めの例外を撃つ(利用者の ``__str__`` が戻らなくても実行は終わる)。
_DESCRIBE_LIMIT_S = 2.0


def _clip_text(s: str, limit: int | None = None) -> str:
    """長い文を *limit* 文字で切り、切った文字数を書く。"""
    limit = MAX_ERROR_CHARS if limit is None else limit
    if len(s) <= limit:
        return s
    return s[:limit] + " … (%d more characters)" % (len(s) - limit)


def _exception_text(e) -> str:
    """例外の文(``str(e)``)。**利用者のコードを呼ぶ唯一の所**(``__str__``、引数の ``__repr__``)なので、必ず作業
    スレッドの中・見張りの内側から呼ぶこと。戻らなければ見張りが止めの例外を撃ち、型の名前だけの文になる。"""
    try:
        s = str(e)
        return _clip_text(s) if type(s) is str else "<%s>" % _tname(type(e))
    except ProgramStopped:
        return "<the text of this %s is not available: its __str__ did not return in time>" % _tname(type(e))
    except BaseException as x:                       # noqa: BLE001 -- __str__ の中の誤り
        return "<the text of this %s is not available: its __str__ raised %s>" % (_tname(type(e)), _tname(type(x)))


#: 止めの例外を撃ってから、戻らなければ諦めるまでの秒数(呼び出し側を永久に待たせない)。
_STOP_GRACE_S = 1.0
#: 撃ち直しの間隔と上限回数(`except BaseException` で握りつぶすループ対策)。
_SHOT_INTERVAL_S = 0.05
_MAX_SHOTS = 60
#: Debug の見張りは行フックより少し遅らせる(行フックの方が行番号つきの文で止める)。
_WATCHDOG_DEBUG_SLACK_S = 0.25
#: 止められずに残した実行(daemon スレッド)。``abandoned_runs()`` で一覧。
_ABANDONED: list = []
#: 作業スレッドのスタック(深い再帰で RecursionError より先にスタックが尽きないように)。
_WORKER_STACK_BYTES = 64 * 1024 * 1024
_STACK_LOCK = threading.Lock()
#: このモジュールを読み込んだ時の本物の import の入口(``builtins.__import__``・``importlib.import_module``・
#: ``importlib.__import__``)。見張りの「元の物」が無い時の行き先(外した見張りが鉤の列に残っても None を呼ばない)。
_REAL_IMPORTS = (builtins.__import__, importlib.import_module, importlib.__import__)


class _AsyncTimeLimit(ProgramStopped):
    """見張りが SetAsyncExc で撃つ止めの例外(時間の上限)。引数なしで作られる。"""

    def __init__(self, *args):
        super().__init__("time_limit", 0)


class _AsyncStopRequested(ProgramStopped):
    """見張りが SetAsyncExc で撃つ止めの例外(停止の要求)。"""

    def __init__(self, *args):
        super().__init__("stop_requested", 0)


def _shoot(thread_id: int, exc_cls) -> bool:
    """*thread_id* のスレッドに、次の bytecode の境目で *exc_cls* を投げさせる(CPython の
    ``PyThreadState_SetAsyncExc``)。C の中で回っている間は届かない(戻った所で届く)。"""
    import ctypes
    n = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), ctypes.py_object(exc_cls))
    if n > 1:                                        # 起きないはずだが、起きたら取り消す(他のスレッドを壊さない)
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), None)
        return False
    return n == 1


def abandoned_runs() -> list:
    """止められずに残した実行の一覧 ``[{"thread", "started", "alive"}]``(生きている物だけ残す)。"""
    _ABANDONED[:] = [a for a in _ABANDONED if a["thread"].is_alive()]
    return [dict(a, alive=a["thread"].is_alive()) for a in _ABANDONED]


#: 止められずに残した実行が生きている間に、次の実行を断る時の文(``%d`` = 残っている実行の数)。
ABANDONED_BLOCKS_RUN = ("not run: an earlier run could not be stopped and is still running in the background (%d) — "
                        "it can still change files, the environment and the working folder; wait until it ends "
                        "or restart Studio")


#: 変数・ウォッチの欄が利用者のコード(``__repr__``・式)のために起こして、時間切れの後も残っているスレッドがある間に、
#: 次の実行を断る時の文(``%d`` = 残っている数)。止めの例外が保留のまま残ると、``sys.settrace`` の下の実行(Debug)が
#: 約 300 倍遅くなり、何もしないプログラムが時間切れになる(CPython 3.11。2026-11-13 第 2 回レビュー R5)。
STRAY_BLOCKS_RUN = ("not run: a value shown in the Variables or Watch panel is still running its own code in the "
                    "background (%d) — wait until it ends or restart Studio")


def _stray_value_threads() -> int:
    """``studio_pyedit_values`` が残したスレッドの数(読み込まれていなければ 0。ここからは import しない)。"""
    mod = sys.modules.get("studio_pyedit_values")
    try:
        return len(mod.stray_threads()) if mod is not None else 0
    except Exception:                                # noqa: BLE001
        return 0


def _restore_when_done(waits, snapshot, guard=None) -> None:
    """止められずに残した実行が終わった所で、プロセスの状態をもう一度戻し、import の見張りを外す(残った実行は、
    諦めて戻した**後**にも環境変数や作業フォルダを書き換える。2026-11-13 レビュー H3)。その間、次の実行は始めない
    (:data:`ABANDONED_BLOCKS_RUN`)ので、戻す相手は必ずこの実行の前の状態。

    *waits* = 待つ物の列: ``_ABANDONED`` の行(そのスレッドが終わるまで)と、止まって待っている間に始めた「選んだ行」の
    入口(:class:`_Entry`。呼び出しが戻り、止められずに残したスレッドがあればそれも終わるまで)。**外側の入口だけが
    呼ぶ**。入れ子の入口(止まっている間の選んだ行)は、自分の写しへ遅れて戻さない(2026-11-15 第 4 回の確かめ:
    止まっている間の選んだ行を残した後で Debug の実行が終わると、選んだ行の遅れた戻しが「止まっていた時の写し」=
    プログラムが変えた環境変数と作業フォルダと、外した見張りを戻し、Studio の中の import が全部 TypeError になった)。

    **戻し終えるまで**を「残っている」に数える(行のスレッドを、この後始末のスレッドに差し替える。行が無ければ、
    後始末のスレッドの行を足す)。残した実行のスレッドが終わった瞬間に次の実行を通すと、その実行の途中で状態と
    import の見張りが戻されてしまう。"""
    inner = [w for w in waits if type(w) is _Entry]
    rows = [w for w in waits if type(w) is dict] + [e.left_row for e in inner if e.left_row is not None]
    threads = [r["thread"] for r in rows]

    def body():
        for th in threads:
            th.join()
        for e in inner:
            e.done.wait()
            if e.left_thread is not None:
                e.left_thread.join()
        try:
            snapshot.restore()
            if guard is not None:
                guard.uninstall()
        except Exception:                            # noqa: BLE001 -- 見張りのスレッドを落とさない
            pass
    reaper = threading.Thread(target=body, name="studio-program-late-restore", daemon=True)
    reaper.start()
    for r in rows:                                   # 始めてから差し替える(始める前は is_alive() が偽で、行が消される)
        r["thread"] = reaper
    if not rows:
        _ABANDONED.append({"thread": reaper, "started": time.time()})


#: 作業スレッドからの import を断る GUI の部品(Qt の束ね・tkinter)。Qt の窓は GUI(main)スレッドでしか作れない。
GUI_TOOLKIT_MODULES = ("PySide6", "PySide2", "PyQt5", "PyQt6", "shiboken6", "pyqtgraph", "qtpy", "tkinter", "_tkinter", "wx")
#: matplotlib の、窓を出す backend の名前に入る語(``matplotlib.backends.backend_qtagg`` など)。
_MPL_GUI_BACKEND_WORDS = ("qt", "tk", "wx", "gtk", "macosx", "webagg", "nbagg")
GUI_IMPORT_REFUSED = ("Studio does not let a running program import %s: GUI toolkits (Qt, tkinter, the interactive "
                      "matplotlib backends) only work on Studio's own GUI thread — draw with matplotlib as usual; "
                      "plt.show() and show(fig) put the figure in the image pane")
MPL_SHOWN_NOTE = "plt.show(): the figure was put in the image pane (a program does not open windows in Studio)"
#: 窓を出す backend(QtAgg など)で作られた図が残っていて、pyplot の一覧から外した時の知らせ(``%d`` = 外した数)。
MPL_DETACHED_NOTE = ("%d matplotlib figure(s) made with a window backend were still open: they were taken off "
                     "pyplot's list (a program in Studio draws on Agg and cannot use or close a GUI window)")
#: 外した図の管理役(Qt の窓を持つ)。**消さない**ために持ち続ける: 持ち主でないスレッドから Qt の窓を消すと、
#: Studio 全体が固まる(2026-11-13 第 3 回レビュー S1-d)。
_DETACHED_FIGURES: list = []
#: 作業スレッドから呼ばれた、Qt を直接 import する文面を断る時の文(``%d`` = その import の行)。
QT_PROGRAM_REFUSED = ("line %d: not run: this program imports Qt directly, and Qt widgets can only be "
                      "made on the GUI thread — this version of Studio cannot run Qt programs from the "
                      "Program (use the Python Editor window, or run it outside Studio)")


def _figure_to_array(fig):
    """matplotlib の図を画像の配列(H×W×3、0..1 の float)にする(Agg で描く。窓は作らない)。"""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    canvas = fig.canvas if type(fig.canvas) is FigureCanvasAgg else FigureCanvasAgg(fig)
    canvas.draw()
    rgba = np.asarray(canvas.buffer_rgba())
    return np.ascontiguousarray(rgba[..., :3]).astype(np.float64) / 255.0


def _is_mpl_figure(x) -> bool:
    t = type(x)
    try:
        mod = type.__dict__["__module__"].__get__(t)
    except Exception:                                # noqa: BLE001
        return False
    return type(mod) is str and mod.split(".")[0] == "matplotlib" and _tname(t) in ("Figure", "SubFigure")


class _ImportGuard:
    """実行の間だけ効く見張り(設計書 §15、2026-11-13 第 2 回レビュー R3):

    * **プログラムの作業スレッド**からの GUI の部品(:data:`GUI_TOOLKIT_MODULES`、matplotlib の窓を出す backend)の
      import を ``ImportError`` で断る。``import`` 文(相対 import も: ``__package__`` / ``__spec__`` / ``__name__``
      から絶対の名前にして調べる)・``__import__``・``importlib.import_module``・``importlib.__import__``・``exec``
      した文字列の中の import、ライブラリ(matplotlib)の中からの import を拾う。``sys.modules`` から直接引く道と、
      プログラムが起こした別のスレッドは拾えない(既知の制約)。他のスレッド(Studio の GUI)の import は通す。
    * matplotlib は Agg(窓を出さない)で動かし、``plt.show()`` は今の図を画像の欄へ出す。

    Studio は PySide6 を読み込み済みなので、何もしないと matplotlib は QtAgg を選び、``plt.show()`` の 1 行が
    作業スレッドで Qt の窓を作る(図を閉じた所で Studio 全体が固まった)。

    **図が残っていても Agg にする**(2026-11-13 第 3 回レビュー S1-d)。前は「図が 1 つでもあれば backend を
    変えない」だったので、窓を出す backend の図が 1 つ残っているだけで、次の実行の ``plt.figure()`` が作業スレッドで
    Qt の窓を作った。窓を出す backend で作られた図は、作業スレッドからは使えず、閉じる事もできない(持ち主でない
    スレッドから Qt の窓を消すと固まる)ので、pyplot の一覧から外して(:data:`_DETACHED_FIGURES` が持ち続ける。
    窓は消さない)、結果の ``notes`` に :data:`MPL_DETACHED_NOTE` を入れる。

    **付いている見張りは 1 つだけ**(2026-11-15 第 4 回の確かめ): 止まって待っている Debug の実行の間の「選んだ行」は、
    自分の見張りを重ねず、そのスレッドを外側の見張りの :attr:`recs` に足す。外す時は先に :attr:`recs` を空にし、
    元の物は持ち続ける: 上に別の鉤が重なっていて元へ戻せなかった鉤が残っても、何も断らずに元の物へ素通しする
    (前は外す時に元の物を None にしたので、残った鉤が None を呼び、Studio の中の import が全部 TypeError になった)。"""

    def __init__(self):
        #: 見張りが断る作業スレッド → そのスレッドの ``plt.show()`` の図の出し先(:class:`Recorder`)。
        #: :func:`_guarded_user_call` が入れる(外側の実行のスレッドと、止まっている間の選んだ行のスレッド)。
        self.recs: dict = {}
        self.installed = False
        self.orig_import = None
        self.orig_import_module = None
        self.orig_importlib_import = None            # importlib.__import__(builtins.__import__ の Python 版)
        self._mine = (None, None, None)
        self.plt_show = None                         # (pyplot, 元の show, 差し替えた show)
        self.mpl_env = None
        self.shown_figures = 0
        self.detached_figures = 0                    # pyplot の一覧から外した、窓を出す backend の図の数

    # ---- 断る名前 ----
    @staticmethod
    def refused(name) -> bool:
        if type(name) is not str:
            return False
        if name.split(".")[0] in GUI_TOOLKIT_MODULES:
            return True
        if name.startswith("matplotlib.backends.backend_"):
            tail = name[len("matplotlib.backends.backend_"):].lower()
            return any(w in tail for w in _MPL_GUI_BACKEND_WORDS)
        return False

    def _check(self, name):
        if self.refused(name):
            raise ImportError(GUI_IMPORT_REFUSED % name)

    @staticmethod
    def _absolute(name, globals_, level):
        """import 文の名前を絶対の名前にする。相対 import(*level* > 0)は、import 文と同じ決まりで親のパッケージを
        決める(``__package__`` → ``__spec__.parent`` → ``__name__``)。決められなければ None(本物の import が
        同じ理由で ``ImportError`` にする)。前は ``level != 0`` を調べずに通していたので、
        ``__package__ = "PySide6"`` と ``from . import QtWidgets`` で見張りを抜けた(2026-11-13 第 3 回レビュー S7)。"""
        if type(name) is not str:
            return None
        if not level:
            return name
        try:
            if type(globals_) is not dict:
                return None
            pkg = globals_.get("__package__")
            if type(pkg) is not str:
                spec = globals_.get("__spec__")
                pkg = getattr(spec, "parent", None) if spec is not None else None
            if type(pkg) is not str:
                pkg = globals_.get("__name__")
                if type(pkg) is str and "__path__" not in globals_:
                    pkg = pkg.rpartition(".")[0]
            if type(pkg) is not str or not pkg:
                return None
            bits = pkg.rsplit(".", int(level) - 1)
            if len(bits) < int(level):
                return None
            return "%s.%s" % (bits[0], name) if name else bits[0]
        except ProgramStopped:
            raise
        except Exception:                            # noqa: BLE001 -- 決められない名前は本物の import に任せる
            return None

    def _check_import(self, name, globals_, fromlist, level):
        """``__import__(name, globals, locals, fromlist, level)`` の形の呼び出しを調べる。"""
        full = self._absolute(name, globals_, level)
        if full is None:
            return
        self._check(full)
        for sub in (fromlist or ()):                 # from matplotlib.backends import backend_qtagg
            if type(sub) is str:
                self._check("%s.%s" % (full, sub))

    # ---- 付ける・外す(呼び出し側のスレッド) ----
    def install(self):
        import importlib
        guard = self
        self.orig_import = builtins.__import__
        self.orig_import_module = importlib.import_module
        self.orig_importlib_import = importlib.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            mine = threading.get_ident() in guard.recs
            if mine:
                guard._check_import(name, globals, fromlist, level)
            mod = (guard.orig_import or _REAL_IMPORTS[0])(name, globals, locals, fromlist, level)
            if mine:
                guard._after_import()
            return mod

        def guarded_importlib_import(name, globals=None, locals=None, fromlist=(), level=0):
            mine = threading.get_ident() in guard.recs
            if mine:
                guard._check_import(name, globals, fromlist, level)
            mod = (guard.orig_importlib_import or _REAL_IMPORTS[2])(name, globals, locals, fromlist, level)
            if mine:
                guard._after_import()
            return mod

        def guarded_import_module(name, package=None):
            mine = threading.get_ident() in guard.recs
            if mine and type(name) is str and not name.startswith("."):
                guard._check(name)
            mod = (guard.orig_import_module or _REAL_IMPORTS[1])(name, package)
            if mine:
                guard._after_import()
            return mod

        builtins.__import__ = guarded_import
        importlib.import_module = guarded_import_module
        importlib.__import__ = guarded_importlib_import
        self._mine = (guarded_import, guarded_import_module, guarded_importlib_import)
        self.installed = True
        # matplotlib: 窓を出さない backend に固定する(利用者の環境の MPLBACKEND=QtAgg も、実行の間だけ Agg にする。
        # 写し(_GlobalState)はこの後に取るので、戻しはこの値を保ち、外す時(uninstall)に実行の前の値へ戻す)
        self.mpl_env = os.environ.get("MPLBACKEND")
        os.environ["MPLBACKEND"] = "Agg"
        mpl = sys.modules.get("matplotlib")
        if mpl is not None:
            try:
                if sys.modules.get("matplotlib.pyplot") is not None:
                    self.detached_figures = self._detach_window_figures()
                now = dict.__getitem__(mpl.rcParams, "backend")       # 自動の選択を起こさずに今の設定だけ読む
                if not (type(now) is str and now.lower() == "agg"):
                    mpl.use("Agg", force=True)       # 残っている図は窓を持たない物だけ(閉じられても固まらない)
            except Exception:                        # noqa: BLE001 -- matplotlib の都合で実行を止めない
                pass
        self._after_import()

    @staticmethod
    def _detach_window_figures() -> int:
        """pyplot が持っている図のうち、窓を出す backend(Qt・Tk など)で作られた物を pyplot の一覧から外す。
        外した数を返す。**窓は消さない**(管理役を :data:`_DETACHED_FIGURES` が持ち続ける)。図そのもの
        (``Figure``)は名前空間に残っていれば ``show(fig)`` で画像の欄へ出せる(Agg で描き直す)。"""
        try:
            from matplotlib import _pylab_helpers
            figs = _pylab_helpers.Gcf.figs
        except Exception:                            # noqa: BLE001 -- matplotlib の版の違い
            return 0
        n = 0
        for num, manager in list(figs.items()):
            canvas = getattr(manager, "canvas", None)
            if getattr(type(canvas), "required_interactive_framework", None) is None:
                continue                             # Agg・pdf・svg など、窓を持たない図はそのまま
            if figs.pop(num, None) is not None:
                _DETACHED_FIGURES.append(manager)
                n += 1
        return n

    def uninstall(self):
        """外す(呼び出し側のスレッド)。先に :attr:`recs` を空にする(残った鉤は何も断らない)。元の物は None に
        しない(上に別の鉤が重なっていて戻せなかった鉤は、元の物へ素通しする)。2 回目からは何もしない。"""
        import importlib
        self.recs.clear()
        if not self.installed:
            return
        self.installed = False
        if builtins.__import__ is self._mine[0]:
            builtins.__import__ = self.orig_import
        if importlib.import_module is self._mine[1]:
            importlib.import_module = self.orig_import_module
        if importlib.__import__ is self._mine[2]:
            importlib.__import__ = self.orig_importlib_import
        if self.plt_show is not None:
            plt, orig, mine = self.plt_show
            if getattr(plt, "show", None) is mine:
                plt.show = orig
            self.plt_show = None
        if self.mpl_env is None:                     # 実行の間だけの MPLBACKEND=Agg を、実行の前の値へ
            os.environ.pop("MPLBACKEND", None)
        else:
            os.environ["MPLBACKEND"] = self.mpl_env

    # ---- matplotlib の show ----
    def _after_import(self):
        if self.plt_show is not None:
            return
        plt = sys.modules.get("matplotlib.pyplot")
        if plt is None or not hasattr(plt, "show") or not hasattr(plt, "get_fignums"):
            return
        guard = self
        orig = plt.show

        def show(*args, **kwargs):
            """Studio の中の ``plt.show()``: 窓は開かず、今の図を画像の欄へ出す(Studio の ``show(fig)`` と同じ)。"""
            rec = guard.recs.get(threading.get_ident())
            if rec is None:
                return orig(*args, **kwargs)
            nums = plt.get_fignums()
            if not nums:
                return None
            rec.show(_figure_to_array(plt.gcf()))
            guard.shown_figures += 1
            return None
        plt.show = show
        self.plt_show = (plt, orig, show)


def _program_threads_alive(before: set) -> list:
    """実行の前(*before* = その時のスレッドの集合)には無く、今も生きているスレッド(プログラムが起こした物)。
    Studio 自身の作業用のスレッド(名前が ``studio-`` / ``pyedit-`` で始まる物)は数えない。"""
    out = []
    for th in threading.enumerate():
        if th in before or not th.is_alive() or th is threading.current_thread():
            continue
        if str(th.name).startswith(("studio-", "pyedit-")):
            continue
        out.append(th)
    return out


#: プログラムが起こして、実行の後も動いているスレッド(生きている物だけ残す)。``program_threads()`` で一覧。
_PROGRAM_THREADS: list = []
PROGRAM_THREADS_NOTE = ("the program started %d thread(s) that are still running after it ended: %s — they keep "
                        "running in Studio and can change files, the environment and the working folder; what "
                        "they change is not restored")


def program_threads() -> list:
    """前の実行のプログラムが起こして、まだ動いているスレッドの名前の一覧。"""
    _PROGRAM_THREADS[:] = [t for t in _PROGRAM_THREADS if t.is_alive()]
    return [str(t.name) for t in _PROGRAM_THREADS]


def _first_qt_import_line(text: str) -> int:
    """Qt を直接 import する最初の行(無ければ 0)。"""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 0
    lines = []
    for x in ast.walk(tree):
        if isinstance(x, ast.Import) and any(al.name.split(".")[0] in QT_MODULES for al in x.names):
            lines.append(x.lineno)
        elif isinstance(x, ast.ImportFrom) and x.module and x.module.split(".")[0] in QT_MODULES:
            lines.append(x.lineno)
    return min(lines) if lines else 0


def _run_with_watchdog(fn, outcome: dict, deadline, stop_event, in_caller: bool, clock=None) -> bool:
    """*fn* を回し、時間の上限(*deadline*)か *stop_event* で止めの例外を撃つ。戻らなければ撃ち直し、
    撃ち始めて :data:`_STOP_GRACE_S` 秒で諦めて True(= 残した)を返す。

    ``in_caller=False``: *fn* を作業スレッド(daemon)で回し、呼び出し側は待つだけ。諦めたら戻る。
    ``in_caller=True``(Qt を直接使うプログラム): *fn* を呼び出し側のスレッドで回し、見張りは別のスレッドから
    撃つ。この形では C の中で止まった物を諦めて戻ることはできない(設計書 §15)。"""
    if in_caller:
        target = threading.current_thread().ident
        done = threading.Event()

        def watch():
            shot_at, shots, last, phase = None, 0, 0.0, None
            while not done.wait(0.02):
                if outcome.get("phase") != phase:    # 実行 → 結果を文字にする段: 撃った数と諦めるまでの時間を数え直す
                    shot_at, shots, last, phase = None, 0, 0.0, outcome.get("phase")
                exc = _due(deadline, stop_event, clock, outcome)
                if exc is None:
                    continue
                now = time.perf_counter()
                if shot_at is None:
                    shot_at = now
                if shots < _MAX_SHOTS and now - last >= _SHOT_INTERVAL_S:
                    _shoot(target, exc)
                    shots, last = shots + 1, now
        w = threading.Thread(target=watch, name="studio-program-watchdog", daemon=True)
        w.start()
        try:
            fn()
        finally:
            done.set()
            w.join(1.0)
        return False
    with _STACK_LOCK:
        old = threading.stack_size()
        try:
            threading.stack_size(_WORKER_STACK_BYTES)
        except (ValueError, RuntimeError):
            pass
        th = threading.Thread(target=fn, name="studio-program", daemon=True)
        th.start()
        try:
            threading.stack_size(old)
        except (ValueError, RuntimeError):
            pass
    shot_at, shots, last, phase = None, 0, 0.0, None
    while th.is_alive():
        th.join(0.02)
        if not th.is_alive():
            break
        if outcome.get("phase") != phase:            # 実行 → 結果を文字にする段: 撃った数と諦めるまでの時間を数え直す
            shot_at, shots, last, phase = None, 0, 0.0, outcome.get("phase")
        exc = _due(deadline, stop_event, clock, outcome)
        if exc is None:
            continue
        now = time.perf_counter()
        if shot_at is None:
            shot_at = now
        if shots < _MAX_SHOTS and now - last >= _SHOT_INTERVAL_S:
            _shoot(th.ident, exc)
            shots, last = shots + 1, now
        if now - shot_at > _STOP_GRACE_S:
            _ABANDONED.append({"thread": th, "started": time.time()})
            return True
    return False


def _due(deadline, stop_event, clock=None, outcome=None):
    """今撃つべき止めの例外(無ければ None)。ブレークポイントで待っている間(*clock*.paused)は時間切れを
    撃たず、待っていた時間は上限に数えない。止める要求は待っている間も撃つ(待ちから起きた所で届く)。
    プログラムが終わって結果を文字にする段(``outcome["phase"] == "describe"``)は、その段の上限だけを見る
    (プログラムの時間切れ・止める要求でこの段を撃たない。撃つと結果の文が作れない)。"""
    if outcome is not None and outcome.get("phase") == "describe":
        dl = outcome.get("describe_deadline")
        return _AsyncTimeLimit if dl is not None and time.perf_counter() > dl else None
    if stop_event is not None and stop_event.is_set():
        return _AsyncStopRequested
    if clock is not None and clock.paused:
        return None
    if deadline is not None and time.perf_counter() - (clock.paused_s if clock is not None else 0.0) > deadline:
        return _AsyncTimeLimit
    return None


class _GlobalState:
    """実行の前後で戻すプロセス全体の状態: ``sys.path``・``os.environ``・作業フォルダ・``builtins`` の名前・
    ``warnings`` の絞り・``sys.stdout`` / ``stderr`` / ``stdin``・``sys.excepthook`` / ``displayhook`` /
    ``unraisablehook``・``threading.excepthook``・再帰の上限(:data:`RESTORED_STATE` が戻す物の一覧)。
    戻さない物(設計書 §4.2): 読み込んだ他人のパッケージ(``sys.modules``。利用者のフォルダの物は外す)・numpy の
    乱数や ``seterr``・logging の設定・signal・開いたファイルやスレッド。"""

    #: ``sys`` の属性のうち、差し替えられたら元の物へ戻す物(差し替えると Studio 本体の出力・クラッシュ記録が消える)。
    SYS_ATTRS = ("stdout", "stderr", "stdin", "excepthook", "displayhook", "unraisablehook")

    def __init__(self):
        import warnings
        self.sys_attrs = {k: getattr(sys, k, None) for k in self.SYS_ATTRS}
        self.thread_hook = threading.excepthook
        self.recursion = sys.getrecursionlimit()
        self.path = list(sys.path)
        self.environ = dict(os.environ)
        try:
            self.cwd = os.getcwd()
        except OSError:
            self.cwd = None
        self.builtins = dict(vars(builtins))
        self.warnings = list(warnings.filters)

    @classmethod
    def take(cls) -> "_GlobalState":
        return cls()

    def restore(self) -> list:
        """戻した物の名前の列(変わっていなかった物は書かない)。"""
        import warnings
        done = []
        if sys.path != self.path:
            sys.path[:] = self.path
            done.append("sys.path")
        if dict(os.environ) != self.environ:
            for k in [k for k in os.environ if k not in self.environ]:
                del os.environ[k]
            for k, v in self.environ.items():
                if os.environ.get(k) != v:
                    os.environ[k] = v
            done.append("os.environ")
        if self.cwd is not None:
            try:
                if os.getcwd() != self.cwd:
                    os.chdir(self.cwd)
                    done.append("cwd")
            except OSError:
                os.chdir(self.cwd)
                done.append("cwd")
        bd = vars(builtins)
        if bd.keys() != self.builtins.keys() or any(bd[k] is not v for k, v in self.builtins.items()):
            for k in [k for k in bd if k not in self.builtins]:
                del bd[k]
            for k, v in self.builtins.items():
                if bd.get(k) is not v:
                    bd[k] = v
            done.append("builtins")
        if warnings.filters != self.warnings:
            warnings.filters[:] = self.warnings
            done.append("warnings")
        for k, v in self.sys_attrs.items():
            if getattr(sys, k, None) is not v:
                setattr(sys, k, v)
                done.append("sys." + k)
        if threading.excepthook is not self.thread_hook:
            threading.excepthook = self.thread_hook
            done.append("threading.excepthook")
        if sys.getrecursionlimit() != self.recursion:
            try:
                sys.setrecursionlimit(self.recursion)
                done.append("recursion limit")
            except (RecursionError, ValueError):     # 今の深さより小さくは戻せない(呼び出し側が深い所にいる)
                pass
        return done


#: 実行の後に戻すプロセス全体の状態の名前(``notes`` の「restored after the run: …」に出る語と同じ。試験が全部を見る)。
RESTORED_STATE = ("sys.path", "os.environ", "cwd", "builtins", "warnings", "sys.stdout", "sys.stderr", "sys.stdin",
                  "sys.excepthook", "sys.displayhook", "sys.unraisablehook", "threading.excepthook",
                  "recursion limit")


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


class _Guarded:
    """:func:`_guarded_user_call` の結果。"""

    def __init__(self):
        #: 走らせなかった理由(走らせたなら None)と、その行(Qt の import の行。行に結び付かない理由なら None)。
        self.refused: str | None = None
        self.refused_line: int | None = None
        #: 止められずに残した(その実行が終わった所で、状態の取り戻しと見張りの取り外しをもう一度行う)。
        self.abandoned = False
        #: 見張りが戻った時刻(``time.perf_counter()``)。
        self.ended = 0.0
        #: 結果に足す知らせ(外した図・``plt.show()``・残ったスレッド・戻した状態、の順)。
        self.notes: list = []


class _Entry:
    """利用者のコードを回している入口(:func:`_guarded_user_call`)の 1 回分(2026-11-15 第 4 回の確かめ)。

    入口は**入れ子にしない**: Debug の実行がブレークポイントで止まって待っている間の「選んだ行」(:func:`evaluate`)は、
    その実行(外側の入口)の import の見張りの下で回す(作業スレッドを外側の見張りに足すだけ。見張りを重ねず、自分の
    写しは「止まっている実行の状態」へ戻すのにだけ使い、遅れた戻しはしない)。外側が終わる時に、まだ終わって
    いない・止められずに残した内側があれば、外側の後始末(:func:`_restore_when_done`)がそれを待ってから、外側の
    写しへ戻して見張りを外す。"""

    def __init__(self, guard, clock, outer=None):
        self.guard = guard                           # import の見張り(内側は外側の物を共有する。無ければ None)
        self.clock = clock                           # 外側: 止まって待っているかを見る時計(無ければ None)
        self.outer = outer                           # 内側: 外側の入口(外側なら None)
        self.closed = False                          # 外側: 終わった(戻して外す段に入った)
        self.children: list = []                     # 外側: 止まっている間に始めた内側の入口
        self.done = threading.Event()                # 呼び出しが戻った(後始末を済ませた)
        self.left_thread = None                      # 内側: 止められずに残したスレッド
        self.left_row = None                         # 内側: その ``_ABANDONED`` の行(外側の後始末が引き継ぐ)


#: 今、利用者のコードを回している外側の入口(無ければ None)。:data:`_ENTRY_LOCK` の下で読み書きする。
_OUTER_ENTRY = None
_ENTRY_LOCK = threading.Lock()
#: 実行が走っている(ブレークポイントで止まって待っていない)間に、別の入口から利用者のコードを始めようとした時の文。
ANOTHER_RUN_BLOCKS_RUN = ("not run: another run of the program is in progress — wait until it ends or stop it "
                          "(selected lines can run while a Debug run waits at a breakpoint)")


def _refusal(text: str):
    """利用者のコード *text* を**今は走らせない**理由 ``(文, 行か None)``。走らせてよければ None。

    * 止められずに残した実行が生きている(:data:`ABANDONED_BLOCKS_RUN`。残った実行は状態を書き換え続ける。H3)。
    * 変数・ウォッチの欄の ``__repr__`` 用のスレッドが残っている(:data:`STRAY_BLOCKS_RUN`。R5)。
    * 作業スレッドから呼ばれていて、文面が Qt を直接 import する(:data:`QT_PROGRAM_REFUSED`)。Qt の窓は GUI(main)
      スレッドでしか作れない。橋(:data:`GUI_BRIDGE`)が無いまま作業スレッドで走らせると未定義の動作になる(M1)。"""
    left = abandoned_runs()
    if left:
        return ABANDONED_BLOCKS_RUN % len(left), None
    stray = _stray_value_threads()
    if stray:
        return STRAY_BLOCKS_RUN % stray, None
    if GUI_BRIDGE is None and threading.current_thread() is not threading.main_thread() and needs_gui_thread(text):
        ln = _first_qt_import_line(text) or 1
        return QT_PROGRAM_REFUSED % ln, ln
    return None


def _runs_in_caller(text: str) -> bool:
    """*text* を呼び出し側のスレッドで回すか: Qt を直接 import する文面を main スレッドから呼んだ時だけ
    (設計書 §15 の案 C)。それ以外は作業スレッドで回す。"""
    return needs_gui_thread(text) and threading.current_thread() is threading.main_thread()


def _guarded_user_call(fn, text: str, *, recorder, outcome: dict, time_limit_s: float | None = None,
                       slack_s: float = 0.0, stop_event=None, clock=None, user_dirs=()) -> _Guarded:
    """利用者のコードを回す**ただ 1 つの入口**。F5・続行・1 行実行(:func:`run_program`)も、選んだ行
    (:func:`evaluate`)も、この先に足す入口(対話の窓など)も、必ずここを通す(2026-11-13 第 3 回レビュー S1:
    選んだ行だけが守りを通らず、作業スレッドに Qt の窓ができて Studio 全体が固まった)。

    *fn* = 利用者のコード *text* を走らせる関数(引数なし。例外は自分で受ける)。ここがする事:

    1. 断る(:func:`_refusal`): 残した実行・残ったスレッドがある間、作業スレッドからの Qt。別の実行が**走っている**
       (ブレークポイントで止まって待っていない)間も断る(:data:`ANOTHER_RUN_BLOCKS_RUN`)。
    2. GUI の部品の import の見張り(:class:`_ImportGuard`。*recorder* は ``plt.show()`` の図の出し先)を付け、
       matplotlib を Agg にする。作業スレッドで回す時だけ(橋があれば、窓は橋が GUI スレッドで作る)。
       **入れ子にしない**(2026-11-15 第 4 回の確かめ): 止まって待っている実行の間の選んだ行は、見張りを付けず、
       作業スレッドを外側の見張りに足す(:class:`_Entry`)。
    3. プロセス全体の状態の写し(:class:`_GlobalState`)を取り、*user_dirs* を ``sys.path`` の先頭に足す。
    4. *fn* を見張りつきで回す(:func:`_run_with_watchdog`。上限 = *time_limit_s* + *slack_s*、*stop_event*、
       待っている間を除く時計 *clock*)。始めた時刻と上限を ``outcome["t0"]`` / ``outcome["deadline"]`` に入れる。
    5. 終わったら(例外でも)足した道を外し、状態を戻し、見張りを外す。止められずに残した時と、止まっている間に始めた
       選んだ行がまだ終わっていない・残した時は、見張りを付けたまま、それらが終わった所でもう一度戻して外す
       (:func:`_restore_when_done`。外側の入口だけ)。内側(選んだ行)は自分の写し(= 止まっている実行の状態)へ
       戻すだけで、外側が先に終わっていれば戻さない。
    6. 知らせ(外した図・``plt.show()``・プログラムが起こして残したスレッド・戻した状態)を ``notes`` に入れる。"""
    global _OUTER_ENTRY
    run = _Guarded()
    in_caller = _runs_in_caller(text)
    with _ENTRY_LOCK:                                # 断り・見張り・写しを、外側の入口の出入りと重ねない
        why = _refusal(text)
        outer = _OUTER_ENTRY
        if why is None and outer is not None and (
                outer.clock is None or not outer.clock.paused
                or (outer.guard is None and GUI_BRIDGE is None and not in_caller)):
            why = ANOTHER_RUN_BLOCKS_RUN, None
        if why is not None:
            run.refused, run.refused_line = why
            return run
        if outer is None:
            guard = _ImportGuard() if (GUI_BRIDGE is None and not in_caller) else None
            if guard is not None:
                guard.install()                      # 写しを取る前に付ける(戻しの後で自分で外す)
            entry = _OUTER_ENTRY = _Entry(guard, clock)
        else:
            guard = outer.guard                      # 止まっている実行の見張りの下で回す(見張りを重ねない)
            entry = _Entry(guard, None, outer)
            outer.children.append(entry)
        snapshot = _GlobalState.take()
        shown0 = guard.shown_figures if guard is not None else 0
    threads_before = set(threading.enumerate())
    path_token = _push_sys_path(user_dirs)
    me: list = []

    def worker():
        me.append(threading.get_ident())
        if guard is not None and not in_caller:      # 呼び出し側(main)のスレッドは見張らない(Studio の GUI の import)
            guard.recs[me[0]] = recorder             # 見張りが断るのは、入口の作業スレッドからの import だけ
        fn()

    t0 = time.perf_counter()
    outcome["t0"] = t0
    deadline = outcome["deadline"] = None if time_limit_s is None else t0 + time_limit_s + slack_s
    try:
        run.abandoned = _run_with_watchdog(worker, outcome, deadline, stop_event, in_caller=in_caller, clock=clock)
    finally:
        run.ended = time.perf_counter()
        left = None
        if run.abandoned:                            # この入口の作業スレッドの行(無ければ最後の行)
            left = next((r for r in reversed(_ABANDONED) if me and r["thread"].ident == me[0]), None) \
                or (_ABANDONED[-1] if _ABANDONED else None)
        if guard is not None and outer is None and guard.detached_figures:
            run.notes.append(MPL_DETACHED_NOTE % guard.detached_figures)
        if guard is not None and guard.shown_figures != shown0:
            run.notes.append(MPL_SHOWN_NOTE)
        left_threads = _program_threads_alive(threads_before) if not run.abandoned else []
        if left_threads:
            _PROGRAM_THREADS.extend(left_threads)
            names = ", ".join(str(t.name) for t in left_threads[:5]) + (" …" if len(left_threads) > 5 else "")
            run.notes.append(PROGRAM_THREADS_NOTE % (len(left_threads), names))
        _pop_sys_path(path_token)
        with _ENTRY_LOCK:
            waits: list = []
            if outer is None:
                entry.closed = True
                if _OUTER_ENTRY is entry:
                    _OUTER_ENTRY = None
                if left is not None:
                    waits.append(left)
                waits += [c for c in entry.children if not c.done.is_set() or c.left_thread is not None]
            else:
                entry.left_row = left
                entry.left_thread = left["thread"] if left is not None else None
                if left is None and guard is not None and me and not in_caller:
                    guard.recs.pop(me[0], None)      # 残したスレッドは、外側が外すまで見張る
            # 内側: 外側がまだ終わっていなければ、自分の写し(= 止まっている実行の状態)へ戻す。外側が先に終わって
            # いれば戻さない(外側の後始末が、これが終わるのを待って外側の写しへ戻す)
            restored = snapshot.restore() if (outer is None or not outer.closed) else []
            if waits:
                _restore_when_done(waits, snapshot, guard)    # 残した物が終わった所で、もう一度戻して外す
            elif outer is None and guard is not None:
                guard.uninstall()
            entry.done.set()
        if restored:
            run.notes.append("restored after the run: " + ", ".join(restored))
    return run


def run_file(path: str, image, **kw) -> ProgramResult:
    """ファイルを実行の対象にする(:func:`run_program` の ``filename=`` と同じ)。本文はファイルから読む。"""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return run_program(text, image, filename=path, **kw)


def evaluate(source: str, namespace, *, trusted: bool = True, time_limit_s: float | None = None,
             stop_event: threading.Event | None = None) -> dict:
    """実行後の名前空間 *namespace*(``ProgramResult`` か ``ProgramResult.namespace``)で式か文を評価する
    (選んだ行の実行・対話の窓の入口)。``{"value", "stdout", "error", "calls", "notes", "shown"}`` を返す。op の
    呼び出しはその実行の記録に足る。式なら値を返し、文(代入など)なら実行して ``value`` は None。誤りは
    ``"line N: Type: msg"``。``shown`` = この呼び出しの間に ``show()`` / ``plt.show()`` が見せた物(無ければ None)。

    **:func:`run_program` と同じ入口(:func:`_guarded_user_call`)を通る**(2026-11-13 第 3 回レビュー S1):
    作業スレッドからの Qt を断り、GUI の部品の import を見張り、matplotlib は Agg、変えたプロセスの状態
    (``sys.stdout``・環境変数・作業フォルダ …)は戻して ``notes`` に「restored after the run: …」と入れ、
    残した実行・残ったスレッドがある間は始めない。``time_limit_s`` / ``stop_event`` は見張りと op の呼び出しの
    境目の両方で効く。止めたら ``error`` は ``"stopped: …"``、止められなければ ``"could not stop …"``
    (結果は捨て、終わった所でもう一度状態を戻す)。どちらも渡さなければ、終わるまで待つ。

    2026-11-15 第 4 回の確かめ: 名前空間の ``print`` は、終わったら前の物へ戻す(止まっている Debug の実行の間に
    選んだ行を走らせると、続行したプログラムの print が捨てた入れ物に入り、出力に出なかった)。選んだ行が ``print``
    に別の物を入れたら、それは残す。記録役は、名前空間の ``__studio_recorder__`` が :class:`Recorder` **そのもの**の
    時だけ使う(プログラムがそこに置いた物の属性を、入口の外 = 呼び出し側のスレッドで読み書きしない)。"""
    ns = getattr(namespace, "namespace", namespace)
    if ns is None:
        return {"value": None, "stdout": "", "error": "no namespace: run the program first (keep_namespace=True)",
                "calls": [], "notes": [], "shown": None}
    if not trusted:
        return {"value": None, "stdout": "", "error": "not run: untrusted input", "calls": [], "notes": [],
                "shown": None}
    rec = ns.get("__studio_recorder__")
    if type(rec) is not Recorder:                    # 型だけで決める(利用者の物の __bool__ / 属性を呼ばない)
        rec = Recorder()
    out = _BoundedOutput()
    no_print = object()
    prev_print = ns.get("print", no_print)
    mine_print = ns["print"] = _capture_print(out)
    n0 = len(rec.calls)
    shown0 = rec.shown_n
    box: dict = {}
    # op の呼び出しの境目で見る停止の要求と時間の上限は、**この呼び出しの物**にする。記録は前の実行の物を
    # 使い回すので、そのままだと Release の実行の上限が残り、その後の選んだ行の op が「時間切れ」で止まった
    before = (rec.stop_event, rec.time_limit_s, rec.deadline)
    rec.stop_event, rec.time_limit_s = stop_event, time_limit_s
    rec.deadline = None if time_limit_s is None else time.perf_counter() + time_limit_s

    def body():
        token = _ACTIVE.set(rec)
        try:
            try:
                code = compile(source, "<studio-console>", "eval")
                is_expr = True
            except SyntaxError:
                code = compile(source, "<studio-console>", "exec")
                is_expr = False
            box["value"] = eval(code, ns) if is_expr else (exec(code, ns), None)[1]   # noqa: S307,S102 -- 利用者が打った物
            box["err"] = None
        except SyntaxError as e:
            box["value"], box["err"] = None, "line %d: SyntaxError: %s" % (e.lineno or 1, e.msg)
        except ProgramStopped as e:
            box["value"], box["err"] = None, "stopped: %s" % ("time limit" if e.reason == "time_limit" else "on request")
        except BaseException as e:                   # noqa: BLE001 -- 行番号つきで返す
            box["value"] = None
            box["err"] = "line %d: %s: %s" % (_err_line_from_tb(_EXC_TRACEBACK.__get__(e), "<studio-console>") or 1,
                                               _tname(type(e)), _exception_text(e))
        finally:
            try:
                _ACTIVE.reset(token)
            except BaseException:                    # noqa: BLE001 -- 遅れて届いた止めの例外
                pass

    def guarded():
        try:
            body()
        except BaseException:                        # noqa: BLE001 -- body の外で届いた止めの例外
            box.setdefault("err", "stopped")

    try:
        run = _guarded_user_call(guarded, source, recorder=rec, outcome={}, time_limit_s=time_limit_s,
                                 stop_event=stop_event)
    finally:
        rec.stop_event, rec.time_limit_s, rec.deadline = before
        if ns.get("print") is mine_print:            # 選んだ行が print を書き換えていなければ、前の物へ戻す
            if prev_print is no_print:
                ns.pop("print", None)
            else:
                ns["print"] = prev_print
    if run.refused is not None:
        return {"value": None, "stdout": "", "calls": [], "error": run.refused, "notes": [], "shown": None}
    if run.abandoned:
        return {"value": None, "stdout": out.getvalue(), "calls": [], "notes": run.notes, "shown": None,
                "error": "could not stop the selected lines within %.1f s — they go on running in the background "
                         "and their results are ignored" % _STOP_GRACE_S}
    return {"value": box.get("value"), "stdout": out.getvalue(), "error": box.get("err"), "calls": rec.calls[n0:],
            "notes": run.notes, "shown": rec.shown if rec.shown_n != shown0 else None}


#: 取り込む標準出力の上限(文字数)。越えたら**古い方から**捨て、捨てた事を先頭に書く(50 MB の print で
#: メモリと画面を埋めない)。
MAX_STDOUT_CHARS = 1_000_000


class _BoundedOutput:
    """``print`` の取り込み先。末尾 :data:`MAX_STDOUT_CHARS` 文字だけを持つ(``io.StringIO`` と同じ write / getvalue)。"""

    def __init__(self, limit: int | None = None):
        self.limit = int(MAX_STDOUT_CHARS if limit is None else limit)
        self._parts: list = []
        self._size = 0
        #: 今までに書かれた文字数(捨てた分も含む)。止まるたびに「前に出した分」を数えるのに使う。
        self.total = 0

    def write(self, s) -> int:
        s = str(s)
        self._parts.append(s)
        self._size += len(s)
        self.total += len(s)
        if self._size > 2 * self.limit:              # たまにまとめて詰める(1 回の write ごとに繋ぎ直さない)
            tail = "".join(self._parts)[-self.limit:]
            self._parts, self._size = [tail], len(tail)
        return len(s)

    @property
    def dropped(self) -> int:
        return self.total - min(self._size, self.limit)

    def getvalue(self) -> str:
        text = "".join(self._parts)
        if len(text) > self.limit:
            text = text[-self.limit:]
        if self.total > len(text):
            return "… (%d earlier characters of output dropped)\n" % (self.total - len(text)) + text
        return text


def _capture_print(buf) -> Callable:
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
    for k, v in list(ns.items()):
        if type(k) is not str or k.startswith("_") or k in ("__builtins__",):
            continue
        if k in base and base[k] is v:
            continue                                 # 前置きの名前(書き換えていない物)
        if _is(v, types.ModuleType):
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
                keep_namespace: bool = True, conditions=None, resume_after_lines: int = 0,
                pause_hook: Callable | None = None) -> ProgramResult:
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
    * ``keep_namespace``: 実行後の名前空間を ``ProgramResult.namespace`` に残す(:func:`evaluate` が使う)。
    * ``conditions``: 条件つきブレークポイント ``{行: 式}``(Debug だけ。偽なら止めない、評価できなければ止める)。
    * ``resume_after_lines``: 続行の走り直しで、最初の N 行(すでに通った所)ではブレークポイントで止めない
      (2026-11-13 UI の繋ぎ: 止まった所から続行 = ``resume_after_lines=前の lines_run + 1``、1 行実行 =
      ``max_lines=前の lines_run + 1``。止まった行はまだ実行していないので、走り直しではそこを素通りさせる)。
    * ``pause_hook``(Debug だけ): 渡すと、ブレークポイント・1 行実行で実行を**終えずにその場で待つ**。
      ``pause_hook(その時点の ProgramResult) -> "continue" / "step" / "stop"``(または
      ``{"command": …, "breakpoints": […], "conditions": {…}}`` = 続ける前にブレークポイントを差し替える)を
      プログラムの作業スレッドから呼び、戻るまで待つ。"continue" は止まった所から続け、"step" は 1 行実行して
      また呼び、"stop" は ``stopped="stop_requested"`` で終える。待っている時間は時間の上限に数えない。
      待っている間に ``stop_event`` が立てば見張りが止める(フックが見ていなくても戻る)。Qt を直接使う
      プログラムを main スレッドで回す形(§15)では待てないので、今までどおり止まった所で実行を終える。
      止まった所が関数の中なら、その枠の局所変数を ``ProgramResult.locals``、呼び出しの積み重ねを ``stack`` に入れる。"""
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
        result.errors = [result.not_run_reason]      # 黙って何もしない、にしない
        return result
    if image is None:
        result.errors = ["line 1: a Python program needs an input image"]
        result.error_line = 1
        return result
    def refuse(why) -> ProgramResult:
        """「ran」と報告しない: 残した実行・残ったスレッドがある、作業スレッドからの Qt(H3 / R5 / M1)。"""
        result.not_run_reason, ln = why
        result.errors = [result.not_run_reason]
        if ln is not None:
            result.error_line = ln
        return result

    why = _refusal(text)                             # 先に断る(構文の誤りより前。入口の中でももう一度確かめる)
    if why is not None:
        return refuse(why)
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
    rec.param_dirs = params_search_dirs(project_dir=project_dir, program_dir=program_dir)
    inp = rec.set_input(image)
    base = prelude_namespace()
    ns = dict(base)
    ns.update(__name__="__studio_program__", __builtins__=builtins, img=inp, image=inp)
    if filename:
        ns["__file__"] = code_name
    ns["__studio_recorder__"] = rec
    clock = _Clock()
    tracer = _Tracer(time_limit_s, breakpoints, skip_hits, max_lines, stop_event, filename=code_name,
                     conditions=conditions, resume_after_lines=resume_after_lines, clock=clock)
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
    out = _BoundedOutput()
    # print はプログラムの名前空間の中だけで取り込む(sys.stdout を差し替えると、作業スレッドで回している間に
    # Studio 本体や他のスレッドの出力まで取り込んでしまう)。file= を渡した print はそのまま。
    ns["print"] = _capture_print(out)
    hits0 = memo.hits if memo is not None else 0
    in_caller = _runs_in_caller(text)
    outcome: dict = {}
    t_call = time.perf_counter()

    def body():
        """作業スレッドの中身: contextvar・settrace はこのスレッドだけに付ける。"""
        token = _ACTIVE.set(rec)
        try:
            if not release:
                sys.settrace(tracer.global_trace)
            try:
                exec(code, ns)                       # noqa: S102 -- 本物の Python(trusted のときだけ)
            finally:
                if not release:
                    sys.settrace(None)
            outcome["kind"] = "ok"
        except ProgramStopped as e:
            outcome.update(kind="stopped", reason=e.reason,
                           line=e.line or _err_line_from_tb(_EXC_TRACEBACK.__get__(e), code_name) or 0)
        except SystemExit as e:
            outcome.update(kind="exit", code=_EXIT_CODE.__get__(e),
                           line=_err_line_from_tb(_EXC_TRACEBACK.__get__(e), code_name) or 0)
        except BaseException as e:                   # noqa: BLE001 -- 行番号つきで返す(KeyboardInterrupt も)
            outcome.update(kind="error", exc=e)
        finally:
            try:
                _ACTIVE.reset(token)
            except BaseException:                    # noqa: BLE001 -- 遅れて届いた止めの例外
                pass

    def describe_once() -> dict:
        """結果を文字にする(作業スレッド・見張りの内側)。利用者のコードを呼びうるのは :func:`_exception_text` だけ。"""
        texts: dict = {}
        kind_ = outcome.get("kind")
        if kind_ == "exit":
            code_ = outcome.get("code")
            texts["code"] = _safe_text(code_) or "<%s>" % _tname(type(code_))
        elif kind_ == "error":
            e = outcome["exc"]
            tb = _EXC_TRACEBACK.__get__(e)
            texts["type"] = _tname(type(e))
            texts["where"] = _err_location(tb, code_name, user_dirs)
            texts["line"] = _err_line_from_tb(tb, code_name) or 0
            if _is(e, ModuleNotFoundError):
                name = _IMPORT_NAME.__get__(e)
                texts["missing"] = name.split(".")[0] if type(name) is str and name else None
            if "exc_text" not in outcome:            # やり直しになっても __str__ は 1 回しか呼ばない
                outcome["exc_text"] = "<the text of this %s is not available>" % texts["type"]
                outcome["exc_text"] = _exception_text(e)
                # ここから先は利用者のコードを呼ばない: 残りの分の時間を取り直す(__str__ が上限を使い切っていても表は作る)
                outcome["describe_deadline"] = time.perf_counter() + _DESCRIBE_LIMIT_S
            texts["text"] = outcome["exc_text"]
        filled = ProgramResult(syntax=syn, config=config)
        fill(filled)
        texts["filled"] = filled
        return texts

    def describe():
        """プログラムが終わった後、**結果を文字にする処理の全部**をここ(作業スレッド・見張りの内側・上限つき)で
        済ませる。呼び出し側(GUI)は出来上がった str と表だけを受け取り、利用者の値には触らない
        (2026-11-13 第 2 回レビュー R1: 例外の ``__str__``・``sys.exit(obj)`` の ``__repr__``・メタクラスの
        ``__eq__`` / ``__name__``・``__class__`` のプロパティが、見張りの外で上限なしに呼ばれていた)。"""
        outcome["phase"] = "describe"               # 先に段を切り替える(見張りがプログラムの時間切れで撃つのをやめる)
        outcome.setdefault("describe_deadline", time.perf_counter() + _DESCRIBE_LIMIT_S)
        for _attempt in range(4):                    # 遅れて届いた止めの例外で途中から抜けたら、作り直す
            try:
                outcome["texts"] = describe_once()
                break
            except BaseException:                    # noqa: BLE001 -- 止めの例外・思わぬ誤り
                if time.perf_counter() > outcome["describe_deadline"]:
                    break
        outcome["phase"] = "done"

    def guarded():
        try:
            body()
        except BaseException:                        # noqa: BLE001 -- body の外で届いた止めの例外は捨てる
            outcome.setdefault("kind", "stopped")
        for _attempt in range(4):                    # 段の切り替えの前後に届いた止めの例外では、やり直す
            try:
                describe()
                break
            except BaseException:                    # noqa: BLE001
                continue
        outcome["phase"] = "done"

    def fill(res: ProgramResult, live: bool = False, values: bool = True) -> None:
        """実行の状態を *res* へ写す(終わった時の結果と、止まって待つ時の途中の結果で同じ)。*live* = 途中:
        記録は写しを渡す(続きの実行が足しても、渡した結果は変わらない)。型の判定は同一性だけ(利用者のコードを
        呼ばない)。*values* = False: 値に触らない(結果を文字にする段が終わらなかった時の最小の埋め方)。"""
        res.elapsed_s = time.perf_counter() - outcome.get("t0", t_call) - clock.paused_s
        res.lines_run = tracer.lines
        res.notes.extend(tracer.notes)
        res.stdout = out.getvalue()
        res.stdout_total = out.total
        res.calls = list(rec.calls) if live else rec.calls
        res.clamped = rec.clamped
        res.directives = rec.directives
        res.windows = rec.windows
        if values:
            res.output, res.output_source = rec.output()
            res.output_sort = rec.sort_of(res.output) if _is(res.output, np.ndarray) else _kind_of(res.output)
            res.variables, res.values = _variables(ns, base, rec)
            if keep_namespace:
                res.namespace = ns
        res.memo_hits = (memo.hits - hits0) if memo is not None else 0

    def on_pause(reason, ln, frame):
        """作業スレッド: 止まった時点の結果を作って ``pause_hook`` に渡し、戻るまで待つ(時計は止める)。"""
        snap = ProgramResult(syntax=syn, config=config)
        snap.ran, snap.filename = True, code_name
        snap.stopped, snap.stopped_line = reason, ln
        snap.notes = list(result.notes)
        snap.locals, snap.stack = dict(tracer.locals), list(tracer.stack)
        fill(snap, live=True)
        t_wait = time.perf_counter()
        clock.paused = True
        try:
            return pause_hook(snap)
        finally:
            clock.paused_s += time.perf_counter() - t_wait   # 先に足してから「待ち」を解く(見張りが誤って撃たない)
            clock.paused = False

    if pause_hook is not None and not release and not in_caller:
        tracer.on_pause = on_pause                   # Qt を直接使うプログラムを main スレッドで回す形(§15)では待てない
    # 守りの全部(断り・import の見張り・状態の写しと戻し・残した実行の後始末)は、選んだ行と共通の入口の中。
    # Debug は行フックが先に止める(行番号つきの文)ので、見張りの上限は少し遅らせる(見張りは保険)
    run = _guarded_user_call(guarded, text, recorder=rec, outcome=outcome, time_limit_s=time_limit_s,
                             slack_s=0.0 if release else _WATCHDOG_DEBUG_SLACK_S, stop_event=stop_event,
                             clock=clock, user_dirs=user_dirs)
    if run.refused is not None:                      # 上で確かめた後に、残した実行・残ったスレッドが増えていた
        return refuse((run.refused, run.refused_line))
    abandoned, deadline = run.abandoned, outcome.get("deadline")
    result.ran = True
    kind = outcome.get("kind")
    texts = outcome.get("texts") if not abandoned else None      # 作業スレッドが作り終えた文と表(無ければ None)
    if abandoned:
        reason = "time limit %.3g s" % time_limit_s \
            if (deadline is not None and run.ended - clock.paused_s > deadline) else "a stop request"
        result.stopped = "unstoppable"
        result.errors = ["could not stop the program after %s within %.1f s — it is inside a long call "
                         "(C code, time.sleep, a big numpy operation) or keeps catching the stop; it goes on "
                         "running in the background and its results are ignored" % (reason, _STOP_GRACE_S)]
        result.notes.append("abandoned run: see studio_program.abandoned_runs()")
        result.notes.append("until the abandoned run ends, new runs are refused; the process state is restored "
                            "again when it ends")
    elif kind == "stopped":
        reason, ln = outcome.get("reason", "stop_requested"), outcome.get("line", 0)
        result.stopped, result.stopped_line = reason, ln
        if reason in ("breakpoint", "step"):
            result.locals, result.stack = dict(tracer.locals), list(tracer.stack)
        if reason == "time_limit":
            result.errors = ["line %d: stopped: time limit %.3g s exceeded" % (ln, time_limit_s)]
            result.error_line = ln
        elif reason == "stop_requested":
            result.errors = ["line %d: stopped on request" % ln]
            result.error_line = ln
    elif kind == "exit":
        ln = outcome["line"]
        code_text = texts["code"] if texts else "<not available>"
        result.errors = ["line %d: the program called exit(%s)" % (ln, code_text)]
        result.error_line = ln
    elif kind == "error":
        # ここ(呼び出し側)では例外そのものに触らない: 作業スレッドが作った str だけを使う
        if texts:
            result.error_file, deep_line = texts["where"]
            ln = texts["line"]
            if result.error_file != code_name and deep_line is not None:
                result.notes.append("the error is in %s line %d (called from line %d)"
                                    % (result.error_file, deep_line, ln))
            else:
                result.error_file = code_name
            msg = "line %d: %s: %s" % (ln, texts["type"], texts["text"])
            if texts.get("missing"):
                # 入っていない物は ImportError をそのまま見せ、入れ方を 1 行で言う(Studio と同じ Python へ)
                msg += " — install it into Studio's Python: \"%s\" -m pip install %s" % (sys.executable,
                                                                                         texts["missing"])
        else:
            ln, result.error_file = 0, code_name
            msg = "line %d: the program raised an error, but its text could not be made in time" % ln
        result.errors = [msg]
        result.error_line = ln
    result.notes.extend(run.notes)                   # 外した図・plt.show()・残ったスレッド・戻した状態(入口が作る)
    if texts:                                        # 作業スレッドが作り終えた表を写す(呼び出し側は値に触らない)
        f = texts["filled"]
        for name in ("elapsed_s", "lines_run", "stdout", "stdout_total", "calls", "clamped", "directives",
                     "windows", "output", "output_source", "output_sort", "variables", "values", "namespace",
                     "memo_hits"):
            setattr(result, name, getattr(f, name))
        result.notes.extend(f.notes)
    else:
        fill(result, values=False)
        if not abandoned:
            result.notes.append("the result could not be described in time: the variables are not listed")
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


def _directive_to_python(code: str) -> str | None:
    """表示の指示の行(``dev_set_lut (gray)``)を Python の呼び出しの文字列にする。変換できなければ None。

    **引数は定数(数・引用符つきの文字列)と素の語だけ**を通す(素の語は文字列にする)。それ以外 — 呼び出し・
    属性・添字・演算・キーワード引数・内包表記 … — は断る(fail-closed)。パイプラインのファイルはデータとして
    確認なしに開かれるので、指示の引数に式を書けると「Python に変換 → 実行」で任意のコードが走る
    (2026-11-13 レビュー H1)。出す文字列は構文木から作り直し、元の文字列は写さない。"""
    c = (code if "(" in code else code + " ()").strip()
    if "\n" in c or "\r" in c:
        return None
    try:
        call = ast.parse(c, mode="eval").body
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.keywords:
        return None
    args = []
    for x in call.args:
        if isinstance(x, ast.Name):
            args.append(ast.Constant(x.id))          # HDevelop の素の語(`dev_set_lut (gray)`)は文字列にする
            continue
        node = x.operand if isinstance(x, ast.UnaryOp) and isinstance(x.op, (ast.USub, ast.UAdd)) else x
        if not isinstance(node, ast.Constant) or type(node.value) not in (int, float, str, bool):
            return None
        if node is not x and type(node.value) not in (int, float):
            return None                              # 符号は数にだけ
        args.append(x)
    return ast.unparse(ast.Call(func=ast.Name(call.func.id, ast.Load()), args=args, keywords=[]))


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
                c = _directive_to_python(code)
                if c is None:
                    return "", ["line %d: cannot convert the directive %r — its arguments must be numbers, quoted "
                                "text or plain words" % (i + 1, code)]
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
