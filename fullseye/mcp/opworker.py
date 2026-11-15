# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""台帳 op(光学・照明・合成の入口など)を、隔離した子プロセスで走らせる。

MCP の ``fullseye_pipeline`` は、registry 層の op を同じプロセスで走らせる(画素数の上限と、生成時の
「2 秒以内」の検証が実行時間を縛る)。台帳 op は**引数で仕事の大きさが決まる**(格子の点数、光線の本数)ので、
同じやり方では 1 回の呼び出しの時間とメモリを縛れない。ここでは子プロセスに分け、親が時間で、子が自分の
メモリで止める:

- **時間**: 親が ``time_limit_s`` を過ぎたら子を殺す(``reason="time_limit"``)。
- **メモリ**: 子の見張りスレッドが 50 ms ごとに自分の使用量を読み、op を呼ぶ直前からの**増分**が
  ``max_rss`` を超えたら即終了する(終了コード :data:`EXIT_MEMORY` → ``reason="memory_limit"``)。
  増分で数えるのは、import しただけで commit が 1.8 GB ある環境があるから(2026-11-13 実測)。
  50 ms の間の急増は次の周期で止まる。
- **ファイルとネット**: 子は audit hook で、作業用の一時フォルダの外への書き込み・Python と fullseye の
  置き場所の外の読み込み・ソケット・子プロセスの起動を拒否する(``PermissionError``、fail-closed)。
  読める場所は :func:`_read_roots`(Python の本体と site-packages・fullseye の置き場所・作業フォルダ)だけで、
  親の ``sys.path`` の他の場所(``python -m`` で起動した時の cwd など)は入れない。
- **import**: 子は ``-I``(PYTHONPATH・ユーザの site・cwd を読まない)で起動し、``sys.path`` には親の物のうち
  :func:`_trusted_roots` の中の場所だけを渡す。台帳のモジュールは、点の無い名前で、出どころ(``spec.origin``)が
  fullseye の置き場所の中の物だけを読む(:func:`_ledger_module`)。
- **結果の大きさ**: job の ``max_elements``(配列の要素と、配列でない値・dict / list の数の和)・``max_result_bytes``
  (配列のバイト + 文字列の長さ + 他の値 1 つ 8 バイト)を子が数え、超えたら結果を書き出さずに断る
  (``reason="output_limit"``)。返事の 1 行は :data:`MAX_REPLY_BYTES` まで(子が JSON にしてから測り、親も 1 行を
  その長さまでしか読まない)。メモリの見張りと囲いは、結果を送り終えるまで掛けたまま。親も子の出力を読む前に、
  ``.npy`` の見出しで数える。
- **値の受け渡し**: JSON の木 + 数値配列だけ(pickle は使わない。object 配列・知らない型は拒否)。

