# -*- coding: utf-8 -*-
"""`fs_apply`(fullseye_abi.h の汎用入口)—— python 経路 / native 経路 / fail-closed。

道 1(memory `project_fullseye_multilang_abi_program` 第 3 期): cdylib に汎用入口を 1 本置き、
埋め込み CPython 経由でレジストリの全 op を呼べるようにした。ここで検査するのは 4 つ:

  1. **python 経路が Python 直呼びとビット一致**する(往復のコピーで何も変わらない)。
  2. **差分**: 契約の 5 op を `route_pref=1`(native)と `2`(python)で走らせて突き合わせる。
     契約が決めている点(閉区間 / 8 連結 / 並び / gauss の折り返し)は一致しなければならず、
     食い違ったら**隠さず落とす** —— それがこの入口を作った目的(道 3 の門)。
  3. **fail-closed**: 未知 op / 型違い / NaN / 知らないキー / 容量不足 / 別経路の強制。
  4. **来歴**: どの経路で走ったかが `info.route` に必ず出る。

作法は `test_rust_abi_parity.py` と同じ —— cargo が無ければ理由つきで SKIP、建ったのに
答えが違えば失敗。`embed` feature のビルドはこのテストを走らせている CPython と同じ版に
向ける(`PYO3_PYTHON=sys.executable`)。違う版の python3XY.dll を同じプロセスに 2 つ
起こさないための制約で、3.11 以外で走らせたときは SKIP する。
"""
from __future__ import annotations

import ctypes as C
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import fslib
import fullseye
from fullseye import abi_bridge

ROOT = Path(__file__).resolve().parents[1]
CRATE = ROOT / "rust" / "fullseye_core"
HEADER = ROOT / "fullseye_abi.h"
LIBNAME = {"win32": "fullseye_core.dll", "darwin": "libfullseye_core.dylib"}.get(
    sys.platform, "libfullseye_core.so")

FS_OK, FS_E_INVALID_ARG, FS_E_TYPE, FS_E_UNSUPPORTED = 0, 1, 2, 6
FS_E_NO_PYTHON, FS_E_UNKNOWN_OP, FS_E_BAD_PARAMS, FS_E_PY_EXCEPTION = 10, 11, 12, 13
KIND_IMAGE, KIND_REGION, KIND_OBJECTSET, KIND_TUPLE = 1, 2, 3, 4
ROUTE_AUTO, ROUTE_NATIVE, ROUTE_PYTHON = 0, 1, 2
FS_DTYPE_F64 = 4


class FsRun(C.Structure):
    _fields_ = [("row", C.c_int32), ("col_begin", C.c_int32), ("col_end", C.c_int32)]


class FsHandle(C.Structure):
    _fields_ = [("kind", C.c_int), ("ptr", C.c_void_p)]


class FsApplyInfo(C.Structure):
    _fields_ = [("route", C.c_char * 16), ("op", C.c_char * 64), ("backend", C.c_char * 32),
                ("degraded", C.c_int), ("message", C.c_char * 512)]


# --------------------------------------------------------------------------- #
# ビルド(2 種: embed あり / なし)
# --------------------------------------------------------------------------- #
_BUILD_LOG: dict[str, str] = {}


