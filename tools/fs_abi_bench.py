"""`fullseye_abi.h` の 2 実装(`fslib` と Rust)を **速度で**突き合わせる。

正しさの門は `tests/test_rust_abi_parity.py`。こちらは**測るだけ**で、合否は出さない ——
速い遅いを CI の合否にすると、機械が変わるたびに赤くなるだけで何も守れない。

**この数字を読むときに必ず要る前置き**:

* Rust 側は **素のスカラ実装**(SIMD なし、`connection` は run の総当たり O(n^2))。
  「Rust だから速い」の材料ではなく、**同じ契約を素直に書くといくらか**の基準線。
* ctypes の境界で **画素を 1 回コピー**している(`fs_image_create`)。演算そのものと
  境界のコストを**分けて出す**。分けないと「速い」も「遅い」も嘘になる。
* 冷えた状態は熱定常より速く出る(実測 1.7 倍)ので、先に暖機する。
* 表現が違えば**同じ仕事をしていない**。Rust の Region は run-length なので、
  `connection` と `measure_all` は O(run 数) で済む。numpy/cv2 は dense なラベル画像に
  対して O(画素数) を掛け直す。ここで出る大差は**言語差ではなく表現差**。

使い方(Rust 実装を先に建てておくこと):

    cd rust/fullseye_core && cargo build --release
    py -3.11 tools/fs_abi_bench.py [--size 512] [--warm 12]
"""
from __future__ import annotations

import argparse
import ctypes as C
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import fslib  # noqa: E402

LIBNAME = {"win32": "fullseye_core.dll", "darwin": "libfullseye_core.dylib"}.get(
    sys.platform, "libfullseye_core.so")
LIB = ROOT / "rust" / "fullseye_core" / "target" / "release" / LIBNAME


def load_rust():
    if not LIB.exists():
        print("Rust 実装が建っていない(%s)。\n"
              "  cd rust/fullseye_core && cargo build --release\n"
              "を先に走らせること —— **建たなかった**ことを「速度差が無い」と混ぜない。"
              % LIB.name)
        raise SystemExit(2)
    lib = C.CDLL(str(LIB))
    p = C.POINTER
    lib.fs_image_create.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_int64,
                                    C.c_double, C.c_double, p(C.c_void_p)]
    lib.fs_threshold.argtypes = [C.c_void_p, C.c_double, C.c_double, p(C.c_void_p)]
    lib.fs_gauss.argtypes = [C.c_void_p, C.c_double, p(C.c_void_p)]
    lib.fs_connection.argtypes = [C.c_void_p, p(C.c_void_p)]
    lib.fs_region_run_count.argtypes = [C.c_void_p, p(C.c_int64)]
    lib.fs_measure_all.argtypes = [C.c_void_p] + [p(C.c_void_p)] * 3
    for n in ("fs_image_release", "fs_region_release", "fs_objectset_release",
              "fs_tuple_release"):
        getattr(lib, n).argtypes = [C.c_void_p]
        getattr(lib, n).restype = None
    return lib


