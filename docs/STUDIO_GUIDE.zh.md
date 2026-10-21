<!-- i18n-source-sha: 71c18c518f4c -->
# Fullseye Studio 完全指南

繁重处理不会冻结窗口。底部区域显示当前阶段和进度；停止请求会在下一个阶段边界得到确认。若运行期间设置发生变化，界面会标明显示结果的代次，并可选择查看旧设置的完成结果或用当前设置重新运行。

按处理目的搜索时，候选项会分为适用于当前输入、需要预处理和其他三组。候选项可在不添加处理阶段的情况下试运行一次。运行失败时，Problems 面板会显示原因、位置和下一步操作，可重新选择输入、并排比较、查看详细日志、编辑参数或搜索建议的处理阶段。

[日本語](./STUDIO_GUIDE.md) · [English](./STUDIO_GUIDE.en.md) · **简体中文** · [繁體中文](./STUDIO_GUIDE.tw.md) · [한국어](./STUDIO_GUIDE.ko.md) · [Deutsch](./STUDIO_GUIDE.de.md) · [हिन्दी](./STUDIO_GUIDE.hi.md)

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
从下拉菜单中选择 **25 个**现成配方（`recipes.py`）之一，流水线就会替换为该配方。例如"Edge — Sobel + Otsu""Denoise — bilateral + unsharp""Segment — blob / coin""Count — blobs""Texture — Gabor"等。是先跑起来再看内容的便捷起点。

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
| Image Viewer | `Ctrl+Shift+I` | Run a ledger op | `Ctrl+Shift+L` |
| Pipeline as code → editor | `Ctrl+Shift+E` | | |

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
**File ▸ Sample images**（共 16 张，来源见 `studio_assets/sample_images/manifest.json`。
合成图像 = 自制作品／`coins`·`camera` 等 = 来自 skimage.data 的 BSD/公有领域素材。可用
`tools/gen_sample_images.py` 重新生成）。其中 5 张是外观检测（FA）用的场景，不是照片，而是由照明与反射的
物理计算（`illumdesign`）和 PoC 的成像模型算出：拉丝金属上的划痕、树脂上的压痕与异物纤维、雕刻的批号、
背光下的开孔板、焊缝 X 光图像中的气孔。每张都附有缺陷的真值掩膜（`<名称>.truth.png`）与 manifest 中的说明，
各自对应一个“FA — ...”配方（测试确认它能找出缺陷），可用 `tools/gen_fa_samples.py` 重新生成。

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

## 可以拖放打开的文件(2026-10-03)

把文件或文件夹**拖放到主窗口**,就会在合适的窗口中打开(一次拖放多个文件会打开多个窗口)。完整列表见
**Help ▸ 可打开的文件(拖放)…**;那张表由 Studio 实际使用的扩展名常量生成,可能比本节更新。

| 拖放的内容 | 打开方式 | 说明 |
|---|---|---|
| 图像(png / jpg / tif / webp / pgm / pfm / jp2 …)、文件夹 | 图像查看器 | 列表、缩放、像素值、直方图、“用作流水线输入”。文件夹打开其中直接包含的图像 |
| `.py` | Python 编辑器(每个文件一个标签页) | |
| `.json` | 流水线 | |
| 点云与网格(PLY / STL / PCD / OBJ / OFF / XYZ) | 3-D 查看器 | **ASCII 与二进制皆可**(PLY 小端与大端,PCD 也支持 binary_compressed) |
| 3DGS(`.ply` / `.splat`) | 3-D 查看器 | 颜色取球谐 DC 项;不透明度 < 0.05 的被隐藏 |
| 医学体数据(NIfTI / NRRD / MHA / DICOM) | 3-D 查看器 | 需要 SimpleITK 等 |
| glTF(`.glb` / `.gltf`)、LiDAR(`.las` / `.laz`) | 3-D 查看器 | 需要 pygltflib / laspy |
| 机器人(MJCF / URDF) | 3-D 查看器 | `.xml` 仅当根元素为 `<mujoco>` 或 `<robot>`。需要 mujoco |
| 动作捕捉(`.bvh`)、神经元形态(`.swc`) | 3-D 查看器 | BVH 关节轨迹按时间着色 |
| 视频、动画 GIF、HDF5 | 视频立方体 | |
| 事件相机 (x, y, t, p)(txt / csv / npy / npz) | 视频立方体 | 按内容识别,转成带极性的帧 |
| `.npy` | 按形状 | 2-D → 输入图像,(N, 3 / 6) → 点云,3-D → 体数据 |
| Markdown、SVG | 文档查看器 | |
| 音频(wav / mp3 / flac / ogg …) | 音频窗口 | 波形、频谱图、播放。WAV 以外需要 soundfile |
| 机器人模型 + qpos `.npy` (T, nq) 一起 | 机器人回放 | 滑块与播放按钮 |

## 试运行任意台账 op(Tools ▸ 运行台账 op…,Ctrl+Shift+L)(2026-10-03)

