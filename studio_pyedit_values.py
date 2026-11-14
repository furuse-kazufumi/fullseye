# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_pyedit_values — 変数の一覧とウォッチの論理(Qt なし)。

* 値の「表示用の要約」(``summarize``): 型・形と dtype・最小/最大/平均・長さ・先頭の数個・文字列の切り詰め。
  大きな配列は全部を走査しない(標本で数え、標本だと表示する)。利用者のオブジェクトの ``__repr__`` が
  例外を出す・遅い・巨大な場合でも固まらない(時間と長さの上限。例外は「repr が失敗」と出す)。
* 木の展開(``children``): dict / list / tuple / set / 構造化配列 / オブジェクト。オブジェクトの属性は
  ``__dict__`` と ``__slots__`` だけ(プロパティを勝手に呼ばない)。``explicit_attrs`` で選んだ名前だけ追加で読む。
* 変わった値の印(``VariableTracker``): 新しい・変わった・消えた。
* 値の編集の型の検査(``parse_edit``): 数・文字列・真偽値だけ。
* ウォッチ(``WatchEvaluator`` / ``WatchList``): 利用者が自分で書いた式を、自分の名前空間で評価する。時間の上限つき、
  例外は理由つきで返す。条件つきブレークポイントも同じ評価器(``condition``)。
* 画像らしい配列の判定とサムネイル(``is_image_like`` / ``thumbnail_u8``)。

供給元(Protocol)
    ``VariableSource.snapshot()`` は名前空間の ``dict``(または ``(名前, 値)`` の列)、``set_value(path, value)`` は値の書き込み。
    ``path`` は ``(("name", "cfg"), ("item", "k"), ("attr", "x"))`` のような「段」の列。

正直な限界
    * 時間切れの打ち切りは、別のスレッドで走らせて、時間が来たら ``PyThreadState_SetAsyncExc`` で例外を送る方式。
      Python のコードの無限ループは止まるが、C の長い呼び出しの中では次の命令まで止まらない(その間 UI は
      待たない。スレッドは裏で残る)。
    * 大きな配列の変化の判定は標本(最大 65,536 要素)で行う。標本の外だけを書き換えると「変わった」印が付かない。
