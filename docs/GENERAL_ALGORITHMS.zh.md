# 让通用算法也能实现 — algo-c 对应路线图

[日本語](./GENERAL_ALGORITHMS.md) · [English](./GENERAL_ALGORITHMS.en.md) · **简体中文** · [繁體中文](./GENERAL_ALGORITHMS.tw.md) · [한국어](./GENERAL_ALGORITHMS.ko.md) · [Deutsch](./GENERAL_ALGORITHMS.de.md)

> 用户需求(2026-08-16):<https://github.com/okumuralab/algo-c>(奥村晴彦
> 《[修订新版] C语言标准算法辞典》全部源码)中出现的**通用算法**,
> 也希望能在 Fullseye 中实现。
>
> **诚实的现状认知**:Fullseye 目前是 **图像算法设计 AI**(op 注册表 = image/region/
> feature/contour/volume 的 sort、进化 + holdout gate + Python→C codegen)。通用算法
> (排序/搜索/图论/数论/加密/压缩)无法归入图像 sort,因此需要**扩展语言、类型与 codegen**。
> 这是跨越多个会话的工作。本文档就是其**确定计划**(供下一次会话在完整上下文中执行的正本)。

## algo-c 的分类(书籍目录 · 实现对象地图)
※ 严格的覆盖范围以 repo 的 `/src` 为正本。

| 领域 | 代表性算法 | Fullseye 中的承接方式 |
|---|---|---|
| 数值计算 | 方程式(二分法/Newton)、数值积分(Simpson/Romberg)、线性方程组(Gauss/LU)、插值(spline)、FFT | 既有 `dsp`(FFT)+ 新增 `numeric` op 族 |
| 随机数 · 统计 | Mersenne Twister、分布、统计量 | 新增 `rng`/`stat` op(确定性 seed) |
| 排序 | quick/heap/merge/shell/radix | 新增 `array` sort + `seq` 类型 |
| 搜索 | 二分搜索、哈希、BST/AVL/B-tree | 新增 `array`/`map` op |
| 字符串 | KMP/BM/Rabin-Karp、编辑距离、正则表达式 | 新增 `text` 类型 + op |
| 图 | DFS/BFS、Dijkstra、Warshall-Floyd、MST、最大流 | 新增 `graph` 类型 + op |
| 几何 | 凸包、线段相交、Voronoi | 既有 `pcseg`/几何 + 新增 `geom2d` |
| 数论 · 加密 | 素数、GCD、RSA、MD5/SHA、AES | 新增 `numtheory`/`crypto`(教学用 · honest 披露) |
| 数据压缩 | Huffman、LZ/LZW、算术编码 | 新增 `compress` op |
| DP/搜索 | 8-queens、背包问题、DP | fscript 的控制流 + `array` |

## 实现架构(确定方针)
将 Fullseye 的既有资产扩展到通用领域。**不会稀释图像 AI 的焦点**(通用 op 归入独立 tier / opt-in)。

1. **类型系统扩展**:在现有 6+1 种 sort(image/region/feature/contour/match/any/volume)基础上,
   新增**`seq`(一维数组)/`text`(字符串)/`graph`/`scalar`**(`ops.py` 的 sort · `fslib` 类型)。
2. **fscript 的通用语言化**:目前已具备 if/for/while、赋值、tuple。将分阶段新增**数组/字符串
   字面量、索引、procedure(函数)**(此前决定收窄语言范围,通用 tier 将以独立 profile 解禁)。
   正本 = 重新审视 `docs/FSCRIPT_DECISION.md` 中的 A/B 分支。
