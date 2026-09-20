<!-- i18n-source-sha: c70ba3c329f3 -->
# 快速上手（5 分鐘跑起來）

[日本語](./GETTING_STARTED.md) · [English](./GETTING_STARTED.en.md) · [简体中文](./GETTING_STARTED.zh.md) · **繁體中文** · [한국어](./GETTING_STARTED.ko.md) · [Deutsch](./GETTING_STARTED.de.md)

## 哪個入口適合你的工作(3 個入口)

Fullseye 涵蓋範圍很廣，如果不能先決定「第一個要打開哪一個」，就會卡住。這裡列出的
不是新寫的展示範例，而是**關卡(gate)每次都會執行的範例**(一旦失敗 CI 就會變紅)。

| 入口 | 適合對象 | 5 分鐘:先跑起來 | 30 分鐘:深入內部 | 半天:用自己的資料 |
|---|---|---|---|---|
| **可解釋的外觀檢測** | 檢測·品質保證 | `py -3.11 examples/poc_solder_fillet_aoi.py` 錫膏(fillet)AOI | `py -3.11 examples/poc_fabric_defect.py` 把漏檢與誤判分開計算 | [CAPABILITIES.md](CAPABILITIES.md) 的「發現」→ 在 Studio 中用自己的影像 |
| **面向機器人的 3-D** | 機器人·3-D 量測 | `py -3.11 examples/perception_pipeline.py` 立體視覺→深度→點雲→可通行性 | `py -3.11 examples/grasp_pose.py` 將點雲對齊模型，得到 6-DoF 姿態與夾取方向 | [EXAMPLES_3D.md](EXAMPLES_3D.md) → 輸入自己的點雲/網格 |
| **以物理為基礎的非破壞檢測** | X 光·光學·計量 | `py -3.11 examples/ct_reconstruction.py` 投影→重建→尺寸(mm)與缺陷數 | `py -3.11 examples/poc_ct_void_morphology.py` 為什麼「合格/不合格」這一個數字對形狀是盲目的 | [CAPABILITIES.md](CAPABILITIES.md) 的「成形」→ 用自己的體積資料 |

每個範例都附有**真值**(封閉解或合成資料)。一律並列給出零點(什麼都不做時)的結果，
所以你可以自行判斷是否真的「有效」。目前驗證到什麼程度的台帳在
[MATURITY.md](MATURITY.md) —— 這不是手寫的，而是從實際執行的關卡與真實資料的有無統計出來的。

---

這是讓 Fullseye(內部代號 imgevolve)以最短路徑跑起來的指南。依照**安裝 → 建立第一個流水線 → 執行 → 檢視結果**的順序，走一條不會卡住的路線。更詳細的環境建置請見 [INSTALL.md](INSTALL.md)，Studio 的完整功能請見 [STUDIO_GUIDE.md](STUDIO_GUIDE.md)，從程式呼叫請見 [ENGINE.md](ENGINE.md)。

Fullseye 是一個**以 numpy 陣列作為輸入輸出的影像處理運算子函式庫**，其上搭載了 **類似 HDevelop 的視覺化流水線設計環境（Fullseye Studio）** 與 **執行期環境（FullseyeEngine）**。用 HALCON/HDevelop 的說法來說，就是「在 HDevelop 中建立流程，在 HDevEngine 中從自己的應用程式呼叫」這種兩段式架構，原封不動用 Python + numpy 重現出來。

---

## 1. 安裝（1 分鐘）

前提: **Python 3.11**（Windows 用 `py -3.11`，Linux 用 `python3.11`）。

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .          # 僅核心（numpy + scipy。所有 op 都看得到，需要 optional backend 的 op 呼叫時會指出缺少的 extra）
```

核心**只靠 numpy 與 scipy** 就能運作。OpenCV / scikit-image / Pillow 等額外後端都是選配，即使沒有安裝，也只是該後端專屬的運算子會被停用而已（優雅降級）。實務上至少需要 OpenCV 或 Pillow 來讀寫影像檔案，建議額外安裝下列其中之一。

```powershell
py -3.11 -m pip install -e ".[opencv]"    # 影像 I/O + 來自 OpenCV 的運算子
py -3.11 -m pip install -e ".[all]"       # 全部後端（opencv, skimage, pil, wavelets, gpu, extra）
py -3.11 -m pip install -e ".[gui]"       # 若要使用 Fullseye Studio（PySide6）
```

extras 的清單與說明整理在 [INSTALL.md](INSTALL.md)。要使用 GUI 需要 `[gui]`（或 `[all]` + `[gui]`）。

> 也可以不安裝直接試用。把儲存庫根目錄（`<path-to-fullseye>`）設為工作目錄，並將該路徑加入環境變數 `PYTHONPATH`，`import fullseye` 就能運作。不過 `fullseye` / `fullseye-studio` 這兩個指令（主控台腳本）只有執行過 `pip install -e .` 之後才能使用。

---

## 2. 先執行 1 個運算子（Python）

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

edges = fullseye.apply(frame, "sobel_amp")     # image → image（梯度強度）
seg   = fullseye.apply(frame, "otsu")          # image → region（0/1 二值）
n     = fullseye.apply(seg,   "count_obj")     # region → feature（物件數＝Python float）
print(n)                                       # 例如: 316.0
```

