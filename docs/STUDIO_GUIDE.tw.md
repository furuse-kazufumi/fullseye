<!-- i18n-source-sha: a77086926760 -->
# Fullseye Studio 完全指南

[日本語](./STUDIO_GUIDE.md) · [English](./STUDIO_GUIDE.en.md) · [简体中文](./STUDIO_GUIDE.zh.md) · **繁體中文** · [한국어](./STUDIO_GUIDE.ko.md) · [Deutsch](./STUDIO_GUIDE.de.md)

**Fullseye Studio** 是一個類似 HDevelop 的視覺化流水線工作台。你可以搜尋並排列運算子，用兩個旋鈕滑桿調整參數，一邊縮放/平移檢視中間結果一邊逐段執行，最後把建好的流水線匯出成 `--ops` 字串 / Python / JSON。它的實體是 `fullseye` API 的一層薄 GUI 前端，流水線邏輯（`PipelineModel`）·Inspector（`inspect_result`）·範例集（`recipes`）皆不依賴 Qt，並且都有各自的單元測試。

本指南是把 `studio.py`（`build_window`）與實際程式碼對照後列出的功能清單。UX/設計的意圖請見 [STUDIO_UX.md](STUDIO_UX.md)，v14 感知面板的背景請見 [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md)。

---

## 啟動方式

需要 GUI extras（PySide6）（`pip install -e ".[gui]"`）。

```powershell
py -3.11 studio.py          # 直接從儲存庫根目錄執行
fullseye-studio             # 若已 pip install -e .，可用主控台腳本
```

啟動後會開啟一個 1320×860 的主視窗（標題: Fullseye Studio）。若存在 `assets/fullseye.ico`，會作為視窗/工作列圖示出現。初始狀態下已載入合成展示影像（`demo_image`，包含邊緣·斑點·漸層的 256×256 影像）。

---

## 畫面配置（3 個面板）

上方是**選單列**（File / Edit / View / Run / Help）與**品牌工具列**，下方是**狀態列**（滑鼠停留時的座標+像素值，`flash()` 的暫時訊息）。中央為左右分割的 3 個面板。

| 面板 | 區塊（QGroupBox） | 作用 |
|---|---|---|
| 左 | **SAMPLE PIPELINES** / **OPERATORS** | 載入範例、瀏覽運算子 |
| 中 | **PIPELINE** / **SELECTED STAGE · KNOBS** / **EXPORT & I/O** | 建構流水線、調整旋鈕、匯出 |
| 右 | **IMAGE** / **DISPLAY & PERCEPTION (v14)** / **ANALYSIS** | 結果顯示、色彩映射/感知、直方圖/Inspector |

初始分割寬度為 340 / 360 / 640 px，右側面板可伸縮。

---

## 左側面板: Operators 瀏覽器

### 範例流水線（SAMPLE PIPELINES）
從下拉選單中選擇 **20 個**現成配方（`recipes.py`）之一，流水線就會替換為該配方。例如「Edge — Sobel + Otsu」「Denoise — bilateral + unsharp」「Segment — blob / coin」「Count — blobs」「Texture — Gabor」等。是先跑起來再觀察內容的便利起點。

### 運算子瀏覽器（OPERATORS）
- **分類篩選**: 「all categories」+ 31 個分類（smoothing / edges / morphology / segmentation / features / texture / region / contour / color / frequency / restoration / 3d ……）。
- **搜尋欄**: 依運算子名稱·HALCON 別名·分類做部分比對過濾（附清除按鈕）。
- **清單**: 每行顯示 `name [in_sort → out_sort]`。**雙擊插入**。滑鼠停留會以工具提示顯示「名稱 / HALCON 別名 / 分類 / sort 轉換 / 旋鈕 a,b 的說明」。

插入位置為「目前選取階段的下一個位置」。若未選取任何階段，則附加到末尾。

---

## 中央面板: 建構流水線與逐段執行

### PIPELINE（階段清單）
每一行的格式為 `N. op (a=…, b=…) -> 結果摘要`，執行到該階段為止的結果狀態（image/region/feature 等）顯示在右側。

- **重新排序**: 拖曳該行（InternalMove）互換位置，或使用 **↑ Up / ↓ Down** 按鈕·**Ctrl+↑ / Ctrl+↓**。
- **刪除**: **Remove** 按鈕·**Del**。
- **逐步執行的 3 個按鈕**:
  - **⏮ Reset（Home）** — 顯示套用流水線之前的原始影像（逐步執行的起點）。
  - **Step ▶（Ctrl+→）** — 前進一段。
  - **Run all ▶▶（Ctrl+Enter）** — 一次顯示最終結果（主要強調色按鈕）。

選取某一階段後，該階段為止的中間結果會繪製在右側 IMAGE 面板，下方的 ANALYSIS（直方圖 / Inspector）也會同步更新。這相當於「逐步偵錯器」。

