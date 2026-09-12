# 讓通用演算法也能實作 — algo-c 對應路線圖

[日本語](./GENERAL_ALGORITHMS.md) · [English](./GENERAL_ALGORITHMS.en.md) · [简体中文](./GENERAL_ALGORITHMS.zh.md) · **繁體中文** · [한국어](./GENERAL_ALGORITHMS.ko.md) · [Deutsch](./GENERAL_ALGORITHMS.de.md)

> 使用者需求(2026-08-16):<https://github.com/okumuralab/algo-c>(奧村晴彥
> 《[修訂新版] C語言標準演算法辭典》全部原始碼)中出現的**通用演算法**,
> 也希望能在 Fullseye 中實作。
>
> **誠實的現狀認知**:Fullseye 目前是 **影像演算法設計 AI**(op 註冊表 = image/region/
> feature/contour/volume 的 sort、演化 + holdout gate + Python→C codegen)。通用演算法
> (排序/搜尋/圖論/數論/加密/壓縮)無法歸入影像 sort,因此需要**擴充語言、型別與 codegen**。
> 這是橫跨多個工作階段的工作。本文件就是其**確定計畫**(供下一次工作階段在完整脈絡中執行的正本)。

## algo-c 的分類(書籍目錄 · 實作對象地圖)
※ 嚴格的涵蓋範圍以 repo 的 `/src` 為正本。

| 領域 | 代表性演算法 | Fullseye 中的承接方式 |
|---|---|---|
| 數值計算 | 方程式(二分法/Newton)、數值積分(Simpson/Romberg)、線性方程組(Gauss/LU)、內插(spline)、FFT | 既有 `dsp`(FFT)+ 新增 `numeric` op 族 |
| 亂數 · 統計 | Mersenne Twister、分布、統計量 | 新增 `rng`/`stat` op(確定性 seed) |
| 排序 | quick/heap/merge/shell/radix | 新增 `array` sort + `seq` 型別 |
| 搜尋 | 二分搜尋、雜湊、BST/AVL/B-tree | 新增 `array`/`map` op |
| 字串 | KMP/BM/Rabin-Karp、編輯距離、正規表示式 | 新增 `text` 型別 + op |
| 圖 | DFS/BFS、Dijkstra、Warshall-Floyd、MST、最大流 | 新增 `graph` 型別 + op |
| 幾何 | 凸包、線段相交、Voronoi | 既有 `pcseg`/幾何 + 新增 `geom2d` |
| 數論 · 加密 | 質數、GCD、RSA、MD5/SHA、AES | 新增 `numtheory`/`crypto`(教學用 · honest 揭露) |
| 資料壓縮 | Huffman、LZ/LZW、算術編碼 | 新增 `compress` op |
| DP/搜尋 | 8-queens、背包問題、DP | fscript 的控制流程 + `array` |

## 實作架構(確定方針)
將 Fullseye 的既有資產擴充到通用領域。**不會稀釋影像 AI 的焦點**(通用 op 歸入獨立 tier / opt-in)。

1. **型別系統擴充**:在現有 6+1 種 sort(image/region/feature/contour/match/any/volume)基礎上,
   新增**`seq`(一維陣列)/`text`(字串)/`graph`/`scalar`**(`ops.py` 的 sort · `fslib` 型別)。
2. **fscript 的通用語言化**:目前已具備 if/for/while、指派、tuple。將分階段新增**陣列/字串
   字面量、索引、procedure(函式)**(先前決定收窄語言範圍,通用 tier 將以獨立 profile 解禁)。
   正本 = 重新檢視 `docs/FSCRIPT_DECISION.md` 中的 A/B 分支。