def _cargo(args: list[str], env: dict) -> tuple[bool, str]:
    try:
        r = subprocess.run(["cargo", "build", "--release", *args], cwd=str(CRATE),
                           capture_output=True, text=True, timeout=900, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return r.returncode == 0, (r.stderr or "")[-1500:]


#: ★target dir は **別に切る**。最初は `target/release`(既定)に建ててそこから直接ロードして
#: いたが、同じプロセスで後に走る `test_rust_abi_parity.py` が `cargo build --release`
#: (feature なし)で同じ DLL を書き換えようとし、ロード済みでロックされているので
#: ビルドに失敗 → **36 件が黙って SKIP** になった([[feedback_zero_findings_may_mean_never_executed]])。
#: 建てる場所を分け、ロードは tmp へのコピーから行う。
EMBED_TARGET = CRATE / "target" / "embed"


def _build_embed(dst_dir: Path) -> Path | None:
    if not CRATE.exists() or shutil.which("cargo") is None:
        _BUILD_LOG["embed"] = "cargo が無い"
        return None
    env = dict(os.environ, PYO3_PYTHON=sys.executable)
    ok, log = _cargo(["--features", "embed", "--target-dir", str(EMBED_TARGET)], env)
    _BUILD_LOG["embed"] = log
    src = EMBED_TARGET / "release" / LIBNAME
    if not (ok and src.exists()):
        return None
    dst = dst_dir / LIBNAME
    shutil.copy2(src, dst)
    return dst


def _build_plain(dst_dir: Path) -> Path | None:
    """feature off のビルド。別の target dir に建て、別名でコピーして同時ロードできるようにする。"""
    if not CRATE.exists() or shutil.which("cargo") is None:
        return None
    ok, log = _cargo(["--target-dir", str(CRATE / "target" / "no_embed")], dict(os.environ))
    _BUILD_LOG["plain"] = log
    src = CRATE / "target" / "no_embed" / "release" / LIBNAME
    if not (ok and src.exists()):
        return None
    dst = dst_dir / LIBNAME.replace("fullseye_core", "fullseye_core_noembed")
    shutil.copy2(src, dst)
    return dst


def _declare(lib: C.CDLL) -> C.CDLL:
    P = C.POINTER
    lib.fs_apply.argtypes = [C.c_char_p, P(FsHandle), C.c_int, C.c_char_p, C.c_int,
                             P(FsHandle), C.c_int, P(C.c_int), P(FsApplyInfo)]
    lib.fs_python_init.argtypes = [C.c_char_p]
    lib.fs_python_available.argtypes = [C.c_char_p, C.c_int]
    lib.fs_catalog_json.argtypes = [P(C.c_char_p)]
    lib.fs_image_create.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_int64,
                                    C.c_int32, C.c_double, C.c_double, P(C.c_void_p)]
    lib.fs_image_shape.argtypes = [C.c_void_p, P(C.c_int32), P(C.c_int32)]
    lib.fs_image_range.argtypes = [C.c_void_p, P(C.c_double), P(C.c_double)]
    lib.fs_region_area.argtypes = [C.c_void_p, P(C.c_int64)]
    lib.fs_region_run_count.argtypes = [C.c_void_p, P(C.c_int64)]
    lib.fs_region_runs.argtypes = [C.c_void_p, P(FsRun), C.c_int64, P(C.c_int64)]
    lib.fs_objectset_count.argtypes = [C.c_void_p, P(C.c_int64)]
    lib.fs_objectset_region.argtypes = [C.c_void_p, C.c_int64, P(C.c_void_p)]
    lib.fs_tuple_length.argtypes = [C.c_void_p, P(C.c_int64)]
    lib.fs_tuple_get_real.argtypes = [C.c_void_p, C.c_int64, P(C.c_double)]
    lib.fs_debug_copy_pixels.argtypes = [C.c_void_p, P(C.c_double), C.c_int64]
    for n in ("fs_image_release", "fs_region_release", "fs_objectset_release", "fs_tuple_release"):
        getattr(lib, n).argtypes = [C.c_void_p]
        getattr(lib, n).restype = None
    return lib


@pytest.fixture(scope="module")
def rust(tmp_path_factory):
    """embed ありの cdylib(python 経路が動く)。"""
    if sys.version_info[:2] != (3, 11):
        pytest.skip("このテストは CPython 3.11 で走らせる(embed ビルドをホストの版に合わせるため)")
    p = _build_embed(tmp_path_factory.mktemp("embed"))
    if p is None:
        pytest.skip("embed ビルドを建てられない: %s" % _BUILD_LOG.get("embed", "?")[-600:])
    return _declare(C.CDLL(str(p)))


@pytest.fixture(scope="module")
def rust_plain(tmp_path_factory):
    """embed なしの cdylib(python 経路は FS_E_NO_PYTHON を返すはず)。"""
    p = _build_plain(tmp_path_factory.mktemp("noembed"))
    if p is None:
        pytest.skip("feature off のビルドを建てられない: %s" % _BUILD_LOG.get("plain", "?")[-600:])
    return _declare(C.CDLL(str(p)))


