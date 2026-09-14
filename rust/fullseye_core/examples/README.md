# 他言語からの呼び出し例

**バインディングは書いていない。** `fullseye_core` は cdylib なので、吐くのは
そのまま C ABI であり、`fullseye_abi.h` がその宣言そのもの。だから

* Python … `ctypes` / `cffi`
* C# … `DllImport`(P/Invoke)
* C / C++ … `fullseye_abi.h` を include して直接リンク
* Lua … LuaJIT の `ffi.cdef`

は **どれも同じ 1 本の .dll / .so を直接叩く**。言語ごとにラッパ層を作ると、
その層の数だけ「仕様の解釈」が増える —— それは
[[feedback_second_implementation_finds_what_tests_cannot]] が言う「解釈が分かれる場所」を
**わざと増やす**行為で、堅牢さの逆を行く。ここに置くのは**呼び出し方の見本 1 つずつ**だけ。

## 実行したかどうか(正直に)

| 例 | 手元の環境(2026-09-14 実測) | 状態 |
|---|---|---|
| `csharp/` | `dotnet` は在るが **ランタイムのみ**(`dotnet --list-sdks` が空、`dotnet --version` が失敗)。`dotnet run` はビルドできない | **未実行** |
| `luajit_ffi.lua` | `luajit` / `lua` いずれも無し | **未実行** |

**どちらも未実行。** コードは `fullseye_abi.h` から機械的に書き写したもので、
**動作は確認していない。**

「書いた」と「走った」は違う([[feedback_ran_is_not_meaningful_output]])。
未実行のものを「対応済み」と数えない。`which dotnet` が当たったのを見て
「C# は確認済み」と書きかけた —— **実行ファイルが在ることと、それでビルドできることは別**。

動かせる環境で走らせたら、この表を**そのとき**更新すること(先に「済」にしない)。
確認できる最低線は、どちらの例も **8×8 の市松が 1 個**(8 連結)と
**`lo > hi` が非ゼロ status** を表示すること —— これが契約の 2 つの要点。

## 先に建てること

```
cd rust/fullseye_core
cargo build --release
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
