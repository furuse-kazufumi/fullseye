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


#: `fs_dtype_t`(契約 R-4)。このスパイクは f64 の画素しか読まない。
FS_DTYPE_F64 = 4


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
                                    C.c_int32,          # ★fs_dtype_t(契約の第 5 引数)
                                    C.c_double, C.c_double, C.POINTER(C.c_void_p)]
    lib.fs_threshold.argtypes = [C.c_void_p, C.c_double, C.c_double, C.POINTER(C.c_void_p)]
    lib.fs_region_area.argtypes = [C.c_void_p, C.POINTER(C.c_int64)]
    lib.fs_region_run_count.argtypes = [C.c_void_p, C.POINTER(C.c_int64)]
    lib.fs_connection.argtypes = [C.c_void_p, C.POINTER(C.c_void_p)]
    lib.fs_objectset_count.argtypes = [C.c_void_p, C.POINTER(C.c_int64)]
    lib.fs_objectset_region.argtypes = [C.c_void_p, C.c_int64, C.POINTER(C.c_void_p)]
    lib.fs_abi_version.argtypes = [C.POINTER(C.c_int32), C.POINTER(C.c_int32)]
    lib.fs_gauss.argtypes = [C.c_void_p, C.c_double, C.POINTER(C.c_void_p)]
    lib.fs_measure_all.argtypes = [C.c_void_p] + [C.POINTER(C.c_void_p)] * 3
    lib.fs_select_shape.argtypes = [C.c_void_p, C.c_char_p, C.c_double, C.c_double,
                                    C.POINTER(C.c_void_p)]
    lib.fs_tuple_length.argtypes = [C.c_void_p, C.POINTER(C.c_int64)]
    lib.fs_tuple_get_real.argtypes = [C.c_void_p, C.c_int64, C.POINTER(C.c_double)]
    lib.fs_debug_copy_pixels.argtypes = [C.c_void_p, C.POINTER(C.c_double), C.c_int64]
    for n in ("fs_image_release", "fs_region_release", "fs_objectset_release",
              "fs_tuple_release"):
        getattr(lib, n).argtypes = [C.c_void_p]
        getattr(lib, n).restype = None
    return lib


def _rust_run(lib, px, lo, hi, vrange):
    a = np.ascontiguousarray(px, dtype=np.float64)
    h, w = a.shape
    img = C.c_void_p()
    st = lib.fs_image_create(a.ctypes.data_as(C.c_void_p), h, w, a.strides[0],
                             FS_DTYPE_F64, vrange[0], vrange[1], C.byref(img))
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
    except (fslib.FsValueError, fslib.FsTypeError):
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


# --------------------------------------------------------------------------- #
# 残り 3 演算子 —— gauss / measure_all / select_shape
# --------------------------------------------------------------------------- #
def _rust_image(lib, px, vrange):
    a = np.ascontiguousarray(px, dtype=np.float64)
    img = C.c_void_p()
    assert lib.fs_image_create(a.ctypes.data_as(C.c_void_p), a.shape[0], a.shape[1],
                               a.strides[0], FS_DTYPE_F64,
                               vrange[0], vrange[1], C.byref(img)) == 0
    return img, a


def _rust_objs(lib, px, lo, hi, vrange=(0.0, 1.0)):
    img, _ = _rust_image(lib, px, vrange)
    reg = C.c_void_p()
    assert lib.fs_threshold(img, lo, hi, C.byref(reg)) == 0
    objs = C.c_void_p()
    assert lib.fs_connection(reg, C.byref(objs)) == 0
    return img, reg, objs


def _tuple_vals(lib, t):
    n = C.c_int64()
    lib.fs_tuple_length(t, C.byref(n))
    out = []
    for i in range(int(n.value)):
        v = C.c_double()
        lib.fs_tuple_get_real(t, i, C.byref(v))
        out.append(float(v.value))
    return out


#: 端に構造のある入力を必ず混ぜる —— 折り返しの流儀の違いは**端にしか出ない**。
GAUSS_CASES = [
    ("階段(端に構造がある)", lambda: np.tile(np.linspace(0, 1, 32), (32, 1))),
    ("市松 32x32", lambda: _checker(32)),
    ("中央の点", _one_pixel),
    ("枠(端そのものが立っている)", _frame),
    ("乱数 32x32", lambda: np.random.default_rng(0).random((32, 32))),
]


