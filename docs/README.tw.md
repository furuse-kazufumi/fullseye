# Fullseye 文件索引

**Language:** [日本語](README.md) · [English](README.en.md) · [简体中文](README.zh.md) · [繁體中文](README.tw.md) · [한국어](README.ko.md) · [Deutsch](README.de.md)

> **請注意：**目前只有這份索引頁有譯文，它所連結的各篇文件暫時僅有日文版。

**Fullseye**（開發代號 imgevolve）是一套 HALCON/HDevelop 等級的實用軟體：由 numpy 原生的影像處理運算子函式庫、HDevelop 風格的視覺化管線設計環境（Fullseye Studio），以及負責執行的 runtime（FullseyeEngine）三者組成。運算子約 **521** 個（以 registry 計），其中 **269/2313** 個真實的 HALCON 運算子做到 genuine（真正等效）的實作，涵蓋 31 個類別。

> **請從這裡開始 → [GETTING_STARTED.md](GETTING_STARTED.md)（5 分鐘跑起來）**

---

## 用法（給使用者 —— 先看這四篇）

| 文件 | 內容 |
|---|---|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | 5 分鐘上手：安裝 → 第一條管線 → 在 Studio／CLI／程式碼中執行 → 看結果 |
| **[INSTALL.md](INSTALL.md)** | 環境建置完整指南：前置條件、`pip install -e .` 與各 extras 的取捨、Windows／Linux 安裝程式、最小組態與嵌入式整合、疑難排解 |
| **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** | Fullseye Studio 完整指南：三面板、運算子瀏覽器、單步執行、參數旋鈕、Inspector、感知面板、命令面板、快速鍵、匯出 |
| **[ENGINE.md](ENGINE.md)** | FullseyeEngine（設計 → 執行）：全部方法、在 Python 中的用法、CLI `run`、從其他專案呼叫 |

---

## 運算子 / API 參考

| 文件 | 內容 |
|---|---|
| [OPERATORS.md](OPERATORS.md) | 全部 521 個運算子的目錄（31 個類別，依 sort 分組，並列出 HALCON／OpenCV／scikit-image／MATLAB 的對應 API） |
| [EXAMPLES.md](EXAMPLES.md) | 逐個運算子的範例程式碼（附上其他函式庫中的等價呼叫） |
| [OP_INDEX.json](OP_INDEX.json) | 機器可讀的運算子索引（用 `imgevolve.py index` 重新產生） |
| [ADDING_OPS.md](ADDING_OPS.md) | 如何新增運算子（演化、codegen、目錄與索引都會自動跟上） |
| [../examples/README.md](../examples/README.md) | 可直接執行的端對端範例程式集 |

## 感知堆疊（機器人 / 視覺）

| 文件 | 內容 |
|---|---|
| [PERCEPTION.md](PERCEPTION.md) | 感知堆疊單頁速查（stereo／terrain／detect／registration／pose／flow／motion） |
| [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) | 在實拍影片片段上的量測結果（影片 I/O ＋ 誠實列出的實測數值） |

## HALCON 對等性 / 涵蓋率（誠實揭露 honest disclosure）

| 文件 | 內容 |
|---|---|
| [HALCON_PARITY.md](HALCON_PARITY.md) | genuine（真正等效）實作的進度（269/2313）：不是「只有名字一樣」，而是確實做得到同樣的處理 |
| [HALCON_COVERAGE.md](HALCON_COVERAGE.md) | 實際抓取官方參考手冊（v2605）後量出的涵蓋率 |
| [LIB_COVERAGE.md](LIB_COVERAGE.md) | 跨多個函式庫的涵蓋情形（納入 HALCON 以外具特色的運算子） |
| [PARITY_CROSSBACKEND.md](PARITY_CROSSBACKEND.md) | 以多個獨立實作（scipy／cv2／skimage）之間的跨後端一致性，來佐證對等性 |

## 品質 / 來源履歷 / 重現

| 文件 | 內容 |
|---|---|
| [ACCURACY_BENCH.md](ACCURACY_BENCH.md) | 常設精度表：演化出的 champion 對上 null 基準（holdout） |
| [CHAIN_FUZZ.md](CHAIN_FUZZ.md) | 鏈式 fuzzer——把運算子串成鏈條施加擾動的第三層品質保證（擴散 → 收斂 → 最小重現） |
| [EVOLUTION_ENVIRONMENT.md](EVOLUTION_ENVIRONMENT.md) | 演化式演算法開發環境（擴散 → 收縮 → 晉升；counterfactual utility 閘門，以及連接兩個運算子宇宙的橋） |
| [PROVENANCE.md](PROVENANCE.md) | 來源履歷：說明這些實作都是依據公開演算法自行寫成 |
| [REFERENCES.md](REFERENCES.md) | 每個運算子的文獻依據 |
| [REPRODUCE.md](REPRODUCE.md) | 數值重現步驟：由 seed 驅動、結果確定 |
| [STATUS.md](STATUS.md) | 專案目前的位置與後續計畫（plan_ref） |

## 發行說明 / 設計

| 文件 | 內容 |
|---|---|
| [V13.md](V13.md) | v13 ＝ 走向實用 ＋ 跨專案 packaging ＋ 感知堆疊 |
| [V14.md](V14.md) | v14 ＝ 感知堆疊完成（運動 ＋ 強化） |
| [STUDIO_UX.md](STUDIO_UX.md) | Fullseye Studio 在 UX／設計上的改良意圖與來龍去脈 |

---

## 快速指令

```powershell
py -3.11 -m pip install -e ".[opencv,gui]"     # 安裝（影像 I/O + Studio）
py -3.11 studio.py                              # 啟動 Fullseye Studio（= fullseye-studio）
py -3.11 imgevolve.py ops --search edge         # 搜尋運算子（= fullseye ops --search edge）
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py run pipeline.json in.png --out result.png
py -3.11 imgevolve.py coverage                  # 誠實的涵蓋數字
```

在 Python 中：

```python
import fullseye, numpy as np
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
eng = fullseye.FullseyeEngine.load("pipeline.json"); result = eng.run(frame)
```
