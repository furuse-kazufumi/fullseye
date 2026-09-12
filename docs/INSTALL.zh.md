# 安装 / 环境搭建完全指南

[日本語](./INSTALL.md) · [English](./INSTALL.en.md) · **简体中文** · [繁體中文](./INSTALL.tw.md) · [한국어](./INSTALL.ko.md) · [Deutsch](./INSTALL.de.md)

面向从开发机到嵌入式 Linux、按用途搭建 Fullseye(工作代号 imgevolve)的指南。若只想在 5 分钟内跑起来，[GETTING_STARTED.md](GETTING_STARTED.md) 是更快的路径。

Fullseye 的设计方针是 **「仅靠 numpy + scipy 就能运行的核心」+「所有重量级依赖均为可选」**。即使没有额外后端，也只是该后端专属的算子被禁用，核心始终可用(优雅降级)。

---

## (a) 前提条件

| 项目 | 要求 |
|---|---|
| Python | **3.11**(`pyproject.toml` 中 `requires-python = ">=3.10"`；开发与验证使用 3.11) |
| 执行命令 | Windows: `py -3.11` / Linux: `python3.11` |
| 核心依赖 | `numpy>=1.23`, `scipy>=1.9`(`pip install -e .` 会自动安装) |
| 操作系统 | Windows 10/11、Linux(含嵌入式)。只要 Python 能运行，macOS 也可以 |

---

## (b) pip install(extras 的含义与用法)

在仓库根目录下进行可编辑安装(editable install)。

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .            # 仅核心(numpy + scipy，约 885 个算子)
```

额外的后端通过 **extras** 来选择(实体定义在 `pyproject.toml` 的 `[project.optional-dependencies]` 中)。

| extras | 追加的依赖 | 启用的内容 |
|---|---|---|
| `opencv` | `opencv-python>=4.6` | 图像文件 I/O(`apply`/`pipeline` CLI 必需)、`cv_*` 系列算子 |
| `skimage` | `scikit-image>=0.20` | `sk_*` / `xsk_*` 系列(众多自动生成算子的基础) |
| `pil` | `Pillow>=9` | 图像 I/O 的备用方案、`xpil_*` 系列(emboss/posterize/solarize 等) |
| `wavelets` | `PyWavelets>=1.4` | 小波系列(VisuShrink/子带/小波包等) |
| `gpu` | `torch>=2.0`, `kornia>=0.7` | GPU 批处理后端(`accel.py`/`bench.py`)、`xkor_*`(kornia)系列 |
| `extra` | `mahotas>=1.4`, `SimpleITK>=2.2` | `xsitk_*`(curvature flow 等)、源自 mahotas(Zernike/pftas 等) |
| `gui` | `PySide6>=6.5` | **Fullseye Studio**(`studio.py` / `fullseye-studio`) |
| `all` | 以上除 GUI 外的全部(opencv, skimage, pil, wavelets, gpu, extra) | 全部算子与后端 |

使用建议：

```powershell
# 实务中常用的最小配置 + 图像 I/O(不需要 GUI，以代码/CLI 为主)
py -3.11 -m pip install -e ".[opencv]"

# 也要使用 GUI(Studio)
py -3.11 -m pip install -e ".[opencv,gui]"

# 全套装备(含 GUI。all 不包含 GUI，因此需另外加上 gui)
py -3.11 -m pip install -e ".[all,gui]"

# 也想尝试 GPU 批处理路径(需要支持 CUDA 的 torch)
py -3.11 -m pip install -e ".[gpu]"
```

> `all` **不包含 `gui`**(GUI 用途不同，单独划分)。若要使用 Studio，请务必明确加上 `gui`。

安装成功后，以下 **两个控制台脚本** 即可使用(`[project.scripts]`)。

| 命令 | 实体 | 对应的直接执行方式 |
|---|---|---|
| `fullseye` | `imgevolve:main`(CLI) | `py -3.11 imgevolve.py ...` |
| `fullseye-studio` | `studio:main`(GUI) | `py -3.11 studio.py` |

若不安装也想尝试，只需将仓库根目录加入 `PYTHONPATH`，`import fullseye` 即可运行(但无法使用控制台脚本)。

```powershell
$env:PYTHONPATH = "<path-to-fullseye>"
py -3.11 -c "import fullseye; print(fullseye.version())"      # 0.1.0
```

---

## (c) Windows 安装程序

运行 `install\install.ps1` 可一次性完成环境搭建与桌面集成(PowerShell)。

```powershell
cd <path-to-fullseye>
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

运行该安装程序后，大致会执行以下操作。

- 确认 Python 3.11 是否存在
- 通过 `pip install -e .`(含所需 extras)安装 Fullseye
- **创建 Fullseye Studio 快捷方式(`Fullseye Studio.lnk`)** — 通过 `pyw.exe` 注册，以便不弹出控制台窗口即可启动，并附带 `assets\fullseye.ico` 图标

此后可从开始菜单/桌面快捷方式启动 Studio。

> 若因执行策略而被阻止，请加上 `-ExecutionPolicy Bypass`(已包含在上述命令中)。

---