> **參數順序是 `apply(image, name, a, b)`** — 第 1 個參數是陣列，第 2 個參數是運算子名稱。反過來傳的話，
> 從 0.1.9 起會以 `TypeError: ... arguments look swapped` 中止（0.1.8 之前會出現 numpy 的
> 「truth value of an array is ambiguous」這種不相關的錯誤）。
> `a`/`b` 必須是 0..1 之間的有限值。字串·`None`·NaN 會立即觸發 `TypeError`/`ValueError`，超出範圍的值會被截斷並記錄到台帳中。

- `apply(image, name, a=0.5, b=0.5)` 用來套用**單一運算子**。`name` 可以是**運算子名稱**（例如 `gaussian`），也可以是**HALCON 別名**（例如 `gauss_filter`），兩者都能被解析。
- `a`、`b` 是每個運算子擁有的 **2 個旋鈕（0.0～1.0）**。意義因運算子而異（半徑、閾值、σ 等）。
- 輸出的型別（sort）由運算子決定: `image`（灰階）/ `region`（二值）/ `feature`（純量 float）/ `color`（RGB）/ `contour`（XLD）/ `volume`（3D）。
- **失敗時會怎樣**（自 2026-09-03 起）: 預設 `on_error="fallback"` 之下，即使運算子內部失敗，也會回傳與型別相符的無害值（例如影像會回傳輸入的副本），並且**每個運算子只會跳出一次** `FullseyeFallbackWarning`。什麼發生了多少次備援，可用 `fullseye.fallbacks()` / `fullseye.fallback_counts()` 確認。傳入 `on_error="raise"`（或設定環境變數 `FULLSEYE_ON_ERROR=raise`）則會變成**fail-closed**，運算子真正的例外、dtype 違規（整數/bool 影像）、GPU 核心失敗都會原封不動拋出。**sort 不一致只會被部分偵測到**（例如把 RGB `(H,W,3)` 傳給 2-D 運算子會被當作體積資料處理，即使在 `raise` 模式下也不會報錯 —— 見 `docs/KNOWN_ISSUES.md` #32-4）。在 CI 或驗證中建議使用 `raise`。
- **多輸入運算子**（`add_image` / `union2` 等，在 `list_ops()` 中 `tier == "nary"`）需要**以清單形式**傳入輸入: `fullseye.apply([img1, img2], "add_image")`。
- **樣板比對**（`ncc_locate` / `shape_locate`）透過 `template=` 傳入要尋找的影像: `corr, row, col = fullseye.apply(img, "ncc_locate", template=patch)`（傳回的 row/col 是比對位置的**中心**）。沒有樣板時會傳回 no-match 的 `[0, 0, 0]`。

可以用下面的方式查詢有哪些運算子。

```python
fullseye.op_names()                 # 全部已註冊的運算子名稱（860 個，截至 2026-09-03）
fullseye.list_ops(search="edge")    # 依名稱 / HALCON 名稱 / 分類做部分比對搜尋
fullseye.list_ops(sort="region")    # 依輸入 sort 篩選
fullseye.categories()               # 47 個分類
```

---

## 3. 建立流水線（串接多個運算子）

把多個運算子依序串接起來就是「流水線」。陣列會依序流經每一段並傳回最終結果。

```python
# 所有階段共用同一組 a, b（與 CLI 相同的形式）
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])

# 每個階段想用不同旋鈕時（用 (name, a, b) 元組指定）
out = fullseye.run_pipeline(frame, [("gaussian", 0.3, 0.5), ("otsu", 0.4, 0.5)])
```

這是「smooth（平滑）→ 邊緣強度 → Otsu 二值化」，從影像產生二值邊緣圖的典型範例。系統內建了 **20 個**可直接使用的組合(範例配方)。

```python
import recipes
recipes.names()                                   # 配方名稱一覽
stages = recipes.stages("Edge — Sobel + Otsu")    # [(op, a, b), ...]
out = fullseye.run_pipeline(frame, stages)
```

---

## 4. 視覺化建構（Fullseye Studio）

不用寫程式，搜尋並排列運算子，用滑桿調整旋鈕，一段一段執行並即時檢視中間結果來建構流水線。需要 GUI extras（`pip install -e ".[gui]"` = PySide6）。

```powershell
py -3.11 studio.py          # 或者已安裝的話: fullseye-studio
```

由 3 個面板構成。

