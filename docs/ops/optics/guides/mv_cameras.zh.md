---
guide: mv_cameras
dim: optics
title: 工业相机厂商(与传感器的对应、线扫描 / TDI)
title_en: Industrial camera makers (sensor mapping, line scan / TDI)
title_zh: 工业相机厂商(与传感器的对应、线扫描 / TDI)
title_tw: 工業相機廠商(與感測器的對應、線掃描 / TDI)
title_ko: 산업용 카메라 제조사(센서와의 대응·라인 스캔 / TDI)
title_de: Hersteller von Industriekameras (Sensorzuordnung, Zeilenkamera / TDI)
title_hi: Industrial camera निर्माता (sensor mapping, line scan / TDI)
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, optics/scene, optics/imaging
lang: zh
translation_of: docs/ops/optics/guides/mv_cameras.md
source_sha256: 605125b29a4c6cd9d419ec3eefe6f94d51ea87ffa13f54c28b8ec65efa354d59
---

<!-- fullseye guide: 机器视觉的周边知识。不是 op,而是说明传给 op 的值
     从何而来的教材。相关 op: linescan_capture / sensor_spec -->

# 工业相机厂商(与传感器的对应、线扫描 / TDI)

传感器一侧的台账是 `image_sensors.md`。本页讲**相机一侧**,尤其要把握
"无法从传感器型号查到的领域"和"不属于面阵扫描的领域"。

## 1. 采购传感器制造相机的厂商

Basler / FLIR (Teledyne) / IDS / Baumer / Allied Vision / JAI / XIMEA / SVS-Vistek /
Matrix Vision / The Imaging Source 等。所搭载的传感器(IMX / XGS / GMAX …)是公开的,
因此可以从 `image_sensors.md` 的表中查到规格。**相机改变的是分辨率的裁切方式
(有时会裁掉边缘),以及由接口决定的帧率与 ROI 约束**,
画质本身由传感器决定。

## 2. 自研传感器的厂商(无法从型号查到)

Canon(仅供自家产品)/ Teledyne DALSA・e2v(传感器也对外销售)/ Photron(高速相机)/
Vision Research = Phantom(28 µm 像素的定制传感器,TMX 为背照式)/ Hamamatsu(自研与
外购混用。ORCA-Quest 由 Fairchild Imaging 开发)/ Sony(两者兼有)。
→ 详见 `image_sensors.md` 的相应小节。

## 3. 擅长大幅面、超高分辨率与 TDI 的厂商

### Vieworks(韩国)

产品线覆盖面阵扫描(VC / VN / VP / VNP / VQ / VZ / VX)与线扫描・TDI(VT / VL)。
从虚拟化的角度看,重要的是以下 3 点:

| 系列 | 特点(公开规格) | 对光学模型的含义 |
| --- | --- | --- |
| **VP** | 25 MP〜**288 MP**,4.2〜31 fps。**传感器可冷却至比环境温度低最多 20 °C** | 长时间曝光时暗电流也能得到抑制 → 对暗场和微弱信号有效。可将 `sensor_spec(dark_e_per_s=)` 设为以冷却为前提的值 |
| **VN** | 面向静止物体的超高分辨率。VN-200MX 通过**像素位移将 50 MP 扩展到 427 MP**,经 CoaXPress 达 30 fps | 像素位移是"传感器 = 相机"这一等式失效的例子。有效像素间距被机械地细分 |
| **VT** | **TDI**(时间延迟积分)。256 级带来 **256 倍灵敏度**,行频最高 300 kHz。面向 FPD / 半导体检测 | 无法用面阵传感器模型表示(见下文) |

### 竹中系统机器(日本,1975 年创立)

**线扫描相机的先驱**。是最早用线扫描实现人工外观检测自动化的 1 家公司之一,
用于针孔检测、缺陷检测和片材宽度测量。近年来主要用于半导体制造设备和
液晶面板检测。也被国际空间站"希望号"(Kibo)舱段采用。
产品有 `TL-` 系列(例如 TL-16KNCL / TL-8K35ACL / TL-4096UCL)和 `TLC-` 系列(彩色)。

> 注: 截至 2026-09-05,`takex-system.co.jp` 在本环境中无法进行 DNS 解析,
> 各型号的像素数和行频尚未获取。型号命名(16K / 8K / 4096)表示
> **每 1 行的像素数**是业界惯例,但实际数值需以数据手册为准。

## 4. 线扫描 / TDI 需要另一种模型(当前的缺口)

`optscene` 的相机只有面阵传感器(2-D 网格),无法表示线扫描和 TDI。
这正是两家公司的主力产品所在,因此对虚拟化而言是很大的缺失。所需参数:

| 参数 | 含义 | 与面阵的区别 |
| --- | --- | --- |
| 1 行像素数 | 4096 / 8192 / 16384 … | 高度为 1 的"传感器" |
| 行频 [kHz] | 每 1 秒的行数 | 相当于帧率 |
| 输送速度 [mm/s] | 传送带或载物台的速度 | **与它组合决定扫描方向的分辨率** |
| 扫描方向的像素实际尺寸 | 速度 ÷ 行频 | 速度偏离时**纵横比失真**(面阵没有的故障模式) |
| TDI 级数 | 32 / 64 / 128 / 256 | 灵敏度为级数倍。但**同步偏离时会模糊相应的级数** |
| 照明 | 必须使用**线光源** | 不能使用环形光/穹顶光(只需要 1 行) |

若要实现: 把传感器做成高度为 1 的相机,在布局中加入输送速度和行频,
逐 1 行拍摄并堆叠。TDI 只要做 M 行累加,并把同步误差作为偏移量给出,
就能连"同步偏离就会模糊"这一实机的主要故障模式也一并再现。
