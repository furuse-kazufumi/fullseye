<!-- i18n-source-sha: bb5f3e736657 -->
# Fullseye Studio 完全指南

繁重處理不會凍結視窗。底部區域顯示目前階段與進度；停止要求會在下一個階段邊界確認。若執行期間設定有變，介面會標示顯示結果的世代，並可選擇查看舊設定的完成結果或用目前設定重新執行。

依處理目的搜尋時，候選項會分為適用於目前輸入、需要前處理和其他三組。候選項可在不新增處理階段的情況下試跑一次。執行失敗時，Problems 面板會顯示原因、位置與下一步操作，可重新選擇輸入、並排比較、查看詳細記錄、編輯參數或搜尋建議的處理階段。

[日本語](./STUDIO_GUIDE.md) · [English](./STUDIO_GUIDE.en.md) · [简体中文](./STUDIO_GUIDE.zh.md) · **繁體中文** · [한국어](./STUDIO_GUIDE.ko.md) · [Deutsch](./STUDIO_GUIDE.de.md) · [हिन्दी](./STUDIO_GUIDE.hi.md)

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
從下拉選單中選擇 **25 個**現成配方（`recipes.py`）之一，流水線就會替換為該配方。例如「Edge — Sobel + Otsu」「Denoise — bilateral + unsharp」「Segment — blob / coin」「Count — blobs」「Texture — Gabor」等。是先跑起來再觀察內容的便利起點。

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
| Image Viewer | `Ctrl+Shift+I` | Run a ledger op | `Ctrl+Shift+L` |
| Pipeline as code → editor | `Ctrl+Shift+E` | | |

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
**File ▸ Sample images**（共 16 張，來源見 `studio_assets/sample_images/manifest.json`。
合成影像 = 自製作品／`coins`·`camera` 等 = 來自 skimage.data 的 BSD/公眾領域素材。可用
`tools/gen_sample_images.py` 重新產生）。其中 5 張是外觀檢查（FA）用的場景，不是照片，而是由照明與反射的
物理計算（`illumdesign`）和 PoC 的成像模型算出：髮絲紋金屬上的刮痕、樹脂上的壓痕與異物纖維、雕刻的批號、
背光下的開孔板、焊道 X 光影像中的氣孔。每張都附有缺陷的真值遮罩（`<名稱>.truth.png`）與 manifest 中的說明，
各自對應一個「FA — ...」配方（測試確認它能找出缺陷），可用 `tools/gen_fa_samples.py` 重新產生。

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

## 可以拖放開啟的檔案(2026-10-03)

把檔案或資料夾**拖放到主視窗**,就會在合適的視窗中開啟(一次拖放多個檔案會開啟多個視窗)。完整清單見
**Help ▸ 可開啟的檔案(拖放)…**;那張表由 Studio 實際使用的副檔名常數產生,可能比本節更新。

| 拖放的內容 | 開啟方式 | 說明 |
|---|---|---|
| 影像(png / jpg / tif / webp / pgm / pfm / jp2 …)、資料夾 | 影像檢視器 | 清單、縮放、像素值、直方圖、「用作管線輸入」。資料夾開啟其中直接包含的影像 |
| `.py` | Python 編輯器(每個檔案一個分頁) | |
| `.json` | 管線 | |
| 點雲與網格(PLY / STL / PCD / OBJ / OFF / XYZ) | 3-D 檢視器 | **ASCII 與二進位皆可**(PLY 小端與大端,PCD 也支援 binary_compressed) |
| 3DGS(`.ply` / `.splat`) | 3-D 檢視器 | 顏色取球諧 DC 項;不透明度 < 0.05 的會隱藏 |
| 醫學體積資料(NIfTI / NRRD / MHA / DICOM) | 3-D 檢視器 | 需要 SimpleITK 等 |
| glTF(`.glb` / `.gltf`)、LiDAR(`.las` / `.laz`) | 3-D 檢視器 | 需要 pygltflib / laspy |
| 機器人(MJCF / URDF) | 3-D 檢視器 | `.xml` 僅當根元素為 `<mujoco>` 或 `<robot>`。需要 mujoco |
| 動作擷取(`.bvh`)、神經元形態(`.swc`) | 3-D 檢視器 | BVH 關節軌跡依時間著色 |
| 影片、動畫 GIF、HDF5 | 影片立方體 | |
| 事件相機 (x, y, t, p)(txt / csv / npy / npz) | 影片立方體 | 依內容辨識,轉成帶極性的影格 |
| `.npy` | 依形狀 | 2-D → 輸入影像,(N, 3 / 6) → 點雲,3-D → 體積資料 |
| Markdown、SVG | 文件檢視器 | |
| 音訊(wav / mp3 / flac / ogg …) | 音訊視窗 | 波形、頻譜圖、播放。WAV 以外需要 soundfile |
| 機器人模型 + qpos `.npy` (T, nq) 一起 | 機器人重播 | 滑桿與播放按鈕 |

## 試跑任意台帳 op(Tools ▸ 執行台帳 op…,Ctrl+Shift+L)(2026-10-03)