- **左側（Operators）**: 依分類 / 搜尋縮小運算子範圍，**雙擊插入**（Edit ▸ Focus operator search = **Ctrl+F** 定位到搜尋欄）。範例流水線也可以從這裡載入。**Insert（＋）與 HDevelop 的運算子視窗相同**，在流水線中新增一段的同時，會在 Program 視窗的游標位置寫入一行 `op (a, b)`（數值為 `repr` 的全精度。若 Program 中有尚未套用的手動編輯，只會插入這一行，需要 Apply 才會生效）。
- **中央（Pipeline）**: 已排列階段的清單。可拖曳或用 Ctrl+↑/↓ 調整順序，調整選取階段的**旋鈕 a / b**。旋鈕永遠是 0..1 的值，但**對於有專屬顯示規格的運算子（`param_specs.py`）可依實際單位操作** — `gaussian` 用 σ（px，滑桿 + 帶單位的數值輸入框），`median` 用 3/5/7/9 的下拉選單選核心大小，`reg_erode` 用整數輸入框指定疊代次數，`aug_barrel` 的 b 用「pincushion」核取方塊表示。右側的 0..1 數值輸入框永遠是原始值（供精確輸入）。這些規格是依 ops.py 中的換算公式（如 `0.3 + 2.7·a`）手寫，並透過測試與實作互相核對（`tests/test_studio_params.py`）。沒有規格的運算子仍是原本的 2 個 0..1 滑桿。階段清單也會以顯示單位書寫（`gaussian (blur σ=1.08 px, b=–)`）。**Reset（Home）→ Step（Ctrl+→）→ Run all（Ctrl+Enter）**可逐段執行，也可以一次執行到底。
- **右側（Image / Perception / Analysis）**: 縮放/平移顯示結果影像、直方圖、Inspector（檢查 image / region / feature 的值）、v14 的感知面板（光流 / 立體深度等）。**在影像檢視上按右鍵**可執行 Fit / 1:1 / Zoom / Save result / Save view as shown / Copy / Display mode / 3D surface（與選單相同的動作）。另外開啟的繪圖視窗也附有 Fit·1:1·±·Save 的小工具列與相同的右鍵選單，3-D 檢視器（Ctrl+4）可透過右鍵切換 Reset view / 第一人稱(透視) / Wireframe / Save screenshot。

建好的流水線可用 **Export（Ctrl+E）** 匯出為 `--ops` 字串或 Python 程式碼，也可用 **Save pipeline（Ctrl+Shift+S）** 儲存為 JSON。完整功能與快捷鍵請見 [STUDIO_GUIDE.md](STUDIO_GUIDE.md)，應用程式內按 **F1** 即可顯示一覽表。

---

## 5. 執行已儲存的流水線（CLI / 程式）

在 Studio 中用 `Save pipeline` 儲存的 JSON(或 `--ops` 字串)，可以原封不動對檔案執行。這就是相當於 HDevEngine 的「不需重寫已設計好的內容即可執行」的路徑。

```powershell
# 檢查已儲存 JSON 的 I/O 與各階段（不使用影像，僅做結構檢查）
py -3.11 imgevolve.py run edge.json --describe

# 套用到影像並儲存結果
py -3.11 imgevolve.py run edge.json in.png --out result.png

# 逐段儲存結果（result_00.png, result_01.png, ...）
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png

# 把流水線匯出為獨立的 Python 函式
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python
```

從程式執行時使用 `FullseyeEngine`（詳見 [ENGINE.md](ENGINE.md)）。

```python
import fullseye
eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # 各階段的中間結果（清單）
```

---

## 6. 用 CLI 逐一套用

想直接處理影像檔案時，用 CLI 更方便（影像 I/O 需要 OpenCV 或 Pillow）。

```powershell
py -3.11 imgevolve.py ops --search edge                    # 搜尋運算子
py -3.11 imgevolve.py has gauss_filter                      # 該 HALCON 名稱是否已實作 + 呼叫方式
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py pipeline in.png out.png --ops "gaussian,sobel_amp,otsu"
```

`apply` / `pipeline` 在各階段共用相同的 `--a` / `--b`。想在每個階段使用不同旋鈕時，請使用上面的 `run_pipeline`（Python）或 Studio。

---

## 遇到問題時

| 症狀 | 處理方式 |
|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | 執行 `pip install -e .`，或把儲存庫根目錄加入 `PYTHONPATH` |
| 沒有 `fullseye` / `fullseye-studio` 指令 | 主控台腳本是透過 `pip install -e .` 註冊的。未安裝時用 `py -3.11 imgevolve.py ...` / `py -3.11 studio.py` |
| Studio 無法啟動 | 未安裝 GUI extras。`pip install -e ".[gui]"`（PySide6） |
| `apply` / `pipeline` 出現 `cannot read ...` | 需為影像 I/O 安裝 OpenCV（`[opencv]`）或 Pillow（`[pil]`） |
| 額外後端的運算子顯示為「unknown」 | 該後端尚未安裝。追加 `.[skimage]` `.[wavelets]` `.[extra]` 等 |

更詳細的疑難排解請參考 [INSTALL.md](INSTALL.md)。

## 接下來閱讀

- **[INSTALL.md](INSTALL.md)** — 環境建置完全指南（extras 的使用區分、Windows/Linux 安裝程式、最小配置·嵌入）
- **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** — Fullseye Studio 完全指南
- **[ENGINE.md](ENGINE.md)** — FullseyeEngine（設計 → 執行）指南
- **[README.md](README.md)** — 文件索引
