# Fullseye C/C++ SDK

The pybind11 C SDK is first published as ABI 0.2 and extended compatibly in
ABI 0.3. It is a development SDK: set
`fs_init_options_t.runtime_root` (with `runtime_root_bytes` for 0.2) or
`FULLSEYE_PYTHON_ROOT` to an environment containing the `fullseye` package.

| Surface | Version | Result lifetime |
| --- | --- | --- |
| `fullseye_abi.h` public L1 contract | published 0.1 | Each function's declared opaque handle |
| `fs_runtime_create`, `fs_find_ops_json`, `fs_call`, and pointer accessors | C SDK 0.2 | `fs_result_t *`, released by `fs_result_release` |
| `fs_find_ops_json_n`, `fs_call_id_n`, and ID accessors | C SDK 0.2 | `fs_result_id_t`, released by `fs_result_release_n` |
| `fs_input_n_t` contour/points tail and coordinate result accessors | C SDK 0.3 | Borrowed coordinate views, valid until `fs_result_release_n` |

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

## Typed operator reachability

`fs_call_id_n` derives its callable operators from the contract and registry
type ledgers. An operator is callable when both its declared input and output
are one of `image`, `region`, `color`, `volume`, scalar `feature`, `contour`,
or `points`; a row
with another sort is rejected as `FS_E_UNSUPPORTED` with the declared-sort
reason. This is fail-closed: it does not substitute an image or tuple for an
unrepresentable value.

`fs_input_n_t` carries direct `image`, `color`, `volume`, and `feature` inputs.
Color uses a 3-D `(H, W, 3)` `fs_array_view_t`; volume uses a dense 3-D or 4-D
`fs_array_view_t`. Shape and stride slots after `ndim` must be zero, and every
axis after the first must be contiguous for all four supported dtypes. Feature
is a finite `double`. Use `fs_result_array_n`
for color or volume outputs and `fs_result_real_n` for feature outputs. The
machine-readable ledger and complete help are generated in
[`fullseye/data/C_API_OPS.json`](../fullseye/data/C_API_OPS.json) and
[`C_API_OPS.md`](C_API_OPS.md); regenerate both with
`py -3.11 tools/gen_c_api_ops.py`.

ABI 0.3 appends `contour` and `points` fields to `fs_input_n_t`; no existing
field or numeric enum value moved. `fs_points_view_t` is the same stable array
layout as `fs_array_view_t`, restricted on direct input to a dense `(N,2)` or
`(N,3)` matrix with `N > 0`; results may be an empty `(0,2)` or `(0,3)` matrix.
A direct contour input is an image `(height,width)` plus one or more
`fs_contour_part_t` values; an operator result may contain no parts. Every part
is a non-empty `(N,2)` coordinate matrix and carries an explicit `closed` flag.
`contours_bytes` and `contour_stride_bytes` bound the descriptor array. The flag is semantic: a
closed C contour has an implicit last-to-first segment. The bridge maps it to
the Python contour convention by repeating the first point when needed, and
removes a repeated endpoint from a part explicitly marked open.

Coordinate views apply the same fail-closed checks as color and volume:
supported dtype, positive dimensions and strides, zero unused shape/stride
slots, contiguous inner axis, sufficient byte extent, alignment, and no NaN or
infinity. Direct input memory is borrowed only during `fs_call_id_n`. Use
`fs_result_points_n`, or `fs_result_contour_shape_n`,
`fs_result_contour_count_n`, and `fs_result_contour_n` for borrowed outputs.
## Five-minute start (continued)

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
fullseye_deploy_runtime(app)
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
  const fullseye::Runtime::Parameter blur{"a", 0.5};
  auto out = fs.call("gaussian", image, {blur});
  return out.size() == 1 ? 0 : 1;
}
```

そのままコピーして使える C++ と C の consumer project は
[`examples/c_api/hello_cpp`](../examples/c_api/hello_cpp) と
[`examples/c_api/hello_c`](../examples/c_api/hello_c) にある。

## Studio の保存を C++ で動かす / Run a saved Studio pipeline from C++

Studio で pipeline を作り、Problems が空であることを確認して **Save pipeline** を選ぶ。
保存された UTF-8 JSON をアプリの実行時 working directory に `inspect.json` として置けば、
アプリ側は次だけで入力名・型を読み、実行できる。

```cpp
fullseye::Runtime fs;
auto image = fullseye::Image::from_buffer(pixels.data(), height, width);
fullseye::Pipeline p = fs.load_pipeline("inspect.json");
auto input = p.input();       // {"image", FS_VALUE_IMAGE}
auto output = p.output();     // 例: {"result", FS_VALUE_REGION}
const fullseye::PipelineInput pipeline_input{"image", image};
auto out = p.run({pipeline_input});
```

`Pipeline` と `Result` は move-only RAII 型で、結果 ID と pipeline handle を自動で解放する。
`out.image()` は画像の借用 view、`out.region_runs()` は region の run list のコピー、
`out.real()` はスカラーを返す。入力名・型、出力名・型が違う場合は実行前に拒否され、
例外にはどの stage / op / 型が合わないかと Studio での直し方が入る。

`examples/c_api/hello_pipeline` は `inspect.json` を Studio 保存物として C++ から読む完全な
consumer project である。最初の CMake build の後は JSON の stage や knob を保存し直して
アプリを再起動するだけでよい。C++ を再コンパイルする必要はない。

C では同じ Python 実行器の上にある `fs_pipeline_load_path_n` または
`fs_pipeline_load_json_n` を使う。`fs_pipeline_input_info` / `fs_pipeline_output_info` が
名前と `fs_value_kind_t` を返し、`fs_pipeline_run_n` は `fs_pipeline_input_n_t` の名前付き
入力から通常の generation-tagged `fs_result_id_t` を返す。パスは 98,301 UTF-8 bytes、
JSON と pipeline file は 1 MiB を上限として、ファイルを開く・解析する前に拒否する。
未知 op、型連鎖の不一致、余計な JSON key も同じ読み込み時に fail-closed となる。

Python でも同じ入口を使える。

```python
import fullseye

