# FullseyeEngine — 运行已设计管道的运行时

[日本語](./ENGINE.md) · [English](./ENGINE.en.md) · **简体中文** · [繁體中文](./ENGINE.tw.md) · [한국어](./ENGINE.ko.md) · [Deutsch](./ENGINE.de.md)

`FullseyeEngine`（`engine.py`）是一个运行时，用于**执行**在 Fullseye Studio 中**搭建**好的图像算子管道——无论是从自己的代码还是从 CLI 调用。它相当于 MVTec 的 **HDevEngine**——用可视化工具设计流程，再原封不动地从应用程序中调用，这正是两段式流程中后半段的角色。

- **设计（author）**：Fullseye Studio → `Save pipeline` 导出 JSON（[STUDIO_GUIDE.md](STUDIO_GUIDE.md)）。
- **执行（execute）**：`FullseyeEngine.load("pipeline.json").run(frame)` —— **输入 numpy 数组，输出 numpy 数组**。不需要文件 I/O，也不需要 GUI。

管道是由 `(op, a, b)` 组成的阶段列表。引擎可以从 Studio 的 JSON、`--ops` 字符串，或 Python 列表中加载，检查输入输出的 sort，调整每个阶段的旋钮，并对 numpy 帧执行（整体执行、执行到中途、或逐阶段执行）。它还会进行结构验证（未知算子、sort 不一致），这与 Studio 诊断面板中的检查完全相同。

---

## 最简用法

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # 各阶段的中间结果(列表)
```

`FullseyeEngine` 与 `diagnose_stages` 均从 `fullseye`（以及 `engine`）模块公开。

---

## 四种加载方式

| 构建方式 | 签名 | 用途 |
|---|---|---|
| JSON 文件 | `FullseyeEngine.load(path)` | 读取 Studio 的 `Save pipeline` 输出 |
| ops 字符串 | `FullseyeEngine.from_ops(ops, a=0.5, b=0.5, name="pipeline")` | 逗号分隔字符串，例如 `"gaussian,sobel_amp,otsu"`（共用旋钮） |
| dict | `FullseyeEngine.from_dict(d, name="pipeline")` | 从含 `{"stages": [...]}` 的字典构建 |
| 阶段列表 | `FullseyeEngine(stages=None, name="pipeline")` | 直接传入 `[("gaussian",0.4,0.5), "otsu"]`（仅给名称的阶段默认 a=b=0.5） |

若 `from_dict` 缺少 `"stages"` 键会抛出 `ValueError`。`load` 会读取 JSON 后传给 `from_dict`，并以文件名（不含扩展名）作为 `name`。

---

## 方法一览

| 方法 | 返回值 | 说明 |
|---|---|---|
| `load(path)` *(classmethod)* | `FullseyeEngine` | 从 Studio 的 JSON 加载 |
| `from_ops(ops, a=0.5, b=0.5, name=…)` *(classmethod)* | `FullseyeEngine` | 从逗号分隔的 ops 字符串加载(共用旋钮) |
| `from_dict(d, name=…)` *(classmethod)* | `FullseyeEngine` | 从 `{"stages": [...]}` 加载 |
| `describe()` | `list[dict]` | 每个阶段的 `{index, op, a, b, in_sort, out_sort, halcon, known}` |
| `op_names()` | `list[str]` | 各阶段的算子名称 |
| `input_sort()` | `str \| None` | 管道所期望的输入 sort(第一个已知 op 的 in_sort) |
| `output_sort()` | `str \| None` | 管道返回的输出 sort(最后一个已知 op 的 out_sort) |
| `validate()` | `list[dict]` | 结构性问题 `{index, op, severity, message}`。`[]` 表示健全 |
| `is_runnable()` | `bool` | 若所有阶段都能解析为已知算子(没有 error)则为 `True` |
| `get_knobs(i)` | `tuple` | 阶段 `i` 的旋钮 `(a, b)` |
| `set_knobs(i, a=None, b=None)` | `self` | 修改阶段 `i` 的旋钮(可链式调用) |
| `run(image, upto=None, coerce=True)` | ndarray / float / dict | 执行管道。`upto` 仅执行第 0..upto 阶段 |
| `run_stepwise(image, coerce=True)` | `list` | 每个阶段执行后的中间结果(长度 = 阶段数) |
| `run_file(in_path, out_path=None, upto=None)` | 原始结果 | 读取图像、执行，若为栅格结果则可选保存 |
| `to_dict()` | `dict` | `{"fullseye_pipeline": 1, "name", "stages"}` |
| `to_ops()` | `str` | 逗号分隔的 ops 字符串 |
| `to_python()` | `str` | 单个 Python 函数的源代码(与 Studio 的 Export 相同) |
| `save(path)` | `None` | 将 `to_dict()` 保存为 JSON |
| `len(eng)` | `int` | 阶段数 |

`diagnose_stages(stages)` 是一个不需要创建引擎即可验证阶段列表的函数，是 `validate()` 的实际实现。未知算子的 `severity` 为 `"error"`，相邻阶段 sort 不一致时为 `"warning"`。

### 关于 sort(类型)

每个算子都声明输入/输出的 **sort**：`image`(gray H×W float64 [0,1]) / `region`(二值 {0,1}) / `color`(H×W×3 RGB) / `feature`(标量 float) / `contour`(XLD dict) / `volume`(3D 堆栈) / `any`(可与任何类型连接)。当相邻阶段的 out→in 不匹配时，`validate()` 会给出警告(`any` 始终视为匹配)。

---

## Python 使用示例

### 先验证再执行

```python
import fullseye