# --------------------------------------------------------------------------- #
# ハンドルの取り回し
# --------------------------------------------------------------------------- #
class Session:
    """作ったハンドルを覚えておいて最後に全部 release する(R-5)。"""

    def __init__(self, lib):
        self.lib = lib
        self.owned: list[FsHandle] = []

    def image(self, px, vrange=(0.0, 1.0)) -> FsHandle:
        a = np.ascontiguousarray(px, dtype=np.float64)
        h = C.c_void_p()
        st = self.lib.fs_image_create(a.ctypes.data_as(C.c_void_p), a.shape[0], a.shape[1],
                                      a.strides[0], FS_DTYPE_F64, vrange[0], vrange[1], C.byref(h))
        assert st == FS_OK, "fs_image_create -> %d" % st
        hd = FsHandle(KIND_IMAGE, h.value)
        self.owned.append(hd)
        return hd

    def apply(self, op, handles, params, route, out_cap=4):
        ins = (FsHandle * max(1, len(handles)))(*handles)
        outs = (FsHandle * max(1, out_cap))()
        n = C.c_int()
        info = FsApplyInfo()
        st = self.lib.fs_apply(op.encode(), ins, len(handles),
                               None if params is None else params.encode("utf-8"),
                               route, outs, out_cap, C.byref(n), C.byref(info))
        got = [outs[i] for i in range(n.value)] if st == FS_OK else []
        self.owned.extend(got)
        return st, got, info

    def pixels(self, h: FsHandle) -> np.ndarray:
        assert h.kind == KIND_IMAGE
        hh, ww = C.c_int32(), C.c_int32()
        assert self.lib.fs_image_shape(h.ptr, C.byref(hh), C.byref(ww)) == FS_OK
        buf = np.empty(hh.value * ww.value, dtype=np.float64)
        assert self.lib.fs_debug_copy_pixels(h.ptr, buf.ctypes.data_as(C.POINTER(C.c_double)),
                                             buf.size) == FS_OK
        return buf.reshape(hh.value, ww.value)

    def runs(self, ptr) -> np.ndarray:
        n = C.c_int64()
        assert self.lib.fs_region_run_count(ptr, C.byref(n)) == FS_OK
        buf = (FsRun * max(1, n.value))()
        w = C.c_int64()
        assert self.lib.fs_region_runs(ptr, buf, max(1, n.value), C.byref(w)) == FS_OK
        return np.array([(r.row, r.col_begin, r.col_end) for r in buf[:n.value]],
                        dtype=np.int32).reshape(-1, 3)

    def region(self, h: FsHandle) -> np.ndarray:
        assert h.kind == KIND_REGION
        return self.runs(h.ptr)

    def objects(self, h: FsHandle) -> list[np.ndarray]:
        assert h.kind == KIND_OBJECTSET
        n = C.c_int64()
        assert self.lib.fs_objectset_count(h.ptr, C.byref(n)) == FS_OK
        out = []
        for i in range(n.value):
            sub = C.c_void_p()
            assert self.lib.fs_objectset_region(h.ptr, i, C.byref(sub)) == FS_OK
            out.append(self.runs(sub))
            self.lib.fs_region_release(sub)
        return out

    def tuple(self, h: FsHandle) -> list[float]:
        assert h.kind == KIND_TUPLE
        n = C.c_int64()
        assert self.lib.fs_tuple_length(h.ptr, C.byref(n)) == FS_OK
        vals = []
        for i in range(n.value):
            v = C.c_double()
            assert self.lib.fs_tuple_get_real(h.ptr, i, C.byref(v)) == FS_OK
            vals.append(v.value)
        return vals

    def close(self):
        rel = {KIND_IMAGE: "fs_image_release", KIND_REGION: "fs_region_release",
               KIND_OBJECTSET: "fs_objectset_release", KIND_TUPLE: "fs_tuple_release"}
        for h in self.owned:
            if h.ptr:
                getattr(self.lib, rel[h.kind])(h.ptr)
        self.owned.clear()


@pytest.fixture
def s(rust):
    sess = Session(rust)
    yield sess
    sess.close()


def _msg(info: FsApplyInfo) -> str:
    return info.message.decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# 探針(構造つき。乱数だけでは端も連結性も見えない)
# --------------------------------------------------------------------------- #
def _checker(n=8):
    return (np.indices((n, n)).sum(axis=0) % 2).astype(np.float64)


def _gradient(n=32):
    return np.tile(np.linspace(0.0, 1.0, n), (n, 1))


def _frame(n=9):
    a = np.zeros((n, n)); a[0, :] = 1.0; a[:, -1] = 1.0; a[-1, :] = 1.0
    return a


def _two_squares():
    a = np.zeros((9, 9)); a[1:4, 1:4] = 1.0; a[4:7, 4:7] = 1.0
    return a