p = fullseye.load_pipeline("inspect.json")
result = p.run(image.copy())
```

CLI の `fullseye run inspect.json ...`、Python、C、C++ はこの同じ保存 JSON 検証を共有する。

## SDK CLI

```text
python -m fullseye.sdk --cmakedir    # find_package 用の Config directory
python -m fullseye.sdk --includedir  # <fullseye.hpp> がある directory
python -m fullseye.sdk --python      # Config が使う Python executable
python -m fullseye.sdk --doctor      # compiler / Python headers / pybind11 / example build
python -m fullseye.sdk relink ./build # 実行ファイル横の runtime manifest を更新する
```

`fullseye_deploy_runtime(app)` はビルド時に、`app` の横へ UTF-8 の
`fullseye_runtime.json` を置く。中身は Python executable、runtime root、SDK ABI 版、作成日時
であり、runtime root を DLL/SO に焼き込まない。したがって、仮想環境を移動した後も新しい
Python から `relink` を一度実行すれば、CMake の configure や再ビルドは不要である。

起動時は、候補を Python process として起動せず、`fullseye/__init__.py` と
`fullseye/sdk/ABI_VERSION` の存在・ABI を確認して次の順に選ぶ。選んだ場所は stderr に出る。

1. `fs_init_options_t.runtime_root` の明示値
2. `FULLSEYE_PYTHON_ROOT`
3. 実行ファイル横の `fullseye_runtime.json`
4. `VIRTUAL_ENV`、`CONDA_PREFIX`
5. Windows の PEP 514 registry、Linux/macOS の `PATH` 上の `python3`
6. 古い build-time fallback（存在する旧 binary だけ）

SDK ABI が違う候補、`fullseye` の無い候補は使わない。`Runtime::diagnose()` と
`fs_runtime_diagnose()` は CPython を起動せずに同じ探索表を返す。

`--doctor` は CMake、コンパイラ、Python 開発ヘッダ、同梱 pybind11 を確認し、temp directory
で consumer C++ project を configure、build、run する。失敗時は不足した部品ごとに
Windows/Linux/macOS の導入コマンドを stderr に出す。CMake configure 自体でも同じく、
compiler、Python 開発ヘッダ、pybind11 が無い理由と導入コマンドを出して止まる。

## うまく動かないとき / Troubleshooting

まず、実行ファイルと同じ directory を指定して manifest を更新する。これは再ビルドではない。

```powershell
py -3.11 -m pip install fullseye
py -3.11 -m fullseye.sdk relink .\build
```

```sh
python3 -m pip install fullseye
python3 -m fullseye.sdk relink ./build
```

それでも `fs_runtime_create` が `FS_E_NO_PYTHON` を返すとき、`fs_last_error` には試行した
全候補と結果（無い、`fullseye` が無い、ABI 版違い）が並ぶ。C++ では同じ本文が
`fullseye::Error` に入り、アプリを起動せず表示したいときは
`fullseye::Runtime::diagnose()` を呼ぶ。Windows で Python DLL や build tool が見つからない
場合は `py -3.11 -m fullseye.sdk --doctor` を実行する。

## C API

C でも同じ Config target を link する。`examples/c_api/hello_c/hello.c` は、環境変数も
Python のパスの手書きもせず `fs_runtime_create`、`registry:gaussian`、結果の解放までを示す。
入力バッファは `fs_call` / `fs_call_id_n` が戻るまで借用される。結果の borrowed view は対応する
`fs_result_release*` まで有効で、library が確保した文字列は `fs_free` で解放する。

C ABI は fail-closed である。scope の無い op 名、未知の JSON key、NaN/Inf、形状・stride・
buffer length の不整合は状態コードと `fs_last_error` で拒否する。既存の ABI 0.1 関数と
`fullseye_abi.h` は互換のまま残る。

## Rust の第 2 実装 / Rust second implementation

`rust/fullseye_core` は仕様差分を見つけるための第 2 実装であり、現在は ABI 0.2 の部分集合を
名乗る。ヘッダの ABI 0.3 で追加した Studio pipeline (`fs_pipeline_*`) は Rust 側に未実装なので、
Rust library を pipeline consumer として使ってはならない。

この部分集合には image / region / objectset / tuple の基本関数、`fs_gauss`、`fs_threshold`、
`fs_connection`、`fs_measure_all`、`fs_select_shape` と `fs_apply` が含まれる。ABI parity test は
Rust が名乗る版がヘッダ以下であることと、この実装済み関数集合だけを検証する。ヘッダと同じ
最新版を名乗らせて未実装の pipeline を利用可能に見せることはしない。

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
