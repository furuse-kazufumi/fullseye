"""fullseye_abi.h を Python の ``ctypes`` から直接叩く見本。**バインディング層は無い。**

C(``c/main.c``)・C#(``csharp/Program.cs``)・LuaJIT(``luajit_ffi.lua``)と
**同じ 1 本の .dll / .so** を呼び、同じ 5 行を印字する。この見本は標準ライブラリ
だけで動く(numpy も fullseye 本体も import しない)—— 「Python から使う」の最小形は
これで、918 op の Python ライブラリとは別物である。

実行::

    cd rust/fullseye_core && cargo build --release
    py -3.11 examples/python_ctypes.py

宣言は ``fullseye_abi.h`` から書き写している。書き写しは C から ``#include`` する
呼び手(``c/main.c``)があって初めて型検査される —— この見本が正しいことの根拠は
``tests/test_abi_signatures_match.py`` が引数の数をヘッダと照合していることと、
出力が C の見本と一致することの 2 つで、この見本自身ではない。
"""
from __future__ import annotations

import ctypes as C
import sys
from pathlib import Path

#: ``fs_dtype_t``(契約 R-4)。この見本は f64 の画素しか渡さない。
FS_DTYPE_F64 = 4
FS_OK = 0

_LIBNAME = {"win32": "fullseye_core.dll", "darwin": "libfullseye_core.dylib"}.get(
    sys.platform, "libfullseye_core.so")


def load() -> C.CDLL:
    """cdylib を読み、使う関数の引数型を宣言して返す。無ければ理由つきで止まる。"""
    here = Path(__file__).resolve().parent
    path = here.parent / "target" / "release" / _LIBNAME
    if not path.exists():
        raise SystemExit(
            "%s が無い。先に `cd rust/fullseye_core && cargo build --release`" % path)
    lib = C.CDLL(str(path))
    P = C.POINTER
    lib.fs_abi_version.argtypes = [P(C.c_int32), P(C.c_int32)]
    # ★第 5 引数 fs_dtype_t。2026-09-14 までヘッダにだけ在って実装と FFI 宣言に
    #   無かった引数。ctypes は引数の数を検査しないので、抜けても黙って動く。
    lib.fs_image_create.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_int64,
                                    C.c_int32, C.c_double, C.c_double, P(C.c_void_p)]
    lib.fs_image_dtype.argtypes = [C.c_void_p, P(C.c_int32)]
    lib.fs_threshold.argtypes = [C.c_void_p, C.c_double, C.c_double, P(C.c_void_p)]
    lib.fs_region_area.argtypes = [C.c_void_p, P(C.c_int64)]
    lib.fs_region_run_count.argtypes = [C.c_void_p, P(C.c_int64)]
    lib.fs_connection.argtypes = [C.c_void_p, P(C.c_void_p)]
    lib.fs_objectset_count.argtypes = [C.c_void_p, P(C.c_int64)]
    for name in ("fs_image_release", "fs_region_release", "fs_objectset_release"):
        fn = getattr(lib, name)
        fn.argtypes = [C.c_void_p]
        fn.restype = None
    return lib


def check(st: int, what: str) -> None:
    """R-1: すべての関数が状態コードを返す。黙って代替値を使わない。"""
    if st != FS_OK:
        raise SystemExit("%s が status %d を返した" % (what, st))


def main() -> int:
    fs = load()

    major, minor = C.c_int32(), C.c_int32()
    check(fs.fs_abi_version(C.byref(major), C.byref(minor)), "fs_abi_version")
    print("ABI %d.%d" % (major.value, minor.value))

    n = 8
    px = (C.c_double * (n * n))()
    for r in range(n):
        for c in range(n):
            px[r * n + c] = float((r + c) % 2)          # 市松

    img = C.c_void_p()
    check(fs.fs_image_create(px, n, n, n * C.sizeof(C.c_double), FS_DTYPE_F64,
                             0.0, 1.0, C.byref(img)), "fs_image_create")
    dt = C.c_int32()
    check(fs.fs_image_dtype(img, C.byref(dt)), "fs_image_dtype")
    print("dtype 読み返し: %d (FS_DTYPE_F64 = %d)" % (dt.value, FS_DTYPE_F64))

    # lo/hi は 0..1 の相対値。画像が名乗る値域を通して解決される(R-3)。
    reg = C.c_void_p()
    check(fs.fs_threshold(img, 0.5, 1.0, C.byref(reg)), "fs_threshold")

    area, runs = C.c_int64(), C.c_int64()
    check(fs.fs_region_area(reg, C.byref(area)), "fs_region_area")
    check(fs.fs_region_run_count(reg, C.byref(runs)), "fs_region_run_count")

    objs = C.c_void_p()
    check(fs.fs_connection(reg, C.byref(objs)), "fs_connection")
    count = C.c_int64()
    check(fs.fs_objectset_count(objs, C.byref(count)), "fs_objectset_count")

    print("面積 %d / run %d / 物体 %d" % (area.value, runs.value, count.value))
    # 契約は 8 連結なので市松は 1 個(4 連結なら 32 個)。
    ok = area.value == 32 and count.value == 1
    print("契約どおり: 8x8 の市松は 8 連結で 1 個" if ok else "★契約と違う")

    # 逆さの区間は「空」ではなく **失敗**(R-1)。
    bad_reg = C.c_void_p()
    bad = fs.fs_threshold(img, 0.8, 0.2, C.byref(bad_reg))
    print("逆さの区間 lo>hi は status %d で拒まれた" % bad if bad != FS_OK
          else "★逆さの区間が通ってしまった")

    fs.fs_objectset_release(objs)
    fs.fs_region_release(reg)
    fs.fs_image_release(img)
    return 0 if (ok and bad != FS_OK) else 1


if __name__ == "__main__":
    sys.exit(main())
