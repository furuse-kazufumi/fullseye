---
guide: mv_standards
dim: optics
title: 相机接口规格与标准组织
title_en: Camera interface standards and the bodies behind them
title_zh: 相机接口规格与标准组织
title_tw: 相機介面規格與標準組織
title_ko: 카메라 인터페이스 규격과 단체
title_de: Kameraschnittstellen: Standards und Gremien
title_hi: Camera interface standards और उनके पीछे की संस्थाएँ
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, videostream
lang: zh
translation_of: docs/ops/optics/guides/mv_standards.md
source_sha256: 1a9b3748af332a4f69b0fb9bd1b803a9b5c6c5c5356b77cb5403cd0f3e57bf3e
---

<!-- fullseye guide: 机器视觉的周边知识。不是 op,而是说明传给 op 的值
     从何而来的教材。相关 op: sensor_spec / lens_spec / light_spec / interface_budget -->

# 相机接口规格与标准组织

工业相机的接口已**作为行业标准实现了规格化**,每项标准都有主管组织。
弄清哪个组织掌管哪项标准,就能找到规格的一手资料。

## 1. 谁掌管哪项标准

| 组织 | 主管的标准 |
| --- | --- |
| **A3**(Association for Advancing Automation,原 AIA、美国) | **Camera Link**(含 PoCL / PoCL-Lite)、**Camera Link HS**、**GigE Vision**、**USB3 Vision** |
| **JIIA**(日本工业成像协会) | **CoaXPress**(2013 年发布)、IIDC2、SLVS-EC 系列 |
| **EMVA**(European Machine Vision Association) | **GenICam**(GenApi / **GenTL** / **SFNC** / PFNC)、**EMVA1288**(相机性能的测量方法)、**OOCI**(Open Optics Camera Interface) |
| **VDMA**(德国) | 与其说是标准本身,不如说负责解说、推广、协调 |
| **CMVU**(中国) | 中国方面的窗口 |
| **G3** | 横跨上述组织的**协调机构**。跨越各硬件标准保持共同软件层的框架 |

## 2. 有 2 个层(这是要点)

```
アプリケーション
      │
  GenICam（EMVA）          ← ソフトの層：機能名と設定の共通化
      │  GenApi / SFNC / GenTL / PFNC
      ├── Camera Link / Camera Link HS  (A3)
      ├── GigE Vision                   (A3)
      ├── USB3 Vision                   (A3)
      ├── CoaXPress                     (JIIA)
      └── Open Optics Camera Interface  (EMVA)
```

**GenICam 是 G3 的全部硬件标准共用的软件层**。所以
"改变曝光时间""设置 ROI"之类的操作,无论传输标准是 Camera Link、
CoaXPress 还是 GigE,都能用**同样的功能名**(SFNC = Standard Features Naming Convention)
来写。电缆和带宽因标准而异,应用程序却不必改写。

* **GenApi** —— 相机用 XML 描述自身的功能,主机读取后生成 UI/API。
* **SFNC** —— 功能名的标准(`ExposureTime`, `Gain`, `Width`, `OffsetX`, `TriggerMode` …)。
* **GenTL** —— 传输层的通用 API。吸收图像采集卡和驱动程序之间的差异。
* **PFNC** —— 像素格式名的标准(`Mono8`, `BayerRG12p`, `RGB8` …)。

## 3. EMVA1288(性能的测量方法)

同样由 EMVA 掌管的**相机性能测量、表述标准**。对 QE、时间暗噪声、饱和容量、
动态范围、最大 SNR、绝对灵敏度阈值,**用同样的步骤测量、以同样的形式给出**。

`image_sensors.md` 的传感器表之所以能跨厂商横向比较,
是因为所有值都按 EMVA1288 测得。反过来说,没有发布 EMVA1288 报告的
相机,其数值无法直接与其他厂商比较。

## 4. 对虚拟化的含义

* **传输标准变了,控制的词汇(SFNC)也不变**。所以
  `optscene` 的传感器/镜头/照明对象也应当用不依赖传输标准的量
  (曝光、增益、ROI、触发)来表示。把传输单独分离到 `interface_budget` 中,
  这种划分与上述结构是一致的。
* **EMVA1288 是单一事实来源**。目录中的 QE / 噪声 / 饱和容量取自这里。
  混入自有指标的数值会破坏横向比较。
* 一手资料的查找路径: 传输标准的规格书在 A3 / JIIA,软件层和测量方法在 EMVA。
  相机的实测值在厂商的 EMVA1288 报告中。
