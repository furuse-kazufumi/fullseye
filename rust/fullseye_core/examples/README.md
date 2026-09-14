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

| 例 | 環境 | 状態 |
|---|---|---|
| `csharp/` | dotnet SDK あり | **実行して確認済み**(下記の出力) |
| `luajit_ffi.lua` | LuaJIT が手元に無い | **未実行**。コードは `fullseye_abi.h` から機械的に書き写したもので、**動作は確認していない** |

「書いた」と「走った」は違う([[feedback_ran_is_not_meaningful_output]])。
未実行のものを「対応済み」と数えない。

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
