---
guide: virtual_machine_vision
dim: optics
title: 虚拟机器视觉 —— 梳理参数与对象模型
title_en: Virtual machine vision — enumerating the parameters and an object model
title_zh: 虚拟机器视觉 —— 梳理参数与对象模型
title_tw: 虛擬機器視覺 —— 梳理參數與物件模型
title_ko: 가상 머신 비전 — 파라미터 도출과 객체 모형
title_de: Virtuelle Bildverarbeitung — Parameter erfassen und Objektmodell
title_hi: Virtual machine vision — parameters की सूची और एक object model
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, optics/scene, optics/imaging
lang: zh
translation_of: docs/ops/optics/guides/virtual_machine_vision.md
source_sha256: cbfb71e92e1e9418da597e5f8b96b9f8641a650352d1a49624bfd0befef7f0cb
---

# 虚拟机器视觉 —— 梳理参数与对象模型

为了在物理空间中搭建观察光学系统并生成图像,本台账梳理了**给出哪些量才能确定图像**。
若在这一点含糊不清的情况下继续添加实现,就会做出只是看起来像、却与实机不对应的
生成器(2026-09-05 的用户指示:"请先梳理传感器的参数、镜头的参数、
光源的参数、布局的参数再推进。我想它们自然会
成为对象")。

## 0. 一手资料(本台账的依据)

| 出处 | 从中采用的事实 |
| --- | --- |
| SYNOSIS, arXiv:2410.14844(金属表面检测的图像合成) | 粗糙金属 BRDF(roughness 0.05–0.3)/表面形貌由焦点变化显微镜的实测值(横向 0.44–1.75 µm・纵向 410 nm)转换为法线贴图(13107²・6.1 µm 间隔)/切削面采用程序化模型(刀具旋转环纹・路径・余弦・振动噪声,环径 4–8 mm・中心间距 0.09 mm)/喷砂采用 ADSN + Efros–Freeman/缺陷为 3-D 形状的布尔差,掩膜为与 0.9–1.0 倍刀具形状的交集/path tracing 256 spp・8 bounce・1224×1025/环面形环形光 |
| Adimec / Vision Doctor(明场 对 暗场) | 划痕**在明场下呈暗、在暗场下呈亮**(对比度反转)。暗场的入射角以 10–15° 为定式 |
| automatica Munich “Virtualising Machine Vision” | 光学数字孪生 × PBR × 缺陷模型 × 像素精度的自动标注 |

RAD 语料库中**没有机器视觉光学这一领域**(最接近的是
`halcon_operators_corpus_v2` 和 `fullseye_3d_vision_corpus_v2`)。本文件是填补这一空缺的
知识层,此后的实现都以此为起点。

---

## 1. 传感器(Sensor)

| 参数 | 符号・单位 | 对图像的作用 | fullseye 的现状 |
| --- | --- | --- | --- |
| 像素间距 | p [µm] | 采样极限 2p。与衍射极限哪个大决定了瓶颈 | `optical_camera(pixel_um=)` ✓ |
| 分辨率 | W×H [px] | 视场 = W·p·WD/f | ✓ |
| 量子效率 | QE(λ) [-] | 电子数 = 光子数 × QE。随波长变化 | `sensor_spec(quantum_efficiency=)` ✓(常数)/**QE(λ) 曲线尚未实现** |
| 满阱 | FW [e⁻] | 饱和。过曝不会折返 | `sensor_capture(full_well_e=)` ✓ |
| 读出噪声 | σ_r [e⁻] | 暗部的下限。在暗场下起作用 | ✓ |
| 暗电流 | [e⁻/s] | 长曝光时起作用。暗场的曝光较长 | `sensor_spec(dark_e_per_s=)` ✓(由 `layout_capture` 与曝光时间合成)/温度依赖性尚未实现 |
| ADC 位深 | [bit] | 量化。8 bit 时微小对比度会被量化截断而消失 | ✓ |
| 增益 | [e⁻/DN] | 与散粒噪声之比 | ✓ |
| 快门方式 | rolling / global | 运动物体的畸变。对传送带上的零件起作用 | `sensor_spec(shutter=)` **仅作记录**。卷帘快门的畸变尚未实现 |
| 光谱灵敏度 | S(λ) | 与光源光谱的乘积决定有效亮度 | **尚未实现** |

## 2. 镜头(Lens)

| 参数 | 符号・单位 | 对图像的作用 | fullseye 的现状 |
| --- | --- | --- | --- |
| 焦距 | f [mm] | 倍率 m = f/(WD−f)、视场 | ✓ |
| F 值 / NA | N, NA = 1/(2N) | 衍射・景深・亮度。工作 F 值 N_w = (1+\|m\|)·N | `optical_budget(f_number=/na=)` ✓ |
| 工作距离 | WD [mm] | 倍率・布局・照明的摆放位置 | ✓ |
| 容许弥散圆 | c [µm] | 景深 DOF ≈ 2·N_w·c/m²(几何)+ 2λN_w²/m²(波动) | ✓ |
| 艾里半径 | 1.22·λ·N_w [µm] | 细微缺陷可见性的下限。**与像素比较** | `airy_radius_um` ✓ / `optics.airy_pattern` ✓ |
| MTF | MTF(ν) | 对比度传递。缺陷是高频的,所以这里起作用 | `optics.mtf_diffraction` / `psf_to_mtf` ✓ |
| 像差 | Seidel / Zernike | 视场边缘模糊・不对称 | `raytrace.seidel_coefficients` / `opd_map` ✓(未接入) |
| 畸变 | k1, k2 … | 直接影响尺寸测量 | `lensimage.distortion_map` ✓(未接入) |
| 周边光量 | cos⁴θ 等 | 边缘暗 = 边缘的缺陷看不见 | `optics.relative_illumination` ✓(未接入) |
| 远心性 | 物方/双侧 | 倍率不随距离变化 = 尺寸测量的前提 | **尚未实现** |
| 色差 | Δf(λ) | 不同波长的对焦位置不同 | `raytrace.chromatic_shift` ✓(未接入) |

## 3. 光源(Light)

| 参数 | 单位 | 对图像的作用 | fullseye 的现状 |
| --- | --- | --- | --- |
| 类型 | LED / 卤素灯 / 激光 | 光谱宽度和相干性不同 | `light_spec(source=)` ✓(LED 窄带 / 卤素灯宽带 / 激光单波长)。相干性尚未实现 |
| 光谱 | S(λ) | 材料的反射率依赖于波长(金在短波长下反射率下降)。粗糙度对应的镜面比例 exp(−(4πσcosθ/λ)²) 也依赖于波长 | `render_optscene(wavelength_nm=)` 单波长 ✓/宽带用 `layout_capture(spectral_samples=)` 叠加 ✓ |
| 相干性 | 空间・时间 | 激光会产生散斑。卤素灯不会 | **尚未实现**(`optics.gaussian_beam` / `angular_spectrum_propagate` 是基础) |
| 辐射强度分布 | I(θ) = I₀cosⁿθ | 均匀性。边缘照度下降 | `light_source(cos_exponent=)` ✓ |
| 灯具的实际尺寸 | [mm] | **是否作为镜像被拍到** = 明场/暗场的本质 | `light["size_mm"]` ✓(2026-09-05 添加) |
| 偏振 | 线/圆 | 去除反光。Jones/Mueller | `optics.jones_*` / `mueller_*` ✓(未接入) |
| 脉冲/连续 | [µs] | 抑制运动模糊 | **尚未实现** |

## 4. 布局(Layout)

| 参数 | 单位 | 对图像的作用 | fullseye 的现状 |
| --- | --- | --- | --- |
| 照明的仰角 | [deg] | 明场(灯具进入镜像)/ 暗场(不进入,10–15°)的分界 | `light_source(height_mm, radius_mm)` ✓ |
| 照明的方位 | [deg] | 对比度随其与划痕方向的关系而变 | ✓ |
| 照明的形状 | 同轴/环形/穹顶/条形/背光 | 什么会进入镜像 | ✓ |
| 相机的倾斜 | [deg] | **从正上方看平面时反射方向集中在天顶,加工纹理显现不出来**(实测) | `optical_camera(tilt_deg=)` ✓ |
| 工作距离 | [mm] | 倍率・照明的摆放位置・景深 | ✓ |
| 视场 | [mm] | 零件能否容纳 | `camera["fov_mm"]` ✓ |
| 零件姿态的波动 | [mm], [deg] | 域随机化的主轴 | `inspection_dataset(jitter_mm=, tilt_jitter_deg=)` ✓ |
| 背景・夹具 | — | 误检的主要原因 | 仅有 `scene_plane` / `scene_box` / CSG(不支持 CAD 网格) |

---

## 5. 对象模型(已实现)

梳理之后,参数自然分为 4 个块。**每个块做成 1 个对象**,
由布局把其余 3 个捆在一起。

`sensor_spec` / `lens_spec` / `light_spec` / `vision_layout` / `layout_capture`。

```
Layout ─┬─ Sensor  (画素・雑音・飽和・分光感度)
        ├─ Lens    (f, NA/F, WD, 収差, 歪曲, MTF)
        ├─ Light[] (スペクトル, コヒーレンス, 配光, 実体寸法, 姿勢)
        └─ Scene   (部品 + 材質 + 仕上げ + 欠陥)   ← 既存の scene_* op
```

导出量(倍率・工作 F 值・艾里半径・景深・视场・分辨极限)由
`optical_budget` **以闭式**返回。在拍摄之前先看这里、判断配置是否可行,
就是设置这一层的目的。

## 6. PoC 的顺序(从基本形开始)

1. **基本形**: 铝 + 拉丝纹 + 同轴照明 + 单波长。用 `observe_surface` 写成 1 行。
   合格标准是"划痕在明场下呈暗"(与教科书的符号一致)。
2. 加上暗场,确认会出现**对比度反转** ✓(参见 §7。缺陷的粗糙度是关键)。
3. 改变波长,确认粗糙度与波长的关系 exp(−(4πσcosθ/λ)²) 起作用。
4. 扩展到宽带(卤素灯)= 多个波长的叠加、LED = 窄带、激光 = 单波长 +
   散斑。
5. 像差・畸变・周边光量通过在后级施加 `lensimage.render_through_lens` 来汇合。

## 7. 已解决的问题 / 尚未达成的部分(截至 2026-09-05)

### 已解决: 明场 / 暗场的对比度反转

只有镜面反射的模型中,暗场**在原理上**不能成立。要把低角度 12° 的照明返回到正上方的相机,
面法线需要**倾斜 (90−12)/2 = 39°**,而划痕的倾斜(5–15°)达不到。
实际的暗场之所以发亮,是因为划痕是材料被削去的痕迹,**局部粗糙,靠散射把光返回**。

给缺陷赋予 `roughness_um`,仅用 1 个粗糙度就同时引起
"镜面比例 exp(−(4πσcosθ/λ)²) 下降 → 明场下变暗"与
"散射瓣变宽(RMS 斜率 √2σ/T)→ 暗场下变亮"。
实测 **粗糙度 0.4 µm 时 明场 −59% / 暗场 +91%**。

**界限**: 这不是严格的散射计算,而是基于"镜面比例 × 表面纹理的粒度"的伪生成。
出现反转的是缺陷粗糙度 **0.2–0.6 µm** 的情况。比这更粗糙时散射扩散过度,即使在暗场下也会
比周围更暗。表现上的分工是"可分辨的凹凸 = 法线,不可分辨的凹凸 = 粗糙度",
`surface_finish` 的加工纹理相当于把前者**压缩**成数个倍频程噪声的表现。

### 已解决: 线扫描 / TDI

`linescan_capture` 一边输送一边堆叠。纵横比 =(速度/行频)/(像素间距·WD/f)
偏离 1 时图像会变形(光学无法修正、线扫描特有的故障模式)。
TDI 中电荷与被摄物一起转移,所以**完全同步时所有级都看到同一个物点**
(只是变亮)。同步误差有多大就拖尾多少。

### 已解决: 传输带宽

`interface_budget` 根据 CXP / Camera Link / CLHS / GigE / Opt-C:Link 的带宽
返回受带宽限制的速率。16k・8bit 经 CXP-12 ×4 为 **324 kHz** ―― 与 Vieworks VT 的
标称 300 kHz 相符。在面阵扫描中则反过来带宽有富余(IMX541 可达 262 fps,而
传感器为 18–42 fps)。**瓶颈在哪一方会随配置而互换**。

### 尚未达成

* 传感器: QE(λ) 光谱曲线・暗电流的温度依赖性・转换增益・PRNU / DSNU・
  卷帘快门的畸变。目录中的值是 Basler 的 EMVA1288 实测值(包含相机实现)。
* 镜头: 像差・畸变・周边光量在 `raytrace` / `lensimage` / `optics` 中已有实现,却
  **未接入**。远心性尚未实现。线扫描专用镜头(大像圈、
  弧矢/子午的像差分配)也尚未建模。
* 光源: 相干性(激光散斑)、偏振(Jones/Mueller 在 `optics` 中已有)、
  脉冲驱动。宽带仅做到用 `layout_capture(spectral_samples=)` 叠加为止。
* 零件: 无法读取 CAD 网格(只有解析形状 + CSG 差集)。也没有夹具和输送机构。