### SELECTED STAGE · KNOBS（旋鈕調整）
顯示所選階段的詳細資訊（`op_detail`: 名稱·`in → out` sort·分類·HALCON 別名），並透過 **2 個滑桿 a / b（0.00～1.00）** 調整。拖動數值會立即重新計算結果。未選取任何階段時，滑桿會被停用（不讓「沒有意義的旋鈕」處於可操作狀態的設計）。

旋鈕的意義因運算子而異（半徑 / 閾值 / σ / 方向等）。要調整的是什麼，可透過階段詳情標籤與工具提示確認。

### EXPORT & I/O
- **Export（ops string + Python）…（Ctrl+E）** — 將目前的流水線同時以 `--ops "…"` 字串與可獨立執行的 Python 函式兩種形式輸出到對話方塊（便於複製）。
- **Save pipeline…（Ctrl+Shift+S）** — 將流水線儲存為 JSON（`{"fullseye_pipeline": 1, "stages": [...]}`）。這個 JSON 就是 `FullseyeEngine.load` / `imgevolve.py run` 的輸入。
- **Open pipeline…（Ctrl+Shift+O）** — 載入已儲存的 JSON。

---

## 右側面板: 顯示·感知·分析

### IMAGE（結果檢視）
- **Load image…（Ctrl+O）** — 載入影像檔案作為基準影格（png/jpg/bmp/tif）。
- **Synthetic demo（Ctrl+D）** — 載入合成展示影像。
- **Save result…（Ctrl+S）** — 將目前顯示的結果儲存為 PNG。
- **縮放**: 滑鼠滾輪在游標位置縮放，拖曳平移。**Zoom +（Ctrl+=）/ Zoom −（Ctrl+-）/ Fit（Ctrl+0）/ 1:1（Ctrl+1）**。
- 當結果為純量 feature、contour 結果或尚未載入影像時，檢視中央會顯示提示訊息（不留空白）。
- 滑鼠停留時，狀態列會顯示 `x, y, value`（彩色影像則顯示 RGB）。

### DISPLAY & PERCEPTION (v14)
- **Display（色彩映射）** — 為 2D 結果著色以便顯示: `gray` / `shaded relief` / `height (color)` / 各種色彩映射（jet, viridis, turbo, magma, plasma, inferno ……）。
- **3D surface（Ctrl+3）** — 將目前結果以可旋轉的 3D 曲面顯示（僅在有 `QtDataVisualization` 時可用／best-effort）。方便檢視高度/深度圖。
- **感知面板（2 個影格）** — 用 **Load frame B…** 載入第 2 個影格，選擇模式後 **Run**:
  - `optical flow` — 用色相將兩個影格之間的密集光流視覺化。
  - `motion overlay` — 把移動區域疊加到原圖上。
  - `stereo depth` — 從立體視差估算深度並著色。
  - `stereo terrain` — 立體→點雲→地形高度圖，並著色。

  沒有影格 B 或尺寸不一致時，會在狀態列顯示錯誤並安全中止。

### ANALYSIS
- **Histogram** — 目前 2D 結果的亮度直方圖。
- **Inspector（variable / image / region）** — 依 sort 檢查結果。image/color 顯示 shape·min/max/mean·非有限值數量，region 顯示連通元件數·面積·最大區域，feature 顯示數值，contour 顯示輪廓數。二值區域時還會附上各區域的特徵表（`detect.feature_table`）。

---

## Command palette（Ctrl+P）

按 `Ctrl+P` 會開啟一個模糊搜尋對話方塊，可以**依名稱執行任意動作或任意運算子**。排序規則為前綴比對 > 單字前綴比對 > 部分比對（`palette_filter`，不依賴 Qt，已做單元測試）。動作（如 `▸ Open image`）排在前面，接著是全部運算子（如 `op: gaussian`），按 Enter 執行。僅用鍵盤即可完成到運算子插入為止的所有操作。

---

## 鍵盤快捷鍵

應用程式內可透過 **Help ▸ Keyboard shortcuts（F1）** 以表格顯示全部快捷鍵（自我文件化）。主要快捷鍵（來自 `studio.py` 的 `act_*` 定義）:

| 操作 | 快捷鍵 | 操作 | 快捷鍵 |
|---|---|---|---|
| Open image | `Ctrl+O` | Remove stage | `Del` |
| Synthetic demo | `Ctrl+D` | Move stage up / down | `Ctrl+↑` / `Ctrl+↓` |
| Save result | `Ctrl+S` | Clear pipeline | `Ctrl+Shift+Backspace` |
| Open pipeline | `Ctrl+Shift+O` | Zoom in / out | `Ctrl+=` / `Ctrl+-` |
| Save pipeline | `Ctrl+Shift+S` | Fit / Actual size (1:1) | `Ctrl+0` / `Ctrl+1` |
| Export | `Ctrl+E` | 3D surface | `Ctrl+3` |
| Quit | `Ctrl+Q` | Reset to start | `Home` |
| Command palette | `Ctrl+P` | Step forward | `Ctrl+→` |
| Keyboard shortcuts | `F1` | Run all | `Ctrl+Enter` |

