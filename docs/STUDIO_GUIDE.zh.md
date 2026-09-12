# Fullseye Studio 完全指南

[日本語](./STUDIO_GUIDE.md) · [English](./STUDIO_GUIDE.en.md) · **简体中文** · [繁體中文](./STUDIO_GUIDE.tw.md) · [한국어](./STUDIO_GUIDE.ko.md) · [Deutsch](./STUDIO_GUIDE.de.md)

**Fullseye Studio** 是一个类似 HDevelop 的可视化流水线工作台。你可以搜索并排列算子，用两个旋钮滑块调节参数，一边缩放/平移查看中间结果一边逐段执行，最终把搭建好的流水线导出为 `--ops` 字符串 / Python / JSON。它的实体是 `fullseye` API 的一层薄 GUI 前端，流水线逻辑（`PipelineModel`）·Inspector（`inspect_result`）·示例集（`recipes`）都不依赖 Qt，并且都有独立的单元测试。

本指南是把 `studio.py`（`build_window`）与实际代码对照后列出的功能清单。UX/设计的意图在 [STUDIO_UX.md](STUDIO_UX.md)，v14 感知面板的背景在 [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md)。

---

## 启动方式

需要 GUI extras（PySide6）（`pip install -e ".[gui]"`）。

```powershell
py -3.11 studio.py          # 直接从仓库根目录运行
fullseye-studio             # 若已 pip install -e .，可用控制台脚本
```

启动后会打开一个 1320×860 的主窗口（标题: Fullseye Studio）。如果存在 `assets/fullseye.ico`，会作为窗口/任务栏图标出现。初始状态下已加载合成演示图像（`demo_image`，包含边缘·斑点·渐变的 256×256 图像）。

---

## 界面构成（3 个面板）

上方是**菜单栏**（File / Edit / View / Run / Help）和**品牌工具栏**，下方是**状态栏**（悬停时的坐标+像素值，`flash()` 的临时消息）。中央为左右分栏的 3 个面板。

| 面板 | 分区（QGroupBox） | 作用 |
|---|---|---|
| 左 | **SAMPLE PIPELINES** / **OPERATORS** | 加载示例、浏览算子 |
| 中 | **PIPELINE** / **SELECTED STAGE · KNOBS** / **EXPORT & I/O** | 搭建流水线、调节旋钮、导出 |
| 右 | **IMAGE** / **DISPLAY & PERCEPTION (v14)** / **ANALYSIS** | 结果显示、颜色映射/感知、直方图/Inspector |

初始分栏宽度为 340 / 360 / 640 px，右侧面板可伸缩。

---

## 左侧面板: Operators 浏览器

### 示例流水线（SAMPLE PIPELINES）
从下拉菜单中选择 **20 个**现成配方（`recipes.py`）之一，流水线就会替换为该配方。例如"Edge — Sobel + Otsu""Denoise — bilateral + unsharp""Segment — blob / coin""Count — blobs""Texture — Gabor"等。是先跑起来再看内容的便捷起点。

### 算子浏览器（OPERATORS）
- **分类筛选**: "all categories" + 31 个分类（smoothing / edges / morphology / segmentation / features / texture / region / contour / color / frequency / restoration / 3d ……）。
- **搜索框**: 按算子名·HALCON 别名·分类做部分匹配过滤（带清除按钮）。
- **列表**: 每行显示 `name [in_sort → out_sort]`。**双击插入**。悬停会以工具提示显示"名称 / HALCON 别名 / 分类 / sort 转换 / 旋钮 a,b 的说明"。

插入位置为"当前选中阶段的下一个位置"。如果没有选中任何阶段，则追加到末尾。

---

## 中央面板: 搭建流水线与逐段执行

### PIPELINE（阶段列表）
每一行的格式为 `N. op (a=…, b=…) -> 结果摘要`，执行到该阶段为止的结果状态（image/region/feature 等）显示在右侧。

- **重新排序**: 拖动行（InternalMove）互换位置，或使用 **↑ Up / ↓ Down** 按钮·**Ctrl+↑ / Ctrl+↓**。
- **删除**: **Remove** 按钮·**Del**。
- **逐步执行的 3 个按钮**:
  - **⏮ Reset（Home）** — 显示应用流水线之前的原始图像（逐步执行的起点）。
  - **Step ▶（Ctrl+→）** — 前进一段。
  - **Run all ▶▶（Ctrl+Enter）** — 一次性显示最终结果（主强调色按钮）。

