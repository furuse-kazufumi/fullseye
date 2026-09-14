"""`fullseye_abi.h` の契約を **2 度目に実装したもの**と `fslib` を突き合わせる。

目的は性能比較ではない。単一実装のテストは「実装者の解釈」を検査するだけで、
**解釈そのものが分かれうる場所**を指し示さない。同じ仕様を別の言語で書き、
同じ入力を通して食い違いを探す —— それが 2026-09-14 に
「同じ `connection` op が numpy backend で 4 連結、cv2 backend で 8 連結」という
静かな壊れ方を見つけた道筋。

作法は `algo_difftest.find_c_compiler` と同型:

  * cargo があれば `rust/fullseye_core` を release で建てて突き合わせる。
  * 無ければ **正直な理由つきで SKIP**(緑にはするが、理由を必ず表示する)。
  * 建ったのに食い違ったら **失敗**。「建たなかった」と「答えが違う」を混ぜない。

入力は **構造つきを先に**置く。市松模様は 4/8 連結を一発で分けるが、乱数では
絶対に出ない(feedback_random_test_data_hides_structural_defects)。
"""
from __future__ import annotations

import ctypes as C
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import fslib

ROOT = Path(__file__).resolve().parents[1]
CRATE = ROOT / "rust" / "fullseye_core"
LIBNAME = {"win32": "fullseye_core.dll", "darwin": "libfullseye_core.dylib"}.get(
    sys.platform, "libfullseye_core.so")


class FsRun(C.Structure):
    _fields_ = [("row", C.c_int32), ("col_begin", C.c_int32), ("col_end", C.c_int32)]


def _build() -> Path | None:
    """cdylib を建てて返す。cargo が無い / 建たないなら ``None``。"""
    if not CRATE.exists() or shutil.which("cargo") is None:
        return None
    try:
        subprocess.run(["cargo", "build", "--release"], cwd=str(CRATE),
                       check=True, capture_output=True, text=True, timeout=600)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    p = CRATE / "target" / "release" / LIBNAME
    return p if p.exists() else None


@pytest.fixture(scope="module")
def rust():
    p = _build()
    if p is None:
        pytest.skip("Rust 実装を建てられない(cargo が無いか、ビルドに失敗した)—— "
                    "契約の第 2 実装が無い環境では、この門は何も検査しない")
    lib = C.CDLL(str(p))
    lib.fs_image_create.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_int64,
                                    C.c_double, C.c_double, C.POINTER(C.c_void_p)]
    lib.fs_threshold.argtypes = [C.c_void_p, C.c_double, C.c_double, C.POINTER(C.c_void_p)]
    lib.fs_region_area.argtypes = [C.c_void_p, C.POINTER(C.c_int64)]
    lib.fs_region_run_count.argtypes = [C.c_void_p, C.POINTER(C.c_int64)]
    lib.fs_connection.argtypes = [C.c_void_p, C.POINTER(C.c_void_p)]
    lib.fs_objectset_count.argtypes = [C.c_void_p, C.POINTER(C.c_int64)]
    lib.fs_objectset_region.argtypes = [C.c_void_p, C.c_int64, C.POINTER(C.c_void_p)]
    lib.fs_abi_version.argtypes = [C.POINTER(C.c_int32), C.POINTER(C.c_int32)]
    for n in ("fs_image_release", "fs_region_release", "fs_objectset_release"):
        getattr(lib, n).argtypes = [C.c_void_p]
        getattr(lib, n).restype = None
    return lib


def _rust_run(lib, px, lo, hi, vrange):
    a = np.ascontiguousarray(px, dtype=np.float64)
    h, w = a.shape
    img = C.c_void_p()
    st = lib.fs_image_create(a.ctypes.data_as(C.c_void_p), h, w, a.strides[0],
                             vrange[0], vrange[1], C.byref(img))
    assert st == 0, "fs_image_create -> %d" % st
    reg = C.c_void_p()
    st = lib.fs_threshold(img, lo, hi, C.byref(reg))
    if st != 0:
        lib.fs_image_release(img)
        return {"status": st}
    area, nrun = C.c_int64(), C.c_int64()
    lib.fs_region_area(reg, C.byref(area))
    lib.fs_region_run_count(reg, C.byref(nrun))
    objs = C.c_void_p()
    assert lib.fs_connection(reg, C.byref(objs)) == 0
    ncomp = C.c_int64()
    lib.fs_objectset_count(objs, C.byref(ncomp))
    areas = []
    for i in range(int(ncomp.value)):
        sub = C.c_void_p()
        lib.fs_objectset_region(objs, i, C.byref(sub))
        sa = C.c_int64()
        lib.fs_region_area(sub, C.byref(sa))
        areas.append(int(sa.value))
        lib.fs_region_release(sub)
    lib.fs_objectset_release(objs)
    lib.fs_region_release(reg)
    lib.fs_image_release(img)
    return {"status": 0, "area": int(area.value), "n_runs": int(nrun.value),
            "n_comp": int(ncomp.value), "comp_areas": sorted(areas)}


