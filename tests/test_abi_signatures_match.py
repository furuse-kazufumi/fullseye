# -*- coding: utf-8 -*-
"""`fullseye_abi.h` の宣言と、それを呼ぶ側の宣言が**引数の数で一致**すること。

★この門が無かったせいで起きたこと(2026-09-14 実測): `fs_image_create` は
ヘッダで **8 引数**(第 5 が `fs_dtype_t dtype`)なのに、Rust 実装も ctypes の
3 箇所も **7 引数**で書かれていた。**C ABI の引数がずれたまま**、差分ファジング
60,000 ケース × 3 シードも変異解析 10/10 も全部緑だった。

なぜ誰も気づけなかったか —— Python(ctypes)/ C#(P/Invoke)/ Lua(FFI)は
どれも**宣言を書き写す**ので、**全員が同じ写し間違いをしていれば一致してしまう**。
「2 つの実装を突き合わせる」差分テストは、**両方が同じ写しから出発している**と
無力になる([[feedback_second_implementation_finds_what_tests_cannot]] の限界)。

見つかったのは **C から `#include` して呼ぶ例を初めて書いたとき**。ヘッダを読む
呼び手が 1 つあれば、コンパイラがその場で止める。この門はそれを機械化したもの
で、C コンパイラが無い環境でも効くよう **テキストとして数を突き合わせる**。
"""
from __future__ import annotations

import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HEADER = os.path.join(ROOT, "fullseye_abi.h")
RUST = os.path.join(ROOT, "rust", "fullseye_core", "src", "lib.rs")

#: ヘッダが宣言していて Rust スパイクが**意図的に実装していない**もの。
#: 実装しない理由を書く —— 空欄にすると「未実装」と「書き忘れ」が混ざる。
RUST_NOT_IMPLEMENTED = {
    "fs_image_domain": "処理領域(HALCON モデル)はこのスパイクの範囲外",
    "fs_image_reduce_domain": "同上",
    "fs_tuple_elem_type": "real しか作らないので型問い合わせは未実装",
}

#: Rust 側にあってヘッダに無いもの。**契約ではない**ことを明示する。
RUST_ONLY = {
    "fs_abi_version": "版の問い合わせ。ヘッダはマクロで版を持つので関数宣言は無い",
    "fs_debug_copy_pixels": "テスト専用の抜け道。契約に足すかは別の決定(ヘッダの註を参照)",
}


def header_decls() -> dict[str, int]:
    """ヘッダの関数宣言 -> 引数の数。"""
    src = open(HEADER, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"(?:fs_status_t|void)\s+(fs_\w+)\s*\(([^;]*?)\)\s*;", src, re.S):
        args = [a.strip() for a in m.group(2).split(",") if a.strip()]
        out[m.group(1)] = len(args)
    return out


def rust_decls() -> dict[str, int]:
    """Rust の `extern "C"` 関数 -> 引数の数。"""
    src = open(RUST, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'pub extern "C" fn (fs_\w+)\s*\(([^)]*)\)', src, re.S):
        args = [a.strip() for a in m.group(2).split(",") if a.strip()]
        out[m.group(1)] = len(args)
    return out


def ctypes_argtypes() -> dict[str, dict[str, int]]:
    """ctypes で `argtypes` を宣言している箇所 -> {関数名: 引数の数}。

    リストの要素数を数えるだけ(型までは見ない)。**数のずれがいちばん静かに
    壊れる**ので、まずそこを固定する。
    """
    files = ["tools/fs_abi_fuzz.py", "tools/fs_abi_bench.py",
             "tests/test_rust_abi_parity.py"]
    out = {}
    for rel in files:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        # コメントを落としてから括弧の中の要素を数える
        got = {}
        # ★`[A] + [B] * 3` のような**式**で書かれた argtypes がある。最初この形を
        #   数えられず `fs_measure_all` を「1 引数」と誤読して門が 3 件赤になった ——
        #   **門のパーサが弱いのを実装の欠陥と読まない。** 行末までを 1 宣言として
        #   取り、`[...]` の各塊の要素数に `* N` の倍数を掛けて合計する。
        for m in re.finditer(r"\.(fs_\w+)\.argtypes\s*=\s*(.+?)(?=\n\s*(?:lib|getattr|for|return|#|$))",
                             src, re.S):
            body = re.sub(r"#[^\n]*", "", m.group(2))
            total = 0
            for part in re.finditer(r"\[([^\[\]]*)\]\s*(?:\*\s*(\d+))?", body):
                items = [x for x in part.group(1).split(",") if x.strip()]
                total += len(items) * int(part.group(2) or 1)
            if total:
                got[m.group(1)] = total
        if got:
            out[rel] = got
    return out