def _stripes():
    a = np.zeros((7, 7)); a[::2, :] = 1.0
    return a


PROBES = [("市松8x8", _checker), ("勾配32x32", _gradient), ("枠", _frame),
          ("斜めに接する2つの正方形", _two_squares), ("横縞", _stripes),
          ("乱数16x16", lambda: np.random.default_rng(0).random((16, 16)))]


def _nontrivial(a: np.ndarray, what: str):
    """「走った」≠「意味のある出力」: 要素数と非定数を別に検査する。"""
    assert a.size > 1, "%s: 要素が %d 個しか無い" % (what, a.size)
    assert np.isfinite(a).all(), "%s: 非有限が混じる" % what
    assert a.max() > a.min(), "%s: 定数になっている(min = max = %g)" % (what, a.min())


# --------------------------------------------------------------------------- #
# 1. ヘッダとの機械照合(数字・名前・表)
# --------------------------------------------------------------------------- #
def _header_status_codes() -> dict[str, int]:
    src = HEADER.read_text(encoding="utf-8")
    body = re.search(r"typedef enum fs_status\s*\{(.*?)\}", src, re.S).group(1)
    return {m.group(1): int(m.group(2)) for m in re.finditer(r"\b(FS_[A-Z_]+)\s*=\s*(\d+)", body)}


def test_status_codes_agree_across_header_rust_and_bridge():
    """状態コードの**番号**が 3 か所で一致する。

    ★これが無かったせいで、Rust 側は `FS_E_UNSUPPORTED = 4`(ヘッダでは FS_E_RANGE の番号)を
    2026-09-14 から返し続けていた。差分テストは「非ゼロを返した」までしか見ていなかった。
    `fslib` 側で同じ日に見つけた「状態コードの取り違え」と同じ型が、こちら側にも在った。
    """
    hdr = _header_status_codes()
    assert len(hdr) >= 14, "ヘッダの状態コードを読めていない(%d 件)" % len(hdr)
    rs = {m.group(1): int(m.group(2)) for m in re.finditer(
        r"pub const (FS_[A-Z_]+): c_int = (\d+);", (CRATE / "src" / "lib.rs").read_text(encoding="utf-8"))}
    bad = {n: (hdr[n], rs[n]) for n in set(hdr) & set(rs) if hdr[n] != rs[n]}
    assert not bad, "ヘッダと Rust で状態コードの番号が違う: %s" % bad
    missing = sorted(set(hdr) - set(rs))
    assert not missing, "ヘッダにあって Rust に無い状態コード: %s" % missing
    for name, val in hdr.items():
        assert getattr(abi_bridge, name) == val, "abi_bridge.%s = %r(ヘッダは %d)" % (
            name, getattr(abi_bridge, name, None), val)


def test_contract_ops_are_the_header_tags():
    """ブリッジが「契約」として扱う op = ヘッダの `@fslib` タグの集合(増減したら落ちる)。"""
    src = HEADER.read_text(encoding="utf-8")
    tags = set(re.findall(r"@fslib\s+(\w+)\b", src))
    assert tags == set(abi_bridge.CONTRACT_OPS), "ヘッダ %s / ブリッジ %s" % (
        sorted(tags), sorted(abi_bridge.CONTRACT_OPS))
    # Rust の native 表も同じ集合
    rs = (CRATE / "src" / "apply.rs").read_text(encoding="utf-8")
    m = re.search(r"NATIVE_OPS: \[&str; \d+\] = \[(.*?)\];", rs, re.S)
    native = set(re.findall(r'"(\w+)"', m.group(1)))
    assert native == tags, "Rust NATIVE_OPS %s / ヘッダ %s" % (sorted(native), sorted(tags))


def test_native_route_reads_exactly_the_parameters_python_declares():
    """パラメータの正本は Python(カタログ)。Rust の native 経路が読むキーは、その表と
    **名前の集合で一致**しなければならない —— 二重管理を許した瞬間に黙ってずれる。"""
    rs = (CRATE / "src" / "apply.rs").read_text(encoding="utf-8")
    rust_keys: dict[str, set] = {}
    for m in re.finditer(r'"(\w+)" => \{\s*only_keys\(op, p, &\[(.*?)\]\)', rs, re.S):
        rust_keys[m.group(1)] = set(re.findall(r'"(\w+)"', m.group(2)))
    assert set(rust_keys) == set(abi_bridge.CONTRACT_OPS), sorted(rust_keys)
    cat = {o["name"]: o for o in abi_bridge.catalog()["ops"] if o["tier"] == "contract"}
    for name in abi_bridge.CONTRACT_OPS:
        py = {p["name"] for p in cat[name]["params"]}
        assert py == rust_keys[name], "%s: Python %s / Rust %s" % (name, sorted(py), sorted(rust_keys[name]))
        assert all(p["required"] for p in cat[name]["params"]), (
            "%s に既定値つきの引数が増えた —— native 経路は既定値を解決しないので設計を見直すこと" % name)