3. **op 注册表扩展**:将 algo-c 中的各个算法以 **op**(name/in-out sort/params/**c_stmt**)形式
   注册。直接沿用既有的 Python→C codegen(`engine.to_python`/`to_c`)+ **difftest**(honest gate:以
   Python 为 oracle,对 C 做差分验证)→ **用实测保证"能用 C 实现"**。
4. **honest gate**:把 algo-c 的 C 代码作为参考实现喂给 `difftest`,与 Fullseye codegen 生成的 C
   验证数值/位一致性(既有 gate 的扩展)。**尊重原始代码的许可协议**(algo-c = 书籍附带代码,
   使用条件待确认),**不直接照抄,而是从规格重新实现**(公开披露方针)。

## 阶段计划(下次会话以后)
- **P1**:将 `seq`/`scalar` 类型 + 3 种排序(quick/heap/merge)op 化 + C codegen + difftest。
  = "Fullseye 也能为通用算法生成 C 代码"的最小实证。
- **P2**:数值计算(二分法/Newton/Simpson/Gauss)op 族。
- **P3**:字符串(KMP/BM/编辑距离)+ `text` 类型。
- **P4**:图(Dijkstra/BFS/MST)+ `graph` 类型。
- **P5**:压缩/数论/加密(教学用 · honest 披露,禁止照抄)。
- 每个 P 阶段:进化 gate 不适用(通用 op 是确定性的、不做 holdout 进化),**用 difftest 对 C 一致性做 honest 实测**,
  在 Studio 的 op 浏览器中展示新 tier。

## honest 的局限与规律
- **不照抄**:参考 algo-c 的 C 代码,但**从规格重新实现**(`feedback_provenance_research_method`)。
  在确认许可协议之前不纳入代码。
- **不稀释图像 AI 的焦点**:通用 op 属于 opt-in tier。北极星目标(HALCON 级图像 op 全覆盖 + honest
  holdout)保持不变。

---

## P1 完成记录(2026-08-16, Opus5[1m]/ultracode)
**达成了最小实证"Fullseye 也能为通用算法生成 C 代码,并能 honest 实测出 C 一致性"。**

- **新 tier(与图像 REGISTRY 完全分离、opt-in)** = `algo.py`。新设 `seq`(一维数列)/`scalar`(单一实数)类型。
  完全不触碰图像 `ops.REGISTRY`,因此进化搜索、Wave-0 champion pin 不受影响(已用测试实证)。
- **op(5 个)**:排序 3 种 `quicksort`(Hoare/median-of-three/Lomuto/显式栈)、`heapsort`(Williams
  1964 二叉最大堆)、`mergesort`(von Neumann 1945 自顶向下稳定排序)= `seq→seq`。此外为 `scalar`
  类型赋予角色的归约(reduction)`seq_max`/`seq_min`(`seq→scalar`、与顺序无关且 exact)。**全部从规格
  重新实现**(algo-c 源码不照抄 · 各 op 均标明 `provenance`)。
- **单一 source of truth**:各 op 将 Python 主体与 C 主体以**字符串**形式保存,进程内引用由
  `algo.py_fn` 编译同一字符串,`algo_codegen` 将同一字符串输出为独立的 `.py`/`.c`。
  → 被测试的 oracle 与出货物不会漂移(用测试 `test_emitted_python_*` 实证)。
- **codegen** = `algo_codegen.py`(`emit_python`/`emit_c`。C 是函数 + 二进制 I/O driver = 可完整
  编译的独立程序)。
- **honest gate** = `algo_difftest.py`(两个实测,均非 deferred skip):
  (1) Python 参照 **== numpy oracle**(`np.sort`/`np.max`/`np.min`),(2) codegen **C == Python
  按位一致**(holdout = 边界情况 10 + 随机 40)。由于这些 op 只是移动/选择既有 double,正确实现应
  按位完全一致(tol=0.0)。
- **★实测(2026-08-16, `zig cc` = `python -m ziglang cc`, 通过 pip 安装 ziglang 0.16.0)**:
  全部 5 个 op 均为 **python diff 0.00e+00 / C-vs-Python diff 0.00e+00 / passed=True**(实际
  编译→实际运行→按位比较)。= 作为**非 deferred skip 的真实测量**达成了"honest 实测 C 一致性"。
- **fail-closed**:无 toolchain 时 → C 部分 honest skip(Python 部分照常运行)。compile/run 失败 →
  gate FAIL(不设为 neutral skip。用测试 `test_difftest_compile_error_fails_closed` 实证)。
- **facade**:`fullseye.algo_ops()/run_algo()/algo_to_c()/algo_to_python()/algo_difftest()`
  (+ `api.py`)。**skill** = 在 `~/.claude/skills/image-processing/SKILL.md` 中补写"General algorithms
  (algo-c tier)"一节(可供子代理使用)。
- **测试**:`tests/test_algo.py`(42 个用例 = 注册表一致性 · Python==sorted/oracle · 稳定性 · 单一 source
  of truth · C 按位一致[有 toolchain 时] · compile-error fail-closed · 不污染图像注册表 · facade)。
- **honest 的局限**:①含 NaN 的数列因比较排序的约定在 Python/C/numpy 间不一致,故从 holdout 中
  排除(已披露)。②**累积会导致顺序依赖的 op 不纳入 P1**(如浮点求和;seq_max/min 是 exact 的)。
  ③CLI 子命令整合(`imgevolve.py algo ...`)与 Studio op 浏览器 tier 显示留待下阶段(P1.5)。
  ④fscript 的数组/procedure 语言化(设计文档架构第 2 项)不在 P1 范围内(另设 track)。

## P1 对抗性评审后的强化(2026-08-16, [[feedback_no_solo_ai_judgment]])
对本会话自行编写的代码实施了独立的对抗性评审(Workflow 4 个视角 = 算法正确性 / codegen · C 安全 /
gate 健全性 / 集成 · 焦点安全,共 22 项 findings)。我对全部结果做了一手代码验证(v11 规律),
修正了真正的缺陷:
- **[HIGH] gate 的 fail-open(NaN/带符号零)**:`_max_diff_*` 因 `max(0.0, nan)=0.0` 而把 NaN 差异
  抹平,虚报"按位一致"(已实测重现)→ 拆分为 **(1)Python×oracle=数值比较,但非有限值 fail-closed
  (inf、不用 tol 放行);(2)C×Python=真正的按位比较(IEEE float64 原始字节 = 带符号零/NaN payload
  也能检测)**。用 `c_verified` 字段区分"实际编译验证通过"与"无 toolchain 未验证通过"。
- **[HIGH] quicksort 对大量重复输入呈 O(n²)**(Lomuto `<=` 使全部相等元素落到一侧;二值化 = binary
  mask flatten 是现实输入、实测呈 quadratic)→ Python/C 均改写为 **3-way(Dutch national flag)
  划分 + median-of-three**(全等值时 O(n))。追加性能防护测试(20000 全等值 <2s)。
- **[HIGH] 生成的 C `heapsort` 与 BSD `<stdlib.h>` 的 `heapsort()` 符号冲突**(macOS/BSD 上无法编译,
  用 `zig cc -target x86_64-macos` 实测)→ C 符号改名为 **`heapsort_asc`**(与 `mergesort_asc` 统一)。
  追加**全部 op 的 macOS 交叉编译测试**(回归防护)。
- **[LOW] C 的 fail-open/UB 3 处**:mergesort 的 malloc 失败 = 输出未排序 → **改为原地插入排序
  fallback(fail-closed · 保持 stable)**;heapsort 的 `2*root+1` int 溢出 → 改为 **long long**;
  driver 的 len 为 32 位导致 size_t 环绕 → **加入 `SIZE_MAX/sizeof(double)` 上限检查 + `<stdint.h>`**。
- **[MED] test_mergesort_is_stable 是空洞测试**(值比较 = 任何排序都能通过)→ 改写为通过**带符号零
  的顺序保留**实际观测稳定性(`<` = 会检测到退化为不稳定)。同时新增 **no-mutation 测试**(`run(a)`
  不会破坏调用方的 list)。
- **[MED] holdout 太小、重复稀疏**→ 追加大规模全相等(300)/ 二值(300)/ few-distinct(300)+ 更多
  重复的随机数据(使 C gate 能实际检验重复度与规模区间)。
- **[MED/honesty] NaN 约定未文档化**→ 在 module docstring 与各 op docstring 中明确"以 NaN-free
  为前提 · 非有限值由 gate fail-closed"。seq_max/min 的"order-independent"改为"在 NaN-free 输入下
  order-independent"。
- **相邻的既有 ship-bug**:`sample_images`(studio 运行时 import)在 `pyproject.toml` 的 py-modules
  中缺失 = 非 editable wheel 会消失 → 补齐(用实际构建 wheel 确认)。
- 测试从 **43 增至 58 个**(新增位检查 · fail-closed · macOS 交叉编译 · 重复度性能 · no-mutation ·
  c_verified · 稳定性观测)。重新运行全部 op 的 difftest = Python 与 C 均 diff 0.0 · 按位一致 ·
  passed=True。
- **未修正(用户判断 · P1 范围外的既有问题)**:(a)`pyproject.toml` 的 `[tool.setuptools.package-data]`
  `"*"` glob 无法把根级平铺的 `studio_assets/`、`data/` 收进 wheel(studio i18n/op-help/示例图像在
  installed wheel 中缺失 = 既有问题、需要 MANIFEST.in 或改变 package 化设计)/ (b)`fullseye.__all__`
  缺少 api 中 pcseg 系列的 18 个名称(星号导入会缺失 = 既有问题)。**algo tier 与此无关**(algo* 通过
  py-modules 确实会一并打包 · facade 是一致的)。

## 接下来(P2 以后)
- **P1.5a(已完成, 2026-08-16)**:新增 `imgevolve.py algo <list|run|emit-c|emit-py|difftest>` 子命令
  (统一 CLI 入口。`algo run quicksort --seq 3,1,2` / `algo emit-c mergesort` / `algo difftest all`)。
  新增 CLI 回归测试 2 个 + 更新 skill 中的 CLI 示例。
- **P1.5b(完成于 2026-08-17)**:在 Studio 的 op 浏览器中以 **只读方式**展示 general(algo)tier(记录见下)。
- **P2(完成于 2026-08-16)**:在 seq/scalar 类型基础上加入数值计算 op。**simpson / bisection / newton**
  (多项式 · 样本内含于输入 seq 的 seq→scalar · 沿用既有 reduce driver)+ **gauss_solve**
  (线性方程组 Gauss 消元 · 部分主元 = 记录见下方 P2 完成记录)。honest gate = **C-vs-Python 为按位
  一致**(同一算法 + `-ffp-contract=off` 抑制 FMA)/ **Python-vs-oracle 为数值容差**(`AlgoOp.tol`)与
  独立 oracle(simpson=scipy / 求根=残差 |p(root)| / gauss=`np.linalg.solve`)核对。将 fail-soft 做 honest 文档化。
- **P3(完成于 2026-08-17)**:字符串 op(记录见下方 P3 完成记录)。`text` 类型采用"以 float64 携带
  代码点序列"的约定(`text_to_seq`/`seq_to_text`),不新增 wire 类型即可搭载既有 float64 harness。
- **P4(完成于 2026-08-17)**:图 op(components/mst_weight/dijkstra,记录见下方 P4 完成记录)。`graph`
  以 `[n, m, (u,v,w)*m]` 打包搭载既有 harness(无需新 wire 类型)。
- **P5(完成于 2026-08-17)**:数论 · 压缩 · 教学用哈希(gcd_seq / sieve_primes / pow_mod / crc32 /
  rle_encode,记录见下方 P5 完成记录)。整数以 float64 携带(exact <2^53),因此不需要新的 wire 类型。全部 op 都是
  **exact 的**(C 按位一致,且 Python==独立 oracle tol 0)。**加密仅提供 primitive**(modular
  exponentiation / CRC)= 完整的 RSA/AES/SHA 因需要 bignum/大状态而无法搭载 float64 seq harness,故明确
  界定为范围外并 honest 披露。

## P3 完成记录 — 字符串 op(2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**为 algo tier 新增 3 种字符串算法。**"字符串 = 以 float64 携带代码点序列"(Unicode 标量 < 2^53 故为
严格精确)使其**无需改造即可搭载既有的 float64 二进制 harness**(无需新 wire 类型)。值仅做相等比较
(整数编码精确)· 位置/距离为严格整数 → **C-vs-Python 按位一致 且 Python-vs-oracle 为 EXACT(tol 0)**。

- **op(3 个)**:`strfind`(Knuth-Morris-Pratt = 失败函数前缀自动机。输入 `[m, pattern(m), text]` →
  全部出现的起始位置的升序列表 · 含重复出现 = **可变长 KIND_MAP**,复用 gauss 中构建的可变长 wire) /
  `edit_distance`(Wagner-Fischer/Levenshtein 双行 DP = **KIND_REDUCE** · 严格整数) / `lcs_length`
  (最长公共子序列长度双行 DP = KIND_REDUCE)。全部从规格重新实现(明确标注 provenance)。fail-soft =
  空 pattern/截断/pattern 长于 text 时为 `[]`,na<0/截断为 `0.0`。
- **单一 source of truth + text 类型辅助函数**:新增 `text_to_seq(s)`/`seq_to_text(seq)`(代码点↔float64)。
- **honest gate 实测(3 个 op 均 passed=True · c_verified=true)**:Python==**独立 oracle**(strfind=
  朴素 all-occurrences 扫描[与 KMP 独立] / edit·lcs=**自顶向下的 memo 递归**[与自底向上的双行 DP 是
  不同代码路径])**diff 0.0(exact)** / codegen **C==Python 按位一致**(ziglang cc)。
- **work-graph op 波(候选 d 的实演)**:每新增一个 op 就叠加一个 `algo_gate` gate 节点 = **1 op = 1
  节点**。将 3 个 op 通过 `raptor-worklog add --capability tool` → `run-once --available
  tool:command` 实现 **无人值守完成**(生成 gate_ok.json)。
- **回归**:在 `tests/test_algo.py` 中为 strfind/edit_distance/lcs_length 新增测试组(已知解 · 随机×
  独立 oracle · fail-soft · 可变长输出 · no-mutation · python exact · C 按位一致)。全部套件 **4669
  passed / 0 failed**(较 P2 后的 4649 增加 +20)· ruff clean · mypy 回归 0。commit + push 已在本会话
  执行(用户于 2026-08-16 就寝时批准 = push gate 开放)。

### P3 字符串 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
独立对抗性评审 Workflow(4 个视角 · 各项 finding 由验证代理以实际代码/实际 compile 确认)= **3 项
findings 全部 CONFIRMED**(其中 2 项是同一根本原因被不同视角分别报告)。经一手验证后全部修正:
- **[MED] Python 在做范围检查前先执行 `int(a[0])` → 与 C 不一致**:edit_distance/lcs_length 的 Python
  先求值 `na = int(a[0])`(截断),而 C 是先用原始 double 做守卫。当 **`a[0]` ∈ (-1.0, 0.0)**(例如
  -0.5)时,Python 会得到 na=0(有效的空字符串)并继续返回实际距离,而 C 用原始值守卫直接拒绝返回
  0.0 → **违反按位一致契约**(用 ziglang cc 实测:`[-0.5,65,66]` = Python 得 2.0 而 C 得 0.0)。holdout
  只有非负整数 na,故 gate 未能检测到。
- **[LOW] NaN 表头会使 Python 崩溃**(C 是 fail-soft):`int(nan)` 会抛出 ValueError,违反 op docstring
  中的 fail-soft 承诺(C 用 NaN-false 守卫返回 0.0/`[]`)。※虽然 NaN 属于"以 NaN-free 为前提"的契约
  之外,但属于同一类守卫顺序缺陷。
- **修正(一处修复两个问题)**:将全部 3 个 op 的 Python 中**原始值守卫移到 `int()` 之前**
  (`not (x >= lo and x <= hi)` = NaN-false)= **精确镜像 C**。gauss 原本就是原始值守卫、写法正确
  (统一为同一形式)。
- **边界覆盖补足**:因超出 oracle 验证域(oracle 的截断会产生不同的值 = 正是这个 bug 本身),故对
  超出 oracle 验证域(oracle 会因截断而给出不同值 = 正是此 bug)之外的小数负值/NaN/超长表头,新增
  **专用测试直接固定 C-vs-Python parity**(`test_string_c_python_parity_on_bad_headers`)+ Python
  fail-soft 不崩溃测试。algorithm-correctness/c-safety 方面的核心指摘为 0(KMP/DP/内存安全均干净)。
- 评审后:3 个 op 的 difftest 均为 python exact / C 按位一致 / c_verified=true,全部套件全绿(见下)·
  ruff/mypy 回归 0。

## P2 完成记录 — gauss_solve(2026-08-16, Opus5[1m]/ultracode, `graph-loop-engineering`)
**新增线性方程组 Gauss 消元(部分主元),完成 P2 数值计算。** 依用户指示以 `graph-loop-engineering`
技能将其节点化到 raptor work-graph,让 tool driver 无人值守执行(双层方针 = breadth 由 work-graph 的
difftest gate 负责,对抗性 findings 的采纳与 push 是会话内的人工检查点)。

- **新 kind `KIND_MAP`(`map_varlen`)= 可变长 seq→seq**:既有 op 只有 sort(输入长度=输出长度)/
  reduce(→单值)两种,而线性方程组的解(输入 `[n, 扩充系数矩阵 n×(n+1) row-major]` → 解向量长度 n)
  输入长度≠输出长度。C 边界 = `int f(const double* a, int n, double* out)` 向 out 写入
  out_len(≤ n)个值并返回 out_len(fail-soft=0)。
- **`algo_codegen` driver 新增可变长输出模式**:KIND_MAP 分支写出 `{int32 out_len,
  out_len*float64}`(与 sort 相同的 wire,但 out_len≠输入长度)。out 缓冲区按输入长度分配(契约
  out_len≤n 保证上界)+ 对 `out_len ∈ [0,len]` 做 **fail-closed clamp**(防止失控 op 让读取方发生
  over-read)。
- **gauss_solve(`algo.py`)**:Python 参照实现(仅用 stdlib、逐 index 精确镜像 C)与 C 参照实现为单一
  source。前向消元(部分主元 = 选取 |元素| 最大的行)+ 回代。奇异(残留主元为 0)/畸形输入以
  **[] / 0** 做 fail-soft(不抛异常)。**Python/C 的浮点运算顺序严格一致**(同一除法 · 先减后乘 ·
  被消元元素精确赋值为 `0.0` · abs 用内联符号反转以避免依赖 `math.h`/`-lm`)故按位一致。int 溢出通过
  `n≤46340` + `long long need` 防止。
- **honest gate 双段(实测)**:(1)Python **== `np.linalg.solve`**(独立 oracle · 良态 holdout 34 例 =
  对角占优 + 行置换 + **必经主元的情形**[exact-zero(0,0)· 微小(0,0)· 3×3 零对角])→ **最大绝对差
  3.55e-15**(tol 1e-9)。(2)codegen **C == Python 按位一致**(`ziglang cc` · `-ffp-contract=off`)→
  **diff 0.0 / c_verified=true**。奇异/畸形输入的 **C fail-soft 与 Python 完全一致**,用专门测试直接
  验证(因超出 oracle 支持范围,故做 C-vs-Python 直接比较而非 holdout)。
- **`tools/algo_gate.py`(可复用的 gated-stage runner)**:work-graph 的 `CommandWorker` 以"生成
  produces"或"exit0"判定完成,而目前 difftest 在 FAIL 时也会写 JSON,导致**fail-open**(失败的 gate
  被判定为 done)。为堵住此漏洞 = **仅在通过时写标记文件 `gate_ok.json`,并以 exit code 判定**。将
  节点的 produces 指向该标记后,失败的 gate 会 **fail-closed**、使节点失败。可直接用于 P3 以后的 op
  波(1 op = 1 节点)。
- **work-graph 节点化**:`raptor-worklog add --capability tool --project imgevolve --priority 0`
  (spec = `tools/algo_gate.py --op gauss_solve --out <OUT>`,produces=`<OUT>/gate_ok.json`)→
  `run-once --available tool:command` 实现 **无人值守执行 → status=done**(exit0 · c_verified=true ·
  生成按位一致标记)。
- **回归**:在 `tests/test_algo.py` 中新增 gauss + algo_gate + C fail-soft + require_c 测试组(算法
  测试 **93 passed**),全部套件 **4649 passed / 0 failed**(较评审前的 4637 增加 +12)。我修改的
  全部文件 **ruff clean** · mypy 回归 0(既有 baseline 仅为 scipy/ziglang stub 缺失及 difftest 签名的
  既有 quirk,与我新增的代码无关)。全部本地 commit,**未 push = human-gate**。

### P2 gauss 对抗性评审后的强化(2026-08-16, [[feedback_no_solo_ai_judgment]])
对自行编写的 gauss 代码实施独立对抗性评审 Workflow(4 个视角 = numeric 正确性 / C 安全 / gate 健全性 /
集成 · 覆盖,各项 finding 均由验证代理**实际执行重现**)。5 项 findings 中 **4 项 CONFIRMED**,经一手
代码验证后全部修正:
- **[HIGH] algo_gate 的 fail-open(未知 op)**:`find_algo` 的 `SystemExit` 发生在 `marker.unlink()`
  **之前**,导致旧一轮通过时留下的 `gate_ok.json` 残留 → CommandWorker 因 produces 存在而**误判为
  done**(在 op 改名/typo 后重新运行时会显现)。→ 把 mkdir + stale-marker unlink **移到注册表检查之前**
  (无论哪个早期 exit 都不会继承上一轮的通过结果)。已追加回归测试。
- **[MED] gate 无法证伪部分主元的正确性**:holdout 只有对角占优的情形(没有 exact-zero 主元)→ 删除
  主元搜索的 mutant 仍与 `np.linalg.solve` 相差 2.2e-14 而**通过**(pytest 能捕捉,但 work-graph 实际
  运行的 algo_gate 走的是 difftest holdout,故捕捉不到)。→ 在 holdout 中新增**必经主元的情形**
  (exact-zero(0,0)=`[[0,1],[1,0]]`· 微小(0,0)=`[[1e-14,1],[1,1]]`· 3×3 零对角)= no-pivot mutant
  会**结构性不一致→inf→FAIL**,从而被证伪(已自行实测确认)。同时修正了有误导性的注释。
- **[MED] C 端 skip 时仍产生 pass 标记**:toolchain 不存在时 C 部分 skip(honest 但**未验证**),
  但仅凭 `res["passed"]` 就写标记文件,graph 只读取标记是否存在 → **对未编译的 C 也发放认证**。→
  新增 `require_c`(默认 True)= 未验证的 pass 不会写 `gate_ok.json`(写入 `gate_unverified.json` 附带
  diagnostic)以 **fail-closed**。`--allow-unverified-c` 可显式 opt-out,`--no-c` 表示刻意的
  Python-only 弱 gate。
- **[REFUTED]"out_len==0 的 wire 未被测试"**:我事先补充的 `test_gauss_c_fail_soft_matches_python`
  实际编译/运行了 C 并已覆盖 → 验证代理通过 mutation 确认其健全性后**予以驳回**。仅采纳了 macOS
  交叉编译防护测试的一处轻微 nit(将 `_ALL` 改为 `_ALL_OPS` 以同时覆盖 numeric/gauss)。
评审后 gauss 的 difftest 仍为 python 3.55e-15 / C 按位一致 / c_verified=true · work-graph 节点(已强化)= done。

## P1.5b 完成记录 — 在 Studio 中以只读方式展示 general tier(2026-08-17, Opus5[1m]/ultracode)
**在 op 浏览器中展示 general(algo)tier。** 为不稀释图像焦点的设计 = general op 属于 seq/scalar 的
另一套计算模型,故 **只读**(不纳入图像流水线)。
- 在 `api.list_ops(include_algo=False)` 上新增 opt-in 参数 + `api.algo_rows()`(backend="general" ·
  category "algo:*" · tier "z_algo" 用于末尾排序 · halcon None · 附带 provenance)。**默认值不变**
  (既有调用方仍只看到图像 op = 保持焦点)。
- studio:`all_ops = list_ops(include_algo=True)` 使 browser 得以显示 / `_op_row` 增加 algo 回退 /
  `op_signature_detail`、`op_tooltip` 新增 general 分支("seq/scalar op · not an image op · run via
  CLI" + provenance)/ `on_op_selected` 在选中 general 时禁用 Insert · Run once · Help · a/b 旋钮 /
  `add_op`、`run_op_once`、调色板对 general 做 flash 拒绝。多重防御 = **`PipelineModel.add_stage`
  在图像 REGISTRY 中查不到则 KeyError fail-closed**。
- **对抗性评审(2 个视角 · 实际执行验证)= 3 项 CONFIRMED(其中 2 项为同一根本原因)全部修正**:
  - **[HIGH/MED] Program(HDevelop 代码)编辑器的"Apply → pipeline"未设防**:`op_names` 是从
    `list_ops(include_algo=True)` 派生的,导致 general 名称流入代码解析器/自动补全/Help 选择器 →
    `apply_program` 直接写 `model.stages=` **绕过了 add_stage 的后备防护** → general op 侵入
    pipeline。→ **将 `op_names` 限定为图像专用**(用 `backend != "general"` 排除;browser 显示用的
    `all_ops` 仍保留 general)+ 在 `apply_program` 中新增 general stage 拒绝防护(多重防御)。
  - **[MED] Help 对话框选择器对 general 显示虚假信息**("Two knobs a,b tune this operator")→ 同一处
    `op_names` 图像限定化也一并从 Help 选择器中排除(根因修复同时解决两处)。
- 回归测试:`_op_row`/signature/tooltip 的 general 分支、在 offscreen 环境下 browser 显示 general 但
  Insert 等被禁用、`win._op_names` 排除 general、代码解析器拒绝 general 行。全部套件全绿 · ruff
  net-new 0(新增测试干净,studio.py 的 flash 与文件既有的 `%`-format 惯用法一致)· mypy 回归 0。
  同时**实演了候选 (d) op 波**:将全部 12 个 algo op 以 1 op = 1 节点纳入 work-graph,用 `run-once`
  实现无人值守完成。

## P4 完成记录 — 图 op(2026-08-17, Opus5[1m]/ultracode, bonus)
**为 algo tier 新增 3 种图算法**(不在候选之内,但顺应用户"全部推进"+ 7-8h 自律的方针作为 bonus)。
将图打包进输入 seq(`[n, m, (u,v,w)*m]`,无向;dijkstra 会在前面加上 src 前缀 `[n, m, src, ...]`),
搭载既有的 float64 harness。
- **op(3 个)**:`graph_components`(union-find · 连通分量数 = KIND_REDUCE 严格整数) /
  `graph_mst_weight`(Kruskal · 最小生成森林总权重 = KIND_REDUCE) / `graph_dijkstra`(单源最短距离 =
  **KIND_MAP** · -1.0 = 不可达)。用确定性的 union 规则 + (weight, index) 排序 + 最小距离 · 最小
  index 的 settle 顺序,实现 **C==Python 按位一致**。
- **★将 KIND_MAP driver 做成两段式(size-probe)**:dijkstra 的输出长度 n **可能超过**输入长度
  3+3m(稀疏图)。旧 driver 按输入长度分配 out,存在 heap OOB 的缺陷 → 改为让 driver 先用
  `f(a,n,NULL)` 询问 out_len 上界,按此分配后再真正写入的两段协议(在 gauss/strfind/dijkstra 中
  加入 `if(!out) return <bound>`)。
- **honest gate**:Python == 独立 oracle **scipy.sparse.csgraph**(connected_components/
  minimum_spanning_tree/dijkstra)。整数权重 holdout 下 **components 严格精确(tol 0)/ mst ·
  dijkstra tol 1e-9(实测为 0)**。C==Python 按位一致(ziglang cc)。MST/Dijkstra 的 holdout 使用简单图
  (避免 csr 的重复边累加),components 允许多重边(只关心连通性)。
- **对抗性评审(3 个视角 · 实际执行验证)= 2 项 CONFIRMED(均为 HIGH · dijkstra 内存安全)全部修正**:
  (#2)out 缓冲区按输入长度分配 → n>3+3m 时发生 OOB 写入 → 用**两段式 driver** 解决(在被发现前已
  先行修复)。(#1)src 守卫使用原始 `sd < nd` → 小数 nd 会使 src==n 通过、导致 out[n] OOB → 改为用
  整数 n 约束(`sd < n`)。1 项 REFUTED(不可达节点未被测试 ← 已由 known-answer/sparse 测试覆盖)。
  numeric/oracle 各视角均无其他指摘。
- **op 波**:3 个图 op 也纳入 work-graph gate 化(全部 algo op = 15 个,均以 1 op = 1 节点实现无人值守
  完成)。全部套件全绿 · ruff clean · mypy 回归 0。push 已在本会话完成(用户批准)。

## P5 完成记录 — 数论 · 压缩 · 教学用哈希(2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**为 algo tier 新增 5 种通用算法,完成 algo-c 路线图(P1→P5)。** 整数以 float64 携带(exact < 2^53),
因此不需要新的 wire 类型。位/整数运算在 C 端 cast 为 `unsigned long long`/`unsigned int` 后进行,再
转回 double(结果 < 2^53 故 exact)。**全部 5 个 op 均为 exact**(C 按位一致,且 Python==独立 oracle
tol 0)。
- **op(5 个)**:
  - `gcd_seq`(KIND_REDUCE):非负整数列的 GCD(Euclid · 对数列 fold)。oracle=`math.gcd`。
  - `sieve_primes`(**KIND_MAP**):埃拉托斯特尼筛法。输入 `[n]`(长度 1)→ n 以下素数的升序列表 =
    **输出远超输入长度**的代表案例。size-probe 上界 `π(n) ≤ n/2 + 1`(2 与奇数的数目,无需
    log = 不依赖 `math.h`)。oracle=试除法(独立路径)。
  - `pow_mod`(KIND_REDUCE):模幂 base^exp mod m(square-and-multiply = RSA/DH 的 primitive · 教学用)。
    oracle=内置 `pow`。
  - `crc32`(KIND_REDUCE):CRC-32(IEEE 802.3 · reflected · poly 0xEDB88320)。**c_func 为
    `crc32_ieee`**(防御性地避开与 zlib/BSD 的 `crc32` 符号冲突,同 heapsort_asc)。oracle=
    `zlib.crc32`(zlib C 库 = 完全独立)。
  - `rle_encode`(**KIND_MAP**):行程编码 →`[value, count, ...]`(**输出最大为输入的 2 倍**,全不同
    时为 2n)。可逆 · oracle=`itertools.groupby`。
- **★honest 域的披露(pow_mod)**:为防止 uint64 的中间积溢出,**mod ≤ 2^32−1**(积 < mod² < 2^64),
  base/exp ≤ 2^53。结果 < mod < 2^53 于 float64 为 exact。域外 fail-soft 为 0.0(原始值守卫在
  int() 之前 · NaN 安全)。
- **★加密仅提供 primitive(honest scope)**:完整的 RSA/AES/SHA 因需要 bignum · 大状态而无法搭载
  float64 seq harness,故明确标注为范围外。能搭载的 primitive(modular exponentiation / CRC
  checksum)以**算法披露**的形式提供(并非 cipher)。
- **★整数性守卫(新增 · honest 改进)**:gcd_seq/pow_mod/crc32 属于**数据值**,故非整数视为畸形 →
  fail-soft。将 `x == float(int(x))` / `x == (double)(long long)x` 放在**范围检查之后**做
  short-circuit(NaN/超范围值不会到达 cast,避免 `int(nan)` 崩溃 · C 的 `(long long)nan` UB)。表头类
  (sieve 的 n)沿用与既有 gauss/dijkstra 相同的截断约定。
- **★在新的 2 个 op 中运用 KIND_MAP 两段式 size-probe**:sieve(输出远大于输入)· rle(输出≤输入的
  2 倍)均用 `if(!out) return <上界>` 让 driver 先问上界→分配→再真正写入。用专门测试以实际
  compile/run 固定"即使 C 输出超过输入长度也不会 heap OOB"。
- **honest gate 实测(5 个 op 均 passed=True · c_verified=true · ziglang cc)**:Python==独立 oracle
  **diff 0.0(exact)** / codegen **C==Python 按位一致 diff 0.0**。crc32 已在全部字节值 ·
  "Hello" · 全 256 字节上与 `zlib.crc32` 核对一致。
- **work-graph op 波**:将 5 个 P5 op 做成 `algo_gate` gate 节点(`1 op = 1 节点` · priority 0 ·
  tool capability)→ `run-once --available tool:command` 实现 **5 个节点无人值守完成**(各自生成
  `gate_ok.json` = c_verified/按位一致标记)。= **全部 algo op 达到 20 个、均已 work-graph gate 化**
  (15→20)。
- **回归**:在 `tests/test_algo.py` 中新增 P5 测试组(已知解 · 与独立 oracle 大量随机核对 · fail-soft ·
  整数性 · 两段式 probe 的输出超量 · bad-input 的 C-vs-Python parity · no-mutation · python exact ·
  C 按位一致)。全部套件从 **4700 增至 4736 passed / 0 failed**(+36)· 我新增文件 ruff clean · mypy
  新增错误 0(仅有既有 baseline)。

### P5 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
对自行编写的 P5 代码实施独立对抗性评审 Workflow(4 个视角 = algorithm-correctness / C-safety-codegen /
gate-honesty / integration-focus,各项 finding 均由验证代理**以实际 compile/执行重现**,18 个
agent)。**14 项原始 → 9 项 CONFIRMED / 5 项 REFUTED**。全部 CONFIRMED 均由我一手重现(亲自用
ziglang 编译 · 运行)后修正。**尤为值得一提的是对"gate 是否能证伪自身守卫"这一点的深入追问**:
- **[MED] pow_mod 的 honest 域(base/exp ≤ 2^53)未被 holdout 实测覆盖** → 将 exp 截断为 uint32 的
  C 变异体能通过 gate(base/exp 最大值仅取到 1e6/1e5,高位约 33 位未被覆盖)。**修正**=在 holdout
  中新增 2^53 边界情形([2,2^53,7]·[2^53,2^53,2^32-1] 等)+ 将随机数扩大到 [0,2^53] 全域。**重现
  确认**:修正后 exp→uint32 变异体的 `passed=False`。
- **[LOW] gcd(2^53 守卫)/sieve(5,000,000 上限)存在同类未被覆盖的边界** → 将 gcd 边界补入 holdout
  (确认变异体被证伪),sieve 在上限处 Python 参照较慢(约 7.7s)故用**专用 C-only 测试**验证 n=5,000,000
  被接受(π=348513 · 用独立 numpy sieve 核算)· n=5,000,001 被拒绝。
- **[MED] -ffast-math / -ffinite-math-only 会消除 NaN 守卫** → 用 fast-math 编译出货的 C artifact 会
  使 `x >= 0.0` 的 NaN 拒绝被省略、执行 `(long long)NaN` UB(**自行重现**:`gcd_seq([NaN,6])` 在
  `-ffinite-math-only` 下得 2.0,而 gate 默认的 `-ffp-contract=off` 下得 0.0)。**修正**=在
  `algo_codegen.emit_c` 中注入 `#if __FAST_MATH__ || __FINITE_MATH_ONLY__ → #error`(使 artifact
  不会 silent miscompile,而是**拒绝构建** = fail-closed)+ 将 C 注释中"UB 不可达"的说法诚实地更正为
  以 IEEE 为前提 + 新增拒绝 fast-math 构建的测试。
- **[MED] C 端的短小输入守卫(pow_mod 的 `n<3` / sieve 的 `n_in<1`)无法被证伪** → 全部 holdout 均为
  固定长度,删除守卫导致 OOB heap read 也全部通过测试。**修正**=在 holdout / parity 测试中加入
  空 · 短小数组以行使边界路径。**honest 披露**:黑盒值比较**在原理上**无法确定性地捕捉安全守卫被
  删除(因 OOB 读取值本身不确定)。本应由 ASan 正面解决,但**ziglang 的 ASan 在本 Windows 环境下
  无法链接**(`__asan_shadow_memory_dynamic_address` 未定义)。Python 侧守卫可确定性证伪 · C 侧可
  通过边界行使 + sanitizer 捕捉(受环境限制、自动化暂缓)。
- **[MED] pow_mod 的 `1 % mod` 特殊分支无法被证伪**(exp==0 且 mod==1 同时成立的情形不存在于任何
  用例)→ 在 holdout 中新增 [7,0,1]·[0,0,1] + 已知解断言(**重现确认**:`1%mod→1` 变异体的
  `passed=False`)。
- **[MED] P5 的 oracle 在域外输入时崩溃**(zlib.crc32 / pow() / int(nan) 会抛异常)→ 一旦在 holdout
  中加入域外情形,difftest 就会抛异常 = gate 在结构上**无法覆盖**守卫规约(只有 1 个 unit test 能
  捕捉)。**修正**=将各 P5 oracle **域感知化**(用 `_int_in` 精确镜像 op 的声明域 → 域外时返回 op 的
  fail-soft 值 0.0/[]、避免崩溃)。这样 gate 本身就能证伪守卫发散(**重现确认**:删除 crc 整数性 ·
  缩小 gcd 守卫的各变异体 `passed=False`)。
- **[LOW] Studio 的 Operator-help 卡片对 general op 显示"Two knobs a,b"的虚假信息**(P1.5b 已堵住
  picker,但 browser 选择时的 `op_help_html` 回退未设防、波及全部 20 个 algo op)→ 在 `op_help_html`
  中新增 general 分支(展示 provenance + packed-input 契约 + CLI 执行方式)+ 在 `_op_row`/
  `api.algo_rows` 中新增 `desc`(op.doc)+ 回归测试。
- **[LOW] image-processing skill 的 YAML frontmatter description(自动触发面)只宣传了 P1**(body 已
  更新到 20 个 op)→ 将 description 中的 algo 一节扩展到 P2–P5 全部范围 + 触发词(primes/modular
  exponentiation/CRC-32/RLE/shortest path)。
- **5 项 REFUTED**(经验证驳回):均为现行代码正确,finding 误认了实际行为(验证代理通过实际执行
  反证)。
- 评审后:5 个 P5 op 的 difftest 均为 python exact / C 按位一致 / c_verified=true,全部套件
  **4742 passed / 0 failed**(评审修正新增测试 +6)· 我新增文件 ruff clean · mypy 新增 0。work-graph
  的 5 个节点也在修复后重新 gate 化(done)。

## P6 完成记录 — 计算几何(2026-08-17, Opus5[1m]/ultracode, 12h 自律 · `graph-loop-engineering`)
**为 algo tier 新增 3 种几何算法**(algo-c 路线图 P1→P5 完成后的扩展 = P6。对应最初 TOC 中的
"几何 = 凸包/线段相交")。**也是通向图像 tier 中轮廓/区域处理的桥梁**。将 2-D 点打包进输入
seq,用**整数坐标**(各 [-100000, 100000])使全部方向判定/鞋带和都成为**严格整数**运算(完全不使用
浮点除法)= C 按位一致,且 Python==独立 oracle tol 0。
- **op(3 个)**:
  - `polygon_area2`(KIND_REDUCE):用鞋带公式求多边形的 **2 倍带符号面积**(符号 = 绕行方向)。
    oracle=numpy 向量化鞋带公式(`dot`+`roll` = 不同代码路径)。**honest 域**:坐标 ≤1e5 · n ≤1e5
    时和最大为 2e15 < 2^53(用箱形绕行螺旋实测为 exact)。
  - `point_in_polygon`(KIND_REDUCE):用交点数(射线投射法)判定内外。用整数叉积判定交点(不含
    除法)。oracle=**卷绕数算法**(与交点数不同的方法,两者在简单多边形的严格内外判定上一致)。
    对凹多边形也正确(已验证 notch=outside)。**边界(边上)的点视为实现相关**,故已从 holdout 中
    排除(因交点数与卷绕数在边界处可能分歧,已披露)。
  - `convex_hull`(**KIND_MAP**):用 Andrew 的 monotone chain 求凸包。输出为**从字典序最小顶点开始的
    CCW 顺序**顶点列表(共线点被排除 = strict hull · 与 scipy 一致)。oracle=`scipy.spatial.ConvexHull`
    的**顶点集合**比较(顺序另由 C-vs-Python 按位一致来保证)。退化情形(distinct 点数不足 3 / 全部
    共线)两者均返回 [] 做 fail-soft。已提前用**2000 组随机点集**实测与 scipy 的不一致数为 0。
- **KIND_MAP**:convex_hull 的输出 ≤ 输入长度(顶点数 ≤ n),但仍沿用两段式 size-probe(上界 2n)。
- **honest gate 实测(3 个 op 均 passed=True · c_verified=true · ziglang cc)**:Python==独立 oracle
  diff 0.0 / C==Python 按位一致 diff 0.0。
- **work-graph op 波**:3 个几何 op 也做成 `algo_gate` 节点(`1 op = 1 节点`)→ 用 `run-once` 实现
  无人值守完成(全部 algo op 达到 23 个 · 均已 gate 化)。
- **回归**:在 `tests/test_algo.py` 中新增几何测试组(已知解 · 与 scipy/numpy/matplotlib/卷绕数等
  多个独立 oracle 核对 · 凸性/CCW/点内包的结构验证 · fail-soft · 退化情形 · no-mutation · python
  exact · C 按位一致)。全部套件从 **4742 增至 4765 passed / 0 failed**(+23)· ruff clean · mypy
  新增 0。

### P6 对抗性评审(2026-08-17, [[feedback_no_solo_ai_judgment]])
并行实施了 2 场独立对抗性评审 Workflow(各项 finding 均由验证代理以实际 compile/执行/压力测试重现):
- **P6a(polygon_area2 / point_in_polygon,4 个视角 · 102 次工具调用)= findings 0**。geometry-
  correctness / C-safety / gate-honesty / integration-focus 全部为零(整数严格 · 边界已披露 · 2^53
  域已事先实测)。我也已用最坏情形(箱形绕行螺旋 n=1e5)实测 2×面积=2.0e15 < 2^53,确认 op==numpy==C
  一致。
- **P6b(convex_hull,3 个视角 · 85 次工具调用)= 1 项原始 → 0 项 CONFIRMED**(1 项 REFUTED)。唯一的
  指摘"删除 dedup 的变异体能通过 difftest"经验证被**驳回为非缺陷**:去重本来就已由 strict `<=0` 的
  monotone-chain pop 以及 `hv<3` 的后置检查保证,是**防御性冗余**(两个 backend 即使都删除去重效果也
  等价,在 200,000 个重复多点集合上分歧数为 0)。验证代理独立确认了**2n 的 size-probe 是紧凑不
  超量的上界**(抛物线输入下 out_len=2n)/ **ASan+UBSan 在 1104 个敌对用例上干净**(out[] 写入无
  OOB · long long 叉积无 overflow)/ C==Python 按位一致 · Python==scipy 顶点集合完全一致 /
  CCW-from-lex-min 顺序也已用测试保证 / qsort 的不稳定性因(x,y)全序比较子 + 相邻去重而无影响
  (=`sorted(set())`)。→ 仅补充说明 dedup 属于防御性冗余的注释(行为不变)。
- **结论**:P6 的 3 个几何 op 未发现出货缺陷。commit + push 已在本会话完成(`24bc8ad`)。

## P7 完成记录 — 线段相交(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**几何工具集扩展 1 个 op**:`segments_intersect`(KIND_REDUCE)= 判定 2 条闭线段
`[x1,y1,x2,y2,x3,y3,x4,y4]` 是否相交(1.0/0.0)。**是通向图像的直线/轮廓分析的桥梁**。采用 CLRS
33.1 的整数方向判定法(proper crossing = 端点严格跨越对方线段 + 4 个共线 on-segment 特殊情形)。整数
坐标 [-100000,100000] 下叉积严格精确(|cross| ≤ 8e10 可放入 long long)= C 按位一致。**oracle =
`sympy.geometry` 的 Segment 相交判定**(符号计算 = 与方向判定完全不同的方法)。实测:8 个固定情形
全部正确 + **与 sympy 在 2970 组随机整数线段对上不一致数为 0**(含共线重叠/T 字形/共享端点/near-miss)。
退化(点)线段因 sympy 无法构造 Segment,已从 holdout 中排除(op 本身用通用方向判定逻辑可处理,但
未纳入 gate = 已披露)。difftest passed(python exact / C 按位一致 / c_verified),work-graph 节点
无人值守完成(全部 algo op 达到 24 个 · 已 gate 化)。

### P7 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 个视角的对抗性评审(验证代理以实际 compile/执行重现)= **1 项原始 → 1 项 CONFIRMED**(MED ·
gate-honesty)。**op 本身正确**(与 sympy 完全一致),但**difftest holdout 从未以单独理由驱动过
d1/d3/d4 的 on-segment 特殊情形(端点落在对方线段内部 = 无共享端点)**,导致删除该分支的错误 op
能通过 gate(50 个 holdout 的判定结果一个也没变化)。已自行重现确定(丢弃 d3+d4 的变异体
passed=True · `[0,0,10,0,3,0,3,5]`→错误得到 0.0)。**修正**=为各 on_seg 分支(d1/d2/d3/d4)新增以
单独理由驱动的固定 holdout 情形(端点在对方线段内部 · 轴平行 4 个 + 对角 2 个)→ 已自行确认**任意
丢弃 d1/d2/d3/d4 中的一个分支都会使 difftest FAIL**(均为 passed=False)。已知解测试中也新增了
4 个端点-内部情形。全部套件从 **4765 增至 4772 passed / 0 failed**(+7)· ruff clean · mypy 新增 0。

## P8 完成记录 — 搜索/选择(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**为 algo tier 新增 2 种搜索/选择算法**(从几何转向另一个领域以均衡 tier)。基于比较,可处理任意
(NaN-free)double,结果为 index 或既有元素,故 exact(tol 0)· C 按位一致。
- **op(2 个)**:`binary_search`(KIND_REDUCE):在已排序列 `[target, v0..v_{n-1}]` 中求 target 的
  **最左 index**(lower bound),不存在则为 -1.0。oracle=`bisect_left` + 存在性确认(独立)。/
  `kth_smallest`(KIND_REDUCE):`[k, v0..]` 中第 k 小的值(0 索引 order statistic),用
  **quickselect**(median-of-three pivot · Lomuto)。**第 k 个值与顺序无关**,故即使 pivot 顺序不同
  也 C==Python 按位一致。oracle=`sorted()[k]`(Timsort = 不同算法)。median-of-three 使已排序输入也
  是 O(n)(n=40001 时 <2s)。
- **honest gate 实测**:两个 op 均为 passed=True · python exact / C 按位一致 / c_verified。已事先
  用**各 5000 组随机情形与 oracle 核对不一致数为 0**。fail-soft = binary_search 在空/不存在时为
  -1.0,kth_smallest 在 k 超域/非整数/空时为 0.0。
- **work-graph**:2 个 op 也用 `algo_gate` 节点无人值守完成(全部 algo op 达到 26 个 · 已 gate
  化)。回归 = 在 `tests/test_algo.py` 中新增 P8 测试组(已知解 · 与 bisect/sorted 核对 · O(n²)
  防护 · fail-soft · no-mutation · python exact · C 按位一致)。ruff clean · mypy 新增 0。

### P8 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 个视角的对抗性评审(实际 compile/执行验证)= **1 项原始 → 1 项 CONFIRMED**(LOW · correctness)。
**正确性不变,但存在性能缺陷**:kth_smallest 的 quickselect 因单一 pivot(Lomuto)而在
**all-equal/低基数大输入下呈 O(n²)**(median-of-three 无法保护重复值 · n=40000 全相等时耗时
7.44s,sorted/reverse 则很快)。测试的 holdout 仅 n≤30、计时测试只有 sorted 情形,未能捕捉。
姐妹 op quicksort 已在使用 3-way(Dutch flag)划分。**修正**=将 kth_smallest 改写为
**3-way(Dutch national flag)划分**(用 equal-band 把重复值折叠 → 使 all-equal 变为 O(n) · 仅用
比较且与顺序无关 → **维持 C==Python==sorted()[k] 的 parity**)。已自行重现确认:**all-equal
n=40000 从 7.44s 降至 0.0019s**(实现 O(n) 化)· correctness 的 5000 组情形不一致数为 0 · difftest
按位一致。计时测试已扩展到 sorted/reverse/**all_equal/few_distinct**(实际防护退化)。

## P9 完成记录 — 统计/聚合(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**为 algo tier 新增 2 种统计 op**:`count_distinct`(去重值数量 = 整数 count)/ `mode_value`
(众数 · 值较小者优先 tie)。均基于比较(任意 NaN-free double),结果为 count 或既有元素,故 exact
(tol 0)。两个 op 均先复制并排序,再做单遍扫描(结果与顺序无关,故即使 C 的 qsort 与 Python 的
sorted 顺序不同也按位一致)。oracle=`len(set())` / `collections.Counter`(独立机制)。
**★主动强化**:当 mode_value 的众数为零且 ±0.0 混杂时,C 的不稳定 qsort 与 Python 的稳定 sort 可能
返回符号不同的值而导致按位不一致 → 用 **`+ 0.0` 把 −0.0→+0.0 归一化**(其他值不变)使 C==Python
更加健壮(与 rle_encode 的带符号零披露同属一类)。实测:各 5000 组随机情形与 oracle 的不一致数为
0 · difftest passed(python exact / C 按位一致 / c_verified)。全部 algo op 达到 28 个 · 已 gate 化。
ruff clean · mypy 新增 0。

### P9 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 个视角的对抗性评审(实际 compile/执行/变异验证)= **1 项原始 → 1 项 CONFIRMED**(MED ·
gate-safety)。**正确性不变,但存在 gate 覆盖缺口**:holdout 无法证伪删除 mode_value 的 `+0.0`
归一化这一变异体(唯一的带符号零情形 `[0.0,-0.0,0.0]` 在两个 backend 中都被排序为 +0.0 在末尾,
删除归一化也仍然按位一致)。注释声称能担保的按位检查从未真正驱动过该归一化。**修正**=在 holdout
中新增 `-0.0` 不落在 run 末尾的情形 `[0.0,-0.0]`·`[-0.0,0.0]`(两种顺序,无论 qsort 的 tie 顺序如何
必有一方会发散)。已自行重现确认:**删除归一化的变异体使 difftest FAIL**,现行(已归一化)代码在
新增情形下按位一致 pass。全部套件从 **4787 增至 4796 passed / 0 failed**。

## P10 完成记录 — 数论(第2部分)(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**新增 2 种数论 op**(建立在 P5 的整数机制之上 · 共享 category numtheory)。整数以 float64 携带
(exact <2^53)· 在 honest 域内全部模乘积都能放入 uint64/long long = C 按位一致,且 Python==独立
oracle tol 0。
- **op(2 个)**:`is_prime`(KIND_REDUCE):**确定性 Miller-Rabin**(witness {2..37})。honest 域为
  0≤n≤2^32−1(a·a mod n 能放入 uint64 · witness 集合确定性成立至 n<3.3e24 为止,可证明素性)。
  oracle=`sympy.isprime`。★能正确判定 Carmichael 数(561/1105/1729/2465…)为合数。/
  `modular_inverse`(KIND_REDUCE):用**扩展欧几里得算法**求 a^−1 mod m(gcd≠1 则 −1.0)。域为
  a≤2^53 · m≤2^53(Bezout 系数的不变量 |q·s|=|old_s−new_s|≤2m 能放入 long long)· m=1→0。将 C 的
  截断取模正规化到 [0,m−1](+m)使其与 Python 的向下取整取模一致。oracle=内置 `pow(a,−1,m)`。
- **honest gate 实测**:两个 op 均为 passed=True · python exact / C 按位一致 / c_verified。已事先
  用 **is_prime 与 sympy 在 8000 组随机 + 2000 组穷举(含 561 等 Carmichael 数)上核对不一致数为
  0 / modular_inverse 与 pow 在 8000 组上核对不一致数为 0** 实测。全部 algo op 达到 30 个 ·
  已 gate 化。ruff clean · mypy 新增 0。

### P10 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 个视角的对抗性评审(实际 compile/执行/变异验证)= **1 项原始 → 1 项 CONFIRMED**(MED ·
c-safety-gate)。**op 本身正确且 overflow-safe**(已用 353 个敌对情形验证),但
**modular_inverse 的 holdout 未驱动到声明域 2^53**(in-domain 的 m 最大只到约 1e9),使 C 的
`long long→int` 窄化变异体(破坏 2^53 域)能以按位一致通过 gate。姐妹 op pow_mod(base=exp 已固定在
2^53)/ gcd_seq(已固定 2^53 守卫边界)/ is_prime(近 2^32)都能捕捉同类变异体,唯独 modular_inverse
未覆盖。**修正**=在 holdout 中新增 2^53 边界情形(`[2, 2^53−1]` coprime → inverse · 接近 2^53 的大
coprime 值 · `[2^52, 2^53]` 均为偶数 → −1,使 Bezout 运算驱动 |q·s|~2m~2^54)。已自行重现确认:
**`long long→int` 变异体使 difftest FAIL**,baseline 按位一致 pass。oracle(pow)已经能对应,故仅
新增 holdout。全部套件全绿。

## P11 完成记录 — 位运算(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**新增 2 种位运算 op**:`xor_reduce`(全部元素的按位 XOR)/ `popcount_total`(全部元素的 1 位总数 =
Kernighan 算法)。用 float64 携带非负整数,域 [0, 2^53−1] 内全部值可放入 53 位(XOR 结果也
< 2^53=exact · popcount 是较小整数)= C 按位一致,且 Python==独立 oracle
(`functools.reduce(operator.xor)` / 内置 `int.bit_count()` = 与 Kernighan 不同的机制)tol 0。
两个 op 均为 passed=True · python exact / C 按位一致 / c_verified。已事先用各 3000 组随机情形与
oracle 核对不一致数为 0。fail-soft = 负数/非整数/≥2^53 时为 0.0。全部 algo op 达到 32 个 ·
已 gate 化。ruff clean(以 FURB161 将 `bin().count('1')`→`.bit_count()` 化)· mypy 新增 0。

### P11 对抗性评审结果(2026-08-17, [[feedback_no_solo_ai_judgment]])
2 个视角的对抗性评审 Workflow(correctness + gate-safety,`wf_7d130631-c0f`)= **findings 0
(无缺陷)**。评审者 1 得到 `{findings:[]}`,评审者 2 在做"gate mutation testing(破坏实现看 gate 能
否抓到)"过程中因 window 压缩而中断(未产出结果)。**依规律不去复活死掉的 background,而是由我
用同样的 mutation test 亲自一手完成验证**:对 xor_reduce/popcount_total 的代表性 7 种变异体(空
初始化 acc=1 / 误用 OR / 2^53 域边界 off-by-one / 删除负数守卫 / Kernighan→shift[popcount≠bitlength]
/ +2 误差 / admit 2^53)在 holdout 上执行 → **全部 7 种变异体均被独立 oracle 捕捉**(oracle_err >
0)。**结论 = P11 的 gate 可证伪 · 未发现确定缺陷**(`fed093a` 正当、无需 follow-up commit)。

## P12 完成记录 — 扩展欧几里得算法(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**新增 1 种数论 op**(建立在 P5 的整数机制 + P10 的 Bezout 不变量之上 · 共享 category
numtheory=P5+P10+P12)。`extended_gcd`(**KIND_MAP**):输入 `[a, b]`(非负整数 ≤ 2^53)→ 输出
`[g, x, y]`(**严格 3 值**,满足 `a·x + b·y = g = gcd(a,b)`),域外为 `[]` fail-soft。用迭代版
two-variable sweep 计算系数。**系数为严格精确**(不变量 `|q·s| = |old_s − new_s| ≤ 2·max(a,b) ≤
2^54` 能放入 C 的 long long)故 C==Python 按位一致。域为 **[0, 2^53] 含端点**(2^53 为 exact ·
系数 |x|,|y| ≲ 2^52 在 float64 也是 exact)。
- **★oracle 独立性要点(P10 的教训)**:Bezout (x,y) 不唯一,故"`a·x+b·y==g`"这一**恒等式验证**无法
  让 gate 证伪符号/正规形式的差异。→ oracle 改为用**独立的递归版扩展欧几里得 `_ext_gcd_rec`
  (不同代码路径)计算 (g,x,y) 并逐元素比较**。迭代版与递归版返回相同的 canonical 系数(展开递归
  即得迭代版 = 数学上一致,已确认 `[0,b]`/`[a,0]`/`[0,0]`/相等值等全部端点也一致)。
- **honest gate 实测(passed=True · c_verified=true · ziglang cc · 70 个用例)**:python==独立递归
  oracle **diff 0.0(exact)** / codegen **C==Python 按位一致 diff 0.0**。已事先实测=**在 200,000
  组随机数据(含 2^53 域端)上迭代版 op == 递归 oracle 不一致数为 0,且 `a·x+b·y==g==math.gcd(a,b)`
  的恒等式(用 bignum 独立核算)失败数为 0**。fail-soft = 短小/非整数/负数/NaN/>2^53 → `[]`。
- **★gate mutation test(自行验证)**:交换 x,y / 取反 x / 删除 old_s 更新 / 放宽守卫(允许 >2^53)/
  错误长度这 5 种终止性变异体**全部被捕捉**(元素不一致或结构不一致 inf)。误商 q+1 会使 op 本身
  陷入无限循环(由 difftest harness 的 timeout 检测到失败)= 全部会终止的错误实现都能被证伪。
- **holdout(以单独理由驱动域端与全部分支)**:已知 `[35,15]→(5,1,-2)` 等 + coprime/非 coprime +
  相等值 `[7,7]` + 一方为 0(`[0,5]`/`[5,0]`/`[0,0]`)+ a=1 + **2^53 域端**(`[2, 2^53−1]` coprime ·
  接近 2^53 的大 coprime 值 · `[2^52, 2^53]` gcd 为 2^52 · `[2^53, 6]` 含端点上限)+ 域外 fail-soft
  (短小/`>2^53`=`[2^53+2,3]`/非整数/负数/NaN)+ 随机 48 组。
- **work-graph op 波**:将 extended_gcd 做成 `algo_difftest --op` gate 节点(`1 op = 1 节点` ·
  priority 0 · tool capability · produces=gate JSON)→ `run-once --available tool:command` 实现
  **无人值守完成**(passed:true · c_verified · 生成按位一致标记)。= **全部 algo op 达到 33 个、
  均已 work-graph gate 化**(32→33)。
- **回归**:在 `tests/test_algo.py` 中新增 P12 测试组(已知值 · Bezout 恒等式随机×5000 · 与独立
  递归 oracle 一致随机×5000 · fail-soft · category grouping[numtheory=P5+P10+P12] · difftest
  python exact · C 按位一致)。全部套件 **4827 passed / 0 failed**(test_algo.py 单体 260 个)· 我
  的全部改动 ruff clean · mypy 新增 0(与 origin/master 的 15 个相同 = net-new 0)。

### P12 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 个视角的对抗性评审 Workflow(correctness / c-safety+gate-honesty / integration,各项 finding 均由
验证代理**以实际 compile/执行的 mutation 重现**,5 个 agent · 125 次工具调用)= **2 项原始(同一
根本原因)→ 1 项 CONFIRMED**(MED · gate-cannot-falsify)。**op 本身正确**(已在 20 万组 + 全部端点
上验证 · 与递归 oracle 不发散 · 域内无 long long overflow),但**difftest holdout 的域外情形全部
集中在 operand `a` 一侧**(`[2^53+2,3]`/`[2.5,7]`/`[-1,7]`),唯一的 bad-`b` 情形 `[7,NaN]` 因
NaN 在 `bd>=0.0` 处即短路,一次也没能单独驱动 b 的 3 个守卫分支 → **b 侧守卫的单侧退化(a/b 是
复制对称代码,因而看似合理)能同时穿过两个 gate 的一半**(与 P5/P7/P9/P10 相同的 gate-coverage
教训)。**自行重现确定**:从 _PY/_C 两侧同时删除 `bd>=0`/`bd<=2^53`/`bd==int` → **全部
`passed=True`(未被捕捉)**,而对称的 a 侧删除全部 `passed=False`(已被捕捉 · 因 a 的域端在
holdout 中)。**修正**=在 holdout 与 fail-soft 测试中新增 `[valid_a, finite_bad_b]` 情形
(`[3, 2^53+2]`·`[7,-1]`·`[7,2.5]`)→ 重新实测后 **b 侧 3 处删除全部被捕捉(passed=False,
pydiff=inf)**、baseline 在 70 个用例上按位一致 pass。★**采纳验证代理的 honest 纠正(驳回 finding
中的过度断言)**:"删除 `bd<=2^53` 会使 b=2^62 时 C long long 发生 overflow UB"这一说法**不准确**
——b=2^62 时 C(long long)与 Python(bignum)按位一致(无 overflow)。真正的问题是**输出的精度损失**
(Bezout 系数在 > 2^53 时无法用 float64 严格表示,导致 `a·x+b·y==g` 被破坏),`b<=2^53` 的上限正是
为守护此精度。机制描述有误,但缺陷本身与修复方案成立 = 予以采纳。

## P13 完成记录 — 最近点对(分治法)(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**几何工具集再扩展 1 个 op(P6/P7 之后的第 2 弹)**:`closest_pair`(KIND_REDUCE)= 用**分治法**
(CLRS 33.4)求 2-D 整数点集的**最小平方距离**。输入 `[x0,y0,x1,y1,...]`(2n 个 · 整数坐标
[-1e5,1e5])→ 输出 = 最小平方欧氏距离(整数严格精确)。**仅用平方距离(不开方)**,故封闭于
long long/整数 float64,C==Python 按位一致。最大平方距离 = (2e5)²×2 = 8e10 < 2^53=exact。
fail-soft = 点数 <2(n<4)/ 长度为奇数 / 坐标非整数或超出 [-1e5,1e5] 域 → -1.0。
- **算法**:按 x 排序(相等按 y)→ 递归左右两半 → d=min(dl,dr) → 从中线开始收集
  (x−midx)²<d 的点构建 strip → strip 按 y 排序 → 从每个点向前扫描(仅在 `(yj−yi)²<d` 期间 = 7
  近邻上界)。base(m≤3)用暴力法。重复点(距离 0)因相同 x 相邻排序,即使跨越分割线也会被 strip
  拾取。C 在 op.c_code 内定义 `CpPt` 结构体 + `cp_rec` 递归 + `cp_cmp_x/cp_cmp_y`(qsort)
  (codegen 会将 c_code 原样插入,故可定义 static helper)。strip 缓冲区在递归间共用一份(子调用先
  完成 = post-order,故无别名冲突)。递归深度约 log2(n)(n=1e5 时为 17)= 栈安全。
- **honest gate 实测(passed=True · c_verified=true · ziglang cc · 58 个用例)**:python==**独立
  暴力 O(n²) oracle**(不排序、不用 strip 的不同代码路径)**diff 0.0(exact)** / codegen
  **C==Python 按位一致 diff 0.0**。已事先实测=**30,000 组随机数据(用 R=3/8/30 的聚簇驱动 strip
  深度)+ 16,000 组敌对布局(密集网格/纵横直线[全部点都在 strip 内]/微小聚簇/边界坐标)与暴力法
  不一致数为 0**。
- **★gate mutation test(自行验证)**:省略 strip 扫描 / sq 忽略 y / 删除坐标上限 / 删除坐标下限 /
  删除整数性 / strip 为空这 6 种变异体**全部被捕捉**(passed=False)。cross-strip 最小情形
  ([-5,-5,-1,0,1,0,5,5]→4)单独驱动了 strip 逻辑,两个坐标槽的域外情形单独驱动了守卫。
- **holdout**:已知(单对 25 · 3 点 · 重复 dist0 · 纵向一列 · **cross-strip 最小**)+ 极端
  in-domain 坐标(8e10 上端)+ 在**两个坐标槽**上以单独理由化的域外情形(奇数长度/单点/非整数
  x·y/±1e5 超出 x·y/NaN x·y)+ 随机 40 组(聚簇)。
- **work-graph op 波**:将 closest_pair 做成 `algo_difftest --op` gate 节点(`1 op = 1 节点`)→
  用 `run-once` 实现无人值守完成。= **全部 algo op 达到 34 个 · 均已 work-graph gate 化**(33→34)。
- **回归**:在 `tests/test_algo.py` 中新增 P13 测试组(已知值 · 暴力法一致随机×4000 ·
  fail-soft[两个坐标槽] · category grouping[geometry=P6+P7+P13] · difftest python exact · C
  按位一致)。全部套件 **4834 passed / 0 failed**(+7)· ruff clean · mypy 新增 0(与
  origin/master 的 15 个相同)。对抗性评审结果见下(1 项 CONFIRMED,已自行重现并修正)。

### P13 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 个视角的对抗性评审 Workflow(correctness / c-safety+gate-honesty / integration,各项 finding 均由
验证代理**以实际 compile/执行的 mutation 重现**)= **3 个视角收敛到同一根本原因 → 1 项 CONFIRMED**
(severity = 我最初评为 MED / **验证代理评为 HIGH**,认为 gate-honesty 失败[gate 会 green-light 错误
op]更严重。作为 honest 披露两种评价并存,修正内容相同)。**op 本身正确**(在 3 万+1.6 万组敌对情形
上与暴力法不一致数为 0),但**difftest holdout 从未驱动 strip 的 y-scan 超过 immediate
neighbor(j==i+1)**→ 将 strip 前向扫描收窄至**仅 j==i+1** 的退化能被 gate 放行(因 7 近邻定理指的是
"至多 7 个"而非"恰好 1 个",按 y 序存在非相邻的最近点对是可能的)。**自行重现确定**:将扫描范围
收窄为 `range(i+1, min(i+2, sc))` 的 mutation 同时应用到 _PY/_C → `passed=True`(未被捕捉)。已在
整数网格中搜索并发现能证伪该缺陷的最小情形(例如 `[0,-6,-2,-2,4,-3,-5,3]`= 最近点对在 y 序上相隔
2 个位置 → 完整/暴力法得 20,而仅 j==i+1 得 25)。**修正**=在 holdout 与已知值测试中新增 strip 内
最近点对在 y-sorted 中非相邻的 3 种情形(`[0,-6,-2,-2,4,-3,-5,3]`→20 /
`[-4,5,-1,-3,0,-1,3,-3]`→5 / `[-1,-6,-1,0,-5,-4,1,-4,4,4]`→8)→ 重新实测确认 **j==i+1-only 的
mutation 被捕捉(passed=False, pydiff=12)**、baseline 在 61 个用例上按位一致 pass、其他 5 个
mutation 无回归。在既有的 6 种 mutation(省略 strip/sq 忽略 y/坐标上下限/整数性/空 strip)基础上,
strip 扫描深度也变得可证伪(将 P12 的 gate-coverage 教训扩展到几何领域的 strip 扫描)。

## P14 完成记录 — Huffman 最优前缀编码代价(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**数据压缩再扩展 1 个 op(P5 的 rle_encode 之后的压缩第 2 弹)**:`huffman_cost`(KIND_REDUCE)= 给定
符号频率 `[f0,f1,...]`(非负整数 ≤2^40),求**最优前缀(Huffman)编码的最小总代价**(=全部内部节点
合并权重之和 = Σ freq×编码长度)。**★核心 = 最优代价对 tie 不变**(每个符号的编码长度会随 tie
打破方式改变,但总代价由频率多重集合唯一决定),故即使 C 与 Python 以不同顺序取出等权元素,
**总和依旧相同 = 按位一致能干净地成立**。整数用 long long 携带(通过域守卫约束在 < 2^54,无
overflow)。
- **算法 = 两队列法**(Huffman O(n log n)):将频率升序排序放入 q1[叶],q2[合并节点]非递减地生成 →
  每次从 q1/q2 各自的队首取最小 2 个、把合并和 s 计入 total 并放入 q2 队尾(重复 n−1 次)。C 也用
  两个数组 + 两个队首 index 实现同一算法(qsort 比较子 hc_cmp)。
- **域与 fail-soft**:各频率 0≤f≤2^40(整数)· 否则 -1.0。**当 merge total 超过 2^53 时为
  -1.0**(float64 无法严格表示)= **对精度关键的 exactness 分支(可证伪)**。守卫过程中累计总频率
  total_freq,超过 2^53 时提前返回 -1.0 = long long safety(每个 s≤total_freq≤2^53 ·
  total≤2^54<2^63)。n=0/1 → 0.0。★**honest 披露**:上游的 total_freq 守卫是为"频率总和本身会使
  long long 溢出的极端 n(>约 4M 个符号)"设置的 safety guard,在现实的 n 下会返回与 merge bail
  相同的 -1.0 = 单靠值比较难以单独证伪(与 P5 的 OOB 守卫披露同型)。守护 exactness 的 merge-total
  bail 可由 holdout 中的 `[2^40]×1024`(总和 2^50<2^53 通过上游 · 代价约 2^53.3 触发 merge
  bail)单独驱动 = 可证伪。
- **honest gate 实测(passed=True · c_verified=true · ziglang cc)**:python==**独立 heapq(最小堆)
  版 Huffman 代价**(与两队列法不同代码路径)**diff 0.0(exact)** / codegen **C==Python 按位一致
  diff 0.0**。已事先实测=**在 5 万组随机数据(全相同频率/0 频率/2^40 域端驱动 tie)上与 heapq 不
  一致数为 0** ·**在 4000 个微小情形上与全部合并顺序暴力求出的 true optimum 不一致数为 0**
  (=贪心达到最优)·**在 2 万组上与逆 tie 顺序堆不一致数为 0**(=证明 tie 不变性)。
- **★gate mutation test(自行验证)**:删除频率上限 / 删除负数守卫 / 删除整数性 / **禁用
  merge-total bail**(能被 `[2^40]×1024` 证伪)/ 合并时丢弃 x2 / n==1 返回 1.0 这 6 种数值分支
  变异体**全部被捕捉**(passed=False)。
- **work-graph op 波**:将 huffman_cost 做成 `algo_difftest --op` gate 节点(`1 op = 1
  节点`)→ 用 `run-once` 实现无人值守完成。= **全部 algo op 达到 35 个 · 均已 work-graph gate
  化**(34→35)。
- **回归**:在 `tests/test_algo.py` 中新增 P14 测试组(已知值 · heapq 一致随机×5000 ·
  fail-soft/overflow · category grouping[compress=P5+P14] · difftest python exact · C 按位
  一致)。全部套件 **4841 passed / 0 failed**(+7)· ruff clean · mypy 新增 0(与
  origin/master 的 15 个相同)。

### P14 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 个视角的对抗性评审 Workflow(correctness / c-safety+gate-honesty / integration,各项 finding 均由
验证代理**以实际 mutation 重现**)= **3 项 CONFIRMED**(均为 merge overflow bail 边界的
gate-coverage 问题 · op 本身正确、tie 不变性也已在 5 万+4000+2 万组数据上确定)。**correctness 相关
的指摘为 0**(tie 不变性的主张、两队列法的最优性均稳健)。CONFIRMED 全部集中在"merge-total>2^53 的
fail-soft 边界"的覆盖上:
- **[MED] 阈值在约 6 个数量级内未被固定**(把 merge-total 的阈值 2^53 收窄为 2^50 等的变异体能
  通过 gate)= **自行重现确定**(2^53→2^50 的变异体 passed=True)。**修正**=在 holdout 中新增
  `[2^40]×837`(代价 8997303650091008 ≈ 2^52.998 · VALID · 应严格返回)+ `[2^40]×838`(代价 > 2^53
  → -1.0),将阈值**紧固定在 2^53 的 ±约 1e13 范围内**→ 重新实测后阈值收窄变异体(2^53→2^50、
  →8e15)全部被 **CAUGHT**。已知值测试中也新增了 837/838。
- **[MED] cost 恰好等于 2^53 的情形不在 holdout 中,导致 `>`→`>=` 的 off-by-one 未被捕捉 → 用
  WITNESS 修正**:最初曾打算披露"在 freq ≤ 2^40 下 cost 不会恰好等于 2^53",但**验证代理发现了
  构造方法**=`2^16 个 × freq 2^33`(2^33 ≤ 2^40)在每一深度 16 下**cost = 2^16 · 2^33 · 16 恰好
  = 2^53**。2^53 可精确表示,属于 VALID(应返回 2^53),而 `>` 变为 `>=` 的变异体会将其误判为
  -1.0。**我自己也做了一手验证**(用 bignum 确认 cost==2^53 · 确认 op 返回 2^53 · total_freq=
  2^49<2^53 能通过上游),之后**采纳**该 witness 情形加入 holdout 与已知值测试 → 使 `>`→`>=` 的
  off-by-one 变得可证伪(用这一处单值边界单独 pin 住)。**对抗性评审不仅发现了 gap、还发现了
  修复方法本身的一个绝佳例子**(证伪了我最初"不可达"的判断)。
- **[LOW] 上游 `total_freq > 2^53` 守卫分支未被驱动/无法证伪** = **honest 披露**:这是为"频率总和
  本身会使 long long 溢出的极端 n(>约 4M 个符号)"设置的 safety guard。在现实的 n 下 merge bail
  会返回相同的 -1.0(即使删除该守卫也不会 long long overflow、结果不变),故单靠值比较无法单独
  证伪(与 P5 的 OOB 守卫披露同型)。极端 n 的 holdout 因不现实的慢速而不予新增。
- 验证代理将这 3 项判定为"gate 无法证伪特定错误实现"的真实缺陷、判为 CONFIRMED。**op 的正确性
  不变**(未出货错误 op),已用 #2 强化 gate 的覆盖并对 #1/#3 做 honest 披露。

## P15 完成记录 — 最长递增子序列长度(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**搜索/选择再扩展 1 个 op(P8 binary_search/kth_smallest 之后的搜索第 2 弹 · DP/patience sorting
新算法族)**:`lis_length`(KIND_REDUCE)= 用 **patience sorting** 求任意 NaN-free double 数列的
**最长严格递增子序列(LIS)长度**。仅用比较(不对值做算术运算),故长度由数组本身唯一确定 =
**C==Python 按位一致**。tails[k] 保存长度 k+1 的递增子序列的最小末尾,对每个元素在
`tails[mid] < x`(bisect_left · **严格**)位置替换或扩展末尾(O(n log n))。空 → 0.0,混有 NaN →
-1.0 fail-soft(用 `x != x` 检测)。
- **honest gate 实测(passed=True · c_verified=true · ziglang cc)**:python==**独立 O(n²) DP
  oracle**(`dp[i]=1+max(dp[j]|j<i,a[j]<a[i])`,与 patience sorting 是不同代码路径)**diff
  0.0(exact)** / codegen **C==Python 按位一致 diff 0.0**。已事先实测=**在 4 万组随机数据
  (整数+浮点、小范围以大量产生 tie = 驱动严格比较)上与 DP 不一致数为 0**。
- **★gate mutation test(自行验证)**:严格 `<`→`<=`(变为非递减 = 不同答案)/ 删除 NaN 守卫 /
  二分方向反转 这 3 种变异体**全部被捕捉**(passed=False)。全相同的 `[2,2,2,2]`→1 与交替重复
  情形单独驱动了严格比较,NaN holdout 驱动了守卫。
- **holdout**:已知(`[3,1,2,4]`→3 ·`[5,4,3,2,1]`→1 · 全递增→n · 空→0 · 单元素→1)+
  **全相同→1(严格比较下重复不延伸)** + 交替重复 + -0.0/+0.0 相等值 + ±inf + 浮点 tie + 在
  **开头/中间/末尾**放置 NaN 做 fail-soft + 随机数据(整数 tie 较多 + 浮点)。
- **C 安全**:tails 缓冲区 malloc(n)· 写入 tails[lo] 时 lo≤len<n 无 OOB · n=0 时 malloc(1)+
  循环不执行返回 0.0 · malloc 失败返回 -1.0 · NaN 守卫在全部比较之前(NaN 安全)。
- **work-graph op 波**:将 lis_length 做成 `algo_difftest --op` gate 节点(`1 op = 1 节点`)→
  用 `run-once` 实现无人值守完成。= **全部 algo op 达到 36 个 · 均已 work-graph gate 化**
  (35→36)。
- **回归**:在 `tests/test_algo.py` 中新增 P15 测试组(已知值 · DP 一致随机×5000 · NaN
  fail-soft[3 个位置] · category grouping[search=P8+P15] · difftest python exact · C 按位
  一致)。全部套件 **4848 passed / 0 failed**(+7)· ruff clean · mypy 新增 0(与
  origin/master 的 15 个相同)。

### P15 对抗性评审结果(2026-08-17, [[feedback_no_solo_ai_judgment]])
3 个视角的对抗性评审 Workflow(correctness / c-safety+gate-honesty / integration,mutation 验证)=
**findings 0**(全部视角均无指摘)。已验证 patience sorting 的严格比较 · NaN 守卫 · tails
缓冲区安全 · O(n²) DP oracle 的独立性 · holdout 单独驱动严格比较的能力,未检测到可证伪的缺陷。
事先的 mutation 3/3 全部被捕捉(严格 `<`→`<=`/NaN 守卫/二分方向)与 4 万组 DP 一致,说明 gate 稳健。

## P16 完成记录 — 逆序数(归并排序法)(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**统计再扩展 1 个 op(P9 count_distinct/mode_value 之后的统计第 2 弹)**:`count_inversions`
(KIND_REDUCE)= 用**计数归并排序**以 O(n log n) 求任意 NaN-free double 数列的**逆序数**
(i<j 且 a[i] > a[j] 的**严格**对数)。仅用比较(不对值做算术运算),故 count 由数组本身唯一确定 =
**C==Python 按位一致**。合并时每当右列先取出一个元素,就把左列剩余数量累加(经典做法)。count 为
非负整数,故 **-1.0 是安全 sentinel**:NaN→-1.0 fail-soft,空/单元素→0.0。相等值不算逆序(tie 时
先取左边 = `arr[i] <= arr[j]`)。
- **honest gate 实测(passed=True · c_verified=true · ziglang cc)**:python==**独立 O(n²) 暴力
  count**(与归并排序不同代码路径)**diff 0.0(exact)** / codegen **C==Python 按位一致 diff
  0.0**。已事先实测=**在 4 万组随机数据(整数+浮点、小范围产生大量 tie = 驱动严格比较)上与暴力
  法不一致数为 0**。
- **★gate mutation test(自行验证)**:tie 处理 `<=`→`<`(将相等值误计为逆序)/ inv 计数
  off-by-one / 删除 NaN 守卫 / 不计数(inv=0)这 4 种变异体**全部被捕捉**(passed=False)。全相同
  `[2,2,2]`→0 与重复情形单独驱动了严格比较。
- **holdout**:已知(sorted→0 · reversed→n(n-1)/2 ·`[2,1,3]`→1 ·`[3,1,2]`→2 · 空/单元素→0)+
  **全相同→0(严格性)** + 重复(sorted→0 ·`[2,1,2,1]`→3)+ -0.0/+0.0 相等值(两种顺序)+ ±inf +
  在**开头/中间/末尾**放置 NaN 做 fail-soft + 随机数据(整数 tie 较多 + 浮点)。
- **C 安全**:arr/tmp 用 malloc(n)· 递归深度 O(log n)· malloc 失败返回 -1.0 · NaN 守卫在全部
  比较之前。count 用 long long(对 n < 4.3e9 而言 n(n-1)/2 < 2^63),返回的 double 在
  n(n-1)/2 < 2^53 时严格精确(honest:在极端 n 下可能不再严格,但 holdout/实用域内是严格的)。
- **work-graph op 波**:将 count_inversions 做成 `algo_difftest --op` gate 节点(`1 op = 1
  节点`)→ 用 `run-once` 实现无人值守完成。= **全部 algo op 达到 37 个 · 均已 work-graph gate
  化**(36→37)。
- **回归**:在 `tests/test_algo.py` 中新增 P16 测试组(已知值 · 暴力法一致随机×5000 · NaN
  fail-soft[3 个位置] · category grouping[stat=P9+P16] · difftest python exact · C 按位
  一致)。全部套件 **4855 passed / 0 failed**(+7)· ruff clean · mypy 新增 0(与
  origin/master 的 15 个相同)。**对抗性评审在 worktree 隔离环境下执行**(源于 P14 的教训 =
  评审代理曾 mutate 了目标 repo 的 algo.py,故 commit 后改在隔离 worktree 中评审 → 结果作为
  follow-up)。

### P16 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
**★worktree 隔离评审首次成功应用**:3 个视角 × 隔离 git worktree(各代理从 cd76da0 建立各自
专用副本并做 mutation)→ **本 repo 的 algo.py 始终保持干净**(验证代理也明确记录"real repo 为
只读 · 在隔离 worktree 中做 mutation · 已清理善后")。结构性解决了 P14 的污染问题。结果 =
**2 项 CONFIRMED(均为 LOW)** · correctness 相关为 0(op 正确):
- **[LOW gate-coverage] long long 位宽未被证伪**:holdout 的最大逆序数低于 INT_MAX(len ≤ 40 →
  最大约 700),使 C 的累加器由 `long long` 收窄为 `int` 的变异体能通过 gate(出货代码本身正确地
  使用 long long)。**自行重现确定**(int 收窄变异体 passed=True · n=65537 的严格降序中真值
  2147516416 > INT_MAX,int 会环绕为 -2147450880)。**修正**=(1)新增**独立的 Fenwick(树状数组)版
  oracle `_fenwick_inversions`**(O(n log n)· 与归并排序不同的算法,可对大 n 做核算,弥补 O(n²)
  暴力法过慢的问题),(2)在 holdout 与已知值测试中新增**严格降序 witness(n=65537,逆序数
  2147516416 > INT_MAX)**→ 重新实测后 int 收窄变异体被 **CAUGHT**(passed=False)。
- **[LOW annotation] 注释有误**:曾在 `[inf,1,-inf]` 处注记为 `-> 2`,实际应为 3(全部 3 对均为
  逆序)。gate 是与 oracle 比较(在 3 处一致)故不会放行错误实现 = **仅注记本身不准确**。
  **修正**=将注释改为 `-> 3`(已确认 op/oracle/Fenwick 三者均得 3、一致)。
- **★运用改进的实证**:此后的评审均默认采用 worktree 隔离。全部套件全绿 · ruff clean · mypy
  新增 0。

## P17 完成记录 — 最大子数组和(Kadane 算法)(2026-08-17, Opus5[1m]/ultracode, 12h 自律)
**搜索/优化再扩展 1 个 op(P8 binary_search/kth_smallest · P15 lis_length 之后的搜索第 3
弹)**:`max_subarray`(KIND_REDUCE)= 对整数值 double 数列用 **Kadane 的 O(n) 重置扫描**
(`cur = max(0, cur+x); best = max(best, cur)`)求**连续子数组的最大和**。**允许空子数组**
(和为 0),故答案**恒 ≥ 0**(全负时为 0.0)= **-1.0 是安全 sentinel**。在整数域内(各
`|x| ≤ 2^52` 且绝对值的滚动和 ≤ 2^52)使全部部分和都保持在严格整数 < 2^53 → 答案严格精确 ·
**C==Python 按位一致**。独立 oracle(全部 O(n²) 子数组的暴力最大值)因**整数加法的结合律**而与
Kadane 严格一致。fail-soft -1.0 = NaN / inf / 非整数 / `|x| > 2^52` / 滚动和溢出。
- **honest gate 实测(passed=True · c_verified=true · ziglang cc)**:python==**独立 O(n²) 暴力法**
  (与 Kadane 不同代码路径)**diff 0.0(exact)** / codegen **C==Python 按位一致 diff 0.0**。已
  事先实测=**在 5000 组随机数据(整数 · 混合符号 · 小范围以大量驱动 tie/重置)上与暴力法不一致数
  为 0**。
- **★gate mutation test(自行验证)**:(1) overflow 守卫 `>`→`>=`(用恰好 2^52 的 witness
  误判 bail)→**被捕捉**,(2) 删除重置逻辑 `if cur<0: cur=0`(变为后缀和 = 错误)→**被捕捉**,
  (3) 删除域守卫(inf 时 `int()` 崩溃)→**被捕捉**,(4) **真正的非空 Kadane**(不含空选项)→ 在
  全负 holdout `[-1,-2,-3]`(正确答案 0.0)上**被捕捉**(err=5.0),(5) best 更新 `>`→`>=`
  (等价)→ 如预期未被捕捉。
- **★设计依据的验证**:真正的非空 Kadane 在全负 `[-1,-2,-3]` 上会返回最大元素 -1.0 =
  **与 fail-soft sentinel -1.0 冲突**。mutation test 证明了"因允许空而使答案 ≥ 0 → -1.0 是安全的"
  这一设计正是为了避免这种冲突而生效(允许空 = sentinel 健全性的前提)。
- **holdout**:空/单个正数(5)/单个负数(0)·**全负→0(单独 pin 住允许空这一点)**· 经典 Kadane
  `[-2,1,-3,4,-1,2,1,-5,4]`→6 · 中段回落造成重置 · 0/-0.0 带符号零 · **在 2^52 处 pin 住 overflow
  边界**(`[2^52]`=滚动和 2^52 → **valid**(单独 pin 住 `>` 与 `>=` 之别)/ `[2^52,1]`=2^52+1 →
  -1.0 / `[2^51,2^51]`=2^52 → valid / 单个 `[2^52+1]` > 2^52 → -1.0)· 在开头/中间放置非整数/
  ±inf、在开头/中间/末尾放置 NaN 做 fail-soft · 随机整数数据。
- **C 安全**:域检查 `x >= -LIM && x <= LIM` 在**(long long) cast 之前**就拒绝 NaN/inf/超大值
  (NaN→int 是 UB)。累加用 long long,滚动和 ≤ 2^52 使全部部分和 < 2^63(不会溢出),返回的
  double 在 best < 2^53 时严格精确。
- **work-graph op 波**:将 max_subarray 做成 `algo_difftest --op` gate 节点(`1 op = 1 节点`)→
  用 `run-once --available tool:command` 实现无人值守完成(gate JSON passed=True ·
  c_verified=true)。= **全部 algo op 达到 38 个 · 均已 work-graph gate 化**(37→38)。
- **回归**:在 `tests/test_algo.py` 中新增 P17 测试组(registered_kind · 已知值 · 暴力法一致
  随机×5000 · fail-soft/overflow · difftest python exact · C 按位一致)。**honest**:首次完整
  运行时 `test_search_ops_registered_kinds` 出现 1 failed(search category 集合的更新只改了 **两处
  中的一处**[`test_categories_grouping`])→ 已发现并立即修正,重新运行后 **test_algo.py 295
  passed / 0 failed** · ruff clean · mypy 新增 0(与 origin/master 的 15 个相同)。**对抗性评审在
  worktree 隔离环境下执行**(P16 建立的做法)。

### P17 对抗性评审后的强化(2026-08-17, [[feedback_no_solo_ai_judgment]])
**worktree 隔离评审(4 个 agent · 3 个视角 + 对抗性验证)= 1 项 CONFIRMED(LOW ·
gate-honesty)/ refuted 0**。验证代理在隔离 worktree 中完整重现,并明确记录本 repo 的 algo.py
未被污染(`status --porcelain` 只有 auto 的 SESSION_SUMMARY)。correctness/integration 相关为 0
(op 正确):
- **[LOW gate-honesty] C 中"在 cast 之前拒绝 NaN"这一点无法被 gate 证伪**:honest gate 只用
  `-O2 -std=c99 -ffp-contract=off`(无 UBSan)编译 C。若将 C 的域守卫做 De Morgan 改写
  `if (!(x>=-LIM && x<=LIM))` → `if (x<-LIM || x>LIM)`(NaN 时两个比较都为 false = NaN 会漏过),
  紧接着下一行 `x != (double)(long long)x` 的 **`(long long)NaN` 是 UB**,在 -O2 下恰好落到
  相当于 -1.0 的结果、与 Python 按位一致 → gate 判为 passed=True。但同一变异体**在
  UBSan/ReleaseSafe 构建下会硬性 trap**(`panic: nan is outside the range of representable
  values of type 'long long'`)。**出货的 op 是正确的**(守卫 `!(x>=-LIM && x<=LIM)` 会在 cast
  之前拒绝 NaN)= 这是 gate-coverage 的缺口(不是生产缺陷)。Python 一侧已被 pin 住(删除域守卫会
  使 `int(nan)` 抛出 ValueError,gate 不会放行而报错)= 唯独 C 侧未对称地 pin 住。
- **一手验证(自行重现)**:用与 gate 相同的编译选项 `-O2 -std=c99 -ffp-contract=off` 做独立
  probe:出货 guard = NaN→-1.0 正常 / De Morgan+UBSan = `(long long)NaN` trap(与 finding 中的
  panic 一致)/ 出货 guard+UBSan = 无 trap(在 cast 之前就拒绝 NaN = **UBSan-clean**)。
  **honest 的差异**:我的独立 probe 中 De Morgan+-O2 会以 exit3 崩溃,但**实际 gate**
  (`algo_difftest --op`)中确认了如验证代理所报告的那样通过 = -O2 下的 UB 行为不确定,无论如何
  "仅靠 -O2 无法确实 pin 住 reject-before-cast"这一点成立。
- **修正(强化全部 op)**:在 `run_c_backend` 中新增 **UBSan pass**——在 -O2 按位比较之后,用
  `-fsanitize=undefined -fno-sanitize-recover=all` 对同一份 C 重新编译并在同一 holdout 上再次运行。
  一旦 NaN/inf/域外值到达整数 cast 就会 trap → **gate fail**(不支持 UBSan 的 toolchain 返回
  `"unsupported"` = neutral,不会误判)。**事先实测**:全部 38 个 op 均为 UBSan-clean(trap 数
  0)= 无误报、可安全采用。**修正后实测**:出货 op = passed=True/ubsan=ok,**De Morgan 变异体 =
  passed=False/ubsan=trap**(按位比较在 -O2 下为 True,但被 UBSan 捕捉)、其他 op 无回归。=
  **使"reject-before-cast"在 C 侧也变得 load-bearing**(与 Python 的 `int(nan)` raise 对称)。
  新增回归 pytest `test_ubsan_pass_catches_nan_slip_through_cast`。全部套件从 **295 增至 296
  passed / 0 failed** · ruff clean · mypy 新增 0。
- **★这不是 max_subarray 专属问题,而是 gate 基础设施的强化** = 此后全部 algo op 都能让 gate
  证伪"非有限值到达 cast 造成 UB"这类问题。

## 2026-09-03:对抗性评审(algo + C codegen)的 8 项修正

- **[HIGH] C 的 `unsharp`(`sharpen`)缺少 [0,1] 裁剪,导致后段 op 与 Python 产生偏差**
  (unsharp→gaussian 最大差 6.6e-2,unsharp→threshold(1.0) 时 512 个像素反转)。在 `sharpen` 出口
  加入 clamp + `codegen.py` 在每个需要 clip 的 sort 的各 stage 之后输出 `clamp01()`(双重保险)。
  修正后 ≤ 3e-7。
- `difftest.py` 只查找 gcc/cc/clang,导致**在本环境下 C gate 被静默 skip**(因此上述偏差一直未被
  发现)。改为共用 `algo_difftest.find_c_compiler()`(带 ziglang fallback)。结果字典中新增记录
  `compiler`。
- 图 op 的 `n` 在 int32 上限内不受限制(`graph_components([2147483000,0])` 会分配 17 GB)→ 改为
  **`n ≤ 5,000,000`**(与 sieve 相同的明确上限),`m ≤ 2147483000`,Python/C 均如此。
- 曾先将端点 `(int)` cast 后才做范围检查(float→int 溢出 UB,会被 UBSan trap)→ 改为先用原始
  double 检查范围与整数性。UBSan trap 从 3 处降为 0,39/39 位一致。
- **哨兵值变更(ABI)**:对于"0.0 本身也是合法答案"的 op,将其 fail-soft 哨兵值由 **0.0 改为
  −1.0**——涉及 `is_prime` / `segments_intersect` / `edit_distance` / `point_in_polygon` /
  `lcs_length`(与 P13〜P18 相同的约定)。例如:`is_prime([4294967311])`(超出定义域)现在返回
  −1.0 而非表示"合数"的 0.0。未变更的(可能存在冲突、待研究):`pow_mod` / `gcd_seq` /
  `popcount_total` / `polygon_area2`。
- `run_algo` 曾对超过 2^53 的整数先用 `float()` 舍入再做定义域检查 → 改为用 `wire_float()`,对
  |x|>2^53 的整数输入抛出 `ValueError`(fail-closed)。
- `box` 的偶数 k 曾使用 k+1 个 tap 却除以 k(增益 1.25)→ 改为与 scipy `uniform_filter` 相同的
  origin、使用 k 个 tap。
- `difftest` 中的 NaN 曾因 `max(0.0, nan)=0.0` 而被判为合格 → 改为将非有限值视为 inf 判定为不合格。
- 回归:新增 `tests/test_imgops_c.py`(新设 11 个)等共 35 个测试,5 个文件共 355 passed(C 测试
  全部用 ziglang 执行)。