def test_the_header_and_the_rust_implementation_agree_on_arity():
    hdr, rs = header_decls(), rust_decls()
    assert len(hdr) >= 20, "ヘッダの宣言を読めていない(%d 件)" % len(hdr)
    assert len(rs) >= 20, "Rust の宣言を読めていない(%d 件)" % len(rs)

    bad = {n: (hdr[n], rs[n]) for n in set(hdr) & set(rs) if hdr[n] != rs[n]}
    assert not bad, (
        "ヘッダと Rust で**引数の数が違う**: %s\n"
        "  C ABI の引数ずれは実行時に何の兆候も出さず、黙って別の値を掴む。"
        % ", ".join("%s(ヘッダ %d / Rust %d)" % (n, a, b) for n, (a, b) in sorted(bad.items())))

    missing = sorted(set(hdr) - set(rs) - set(RUST_NOT_IMPLEMENTED))
    assert not missing, (
        "ヘッダにあって Rust に無い関数が増えた: %s —— 実装するか、"
        "RUST_NOT_IMPLEMENTED に**理由つきで**足すこと" % missing)

    extra = sorted(set(rs) - set(hdr) - set(RUST_ONLY))
    assert not extra, (
        "Rust にあってヘッダに無い関数が増えた: %s —— 契約に入れるなら宣言し、"
        "契約外なら RUST_ONLY に**理由つきで**足すこと(黙って生やさない)" % extra)


@pytest.mark.parametrize("rel", sorted(ctypes_argtypes()))
def test_ctypes_declarations_match_the_header(rel):
    """FFI で書き写した宣言が、ヘッダと**引数の数で**一致すること。

    書き写しどうしを突き合わせても、全員が同じ間違いをしていれば一致する ——
    だから**ヘッダと**照合する。
    """
    hdr = header_decls()
    got = ctypes_argtypes()[rel]
    assert got, "%s に argtypes が 1 つも無い" % rel
    bad = {n: (hdr[n], k) for n, k in got.items() if n in hdr and hdr[n] != k}
    assert not bad, (
        "%s の argtypes がヘッダと合わない: %s"
        % (rel, ", ".join("%s(ヘッダ %d / ctypes %d)" % (n, a, b)
                          for n, (a, b) in sorted(bad.items()))))


#: C の処理系は 3 系統あり、**顧客は選べない**(既存の C++ 製品に組み込むとき、
#: その製品がどれで建っているかは向こうの都合)。だから在るものは**全部**試す ——
#: 1 つ通ったから良し、にすると残り 2 つで落ちる方言が残る。
_C_COMPILERS = ("clang", "gcc", "cc")


@pytest.mark.parametrize("cc_name", _C_COMPILERS)
def test_the_header_compiles_as_c(cc_name):
    """ヘッダ単体が C として通ること。**無ければ正直に SKIP**。

    ★「最初に見つかった 1 つだけ」を試していたのを、在る処理系すべてに広げた
    (2026-09-14)—— clang(MSVC ABI)で通っても gcc(MinGW)で通るとは限らず、
    その逆もある。**1 つで代表させない**のは探針の話と同じ
    ([[feedback_one_probe_input_is_not_coverage]])。
    """
    import shutil
    import subprocess
    cc = shutil.which(cc_name)
    if cc is None:
        pytest.skip("%s が無い —— **建たなかった**ことを「通った」と混ぜない" % cc_name)
    r = subprocess.run([cc, "-fsyntax-only", "-std=c11", "-Wall", "-Wextra", HEADER],
                       capture_output=True, text=True)
    assert r.returncode == 0, (
        "fullseye_abi.h が %s で C として通らない:\n%s"
        % (cc_name, (r.stderr or r.stdout)[:2000]))