每個動作無論從選單、工具列或按鈕觸發，都會呼叫同一個處理函式（一個動作、多個入口）。

---

## HDevelop `dev_*` 繪圖控制指令

與 HDevelop 相同，可以**從程式中控制繪圖行為**。在 Program 視窗的腳本中寫入 `dev_*` 行，
不會被解讀為影像階段，而是作為**顯示指令**，在 Apply 時生效
（`docs/HDEVELOP_DEV_OPS.md` 收錄了全部 43 個 `dev_*` 的完整說明）。

| 指令 | 效果 | 對應 UI |
|---|---|---|
| `dev_update_window ('off'|'on')` | 切換圖形視窗的自動更新 | View ▸ Display updates ▸ Graphics window |
| `dev_update_var ('off'|'on')` | 切換變數視窗的自動更新 | 同上 Variable window |
| `dev_update_pc ('off'|'on')` | 切換執行游標的更新 | 同上 Program counter |
| `dev_update_time ('off'|'on')` | 切換逐行處理時間顯示 | 同上 Operator timings |
| `dev_update_off ()` / `dev_update_on ()` | 一次將以上全部關閉 / 開啟 | 工具列 **Auto-update** 開關 |
| `dev_set_part (Row1, Col1, Row2, Col2)` | 設定顯示範圍（縮放/平移）·負值=整體 | 與滑鼠滾輪/Fit 併用 |
| `dev_set_lut ('gray'|'jet'|'viridis'…)` | 切換色彩映射（LUT） | View ▸ Display mode |
| `dev_clear_window ()` | 清空目前視窗 | — |
| `set_system ('thread_num', N)` | 設定 OpenCV 工作執行緒數（0=預設/全部） | Tools ▸ System settings |
| `set_system ('operator_timeout', ms)` | 軟性運算子逾時（在 Run status 中警告執行緩慢的階段） | 同上 |
| `dev_set_draw ('fill'|'margin')` | 切換 region 疊加層的填滿（fill）/ 輪廓（margin） | View ▸ Display mode = region overlay |
| `dev_set_color ('red'|'green'…)` | region 疊加層的顏色 | 同上 |
| `dev_set_line_width (N)` | margin 輪廓線寬（px） | 同上 |
| `dev_disp_text ('label', Row, Col)` | 在結果上方加入文字註解（於下次繪製/`dev_clear_window` 時消失） | — |
| `dev_open_window (Row, Col, W, H)` | **開啟並配置**圖形視窗並設為目前視窗（再次 Apply 會重新配置同一視窗=不會重複增生） | Ctrl+G / Window ▸ Graphics |
| `dev_set_window (Handle)` | 以控制代碼切換目前視窗 | 點擊視窗 |
| `dev_set_window_extents (Row, Col, W, H)` | 目前視窗的位置·大小（-1=維持現狀） | 拖曳視窗 |
| `dev_close_window ()` | 關閉目前視窗（常駐的主視窗受保護） | 視窗的 × |
| `set_system ('max_graphics_windows', N)` | 視窗數量上限（預設 256·所有路徑 fail-closed） | Tools ▸ System settings ▸ Windows |

**用途**: 在開頭放置 `dev_update_off ()`，可以在**沒有繪圖開銷**的情況下進行大量處理或大量編輯，
之後用 `dev_update_on ()` 一次更新到目前狀態（與 HDevelop 的效能技巧相同）。更新處於
關閉狀態時，狀態列右側會顯示 `updates off: …`，因此凍結狀態不會看起來「像是壞掉了」。
工具列的 **Auto-update** 開關也能達成相同的切換。

**注意**（誠實揭露）: 與流水線階段不同，`dev_*` **不遵循** `if`/`for`，會**無條件套用**
（即使寫在分支內部也會觸發）。請寫在頂層。不支援的 `dev_*` 會出現錯誤。

**動手試試**: 透過 **File ▸ dev_* visualization demo**，可以載入並執行一個實際使用 coins 影像 +
上述 `dev_*` 的 HDevelop 程式（分割→用青色輪廓+標籤顯示區域）。用於練習的範例影像位於
**File ▸ Sample images**（共 8 張，來源見 `studio_assets/sample_images/manifest.json`。
合成影像 = 自製作品／`coins`·`camera` 等 = 來自 skimage.data 的 BSD/公眾領域素材。可用
`tools/gen_sample_images.py` 重新產生）。

