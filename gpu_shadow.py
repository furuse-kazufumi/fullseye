# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gpu_shadow — run the existing numpy/scipy operators on CuPy arrays, unchanged.

既存の numpy/scipy 実装を**書き換えず**に GPU 配列で動かすための「影のモジュール」層。
op を 1 件ずつ torch へ手書きする代わりに、同じソースをもう一度別の名前空間で実行し、
その名前空間の中だけ ``numpy`` / ``scipy`` を CuPy 側へ向ける。

How it works / 仕組み:

* ``ShadowImporter.load("ops")`` compiles ``ops.py`` again into a private module object
  whose ``__builtins__`` carries its own ``__import__``.  The real ``sys.modules`` entry,
  and therefore every CPU code path, is left alone: the shadow is thread-safe by
  construction because nothing global is swapped.
  本物の ``sys.modules`` にも既定の CPU 経路にも触らない(大域の差し替えをしない)。
* Project modules imported from a shadow are shadowed too; third-party modules stay real.
  The module body runs on real numpy (import-time tables stay as they were), and only
  after it finished are ``np`` / ``ndimage`` / ``gaussian_filter`` … rebound to proxies.
* A numpy/scipy function with a CuPy twin runs on the GPU.  One without a twin is run on
  the CPU with an explicit transfer, and **that fall-back is counted** (:class:`Stats`):
  running is not the claim, the measured speed is.  差し替えて動いただけでは GPU 化では
  ない —— 転送が増えただけの op は採点(``tools/gpu_auto_sweep.py``)で落ちる。

Limits (measured, not assumed):

* ``cv2`` / ``skimage`` / ``PIL`` are native and refuse CuPy arrays: those ops raise here.
* Project classes in a shadow are distinct from the real ones (``isinstance`` across the
  boundary is False); an op that takes an instance built on the CPU side raises.
* ``sys.modules[__name__]`` inside an op still names the real, CPU module.

The default path never imports this file.  ``fullseye.gpu_run`` style callers go through
:func:`run_allowed`, which refuses every op outside the machine-readable allow-list
``fullseye/data/gpu_auto_allow.json`` — measured parity + speed, not a guess.
既定の経路はこのファイルを import しない。許可リスト外の op は fail-closed で拒否する。
"""
from __future__ import annotations

import builtins
import collections
import importlib
import importlib.util
import json
import os
import threading
import types

import numpy as _np

__all__ = ["ShadowImporter", "Stats", "get_shadow", "to_gpu", "to_cpu", "available",
           "allowed_ops", "shadow_fn", "run_allowed", "apply", "GpuAutoError"]

ROOT = os.path.dirname(os.path.abspath(__file__))
ALLOW_PATH = os.path.join(ROOT, "fullseye", "data", "gpu_auto_allow.json")

_MISSING = object()
_CUPY = None


class GpuAutoError(RuntimeError):
    """The shadow path cannot run this request (no CuPy, no GPU, op not allowed)."""


# ---- counters: a fall-back is a fact to report, not a thing to hide -------------- #
class Stats:
    """Per-run counters.  実行の内訳(GPU 呼び出し / CPU 退避 / 転送量)。"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.gpu_calls = 0
        self.cpu_calls = collections.Counter()
        self.bytes_to_cpu = 0
        self.bytes_to_gpu = 0

    def as_dict(self):
        return {"gpu_calls": self.gpu_calls, "n_cpu_fallback": sum(self.cpu_calls.values()),
                "cpu_fallback": dict(self.cpu_calls.most_common(8)),
                "bytes_to_cpu": self.bytes_to_cpu, "bytes_to_gpu": self.bytes_to_gpu}


STATS = Stats()


def _cupy():
    """Import CuPy lazily; fail-closed with a sentence when it cannot run here."""
    global _CUPY
    if _CUPY is not None:
        return _CUPY
    try:
        if os.name == "nt":
            # Windows の CuPy wheel は NVRTC を同梱しない。torch(cu128)同梱の NVRTC 12.8 を使う
            import torch  # noqa: F401
        import cupy
    except Exception as e:  # noqa: BLE001 - CuPy の失敗は ImportError に限らない
        raise GpuAutoError("CuPy is not usable here: %s" % (e,)) from e
    _fix_nvrtc_headers(cupy)
    _CUPY = cupy
    return cupy