# --------------------------------------------------------------------------- #
# 2. python 経路 = Python 直呼び(ビット一致)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name,make", [("市松", _checker), ("勾配", _gradient)])
def test_registry_op_through_fs_apply_is_bit_identical_to_fullseye_apply(s, name, make):
    """`gaussian`(レジストリ、σ = 0.3 + 2.7a → a=0.63 で σ≈2)を fs_apply で呼んだ結果が
    `fullseye.apply` 直呼びと**ビット一致**する。"""
    a = make()
    img = s.image(a)
    st, outs, info = s.apply("gaussian", [img], '{"a": 0.63}', ROUTE_AUTO)
    assert st == FS_OK, _msg(info)
    assert info.route == b"python" and info.degraded == 0, (info.route, info.degraded, _msg(info))
    assert len(outs) == 1 and outs[0].kind == KIND_IMAGE
    got = s.pixels(outs[0])
    want = fullseye.apply(a, "gaussian", 0.63, 0.5)
    _nontrivial(got, "gaussian(%s)" % name)
    assert got.shape == want.shape
    assert np.array_equal(got, want), "%s: 最大差 %g" % (name, np.abs(got - want).max())
    assert b"a=0.63(float)" in info.message, _msg(info)


@pytest.mark.parametrize("name,make", [("市松", _checker), ("勾配", _gradient)])
def test_contract_gauss_through_python_route_is_bit_identical_to_fslib(s, name, make):
    a = make()
    st, outs, info = s.apply("gauss", [s.image(a)], '{"sigma": 2}', ROUTE_PYTHON)
    assert st == FS_OK, _msg(info)
    assert info.route == b"python"
    assert info.backend in (b"numpy", b"cv2"), info.backend
    got = s.pixels(outs[0])
    want = fslib.gauss(fslib.FImage(a, value_range=(0.0, 1.0)), 2).pixels
    _nontrivial(got, "gauss(%s)" % name)
    assert np.array_equal(got, want), "%s: 最大差 %g" % (name, np.abs(got - want).max())


# --------------------------------------------------------------------------- #
# 3. 差分: native(route 1)vs python(route 2)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name,make", PROBES, ids=[p[0] for p in PROBES])
@pytest.mark.parametrize("sigma", [1.0, 2.5])
def test_gauss_native_and_python_agree_to_the_edge(s, name, make, sigma):
    """契約: 半径 4σ、`(d c b a | a b c d)` の折り返し。**端まで**比べる(端だけ違うなら折り返し、
    全体が違うなら半径 —— 2026-09-14 に 13% の食い違いが出た場所)。"""
    a = make()
    img = s.image(a)
    st1, o1, i1 = s.apply("gauss", [img], '{"sigma": %r}' % sigma, ROUTE_NATIVE)
    st2, o2, i2 = s.apply("gauss", [img], '{"sigma": %r}' % sigma, ROUTE_PYTHON)
    assert (st1, st2) == (FS_OK, FS_OK), (_msg(i1), _msg(i2))
    assert (i1.route, i2.route) == (b"native", b"python")
    p1, p2 = s.pixels(o1[0]), s.pixels(o2[0])
    d = np.abs(p1 - p2)
    r = int(4.0 * sigma + 0.5) + 1
    inner = np.zeros(d.shape, bool)
    inner[r:-r, r:-r] = True
    assert d.max() < 1e-5, (
        "%s σ=%g: native と python(%s)が違う: 端 %.3g / 内部 %.3g"
        % (name, sigma, i2.backend.decode(), d[~inner].max(),
           d[inner].max() if inner.any() else float("nan")))


