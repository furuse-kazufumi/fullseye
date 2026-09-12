<!-- i18n-source-sha: fb18d30eac9c -->
# 安裝 / 環境建置完整指南

[日本語](./INSTALL.md) · [English](./INSTALL.en.md) · [简体中文](./INSTALL.zh.md) · **繁體中文** · [한국어](./INSTALL.ko.md) · [Deutsch](./INSTALL.de.md)

這是一份從開發機到嵌入式 Linux、依用途建置 Fullseye(工作代號 imgevolve)的指南。若只想在 5 分鐘內跑起來，[GETTING_STARTED.md](GETTING_STARTED.md) 是比較快的捷徑。

Fullseye 的設計方針是 **「僅靠 numpy + scipy 即可運作的核心」+「所有重量級相依套件皆為選用」**。即使沒有額外的後端，也只是該後端專屬的運算子會被停用，核心永遠能運作(優雅降級)。

---

## (a) 前提條件

| 項目 | 需求 |
|---|---|
| Python | **3.11**(`pyproject.toml` 中 `requires-python = ">=3.10"`；開發與驗證使用 3.11) |
| 執行指令 | Windows: `py -3.11` / Linux: `python3.11` |
| 核心相依套件 | `numpy>=1.23`, `scipy>=1.9`(`pip install -e .` 會自動安裝) |
| 作業系統 | Windows 10/11、Linux(含嵌入式)。只要 Python 能執行，macOS 也可以 |

---

## (b) pip install(extras 的意義與用法)

在儲存庫根目錄下進行可編輯安裝(editable install)。

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .            # 僅核心(numpy + scipy，約 885 個運算子)
```

額外的後端透過 **extras** 選擇(實際定義在 `pyproject.toml` 的 `[project.optional-dependencies]` 中)。

| extras | 新增的相依套件 | 啟用的內容 |
|---|---|---|
| `opencv` | `opencv-python>=4.6` | 影像檔案 I/O(`apply`/`pipeline` CLI 必需)、`cv_*` 系列運算子 |
| `skimage` | `scikit-image>=0.20` | `sk_*` / `xsk_*` 系列(眾多自動產生運算子的基礎) |
| `pil` | `Pillow>=9` | 影像 I/O 的備援方案、`xpil_*` 系列(emboss/posterize/solarize 等) |
| `wavelets` | `PyWavelets>=1.4` | 小波系列(VisuShrink/子頻帶/小波封包等) |
| `gpu` | `torch>=2.0`, `kornia>=0.7` | GPU 批次後端(`accel.py`/`bench.py`)、`xkor_*`(kornia)系列 |
| `extra` | `mahotas>=1.4`, `SimpleITK>=2.2` | `xsitk_*`(curvature flow 等)、源自 mahotas(Zernike/pftas 等) |
| `gui` | `PySide6>=6.5` | **Fullseye Studio**(`studio.py` / `fullseye-studio`) |
| `all` | 上述除 GUI 以外的全部(opencv, skimage, pil, wavelets, gpu, extra) | 全部運算子與後端 |

使用建議：

```powershell
# 實務上常用的最小配置 + 影像 I/O(不需要 GUI，以程式碼/命令列為主)
py -3.11 -m pip install -e ".[opencv]"

# 也要使用 GUI(Studio)
py -3.11 -m pip install -e ".[opencv,gui]"

# 完整配備(含 GUI。all 不含 GUI，因此需另外加上 gui)
py -3.11 -m pip install -e ".[all,gui]"

# 也想嘗試 GPU 批次路徑(需要支援 CUDA 的 torch)
py -3.11 -m pip install -e ".[gpu]"
```

> `all` **不包含 `gui`**(GUI 用途不同，單獨劃分)。若要使用 Studio，請務必明確加上 `gui`。

安裝成功後，以下 **兩個主控台指令稿** 即可使用(`[project.scripts]`)。

| 指令 | 實體 | 對應的直接執行方式 |
|---|---|---|
| `fullseye` | `imgevolve:main`(CLI) | `py -3.11 imgevolve.py ...` |
| `fullseye-studio` | `studio:main`(GUI) | `py -3.11 studio.py` |

若不安裝也想嘗試，只要將儲存庫根目錄加入 `PYTHONPATH`，`import fullseye` 即可運作(但無法使用主控台指令稿)。

```powershell
$env:PYTHONPATH = "<path-to-fullseye>"
py -3.11 -c "import fullseye; print(fullseye.version())"      # 0.1.0
```

---

## (c) Windows 安裝程式

執行 `install\install.ps1` 可一次完成環境建置與桌面整合(PowerShell)。

```powershell
cd <path-to-fullseye>
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

執行此安裝程式後，大致會進行以下動作。

- 確認 Python 3.11 是否存在
- 透過 `pip install -e .`(含所需 extras)安裝 Fullseye
- **建立 Fullseye Studio 捷徑(`Fullseye Studio.lnk`)** — 透過 `pyw.exe` 註冊，使其可在不彈出主控台視窗的情況下啟動，並附上 `assets\fullseye.ico` 圖示

之後可從開始功能表 / 桌面捷徑啟動 Studio。

> 若因執行原則而被阻擋，請加上 `-ExecutionPolicy Bypass`(已包含在上述指令中)。

---