eng = fullseye.FullseyeEngine.from_ops("gaussian,sobel_amp,otsu")
problems = eng.validate()
if not eng.is_runnable():                      # 存在 error(未知 op)时停止
    raise SystemExit(problems)
result = eng.run(frame)                         # 返回 region(二值)
```

### 执行到中途 / 逐阶段执行

```python
mid = eng.run(frame, upto=1)                    # 执行到第 0..1 阶段(gaussian → sobel_amp)
for i, s in enumerate(eng.run_stepwise(frame)):  # 各阶段的中间结果
    print(i, eng.stages[i][0], getattr(s, "shape", s))
```

### 调整旋钮后重新执行

```python
eng.set_knobs(0, a=0.3).set_knobs(2, a=0.4)     # 可链式调用
out = eng.run(frame)
```

### 文件输入输出(在代码内完成)

```python
eng = fullseye.FullseyeEngine.load("edge.json")
result = eng.run_file("in.png", "out.png")      # 读取 → 执行 → 若为栅格则保存
```

### 保存 / 导出

```python
eng.save("edge.json")                           # 保存为 JSON(可在 Studio 中重新打开)
print(eng.to_ops())                             # "gaussian,sobel_amp,otsu"
print(eng.to_python())                          # 输出为单个 Python 函数
```

`to_python()` 的输出示例：

```python
import fullseye, numpy as np

def pipeline(frame):
    return fullseye.run_pipeline(frame, [
        ('gaussian', 0.500, 0.500),
        ('sobel_amp', 0.500, 0.500),
        ('otsu', 0.500, 0.500),
    ])
```

---

## CLI: `imgevolve.py run`

可以从 CLI 执行已保存的管道(JSON 或 ops 字符串)。其内部使用 `FullseyeEngine`。

```
py -3.11 imgevolve.py run <pipeline.json|ops> [inp] [--out PATH]
                          [--upto N] [--stepwise] [--describe] [--to-python] [--a A] [--b B]
```

| 参数 / 选项 | 含义 |
|---|---|
| `pipeline` | 管道 `.json`(Studio 的 Save pipeline)或逗号分隔的 ops 字符串 |
| `inp` | 输入图像(省略时仅可执行 `--describe` / `--to-python`) |
| `--out PATH` | 结果的保存路径(仅保存栅格结果) |
| `--upto N` | 执行到第 0..N 阶段 |
| `--stepwise` | 报告每个阶段的结果，若指定 `--out` 则保存为 `PATH_00`、`PATH_01`、… |
| `--describe` | 显示管道的输入输出、各阶段及验证结果(未提供输入图像时仅显示后结束) |
| `--to-python` | 将管道输出为 Python 函数 |
| `--a` / `--b` | 以 ops 字符串构建时的共用旋钮(默认 0.5) |

示例：

```powershell
# 仅确认结构(无需图像)
py -3.11 imgevolve.py run edge.json --describe
#   pipeline 'edge': image -> region
#     0. gaussian      a=0.50 b=0.50   [image -> image]
#     1. sobel_amp     a=0.50 b=0.50   [image -> image]
#     2. otsu          a=0.50 b=0.50   [image -> region]

py -3.11 imgevolve.py run edge.json in.png --out result.png       # 执行并保存
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png  # 保存每个阶段
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python   # ops 字符串 → Python
```

包含未知算子(error)的管道可以用 `--describe` 显示，但执行时会停止并报告问题。

---

## 从其他项目调用(onocollo / evis / hillco 等)

由于 `fullseye` 的输入输出完全基于 numpy 数组，可以直接嵌入机器人/视觉管道中。这样就能实现 **设计在 Studio、执行在各项目** 的分工。

```python
import fullseye

# 在启动时加载一次即可(轻量。仅保存 ops 的解析结果和旋钮)
PIPELINE = fullseye.FullseyeEngine.load("assets/segment.json")

def perceive(frame):                            # frame: 自行准备的 float64 gray [0,1]
    seg = PIPELINE.run(frame)                   # 输入 numpy，输出 numpy(不需要磁盘)
    return seg
```

要点：

- **无需文件 I/O**：可以直接传入从传感器/仿真器获取的 numpy 帧，并直接接收 numpy 结果。在嵌入式或 GPU 仿真环境中，即使没有 I/O 后端也能运行。
- **轻量**：`load` / `from_ops` 只保存算子名称和旋钮。繁重的计算只在调用 `run` 时才会发生。
- **版本无关**：由于管道 JSON 是数据，替换管道不会影响调用方代码。研究中的反复迭代(在 Studio 中调整管道 → 更新 JSON)不会波及使用方。
- **如果只需单个算子**，可直接调用 `fullseye.apply(frame, "otsu")`；若为多阶段，可直接调用 `fullseye.run_pipeline(frame, [...])`(不经过引擎的轻量路径)。

感知栈(stereo / terrain / flow / detect / registration / pose)同样基于 numpy 运行(如 `fullseye.disparity_map`)。使用示例请参见 `examples/`([../examples/README.md](../examples/README.md))以及 [PERCEPTION.md](PERCEPTION.md) / [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md)。

---

## 相关文档

- [STUDIO_GUIDE.md](STUDIO_GUIDE.md) —— 搭建管道并导出 JSON
- [GETTING_STARTED.md](GETTING_STARTED.md) —— 5 分钟快速上手
- [INSTALL.md](INSTALL.md) —— 环境搭建(包括嵌入式与最小配置)