用**与每个参数类型相符的输入框**运行类型化台账中的 op(PIV、数学、驾驶、3-D 等约 1,700 个)的窗口。
在左侧搜索框输入名称或词语,选中 op 后右侧会出现参数表单。

- **数据输入**可选"样本(合成)""当前图像""上一次结果"。样本是为该 op 合成、带真值的输入;"上一次结果"是
  **此窗口中最后运行的 op 的结果**,因此换选 op 就能把它传给下一个 op(例:用 `ode_vector_field_grid` 生成流场,
  再把 `piv_quiver` 的输入设为"上一次结果",即得箭头图)。类型不符的输入(把当前图像放进 flow2d 栏)不会运行,而是给出原因。
- **参数**:整数用整数框、实数用实数框、真假用复选框、有候选的用下拉、其余用文本行。空栏为默认值,写 `None` 即 None,
  序列写 `1, 2, 3`。矩阵或字典样本以 `<sample>` 标记保存。读不懂的值**不会悄悄换回默认值**,会说明是哪个参数、为什么。
- **运行**后以图和内容(形状、值域、字段)展示结果,并给出**做同样事情的一行 Python**("复制代码"可直接贴进脚本,相当于 MATLAB 的命令历史)。
- 勾选"**值改变时自动重新运行**"后,每次改值都会重新运行。
- **一键进编辑器**:"插入到编辑器"把窗口中的代码(包括重建样本、**原样即可运行的脚本**)放到 Python 编辑器的光标处
  (没有编辑器时会打开;import 只在文档顶部补上缺少的行)。"把历史作为脚本"按顺序汇总此窗口中所有成功的运行
  (用"上一次结果"串起的步骤会变成一串 `result = …`)。
- **也可以从编辑器出发**:在 Python 编辑器中于 `fs.ledger.` 或 `fs.` 之后输入会弹出名称候选(随时可按 Ctrl+Space)。
  选中台账 op 会插入**列出数据参数与必填参数的调用形式**,例如 `dem_slope(dem, cell_size=)`,光标停在第一个空位。
  在 op 名称上右键或按 Ctrl+Shift+L,即可打开该 op 的运行窗口。
- **命令面板(Ctrl+P)**:输入 `ledger: 名称`,三步(Ctrl+P → 名称 → Enter)即可打开任意台账 op 的窗口。
- **从正在看的结果出发**:在主画面的图像上右键 →"把流水线作为代码送到编辑器"(Ctrl+Shift+E,读取当前图像并运行的脚本)/"把此结果交给台账 op…"(运行窗口的图像输入已预选为当前结果)。

有些 op 用样本跑不起来(这是各 op 样本构造方式的限制;2026-10-03 实测 60 个中 27 个能直接用样本运行)。
窗口本身没有增加失败,由"与把样本直接传给 op 的结果一致"这道门来确认。

### 将 CSV 列分配给表格操作

类型输入为 `table` 时，可在现有台账运行器中选择 **CSV 文件…**。每个角色只能从实际列名中选择；量具 R&R 使用
`part / 零件 ID`、`operator / 操作者`、`value / 测量值`。检查会显示行数、唯一键、缺失值和重复数。重复数不等时，
会在运行前列出并拒绝相关组，绝不自动修补。映射按操作和表头签名保存，仅相同格式复用。CSV 不会被修改或改名。

### 结果视图的显示方式

| 结果 | 显示方式 |
|---|---|
| `flow2d` `(2, h, w)` | 色相 = 方向、亮度 = 速度的色轮图上叠加箭头图(最长箭头 = 间距的 0.9 倍) |
| 一维数列 | 折线(MATLAB 的 `plot(y)`) |
| 表(dict) | 等长的数值列叠成折线;若有 `t` / `x` / `freq` … 列则作横轴 |
| `(h, w, 4)` / `(h, w, 1)` / 复数 | 合成到白底的 RGB / 灰度 / 绝对值 \|z\| |
| 空数组、4 维以上 | 以文字给出形状和值域(不把第一个值当作"标量") |

## 结果缓存、需确认标记与输入图像引用(2026-10-19)

