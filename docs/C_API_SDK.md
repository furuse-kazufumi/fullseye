# C/C++ SDK の導入

SDK は `pip install fullseye` の標準内容である。extra `[native]` は互換用の空 alias として
残っているだけで、指定する必要はない。最短手順、C/C++ の consumer project、runtime の選び方、
診断は [C_API.md](C_API.md) を参照する。

インストーラーは SDK を別 runtime/DLL として配らない。wheel 内の header、bridge source、CMake
Config、`python -m fullseye.sdk` を一つの標準 Python package として配置する。実行時の既定 root は
`--cmakedir` を出した Python 環境であり、環境変数の設定は不要である。