@pytest.mark.parametrize("name,make", PROBES, ids=[p[0] for p in PROBES])
@pytest.mark.parametrize("lo,hi", [(0.5, 1.0), (0.5, 0.5), (0.0, 1.0)])
def test_threshold_native_and_python_agree_run_for_run(s, name, make, lo, hi):
    """契約: 閉区間。run の並びまで一致する(R-2 の唯一の観測窓)。"""
    a = make()
    img = s.image(a)
    params = '{"lo": %r, "hi": %r}' % (lo, hi)
    st1, o1, i1 = s.apply("threshold", [img], params, ROUTE_NATIVE)
    st2, o2, i2 = s.apply("threshold", [img], params, ROUTE_PYTHON)
    assert (st1, st2) == (FS_OK, FS_OK), (_msg(i1), _msg(i2))
    r1, r2 = s.region(o1[0]), s.region(o2[0])
    assert r1.shape == r2.shape and np.array_equal(r1, r2), (
        "%s [%g,%g]: run が違う native %d 本 / python %d 本" % (name, lo, hi, len(r1), len(r2)))


@pytest.mark.parametrize("name,make", PROBES, ids=[p[0] for p in PROBES])
def test_connection_measure_select_native_and_python_agree(s, name, make):
    """契約: 8 連結 / 最初の run の (row, col) 昇順 / 面積と重心 / 閉区間の select。
    両経路とも fs_apply で走らせ、**並びをソートせずに**突き合わせる。"""
    a = make()
    img = s.image(a)
    regs = {}
    for route in (ROUTE_NATIVE, ROUTE_PYTHON):
        st, o, i = s.apply("threshold", [img], '{"lo": 0.5, "hi": 1.0}', route)
        assert st == FS_OK, _msg(i)
        st, o, i = s.apply("connection", [o[0]], None, route)
        assert st == FS_OK, _msg(i)
        objs = o[0]
        st, t, i = s.apply("measure_all", [objs], "{}", route)
        assert st == FS_OK and len(t) == 3, (_msg(i), len(t))
        st, sel, i = s.apply("select_shape", [objs], '{"feature": "area", "vmin": 2, "vmax": 20}', route)
        assert st == FS_OK, _msg(i)
        regs[route] = (s.objects(objs), [s.tuple(x) for x in t], s.objects(sel[0]))
    (on, tn, sn), (op_, tp, sp) = regs[ROUTE_NATIVE], regs[ROUTE_PYTHON]
    assert len(on) == len(op_), "%s: 物体数 native %d / python %d(4/8 連結?)" % (name, len(on), len(op_))
    for k, (x, y) in enumerate(zip(on, op_)):
        assert np.array_equal(x, y), "%s: %d 番目の物体の run が違う(並びか連結性)" % (name, k)
    for label, x, y in zip(("area", "row", "column"), tn, tp):
        assert len(x) == len(y) and np.allclose(x, y, atol=1e-9), "%s: %s が違う %s / %s" % (name, label, x, y)
    assert len(sn) == len(sp), "%s: select_shape の個数 native %d / python %d" % (name, len(sn), len(sp))


def test_inverted_intervals_are_refused_with_the_same_code_on_both_routes(s):
    """R-1: 逆さの区間は「空」ではなく **FS_E_INVALID_ARG**。両経路で同じ番号。"""
    img = s.image(_checker())
    for route in (ROUTE_NATIVE, ROUTE_PYTHON):
        st, o, i = s.apply("threshold", [img], '{"lo": 0.8, "hi": 0.2}', route)
        assert st == FS_E_INVALID_ARG, (route, st, _msg(i))
        assert not o
    st, o, i = s.apply("threshold", [img], '{"lo": 0.5, "hi": 1.0}', ROUTE_NATIVE)
    st, o, i = s.apply("connection", [o[0]], None, ROUTE_NATIVE)
    for route in (ROUTE_NATIVE, ROUTE_PYTHON):
        st, sel, i = s.apply("select_shape", [o[0]], '{"feature": "area", "vmin": 9, "vmax": 1}', route)
        assert st == FS_E_INVALID_ARG, (route, st, _msg(i))
        st, sel, i = s.apply("select_shape", [o[0]], '{"feature": "perimeter", "vmin": 0, "vmax": 1}', route)
        assert st == FS_E_INVALID_ARG, (route, st, _msg(i))


# --------------------------------------------------------------------------- #
# 4. fail-closed
# --------------------------------------------------------------------------- #
def test_unknown_op_is_refused_with_a_reason(s):
    st, o, i = s.apply("no_such_operator_xyz", [s.image(_checker())], "{}", ROUTE_AUTO)
    assert st == FS_E_UNKNOWN_OP and not o
    assert "no_such_operator_xyz" in _msg(i)
    assert i.route == b"python"          # 契約に無い名前は python 経路で答えを出す


