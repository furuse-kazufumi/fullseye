# FullseyeEngine — 執行已設計管線的執行環境

[日本語](./ENGINE.md) · [English](./ENGINE.en.md) · [简体中文](./ENGINE.zh.md) · **繁體中文** · [한국어](./ENGINE.ko.md) · [Deutsch](./ENGINE.de.md)

`FullseyeEngine`(`engine.py`)是一個執行環境，用於**執行**在 Fullseye Studio 中**建立**的影像運算子管線——無論是從自己的程式碼還是從命令列呼叫。它相當於 MVTec 的 **HDevEngine**——用視覺化工具設計流程，再原封不動地從應用程式呼叫，這正是兩段式流程中後半段的角色。

- **設計(author)**：Fullseye Studio → `Save pipeline` 匯出 JSON([STUDIO_GUIDE.md](STUDIO_GUIDE.md))。
- **執行(execute)**：`FullseyeEngine.load("pipeline.json").run(frame)` —— **輸入 numpy 陣列，輸出 numpy 陣列**。不需要檔案 I/O，也不需要 GUI。

管線是由 `(op, a, b)` 組成的階段清單。引擎可以從 Studio 的 JSON、`--ops` 字串，或 Python 清單載入，檢查輸入輸出的 sort，調整每個階段的旋鈕，並對 numpy 影格執行(整體執行、執行到中途、或逐階段執行)。它也會進行結構驗證(未知運算子、sort 不一致)，這與 Studio 診斷面板中的檢查完全相同。

---

## 最簡單的用法

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # 各階段的中間結果(清單)
```

`FullseyeEngine` 與 `diagnose_stages` 皆從 `fullseye`(以及 `engine`)模組公開。

---

## 四種載入方式

| 建構方式 | 簽名 | 用途 |
|---|---|---|
| JSON 檔案 | `FullseyeEngine.load(path)` | 讀取 Studio 的 `Save pipeline` 輸出 |
| ops 字串 | `FullseyeEngine.from_ops(ops, a=0.5, b=0.5, name="pipeline")` | 逗號分隔字串，例如 `"gaussian,sobel_amp,otsu"`(共用旋鈕) |
| dict | `FullseyeEngine.from_dict(d, name="pipeline")` | 從含 `{"stages": [...]}` 的字典建構 |
| 階段清單 | `FullseyeEngine(stages=None, name="pipeline")` | 直接傳入 `[("gaussian",0.4,0.5), "otsu"]`(僅給名稱的階段預設 a=b=0.5) |

若 `from_dict` 缺少 `"stages"` 鍵會擲出 `ValueError`。`load` 會讀取 JSON 後傳給 `from_dict`，並以檔名(不含副檔名)作為 `name`。

---

## 方法一覽

| 方法 | 回傳值 | 說明 |
|---|---|---|
| `load(path)` *(classmethod)* | `FullseyeEngine` | 從 Studio 的 JSON 載入 |
| `from_ops(ops, a=0.5, b=0.5, name=…)` *(classmethod)* | `FullseyeEngine` | 從逗號分隔的 ops 字串載入(共用旋鈕) |
| `from_dict(d, name=…)` *(classmethod)* | `FullseyeEngine` | 從 `{"stages": [...]}` 載入 |
| `describe()` | `list[dict]` | 每個階段的 `{index, op, a, b, in_sort, out_sort, halcon, known}` |
| `op_names()` | `list[str]` | 各階段的運算子名稱 |
| `input_sort()` | `str \| None` | 管線所期望的輸入 sort(第一個已知 op 的 in_sort) |
| `output_sort()` | `str \| None` | 管線回傳的輸出 sort(最後一個已知 op 的 out_sort) |
| `validate()` | `list[dict]` | 結構性問題 `{index, op, severity, message}`。`[]` 表示健全 |
| `is_runnable()` | `bool` | 若所有階段都能解析為已知運算子(沒有 error)則為 `True` |
| `get_knobs(i)` | `tuple` | 階段 `i` 的旋鈕 `(a, b)` |
| `set_knobs(i, a=None, b=None)` | `self` | 修改階段 `i` 的旋鈕(可鏈式呼叫) |
| `run(image, upto=None, coerce=True)` | ndarray / float / dict | 執行管線。`upto` 僅執行第 0..upto 階段 |
| `run_stepwise(image, coerce=True)` | `list` | 每個階段執行後的中間結果(長度 = 階段數) |
| `run_file(in_path, out_path=None, upto=None)` | 原始結果 | 讀取影像、執行，若為點陣結果則可選擇儲存 |
| `to_dict()` | `dict` | `{"fullseye_pipeline": 1, "name", "stages"}` |
| `to_ops()` | `str` | 逗號分隔的 ops 字串 |
| `to_python()` | `str` | 單一 Python 函式的原始碼(與 Studio 的 Export 相同) |
| `save(path)` | `None` | 將 `to_dict()` 儲存為 JSON |
| `len(eng)` | `int` | 階段數 |

`diagnose_stages(stages)` 是一個不需要建立引擎即可驗證階段清單的函式，是 `validate()` 的實際實作。未知運算子的 `severity` 為 `"error"`，相鄰階段 sort 不一致時為 `"warning"`。

### 關於 sort(型別)

每個運算子都宣告輸入/輸出的 **sort**：`image`(gray H×W float64 [0,1]) / `region`(二值 {0,1}) / `color`(H×W×3 RGB) / `feature`(純量 float) / `contour`(XLD dict) / `volume`(3D 堆疊) / `any`(可與任何型別連接)。當相鄰階段的 out→in 不相符時，`validate()` 會發出警告(`any` 永遠視為相符)。

---

## Python 使用範例

### 先驗證再執行

```python
import fullseye