子は使い回す(import の時間を毎回払わない)。時間切れ・メモリ超過・異常終了のあとは作り直す。
親の側の入口は :func:`run_isolated` だけ。
"""
from __future__ import annotations

import atexit
import base64
import importlib
import importlib.util
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np

#: 子がメモリの上限で自分を止めたときの終了コード。
EXIT_MEMORY = 86
#: 子の起動と import を待つ上限(秒)。op の実行時間の上限とは別。
STARTUP_LIMIT_S = 180.0
#: これより小さい配列は JSON の中に base64 で運ぶ(大きい配列は一時フォルダの .npy)。
INLINE_ARRAY_BYTES = 1 << 20
#: 1 回の返事の中で JSON に base64 で運ぶ小さい配列の合計の上限(超えた分は .npy で渡す)。
INLINE_TOTAL_BYTES = 8 * 1024 * 1024
#: 子の返事の 1 行の上限(バイト)。配列は .npy で渡すので、この行に入るのは JSON の木と小さい配列だけ。
MAX_REPLY_BYTES = 64 * 1024 * 1024
#: 受け渡す木の深さの上限。
MAX_TREE_DEPTH = 12
_NUMERIC_KINDS = "biufc"
#: 台帳のモジュールの名前の形(点の無い、最上位のモジュールだけ)。
_MODULE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
#: 親の読み手が、上限を超える 1 行を見た時に置く印。
_TOO_LONG = object()


class OpWorkerError(RuntimeError):
    """隔離した実行の失敗。``reason`` は機械が読む符号。"""

    def __init__(self, reason: str, message: str, *, error_type: str | None = None):
        super().__init__(message)
        self.reason = reason
        self.error_type = error_type


# --------------------------------------------------------------------------- #
# 値の符号化(JSON の木 + 数値配列。pickle を使わない)                           #
# --------------------------------------------------------------------------- #
def encode_tree(value, folder: str, _depth: int = 0, _counter: list | None = None):
    """Python の値 → JSON にできる木。数値配列以外の ndarray・知らない型は ``TypeError``。"""
    counter = _counter if _counter is not None else [0, 0]          # [.npy の数, JSON に入れた配列のバイト]
    if _depth > MAX_TREE_DEPTH:
        raise TypeError("value is nested deeper than %d levels" % MAX_TREE_DEPTH)
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value if -(2 ** 53) <= value <= 2 ** 53 else {"t": "i", "v": str(value)}
    if isinstance(value, float):
        return {"t": "f", "v": repr(value)} if value != value or value in (float("inf"), float("-inf")) else value
    if isinstance(value, complex):
        return {"t": "c", "v": [repr(value.real), repr(value.imag)]}
    if isinstance(value, np.generic):
        if value.dtype.kind not in _NUMERIC_KINDS:
            raise TypeError("unsupported numpy scalar dtype %s" % value.dtype)
        return {"t": "g", "dtype": value.dtype.str, "v": encode_tree(value.item(), folder, _depth + 1, counter)}
    if isinstance(value, np.ndarray):
        if value.dtype.kind not in _NUMERIC_KINDS:
            raise TypeError("unsupported array dtype %s (only numeric arrays cross the worker boundary)" % value.dtype)
        arr = np.ascontiguousarray(value)
        if arr.nbytes <= INLINE_ARRAY_BYTES and counter[1] + arr.nbytes <= INLINE_TOTAL_BYTES:
            counter[1] += int(arr.nbytes)
            return {"t": "a", "dtype": arr.dtype.str, "shape": list(arr.shape),
                    "b64": base64.b64encode(arr.tobytes()).decode("ascii")}
        counter[0] += 1
        name = "a%06d.npy" % counter[0]
        np.save(os.path.join(folder, name), arr, allow_pickle=False)
        return {"t": "n", "file": name}
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if isinstance(key, (bool, int, float, np.generic)):
                key = str(key.item() if isinstance(key, np.generic) else key)
            if not isinstance(key, str):
                raise TypeError("unsupported dict key type %s" % type(key).__name__)
            out[key] = encode_tree(item, folder, _depth + 1, counter)
        return {"t": "d", "v": out}
    if isinstance(value, (list, tuple)):
        return {"t": "l" if isinstance(value, list) else "u",
                "v": [encode_tree(item, folder, _depth + 1, counter) for item in value]}
    raise TypeError("unsupported value type %s (the worker boundary carries JSON trees and numeric arrays only)"
                    % type(value).__name__)


class ResultTooLarge(ValueError):
    """子の出力の配列の要素の数が ``max_elements`` を超えた(読む前に断った)。"""


def _spend(budget: list | None, count: int) -> None:
    """値の数(配列の要素 + 配列でない値と dict / list の数)を予算から引く。超えたら :class:`ResultTooLarge`。"""
    if budget is None:
        return
    budget[0] -= int(count)
    if budget[0] < 0:
        raise ResultTooLarge("the value has more than %d values (array elements and other values) in total "
                             "(max_elements)" % budget[1])


def decode_tree(node, folder: str, _depth: int = 0, *, max_elements: int | None = None, _budget: list | None = None):
    """:func:`encode_tree` の逆。形の崩れた木は ``ValueError``(信頼境界: 子の出力も検査する)。

    ``max_elements`` を渡すと、配列の要素の数の和がそれを超えた時点で ``ValueError``。``.npy`` は見出しの形で
    数えてから読む(★2026-11-15、独立レビュー: 以前は全部読んでから、サーバが画素の上限で断っていた)。"""
    if _budget is None and max_elements is not None:
        _budget = [int(max_elements), int(max_elements)]
    if _depth > MAX_TREE_DEPTH + 2:
        raise ValueError("tree is nested too deeply")
    if node is None or isinstance(node, (bool, int, float, str)):
        _spend(_budget, 1)
        return node
    if not isinstance(node, dict) or "t" not in node:
        raise ValueError("malformed tree node")
    tag = node["t"]
    if tag not in ("a", "n"):
        _spend(_budget, 1)                     # ★2026-11-15(外部レビュー): 配列でない値・dict / list も数える
    if tag == "i":
        return int(node["v"])
    if tag == "f":
        return float(node["v"])
    if tag == "c":
        return complex(float(node["v"][0]), float(node["v"][1]))
    if tag == "g":
        dtype = np.dtype(node["dtype"])
        if dtype.kind not in _NUMERIC_KINDS:
            raise ValueError("unsupported scalar dtype")
        return dtype.type(decode_tree(node["v"], folder, _depth + 1))           # 中身は上で 1 つと数えた
    if tag == "a":
        dtype = np.dtype(node["dtype"])
        if dtype.kind not in _NUMERIC_KINDS:
            raise ValueError("unsupported array dtype")
        shape = tuple(int(x) for x in node["shape"])
        _spend(_budget, int(np.prod(shape, dtype=np.int64)))
        raw = base64.b64decode(node["b64"].encode("ascii"), validate=True)
        if len(raw) != int(np.prod(shape, dtype=np.int64)) * dtype.itemsize:
            raise ValueError("array payload does not match its declared shape")
        return np.frombuffer(raw, dtype=dtype).reshape(shape).copy()
    if tag == "n":
        name = node["file"]
        if not isinstance(name, str) or os.path.basename(name) != name or not name.endswith(".npy"):
            raise ValueError("malformed array file name")
        path = os.path.join(folder, name)
        if _budget is not None:
            head = np.load(path, mmap_mode="r", allow_pickle=False)      # 見出しだけ(中身は読まない)
            count, kind = int(head.size), head.dtype.kind
            del head                                                     # 写像を閉じる(Windows でファイルを消せるように)
            if kind not in _NUMERIC_KINDS:
                raise ValueError("unsupported array dtype")
            _spend(_budget, count)
        arr = np.load(path, allow_pickle=False)
        if arr.dtype.kind not in _NUMERIC_KINDS:
            raise ValueError("unsupported array dtype")
        return arr
    if tag == "d":
        return {str(k): decode_tree(v, folder, _depth + 1, _budget=_budget) for k, v in node["v"].items()}
    if tag in ("l", "u"):
        items = [decode_tree(v, folder, _depth + 1, _budget=_budget) for v in node["v"]]
        return items if tag == "l" else tuple(items)
    raise ValueError("unknown tree tag %r" % (tag,))


def _text_bytes(text: str) -> int:
    """文字列の UTF-8 のバイト数(ASCII だけなら写しを作らない)。"""
    return len(text) if text.isascii() else len(text.encode("utf-8", "surrogatepass"))


def result_counts(value, max_values: int | None = None, max_bytes: int | None = None) -> dict:
    """結果の木の大きさを、送る時と同じに数える(同じ物が 2 回あれば 2 回書くので 2 回数える)。再帰しない。

    返すのは ``array_elements`` / ``other_values``(配列でない葉と dict・list・tuple の数)/ ``array_bytes`` /
    ``other_bytes``(配列でない値 1 つ 8 バイト + 文字列と dict の鍵の UTF-8 の長さ)。``max_values`` か ``max_bytes``
    を超えた所で数えるのをやめる(大きな木を最後までたどらない)。:data:`MAX_TREE_DEPTH` より深い所は数えない
    (その木は符号化が断る)。

    ★2026-11-15(外部レビュー、Codex): 以前は配列の要素とバイトだけを数え、文字列・数の list・dict は 0 と数えた。
    200,000 文字の文字列や 50,000 個の数の list が、上限 10,000 要素 / 100,000 バイトを素通りした。"""
    c = {"array_elements": 0, "other_values": 0, "array_bytes": 0, "other_bytes": 0}
    todo = [(value, 0)]
    while todo:
        item, depth = todo.pop()
        if isinstance(item, np.ndarray):
            c["array_elements"] += int(item.size)
            c["array_bytes"] += int(item.nbytes)
        else:
            c["other_values"] += 1
            c["other_bytes"] += 8
            if isinstance(item, str):
                c["other_bytes"] += _text_bytes(item)
            elif isinstance(item, (bytes, bytearray)):
                c["other_bytes"] += len(item)
            elif isinstance(item, dict) and depth <= MAX_TREE_DEPTH:
                for key, sub in item.items():
                    c["other_bytes"] += _text_bytes(key) if isinstance(key, str) else 8
                    todo.append((sub, depth + 1))
            elif isinstance(item, (list, tuple)) and depth <= MAX_TREE_DEPTH:
                todo.extend((sub, depth + 1) for sub in item)
        if ((max_values and c["array_elements"] + c["other_values"] > max_values)
                or (max_bytes and c["array_bytes"] + c["other_bytes"] > max_bytes)):
            break
    return c


def _result_limit_error(value, job: dict) -> str | None:
    """結果が job の ``max_elements`` / ``max_result_bytes`` を超えれば理由の文、収まれば None。"""
    max_elements, max_bytes = job.get("max_elements"), job.get("max_result_bytes")
    if not max_elements and not max_bytes:
        return None
    c = result_counts(value, int(max_elements) if max_elements else None, int(max_bytes) if max_bytes else None)
    values = c["array_elements"] + c["other_values"]
    nbytes = c["array_bytes"] + c["other_bytes"]
    if max_elements and values > int(max_elements):
        return ("the op returned %d or more values (%d array elements + %d other values), above the %d limit "
                "(mcp_stack_max_pixels); ask for a smaller grid or window"
                % (values, c["array_elements"], c["other_values"], int(max_elements)))
    if max_bytes and nbytes > int(max_bytes):
        return ("the op returned %d or more bytes (%d of arrays + %d of strings and other values), above the %d "
                "limit (mcp_pipeline_max_intermediate_bytes)"
                % (nbytes, c["array_bytes"], c["other_bytes"], int(max_bytes)))
    return None


# --------------------------------------------------------------------------- #
# 子プロセスの側                                                                #
# --------------------------------------------------------------------------- #
def _memory_bytes() -> int:
    """このプロセスが今使っているメモリ(Windows は working set と commit の大きい方、他は RSS)。"""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class _Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        info = kernel32.K32GetProcessMemoryInfo
        info.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Counters), wintypes.DWORD]
        info.restype = ctypes.c_int
        counters = _Counters()
        counters.cb = ctypes.sizeof(_Counters)
        if not info(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return 0
        return int(max(counters.WorkingSetSize, counters.PagefileUsage))
    try:
        with open("/proc/self/statm", encoding="ascii") as fh:
            return int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(peak if sys.platform == "darwin" else peak * 1024)


class _Sandbox:
    """audit hook: 一時フォルダの外への書き込み・置き場所の外の読み込み・ネット・子プロセスを拒否する。"""

    _DENY = ("socket.connect", "socket.bind", "socket.getaddrinfo", "socket.gethostbyname",
             "socket.gethostbyaddr", "socket.sendto", "socket.sendmsg", "urllib.Request",
             "http.client.connect", "ftplib.connect", "smtplib.connect", "imaplib.open", "poplib.connect",
             "nntplib.connect", "telnetlib.Telnet.open", "webbrowser.open",
             "subprocess.Popen", "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "os.forkpty",
             "os.startfile", "os.startfile/2", "pty.spawn",
             "winreg.CreateKey", "winreg.DeleteKey", "winreg.DeleteValue", "winreg.SetValue",
             "winreg.SaveKey", "winreg.LoadKey", "os.putenv", "os.unsetenv", "os.kill", "signal.pthread_kill")
    _WRITE_PATH = ("os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.link",
                   "os.symlink", "os.truncate", "os.utime", "shutil.rmtree", "shutil.move", "shutil.copyfile",
                   "shutil.copymode", "shutil.copystat", "shutil.copytree", "shutil.chown", "shutil.make_archive",
                   "shutil.unpack_archive", "tempfile.mkstemp", "tempfile.mkdtemp", "os.mkfifo", "os.mknod")

    def __init__(self, tmp: str):
        self.tmp = os.path.realpath(tmp)
        self.read_roots = _read_roots(self.tmp)
        self.armed = False

    def _inside(self, path, roots) -> bool:
        if isinstance(path, int):
            return True                                   # 既に開いた記述子
        try:
            real = os.path.realpath(os.fsdecode(path))
        except (TypeError, ValueError):
            return False
        return any(real == root or real.startswith(root + os.sep) for root in roots)

    def hook(self, event: str, args) -> None:
        if not self.armed:
            return
        if event == "open":
            path, mode, flags = (list(args) + [None, None, None])[:3]
            writing = (isinstance(mode, str) and any(ch in mode for ch in "wax+")) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC))
            if writing:
                if not self._inside(path, (self.tmp,)):
                    raise PermissionError("the MCP op worker does not write files outside its scratch folder")
            elif not self._inside(path, self.read_roots) and os.fsdecode(path) not in (os.devnull, "/proc/self/statm"):
                raise PermissionError("the MCP op worker does not read files outside the Python and fullseye trees")
            return
        if event in self._DENY or event.startswith(("socket.connect", "os.exec", "os.spawn")):
            raise PermissionError("the MCP op worker has no network and starts no processes (%s)" % event)
        if event in self._WRITE_PATH:
            paths = [a for a in args[:2] if isinstance(a, (str, bytes, os.PathLike))]
            if event in ("tempfile.mkstemp", "tempfile.mkdtemp"):
                return
            if not all(self._inside(p, (self.tmp,)) for p in paths):
                raise PermissionError("the MCP op worker does not change files outside its scratch folder (%s)" % event)


def _dist_root() -> str:
    """fullseye の置き場所(fullseye パッケージと、台帳のモジュール(opsoptics …)が並ぶ場所)。"""
    return os.path.realpath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _inside(path, roots) -> bool:
    """*path* の実体が *roots* のどれかの中(またはそのもの)か。比べる前に realpath と normcase で揃える。"""
    try:
        real = os.path.normcase(os.path.realpath(os.fsdecode(path)))
    except (TypeError, ValueError, OSError):
        return False
    for root in roots:
        root = os.path.normcase(root).rstrip(os.sep)
        if real == root or real.startswith(root + os.sep):
            return True
    return False


def _trusted_roots() -> tuple:
    """子が import してよい場所: Python の本体(prefix と stdlib)・site-packages・fullseye の置き場所。"""
    import site
    import sysconfig
    candidates = [sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix, _dist_root()]
    for key in ("stdlib", "platstdlib", "purelib", "platlib"):
        try:
            candidates.append(sysconfig.get_path(key))
        except KeyError:
            pass
    try:
        candidates += list(site.getsitepackages())
    except AttributeError:                                   # 古い virtualenv の site
        pass
    try:
        candidates.append(site.getusersitepackages())
    except AttributeError:
        pass
    candidates += [p for p in sys.path if p and os.path.basename(os.path.normpath(p)).lower()
                   in ("site-packages", "dist-packages")]
    return tuple(sorted({os.path.realpath(p) for p in candidates if p}))


def _ledger_module(name):
    """台帳のモジュールを import して返す。点の無い名前で、出どころ(``spec.origin``)が fullseye の置き場所の中の
    物だけ。それ以外は ImportError(文にホストのパスは書かない)。

    ★2026-11-15(外部レビュー、Codex): 実行先の名前をそのまま ``import_module`` していた。sys.path を確かめた場所
    だけにした上で(:meth:`OpWorker._start`)、読む前に出どころを見る(標準ライブラリや site-packages にある同じ名前の
    物を、台帳と取り違えない)。"""
    if not isinstance(name, str) or not _MODULE_NAME.match(name):
        raise ImportError("ledger module name %r is not a plain top-level module name" % (str(name)[:80],))
    mod = sys.modules.get(name)
    spec = getattr(mod, "__spec__", None) if mod is not None else importlib.util.find_spec(name)
    origin = getattr(spec, "origin", None)
    if not origin or not os.path.isfile(origin) or not _inside(origin, (_dist_root(),)):
        raise ImportError("ledger module %s does not come from the fullseye installation" % name)
    return mod if mod is not None else importlib.import_module(name)


def _read_roots(tmp: str) -> tuple:
    """子が読んでよい場所: 作業フォルダ・Python の本体(prefix と stdlib)・site-packages・fullseye の置き場所。

    ★2026-11-15(独立レビュー、PR #318): 以前は親の ``sys.path`` を全部入れていた。``python -m fullseye.mcp`` は
    cwd を ``sys.path[0]`` に置くので、ドライブの直下やホームで起動すると読み込みの制限が実質なくなった。``sys.path`` からは
    site-packages / dist-packages という名前の場所だけを取る(Homebrew など prefix の外にある物のため)。"""
    return tuple(sorted(set(_trusted_roots()) | {os.path.realpath(tmp)}))


def _call_ledger_op(job: dict, args: list, kwargs: dict):
    """台帳の入口を呼ぶ(``opassist.run`` と同じ規則: adapter を通して宣言の out 型で返す)。"""
    mod = _ledger_module(job["ledger_module"])
    table = getattr(mod, job["ledger_table"])
    entry = table[job["key"]]
    caller = getattr(mod, "call", None)
    if job.get("data_names") and args:
        import inspect
        try:
            leading = [p.name for p in inspect.signature(entry["func"]).parameters.values()][:len(args)]
        except (TypeError, ValueError):
            leading = list(job["data_names"][:len(args)])
        if leading != list(job["data_names"][:len(args)]):
            kwargs = dict(kwargs, **dict(zip(job["data_names"], args)))
            args = []
    if caller is None or "name" in kwargs:
        return entry["func"](*args, **kwargs)
    return caller(job["key"], *args, **kwargs)


def _child_main(tmp: str) -> int:
    proto_out = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8", newline="\n")
    sys.stdout = sys.stderr                               # op の print がプロトコルを壊さない
    sys.dont_write_bytecode = True
    sandbox = _Sandbox(tmp)
    sys.addaudithook(sandbox.hook)
    state = {"limit": 0, "active": False}

    def watchdog():
        while True:
            time.sleep(0.05)
            if state["active"] and state["limit"] and _memory_bytes() > state["limit"]:
                os._exit(EXIT_MEMORY)

    threading.Thread(target=watchdog, name="fullseye-mcp-memory-watchdog", daemon=True).start()

    def check_memory() -> None:
        """見張りと同じ判定を、その場で 1 回。C の処理(json.dumps など)が GIL を持ったままだと見張りは回れない。"""
        if state["active"] and state["limit"] and _memory_bytes() > state["limit"]:
            os._exit(EXIT_MEMORY)

    def send_text(text: str) -> None:
        proto_out.write(text)
        proto_out.flush()

    def send(obj: dict) -> None:
        send_text(json.dumps(obj, ensure_ascii=False) + "\n")

    def encode_reply(obj: dict, limit: int) -> str:
        """返事を 1 行の JSON にし、長さを測る。上限を超えたら、結果の代わりに output_limit の返事にする。"""
        text = json.dumps(obj, ensure_ascii=False) + "\n"
        check_memory()
        size = _text_bytes(text)
        if size <= limit:
            return text
        return json.dumps({"id": obj.get("id"), "phase": "done", "ok": False,
                           "error": {"type": "ResourceLimit", "stage": "limit",
                                     "message": "the encoded reply is %d bytes, above the %d-byte reply limit; "
                                                "ask for a smaller result" % (size, limit)}},
                          ensure_ascii=False) + "\n"

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        job = json.loads(line)
        jid = job.get("id")
        in_dir = os.path.join(tmp, "in-%s" % jid)
        out_dir = os.path.join(tmp, "out-%s" % jid)
        reply_limit = min(int(job.get("max_reply_bytes") or MAX_REPLY_BYTES), MAX_REPLY_BYTES)
        try:
            _ledger_module(job["ledger_module"])                   # import の時間は実行時間に数えない
            args = [decode_tree(a, in_dir) for a in job.get("args", [])]
            kwargs = {str(k): decode_tree(v, in_dir) for k, v in (job.get("kwargs") or {}).items()}
        except Exception as exc:                                   # noqa: BLE001
            send({"id": jid, "phase": "done", "ok": False,
                  "error": {"type": type(exc).__name__, "message": str(exc)[:400], "stage": "prepare"}})
            continue
        send({"id": jid, "phase": "ready"})
        state["limit"] = (_memory_bytes() + int(job["max_rss"])) if job.get("max_rss") else 0
        started = time.monotonic()
        np_state = np.random.get_state()
        sandbox.armed = True
        state["active"] = True
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = _call_ledger_op(job, args, kwargs)
            elapsed = time.monotonic() - started
            check_memory()
            # ★2026-11-15(外部レビュー、Codex): 見張りと囲いを op が返った所で止めていて、結果を数える・JSON にする・
            #   送る間は上限の外だった(8 MB の NUL の文字列が、JSON で 48 MB になる)。送り終えるまで掛けたままにする。
            too_big = _result_limit_error(result, job)
            if too_big is not None:
                # ★2026-11-15(独立レビュー): 結果を .npy に書き出して親が全部読んでから断っていた。書かずに断る。
                del result
                reply = {"id": jid, "phase": "done", "ok": False,
                         "error": {"type": "ResourceLimit", "message": too_big, "stage": "limit"}}
            else:
                os.makedirs(out_dir, exist_ok=True)
                reply = {"id": jid, "phase": "done", "ok": True, "value": encode_tree(result, out_dir),
                         "elapsed_s": elapsed}
                del result
                check_memory()
            text = encode_reply(reply, reply_limit)
            del reply
        except MemoryError:
            os._exit(EXIT_MEMORY)
        except BaseException as exc:                               # noqa: BLE001 - op の失敗は結果として返す
            reply = {"id": jid, "phase": "done", "ok": False,
                     "error": {"type": type(exc).__name__, "message": str(exc)[:400], "stage": "run"}}
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                reply["error"]["message"] = "the op tried to stop the interpreter"
            text = json.dumps(reply, ensure_ascii=False) + "\n"
        try:
            send_text(text)
        finally:
            state["active"] = False
            sandbox.armed = False
            np.random.set_state(np_state)                          # 次の呼び出しへ乱数の状態を持ち越さない
    return 0


def _pump(stream, q: queue.Queue, limit: int) -> None:
    """子の返事を 1 行ずつ *q* へ。改行を除いて *limit* バイトを超える行を見たら :data:`_TOO_LONG` を置いて読むのを
    やめる(その子は捨てる)。最後に None。"""
    try:
        while True:
            raw = stream.readline(limit + 2)
            if not raw:
                break
            if len(raw) - (1 if raw.endswith(b"\n") else 0) > limit:
                q.put(_TOO_LONG)
                break
            q.put(raw)
    except (OSError, ValueError):
        pass
    q.put(None)


#: 子の起動。sys.path は最初の 1 行で渡す(コマンド行に載せると、長い sys.path で Windows の上限を超える)。
_BOOT = ("import sys, json; sys.path[:] = json.loads(sys.stdin.readline()); "
         "from fullseye.mcp.opworker import _child_main; sys.exit(_child_main(sys.argv[1]))")


# --------------------------------------------------------------------------- #
# 親の側                                                                        #
# --------------------------------------------------------------------------- #
class OpWorker:
    """子プロセス 1 つを持ち、1 回に 1 つの op を走らせる。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._queue: queue.Queue | None = None
        self._tmp: str | None = None
        self._seq = 0

    def _start(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="fullseye-mcp-worker-")
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
                   TMP=self._tmp, TEMP=self._tmp, TMPDIR=self._tmp)
        # ★2026-11-15(外部レビュー、Codex): 子へ親の sys.path を全部渡し、子は ``-I`` 無しで起動していた。``python -m``
        #   は cwd を sys.path に置くので、起動したフォルダ(信頼しない repo など)の ``scipy.py`` が、囲いを掛ける前に
        #   子で import された(手元で再現)。子は ``-I``(PYTHONPATH・ユーザの site・cwd を読まない)で起動し、
        #   sys.path には Python の本体・site-packages・fullseye の置き場所の中の場所だけを渡す。
        roots = _trusted_roots()
        paths = [os.path.abspath(p) for p in dict.fromkeys(p for p in sys.path if p) if _inside(p, roots)]
        self._proc = subprocess.Popen(
            [sys.executable, "-I", "-X", "utf8", "-B", "-c", _BOOT, self._tmp],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=self._tmp, env=env)
        self._proc.stdin.write((json.dumps(paths) + "\n").encode("utf-8"))
        self._proc.stdin.flush()
        self._queue = queue.Queue()
        threading.Thread(target=_pump, args=(self._proc.stdout, self._queue, MAX_REPLY_BYTES),
                         name="fullseye-mcp-worker-reader", daemon=True).start()

    def _stop(self) -> None:
        proc, tmp = self._proc, self._tmp
        self._proc = self._queue = self._tmp = None
        if proc is not None:
            try:
                proc.kill()
            except OSError:
                pass
            try:
                proc.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                pass
            for stream in (proc.stdin, proc.stdout):
                try:
                    if stream is not None:
                        stream.close()
                except OSError:
                    pass
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    def close(self) -> None:
        with self._lock:
            self._stop()

    def _next(self, timeout: float):
        try:
            raw = self._queue.get(timeout=max(0.0, timeout))
        except queue.Empty:
            return "timeout"
        if raw is None:
            return None
        if raw is _TOO_LONG:
            return {"phase": "too_long"}
        try:
            return json.loads(raw)
        except ValueError:
            return {"phase": "garbage"}

    def run(self, job: dict, args: list, kwargs: dict, *, time_limit_s: float, max_rss: int):
        """*job*(``ledger_module`` / ``ledger_table`` / ``key`` / ``data_names``)を走らせ、``(値, 情報)`` を返す。

        job に ``max_elements`` / ``max_result_bytes`` があれば、結果の大きさを子が数えて断る。

        失敗は :class:`OpWorkerError`: ``time_limit`` / ``memory_limit`` / ``output_limit`` / ``worker_died`` /
        ``op_error`` / ``unsupported_value`` / ``startup``。時間切れ・メモリ超過・異常終了では子を捨てる。"""
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._stop()
                self._start()
            self._seq += 1
            jid = "%d" % self._seq
            in_dir = os.path.join(self._tmp, "in-" + jid)
            out_dir = os.path.join(self._tmp, "out-" + jid)
            os.makedirs(in_dir, exist_ok=True)
            try:
                try:
                    message = dict(job, id=jid, max_rss=int(max_rss),
                                   args=[encode_tree(a, in_dir) for a in args],
                                   kwargs={k: encode_tree(v, in_dir) for k, v in kwargs.items()})
                except TypeError as exc:
                    raise OpWorkerError("unsupported_value", str(exc)) from None
                try:
                    self._proc.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
                    self._proc.stdin.flush()
                except OSError as exc:
                    self._stop()
                    raise OpWorkerError("worker_died", "the op worker is not accepting jobs (%s)" % exc) from None
                deadline = time.monotonic() + STARTUP_LIMIT_S
                running = False
                while True:
                    reply = self._next(deadline - time.monotonic())
                    if reply == "timeout":
                        self._stop()
                        if running:
                            raise OpWorkerError("time_limit", "the op ran longer than the %.0f s limit and was stopped"
                                                % time_limit_s)
                        raise OpWorkerError("startup", "the op worker did not start within %.0f s" % STARTUP_LIMIT_S)
                    if reply is None:
                        code = self._proc.poll() if self._proc is not None else None
                        if code is None:
                            try:
                                code = self._proc.wait(timeout=5)
                            except (OSError, subprocess.TimeoutExpired):
                                code = None
                        self._stop()
                        if code == EXIT_MEMORY:
                            raise OpWorkerError("memory_limit", "the op grew the worker's memory by more than "
                                                "the %d MiB limit and was stopped" % (int(max_rss) >> 20))
                        raise OpWorkerError("worker_died", "the op worker exited (code %s)" % code)
                    if reply.get("phase") == "too_long":
                        self._stop()
                        raise OpWorkerError("output_limit", "the op worker's reply was longer than %d bytes and was "
                                            "not read" % MAX_REPLY_BYTES)
                    if reply.get("id") != jid:
                        continue
                    if reply.get("phase") == "ready":
                        running = True
                        deadline = time.monotonic() + float(time_limit_s)
                        continue
                    if reply.get("phase") != "done":
                        continue
                    if not reply.get("ok"):
                        err = reply.get("error") or {}
                        if err.get("stage") == "limit":
                            raise OpWorkerError("output_limit", str(err.get("message", ""))[:400],
                                                error_type=err.get("type"))
                        reason = "unsupported_value" if err.get("stage") == "prepare" else "op_error"
                        if err.get("type") == "TypeError" and "worker boundary" in str(err.get("message")):
                            reason = "unsupported_value"
                        raise OpWorkerError(reason, str(err.get("message", ""))[:400], error_type=err.get("type"))
                    try:
                        value = decode_tree(reply["value"], out_dir, max_elements=job.get("max_elements"))
                    except ResultTooLarge as exc:
                        raise OpWorkerError("output_limit", str(exc)) from None
                    except (ValueError, KeyError, OSError, TypeError) as exc:
                        raise OpWorkerError("unsupported_value", "the op result could not be read back: %s" % exc) from None
                    return value, {"elapsed_s": float(reply.get("elapsed_s", 0.0))}
            finally:
                shutil.rmtree(in_dir, ignore_errors=True)
                shutil.rmtree(out_dir, ignore_errors=True)


_WORKER: OpWorker | None = None
_WORKER_LOCK = threading.Lock()


def run_isolated(job: dict, args: list, kwargs: dict, *, time_limit_s: float, max_rss: int):
    """プロセスに 1 つの使い回しの子で *job* を走らせる(:meth:`OpWorker.run`)。"""
    global _WORKER
    with _WORKER_LOCK:
        if _WORKER is None:
            _WORKER = OpWorker()
            atexit.register(close_worker)
        worker = _WORKER
    return worker.run(job, args, kwargs, time_limit_s=time_limit_s, max_rss=max_rss)


def close_worker() -> None:
    """子を止め、一時フォルダを消す(終了時に呼ばれる。何度呼んでもよい)。"""
    global _WORKER
    with _WORKER_LOCK:
        worker, _WORKER = _WORKER, None
    if worker is not None:
        worker.close()
