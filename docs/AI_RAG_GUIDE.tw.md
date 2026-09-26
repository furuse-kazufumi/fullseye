<!-- i18n-source-sha: 8fe28ab585e4 -->
# 將 Fullseye 用作 AI 助理 RAG 的方法（針對 Claude Code）

[日本語](./AI_RAG_GUIDE.md) · [English](./AI_RAG_GUIDE.en.md) · [简体中文](./AI_RAG_GUIDE.zh.md) · **繁體中文** · [한국어](./AI_RAG_GUIDE.ko.md) · [Deutsch](./AI_RAG_GUIDE.de.md)

Fullseye 建議的用法是「**作為 AI 程式設計助理的知識庫（RAG）使用**」。由於所有 op 都擁有機器可讀的 Markdown 筆記（`docs/ops`，單一真實來源），因此**不需要**額外的向量資料庫或嵌入服務。只要環境能夠 grep，本身就是一個 RAG。

我們提供三個階段的導入方式。**Tier 0/1 沒有任何外部相依性**（僅靠 Fullseye 儲存庫本身即可完成）。

> **從 PyPI 使用**：在執行過 `pip install fullseye` 的環境中，可以使用主控台指令 **`fullseye-rag`**。若是 checkout（clone / `pip install -e .`），會將 `docs/ops` 的完整語料庫固定到技能中；若僅為 wheel 安裝，則會將隨附的 `OP_CATALOG.md`（面向 AI 的全 op 目錄）固定為技能（之後若需要完整的逐 op 筆記，只要 clone 儲存庫後重新執行即可）。更新方式為 `py -3.11 tools/update_fullseye.py`（拒絕在 dirty 樹上執行 · `--ff-only` · 在備份基礎上更新技能 · 不觸碰 Studio 設定——設計上不會破壞你的環境）。

---

## Tier 0：只要開啟儲存庫（零步驟）

在 Claude Code 中開啟 Fullseye 儲存庫的 checkout，即可直接檢索並參照 `docs/ops/INDEX.md` 與各 op 筆記。語料庫屬於儲存庫內容（wheel 中不包含），因此若只做了 pip 安裝，也請一併 clone 儲存庫。

```
docs/ops/2d/<category>/<op>.md   # 呼叫形式·型別契約·HALCON 別名·參考文獻·相關 op
docs/ops/3d/<category>/<op>.md
docs/ops/INDEX.md                # 走訪資料夾階層自動產生的整體目錄
docs/ops/2d/guides/<family>.md   # 13 個家族的使用指南(公式·圖示·經典文獻引用)
docs/OP_INDEX.json               # 登錄庫的機器可讀索引
```

## Tier 1：作為技能常駐（建議 · 內建安裝指令碼）

如果想在自己的專案中工作的同時參照 Fullseye，只需執行一次內建的安裝指令碼：

```bash
py -3.11 tools/setup_claude_rag.py              # 安裝(重新執行 = 更新)
py -3.11 tools/setup_claude_rag.py --uninstall  # 解除安裝
```

內建技能 `skills/fullseye-ops` 會被複製到 `~/.claude/skills/fullseye-ops`，SKILL.md 中的 `FULLSEYE_REPO =` 那一行會**自動固定為此 checkout 的絕對路徑**（如此一來，無論 AI 在哪個專案中工作，都能知道語料庫的位置）。若在找不到語料庫（`docs/ops`）的 checkout 中執行，安裝會被拒絕（fail-closed）。

此後，只要話題涉及影像處理、幾何視覺，Claude Code 就會自動啟動此技能，依照「檢索（retrieve）`docs/ops` → 挑選型別（sort）相銜接的 op 並實作 → 以內建的 worked example 驗證」的流程運作。技能本文本身就是「給 AI 的使用說明書」。若想手動安裝，只要把 `skills/fullseye-ops` 複製到 `~/.claude/skills/` 也能運作（只是少了路徑固定，AI 每次都得自行尋找儲存庫位置）。

## Tier 2（選用）：叢集化語料庫——藉助外部工具的進階型態

也可以把 **2,195 篇**筆記依主題分層叢集，並為每個叢集附上 LLM 摘要，做成「附導覽的語料庫」。我們內部使用的是 [RAPTOR](https://github.com/gadievron/raptor) 分支的 `corpus2skill`（TF-IDF + k-means + LLM 摘要），但**這只是一種選用的最佳化，並非必要**。要求僅僅是「以 `docs/ops` 為輸入，輸出依叢集劃分的 SKILL.md 階層」，因此任何具同等功能的工具都可以替代。

重新匯入（筆記更新後）的範例——如實記錄內部的運作方式：

```powershell
$env:RAPTOR_DIR="<path-to-raptor-checkout>"
py -3.11 raptor_corpus2skill.py --source <fullseye>/docs/ops --name fullseye_ops_corpus_v2 `
  --overwrite --max-depth 2 --max-clusters 6 --min-cluster-size 8   # 需要 ANTHROPIC_API_KEY
```

注意：叢集化語料庫是**匯入當下的快照**。更新 `docs/ops` 後若不重新匯入就會過時（Tier 0/1 一律讀取原始筆記，因此不會過時）。

---

## Tier 3（內建）：文獻層——把製造技術知識落到「該用哪些 op」

op 筆記回答「這個 op 做什麼」，卻不回答「在這道工序、這個零件上該量什麼」。
[`docs/literature/`](literature/INDEX.md) 填補這個空隙：外部文獻語料（機械設計、機電零組件、製造製程，約 7,000 筆 OpenAlex
中繼資料）依叢集摘要，並附上**每個叢集要用的 op**（人工撰寫的主題 → op 對照表，生成時以出貨筆記核對 op 名是否存在）以及代表
論文的標題 / 年份 / DOI 作為來源。閱讀順序：製程或零件 → 文獻叢集 → 要用的 op → op 筆記（型別契約、可執行範例）→ 實作。
不複製摘要，也從不用字面重合挑 op（實測會被通用詞帶出無關 op，已捨棄）。語料本體不在儲存庫裡，因此只有這一層用
`tools/gen_literature_notes.py --rad-root <RAD>` 重建，`tests/test_literature_notes.py` 守住它的形狀。

---

## 為什麼這樣可行（設計依據）

1. **md = 單一真實來源**：筆記由登錄庫確定性地自動產生，CI 的 drift 測試會強制要求「已提交的筆記 == 由目前程式碼產生的筆記」一致。**AI 讀取的文件與實際程式碼永遠是同一版本**（frontmatter 的 `version` + fingerprint）。
2. **型別（sort）契約**：每篇筆記都帶有 `in:`/`out:` 以及「型別相銜接的相關 op」，因此 AI 能在**進行型別檢查的同時**組裝管線。
3. **可驗證**：所有 op 都附有帶 ground truth 的 worked example（`examples/` / `examples_3d/`），AI 可以自行執行其提案並加以確認。
4. **一路貫通到顯示**：開啟 Studio（`py -3.11 studio.py`），人類就能在同一畫面上以影像視窗、3D 顯示的形式檢查 AI 組裝的結果（也能透過 `dev_open_window` 等從指令碼中配置多個視窗）。
