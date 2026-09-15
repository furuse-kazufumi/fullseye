<!-- i18n-source-sha: b50d12a26df4 -->
# 将 Fullseye 用作 AI 助手 RAG 的方法（面向 Claude Code）

[日本語](./AI_RAG_GUIDE.md) · [English](./AI_RAG_GUIDE.en.md) · **简体中文** · [繁體中文](./AI_RAG_GUIDE.tw.md) · [한국어](./AI_RAG_GUIDE.ko.md) · [Deutsch](./AI_RAG_GUIDE.de.md)

Fullseye 的推荐用法是"**作为 AI 编码助手的知识库（RAG）使用**"。由于所有 op 都拥有机器可读的 Markdown 笔记（`docs/ops`，唯一可信来源），因此**不需要**额外的向量数据库或嵌入服务。只要环境支持 grep，它本身就是一个 RAG。

我们提供三个阶段的引入方式。**Tier 0/1 没有任何外部依赖**（仅凭 Fullseye 仓库本身即可完成）。

## 入口不止一个（请先读这一节）

只拿到文档的 Codex 和 Copilot，在第一次尝试时**都没能找到按用途查找的索引**（2026-09-15）。原因就是本指南没有指向它的链接。入口有四个：

1. **按用途** → [`docs/CAPABILITIES.md`](CAPABILITIES.md)。每个课题一个文件（`docs/capabilities/`），给出**推荐流水线（有序 op）/ 替代 / 局限 / 实际尺寸标定**；`tests/test_capabilities.py` 检查 op 名实际存在，并且**类型（in → out）在前后步骤之间衔接**。
2. **按 op 名或概念** → [`docs/ops/INDEX.zh.md`](ops/INDEX.zh.md) → 系列目录 → op 笔记。
3. **由机器查找** → `fs.op_find(query)`（自由词·词干）/ `fs.op_assist(op)`（规格·预设·下一步可接什么）/ `fs.op_path(from_sort, to_sort)`（把类型 A 连到类型 B 的 op 序列）/ `fs.op_producers(sort)`（生成该类型的 op）/ `fs.op_accepts(op)`（实测的可接受类型）；命令行用 `fullseye has <op>`（HALCON 名也可）。
4. **索引文件** → [`docs/OP_INDEX.json`](OP_INDEX.json)（全部 op 的类型契约）、wheel 随附的 `OP_CATALOG.md`。


> **从 PyPI 使用**：在执行了 `pip install fullseye` 的环境中，可以使用控制台脚本 **`fullseye-rag`**。若是 checkout（clone / `pip install -e .`），会将 `docs/ops` 的完整语料库固定到技能中；若仅为 wheel 安装，则会将随附的 `OP_CATALOG.md`（面向 AI 的全 op 目录）固定为技能（之后如果需要完整的逐 op 笔记，只需 clone 仓库后重新执行即可）。更新方式为 `py -3.11 tools/update_fullseye.py`（拒绝在 dirty 树上执行 · `--ff-only` · 在备份基础上更新技能 · 不触碰 Studio 设置——设计上不会破坏你的环境）。

---

## Tier 0：只需打开仓库（零步骤）

在 Claude Code 中打开 Fullseye 仓库的 checkout，即可直接检索和参照 `docs/ops/INDEX.md` 以及各 op 笔记。语料库属于仓库内容（wheel 中不包含），因此若只做了 pip 安装，请同时 clone 仓库。

```
docs/CAPABILITIES.md                    # 用途 → op 链(推荐流水线 / 替代 / 局限 / 实际尺寸标定)。从这里进入
docs/ops/<family>/<category>/<op>.md    # 调用形式·类型契约·HALCON 别名·参考文献·相关 op(2d / 3d / optics / piv …)
docs/ops/INDEX.md                       # 遍历文件夹层级自动生成的整体目录(34 个系列)
docs/ops/<family>/guides/<name>.md      # 使用指南 49 篇(34 个系列。2-D 的是 gallery2d_*;公式·图示·经典文献引用)
docs/OP_INDEX.json                      # 注册表的机器可读索引
```