def _fix_nvrtc_headers(cupy) -> None:
    """NVRTC 12.8 + a newer CUDA Toolkit: switch off CCCL's FP8 support.

    NVRTC は導入済みの Toolkit(13.x)のヘッダを見に行く。13.x の ``cuda_fp8.hpp`` は NVRTC 12.8
    に無いマクロと型を使うので、ndimage 系のカーネルが CompileException で全滅する
    (2026-11-02 実測)。FP8 型はどの op も使わないので、CCCL の正規のスイッチで切る。
    """
    comp = getattr(getattr(cupy, "cuda", None), "compiler", None)
    prev = getattr(comp, "_get_extra_include_dir_opts", None)
    if prev is None:
        return

    def opts():
        return tuple(prev()) + ("-D_CCCL_DISABLE_NVFP8_SUPPORT",)
    comp._get_extra_include_dir_opts = opts


def available() -> bool:
    """True when CuPy imports and a CUDA device answers.  例外は投げない。"""
    try:
        return _cupy().cuda.runtime.getDeviceCount() > 0
    except Exception:  # noqa: BLE001 - 判定関数なので何が起きても False
        return False


def _is_gpu(x) -> bool:
    return type(x).__module__.startswith("cupy") and hasattr(x, "get") and hasattr(x, "shape")


def to_gpu(x):
    """numpy leaves -> CuPy, through list / tuple / dict.  Non-numeric leaves stay."""
    if isinstance(x, _np.ndarray):
        if x.dtype.kind in "biufc":
            STATS.bytes_to_gpu += x.nbytes
            return _cupy().asarray(x)
        return x
    if isinstance(x, list):
        return [to_gpu(v) for v in x]
    if isinstance(x, tuple):
        vals = [to_gpu(v) for v in x]
        return type(x)(*vals) if hasattr(x, "_fields") else tuple(vals)
    if isinstance(x, dict):
        return type(x)((k, to_gpu(v)) for k, v in x.items()) if type(x) is not dict \
            else {k: to_gpu(v) for k, v in x.items()}
    if isinstance(x, _np.random.Generator):
        return _GenProxy(x)
    return x


def to_cpu(x):
    """CuPy leaves -> numpy, through list / tuple / dict; wrap Python callbacks."""
    if _is_gpu(x):
        STATS.bytes_to_cpu += int(x.nbytes)
        return x.get()
    if isinstance(x, list):
        return [to_cpu(v) for v in x]
    if isinstance(x, tuple):
        vals = [to_cpu(v) for v in x]
        return type(x)(*vals) if hasattr(x, "_fields") else tuple(vals)
    if isinstance(x, dict):
        return {k: to_cpu(v) for k, v in x.items()}
    if isinstance(x, types.FunctionType):
        return _cpu_callback(x)
    return x


def _cpu_callback(fn):
    """A callback handed to a CPU library: its body is shadow code, so bridge both ways."""
    def call(*a, **k):
        return to_cpu(fn(*to_gpu(a), **to_gpu(k)))
    call.__name__ = getattr(fn, "__name__", "callback")
    return call


def _cpu_call(fn, label):
    """Run a CPU function on transferred arguments; count it."""
    def call(*a, **k):
        STATS.cpu_calls[label] += 1
        target = k.get("out")
        r = to_gpu(fn(*to_cpu(a), **to_cpu(k)))
        if _is_gpu(target):              # ``out=`` は CPU の写しに書かれるので戻す
            target[...] = r
            return target
        return r
    call.__name__ = getattr(fn, "__name__", label)
    call.__wrapped_cpu__ = fn
    return call


class _CpuObject:
    """A CPU-only object (``cKDTree``, ``ConvexHull`` …): arguments and results cross."""

    def __init__(self, obj, label):
        object.__setattr__(self, "_o", obj)
        object.__setattr__(self, "_l", label)

    def __getattr__(self, name):
        v = getattr(self._o, name)
        if callable(v) and not isinstance(v, type):
            return _cpu_call(v, "%s.%s" % (self._l, name))
        return to_gpu(v)

    def __call__(self, *a, **k):
        return _cpu_call(self._o, self._l)(*a, **k)