选中某一阶段后，该阶段为止的中间结果会绘制在右侧 IMAGE 面板，下方的 ANALYSIS（直方图 / Inspector）也会同步更新。这相当于"逐步调试器"。

### SELECTED STAGE · KNOBS（旋钮调节）
显示所选阶段的详细信息（`op_detail`: 名称·`in → out` sort·分类·HALCON 别名），并通过 **2 个滑块 a / b（0.00～1.00）** 调节。拖动数值会立即重新计算结果。未选中任何阶段时，滑块会被禁用（不让"无意义的旋钮"处于可用状态的设计）。

旋钮的含义因算子而异（半径 / 阈值 / σ / 方向等）。要调节的是什么，可通过阶段详情标签和工具提示确认。

### EXPORT & I/O
- **Export（ops string + Python）…（Ctrl+E）** — 将当前流水线同时以 `--ops "…"` 字符串和可独立运行的 Python 函数两种形式输出到对话框（便于复制）。
- **Save pipeline…（Ctrl+Shift+S）** — 将流水线保存为 JSON（`{"fullseye_pipeline": 1, "stages": [...]}`）。这个 JSON 就是 `FullseyeEngine.load` / `imgevolve.py run` 的输入。
- **Open pipeline…（Ctrl+Shift+O）** — 加载已保存的 JSON。

---

## 右侧面板: 显示·感知·分析

### IMAGE（结果视图）
- **Load image…（Ctrl+O）** — 加载图像文件作为基准帧（png/jpg/bmp/tif）。
- **Synthetic demo（Ctrl+D）** — 加载合成演示图像。
- **Save result…（Ctrl+S）** — 将当前显示的结果保存为 PNG。
- **缩放**: 鼠标滚轮在光标位置缩放，拖动平移。**Zoom +（Ctrl+=）/ Zoom −（Ctrl+-）/ Fit（Ctrl+0）/ 1:1（Ctrl+1）**。
- 当结果为标量 feature、contour 结果或尚未加载图像时，视图中央会显示提示信息（不留空白）。
- 悬停时，状态栏会显示 `x, y, value`（彩色图像则显示 RGB）。

### DISPLAY & PERCEPTION (v14)
- **Display（颜色映射）** — 为 2D 结果着色以便显示: `gray` / `shaded relief` / `height (color)` / 各种颜色映射（jet, viridis, turbo, magma, plasma, inferno ……）。
- **3D surface（Ctrl+3）** — 将当前结果以可旋转的 3D 曲面显示（仅在有 `QtDataVisualization` 时可用／best-effort）。便于查看高度/深度图。
- **感知面板（2 帧）** — 用 **Load frame B…** 加载第 2 帧，选择模式后 **Run**:
  - `optical flow` — 用色相可视化两帧之间的稠密光流。
  - `motion overlay` — 把运动区域叠加到原图上。
  - `stereo depth` — 从立体视差估计深度并着色。
  - `stereo terrain` — 立体→点云→地形高度图，并着色。

  没有帧 B 或尺寸不一致时，会在状态栏显示错误并安全中止。

### ANALYSIS
- **Histogram** — 当前 2D 结果的亮度直方图。
- **Inspector（variable / image / region）** — 按 sort 检查结果。image/color 显示 shape·min/max/mean·非有限值数量，region 显示连通分量数·面积·最大区域，feature 显示数值，contour 显示轮廓数。二值区域时还会附上各区域的特征表（`detect.feature_table`）。

---

## Command palette（Ctrl+P）

按 `Ctrl+P` 会打开一个模糊搜索对话框，可以**按名称执行任意操作或任意算子**。排序规则是前缀匹配 > 单词前缀匹配 > 部分匹配（`palette_filter`，不依赖 Qt，已做单元测试）。操作（如 `▸ Open image`）排在前面，接着是全部算子（如 `op: gaussian`），按 Enter 执行。仅用键盘就能完成到算子插入为止的全部操作。

---

## 键盘快捷键

应用内可通过 **Help ▸ Keyboard shortcuts（F1）** 以表格形式查看全部快捷键（自文档化）。主要的（来自 `studio.py` 的 `act_*` 定义）:

| 操作 | 快捷键 | 操作 | 快捷键 |
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

每个操作无论从菜单、工具栏还是按钮触发，都会调用同一个处理函数（一个动作、多个入口）。

