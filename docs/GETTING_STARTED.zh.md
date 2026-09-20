<!-- i18n-source-sha: c70ba3c329f3 -->
# 快速上手（5 分钟运行起来）

[日本語](./GETTING_STARTED.md) · [English](./GETTING_STARTED.en.md) · **简体中文** · [繁體中文](./GETTING_STARTED.tw.md) · [한국어](./GETTING_STARTED.ko.md) · [Deutsch](./GETTING_STARTED.de.md)

## 哪个入口适合你的工作(3 个入口)

Fullseye 的范围很广，如果不能先决定"第一个要打开哪一个"，就会卡住。这里列出的
不是新写的演示，而是**关卡(gate)每次都会执行的示例**(一旦失败 CI 就会变红)。

| 入口 | 面向 | 5 分钟:先跑起来 | 30 分钟:深入内部 | 半天:用自己的数据 |
|---|---|---|---|---|
| **可解释的外观检查** | 检测·质量保证 | `py -3.11 examples/poc_solder_fillet_aoi.py` 焊点(fillet)AOI | `py -3.11 examples/poc_fabric_defect.py` 把漏检和误检分开计数 | [CAPABILITIES.md](CAPABILITIES.md) 的"发现"→ 在 Studio 中用自己的图像 |
| **面向机器人的 3-D** | 机器人·3-D 测量 | `py -3.11 examples/perception_pipeline.py` 立体→深度→点云→可通行性 | `py -3.11 examples/grasp_pose.py` 将点云与模型对齐得到 6-DoF 姿态和抓取方向 | [EXAMPLES_3D.md](EXAMPLES_3D.md) → 输入自己的点云/网格 |
| **基于物理的无损检测** | X 射线·光学·计量 | `py -3.11 examples/ct_reconstruction.py` 投影→重建→尺寸(mm)和缺陷数 | `py -3.11 examples/poc_ct_void_morphology.py` 为什么"合格/不合格"这一个数字对形状是盲目的 | [CAPABILITIES.md](CAPABILITIES.md) 的"成形"→ 用自己的体数据 |

每个示例都有**真值**(闭式解或合成数据)。总会并列给出零点(什么都不做时)的结果，
所以你可以自行判断是否真的"起作用了"。目前验证到什么程度的台账在
[MATURITY.md](MATURITY.md) —— 这不是手写的，而是从实际运行的关卡和真实数据的有无中统计出来的。

---

这是让 Fullseye(内部代号 imgevolve)以最短路径跑起来的指南。按照**安装 → 搭建第一个流水线 → 执行 → 查看结果**的顺序，走一条不会卡住的路线。更详细的环境搭建见 [INSTALL.md](INSTALL.md)，Studio 的全部功能见 [STUDIO_GUIDE.md](STUDIO_GUIDE.md)，从代码调用见 [ENGINE.md](ENGINE.md)。

Fullseye 是一个**以 numpy 数组为输入输出的图像处理算子库**，在其上搭载了 **类似 HDevelop 的可视化流水线设计环境（Fullseye Studio）** 和 **执行运行时（FullseyeEngine）**。用 HALCON/HDevelop 的说法来讲，就是"在 HDevelop 中搭建流程，在 HDevEngine 中从自己的应用调用"这种两段式结构，原样用 Python + numpy 重现了出来。

---

## 1. 安装（1 分钟）

前提: **Python 3.11**（Windows 用 `py -3.11`，Linux 用 `python3.11`）。

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .          # 仅核心（numpy + scipy。所有 op 都可见，需要 optional backend 的 op 调用时会指出缺少的 extra）
```

核心**只靠 numpy 和 scipy** 就能运行。OpenCV / scikit-image / Pillow 等额外后端都是可选的，即使没有安装，也只是该后端特有的算子被禁用而已（优雅降级）。实际使用中至少需要 OpenCV 或 Pillow 来读写图像文件，所以建议追加安装以下之一。

```powershell
py -3.11 -m pip install -e ".[opencv]"    # 图像 I/O + 来自 OpenCV 的算子
py -3.11 -m pip install -e ".[all]"       # 全部后端（opencv, skimage, pil, wavelets, gpu, extra）
py -3.11 -m pip install -e ".[gui]"       # 如果要用 Fullseye Studio（PySide6）
```

extras 的清单和含义汇总在 [INSTALL.md](INSTALL.md)。要用 GUI 需要 `[gui]`（或 `[all]` + `[gui]`）。

> 也可以不安装就试用。把仓库根目录（`<path-to-fullseye>`）设为工作目录，并把该路径加入环境变量 `PYTHONPATH`，`import fullseye` 就能工作。不过 `fullseye` / `fullseye-studio` 这两个命令（控制台脚本）只有执行了 `pip install -e .` 之后才能使用。

---

## 2. 先运行 1 个算子（Python）

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

edges = fullseye.apply(frame, "sobel_amp")     # image → image（梯度强度）
seg   = fullseye.apply(frame, "otsu")          # image → region（0/1 二值）
n     = fullseye.apply(seg,   "count_obj")     # region → feature（对象数＝Python float）
print(n)                                       # 例如: 316.0
```