def test_the_header_compiles_under_msvc():
    """MSVC(`cl.exe`)でも C / C++ として通ること。**無ければ正直に SKIP**。

    MSVC は方言が最も違う処理系で、しかも**顧客の C++ 製品はたいていこれで建つ**。
    gcc / clang が通っても MSVC が通るとは限らない(`/W4` の警告も別物)。
    `vcvars64.bat` を通して環境を作らないと `cl` は動かないので、`cmd` 越しに呼ぶ。
    """
    import glob
    import subprocess
    vcvars = glob.glob(r"C:\Program Files*\Microsoft Visual Studio\*\*\VC\Auxiliary"
                       r"\Build\vcvars64.bat")
    if not vcvars:
        pytest.skip("MSVC(vcvars64.bat)が無い —— 建たなかったことを「通った」と混ぜない")
    import tempfile
    # ★`cl` に `.h` を直接渡してはいけない —— MSVC は拡張子で言語を決めるので
    #   「ソースファイルの種類は認識できません」と**警告だけ出して rc=0 を返す**。
    #   検査が 1 行も走っていないのに緑になる、最悪の形
    #   ([[feedback_ran_is_not_meaningful_output]]。2026-09-14 に実際そう読みかけた)。
    #   `#include` する小さな .c / .cpp を作って `/Zs`(構文検査のみ)を掛ける。
    with tempfile.TemporaryDirectory() as td:
        for std, ext in (("c11", ".c"), ("c++17", ".cpp")):
            src = os.path.join(td, "probe" + ext)
            with open(src, "w", encoding="ascii") as f:
                f.write('#include "%s"\n' % HEADER.replace("\\", "\\\\"))
            # ★引用は **1 段も挟まない**。`subprocess` にリストで渡すと Python が
            #   引数を再クォートし、内側の `"` が `\"` に化けて cmd に届く
            #   (実測のエラー: `'\"C:\Program Files...\vcvars64.bat\"' は認識されて
            #    いません`)。バッチファイルに書き出して、それを叩くのが確実。
            bat = os.path.join(td, "probe%s.bat" % ext.replace(".", "_"))
            with open(bat, "w", encoding="cp932") as f:
                f.write('@echo off\r\ncall "%s" >nul\r\n'
                        'cl /nologo /std:%s /W4 /WX /Zs "%s"\r\n' % (vcvars[0], std, src))
            # 出力は cp932(日本語)。`text=True` だと UTF-8 復号に失敗して
            # **stdout/stderr が空になり「rc だけあって理由が無い」**になる。
            r = subprocess.run(["cmd", "/c", bat], capture_output=True)
            out = ((r.stdout or b"") + (r.stderr or b"")).decode("cp932", "replace")
            assert r.returncode == 0, (
                "fullseye_abi.h が MSVC(/std:%s)で通らない:\n%s" % (std, out[:2000]))
            assert "D9024" not in out and "D9021" not in out, (
                "MSVC がソースを認識していない(= 検査が走っていない):\n%s" % out[:800])


def test_the_header_compiles_as_cpp_when_a_compiler_is_available():
    """**C++ からも include できること。** ヘッダは `extern "C"` を宣言しているので
    通るはずだが、通ることを誰も確かめていなかった —— 顧客が組み込む先は
    たいてい C ではなく **C++** の製品。"""
    import shutil
    import subprocess
    cxx = shutil.which("clang++") or shutil.which("g++")
    if cxx is None:
        pytest.skip("C++ コンパイラが無い")
    r = subprocess.run([cxx, "-fsyntax-only", "-std=c++17", "-Wall", "-Wextra",
                        "-x", "c++", HEADER], capture_output=True, text=True)
    assert r.returncode == 0, (
        "fullseye_abi.h が C++ として通らない:\n%s" % (r.stderr or r.stdout)[:2000])