## (d) Linux 安裝程式 + `.desktop` 啟動器

執行 `install/install.sh` 可在 Linux 環境中完成同等建置。

```bash
cd /path/to/imgevolve
bash install/install.sh
```

執行此指令碼後，大致會進行以下動作。

- 確認 `python3.11` 是否存在
- `pip install -e .`(含所需 extras)
- **建立 `.desktop` 啟動器** — 註冊以 `assets/fullseye.ico` 為圖示的桌面項目，以便從應用程式選單啟動 Fullseye Studio

之後可從桌面環境的應用程式清單啟動 Studio。

---

## (e) 最小配置 / 嵌入式(embedded Linux)

Fullseye 的核心設計成 **僅靠 numpy + scipy** 即可運作。對於不需要 GUI、GPU、重量級後端的嵌入式用途，只安裝核心就已足夠。

```bash
python3.11 -m pip install -e .        # 僅 numpy + scipy。不需要 GUI/torch/opencv
```

嵌入式用法要點：

- **輸入輸出完全以 numpy 陣列完成**。完全不需要檔案 I/O，可直接傳入從感測器/攝影機取得的 numpy 影格。

  ```python
  import fullseye, numpy as np
  frame = get_camera_frame()                       # 自行取得的 float64 gray [0,1]
  seg = fullseye.apply(frame, "otsu")              # 不需要寫入磁碟
  out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
  ```

- **需要檔案 I/O 時**(`fullseye.load` / `fullseye.save`、`imgevolve.py run`、examples)，只要具備 **OpenCV 或 Pillow 其中之一** 即可運作(`imgio` 會自動回退)。若嵌入式場景以輕量為優先，Pillow(`[pil]`)體積較小。
- 可以做到 **設計在開發機、執行在嵌入式機** 的分工。在開發機的 Studio 中建立管線並匯出 JSON，嵌入式機上只需 `FullseyeEngine.load("pipeline.json").run(frame)` 即可執行(不需要 GUI)。詳情請參見 [ENGINE.md](ENGINE.md)。
- **感知堆疊**(stereo / terrain / flow / detect / registration / pose)同樣僅靠 numpy + scipy 運作(如 `fullseye.disparity_map`)。在機器人/視覺用途中無需額外相依套件即可使用。

> GPU(`torch`)終究只是 **批次加速的選用項目**。嵌入式的單張影像處理不需要它，即使不安裝，所有運算子也都能在 CPU 上運作。

---

## (f) 常見問題

| 症狀 | 原因 | 處理方式 |
|---|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | 未安裝 / 路徑未設定 | 執行 `pip install -e .`，或將儲存庫根目錄加入 `PYTHONPATH` |
| 找不到 `fullseye` / `fullseye-studio` 指令 | 主控台指令稿未註冊 | 執行 `pip install -e .`。若不安裝，可用 `py -3.11 imgevolve.py` / `py -3.11 studio.py` |
| Studio 啟動時出現 PySide6 的 ImportError | 未安裝 GUI extras | `pip install -e ".[gui]"` |
| `apply` / `pipeline` 出現 `cannot read <path>` | 沒有影像 I/O 後端 | `pip install -e ".[opencv]"`(或 `[pil]`) |
| `read_image` / `write_image`(API)出現 cv2 的 ImportError | 這兩者 **專屬於 OpenCV** | `pip install -e ".[opencv]"`。若只想用 Pillow，請改用 `fullseye.load` / `fullseye.save` |
| `list_ops` 中缺少預期的運算子 / `has` 顯示 unknown | 對應後端未安裝 | 加入相應的 extras(`skimage`/`wavelets`/`extra` 等) |
| GPU 批次(`accel`/`bench`)在 CPU 上很慢 | `torch` 為 CPU 版本 | GPU 上請使用 `--device cuda`。CPU 上單純的逐點運算因轉換成本而處於劣勢(設計本就如此) |
| Studio 的 3D surface 無法開啟 | 缺少 `QtDataVisualization` | 屬盡力而為(best-effort)功能。依賴 PySide6 的版本/組態，缺少時會靜默跳過 |

### 影像 I/O 的相依關係(重要)

檔案讀寫所需的後端會因路徑而異。

| 路徑 | 所需後端 |
|---|---|
| `fullseye.load` / `fullseye.save`(= `imgio`)、`imgevolve.py run`、examples | **OpenCV 或 Pillow**(擇一即可 / 自動回退) |
| `imgevolve.py apply` / `pipeline` | **必須使用 OpenCV** |
| `fullseye.read_image` / `fullseye.write_image`(API) | **必須使用 OpenCV** |

直接傳入 numpy 陣列的 `apply` / `run_pipeline` / `FullseyeEngine.run`，**完全不需要任何影像 I/O 後端**(僅靠核心的 numpy + scipy 即可運作)。

---

## 執行確認

```powershell
py -3.11 imgevolve.py coverage        # 誠實的覆蓋數量(979/2313 個 HALCON op 已做真實實作)
py -3.11 imgevolve.py ops --search edge
py -3.11 -c "import fullseye; print(fullseye.version(), len(fullseye.op_names()), 'ops')"
```

`fullseye.version()` 為 `0.1.0`，`op_names()` 回傳 860 個註冊運算子(截至 2026-09-03)。