- **逐段结果缓存**:拖动旋钮时,只重新计算该段及其后的各段,前面的结果直接复用。每段行的右端,本次计算的段显示 `⟳ calc`,取自缓存的段显示 `↺ cache`。更换图像、调整顺序或删除某段时,从受影响的段起的缓存会被丢弃。每段只保留最新的一份结果,反复拖动旋钮也不会增长。
- **需确认标记(⚠)**:"是否运行成功(ran)"与"结果是否有效(valid)"分开记录。结果含 NaN / Inf、为空、或所有像素相同时,该段行会带 `⚠`,原因显示在提示和 Problems 中(与 `✕` 错误是不同的行)。若结果是带有 `converged` / `valid` / `ok` 等字段的表,则照录其申报。没有有效性信息的结果显示为"妥当性未判定",不会显示 OK。Run all 之后状态栏显示"运行:完成 / 结果:需确认(原因)"或"运行:完成 / 结果:未判定有效性"。Studio 只**报告**,不会修复 op 的数值问题,也不会改动任何值。
- **输入图像引用**:Save pipeline 会把已载入图像文件的引用(原样路径、文件 sha256、shape、dtype)写入 JSON 的 `input`。打开时,文件存在且 sha256 一致则静默重新载入;文件存在但内容已变,则载入并在 Problems 显示 "input file changed since save";找不到则保留当前图像,并显示 "input not found: 路径"(会尝试 `.json` 同目录下的同名文件作为重新链接的候选)。没有 `input` 的旧 JSON 与以前完全一样地读取。
- **阶段缩略图(2026-10-20)**: 每个阶段行左侧显示该阶段结果的小图(约 48×36 像素):区域为二值图,轮廓为线条,表或标量为表示其种类的符号。小图只由缓存中已有的结果生成,不会为了画图而重新计算阶段。尚未计算的阶段显示“未计算 / not computed”;之前算过但旋钮或图像已改变的阶段显示“再计算が必要 / recompute needed”,不会把旧图当作当前结果。每个阶段只保留一个很小的数组,因此大图像下内存几乎不增加。 重建列表本身不会计算任何阶段(只在运行、单步或旋钮拖动结束时计算)。 _(ja)_
- **阶段输入→输出面板(Window ▸ Panels ▸ Stage in → out)**: 选中某个阶段后,以相同的显示模式和数值范围并排显示它的输入和输出,下方一行给出差异:区域/标签结果为“区域数 128 → 37”,图像为平均值、σ、最小值、最大值的前后变化,表为行数和列数,轮廓为条数。面板关闭时不做任何计算。
- **旁路(Ctrl+B / 阶段右键菜单)**: 暂时关闭所选阶段而不删除它。该阶段原样传递输入,在列表中显示为灰色并带删除线。撤销记录显示为“bypass”,与“remove”不同。旁路作为阶段的第 4 个元素 `true` 保存在项目文件中(关闭时不写任何内容,所以不使用旁路的文件与以前逐字节相同);它是缓存键的一部分,因此切换后从该阶段起重新计算。Python 导出只保留 `# bypassed: op` 注释行,导出的脚本结果与画面一致。在 Program 文本中,旁路阶段是一行 `# bypassed: op (a, b)`,“Apply” 会把它读回来,标记因此得以保留。
- **相邻取值对比条(旋钮下方的 "Try nearby values")**: 把所选阶段在当前旋钮值上下相邻的 3 个(或 5 个)取值时的结果以小图并排显示。取值间隔取规格中的步长与取值范围的 1/10 中较大者(对数刻度规格则为等比);整数或选项型旋钮取相邻的值,且不会超出允许范围。只在展开时计算,并从上一阶段的缓存结果出发,**只运行该阶段**(每个候选运行一次,其他阶段不运行)。所有小图使用同一显示范围,只保存小图,因此大图像也几乎不增加内存。点击小图不会改变任何东西;点击所选小图下方的 "Adopt this value",才会沿与滑块相同的路径写入该值,撤销记录为一步(如 "change blur σ")。若在主图像上用 Shift + 拖动标出了区域(Shift + 单击取消),该条只绘制该区域。
- **固定 A、与 B 比较(工具栏 "Pin as A" / Ctrl+Shift+A,Window ▸ Panels ▸ A / B)**: 冻结阶段列表(含旁路标记)、输入引用、最终结果和显示设置。结果是一份只读副本,之后无论怎样运行都不会改变。最多保留两个,第三个会丢弃最旧的(状态栏会提示)。A / B 面板把 A 与实时结果 B 以并排、滑动(拖动分界线)、闪烁(默认 500 ms,关闭面板即停止)或差异(绝对值 / 带符号,0 为白色的对称色图 / 比值 log2)显示。A 与 B 使用由 A ∪ B 决定的同一显示范围。下方 "What changed" 依次列出相对 A 新增、删除、修改(旧值 → 新值,带单位)、旁路以及输入的变化。"Restore A" 恢复 A 的流水线(撤销算一步),"Adopt B" 丢弃 A,"Keep both" 把 B 固定为第二个快照。项目文件只在 `pinned` 中保存阶段、输入、显示和备注(不保存数组),打开时重新计算数组;若无法重新计算,固定仍保留,Problems 中显示 "cannot recompute A"。没有 `pinned` 的旧文件照常打开。
- **缩放、平移与光标同步**: "Stage in → out" 面板与 A / B 面板中的图像一起缩放、平移;光标移到其中一幅上时,其他幅的同一像素处显示十字线。在 A / B 面板勾选 "sync the main view too",主图像也加入同步。


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
- **验证导出的 Python（Run ▸ Verify exported Python / Ctrl+Shift+R）**：在隔离的 Python 进程中运行可编辑的导出代码，并逐阶段与 GUI 中间结果比较。可设置绝对、相对容差，以及 NaN 必须同位置、忽略或禁止。shape 和 dtype 始终必须一致。不一致会加入 Problems，并定位到首个不同阶段；Studio 只报告，不修改数值。
