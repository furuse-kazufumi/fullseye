# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_pyedit_safe — 実行後の値を「利用者のコードを走らせずに」調べるための小さな道具(Qt なし)。

補完・ホバー・変数の一覧は GUI のスレッドで動く。実行後の名前空間には利用者のクラスの物が残っていて、
``dir(x)``・``getattr(x, …)``・``isinstance(x, …)``(``x.__class__`` を読む)・``repr(x)``・``len(x)`` は、
そのクラスの ``__dir__`` / ``__getattr__`` / ``__class__`` のプロパティ / ``__repr__`` / ``__len__`` を呼ぶ。
戻らないメソッドなら画面が固まる(2026-11-13 の独立レビュー M3: ``__class__`` のプロパティ 1 つで 45 秒)。

ここの決まり:

* 値の種類は **``type(x)`` だけ**で決める(:func:`isinst`)。``x.__class__`` は読まない。
* 「ライブラリの型」(:func:`is_library_type` = 標準ライブラリ・site-packages・Studio 自身のモジュールで
  定義された型)の物だけ、その型のメソッド(``dir``・``repr``・属性の読み出し)を使ってよい(:func:`is_inert`)。
* それ以外(プログラムの中・利用者のフォルダで定義された型とその派生)は、**静的な情報だけ**を使う
  (:func:`static_names` = 型の MRO の ``__dict__`` の名前と、インスタンスの ``__dict__`` の名前)。値は読まない。