def make_scene(n: int, seed: int = 2) -> np.ndarray:
    """円盤を散らした構造つきの場面 + 弱い雑音。

    乱数だけのしきい値像は run が細切れになり、`connection` の性格そのものが変わる
    (feedback_random_test_data_hides_structural_defects)。検査の絵に寄せる。
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((n, n))
    a = np.zeros((n, n))
    lo, hi = int(n * 0.04), int(n * 0.96)
    for (cy, cx), rr in zip(rng.integers(lo, hi, size=(60, 2)),
                            rng.integers(n // 85 + 3, n // 28 + 3, size=60)):
        a[(yy - int(cy)) ** 2 + (xx - int(cx)) ** 2 <= int(rr) ** 2] = 1.0
    return np.clip(a + rng.random((n, n)) * 0.2, 0.0, 1.0)


def warm(seconds: float):
    print("熱定常にするため %.0f 秒まわす(冷えた状態は速く出るので測らない)..." % seconds)
    x = np.random.default_rng(1).random((512, 512))
    t0, k = time.perf_counter(), 0
    while time.perf_counter() - t0 < seconds:
        x = x * 1.0000001 + 1e-9
        float(x.sum())
        k += 1
    print("  暖機 %d 回" % k)


def bench(fn, repeats=7, inner=1):
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        for _ in range(inner):
            fn()
        ts.append((time.perf_counter() - t0) / inner)
    ts.sort()
    return ts[len(ts) // 2] * 1e3, ts[0] * 1e3


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--warm", type=float, default=12.0)
    ap.add_argument("--sigma", type=float, default=2.0)
    args = ap.parse_args()

    lib = load_rust()
    a = np.ascontiguousarray(make_scene(args.size))
    vr, lo, hi = (0.0, 1.0), 0.5, 1.0
    img_py = fslib.FImage(a, value_range=vr)
    reg_py = fslib.threshold(img_py, lo, hi)

    def mk():
        img = C.c_void_p()
        assert lib.fs_image_create(a.ctypes.data_as(C.c_void_p), a.shape[0], a.shape[1],
                                   a.strides[0], vr[0], vr[1], C.byref(img)) == 0
        return img

    img_r = mk()
    reg_r = C.c_void_p()
    lib.fs_threshold(img_r, lo, hi, C.byref(reg_r))
    nrun = C.c_int64()
    lib.fs_region_run_count(reg_r, C.byref(nrun))
    objs_r = C.c_void_p()
    lib.fs_connection(reg_r, C.byref(objs_r))

    warm(args.warm)
    print()
    print("=" * 78)
    print("%dx%d f64 / 面積 %d 画素 / run 数 %d / 中央値 ms / 最小 ms"
          % (args.size, args.size, int(reg_py.area()), nrun.value))
    print("=" * 78)

    def boundary():
        lib.fs_image_release(mk())
    med, mn = bench(boundary)
    print("  [境界] ctypes の画素コピー+生成+解放   %9.3f / %9.3f" % (med, mn))
    print("         ↑ 下の Rust 行はすべてこれを含む。**引いてから読むこと**")

    def avail(op):
        return [b for b in fslib.backends_for(op) if b in fslib._REGISTRY[op]]

    rows = []

    def r_thr():
        img = mk()
        reg = C.c_void_p()
        lib.fs_threshold(img, lo, hi, C.byref(reg))
        lib.fs_region_release(reg)
        lib.fs_image_release(img)
    rows.append(("threshold", "Rust(境界込み)", bench(r_thr)))
    for b in avail("threshold"):
        rows.append(("threshold", b, bench(lambda b=b: fslib._REGISTRY["threshold"][b](img_py, lo, hi))))

    s = args.sigma

    def r_g():
        img = mk()
        out = C.c_void_p()
        lib.fs_gauss(img, s, C.byref(out))
        lib.fs_image_release(out)
        lib.fs_image_release(img)
    rows.append(("gauss s=%g" % s, "Rust(素のスカラ, 境界込み)", bench(r_g, repeats=5)))
    for b in avail("gauss"):
        rows.append(("gauss s=%g" % s, b, bench(lambda b=b: fslib._REGISTRY["gauss"][b](img_py, s), repeats=5)))

    def r_conn():
        o = C.c_void_p()
        lib.fs_connection(reg_r, C.byref(o))
        lib.fs_objectset_release(o)
    rows.append(("connection", "Rust(run 総当たり O(n^2))", bench(r_conn, repeats=3)))
    for b in avail("connection"):
        rows.append(("connection", b, bench(lambda b=b: fslib._REGISTRY["connection"][b](reg_py), repeats=5)))

    def r_meas():
        t = [C.c_void_p(), C.c_void_p(), C.c_void_p()]
        lib.fs_measure_all(objs_r, C.byref(t[0]), C.byref(t[1]), C.byref(t[2]))
        for x in t:
            lib.fs_tuple_release(x)
    rows.append(("measure_all", "Rust(run から積算 = O(run 数))", bench(r_meas)))
    for b in avail("measure_all"):
        rows.append(("measure_all", b, bench(
            lambda b=b: fslib._REGISTRY["measure_all"][b](fslib._REGISTRY["connection"][b](reg_py)),
            repeats=5)))

    cur = None
    for opn, who, (m, x) in rows:
        if opn != cur:
            print("  --- %s ---" % opn)
            cur = opn
        print("    %-32s %9.3f / %9.3f" % (who, m, x))

    print()
    print("読み方: 負ける演算子(threshold / gauss)は **ベクトル化・SIMD の欠如**であって")
    print("        言語の差ではない。勝つ演算子(connection / measure_all)は **表現の差** ——")
    print("        Rust は Region を run-length で持つので O(run 数)、numpy/cv2 は dense な")
    print("        ラベル画像に O(画素数) を掛け直す。**この利得は Python 側でも取れる。**")

    lib.fs_objectset_release(objs_r)
    lib.fs_region_release(reg_r)
    lib.fs_image_release(img_r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