这些数字（34 个系列、49 篇指南、笔记数）都是从发布的文件一侧数出来的，`tests/test_docs_index_reachable.py` 会把这一行与实际文件比对（防止自我描述落后于内容）。

**从 Windows 的 shell 读取时请显式指定 UTF-8** —— 笔记是不带 BOM 的 UTF-8，用默认代码页打开会使日文变成乱码，AI 明明是"没读到"却判断为"不存在"（Codex 上实际发生过）。PowerShell 用 `Get-Content -Encoding utf8`、`[Console]::OutputEncoding = [Text.Encoding]::UTF8`（或 `chcp 65001`），Python 用 `PYTHONUTF8=1`。

## Tier 1：作为技能常驻（推荐 · 内置安装脚本）

如果想在自己的项目中工作的同时调用 Fullseye，只需运行一次内置的安装脚本：

```bash
py -3.11 tools/setup_claude_rag.py              # 安装(重新执行 = 更新)
py -3.11 tools/setup_claude_rag.py --uninstall  # 卸载
```

内置技能 `skills/fullseye-ops` 会被复制到 `~/.claude/skills/fullseye-ops`，SKILL.md 中的 `FULLSEYE_REPO =` 一行会**自动固定为此 checkout 的绝对路径**（这样无论 AI 在哪个项目中工作，都能知道语料库的位置）。若在找不到语料库（`docs/ops`）的 checkout 中执行，安装会被拒绝（fail-closed）。

此后，在涉及图像处理、几何视觉的话题时，Claude Code 会自动启动此技能，按照"检索（retrieve）`docs/ops` → 选择类型（sort）相衔接的 op 并实现 → 用内置的 worked example 验证"的流程运作。技能正文本身就是"对 AI 的使用说明书"。若想手动安装，只需将 `skills/fullseye-ops` 复制到 `~/.claude/skills/` 也可以运作（只是没有路径固定，AI 每次都需要自行查找仓库位置）。

## Tier 2（可选）：聚类语料库——借助外部工具的进阶形态

也可以将 **1,949 条**笔记按主题聚类分层，并为每个聚类附上 LLM 摘要，做成"带导航的语料库"。我们内部使用的是 [RAPTOR](https://github.com/gadievron/raptor) 分支的 `corpus2skill`（TF-IDF + k-means + LLM 摘要），但**这只是一种可选的优化，并非必需**。要求仅仅是"以 `docs/ops` 为输入，输出按聚类划分的 SKILL.md 层级结构"，因此任何等效的工具都可以替代。

重新导入（笔记更新后）的示例——如实记录内部的运行方式：

```powershell
$env:RAPTOR_DIR="<path-to-raptor-checkout>"
py -3.11 raptor_corpus2skill.py --source <fullseye>/docs/ops --name fullseye_ops_corpus_v2 `
  --overwrite --max-depth 2 --max-clusters 6 --min-cluster-size 8   # 需要 ANTHROPIC_API_KEY
```

注意：聚类语料库是**导入时刻的快照**。更新 `docs/ops` 后如果不重新导入就会过时（Tier 0/1 始终读取原始笔记，因此不会过时）。

---

## 为什么这样可行（设计依据）

1. **md = 唯一可信来源**：笔记由注册表确定性地自动生成，CI 的 drift 测试会强制要求"已提交的笔记 == 由当前代码生成的笔记"一致。**AI 阅读的文档与实际代码始终是同一版本**（frontmatter 的 `version` + fingerprint）。
2. **类型（sort）契约**：每条笔记都带有 `in:`/`out:` 以及"类型相衔接的相关 op"，因此 AI 可以在**进行类型检查的同时**组装流水线。
3. **可验证**：所有 op 都配有带 ground truth 的 worked example（`examples/` / `examples_3d/`），AI 可以自行执行其提案并加以确认。
4. **一直贯通到显示**：打开 Studio（`py -3.11 studio.py`），人类就能在同一屏幕上以图像窗口、3D 显示的形式检查 AI 组装的结果（也可以通过 `dev_open_window` 等从脚本中配置多个窗口）。
