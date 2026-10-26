# tools/probe_studio_web — Studio をブラウザで動かす可否の探針(probe、2026-10-25)

**これは探針であって製品でも生成器でもない。** ここの script は repo の中に何も書かない(出力先は引数で渡す
repo の外のディレクトリ)。`tools/regen_all.py` の表では `NOT_A_GENERATOR` に載せてある。
測った数字と判断は `fullseye_private/notes/studio_web_feasibility_2026_10_25.md`(repo の外)にある。
製品側(ブラウザ版 Studio-lite v0)は `studio_lite/` を見る。

| ファイル | 何をするか |
|---|---|
| `op_inventory.py` | 全 op(registry / n-ary / 型付き台帳 = 3,565)を実装モジュールの import で分類する。モジュール先頭の素の import、try で守られた import、関数内の遅延 import を分け、repo 内モジュールの先頭 import の閉包まで辿る。Pyodide に同梱される配布物(numpy / scipy / cv2 / skimage / Pillow …)に無いものを「ブラウザで動かない」側に数える |
| `bench_body.py` | 代表 11 op(閾値 / 平滑 / 形態 / 縁 / 距離変換 / 3-D の RANSAC 平面と法線 / 光学の Airy と MTF)を 512×512 画像と 1 万点で計時する**共通本体**。CPython でも Pyodide でも同じファイルを読む |
| `pyodide_trial.mjs` | node 上の Pyodide に repo を NODEFS で見せ、op を定義する全モジュールを 1 つずつ import して読めないものと理由を集め、`bench_body` を同じ入力で回す(`min` = numpy/scipy だけ、`full` = cv2 / skimage / Pillow / PyWavelets / imageio も) |
| `pyodide_studio_import.mjs` | Studio の Qt でない部品(`studio.apply_display` / `param_specs` / `recipes` / `engine` / `studio_display` …)が Pyodide で読めて呼べるかを測る |
| `build_proof.py` | 最小の証明ページを repo の外に組む: Pyodide 本体と wheel を**同じ dist に複製**(外部 URL なし)、`import api` が読む repo 内モジュールを zip に固める、`proof.html` を置く、各部のバイト数を `sizes.json` に書く |
| `proof.html` | 証明ページ本体。画像を読む(または合成画像)→ gaussian → sobel_amp → otsu を走らせ、pocviewer の「処理の帯」の流儀で 入力 → 各 op → 出力 → 理論 vs op を並べる。理論 = 256 階調の総当たり Otsu 閾値 |
| `cdp_shot.mjs` | 撮影係。`chrome --screenshot` は WebAssembly の読み込みを待たない(2 秒で撮れてしまう)ので、DevTools protocol でページが「出来た」と言う式を待ってから撮る |

## 回し方(pyodide npm と wheel は repo の外に置く)

```
npm i pyodide@314.0.7                      # scratchpad など repo の外で
py -3.11 tools/probe_studio_web/op_inventory.py --out <out>
py -3.11 tools/probe_studio_web/bench_body.py 5 > <out>/bench_native.json
node tools/probe_studio_web/pyodide_trial.mjs <repo> tools/probe_studio_web/bench_body.py <out>/op_inventory_rows.json <out>/trial_min.json min
py -3.11 tools/probe_studio_web/build_proof.py --pyodide-dir <node_modules/pyodide> --wheels-dir <wheel cache> --out <dist>
py -3.11 -m http.server 8765 --bind 127.0.0.1    # dist の中で(file:// では WebAssembly を fetch できない)
node tools/probe_studio_web/cdp_shot.mjs <chrome.exe> http://127.0.0.1:8765/proof.html?auto <out>/shot.png "!!(window.__probe)"
```

`pyodide_trial.mjs` / `cdp_shot.mjs` は `pyodide` npm を解決できる場所(npm を入れたディレクトリの中)から
`node` で回す。Pyodide の wheel は初回だけ配布元から取って `PYO_CACHE` に置く(以後はオフライン)。