## (d) Linux 安装脚本 + `.desktop` 启动器

运行 `install/install.sh` 可在 Linux 环境中完成同等搭建。

```bash
cd /path/to/imgevolve
bash install/install.sh
```

运行该脚本后，大致会执行以下操作。

- 确认 `python3.11` 是否存在
- `pip install -e .`(含所需 extras)
- **创建 `.desktop` 启动器** — 注册以 `assets/fullseye.ico` 为图标的桌面条目，以便从应用程序菜单启动 Fullseye Studio

此后可从桌面环境的应用列表启动 Studio。

---

## (e) 最小配置 / 嵌入式(embedded Linux)

Fullseye 的核心被设计为 **仅靠 numpy + scipy** 即可运行。对于不需要 GUI、GPU、重量级后端的嵌入式用途，只安装核心即可。

```bash
python3.11 -m pip install -e .        # 仅 numpy + scipy。不需要 GUI/torch/opencv
```

嵌入式用法要点：

- **输入输出完全通过 numpy 数组完成**。无需任何文件 I/O，可直接传入从传感器/相机获取的 numpy 帧。

  ```python
  import fullseye, numpy as np
  frame = get_camera_frame()                       # 自行获取的 float64 gray [0,1]
  seg = fullseye.apply(frame, "otsu")              # 不需要写入磁盘
  out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
  ```

- **需要文件 I/O 时**(`fullseye.load` / `fullseye.save`、`imgevolve.py run`、examples)，只要具备 **OpenCV 或 Pillow 其中之一** 即可运行(`imgio` 会自动进行回退)。若嵌入式场景优先考虑轻量，Pillow(`[pil]`)体积更小。
- 可以实现 **设计在开发机、执行在嵌入式机** 的分工。在开发机的 Studio 中搭建管道并导出 JSON，嵌入式机上只需 `FullseyeEngine.load("pipeline.json").run(frame)` 即可执行(不需要 GUI)。详情参见 [ENGINE.md](ENGINE.md)。
- **感知栈**(stereo / terrain / flow / detect / registration / pose)同样仅靠 numpy + scipy 运行(如 `fullseye.disparity_map`)。在机器人/视觉用途中无需额外依赖即可使用。

> GPU(`torch`)终究只是 **批处理加速的可选项**。嵌入式的单张图像处理不需要它，即使不安装，所有算子也都能在 CPU 上运行。

---

## (f) 常见问题

| 症状 | 原因 | 处理方法 |
|---|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | 未安装 / 路径未设置 | 执行 `pip install -e .`，或将仓库根目录加入 `PYTHONPATH` |
| 找不到 `fullseye` / `fullseye-studio` 命令 | 控制台脚本未注册 | 执行 `pip install -e .`。若不安装，可用 `py -3.11 imgevolve.py` / `py -3.11 studio.py` |
| Studio 启动时出现 PySide6 的 ImportError | 未安装 GUI extras | `pip install -e ".[gui]"` |
| `apply` / `pipeline` 出现 `cannot read <path>` | 没有图像 I/O 后端 | `pip install -e ".[opencv]"`(或 `[pil]`) |
| `read_image` / `write_image`(API)出现 cv2 的 ImportError | 这两者 **专属于 OpenCV** | `pip install -e ".[opencv]"`。若只想用 Pillow，请改用 `fullseye.load` / `fullseye.save` |
| `list_ops` 中缺少预期的算子 / `has` 显示 unknown | 对应后端未安装 | 添加相应的 extras(`skimage`/`wavelets`/`extra` 等) |
| GPU 批处理(`accel`/`bench`)在 CPU 上很慢 | `torch` 是 CPU 版本 | GPU 上使用 `--device cuda`。CPU 上简单的逐点运算因转换成本而处于劣势(属设计如此) |
| Studio 的 3D surface 无法打开 | 缺少 `QtDataVisualization` | 属尽力而为(best-effort)功能。依赖 PySide6 的版本/构成，缺失时会静默跳过 |

### 图像 I/O 的依赖关系(重要)

文件读写所需的后端因路径而异。

| 路径 | 所需后端 |
|---|---|
| `fullseye.load` / `fullseye.save`(= `imgio`)、`imgevolve.py run`、examples | **OpenCV 或 Pillow**(任一即可 / 自动回退) |
| `imgevolve.py apply` / `pipeline` | **必须使用 OpenCV** |
| `fullseye.read_image` / `fullseye.write_image`(API) | **必须使用 OpenCV** |

直接传入 numpy 数组的 `apply` / `run_pipeline` / `FullseyeEngine.run`，**完全不需要任何图像 I/O 后端**(仅靠核心的 numpy + scipy 即可运行)。

---

## 运行确认

```powershell
py -3.11 imgevolve.py coverage        # 诚实的覆盖数(979/2313 个 HALCON op 已作真实实现)
py -3.11 imgevolve.py ops --search edge
py -3.11 -c "import fullseye; print(fullseye.version(), len(fullseye.op_names()), 'ops')"
```

`fullseye.version()` 为 `0.1.0`，`op_names()` 返回 860 个注册算子(截至 2026-09-03)。