---

## 多語言支援(en / ja / zh，表格驅動)

介面語言可透過 **Tools ▸ Language / 言語 / 语言** 切換(會被記住)。對照譯文統一收錄在
**`studio_assets/i18n.json`** 這張表中，不需修改程式碼即可新增語言:

- `languages` — 語言清單(新增後會自動列在選單中。英語永遠是基準)
- `tooltips` — 工具提示對照譯文(以英文原文為鍵)
- `strings` — **選單·按鈕·對話方塊標籤的對照譯文**(以英文原文為鍵。2026-08-30
  新增。內建日語 40+ 項目，尚未翻譯的字串保留英文=優雅降級)
- `guide` — 快速指南本文(Shift+F2)

運算子說明若存在 `op_help/<name>.<lang>.html` 就會依語言顯示。誠實揭露:
執行過程中變化的狀態文字(`running…` / `PASS` 等)以及運算子附註本文目前
不在翻譯範圍內(運算子附註的英文化是與 docstring 雙語化配套的未來課題)。

## Python 編輯器與 IDE 功能(2026-08-30)

Studio 已經超越「只能從流水線呼叫程式碼」的階段，也可以作為**Python 開發環境**使用。

- **Python Editor**(File ▸ Python Editor… / 圖庫中的「Open in editor」): 具備語法標示+
  行號+自動縮排的**多分頁**編輯器(與 HDevelop 的主腳本+子腳本相似，
  可同時編輯多個腳本)。**F5 / Run** 會在子行程中執行目前分頁(儲存庫會加入 PYTHONPATH，
  因此 `import fullseye` 可直接使用。未儲存的緩衝區會以暫存副本方式執行，不強制 Save)。
  可從 **Samples ▾** 在新分頁中開啟全部隨附的可執行範例(以不帶路徑的方式開啟，
  因此不會誤覆寫出廠範例)。執行所用的直譯器可在 System settings ▸ Editor 中變更。
- **MDI 程式碼視窗**(圖庫中的「Open in window」): 可以把範例程式碼作為獨立視窗
  **任意排列多個**，方便選取片段複製(Window ▸ Tile/Cascade 同樣有效)。
- **執行控制**: 在行號欄點擊設定中斷點(=暫停執行)，用 **Continue** 按鈕從目前執行行
  繼續到下一個中斷點/末尾，於階段上按右鍵選擇 **Run from here** 可從任意行重新開始
  (與 **Run to here** 相對)。
- **變數監看**: 可在 Variables 視窗註冊任意運算式(如 `v.mean()` / `np.percentile(v, 99)` /
  `(v > 0.5).sum()`。`v`=選取的變數，`np`=numpy，`img`=輸入)，每當選取或流水線發生變化時
  都會**自動重新求值**。求值失敗的運算式會在該行顯示 ⚠(面板不會當掉)。在變數上
  **按右鍵 ▸ Inspect in popup…** 可立即彈出依型別分類的檢查結果+百分位數+數值預覽。
  已知的限制(誠實揭露): 由於監看運算式在 GUI 執行緒中同步求值，**非常耗時的運算式**
  (如對巨大陣列做全量掃描)會在此期間卡住介面。較重的統計運算應簡化運算式，
  或改到 Python Editor 中執行。
- **System settings**(Tools ▸ System settings… / Ctrl+,): 分類樹+分頁結構。
  Execution(執行緒數 / 逾時)·Windows(視窗數上限)·Display(預設 LUT / region 繪製)·
  Editor(字型大小 / 執行直譯器)。

## Export 與 Save/Open 的關係

在 Studio 中建好的流水線可以用 3 種形式帶走。

| 形式 | 匯出方式 | 使用時機 |
|---|---|---|
| `--ops` 字串 | Export（Ctrl+E） | 貼到 CLI 的 `imgevolve.py pipeline --ops "…"` / `run "…"` 中 |
| Python 函式 | Export（Ctrl+E） | 以 `fullseye.run_pipeline(...)` 的形式嵌入自己的程式碼 |
| JSON | Save pipeline（Ctrl+Shift+S） | 用 `FullseyeEngine.load(...)` / `imgevolve.py run pipeline.json` 執行 |

**設計在 Studio 完成，執行交給程式碼/CLI**這種相當於 HDevelop→HDevEngine 的流程，是透過 JSON 完成的。接收 JSON 並執行的一方請參見 [ENGINE.md](ENGINE.md)。

---

## 相關文件

- [STUDIO_UX.md](STUDIO_UX.md) — 設計系統·UX 改善的意圖與背景（設計視角）
- [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md) — 感知面板的內容（flow / stereo / terrain）
- [ENGINE.md](ENGINE.md) — 執行匯出的流水線
- [GETTING_STARTED.md](GETTING_STARTED.md) — 5 分鐘入門