限界(正直に): ライブラリの型のメソッドは呼ぶ(numpy・標準ライブラリを信用する)。``inspect.getattr_static`` は
標準ライブラリの約束の範囲で静的。利用者が site-packages に入れたパッケージは「ライブラリ」として扱う。
"""
from __future__ import annotations

import os
import sys
import sysconfig
import types

_STDLIB = frozenset(getattr(sys, "stdlib_module_names", ())) | {"builtins"}
_HERE = os.path.normcase(os.path.dirname(os.path.abspath(__file__)))
_MODULE_VERDICT: dict = {}
_LIB_DIRS: list | None = None

#: そのまま値を見てよい型(完全一致)。派生した型は :func:`is_library_type` で決める。
EXACT_SAFE_SCALARS = (bool, int, float, complex, str, bytes, type(None))


def _lib_dirs() -> list:
    global _LIB_DIRS
    if _LIB_DIRS is None:
        dirs = set()
        for key in ("purelib", "platlib", "stdlib", "platstdlib"):
            try:
                p = sysconfig.get_paths().get(key)
            except Exception:                                # noqa: BLE001
                p = None
            if p:
                dirs.add(os.path.normcase(os.path.abspath(p)))
        try:
            import site
            for p in list(site.getsitepackages()) + [site.getusersitepackages()]:
                if p:
                    dirs.add(os.path.normcase(os.path.abspath(p)))
        except Exception:                                    # noqa: BLE001
            pass
        _LIB_DIRS = sorted(dirs)
    return _LIB_DIRS


def is_library_module_name(name) -> bool:
    """モジュール名 *name* が、標準ライブラリ・site-packages・Studio 自身のモジュールか。分からなければ False
    (利用者の物として扱う側 = fail-closed)。"""
    if type(name) is not str or not name:
        return False
    hit = _MODULE_VERDICT.get(name)
    if hit is not None:
        return hit
    top = name.split(".")[0]
    if top in _STDLIB:
        verdict = True
    else:
        verdict = False
        mod = sys.modules.get(name)
        if mod is None:
            mod = sys.modules.get(top)
        if type(mod) is types.ModuleType:
            f = types.ModuleType.__dict__["__dict__"].__get__(mod).get("__file__")
            if type(f) is str:
                path = os.path.normcase(os.path.abspath(f))
                d = os.path.dirname(path)
                verdict = d == _HERE or any(path.startswith(root + os.sep) for root in _lib_dirs())
    if len(_MODULE_VERDICT) > 4000:
        _MODULE_VERDICT.clear()
    _MODULE_VERDICT[name] = verdict
    return verdict


#: ``type`` 自身の記述子。クラスの ``__dict__`` / ``__mro__`` / ``__name__`` を**これで直接**読む。
#: ``cls.__mro__`` や ``type.__getattribute__(cls, "__mro__")`` は、メタクラスに同じ名前のプロパティがあるとそれ
#: (利用者のコード)を呼ぶ。記述子の ``__get__`` はメタクラスを見ない。
_T = type.__dict__
_MODULE_OF = _T["__module__"]
_HEAPTYPE = 1 << 9                 # Py_TPFLAGS_HEAPTYPE: Python の class 文(と一部の C 拡張)で作った型


def class_dict(cls):
    """クラスの ``__dict__``(メタクラスのプロパティ・``__getattribute__`` を通さない)。"""
    return _T["__dict__"].__get__(cls)


def mro_of(cls) -> tuple:
    """クラスの MRO(メタクラスの ``__mro__`` のプロパティを通さない)。"""
    return _T["__mro__"].__get__(cls)


def name_of(cls) -> str:
    """クラスの名前(メタクラスの ``__name__`` のプロパティを通さない)。"""
    try:
        n = _T["__name__"].__get__(cls)
        return n if type(n) is str else "object"
    except Exception:                                        # noqa: BLE001
        return "object"


def tin(t, types_) -> bool:
    """*t* が *types_* のどれかと**同一**か。``t in (int, str)`` は ``==`` を呼び、メタクラスの ``__eq__``
    (利用者のコード)が走るので使わない。"""
    for x in types_:
        if t is x:
            return True
    return False


_class_dict = class_dict
_mro = mro_of


def module_of(cls):
    """クラスを定義したモジュールの名前(``type`` 自身の記述子で読む = メタクラスの ``__getattribute__`` を通さない。
    組み込みの型は ``__dict__`` に ``__module__`` を持たないので、``__dict__`` からは読めない)。"""
    try:
        return _MODULE_OF.__get__(cls)
    except Exception:                                        # noqa: BLE001
        return None


def _module_dict(mod):
    return types.ModuleType.__dict__["__dict__"].__get__(mod)


def is_library_class(c) -> bool:
    """クラス *c* そのものがライブラリの物か。**名前でなく実体**で確かめる(2026-11-13 第 2 回レビュー R2:
    クラス本体の ``__module__ = "json"`` や、プログラムの ``__name__ = "numpy"`` で名前は偽れる)。

    * C で定義された静的な型(``int``・``numpy.ndarray`` …)は、Python のプログラムからは作れないので真。
    * それ以外は、``__module__`` がライブラリのモジュールで、**そのモジュールから ``__qualname__`` を辿ると同じ
      型に着く**時だけ真(関数の中で作られた型など、辿れない物は偽 = 利用者の物として扱う側)。"""
    try:
        if not _T["__flags__"].__get__(c) & _HEAPTYPE:
            return True
        mod = module_of(c)
        if not is_library_module_name(mod):
            return False
        m = sys.modules.get(mod)
        if m is None or not issubclass(type(m), types.ModuleType):
            return False
        qual = _T["__qualname__"].__get__(c)
        if type(qual) is not str or "<" in qual:
            return False
        parts = qual.split(".")
        obj = _module_dict(m).get(parts[0])
        for part in parts[1:]:
            if obj is None or not issubclass(type(obj), type):
                return False
            obj = class_dict(obj).get(part)
        return obj is c
    except Exception:                                        # noqa: BLE001 -- 分からない物は利用者の物として扱う
        return False


def is_library_type(t) -> bool:
    """型 *t* とその基底の全部(とメタクラス)が、ライブラリで定義されているか(:func:`is_library_class`)。"""
    try:
        if not issubclass(type(t), type):
            return False
        for c in _mro(t):
            if not is_library_class(c):
                return False
        meta = type(t)
        if meta is not type:
            for c in _mro(meta):
                if not is_library_class(c):
                    return False
        return True
    except Exception:                                        # noqa: BLE001 -- 分からない物は利用者の物として扱う
        return False


def isinst(obj, cls) -> bool:
    """``isinstance`` の代わり: ``type(obj)`` だけで決める(``obj.__class__`` を読まない)。"""
    return issubclass(type(obj), cls)


def is_inert(obj) -> bool:
    """*obj* を ``dir``・``repr``・属性の読み出しで調べても、利用者のコードが走らないか。

    ライブラリの型のインスタンス、ライブラリのクラス、ライブラリのモジュール、関数(``def`` で作った物)が真。
    利用者のクラスとそのインスタンス、利用者のモジュール(``__getattr__`` / ``__dir__`` を持てる)は偽。
    入れ物(list など)は真だが、**中身は別に**確かめること。"""
    t = type(obj)
    if not is_library_type(t):
        return False
    if issubclass(t, type):
        return is_library_type(obj)
    if issubclass(t, types.ModuleType):
        name = _module_dict(obj).get("__name__")             # 名前を偽っていないか: sys.modules のその名前がこの物か
        return is_library_module_name(name) and sys.modules.get(name) is obj
    if t is types.MethodType:
        return is_inert(obj.__self__) and is_inert(obj.__func__)
    return True


def is_plain_value(obj) -> bool:
    """補完のために生きた値をそのまま渡してよいか: 数・文字列・numpy の配列とスカラ・ライブラリの
    モジュール / クラス / 関数。入れ物(中に利用者の物が入り得る)と利用者の物は偽。"""
    t = type(obj)
    if tin(t, EXACT_SAFE_SCALARS):
        return True
    if tin(t, (list, tuple, dict, set, frozenset)):
        return False
    if t is types.FunctionType:
        return is_library_module_name(obj.__module__)
    if t is types.BuiltinFunctionType or t is types.ModuleType or issubclass(t, type):
        return is_inert(obj)
    mod = module_of(t)
    return type(mod) is str and mod.split(".")[0] == "numpy" and is_library_type(t)


def instance_dict(obj):
    """インスタンスの ``__dict__``(利用者の ``__getattribute__`` / ``__dict__`` のプロパティを通さない)。無ければ None。"""
    try:
        for c in _mro(type(obj)):
            d = _class_dict(c).get("__dict__")
            if d is not None:
                if type(d) is not types.GetSetDescriptorType:
                    return None                              # 利用者が __dict__ を作り替えている: 読まない
                break
        d = object.__getattribute__(obj, "__dict__")
        return d if type(d) is dict else None
    except Exception:                                        # noqa: BLE001
        return None


def static_names(obj) -> list:
    """*obj* の属性の名前。ライブラリの物(:func:`is_inert`)は ``dir``、それ以外は静的な情報だけ
    (モジュール = その ``__dict__``、クラス = MRO の ``__dict__``、インスタンス = 型の MRO とインスタンスの ``__dict__``)。"""
    t = type(obj)
    try:
        if is_inert(obj):
            return list(dir(obj))
        names: set = set()
        if issubclass(t, types.ModuleType):
            names.update(k for k in _module_dict(obj) if type(k) is str)
            return sorted(names)
        if issubclass(t, type):
            for c in _mro(obj):
                names.update(k for k in _class_dict(c) if type(k) is str)
            return sorted(names)
        for c in _mro(t):
            names.update(k for k in _class_dict(c) if type(k) is str)
        d = instance_dict(obj)
        if d:
            names.update(k for k in d if type(k) is str)
        return sorted(names)
    except Exception:                                        # noqa: BLE001
        return []


def type_name(obj) -> str:
    """型の名前(``type(obj)`` から。利用者のコードを通さない)。"""
    try:
        return name_of(type(obj))
    except Exception:                                        # noqa: BLE001
        return "object"


_ARGS = BaseException.__dict__["args"]


def exception_text(exc, limit: int = 200) -> str:
    """例外を ``型の名前: 文`` にする。**利用者のコードを呼ばない**: 文は、引数が数・文字列だけの時に限ってそれを
    繋ぐ(``str(exc)`` は例外の ``__str__`` や引数の ``__repr__`` を呼ぶので使わない)。それ以外は型の名前だけ。"""
    tn = type_name(exc)
    try:
        args = _ARGS.__get__(exc)
        if type(args) is tuple and args and all(tin(type(a), (str, int, float, bool)) for a in args):
            if len(args) == 1 and type(exc) is KeyError:
                text = repr(args[0])                         # str(KeyError('x')) は "'x'"
            else:
                text = ", ".join(a if type(a) is str else repr(a) for a in args) if len(args) == 1 else repr(args)
            return "%s: %s" % (tn, text if len(text) <= limit else text[:limit] + "…")
    except Exception:                                        # noqa: BLE001
        pass
    return tn
