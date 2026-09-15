# -*- coding: utf-8 -*-
"""`fs_apply` の python 経路を **wheel から** 通す門(配布物の側で数える)。

`fullseye_abi.h` の汎用入口 `fs_apply` は、ネイティブ実装の無い op を埋め込み CPython →
`fullseye.abi_bridge` に回す。そのブリッジは checkout のテスト(`tests/test_abi_apply.py`)
では緑でも、**wheel に入っていなければ** `pip install fullseye` した環境からは
`No module named 'fullseye.abi_bridge'` で止まる —— 2026-09-15 に実際に踏んだ形
(site-packages の 0.1.11 wheel に abi_bridge.py が無く、checkout を `FULLSEYE_ROOT` で
指すまで C の見本が動かなかった)。門は事故の起きる場所に立てる
([[feedback_gate_must_stand_where_the_accident_happens]])ので、ここでは

1. `tests/test_mcp_wheel.py` と同じ流儀で wheel を建て、別 venv に **wheel だけ**
   (+ numpy / scipy)入れ(fixture は同じものを import して使い回す)、
2. **リポジトリの外の cwd**、`FULLSEYE_ROOT` 無しで、
3. (a) `fullseye.abi_bridge` が **venv の site-packages から** import でき、本体の大きさが
   checkout の `fullseye/abi_bridge.py` と一致すること(0 バイトの「在る」は通さない)、
   (b) `abi_bridge.apply("gaussian", …)`(レジストリ)と `apply("gauss", …)`(契約)が
   **意味のある出力**(要素数・非定数・有限・入力から変化)を返し、同じ venv の
   `fullseye.apply` 直呼びと**ビット一致**すること、未知 op / 知らないキーは状態コードで
   拒むこと、`catalog_json()` が契約 5 + レジストリを数えること、
   (c) **cdylib 経由**: `rust/fullseye_core/target/embed` の embed ビルドを ctypes で
   venv の python に読み込み、`fs_apply(route_pref=python)` が wheel のブリッジまで届いて
   (a)(b) と同じ答えを返し、`info.route` が "python"、`fs_catalog_json` がブリッジの
   `catalog_json()` と文字列ごと一致すること。native 経路(`gauss`, route=native)も
   同じプロセスで通す。

**cdylib の門が「wheel を入れた venv」を使えるのは、ホストが CPython だから**(ctypes)。
`embed.rs` の `init()` は `Py_IsInitialized()` が真なら解釈系を起こさず、ホストのそれ
(= venv、sys.path に wheel の site-packages)をそのまま使う。ホストが C / C# / Lua の
ときは `FULLSEYE_PYTHON_HOME`(`fs_python_init(python_home)`)で決まるのは `PyConfig.home`
= **インストール本体**(Windows では `python311.dll` を持つ dir でなければ拒む)であって、
venv(`pyvenv.cfg` + `Scripts/python.exe` だけ)は指せない —— つまり C ホストからは
「wheel を入れた venv」を選ぶ設計になっていない(base の site-packages に pip install
するか、`FULLSEYE_ROOT` で checkout を指す)。だから C ホスト × venv の組は**この門の
対象外**で、ここで通すのは ctypes ホスト × venv までである(理由は本 docstring に残す)。

重い(wheel の build 1〜2 分 + venv)ので **opt-in**: ``FULLSEYE_WHEEL_GATE=1``。
CI では core-minimal ジョブが建てた wheel と venv を ``FULLSEYE_WHEEL_PYTHON`` で使い回す。
embed の cdylib は `target/embed` に在ればそれを使い、無ければ cargo で建て(数分)、
cargo も無ければ (c) だけ理由つきで SKIP する(-ra で見える)。手元では::

    $env:FULLSEYE_WHEEL_GATE = "1"; py -3.11 -m pytest tests/test_abi_wheel.py -q -ra
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

# wheel を建てて venv に入れる fixture(session scope)と転送のヘルパは MCP の門と共有する
from test_mcp_wheel import ROOT, _clean_env, _run, outside, wheel_python  # noqa: F401

GATE = os.environ.get("FULLSEYE_WHEEL_GATE") == "1"

pytestmark = pytest.mark.skipif(
    not GATE, reason="FULLSEYE_WHEEL_GATE=1 で有効(wheel を建てて別 venv に入れる。数分かかる)")

CRATE = os.path.join(ROOT, "rust", "fullseye_core")
EMBED_TARGET = os.path.join(CRATE, "target", "embed")
LIBNAME = {"win32": "fullseye_core.dll", "darwin": "libfullseye_core.dylib"}.get(
    sys.platform, "libfullseye_core.so")

FS_OK, FS_E_UNKNOWN_OP, FS_E_BAD_PARAMS = 0, 11, 12


def _env() -> dict:
    """リポジトリも checkout の指定も見えない環境。`FULLSEYE_ROOT` が残っていると
    embed.rs がそれを sys.path の先頭に入れ、wheel の欠落が隠れる。"""
    env = _clean_env()
    for k in ("FULLSEYE_ROOT", "FULLSEYE_PYTHON_HOME"):
        env.pop(k, None)
    return env


#: venv の python で走らせる探針。**fullseye を import するのは venv の側**(この検査は
#: 配布物に立つ)。`bridge` は Python 経路だけ、`cdylib` はそれに加えて ctypes で DLL を
#: 読み、`fs_apply` を往復する。結果は 1 行の JSON で返す(数値で突き合わせる)。
_PROBE = r'''
import ctypes as C, json, os, sys
import numpy as np

mode, libpath = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
out = {"cwd": os.getcwd(), "FULLSEYE_ROOT": os.environ.get("FULLSEYE_ROOT")}

import fullseye
from fullseye import abi_bridge as B
out["fullseye_file"] = fullseye.__file__
out["bridge_file"] = B.__file__

# 構造のある探針(乱数だけでは端も平滑化の効きも見えない): 勾配 + 暗い正方形
img = np.tile(np.linspace(0.0, 1.0, 32), (32, 1))
img[8:24, 8:24] = 0.0
img = np.ascontiguousarray(img)
handle = {"kind": "image", "h": 32, "w": 32, "lo": 0.0, "hi": 1.0, "dtype": 4,
          "pixels": img.tobytes()}

def stats(px):
    return {"size": int(px.size), "finite": bool(np.isfinite(px).all()), "min": float(px.min()),
            "max": float(px.max()), "n_changed": int((px != img).sum())}

r = B.apply("gaussian", [handle], '{"a": 0.5}')
out["gaussian"] = {"status": r["status"], "tier": r.get("tier"), "backend": r["backend"],
                   "message": r["message"][:120], "n_out": len(r["outputs"])}
gauss_px = None
if r["status"] == 0:
    o = r["outputs"][0]
    gauss_px = np.frombuffer(o["pixels"], dtype=np.float64).reshape(o["h"], o["w"])
    out["gaussian"].update(kind=o["kind"], h=o["h"], w=o["w"], **stats(gauss_px))
    direct = fullseye.apply(img, "gaussian", 0.5, 0.5)
    out["gaussian"]["bit_identical_to_direct_call"] = bool(np.array_equal(gauss_px, direct))

r = B.apply("gauss", [handle], '{"sigma": 1.5}')
out["gauss"] = {"status": r["status"], "tier": r.get("tier"), "backend": r["backend"],
                "message": r["message"][:120], "n_out": len(r["outputs"])}
if r["status"] == 0:
    o = r["outputs"][0]
    px = np.frombuffer(o["pixels"], dtype=np.float64).reshape(o["h"], o["w"])
    out["gauss"].update(kind=o["kind"], h=o["h"], w=o["w"], **stats(px))

out["unknown_op"] = B.apply("no_such_op_zz", [handle], "{}")["status"]
out["bad_param"] = B.apply("gaussian", [handle], '{"zzz": 1}')["status"]

cat_s = B.catalog_json()
cat = json.loads(cat_s)
names = [o["name"] for o in cat["ops"]]
dup = sorted({n for n in names if names.count(n) > 1})
out["catalog"] = {"n_ops": cat["n_ops"], "n_rows": len(names), "n_unique": len(set(names)),
                  "duplicates": dup, "n_native": cat["n_native"], "chars": len(cat_s),
                  "has": {n: (n in names) for n in ("gauss", "threshold", "connection",
                                                    "measure_all", "select_shape",
                                                    "gaussian", "otsu", "sobel_amp")}}

if mode == "cdylib":
    class FsHandle(C.Structure):
        _fields_ = [("kind", C.c_int), ("ptr", C.c_void_p)]

    class FsApplyInfo(C.Structure):
        _fields_ = [("route", C.c_char * 16), ("op", C.c_char * 64), ("backend", C.c_char * 32),
                    ("degraded", C.c_int), ("message", C.c_char * 512)]

    P = C.POINTER
    lib = C.CDLL(libpath)
    lib.fs_apply.argtypes = [C.c_char_p, P(FsHandle), C.c_int, C.c_char_p, C.c_int,
                             P(FsHandle), C.c_int, P(C.c_int), P(FsApplyInfo)]
    lib.fs_python_available.argtypes = [C.c_char_p, C.c_int]
    lib.fs_catalog_json.argtypes = [P(C.c_char_p)]
    lib.fs_image_create.argtypes = [C.c_void_p, C.c_int32, C.c_int32, C.c_int64,
                                    C.c_int32, C.c_double, C.c_double, P(C.c_void_p)]
    lib.fs_image_shape.argtypes = [C.c_void_p, P(C.c_int32), P(C.c_int32)]
    lib.fs_debug_copy_pixels.argtypes = [C.c_void_p, P(C.c_double), C.c_int64]
    lib.fs_image_release.argtypes = [C.c_void_p]
    lib.fs_image_release.restype = None

    why = C.create_string_buffer(1024)
    out["python_available"] = {"status": lib.fs_python_available(why, 1024),
                               "why": why.value.decode("utf-8", "replace")}

    h = C.c_void_p()
    st = lib.fs_image_create(img.ctypes.data_as(C.c_void_p), 32, 32, img.strides[0], 4,
                             0.0, 1.0, C.byref(h))
    out["image_create"] = st
    owned = [h.value]

    def call(op, params, route):
        ins = (FsHandle * 1)(FsHandle(1, h.value))
        outs = (FsHandle * 4)()
        n = C.c_int()
        info = FsApplyInfo()
        st = lib.fs_apply(op.encode(), ins, 1, params.encode(), route, outs, 4,
                          C.byref(n), C.byref(info))
        rec = {"status": st, "route": info.route.decode(), "backend": info.backend.decode(),
               "degraded": info.degraded, "message": info.message.decode("utf-8", "replace")[:120],
               "n_out": n.value if st == 0 else None}
        if st == 0 and n.value >= 1 and outs[0].kind == 1:
            owned.append(outs[0].ptr)
            hh, ww = C.c_int32(), C.c_int32()
            lib.fs_image_shape(outs[0].ptr, C.byref(hh), C.byref(ww))
            buf = np.empty(hh.value * ww.value, dtype=np.float64)
            lib.fs_debug_copy_pixels(outs[0].ptr, buf.ctypes.data_as(P(C.c_double)), buf.size)
            px = buf.reshape(hh.value, ww.value)
            rec.update(kind="image", h=hh.value, w=ww.value, **stats(px))
            rec["bit_identical_to_bridge"] = (bool(np.array_equal(px, gauss_px))
                                              if gauss_px is not None else None)
        return rec

    out["fs_apply_python"] = call("gaussian", '{"a": 0.5}', 2)     # FS_ROUTE_PYTHON
    out["fs_apply_native"] = call("gauss", '{"sigma": 1.5}', 1)    # FS_ROUTE_NATIVE
    p = C.c_char_p()
    st = lib.fs_catalog_json(C.byref(p))
    s = (p.value or b"").decode("utf-8")
    out["fs_catalog"] = {"status": st, "chars": len(s), "identical_to_bridge": s == cat_s}
    for ptr in owned:
        if ptr:
            lib.fs_image_release(ptr)
    # DLL が sys.path をいじって checkout を差し込んでいないか(ブリッジの在り処は不変)
    out["bridge_file_after"] = sys.modules["fullseye.abi_bridge"].__file__

print(json.dumps(out))
'''


def _probe(wheel_python: str, outside: str, mode: str, libpath: str | None = None) -> dict:
    script = os.path.join(outside, "abi_wheel_probe.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(_PROBE)
    args = [wheel_python, script, mode] + ([libpath] if libpath else [])
    p = _run(args, cwd=outside, env=_env(), timeout=600)
    lines = p.stdout.decode("utf-8", "replace").strip().splitlines()
    assert lines, "探針が何も印字しなかった: %s" % p.stderr.decode("utf-8", "replace")[-1500:]
    return json.loads(lines[-1])


def _under(path: str, root: str) -> bool:
    return os.path.abspath(path).lower().startswith(os.path.abspath(root).lower() + os.sep)


def _from_checkout(path: str) -> bool:
    """checkout のソースを import していたら真。**site-packages の下なら配布物**とみなす。

    CI は wheel 用の venv を checkout の中(`.wheelenv/`)に作るので、「checkout の下に
    あるか」だけで判定すると venv の site-packages まで checkout 扱いになって門が
    空振りする(2026-09-15 の run 34974161857 で 4 件が誤って落ちた)。"""
    norm = os.path.abspath(path).replace("\\", "/")
    return _under(path, ROOT) and "/site-packages/" not in norm


def _meaningful(rec: dict, what: str):
    """「走った」≠「意味のある出力」: 要素数・有限・非定数・入力からの変化を別々に見る。"""
    assert rec["status"] == FS_OK, "%s: status %s — %s" % (what, rec["status"], rec["message"])
    assert rec["n_out"] == 1 and rec["kind"] == "image" and (rec["h"], rec["w"]) == (32, 32), rec
    assert rec["size"] == 32 * 32, rec
    assert rec["finite"], "%s: 非有限が混じる" % what
    assert rec["max"] > rec["min"], "%s: 定数になっている(min = max = %g)" % (what, rec["min"])
    assert rec["n_changed"] > 100, "%s: 入力からほとんど変わっていない(%d 画素)" % (what, rec["n_changed"])


# --------------------------------------------------------------------------- #
# (a) 配布物にブリッジが入っている
# --------------------------------------------------------------------------- #
def test_the_wheel_ships_the_bridge_module_with_its_body(wheel_python, outside):
    """`fullseye/abi_bridge.py` が wheel の RECORD に載り、**中身ごと**入っていること
    (大きさは checkout の正本と一致)。import 先が venv の site-packages であること。"""
    code = ("import os, importlib.metadata as M, fullseye.abi_bridge as B;"
            "rows = [p for p in M.files('fullseye') if str(p).replace(os.sep, '/') == 'fullseye/abi_bridge.py'];"
            "print(len(rows), rows[0].size if rows else -1, os.path.getsize(B.__file__), B.__file__)")
    p = _run([wheel_python, "-c", code], cwd=outside, env=_env(), timeout=300)
    n_rows, size_record, size_disk, where = p.stdout.decode("utf-8", "replace").split(maxsplit=3)
    want = os.path.getsize(os.path.join(ROOT, "fullseye", "abi_bridge.py"))
    assert int(n_rows) == 1, "wheel の RECORD に fullseye/abi_bridge.py が %s 件" % n_rows
    assert int(size_record) == int(size_disk) == want, (size_record, size_disk, want)
    assert want > 15_000, "abi_bridge.py が小さすぎる(%d バイト)" % want
    where = where.strip()
    assert not _from_checkout(where), "ブリッジが checkout から import されている: %s" % where
    assert "site-packages" in where.replace("\\", "/"), where


# --------------------------------------------------------------------------- #
# (b) Python 経路が wheel から意味のある答えを返す
# --------------------------------------------------------------------------- #
def test_the_bridge_applies_ops_from_the_wheel_outside_the_repo(wheel_python, outside):
    r = _probe(wheel_python, outside, "bridge")
    assert r["FULLSEYE_ROOT"] is None and not _under(r["cwd"], ROOT), (r["FULLSEYE_ROOT"], r["cwd"])
    assert not _from_checkout(r["fullseye_file"]) and not _from_checkout(r["bridge_file"]), r

    g = r["gaussian"]
    _meaningful(g, "abi_bridge.apply('gaussian')")
    assert g["tier"] == "registry" and g["backend"], g
    assert g["bit_identical_to_direct_call"] is True, "往復のコピーで画素が変わった"
    assert "a=0.5(float)" in g["message"], g["message"]

    c = r["gauss"]
    _meaningful(c, "abi_bridge.apply('gauss')")
    assert c["tier"] == "contract" and c["backend"], c
    assert "sigma=1.5(float)" in c["message"], c["message"]

    assert r["unknown_op"] == FS_E_UNKNOWN_OP, r["unknown_op"]
    assert r["bad_param"] == FS_E_BAD_PARAMS, r["bad_param"]

    cat = r["catalog"]
    assert cat["n_native"] == 5, cat
    assert cat["n_ops"] == cat["n_rows"], cat
    # 同名が 2 行あるのは「契約にもレジストリにもある名前」だけ(実測: threshold /
    # select_shape。fs_apply の名前解決は契約が勝つので、レジストリ側の同名 op は
    # この入口からは届かない —— 別の名前の op が黙って 2 重に数えられていないことを見る)
    assert set(cat["duplicates"]) <= {"gauss", "threshold", "connection", "measure_all", "select_shape"}, cat["duplicates"]
    assert cat["n_unique"] == cat["n_rows"] - len(cat["duplicates"]), cat
    # numpy + scipy だけの venv でも core の op は載る(ci.yml の bare-install smoke と同じ下限)
    assert cat["n_ops"] > 500, cat
    assert all(cat["has"].values()), {k: v for k, v in cat["has"].items() if not v}
    assert cat["chars"] > 100_000, cat["chars"]


# --------------------------------------------------------------------------- #
# (c) cdylib の fs_apply が wheel のブリッジまで届く
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def embed_lib(tmp_path_factory) -> str:
    """embed feature の cdylib(tmp へのコピー)。`target/embed` に在ればそれ、無ければ
    cargo で建てる(`tests/test_abi_apply.py` と同じ手順・同じ場所)。ホストの CPython と
    同じ版に向けて建ててあるので、3.11 以外では SKIP(python3XY.dll を 2 つ起こさない)。"""
    if sys.version_info[:2] != (3, 11):
        pytest.skip("embed ビルドはホストの CPython 3.11 に向けてある(他の版では走らせない)")
    dst_dir = str(tmp_path_factory.mktemp("abi_wheel_embed"))
    src = os.path.join(EMBED_TARGET, "release", LIBNAME)
    if not os.path.exists(src):
        import test_abi_apply  # cargo が無ければ None を返す(理由は _BUILD_LOG に)
        built = test_abi_apply._build_embed(__import__("pathlib").Path(dst_dir))
        if built is None:
            pytest.skip("embed の cdylib が無く、建てられもしない: %s"
                        % test_abi_apply._BUILD_LOG.get("embed", "?")[-600:])
        src = str(built)
    dst = os.path.join(dst_dir, LIBNAME)
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copy2(src, dst)
    return dst


def test_fs_apply_reaches_the_wheel_through_the_cdylib(wheel_python, outside, embed_lib):
    """ctypes ホスト(= wheel を入れた venv の python)から DLL を読み、`fs_apply` の
    python 経路が **venv の site-packages のブリッジ**で走ること。DLL は tmp のコピー
    なので、embed.rs の「DLL の祖先から checkout を探す」経路は効かない —— wheel に
    ブリッジが無ければここで落ちる(checkout に逃げない)。"""
    r = _probe(wheel_python, outside, "cdylib", embed_lib)
    assert r["FULLSEYE_ROOT"] is None and not _under(r["cwd"], ROOT)

    pa = r["python_available"]
    assert pa["status"] == FS_OK, "python 経路が使えない: %s" % pa["why"]
    assert r["image_create"] == FS_OK

    py = r["fs_apply_python"]
    _meaningful(py, "fs_apply('gaussian', route=python)")
    assert py["route"] == "python" and py["backend"], py
    assert py["degraded"] == 0, py
    assert py["bit_identical_to_bridge"] is True, "cdylib 経由と Python 直呼びの画素が違う"
    assert "a=0.5(float)" in py["message"], py["message"]

    na = r["fs_apply_native"]
    _meaningful(na, "fs_apply('gauss', route=native)")
    assert na["route"] == "native" and na["backend"] == "rust", na

    fc = r["fs_catalog"]
    assert fc["status"] == FS_OK and fc["chars"] == r["catalog"]["chars"] > 100_000, (fc, r["catalog"]["chars"])
    assert fc["identical_to_bridge"] is True, "fs_catalog_json とブリッジの catalog_json が違う"

    assert not _from_checkout(r["bridge_file_after"]), r["bridge_file_after"]
    assert r["bridge_file_after"] == r["bridge_file"], (r["bridge_file_after"], r["bridge_file"])