def _python_run(px, lo, hi, vrange):
    img = fslib.FImage(np.ascontiguousarray(px, dtype=np.float64), value_range=vrange)
    try:
        reg = fslib.threshold(img, lo, hi)
    except fslib.FsTypeError:
        return {"status": 1}          # 契約の FS_E_INVALID_ARG に対応
    objs = fslib.connection(reg)
    areas = sorted(int(objs.region(i).area()) for i in range(len(objs.ids)))
    return {"status": 0, "area": int(reg.area()), "n_runs": int(reg.run_count()),
            "n_comp": len(objs.ids), "comp_areas": areas}


#: 構造つきを先に、乱数は最後。名前は失敗時に何が壊れたか分かるように付ける。
CASES = [
    ("斜めに接する2つの正方形", lambda: _two_squares(), 0.5, 1.0, (0.0, 1.0)),
    ("市松模様8x8(4連結なら32個/8連結なら1個)", lambda: _checker(8), 0.5, 1.0, (0.0, 1.0)),
    ("しきい値ちょうど(境界の開閉)", lambda: np.full((4, 4), 0.5), 0.5, 0.5, (0.0, 1.0)),
    ("範囲外しかない", lambda: np.zeros((5, 5)), 0.9, 1.0, (0.0, 1.0)),
    ("全面", lambda: np.full((5, 5), 0.5), 0.0, 1.0, (0.0, 1.0)),
    ("1画素", lambda: _one_pixel(), 0.5, 1.0, (0.0, 1.0)),
    ("横縞", lambda: _stripes(), 0.5, 1.0, (0.0, 1.0)),
    ("値域100..300(相対しきい値の写し)", lambda: _wide_range(), 0.5, 1.0, (100.0, 300.0)),
    ("逆さの区間 lo>hi(R-1: 失敗と空を区別)", lambda: np.full((4, 4), 0.5), 0.8, 0.2, (0.0, 1.0)),
    ("NaN と inf が混じる", lambda: _with_nonfinite(), 0.4, 0.6, (0.0, 1.0)),
    ("枠(端で切れる run)", lambda: _frame(), 0.5, 1.0, (0.0, 1.0)),
    ("値域の外に出た画素", lambda: np.array([[-5.0, 0.5, 7.0], [0.0, 1.0, 0.25]]), 0.0, 1.0, (0.0, 1.0)),
    ("定数画像", lambda: np.full((6, 6), 0.7), 0.7, 0.7, (0.0, 1.0)),
    ("乱数16x16", lambda: np.random.default_rng(0).random((16, 16)), 0.4, 0.6, (0.0, 1.0)),
]


def _two_squares():
    a = np.zeros((9, 9)); a[1:4, 1:4] = 1.0; a[4:7, 4:7] = 1.0
    return a


def _checker(n):
    return (np.indices((n, n)).sum(axis=0) % 2).astype(float)


def _one_pixel():
    a = np.zeros((6, 6)); a[3, 3] = 1.0
    return a


def _stripes():
    a = np.zeros((7, 7)); a[::2, :] = 1.0
    return a


def _wide_range():
    return np.array([[100.0, 150.0, 200.0], [250.0, 300.0, 175.0]])


def _with_nonfinite():
    a = np.full((4, 4), 0.5); a[1, 1] = np.nan; a[2, 2] = np.inf
    return a


def _frame():
    a = np.zeros((5, 5)); a[0, :] = 1.0; a[:, 4] = 1.0; a[4, :] = 1.0
    return a


@pytest.mark.parametrize("name,make,lo,hi,vrange", CASES, ids=[c[0] for c in CASES])
def test_rust_and_python_agree(rust, name, make, lo, hi, vrange):
    """同じ契約の 2 実装が同じ答えを出す。食い違ったら**契約が決めていない疑い**。"""
    px = make()
    r = _rust_run(rust, px, lo, hi, vrange)
    p = _python_run(px, lo, hi, vrange)
    assert (r["status"] == 0) == (p["status"] == 0), (
        "%s: 片方だけが拒否した(Rust status %d / Python status %d)。"
        "契約 R-1 は失敗と「何も無い」を区別するので、**どちらが正しいかは "
        "fullseye_abi.h が決める**" % (name, r["status"], p["status"]))
    if r["status"] != 0:
        return
    assert r["area"] == p["area"], "%s: 面積 Rust %d / Python %d" % (name, r["area"], p["area"])
    assert r["n_comp"] == p["n_comp"], (
        "%s: 連結成分 Rust %d / Python %d —— 4 連結と 8 連結が混じっていないか"
        % (name, r["n_comp"], p["n_comp"]))
    assert r["comp_areas"] == p["comp_areas"], (
        "%s: 成分ごとの面積 Rust %s / Python %s" % (name, r["comp_areas"], p["comp_areas"]))


def test_abi_version_matches_the_header(rust):
    """第 2 実装が名乗る ABI 版が、ヘッダの版と一致する。"""
    src = (ROOT / "fullseye_abi.h").read_text(encoding="utf-8")
    import re
    mj = int(re.search(r"FULLSEYE_ABI_VERSION_MAJOR\s+(\d+)", src).group(1))
    mn = int(re.search(r"FULLSEYE_ABI_VERSION_MINOR\s+(\d+)", src).group(1))
    a, b = C.c_int32(), C.c_int32()
    assert rust.fs_abi_version(C.byref(a), C.byref(b)) == 0
    assert (a.value, b.value) == (mj, mn), (
        "Rust 実装の ABI 版 %d.%d がヘッダの %d.%d と違う" % (a.value, b.value, mj, mn))
