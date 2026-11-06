---
guide: mv_standards
dim: optics
title: Camera interface standards and the bodies behind them
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
lang: en
translation_of: docs/ops/optics/guides/mv_standards.md
source_sha256: 1a9b3748af332a4f69b0fb9bd1b803a9b5c6c5c5356b77cb5403cd0f3e57bf3e
---

<!-- fullseye guide: background knowledge around machine vision. Not an op, but teaching
     material that shows where the values passed to ops come from. Related ops: sensor_spec / lens_spec / light_spec / interface_budget -->

# Camera interface standards and the bodies behind them

The interfaces of industrial cameras are **standardized as industry standards**, and each standard has a body
in charge of it. Knowing which body holds which standard lets you reach the primary sources of the specifications.

## 1. Who holds what

| Body | Standards in its charge |
| --- | --- |
| **A3** (Association for Advancing Automation, formerly AIA, USA) | **Camera Link** (including PoCL / PoCL-Lite), **Camera Link HS**, **GigE Vision**, **USB3 Vision** |
| **JIIA** (Japan Industrial Imaging Association) | **CoaXPress** (released 2013), IIDC2, the SLVS-EC family |
| **EMVA** (European Machine Vision Association) | **GenICam** (GenApi / **GenTL** / **SFNC** / PFNC), **EMVA1288** (measurement method for camera performance), **OOCI** (Open Optics Camera Interface) |
| **VDMA** (Germany) | Less the standards themselves than explanation, promotion and coordination |
| **CMVU** (China) | The point of contact on the Chinese side |
| **G3** | A **coordinating body** across the above. A framework for keeping a common software layer across hardware standards |

## 2. There are 2 layers (this is the key point)

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

**GenICam is the common software layer used by all G3 hardware standards**. That is why
operations such as "change the exposure time" or "set an ROI" can be written with **the same feature names**
(SFNC = Standard Features Naming Convention) whether the transmission standard is Camera Link,
CoaXPress or GigE. Cables and bandwidth differ by standard, yet the application does not have to be rewritten.

* **GenApi** — the camera describes its own features in XML, and the host reads it to build the UI/API.
* **SFNC** — the standard for feature names (`ExposureTime`, `Gain`, `Width`, `OffsetX`, `TriggerMode` …).
* **GenTL** — the common API of the transport layer. It absorbs the differences between frame grabbers and drivers.
* **PFNC** — the standard for pixel format names (`Mono8`, `BayerRG12p`, `RGB8` …).

## 3. EMVA1288 (measurement method for performance)

The **standard for measuring and stating camera performance**, held by the same EMVA. QE, temporal dark noise, saturation capacity,
dynamic range, maximum SNR and absolute sensitivity threshold are **measured with the same procedure and reported in the same form**.

The sensor table in `image_sensors.md` can be compared side by side across makers
because all of its values were measured with EMVA1288. Conversely, the figures of cameras without an EMVA1288 report
cannot be compared with other makers as they are.

## 4. Implications for virtualization

* **Even if the transmission standard changes, the control vocabulary (SFNC) does not**. That is why it is correct for
  the sensor / lens / lighting objects of `optscene` to hold quantities that do not depend on the transmission standard
  (exposure, gain, ROI, trigger). Transmission is separated out
  into `interface_budget`, and this division matches that structure.
* **EMVA1288 is the single source of truth**. The QE / noise / saturation capacity in the catalogue are taken from here.
  Mixing in figures from proprietary metrics breaks side-by-side comparison.
* How to trace primary sources: the specifications of the transmission standards are at A3 / JIIA; the software layer and the measurement method are at EMVA.
  Measured values of cameras are in the makers' EMVA1288 reports.