@pytest.mark.parametrize("sigma", [1.0, 2.5])
@pytest.mark.parametrize("name,make", GAUSS_CASES, ids=[c[0] for c in GAUSS_CASES])
def test_gauss_matches_the_python_oracle(rust, name, make, sigma):
    """`fs_gauss` は**端まで**一致する。

    ヘッダはカーネル半径も端の折り返し方も決めていない。Rust 側は scipy の流儀
    (`lw = int(4*sigma + 0.5)`、`mode='reflect'`)を明示的に選んだ —— numpy backend が
    既存レシピのオラクルだから。ここが食い違うなら、**決めるべきはヘッダのほう**。
    """
    px = make()
    img, a = _rust_image(rust, px, (0.0, 1.0))
    out = C.c_void_p()
    assert rust.fs_gauss(img, sigma, C.byref(out)) == 0
    buf = np.empty(a.size, dtype=np.float64)
    assert rust.fs_debug_copy_pixels(out, buf.ctypes.data_as(C.POINTER(C.c_double)),
                                     buf.size) == 0
    rust.fs_image_release(out)
    rust.fs_image_release(img)
    got = buf.reshape(a.shape)
    oracle = np.asarray(
        fslib._REGISTRY["gauss"]["numpy"](
            fslib.FImage(a, value_range=(0.0, 1.0)), sigma).pixels, dtype=np.float64)
    d = np.abs(got - oracle)
    inner = np.zeros(d.shape, bool)
    r = int(4.0 * sigma + 0.5) + 1
    inner[r:-r, r:-r] = True
    assert d.max() < 1e-5, (
        "%s sigma=%.1f: Rust と numpy が違う(端 %.3g / 内部 %.3g)—— 端だけ大きいなら "
        "折り返しの流儀、両方大きいならカーネル半径"
        % (name, sigma, d[~inner].max(), d[inner].max() if inner.any() else float("nan")))


def test_gauss_rejects_a_nonpositive_sigma(rust):
    """sigma <= 0 は両方が拒む(R-1: 失敗と「何も起きない」を分ける)。"""
    img, _ = _rust_image(rust, np.full((8, 8), 0.5), (0.0, 1.0))
    out = C.c_void_p()
    for s in (0.0, -1.0):
        assert rust.fs_gauss(img, s, C.byref(out)) != 0, "Rust が sigma=%r を受けた" % s
        with pytest.raises(Exception):
            fslib.gauss(fslib.FImage(np.full((8, 8), 0.5), value_range=(0.0, 1.0)), s)
    rust.fs_image_release(img)


def test_measure_all_matches(rust):
    """面積と重心が一致する。重心は**画素インデックス**(画素の中心が整数)。"""
    a = np.zeros((12, 12))
    a[1:4, 1:4] = 1.0      # 面積 9
    a[6:8, 2:9] = 1.0      # 面積 14
    a[9, 9] = 1.0          # 面積 1
    img, reg, objs = _rust_objs(rust, a, 0.5, 1.0)
    ta, tr, tc = C.c_void_p(), C.c_void_p(), C.c_void_p()
    assert rust.fs_measure_all(objs, C.byref(ta), C.byref(tr), C.byref(tc)) == 0
    got = sorted(zip(_tuple_vals(rust, ta), _tuple_vals(rust, tr), _tuple_vals(rust, tc)))
    for t in (ta, tr, tc):
        rust.fs_tuple_release(t)
    rust.fs_objectset_release(objs)
    rust.fs_region_release(reg)
    rust.fs_image_release(img)

    ar, ro, co = fslib.measure_all(fslib.connection(fslib.threshold(
        fslib.FImage(a, value_range=(0.0, 1.0)), 0.5, 1.0)))
    want = sorted(zip(map(float, ar), map(float, ro), map(float, co)))
    assert len(got) == len(want), "物体数 Rust %d / Python %d" % (len(got), len(want))
    for g, w in zip(got, want):
        assert all(abs(x - y) < 1e-9 for x, y in zip(g, w)), (
            "measure_all が違う Rust %s / Python %s" % (g, w))