eng = fullseye.FullseyeEngine.from_ops("gaussian,sobel_amp,otsu")
problems = eng.validate()
if not eng.is_runnable():                      # 存在 error(未知 op)時停止
    raise SystemExit(problems)
result = eng.run(frame)                         # 回傳 region(二值)
```

### 執行到中途 / 逐階段執行

```python
mid = eng.run(frame, upto=1)                    # 執行到第 0..1 階段(gaussian → sobel_amp)
for i, s in enumerate(eng.run_stepwise(frame)):  # 各階段的中間結果
    print(i, eng.stages[i][0], getattr(s, "shape", s))
```

### 調整旋鈕後重新執行

```python
eng.set_knobs(0, a=0.3).set_knobs(2, a=0.4)     # 可鏈式呼叫
out = eng.run(frame)
```

### 檔案輸入輸出(在程式碼內完成)

```python
eng = fullseye.FullseyeEngine.load("edge.json")
result = eng.run_file("in.png", "out.png")      # 讀取 → 執行 → 若為點陣則儲存
```

### 儲存 / 匯出

```python
eng.save("edge.json")                           # 儲存為 JSON(可在 Studio 中重新開啟)
print(eng.to_ops())                             # "gaussian,sobel_amp,otsu"
print(eng.to_python())                          # 輸出為單一 Python 函式
```

`to_python()` 的輸出範例：

```python
import fullseye, numpy as np

def pipeline(frame):
    return fullseye.run_pipeline(frame, [
        ('gaussian', 0.500, 0.500),
        ('sobel_amp', 0.500, 0.500),
        ('otsu', 0.500, 0.500),
    ])
```

---

## CLI: `imgevolve.py run`

可以從命令列執行已儲存的管線(JSON 或 ops 字串)。其內部使用 `FullseyeEngine`。

```
py -3.11 imgevolve.py run <pipeline.json|ops> [inp] [--out PATH]
                          [--upto N] [--stepwise] [--describe] [--to-python] [--a A] [--b B]
```

| 參數 / 選項 | 意義 |
|---|---|
| `pipeline` | 管線 `.json`(Studio 的 Save pipeline)或逗號分隔的 ops 字串 |
| `inp` | 輸入影像(省略時僅可執行 `--describe` / `--to-python`) |
| `--out PATH` | 結果的儲存路徑(僅儲存點陣結果) |
| `--upto N` | 執行到第 0..N 階段 |
| `--stepwise` | 回報每個階段的結果，若指定 `--out` 則儲存為 `PATH_00`、`PATH_01`、… |
| `--describe` | 顯示管線的輸入輸出、各階段及驗證結果(未提供輸入影像時僅顯示後結束) |
| `--to-python` | 將管線輸出為 Python 函式 |
| `--a` / `--b` | 以 ops 字串建構時的共用旋鈕(預設 0.5) |

範例：

```powershell
# 僅確認結構(不需要影像)
py -3.11 imgevolve.py run edge.json --describe
#   pipeline 'edge': image -> region
#     0. gaussian      a=0.50 b=0.50   [image -> image]
#     1. sobel_amp     a=0.50 b=0.50   [image -> image]
#     2. otsu          a=0.50 b=0.50   [image -> region]

py -3.11 imgevolve.py run edge.json in.png --out result.png       # 執行並儲存
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png  # 儲存每個階段
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python   # ops 字串 → Python
```

包含未知運算子(error)的管線可以用 `--describe` 顯示，但執行時會停止並回報問題。

---

## 從其他專案呼叫(onocollo / evis / hillco 等)

由於 `fullseye` 的輸入輸出完全以 numpy 陣列完成，可以直接嵌入機器人/視覺管線中。如此便能實現 **設計在 Studio、執行在各專案** 的分工。

```python
import fullseye

# 在啟動時載入一次即可(輕量。僅保存 ops 的解析結果與旋鈕)
PIPELINE = fullseye.FullseyeEngine.load("assets/segment.json")

def perceive(frame):                            # frame: 自行準備的 float64 gray [0,1]
    seg = PIPELINE.run(frame)                   # 輸入 numpy，輸出 numpy(不需要磁碟)
    return seg
```

重點：

- **不需要檔案 I/O**：可以直接傳入從感測器/模擬器取得的 numpy 影格，並直接取得 numpy 結果。在嵌入式或 GPU 模擬環境中，即使沒有 I/O 後端也能運作。
- **輕量**：`load` / `from_ops` 只保存運算子名稱與旋鈕。繁重的運算只在呼叫 `run` 時才會發生。
- **版本無關**：由於管線 JSON 是資料，替換管線不會影響呼叫端程式碼。研究中的反覆迭代(在 Studio 中調整管線 → 更新 JSON)不會波及使用端。
- **若只需要單一運算子**，可直接呼叫 `fullseye.apply(frame, "otsu")`；若為多階段，可直接呼叫 `fullseye.run_pipeline(frame, [...])`(不經過引擎的輕量路徑)。

感知堆疊(stereo / terrain / flow / detect / registration / pose)同樣以 numpy 運作(如 `fullseye.disparity_map`)。使用範例請參見 `examples/`([../examples/README.md](../examples/README.md))以及 [PERCEPTION.md](PERCEPTION.md) / [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md)。

---

## 相關文件

- [STUDIO_GUIDE.md](STUDIO_GUIDE.md) —— 建立管線並匯出 JSON
- [GETTING_STARTED.md](GETTING_STARTED.md) —— 5 分鐘快速上手
- [INSTALL.md](INSTALL.md) —— 環境建置(包括嵌入式與最小配置)
