# Fullseye 3DGS —— 使用方法（单条命令）

[日本語](./3DGS_USAGE.md) · [English](./3DGS_USAGE.en.md) · **简体中文** · [繁體中文](./3DGS_USAGE.tw.md) · [한국어](./3DGS_USAGE.ko.md) · [Deutsch](./3DGS_USAGE.de.md)

将 MuJoCo 的仿真场景转换为 **3D Gaussian Splatting**，生成可以全方位旋转查看的 GIF 以及新视角图像。相机位姿使用仿真的真值，因此**不需要 COLMAP**。

## 最简单的用法

在 imgevolve 文件夹下：

```bat
3dgs go2 --open
```

仅凭这一条命令，就会将 go2（四足机器人）转换为 3DGS，并自动打开完成的全方位 GIF。

- 更换场景：`3dgs cassie` / `3dgs apollo` / `3dgs anymal` / `3dgs spot`
- 使用自己的 MJCF：`3dgs <本地工作路径>\path\to\scene.xml`
- 查看列表：`3dgs --list`

## 质量预设

```bat
3dgs go2 --quality fast       :: 128px / 8 千个高斯(数秒完成,适合预览)
3dgs go2 --quality balanced   :: 256px / 2 万个高斯(默认)
3dgs go2 --quality high       :: 384px / 4.5 万个高斯(最精细)
```

## 更精细(densify)

```bat
3dgs go2 --quality high --densify --open
```

加上 `--densify` 后，训练过程中会**自动增加高斯数量以提升细节**（仅限 native gsplat）。以 go2 为例，会从约 8 千个增长到约 5 万个，机身和腿部会更加平滑。通常几秒到十几秒即可完成。

## backend 自动选择

- 若可使用 **native gsplat**（tile CUDA），会自动采用（速度快、精度高，可达每秒数百 it）
- 若不可用，会自动回退到**纯 PyTorch**（较慢，但可以运行）
- 也可通过 `--backend torch` / `--backend gsplat` 明确指定

环境（CUDA / 编译器）由 launcher 自动配置，无需关心 vcvars 等设置。

## 从 Studio 使用

启动 `spikes/studio_app.py` → 在"以 3D 查看仿真模型 / 转换为 3DGS"面板中，选择场景名称（点击标签或直接输入）和质量后点击"3DGS 训练 🎇" → 完成后会打开全方位 GIF。

## 输出

在 `out/3dgs_<scene>/`（或 `--out` 指定的目录）下会生成：
- `turntable.gif` … 全方位预览
- `novelview.png` … 左 = 真值 / 右 = 新视角渲染
- `gaussians.npz` … 训练完成的高斯(npz)
- `gaussians.ply` … 标准 3DGS .ply 格式(native 模式下)。可**拖放到 SuperSplat 等 Web 查看器**中打开
- `report.json` … PSNR 等指标

## 所需环境

- 用于 GPU 训练的 venv `.venv-gsplat`（torch cu128）
- 若使用 native，需要 `.gsplat-cuda`（CUDA 12.8）+ VS BuildTools 的 C++ 工具。详情及复现步骤见 `docs/GSPLAT_NATIVE_WINDOWS.md`

> 如实说明：`--densify` 的效果因场景而异。像 go2 这样的整块结构会变得很干净，但像 cassie 这样细长的双足机器人，可能会对训练视角过拟合，导致 hold-out 略微变软。建议先不加此选项尝试，若觉得不够再加上。

## 播放动作(--motion)

```bat
3dgs go2 --motion --open
```

不再是静止画面，而是生成**运动中机器人的 3DGS**。原理如下：
1. 在标准姿势下训练 3DGS
2. 通过 **segmentation** 确定每个高斯来自 MuJoCo 的哪个 body（连杆）并完成绑定
3. 移动关节（默认 = 正弦波），用每一帧的 body 姿态（仿真真值）进行刚体蒙皮 → 重新渲染 → 生成 `motion.gif`

由于机器人是刚性连杆的集合，因此无需完整的 4D-GS 即可自然运动。可通过 `--frames N` 更改帧数。

> 如实说明：默认的动作是用于演示的正弦波（并非实际的行走策略）。由于仿真姿态是真值，不会出现结构性崩坏，但脚部附近可能出现轻微噪声（初始化点的 body 归属边界处）。

### 自动生成步态(gait)

```bat
3dgs go2 --motion --gait trot --open
```

`--gait trot` 会自动生成并播放**四足的 trot 步态**（对角腿同相位交替迈步）。会根据关节名称（FL/FR/RL/RR 或 LF/RF/LH/RH + thigh/calf）自动检测腿部，因此适用于 go2 和 anymal。无法检测的模型会回退到正弦波。若要使用实际行走策略的输出，可使用 `--motion-file traj.npy`（qpos 轨迹 (F,nq)）。
