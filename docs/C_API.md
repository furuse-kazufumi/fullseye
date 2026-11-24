# Fullseye C/C++ SDK

## 5 分で動かす / Five-minute start

`pip install fullseye` だけで C/C++ 用のヘッダ、pybind11 ブリッジのソース、CMake
Config、SDK 検出 CLI が入る。pip の導入時にも `import fullseye` 時にもネイティブコードを
ビルド・読込しない。利用者の CMake が、その利用者のコンパイラと Python 環境に合わせて
ブリッジをビルドする。

```text
pip install fullseye
cmake -S . -B build -Dfullseye_DIR="$(python -m fullseye.sdk --cmakedir)"
cmake --build build
```

PowerShell では `python` の代わりに導入した Python を明示してもよい。

```powershell
py -3.11 -m pip install fullseye
cmake -S . -B build "-Dfullseye_DIR=$(py -3.11 -m fullseye.sdk --cmakedir)"
cmake --build build
```

Linux/macOS では次のとおり。

```sh
python3.11 -m pip install fullseye
cmake -S . -B build -Dfullseye_DIR="$(python3.11 -m fullseye.sdk --cmakedir)"
cmake --build build
./build/app
```

利用側の `CMakeLists.txt` はこれだけでよい。

```cmake
find_package(fullseye CONFIG REQUIRED)
add_executable(app main.cpp)
target_link_libraries(app PRIVATE fullseye::fullseye)
```

`main.cpp` は借用かコピーかを選んで既存の連続 `double` バッファを渡せる。名前に scope を
書かない場合、C++ 層は registry の実在 op として解決する。C ABI 自体では曖昧さを防ぐため
`registry:gaussian` のような scope が必須である。

```cpp
#include <fullseye.hpp>
#include <array>

int main() {
  fullseye::Runtime fs;  // CMake を設定した Python 環境を既定で使う
  std::array<double, 9> pixels{0, .2, 0, .2, 1, .2, 0, .2, 0};
  auto image = fullseye::Image::from_buffer(pixels.data(), 3, 3);
  auto matches = fs.find("gaussian");
  auto out = fs.call("gaussian", image, {{"a", 0.5}});
  return out.size() == 1 ? 0 : 1;
}
```

そのままコピーして使える C++ と C の consumer project は
[`examples/c_api/hello_cpp`](../examples/c_api/hello_cpp) と
[`examples/c_api/hello_c`](../examples/c_api/hello_c) にある。

## SDK CLI

```text
python -m fullseye.sdk --cmakedir    # find_package 用の Config directory
python -m fullseye.sdk --includedir  # <fullseye.hpp> がある directory
python -m fullseye.sdk --python      # Config が使う Python executable
python -m fullseye.sdk --doctor      # compiler / Python headers / pybind11 / example build
```

`--cmakedir` は呼び出した Python executable と、その `fullseye` package root を記録した
小さな Config shim を返す。そこでビルドされた DLL/SO は `Runtime()` の既定で同じ root を
使う。明示的な `fs_init_options_t.runtime_root` と `FULLSEYE_PYTHON_ROOT` は、既存アプリで
別の runtime を指定する上書きとして引き続き使える。

Config を作った後で仮想環境を移動または削除すると、埋め込んだ build-time の root は無効になる。
この場合 `fs_runtime_create` は理由と `cmake` を再実行する手順を含む `FS_E_NO_PYTHON` を返す。
環境を移動したら、新しい環境の Python で `cmake -S . -B build -Dfullseye_DIR="$(python -m
fullseye.sdk --cmakedir)"` をもう一度実行してから build する。

`--doctor` は CMake、コンパイラ、Python 開発ヘッダ、同梱 pybind11 を確認し、temp directory
で consumer C++ project を configure、build、run する。失敗時は不足した部品と対処を stderr
に出す。

## C API

C でも同じ Config target を link する。`examples/c_api/hello_c/hello.c` は、環境変数も
Python のパスの手書きもせず `fs_runtime_create`、`registry:gaussian`、結果の解放までを示す。
入力バッファは `fs_call` / `fs_call_id_n` が戻るまで借用される。結果の borrowed view は対応する
`fs_result_release*` まで有効で、library が確保した文字列は `fs_free` で解放する。

C ABI は fail-closed である。scope の無い op 名、未知の JSON key、NaN/Inf、形状・stride・
buffer length の不整合は状態コードと `fs_last_error` で拒否する。既存の ABI 0.1 関数と
`fullseye_abi.h` は互換のまま残る。

## C++ の寿命・エラー・OpenCV

`Runtime` と `Result` は move-only RAII 型で、例外 `fullseye::Error` は C status と op 名を含む
メッセージを返す。C++20 では `Image::from_buffer(std::span<const double>, h, w)` も使える。
`BufferOwnership::copy` を渡すと入力を所有し、既定の `borrow` は呼出し中だけ caller の buffer を
借用する。

OpenCV は必須依存にしない。OpenCV を link する target だけが `FULLSEYE_WITH_OPENCV` を定義して
`<fullseye_opencv.hpp>` を include すると、連続した `CV_64FC1` の `cv::Mat` を
`fullseye::image_from_mat` で borrow/copy できる。

## 配布の理由と限界

wheel は pure Python のまま、ヘッダと bridge source を同梱する。利用者側でビルドするので
MSVC、MinGW、GCC、Clang 間の C++ ABI 差を配布 DLL に持ち込まず、platform-specific wheel も
不要になる。pybind11 はヘッダだけの固定依存だが、CMake とコンパイラは C/C++ 利用時だけ必要で、
Python 利用だけなら増えない。

この bridge は同一プロセスの CPython を呼ぶ。Python/ネイティブ拡張のクラッシュは host process
も終了させるため、未信頼の op を隔離する用途には別 process の経路を使う。Python runtime の
上書きは最初の `Runtime` 初期化前に行い、同じ process で複数の異なる runtime root は使えない。