def _cpu_class(cls, label):
    """Wrap a CPU class.  Static constructors (``Rotation.from_matrix``) are wrapped too."""
    class Meta(type):
        def __getattr__(mcs, name):
            v = getattr(cls, name)
            if callable(v) and not isinstance(v, type):
                def ctor(*a, **k):
                    STATS.cpu_calls[label] += 1
                    r = v(*to_cpu(a), **to_cpu(k))
                    return _CpuObject(r, label) if isinstance(r, cls) else to_gpu(r)
                return ctor
            return v

    class Wrapped(metaclass=Meta):
        def __new__(klass, *a, **k):
            STATS.cpu_calls[label] += 1
            return _CpuObject(cls(*to_cpu(a), **to_cpu(k)), label)

    Wrapped.__name__ = cls.__name__
    return Wrapped


#: ndarray を CPU へ運ばずに答えられる述語。ここを通さないと ``np.iterable(a)`` のために
#: 2048² の転送が起きる。
_NO_TRANSFER = {"issubdtype", "iterable", "promote_types", "finfo", "iinfo", "errstate",
                "seterr", "geterr", "printoptions", "set_printoptions", "isscalar",
                "format_float_positional", "format_float_scientific", "dtype", "isrealobj"}

#: CuPy の例外のうち「その引数の形は CuPy に無い」を意味するもの。OOM や値の誤りは含めない。
_RETRY_ON = (TypeError, NotImplementedError, ImportError, AttributeError)


def _coerce_seq(args):
    """Turn a leading list / tuple into one array, as numpy does implicitly."""
    cp = _cupy()
    out = list(args)
    for i, v in enumerate(out):
        if isinstance(v, (list, tuple)) or isinstance(v, _np.ndarray):
            try:
                out[i] = cp.asarray(v) if not isinstance(v, (list, tuple)) else cp.array(v)
            except Exception:  # noqa: BLE001 - 配列にならない引数はそのまま
                pass
    return out


def _all_scalar(a, k) -> bool:
    """No array anywhere in the arguments: numpy returns a scalar, CuPy a 0-d array."""
    return not any(isinstance(v, (list, tuple, _np.ndarray)) or _is_gpu(v)
                   for v in list(a) + list(k.values()))


def _gpu_call(gfn, cfn, label):
    """Try the CuPy function; on a signature CuPy lacks, cross to the CPU and count it."""
    def call(*a, **k):
        STATS.gpu_calls += 1
        try:
            return gfn(*a, **k)
        except _RETRY_ON as first:
            try:
                a2 = _coerce_seq(a)
                k2 = dict(zip(k, _coerce_seq(list(k.values()))))
                return gfn(*a2, **k2)
            except _RETRY_ON:
                if cfn is None:
                    raise first from None
            return _cpu_call(cfn, label)(*a, **k)
    call.__name__ = getattr(gfn, "__name__", label)
    return call


class _Ufunc:
    """CuPy ufunc keeping ``.reduce`` / ``.at`` / ``.accumulate``; lists are coerced."""

    def __init__(self, g, c, label):
        self._g, self._c, self._l = g, c, label

    def __call__(self, *a, **k):
        if self._c is not None and _all_scalar(a, k):
            return self._c(*a, **k)      # スカラーの計算は numpy のスカラーのまま(round() が効く)
        return _gpu_call(self._g, self._c, self._l)(*a, **k)

    def __getattr__(self, name):
        g = getattr(self._g, name, _MISSING)
        c = getattr(self._c, name, None)
        if g is _MISSING:
            return _cpu_call(c, "%s.%s" % (self._l, name)) if callable(c) else c
        return _gpu_call(g, c, "%s.%s" % (self._l, name)) if callable(g) else g


def _round(x, *n):
    """Builtin ``round``: a CuPy 0-d array has no ``__round__`` (numpy scalars do)."""
    return builtins.round(x.item() if _is_gpu(x) else x, *n)


def _sort_kw(k: dict) -> dict:
    """CuPy の ``kind`` は None か 'stable' だけ。numpy の名前を写す。"""
    if "kind" in k:
        k = dict(k)
        kind = k.pop("kind")
        if kind in ("stable", "mergesort"):
            k["kind"] = "stable"
    return k


def _ndarray_type():
    """``isinstance(x, np.ndarray)`` in shadow code must accept a CuPy array and numpy."""
    cp = _cupy()

    class Meta(type):
        def __instancecheck__(cls, x):
            return isinstance(x, (cp.ndarray, _np.ndarray))

        def __subclasscheck__(cls, c):
            return issubclass(c, (cp.ndarray, _np.ndarray))

    class ndarray(metaclass=Meta):  # noqa: N801 - numpy の名前のまま
        pass
    return ndarray