---

## HDevelop `dev_*` 绘图控制指令

与 HDevelop 相同，可以**从程序中控制绘图行为**。在 Program 窗口的脚本中写入 `dev_*` 行，
它不会被解释为图像阶段，而是作为**显示指令**，在 Apply 时生效
（`docs/HDEVELOP_DEV_OPS.md` 中收录了全部 43 个 `dev_*` 的详尽说明）。

| 指令 | 效果 | 对应 UI |
|---|---|---|
| `dev_update_window ('off'|'on')` | 切换图形窗口的自动更新 | View ▸ Display updates ▸ Graphics window |
| `dev_update_var ('off'|'on')` | 切换变量窗口的自动更新 | 同上 Variable window |
| `dev_update_pc ('off'|'on')` | 切换执行光标的更新 | 同上 Program counter |
| `dev_update_time ('off'|'on')` | 切换逐行处理时间显示 | 同上 Operator timings |
| `dev_update_off ()` / `dev_update_on ()` | 一次性将以上全部关闭 / 打开 | 工具栏 **Auto-update** 开关 |
| `dev_set_part (Row1, Col1, Row2, Col2)` | 设置显示范围（缩放/平移）·负值=整体 | 与鼠标滚轮/Fit 配合使用 |
| `dev_set_lut ('gray'|'jet'|'viridis'…)` | 切换颜色映射（LUT） | View ▸ Display mode |
| `dev_clear_window ()` | 清空当前窗口 | — |
| `set_system ('thread_num', N)` | 设置 OpenCV 工作线程数（0=默认/全部） | Tools ▸ System settings |
| `set_system ('operator_timeout', ms)` | 软性算子超时（在 Run status 中警告执行慢的阶段） | 同上 |
| `dev_set_draw ('fill'|'margin')` | 切换 region 叠加层的填充（fill）/ 轮廓（margin） | View ▸ Display mode = region overlay |
| `dev_set_color ('red'|'green'…)` | region 叠加层的颜色 | 同上 |
| `dev_set_line_width (N)` | margin 轮廓线宽（px） | 同上 |
| `dev_disp_text ('label', Row, Col)` | 在结果上方添加文字注释（在下一次绘制/`dev_clear_window` 时消失） | — |
| `dev_open_window (Row, Col, W, H)` | **打开并放置**图形窗口并设为当前（再次 Apply 会重新放置同一个窗口=不会重复增生） | Ctrl+G / Window ▸ Graphics |
| `dev_set_window (Handle)` | 用句柄切换当前窗口 | 点击窗口 |
| `dev_set_window_extents (Row, Col, W, H)` | 当前窗口的位置·大小（-1=保持现状） | 拖动窗口 |
| `dev_close_window ()` | 关闭当前窗口（常驻的主窗口受保护） | 窗口的 × |
| `set_system ('max_graphics_windows', N)` | 窗口数量上限（默认 256·所有路径 fail-closed） | Tools ▸ System settings ▸ Windows |

**用途**: 在开头放置 `dev_update_off ()`，可以在**不产生绘图开销**的情况下进行大量处理或大量编辑，
之后用 `dev_update_on ()` 一次性刷新到当前状态（与 HDevelop 的性能技巧相同）。更新处于
关闭状态时，状态栏右侧会显示 `updates off: …`，因此冻结状态不会看起来"像是坏了"。
工具栏的 **Auto-update** 开关也能实现同样的切换。

**注意**（如实说明）: 与流水线阶段不同，`dev_*` **不遵循** `if`/`for`，会**无条件应用**
（即使写在分支内部也会触发）。请写在顶层。未支持的 `dev_*` 会报错。

**动手看看**: 通过 **File ▸ dev_* visualization demo**，可以加载并执行一个实际使用 coins 图像 +
上述 `dev_*` 的 HDevelop 程序（分割→用青色轮廓+标签显示区域）。用于练习的示例图像位于
**File ▸ Sample images**（共 8 张，来源见 `studio_assets/sample_images/manifest.json`。
合成图像 = 自制作品／`coins`·`camera` 等 = 来自 skimage.data 的 BSD/公有领域素材。可用
`tools/gen_sample_images.py` 重新生成）。

---

## 多语言支持(en / ja / zh，表驱动)

界面语言可通过 **Tools ▸ Language / 言語 / 语言** 切换(会被记住)。译文统一存放在
**`studio_assets/i18n.json`** 这张表中，无需修改代码即可增加语言:

- `languages` — 语言列表(添加后会自动出现在菜单中。英语始终作为基准)
- `tooltips` — 工具提示译文(以英文原文为键)
- `strings` — **菜单·按钮·对话框标签的译文**(以英文原文为键。2026-08-30
  新增。内置日语 40+ 条目，未翻译的字符串保留英文=优雅降级)
- `guide` — 快速指南正文(Shift+F2)

算子帮助如果存在 `op_help/<name>.<lang>.html` 就会按语言显示。如实说明:
运行中变化的状态文字(`running…` / `PASS` 等)以及算子备注正文目前
不在翻译范围内(算子备注的英文化是与 docstring 双语化配套的未来课题)。

## Python 编辑器与 IDE 功能(2026-08-30)

Studio 已经超越了"只能从流水线调用代码"的阶段，也可以作为**Python 开发环境**使用。

- **Python Editor**(File ▸ Python Editor… / 图库中的"Open in editor"): 具备语法高亮+
  行号+自动缩进的**多标签**编辑器(与 HDevelop 的主脚本+子脚本类似，
  可同时编辑多个脚本)。**F5 / Run** 会在子进程中执行当前标签页(仓库会加入 PYTHONPATH，
  所以 `import fullseye` 可以直接使用。未保存的缓冲区会以临时副本方式运行，不强制 Save)。
  可从 **Samples ▾** 在新标签页中打开全部随附的可运行示例(以不带路径的方式打开，
  因此不会误覆盖出厂示例)。执行所用的解释器可在 System settings ▸ Editor 中更改。
- **MDI 代码窗口**(图库中的"Open in window"): 可以把示例代码作为独立窗口
  **随意排列多个**，方便选取片段复制(Window ▸ Tile/Cascade 同样有效)。
- **执行控制**: 在行号槽点击设置断点(=暂停执行)，用 **Continue** 按钮从当前执行行
  继续到下一个断点/末尾，在阶段上右键选择 **Run from here** 可从任意行重新开始
  (与 **Run to here** 相对)。
- **变量监视**: 可在 Variables 窗口注册任意表达式(如 `v.mean()` / `np.percentile(v, 99)` /
  `(v > 0.5).sum()`。`v`=选中的变量，`np`=numpy，`img`=输入)，每当选择或流水线发生变化时
  都会**自动重新求值**。求值失败的表达式会在该行显示 ⚠(面板不会崩溃)。在变量上
  **右键 ▸ Inspect in popup…** 可立即弹出按类型分类的检查结果+百分位数+数值预览。
  已知的限制(如实说明): 由于监视表达式在 GUI 线程中同步求值，**非常耗时的表达式**
  (如对巨大数组做全量扫描)会在此期间阻塞界面。较重的统计计算应简化表达式，
  或改在 Python Editor 中执行。
- **System settings**(Tools ▸ System settings… / Ctrl+,): 分类树+分页结构。
  Execution(线程数 / 超时)·Windows(窗口数上限)·Display(默认 LUT / region 绘制)·
  Editor(字体大小 / 执行解释器)。

## Export 与 Save/Open 的关系

在 Studio 中搭建的流水线可以用 3 种形式带走。

| 形式 | 导出方式 | 使用场景 |
|---|---|---|
| `--ops` 字符串 | Export（Ctrl+E） | 贴到 CLI 的 `imgevolve.py pipeline --ops "…"` / `run "…"` 中 |
| Python 函数 | Export（Ctrl+E） | 以 `fullseye.run_pipeline(...)` 的形式嵌入自己的代码 |
| JSON | Save pipeline（Ctrl+Shift+S） | 用 `FullseyeEngine.load(...)` / `imgevolve.py run pipeline.json` 执行 |

**设计在 Studio 中完成，执行由代码/CLI 负责**这种相当于 HDevelop→HDevEngine 的流程，是通过 JSON 完成的。接收 JSON 并执行的一方请参见 [ENGINE.md](ENGINE.md)。

---

## 相关文档

- [STUDIO_UX.md](STUDIO_UX.md) — 设计系统·UX 改进的意图与背景（设计视角）
- [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md) — 感知面板的内容（flow / stereo / terrain）
- [ENGINE.md](ENGINE.md) — 执行导出的流水线
- [GETTING_STARTED.md](GETTING_STARTED.md) — 5 分钟入门