@pytest.mark.parametrize("route", [ROUTE_NATIVE, ROUTE_PYTHON])
@pytest.mark.parametrize("params", ['{"sigma": "abc"}', '{"sigma": NaN}', '{"sigma": Infinity}',
                                    '{"sigma": 1, "extra": 2}', '{}', '[1, 2]', '{"sigma": 1,}'])
def test_bad_params_are_refused_on_both_routes(s, route, params):
    st, o, i = s.apply("gauss", [s.image(_checker())], params, route)
    assert st == FS_E_BAD_PARAMS, (route, params, st, _msg(i))
    assert not o and _msg(i), "拒否に理由が無い"


def test_int_and_float_are_kept_apart_on_the_way_to_python(s):
    """`2` は int、`2.0` は float として Python に届く(message に型が出る)。結果は同じ画素。"""
    img = s.image(_gradient())
    st_i, o_i, i_i = s.apply("gauss", [img], '{"sigma": 2}', ROUTE_PYTHON)
    st_f, o_f, i_f = s.apply("gauss", [img], '{"sigma": 2.0}', ROUTE_PYTHON)
    assert (st_i, st_f) == (FS_OK, FS_OK)
    assert b"sigma=2(int)" in i_i.message and b"sigma=2.0(float)" in i_f.message, (
        _msg(i_i), _msg(i_f))
    assert np.array_equal(s.pixels(o_i[0]), s.pixels(o_f[0]))
    # ブリッジ単体でも同じ(往復で型が化けていないことの直接の観測)
    assert type(abi_bridge.validate("gauss", '{"sigma": 2}')["sigma"]) is int
    assert type(abi_bridge.validate("gauss", '{"sigma": 2.0}')["sigma"]) is float


def test_forcing_native_on_a_registry_op_is_unsupported_not_silent(s):
    st, o, i = s.apply("gaussian", [s.image(_checker())], "{}", ROUTE_NATIVE)
    assert st == FS_E_UNSUPPORTED and not o and "gaussian" in _msg(i)
    st, o, i = s.apply("gauss", [s.image(_checker())], '{"sigma": 1}', 3)
    assert st == FS_E_INVALID_ARG and "route_pref" in _msg(i)


def test_sort_mismatch_is_a_type_error_on_the_python_route(s):
    """MCP と同じ立場: 画像 op に region を渡したら走らせない(黙って倒さない)。"""
    st, o, i = s.apply("threshold", [s.image(_checker())], '{"lo": 0.5, "hi": 1.0}', ROUTE_NATIVE)
    st, o, i = s.apply("gaussian", [o[0]], "{}", ROUTE_PYTHON)
    assert st == FS_E_TYPE and "gaussian" in _msg(i), (st, _msg(i))
    st, o, i = s.apply("gauss", [s.image(_checker()), s.image(_checker())], '{"sigma": 1}', ROUTE_NATIVE)
    assert st == FS_E_INVALID_ARG


def test_too_small_output_buffer_reports_the_required_count(s):
    st, o, i = s.apply("threshold", [s.image(_checker())], '{"lo": 0.5, "hi": 1.0}', ROUTE_NATIVE)
    st, o, i = s.apply("connection", [o[0]], None, ROUTE_NATIVE)
    objs = o[0]
    ins = (FsHandle * 1)(objs)
    outs = (FsHandle * 1)()
    n = C.c_int()
    info = FsApplyInfo()
    st = s.lib.fs_apply(b"measure_all", ins, 1, b"{}", ROUTE_NATIVE, outs, 1, C.byref(n), C.byref(info))
    assert st == FS_E_INVALID_ARG and n.value == 3, (st, n.value, _msg(info))
    assert outs[0].ptr is None, "容量不足なのにハンドルを書いた(所有権が漏れる)"


def test_route_is_reported_on_every_return(s):
    img = s.image(_checker())
    cases = [("gauss", '{"sigma": 1}', ROUTE_AUTO, b"native"),
             ("gauss", '{"sigma": 1}', ROUTE_PYTHON, b"python"),
             ("gaussian", '{"a": 0.5}', ROUTE_AUTO, b"python"),
             ("gaussian", '{"a": 5}', ROUTE_AUTO, b"python"),        # 拒否でも経路は出る
             ("gauss", '{"sigma": NaN}', ROUTE_AUTO, b"")]           # 走る前に拒否 = 空
    for op, params, route, want in cases:
        st, o, i = s.apply(op, [img], params, route)
        assert i.route == want, (op, params, route, i.route, _msg(i))
        assert i.op == op.encode()


