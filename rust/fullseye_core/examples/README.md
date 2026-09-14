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
| `csharp/` | .NET SDK 9.0.318(`winget install Microsoft.DotNet.SDK.9`) | **実行して確認済み** |
| `luajit_ffi.lua` | LuaJIT 2.1.19907(`winget install DEVCOM.LuaJIT`) | 導入済み・**実行確認は未** |

### C# の実際の出力(`dotnet run`)

```
ABI 0.1
面積 32 / run 32 / 物体 1
契約どおり: 8x8 の市松は 8 連結で 1 個
逆さの区間 lo>hi は status 1 で拒まれた
```

確認できる最低線は、どちらの例も **8×8 の市松が 1 個**(8 連結)と
**`lo > hi` が非ゼロ status** を出すこと —— これが契約の 2 つの要点で、
どちらも「実装が黙って別の答えを返していた」実際の欠陥に対応する。

### 記録しておく失敗

最初、`which dotnet` が当たったのを見て「C# は確認済み」と書きかけた。
実際は **ランタイムだけで SDK が無く、`dotnet run` はビルドできなかった**。
**実行ファイルが在ることと、それでビルドできることは別**
([[feedback_ran_is_not_meaningful_output]])。SDK を入れて初めて上の出力が得られた。
未実行のものを「対応済み」と数えない —— 表は**走らせたその時に**更新する。

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