class _GenProxy:
    """``numpy.random.Generator`` with results on the GPU: the same stream as the CPU run."""

    def __init__(self, gen):
        self._gen = gen

    def __getattr__(self, name):
        v = getattr(self._gen, name)
        if callable(v):
            return _cpu_call(v, "random.%s" % name)
        return v


class _RandomProxy(types.SimpleNamespace):
    """``np.random``: always numpy's stream (CuPy's differs), results moved to the GPU."""

    def __getattr__(self, name):
        v = getattr(_np.random, name)
        if name in ("default_rng", "RandomState", "Generator"):
            def make(*a, **k):
                return _GenProxy(v(*a, **k))
            return make
        if callable(v) and not isinstance(v, type):
            return _cpu_call(v, "random.%s" % name)
        return v


class _Namespace:
    """Proxy of a numpy / scipy module.  解決の順序: 上書き → GPU 版 → CPU 版(計数つき)。"""

    def __init__(self, shadow, label, cpu_mod, gpu_mod):
        self.__dict__.update(_s=shadow, _l=label, _c=cpu_mod, _g=gpu_mod)

    def __repr__(self):
        return "<gpu_shadow proxy of %s>" % self._l

    def __getattr__(self, name):
        v = self._resolve(name)
        self.__dict__[name] = v
        return v

    def _resolve(self, name):
        cv = getattr(self._c, name, _MISSING)
        gv = getattr(self._g, name, _MISSING) if self._g is not None else _MISSING
        if cv is _MISSING and gv is _MISSING:
            try:
                return self._s.namespace(self._l + "." + name)
            except ImportError:
                raise AttributeError("%s has no attribute %r" % (self._l, name)) from None
        label = "%s.%s" % (self._l, name)
        if isinstance(cv, types.ModuleType) or isinstance(gv, types.ModuleType):
            return self._s.namespace(self._l + "." + name)
        if name in _NO_TRANSFER:
            return cv if cv is not _MISSING else gv
        if label == "numpy.ma.is_masked":
            return lambda x: False if _is_gpu(x) else cv(x)   # CuPy 配列に mask は無い
        cp = _cupy()
        if isinstance(cv, type) and issubclass(cv, BaseException):
            return cv
        if callable(cv) and not isinstance(cv, (type, types.FunctionType, _np.ufunc,
                                                types.BuiltinFunctionType)):
            return _CpuObject(cv, label)     # ``scipy.stats.norm``: 呼べるオブジェクト
        if gv is not _MISSING:
            if isinstance(gv, cp.ufunc):
                return _Ufunc(gv, cv if cv is not _MISSING else None, label)
            if isinstance(gv, type):
                if isinstance(cv, type):
                    return gv if self._l == "numpy" else _cpu_class(cv, label)
                return gv
            if callable(gv):
                return _gpu_call(gv, cv if callable(cv) else None, label)
            return gv
        if isinstance(cv, type):
            if issubclass(cv, (_np.generic, Warning, Exception)) or self._l == "numpy":
                return cv
            return _cpu_class(cv, label)
        if isinstance(cv, (types.FunctionType, types.BuiltinFunctionType, _np.ufunc)):
            return _cpu_call(cv, label)
        return cv


class _NumpyNamespace(_Namespace):
    """``numpy`` itself: array creation always lands on the GPU."""

    def _resolve(self, name):
        cp = _cupy()
        if name == "ndarray":
            return self._s.ndarray
        if name == "random":
            return _RandomProxy()
        if name in ("sort", "argsort"):
            full = _gpu_call(getattr(cp, name), getattr(_np, name), "numpy." + name)
            return lambda *a, **k: full(*a, **_sort_kw(k))
        if name in ("clip", "round", "around", "round_"):
            gfn2, cfn2 = getattr(cp, name, None), getattr(_np, name)
            full = _gpu_call(gfn2, cfn2, "numpy." + name) if gfn2 is not None else None

            def scalar_safe(*a, **k):
                if full is None or _all_scalar(a, k):
                    return cfn2(*a, **k)
                return full(*a, **k)
            return scalar_safe
        if name in ("asarray", "array", "asanyarray"):
            gfn = getattr(cp, name)
            cfn = getattr(_np, name)

            def make(obj, *a, **k):
                # 文字列・object は GPU に載らない: numpy のまま返す(下流で落ちれば例外として数える)
                try:
                    return gfn(obj, *a, **k)
                except (TypeError, ValueError, NotImplementedError):
                    return to_gpu(cfn(to_cpu(obj), *a, **k))
            return make
        return super()._resolve(name)