3. **op 註冊表擴充**:將 algo-c 中的各個演算法以 **op**(name/in-out sort/params/**c_stmt**)形式
   註冊。直接沿用既有的 Python→C codegen(`engine.to_python`/`to_c`)+ **difftest**(honest gate:以
   Python 為 oracle,對 C 做差分驗證)→ **用實測保證「能以 C 實作」**。
4. **honest gate**:把 algo-c 的 C 程式碼作為參考實作餵給 `difftest`,與 Fullseye codegen 產生的 C
   驗證數值/位元一致性(既有 gate 的擴充)。**尊重原始程式碼的授權條款**(algo-c = 書籍附帶程式碼,
   使用條件待確認),**不直接照抄,而是從規格重新實作**(公開揭露方針)。

## 階段計畫(下次工作階段以後)
- **P1**:將 `seq`/`scalar` 型別 + 3 種排序(quick/heap/merge)op 化 + C codegen + difftest。
  = 「Fullseye 也能為通用演算法產生 C 程式碼」的最小實證。
- **P2**:數值計算(二分法/Newton/Simpson/Gauss)op 族。
- **P3**:字串(KMP/BM/編輯距離)+ `text` 型別。
- **P4**:圖(Dijkstra/BFS/MST)+ `graph` 型別。
- **P5**:壓縮/數論/加密(教學用 · honest 揭露,禁止照抄)。
- 每個 P 階段:演化 gate 不適用(通用 op 是確定性的、不做 holdout 演化),**用 difftest 對 C 一致性做 honest 實測**,
  在 Studio 的 op 瀏覽器中展示新 tier。

## honest 的侷限與規律
- **不照抄**:參考 algo-c 的 C 程式碼,但**從規格重新實作**(`feedback_provenance_research_method`)。
  在確認授權條款之前不納入程式碼。
- **不稀釋影像 AI 的焦點**:通用 op 屬於 opt-in tier。北極星目標(HALCON 級影像 op 全覆蓋 + honest
  holdout)保持不變。

---

## P1 完成紀錄(2026-08-16, Opus5[1m]/ultracode)
**達成了最小實證「Fullseye 也能為通用演算法產生 C 程式碼,並能 honest 實測出 C 一致性」。**

- **新 tier(與影像 REGISTRY 完全分離、opt-in)** = `algo.py`。新設 `seq`(一維數列)/`scalar`(單一實數)型別。
  完全不觸碰影像 `ops.REGISTRY`,因此演化搜尋、Wave-0 champion pin 不受影響(已用測試實證)。
- **op(5 個)**:排序 3 種 `quicksort`(Hoare/median-of-three/Lomuto/顯式堆疊)、`heapsort`(Williams
  1964 二元最大堆積)、`mergesort`(von Neumann 1945 由上而下的穩定排序)= `seq→seq`。此外為 `scalar`
  型別賦予角色的歸約(reduction)`seq_max`/`seq_min`(`seq→scalar`、與順序無關且 exact)。**全部從規格
  重新實作**(algo-c 原始碼不照抄 · 各 op 均標明 `provenance`)。
- **單一 source of truth**:各 op 將 Python 主體與 C 主體以**字串**形式保存,行程內參照由
  `algo.py_fn` 編譯同一字串,`algo_codegen` 將同一字串輸出為獨立的 `.py`/`.c`。
  → 被測試的 oracle 與出貨物不會漂移(用測試 `test_emitted_python_*` 實證)。
- **codegen** = `algo_codegen.py`(`emit_python`/`emit_c`。C 是函式 + 二進位 I/O driver = 可完整
  編譯的獨立程式)。
- **honest gate** = `algo_difftest.py`(兩項實測,均非 deferred skip):
  (1) Python 參照 **== numpy oracle**(`np.sort`/`np.max`/`np.min`),(2) codegen **C == Python
  逐位元一致**(holdout = 邊界情況 10 + 隨機 40)。由於這些 op 只是移動/選取既有 double,正確實作應
  逐位元完全一致(tol=0.0)。
- **★實測(2026-08-16, `zig cc` = `python -m ziglang cc`, 以 pip 安裝 ziglang 0.16.0)**:
  全部 5 個 op 均為 **python diff 0.00e+00 / C-vs-Python diff 0.00e+00 / passed=True**(實際
  編譯→實際執行→逐位元比較)。= 作為**非 deferred skip 的真實量測**達成了「honest 實測 C 一致性」。
- **fail-closed**:無 toolchain 時 → C 部分 honest skip(Python 部分照常執行)。compile/run 失敗 →
  gate FAIL(不設為 neutral skip。用測試 `test_difftest_compile_error_fails_closed` 實證)。
- **facade**:`fullseye.algo_ops()/run_algo()/algo_to_c()/algo_to_python()/algo_difftest()`
  (+ `api.py`)。**skill** = 在 `~/.claude/skills/image-processing/SKILL.md` 中補寫「General algorithms
  (algo-c tier)」一節(可供子代理使用)。
- **測試**:`tests/test_algo.py`(42 個案例 = 註冊表一致性 · Python==sorted/oracle · 穩定性 · 單一 source
  of truth · C 逐位元一致[有 toolchain 時] · compile-error fail-closed · 不汙染影像註冊表 · facade)。
- **honest 的侷限**:①含 NaN 的數列因比較排序的約定在 Python/C/numpy 間不一致,故從 holdout 中
  排除(已揭露)。②**累加會造成順序相依的 op 不納入 P1**(如浮點求和;seq_max/min 是 exact 的)。
  ③CLI 子命令整合(`imgevolve.py algo ...`)與 Studio op 瀏覽器 tier 顯示留待下階段(P1.5)。
  ④fscript 的陣列/procedure 語言化(設計文件架構第 2 項)不在 P1 範圍內(另設 track)。

## P1 對抗性審查後的強化(2026-08-16, [[feedback_no_solo_ai_judgment]])
對本工作階段自行撰寫的程式碼實施了獨立的對抗性審查(Workflow 4 個視角 = 演算法正確性 / codegen · C 安全 /
gate 健全性 / 整合 · 焦點安全,共 22 項 findings)。我對全部結果做了第一手程式碼驗證(v11 規律),
修正了真正的缺陷:
- **[HIGH] gate 的 fail-open(NaN/帶正負號零)**:`_max_diff_*` 因 `max(0.0, nan)=0.0` 而把 NaN 差異
  抹平,虛報「逐位元一致」(已實測重現)→ 拆分為 **(1)Python×oracle=數值比較,但非有限值 fail-closed
  (inf、不用 tol 放行);(2)C×Python=真正的逐位元比較(IEEE float64 原始位元組 = 帶正負號零/NaN payload
  也能偵測)**。用 `c_verified` 欄位區分「實際編譯驗證通過」與「無 toolchain 未驗證通過」。
- **[HIGH] quicksort 對大量重複輸入呈 O(n²)**(Lomuto `<=` 使全部相等元素落到一側;二值化 = binary
  mask flatten 是現實輸入、實測呈 quadratic)→ Python/C 均改寫為 **3-way(Dutch national flag)
  分割 + median-of-three**(全等值時 O(n))。追加效能防護測試(20000 全等值 <2s)。
- **[HIGH] 產生的 C `heapsort` 與 BSD `<stdlib.h>` 的 `heapsort()` 符號衝突**(macOS/BSD 上無法編譯,
  用 `zig cc -target x86_64-macos` 實測)→ C 符號改名為 **`heapsort_asc`**(與 `mergesort_asc` 統一)。
  追加**全部 op 的 macOS 交叉編譯測試**(回歸防護)。
- **[LOW] C 的 fail-open/UB 3 處**:mergesort 的 malloc 失敗 = 輸出未排序 → **改為原地插入排序
  fallback(fail-closed · 保持 stable)**;heapsort 的 `2*root+1` int 溢位 → 改為 **long long**;
  driver 的 len 為 32 位元導致 size_t 環繞 → **加入 `SIZE_MAX/sizeof(double)` 上限檢查 + `<stdint.h>`**。
- **[MED] test_mergesort_is_stable 是空洞測試**(值比較 = 任何排序都能通過)→ 改寫為透過帶
  正負號零的**順序保留**實際觀測穩定性(`<` = 會偵測到退化為不穩定)。同時新增 **no-mutation 測試**
  (`run(a)` 不會破壞呼叫端的 list)。
- **[MED] holdout 太小、重複稀疏**→ 追加大規模全相等(300)/ 二值(300)/ few-distinct(300)+ 更多
  重複的隨機資料(使 C gate 能實際檢驗重複度與規模區間)。
- **[MED/honesty] NaN 約定未文件化**→ 在 module docstring 與各 op docstring 中明確「以 NaN-free
  為前提 · 非有限值由 gate fail-closed」。seq_max/min 的「order-independent」改為「在 NaN-free 輸入下
  order-independent」。
- **相鄰的既有 ship-bug**:`sample_images`(studio 執行期 import)在 `pyproject.toml` 的 py-modules
  中缺漏 = 非 editable wheel 會消失 → 補齊(用實際建置 wheel 確認)。
- 測試從 **43 增至 58 個**(新增位元檢查 · fail-closed · macOS 交叉編譯 · 重複度效能 · no-mutation ·
  c_verified · 穩定性觀測)。重新執行全部 op 的 difftest = Python 與 C 均 diff 0.0 · 逐位元一致 ·
  passed=True。
- **未修正(使用者判斷 · P1 範圍外的既有問題)**:(a)`pyproject.toml` 的 `[tool.setuptools.package-data]`
  `"*"` glob 無法把根層級平鋪的 `studio_assets/`、`data/` 收進 wheel(studio i18n/op-help/範例影像在
  installed wheel 中缺漏 = 既有問題、需要 MANIFEST.in 或改變 package 化設計)/ (b)`fullseye.__all__`
  缺少 api 中 pcseg 系列的 18 個名稱(星號匯入會缺漏 = 既有問題)。**algo tier 與此無關**(algo* 透過
  py-modules 確實會一併打包 · facade 是一致的)。

## 接下來(P2 以後)
- **P1.5a(已完成, 2026-08-16)**:新增 `imgevolve.py algo <list|run|emit-c|emit-py|difftest>` 子命令
  (統一 CLI 入口。`algo run quicksort --seq 3,1,2` / `algo emit-c mergesort` / `algo difftest all`)。
  新增 CLI 回歸測試 2 個 + 更新 skill 中的 CLI 範例。
- **P1.5b(完成於 2026-08-17)**:在 Studio 的 op 瀏覽器中以 **唯讀方式**展示 general(algo)tier(紀錄見下)。
- **P2(完成於 2026-08-16)**:在 seq/scalar 型別基礎上加入數值計算 op。**simpson / bisection / newton**
  (多項式 · 樣本內含於輸入 seq 的 seq→scalar · 沿用既有 reduce driver)+ **gauss_solve**
  (線性方程組 Gauss 消去 · 部分主元 = 紀錄見下方 P2 完成紀錄)。honest gate = **C-vs-Python 為逐位元
  一致**(同一演算法 + `-ffp-contract=off` 抑制 FMA)/ **Python-vs-oracle 為數值容差**(`AlgoOp.tol`)與
  獨立 oracle(simpson=scipy / 求根=殘差 |p(root)| / gauss=`np.linalg.solve`)核對。將 fail-soft 做 honest 文件化。
- **P3(完成於 2026-08-17)**:字串 op(紀錄見下方 P3 完成紀錄)。`text` 型別採用「以 float64 承載
  code point 序列」的約定(`text_to_seq`/`seq_to_text`),不新增 wire 型別即可搭載既有 float64 harness。
- **P4(完成於 2026-08-17)**:圖 op(components/mst_weight/dijkstra,紀錄見下方 P4 完成紀錄)。`graph`
  以 `[n, m, (u,v,w)*m]` 打包搭載既有 harness(無需新 wire 型別)。
- **P5(完成於 2026-08-17)**:數論 · 壓縮 · 教學用雜湊(gcd_seq / sieve_primes / pow_mod / crc32 /
  rle_encode,紀錄見下方 P5 完成紀錄)。整數以 float64 承載(exact <2^53),因此不需要新的 wire 型別。全部 op 都是
  **exact 的**(C 逐位元一致,且 Python==獨立 oracle tol 0)。**加密僅提供 primitive**(modular
  exponentiation / CRC)= 完整的 RSA/AES/SHA 因需要 bignum/大狀態而無法搭載 float64 seq harness,故明確
  界定為範圍外並 honest 揭露。

## P3 完成紀錄 — 字串 op(2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**為 algo tier 新增 3 種字串演算法。**「字串 = 以 float64 承載 code point 序列」(Unicode 純量 < 2^53 故為
嚴格精確)使其**無需改造即可搭載既有的 float64 二進位 harness**(無需新 wire 型別)。值僅做相等比較
(整數編碼精確)· 位置/距離為嚴格整數 → **C-vs-Python 逐位元一致 且 Python-vs-oracle 為 EXACT(tol 0)**。

- **op(3 個)**:`strfind`(Knuth-Morris-Pratt = 失敗函式前綴自動機。輸入 `[m, pattern(m), text]` →
  全部出現的起始位置的遞增列表 · 含重複出現 = **可變長 KIND_MAP**,重複利用 gauss 中建構的可變長 wire) /
  `edit_distance`(Wagner-Fischer/Levenshtein 雙列 DP = **KIND_REDUCE** · 嚴格整數) / `lcs_length`
  (最長共同子序列長度雙列 DP = KIND_REDUCE)。全部從規格重新實作(明確標註 provenance)。fail-soft =
  空 pattern/截斷/pattern 長於 text 時為 `[]`,na<0/截斷為 `0.0`。
- **單一 source of truth + text 型別輔助函式**:新增 `text_to_seq(s)`/`seq_to_text(seq)`(code point↔float64)。
- **honest gate 實測(3 個 op 均 passed=True · c_verified=true)**:Python==**獨立 oracle**(strfind=
  樸素 all-occurrences 掃描[與 KMP 獨立] / edit·lcs=**由上而下的 memo 遞迴**[與由下而上的雙列 DP 是
  不同程式碼路徑])**diff 0.0(exact)** / codegen **C==Python 逐位元一致**(ziglang cc)。
- **work-graph op 波(候選 d 的實演)**:每新增一個 op 就疊加一個 `algo_gate` gate 節點 = **1 op = 1
  節點**。將 3 個 op 透過 `raptor-worklog add --capability tool` → `run-once --available
  tool:command` 實現 **無人值守完成**(產生 gate_ok.json)。
- **回歸**:在 `tests/test_algo.py` 中為 strfind/edit_distance/lcs_length 新增測試群組(已知解 · 隨機×
  獨立 oracle · fail-soft · 可變長輸出 · no-mutation · python exact · C 逐位元一致)。全部套件 **4669
  passed / 0 failed**(較 P2 後的 4649 增加 +20)· ruff clean · mypy 回歸 0。commit + push 已在本工作階段
  執行(使用者於 2026-08-16 就寢時核准 = push gate 開放)。

### P3 字串 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
獨立對抗性審查 Workflow(4 個視角 · 各項 finding 由驗證代理以實際程式碼/實際 compile 確認)= **3 項
findings 全部 CONFIRMED**(其中 2 項是同一根本原因被不同視角分別回報)。經第一手驗證後全部修正:
- **[MED] Python 在做範圍檢查前就先執行 `int(a[0])` → 與 C 不一致**:edit_distance/lcs_length 的 Python
  先求值 `na = int(a[0])`(截斷),而 C 是先用原始 double 做守衛。當 **`a[0]` ∈ (-1.0, 0.0)**(例如
  -0.5)時,Python 會得到 na=0(有效的空字串)並繼續回傳實際距離,而 C 用原始值守衛直接拒絕回傳
  0.0 → **違反逐位元一致契約**(用 ziglang cc 實測:`[-0.5,65,66]` = Python 得 2.0 而 C 得 0.0)。holdout
  只有非負整數 na,故 gate 未能偵測到。
- **[LOW] NaN 表頭會使 Python 崩潰**(C 是 fail-soft):`int(nan)` 會拋出 ValueError,違反 op docstring
  中的 fail-soft 承諾(C 用 NaN-false 守衛回傳 0.0/`[]`)。※雖然 NaN 屬於「以 NaN-free 為前提」的契約
  之外,但屬於同一類守衛順序缺陷。
- **修正(一處修復兩個問題)**:將全部 3 個 op 的 Python 中**原始值守衛移到 `int()` 之前**
  (`not (x >= lo and x <= hi)` = NaN-false)= **精確鏡射 C**。gauss 原本就是原始值守衛、寫法正確
  (統一為同一形式)。
- **邊界覆蓋補強**:因超出 oracle 驗證域(oracle 的截斷會產生不同的值 = 正是這個 bug 本身)之外的
  小數負值/NaN/超長表頭,新增**專用測試直接固定 C-vs-Python parity**
  (`test_string_c_python_parity_on_bad_headers`)+ Python fail-soft 不崩潰測試。algorithm-correctness/
  c-safety 方面的核心指摘為 0(KMP/DP/記憶體安全均乾淨)。
- 審查後:3 個 op 的 difftest 均為 python exact / C 逐位元一致 / c_verified=true,全部套件全綠(見下)·
  ruff/mypy 回歸 0。

## P2 完成紀錄 — gauss_solve(2026-08-16, Opus5[1m]/ultracode, `graph-loop-engineering`)
**新增線性方程組 Gauss 消去(部分主元),完成 P2 數值計算。** 依使用者指示以 `graph-loop-engineering`
技能將其節點化到 raptor work-graph,讓 tool driver 無人值守執行(雙層方針 = breadth 由 work-graph 的
difftest gate 負責,對抗性 findings 的採納與 push 是工作階段內的人工檢查點)。

- **新 kind `KIND_MAP`(`map_varlen`)= 可變長 seq→seq**:既有 op 只有 sort(輸入長度=輸出長度)/
  reduce(→單值)兩種,而線性方程組的解(輸入 `[n, 增廣係數矩陣 n×(n+1) row-major]` → 解向量長度 n)
  輸入長度≠輸出長度。C 邊界 = `int f(const double* a, int n, double* out)` 向 out 寫入
  out_len(≤ n)個值並回傳 out_len(fail-soft=0)。
- **`algo_codegen` driver 新增可變長輸出模式**:KIND_MAP 分支寫出 `{int32 out_len,
  out_len*float64}`(與 sort 相同的 wire,但 out_len≠輸入長度)。out 緩衝區按輸入長度配置(契約
  out_len≤n 保證上界)+ 對 `out_len ∈ [0,len]` 做 **fail-closed clamp**(防止失控 op 讓讀取端發生
  over-read)。
- **gauss_solve(`algo.py`)**:Python 參照實作(僅用 stdlib、逐 index 精確鏡射 C)與 C 參照實作為單一
  source。前向消去(部分主元 = 選取 |元素| 最大的列)+ 回代。奇異(殘留主元為 0)/畸形輸入以
  **[] / 0** 做 fail-soft(不擲出例外)。**Python/C 的浮點運算順序嚴格一致**(同一除法 · 先減後乘 ·
  被消去元素精確指派為 `0.0` · abs 用內聯正負號反轉以避免依賴 `math.h`/`-lm`)故逐位元一致。int 溢位透過
  `n≤46340` + `long long need` 防止。
- **honest gate 雙段(實測)**:(1)Python **== `np.linalg.solve`**(獨立 oracle · 良態 holdout 34 例 =
  對角占優 + 列置換 + **必經主元的情形**[exact-zero(0,0)· 微小(0,0)· 3×3 零對角])→ **最大絕對差
  3.55e-15**(tol 1e-9)。(2)codegen **C == Python 逐位元一致**(`ziglang cc` · `-ffp-contract=off`)→
  **diff 0.0 / c_verified=true**。奇異/畸形輸入的 **C fail-soft 與 Python 完全一致**,用專門測試直接
  驗證(因超出 oracle 支援範圍,故做 C-vs-Python 直接比較而非 holdout)。
- **`tools/algo_gate.py`(可重複使用的 gated-stage runner)**:work-graph 的 `CommandWorker` 以「產生
  produces」或「exit0」判定完成,而目前 difftest 在 FAIL 時也會寫 JSON,導致**fail-open**(失敗的 gate
  被判定為 done)。為堵住此漏洞 = **僅在通過時寫入標記檔 `gate_ok.json`,並以 exit code 判定**。將
  節點的 produces 指向該標記後,失敗的 gate 會 **fail-closed**、使節點失敗。可直接用於 P3 以後的 op
  波(1 op = 1 節點)。
- **work-graph 節點化**:`raptor-worklog add --capability tool --project imgevolve --priority 0`
  (spec = `tools/algo_gate.py --op gauss_solve --out <OUT>`,produces=`<OUT>/gate_ok.json`)→
  `run-once --available tool:command` 實現 **無人值守執行 → status=done**(exit0 · c_verified=true ·
  產生逐位元一致標記)。
- **回歸**:在 `tests/test_algo.py` 中新增 gauss + algo_gate + C fail-soft + require_c 測試群組(演算法
  測試 **93 passed**),全部套件 **4649 passed / 0 failed**(較審查前的 4637 增加 +12)。我修改的
  全部檔案 **ruff clean** · mypy 回歸 0(既有 baseline 僅為 scipy/ziglang stub 缺漏及 difftest 簽章的
  既有 quirk,與我新增的程式碼無關)。全部本地 commit,**未 push = human-gate**。

### P2 gauss 對抗性審查後的強化(2026-08-16, [[feedback_no_solo_ai_judgment]])
對自行撰寫的 gauss 程式碼實施獨立對抗性審查 Workflow(4 個視角 = numeric 正確性 / C 安全 / gate 健全性 /
整合 · 覆蓋,各項 finding 均由驗證代理**實際執行重現**)。5 項 findings 中 **4 項 CONFIRMED**,經第一手
程式碼驗證後全部修正:
- **[HIGH] algo_gate 的 fail-open(未知 op)**:`find_algo` 的 `SystemExit` 發生在 `marker.unlink()`
  **之前**,導致上一輪通過時留下的 `gate_ok.json` 殘留 → CommandWorker 因 produces 存在而**誤判為
  done**(在 op 改名/typo 後重新執行時會顯現)。→ 把 mkdir + stale-marker unlink **移到註冊表檢查之前**
  (無論哪個提早 exit 都不會繼承上一輪的通過結果)。已追加回歸測試。
- **[MED] gate 無法證偽部分主元的正確性**:holdout 只有對角占優的情形(沒有 exact-zero 主元)→ 刪除
  主元搜尋的 mutant 仍與 `np.linalg.solve` 相差 2.2e-14 而**通過**(pytest 能捕捉,但 work-graph 實際
  執行的 algo_gate 走的是 difftest holdout,故捕捉不到)。→ 在 holdout 中新增**必經主元的情形**
  (exact-zero(0,0)=`[[0,1],[1,0]]`· 微小(0,0)=`[[1e-14,1],[1,1]]`· 3×3 零對角)= no-pivot mutant
  會**結構性不一致→inf→FAIL**,從而被證偽(已自行實測確認)。同時修正了具誤導性的註解。
- **[MED] C 端 skip 時仍產生 pass 標記**:toolchain 不存在時 C 部分 skip(honest 但**未驗證**),
  但僅憑 `res["passed"]` 就寫入標記檔,graph 只讀取標記是否存在 → **對未編譯的 C 也發放認證**。→
  新增 `require_c`(預設 True)= 未驗證的 pass 不會寫入 `gate_ok.json`(改寫入 `gate_unverified.json`
  附帶 diagnostic)以 **fail-closed**。`--allow-unverified-c` 可明確 opt-out,`--no-c` 表示刻意的
  Python-only 弱 gate。
- **[REFUTED]「out_len==0 的 wire 未被測試」**:我事先補充的 `test_gauss_c_fail_soft_matches_python`
  實際編譯/執行了 C 並已涵蓋 → 驗證代理透過 mutation 確認其健全性後**予以駁回**。僅採納了 macOS
  交叉編譯防護測試中一處輕微 nit(將 `_ALL` 改為 `_ALL_OPS` 以同時涵蓋 numeric/gauss)。
審查後 gauss 的 difftest 仍為 python 3.55e-15 / C 逐位元一致 / c_verified=true · work-graph 節點(已強化)= done。

## P1.5b 完成紀錄 — 在 Studio 中以唯讀方式展示 general tier(2026-08-17, Opus5[1m]/ultracode)
**在 op 瀏覽器中展示 general(algo)tier。** 為不稀釋影像焦點的設計 = general op 屬於 seq/scalar 的
另一套計算模型,故 **唯讀**(不納入影像流水線)。
- 在 `api.list_ops(include_algo=False)` 上新增 opt-in 參數 + `api.algo_rows()`(backend="general" ·
  category "algo:*" · tier "z_algo" 用於末尾排序 · halcon None · 附帶 provenance)。**預設值不變**
  (既有呼叫端仍只看到影像 op = 保持焦點)。
- studio:`all_ops = list_ops(include_algo=True)` 使 browser 得以顯示 / `_op_row` 增加 algo 回退 /
  `op_signature_detail`、`op_tooltip` 新增 general 分支(「seq/scalar op · not an image op · run via
  CLI」+ provenance)/ `on_op_selected` 在選中 general 時停用 Insert · Run once · Help · a/b 旋鈕 /
  `add_op`、`run_op_once`、調色盤對 general 做 flash 拒絕。多重防禦 = **`PipelineModel.add_stage`
  在影像 REGISTRY 中查不到則 KeyError fail-closed**。
- **對抗性審查(2 個視角 · 實際執行驗證)= 3 項 CONFIRMED(其中 2 項為同一根本原因)全部修正**:
  - **[HIGH/MED] Program(HDevelop 程式碼)編輯器的「Apply → pipeline」未設防**:`op_names` 是從
    `list_ops(include_algo=True)` 衍生的,導致 general 名稱流入程式碼解析器/自動完成/Help 選擇器 →
    `apply_program` 直接寫入 `model.stages=` **繞過了 add_stage 的後備防護** → general op 侵入
    pipeline。→ **將 `op_names` 限定為影像專用**(用 `backend != "general"` 排除;browser 顯示用的
    `all_ops` 仍保留 general)+ 在 `apply_program` 中新增 general stage 拒絕防護(多重防禦)。
  - **[MED] Help 對話框選擇器對 general 顯示不實資訊**(「Two knobs a,b tune this operator」)→ 同一處
    `op_names` 影像限定化也一併從 Help 選擇器中排除(根因修復同時解決兩處)。
- 回歸測試:`_op_row`/signature/tooltip 的 general 分支、在 offscreen 環境下 browser 顯示 general 但
  Insert 等被停用、`win._op_names` 排除 general、程式碼解析器拒絕 general 行。全部套件全綠 · ruff
  net-new 0(新增測試乾淨,studio.py 的 flash 與檔案既有的 `%`-format 慣用法一致)· mypy 回歸 0。
  同時**實演了候選 (d) op 波**:將全部 12 個 algo op 以 1 op = 1 節點納入 work-graph,用 `run-once`
  實現無人值守完成。

## P4 完成紀錄 — 圖 op(2026-08-17, Opus5[1m]/ultracode, bonus)
**為 algo tier 新增 3 種圖演算法**(不在候選之內,但順應使用者「全部推進」+ 7-8h 自律的方針作為 bonus)。
將圖打包進輸入 seq(`[n, m, (u,v,w)*m]`,無向;dijkstra 會在前面加上 src 前綴 `[n, m, src, ...]`),
搭載既有的 float64 harness。
- **op(3 個)**:`graph_components`(union-find · 連通分量數 = KIND_REDUCE 嚴格整數) /
  `graph_mst_weight`(Kruskal · 最小生成森林總權重 = KIND_REDUCE) / `graph_dijkstra`(單源最短距離 =
  **KIND_MAP** · -1.0 = 不可達)。用確定性的 union 規則 + (weight, index) 排序 + 最小距離 · 最小
  index 的 settle 順序,實現 **C==Python 逐位元一致**。
- **★將 KIND_MAP driver 做成兩段式(size-probe)**:dijkstra 的輸出長度 n **可能超過**輸入長度
  3+3m(稀疏圖)。舊 driver 按輸入長度配置 out,存在 heap OOB 的缺陷 → 改為讓 driver 先用
  `f(a,n,NULL)` 詢問 out_len 上界,依此配置後再真正寫入的兩段協定(在 gauss/strfind/dijkstra 中
  加入 `if(!out) return <bound>`)。
- **honest gate**:Python == 獨立 oracle **scipy.sparse.csgraph**(connected_components/
  minimum_spanning_tree/dijkstra)。整數權重 holdout 下 **components 嚴格精確(tol 0)/ mst ·
  dijkstra tol 1e-9(實測為 0)**。C==Python 逐位元一致(ziglang cc)。MST/Dijkstra 的 holdout 使用簡單圖
  (避免 csr 的重複邊累加),components 允許多重邊(只關心連通性)。
- **對抗性審查(3 個視角 · 實際執行驗證)= 2 項 CONFIRMED(均為 HIGH · dijkstra 記憶體安全)全部修正**:
  (#2)out 緩衝區按輸入長度配置 → n>3+3m 時發生 OOB 寫入 → 用**兩段式 driver** 解決(在被發現前已
  先行修復)。(#1)src 守衛使用原始 `sd < nd` → 小數 nd 會使 src==n 通過、導致 out[n] OOB → 改為用
  整數 n 約束(`sd < n`)。1 項 REFUTED(不可達節點未被測試 ← 已由 known-answer/sparse 測試涵蓋)。
  numeric/oracle 各視角均無其他指摘。
- **op 波**:3 個圖 op 也納入 work-graph gate 化(全部 algo op = 15 個,均以 1 op = 1 節點實現無人值守
  完成)。全部套件全綠 · ruff clean · mypy 回歸 0。push 已在本工作階段完成(使用者核准)。

## P5 完成紀錄 — 數論 · 壓縮 · 教學用雜湊(2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**為 algo tier 新增 5 種通用演算法,完成 algo-c 路線圖(P1→P5)。** 整數以 float64 承載(exact < 2^53),
因此不需要新的 wire 型別。位元/整數運算在 C 端 cast 為 `unsigned long long`/`unsigned int` 後進行,再
轉回 double(結果 < 2^53 故 exact)。**全部 5 個 op 均為 exact**(C 逐位元一致,且 Python==獨立 oracle
tol 0)。
- **op(5 個)**:
  - `gcd_seq`(KIND_REDUCE):非負整數列的 GCD(Euclid · 對數列 fold)。oracle=`math.gcd`。
  - `sieve_primes`(**KIND_MAP**):埃拉托斯特尼篩法。輸入 `[n]`(長度 1)→ n 以下質數的遞增列表 =
    **輸出遠超輸入長度**的代表案例。size-probe 上界 `π(n) ≤ n/2 + 1`(2 與奇數的數目,無需
    log = 不依賴 `math.h`)。oracle=試除法(獨立路徑)。
  - `pow_mod`(KIND_REDUCE):模冪 base^exp mod m(square-and-multiply = RSA/DH 的 primitive · 教學用)。
    oracle=內建 `pow`。
  - `crc32`(KIND_REDUCE):CRC-32(IEEE 802.3 · reflected · poly 0xEDB88320)。**c_func 為
    `crc32_ieee`**(防禦性地避開與 zlib/BSD 的 `crc32` 符號衝突,同 heapsort_asc)。oracle=
    `zlib.crc32`(zlib C 函式庫 = 完全獨立)。
  - `rle_encode`(**KIND_MAP**):行程長度編碼 →`[value, count, ...]`(**輸出最大為輸入的 2 倍**,全不同
    時為 2n)。可逆 · oracle=`itertools.groupby`。
- **★honest 域的揭露(pow_mod)**:為防止 uint64 的中間乘積溢位,**mod ≤ 2^32−1**(積 < mod² < 2^64),
  base/exp ≤ 2^53。結果 < mod < 2^53 於 float64 為 exact。域外 fail-soft 為 0.0(原始值守衛在
  int() 之前 · NaN 安全)。
- **★加密僅提供 primitive(honest scope)**:完整的 RSA/AES/SHA 因需要 bignum · 大狀態而無法搭載
  float64 seq harness,故明確標註為範圍外。能搭載的 primitive(modular exponentiation / CRC
  checksum)以**演算法揭露**的形式提供(並非 cipher)。
- **★整數性守衛(新增 · honest 改進)**:gcd_seq/pow_mod/crc32 屬於**資料值**,故非整數視為畸形 →
  fail-soft。將 `x == float(int(x))` / `x == (double)(long long)x` 放在**範圍檢查之後**做
  short-circuit(NaN/超範圍值不會抵達 cast,避免 `int(nan)` 崩潰 · C 的 `(long long)nan` UB)。表頭類
  (sieve 的 n)沿用與既有 gauss/dijkstra 相同的截斷約定。
- **★在新增的 2 個 op 中運用 KIND_MAP 兩段式 size-probe**:sieve(輸出遠大於輸入)· rle(輸出≤輸入的
  2 倍)均用 `if(!out) return <上界>` 讓 driver 先問上界→配置→再真正寫入。用專門測試以實際
  compile/run 固定「即使 C 輸出超過輸入長度也不會 heap OOB」。
- **honest gate 實測(5 個 op 均 passed=True · c_verified=true · ziglang cc)**:Python==獨立 oracle
  **diff 0.0(exact)** / codegen **C==Python 逐位元一致 diff 0.0**。crc32 已在全部位元組值 ·
  「Hello」· 全 256 位元組上與 `zlib.crc32` 核對一致。
- **work-graph op 波**:將 5 個 P5 op 做成 `algo_gate` gate 節點(`1 op = 1 節點` · priority 0 ·
  tool capability)→ `run-once --available tool:command` 實現 **5 個節點無人值守完成**(各自產生
  `gate_ok.json` = c_verified/逐位元一致標記)。= **全部 algo op 達到 20 個、均已 work-graph gate
  化**(15→20)。
- **回歸**:在 `tests/test_algo.py` 中新增 P5 測試群組(已知解 · 與獨立 oracle 大量隨機核對 · fail-soft ·
  整數性 · 兩段式 probe 的輸出超量 · bad-input 的 C-vs-Python parity · no-mutation · python exact ·
  C 逐位元一致)。全部套件從 **4700 增至 4736 passed / 0 failed**(+36)· 我新增檔案 ruff clean · mypy
  新增錯誤 0(僅有既有 baseline)。

### P5 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
對自行撰寫的 P5 程式碼實施獨立對抗性審查 Workflow(4 個視角 = algorithm-correctness / C-safety-codegen /
gate-honesty / integration-focus,各項 finding 均由驗證代理**以實際 compile/執行重現**,18 個
agent)。**14 項原始 → 9 項 CONFIRMED / 5 項 REFUTED**。全部 CONFIRMED 均由我第一手重現(親自用
ziglang 編譯 · 執行)後修正。**尤其值得一提的是對「gate 是否能證偽自身守衛」這一點的深入追問**:
- **[MED] pow_mod 的 honest 域(base/exp ≤ 2^53)未被 holdout 實測涵蓋** → 將 exp 截斷為 uint32 的
  C 變異體能通過 gate(base/exp 最大值僅取到 1e6/1e5,高位約 33 位元未被涵蓋)。**修正**=在 holdout
  中新增 2^53 邊界情形([2,2^53,7]·[2^53,2^53,2^32-1] 等)+ 將隨機數擴大到 [0,2^53] 全域。**重現
  確認**:修正後 exp→uint32 變異體的 `passed=False`。
- **[LOW] gcd(2^53 守衛)/sieve(5,000,000 上限)存在同類未被涵蓋的邊界** → 將 gcd 邊界補入 holdout
  (確認變異體被證偽),sieve 在上限處 Python 參照較慢(約 7.7s)故用**專用 C-only 測試**驗證 n=5,000,000
  被接受(π=348513 · 用獨立 numpy sieve 核算)· n=5,000,001 被拒絕。
- **[MED] -ffast-math / -ffinite-math-only 會消除 NaN 守衛** → 用 fast-math 編譯出貨的 C artifact 會
  使 `x >= 0.0` 的 NaN 拒絕被省略、執行 `(long long)NaN` UB(**自行重現**:`gcd_seq([NaN,6])` 在
  `-ffinite-math-only` 下得 2.0,而 gate 預設的 `-ffp-contract=off` 下得 0.0)。**修正**=在
  `algo_codegen.emit_c` 中注入 `#if __FAST_MATH__ || __FINITE_MATH_ONLY__ → #error`(使 artifact
  不會 silent miscompile,而是**拒絕建置** = fail-closed)+ 將 C 註解中「UB 不可達」的說法誠實地更正為
  以 IEEE 為前提 + 新增拒絕 fast-math 建置的測試。
- **[MED] C 端的短小輸入守衛(pow_mod 的 `n<3` / sieve 的 `n_in<1`)無法被證偽** → 全部 holdout 均為
  固定長度,刪除守衛導致 OOB heap read 也全部通過測試。**修正**=在 holdout / parity 測試中加入
  空 · 短小陣列以行使邊界路徑。**honest 揭露**:黑箱值比較**在原理上**無法確定性地捕捉安全守衛被
  刪除(因 OOB 讀取值本身不確定)。本應由 ASan 正面解決,但**ziglang 的 ASan 在本 Windows 環境下
  無法連結**(`__asan_shadow_memory_dynamic_address` 未定義)。Python 側守衛可確定性證偽 · C 側可
  透過邊界行使 + sanitizer 捕捉(受環境限制、自動化暫緩)。
- **[MED] pow_mod 的 `1 % mod` 特殊分支無法被證偽**(exp==0 且 mod==1 同時成立的情形不存在於任何
  用例)→ 在 holdout 中新增 [7,0,1]·[0,0,1] + 已知解斷言(**重現確認**:`1%mod→1` 變異體的
  `passed=False`)。
- **[MED] P5 的 oracle 在域外輸入時崩潰**(zlib.crc32 / pow() / int(nan) 會拋例外)→ 一旦在 holdout
  中加入域外情形,difftest 就會拋出例外 = gate 在結構上**無法涵蓋**守衛規約(只有 1 個 unit test 能
  捕捉)。**修正**=將各 P5 oracle **域感知化**(用 `_int_in` 精確鏡射 op 的宣告域 → 域外時回傳 op 的
  fail-soft 值 0.0/[]、避免崩潰)。這樣 gate 本身就能證偽守衛發散(**重現確認**:刪除 crc 整數性 ·
  縮小 gcd 守衛的各變異體 `passed=False`)。
- **[LOW] Studio 的 Operator-help 卡片對 general op 顯示「Two knobs a,b」的不實資訊**(P1.5b 已堵住
  picker,但 browser 選取時的 `op_help_html` 回退未設防、波及全部 20 個 algo op)→ 在 `op_help_html`
  中新增 general 分支(展示 provenance + packed-input 契約 + CLI 執行方式)+ 在 `_op_row`/
  `api.algo_rows` 中新增 `desc`(op.doc)+ 回歸測試。
- **[LOW] image-processing skill 的 YAML frontmatter description(自動觸發面)只宣傳了 P1**(body 已
  更新到 20 個 op)→ 將 description 中的 algo 一節擴充到 P2–P5 全部範圍 + 觸發詞(primes/modular
  exponentiation/CRC-32/RLE/shortest path)。
- **5 項 REFUTED**(經驗證駁回):均為現行程式碼正確,finding 誤認了實際行為(驗證代理透過實際執行
  反證)。
- 審查後:5 個 P5 op 的 difftest 均為 python exact / C 逐位元一致 / c_verified=true,全部套件
  **4742 passed / 0 failed**(審查修正新增測試 +6)· 我新增檔案 ruff clean · mypy 新增 0。work-graph
  的 5 個節點也在修復後重新 gate 化(done)。

## P6 完成紀錄 — 計算幾何(2026-08-17, Opus5[1m]/ultracode, 12h 自律 · `graph-loop-engineering`)
**為 algo tier 新增 3 種幾何演算法**(algo-c 路線圖 P1→P5 完成後的擴充 = P6。對應最初 TOC 中的
「幾何 = 凸包/線段相交」)。**也是通向影像 tier 中輪廓/區域處理的橋梁**。將 2-D 點打包進輸入
seq,用**整數座標**(各 [-100000, 100000])使全部方向判定/鞋帶和都成為**嚴格整數**運算(完全不使用
浮點除法)= C 逐位元一致,且 Python==獨立 oracle tol 0。
- **op(3 個)**:
  - `polygon_area2`(KIND_REDUCE):用鞋帶公式求多邊形的 **2 倍帶正負號面積**(正負號 = 繞行方向)。
    oracle=numpy 向量化鞋帶公式(`dot`+`roll` = 不同程式碼路徑)。**honest 域**:座標 ≤1e5 · n ≤1e5
    時和最大為 2e15 < 2^53(用箱形繞行螺旋實測為 exact)。
  - `point_in_polygon`(KIND_REDUCE):用交點數(射線投射法)判定內外。用整數叉積判定交點(不含
    除法)。oracle=**卷繞數演算法**(與交點數不同的方法,兩者在簡單多邊形的嚴格內外判定上一致)。
    對凹多邊形也正確(已驗證 notch=outside)。**邊界(邊上)的點視為實作相關**,故已從 holdout 中
    排除(因交點數與卷繞數在邊界處可能分歧,已揭露)。
  - `convex_hull`(**KIND_MAP**):用 Andrew 的 monotone chain 求凸包。輸出為**從字典序最小頂點開始的
    CCW 順序**頂點列表(共線點被排除 = strict hull · 與 scipy 一致)。oracle=`scipy.spatial.ConvexHull`
    的**頂點集合**比較(順序另由 C-vs-Python 逐位元一致來保證)。退化情形(distinct 點數不足 3 / 全部
    共線)兩者均回傳 [] 做 fail-soft。已提前用**2000 組隨機點集**實測與 scipy 的不一致數為 0。
- **KIND_MAP**:convex_hull 的輸出 ≤ 輸入長度(頂點數 ≤ n),但仍沿用兩段式 size-probe(上界 2n)。
- **honest gate 實測(3 個 op 均 passed=True · c_verified=true · ziglang cc)**:Python==獨立 oracle
  diff 0.0 / C==Python 逐位元一致 diff 0.0。
- **work-graph op 波**:3 個幾何 op 也做成 `algo_gate` 節點(`1 op = 1 節點`)→ 用 `run-once` 實現
  無人值守完成(全部 algo op 達到 23 個 · 均已 gate 化)。
- **回歸**:在 `tests/test_algo.py` 中新增幾何測試群組(已知解 · 與 scipy/numpy/matplotlib/卷繞數等
  多個獨立 oracle 核對 · 凸性/CCW/點內含的結構驗證 · fail-soft · 退化情形 · no-mutation · python
  exact · C 逐位元一致)。全部套件從 **4742 增至 4765 passed / 0 failed**(+23)· ruff clean · mypy
  新增 0。

### P6 對抗性審查(2026-08-17, [[feedback_no_solo_ai_judgment]])
並行實施了 2 場獨立對抗性審查 Workflow(各項 finding 均由驗證代理以實際 compile/執行/壓力測試重現):
- **P6a(polygon_area2 / point_in_polygon,4 個視角 · 102 次工具呼叫)= findings 0**。geometry-
  correctness / C-safety / gate-honesty / integration-focus 全部為零(整數嚴格 · 邊界已揭露 · 2^53
  域已事先實測)。我也已用最壞情形(箱形繞行螺旋 n=1e5)實測 2×面積=2.0e15 < 2^53,確認 op==numpy==C
  一致。
- **P6b(convex_hull,3 個視角 · 85 次工具呼叫)= 1 項原始 → 0 項 CONFIRMED**(1 項 REFUTED)。唯一的
  指摘「刪除 dedup 的變異體能通過 difftest」經驗證被**駁回為非缺陷**:去重本來就已由 strict `<=0` 的
  monotone-chain pop 以及 `hv<3` 的後置檢查保證,是**防禦性冗餘**(兩個 backend 即使都刪除去重效果也
  等價,在 200,000 個重複多點集合上分歧數為 0)。驗證代理獨立確認了**2n 的 size-probe 是緊湊不
  超量的上界**(拋物線輸入下 out_len=2n)/ **ASan+UBSan 在 1104 個敵對案例上乾淨**(out[] 寫入無
  OOB · long long 叉積無 overflow)/ C==Python 逐位元一致 · Python==scipy 頂點集合完全一致 /
  CCW-from-lex-min 順序也已用測試保證 / qsort 的不穩定性因(x,y)全序比較子 + 相鄰去重而無影響
  (=`sorted(set())`)。→ 僅補充說明 dedup 屬於防禦性冗餘的註解(行為不變)。
- **結論**:P6 的 3 個幾何 op 未發現出貨缺陷。commit + push 已在本工作階段完成(`24bc8ad`)。

## P7 完成紀錄 — 線段相交(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**幾何工具集擴充 1 個 op**:`segments_intersect`(KIND_REDUCE)= 判定 2 條封閉線段
`[x1,y1,x2,y2,x3,y3,x4,y4]` 是否相交(1.0/0.0)。**是通向影像的直線/輪廓分析的橋梁**。採用 CLRS
33.1 的整數方向判定法(proper crossing = 端點嚴格跨越對方線段 + 4 個共線 on-segment 特殊情形)。整數
座標 [-100000,100000] 下叉積嚴格精確(|cross| ≤ 8e10 可放入 long long)= C 逐位元一致。**oracle =
`sympy.geometry` 的 Segment 相交判定**(符號運算 = 與方向判定完全不同的方法)。實測:8 個固定情形
全部正確 + **與 sympy 在 2970 組隨機整數線段對上不一致數為 0**(含共線重疊/T 字形/共享端點/near-miss)。
退化(點)線段因 sympy 無法建構 Segment,已從 holdout 中排除(op 本身用通用方向判定邏輯可處理,但
未納入 gate = 已揭露)。difftest passed(python exact / C 逐位元一致 / c_verified),work-graph 節點
無人值守完成(全部 algo op 達到 24 個 · 已 gate 化)。

### P7 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 個視角的對抗性審查(驗證代理以實際 compile/執行重現)= **1 項原始 → 1 項 CONFIRMED**(MED ·
gate-honesty)。**op 本身正確**(與 sympy 完全一致),但**difftest holdout 從未以單獨理由驅動過
d1/d3/d4 的 on-segment 特殊情形(端點落在對方線段內部 = 無共享端點)**,導致刪除該分支的錯誤 op
能通過 gate(50 個 holdout 的判定結果一個也沒變化)。已自行重現確定(丟棄 d3+d4 的變異體
passed=True ·`[0,0,10,0,3,0,3,5]`→錯誤得到 0.0)。**修正**=為各 on_seg 分支(d1/d2/d3/d4)新增以
單獨理由驅動的固定 holdout 情形(端點在對方線段內部 · 軸平行 4 個 + 對角 2 個)→ 已自行確認**任意
丟棄 d1/d2/d3/d4 中的一個分支都會使 difftest FAIL**(均為 passed=False)。已知解測試中也新增了
4 個端點-內部情形。全部套件從 **4765 增至 4772 passed / 0 failed**(+7)· ruff clean · mypy 新增 0。

## P8 完成紀錄 — 搜尋/選擇(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**為 algo tier 新增 2 種搜尋/選擇演算法**(從幾何轉向另一個領域以均衡 tier)。基於比較,可處理任意
(NaN-free)double,結果為 index 或既有元素,故 exact(tol 0)· C 逐位元一致。
- **op(2 個)**:`binary_search`(KIND_REDUCE):在已排序列 `[target, v0..v_{n-1}]` 中求 target 的
  **最左 index**(lower bound),不存在則為 -1.0。oracle=`bisect_left` + 存在性確認(獨立)。/
  `kth_smallest`(KIND_REDUCE):`[k, v0..]` 中第 k 小的值(0 索引 order statistic),用
  **quickselect**(median-of-three pivot · Lomuto)。**第 k 個值與順序無關**,故即使 pivot 順序不同
  也 C==Python 逐位元一致。oracle=`sorted()[k]`(Timsort = 不同演算法)。median-of-three 使已排序輸入也
  是 O(n)(n=40001 時 <2s)。
- **honest gate 實測**:兩個 op 均為 passed=True · python exact / C 逐位元一致 / c_verified。已事先
  用**各 5000 組隨機情形與 oracle 核對不一致數為 0**。fail-soft = binary_search 在空/不存在時為
  -1.0,kth_smallest 在 k 超域/非整數/空時為 0.0。
- **work-graph**:2 個 op 也用 `algo_gate` 節點無人值守完成(全部 algo op 達到 26 個 · 已 gate
  化)。回歸 = 在 `tests/test_algo.py` 中新增 P8 測試群組(已知解 · 與 bisect/sorted 核對 · O(n²)
  防護 · fail-soft · no-mutation · python exact · C 逐位元一致)。ruff clean · mypy 新增 0。

### P8 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 個視角的對抗性審查(實際 compile/執行驗證)= **1 項原始 → 1 項 CONFIRMED**(LOW · correctness)。
**正確性不變,但存在效能缺陷**:kth_smallest 的 quickselect 因單一 pivot(Lomuto)而在
**all-equal/低基數大輸入下呈 O(n²)**(median-of-three 無法保護重複值 · n=40000 全相等時耗時
7.44s,sorted/reverse 則很快)。測試的 holdout 僅 n≤30、計時測試只有 sorted 情形,未能捕捉。
姊妹 op quicksort 已在使用 3-way(Dutch flag)分割。**修正**=將 kth_smallest 改寫為
**3-way(Dutch national flag)分割**(用 equal-band 把重複值折疊 → 使 all-equal 變為 O(n) · 僅用
比較且與順序無關 → **維持 C==Python==sorted()[k] 的 parity**)。已自行重現確認:**all-equal
n=40000 從 7.44s 降至 0.0019s**(實現 O(n) 化)· correctness 的 5000 組情形不一致數為 0 · difftest
逐位元一致。計時測試已擴充到 sorted/reverse/**all_equal/few_distinct**(實際防護退化)。

## P9 完成紀錄 — 統計/彙總(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**為 algo tier 新增 2 種統計 op**:`count_distinct`(去重值數量 = 整數 count)/ `mode_value`
(眾數 · 值較小者優先 tie)。均基於比較(任意 NaN-free double),結果為 count 或既有元素,故 exact
(tol 0)。兩個 op 均先複製並排序,再做單趟掃描(結果與順序無關,故即使 C 的 qsort 與 Python 的
sorted 順序不同也逐位元一致)。oracle=`len(set())` / `collections.Counter`(獨立機制)。
**★主動強化**:當 mode_value 的眾數為零且 ±0.0 混雜時,C 的不穩定 qsort 與 Python 的穩定 sort 可能
回傳正負號不同的值而導致逐位元不一致 → 用 **`+ 0.0` 把 −0.0→+0.0 正規化**(其他值不變)使 C==Python
更加穩健(與 rle_encode 的帶正負號零揭露同屬一類)。實測:各 5000 組隨機情形與 oracle 的不一致數為
0 · difftest passed(python exact / C 逐位元一致 / c_verified)。全部 algo op 達到 28 個 · 已 gate 化。
ruff clean · mypy 新增 0。

### P9 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 個視角的對抗性審查(實際 compile/執行/變異驗證)= **1 項原始 → 1 項 CONFIRMED**(MED ·
gate-safety)。**正確性不變,但存在 gate 覆蓋缺口**:holdout 無法證偽刪除 mode_value 的 `+0.0`
正規化這一變異體(唯一的帶正負號零情形 `[0.0,-0.0,0.0]` 在兩個 backend 中都被排序為 +0.0 在末尾,
刪除正規化也仍然逐位元一致)。註解聲稱能擔保的逐位元檢查從未真正驅動過該正規化。**修正**=在 holdout
中新增 `-0.0` 不落在 run 末尾的情形 `[0.0,-0.0]`·`[-0.0,0.0]`(兩種順序,無論 qsort 的 tie 順序如何
必有一方會發散)。已自行重現確認:**刪除正規化的變異體使 difftest FAIL**,現行(已正規化)程式碼在
新增情形下逐位元一致 pass。全部套件從 **4787 增至 4796 passed / 0 failed**。

## P10 完成紀錄 — 數論(第2部分)(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**新增 2 種數論 op**(建立在 P5 的整數機制之上 · 共享 category numtheory)。整數以 float64 承載
(exact <2^53)· 在 honest 域內全部模乘積都能放入 uint64/long long = C 逐位元一致,且 Python==獨立
oracle tol 0。
- **op(2 個)**:`is_prime`(KIND_REDUCE):**確定性 Miller-Rabin**(witness {2..37})。honest 域為
  0≤n≤2^32−1(a·a mod n 能放入 uint64 · witness 集合確定性成立至 n<3.3e24 為止,可證明質性)。
  oracle=`sympy.isprime`。★能正確判定 Carmichael 數(561/1105/1729/2465…)為合數。/
  `modular_inverse`(KIND_REDUCE):用**擴充歐幾里得演算法**求 a^−1 mod m(gcd≠1 則 −1.0)。域為
  a≤2^53 · m≤2^53(Bezout 係數的不變量 |q·s|=|old_s−new_s|≤2m 能放入 long long)· m=1→0。將 C 的
  截斷取模正規化到 [0,m−1](+m)使其與 Python 的向下取整取模一致。oracle=內建 `pow(a,−1,m)`。
- **honest gate 實測**:兩個 op 均為 passed=True · python exact / C 逐位元一致 / c_verified。已事先
  用 **is_prime 與 sympy 在 8000 組隨機 + 2000 組窮舉(含 561 等 Carmichael 數)上核對不一致數為
  0 / modular_inverse 與 pow 在 8000 組上核對不一致數為 0** 實測。全部 algo op 達到 30 個 ·
  已 gate 化。ruff clean · mypy 新增 0。

### P10 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 個視角的對抗性審查(實際 compile/執行/變異驗證)= **1 項原始 → 1 項 CONFIRMED**(MED ·
c-safety-gate)。**op 本身正確且 overflow-safe**(已用 353 個敵對情形驗證),但
**modular_inverse 的 holdout 未驅動到宣告域 2^53**(in-domain 的 m 最大只到約 1e9),使 C 的
`long long→int` 窄化變異體(破壞 2^53 域)能以逐位元一致通過 gate。姊妹 op pow_mod(base=exp 已固定在
2^53)/ gcd_seq(已固定 2^53 守衛邊界)/ is_prime(近 2^32)都能捕捉同類變異體,唯獨 modular_inverse
未涵蓋。**修正**=在 holdout 中新增 2^53 邊界情形(`[2, 2^53−1]` coprime → inverse · 接近 2^53 的大
coprime 值 · `[2^52, 2^53]` 均為偶數 → −1,使 Bezout 運算驅動 |q·s|~2m~2^54)。已自行重現確認:
**`long long→int` 變異體使 difftest FAIL**,baseline 逐位元一致 pass。oracle(pow)已經能對應,故僅
新增 holdout。全部套件全綠。

## P11 完成紀錄 — 位元運算(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**新增 2 種位元運算 op**:`xor_reduce`(全部元素的位元 XOR)/ `popcount_total`(全部元素的 1 位元總數 =
Kernighan 演算法)。用 float64 承載非負整數,域 [0, 2^53−1] 內全部值可放入 53 位元(XOR 結果也
< 2^53=exact · popcount 是較小整數)= C 逐位元一致,且 Python==獨立 oracle
(`functools.reduce(operator.xor)` / 內建 `int.bit_count()` = 與 Kernighan 不同的機制)tol 0。
兩個 op 均為 passed=True · python exact / C 逐位元一致 / c_verified。已事先用各 3000 組隨機情形與
oracle 核對不一致數為 0。fail-soft = 負數/非整數/≥2^53 時為 0.0。全部 algo op 達到 32 個 ·
已 gate 化。ruff clean(以 FURB161 將 `bin().count('1')`→`.bit_count()` 化)· mypy 新增 0。

### P11 對抗性審查結果(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 個視角的對抗性審查 Workflow(correctness + gate-safety,`wf_7d130631-c0f`)= **findings 0
(無缺陷)**。審查者 1 得到 `{findings:[]}`,審查者 2 在做「gate mutation testing(破壞實作看 gate 能
否抓到)」過程中因 window 壓縮而中斷(未產出結果)。**依規律不去復活死掉的 background,而是由我
用同樣的 mutation test 親自第一手完成驗證**:對 xor_reduce/popcount_total 的代表性 7 種變異體(空
初始化 acc=1 / 誤用 OR / 2^53 域邊界 off-by-one / 刪除負數守衛 / Kernighan→shift[popcount≠bitlength]
/ +2 誤差 / admit 2^53)在 holdout 上執行 → **全部 7 種變異體均被獨立 oracle 捕捉**(oracle_err >
0)。**結論 = P11 的 gate 可證偽 · 未發現確定缺陷**(`fed093a` 正當、無需 follow-up commit)。

## P12 完成紀錄 — 擴充歐幾里得演算法(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**新增 1 種數論 op**(建立在 P5 的整數機制 + P10 的 Bezout 不變量之上 · 共享 category
numtheory=P5+P10+P12)。`extended_gcd`(**KIND_MAP**):輸入 `[a, b]`(非負整數 ≤ 2^53)→ 輸出
`[g, x, y]`(**嚴格 3 值**,滿足 `a·x + b·y = g = gcd(a,b)`),域外為 `[]` fail-soft。用迭代版
two-variable sweep 計算係數。**係數為嚴格精確**(不變量 `|q·s| = |old_s − new_s| ≤ 2·max(a,b) ≤
2^54` 能放入 C 的 long long)故 C==Python 逐位元一致。域為 **[0, 2^53] 含端點**(2^53 為 exact ·
係數 |x|,|y| ≲ 2^52 在 float64 也是 exact)。
- **★oracle 獨立性要點(P10 的教訓)**:Bezout (x,y) 不唯一,故「`a·x+b·y==g`」這一**恆等式驗證**無法
  讓 gate 證偽正負號/正規形式的差異。→ oracle 改為用**獨立的遞迴版擴充歐幾里得 `_ext_gcd_rec`
  (不同程式碼路徑)計算 (g,x,y) 並逐元素比較**。迭代版與遞迴版回傳相同的 canonical 係數(展開遞迴
  即得迭代版 = 數學上一致,已確認 `[0,b]`/`[a,0]`/`[0,0]`/相等值等全部端點也一致)。
- **honest gate 實測(passed=True · c_verified=true · ziglang cc · 70 個用例)**:python==獨立遞迴
  oracle **diff 0.0(exact)** / codegen **C==Python 逐位元一致 diff 0.0**。已事先實測=**在 200,000
  組隨機資料(含 2^53 域端)上迭代版 op == 遞迴 oracle 不一致數為 0,且 `a·x+b·y==g==math.gcd(a,b)`
  的恆等式(用 bignum 獨立核算)失敗數為 0**。fail-soft = 短小/非整數/負數/NaN/>2^53 → `[]`。
- **★gate mutation test(自行驗證)**:交換 x,y / 取反 x / 刪除 old_s 更新 / 放寬守衛(允許 >2^53)/
  錯誤長度這 5 種終止性變異體**全部被捕捉**(元素不一致或結構不一致 inf)。誤商 q+1 會使 op 本身
  陷入無限迴圈(由 difftest harness 的 timeout 偵測到失敗)= 全部會終止的錯誤實作都能被證偽。
- **holdout(以單獨理由驅動域端與全部分支)**:已知 `[35,15]→(5,1,-2)` 等 + coprime/非 coprime +
  相等值 `[7,7]` + 一方為 0(`[0,5]`/`[5,0]`/`[0,0]`)+ a=1 + **2^53 域端**(`[2, 2^53−1]` coprime ·
  接近 2^53 的大 coprime 值 · `[2^52, 2^53]` gcd 為 2^52 · `[2^53, 6]` 含端點上限)+ 域外 fail-soft
  (短小/`>2^53`=`[2^53+2,3]`/非整數/負數/NaN)+ 隨機 48 組。
- **work-graph op 波**:將 extended_gcd 做成 `algo_difftest --op` gate 節點(`1 op = 1 節點` ·
  priority 0 · tool capability · produces=gate JSON)→ `run-once --available tool:command` 實現
  **無人值守完成**(passed:true · c_verified · 產生逐位元一致標記)。= **全部 algo op 達到 33 個、
  均已 work-graph gate 化**(32→33)。
- **回歸**:在 `tests/test_algo.py` 中新增 P12 測試群組(已知值 · Bezout 恆等式隨機×5000 · 與獨立
  遞迴 oracle 一致隨機×5000 · fail-soft · category grouping[numtheory=P5+P10+P12] · difftest
  python exact · C 逐位元一致)。全部套件 **4827 passed / 0 failed**(test_algo.py 單體 260 個)· 我
  的全部改動 ruff clean · mypy 新增 0(與 origin/master 的 15 個相同 = net-new 0)。

### P12 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 個視角的對抗性審查 Workflow(correctness / c-safety+gate-honesty / integration,各項 finding 均由
驗證代理**以實際 compile/執行的 mutation 重現**,5 個 agent · 125 次工具呼叫)= **2 項原始(同一
根本原因)→ 1 項 CONFIRMED**(MED · gate-cannot-falsify)。**op 本身正確**(已在 20 萬組 + 全部端點
上驗證 · 與遞迴 oracle 不發散 · 域內無 long long overflow),但**difftest holdout 的域外情形全部
集中在 operand `a` 一側**(`[2^53+2,3]`/`[2.5,7]`/`[-1,7]`),唯一的 bad-`b` 情形 `[7,NaN]` 因
NaN 在 `bd>=0.0` 處即短路,一次也沒能單獨驅動 b 的 3 個守衛分支 → **b 側守衛的單側退化(a/b 是
複製對稱程式碼,因而看似合理)能同時穿過兩個 gate 的一半**(與 P5/P7/P9/P10 相同的 gate-coverage
教訓)。**自行重現確定**:從 _PY/_C 兩側同時刪除 `bd>=0`/`bd<=2^53`/`bd==int` → **全部
`passed=True`(未被捕捉)**,而對稱的 a 側刪除全部 `passed=False`(已被捕捉 · 因 a 的域端在
holdout 中)。**修正**=在 holdout 與 fail-soft 測試中新增 `[valid_a, finite_bad_b]` 情形
(`[3, 2^53+2]`·`[7,-1]`·`[7,2.5]`)→ 重新實測後 **b 側 3 處刪除全部被捕捉(passed=False,
pydiff=inf)**、baseline 在 70 個用例上逐位元一致 pass。★**採納驗證代理的 honest 修正(駁回 finding
中的過度斷言)**:「刪除 `bd<=2^53` 會使 b=2^62 時 C long long 發生 overflow UB」這一說法**不準確**
——b=2^62 時 C(long long)與 Python(bignum)逐位元一致(無 overflow)。真正的問題是**輸出的精度
損失**(Bezout 係數在 > 2^53 時無法用 float64 嚴格表示,導致 `a·x+b·y==g` 被破壞),`b<=2^53` 的
上限正是為守護此精度。機制描述有誤,但缺陷本身與修復方案成立 = 予以採納。

## P13 完成紀錄 — 最近點對(分治法)(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**幾何工具集再擴充 1 個 op(P6/P7 之後的第 2 彈)**:`closest_pair`(KIND_REDUCE)= 用**分治法**
(CLRS 33.4)求 2-D 整數點集的**最小平方距離**。輸入 `[x0,y0,x1,y1,...]`(2n 個 · 整數座標
[-1e5,1e5])→ 輸出 = 最小平方歐氏距離(整數嚴格精確)。**僅用平方距離(不開根號)**,故封閉於
long long/整數 float64,C==Python 逐位元一致。最大平方距離 = (2e5)²×2 = 8e10 < 2^53=exact。
fail-soft = 點數 <2(n<4)/ 長度為奇數 / 座標非整數或超出 [-1e5,1e5] 域 → -1.0。
- **演算法**:按 x 排序(相等按 y)→ 遞迴左右兩半 → d=min(dl,dr) → 從中線開始蒐集
  (x−midx)²<d 的點建構 strip → strip 按 y 排序 → 從每個點向前掃描(僅在 `(yj−yi)²<d` 期間 = 7
  近鄰上界)。base(m≤3)用暴力法。重複點(距離 0)因相同 x 相鄰排序,即使跨越分割線也會被 strip
  拾取。C 在 op.c_code 內定義 `CpPt` 結構體 + `cp_rec` 遞迴 + `cp_cmp_x/cp_cmp_y`(qsort)
  (codegen 會將 c_code 原樣插入,故可定義 static helper)。strip 緩衝區在遞迴間共用一份(子呼叫先
  完成 = post-order,故無別名衝突)。遞迴深度約 log2(n)(n=1e5 時為 17)= 堆疊安全。
- **honest gate 實測(passed=True · c_verified=true · ziglang cc · 58 個用例)**:python==**獨立
  暴力 O(n²) oracle**(不排序、不用 strip 的不同程式碼路徑)**diff 0.0(exact)** / codegen
  **C==Python 逐位元一致 diff 0.0**。已事先實測=**30,000 組隨機資料(用 R=3/8/30 的聚簇驅動 strip
  深度)+ 16,000 組敵對版面(密集網格/縱橫直線[全部點都在 strip 內]/微小聚簇/邊界座標)與暴力法
  不一致數為 0**。
- **★gate mutation test(自行驗證)**:省略 strip 掃描 / sq 忽略 y / 刪除座標上限 / 刪除座標下限 /
  刪除整數性 / strip 為空這 6 種變異體**全部被捕捉**(passed=False)。cross-strip 最小情形
  ([-5,-5,-1,0,1,0,5,5]→4)單獨驅動了 strip 邏輯,兩個座標槽的域外情形單獨驅動了守衛。
- **holdout**:已知(單對 25 · 3 點 · 重複 dist0 · 縱向一列 · **cross-strip 最小**)+ 極端
  in-domain 座標(8e10 上端)+ 在**兩個座標槽**上以單獨理由化的域外情形(奇數長度/單點/非整數
  x·y/±1e5 超出 x·y/NaN x·y)+ 隨機 40 組(聚簇)。
- **work-graph op 波**:將 closest_pair 做成 `algo_difftest --op` gate 節點(`1 op = 1 節點`)→
  用 `run-once` 實現無人值守完成。= **全部 algo op 達到 34 個 · 均已 work-graph gate 化**(33→34)。
- **回歸**:在 `tests/test_algo.py` 中新增 P13 測試群組(已知值 · 暴力法一致隨機×4000 ·
  fail-soft[兩個座標槽] · category grouping[geometry=P6+P7+P13] · difftest python exact · C
  逐位元一致)。全部套件 **4834 passed / 0 failed**(+7)· ruff clean · mypy 新增 0(與
  origin/master 的 15 個相同)。對抗性審查結果見下(1 項 CONFIRMED,已自行重現並修正)。

### P13 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 個視角的對抗性審查 Workflow(correctness / c-safety+gate-honesty / integration,各項 finding 均由
驗證代理**以實際 compile/執行的 mutation 重現**)= **3 個視角收斂到同一根本原因 → 1 項 CONFIRMED**
(severity = 我最初評為 MED / **驗證代理評為 HIGH**,認為 gate-honesty 失敗[gate 會 green-light 錯誤
op]更嚴重。作為 honest 揭露兩種評價並陳,修正內容相同)。**op 本身正確**(在 3 萬+1.6 萬組敵對情形
上與暴力法不一致數為 0),但**difftest holdout 從未驅動 strip 的 y-scan 超過 immediate
neighbor(j==i+1)**→ 將 strip 前向掃描收窄至**僅 j==i+1** 的退化能被 gate 放行(因 7 近鄰定理指的是
「至多 7 個」而非「恰好 1 個」,按 y 序存在非相鄰的最近點對是可能的)。**自行重現確定**:將掃描範圍
收窄為 `range(i+1, min(i+2, sc))` 的 mutation 同時套用到 _PY/_C → `passed=True`(未被捕捉)。已在
整數網格中搜尋並發現能證偽該缺陷的最小情形(例如 `[0,-6,-2,-2,4,-3,-5,3]`= 最近點對在 y 序上相隔
2 個位置 → 完整/暴力法得 20,而僅 j==i+1 得 25)。**修正**=在 holdout 與已知值測試中新增 strip 內
最近點對在 y-sorted 中非相鄰的 3 種情形(`[0,-6,-2,-2,4,-3,-5,3]`→20 /
`[-4,5,-1,-3,0,-1,3,-3]`→5 / `[-1,-6,-1,0,-5,-4,1,-4,4,4]`→8)→ 重新實測確認 **j==i+1-only 的
mutation 被捕捉(passed=False, pydiff=12)**、baseline 在 61 個用例上逐位元一致 pass、其他 5 個
mutation 無回歸。在既有的 6 種 mutation(省略 strip/sq 忽略 y/座標上下限/整數性/空 strip)基礎上,
strip 掃描深度也變得可證偽(將 P12 的 gate-coverage 教訓擴展到幾何領域的 strip 掃描)。

## P14 完成紀錄 — Huffman 最佳前綴編碼成本(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**資料壓縮再擴充 1 個 op(P5 的 rle_encode 之後的壓縮第 2 彈)**:`huffman_cost`(KIND_REDUCE)= 給定
符號頻率 `[f0,f1,...]`(非負整數 ≤2^40),求**最佳前綴(Huffman)編碼的最小總成本**(=全部內部節點
合併權重之和 = Σ freq×編碼長度)。**★核心 = 最佳成本對 tie 不變**(每個符號的編碼長度會隨 tie
打破方式改變,但總成本由頻率多重集合唯一決定),故即使 C 與 Python 以不同順序取出等權元素,
**總和依舊相同 = 逐位元一致能乾淨地成立**。整數用 long long 承載(透過域守衛約束在 < 2^54,無
overflow)。
- **演算法 = 兩佇列法**(Huffman O(n log n)):將頻率遞增排序放入 q1[葉],q2[合併節點]非遞減地產生 →
  每次從 q1/q2 各自的佇列首取最小 2 個、把合併和 s 計入 total 並放入 q2 佇列尾(重複 n−1 次)。C 也用
  兩個陣列 + 兩個佇列首 index 實作同一演算法(qsort 比較子 hc_cmp)。
- **域與 fail-soft**:各頻率 0≤f≤2^40(整數)· 否則 -1.0。**當 merge total 超過 2^53 時為
  -1.0**(float64 無法嚴格表示)= **對精度關鍵的 exactness 分支(可證偽)**。守衛過程中累計總頻率
  total_freq,超過 2^53 時提前回傳 -1.0 = long long safety(每個 s≤total_freq≤2^53 ·
  total≤2^54<2^63)。n=0/1 → 0.0。★**honest 揭露**:上游的 total_freq 守衛是為「頻率總和本身會使
  long long 溢位的極端 n(>約 4M 個符號)」設置的 safety guard,在現實的 n 下會回傳與 merge bail
  相同的 -1.0 = 單靠值比較難以單獨證偽(與 P5 的 OOB 守衛揭露同型)。守護 exactness 的 merge-total
  bail 可由 holdout 中的 `[2^40]×1024`(總和 2^50<2^53 通過上游 · 成本約 2^53.3 觸發 merge
  bail)單獨驅動 = 可證偽。
- **honest gate 實測(passed=True · c_verified=true · ziglang cc)**:python==**獨立 heapq(最小堆積)
  版 Huffman 成本**(與兩佇列法不同程式碼路徑)**diff 0.0(exact)** / codegen **C==Python 逐位元一致
  diff 0.0**。已事先實測=**在 5 萬組隨機資料(全相同頻率/0 頻率/2^40 域端驅動 tie)上與 heapq 不
  一致數為 0** ·**在 4000 個微小情形上與全部合併順序暴力求出的 true optimum 不一致數為 0**
  (=貪婪達到最佳)·**在 2 萬組上與反 tie 順序堆積不一致數為 0**(=證明 tie 不變性)。
- **★gate mutation test(自行驗證)**:刪除頻率上限 / 刪除負數守衛 / 刪除整數性 / **停用
  merge-total bail**(能被 `[2^40]×1024` 證偽)/ 合併時丟棄 x2 / n==1 回傳 1.0 這 6 種數值分支
  變異體**全部被捕捉**(passed=False)。
- **work-graph op 波**:將 huffman_cost 做成 `algo_difftest --op` gate 節點(`1 op = 1
  節點`)→ 用 `run-once` 實現無人值守完成。= **全部 algo op 達到 35 個 · 均已 work-graph gate
  化**(34→35)。
- **回歸**:在 `tests/test_algo.py` 中新增 P14 測試群組(已知值 · heapq 一致隨機×5000 ·
  fail-soft/overflow · category grouping[compress=P5+P14] · difftest python exact · C 逐位元
  一致)。全部套件 **4841 passed / 0 failed**(+7)· ruff clean · mypy 新增 0(與
  origin/master 的 15 個相同)。

### P14 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 個視角的對抗性審查 Workflow(correctness / c-safety+gate-honesty / integration,各項 finding 均由
驗證代理**以實際 mutation 重現**)= **3 項 CONFIRMED**(均為 merge overflow bail 邊界的
gate-coverage 問題 · op 本身正確、tie 不變性也已在 5 萬+4000+2 萬組資料上確定)。**correctness 相關
的指摘為 0**(tie 不變性的主張、兩佇列法的最佳性均穩健)。CONFIRMED 全部集中在「merge-total>2^53 的
fail-soft 邊界」的覆蓋上:
- **[MED] 閾值在約 6 個數量級內未被固定**(把 merge-total 的閾值 2^53 收窄為 2^50 等的變異體能
  通過 gate)= **自行重現確定**(2^53→2^50 的變異體 passed=True)。**修正**=在 holdout 中新增
  `[2^40]×837`(成本 8997303650091008 ≈ 2^52.998 · VALID · 應嚴格回傳)+ `[2^40]×838`(成本 > 2^53
  → -1.0),將閾值**緊固定在 2^53 的 ±約 1e13 範圍內**→ 重新實測後閾值收窄變異體(2^53→2^50、
  →8e15)全部被 **CAUGHT**。已知值測試中也新增了 837/838。
- **[MED] cost 恰好等於 2^53 的情形不在 holdout 中,導致 `>`→`>=` 的 off-by-one 未被捕捉 → 用
  WITNESS 修正**:最初曾打算揭露「在 freq ≤ 2^40 下 cost 不會恰好等於 2^53」,但**驗證代理發現了
  建構方法**=`2^16 個 × freq 2^33`(2^33 ≤ 2^40)在每一深度 16 下**cost = 2^16 · 2^33 · 16 恰好
  = 2^53**。2^53 可精確表示,屬於 VALID(應回傳 2^53),而 `>` 變為 `>=` 的變異體會將其誤判為
  -1.0。**我自己也做了一手驗證**(用 bignum 確認 cost==2^53 · 確認 op 回傳 2^53 · total_freq=
  2^49<2^53 能通過上游),之後**採納**該 witness 情形加入 holdout 與已知值測試 → 使 `>`→`>=` 的
  off-by-one 變得可證偽(用這一處單值邊界單獨 pin 住)。**對抗性審查不僅發現了 gap、還發現了
  修復方法本身的一個絕佳例子**(證偽了我最初「不可達」的判斷)。
- **[LOW] 上游 `total_freq > 2^53` 守衛分支未被驅動/無法證偽** = **honest 揭露**:這是為「頻率總和
  本身會使 long long 溢位的極端 n(>約 4M 個符號)」設置的 safety guard。在現實的 n 下 merge bail
  會回傳相同的 -1.0(即使刪除該守衛也不會 long long overflow、結果不變),故單靠值比較無法單獨
  證偽(與 P5 的 OOB 守衛揭露同型)。極端 n 的 holdout 因不現實的緩慢而不予新增。
- 驗證代理將這 3 項判定為「gate 無法證偽特定錯誤實作」的真實缺陷、判為 CONFIRMED。**op 的正確性
  不變**(未出貨錯誤 op),已用 #2 強化 gate 的覆蓋並對 #1/#3 做 honest 揭露。

## P15 完成紀錄 — 最長遞增子序列長度(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**搜尋/選擇再擴充 1 個 op(P8 binary_search/kth_smallest 之後的搜尋第 2 彈 · DP/patience sorting
新演算法族)**:`lis_length`(KIND_REDUCE)= 用 **patience sorting** 求任意 NaN-free double 數列的
**最長嚴格遞增子序列(LIS)長度**。僅用比較(不對值做算術運算),故長度由陣列本身唯一確定 =
**C==Python 逐位元一致**。tails[k] 保存長度 k+1 的遞增子序列的最小結尾,對每個元素在
`tails[mid] < x`(bisect_left · **嚴格**)位置替換或延伸結尾(O(n log n))。空 → 0.0,混有 NaN →
-1.0 fail-soft(用 `x != x` 偵測)。
- **honest gate 實測(passed=True · c_verified=true · ziglang cc)**:python==**獨立 O(n²) DP
  oracle**(`dp[i]=1+max(dp[j]|j<i,a[j]<a[i])`,與 patience sorting 是不同程式碼路徑)**diff
  0.0(exact)** / codegen **C==Python 逐位元一致 diff 0.0**。已事先實測=**在 4 萬組隨機資料
  (整數+浮點、小範圍以大量產生 tie = 驅動嚴格比較)上與 DP 不一致數為 0**。
- **★gate mutation test(自行驗證)**:嚴格 `<`→`<=`(變為非遞減 = 不同答案)/ 刪除 NaN 守衛 /
  二分方向反轉 這 3 種變異體**全部被捕捉**(passed=False)。全相同的 `[2,2,2,2]`→1 與交替重複
  情形單獨驅動了嚴格比較,NaN holdout 驅動了守衛。
- **holdout**:已知(`[3,1,2,4]`→3 ·`[5,4,3,2,1]`→1 · 全遞增→n · 空→0 · 單元素→1)+
  **全相同→1(嚴格比較下重複不延伸)** + 交替重複 + -0.0/+0.0 相等值 + ±inf + 浮點 tie + 在
  **開頭/中間/末尾**放置 NaN 做 fail-soft + 隨機資料(整數 tie 較多 + 浮點)。
- **C 安全**:tails 緩衝區 malloc(n)· 寫入 tails[lo] 時 lo≤len<n 無 OOB · n=0 時 malloc(1)+
  迴圈不執行回傳 0.0 · malloc 失敗回傳 -1.0 · NaN 守衛在全部比較之前(NaN 安全)。
- **work-graph op 波**:將 lis_length 做成 `algo_difftest --op` gate 節點(`1 op = 1 節點`)→
  用 `run-once` 實現無人值守完成。= **全部 algo op 達到 36 個 · 均已 work-graph gate 化**
  (35→36)。
- **回歸**:在 `tests/test_algo.py` 中新增 P15 測試群組(已知值 · DP 一致隨機×5000 · NaN
  fail-soft[3 個位置] · category grouping[search=P8+P15] · difftest python exact · C 逐位元
  一致)。全部套件 **4848 passed / 0 failed**(+7)· ruff clean · mypy 新增 0(與
  origin/master 的 15 個相同)。

### P15 對抗性審查結果(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 個視角的對抗性審查 Workflow(correctness / c-safety+gate-honesty / integration,mutation 驗證)=
**findings 0**(全部視角均無指摘)。已驗證 patience sorting 的嚴格比較 · NaN 守衛 · tails
緩衝區安全 · O(n²) DP oracle 的獨立性 · holdout 單獨驅動嚴格比較的能力,未偵測到可證偽的缺陷。
事先的 mutation 3/3 全部被捕捉(嚴格 `<`→`<=`/NaN 守衛/二分方向)與 4 萬組 DP 一致,說明 gate 穩健。

## P16 完成紀錄 — 逆序數(合併排序法)(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**統計再擴充 1 個 op(P9 count_distinct/mode_value 之後的統計第 2 彈)**:`count_inversions`
(KIND_REDUCE)= 用**計數合併排序**以 O(n log n) 求任意 NaN-free double 數列的**逆序數**
(i<j 且 a[i] > a[j] 的**嚴格**對數)。僅用比較(不對值做算術運算),故 count 由陣列本身唯一確定 =
**C==Python 逐位元一致**。合併時每當右列先取出一個元素,就把左列剩餘數量累加(經典做法)。count 為
非負整數,故 **-1.0 是安全 sentinel**:NaN→-1.0 fail-soft,空/單元素→0.0。相等值不算逆序(tie 時
先取左邊 = `arr[i] <= arr[j]`)。
- **honest gate 實測(passed=True · c_verified=true · ziglang cc)**:python==**獨立 O(n²) 暴力
  count**(與合併排序不同程式碼路徑)**diff 0.0(exact)** / codegen **C==Python 逐位元一致 diff
  0.0**。已事先實測=**在 4 萬組隨機資料(整數+浮點、小範圍產生大量 tie = 驅動嚴格比較)上與暴力
  法不一致數為 0**。
- **★gate mutation test(自行驗證)**:tie 處理 `<=`→`<`(將相等值誤計為逆序)/ inv 計數
  off-by-one / 刪除 NaN 守衛 / 不計數(inv=0)這 4 種變異體**全部被捕捉**(passed=False)。全相同
  `[2,2,2]`→0 與重複情形單獨驅動了嚴格比較。
- **holdout**:已知(sorted→0 · reversed→n(n-1)/2 ·`[2,1,3]`→1 ·`[3,1,2]`→2 · 空/單元素→0)+
  **全相同→0(嚴格性)** + 重複(sorted→0 ·`[2,1,2,1]`→3)+ -0.0/+0.0 相等值(兩種順序)+ ±inf +
  在**開頭/中間/末尾**放置 NaN 做 fail-soft + 隨機資料(整數 tie 較多 + 浮點)。
- **C 安全**:arr/tmp 用 malloc(n)· 遞迴深度 O(log n)· malloc 失敗回傳 -1.0 · NaN 守衛在全部
  比較之前。count 用 long long(對 n < 4.3e9 而言 n(n-1)/2 < 2^63),回傳的 double 在
  n(n-1)/2 < 2^53 時嚴格精確(honest:在極端 n 下可能不再嚴格,但 holdout/實用域內是嚴格的)。
- **work-graph op 波**:將 count_inversions 做成 `algo_difftest --op` gate 節點(`1 op = 1
  節點`)→ 用 `run-once` 實現無人值守完成。= **全部 algo op 達到 37 個 · 均已 work-graph gate
  化**(36→37)。
- **回歸**:在 `tests/test_algo.py` 中新增 P16 測試群組(已知值 · 暴力法一致隨機×5000 · NaN
  fail-soft[3 個位置] · category grouping[stat=P9+P16] · difftest python exact · C 逐位元
  一致)。全部套件 **4855 passed / 0 failed**(+7)· ruff clean · mypy 新增 0(與
  origin/master 的 15 個相同)。**對抗性審查在 worktree 隔離環境下執行**(源於 P14 的教訓 =
  審查代理曾 mutate 了目標 repo 的 algo.py,故 commit 後改在隔離 worktree 中審查 → 結果作為
  follow-up)。

### P16 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
**★worktree 隔離審查首次成功應用**:3 個視角 × 隔離 git worktree(各代理從 cd76da0 建立各自
專用副本並做 mutation)→ **本 repo 的 algo.py 始終保持乾淨**(驗證代理也明確記錄「real repo 為
唯讀 · 在隔離 worktree 中做 mutation · 已清理善後」)。結構性解決了 P14 的汙染問題。結果 =
**2 項 CONFIRMED(均為 LOW)** · correctness 相關為 0(op 正確):
- **[LOW gate-coverage] long long 位元寬度未被證偽**:holdout 的最大逆序數低於 INT_MAX(len ≤ 40 →
  最大約 700),使 C 的累加器由 `long long` 收窄為 `int` 的變異體能通過 gate(出貨程式碼本身正確地
  使用 long long)。**自行重現確定**(int 收窄變異體 passed=True · n=65537 的嚴格遞減中真值
  2147516416 > INT_MAX,int 會環繞為 -2147450880)。**修正**=(1)新增**獨立的 Fenwick(樹狀陣列)版
  oracle `_fenwick_inversions`**(O(n log n)· 與合併排序不同的演算法,可對大 n 做核算,彌補 O(n²)
  暴力法過慢的問題),(2)在 holdout 與已知值測試中新增**嚴格遞減 witness(n=65537,逆序數
  2147516416 > INT_MAX)**→ 重新實測後 int 收窄變異體被 **CAUGHT**(passed=False)。
- **[LOW annotation] 註解有誤**:曾在 `[inf,1,-inf]` 處註記為 `-> 2`,實際應為 3(全部 3 對均為
  逆序)。gate 是與 oracle 比較(在 3 處一致)故不會放行錯誤實作 = **僅註記本身不準確**。
  **修正**=將註解改為 `-> 3`(已確認 op/oracle/Fenwick 三者均得 3、一致)。
- **★運用改進的實證**:此後的審查均預設採用 worktree 隔離。全部套件全綠 · ruff clean · mypy
  新增 0。

## P17 完成紀錄 — 最大子陣列和(Kadane 演算法)(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**搜尋/最佳化再擴充 1 個 op(P8 binary_search/kth_smallest · P15 lis_length 之後的搜尋第 3
彈)**:`max_subarray`(KIND_REDUCE)= 對整數值 double 數列用 **Kadane 的 O(n) 重置掃描**
(`cur = max(0, cur+x); best = max(best, cur)`)求**連續子陣列的最大和**。**允許空子陣列**
(和為 0),故答案**恆 ≥ 0**(全負時為 0.0)= **-1.0 是安全 sentinel**。在整數域內(各
`|x| ≤ 2^52` 且絕對值的滾動和 ≤ 2^52)使全部部分和都保持在嚴格整數 < 2^53 → 答案嚴格精確 ·
**C==Python 逐位元一致**。獨立 oracle(全部 O(n²) 子陣列的暴力最大值)因**整數加法的結合律**而與
Kadane 嚴格一致。fail-soft -1.0 = NaN / inf / 非整數 / `|x| > 2^52` / 滾動和溢位。
- **honest gate 實測(passed=True · c_verified=true · ziglang cc)**:python==**獨立 O(n²) 暴力法**
  (與 Kadane 不同程式碼路徑)**diff 0.0(exact)** / codegen **C==Python 逐位元一致 diff 0.0**。已
  事先實測=**在 5000 組隨機資料(整數 · 混合正負號 · 小範圍以大量驅動 tie/重置)上與暴力法不一致數
  為 0**。
- **★gate mutation test(自行驗證)**:(1) overflow 守衛 `>`→`>=`(用恰好 2^52 的 witness
  誤判 bail)→**被捕捉**,(2) 刪除重置邏輯 `if cur<0: cur=0`(變為後綴和 = 錯誤)→**被捕捉**,
  (3) 刪除域守衛(inf 時 `int()` 崩潰)→**被捕捉**,(4) **真正的非空 Kadane**(不含空選項)→ 在
  全負 holdout `[-1,-2,-3]`(正確答案 0.0)上**被捕捉**(err=5.0),(5) best 更新 `>`→`>=`
  (等價)→ 如預期未被捕捉。
- **★設計依據的驗證**:真正的非空 Kadane 在全負 `[-1,-2,-3]` 上會回傳最大元素 -1.0 =
  **與 fail-soft sentinel -1.0 衝突**。mutation test 證明了「因允許空而使答案 ≥ 0 → -1.0 是安全的」
  這一設計正是為了避免這種衝突而生效(允許空 = sentinel 健全性的前提)。
- **holdout**:空/單個正數(5)/單個負數(0)·**全負→0(單獨 pin 住允許空這一點)**· 經典 Kadane
  `[-2,1,-3,4,-1,2,1,-5,4]`→6 · 中段回落造成重置 · 0/-0.0 帶正負號零 · **在 2^52 處 pin 住 overflow
  邊界**(`[2^52]`=滾動和 2^52 → **valid**(單獨 pin 住 `>` 與 `>=` 之別)/ `[2^52,1]`=2^52+1 →
  -1.0 / `[2^51,2^51]`=2^52 → valid / 單個 `[2^52+1]` > 2^52 → -1.0)· 在開頭/中間放置非整數/
  ±inf、在開頭/中間/末尾放置 NaN 做 fail-soft · 隨機整數資料。
- **C 安全**:域檢查 `x >= -LIM && x <= LIM` 在**(long long) cast 之前**就拒絕 NaN/inf/超大值
  (NaN→int 是 UB)。累加用 long long,滾動和 ≤ 2^52 使全部部分和 < 2^63(不會溢位),回傳的
  double 在 best < 2^53 時嚴格精確。
- **work-graph op 波**:將 max_subarray 做成 `algo_difftest --op` gate 節點(`1 op = 1 節點`)→
  用 `run-once --available tool:command` 實現無人值守完成(gate JSON passed=True ·
  c_verified=true)。= **全部 algo op 達到 38 個 · 均已 work-graph gate 化**(37→38)。
- **回歸**:在 `tests/test_algo.py` 中新增 P17 測試群組(registered_kind · 已知值 · 暴力法一致
  隨機×5000 · fail-soft/overflow · difftest python exact · C 逐位元一致)。**honest**:首次完整
  執行時 `test_search_ops_registered_kinds` 出現 1 failed(search category 集合的更新只改了**兩處
  中的一處**[`test_categories_grouping`])→ 已發現並立即修正,重新執行後 **test_algo.py 295
  passed / 0 failed** · ruff clean · mypy 新增 0(與 origin/master 的 15 個相同)。**對抗性審查在
  worktree 隔離環境下執行**(P16 建立的做法)。

### P17 對抗性審查後的強化(2026-08-17, [[feedback_no_solo_ai_judgment]])
**worktree 隔離審查(4 個 agent · 3 個視角 + 對抗性驗證)= 1 項 CONFIRMED(LOW ·
gate-honesty)/ refuted 0**。驗證代理在隔離 worktree 中完整重現,並明確記錄本 repo 的 algo.py
未被汙染(`status --porcelain` 只有 auto 的 SESSION_SUMMARY)。correctness/integration 相關為 0
(op 正確):
- **[LOW gate-honesty] C 中「在 cast 之前拒絕 NaN」這一點無法被 gate 證偽**:honest gate 只用
  `-O2 -std=c99 -ffp-contract=off`(無 UBSan)編譯 C。若將 C 的域守衛做 De Morgan 改寫
  `if (!(x>=-LIM && x<=LIM))` → `if (x<-LIM || x>LIM)`(NaN 時兩個比較都為 false = NaN 會漏過),
  緊接著下一行 `x != (double)(long long)x` 的 **`(long long)NaN` 是 UB**,在 -O2 下恰好落到
  相當於 -1.0 的結果、與 Python 逐位元一致 → gate 判為 passed=True。但同一變異體**在
  UBSan/ReleaseSafe 建置下會強制 trap**(`panic: nan is outside the range of representable
  values of type 'long long'`)。**出貨的 op 是正確的**(守衛 `!(x>=-LIM && x<=LIM)` 會在 cast
  之前拒絕 NaN)= 這是 gate-coverage 的缺口(不是正式生產缺陷)。Python 一側已被 pin 住(刪除域守衛會
  使 `int(nan)` 拋出 ValueError,gate 不會放行而報錯)= 唯獨 C 側未對稱地 pin 住。
- **一手驗證(自行重現)**:用與 gate 相同的編譯選項 `-O2 -std=c99 -ffp-contract=off` 做獨立
  probe:出貨 guard = NaN→-1.0 正常 / De Morgan+UBSan = `(long long)NaN` trap(與 finding 中的
  panic 一致)/ 出貨 guard+UBSan = 無 trap(在 cast 之前就拒絕 NaN = **UBSan-clean**)。
  **honest 的差異**:我的獨立 probe 中 De Morgan+-O2 會以 exit3 崩潰,但**實際 gate**
  (`algo_difftest --op`)中確認了如驗證代理所回報的那樣通過 = -O2 下的 UB 行為不確定,無論如何
  「僅靠 -O2 無法確實 pin 住 reject-before-cast」這一點成立。
- **修正(強化全部 op)**:在 `run_c_backend` 中新增 **UBSan pass**——在 -O2 逐位元比較之後,用
  `-fsanitize=undefined -fno-sanitize-recover=all` 對同一份 C 重新編譯並在同一 holdout 上再次執行。
  一旦 NaN/inf/域外值抵達整數 cast 就會 trap → **gate fail**(不支援 UBSan 的 toolchain 回傳
  `"unsupported"` = neutral,不會誤判)。**事先實測**:全部 38 個 op 均為 UBSan-clean(trap 數
  0)= 無誤報、可安全採用。**修正後實測**:出貨 op = passed=True/ubsan=ok,**De Morgan 變異體 =
  passed=False/ubsan=trap**(逐位元比較在 -O2 下為 True,但被 UBSan 捕捉)、其他 op 無回歸。=
  **使「reject-before-cast」在 C 側也變得 load-bearing**(與 Python 的 `int(nan)` raise 對稱)。
  新增回歸 pytest `test_ubsan_pass_catches_nan_slip_through_cast`。全部套件從 **295 增至 296
  passed / 0 failed** · ruff clean · mypy 新增 0。
- **★這不是 max_subarray 專屬問題,而是 gate 基礎建設的強化** = 此後全部 algo op 都能讓 gate
  證偽「非有限值抵達 cast 造成 UB」這類問題。

## 2026-09-03:對抗性審查(algo + C codegen)的 8 項修正

- **[HIGH] C 的 `unsharp`(`sharpen`)缺少 [0,1] 裁剪,導致後段 op 與 Python 產生偏差**
  (unsharp→gaussian 最大差 6.6e-2,unsharp→threshold(1.0) 時 512 個像素反轉)。在 `sharpen` 出口
  加入 clamp + `codegen.py` 在每個需要 clip 的 sort 的各 stage 之後輸出 `clamp01()`(雙重保險)。
  修正後 ≤ 3e-7。
- `difftest.py` 只尋找 gcc/cc/clang,導致**在本環境下 C gate 被靜默 skip**(因此上述偏差一直未被
  發現)。改為共用 `algo_difftest.find_c_compiler()`(帶 ziglang fallback)。結果字典中新增記錄
  `compiler`。
- 圖 op 的 `n` 在 int32 上限內不受限制(`graph_components([2147483000,0])` 會配置 17 GB)→ 改為
  **`n ≤ 5,000,000`**(與 sieve 相同的明確上限),`m ≤ 2147483000`,Python/C 均如此。
- 曾先將端點 `(int)` cast 後才做範圍檢查(float→int 溢位 UB,會被 UBSan trap)→ 改為先用原始
  double 檢查範圍與整數性。UBSan trap 從 3 處降為 0,39/39 位元一致。
- **哨兵值變更(ABI)**:對於「0.0 本身也是合法答案」的 op,將其 fail-soft 哨兵值由 **0.0 改為
  −1.0**——涉及 `is_prime` / `segments_intersect` / `edit_distance` / `point_in_polygon` /
  `lcs_length`(與 P13〜P18 相同的約定)。例如:`is_prime([4294967311])`(超出定義域)現在回傳
  −1.0 而非表示「合數」的 0.0。未變更的(可能存在衝突、待研究):`pow_mod` / `gcd_seq` /
  `popcount_total` / `polygon_area2`。
- `run_algo` 曾對超過 2^53 的整數先用 `float()` 四捨五入再做定義域檢查 → 改為用 `wire_float()`,對
  |x|>2^53 的整數輸入拋出 `ValueError`(fail-closed)。
- `box` 的偶數 k 曾使用 k+1 個 tap 卻除以 k(增益 1.25)→ 改為與 scipy `uniform_filter` 相同的
  origin、使用 k 個 tap。
- `difftest` 中的 NaN 曾因 `max(0.0, nan)=0.0` 而被判為合格 → 改為將非有限值視為 inf 判定為不合格。
- 回歸:新增 `tests/test_imgops_c.py`(新設 11 個)等共 35 個測試,5 個檔案共 355 passed(C 測試
  全部用 ziglang 執行)。