"""
from __future__ import annotations

import builtins
import ctypes
import inspect
import itertools
import json
import math
import threading
import time
import types
import zlib
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, Protocol, Sequence, runtime_checkable

import numpy as np

import studio_pyedit_safe as safe

#: 派生した型がメソッドを差し替えられる「値」の型。利用者が派生した物はその種類として扱わない。
_VALUE_CLASSES = (str, bytes, bytearray, np.ndarray, np.generic)


def _isinst(obj, cls) -> bool:
    """``isinstance`` の代わり。``type(obj)`` だけで決め(``obj.__class__`` のプロパティ = 利用者のコードを
    読まない)、利用者が派生した str / bytes / ndarray / numpy のスカラは、その種類として扱わない(``len`` や
    添字が利用者のメソッドになり得る。型の名前だけの「オブジェクト」として見せる)。入れ物(list / dict …)の
    派生は、基底のメソッド(``list.__iter__`` など)で読むので通す。"""
    t = type(obj)
    if not issubclass(t, cls):
        return False
    if issubclass(t, _VALUE_CLASSES) and not safe.is_library_type(t):
        return False
    return True


def _ident(text: str) -> str:
    return text


# --------------------------------------------------------------------------- #
# 時間の上限つきの呼び出し
# --------------------------------------------------------------------------- #
class _Timeout(BaseException):
    """時間切れで送り込む例外(利用者の ``except Exception`` で握りつぶされないよう BaseException)。"""


_STUCK: set = set()       # 時間切れになった (型, id)。同じ物の repr を繰り返さない


def _env_snapshot() -> tuple:
    import os
    try:
        cwd = os.getcwd()
    except OSError:
        cwd = None
    return dict(os.environ), cwd


def _env_restore(snap: tuple) -> bool:
    """利用者の ``__repr__`` などが変えた環境変数と作業フォルダを、呼ぶ前の値へ戻す。変わっていたら True。"""
    import os
    env, cwd = snap
    changed = False
    if dict(os.environ) != env:
        for k in [k for k in os.environ if k not in env]:
            del os.environ[k]
        for k, v in env.items():
            if os.environ.get(k) != v:
                os.environ[k] = v
        changed = True
    try:
        if cwd is not None and os.getcwd() != cwd:
            os.chdir(cwd)
            changed = True
    except OSError:
        pass
    return changed


def stray_threads() -> list:
    """時間切れの後も止まらずに残っている、利用者のコード(``__repr__``・ウォッチの式)のスレッド(生きている物だけ)。

    1 本でも残っている間は、新しいスレッドを起こさない(:func:`run_with_timeout` は ``"busy"`` を返す)。止めの
    例外が届かずに保留のまま残ると、CPython 3.11 では ``sys.settrace`` の下のコードが約 300 倍遅くなり、次の Debug の
    実行が何もしなくても時間切れになる(2026-11-13 第 2 回レビュー R5)。Studio は、残っている間は次の実行を始めず、
    そう知らせる。"""
    STUCK_THREADS[:] = [t for t in STUCK_THREADS if t.is_alive()]
    return list(STUCK_THREADS)


def _remember_stray(th, snap=None) -> None:
    STUCK_THREADS.append(th)
    if snap is not None:                                     # 終わった所で、そのスレッドが変えた環境を戻す
        def reap():
            th.join()
            _env_restore(snap)
        threading.Thread(target=reap, name="pyedit-reaper", daemon=True).start()


def run_with_timeout(fn: Callable, timeout_s: float) -> tuple:
    """``fn()`` を別スレッドで走らせる。返り値 ``(状態, 値)``: 状態は ``"ok"`` / ``"error"``(値は例外)/
    ``"timeout"`` / ``"busy"``(前の時間切れのスレッドがまだ残っているので、呼ばなかった)。
    ``fn`` が変えた環境変数と作業フォルダは、戻った所(残ったなら終わった所)で呼ぶ前の値へ戻す。"""
    if stray_threads():
        return "busy", None
    box: dict = {}
    snap = _env_snapshot()

    def target():
        try:
            box["v"] = fn()
        except _Timeout:
            box["timeout"] = True
        except BaseException as exc:                         # noqa: BLE001 — 利用者のコードの何が出ても受ける
            box["e"] = exc

    th = threading.Thread(target=target, name="pyedit-eval", daemon=True)
    th.start()
    th.join(timeout_s)
    if th.is_alive():
        try:                                                 # 無限ループなら止まる(C の中なら次の命令で)
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(th.ident), ctypes.py_object(_Timeout))
        except Exception:                                    # noqa: BLE001
            pass
        th.join(0.05)
        if th.is_alive():
            _remember_stray(th, snap)                        # 残った: 数に入れ、終わった所で環境を戻す
        else:
            _env_restore(snap)
        return "timeout", None
    _env_restore(snap)
    if "e" in box:
        return "error", box["e"]
    if box.get("timeout"):
        return "timeout", None
    return "ok", box.get("v")


# --------------------------------------------------------------------------- #
# 要約
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Limits:
    """要約の上限。"""
    max_text: int = 100            # 1 行の文字数
    repr_timeout_s: float = 0.05   # 利用者の __repr__ を待つ時間
    sample_max: int = 200_000      # 配列の統計に使う最大の要素数
    preview_items: int = 4         # コンテナの先頭の数個
    max_children: int = 200        # 木の 1 段の子の数


DEFAULT_LIMITS = Limits()


@dataclass(frozen=True)
class Summary:
    kind: str                       # none/bool/int/float/complex/str/bytes/ndarray/scalar/list/tuple/set/dict/function/class/module/object/error
    type_name: str
    text: str                       # 1 行の値の要約
    shape: tuple | None = None
    dtype: str | None = None
    length: int | None = None
    detail: str = ""                # 複数行の説明(ツールヒント)
    is_image: bool = False
    expandable: bool = False
    editable: bool = False
    sampled: bool = False
    problem: str | None = None      # "repr_failed" / "repr_timeout" / "circular"


def _clip(s: str, n: int) -> str:
    s = s.replace("\r", " ").replace("\n", " ")
    return s if len(s) <= n else s[:max(0, n - 1)] + "…"


def type_name_of(v) -> str:
    t = type(v)
    name = safe.type_name(v)
    mod = safe.module_of(t)                                            # メタクラスの属性の読み出しを通さない
    if type(mod) is not str or mod in ("builtins", "__main__"):
        return name
    return "%s.%s" % (mod.split(".")[0], name)


def _sample(a: np.ndarray, limit: int) -> tuple:
    """配列の標本(1 次元)。``(標本, 標本か)``。全部をコピー・走査しない。"""
    n = int(a.size)
    if n <= limit:
        if a.flags.c_contiguous or a.flags.f_contiguous:
            return a.reshape(-1, order="A"), False
        return np.asarray(a).ravel(), False
    step = -(-n // limit)
    if a.flags.c_contiguous or a.flags.f_contiguous:
        return a.reshape(-1, order="A")[::step], True
    return np.asarray(a.flat[::step]), True


def _num(x: float) -> str:
    if x != x:
        return "nan"
    if x in (math.inf, -math.inf):
        return "inf" if x > 0 else "-inf"
    return "%.6g" % x


def is_image_like(a) -> bool:
    """画像らしい配列: 数値の 2 次元(短い辺が 8 以上)か、3 次元で最後が 1・3・4。"""
    if not _isinst(a, np.ndarray) or a.dtype.kind not in "biuf" or a.dtype.names:
        return False
    if a.ndim == 2:
        return min(a.shape) >= 8
    if a.ndim == 3 and a.shape[2] in (1, 3, 4):
        return min(a.shape[:2]) >= 8
    return False


def _summarize_array(a: np.ndarray, lim: Limits, tr) -> Summary:
    shape = tuple(int(s) for s in a.shape)
    dims = "×".join(str(s) for s in shape) or "scalar"
    kind = "ndarray"
    if a.dtype.names:
        names = ", ".join(a.dtype.names[:6]) + ("…" if len(a.dtype.names) > 6 else "")
        return Summary(kind, "ndarray", "%s %s  [%s]" % (dims, a.dtype, names), shape, str(a.dtype), int(a.shape[0]) if a.ndim else None,
                       detail="%s\n%s: %s" % (dims, tr("fields"), ", ".join(a.dtype.names)), expandable=True)
    if a.size == 0:
        return Summary(kind, "ndarray", "%s %s (%s)" % (dims, a.dtype, tr("empty")), shape, str(a.dtype), 0)
    k = a.dtype.kind
    if k in "biuf":
        samp, sampled = _sample(a, lim.sample_max)
        if k == "f":
            fin = np.isfinite(samp)
            nn = int(samp.size - np.count_nonzero(fin))
            vals = samp[fin] if nn else samp
        else:
            nn, vals = 0, samp
        if vals.size:
            if k == "b":
                stats = "%d true" % int(np.count_nonzero(vals))
                mn = mx = mean = None
            else:
                mn, mx = float(vals.min()), float(vals.max())
                mean = float(vals.mean(dtype=np.float64))
                stats = "[%s .. %s] %s %s" % (_num(mn), _num(mx), tr("mean"), _num(mean))
        else:
            stats = tr("all non-finite")
        extra = (" · %d %s" % (nn, tr("non-finite"))) if nn else ""
        approx = ("≈ " if sampled else "")
        text = "%s %s %s%s%s" % (dims, a.dtype, approx, stats, extra)
        det = "%s %s\n%s: %s" % (dims, a.dtype, tr("size"), _bytes(a.nbytes))
        if sampled:
            det += "\n" + tr("statistics are from a sample of the elements")
        return Summary(kind, "ndarray", text, shape, str(a.dtype), int(a.shape[0]) if a.ndim else None,
                       detail=det, is_image=is_image_like(a), sampled=sampled)
    if k == "c":
        samp, sampled = _sample(a, lim.sample_max)
        return Summary(kind, "ndarray", "%s %s |max| %s" % (dims, a.dtype, _num(float(np.abs(samp).max()))),
                       shape, str(a.dtype), int(a.shape[0]) if a.ndim else None, sampled=sampled)
    first = ""
    if k in "US" and a.size:
        first = " " + _clip(repr(a.reshape(-1, order="A")[0]) if (a.flags.c_contiguous or a.flags.f_contiguous) else "", 30)
    return Summary(kind, "ndarray", "%s %s%s" % (dims, a.dtype, first), shape, str(a.dtype),
                   int(a.shape[0]) if a.ndim else None)


def _bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%d %s" % (n, unit) if unit == "B" else "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%d B" % n


def _brief(v, lim: Limits) -> str:
    """コンテナの先頭の要素の短い表示(再帰しない・利用者のコードを呼ばない)。"""
    t = type(v)
    if v is None or t is bool:
        return str(v)
    if t is int:
        return str(v) if v.bit_length() < 200 else "int(%d bits)" % v.bit_length()
    if t is float:
        return _num(v)
    if t is str:
        return repr(v[:20]) if len(v) <= 20 else repr(v[:19]) + "…"
    if _isinst(v, np.ndarray):
        return "ndarray[%s]" % "×".join(str(s) for s in v.shape)
    if _isinst(v, np.generic):
        try:
            return _num(float(v)) if v.dtype.kind in "iuf" else str(v.dtype)
        except Exception:                                    # noqa: BLE001
            return safe.type_name(v)
    if safe.tin(t, (list, tuple, set, frozenset, dict)):
        return "%s[%d]" % (safe.name_of(t), _base_len(v))
    return safe.name_of(t)


def _base_len(v) -> int:
    if _isinst(v, dict):
        return dict.__len__(v)
    if _isinst(v, list):
        return list.__len__(v)
    if _isinst(v, tuple):
        return tuple.__len__(v)
    if _isinst(v, (set, frozenset)):
        return (set if _isinst(v, set) else frozenset).__len__(v)
    return 0


def _items_of(v, n: int) -> list:
    """コンテナの先頭 ``n`` 個(基底クラスの反復だけを使い、利用者の ``__iter__`` を呼ばない)。"""
    if _isinst(v, dict):
        return list(itertools.islice(dict.items(v), n))
    if _isinst(v, list):
        return list(itertools.islice(list.__iter__(v), n))
    if _isinst(v, tuple):
        return list(itertools.islice(tuple.__iter__(v), n))
    if _isinst(v, (set, frozenset)):
        return list(itertools.islice((set if _isinst(v, set) else frozenset).__iter__(v), n))
    return []


def summarize(value, limits: Limits = DEFAULT_LIMITS, tr: Callable = _ident) -> Summary:
    """値を 1 行の要約にする。固まらない・落ちない(どんな値でも ``Summary`` を返す)。"""
    lim = limits
    try:
        return _summarize(value, lim, tr)
    except Exception as exc:                                 # noqa: BLE001 — 要約の失敗で一覧を落とさない
        return Summary("error", type_name_of(value), tr("summary failed: %s") % _clip(safe.exception_text(exc), 60),
                       problem="repr_failed")


def _summarize(v, lim: Limits, tr) -> Summary:
    t = type(v)
    tn = type_name_of(v)
    if v is None:
        return Summary("none", "NoneType", "None")
    if t is bool:
        return Summary("bool", "bool", str(v), editable=True)
    if t is int:
        txt = str(v) if v.bit_length() < 4000 else "int (%d bits)" % v.bit_length()
        return Summary("int", "int", _clip(txt, lim.max_text), editable=True)
    if t is float:
        return Summary("float", "float", _num(v), editable=True)
    if t is complex:
        return Summary("complex", "complex", "%s%+sj" % (_num(v.real), _num(v.imag)))
    if _isinst(v, str):
        r = repr(v[:lim.max_text + 1])
        return Summary("str", tn, _clip(r, lim.max_text), length=len(v), editable=(t is str),
                       detail="%s: %d" % (tr("length"), len(v)))
    if _isinst(v, (bytes, bytearray)):
        return Summary("bytes", tn, "%s[%d] %s" % (safe.name_of(t), len(v), v[:12].hex(" ")), length=len(v))
    if _isinst(v, np.ndarray):
        return _summarize_array(v, lim, tr)
    if _isinst(v, np.generic):
        try:
            txt = _num(float(v)) if v.dtype.kind in "f" else str(v.item())
        except Exception:                                    # noqa: BLE001
            txt = tn
        return Summary("scalar", tn, "%s (%s)" % (txt, v.dtype), dtype=str(v.dtype),
                       editable=bool(v.dtype.kind in "biuf"))
    if _isinst(v, (list, tuple, set, frozenset, dict)):
        n = _base_len(v)
        items = _items_of(v, lim.preview_items)
        if _isinst(v, dict):
            body = ", ".join("%s: %s" % (_brief(k, lim), _brief(x, lim)) for k, x in items)
        else:
            body = ", ".join(_brief(x, lim) for x in items)
        more = ", …" if n > len(items) else ""
        br = {"list": "[%s]", "tuple": "(%s)", "set": "{%s}", "frozenset": "{%s}", "dict": "{%s}"}[
            "dict" if _isinst(v, dict) else "list" if _isinst(v, list) else "tuple" if _isinst(v, tuple)
            else "set" if _isinst(v, set) else "frozenset"]
        kind = "dict" if _isinst(v, dict) else "list" if _isinst(v, list) else "tuple" if _isinst(v, tuple) else "set"
        return Summary(kind, tn, _clip("%s[%d] " % (safe.name_of(t), n) + br % (body + more), lim.max_text),
                       length=n, expandable=n > 0)
    if _isinst(v, types.ModuleType):
        return Summary("module", "module", "module " + _module_name(v))
    if _isinst(v, type):
        return Summary("class", "type", "class " + safe.name_of(v), expandable=False)
    if _isinst(v, (types.FunctionType, types.BuiltinFunctionType, types.MethodType)):
        return Summary("function", tn, _clip(_callable_text(v), lim.max_text))
    return _summarize_object(v, lim, tr, tn)


_FUNC = types.FunctionType.__dict__


def _module_name(v) -> str:
    """モジュールの名前(モジュールの ``__dict__`` から読む。派生した型の ``__getattribute__`` を通さない)。"""
    try:
        n = types.ModuleType.__dict__["__dict__"].__get__(v).get("__name__")
    except Exception:                                        # noqa: BLE001
        n = None
    return n if type(n) is str else "?"


def _static_signature(f, bound: bool) -> str:
    """利用者の関数 *f* の引数の並びを ``__code__`` から作る(:func:`studio_pyedit_safe.static_parameters`)。
    **既定値は文字にしない**(``…`` と書く。``__repr__`` を呼ばない)。*bound* = 束縛メソッド(先頭の引数を書かない)。"""
    params = safe.static_parameters(f, bound)
    if params is None:
        raise TypeError("not a function")
    parts = []
    kinds = [k for _n, _t, k in params]
    last_only = max((i for i, k in enumerate(kinds) if k == "positional_only"), default=-1)
    star = "var_positional" in kinds
    for i, (_n, text, kind) in enumerate(params):
        if kind == "keyword" and not star and (i == 0 or kinds[i - 1] != "keyword"):
            parts.append("*")
        parts.append(text)
        if i == last_only:
            parts.append("/")
    return "(" + ", ".join(parts) + ")"


def _callable_text(v) -> str:
    """関数・メソッドの「名前(引数)」。ライブラリの関数(:func:`studio_pyedit_safe.is_inert`)は
    ``inspect.signature``、それ以外(プログラムの中の関数)は :func:`_static_signature`。

    前はどの関数にも ``str(inspect.signature(v))`` を呼んでいた。これは既定値を ``repr`` で文字にするので、
    ``def f(x, cfg=Config()):`` のような普通の書き方で、利用者の ``__repr__`` が GUI のスレッドで走った
    (2026-11-13 第 3 回レビュー S4 を直す途中で見つけた)。"""
    f = v.__func__ if type(v) is types.MethodType else v
    name = None
    try:
        if type(f) is types.FunctionType:
            name = _FUNC["__name__"].__get__(f)
        elif type(f) is types.BuiltinFunctionType:
            name = f.__name__
    except Exception:                                        # noqa: BLE001
        name = None
    if type(name) is not str:
        name = "function"
    try:
        if safe.is_inert(v):
            return name + str(inspect.signature(v))
        if type(f) is types.FunctionType:
            return name + _static_signature(f, bound=type(v) is types.MethodType)
    except Exception:                                        # noqa: BLE001 -- シグネチャの無い C の関数など
        pass
    return name + "(…)"


def _object_dict(v):
    """インスタンスの ``__dict__``(利用者の ``__getattribute__`` / 作り替えた ``__dict__`` を通さない)。"""
    return safe.instance_dict(v)


def _has_default_repr(t: type) -> bool:
    """``__repr__`` を誰も定義していないか(MRO の ``__dict__`` を静的に見る)。"""
    try:
        for k in safe.mro_of(t):
            if "__repr__" in safe.class_dict(k):
                return k is object
        return True
    except Exception:                                        # noqa: BLE001
        return False


def _summarize_object(v, lim: Limits, tr, tn: str) -> Summary:
    d = _object_dict(v)
    has_children = bool(d) or _has_slots(type(v))
    if _has_default_repr(type(v)):
        txt = "<%s object>" % tn
        return Summary("object", tn, txt, expandable=has_children)
    key = (tn, id(v))
    if key in _STUCK:
        return Summary("object", tn, tr("(repr timed out)"), problem="repr_timeout", expandable=has_children)
    st, val = run_with_timeout(lambda: repr(v), lim.repr_timeout_s)
    if st == "busy":
        return Summary("object", tn, tr("(not shown: an earlier value is still running its own code)"),
                       problem="repr_timeout", expandable=has_children)
    if st == "timeout":
        _STUCK.add(key)
        if len(_STUCK) > 500:
            _STUCK.clear()
        return Summary("object", tn, tr("(repr timed out)"), problem="repr_timeout", expandable=has_children)
    if st == "error":
        return Summary("object", tn, tr("(repr failed: %s)") % _clip(safe.exception_text(val), 50),
                       problem="repr_failed", expandable=has_children)
    if not _isinst(val, str):
        return Summary("object", tn, tr("(repr failed: %s)") % "returned non-string", problem="repr_failed")
    return Summary("object", tn, _clip(val, lim.max_text), length=None, expandable=has_children,
                   detail=_clip(val, 2000))


def _has_slots(t: type) -> bool:
    try:
        return any("__slots__" in safe.class_dict(k) for k in safe.mro_of(t) if k is not object)
    except Exception:                                        # noqa: BLE001
        return False


# --------------------------------------------------------------------------- #
# 木の展開
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Child:
    label: str
    step: tuple | None           # ("item", key) / ("attr", name) / ("field", name) / ("elem", index)。None = 「…あと N 個」の行
    value: object = None
    note: str = ""
    cycle: bool = False
    more: int = 0


def _slot_names(t: type) -> list:
    out = []
    for k in safe.mro_of(t):
        sl = safe.class_dict(k).get("__slots__")
        if sl is None:
            continue
        for n in ([sl] if _isinst(sl, str) else list(sl)):
            if n not in ("__dict__", "__weakref__") and n not in out:
                out.append(n)
    return out


def children(value, *, ancestors: Iterable = (), explicit_attrs: Iterable = (), include_private: bool = False,
             limits: Limits = DEFAULT_LIMITS, tr: Callable = _ident) -> list:
    """``value`` の子の列。プロパティは呼ばない。``ancestors`` は祖先の ``id``(循環を印す)。"""
    anc = set(ancestors) | {id(value)}
    out: list = []
    n = limits.max_children

    def add(label, step, v):
        out.append(Child(label, step, v, cycle=(id(v) in anc and not _is_atom(v))))

    if _isinst(value, dict):
        for k, v in itertools.islice(dict.items(value), n):
            add(_brief(k, limits) if _isinst(k, (str, int, float, bool, tuple, type(None))) else safe.type_name(k),
                ("item", k), v)
        rest = dict.__len__(value) - n
        if rest > 0:
            out.append(Child(tr("… %d more") % rest, None, more=rest))
    elif _isinst(value, (list, tuple)):
        fields = getattr(type(value), "_fields", None) if _isinst(value, tuple) else None
        base_iter = list.__iter__ if _isinst(value, list) else tuple.__iter__
        for i, v in enumerate(itertools.islice(base_iter(value), n)):
            label = "[%d]" % i if not fields or i >= len(fields) else str(fields[i])
            add(label, ("item", i), v)
        rest = _base_len(value) - n
        if rest > 0:
            out.append(Child(tr("… %d more") % rest, None, more=rest))
    elif _isinst(value, (set, frozenset)):
        for i, v in enumerate(_items_of(value, n)):
            add("{%d}" % i, ("elem", i), v)
        rest = _base_len(value) - n
        if rest > 0:
            out.append(Child(tr("… %d more") % rest, None, more=rest))
    elif _isinst(value, np.ndarray):
        if value.dtype.names:
            for name in value.dtype.names:
                try:
                    out.append(Child(name, ("field", name), value[name]))
                except Exception:                            # noqa: BLE001
                    continue
    elif _isinst(value, (types.ModuleType, type, types.FunctionType)) or value is None:
        pass
    else:
        d = _object_dict(value)
        if d:
            for k, v in itertools.islice(dict.items(d), n):
                if _isinst(k, str) and (include_private or not k.startswith("_")):
                    add(k, ("attr", k), v)
        t = type(value)
        for name in _slot_names(t):
            if name.startswith("_") and not include_private:
                continue
            descr = None
            for kl in safe.mro_of(t):
                if name in safe.class_dict(kl):
                    descr = safe.class_dict(kl)[name]
                    break
            if safe.type_name(descr) == "member_descriptor":
                try:
                    add(name, ("attr", name), descr.__get__(value))
                except AttributeError:
                    continue
        for name in explicit_attrs:                          # 利用者が選んだ属性だけ(プロパティの呼び出しもあり得る)
            if any(c.step == ("attr", name) for c in out):
                continue
            st, v = run_with_timeout(lambda nm=name: getattr(value, nm), 0.25)
            if st == "ok":
                add(name, ("attr", name), v)
            else:
                out.append(Child(name, ("attr", name), None,
                                 note=tr("could not read: %s") % (tr("timed out") if st == "timeout" else
                                                                  _clip(safe.exception_text(v), 50))))
    return out


def _is_atom(v) -> bool:
    return v is None or safe.tin(type(v), (int, float, bool, str, complex, bytes))


def candidate_attributes(value) -> list:
    """「この属性を展開」で選べる名前(公開名。プロパティの名前を含む)。値は読まない。利用者のクラスの物は
    ``dir`` を呼ばず(``__dir__`` が走る)、型の MRO とインスタンスの ``__dict__`` の名前だけ。"""
    return [n for n in safe.static_names(value) if not n.startswith("_")]


# --------------------------------------------------------------------------- #
# 路(path)の読み書きと式への変換
# --------------------------------------------------------------------------- #
class EditError(ValueError):
    """値の編集・書き込みを断る理由(画面に赤で出す)。"""


def path_to_expression(path: Sequence) -> str:
    """路 → 式の文字列(「式としてコピー」「ウォッチに足す」に使う)。"""
    out = ""
    for kind, key in path:
        if kind == "name":
            out = str(key)
        elif kind == "item":
            out += "[%r]" % (key,)
        elif kind == "attr":
            out += "." + str(key)
        elif kind == "field":
            out += "[%r]" % (key,)
        elif kind == "elem":
            out = "list(%s)[%d]" % (out, key)
    return out


_NO_ATTR = object()


def resolve_path(ns: Mapping, path: Sequence):
    """路をたどって値を返す(プロパティは呼ばない)。たどれなければ ``KeyError``。"""
    if not path or path[0][0] != "name":
        raise KeyError("path must start with a name")
    cur = ns[path[0][1]]
    for kind, key in path[1:]:
        if kind == "item":
            cur = cur[key]
        elif kind == "attr":
            d = _object_dict(cur)
            if d is not None and key in d:
                cur = d[key]
            else:
                cur = safe.static_getattr(cur, key, _NO_ATTR)   # メタクラスの __getattribute__ も呼ばない
                if cur is _NO_ATTR:
                    raise AttributeError(key)
                if safe.type_name(cur) == "member_descriptor":
                    raise KeyError(key)
        elif kind == "field":
            cur = cur[key]
        elif kind == "elem":
            cur = list(itertools.islice(iter(cur), key + 1))[key]
        else:
            raise KeyError(kind)
    return cur


def assign_path(ns: dict, path: Sequence, value) -> None:
    """路の先へ値を書く。書けなければ ``EditError``(理由つき)。"""
    if not path or path[0][0] != "name":
        raise EditError("invalid path")
    if len(path) == 1:
        ns[path[0][1]] = value
        return
    try:
        parent = resolve_path(ns, path[:-1])
    except Exception as exc:                                 # noqa: BLE001
        raise EditError(safe.exception_text(exc)) from exc
    kind, key = path[-1]
    try:
        if kind == "item":
            parent[key] = value
        elif kind == "attr":
            d = _object_dict(parent)
            if d is not None and key in d:
                d[key] = value
            else:
                descr = None
                for kl in safe.mro_of(type(parent)):
                    if key in safe.class_dict(kl):
                        descr = safe.class_dict(kl)[key]
                        break
                if safe.type_name(descr) == "member_descriptor":
                    descr.__set__(parent, value)
                else:
                    raise EditError("not a plain attribute")
        else:
            raise EditError("cannot assign here")
    except EditError:
        raise
    except Exception as exc:                                 # noqa: BLE001
        raise EditError(safe.exception_text(exc)) from exc


@runtime_checkable
class VariableSource(Protocol):
    def snapshot(self): ...
    def set_value(self, path: tuple, value) -> None: ...


class DictSource:
    """名前空間の ``dict`` を直接見て書く ``VariableSource``。"""

    def __init__(self, ns: dict):
        self.ns = ns

    def snapshot(self):
        return self.ns

    def set_value(self, path, value):
        assign_path(self.ns, path, value)


def namespace_items(snap) -> list:
    """``snapshot()`` の結果(dict か ``(名前, 値)`` の列)を ``[(名前, 値)]`` に。"""
    if _isinst(snap, Mapping):
        return [(k, v) for k, v in snap.items() if _isinst(k, str)]
    return [(k, v) for k, v in snap if _isinst(k, str)]


# --------------------------------------------------------------------------- #
# 値の編集(数・文字列・真偽値だけ)
# --------------------------------------------------------------------------- #
def is_editable(value) -> bool:
    t = type(value)
    if safe.tin(t, (bool, int, float, str)):
        return True
    return _isinst(value, (np.bool_, np.integer, np.floating))


def parse_edit(text: str, current, tr: Callable = _ident):
    """入力された文字列を、``current`` と同じ型の値にする。合わなければ ``EditError``(理由は ``tr`` 済み)。"""
    if not is_editable(current):
        raise EditError(tr("only numbers, strings and booleans can be edited"))
    s = text.strip()
    t = type(current)
    if t is bool or _isinst(current, np.bool_):
        low = s.lower()
        if low in ("true", "1", "yes"):
            val = True
        elif low in ("false", "0", "no"):
            val = False
        else:
            raise EditError(tr("not a boolean: write True or False"))
        return t(val) if t is not bool else val
    if t is str:
        if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
            return s[1:-1]
        return text
    if t is int or _isinst(current, np.integer):
        try:
            iv = int(s, 0)
        except ValueError:
            raise EditError(tr("not an integer: %s") % _clip(s, 20)) from None
        if t is int:
            return iv
        info = np.iinfo(t)
        if not (info.min <= iv <= info.max):
            raise EditError(tr("out of range for %s: %d..%d") % (safe.name_of(t), info.min, info.max))
        return t(iv)
    try:
        fv = float(s)
    except ValueError:
        raise EditError(tr("not a number: %s") % _clip(s, 20)) from None
    if t is float:
        return fv
    return t(fv)


# --------------------------------------------------------------------------- #
# 指紋と「変わった」印
# --------------------------------------------------------------------------- #
def fingerprint(v) -> tuple:
    """値の小さな指紋(変わったかの判定用)。大きな配列は標本で見る。利用者のコードは呼ばない。"""
    t = type(v)
    if v is None or safe.tin(t, (bool, int, float, complex)):
        return (safe.name_of(t), v if t is not float or v == v else "nan")
    if _isinst(v, str):
        return ("str", len(v), zlib.adler32(v[:20000].encode("utf-8", "replace")), hash(v[-64:]))
    if _isinst(v, (bytes, bytearray)):
        return ("bytes", len(v), zlib.adler32(bytes(v[:65536])))
    if _isinst(v, np.ndarray):
        if v.dtype.kind in "biufc" and v.size:
            samp, _s = _sample(v, 65536)
            return ("nd", v.shape, v.dtype.str, zlib.adler32(np.ascontiguousarray(samp).tobytes()))
        return ("nd", v.shape, v.dtype.str)
    if _isinst(v, np.generic):
        return ("np", v.dtype.str, str(v))
    if _isinst(v, (list, tuple, dict, set, frozenset)):
        items = _items_of(v, 32)
        if _isinst(v, dict):
            sub = tuple((repr(k)[:40] if safe.tin(type(k), (str, int)) else safe.type_name(k), _fp_brief(x)) for k, x in items)
        else:
            sub = tuple(_fp_brief(x) for x in items)
        return (safe.name_of(t), _base_len(v), sub)
    if _isinst(v, (types.ModuleType, types.FunctionType, type)):
        return (safe.name_of(t), id(v))
    d = _object_dict(v)
    if d is not None:
        return (type_name_of(v), tuple((k, _fp_brief(x)) for k, x in itertools.islice(dict.items(d), 16)))
    return (type_name_of(v),)


def _fp_brief(v) -> tuple:
    t = type(v)
    if v is None or safe.tin(t, (bool, int, float)):
        return (safe.name_of(t), v if t is not float or v == v else "nan")
    if _isinst(v, str):
        return ("str", len(v), hash(v[:200]))
    if _isinst(v, np.ndarray):
        return ("nd", v.shape, v.dtype.str, zlib.adler32(np.ascontiguousarray(_sample(v, 256)[0]).tobytes())
                if v.dtype.kind in "biufc" and v.size else 0)
    if _isinst(v, (list, tuple, dict, set, frozenset)):
        return (safe.name_of(t), _base_len(v))
    return (type_name_of(v),)


_NEVER = object()


class VariableTracker:
    """前の停止から変わった値の印(``"new"`` / ``"changed"`` / ``"same"`` / 消えた名前)。

    停止(実行後・ステップ)のたびに ``begin()`` を呼び、木を作る間 ``status(path, value)`` を呼ぶ。
    最初の停止(比べる前の記録が無い)は全部 ``"same"``。"""

    def __init__(self):
        self.prev: dict = {}
        self.cur: dict = {}
        self.prev_parents: set = set()       # 前の停止で子まで見た(展開していた)親の路
        self.cur_parents: set = set()
        self.has_prev = False
        self.generation = 0

    def begin(self) -> None:
        self.prev, self.cur = self.cur, {}
        self.prev_parents, self.cur_parents = self.cur_parents, set()
        self.has_prev = self.generation > 0
        self.generation += 1

    def status(self, path: tuple, value) -> str:
        fp = fingerprint(value)
        self.cur[tuple(path)] = fp
        if len(path) > 1:
            self.cur_parents.add(tuple(path[:-1]))
        if not self.has_prev:
            return "same"
        old = self.prev.get(tuple(path), _NEVER)
        if old is _NEVER:
            if len(path) == 1:
                return "new"
            return "new" if tuple(path[:-1]) in self.prev_parents else "same"     # 前に展開していなかった親の子は印なし
        return "same" if old == fp else "changed"

    def removed(self) -> list:
        """前の停止にあって今は無い名前。"""
        if not self.has_prev:
            return []
        now = {p[0][1] for p in self.cur if len(p) == 1}
        return sorted(p[0][1] for p in self.prev if len(p) == 1 and p[0][1] not in now)

    def reset(self) -> None:
        self.__init__()


# --------------------------------------------------------------------------- #
# 絞り込み
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Entry:
    name: str
    value: object
    summary: Summary


def is_hidden_by_default(name: str, value) -> bool:
    """既定で一覧に出さない物: ``_`` で始まる名前、モジュール・関数・クラス。"""
    return name.startswith("_") or _isinst(value, (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, type))


def filter_entries(entries: Iterable, query: str, show_callables: bool = False) -> list:
    """``query`` は空白で区切った語。各語が名前か型の名前に(大小無視で)含まれる行だけ。``型:ndarray`` のように
    ``型:`` / ``type:`` / ``t:`` を付けると型だけ、``name:`` / ``名前:`` / ``n:`` で名前だけを見る。"""
    toks = [w for w in (query or "").lower().split() if w]
    out = []
    for e in entries:
        if not show_callables and is_hidden_by_default(e.name, e.value):
            continue
        nm, ty = e.name.lower(), (e.summary.type_name + " " + e.summary.kind).lower()
        ok = True
        for w in toks:
            if w.split(":", 1)[0] in ("type", "t", "型") and ":" in w:
                ok = ok and w.split(":", 1)[1] in ty
            elif w.split(":", 1)[0] in ("name", "n", "名前") and ":" in w:
                ok = ok and w.split(":", 1)[1] in nm
            else:
                ok = ok and (w in nm or w in ty)
        if ok:
            out.append(e)
    return out


# --------------------------------------------------------------------------- #
# サムネイル
# --------------------------------------------------------------------------- #
def thumbnail_u8(a: np.ndarray, size: int = 48) -> np.ndarray:
    """画像らしい配列 → 小さな ``uint8``(``(h, w)`` か ``(h, w, 3)``)。全部は走査しない(間引いて取る)。

    浮動小数は標本の最小〜最大を 0..255 に、``uint8`` はそのまま、それ以外の整数は最小〜最大、真偽は 0/255。
    NaN・inf は 0 として扱う。"""
    if not _isinst(a, np.ndarray) or a.ndim not in (2, 3) or a.size == 0:
        raise ValueError("thumbnail_u8: 2-D か 3-D の配列が要ります")
    h, w = a.shape[:2]
    sy, sx = max(1, h // size), max(1, w // size)
    sub = a[::sy, ::sx]
    if sub.ndim == 3:
        if sub.shape[2] == 1:
            sub = sub[:, :, 0]
        elif sub.shape[2] >= 3:
            sub = sub[:, :, :3]
        else:
            sub = sub[:, :, 0]
    if sub.dtype == np.uint8:
        return np.ascontiguousarray(sub)
    if sub.dtype.kind == "b":
        return np.ascontiguousarray(sub.astype(np.uint8) * 255)
    x = sub.astype(np.float64)
    fin = np.isfinite(x)
    if not fin.all():
        x = np.where(fin, x, 0.0)
    lo, hi = float(x.min()), float(x.max())
    if hi <= lo:
        return np.full(x.shape, 128, np.uint8)
    return np.ascontiguousarray(((x - lo) / (hi - lo) * 255.0 + 0.5).astype(np.uint8))


def histogram_data(a: np.ndarray, bins: int = 64) -> tuple:
    """数の配列のヒストグラム ``(度数, 境界, 標本か)``。大きな配列は標本(最大 100 万要素)。非有限は除く。"""
    samp, sampled = _sample(np.asarray(a), 1_000_000)
    x = samp.astype(np.float64)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return np.zeros(bins, int), np.linspace(0.0, 1.0, bins + 1), sampled
    counts, edges = np.histogram(x, bins=bins)
    return counts, edges, sampled


# --------------------------------------------------------------------------- #
# ウォッチ
# --------------------------------------------------------------------------- #
@dataclass
class WatchResult:
    expr: str
    ok: bool
    value: object = None
    summary: Summary | None = None
    error: str | None = None
    timed_out: bool = False
    elapsed_ms: float = 0.0
    changed: bool = False
    stuck: bool = False             # 時間切れで、止める例外を送っても止まらなかった(C の長い呼び出しの中など)


@dataclass
class ConditionResult:
    ok: bool                    # 評価できたか
    hit: bool = False           # 真か
    error: str | None = None


class WatchEvaluator:
    """式を名前空間で評価する。利用者が自分で書いた式を自分の名前空間で評価する(``eval``)。時間の上限つき。"""

    def __init__(self, namespace, timeout_s: float = 0.25, tr: Callable = _ident, limits: Limits = DEFAULT_LIMITS):
        self._ns = namespace
        self.timeout_s = float(timeout_s)
        self.tr = tr
        self.limits = limits
        self._last: dict = {}

    def namespace(self) -> dict:
        ns = self._ns() if callable(self._ns) else self._ns
        return dict(ns or {})

    def _eval(self, expr: str) -> tuple:
        """``(状態, 値か例外, 経過 ms)``。状態は ok / error / timeout / syntax。"""
        src = (expr or "").strip()
        if not src:
            return "syntax", ValueError(self.tr("empty expression")), 0.0
        try:
            code = compile(src, "<watch>", "eval")
        except SyntaxError as exc:
            return "syntax", exc, 0.0
        g = self.namespace()
        g.setdefault("__builtins__", builtins)
        t0 = time.perf_counter()
        st, val = run_with_timeout(lambda: eval(code, g), self.timeout_s)      # noqa: S307 — 利用者自身の式
        return st, val, (time.perf_counter() - t0) * 1000.0

    def _error_text(self, st: str, val) -> str:
        if st == "busy":
            return self.tr("(not shown: an earlier value is still running its own code)")
        if st == "timeout":
            return self.tr("timed out (over %d ms)") % int(self.timeout_s * 1000)
        if _isinst(val, SyntaxError):
            return self.tr("syntax error: %s") % _clip(str(val.msg or val), 80)
        return _clip(safe.exception_text(val, 100), 130)       # 利用者の例外の __str__ は呼ばない

    def evaluate(self, expr: str) -> WatchResult:
        st, val, ms = self._eval(expr)
        if st != "ok":
            self._last.pop(expr, None)
            return WatchResult(expr, False, error=self._error_text(st, val), timed_out=(st == "timeout"), elapsed_ms=ms)
        fp = fingerprint(val)
        prev = self._last.get(expr, _NEVER)
        self._last[expr] = fp
        return WatchResult(expr, True, val, summarize(val, self.limits, self.tr), None, False, ms,
                           changed=(prev is not _NEVER and prev != fp))

    def condition(self, expr: str) -> ConditionResult:
        """条件つきブレークポイント用: 式が真か。評価できない・曖昧(配列)なら ``ok=False`` と理由(止めずに知らせる側)。"""
        st, val, _ms = self._eval(expr)
        if st != "ok":
            return ConditionResult(False, False, self._error_text(st, val))
        try:
            hit = bool(val)
        except Exception as exc:                             # noqa: BLE001
            return ConditionResult(False, False, _clip(safe.exception_text(exc, 80), 110))
        return ConditionResult(True, hit, None)

    def reset_changes(self) -> None:
        self._last.clear()

    def start(self, expr: str) -> "WatchJob":
        """評価を作業スレッドで始める(UI を待たせない)。結果は ``job.poll()`` で受ける。"""
        return WatchJob(self, expr)


#: 止められずに裏で走り続けているスレッドの数(診断用)。
STUCK_THREADS: list = []
#: 止める例外を送ってから「止められなかった」と判断するまでの猶予(秒)。
STOP_GRACE_S = 0.3


class WatchJob:
    """ウォッチの式 1 つの非同期の評価。UI スレッドでは ``poll()`` を呼ぶだけ(待たない)。

    状態: ``running`` → 結果が出る(``poll()`` が ``WatchResult`` を返す)か、時間の上限を超えると止める例外を送り、
    それでも止まらなければ ``stuck``(「時間切れ(止められなかった)」)。止まれば「時間切れ」。

    限界: 作業スレッドは Python のスレッドなので、GIL を握ったままの C の長い呼び出し(``sum(range(10**10))`` など)の間は
    UI スレッドも進めない。``time.sleep`` や、GIL を手放す numpy の長い演算なら UI は止まらない。
    """

    def __init__(self, evaluator: "WatchEvaluator", expr: str):
        self.ev = evaluator
        self.expr = expr
        self.t0 = time.perf_counter()
        self.result: WatchResult | None = None
        self._box: dict = {}
        self._killed_at: float | None = None
        self._thread: threading.Thread | None = None
        src = (expr or "").strip()
        if not src:
            self.result = WatchResult(expr, False, error=evaluator.tr("empty expression"))
            return
        try:
            code = compile(src, "<watch>", "eval")
        except SyntaxError as exc:
            self.result = WatchResult(expr, False, error=evaluator._error_text("syntax", exc))
            return
        if stray_threads():                            # 前の時間切れのスレッドが残っている間は、新しく起こさない
            self.result = WatchResult(expr, False, stuck=True,
                                      error=evaluator.tr("(not shown: an earlier value is still running its own code)"))
            return
        g = evaluator.namespace()                      # 名前空間の写しは UI スレッドで取る(辞書の反復中の変更を避ける)
        g.setdefault("__builtins__", builtins)
        box = self._box

        def target():
            try:
                box["v"] = eval(code, g)               # noqa: S307 — 利用者自身の式
            except _Timeout:
                box["timeout"] = True
            except BaseException as exc:               # noqa: BLE001
                box["e"] = exc

        self._thread = threading.Thread(target=target, name="pyedit-watch", daemon=True)
        self._thread.start()

    @property
    def running(self) -> bool:
        return self.result is None

    def poll(self) -> "WatchResult | None":
        """結果が出ていれば返す(出ていなければ ``None``)。待たない。"""
        if self.result is not None:
            return self.result
        th = self._thread
        now = time.perf_counter()
        ms = (now - self.t0) * 1000.0
        ev = self.ev
        if th is not None and not th.is_alive():
            if "e" in self._box:
                self.result = WatchResult(self.expr, False, error=ev._error_text("error", self._box["e"]), elapsed_ms=ms)
            elif self._box.get("timeout") or self._killed_at is not None and "v" not in self._box:
                self.result = WatchResult(self.expr, False, error=ev._error_text("timeout", None), timed_out=True, elapsed_ms=ms)
            else:
                val = self._box.get("v")
                fp = fingerprint(val)
                prev = ev._last.get(self.expr, _NEVER)
                ev._last[self.expr] = fp
                self.result = WatchResult(self.expr, True, val, summarize(val, ev.limits, ev.tr), None, False, ms,
                                          changed=(prev is not _NEVER and prev != fp))
            return self.result
        if ms > ev.timeout_s * 1000.0:
            if self._killed_at is None:
                self._killed_at = now
                try:                                    # Python のコードなら次の命令で止まる
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(th.ident), ctypes.py_object(_Timeout))
                except Exception:                       # noqa: BLE001
                    pass
            elif now - self._killed_at > STOP_GRACE_S:
                STUCK_THREADS.append(th)
                ev._last.pop(self.expr, None)
                self.result = WatchResult(self.expr, False, error=ev.tr("timed out (could not be stopped)"),
                                          timed_out=True, elapsed_ms=ms, stuck=True)
        return self.result


class WatchList:
    """ウォッチの式の並び。プロジェクトごとに保存できる JSON の形で出し入れする。"""

    SCHEMA = "fullseye_watch"
    VERSION = 1

    def __init__(self, exprs: Iterable | None = None):
        self.exprs: list = []
        for e in exprs or ():
            self.add(e)

    def add(self, expr: str) -> int:
        e = (expr or "").strip()
        if not e:
            raise ValueError("empty expression")
        if e in self.exprs:
            return self.exprs.index(e)
        self.exprs.append(e)
        return len(self.exprs) - 1

    def remove(self, index: int) -> None:
        del self.exprs[index]

    def move(self, index: int, to: int) -> None:
        if not (0 <= index < len(self.exprs)) or not (0 <= to < len(self.exprs)):
            raise IndexError("move: index out of range")
        self.exprs.insert(to, self.exprs.pop(index))

    def dumps(self) -> str:
        return json.dumps({"fullseye_kind": self.SCHEMA, "version": self.VERSION, "expressions": list(self.exprs)},
                          ensure_ascii=False, indent=2)

    @classmethod
    def loads(cls, text: str) -> "WatchList":
        """読めない・形が違うときは ``ValueError``(黙って空にしない)。"""
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ValueError("watch file is not valid JSON: %s" % exc) from exc
        if not _isinst(data, dict) or data.get("fullseye_kind") != cls.SCHEMA:
            raise ValueError("not a watch file (fullseye_kind != %s)" % cls.SCHEMA)
        if data.get("version") != cls.VERSION:
            raise ValueError("unsupported watch file version: %r" % (data.get("version"),))
        ex = data.get("expressions")
        if not _isinst(ex, list) or not all(_isinst(x, str) for x in ex):
            raise ValueError("'expressions' must be a list of strings")
        return cls(ex)