#: scipy 公開モジュール → CuPy 版。ここに無いもの(sparse / spatial / optimize)は CPU 側。
_GPU_TWIN = {"numpy.linalg": "cupy.linalg", "numpy.fft": "cupy.fft",
             "scipy.ndimage": "cupyx.scipy.ndimage", "scipy.signal": "cupyx.scipy.signal",
             "scipy.fft": "cupyx.scipy.fft", "scipy.fftpack": "cupyx.scipy.fftpack",
             "scipy.linalg": "cupyx.scipy.linalg", "scipy.special": "cupyx.scipy.special",
             "scipy.stats": "cupyx.scipy.stats", "scipy.interpolate": "cupyx.scipy.interpolate"}


class ShadowImporter:
    """Compile project modules a second time, with numpy / scipy pointed at the GPU."""

    def __init__(self):
        self.mods: dict = {}
        self.spaces: dict = {}
        self._new: list = []
        self._lock = threading.RLock()
        self._depth = 0
        self.failed: dict = {}
        self.builtins = dict(vars(builtins))
        self.builtins["__import__"] = self._import
        self.builtins["round"] = _round
        self._ndarray = None
        self._importlib = _ImportlibProxy(self)

    @property
    def ndarray(self):
        if self._ndarray is None:
            self._ndarray = _ndarray_type()
        return self._ndarray

    # ---- proxies ---- #
    def namespace(self, dotted: str):
        """The proxy of ``numpy`` / ``numpy.linalg`` / ``scipy.ndimage`` …."""
        ns = self.spaces.get(dotted)
        if ns is not None:
            return ns
        cpu = importlib.import_module(dotted)
        twin = _GPU_TWIN.get(dotted)
        gpu = None
        if dotted == "numpy":
            gpu = _cupy()
        elif twin:
            try:
                gpu = importlib.import_module(twin)
            except ImportError:
                gpu = None
        cls = _NumpyNamespace if dotted == "numpy" else _Namespace
        ns = self.spaces[dotted] = cls(self, dotted, cpu, gpu)
        return ns

    # ---- import hook (only ever seen by shadow code) ---- #
    @staticmethod
    def is_project(name: str) -> bool:
        return "." not in name and os.path.isfile(os.path.join(ROOT, name + ".py"))

    def _import(self, name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if level == 0:
            if self.is_project(name) and name != "gpu_shadow":
                return self.load(name)
            top = name.split(".")[0]
            if top == "importlib" and name == "importlib":
                return self._importlib
            # scipy は import 中でも proxy を渡す: 関数の中の ``from scipy import signal`` が
            # 登録時に走り、閉包に本物が残る op がある(backends_scipy)。numpy は表を作るので本物
            if top == "scipy" or (top == "numpy" and self._depth == 0):
                return self.namespace(name if fromlist else top)
        return builtins.__import__(name, globals, locals, fromlist, level)

    def load(self, name: str):
        """The shadow of project module *name*; compiled once, per importer."""
        with self._lock:
            mod = self.mods.get(name)
            if mod is not None:
                return mod
            real = importlib.import_module(name)     # dataclasses / NamedTuple が本物を引く
            spec = importlib.util.find_spec(name)
            code = spec.loader.get_code(name)
            mod = types.ModuleType(name, getattr(real, "__doc__", None))
            mod.__dict__.update(__file__=spec.origin, __spec__=spec, __package__="",
                                __loader__=spec.loader, __builtins__=self.builtins)
            self.mods[name] = mod
            self._new.append(mod)
            self._depth += 1
            try:
                exec(code, mod.__dict__)             # noqa: S102 - 自分のソースを再実行するだけ
            except BaseException:
                self.mods.pop(name, None)
                raise
            finally:
                self._depth -= 1
            if self._depth == 0:
                new, self._new = self._new, []
                for m in new:
                    self._rebind(m)
            return mod

    def _rebind(self, mod) -> None:
        """Point a finished module's numpy / scipy names at the proxies."""
        cp = _cupy()
        ns = mod.__dict__
        for key, v in list(ns.items()):
            if key.startswith("__"):
                continue
            if isinstance(v, types.ModuleType):
                nm = v.__name__
                if nm == "numpy" or nm.startswith("numpy.") or nm == "scipy" \
                        or nm.startswith("scipy."):
                    ns[key] = self.namespace(self._public(nm))
                elif nm == "importlib":
                    ns[key] = self._importlib
                continue
            if isinstance(v, _np.ndarray):
                if v.dtype.kind in "biufc" and v.size:
                    ns[key] = cp.asarray(v)
                continue
            if isinstance(v, type) and issubclass(v, _np.generic):
                continue
            origin = getattr(v, "__module__", None)
            if origin is None and isinstance(v, _np.ufunc):
                origin = "numpy"
            if isinstance(origin, str) and (origin == "numpy" or origin.startswith("numpy.")
                                            or origin.startswith("scipy.")) \
                    and callable(v) and hasattr(v, "__name__"):
                try:
                    ns[key] = getattr(self.namespace(self._public(origin)), v.__name__)
                except (AttributeError, ImportError):
                    pass

    @staticmethod
    def _public(dotted: str) -> str:
        """``scipy.ndimage._filters`` -> ``scipy.ndimage``(private な枝を落とす)."""
        parts = dotted.split(".")
        keep = [parts[0]]
        for p in parts[1:]:
            if p.startswith("_") or p == "core":
                break
            keep.append(p)
        return ".".join(keep)


class _ImportlibProxy:
    """``importlib`` seen from shadow code: ``import_module`` stays inside the shadow."""

    def __init__(self, shadow):
        self._s = shadow

    def import_module(self, name, package=None):
        if self._s.is_project(name):
            return self._s.load(name)
        return importlib.import_module(name, package)

    def __getattr__(self, name):
        return getattr(importlib, name)


_SHADOW = None
_SHADOW_LOCK = threading.Lock()


def get_shadow() -> ShadowImporter:
    """The process-wide importer (compiled lazily, once)."""
    global _SHADOW
    with _SHADOW_LOCK:
        if _SHADOW is None:
            _cupy()
            _SHADOW = ShadowImporter()
        return _SHADOW


def shadow_fn(name: str):
    """The shadow callable of a registry or ledger op, or ``None`` when it has none."""
    sh = get_shadow()
    ops = sh.load("ops")
    fn = getattr(ops, "RT", {}).get(name)
    if fn is not None:
        return fn
    nary = sh.load("imgops_nary")
    for o in nary.build_nary():
        if o.name == name:
            return o.fn
    for row in sh.load("typed_catalog").catalog():
        if row[0] == name:
            return row[4]
    return None


def allowed_ops() -> dict:
    """``{op: row}`` of the machine-readable allow-list (empty when none is shipped)."""
    try:
        with open(ALLOW_PATH, encoding="utf-8") as f:
            return dict(json.load(f).get("ops", {}))
    except FileNotFoundError:
        return {}


def run_allowed(name: str, *args, **kwargs):
    """Run allow-listed op *name* on the GPU; numpy in, numpy out.

    Fail-closed: an op outside the list, or a host without CuPy/CUDA, raises
    :class:`GpuAutoError` instead of quietly running somewhere else.
    許可リスト外は黙って CPU へ落とさず拒否する(呼ぶ側が選ぶ)。
    """
    if name not in allowed_ops():
        raise GpuAutoError("%r is not on the GPU allow-list (%s)"
                           % (name, os.path.basename(ALLOW_PATH)))
    if not available():
        raise GpuAutoError("no CUDA device visible to CuPy")
    fn = shadow_fn(name)
    if fn is None:
        raise GpuAutoError("%r has no shadow callable" % (name,))
    return to_cpu(fn(*to_gpu(args), **to_gpu(kwargs)))


def apply(image, name: str, a: float = 0.5, b: float = 0.5, device: str = "cuda"):
    """``fullseye.apply`` with the allow-listed GPU path, on explicit request only.

    ``device="cuda"`` runs an allow-listed registry op through the shadow when *image*
    is a float64 array and CuPy sees a device; every other case — ``device="cpu"``, an
    op outside the list, another dtype, a host without CUDA — is plain
    :func:`api.apply`, whose contract and fallback ledger are unchanged.
    明示の ``device="cuda"`` と許可リストの両方が揃ったときだけ GPU へ行く。
    """
    import api
    if str(device) == "cuda" and name in allowed_ops() and isinstance(image, _np.ndarray)             and image.dtype == _np.float64 and name in importlib.import_module("ops").RT             and available():
        return run_allowed(name, image, a, b)
    return api.apply(image, name, a, b, device=device)