> **参数顺序是 `apply(image, name, a, b)`** — 第 1 个参数是数组，第 2 个参数是算子名。反过来传的话，
> 从 0.1.9 起会以 `TypeError: ... arguments look swapped` 停止（0.1.8 及以前会出现 numpy 的
> "truth value of an array is ambiguous" 这种无关的错误）。
> `a`/`b` 必须是 0..1 之间的有限值。字符串·`None`·NaN 会立即触发 `TypeError`/`ValueError`，超出范围的值会被截断并记录到台账中。

- `apply(image, name, a=0.5, b=0.5)` 用于应用**单个算子**。`name` 既可以是**算子名**（例如 `gaussian`），也可以是**HALCON 别名**（例如 `gauss_filter`），都能被解析。
- `a`、`b` 是每个算子拥有的 **2 个旋钮（0.0～1.0）**。含义因算子而异（半径、阈值、σ 等）。
- 输出的类型（sort）由算子决定: `image`（灰度）/ `region`（二值）/ `feature`（标量 float）/ `color`（RGB）/ `contour`（XLD）/ `volume`（3D）。
- **失败时会怎样**（自 2026-09-03 起）: 默认 `on_error="fallback"` 下，即使算子内部失败，也会返回与类型相符的无害值（例如图像会返回输入的副本），并且**每个算子只会弹出一次** `FullseyeFallbackWarning`。什么发生了多少次回退，可以用 `fullseye.fallbacks()` / `fullseye.fallback_counts()` 确认。传入 `on_error="raise"`（或设置环境变量 `FULLSEYE_ON_ERROR=raise`）则变为**fail-closed**，算子真正的异常、dtype 违约（整数/bool 图像）、GPU 内核失败都会原样抛出。**sort 不一致只会被部分检测到**（例如把 RGB `(H,W,3)` 传给一个 2-D 算子会被当作体数据处理，即使在 `raise` 模式下也不会报错 —— 见 `docs/KNOWN_ISSUES.md` #32-4）。在 CI 或验证中建议使用 `raise`。
- **多输入算子**（`add_image` / `union2` 等，在 `list_ops()` 中 `tier == "nary"`）需要**以列表形式**传入输入: `fullseye.apply([img1, img2], "add_image")`。
- **模板匹配**（`ncc_locate` / `shape_locate`）通过 `template=` 传入要查找的图像: `corr, row, col = fullseye.apply(img, "ncc_locate", template=patch)`（返回的 row/col 是匹配位置的**中心**）。没有模板时会返回 no-match 的 `[0, 0, 0]`。

可以用下面的方式查找有哪些算子。

```python
fullseye.op_names()                 # 全部注册的算子名（860 个，截至 2026-09-03）
fullseye.list_ops(search="edge")    # 按名称 / HALCON 名 / 分类做部分匹配搜索
fullseye.list_ops(sort="region")    # 按输入 sort 筛选
fullseye.categories()               # 47 个分类
```

---

## 3. 搭建流水线（串联多个算子）

把多个算子依次串联起来就是"流水线"。数组会依次穿过每一段并返回最终结果。

```python
# 所有阶段共用同一组 a, b（与 CLI 相同的形式）
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])

# 每个阶段想用不同旋钮时（用 (name, a, b) 元组指定）
out = fullseye.run_pipeline(frame, [("gaussian", 0.3, 0.5), ("otsu", 0.4, 0.5)])
```

这是"smooth（平滑）→ 边缘强度 → Otsu 二值化"，从图像生成二值边缘图的典型例子。系统内置了 **20 个**可以直接使用的组合(配方)。

```python
import recipes
recipes.names()                                   # 配方名称一览
stages = recipes.stages("Edge — Sobel + Otsu")    # [(op, a, b), ...]
out = fullseye.run_pipeline(frame, stages)
```

---

## 4. 可视化搭建（Fullseye Studio）

不用写代码，搜索并排列算子，用滑块调节旋钮，一段一段执行并实时查看中间结果来搭建流水线。需要 GUI extras（`pip install -e ".[gui]"` = PySide6）。

```powershell
py -3.11 studio.py          # 或者已安装的话: fullseye-studio
```

由 3 个面板构成。