def test_objects_come_back_in_the_declared_order(rust):
    """物体の並びは契約の一部 —— 最初の run の (row, col) 昇順(`fs_connection`)。

    `measure_all` の三つ組を**ソートせずに**突き合わせる。ソートして比べていた
    あいだ、差分ファジングは 60,000 ケース撒いても順序の欠陥を 1 件も出さなかった
    ([[feedback_observe_what_the_contract_declares]])——
    観測していない性質は、ケース数をいくら増やしても見えない。

    盤面はファザーが実際に出した反例。物体は (row=0,col=3) 面積 2 と
    (row=1,col=1) 面積 1 で、契約の昇順なら**前者が先**。`fslib` は `ndi.label` /
    `cv2` が振る走査順のラベル番号で並べていたので、逆になっていた。
    """
    a = np.array([[0.0, 0.0, 0.0, 1.0, 0.0],
                  [0.0, 1.0, 0.0, 1.0, 0.0]])
    img, reg, objs = _rust_objs(rust, a, 0.5, 1.0)
    ta, tr, tc = C.c_void_p(), C.c_void_p(), C.c_void_p()
    assert rust.fs_measure_all(objs, C.byref(ta), C.byref(tr), C.byref(tc)) == 0
    got = list(zip(_tuple_vals(rust, ta), _tuple_vals(rust, tr), _tuple_vals(rust, tc)))
    for t in (ta, tr, tc):
        rust.fs_tuple_release(t)
    rust.fs_objectset_release(objs)
    rust.fs_region_release(reg)
    rust.fs_image_release(img)

    ar, ro, co = fslib.measure_all(fslib.connection(fslib.threshold(
        fslib.FImage(a, value_range=(0.0, 1.0)), 0.5, 1.0)))
    want = list(zip(map(float, ar), map(float, ro), map(float, co)))
    assert len(got) == len(want) == 2, "物体数 Rust %d / Python %d" % (len(got), len(want))
    for i, (g, w) in enumerate(zip(got, want)):
        assert all(abs(x - y) < 1e-9 for x, y in zip(g, w)), (
            "%d 番目が Rust %s / Python %s —— 集合は同じでも**並び**が違う。"
            "呼び手は添字で引くので、指す物体が変わる" % (i, g, w))
    # 契約そのものも確かめる(2 実装が仲良く同じ間違いをしている場合を落とす)
    assert got[0][0] == 2.0 and got[1][0] == 1.0, (
        "並びが契約と違う: 面積 %s(最初の run が (0,3) の面積 2 が先)"
        % [t[0] for t in got])


@pytest.mark.parametrize("feature,vmin,vmax", [
    ("area", 5.0, 20.0), ("area", 0.0, 1.0), ("area", 0.0, 0.0),
    ("row", 0.0, 5.0), ("column", 100.0, 200.0), ("column", 0.0, 11.0),
])
def test_select_shape_matches(rust, feature, vmin, vmax):
    """区間は**両端を含む**(threshold と揃える)。並びは入力の並びを保つ。"""
    a = np.zeros((12, 12))
    a[1:4, 1:4] = 1.0
    a[6:8, 2:9] = 1.0
    a[9, 9] = 1.0
    img, reg, objs = _rust_objs(rust, a, 0.5, 1.0)
    sel = C.c_void_p()
    st = rust.fs_select_shape(objs, feature.encode(), vmin, vmax, C.byref(sel))
    assert st == 0
    cnt = C.c_int64()
    rust.fs_objectset_count(sel, C.byref(cnt))
    rust.fs_objectset_release(sel)
    rust.fs_objectset_release(objs)
    rust.fs_region_release(reg)
    rust.fs_image_release(img)

    py = fslib.select_shape(fslib.connection(fslib.threshold(
        fslib.FImage(a, value_range=(0.0, 1.0)), 0.5, 1.0)), feature, vmin, vmax)
    assert int(cnt.value) == len(py.ids), (
        "%s [%s,%s]: Rust %d 個 / Python %d 個"
        % (feature, vmin, vmax, cnt.value, len(py.ids)))


def test_select_shape_rejects_what_the_contract_calls_a_caller_error(rust):
    """逆さの区間と知らない feature —— **どちらも失敗**であって空ではない。

    2026-09-14 の測定では、逆さの区間を Rust は拒み **`fslib` は黙って 0 個を
    返していた**。`threshold` で直したのと同じ欠陥が兄弟に残っていた形
    ([[feedback_same_bug_class_recurs_check_siblings]])。
    """
    a = np.zeros((12, 12))
    a[1:4, 1:4] = 1.0
    img, reg, objs = _rust_objs(rust, a, 0.5, 1.0)
    sel = C.c_void_p()
    assert rust.fs_select_shape(objs, b"area", 20.0, 5.0, C.byref(sel)) != 0
    assert rust.fs_select_shape(objs, b"perimeter", 0.0, 1.0, C.byref(sel)) != 0
    rust.fs_objectset_release(objs)
    rust.fs_region_release(reg)
    rust.fs_image_release(img)

    py_objs = fslib.connection(fslib.threshold(
        fslib.FImage(a, value_range=(0.0, 1.0)), 0.5, 1.0))
    # ★契約では **FS_E_INVALID_ARG**(引数が定義域の外)であって FS_E_TYPE ではない。
    #   `FsValueError` を足すまでは両方 `FsTypeError` で、Rust が 1 を返すのに
    #   Python は 2 相当を投げる、という**状態コードの食い違い**が残っていた。
    with pytest.raises(fslib.FsValueError):
        fslib.select_shape(py_objs, "area", 20.0, 5.0)
    with pytest.raises(fslib.FsValueError):
        fslib.select_shape(py_objs, "perimeter", 0.0, 1.0)


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