用**與每個參數型別相符的輸入框**執行型別化台帳中的 op(PIV、數學、駕駛、3-D 等約 1,700 個)的視窗。
在左側搜尋框輸入名稱或詞語,選取 op 後右側會出現參數表單。

- **資料輸入**可選「樣本(合成)」「目前影像」「上一次結果」。樣本是為該 op 合成、帶真值的輸入;「上一次結果」是
  **此視窗中最後執行的 op 的結果**,因此改選 op 就能把它傳給下一個 op(例:用 `ode_vector_field_grid` 產生流場,
  再把 `piv_quiver` 的輸入設為「上一次結果」,即得箭頭圖)。型別不符的輸入(把目前影像放進 flow2d 欄)不會執行,而是說明原因。
- **參數**:整數用整數框、實數用實數框、真假用核取方塊、有候選的用下拉、其餘用文字列。空欄為預設值,寫 `None` 即 None,
  序列寫 `1, 2, 3`。矩陣或字典樣本以 `<sample>` 標記保存。讀不懂的值**不會悄悄換回預設值**,會說明是哪個參數、為什麼。
- **執行**後以圖和內容(形狀、值域、欄位)呈現結果,並給出**做同樣事情的一行 Python**(「複製程式碼」可直接貼進腳本,相當於 MATLAB 的命令歷史)。
- 勾選「**值改變時自動重新執行**」後,每次改值都會重新執行。
- **一鍵進編輯器**:「插入到編輯器」把視窗中的程式碼(包括重建樣本、**原樣即可執行的腳本**)放到 Python 編輯器的游標處
  (沒有編輯器時會開啟;import 只在文件頂部補上缺少的行)。「把歷史作為腳本」依序彙整此視窗中所有成功的執行
  (用「上一次結果」串起的步驟會變成一串 `result = …`)。
- **也可以從編輯器出發**:在 Python 編輯器中於 `fs.ledger.` 或 `fs.` 之後輸入會彈出名稱候選(隨時可按 Ctrl+Space)。
  選取台帳 op 會插入**列出資料參數與必填參數的呼叫形式**,例如 `dem_slope(dem, cell_size=)`,游標停在第一個空位。
  在 op 名稱上按右鍵或按 Ctrl+Shift+L,即可開啟該 op 的執行視窗。
- **命令面板(Ctrl+P)**:輸入 `ledger: 名稱`,三步(Ctrl+P → 名稱 → Enter)即可開啟任意台帳 op 的視窗。
- **從正在看的結果出發**:在主畫面的影像上按右鍵 →「把管線作為程式碼送到編輯器」(Ctrl+Shift+E,讀取目前影像並執行的腳本)/「把此結果交給台帳 op…」(執行視窗的影像輸入已預選為目前結果)。

有些 op 用樣本跑不起來(這是各 op 樣本建構方式的限制;2026-10-03 實測 60 個中 27 個能直接用樣本執行)。
視窗本身沒有增加失敗,由「與把樣本直接傳給 op 的結果一致」這道門來確認。

### 將 CSV 欄位指派給表格運算

型別輸入為 `table` 時，可在既有臺帳執行器選擇 **CSV 檔案…**。每個角色只能從實際欄名選取；量具 R&R 使用
`part / 零件 ID`、`operator / 操作者`、`value / 測量值`。檢查會顯示列數、相異鍵、缺失值與重複數。重複數不等時，
會在執行前列名拒絕，不會自動修補。對應按運算與標頭簽章保存，只在相同格式重用。CSV 不會被修改或改名。

### 結果檢視的顯示方式

| 結果 | 顯示方式 |
|---|---|
| `flow2d` `(2, h, w)` | 色相 = 方向、亮度 = 速度的色輪圖上疊加箭頭圖(最長箭頭 = 間距的 0.9 倍) |
| 一維數列 | 折線(MATLAB 的 `plot(y)`) |
| 表(dict) | 等長的數值欄疊成折線;若有 `t` / `x` / `freq` … 欄則作橫軸 |
| `(h, w, 4)` / `(h, w, 1)` / 複數 | 合成到白底的 RGB / 灰階 / 絕對值 \|z\| |
| 空陣列、4 維以上 | 以文字給出形狀和值域(不把第一個值當作「純量」) |

## 結果快取、需確認標記與輸入影像參照(2026-10-19)