def test_python_available_and_catalog(s):
    why = C.create_string_buffer(512)
    assert s.lib.fs_python_available(why, 512) == FS_OK, why.value
    p = C.c_char_p()
    assert s.lib.fs_catalog_json(C.byref(p)) == FS_OK
    cat = json.loads(p.value.decode("utf-8"))
    names = {o["name"]: o for o in cat["ops"]}
    assert cat["n_ops"] >= 900 and cat["n_native"] == 5, (cat["n_ops"], cat["n_native"])
    assert names["gauss"]["routes"] == ["native", "python"]
    assert names["gaussian"]["routes"] == ["python"]
    knobs = {q["name"]: q for q in names["gaussian"]["params"]}
    assert knobs["a"]["default"] == 0.5 and knobs["a"]["minimum"] == 0.0 and knobs["a"]["maximum"] == 1.0
    assert {"a", "b", "allow_degraded"} == set(knobs)


def test_build_without_embed_fails_closed_but_keeps_the_native_route(rust_plain):
    """feature off: python 経路は **FS_E_NO_PYTHON + 理由**、native 経路はそのまま動く。"""
    sess = Session(rust_plain)
    try:
        why = C.create_string_buffer(512)
        assert rust_plain.fs_python_available(why, 512) == FS_E_NO_PYTHON
        assert b"embed" in why.value, why.value
        img = sess.image(_checker())
        st, o, i = sess.apply("gaussian", [img], '{"a": 0.5}', ROUTE_AUTO)
        assert st == FS_E_NO_PYTHON and not o and b"embed" in i.message, (st, _msg(i))
        assert i.route == b"python"
        st, o, i = sess.apply("gauss", [img], '{"sigma": 1}', ROUTE_AUTO)
        assert st == FS_OK and i.route == b"native", (st, _msg(i))
        _nontrivial(sess.pixels(o[0]), "gauss(no embed)")
        p = C.c_char_p()
        assert rust_plain.fs_catalog_json(C.byref(p)) == FS_E_NO_PYTHON and p.value is None
    finally:
        sess.close()


# --------------------------------------------------------------------------- #
# 5. C から呼ぶ(本当の埋め込み経路: ホストは Python ではない)
# --------------------------------------------------------------------------- #
def test_the_c_example_runs_the_python_route_from_a_non_python_host(rust, tmp_path):
    """ctypes からの呼び出しではホストが既に CPython なので、`Py_InitializeFromConfig` は
    走らない。C の見本を建てて別プロセスで走らせると、home の探索と解釈系の起動と
    `fullseye.abi_bridge` の import が**初めて**検査される。clang が無ければ SKIP。"""
    cc = shutil.which("clang")
    if cc is None:
        pytest.skip("clang が無い —— 建たなかったことを「通った」と混ぜない")
    implib = EMBED_TARGET / "release" / "fullseye_core.dll.lib"
    if sys.platform != "win32" or not implib.exists():
        pytest.skip("Windows の import library が無い(%s)" % implib)
    exe = tmp_path / "fs_example.exe"
    r = subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-I", str(ROOT),
                        str(CRATE / "examples" / "c" / "main.c"), str(implib), "-o", str(exe)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, "C の見本が建たない:\n%s" % (r.stderr or r.stdout)[:2000]
    shutil.copy2(EMBED_TARGET / "release" / LIBNAME, tmp_path / LIBNAME)
    env = dict(os.environ, FULLSEYE_ROOT=str(ROOT))
    # python3XY.dll は OS の DLL 探索で解決される(静的 import)。この解釈系の dir を PATH に足す。
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")
    r = subprocess.run([str(exe)], capture_output=True, timeout=300, env=env, cwd=str(tmp_path))
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    assert r.returncode == 0, "C の見本が失敗した(rc=%d):\n%s" % (r.returncode, out[:2000])
    assert "契約どおり: 8x8 の市松は 8 連結で 1 個" in out, out
    assert "fs_apply" in out and "route=python" in out, out
    assert "route=native" in out, out
