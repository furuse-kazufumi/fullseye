# 他言語からの呼び出し例

**バインディングは書いていない。** `fullseye_core` は cdylib なので、吐くのは
そのまま C ABI であり、`fullseye_abi.h` がその宣言そのもの。だから

* Python … `ctypes` / `cffi`
* C# … `DllImport`(P/Invoke)
* C / C++ … `fullseye_abi.h` を include して直接リンク
* Lua … LuaJIT の `ffi.cdef`

は **どれも同じ 1 本の .dll / .so を直接叩く**。言語ごとにラッパ層を作ると、
その層の数だけ「仕様の解釈」が増える —— 同じ仕様を 2 度実装して初めて見つかる欠陥が
あるのは事実だが、それは**解釈が分かれる場所をわざと増やす**理由にはならず、堅牢さの
逆を行く。ここに置くのは**呼び出し方の見本 1 つずつ**だけ。

| 言語 | ファイル | 呼び方 |
|---|---|---|
| C / C++ | [`c/main.c`](c/main.c) | `#include "fullseye_abi.h"` して直接リンク。C++ からも同じヘッダをそのまま include できる(`extern "C"` はヘッダ側にある) |
| C# | [`csharp/Program.cs`](csharp/Program.cs) | `DllImport`(P/Invoke) |
| Lua | [`luajit_ffi.lua`](luajit_ffi.lua) | LuaJIT の `ffi.cdef` |
| Python | [`python_ctypes.py`](python_ctypes.py) | `ctypes`(標準ライブラリだけ。numpy も fullseye 本体も使わない) |

## 実行したかどうか(正直に)

| 例 | 手元の環境(2026-09-14 実測、Python は 2026-09-15) | 状態 |
|---|---|---|
| `c/`(clang) | clang 22.1.8 / target `x86_64-pc-windows-msvc`(`winget install LLVM.LLVM`)。`target/release/fullseye_core.dll.lib` をリンク | **実行して確認済み** |
| `c/`(gcc) | gcc 16.1.0 MinGW-W64 ucrt-posix-seh(`winget install BrechtSanders.WinLibs.POSIX.UCRT`、実体は `%LOCALAPPDATA%\Microsoft\WinGet\Packages\BrechtSanders...\mingw64\bin`)。**`.dll` を直リンク** | **実行して確認済み** |
| MSVC(`cl.exe`) | MSVC 14.44.35207(Build Tools 2022)。`winget` の一発インストールは **失敗**(`Installer failed with exit code: 1` を返すのに **winget 自体は exit 0**)—— 本体は入っていて **C++ ワークロードだけが欠けていた**ので、`setup.exe modify --add Microsoft.VisualStudio.Workload.VCTools` で追加した | **ヘッダ検査は C / C++ とも通過** |
| `csharp/` | .NET SDK 9.0.318(`winget install Microsoft.DotNet.SDK.9`) | **実行して確認済み** |
| `luajit_ffi.lua` | LuaJIT 2.1.19907(`winget install DEVCOM.LuaJIT`、実体は `%LOCALAPPDATA%\Programs\LuaJIT\bin`) | **実行して確認済み** |
| `python_ctypes.py` | CPython 3.11(標準ライブラリのみ) | **実行して確認済み** |

★ MSVC の件は同じ日に 3 度目の「**exit 0 なのに失敗**」だった(あとの 2 つは
pytest の collection 中断と、`head` にパイプした `$?` の読み違い)。
**終了コードを信じず、成果物の実在で確かめる。**

### 実際の出力 —— C / C# / Lua / Python で**同一**

```
ABI 0.1
dtype 読み返し: 4 (FS_DTYPE_F64 = 4)
面積 32 / run 32 / 物体 1
契約どおり: 8x8 の市松は 8 連結で 1 個
逆さの区間 lo>hi は status 1 で拒まれた
```

4 つの言語が**同じ 1 本の .dll を叩いて同じ答え**を出している。
これがバインディングを書かずに済む理由であり、「多言語対応」の実体でもある。

### ★ C の例だけが持っている役目

Python(ctypes)・C#(P/Invoke)・Lua(FFI)は、どれも**宣言を書き写す**。
だから **全員が同じ写し間違いをしていれば、互いに一致していることが検証にならない**。

実際 2026-09-14 に `fs_image_create` の第 5 引数 `fs_dtype_t dtype` が
**ヘッダにだけ在って、Rust 実装にも 3 つの FFI 宣言にも無い**状態が見つかった ——
差分ファジング 60,000 ケース × 3 シードも、変異解析 10/10 も、全部素通りしていた。
C ABI の引数ずれは実行時に何の兆候も出さず、黙って別の値を掴む。

**ヘッダを `#include` する呼び手が 1 つあれば、コンパイラがその場で止める。**
それがこの例の存在理由で、速度や機能のためではない。機械検査は
`tests/test_abi_signatures_match.py`(C コンパイラが無い環境でも引数の数を照合する)。

確認できる最低線は、どちらの例も **8×8 の市松が 1 個**(8 連結)と
**`lo > hi` が非ゼロ status** を出すこと —— これが契約の 2 つの要点で、
どちらも「実装が黙って別の答えを返していた」実際の欠陥に対応する。

### 記録しておく失敗

最初、`which dotnet` が当たったのを見て「C# は確認済み」と書きかけた。
実際は **ランタイムだけで SDK が無く、`dotnet run` はビルドできなかった**。
**実行ファイルが在ることと、それでビルドできることは別**(「走った」と「意味のある
出力が出た」を混ぜない)。SDK を入れて初めて上の出力が得られた。
未実行のものを「対応済み」と数えない —— 表は**走らせたその時に**更新する。

## 先に建てること

```
cd rust/fullseye_core
cargo build --release
```

## C / C++

```
cd rust/fullseye_core
clang -std=c11 -Wall -Wextra -I../.. examples/c/main.c target/release/fullseye_core.dll.lib -o examples/c/fs_example.exe
cp target/release/fullseye_core.dll examples/c/
cd examples/c && ./fs_example.exe
```

Linux / macOS は `-Ltarget/release -lfullseye_core` でリンクし、`LD_LIBRARY_PATH=target/release`
で実行する(gcc / MSVC の行は `c/main.c` 冒頭のコメントにある)。★インポートライブラリで
リンクしても**実行時は DLL を別に探す** —— 置き忘れると exe は何も印字せずに終わる。

## Python (ctypes)

```
py -3.11 rust/fullseye_core/examples/python_ctypes.py
```

## C#

```
cd rust/fullseye_core/examples/csharp
dotnet run
```

## Lua (LuaJIT)

```
luajit rust/fullseye_core/examples/luajit_ffi.lua
```