- **逐段結果快取**:拖動旋鈕時,只重新計算該段及其後的各段,前面的結果直接沿用。每段列的右端,本次計算的段顯示 `⟳ calc`,取自快取的段顯示 `↺ cache`。更換影像、調整順序或刪除某段時,從受影響的段起的快取會被捨棄。每段只保留最新的一份結果,反覆拖動旋鈕也不會增加。
- **需確認標記(⚠)**:「是否執行成功(ran)」與「結果是否有效(valid)」分開記錄。結果含 NaN / Inf、為空、或所有像素相同時,該段列會帶 `⚠`,原因顯示在提示與 Problems 中(與 `✕` 錯誤是不同的列)。若結果是帶有 `converged` / `valid` / `ok` 等欄位的表,則照錄其申報。沒有有效性資訊的結果顯示為「妥當性未判定」,不會顯示 OK。Run all 之後狀態列顯示「執行:完成 / 結果:需確認(原因)」或「執行:完成 / 結果:未判定有效性」。Studio 只**回報**,不會修復 op 的數值問題,也不會改動任何值。
- **輸入影像參照**:Save pipeline 會把已載入影像檔的參照(原樣路徑、檔案 sha256、shape、dtype)寫入 JSON 的 `input`。開啟時,檔案存在且 sha256 一致則靜默重新載入;檔案存在但內容已變,則載入並在 Problems 顯示 "input file changed since save";找不到則保留目前影像,並顯示 "input not found: 路徑"(會嘗試 `.json` 同資料夾下的同名檔案作為重新連結的候選)。沒有 `input` 的舊 JSON 與以前完全一樣地讀取。
- **階段縮圖(2026-10-20)**: 每個階段列左側顯示該階段結果的小圖(約 48×36 像素):區域為二值圖,輪廓為線條,表或純量為表示其種類的符號。小圖只由快取中既有的結果產生,不會為了畫圖而重新計算階段。尚未計算的階段顯示「未計算 / not computed」;先前算過但旋鈕或影像已改變的階段顯示「再計算が必要 / recompute needed」,不會把舊圖當成目前結果。每個階段只保留一個很小的陣列,因此大影像下記憶體幾乎不增加。 重建清單本身不會計算任何階段(只在執行、單步或旋鈕拖曳結束時計算)。 _(ja)_
- **階段輸入→輸出面板(Window ▸ Panels ▸ Stage in → out)**: 選取某個階段後,以相同的顯示模式與數值範圍並排顯示它的輸入與輸出,下方一行給出差異:區域/標籤結果為「區域數 128 → 37」,影像為平均值、σ、最小值、最大值的前後變化,表為列數與欄數,輪廓為條數。面板關閉時不做任何計算。
- **旁路(Ctrl+B / 階段右鍵選單)**: 暫時關閉所選階段而不刪除它。該階段原樣傳遞輸入,在清單中顯示為灰色並帶刪除線。復原記錄顯示為「bypass」,與「remove」不同。旁路以階段的第 4 個元素 `true` 存入專案檔(關閉時不寫入任何內容,所以不使用旁路的檔案與以前逐位元組相同);它是快取鍵的一部分,因此切換後從該階段起重新計算。Python 匯出只保留 `# bypassed: op` 註解列,匯出的腳本結果與畫面一致。在 Program 文字中,旁路階段是一列 `# bypassed: op (a, b)`,“Apply” 會把它讀回來,標記因此得以保留。
- **相鄰取值對比列(旋鈕下方的 "Try nearby values")**: 把所選階段在目前旋鈕值上下相鄰的 3 個(或 5 個)取值時的結果以小圖並排顯示。取值間隔取規格中的步長與取值範圍的 1/10 中較大者(對數刻度規格則為等比);整數或選項型旋鈕取相鄰的值,且不會超出允許範圍。只在展開時計算,並從上一階段的快取結果出發,**只執行該階段**(每個候選執行一次,其他階段不執行)。所有小圖使用同一顯示範圍,只保存小圖,因此大影像也幾乎不增加記憶體。點擊小圖不會改變任何東西;點擊所選小圖下方的 "Adopt this value",才會沿與滑桿相同的路徑寫入該值,復原記錄為一步(如 "change blur σ")。若在主影像上以 Shift + 拖曳標出了區域(Shift + 點擊取消),該列只繪製該區域。
- **固定 A、與 B 比較(工具列 "Pin as A" / Ctrl+Shift+A,Window ▸ Panels ▸ A / B)**: 凍結階段清單(含旁路標記)、輸入參照、最終結果與顯示設定。結果是一份唯讀副本,之後無論怎樣執行都不會改變。最多保留兩個,第三個會捨棄最舊的(狀態列會提示)。A / B 面板把 A 與即時結果 B 以並排、滑動(拖曳分界線)、閃爍(預設 500 ms,關閉面板即停止)或差異(絕對值 / 帶符號,0 為白色的對稱色圖 / 比值 log2)顯示。A 與 B 使用由 A ∪ B 決定的同一顯示範圍。下方 "What changed" 依序列出相對 A 新增、刪除、修改(舊值 → 新值,帶單位)、旁路以及輸入的變化。"Restore A" 還原 A 的流程(復原算一步),"Adopt B" 捨棄 A,"Keep both" 把 B 固定為第二個快照。專案檔只在 `pinned` 中儲存階段、輸入、顯示與備註(不儲存陣列),開啟時重新計算陣列;若無法重新計算,固定仍保留,Problems 中顯示 "cannot recompute A"。沒有 `pinned` 的舊檔照常開啟。
- **縮放、平移與游標同步**: "Stage in → out" 面板與 A / B 面板中的影像一起縮放、平移;游標移到其中一幅上時,其他幅的同一像素處顯示十字線。在 A / B 面板勾選 "sync the main view too",主影像也加入同步。


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
