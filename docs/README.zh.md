# Fullseye 文档索引

**Language:** [日本語](README.md) · [English](README.en.md) · [简体中文](README.zh.md) · [繁體中文](README.tw.md) · [한국어](README.ko.md) · [Deutsch](README.de.md)

> **请注意：**目前只有本索引页有译文，它所链接的各篇文档暂时仅有日文版。

**Fullseye**（工作代号 imgevolve）是一套 HALCON/HDevelop 级别的实用工具：由 numpy 原生的图像处理算子库、HDevelop 风格的可视化流水线设计环境（Fullseye Studio）以及执行运行时（FullseyeEngine）三者组成。算子约 **885** 个（以注册表计数），其中 **979/2313** 个真实 HALCON 算子做到了 genuine（真正等效）实现，覆盖 47 个类别。

> **先从这里开始 → [GETTING_STARTED.md](GETTING_STARTED.md)（5 分钟跑起来）**

---

## 用法（面向使用者 —— 先看这四篇）

| 文档 | 内容 |
|---|---|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | 5 分钟上手：安装 → 第一条流水线 → 在 Studio／CLI／代码中运行 → 查看结果 |
| **[INSTALL.md](INSTALL.md)** | 环境搭建完整指南：前置条件、`pip install -e .` 与各 extras 的取舍、Windows／Linux 安装器、最小配置与嵌入式集成、疑难排查 |
| **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** | Fullseye Studio 完整指南：三面板、算子浏览器、单步执行、参数旋钮、Inspector、感知面板、命令面板、快捷键、导出 |
| **[ENGINE.md](ENGINE.md)** | FullseyeEngine（设计 → 执行）：全部方法、在 Python 中的用法、CLI `run`、从其他项目中调用 |

---

## 算子 / API 参考

| 文档 | 内容 |
|---|---|
| [OPERATORS.md](OPERATORS.md) | 全部 521 个算子的目录（31 个类别，按 sort 分组，并列出 HALCON／OpenCV／scikit-image／MATLAB 的对应 API） |
| [EXAMPLES.md](EXAMPLES.md) | 逐个算子的示例代码（附其他库中的等价调用） |
| [OP_INDEX.json](OP_INDEX.json) | 机器可读的算子索引（用 `imgevolve.py index` 重新生成） |
| [ADDING_OPS.md](ADDING_OPS.md) | 如何新增算子（演化、codegen、目录与索引都会自动跟进） |
| [../examples/README.md](../examples/README.md) | 可直接运行的端到端示例脚本集 |

## 感知栈（机器人 / 视觉）

| 文档 | 内容 |
|---|---|
| [PERCEPTION.md](PERCEPTION.md) | 感知栈单页速查（stereo／terrain／detect／registration／pose／flow／motion） |
| [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) | 在实拍视频片段上的测量结果（视频 I/O ＋ 诚实给出的实测数值） |

## HALCON 对等性 / 覆盖率（诚实披露 honest disclosure）

| 文档 | 内容 |
|---|---|
| [HALCON_PARITY.md](HALCON_PARITY.md) | genuine（真正等效）实现的进展（979/2313）：不是“只有名字相同”，而是确实能做同样的处理 |
| [HALCON_COVERAGE.md](HALCON_COVERAGE.md) | 通过真实抓取官方参考手册（v2605）得到的覆盖率测量 |
| [LIB_COVERAGE.md](LIB_COVERAGE.md) | 跨多个库的覆盖情况（吸收 HALCON 之外具有特色的算子） |
| [PARITY_CROSSBACKEND.md](PARITY_CROSSBACKEND.md) | 以多个独立实现（scipy／cv2／skimage）之间的跨后端一致性来证明对等性 |

## 质量 / 溯源 / 复现

| 文档 | 内容 |
|---|---|
| [ACCURACY_BENCH.md](ACCURACY_BENCH.md) | 常设精度表：演化得到的 champion 对比 null 基线（holdout） |
| [CHAIN_FUZZ.md](CHAIN_FUZZ.md) | 链式 fuzzer——把算子串成链条施加扰动的第三层质量保障（扩散 → 收敛 → 最小复现） |
| [EVOLUTION_ENVIRONMENT.md](EVOLUTION_ENVIRONMENT.md) | 演化式算法开发环境（扩散 → 收缩 → 晋级；counterfactual utility 闸门，以及连接两个算子宇宙的桥） |
| [PROVENANCE.md](PROVENANCE.md) | 溯源：说明这些实现都是依据公开算法自行编写而成 |
| [REFERENCES.md](REFERENCES.md) | 每个算子的文献依据 |
| [REPRODUCE.md](REPRODUCE.md) | 数值复现步骤：由 seed 驱动、结果确定 |
| [STATUS.md](STATUS.md) | 项目当前所处的位置与后续计划（plan_ref） |

## 发行说明 / 设计

| 文档 | 内容 |
|---|---|
| [V13.md](V13.md) | v13 ＝ 走向实用 ＋ 跨项目 packaging ＋ 感知栈 |
| [V14.md](V14.md) | v14 ＝ 感知栈完成（运动 ＋ 健壮化） |
| [STUDIO_UX.md](STUDIO_UX.md) | Fullseye Studio 在 UX／设计上的改进意图与来龙去脉 |

---

## 快捷命令

```powershell
py -3.11 -m pip install -e ".[opencv,gui]"     # 安装（图像 I/O + Studio）
py -3.11 studio.py                              # 启动 Fullseye Studio（= fullseye-studio）
py -3.11 imgevolve.py ops --search edge         # 搜索算子（= fullseye ops --search edge）
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py run pipeline.json in.png --out result.png
py -3.11 imgevolve.py coverage                  # 诚实的覆盖数字
```

在 Python 中：

```python
import fullseye, numpy as np
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
eng = fullseye.FullseyeEngine.load("pipeline.json"); result = eng.run(frame)
```