- **左侧（Operators）**: 按分类 / 搜索缩小算子范围，**双击插入**（Edit ▸ Focus operator search = **Ctrl+F** 定位到搜索框）。示例流水线也可以从这里加载。**Insert（＋）与 HDevelop 的算子窗口相同**，在流水线中添加一段的同时，会在 Program 窗口的光标位置写入一行 `op (a, b)`（数值为 `repr` 的全精度。如果 Program 中有尚未应用的手动编辑，只插入这一行，需要 Apply 才会生效）。
- **中央（Pipeline）**: 已排列阶段的列表。可拖动或用 Ctrl+↑/↓ 调整顺序，调节选中阶段的**旋钮 a / b**。旋钮始终是 0..1 的值，但**对于有专用显示规格的算子（`param_specs.py`）可以按真实单位操作** — `gaussian` 用 σ（px，滑块 + 带单位的数值输入），`median` 用 3/5/7/9 的下拉框选核大小，`reg_erode` 用整数输入指定迭代次数，`aug_barrel` 的 b 用"pincushion"复选框表示。右端的 0..1 数值输入始终是原始值（供精确输入）。这些规格是根据 ops.py 中的换算公式（如 `0.3 + 2.7·a`）手写的，并通过测试与实现进行核对（`tests/test_studio_params.py`）。没有规格的算子仍然是原来的 2 个 0..1 滑块。阶段列表也会用显示单位书写（`gaussian (blur σ=1.08 px, b=–)`）。**Reset（Home）→ Step（Ctrl+→）→ Run all（Ctrl+Enter）**可以逐段执行，也可以一次性执行。
- **右侧（Image / Perception / Analysis）**: 缩放/平移显示结果图像、直方图、Inspector（检查 image / region / feature 的值）、v14 的感知面板（光流 / 立体深度等）。**在图像视图上右键**可以 Fit / 1:1 / Zoom / Save result / Save view as shown / Copy / Display mode / 3D surface（与菜单相同的操作）。另外打开的图形窗口也带有 Fit·1:1·±·Save 的小工具条和同样的右键菜单，3-D 查看器（Ctrl+4）可通过右键 Reset view / 切换第一人称(透视) / Wireframe / Save screenshot。

搭建好的流水线可以用 **Export（Ctrl+E）** 导出为 `--ops` 字符串或 Python 代码，也可以用 **Save pipeline（Ctrl+Shift+S）** 保存为 JSON。全部功能和快捷键见 [STUDIO_GUIDE.md](STUDIO_GUIDE.md)，应用内按 **F1** 即可显示一览。

---

## 5. 执行已保存的流水线（CLI / 代码）

在 Studio 中 `Save pipeline` 得到的 JSON(或 `--ops` 字符串)，可以原样对文件执行。这就是相当于 HDevEngine 的"无需重写设计好的内容即可执行"的路径。

```powershell
# 检查保存的 JSON 的 I/O 和各阶段（不用图像，只做结构检查）
py -3.11 imgevolve.py run edge.json --describe

# 应用到图像并保存结果
py -3.11 imgevolve.py run edge.json in.png --out result.png

# 逐段保存结果（result_00.png, result_01.png, ...）
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png

# 把流水线导出为独立的 Python 函数
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python
```

从代码执行时使用 `FullseyeEngine`（详见 [ENGINE.md](ENGINE.md)）。

```python
import fullseye
eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # 各阶段的中间结果（列表）
```

---

## 6. 用 CLI 逐个应用

想直接处理图像文件时用 CLI 更方便（图像 I/O 需要 OpenCV 或 Pillow）。

```powershell
py -3.11 imgevolve.py ops --search edge                    # 搜索算子
py -3.11 imgevolve.py has gauss_filter                      # 该 HALCON 名是否已实现 + 调用方式
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py pipeline in.png out.png --ops "gaussian,sobel_amp,otsu"
```

`apply` / `pipeline` 在各阶段共用相同的 `--a` / `--b`。想在每个阶段使用不同旋钮时，请使用上面的 `run_pipeline`（Python）或 Studio。

---

## 遇到问题时

| 症状 | 处理方法 |
|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | 执行 `pip install -e .`，或把仓库根目录加入 `PYTHONPATH` |
| 没有 `fullseye` / `fullseye-studio` 命令 | 控制台脚本是通过 `pip install -e .` 注册的。未安装时用 `py -3.11 imgevolve.py ...` / `py -3.11 studio.py` |
| Studio 无法启动 | 未安装 GUI extras。`pip install -e ".[gui]"`（PySide6） |
| `apply` / `pipeline` 报 `cannot read ...` | 需要为图像 I/O 安装 OpenCV（`[opencv]`）或 Pillow（`[pil]`） |
| 额外后端的算子显示为"unknown" | 该后端未安装。追加 `.[skimage]` `.[wavelets]` `.[extra]` 等 |

更详细的故障排查请参见 [INSTALL.md](INSTALL.md)。

## 接下来阅读

- **[INSTALL.md](INSTALL.md)** — 环境搭建完全指南（extras 的使用区分、Windows/Linux 安装器、最小配置·嵌入）
- **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** — Fullseye Studio 完全指南
- **[ENGINE.md](ENGINE.md)** — FullseyeEngine（设计 → 执行）指南
- **[README.md](README.md)** — 文档索引
