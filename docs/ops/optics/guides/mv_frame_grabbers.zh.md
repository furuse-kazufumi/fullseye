---
guide: mv_frame_grabbers
dim: optics
title: 图像采集卡(不属于光学系统,却决定能否采到图像)
title_en: Frame grabber boards (not optics, but they decide whether you can capture at all)
title_zh: 图像采集卡(不属于光学系统,却决定能否采到图像)
title_tw: 影像擷取卡(不屬於光學系統,卻決定能否擷取到影像)
title_ko: 프레임 그래버 보드(광학계는 아니지만 촬영 가능 여부를 정한다)
title_de: Framegrabber-Karten (keine Optik, entscheiden aber, ob überhaupt aufgenommen werden kann)
title_hi: Frame grabber boards (optics नहीं, पर यही तय करते हैं कि capture हो भी सकता है या नहीं)
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, videostream
lang: zh
translation_of: docs/ops/optics/guides/mv_frame_grabbers.md
source_sha256: 557994798a3a248f2fe13b8bb85a8726615d9d18e501d9db5e52ca968d06ed0f
---

<!-- fullseye guide: 机器视觉的周边知识。不是 op,而是说明传给 op 的值
     从何而来的教材。相关 op: interface_budget -->

# 图像采集卡(不属于光学系统,却决定能否采到图像)

光学决定"能否以所需的对比度成像",而图像采集卡决定
**能否不丢失地把它传输出去**。在高分辨率、高速和线扫描场合,
瓶颈不在传感器而在**传输带宽**,这种情况很常见。

## 接口带宽(已对照一手资料确认的值)

| 标准 | 每 1 路连接 | 实用配置 | 备注 |
| --- | --- | --- | --- |
| **CoaXPress CXP-6** | 6.25 Gbps | 1〜8 路连接 | 1 根同轴电缆同时传输供电(PoCXP)、控制和数据 |
| **CoaXPress CXP-12** | **12.5 Gbps** | **4 路连接 = 50 Gbps = 5 GB/s** | 足以让 8 bit、16k 线阵传感器以 **300 kHz** 运行的带宽 |
| **Camera Link Base** | 2.04 Gbps | 24 bit × 85 MHz,1 个连接器 | 老标准但仍在使用。电缆粗且短(〜10 m) |
| **Camera Link Medium** | 4.08 Gbps | 48 bit,2 个连接器 | |
| **Camera Link Full** | 5.44 Gbps | 64 bit | |
| **Camera Link Deca** | 6.80 Gbps | 80 bit | Camera Link 的上限 |
| Camera Link HS | 3.125 Gbps/lane | 多 lane | 长距离(可用光纤) |
| **Opt-C:Link**(AVAL DATA 自有) | **6.25 Gbps/ch**,2 ch 捆绑达 **12.5 Gbps** | 光纤(纤芯 50 / 62.5 µm,包层 125 µm) | **可延长至数百 m,抗噪声能力强**。通过图像、串口、触发、链路、用户 5 种数据包,连控制信号也走光纤。Camera Link 相机经转换单元(AOC-162 等)连接 |
| GigE Vision | 1 / 5 / 10 / 25 GigE | — | 电缆便宜且长。CPU 负载偏高 |

其设计是 **16k × 300 kHz × 8 bit ≈ 4.9 GB/s** 恰好装进 CXP-12 ×4 的 5 GB/s。
Vieworks VT 系列(TDI、最高 300 kHz)就是以此带宽为前提的产品。

## 主要厂商与现行采集卡

| 厂商 | 产品 | 已确认的规格 |
| --- | --- | --- |
| **Euresys** | Coaxlink Quad CXP-12 | PCIe 3.0 x8,相机带宽 5000 MB/s,CXP-12 ×4 |
| Euresys | Coaxlink Quad CXP-12 JPEG | 4 个独立通道 + **基线 JPEG 编码器 250 Mpixel/s**(在板上压缩) |
| Euresys | Coaxlink QSFP+ / Duo / Mono LH | 可配置 1〜8 台相机,覆盖 CXP-6〜CXP-12 |
| **Matrox** | Rapixo CXP(RAP8G4C12P602) | CoaXPress 2.0,CXP-12 ×4,PCIe 3.1 x8,**12.5 GB/s 相机带宽**,PoCXP |
| **Teledyne DALSA** | Xtium2-CXP PX8 Quad | CXP-12 ×4,相机带宽 5000 MB/s,PCIe Gen3 x8(总线最高 7000 MB/s) |
| BitFlow | Claxon / Cyton | CXP / Camera Link |
| Active Silicon | FireBird | CXP / Camera Link |
| Kaya Instruments | Komodo | CXP |
| **AVAL DATA(アバールデータ)** | APX-3312A / APX-3313A(Camera Link)、Opt-C:Link 系列 | 同时拥有 Camera Link 采集卡和自有光接口。在日本国内的设备领域实力强 |
| Euresys | Grablink(Camera Link) | 与 CXP 的 Coaxlink 分属不同产品线,继续提供 Camera Link |

## 为什么在虚拟化中不能忽视

0. **需要长距离时,可选项会变少**。Camera Link 在 10 m 级就到头了,
   而 Opt-C:Link(光纤)可达数百 m。在设备庞大、电气噪声多的现场(焊接、
   电机驱动器附近),先于带宽,**距离和抗噪声能力**决定了标准的选择。
1. **在面阵扫描中,瓶颈通常是传感器**。IMX541(20.3 MP、8 bit)每 1 帧 20.3 MB,
   因此在 5 GB/s 下理论上可达 246 fps,但传感器本身只有 18〜42 fps。→ 带宽有富余。
2. **在线扫描 / TDI 中,瓶颈变成带宽**。16k × 300 kHz 会用满 4.9 GB/s。
   若想提高行频,首先要谈的是采集卡和电缆的数量。
3. **编码器同步**(线扫描专用)。让输送速度与行频同步是
   采集卡的工作,这里一旦偏离,**图像的纵横比就会失真**。这是面阵扫描中
   不存在的故障模式,光学调得再好也无法修正。
4. **板上预处理**。在采集卡上做阴影校正、位打包和 JPEG 压缩,
   可降低主机负载。部署用合成数据训练的模型时,
   **推理之前会经过这道校正**,因此需要事先决定是让训练数据也经过同样的校正,
   还是用校正前的原始数据训练。
5. **触发抖动**。与脉冲照明或频闪同步时,抖动会变成曝光波动 =
   亮度波动。域随机化中的 `intensity_jitter` 本来的依据就在这里。

## 与实现的衔接

`optscene.interface_budget()` 根据传感器的像素数、位深和接口,
返回**受带宽限制的最大帧率 / 行频**。这是一个与传感器侧的上限对照、
预先弄清"哪一方是瓶颈"的 op。
